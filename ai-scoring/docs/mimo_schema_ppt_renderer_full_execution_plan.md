# MiMo Schema PPT Renderer Full Execution Plan

## 0. 背景与核心结论

当前 V5 的根本问题不是某几个页面失败，而是生成权力分配不合理：

```text
MiMo 同时负责内容理解、表达判断、页面布局、SVG 绘制、HTML 落版
```

这会导致：

- MiMo 一次性处理文字、架构图、流程图、图片证据、留白、重心，稳定性差。
- 页面容易出现越界、重叠、小字、二次白板、网页感容器。
- 如果改成本地固定模板，又会变成所有用户 PPT 长得一样，产品上限很低。

新的方向不是“系统套模板”，也不是“MiMo 放飞”，而是：

```text
MiMo 负责专业判断与语义规划
系统负责确定性排版、专业图解渲染、质量审查和返工调度
```

更准确地说：

```text
MiMo = 内容导演 + 表达策划 + 图解语义设计
系统 = PPT 排版物理引擎 + SVG 图解编译器 + 视觉质量门禁
```

这份文档是完整执行方案，重点解决 5 个问题：

1. 系统清洗/去重/提炼如何不损伤内容。
2. MiMo 如何具备全局、比赛、裁判、架构师、编辑视角。
3. Composition Intent 如何足够专业、丰富，避免画出平庸图。
4. Layout Solver 如何真实计算文字、图片、图解面积，避免溢出和低质。
5. 每个流程用什么技术、如何衔接、如何并发、如何分阶段落地。

---

## 1. 总体链路

最终生成链路：

```text
用户问卷 / 原始材料
  ↓
Round 1/2/3 内容生成
  ↓
Content Ledger 内容账本
  ↓
Content Understanding & Preservation Pass
  ↓
Deck Strategy Pass
  ↓
Competition Judge Pass
  ↓
Page Expression Planner
  ↓
Composition Intent Planner
  ↓
Diagram Schema Planner
  ↓
Layout Solver
  ↓
PPT SVG Renderer
  ↓
Safe Region Page Renderer
  ↓
Visual Auditor
  ↓
Layered Repair Loop
  ↓
Preview / PPTX
```

其中最重要的变化：

- MiMo 不直接输出整页 HTML。
- MiMo 不直接控制最终坐标。
- MiMo 不直接自由绘制复杂 SVG。
- 系统不使用固定整页模板。
- 系统使用可变构图、确定性几何、专业图解组件和审查规则。

---

## 2. 内容不受损机制

### 2.1 问题

“系统清洗/去重/提炼”如果做得粗暴，会损伤内容：

- 把关键证明删掉。
- 把参赛项目特色磨平。
- 把原始素材里的真实细节改成空泛表达。
- 把裁判关心的实操证据删掉。
- 把技术严谨性削弱。

所以清洗不能是普通摘要，也不能是简单去重。

### 2.2 解决方案：Content Ledger 内容账本

系统必须先建立不可变内容账本。

每条内容都带来源、用途、状态，不直接覆盖原文。

```json
{
  "content_id": "p11_fact_03",
  "source": "round3_enriched",
  "source_page": 11,
  "raw_text": "边缘网关完成 MQTT、LoRa、HTTP 多协议适配，并对异常数据进行本地预警。",
  "semantic_type": "technical_fact",
  "evidence_role": "supports_architecture",
  "competition_value": "shows_practical_feasibility",
  "importance": "high",
  "status": "active",
  "used_in": []
}
```

### 2.3 清洗不是删除，而是分层保留

内容处理分 4 层：

```text
Raw Layer
原始内容，永不删除。

Canonical Layer
清理错别字、提示词污染、重复句，但保留含义。

Slide Layer
适合放到页面上的短表达。

Speaker Layer
不适合放页面但适合讲解的内容，转入讲稿或备注。
```

示例：

```json
{
  "raw": "边缘网关完成 MQTT、LoRa、HTTP 多协议适配，并对异常数据进行本地预警。",
  "canonical": "边缘网关支持 MQTT、LoRa、HTTP 多协议适配，并完成本地异常预警。",
  "slide_text": "多协议适配 + 本地预警",
  "speaker_note": "这里强调边缘网关不是单纯转发，而是完成协议适配、预处理和异常预警。"
}
```

页面内容变短，但信息不丢。

### 2.4 内容保护规则

任何清洗、去重、提炼必须通过内容保护规则：

```text
1. high importance 内容不能直接删除，只能转移到 speaker_note 或旁注。
2. evidence_role 为 proof / result / practice 的内容不能被摘要成空泛口号。
3. 技术名词、指标、专利、证书、政策文件名必须原样保留或建立别名映射。
4. 删除重复内容时必须记录 duplicate_of。
5. 每页至少保留 1 个核心论点、2-4 个支撑点或 1 个强证据。
6. 如果内容太多，优先拆页或移讲稿，不允许压成小字。
```

### 2.5 内容质量审查

新增 `content_preservation_auditor`。

检查：

