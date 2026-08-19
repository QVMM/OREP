# AI 生成 PPT 成品链路 -- 12 环节完成状态分析报告

> 分析时间：2026-05-03
> 分析范围：`app/services/ppt/` 全部模块（v4/v5/v6 三代渲染引擎 + 主服务 + 路由层 + QA 基础设施）
> 项目代号：PitchForge (OREP AI PPT)

---

## 总览：12 环节完成状态一览表

| # | 环节 | 状态 | 完成度 | 关键模块 |
|---|------|------|--------|----------|
| 1 | 用户问卷/项目资料解析 | ✅ 已完成 | 95% | `questionnaire_schema.py`, `knowledge_base.py`, 前端表单 |
| 2 | AI 生成大纲、叙事结构、评分点映射 | ⚠️ 已完成但有问题 | 80% | `outline_generator.py`, `page_semantics.py`, `page_contracts.py` |
| 3 | AI 生成每页内容与表达意图 | ⚠️ 已完成但有问题 | 75% | `pipeline_coordinator.py`, `expression_planner.py`, Round 2/3 |
| 4 | AI 输出 schema / composition / visual intent | ✅ 已完成 | 90% | v5 `composition_engine.py`, v6 `blueprint.py` + `expression_planner.py` |
| 5 | 系统做 schema 校验、去噪、内容边界控制 | ✅ 已完成 | 90% | `data_validator.py`, `hard_gate_rules.py`, `lexicon_firewall.py`, `text_sanitizer.py` |
| 6 | 系统规划页面结构、primitive、space budget、text measurement | ✅ 已完成 | 90% | v4/v5/v6 三代 `layout_solver.py` |
| 7 | 视觉 renderer 生成专业 SVG / 图表 / 证据位 / 页面主体 | ⚠️ 已完成但有问题 | 70% | v6 `svg_renderer/`, v5 `ai_passes.py`, `formal_render_engine.py` |
| 8 | Shell 层整合封面、目录、标题、副标题、页脚、主题 | ✅ 已完成 | 90% | v5 `shell_system.py`, v6 `render_engine.py`, `style_presets.py` |
| 9 | 自动视觉审查：溢出、重叠、空白、模板感、可读性、截图质量 | ✅ 已完成 | 85% | `reviewer.py`, `vision_judge_service.py`, `render_layout_auditor.py` |
| 10 | Repair pass：把问题反馈给 AI 或系统重排 | ⚠️ 已完成但有问题 | 70% | v5 `ai_passes.py` (repair), `repair_planner.py`, API `/repair` 端点 |
| 11 | Preview / HTML / PPTX 稳定生成，任务状态与超时控制 | ⚠️ 已完成但有问题 | 65% | `html_renderer.py`, `pptx_renderer_html.py`, `ppt_router.py` |
| 12 | 多真实问卷回归 + 人工审美验收，确认不同项目不会同质化 | ⚠️ 部分完成 | 50% | `qa/`, `tests/`, `tools/page_series_regression.py` |

**整体评估：链路骨架已完整搭建（12 环节均有代码实现），但端到端可用性仍有关键断点。**

---

## 环节 1：用户问卷/项目资料解析

### 状态：✅ 已完成（95%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| 问卷 Schema | `app/services/ppt/questionnaire_schema.py` | 定义 6 大 section、30+ 字段的结构化问卷 |
| 行业知识库 | `app/services/ppt/knowledge_base.py` | 5 个行业（healthcare/fintech/education/ai_iot/elderly_care）的市场数据、指标基准、竞品信息 |
| 前端表单 | `frontend/src/views/Phase1Round1.vue` | Vue 3 + Naive UI 动态表单 |
| API 端点 | `ppt_router.py` → `POST /api/ppt/questionnaire/submit` | 提交问卷数据 |
| 完整度评估 | `ppt_service.py` → `assess_questionnaire_readiness()` | 6 维度评分（基础叙事 22 / 评分对齐 18 / 实操演示 18 / 技术难度 16 / 证据素材 14 / 团队规范 12） |
| 领域自动检测 | `knowledge_base.py` → `detect_domain_from_responses()` | 基于关键词匹配自动判断行业 |

### 数据流

