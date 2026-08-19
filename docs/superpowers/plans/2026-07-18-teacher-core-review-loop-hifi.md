# OREP 教师端核心审核闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan.

**Goal:** 在现有静态高保真原型中完成“教师审核 → 退回/通过 → 学生整改/完成”的可重复跨端闭环，并把教师工作台、审核工作台和营看板提升到当前学生首页的视觉完成度。

**Architecture:** 以一个无依赖 UMD 状态模块作为唯一业务事实源；教师端和学生端分别使用页面适配器消费派生数据。状态模块负责合法迁移、校验、版本化持久化和跨标签页同步，页面脚本只负责渲染与交互，不维护第二份审核状态。

**Tech Stack:** 静态 HTML、CSS、原生 JavaScript、`localStorage`、Node `node:test`、现有 Playwright 1.56、Python 静态服务器。

---

## 0. 执行前约束

设计权威文件：

- `docs/superpowers/specs/2026-07-18-teacher-core-review-loop-hifi-design.md`
- `OREP-高保真原型/user/index.html`
- `OREP-高保真原型/user/css/pages/home.css`
- `OREP-高保真原型/user/css/app.css`
- `OREP-高保真原型/user/THEME.md`
- `OREP-高保真原型/user/LAYOUT.md`

实施前必须加载：

- `superpowers:test-driven-development`
- `frontend-design`
- `impeccable`

最终验收前必须加载：

- `superpowers:verification-before-completion`

版本控制约束：

- `/Users/liuyixing/项目/OREP` 当前不是 Git 仓库。
- 不要在执行过程中擅自初始化 Git。
- 本计划不包含无法执行的提交步骤；每个任务以“失败测试 → 最小实现 → 通过测试 → 检查改动范围”作为检查点。
- 若执行前用户已经把目录纳入 Git，则在每个任务通过后再做小粒度提交。

边界约束：

- 不修改超管端。
- 不继续向 `user/css/app.css` 追加页面专属样式。
- 不把业务状态写进 `teacher-core.js`、`student-demo-sync.js` 或 HTML。
- 不复用遗留键 `orep-demo-state` 或 `orep-role`。
- 重置只处理本轮演示键，不调用 `localStorage.clear()`。
- 教师首页移除重复二级栏；教师审核页和营看板保留二级栏。
- 学生首页只增加稳定钩子并映射状态，不重排现有 Bento 结构，不覆盖“上场反馈”卡。

## 1. 最终文件边界

```text
OREP-高保真原型/
├── shared/
│   └── demo-state.js                         # 新增：唯一业务状态源
├── teacher/
│   ├── css/
│   │   └── teacher-core.css                  # 新增：三个教师标杆页
│   ├── js/
│   │   └── teacher-core.js                   # 新增：教师页面适配器
│   ├── index.html                            # 重做内容层，保留一级轨
│   ├── review.html                           # 重做为三栏审核工作台
│   └── camp.html                             # 升级为 8×21 矩阵
├── user/
│   ├── css/pages/camp.css                    # 只补学生反馈区局部样式
│   ├── js/
│   │   └── student-demo-sync.js              # 新增：学生状态适配器
│   ├── index.html                            # 只加动态钩子和脚本
│   └── training-day.html                     # 升级反馈与重提区
├── tests/
│   ├── demo-state.test.cjs                   # 新增：纯状态单测
│   └── hifi-contracts.test.cjs               # 新增：HTML/资源契约
└── portals.html                              # 增加低干扰重置入口

frontend/user/tests/
└── hifi-teacher-review-loop.spec.js          # 新增：浏览器验收
```

三个教师页的资源顺序必须固定：

```html
<link rel="stylesheet" href="../user/css/app.css" />
<link rel="stylesheet" href="../css/portals.css" />
<!-- camp.html 在这里先加载 ../user/css/pages/camp.css -->
<link rel="stylesheet" href="css/teacher-core.css" />

<script src="../shared/demo-state.js"></script>
<script src="../user/js/app.js"></script>
<script src="js/teacher-core.js"></script>
```

两个学生页的脚本顺序必须固定：

```html
<script src="../shared/demo-state.js"></script>
<script src="js/app.js"></script>
<script src="js/student-demo-sync.js"></script>
```

## 2. 共享状态契约

### 2.1 常量

```js
var STORAGE_KEY = "orep-hifi-teacher-review-loop:v1";
var SCHEMA_VERSION = 1;
var EVENT_NAME = "orep:demo-state-changed";

var STATUS = Object.freeze({
  PENDING_REVIEW: "PENDING_REVIEW",
  CHANGES_REQUESTED: "CHANGES_REQUESTED",
  RESUBMITTED: "RESUBMITTED",
  PASSED: "PASSED"
});

var ACTION = Object.freeze({
  APPROVE: "APPROVE",
  REQUEST_CHANGES: "REQUEST_CHANGES",
  RESUBMIT: "RESUBMIT"
});
```

### 2.2 默认案例

状态只保存三项真实审核案例，审核队列从案例派生：

| caseId | 学生 | 任务 | 初始状态 | 标记 |
|---|---|---|---|---|
| `zhang-day4` | 张志强 | Day 4 主功能组件封装与排障 | `PENDING_REVIEW` | 主演示案例 |
| `li-day4` | 李晓萌 | Day 4 主功能组件封装与排障 | `PENDING_REVIEW` | 首次审核 |
| `zhao-day1` | 赵丽颖 | Day 1 题意解读与功能框架 | `PENDING_REVIEW` | 补交、逾期 |

顶层结构固定为：

```js
{
  version: 1,
  revision: 0,
  activeCampId: "camp-gold-21",
  updatedAt: "2026-07-18T14:22:00+08:00",
  reviewCases: []
}
```

每个 `reviewCase` 固定包含：

```js
{
  caseId: "zhang-day4",
  kind: "daily",
  task: {
    day: 4,
    title: "主功能组件封装与排障",
    summary: "能讲清模块怎么拆、卡点怎么排。",
    dueAt: "2026-07-18T22:00:00+08:00",
    criteria: [
      "组件结构说明，一页内",
      "排障清单不少于 3 条",
      "可选：30 秒口述热身"
    ]
  },
  student: { id: "student-zhang", name: "张志强" },
  team: { id: "team-application", name: "应用攻坚队" },
  status: "PENDING_REVIEW",
  round: 1,
  isPinned: true,
  isOverdue: false,
  firstSubmittedAt: "2026-07-18T14:22:00+08:00",
  submissions: [],
  aiAssessment: {},
  decisions: [],
  timeline: []
}
```

`decisions[]` 固定结构：

```js
{
  id: "decision-zhang-day4-r1",
  type: "APPROVE",
  round: 1,
  decidedAt: "2026-07-18T16:30:00+08:00",
  teacher: { id: "teacher-liu", name: "刘老师" },
  scores: { structure: 88, troubleshooting: 86, evidence: 82, clarity: 84 },
  comment: "结构清楚，异常路径已能支撑本轮验收。",
  nextMove: "保留异常路径图，下一次按定位顺序口述。",
  remediation: null
}
```

退回裁决的 `type` 为 `REQUEST_CHANGES`，`remediation` 使用第 2.4 节的五字段结构。`timeline[]` 每项固定包含 `id`、`type`、`at`、`actor`、`title`、`detail`、`round`；允许的 `type` 为 `SUBMITTED`、`APPROVED`、`CHANGES_REQUESTED`、`RESUBMITTED`。

张志强首轮提交固定事实：

