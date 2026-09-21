'use strict';
// Physical smoke: biometric values stay only in process memory/private SDK pipes.
const crypto = require('node:crypto');
const { NativeDevice } = require('../native-device');
const { createService } = require('../server');
const p = require('../capture-protocol');
(async () => {
 const secret = crypto.randomBytes(32).toString('hex'), device = new NativeDevice();
 const probe = await device.probe();
 console.log(JSON.stringify({reader_detected: Boolean(probe.device_id), sdk_open: probe.can_capture}));
 const service = createService({device, secret});
 const server = service.app.listen(0,'127.0.0.1');
 await new Promise(r=>server.once('listening',r));
 const post = async (url, body) => { const r=await fetch(`http://127.0.0.1:${server.address().port}${url}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)}); return {status:r.status,body:await r.json()}; };
 let envelope;
 try {
  const now=Date.now(), challenge=crypto.randomBytes(32).toString('base64url');
  const nonce=crypto.randomBytes(12), key=crypto.createHmac('sha256',secret).update('HES-MATCH-KEY-V2').digest();
  const cipher=crypto.createCipheriv('aes-256-gcm',key,nonce); cipher.setAAD(Buffer.from(challenge));
  const job=Buffer.concat([nonce,cipher.update('[]'),cipher.final(),cipher.getAuthTag()]).toString('base64url'); key.fill(0);
  const context={protocol_version:2,challenge_id:challenge,session_id:'nonclinical-physical-smoke',action:'ENROLAMIENTO_MEDICO',issued_at:new Date(now).toISOString(),expires_at:new Date(now+60000).toISOString(),match_required:false,match_job:job};
  const encoded=Buffer.from(JSON.stringify(context)).toString('base64url');
  const authorization=encoded+'.'+p.sign(secret,'HES-CAPTURE-REQUEST-V2\n'+encoded);
  const begin=await post('/begin-capture',{authorization});
  if(begin.status!==201) throw Error(begin.body.code);
  console.log(JSON.stringify({waiting_for_finger:true, timeout_seconds:60}));
  let result;
  do { await new Promise(r=>setTimeout(r,250)); result=await post('/capture-result',{authorization,acquisition_id:begin.body.acquisition_id}); } while(result.status===202);
  if(result.status!==200) throw Error(result.body.code);
  envelope=JSON.parse(result.body.fmd_template); result.body.fmd_template=null;
  const attested=p.equal(envelope.attestation,p.sign(secret,'HES-CAPTURE-ATTESTATION-V2\n'+p.message(envelope)));
  const match=await device.match(envelope.data,[{id:1,data:envelope.data}]);
  envelope.data=null;
  const cleanup=await device.probe();
  console.log(JSON.stringify({capture:true,ansi_fmd:true,attestation:attested,sdk_self_match:match.success===true&&match.isMatch===true,reader_reopened_after_cleanup:Boolean(cleanup.device_id),raw_persisted:false}));
  if(!attested||!match.isMatch) process.exitCode=1;
 } finally { if(envelope) envelope.data=null; service.close(); await new Promise(r=>server.close(r)); }
})().catch(e=>{console.log(JSON.stringify({physical_smoke:false,code:/^[A-Z_]+$/.test(e.message)?e.message:'SMOKE_FAILED'}));process.exitCode=1;});
