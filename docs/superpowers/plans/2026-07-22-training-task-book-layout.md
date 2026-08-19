# 训练详情任务书与右侧行动栏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将训练详情页重构为清晰的任务书主区和精简右侧行动栏。

**Architecture:** 继续使用 `TrainingDayView.vue` 现有接口数据，在主卡中按任务标题、概要、正式描述、附件和交付要求分节渲染。右侧删除重复内容，只保留周导航与按提交状态变化的行动卡；Playwright 契约测试锁定信息归属和卡片数量。

**Tech Stack:** Vue 3 Composition API、DOMPurify、scoped CSS、Playwright、Vite。

---

## File map

- Modify `frontend/user/tests/training-copy.spec.js`: 增加任务书信息架构与右侧精简契约。
- Modify `frontend/user/src/modules/training/TrainingDayView.vue`: 重排模板、删除进度步骤及重复右栏、清理计算属性和样式。

### Task 1: 用失败测试定义新信息架构

**Files:**
- Modify: `frontend/user/tests/training-copy.spec.js`

- [ ] **Step 1: 扩充今日训练接口夹具**

在现有 `data` 中加入：

```js
dueAt: '2026-07-22T22:00:00',
contentHtml: '<p>通过三次真实访谈确认用户痛点，并形成项目边界结论。</p>',
primaryTask: {
  taskId: 1,
  description: '任务描述纯文本回退',
  requirements: [{ id: 1, title: '需求说明', description: '说明目标用户、核心问题和边界', required: true }]
},
attachments: [{
  id: 1,
  fileName: '需求访谈记录模板.pdf',
  fileSize: 627712,
  fileUrl: '/fixtures/interview-template.pdf',
  mimeType: 'application/pdf'
}],
feedback: { feedbackReady: false },
```

- [ ] **Step 2: 增加任务书与右栏契约断言**

```js
const taskBook = page.locator('.training-focus-card')
const side = page.locator('.training-side')

await expect(taskBook.getByRole('heading', { name: '任务书' })).toBeVisible()
await expect(taskBook.getByText('任务概要', { exact: true })).toBeVisible()
await expect(taskBook.getByText('正式任务描述', { exact: true })).toBeVisible()
await expect(taskBook.getByText('用真实访谈和场景证据明确项目边界。')).toBeVisible()
await expect(taskBook.getByText('通过三次真实访谈确认用户痛点，并形成项目边界结论。')).toBeVisible()
await expect(taskBook.getByText('需求访谈记录模板.pdf')).toBeVisible()
await expect(taskBook.getByText('需求说明', { exact: true })).toBeVisible()
await expect(page.getByTestId('training-progress-steps')).toHaveCount(0)

await expect(side.locator('section.student-card')).toHaveCount(2)
await expect(side.getByRole('heading', { name: '提交成果' })).toBeVisible()
await expect(side.getByRole('link', { name: /去提交成果/ })).toHaveCount(1)
await expect(side.locator('.training-week-current')).toHaveCount(0)
await expect(side.locator('.training-neighbor-links')).toHaveCount(0)
await expect(side.getByText('任务附件', { exact: true })).toHaveCount(0)
await expect(side.getByText('交付要求', { exact: true })).toHaveCount(0)
await expect(side.getByText('查看完整任务说明', { exact: true })).toHaveCount(0)
await expect(side.getByText('先看课程', { exact: true })).toHaveCount(0)
await expect(side.getByRole('heading', { name: '老师反馈' })).toHaveCount(0)
await expect(side.getByRole('heading', { name: '接下来可以做' })).toHaveCount(0)
```

- [ ] **Step 3: 运行聚焦测试并确认红灯**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-copy.spec.js --reporter=line
```

Expected: FAIL，因为页面仍显示“训练任务”、进度步骤和四张右侧卡片。

### Task 2: 重构任务书主区

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingDayView.vue`

- [ ] **Step 1: 替换主卡顶部结构**

将标题改为“任务书”，删除 `TrainingProgressSteps` 和主卡中的 `training-status-banner`，依次渲染任务主题、任务概要和正式任务描述。正式描述使用：

```vue
<div v-if="safeContentHtml" class="training-rich-content" v-html="safeContentHtml"></div>
<p v-else-if="primaryTask.description" class="training-task-book__fallback">{{ primaryTask.description }}</p>
<div v-else class="training-inline-empty">老师暂未填写正式任务描述。</div>
```

- [ ] **Step 2: 将附件和交付要求移动到主卡**

复用现有附件预览按钮和交付要求列表，放在正式任务描述之后。附件无数据时不显示分节；交付要求无数据时显示现有空状态。

- [ ] **Step 3: 清理进度组件依赖**

删除：

```js
import TrainingProgressSteps from './components/TrainingProgressSteps.vue'
```

以及完整的 `stageItems` computed。

### Task 3: 精简右侧周导航与提交行动

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingDayView.vue`

- [ ] **Step 1: 精简周导航**

保留周头部和 `.training-week-days`，删除 `.training-week-current` 与 `.training-neighbor-links` 模板。

- [ ] **Step 2: 将任务工具卡改为提交行动卡**

卡片标题改为“提交成果”，保留状态、时间与 `statusBanner` 文案。按钮按以下顺序条件渲染：未提交为“去提交成果”；需修改为“提交新版本”；有反馈且无需修改为“查看老师反馈”；其余已提交状态为“查看我的提交”。次级按钮只补充当前状态仍需访问的提交或反馈。

- [ ] **Step 3: 删除重复右侧卡片与数据**

删除独立老师反馈卡和接下来行动卡，以及右侧附件、要求、材料和完整说明模板。删除不再使用的 `recentFeedback`、`submittedItems`、`currentFeedbackTitle`、`currentFeedbackDescription`，并从图标导入中移除 `ArrowLeft` 和 `Document`。

### Task 4: 重写相关样式并验证

**Files:**
- Modify: `frontend/user/src/modules/training/TrainingDayView.vue`

- [ ] **Step 1: 增加任务书分节样式**

增加 `.training-task-book__title`、`.training-task-book__section`、`.training-task-book__fallback` 和 `.training-submit-*` 样式；使用分隔线和留白，不使用嵌套卡片。

- [ ] **Step 2: 删除废弃样式**

删除 `.training-week-current*`、`.training-neighbor-links*`、`.training-materials*`、`.training-submission-note*`、`.training-task-details*`、`.training-feedback-*` 和 `.training-next-actions*`。同步清理媒体查询中的废弃选择器。

- [ ] **Step 3: 重跑聚焦测试**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/training-copy.spec.js --reporter=line
```

Expected: 1 test passes。

- [ ] **Step 4: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite build exits with code 0；现有大分块提示仍为非阻塞警告。

- [ ] **Step 5: 浏览器验收真实训练日**

在 `/training/days/22` 验证任务书标签、正式描述、附件和要求均在左侧；右侧仅有两张卡，无重复导航或辅助入口；窄屏无横向溢出；控制台无错误。

## Workspace note

当前目录没有 `.git` 元数据，因此不包含提交步骤。