```
用户填写前端表单 → POST /questionnaire/submit → 存入 SQLite/MySQL
→ assess_questionnaire_readiness() → 返回完整度评分 + 阻断项
→ create_task_v2() → 创建生成任务
```

### 已知问题

- 领域检测仅支持 5 个行业，新行业需手动扩展 `knowledge_base.py`
- 完整度评估的阈值逻辑较简单，缺少渐进式引导

---

## 环节 2：AI 生成大纲、叙事结构、评分点映射

### 状态：⚠️ 已完成但有问题（80%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| 大纲生成器 | `app/services/ppt/outline_generator.py` | 9 步流程：行业知识注入 → AI 生成语义序列 → 规则引擎转换 → 评分点检查 |
| 页面语义定义 | `app/services/ppt/page_semantics.py` | 12 种页面语义类型（4 固定 + 8 内容页） |
| 页面契约 | `app/services/ppt/page_contracts.py` | 14 个页面契约 + 13 个竞赛评分点映射 |
| 评分检查 | `app/services/ppt/scoring_checker.py` | 大纲级评分点覆盖检查 |
| 布局规划 | `app/services/ppt/outline_layout_planner.py` | 大纲级布局编排 |
| 规则引擎 | `app/services/ppt/rule_engine.py` | 评分规则引擎 |
| AI 调用 | `app/services/ppt/llm_factory.py` + `qwen_client.py` | DashScope 通义千问 qwen3.6-plus |

### AI Prompt 设计（v4.0 架构）

核心设计思想：**"AI 只选语义，规则引擎决定布局"**

- 系统提示词 `OUTLINE_SYSTEM_PROMPT_V4` 约 400 行
- 定义 8 种可用语义类型
- 指定 40-50 页的叙事节奏：背景 5-7 页 → 痛点 3-5 页 → 解决方案 10-15 页 → 功能 5-7 页 → 成果 5-7 页 → 团队 3-5 页
- 硬性规则：SKILL_STEPS 必须有 steps_detail，连续不超过 3 页
- 降级方案：`_get_default_semantic_sequence()` 返回 7 个默认页面

### 输出格式

```json
{
    "$schema": "ppt-dsl-v4.0",
    "version": "4.0",
    "project": {"name": "...", "team": "...", "theme": "..."},
    "pages": [
        {
            "page_index": 1,
            "section": "...",
            "layout": "kpi_metrics",
            "component_id": "kpi_metrics",
            "semantic": "BACKGROUND_DATA",
            "data": {"title": "...", "metrics": [...]}
        }
    ]
}
```

### 已知问题

1. **空壳页问题严重**：Sprint 1 P0 回归测试中，3/3 用例全部失败，有效页数为 0，空壳页 7-27 个
2. **AI 输出不稳定**：语义序列解析支持新旧格式兼容，但降级路径可能导致内容丢失
3. **行业覆盖有限**：知识库仅 5 个行业，跨行业项目容易出现"跨行业污染"

---

## 环节 3：AI 生成每页内容与表达意图

### 状态：⚠️ 已完成但有问题（75%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| Pipeline 协调器 | `app/services/ppt/adapter_code/pipeline_coordinator.py` | 编排 Round 1-3 多轮生成 |
| Round 1 | `outline_generator.py` | 生成语义序列 + 基础内容 |
| Round 2 | 页面丰富化 | 为每页填充详细内容、评分证据块 |
| Round 3 | 页面丰富化续 | 补充缺失的评分点映射、证据提示 |
| V5 表达规划 | `app/services/ppt/v5/professional_expression_planner.py` | 11 种专业表达类型推断 |
| V6 表达规划 | `app/services/ppt/v6/expression_planner.py` | 10 种表达类型 + 评委问题推断 |
| 内容登记 | `app/services/ppt/v6/content_ledger.py` | 原子化内容单元 + 去重 + 语义分类 |

### V6 表达类型体系

| 类型 | 触发条件 | 主视觉 |
|------|---------|--------|
| `cover_hero` | series == "cover_keynote" | 封面信号图 |
| `agenda_navigation` | 含"目录/议程" | 路线图 |
| `architecture_diagram` | 含"架构/技术栈" | 分层架构图 |
| `evidence_board` | 含"实操/截图/验证" | 证据板 |
| `process_flow` | 含"流程/步骤" | 流程图 |
| `chart_dashboard` | 含"指标/收益/%" | 仪表盘 |
| `comparison_matrix` | 含"对比/改良前后" | 对比矩阵 |
| `risk_radar` | 含"风险/安全" | 风险雷达 |
| `value_chain` | series == "value_matrix" | 价值链 |
| `closing_signal` | series == "closing_board" | 收束信号 |

