# 正式考试右侧栏对齐修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让桌面端答题卡顶部与左侧答题面板顶部精确对齐，同时保留右栏吸顶、卡片间距和窄屏单栏布局。

**Architecture:** 复用 `ExamTaking.vue` 现有 CSS Grid，仅统一 `.answer-side` 两处重复的 sticky `top` 值。扩展已有 Playwright 回归文件，通过真实渲染后的边界坐标与计算样式验证顶部基线、卡片间距和 sticky 行为。

**Tech Stack:** Vue 3 scoped CSS、Vite、Playwright

---

### Task 1: 修正并验证右侧栏顶部基线

**Files:**
- Modify: `frontend/user/tests/exam-topbar-alignment.spec.js`
- Modify: `frontend/user/src/views/ExamTaking.vue:704-709,1121-1124`

- [x] **Step 1: 写入失败的桌面端顶部对齐测试**

在 `frontend/user/tests/exam-topbar-alignment.spec.js` 追加：

```js
test('桌面端答题卡与左侧答题面板顶部对齐', async ({ page }) => {
  await page.setViewportSize({ width: 1284, height: 892 })
  await page.goto('/exam-system/take/7')

  const alignment = await page.locator('.take-layout').evaluate(layout => {
    const question = layout.querySelector('.question-stage').getBoundingClientRect()
    const answerSide = layout.querySelector('.answer-side')
    const panels = [...answerSide.querySelectorAll(':scope > .side-panel')]
      .map(panel => panel.getBoundingClientRect())

    return {
      questionTop: question.top,
      firstPanelTop: panels[0].top,
      panelGap: panels[1].top - panels[0].bottom,
      position: getComputedStyle(answerSide).position,
      stickyTop: getComputedStyle(answerSide).top
    }
  })

  expect(Math.abs(alignment.firstPanelTop - alignment.questionTop)).toBeLessThanOrEqual(1)
  expect(alignment.panelGap).toBeCloseTo(14, 0)
  expect(alignment.position).toBe('sticky')
  expect(alignment.stickyTop).toBe('90px')
})
```

- [x] **Step 2: 运行测试并确认当前约 52px 的错位会导致失败**

Run:

```bash
cd frontend/user && OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/exam-topbar-alignment.spec.js --grep "答题卡与左侧答题面板" --reporter=line
```

Expected: `FAIL`，`firstPanelTop - questionTop` 约为 `52px`。

- [x] **Step 3: 最小化修正两处 sticky 偏移**

在 `frontend/user/src/views/ExamTaking.vue` 的两处桌面端 `.answer-side` 规则中，将现有 `top` 声明统一替换为：

```css
top: 90px;
```

保留 `position: sticky`、`gap: 14px` 与 `@media (max-width: 1100px)` 中的 `position: static`。

- [x] **Step 4: 运行完整对齐回归测试**

Run:

```bash
cd frontend/user && OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/exam-topbar-alignment.spec.js --reporter=line
```

Expected: `3 passed`。

- [x] **Step 5: 运行生产构建**

Run:

```bash
cd frontend/user && npm run build
```

Expected: Vite 构建退出码为 `0`，无 Vue 或 CSS 编译错误。

- [x] **Step 6: 刷新当前页面并测量实际基线**

刷新 `http://localhost:5174/exam-system/take/7`，确认 `.question-stage` 与第一个 `.side-panel` 的 `top` 坐标差不超过 `1px`，且右侧两卡片保持 `14px` 间距。

- [x] **Step 7: 记录版本控制限制**

工作区 `/Users/liuyixing/项目/OREP` 不是 Git 仓库，因此不执行提交；交付时列出修改文件和验证结果。
