# 首页训练周标题去重 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复首页训练日历的重复周标题，同时保留有效的自定义周主题。

**Architecture:** 在 `StudentHome.vue` 增加纯展示格式化函数，以 `weekNo` 生成基础标题，并对接口 `title` 做空格规范化后判断是否重复。Playwright 使用现有首页接口夹具复现历史默认标题，锁定去重行为。

**Tech Stack:** Vue 3 Composition API、Playwright、Vite。

---

## File map

- Modify `frontend/user/tests/home-training-trend.spec.js`: 复现默认周标题重复并锁定输出。
- Modify `frontend/user/src/modules/home/StudentHome.vue`: 格式化首页训练周标题。

### Task 1: 用失败测试复现重复标题

**Files:**
- Modify: `frontend/user/tests/home-training-trend.spec.js`

- [ ] **Step 1: 将训练周夹具标题改成后端默认值**

```js
title: '第 1 周',
```

- [ ] **Step 2: 增加唯一标题断言**

```js
const rhythmCard = page.getByTestId('home-rhythm-card')
await expect(rhythmCard.getByText('第 1 周', { exact: true })).toHaveCount(1)
await expect(rhythmCard.getByText('第 1 周 · 第 1 周', { exact: true })).toHaveCount(0)
```

- [ ] **Step 3: 运行聚焦测试并确认红灯**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js --reporter=line
```

Expected: FAIL，因为当前模板仍输出“第 1 周 · 第 1 周”。

### Task 2: 实现标题格式化并验证

**Files:**
- Modify: `frontend/user/src/modules/home/StudentHome.vue`

- [ ] **Step 1: 让模板使用格式化结果**

```vue
<strong>{{ formatTrainingWeekTitle(currentWeek) }}</strong>
```

- [ ] **Step 2: 增加格式化函数**

```js
function formatTrainingWeekTitle(week) {
  const baseTitle = `第 ${Number(week?.weekNo || 1)} 周`
  const topic = String(week?.title || '').trim()
  const normalized = value => String(value || '').replace(/\s+/g, '')
  if (!topic || normalized(topic) === normalized(baseTitle)) return baseTitle
  return `${baseTitle} · ${topic}`
}
```

- [ ] **Step 3: 重跑聚焦测试并确认绿灯**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js --reporter=line
```

Expected: 1 test passes。

- [ ] **Step 4: 运行首页回归与生产构建**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/home-training-trend.spec.js tests/student-prototype-contract.spec.js --grep "学习时长|桌面首页严格保持原型的三列六卡结构|首页在中等和窄屏下按规范降列且核心操作保持可见|首页无业务数据时六个模块仍然存在" --reporter=line
npm run build
```

Expected: 4 tests pass，Vite build exits with code 0；现有大分块提示仍为非阻塞警告。

- [ ] **Step 5: 浏览器验证真实数据**

确认首页训练日历标题只显示一次“第 1 周”，有效周主题仍按“第 N 周 · 主题”展示，控制台无错误。

## Workspace note

当前目录没有 `.git` 元数据，因此不包含提交步骤。
