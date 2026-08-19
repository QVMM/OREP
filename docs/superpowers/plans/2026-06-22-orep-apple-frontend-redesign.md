# OREP Apple 风格前端重设计开发规划

> **给执行 Agent 的要求：**实现本规划时，必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行。所有步骤均使用 checkbox（`- [ ]`）格式，便于跟踪进度。

**目标：**将 OREP 用户端和管理端前端整体重设计为「Apple 风格的 AI 路演生产力工作台」，在保留现有 Vue 路由、API 协议、登录鉴权、LiveKit、PPT 生成、课程、考试、评分和数据分析逻辑的前提下，统一视觉系统、应用壳、页面结构和核心工作流体验。

**架构思路：**先建立共享设计系统，再迁移应用壳和首页样板，最后按业务域逐步迁移页面。用户端采用「白色产品舞台 + 中央工作区 + Agent 辅助 + 流程进度」的结构；管理端共享品牌 tokens，但保留密集、稳定、可扫描的运营后台布局。

**技术栈：**Vue 3、Vue Router、Pinia、Element Plus、Vite、ECharts、LiveKit client、现有 React/Konva PPT 编辑器桥接。

---

## 1. 输入来源与产品方向

### 1.1 参考来源

- Apple 设计规范参考：`https://getdesign.md/apple/design-md`
- 本地 UI 原型图：`/Users/liuyixing/项目/OREP/新UI参考图`
- 用户端前端：`frontend/user`
- 管理端前端：`frontend/admin`

### 1.2 总体视觉方向

OREP 不应该被改成纯营销官网，也不应该继续保持当前偏深色科技后台的状态。目标方向是：

- 像 Apple 一样让「内容和产品能力」成为主角。
- 用白色、浅灰、淡蓝构成清爽空间。
- 导航、边框、阴影、分隔线保持轻薄。
- 每个页面只突出一个最重要的蓝色主行动。
- Agent 辅助能力前置，成为工作流的一部分。
- 明确呈现路演准备流程：材料、脚本、PPT、练习、路演、复盘。
- 数据页面重点呈现能力画像、趋势、改进建议，而不是堆图表。

### 1.3 设计原则

- 不做通用 SaaS 卡片网格。
- 不嵌套卡片。
- 不把首页做成宣传落地页，首屏必须可操作。
- 不为了视觉效果破坏现有业务逻辑。
- 不一次性重写 PPT 编辑器核心。
- 页面重构优先抽出通用组件和 composable。
- 管理端强调效率，不照搬用户端的大舞台布局。

---

## 2. 当前前端结构梳理

### 2.1 用户端

核心文件：

- `frontend/user/src/main.js`：Vue 应用启动、Element Plus 中文配置、全局 CSS 引入、前端监控。
- `frontend/user/src/App.vue`：当前应用壳、顶部导航、移动端导航、用户下拉菜单。
- `frontend/user/src/theme.css`：当前深色/浅色主题变量和 Element Plus 覆盖。
- `frontend/user/src/mobile.css`：移动端样式。
- `frontend/user/src/orep-feedback.css`：全局反馈样式。
- `frontend/user/src/router/index.js`：路由表和登录鉴权守卫。

核心页面：

- `Dashboard.vue`：首页。
- `CourseLearning.vue`、`CourseLessonPlayer.vue`：课程学习。
- `ExamSystem.vue`、`ExamTaking.vue`、`ExamPractice.vue`、`ExamWrongBook.vue`、`ExamFavorites.vue`：考试练习。
- `OnlineMeeting.vue`、`MeetingRoom.vue`、`MeetingHistoryDetail.vue`、`MyRecordings.vue`：会议与录制。
- `ScriptList.vue`、`ScriptEditor.vue`：脚本工作流。
- `PptGenerator.vue`、`PptEditor.vue`、`PptTemplate.vue`、`PptHistoryDetail.vue`：PPT 工作流。
- `ScoreResult.vue`、`AiScoreResult.vue`、`RoadshowChat.vue`、`Statistics.vue`：评分、AI 复盘、数据分析。
- `ProjectTeam.vue`、`Profile.vue`、`Login.vue`：团队、个人中心、登录。

特殊区域：

- `frontend/user/src/react-ppt-editor/*` 是嵌入 Vue 的 React/Konva PPT 编辑器。第一轮只重设计外壳和容器，不重写画布核心逻辑。

### 2.2 管理端

核心文件：

