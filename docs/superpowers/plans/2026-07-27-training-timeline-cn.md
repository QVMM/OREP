# 训练任务纯中文时间线 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将学生端训练任务列表改造成纯中文的“吸顶周标 + 纵向进度轨道”，同时保留现有任务逻辑与信息密度。

**Architecture:** 继续由 `TrainingPlan.vue` 负责页面结构、周进度计算和状态映射，不新增依赖或后端接口。使用原生吸顶布局、伪元素进度轨道和渐进式视口动画实现时间线效果。

**Tech Stack:** Vue 3、原生 CSS、Playwright、Vite

---

### Task 1: 锁定纯中文和时间线布局契约

**Files:**
- Modify: `frontend/user/tests/training-task-list.spec.js`

- [ ] **Step 1: 添加失败测试**

```js
test('训练任务使用纯中文吸顶时间线并在窄屏降为单列', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  const firstWeek = page.locator('.tasks-week').first()
  await expect(firstWeek.getByText('第 1 周', { exact: true })).toBeVisible()
  await expect(firstWeek.getByText('第 1 天', { exact: true })).toBeVisible()
  await expect(firstWeek.getByText(/^W\\d+/)).toHaveCount(0)
  await expect(firstWeek.getByText(/^DAY\\s+\\d+/)).toHaveCount(0)
  await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('position', 'sticky')
  await expect(firstWeek).toHaveCSS('grid-template-columns', /.+ .+/)

  await page.setViewportSize({ width: 720, height: 900 })
  await expect(firstWeek).toHaveCSS('grid-template-columns', /.+/)
  await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('position', 'static')
  await expect.poll(() => page.evaluate(() => document.body.scrollWidth <= document.body.clientWidth)).toBe(true)
})
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:5174 npx playwright test tests/training-task-list.spec.js -g '训练任务使用纯中文吸顶时间线并在窄屏降为单列'
```

Expected: FAIL，因为现有页面仍显示 `W01`、`DAY 01`，周头也不是吸顶布局。

### Task 2: 实现周进度数据和纯中文文案

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingPlan.vue`

- [ ] **Step 1: 将周、日标签改为中文**

```vue
<span class="tasks-week__number">第 {{ week.weekNo || 1 }} 周</span>
<span>第 {{ day.dayNo || 0 }} 天</span>
```

- [ ] **Step 2: 增加周标题与进度计算**

```js
function weekTitle(week) {
  const weekNo = Number(week?.weekNo) || 1
  const customTitle = String(week?.title || '').trim()
  if (!customTitle || customTitle.replace(/\s+/g, '') === `第${weekNo}周`) return '本周训练'
  return customTitle
}

function weekStats(week) {
  const entries = (week.days || []).flatMap(day => (day.tasks || []).map(task => ({ task, day })))
  const submitted = entries.filter(({ task, day }) => ['complete', 'review'].includes(taskState(task, day).tone)).length
  return {
    submitted,
    total: entries.length,
    rate: entries.length ? Math.round((submitted / entries.length) * 100) : 0
  }
}
```

- [ ] **Step 3: 在周头展示真实进度**

```vue
<span>{{ weekStats(week).submitted }} / {{ weekStats(week).total }} 项已提交</span>
<div class="tasks-week__progress" aria-hidden="true">
  <i :style="{ width: `${weekStats(week).rate}%` }"></i>
</div>
```

### Task 3: 实现吸顶周标与纵向进度轨道

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingPlan.vue`

- [ ] **Step 1: 将每周容器改为双栏**

```css
.tasks-week {
  display: grid;
  grid-template-columns: 164px minmax(0, 1fr);
  align-items: start;
  gap: 24px;
}

.tasks-week__head {
  position: sticky;
  top: 24px;
  display: block;
}
```

- [ ] **Step 2: 使用伪元素绘制橙灰时间线**

```css
.tasks-week__days {
  --week-progress: 0%;
  position: relative;
  padding-left: 28px;
}

.tasks-week__days::before,
.tasks-week__days::after {
  content: "";
  position: absolute;
  top: 8px;
  bottom: 18px;
  left: 7px;
  width: 3px;
  border-radius: 999px;
}

.tasks-week__days::before {
  background: #d9dce1;
}

.tasks-week__days::after {
  bottom: auto;
  height: var(--week-progress);
  background: var(--tasks-orange);
}
```

- [ ] **Step 3: 添加克制的视口进入动画和减少动态效果支持**

```css
@supports (animation-timeline: view()) {
  .tasks-day {
    animation: tasks-day-enter both;
    animation-timeline: view();
    animation-range: entry 5% entry 32%;
  }
}

@keyframes tasks-day-enter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .tasks-day {
    animation: none;
  }
}
```

- [ ] **Step 4: 移动端降为单栏**

```css
@media (max-width: 760px) {
  .tasks-week {
    grid-template-columns: 1fr;
  }

  .tasks-week__head {
    position: static;
  }
}
```

### Task 4: 验证和部署

**Files:**
- Update generated files: `deploy/frontend/user/dist`

- [ ] **Step 1: 运行目标测试**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:5174 npx playwright test tests/training-task-list.spec.js
```

Expected: PASS。

- [ ] **Step 2: 运行学生端专项测试并构建**

```bash
npm run build
```

Expected: Vite 构建退出码为 `0`。

- [ ] **Step 3: 备份并仅部署学生端**

将当前云端 `frontend/user/dist` 备份到 `/opt/orep/backups`，同步新构建并只重建 `frontend-user`。

- [ ] **Step 4: 线上核验**

确认首页、`/training/today` 和新时间线资源返回 `200`，其他容器创建时间保持不变。