```text
原始 high importance 内容是否仍有去向
技术名词是否被误删
实操证据是否保留
指标/证书/政策是否保留
页面是否从具体内容退化成空泛表达
```

输出：

```json
{
  "pass": false,
  "issues": [
    "实操现场证据被删除且未转入 speaker_note",
    "核心技术名词 LoRa 被清洗过程移除"
  ],
  "required_action": "restore_or_move_to_notes"
}
```

### 2.6 技术实现

模块建议：

```text
app/services/ppt/v6/content_ledger.py
app/services/ppt/v6/content_preservation.py
app/services/ppt/v6/content_preservation_auditor.py
```

数据模型使用 Pydantic：

```python
class ContentAtom(BaseModel):
    content_id: str
    source: str
    raw_text: str
    canonical_text: str | None = None
    slide_text: str | None = None
    speaker_note: str | None = None
    semantic_type: Literal[
        "claim", "technical_fact", "metric", "evidence",
        "practice_step", "risk", "value", "policy", "team"
    ]
    importance: Literal["critical", "high", "medium", "low"]
    evidence_role: str | None = None
    status: Literal["active", "merged", "moved_to_notes", "discarded"]
    duplicate_of: str | None = None
```

---

## 3. MiMo 判断视角如何专业化

### 3.1 问题

不能只问 MiMo：

```text
这一页适合什么布局？
```

因为它可能只从网页设计或普通 PPT 角度判断，不一定具备：

- 全局 deck 眼光。
- 职业院校技能大赛眼光。
- 裁判评分表眼光。
- 优秀架构师眼光。
- 优秀编辑眼光。
- 反向审查眼光。

### 3.2 解决方案：多角色判断，不是单 prompt 判断

引入 5 个判断 pass：

```text
Deck Strategist
从整套 PPT 叙事、节奏、章节结构判断页面职责。

Competition Judge
从职业院校技能大赛评分和裁判关注点判断页面是否有证明力。

Technical Architect
从技术真实性、架构合理性、工程闭环判断页面表达。

Editorial Director
从表达清晰度、删减、重点、标题副标题判断。

Reverse Reviewer
从裁判挑刺角度反向审查：哪里空泛、哪里像编的、哪里证据不足。
```

这些 pass 不一定每页都请求 5 次 MiMo，可以通过一次 structured prompt 让 MiMo 按角色输出，也可以对关键页拆多次调用。

### 3.3 全局 Deck Strategy Pass

输入整份 outline 和问卷。

输出：

```json
{
  "deck_goal": "职业院校技能大赛路演：证明项目真实、可运行、有技术含量、有实操成果",
  "narrative_arc": [
    "问题与背景",
    "方案与技术",
    "实操与验证",
    "成果与价值",
    "团队与展望"
  ],
  "must_have_proofs": [
    "实操现场证据",
    "系统界面证据",
    "核心技术架构",
    "数据结果或指标",
    "团队分工和产教融合"
  ],
  "risk_flags": [
    "不要只讲概念",
    "不要缺少实操证据",
    "不要技术架构空泛",
    "不要成果无量化"
  ]
}
```

### 3.4 Competition Judge Pass

必须内置职业院校技能大赛评分视角。

评分维度建议：

```text
项目价值
技术实现
创新性
实操过程
成果证明
团队协作
表达展示
可推广性
```

输出：

```json
{
  "judge_expectation": "本页需要证明技术方案不是概念，而是可运行的工程实现。",
  "score_dimension": ["technical_feasibility", "practice_process"],
  "required_evidence": ["架构图", "系统截图", "实操步骤"],
  "judge_questions": [
    "数据从哪里来？",
    "边缘层具体做了什么？",
    "结果如何验证？"
  ],
  "page_risk": "如果只画模块卡片，会被认为技术表达空泛。"
}
```

### 3.5 Technical Architect Pass

判断技术页是否站得住。

输出：

```json
{
  "architecture_claim": "端-边-云三层协同",
  "must_show": [
    "数据采集入口",
    "边缘处理职责",
    "云端分析职责",
    "数据流向",
    "协议或接口"
  ],
  "avoid": [
    "只列技术名词",
    "没有数据流",
    "没有边界和职责"
  ]
}
```

### 3.6 Editorial Director Pass

判断页面是否可读、精炼、有重点。

输出：

```json
{
  "core_sentence": "端侧采集、边缘预处理、云端分析构成从数据到决策的闭环。",
  "slide_copy": [
    "端侧：多源采集",
    "边缘：协议适配与预警",
    "云端：AI 分析与看板"
  ],
  "speaker_notes": [
    "这里讲清楚三层不是堆技术，而是分工明确的数据闭环。"
  ],
  "remove_or_deemphasize": [
    "过长的背景解释",
    "重复的平台价值描述"
  ]
}
```

### 3.7 Reverse Reviewer Pass

反向挑刺。

输出：

```json
{
  "judge_objections": [
    "这页没有证明系统真的跑起来",
    "架构图如果没有数据流会显得像概念图",
    "如果没有截图或指标，成果说服力不足"
  ],
  "must_fix_before_render": [
    "补数据流箭头",
    "补一个系统界面证据位",
    "突出边缘层真实职责"
  ]
}
```