- `frontend/admin/src/App.vue`：根路由视图。
- `frontend/admin/src/views/Layout.vue`：当前管理端布局。
- `frontend/admin/src/theme.css`：管理端主题变量。
- `frontend/admin/src/style.css`：管理端全局样式。
- `frontend/admin/src/router/index.js`：管理端路由和权限。

主要页面：

- `Dashboard.vue`、`Analytics.vue`、`DataMonitor.vue`
- `Users.vue`、`OrganizationManagement.vue`
- `Meetings.vue`、`Scores.vue`、`Issues.vue`
- `Resources.vue`、`CourseManagement.vue`、`ExamManagement.vue`、`PptManagement.vue`
- `AiJuryPersonas.vue`、`HomeBannerManagement.vue`

---

## 3. 目标信息架构

### 3.1 用户端主导航

把现有路由按用户任务重新分组：

1. 首页：`/`
2. 学习：`/course-learning`
3. 练习：`/exam-system`
4. 准备：`/script-editor`、`/resources`、`/ppt-generator`、`/ppt-editor`
5. 路演：`/online-meeting`、`/my-recordings`
6. 提升：`/statistics`、`/ai-score/:meetingId`、`/score-result/:meetingId`
7. 团队：`/project-team`

顶部导航只展示核心入口。PPT 模板、PPT 历史、录制详情、评分详情等页面通过上下文入口进入，不在主导航中拥挤展示。

### 3.2 用户端页面类型

- **产品舞台页**：大面积中央内容区，展示当前项目、下一步行动、进度和 Agent 建议。用于首页。
- **工作台页**：左侧资源栏、中间编辑/生成区、右侧 Agent 面板。用于脚本和 PPT。
- **学习路径页**：课程进度、今日学习任务、下一课推荐。用于课程。
- **练习页**：突出当前练习目标、错题、收藏、考试入口。用于考试。
- **沉浸会议页**：保留视频/会议操作优先级，视觉上更轻但不弱化控制能力。
- **复盘分析页**：能力画像、趋势、维度评分、下一步改进任务。

### 3.3 管理端信息架构

管理端继续使用侧边栏，但重做为更轻的管理控制台：

- 侧栏颜色从深蓝灰改为浅色或中性低对比。
- 内容区采用白色表格、浅灰背景、清晰筛选区。
- 表格密度保留，不使用用户端的大舞台布局。
- 状态颜色、圆角、阴影和用户端共享基础规范。

---

## 4. 设计系统规划

### 4.1 新增和修改文件

用户端：

- 修改：`frontend/user/src/theme.css`
- 新增：`frontend/user/src/styles/apple-tokens.css`
- 新增：`frontend/user/src/styles/apple-components.css`

管理端：

- 修改：`frontend/admin/src/theme.css`
- 新增：`frontend/admin/src/styles/admin-apple-tokens.css`
- 新增：`frontend/admin/src/styles/admin-apple-components.css`

### 4.2 用户端基础 tokens

第一阶段使用以下变量作为基准：

```css
:root,
:root[data-theme="light"] {
  color-scheme: light;
  --orep-font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", system-ui, sans-serif;
  --orep-bg: oklch(0.982 0.006 250);
  --orep-bg-soft: oklch(0.955 0.012 250);
  --orep-surface: oklch(0.995 0.003 250);
  --orep-surface-raised: oklch(1 0.003 250);
  --orep-text: oklch(0.23 0.028 255);
  --orep-text-strong: oklch(0.16 0.026 255);
  --orep-muted: oklch(0.48 0.024 255);
  --orep-faint: oklch(0.68 0.018 255);
  --orep-border: oklch(0.86 0.014 255);
  --orep-border-soft: oklch(0.91 0.01 255);
  --orep-blue: oklch(0.58 0.205 255);
  --orep-blue-hover: oklch(0.52 0.22 255);
  --orep-blue-soft: oklch(0.93 0.035 255);
  --orep-green: oklch(0.62 0.16 150);
  --orep-orange: oklch(0.72 0.15 70);
  --orep-red: oklch(0.62 0.19 28);
  --orep-radius-sm: 8px;
  --orep-radius-md: 14px;
  --orep-radius-lg: 22px;
  --orep-radius-stage: 32px;
  --orep-shadow-soft: 0 18px 60px oklch(0.42 0.05 255 / 0.12);
  --orep-shadow-stage: 0 30px 90px oklch(0.42 0.05 255 / 0.16);
  --orep-ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --el-color-primary: var(--orep-blue);
  --el-bg-color: var(--orep-surface);
  --el-bg-color-overlay: var(--orep-surface-raised);
  --el-border-color: var(--orep-border);
  --el-text-color-primary: var(--orep-text);
  --el-text-color-regular: var(--orep-muted);
}
```

