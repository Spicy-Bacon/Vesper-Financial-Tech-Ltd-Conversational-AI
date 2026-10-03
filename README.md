# The Careful Conversation

A responsive conversation frontend for the Vesper hackathon. The original repository contained only its title: no framework, backend, model service, profiling rules or detector was present. This implementation uses native JavaScript and CSS with npm and no dependencies. Model access belongs to the backend teammate.

## Run

Use Node.js 22 or newer:

```sh
npm run dev
```

Open http://127.0.0.1:5173. No install is needed. `npm run check`, `npm test` and `npm run build` run syntax checks, adapter tests and create a static `dist/` directory. `SERVE_DIST=1 npm run dev` previews the build. The development server serves frontend files only.

## Demo and walkthrough

Default: **Demo mode**, with scripted synthetic answers, no LLM and no real saving. It does not interpret the text you type. Please use fictional circumstances.

1. Type “I can handle some ups and downs”. Review and Confirm the fixed proposal.
2. Type “Maybe in a few years”. The demo asks for clarification. Choose the five-year example, then Confirm.
3. Type a fictional answer about essential spending. Check the additional safety confirmation before Confirm.
4. On final playback, choose Change an answer, then Attitude to risk. Its confirmation is removed immediately. Choose the alternative demo answer, then Confirm again.
5. Review final playback and choose Accept and save. The acknowledgement explicitly says saving was simulated.

You can also choose Change answer or Not sure on a proposal. Stop cancels the browser request and prevents further interaction until Restart. Restart uses a native confirmation dialog; Escape cancels it. Enter sends, Shift+Enter adds a line, and IME composition does not send. Long transcripts scroll independently and do not automatically jump when you are reading earlier messages.

State exists only in memory. Refreshing loses the session. Conversation content is not written to local storage, analytics or console logs. Restart is not deletion of a profile already saved by a real backend. Stopping a browser request cannot undo an operation already accepted by a backend; a pending save is reported as unknown.

## Connect the backend

Edit `src/config.js`: set `mode: 'http'` and the endpoint (default `/api/conversation`). Serve the frontend and API on the same origin or provide an appropriate development reverse proxy. The supplied development server does not proxy requests. There is no automatic fallback from the real service to synthetic answers.

All communication goes through `src/service.js`. See [API.md](API.md) for the proposed JSON contract, action IDs, idempotency requirements and save rules. Keep Ollama calls, model configuration and credentials on the server. This is public browser configuration; no secrets belong here. No streaming is implemented because no streaming contract exists.

The backend owns question wording and options, interpretation, deterministic validation, session state, confirmation invalidation, final playback and persistence. The frontend never calculates a financial classification. Optional findings are rendered only when returned; no detector is implemented and absence of findings is never described as compliance.

## Layout and accessibility

Calm green and neutral layout with user/assistant labels, labelled input, visible keyboard focus, live response/loading/error announcements, native restart dialog and explicit safety checkbox. Desktop has an answer summary beside the conversation; phone uses one column. The app uses system fonts and has no external asset requests.

## Verification

Passed: syntax checks, five Node adapter tests, static build, and automated Chrome checks at 1280px and 390px. The browser checks cover the complete demo, correction, mandatory safety checkbox, simulated save, Enter/Shift+Enter, Escape in the restart dialog, stop, long-message overflow, and HTTP error/retry without duplicated messages or confirmations. Desktop and phone screenshots were visually inspected. Screen-reader testing and Safari/Firefox testing remain manual checks.

To repeat the browser checks, run the development server and a separate Chrome instance with `--headless --remote-debugging-port=9223 --user-data-dir=/tmp/careful-test-chrome about:blank`, then run `node scripts/browser-check.mjs`. The script uses Node's built-in WebSocket and an isolated Chrome debugging page; no browser-test dependencies are installed. It injects synthetic HTTP failures only into that test page. Screenshots are written to `/private/tmp/careful-desktop.png` and `/private/tmp/careful-mobile.png` on macOS. Use an isolated Chrome profile, not your personal browsing session.
