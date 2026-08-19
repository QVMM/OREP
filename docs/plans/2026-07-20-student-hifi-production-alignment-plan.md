# OREP 学生端高保真落地方案（对齐稿）

> 日期：2026-07-20  
> 状态：待确认后实施  
> 原型基准：`OREP-高保真原型/user/`  
> 现有成品代码：`frontend/user/` + `backend/` + MySQL / Redis / MinIO  
> 本轮边界：只确定改造方案，不修改业务代码、数据库或接口。

## 1. 结论

不重写现有产品，也不把静态 HTML 原型直接搬进 Vue。采用“保留成熟业务能力，按高保真重组学生端体验，补齐缺失数据闭环”的方式：

1. 保留 Vue 3 学生端、Spring Boot 后端、MySQL、Redis、MinIO 和现有鉴权。
2. 课程、考试、会议、录制、团队任务、材料审核、PPT、讲稿、AI 评分优先复用现有表和接口。
3. 新增 21 天集训编排、文件版本、学习行为、消息、奖状、整改、延期申请等缺失能力。
4. 页面显示的数据全部来自接口。生产页面不保留静态数组、演示 Toast、伪造人数、伪造分数或前端推测状态。
5. 先建立可回滚的数据库迁移机制，再分模块做前后端垂直切片；每个切片都必须能从页面操作到数据库落盘再回显。

## 2. 不变的产品主线

```text
当前项目/团队
  → 今日集训
  → 课程或练习补强
  → 协作交付材料
  → PPT/讲稿准备
  → 在线路演或上传录像
  → AI 评分报告
  → 生成改进任务
  → 再练一场
```

学生首页只回答三件事：

1. 今天练什么、交什么；
2. 路演练到哪一步；
3. 上一次评分最需要改什么。

## 3. 技术落地原则

### 3.1 应用结构

- 继续使用 `frontend/user` 作为学生端独立 SPA。
- 不把学生端与教师端写成一个按角色动态拼页面的 SPA；后续教师端独立应用，共享设计令牌、基础组件和接口类型。
- 学生端先完成路由和页面拆分，不等整个仓库完成 monorepo 重构。
- 保留旧路由作为重定向，避免现有收藏、消息链接和后端返回地址失效。

### 3.2 数据真实性

- 所有分数、人数、时长、任务状态、日期、倒计时、文件版本、奖状、整改均以服务端为准。
- 前端可以做即时乐观更新，但接口失败必须回滚。
- 页面必须实现 loading、empty、error、permission denied、offline/retry 五类状态。
- 数据缺失时显示真实空状态，例如“本场尚未生成转录”，不得补写推测内容。
- AI 评分五维只读取正式报告：技能水平 60、职业素养 10、应用价值 10、团队合作 10、创新创意 10。

### 3.3 数据库迁移

现有部分服务通过 `@PostConstruct` 建表，长期不利于版本控制。正式新增数据前引入 Flyway：

- 对现有数据库做 baseline，不改写历史数据；
- 新表、字段和数据回填统一放入 `Vxxx__*.sql`；
- 禁止继续在新业务 Service 中运行 DDL；
- 每次迁移同时提供索引、回填、回滚说明和生产前备份检查。

## 4. 全局壳与设计规范

### 4.1 导航与布局

- 最终一级顺序：`首页 → 训练营 → 路演中心 → 复盘 → 协作 → 我的`。
- 非首页、非沉浸页统一使用主内容区四边 40px；页面根不再叠加 margin/padding。
- 每页只有一个页面级 `h1`：24px / 700 / 1.3；说明 13px / 1.55；页头到正文 20px。
- 返回按钮进入页头右侧操作组，不独占标题上方一行。
- 会议室、考试作答等沉浸页不显示常规顶栏；弹窗遮罩覆盖顶栏和侧栏。

### 4.2 按钮

