# V5 Product-Grade PPT Generation Upgrade Plan

> 目标：在不推倒当前 V5 formal 流程的前提下，把“能生成 PPT 页面”升级为“能稳定生成参赛级路演 PPT 初稿”。  
> 核心策略：不再继续堆大段提示词，而是在 MiMo 主体区生成前增加表达决策、页面打法、图示结构、素材策略和设计质量门禁。

## 1. 背景与当前问题

当前 V5 已经具备完整链路：

- 问卷解析。
- 大纲生成。
- 页面内容富化。
- V5 formal shell。
- MiMo 主体区 HTML 生成。
- 图示提示词库注入。
- render audit 与修复。
- PPTX 与 preview 落盘。

但从 `task185` 的完整生成结果看，当前能力仍停留在“页面可看、图示更稳”的阶段，尚未达到产品级参赛 PPT。

主要问题不是单点 bug，而是系统缺少“设计生产线”的中间层：

- MiMo 直接从页面内容进入 HTML 设计，缺少页面表达决策。
- 图示逐渐规范，但页面仍缺少视觉焦点和叙事张力。
- 很多页像“一个图 + 一段话”，信息密度不稳定。
- 章节节奏太平，页面长相重复。
- 证据页、实操页、价值页缺少真实业务语境。
- 生成后审查偏技术可交付，缺少设计质量门禁。
- 失败页容易被降级为 formal V4 安全页，导致最终效果断层。

## 2. 产品级目标

### 2.1 生成目标

V5 升级后应稳定产出以下级别的 PPT 初稿：

- 不是模板套页，而是根据项目内容自动选择页面打法。
- 每页有清晰主结论，评委 1-3 秒能抓住重点。
- 图示规范、对称、可读，不错位、不溢出、不乱线。
- 内容密度刚好：页面只呈现重点，细节进入讲稿或备注。
- 重点页有主视觉：封面、目录、方案、架构、实操、价值、结尾至少形成 6-8 个视觉记忆点。
- 证据页有可信来源或明确素材缺口，不伪造真实证据。
- 整套 deck 有章节节奏，而不是每页都像浅色卡片。

### 2.2 产品指标

以完整智慧农业 39 页测试为第一验收样本，目标指标如下：

| 指标 | 当前问题 | 第一阶段目标 | 产品级目标 |
| --- | --- | --- | --- |
| 大面积兜底页 | 偶发 2-4 页降级 | 不超过 2 页 | 0 页或只允许素材缺失页软降级 |
| 图示错位/重叠 | 已下降但仍不稳定 | 关键图示页 90% 无明显错位 | 95% 以上 |
| 页面视觉焦点 | 多数页弱 | 70% 内容页有明确焦点文字 | 90% 以上 |
| 页面空散轻 | 较明显 | 重点页显著下降 | 普通页也保持合理密度 |
| 页面重复感 | 高 | 同章节内有 2-3 种变化 | 全 deck 有稳定节奏 |
| 证据可信度 | 政策/实操/价值页不足 | 明确证据位与缺口 | 能自动补素材或提示上传 |
| 人工可改性 | HTML 分散 | 产出结构化计划与审查报告 | 支持定点重跑单页 |

## 3. 设计原则

### 3.1 做什么

- 做“页面表达生产线”，不是继续堆万能 prompt。
- 做“打法库”，让每类页面有明确构图策略。
- 做“结构化 diagram JSON”，让 MiMo 按图示语法绘制。
- 做“生成前审稿”，在内容不足时先补结构。
- 做“设计质量门禁”，检查空、散、轻、无焦点、模板感。
- 做“可追踪中间产物”，方便定位一页为什么失败。
- 做“失败页分层返工”，而不是直接降级。

### 3.2 不做什么

- 不做本地固定模板套页。
- 不把本地 SVG 作为最终主图强塞给 MiMo。
- 不让 MiMo 完全自由决定每页表达方式。
- 不把所有页面都做成浅色卡片。
- 不用大段正文堆满页面来追求“内容详细”。
- 不在缺少真实素材时伪造政策截图、实操截图、真实数据来源。
- 不把所有失败都交给 HTML repair 盲修。

## 4. 目标流程

升级后的流程如下：

