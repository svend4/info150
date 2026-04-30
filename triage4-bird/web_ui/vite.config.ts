import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND_TARGET =
  process.env.TRIAGE4_BIRD_API_TARGET || "http://127.0.0.1:8000";

const BACKEND_PATHS = [
  "/health", "/report", "/observations", "/alerts", "/demo", "/export.html",
];

const proxy: Record<string, { target: string; changeOrigin: boolean }> = {};
for (const p of BACKEND_PATHS) proxy[p] = { target: BACKEND_TARGET, changeOrigin: true };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
});