```js
{
  id: "submission-zhang-day4-r1",
  round: 1,
  submittedAt: "2026-07-18T14:22:00+08:00",
  note: "已完成主功能拆分，并记录联调时遇到的三个排障点。",
  changeSummary: "",
  artifacts: [
    { id: "artifact-structure", type: "document", name: "组件结构说明.pdf", meta: "1 页 · 680 KB" },
    { id: "artifact-checklist", type: "checklist", name: "排障清单.md", meta: "4 条 · 已展开" },
    { id: "artifact-audio", type: "audio", name: "30 秒口述热身.m4a", meta: "00:32 · 含转写" }
  ]
}
```

张志强 AI 初评固定为：

```js
{
  scores: {
    structure: 88,
    troubleshooting: 84,
    evidence: 76,
    clarity: 82
  },
  evidenceGaps: [
    "异常分支没有对应到具体组件",
    "回滚条件缺少可验证证据"
  ],
  suggestedComment: "模块拆分清楚，排障路径基本完整；请补充异常分支和回滚触发条件。",
  suggestedNextMove: "用一张异常路径图说明：触发条件 → 定位步骤 → 回滚结果。"
}
```

### 2.3 状态模块导出面

Node `require()` 和浏览器 `window.OREPDemoState` 必须暴露同一组核心 API：

```js
{
  STORAGE_KEY,
  SCHEMA_VERSION,
  EVENT_NAME,
  STATUS,
  ACTION,
  DemoStateError,
  createInitialState,
  createMemoryStorage,
  validateState,
  reduce,
  createStore,
  selectCase,
  selectReviewQueue,
  selectTeacherSummary,
  selectStudentDay4,
  selectCampMatrix
}
```

核心签名固定为：

```js
new DemoStateError(code, message, fields)
validateState(candidate)
reduce(state, action, now)
createStore({ storage, eventTarget, now, persistent })
```

- `DemoStateError` 继承 `Error`，公开 `name="DemoStateError"`、`code` 和字段名数组 `fields`。
- `validateState(candidate)` 成功时返回规范化后的防御性副本，失败时抛出 `DemoStateError("INVALID_STATE", ...)`。
- `reduce(state, action, now)` 是纯函数，不修改输入；`now` 是返回 ISO 字符串的函数。
- `createStore()` 捕获持久化中的 `INVALID_STATE` 并恢复默认数据，但不会吞掉业务动作的 `VALIDATION_ERROR` 或 `INVALID_TRANSITION`。

浏览器环境再把默认 store 的以下方法合并到 `window.OREPDemoState`：

```js
{
  getState,
  dispatch,
  subscribe,
  reset,
  consumeRecoveryNotice,
  destroy
}
```

`createStore({ storage, eventTarget, now, persistent })` 的 `persistent` 表示当前存储是否能跨刷新保留；浏览器安全读取到 `localStorage` 时为 `true`，降级到内存存储时为 `false`。`dispatch(action)` 返回：

```js
{
  state: {},
  persistent: true
}
```

`state` 必须是防御性深拷贝。`persistent: false` 表示状态已在当前页面内存中生效，但浏览器存储不可用，刷新后可能回退。页面适配器必须显示“当前为临时演示状态，刷新后可能丢失”，不能误报为已永久保存。

UMD 封装必须按以下次序完成：

1. factory 内定义并返回上方列出的完整核心 API。
2. CommonJS 环境把核心 API 赋给 `module.exports`。
3. 无 DOM 的全局环境把同一个核心 API 赋给 `globalThis.OREPDemoState`。
4. 浏览器环境安全读取 `localStorage`；读取受限时改用 `createMemoryStorage()`，并把 `persistent` 设为 `false`。
5. 浏览器环境用 `createStore({ storage, eventTarget: window, persistent })` 建立默认 store。
6. 最后用 `Object.assign({}, core, store)` 赋给 `window.OREPDemoState`。

测试必须证明 CommonJS 导出、无 DOM 全局导出和浏览器默认 store 三条路径都成立；最终文件中不得保留空 factory 或实现占位。

### 2.4 动作负载

通过：

```js
store.dispatch({
  type: ACTION.APPROVE,
  caseId: "zhang-day4",
  payload: {
    scores: {
      structure: 88,
      troubleshooting: 86,
      evidence: 82,
      clarity: 84
    },
    comment: "结构清楚，异常路径已能支撑本轮验收。",
    nextMove: "保留这张异常路径图，下一次口述时按定位顺序讲。"
  }
});
```

退回：

```js
store.dispatch({
  type: ACTION.REQUEST_CHANGES,
  caseId: "zhang-day4",
  payload: {
    scores: {
      structure: 86,
      troubleshooting: 78,
      evidence: 70,
      clarity: 80
    },
    comment: "结构已完成，但异常路径还不能复验。",
    nextMove: "先补齐异常分支与回滚证据，再做一次 30 秒口述。",
    remediation: {
      issueType: "证据不足",
      evidenceLocation: "排障清单第 2、3 条",
      expectedResult: "每条异常路径都包含触发条件、定位步骤和回滚结果",
      dueAt: "2026-07-19T18:00:00+08:00",
      reason: "当前清单只写了处理动作，无法判断何时触发以及是否回滚成功"
    }
  }
});
```

重新提交：

```js
store.dispatch({
  type: ACTION.RESUBMIT,
  caseId: "zhang-day4",
  payload: {
    note: "已按老师意见补充异常分支和回滚条件。",
    changeSummary: "新增异常路径图；补充清单第 2、3 条的触发条件和验证结果。",
    artifacts: [
      { id: "artifact-structure-r2", type: "document", name: "组件结构说明_v2.pdf", meta: "2 页 · 920 KB" },
      { id: "artifact-checklist-r2", type: "checklist", name: "排障清单_v2.md", meta: "5 条 · 已展开" }
    ]
  }
});
```

### 2.5 迁移与校验规则

- `APPROVE` 只接受 `PENDING_REVIEW` 或 `RESUBMITTED`。
- `REQUEST_CHANGES` 只接受 `PENDING_REVIEW` 或 `RESUBMITTED`。
- `RESUBMIT` 只接受 `CHANGES_REQUESTED`。
- 通过时四个分数、教师评语和“下一刀”都必填。
- 退回时四个分数、教师评语、“下一刀”和五个整改字段都必填。
- 重提时说明和修改摘要必填。
- 分数必须是 `0–100` 的有限整数。
- 任何业务校验或非法迁移失败都抛出 `DemoStateError`，使用 `VALIDATION_ERROR` 或 `INVALID_TRANSITION`，且不得修改内存和持久化状态。
- 每次动作追加时间线，不覆盖旧提交与旧裁决。
- 每次成功业务动作将顶层 `revision` 单调加一；`updatedAt` 只用于展示，不能作为同步去重依据。
- `round` 等于当前提交版本数；退回不加轮次，重提才加一。
- JSON 损坏、结构缺字段或 `version !== 1` 时恢复默认数据，并让 `consumeRecoveryNotice()` 只返回一次 `true`。
- reducer 与业务校验成功后生成下一状态并尝试持久化；存储写入失败时进入“仅内存降级模式”，返回 `persistent: false`，继续通知当前页面订阅者，但不派发会误导其他标签页的持久化成功事件。
- 每个 store 生成唯一 `storeId`；同页自定义事件携带 `storeId`、状态和 `persistent`，发起 store 忽略自己的事件，避免一次动作重复渲染。
- `storage` 事件只接收匹配 `STORAGE_KEY` 的合法新状态；`newValue === null` 视为重置。新状态 `revision` 大于当前值时应用；revision 相同但序列化内容不同视为并发的最后写入并应用；内容完全相同时忽略。不能按时间字符串去重。