### 4.3 组件样式规则

- 主按钮：蓝色填充，40-48px 高，圆角胶囊或 12px 圆角。
- 次按钮：白底或透明底，浅边框。
- 舞台容器：最大宽度 1180-1280px，居中，28-32px 圆角，轻边框，柔和阴影。
- 工作台布局：桌面端 `260px minmax(0, 1fr) 320px` 三栏。
- 移动端：单栏布局，Agent 面板下沉为页面区块或抽屉。
- 标题：只有首页/舞台页使用大标题，工具页标题保持紧凑。
- 动效：只用透明度和轻微位移动效，不做布局属性动画。

---

## 5. 组件架构

### 5.1 用户端新增组件

新增目录：

- `frontend/user/src/components/apple/`

新增组件：

- `OrepTopNav.vue`：全局顶部导航、项目切换、用户菜单。
- `OrepMobileNav.vue`：移动端底部导航。
- `OrepPageShell.vue`：页面宽度、边距、背景控制。
- `OrepStage.vue`：首页和关键流程的舞台容器。
- `OrepActionButton.vue`：统一主按钮/次按钮/危险按钮。
- `OrepAgentPanel.vue`：右侧 AI 建议和快捷操作。
- `OrepFlowRail.vue`：横向或纵向流程进度。
- `OrepMetricStrip.vue`：紧凑指标条。
- `OrepTaskList.vue`：下一步任务列表。
- `OrepAbilityRadar.vue`：ECharts 雷达图封装。
- `OrepEmptyState.vue`：空状态。
- `OrepSectionHeader.vue`：页面分区标题和操作区。

### 5.2 用户端新增 composable

新增目录：

- `frontend/user/src/composables/apple/`

新增 composable：

- `useOrepNavigation.js`：导航分组、激活状态、移动端显示规则。
- `useOrepProjectContext.js`：当前项目、路演进度、默认 fallback。
- `useOrepAgentSuggestions.js`：按页面返回 Agent 建议。
- `useOrepResponsiveShell.js`：桌面/移动端布局状态。

第一版 composable 可以先返回静态 fallback 数据，页面迁移时再逐步接入现有 API。

### 5.3 管理端新增组件

新增目录：

- `frontend/admin/src/components/apple/`

新增组件：

- `AdminShell.vue`：侧边栏、顶部栏、内容区。
- `AdminPageHeader.vue`：页面标题、说明、操作按钮。
- `AdminFilterBar.vue`：筛选、搜索、批量操作。
- `AdminStatusBadge.vue`：统一状态标签。
- `AdminMetricCard.vue`：管理端指标卡。

---

## 6. 页面迁移阶段

### 阶段 0：基线构建和安全检查

目标：确认现有前端可以构建，记录修改前状态。

执行：

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

```bash
cd /Users/liuyixing/项目/OREP/frontend/admin
npm run build
```

检查页面：

- 用户端：`/`、`/course-learning`、`/exam-system`、`/script-editor`、`/ppt-generator`、`/statistics`
- 管理端：`/dashboard`

验收：

- 构建能通过，或明确记录当前已有构建错误。
- 修改前截图和控制台错误有记录。

### 阶段 1：tokens 和应用壳

目标：先统一视觉底座，不触碰页面业务逻辑。

涉及文件：

- `frontend/user/src/main.js`
- `frontend/user/src/theme.css`
- `frontend/user/src/App.vue`
- `frontend/user/src/styles/apple-tokens.css`
- `frontend/user/src/styles/apple-components.css`
- `frontend/user/src/components/apple/OrepTopNav.vue`
- `frontend/user/src/components/apple/OrepMobileNav.vue`
- `frontend/user/src/components/apple/OrepPageShell.vue`
- `frontend/user/src/composables/apple/useOrepNavigation.js`

验收：

- `/login` 不显示应用导航。
- 登录后页面显示新顶部导航。
- `/meeting/` 会议路由保持特殊沉浸处理。
- 移动端显示底部导航。
- 未登录访问鉴权路由仍跳转 `/login`。

### 阶段 2：首页样板

目标：把 `Dashboard.vue` 做成全站视觉样板，对齐参考图 1/2。

涉及文件：

