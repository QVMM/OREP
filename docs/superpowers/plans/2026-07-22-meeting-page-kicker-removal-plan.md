# 在线会议与会议回放栏目标签移除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从在线会议和会议回放列表页移除标题上方的“现场讲解”标签及孤立样式，同时保留完整页头功能。

**Architecture:** 不改变组件结构或数据流，仅删除两个静态标签节点及各自的 scoped CSS 规则。扩展现有在线会议 Playwright 测试，在真实路由渲染中验证两页不再出现 `.page-kicker`，且主标题仍可见。

**Tech Stack:** Vue 3、scoped CSS、Vite、Playwright

---

### Task 1: 删除两页栏目标签并验证页头

**Files:**
- Modify: `frontend/user/tests/online-meeting-validation-alignment.spec.js`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:5-10,1676-1682`
- Modify: `frontend/user/src/views/MyRecordings.vue:3-8,1752-1758`

- [x] **Step 1: 扩展接口桩并写入失败的页面测试**

在现有 `beforeEach` 中加入：

```js
await page.route('**/api/recording/my', route => route.fulfill({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ code: 200, data: [] })
}))
```

在文件末尾追加：

```js
test('在线会议和会议回放页头不再显示现场讲解标签', async ({ page }) => {
  await page.goto('/online-meeting')
  await expect(page.locator('.page-head .page-kicker')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '在线会议', level: 1 })).toBeVisible()

  await page.goto('/my-recordings')
  await expect(page.locator('.archive-page-head .page-kicker')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '会议回放', level: 1 })).toBeVisible()
})
```

- [x] **Step 2: 运行新测试并确认它因标签仍存在而失败**

Run:

```bash
cd frontend/user && OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js --grep "不再显示现场讲解标签" --reporter=line
```

Expected: `FAIL`，在线会议页 `.page-kicker` 数量为 `1`。

- [x] **Step 3: 删除两个标签节点和两段孤立样式**

从 `OnlineMeeting.vue` 和 `MyRecordings.vue` 分别删除：

```vue
<span class="page-kicker">现场讲解</span>
```

并分别删除完整的：

```css
.page-kicker {
  display: block;
  margin-bottom: 6px;
  color: var(--ds-orange-action);
  font-size: var(--ds-text-label, 12px);
  font-weight: 700;
}
```

- [x] **Step 4: 运行在线会议测试文件**

Run:

```bash
cd frontend/user && OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js --reporter=line
```

Expected: `2 passed`。

- [x] **Step 5: 运行生产构建**

Run:

```bash
cd frontend/user && npm run build
```

Expected: Vite 构建退出码为 `0`。

- [x] **Step 6: 浏览器核验两页页头**

刷新 `/online-meeting` 并访问 `/my-recordings`，确认“现场讲解”标签消失，主标题、说明和右侧操作区保持正常，无横向溢出。

- [x] **Step 7: 记录版本控制限制**

工作区 `/Users/liuyixing/项目/OREP` 不是 Git 仓库，因此不执行提交。
