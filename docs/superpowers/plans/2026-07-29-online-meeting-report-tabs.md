# Online Meeting Report Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将参会记录与评分报告融合进在线会议页的双标签区域，移除独立“复盘”主导航，并让旧评分报告地址安全跳转到新标签。

**Architecture:** `OnlineMeeting.vue` 负责由 URL query 驱动的一级标签与参会记录，`Statistics.vue` 通过 `embedded` 属性复用原有评分请求、筛选和详情跳转。主导航把评分深层页面归入“现场讲解”，`/statistics` 仅作为兼容重定向入口，工作区二级菜单只保留协作模块。

**Tech Stack:** Vue 3 `<script setup>`、Vue Router、Element Plus、项目设计令牌、Playwright、Vite

**Design Spec:** `docs/superpowers/specs/2026-07-29-online-meeting-report-tabs-design.md`

**Version-control note:** 当前工作目录没有 Git 元数据，因此本计划使用“检查点”代替提交步骤；不执行或模拟 Git 提交。

---

## File Map

- Create: `frontend/user/tests/online-meeting-report-tabs.spec.js`
  - 覆盖双标签、query 同步、延迟加载、报告复用、旧地址跳转和窄屏无溢出。
- Modify: `frontend/user/src/views/OnlineMeeting.vue`
  - 持有一级标签状态，渲染参会记录或嵌入式评分报告。
- Modify: `frontend/user/src/views/Statistics.vue`
  - 增加 `embedded` 模式，保留上传入口并移除嵌入时的重复页面表面。
- Modify: `frontend/user/src/router/index.js`
  - 将 `/statistics` 改为新评分标签的兼容重定向。
- Modify: `frontend/user/src/composables/apple/useOrepNavigation.js`
  - 删除“复盘”主导航，并把评分相关深层路由归入“现场讲解”。
- Modify: `frontend/user/src/components/workspace/WorkspaceShell.vue`
  - 仅为协作模块渲染二级菜单。
- Modify: `frontend/user/tests/workspace-sidebar-navigation.spec.js`
  - 将主导航契约更新为六项，并验证评分深层页面的当前态。
- Modify: `frontend/user/tests/online-meeting-validation-alignment.spec.js`
  - 更新旧 `/statistics` 与二级菜单预期。
- Modify: `frontend/user/tests/review-pages-design.spec.js`
  - 将评分报告视觉与窄屏检查迁移到 `/online-meeting?tab=reports`。

### Task 1: 用失败测试锁定在线会议双标签契约

**Files:**
- Create: `frontend/user/tests/online-meeting-report-tabs.spec.js`

- [ ] **Step 1: 创建双标签端到端测试**

写入完整测试夹具和四个核心场景：

