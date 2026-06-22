import { useState, useEffect, useCallback } from 'react';
import { FingerprintReader, SampleFormat } from '@digitalpersona/devices';

export const useDigitalPersona = () => {
    const [reader, setReader] = useState(null);
    const [status, setStatus] = useState('Desconectado');
    const [devices, setDevices] = useState([]);
    const [isAcquiring, setIsAcquiring] = useState(false);
    
    // El template extraído de la huella en Base64
    const [fmdTemplate, setFmdTemplate] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fpReader = new FingerprintReader();
        setReader(fpReader);

        const onDeviceConnected = (event) => {
            console.log("Device connected", event);
            setStatus('Lector Conectado');
            if (event.deviceUid) {
                setDevices(prev => {
                    if (!prev.includes(event.deviceUid)) return [...prev, event.deviceUid];
                    return prev;
                });
            }
        };

        const onDeviceDisconnected = (event) => {
            console.log("Device disconnected", event);
            setStatus('Lector Desconectado');
            if (event.deviceUid) {
                setDevices(prev => prev.filter(uid => uid !== event.deviceUid));
            }
        };

        const onSamplesAcquired = (event) => {
            console.log("Muestra adquirida", event);
            try {
                let sample = event.samples[0];
                if (sample) {
                    let rawData = sample.Data || sample.data || sample;
                    let format = sample.Format || sample.format || sample;
                    
                    if (typeof rawData === 'string' && rawData.startsWith('eyJ')) {
                        try {
                            const decodedStr = atob(rawData);
                            const parsed = JSON.parse(decodedStr);
                            if (parsed.Data) {
                                rawData = parsed.Data;
                            }
                            if (parsed.Format) {
                                format = parsed.Format;
                            }
                        } catch (e) {
                            console.warn("Failed to parse inner JSON", e);
                        }
                    }
                    
                    const cleanBase64 = typeof rawData === 'string' ? rawData.replace(/-/g, '+').replace(/_/g, '/') : rawData;
                    
                    const metadata = {
                        width: format.iWidth || format.width || 0,
                        height: format.iHeight || format.height || 0,
                        resolution: format.iXdpi || format.resolution || 500
                    };
                    
                    const fmdObj = {
                        base64: cleanBase64,
                        metadata: metadata
                    };
                    
                    setFmdTemplate(JSON.stringify(fmdObj));
                    setStatus('Huella Capturada');
                    setIsAcquiring(false);
                    // Stop acquisition after a successful read if we want to be fully manual
                    fpReader.stopAcquisition().catch(e => console.log("Ignored stop error", e));
                }
            } catch (err) {
                console.error("Error al procesar huella:", err);
                setError("Error procesando huella");
                setIsAcquiring(false);
            }
        };

        fpReader.on("DeviceConnected", onDeviceConnected);
        fpReader.on("DeviceDisconnected", onDeviceDisconnected);
        fpReader.on("SamplesAcquired", onSamplesAcquired);

        let isMounted = true;

        const init = async () => {
            try {
                const devs = await fpReader.enumerateDevices();
                if (!isMounted) return;
                setDevices(devs || []);
                if (devs && devs.length > 0) {
                    setStatus('Lector detectado, presione Capturar');
                } else {
                    setStatus('Sin lector conectado');
                }
            } catch (err) {
                if (!isMounted) return;
                const errorMsg = err instanceof Error ? err.message : (err.Message || JSON.stringify(err));
                console.error("Error inicializando WebSDK", err);
                setError(`Error del lector: ${errorMsg}`);
                setStatus('Error WebSDK');
                setDevices([]);
            }
        };

        init();

        return () => {
            isMounted = false;
            fpReader.off("DeviceConnected", onDeviceConnected);
            fpReader.off("DeviceDisconnected", onDeviceDisconnected);
            fpReader.off("SamplesAcquired", onSamplesAcquired);
            fpReader.stopAcquisition().catch(e => console.error("Error deteniendo", e));
        };
    }, []);

    const startCapture = async () => {
        if (!reader) return;
        try {
            setError(null);
            setFmdTemplate(null);
            setStatus('Esperando huella...');
            setIsAcquiring(true);
            await reader.startAcquisition(SampleFormat.Raw);
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : (err.Message || JSON.stringify(err));
            if (errorMsg.toLowerCase().includes('already') || errorMsg.includes('0x80040001')) {
                setStatus('Lector ya está activo...');
            } else {
                setError(`Error al iniciar captura: ${errorMsg}`);
                setIsAcquiring(false);
            }
        }
    };

    const resetFmd = useCallback(() => {
        setFmdTemplate(null);
        setStatus(devices.length > 0 ? 'Lector detectado, presione Capturar' : 'Sin lector conectado');
        setIsAcquiring(false);
    }, [devices]);

    return { status, fmdTemplate, error, devices, resetFmd, startCapture, isAcquiring };
};