### 2.6 派生规则

`selectReviewQueue(state, filter)`：

- 队列只含 `PENDING_REVIEW` 和 `RESUBMITTED`。
- `first` 只含 `PENDING_REVIEW`。
- `resubmitted` 只含 `RESUBMITTED`。
- `overdue` 只含逾期案例。

`selectTeacherSummary(state)`：

- `pendingCount` 等于审核队列长度。
- `firstReviewCount`、`resubmittedCount`、`changesRequestedCount` 均从案例计算。
- `nextReviewCase` 排序为：主演示置顶 `isPinned` → 复审优先 → 逾期优先 → 等待最久优先。只有 `zhang-day4` 初始 `isPinned: true`，因此首页初始最高优先项稳定为张志强；案例离开审核队列后再选下一项。
- 初始 `pendingCount` 必须为 3。
- 张志强通过或被退回后必须为 2。
- 张志强重提后必须回到 3，且 `resubmittedCount` 为 1。

`selectStudentDay4(state)` 返回以下完整页面映射：

| 状态 | 今日状态 | 欢迎区主 CTA | “今天练什么” CTA | 本周今日卡 | “现在可做”首项 | 今日集训 CTA |
|---|---|---|---|---|---|---|
| `PENDING_REVIEW` | 已提交，等待老师 | 查看今日提交 → `training-day.html` | 查看提交 → `training-day.html` | 待批改 · 今日 14:22 已提交 | 今日成果已提交 · 待批改 | 禁用按钮“已提交，等待批改” |
| `CHANGES_REQUESTED` | 老师已退回 | 查看反馈并修改 → `training-day.html` | 按反馈修改 → `training-day.html` | 待修改 · 明日 18:00 截止 | 按老师反馈修改 Day 4 · 优先 | 按钮“重新提交” |
| `RESUBMITTED` | 已重新提交，复审中 | 查看复审进度 → `training-day.html` | 查看复审 → `training-day.html` | 复审中 · 第 2 轮已提交 | 第 2 轮已提交 · 复审中 | 禁用按钮“复审中” |
| `PASSED` | 已完成 | 去练一场路演 → `roadshow.html` | 查看老师反馈 → `training-day.html` | 已完成 · 本日已通过 | 查看 Day 4 老师反馈 · 已完成 | 按钮“查看老师反馈” |

首页四个链接始终保留有意义的导航，不使用伪禁用。今日集训的提交控件是 `<button>`；`PENDING_REVIEW` 和 `RESUBMITTED` 必须设置真实 `disabled`，不能只设置 `aria-disabled`。

通过后的 `overallScore` 固定为四个维度的算术平均值四舍五入；学生反馈和营看板都显示这个派生总分，不在状态中重复保存总分。

`selectCampMatrix(state)`：

- 返回 8 名学生 × 21 天。
- D1–D3 使用固定历史数据，D5–D21 使用未开始/未解锁数据。
- 张志强 D4 必须从 `zhang-day4` 派生。
- 李晓萌 D4 从 `li-day4` 派生。
- 赵丽颖 D1 从 `zhao-day1` 派生，赵丽颖 D4 不得再额外显示“待评”。
- 初始矩阵的待评单元格总数与教师队列保持 3。

固定 roster 与 D1–D4 基线：

| 学生 | 分组 | D1 | D2 | D3 | D4 |
|---|---|---|---|---|---|
| 张志强 | 应用攻坚队 | 88 | 83 | 90 | 从 `zhang-day4` 派生 |
| 李晓萌 | 应用攻坚队 | 95 | 90 | 92 | 从 `li-day4` 派生 |
| 赵丽颖 | 应用攻坚队 | 从 `zhao-day1` 派生 | 85 | 88 | 未交 |
| 王俊凯 | 硬件联调组 | 80 | 未交 | 78 | 未交 |
| 周雨桐 | 硬件联调组 | 86 | 84 | 81 | 进行中 |
| 孙浩然 | 硬件联调组 | 79 | 82 | 80 | 已通过 87 |
| 陈国华 | 文档路演组 | 82 | 80 | 未交 | 已通过 84 |
| 林诗雅 | 文档路演组 | 91 | 89 | 94 | 已通过 91 |

因此“应用攻坚队”筛选固定返回 3 人，D4 已提交人数固定为 5/8；D5–D21 全部为未开始/未解锁。

## 3. 稳定 DOM 契约

页面脚本只使用以下 `data-*` 钩子，不依赖中文文案或 `nth-child`。

| 页面 | 必须存在的钩子 |
|---|---|
| 教师首页 | `data-teacher-pending-count`、`data-teacher-priority-card`、`data-teacher-today-list`、`data-teacher-waiting-count` |
| 审核页 | `data-review-filter`、`data-review-queue`、`data-review-evidence`、`data-review-decision`、`data-review-live`、`data-review-pane-tabs`、`data-review-decision-toggle`、`data-teacher-module-toggle` |
| 审核表单 | `data-score-dimension`、`data-score-value`、`data-apply-ai`、`data-prepare-approve`、`data-prepare-return`、`data-confirm-decision`、`data-external-update-banner` |
| 营看板 | `data-camp-team-filter`、`data-camp-status-filter`、`data-camp-student-search`、`data-camp-matrix`、`data-camp-detail`、`data-camp-detail-close` |
| 学生首页 | `data-student-primary-action`、`data-student-day4-status`、`data-student-today-action`、`data-student-week-card`、`data-student-now-action` |
| 今日集训 | `data-student-day4-card`、`data-student-day4-status`、`data-student-day4-action`、`data-student-day4-feedback`、`data-student-resubmit`、`data-student-resubmit-note`、`data-student-resubmit-summary` |
| 门户 | `data-demo-reset`、`data-demo-reset-confirm` |

教师页面增加：

```html
<body data-portal="teacher" data-teacher-page="dashboard">
<body data-portal="teacher" data-teacher-page="review">
<body data-portal="teacher" data-teacher-page="camp">
```

学生页面增加：

```html
<body data-portal="student" data-nav="home" data-student-page="home">
<body data-portal="student" data-nav="training" data-student-page="training-day">
```

## 4. 任务拆分

### Task 1：用测试锁定唯一状态机

**Files:**

- Create: `OREP-高保真原型/tests/demo-state.test.cjs`
- Create: `OREP-高保真原型/shared/demo-state.js`

**Step 1: 先写失败测试**

测试文件使用 `node:test`、`node:assert/strict` 和 `node:vm`，覆盖以下 12 项：

1. `require()` 与 `globalThis.OREPDemoState` 暴露相同核心 API。
2. 用 `node:vm` 构造带 `document`、`localStorage` 和 `EventTarget` 的浏览器脚本环境，确认自动创建含 `getState/dispatch/reset` 的默认 store。
3. 默认有三个待评案例，张志强为第 1 轮。
4. `getState()` 和 `dispatch().state` 都返回防御性深拷贝。
5. 直接通过后为 `PASSED`、队列从 3 变 2、历史保留。
6. 空白教师评语或不完整整改字段抛出 `DemoStateError`，且 `error.code === "VALIDATION_ERROR"`，状态不变。
7. 正常退回进入 `CHANGES_REQUESTED`。
8. 重提创建第 2 个 submission，状态为 `RESUBMITTED`。
9. 复审可再次退回，之后可第 3 次提交。
10. 非法迁移抛出 `DemoStateError`，且 `error.code === "INVALID_TRANSITION"`，持久化内容不变。
11. 损坏 JSON 和错误 schema 安全恢复，恢复提示只消费一次。
12. `subscribe()`、取消订阅、`reset()`、revision 同步、模拟 `storage` 事件和存储写失败的内存降级行为正确。

