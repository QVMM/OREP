# 路演 PPT 现场执行优化方案与开发步骤

依据：`competition_video_field_analysis.md`

## 1. 本轮优化目标

把路演 PPT 生成从“比赛主题 PPT”推进到“能支撑比赛现场的 PPT”。本轮不先重做 SVG 视觉系统，而是优先补齐现场执行结构，让后续视觉生成有正确输入。

核心目标：

1. 生成五大板块主线：项目介绍、总体思路、技能要点、主要成果、项目创新。
2. 每个核心模块形成技能展示链：功能价值说明 -> 关键技术/代码还原 -> 产品效果测试 -> 模块小结。
3. 每页具备现场执行字段：谁讲、谁操作、显示在哪个屏幕、操作什么、成功判据是什么、失败怎么恢复。
4. 正式导出时拦截无来源成果数据、无故障恢复、无代码/实现解释的比赛稿。

## 2. 开发步骤

### Step 1：新增 FieldRunOfShowAgent

在 `roadshow_agent.py` 的大纲之后、manuscript 之前新增现场执行分镜阶段。

输出内容：

- site setup：主屏、副屏、设备区、操作席、网络与备用素材。
- competition blocks：五大板块、时长、页码范围和评分支撑。
- module demo pattern：核心模块的价值、代码/实现、产品测试和成功判据。
- segment run-of-show：逐段时长、角色、口令、屏幕状态、fallback。
- evidence/result claims：证据和成果数据来源。

### Step 2：扩展 Manuscript 合同

每页在原有视觉字段基础上新增：

- `stage_mode`
- `display_target`
- `time_budget_sec`
- `speaker_role`
- `operator_role`
- `operator_action`
- `expected_screen_state`
- `fallback_plan`
- `module_flow`
- `acceptance_signal`
- `command_cue`

这些字段主要用于后续设计和讲稿，不应作为内部字段名直接显示在成品页。

### Step 3：强化 Strategist 约束

Roadshow strategist 必须理解：

- 比赛 PPT 更像 live operation console。
- 代码页要展示关键片段和标注，不整屏堆代码。
- 产品测试页要展示当前操作、预期屏幕、成功判据、证据和 fallback。
- 成果页必须区分已验证指标和待补充数据。

### Step 4：强化正式导出门禁

正式导出前阻断：

- 缺现场执行字段。
- 核心技能模块无代码还原或实现解释。
- 现场实操无故障恢复/复测方案。
- 成果百分比、金额、推广数量无来源。
- 实操/证据/数据页仍有待补充。

## 3. 本轮改动文件

- `ai-scoring/app/services/ppt/agent/backend/orchestrator/roadshow_agent.py`
- `ai-scoring/app/services/ppt/agent/backend/orchestrator/roadshow_quality.py`
- `ai-scoring/app/services/ppt/agent/backend/orchestrator/strategist_agent.py`

## 4. 验收标准

快速验证 8 页也应能看到：

1. 开场安全/环境确认。
2. 五大板块主线。
3. 至少一个核心模块包含代码/实现解释。
4. 至少一个产品测试页包含 `acceptance_signal` 和 `command_cue`。
5. 至少一个实操页包含可执行 `fallback_plan`。

正式版 35-45 页应进一步满足：

1. 每个核心模块都有价值、技术/代码、产品测试、模块小结。
2. 成果数据都有来源或标记待补充。
3. 团队分工以匿名岗位角色和口令式协作体现。
4. 无个人信息、学校、电话、邮箱等敏感内容。
