# 路演训练统一命名 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将路演模块的菜单、入口页、路演房间、记录、回放和评分关联入口统一为“路演训练／路演”词根，同时保留正式评分维度原文。

**Architecture:** 保持现有 Vue 路由、接口字段和组件职责不变，只替换学生可见文案与可访问名称。通过 Playwright 锁定主导航、入口页、回放页和评分标签，通过源文件契约测试防止直接关联组件重新出现“在线会议／现场讲解／参会记录”等旧词。

**Tech Stack:** Vue 3、Vue Router、Element Plus、Playwright、Node.js test runner、Vite

---

## 文件结构

- Modify: `frontend/user/src/composables/apple/useOrepNavigation.js` — 六项主导航名称与路由组保持一致。
- Modify: `frontend/user/src/router/index.js` — 为路演训练和路演回放设置浏览器标题。
- Modify: `frontend/user/src/views/OnlineMeeting.vue` — 路演训练入口页全部可见文案。
- Modify: `frontend/user/src/views/Statistics.vue` — 评分报告范围标签。
- Modify: `frontend/user/src/views/MyRecordings.vue` — 路演回放列表页文案。
- Modify: `frontend/user/src/views/MeetingReplay.vue` — 单场路演回放文案。
- Modify: `frontend/user/src/views/MeetingRoom.vue` — 路演房间的状态、交流、录制和离开操作。
- Modify: `frontend/user/src/components/workspace/WorkspaceTopbar.vue` — 搜索与快捷入口名称。
- Modify: `frontend/user/src/components/workspace/WorkspaceModuleNav.vue` — 兼容配置中的路演模块名称。
- Modify: `frontend/user/src/components/layout/AppHeader.vue` — 旧外壳兼容入口名称。
- Modify: `frontend/user/src/components/intro/IntroProductPreview.vue` — 产品预览中的入口名称。
- Modify: `frontend/user/src/components/AudioRecorder.vue` — 路演房间内的用户提示。
- Modify: `frontend/user/src/components/ai-score/AiScoreControl.vue` — 评分来源的可见名称。
- Modify: `frontend/user/src/components/ai-score/AiScoreStartDialog.vue` — 评分来源的可见名称。
- Modify: `frontend/user/src/components/ai-score/ScoreSummaryHeader.vue` — 评分来源的可见名称。
- Modify: `frontend/user/src/components/ai-score/report/AiScoreReportShell.vue` — 报告返回入口。
- Modify: `frontend/user/src/components/ai-score/report/AiScoreSummaryChrome.vue` — 报告返回入口。
- Modify: `frontend/user/tests/workspace-sidebar-navigation.spec.js` — 主导航名称与当前态。
- Modify: `frontend/user/tests/workspace-route-shell-stability.spec.js` — 从首页进入路演训练的外壳稳定性。
- Modify: `frontend/user/tests/online-meeting-report-tabs.spec.js` — 入口页与评分范围词汇。
- Modify: `frontend/user/tests/online-meeting-validation-alignment.spec.js` — 表单、回放和双向跳转。
- Modify: `frontend/user/tests/review-pages-design.spec.js` — 嵌入评分页主标题。
- Create: `frontend/user/tests/roadshow-terminology-contract.test.mjs` — 直接关联组件的统一词根契约。

### Task 1: 用失败测试锁定主导航和路演训练入口

**Files:**
- Modify: `frontend/user/tests/workspace-sidebar-navigation.spec.js`
- Modify: `frontend/user/tests/workspace-route-shell-stability.spec.js`
- Modify: `frontend/user/tests/online-meeting-report-tabs.spec.js`
- Modify: `frontend/user/tests/online-meeting-validation-alignment.spec.js`
- Modify: `frontend/user/tests/review-pages-design.spec.js`

- [ ] **Step 1: 将主导航期望名称统一为“路演训练”**

在桌面和移动端的 `expectedNames` 中使用：

```js
const expectedNames = ['首页', '训练营', '路演训练', '协作', 'AI应用中心', '我的']
```

将路演路由当前态定位器统一为：

```js
const roadshowLink = navigation.getByRole('link', { name: '路演训练', exact: true })
```

- [ ] **Step 2: 更新入口页的可访问文案断言**

在 `online-meeting-report-tabs.spec.js` 中使用：

```js
const mainTabs = page.getByRole('tablist', { name: '路演训练内容' })
await expect(page.getByRole('heading', { name: '路演训练', level: 1 })).toBeVisible()
await expect(page).toHaveTitle('路演训练｜竞赛大脑')
await expect(mainTabs.getByRole('tab', { name: '路演记录', exact: true }))
  .toHaveAttribute('aria-selected', 'true')
await expect(page.getByRole('button', { name: '发起路演', exact: true })).toHaveCount(1)
await expect(page.getByRole('button', { name: '进入路演', exact: true })).toBeVisible()
```

评分范围标签改为：

```js
await page.getByRole('tab', { name: '我队伍的路演 0', exact: true }).click()
```