### 3.8 技术实现

模块建议：

```text
app/services/ppt/v6/deck_strategy_pass.py
app/services/ppt/v6/competition_judge_pass.py
app/services/ppt/v6/technical_architect_pass.py
app/services/ppt/v6/editorial_director_pass.py
app/services/ppt/v6/reverse_reviewer_pass.py
```

为了控制耗时：

```text
Deck Strategy: 每套 deck 1 次
Competition Judge: 每套 deck 1 次 + 关键页补充
Technical Architect: 仅技术/架构/流程页
Editorial Director: 每页轻量执行
Reverse Reviewer: 关键页 + 审查失败页
```

---

## 4. Composition Intent 必须升级为 Presentation Blueprint

### 4.1 问题

普通 composition intent 太薄：

```json
{
  "dominant_element": "architecture_diagram",
  "visual_weight": {"architecture_diagram": 0.55}
}
```

这不足以画出高级图。

如果信息不够丰富，系统 renderer 只能画出：

- 普通矩形。
- 普通箭头。
- 普通模块卡片。
- 平庸、单调、没有解释力的 SVG。

### 4.2 解决方案：Presentation Blueprint

Composition Intent 要升级成更完整的 `PresentationBlueprint`。

它不是只说明“放什么”，还必须说明：

```text
本页要证明什么
裁判会看什么
主视觉要解释什么关系
哪些节点必须突出
哪些标注必须出现
哪些证据必须绑定到哪个结论
图解应该是什么风格
哪些信息不能画成普通卡片
```

### 4.3 Blueprint Schema

```json
{
  "page_index": 11,
  "page_mission": "证明系统架构真实可运行，而不是概念堆叠",
  "judge_takeaway": "评委应理解数据如何从田间采集并转化为决策建议",
  "expression_type": "architecture_diagram",
  "dominant_question": "系统如何形成端-边-云数据闭环？",
  "main_visual": {
    "type": "layered_architecture",
    "must_explain": [
      "三层职责",
      "数据流向",
      "协议适配",
      "AI 分析位置",
      "可视化输出"
    ],
    "emphasis_nodes": ["边缘预警", "AI识别", "决策看板"],
    "required_annotations": [
      {
        "anchor": "边缘处理层",
        "text": "本地预警降低云端延迟",
        "importance": "high"
      },
      {
        "anchor": "云端平台层",
        "text": "统一分析与可视化决策",
        "importance": "medium"
      }
    ]
  },
  "supporting_regions": [
    {
      "type": "key_insight",
      "content": "端侧采集、边缘预处理、云端分析形成闭环。",
      "role": "summarize"
    },
    {
      "type": "evidence_badge",
      "content": "建议配系统界面截图",
      "role": "proof"
    }
  ],
  "visual_style": {
    "tone": "clean_tech",
    "depth": "moderate",
    "line_language": "precise_data_flow",
    "avoid": ["cartoon_icon", "web_card_grid", "generic_blocks"]
  },
  "content_budget": {
    "max_visible_text_blocks": 5,
    "max_words_per_label": 14,
    "min_visual_area_ratio": 0.42
  }
}
```

### 4.4 Blueprint 质量门槛

如果 Blueprint 只有泛泛描述，不能进入 render。

必须满足：

```text
有 page_mission
有 judge_takeaway
有 dominant_question
有 main_visual.must_explain
有 emphasis_nodes 或 required_annotations
有 content_budget
有 visual_style.avoid
```

否则返回 MiMo 重写 blueprint。

### 4.5 技术实现

模块：

```text
app/services/ppt/v6/presentation_blueprint.py
app/services/ppt/v6/blueprint_validator.py
app/services/ppt/v6/blueprint_prompt.py
```

Pydantic 模型：

```python
class PresentationBlueprint(BaseModel):
    page_index: int
    page_mission: str
    judge_takeaway: str
    expression_type: str
    dominant_question: str
    main_visual: MainVisualSpec
    supporting_regions: list[SupportingRegion]
    visual_style: VisualStyleSpec
    content_budget: ContentBudget
```

---

## 5. Layout Solver 不能靠拍脑袋

### 5.1 问题

简单按百分比分区不够。

例如：

```text
3 段文字，每段不长，但段落多
每段之间如果固定 12% gap
总高度仍然会溢出
```

所以 Layout Solver 不能只看元素数量和大概权重，必须做真实容量测量。

### 5.2 解决方案：Measure -> Generate -> Score -> Fit

Layout Solver 流程：

```text
1. Measure
   测量文字、图片、图解的最小/理想/最大尺寸

2. Generate
   生成多个候选布局

3. Score
   用视觉规则和物理规则打分

4. Fit
   如果装不下，执行压缩、合并、移旁注、拆页
```

### 5.3 文本测量

不能用粗略字数估算，必须有真实测量。

技术方式：

