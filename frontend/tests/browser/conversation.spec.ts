import { test, expect, type Page } from "@playwright/test";
async function start(page: Page) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Start fictional conversation" })
    .click();
  await expect(
    page.getByRole("group", { name: "Choose a fixed answer" }),
  ).toBeVisible();
}
async function choose(page: Page, index = 0) {
  await page.locator(".options button").nth(index).click();
  await expect(page.getByText("PROPOSED · NOT YET CONFIRMED")).toBeVisible();
  const check = page.getByRole("checkbox");
  if (await check.count()) {
    await expect(
      page.getByRole("button", { name: "Confirm answer", exact: true }),
    ).toBeDisabled();
    await check.check();
  }
  await page
    .getByRole("button", { name: "Confirm answer", exact: true })
    .click();
}
test("six answers, Unsure, review explanation, correction, audit and simulated export", async ({
  page,
}) => {
  await start(page);
  for (let i = 0; i < 6; i++) await choose(page, i === 2 ? 2 : 0);
  await expect(page.getByText("Q7 · REVIEW AND ACCEPTANCE")).toBeVisible();
  await expect(page.locator("#actions .unresolved")).toContainText(
    "unresolved",
  );
  await page
    .getByRole("button", { name: "I’m not sure about this review" })
    .click();
  await expect(
    page.getByRole("button", { name: "Accept and save these answers" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Edit Q4:" }).click();
  await expect(page.locator(".summary .answer")).toHaveCount(5);
  await choose(page, 1);
  await expect(page.locator(".summary .answer")).toHaveCount(6);
  await page.getByRole("button", { name: "Conversation evidence" }).click();
  await expect(page.locator(".events")).toContainText("Proposed");
  await expect(page.locator(".events")).toContainText("Confirmed");
  await page
    .getByRole("button", { name: "Accept and save these answers" })
    .click();
  await expect(page.getByText("Demo complete. No real save.")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export simulated profile" }).click();
  expect((await download).suggestedFilename()).toBe("simulated-profile.json");
  await page
    .getByRole("button", { name: "Export this fictional demo audit" })
    .click();
  await expect(page.getByRole("dialog")).toContainText("raw replies");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.screenshot({
    path: "/private/tmp/careful-v2-desktop.png",
    fullPage: true,
  });
});
test("phone, keyboard, clarification, pause during request, resume, end and restart dialog", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await start(page);
  const input = page.getByRole("textbox", { name: "Your message" });
  await input.fill("Fictional reply");
  await input.press("Shift+Enter");
  expect(await input.inputValue()).toContain("\n");
  await input.press("Enter");
  await expect(
    page.getByRole("group", { name: "Choose a fixed answer" }),
  ).toBeEnabled();
  await expect(page.locator(".bubble.user")).toHaveCount(1);
  await page.locator(".options button").first().click();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Resume conversation" }),
  ).toBeEnabled();
  await expect(
    page.getByRole("button", { name: "Confirm answer", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Resume conversation" }).click();
  await expect(
    page.getByRole("group", { name: "Choose a fixed answer" }),
  ).toBeEnabled();
  await expect(page.locator(".summary .answer")).toHaveCount(0);
  await page.getByRole("button", { name: "Restart", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await input.fill("Fictional long reply ".repeat(200));
  await input.press("Enter");
  await expect(
    page.getByRole("group", { name: "Choose a fixed answer" }),
  ).toBeEnabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator("#status")).toHaveText("");
  await page.screenshot({
    path: "/private/tmp/careful-v2-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "End", exact: true }).click();
  await page
    .getByRole("button", { name: "End and clear temporary session" })
    .click();
  await expect(
    page.getByText("Conversation ended.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".bubble")).toHaveCount(0);
  await expect(page.locator(".summary .answer")).toHaveCount(0);
  await page.getByRole("button", { name: "Start a new conversation" }).click();
  await page
    .getByRole("button", { name: "Start fictional conversation" })
    .click();
  await expect(page.locator(".options button").first()).toBeEnabled();
  await page.getByRole("button", { name: "Restart", exact: true }).click();
  await page.getByRole("button", { name: "End current session" }).click();
  await expect(
    page.getByRole("button", { name: "Start fictional conversation" }),
  ).toBeVisible();
});
