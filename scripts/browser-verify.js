#!/usr/bin/env node

/**
 * Browser Verification Script
 * 
 * Opens a browser and verifies that the staging/production site loads correctly.
 * Takes a screenshot and checks for JavaScript errors.
 * 
 * Usage:
 *   node scripts/browser-verify.js                    # Uses staging URL
 *   STAGING_URL=https://styxproxy.com node scripts/browser-verify.js  # Uses production URL
 */

const { chromium } = require('playwright');

const DEFAULT_STAGING_URL = 'https://staging.styxproxy.com';
const TIMEOUT_MS = 30000;

async function verifySite() {
  const targetUrl = process.env.STAGING_URL || DEFAULT_STAGING_URL;
  
  console.log(`Verifying site: ${targetUrl}`);
  console.log('Starting browser...');

  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });
  
  const page = await context.newPage();
  
  const errors = [];
  const consoleMessages = [];
  
  // Listen for console messages
  page.on('console', msg => {
    const text = msg.text();
    consoleMessages.push({ type: msg.type(), text });
    
    if (msg.type() === 'error') {
      errors.push(text);
    }
  });
  
  // Listen for page errors
  page.on('pageerror', error => {
    errors.push(`Page error: ${error.message}`);
  });
  
  try {
    console.log(`Navigating to ${targetUrl}...`);
    
    // Navigate with timeout
    const response = await page.goto(targetUrl, { 
      waitUntil: 'networkidle',
      timeout: TIMEOUT_MS
    });
    
    if (!response.ok()) {
      console.error(`ERROR: Page returned status ${response.status()}`);
      await browser.close();
      process.exit(1);
    }
    
    console.log('Page loaded successfully!');
    
    // Wait a bit for any delayed errors
    await page.waitForTimeout(2000);
    
    // Get page title
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Take screenshot
    const screenshotPath = `/tmp/verify-${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved to: ${screenshotPath}`);
    
    // Report results
    console.log('\n--- Verification Results ---');
    
    if (errors.length > 0) {
      console.log('\nERRORS FOUND:');
      errors.forEach(err => console.log(`  - ${err}`));
      await browser.close();
      process.exit(1);
    } else {
      console.log('No JavaScript errors detected!');
      console.log(`\n✓ Site verification PASSED for ${targetUrl}`);
    }
    
    if (consoleMessages.length > 0) {
      console.log('\nConsole messages:');
      consoleMessages.slice(0, 5).forEach(msg => {
        console.log(`  [${msg.type}] ${msg.text}`);
      });
    }
    
  } catch (error) {
    console.error(`\nERROR: ${error.message}`);
    
    // Try to take a screenshot even on error
    try {
      const errorScreenshot = `/tmp/verify-error-${Date.now()}.png`;
      await page.screenshot({ path: errorScreenshot, fullPage: true });
      console.log(`Error screenshot saved to: ${errorScreenshot}`);
    } catch (screenshotError) {
      // Ignore screenshot errors
    }
    
    await browser.close();
    process.exit(1);
  }
  
  await browser.close();
}

// Run verification
verifySite().catch(error => {
  console.error('Unexpected error:', error);
  process.exit(1);
});