关键断言使用固定时钟：

```js
const fixedNow = () => "2026-07-18T16:30:00+08:00";
const storage = api.createMemoryStorage();
const store = api.createStore({ storage, now: fixedNow });

assert.equal(api.selectTeacherSummary(store.getState()).pendingCount, 3);

store.dispatch({
  type: api.ACTION.APPROVE,
  caseId: "zhang-day4",
  payload: {
    scores: { structure: 88, troubleshooting: 86, evidence: 82, clarity: 84 },
    comment: "结构清楚，异常路径已能支撑本轮验收。",
    nextMove: "保留异常路径图，下一次按定位顺序口述。"
  }
});

assert.equal(api.selectCase(store.getState(), "zhang-day4").status, api.STATUS.PASSED);
assert.equal(api.selectTeacherSummary(store.getState()).pendingCount, 2);
```

**Step 2: 运行并确认失败**

```bash
cd "/Users/liuyixing/项目/OREP/OREP-高保真原型"
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/demo-state.test.cjs"
```

预期：因 `shared/demo-state.js` 尚不存在而失败，错误包含 `MODULE_NOT_FOUND`。

**Step 3: 实现最小状态模块**

实现第 2 节的完整契约：

- UMD 导出。
- 不可变 `reduce()`。
- 原子 `dispatch()`。
- 内存存储降级。
- `localStorage` 读写容错。
- 同页自定义事件与跨页 `storage` 事件。
- 防御性深拷贝。
- 恢复提示。
- 所有选择器。

reducer 与业务校验全部成功后才生成下一状态；随后尝试持久化。持久化失败时仍更新内存并通知订阅者，`dispatch()` 返回 `persistent: false`，页面必须提示刷新后可能丢失。

订阅回调签名固定为：

```js
listener(nextState, {
  source: "local" | "storage" | "reset" | "recovered",
  action: "APPROVE" | "REQUEST_CHANGES" | "RESUBMIT" | null,
  persistent: true
});
```

**Step 4: 运行并确认通过**

```bash
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/demo-state.test.cjs"
```

预期：`pass 12`、`fail 0`。

**Step 5: 检查范围**

- 确认只新增两个文件。
- 搜索并确认没有复用 `orep-demo-state` 或 `orep-role`。
- 确认状态模块不查询或修改 DOM。

### Task 2：建立 HTML 资源与钩子契约

**Files:**

- Create: `OREP-高保真原型/tests/hifi-contracts.test.cjs`
- Create: `OREP-高保真原型/teacher/css/teacher-core.css`
- Create: `OREP-高保真原型/teacher/js/teacher-core.js`
- Modify: `OREP-高保真原型/teacher/index.html`
- Modify: `OREP-高保真原型/teacher/review.html`
- Modify: `OREP-高保真原型/teacher/camp.html`

**Step 1: 先写失败契约测试**

测试读取三个教师 HTML 并断言：

- body 有正确 `data-teacher-page`。
- 搜索框都有 `id="searchInput"`。
- 每个资源恰好引用一次，且不带 `async` 或 `defer`。
- `index.html`、`review.html` 的 CSS 严格按 `app.css → portals.css → teacher-core.css`。
- `camp.html` 继续依赖现有 `camp.css`，CSS 严格按 `app.css → portals.css → camp.css → teacher-core.css`。
- 三页脚本严格按 `demo-state.js → app.js → teacher-core.js`。
- `index.html` 不含 `has-module-list` 和 `<aside class="module-list">`。
- `review.html` 与 `camp.html` 仍含 `has-module-list` 和模块栏。
- `review.html` 不再含空锚点 `#materials`。
- 第 3 节中对应教师页面的钩子均存在。
- 所有新 `href`、`src` 的本地文件存在。

资源顺序测试用字符串索引与出现次数，不引入 HTML 解析依赖：

```js
const demoIndex = html.indexOf("../shared/demo-state.js");
const appIndex = html.indexOf("../user/js/app.js");
const pageIndex = html.indexOf("js/teacher-core.js");

assert.equal(html.split("../shared/demo-state.js").length - 1, 1);
assert.equal(html.split("../user/js/app.js").length - 1, 1);
assert.equal(html.split("js/teacher-core.js").length - 1, 1);
assert.ok(demoIndex < appIndex);
assert.ok(appIndex < pageIndex);
assert.doesNotMatch(html, /<script[^>]+(?:async|defer)[^>]*>/);
```

**Step 2: 运行并确认失败**

```bash
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

预期：缺少教师专属文件、页面标识和钩子而失败。

**Step 3: 建立无副作用骨架**

`teacher-core.js` 先只做守卫：

```js
(function () {
  "use strict";

  if (document.body.dataset.portal !== "teacher") return;
  if (!window.OREPDemoState || !window.OREPDemoState.getState) {
    document.body.insertAdjacentHTML(
      "afterbegin",
      '<div class="tcore-runtime-alert" role="alert">演示状态暂不可用，请刷新页面。</div>'
    );
    return;
  }

  var page = document.body.dataset.teacherPage;
  if (!page) return;
})();
```

创建 `teacher-core.css` 并遵守：

- 业务内容规则以 `body[data-portal="teacher"]` 和 `.tcore-*` 共同限定。
- 不裸写 `.workspace-main`、`.workspace-app`、`.arch-rail`、`.module-list`、`.p-card` 或 `.tcamp-cell`。
- 唯一例外是审核页响应式壳层：允许使用 `body[data-portal="teacher"][data-teacher-page="review"]` 限定后覆盖 `.workspace-app` 与 `.module-list`，用于 1440px 以下的可控折叠；不得影响其他教师页或学生页。
- 复用现有 `--ds-*` token。
- 不重新定义 `:root`。

三个教师页：

- 添加 body 页面标识和搜索框 ID。
- 加载新 CSS/JS 和共享状态。
- 教师首页删除 `has-module-list` 与第 24–32 行旧模块栏。
- 教师审核页删除不在本轮范围内的“材料审核”空入口，把第二项改为 `review.html?filter=overdue#queue`，标签为“补交与逾期”。
- 先放置第 3 节的空容器与钩子，下一任务填内容。

**Step 4: 运行并确认通过**

```bash
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

预期：所有资源、顺序、壳层和钩子契约通过。

**Step 5: 回归共享壳**

```bash
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/demo-state.test.cjs" "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

预期：全部通过，学生首页文件尚未改动。

### Task 3：把教师首页做成状态驱动的今日决策台

**Files:**

- Modify: `OREP-高保真原型/teacher/index.html`
- Modify: `OREP-高保真原型/teacher/css/teacher-core.css`
- Modify: `OREP-高保真原型/teacher/js/teacher-core.js`
- Create: `frontend/user/tests/hifi-teacher-review-loop.spec.js`

**Step 1: 先写教师首页浏览器测试**

Playwright 测试先调用：

```js
await page.goto("/teacher/index.html");
await page.evaluate(() => window.OREPDemoState.reset());
await page.reload();
```

断言：

- 页面标题为“教师工作台 · 老师端”。
- 无二级栏。
- `[data-teacher-pending-count]` 为 `3`。
- 最高优先卡包含“张志强”“Day 4”“首次审核”。
- 页面只有一个实心橙色主行动。
- “处理待评”链接指向 `review.html?item=zhang-day4#queue`。
- 无 `pageerror` 和页面自身 console error。

