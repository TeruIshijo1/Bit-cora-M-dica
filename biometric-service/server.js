'use strict';
const crypto = require('node:crypto');
const express = require('express');
const cors = require('cors');
const { NativeDevice } = require('./native-device');
const protocol = require('./capture-protocol');

const errors = {
    INVALID_CHALLENGE: 'El challenge de captura no es válido.',
    EXPIRED_CHALLENGE: 'El challenge venció. Solicite una captura nueva.',
    READER_BUSY: 'El lector está ocupado. Cancele la captura anterior y reintente.',
    READER_DISCONNECTED: 'Lector desconectado.',
    CAPTURE_TIMEOUT: 'Tiempo de captura agotado. Vuelva a colocar el dedo.',
    CAPTURE_CANCELLED: 'Captura cancelada.',
    READER_CHANGED: 'El dispositivo cambió durante la captura.',
    FMD_EXTRACTION_FAILED: 'No fue posible extraer una huella válida. Reintente.',
    SDK_UNAVAILABLE: 'El SDK biométrico no está disponible.',
    READER_OPEN_FAILED: 'No se pudo abrir el lector. Cierre otras aplicaciones biométricas y reintente.',
    READER_NOT_READY: 'El lector no está listo. Reconéctelo y reintente.',
    READER_SELECTION_REQUIRED: 'Conecte un solo lector para iniciar la captura.',
    CAPTURE_UNSUPPORTED: 'El dispositivo no permite la captura requerida.',
    MATCH_FAILED: 'La comparación biométrica falló. Solicite una captura nueva.',
    INVALID_FMD: 'La plantilla no es un FMD ANSI válido.',
    ACQUISITION_USED: 'Esta adquisición ya fue utilizada. Solicite una captura nueva.',
    ACQUISITION_INVALID: 'Adquisición vencida o ajena a la sesión. Solicite una captura nueva.',
    CLIENT_CAPTURE_RETIRED: 'La captura enviada por el navegador está retirada. Use el agente local V2.',
    CLIENT_CAPTURE_FORBIDDEN: 'Sólo se admite la autorización de adquisición emitida por el servidor.',
    CAPTURE_FAILED: 'Captura incorrecta. Limpie el dedo y reintente.'
};
function createService({ device = new NativeDevice(), secret = process.env.BIOMETRIC_ATTESTATION_SECRET || '', now = Date.now } = {}) {
    if (secret.length < 32) throw new Error('BIOMETRIC_ATTESTATION_SECRET debe tener al menos 32 caracteres.');
    const app = express();
    const origins = (process.env.BIOMETRIC_ALLOWED_ORIGINS || 'http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173').split(',').map(value => value.trim());
    const acquisitions = new Map(), challenges = new Map();
    let active = null, probePending = null;
    app.disable('x-powered-by');
    app.use((req, res, next) => {
        if (req.headers.origin && !origins.includes(req.headers.origin)) return res.status(403).json({ code: 'ORIGIN_DENIED', error: 'Origen no autorizado.' });
        if (!['127.0.0.1', 'localhost', '[::1]'].includes(req.hostname)) return res.status(403).json({ code: 'HOST_DENIED', error: 'Host no autorizado.' });
        if (origins.includes(req.headers.origin)) res.set('Access-Control-Allow-Private-Network', 'true');
        next();
    });
    app.use(cors({ origin: origins, methods: ['POST', 'GET', 'OPTIONS'] }));
    app.use(express.json({ limit: '10mb' }));
    app.use((_req, res, next) => { res.set('Cache-Control', 'no-store'); next(); });
    const error = (res, status, code) => res.status(status).json({ code, error: errors[code] || 'La adquisición biométrica no está disponible. Reintente.' });
    function clean() {
        for (const [id, item] of acquisitions) if (item.expires <= now()) {
            item.code = item.code || 'CAPTURE_TIMEOUT';
            item.state = 'FAILED';
            item.abort.abort();
            clearTimeout(item.timer);
            clearTimeout(item.releaseTimer);
            item.result = null;
            acquisitions.delete(id);
            // La exclusividad pertenece sólo a esta estación. Una captura nativa
            // atascada nunca debe conservar el lector después de vencer su ticket.
            if (active === item) active = null;
        }
        for (const [id, expiry] of challenges) if (expiry <= now()) challenges.delete(id);
    }
    const cleanupTimer = setInterval(clean, 30000);
    cleanupTimer.unref();
    function bodyOnly(req, keys) { return req.body && !Array.isArray(req.body) && Object.keys(req.body).every(key => keys.includes(key)); }
    app.post(['/extract-fmd', '/acquisitions/start'], (req, res) => {
        if (req.body) { req.body.raw = null; req.body.fmd_template = null; }
        return error(res, 410, 'CLIENT_CAPTURE_RETIRED');
    });
    app.get('/health', (_req, res) => res.json({ status: 'alive', protocol_version: 2 }));
    app.get('/devices', async (_req, res) => {
        clean();
        if (active) return res.json({ devices: [active.deviceId || 'capturing'], busy: true });
        try {
            if (!probePending) probePending = Promise.resolve().then(() => device.probe()).finally(() => { probePending = null; });
            const result = await probePending;
            res.json({ devices: [result.device_id], busy: Boolean(active) });
        }
        catch (failure) { error(res, 503, failure.code || 'SDK_UNAVAILABLE'); }
    });
    app.post('/begin-capture', (req, res) => {
        clean();
        if (!bodyOnly(req, ['authorization'])) return error(res, 422, 'CLIENT_CAPTURE_FORBIDDEN');
        let context;
        try { context = protocol.authorize(req.body.authorization, secret, now()); }
        catch (failure) { return error(res, 401, failure.message); }
        if (challenges.has(context.challenge_id)) return error(res, 409, 'ACQUISITION_USED');
        if (active) return error(res, 409, 'READER_BUSY');
        const id = crypto.randomBytes(32).toString('base64url');
        const item = { id, context, authorization: req.body.authorization, started: new Date(now()).toISOString(), expires: Date.parse(context.expires_at), state: 'CAPTURING', abort: new AbortController(), result: null, deviceId: null };
        active = item;
        acquisitions.set(id, item); challenges.set(context.challenge_id, item.expires);
        item.timer = setTimeout(() => {
            item.code = 'CAPTURE_TIMEOUT'; item.state = 'FAILED'; item.result = null; item.abort.abort();
            // NativeDevice fuerza el cierre del bridge en 1 s. Este segundo límite
            // evita un bloqueo permanente si Windows no notifica la salida del proceso.
            item.releaseTimer = setTimeout(() => { if (active === item) active = null; }, 1500);
            item.releaseTimer.unref?.();
        }, Math.max(1, item.expires - now()));
        Promise.resolve().then(async () => {
            if (probePending) await probePending.catch(() => {});
            if (item.abort.signal.aborted || item.expires <= now()) throw new Error(item.code || 'CAPTURE_TIMEOUT');
            return device.capture({ timeoutMs: item.expires - now(), signal: item.abort.signal, onWaiting: deviceId => { item.deviceId = deviceId; } });
        }).then(async capture => {
            try {
                if (item.abort.signal.aborted || item.expires <= now()) throw new Error(item.code || 'CAPTURE_TIMEOUT');
                if (!item.deviceId || capture.device_id !== item.deviceId) throw new Error('READER_CHANGED');
                const start = Date.parse(capture.capture_started_at), end = Date.parse(capture.captured_at);
                if (!Number.isFinite(start) || !Number.isFinite(end) || start < Date.parse(item.started) || end < start || end > now() || end >= item.expires) throw new Error('CAPTURE_TIMEOUT');
                const data = protocol.parseFmd({ format: protocol.FORMAT, version: 1, data: capture.data });
                const bytes = Buffer.from(data, 'base64');
                const fmdHash = protocol.hash(bytes); bytes.fill(0);
                const payload = { protocol_version: 2, format: protocol.FORMAT, version: 1, data, fmd_hash: fmdHash,
                    challenge_id: context.challenge_id, session_id: context.session_id, acquisition_id: id,
                    acquisition_started_at: item.started, capture_started_at: capture.capture_started_at,
                    captured_at: capture.captured_at, device_id: capture.device_id, authorization: item.authorization };
                const candidates = protocol.matchJob(context, secret);
                let matched = null;
                try {
                    if (context.match_required) {
                        const match = await device.match(data, candidates);
                        if (match.success !== true || typeof match.isMatch !== 'boolean') throw new Error('MATCH_FAILED');
                        matched = match.isMatch ? candidates.find(row => row.id === match.match_id) : null;
                        if (match.isMatch && !matched) throw new Error('MATCH_FAILED');
                        payload.match_success = Boolean(matched);
                    } else payload.match_success = null;
                    payload.matched_identity = matched?.identity || null;
                    payload.matched_template_hash = matched?.template_hash || null;
                } finally { candidates.forEach(row => { row.data = null; }); }
                if (item.abort.signal.aborted || item.expires <= now()) throw new Error(item.code || 'CAPTURE_TIMEOUT');
                payload.attestation = protocol.sign(secret, 'HES-CAPTURE-ATTESTATION-V2\n' + protocol.message(payload));
                item.result = JSON.stringify(payload); item.state = 'READY';
            } finally { capture.data = null; }
        }).catch(failure => { item.result = null; item.code = item.code || failure.code || failure.message || 'CAPTURE_FAILED'; item.state = 'FAILED'; })
          .finally(() => { clearTimeout(item.releaseTimer); if (active === item) active = null; });
        res.status(201).json({ acquisition_id: id, state: 'CAPTURING', expires_at: context.expires_at });
    });
    function lookup(req, res) {
        clean();
        if (!bodyOnly(req, ['acquisition_id', 'authorization'])) { error(res, 422, 'CLIENT_CAPTURE_FORBIDDEN'); return null; }
        const item = acquisitions.get(req.body.acquisition_id);
        if (!item || item.authorization !== req.body.authorization) { error(res, 409, 'ACQUISITION_INVALID'); return null; }
        return item;
    }
    app.post('/capture-result', (req, res) => {
        const item = lookup(req, res); if (!item) return;
        if (item.state === 'CAPTURING') return res.status(202).json({ state: 'CAPTURING' });
        if (item.state === 'READY') {
            const result = item.result; item.result = null; item.state = 'USED'; clearTimeout(item.timer);
            return res.json({ fmd_template: result });
        }
        if (item.state === 'FAILED') return error(res, item.code === 'CAPTURE_TIMEOUT' ? 408 : 503, item.code);
        return error(res, 409, 'ACQUISITION_USED');
    });
    app.post('/cancel-capture', (req, res) => {
        const item = lookup(req, res); if (!item) return;
        item.state = 'USED'; item.result = null; item.code = 'CAPTURE_CANCELLED'; clearTimeout(item.timer); item.abort.abort();
        item.releaseTimer = setTimeout(() => { if (active === item) active = null; }, 1500);
        item.releaseTimer.unref?.();
        res.json({ success: true });
    });
    app.post('/match-bulk', async (req, res) => {
        try {
            if (!Array.isArray(req.body?.medicos) || req.body.medicos.length > 10000) return error(res, 422, 'INVALID_FMD');
            const probe = protocol.parseFmd(req.body.fmd1);
            const candidates = req.body.medicos.map(row => {
                if (!Number.isInteger(row.id)) throw new Error('INVALID_FMD');
                return { id: row.id, data: protocol.parseFmd(row.fmd_template) };
            });
            const result = await device.match(probe, candidates);
            res.json({ success: result.success === true, isMatch: result.isMatch === true, match_id: result.match_id });
        } catch (failure) { error(res, 422, failure.code || 'INVALID_FMD'); }
        finally { if (req.body) { req.body.fmd1 = null; req.body.medicos = null; } }
    });
    app.use((_failure, _req, res, _next) => error(res, 400, 'INVALID_REQUEST'));
    return { app, close() { clearInterval(cleanupTimer); for (const item of acquisitions.values()) { clearTimeout(item.timer); clearTimeout(item.releaseTimer); item.abort.abort(); item.result = null; } acquisitions.clear(); challenges.clear(); } };
}
if (require.main === module) {
    const service = createService();
    const server = service.app.listen(Number(process.env.BIOMETRIC_PORT || 8082), '127.0.0.1');
    server.on('error', failure => {
        service.close();
        console.error(failure.code === 'EADDRINUSE' ? 'HES: el puerto local 8082 ya está ocupado. Revise el agente existente.' : 'HES: no se pudo iniciar el servicio local.');
        process.exitCode = 1;
    });
}
module.exports = { createService };
