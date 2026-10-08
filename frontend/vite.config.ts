/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

/** Build stamp for the footer badge: `make docker-build` sets GIT_COMMIT, a checkout supplies it. */
function webCommit(): string {
  const fromEnv = process.env["GIT_COMMIT"]?.trim();
  if (fromEnv) return fromEnv;
  try {
    const out = execFileSync("git", ["rev-parse", "--short", "HEAD"], {
      stdio: ["ignore", "pipe", "ignore"],
    });
    return out.toString().trim() || "unknown";
  } catch {
    return "unknown";
  }
}

function webVersion(): string {
  try {
    return readFileSync(new URL("../VERSION", import.meta.url), "utf8").trim() || "0.0.0";
  } catch {
    return "0.0.0";
  }
}

// Dev server binds to loopback only; /api is proxied to the FastAPI dev server.
// In production the built SPA is served by FastAPI itself (same origin).
export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
  define: {
    __WEB_VERSION__: JSON.stringify(webVersion()),
    __WEB_COMMIT__: JSON.stringify(webCommit()),
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
  preview: { host: "127.0.0.1", port: 4173 },
  build: {
    target: "es2022",
    sourcemap: true,
    // Route pages are lazy (see src/router.tsx); the bundler's default chunking
    // keeps vendor code in its own chunk.
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/unit/**/*.test.ts", "tests/component/**/*.test.tsx"],
    css: { modules: { classNameStrategy: "non-scoped" } },
  },
});
