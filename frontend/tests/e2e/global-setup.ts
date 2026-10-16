/* Prepares the isolated e2e database: migrate, seed the content packs, ensure an owner.
   Runs the same CLI an operator would, against TEST_DATABASE_URL (never the dev db). */

import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const backend = fileURLToPath(new URL("../../../backend", import.meta.url));

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
  // The fixture pack adds two verified labs graded by the stub K16S (never shipped).
  const fixture = join(tmpdir(), "istari-e2e-fixture-pack.json");
  writeFileSync(
    fixture,
    run([
      "python",
      "-c",
      "import json; from tests.fixtures import mini_pack; print(json.dumps(mini_pack()))",
    ]),
  );
  run(["python", "-m", "app.cli", "import-pack", fixture]);
  run(["python", "-m", "app.cli", "bootstrap-owner", "--username", E2E_USERNAME], {
    ISTARI_OWNER_PASSWORD: E2E_PASSWORD,
  });
  // A one-lecture course on the fixture track, so the lecture index has something to read.
  // playwright.config.ts points the API's LEARNING_ROOT at the same folder.
  const course = join(
    tmpdir(),
    "istari-e2e-learning",
    "Cloud",
    "Testing",
    "Mapping Course 2024 [TST-C01]",
    "01 - IAM",
  );
  mkdirSync(course, { recursive: true });
  writeFileSync(join(course, "001 Roles and least privilege obj-1-1.mp4"), Buffer.alloc(1024));
  writeFileSync(
    join(course, "001 Roles and least privilege obj-1-1.srt"),
    "1\n00:00:01,000 --> 00:00:04,000\nIAM roles and least privilege.\n\n" +
      "2\n00:00:04,000 --> 00:00:08,500\nA role hands out temporary credentials through STS.\n",
  );
}