```text
问卷 / 素材
  ↓
大纲生成
  ↓
页面角色识别
  ↓
page_expression_plan
  ↓
内容压缩：页面重点 / 支撑点 / 讲稿 / 证据需求
  ↓
slide_playbook 选择
  ↓
diagram_type 分类
  ↓
diagram JSON 生成
  ↓
图片素材策略：已有素材 / AI 生成 / 缺口提示
  ↓
MiMo 主体区 HTML 生成
  ↓
设计质量门禁 + render audit
  ↓
失败页回到对应层重做
  ↓
preview / PPTX / 质量报告
```

核心变化是：MiMo 不再直接面对松散页面内容，而是面对明确的表达计划、页面打法、图示结构和质量标准。

## 5. 模块设计

## 5.1 Page Expression Plan

### 目标

在 MiMo 生成 HTML 前，为每页生成一份表达计划，回答：

- 这一页在整场路演里承担什么功能？
- 评委 3 秒内必须记住什么？
- 页面上应该出现哪些内容，哪些放进讲稿？
- 应该使用哪种主视觉？
- 信息密度应该是多少？
- 是否需要图示、证据、图片、指标或对比？

### 数据结构

建议新增 `app/services/ppt/v5/expression_planner.py`。

核心输出：

```json
{
  "page_index": 24,
  "page_role": "technical_proof",
  "audience_question": "这个系统是否真的从数据到决策跑通了？",
  "one_sentence_takeaway": "从传感器采集到生产反馈形成可追溯技术闭环。",
  "visual_focus_text": "数据可追溯，决策可落地",
  "content_density": "medium_high",
  "primary_visual_type": "evidence_chain",
  "secondary_blocks": [
    "源头可信",
    "过程可追溯",
    "结果可验证",
    "价值可落地"
  ],
  "speaker_notes_brief": "讲解时补充每个节点对应的日志、截图或演示步骤。",
  "evidence_needs": [
    {
      "type": "operation_log",
      "required": true,
      "fallback": "use_evidence_placeholder_without_fake_source"
    }
  ],
  "avoid_patterns": [
    "普通横向节点链",
    "单图加一句话",
    "无主结论大留白"
  ]
}
```

### 分类枚举

`page_role` 建议从以下枚举开始：

- `opening_hook`
- `agenda_map`
- `policy_context`
- `problem_pressure`
- `solution_overview`
- `business_value_loop`
- `technical_architecture`
- `data_pipeline`
- `algorithm_proof`
- `feature_showcase`
- `practice_demo`
- `technical_evidence`
- `risk_control`
- `economic_value`
- `innovation_summary`
- `team_execution`
- `roadmap`
- `closing_memory`

### 实现方式

第一版采用规则 + LLM 混合：

- 规则从 `page_type`、`slide_role`、`title`、`section`、`chart.type` 判断大类。
- LLM 用于生成 `one_sentence_takeaway`、`visual_focus_text`、`secondary_blocks`。
- 对关键页强制更高质量：封面、目录、方案、架构、实操、价值、结尾。

### 接入点

在 `app/services/ppt/v5/clean_pipeline.py` 或当前页面富化完成后插入：

```text
outline pages
  → build_page_expression_plans()
  → build_design_contracts()
  → ai_passes body generation
```

## 5.2 Slide Playbook Library

### 目标

建立页面类型打法库，解决“每页怎么设计”的问题。图示库只解决“图怎么画”，打法库解决“整页怎么赢”。

### 建议文件

- `docs/v5_slide_playbook_library.md`
- `docs/v5_slide_playbook_library.json`
- `app/services/ppt/v5/slide_playbook_library.py`

### 首批打法类型

| Playbook | 用途 | 核心要求 |
| --- | --- | --- |
| `cover_key_visual` | 封面 | 强主视觉、项目品牌感、少字、高记忆点 |
| `agenda_story_map` | 目录 | 用路线图/章节地图展示整场逻辑 |
| `policy_evidence_board` | 政策背景 | 官方证据 + 项目承接，不做资料罗列 |
| `problem_pressure_wall` | 痛点 | 场景 + 数据 + 冲突，不做普通卡片 |
| `solution_big_picture` | 解决方案 | 一个主图讲清端到端方案 |
| `architecture_system_map` | 技术架构 | 系统边界、分层、数据流、职责 |
| `data_pipeline_trace` | 数据流 | 输入、清洗、分析、输出、反馈 |
| `algorithm_proof_panel` | 算法 | 输入、模型、输出、验证指标 |
| `practice_demo_stage` | 实操演示 | 现场感、步骤、结果、证据 |
| `evidence_chain_proof` | 证据链 | 证据节点与证明逻辑一一对应 |
| `metric_dashboard_focus` | 指标看板 | 一个主指标 + 3-5 个支撑指标 |
| `risk_response_matrix` | 风险预案 | 风险、触发、响应、恢复 |
| `economic_value_calculation` | 经济价值 | 公式、参数、结果、适用场景 |
| `innovation_comparison` | 创新点 | 旧方法 vs 新方法，突出差异 |
| `team_execution_map` | 团队协作 | 分工、协作流、交付能力 |
| `closing_memory_point` | 结尾 | 一句记忆点 + 项目价值回收 |

