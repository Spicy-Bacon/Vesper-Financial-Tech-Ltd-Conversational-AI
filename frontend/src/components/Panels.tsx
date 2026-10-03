import { useEffect, useRef, useState } from "react";
import type { Adapter, Audit, Snapshot, Answer } from "../api/contracts";
export function ConfirmDialog({
  title,
  children,
  onConfirm,
  onClose,
  label = "Continue",
}: {
  title: string;
  children: React.ReactNode;
  onConfirm: () => void;
  onClose: () => void;
  label?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current!;
    d.showModal();
    return () => d.close();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-labelledby="dialog-title"
    >
      <h2 id="dialog-title">{title}</h2>
      <div>{children}</div>
      <div className="buttons">
        <button autoFocus onClick={onClose}>
          Cancel
        </button>
        <button className="primary" onClick={onConfirm}>
          {label}
        </button>
      </div>
    </dialog>
  );
}
export function AnswerList({
  answers,
  onEdit,
  disabled = false,
}: {
  answers: Answer[];
  onEdit?: (id: string) => void;
  disabled?: boolean;
}) {
  return (
    <>
      {[...answers]
        .sort((a, b) => a.order - b.order)
        .map((a) => (
          <div className="answer" key={a.question_id}>
            <span className="answer-label">
              {a.question_id} · {a.label}
            </span>
            {a.is_unsure && (
              <span className="unresolved">Unsure · unresolved</span>
            )}
            <p>{a.playback}</p>
            {onEdit && (
              <button
                disabled={disabled}
                onClick={() => onEdit(a.question_id)}
                aria-label={`Edit ${a.question_id}: ${a.label}`}
              >
                Edit
              </button>
            )}
          </div>
        ))}
    </>
  );
}
export function ExplanationCard({ snapshot }: { snapshot: Snapshot }) {
  if (!snapshot.explanations.length) return null;
  return (
    <section className="explanation" aria-label="Explanation">
      <h3>
        {snapshot.catalog_status === "approved"
          ? "Reviewed explanation"
          : "Provisional demo explanation"}
      </h3>
      {snapshot.explanations.map((s) => (
        <div key={s.content_id}>
          <p>{s.text}</p>
          <small>
            {s.content_id} · {s.source_sheet}, row {s.source_row}
          </small>
        </div>
      ))}
    </section>
  );
}
function download(value: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function AcceptedProfile({ snapshot }: { snapshot: Snapshot }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const receipt = snapshot.receipt!;
  const exportProfile = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      download(
        receipt,
        `${receipt.simulated ? "simulated-" : "accepted-"}profile.json`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="proposal">
      <p className="eyebrow">
        {receipt.simulated ? "SIMULATED ACCEPTANCE" : "ACCEPTED PROFILE"}
      </p>
      <h3>
        {receipt.simulated
          ? "Demo complete. No real save."
          : "Your answers have been saved."}
      </h3>
      <p>
        Receipt: <span className="identifier">{receipt.profile_id}</span>
      </p>
      <p>
        Accepted {new Date(receipt.accepted_at).toLocaleString("en-GB")} ·{" "}
        {receipt.catalog_version}
      </p>
      <AnswerList answers={receipt.answers} />
      {receipt.score?.status === "scored" && (
        <div>
          <h3>Risk profile: {receipt.score.classification}</h3>
          {(["attitude", "capacity", "horizon", "overall"] as const).map(
            (dimension) => (
              <p key={dimension}>
                {dimension}:{" "}
                {receipt.score!.values[dimension] === undefined
                  ? "Not scored"
                  : `${receipt.score!.values[dimension]} / 100`}
              </p>
            ),
          )}
          <p className="subtle">
            Prototype risk profile based on your confirmed questionnaire
            answers. This is not investment advice.
          </p>
        </div>
      )}
      <button disabled={busy} onClick={exportProfile}>
        {busy
          ? "Preparing export…"
          : receipt.simulated
            ? "Export simulated profile"
            : "Export accepted profile"}
      </button>
      <p className="subtle">
        Includes only the accepted answer records and receipt, not your chat or
        audit.
      </p>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
export function AuditPanel({
  snapshot,
  adapter,
}: {
  snapshot: Snapshot;
  adapter: Adapter;
}) {
  const [open, setOpen] = useState(false),
    [audit, setAudit] = useState<Audit | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [attempt, setAttempt] = useState(0),
    [exporting, setExporting] = useState(false);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setAudit(null);
    adapter
      .audit(snapshot.session_id, controller.signal)
      .then(setAudit)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [open, snapshot.session_id, snapshot.revision, adapter, attempt]);
  return (
    <section className="audit">
      <button
        className="audit-toggle"
        aria-expanded={open}
        aria-controls="audit-content"
        onClick={() => setOpen(!open)}
      >
        Conversation evidence {open ? "−" : "+"}
      </button>
      {open && (
        <div id="audit-content">
          <p className="subtle">
            Temporary evidence from the service. Proposed and confirmed are
            different events. No private reasoning traces are shown.
          </p>
          {loading && <p role="status">Loading evidence…</p>}
          {error && (
            <div role="alert">
              <p>{error}</p>
              <button onClick={() => setAttempt((n) => n + 1)}>
                Retry evidence
              </button>
            </div>
          )}
          {audit && (
            <>
              <ol
                className="events"
                tabIndex={0}
                aria-label="Temporary audit events"
              >
                {audit.events.map((e) => (
                  <li key={e.event_id}>
                    <details>
                      <summary>
                        {e.event_type === "proposed"
                          ? "Proposed"
                          : e.event_type === "confirmed"
                            ? "Confirmed"
                            : e.event_type}{" "}
                        · {e.question_id ?? "Session"}{" "}
                        {e.synthetic ? "· Synthetic" : ""}
                      </summary>
                      <p>
                        {new Date(e.at).toLocaleTimeString("en-GB")} ·{" "}
                        {e.state_before} → {e.state_after}
                      </p>
                      <h4>Raw reply</h4>
                      <p className="raw">
                        {e.raw_reply ?? "No text reply for this event."}
                      </p>
                      <h4>Retrieved content</h4>
                      <p>
                        {e.retrieval_method} · {e.catalog_version}
                      </p>
                      {e.snippets.map((s) => (
                        <blockquote key={s.content_id}>
                          {s.text}
                          <small>
                            {s.content_id} · {s.source_sheet}, row{" "}
                            {s.source_row}
                          </small>
                        </blockquote>
                      ))}
                      <h4>Model proposal and validation</h4>
                      <p>
                        Action: {e.model_action ?? "No model call"} · Option:{" "}
                        {e.option_id ?? "None"}
                      </p>
                      <p>Proposal: {e.proposal_id ?? "None"}</p>
                      <p>{e.validation_result}</p>
                      <small>
                        {e.model_id ?? "No model"} · {e.latency_ms} ms
                      </small>
                    </details>
                  </li>
                ))}
              </ol>
              {!audit.events.length && <p>No evidence events returned.</p>}
              <button onClick={() => setAttempt((n) => n + 1)}>
                Refresh evidence
              </button>{" "}
              <button onClick={() => setExporting(true)}>
                Export this fictional demo audit
              </button>
              <p className="subtle">
                Export is optional and includes messages. Use fictional
                circumstances only.
              </p>
            </>
          )}
        </div>
      )}
      {exporting && audit && (
        <ConfirmDialog
          title="Export the fictional audit?"
          label="Export audit including messages"
          onClose={() => setExporting(false)}
          onConfirm={() => {
            download(audit, "fictional-demo-audit.json");
            setExporting(false);
          }}
        >
          <p>
            This downloads raw replies, retrieved snippets and confirmation
            events to a file on your device. It is separate from the accepted
            profile. Only export fictional data.
          </p>
        </ConfirmDialog>
      )}
    </section>
  );
}
