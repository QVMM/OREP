# Sprint 计划

> 项目代号：PitchForge
> 版本：1.0.0
> 维护者：Tech Lead

---

## Sprint 0：项目初始化（当前）

**目标**：建立项目基础设施和团队协作规范

### 任务清单

| 任务 ID | 名称 | 负责人 | 状态 |
|---------|------|--------|------|
| T000 | 发布 README、创建目录结构 | Tech Lead | 进行中 |
| T001 | 制定编码规范 | Standards Keeper | 待启动 |
| T002 | 制定数据格式规范 | Standards Keeper | 待启动 |

### 产出物

- [x] README.md
- [ ] docs/SPRINT_PLAN.md（本文档）
- [ ] docs/ARCHITECTURE_DECISIONS.md
- [ ] standards/CODING_STANDARDS.md
- [ ] standards/DATA_FORMAT_SPEC.md

---

## Sprint 1：架构优化与核心修复

**目标**：修复已知 Bug，优化核心 Pipeline 架构

**预计周期**：1-2 周

### 主要任务

#### 1.1 修复 bg_generator 方法名 Bug

**问题**：`bg_generator.py` 方法名不匹配导致 AI 背景图生成完全失效

**位置**：`ppt_service.py` 第 267 行

**修复**：将 `batch_generate` 改为 `generate_batch`

**影响页面**：COVER/SECTION_DIVIDER/ENDING 页面

**状态**：待修复

#### 1.2 消除章节分隔空壳页

**问题**：11 个章节分隔页只有大号数字，无实质内容

**方案**：在 `layout_rules.py` 中修改章节分隔页生成逻辑，添加 3-5 个章节要点

**预期效果**：47 页 -> 36 页左右，每页都有实质内容

**状态**：待实现

#### 1.3 建立组件数据 Schema 统一规范

**问题**：各组件期望的字段不统一（metrics/items/segments/values 等）

**方案**：建立 `COMPONENT_DATA_SCHEMAS` 统一规范

**产出**：
- component_schemas.py
- normalize_component_data() 函数

**状态**：待设计

#### 1.4 提取 _fix_empty_data_pages 到独立模块

**问题**：`_fix_empty_data_pages` 混合在 layout_rules 中，职责不清

**方案**：提取到 `data_validator.py`

**职责划分**：
```
Phase 1: Outline Generation
└─ _validate_and_normalize_pages()  // 新增：统一数据格式 + 空壳修复

Phase 2: Data Validation（原 layout_rules 的 Step 6）
└─ validate_metrics_integrity()  // 提取到这里
```

**状态**：待实现

---

## Sprint 2：增强功能与组件扩展

**目标**：增加新组件类型，提升生成质量

**预计周期**：2-3 周

### 主要任务

#### 2.1 增加技能操作页和 Before/After 对比页

**目标**：
- 技能操作页 >= 2 页
- Before/After 对比页 >= 1 页

**方案**：
1. 在 `outline_generator.py` 中增加技能操作页生成规则
2. 添加 Before/After 对比页模板

#### 2.2 语义驱动的组件选择

**问题**：`data_layout` 路由仅基于字段存在性，不考虑语义

**方案**：改为语义驱动的组件选择

```python
SEMANTIC_TO_COMPONENT = {
    "BACKGROUND_DATA": {
        "default": "kpi_metrics",
        "chart_types": {
            "market_share": "pie_chart_svg",
            "trend": "line_chart_svg",
            "comparison": "bar_chart_svg"
        }
    },
    "DATA_COMPARE": {"default": "comparison_table"},
    "SKILL_STEPS": {"default": "timeline_vertical"}
}
```

#### 2.3 增加数据来源标注

**问题**：竞品有"艾瑞咨询 2024"等数据来源标注，我们没有

**方案**：在 `outline_generator.py` 的系统提示词中添加数据来源标注要求

#### 2.4 视觉元素增强

**目标**：缩小与竞品的视觉差距

