# Glossary - 术语表

> 项目代号：PitchForge
> 版本：1.0.0
> 创建日期：2026-04-15
> 维护者：Standards Keeper

---

## 变更历史

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|-------|
| 1.0.0 | 2026-04-15 | 初始版本 | Standards Keeper |

---

## 一、项目术语

### 1.1 Round（轮次）

指 PPT 生成过程中的不同轮次迭代。

| 术语 | 说明 | 上下文 |
|------|------|--------|
| Round 1 | 第一轮生成 | AI 根据问卷数据生成初始大纲和PPT |
| Round 2 | 第二轮生成 | 基于第一轮反馈进行调整优化 |
| Round 3 | 第三轮生成 | 最终优化，完成定稿 |

### 1.2 Phase（阶段）

指 PPT 生成管道的不同处理阶段。

| 术语 | 说明 | 关键文件 |
|------|------|----------|
| Phase 1 | Outline Generation | AI 生成 PPT 大纲结构 |
| Phase 2 | Data Validation & Enhancement | 数据验证与增强（非AI） |
| Phase 3 | Layout & Structure | 布局与结构分配（非AI） |
| Phase 4 | Background Generation | AI 生成背景图（可选） |
| Phase 5 | Assembly & Render | 组件装配与渲染（非AI） |

### 1.3 组件类型 (Component Types)

PPT 页面中的各种可视化组件。

| 组件ID | 名称 | 说明 | 适用语义类型 |
|--------|------|------|-------------|
| cover | 封面组件 | 项目名称、团队、学校信息 | COVER |
| toc | 目录组件 | 章节概览列表 | TOC |
| section_divider | 章节分隔组件 | 大标题+章节序号 | SECTION_DIVIDER |
| ending | 结尾组件 | 感谢语/联系方式 | ENDING |
| kpi_metrics | KPI指标组件 | 关键数据指标展示 | BACKGROUND_DATA, ACHIEVEMENT |
| bar_chart_svg | 柱状图组件 | 柱状图数据可视化 | BACKGROUND_DATA, DATA_COMPARE |
| pie_chart_svg | 饼图组件 | 占比数据可视化 | BACKGROUND_DATA, ACHIEVEMENT |
| line_chart_svg | 折线图组件 | 趋势数据可视化 | BACKGROUND_DATA |
| timeline_vertical | 垂直时间线组件 | 操作步骤展示 | SKILL_STEPS |
| flow_diagram | 流程图组件 | 架构/流程展示 | SOLUTION_ARCH, SKILL_STEPS |
| three_column_cards | 三列卡片组件 | 痛点/特性对比 | PAIN_POINTS |
| two_column_ps | 双列图文组件 | 左图右文布局 | PAIN_POINTS, SOLUTION_ARCH |
| comparison_table | 对比表格组件 | 竞品/方案对比 | DATA_COMPARE |
| team_cards | 团队卡片组件 | 团队成员介绍 | TEAM_INTRO |
| full_text_page | 全文本组件 | 纯文本内容页 | 所有内容页 |

### 1.4 布局类型 (Layout Types)

页面布局模板。

| 布局ID | 名称 | 说明 |
|--------|------|------|
| cover_layout | 封面布局 | 封面页专用布局 |
| toc_layout | 目录布局 | 目录页专用布局 |
| section_layout | 章节布局 | 章节分隔页专用布局 |
| ending_layout | 结尾布局 | 结尾页专用布局 |
| content_layout | 内容布局 | 通用内容布局 |
| two_column_layout | 双列布局 | 左右分栏布局 |
| data_layout | 数据布局 | 数据展示布局 |
| team_layout | 团队布局 | 团队介绍布局 |
| timeline_layout | 时间线布局 | 时间轴/步骤布局 |

---

## 二、角色定义

### 2.1 用户角色 (User Roles)

| 角色 | 说明 | 权限范围 |
|------|------|----------|
| 普通用户 | 提交问卷、生成PPT、下载查看 | 自己的任务 |
| 管理员 | 管理所有任务、配置评分规则 | 所有任务 + 系统配置 |

### 2.2 系统角色 (Agent Roles)

项目团队中的 Agent 角色定义。

| 角色 | 职责 | 不做的事 |
|------|------|---------|
| Orchestrator | 调度者，唯一与人对话的接口 | 不写代码、不做技术决策 |
| Tech Lead | 架构决策、任务分配、冲突仲裁 | 不写具体代码 |
| Prompt Engineer | Prompt 设计、调试、优化 | 不写后端/前端 |
| Backend Engineer | API、Pipeline、后端实现 | 不改 Prompt、不做前端 |
| Frontend Engineer | 确认节点 UI、进度展示 | 不写后端逻辑 |
| QA Reviewer | 代码审查、产出物质量审查 | 不写代码 |
| Standards Keeper | 规范制定、验收标准 | 不写代码、不审查代码 |

---

## 三、流程术语

### 3.1 流程阶段 (Process Phases)

| 阶段名称 | 说明 | 输入 | 输出 |
|----------|------|------|------|
| 问卷提交 | 用户填写并提交问卷 | 用户填写的表单数据 | Questionnaire 数据 |
| 任务创建 | 创建 PPT 生成任务 | Questionnaire ID | Task 创建 |
| 大纲生成 | AI 生成 PPT 结构大纲 | Questionnaire 数据 | Outline JSON |
| 大纲确认 | 用户确认/调整大纲 | Outline JSON | 确认的大纲 |
| PPT生成 | 完整 PPT 文件生成 | 确认的大纲 | PPT 文件 |
| 任务完成 | 通知用户，任务结束 | PPT 文件 | 完成的 Task |

