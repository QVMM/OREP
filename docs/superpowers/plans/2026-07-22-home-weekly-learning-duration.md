# Home Weekly Learning Duration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the semantically invalid training-status bars on the student home page with a seven-day bar chart whose height represents real daily learning duration.

**Architecture:** Extract the existing course, exam, roadshow, and collaboration duration query and aggregations into `StudentLearningAnalyticsService`. Both the profile dashboard and home dashboard consume that service, so their learning-duration definitions cannot drift. The home API returns a compact `weeklyLearning` payload; `StudentHome.vue` renders a dependency-free, accessible CSS bar chart with a labeled linear minute scale.

**Tech Stack:** Java 21, Spring Boot, JdbcTemplate, JUnit 5, Vue 3 Composition API, scoped CSS, Playwright, Vite.

---

## File map

- Create `backend/src/main/java/com/orep/backend/service/StudentLearningAnalyticsService.java`: own the shared learning-session query and learning-duration aggregations.
- Create `backend/src/test/java/com/orep/backend/service/StudentLearningAnalyticsServiceTest.java`: deterministic tests for Monday-to-Sunday aggregation and invalid durations.
- Modify `backend/src/main/java/com/orep/backend/service/StudentProfileService.java`: delegate summary, heatmap, and distribution calculations to the shared service.
- Modify `backend/src/main/java/com/orep/backend/service/StudentHomeService.java`: add `weeklyLearning` to the existing home payload.
- Modify `frontend/user/tests/home-training-trend.spec.js`: replace status-chart fixtures and assertions with real duration-chart contracts.
- Modify `frontend/user/src/modules/home/StudentHome.vue`: render weekly learning duration, minute scale, today state, zero state, and future state.

### Task 1: Build the shared weekly-duration aggregator

**Files:**
- Create: `backend/src/test/java/com/orep/backend/service/StudentLearningAnalyticsServiceTest.java`
- Create: `backend/src/main/java/com/orep/backend/service/StudentLearningAnalyticsService.java`

- [ ] **Step 1: Write the failing weekly aggregation test**

```java
package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class StudentLearningAnalyticsServiceTest {

    @Test
    void weeklyLearningAlwaysReturnsMondayToSundayAndSumsValidSessions() {
        LocalDate today = LocalDate.of(2026, 7, 22);
        List<Map<String, Object>> sessions = List.of(
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 20, 9, 0), "durationSeconds", 1800),
                Map.of("activityType", "EXAM", "startedAt", LocalDateTime.of(2026, 7, 20, 14, 0), "durationSeconds", 900),
                Map.of("activityType", "ROADSHOW", "startedAt", LocalDateTime.of(2026, 7, 21, 19, 0), "durationSeconds", 3600),
                Map.of("activityType", "COLLABORATION", "startedAt", LocalDateTime.of(2026, 7, 22, 10, 0), "durationSeconds", 0),
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 22, 11, 0), "durationSeconds", -20),
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 19, 11, 0), "durationSeconds", 9999)
        );

        Map<String, Object> result = StudentLearningAnalyticsService.weeklyFromSessions(sessions, today);
        List<Map<String, Object>> daily = (List<Map<String, Object>>) result.get("daily");

        assertEquals("2026-07-20", result.get("weekStart"));
        assertEquals("2026-07-26", result.get("weekEnd"));
        assertEquals("2026-07-22", result.get("serverDate"));
        assertEquals(6300L, result.get("totalSeconds"));
        assertEquals(2L, result.get("activeDays"));
        assertEquals(7, daily.size());
        assertEquals(2700L, daily.get(0).get("durationSeconds"));
        assertEquals(3600L, daily.get(1).get("durationSeconds"));
        assertEquals(0L, daily.get(2).get("durationSeconds"));
        assertEquals("2026-07-26", daily.get(6).get("date"));
    }
}
```

- [ ] **Step 2: Run the test and confirm the expected red state**

Run:

```bash
cd backend
mvn -Dtest=StudentLearningAnalyticsServiceTest test
```

Expected: compilation fails because `StudentLearningAnalyticsService` does not exist.

- [ ] **Step 3: Implement the shared service**

Create a Spring `@Service` with these public operations:

```java
public List<Map<String, Object>> learningSessions(Long userId)
public Map<String, Object> summary(List<Map<String, Object>> sessions)
public List<Map<String, Object>> heatmap(List<Map<String, Object>> sessions)
public List<Map<String, Object>> distribution(List<Map<String, Object>> sessions)
public Map<String, Object> weekly(Long userId)
static Map<String, Object> weeklyFromSessions(List<Map<String, Object>> sessions, LocalDate today)
```

Move the existing union query and the `summary`, `heatmap`, and `distribution` implementations from `StudentProfileService` unchanged, except use `LocalDate.now(ZoneId.of("Asia/Shanghai"))` wherever the current date is needed.

Implement the weekly method with a fixed seven-day result:

```java
public Map<String, Object> weekly(Long userId) {
    return weeklyFromSessions(learningSessions(userId), LocalDate.now(CHINA_ZONE));
}

static Map<String, Object> weeklyFromSessions(List<Map<String, Object>> sessions, LocalDate today) {
    LocalDate weekStart = today.minusDays(today.getDayOfWeek().getValue() - 1L);
    LocalDate weekEnd = weekStart.plusDays(6);
    Map<LocalDate, Long> secondsByDate = new LinkedHashMap<>();
    for (int index = 0; index < 7; index++) {
        secondsByDate.put(weekStart.plusDays(index), 0L);
    }
    for (Map<String, Object> session : sessions) {
        LocalDate date = dateValue(session.get("startedAt"));
        long seconds = Math.max(0L, longValue(session.get("durationSeconds")));
        if (date == null || date.isBefore(weekStart) || date.isAfter(today) || seconds == 0) continue;
        secondsByDate.computeIfPresent(date, (key, value) -> value + seconds);
    }
    List<Map<String, Object>> daily = secondsByDate.entrySet().stream()
            .map(entry -> Map.<String, Object>of(
                    "date", entry.getKey().toString(),
                    "durationSeconds", entry.getValue()
            ))
            .toList();
    long totalSeconds = secondsByDate.values().stream().mapToLong(Long::longValue).sum();
    long activeDays = secondsByDate.entrySet().stream()
            .filter(entry -> !entry.getKey().isAfter(today) && entry.getValue() > 0)
            .count();
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("weekStart", weekStart.toString());
    result.put("weekEnd", weekEnd.toString());
    result.put("serverDate", today.toString());
    result.put("totalSeconds", totalSeconds);
    result.put("activeDays", activeDays);
    result.put("daily", daily);
    return result;
}
```

- [ ] **Step 4: Run the aggregator test**

Run:

```bash
cd backend
mvn -Dtest=StudentLearningAnalyticsServiceTest test
```

Expected: `BUILD SUCCESS`, one test passes.

- [ ] **Step 5: Record the checkpoint**

The workspace has no `.git` repository, so a Git commit is unavailable. Record the passing test output in the task handoff instead of fabricating a commit.

### Task 2: Reuse analytics in profile and home APIs

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/StudentProfileService.java`
- Modify: `backend/src/main/java/com/orep/backend/service/StudentHomeService.java`

- [ ] **Step 1: Delegate profile learning calculations**

Change the profile service constructor and dashboard method:

```java
private final JdbcTemplate jdbc;
private final StudentLearningAnalyticsService learningAnalytics;

public StudentProfileService(JdbcTemplate jdbc, StudentLearningAnalyticsService learningAnalytics) {
    this.jdbc = jdbc;
    this.learningAnalytics = learningAnalytics;
}