### 已知问题

1. **Round 2/3 内容填充质量不稳定**：部分页面的 content_points 为空或为占位符
2. **V5 和 V6 表达规划器存在重复**：两套系统各自独立，未统一
3. **评委问题推断过于简单**：仅基于关键词匹配，缺少深度语义理解

---

## 环节 4：AI 输出 schema / composition / visual intent

### 状态：✅ 已完成（90%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| V5 构图引擎 | `app/services/ppt/v5/composition_engine.py` | 16 种预定义构图模板 + 信号检测 + 视觉意图推断 |
| V5 叙事图 | `app/services/ppt/v5/narrative_graph.py` | 16 种叙事角色 + 5 种叙事段落 |
| V5 SVG Schema | `app/services/ppt/v5/svg_schema_builder.py` | 5 种 SVG 类型（route/timeline/handoff/value/signal） |
| V6 蓝图 | `app/services/ppt/v6/blueprint.py` | PresentationBlueprint + MainVisualSpec + SupportingRegionSpec |
| V6 图表 Schema | `app/services/ppt/v6/diagram_schema.py` | 5 种 payload（cover/agenda/architecture/process/evidence） |
| V4 蓝图规划 | `app/services/ppt/v4/deck_blueprint_planner.py` + `page_blueprint_builder.py` | DeckBlueprint + PageBlueprint |
| 数据模型 | `app/services/ppt/v6/models.py` | 12 个 @dataclass 定义完整数据契约 |

### V5 构图模板库（16 种）

```
blank_body, hero_statement_support, hero_canvas_metric,
route_board_metric_tail, route_story_split,
evidence_mosaic_insight, definition_split_focus,
support_stack_focus, left_timeline_right_retro,
top_timeline_bottom_findings, center_chain_side_roles,
left_roles_right_handoff, scenario_board_metric_side,
top_value_statement_bottom_evidence
```

### V6 蓝图结构

```python
PresentationBlueprint:
    page_mission: str           # 页面使命
    judge_takeaway: str         # 评委带走的一句话
    dominant_question: str      # 评委最可能问的问题
    main_visual: MainVisualSpec # 主视觉规格
    supporting_regions: List[SupportingRegionSpec]  # 辅助区域
    visual_style: VisualStyleSpec  # 视觉风格
    content_budget: ContentBudget  # 内容预算
```

### 已知问题

1. **V5 构图选择基于规则匹配**，缺少对内容复杂度的自适应
2. **V6 蓝图的 `min_visual_area_ratio` 硬编码**（0.38 / 0.48），未考虑实际内容量

---

## 环节 5：系统做 schema 校验、去噪、内容边界控制

### 状态：✅ 已完成（90%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| 数据验证器 | `app/services/ppt/data_validator.py` | 空壳页检测 + 自动修复 + 邻页借调 + 小页合并 |
| 硬门控规则 | `app/services/ppt/v4/hard_gate_rules.py` | 5 项确定性 pass/fail 检查 |
| 词库防火墙 | `app/services/ppt/v4/lexicon_firewall.py` | 空话检测（6 项）+ 跨行业漂移检测 |
| 文本净化器 | `app/services/ppt/v5/text_sanitizer.py` | 移除指令性短语（"把...讲清楚"等） |
| 演示净化器 | `app/services/ppt/presentation_sanitizer.py` | 剥离 7 类内部标记（aside/prefix/h3/badge/card/token/snippet） |
| 内容登记审计 | `app/services/ppt/v6/content_ledger.py` | 原子化内容 + 语义分类 + 重要性评级 + 去重 + 完整性审计 |
| 嵌套画布审计 | `app/services/ppt/v5/nested_canvas_auditor.py` | 检测"HTML page inside PPT page"失败模式 |
| Body 布局审计 | `app/services/ppt/v5/body_layout_auditor.py` | AI 生成 body 后的 8 项预审检查 |

### 硬门控检查项

