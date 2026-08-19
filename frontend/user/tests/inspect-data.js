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
  
  console.log('Connected! Querying issues from Vue app context...');
  
  const issues = await targetPage.evaluate(() => {
    const appEl = document.querySelector('#app');
    if (!appEl) return { error: 'No #app' };
    const vueInstance = appEl.__vue_app__;
    if (!vueInstance) return { error: 'No __vue_app__' };
    
    // Let's find any vue components or values from router view component instance
    // Let's look for issueList values
    const data = {};
    try {
      // Find the component instance
      const vnode = appEl.__vue_app__._instance;
      // We can search the component tree for AiScoreReportOverview
      const findOverview = (instance) => {
        if (!instance) return null;
        if (instance.type.name === 'AiScoreReportOverview' || instance.type.__name === 'AiScoreReportOverview') {
          return instance;
        }
        if (instance.subTree) {
          const res = findOverview(instance.subTree.component);
          if (res) return res;
        }
        if (instance.subTree && instance.subTree.children && Array.isArray(instance.subTree.children)) {
          for (const child of instance.subTree.children) {
            const res = findOverview(child.component);
            if (res) return res;
          }
        }
        return null;
      };
      
      const overviewInst = findOverview(vnode);
      if (overviewInst) {
        data.issues = overviewInst.setupState.topThreeIssues.value.map(i => ({
          id: i.id,
          title: i.title,
          score: i.score
        }));
      } else {
        data.error = 'AiScoreReportOverview instance not found in tree';
      }
    } catch (e) {
      data.error = 'Exception: ' + e.message;
    }
    return data;
  });
  
  console.log('Issues data in page:', JSON.stringify(issues, null, 2));
  await browser.close();
}

run().catch(console.error);
