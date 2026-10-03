import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createDemo} from '../src/demo.js';
import {createService,validateResponse} from '../src/service.js';
function journey(){const service=createService({mode:'demo',timeoutMs:2000},createDemo());let revision=0;const sessionId=crypto.randomUUID();return async(action,extra={})=>{const req={sessionId,revision,requestId:crypto.randomUUID(),action,...extra};const r=await service.send(req);revision=r.revision;return r;};}
test('clarification, safety confirmation, correction, final playback and simulated save',async()=>{
 const send=journey();await send('start');let r=await send('message',{message:{role:'user',text:'Fictional example'}});assert.equal(r.type,'proposed_answer');
 r=await send('confirm',{questionId:r.proposal.questionId,optionId:r.proposal.optionId});assert.equal(r.confirmedAnswers.length,1);
 r=await send('message',{message:{role:'user',text:'Maybe'}});assert.equal(r.type,'clarification');r=await send('example');r=await send('confirm',{questionId:r.proposal.questionId,optionId:r.proposal.optionId});
 r=await send('message',{message:{role:'user',text:'Fictional essentials'}});assert.equal(r.proposal.safety,true);
 await assert.rejects(send('confirm',{questionId:r.proposal.questionId,optionId:r.proposal.optionId}),/Review/);
 r=await send('confirm',{questionId:r.proposal.questionId,optionId:r.proposal.optionId,explicitConfirmation:true});assert.equal(r.type,'final_playback');
 r=await send('edit');r=await send('change',{questionId:'attitude'});assert.equal(r.confirmedAnswers.length,2);assert.equal(r.saveStatus,'unsaved');
 r=await send('replace');assert.equal(r.proposal.optionId,'attitude_alternative');r=await send('confirm',{questionId:r.proposal.questionId,optionId:r.proposal.optionId});assert.equal(r.type,'final_playback');r=await send('save');assert.equal(r.saveStatus,'simulated');
 r=await send('change',{questionId:'attitude'});assert.equal(r.saveStatus,'unsaved');assert.equal(r.confirmedAnswers.length,2);
});
test('duplicate requests return the same result without adding a confirmation',async()=>{const service=createService({mode:'demo',timeoutMs:2000});const req={sessionId:'test',revision:0,requestId:'start',action:'start'};await service.send(req);const p=await service.send({...req,revision:1,requestId:'message',action:'message'});const confirm={...req,revision:2,requestId:'confirm',action:'confirm',questionId:p.proposal.questionId,optionId:p.proposal.optionId};const first=await service.send(confirm);assert.deepEqual(await service.send(confirm),first);assert.equal(first.confirmedAnswers.length,1);});
test('invalid responses and premature saves are rejected',()=>{assert.throws(()=>validateResponse({},{}),/invalid/);const base={sessionId:'s',revision:1,type:'message',assistant:{role:'assistant',text:'Hello'},canMessage:true,actions:[],confirmedAnswers:[],saveStatus:'unsaved'};assert.throws(()=>validateResponse({...base,actions:[{id:'save',label:'Save'}]},{sessionId:'s',revision:0}),/playback/);assert.throws(()=>validateResponse({...base,type:'saved'},{sessionId:'s',revision:0}),/acknowledgement/);});
test('timeouts give retry guidance',async()=>{const service=createService({mode:'demo',timeoutMs:1});await assert.rejects(service.send({sessionId:'s',revision:0,requestId:'r',action:'start'}),/too long/);});
test('live transport handles unavailable services and malformed JSON',async()=>{const original=globalThis.fetch;const req={sessionId:'s',revision:0,requestId:'r',action:'start'};try{const service=createService({mode:'http',endpoint:'/api/conversation',timeoutMs:100});globalThis.fetch=async()=>{throw new TypeError('offline')};await assert.rejects(service.send(req),/Unable to reach/);globalThis.fetch=async()=>({ok:true,json:async()=>{throw new SyntaxError()}});await assert.rejects(service.send(req),/unreadable/);}finally{globalThis.fetch=original;}});
