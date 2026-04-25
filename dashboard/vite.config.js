import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(() => {
  const apiTarget = process.env.VITE_API_URL || "http://localhost:8000";
  const ingestionTarget = process.env.VITE_INGESTION_URL || "http://localhost:8080";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
        "/ws": {
          target: apiTarget,
          ws: true,
          changeOrigin: true,
        },
        "/ingest": {
          target: ingestionTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
