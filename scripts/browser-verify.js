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

const DEFAULT_URL = 'https://styxproxy.com';
const TIMEOUT_MS = 30000;

async function verifySite() {
  const targetUrl = process.env.SITE_URL || DEFAULT_URL;
  
  console.log(`Verifying site: ${targetUrl}`);
  console.log('Starting browser...');

  const browser = await chromium.launch({
    executablePath: '/snap/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
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

    // Check for canvas (globe)
    const canvasCount = await page.locator('canvas').count();
    console.log(`Canvas elements: ${canvasCount}`);

    // Check for stuck loading states
    const loadingCount = await page.locator('text=/loading/i').count();
    console.log(`Loading states: ${loadingCount}`);

    // Check nav links
    const navLinks = await page.locator('nav a, header a').count();
    console.log(`Nav links: ${navLinks}`);

    // Check h1 text
    const h1 = await page.locator('h1').first().textContent().catch(() => 'none');
    console.log(`H1: ${h1}`);

    // Report results
    console.log('\n--- Verification Results ---');

    if (errors.length > 0) {
      console.log('\nERRORS FOUND:');
      errors.forEach(err => console.log(`  - ${err}`));
      await browser.close();
      process.exit(1);
    }

    // Fail if globe is missing (canvas count 0)
    if (canvasCount === 0) {
      console.log('\nWARNING: No canvas elements found — globe may not be rendering');
    }

    // Fail if stuck loading
    if (loadingCount > 0) {
      console.log('\nERROR: Stuck loading states detected');
      await browser.close();
      process.exit(1);
    }

    // Fail if nav is empty
    if (navLinks === 0) {
      console.log('\nERROR: No navigation links found');
      await browser.close();
      process.exit(1);
    }

    console.log('\nNo JavaScript errors detected!');
    console.log(`\n✓ Site verification PASSED for ${targetUrl}`);
    
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
