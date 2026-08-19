# 教师端 UI 架构说明（2026-08）

## 目标

以功能清单与可交互原型为准，结合学生端（`frontend/user`）设计 token 与壳层模式，重构教师端：

1. **业务语义**：项目为主上下文，训练营为训练执行上下文（不再用“团队名称”承载业务归属）。
2. **信息架构**：对齐原型导航（工作台 / 项目团队 / 训练管理 / 路演管理 / AI应用 / 资源管理 / 学情分析）。
3. **视觉系统**：复用学生端 `@user-styles/workspace-tokens.css` 的 `--ds-*`，教师端在 `styles/teacher.css` 落地壳层与运营页组件。

## 品牌

- 正式名称：**启发·竞赛大脑**
- Logo：`public/brand/competition-brain-mark.svg`（与学生端一致）
- 文档标题：`{页面} · 启发·竞赛大脑`

## 壳层结构（V2）

```text
TeacherShell
├── 左侧 sidebar
│   ├── 品牌（logo + 启发·竞赛大脑 / 教师端）
│   ├── 一级导航 + 手风琴二级
│   └── 协作入口（横向卡片）
├── 顶栏 topbar
│   ├── 当前上下文切换（项目 / 训练营）
│   ├── 消息（不造假未读数）
│   └── 账户菜单
├── 已访问页签 route-tabs（工作台固定）
└── main → router-view
```

对应实现：

- `src/components/TeacherShell.vue`
- `src/config/nav.js`
- `src/stores/context.js`（项目 / 训练营）
- `src/stores/visitedTabs.js`
- `src/styles/teacher.css`

## 路由映射

| 导航 | 路径 |
| --- | --- |
| 工作台 | `/` |
| 项目管理 | `/projects` |
| 成员管理 | `/members` |
| 训练营管理 | `/camp` |
| 每日计划 | `/camp/plan` |
| 提交与批改 | `/camp/review-queue` |
| 训练进度 | `/camp/progress` |
| 路演场次 | `/roadshow` |
| 评分报告 | `/review/reports` |
| 整改复盘 | `/review/ai-todos` |
| 小启AI | `/ai/assistant` |
| PPT管理 | `/ai/ppt` |
| 讲稿管理 | `/ai/scripts` |
| 团队资源 / 公共资源 | `/resources?scope=team\|public` |
| 学情总览 / 学生档案 / 荣誉与整改 | `/analytics` 等 |

旧路径 `/team*` 保留 redirect。

## 数据策略（强制真实数据）

- **禁止**页面内置演示静态业务数据。
- 全局上下文：`TeacherShell` → `fetchMyTeams` + `fetchTeacherCamps` → `stores/context`
- 工作台：`/api/teacher/portal/workbench` + camp overview + review-queue
- 每日计划 / 训练进度 / 批改：`/api/teacher/portal/camp` + review-queue + submission detail
- 项目 / 成员：`/api/project-teams/*`
- 资源 / PPT / 讲稿：`/api/teacher/portal/resources`
- 接口失败时展示空态与错误提示，**不得**回落假数据

## 设计对齐

| 项 | 学生端 | 教师端 |
| --- | --- | --- |
| Token | `workspace-tokens.css` | 同路径 alias 引入 |
| 品牌橙 | `--ds-orange` | 主按钮 / 导航激活 |
| 页面标题 | 24px / 700 | `.teacher-page__head h1` |
| 主按钮 | 40px | `.teacher-btn` |
| 卡片 | 轻表面 + 弱阴影 | `.teacher-card` |

## 第二阶段已落地（2026-08）

### 每日计划 `/camp/plan`
- 周期卡片：训练营 / 项目 / 日期范围 / 发布·草稿·未规划统计
- 三日窗口导航 + 昨天/今天/明天标记 + 查看周期日历
- 三步编辑：基本信息 → 学习内容 → 提交任务（含格式多选）
- 有后端训练营数据时走 API 保存；否则演示 mock 完整可编辑

### 提交与批改 `/camp/review-queue`
- 训练日概览指标（应提交 / 全部 / 必交 / 部分 / 未交 / 待批改）
- 姓名搜索、提交状态、批改状态筛选
- 提醒未提交、开始/继续批改、复核、查看
- 批改抽屉：材料、历史、反馈、通过/重交、要求整改
- 真实 review-queue 有数据时会合并进今日列表

## 后续迭代建议

1. 训练进度页：完成趋势 / 提交分布 / 项目完成率图（对齐原型）。
2. 项目详情页签：概览 / 成员岗位 / 团队任务 / 共享资源 / 训练与路演。
3. 真实 API 字段统一为 project 语义，逐步去掉 team 命名。
4. 路演主持台、整改复盘主从布局按原型加深。