```text
Node Canvas / browser canvas measureText
或者 Playwright 在隐藏容器中测量 text bounding box
```

输入：

```json
{
  "text": "边缘网关支持 MQTT、LoRa、HTTP 多协议适配",
  "font_size": 18,
  "font_weight": 600,
  "max_width": 360,
  "line_height": 1.45
}
```

输出：

```json
{
  "line_count": 2,
  "measured_width": 328,
  "measured_height": 52,
  "fits": true
}
```

### 5.4 文本块不是固定 gap，而是弹性 stack

文字段落用 `TextStack`。

每个 TextStack 有：

```json
{
  "items": [
    {"text": "端侧多源采集", "priority": "high"},
    {"text": "边缘协议适配", "priority": "high"},
    {"text": "云端 AI 分析", "priority": "medium"}
  ],
  "gap_policy": {
    "ideal": 18,
    "min": 8,
    "max": 28
  },
  "font_policy": {
    "ideal": 18,
    "min": 15,
    "max": 22
  }
}
```

Fit 策略：

```text
先压缩 gap：18 -> 14 -> 10 -> 8
再减少低优先级文字
再把部分内容移到 speaker_note
再请求 layout solver 扩大区域
最后建议拆页
```

不允许直接把字号压到 10px。

### 5.5 图片区域计算

图片证据位按类型决定尺寸范围：

```json
{
  "system_screenshot": {
    "ratio": "16:9",
    "min_area": 0.18,
    "ideal_area": 0.28,
    "max_area": 0.45
  },
  "practice_photo": {
    "ratio": "4:3",
    "min_area": 0.16,
    "ideal_area": 0.25,
    "max_area": 0.38
  },
  "certificate": {
    "ratio": "3:4",
    "min_area": 0.10,
    "ideal_area": 0.18,
    "max_area": 0.26
  }
}
```

图片不能过小，否则不像证据；也不能过大，否则挤压图解和文字。

### 5.6 图解区域计算

每种 diagram type 有区域下限：

```json
{
  "layered_architecture": {
    "min_area": 0.38,
    "ideal_area": 0.52,
    "min_width": 760,
    "min_height": 390
  },
  "process_flow": {
    "min_area": 0.32,
    "ideal_area": 0.48,
    "min_width": 920,
    "min_height": 280
  },
  "evidence_board": {
    "min_area": 0.35,
    "ideal_area": 0.55
  }
}
```

如果给不到最小面积，不能硬画：

```text
扩大图解区域
减少辅助文字
换更紧凑图解
拆页
```

### 5.7 候选布局生成

不是固定模板，而是根据表达类型和元素数量生成候选。

例如 architecture_diagram：

```text
center_visual_right_notes
top_insight_center_visual
left_data_flow_right_layers
full_width_architecture_bottom_evidence
radial_core_with_side_annotations
```

每个候选都通过真实测量和评分。

### 5.8 评分模型

硬约束：

```text
不越界
不重叠
最小字号
图解最小面积
图片最小面积
页脚安全区
标题安全区
```

软评分：

```text
主视觉是否突出
留白是否合理
阅读路径是否清楚
页面重心是否稳定
同 deck 是否结构重复
视觉密度是否符合章节节奏
```

### 5.9 技术实现

模块：

```text
app/services/ppt/v6/layout_solver/
  __init__.py
  models.py
  text_measure.py
  region_generator.py
  candidate_scorer.py
  fit_engine.py
  rhythm_guard.py
```

推荐技术：

```text
Python + Pydantic: schema 和决策流
Playwright: 精准文字测量和最终截图审查
NumPy / 自研几何函数: overlap、area、alignment、density
Optional Node canvas: 更快 text measurement
```

---

## 6. PPT SVG Renderer 技术设计

### 6.1 核心原则

系统 SVG renderer 不能是普通矩形箭头生成器。

它必须是：

```text
schema-driven
theme-token-driven
region-aware
auditable
repairable
```

### 6.2 Renderer 架构

```text
DiagramSchema
  ↓
DiagramNormalizer
  ↓
DiagramLayoutEngine
  ↓
VisualTokenResolver
  ↓
SVGPrimitiveRenderer
  ↓
SVGInternalAuditor
  ↓
SVGOutput
```

### 6.3 Renderer 类型

首批：

```text
ArchitectureRenderer
ProcessFlowRenderer
EvidenceBoardRenderer
MetricDashboardRenderer
```

第二批：

```text
TimelineRenderer
RiskRadarRenderer
ComparisonMatrixRenderer
CollaborationMapRenderer
ValueChainRenderer
GanttRenderer
```

### 6.4 ArchitectureRenderer

支持布局：

```text
layered_vertical
layered_horizontal
hub_and_spoke
data_flow_pipeline
system_boundary_map
```

输入：

```json
{
  "diagram_type": "layered_architecture",
  "layers": [],
  "flows": [],
  "annotations": [],
  "emphasis": []
}
```

系统决定：

```text
层方向
每层高度
模块网格
箭头路径
标注位置
模块折叠
```

### 6.5 ProcessFlowRenderer

