# OREP 教学成长与竞赛拔尖双轮驱动研发需求版

> 文档版本：V4.4-RD  
> 日期：2026-06-06  
> 目标读者：研发、产品、测试、交付  
> 当前系统基础：Vue 用户端 + Spring Boot 后端 + MySQL + 已有会议、评分、问题、录制、PPT、讲稿、AI 评分分析模块  
> 研发目标：在不推翻现有 OREP 的前提下，新增“课程化 AI 练习、能力画像、问题分流、竞赛候选、竞赛训练闭环、学校驾驶舱”能力。

---

## 1. 研发总目标

OREP V4.4 不重做一个新系统，而是在现有系统上升级为：

> **教学成长 + 竞赛拔尖双轮驱动平台。**

研发上要跑通两条主链路：

```text
教学成长轮：
教学大纲 → AI 练习 → 能力事件 → 能力画像 → 班级报告 → 补练任务

竞赛拔尖轮：
能力画像 → 候选推荐 → 训练计划 → PPT/讲稿/模拟展示 → 会后复盘 → 整改任务
```

并新增一个关键中枢：

```text
问题分流机制：
AI练习 / PPT / 讲稿 / 会议评分 / 会后复盘
→ issue_event
→ 问题归因
→ 老师审核
→ 全班补练 / 候选专项 / 队伍整改 / 忽略
```

---

## 2. 当前系统现状

### 2.1 已有前端页面

| 页面文件 | 当前定位 | 本次处理方式 |
|---|---|---|
| `frontend/user/src/App.vue` | 顶部导航 HOME/MEET/REC/DATA、用户菜单 | 增加角色化入口，不大改导航结构 |
| `frontend/user/src/views/Dashboard.vue` | 首页任务台，已有会议、PPT、讲稿、数据入口 | 改为“分层工作台” |
| `frontend/user/src/views/OnlineMeeting.vue` | 加入会议、创建会议、参与记录 | 增加会议类型、关联训练计划/项目 |
| `frontend/user/src/views/MeetingRoom.vue` | 会中会议室、评分、问题、录制 | 保持会中纯净，仅增加会议类型上下文 |
| `frontend/user/src/views/MyRecordings.vue` | 我的录制 | 增加会后复盘证据与整改入口 |
| `frontend/user/src/views/Statistics.vue` | 路演复盘中心、评分趋势、问题排行 | 改造为角色化数据分析页 |
| `frontend/user/src/views/Profile.vue` | 账号资料和修改密码 | 保留账号中心，不承载能力画像 |
| `frontend/user/src/views/AiScoreResult.vue` | AI 路演评分分析台 | 增加“生成问题事件/整改任务”出口 |
| `frontend/user/src/views/PptEditor.vue` | AI PPT 生成/编辑 | 增加竞赛训练项目绑定、材料问题输出 |
| `frontend/user/src/views/ScriptList.vue` / `ScriptEditor.vue` | 讲稿列表和编辑 | 增加训练计划绑定、讲稿问题输出 |

### 2.2 已有前端路由

当前路由文件：`frontend/user/src/router/index.js`

已有核心路由：

```text
/                       Dashboard
/online-meeting          OnlineMeeting
/meeting/:id             MeetingRoom
/meeting-history/:id     MeetingHistoryDetail
/score-result/:meetingId ScoreResult
/ai-score/:meetingId     AiScoreResult
/statistics              Statistics
/profile                 Profile
/script-editor           ScriptList
/script-editor/detail/:scriptId ScriptEditor
/ppt-editor              PptEditor
/ppt-history/:id         PptHistoryDetail
/my-recordings           MyRecordings
```

### 2.3 已有后端模块

| 后端文件 | 当前能力 | 本次处理方式 |
|---|---|---|
| `MeetingController` / `MeetingService` | 创建、加入、结束会议、会议历史 | 增加会议类型、训练计划关联 |
| `IssueController` / `IssueService` | 会议问题跟踪、问题 PDF | 保留 `issue`，新增 `issue_event` 做问题分流 |
| `StatisticsController` / `StatisticsService` | 路演评分统计 | 增加能力画像、班级、学校统计接口 |
| `AiChatController` | 会议 AI 复盘问答记录 | 新增课程练习型 AI 对话，不再只依赖 meeting |
| `AiScoreController` | AI 评分报告 | 增加生成 `ability_event` / `issue_event` 的任务 |
| `PptScriptPageController` / `PptScriptPageService` | PPT 每页讲稿持久化 | 增加训练计划/问题事件关联 |
| `RecordingController` | 录制列表、录制文件 | 作为会后复盘证据来源 |

### 2.4 已有数据库表

已有核心表：

```text
tenant
users
meeting
meeting_participant
meeting_recording
score_template
score_item
score_record
score_detail
issue
chat_message
ai_chat_session
ai_chat_message
ppt_task
ppt_questionnaire
ppt_html_page
ppt_generation_snapshot
ppt_page_quality_report
ppt_scoring_coverage
ppt_script_page
```

本次研发不删除已有表，采用新增表 + 少量字段扩展。

---

## 3. 新增前端路由与页面

### 3.1 新增路由

修改文件：`frontend/user/src/router/index.js`

新增路由：

```js
{
  path: '/practice',
  name: 'PracticeTaskList',
  component: () => import('../views/PracticeTaskList.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/practice/:taskId',
  name: 'PracticeSession',
  component: () => import('../views/PracticeSession.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/ability-profile',
  name: 'AbilityProfile',
  component: () => import('../views/AbilityProfile.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/teacher-workbench',
  name: 'TeacherWorkbench',
  component: () => import('../views/TeacherWorkbench.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/issue-center',
  name: 'IssueEventCenter',
  component: () => import('../views/IssueEventCenter.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/competition',
  name: 'CompetitionWorkbench',
  component: () => import('../views/CompetitionWorkbench.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/school-dashboard',
  name: 'SchoolDashboard',
  component: () => import('../views/SchoolDashboard.vue'),
  meta: { requiresAuth: true }
}
```

### 3.2 顶部导航处理

修改文件：`frontend/user/src/App.vue`

不建议把顶部导航改得过重。第一版保留：

```text
HOME / MEET / REC / DATA
```

新增页面通过 Dashboard 模块卡、Statistics 页 Tab、用户菜单进入。

用户菜单增加：

```text
个人中心
能力画像
教师工作台（仅老师/管理员显示）
学校驾驶舱（仅 SCHOOL_ADMIN/ADMIN 显示）
AI PPT生成
退出登录
```

---

## 4. 页面研发需求

## 4.1 Dashboard.vue 改造：分层工作台

### 4.1.1 文件

修改：

```text
frontend/user/src/views/Dashboard.vue
```

新增接口调用：

```text
GET /api/dashboard/workbench
```

### 4.1.2 页面目标

把现有首页从“会议/PPT/讲稿/数据入口”升级为“按用户身份动态显示今天最重要的任务”。

### 4.1.3 用户状态

后端返回：

```json
{
  "role": "STUDENT",
  "studentStage": "NORMAL",
  "mainTask": {},
  "metrics": [],
  "modules": [],
  "todoList": [],
  "quickActions": []
}
```

`studentStage` 枚举：

```text
NORMAL          普通学生
CANDIDATE       竞赛候选
TEAM_MEMBER     参赛队员
TEAM_LEADER     队长/主讲
TEACHER         老师
SCHOOL_ADMIN    学校管理员
```

### 4.1.4 布局草图

```text
┌─────────────────────────────────────────────────────────────┐
│ OREP Header: HOME | MEET | REC | DATA | User                │
├─────────────────────────────────────────────────────────────┤
│ Mission Hero                         │ System Status        │
│ - 问候语/角色状态                    │ - 今日状态           │
│ - 当前主任务说明                     │ - 画像/练习/竞赛     │
│ [主按钮] [次按钮]                    │                      │
├─────────────────────────────────────────────────────────────┤
│ Telemetry Strip: 今日任务 | 能力变化 | 候选状态 | 待处理     │
├─────────────────────────────────────────────────────────────┤
│ Core Modules                                                │
│ ┌────────┬────────┬────────┬────────┐                      │
│ │模块 01 │模块 02 │模块 03 │模块 04 │                      │
│ └────────┴────────┴────────┴────────┘                      │
├─────────────────────────────────────────────────────────────┤
│ 左：今日任务/最近参与/训练任务       │ 右：快捷操作          │
└─────────────────────────────────────────────────────────────┘
```

### 4.1.5 普通学生展示内容

Hero：

```text
标题：晚上好，小明
说明：完成今日课程练习，查看能力变化和补练建议。
主按钮：开始今日练习 → /practice/{taskId}
次按钮：查看能力画像 → /ability-profile
```

Telemetry：

```text
今日练习：1
连续练习：6 天
综合能力：78
待补练：3
```

Modules：

```text
01 今日 AI 练习 → /practice
02 能力画像 → /ability-profile
03 补练任务 → /practice?tab=remedial
04 参赛成长路径 → /ability-profile?tab=competition
```

### 4.1.6 候选学生展示内容

Hero：

```text
标题：候选赛道：新一代信息技术
说明：推荐分 86，距离入队还差表达 +5、应用 +4。
主按钮：开始专项补练
次按钮：查看推荐理由
```

Modules：

```text
01 入队差距
02 专项补练
03 候选观察报告
04 展示讲解基础训练
```

### 4.1.7 参赛学生展示内容

Hero：

```text
标题：智造领航队训练中
说明：下一场模拟展示 6月12日 19:30，PPT 第 8 页待优化。
主按钮：进入模拟展示会议 → /meeting/{id}
次按钮：查看训练任务 → /competition
```

Modules：

```text
01 模拟展示会议
02 AI PPT生成
03 讲稿编辑
04 会后复盘
```

### 4.1.8 老师展示内容

Hero：

```text
标题：软件 24-1 班今日概览
说明：完成率 32/45，高频卡点 3 个，新增候选 2 人。
主按钮：查看班级报告 → /teacher-workbench
次按钮：审核回流建议 → /issue-center
```

Modules：

```text
01 教学大纲
02 班级报告
03 问题回流审核
04 候选推荐
```

### 4.1.9 代码修改点

```text
Dashboard.vue
- 保留现有 Mission Control 样式。
- features 改为由接口返回，不再写死会议/PPT/讲稿/数据。
- quickActions 改为由接口返回。
- recentHistory 保留，但对参赛学生改名为“最近训练”。
- 增加 studentStage 判断。
- 增加 routeAction(action) 统一跳转函数。
```

新增类型建议：

```text
frontend/user/src/constants/workbench.js
frontend/user/src/utils/roleStage.js
```

---

## 4.2 PracticeTaskList.vue：课程练习列表

### 4.2.1 文件

新增：

```text
frontend/user/src/views/PracticeTaskList.vue
```

### 4.2.2 页面目标

展示学生当前课程练习、补练任务、候选专项训练。

### 4.2.3 布局草图

