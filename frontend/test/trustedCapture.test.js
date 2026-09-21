import test from 'node:test';
import assert from 'node:assert/strict';
import { createTrustedCapture } from '../src/utils/trustedCapture.js';
import { shouldOmitAuthorization } from '../src/utils/authRequest.js';
const reply = (status,data) => ({status,ok:status<400,json:async()=>data});
function harness(overrides={}) {
 let session, challenges=0;const calls=[];
 const api={post:async(_path,body)=>{challenges++; session=body.session_id;return {data:{challenge_id:'challenge',capture_authorization:'signed-ticket'}};}};
 const fetchImpl=async(url,options)=>{
  const body=options.body?JSON.parse(options.body):null;calls.push({url,body,options});
  if(url.endsWith('/begin-capture'))return reply(201,{acquisition_id:'acquisition'});
  if(url.endsWith('/capture-result'))return reply(200,{fmd_template:JSON.stringify({protocol_version:2,challenge_id:'challenge',session_id:session,data:'synthetic-fmd'})});
  return reply(200,{success:true,devices:['reader']});
 };
 return {controller:createTrustedCapture({api,fetchImpl,...overrides}),calls,count:()=>challenges};
}
test('trusted capture sends only signed authorization and purges after stop',async()=>{
 const h=harness();assert.equal(await h.controller.start({action:'LOGIN'}),true);
 assert.deepEqual(h.calls[0].body,{authorization:'signed-ticket'});
 assert.equal(h.calls[0].options.targetAddressSpace,'loopback');
 assert.ok(h.controller.snapshot().fmdTemplate);await h.controller.stop();
 assert.equal(h.controller.snapshot().fmdTemplate,null);assert.equal(h.controller.snapshot().challengeId,null);
});
test('simultaneous SPA starts request only one challenge',async()=>{
 const h=harness();const results=await Promise.all([h.controller.start({action:'LOGIN'}),h.controller.start({action:'LOGIN'})]);
 assert.deepEqual(results,[false,true]);assert.equal(h.count(),1);
});
test('challenge failure never activates the local reader',async()=>{
 const h=harness({api:{post:async()=>{throw Error('challenge failed');}}});
 assert.equal(await h.controller.start({action:'LOGIN'}),false);assert.equal(h.calls.length,0);
 assert.equal(await h.controller.refreshDevices(),true);
 assert.equal(h.controller.snapshot().error,'challenge failed');
 assert.equal(h.controller.snapshot().errorKind,'capture');
});
test('cancel during begin cancels late acquisition and suppresses its result',async()=>{
 let release, arrived;const ready=new Promise(r=>{arrived=r;});let canceled=0;
 const h=harness({fetchImpl:async(url)=>{
  if(url.endsWith('/begin-capture')){arrived();return new Promise(r=>{release=()=>r(reply(201,{acquisition_id:'late'}));});}
  if(url.endsWith('/cancel-capture')){canceled++;return reply(200,{success:true});}
  throw Error('Canceled acquisition must not be polled');
 }});
 const pending=h.controller.start({action:'LOGIN'});await ready;await h.controller.stop();release();
 assert.equal(await pending,false);assert.equal(canceled,1);assert.equal(h.controller.snapshot().fmdTemplate,null);
});
test('local timeout clears biometrics and permits retry',async()=>{
 let attempts=0;
 const h=harness({fetchImpl:async(url)=>{
  if(url.endsWith('/begin-capture')){attempts++;return reply(201,{acquisition_id:'acq'});}
  if(url.endsWith('/capture-result'))return reply(408,{error:'Tiempo agotado'});
  return reply(200,{success:true});
 }});
 assert.equal(await h.controller.start({action:'LOGIN'}),false);
 assert.equal(h.controller.snapshot().error,'Tiempo agotado');assert.equal(h.controller.snapshot().sessionId,null);
 await h.controller.start({action:'LOGIN'});assert.equal(attempts,2);
});
test('concurrent subscribers share one physical device probe',async()=>{
 let probes=0, release;
 const h=harness({fetchImpl:async()=>{probes++;return new Promise(r=>{release=()=>r(reply(200,{devices:['reader']}));});}});
 const first=h.controller.refreshDevices(), second=h.controller.refreshDevices();
 assert.equal(probes,1);release();assert.deepEqual(await Promise.all([first,second]),[true,true]);
 assert.deepEqual(h.controller.snapshot().devices,['reader']);
});
test('mount cleanup cannot discard an in-flight reader inventory',async()=>{
 let release;
 const h=harness({fetchImpl:async()=>new Promise(r=>{release=()=>r(reply(200,{devices:['reader']}));})});
 const pending=h.controller.refreshDevices();await h.controller.stop();release();await pending;
 assert.deepEqual(h.controller.snapshot().devices,['reader']);assert.equal(h.controller.snapshot().fmdTemplate,null);
});
test('a transient initial reader failure can be retried',async()=>{
 let probes=0;
 const h=harness({fetchImpl:async()=>{
  probes++;if(probes===1)throw Error('agent still starting');
  return reply(200,{devices:['reader']});
 }});
 assert.equal(await h.controller.refreshDevices(),false);
 assert.equal(h.controller.snapshot().devices.length,0);
 assert.match(h.controller.snapshot().error,/permita a Bitácora/);
 assert.equal(await h.controller.refreshDevices(),true);
 assert.deepEqual(h.controller.snapshot().devices,['reader']);
});
test('device polling is suppressed during physical acquisition',async()=>{
 let releaseBegin;
 const h=harness({fetchImpl:async(url)=>{
  if(url.endsWith('/begin-capture'))return new Promise(resolve=>{releaseBegin=()=>resolve(reply(201,{acquisition_id:'acquisition'}));});
  if(url.endsWith('/cancel-capture'))return reply(200,{success:true});
  throw Error('device probe must not run while acquisition is active');
 }});
 const capture=h.controller.start({action:'LOGIN'});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(await h.controller.refreshDevices(),true);
 releaseBegin();
 await capture;
});
test('a reader busy in another page is not exposed as ready',async()=>{
 const h=harness({fetchImpl:async()=>reply(200,{devices:['reader'],busy:true})});
 assert.equal(await h.controller.refreshDevices(),true);
 assert.deepEqual(h.controller.snapshot().devices,['reader']);
 assert.equal(h.controller.snapshot().status,'Lector en uso en este equipo');
 assert.match(h.controller.snapshot().error,/en este equipo/);
});
test('public login calls never inherit a stale authorization token',()=>{
 assert.equal(shouldOmitAuthorization({url:'/biometrics/challenge',data:{action:'LOGIN'}}),true);
 assert.equal(shouldOmitAuthorization({url:'/auth/login/biometric'}),true);
 assert.equal(shouldOmitAuthorization({url:'/auth/login/admin'}),true);
 assert.equal(shouldOmitAuthorization({url:'/biometrics/challenge',data:{action:'FIRMA_MEDICA'}}),false);
 assert.equal(shouldOmitAuthorization({url:'/biometrics/challenge',data:JSON.stringify({action:'LOGIN'})}),true);
});

test('insecure intranet origin fails visibly before challenge or local request',async()=>{
 const h=harness({isSecureContext:()=>false});
 assert.equal(await h.controller.start({action:'LOGIN'}),false);
 assert.equal(h.count(),0);assert.equal(h.calls.length,0);
 assert.match(h.controller.snapshot().error,/HTTPS/);
 assert.equal(h.controller.snapshot().isAcquiring,false);
});

test('a stalled agent request times out and releases acquisition state',async()=>{
 const h=harness({requestTimeoutMs:10,fetchImpl:async(_url,options)=>new Promise((_resolve,reject)=>{
  options.signal.addEventListener('abort',()=>reject(Error('aborted')),{once:true});
 })});
 assert.equal(await h.controller.start({action:'LOGIN'}),false);
 assert.match(h.controller.snapshot().error,/no respondió a tiempo/);
 assert.equal(h.controller.snapshot().isAcquiring,false);
});
