# 工作区侧栏选中态实心图标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让桌面侧栏仅当前路由对应的图标使用实心版本，其余导航图标继续使用线框版本。

**Architecture:** 继续复用 `WorkspaceModuleIcon.vue` 已有的 `outline`/`filled` 双态图标数据，不增加依赖或重复 SVG。`WorkspaceSidebar.vue` 使用现有 `isOrepRouteActive()` 结果同时控制链接当前态和图标 `variant`，确保路由变化时两者同步。

**Tech Stack:** Vue 3、Vue Router、Playwright、Vite

---

### Task 1: 用回归测试定义桌面导航的双态图标规则

**Files:**
- Modify: `frontend/user/tests/workspace-sidebar-navigation.spec.js:62-64`
- Test: `frontend/user/tests/workspace-sidebar-navigation.spec.js`

- [x] **Step 1: 在现有训练营当前态测试中加入图标断言**

在训练营链接当前态断言之后加入：

```js
const trainingIcon = trainingLink.locator('.workspace-module-icon')
const activeIconColor = await trainingLink.evaluate(
  element => getComputedStyle(element).color,
)

await expect(trainingIcon).toHaveClass(/\bis-filled\b/)
await expect(trainingIcon).toHaveCSS('fill', activeIconColor)

for (const link of await links.all()) {
  if (await link.getAttribute('aria-current') === 'page') continue
  await expect(link.locator('.workspace-module-icon')).toHaveClass(/\bis-outline\b/)
}
```

- [x] **Step 2: 在现场讲解子路由测试中验证状态随路由同步**

在现场讲解当前态断言之后加入：

```js
const roadshowIcon = roadshowLink.locator('.workspace-module-icon')
const trainingIcon = page
  .getByRole('navigation', { name: '用户端主导航' })
  .getByRole('link', { name: '训练营', exact: true })
  .locator('.workspace-module-icon')

await expect(roadshowIcon).toHaveClass(/\bis-filled\b/)
await expect(trainingIcon).toHaveClass(/\bis-outline\b/)
```

- [x] **Step 3: 运行测试并确认因当前项仍为线框而失败**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/workspace-sidebar-navigation.spec.js
```

Expected: FAIL，训练营图标实际类名包含 `is-outline`，不包含 `is-filled`。

### Task 2: 让图标样式跟随现有路由激活态

**Files:**
- Modify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue:27-29`
- Test: `frontend/user/tests/workspace-sidebar-navigation.spec.js`

- [x] **Step 1: 将固定线框参数改为基于路由激活态的双态参数**

把图标调用改为：

```vue
<WorkspaceModuleIcon
  :name="item.group"
  :variant="isOrepRouteActive(route, item.path) ? 'filled' : 'outline'"
/>
```

- [x] **Step 2: 运行侧栏导航测试并确认通过**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/workspace-sidebar-navigation.spec.js
```

Expected: 全部通过，训练营和现场讲解路由下均只有当前项为 `is-filled`。

- [x] **Step 3: 运行侧栏壳层回归**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/workspace-sidebar-navigation.spec.js tests/workspace-route-shell-stability.spec.js
```

Expected: 全部通过，无导航、尺寸、气泡或路由回归。

- [x] **Step 4: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite 构建退出码为 0。

### Task 3: 浏览器视觉验收

**Files:**
- Verify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- Verify: `frontend/user/src/components/workspace/WorkspaceModuleIcon.vue`

- [x] **Step 1: 在训练营页面检查选中态**

打开 `http://localhost:5174/training/today`，确认训练营图标为深色实心，首页、现场讲解、复盘、协作、AI 应用中心和我的仍为线框。

- [x] **Step 2: 切换路由检查状态转移**

进入现场讲解页面，确认现场讲解图标切换为实心，训练营恢复为线框；按钮仍为 52×52px，图标仍为 28×28px，气泡和箭头保持原样。

- [x] **Step 3: 检查无障碍与视觉边界**

确认当前链接仍具有 `aria-current="page"`，实心图标未超出 24×24 `viewBox`，侧栏没有新增横向滚动。
