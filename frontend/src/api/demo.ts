import {
  snapshotSchema,
  type Adapter,
  type Snapshot,
  type Command,
  type Audit,
  type Answer,
  type Profile,
} from "./contracts";
import { questions, scenarios } from "./fixtures";
const copy = <T>(x: T): T => structuredClone(x);
const version = "synthetic-provisional-v2";
const reviewHelp =
  "These are the answers you explicitly confirmed. Unsure answers remain unresolved. This profile is not an assessment of investment suitability. Accept only if the statements reflect your fictional answers.";
export function createDemo(delayMs = 350): Adapter {
  let state: Snapshot | null = null;
  let events: Audit["events"] = [];
  let profiles = new Map<string, Profile>();
  const requests = new Map<string, { body: string; result: Snapshot }>();
  const delay = async (signal?: AbortSignal) => {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    await new Promise<void>((resolve, reject) => {
      const abort = () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = setTimeout(() => {
        signal?.removeEventListener("abort", abort);
        resolve();
      }, delayMs);
      signal?.addEventListener("abort", abort, { once: true });
    });
  };
  const current = (id: string) => {
    if (!state || state.session_id !== id)
      throw Error("The demo session has ended. Start again.");
    return state;
  };
  const prepareReview = () => {
    state!.state = "REVIEW";
    state!.active_question = null;
    state!.pending_proposal = null;
    state!.review_version = crypto.randomUUID();
    state!.review = {
      statements: copy(state!.confirmed_answers),
      help_text: reviewHelp,
    };
    state!.assistant_message =
      "Review all six fictional answers below. Nothing is saved until you accept this version.";
    state!.response_type = "review";
    state!.allowed_actions = [
      "change",
      "finalize",
      "explain_review",
      "pause",
      "end",
    ];
  };
  const ask = (questionId?: string) => {
    const q = questions.find((q) =>
      questionId
        ? q.question_id === questionId
        : !state!.confirmed_answers.some(
            (a) => a.question_id === q.question_id,
          ),
    );
    if (!q) {
      prepareReview();
      return;
    }
    state!.state = "ASKING";
    state!.active_question = copy(q);
    state!.pending_proposal = null;
    state!.review = null;
    state!.review_version = null;
    state!.assistant_message = q.text;
    state!.response_type = "message";
    state!.allowed_actions = ["message", "select", "pause", "end"];
  };
  return {
    mode: "demo",
    async mutate(c, signal) {
      await delay(signal);
      const previous = requests.get(c.request_id);
      if (previous) {
        if (previous.body !== JSON.stringify(c))
          throw Error("Conflicting request ID.");
        return copy(previous.result);
      }
      const before = state?.state ?? "NEW";
      let kind: Audit["events"][number]["event_type"] = "message";
      let proposalId: string | null = null,
        optionId: string | null = null;
      if (c.action === "start") {
        requests.clear();
        events = [];
        profiles = new Map();
        state = {
          session_id: crypto.randomUUID(),
          revision: 0,
          catalog_version: version,
          catalog_status: "provisional",
          state: "ASKING",
          active_question: null,
          pending_proposal: null,
          confirmed_answers: [],
          assistant_message: "Welcome",
          response_type: "message",
          allowed_actions: [],
          review_version: null,
          review: null,
          receipt: null,
          explanations: [],
          findings: [],
        };
        ask();
        kind = "started";
      } else {
        current(c.session_id!);
        if (c.expected_revision !== state!.revision)
          throw Error(
            "The session changed. Refresh its state before continuing.",
          );
        if (!state!.allowed_actions.includes(c.action))
          throw Error("That action is not available in this state.");
        state!.explanations = [];
        if (c.action === "message" || c.action === "explain_review") {
          if (c.action === "explain_review") {
            state!.assistant_message = reviewHelp;
            state!.response_type = "explanation";
          } else if (c.text === scenarios.refusal) {
            state!.assistant_message =
              "You do not have to answer. You can pause or end here; the profile will remain incomplete.";
            state!.response_type = "support";
            state!.allowed_actions = ["pause", "end"];
          } else if (c.text === scenarios.support) {
            state!.assistant_message =
              "We can pause or stop here. Would you prefer that? This is a scripted support example, not a diagnosis.";
            state!.response_type = "support";
          } else if (c.text === scenarios.out_of_scope) {
            state!.assistant_message =
              "This demo records answers and does not recommend investments. You can continue with a fictional answer or pause.";
            state!.response_type = "out_of_scope";
          } else if (c.text === scenarios.explanation) {
            state!.assistant_message =
              "Here is provisional help supplied by the demo fixture.";
            state!.response_type = "explanation";
            state!.explanations = [
              {
                content_id: "demo-help-" + state!.active_question!.question_id,
                text:
                  state!.active_question!.question_id === "Q4"
                    ? "The example distinguishes money separate from this investment and accessible within a few days. Choose an option only if both details fit your fictional circumstances."
                    : "Read each fictional option and its playback. You can choose Not sure and review that answer before confirming.",
                source_sheet: "Synthetic UI fixture (not reviewed workbook)",
                source_row: state!.active_question!.order,
              },
            ];
          } else {
            state!.assistant_message =
              c.text === scenarios.fallback
                ? "Scripted model-offline example. You can still choose a fixed option below; it will need confirmation."
                : "This demo does not interpret free text. Please clarify by choosing a provisional fixed option below. A short or conditional reply is not treated as a confirmed answer.";
            state!.response_type =
              c.text === scenarios.fallback ? "fallback" : "clarification";
          }
        } else if (c.action === "select") {
          const q = state!.active_question!,
            o = q.options.find((o) => o.option_id === c.option_id);
          if (!o)
            throw Error("That option does not belong to the current question.");
          proposalId = crypto.randomUUID();
          optionId = o.option_id;
          state!.pending_proposal = {
            proposal_id: proposalId,
            question_id: q.question_id,
            option_id: o.option_id,
            playback: o.playback,
            is_unsure: o.is_unsure,
            origin: "button",
            safety: q.safety,
          };
          state!.state = "AWAITING_CONFIRMATION";
          state!.assistant_message =
            "Here is the exact provisional playback for your selection. Please confirm it or change your answer.";
          state!.response_type = "proposal";
          state!.allowed_actions = ["confirm", "change", "pause", "end"];
          kind = "proposed";
        } else if (c.action === "confirm") {
          const p = state!.pending_proposal,
            q = state!.active_question!;
          if (
            !p ||
            p.proposal_id !== c.proposal_id ||
            (p.safety && !c.explicit_confirmation)
          )
            throw Error("Review and explicitly confirm the current proposal.");
          proposalId = p.proposal_id;
          optionId = p.option_id;
          const a: Answer = {
            question_id: q.question_id,
            option_id: p.option_id,
            label: q.label,
            playback: p.playback,
            is_unsure: p.is_unsure,
            order: q.order,
          };
          state!.confirmed_answers.push(a);
          state!.confirmed_answers.sort((a, b) => a.order - b.order);
          kind = "confirmed";
          ask();
        } else if (c.action === "change") {
          if (!questions.some((q) => q.question_id === c.question_id))
            throw Error("Unknown question.");
          state!.confirmed_answers = state!.confirmed_answers.filter(
            (a) => a.question_id !== c.question_id,
          );
          state!.receipt = null;
          ask(c.question_id);
          kind = "corrected";
        } else if (c.action === "pause") {
          state!.state = "PAUSED";
          state!.pending_proposal = null;
          state!.review = null;
          state!.review_version = null;
          state!.allowed_actions = ["resume", "end"];
          state!.assistant_message =
            "Take your time. Confirmed answers remain in this temporary session. Resume will ask the current question again.";
          state!.response_type = "paused";
          kind = "paused";
        } else if (c.action === "resume") {
          ask(state!.active_question?.question_id);
          kind = "resumed";
        } else if (c.action === "finalize") {
          if (
            state!.state !== "REVIEW" ||
            state!.confirmed_answers.length !== 6 ||
            !c.review_version ||
            c.review_version !== state!.review_version ||
            state!.pending_proposal
          )
            throw Error("Only the current complete review can be accepted.");
          const receipt: Profile = {
            profile_id: crypto.randomUUID(),
            session_id: state!.session_id,
            catalog_version: version,
            review_version: c.review_version,
            accepted_at: new Date().toISOString(),
            simulated: true,
            answers: copy(state!.confirmed_answers),
          };
          profiles.set(receipt.profile_id, receipt);
          state!.receipt = receipt;
          state!.state = "SAVED";
          state!.allowed_actions = [];
          state!.response_type = "saved";
          state!.assistant_message =
            "Simulated acceptance complete. No profile was saved to a database. You can export the fictional example explicitly below.";
          kind = "accepted";
        } else if (c.action === "end") {
          state!.state = "ENDED";
          state!.pending_proposal = null;
          state!.active_question = null;
          state!.confirmed_answers = [];
          state!.review = null;
          state!.review_version = null;
          state!.receipt = null;
          state!.allowed_actions = [];
          state!.assistant_message =
            "Conversation ended. Temporary demo data has been cleared.";
          state!.response_type = "ended";
          events = [];
          requests.clear();
          profiles.clear();
        }
      }
      state!.revision++;
      if (c.action !== "end")
        events.push({
          event_id: crypto.randomUUID(),
          at: new Date().toISOString(),
          question_id:
            c.question_id ??
            (kind === "confirmed"
              ? (state!.confirmed_answers.find((a) => a.option_id === optionId)
                  ?.question_id ?? null)
              : (state!.active_question?.question_id ?? null)),
          event_type: kind,
          raw_reply: c.text ?? null,
          catalog_version: version,
          retrieval_method: state!.explanations.length
            ? "synthetic fixture lookup"
            : "none (no model call)",
          snippets: copy(state!.explanations),
          model_action: null,
          proposal_id: proposalId,
          option_id: optionId,
          validation_result:
            "Demo adapter accepted this explicit UI event; not evidence of live model validation.",
          state_before: before,
          state_after: state!.state,
          latency_ms: delayMs,
          model_id: null,
          synthetic: true,
        });
      const result = snapshotSchema.parse(state);
      requests.set(c.request_id, {
        body: JSON.stringify(c),
        result: copy(result),
      });
      return copy(result);
    },
    async load(id, signal) {
      await delay(signal);
      return copy(current(id));
    },
    async audit(id, signal) {
      await delay(signal);
      current(id);
      return { session_id: id, events: copy(events) };
    },
    async profile(id, sessionId, signal) {
      await delay(signal);
      current(sessionId);
      const p = profiles.get(id);
      if (!p) throw Error("Profile unavailable.");
      return copy(p);
    },
  };
}