```js
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'online-meeting-report-tabs-token')
  })

  await page.route('**/api/meeting/my-history', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))

  await page.route('**/api/ai-score/reports/summary?*', route => {
    const scope = new URL(route.request().url()).searchParams.get('scope')
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        data: scope === 'participant'
          ? [{
              sessionId: 26,
              title: '乡村振兴项目路演',
              completedAt: '2026-06-26T14:16:45',
              status: 'completed',
              sourceType: 'meeting_recording',
              totalScore: 88,
              issueCount: 3,
              highRiskCount: 1
            }]
          : []
      })
    })
  })
})

test('默认展示参会记录且评分请求只在切换后发出', async ({ page }) => {
  let reportRequestCount = 0
  page.on('request', request => {
    if (request.url().includes('/api/ai-score/reports/summary?')) reportRequestCount += 1
  })

  await page.goto('/online-meeting')

  const mainTabs = page.getByRole('tablist', { name: '在线会议内容' })
  await expect(mainTabs.getByRole('tab', { name: '参会记录' })).toHaveAttribute('aria-selected', 'true')
  await expect(mainTabs.getByRole('tab', { name: '评分报告' })).toHaveAttribute('aria-selected', 'false')
  await expect(page.getByRole('tablist', { name: '筛选参与记录' })).toBeVisible()
  expect(reportRequestCount).toBe(0)

  await mainTabs.getByRole('tab', { name: '评分报告' }).click()
  await expect(page).toHaveURL('/online-meeting?tab=reports')
  await expect(page.getByRole('heading', { name: '报告记录', level: 2 })).toBeVisible()
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toBeVisible()
  await expect.poll(() => reportRequestCount).toBe(2)
})

test('主标签使用 query 并支持浏览器前进后退', async ({ page }) => {
  await page.goto('/online-meeting?tab=meetings')
  const mainTabs = page.getByRole('tablist', { name: '在线会议内容' })

  await mainTabs.getByRole('tab', { name: '评分报告' }).click()
  await expect(page).toHaveURL('/online-meeting?tab=reports')

  await mainTabs.getByRole('tab', { name: '参会记录' }).click()
  await expect(page).toHaveURL('/online-meeting?tab=meetings')

  await page.goBack()
  await expect(mainTabs.getByRole('tab', { name: '评分报告' })).toHaveAttribute('aria-selected', 'true')
  await page.goBack()
  await expect(mainTabs.getByRole('tab', { name: '参会记录' })).toHaveAttribute('aria-selected', 'true')
})

test('评分标签复用报告内容且不重复独立页头', async ({ page }) => {
  await page.goto('/online-meeting?tab=reports')

  await expect(page.getByRole('heading', { name: '在线会议', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: '评分报告', level: 1 })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '报告记录', level: 2 })).toBeVisible()
  await expect(page.getByRole('tablist', { name: '评分报告范围' })).toBeVisible()
  await expect(page.getByText('乡村振兴项目路演', { exact: true })).toBeVisible()
  await expect(page.locator('.score-summary-page')).toHaveClass(/\bis-embedded\b/)
})

test('无效标签回退参会记录且窄屏不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/online-meeting?tab=unknown')

  await expect(page.getByRole('tab', { name: '参会记录' })).toHaveAttribute('aria-selected', 'true')
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)

  await page.getByRole('tab', { name: '评分报告' }).click()
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})
```

- [ ] **Step 2: 运行测试并确认因功能缺失而失败**

Run:

```bash
cd frontend/user
npx playwright test tests/online-meeting-report-tabs.spec.js
```

Expected: FAIL；页面尚不存在名为“在线会议内容”的一级 `tablist`，也没有嵌入式评分报告。

- [ ] **Step 3: 检查点**

确认失败原因是缺少本次功能，而不是开发服务器、登录夹具或 API mock 异常。

### Task 2: 实现 query 驱动的一级标签和嵌入式评分报告

**Files:**
- Modify: `frontend/user/src/views/OnlineMeeting.vue:138-212`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:297-306`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:1769-1888`
- Modify: `frontend/user/src/views/Statistics.vue:1-78`
- Modify: `frontend/user/src/views/Statistics.vue:80-99`
- Modify: `frontend/user/src/views/Statistics.vue:497-746`
- Test: `frontend/user/tests/online-meeting-report-tabs.spec.js`

- [ ] **Step 1: 在在线会议页引入评分报告并建立 query 状态**

在 `OnlineMeeting.vue` 增加组件导入、派生状态和导航函数：

```js
import Statistics from './Statistics.vue'

const activeContentTab = computed(() => (
  route.query.tab === 'reports' ? 'reports' : 'meetings'
))

function selectContentTab(tab) {
  if (activeContentTab.value === tab && route.query.tab === tab) return
  router.push({
    query: {
      ...route.query,
      tab
    }
  })
}
```

不增加 watcher；路由 query 是唯一一级标签状态来源，缺少或无效值自然回退到 `meetings`。

- [ ] **Step 2: 将“最近参与”区域改造成一级标签容器**

用下面的结构包住现有参会记录内容；原来的 `list-head`、筛选按钮、空状态和记录行原样放进 `meetings-panel`：