```text
┌────────────────────────────────────────────┐
│ Hero: AI PRACTICE / 课程 AI 练习            │
│ 说明：围绕课程知识点完成能力检测和补练       │
├────────────────────────────────────────────┤
│ Tabs: 今日练习 | 补练任务 | 候选专项 | 已完成 │
├────────────────────────────────────────────┤
│ 任务卡片列表                                │
│ ┌────────────────────────────────────────┐ │
│ │ 数据库应用开发 · 查询优化               │ │
│ │ 预计 8min · 关联能力：专业/应用         │ │
│ │ 状态：待完成      [开始练习]            │ │
│ └────────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

### 4.2.4 接口

```text
GET /api/practice/tasks?tab=today
GET /api/practice/tasks?tab=remedial
GET /api/practice/tasks?tab=candidate
```

返回：

```json
{
  "list": [
    {
      "id": 1001,
      "taskType": "COURSE",
      "courseName": "数据库应用开发",
      "knowledgePointTitle": "查询优化",
      "estimatedMinutes": 8,
      "abilityDimensions": ["PROFESSIONAL", "APPLICATION"],
      "status": "NOT_STARTED",
      "dueAt": "2026-06-10T23:59:59"
    }
  ]
}
```

---

## 4.3 PracticeSession.vue：课程化 AI 对话练习

### 4.3.1 文件

新增：

```text
frontend/user/src/views/PracticeSession.vue
```

### 4.3.2 页面目标

不是普通聊天页，而是课程化练习页。每次练习都要产出：

```text
dialogue_practice
dialogue_detail
ability_event
issue_event
student_ability_profile 更新
```

### 4.3.3 布局草图

```text
┌─────────────────────────────────────────────────────────────┐
│ AI PRACTICE · 数据库应用开发 / 查询优化                      │
├───────────────┬───────────────────────────┬─────────────────┤
│ 左：课程上下文 │ 中：AI 对话区              │ 右：实时反馈     │
│ - 课程         │ AI：事实层问题             │ - 当前得分 82    │
│ - 教学周       │ 学生：回答                 │ - 专业 +2.1      │
│ - 知识点       │ AI：推理追问               │ - 应用 +1.4      │
│ - 关联能力     │ 学生：回答                 │ - 卡点列表       │
│ - 练习层级     │ [输入框] [发送] [下一题]    │ - 下一步补练     │
└───────────────┴───────────────────────────┴─────────────────┘
```

### 4.3.4 对话层级

每个任务至少包含：

```text
FACT        事实层：概念、定义、基础操作
REASONING   推理层：为什么、条件变化、原理解释
APPLICATION 应用层：放到岗位任务或项目场景中
REFLECTION  复盘层：指出自己刚才回答的不足和改进
```

### 4.3.5 接口

开始练习：

```text
POST /api/practice/{taskId}/start
```

返回：

```json
{
  "practiceId": 2001,
  "taskId": 1001,
  "currentLayer": "FACT",
  "question": "什么是 B+ 树索引？请用一句话说明它为什么适合查询。",
  "context": {
    "courseName": "数据库应用开发",
    "knowledgePointTitle": "查询优化"
  }
}
```

提交回答：

```text
POST /api/practice/{practiceId}/answer
```

请求：

```json
{
  "questionId": "q_001",
  "answerText": "B+ 树把数据按顺序组织在叶子节点...",
  "durationSeconds": 42
}
```

返回：

```json
{
  "detailId": 3001,
  "score": 82,
  "layer": "FACT",
  "feedback": "概念基本准确，但缺少范围查询解释。",
  "abilityDelta": [
    { "dimension": "PROFESSIONAL", "delta": 2.1 },
    { "dimension": "APPLICATION", "delta": 1.4 }
  ],
  "issues": [
    {
      "issueType": "JOB_SKILL",
      "description": "索引适用场景解释不完整",
      "suggestedAudience": "CLASS"
    }
  ],
  "nextQuestion": "如果条件是 LIKE '%三'，索引还能稳定命中吗？为什么？"
}
```

结束练习：

```text
POST /api/practice/{practiceId}/finish
```

返回：

```json
{
  "finalScore": 82,
  "summary": "本次练习暴露慢查询排查步骤不完整。",
  "profileUpdated": true,
  "nextTasks": []
}
```

### 4.3.6 代码修改点

新增前端：

```text
PracticeSession.vue
frontend/user/src/api/practice.js
frontend/user/src/components/practice/PracticeContextPanel.vue
frontend/user/src/components/practice/PracticeDialoguePanel.vue
frontend/user/src/components/practice/PracticeFeedbackPanel.vue
```

新增后端：

```text
PracticeController
PracticeService
PracticeTaskMapper
DialoguePracticeMapper
DialogueDetailMapper
AbilityEventMapper
IssueEventMapper
```

---

## 4.4 AbilityProfile.vue：能力画像页

### 4.4.1 文件

新增：

```text
frontend/user/src/views/AbilityProfile.vue
```

保留：

```text
frontend/user/src/views/Profile.vue
```

说明：`Profile.vue` 继续做账号资料和密码管理，不要把账号中心强行改成能力画像。

### 4.4.2 布局草图

```text
┌─────────────────────────────────────────────────────────┐
│ Hero: 学生成长档案                                      │
│ 综合能力 78 | 本周 +3 | 班级位置 12/45                  │
├───────────────────┬─────────────────────────────────────┤
│ 左：能力雷达       │ 右：能力解释                         │
│ 专业 88            │ 专业能力为什么是 88？                 │
│ 应用 72            │ - AI练习 4 次稳定高分                 │
│ 表达 76            │ - 慢查询解释仍不完整                  │
├───────────────────┴─────────────────────────────────────┤
│ Tabs: 证据来源 | 短板卡点 | 成长建议 | 竞赛潜力          │
│ - 来自 AI练习、补练、PPT、讲稿、会议、复盘               │
└─────────────────────────────────────────────────────────┘
```

### 4.4.3 接口

```text
GET /api/ability-profile/me
GET /api/ability-profile/student/{studentId}
GET /api/ability-profile/student/{studentId}/evidence
GET /api/ability-profile/student/{studentId}/competition-fit
```

### 4.4.4 返回结构

```json
{
  "studentId": 12,
  "overallScore": 78,
  "trendDelta": 3,
  "classRank": 12,
  "classSize": 45,
  "dimensions": [
    {
      "dimension": "PROFESSIONAL",
      "score": 88,
      "trend": 2.1,
      "explanation": "索引原理和接口部署回答稳定。",
      "evidenceCount": 14
    }
  ],
  "weaknesses": [],
  "suggestions": [],
  "competitionFit": {
    "track": "新一代信息技术",
    "fitScore": 86,
    "gap": [
      { "dimension": "EXPRESSION", "need": 5 },
      { "dimension": "APPLICATION", "need": 4 }
    ]
  }
}
```

---

## 4.5 TeacherWorkbench.vue：教师工作台

### 4.5.1 文件

新增：

```text
frontend/user/src/views/TeacherWorkbench.vue
```

### 4.5.2 布局草图

```text
┌─────────────────────────────────────────────────────────────┐
│ 教师工作台 · 软件 24-1 班                                   │
├─────────────────────────────────────────────────────────────┤
│ 今日概览：完成率 32/45 | 平均分 78 | 卡点 3 | 预警 5 | 候选 2 │
├─────────────────────────────────────────────────────────────┤
│ Tabs: 今日 | 本周 | 能力 | 预警 | 竞赛潜力 | 教学建议         │
├───────────────────────────────┬─────────────────────────────┤
│ 左：班级报告                   │ 右：待处理                  │
│ - 完成率趋势                   │ - 7 名学生未完成            │
│ - 高频卡点排行                 │ - 3 名学生连续下降          │
│ - 能力分布                     │ - 2 名学生建议进入观察池    │
└───────────────────────────────┴─────────────────────────────┘
```

### 4.5.3 功能

| 功能 | 说明 |
|---|---|
| 教学大纲入口 | 创建/导入/AI 生成知识点 |
| 班级报告 | 完成率、平均分、卡点、能力分布 |
| 学生预警 | 未练习、连续下降、卡点重复 |
| 候选推荐 | 查看推荐学生和证据 |
| 回流审核入口 | 进入问题事件中心 |

### 4.5.4 接口

```text
GET /api/teacher/dashboard?classId=101
GET /api/teacher/classes
GET /api/teacher/class/{classId}/report?range=today|week|month
GET /api/teacher/class/{classId}/warnings
GET /api/teacher/class/{classId}/candidate-recommendations
```

---

## 4.6 IssueEventCenter.vue：问题事件中心

### 4.6.1 文件

新增：

```text
frontend/user/src/views/IssueEventCenter.vue
```

### 4.6.2 和现有 `issue` 的关系

当前已有表 `issue` 是会议问题跟踪，字段较少，主要服务：

```text
meeting_id
score_detail_id
category
description
status
resolved_meeting_id
```

新增 `issue_event` 不替代 `issue`，而是做能力画像体系下的问题分流。

关系：

```text
issue              会议问题原始记录
issue_event        结构化问题事件，用于归因、分流、教学回流
```

可从 `issue` 生成 `issue_event`：

```text
issue.id → issue_event.source_type = MEETING_ISSUE
issue.id → issue_event.source_id
```

### 4.6.3 布局草图

```text
┌────────────────────────────────────────────────────────────┐
│ 问题事件中心                                                │
│ 说明：审核哪些问题进入课堂、候选专项或队伍整改              │
├────────────────────────────────────────────────────────────┤
│ 筛选：班级 | 课程 | 来源 | 问题类型 | 建议人群 | 状态       │
├────────────────────────────────────────────────────────────┤
│ Tabs: 待审核 | 可回流课堂 | 项目化素养 | 候选专项 | 队伍整改 │
├───────────────────────┬────────────────────────────────────┤
│ 左：问题列表           │ 右：问题详情                         │
│ - 问题描述             │ - 来源证据                           │
│ - 来源                 │ - 关联课程/知识点/能力                │
│ - 建议人群             │ - 系统建议                           │
│ - 置信度               │ [全班补练] [候选专项] [队伍整改] [忽略]│
└───────────────────────┴────────────────────────────────────┘
```

### 4.6.4 问题类型枚举

```text
JOB_SKILL           岗位技能问题
JOB_TASK_UNDERSTAND 岗位任务理解问题
COMPETITION_DISPLAY 竞赛展示问题
TEAM_COLLABORATION  团队协作问题
MATERIAL_STANDARD   材料规范问题
```

### 4.6.5 适用人群枚举

```text
CLASS
PARTIAL_STUDENTS
CANDIDATE
TEAM
TEAM_LEADER
TEACHER_ONLY
IGNORE
```

### 4.6.6 状态枚举

```text
PENDING_REVIEW
APPROVED_CLASS
APPROVED_CANDIDATE
APPROVED_TEAM
IGNORED
CONVERTED_TASK
```

### 4.6.7 接口

```text
GET /api/issue-events
GET /api/issue-events/{id}
POST /api/issue-events/{id}/review
POST /api/issue-events/{id}/convert-remedial-task
POST /api/issue-events/{id}/convert-training-task
```

审核请求：

```json
{
  "decision": "APPROVED_CLASS",
  "targetClassId": 101,
  "note": "下节课作为索引优化补练",
  "dueAt": "2026-06-12T23:59:59"
}
```

---

## 4.7 CompetitionWorkbench.vue：竞赛训练工作台

### 4.7.1 文件

新增：

```text
frontend/user/src/views/CompetitionWorkbench.vue
```

### 4.7.2 页面目标

服务候选学生、参赛学生、队长和指导老师。  
把现有 PPT、讲稿、会议室、录制、AI 评分串成训练闭环。

### 4.7.3 布局草图

```text
┌──────────────────────────────────────────────────────────────┐
│ 竞赛训练工作台 · 智造领航队                                  │
│ 赛道：新一代信息技术 | 训练完成率 68% | 下一场 6月12日 19:30 │
├──────────────────────────────────────────────────────────────┤
│ Tabs: 项目空间 | 材料准备 | 模拟展示 | 会后复盘 | 整改任务    │
├───────────────────────────────┬──────────────────────────────┤
│ 左：项目/队伍信息              │ 右：本周训练任务             │
│ - 项目名称                     │ - 修改 PPT 第 8 页           │
│ - 队员分工                     │ - 补充讲稿应用价值段         │
│ - 老师                         │ - 创建模拟展示会议           │
├──────────────────────────────────────────────────────────────┤
│ 材料区：PPT版本 | 讲稿版本 | 材料问题 | 评分点覆盖           │
├──────────────────────────────────────────────────────────────┤
│ 训练区：会议记录 | 录制 | 评分 | 复盘 | 下一轮整改           │
└──────────────────────────────────────────────────────────────┘
```

### 4.7.4 和现有功能联动

| 现有功能 | 联动方式 |
|---|---|
| `PptEditor.vue` | 从训练工作台进入时带 `trainingPlanId/projectId` |
| `ScriptEditor.vue` | 讲稿绑定项目、PPT task、训练计划 |
| `OnlineMeeting.vue` | 创建会议时可选会议类型 `SIMULATION_DISPLAY` |
| `MeetingRoom.vue` | 会中只显示会议和评分，不显示 AI 干扰 |
| `AiScoreResult.vue` | 会后生成问题事件和整改任务 |
| `MyRecordings.vue` | 录制作为复盘证据 |

### 4.7.5 接口

```text
GET /api/competition/workbench
GET /api/competition/projects/{projectId}
POST /api/competition/projects
POST /api/competition/projects/{projectId}/members
GET /api/competition/training-plans/{planId}
POST /api/competition/training-plans
POST /api/competition/training-tasks
PATCH /api/competition/training-tasks/{taskId}
```

---

## 4.8 OnlineMeeting.vue 改造：会议类型与训练关联

### 4.8.1 文件

修改：

```text
frontend/user/src/views/OnlineMeeting.vue
backend/src/main/java/com/orep/backend/dto/CreateMeetingRequest.java
backend/src/main/java/com/orep/backend/entity/Meeting.java
backend/src/main/java/com/orep/backend/service/MeetingService.java
backend/src/main/java/com/orep/backend/controller/MeetingController.java
```

### 4.8.2 新增字段

`meeting` 表增加：

```sql
ALTER TABLE meeting
  ADD COLUMN meeting_type VARCHAR(32) NOT NULL DEFAULT 'NORMAL' COMMENT 'NORMAL/SIMULATION_DISPLAY/FORMAL_REVIEW/REVIEW_MEETING',
  ADD COLUMN project_id BIGINT NULL COMMENT '关联竞赛项目',
  ADD COLUMN training_plan_id BIGINT NULL COMMENT '关联训练计划',
  ADD COLUMN course_id BIGINT NULL COMMENT '关联课程',
  ADD COLUMN track_code VARCHAR(64) NULL COMMENT '赛道编码';
