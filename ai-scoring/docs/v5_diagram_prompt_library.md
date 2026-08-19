# V5 图示类型提示词库 v1

这份库的目标不是让 MiMo “自由理解什么是好图”，而是让程序先按页面语义选中图示类型，再把对应的抽取字段、布局规则和制图规范交给 MiMo。也就是说：MiMo 负责设计和绘制，但图示语法由本地库约束。

配套结构化文件：

- `docs/v5_diagram_prompt_library.json`

## 执行方式

推荐采用“预设图示提示词库 + 页面类型自动选取 + 二段式执行”。

1. 页面内容进入图示分类器。
2. 根据标题、页面类型、chart、content_points、core_argument 选择图示类型。
3. 用该类型的 `extract_schema` 抽取页面专属 diagram JSON。
4. 将 diagram JSON 和该类型的 `render_contract` 注入 MiMo 主体区 prompt。
5. 本地审查重叠、越界、信息密度、焦点短句、自由路径数量。
6. 不通过时带同一图示类型规则重画，不换成泛化卡片页。

不建议让 MiMo 每次自己生成提示词。原因是不同图的语义不同：流程图讲顺序，架构图讲层级和边界，证据链讲证明逻辑，指标看板讲主指标和支撑指标。如果给一个万能 prompt，MiMo 很容易把所有图都画成横向节点链或卡片网格。

## 全局制图规范

所有图示都必须遵守：

- 只设计主体区，不管理外层标题、副标题、页脚。
- 根节点必须是 `.mimo-body-root`。
- 内容页根节点必须带 `data-page-archetype`、`data-visual-motif`、`data-dominant-visual`、`data-focus-text`。
- 页面必须有 8-18 个汉字的可见焦点短句，不能重复外层标题。
- 内容页采用“焦点短句 + 主图解/主证据 + 2-4 个支撑信息”的刚好密度。
- 普通页可见文字约 70-170 个汉字，技术/证据重页约 120-240 个汉字。
- 优先使用稳定可画结构：中心环、塔、金字塔、2x2 或 3x2 矩阵、镜像对比、垂直/水平泳道、仪表盘墙、单一路径。
- 主节点最多 6 个，判断节点最多 2 个，支撑标签最多 4 个。
- SVG viewBox 内实际图形四周留 6%-8% 安全边距。
- 主体区左右安全边距约 1.8%，上下安全边距约 3.5%。
- 禁止随机漂浮节点、交叉连线、文字压在线上、多条自由曲线、负坐标、越界、大白板容器、上传控件样式、评分点话术。

## 图示类型

### 1. 技术路线图 `technical_route`

适用：研究路线、技术路线、项目实施路径、方法论路线。

抽取字段：

- `topic_name`：课题/项目名称，或根据内容概括。
- `research_object`：研究对象，10-20 字。
- `core_problem`：核心问题，30-50 字。
- `research_contents`：3-5 项研究内容，按逻辑排序。
- `main_methods`：3-5 个关键方法。
- `expected_results`：2-4 项预期成果。
- `academic_or_business_field`：所属领域。
- `route_stages`：3-6 个路线阶段。
- `validation_or_feedback`：验证或反馈关系，可为空。

制图规范：

- 图表类型为技术路线图。
- 推荐垂直路线、水平路线、层级树、中心辐射。
- 每个阶段必须包含动作 + 方法/结果标签。
- 最终成果节点要比普通节点更强。
- 方法与内容并行时，用侧边带汇入主路线。
- 决策/验证节点使用菱形，最多 2 个。
- 反馈环路只允许 1 条虚线箭头。

### 2. 流程图 `flowchart`

适用：执行流程、操作步骤、实操环节、处理链路。

抽取字段：

- `diagram_title`：图示标题，12-20 字。
- `process_goal`：流程要证明的核心结论，20-40 字。
- `start_state`：流程起点，8-16 字。
- `end_state`：流程终点，8-16 字。
- `main_steps`：3-6 个主步骤。
- `step_inputs`：每步输入。
- `step_outputs`：每步输出。
- `key_decisions`：0-2 个判断节点。
- `feedback_loop`：反馈从哪里回到哪里。
- `evidence_labels`：2-4 个证据/数据/来源标签。
- `risk_or_exception`：0-2 个异常处理节点。
- `preferred_layout`：`vertical` / `horizontal` / `swimlane` / `loop` / `radial`。

制图规范：

- 主流程节点 3-6 个，禁止超过 6 个。
- 优先水平、垂直、泳道或闭环，不用 S 曲线。
- 判断节点必须是菱形，最多 2 个。
- 连接线短、清晰、少转折。
- 反馈箭头只允许 1 条虚线。
- 证据标签贴近对应步骤，不能压在线上。