- [ ] **Step 3: 更新表单与回放跳转断言**

在 `online-meeting-validation-alignment.spec.js` 中使用：

```js
await page.getByRole('button', { name: '进入路演', exact: true }).click()
await expect(page.getByText('请输入路演号', { exact: true })).toBeVisible()

await page.getByRole('button', { name: '路演回放', exact: true }).click()
await expect(page).toHaveURL('/my-recordings')
const returnLink = page.getByRole('link', { name: '返回路演训练', exact: true })
```

- [ ] **Step 4: 运行测试确认 RED**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js \
  tests/online-meeting-report-tabs.spec.js \
  tests/online-meeting-validation-alignment.spec.js \
  tests/review-pages-design.spec.js
```

Expected: FAIL；页面和导航仍显示“现场讲解／在线会议／参会记录／会议回放”。

### Task 2: 实现主导航、入口页和评分范围统一

**Files:**
- Modify: `frontend/user/src/composables/apple/useOrepNavigation.js`
- Modify: `frontend/user/src/router/index.js`
- Modify: `frontend/user/src/views/OnlineMeeting.vue`
- Modify: `frontend/user/src/views/Statistics.vue`
- Modify: `frontend/user/src/components/workspace/WorkspaceTopbar.vue`
- Modify: `frontend/user/src/components/workspace/WorkspaceModuleNav.vue`
- Modify: `frontend/user/src/components/layout/AppHeader.vue`
- Modify: `frontend/user/src/components/intro/IntroProductPreview.vue`

- [ ] **Step 1: 修改主导航名称**

将路演导航项改为：

```js
{ path: '/online-meeting', label: '路演训练', code: 'Roadshow', group: 'roadshow' }
```

兼容导航和搜索入口统一使用“路演训练”“进入路演训练与回放”。

- [ ] **Step 2: 为相关路由设置浏览器标题**

路由元信息使用：

```js
{
  path: '/online-meeting',
  name: 'OnlineMeeting',
  component: () => import('../views/OnlineMeeting.vue'),
  meta: { requiresAuth: true, title: '路演训练' }
}
```

```js
{
  path: '/my-recordings',
  name: 'MyRecordings',
  component: () => import('../views/MyRecordings.vue'),
  meta: { requiresAuth: true, title: '路演回放' }
}
```

在路由创建后增加统一标题更新：

```js
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title}｜竞赛大脑` : '竞赛大脑'
})
```

- [ ] **Step 3: 替换入口页的全部学生可见文案**

页头和加入卡片使用：

```vue
<h1>路演训练</h1>
<p class="sub">发起或加入线上路演，反复练习、回看表现并获得评分反馈</p>
<span class="live-pill" aria-label="路演服务可用">路演服务可用</span>
<button type="button" class="btn soft" @click="goRecordings">路演回放</button>
<BaseButton type="primary" @click="openCreateModal">发起路演</BaseButton>

<h2 id="joinTitle">加入路演</h2>
<span class="hint">使用老师或队友分享的路演信息</span>
```

表单使用：

```vue
<el-form-item prop="meetingCode" class="field" label="路演号">
  <el-input placeholder="6 位路演号" />
</el-form-item>
<el-form-item prop="password" class="field" label="路演密码">
  <el-input placeholder="密码" />
</el-form-item>
<BaseButton type="primary">进入路演</BaseButton>
```

标签和说明使用：

```vue
<section aria-label="路演记录与评分">
  <div class="content-tabs" role="tablist" aria-label="路演训练内容">
    <button role="tab">路演记录</button>
    <button role="tab">评分报告</button>
  </div>
  <h2>路演记录</h2>
  <p>继续进行中的路演，或查看已结束场次</p>
</section>
```

同步把校验、Toast、复制信息和创建弹窗中的“会议号／参会信息／路演室”改成“路演号／路演信息／路演”。

- [ ] **Step 4: 修改评分范围标签**

```js
const reportTabs = computed(() => [
  { key: 'participant', label: '我参与的路演', count: states.participant.reports.length },
  { key: 'team', label: '我队伍的路演', count: states.team.reports.length }
])
```

- [ ] **Step 5: 运行入口与导航测试确认 GREEN**

Run:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js \
  tests/online-meeting-report-tabs.spec.js \
  tests/online-meeting-validation-alignment.spec.js \
  tests/review-pages-design.spec.js