支持：

```text
horizontal_flow
vertical_flow
swimlane_flow
feedback_loop
input_output_chain
```

处理：

```text
步骤超过 6 个时合并低优先级步骤
反馈箭头自动走外侧
步骤说明超长时转为 tooltip-like PPT 注释，不进入主节点
```

### 6.6 EvidenceBoardRenderer

支持：

```text
primary_evidence_large
evidence_mosaic
system_screenshot_with_callouts
practice_photo_sequence
certificate_strip
```

必须区别：

```text
PPT 证据位 != 网页上传框
```

证据位包括：

```text
证据标题
建议图片类型
建议比例
证据用途
来源说明
裁切角标
```

### 6.7 Visual Tokens

视觉 token 由 deck DNA 生成。

示例：

```json
{
  "theme_family": "light_tech_competition",
  "palette": {
    "ink": "#0f172a",
    "muted": "rgba(15,23,42,.62)",
    "accent": "#2563eb",
    "accent_alt": "#0f766e",
    "surface": "rgba(255,255,255,.72)"
  },
  "diagram": {
    "stroke_width": 1.4,
    "node_radius": 16,
    "group_radius": 28,
    "shadow": "soft_depth",
    "gradient": "controlled_accent",
    "line_style": "precise_data_flow",
    "label_style": "technical_caption",
    "emphasis_style": "edge_glow"
  }
}
```

### 6.8 高级感如何保证

高级感不靠随机炫技，而靠：

```text
统一线宽
克制色彩
明确层级
主次对比
精确对齐
适度阴影
少量强调光效
高质量标注
真实信息密度
```

系统 renderer 需要内置“专业图解语法”：

```text
数据流线要细而明确
关键节点要有强调边或光晕
模块分组要有轻背景而非大白板
标注要贴近锚点而不是漂浮
箭头不能穿文字
证据位要像 PPT 裁切框
```

### 6.9 技术实现

模块：

```text
app/services/ppt/v6/svg_renderer/
  models.py
  tokens.py
  primitives.py
  architecture.py
  process_flow.py
  evidence_board.py
  metric_dashboard.py
  internal_auditor.py
```

推荐依赖：

```text
Python string/SVG builder: 首期自研，便于完全控制输出
svgwrite: 可选，但不强依赖
ELK / Graphviz: 后续可用于复杂 graph layout，不直接用于最终视觉
Playwright: 用于渲染后真实审查
```

首期不建议直接用 Mermaid 作为最终输出，因为视觉容易像技术文档，不像高质量路演 PPT。

---

## 7. 外部图解/布局技术选型

### 7.1 总体判断

外部库可以用，但不能把最终 PPT 视觉交给外部库直接输出。

原因：

```text
Mermaid / Graphviz 输出更像技术文档
ELK / Dagre 更擅长算布局，不擅长最终视觉表现
D3 很强但太底层，需要自研视觉语法
G2 / AntV 更适合数据图表，不适合所有 PPT 图解
```

因此生产链路应该是：

```text
MiMo 输出 PPT diagram schema
  ↓
ELK / Dagre / 自研算法计算节点坐标和边路由
  ↓
自研 PPT SVG theme renderer 负责最终视觉
  ↓
Visual Auditor 审查
```

而不是：

```text
MiMo 输出 Mermaid / DOT
  ↓
Mermaid / Graphviz 直接生成最终 SVG
```

### 7.2 技术角色分层

```text
Schema 层
MiMo 输出业务图解结构，不绑定 Mermaid/DOT/G6 等具体语法。

Layout 层
ELK / Dagre / 自研几何算法只负责算坐标、层级、边路由。

Render 层
自研 PPT SVG theme renderer 根据 layout result 和 visual tokens 生成最终 SVG。

Chart 层
G2 / AntV / D3 可用于折线、柱状、雷达、指标看板等局部图表。

Debug 层
Mermaid / Graphviz 可用于开发期快速验证 graph 结构，不作为最终视觉。
```

### 7.3 ELK

定位：

```text
工程级 graph layout engine
适合复杂节点、层级、端口、边路由
```

适用场景：

```text
复杂架构图
多层系统图
数据流图
协作关系图
模块依赖图
```

用途：

```text
进入生产候选
用于 Layout 层计算坐标和边路由
不直接负责视觉渲染
```

边界：

```text
ELK 输出的是布局结果，不是高级 PPT 视觉
需要系统把 ELK layout result 转成自研 SVG theme renderer 输入
```

生产链路建议：

```text
DiagramSchema
  ↓
ELKGraphAdapter
  ↓
ELK layout result
  ↓
PPTSvgThemeRenderer
```

优先级：

```text
P1 评估
P2 按需接入复杂 architecture / collaboration / flow 页面
```

### 7.4 Dagre

定位：

```text
轻量级 directed graph layout
适合有方向的流程图、链路图、简单架构图
```

适用场景：

```text
流程图
输入-处理-输出链路
简单数据流
步骤型实操流程
```

用途：

