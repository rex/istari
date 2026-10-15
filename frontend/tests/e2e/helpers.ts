import { expect, type Page } from "@playwright/test";

import { E2E_PASSWORD, E2E_USERNAME } from "./global-setup";

export async function shot(page: Page, name: string, project: string) {
  await page.screenshot({
    path: `test-results/screenshots/${project}-${name}.png`,
    fullPage: true,
  });
}

export async function login(page: Page) {
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

interface TrackSummary {
  exam_version_id: number;
  code: string;
}

/** Make `code` the active track through the API (what onboarding does), with the CSRF token. */
export async function switchTrack(page: Page, code: string) {
  const me = (await (await page.request.get("/api/me")).json()) as {
    user: { csrf_token: string };
  };
  const tracks = (await (await page.request.get("/api/tracks")).json()) as TrackSummary[];
  const track = tracks.find((t) => t.code === code);
  expect(track, `track ${code} is seeded`).toBeTruthy();
  const response = await page.request.post("/api/onboarding", {
    data: { exam_version_id: track?.exam_version_id, preferred_session_minutes: 5 },
    headers: { "x-csrf-token": me.user.csrf_token },
  });
  expect(response.ok(), `switch to ${code}: ${response.status()}`).toBe(true);
}
