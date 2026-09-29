/// Playwright E2E tests for the AERIS dashboard.
///
/// These tests run against a running snapshot API (the FastAPI service in
/// snapshot_api/). Set the API URL via the VITE_API_BASE_URL env var or the
/// PLAYWRIGHT_API_BASE_URL env var (which overrides the Vite build-time value
/// for test runs).
///
/// Prerequisites:
/// - Node 18+
/// - A running snapshot API at the configured base URL
/// - Playwright browsers installed: `npx playwright install`
///
/// Run:
///   npx playwright test
///
/// With a specific API URL:
///   PLAYWRIGHT_API_BASE_URL=http://localhost:8000 npx playwright test

import { test, expect } from "@playwright/test";
import {
  getScenarioSelect,
  getPlaybackPill,
  getPlaybackPillPlaying,
  getPlaybackPillPaused,
  getMissionControls,
  getPlayButton,
  getResetButton,
  getFlightDistanceDisplay,
  getTelemetryChart,
  getMetricCards,
  getSimBanner,
  getStatusBadge,
  getTopbar,
  getAINotice,
  getSettingsPanel,
  getApiKeyInput,
  getSaveKeyButton,
  getClearKeyButton,
  getTestConnectionButton,
  getConnectionStatus,
} from "./helpers";

// The base URL of the deployed (or local) dashboard. In CI, this would be the
// Supabase Storage site URL; for local dev, it's the Vite dev server.
const BASE_URL =
  process.env.PLAYWRIGHT_BASE_URL ??
  process.env.VITE_API_BASE_URL?.replace("http://localhost:8000", "http://localhost:5173") ??
  "http://localhost:5173";

// The base URL of the snapshot API (used by the dashboard).
// The Playwright test server loads the React app with this env var embedded.
const API_BASE_URL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://localhost:8000";