```text
进入生产候选
作为轻量 Layout 层
适合比 ELK 更简单、更快的页面
```

边界：

```text
不负责最终视觉
复杂端口、复杂边避让能力弱于 ELK
不适合直接输出成品 SVG
```

生产链路建议：

```text
ProcessFlowSchema
  ↓
DagreLayoutAdapter
  ↓
Flow coordinates
  ↓
PPTSvgThemeRenderer
```

优先级：

```text
P0/P1 可先接入
适合快速支撑 process_flow 和 simple architecture
```

### 7.5 D3

定位：

```text
底层数据驱动 SVG 工具
适合自定义图形、比例尺、路径、力导向、过渡计算
```

适用场景：

```text
自定义 SVG primitives
复杂路径生成
数据图表辅助
力导向关系图实验
坐标轴和比例尺
```

用途：

```text
可作为局部依赖
用于 renderer 内部计算或生成 path
不作为整体页面布局器
不直接决定 PPT 视觉风格
```

边界：

```text
D3 本身不提供高级 PPT 审美
如果直接用 D3 example 风格，会像网页可视化而不是路演 PPT
必须由 visual tokens 和自研 renderer 控制最终样式
```

生产链路建议：

```text
ChartSchema / DiagramSchema
  ↓
D3 utilities for scale/path
  ↓
PPTSvgThemeRenderer 输出统一 SVG
```

优先级：

```text
P1/P2 按需引入
首期可先不用，避免增加技术复杂度
```

### 7.6 G2 / AntV

定位：

```text
成熟图表语法和可视化体系
适合数据图表，不适合作为所有 PPT 图解 renderer
```

适用场景：

```text
折线图
柱状图
雷达图
指标看板
趋势图
对比图
```

用途：

```text
Chart 层候选
适合 metric_dashboard / chart_dashboard / risk_radar
最终视觉仍需适配 PPT theme tokens
```

边界：

```text
G2/AntV 默认视觉偏网页图表
需要关闭或改造交互、tooltip、hover 等网页组件
需要导出静态 SVG 或静态 HTML/SVG 片段
不能用于 cover / agenda / architecture 的最终页面整体视觉
```

生产链路建议：

```text
MetricSchema
  ↓
G2/AntV chart generation
  ↓
Static SVG extraction / custom theme
  ↓
Safe Region Renderer
```

优先级：

```text
P1 评估
P2 接入指标图、雷达图、趋势图
```

### 7.7 Graphviz

定位：

```text
经典 graph visualization 工具
适合 DOT graph 到 SVG 的自动布局和可视化
```

适用场景：

```text
开发调试
结构验证
快速查看节点关系是否正确
复杂 graph layout 对照
```

用途：

```text
不建议作为最终生产 SVG renderer
可作为 debug / fallback diagnostics
可作为 graph layout 参考
```

边界：

```text
默认视觉强烈偏技术文档
节点、箭头、字体、间距不符合高级 PPT 气质
调样式成本高，且仍容易像工程文档
```

生产链路建议：

```text
仅开发期：
DiagramSchema -> DOT -> Graphviz SVG -> Debug Preview

不进入最终 preview / PPTX
```

优先级：

```text
P2 可选 debug 工具
不作为 P0/P1 核心依赖
```

### 7.8 Mermaid

定位：

```text
文本定义图表工具
适合 markdown 文档里的流程图、时序图、架构草图
```

适用场景：

```text
研发文档
debug schema
快速验证流程关系
人工阅读中间结构
```

用途：

```text
不进入最终生产视觉
可作为 debug / explain 输出
```

边界：

```text
默认视觉像文档图
高级感、空间控制、标注能力不足
复杂页面容易显得廉价
不适合职业院校技能大赛路演 PPT 最终效果
```

生产链路建议：

```text
仅开发期：
ProcessFlowSchema -> Mermaid -> Debug Diagram

最终交付：
ProcessFlowSchema -> Dagre/自研 layout -> PPTSvgThemeRenderer
```

优先级：

```text
P2 可选 debug 工具
不作为最终渲染方案
```

### 7.9 自研 PPT SVG Theme Renderer

定位：

```text
最终 SVG 视觉输出层
负责高级 PPT 风格、主题 token、标注、层级、证据位和审查友好结构
```

必须自研的原因：

```text
职业院校技能大赛 PPT 需要路演气质，不是技术文档图
需要和 shell、标题、页脚、全局主题统一
需要控制图片证据位、裁判视角标注、实操感
需要输出可审查、可 repair 的结构化 SVG
```

负责：

```text
节点视觉
分组视觉
数据流线
箭头样式
强调节点
证据角标
说明标注
主题适配
SVG 内部审查标记
```

不负责：

```text
业务内容判断
裁判视角判断
复杂 graph layout 全部算法
```

生产链路：

```text
DiagramSchema
  ↓
LayoutAdapter: 自研 / Dagre / ELK
  ↓
ResolvedDiagramLayout
  ↓
VisualTokenResolver
  ↓
PPTSvgThemeRenderer
  ↓
SVGInternalAuditor
```

