'use strict';
// Test-only process adapter. Not imported by the service entry point.
const {createService}=require('../server');
(async()=>{
 let input=''; for await(const chunk of process.stdin) input+=chunk;
 const command=JSON.parse(input); input='';
 const device={async capture({onWaiting}){const id='a'.repeat(64);onWaiting(id);return {device_id:id,data:command.data,capture_started_at:new Date().toISOString(),captured_at:new Date().toISOString()};},async match(probe,candidates){const c=candidates.find(c=>c.data===probe);return {success:true,isMatch:!!c,match_id:c?.id};}};
 const service=createService({device});const server=service.app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 const post=async(path,body)=>{const r=await fetch(`http://127.0.0.1:${server.address().port}${path}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});return {status:r.status,data:await r.json()};};
 try{const a=await post('/begin-capture',{authorization:command.authorization});if(a.status!==201)throw Error('BEGIN_FAILED');let r;do{r=await post('/capture-result',{authorization:command.authorization,acquisition_id:a.data.acquisition_id});}while(r.status===202);if(r.status!==200)throw Error('CAPTURE_FAILED');process.stdout.write(r.data.fmd_template);}finally{service.close();await new Promise(r=>server.close(r));}
})().catch(()=>{process.stderr.write('TEST_CAPTURE_FAILED');process.exitCode=1;});