**Step 2: 运行并确认失败**

先确认 8765 静态服务正在运行；若没有，在独立终端运行：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory "/Users/liuyixing/项目/OREP/OREP-高保真原型"
```

再运行：

```bash
cd "/Users/liuyixing/项目/OREP/frontend/user"
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "教师首页初始态"
```

预期：动态内容或布局断言失败。

**Step 3: 实现 Bento 内容层**

整段替换旧 `.p-page` 内容，保留一级轨、顶栏和 `.workspace-main`。

页面结构固定为：

```text
.tcore-dashboard
├── .tcore-welcome
│   ├── 刘老师 + 营上下文
│   └── 处理待评（主）/ 打开营看板（次）
├── .tcore-dashboard-grid
│   ├── .tcore-priority-card
│   ├── .tcore-progress-card
│   ├── .tcore-risk-card
│   ├── .tcore-roadshow-card
│   └── .tcore-today-card
└── [data-review-live]
```

视觉规则：

- 对齐学生首页 16px 圆角、细边框、暖灰阴影和 40px 页边距。
- 教师角色只用深墨小胶囊，不使用深色侧栏。
- 页面仅“处理待评”是实心橙按钮。
- KPI 使用轻量状态条，不做四个等权彩色数字卡。
- 1512×744 首屏能看到欢迎区、最高优先卡和“今天先做”。

`teacher-core.js` 增加：

```text
initDashboard()
renderDashboard(state)
renderPriorityCase(summary.nextReviewCase)
renderTodayList(summary)
```

订阅 store 后，张志强离开队列时自动展示下一项；没有待评时展示明确空状态。

**Step 4: 运行并确认通过**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "教师首页初始态"
```

预期：测试通过。

### Task 4：完成三栏审核工作台和直接通过路径

**Files:**

- Modify: `OREP-高保真原型/teacher/review.html`
- Modify: `OREP-高保真原型/teacher/css/teacher-core.css`
- Modify: `OREP-高保真原型/teacher/js/teacher-core.js`
- Modify: `frontend/user/tests/hifi-teacher-review-loop.spec.js`

**Step 1: 先写失败的审核工作台测试**

直接通过场景：

1. 重置。
2. 打开 `/teacher/review.html?item=zhang-day4#queue`。
3. 左栏张志强项有 `aria-current="true"`。
4. 中栏可见三类证据、验收标准、学生备注和第 1 轮时间线。
5. 右栏明确显示“AI 初评 · 仅供参考”。
6. 点击“采用 AI 建议”。
7. 四个评分输入、教师评语和下一刀被填充，但状态仍是待审核。
8. 点击“通过并发布”，当前栏展开确认区。
9. 点击最终确认。
10. 队列从 3 变 2，张志强案例为 `PASSED`，下一案例被选中。

状态断言：

```js
const state = await page.evaluate(() => window.OREPDemoState.getState());
const currentCase = state.reviewCases.find((item) => item.caseId === "zhang-day4");
expect(currentCase.status).toBe("PASSED");
expect(currentCase.decisions).toHaveLength(1);
expect(currentCase.submissions).toHaveLength(1);
```

同时先写两个独立失败测试：

- `退回校验`：空退回表单不改变状态；所有必填字段设置 `aria-invalid` 和有效 `aria-describedby`；补全后才能进入 `CHANGES_REQUESTED`。
- `审核响应控件`：1280px 模块栏按钮、1024px 非模态裁决侧板、390px 三段 tab 的 `aria-expanded`/`aria-selected`、Esc 和焦点归还正确。

**Step 2: 运行并确认失败**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "直接通过|退回校验|审核响应控件"
```

预期：三栏、证据、退回校验或响应控件缺失。

**Step 3: 重做审核页内容**

替换当前第 46–78 行旧 `.p-page` 内容，建立：

```text
.tcore-review
├── .tcore-review-header
│   ├── button[data-teacher-module-toggle]
│   └── button[data-review-decision-toggle]
├── .tcore-review-panes[data-review-pane-tabs]
├── .tcore-review-layout
│   ├── #reviewQueuePanel.tcore-review-queue        260–280px
│   ├── #reviewEvidencePanel.tcore-review-evidence  minmax(0, 1fr)
│   └── #reviewDecisionPanel.tcore-review-decision  320–340px
├── .tcore-sync-banner[hidden]
└── .tcore-live[aria-live="polite"]
```

响应式控件在 Task 4 就进入 DOM，Task 8 只精修布局：

- 模块栏加 `id="teacherModuleList"`；`data-teacher-module-toggle` 使用 `aria-controls="teacherModuleList"` 和 `aria-expanded`。
- 1180–1439px 默认收起模块栏；按钮可把它作为覆盖层打开，Esc 关闭并归还焦点，模块导航仍可键盘访问。
- 900–1179px 的 `data-review-decision-toggle` 打开页面内非模态裁决侧板，使用 `aria-controls="reviewDecisionPanel"` 和 `aria-expanded`；焦点进入侧板标题，Esc 返回按钮。
- 所有关闭的模块栏覆盖层、裁决侧板和非当前移动面板都同时设置 `hidden`，并在浏览器支持时设置 `inert`；打开时同步移除，保证隐藏内容不会进入 Tab 顺序。
- `<900px` 的 `data-review-pane-tabs` 使用 `role="tablist"`；三个按钮使用 `role="tab"`、`aria-selected`、`aria-controls`，三个面板使用 `role="tabpanel"`，一次只显示一个。tab 支持 `ArrowLeft`、`ArrowRight`、`Home`、`End` 循环移动焦点并激活对应面板。
- `>=900px` 隐藏分段控件但保持三块内容在正常阅读顺序中。

左栏：

- 全部、首次审核、复审、逾期筛选。
- 队列项使用按钮，不使用假链接。
- 当前项使用 `aria-current="true"`。
- URL `?item=` 和 `?filter=` 可深链并恢复选中案例与队列筛选。

中栏：

- 目标与验收标准。
- 学生备注。
- 三种证据预览。
- 提交版本、修改摘要和轮次时间线。
- 无附件与无历史的空状态。

右栏：

- AI 建议与证据缺口。
- 四个带可见 label 的 `input type="range"`，步长 1，支持键盘。
- 每个 range 有同步的可见数值、`aria-valuetext`，并由 label 与数值共同说明维度。
- 教师评语和“下一刀”。
- “采用 AI 建议”只填表。
- “通过并发布”和“退回修改”先展开当前栏确认区。
- 不使用打断式 modal。

移除旧业务按钮的 `data-toast`，成功 dispatch 后再调用 `window.toast()`。

`teacher-core.js` 增加：

```text
initReview()
renderReviewQueue(state, filter)
renderReviewEvidence(reviewCase)
renderDecisionForm(reviewCase)
applyAiSuggestion()
prepareDecision(mode)
validateDecisionForm(mode)
confirmDecision(mode)
selectNextReviewCase()
```

表单错误：

- 就地显示。
- 第一个错误字段获得焦点。
- 输入后清除对应错误。
- 失败时不调用 `dispatch()`。
- 错误字段设置 `aria-invalid="true"`，并用 `aria-describedby` 指向字段错误。
- 错误摘要使用 `role="alert"`；修正后移除错误关联，不留下失效 ID。

**Step 4: 运行单测与审核工作台测试**

```bash
cd "/Users/liuyixing/项目/OREP/OREP-高保真原型"
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/demo-state.test.cjs" "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

```bash
cd "/Users/liuyixing/项目/OREP/frontend/user"
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "直接通过|退回校验|审核响应控件"
```

