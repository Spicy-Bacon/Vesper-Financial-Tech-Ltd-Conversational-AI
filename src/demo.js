const questions = [
  {id:'attitude', label:'Attitude to risk', optionId:'some_fluctuation', answer:'I am comfortable with some ups and downs.'},
  {id:'horizon', label:'Time horizon', optionId:'five_plus', answer:'I do not expect to need this money for at least five years.'},
  {id:'capacity', label:'Capacity for loss', optionId:'essentials_covered', answer:'In this fictional example, a loss would not affect my essential spending.', safety:true}
];
const action = (id,label,extra={}) => ({id,label,...extra});
export function createDemo() {
  let state; const cache = new Map();
  return async function demo(req, signal) {
    await new Promise((resolve,reject)=>{ const timer=setTimeout(resolve,450); signal?.addEventListener('abort',()=>{clearTimeout(timer);reject(new DOMException('Aborted','AbortError'));},{once:true}); });
    if(cache.has(req.requestId)) return structuredClone(cache.get(req.requestId));
    if(req.action==='start') state={sessionId:req.sessionId,revision:0,confirmedAnswers:[],saveStatus:'unsaved', index:0, clarified:false};
    if(!state || state.sessionId!==req.sessionId) throw new Error('This demo session has ended. Start again.');
    let type='message', text='', proposal=null, actions=[];
    const q=questions[state.index];
    const prompt=()=>state.index===0 ? 'Imagine a fictional investment going up and down. How would you feel? Try “I can handle some ups and downs”.' : state.index===1 ? 'When might you need the money? Try an uncertain answer, such as “Maybe in a few years”.' : 'For this fictional example, could you cover essential spending if the investment lost value?';
    if(req.action==='start') text='Welcome to the scripted demo. Please use fictional circumstances. '+prompt();
    else if(req.action==='change') {
      const index=questions.findIndex(x=>x.id===req.questionId);
      if(index<0) throw new Error('Unknown demo question.');
      state.index=index; state.confirmedAnswers=state.confirmedAnswers.filter(x=>x.questionId!==req.questionId); state.saveStatus='unsaved'; state.clarified=true;
      text='The previous confirmation has been removed. Any final acceptance must be given again. Choose the replacement fictional answer below.';
      actions=[action('replace','Use the alternative demo answer',{questionId:req.questionId})];
    } else if(req.action==='not_sure') { type='clarification'; text='That’s okay. Take your time. This demo can show a fixed fictional example when you are ready.'; actions=[action('example','Show fictional example')]; }
    else if(req.action==='confirm') {
      if(!state.proposal || req.questionId!==state.proposal.questionId || req.optionId!==state.proposal.optionId || (state.proposal.safety&&!req.explicitConfirmation)) throw new Error('Review the proposed answer before confirming.');
      state.confirmedAnswers.push({...state.proposal}); state.proposal=null;
      state.index=questions.findIndex(x=>!state.confirmedAnswers.some(a=>a.questionId===x.id));
      if(state.index<0){type='final_playback';text='Please review your fictional answers together. They describe your comfort with ups and downs, your time horizon, and the effect of a loss. No risk classification has been calculated.';actions=[action('save','Accept and save'),action('edit','Change an answer')];}
      else text='That answer is confirmed for this session. '+prompt();
    } else if(req.action==='save') {if(state.confirmedAnswers.length!==3) throw new Error('Confirm all answers first.');type='saved';state.saveStatus='simulated';text='Demo complete. Saving was simulated; no profile has been stored.';}
    else if(req.action==='edit') {text='Choose a confirmed answer to change.';actions=state.confirmedAnswers.map(a=>action('change',a.label,{questionId:a.questionId}));}
    else if(state.index===1&&!state.clarified&&req.action==='message') {state.clarified=true;type='clarification';text='“A few years” could mean different things. For this scripted example, shall we use at least five years?';actions=[action('example','Use five years in this demo')];}
    else {
      if(!q) throw new Error('Please restart to begin a new demo.');
      proposal={questionId:q.id,optionId:q.optionId,label:q.label,answer:q.answer,safety:!!q.safety};
      if(req.action==='replace') {proposal.optionId=q.id+'_alternative';proposal.answer=q.id==='attitude'?'I would prefer fewer ups and downs.':q.id==='horizon'?'I might need this money within three years.':'In this fictional example, a loss could affect essential spending.';}
      type='proposed_answer';text='Here is a fixed fictional answer for the demo. This is scripted and is not an interpretation of your message.';
      actions=[action('confirm','Confirm',{questionId:proposal.questionId,optionId:proposal.optionId}),action('change','Change answer',{questionId:proposal.questionId}),action('not_sure','Not sure')];
    }
    state.proposal=proposal; state.revision++;
    const result={sessionId:state.sessionId,revision:state.revision,assistant:{role:'assistant',text},type,proposal,actions,confirmedAnswers:structuredClone(state.confirmedAnswers),saveStatus:state.saveStatus,canMessage:['message','clarification'].includes(type)&&!['edit','change'].includes(req.action), findings:[]};
    cache.set(req.requestId,result); return structuredClone(result);
  };
}