- 主按钮：品牌橙 `#E84A1C`、白字；标准 40px，紧凑 36px，大行动 48px。
- 次按钮：白底、浅灰描边、深色字。
- 危险按钮：红色语义，不使用品牌橙冒充危险态。
- 每个按钮必须具备默认、hover、pressed、focus、loading、disabled 状态。
- 不允许仅弹“演示：已完成”的假操作；按钮必须跳转、打开真实弹窗或调用真实接口。

### 4.3 顶栏

- 搜索：服务端搜索课程、任务、文件、报告；支持键盘导航和无结果态。
- 消息：真实未读数、消息列表、全部已读、点击跳到业务对象。
- 删除没有实质功能的日历图标。
- 右侧展示头像和姓名；下拉项为“个人中心、修改密码、退出登录”。
- 修改密码放全局弹窗，不再占用个人中心主页面。
- AI 助手浮钮只有在接入现有 AI Chat 会话后保留，否则阶段性隐藏。

## 5. 页面、子页面、弹窗和按钮改造清单

### 5.1 公共与登录

| 页面 | 目标路由 | 改造 | 主要按钮/弹窗 | 数据 |
|---|---|---|---|---|
| 登录 | `/login` | 保留真实用户名密码登录；移除“选择身份演示进入”和原型导航链接 | 登录、忘记密码（若本期不做则不展示）、登录错误提示 | 复用 `/api/auth/login`、`/api/auth/check` |
| 邀请确认 | `/invite/:token` | 展示邀请团队、项目、发起人、有效期和当前账号 | 接受邀请、拒绝邀请、登录后继续；过期/已处理弹窗 | 新增邀请查询和处理接口 |
| 全局搜索 | 顶栏弹层 | 分组显示课程、任务、文件、报告 | 搜索结果跳转、清空、查看全部 | 新增 `/api/student/search` |
| 消息中心 | 顶栏弹层 | 真实未读消息和业务链接 | 全部已读、单条已读、打开业务对象 | 新增通知表和接口 |
| 账号菜单 | 顶栏下拉 | 头像、姓名、项目角色 | 个人中心、修改密码弹窗、退出确认弹窗 | 复用 Auth Store 和改密接口 |

### 5.2 首页

目标路由：`/`

页面改造：

- 将现有功能入口式 `Dashboard.vue` 改成高保真决策首页。
- 欢迎卡展示真实用户、当前项目、集训第几天、距离备赛结束天数和结束日期。
- “集训进度”读取营日历与本人提交状态；连续打卡从真实连续完成日计算。
- “今天练什么”读取今日训练日、关联项目任务、交付要求和当前提交状态。
- “路演怎么练”读取团队是否已有材料、本周是否完成有效路演、报告是否生成。
- “AI 路演评分”只展示最新正式报告及五维正式分，不使用首页自算分。
- “本周节奏”和“现在可做”由服务端按规则排序，不在前端硬编码。

按钮与结果：

| 按钮 | 行为 |
|---|---|
| 去练路演 | `/roadshow/meetings` |
| 查看今日任务 | `/training/today` |
| 查看全部进度 / 21 天 | `/training/plan` |
| 详情 / 查看提交 | `/training/submissions/:submissionId`；未提交则 `/training/today` |
| 先看微课 | 打开今日任务关联课程；无关联课程时不展示 |
| 去练一场路演 | `/roadshow/meetings`，带当前项目参数 |
| 查看 AI 评分与建议 | `/review/reports/:reportId/summary` |
| 现在可做卡片 | 根据 `targetType + targetId` 跳到真实对象 |

接口：新增 `GET /api/student/home`，一次返回 `userContext、campSummary、todayTraining、roadshowState、latestScore、weekRhythm、nextActions、serverTime`，替代前端并发拼装和静态兜底。

### 5.3 训练营：今日集训与 21 天计划