预期：全部通过。

### Task 5：完成 8×21 营看板、筛选和详情面板

**Files:**

- Modify: `OREP-高保真原型/teacher/camp.html`
- Modify: `OREP-高保真原型/teacher/css/teacher-core.css`
- Modify: `OREP-高保真原型/teacher/js/teacher-core.js`
- Modify: `frontend/user/tests/hifi-teacher-review-loop.spec.js`

**Step 1: 先写失败的营看板测试**

断言：

- 初始有 8 个学生行和 21 个 Day 列。
- “应用攻坚队”筛选固定显示 3 人。
- 学生列和表头为 sticky。
- 张志强 D4 显示“待审核”，可访问名称含“张志强 Day 4 待审核”。
- 点击单元格打开详情面板，显示证据 3、轮次 1、最近状态和进入审核链接。
- 初始只有张志强 D4 格内按钮 `tabindex="0"`；方向键移动焦点，Enter 打开详情，Esc 关闭并返回原格。
- 选择“应用攻坚队”后只显示该组学生。
- 选择“待审核”后结果数与审核队列一致。
- 张志强通过后无需刷新，D4 变为“已通过”并显示分数。

**Step 2: 运行并确认失败**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "营看板"
```

预期：旧页只有 5×7 静态矩阵，测试失败。

**Step 3: 实现矩阵**

保留教师壳层和模块栏，替换主区内容：

```text
.tcore-camp
├── .tcore-camp-header
├── .tcore-camp-summary
├── .tcore-camp-toolbar
├── .tcore-camp-body
│   ├── .tcore-matrix-shell
│   │   └── table[data-camp-matrix]
│   └── aside[data-camp-detail]
├── .tcore-status-legend
└── .tcore-live[aria-live="polite"]
```

实现规则：

- 表头和 tbody 由 `selectCampMatrix()` 渲染。
- 单元格必须同时有文本/图标与语义 class，不只靠颜色。
- 使用语义 `<table>`；提供可见或视觉隐藏的 `<caption>`，Day 表头使用 `<th scope="col">`，学生行头使用 `<th scope="row">`，每个状态单元格内部使用 `<button>`。
- 168 个格内按钮采用 roving `tabindex`：当前格为 `0`，其余为 `-1`；方向键在同一矩阵移动，Enter/Space 打开详情，避免所有格子进入 Tab 顺序。
- 初始 roving 目标为张志强 D4；每个按钮的 `aria-label` 包含学生、Day、任务状态和分数。
- 每次筛选后重新校正 roving 目标：若原目标仍可见就保留，否则把第一个可见且可操作的格设为 `tabindex="0"`；空结果时把焦点移回筛选工具栏并播报空状态。
- 矩阵容器自身横向滚动，页面主体不横向溢出。
- 张志强 D4 使用 `data-case-id="zhang-day4"`。
- 详情面板有可见标题、显式关闭按钮和 `tabindex="-1"`；触发格使用 `aria-controls`、`aria-expanded`。打开后焦点进入标题，Esc 或关闭按钮关闭并把焦点还给原单元格。
- 筛选后没有结果时显示空状态而不是空白表。
- “批量 AI 初评”仅保留为清楚标注的演示辅助，不改变最终裁决。

`teacher-core.js` 增加：

```text
initCamp()
renderCampSummary(state)
renderCampMatrix(state, filters)
openCampDetail(cell)
closeCampDetail()
applyCampFilters()
moveCampGridFocus(direction)
```

**Step 4: 运行并确认通过**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "营看板"
```

预期：全部通过。

### Task 6：让学生首页和今日集训读取同一事实

**Files:**

- Create: `OREP-高保真原型/user/js/student-demo-sync.js`
- Modify: `OREP-高保真原型/user/index.html`
- Modify: `OREP-高保真原型/user/training-day.html`
- Modify: `OREP-高保真原型/user/css/pages/camp.css`
- Modify: `OREP-高保真原型/tests/hifi-contracts.test.cjs`
- Modify: `frontend/user/tests/hifi-teacher-review-loop.spec.js`

**Step 1: 先扩展失败契约**

增加断言：

- 两个学生页有正确 `data-student-page`。
- 脚本顺序为 `demo-state.js → app.js → student-demo-sync.js`。
- 第 3 节的学生钩子存在。
- 学生首页“上场反馈”区没有 `data-student-day4-feedback`，防止日任务反馈覆盖路演反馈。

**Step 2: 先写失败的学生同步测试**

场景 A：

1. 重置后学生首页显示“已提交，等待老师”。
2. 今日集训 D4 显示“待批改”，没有重复提交按钮。
3. 教师通过。
4. 学生首页显示“已完成”，主 CTA 指向 `/user/roadshow.html`。
5. 今日集训显示最终评分、评语、下一刀和第 1 轮时间线。
6. 点击“查看老师反馈”不会打开提交 modal，页面滚动到反馈区且反馈容器获得焦点。
7. “上场反馈”仍保持原来的 64 分、反馈正文、“下一刀”、五维分和报告链接。

再写独立的“学生重提表单”测试：用状态 API 把张志强预置为 `CHANGES_REQUESTED`，打开今日集训；断言说明或修改摘要为空时 modal 不关闭、状态不变、首错聚焦；补全两项后状态变为 `RESUBMITTED`、round 为 2、submission 数为 2。

**Step 3: 运行并确认失败**

```bash
cd "/Users/liuyixing/项目/OREP/OREP-高保真原型"
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

```bash
cd "/Users/liuyixing/项目/OREP/frontend/user"
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "学生端同步|学生重提表单"
```

预期：缺少脚本、钩子和动态反馈而失败。

**Step 4: 只给学生首页增加稳定钩子**

在现有节点上加属性，不重排结构：

- 第 82 行欢迎区主 CTA：`data-student-primary-action`。
- 第 136 行今日任务状态：`data-student-day4-status aria-live="polite"`。
- 第 192 行今天练什么 CTA：`data-student-today-action`。
- 第 312 行本周今日卡：添加 `data-student-week-card`。
- 第 349 行“现在可做”首项：`data-student-now-action`。

脚本只修改这些节点的：

- 文案。
- `href`。
- 状态 class。
- 必要的辅助说明。

四种状态逐节点使用第 2.6 节的固定映射，不自行推断文案。首页节点都是有效链接，不用 `aria-disabled` 伪装按钮；只有今日集训的提交 `<button>` 在待评和复审状态设置真实 `disabled`。

不要修改第 251–279 行“上场反馈”。

**Step 5: 升级今日集训反馈区**

- D4 状态和按钮从 `selectStudentDay4()` 渲染。
- 在“我的提交与反馈”顶部渲染 D4，D3–D1 原内容保留。
- 展示当前状态、最新裁决、结构化整改、截止时间、版本与时间线。
- `CHANGES_REQUESTED` 时展示“重新提交”。
- `PENDING_REVIEW` 和 `RESUBMITTED` 时禁用重复提交。
- `PASSED` 时展示评分、教师评语和下一刀。
- 保留 D1–D21 点击预览能力；把第 270–285 行迁入 `initDayPreview()`，仅将 D4 预览文案改为读取 `selectStudentDay4()`，不得让 21 天轨道交互退化。
- 重提表单增加“本轮说明”与“修改摘要”两个稳定字段，分别使用 `data-student-resubmit-note` 和 `data-student-resubmit-summary`。
- 首次提交只显示说明；`CHANGES_REQUESTED` 重提时同时显示说明和修改摘要。
- 两个字段都有就地错误节点、`aria-invalid`、`aria-describedby` 和首错聚焦。
- 在本任务就从确认按钮移除旧 `data-toast` 和 `data-close-modal`；取消按钮继续保留 `data-close-modal`。校验失败时 modal 保持打开，dispatch 成功后才由 `student-demo-sync.js` 调用 `closeModal("submitCampModal")`。
- 今日集训主按钮只有 `CHANGES_REQUESTED` 设置 `data-open-modal="submitCampModal"`；`PENDING_REVIEW`、`RESUBMITTED` 移除该属性并真实 `disabled`；`PASSED` 移除该属性并改为滚动、聚焦 `data-student-day4-feedback`，反馈容器设置 `tabindex="-1"`。

在 `camp.css` 末尾只增加 `.camp-feedback-*`，并统一限定为 `body[data-student-page="training-day"] .camp-feedback-*`；不要增加会命中教师营看板的裸 `.is-*` 规则。

`student-demo-sync.js` 使用 IIFE。先检查 `data-student-page` 与状态 API，再进入对应页面分支；每个查询结果都有 null 守卫，任一非关键钩子缺失不能使整页报错。实现：

```text
initStudentHome()
renderStudentHome(view)
initTrainingDay()
initDayPreview()
renderTrainingDay(view)
renderDay4Feedback(view)
openResubmitForm(view)
submitRevision()
showRecoveryNoticeOnce()
```

**Step 6: 运行并确认通过**

```bash
cd "/Users/liuyixing/项目/OREP/OREP-高保真原型"
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/demo-state.test.cjs" "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

