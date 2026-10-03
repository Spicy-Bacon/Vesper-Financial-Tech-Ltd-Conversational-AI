import {createService} from './service.js';
const $=id=>document.getElementById(id);
const service=createService();
let sessionId, snapshot, busy=false, stopped=false, pending=null, controller, generation=0;
function node(tag,text,cls) {const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
function button(text,run,cls='') {const b=node('button',text,cls);b.type='button';b.addEventListener('click',run);b.disabled=busy||stopped||!!pending;return b;}
function addMessage(role,text) {
  const nearBottom=$('messages').scrollHeight-$('messages').scrollTop-$('messages').clientHeight<100;
  const article=node('article',undefined,'bubble '+role);article.append(node('span',role==='user'?'You':service.mode==='demo'?'Conversation · demo':'Conversation','speaker'),node('p',text));$('messages').append(article);
  if(nearBottom||role==='user') $('messages').scrollTop=$('messages').scrollHeight;
}
function render() {
  $('actions').replaceChildren();$('answers').replaceChildren();
  const locked=busy||stopped||!!pending;
  $('message').disabled=locked||!snapshot?.canMessage;
  $('send').disabled=$('message').disabled||!$('message').value.trim();
  $('stop').disabled=stopped;
  $('status').textContent=stopped?'Conversation stopped. Restart whenever you are ready.':busy?'Preparing a response…':'';
  $('composer').setAttribute('aria-busy',String(busy));
  const answers=snapshot?.confirmedAnswers||[];
  if(!answers.length) $('answers').append(node('p','Your confirmed answers will appear here.','empty'));
  answers.forEach(a=>{const item=node('div',undefined,'answer');item.append(node('span','✓ '+a.label,'answer-label'),node('p',a.answer));$('answers').append(item);});
  $('save-state').textContent=snapshot?.saveStatus==='saved'?'Profile saved · confirmed by the service':snapshot?.saveStatus==='simulated'?'Simulated save · no profile stored':`${answers.length} confirmed · nothing saved yet`;
  if(stopped) return;
  if(snapshot?.type==='proposed_answer') {
    const card=node('section',undefined,'proposal');card.append(node('span','PROPOSED ANSWER · REVIEW BEFORE CONFIRMING','eyebrow'),node('h3',snapshot.proposal.label),node('p',snapshot.proposal.answer));
    if(snapshot.proposal.safety) {const label=node('label',undefined,'safety');const check=node('input');check.type='checkbox';check.id='safety';check.disabled=locked;label.append(check,document.createTextNode('I have checked this answer about essential spending and want to confirm it.'));card.append(label);check.addEventListener('change',()=>{const b=$('confirm-answer');if(b)b.disabled=locked||!check.checked;});}
    $('actions').append(card);
  }
  if(snapshot?.type==='final_playback') {const card=node('section',undefined,'proposal');card.append(node('h3','Your final playback'));answers.forEach(a=>card.append(node('p',a.label+': '+a.answer)));card.append(node('p','Please check every answer before accepting.'));$('actions').append(card);}
  const actions=node('div',undefined,'buttons');
  for(const a of snapshot?.actions||[]) {
    const b=button(a.label,()=>submit(a.id,a.label,{...(a.questionId?{questionId:a.questionId}:{}),...(a.optionId?{optionId:a.optionId}:{}),...(a.id==='confirm'?{explicitConfirmation:!!$('safety')?.checked}:{})}),['confirm','save'].includes(a.id)?'primary':'');
    if(a.id==='confirm'){b.id='confirm-answer';if(snapshot.proposal?.safety)b.disabled=true;}
    actions.append(b);
  }
  $('actions').append(actions);
  $('findings').hidden=!snapshot?.findings?.length;$('finding-content').replaceChildren();
  for(const f of snapshot?.findings||[]){const item=node('section');item.append(node('h3',f.flag),node('blockquote',f.quote),node('p',f.explanation));$('finding-content').append(item);}
}
async function perform(req) {
  if(busy||stopped)return;
  busy=true;pending=req;const epoch=generation;controller=new AbortController();$('error').hidden=true;render();
  try {
    const next=await service.send(req,controller.signal);
    if(epoch!==generation||stopped)return;
    snapshot=next;pending=null;addMessage('assistant',next.assistant.text);
  } catch(e) {
    if(epoch!==generation||stopped)return;
    $('error').replaceChildren(node('p',e.message));
    const retry=node('button','Retry');retry.type='button';retry.onclick=()=>perform(req);$('error').append(retry);$('error').hidden=false;
  } finally {
    if(epoch===generation){busy=false;render();if(!stopped){if(pending)$('error').querySelector('button')?.focus();else if(snapshot?.canMessage)$('message').focus({preventScroll:true});else $('actions').querySelector('input,button')?.focus({preventScroll:true});}}
  }
}
function submit(action,label,extra={}) {
  if(busy||stopped||pending)return;
  const req={sessionId,requestId:crypto.randomUUID(),revision:snapshot?.revision||0,action,...extra};
  if(action==='message')req.message={role:'user',text:label};
  if(label)addMessage('user',label);
  // Hide stale confirmation and acceptance immediately while an edit is pending.
  if(action==='change'&&snapshot)snapshot={...snapshot,confirmedAnswers:snapshot.confirmedAnswers.filter(a=>a.questionId!==extra.questionId),saveStatus:'unsaved',actions:[],proposal:null,type:'message'};
  perform(req);
}
function start() {
  generation++;controller?.abort();sessionId=crypto.randomUUID();snapshot=null;busy=false;stopped=false;pending=null;
  $('messages').replaceChildren();$('error').hidden=true;$('message').value='';render();submit('start');
}
$('mode').textContent=service.mode==='demo'?'● Demo mode':'● Connected service';$('demo-note').hidden=service.mode!=='demo';
$('composer').onsubmit=e=>{e.preventDefault();const text=$('message').value.trim();if(text&&!$('message').disabled&&!busy&&!pending){$('message').value='';$('message').style.height='auto';submit('message',text);}};
$('message').addEventListener('input',()=>{$('send').disabled=busy||stopped||!!pending||!$('message').value.trim();$('message').style.height='auto';$('message').style.height=Math.min($('message').scrollHeight,180)+'px';});
$('message').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('composer').requestSubmit();}});
$('stop').onclick=()=>{const uncertain=pending?.action==='save';stopped=true;controller?.abort();$('error').hidden=true;addMessage('assistant',uncertain?'You stopped while a save was pending. Its outcome is unknown; the service may have completed it.':'You stopped this conversation. No further requests will be sent from this screen.');render();$('restart').focus();};
$('restart').onclick=()=>$('restart-dialog').showModal();$('cancel-restart').onclick=()=>$('restart-dialog').close();$('confirm-restart').onclick=()=>{$('restart-dialog').close();start();};
start();