### 每个 Playbook 的字段

```json
{
  "id": "architecture_system_map",
  "applies_to": ["technical_architecture"],
  "design_goal": "让评委相信系统是完整、可实现、可运行的工程体系。",
  "recommended_compositions": [
    "layered_architecture",
    "center_system_with_side_evidence",
    "three_zone_data_flow"
  ],
  "must_include": [
    "系统边界",
    "输入输出",
    "核心模块职责",
    "数据流方向",
    "关键可信证据"
  ],
  "forbid": [
    "只有模块名的卡片堆叠",
    "没有箭头方向",
    "超过 6 个同级节点",
    "无主结论"
  ],
  "text_budget": {
    "focus_text_max_chars": 18,
    "support_blocks": "3-5",
    "body_text_max_chars": 140
  },
  "visual_density": "medium_high",
  "quality_checks": [
    "3 秒内能看出系统如何流动",
    "主路径比辅助信息更显眼",
    "没有孤立节点"
  ]
}
```

## 5.3 Content Compression And Speaker Notes Split

### 目标

解决“页面文字过多”和“页面太空”同时存在的问题。

### 核心规则

每页内容拆为四层：

- `on_slide_focus`：页面最重要的一句话。
- `on_slide_supports`：2-4 个支撑点。
- `evidence_payload`：图示、数据、截图、来源。
- `speaker_notes`：讲稿，不挤到页面。

### 输出示例

```json
{
  "on_slide_focus": "数据从采集到反馈形成闭环，支撑可追溯决策。",
  "on_slide_supports": [
    "源头：传感器采集日志",
    "过程：边缘过滤与云端分析",
    "结果：模型看板输出建议",
    "反馈：农事动作回写"
  ],
  "evidence_payload": [
    {
      "type": "log",
      "label": "采集日志",
      "availability": "missing",
      "fallback_display": "证据占位，不伪造"
    }
  ],
  "speaker_notes": "本页讲解时按四个环节说明数据如何进入平台、如何被过滤、如何进入模型、如何变成可执行建议。"
}
```

### 接入点

该输出应成为 `page_expression_plan` 的一部分，并传给 MiMo。

## 5.4 Diagram JSON Generator

### 目标

在现有 `v5_diagram_prompt_library` 基础上，进一步从“注入图示提示词”升级为“先生成图示结构 JSON，再让 MiMo 渲染”。

### 当前已有基础

- `docs/v5_diagram_prompt_library.json`
- `app/services/ppt/v5/diagram_prompt_library.py`
- `design_contracts.py` 已注入 `diagram_prompt_contract`
- `ai_passes.py` 已把 contract 给 MiMo

### 需要新增

建议新增：

- `app/services/ppt/v5/diagram_spec_builder.py`

输出结构：

```json
{
  "diagram_type": "evidence_chain",
  "layout": "center_path_with_evidence_cards",
  "core_message": "数据可追溯，决策可落地",
  "nodes": [
    {
      "id": "sensor",
      "label": "传感器采集",
      "role": "source",
      "support_text": "采集日志",
      "importance": "high"
    },
    {
      "id": "edge",
      "label": "边缘清洗",
      "role": "process",
      "support_text": "异常过滤结果",
      "importance": "medium"
    }
  ],
  "connections": [
    {
      "from": "sensor",
      "to": "edge",
      "label": "原始数据",
      "style": "solid"
    }
  ],
  "visual_rules": {
    "must_be_symmetric": true,
    "max_nodes": 5,
    "no_crossing_lines": true,
    "main_path_must_be_prominent": true,
    "prefer_html_css_shapes": true,
    "svg_allowed": true,
    "freeform_paths_max": 2
  }
}
```