优先级：

```text
P0 必做
这是最终视觉质量的核心
```

### 7.10 选型总表

| 技术 | 进入生产链路 | 主要用途 | 不做什么 | 优先级 |
| --- | --- | --- | --- | --- |
| 自研 PPT SVG Theme Renderer | 是 | 最终 SVG 视觉输出 | 不做业务判断 | P0 |
| 自研几何 Layout | 是 | 简单图解、证据位、区域排版 | 不解决所有复杂 graph | P0 |
| Dagre | 候选 | 简单流程/有向图布局 | 不负责最终视觉 | P0/P1 |
| ELK | 候选 | 复杂架构/关系图布局 | 不负责最终视觉 | P1/P2 |
| D3 | 局部候选 | path/scale/自定义图形辅助 | 不控制 PPT 风格 | P1/P2 |
| G2 / AntV | 局部候选 | 数据图表、指标图、雷达图 | 不做整页 PPT 图解 | P1/P2 |
| Graphviz | 否 | Debug、结构验证 | 不做最终 SVG | P2 |
| Mermaid | 否 | Debug、文档解释 | 不做最终 SVG | P2 |

### 7.11 决策原则

```text
1. 最终视觉必须由自研 PPT SVG Theme Renderer 控制。
2. 外部库只负责它最擅长的部分：布局计算或图表计算。
3. 外部库输出不能直接进入最终页面，必须经过 theme renderer 或 style adapter。
4. 如果外部库输出无法满足 PPT 审美和审查要求，就只保留为 debug 工具。
5. 所有外部库接入必须能被 Visual Auditor 检查和 repair。
```

---

## 8. Safe Region Page Renderer

### 7.1 页面结构

```html
<main class="slide">
  <header class="shell-title"></header>
  <section class="shell-subtitle"></section>
  <section class="shell-body">
    <div class="ppt-body-root">
      <div class="region region-main-visual"></div>
      <div class="region region-insight"></div>
      <div class="region region-evidence"></div>
    </div>
  </section>
  <footer></footer>
</main>
```

### 8.2 系统控制

系统控制：

```text
坐标
尺寸
字号上下限
图片比例
SVG viewBox
overflow
根容器样式
页脚和标题安全区
```

MiMo 控制：

```text
短文本内容
图解 schema
标注内容
证据用途说明
```

### 8.3 禁止项

```text
MiMo 禁止写整页背景
MiMo 禁止写 .ppt-body-root padding/background
MiMo 禁止写任意 absolute 全局坐标
MiMo 禁止写复杂 SVG 源码
MiMo 禁止创建覆盖 70% 以上大面板
```

---

## 9. Visual Auditor 与 Repair 调度

### 9.1 审查类型

```text
DOM Audit
检查结构、重复标题、root 样式、占位符类型。

Geometry Audit
检查越界、重叠、面积、留白、重心。

Text Audit
检查字号、行数、溢出、内容退化。

SVG Internal Audit
检查节点、箭头、文字、标注。

Screenshot Audit
截图级判断大空白、黑块遮挡、视觉密度。
```

### 9.2 Repair 分层

```text
content_repair
内容压缩、恢复、移 notes

blueprint_repair
补 mission、judge takeaway、annotations

layout_repair
重新分配区域

diagram_schema_repair
减少节点、重组层级、补关系

svg_renderer_repair
换方向、折叠、避让

page_render_repair
修 root、安全区、占位符
```

### 9.3 Repair 调度

必须避免当前串行重画过慢的问题。

策略：

```text
按严重度排序
只 repair 失败页
每轮最多 repair N 页
每页 repair 独立超时
每轮保存中间 audit
失败页保留 debug HTML
连续两轮同类失败则升级为 layout/schema 层修复，不继续让 MiMo 盲改
```

建议默认：

```text
max_repair_rounds = 2
max_pages_per_round = 8
page_repair_timeout = 90s
total_repair_timeout = 12min
```

如果失败页太多，不应全部串行重画，而是：

```text
先处理 P0 硬失败：
越界、重叠、空白、黑块、root 白板

再处理 P1 质量失败：
小字、图片过小、主视觉不足、卡片同质化
```

### 9.4 并发策略

可以并发的：

```text
Content preservation audit
Page expression planning
Diagram schema planning
SVG rendering
DOM/geometry audit
```

不建议完全并发的：

```text
Deck Strategy
Rhythm planning
跨页结构去重
章节节奏判断
```

推荐并发粒度：

```text
Deck-level pass: 串行 1 次
Page-level planning: 并发 4-6 页
Diagram renderer: 本地并发
Visual audit: Playwright 可按 1-2 browser contexts 并发
Repair: 按失败页并发 2-3 页，避免 MiMo 请求过载
```

---

## 10. 数据流与模块接口

### 10.1 Pipeline Payload

```json
{
  "deck_strategy": {},
  "content_ledger": [],
  "page_blueprints": [],
  "layout_candidates": [],
  "selected_layouts": [],
  "diagram_schemas": [],
  "rendered_svgs": [],
  "html_pages": [],
  "audit_reports": [],
  "repair_trace": []
}
```

