import { FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global teardown...');
  
  // Clean up temporary test data if needed
  const testDataDir = path.join(process.cwd(), 'test-data');
  if (fs.existsSync(testDataDir)) {
    try {
      fs.rmSync(testDataDir, { recursive: true, force: true });
      console.log('🗑️ Cleaned up test data directory');
    } catch (error) {
      console.warn('⚠️ Failed to clean up test data:', error);
    }
  }
  
  // Archive test results if on CI
  if (process.env.CI) {
    const testResultsDir = path.join(process.cwd(), 'test-results');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const archiveDir = path.join(process.cwd(), `test-results-${timestamp}`);
    
    try {
      if (fs.existsSync(testResultsDir)) {
        fs.renameSync(testResultsDir, archiveDir);
        console.log(`📦 Archived test results to: ${archiveDir}`);
      }
    } catch (error) {
      console.warn('⚠️ Failed to archive test results:', error);
    }
  }

  console.log('✅ Global teardown completed');
}

export default globalTeardown;