```vue
<section class="list-card neo-raised" aria-label="在线会议记录与报告">
  <div class="content-tabs" role="tablist" aria-label="在线会议内容">
    <button
      id="meetings-tab"
      type="button"
      role="tab"
      aria-controls="meetings-panel"
      :aria-selected="activeContentTab === 'meetings'"
      :class="{ active: activeContentTab === 'meetings' }"
      @click="selectContentTab('meetings')"
    >
      参会记录
    </button>
    <button
      id="reports-tab"
      type="button"
      role="tab"
      aria-controls="reports-panel"
      :aria-selected="activeContentTab === 'reports'"
      :class="{ active: activeContentTab === 'reports' }"
      @click="selectContentTab('reports')"
    >
      评分报告
    </button>
  </div>

  <div
    v-if="activeContentTab === 'meetings'"
    id="meetings-panel"
    role="tabpanel"
    aria-labelledby="meetings-tab"
  >
    <!-- 现有 list-head 与 list-body -->
  </div>

  <Statistics
    v-else
    id="reports-panel"
    embedded
    role="tabpanel"
    aria-labelledby="reports-tab"
  />
</section>
```

`Statistics` 必须使用 `v-else`，保证默认参会记录标签不会加载评分 API。

- [ ] **Step 3: 为一级标签增加清晰、克制且响应式的视觉**

在 `OnlineMeeting.vue` 最后的设计系统覆盖层增加：

```css
.content-tabs {
  min-height: 56px;
  padding: 0 var(--ds-space-6, 24px);
  border-bottom: 1px solid var(--ds-line);
  display: flex;
  align-items: flex-end;
  gap: var(--ds-space-6, 24px);
  background: var(--ds-card-bg);
}

.content-tabs button {
  min-height: 56px;
  padding: 0 2px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--ds-muted);
  font: inherit;
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-bold);
  cursor: pointer;
}

.content-tabs button.active {
  border-bottom-color: var(--ds-orange);
  color: var(--ds-ink);
}

.content-tabs button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: -4px;
}

@media (max-width: 640px) {
  .content-tabs {
    padding: 0 var(--ds-space-4, 16px);
  }

  .content-tabs button {
    flex: 1;
  }
}
```

- [ ] **Step 4: 为评分报告组件增加嵌入模式**

把 `Statistics.vue` 根元素改为动态元素，独立模式保持 `<main>`，嵌入模式使用 `<div>`：

```vue
<component
  :is="embedded ? 'div' : 'main'"
  class="score-summary-page"
  :class="{ 'is-embedded': embedded }"
>
  <header v-if="!embedded" class="summary-head">
    <div>
      <h1>评分报告</h1>
      <p>查看每次路演的评分结论、扣分依据和下一轮改进建议。</p>
    </div>
    <BaseButton to="/ai-score-upload">上传评分</BaseButton>
  </header>

  <section class="summary-card" aria-labelledby="reportListTitle">
    <header class="report-toolbar">
      <div>
        <h2 id="reportListTitle">报告记录</h2>
        <p>共 {{ activeReports.length }} 份已完成报告</p>
      </div>
      <div class="report-toolbar__actions">
        <!-- 原有“评分报告范围” tabs -->
        <BaseButton v-if="embedded" size="small" to="/ai-score-upload">
          上传评分
        </BaseButton>
      </div>
    </header>
    <!-- 原有加载、错误、空状态和 report-list -->
  </section>
</component>
```

脚本增加属性定义：

```js
defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
})
```

不得复制或改写 `loadReports`、`normalizeReports`、`openReport` 等业务函数。

- [ ] **Step 5: 移除嵌入模式的重复表面并整理工具栏**

在 `Statistics.vue` 最后的样式覆盖层增加：

```css
.report-toolbar__actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.score-summary-page.is-embedded {
  min-height: 0;
  padding: 0;
}

.is-embedded .summary-card {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  overflow: visible;
}

@media (max-width: 900px) {
  .report-toolbar__actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
  }

  .report-toolbar__actions :deep(.base-button) {
    width: 100%;
  }
}
```

- [ ] **Step 6: 运行双标签测试并确认通过**

Run:

```bash
cd frontend/user
npx playwright test tests/online-meeting-report-tabs.spec.js
```

Expected: 4 tests PASS。

- [ ] **Step 7: 检查点**

检查 `OnlineMeeting.vue` 只负责标签与参会记录，`Statistics.vue` 仍是评分数据与报告跳转的唯一实现。