| 页面 | 目标路由 | 页面内容 | 按钮/弹窗 | 数据策略 |
|---|---|---|---|---|
| 今日集训 | `/training/today` | 营信息、今日任务、交付要求、已提交材料、本周 7 天、老师反馈、下一步 | 查看/提交/重新提交、先看微课、完整计划、查看反馈、去练路演 | 新训练营聚合接口；提交复用项目任务提交 |
| 21 天计划 | `/training/plan` | 按三周纵向分组；明确每周起止日、每天几月几日；使用“第1天”而非 D1 | 点击某日打开日详情；当前日查看提交；锁定日只看说明 | 新增训练营计划接口 |
| 日详情 | `/training/days/:dayId` | 日目标、交付要求、关联课/题、截止日期、状态、历史提交 | 开始任务、查看提交、补强学习 | 新增日详情接口 |
| 我的提交 | `/training/submissions/:submissionId` | 本轮材料、说明、审核状态、版本、提交记录 | 文件预览、音频播放、下载、查看反馈 | 复用任务提交、资产和审核数据 |
| 老师反馈 | `/training/feedback/:submissionId` | 分数、评语、做得好、需改进、建议动作、历史反馈 | 查看提交、按建议练一场、查看关联微课 | 复用 `project_task_submission.review_*`，必要时补结构化反馈字段 |

今日集训提交弹窗：

- 列出全部必交和选交要求；每项明确文件类型、大小、是否已满足。
- 支持本地上传、从文件中心选择、填写说明。
- 提交前确认；提交后展示服务端时间和审核状态。
- “重新提交”只在老师退回或规则允许时可用；保留版本，不覆盖历史。

数据库：新增 `training_camp、training_camp_week、training_camp_team、training_day、training_day_task`；新增通用 `project_task_requirement`。训练任务实体、负责人、提交、资产和审核继续复用现有项目任务表，避免两套任务系统。

### 5.4 课程学习

| 页面 | 目标路由 | 改造 | 主要动作 | 后端 |
|---|---|---|---|---|
| 课程列表 | `/training/courses` | 保留分类、状态筛选；顶部突出总学习时长、当前课程、预计剩余时长 | 继续上次学习、课程详情、筛选分类/状态 | 复用课程列表；补学习汇总字段 |
| 课程详情 | `/training/courses/:courseId` | 弱化“学完你能做到”；课程目录按章节分组；显示总时长、已学时长、剩余时长 | 继续课时、课后自测、下载资料 | 复用课程详情；补结果和进度字段 |
| 课时播放 | `/training/courses/:courseId/lessons/:lessonId` | 视频 + 分章节目录；介绍、资料、我的笔记；心跳保存进度 | 播放、保存笔记、完成本课、下一课、自测 | 复用播放/完成/进度接口；新增笔记和心跳接口 |

弹窗：完成本课确认。确认后调用接口并按章节规则解锁下一课；失败保持当前状态。课程目录和播放器目录使用同一后端结构。

新增数据：`course_lesson_note`；学习时长写入统一学习会话表。现有课程、章节、课时、附件、进度表保留。

### 5.5 练习与考试

| 页面 | 目标路由 | 改造 | 主要动作 |
|---|---|---|---|
| 练习考试中心 | `/training/exams` | 学习状态压缩为次要摘要；取消单独“下一步建议”横幅；训练、正式考试、错题三个列表 | 切换标签、查看训练说明、继续、开始、查看结果 |
| 训练/考试详情 | `/training/exams/:paperId` | 题数、时长、通过分、知识范围、历史成绩；弱化知识点展示 | 开始训练弹窗、先看相关课程 |
| 作答页 | `/training/exam-attempts/:attemptId` | 沉浸页，无顶栏；服务端倒计时、题目导航、自动保存、离屏提示 | 上一题、下一题、标记、交卷 |
| 结果页 | `/training/exam-attempts/:attemptId/result` | 成绩、用时、正确率、逐题结果、错因和关联课程 | 再练一次、复习课程、收藏/取消收藏 |

弹窗：开始训练、交卷确认、时间到自动交卷、离开页面确认。历史记录中的数值明确标注“得分”，避免与序号混淆。

现有考试接口保留；新增可恢复作答能力：

- `GET /api/exams/attempts/:attemptId`
- `PUT /api/exams/attempts/:attemptId/answers/:questionId`
- `PATCH /api/exams/attempts/:attemptId/marks/:questionId`
- `GET /api/exams/attempts/:attemptId/result`

