import { defineConfig, devices } from "@playwright/test";

// RR-011 accessibility / E2E starter.
// The app must already be running. Point E2E_BASE_URL at the Vite dev server
// (http://localhost:5173) or the backend-served SPA (http://localhost:8000).
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
