import { test, chromium } from '@playwright/test'

test('inspect user live browser tab', async () => {
  console.log('Connecting to debugging Chrome on port 9222...')
  // Connect to Chrome
  const browser = await chromium.connectOverCDP('http://localhost:9222')
  
  // Get all contexts and pages
  const contexts = browser.contexts()
  console.log(`Found ${contexts.length} contexts`)
  
  let targetPage = null
  for (const context of contexts) {
    const pages = context.pages()
    for (const p of pages) {
      const url = p.url()
      console.log(`Page URL: ${url}`)
      if (url.includes('/ai-score/report/23/overview')) {
        targetPage = p
        break
      }
    }
    if (targetPage) break
  }
  
  if (!targetPage) {
    console.log('Could not find active score report tab in browser contexts.')
    await browser.close()
    return
  }
  
  console.log('Found active page! Extracting console logs, errors and HTML...')
  
  // Set up listeners on the user's active page
  targetPage.on('console', msg => {
    console.log(`USER BROWSER CONSOLE [${msg.type()}]:`, msg.text())
  })
  
  // Get console errors from window
  const errors = await targetPage.evaluate(() => {
    return window.__playwright_errors || []
  })
  console.log('Errors array in window:', errors)

  // Evaluate any errors in the DOM or state
  const consoleErrorLog = await targetPage.evaluate(() => {
    // Let's capture the text of any visible errors or app root state
    const app = document.querySelector('#app')
    return {
      appInnerHtml: app ? app.innerHTML : 'No #app found',
      bodyClass: document.body.className
    }
  })
  console.log('DOM State:', consoleErrorLog)

  const screenshotPath = '/Users/liuyixing/.gemini/antigravity-ide/brain/ba4b7912-a404-49ba-af88-55b0331deb5a/user_live_view.png'
  console.log(`Taking screenshot of user's active view: ${screenshotPath}`)
  await targetPage.screenshot({ path: screenshotPath })
  
  await browser.close()
})