### 5.6 路演中心、在线会议与回放

| 页面 | 目标路由 | 改造 | 主要动作 |
|---|---|---|---|
| 在线路演 | `/roadshow/meetings` | 加入会议、创建会议、会议列表；准备信息只展示可验证来源 | 加入、创建、进入、复制会议信息、查看回放 |
| 会议室 | `/roadshow/meetings/:meetingId/room` | 沉浸式舞台；成员、共享、聊天、录制、计时 | 开始/结束、麦克风、摄像头、共享、录制、聊天、离开 |
| 会议回放列表 | `/roadshow/replays` | 仅做录像列表和转录入口，不混入复杂评分看板 | 播放、查看转录、打开关联报告 |
| 回放详情 | `/roadshow/replays/:meetingId` | 视频播放器 + 时间同步转录；无转录时真实空态 | 播放、倍速、点击转录跳时点、下载允许的文件 |

创建会议弹窗：标题、项目、预计时长、是否录制、参与成员；“会议准备”只展示项目、PPT、讲稿是否由用户确认关联，禁止 AI 猜测“已准备好”。

结束会议弹窗：确认结束、录制处理提示、是否发起 AI 评分。结束动作幂等。

数据：复用 Meeting、Participant、Recording、Chat、MinIO 和 AI transcript 表。新增 `GET /api/meeting/:id/replay` 聚合录像、转录、说话人和关联报告；无转录不新增伪数据。

### 5.7 PPT 与讲稿

| 页面 | 目标路由 | 改造 | 动作 |
|---|---|---|---|
| PPT 制作 | `/roadshow/ppt` | 作品列表、当前项目、生成/编辑状态、版本 | 新建、继续编辑、预览、下载、删除确认 |
| PPT 工作台 | `/roadshow/ppt/:jobId` | 复用现有成熟编辑、预览、质量检查能力，外壳换成规范 | 保存、生成、重试、预览、下载、转讲稿 |
| 讲稿列表 | `/roadshow/scripts` | 项目讲稿、模板和更新时间 | 新建、从 PPT 生成、打开、删除 |
| 讲稿编辑 | `/roadshow/scripts/:scriptId` | 复用现有逐字稿编辑和 PDF 导出 | 自动保存、手动保存、导出、关联 PPT |

此模块不新造业务表，复用现有 PPT、PPT 历史、Script、ScriptTemplate、SlideScript 接口。只补齐列表聚合和权限检查。

### 5.8 协作：任务管理

| 页面 | 目标路由 | 改造 | 主要动作 |
|---|---|---|---|
| 任务管理 | `/collaboration/tasks` | 待我处理、团队进展、待我验收、已完成；右侧检查器只做快速阅读 | 切换项目、新建任务、筛选、打开详情、查看反馈 |
| 任务详情 | `/collaboration/tasks/:taskId` | 来源、完成标准、负责人、截止日期、提交区、动态、关联文件 | 上传/关联文件、保存草稿、提交验收、申请延期、查看来源 |

弹窗：

- 新建任务：标题、说明、来源、负责人（多人）、优先级、开始和截止日期、完成标准、是否需验收。
- 切换项目：只列当前用户可访问项目。
- 提交验收：显示材料和完成标准检查，不满足必交项时禁用。
- 申请延期：新截止日期、原因、提交；不是直接修改任务日期。
- 从文件中心选择：分页、搜索、版本确认。
- 快速预览：真实文件预览；不支持的格式给下载入口。

数据：复用 project_task、assignee、submission、asset、link；新增 `project_task_extension_request、project_task_activity`。状态统一为 TODO / IN_PROGRESS / SUBMITTED / CHANGES_REQUESTED / DONE / EXPIRED；所有中文展示使用“过期”，不出现“逾期”。

### 5.9 协作：文件中心