### Task 3: 移除“复盘”导航并兼容旧地址

**Files:**
- Modify: `frontend/user/tests/workspace-sidebar-navigation.spec.js:15-75`
- Modify: `frontend/user/tests/online-meeting-validation-alignment.spec.js:59-81`
- Modify: `frontend/user/src/composables/apple/useOrepNavigation.js:1-58`
- Modify: `frontend/user/src/components/workspace/WorkspaceShell.vue:49-90`
- Modify: `frontend/user/src/router/index.js:191-196`

- [ ] **Step 1: 先更新导航契约测试**

将主导航测试的名称、数量和图标数量改为六项：

```js
test('桌面主导航保留六个准确命名的可访问链接及训练营当前态', async ({ page }) => {
  // existing setup
  const expectedNames = ['首页', '训练营', '现场讲解', '协作', 'AI应用中心', '我的']
  await expect(links).toHaveCount(6)
  // existing accessible-name and icon geometry assertions
  expect(iconGeometry).toHaveLength(6)
})
```

在同一文件增加评分深层路由当前态用例：

```js
test('评分深层页面归入现场讲解且不再显示复盘入口', async ({ page }) => {
  await page.goto('/ai-score-upload')

  const navigation = page.getByRole('navigation', { name: '用户端主导航' })
  await expect(navigation.getByRole('link', { name: '复盘', exact: true })).toHaveCount(0)
  await expect(navigation.getByRole('link', { name: '现场讲解', exact: true }))
    .toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
})
```

更新二级菜单测试中 `/statistics` 段落：

```js
await page.goto('/statistics')
await expect(page).toHaveURL('/online-meeting?tab=reports')
await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
await expect(page.getByRole('tab', { name: '评分报告' })).toHaveAttribute('aria-selected', 'true')

await page.goto('/project-team')
await expect(page.getByRole('navigation', { name: '团队协作二级导航' })).toBeVisible()
```

- [ ] **Step 2: 运行导航测试并确认失败**

Run:

```bash
cd frontend/user
npx playwright test tests/workspace-sidebar-navigation.spec.js tests/online-meeting-validation-alignment.spec.js
```

Expected: FAIL；当前仍有七项导航、“复盘”入口仍存在，且 `/statistics` 尚未重定向。

- [ ] **Step 3: 删除复盘主导航并扩展现场讲解当前态**

`useOrepNavigation.js` 的主导航改为：

```js
export const OREP_NAV_ITEMS = [
  { path: '/', label: '首页', code: 'Home', group: 'home' },
  { path: '/training/today', label: '训练营', code: 'Training', group: 'training' },
  { path: '/online-meeting', label: '现场讲解', code: 'Roadshow', group: 'roadshow' },
  { path: '/project-team', label: '协作', code: 'Collaboration', group: 'collaboration' },
  { path: '/ai-apps', label: 'AI应用中心', code: 'AI Apps', group: 'aiApps' },
  { path: '/profile', label: '我的', code: 'Profile', group: 'profile' },
]
```

将 `/online-meeting` 的当前态判断替换为：

```js
if (itemPath === '/online-meeting') {
  return routePath.startsWith('/online-meeting')
    || routePath.startsWith('/meeting/')
    || routePath.startsWith('/meeting-history')
    || routePath.startsWith('/my-recordings')
    || routePath.startsWith('/statistics')
    || routePath.startsWith('/score-result')
    || routePath.startsWith('/ai-score')
    || routePath.startsWith('/roadshow-chat')
}
```

删除原 `if (itemPath === '/statistics')` 分支。

- [ ] **Step 4: 只允许协作模块显示二级菜单**

`WorkspaceShell.vue` 修改为：

```js
const hasModuleNav = computed(() => moduleGroup.value === 'collaboration')
```

并将 `inferModuleGroup` 中评分路由归入 roadshow：

```js
if (
  path.startsWith('/online-meeting')
  || path.startsWith('/meeting/')
  || path.startsWith('/meeting-history')
  || path.startsWith('/my-recordings')
  || path.startsWith('/statistics')
  || path.startsWith('/ai-score')
  || path.startsWith('/score-result')
  || path.startsWith('/roadshow-chat')
) return 'roadshow'
```