```

### 4.8.3 创建会议表单增加

```text
会议类型：
- 普通会议
- 模拟展示
- 复盘会议

关联对象：
- 竞赛项目
- 训练计划
- 课程
```

布局草图：

```text
创建会议室
┌────────────────────────┐
│ 会议标题               │
│ 会议类型 [普通会议 v]  │
│ 关联项目 [可选 v]      │
│ 预计时长               │
│ [创建会议室]           │
└────────────────────────┘
```

### 4.8.4 会中要求

`MeetingRoom.vue` 不增加 AI Sidecar，不增加会中弹窗。

只在顶部或侧栏显示：

```text
会议类型：模拟展示
关联项目：智造领航
训练计划：第 3 轮模拟展示
```

---

## 4.9 AiScoreResult.vue 改造：复盘到问题事件

### 4.9.1 文件

修改：

```text
frontend/user/src/views/AiScoreResult.vue
backend/src/main/java/com/orep/backend/controller/AiScoreController.java
backend/src/main/java/com/orep/backend/service/ScoreService.java 或新增 ReviewEventService
```

### 4.9.2 页面新增区块

在评分分析台概览或结论区增加：

```text
问题事件生成结果
- 可回流课堂：2
- 候选专项：1
- 队伍整改：4
- 忽略建议：1