| 页面 | 目标路由 | 改造 | 主要动作 |
|---|---|---|---|
| 文件中心 | `/collaboration/files` | 当前项目文件、类型/状态筛选、搜索、版本、负责人、关联任务 | 上传文件、新建文件夹（本期可不做）、预览、打开详情 |
| 文件详情 | `/collaboration/files/:fileId` | 预览、当前版本、版本历史、关联任务、操作记录、权限 | 全屏预览、下载、上传新版本、设为当前、归档 |

弹窗：上传文件、上传新版本、设置当前版本确认、归档确认、全屏预览。上传到 MinIO 后数据库提交，数据库失败时清理孤立对象。

数据：保留 `project_material` 作为文件主记录；新增 `project_material_version、project_material_task_link、project_material_activity`，并把现有 material 文件回填为 V1。

### 5.10 复盘：评分列表与上传评分

| 页面 | 目标路由 | 改造 | 主要动作 |
|---|---|---|---|
| 评分报告列表 | `/review/reports` | 最新报告卡 + 历史报告；页面右上不再重复“上传视频评分”按钮，入口只保留在二级导航 | 打开报告、查看改进任务、筛选项目/时间 |
| 上传评分 | `/review/upload` | 选择项目、视频、可选 PPT/讲稿、评分规则确认、上传进度、处理状态 | 选视频、选材料、创建评分、取消上传、查看处理结果 |

上传流程必须显示服务端 session 状态：上传中、预处理、转录、评分、报告生成、失败可重试。复用现有 AI score upload/session 接口，不用前端模拟进度。

### 5.11 复盘：评分报告全部子页

报告骨架固定为：`结果 → 改进任务 → 评分依据 → 多维评委`，另有前后对比。不存在“评委追问”环节。

| 页面 | 目标路由 | 内容 | 动作 |
|---|---|---|---|
| 结果 | `/review/reports/:reportId/summary` | 正式总分、五维、Top 3 问题、结论、下一刀 | 下载报告、再评一场、打开评分项、进入改进任务 |
| 评分项详情 | `/review/reports/:reportId/scores/:dimensionKey` | 该维度评分项、满分/得分、扣分、证据、规则依据 | 打开证据、生成/关联任务 |
| 改进任务 | `/review/reports/:reportId/todos` | 待办、负责人、截止日期、可追回分、验收标准、状态 | 派给队友、同步任务管理、更新状态 |
| 改进任务详情 | `/review/reports/:reportId/todos/:taskId` | 问题、怎么改、验收标准、关联扣分与证据 | 去任务管理、查看证据、重新评分 |
| 评分依据 | `/review/reports/:reportId/evidence` | 视频时间线、转录、画面帧、材料证据、已关联/未识别 | 筛选、搜索、播放到时间点、证据详情 |
| 证据详情 | `/review/reports/:reportId/evidence/:evidenceId` | 原文/画面、时间点、置信度、关联维度、扣分 | 播放、打开评分项 |
| 多维评委 | `/review/reports/:reportId/jury` | 各评价视角、共识、分歧；不改变正式分 | 评委详情、切换评委、查看依据 |
| 评委详情 | `/review/reports/:reportId/jury/:memberId` | 该评委视角、关注点、优点、问题和依据 | 打开关联证据 |
| 前后对比 | `/review/reports/:reportId/compare` | 当前轮与上一轮总分/维度/已解决问题/新问题 | 切换对比轮次、打开两份报告 |

弹窗：派给队友（成员单选/多选、截止日期，字段名称必须为“截止日期”）、下载报告、重新评分确认、证据播放器。复用现有 report、remediation、evidence、jury、speaker、transcript、PDF 接口；前端不得重新计算权威分。

### 5.12 个人中心

目标路由：`/profile`

页面改造：

- 删除账号与安全主体；修改密码只在顶栏账号菜单。
- 展示真实身份、当前项目、团队角色、今日学习时长。
- 五项统计：累计学习时长、本周学习时长、最长单次学习、当前连续天数、最长连续天数。
- 学习活动热力图支持每日/每周/累计；色块 hover 气泡显示具体日期和学习时长。
- 学习时长分布：课程学习、练习考试、路演训练、协作复盘。
- 展示个人和团队奖状预览；展示个人/团队整改说明和状态。

