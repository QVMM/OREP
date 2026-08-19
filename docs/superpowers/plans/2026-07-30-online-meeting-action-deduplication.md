# Online Meeting Action Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除在线会议页重复的创建与上传入口，让“创建会议”和“上传评分”各自只保留一个稳定位置。

**Architecture:** `OnlineMeeting.vue` 只保留页头创建入口和入会卡片的记住凭证控件；`Statistics.vue` 只保留页头或嵌入式工具栏上传入口，空状态改为纯说明。Playwright 先锁定入口唯一性和空状态文案，再进行最小模板、函数和死样式清理。

**Tech Stack:** Vue 3 `<script setup>`、Vue Router、项目基础按钮组件、Playwright、Vite

**Design Spec:** `docs/superpowers/specs/2026-07-30-online-meeting-action-deduplication-design.md`

**Version-control note:** 当前目录没有 Git 元数据，因此使用检查点代替提交步骤，不执行或模拟 Git 提交。

---

## File Map

- Modify: `frontend/user/tests/online-meeting-report-tabs.spec.js`
  - 锁定创建入口、上传入口和空状态操作的唯一性。
- Modify: `frontend/user/src/views/OnlineMeeting.vue`
  - 删除入会卡片底部重复操作、不再使用的跳转函数及相关死样式。
- Modify: `frontend/user/src/views/Statistics.vue`
  - 删除空状态上传按钮并精简说明文字。

### Task 1: 用失败测试锁定单一操作入口

**Files:**
- Modify: `frontend/user/tests/online-meeting-report-tabs.spec.js:36-67`
- Modify: `frontend/user/tests/online-meeting-report-tabs.spec.js:107-142`

- [ ] **Step 1: 在默认参会记录测试中排除入会卡片重复操作**

在默认页面断言后加入：

```js
await expect(page.getByRole('button', { name: '创建会议', exact: true })).toHaveCount(1)
await expect(page.getByRole('button', { name: '没有会议？创建本场', exact: true })).toHaveCount(0)
await expect(page.getByRole('button', { name: '上传视频评分', exact: true })).toHaveCount(0)
await expect(page.locator('.join-foot')).toContainText('记住本机号与密码')
```

切换评分报告后，将上传入口断言加强为：

```js
const uploadLinks = page.getByRole('link', { name: '上传评分', exact: true })
await expect(uploadLinks).toHaveCount(1)
await expect(page.locator('.report-toolbar').getByRole('link', {
  name: '上传评分',
  exact: true
})).toBeVisible()
```

- [ ] **Step 2: 增加空状态无重复按钮测试**

在同一测试文件新增：

```js
test('评分空状态只保留工具栏上传入口', async ({ page }) => {
  await page.unroute('**/api/ai-score/reports/summary?*')
  await page.route('**/api/ai-score/reports/summary?*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))

  await page.goto('/online-meeting?tab=reports')

  await expect(page.getByText('上传完整路演视频后，评分报告会显示在这里。', {
    exact: true
  })).toBeVisible()
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toHaveCount(1)
  await expect(page.locator('.empty-state .base-button')).toHaveCount(0)

  await page.getByRole('tab', { name: '我队伍的会议 0', exact: true }).click()
  await expect(page.getByText('团队完成路演评分后，报告会显示在这里。', {
    exact: true
  })).toBeVisible()
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toHaveCount(1)
  await expect(page.locator('.empty-state .base-button')).toHaveCount(0)
})
```

- [ ] **Step 3: 运行测试并确认因当前重复入口而失败**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 \
  npx playwright test tests/online-meeting-report-tabs.spec.js
```

Expected: FAIL，当前仍能找到“没有会议？创建本场”“上传视频评分”，空状态仍有第二个“上传评分”，旧说明文字也不匹配。

- [ ] **Step 4: 检查点**

确认失败来自本次入口精简要求，而不是登录、API mock、路由或浏览器协议错误。

### Task 2: 删除重复入口并清理死代码

**Files:**
- Modify: `frontend/user/src/views/OnlineMeeting.vue:87-104`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:657-659`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:1088-1154`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:1544-1575`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:1639-1643`
- Modify: `frontend/user/src/views/OnlineMeeting.vue:1818-1827`
- Modify: `frontend/user/src/views/Statistics.vue:51-55`
- Test: `frontend/user/tests/online-meeting-report-tabs.spec.js`

- [ ] **Step 1: 精简入会卡片底部模板**

将 `join-foot` 改为只保留记住凭证控件：

```vue
<div class="join-foot">
  <button
    type="button"
    class="remember"
    :class="{ on: rememberCredentials }"
    role="checkbox"
    :aria-checked="rememberCredentials"
    @click="rememberCredentials = !rememberCredentials"
  >
    <span class="box" aria-hidden="true" />
    记住本机号与密码
  </button>