| 元素 | 当前状态 | 目标 | 实施难度 |
|------|---------|------|----------|
| 粒子动画 | 无 | 每页 20 个 | 高 |
| 环形旋转动画 | 无 | 封面+结束页 | 高 |
| 渐入动画组合 | 无 | 每页 1-2 种 | 中 |
| 玻璃态卡片 | 无 | 内容页卡片 | 中 |
| 进度条/达成率 | 无 | 痛点页 | 中 |

---

## Sprint 3：Pipeline 重构与长期优化

**目标**：建立清晰的 Phase 划分，消除循环依赖

**预计周期**：1 个月+

### 主要任务

#### 3.1 Pipeline 重构

**目标**：建立清晰的 Phase 划分

```
Phase 1: Outline Generation (AI 调用)
└─ outline_generator.py
   ├─ generate()
   ├─ _parse_semantic_sequence()
   └─ _normalize_page_data()  // 新增：统一数据格式

Phase 2: Data Validation & Enhancement (0 次 AI)
└─ data_validator.py  // 新增模块
   ├─ validate_and_fix_empty_pages()
   └─ validate_metrics_integrity()

Phase 3: Layout & Structure (0 次 AI)
└─ layout_rules.py（精简，只保留布局相关）

Phase 4: Background Generation (AI 调用 - 可选)
└─ bg_generator.py（修复方法名）

Phase 5: Assembly & Render (0 次 AI)
└─ assembly_engine.py（简化路由逻辑）
```

#### 3.2 图表类型扩展

**当前**：只有 KPI 卡片 + SVG 圆环

**目标**：增加柱状图/折线图/架构图/仪表盘

**方案**：
1. 扩展 `bar_chart_svg.py` 支持更多数据格式
2. 新增 `architecture_diagram.py` 组件
3. 新增 `dashboard_svg.py` 仪表盘组件

#### 3.3 消除循环依赖

**问题**：`outline_generator.py` <-> `layout_rules.py` 循环调用

**方案**：提取共同接口到 `page_semantics.py`

```
outline_generator.py
    ├─> page_semantics.py (提取接口)
    └─> layout_rules.py (单向调用)

layout_rules.py
    └─> page_semantics.py (单向调用)
```

---

## 质量指标

| 指标 | 当前基线 | Sprint 1 目标 | Sprint 2 目标 | Sprint 3 目标 |
|------|---------|--------------|--------------|---------------|
| 有效页数 | 29 | >=32 | >=35 | >=35 |
| 空壳页 | 11 | <=6 | <=3 | <=3 |
| 空壳率 | 23% | <=15% | <=8% | <=8% |
| SVG 图表 | 13 | >=12 | >=10 | >=10 |
| KPI 页面 | - | >=6 | >=8 | >=8 |
| 技能操作页 | 0 | - | >=2 | >=2 |

---

## 测试计划

| Case ID | 名称 | 优先级 | 计划 Sprint |
|---------|------|--------|-------------|
| P0-001 | Baseline-Test Task 54 | P0_Critical | Sprint 1 |
| P0-002 | Multi-industry Regression-Healthcare | P0_Critical | Sprint 1 |
| P0-003 | Multi-industry Regression-AIIoT | P0_Critical | Sprint 1 |
| P1-001 | Healthcare Full Test | P1_High | Sprint 2 |
| P1-002 | Education Industry Test | P1_High | Sprint 2 |
| P1-003 | Manufacturing Industry Test | P1_High | Sprint 2 |
| P2-001 | Minimal Data Test | P2_Medium | Sprint 2 |
| P3-001 | Stability-Multiple Runs | P3_Low | Sprint 3 |

---

## 风险登记

| 风险 | 影响 | 概率 | 应对策略 |
|------|------|------|----------|
| AI 生成质量不稳定 | 高 | 中 | 增加后置验证步骤 |
| Pipeline 重构影响范围大 | 高 | 中 | 分阶段实施，充分测试 |
| 外部 API 网络问题 | 中 | 中 | 添加降级策略 |
| 循环依赖难以消除 | 中 | 低 | 提前设计接口边界 |

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|--------|
| 1.0.0 | 2026-04-15 | 初始版本 | Tech Lead |
