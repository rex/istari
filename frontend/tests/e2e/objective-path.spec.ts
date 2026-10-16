import { expect, test } from "@playwright/test";

import { login, shot, switchTrack } from "./helpers";

// Needs the lecture index (built here when no run exists). The viewport projects share one
// database; the exclusion is restored at the end, so every project finds the same path.
test.describe("learning path", () => {
  test.afterEach(async ({ page }) => {
    await switchTrack(page, "SAA-C03");
  });

  test("the objective's path lists the mapped lecture, plays along it, takes an exclusion", async ({
    page,
  }, info) => {
    await login(page);
    await switchTrack(page, "TST-C01");
    const status = (await (await page.request.get("/api/lecture-index")).json()) as {
      last_run_at: string | null;
    };
    if (!status.last_run_at) {
      await page.goto("/content/lectures");
      const rebuild = page.getByRole("button", { name: "Rebuild index" });
      await rebuild.click();
      await expect(rebuild).toBeEnabled({ timeout: 30_000 });
      await expect(page.getByText(/1 of 1 lectures indexed/)).toBeVisible({ timeout: 30_000 });
    }

    await page.goto("/learn/path/1.1");
    await expect(page.getByRole("heading", { level: 1, name: /^1\.1/ })).toBeVisible();
    const list = page.getByRole("list", { name: "Lectures on the path" });
    const lecture = list.getByRole("link", { name: "Roles and least privilege obj-1-1" });
    await expect(lecture).toBeVisible();
    await shot(page, "learning-path", info.project.name);

    // Play along the path: the player names the position and links back.
    await page.getByRole("button", { name: /^(Start|Continue):/ }).click();
    // The router quotes a search string that reads as a number, so match the key only.
    await page.waitForURL(/[?&]path=/);
    await expect(page.getByText("1 of 1 in path 1.1")).toBeVisible();
    await page.getByRole("link", { name: "path 1.1" }).click();
    await expect(page.getByRole("heading", { level: 1, name: /^1\.1/ })).toBeVisible();

    // Exclude the lecture, then restore it; the path is recomposed each time.
    await page.getByRole("button", { name: "Exclude" }).first().click();
    await expect(page.getByRole("heading", { name: "Excluded" })).toBeVisible();
    await page.getByRole("button", { name: "Restore" }).click();
    await expect(
      list.getByRole("link", { name: "Roles and least privilege obj-1-1" }),
    ).toBeVisible();

    // Progress links to the path from the objective's row.
    await page.goto("/progress");
    await expect(page.getByRole("link", { name: /^path: 1 lectures/ }).first()).toBeVisible();
  });
});