| 检查 | 惩罚分 | 是否阻断 |
|------|--------|----------|
| 不支持的 page_series_type | 35 | ✅ 阻断 |
| 空标题 | 20 | ✅ 阻断 |
| 缺失 core_argument/page_goal | 20 | ✅ 阻断 |
| 无 selected_variant | 15 | ❌ |
| content_points 超过 max_bullets(5) | 8 | ❌ |
| 缺失 audience_takeaway | 6 | ❌ |

### 已知问题

1. **空壳页修复使用兜底内容**：填充的是默认指标（"覆盖率 95%"、"准确率 98.5%"），非项目真实数据
2. **净化器的正则匹配可能误删**：某些正常文本可能匹配到内部标记模式

---

## 环节 6：系统规划页面结构、primitive、space budget、text measurement

### 状态：✅ 已完成（90%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| V4 布局求解器 | `app/services/ppt/v4/layout_solver.py`（896 行） | 两阶段决策：family 选择 + variant 选择，4 维评分 |
| V5 布局引擎 | `app/services/ppt/v5/layout_engine.py` | 16 种叙事角色 → 布局参数映射 |
| V6 布局求解器 | `app/services/ppt/v6/layout_solver.py` | 5 种候选布局模板 + 评分机制 + text height 估算 |
| V4 布局文法注册 | `app/services/ppt/v4/layout_grammar_registry.py` | 15 种页面系列 × 1-2 布局族 × 2 变体 |
| V5 Shell 规格 | `app/services/ppt/v5/shell_system.py` | 1920x1080 页面 + 4 区域框架 + 调色板 + 排版 + 间距 |
| V6 内容预算 | `app/services/ppt/v6/models.py` → `ContentBudget` | max_visible_text_blocks=5, max_words_per_label=14, min_visual_area_ratio=0.38 |
| primitive 注册 | `app/services/ppt/v4/primitive_registry.py` | 每种页面系列的默认 primitive 映射 |

### V4 布局求解评分体系

```
总分 = 语义分(关键词匹配) + 节奏分(反重复惩罚) + 角色奖励 + 牌组偏好(确定性哈希)
```

- 防止连续 3+ 页使用同一家族
- 防止同一变体重复
- 控制牌组级家族使用比例

### V6 候选布局模板

| 布局 | 适用场景 | 区域划分 |
|------|---------|---------|
| `center_visual_right_notes` | 默认 | 左 62% 主视觉 + 右侧辅助 |
| `top_insight_center_visual` | 默认 | 顶部 insight + 中间大视觉 + 底部 |
| `full_visual_bottom_strip` | 默认 | 上 68% 大视觉 + 底部三列 |
| `evidence_mosaic` | evidence_board | 左 55% 主证据 + 右侧卡片 |
| `cover_hero` | cover_hero | 全幅封面 |

### 已知问题

1. **三代布局求解器并存**（v4/v5/v6），未统一，维护成本高
2. **text height 估算基于简单公式**，未考虑字体渲染差异

---

## 环节 7：视觉 renderer 生成专业 SVG / 图表 / 证据位 / 页面主体

### 状态：⚠️ 已完成但有问题（70%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| V6 SVG 调度器 | `app/services/ppt/v6/svg_renderer/renderer.py` | 按 diagram_type 分发到 5 种渲染器 |
| V6 封面渲染 | `app/services/ppt/v6/svg_renderer/cover.py` | 同心圆 + 标题 + 关键词胶囊 + 信号词 |
| V6 议程渲染 | `app/services/ppt/v6/svg_renderer/agenda.py` | 2×3 卡片网格 + 箭头连接 + 节奏标签 |
| V6 架构图渲染 | `app/services/ppt/v6/svg_renderer/architecture.py` | 分层布局 + 模块胶囊 + 层间箭头 |
| V6 流程图渲染 | `app/services/ppt/v6/svg_renderer/process_flow.py` | 横向步骤节点 + 贝塞尔箭头 + 反馈回路 |
| V6 证据板渲染 | `app/services/ppt/v6/svg_renderer/evidence_board.py` | 左侧大证据槽 + 右侧小卡片 + 底部结论 |
| V6 图元库 | `app/services/ppt/v6/svg_renderer/primitives.py` | pill/arrow/text_lines/wrap_label/svg_shell |
| V6 视觉令牌 | `app/services/ppt/v6/svg_renderer/tokens.py` | 配色方案 + 图表样式参数 |
| V5 AI Body 生成 | `app/services/ppt/v5/ai_passes.py` | AI 生成主体区 HTML + 3 次重试 + 质检 |
| V4 正式渲染引擎 | `app/services/ppt/v4/formal_render_engine.py`（156KB） | 生产级 HTML 渲染，15 种页面系列 |
| V4 图表子系统 | `app/services/ppt/v4/diagram_*.py`（6 个文件） | SVG 扁平/高级/2.5D 三种渲染 profile |
| HTML 生成器 | `app/services/ppt/html_generator.py`（1100+ 行） | AI 生成 + 模板降级 + Token 合规检查 |
| HTML 渲染器 | `app/services/ppt/html_renderer.py`（700+ 行） | Playwright 截图 + 缓存 + 尺寸适配 |