test.describe("AERIS Dashboard — E2E", () => {
  test.describe("load and initial state", () => {
    test("page loads without error", async ({ page }) => {
      // The dashboard embeds the API base URL at build time via Vite. For
      // tests, we override it by setting the env var before building, or we
      // run the dev server with the env var set.
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      await expect(page.locator(".layout")).toBeVisible();
      await expect(page.locator(".sidebar__title h1")).toHaveText("AERIS");
    });

    test("simulation banner is visible on load", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
      await expect(getSimBanner(page)).toBeVisible();
      await expect(getSimBanner(page).locator(".sim-banner__label")).toHaveText("SIMULATION");
    });

    test("playback pill shows paused state initially", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
      await expect(getPlaybackPillPaused(page)).toBeVisible();
      await expect(getPlaybackPillPlaying(page)).not.toBeVisible();
    });

    test("scenario select defaults to Auto guided tour", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
      await expect(getScenarioSelect(page)).toHaveValue("AUTO_SCENARIO");
    });

    test("snapshot API is called on load", async ({ page }) => {
      // Instrument the fetch to verify the snapshot endpoint is called.
      const responses: string[] = [];
      await page.route("**/api/snapshot", (route) => {
        responses.push(route.request().url());
        route.continue();
      });

      await page.goto(BASE_URL, { waitUntil: "networkidle" });

      expect(responses.length).toBeGreaterThan(0);
    });
  });

  test.describe("mission controls", () => {
    test("play button starts playback", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
      await expect(getPlaybackPillPaused(page)).toBeVisible();

      await page.click(getPlayButton(page));
      await expect(getPlaybackPillPlaying(page)).toBeVisible();

      // Play a few seconds, then pause.
      await page.waitForTimeout(2500);
      await page.click(getPlayButton(page));
      await expect(getPlaybackPillPaused(page)).toBeVisible();
    });

    test("reset returns to start", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      // Advance a bit.
      await page.click(getPlayButton(page));
      await page.waitForTimeout(2000);
      await page.click(getPlayButton(page));

      const distanceBefore = await getFlightDistanceDisplay(page).textContent();
      expect(distanceBefore).toContain("km");

      await page.click(getResetButton(page));
      const distanceAfter = await getFlightDistanceDisplay(page).textContent();
      expect(distanceAfter).toContain("0.0 km");
    });

    test("scrubber advances the mission", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      const distanceSlider = page.locator("#distance-slider");
      await distanceSlider.fill("150");
      await page.expect(page.locator(".mission-controls__label")).toContainText("150");

      // The snapshot should have been re-fetched at 150 km.
      await expect(getTelemetryChart(page)).toBeVisible();
    });
  });

  test.describe("scenario switching", () => {
    test("switching scenario re-fetches the snapshot", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      const [request] = await Promise.all([
        page.waitForRequest("**/api/snapshot"),
        getScenarioSelect(page).selectOption(
          "6. Oil Pressure Loss / Lubrication Degradation",
        ),
      ]);

      expect(request).toBeTruthy();
    });

    test("status badge reflects scenario", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      // The Auto scenario at 140 km should be in cruise with normal status
      // (depends on the engine; this test just verifies the badge is visible).
      await expect(getStatusBadge(page)).toBeVisible();
    });
  });

  test.describe("telemetry chart", () => {
    test("chart renders after snapshot loads", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await expect(getTelemetryChart(page)).toBeVisible();
      await expect(getTelemetryChart(page)).toBeVisible();
    });

    test("metric cards are populated", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      const cards = page.locator(".metric-card");
      await expect(cards).toHaveCount(6);
    });
  });

  test.describe("AI diagnostics tab", () => {
    test("AI diagnostics tab shows placeholder when no review", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      // Switch to the AI tab.
      await page.locator(".tab-bar__tab").filter({ hasText: "AI Diagnostics" }).click();
      await expect(getAINotice(page)).toBeVisible();
    });

    test("generating a review produces local fallback", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "networkidle" });

      await page.locator(".tab-bar__tab").filter({ hasText: "AI Diagnostics" }).click();

      await page.click("text=Generate Telemetry Review");
      await page.waitForSelector(".ai-diagnostic-panel__badge", { state: "visible" });

      const badge = page.locator(".ai-diagnostic-panel__badge");
      await expect(badge).toContainText("Local fallback summary");
    });

    test("downloading a review produces a markdown file", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "networkidle" });

      await page.locator(".tab-bar__tab").filter({ hasText: "AI Diagnostics" }).click();
      await page.click("text=Generate Telemetry Review");
      await page.waitForSelector(".ai-diagnostic-panel__badge", { state: "visible" });

      const [download] = await Promise.all([
        page.waitForEvent("download"),
        page.click("text=Download Review"),
      ]);

      expect(download.suggestedFilename()).toMatch(/areis-review-.*\.md$/);
    });
  });

  test.describe("settings panel", () => {
    test("settings tab is accessible", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      await page.locator(".tab-bar__tab").filter({ hasText: "Settings" }).click();
      await expect(getSettingsPanel(page)).toBeVisible();
    });

    test("saving an API key updates the input state", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      await page.locator(".tab-bar__tab").filter({ hasText: "Settings" }).click();
      await getApiKeyInput(page).fill("test-key-12345");
      await page.click(getSaveKeyButton(page));

      // The key is kept in memory (not persisted to disk in the demo).
      await expect(getApiKeyInput(page)).toHaveValue("test-key-12345");
    });

    test("clearing the key resets the input", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      await page.locator(".tab-bar__tab").filter({ hasText: "Settings" }).click();
      await getApiKeyInput(page).fill("test-key-12345");
      await page.click(getSaveKeyButton(page));
      await page.click(getClearKeyButton(page));

      await expect(getApiKeyInput(page)).toHaveValue("");
    });

    test("connection test button is present", async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      await page.locator(".tab-bar__tab").filter({ hasText: "Settings" }).click();
      await expect(getTestConnectionButton(page)).toBeVisible();
    });
  });

  test.describe("cors and network error handling", () => {
    test("dashboard shows error when API is unreachable", async ({ page }) => {
      // Point the dashboard at an unreachable API URL by overriding the env
      // var for this test. This requires the test server to be built with the
      // override — in practice you'd set VITE_API_BASE_URL before running the
      // dev server. Here we simulate by intercepting the snapshot request and
      // returning an error.
      await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });

      await page.route("**/api/snapshot", (route) => {
        route.abort("failed");
      });

      // Wait for the dashboard to attempt a fetch and show the error.
      await expect(
        page.locator(".panel--error"),
      ).toBeVisible({ timeout: 10_000 });
    });
  });
});
