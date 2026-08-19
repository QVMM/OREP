# Home Training Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated “本周节奏 + 今日任务” block with a seven-row training calendar that always shows every date in the active training week.

**Architecture:** Keep the existing home API. `StudentHome.vue` selects the current training week using the server date, generates seven consecutive date slots from the week start, and merges published training days by date. Published rows are links; unplanned rows are inert calendar entries with explicit past, today, or future copy.

**Tech Stack:** Vue 3 Composition API, Vue Router, scoped CSS, Playwright, Vite.

---

## File map

- Modify `frontend/user/tests/home-training-trend.spec.js`: define the seven-day calendar behavior and duplicate-removal contract.
- Modify `frontend/user/src/modules/home/StudentHome.vue`: select the current week, build calendar rows, render link and non-link states, and replace the old rhythm styles.

### Task 1: Define the calendar behavior with a failing test

**Files:**
- Modify: `frontend/user/tests/home-training-trend.spec.js`

- [ ] **Step 1: Reduce the weekly fixture to one published day**

Use a training week from 2026-07-20 to 2026-07-26 and keep only this day:

```js
days: [{
  dayId: 4,
  dayNo: 4,
  trainingDate: '2026-07-22',
  title: '提交组件结构说明',
  progressStatus: 'TODAY'
}]
```

The existing `weeklyLearning.serverDate` remains `2026-07-22`, so two dates are past and four are future.

- [ ] **Step 2: Add the calendar and duplicate-removal assertions**

```js
const calendar = page.getByTestId('home-training-calendar')
await expect(page.getByTestId('home-rhythm-card').getByRole('heading', { name: '训练日历' })).toBeVisible()
await expect(calendar.locator('.training-calendar-day')).toHaveCount(7)
await expect(calendar.locator('a.training-calendar-day')).toHaveCount(1)
await expect(calendar.locator('.training-calendar-day.is-past-empty')).toHaveCount(2)
await expect(calendar.locator('.training-calendar-day.is-future-empty')).toHaveCount(4)
await expect(calendar.getByText('无安排', { exact: true })).toHaveCount(2)
await expect(calendar.getByText('待安排', { exact: true })).toHaveCount(4)
await expect(calendar.getByText('进行中', { exact: true })).toHaveCount(1)
await expect(page.locator('.rhythm-today-task')).toHaveCount(0)
await expect(page.locator('.student-home a[href="/training/days/4"]')).toHaveCount(1)
```

Keep the existing route deduplication assertions for `/online-meeting`, `/training/plan`, the score report, and `/training/today`.

- [ ] **Step 3: Run the focused test and verify the red state**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js --reporter=line
```

Expected: fails because the current heading is “本周节奏”, only published days render, and `.rhythm-today-task` still exists.

### Task 2: Build the seven-day calendar model

**Files:**
- Modify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: Select the current week using server date**

Replace the current `currentWeek` computed with:

```js
const homeServerDate = computed(() => String(
  weeklyLearning.value.serverDate || data.value.serverTime || ''
).slice(0, 10))

const currentWeek = computed(() => {
  const weeks = planSummary.value.weeks || []
  const serverDate = homeServerDate.value
  return weeks.find(week => {
    const start = String(week.startDate || '').slice(0, 10)
    const end = String(week.endDate || '').slice(0, 10)
    return start && end && serverDate >= start && serverDate <= end
  }) || weeks.find(week => (week.days || []).some(day => day.progressStatus === 'TODAY')) || weeks[0] || null
})
```

- [ ] **Step 2: Add the calendar row builder**

Add:

```js
const trainingCalendarDays = computed(() => buildTrainingCalendarDays(
  currentWeek.value,
  homeServerDate.value
))

