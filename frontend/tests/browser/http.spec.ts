import { test, expect } from "@playwright/test";
import { createDemo } from "../../src/api/demo";
import type { Command, Snapshot } from "../../src/api/contracts";
test("HTTP retry uses original IDs; lost confirmation reply never duplicates an answer", async ({
  page,
}) => {
  const backend = createDemo(0);
  const attempts: Command[] = [];
  let lostMessage = false,
    lostConfirm = false;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url()),
      body = request.postDataJSON() ?? {};
    const action = (
      {
        messages: "message",
        selections: "select",
        confirmations: "confirm",
        corrections: "change",
        pause: "pause",
        resume: "resume",
        finalize: "finalize",
      } as Record<string, Command["action"]>
    )[url.pathname.split("/").at(-1)!];
    const command: Command = {
      ...body,
      action: action ?? "start",
      ...(action ? { session_id: url.pathname.split("/")[4] } : {}),
    };
    attempts.push(command);
    if (action === "message" && !lostMessage) {
      lostMessage = true;
      await route.abort();
      return;
    }
    const snapshot = await backend.mutate(command);
    if (action === "confirm" && !lostConfirm) {
      lostConfirm = true;
      await route.abort();
      return;
    }
    await route.fulfill({ json: snapshot });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Start fictional conversation" })
    .click();
  const input = page.getByRole("textbox", { name: "Your message" });
  await input.fill("Fictional request");
  await input.press("Enter");
  await expect(page.getByRole("alert")).toContainText("Unable to reach");
  await page.getByRole("button", { name: "Retry same request" }).click();
  await expect(
    page.getByRole("group", { name: "Choose a fixed answer" }),
  ).toBeEnabled();
  await expect(page.locator(".bubble.user")).toHaveCount(1);
  await page.locator(".options button").first().click();
  await page
    .getByRole("button", { name: "Confirm answer", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByRole("button", { name: "Retry same request" }).click();
  await expect(page.locator(".summary .answer")).toHaveCount(1);
  await expect(page.locator(".bubble.user")).toHaveCount(3);
  expect(
    attempts.filter((x) => x.action === "message").map((x) => x.request_id)[0],
  ).toBe(
    attempts.filter((x) => x.action === "message").map((x) => x.request_id)[1],
  );
  expect(
    attempts.filter((x) => x.action === "confirm").map((x) => x.request_id)[0],
  ).toBe(
    attempts.filter((x) => x.action === "confirm").map((x) => x.request_id)[1],
  );
});
test("late HTTP result cannot undo Pause", async ({ page }) => {
  const backend = createDemo(0);
  let latest: Snapshot;
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request(),
      parts = new URL(req.url()).pathname.split("/"),
      body = req.postDataJSON() ?? {};
    if (req.method() === "GET") {
      await route.fulfill({ json: latest });
      return;
    }
    if (parts.at(-1) === "messages") {
      // Backend completes before the browser receives the reply. Pause loads that
      // newer revision, then the delayed response must be ignored by the UI.
      latest = await backend.mutate({
        ...body,
        action: "message",
        session_id: parts[4],
      });
      const delayed = structuredClone(latest);
      await new Promise((r) => setTimeout(r, 600));
      await route.fulfill({ json: delayed }).catch(() => {});
      return;
    }
    latest = await backend.mutate({
      ...body,
      action: parts.at(-1) === "sessions" ? "start" : parts.at(-1),
      ...(parts[4] ? { session_id: parts[4] } : {}),
    });
    await route.fulfill({ json: latest });
  });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Start fictional conversation" })
    .click();
  await page
    .getByRole("textbox", { name: "Your message" })
    .fill("Fictional delayed reply");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Resume conversation" }),
  ).toBeVisible();
  await page.waitForTimeout(800);
  await expect(
    page.getByRole("button", { name: "Resume conversation" }),
  ).toBeVisible();
  await expect(page.getByRole("textbox")).toBeDisabled();
});

for (const status of [404, 410]) {
  test(`expired session ${status} can return to start and begin a new conversation`, async ({
    page,
  }) => {
    const backend = createDemo(0);
    let creations = 0;
    await page.route("**/api/v1/**", async (route) => {
      const req = route.request();
      if (req.url().endsWith("/sessions") && req.method() === "POST") {
        creations++;
        await route.fulfill({
          json: await backend.mutate({
            ...req.postDataJSON(),
            action: "start",
          }),
        });
      } else await route.fulfill({ status, json: { code: "session_expired" } });
    });
    await page.goto("/");
    await page
      .getByRole("button", { name: "Start fictional conversation" })
      .click();
    await page.locator(".options button").first().click();
    await expect(page.getByRole("alert")).toContainText(
      "session is no longer available",
    );
    await expect(
      page.getByRole("button", { name: "Return to start" }),
    ).toBeFocused();
    await expect(
      page.getByRole("button", { name: "Retry same request" }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Return to start" }).click();
    await page
      .getByRole("button", { name: "Start fictional conversation" })
      .click();
    await expect(page.locator(".options button").first()).toBeEnabled();
    await expect(page.locator(".bubble.user")).toHaveCount(0);
    expect(creations).toBe(2);
  });
}
