import {
  test,
  expect,
  type Page,
  type APIResponse,
  type Response,
} from "@playwright/test";
import { snapshotSchema, type Snapshot } from "../../src/api/contracts";

// Errors report stages/status/schema paths, never request text or response bodies.
function check(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function snapshot(response: APIResponse | Response, stage: string) {
  check(
    response.ok(),
    `${stage}: HTTP ${response.status()}. CS2 must expose the /api/v1 contract on port 8001.`,
  );
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new Error(
      `${stage}: expected an unwrapped JSON SessionSnapshot, not HTML or an empty response.`,
    );
  }
  const parsed = snapshotSchema.safeParse(value);
  if (!parsed.success) {
    const paths = parsed.error.issues
      .map((issue) => `${issue.path.join(".") || "snapshot"} (${issue.code})`)
      .slice(0, 8)
      .join(", ");
    throw new Error(
      `${stage}: invalid SessionSnapshot fields: ${paths}. See src/api/contracts.ts.`,
    );
  }
  return parsed.data;
}

async function mutation(
  page: Page,
  path: string,
  before: Snapshot | undefined,
  stage: string,
  action: () => Promise<unknown>,
) {
  const waiting = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === path &&
      response.request().method() === "POST",
    { timeout: 35000 },
  );
  let response: Response;
  try {
    [response] = await Promise.all([waiting, action()]);
  } catch {
    throw new Error(
      `${stage}: no completed response through Vite within the adapter's 35-second budget. Check FastAPI :8001, /api/v1 routes, and HTTP-mode UI controls.`,
    );
  }
  const body = response.request().postDataJSON();
  check(
    typeof body.request_id === "string" &&
      body.request_id.length > 0 &&
      response.request().headers()["idempotency-key"] === body.request_id,
    `${stage}: request_id must match Idempotency-Key.`,
  );
  check(
    body.expected_revision === (before?.revision ?? 0),
    `${stage}: incorrect expected_revision.`,
  );
  const next = await snapshot(response, stage);
  check(
    next.revision > body.expected_revision,
    `${stage}: mutation revision must increase.`,
  );
  if (before) {
    check(
      next.session_id === before.session_id,
      `${stage}: session ID changed.`,
    );
    check(
      next.catalog_version === before.catalog_version,
      `${stage}: catalog version changed.`,
    );
  }
  if (path.endsWith("/confirmations")) {
    check(
      body.proposal_id === before?.pending_proposal?.proposal_id,
      `${stage}: confirmation must reference the pending proposal.`,
    );
    check(
      body.explicit_confirmation === !!before?.pending_proposal?.safety,
      `${stage}: safety confirmation does not match the checkbox.`,
    );
  }
  return next;
}

async function send(page: Page, text: string, before: Snapshot, stage: string) {
  check(
    before.allowed_actions.includes("message"),
    `${stage}: backend must allow free-text messages.`,
  );
  try {
    await page.getByRole("textbox", { name: "Your message" }).fill(text);
  } catch {
    throw new Error(`${stage}: the HTTP-mode message composer is unavailable.`);
  }
  return mutation(
    page,
    `/api/v1/sessions/${encodeURIComponent(before.session_id)}/messages`,
    before,
    stage,
    () => page.getByRole("button", { name: "Send" }).click(),
  );
}

async function visibleText(
  page: Page,
  selector: string,
  text: string,
  stage: string,
) {
  // Boolean comparisons keep response text out of assertion diagnostics.
  await expect
    .poll(
      async () =>
        (await page.locator(selector).allTextContents()).some(
          (value) => value.trim() === text,
        ),
      { message: `${stage}: backend text must appear in the UI.` },
    )
    .toBe(true);
}

test.afterEach(async ({ page }) => {
  // Playwright may attach a DOM error context even with tracing disabled.
  // Clear fictional chat before teardown collects that context.
  await page.goto("about:blank").catch(() => {});
});