### V6 SVG 图表类型

| diagram_type | 渲染器 | 输出 |
|-------------|--------|------|
| `cover_signal` | `cover.py` | 封面信号图 |
| `route_map` | `agenda.py` | 议程路线图 |
| `layered_architecture` | `architecture.py` | 分层架构图 |
| `process_flow` | `process_flow.py` | 流程图 |
| `evidence_board` | `evidence_board.py` | 证据板 |

### V5 AI Body 生成流程

```
构建 prompt（系统提示 + 用户提示 + 构图约束）
→ 调用 AI 生成 body HTML
→ audit_ai_body_fragment() 质检（8 项检查）
→ 不通过则重试（最多 3 次）
→ 返回 body_html_fragment
```

### 已知问题

1. **V6 SVG 渲染器仅 5 种图表类型**，覆盖面有限（缺少甘特图、雷达图、对比矩阵等）
2. **V4 正式渲染引擎 156KB 过于庞大**，单文件 3500+ 行，维护困难
3. **V4 图表子系统的 SVG 渲染器是占位符**（`diagram_svg_renderer.py` 仅输出文本标签）
4. **AI Body 生成依赖 LLM**，质量不稳定，3 次重试后可能仍不通过
5. **HTML 生成器的 AI prompt 体系复杂**（V6/V7/V8 多版本叠加），维护成本高

---

## 环节 8：Shell 层整合封面、目录、标题、副标题、页脚、主题

### 状态：✅ 已完成（90%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| V5 Shell 系统 | `app/services/ppt/v5/shell_system.py` | ShellSpec 定义：4 区域框架 + 调色板 + 排版 + 间距 |
| V6 渲染引擎 | `app/services/ppt/v6/render_engine.py` | Shell 整合：grid-bg + shell-title + shell-subtitle + shell-body + footer |
| V4 风格预设 | `app/services/ppt/v4/style_presets.py` | 3 种预设：professional_clean / tech_premium / academic_formal |
| V5 渲染引擎 | `app/services/ppt/v5/render_engine.py` | `_page_shell()` 生成完整 HTML shell |
| V5 Safe Body | `app/services/ppt/v5/safe_body_renderer.py` | 非 AI 模式下的安全主体区渲染 |

### Shell 区域框架（V5）

```
title_frame:    x=84,  y=64,   w=1260, h=72    (标题)
subtitle_frame: x=84,  y=142,  w=1180, h=58    (副标题)
body_frame:     x=84,  y=224,  w=1752, h=764   (主体区)
footer_frame:   x=84,  y=1018, w=1752, h=28    (页脚)
```

### 风格预设（V4）

| 预设 | 背景 | 主色 | 卡片风格 | 标志元素 |
|------|------|------|---------|---------|
| `professional_clean` | 浅色 #F8FAFC | 深色 #0F172A | 实心, r=28 | clean_divider, metric_strip |
| `tech_premium` | 深色 #08111F | 蓝色 #4A9AFF | 玻璃态, r=30, 发光 | energy_bar, grid_background |
| `academic_formal` | 白色 #FFFFFF | 藏蓝 #1E3A8A | 描边, r=24, 无阴影 | section_rule, formal_footer |

### 已知问题

1. **封面页和内容页的 Shell 差异处理不够灵活**：封面隐藏标题/副标题/页脚的逻辑硬编码
2. **V4 的 3 种风格预设与 V5/V6 的主题系统未统一**

---

