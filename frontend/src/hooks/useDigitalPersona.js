import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { createTrustedCapture } from '../utils/trustedCapture';
import { registerBiometricPurge } from '../utils/biometricLifecycle';

// One controller per SPA. The native local service exclusively owns the reader.
const subscribers = new Set();
const controller = createTrustedCapture({ api, onChange: state => subscribers.forEach(listener => listener(state)) });
let deviceMonitorVersion = 0;
let deviceMonitorTimer = null;

const stopDeviceMonitor = () => {
    deviceMonitorVersion += 1;
    if (deviceMonitorTimer) clearTimeout(deviceMonitorTimer);
    deviceMonitorTimer = null;
};

const startDeviceMonitor = () => {
    if (deviceMonitorTimer) return;
    const version = ++deviceMonitorVersion;
    const poll = async () => {
        deviceMonitorTimer = null;
        await controller.refreshDevices();
        if (version === deviceMonitorVersion && subscribers.size) {
            deviceMonitorTimer = setTimeout(poll, 800);
        }
    };
    deviceMonitorTimer = setTimeout(poll, 0);
};

export const purgeBiometrics = () => { void controller.stop(); };
registerBiometricPurge(purgeBiometrics);

export const useDigitalPersona = () => {
    const [state, setState] = useState(controller.snapshot);
    useEffect(() => {
        subscribers.add(setState);
        setState(controller.snapshot());
        startDeviceMonitor();
        return () => {
            subscribers.delete(setState);
            if (!subscribers.size) {
                stopDeviceMonitor();
                void controller.stop();
            }
        };
    }, []);
    const startCapture = useCallback(context => controller.start(context), []);
    const stopCapture = useCallback(() => controller.stop(), []);
    const refreshDevices = useCallback(() => controller.refreshDevices(), []);
    const resetFmd = useCallback(() => { void controller.stop(); }, []);
    return { ...state, isReady: state.devices.length > 0 && !state.isAcquiring, startCapture, stopCapture, refreshDevices, resetFmd, purgeBiometrics };
};
