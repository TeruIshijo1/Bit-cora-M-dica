'use strict';
const { spawn } = require('node:child_process');
const path = require('node:path');

class NativeDevice {
    constructor(executable = path.join(__dirname, 'native', 'bin', 'CaptureBridge.exe')) {
        this.executable = executable;
    }
    run(command, { signal, onWaiting, timeoutMs = 10000 } = {}) {
        return new Promise((resolve, reject) => {
            const childEnv = { ...process.env };
            delete childEnv.BIOMETRIC_ATTESTATION_SECRET;
            const child = spawn(this.executable, [], { env: childEnv, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
            let pending = '', result = null, settled = false, failure = null;
            const fail = code => { failure = code; child.kill(); };
            const abort = () => {
                failure = 'CAPTURE_CANCELLED';
                if (child.stdin.writable) child.stdin.write('CANCEL\n');
                cancellation = setTimeout(() => child.kill(), 1000);
            };
            let cancellation;
            const timer = setTimeout(() => fail('CAPTURE_TIMEOUT'), timeoutMs + 2000);
            const finish = (error, value) => {
                if (settled) return;
                settled = true;
                clearTimeout(timer); clearTimeout(cancellation);
                signal?.removeEventListener('abort', abort);
                pending = '';
                if (error) reject(Object.assign(new Error(error), { code: error })); else resolve(value);
            };
            child.on('error', () => finish('SDK_UNAVAILABLE'));
            child.stdin.on('error', () => {});
            // Never forward native stderr or biometric stdout to a logger.
            child.stderr.resume();
            child.stdout.setEncoding('utf8');
            child.stdout.on('data', chunk => {
                pending += chunk;
                if (pending.length > 2000000) return fail('SDK_INVALID_RESPONSE');
                let end;
                while ((end = pending.indexOf('\n')) >= 0) {
                    const line = pending.slice(0, end); pending = pending.slice(end + 1);
                    try {
                        const message = JSON.parse(line);
                        if (message.event_type === 'waiting_for_finger') onWaiting?.(message.device_id);
                        else result = message;
                    } catch { fail('SDK_INVALID_RESPONSE'); }
                }
            });
            child.on('close', code => {
                if (failure) return finish(failure);
                if (code !== 0 || result?.ok !== true) return finish(result?.code || 'SDK_UNAVAILABLE');
                finish(null, result);
                result = null;
            });
            child.stdin.write(JSON.stringify(command) + '\n');
            if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, { once: true });
        });
    }
    probe() { return this.run({ mode: 'probe' }); }
    capture({ timeoutMs, signal, onWaiting }) {
        return this.run({ mode: 'capture', timeout_ms: Math.max(1, Math.floor(timeoutMs)) }, { timeoutMs, signal, onWaiting });
    }
    match(probe, candidates) { return this.run({ mode: 'match', probe, candidates }, { timeoutMs: 10000 }); }
}
module.exports = { NativeDevice };
