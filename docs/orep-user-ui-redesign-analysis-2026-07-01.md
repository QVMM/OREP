# OREP 用户端新版 UI 与页面分析

生成日期：2026-07-01  
范围：`frontend/user` 用户端全部已注册路由、共享壳层、详情页、工作台、弹窗、抽屉、沉浸式页面。  
参考输入：微信文件 `index.html` 与截图中的“竞赛备考 AI Platform”浅暖橙三栏工作台风格。

## 1. 设计目标

新版用户端不再按“传统顶部导航 + 各页面单独长页面”的方式呈现，而是统一成一个竞赛备考工作台：

- 左侧固定为模块导航与身份/版本区域。
- 顶部固定为搜索、当前项目、提醒、日程、帮助等全局操作。
- 中央为当前任务主工作区，每个页面根据任务类型切换为看板、列表、播放器、编辑器、报告或会议舞台。
- 右侧为 AI 助手、项目进度、最近结果、待办建议等上下文面板。
- 沉浸式页面（会议室、练习、答题、课程播放）保留专注模式，但视觉语言与新版壳层一致。

参考图的关键风格可以保留：暖色浅背景、半透明白色面板、柔和阴影、橙色主行动、圆角任务卡、右侧 AI 陪伴栏。需要克制的是，不把每个模块都做成大卡片堆叠；工具页、报表页和编辑页要更像专业产品。

## 2. 当前用户端代码结构

用户端入口是 `frontend/user/src/App.vue`：

- 登录页 `/login` 不使用应用壳层。
- 普通页面使用 `OrepTopNav` + `OrepPageShell` + `OrepMobileNav`。
- 沉浸式页面由路由 `meta.immersive` 或 `shouldUseImmersiveShell()` 控制。

当前一级导航来自 `useOrepNavigation.js`：

| 模块 | 当前路径 | 当前含义 | 新版呈现 |
|---|---|---|---|
| 首页 | `/` | 用户总览、快捷入口 | 工作台首页，承载项目进度、今日任务、AI 建议 |
| 赛道匹配 | `/track-match` | 42 赛道库与智能匹配 | 赛道雷达 + 筛选库 + 推荐理由 |
| 学习 | `/course-learning` | 课程列表、详情、课时播放 | 课程中心 + 详情页 + 沉浸播放器 |
| 练习 | `/exam-system` | 训练、考试、错题、收藏 | 练习诊断台 + 练习/考试沉浸页 |
| 准备 | `/script-editor` | 脚本、资源、PPT 生成编辑 | 路演材料工作台 |
| 路演 | `/online-meeting` | 会议列表、会议室、录制 | 路演排练中心 + 沉浸会议室 |
| 评分总结 | `/statistics` | 评分统计、AI 报告 | AI 评分报告与复盘 |
| 团队 | `/project-team` | 团队管理 | 团队协作看板 |

## 3. 需要覆盖的页面

下面只列当前路由和组件实际用到的页面，不包含没有路由入口的旧文件。

### 3.1 认证与总览

1. `/login`，`Login.vue`  
   登录、注册跳转合并入口。新版应做成独立浅色品牌登录页：左侧品牌/项目说明，右侧登录卡片，不显示主壳层。

2. `/`，`Dashboard.vue`  
   当前包含首页主视觉、核心能力模块、大赛信息、智能记录盒。新版应改成参考图式三栏首页：当前项目、项目完成度、优先任务、快捷入口、项目任务、团队动态、AI 助手。

### 3.2 赛道匹配

3. `/track-match`，`TrackMatch.vue`  
   当前包含赛道库说明、智能匹配辅助区、分类筛选、42 赛道卡片。新版应突出“匹配过程”：左侧筛选/项目画像，中间赛道推荐结果，右侧 AI 解释与下一步备赛建议。

### 3.3 课程学习

4. `/course-learning`，`CourseLearning.vue` 列表态  
   当前包含课程 hero、分类树、周计划、筛选、课程卡片。新版应将周计划前置，课程列表更密集，右侧显示学习建议和最近课时。

5. `/course-learning/:courseId`，`CourseLearning.vue` 详情态  
   同一个组件内通过 `selectedCourse` 切换详情。当前包含详情 hero、课程目录、介绍、学习记录、课程资料四个 tab。新版应作为课程详情图单独呈现：上方课程目标与进度，下方目录/资料/记录切换，右侧学习路径。

6. `/course-learning/:courseId/lesson/:lessonId`，`CourseLessonPlayer.vue`  
   当前是课程播放器，包含视频、目录、笔记、课后动作。新版应为沉浸学习模式：顶部回退与进度，中间视频，右侧课时目录与笔记。

### 3.4 练习考试

7. `/exam-system`，`ExamSystem.vue`  
   当前包含能力诊断、任务队列、训练/考试/错题 tab。新版应是“练习诊断台”：诊断环、推荐训练、试卷列表、错题复盘入口、AI 练习建议。

8. `/exam-system/wrong-book`，`ExamWrongBook.vue`  
   错题本子页面。新版应以错题队列、知识点标签、复盘建议、再练按钮为主。