## 环节 9：自动视觉审查：溢出、重叠、空白、模板感、可读性、截图质量

### 状态：✅ 已完成（85%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| V5 审查器 | `app/services/ppt/v5/reviewer.py` | 结构分 + 视觉分 + 综合分 |
| V5 渲染布局审计 | `app/services/ppt/v5/render_layout_auditor.py` | Playwright 浏览器环境审计（9 项检查） |
| V5 嵌套画布审计 | `app/services/ppt/v5/nested_canvas_auditor.py` | 检测"HTML page inside PPT"失败模式 |
| V5 Body 布局审计 | `app/services/ppt/v5/body_layout_auditor.py` | AI 生成 body 后的 8 项预审 |
| V4 视觉审查 | `app/services/ppt/v4/visual_review_v4.py` | 单页 critic（硬门控 + 词库 + 图标 + 图表 + 节奏） |
| V4 牌组一致性 | `app/services/ppt/v4/deck_consistency_service.py` | 牌组级检查（重复标题、节奏同质化、焦点多样性） |
| V4 节奏审计 | `app/services/ppt/v4/rhythm_audit.py` | 验证 HTML 输出是否反映布局求解器的决策 |
| 视觉检察官 | `app/services/vision_judge_service.py` | 多模态视觉模型审查 HTML 截图 |
| 视觉质量评分 | `docs/visual_quality_rubric.md` | 100 分制评分标准（7 维度 + 9 项一票否决） |

### Playwright 渲染布局审计检查项

1. 元素溢出检测
2. 视觉利用率检查
3. 重复标题检测
4. 根容器背景检查
5. 嵌套画布检测
6. 深色遮挡块检测
7. 提示词泄露检测
8. 主视觉面积和位置检查
9. 卡片数量检查

### 视觉质量评分维度（100 分制）

| 维度 | 分值 |
|------|------|
| 叙事职责 | 15 |
| 视觉焦点 | 15 |
| 信息层级 | 15 |
| 专业表达 | 20 |
| 版式呼吸 | 15 |
| 比赛可信度 | 10 |
| 视觉完成度 | 10 |

**门槛**：< 82 分不得进入 renderer 抽象阶段，< 90 分不得进入生产主链。

### 已知问题

1. **视觉检察官依赖多模态 LLM**，成本高、速度慢，不适合全量页面审查
2. **V4 节奏审计的 72 个标记物需要手动维护**，与渲染引擎强耦合
3. **评分标准的 9 项一票否决过于严格**，实际通过率低

---

## 环节 10：Repair pass：把问题反馈给 AI 或系统重排

### 状态：⚠️ 已完成但有问题（70%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| V5 AI 修复 Pass | `app/services/ppt/v5/ai_passes.py` → `repair_ai_design_passes_from_render_audit()` | 接收审计失败项 → 重新生成 body |
| V4 修复规划器 | `app/services/ppt/v4/repair_planner.py` | 生成优先级修复动作预览 |
| API 修复端点 | `ppt_router.py` → `POST /task/{task_id}/pages/{page_index}/repair` | 单页定向修复 |
| API 批量修复 | `ppt_router.py` → `POST /task/{task_id}/pages/repair-batch` | 批量修复 |
| API 修复回滚 | `ppt_router.py` → `POST /task/{task_id}/pages/{page_index}/repair-rollback` | 回滚到快照 |
| 修复历史 | `ppt_router.py` → `GET /task/{task_id}/pages/{page_index}/repair-history` | 查看修复历史 |

### 修复流程

```
视觉审查发现问题
→ 生成 repair_brief（问题描述 + 修复指令）
→ 调用 AI 重新生成 body HTML
→ 审计新生成的 body
→ 用户确认采用 / 回滚
→ 更新页面 HTML
```

### 修复策略

| 策略 | 说明 |
|------|------|
| `switch_variant` | 切换布局变体 |
| `rebalance_regions` | 重新平衡区域 |
| `compress_copy` | 压缩文本 |
| `promote_evidence` | 提升证据优先级 |
| `align_with_deck_tokens` | 对齐牌组视觉令牌 |

### 已知问题

1. **修复成功率未统计**：缺少修复效果的量化追踪
2. **AI 修复可能引入新问题**：修复后需要再次审查，但未自动触发
3. **快照机制的存储成本**：每次修复都保存完整 HTML 快照
4. **批量修复的 max_pages 限制**：未根据问题严重程度智能排序

