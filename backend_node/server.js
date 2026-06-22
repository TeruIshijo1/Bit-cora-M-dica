const express = require('express');
const cors = require('cors');
const { FeatureSetMatcher } = require('uareu-biometric');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' })); // Allow up to 50mb in case of many medicos

let matcher = null;

async function initMatcher() {
    try {
        matcher = new FeatureSetMatcher();
        await matcher.initialize();
        console.log('✅ FeatureSetMatcher inicializado correctamente.');
    } catch (error) {
        console.error('❌ Error inicializando FeatureSetMatcher:', error);
    }
}

async function getAnsiFeatureSet(fmdStr) {
    let obj;
    try {
        obj = JSON.parse(fmdStr);
    } catch (e) {
        throw new Error("Formato de huella obsoleto. Por favor vuelva a registrar su huella.");
    }
    if (!obj.metadata || !obj.base64) {
        throw new Error("Formato de huella RAW inválido.");
    }
    
    // Clean Base64 string if it contains data URI header
    const cleanBase64 = obj.base64.replace(/^data:[^;]+;base64,/, "");
    const rawBuffer = Buffer.from(cleanBase64, 'base64');
    const ANSI_378_2004 = 0x001B0001;
    
    const ansiFmd = await matcher.uareu.dpfjCreateFmdFromRaw(
        rawBuffer, 
        obj.metadata.width, 
        obj.metadata.height, 
        obj.metadata.resolution, 
        ANSI_378_2004
    );
    return ansiFmd;
}

app.post('/match-bulk', async (req, res) => {
    try {
        const { fmd1, medicos } = req.body;

        if (!fmd1 || !Array.isArray(medicos)) {
            return res.status(400).json({ error: 'Debes enviar fmd1 y un arreglo de medicos' });
        }

        if (!matcher) {
            return res.status(500).json({ error: 'Matcher no está inicializado' });
        }

        let ansiFmd1;
        try {
            ansiFmd1 = await getAnsiFeatureSet(fmd1);
        } catch(e) {
            return res.status(400).json({ error: 'Huella ingresada inválida: ' + e.message });
        }

        const ANSI_378_2004 = 0x001B0001;
        const falseAcceptRate = 10000;

        for (let medico of medicos) {
            try {
                if (!medico.fmd_template) continue;
                const ansiFmd2 = await getAnsiFeatureSet(medico.fmd_template);
                
                const score = await matcher.uareu.dpfjCompareFeatureSets(
                    ansiFmd1.data, ansiFmd1.size, 
                    ansiFmd2.data, ansiFmd2.size, 
                    ANSI_378_2004
                );

                if (score <= falseAcceptRate) {
                    return res.json({
                        success: true,
                        isMatch: true,
                        match_id: medico.id,
                        score: score
                    });
                }
            } catch(err) {
                // Ignore invalid old fmds in DB
                console.warn(`Skipping invalid fmd for medico ${medico.id}: ${err.message}`);
            }
        }

        res.json({
            success: true,
            isMatch: false,
            match_id: null
        });

    } catch (error) {
        console.error('Error en /match-bulk:', error);
        res.status(500).json({ error: error.message || 'Error interno del servidor' });
    }
});

const PORT = 8082;
app.listen(PORT, async () => {
    console.log(`🚀 Microservicio Biométrico corriendo en el puerto ${PORT}`);
    await initMatcher();
});
