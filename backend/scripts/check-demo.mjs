// Exercise the running backend using the frontend's actual response validator.
import assert from 'node:assert/strict';
import {validateResponse} from '../../src/service.js';

const origin = process.argv[2] || 'http://127.0.0.1:8765';
const catalogResponse = await fetch(`${origin}/api/catalog`);
assert.equal(catalogResponse.status, 200);
const catalog = await catalogResponse.json();
assert.equal(catalog.demo, true, 'This check must only run against the fictional demo.');
assert.equal(catalog.financeApproved, false);
assert.equal((await fetch(origin)).status, 200);
assert.match(await (await fetch(`${origin}/src/config.js`)).text(), /mode: 'http'/);

const sessionId = crypto.randomUUID();
let revision = 0;
async function send(action, extra = {}) {
  const request = {sessionId, requestId: crypto.randomUUID(), revision, action, ...extra};
  const response = await fetch(`${origin}/api/conversation`, {
    method: 'POST', headers: {'Content-Type': 'application/json', 'Idempotency-Key': request.requestId},
    body: JSON.stringify(request),
  });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const snapshot = validateResponse(await response.json(), request);
  revision = snapshot.revision;
  return snapshot;
}

await send('start');
for (const question of catalog.questions) {
  const option = question.options[0];
  const proposed = await send('message', {message: {role: 'user', text: option.id}});
  assert.equal(proposed.type, 'proposed_answer');
  assert.equal(proposed.proposal.answer, option.answer);
  await send('confirm', {questionId: question.id, optionId: option.id,
    explicitConfirmation: question.requiresExplicitConfirmation});
}
const saved = await send('save');
assert.equal(saved.type, 'saved');
assert.equal(saved.confirmedAnswers.length, catalog.questions.length);
await send('edit');
const changed = await send('change', {questionId: catalog.questions[0].id});
assert.equal(changed.saveStatus, 'unsaved');
assert.equal(changed.confirmedAnswers.length, catalog.questions.length - 1);
console.log('Running demo passed the frontend contract: propose, confirm, save, edit.');