### 图示类型策略

优先使用 HTML/CSS 容易稳定绘制的结构：

- 对称流程。
- 三层架构。
- 中心辐射。
- 2x2 矩阵。
- 主指标仪表盘。
- 横向阶段轴。
- 左右对比。
- 金字塔。
- 环形闭环。

谨慎使用：

- 大量曲线。
- 自由手绘路径。
- 超过 7 个节点的复杂网络。
- 多层嵌套连接线。
- 蜘蛛网图。

## 5.5 Material Strategy

### 目标

让页面需要图片时有清晰策略：

- 有真实素材则优先使用。
- 缺少素材但可生成视觉氛围图，则调用图片生成。
- 缺少政策/实操/日志这类真实性证据时，不伪造，只生成明确的证据占位或提示上传。

### 素材类型

| 类型 | 能否 AI 生成 | 说明 |
| --- | --- | --- |
| 封面氛围主视觉 | 可以 | 行业场景、科技感、产品隐喻 |
| 目录背景图 | 可以 | 抽象路线、场景地图、行业纹理 |
| 场景示意图 | 可以 | 农田、工厂、校园、医疗等场景 |
| 政策文件截图 | 不可以伪造 | 必须用户上传或真实抓取 |
| 实操日志截图 | 不可以伪造 | 必须用户上传或系统真实产生 |
| 产品界面截图 | 可以用原型示意，但必须标注示意 | 避免冒充真实产品 |
| 团队照片 | 不可以伪造真人 | 可用抽象协作视觉 |

### 建议新增文件

- `app/services/ppt/v5/material_strategy.py`
- `app/services/ppt/v5/image_generation_client.py`

图片生成接入用户提供的 DashScope `qwen-image-2.0-pro`，并复用程序里 Qwen 模型相同 key。

### 输出结构

```json
{
  "page_index": 1,
  "image_strategy": "generate_atmosphere_visual",
  "prompt": "A premium keynote cover visual for smart agriculture IoT...",
  "must_not_generate": [
    "fake policy document",
    "fake dashboard screenshot",
    "fake real person"
  ],
  "asset_status": "pending_generation"
}
```

## 5.6 MiMo Body Prompt Upgrade

### 目标

让 `ai_passes.py` 的主体区 prompt 从“要求 MiMo 做好看”升级为“按表达计划、打法、图示结构执行”。

### 输入应包含

- `page_expression_plan`
- `slide_playbook`
- `content_brief`
- `diagram_spec`
- `diagram_prompt_contract`
- `material_strategy`
- `design_quality_requirements`

### Prompt 关键规则

MiMo 必须：

- 先遵守 `one_sentence_takeaway`。
- 页面必须有 `data-focus-text`。
- 主视觉必须服务 `primary_visual_type`。
- 图示必须遵守 `diagram_spec.nodes/connections/visual_rules`。
- 不得把 speaker notes 放到页面上。
- 不得伪造证据。
- 不得用单调卡片堆叠替代图示。
- 不得让所有节点同权重。
- 不得创建二次画布、巨大圆角白卡、无意义大留白。

## 5.7 Design Quality Gate

### 目标

新增设计审查，不只检查 HTML 是否溢出，还检查页面是否像专业 PPT。

### 建议新增

- `app/services/ppt/v5/design_quality_auditor.py`

### 审查维度

```json
{
  "has_focus_text": true,
  "focus_visible_in_3_seconds": true,
  "content_density": "balanced",
  "visual_hierarchy": "clear",
  "diagram_serves_argument": true,
  "blank_space_issue": false,
  "template_like_issue": false,
  "too_many_equal_cards": false,
  "evidence_fake_risk": false,
  "page_similarity_risk": false,
  "repair_route": "pass"
}
```

### 失败类型与返工路径

| 失败类型 | 返工层级 |
| --- | --- |
| 缺少主结论 | 回到 `page_expression_plan` |
| 图示语义不清 | 回到 `diagram_spec_builder` |
| 页面太空 | 回到 `content_compression` 补支撑点 |
| 页面太挤 | 回到 `content_compression` 减少上屏文本 |
| 视觉模板感强 | 换 `slide_playbook` 或 composition |
| 证据缺失 | 进入 `material_strategy` |
| HTML 溢出 | 进入 render repair |

