'use strict';
const crypto = require('node:crypto');
const PROTOCOL = 2;
const FORMAT = 'ANSI_378_2004';
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
function sign(secret, text) { return crypto.createHmac('sha256', secret).update(text, 'utf8').digest('hex'); }
function equal(a, b) {
    return typeof a === 'string' && /^[a-f0-9]{64}$/.test(a) && typeof b === 'string'
        && crypto.timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex'));
}
function authorize(ticket, secret, now) {
    if (typeof ticket !== 'string' || ticket.length > 2000000) throw new Error('INVALID_CHALLENGE');
    const parts = ticket.split('.');
    if (parts.length !== 2 || !equal(parts[1], sign(secret, 'HES-CAPTURE-REQUEST-V2\n' + parts[0]))) throw new Error('INVALID_CHALLENGE');
    let context;
    try { context = JSON.parse(Buffer.from(parts[0], 'base64url').toString('utf8')); } catch { throw new Error('INVALID_CHALLENGE'); }
    const issued = Date.parse(context.issued_at), expires = Date.parse(context.expires_at);
    if (context.protocol_version !== PROTOCOL || !context.challenge_id || !context.session_id || !context.action
        || !Number.isFinite(issued) || !Number.isFinite(expires) || issued > now || expires <= now || expires - issued > 120001) throw new Error('EXPIRED_CHALLENGE');
    return context;
}
function message(p) {
    return JSON.stringify([p.protocol_version, p.format, p.version, p.fmd_hash, p.challenge_id,
        p.session_id, p.acquisition_id, p.acquisition_started_at, p.capture_started_at,
        p.captured_at, p.device_id, p.authorization, p.match_success, p.matched_identity, p.matched_template_hash]);
}
function parseFmd(value) {
    let p;
    try { p = typeof value === 'string' ? JSON.parse(value) : value; } catch { throw new Error('INVALID_FMD'); }
    if (!p || p.format !== FORMAT || p.version !== 1 || typeof p.data !== 'string' || p.data.length > 256000) throw new Error('INVALID_FMD');
    const bytes = Buffer.from(p.data, 'base64');
    const valid = bytes.length >= 16 && bytes.subarray(0, 4).equals(Buffer.from('FMR\0')) && bytes.toString('base64') === p.data;
    bytes.fill(0);
    if (!valid) throw new Error('INVALID_FMD');
    return p.data;
}
function matchJob(context, secret) {
    const bytes = Buffer.from(context.match_job, 'base64url');
    const key = crypto.createHmac('sha256', secret).update('HES-MATCH-KEY-V2').digest();
    let plain;
    try {
        const decipher = crypto.createDecipheriv('aes-256-gcm', key, bytes.subarray(0, 12));
        decipher.setAAD(Buffer.from(context.challenge_id));
        decipher.setAuthTag(bytes.subarray(-16));
        plain = Buffer.concat([decipher.update(bytes.subarray(12, -16)), decipher.final()]);
        return JSON.parse(plain.toString('utf8'));
    } finally { key.fill(0); bytes.fill(0); plain?.fill(0); }
}
module.exports = { matchJob, PROTOCOL, FORMAT, hash, sign, equal, authorize, message, parseFmd };