9. `/exam-system/favorites`，`ExamFavorites.vue`  
   收藏题子页面。新版应以收藏题清单、来源筛选、复习状态为主。

10. `/exam-system/practice/:source`，`ExamPractice.vue`  
    沉浸练习页。当前包含题目舞台、答案选项、答题卡、完成结果。新版应保留专注布局：左侧题目，中间答题，右侧题号网格与解析。

11. `/exam-system/take/:paperId`，`ExamTaking.vue`  
    正式答题页。新版与练习页相似，但更强调时间、提交确认、题目导航、考试状态。

### 3.5 路演与会议

12. `/online-meeting`，`OnlineMeeting.vue`  
    当前是会议/排练入口，包含创建会议、会议列表、进入会议室。新版应是路演排练中心：近期排练、创建会议、会议记录、AI 评分入口。

13. `/meeting/:id`，`MeetingRoom.vue`  
    沉浸会议室。当前包含视频宫格/屏幕共享、聊天侧栏、评分侧栏、问题列表、移动折叠控件。新版应为深浅结合的专注会议舞台：主视频/共享区、成员条、底部控制条、可展开聊天/评分侧栏。

14. `/meeting-history/:id`，`MeetingHistoryDetail.vue`  
    会议历史详情。新版应突出回放、摘要、聊天记录、评分结果、AI 建议。

15. `/my-recordings`，`MyRecordings.vue`  
    我的录制。新版应呈现录制列表、转写状态、生成报告/下载入口。

### 3.6 AI 评分与复盘

16. `/score-result/:meetingId`，`ScoreResult.vue`  
    旧评分表格结果页，包含 Element Plus 表格和 AI 复盘问答入口。新版可作为“简版评分列表”图，重点是评分人、维度、分数、评语。

17. `/roadshow-chat/:meetingId`，`RoadshowChat.vue`  
    AI 复盘问答。新版应做成复盘聊天工作台：左侧评分摘要，中间对话，右侧证据/建议。

18. `/ai-score-upload`，`VideoScoreUpload.vue`  
    视频评分上传入口，内部使用 `VideoScoreUploadForm`。新版应为“上传与评分启动”图：上传区、项目/会议选择、评分配置、运行状态。

19. `/ai-score/report/:sessionId/*`、`/ai-score/report-id/:reportId/*`、`/ai-score/:meetingId/*`，`AiScoreReportLayout.vue` + 7 个子页面  
    三套路由复用同一报告布局，必须按子页面单独出图：
    - `overview`：总览、问题队列、证据时间线、维度影响。
    - `dimensions`：维度得分、证据关联、扣分原因。
    - `evidence`：证据时间线、关键帧、转写、锚点表。
    - `voice`：表达训练、语速/停顿/口癖、改写建议。
    - `presentation`：PPT/现场呈现问题、画面截图标注、训练任务。
    - `actions`：团队工作项、优先级、负责人、验收标准。
    - `jury`：16 人格评审团复核、共识矩阵、成员观点。

20. `/ai-score/report-prototype`，`AiScoreReportPrototype.vue`  
    原型页。若用于内部验证可保留为“报告原型总览”，新版图中可并入 AI 报告总览，不作为正式导航主页面。

### 3.7 准备/PPT/资料

21. `/script-editor`，`ScriptList.vue`  
    脚本列表。新版应为路演稿管理台：脚本列表、模板入口、最近编辑、AI 优化建议。

22. `/script-editor/detail/:scriptId` 和 `/script-editor/template/:templateId`，`ScriptEditor.vue`  
    脚本编辑详情。新版应为编辑器布局：左侧章节，中央正文，右侧 AI 建议/评分点。

23. `/resources`，`PptTemplate.vue`  
    PPT 模板/资源页。新版应为模板库：筛选、模板卡、适用赛道、使用按钮。

24. `/ppt-generator`，`PptGenerator.vue`  
    旧生成向导，包含 `el-steps`。新版应为生成流程页：资料上传、目标配置、生成步骤、结果入口。

25. `/ppt-editor`，`PptEditor.vue`  
    重型 PPT 工作台。当前用到历史生成记录抽屉、问卷/资料补充抽屉、内容卡片确认、预览工作区、质量报告、路演结构检查、补图任务内联抽屉。新版应单独出图，采用“三栏编辑器”：左侧流程与历史，中间幻灯片预览/卡片，右侧 AI 质量/补充资料/路演检查。

26. `/ppt-history/:id`，`PptHistoryDetail.vue`  
    PPT 历史详情。新版应展示历史版本、预览、质量报告、下载与继续编辑。

### 3.8 统计、团队与个人

27. `/statistics`，`Statistics.vue`  
    评分总结。新版应为数据盘点页：趋势、维度雷达、训练完成度、最近报告。

28. `/project-team`，`ProjectTeam.vue`  
    团队协作。新版应为团队看板：成员、分工、任务、动态、资料缺口。

29. `/profile`，`Profile.vue`  
    个人中心。新版应为账户与成长档案：基础信息、项目身份、学习/练习/评分记录、设置。

