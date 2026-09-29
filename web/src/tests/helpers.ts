/// Playwright test helpers for the AERIS dashboard.
///
/// These are thin wrappers around Playwright's page object that reference the
/// CSS class names defined in src/styles/components.css. Keep them in sync
/// with the class names — if you rename a class, update the selector here.

import { type Page, type Locator } from "@playwright/test";

export function getSidebar(page: Page): Locator {
  return page.locator(".sidebar");
}

export function getPlaybackPill(page: Page): Locator {
  return page.locator(".playback-pill");
}

export function getPlaybackPillPlaying(page: Page): Locator {
  return getPlaybackPill(page).filter({ hasClass: "playback-pill--playing" });
}

export function getPlaybackPillPaused(page: Page): Locator {
  return getPlaybackPill(page).filter({ hasClass: "playback-pill--paused" });
}

export function getScenarioSelect(page: Page): Locator {
  return page.locator("#scenario-select");
}

export function getNoiseSlider(page: Page): Locator {
  return page.locator("#noise-slider");
}

export function getSeedInput(page: Page): Locator {
  return page.locator("#seed-input");
}

export function getDistanceSlider(page: Page): Locator {
  return page.locator("#distance-slider");
}

export function getTopbar(page: Page): Locator {
  return page.locator(".topbar");
}

export function getStatusBadge(page: Page): Locator {
  return page.locator(".status-badge");
}

export function getSimBanner(page: Page): Locator {
  return page.locator(".sim-banner");
}

export function getMissionControls(page: Page): Locator {
  return page.locator(".mission-controls");
}

export function getPlayButton(page: Page): Locator {
  return page.locator(".mission-controls__button--play");
}

export function getResetButton(page: Page): Locator {
  return page.locator(".mission-controls__button--reset");
}

export function getFlightDistanceDisplay(page: Page): Locator {
  return page.locator(".mission-controls__label");
}

export function getTelemetryChart(page: Page): Locator {
  return page.locator(".js-plotly-plot");
}

export function getMetricCards(page: Page): Locator {
  return page.locator(".metric-card");
}

export function getTabBar(page: Page): Locator {
  return page.locator(".tab-bar");
}

export function getTab(page: Page, tabId: string): Locator {
  return page.locator(`.tab-bar__tab[data-tab-id="${tabId}"]`);
}

export function getAINotice(page: Page): Locator {
  return page.locator(".ai-diagnostic-panel__note");
}

export function getAIDownloadButton(page: Page): Locator {
  return page.locator(".ai-diagnostic-panel__download");
}

export function getSettingsPanel(page: Page): Locator {
  return page.locator(".settings-panel");
}

export function getApiKeyInput(page: Page): Locator {
  return page.locator("#gemini-api-key");
}

export function getSaveKeyButton(page: Page): Locator {
  return page.locator(".settings-panel__button--primary");
}

export function getClearKeyButton(page: Page): Locator {
  return page.locator(".settings-panel__button--secondary");
}

export function getTestConnectionButton(page: Page): Locator {
  return page.locator(".settings-panel__button--test");
}

export function getConnectionStatus(page: Page): Locator {
  return page.locator(".settings-panel__status");
}