### 3.2 状态定义 (Status Definitions)

**问卷状态 (Questionnaire Status)**：

| 状态 | 说明 |
|------|------|
| draft | 草稿（用户正在填写） |
| submitted | 已提交 |
| approved | 已审核 |
| rejected | 已驳回 |

**任务状态 (Task Status)**：

| 状态 | 说明 |
|------|------|
| pending | 等待处理 |
| processing | 处理中 |
| outline_ready | 大纲已生成，待确认 |
| confirmed | 大纲已确认，生成中 |
| completed | PPT 生成完成 |
| failed | 生成失败 |

### 3.3 评分标准术语

职业技能大赛 PPT 评分维度。

| 术语 | 分值 | 说明 |
|------|------|------|
| 项目背景和意义 | 6分 | 国家战略对接、行业趋势、社会需求 |
| 调研分析 | 8分 | 目标用户、市场调研、竞品分析 |
| 方案设计 | 10分 | 系统架构、技术路线、可行性 |
| 功能实现 | 15分 | 核心功能、创新点、技术实现 |
| 演示效果 | 10分 | PPT 呈现效果、视觉效果 |
| 现场答辩 | 15分 | 现场表现、应变能力 |
| 技能操作 | 20分 | 标准化操作、流程规范 |
| 团队协作 | 8分 | 分工合理、协作顺畅 |
| 成果展示 | 8分 | 已取得成果、数据验证 |

### 3.4 语义类型 (Semantic Types)

页面内容语义分类，用于 AI 选择组件和布局。

| 语义类型 | 说明 | 所属章节分类 |
|----------|------|-------------|
| COVER | 封面页 | - |
| TOC | 目录页 | - |
| SECTION_DIVIDER | 章节分隔页 | - |
| ENDING | 结尾页 | - |
| BACKGROUND_DATA | 背景数据页 | 项目背景 |
| PAIN_POINTS | 痛点分析页 | 痛点分析 |
| SOLUTION_ARCH | 方案架构页 | 解决方案 |
| SKILL_STEPS | 技能操作页 | 解决方案 |
| DATA_COMPARE | 数据对比页 | 功能实现 |
| TEAM_INTRO | 团队介绍页 | 团队总结 |
| ACHIEVEMENT | 成果展示页 | 成果展示 |
| FUTURE_PLAN | 未来规划页 | 未来规划 |

---

## 四、技术术语

### 4.1 AI 服务

| 术语 | 说明 |
|------|------|
| DeepSeek | 大语言模型，用于大纲和内容生成 |
| Qwen | 阿里通义千问，用于HTML渲染 |
| AI Background Generation | AI 生成背景图片 |

### 4.2 存储服务

| 术语 | 说明 |
|------|------|
| MySQL | 关系型数据库，存储任务和问卷数据 |
| Local File System | 本地文件系统，存储生成的 PPT 文件 |

### 4.3 配置管理

| 术语 | 说明 |
|------|------|
| .env | 环境变量配置文件 |
| settings | 应用配置对象 |
| theme | PPT 视觉主题配置 |

---

## 五、文件路径约定

### 5.1 目录结构

```
项目根目录/
├── app/                          # 应用代码
│   ├── routers/                  # API 路由
│   ├── services/                 # 业务服务
│   │   └── ppt/                  # PPT 生成相关
│   │       ├── components/       # PPT 组件
│   │       ├── layouts/          # 布局模板
│   │       └── adapter_code/     # 适配器代码
│   ├── models/                   # 数据模型
│   └── config.py                 # 配置文件
├── standards/                    # 规范文档（Standards Keeper）
├── prompts/                      # Prompt 模板（Prompt Engineer）
├── tests/                        # 测试代码（QA）
├── docs/                         # 技术文档（Tech Lead）
├── WORK_LOG/                     # 工作日志
└── uploads/                      # 用户上传/生成文件
```

### 5.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| Python 模块 | 小写下划线 | `ppt_service.py` |
| Python 类 | CapWords | `PPTService`, `OutlineGenerator` |
| API 路由文件 | `*_router.py` | `ppt_router.py` |
| 组件文件 | `*.py` | `kpi_metrics.py` |
| 布局文件 | `*.py` | `cover.py`, `content.py` |
| 配置文件 | 小写下划线 | `config.py`, `settings.py` |

---

## 六、缩略语

| 缩略语 | 全称 | 说明 |
|--------|------|------|
| PPT | PowerPoint | 演示文稿 |
| API | Application Programming Interface | 应用程序接口 |
| JSON | JavaScript Object Notation | JSON 数据格式 |
| Schema | Schema | 数据结构定义 |
| ID | Identifier | 标识符 |
| UUID | Universally Unique Identifier | 通用唯一标识符 |
| ORM | Object-Relational Mapping | 对象关系映射 |
| CI/CD | Continuous Integration/Continuous Deployment | 持续集成/持续部署 |

---

## 七、参考文档

| 文档 | 路径 | 说明 |
|------|------|------|
| CODING_STANDARDS | standards/CODING_STANDARDS.md | 代码规范 |
| DATA_FORMAT_SPEC | standards/DATA_FORMAT_SPEC.md | 数据格式规范 |
| AGENTS | AGENTS.md | Agent 团队协作总则 |
| ROADMAP | roadmap.md | 项目路线图 |
