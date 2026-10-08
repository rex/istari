import { expect, test, type Page } from "@playwright/test";

import { E2E_PASSWORD, E2E_USERNAME } from "./global-setup";

async function shot(page: Page, name: string, project: string) {
  await page.screenshot({
    path: `test-results/screenshots/${project}-${name}.png`,
    fullPage: true,
  });
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(E2E_USERNAME);
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Enter" }).click();
  await page.waitForURL((url) => !url.pathname.endsWith("/login"));
  // The first login must complete onboarding. Ask the API rather than race the
  // router's redirect from "/" to "/onboarding".
  const probe = await page.request.get("/api/me");
  expect(probe.ok(), `GET /api/me after login: ${probe.status()} ${await probe.text()}`).toBe(true);
  const me = (await probe.json()) as { onboarding_required: boolean };
  if (me.onboarding_required) {
    await page.goto("/onboarding");
    await page.getByRole("button", { name: "Start studying" }).click();
    await page.waitForURL(/\/$/);
  } else {
    await page.goto("/");
  }
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
}

test.describe("core study loop", () => {
  test("login → Today → five-question session → feedback → summary → review → progress", async ({
    page,
  }, info) => {
    const project = info.project.name;
    await login(page);
    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator(".build-badge")).toHaveText(/Istari v\d+\.\d+\.\d+ · \S+ · up since/);
    await shot(page, "today", project);

    // Resume-or-start: abandon any leftover session so the run is deterministic.
    const resume = page.getByRole("button", { name: "Resume" });
    if (await resume.isVisible().catch(() => false)) {
      await page.goto("/practice");
      await page.getByRole("button", { name: "Abandon it" }).click();
      await page.goto("/");
    }
    // With a fresh pack the plan rightly leads with due flashcards, so start the
    // five-question practice session explicitly from the Practice page.
    await page.goto("/practice");
    await page.locator('label[for="minutes-5"]').click();
    await expect(page.locator("#minutes-5")).toBeChecked();
    await page.getByRole("button", { name: "Start practice" }).click();
    await expect(page).toHaveURL(/\/practice\/\d+$/);

    for (let i = 1; i <= 5; i += 1) {
      await expect(page.getByText(`Question ${i} of 5`)).toBeVisible();
      const instruction = await page.locator(".question__instruction").textContent();
      const needed = /Choose (\d+)/.exec(instruction ?? "")?.[1] ?? "1";
      const count = Number(needed);
      if (i === 1) await shot(page, "question", project);
      const options = page.locator(".option");
      for (let n = 0; n < count; n += 1) await options.nth(n).click();
      await page.getByRole("button", { name: "Confident" }).click();
      const check = page.getByRole("button", { name: "Check answer" });
      await expect(check).toBeEnabled();
      await check.click();
      await expect(page.locator(".feedback__verdict")).toBeVisible();
      await expect(page.getByText("Decisive constraint:")).toBeVisible();
      if (i === 1) await shot(page, "feedback", project);
      if (i < 5) await page.getByRole("button", { name: "Next question" }).click();
    }
    await page.getByRole("button", { name: "Finish session" }).click();
    await expect(page.getByText(/Practice complete/)).toBeVisible();
    await expect(page.locator(".summary-score")).toContainText("/ 5");
    await shot(page, "summary", project);

    // Review: reveal with the keyboard, rate Good.
    await page.goto("/review");
    await expect(page.locator(".flashcard__face").first()).toBeVisible();
    await page.keyboard.press("Space");
    await expect(page.locator(".flashcard__face--back")).toBeVisible();
    await shot(page, "review", project);
    await page.keyboard.press("3");
    await expect(page.locator(".flashcard__counter")).toContainText("Card 2 of");

    await page.goto("/progress");
    await expect(page.getByRole("heading", { name: "Progress" })).toBeVisible();
    await expect(page.getByText("First-attempt accuracy", { exact: true })).toBeVisible();
    await expect(page.getByText(/not exam evidence/i).first()).toBeVisible();
    await shot(page, "progress", project);
  });

  test("keyboard shortcuts select options but Enter on a link never submits", async ({ page }) => {
    await login(page);
    // Decide "abandon or start" only once the page knows whether a session is open.
    const activeKnown = page.waitForResponse((r) => r.url().endsWith("/api/sessions/active"));
    await page.goto("/practice");
    await activeKnown;
    const abandon = page.getByRole("button", { name: "Abandon it" });
    if (await abandon.isVisible()) {
      await abandon.click();
      await expect(abandon).toBeHidden();
    }
    const start = page.getByRole("button", { name: /Start practice/ });
    await expect(start).toBeEnabled();
    await start.click();
    await expect(page).toHaveURL(/\/practice\/\d+$/);
    await page.locator("body").click({ position: { x: 5, y: 5 } });
    await page.keyboard.press("1");
    await expect(page.locator(".option").first()).toHaveClass(/is-selected/);
    // Focus a navigation control, press Enter: nothing should be submitted.
    await page.getByRole("button", { name: "Exit focus mode" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".feedback__verdict")).toHaveCount(0);
  });
});

test.describe("protection", () => {
  test("API refuses without a session and the SPA bounces to login", async ({ page, request }) => {
    const me = await request.get("/api/me");
    expect(me.status()).toBe(401);
    const health = await request.get("/api/health");
    expect(health.headers()["content-security-policy"]).toContain("script-src 'self'");
    await page.goto("/progress");
    await expect(page).toHaveURL(/\/login$/);
    // The build stamp is visible before login, and it is the API's, not the bundle's.
    const badge = page.locator(".build-badge");
    await expect(badge).toHaveText(/Istari v\d+\.\d+\.\d+ · \S+ · up since/);
    await expect(badge.getByRole("status")).toHaveCount(0);
  });
});