关键原则：方向错了不要修 HTML，要回到表达层重做。

## 5.8 Failure Handling

### 当前问题

`task185` 中第 2、22、35 页被降级为 formal V4 安全页。降级虽然保证可导出，但会让最终 deck 视觉断层。

### 新策略

降级前增加分层重试：

```text
MiMo body fail
  ↓
HTML repair once
  ↓
如果仍失败，判断失败类型
  ↓
表达问题 → 重做 expression plan
图示问题 → 重做 diagram spec
素材问题 → 启用 material strategy
布局问题 → 换 playbook composition
  ↓
重新生成 MiMo body
  ↓
仍失败才进入 soft fallback
```

### Soft Fallback 要求

如果最终必须 fallback，也不能回到普通 V4 安全页，而应使用对应 playbook 的安全版：

- 目录页 fallback 仍应像目录。
- 实操页 fallback 仍应有演示证据结构。
- 团队页 fallback 仍应有分工与协作图。

## 6. 开发计划

## Phase 0：基线固定与诊断报告

### 目标

固定当前问题样本，作为后续升级的对照。

### 任务

- 保存 `task185` 的 PPTX、preview、contact sheet。
- 提取第 2、22、35 页降级原因。
- 提取第 10、12、24、27 页成功图示输入，作为正样本。
- 建立 `v5_generation_quality_report` 输出字段。

### 产物

- `output/v5_full_mimo_review/task185_diagram_prompt_library_final/`
- `docs/v5_task185_quality_diagnosis.md`

### 验收

- 能明确列出每页 `expression_plan / playbook / diagram_type / audit_result / fallback_reason`。

## Phase 1：Page Expression Plan

### 目标

每页生成前先有表达计划。

### 开发任务

- 新增 `expression_planner.py`。
- 新增 `PageExpressionPlan` schema。
- 将计划注入 `design_contracts.py` 或页面 enriched JSON。
- 更新 `ai_passes.py`，把 expression plan 放入 MiMo prompt。
- 增加单测。

### 重点页面

- 1 封面。
- 2 目录。
- 8-10 方案与架构。
- 18-24 实操。
- 29-32 价值。
- 37-39 收尾。

### 验收

- 每页都有 `one_sentence_takeaway`。
- 每个内容页都有 `visual_focus_text`。
- 目录页不再被识别成普通内容页。
- 页面上屏文字明显减少但信息不空。

## Phase 2：Slide Playbook Library

### 目标

让每类页面有明确构图打法。

### 开发任务

- 新增 `docs/v5_slide_playbook_library.json`。
- 新增 `docs/v5_slide_playbook_library.md`。
- 新增 `slide_playbook_library.py`。
- 建立 `classify_slide_playbook(page, expression_plan)`。
- 将 playbook 注入 MiMo prompt。
- 对封面、目录、架构、实操、价值、结尾先强制使用 playbook。

### 验收

- 第 2 页目录必须是 `agenda_story_map`。
- 第 10 页架构必须是 `architecture_system_map`。
- 第 24 页证据链必须是 `evidence_chain_proof`。
- 第 30 页经济价值必须是 `economic_value_calculation`。
- 同章节页面不再全部长成浅色卡片。

## Phase 3：Diagram JSON Builder

### 目标

图示从“提示词约束”升级为“结构 JSON 约束”。

### 开发任务

- 新增 `diagram_spec_builder.py`。
- 复用 `v5_diagram_prompt_library.json`。
- 为首批 8 类图生成 spec：
  - `architecture`
  - `data_flow`
  - `evidence_chain`
  - `flowchart`
  - `metric_dashboard`
  - `comparison_matrix`
  - `risk_matrix`
  - `value_loop`
- 更新 `design_contracts.py`，加入 `diagram_spec`。
- 更新 `ai_passes.py`，要求 MiMo 按 spec 绘图。
- 增加 HTML 稳定性规则：对称、少曲线、少自由路径、节点上限。

### 验收

- 架构、流程、证据链、风险矩阵不再出现线乱、框乱、重叠。
- 第 24 页不能再出现大片空白主图。
- 每个 diagram spec 都能追溯到页面主结论。

## Phase 4：Material Strategy And Image Generation

### 目标

为封面、目录、场景页补主视觉；为证据页标记真实素材缺口。

### 开发任务