- `frontend/user/src/views/Dashboard.vue`
- `frontend/user/src/components/apple/OrepStage.vue`
- `frontend/user/src/components/apple/OrepFlowRail.vue`
- `frontend/user/src/components/apple/OrepMetricStrip.vue`
- `frontend/user/src/components/apple/OrepTaskList.vue`
- `frontend/user/src/components/apple/OrepAgentPanel.vue`
- `frontend/user/src/composables/apple/useOrepProjectContext.js`
- `frontend/user/src/composables/apple/useOrepAgentSuggestions.js`

目标结构：

- 顶部主标题：`下一场路演，从这里开始。`
- 中央舞台：当前项目、主行动、Agent 行动。
- 右侧区域：上次进度、下一步建议、最近分数。
- 底部流程：材料、脚本、PPT、练习、路演、复盘。

验收：

- 首页无 API 数据时也有合理 fallback。
- 主按钮能进入核心准备流程。
- 桌面和移动端都无横向溢出。
- 首页风格确认后再迁移其他页面。

### 阶段 3：路演准备工作流

目标：把脚本和 PPT 相关页面统一为三栏工作台。

涉及文件：

- `frontend/user/src/views/ScriptList.vue`
- `frontend/user/src/views/ScriptEditor.vue`
- `frontend/user/src/views/PptGenerator.vue`
- `frontend/user/src/views/PptTemplate.vue`
- `frontend/user/src/views/PptHistoryDetail.vue`
- `frontend/user/src/views/PptEditor.vue`
- `frontend/user/src/components/apple/OrepWorkbenchLayout.vue`
- `frontend/user/src/components/apple/OrepResourceRail.vue`
- `frontend/user/src/components/apple/OrepGenerationPanel.vue`
- `frontend/user/src/components/apple/OrepDocumentPreview.vue`

原则：

- `ScriptList.vue` 改为资源列表 + 最近编辑 + 下一步行动。
- `ScriptEditor.vue` 改为中间写作区 + 右侧 Agent 建议。
- `PptGenerator.vue` 改为项目材料栏 + 生成表单 + Agent 检查清单。
- `PptEditor.vue` 只改外壳，第一轮不重写 React/Konva 核心。

验收：

- 脚本新增、编辑、列表仍可用。
- PPT 生成仍能提交。
- PPT 编辑器能打开旧内容。
- 下载准备和修复相关 composable 不受影响。

### 阶段 4：学习与考试

目标：把课程和考试从工具页改成「备赛路径」。

涉及文件：

- `frontend/user/src/views/CourseLearning.vue`
- `frontend/user/src/views/CourseLessonPlayer.vue`
- `frontend/user/src/views/ExamSystem.vue`
- `frontend/user/src/views/ExamPractice.vue`
- `frontend/user/src/views/ExamTaking.vue`
- `frontend/user/src/views/ExamWrongBook.vue`
- `frontend/user/src/views/ExamFavorites.vue`
- `frontend/user/src/components/apple/OrepLearningPath.vue`
- `frontend/user/src/components/apple/OrepPracticeLauncher.vue`
- `frontend/user/src/components/apple/OrepQuestionCard.vue`
- `frontend/user/src/components/apple/OrepReviewQueue.vue`

验收：

- 课程列表、课程播放、学习进度仍正常。
- 练习、考试、错题、收藏路由参数不变。
- 做题页面移动端可读，不被大视觉元素干扰。

### 阶段 5：会议、评分与数据分析

目标：把路演、录制、评分、AI 复盘、数据分析串成提升闭环。

涉及文件：

- `frontend/user/src/views/OnlineMeeting.vue`
- `frontend/user/src/views/MeetingRoom.vue`
- `frontend/user/src/views/MeetingHistoryDetail.vue`
- `frontend/user/src/views/MyRecordings.vue`
- `frontend/user/src/views/ScoreResult.vue`
- `frontend/user/src/views/AiScoreResult.vue`
- `frontend/user/src/views/RoadshowChat.vue`
- `frontend/user/src/views/Statistics.vue`
- `frontend/user/src/components/apple/OrepAbilityRadar.vue`
- `frontend/user/src/components/apple/OrepScoreTrend.vue`
- `frontend/user/src/components/apple/OrepRecordingList.vue`
- `frontend/user/src/components/apple/OrepReviewActionPlan.vue`

验收：

- LiveKit 加入、退出、静音、录制能力不变。
- 录制列表和详情仍可加载。
- 评分页展示字段不丢失。
- 数据分析图表 resize 正常。

### 阶段 6：登录、个人中心、团队、空状态

目标：补齐次级页面体验。

涉及文件：

