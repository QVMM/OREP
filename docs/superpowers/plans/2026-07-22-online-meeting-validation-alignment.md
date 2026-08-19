# 在线路演入会表单错误提示对齐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让会议号单列出现校验提示时，会议号与密码字段仍保持顶部和输入框基线对齐。

**Architecture:** 新增一个 Playwright 视觉几何回归测试，触发仅会议号字段报错并读取标签、输入框与错误文本的边界坐标。生产修复只调整 `OnlineMeeting.vue` 的 `.fields` 网格交叉轴对齐方式，保留错误文本的静态文档流布局。

**Tech Stack:** Vue 3、Element Plus Form、scoped CSS、Playwright、Vite。

---

## File map

- Create `frontend/user/tests/online-meeting-validation-alignment.spec.js`: 复现并锁定单列错误状态的几何对齐。
- Modify `frontend/user/src/views/OnlineMeeting.vue`: 将入会字段网格改为顶部对齐。

### Task 1: 用失败测试复现输入框被顶高

**Files:**
- Create: `frontend/user/tests/online-meeting-validation-alignment.spec.js`

- [ ] **Step 1: 创建页面夹具并触发单列错误**

```js
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('orep_user_token', 'meeting-alignment-token'))
  await page.route('**/api/meeting/my-history', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
})

test('会议号单列报错时入会字段仍保持顶部对齐', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/online-meeting')
  await page.getByPlaceholder('密码').fill('123456')
  await page.getByRole('button', { name: '进入路演室' }).click()
  await expect(page.getByText('请输入会议号', { exact: true })).toBeVisible()
```

- [ ] **Step 2: 增加几何对齐断言**

```js
  const fields = page.locator('.fields')
  const codeField = fields.locator('.field').nth(0)
  const passwordField = fields.locator('.field').nth(1)
  const metrics = await fields.evaluate(container => {
    const rows = container.querySelectorAll('.field')
    const codeLabel = rows[0].querySelector('.el-form-item__label').getBoundingClientRect()
    const passwordLabel = rows[1].querySelector('.el-form-item__label').getBoundingClientRect()
    const codeInput = rows[0].querySelector('.el-input__wrapper').getBoundingClientRect()
    const passwordInput = rows[1].querySelector('.el-input__wrapper').getBoundingClientRect()
    const error = rows[0].querySelector('.el-form-item__error').getBoundingClientRect()
    return {
      labelDelta: Math.abs(codeLabel.top - passwordLabel.top),
      inputDelta: Math.abs(codeInput.top - passwordInput.top),
      errorBelowInput: error.top >= codeInput.bottom
    }
  })
  expect(metrics.labelDelta).toBeLessThanOrEqual(1)
  expect(metrics.inputDelta).toBeLessThanOrEqual(1)
  expect(metrics.errorBelowInput).toBe(true)
  await expect(codeField).toBeVisible()
  await expect(passwordField).toBeVisible()
})
```

- [ ] **Step 3: 运行聚焦测试并确认红灯**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js --reporter=line
```

Expected: FAIL，`labelDelta` 和 `inputDelta` 大于 1px。

### Task 2: 实现顶部对齐并验证

**Files:**
- Modify: `frontend/user/src/views/OnlineMeeting.vue:916`

- [ ] **Step 1: 修改网格对齐方式**

```css
.fields {
  display: grid;
  grid-template-columns: 1fr 1fr minmax(132px, auto);
  gap: 12px 12px;
  align-items: start;
}
```

- [ ] **Step 2: 重跑聚焦测试并确认绿灯**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js --reporter=line
```

Expected: 1 test passes。

- [ ] **Step 3: 运行相关回归和生产构建**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/online-meeting-validation-alignment.spec.js tests/student-prototype-contract.spec.js --grep "会议号单列报错|在线路演" --reporter=line
npm run build
```

Expected: 相关测试通过，Vite build exits with code 0；现有大分块提示仍为非阻塞警告。

- [ ] **Step 4: 浏览器验证**

在真实 `/online-meeting` 页面触发“请输入会议号”，确认标签和输入框保持对齐，错误提示位于输入框下方，控制台无错误。

## Workspace note

当前目录没有 `.git` 元数据，因此不包含提交步骤。
