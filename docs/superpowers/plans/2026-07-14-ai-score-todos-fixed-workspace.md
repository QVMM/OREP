# AI Score Todos Fixed Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the desktop AI-score todos page fit the available report viewport while the task queue and selected task detail scroll independently.

**Architecture:** Preserve the existing Vue component and editorial report shell. Convert the todos content height chain into a bounded flex layout, restrict scrolling to the queue and detail panes on desktop, and restore document scrolling below the existing 900px breakpoint.

**Tech Stack:** Vue 3 SFC, scoped CSS, Playwright, Vite

---

### Task 1: Add a real-browser fixed-workspace regression test

**Files:**
- Modify: `frontend/user/tests/ai-score-hardening.spec.js`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`

- [ ] **Step 1: Add stable layout selectors to the existing template**

Add `data-testid="todos-workspace"` to `.todos-scroll`, `data-testid="todos-layout"` to `.todo-layout`, `data-testid="todo-list"` to `.todo-list`, and `data-testid="todo-detail"` to both `.todo-main` branches.

- [ ] **Step 2: Write the failing browser assertion before changing production CSS**

After the existing todo count and coverage assertions, evaluate the real DOM:

```js
const todosLayout = await page.evaluate(() => {
  const workspace = document.querySelector('[data-testid="todos-workspace"]')
  const layout = document.querySelector('[data-testid="todos-layout"]')
  const list = document.querySelector('[data-testid="todo-list"]')
  const detail = document.querySelector('[data-testid="todo-detail"]')
  const workspaceRect = workspace?.getBoundingClientRect()
  const layoutRect = layout?.getBoundingClientRect()
  return {
    workspaceNoVerticalScroll: workspace ? workspace.scrollHeight <= workspace.clientHeight + 1 : false,
    layoutFitsWorkspace: Boolean(workspaceRect && layoutRect && layoutRect.bottom <= workspaceRect.bottom + 1),
    listScrollsIndependently: list ? list.scrollHeight > list.clientHeight : false,
    detailScrollsIndependently: detail ? detail.scrollHeight > detail.clientHeight : false
  }
})
expect(todosLayout.workspaceNoVerticalScroll).toBe(true)
expect(todosLayout.layoutFitsWorkspace).toBe(true)
expect(todosLayout.listScrollsIndependently).toBe(true)
expect(todosLayout.detailScrollsIndependently).toBe(true)
```

- [ ] **Step 3: Run the target test and confirm RED**

Run:

```bash
cd frontend/user
npx playwright test tests/ai-score-hardening.spec.js --grep "entire 50.5 point gap"
```

Expected: the test fails because the existing `.todos-scroll` scrolls the whole content and the 520px workbench extends past its visible area.

### Task 2: Bound the desktop workspace and isolate scrolling

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`

- [ ] **Step 1: Replace outer scrolling with a bounded flex height chain**

Set `.todos-scroll` to `display: flex; flex-direction: column; overflow: hidden`, and set `.page` to `width: 100%; height: 100%; min-height: 0; display: flex; flex-direction: column; box-sizing: border-box` with reduced bottom padding.

- [ ] **Step 2: Let the workbench consume only the remaining height**

Set `.todo-layout` to `flex: 1 1 auto; min-height: 0; overflow: hidden`. Add `min-height: 0`, `overflow-y: auto`, `overscroll-behavior: contain`, and `scrollbar-gutter: stable` to both `.todo-list` and `.todo-main`.

- [ ] **Step 3: Add short-desktop spacing compression**

Under `@media (max-height: 760px) and (min-width: 901px)`, reduce `.page` padding, top margins, fact-cell padding, and detail padding without hiding content.

- [ ] **Step 4: Restore natural scrolling on narrow screens**

Under the existing `@media (max-width: 900px)`, set `.todos-page` and `.todos-scroll` to natural vertical scrolling, set `.page` height to auto, and allow `.todo-layout` and `.todo-main` to expand in the single-column layout while retaining the left-list maximum height.

- [ ] **Step 5: Run the target Playwright test and confirm GREEN**

Run:

```bash
cd frontend/user
npx playwright test tests/ai-score-hardening.spec.js --grep "entire 50.5 point gap"
```

Expected: 1 passed.

### Task 3: Regression verification

**Files:**
- Verify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`
- Verify: `frontend/user/tests/ai-score-hardening.spec.js`

- [ ] **Step 1: Run the full AI-score browser suite**

```bash
cd frontend/user
npm run test:e2e:ai-score
```

Expected: all AI-score Playwright tests pass.

- [ ] **Step 2: Build the user frontend**

```bash
cd frontend/user
npm run build
```

Expected: Vite exits with code 0 and produces the production bundle.

- [ ] **Step 3: Review the rendered desktop page**

Open session 26 at `/ai-score/report/26/todos` and verify that the browser page itself does not move vertically, the top summary remains visible, and the two workbench panes scroll independently.

- [ ] **Step 4: Record completion without a Git commit**

This workspace has no `.git` directory, so store verification evidence in the command output and final delivery summary rather than attempting a commit.

