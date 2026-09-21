'use strict';
const crypto = require('node:crypto');
const http = require('node:http');
const test = require('node:test');
const assert = require('node:assert/strict');
const { createService } = require('../server');
const protocol = require('../capture-protocol');
const secret = 'synthetic-biometric-attestation-secret-32chars';
const fmd = Buffer.concat([Buffer.from('FMR\0'), Buffer.alloc(64, 65)]).toString('base64');
const deviceId = 'a'.repeat(64);
function ticket(now, overrides = {}, candidates = []) {
    const context = { protocol_version: 2, challenge_id: crypto.randomBytes(32).toString('base64url'), session_id: 'test-session',
        action: 'LOGIN', patient_ref: null, document_code: null, document_ref: null, subject_ref: null, expected_identity_ref: null,
        issued_at: new Date(now - 10).toISOString(), expires_at: new Date(now + 119990).toISOString(), match_required: false, ...overrides };
    const key = crypto.createHmac('sha256', secret).update('HES-MATCH-KEY-V2').digest();
    const nonce = crypto.randomBytes(12), cipher = crypto.createCipheriv('aes-256-gcm', key, nonce);
    cipher.setAAD(Buffer.from(context.challenge_id));
    const ciphertext = Buffer.concat([cipher.update(JSON.stringify(candidates)), cipher.final()]);
    context.match_job = Buffer.concat([nonce, ciphertext, cipher.getAuthTag()]).toString('base64url');
    const data = Buffer.from(JSON.stringify(context)).toString('base64url');
    return data + '.' + protocol.sign(secret, 'HES-CAPTURE-REQUEST-V2\n' + data);
}
async function harness(run, captureImpl) {
    let time = Date.now(), captures = 0;
    const device = {
        async probe() { return { device_id: deviceId }; },
        async capture(args) {
            captures++;
            args.onWaiting(deviceId);
            if (captureImpl) return captureImpl(args, () => time);
            return { data: fmd, device_id: deviceId, capture_started_at: new Date(time).toISOString(), captured_at: new Date(time).toISOString() };
        },
        async match(probe, candidates) { const row = candidates.find(c => c.data === probe); return { success: true, isMatch: Boolean(row), match_id: row?.id || null }; }
    };
    const service = createService({ secret, device, now: () => time });
    const server = service.app.listen(0, '127.0.0.1');
    await new Promise(resolve => server.once('listening', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    const post = async (path, body) => {
        const response = await fetch(base + path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
        return { status: response.status, body: await response.json() };
    };
    const get = async path => {
        const response = await fetch(base + path);
        return { status: response.status, body: await response.json() };
    };
    async function begin(authorization = ticket(time), extras = {}) { const response = await post('/begin-capture', { authorization, ...extras }); return { ...response, authorization, acquisition_id: response.body.acquisition_id }; }
    const result = acquisition => post('/capture-result', { authorization: acquisition.authorization, acquisition_id: acquisition.acquisition_id });
    try { await run({ post, get, begin, result, now: () => time, advance: ms => { time += ms; }, count: () => captures, device }); }
    finally { service.close(); await new Promise(resolve => server.close(resolve)); }
}
for (const field of ['raw', 'fmd_template', 'data', 'captured_at', 'acquisition_id']) {
    test(`AF02 rejects caller-controlled ${field} before activating device`, async () => harness(async h => {
        const response = await h.begin(undefined, { [field]: 'archived-client-material' });
        assert.equal(response.status, 422); assert.equal(h.count(), 0);
    }));
}
test('AF02 retired RAW API never attests and browser cannot issue acquisitions', async () => harness(async h => {
    for (const path of ['/extract-fmd', '/acquisitions/start']) {
        const response = await h.post(path, { raw: 'archive', challenge_id: 'new', session_id: 'valid' });
        assert.equal(response.status, 410); assert.equal(response.body.fmd_template, undefined);
    }
    assert.equal(h.count(), 0);
}));
test('AF02 challenge -> native interface event -> valid attestation with encrypted matching', async () => harness(async h => {
    const ref = { id: 7, identity: 'medico:7', data: fmd, template_hash: 'b'.repeat(64) };
    const authorization = ticket(h.now(), { match_required: true }, [ref]);
    const a = await h.begin(authorization); assert.equal(a.status, 201);
    const result = await h.result(a); assert.equal(result.status, 200);
    const envelope = JSON.parse(result.body.fmd_template);
    assert.equal(envelope.protocol_version, 2); assert.equal(envelope.matched_identity, 'medico:7');
    assert.equal(envelope.matched_template_hash, ref.template_hash);
    assert.equal(envelope.fmd_hash, protocol.hash(Buffer.from(fmd, 'base64')));
    assert.ok(protocol.equal(envelope.attestation, protocol.sign(secret, 'HES-CAPTURE-ATTESTATION-V2\n' + protocol.message(envelope))));
    assert.equal(envelope.raw, undefined); assert.equal(h.count(), 1);
}));
test('AF02 simultaneous retrieval and challenge reuse have one winner', async () => harness(async h => {
    const authorization = ticket(h.now());
    const starts = await Promise.all([h.begin(authorization), h.begin(authorization)]);
    assert.deepEqual(starts.map(r => r.status).sort(), [201, 409]);
    const acquired = starts.find(r => r.status === 201);
    const outcomes = await Promise.all([h.result(acquired), h.result(acquired)]);
    assert.deepEqual(outcomes.map(r => r.status).sort(), [200, 409]); assert.equal(h.count(), 1);
}));
for (const field of ['challenge_id', 'session_id', 'action', 'patient_ref', 'document_code']) {
    test(`AF02 refuses forged ${field} authorization`, async () => harness(async h => {
        const auth = ticket(h.now()).split('.'); const context = JSON.parse(Buffer.from(auth[0], 'base64url'));
        context[field] = 'changed'; auth[0] = Buffer.from(JSON.stringify(context)).toString('base64url');
        const result = await h.begin(auth.join('.')); assert.equal(result.status, 401); assert.equal(h.count(), 0);
    }));
}
test('AF02 acquisition cannot predate signed challenge', async () => harness(async h => {
    const response = await h.begin(ticket(h.now(), { issued_at: new Date(h.now() + 1000).toISOString() }));
    assert.equal(response.status, 401); assert.equal(h.count(), 0);
}));
test('AF02 a different session cannot retrieve a capture', async () => harness(async h => {
    const a = await h.begin(); a.authorization = ticket(h.now(), { session_id: 'other' });
    assert.equal((await h.result(a)).status, 409);
}));
test('AF02 TTL invalidates even a previously ready capture', async () => harness(async h => {
    const a = await h.begin(); h.advance(120001);
    assert.equal((await h.result(a)).status, 409);
}));
for (const code of ['READER_DISCONNECTED', 'CAPTURE_TIMEOUT', 'SDK_UNAVAILABLE', 'FMD_EXTRACTION_FAILED']) {
    test(`AF02 ${code} issues no attestation`, async () => harness(async h => {
        const a = await h.begin(); const result = await h.result(a);
        assert.ok([408, 503].includes(result.status)); assert.equal(result.body.code, code); assert.equal(result.body.fmd_template, undefined);
    }, async () => { throw Object.assign(new Error(code), { code }); }));
}
test('AF02 changing device and stale SDK samples fail closed', async () => harness(async h => {
    const a = await h.begin(); const r = await h.result(a); assert.equal(r.status, 503); assert.equal(r.body.code, 'READER_CHANGED');
}, async (_args, now) => ({ data: fmd, device_id: 'b'.repeat(64), capture_started_at: new Date(now()).toISOString(), captured_at: new Date(now()).toISOString() })));
test('AF02 capture after TTL is never attested', async () => harness(async h => {
    const a = await h.begin(); const r = await h.result(a); assert.notEqual(r.status, 200); assert.equal(r.body.fmd_template, undefined);
}, async (_args, now) => ({ data: fmd, device_id: deviceId, capture_started_at: new Date(now()).toISOString(), captured_at: new Date(now() + 120000).toISOString() })));
test('AF02 cancellation cleans result and cancels physical operation', async () => harness(async h => {
    const a = await h.begin(); await h.post('/cancel-capture', { acquisition_id: a.acquisition_id, authorization: a.authorization });
    const result = await h.result(a); assert.notEqual(result.status, 200); assert.equal(result.body.fmd_template, undefined);
}, args => new Promise((_resolve, reject) => args.signal.addEventListener('abort', () => reject(Object.assign(new Error('cancel'), { code: 'CAPTURE_CANCELLED' })), { once: true }))));
test('an expired native capture cannot leave its workstation permanently busy', async () => harness(async h => {
    const acquisition = await h.begin(); assert.equal(acquisition.status, 201);
    h.advance(120001);
    const devices = await h.get('/devices');
    assert.equal(devices.status, 200);
    assert.equal(devices.body.busy, false);
    assert.deepEqual(devices.body.devices, [deviceId]);
}, () => new Promise(() => {})));
test('AF02 stale sample from the same SDK device is rejected', async () => harness(async h => {
    const a = await h.begin(); const result = await h.result(a);
    assert.equal(result.status, 408); assert.equal(result.body.fmd_template, undefined);
}, async (_args, now) => ({ data: fmd, device_id: deviceId, capture_started_at: new Date(now() - 60000).toISOString(), captured_at: new Date(now() - 59000).toISOString() })));

test('multiple tabs share one device probe; foreign origins cannot reach the SDK', async () => {
    let probes = 0, requests = 0, release;
    const pending = new Promise(resolve => { release = () => resolve({device_id: deviceId}); });
    const service = createService({secret, device: {probe: () => {probes++; return pending;}}});
    const server = http.createServer((req,res) => {
        service.app(req,res);
        if (++requests === 20) setImmediate(release);
    }).listen(0,'127.0.0.1');
    await new Promise(resolve => server.once('listening',resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    try {
        const responses = await Promise.all(Array.from({length:20},()=>fetch(base+'/devices')));
        assert.ok(responses.every(response => response.status === 200));
        assert.equal(probes,1);
        const denied = await fetch(base+'/devices',{headers:{Origin:'https://untrusted.example'}});
        assert.equal(denied.status,403);assert.equal(probes,1);
        const rebinding = await new Promise((resolve,reject)=>{
            http.get(base+'/devices',{headers:{Host:'untrusted.example'}},response=>{response.resume();response.on('end',()=>resolve(response.statusCode));}).on('error',reject);
        });
        assert.equal(rebinding,403);assert.equal(probes,1);
    } finally { service.close(); await new Promise(resolve => server.close(resolve)); }
});

test('capture waits for an in-flight probe to release the physical reader',async()=>{
    let releaseProbe, probeStarted, captureStarted=false;
    const ready=new Promise(resolve=>{probeStarted=resolve;});
    const service=createService({secret,device:{
        probe:()=>{probeStarted();return new Promise(resolve=>{releaseProbe=()=>resolve({device_id:deviceId});});},
        capture:async()=>{captureStarted=true;throw Object.assign(Error('test'),{code:'READER_DISCONNECTED'});}
    }});
    const server=service.app.listen(0,'127.0.0.1');
    await new Promise(resolve=>server.once('listening',resolve));
    const base=`http://127.0.0.1:${server.address().port}`;
    try {
        const probe=fetch(base+'/devices');await ready;
        const begin=await fetch(base+'/begin-capture',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({authorization:ticket(Date.now())})});
        assert.equal(begin.status,201);assert.equal(captureStarted,false);
        releaseProbe();await probe;await new Promise(resolve=>setImmediate(resolve));
        assert.equal(captureStarted,true);
    } finally { service.close(); await new Promise(resolve=>server.close(resolve)); }
});
