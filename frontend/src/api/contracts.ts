import { z } from "zod";
const text = z.string().min(1);
export const actions = [
  "message",
  "select",
  "confirm",
  "change",
  "pause",
  "end",
  "resume",
  "finalize",
  "explain_review",
] as const;
export const optionSchema = z.object({
  option_id: text,
  label: text,
  playback: text,
  is_unsure: z.boolean(),
});
export const questionSchema = z.object({
  question_id: text,
  text,
  label: text,
  order: z.number().int().min(1).max(6),
  safety: z.boolean(),
  options: z.array(optionSchema).min(1),
});
export const answerSchema = z.object({
  question_id: text,
  option_id: text,
  label: text,
  playback: text,
  is_unsure: z.boolean(),
  order: z.number().int().min(1).max(6),
});
const snippetSchema = z.object({
  content_id: text,
  text,
  source_sheet: text,
  source_row: z.number().int().positive(),
});
export const profileSchema = z.object({
  profile_id: text,
  session_id: text,
  catalog_version: text,
  review_version: text,
  accepted_at: text,
  simulated: z.boolean(),
  answers: z.array(answerSchema).length(6),
  score: z
    .object({
      status: z.enum(["not_configured", "scored"]),
      policyVersion: text.nullable(),
      catalogVersion: text,
      values: z.record(
        text,
        z.union([z.number().finite(), z.string().regex(/^\d+(\.\d+)?$/)]),
      ),
      classification: z
        .enum(["Low", "Medium", "High", "Not assigned"])
        .nullable(),
      limitingDimensions: z.array(z.enum(["attitude", "capacity", "horizon"])),
      unresolvedDimensions: z.array(
        z.enum(["attitude", "capacity", "horizon"]),
      ),
    })
    .nullable()
    .optional(),
});
export const snapshotSchema = z
  .object({
    session_id: text,
    revision: z.number().int().nonnegative(),
    catalog_version: text,
    catalog_status: z.enum(["provisional", "approved"]),
    state: z.enum([
      "ASKING",
      "AWAITING_CONFIRMATION",
      "REVIEW",
      "PAUSED",
      "ENDED",
      "SAVED",
    ]),
    active_question: questionSchema.nullable(),
    pending_proposal: z
      .object({
        proposal_id: text,
        question_id: text,
        option_id: text,
        playback: text,
        is_unsure: z.boolean(),
        origin: z.enum(["model", "button", "demo"]),
        safety: z.boolean(),
      })
      .nullable(),
    confirmed_answers: z.array(answerSchema).max(6),
    assistant_message: text,
    response_type: z.enum([
      "message",
      "clarification",
      "explanation",
      "proposal",
      "support",
      "out_of_scope",
      "fallback",
      "review",
      "paused",
      "ended",
      "saved",
    ]),
    allowed_actions: z.array(z.enum(actions)),
    review_version: text.nullable(),
    review: z
      .object({ statements: z.array(answerSchema).length(6), help_text: text })
      .nullable(),
    receipt: profileSchema.nullable(),
    explanations: z.array(snippetSchema).default([]),
    retention_notice: text.optional(),
    findings: z
      .array(z.object({ flag: text, quote: text, explanation: text }))
      .default([]),
  })
  .superRefine((s, c) => {
    const invalid = (message: string) =>
      c.addIssue({ code: "custom", message });
    const ids = s.confirmed_answers.map((a) => a.question_id);
    if (new Set(ids).size !== ids.length)
      invalid("Duplicate confirmed answers");
    if (
      s.state === "AWAITING_CONFIRMATION" &&
      (!s.pending_proposal || !s.active_question)
    )
      invalid("Missing proposal/question");
    if (s.pending_proposal) {
      const p = s.pending_proposal,
        q = s.active_question;
      const o = q?.options.find((o) => o.option_id === p.option_id);
      if (
        s.state !== "AWAITING_CONFIRMATION" ||
        !q ||
        q.question_id !== p.question_id ||
        !o ||
        o.playback !== p.playback ||
        o.is_unsure !== p.is_unsure ||
        q.safety !== p.safety
      )
        invalid("Proposal does not match catalog");
    }
    if (s.state === "REVIEW") {
      if (
        s.confirmed_answers.length !== 6 ||
        !s.review_version ||
        !s.review ||
        s.pending_proposal
      )
        invalid("Incomplete review");
      for (const a of s.review?.statements ?? []) {
        const confirmed = s.confirmed_answers.find(
          (x) => x.question_id === a.question_id,
        );
        if (JSON.stringify(confirmed) !== JSON.stringify(a))
          invalid("Review differs from confirmed answers");
      }
      if (new Set(s.review?.statements.map((a) => a.question_id)).size !== 6)
        invalid("Duplicate review answers");
    }
    if ((s.state === "SAVED") !== !!s.receipt)
      invalid("Missing or premature receipt");
    if (
      s.receipt &&
      (s.receipt.session_id !== s.session_id ||
        s.receipt.catalog_version !== s.catalog_version ||
        s.receipt.review_version !== s.review_version ||
        JSON.stringify(s.receipt.answers) !==
          JSON.stringify(s.confirmed_answers))
    )
      invalid("Receipt differs from confirmed profile");
    if (s.allowed_actions.includes("finalize") && s.state !== "REVIEW")
      invalid("Premature save action");
    if (
      s.allowed_actions.includes("confirm") &&
      s.state !== "AWAITING_CONFIRMATION"
    )
      invalid("Premature confirmation");
    if (
      s.state === "ENDED" &&
      (s.confirmed_answers.length || s.pending_proposal)
    )
      invalid("Ended session retains answers");
  });
export const auditEventSchema = z.object({
  event_id: text,
  at: text,
  question_id: z.string().nullable(),
  event_type: z.enum([
    "started",
    "proposed",
    "confirmed",
    "corrected",
    "message",
    "paused",
    "resumed",
    "accepted",
    "ended",
  ]),
  raw_reply: z.string().nullable(),
  catalog_version: text,
  retrieval_method: text,
  snippets: z.array(snippetSchema),
  model_action: z.string().nullable(),
  proposal_id: z.string().nullable(),
  option_id: z.string().nullable(),
  validation_result: text,
  state_before: text,
  state_after: text,
  latency_ms: z.number().nonnegative(),
  model_id: z.string().nullable(),
  synthetic: z.boolean(),
});
export const auditSchema = z.object({
  session_id: text,
  events: z.array(auditEventSchema),
  retention_notice: text.optional(),
  source_workbook: text.nullable().optional(),
  source_sha256: text.nullable().optional(),
});
export type Snapshot = z.infer<typeof snapshotSchema>;
export type Question = z.infer<typeof questionSchema>;
export type Answer = z.infer<typeof answerSchema>;
export type Profile = z.infer<typeof profileSchema>;
export type Audit = z.infer<typeof auditSchema>;
export type Action = (typeof actions)[number];
export type Command = {
  action: Action | "start";
  request_id: string;
  expected_revision: number;
  session_id?: string;
  text?: string;
  option_id?: string;
  proposal_id?: string;
  question_id?: string;
  review_version?: string;
  explicit_confirmation?: boolean;
};
export interface Adapter {
  mode: "demo" | "http";
  mutate(command: Command, signal?: AbortSignal): Promise<Snapshot>;
  load(sessionId: string, signal?: AbortSignal): Promise<Snapshot>;
  audit(sessionId: string, signal?: AbortSignal): Promise<Audit>;
  profile(
    profileId: string,
    sessionId: string,
    signal?: AbortSignal,
  ): Promise<Profile>;
}
