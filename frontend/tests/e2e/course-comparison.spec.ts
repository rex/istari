import { expect, test } from "@playwright/test";

import { login, shot, switchTrack } from "./helpers";

// Runs before lecture-review.spec.ts (file order) and the viewport projects share one
// database, so it builds the index itself when no run exists yet and tolerates one that does.
test.describe("courses compared", () => {
  test.afterEach(async ({ page }) => {
    await switchTrack(page, "SAA-C03");
  });

  test("the fixture course shows its coverage, captions and currency", async ({ page }, info) => {
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

    await page.goto("/watch/compare");
    await expect(page.getByRole("heading", { name: "Courses compared" })).toBeVisible();
    const fixture = page.getByRole("row", { name: /Mapping Course 2024/ });
    await expect(fixture).toBeVisible();
    // Objectives touched of the fixture track's three: the title rule maps one lecture.
    await expect(fixture.getByText(/^[1-3]\/3$/)).toBeVisible();
    if (info.project.name !== "mobile") {
      await expect(fixture.getByText("current exam")).toBeVisible();
      await expect(fixture.getByText("1 of 1")).toBeVisible();
    }
    await shot(page, "courses-compared", info.project.name);

    // Sorting by title keeps the row and marks the column.
    await page.getByRole("button", { name: "Course" }).click();
    await expect(page.getByRole("columnheader", { name: "Course" })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    await expect(page.getByRole("row", { name: /Mapping Course 2024/ })).toBeVisible();
  });
});