---

## 环节 11：Preview / HTML / PPTX 稳定生成，任务状态与超时控制

### 状态：⚠️ 已完成但有问题（65%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| HTML 渲染器 | `app/services/ppt/html_renderer.py` | Playwright 截图 + 缓存 + 尺寸适配 |
| PPTX 渲染器 | `app/services/ppt/pptx_renderer_html.py` | HTML 截图 → PPTX 幻灯片 |
| 任务路由 | `app/routers/ppt_router.py`（1057 行） | 完整任务生命周期 API |
| 模板路由 | `app/routers/ppt_generator_router.py` | 模板化 PPT 生成（同步/异步） |
| 任务状态 | SQLite/MySQL 持久化 | creating → generating → outline_generated → confirmed → completed/failed |
| 下载门控 | `ppt_router.py` → `get_task_deliverability()` | 不可交付的 P0 硬伤阻止下载（HTTP 409） |

### 渲染管线

```
AI 生成 HTML
→ Token 合规检查（ruipu_token.validate_html_compliance）
→ 视觉审查优化（综合评分 < 90 时触发）
→ 净化（presentation_sanitizer）
→ Playwright 截图（1920x1080, 网络空闲 + 字体加载 + ready 信号）
→ PPTX 组装（Blank 布局 + 图片填满）
```

### API 端点汇总

| 类别 | 端点数 | 关键端点 |
|------|--------|---------|
| 任务生命周期 | 7 | create, status, confirm, download, cancel, delete |
| 大纲管理 | 2 | retry, storyline-guard |
| 质量检查 | 3 | quality-summary, quality-check, visual-review |
| 路演健康 | 4 | roadshow-health, roadshow-structure, optimization-queue |
| 页面修复 | 5 | repair, repair/apply, repair-batch, repair-history, repair-rollback |
| 评分素材 | 5 | scoring-coverage, scoring-dashboard, materials, bindings |
| 风格管理 | 4 | themes, style-presets, style-preview, visual-style |

### 已知问题

1. **P0 端到端测试全部失败**：有效页数为 0，空壳页 7-27 个，竞品评分 5-22/100
2. **模板路由使用内存字典存储任务状态**，重启后丢失
3. **Playwright 截图的 ready 信号机制脆弱**：依赖 `window.__OREP_CAPTURE_READY__`，某些页面可能不触发
4. **PPTX 输出是截图嵌入**，非原生 PPTX 元素，无法编辑
5. **超时控制未显式实现**：依赖 FastAPI 的默认超时

---

## 环节 12：多真实问卷回归 + 人工审美验收，确认不同项目不会同质化

### 状态：⚠️ 部分完成（50%）

### 实现详情

| 模块 | 文件 | 功能 |
|------|------|------|
| 测试用例矩阵 | `tests/integration/test_case_matrix.py` | 16 个用例（P0×3, P1×5, P2×5, P3×3） |
| 回归测试定义 | `qa/regression_test_cases.md` | 用例详情 + 通过标准 + 执行频率 |
| 页系骨架回归 | `tools/page_series_regression.py` | 14 种页面系列 × 30 个探测点 |
| 定向验证 | `qa/run_targeted_validation_tasks.py` | 3 个叙事族定向验证 |
| V5 截图审查 | `qa/run_v5_screenshot_review.py` | V5 预览页面截图审查 |
| V5 预览验证 | `qa/run_v5_preview_validation.py` | 15 种目标页面系列覆盖检查 |
| 全流程测试 | `qa/run_questionnaire_full_flow.py` | 端到端全流程测试 |
| 代码审查清单 | `qa/CODE_REVIEW_CHECKLIST.md` | 5 维度 30 项检查 |
| 内容审查清单 | `qa/CONTENT_REVIEW_CHECKLIST.md` | 3 轮递进审查 |
| 视觉质量评分 | `docs/visual_quality_rubric.md` | 100 分制 + 9 项一票否决 |
| 单元测试 | `tests/test_v5_clean_pipeline.py`（746 行） | 24 个测试方法 |
| 单元测试 | `tests/test_v6_schema_ppt_renderer.py`（201 行） | 7 个测试方法 |

### 回归测试矩阵

