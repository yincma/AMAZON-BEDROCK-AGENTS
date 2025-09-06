import { test, expect } from '@playwright/test';
import { AppPage } from '../utils/test-helpers';
import { API_CONFIG, PERFORMANCE_THRESHOLDS } from '../fixtures/test-data';

test.describe('First-time User Experience', () => {
  let appPage: AppPage;

  test.beforeEach(async ({ page }) => {
    appPage = new AppPage(page);
    // Clear any existing data to simulate first-time user
    await appPage.clearLocalStorage();
    await appPage.navigateToHome();
    await appPage.waitForAppLoad();
  });

  test('should show welcome screen for first-time users', async ({ page }) => {
    // Verify welcome screen is displayed
    const welcomeScreen = page.locator('[data-testid="welcome-screen"]');
    await expect(welcomeScreen).toBeVisible();

    const welcomeTitle = page.locator('[data-testid="welcome-title"]');
    await expect(welcomeTitle).toContainText('Welcome to AI PPT Generator');

    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await expect(getStartedButton).toBeVisible();
  });

  test('should guide user through API configuration setup', async ({ page }) => {
    // Click get started
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await getStartedButton.click();

    // Should show API configuration step
    const configStep = page.locator('[data-testid="config-step"]');
    await expect(configStep).toBeVisible();

    const stepTitle = page.locator('[data-testid="step-title"]');
    await expect(stepTitle).toContainText('Configure API Settings');

    // Fill API configuration
    await appPage.configureAPI(API_CONFIG.valid);

    // Should proceed to next step or show success
    const successMessage = page.locator('[data-testid="config-success"]');
    await expect(successMessage).toBeVisible();
  });

  test('should validate API configuration before proceeding', async ({ page }) => {
    // Start configuration
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await getStartedButton.click();

    // Try with invalid configuration
    const apiKeyInput = page.locator('[data-testid="api-key-input"]');
    await apiKeyInput.fill('');

    const saveButton = page.locator('[data-testid="save-config-button"]');
    await saveButton.click();

    // Should show validation error
    const errorMessage = page.locator('[data-testid="validation-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('API key is required');

    // Try with valid configuration
    await apiKeyInput.fill(API_CONFIG.valid.apiKey);
    
    const endpointInput = page.locator('[data-testid="endpoint-input"]');
    await endpointInput.fill(API_CONFIG.valid.endpoint);

    await saveButton.click();

    // Should succeed
    const successMessage = page.locator('[data-testid="config-success"]');
    await expect(successMessage).toBeVisible();
  });

  test('should create first project after configuration', async ({ page }) => {
    // Complete API configuration
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await getStartedButton.click();
    
    await appPage.configureAPI(API_CONFIG.valid);

    // Should show project creation step
    const projectStep = page.locator('[data-testid="project-step"]');
    await expect(projectStep).toBeVisible();

    const createProjectButton = page.locator('[data-testid="create-first-project-button"]');
    await createProjectButton.click();

    // Fill project details
    const titleInput = page.locator('[data-testid="project-title-input"]');
    await titleInput.fill('My First Presentation');

    const descriptionInput = page.locator('[data-testid="project-description-input"]');
    await descriptionInput.fill('This is my first AI-generated presentation');

    const topicInput = page.locator('[data-testid="project-topic-input"]');
    await topicInput.fill('Introduction to AI');

    const createButton = page.locator('[data-testid="create-project-button"]');
    await createButton.click();

    // Should show project creation success
    const successMessage = page.locator('[data-testid="project-created-success"]');
    await expect(successMessage).toBeVisible();

    // Should navigate to main application
    const mainApp = page.locator('[data-testid="main-app"]');
    await expect(mainApp).toBeVisible();

    // Verify project is loaded
    await appPage.expectProjectToBeLoaded('My First Presentation');
  });

  test('should show tutorial hints for first-time users', async ({ page }) => {
    // Complete initial setup
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await getStartedButton.click();
    
    await appPage.configureAPI(API_CONFIG.valid);
    await appPage.createNewProject();

    // Should show tutorial overlay or hints
    const tutorialHint = page.locator('[data-testid="tutorial-hint"]');
    await expect(tutorialHint).toBeVisible();

    const nextHintButton = page.locator('[data-testid="next-hint-button"]');
    await expect(nextHintButton).toBeVisible();

    // Click through tutorial
    await nextHintButton.click();

    // Should show next hint
    const secondHint = page.locator('[data-testid="tutorial-hint-2"]');
    await expect(secondHint).toBeVisible();

    // Skip tutorial
    const skipButton = page.locator('[data-testid="skip-tutorial-button"]');
    await skipButton.click();

    // Tutorial should be dismissed
    await expect(tutorialHint).not.toBeVisible();
  });

  test('should remember user preferences after initial setup', async ({ page }) => {
    // Complete initial setup
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await getStartedButton.click();
    
    await appPage.configureAPI(API_CONFIG.valid);
    await appPage.createNewProject();

    // Refresh page
    await page.reload();
    await appPage.waitForAppLoad();

    // Should not show welcome screen again
    const welcomeScreen = page.locator('[data-testid="welcome-screen"]');
    await expect(welcomeScreen).not.toBeVisible();

    // Should load main app directly
    const mainApp = page.locator('[data-testid="main-app"]');
    await expect(mainApp).toBeVisible();

    // Should have saved API configuration
    const settingsButton = page.locator('[data-testid="settings-button"]');
    await settingsButton.click();

    const apiKeyInput = page.locator('[data-testid="api-key-input"]');
    await expect(apiKeyInput).toHaveValue(API_CONFIG.valid.apiKey);
  });

  test('should handle first-time user experience on mobile devices', async ({ page, isMobile }) => {
    // Skip if not mobile
    test.skip(!isMobile, 'This test is for mobile devices only');

    // Verify mobile-optimized welcome screen
    const welcomeScreen = page.locator('[data-testid="welcome-screen"]');
    await expect(welcomeScreen).toBeVisible();

    // Check mobile-specific elements
    const mobileMenu = page.locator('[data-testid="mobile-menu-button"]');
    await expect(mobileMenu).toBeVisible();

    // Continue with mobile setup flow
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    await getStartedButton.click();

    // API configuration should work on mobile
    await appPage.configureAPI(API_CONFIG.valid);

    // Verify mobile navigation
    const bottomNav = page.locator('[data-testid="bottom-navigation"]');
    await expect(bottomNav).toBeVisible();
  });

  test('should meet performance requirements during first-time setup', async ({ page }) => {
    // Measure page load time
    const loadTime = await appPage.measurePageLoadTime();
    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.pageLoad);

    // Measure setup flow performance
    const getStartedButton = page.locator('[data-testid="get-started-button"]');
    
    const setupTime = await appPage.measureAPIResponseTime(async () => {
      await getStartedButton.click();
      await appPage.configureAPI(API_CONFIG.valid);
    });

    expect(setupTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse);
  });
});