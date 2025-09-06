import { Page, Locator, expect } from '@playwright/test';
import { API_CONFIG, PROJECT_DATA, PERFORMANCE_THRESHOLDS } from '../fixtures/test-data';

/**
 * Page Object Model helpers and utilities for E2E tests
 */

export class AppPage {
  constructor(public page: Page) {}

  // Navigation helpers
  async navigateToHome() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async waitForAppLoad() {
    await this.page.waitForSelector('[data-testid="app-layout"]', { timeout: 10000 });
    await this.page.waitForLoadState('domcontentloaded');
  }

  // API Configuration helpers
  async configureAPI(config = API_CONFIG.valid) {
    const settingsButton = this.page.locator('[data-testid="settings-button"]');
    await settingsButton.click();

    const apiKeyInput = this.page.locator('[data-testid="api-key-input"]');
    await apiKeyInput.fill(config.apiKey);

    const endpointInput = this.page.locator('[data-testid="endpoint-input"]');
    await endpointInput.fill(config.endpoint);

    const modelSelect = this.page.locator('[data-testid="model-select"]');
    await modelSelect.selectOption(config.model);

    const saveButton = this.page.locator('[data-testid="save-config-button"]');
    await saveButton.click();

    // Wait for success notification
    await this.page.waitForSelector('[data-testid="notification-success"]');
  }

  // Project management helpers
  async createNewProject(projectData = PROJECT_DATA.simple) {
    const newProjectButton = this.page.locator('[data-testid="new-project-button"]');
    await newProjectButton.click();

    const titleInput = this.page.locator('[data-testid="project-title-input"]');
    await titleInput.fill(projectData.title);

    const descriptionInput = this.page.locator('[data-testid="project-description-input"]');
    await descriptionInput.fill(projectData.description);

    const topicInput = this.page.locator('[data-testid="project-topic-input"]');
    await topicInput.fill(projectData.topic);

    const createButton = this.page.locator('[data-testid="create-project-button"]');
    await createButton.click();

    // Wait for project creation success
    await this.page.waitForSelector('[data-testid="project-created-success"]');
  }

  async loadProject(projectName: string) {
    const loadProjectButton = this.page.locator('[data-testid="load-project-button"]');
    await loadProjectButton.click();

    const projectOption = this.page.locator(`[data-testid="project-option-${projectName}"]`);
    await projectOption.click();

    const confirmButton = this.page.locator('[data-testid="confirm-load-button"]');
    await confirmButton.click();

    // Wait for project load success
    await this.page.waitForSelector('[data-testid="project-loaded-success"]');
  }

  // PPT creation workflow helpers
  async generateOutline() {
    const generateButton = this.page.locator('[data-testid="generate-outline-button"]');
    await generateButton.click();

    // Wait for outline generation with timeout
    await this.page.waitForSelector('[data-testid="outline-generated"]', { 
      timeout: PERFORMANCE_THRESHOLDS.apiResponse 
    });
  }

  async enhanceContent(sectionIndex: number = 0) {
    const enhanceButton = this.page.locator(`[data-testid="enhance-section-${sectionIndex}"]`);
    await enhanceButton.click();

    // Wait for content enhancement
    await this.page.waitForSelector(`[data-testid="section-enhanced-${sectionIndex}"]`, {
      timeout: PERFORMANCE_THRESHOLDS.apiResponse
    });
  }

  async searchImages(keyword: string) {
    const searchInput = this.page.locator('[data-testid="image-search-input"]');
    await searchInput.fill(keyword);

    const searchButton = this.page.locator('[data-testid="image-search-button"]');
    await searchButton.click();

    // Wait for image results
    await this.page.waitForSelector('[data-testid="image-results"]', {
      timeout: PERFORMANCE_THRESHOLDS.imageLoad
    });
  }

  async selectImages(count: number = 3) {
    const images = this.page.locator('[data-testid^="image-option-"]').first(count);
    
    for (let i = 0; i < count; i++) {
      const image = images.nth(i);
      await image.click();
    }

    const confirmButton = this.page.locator('[data-testid="confirm-image-selection"]');
    await confirmButton.click();
  }

