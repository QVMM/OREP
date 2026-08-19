# Home Motivational Hero Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic home greeting with truthful training-day encouragement, remove the calendar and action cards, and reflow the remaining home content into a full-width two-column layout.

**Architecture:** Keep the existing home API and core cards. Add two small computed strings for Hero copy, delete the calendar/action template branches and their client-only derivations, then simplify the CSS grid from three columns and six cards to two columns and four cards.

**Tech Stack:** Vue 3 SFC, Playwright, Vite.

---

### Task 1: Replace the old six-card contract

**Files:**
- Modify: `frontend/user/tests/student-prototype-contract.spec.js`
- Modify: `frontend/user/tests/home-training-trend.spec.js`

- [ ] **Step 1: Update the desktop Hero and layout assertions**

Assert the fixture with `camp.currentDay: 4` renders:

```js
await expect(page.getByRole('heading', { name: '张志强，今天是你备赛的第 4 天' })).toBeVisible()
await expect(page.getByText('继续保持节奏，你今天完成的每一步，都在为赛场上的从容积累底气。')).toBeVisible()
```

Keep only `progress`, `today`, `roadshow`, and `score` in the visible card map. Assert the desktop `.student-home` grid has two columns, Hero spans both, the two cards in each row share a `y` coordinate, and the second column is to the right of the first.

- [ ] **Step 2: Assert the removed modules are absent**

Add:

```js
await expect(page.getByTestId('home-rhythm-card')).toHaveCount(0)
await expect(page.getByTestId('home-actions-card')).toHaveCount(0)
await expect(page.getByRole('heading', { name: '训练日历' })).toHaveCount(0)
await expect(page.getByRole('heading', { name: '现在可做' })).toHaveCount(0)
await expect(page.getByRole('link', { name: /完整计划/ })).toHaveCount(0)
```

Remove calendar-day and training-plan assertions from `home-training-trend.spec.js`, while retaining all seven-day learning-duration assertions.

- [ ] **Step 3: Update fallback and responsive assertions**

For the empty payload, assert four home cards and the fallback copy:

```js
await expect(page.locator('[data-testid^="home-"][data-testid$="-card"]')).toHaveCount(4)
await expect(page.getByRole('heading', { name: '同学，今天也向目标更近了一步' })).toBeVisible()
await expect(page.getByText('从一件最重要的事开始，把今天的进度稳稳拿下。')).toBeVisible()
```

At 1024px assert two columns; at 820px assert one column and no horizontal overflow.

- [ ] **Step 4: Run the two focused specs and verify RED**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/student-prototype-contract.spec.js tests/home-training-trend.spec.js --reporter=line
```

Expected: FAIL because the old greeting, calendar, action card, and three-column grid still render.

### Task 2: Implement truthful Hero copy and remove the two modules

**Files:**
- Modify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: Add Hero copy derivations**

Add computed values:

```js
const displayName = computed(() => profile.value.username || '同学')
const trainingDayNumber = computed(() => {
  const value = Number(camp.value.currentDay)
  return Number.isInteger(value) && value > 0 ? value : null
})
const heroTitle = computed(() => trainingDayNumber.value
  ? `${displayName.value}，今天是你备赛的第 ${trainingDayNumber.value} 天`
  : `${displayName.value}，今天也向目标更近了一步`)
const heroEncouragement = computed(() => trainingDayNumber.value
  ? '继续保持节奏，你今天完成的每一步，都在为赛场上的从容积累底气。'
  : '从一件最重要的事开始，把今天的进度稳稳拿下。')
```

Render `heroTitle` in the Hero heading and `heroEncouragement` in the supporting paragraph. Keep the CTA and countdown unchanged.

- [ ] **Step 2: Delete calendar and action templates**

Remove the complete `home-rhythm-card` and `home-actions-card` sections from the template.

- [ ] **Step 3: Remove unused home derivations**

Delete `RouterLink`, `planSummary`, `nextActions`, `homeServerDate`, `currentWeek`, `trainingCalendarDays`, `formatTrainingWeekTitle`, and `buildTrainingCalendarDays`. Keep the date helpers used by the learning-duration chart.

- [ ] **Step 4: Reflow the desktop and responsive grid**

Use:

```css
.student-home:has(.home-hero) {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: 156px 308px 310px;
}

.home-hero { grid-column: 1 / -1; }
.progress-card { grid-column: 1; grid-row: 2; }
.today-card { grid-column: 2; grid-row: 2; }
.roadshow-card { grid-column: 1; grid-row: 3; }
.score-card { grid-column: 2; grid-row: 3; }
```

Remove `.rhythm-card`, `.actions-card`, calendar CSS, and their responsive grid areas. At 1100px retain a two-column `home-grid`; at 900px change it to one column.

- [ ] **Step 5: Run the focused specs and verify GREEN**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/student-prototype-contract.spec.js tests/home-training-trend.spec.js --reporter=line
```

Expected: all tests in both specs pass.

### Task 3: Build and inspect the real home page

**Files:**
- Verify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: Build the user frontend**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite exits with code 0.

- [ ] **Step 2: Check for stale removed-module code**

Run:

```bash
rg -n "home-rhythm-card|home-actions-card|rhythm-card|actions-card|training-calendar|currentWeek|trainingCalendarDays|nextActions|formatTrainingWeekTitle|buildTrainingCalendarDays" frontend/user/src/modules/home/StudentHome.vue
```

Expected: no matches.

- [ ] **Step 3: Inspect `http://localhost:5174/`**

Verify the real page shows the training-day Hero copy, four core cards in a full-width two-column grid, no calendar/action card, and no horizontal overflow.

> This workspace has no Git metadata, so test and build outputs replace commit checkpoints.
