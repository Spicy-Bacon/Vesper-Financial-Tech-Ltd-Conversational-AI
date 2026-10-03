import { useEffect, useRef, useState } from "react";
import { ServiceError } from "./api/client";
import type { Adapter } from "./api/contracts";
import type { Action, Command, Snapshot } from "./api/contracts";
import { scenarios } from "./api/fixtures";
import {
  AcceptedProfile,
  AnswerList,
  AuditPanel,
  ConfirmDialog,
  ExplanationCard,
} from "./components/Panels";
type Message = { id: string; role: "user" | "assistant"; text: string };
type Operation = { command: Command; syncFirst?: boolean };
export default function App({ adapter }: { adapter: Adapter }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [messages, setMessages] = useState<Message[]>([]),
    [draft, setDraft] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [safety, setSafety] = useState(false),
    [dialog, setDialog] = useState<"end" | "restart" | null>(null),
    [held, setHeld] = useState<"pause" | "end" | null>(null),
    [sessionUnavailable, setSessionUnavailable] = useState(false);
  const restartAfterEnd = useRef(false);
  const pending = useRef<Operation | null>(null),
    lock = useRef(false),
    epoch = useRef(0),
    controller = useRef<AbortController | null>(null),
    input = useRef<HTMLTextAreaElement>(null),
    log = useRef<HTMLDivElement>(null),
    controls = useRef<HTMLDivElement>(null),
    errorControls = useRef<HTMLDivElement>(null),
    follow = useRef(true);
  const append = (role: Message["role"], text: string) =>
    setMessages((m) => [...m, { id: crypto.randomUUID(), role, text }]);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (follow.current && log.current)
      log.current.scrollTop = log.current.scrollHeight;
  }, [messages, busy]);
  useEffect(() => {
    if (busy || error) return;
    setSafety(false);
    if (snapshot?.allowed_actions.includes("message"))
      input.current?.focus({ preventScroll: true });
    else
      controls.current
        ?.querySelector<HTMLElement>("input,button")
        ?.focus({ preventScroll: true });
  }, [snapshot?.revision, busy, error]);
  useEffect(() => {
    if (error && !busy)
      errorControls.current
        ?.querySelector<HTMLButtonElement>("button")
        ?.focus();
  }, [error, busy]);
  const handleError = (failure: unknown) => {
    if (
      failure instanceof ServiceError &&
      ["SESSION_UNAVAILABLE", "CATALOG_CHANGED"].includes(failure.code)
    ) {
      pending.current = null;
      restartAfterEnd.current = false;
      setHeld(null);
      setSessionUnavailable(true);
    }
    setError(
      failure instanceof Error
        ? failure.message
        : "The service could not complete the request.",
    );
  };
  const apply = (next: Snapshot) => {
    if (next.state === "ENDED" && restartAfterEnd.current) {
      restartAfterEnd.current = false;
      reset();
      return;
    }
    restartAfterEnd.current = false;
    setSnapshot(next);
    setSafety(false);
    setHeld(null);
    if (next.state === "ENDED") {
      setMessages([]);
      setDraft("");
    } else append("assistant", next.assistant_message);
  };
  async function execute(op: Operation, interrupt = false) {
    if (lock.current && !interrupt) return;
    controller.current?.abort();
    const current = ++epoch.current;
    const abort = new AbortController();
    controller.current = abort;
    lock.current = true;
    setBusy(true);
    setError("");
    pending.current = op;
    try {
      if (op.syncFirst) {
        const latest = await adapter.load(op.command.session_id!, abort.signal);
        if (current !== epoch.current) return;
        if (latest.state === "SAVED" || latest.state === "ENDED") {
          pending.current = null;
          apply(latest);
          return;
        }
        op.command = { ...op.command, expected_revision: latest.revision };
        op.syncFirst = false;
      }
      const next = await adapter.mutate(op.command, abort.signal);
      if (current !== epoch.current) return;
      pending.current = null;
      apply(next);
    } catch (e) {
      if (current === epoch.current) {
        handleError(e);
      }
    } finally {
      if (current === epoch.current) {
        lock.current = false;
        setBusy(false);
      }
    }
  }
  function act(
    action: Action | "start",
    extra: Partial<Command> = {},
    label?: string,
  ) {
    if (lock.current || pending.current) return;
    if (action !== "start" && !snapshot?.allowed_actions.includes(action))
      return;
    if (label) {
      follow.current = true;
      append("user", label);
    }
    const command: Command = {
      action,
      request_id: crypto.randomUUID(),
      expected_revision: snapshot?.revision ?? 0,
      ...(snapshot ? { session_id: snapshot.session_id } : {}),
      ...extra,
    };
    if (action === "change" && snapshot)
      setSnapshot({
        ...snapshot,
        confirmed_answers: snapshot.confirmed_answers.filter(
          (a) => a.question_id !== extra.question_id,
        ),
        pending_proposal: null,
        review: null,
        review_version: null,
        receipt: null,
        allowed_actions: [],
      });
    void execute({ command });
  }
  function interrupt(action: "pause" | "end") {
    if (!snapshot) return;
    setHeld(action);
    setSafety(false);
    if (action === "end") {
      setMessages([]);
      setDraft("");
    }
    void execute(
      {
        command: {
          action,
          session_id: snapshot.session_id,
          request_id: crypto.randomUUID(),
          expected_revision: snapshot.revision,
        },
        syncFirst: true,
      },
      true,
    );
  }
  async function refresh() {
    if (!snapshot || lock.current) return;
    controller.current?.abort();
    const current = ++epoch.current;
    controller.current = new AbortController();
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await adapter.load(
        snapshot.session_id,
        controller.current.signal,
      );
      if (current !== epoch.current) return;
      pending.current = null;
      apply(next);
    } catch (e) {
      if (current === epoch.current) handleError(e);
    } finally {
      if (current === epoch.current) {
        lock.current = false;
        setBusy(false);
      }
    }
  }
  function reset() {
    controller.current?.abort();
    epoch.current++;
    pending.current = null;
    lock.current = false;
    setSnapshot(null);
    setMessages([]);
    setDraft("");
    setBusy(false);
    setError("");
    setHeld(null);
    setSessionUnavailable(false);
    restartAfterEnd.current = false;
  }
  const locked = busy || !!pending.current || !!held || sessionUnavailable;
  const allowed = (a: Action) => !!snapshot?.allowed_actions.includes(a);
  const active =
    !!snapshot &&
    !sessionUnavailable &&
    !["SAVED", "ENDED"].includes(snapshot.state);
  const canPause = active && snapshot.state !== "PAUSED";
  const proposal = snapshot?.pending_proposal;
  const canMessage = allowed("message") && !locked;
  const submit = () => {
    if (!draft.trim() || !canMessage) return;
    const text = draft.trim();
    setDraft("");
    if (input.current) input.current.style.height = "auto";
    act("message", { text }, text);
  };
  const start = () => act("start");
  return (
    <>
      <a className="skip" href="#conversation-title">
        Skip to conversation
      </a>
      <header>
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            c.
          </span>
          <span>
            VESPER <small>THE CAREFUL CONVERSATION</small>
          </span>
        </div>
        <span className="pill">
          {adapter.mode === "demo" ? "● Scripted demo" : "● Backend mode"}
        </span>
      </header>
      <main>
        <section className="intro">
          <p className="eyebrow">A LITTLE CLARITY, ONE ANSWER AT A TIME</p>
          <h1>
            Let’s talk about what
            <br /> feels right for you.
          </h1>
          <p>
            This demo uses fictional finances. It records your answers about
            risk, the effect of a loss and when you might need your money. It
            does not recommend investments.
          </p>
        </section>
        <div className="layout">
          <section
            className="conversation"
            aria-labelledby="conversation-title"
          >
            <div className="section-head">
              <div>
                <h2 id="conversation-title" tabIndex={-1}>
                  Your conversation
                </h2>
                <span className="subtle">
                  {snapshot
                    ? `${snapshot.confirmed_answers.length} of 6 answers confirmed · Take your time.`
                    : "Six questions, then a review. You’re in control."}
                </span>
              </div>
              <div className="toolbar">
                {snapshot && !error && !sessionUnavailable && (
                  <button disabled={busy} onClick={() => void refresh()}>
                    Refresh session state
                  </button>
                )}
                {canPause && (
                  <button
                    onClick={() => interrupt("pause")}
                    disabled={held === "pause"}
                  >
                    Pause
                  </button>
                )}
                {active && (
                  <button onClick={() => setDialog("end")}>End</button>
                )}
                {snapshot && (
                  <button
                    className="text-button"
                    onClick={() => setDialog("restart")}
                  >
                    Restart
                  </button>
                )}
              </div>
            </div>
            <div className="notice">
              {adapter.mode === "demo"
                ? "SCRIPTED DEMO · Synthetic, provisional fixtures. No model is connected; saving is simulated."
                : "SYNTHETIC DATA ONLY · Use fictional circumstances."}
              {snapshot?.catalog_status === "provisional" &&
              adapter.mode !== "demo"
                ? " The backend catalog is provisional and awaits finance approval."
                : ""}
            </div>
            {!snapshot && !busy && !error && (
              <section className="start-panel">
                <h2>A conversation you can check.</h2>
                <p>
                  Choose a fixed answer or reply in your own words. Every
                  answer, including “Not sure”, needs your confirmation. You can
                  ask for an explanation, change an answer, pause or end.
                </p>
                <p>
                  Draft answers stay in a temporary session until you accept the
                  final profile. Model software may retain caches or logs; the
                  team must verify its retention settings.
                </p>
                <button className="primary" onClick={start}>
                  Start fictional conversation
                </button>
              </section>
            )}
            {snapshot && snapshot.state !== "ENDED" && held !== "end" && (
              <div
                id="messages"
                ref={log}
                role="log"
                aria-label="Conversation"
                aria-live="polite"
                aria-relevant="additions"
                onScroll={() => {
                  const e = log.current!;
                  follow.current =
                    e.scrollHeight - e.scrollTop - e.clientHeight < 100;
                }}
              >
                {messages.map((m) => (
                  <article key={m.id} className={`bubble ${m.role}`}>
                    <span className="speaker">
                      {m.role === "user"
                        ? "You"
                        : adapter.mode === "demo"
                          ? "Conversation · demo"
                          : "Conversation"}
                    </span>
                    <p>{m.text}</p>
                  </article>
                ))}
              </div>
            )}
            <div id="actions" ref={controls} aria-busy={busy}>
              {held && (
                <section className="proposal">
                  <h3>
                    {held === "pause" ? "Pausing…" : "Ending conversation…"}
                  </h3>
                  <p>
                    Waiting for the service to confirm. An operation already
                    received by the backend may have completed.
                  </p>
                </section>
              )}
              {snapshot && !held && !sessionUnavailable && (
                <>
                  <ExplanationCard snapshot={snapshot} />
                  {snapshot.state === "ASKING" && snapshot.active_question && (
                    <section className="question">
                      <p className="eyebrow">
                        {snapshot.active_question.question_id} ·{" "}
                        {snapshot.active_question.label}
                      </p>
                      <h3>{snapshot.active_question.text}</h3>
                      {allowed("select") && (
                        <fieldset disabled={locked}>
                          <legend>Choose a fixed answer</legend>
                          <div className="options">
                            {snapshot.active_question.options.map((o) => (
                              <button
                                key={o.option_id}
                                onClick={() =>
                                  act(
                                    "select",
                                    { option_id: o.option_id },
                                    o.label,
                                  )
                                }
                              >
                                {o.label}
                              </button>
                            ))}
                          </div>
                          <p className="subtle">
                            Choosing an option creates a proposal. It does not
                            confirm it.
                          </p>
                        </fieldset>
                      )}
                    </section>
                  )}
                  {proposal && snapshot.state === "AWAITING_CONFIRMATION" && (
                    <section className="proposal">
                      <p className="eyebrow">PROPOSED · NOT YET CONFIRMED</p>
                      <h3>Here is how I understood your answer</h3>
                      <p>{proposal.playback}</p>
                      {proposal.is_unsure && (
                        <p className="unresolved">
                          Unsure · this answer will remain unresolved in the
                          review.
                        </p>
                      )}
                      {proposal.safety && (
                        <label className="safety">
                          <input
                            type="checkbox"
                            checked={safety}
                            disabled={locked}
                            onChange={(e) => setSafety(e.target.checked)}
                          />
                          I have checked this safety answer and want to confirm
                          exactly what it says.
                        </label>
                      )}
                      <div className="buttons">
                        <button
                          className="primary"
                          disabled={
                            locked ||
                            !allowed("confirm") ||
                            (proposal.safety && !safety)
                          }
                          onClick={() =>
                            act(
                              "confirm",
                              {
                                proposal_id: proposal.proposal_id,
                                explicit_confirmation: safety,
                              },
                              "Confirm answer",
                            )
                          }
                        >
                          Confirm answer
                        </button>
                        <button
                          disabled={locked || !allowed("change")}
                          onClick={() =>
                            act(
                              "change",
                              { question_id: proposal.question_id },
                              "Change answer",
                            )
                          }
                        >
                          Change answer
                        </button>
                      </div>
                    </section>
                  )}
                  {snapshot.state === "REVIEW" && snapshot.review && (
                    <section className="proposal">
                      <p className="eyebrow">Q7 · REVIEW AND ACCEPTANCE</p>
                      <h3>Your answers, in your own hands.</h3>
                      <p>{snapshot.review.help_text}</p>
                      {adapter.mode === "http" &&
                        snapshot.catalog_status !== "approved" && (
                          <p className="notice">
                            Saving is unavailable until the finance team
                            approves this catalog.
                          </p>
                        )}
                      <AnswerList
                        answers={snapshot.review.statements}
                        disabled={locked || !allowed("change")}
                        onEdit={(id) =>
                          act("change", { question_id: id }, `Edit ${id}`)
                        }
                      />
                      <div className="buttons">
                        <button
                          disabled={locked || !allowed("change")}
                          onClick={() =>
                            controls.current
                              ?.querySelector<HTMLButtonElement>(
                                '[aria-label^="Edit Q"]',
                              )
                              ?.focus()
                          }
                        >
                          Change an answer
                        </button>
                        <button
                          className="primary"
                          disabled={
                            locked ||
                            !allowed("finalize") ||
                            (adapter.mode === "http" &&
                              snapshot.catalog_status !== "approved")
                          }
                          onClick={() =>
                            act(
                              "finalize",
                              { review_version: snapshot.review_version! },
                              "Accept and save these answers",
                            )
                          }
                        >
                          Accept and save these answers
                        </button>
                        <button
                          disabled={locked || !allowed("explain_review")}
                          onClick={() =>
                            act(
                              "explain_review",
                              {},
                              "I’m not sure about this review",
                            )
                          }
                        >
                          I’m not sure about this review
                        </button>
                      </div>
                    </section>
                  )}
                  {snapshot.state === "PAUSED" && (
                    <section className="proposal">
                      <p className="eyebrow">PAUSED · NOTHING ACCEPTED</p>
                      <h3>Room to think.</h3>
                      <p>
                        Your confirmed answers remain in this temporary session.
                        Any unconfirmed proposal has been cleared.
                      </p>
                      <button
                        className="primary"
                        disabled={locked || !allowed("resume")}
                        onClick={() => act("resume", {}, "Resume conversation")}
                      >
                        Resume conversation
                      </button>
                    </section>
                  )}
                  {snapshot.state === "ENDED" && (
                    <section className="start-panel">
                      <h3>Conversation ended.</h3>
                      <p>
                        The service confirmed that temporary session data was
                        cleared.
                      </p>
                      <button onClick={reset}>Start a new conversation</button>
                    </section>
                  )}
                  {snapshot.state === "SAVED" && snapshot.receipt && (
                    <AcceptedProfile snapshot={snapshot} />
                  )}
                </>
              )}
            </div>
            <div id="status" role="status">
              {busy ? "Waiting for the service…" : ""}
            </div>
            {error && (
              <div id="error" role="alert">
                <p>{error}</p>
                <div className="buttons" ref={errorControls}>
                  {pending.current && (
                    <button
                      disabled={busy}
                      onClick={() => void execute(pending.current!)}
                    >
                      Retry same request
                    </button>
                  )}
                  {snapshot && !sessionUnavailable && (
                    <button disabled={busy} onClick={() => void refresh()}>
                      Refresh session state
                    </button>
                  )}
                  {(!snapshot || sessionUnavailable) && (
                    <button disabled={busy} onClick={reset}>
                      Return to start
                    </button>
                  )}
                </div>
                <p className="subtle">
                  A failed response does not tell us whether the service applied
                  the request.
                </p>
              </div>
            )}
            {snapshot && active && (
              <form
                id="composer"
                onSubmit={(e) => {
                  e.preventDefault();
                  submit();
                }}
              >
                <label htmlFor="message">Your message</label>
                <div className="input-row">
                  <textarea
                    ref={input}
                    id="message"
                    rows={2}
                    maxLength={8000}
                    value={draft}
                    disabled={!canMessage}
                    aria-describedby="input-help"
                    placeholder="Use fictional circumstances…"
                    onChange={(e) => {
                      setDraft(e.target.value);
                      e.target.style.height = "auto";
                      e.target.style.height =
                        Math.min(e.target.scrollHeight, 180) + "px";
                    }}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        submit();
                      }
                    }}
                  />
                  <button
                    className="primary"
                    type="submit"
                    disabled={!canMessage || !draft.trim()}
                  >
                    Send ↗
                  </button>
                </div>
                <p id="input-help">
                  {canMessage
                    ? "Enter to send · Shift + Enter for a new line"
                    : "Use the controls above to continue, pause or end."}
                </p>
                {adapter.mode === "demo" && allowed("message") && (
                  <details className="demo-scenarios">
                    <summary>Try a scripted demo scenario</summary>
                    <div className="buttons">
                      {Object.entries(scenarios).map(([key, text]) => (
                        <button
                          key={key}
                          type="button"
                          disabled={locked}
                          onClick={() => act("message", { text }, text)}
                        >
                          {key.replaceAll("_", " ")}
                        </button>
                      ))}
                    </div>
                  </details>
                )}
              </form>
            )}
          </section>
          <aside>
            <section className="summary">
              <p className="eyebrow">CONFIRMED SESSION ANSWERS</p>
              <h2>A picture, built together.</h2>
              <p className="subtle">
                Proposals appear in the conversation. Only answers you
                explicitly confirm appear here.
              </p>
              {held === "end" ? (
                <p>Waiting for the session to end.</p>
              ) : snapshot?.confirmed_answers.length ? (
                <AnswerList answers={snapshot.confirmed_answers} />
              ) : (
                <p className="empty">
                  Your confirmed answers will appear here.
                </p>
              )}
              <div className="save-state">
                {snapshot?.receipt
                  ? snapshot.receipt.simulated
                    ? "Simulated acceptance · no real save"
                    : "Saved · receipt received"
                  : "Not saved · final acceptance still required"}
              </div>
            </section>
            <section className="how">
              <h3>You choose the pace.</h3>
              <p>
                “Not sure” is a valid answer to confirm. You can also decline to
                answer and end with an incomplete session.
              </p>
              <p className="privacy">
                This browser keeps the conversation only in memory. Refreshing
                loses access to the session.{" "}
                {snapshot?.retention_notice ??
                  "Backend session expiry and model-server caches or logs must be checked by the team before making broader retention claims."}
              </p>
            </section>
            {snapshot &&
              !["ENDED"].includes(snapshot.state) &&
              !sessionUnavailable &&
              held !== "end" && (
                <AuditPanel snapshot={snapshot} adapter={adapter} />
              )}{" "}
            {!!snapshot?.findings.length && (
              <details>
                <summary>Returned detector findings</summary>
                {snapshot.findings.map((f, i) => (
                  <section key={i}>
                    <h3>{f.flag}</h3>
                    <blockquote>{f.quote}</blockquote>
                    <p>{f.explanation}</p>
                  </section>
                ))}
              </details>
            )}
          </aside>
        </div>
      </main>
      <footer>
        THE CAREFUL CONVERSATION{" "}
        <span>Synthetic data · No investment recommendations</span>
      </footer>
      {dialog && (
        <ConfirmDialog
          title={
            dialog === "end"
              ? "End this conversation?"
              : "Restart this conversation?"
          }
          label={
            dialog === "end"
              ? "End and clear temporary session"
              : active
                ? "End current session"
                : "Return to start"
          }
          onClose={() => setDialog(null)}
          onConfirm={() => {
            setDialog(null);
            if (active) {
              restartAfterEnd.current = dialog === "restart";
              interrupt("end");
            } else reset();
          }}
        >
          <p>
            {active
              ? "This discards the temporary conversation and answers once the service confirms. A save already in progress may still complete."
              : "This clears the screen. Any profile already saved by the service will remain saved."}
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}
