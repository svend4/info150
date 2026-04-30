import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND_TARGET =
  process.env.TRIAGE4_FISH_API_TARGET || "http://127.0.0.1:8000";

const BACKEND_PATHS = [
  "/health",
  "/report",
  "/pens",         // + /pens/{id}
  "/alerts",
  "/demo",         // + /demo/reload
  "/export.html",
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
