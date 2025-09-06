import { test, expect } from '@playwright/test';
import { AppPage } from '../utils/test-helpers';
import { API_CONFIG, PROJECT_DATA, OUTLINE_DATA, IMAGE_SEARCH, PERFORMANCE_THRESHOLDS } from '../fixtures/test-data';

test.describe('PPT Creation Flow', () => {
  let appPage: AppPage;

  test.beforeEach(async ({ page }) => {
    appPage = new AppPage(page);
    await appPage.navigateToHome();
    await appPage.waitForAppLoad();
    
    // Setup API configuration
    await appPage.configureAPI(API_CONFIG.valid);
  });

  test('should complete full PPT creation workflow', async ({ page }) => {
    // Create new project
    await appPage.createNewProject(PROJECT_DATA.simple);
    
    // Verify project is created
    await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);

    // Generate outline
    await appPage.generateOutline();
    
    // Verify outline is generated
    await appPage.expectOutlineToHaveSections(OUTLINE_DATA.simple.sections);

    // Enhance content for each section
    for (let i = 0; i < OUTLINE_DATA.simple.sections; i++) {
      await appPage.enhanceContent(i);
    }

    // Search and select images
    await appPage.searchImages(IMAGE_SEARCH.keywords[0]);
    await appPage.selectImages(3);
    
    // Verify images are selected
    await appPage.expectImagesInGallery(3);

    // Generate PPT
    await appPage.generatePPT();

    // Verify PPT is generated
    const pptStatus = page.locator('[data-testid="ppt-generated"]');
    await expect(pptStatus).toBeVisible();

    // Download PPT
    const download = await appPage.downloadPPT();
    expect(download.suggestedFilename()).toMatch(/.*\.pptx$/);
    
    // Verify success notification
    await appPage.expectNotificationToShow('success', 'PPT generated successfully');
  });

  test('should handle outline generation with different project types', async ({ page }) => {
    // Test with complex project
    await appPage.createNewProject(PROJECT_DATA.complex);
    await appPage.generateOutline();
    
    // Complex projects should generate more sections
    await appPage.expectOutlineToHaveSections(OUTLINE_DATA.detailed.sections);

    // Verify section titles are meaningful
    const sectionTitles = page.locator('[data-testid^="section-title-"]');
    const firstTitle = await sectionTitles.first().textContent();
    expect(firstTitle).toBeTruthy();
    expect(firstTitle!.length).toBeGreaterThan(5);

    // Test with simple project
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    
    await appPage.expectOutlineToHaveSections(OUTLINE_DATA.simple.sections);
  });

  test('should validate content enhancement features', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();

    // Get initial content
    const sectionContent = page.locator('[data-testid="section-content-0"]');
    const initialContent = await sectionContent.textContent();

    // Enhance content
    await appPage.enhanceContent(0);

    // Verify content is enhanced (should be different and longer)
    const enhancedContent = await sectionContent.textContent();
    expect(enhancedContent).not.toBe(initialContent);
    expect(enhancedContent!.length).toBeGreaterThan(initialContent!.length);

    // Verify enhancement indicator
    const enhancementBadge = page.locator('[data-testid="enhanced-badge-0"]');
    await expect(enhancementBadge).toBeVisible();
  });

  test('should handle image search and selection', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);

    // Test image search with different keywords
    for (const keyword of IMAGE_SEARCH.keywords.slice(0, 2)) {
      await appPage.searchImages(keyword);
      
      // Verify images are loaded
      const imageResults = page.locator('[data-testid^="image-option-"]');
      await expect(imageResults).toHaveCount(expect.any(Number));
      
      // Verify images have proper attributes
      const firstImage = imageResults.first();
      await expect(firstImage.locator('img')).toHaveAttribute('src');
      await expect(firstImage.locator('img')).toHaveAttribute('alt');
    }

    // Select multiple images
    await appPage.selectImages(5);
    await appPage.expectImagesInGallery(5);

    // Verify selected images in gallery
    const galleryImages = page.locator('[data-testid^="gallery-image-"]');
    expect(await galleryImages.count()).toBe(5);

    // Test image removal
    const removeButton = page.locator('[data-testid="remove-image-0"]');
    await removeButton.click();
    
    expect(await galleryImages.count()).toBe(4);
  });

  test('should handle invalid image search queries', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);

    // Test with empty search
    await appPage.searchImages('');
    
    const errorMessage = page.locator('[data-testid="search-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('Please enter a search keyword');

    // Test with whitespace only
    await appPage.searchImages('   ');
    await expect(errorMessage).toContainText('Please enter a search keyword');

    // Test with very short query
    await appPage.searchImages('a');
    await expect(errorMessage).toContainText('Search keyword must be at least 2 characters');
  });

  test('should track progress throughout PPT creation', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);

    // Verify initial progress
    const progressBar = page.locator('[data-testid="creation-progress"]');
    await expect(progressBar).toBeVisible();
    
    let progress = await progressBar.getAttribute('data-progress');
    expect(parseInt(progress!)).toBe(0);

    // Generate outline - progress should increase
    await appPage.generateOutline();
    progress = await progressBar.getAttribute('data-progress');
    expect(parseInt(progress!)).toBeGreaterThan(0);

    // Enhance content - progress should increase more
    await appPage.enhanceContent(0);
    const newProgress = await progressBar.getAttribute('data-progress');
    expect(parseInt(newProgress!)).toBeGreaterThan(parseInt(progress!));

    // Add images
    await appPage.searchImages(IMAGE_SEARCH.keywords[0]);
    await appPage.selectImages(2);
    progress = await progressBar.getAttribute('data-progress');
    expect(parseInt(progress!)).toBeGreaterThan(50);

    // Generate PPT - should reach 100%
    await appPage.generatePPT();
    progress = await progressBar.getAttribute('data-progress');
    expect(parseInt(progress!)).toBe(100);
  });

  test('should allow saving work in progress', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    await appPage.enhanceContent(0);

    // Save work in progress
    const saveButton = page.locator('[data-testid="save-progress-button"]');
    await saveButton.click();

    await appPage.expectNotificationToShow('success', 'Progress saved');

    // Refresh page and verify work is preserved
    await page.reload();
    await appPage.waitForAppLoad();

    // Project should still be loaded
    await appPage.expectProjectToBeLoaded(PROJECT_DATA.simple.title);

    // Outline should still be there
    await appPage.expectOutlineToHaveSections(OUTLINE_DATA.simple.sections);

    // Enhanced content should be preserved
    const enhancementBadge = page.locator('[data-testid="enhanced-badge-0"]');
    await expect(enhancementBadge).toBeVisible();
  });

  test('should handle PPT generation with different templates', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();
    await appPage.enhanceContent(0);

    // Select different template
    const templateSelector = page.locator('[data-testid="template-selector"]');
    await templateSelector.click();

    const professionalTemplate = page.locator('[data-testid="template-professional"]');
    await professionalTemplate.click();

    // Generate PPT with selected template
    await appPage.generatePPT();

    // Verify template is applied
    const generatedPPT = page.locator('[data-testid="ppt-generated"]');
    await expect(generatedPPT).toBeVisible();
    
    const templateInfo = page.locator('[data-testid="applied-template"]');
    await expect(templateInfo).toContainText('professional');
  });

  test('should meet performance requirements during PPT creation', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);

    // Measure outline generation time
    const outlineTime = await appPage.measureAPIResponseTime(async () => {
      await appPage.generateOutline();
    });
    expect(outlineTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse);

    // Measure content enhancement time
    const enhanceTime = await appPage.measureAPIResponseTime(async () => {
      await appPage.enhanceContent(0);
    });
    expect(enhanceTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse);

    // Measure image search time
    const imageSearchTime = await appPage.measureAPIResponseTime(async () => {
      await appPage.searchImages(IMAGE_SEARCH.keywords[0]);
    });
    expect(imageSearchTime).toBeLessThan(PERFORMANCE_THRESHOLDS.imageLoad);

    // Measure PPT generation time (can be longer)
    const pptTime = await appPage.measureAPIResponseTime(async () => {
      await appPage.selectImages(2);
      await appPage.generatePPT();
    });
    expect(pptTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse * 2);
  });

  test('should handle concurrent operations gracefully', async ({ page }) => {
    await appPage.createNewProject(PROJECT_DATA.simple);
    await appPage.generateOutline();

    // Start multiple enhancement operations
    const enhancePromises = [];
    for (let i = 0; i < 3; i++) {
      enhancePromises.push(appPage.enhanceContent(i));
    }

    // Wait for all to complete
    await Promise.all(enhancePromises);

    // Verify all sections are enhanced
    for (let i = 0; i < 3; i++) {
      const enhancementBadge = page.locator(`[data-testid="enhanced-badge-${i}"]`);
      await expect(enhancementBadge).toBeVisible();
    }

    // Verify no conflicts or errors occurred
    const errorNotification = page.locator('[data-testid="notification-error"]');
    await expect(errorNotification).not.toBeVisible();
  });

  test('should support mobile PPT creation workflow', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'This test is for mobile devices only');

    await appPage.createNewProject(PROJECT_DATA.simple);

    // Verify mobile-optimized creation interface
    const mobileCreator = page.locator('[data-testid="mobile-ppt-creator"]');
    await expect(mobileCreator).toBeVisible();

    // Test swipe gestures for navigation
    await page.touchscreen.tap(100, 300);
    
    // Generate outline on mobile
    await appPage.generateOutline();
    
    // Verify mobile progress indicator
    const mobileProgress = page.locator('[data-testid="mobile-progress"]');
    await expect(mobileProgress).toBeVisible();

    // Test mobile image selection
    await appPage.searchImages(IMAGE_SEARCH.keywords[0]);
    await appPage.selectImages(2);

    // Complete mobile workflow
    await appPage.generatePPT();
    
    // Verify mobile download works
    const mobileDownload = page.locator('[data-testid="mobile-download-button"]');
    await expect(mobileDownload).toBeVisible();
  });
});