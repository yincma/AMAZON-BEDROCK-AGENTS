import { test, expect } from '@playwright/test';
import { AppPage, PerformanceMonitor } from '../utils/test-helpers';
import { API_CONFIG, PROJECT_DATA, PERFORMANCE_THRESHOLDS, VIEWPORT_SIZES } from '../fixtures/test-data';

test.describe('Performance and Accessibility', () => {
  let appPage: AppPage;
  let performanceMonitor: PerformanceMonitor;

  test.beforeEach(async ({ page }) => {
    appPage = new AppPage(page);
    performanceMonitor = new PerformanceMonitor(page);
    await appPage.navigateToHome();
    await appPage.waitForAppLoad();
  });

  test.describe('Performance Tests', () => {
    test('should meet page load performance requirements', async ({ page }) => {
      await performanceMonitor.startMonitoring();
      
      // Measure initial page load
      const loadTime = await appPage.measurePageLoadTime();
      expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.pageLoad);

      // Get detailed performance metrics
      const metrics = await performanceMonitor.getPerformanceMetrics();
      
      // DNS lookup should be fast
      expect(metrics.dns).toBeLessThan(200);
      
      // Request/response time should be reasonable
      expect(metrics.request + metrics.response).toBeLessThan(1000);
      
      // DOM interactive should be fast
      expect(metrics.domInteractive).toBeLessThan(2000);
      
      // DOM complete should meet threshold
      expect(metrics.domComplete).toBeLessThan(PERFORMANCE_THRESHOLDS.pageLoad);

      const coverage = await performanceMonitor.stopMonitoring();
      console.log('JavaScript coverage:', coverage?.jsCoverage?.length || 0, 'files');
      console.log('CSS coverage:', coverage?.cssCoverage?.length || 0, 'files');
    });

    test('should handle large datasets efficiently', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.complex);

      // Measure outline generation with large project
      const outlineTime = await appPage.measureAPIResponseTime(async () => {
        await appPage.generateOutline();
      });
      expect(outlineTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse);

      // Measure content enhancement performance
      const enhanceTime = await appPage.measureAPIResponseTime(async () => {
        await appPage.enhanceContent(0);
      });
      expect(enhanceTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse);

      // Measure image search performance
      const imageTime = await appPage.measureAPIResponseTime(async () => {
        await appPage.searchImages('technology');
      });
      expect(imageTime).toBeLessThan(PERFORMANCE_THRESHOLDS.imageLoad);

      // Verify UI responsiveness during operations
      const uiButton = page.locator('[data-testid="settings-button"]');
      const clickTime = await appPage.measureAPIResponseTime(async () => {
        await uiButton.click();
      });
      expect(clickTime).toBeLessThan(500); // UI should remain responsive
    });

    test('should optimize memory usage', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);

      // Measure initial memory
      const initialMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });

      // Create and work with multiple projects
      for (let i = 0; i < 3; i++) {
        await appPage.createNewProject({
          title: `Performance Test Project ${i}`,
          description: `Test project ${i} for performance testing`,
          topic: `Test Topic ${i}`
        });
        await appPage.generateOutline();
        await appPage.enhanceContent(0);
        await appPage.searchImages('test');
        await appPage.selectImages(2);
      }

      // Measure memory after operations
      const finalMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });

      // Memory growth should be reasonable (less than 50MB increase)
      const memoryGrowth = finalMemory - initialMemory;
      expect(memoryGrowth).toBeLessThan(50 * 1024 * 1024);

      // Force garbage collection if available
      await page.evaluate(() => {
        if ((window as any).gc) {
          (window as any).gc();
        }
      });
    });

    test('should handle concurrent operations efficiently', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.complex);
      await appPage.generateOutline();

      // Measure concurrent enhancement operations
      const startTime = Date.now();
      
      const enhancePromises = [
        appPage.enhanceContent(0),
        appPage.enhanceContent(1),
        appPage.enhanceContent(2),
      ];

      await Promise.all(enhancePromises);
      
      const totalTime = Date.now() - startTime;
      
      // Concurrent operations should be faster than sequential
      // Sequential would be 3 * apiResponse, concurrent should be much less
      expect(totalTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse * 2);
    });

    test('should optimize bundle size and loading', async ({ page }) => {
      // Measure network requests
      const requests: any[] = [];
      page.on('request', request => requests.push(request));

      await page.goto('/');
      await appPage.waitForAppLoad();

      // Analyze resource loading
      const jsRequests = requests.filter(req => req.url().endsWith('.js'));
      const cssRequests = requests.filter(req => req.url().endsWith('.css'));
      const imageRequests = requests.filter(req => 
        req.url().match(/\.(jpg|jpeg|png|svg|webp|gif)$/i)
      );

      // Should not load too many resources initially
      expect(jsRequests.length).toBeLessThan(10);
      expect(cssRequests.length).toBeLessThan(5);

      // Check for code splitting - main bundle shouldn't be too large
      const responses = await Promise.all(
        jsRequests.map(req => req.response())
      );

      for (const response of responses) {
        if (response) {
          const size = parseInt(response.headers()['content-length'] || '0');
          expect(size).toBeLessThan(1024 * 1024); // 1MB per chunk
        }
      }
    });

    test('should perform well on mobile devices', async ({ page, isMobile }) => {
      if (!isMobile) {
        await page.setViewportSize(VIEWPORT_SIZES.mobile);
      }

      await performanceMonitor.startMonitoring();

      // Test mobile performance
      const mobileLoadTime = await appPage.measurePageLoadTime();
      expect(mobileLoadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.pageLoad * 1.5); // Allow 50% more time on mobile

      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Mobile operations should still be reasonably fast
      const mobileOutlineTime = await appPage.measureAPIResponseTime(async () => {
        await appPage.generateOutline();
      });
      expect(mobileOutlineTime).toBeLessThan(PERFORMANCE_THRESHOLDS.apiResponse * 1.2);

      await performanceMonitor.stopMonitoring();
    });
  });

  test.describe('Accessibility Tests', () => {
    test('should pass basic accessibility checks', async ({ page }) => {
      // Check for basic accessibility features
      const main = page.locator('main');
      await expect(main).toBeVisible();

      // Check for proper heading structure
      const h1 = page.locator('h1');
      await expect(h1).toHaveCount(1);

      // Check for skip links
      const skipLink = page.locator('[href="#main-content"]');
      if (await skipLink.count() > 0) {
        await expect(skipLink).toBeVisible();
      }

      // Check for proper button labeling
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();
      
      for (let i = 0; i < buttonCount; i++) {
        const button = buttons.nth(i);
        const hasText = await button.textContent();
        const hasAriaLabel = await button.getAttribute('aria-label');
        const hasTitle = await button.getAttribute('title');
        
        expect(hasText || hasAriaLabel || hasTitle).toBeTruthy();
      }
    });

    test('should support keyboard navigation', async ({ page }) => {
      // Test tab navigation
      await page.keyboard.press('Tab');
      
      let focusedElement = await page.locator(':focus').first();
      await expect(focusedElement).toBeVisible();

      // Navigate through several elements
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        focusedElement = await page.locator(':focus').first();
        await expect(focusedElement).toBeVisible();
      }

      // Test reverse navigation
      await page.keyboard.press('Shift+Tab');
      focusedElement = await page.locator(':focus').first();
      await expect(focusedElement).toBeVisible();

      // Test Enter key activation on buttons
      const button = page.locator('button').first();
      await button.focus();
      await page.keyboard.press('Enter');
      
      // Should activate the button (will vary based on button function)
    });

    test('should support screen readers', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Check for proper ARIA labels and roles
      const form = page.locator('form');
      if (await form.count() > 0) {
        const firstForm = form.first();
        const hasAriaLabel = await firstForm.getAttribute('aria-label');
        const hasRole = await firstForm.getAttribute('role');
        expect(hasAriaLabel || hasRole).toBeTruthy();
      }

      // Check input labels
      const inputs = page.locator('input');
      const inputCount = await inputs.count();
      
      for (let i = 0; i < inputCount; i++) {
        const input = inputs.nth(i);
        const inputId = await input.getAttribute('id');
        const hasAriaLabel = await input.getAttribute('aria-label');
        
        if (inputId) {
          const label = page.locator(`label[for="${inputId}"]`);
          const labelExists = await label.count() > 0;
          expect(labelExists || hasAriaLabel).toBeTruthy();
        }
      }

      // Check for live regions
      await appPage.generateOutline();
      
      const liveRegion = page.locator('[aria-live]');
      if (await liveRegion.count() > 0) {
        await expect(liveRegion.first()).toBeVisible();
      }
    });

    test('should have proper color contrast', async ({ page }) => {
      // This is a simplified check - in real scenarios, use axe-core
      const textElements = page.locator('p, span, div, button, a');
      const elementCount = Math.min(await textElements.count(), 10); // Check first 10

      for (let i = 0; i < elementCount; i++) {
        const element = textElements.nth(i);
        const styles = await element.evaluate(el => {
          const computed = window.getComputedStyle(el);
          return {
            color: computed.color,
            backgroundColor: computed.backgroundColor,
            fontSize: computed.fontSize,
          };
        });

        // Basic validation - text should have color and reasonable font size
        expect(styles.color).not.toBe('');
        expect(styles.fontSize).toBeTruthy();
        
        // Font size should be reasonable (at least 14px equivalent)
        const fontSize = parseInt(styles.fontSize);
        expect(fontSize).toBeGreaterThanOrEqual(14);
      }
    });

    test('should support high contrast mode', async ({ page }) => {
      // Simulate high contrast mode
      await page.addStyleTag({
        content: `
          @media (prefers-contrast: high) {
            * {
              background-color: black !important;
              color: white !important;
              border-color: white !important;
            }
          }
        `
      });

      // Test functionality in high contrast mode
      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Core functionality should still work
      await appPage.generateOutline();
      await appPage.expectOutlineToHaveSections(3);

      // Elements should still be visible and functional
      const buttons = page.locator('button');
      const firstButton = buttons.first();
      await expect(firstButton).toBeVisible();
    });

    test('should support reduced motion preferences', async ({ page }) => {
      // Simulate reduced motion preference
      await page.emulateMedia({ reducedMotion: 'reduce' });

      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Generate content and verify animations are reduced
      await appPage.generateOutline();

      // Check that CSS respects reduced motion
      const animatedElements = page.locator('[class*="animate"], [style*="transition"]');
      const count = await animatedElements.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        const element = animatedElements.nth(i);
        const transition = await element.evaluate(el => 
          window.getComputedStyle(el).transition
        );
        
        // Transitions should be minimal or none in reduced motion mode
        expect(transition === 'none' || transition.includes('0s')).toBeTruthy();
      }
    });

    test('should work with different zoom levels', async ({ page }) => {
      const zoomLevels = [0.5, 1, 1.5, 2];

      for (const zoom of zoomLevels) {
        await page.evaluate((zoomLevel) => {
          document.body.style.zoom = zoomLevel.toString();
        }, zoom);

        await appPage.configureAPI(API_CONFIG.valid);
        await appPage.createNewProject(PROJECT_DATA.simple);

        // Core functionality should work at all zoom levels
        await appPage.generateOutline();
        await appPage.expectOutlineToHaveSections(3);

        // No horizontal scrolling should occur
        const scrollWidth = await page.evaluate(() => 
          document.body.scrollWidth > window.innerWidth
        );
        expect(scrollWidth).toBe(false);
      }

      // Reset zoom
      await page.evaluate(() => {
        document.body.style.zoom = '1';
      });
    });

    test('should handle focus management properly', async ({ page }) => {
      await appPage.configureAPI(API_CONFIG.valid);

      // Test modal focus management
      const newProjectButton = page.locator('[data-testid="new-project-button"]');
      await newProjectButton.click();

      // Focus should be trapped in modal
      const modal = page.locator('[data-testid="project-modal"]');
      await expect(modal).toBeVisible();

      const firstInput = page.locator('[data-testid="project-title-input"]');
      await expect(firstInput).toBeFocused();

      // Tab through modal elements
      await page.keyboard.press('Tab');
      const secondInput = page.locator('[data-testid="project-description-input"]');
      await expect(secondInput).toBeFocused();

      // Escape should close modal and restore focus
      await page.keyboard.press('Escape');
      await expect(modal).not.toBeVisible();
      await expect(newProjectButton).toBeFocused();
    });

    test('should provide proper error announcements', async ({ page }) => {
      // Test error message accessibility
      const newProjectButton = page.locator('[data-testid="new-project-button"]');
      await newProjectButton.click();

      const createButton = page.locator('[data-testid="create-project-button"]');
      await createButton.click();

      // Error message should have proper ARIA attributes
      const errorMessage = page.locator('[data-testid="title-error"]');
      await expect(errorMessage).toBeVisible();
      
      const ariaLive = await errorMessage.getAttribute('aria-live');
      const role = await errorMessage.getAttribute('role');
      
      expect(ariaLive === 'polite' || ariaLive === 'assertive' || role === 'alert').toBeTruthy();
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on different viewport sizes', async ({ page }) => {
      const viewports = [
        VIEWPORT_SIZES.mobile,
        VIEWPORT_SIZES.tablet,
        VIEWPORT_SIZES.desktop,
        VIEWPORT_SIZES.wide,
      ];

      for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await appPage.navigateToHome();
        await appPage.waitForAppLoad();

        // Basic functionality should work on all sizes
        await appPage.configureAPI(API_CONFIG.valid);
        await appPage.createNewProject(PROJECT_DATA.simple);

        // Layout should adapt
        const layout = page.locator('[data-testid="app-layout"]');
        await expect(layout).toBeVisible();

        // No horizontal scroll on mobile
        if (viewport.width < 768) {
          const hasHorizontalScroll = await page.evaluate(() => 
            document.body.scrollWidth > window.innerWidth
          );
          expect(hasHorizontalScroll).toBe(false);
        }
      }
    });

    test('should handle orientation changes on mobile', async ({ page, isMobile }) => {
      test.skip(!isMobile, 'This test is for mobile devices only');

      // Portrait orientation
      await page.setViewportSize({ width: 375, height: 667 });
      await appPage.navigateToHome();
      await appPage.waitForAppLoad();

      await appPage.configureAPI(API_CONFIG.valid);
      await appPage.createNewProject(PROJECT_DATA.simple);

      // Switch to landscape
      await page.setViewportSize({ width: 667, height: 375 });
      
      // Layout should adapt
      const layout = page.locator('[data-testid="app-layout"]');
      await expect(layout).toBeVisible();

      // Functionality should still work
      await appPage.generateOutline();
      await appPage.expectOutlineToHaveSections(3);
    });
  });
});