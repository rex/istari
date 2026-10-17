import { expect, test } from "@playwright/test";

import { login, shot, switchTrack } from "./helpers";

// The e2e API reads a one-lecture fixture course (global-setup.ts) on the fixture track.
// The viewport projects share one database: the first project reviews the lecture, the
// later ones find the queue empty and only confirm the mapping shows on the player.
test.describe("lecture mapping", () => {
  test.afterEach(async ({ page }) => {
    await switchTrack(page, "SAA-C03");
  });

  test("rebuild the index, review the lecture, see it on the player", async ({ page }, info) => {
    const project = info.project.name;
    await login(page);
    await switchTrack(page, "TST-C01");

    await page.goto("/content/lectures");
    await expect(page.getByRole("heading", { name: "Lecture mapping" })).toBeVisible();
    const rebuild = page.getByRole("button", { name: "Rebuild index" });
    await rebuild.click();
    await expect(rebuild).toBeEnabled({ timeout: 30_000 });
    await expect(page.getByText(/1 of 1 lectures indexed/)).toBeVisible({ timeout: 30_000 });
    await shot(page, "lecture-index", project);

    const card = page.getByRole("region", { name: "Lecture to review" });
    if (await card.isVisible().catch(() => false)) {
      await expect(
        card.getByRole("heading", { name: "Roles and least privilege obj-1-1" }),
      ).toBeVisible();
      await expect(card.getByText("rule")).toBeVisible();
      await expect(card.getByText(/Course 1 of 1/)).toBeVisible();
      await expect(
        card.getByRole("button", { name: /Accept the rest of this section/ }),
      ).toBeVisible();
      await shot(page, "lecture-review", project);
      await card.getByRole("button", { name: /Pin selected/ }).click();
    }
    await expect(page.getByText("Nothing left to review")).toBeVisible();

    // The player shows what the lecture teaches.
    const courses = (await (await page.request.get("/api/courses")).json()) as {
      courses: { slug: string; title: string }[];
    };
    const course = courses.courses.find((c) => c.title.startsWith("Mapping Course"));
    expect(course, "the fixture course is in the catalog").toBeTruthy();
    const lecture = "01 - IAM/001 Roles and least privilege obj-1-1.mp4";
    await page.goto(
      `/watch/${encodeURIComponent(course?.slug ?? "")}/play?lecture=${encodeURIComponent(lecture)}`,
    );
    await expect(page.getByText("Teaches")).toBeVisible();
    await expect(page.getByText("1.1", { exact: true }).first()).toBeVisible();
    // And borrows the pack's figure for that objective into the rail.
    await expect(page.getByRole("heading", { name: "See it" })).toBeVisible();
    await expect(page.getByRole("img", { name: "A box labelled Figure one" })).toBeVisible();
  });
});
