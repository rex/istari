import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";

// E2E runs against the API serving the built SPA on one origin (same as production).
// `make e2e` builds first; the API must have a migrated database with the seed
// pack and an owner (see tests/e2e/README.md).
const port = Number(process.env["E2E_PORT"] ?? 8001);
const stubPort = Number(process.env["E2E_K16S_PORT"] ?? 8082);
const baseURL = process.env["E2E_BASE_URL"] ?? `http://127.0.0.1:${port}`;
// `make e2e` derives this from the backend settings; no DSN literal lives here.
const databaseUrl = process.env["E2E_DATABASE_URL"] ?? "";
// The fixture learning root global-setup.ts fills with one captioned course.
const learningRoot = join(tmpdir(), "istari-e2e-learning");
if (!process.env["E2E_BASE_URL"] && !databaseUrl) {
  throw new Error("Set E2E_DATABASE_URL (`make e2e` does) or E2E_BASE_URL for a running app.");
}

export default defineConfig({
  testDir: "./tests/e2e",
  globalSetup: "./tests/e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env["CI"],
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  ...(process.env["E2E_BASE_URL"]
    ? {}
    : {
        // Two servers: the stub K16S exam server (tests/k16s_stub.py), then the API pointed
        // at it, so the verified-lab flow runs without a real cluster.
        webServer: [
          {
            command: `cd ../backend && uv run uvicorn tests.k16s_stub:app --host 127.0.0.1 --port ${stubPort}`,
            url: `http://127.0.0.1:${stubPort}/api/status`,
            reuseExistingServer: false,
            timeout: 60_000,
          },
          {
            command: `cd ../backend && DATABASE_URL='${databaseUrl}' STATIC_DIR=static K16S_BASE_URL=http://127.0.0.1:${stubPort} K16S_PUBLIC_URL=http://127.0.0.1:${stubPort} LEARNING_ROOT='${learningRoot}' LEARNING_TOPICS='Cloud/Testing' uv run uvicorn app.main:app --host 127.0.0.1 --port ${port}`,
            url: `${baseURL}/api/health`,
            reuseExistingServer: false,
            timeout: 60_000,
          },
        ],
      }),
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
    {
      name: "ultrawide",
      use: { ...devices["Desktop Chrome"], viewport: { width: 3440, height: 1440 } },
    },
  ],
});