### 3. 系统架构图 `architecture`

适用：系统结构、端-边-云、模块架构、技术栈、平台层级、部署拓扑。

抽取字段：

- `system_goal`：架构要证明什么。
- `layers`：3-5 个层级，从数据源/设备到应用/用户。
- `modules`：每层 2-4 个模块。
- `data_flow`：核心数据流/控制流标签。
- `boundary`：系统边界、外部系统、用户侧/设备侧。
- `key_interfaces`：0-4 个接口或协议。
- `security_or_ops`：可选支撑层。
- `output_value`：最终能力或价值。

制图规范：

- 先画层级和边界，模块是第二层信息。
- 推荐分层堆叠、端边云泳道、中心拓扑、塔式架构、控制面/数据面分离。
- 数据流必须从来源指向价值结果。
- 模块必须落在边界或层级内，不能漂浮。
- 模块太多时先分组，不逐个堆满。
- 禁止画成横向流程节点链。

### 4. 数据流图 `data_flow`

适用：数据采集、清洗、入库、分析、查询、反馈、ETL。

抽取字段：

- `source_data`：1-4 个数据源。
- `processing_steps`：3-6 个处理步骤。
- `storage_or_model`：数据库、模型、服务节点。
- `outputs`：2-4 个输出结果。
- `quality_controls`：校验、清洗、异常过滤。
- `latency_or_metric`：可选指标。
- `feedback_target`：可选反馈对象。

制图规范：

- 数据路径必须连续，可以用一条主带或主线。
- 来源、处理、存储/模型、输出要用分区或泳道区分。
- 质量控制标签贴在具体步骤旁。
- 输出区是视觉终点。
- 禁止退化成四张普通卡片。

### 5. 证据链图 `evidence_chain`

适用：证明、验证、实操证据、截图、日志、测试、成果落地。

抽取字段：

- `claim`：已证明的结论，12-24 字。
- `evidence_sources`：2-4 个来源，例如日志、截图、测试、现场记录。
- `evidence_actions`：证据是如何产生的。
- `evidence_results`：每个证据证明什么。
- `trust_labels`：来源、时间、指标标签。
- `final_value`：证据如何转化为动作/价值。
- `missing_asset_policy`：是否需要图片位或生成素材。

制图规范：

- 结论先行，claim 是第一视觉。
- 证据锚点 2-4 个，每个必须有来源 + 动作/结果。
- 证据位要像材料板、日志片段、仪表盘片段或照片裁切，不像上传框。
- 如果用路径，只允许一条简单箭头从证据指向价值。
- 禁止波浪链、三列机制图、空截图框、评分点话术。

### 6. 指标看板 `metric_dashboard`

适用：KPI、准确率、效率、成本、收益、实验结果、性能指标。

抽取字段：

- `main_metric`：必须突出的主指标。
- `unit`：单位。
- `baseline_or_comparison`：基准、目标或对比值。
- `support_metrics`：2-4 个辅助指标。
- `trend_or_distribution`：趋势或分布，可为空。
- `evidence_source`：数据来源。
- `interpretation`：指标说明的短结论。

制图规范：

- 一个主指标必须成为第一视觉。
- 每个指标必须带单位或来源上下文。
- 辅助指标必须支撑主结论。
- 图表必须有真实轴线/标签逻辑，不能装饰性假图。
- 禁止四个同权 KPI 卡。

### 7. 对比矩阵 `comparison_matrix`

适用：前后对比、传统 vs 升级、方案选择、竞品对比、痛点 vs 方案。

抽取字段：

- `comparison_subject`：比较对象。
- `columns`：2-4 个比较列。
- `rows`：3-5 个维度。
- `winning_or_target_column`：需要突出的目标列。
- `delta_labels`：具体改进差异。
- `evidence_or_metric`：可选指标。
- `takeaway`：对比结论。

制图规范：

- 维度和比较基准必须明确。
- 用对齐、色彩、大小突出差异。
- 目标列可强调，但不能失真。
- 单元格只放短语，禁止段落。
- 如果有升级过程，中间用桥或箭头表达。

### 8. 时间线 `timeline`

适用：研发历程、项目计划、阶段推进、里程碑。

抽取字段：

- `time_scope`：整体时间范围。
- `milestones`：3-6 个里程碑。
- `outputs`：每个阶段产出。
- `review_points`：验证/复盘节点。
- `current_status`：当前阶段，可为空。
- `future_next`：下一步，可为空。

制图规范：

- 时间线必须同时体现顺序和阶段产出。
- 里程碑 3-6 个。
- 当前/关键节点需要强调。
- 产出标签贴近里程碑。
- 禁止只有小圆点无产出。

### 9. 风险矩阵 `risk_matrix`

