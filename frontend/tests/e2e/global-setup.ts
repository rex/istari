/* Prepares the isolated e2e database: migrate, seed the content packs, ensure an owner.
   Runs the same CLI an operator would, against TEST_DATABASE_URL (never the dev db). */

import { execFileSync } from "node:child_process";
import path from "node:path";

const backend = path.resolve(__dirname, "../../../backend");

// `make e2e` derives this from the backend settings (TEST_DATABASE_URL, or
// DATABASE_URL with `_test` appended). No DSN literal lives here on purpose.
const databaseUrl = process.env["E2E_DATABASE_URL"];
if (!databaseUrl) {
  throw new Error("E2E_DATABASE_URL is not set. Run `make e2e`, which derives it.");
}
export const E2E_DATABASE_URL: string = databaseUrl;
export const E2E_USERNAME = process.env["E2E_USERNAME"] ?? "e2e-owner";
export const E2E_PASSWORD = process.env["E2E_PASSWORD"] ?? "e2e-password-not-secret";

function run(args: string[], extraEnv: Record<string, string> = {}): string {
  return execFileSync("uv", ["run", ...args], {
    cwd: backend,
    env: { ...process.env, DATABASE_URL: E2E_DATABASE_URL, ...extraEnv },
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

export default function globalSetup(): void {
  run(["alembic", "downgrade", "base"]);
  run(["alembic", "upgrade", "head"]);
  run(["python", "-m", "app.cli", "seed"]);
  run(["python", "-m", "app.cli", "bootstrap-owner", "--username", E2E_USERNAME], {
    ISTARI_OWNER_PASSWORD: E2E_PASSWORD,
  });
}
