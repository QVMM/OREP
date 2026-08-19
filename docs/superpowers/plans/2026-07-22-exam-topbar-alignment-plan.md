# 正式考试顶栏对齐修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让正式考试答题页顶栏内容在桌面端准确垂直居中，并与视口左右边缘保持一致的安全间距。

**Architecture:** 保留 `ExamTaking.vue` 现有三栏网格和移动端断点，只修正两处重复的桌面端 `.exam-topbar` 内边距声明。新增一个 Playwright 回归测试，通过真实渲染后的元素边界验证垂直中心线、标题水平中心线及左右间距。

**Tech Stack:** Vue 3 scoped CSS、Vite、Playwright

---

### Task 1: 修正并验证考试顶栏对齐

**Files:**
- Create: `frontend/user/tests/exam-topbar-alignment.spec.js`
- Modify: `frontend/user/src/views/ExamTaking.vue:318-330,963-966`

- [x] **Step 1: 写入失败的浏览器回归测试**

创建 `frontend/user/tests/exam-topbar-alignment.spec.js`：

```js
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'exam-topbar-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '李林峰', role: 'STUDENT' }))
  })

  await page.route('**/api/exams/7/start', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        attemptId: 70,
        title: '测试',
        deadlineAt: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
        questions: [{
          id: 1,
          questionType: 'judge',
          stem: '考试倒计时应只依赖前端本地时间。',
          score: 5,
          optionsJson: JSON.stringify([
            { key: 'A', text: '正确' },
            { key: 'B', text: '错误' }
          ])
        }]
      }
    })
  }))
})

test('桌面端顶栏内容垂直居中且标题以视口为基准水平居中', async ({ page }) => {
  await page.setViewportSize({ width: 1284, height: 892 })
  await page.goto('/exam-system/take/7')

  const topbar = page.locator('.exam-topbar')
  const topbarBox = await topbar.boundingBox()
  const groups = [
    page.locator('.back-link'),
    page.locator('.paper-title'),
    page.locator('.status-cluster')
  ]

  for (const group of groups) {
    const box = await group.boundingBox()
    expect(Math.abs((box.y + box.height / 2) - (topbarBox.y + topbarBox.height / 2))).toBeLessThanOrEqual(1)
  }

  const titleBox = await page.locator('.paper-title').boundingBox()
  expect(Math.abs((titleBox.x + titleBox.width / 2) - 1284 / 2)).toBeLessThanOrEqual(1)

  const backBox = await page.locator('.back-link').boundingBox()
  const statusBox = await page.locator('.status-cluster').boundingBox()
  expect(backBox.x).toBeGreaterThanOrEqual(24)
  expect(1284 - (statusBox.x + statusBox.width)).toBeGreaterThanOrEqual(24)
})
```

- [x] **Step 2: 运行测试并确认它因当前错位而失败**

Run:

```bash
cd frontend/user && OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/exam-topbar-alignment.spec.js --reporter=line
```

Expected: `FAIL`，垂直中心差值约为 `12px`，或左右间距小于 `24px`。

- [x] **Step 3: 最小化修正两处桌面端样式声明**

在 `frontend/user/src/views/ExamTaking.vue` 的两处桌面端 `.exam-topbar` 规则中，将：

```css
padding: 0 0 var(--ds-space-6, 24px);
```

替换为：

```css
padding: 0 var(--ds-space-6, 24px);
```

保留 `@media (max-width: 760px)` 中的 `padding: 14px`，不改动移动端布局。

- [x] **Step 4: 重新运行回归测试并确认通过**

Run:

```bash
cd frontend/user && OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/exam-topbar-alignment.spec.js --reporter=line
```

Expected: `1 passed`。

- [x] **Step 5: 运行生产构建**

Run:

```bash
cd frontend/user && npm run build
```

Expected: Vite 构建退出码为 `0`，无 CSS 或 Vue 编译错误。

- [x] **Step 6: 在当前浏览器页面完成视觉验收**

刷新 `http://localhost:5174/exam-system/take/7`，在 `1284×892` 视口确认：返回按钮、标题、保存状态和倒计时在顶栏内垂直居中；标题位于视口水平中心；左右内容不贴边。

- [x] **Step 7: 记录版本控制限制**

工作区 `/Users/liuyixing/项目/OREP` 不是 Git 仓库，因此不执行提交；交付时列出新增测试与修改文件。
