import { expect, test } from "@playwright/test";

import { login, shot } from "./helpers";

// Under 720px the primary nav is a fixed bottom tab bar of five (Today, Learn, Practice,
// Review, Watch); Progress, Labs and Settings live behind More; focus mode hides the bar.
test.describe("phone shell", () => {
  test("tab bar, More sheet and focus mode", async ({ page }, info) => {
    const project = info.project.name;
    test.skip(project !== "mobile", "the tab bar exists only under 720px");
    await login(page);

    const primary = page.getByRole("navigation", { name: "Primary" });
    await expect(primary.getByRole("link", { name: "Review" })).toBeVisible();
    await expect(primary.getByRole("link", { name: "Watch" })).toBeVisible();
    await expect(primary.getByRole("link", { name: "Progress" })).toBeHidden();
    await expect(page.getByRole("navigation", { name: "Secondary" })).toBeHidden();
    await shot(page, "phone-tabs", project);

    await page.getByRole("button", { name: "More" }).click();
    const sheet = page.getByRole("dialog");
    await expect(sheet.getByRole("link", { name: "Progress" })).toBeVisible();
    await shot(page, "phone-more", project);
    await sheet.getByRole("link", { name: "Labs" }).click();
    await expect(page).toHaveURL(/\/labs$/);
    await expect(sheet).toBeHidden();

    // Review enters focus mode: the tab bar goes, the focus bar stays at the top.
    await page.goto("/review");
    const exit = page.getByRole("button", { name: "Exit focus mode" });
    await expect(exit).toBeVisible();
    await expect(primary).toBeHidden();
    await shot(page, "phone-focus", project);
    await exit.click();
    await expect(primary.getByRole("link", { name: "Today" })).toBeVisible();
  });
});
