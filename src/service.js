import {config} from './config.js';
import {createDemo} from './demo.js';
const types=['message','clarification','proposed_answer','final_playback','saved','pause','support'];
const ids=['confirm','change','not_sure','example','replace','save','edit','resume'];
const str=x=>typeof x==='string'&&x.trim().length>0;
const answer=x=>x&&['questionId','optionId','label','answer'].every(k=>str(x[k]));
export function validateResponse(x,req) {
  if(!x||x.sessionId!==req.sessionId||!Number.isInteger(x.revision)||x.revision<=req.revision||!types.includes(x.type)||x.assistant?.role!=='assistant'||!str(x.assistant.text)||typeof x.canMessage!=='boolean'||!Array.isArray(x.actions)||!x.actions.every(a=>a&&ids.includes(a.id)&&str(a.label))||!Array.isArray(x.confirmedAnswers)||!x.confirmedAnswers.every(answer)||new Set(x.confirmedAnswers.map(a=>a.questionId)).size!==x.confirmedAnswers.length||!['unsaved','saved','simulated'].includes(x.saveStatus)) throw new Error('The service returned an invalid response. Retry, or contact your team.');
  if(x.type==='proposed_answer'&&(!answer(x.proposal)||typeof x.proposal.safety!=='boolean'||!x.actions.some(a=>a.id==='confirm'&&a.questionId===x.proposal.questionId&&a.optionId===x.proposal.optionId))) throw new Error('The proposed answer is incomplete. Please retry.');
  if(x.actions.some(a=>a.id==='save')&&x.type!=='final_playback') throw new Error('The service must provide a final playback before saving.');
  if(x.actions.some(a=>a.id==='confirm')&&x.type!=='proposed_answer') throw new Error('A confirmation needs a proposed answer.');
  if(x.actions.some(a=>a.id==='change'&&!str(a.questionId))) throw new Error('The answer to change is missing.');
  if((x.type==='saved')!==(x.saveStatus!=='unsaved')) throw new Error('The save acknowledgement is incomplete. Please retry to check the result.');
  if(x.findings!==undefined&&(!Array.isArray(x.findings)||!x.findings.every(f=>f&&['flag','quote','explanation'].every(k=>str(f[k]))))) throw new Error('The service returned invalid conversation details.');
  return x;
}
export function createService(settings=config, demo=createDemo()) {
  return {mode:settings.mode, async send(req,signal) {
    const controller=new AbortController(); let timedOut=false;
    const abort=()=>controller.abort(); signal?.addEventListener('abort',abort,{once:true});
    if(signal?.aborted) controller.abort();
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},settings.timeoutMs);
    try {
      let result;
      if(settings.mode==='demo') result=await demo(req,controller.signal);
      else {
        const response=await fetch(settings.endpoint,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':req.requestId},body:JSON.stringify(req),signal:controller.signal,cache:'no-store',credentials:'same-origin'});
        if(!response.ok) throw new Error(response.status===409?'This session has changed. Restart to load a fresh conversation.':'The conversation service is unavailable. Please retry in a moment.');
        try {result=await response.json();} catch {throw new Error('The service returned an unreadable response. Please retry.');}
      }
      const valid=validateResponse(result,req);
      if(settings.mode!=='demo'&&valid.saveStatus==='simulated') throw new Error('The live service returned a simulated save. No save is confirmed.');
      return valid;
    } catch(error) {
      if(timedOut) throw new Error('The service took too long. The result is unconfirmed; retry safely to check it.');
      if(error instanceof TypeError) throw new Error('Unable to reach the conversation service. Check your connection and retry.');
      throw error;
    } finally {clearTimeout(timer);signal?.removeEventListener('abort',abort);}
  }};
}