</div>
```

不得改动页头“创建会议”、加入按钮、创建弹窗或记住凭证行为。

- [ ] **Step 2: 删除不再使用的上传跳转函数**

从 `OnlineMeeting.vue` 删除：

```js
const goVideoScoreUpload = () => {
  router.push('/ai-score-upload')
}
```

保留 `goRecordings`、`goAiScore` 和其他路由函数。

- [ ] **Step 3: 清理入会卡片重复入口的死样式**

删除 `.foot-links`、`.foot-links .sep`、`.foot-links button` 和 `.foot-links button:hover` 四个完整规则。

并从组合选择器中移除 `.foot-links button` 或 `.foot-links button:hover`，清理后相关规则应为：

```css
.btn,
.tabs button,
.row-acts .act,
.remember,
.duration .step,
.check {
  transition: color 150ms ease-in-out, background-color 150ms ease-in-out, border-color 150ms ease-in-out;
}

.btn:focus-visible,
.tabs button:focus-visible,
.row:focus-visible,
.row-acts .act:focus-visible,
.remember:focus-visible,
.duration .step:focus-visible,
.check:focus-visible {
  outline: 2px solid var(--ds-orange-action, #cf3d12);
  outline-offset: 2px;
}

.row:hover .title,
.row-acts .act {
  color: var(--ds-orange-800, #b12f0a);
}

.remember {
  min-height: 40px;
}
```

同时把 `join-foot` 的横向对齐明确为：

```css
.join-foot {
  justify-content: flex-start;
}
```

- [ ] **Step 4: 将评分空状态改为纯说明**

把 `Statistics.vue` 空状态替换为：

```vue
<div v-else-if="!activeReports.length" class="empty-state">
  <strong>{{ activeTab === 'participant' ? '还没有我参加的评分报告' : '还没有团队评分报告' }}</strong>
  <p>{{ activeTab === 'participant' ? '上传完整路演视频后，评分报告会显示在这里。' : '团队完成路演评分后，报告会显示在这里。' }}</p>
</div>
```

保留报告工具栏嵌入式“上传评分”、独立页头“上传评分”和错误状态“重新加载”。

- [ ] **Step 5: 运行入口精简测试并确认通过**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 \
  npx playwright test tests/online-meeting-report-tabs.spec.js
```

Expected: 5 tests PASS。

- [ ] **Step 6: 运行入会布局与评分视觉回归**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 \
  npx playwright test \
  tests/online-meeting-validation-alignment.spec.js \
  tests/review-pages-design.spec.js
```

Expected: 8 tests PASS；入会表单、独立上传页、评分表面和窄屏布局保持正常。

- [ ] **Step 7: 运行完整相关回归**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 \
  npx playwright test \
  tests/online-meeting-report-tabs.spec.js \
  tests/workspace-sidebar-navigation.spec.js \
  tests/online-meeting-validation-alignment.spec.js \
  tests/review-pages-design.spec.js
```

Expected: 24 tests PASS。

- [ ] **Step 8: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: `vite build` 退出码为 0，无 Vue 模板、路由或样式编译错误。

- [ ] **Step 9: 浏览器验收**

桌面打开：

```text
http://localhost:5174/online-meeting
http://localhost:5174/online-meeting?tab=reports
```

检查：

- 页头只显示一个“创建会议”。
- 入会卡片底部只显示“记住本机号与密码”。
- 评分报告工具栏只显示一个“上传评分”。
- 空状态没有按钮，说明文字完整。

在 390×844 视口重复检查评分报告标签，确认无横向滚动、主标签和唯一上传入口完整可见。

- [ ] **Step 10: 最终检查点**

记录新鲜测试数量、构建结果和浏览器唯一入口数量后再报告完成。
