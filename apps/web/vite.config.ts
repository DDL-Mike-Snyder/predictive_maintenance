import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// 51-operator-console.md §2: "base baked at build" [50 §6.1]. VITE_BASE_URL
// is the one build-time exception to 09 §4.5's "config.py/settings is the
// only environment reader" rule -- there is no server-side config.py for a
// static SPA, so the base path is the one thing Vite itself must resolve at
// build time (everything else this app reads, e.g. the gateway's own origin,
// is same-origin at runtime and needs no separate config).
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE_URL ?? "/",
  // Vite emits hashed JS/CSS under `<assetsDir>/` (default "assets"). Behind
  // Domino's *workspace* proxy the edge reserves the `/assets/` path segment
  // for its own frontend and never forwards `.../proxy/<port>/assets/...` to
  // the app -- so those requests come back as Domino's own HTML/404, not our
  // bundle. Overriding VITE_ASSETS_DIR to a non-colliding name (the workspace
  // entrypoint sets it) dodges that. Default stays "assets" so the Domino
  // *App* deploy (/apps-internal/<appId>/, which does not reserve it) is
  // unchanged.
  build: { assetsDir: process.env.VITE_ASSETS_DIR ?? "assets" },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
  server: {
    proxy: {
      // Dev-only: apps/web talks to the gateway same-origin in every real
      // deployment (30-gateway.md's BFF shape assumes this); `vite dev`
      // needs an explicit proxy to get the same same-origin cookie behavior
      // against a gateway running on a different port locally.
      "/api": {
        target: process.env.VITE_DEV_GATEWAY_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