- 新增 `material_strategy.py`。
- 新增 `image_generation_client.py`。
- 接入 DashScope `qwen-image-2.0-pro`。
- 配置开关：
  - `PPT_V5_ENABLE_IMAGE_GENERATION`
  - `PPT_V5_IMAGE_GENERATION_MODEL`
  - `PPT_V5_IMAGE_GENERATION_WATERMARK`
- 封面和目录默认允许生成氛围图。
- 政策截图、实操截图、真实日志禁止伪造。
- 生成资产写入 `uploads/ppt/assets/task_{id}/generated/`。

### 验收

- 封面不再是纯背景标题页。
- 目录页有视觉仪式感。
- 缺真实证据时不会生成假截图。
- 质量报告能提示用户需要补哪些真实素材。

## Phase 5：Design Quality Auditor

### 目标

新增专业 PPT 审查门禁。

### 开发任务

- 新增 `design_quality_auditor.py`。
- 基于 HTML DOM、截图检测和启发式规则审查：
  - 主焦点。
  - 信息密度。
  - 空白比例。
  - 卡片数量。
  - 图文关系。
  - 页面相似度。
  - 占位词。
  - 跨行业污染。
- 设计失败时返回 `repair_route`。
- 将审查结果写入任务报告。

### 验收

- 能识别“一个图 + 一句话”的空页。
- 能识别“太多同权重卡片”的平庸页。
- 能识别“缺主结论”的页面。
- 能识别目录页、实操页、价值页是否跑偏。

## Phase 6：Layered Repair And Soft Fallback

### 目标

减少 formal V4 降级造成的视觉断层。

### 开发任务

- 改造 render audit repair。
- 增加失败类型分类。
- 根据失败类型回到对应层：
  - expression plan。
  - playbook。
  - diagram spec。
  - material strategy。
  - body HTML repair。
- 新增 playbook-safe fallback。
- 禁止目录、封面、实操关键页直接降级到普通 V4。

### 验收

- 智慧农业 39 页中普通 V4 降级页不超过 1 页。
- 第 2、22、35 页不再出现明显视觉断层。
- fallback 页仍保留页面角色。

## Phase 7：Single Page Rerun And Product Debug UI

### 目标

让功能可产品化调试，不需要每次完整重跑。

### 开发任务

- 支持按页重跑：
  - 重跑 expression plan。
  - 重跑 playbook。
  - 重跑 diagram spec。
  - 重跑 body HTML。
  - 重跑 render audit。
- 质量报告显示每页中间产物。
- 支持选择“保守 / 平衡 / 冲击力”设计模式。

### 验收

- 能只重跑第 24 页并保留其他页。
- 能查看第 24 页为什么选 evidence_chain。
- 能查看 MiMo 输入和审查失败原因。

## 7. 代码落点

### 新增文件

```text
docs/v5_slide_playbook_library.md
docs/v5_slide_playbook_library.json
docs/v5_product_grade_ppt_generation_upgrade_plan.md

app/services/ppt/v5/expression_planner.py
app/services/ppt/v5/slide_playbook_library.py
app/services/ppt/v5/diagram_spec_builder.py
app/services/ppt/v5/material_strategy.py
app/services/ppt/v5/image_generation_client.py
app/services/ppt/v5/design_quality_auditor.py
```

### 修改文件

```text
app/services/ppt/v5/clean_pipeline.py
app/services/ppt/v5/design_contracts.py
app/services/ppt/v5/ai_passes.py
app/services/ppt/v5/render_layout_auditor.py
app/services/ppt/v5/body_layout_auditor.py
app/services/ppt/v5/repair_planner.py
qa/run_questionnaire_full_flow.py
tests/test_v5_clean_pipeline.py
```

## 8. 数据产物与可观测性

每次完整生成应落盘：

```text
task_{id}_generation_trace.json
task_{id}_page_expression_plans.json
task_{id}_slide_playbooks.json
task_{id}_diagram_specs.json
task_{id}_material_strategy.json
task_{id}_design_quality_report.json
```

每页至少记录：

- page index。
- page title。
- page role。
- selected playbook。
- selected diagram type。
- diagram spec。
- image strategy。
- MiMo attempt count。
- audit result。
- repair route。
- final status。
- fallback reason。

这对产品化很重要，因为用户发现一页不好时，系统必须能解释“为什么生成成这样”。