适用：风险、安全、质量、异常处理、预案、控制措施。

抽取字段：

- `risk_categories`：3-5 类风险。
- `risk_level`：高/中/低或等级。
- `trigger_conditions`：触发条件。
- `response_actions`：响应动作。
- `owner_or_checkpoint`：责任人/检查点，可为空。
- `residual_result`：控制后的结果。

制图规范：

- 风险等级必须可视化编码。
- 每个风险必须有触发条件 + 响应措施。
- 推荐风险矩阵、响应泳道、防护层、控制闭环。
- 结论要说明风险如何被控制。
- 禁止普通风险列表。

### 10. 价值闭环 `value_loop`

适用：价值创造、业务闭环、生态关系、利益相关方循环。

抽取字段：

- `central_value`：核心价值主张。
- `actors_or_nodes`：3-6 个参与方/节点。
- `value_exchanges`：节点间流动的价值。
- `metrics_or_outcomes`：2-4 个结果指标。
- `feedback_mechanism`：价值如何回流。
- `scale_condition`：复制/规模化条件，可为空。

制图规范：

- 中心或终点必须是核心价值。
- 推荐环形、闭环、中心辐射、生态图。
- 节点均匀分布，方向明确。
- 结果标签 2-4 个。
- 禁止随机径向散点。

### 11. 金字塔/能力塔 `pyramid`

适用：能力层级、成熟度模型、基础到目标、分层支撑。

抽取字段：

- `top_goal`：顶层目标。
- `levels`：3-5 层级，从基础到顶部。
- `level_meanings`：每层含义。
- `support_evidence`：1-3 个支撑标签。
- `transition_logic`：下层如何支撑上层。

制图规范：

- 3-5 层，底宽顶窄。
- 顶层目标必须清晰。
- 层级标签居中且短。
- 侧边最多 3 个证据说明。
- 禁止纯装饰三角形。

### 12. 雷达/能力模型 `radar`

适用：能力维度、成熟度评价、多维对比。

抽取字段：

- `dimensions`：4-6 个维度。
- `scores_or_levels`：每维分值或等级。
- `benchmark`：基准或目标，可为空。
- `strongest_dimension`：优势项。
- `weakest_dimension`：改进项。
- `takeaway`：结论。

制图规范：

- 只允许 4-6 个轴。
- 标签放在雷达外侧，不压住多边形。
- 强弱项用 callout 标出。
- 没有精确数据时，用等级，不编小数。

### 13. 推广/路线地图 `route_map`

适用：推广路径、区域落地、复制路线、市场推进、部署计划。

抽取字段：

- `start_region_or_state`：起点。
- `target_region_or_state`：终点。
- `route_steps`：3-5 个推进阶段。
- `key_conditions`：每阶段条件。
- `resource_or_partner`：资源/伙伴。
- `result_at_destination`：终点结果。

制图规范：

- 用路线、地图、道路或 stage-gate 隐喻。
- 必须有明确终点。
- 每阶段包含条件 + 结果。
- 没有真实地图时，用抽象路线，不编假地理。
- 终点/结果节点需要强调。

### 14. 语义信息图 `semantic_infographic`

适用：无法明确归类，但仍需要图解表达的页面。

抽取字段：

- `main_argument`：核心观点。
- `semantic_groups`：2-4 个语义组。
- `relationships`：组间关系。
- `proof_or_result`：证据或结果。
- `recommended_shape`：`ring` / `matrix` / `tower` / `stage` / `dashboard` / `split_compare`。

制图规范：

- 选择一个简单视觉隐喻并坚持到底。
- 禁止退回等宽卡片网格。
- 保持一个焦点短句和 2-4 个支撑标签。
- 关系要明确，连线要少。

## 初始分类规则

可以先用关键词 + page_series_type 进行第一版分类：

- 架构、端-边-云、技术栈、模块、平台层：`architecture`
- 流程、步骤、环节、操作、处理、闭环、链路：`flowchart`
- 数据处理、采集、清洗、入库、查询、分析：`data_flow`
- 证据、验证、实操、日志、截图、测试、成果：`evidence_chain`
- 指标、准确率、效率、耗时、成本、收益、百分比：`metric_dashboard`
- 对比、前后、传统、升级、差异、方案选择：`comparison_matrix`
- 历程、时间、阶段、里程碑、计划：`timeline`
- 风险、安全、质量、异常、预案、控制：`risk_matrix`
- 价值、闭环、生态、协同、循环、复用：`value_loop`
- 层级、能力、成熟度、基础、支撑、目标：`pyramid`
- 雷达、能力评估、多维：`radar`
- 推广、路径、落地、区域、复制、路线：`route_map`

分类置信度低时，用 `semantic_infographic`，但仍禁止卡片网格默认表达。
