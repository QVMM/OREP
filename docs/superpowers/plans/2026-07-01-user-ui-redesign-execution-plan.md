# 用户端 UI 重构执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 OREP 用户端从多代页面风格并存，重构为统一的暖橙色竞赛备考工作台 UI，并保留现有课程、考试、会议、AI 评分、PPT、讲稿、团队协作等业务流程。

**Architecture:** 先统一全局设计 token、页面壳、基础组件、反馈组件，再按页面风险分阶段换皮。普通页面迁移到“左侧导航 + 顶部搜索 + 中间工作区 + 右侧 AI 助手”的工作台结构；会议室、考试答题、正式考试继续保留沉浸式壳，只替换局部视觉组件。

**Tech Stack:** Vue 3、Vue Router、Pinia、Element Plus、Vite、LiveKit、React PPT workspace、现有 `Base*` 组件、现有 `components/apple/*` 壳组件、现有 `components/ai-score/*` 报告组件。

---

## 0. 执行原则

- 只改用户端：`frontend/user`。
- 先做可复用组件，再改页面，不在每个页面重复写同一套卡片、按钮、弹窗样式。
- 不第一阶段重写复杂业务逻辑：会议室、正式考试、PPT 编辑器、团队工作台、AI 报告数据流必须保持原有状态机和接口调用。
- 保留现有路由，不改 URL 结构，避免影响后端、外链和已有入口。
- 每一阶段都必须能独立构建通过，并能在 `https://localhost:5174/` 人工验收。
- 视觉以用户提供的截图和 HTML 为主：暖橙色、浅色纸面/玻璃卡片、左侧导航、顶部搜索、右侧 AI 助手、项目任务驱动。

## 1. 总文件结构规划

### 1.1 新增文件

- `frontend/user/src/styles/workspace-tokens.css`
  - 新工作台设计 token，承载暖橙色主题、字体、圆角、阴影、Element Plus 变量映射。
- `frontend/user/src/styles/workspace-components.css`
  - 全局通用工作台样式类：页面容器、卡片、按钮、chip、空状态、section header、响应式布局。
- `frontend/user/src/components/workspace/WorkspaceShell.vue`
  - 新桌面端工作台外壳，负责左侧导航、顶部搜索、右侧 AI 面板插槽、内容区。
