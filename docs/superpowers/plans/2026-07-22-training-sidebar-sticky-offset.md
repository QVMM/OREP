# Training Sidebar Sticky Offset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the training attachment and submission sidebar exactly 40px below the workspace top bar while scrolling on desktop.

**Architecture:** The workspace content is already laid out below the fixed top bar and has 40px top padding. Set the sidebar sticky offset to `top: 0` so that the existing content padding produces the required 40px visual gap; retain max-height, internal scrolling, and the 1080px breakpoint that returns the sidebar to normal document flow.

**Tech Stack:** Vue 3 scoped CSS, Playwright.

---

### Task 1: Lock desktop and narrow-screen sticky behavior

**Files:**
- Modify: `frontend/user/tests/training-copy.spec.js`

- [ ] **Step 1: Add the failing desktop assertion**

Before changing the viewport to 900px, assert the computed sidebar position:

```js
await expect.poll(() => page.evaluate(() => {
  const style = getComputedStyle(document.querySelector('.training-side'))
  return { position: style.position, top: style.top }
})).toEqual({ position: 'sticky', top: '0px' })
```

- [ ] **Step 2: Add the narrow-screen assertion**

After setting the viewport to 900px, assert that the sidebar no longer sticks:

```js
await expect.poll(() => page.evaluate(() => {
  const style = getComputedStyle(document.querySelector('.training-side'))
  return { position: style.position, top: style.top }
})).toEqual({ position: 'static', top: 'auto' })
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-copy.spec.js --reporter=line
```

Expected: FAIL because the desktop computed `top` is not `0px` and therefore duplicates the content area's existing 40px padding.

### Task 2: Correct the sidebar offset

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingDayView.vue`

- [ ] **Step 1: Change the desktop sticky top value**

Replace the current header-height calculation with the approved content-scrollport offset:

```css
.training-side {
  position: sticky;
  top: 0;
}
```

Keep the existing `max-height`, internal overflow, and the `@media (max-width: 1080px)` reset.

- [ ] **Step 2: Run the focused test and verify GREEN**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-copy.spec.js --reporter=line
```

Expected: `1 passed`.

### Task 3: Build and visually verify the sticky gap

**Files:**
- Verify: `frontend/user/src/modules/training/TrainingDayView.vue`

- [ ] **Step 1: Build the user frontend**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite exits with code 0.

- [ ] **Step 2: Verify the real page while scrolled**

Open `http://localhost:5174/training/days/22`, scroll the main content, and verify the visual gap between the sidebar and the top bar is 40px, with both attachment and submission cards visible and no horizontal overflow.

> This workspace has no Git metadata, so test and build outputs replace commit checkpoints.
