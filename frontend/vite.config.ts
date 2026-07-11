/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(), // Tailwind v4: CSS-first config via @tailwindcss/vite plugin
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Proxy API calls to FastAPI backend during development
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
    port: 5173,
  },
  build: {
    outDir: "dist",
    // Output goes to dist/ which is copied into backend/app/static/ in Docker build
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
    // Only collect Vitest component/unit tests under src/. Playwright specs live
    // in e2e/ and must not be collected by Vitest (they use @playwright/test).
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