| 优先级 | 数量 | 执行频率 | 覆盖行业 |
|--------|------|---------|---------|
| P0 Critical | 3 | 每次 PR | Healthcare, AIoT |
| P1 High | 5 | 每周 | Healthcare, Education, Manufacturing, Finance, Tech |
| P2 Medium | 5 | 每月 | 边界条件（极少/极多/缺失/特殊字符） |
| P3 Low | 3 | 每月 | 稳定性/并发/性能 |

### 质量指标基线

| 指标 | 目标值 | 严重程度 |
|------|--------|----------|
| 有效页数 | >= 35 | P0 |
| 空壳页 | <= 3 | P0 |
| SVG 图表 | >= 10 | P1 |
| 技能操作页 | >= 10 | P1 |
| 乱码字符 | = 0 | P0 |
| KPI 页面 | >= 8 | P1 |

### 当前测试结果

| 测试类型 | 最新结果 | 日期 |
|----------|---------|------|
| Sprint 1 P0 回归 | ❌ 3/3 全部失败 | 2026-04-15 |
| 页系骨架回归 | ✅ 30/30 全部通过 | 2026-04-28 |
| 端到端验收 | ⚠️ Task 107 warning, 106/102 blocked | 2026-04-27 |

### 已知问题

1. **P0 端到端测试全部失败**：核心问题是 PPT 页面内容为空
2. **页系骨架回归通过 ≠ 端到端可用**：骨架正确但内容缺失
3. **跨行业同质化风险**：知识库仅 5 个行业，相似项目可能生成相似内容
4. **人工审美验收缺少标准化流程**：视觉质量评分标准存在但未自动化执行
5. **Roadmap Week 2 及以后的任务均未开始**

---

## 整体架构评估

### 三代渲染引擎并存

```
V4 (46 个模块)          V5 (17 个模块)          V6 (10+ 模块)
├── 正式渲染引擎         ├── Clean Pipeline       ├── 纯确定性流水线
├── 7 阶段渐进迁移       ├── AI Body 生成         ├── 12 个数据模型
├── Shadow 侧车机制     ├── 叙事图 + 构图        ├── 5 种 SVG 渲染器
├── 15 种页面系列       ├── 16 种构图模板        ├── 布局评分求解
└── 156KB 正式渲染      └── 视觉审查 + 修复      └── 内容登记审计
```

**问题**：三代引擎各自独立，数据模型不统一，维护成本高。

### 关键断点

1. **大纲 → 内容填充**：Round 2/3 的内容填充质量不稳定，导致空壳页
2. **AI 生成 → 确定性渲染**：V5 的 AI Body 生成与 V6 的纯确定性渲染路线冲突
3. **骨架正确 → 内容可用**：页系骨架回归通过但端到端失败，说明中间链路有断裂
4. **审查 → 修复闭环**：修复成功率未量化，修复后可能引入新问题

### 建议优先级

| 优先级 | 事项 | 影响 |
|--------|------|------|
| P0 | 解决空壳页问题（端到端测试从 0 有效页提升到 35+） | 链路可用性 |
| P0 | 统一渲染引擎选型（V5 vs V6 二选一） | 维护成本 |
| P1 | 完善内容填充的兜底策略（用真实数据而非默认值） | 内容质量 |
| P1 | 自动化视觉质量评分（替代人工审查） | 验收效率 |
| P2 | 扩展 SVG 图表类型（甘特图、雷达图、对比矩阵） | 视觉丰富度 |
| P2 | 修复成功率统计 + 自动重审 | 修复闭环 |

---

## Roadmap 完成状态

### Week 1（立即）

- [x] 修复 bg_generator 方法名 Bug
- [x] 增强用户提示词内容填充原则
- [x] 增加数据来源标注规则
- [ ] 消除章节分隔空壳页（部分修改）

### Week 2

- [ ] 建立组件数据 Schema 统一规范
- [ ] 提取 _fix_empty_data_pages 到独立模块
- [ ] 增加技能操作页和 Before/After 对比页
- [ ] 语义驱动的组件选择
- [ ] 运行 P0 回归测试验证

### Month 2-4

- [ ] Pipeline 重构
- [ ] 视觉元素增强（动画、粒子、玻璃态）
- [ ] 图表类型扩展
- [ ] 消除循环依赖