- `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
  - 左侧导航、品牌、版本权益、用户信息。
- `frontend/user/src/components/workspace/WorkspaceTopbar.vue`
  - 顶部搜索、日历、消息、帮助、项目快捷入口。
- `frontend/user/src/components/workspace/WorkspaceAiRail.vue`
  - 右侧 AI 助手/项目状态面板，可折叠，普通页面复用。
- `frontend/user/src/components/workspace/WorkspaceMobileNav.vue`
  - 新移动端底部导航，覆盖现有导航项缺失问题。
- `frontend/user/src/components/workspace/PageHero.vue`
  - 页面通用标题区，支持标题、副标题、状态、主操作按钮。
- `frontend/user/src/components/workspace/MetricCard.vue`
  - 指标卡。
- `frontend/user/src/components/workspace/TaskListCard.vue`
  - 任务列表卡。
- `frontend/user/src/components/workspace/ActivityFeedCard.vue`
  - 团队动态/系统动态卡。
- `frontend/user/src/components/workspace/QuickEntryGrid.vue`
  - 快捷入口网格。
- `frontend/user/src/components/workspace/ProgressPipeline.vue`
  - 上传、AI 评分、PPT 生成通用流程进度条。
- `frontend/user/src/components/workspace/ResourceCard.vue`
  - 文件、录制、模板、资料卡片。
- `frontend/user/src/components/workspace/UnifiedEmptyState.vue`
  - 全站空状态。
- `frontend/user/src/components/workspace/index.js`
  - 导出 workspace 组件。

### 1.2 修改文件

- `frontend/user/src/main.js`
  - 调整全局 CSS 导入顺序，去掉重复导入，加入 `workspace-tokens.css` 和 `workspace-components.css`。
- `frontend/user/src/App.vue`
  - 将非登录、非沉浸页面壳切到 `WorkspaceShell`。
- `frontend/user/src/composables/apple/useOrepNavigation.js`
  - 保留路由激活逻辑，扩展移动端导航项和更多入口规则；后续可改名，但第一阶段不强制改名。
- `frontend/user/src/orep-feedback.css`
  - 将 Element Plus 消息、通知、确认框、遮罩统一成新暖色工作台风格。
- `frontend/user/src/mobile.css`
  - 第一阶段保留，仅追加必要兼容，不删除旧补丁。
- `frontend/user/src/components/base/BaseButton.vue`
- `frontend/user/src/components/base/BaseCard.vue`
- `frontend/user/src/components/base/BaseInput.vue`
  - 对齐新 token。
- `frontend/user/src/views/Dashboard.vue`
- `frontend/user/src/views/Statistics.vue`
- `frontend/user/src/views/Profile.vue`
- `frontend/user/src/views/PptTemplate.vue`
- `frontend/user/src/views/TrackMatch.vue`
- `frontend/user/src/views/OnlineMeeting.vue`
- `frontend/user/src/views/CourseLearning.vue`
- `frontend/user/src/views/CourseLessonPlayer.vue`
- `frontend/user/src/views/ExamSystem.vue`
- `frontend/user/src/views/MeetingHistoryDetail.vue`
- `frontend/user/src/views/MyRecordings.vue`
- `frontend/user/src/views/VideoScoreUpload.vue`
- `frontend/user/src/views/ai-score-report/*.vue`
- `frontend/user/src/views/ScoreResult.vue`
- `frontend/user/src/views/RoadshowChat.vue`
- `frontend/user/src/views/ScriptList.vue`
- `frontend/user/src/views/ScriptEditor.vue`
- `frontend/user/src/views/PptEditor.vue`
- `frontend/user/src/views/PptHistoryDetail.vue`
- `frontend/user/src/views/ProjectTeam.vue`
- `frontend/user/src/views/ExamPractice.vue`
- `frontend/user/src/views/ExamTaking.vue`
- `frontend/user/src/views/MeetingRoom.vue`
  - 分阶段重构，具体阶段见下文。

### 1.3 第一轮不改或只做最小兼容的文件

- `frontend/user/src/views/MeetingRoom.vue`
  - 第一阶段不整体重构，只保证新全局 token 不破坏沉浸式页面。
- `frontend/user/src/views/ExamPractice.vue`
  - 第一阶段不改答题交互。
- `frontend/user/src/views/ExamTaking.vue`
  - 第一阶段不改倒计时、自动交卷、切屏记录。
- `frontend/user/src/views/PptEditor.vue`
  - 第一阶段不改生成状态机、React workspace、上传材料逻辑。
- `frontend/user/src/views/ProjectTeam.vue`
  - 第一阶段不拆大文件，只做外观兼容评估。
- `frontend/user/src/views/ai-score-report/*.vue`
  - 第一阶段不改数据流和报告上下文，只做外层 shell 兼容。
- `frontend/user/src/views/AiScoreResult.vue`
  - 当前未直接被路由使用，不纳入首轮。
- `frontend/user/src/views/MeetingList.vue`
  - 当前未被路由注册，不纳入重构范围；只在确认仍有入口时再处理。

## 2. 阶段 1：全局工作台基础设施

**目标:** 先建立新 UI 的地基，让后续页面只组合组件，不重复造样式。

**涉及文件:**

- Create: `frontend/user/src/styles/workspace-tokens.css`
- Create: `frontend/user/src/styles/workspace-components.css`
- Create: `frontend/user/src/components/workspace/WorkspaceShell.vue`
- Create: `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- Create: `frontend/user/src/components/workspace/WorkspaceTopbar.vue`
- Create: `frontend/user/src/components/workspace/WorkspaceAiRail.vue`
- Create: `frontend/user/src/components/workspace/WorkspaceMobileNav.vue`
- Create: `frontend/user/src/components/workspace/index.js`
- Modify: `frontend/user/src/main.js`
- Modify: `frontend/user/src/App.vue`
- Modify: `frontend/user/src/composables/apple/useOrepNavigation.js`
- Modify: `frontend/user/src/orep-feedback.css`

### Task 1.1：建立新 workspace token

- [ ] 新建 `workspace-tokens.css`，定义暖橙色浅色主题变量。
- [ ] 将 Element Plus 的主色、背景、边框、文字变量映射到新 token。
- [ ] 保留现有 `--orep-*` 关键变量名，避免旧页面引用失效。
- [ ] 不删除 `theme.css`、`apple-tokens.css`，第一阶段通过导入顺序覆盖。

验收标准：

- `body` 背景变为暖浅色，不再默认暗色。
- Element Plus 输入框、弹窗、下拉、按钮主色与暖橙主题一致。
- 旧页面中引用 `--orep-bg`、`--orep-text`、`--orep-border` 的地方不报样式异常。

### Task 1.2：建立全局 workspace 组件样式

- [ ] 新建 `workspace-components.css`。
- [ ] 定义 `.workspace-page`、`.workspace-card`、`.workspace-section-title`、`.workspace-primary-btn`、`.workspace-secondary-btn`、`.workspace-chip`、`.workspace-empty`。
- [ ] 定义响应式规则：桌面三栏、中屏右栏折叠、移动端单列。
- [ ] 不把页面专属 class 写进该文件。

验收标准：

- 新增样式类可被首页、统计页、个人中心复用。
- 不影响沉浸式会议室和考试页布局。

### Task 1.3：调整全局 CSS 导入

- [ ] 修改 `main.js`，去掉重复的 `./styles/design-system.css` 导入。
- [ ] 导入顺序建议为：Element Plus -> design-system -> theme -> apple-tokens -> workspace-tokens -> apple-components -> workspace-components -> orep-feedback -> mobile。
- [ ] 保留 `mobile.css` 最后导入，避免旧移动端补丁失效。

验收标准：

- `npm run build` 通过。
- 页面加载后无明显暗色 token 残留在普通页面背景。
- 移动端底部导航仍能显示。

### Task 1.4：实现新工作台壳

- [ ] 新建 `WorkspaceShell.vue`，负责普通页面整体布局。
- [ ] 新建 `WorkspaceSidebar.vue`，迁移截图中的左侧品牌、导航、版本、用户区。
- [ ] 新建 `WorkspaceTopbar.vue`，实现搜索、日历、消息、帮助按钮。
- [ ] 新建 `WorkspaceAiRail.vue`，实现右侧项目完成度、AI 建议、最近结果、输入框。
- [ ] 新建 `WorkspaceMobileNav.vue`，至少包含：首页、学习、练习、准备、路演、AI 评分、团队、我的。
- [ ] `WorkspaceShell` 根据路由 meta 或屏幕宽度控制 AI 右栏显隐。

验收标准：

- 普通页面进入后显示左侧导航、顶部栏、内容区。
- 登录页不显示工作台壳。
- `/meeting/:id`、`/exam-system/practice/:source`、`/exam-system/take/:paperId` 不显示工作台壳。
- 右侧 AI 面板在桌面端可见，中小屏可折叠或下移。

### Task 1.5：替换 App 壳层

- [ ] 修改 `App.vue`，非登录、非沉浸路由使用 `WorkspaceShell`。
- [ ] 保留 `shouldUseImmersiveShell(route.path)` 和 `route.meta.immersive` 判断。
- [ ] 暂时保留 `OrepTopNav/OrepPageShell/OrepMobileNav` 文件，不删除，避免其他引用破坏。

验收标准：

- `/`、`/course-learning`、`/statistics` 使用新壳。
- `/login` 保持独立登录页。
- `/meeting/123` 不显示左侧导航和右侧 AI 面板。

### Task 1.6：统一 Element Plus 反馈样式

- [ ] 修改 `orep-feedback.css`，将 `el-message`、`el-notification`、`el-message-box`、`el-overlay` 调整为新暖色浅色风格。
- [ ] 删除或覆盖旧式深色 command 风格。
- [ ] 危险确认仍保持红色语义。

验收标准：

- 登录错误提示、考试交卷确认、录制删除确认、退出登录提示视觉一致。
- 弹窗遮罩、圆角、按钮风格符合新 UI。

### Task 1.7：阶段 1 验证

- [ ] 运行 `npm run build`，预期构建通过。
- [ ] 本地启动 `npm run dev -- --host 0.0.0.0`，访问 `https://localhost:5174/` 或当前可用 dev URL。
- [ ] 验证路由：`/login`、`/`、`/course-learning`、`/statistics`、`/online-meeting`、`/meeting/1`。
- [ ] 检查浏览器 console 无新增布局相关错误。

阶段 1 暂不动页面：

- `MeetingRoom.vue`
- `ExamPractice.vue`
- `ExamTaking.vue`
- `PptEditor.vue`
- `ProjectTeam.vue`
- `ai-score-report/*.vue` 内部结构

## 3. 阶段 2：首页和低风险页面

**目标:** 快速让用户第一眼看到新 UI，并完成简单页面统一。

**涉及文件:**

- Create: `frontend/user/src/components/workspace/PageHero.vue`
- Create: `frontend/user/src/components/workspace/MetricCard.vue`
- Create: `frontend/user/src/components/workspace/TaskListCard.vue`
- Create: `frontend/user/src/components/workspace/ActivityFeedCard.vue`
- Create: `frontend/user/src/components/workspace/QuickEntryGrid.vue`
- Create: `frontend/user/src/components/workspace/UnifiedEmptyState.vue`
- Create: `frontend/user/src/components/workspace/ResourceCard.vue`
- Modify: `frontend/user/src/views/Dashboard.vue`
- Modify: `frontend/user/src/views/Statistics.vue`
- Modify: `frontend/user/src/views/Profile.vue`
- Modify: `frontend/user/src/views/PptTemplate.vue`
- Modify: `frontend/user/src/views/TrackMatch.vue`
- Modify: `frontend/user/src/views/OnlineMeeting.vue`
- Modify: `frontend/user/src/components/base/BaseButton.vue`
- Modify: `frontend/user/src/components/base/BaseCard.vue`
- Modify: `frontend/user/src/components/base/BaseInput.vue`

### Task 2.1：升级 Base 组件

- [ ] `BaseButton.vue` 支持 `primary`、`secondary`、`ghost`、`danger`、`pill`、`loading`。
- [ ] `BaseCard.vue` 支持 `elevated`、`flat`、`interactive`、`padding`。
- [ ] `BaseInput.vue` 对齐新 token，保留现有 v-model、错误状态、图标插槽能力。

验收标准：

- `Login.vue`、`Profile.vue`、`OnlineMeeting.vue`、`PptGenerator.vue` 现有使用不报错。
- 旧 props 不被破坏。

### Task 2.2：首页 `Dashboard.vue` 重构

- [ ] 改为工作台首页：欢迎区、项目主卡、优先任务、快捷入口、项目任务、团队动态。
- [ ] 保留原有三个主入口：AI 评分、会议室、PPT 生成。
- [ ] 快捷入口对应现有路由：课程学习、考试练习、项目准备、在线路演、评分总结、团队。
- [ ] 右侧 AI 面板由全局 `WorkspaceAiRail` 承担，页面内不重复实现。

验收标准：

- 首页视觉接近用户提供截图。
- 点击“开始 AI 评分”进入 `/ai-score-upload`。
- 点击“进入会议室”进入 `/online-meeting`。
- 点击“生成路演 PPT”进入 `/ppt-editor`；如产品决定保留旧流程，则进入 `/ppt-generator`。
- 首页移动端单列展示，无横向溢出。

### Task 2.3：评分总结 `Statistics.vue` 重构

- [ ] 改为评分报告中心卡片布局。
- [ ] 保留 tabs：我参加的会议、我队伍的会议。
- [ ] 保留数据加载、错误、空状态、fallback 逻辑。
- [ ] 报告项改为统一卡片，显示来源、标题、日期、状态、问题数、总分、高风险数。

验收标准：

- `scope=joined` 和 `scope=team` 都能触发原接口请求。
- sessionId/reportId/meetingId 三种跳转仍正确。
- 空状态显示“发起路演评分”和“上传视频评分”。

### Task 2.4：个人中心 `Profile.vue` 重构

- [ ] 使用 `PageHero`、`BaseCard`、`BaseInput`、`BaseButton`。
- [ ] 保留身份信息卡和修改密码卡。
- [ ] 不改密码接口和校验逻辑。

验收标准：

- 用户名、邮箱、注册时间显示正常。
- 修改密码成功/失败提示正常。
- 重置表单正常。

### Task 2.5：资源中心 `PptTemplate.vue` 重构

- [ ] 改为资源卡片页。
- [ ] 使用 `ResourceCard` 展示文件名、大小、格式、下载按钮。
- [ ] 保留 `/api/ppt-template` 拉取逻辑。
- [ ] 保留 token 拼接下载逻辑。

验收标准：

- 有资源时可下载。
- 无资源时显示统一空状态。
- 返回首页按钮正常。

### Task 2.6：赛道匹配 `TrackMatch.vue` 重构

- [ ] 顶部 hero 显示 42 赛道、领域数量、AI 辅助匹配。
- [ ] 左侧或顶部保留项目方向、核心技能选择。
- [ ] 分类筛选改成统一 tabs/chips。
- [ ] 赛道卡片统一样式。
- [ ] 查看详情建议改成抽屉或展开卡；如果本阶段不做详情抽屉，按钮应有明确反馈，不保留无效按钮。

验收标准：

- 分类筛选结果正确。
- 生成参考建议后匹配结果显示。
- 42 个赛道内容不丢失。

### Task 2.7：在线会议入口 `OnlineMeeting.vue` 重构

- [ ] 改为路演接入中心。
- [ ] 左侧加入会议卡：会议号、密码、记住凭据、加入按钮。
- [ ] 右侧创建会议卡：权限判断、标题、时长、创建按钮。
- [ ] 下方会议历史卡片列表。
- [ ] 保留上传视频评分入口。

验收标准：

- 会议号仍限制 6 位。
- 回车加入会议正常。
- 记住会议号/密码正常。
- 普通用户无创建权限提示正常。
- 创建成功后会议号/密码复制正常。
- 历史会议进入详情、复制、AI 评分入口正常。

### Task 2.8：阶段 2 验证

- [ ] 运行 `npm run build`。
- [ ] 人工验收路由：`/`、`/statistics`、`/profile`、`/resources`、`/track-match`、`/online-meeting`。
- [ ] 使用桌面宽度 1440、1366、移动端 390 验证无横向滚动。

阶段 2 暂不动页面：

- `MeetingRoom.vue`
- `ExamPractice.vue`
- `ExamTaking.vue`
- `PptEditor.vue`
- `PptHistoryDetail.vue`
- `ProjectTeam.vue`
- `ScriptList.vue`
- `ScriptEditor.vue`
- `ai-score-report/*.vue` 内部结构

## 4. 阶段 3：课程、考试入口、会议历史、录制、上传评分

**目标:** 统一中复杂页面的内容布局，但不改沉浸式答题/会议核心逻辑。

**涉及文件:**

- Create: `frontend/user/src/components/workspace/ProgressPipeline.vue`
- Modify: `frontend/user/src/views/CourseLearning.vue`
- Modify: `frontend/user/src/views/CourseLessonPlayer.vue`
- Modify: `frontend/user/src/views/ExamSystem.vue`
- Modify: `frontend/user/src/components/exam/QuestionReviewDesk.vue`
- Modify: `frontend/user/src/views/MeetingHistoryDetail.vue`
- Modify: `frontend/user/src/views/MyRecordings.vue`
- Modify: `frontend/user/src/views/VideoScoreUpload.vue`
- Modify: `frontend/user/src/components/ai-score/VideoScoreUploadForm.vue` only if needed for visual consistency

### Task 3.1：课程列表/详情 `CourseLearning.vue`

- [ ] 列表态改为学习工作台：学习进度 hero、分类筛选、课程卡片、学习计划。
- [ ] 详情态改为课程详情页：hero、目录、介绍、学习记录、资料 tabs。
- [ ] 保留同一文件根据 `courseId` 切换列表/详情的逻辑。
- [ ] 不改课程数据结构和课时跳转逻辑。

验收标准：

- `/course-learning` 显示课程列表。
- `/course-learning/:courseId` 显示课程详情。
- 点击课时进入 `/course-learning/:courseId/lesson/:lessonId`。
- 搜索、分类、继续学习正常。

### Task 3.2：课时播放器 `CourseLessonPlayer.vue`

- [ ] 保留半沉浸式播放器结构。
- [ ] 顶部栏、视频卡片、目录、笔记、行动面板统一视觉。
- [ ] 不改笔记 localStorage key。
- [ ] 不改播放顺序和倍速限制逻辑。

验收标准：

- 视频能播放。
- 课程目录切换正常。
- 笔记保存后刷新仍存在。
- 阶段测评/章节练习入口正常。

### Task 3.3：考试系统入口 `ExamSystem.vue`

- [ ] 改为训练驾驶舱：能力诊断、今日推荐、训练中心、正式考试、错题复盘。
- [ ] 保留推荐训练、正式考试、错题本、收藏题入口。
- [ ] 不改 `/exam-system/practice/:source` 和 `/exam-system/take/:paperId`。

验收标准：

- 推荐训练跳转练习页。
- 正式考试跳转考试页。
- 错题本、收藏题跳转正确。
- tab 切换正常。

### Task 3.4：错题/收藏组件 `QuestionReviewDesk.vue`

- [ ] 使用统一卡片、筛选、空状态。
- [ ] 保留 `fetch-url`、`practice-source`、`accent` props。
- [ ] 保留收藏/取消收藏、查看解析、一键练习。

验收标准：

- `/exam-system/wrong-book` 和 `/exam-system/favorites` 均正常加载。
- 一键练习进入正确 source。
- 解析展开正常。

### Task 3.5：会议历史详情 `MeetingHistoryDetail.vue`

- [ ] 改为统一详情页：会议 hero、指标卡、评分闭环、tabs。
- [ ] 聊天记录、评分结果、问题列表保留原数据展示。
- [ ] AI 评分报告入口突出。

验收标准：

- 返回记录正常。
- 查看 AI 评分报告、上传视频评分、团队扣分项入口正常。
- tab 切换正常。
- 导出问题报告正常。

### Task 3.6：录制资源库 `MyRecordings.vue`

- [ ] 改为录制资源库卡片布局。
- [ ] 保留搜索、状态筛选、刷新、展开详情。
- [ ] 播放区统一视觉，但不改播放 URL 获取逻辑。
- [ ] 删除确认使用统一 Element Plus 反馈样式。

验收标准：

- 搜索和状态筛选正常。
- 展开录制能播放视频/音频/摄像头/屏幕文件。
- 播放/暂停/全屏正常。
- 删除确认和删除结果正常。

### Task 3.7：视频评分上传 `VideoScoreUpload.vue`

- [ ] 改为上传评分工作台：上传表单、处理流程、上传进度、AI 分析进度。
- [ ] 使用 `ProgressPipeline` 展示阶段：排队、音频抽取、ASR、抽帧、OCR、模型评分、规则校准、报告生成。
- [ ] 不改上传状态回调、session 创建、轮询逻辑。

验收标准：

- 上传进度、速度、剩余时间显示正常。
- 上传完成后创建评分 session。
- AI 分析轮询状态正常。
- 完成后可打开报告。

### Task 3.8：阶段 3 验证

- [ ] 运行 `npm run build`。
- [ ] 人工验收：课程列表/详情/播放器、考试首页/错题/收藏、会议历史、录制、视频上传。
- [ ] 抽查移动端课程、考试、录制页面。

阶段 3 暂不动页面：

- `MeetingRoom.vue` 核心会议室
- `ExamPractice.vue` 答题页
- `ExamTaking.vue` 正式考试页
- `PptEditor.vue`
- `PptHistoryDetail.vue`
- `ProjectTeam.vue`
- `ScriptList.vue`
- `ScriptEditor.vue`

## 5. 阶段 4：AI 评分报告、旧评分结果、复盘问答

**目标:** 保留现有 AI 报告数据闭环，统一报告视觉和 AI 问答入口。

**涉及文件:**

- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportLayout.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportDimensions.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportEvidence.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportVoice.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportPresentation.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportActions.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportJury.vue`
- Modify: `frontend/user/src/components/ai-score/report/AiScoreReportShell.vue`
- Modify: `frontend/user/src/components/ai-score/report/*.vue`
- Modify: `frontend/user/src/views/ScoreResult.vue`
- Modify: `frontend/user/src/views/RoadshowChat.vue`

### Task 4.1：报告 shell 视觉统一

- [ ] 修改 `AiScoreReportShell.vue`，使用新工作台卡片、tabs、section header。
- [ ] 保留 provide/inject 上下文。
- [ ] 保留子路由和加载/错误/进度态。

验收标准：

- `/ai-score/report/:sessionId/overview` 正常加载。
- 子页面切换路径不变。
- 加载态、错误态、session 进度态正常。

### Task 4.2：AI 报告子页视觉统一

- [ ] Overview 保留综合得分、诊断结论、KPI、问题队列、证据时间线、五维评分。
- [ ] Dimensions 保留维度切换和扣分项。
- [ ] Evidence 保留证据链。
- [ ] Voice 保留表达节奏和训练话术。
- [ ] Presentation 保留现场呈现问题。
- [ ] Actions 保留改进方案和团队动作。
- [ ] Jury 保留 16 人格/评审团复核展示。

验收标准：

- 每个子页面内容不丢失。
- 问题优先级筛选正常。
- 证据时间点、关键帧选择正常。
- 生成团队工作项正常。

### Task 4.3：旧评分结果 `ScoreResult.vue`

- [ ] 改为兼容型历史评分详情页。
- [ ] 用卡片和分组列表替代裸 `el-table` 视觉。
- [ ] 保留导出 PDF、AI 复盘问答、返回。
- [ ] 移除 emoji 文案。

验收标准：

- `/score-result/:meetingId` 能加载旧评分数据。
- 导出 PDF 正常。
- AI 复盘问答跳转正常。

### Task 4.4：复盘问答 `RoadshowChat.vue`

- [ ] 改为统一 AI 助手聊天界面。
- [ ] 保留 streaming 响应、追问建议、语音模式、录音、朗读、帮助弹窗。
- [ ] 移除 emoji 头像，改为统一 AI/用户头像。
- [ ] 帮助弹窗使用统一反馈样式。

验收标准：

- 文本发送正常。
- 追问建议一键发送正常。
- 语音识别和停止录音正常。
- AI 朗读回答正常。
- 帮助弹窗正常。

### Task 4.5：阶段 4 验证

- [ ] 运行 `npm run build`。
- [ ] 人工验收三种报告入口：`/ai-score/report/:sessionId`、`/ai-score/report-id/:reportId`、`/ai-score/:meetingId`。
- [ ] 验证 `ScoreResult.vue` 和 `RoadshowChat.vue` 兼容旧入口。

阶段 4 暂不动页面：

- `MeetingRoom.vue`
- `ExamPractice.vue`
- `ExamTaking.vue`
- `PptEditor.vue` 核心逻辑
- `ProjectTeam.vue` 核心逻辑

## 6. 阶段 5：项目准备、讲稿、PPT 工作台

**目标:** 统一高复杂生产工具页面的外观和模块边界，不重写生成/编辑核心逻辑。

**涉及文件:**

- Modify: `frontend/user/src/views/ScriptList.vue`
- Modify: `frontend/user/src/views/ScriptEditor.vue`
- Modify: `frontend/user/src/views/PptGenerator.vue`
- Modify: `frontend/user/src/views/PptEditor.vue`
- Modify: `frontend/user/src/views/PptHistoryDetail.vue`
- Modify: `frontend/user/src/components/ppt/*.vue`
- Modify: `frontend/user/src/react-ppt-editor/*.css`

### Task 5.1：准备工作台 `ScriptList.vue`

- [ ] 保留 topic/materials/ppt/script/roadshow/versions 工作区。
- [ ] 左侧 rail 改成新工作台侧边分组。
- [ ] 主区卡片、tabs、按钮统一。
- [ ] 右侧 artifact panel 改成“当前成果 + AI 建议 + 团队同步”。
- [ ] 模板新建、另存模板、文档预览弹窗统一视觉。

验收标准：

- 各工作区切换正常。
- rail 折叠/展开正常。
- 团队切换正常。
- 选题 prompt、方向选择、生成策划书、同步团队任务正常。
- 打开讲稿、从模板新建、保存模板、预览文档正常。

### Task 5.2：讲稿编辑器 `ScriptEditor.vue`

- [ ] 顶部工具栏统一。
- [ ] 左侧章节导航卡片化。
- [ ] 右侧步骤编辑区使用统一输入、textarea、chip、按钮。
- [ ] 添加角色、添加章节、另存模板弹窗统一。
- [ ] 不改自动保存逻辑。

验收标准：

- 标题、章节、角色、步骤可编辑。
- 增删章节、角色、步骤正常。
- 步骤上移/下移正常。
- 自动保存状态正常。
- 存为模板、导出 PDF、返回正常。

### Task 5.3：旧 PPT 生成器 `PptGenerator.vue`

- [ ] 产品确认是否保留旧四步生成器。
- [ ] 如保留：换成统一步骤卡、领域卡、问卷表单、大纲确认、生成结果。
- [ ] 如不保留：入口统一跳转 `/ppt-editor`，保留路由但页面显示“已升级到智能 PPT 工作台”。

验收标准：

- 领域选择、问卷、大纲确认、主题选择、下载、历史记录正常；或升级提示跳转正常。

### Task 5.4：PPT 编辑器 `PptEditor.vue`

- [ ] 保留三栏布局：材料/设置、预览/编辑、AI 优化/日志。
- [ ] 左侧生成设置卡片统一。
- [ ] 中间 pipeline、页面内容卡片、React workspace 外层统一。
- [ ] 右侧反馈优化和日志统一。
- [ ] 历史记录 drawer、问卷 drawer 统一视觉。
- [ ] 不改生成状态机、缓存继续、上传材料、React workspace 事件。

验收标准：

- 新建 PPT、选择生成对象、material mode 正常。
- 主文件上传、分类材料上传/删除正常。
- 问卷编辑正常。
- 开始生成、继续缓存、取消生成正常。
- 页面内容卡片保存、确认进入设计渲染正常。
- 下载 PPTX 正常。
- React workspace 选页、删页、新建空白页、保存页、保存备注、刷新预览正常。
- 反馈优化重新生成正常。

### Task 5.5：PPT 历史详情 `PptHistoryDetail.vue`

- [ ] 改成交付详情页：顶部状态、下载条件、质量指标、预览工作台。
- [ ] 保留 `PptDownloadReadinessCard`、`PptHtmlWorkbench`、`PptQualityReportPanel`、`PptRoadshowPanel`、`PptScoringCoveragePanel`、`PptPracticeDemoPanel`、`PptMaterialsAdvancedPanel`。
- [ ] 统一这些组件的卡片、按钮、状态样式。
- [ ] 不改下载条件检查和处理阻塞项逻辑。

验收标准：

- 下载按钮根据状态显示正确文案。
- 下载条件检查正常。
- 处理阻塞项、继续下载、退出下载流程正常。
- HTML 页面/质量报告/路演结构/评分覆盖/实操演示/材料检查正常。

### Task 5.6：阶段 5 验证

- [ ] 运行 `npm run build`。
- [ ] 人工验收 `/script-editor`、`/script-editor/detail/:scriptId`、`/ppt-generator`、`/ppt-editor`、`/ppt-history/:id`。
- [ ] 验证 PPT 上传、生成、下载、历史详情核心流程。

阶段 5 暂不整体重写：

- `PptEditor.vue` 内部生成状态机
- `ReactPptWorkspace.vue` 内部 React/Konva 编辑逻辑
- `ScriptList.vue` 内部业务数据结构

## 7. 阶段 6：团队工作台

**目标:** 拆解并统一 `ProjectTeam.vue` 的高密度协作页面。

**涉及文件:**

- Create: `frontend/user/src/components/team/TeamProjectHeader.vue`
- Create: `frontend/user/src/components/team/TeamWorkRail.vue`
- Create: `frontend/user/src/components/team/TeamWorkItemList.vue`
- Create: `frontend/user/src/components/team/TeamWorkItemDrawer.vue`
- Create: `frontend/user/src/components/team/TeamMaterialPanel.vue`
- Create: `frontend/user/src/components/team/TeamVersionPanel.vue`
- Modify: `frontend/user/src/views/ProjectTeam.vue`

### Task 6.1：拆团队头部

- [ ] 提取项目标题、项目切换、协作状态、准备进度、在线人数、待处理数到 `TeamProjectHeader.vue`。
- [ ] 保留原项目切换 popover 行为。

验收标准：

- 项目信息显示正常。
- 项目切换正常。
- 状态、进度、在线人数、待处理数正常。

### Task 6.2：拆左侧工作 rail

- [ ] 提取工作视图、阶段筛选、资料与团队、准备进度、快捷入口到 `TeamWorkRail.vue`。
- [ ] 保留分组折叠/展开。

验收标准：

- 工作视图切换正常。
- 阶段筛选正常。
- 快捷进入准备、视频评分正常。

### Task 6.3：拆工作项列表和详情抽屉

- [ ] 提取列表到 `TeamWorkItemList.vue`。
- [ ] 提取详情/编辑/分配到 `TeamWorkItemDrawer.vue`。
- [ ] 保留筛选、排序、密度、摘要视图、选中、双击执行、新建工作项。

验收标准：

- 工作项筛选、排序、密度切换正常。
- 选中工作项正常。
- 双击执行工作项正常。
- 新建工作项正常。

### Task 6.4：拆材料和版本面板

- [ ] 提取材料视图到 `TeamMaterialPanel.vue`。
- [ ] 提取版本视图到 `TeamVersionPanel.vue`。
- [ ] 保留成员、材料、任务、版本、路演复盘入口。

验收标准：

- 各分区切换正常。
- 材料、版本、成员、任务入口正常。

### Task 6.5：阶段 6 验证

- [ ] 运行 `npm run build`。
- [ ] 人工验收 `/project-team` 的创建项目、项目切换、分区切换、工作项、新建任务、准备入口、视频评分入口。

阶段 6 暂不改：

- 后端接口契约
- 工作项状态字段含义
- 团队权限逻辑

## 8. 阶段 7：沉浸式页面局部统一

**目标:** 对最高风险页面只做组件级视觉统一，不破坏核心交互。

**涉及文件:**

- Modify: `frontend/user/src/views/MeetingRoom.vue`
- Modify: `frontend/user/src/views/ExamPractice.vue`
- Modify: `frontend/user/src/views/ExamTaking.vue`
- Modify: `frontend/user/src/components/AudioRecorder.vue`
- Modify: `frontend/user/src/components/VoiceAvatar.vue`
- Modify: `frontend/user/src/components/AgentVisualizer.vue`

### Task 7.1：会议室局部视觉统一

- [ ] 只改样式和可拆组件外观，不改 LiveKit 连接逻辑。
- [ ] 顶部会议栏、视频 tile、底部控制栏、聊天面板、评分面板、问题抽屉统一视觉。
- [ ] 保留移动端更多菜单和屏幕共享布局。

验收标准：

- LiveKit 连接、断线重连、手动重连正常。
- 麦克风、摄像头、屏幕共享正常。
- 三种屏幕共享布局正常。
- 聊天文字/图片/文件正常。
- 手动评分提交正常。
- 录制开停正常。
- 问题列表加载、筛选、标记解决正常。
- 清晰度、移动端更多、全屏、离开会议正常。

### Task 7.2：练习答题页 `ExamPractice.vue`

- [ ] 统一顶部栏、题目卡、选项、答题卡、结果面板视觉。
- [ ] 不改答题状态和完成练习逻辑。

验收标准：

- 单选、多选、判断、主观、编程题答题正常。
- 上一题、下一题、题号跳转正常。
- 完成练习、再练一次、返回来源正常。

### Task 7.3：正式考试页 `ExamTaking.vue`

- [ ] 统一顶部栏、倒计时、题目卡、答题卡、交卷确认视觉。
- [ ] 不改倒计时、自动交卷、切屏记录、接口提交逻辑。

验收标准：

- 倒计时正常。
- 到时自动交卷正常。
- 手动交卷确认正常。
- 答题、标记、收藏正常。
- 切屏记录正常。
- 结果页、错题本跳转正常。

### Task 7.4：阶段 7 验证

- [ ] 运行 `npm run build`。
- [ ] 会议室至少完成一次加入、开关麦克风/摄像头、发送消息、打开评分、离开会议。
- [ ] 考试至少完成一次练习和一次正式考试模拟。

## 9. 跨阶段验收清单

每个阶段完成后都必须检查：

- `npm run build` 通过。
- 普通页面无横向滚动。
- 桌面 1440、1366、移动端 390 三种宽度布局可用。
- 登录页不显示工作台壳。
- 沉浸式会议室和考试页不显示普通工作台壳。
- Element Plus 弹窗、消息、下拉菜单风格一致。
- 原路由可访问，URL 不变。
- 浏览器 console 无新增运行时错误。

## 10. 页面级验收标准总表

| 页面 | 文件 | 验收标准 |
|---|---|---|
| 登录 | `Login.vue` | 登录/注册切换、校验、回车提交、记住我、忘记密码、登录跳转正常；不显示工作台壳。 |
| 首页 | `Dashboard.vue` | 呈现新工作台首页；AI 评分、会议室、PPT、课程、练习、团队、评分入口可跳转。 |
| 赛道匹配 | `TrackMatch.vue` | 42 赛道不丢失；方向/技能选择、生成建议、分类筛选正常。 |
| 课程列表/详情 | `CourseLearning.vue` | 列表、详情、搜索、分类、继续学习、课程 tabs、课时跳转正常。 |
| 课时播放 | `CourseLessonPlayer.vue` | 视频播放、目录切换、笔记保存、练习入口、顺序/倍速限制正常。 |
| 考试首页 | `ExamSystem.vue` | 推荐训练、正式考试、错题本、收藏题、tab 切换正常。 |
| 错题/收藏 | `QuestionReviewDesk.vue` | 加载、解析、收藏、一键练习正常。 |
| 练习答题 | `ExamPractice.vue` | 答题、跳题、完成、结果复盘、再练一次正常。 |
| 正式考试 | `ExamTaking.vue` | 倒计时、自动交卷、交卷确认、标记、收藏、切屏记录、结果页正常。 |
| 在线会议入口 | `OnlineMeeting.vue` | 加入、记住凭据、创建权限、创建会议、复制信息、历史、AI 评分入口正常。 |
| 会议室 | `MeetingRoom.vue` | LiveKit、音视频、共享、聊天、评分、录制、问题、清晰度、全屏、离开正常。 |
| 会议历史 | `MeetingHistoryDetail.vue` | 概览、聊天、评分、问题、AI 报告入口、导出问题报告正常。 |
| 录制 | `MyRecordings.vue` | 搜索、筛选、刷新、展开、播放、全屏、删除正常。 |
| 评分总结 | `Statistics.vue` | scope 切换、加载/错误/空状态、三种报告跳转、上传评分入口正常。 |
| 上传评分 | `VideoScoreUpload.vue` | 上传、进度、创建 session、轮询、失败提示、打开报告正常。 |
| AI 报告 | `ai-score-report/*.vue` | 七个子页、问题筛选、证据选择、团队工作项、加载/错误/进度态正常。 |
| 旧评分结果 | `ScoreResult.vue` | 数据加载、导出 PDF、AI 复盘问答、返回正常。 |
| 复盘问答 | `RoadshowChat.vue` | 文本、streaming、追问建议、语音识别、朗读、帮助弹窗正常。 |
| 准备工作台 | `ScriptList.vue` | 模块切换、团队切换、方向生成、策划书、团队任务同步、模板和预览正常。 |
| 讲稿编辑 | `ScriptEditor.vue` | 自动保存、章节/角色/步骤增删改、移动步骤、存模板、导出 PDF 正常。 |
| 资源中心 | `PptTemplate.vue` | 资源加载、空状态、下载、返回正常。 |
| PPT 生成 | `PptGenerator.vue` | 领域、问卷、大纲、主题、生成、下载、历史；或升级跳转正常。 |
| PPT 编辑 | `PptEditor.vue` | 上传、问卷、生成、缓存继续、取消、卡片确认、React 编辑、反馈优化、下载正常。 |
| PPT 历史 | `PptHistoryDetail.vue` | 下载条件、质量报告、HTML 预览、评分覆盖、材料检查、下载流程正常。 |
| 团队 | `ProjectTeam.vue` | 创建项目、切换项目、分区、筛选、排序、工作项、新建、双击执行、快捷入口正常。 |
| 个人中心 | `Profile.vue` | 信息展示、修改密码、重置、提示正常。 |

## 11. 最终完成标准

- 用户端所有路由仍可访问。
- 普通页面统一为新暖橙色工作台 UI。
- 沉浸式页面视觉统一但核心交互不变。
- 未注册路由页面不作为验收阻塞项，但不得被误删。
- 构建通过。
- 核心闭环可跑通：登录 -> 首页 -> 会议/上传评分 -> AI 报告 -> 团队工作项 -> 准备/PPT/讲稿 -> 再评分复盘。