```bash
cd "/Users/liuyixing/项目/OREP/frontend/user"
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "学生端同步|学生重提表单"
```

预期：全部通过。

### Task 7：走通退回、重提、复审和演示重置

**Files:**

- Modify: `OREP-高保真原型/teacher/js/teacher-core.js`
- Modify: `OREP-高保真原型/user/js/student-demo-sync.js`
- Modify: `OREP-高保真原型/portals.html`
- Modify: `OREP-高保真原型/tests/hifi-contracts.test.cjs`
- Modify: `frontend/user/tests/hifi-teacher-review-loop.spec.js`

**Step 1: 先写失败的完整场景 B**

测试必须走 UI，不直接 dispatch：

1. 重置。
2. 教师选择“退回修改”。
3. 空表确认时，五个结构化字段附近出现错误，首个错误字段获得焦点，状态仍为 `PENDING_REVIEW`。
4. 填完后发布，状态为 `CHANGES_REQUESTED`，教师待评数为 2。
5. 学生首页变为“老师已退回”，主 CTA 为“查看反馈并修改”。
6. 今日集训显示原因、位置、期望结果、截止时间。
7. 学生点击“重新提交”，说明或修改摘要为空时不能提交。
8. 填完后状态为 `RESUBMITTED`、round 为 2、submission 数为 2。
9. 教师首页待评回到 3，复审数为 1。
10. 审核页切换“复审”只看到张志强。
11. 教师复审通过，学生最终显示 `PASSED`。

**Step 2: 先写失败的场景 C**

覆盖：

- 教师页和学生页两个标签同时打开；一端变化，另一端无刷新更新。
- 审核表单已编辑时，外部变化显示同步提示，不覆盖输入。
- 人工写入损坏 JSON 后刷新，恢复默认数据并出现一次“演示数据已恢复”提示。
- 门户重置需要二次确认。
- 测试先写入 `orep-demo-state`、`orep-role` 和任意 sentinel；重置后三个案例恢复待评，这三个非本轮键的值完全保留。

**Step 3: 运行并确认失败**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "退回与复审|恢复与同步"
```

预期：退回、重提或重置交互尚不完整而失败。

**Step 4: 完成退回和重提适配**

教师端：

- 复用 Task 4 当前栏确认区。
- dispatch 前映射所有表单字段。
- `source === "storage"` 且表单 dirty 时，不自动重绘表单。
- 展示 `[data-external-update-banner]`，用户确认后才重载当前案例。
- 初始化完成且 `consumeRecoveryNotice()` 返回 `true` 时调用一次 `window.toast("演示数据已恢复")`。
- 每次业务 dispatch 检查返回值；`persistent: false` 时显示“当前为临时演示状态，刷新后可能丢失”。

学生端：

- 重提 modal 复用现有 `#submitCampModal` 外壳。
- 根据状态改标题、说明和确认动作。
- 沿用并验证 Task 6 已建立的按钮属性与关闭时机：确认按钮没有 `data-toast`、`data-close-modal`，取消按钮保留 `data-close-modal`，校验失败不关闭，dispatch 成功后才关闭、清错并播报。
- 初始化完成且 `consumeRecoveryNotice()` 返回 `true` 时调用一次 `window.toast("演示数据已恢复")`。
- 每次业务 dispatch 检查 `persistent`，降级时使用与教师端相同的临时状态提示。

**Step 5: 增加门户重置**

在 `portals.html` 的 `.gate-foot` 附近增加低干扰按钮：

```html
<button type="button" class="gate-reset" data-demo-reset>
  重置演示数据
</button>
```

在 `</body>` 前增加带 `role="dialog"`、`aria-modal="true"`、可访问标题、取消和确认按钮的 `#demoResetModal`。门户不加载 `user/js/app.js`，避免它额外写入遗留 `orep-demo-state`；只加载共享状态，再用局部控制器处理打开、关闭、Esc、焦点归还和 toast：

```html
<script src="shared/demo-state.js"></script>
<script>
  (function () {
    var openButton = document.querySelector("[data-demo-reset]");
    var confirmButton = document.querySelector("[data-demo-reset-confirm]");
    var cancelButton = document.querySelector("[data-demo-reset-cancel]");
    var modal = document.getElementById("demoResetModal");

    if (!openButton || !confirmButton || !cancelButton || !modal || !window.OREPDemoState) return;

    function closeReset() {
      modal.classList.remove("is-open");
      openButton.focus();
    }

    function showResetToast(message) {
      var toast = document.createElement("div");
      toast.className = "toast is-show";
      toast.textContent = message;
      document.body.appendChild(toast);
      window.setTimeout(function () {
        toast.remove();
      }, 2200);
    }

    openButton.addEventListener("click", function () {
      modal.classList.add("is-open");
      cancelButton.focus();
    });

    cancelButton.addEventListener("click", closeReset);
    confirmButton.addEventListener("click", function () {
      window.OREPDemoState.reset();
      closeReset();
      showResetToast("演示数据已恢复到初始状态");
    });

    modal.addEventListener("click", function (event) {
      if (event.target === modal) closeReset();
    });

    document.addEventListener("keydown", function (event) {
      if (!modal.classList.contains("is-open")) return;
      if (event.key === "Escape") {
        closeReset();
        return;
      }
      if (event.key === "Tab" && !event.shiftKey && document.activeElement === confirmButton) {
        event.preventDefault();
        cancelButton.focus();
      } else if (event.key === "Tab" && event.shiftKey && document.activeElement === cancelButton) {
        event.preventDefault();
        confirmButton.focus();
      }
    });
  })();
</script>
```

确认 modal 增加基础焦点圈与按钮样式；最终内联脚本必须先检查元素与 API 是否存在，不能因局部 DOM 缺失抛错。

**Step 6: 运行并确认通过**

```bash
cd "/Users/liuyixing/项目/OREP/OREP-高保真原型"
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/demo-state.test.cjs" "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests/hifi-contracts.test.cjs"
```

```bash
cd "/Users/liuyixing/项目/OREP/frontend/user"
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "退回与复审|恢复与同步"
```

