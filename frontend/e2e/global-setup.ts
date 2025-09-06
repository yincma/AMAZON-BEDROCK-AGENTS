import { chromium, FullConfig } from '@playwright/test';
import path from 'path';
import fs from 'fs';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global setup...');
  
  // Create test results directory
  const testResultsDir = path.join(process.cwd(), 'test-results');
  if (!fs.existsSync(testResultsDir)) {
    fs.mkdirSync(testResultsDir, { recursive: true });
  }

  // Create screenshots directory
  const screenshotsDir = path.join(testResultsDir, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  // Create videos directory
  const videosDir = path.join(testResultsDir, 'videos');
  if (!fs.existsSync(videosDir)) {
    fs.mkdirSync(videosDir, { recursive: true });
  }

  // Wait for the web server to be ready
  console.log('⏳ Waiting for web server to be ready...');
  
  // Pre-warm the browser for faster test execution
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  try {
    // Verify the app is running
    await page.goto(config.webServer?.url || 'http://localhost:5173', { 
      waitUntil: 'networkidle',
      timeout: 60000 
    });
    console.log('✅ Web server is ready');
    
    // Pre-load critical resources
    await page.waitForLoadState('domcontentloaded');
    
  } catch (error) {
    console.error('❌ Failed to connect to web server:', error);
    throw error;
  } finally {
    await browser.close();
  }

  console.log('✅ Global setup completed');
}

export default globalSetup;