- `frontend/user/src/views/Login.vue`
- `frontend/user/src/views/Profile.vue`
- `frontend/user/src/views/ProjectTeam.vue`
- `frontend/user/src/components/apple/OrepEmptyState.vue`

验收：

- 登录表单可提交，错误提示可见。
- 个人中心操作正常。
- 团队成员、角色、权限展示不丢失。

### 阶段 7：管理端重设计

目标：管理端与新品牌一致，但保持后台效率。

涉及文件：

- `frontend/admin/src/main.js`
- `frontend/admin/src/theme.css`
- `frontend/admin/src/style.css`
- `frontend/admin/src/views/Layout.vue`
- `frontend/admin/src/styles/admin-apple-tokens.css`
- `frontend/admin/src/styles/admin-apple-components.css`
- `frontend/admin/src/components/apple/AdminShell.vue`
- `frontend/admin/src/components/apple/AdminPageHeader.vue`
- `frontend/admin/src/components/apple/AdminFilterBar.vue`
- `frontend/admin/src/components/apple/AdminStatusBadge.vue`
- `frontend/admin/src/components/apple/AdminMetricCard.vue`

迁移页面：

- `Dashboard.vue`
- `Analytics.vue`
- `DataMonitor.vue`
- `Users.vue`
- `OrganizationManagement.vue`
- `Meetings.vue`
- `Scores.vue`
- `Issues.vue`
- `Resources.vue`
- `CourseManagement.vue`
- `ExamManagement.vue`
- `PptManagement.vue`
- `AiJuryPersonas.vue`
- `HomeBannerManagement.vue`

验收：

- `MENU_ROLE_MAP`、`showMenu` 和权限显示逻辑不变。
- 表格排序、筛选、分页、批量操作不丢失。
- 管理端构建通过。

---

## 7. 详细任务清单

### 任务 1：构建基线

涉及文件：

- `frontend/user/package.json`
- `frontend/admin/package.json`

- [ ] 执行用户端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：Vite 构建完成并生成 `dist`。

- [ ] 执行管理端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/admin
npm run build
```

预期：Vite 构建完成并生成 `dist`。

- [ ] 如果构建失败，先记录错误文件和错误信息，再开始 UI 修改。

### 任务 2：新增用户端 tokens

涉及文件：

- 新增：`frontend/user/src/styles/apple-tokens.css`
- 新增：`frontend/user/src/styles/apple-components.css`
- 修改：`frontend/user/src/main.js`

- [ ] 在 `apple-tokens.css` 中写入第 4.2 节 tokens。
- [ ] 在 `apple-components.css` 中写入基础类：

```css
.orep-page {
  min-height: calc(100vh - 72px);
  padding: 32px;
  background:
    radial-gradient(circle at 50% 0%, oklch(0.92 0.04 255 / 0.75), transparent 34rem),
    var(--orep-bg);
}

.orep-shell-width {
  width: min(100%, 1280px);
  margin: 0 auto;
}

.orep-stage {
  border: 1px solid var(--orep-border-soft);
  border-radius: var(--orep-radius-stage);
  background: linear-gradient(180deg, var(--orep-surface-raised), var(--orep-surface));
  box-shadow: var(--orep-shadow-stage);
}

.orep-primary-action {
  min-height: 44px;
  border-radius: 999px;
  padding: 0 22px;
  border: 1px solid var(--orep-blue);
  background: var(--orep-blue);
  color: oklch(0.99 0.004 255);
  font-weight: 700;
}
```

- [ ] 在 `main.js` 中调整 CSS 引入顺序：

```js
import './theme.css'
import './styles/apple-tokens.css'
import './styles/apple-components.css'
import './orep-feedback.css'
import './mobile.css'
```

- [ ] 运行用户端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：构建通过。

### 任务 3：新增导航 composable

涉及文件：

- 新增：`frontend/user/src/composables/apple/useOrepNavigation.js`

- [ ] 写入导航分组和激活判断：

```js
export const OREP_NAV_ITEMS = [
  { path: '/', label: '首页', code: 'Home', group: 'home' },
  { path: '/course-learning', label: '学习', code: 'Learn', group: 'learn' },
  { path: '/exam-system', label: '练习', code: 'Practice', group: 'practice' },
  { path: '/script-editor', label: '准备', code: 'Prepare', group: 'prepare' },
  { path: '/online-meeting', label: '路演', code: 'Roadshow', group: 'roadshow' },
  { path: '/statistics', label: '提升', code: 'Improve', group: 'improve' },
  { path: '/project-team', label: '团队', code: 'Team', group: 'team' },
]

