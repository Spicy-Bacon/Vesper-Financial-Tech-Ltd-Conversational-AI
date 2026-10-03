import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const tabs=await (await fetch('http://127.0.0.1:9223/json')).json();
const ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const queue=new Map();ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=queue.get(m.id);queue.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);}});
const cdp=(method,params={})=>new Promise((resolve,reject)=>{const key=++id;queue.set(key,{resolve,reject});ws.send(JSON.stringify({id:key,method,params}));});
const js=async expression=>{const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
const wait=async expression=>{for(let i=0;i<100;i++){if(await js(expression))return;await new Promise(r=>setTimeout(r,100));}throw Error('Timeout: '+expression+' PAGE: '+await js('document.body.innerText'));};
const click=async text=>{await wait(`Array.from(document.querySelectorAll('button')).some(b=>b.textContent.trim()===${JSON.stringify(text)}&&!b.disabled)`);await js(`Array.from(document.querySelectorAll('button')).find(b=>b.textContent.trim()===${JSON.stringify(text)}&&!b.disabled).click()`);await wait(`!document.querySelector('#composer').matches('[aria-busy="true"]')`);};
const say=async text=>{await js(`document.querySelector('#message').value=${JSON.stringify(text)};document.querySelector('#message').dispatchEvent(new Event('input'));document.querySelector('#message').focus()`);await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await new Promise(r=>setTimeout(r,650));await wait(`!document.querySelector('#composer').matches('[aria-busy="true"]')`);};
await cdp('Page.enable');await cdp('Page.bringToFront');await cdp('Emulation.setFocusEmulationEnabled',{enabled:true});await cdp('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});await cdp('Page.navigate',{url:'http://127.0.0.1:5173'});await new Promise(r=>setTimeout(r,1200));await wait(`document.querySelector('#message')&&!document.querySelector('#message').disabled`);
assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
await say('Fictional ups and downs');await click('Confirm');await say('Maybe in a few years');assert.match(await js('document.querySelector("#messages").textContent'),/different things/);await click('Use five years in this demo');await click('Confirm');await say('Fictional essential spending');assert.equal(await js('document.querySelector("#confirm-answer").disabled'),true);await js('document.querySelector("#safety").click()');await click('Confirm');await click('Change an answer');await click('Attitude to risk');assert.equal(await js('document.querySelectorAll(".answer").length'),2);await click('Use the alternative demo answer');await click('Confirm');assert.match(await js('document.querySelector("#actions").textContent'),/final playback/);
await writeFile('/private/tmp/careful-desktop.png',Buffer.from((await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
await click('Accept and save');assert.match(await js('document.querySelector("#save-state").textContent'),/Simulated/);
await click('Restart');assert.equal(await js('document.querySelector("dialog").open'),true);await cdp('Page.bringToFront');await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await wait('!document.querySelector("dialog").open');
await click('Restart');await click('Start again');await wait('!document.querySelector("#message").disabled');await cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
await js('document.querySelector("#message").focus()');await cdp('Input.insertText',{text:'Fictional line one'});await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,modifiers:8});assert.equal(await js('document.querySelectorAll(".user").length'),0);
await js('document.querySelector("#message").value=""');await say('Long fictional message '.repeat(150));assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
await writeFile('/private/tmp/careful-mobile.png',Buffer.from((await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
await click('Stop');assert.equal(await js('document.querySelector("#message").disabled'),true);console.log('PASS browser journey, correction, save, safety, Enter, Shift+Enter, Escape, stop, desktop/mobile overflow');

// Exercise the actual HTTP adapter against synthetic responses inside this test page.
ws.addEventListener('message',async e=>{const m=JSON.parse(e.data);if(m.method==='Fetch.requestPaused')await cdp('Fetch.fulfillRequest',{requestId:m.params.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'text/javascript'}],body:Buffer.from("export const config={mode:'http',endpoint:'/api/conversation',timeoutMs:1000}").toString('base64')});});
await cdp('Fetch.enable',{patterns:[{urlPattern:'*/src/config.js'}]});
await cdp('Page.addScriptToEvaluateOnNewDocument',{source:`
window.testRequests=[];
window.fetch=async (url,options)=>{
 const req=JSON.parse(options.body);window.testRequests.push(req);
 if(req.action==='message'&&window.testRequests.filter(x=>x.action==='message').length===1)throw new TypeError('Synthetic offline');
 if(req.action==='confirm'&&window.testRequests.filter(x=>x.action==='confirm').length===1)throw new TypeError('Synthetic lost confirmation response');
 const proposal={questionId:'fictional',optionId:'fictional-option',label:'Fictional question',answer:'Fictional answer',safety:false};
 const data={sessionId:req.sessionId,revision:req.revision+1,assistant:{role:'assistant',text:'Synthetic test response'},type:req.action==='message'?'proposed_answer':'message',canMessage:req.action!=='message',proposal:req.action==='message'?proposal:null,actions:req.action==='message'?[{id:'confirm',label:'Confirm',questionId:proposal.questionId,optionId:proposal.optionId}]:[],confirmedAnswers:req.action==='confirm'?[proposal]:[],saveStatus:'unsaved'};
 return {ok:true,json:async()=>data};
};`});
await cdp('Page.navigate',{url:'http://127.0.0.1:5173'});await new Promise(r=>setTimeout(r,1200));await wait('!document.querySelector("#message").disabled');
await say('Synthetic retry test');await wait('!document.querySelector("#error").hidden');assert.equal(await js('document.querySelectorAll(".user").length'),1);await click('Retry');assert.equal(await js('document.querySelectorAll(".user").length'),1);
await click('Confirm');await wait('!document.querySelector("#error").hidden');await click('Retry');assert.equal(await js('document.querySelectorAll(".user").length'),2);assert.equal(await js('document.querySelectorAll(".answer").length'),1);
assert.equal(await js('testRequests[1].requestId===testRequests[2].requestId&&testRequests[3].requestId===testRequests[4].requestId'),true);
console.log('PASS HTTP errors, message retry, confirmation retry, unchanged request IDs, no duplicated messages or answers');
await cdp('Fetch.disable');ws.close();
