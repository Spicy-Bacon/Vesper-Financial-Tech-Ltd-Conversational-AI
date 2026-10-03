# Proposed conversation API (v1)

No backend existed in the inspected repository. Agree this contract with the backend owner before connecting. POST one JSON request to `/api/conversation`, returning a complete JSON snapshot. No streaming.

## Requests

```json
{
  "sessionId": "client-generated-uuid",
  "requestId": "client-generated-uuid",
  "revision": 2,
  "action": "confirm",
  "questionId": "attitude",
  "optionId": "some_fluctuation",
  "explicitConfirmation": false
}
```

The first request uses `action: "start"`, revision 0. The server creates a session bound to that identifier. A message request uses `action: "message"` and `message: {"role": "user", "text": "fictional example"}`. No text or identifiers in query strings. Send `Cache-Control: no-store` in API responses.

Other supported actions: `confirm`, `change`, `not_sure`, `example`, `replace`, `save`, `edit`, `resume`. Only advertise actions that the current state allows. `example` and `replace` support the scripted demo; a real backend need not offer them. `change` requires questionId; `confirm` requires questionId and optionId. Safety confirmations additionally require explicitConfirmation true. `edit` opens the backend-provided answer selection. Return `change` actions for the answers the user can revise. Stop is local: it aborts the browser fetch and disables input. Backend request processing may still finish; implement cancellation separately if required.

Every request carries `Idempotency-Key: requestId`. Retries reuse the exact body and key. **The backend must deduplicate atomically**, including confirmation and save side effects, and return the original response for the same key even if the session revision has advanced. Check deduplication before revision conflicts. For new requests, reject stale revisions with 409. Client safeguards alone cannot guarantee exactly-once persistence after timeouts.

## Responses

```json
{
  "sessionId": "client-generated-uuid",
  "revision": 3,
  "assistant": {"role": "assistant", "text": "Please review this proposed answer."},
  "type": "proposed_answer",
  "canMessage": false,
  "proposal": {
    "questionId": "attitude",
    "optionId": "some_fluctuation",
    "label": "Attitude to risk",
    "answer": "I am comfortable with some ups and downs.",
    "safety": false
  },
  "actions": [
    {"id": "confirm", "label": "Confirm", "questionId": "attitude", "optionId": "some_fluctuation"},
    {"id": "change", "label": "Change answer", "questionId": "attitude"},
    {"id": "not_sure", "label": "Not sure"}
  ],
  "confirmedAnswers": [],
  "saveStatus": "unsaved",
  "findings": []
}
```

`revision` is an integer greater than the request revision. Response types: `message`, `clarification`, `proposed_answer`, `final_playback`, `saved`, `pause`, `support`. All render assistant text as plain text, never HTML. `canMessage` controls free text availability. Pause/support may supply a `resume` action. Confirmed answers have questionId, optionId, label and answer; proposal additionally requires boolean safety. Return the full current confirmed-answer list on every response. Do not include proposed answers in that list.

A `final_playback` returns the complete confirmed list, plain-English assistant text, and `save` / `edit` actions. The frontend shows the complete list again for review. `save` must apply to exactly that revision. After durable persistence succeeds, return type `saved`, saveStatus `saved`, and normally no actions/canMessage false. `simulated` is accepted only in demo mode. Never acknowledge a save before the transaction succeeds.

Changing an answer must remove its confirmation and invalidate prior final acceptance on the server. Return saveStatus `unsaved`; do not silently alter an already saved historical profile. A later save is a new acceptance/version according to the backend's storage design. The frontend removes the edited confirmation immediately while waiting and blocks other actions if the request fails, allowing retry or restart.

Optional `findings`: an array of `{ "flag": "name", "quote": "exact evidence", "explanation": "plain English explanation" }`. The UI shows these in a collapsed details panel. The backend owns all analysis. Omit or return [] if unavailable.

## Failures and privacy

Non-2xx responses show a generic availability error (409 gives session-conflict guidance). Invalid JSON/schema is rejected. Timeout is 20 seconds by default. Input/actions lock synchronously during requests, and retries do not append the user message again. Do not place private server errors or financial content in logs. Apply backend input validation, deterministic safety rules, session expiry and appropriate access controls before production. Authentication and infrastructure are outside this hackathon frontend scope.