function buildTrainingCalendarDays(week, serverDate) {
  if (!week) return []
  const days = week.days || []
  const start = parseLocalDate(week.startDate) || parseLocalDate(days[0]?.trainingDate)
  if (!start) return []
  const byDate = new Map(days.map(day => [String(day.trainingDate || '').slice(0, 10), day]))
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    const key = dateKey(date)
    const day = byDate.get(key) || null
    const isToday = key === serverDate
    const isPast = key < serverDate
    const state = day
      ? String(day.progressStatus || 'UPCOMING').toLowerCase()
      : isToday ? 'empty-today' : isPast ? 'past-empty' : 'future-empty'
    return {
      dateKey: key,
      dateLabel: String(date.getDate()),
      weekday: isToday ? '今天' : new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(date).replace('周', ''),
      day,
      isToday,
      state,
      title: day?.title || (isToday ? '暂无训练' : isPast ? '无训练安排' : '等待发布'),
      statusLabel: day
        ? ({ submitted: '已完成', today: '进行中', expired: '待补交', upcoming: '已安排' }[state] || '已安排')
        : isToday ? '今天' : isPast ? '无安排' : '待安排',
    }
  })
}
```

Delete `todayStatus`, `todayStatusTone`, `todayRhythmTask`, and `formatDayOfMonth` because the calendar no longer repeats the current task.

### Task 3: Render and style the training calendar

**Files:**
- Modify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: Replace the rhythm markup**

Change the heading to “训练日历”. Keep the “完整计划” button and week summary, but display `{{ currentWeek.days?.length || 0 }} 项训练`.

Replace `.rhythm-days` and `.rhythm-today-task` with:

```vue
<div class="training-calendar" data-testid="home-training-calendar">
  <component
    :is="item.day ? RouterLink : 'div'"
    v-for="item in trainingCalendarDays"
    :key="item.dateKey"
    class="training-calendar-day"
    :class="[`is-${item.state}`, { 'is-current-date': item.isToday }]"
    :to="item.day ? `/training/days/${item.day.dayId}` : undefined"
  >
    <span class="training-calendar-day__date">
      <small>{{ item.weekday }}</small>
      <strong>{{ item.dateLabel }}</strong>
    </span>
    <span class="training-calendar-day__content">
      <strong>{{ item.title }}</strong>
      <small>{{ item.day ? `训练第 ${item.day.dayNo} 天` : item.dateKey.slice(5).replace('-', '/') }}</small>
    </span>
    <span class="training-calendar-day__status">{{ item.statusLabel }}</span>
    <ArrowRight v-if="item.day" />
  </component>
</div>
```

Import `RouterLink` from `vue-router`. Keep empty rows as `div` elements, so they cannot receive link behavior.

- [ ] **Step 2: Replace the old rhythm CSS**

Delete `.rhythm-days*` and `.rhythm-today-task*` rules. Add a seven-row calendar with 4px gaps and rows that fit the existing tall right card:

```css
.training-calendar {
  margin-top: 12px;
  display: grid;
  gap: 4px;
}

.training-calendar-day {
  min-height: 46px;
  border-radius: 10px;
  padding: 5px 8px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto 14px;
  align-items: center;
  gap: 8px;
  color: var(--ds-ink-2);
  background: #f5f5f7;
  text-decoration: none;
}
```

Use a two-column form for non-link rows with `grid-template-columns: 34px minmax(0, 1fr) auto`, and hide no information. Today uses `var(--ds-orange-50)` plus an orange date block; submitted uses success tokens; future empty rows use quieter neutral text. Link rows receive hover and focus-visible states; inert rows do not.

- [ ] **Step 3: Run the focused test and verify green**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js --reporter=line
```

Expected: one test passes and confirms exactly seven rows, one training link, two past empty dates, four future empty dates, and no duplicate today task.

### Task 4: Regression and visual verification

**Files:**
- Verify: `frontend/user/src/modules/home/StudentHome.vue`
- Verify: `frontend/user/tests/student-prototype-contract.spec.js`

- [ ] **Step 1: Run homepage regression tests**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/home-training-trend.spec.js \
  tests/student-prototype-contract.spec.js \
  --grep "学习时长|训练日历|桌面首页严格保持原型的三列六卡结构|首页在中等和窄屏下按规范降列且核心操作保持可见|首页无业务数据时六个模块仍然存在" \
  --reporter=line
```

Expected: selected homepage tests pass.

- [ ] **Step 2: Build the frontend**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite reports `built`; existing large-chunk warnings remain non-blocking.

- [ ] **Step 3: Inspect the signed-in homepage**

Reload `http://localhost:5174/` and confirm:

- “今日任务” details no longer appear inside the right card;
- all seven dates from 7/22 through 7/28 render for the current real account;
- 7/22 is the only link and shows “进行中”;
- 7/23 through 7/28 show “待安排” without arrows or hover affordance;
- the calendar fits the tall card without clipping;
- console errors remain empty.

- [ ] **Step 4: Check whitespace**

Run:

```bash
rg -n "[ \t]+$" frontend/user/src/modules/home/StudentHome.vue frontend/user/tests/home-training-trend.spec.js
```

Expected: no output and exit code 1, meaning no trailing whitespace matched.

- [ ] **Step 5: Record completion**

The workspace has no `.git` metadata. Report the changed files, Playwright results, Vite build result, signed-in browser verification, and the existing chunk-size warning without claiming a commit.