### 10.2 页面级数据流

```text
PageContent
  ↓
ContentAtoms
  ↓
PageExpressionPlan
  ↓
PresentationBlueprint
  ↓
RegionLayout
  ↓
DiagramSchema
  ↓
RenderedSVG
  ↓
SafeHTML
  ↓
AuditReport
```

### 10.3 中间文件

每个任务保存：

```text
preview_v6_{task_id}/_content_ledger.json
preview_v6_{task_id}/_deck_strategy.json
preview_v6_{task_id}/_page_blueprints.json
preview_v6_{task_id}/_layout_plan.json
preview_v6_{task_id}/_diagram_schemas.json
preview_v6_{task_id}/_render_audit.json
preview_v6_{task_id}/_repair_trace.json
preview_v6_{task_id}_failed_debug/page_*.html
```

这些文件用于：

- 回归分析。
- 审美评估。
- 定位 MiMo 判断问题。
- 定位系统排版问题。
- 定位 SVG renderer 问题。

---

## 11. 完整优化步骤

### 11.1 P0：先建立“不会翻车”的生成骨架

目标：

```text
不再让 MiMo 直接控制整页 HTML
不再让复杂图解自由 SVG 放飞
不再出现 root 白板、越界、重叠、小字无人处理
```

任务：

```text
1. 建 Content Ledger
2. 建 Content Preservation Auditor
3. 建 Page Expression Planner v1
4. 建 Presentation Blueprint schema
5. 建 Layout Solver v1
6. 建 ArchitectureRenderer v1
7. 建 ProcessFlowRenderer v1
8. 建 EvidenceBoardRenderer v1
9. Safe Renderer 改成 region-based
10. Visual Auditor 增加 region 和 SVG internal 检查
11. Repair 调度改为限时、分层、保留 debug
```

覆盖页面：

```text
cover
agenda
architecture_system
practice_evidence
value_matrix
```

验收：

```text
同源智慧农业任务失败页明显下降
不出现 root 大白板
不出现图片占位过小
不出现明显越界
架构页由系统 SVG renderer 输出
失败页有 debug HTML 和 audit trace
```

### 11.2 P1：提升专业表达质量

任务：

```text
1. 增加 Competition Judge Pass
2. 增加 Technical Architect Pass
3. 增加 Reverse Reviewer Pass
4. 增加 MetricDashboardRenderer
5. 增加 TimelineRenderer
6. 增加 ComparisonMatrixRenderer
7. 增加 diagram schema repair
8. 增加 content_budget 自动压缩
```

验收：

```text
实操页至少出现现场/系统/数据样例证据之一
架构页必须有层级、数据流、职责边界
目录页必须真实章节结构
内容不空泛，能经受裁判反问
```

### 11.3 P2：建立高级视觉 DNA

任务：

```text
1. 建 Visual Token System
2. 建多套 deck DNA
3. 图解 renderer 接入主题 token
4. 增加跨页节奏控制
5. 增加反同质化评分
```

视觉 DNA：

```text
light_tech_competition
dark_roadshow_tech
government_evidence
engineering_practice
business_growth
research_demo
```

验收：

```text
同一个 schema 在不同主题下有不同气质
同一 deck 不连续出现同一种重心结构
页面有主次、有留白、有专业图解感
```

### 11.4 P3：真实任务回归与人工审美闭环

任务：

```text
1. 建真实问卷回归集
2. 每个任务生成 contact sheet
3. 每页人工评分：像不像 PPT、专业度、呼吸感、重点、证据力
4. 收集失败类型，更新 planner / solver / renderer
5. 建质量趋势 dashboard
```

验收：

```text
至少 5 个不同主题真实问卷通过
失败页率低于目标阈值
人工审美评分持续提升
不同主题风格差异明显
```

---

## 12. 风险与边界

### 12.1 不能承诺一次生成就是顶尖 PPT

原因：

```text
审美不是纯数学问题
用户输入质量差异大
MiMo 对项目细节理解可能不足
没有真实图片素材时证据页只能占位
```

### 12.2 可以承诺逐步稳定逼近

可以通过系统机制保证：

```text
不越界
不重叠
不小字
不空白
不网页白板
不固定模板
不让复杂图解失控
不让内容无痕丢失
```

### 12.3 质量上限来自三件事

```text
MiMo 的专业判断质量
系统 SVG renderer 的视觉语法质量
Visual Auditor + 人工反馈闭环的持续迭代
```

---

## 13. 最终判断

这条路线比当前 V5 更复杂，但方向更正确。

当前 V5 是：

```text
MiMo 直接画页面，系统事后审查
```

目标 V6 应该是：

```text
MiMo 规划语义和表达
系统计算版式和绘制图解
MiMo 只参与必要的内容和语义修复
系统负责最终稳定落版和质量门禁
```

一句话：

> 我们不是做 HTML 模板生成器，而是做一个面向职业院校技能大赛路演的 PPT 图解编译系统。