test("real HTTP free-text proposal requires confirmation before the next question", async ({
  page,
}, testInfo) => {
  test.setTimeout(120000); // Whole journey; the adapter's per-request timeout stays unchanged.
  const questionId = process.env.LIVE_QUESTION_ID;
  const answer = process.env.LIVE_ANSWER ?? "";
  const optionId = process.env.LIVE_OPTION_ID;
  const ambiguous = process.env.LIVE_AMBIGUOUS_ANSWER;
  check(
    questionId?.trim() && answer?.trim() && optionId?.trim(),
    "Configure LIVE_QUESTION_ID, LIVE_ANSWER, and LIVE_OPTION_ID using an agreed fictional input for the backend's first question. See tests/README.md.",
  );
  check(
    answer.length <= 8000 && (!ambiguous || ambiguous.length <= 8000),
    "Configured fictional messages must fit the 8000-character composer limit.",
  );

  await page.goto("/");
  await expect(page.locator("header .pill")).toContainText("Backend mode");
  let current = await mutation(
    page,
    "/api/v1/sessions",
    undefined,
    "Start session",
    () =>
      page
        .getByRole("button", { name: "Start fictional conversation" })
        .click(),
  );
  check(
    current.state === "ASKING" && current.active_question,
    "Start session: expected ASKING with a real active question.",
  );
  check(
    current.confirmed_answers.length === 0 && current.pending_proposal === null,
    "Start session: answers must start unconfirmed.",
  );
  const question = current.active_question;
  check(
    question.question_id === questionId,
    "Start session: LIVE_QUESTION_ID does not match the active question; update the agreed input configuration.",
  );
  check(
    question.options.some((option) => option.option_id === optionId),
    "Start session: LIVE_OPTION_ID is absent from the active question's catalog.",
  );
  await visibleText(page, ".question h3", question.text, "Active question");

  if (ambiguous) {
    current = await send(page, ambiguous, current, "Agreed ambiguous answer");
    check(
      current.response_type === "clarification" &&
        current.state === "ASKING" &&
        current.pending_proposal === null &&
        current.confirmed_answers.length === 0 &&
        current.active_question?.question_id === questionId,
      "Agreed ambiguous answer: expected clarification on the same question without a proposal or confirmation.",
    );
    await visibleText(
      page,
      ".bubble.assistant p",
      current.assistant_message,
      "Clarification",
    );
    await expect(
      page.getByRole("button", { name: "Confirm answer", exact: true }),
    ).toHaveCount(0);
  } else {
    testInfo.annotations.push({
      type: "coverage",
      description:
        "Clarification not exercised: LIVE_AMBIGUOUS_ANSWER was not configured.",
    });
  }

  current = await send(page, answer, current, "Agreed free-text answer");
  check(
    current.response_type === "proposal" &&
      current.state === "AWAITING_CONFIRMATION" &&
      current.pending_proposal,
    "Agreed free-text answer: expected a proposal. Clarification/fallback is not a completed journey; agree a deterministic input or fix interpretation.",
  );
  const proposal = current.pending_proposal;
  check(
    proposal.origin === "model" &&
      proposal.question_id === questionId &&
      proposal.option_id === optionId,
    "Free-text proposal: expected the configured catalog option from model interpretation, not demo/button output.",
  );
  check(
    current.confirmed_answers.length === 0 &&
      current.allowed_actions.includes("confirm"),
    "Proposal: must remain unconfirmed and allow explicit confirmation.",
  );
  await expect(page.getByText("PROPOSED · NOT YET CONFIRMED")).toBeVisible();
  await visibleText(
    page,
    ".proposal p",
    proposal.playback,
    "Proposal playback",
  );
  await expect(page.locator(".summary .answer")).toHaveCount(0);

  // Read authoritative state through the same proxy/cookie context before clicking.
  let response: APIResponse;
  try {
    response = await page.request.get(
      `/api/v1/sessions/${encodeURIComponent(current.session_id)}`,
      { timeout: 35000 },
    );
  } catch {
    throw new Error(
      "Before confirmation: GET session unavailable through Vite; CS2 must support recovery.",
    );
  }
  const pending = await snapshot(response, "Before confirmation GET session");
  check(
    pending.session_id === current.session_id &&
      pending.catalog_version === current.catalog_version &&
      pending.revision === current.revision &&
      pending.state === "AWAITING_CONFIRMATION" &&
      pending.pending_proposal?.proposal_id === proposal.proposal_id &&
      pending.confirmed_answers.length === 0,
    "Before confirmation: authoritative session must still contain the unconfirmed proposal, with no automatic acceptance.",
  );

  const confirm = page.getByRole("button", {
    name: "Confirm answer",
    exact: true,
  });
  if (proposal.safety) {
    await expect(confirm).toBeDisabled();
    await page
      .getByRole("checkbox", { name: "I have checked this safety answer" })
      .check();
  }
  await expect(confirm).toBeEnabled();
  current = await mutation(
    page,
    `/api/v1/sessions/${encodeURIComponent(current.session_id)}/confirmations`,
    current,
    "Explicit confirmation",
    () => confirm.click(),
  );
  check(
    current.confirmed_answers.length === 1,
    "Confirmation: expected exactly one confirmed answer.",
  );
  const confirmed = current.confirmed_answers[0];
  check(
    confirmed.question_id === questionId &&
      confirmed.option_id === optionId &&
      confirmed.playback === proposal.playback &&
      confirmed.is_unsure === proposal.is_unsure,
    "Confirmation: confirmed answer must match the proposal, including Unsure.",
  );
  check(
    current.state === "ASKING" &&
      current.pending_proposal === null &&
      current.active_question &&
      current.active_question.question_id !== questionId &&
      current.active_question.order > question.order,
    "Confirmation: expected the next active question, with the proposal cleared.",
  );
  await expect(page.locator(".summary .answer")).toHaveCount(1);
  await visibleText(
    page,
    ".summary .answer p",
    proposal.playback,
    "Confirmed answer",
  );
  await visibleText(
    page,
    ".question h3",
    current.active_question.text,
    "Next question",
  );
});