## 4. 当前弹窗、抽屉和浮层

需要在新版设计中体现的交互层：

- `PptEditor.vue`
  - 历史生成记录抽屉 `historyDrawer`。
  - 问卷与材料补充抽屉 `questionnaireDrawer`。
  - 内容卡片确认区 `showCardPlanning`。
  - 内联补图任务抽屉由 `PptHtmlWorkbench.vue` 呈现。
- `FilePreview.vue`
  - 全局文件预览弹窗，支持预览与下载。
- `AudioRecorder.vue`
  - AI 评分开始弹窗 `AiScoreStartDialog`。
  - AI 评分运行弹窗 `AiScoreRunningDialog`。
- `MeetingRoom.vue`
  - 聊天侧栏 `showChat`。
  - 评分侧栏 `showScore`。
  - 问题列表折叠 `showIssues`。
  - 屏幕共享侧边成员条 `showScreenSidebar`。
- `CourseLessonPlayer.vue`
  - 视频加载/错误覆盖层。
- `ai-score-report` 子页面
  - 证据点击跳转、维度打开、问题筛选、评审团成员切换，建议统一为右侧上下文面板或页内详情，而不是频繁弹窗。

## 5. 新版视觉系统建议

### 5.1 场景句

学生在白天或宿舍/教室里准备比赛，需要连续完成学习、练习、资料整理、路演排练、AI 评分复盘。界面应明亮、稳定、可信，AI 的存在感要像教练，不像广告页。

### 5.2 色彩

- 主背景：暖米白到浅橙，接近参考图。
- 主色：竞赛橙，用于主要行动、当前模块、关键提醒。
- 辅助色：蓝色表示学习/资料，绿色表示通过/在线，琥珀表示待补充，红色表示风险。
- 面板：半透明白、轻边框、柔和阴影。
- 数据页：保持浅色基底，允许局部深色图表和高对比证据区域。

### 5.3 布局

推荐统一四种模板：

1. `Dashboard Shell`：左导航 + 顶部搜索 + 中央工作台 + 右 AI 面板。
2. `Catalog Shell`：左筛选/树 + 中央列表/卡片 + 右建议/摘要。
3. `Workbench Shell`：左流程/历史 + 中央编辑/播放器/报告 + 右质检/AI 建议。
4. `Immersive Shell`：无主导航，顶部轻量信息 + 主舞台 + 可折叠侧栏 + 底部控制。

### 5.4 组件语言

- 卡片圆角控制在 16-24px，重复列表项更小，避免每层都套卡片。
- 主要按钮为橙色实心，次要按钮为白色或浅底。
- 标签使用低饱和底色，不用大面积纯色。
- 表格、报告、编辑器要更紧凑，减少装饰光效。
- AI 助手固定为右侧上下文栏，包含“当前建议、最近结果、可执行命令”。

## 6. 本次生成的 UI 图清单

本次设计稿以 `outputs/orep-user-ui-redesign-20260701/index.html` 为源文件生成，每个页面单独截图。页面图建议文件名如下：

1. `01-login.png`
2. `02-dashboard.png`
3. `03-track-match.png`
4. `04-course-learning.png`
5. `05-course-detail.png`
6. `06-course-lesson-player.png`
7. `07-exam-system.png`
8. `08-exam-wrong-book.png`
9. `09-exam-favorites.png`
10. `10-exam-practice.png`
11. `11-exam-taking.png`
12. `12-online-meeting.png`
13. `13-meeting-room.png`
14. `14-meeting-history-detail.png`
15. `15-my-recordings.png`
16. `16-score-result.png`
17. `17-roadshow-chat.png`
18. `18-ai-score-upload.png`
19. `19-ai-report-overview.png`
20. `20-ai-report-dimensions.png`
21. `21-ai-report-evidence.png`
22. `22-ai-report-voice.png`
23. `23-ai-report-presentation.png`
24. `24-ai-report-actions.png`
25. `25-ai-report-jury.png`
26. `26-script-list.png`
27. `27-script-editor.png`
28. `28-resources.png`
29. `29-ppt-generator.png`
30. `30-ppt-editor.png`
31. `31-ppt-history-detail.png`
32. `32-statistics.png`
33. `33-project-team.png`
34. `34-profile.png`
35. `35-file-preview-modal.png`
36. `36-ppt-history-drawer.png`
37. `37-ppt-questionnaire-drawer.png`
38. `38-ai-score-running-dialog.png`

## 7. 落地注意事项

- 如果后续要真正改代码，建议先改壳层和 token，再按模块迁移页面，避免每页各自重写。
- `PptEditor.vue` 很重，应先提炼可复用工作台组件，再改 UI。
- AI 报告 7 个子页面已具备复杂数据结构，新版应统一报告页框架、筛选条、证据面板和右侧建议面板。
- 会议室、考试、课程播放属于沉浸式，不应强塞三栏主壳层。
- 当前 `theme.css` 与 `apple-tokens.css` 有新旧变量并存，真正实现时需要统一 token 来源。
