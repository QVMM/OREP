# 路演页面导航简化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除路演模块的重复二级菜单，并让在线会议与会议回放列表通过页头按钮双向跳转。

**Architecture:** `WorkspaceShell.vue` 继续集中决定哪些模块显示二级导航，但将范围收窄为复盘与协作。在线会议保留现有 `/my-recordings` 跳转，会议回放页新增语义化路由链接返回 `/online-meeting`，不改会议和录制业务数据流。

**Tech Stack:** Vue 3、Vue Router、Playwright、Vite

---

### Task 1: 用回归测试定义路演壳层与双向跳转

**Files:**
- Modify: `frontend/user/tests/online-meeting-validation-alignment.spec.js:58`
- Test: `frontend/user/tests/online-meeting-validation-alignment.spec.js`

- [x] **Step 1: 添加路演二级菜单移除测试**

在测试文件末尾加入：

```js
test('路演页面不再渲染二级菜单且其他模块菜单保持不变', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })

  await page.goto('/online-meeting')
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
  await expect(page.locator('.workspace-app')).not.toHaveClass(/\bhas-module-nav\b/)

  await page.goto('/my-recordings')
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
  await expect(page.locator('.workspace-app')).not.toHaveClass(/\bhas-module-nav\b/)

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: {} })
  }))

  await page.goto('/statistics')
  await expect(page.getByRole('navigation', { name: '复盘改进二级导航' })).toBeVisible()

  await page.goto('/project-team')
  await expect(page.getByRole('navigation', { name: '团队协作二级导航' })).toBeVisible()
})
```

- [x] **Step 2: 添加在线会议与会议回放双向跳转测试**

在同一文件继续加入：

```js
test('在线会议与会议回放可通过页头操作双向切换', async ({ page }) => {
  await page.goto('/online-meeting')
  await page.getByRole('button', { name: '查看回放', exact: true }).click()
  await expect(page).toHaveURL('/my-recordings')

  const returnLink = page.getByRole('link', { name: '返回在线会议', exact: true })
  await expect(returnLink).toBeVisible()
  await returnLink.click()
  await expect(page).toHaveURL('/online-meeting')
})
```

- [x] **Step 3: 添加窄屏操作区边界测试**

在同一文件继续加入：

```js
test('会议回放页头操作在窄屏保持完整且不产生横向滚动', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/my-recordings')

  await expect(page.getByRole('link', { name: '返回在线会议', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '刷新', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})
```

- [x] **Step 4: 运行测试并确认新需求尚未实现**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js
```

Expected: FAIL，`/online-meeting` 仍存在 `.workspace-module-nav`，且 `/my-recordings` 找不到“返回在线会议”链接。

### Task 2: 从工作区壳层移除路演二级菜单

**Files:**
- Modify: `frontend/user/src/components/workspace/WorkspaceShell.vue:54-58`
- Test: `frontend/user/tests/online-meeting-validation-alignment.spec.js`

- [x] **Step 1: 收窄二级导航显示范围**

将 `hasModuleNav` 改为：

```js
const hasModuleNav = computed(() => (
  moduleGroup.value === 'review'
  || moduleGroup.value === 'collaboration'
))
```

- [x] **Step 2: 运行壳层测试并确认路演页面断言通过**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js --grep "路演页面不再渲染二级菜单"
```

Expected: PASS，路演两页无二级导航，复盘与协作仍有二级导航。

### Task 3: 为会议回放页增加返回在线会议入口

**Files:**
- Modify: `frontend/user/src/views/MyRecordings.vue:8-17`
- Modify: `frontend/user/src/views/MyRecordings.vue:1771-1826`
- Modify: `frontend/user/src/views/MyRecordings.vue:2127-2171`
- Test: `frontend/user/tests/online-meeting-validation-alignment.spec.js`

- [x] **Step 1: 在页头操作区加入路由链接**

在状态提示与刷新按钮之间加入：

```vue
<router-link class="return-meeting-action" to="/online-meeting">
  返回在线会议
</router-link>
```

- [x] **Step 2: 复用次级按钮视觉并补齐键盘焦点**

将最终生效的页头操作样式调整为：

```css
.archive-head-actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 8px);
}

.return-meeting-action,
.refresh-action {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: var(--ds-radius-pill);
  color: var(--ds-ink-2);
  background: var(--ds-btn-secondary-bg);
  font-size: var(--ds-text-caption, 13px);
  font-weight: 700;
}

.return-meeting-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  white-space: nowrap;
}

.return-meeting-action:hover,
.refresh-action:hover:not(:disabled) {
  color: var(--ds-orange-deep);
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-btn-secondary-bg-hover);
}
```

将焦点选择器加入 `.return-meeting-action`：

```css
:is(.return-meeting-action, .refresh-action, .status-switch button, .detail-toggle, .asset-btn, .delete-action, .empty-action):focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}
```

- [x] **Step 3: 让窄屏操作区分为状态行与按钮行**

在 `@media (max-width: 640px)` 中使用：

```css
.archive-head-actions {
  width: 100%;
  flex-wrap: wrap;
}

.archive-signal {
  flex: 1 1 100%;
}

.return-meeting-action,
.refresh-action {
  flex: 1 1 0;
  margin-left: 0;
}
```

- [x] **Step 4: 运行在线会议测试文件**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js
```

Expected: 全部通过，双向跳转、菜单范围和窄屏边界均符合要求。

### Task 4: 回归、构建与浏览器验收

**Files:**
- Verify: `frontend/user/src/components/workspace/WorkspaceShell.vue`
- Verify: `frontend/user/src/views/OnlineMeeting.vue`
- Verify: `frontend/user/src/views/MyRecordings.vue`

- [x] **Step 1: 运行相关工作区回归**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js tests/workspace-sidebar-navigation.spec.js tests/workspace-route-shell-stability.spec.js
```

Expected: 所有相关测试通过。

- [x] **Step 2: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite 构建退出码为 0。

- [x] **Step 3: 在浏览器检查桌面路演流程**

在 1545×1071 视口打开 `/online-meeting`，确认“路演中心”二级栏消失、内容向左扩展、主侧栏“现场讲解”仍选中。点击“查看回放”，确认进入 `/my-recordings` 并显示“返回在线会议”；点击返回按钮，确认回到在线会议。

- [x] **Step 4: 在浏览器检查保留的二级菜单**

打开 `/statistics` 与 `/project-team`，确认“复盘改进”和“团队协作”二级菜单仍正常显示。
