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
  // First visit lands on onboarding; complete it once.
  if (
    page.url().includes("/onboarding") ||
    (await page
      .getByRole("heading", { name: "Set up your track" })
      .isVisible()
      .catch(() => false))
  ) {
    await page.getByRole("button", { name: "Start studying" }).click();
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
    await shot(page, "today", project);

    // Resume-or-start: abandon any leftover session so the run is deterministic.
    const resume = page.getByRole("button", { name: "Resume" });
    if (await resume.isVisible().catch(() => false)) {
      await page.goto("/practice");
      await page.getByRole("button", { name: "Abandon it" }).click();
      await page.goto("/");
    }
    await page.getByRole("button", { name: "I have five minutes" }).click();
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
    await expect(page.getByText("First-attempt accuracy")).toBeVisible();
    await expect(page.getByText(/not exam evidence/i).first()).toBeVisible();
    await shot(page, "progress", project);
  });

  test("keyboard shortcuts select options but Enter on a link never submits", async ({ page }) => {
    await login(page);
    await page.goto("/practice");
    const abandon = page.getByRole("button", { name: "Abandon it" });
    if (await abandon.isVisible().catch(() => false)) await abandon.click();
    await page.getByRole("button", { name: /Start practice/ }).click();
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
  });
});