预期：全部通过。

### Task 8：响应式、键盘和视觉精修

**Files:**

- Modify: `OREP-高保真原型/teacher/css/teacher-core.css`
- Modify: `OREP-高保真原型/teacher/js/teacher-core.js`
- Modify: `OREP-高保真原型/user/css/pages/camp.css`
- Modify: `frontend/user/tests/hifi-teacher-review-loop.spec.js`

**Step 1: 先写失败的布局与键盘测试**

视口：

- `1512×744`
- `1280×800`
- `1024×768`
- `390×844`

每个目标页断言：

- `document.documentElement.scrollWidth - window.innerWidth <= 1`。
- 主行动在首屏或可自然滚动到。
- `1512px` 审核页为完整三栏并显示模块栏。
- `1280px` 审核页默认收起模块栏、仍显示三栏；模块栏按钮可打开覆盖层且审核仍可完成。
- `1024px` 审核页显示队列与证据两栏；裁决通过非模态侧板按钮打开。
- `390px` 审核页使用队列、证据、裁决三个页内 tab；营矩阵只在自身容器横滚。
- 教师首页在四个宽度都保持 rail-only，不出现二级栏。

键盘断言：

- Tab 可遍历筛选、队列、评分和发布。
- 评分 range 用方向键调整，显示值同步。
- 矩阵方向键移动 roving 焦点，Enter 打开张志强 D4。
- 营看板表格包含 caption、行列 header scope；筛选隐藏当前格后，roving 焦点落到首个可见可操作格，空结果时回到筛选工具栏。
- Esc 关闭营详情并把焦点还给单元格。
- Esc 关闭审核模块栏覆盖层和裁决侧板，并分别归还焦点。
- 移动审核 tab 的 `ArrowLeft`、`ArrowRight`、`Home`、`End` 行为正确，`aria-selected`、`hidden`/`inert` 面板和焦点状态同步。
- 所有关闭的模块栏覆盖层、裁决侧板和非当前移动面板都不在 Tab 顺序中。
- 退回确认展开后焦点进入标题或首个字段。
- 所有状态有文字或 `aria-label`。
- `prefers-reduced-motion: reduce` 时入场动画关闭。

**Step 2: 运行并确认失败**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "响应式与键盘"
```

预期：至少一个中窄屏布局或焦点断言失败。

**Step 3: 精修 CSS 与焦点管理**

`teacher-core.css` 固定断点：

```text
>=1440       完整审核三栏 + 模块栏
1180–1439    审核页默认收起模块栏，可由按钮打开覆盖层；保留三栏
900–1179     队列 + 证据两栏，裁决侧面板
<900         页内分段，矩阵容器横滚
```

其他规则：

- 正文不小于 13px，极次要角标不小于 11px。
- 操作目标至少 40×40px，主操作尽量 44px。
- 所有 focus-visible 清楚可见。
- 动画 140–220ms，并提供 reduced-motion 覆盖。
- 教师端最多一个实心橙主行动。
- 不用大面积渐变或彩虹 KPI。

**Step 4: 运行并确认通过**

```bash
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js" --grep "响应式与键盘"
```

预期：全部通过。

**Step 5: 生成验收截图**

Playwright 保存：

```text
frontend/user/test-results/hifi-teacher-dashboard-1512.png
frontend/user/test-results/hifi-teacher-review-1512.png
frontend/user/test-results/hifi-teacher-camp-1512.png
frontend/user/test-results/hifi-student-returned-1512.png
frontend/user/test-results/hifi-teacher-review-1280.png
frontend/user/test-results/hifi-teacher-review-mobile.png
```

逐张检查：

- 是否对齐新版学生首页的白底、边框、阴影和密度。
- 是否存在文字裁切、横向溢出或浮层遮挡。
- 是否能一眼看出“当前要判断什么”和“下一步是什么”。

### Task 9：全量验证与收口

**Files:**

- Modify only if verification exposes a defect.

**Step 1: 状态与契约全量测试**

```bash
cd "/Users/liuyixing/项目/OREP/OREP-高保真原型"
node --test "/Users/liuyixing/项目/OREP/OREP-高保真原型/tests"/*.test.cjs
```

预期：

- 状态测试 `pass 12`。
- 契约测试全部通过。
- `fail 0`。

**Step 2: 浏览器全量测试**

```bash
cd "/Users/liuyixing/项目/OREP/frontend/user"
OREP_E2E_BASE_URL=http://127.0.0.1:8765 "/Users/liuyixing/项目/OREP/frontend/user/node_modules/.bin/playwright" test "/Users/liuyixing/项目/OREP/frontend/user/tests/hifi-teacher-review-loop.spec.js" --config="/Users/liuyixing/项目/OREP/frontend/user/playwright.config.js"
```

预期：场景 A、B、C、响应式和键盘测试全部通过。

**Step 3: HTTP 与本地资源检查**

检查以下页面均返回 200：

```text
/portals.html
/teacher/index.html
/teacher/review.html
/teacher/camp.html
/user/index.html
/user/training-day.html
```

检查改动 HTML 的本地 `href`、`src` 均存在；忽略纯页内锚点，但页内锚点目标必须存在。

**Step 4: 控制台检查**

对六个页面分别：

- 清空控制台。
- 刷新。
- 执行主交互。
- 确认无页面脚本 error。
- 忽略并记录与页面无关的浏览器扩展 warning，不把它当作产品错误。

**Step 5: 手工走通三条路径**

场景 A：

```text
重置 → 教师首页 3 项待评 → 张志强直接通过
→ 教师首页 2 项 → 营看板已通过
→ 学生首页已完成 → 主 CTA 去练路演
```

场景 B：

```text
重置 → 教师退回 → 学生查看结构化反馈
→ 学生第 2 轮提交 → 教师复审通过
→ 教师、营看板、学生端一致显示已通过
```

场景 C：

```text
刷新不丢状态 → 双标签页同步 → 编辑保护提示
→ 损坏数据恢复 → 门户二次确认重置
```

**Step 6: 最终范围检查**

```bash
if rg -n "TODO|TBD|FIXME|IMPLEMENT_ME|待实现|演示占位" \
  "/Users/liuyixing/项目/OREP/OREP-高保真原型/shared" \
  "/Users/liuyixing/项目/OREP/OREP-高保真原型/teacher" \
  "/Users/liuyixing/项目/OREP/OREP-高保真原型/user/js/student-demo-sync.js"; then
  echo "发现未完成实现标记"
  exit 1
fi
```

预期：命令退出码为 0。合法的表单 `placeholder` 属性不在检查范围；产品文案中明确标注“AI 仅供参考”或“演示数据”不属于未完成实现，可保留。

确认：

- 未修改超管端。
- 未修改 `user/css/app.css`。
- 未删除旧页面或用户文件。
- 未清除其他 localStorage 键。
- 设计规格状态保持“已确认，可进入实施”。

## 5. 完成门槛

只有以下条件同时成立才可以声称完成：

- 单元测试、契约测试和 Playwright 全部通过。
- 直接通过与退回复审均可重复演示。
- 三个教师标杆页达到新版学生首页的完成度。
- 教师工作台、审核页、营看板和学生端读取同一案例状态。
- AI 建议和教师最终裁决视觉、文案与行为上明确分离。
- 结构化退回字段必填且错误可访问。
- 刷新、多标签页、损坏数据恢复和重置都成立。
- 1512、1280、1024 和 390 宽度无页面级横向溢出。
- 当前浏览器页面与截图验收没有页面自身控制台错误。