public Map<String, Object> dashboard(Long tenantId, Long userId) {
    Map<String, Object> profile = profile(tenantId, userId);
    Long teamId = nullableLong(profile.get("teamId"));
    List<Map<String, Object>> sessions = learningAnalytics.learningSessions(userId);

    Map<String, Object> result = new LinkedHashMap<>();
    result.put("profile", profile);
    result.put("summary", learningAnalytics.summary(sessions));
    result.put("heatmap", learningAnalytics.heatmap(sessions));
    result.put("distribution", learningAnalytics.distribution(sessions));
    result.put("certificates", certificates(tenantId, userId, teamId));
    result.put("rectifications", rectifications(tenantId, userId, teamId));
    result.put("serverDate", LocalDate.now(ZoneId.of("Asia/Shanghai")).toString());
    return result;
}
```

Delete the moved private methods from `StudentProfileService` so only one implementation of the learning-duration definition remains.

- [ ] **Step 2: Add weekly learning to the home payload**

Inject `StudentLearningAnalyticsService` into `StudentHomeService`, then add:

```java
data.put("weeklyLearning", learningAnalytics.weekly(userId));
```

Place it next to `planSummary`, before unrelated roadshow and score data.

- [ ] **Step 3: Compile and run affected backend tests**

Run:

```bash
cd backend
mvn -Dtest=StudentLearningAnalyticsServiceTest,StudentHomeControllerTest,StudentProfileControllerTest test
```

Expected: `BUILD SUCCESS`; aggregator and both controller contracts pass.

- [ ] **Step 4: Record the checkpoint**

Because the workspace has no Git repository, retain the exact Maven test result in the final verification summary.

### Task 3: Define the frontend duration-chart contract

**Files:**
- Modify: `frontend/user/tests/home-training-trend.spec.js`

- [ ] **Step 1: Replace the mocked status trend with weekly learning data**

Add this payload beside the existing home fixture:

```js
weeklyLearning: {
  weekStart: '2026-07-20',
  weekEnd: '2026-07-26',
  serverDate: '2026-07-22',
  totalSeconds: 8100,
  activeDays: 3,
  daily: [1800, 3600, 2700, 0, 0, 0, 0].map((durationSeconds, index) => ({
    date: `2026-07-${String(index + 20).padStart(2, '0')}`,
    durationSeconds
  }))
}
```

Replace status assertions with:

```js
await expect(trendCard.getByRole('heading', { name: '本周学习时长' })).toBeVisible()
await expect(trendCard.getByText('2 小时 15 分')).toBeVisible()
await expect(trendCard.getByText('45 分/天')).toBeVisible()
await expect(chart.locator('.learning-duration-point')).toHaveCount(7)
await expect(chart.locator('.learning-duration-point.is-today')).toHaveCount(1)
await expect(chart.locator('.learning-duration-point.is-future')).toHaveCount(4)
await expect(chart.getByText('30 分', { exact: true })).toBeVisible()
await expect(chart.getByText('1 小时', { exact: true })).toBeVisible()
await expect(chart.getByText('45 分', { exact: true })).toBeVisible()
await expect(chart.getByText('未到')).toHaveCount(4)
```

Check the linear height ratio using CSS custom properties:

```js
const barRatios = await chart.locator('.learning-duration-point:not(.is-future)')
  .evaluateAll(points => points.map(point => Number(getComputedStyle(point).getPropertyValue('--bar-ratio'))))
expect(barRatios.slice(0, 3)).toEqual([0.5, 1, 0.75])
```

Keep the existing duplicate-route assertions unchanged.

- [ ] **Step 2: Run the test and confirm the expected red state**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js --reporter=line
```

Expected: fails because the card still says “本周训练趋势” and has no `.learning-duration-point` elements.

### Task 4: Render an understandable weekly duration chart

**Files:**
- Modify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: Replace status-derived computed data**

Add computed state based only on `data.weeklyLearning`:

```js
const weeklyLearning = computed(() => data.value.weeklyLearning || {})
const elapsedWeekDays = computed(() => {
  const start = parseLocalDate(weeklyLearning.value.weekStart)
  const today = parseLocalDate(weeklyLearning.value.serverDate)
  if (!start || !today) return 1
  return Math.max(1, Math.min(7, Math.round((today - start) / 86400000) + 1))
})
const weeklyAverageSeconds = computed(() => Number(weeklyLearning.value.totalSeconds || 0) / elapsedWeekDays.value)
const weeklyLearningScaleMinutes = computed(() => {
  const maxMinutes = Math.max(0, ...(weeklyLearning.value.daily || []).map(item => Math.ceil(Number(item.durationSeconds || 0) / 60)))
  const step = maxMinutes <= 30 ? 15 : maxMinutes <= 60 ? 30 : maxMinutes <= 120 ? 30 : 60
  return Math.max(30, Math.ceil(maxMinutes / step) * step)
})
const weeklyLearningPoints = computed(() => buildWeeklyLearningPoints(
  weeklyLearning.value,
  weeklyLearningScaleMinutes.value
))
```

`buildWeeklyLearningPoints` must parse local `YYYY-MM-DD` values, mark dates after `serverDate` as future, and set `barRatio` to `Math.min(1, durationMinutes / scaleMinutes)`. It must not read training plan status.

