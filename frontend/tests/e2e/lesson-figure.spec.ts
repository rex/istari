import { expect, test } from "@playwright/test";

import { login, shot, switchTrack } from "./helpers";

// A lesson shows the figures its pack ships: the SAA-C03 pack's VPC drawing on the shipped
// track, and the fixture pack's figure placed in the body of its first lesson.
test.describe("a lesson shows its figure", () => {
  test.afterEach(async ({ page }) => {
    await switchTrack(page, "SAA-C03");
  });

  test("the shipped VPC figure sits in the network lesson", async ({ page }, info) => {
    await login(page);
    await page.goto("/learn/lesson-network-and-data-security");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Securing the network");
    // The accessible name is the figure item's own `alt`, not the Markdown placement's.
    const image = page.getByRole("img", { name: /A VPC with an internet gateway/ });
    await expect(image).toBeVisible();
    await expect(image).toHaveAttribute("src", "/api/figures/fig-vpc-two-tier.svg");
    // The lesson shows more than one figure; read the caption of this one.
    const figure = page.locator("figure.figure").filter({ has: image });
    await expect(figure.locator("figcaption")).toContainText("Two-tier web app in a VPC.");
    // And ends with "Do it": the brief it names, steps inline, the lab page a link away.
    await expect(page.getByRole("heading", { name: "Do it" })).toBeVisible();
    const doIt = page.locator('[data-do-it="lab-s3-gateway-endpoint-policy"]');
    await expect(doIt.getByRole("heading", { name: /Lock an S3 bucket/ })).toBeVisible();
    await expect(doIt.getByRole("heading", { name: "Steps" })).toBeVisible();
    await shot(page, "lesson-figure-vpc", info.project.name);
  });

  test("the fixture figure renders in the body with its caption", async ({ page }) => {
    await login(page);
    await switchTrack(page, "TST-C01");
    await page.goto("/learn/lesson-one");
    await expect(page.getByRole("heading", { name: "Lesson One" })).toBeVisible();
    await expect(page.getByRole("img", { name: "A box labelled Figure one" })).toBeVisible();
    const caption = page.locator("figure.figure figcaption");
    await expect(caption).toContainText("Figure one.");
    await expect(caption).toContainText("1.1");
    // The drawing itself is served by the API as an image.
    const svg = await page.request.get("/api/figures/fig-one.svg");
    expect(svg.ok()).toBe(true);
    expect(svg.headers()["content-type"]).toContain("image/svg+xml");
    // "Do it" runs the graded lab inline: the stub cluster's task and its steps.
    const doIt = page.locator('[data-do-it="lab-verified"]');
    await expect(doIt.getByRole("heading", { name: "Stub: a pod keeps crashing" })).toBeVisible();
    await expect(doIt.getByRole("button", { name: /Set up (environment|again)/ })).toBeVisible();
  });
});
