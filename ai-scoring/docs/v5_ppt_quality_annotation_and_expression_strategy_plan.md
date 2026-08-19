# V5 PPT 质量标注集与表达策略升级计划

## 目标

把当前 V5 从“能生成、少错位”的工程系统，升级为“先做页面表达判断，再生成参赛级 PPT 主体区”的产品系统。

核心变化：

1. 先建立页面级质量标注集：锐普案例、`preview_182` 好页、V5 失败页统一标注。
2. 每页生成前必须有页面表达假设。
3. 页面类型从少量粗分类扩展为 20 类表达策略。
4. 图示先生成结构化规格，再交给 MiMo 美化。
5. 审查从 DOM 安全扩展到截图审美。
6. 支持同页 A/B/C 多方案生成与择优。
7. repair 只处理机械错误；审美失败回到策略选择阶段。

## 页面级质量标注集

每一页样本记录以下字段：

- `sample_id`: 样本唯一 ID。
- `source`: `rapidesign | preview_182_good | v5_failure | v5_regression`。
- `page_type`: 封面、目录、政策、痛点、架构、流程、证据、价值、团队、收尾等。
- `expression_strategy_id`: 20 类策略之一。
- `main_visual_type`: 主视觉类型。
- `main_visual_ratio`: 主视觉占主体区比例。
- `information_density`: `low | balanced | dense | overloaded`。
- `focus_strength`: 1-5 分，1 秒内是否知道重点。
- `diagram_quality`: 1-5 分，图示是否清晰、规范、无漂移。
- `ppt_craft_score`: 1-5 分，是否像专业 PPT 而不是网页/后台 UI。
- `failure_reasons`: 空、散、卡片感、表格感、小字、越界、无主视觉、内容胡编、同质化等。
- `repair_policy`: 机械修复、重选策略、重生成图示规格、进入 A/B。

## 页面表达假设

每页 HTML 生成前必须回答：

- 观众 1 秒应该记住什么？
- 用什么视觉证明它？
- 主视觉占主体区多少？
- 哪些内容上屏，哪些进入讲稿？
- 本页禁止退化成什么形态？

如果这些字段缺失，V5 不应直接进入 MiMo HTML 生成。

## 20 类表达策略

已落第一批策略库，核心策略包括：

1. 封面主题海报 `cover_poster_scene`
2. 图片化目录 `chapter_landscape_index`
3. 政策背书墙 `policy_backing_wall`
4. 痛点压力场 `problem_pressure_field`
5. 解决方案总图 `solution_big_picture`
6. 技术系统总线 `technical_system_bus`
7. 数据交接流水线 `data_handoff_pipeline`
8. 算法验证实验台 `algorithm_proof_lab`
9. 实操演示舞台 `practice_demo_stage`
10. 证据舞台 `evidence_stage`
11. 风险响应环 `risk_response_ring`
12. 价值章印 `value_stamp`
13. 创新前后对照 `innovation_before_after`
14. 团队作战图 `team_operation_map`
15. 里程碑道路 `milestone_road`
16. 结尾记忆信号 `closing_memory_signal`
17. 研究方法路线 `research_method_route`
18. 指标故事图 `metric_story_chart`
19. 场景剖面图 `scenario_cutaway`
20. 攻关战役图 `battle_card`

每类策略定义：

- 主视觉证明方式
- 构图语法
- 目标主视觉占比
- 图示类型
- 禁用形态
- 最低质量门禁

## 图示结构化规格

图示页不再只告诉 MiMo “画一个图”，而是先给：

- `diagram_type`
- `nodes`
- `connections`
- `layout_blueprint`
- `main_visual_ratio_target`
- `connector_rule`
- `label_rule`
- `forbidden_shapes`

MiMo 的职责是基于规格做视觉设计，不是自由发明图示结构。

## 多模态审美评审

后续增加截图级评审字段：

- `one_second_readability`
- `visual_anchor_strength`
- `ppt_craft_score`
- `same_layout_risk`
- `card_ui_risk`
- `diagram_clarity`
- `competition_presentation_fit`

DOM 审查继续负责越界、小字、重复标题等机械问题。

## A/B/C 实验

同一页可生成三种候选：

- `safe`: 保守稳定版
- `reference_inspired`: 锐普式强视觉版
- `diagram_intensive`: 图解强化版

选择逻辑：

1. 先过 DOM 安全。
2. 再过截图审美。
3. 最后看与相邻页的同质化风险。

## Repair 边界

repair 只处理：

- 小字
- 越界
- 重复标题
- 负定位
- SVG/path 超边
- 机械重叠

审美失败不进入 repair，而是：

1. 重新选择表达策略。
2. 重新生成图示规格。
3. 进入 A/B/C 候选生成。

## 当前开发阶段

### 已开始

- 新增 `v5_page_expression_hypotheses`。
- 新增 20 类表达策略库。
- 将表达假设接入 V5 clean pipeline、page contract、diagram spec 和 MiMo prompt。

### 下一阶段

- 建立样本标注 JSONL。
- 写截图审美评审器。
- 支持单页 A/B/C 候选生成。
- 用智慧农业 JSON 做目标页实验。
