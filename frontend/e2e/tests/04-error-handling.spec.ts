import { test, expect } from '@playwright/test';
import { AppPage, ErrorScenarios } from '../utils/test-helpers';
import { API_CONFIG, PROJECT_DATA, ERROR_SCENARIOS } from '../fixtures/test-data';

test.describe('Error Handling and Edge Cases', () => {
  let appPage: AppPage;
  let errorScenarios: ErrorScenarios;

  test.beforeEach(async ({ page }) => {
    appPage = new AppPage(page);
    errorScenarios = new ErrorScenarios(page);
    await appPage.navigateToHome();
    await appPage.waitForAppLoad();
  });

  test.describe('API Configuration Errors', () => {
    test('should handle invalid API credentials', async ({ page }) => {
      // Try to configure with invalid credentials
      await appPage.configureAPI(API_CONFIG.invalid);

      // Should show API validation error
      await appPage.expectNotificationToShow('error', 'Invalid API credentials');

      // Should not allow proceeding without valid config
      const generateButton = page.locator('[data-testid="generate-outline-button"]');
      await expect(generateButton).toBeDisabled();

      // Verify error state in UI
      const apiStatus = page.locator('[data-testid="api-status"]');
      await expect(apiStatus).toHaveClass(/error/);
    });

    test('should handle API endpoint connectivity issues', async ({ page }) => {
      // Simulate network issues
      await errorScenarios.simulateAPIError(503);

      await appPage.configureAPI(API_CONFIG.valid);

      // Should show connection error
      await appPage.expectNotificationToShow('error', 'Unable to connect to API endpoint');

      // Should provide retry option
      const retryButton = page.locator('[data-testid="retry-api-config"]');
      await expect(retryButton).toBeVisible();

      // Test retry functionality
      await errorScenarios.restoreNetwork();
      await retryButton.click();

      // Should succeed after network restoration
      await appPage.expectNotificationToShow('success', 'API configured successfully');
    });

    test('should handle API rate limiting', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Simulate rate limiting
      await errorScenarios.simulateAPIError(429);

      const generateButton = page.locator('[data-testid="generate-outline-button"]');
      await generateButton.click();

      // Should show rate limit error
      await appPage.expectNotificationToShow('error', 'Rate limit exceeded. Please try again later.');

      // Should show retry timer
      const retryTimer = page.locator('[data-testid="retry-timer"]');
      await expect(retryTimer).toBeVisible();

      // Should automatically retry after timer
      await errorScenarios.restoreNetwork();
      
      // Wait for automatic retry
      await page.waitForSelector('[data-testid="outline-generated"]', { timeout: 30000 });
      await appPage.expectNotificationToShow('success', 'Outline generated successfully');
    });
  });

  test.describe('Network Connectivity Issues', () => {
    test('should handle offline scenarios', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Go offline
      await errorScenarios.simulateNetworkFailure();

      const generateButton = page.locator('[data-testid="generate-outline-button"]');
      await generateButton.click();

      // Should show offline notification
      await appPage.expectNotificationToShow('error', 'No internet connection detected');

      // Should show offline indicator
      const offlineIndicator = page.locator('[data-testid="offline-indicator"]');
      await expect(offlineIndicator).toBeVisible();

      // Should queue the operation
      const queuedOps = page.locator('[data-testid="queued-operations"]');
      await expect(queuedOps).toContainText('1 operation queued');

      // Restore network
      await errorScenarios.restoreNetwork();

      // Should automatically process queued operations
      await page.waitForSelector('[data-testid="outline-generated"]', { timeout: 15000 });
      await appPage.expectNotificationToShow('success', 'Outline generated successfully');
    });

    test('should handle slow network conditions', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Simulate slow network
      await errorScenarios.simulateSlowNetwork();

      const generateButton = page.locator('[data-testid="generate-outline-button"]');
      await generateButton.click();

      // Should show loading state
      const loadingIndicator = page.locator('[data-testid="loading-indicator"]');
      await expect(loadingIndicator).toBeVisible();

      // Should show progress information
      const progressText = page.locator('[data-testid="progress-text"]');
      await expect(progressText).toContainText('Generating outline...');

      // Should show cancel option for long operations
      const cancelButton = page.locator('[data-testid="cancel-operation"]');
      await expect(cancelButton).toBeVisible();

      // Wait for operation to complete despite slow network
      await page.waitForSelector('[data-testid="outline-generated"]', { timeout: 30000 });
    });

    test('should handle network timeouts', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Simulate very slow network that will timeout
      await page.context().route('**/api/**', route => {
        // Don't respond, causing timeout
        setTimeout(() => route.abort(), 30000);
      });

      const generateButton = page.locator('[data-testid="generate-outline-button"]');
      await generateButton.click();

      // Should show timeout error
      await appPage.expectNotificationToShow('error', 'Request timed out');

      // Should provide retry option
      const retryButton = page.locator('[data-testid="retry-operation"]');
      await expect(retryButton).toBeVisible();

      // Restore network and retry
      await errorScenarios.restoreNetwork();
      await retryButton.click();

      // Should succeed on retry
      await page.waitForSelector('[data-testid="outline-generated"]', { timeout: 15000 });
    });
  });

  test.describe('Input Validation Errors', () => {
    test('should validate project input fields', async ({ page }) => {
      const newProjectButton = page.locator('[data-testid="new-project-button"]');
      await newProjectButton.click();

      // Test empty title
      const createButton = page.locator('[data-testid="create-project-button"]');
      await createButton.click();

      let errorMessage = page.locator('[data-testid="title-error"]');
      await expect(errorMessage).toContainText('Project title is required');

      // Test title too long
      const titleInput = page.locator('[data-testid="project-title-input"]');
      await titleInput.fill(ERROR_SCENARIOS.validation.longTitle);
      await createButton.click();

      errorMessage = page.locator('[data-testid="title-error"]');
      await expect(errorMessage).toContainText('Title must be less than 100 characters');

      // Test empty description
      await titleInput.fill('Valid Title');
      await createButton.click();

      errorMessage = page.locator('[data-testid="description-error"]');
      await expect(errorMessage).toContainText('Project description is required');

      // Test valid input
      const descriptionInput = page.locator('[data-testid="project-description-input"]');
      await descriptionInput.fill('Valid description');

      const topicInput = page.locator('[data-testid="project-topic-input"]');
      await topicInput.fill('Valid topic');

      await createButton.click();

      // Should succeed
      await appPage.expectNotificationToShow('success', 'Project created successfully');
    });

    test('should validate image search input', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Test empty search
      const searchInput = page.locator('[data-testid="image-search-input"]');
      const searchButton = page.locator('[data-testid="image-search-button"]');

      await searchInput.fill('');
      await searchButton.click();

      const errorMessage = page.locator('[data-testid="search-error"]');
      await expect(errorMessage).toContainText('Please enter a search keyword');

      // Test very short search
      await searchInput.fill('a');
      await searchButton.click();

      await expect(errorMessage).toContainText('Search keyword must be at least 2 characters');

      // Test inappropriate content detection
      await searchInput.fill('inappropriate-content');
      await searchButton.click();

      await expect(errorMessage).toContainText('Search term not allowed');
    });

    test('should handle special characters in input', async ({ page }) => {
      // Test project creation with special characters
      await appPage.createNewProject(PROJECT_DATA.special_chars);

      // Should handle special characters properly
      await appPage.expectProjectToBeLoaded(PROJECT_DATA.special_chars.title);

      // Test outline generation with special characters
      await appPage.generateOutline();

      // Should work without issues
      const outline = page.locator('[data-testid^="outline-section-"]');
      await expect(outline.first()).toBeVisible();
    });
  });

  test.describe('Storage and Resource Limits', () => {
    test('should handle local storage quota exceeded', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);

      // Fill up local storage (simulate quota exceeded)
      await page.evaluate(() => {
        try {
          const largeData = 'x'.repeat(1024 * 1024); // 1MB chunks
          for (let i = 0; i < 10; i++) {
            localStorage.setItem(`large-data-${i}`, largeData);
          }
        } catch (e) {
          // Expected to throw quota exceeded error
        }
      });

      // Try to create project (should trigger storage error)
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Should show storage error
      await appPage.expectNotificationToShow('error', 'Storage quota exceeded');

      // Should offer cleanup options
      const cleanupButton = page.locator('[data-testid="cleanup-storage"]');
      await expect(cleanupButton).toBeVisible();

      // Test cleanup functionality
      await cleanupButton.click();

      const confirmCleanup = page.locator('[data-testid="confirm-cleanup"]');
      await confirmCleanup.click();

      // Should free up space and retry
      await appPage.expectNotificationToShow('success', 'Storage cleaned up successfully');
      await appPage.expectNotificationToShow('success', 'Project created successfully');
    });

    test('should handle large project data', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.complex);

      // Generate large amounts of content
      await appPage.generateOutline();

      // Enhance all sections (creates large content)
      const sectionCount = 5;
      for (let i = 0; i < sectionCount; i++) {
        await appPage.enhanceContent(i);
      }

      // Add many images
      await appPage.searchImages('technology');
      await appPage.selectImages(10);

      // Should handle large project without issues
      await appPage.expectImagesInGallery(10);

      // Test project save with large data
      const saveButton = page.locator('[data-testid="save-progress-button"]');
      await saveButton.click();

      await appPage.expectNotificationToShow('success', 'Progress saved');

      // Test project export with large data
      const exportButton = page.locator('[data-testid="export-project-button"]');
      const downloadPromise = page.waitForEvent('download');
      await exportButton.click();

      const download = await downloadPromise;
      expect(download.suggestedFilename()).toMatch(/.*\.json$/);
    });
  });

  test.describe('Concurrent Operations', () => {
    test('should handle multiple simultaneous API calls', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.complex);
      await appPage.generateOutline();

      // Start multiple enhancement operations simultaneously
      const enhanceButtons = page.locator('[data-testid^="enhance-section-"]');
      const buttonCount = await enhanceButtons.count();

      // Click all enhance buttons rapidly
      for (let i = 0; i < Math.min(buttonCount, 3); i++) {
        await enhanceButtons.nth(i).click({ delay: 100 });
      }

      // Should handle concurrent requests gracefully
      // Wait for all operations to complete
      for (let i = 0; i < Math.min(buttonCount, 3); i++) {
        await page.waitForSelector(`[data-testid="enhanced-badge-${i}"]`, { timeout: 20000 });
      }

      // Should not show any errors
      const errorNotification = page.locator('[data-testid="notification-error"]');
      await expect(errorNotification).not.toBeVisible();
    });

    test('should handle race conditions in project operations', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      
      // Start project creation and immediately try to load another project
      const createPromise = appPage.createNewProject(PROJECT_DATA.simple);
      
      // This should be queued or handled gracefully
      const loadButton = page.locator('[data-testid="load-project-button"]');
      await loadButton.click({ timeout: 1000 }).catch(() => {
        // Expected to fail or be disabled during creation
      });

      // Wait for creation to complete
      await createPromise;

      // Should be in stable state
      await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);
    });
  });

  test.describe('Browser and Device Specific Issues', () => {
    test('should handle browser refresh during operations', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Start outline generation
      const generateButton = page.locator('[data-testid="generate-outline-button"]');
      await generateButton.click();

      // Refresh page during operation
      await page.reload();
      await appPage.waitForAppLoad();

      // Should recover gracefully
      const recoveringIndicator = page.locator('[data-testid="recovering-state"]');
      if (await recoveringIndicator.isVisible({ timeout: 5000 })) {
        await expect(recoveringIndicator).not.toBeVisible({ timeout: 10000 });
      }

      // Should restore project state
      await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);
    });

    test('should handle small viewport sizes', async ({ page }) => {
      // Set very small viewport
      await page.setViewportSize({ width: 320, height: 568 });

      await appPage.navigateToHome();
      await appPage.waitForAppLoad();

      // Should adapt to small screen
      const mobileLayout = page.locator('[data-testid="mobile-layout"]');
      await expect(mobileLayout).toBeVisible();

      // Test functionality on small screen
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Mobile-specific UI should work
      const mobileMenu = page.locator('[data-testid="mobile-menu"]');
      await expect(mobileMenu).toBeVisible();

      // Core functionality should work
      await appPage.generateOutline();
      await appPage.expectOutlineToHaveSections(3);
    });

    test('should handle memory constraints', async ({ page }) => {
      // Simulate memory pressure by creating many objects
      await page.evaluate(() => {
        (window as any).memoryHogs = [];
        for (let i = 0; i < 1000; i++) {
          (window as any).memoryHogs.push(new Array(10000).fill('memory-hog'));
        }
      });

      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);
      await appPage.generateOutline();

      // Should still function under memory pressure
      await appPage.expectOutlineToHaveSections(3);

      // Clean up memory
      await page.evaluate(() => {
        (window as any).memoryHogs = null;
      });
    });
  });

  test.describe('Data Corruption and Recovery', () => {
    test('should handle corrupted project data', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Corrupt project data in localStorage
      await page.evaluate(() => {
        const projectKey = Object.keys(localStorage).find(key => key.includes('project'));
        if (projectKey) {
          localStorage.setItem(projectKey, 'corrupted-data-{invalid-json}');
        }
      });

      // Refresh page to trigger data loading
      await page.reload();
      await appPage.waitForAppLoad();

      // Should detect corruption and show recovery options
      const corruptionNotice = page.locator('[data-testid="data-corruption-notice"]');
      await expect(corruptionNotice).toBeVisible();

      const recoverButton = page.locator('[data-testid="recover-data"]');
      await recoverButton.click();

      // Should clear corrupted data and return to clean state
      await appPage.expectNotificationToShow('success', 'Data recovered successfully');
      
      const emptyState = page.locator('[data-testid="no-project-loaded"]');
      await expect(emptyState).toBeVisible();
    });

    test('should handle partial data recovery', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);
      await appPage.generateOutline();
      await appPage.enhanceContent(0);

      // Partially corrupt project data (remove some fields)
      await page.evaluate(() => {
        const projectKey = Object.keys(localStorage).find(key => key.includes('project'));
        if (projectKey) {
          const project = JSON.parse(localStorage.getItem(projectKey)!);
          delete project.outline[1]; // Remove one section
          localStorage.setItem(projectKey, JSON.stringify(project));
        }
      });

      await page.reload();
      await appPage.waitForAppLoad();

      // Should recover what it can
      const recoveryNotice = page.locator('[data-testid="partial-recovery-notice"]');
      await expect(recoveryNotice).toBeVisible();

      // Should still load the project with available data
      await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);
      
      // Should show recovery status
      const recoveryStatus = page.locator('[data-testid="recovery-status"]');
      await expect(recoveryStatus).toContainText('Some data could not be recovered');
    });
  });
});