  async generatePPT() {
    const generatePPTButton = this.page.locator('[data-testid="generate-ppt-button"]');
    await generatePPTButton.click();

    // Wait for PPT generation
    await this.page.waitForSelector('[data-testid="ppt-generated"]', {
      timeout: PERFORMANCE_THRESHOLDS.apiResponse * 2 // PPT generation takes longer
    });
  }

  async downloadPPT() {
    const downloadButton = this.page.locator('[data-testid="download-ppt-button"]');
    
    const downloadPromise = this.page.waitForEvent('download');
    await downloadButton.click();
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toContain('.pptx');
    
    return download;
  }

  // Assertion helpers
  async expectProjectToBeLoaded(projectName: string) {
    const projectTitle = this.page.locator('[data-testid="current-project-title"]');
    await expect(projectTitle).toContainText(projectName);
  }

  async expectOutlineToHaveSections(count: number) {
    const sections = this.page.locator('[data-testid^="outline-section-"]');
    await expect(sections).toHaveCount(count);
  }

  async expectImagesInGallery(minCount: number = 1) {
    const images = this.page.locator('[data-testid^="gallery-image-"]');
    await expect(images).toHaveCount(minCount, { timeout: 10000 });
  }

  async expectNotificationToShow(type: 'success' | 'error' | 'warning', message?: string) {
    const notification = this.page.locator(`[data-testid="notification-${type}"]`);
    await expect(notification).toBeVisible();
    
    if (message) {
      await expect(notification).toContainText(message);
    }
  }

  // Performance helpers
  async measurePageLoadTime(): Promise<number> {
    const navigationStart = await this.page.evaluate(() => 
      performance.timing.navigationStart
    );
    const loadComplete = await this.page.evaluate(() => 
      performance.timing.loadEventEnd
    );
    
    return loadComplete - navigationStart;
  }

  async measureAPIResponseTime(action: () => Promise<void>): Promise<number> {
    const start = Date.now();
    await action();
    const end = Date.now();
    
    return end - start;
  }

  // Cleanup helpers
  async clearLocalStorage() {
    await this.page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  }

  async resetApp() {
    await this.clearLocalStorage();
    await this.page.reload();
    await this.waitForAppLoad();
  }
}

export class ErrorScenarios {
  constructor(public page: Page) {}

  async simulateNetworkFailure() {
    await this.page.context().setOffline(true);
  }

  async simulateSlowNetwork() {
    await this.page.context().route('**/*', route => {
      setTimeout(() => route.continue(), 2000);
    });
  }

  async simulateAPIError(statusCode: number = 500) {
    await this.page.context().route('**/api/**', route => {
      route.fulfill({
        status: statusCode,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Simulated API error' }),
      });
    });
  }

  async restoreNetwork() {
    await this.page.context().setOffline(false);
    await this.page.context().unroute('**/*');
    await this.page.context().unroute('**/api/**');
  }
}

export class PerformanceMonitor {
  constructor(public page: Page) {}

  async startMonitoring() {
    await this.page.coverage?.startJSCoverage();
    await this.page.coverage?.startCSSCoverage();
  }

  async stopMonitoring() {
    const jsCoverage = await this.page.coverage?.stopJSCoverage();
    const cssCoverage = await this.page.coverage?.stopCSSCoverage();
    
    return { jsCoverage, cssCoverage };
  }

  async getPerformanceMetrics() {
    return await this.page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        dns: navigation.domainLookupEnd - navigation.domainLookupStart,
        tcp: navigation.connectEnd - navigation.connectStart,
        request: navigation.responseStart - navigation.requestStart,
        response: navigation.responseEnd - navigation.responseStart,
        domInteractive: navigation.domInteractive - navigation.navigationStart,
        domComplete: navigation.domComplete - navigation.navigationStart,
        loadEvent: navigation.loadEventEnd - navigation.loadEventStart,
      };
    });
  }
}