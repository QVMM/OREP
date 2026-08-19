# AI Score Todos Compact Header Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove redundant introductory content and metric cards from the AI-score todos page while retaining one compact, truthful coverage status.

**Architecture:** Keep the existing report data and fixed-height workbench unchanged. Simplify only the Vue template and scoped CSS, then use the existing session-26 Playwright flow to prove the redundant content is absent, the compact coverage strip is present, and the workbench scrolling contract remains valid.

**Tech Stack:** Vue 3 SFC, scoped CSS, Playwright, Vite

---

### Task 1: Specify the compact header in the browser test

**Files:**
- Modify: `frontend/user/tests/ai-score-hardening.spec.js`

- [ ] **Step 1: Add assertions for removed and retained information**

After navigating to the todos page, assert that the compact strip exists and the redundant header content does not:

```js
await expect(page.locator('[data-testid="todo-coverage-strip"]')).toContainText('完整队列已覆盖当前 50.5 分差距')
await expect(page.getByText('完整问题一次公开，按优先级逐项兑现。', { exact: true })).toHaveCount(0)
await expect(page.getByText('涉及观测点', { exact: true })).toHaveCount(0)
await expect(page.getByText('失分账目', { exact: true })).toHaveCount(0)
await expect(page.getByText('整改任务', { exact: true })).toHaveCount(0)
await expect(page.getByText('当前差距覆盖率', { exact: true })).toHaveCount(0)
```

- [ ] **Step 2: Run the target test and verify RED**

```bash
cd frontend/user
npx playwright test tests/ai-score-hardening.spec.js --grep "entire 50.5 point gap"
```

Expected: FAIL because the compact strip selector does not exist and the old title/statistics are still rendered.

### Task 2: Remove redundant header content

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`

- [ ] **Step 1: Remove the redundant template blocks**

Delete `.block-label`, `.block-title`, `.block-lead`, and `.portfolio-facts` markup. Keep `.portfolio-status`, add `data-testid="todo-coverage-strip"`, and retain both complete and incomplete coverage branches.

- [ ] **Step 2: Tighten the retained status copy**

For complete coverage, render:

```vue
完整队列已覆盖当前 {{ formatPoints(coverage.coveredGapPoints) }} 分差距。任务可能共同覆盖同一失分，提分区间不可简单相加。
```

Keep the existing incomplete-coverage warning unchanged.

- [ ] **Step 3: Delete orphaned scoped CSS**

Remove `.block-label`, `.block-title`, `.block-lead`, `.portfolio-facts` and their short-screen overrides. Reduce `.portfolio-status` top margin to zero and keep its status semantics.

- [ ] **Step 4: Run the target test and verify GREEN**

```bash
cd frontend/user
npx playwright test tests/ai-score-hardening.spec.js --grep "entire 50.5 point gap"
```

Expected: 1 passed.

### Task 3: Regression and visual verification

**Files:**
- Verify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`
- Verify: `frontend/user/tests/ai-score-hardening.spec.js`

- [ ] **Step 1: Run the full AI-score browser suite**

```bash
cd frontend/user
npm run test:e2e:ai-score
```

Expected: 3 passed.

- [ ] **Step 2: Build the user frontend**

```bash
cd frontend/user
npm run build
```

Expected: Vite exits with code 0.

- [ ] **Step 3: Capture session 26 at 1280×720**

Verify that the compact coverage strip is directly above the workbench and that the left list and right detail panes receive the released height.

- [ ] **Step 4: Record completion without Git operations**

The workspace has no `.git` directory. Preserve verification evidence in command output and the final handoff instead of attempting a commit.