删除原来返回 `review` 的判断。

- [ ] **Step 5: 将旧评分列表地址改为兼容重定向**

`router/index.js` 替换 `/statistics` 路由：

```js
{
  path: '/statistics',
  redirect: {
    path: '/online-meeting',
    query: { tab: 'reports' }
  }
},
```

- [ ] **Step 6: 运行导航测试并确认通过**

Run:

```bash
cd frontend/user
npx playwright test tests/workspace-sidebar-navigation.spec.js tests/online-meeting-validation-alignment.spec.js
```

Expected: 全部 PASS；主导航六项，评分页面选中“现场讲解”，只有协作保留二级菜单。

- [ ] **Step 7: 检查点**

确认桌面侧栏、移动导航、顶部旧式导航和产品预览都共享 `OREP_NAV_ITEMS`，无需额外复制删除逻辑。

### Task 4: 对齐既有评分页面测试并完成视觉回归

**Files:**
- Modify: `frontend/user/tests/review-pages-design.spec.js:42-97`
- Test: `frontend/user/tests/online-meeting-report-tabs.spec.js`
- Test: `frontend/user/tests/workspace-sidebar-navigation.spec.js`
- Test: `frontend/user/tests/online-meeting-validation-alignment.spec.js`
- Test: `frontend/user/tests/review-pages-design.spec.js`

- [ ] **Step 1: 将评分报告视觉测试迁移到新标签**

把报告页测试入口和断言更新为：

```js
test('在线会议评分标签使用嵌入式报告表面并保留可读日期', async ({ page }) => {
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/online-meeting?tab=reports')

  await expect(page.getByRole('heading', { name: '在线会议', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: '评分报告', level: 1 })).toHaveCount(0)
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toBeVisible()
  await expect(page.getByText('2026.06.26 14:16', { exact: false })).toBeVisible()

  const metrics = await page.locator('.score-summary-page.is-embedded').evaluate(root => {
    const card = root.querySelector('.summary-card')
    return {
      borderWidth: getComputedStyle(card).borderTopWidth,
      shadow: getComputedStyle(card).boxShadow,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(metrics.borderWidth).toBe('0px')
  expect(metrics.shadow).toBe('none')
  expect(metrics.noOverflow).toBe(true)
})
```

窄屏测试的评分报告段落改为：

```js
await page.goto('/online-meeting?tab=reports')
await expect(page.getByRole('heading', { name: '报告记录', level: 2 })).toBeVisible()
expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
```

上传评分页的独立布局断言保持不变。

- [ ] **Step 2: 运行本次完整回归集合**

Run:

```bash
cd frontend/user
npx playwright test \
  tests/online-meeting-report-tabs.spec.js \
  tests/workspace-sidebar-navigation.spec.js \
  tests/online-meeting-validation-alignment.spec.js \
  tests/review-pages-design.spec.js
```

Expected: 全部 PASS。

- [ ] **Step 3: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: `vite build` 成功退出，无 Vue 模板、样式或路由错误。

- [ ] **Step 4: 浏览器桌面验收**

在 1545×1071 视口检查：

```text
/online-meeting
/online-meeting?tab=reports
/statistics
/ai-score-upload
/project-team
```

Expected:

- 在线会议默认展示参会记录，一级标签层级清楚。
- 评分标签展示报告范围筛选和上传入口，没有重复“评分报告”大标题或卡片套卡片。
- `/statistics` 到达评分标签。
- 评分深层页主侧栏选中“现场讲解”，不显示复盘二级菜单。
- 协作二级菜单仍正常。

- [ ] **Step 5: 浏览器窄屏验收**

在 390×844 视口检查 `/online-meeting?tab=reports`：

```js
document.documentElement.scrollWidth === window.innerWidth
```

Expected: 返回 `true`；一级标签、报告范围筛选和上传按钮均完整可见。

- [ ] **Step 6: 最终检查点**

记录实际通过的测试数量和构建结果；仅在取得新鲜输出后报告完成。
