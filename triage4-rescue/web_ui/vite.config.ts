import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies the FastAPI backend (default
// http://127.0.0.1:8000). Override with the env var
// TRIAGE4_RESCUE_API_TARGET to point at a remote backend.
const BACKEND_TARGET =
  process.env.TRIAGE4_RESCUE_API_TARGET || "http://127.0.0.1:8000";

const BACKEND_PATHS = [
  "/health",
  "/incident",
  "/casualties",   // + /casualties/{id}
  "/alerts",
  "/demo",         // + /demo/reload
  "/export.html",,
  "/camera"
];

const proxy: Record<string, { target: string; changeOrigin: boolean }> = {};
for (const path of BACKEND_PATHS) {
  proxy[path] = { target: BACKEND_TARGET, changeOrigin: true };
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy,
  },
});
