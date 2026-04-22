import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies every triage4 backend endpoint to the FastAPI
// service on http://127.0.0.1:8000. Keeps frontend + backend on the
// same origin (localhost:5173), so browser CORS never rejects
// anything. Override the backend target with the env var
// TRIAGE4_API_TARGET (e.g. when running the backend on a different
// host or port).
//
// Vite prefix-matches these paths, so "/casualties" also covers
// "/casualties/C1", "/casualties/C1/twin", "/casualties/C1/skeletal",
// etc. — every sub-route of a listed prefix is proxied.
const BACKEND_TARGET = process.env.TRIAGE4_API_TARGET || "http://127.0.0.1:8000";

const BACKEND_PATHS = [
  // base
  "/health",
  "/metrics",
  "/casualties",       // + all sub-routes (/twin, /skeletal, /marker, etc.)
  "/graph",
  "/map",
  "/replay",
  "/tasks",
  "/export.html",
  // Tier 1
  "/mission",          // /mission/status
  "/forecast",         // /forecast/casualty/{id}, /forecast/mission
  "/evaluation",       // /evaluation/scorecard
  // Tier 3
  "/overview",
  // Final
  "/sensing",          // /sensing/ranked
];

const proxy: Record<string, { target: string; changeOrigin: boolean }> = {};
for (const path of BACKEND_PATHS) {
  proxy[path] = { target: BACKEND_TARGET, changeOrigin: true };
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy
  }
});