export function isOrepRouteActive(routePath, itemPath) {
  if (itemPath === '/') return routePath === '/'
  if (itemPath === '/script-editor') {
    return routePath.startsWith('/script-editor')
      || routePath.startsWith('/ppt-generator')
      || routePath.startsWith('/ppt-editor')
      || routePath.startsWith('/resources')
      || routePath.startsWith('/ppt-history')
  }
  if (itemPath === '/online-meeting') {
    return routePath.startsWith('/online-meeting')
      || routePath.startsWith('/meeting/')
      || routePath.startsWith('/meeting-history')
      || routePath.startsWith('/my-recordings')
  }
  if (itemPath === '/statistics') {
    return routePath.startsWith('/statistics')
      || routePath.startsWith('/score-result')
      || routePath.startsWith('/ai-score')
      || routePath.startsWith('/roadshow-chat')
  }
  return routePath.startsWith(itemPath)
}
```

- [ ] 运行用户端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：构建通过。

### 任务 4：新增用户端应用壳组件

涉及文件：

- 新增：`frontend/user/src/components/apple/OrepTopNav.vue`
- 新增：`frontend/user/src/components/apple/OrepMobileNav.vue`
- 新增：`frontend/user/src/components/apple/OrepPageShell.vue`
- 修改：`frontend/user/src/App.vue`

- [ ] 将当前 `App.vue` 中的导航渲染迁移到 `OrepTopNav.vue`。
- [ ] 使用 `OREP_NAV_ITEMS` 和 `isOrepRouteActive` 管理导航状态。
- [ ] 保留用户下拉菜单命令：个人中心、AI PPT 生成、退出登录。
- [ ] 保留 `/meeting/` 路由的特殊处理。
- [ ] 登录页不包裹应用壳。
- [ ] 运行用户端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：构建通过，路由守卫行为不变。

### 任务 5：首页重构

涉及文件：

- 修改：`frontend/user/src/views/Dashboard.vue`
- 新增：`frontend/user/src/components/apple/OrepStage.vue`
- 新增：`frontend/user/src/components/apple/OrepFlowRail.vue`
- 新增：`frontend/user/src/components/apple/OrepMetricStrip.vue`
- 新增：`frontend/user/src/components/apple/OrepTaskList.vue`
- 新增：`frontend/user/src/components/apple/OrepAgentPanel.vue`
- 新增：`frontend/user/src/composables/apple/useOrepProjectContext.js`
- 新增：`frontend/user/src/composables/apple/useOrepAgentSuggestions.js`

- [ ] 新增项目上下文 fallback：

```js
export function useOrepProjectContext() {
  return {
    projectName: '智慧农业温室项目',
    nextActionLabel: '开始今日路演准备',
    lastProgressLabel: '脚本优化完成',
    scoreLabel: '上次路演 78 分',
    completion: 72,
  }
}
```

- [ ] 新增 Agent 建议 fallback：

```js
export function useOrepAgentSuggestions(page = 'dashboard') {
  const common = [
    { title: '补齐项目亮点', description: '把技术方案、市场价值和团队分工合成一页路演要点。' },
    { title: '生成练习任务', description: '根据最近一次评分生成 3 个高优先级练习目标。' },
  ]
  return { suggestions: common, page }
}
```

- [ ] 首页按顺序实现：主标题、项目舞台、下一步任务、Agent 面板、流程进度、指标条。
- [ ] 主按钮跳转到 `/script-editor`，后续接入真实项目上下文后再跳转到当前任务。
- [ ] 运行用户端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：构建通过。

### 任务 6：路演准备工作流迁移

涉及文件：

- 修改：`frontend/user/src/views/ScriptList.vue`
- 修改：`frontend/user/src/views/ScriptEditor.vue`
- 修改：`frontend/user/src/views/PptGenerator.vue`
- 修改：`frontend/user/src/views/PptTemplate.vue`
- 修改：`frontend/user/src/views/PptHistoryDetail.vue`
- 修改：`frontend/user/src/views/PptEditor.vue`
- 新增：`frontend/user/src/components/apple/OrepWorkbenchLayout.vue`
- 新增：`frontend/user/src/components/apple/OrepResourceRail.vue`
- 新增：`frontend/user/src/components/apple/OrepGenerationPanel.vue`
- 新增：`frontend/user/src/components/apple/OrepDocumentPreview.vue`

- [ ] `OrepWorkbenchLayout` 提供 `rail`、`main`、`agent` 三个 slot。
- [ ] 脚本列表迁移为资源栏 + 主列表。
- [ ] 脚本编辑器迁移为写作区 + Agent 建议。
- [ ] PPT 生成器迁移为材料栏 + 生成区 + 检查清单。
- [ ] PPT 模板和历史页面迁移为白色预览卡片。
- [ ] PPT 编辑器只改 Vue 外壳，不改 React/Konva 核心。
- [ ] 每迁移一个页面都运行构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：每个页面迁移后构建通过。

### 任务 7：学习与考试迁移

涉及文件：

- 修改：`frontend/user/src/views/CourseLearning.vue`
- 修改：`frontend/user/src/views/CourseLessonPlayer.vue`
- 修改：`frontend/user/src/views/ExamSystem.vue`
- 修改：`frontend/user/src/views/ExamPractice.vue`
- 修改：`frontend/user/src/views/ExamTaking.vue`
- 修改：`frontend/user/src/views/ExamWrongBook.vue`
- 修改：`frontend/user/src/views/ExamFavorites.vue`
- 新增：`frontend/user/src/components/apple/OrepLearningPath.vue`
- 新增：`frontend/user/src/components/apple/OrepPracticeLauncher.vue`
- 新增：`frontend/user/src/components/apple/OrepQuestionCard.vue`
- 新增：`frontend/user/src/components/apple/OrepReviewQueue.vue`

- [ ] 课程首页突出“今日学习路径”。
- [ ] 课程播放页面保留播放器/内容布局稳定性。
- [ ] 考试系统突出一个下一步练习行动。
- [ ] 考试作答页保证题干、选项、提交按钮优先可读。
- [ ] 错题和收藏使用复习队列布局。
- [ ] 完成学习页面后构建一次，完成考试页面后构建一次。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：构建通过。

### 任务 8：会议、评分和数据分析迁移

涉及文件：

- 修改：`frontend/user/src/views/OnlineMeeting.vue`
- 修改：`frontend/user/src/views/MeetingRoom.vue`
- 修改：`frontend/user/src/views/MeetingHistoryDetail.vue`
- 修改：`frontend/user/src/views/MyRecordings.vue`
- 修改：`frontend/user/src/views/ScoreResult.vue`
- 修改：`frontend/user/src/views/AiScoreResult.vue`
- 修改：`frontend/user/src/views/RoadshowChat.vue`
- 修改：`frontend/user/src/views/Statistics.vue`
- 新增：`frontend/user/src/components/apple/OrepAbilityRadar.vue`
- 新增：`frontend/user/src/components/apple/OrepScoreTrend.vue`
- 新增：`frontend/user/src/components/apple/OrepRecordingList.vue`
- 新增：`frontend/user/src/components/apple/OrepReviewActionPlan.vue`

- [ ] 在线会议页使用舞台 + 日程/入口布局。
- [ ] 会议室保留全屏操作优先级。
- [ ] 我的录制使用清晰列表和预览行动。
- [ ] 评分页展示能力画像、关键评价、下一步行动。
- [ ] 数据分析页展示雷达图、趋势、维度拆解。
- [ ] 运行用户端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

预期：构建通过。

### 任务 9：管理端壳和 tokens

涉及文件：

- 修改：`frontend/admin/src/main.js`
- 修改：`frontend/admin/src/theme.css`
- 修改：`frontend/admin/src/style.css`
- 修改：`frontend/admin/src/views/Layout.vue`
- 新增：`frontend/admin/src/styles/admin-apple-tokens.css`
- 新增：`frontend/admin/src/styles/admin-apple-components.css`
- 新增：`frontend/admin/src/components/apple/AdminShell.vue`
- 新增：`frontend/admin/src/components/apple/AdminPageHeader.vue`
- 新增：`frontend/admin/src/components/apple/AdminFilterBar.vue`
- 新增：`frontend/admin/src/components/apple/AdminStatusBadge.vue`
- 新增：`frontend/admin/src/components/apple/AdminMetricCard.vue`

- [ ] 在 `main.js` 中引入管理端新 tokens。
- [ ] 将 `Layout.vue` 中硬编码侧栏颜色改成 token class。
- [ ] 保持 `MENU_ROLE_MAP` 和 `showMenu` 逻辑不变。
- [ ] 运行管理端构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/admin
npm run build
```

