import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./src/tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // webServer: optional — spin up the Vite dev server and the snapshot API
  // automatically for local tests. Uncomment and configure when you have both
  // services running locally.
  //
  // webServer: [
  //   {
  //     command: "npm run dev",
  //     url: "http://localhost:5173",
  //     reuseExistingServer: !process.env.CI,
  //   },
  //   {
  //     command: "PYTHONPATH=. uvicorn snapshot_api.app.main:api --host 0.0.0.0 --port 8000",
  //     url: "http://localhost:8000/health",
  //     reuseExistingServer: !process.env.CI,
  //   },
  // ],
});