按钮与弹窗：

- 热力图切换每日/每周/累计。
- 点击奖状打开证书预览弹窗；支持后端生成 PDF 后下载（可作为第二阶段）。
- 点击整改打开说明弹窗：发布老师、发布日期、截止日期、原因、整改要求、状态、关联任务。
- “查看相关任务”跳到真实任务详情。

新增数据：统一学习会话表、奖状和接收对象表、整改和接收对象表。Profile 接口在服务端聚合，不从各页面 localStorage 累加时长。

### 5.13 选题策划

目标路由：`/training/topic`

- 现有 `project-prep` 已有真实 bootstrap、会话、方向选择、文档和生成任务能力，直接复用。
- 将当前“试用账号不开放”的原型壳替换为真实权限判断。
- 无权限显示明确原因和申请路径；有权限展示会话、方向、文档、生成任务。

### 5.14 不进入生产导航的原型页

- `map.html`：仅设计/架构说明，不进入学生产品。
- `teacher-camp.html`：属于教师端，不进入学生端。
- `training-course.html`：只作为旧链接重定向到 `/training/courses`。
- `collab.html`：若无独立业务内容，重定向到 `/collaboration/tasks`。

## 6. 数据库变更清单

### 6.1 直接复用

- 用户与租户：`users、tenant`
- 课程：`course、course_chapter、course_lesson、course_attachment、course_learning_progress`
- 考试：`exam_*`
- 会议与录制：`meeting、meeting_participant、meeting_recording、chat_message`
- 团队协作：`project_team、project_team_member、project_stage、project_task、project_task_assignee、project_task_submission、project_submission_asset、project_submission_link、project_material、project_review_issue`
- 评分：`score_*、ai_scoring_session、ai_score_report、ai_score_remediation_task、ai_score_evidence_*、ai_score_transcript_segment、ai_jury_*`
- PPT/讲稿：现有 PPT、Script、SlideScript 相关表。

### 6.2 新建

| 表 | 目的 | 关键字段 |
|---|---|---|
| `training_camp` | 集训营主记录 | tenant、name、start/end、total_days、status |
| `training_camp_week` | 周阶段及日期范围 | camp、week_no、title、start/end、sort |
| `training_camp_team` | 营与团队关系 | camp、team、joined_at、status |
| `training_day` | 每日训练编排 | camp、week、day_no、training_date、title、summary、due_at |
| `training_day_task` | 每日训练与真实项目任务关联 | day、task、is_primary、sort |
| `project_task_requirement` | 任务完成标准/交付清单 | task、title、required、asset_type、sort |
| `project_task_extension_request` | 延期申请 | task、requester、requested_due_at、reason、status、reviewer |
| `project_task_activity` | 任务动态审计 | task、actor、action、payload、created_at |
| `project_material_version` | 文件版本 | material、version_no、object_key、mime、size、note、uploader、is_current |
| `project_material_task_link` | 文件多任务关联 | material、task |
| `project_material_activity` | 文件操作记录 | material、version、actor、action、created_at |
| `course_lesson_note` | 学生课时笔记 | user、lesson、content、updated_at |
| `learning_activity_session` | 统一真实学习时长 | tenant、user、type、source_type/id、start/end、duration、heartbeat、dedupe_key |
| `notification` | 业务消息 | tenant、receiver、category、title、body、target_type/id/path、read_at |
| `team_invitation` | 团队邀请 | team、inviter、invitee/email、token、expires、status |
| `honor_award` | 奖状内容 | tenant、title、description、issuer、issued_at、related_type/id |
| `honor_award_recipient` | 个人/团队接收对象 | award、recipient_type、user/team |
| `correction_order` | 惩罚与整改说明 | tenant、title、reason、requirement、issuer、issued_at、due_at、related_task |
| `correction_order_recipient` | 个人/团队整改状态 | order、recipient_type、user/team、status、completed_at |

### 6.3 修改现有表