预期：构建通过，权限菜单行为不变。

### 任务 10：管理端页面迁移

涉及文件：

- 修改第 2.2 节列出的所有管理端页面。

- [ ] 第一批迁移：`Dashboard.vue`、`Analytics.vue`。
- [ ] 第二批迁移：`DataMonitor.vue`、`Issues.vue`。
- [ ] 第三批迁移：用户、组织、会议、评分、资源、课程、考试、PPT、AI 评审团、首页轮播。
- [ ] 保留 API 调用、分页、筛选、批量删除、权限判断。
- [ ] 每迁移 2-3 个页面运行一次构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/admin
npm run build
```

预期：构建通过。

### 任务 11：视觉 QA

- [ ] 启动用户端开发服务器。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run dev
```

- [ ] 检查桌面宽度：1440、1280、1024。
- [ ] 检查移动端宽度：430、390、360。
- [ ] 检查用户端页面：`/`、`/course-learning`、`/exam-system`、`/script-editor`、`/ppt-generator`、`/statistics`、`/profile`。
- [ ] 启动管理端开发服务器。

```bash
cd /Users/liuyixing/项目/OREP/frontend/admin
npm run dev
```

- [ ] 检查管理端页面：`/dashboard`、`/users`、`/meetings`、`/scores`、`/analytics`、`/resources`。
- [ ] 确认没有文字重叠、按钮溢出、横向滚动、对比度过低或弹层主题错乱。