```

Expected: PASS。

### Task 3: 统一路演房间、回放和评分关联入口

**Files:**
- Modify: `frontend/user/src/views/MyRecordings.vue`
- Modify: `frontend/user/src/views/MeetingReplay.vue`
- Modify: `frontend/user/src/views/MeetingRoom.vue`
- Modify: `frontend/user/src/components/AudioRecorder.vue`
- Modify: `frontend/user/src/components/ai-score/AiScoreControl.vue`
- Modify: `frontend/user/src/components/ai-score/AiScoreStartDialog.vue`
- Modify: `frontend/user/src/components/ai-score/ScoreSummaryHeader.vue`
- Modify: `frontend/user/src/components/ai-score/report/AiScoreReportShell.vue`
- Modify: `frontend/user/src/components/ai-score/report/AiScoreSummaryChrome.vue`
- Create: `frontend/user/tests/roadshow-terminology-contract.test.mjs`

- [ ] **Step 1: 写直接关联组件的失败契约测试**

创建：

```js
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const files = [
  'src/views/MyRecordings.vue',
  'src/views/MeetingReplay.vue',
  'src/views/MeetingRoom.vue',
  'src/components/AudioRecorder.vue',
  'src/components/ai-score/AiScoreControl.vue',
  'src/components/ai-score/AiScoreStartDialog.vue',
  'src/components/ai-score/ScoreSummaryHeader.vue',
  'src/components/ai-score/report/AiScoreReportShell.vue',
  'src/components/ai-score/report/AiScoreSummaryChrome.vue',
]

test('路演直接关联界面不再使用旧入口术语', async () => {
  const contents = await Promise.all(files.map(file => readFile(new URL(`../${file}`, import.meta.url), 'utf8')))
  const source = contents.join('\n')

  const legacyPatterns = [
    /在线会议室/,
    />\s*会议聊天\s*</,
    />\s*离开会议\s*</,
    /会议室录制/,
    /返回会议/,
    /返回会议回放/,
    />\s*会议回放\s*</,
  ]

  for (const pattern of legacyPatterns) {
    assert.doesNotMatch(source, pattern)
  }
})
```

- [ ] **Step 2: 运行契约测试确认 RED**

Run:

```bash
cd frontend/user
node --test tests/roadshow-terminology-contract.test.mjs
```

Expected: FAIL；相关组件仍包含旧用户术语。

- [ ] **Step 3: 替换回放与房间的学生可见文案**

回放列表使用：

```vue
<h1>路演回放</h1>
<router-link to="/online-meeting">返回路演训练</router-link>
<input placeholder="搜索路演标题、状态或编号" />
<h2>还没有路演回放</h2>
<router-link to="/online-meeting">发起一场路演</router-link>
```

单场回放使用：

```vue
<button type="button" @click="router.push('/my-recordings')">返回路演回放</button>
<span class="eyebrow">路演回放</span>
<strong>正在加载路演回放</strong>
```

路演房间使用“在线路演”“路演交流”“路演录制”“离开路演”，连接状态使用“正在进入路演／路演已就绪”。

- [ ] **Step 4: 替换评分关联入口**

评分组件使用：

```js
sourceLabel: { type: String, default: '路演录制' }
```

报告返回入口使用：

```vue
<button type="button" class="secondary" @click="goMeeting">← 返回路演</button>
```

正式维度“现场讲解效果”以及后端 `meeting` 字段保持不变。

- [ ] **Step 5: 运行契约和页面测试确认 GREEN**

Run:

```bash
cd frontend/user
node --test tests/roadshow-terminology-contract.test.mjs
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/online-meeting-report-tabs.spec.js \
  tests/online-meeting-validation-alignment.spec.js \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js \
  tests/review-pages-design.spec.js
```

Expected: 全部 PASS。

### Task 4: 完整回归、构建和浏览器验收

**Files:**
- Verify: `frontend/user/src/**`
- Verify: `frontend/user/tests/**`

- [ ] **Step 1: 扫描残留用户术语**

Run:

```bash
rg -n "现场讲解|在线会议|参会记录|返回在线会议|我参加的会议|我队伍的会议" \
  src/views/OnlineMeeting.vue \
  src/views/MyRecordings.vue \
  src/views/MeetingReplay.vue \
  src/views/MeetingRoom.vue \
  src/views/Statistics.vue \
  src/composables/apple/useOrepNavigation.js \
  src/components/workspace \
  src/components/ai-score
```

Expected: 仅允许正式评分维度“现场讲解效果”、代码注释或技术排障文本；学生可见入口无残留。

- [ ] **Step 2: 运行相关完整回归**

Run:

```bash
cd frontend/user
node --test tests/roadshow-terminology-contract.test.mjs
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/online-meeting-report-tabs.spec.js \
  tests/online-meeting-validation-alignment.spec.js \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js \
  tests/review-pages-design.spec.js
```

Expected: 0 failures。

- [ ] **Step 3: 运行生产构建**

Run:

```bash
cd frontend/user
npm run build
```

Expected: exit code 0。

- [ ] **Step 4: 浏览器验收**

在桌面宽度检查：

- 菜单气泡、页面标题和浏览器标题均为“路演训练”。
- 页面只出现“发起路演、加入路演、进入路演、路演记录、路演回放、评分报告”。
- 路演回放可返回“路演训练”。

在 `390 × 844` 检查：

- 菜单和页头操作完整可达。
- 页面无横向滚动。
- 路演记录与评分报告标签不截断。

## 提交说明

当前工作区没有 Git 元数据，执行时不创建提交或分支；所有修改直接保留在本地工作区。