## 9. 测试计划

### 9.1 单元测试

- `expression_planner` 分类准确性。
- `slide_playbook_library` 加载与匹配。
- `diagram_spec_builder` 输出合法性。
- `material_strategy` 禁止伪造真实证据。
- `design_quality_auditor` 能识别典型失败页。

### 9.2 集成测试

使用智慧农业问卷：

```text
/Users/liuyixing/Downloads/test_questionnaire_智慧农业.json
```

每个 Phase 后都跑：

- 目标页重跑：2、10、12、22、24、27、30、35。
- 完整 V5 formal 重跑。
- 生成 contact sheet。
- 对比 task185。

### 9.3 视觉验收样本

固定以下页面作为重点：

| 页码 | 页面 | 验收重点 |
| --- | --- | --- |
| 1 | 封面 | 是否有项目级主视觉 |
| 2 | 目录 | 是否像路演地图 |
| 10 | 架构 | 是否系统边界清晰 |
| 12 | 数据流 | 是否路径清楚 |
| 18 | 实操总览 | 是否有演示节奏 |
| 22 | 结果展示 | 是否避免降级和占位 |
| 24 | 证据链 | 是否有强主图和清晰闭环 |
| 27 | 风险预案 | 是否无跨行业污染 |
| 30 | 经济价值 | 是否有计算逻辑 |
| 35 | 团队协作 | 是否避免降级 |
| 39 | 结尾 | 是否有记忆点 |

## 10. 里程碑

### M1：表达计划可用

时间：1-2 天。

完成：

- `expression_planner.py`
- MiMo prompt 注入 expression plan。
- 智慧农业目标页重跑。

预期效果：

- 页面主结论更明确。
- 空页减少。
- 页面文字更克制。

### M2：打法库可用

时间：2-3 天。

完成：

- `slide_playbook_library`
- 首批 16 个 playbook。
- 封面、目录、架构、实操、价值重点优化。

预期效果：

- 页面重复感下降。
- 目录、封面、实操页不再像普通卡片页。

### M3：图示结构化可用

时间：2-3 天。

完成：

- `diagram_spec_builder`
- 8 类 diagram spec。
- MiMo 强制按 spec 绘制。

预期效果：

- 图示稳定性继续提高。
- 第 24 页这类重要图不再空散。

### M4：素材策略与图片生成可用

时间：2-4 天。

完成：

- DashScope 图片生成接入。
- 封面、目录、场景页使用 AI 视觉资产。
- 证据素材缺口报告。

预期效果：

- 封面和目录视觉显著增强。
- 不再靠纯背景和卡片撑页面。

### M5：设计质量门禁可用

时间：3-5 天。

完成：

- `design_quality_auditor`
- 分层 repair。
- playbook-safe fallback。

预期效果：

- 大幅减少不合格页面落盘。
- 降级页减少。
- 最终 preview 更稳定。

## 11. 第一轮实施建议

不建议一次性全做。最优先的一轮应该是：

1. 做 `expression_planner.py`。
2. 做 `slide_playbook_library.py` 和 JSON。
3. 做 `diagram_spec_builder.py`。
4. 改 `ai_passes.py` prompt 输入结构。
5. 跑目标页 `2、10、12、22、24、27、30、35`。
6. 再跑完整智慧农业 V5 formal。

原因：

- 这三层直接解决当前最痛的问题：空、散、轻、图示弱、页面重复。
- 不依赖图片生成模型，落地最快。
- 能马上验证 MiMo 是否按新结构变好。

图片生成和设计质量门禁放第二轮，因为它们需要更多工程集成和稳定性测试。

## 12. 成功判定

第一轮成功不是“生成一套完美 PPT”，而是满足：

- 第 2 页不再降级为普通安全页。
- 第 24 页不再显得空，图示能承担核心证明功能。
- 第 10、12、27 页图示保持稳定且更有层级。
- 第 30 页经济价值出现计算逻辑，而不是孤立数字。
- 整套 deck 至少 70% 页面有明确焦点文字。
- contact sheet 上能看出章节节奏差异。

最终产品级成功标准：

- 用户上传问卷和基础素材后，系统能生成一套可用于人工精修的比赛 PPT 初稿。
- 人工主要改内容真实性和素材，不再大量修版式、重画图、救错位。
- 每页生成结果可解释、可重跑、可定位失败原因。