### 任务 12：最终回归

- [ ] 用户端最终构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

- [ ] 管理端最终构建。

```bash
cd /Users/liuyixing/项目/OREP/frontend/admin
npm run build
```

- [ ] 检查变更范围。

```bash
cd /Users/liuyixing/项目/OREP
git status --short
```

预期：如果当前目录是 git 仓库，只出现预期的前端和文档变更。如果当前目录不是 git 仓库，则使用编辑器 diff 或文件列表记录变更。

---

## 8. 验收标准

### 8.1 用户端

- 所有登录后路由可以打开。
- 登录页不显示应用导航。
- 顶部导航对分组路由的激活状态正确。
- 首页符合 Apple 风格参考图方向。
- 脚本/PPT 工作流形成统一工作台。
- 课程/考试形成备赛路径体验。
- 会议室功能稳定，不因视觉重构受损。
- 统计和评分页能明确呈现能力提升路径。
- 移动端无横向溢出。

### 8.2 管理端

- 权限菜单显隐逻辑不变。
- CRUD 页面保留表格、筛选、分页、批量操作。
- 管理端更轻、更统一，但不变成大卡片展示页。

### 8.3 技术

- `frontend/user` 的 `npm run build` 通过。
- `frontend/admin` 的 `npm run build` 通过。
- 无未解析 import。
- 无因组件 props 缺失导致的控制台错误。
- Element Plus 下拉、弹窗、选择器、日期选择器、表格主题一致。

---

## 9. 风险清单

### 风险 1：范围过大

用户端页面很多，一次迁移容易破坏交互。

应对：按业务域迁移，每完成一个页面族就构建验证。

### 风险 2：PPT 编辑器受损

PPT 编辑器是 React/Konva 嵌入 Vue 的特殊区域。

应对：第一轮只改外层 Vue 壳和 CSS，不重写画布核心。

### 风险 3：Element Plus 主题不一致

弹层、下拉、表格可能保留默认样式。

应对：在 token 文件中统一覆盖 Element Plus 变量，并逐项检查弹窗、下拉、日期选择器和表格。

### 风险 4：移动端重叠

Apple 风格大标题和舞台布局在小屏上容易挤压内容。

应对：使用明确断点，不使用基于 viewport 的字体缩放，逐屏检查 360-430px 宽度。

### 风险 5：误改后端协议

UI 重构可能顺手改掉请求参数或数据字段。

应对：请求工具、API payload、鉴权逻辑默认不动；需要适配时只在页面内做轻量 adapter。

---

## 10. 推荐执行顺序

如果 `/Users/liuyixing/项目/OREP` 不是 git 仓库，执行前先确认是否需要复制一份工作目录或建立外部版本记录。

推荐顺序：

1. 阶段 0：构建基线。
2. 阶段 1：tokens 和应用壳。
3. 阶段 2：首页样板。
4. 停下来做一次视觉确认。
5. 阶段 3：脚本/PPT 准备工作流。
6. 停下来做一次功能确认。
7. 阶段 4 和阶段 5：学习、考试、会议、复盘。
8. 阶段 7：管理端刷新。
9. 最终响应式 QA 和构建验证。

第一轮最关键的检查点是阶段 2：首页样板。如果首页方向不对，不要继续迁移其他页面，先调整设计语言。

