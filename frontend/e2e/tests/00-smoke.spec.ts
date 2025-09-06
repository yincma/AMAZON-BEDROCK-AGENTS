import { test, expect } from '@playwright/test';

test.describe('Smoke Tests - 基础功能验证', () => {
  test('应用程序能够正常启动', async ({ page }) => {
    // 访问应用首页
    await page.goto('/');

    // 验证页面标题
    await expect(page).toHaveTitle(/AI PPT Generator/);

    // 验证主要布局元素存在
    const mainContent = page.locator('main, [role="main"], #root, #app');
    await expect(mainContent.first()).toBeVisible();

    // 验证没有控制台错误（基础检查）
    const logs: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        logs.push(msg.text());
      }
    });

    await page.waitForLoadState('networkidle');
    
    // 允许一些非关键错误，但不应该有太多
    expect(logs.length).toBeLessThan(5);
  });

  test('基本导航和交互功能正常', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 查找并点击任何可点击的元素（按钮、链接等）
    const clickableElements = page.locator('button, a, [role="button"]').first();
    if (await clickableElements.count() > 0) {
      await clickableElements.click();
      // 验证点击后没有导致应用崩溃
      const errorMessage = page.locator('[data-testid="error"], .error, [role="alert"]');
      await expect(errorMessage).not.toBeVisible();
    }
  });

  test('响应式布局在不同设备上正常工作', async ({ page }) => {
    // 测试桌面尺寸
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    let mainContent = page.locator('main, [role="main"], #root, #app');
    await expect(mainContent.first()).toBeVisible();

    // 测试平板尺寸
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500); // 等待布局调整
    await expect(mainContent.first()).toBeVisible();

    // 测试手机尺寸
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await expect(mainContent.first()).toBeVisible();
  });

  test('页面加载性能满足基本要求', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    const loadTime = Date.now() - startTime;
    
    // 页面应该在5秒内加载完成（比较宽松的要求）
    expect(loadTime).toBeLessThan(5000);
    
    // 验证关键资源已加载
    await page.waitForLoadState('networkidle');
  });

  test('基本的可访问性要求', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 检查页面是否有合理的标题
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);

    // 检查是否存在主要内容区域
    const main = page.locator('main, [role="main"]');
    if (await main.count() > 0) {
      await expect(main.first()).toBeVisible();
    }

    // 基本的键盘导航测试
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus');
    if (await focusedElement.count() > 0) {
      await expect(focusedElement.first()).toBeVisible();
    }
  });
});