- `project_material` 增加 `current_version_id、archived_at`，现有文件回填 V1。
- `project_task_submission` 明确支持 DRAFT / PENDING_REVIEW / APPROVED / CHANGES_REQUESTED，并保留每次提交版本。
- `course_learning_progress` 保留课程汇总，精确时长改由 `learning_activity_session` 产生。
- 所有新表必须含 tenant 或通过可验证外键链归属 tenant；所有查询必须带租户与用户数据范围。

## 7. 后端接口清单

### 7.1 新增聚合接口

- `GET /api/student/bootstrap`
- `GET /api/student/home`
- `GET /api/student/search?q=&types=`
- `GET /api/student/profile/summary`
- `GET /api/student/profile/learning-activity?from=&to=&granularity=`
- `GET /api/student/profile/learning-distribution?from=&to=`
- `GET /api/student/profile/awards`
- `GET /api/student/profile/corrections`

### 7.2 训练营

- `GET /api/training-camps/current`
- `GET /api/training-camps/:campId/today`
- `GET /api/training-camps/:campId/plan`
- `GET /api/training-days/:dayId`
- `GET /api/training-submissions/:submissionId`
- `GET /api/training-submissions/:submissionId/feedback`
- 提交继续调用现有 `/api/project-teams/tasks/:taskId/submissions`。

### 7.3 任务、文件、消息、邀请与个人中心

- `POST /api/project-teams/tasks/:taskId/extension-requests`
- `GET /api/project-teams/tasks/:taskId/activities`
- `GET /api/project-materials`
- `GET /api/project-materials/:id`
- `POST /api/project-materials`
- `POST /api/project-materials/:id/versions`
- `PATCH /api/project-materials/:id/current-version`
- `PATCH /api/project-materials/:id/archive`
- `GET /api/notifications`
- `PATCH /api/notifications/:id/read`
- `POST /api/notifications/read-all`
- `GET /api/team-invitations/:token`
- `POST /api/team-invitations/:token/accept`
- `POST /api/team-invitations/:token/reject`
- `GET /api/awards/:id/certificate`
- `GET /api/corrections/:id`

### 7.4 稳固现有接口

- 考试增加作答恢复、逐题保存、标记、结果查询。
- 课程增加课时笔记和学习心跳。
- 会议增加 replay 聚合接口。
- AI 报告继续使用现有 session/report/evidence/jury/remediation 接口；只补统一错误码和字段契约。

## 8. 前端代码拆分

现有 `Dashboard.vue`、`ProjectTeam.vue` 等页面过大，不能继续在单文件里叠功能。按业务拆为：

```text
src/modules/student-shell/
src/modules/home/
src/modules/training/
src/modules/course/
src/modules/exam/
src/modules/roadshow/
src/modules/collaboration/
src/modules/review/
src/modules/profile/
src/shared/components/
src/shared/api/
src/shared/types/
```

- 页面组件只负责组合和路由状态。
- API 请求集中到模块 api 文件，不散落在模板组件。
- 服务端 DTO 与前端类型一一对应。
- 评分报告已有复杂呈现工具和测试，优先保留，替换外壳而不是重写算法。

## 9. 分批实施顺序（每批均为可演示闭环）

### 第 0 批：基础治理

- Flyway baseline 和新增迁移目录。
- 统一设计令牌、按钮、页面壳、弹窗层级、路由守卫和旧路由重定向。
- 定义 API 错误码、loading/empty/error 组件。
- 不改变核心业务功能。

### 第 1 批：首页 + 今日集训

- 新训练营表、训练营聚合接口。
- 首页真实聚合接口。
- 首页、今日集训、21 天计划、提交、反馈全部落地。
- 完成“看今日任务 → 提交 → 老师审核数据回显”的真实闭环。

### 第 2 批：课程 + 练习考试

- 课程列表/详情/播放器换壳，章节和学习时长真实化。
- 考试作答恢复、自动保存、结果页和错题闭环。
- 统一写入学习时长会话。

### 第 3 批：路演 + 回放 + PPT/讲稿

- 在线会议列表和弹窗换壳。
- 会议室保持成熟实时能力，修正沉浸布局。
- 回放视频 + 时间同步转录。
- PPT/讲稿只做外壳和路由整合，不重写生成链。

