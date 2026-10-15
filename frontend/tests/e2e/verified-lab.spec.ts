import { expect, test } from "@playwright/test";

import { login, shot, switchTrack } from "./helpers";

// The e2e database carries the fixture pack (two verified labs) next to the shipped packs,
// and the API points at the stub K16S started by playwright.config.ts.
test.describe("verified lab on the lab cluster", () => {
  test.afterEach(async ({ page }) => {
    // Leave the shipped track active for the other specs and projects.
    await switchTrack(page, "SAA-C03");
  });

  test("open lab → set up → check → attempt recorded", async ({ page }, info) => {
    const project = info.project.name;
    await login(page);

    // Switch tracks the way the owner does: the chip in the Settings page head opens the
    // course picker; picking a card switches and the chip follows.
    await page.goto("/settings");
    await page.locator(".track-switch").click();
    await page.getByRole("radio", { name: /TST-C01/ }).click();
    await expect(page.locator(".track-switch__code")).toHaveText("TST-C01");
    await shot(page, "settings-track", project);

    await page.goto("/labs");
    await expect(page.getByRole("heading", { name: "Verified on the lab cluster" })).toBeVisible();
    await expect(page.getByText(/Lab cluster ready/)).toBeVisible();
    await shot(page, "labs", project);
    await page.locator('[data-lab="lab-verified"]').click();
    await expect(page).toHaveURL(/\/labs\/lab-verified$/);

    // The task text is the stub's own, fetched live and attributed.
    await expect(page.getByRole("heading", { name: "Stub: a pod keeps crashing" })).toBeVisible();
    await expect(page.getByText(/fetched live/)).toBeVisible();
    // The e2e database is shared across the viewport projects, so a later project finds the
    // earlier one's attempts: the button then reads "Set up again". Both are the same step.
    const setup = page.getByRole("button", { name: /Set up (environment|again)/ });
    await expect(setup).toBeEnabled();
    await setup.click();
    await expect(page.getByText(/Environment ready/)).toBeVisible();
    await expect(page.getByRole("link", { name: /Open terminal/ })).toBeVisible();
    await shot(page, "lab-set-up", project);

    await page.getByRole("button", { name: "Check answer" }).click();
    await expect(page.getByText("Not yet")).toBeVisible();
    await expect(page.getByText("FAIL: pod web-0 is still CrashLoopBackOff").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Check again" })).toBeVisible();
    // Earlier projects' attempts are listed too, so there may be several "failed" badges.
    const attempts = page.getByRole("list", { name: "Attempts" });
    await expect(attempts.getByText("failed").first()).toBeVisible();
    await shot(page, "lab-checked", project);

    // The card on the list carries the verdict.
    await page.goto("/labs");
    const row = page.locator('[data-lab="lab-verified"]');
    await expect(row.getByText(/failed/)).toBeVisible();
    await expect(row.getByText("FAIL: pod web-0 is still CrashLoopBackOff")).toBeVisible();
  });
});