- [ ] **Step 2: Replace the trend-card markup**

Use this semantic structure:

```vue
<h2>本周学习时长</h2>
<div class="learning-duration__summary">
  <div><span>本周累计</span><strong>{{ formatLearningDuration(weeklyLearning.totalSeconds) }}</strong></div>
  <div><span>日均时长</span><strong>{{ formatLearningAverage(weeklyAverageSeconds) }}</strong></div>
</div>
<div
  class="learning-duration-chart"
  data-testid="weekly-learning-duration"
  role="img"
  :aria-label="weeklyLearningAria"
>
  <div class="learning-duration-axis" aria-hidden="true">
    <span>{{ formatAxisMinutes(weeklyLearningScaleMinutes) }}</span>
    <span>{{ formatAxisMinutes(weeklyLearningScaleMinutes / 2) }}</span>
    <span>0</span>
  </div>
  <div class="learning-duration-grid">
    <div class="learning-duration-gridline is-top"></div>
    <div class="learning-duration-gridline is-middle"></div>
    <div class="learning-duration-gridline is-bottom"></div>
    <div
      v-for="point in weeklyLearningPoints"
      :key="point.dateKey"
      class="learning-duration-point"
      :class="{ 'is-today': point.isToday, 'is-future': point.isFuture }"
      :style="{ '--bar-ratio': point.barRatio }"
    >
      <span class="learning-duration-point__value">{{ point.valueLabel }}</span>
      <div class="learning-duration-point__plot" aria-hidden="true"><i></i></div>
      <strong>{{ point.weekday }}</strong>
      <small>{{ point.dateLabel }}</small>
    </div>
  </div>
</div>
```

If `totalSeconds` is zero, keep the chart and add one compact sentence below it: “完成课程、练习、路演或协作后会自动记录”。

- [ ] **Step 3: Replace the categorical bar CSS**

Use a two-column chart with a 34px axis and seven equal plot columns. Grid lines occupy the chart plot only. Bar height is calculated linearly:

```css
.learning-duration-point__plot i {
  height: calc(var(--bar-ratio) * 100%);
}
```

Past bars use a restrained neutral fill; `.is-today` uses `var(--ds-orange-700)`. Future bars show a dashed baseline and no filled column. Keep visible value labels, weekday labels, and dates at 10–12px without overlapping. Remove all `.weekly-trend*` styles and categorical status colors.

- [ ] **Step 4: Run the focused frontend test**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js --reporter=line
```

Expected: one test passes, including the `[0.5, 1, 0.75]` linear ratio assertion.

- [ ] **Step 5: Record the checkpoint**

Because the workspace has no Git repository, retain the Playwright result in the final verification summary.

### Task 5: Regression and visual verification

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
  --grep "学习时长|桌面首页严格保持原型的三列六卡结构|首页在中等和窄屏下按规范降列且核心操作保持可见|首页无业务数据时六个模块仍然存在" \
  --reporter=line
```

Expected: four selected tests pass.

- [ ] **Step 2: Build the user frontend**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite reports `built`; existing large-chunk warnings are non-blocking.

- [ ] **Step 3: Inspect the rendered desktop homepage**

Capture the 1440×1000 homepage with the mocked duration payload and confirm:

- chart title and summaries fit within the 308px card;
- every non-zero bar has a visible time value;
- 30, 45, and 60 minute bars are visibly linear;
- today is identifiable by both the orange bar and the “今天” label;
- future dates say “未到” and do not look like zero-study past days;
- no nested card treatment or horizontal clipping appears.

- [ ] **Step 4: Run whitespace verification**

Run:

```bash
rg -n "[ \t]+$" \
  backend/src/main/java/com/orep/backend/service/StudentLearningAnalyticsService.java \
  backend/src/main/java/com/orep/backend/service/StudentProfileService.java \
  backend/src/main/java/com/orep/backend/service/StudentHomeService.java \
  frontend/user/src/modules/home/StudentHome.vue \
  frontend/user/tests/home-training-trend.spec.js
```

Expected: no output.

- [ ] **Step 5: Report completion**

Summarize the shared data definition, the chart semantics, changed files, Maven results, Playwright results, Vite build result, and any pre-existing warnings. Do not claim a Git commit because this workspace has no repository metadata.
