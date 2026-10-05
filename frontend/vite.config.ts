/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server binds to loopback only; /api is proxied to the FastAPI dev server.
// In production the built SPA is served by FastAPI itself (same origin).
export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
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
