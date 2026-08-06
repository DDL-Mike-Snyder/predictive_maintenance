import { defineConfig } from "vite";
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