[查看问题事件中心]
[生成整改任务]
```

### 4.9.3 布局草图

```text
AI 路演评分分析台
┌───────────────┬────────────────────────────┐
│ 综合评分/雷达  │ 当前证据                    │
├───────────────┴────────────────────────────┤
│ 问题事件生成                                │
│ 可回流课堂 2 | 候选专项 1 | 队伍整改 4      │
│ [查看问题事件中心] [生成整改任务]           │
└────────────────────────────────────────────┘
```

### 4.9.4 接口

```text
POST /api/ai-score/{meetingId}/generate-events
GET /api/ai-score/{meetingId}/event-summary
```

---

## 4.10 Statistics.vue 改造：角色化数据分析

### 4.10.1 文件

修改：

```text
frontend/user/src/views/Statistics.vue
backend/src/main/java/com/orep/backend/controller/StatisticsController.java
backend/src/main/java/com/orep/backend/service/StatisticsService.java
backend/src/main/java/com/orep/backend/dto/StatisticsVO.java
```

### 4.10.2 页面目标

当前 `Statistics.vue` 是“路演复盘中心”。V4.4 改为角色化数据页：

| 角色 | 默认视图 |
|---|---|
| 学生 | 我的能力画像摘要、练习趋势、补练完成 |
| 老师 | 班级报告、卡点、预警、候选 |
| 学校管理员 | 学校驾驶舱、专业对比、竞赛储备 |
| 参赛学生 | 训练趋势、复盘问题、整改闭环 |

### 4.10.3 Tabs

```text
个人成长
班级报告
问题卡点
竞赛储备
训练成果
学校概览
```

权限控制：

```text
STUDENT：个人成长、训练成果
TEACHER：班级报告、问题卡点、竞赛储备、训练成果
SCHOOL_ADMIN/ADMIN：全部
```

---

## 4.11 SchoolDashboard.vue：学校驾驶舱

### 4.11.1 文件

新增：

```text
frontend/user/src/views/SchoolDashboard.vue
```

### 4.11.2 布局草图

```text
┌────────────────────────────────────────────────────────────┐
│ 学校驾驶舱                                                  │
│ 覆盖学生 1286 | 活跃率 72% | 候选学生 42 | 训练队伍 6       │
├────────────────────────────────────────────────────────────┤
│ 专业对比：软件技术 82 | 人工智能 80 | 智能制造 77           │
├──────────────────────────────┬─────────────────────────────┤
│ 教学质量                      │ 竞赛储备                    │
│ - 高频卡点                    │ - 候选学生                  │
│ - 课程改进建议                │ - 候选队伍                  │
├──────────────────────────────┴─────────────────────────────┤
│ 报告导出：班级周报 | 专业报告 | 竞赛训练报告 | 学期报告      │
└────────────────────────────────────────────────────────────┘
```

### 4.11.3 接口

```text
GET /api/school-dashboard/overview
GET /api/school-dashboard/major-comparison
GET /api/school-dashboard/competition-reserve
POST /api/report-export
```

---

## 5. 新增数据库表

新增 SQL 文件：

```text
sql/ability_growth_tables.sql
deploy/sql/ability_growth_tables.sql
backend/src/main/resources/sql/ability_growth_tables.sql
```

### 5.1 教学大纲表：`teaching_outline`

```sql
CREATE TABLE IF NOT EXISTS teaching_outline (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  teacher_id BIGINT NOT NULL,
  class_id BIGINT NULL,
  course_name VARCHAR(128) NOT NULL,
  teaching_week INT NULL,
  lesson_date DATE NULL,
  knowledge_point_title VARCHAR(255) NOT NULL,
  knowledge_point_desc TEXT NULL,
  difficulty VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
  ability_dimensions JSON NULL,
  job_skill_tags JSON NULL,
  competition_related TINYINT(1) NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_tenant_teacher (tenant_id, teacher_id),
  KEY idx_class_course (class_id, course_name),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教学大纲/知识点表';
```

### 5.2 练习任务表：`practice_task`

```sql
CREATE TABLE IF NOT EXISTS practice_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  outline_id BIGINT NULL,
  creator_id BIGINT NOT NULL,
  target_type VARCHAR(32) NOT NULL COMMENT 'CLASS/STUDENT/CANDIDATE/TEAM',
  target_id BIGINT NULL,
  task_type VARCHAR(32) NOT NULL COMMENT 'COURSE/REMEDIAL/CANDIDATE/TRAINING_SELF_CHECK',
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  course_name VARCHAR(128) NULL,
  knowledge_point_title VARCHAR(255) NULL,
  ability_dimensions JSON NULL,
  estimated_minutes INT NOT NULL DEFAULT 8,
  status VARCHAR(32) NOT NULL DEFAULT 'PUBLISHED',
  due_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_tenant_type (tenant_id, task_type),
  KEY idx_target (target_type, target_id),
  KEY idx_outline (outline_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI练习/补练任务表';
```

### 5.3 对话练习主表：`dialogue_practice`

```sql
CREATE TABLE IF NOT EXISTS dialogue_practice (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  task_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'IN_PROGRESS',
  final_score DECIMAL(5,2) NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  summary TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_task_student (task_id, student_id),
  KEY idx_student_time (student_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI对话练习主记录';
```

### 5.4 对话明细表：`dialogue_detail`

```sql
CREATE TABLE IF NOT EXISTS dialogue_detail (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  practice_id BIGINT NOT NULL,
  layer VARCHAR(32) NOT NULL COMMENT 'FACT/REASONING/APPLICATION/REFLECTION',
  question_text TEXT NOT NULL,
  answer_text TEXT NULL,
  answer_duration_seconds INT NULL,
  score DECIMAL(5,2) NULL,
  score_detail JSON NULL,
  feedback TEXT NULL,
  template_risk_score DECIMAL(5,2) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_practice (practice_id),
  KEY idx_layer (layer)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI对话练习单题明细';
```

### 5.5 能力事件表：`ability_event`

```sql
CREATE TABLE IF NOT EXISTS ability_event (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  source_type VARCHAR(32) NOT NULL COMMENT 'AI_PRACTICE/PPT/SCRIPT/MEETING_SCORE/REVIEW',
  source_id BIGINT NOT NULL,
  dimension VARCHAR(32) NOT NULL COMMENT 'PROFESSIONAL/APPLICATION/EXPRESSION/LEARNING/REVIEW/COLLABORATION/STABILITY',
  score DECIMAL(5,2) NOT NULL,
  delta DECIMAL(5,2) NULL,
  confidence DECIMAL(5,2) NOT NULL DEFAULT 0.80,
  evidence TEXT NULL,
  evidence_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_student_dimension (student_id, dimension),
  KEY idx_source (source_type, source_id),
  KEY idx_tenant_time (tenant_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='能力画像事件表';
```

### 5.6 问题事件表：`issue_event`

```sql
CREATE TABLE IF NOT EXISTS issue_event (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  student_id BIGINT NULL,
  class_id BIGINT NULL,
  team_id BIGINT NULL,
  source_type VARCHAR(32) NOT NULL COMMENT 'AI_PRACTICE/MEETING_ISSUE/PPT/SCRIPT/AI_SCORE/RECORDING_REVIEW',
  source_id BIGINT NOT NULL,
  issue_type VARCHAR(64) NOT NULL COMMENT 'JOB_SKILL/JOB_TASK_UNDERSTAND/COMPETITION_DISPLAY/TEAM_COLLABORATION/MATERIAL_STANDARD',
  description TEXT NOT NULL,
  related_course VARCHAR(128) NULL,
  related_knowledge_point VARCHAR(255) NULL,
  ability_dimensions JSON NULL,
  suggested_audience VARCHAR(32) NOT NULL DEFAULT 'TEACHER_ONLY',
  suggested_action VARCHAR(64) NULL,
  confidence DECIMAL(5,2) NOT NULL DEFAULT 0.80,
  evidence_json JSON NULL,
  review_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME NULL,
  review_note TEXT NULL,
  converted_task_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_tenant_status (tenant_id, review_status),
  KEY idx_student (student_id),
  KEY idx_class (class_id),
  KEY idx_team (team_id),
  KEY idx_source (source_type, source_id),
  KEY idx_issue_type (issue_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问题事件与分流表';
```

### 5.7 学生能力画像表：`student_ability_profile`

```sql
CREATE TABLE IF NOT EXISTS student_ability_profile (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  overall_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  professional_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  application_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  expression_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  learning_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  review_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  collaboration_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  stability_score DECIMAL(5,2) NOT NULL DEFAULT 0,
  profile_json JSON NULL,
  evidence_summary JSON NULL,
  last_event_at DATETIME NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_student (student_id),
  KEY idx_tenant_score (tenant_id, overall_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生能力画像汇总表';
```

### 5.8 补练任务记录表：`remedial_task`

```sql
CREATE TABLE IF NOT EXISTS remedial_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  issue_event_id BIGINT NULL,
  practice_task_id BIGINT NULL,
  assigner_id BIGINT NOT NULL,
  target_type VARCHAR(32) NOT NULL COMMENT 'CLASS/STUDENT/CANDIDATE/TEAM',
  target_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PUBLISHED',
  due_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_issue_event (issue_event_id),
  KEY idx_target (target_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='补练任务表';
```

### 5.9 竞赛项目表：`competition_project`

```sql
CREATE TABLE IF NOT EXISTS competition_project (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  name VARCHAR(255) NOT NULL,
  track_code VARCHAR(64) NULL,
  track_name VARCHAR(128) NULL,
  teacher_id BIGINT NOT NULL,
  team_name VARCHAR(128) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PREPARING',
  ppt_task_id BIGINT NULL,
  script_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_tenant_status (tenant_id, status),
  KEY idx_teacher (teacher_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='竞赛项目/队伍空间表';
```

### 5.10 竞赛项目成员表：`competition_project_member`

```sql
CREATE TABLE IF NOT EXISTS competition_project_member (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  member_role VARCHAR(32) NOT NULL COMMENT 'LEADER/SPEAKER/TECH/DEMO/BACKUP',
  responsibility VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_project_student (project_id, student_id),
  KEY idx_student (student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='竞赛项目成员表';
```

### 5.11 竞赛候选表：`competition_candidate`

```sql
CREATE TABLE IF NOT EXISTS competition_candidate (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  track_code VARCHAR(64) NULL,
  track_name VARCHAR(128) NULL,
  fit_score DECIMAL(5,2) NOT NULL,
  recommendation_reason JSON NULL,
  risk_json JSON NULL,
  gap_json JSON NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'RECOMMENDED',
  reviewed_by BIGINT NULL,
  reviewed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_tenant_track (tenant_id, track_code),
  KEY idx_student (student_id),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='竞赛候选推荐表';
```

### 5.12 训练计划表：`training_plan`

```sql
CREATE TABLE IF NOT EXISTS training_plan (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  plan_type VARCHAR(32) NOT NULL DEFAULT 'COMPETITION',
  start_date DATE NULL,
  end_date DATE NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_project (project_id),
  KEY idx_tenant_status (tenant_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='竞赛训练计划表';
```

### 5.13 训练任务表：`training_task`

```sql
CREATE TABLE IF NOT EXISTS training_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  plan_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  assignee_id BIGINT NULL,
  source_type VARCHAR(32) NULL COMMENT 'MANUAL/ISSUE_EVENT/AI_SCORE/PPT/SCRIPT',
  source_id BIGINT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  task_type VARCHAR(32) NOT NULL COMMENT 'PPT/SCRIPT/MEETING/PRACTICE/REVIEW/MATERIAL',
  status VARCHAR(32) NOT NULL DEFAULT 'NOT_STARTED',
  due_at DATETIME NULL,
  completed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_plan_status (plan_id, status),
  KEY idx_assignee (assignee_id),
  KEY idx_source (source_type, source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='竞赛训练任务表';
```

### 5.14 报告导出任务表：`report_export_task`

```sql
CREATE TABLE IF NOT EXISTS report_export_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  creator_id BIGINT NOT NULL,
  report_type VARCHAR(64) NOT NULL COMMENT 'CLASS_WEEKLY/COURSE_MONTHLY/MAJOR_ABILITY/COMPETITION_TRAINING/SCHOOL_SEMESTER',
  scope_type VARCHAR(32) NOT NULL COMMENT 'CLASS/COURSE/MAJOR/SCHOOL/PROJECT',
  scope_id BIGINT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  file_path VARCHAR(512) NULL,
  file_format VARCHAR(16) NOT NULL DEFAULT 'PDF',
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  KEY idx_tenant_type (tenant_id, report_type),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报告导出任务表';
```

---

## 6. 后端代码改动清单

### 6.1 新增 Entity

目录：

```text
backend/src/main/java/com/orep/backend/entity/
```

新增：

```text
TeachingOutline.java
PracticeTask.java
DialoguePractice.java
DialogueDetail.java
AbilityEvent.java
IssueEvent.java
StudentAbilityProfile.java
RemedialTask.java
CompetitionProject.java
CompetitionProjectMember.java
CompetitionCandidate.java
TrainingPlan.java
TrainingTask.java
ReportExportTask.java
```

### 6.2 新增 Mapper

目录：

```text
backend/src/main/java/com/orep/backend/mapper/
```

新增：

```text
TeachingOutlineMapper.java
PracticeTaskMapper.java
DialoguePracticeMapper.java
DialogueDetailMapper.java
AbilityEventMapper.java
IssueEventMapper.java
StudentAbilityProfileMapper.java
RemedialTaskMapper.java
CompetitionProjectMapper.java
CompetitionProjectMemberMapper.java
CompetitionCandidateMapper.java
TrainingPlanMapper.java
TrainingTaskMapper.java
ReportExportTaskMapper.java
```

### 6.3 新增 Controller

目录：

```text
backend/src/main/java/com/orep/backend/controller/
```

新增：

```text
DashboardController.java
TeachingOutlineController.java
PracticeController.java
AbilityProfileController.java
TeacherWorkbenchController.java
IssueEventController.java
CompetitionController.java
SchoolDashboardController.java
ReportExportController.java
```

### 6.4 新增 Service

目录：

```text
backend/src/main/java/com/orep/backend/service/
```

新增：

```text
DashboardService.java
TeachingOutlineService.java
PracticeService.java
AbilityEventService.java
AbilityProfileService.java
IssueEventService.java
IssueRoutingService.java
TeacherWorkbenchService.java
CompetitionCandidateService.java
CompetitionTrainingService.java
SchoolDashboardService.java
ReportExportService.java
```

### 6.5 修改现有文件

| 文件 | 修改内容 |
|---|---|
| `Meeting.java` | 增加 `meetingType/projectId/trainingPlanId/courseId/trackCode` 字段 |
| `CreateMeetingRequest.java` | 增加会议类型和关联对象字段 |
| `MeetingService.java` | 创建会议时保存新字段 |
| `MeetingController.java` | 创建接口接受新字段 |
| `IssueService.java` | 保留原能力，增加从 `issue` 生成 `issue_event` 的方法 |
| `AiScoreController.java` | 增加生成问题事件接口 |
| `StatisticsController.java` | 增加画像/班级/学校统计接口 |
| `StatisticsService.java` | 拆分现有路演统计和新增画像统计逻辑 |
| `AiChatController.java` | 保留会议 AI 聊天，新增课程练习对话应放到 `PracticeController`，不要继续塞进 meeting 模型 |

---

## 7. API 设计汇总

### 7.1 Dashboard

```text
GET /api/dashboard/workbench
```

### 7.2 教学大纲

```text
GET /api/teaching-outlines
POST /api/teaching-outlines
PUT /api/teaching-outlines/{id}
POST /api/teaching-outlines/import-excel
POST /api/teaching-outlines/generate-ai-draft
POST /api/teaching-outlines/{id}/publish
```

### 7.3 练习

```text
GET /api/practice/tasks
POST /api/practice/{taskId}/start
POST /api/practice/{practiceId}/answer
POST /api/practice/{practiceId}/finish
GET /api/practice/{practiceId}/result
```

### 7.4 能力画像

```text
GET /api/ability-profile/me
GET /api/ability-profile/student/{studentId}
GET /api/ability-profile/student/{studentId}/evidence
GET /api/ability-profile/student/{studentId}/competition-fit
```

### 7.5 教师工作台

```text
GET /api/teacher/classes
GET /api/teacher/dashboard
GET /api/teacher/class/{classId}/report
GET /api/teacher/class/{classId}/warnings
GET /api/teacher/class/{classId}/candidate-recommendations
```

### 7.6 问题事件

```text
GET /api/issue-events
GET /api/issue-events/{id}
POST /api/issue-events/{id}/review
POST /api/issue-events/{id}/convert-remedial-task
POST /api/issue-events/{id}/convert-training-task
POST /api/issues/{issueId}/convert-event
```

### 7.7 竞赛训练

```text
GET /api/competition/workbench
GET /api/competition/candidates
POST /api/competition/candidates/{id}/review
GET /api/competition/projects/{projectId}
POST /api/competition/projects
POST /api/competition/projects/{projectId}/members
GET /api/competition/training-plans/{planId}
POST /api/competition/training-plans
POST /api/competition/training-tasks
PATCH /api/competition/training-tasks/{taskId}
```

### 7.8 AI 评分事件生成

```text
POST /api/ai-score/{meetingId}/generate-events
GET /api/ai-score/{meetingId}/event-summary
```

### 7.9 学校驾驶舱

```text
GET /api/school-dashboard/overview
GET /api/school-dashboard/major-comparison
GET /api/school-dashboard/competition-reserve
GET /api/school-dashboard/training-results
```

### 7.10 报告导出

```text
POST /api/report-export
GET /api/report-export/{taskId}
GET /api/report-export/{taskId}/download
```

---

## 8. 前端代码改动清单

### 8.1 新增页面

```text
frontend/user/src/views/PracticeTaskList.vue
frontend/user/src/views/PracticeSession.vue
frontend/user/src/views/AbilityProfile.vue
frontend/user/src/views/TeacherWorkbench.vue
frontend/user/src/views/IssueEventCenter.vue
frontend/user/src/views/CompetitionWorkbench.vue
frontend/user/src/views/SchoolDashboard.vue
```

### 8.2 新增 API 文件

```text
frontend/user/src/api/dashboard.js
frontend/user/src/api/practice.js
frontend/user/src/api/abilityProfile.js
frontend/user/src/api/teacher.js
frontend/user/src/api/issueEvent.js
frontend/user/src/api/competition.js
frontend/user/src/api/schoolDashboard.js
frontend/user/src/api/reportExport.js
```

如果项目当前没有 `src/api` 目录，可以新增；底层统一调用现有：

```text
frontend/user/src/utils/request.js
```

### 8.3 新增组件目录

```text
frontend/user/src/components/practice/
frontend/user/src/components/ability/
frontend/user/src/components/issue-event/
frontend/user/src/components/competition/
frontend/user/src/components/dashboard/
```

### 8.4 复用现有视觉风格

所有新增页面必须复用现有 OREP 风格：

```text
黑底 #050608
网格背景
Mission Control 文案体系
半透明面板
1px 边框
DIN Alternate / Noto Sans SC 字体栈
Element Plus 表单和按钮风格
```

不得重新做左侧重导航或彩色 SaaS 风格。

---

## 9. 开发分期

## P0：全员成长最小闭环

### 目标

跑通：

```text
教学大纲 → AI 练习 → 能力事件 → 能力画像 → 教师班级概览
```

### 前端范围

```text
Dashboard.vue 改造
PracticeTaskList.vue
PracticeSession.vue
AbilityProfile.vue 基础版
TeacherWorkbench.vue 基础版
router/index.js
```

### 后端范围

```text
TeachingOutlineController/Service
PracticeController/Service
AbilityEventService
AbilityProfileController/Service
DashboardController/Service
```

### 数据表

```text
teaching_outline
practice_task
dialogue_practice
dialogue_detail
ability_event
student_ability_profile
```

### 验收

```text
老师能发布知识点练习
学生能完成一次 AI 练习
练习能生成 ability_event
学生画像能更新
Dashboard 能根据学生状态显示今日练习
老师能看到完成率和高频卡点
```

---

## P1：问题事件与教学回流

### 目标

跑通：

```text
练习问题 → issue_event → 老师审核 → 补练任务
```

### 前端范围

```text
IssueEventCenter.vue
TeacherWorkbench.vue 增加回流审核入口
PracticeTaskList.vue 增加补练任务 Tab
Dashboard.vue 增加待补练卡片
```

### 后端范围

```text
IssueEventController/Service
IssueRoutingService
RemedialTaskMapper/Entity
PracticeService 增加补练任务查询
```

### 数据表

```text
issue_event
remedial_task
```

### 验收

```text
系统能从练习生成 issue_event
老师能审核问题
老师能发布全班补练
学生能收到补练任务
补练完成后能继续生成 ability_event
```

---

## P2：竞赛候选推荐

### 目标

从全体学生能力画像中发现参赛候选。

### 前端范围

```text
AbilityProfile.vue 增加竞赛潜力区
TeacherWorkbench.vue 增加候选推荐 Tab
CompetitionWorkbench.vue 候选基础版
Dashboard.vue 支持 CANDIDATE 首页状态
```

### 后端范围

```text
CompetitionCandidateService
CompetitionController
AbilityProfileService 增加 competition-fit
```

### 数据表

```text
competition_candidate
```

### 验收

```text
老师能看到候选学生列表
每个候选有推荐理由和风险
老师能确认进入观察池
候选学生首页切换为参赛差距
```

---

## P3：竞赛训练融合

### 目标

串联：

```text
项目空间 → PPT/讲稿 → 模拟展示会议 → AI评分 → 会后复盘 → 整改任务
```

### 前端范围

```text
CompetitionWorkbench.vue 完整版
OnlineMeeting.vue 增加会议类型和训练关联
MeetingRoom.vue 显示会议类型上下文
AiScoreResult.vue 增加问题事件生成区
MyRecordings.vue 增加复盘入口
PptEditor.vue 支持 projectId/trainingPlanId 参数
ScriptEditor.vue 支持 projectId/trainingPlanId 参数
```

### 后端范围

```text
CompetitionTrainingService
MeetingService 增加会议类型和训练关联
AiScoreController 增加 generate-events
IssueEventService 支持 AI_SCORE 来源
```

### 数据表

```text
competition_project
competition_project_member
training_plan
training_task
meeting 新增字段
```

### 验收

```text
老师能创建竞赛项目
参赛学生能看到训练工作台
老师能创建模拟展示会议
会议能关联训练计划
AI评分结果能生成 issue_event
issue_event 能转成 training_task
```

---

## P4：学校驾驶舱与报告

### 目标

形成学校采购价值证明。

### 前端范围

```text
SchoolDashboard.vue
Statistics.vue 增加学校概览 Tab
ReportExport 入口
```

### 后端范围

```text
SchoolDashboardController/Service
ReportExportController/Service
StatisticsService 学校聚合逻辑
```

### 数据表

```text
report_export_task
school_ability_summary 可选后续缓存表
major_ability_summary 可选后续缓存表
```

### 验收

```text
学校能看到覆盖学生数、活跃率、能力总览
学校能看到专业对比
学校能看到竞赛储备和训练成果
学校能导出至少 3 类报告
学校端不展示学生原始对话
```

---

## 10. 权限规则

### 10.1 学生

可访问：

```text
Dashboard
Practice
AbilityProfile.me
CompetitionWorkbench 自己所在项目
MyRecordings 自己参与记录
```

不可访问：

```text
TeacherWorkbench
IssueEventCenter 全量数据
SchoolDashboard
```

### 10.2 老师

可访问：

```text
TeacherWorkbench
IssueEventCenter 所属班级/项目
CompetitionWorkbench 所指导项目
Class reports
Candidate recommendations
```

### 10.3 学校管理员

可访问：

```text
SchoolDashboard
专业/班级聚合报告
竞赛储备看板
报告导出
```

不应访问：

```text
学生原始 AI 对话全文
学生隐私原文
```

---

## 11. 测试要求

### 11.1 后端测试

至少覆盖：

```text
PracticeService：开始练习、提交回答、结束练习
AbilityEventService：能力事件聚合画像
IssueRoutingService：问题类型分流规则
IssueEventService：审核后生成补练/整改任务
CompetitionCandidateService：候选推荐规则
MeetingService：会议类型和训练计划关联
```

### 11.2 前端测试

至少人工验收：

```text
普通学生 Dashboard 是否显示今日练习
候选学生 Dashboard 是否显示入队差距
参赛学生 Dashboard 是否显示训练任务
老师 Dashboard 是否显示班级报告和回流审核
AI 练习页三栏布局是否在 1280 和 390 宽度可用
问题事件中心审核操作是否清晰
会议室会中是否没有 AI 弹窗干扰
```

### 11.3 数据验收

```text
一次 AI 练习至少生成一条 dialogue_practice
每轮回答生成 dialogue_detail
完成练习后生成 ability_event
出现卡点时生成 issue_event
老师审核后生成 remedial_task 或 training_task
画像表 student_ability_profile 被更新
```

---

## 12. 研发注意事项

1. 不要把课程 AI 练习继续塞进 `AiChatController` 的 meeting 模型里，应新增 `PracticeController`。
2. 不要改掉 `Profile.vue` 的账号中心职责，能力画像新建 `AbilityProfile.vue`。
3. 不要在 `MeetingRoom.vue` 会中增加 AI Sidecar 或强提醒。
4. 不要把所有 `issue_event` 自动发布给学生，必须经过老师审核。
5. 不要把“裁判提问”作为正式赛制训练文案。
6. `issue` 和 `issue_event` 要分清：前者是会议原始问题，后者是结构化分流事件。
7. P0/P1 可以先用规则生成能力事件和问题事件，不必一次性做复杂 AI 算法。
8. 视觉风格必须沿用现有 OREP，不要另起一套 UI。

---

## 13. 研发交付顺序建议

推荐顺序：

```text
1. SQL 新表与后端 Entity/Mapper
2. PracticeController + PracticeService
3. AbilityEventService + AbilityProfileService
4. PracticeSession.vue + AbilityProfile.vue
5. Dashboard.vue 角色化改造
6. TeacherWorkbench.vue 基础版
7. IssueEventCenter.vue + IssueRoutingService
8. CompetitionCandidateService + 候选推荐
9. CompetitionWorkbench.vue + 会议/PPT/讲稿融合
10. SchoolDashboard.vue + 报告导出
```

最小首个可演示版本建议做到第 6 步：

```text
老师发布练习
学生完成练习
学生看到画像
老师看到班级报告
```

第二个可演示版本做到第 8 步：

```text
从画像推荐候选学生
老师审核候选
候选学生看到差距和专项补练
```

第三个可演示版本做到第 10 步：

```text
参赛队伍项目空间
PPT/讲稿/会议/复盘串联
学校驾驶舱看到成果
```

---

## 14. 最终研发定义

OREP V4.4 的研发目标不是新增几个孤立页面，而是新增一套数据闭环：

```text
教学大纲
→ AI练习
→ ability_event / issue_event
→ 能力画像
→ 教师报告
→ 问题分流
→ 候选推荐
→ 竞赛训练
→ 复盘整改
→ 学校报告
```

只要这个闭环跑通，OREP 才真正从“在线路演评审平台”升级为：

> **职业院校学生能力画像与竞赛拔尖训练平台。**

---

## 15. 接口字段细化

本节用于约束前后端字段命名、枚举值和页面使用方式。所有接口继续使用当前系统的统一响应结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 15.1 `GET /api/dashboard/workbench`

用途：Dashboard 根据当前用户角色和学生阶段渲染不同首页。

返回字段：

```json
{
  "role": "STUDENT",
  "stage": "NORMAL",
  "greeting": "晚上好，小明",
  "hero": {
    "kicker": "MISSION CONTROL",
    "title": "今日课程练习",
    "description": "完成数据库应用开发的查询优化练习，查看能力变化。",
    "primaryAction": {
      "label": "开始今日练习",
      "route": "/practice/1001",
      "type": "primary"
    },
    "secondaryActions": [
      {
        "label": "查看能力画像",
        "route": "/ability-profile",
        "type": "default"
      }
    ]
  },
  "status": {
    "title": "成长画像状态",
    "rows": [
      { "label": "AI 对话练习", "value": "今日待完成", "code": "DAILY" },
      { "label": "能力画像", "value": "持续更新", "code": "LIVE" },
      { "label": "竞赛训练", "value": "未入队", "code": "ROADSHOW" }
    ]
  },
  "metrics": [
    { "code": "PRACTICE", "label": "今日练习", "value": "1", "trend": null },
    { "code": "ABILITY", "label": "综合能力", "value": "78", "trend": "+3" }
  ],
  "modules": [
    {
      "index": "01",
      "kicker": "AI PRACTICE",
      "title": "每日 AI 对话",
      "description": "围绕查询优化完成 8 分钟练习。",
      "route": "/practice/1001",
      "enabled": true
    }
  ],
  "todoList": [
    {
      "id": 5001,
      "type": "PRACTICE",
      "title": "数据库应用开发：查询优化",
      "description": "事实层、推理层、应用层共 8 分钟",
      "status": "NOT_STARTED",
      "route": "/practice/1001",
      "dueAt": "2026-06-10T23:59:59"
    }
  ],
  "quickActions": [
    { "label": "查看能力画像", "route": "/ability-profile", "icon": "DataAnalysis" }
  ]
}
```

枚举：

```text
role: ADMIN / SCHOOL_ADMIN / TEACHER / STUDENT / REVIEWER / EXPERT
stage: NORMAL / CANDIDATE / TEAM_MEMBER / TEAM_LEADER / TEACHER / SCHOOL_ADMIN
todoList.type: PRACTICE / REMEDIAL / TRAINING / MEETING / PPT / SCRIPT / REVIEW
todoList.status: NOT_STARTED / IN_PROGRESS / COMPLETED / OVERDUE / CANCELLED
```

### 15.2 `GET /api/practice/tasks`

用途：获取学生练习任务列表。

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| tab | string | 否 | `today/remedial/candidate/completed` |
| courseName | string | 否 | 课程筛选 |
| status | string | 否 | `NOT_STARTED/IN_PROGRESS/COMPLETED/OVERDUE` |

返回字段：

```json
{
  "tab": "today",
  "list": [
    {
      "id": 1001,
      "taskType": "COURSE",
      "title": "查询优化",
      "description": "围绕索引、执行计划和慢查询排查完成练习。",
      "courseName": "数据库应用开发",
      "knowledgePointTitle": "查询优化",
      "difficulty": "NORMAL",
      "estimatedMinutes": 8,
      "abilityDimensions": ["PROFESSIONAL", "APPLICATION"],
      "status": "NOT_STARTED",
      "progress": 0,
      "dueAt": "2026-06-10T23:59:59",
      "route": "/practice/1001"
    }
  ],
  "summary": {
    "total": 4,
    "completed": 2,
    "overdue": 0
  }
}
```

### 15.3 `POST /api/practice/{taskId}/start`

用途：学生进入练习页时创建或恢复一次练习。

返回字段：

```json
{
  "practiceId": 2001,
  "taskId": 1001,
  "status": "IN_PROGRESS",
  "currentLayer": "FACT",
  "context": {
    "courseName": "数据库应用开发",
    "teachingWeek": 7,
    "knowledgePointTitle": "查询优化",
    "jobSkillTags": ["SQL", "索引", "执行计划"],
    "abilityDimensions": ["PROFESSIONAL", "APPLICATION"]
  },
  "currentQuestion": {
    "questionId": "q_001",
    "layer": "FACT",
    "questionText": "什么是 B+ 树索引？请用一句话说明它为什么适合查询。",
    "answerHint": "可以结合范围查询、叶子节点和磁盘 IO 解释。"
  },
  "history": [],
  "liveScore": {
    "currentScore": 0,
    "dimensionDeltas": []
  }
}
```

### 15.4 `POST /api/practice/{practiceId}/answer`

用途：提交单轮回答，并返回评分、追问、问题事件预览。

请求字段：

```json
{
  "questionId": "q_001",
  "answerText": "B+ 树把数据按顺序组织在叶子节点...",
  "durationSeconds": 42,
  "usedReference": true
}
```

返回字段：

```json
{
  "detailId": 3001,
  "layer": "FACT",
  "score": 82,
  "scoreDetail": {
    "accuracy": 84,
    "completeness": 78,
    "logic": 80,
    "expression": 86
  },
  "feedback": "概念基本准确，但缺少为什么适合范围查询的解释。",
  "templateRiskScore": 18,
  "abilityDeltas": [
    { "dimension": "PROFESSIONAL", "delta": 2.1, "confidence": 0.86 },
    { "dimension": "APPLICATION", "delta": 1.4, "confidence": 0.78 }
  ],
  "issuePreview": [
    {
      "issueType": "JOB_SKILL",
      "description": "索引适用场景解释不完整",
      "suggestedAudience": "CLASS",
      "confidence": 0.82
    }
  ],
  "nextQuestion": {
    "questionId": "q_002",
    "layer": "REASONING",
    "questionText": "如果条件是 LIKE '%三'，索引还能稳定命中吗？为什么？"
  }
}
```

### 15.5 `POST /api/practice/{practiceId}/finish`

用途：结束练习，落库能力事件、问题事件并更新画像。

返回字段：

```json
{
  "practiceId": 2001,
  "finalScore": 82,
  "summary": "本次练习暴露慢查询排查步骤不完整。",
  "abilityEventsCreated": 4,
  "issueEventsCreated": 2,
  "profileUpdated": true,
  "profileSnapshot": {
    "overallScore": 78,
    "professionalScore": 88,
    "applicationScore": 72,
    "expressionScore": 76
  },
  "nextTasks": [
    {
      "id": 1008,
      "title": "慢查询排查补练",
      "route": "/practice/1008"
    }
  ]
}
```

### 15.6 `GET /api/ability-profile/me`

用途：学生查看自己的能力画像。

返回字段：

```json
{
  "studentId": 12,
  "studentName": "小明",
  "overallScore": 78,
  "trendDelta": 3,
  "classRank": 12,
  "classSize": 45,
  "lastUpdatedAt": "2026-06-06T18:30:00",
  "dimensions": [
    {
      "dimension": "PROFESSIONAL",
      "label": "专业能力",
      "score": 88,
      "trend": 2.1,
      "level": "GOOD",
      "explanation": "索引原理和接口部署回答稳定。",
      "evidenceCount": 14
    }
  ],
  "weaknesses": [
    {
      "title": "慢查询排查步骤不完整",
      "dimension": "APPLICATION",
      "relatedKnowledgePoint": "查询优化",
      "suggestion": "完成慢查询排查补练。"
    }
  ],
  "competitionFit": {
    "enabled": true,
    "trackName": "新一代信息技术",
    "fitScore": 86,
    "status": "NOT_IN_POOL",
    "gap": [
      { "dimension": "EXPRESSION", "label": "表达能力", "need": 5 },
      { "dimension": "APPLICATION", "label": "应用能力", "need": 4 }
    ]
  }
}
```

### 15.7 `GET /api/issue-events`

用途：教师查看问题事件列表。

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| reviewStatus | string | 否 | 默认 `PENDING_REVIEW` |
| issueType | string | 否 | 问题类型 |
| suggestedAudience | string | 否 | 建议人群 |
| classId | long | 否 | 班级 |
| sourceType | string | 否 | 来源 |
| page | int | 否 | 默认 1 |
| size | int | 否 | 默认 20 |

返回字段：

```json
{
  "total": 36,
  "list": [
    {
      "id": 7001,
      "description": "索引适用场景解释不完整",
      "sourceType": "AI_PRACTICE",
      "sourceId": 3001,
      "issueType": "JOB_SKILL",
      "issueTypeLabel": "岗位技能问题",
      "relatedCourse": "数据库应用开发",
      "relatedKnowledgePoint": "查询优化",
      "abilityDimensions": ["PROFESSIONAL", "APPLICATION"],
      "suggestedAudience": "CLASS",
      "suggestedAction": "CREATE_REMEDIAL_TASK",
      "confidence": 0.82,
      "reviewStatus": "PENDING_REVIEW",
      "createdAt": "2026-06-06T18:30:00"
    }
  ]
}
```

### 15.8 `POST /api/issue-events/{id}/review`

用途：老师审核问题事件去向。

请求字段：

```json
{
  "decision": "APPROVED_CLASS",
  "targetType": "CLASS",
  "targetId": 101,
  "createTask": true,
  "taskTitle": "查询优化补练",
  "taskDescription": "补练索引适用场景和慢查询排查步骤。",
  "dueAt": "2026-06-12T23:59:59",
  "reviewNote": "下节课前完成。"
}
```

返回字段：

```json
{
  "issueEventId": 7001,
  "reviewStatus": "CONVERTED_TASK",
  "convertedTaskId": 9001,
  "convertedTaskType": "REMEDIAL"
}
```

### 15.9 `GET /api/competition/workbench`

用途：候选学生、参赛队员、老师查看竞赛训练工作台。

返回字段：

```json
{
  "mode": "TEAM_MEMBER",
  "project": {
    "id": 301,
    "name": "智造领航",
    "trackName": "新一代信息技术",
    "teamName": "智造领航队",
    "status": "TRAINING"
  },
  "trainingPlan": {
    "id": 401,
    "title": "省赛前第三轮训练",
    "progress": 68,
    "nextMeeting": {
      "meetingId": 501,
      "title": "第 3 轮模拟展示",
      "startAt": "2026-06-12T19:30:00"
    }
  },
  "materials": {
    "pptTaskId": 601,
    "pptStatus": "第 3 版，待优化 4 页",
    "scriptId": 701,
    "scriptStatus": "应用价值段待补充"
  },
  "tasks": [
    {
      "id": 801,
      "title": "修改 PPT 第 8 页应用价值数据",
      "taskType": "PPT",
      "status": "IN_PROGRESS",
      "assigneeName": "李四"
    }
  ],
  "reviewSummary": {
    "lastScore": 82,
    "openIssues": 4,
    "completedTasks": 9,
    "totalTasks": 14
  }
}
```

### 15.10 `GET /api/school-dashboard/overview`

用途：学校管理员查看聚合数据。

返回字段：

```json
{
  "coverage": {
    "studentCount": 1286,
    "activeStudentCount": 926,
    "activeRate": 72.0,
    "profileCoverageRate": 81.3
  },
  "ability": {
    "overallScore": 78.4,
    "trendDelta": 6.8,
    "dimensionAverages": [
      { "dimension": "PROFESSIONAL", "score": 82 },
      { "dimension": "APPLICATION", "score": 76 }
    ]
  },
  "competition": {
    "candidateCount": 42,
    "projectCount": 6,
    "simulationMeetingCount": 18,
    "reviewCompletionRate": 86.0
  },
  "reports": [
    { "reportType": "SCHOOL_SEMESTER", "label": "学校学期报告", "available": true }
  ]
}
```

---

## 16. 页面交互状态细化

### 16.1 通用页面状态

所有新增页面必须处理：

| 状态 | 展示要求 |
|---|---|
| loading | 使用现有 OREP 深色 loading，不出现白底闪屏 |
| empty | 说明为什么为空，并给出下一步动作 |
| error | 显示错误原因和重试按钮 |
| forbidden | 显示“当前账号无权限访问”，提供返回首页 |
| mobile | 390px 宽度无横向滚动，主操作优先展示 |

### 16.2 Dashboard 交互状态

| 场景 | 页面行为 |
|---|---|
| 普通学生无今日练习 | Hero 主按钮变为“查看补练推荐”，模块显示“暂无今日练习” |
| 学生有逾期任务 | Telemetry 显示逾期数，任务列表置顶逾期任务 |
| 候选学生未被老师确认 | 显示“老师观察中”，不可进入项目空间 |
| 参赛学生有下一场会议 | Hero 主按钮为“进入/查看模拟展示会议” |
| 参赛学生无项目 | 显示空状态“暂未加入参赛队伍” |
| 老师无班级 | 显示“请先绑定班级或创建教学大纲” |

### 16.3 PracticeSession 交互状态

| 场景 | 页面行为 |
|---|---|
| 首次进入 | 自动调用 start，展示第一题 |
| 已有未完成练习 | 恢复历史对话和当前题 |
| 回答提交中 | 输入框禁用，发送按钮 loading |
| 回答为空 | 不提交，提示“请先输入回答” |
| 疑似模板回答 | 右侧反馈提示“回答较模板化，将切换项目场景追问” |
| 当前题完成 | 展示反馈和下一题按钮 |
| 全部完成 | 显示结果页入口和补练建议 |
| 接口失败 | 保留当前输入，允许重试 |

状态机：

```text
NOT_STARTED
→ IN_PROGRESS
→ ANSWERING
→ FEEDBACK
→ NEXT_QUESTION
→ FINISHED
```

### 16.4 AbilityProfile 交互状态

| 场景 | 页面行为 |
|---|---|
| 无画像数据 | 显示“完成一次课程练习后生成画像” |
| 画像更新时间超过 14 天 | 显示“画像需要更新”，推荐练习 |
| 学生非候选 | 竞赛潜力区显示轻量提示，不强调参赛 |
| 候选学生 | 显示入队差距和专项补练入口 |
| 参赛学生 | 显示最近模拟展示对画像的影响 |

### 16.5 IssueEventCenter 交互状态

| 场景 | 页面行为 |
|---|---|
| 无待审核问题 | 显示“暂无待审核问题” |
| 选择问题 | 右侧详情面板更新 |
| 审核为全班补练 | 弹出任务标题、截止时间、目标班级确认框 |
| 审核为候选专项 | 选择候选池或候选学生 |
| 审核为队伍整改 | 选择项目、训练计划、负责人 |
| 忽略 | 必填忽略原因 |
| 审核成功 | 列表移出待审核，显示 toast |

### 16.6 CompetitionWorkbench 交互状态

| 场景 | 页面行为 |
|---|---|
| 候选学生访问 | 默认显示候选差距，不显示队伍材料 |
| 参赛学生访问 | 默认显示项目空间和训练任务 |
| 队长访问 | 显示分配任务、创建会议、队员状态 |
| 老师访问 | 显示候选管理、项目管理、训练进度 |
| 无训练计划 | 显示创建训练计划入口 |
| 无 PPT 绑定 | 显示“绑定或创建 PPT” |
| 无讲稿绑定 | 显示“创建讲稿” |
| 会议未开始 | 显示会议时间和编辑入口 |
| 会议已结束 | 显示复盘入口 |

### 16.7 MeetingRoom 交互状态

| 场景 | 页面行为 |
|---|---|
| 普通会议 | 保持现有会议室 |
| 模拟展示会议 | 顶部显示项目和训练计划，右侧评分仍按现有逻辑 |
| 复盘会议 | 可显示关联录制和问题清单入口 |
| 会中 AI | 不显示 AI 弹窗，不自动插话 |

### 16.8 AiScoreResult 交互状态

| 场景 | 页面行为 |
|---|---|
| AI 评分未生成 | 显示重新加载和返回会议 |
| 问题事件未生成 | 显示“生成问题事件”按钮 |
| 已生成问题事件 | 显示分类统计和“查看问题事件中心” |
| 生成失败 | 显示失败原因和重试按钮 |

---

## 17. 后端类方法级设计

### 17.1 `DashboardService`

```java
public WorkbenchVO getWorkbench(Long tenantId, Long userId, String role);
private StudentStage resolveStudentStage(Long userId, String role);
private WorkbenchVO buildStudentWorkbench(Long tenantId, Long userId, StudentStage stage);
private WorkbenchVO buildTeacherWorkbench(Long tenantId, Long userId);
private WorkbenchVO buildSchoolWorkbench(Long tenantId, Long userId);
```

职责：

```text
1. 判断用户角色和学生阶段。
2. 汇总今日任务、画像摘要、候选状态、训练任务。
3. 返回前端 Dashboard 可直接渲染的数据结构。
```

### 17.2 `TeachingOutlineService`

```java
public List<TeachingOutline> listOutlines(Long tenantId, Long teacherId, OutlineQuery query);
public TeachingOutline createOutline(Long tenantId, Long teacherId, CreateOutlineRequest request);
public TeachingOutline updateOutline(Long tenantId, Long teacherId, Long outlineId, UpdateOutlineRequest request);
public void publishOutline(Long tenantId, Long teacherId, Long outlineId);
public List<PracticeTask> generatePracticeTasksFromOutline(Long tenantId, Long outlineId);
```

事务要求：

```text
publishOutline 与 generatePracticeTasksFromOutline 应在同一事务中完成。
发布失败时不能生成半截练习任务。
```

### 17.3 `PracticeService`

```java
public PracticeTaskPageVO listTasks(Long tenantId, Long studentId, PracticeTaskQuery query);
public PracticeStartVO startPractice(Long tenantId, Long studentId, Long taskId);
public PracticeAnswerVO submitAnswer(Long tenantId, Long studentId, Long practiceId, PracticeAnswerRequest request);
public PracticeFinishVO finishPractice(Long tenantId, Long studentId, Long practiceId);
public PracticeResultVO getPracticeResult(Long tenantId, Long studentId, Long practiceId);
```

核心流程：

```text
startPractice:
1. 校验任务是否属于学生。
2. 如果存在未完成 practice，直接恢复。
3. 否则创建 dialogue_practice。
4. 根据 task 和当前层级生成第一题。

submitAnswer:
1. 写入 dialogue_detail。
2. 计算单题分数。
3. 生成临时 ability delta。
4. 识别 issue preview。
5. 生成下一题。

finishPractice:
1. 汇总 dialogue_detail。
2. 创建 ability_event。
3. 创建 issue_event。
4. 更新 student_ability_profile。
5. 根据 issue_event 生成 nextTasks 建议。
```

第一版评分可以先用规则：

```text
准确性：关键词覆盖 + 语义长度
完整性：是否覆盖题目要求点
逻辑：是否包含因果词、步骤结构
表达：是否清楚、是否过短
模板风险：与标准答案相似但缺少个人场景
```

后续再接入更复杂 AI 评分。

### 17.4 `AbilityEventService`

```java
public List<AbilityEvent> createFromPractice(Long tenantId, Long studentId, Long practiceId);
public List<AbilityEvent> createFromAiScore(Long tenantId, Long meetingId);
public void recalculateStudentProfile(Long tenantId, Long studentId);
public Map<String, BigDecimal> aggregateDimensionScores(Long tenantId, Long studentId);
```

画像计算建议：

```text
每个维度取最近 90 天事件。
按 source_type 设置权重：
AI_PRACTICE       0.55
REMEDIAL          0.15
PPT/SCRIPT        0.10
MEETING_SCORE     0.15
REVIEW            0.05

同一维度按 confidence 加权平均。
最近 14 天事件增加时间权重。
```

### 17.5 `IssueRoutingService`

```java
public IssueEvent classifyFromDialogueDetail(Long tenantId, DialogueDetail detail);
public IssueEvent classifyFromMeetingIssue(Long tenantId, Issue issue);
public IssueEvent classifyFromAiScore(Long tenantId, Long meetingId, Map<String, Object> issuePayload);
public SuggestedAudience suggestAudience(IssueEvent event);
public SuggestedAction suggestAction(IssueEvent event);
```

分流规则：

```text
1. related_course 和 related_knowledge_point 非空，且 issue_type=JOB_SKILL → CLASS
2. issue_type=JOB_TASK_UNDERSTAND → PARTIAL_STUDENTS 或 CANDIDATE
3. issue_type=COMPETITION_DISPLAY → CANDIDATE 或 TEAM
4. issue_type=TEAM_COLLABORATION → TEAM 或 TEAM_LEADER
5. confidence < 0.65 → TEACHER_ONLY
```

### 17.6 `IssueEventService`

```java
public Page<IssueEventVO> listIssueEvents(Long tenantId, Long userId, String role, IssueEventQuery query);
public IssueEventDetailVO getDetail(Long tenantId, Long userId, String role, Long id);
public IssueReviewResultVO review(Long tenantId, Long reviewerId, Long id, IssueReviewRequest request);
public RemedialTask convertToRemedialTask(Long tenantId, Long reviewerId, Long issueEventId, ConvertTaskRequest request);
public TrainingTask convertToTrainingTask(Long tenantId, Long reviewerId, Long issueEventId, ConvertTaskRequest request);
```

事务要求：

```text
review + convert task 必须事务化。
converted_task_id 回写 issue_event。
重复审核要幂等，已 CONVERTED_TASK 不允许再次生成任务。
```

### 17.7 `AbilityProfileService`

```java
public AbilityProfileVO getMyProfile(Long tenantId, Long studentId);
public AbilityProfileVO getStudentProfile(Long tenantId, Long requesterId, String role, Long studentId);
public List<AbilityEvidenceVO> listEvidence(Long tenantId, Long studentId, AbilityEvidenceQuery query);
public CompetitionFitVO getCompetitionFit(Long tenantId, Long studentId);
```

权限：

```text
学生只能看自己。
老师只能看自己班级或指导项目学生。
学校管理员只能看聚合，查看个人需额外授权。
```

### 17.8 `CompetitionCandidateService`

```java
public List<CompetitionCandidateVO> recommendCandidates(Long tenantId, CandidateQuery query);
public CompetitionCandidate createOrUpdateCandidate(Long tenantId, Long studentId, String trackCode);
public void reviewCandidate(Long tenantId, Long teacherId, Long candidateId, CandidateReviewRequest request);
public CandidateGapVO calculateGap(Long tenantId, Long studentId, String trackCode);
```

推荐分计算建议：

```text
fit_score =
专业能力 * 0.28
+ 应用能力 * 0.22
+ 表达能力 * 0.18
+ 学习能力 * 0.12
+ 复盘能力 * 0.08
+ 稳定性 * 0.08
+ 成长趋势 * 0.04
```

第一版不做复杂机器学习，先用透明规则，方便老师信任。

### 17.9 `CompetitionTrainingService`

```java
public CompetitionWorkbenchVO getWorkbench(Long tenantId, Long userId, String role);
public CompetitionProject createProject(Long tenantId, Long teacherId, CreateProjectRequest request);
public void addMember(Long tenantId, Long operatorId, Long projectId, AddMemberRequest request);
public TrainingPlan createPlan(Long tenantId, Long operatorId, CreateTrainingPlanRequest request);
public TrainingTask createTask(Long tenantId, Long operatorId, CreateTrainingTaskRequest request);
public TrainingTask updateTaskStatus(Long tenantId, Long operatorId, Long taskId, UpdateTaskStatusRequest request);
public void bindPptTask(Long tenantId, Long projectId, Long pptTaskId);
public void bindScript(Long tenantId, Long projectId, Long scriptId);
```

### 17.10 `SchoolDashboardService`

```java
public SchoolOverviewVO getOverview(Long tenantId);
public List<MajorComparisonVO> getMajorComparison(Long tenantId);
public CompetitionReserveVO getCompetitionReserve(Long tenantId);
public TrainingResultVO getTrainingResults(Long tenantId);
```

数据原则：

```text
只返回聚合数据。
不返回学生原始对话。
可返回候选数量、项目数量、训练次数、报告数量。
```

---

## 18. SQL 索引与数据性能设计

### 18.1 多租户索引原则

所有新增业务表必须有：

```text
tenant_id
tenant_id + status
tenant_id + created_at
```

凡是学生维度查询高频的表必须有：

```text
student_id
student_id + created_at
student_id + dimension
```

### 18.2 建议补充索引

`practice_task`：

```sql
CREATE INDEX idx_practice_task_due ON practice_task (tenant_id, due_at);
CREATE INDEX idx_practice_task_status ON practice_task (tenant_id, status, task_type);
```

`dialogue_practice`：

```sql
CREATE INDEX idx_dialogue_practice_status ON dialogue_practice (tenant_id, student_id, status);
CREATE INDEX idx_dialogue_practice_finished ON dialogue_practice (tenant_id, finished_at);
```

`dialogue_detail`：

```sql
CREATE INDEX idx_dialogue_detail_practice_layer ON dialogue_detail (practice_id, layer);
```

`ability_event`：

```sql
CREATE INDEX idx_ability_event_profile_calc ON ability_event (student_id, dimension, created_at);
CREATE INDEX idx_ability_event_tenant_source ON ability_event (tenant_id, source_type, source_id);
```

`issue_event`：

```sql
CREATE INDEX idx_issue_event_review_queue ON issue_event (tenant_id, review_status, created_at);
CREATE INDEX idx_issue_event_routing ON issue_event (tenant_id, issue_type, suggested_audience);
CREATE INDEX idx_issue_event_course ON issue_event (tenant_id, related_course, related_knowledge_point);
```

`student_ability_profile`：

```sql
CREATE INDEX idx_profile_tenant_overall ON student_ability_profile (tenant_id, overall_score);
CREATE INDEX idx_profile_updated ON student_ability_profile (tenant_id, updated_at);
```

`competition_candidate`：

```sql
CREATE INDEX idx_candidate_rank ON competition_candidate (tenant_id, track_code, status, fit_score);
```

`training_task`：

```sql
CREATE INDEX idx_training_task_due ON training_task (tenant_id, status, due_at);
CREATE INDEX idx_training_task_project ON training_task (project_id, status);
```

### 18.3 JSON 字段使用原则

允许使用 JSON 的字段：

```text
ability_dimensions
evidence_json
score_detail
profile_json
recommendation_reason
gap_json
```

但以下字段必须单独列，不能只放 JSON：

```text
tenant_id
student_id
class_id
team_id
source_type
source_id
dimension
score
issue_type
suggested_audience
review_status
status
created_at
```

原因：这些字段需要高频筛选、排序、聚合。

### 18.4 画像更新策略

P0/P1 使用同步更新：

```text
finishPractice
→ 写 ability_event
→ recalculateStudentProfile
→ 更新 student_ability_profile
```

P2 以后可改为异步：

```text
ability_event 写入
→ profile_recalc_queue
→ 后台任务批量更新画像
```

第一版不新增队列表，避免复杂度过高。

### 18.5 聚合缓存策略

学校驾驶舱 P4 前可以实时聚合。数据量上来后再新增：

```text
class_ability_summary
major_ability_summary
school_ability_summary
```

刷新策略：

```text
每日凌晨刷新
老师手动刷新班级报告
重大训练结束后触发局部刷新
```

---

## 19. 测试用例细化

### 19.1 后端单元测试

#### PracticeService

| 用例 | 前置条件 | 期望 |
|---|---|---|
| startPractice 创建新练习 | 学生有未开始任务 | 生成 dialogue_practice，返回第一题 |
| startPractice 恢复练习 | 学生已有 IN_PROGRESS | 不重复创建，返回历史记录 |
| submitAnswer 正常评分 | 提交有效回答 | 写 dialogue_detail，返回 score 和 nextQuestion |
| submitAnswer 空回答 | answerText 为空 | 返回 400，不写明细 |
| finishPractice 完成练习 | 至少一条明细 | 创建 ability_event，更新画像 |
| finishPractice 重复调用 | 已 FINISHED | 幂等返回已有结果 |

#### AbilityEventService

| 用例 | 前置条件 | 期望 |
|---|---|---|
| createFromPractice | 练习有多层回答 | 每个维度生成能力事件 |
| recalculateStudentProfile | 学生有近 90 天事件 | 按权重更新画像 |
| recalculateStudentProfile 无事件 | 学生无事件 | 画像为 0 或保持空状态 |

#### IssueRoutingService

| 用例 | 输入问题 | 期望分流 |
|---|---|---|
| 岗位技能问题 | 索引解释不完整 | issueType=JOB_SKILL, audience=CLASS |
| 任务理解问题 | 说不清功能给谁用 | issueType=JOB_TASK_UNDERSTAND |
| 展示问题 | PPT 应用价值页缺数据 | issueType=COMPETITION_DISPLAY, audience=TEAM |
| 协作问题 | 队员衔接混乱 | issueType=TEAM_COLLABORATION, audience=TEAM |
| 低置信度问题 | confidence=0.5 | audience=TEACHER_ONLY |

#### IssueEventService

| 用例 | 前置条件 | 期望 |
|---|---|---|
| review APPROVED_CLASS | 待审核问题 | 更新 review_status |
| convert-remedial-task | 审核为全班补练 | 创建 remedial_task 和 practice_task |
| convert-training-task | 审核为队伍整改 | 创建 training_task |
| 重复 convert | 已 converted | 不重复创建，返回已有任务 |
| 非授权老师审核 | 非所属班级 | 返回 403 |

#### CompetitionCandidateService

| 用例 | 前置条件 | 期望 |
|---|---|---|
| 推荐候选 | 学生画像完整 | 生成 fit_score 和推荐理由 |
| 画像不足 | 练习次数不足 | 标记 evidenceNotEnough |
| 老师确认 | candidateId 有效 | 状态改为 OBSERVING |
| 老师拒绝 | candidateId 有效 | 状态改为 REJECTED，保留原因 |

### 19.2 后端集成测试

#### 流程 1：课程练习到画像

```text
1. 老师创建 teaching_outline。
2. 发布大纲生成 practice_task。
3. 学生 startPractice。
4. 学生 submitAnswer 两次。
5. 学生 finishPractice。
6. 校验 dialogue_practice FINISHED。
7. 校验 ability_event 数量大于 0。
8. 校验 student_ability_profile 更新时间变化。
```

#### 流程 2：问题回流

```text
1. 构造 issue_event PENDING_REVIEW。
2. 老师 review APPROVED_CLASS。
3. 调用 convert-remedial-task。
4. 校验 remedial_task 创建。
5. 校验 practice_task 创建。
6. 校验 issue_event converted_task_id 已回写。
```

#### 流程 3：竞赛训练

```text
1. 老师创建 competition_project。
2. 添加 project_member。
3. 创建 training_plan。
4. 创建 meeting，meeting_type=SIMULATION_DISPLAY。
5. AI score 生成 issue_event。
6. issue_event 转 training_task。
7. 队员完成 training_task。
```

### 19.3 前端页面测试

#### Dashboard.vue

| 场景 | 操作 | 期望 |
|---|---|---|
| 普通学生 | 登录进入首页 | 显示今日练习、能力画像、补练推荐 |
| 候选学生 | mock stage=CANDIDATE | 显示入队差距和专项补练 |
| 参赛学生 | mock stage=TEAM_MEMBER | 显示项目空间、PPT、讲稿、模拟展示 |
| 老师 | mock role=TEACHER | 显示班级概览和回流审核入口 |
| 接口失败 | workbench 返回 500 | 显示错误状态和重试 |

#### PracticeSession.vue

| 场景 | 操作 | 期望 |
|---|---|---|
| 首次进入 | 打开 `/practice/1001` | 自动 start，显示第一题 |
| 提交回答 | 输入回答并发送 | 显示反馈、能力增量、下一题 |
| 模板风险 | mock templateRiskScore 高 | 显示防糊弄提示 |
| 练习完成 | 完成最后一题 | 显示结果和补练建议 |
| 移动端 | 390px 宽度 | 三栏改为上下堆叠，无横向滚动 |

#### IssueEventCenter.vue

| 场景 | 操作 | 期望 |
|---|---|---|
| 查看待审核 | 进入页面 | 左侧问题列表，右侧详情 |
| 发布全班补练 | 点击全班补练 | 弹窗填写标题/截止时间 |
| 转队伍整改 | 点击队伍整改 | 选择项目、训练计划、负责人 |
| 忽略问题 | 点击忽略 | 必填忽略原因 |
| 审核成功 | 提交 | 列表刷新，toast 成功 |

#### CompetitionWorkbench.vue

| 场景 | 操作 | 期望 |
|---|---|---|
| 候选学生 | 进入页面 | 只显示候选差距和专项补练 |
| 参赛学生 | 进入页面 | 显示项目空间和任务 |
| 队长 | 进入页面 | 显示分配任务和创建会议 |
| 老师 | 进入页面 | 显示训练进度和候选管理 |

### 19.4 权限测试

| 用户 | 访问 | 期望 |
|---|---|---|
| STUDENT | `/teacher-workbench` | 403 或跳回首页 |
| STUDENT | `/school-dashboard` | 403 |
| TEACHER | 非自己班级 issue_event | 403 |
| SCHOOL_ADMIN | 学生原始对话详情 | 403 或脱敏 |
| ADMIN | 学校驾驶舱 | 可访问 |

### 19.5 数据库测试

```text
1. 所有新增表可重复执行 CREATE TABLE IF NOT EXISTS。
2. meeting ALTER TABLE 可重复迁移需做字段存在判断或单独版本化。
3. ability_event 大量插入后，按 student_id + dimension 查询走索引。
4. issue_event 按 review_status 查询走 idx_issue_event_review_queue。
5. student_ability_profile student_id 唯一约束生效。
```

---

## 20. 研发任务拆分建议

### 20.1 后端任务拆分

```text
BE-01 新增 SQL 迁移和 Entity/Mapper
BE-02 教学大纲接口
BE-03 练习任务与对话练习接口
BE-04 能力事件生成与画像计算
BE-05 问题事件生成与分流规则
BE-06 教师工作台接口
BE-07 候选推荐接口
BE-08 竞赛项目和训练任务接口
BE-09 会议类型扩展
BE-10 学校驾驶舱和报告导出接口
```

### 20.2 前端任务拆分

```text
FE-01 API 封装和路由新增
FE-02 Dashboard 分层工作台改造
FE-03 PracticeTaskList 和 PracticeSession
FE-04 AbilityProfile
FE-05 TeacherWorkbench
FE-06 IssueEventCenter
FE-07 CompetitionWorkbench
FE-08 OnlineMeeting/MeetingRoom 训练关联
FE-09 AiScoreResult 问题事件出口
FE-10 SchoolDashboard
```

### 20.3 测试任务拆分

```text
QA-01 P0 教学成长闭环测试
QA-02 P1 问题回流闭环测试
QA-03 P2 候选推荐测试
QA-04 P3 竞赛训练闭环测试
QA-05 P4 学校驾驶舱测试
QA-06 权限和隐私测试
QA-07 移动端布局测试
```