### 第 4 批：协作任务 + 文件中心

- 拆分现有 ProjectTeam 大页面。
- 任务列表、详情、延期、动态、提交验收。
- 文件主记录、版本、关联任务、预览、归档。

### 第 5 批：评分报告完整体系

- 报告列表、上传评分。
- 结果、评分项、待办、任务详情、证据、证据详情、评审团、评委详情、对比。
- 验证五维正式分、媒体、转录、证据和整改任务一致。

### 第 6 批：个人中心 + 消息 + 奖惩

- 真实学习活动和时长分布。
- 奖状预览、整改说明和关联任务。
- 顶栏消息、搜索、账号菜单完整闭环。

## 10. 验收标准

### 10.1 功能

- 原型中每个保留按钮都有真实跳转或接口；无演示 Toast。
- 刷新任一详情页，状态可从服务端恢复。
- 文件、考试答案、提交、审核、任务状态、奖状和整改全部持久化。
- 学生只能看到自己和所在团队被授权的数据。
- 任何删除、归档、交卷、结束会议、重新评分操作都有确认和幂等保护。

### 10.2 数据

- 页面可见数字 100% 可追溯到字段或服务端计算规则。
- 总分与五维之和遵循当前正式评分配置，不由前端重算。
- 学习时长采用服务端心跳去重，后台页或断线不继续累计。
- 热力图每个色块能显示具体日期与时长。
- “距离备赛结束”按服务端日期和时区计算。

### 10.3 视觉与交互

- 非首页页面顶部、左右间距均为 40px；标题、说明、页头间距统一。
- 主按钮全站使用主题橙；按钮字号、圆角、状态符合规范。
- 弹窗遮罩覆盖顶栏；键盘焦点锁在弹窗内；Esc 和关闭按钮行为一致。
- 1440、1280、1024 宽度无横向破版；沉浸页面单独验收。
- 页面不存在“逾期”字样，统一为“过期”。

### 10.4 测试

- 后端：新增 Service、Controller、权限、租户隔离、状态机和迁移测试。
- 前端：关键转换函数单测；Playwright 覆盖六条主链。
- 主链用例：登录 → 今日集训 → 提交 → 反馈；课程 → 完成课时；考试 → 自动保存 → 交卷；会议 → 回放；报告 → 改进任务；个人中心 → 奖状/整改。

## 11. 风险和取舍

1. **数据库迁移风险**：现有建表方式较分散。先 baseline 再新增 Flyway，会多花一批治理时间，但能避免后续环境表结构漂移。
2. **大页面拆分风险**：`ProjectTeam.vue` 已非常大。直接改样式最快但维护成本继续扩大；本方案选择模块拆分，初期速度略慢，后续教师端和学生端可复用业务层。
3. **“真实数据”与视觉丰满度冲突**：没有记录时页面会显得少。本方案坚持真实空状态，不用假数据填满卡片。
4. **统一学习时长准确性**：浏览器只能近似判断有效学习。首期用可见页 + 心跳 + 交互 + 服务端去重，明确它是“平台内有效学习时长”，不是绝对专注时间。
5. **评分报告复杂度**：评分链已有较多成熟代码。优先保留后端与转换工具，只重组信息架构；避免为了视觉重做破坏权威分和证据链。

## 12. 待确认的实施口径

本方案按以下假设编制：

- 高保真原型是视觉与交互基准，现有成品代码是业务逻辑和真实数据基准。
- 学生端一级导航采用当前最终顺序：复盘在协作之前。
- 选题策划继续保留，并接现有 Project Preparation 能力。
- 教师端暂不在本轮落代码，但学生提交、奖状、整改等数据结构会预留教师发布/审核权限。
- 批次实施按 0 → 6 顺序；每批验收后再进入下一批，不进行一次性大爆改。

确认本方案后，第一步不是直接改首页 CSS，而是先完成第 0 批和第 1 批的数据契约、迁移脚本、接口测试，再把高保真首页与今日集训接上真实数据。
