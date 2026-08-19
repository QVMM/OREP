import { chromium } from '@playwright/test';

async function run() {
  console.log('Connecting to Chrome on port 9222...');
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  
  const contexts = browser.contexts();
  let targetPage = null;
  for (const context of contexts) {
    for (const p of context.pages()) {
      if (p.url().includes('/ai-score/report/23/overview')) {
        targetPage = p;
        break;
      }
    }
  }
  
  if (!targetPage) {
    console.log('Target page not found');
    await browser.close();
    return;
  }
  
  console.log('Attached! Setting up listeners and reloading page...');
  
  const logs = [];
  targetPage.on('console', msg => {
    logs.push(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });
  
  targetPage.on('pageerror', err => {
    logs.push(`[UNCAUGHT EXCEPTION] ${err.message}\n${err.stack}`);
  });
  
  await targetPage.reload({ waitUntil: 'load' });
  
  // Wait another 3 seconds for async mounts/API calls
  await targetPage.waitForTimeout(3000);
  
  console.log('\n--- BROWSER LOGS DURING RELOAD ---');
  logs.forEach(log => console.log(log));
  console.log('----------------------------------\n');
  
  await browser.close();
}

run().catch(console.error);
