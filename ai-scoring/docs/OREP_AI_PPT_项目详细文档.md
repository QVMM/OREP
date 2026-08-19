# OREP AI PPT 生成系统 - 详细技术文档

> 本文档描述基于 AI 的 PPT 生成系统的完整架构、运行逻辑和约束文档位置。

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目架构图](#2-项目架构图)
3. [目录结构详解](#3-目录结构详解)
4. [Pipeline 四轮执行流程](#4-pipeline-四轮执行流程)
5. [约束文档位置](#5-约束文档位置)
6. [核心模块说明](#6-核心模块说明)
7. [API 入口](#7-api-入口)
8. [数据流](#8-数据流)

---

## 1. 项目概述

### 1.1 项目名称
**OREP AI Scoring System** - 职业技能大赛 AI 智能评分与 PPT 生成系统

### 1.2 核心功能
通过 AI 将用户填写的问卷数据，自动生成专业的路演 PPT（HTML 格式）。

### 1.3 技术栈
| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| AI 模型 | 阿里云百炼 Qwen3 (qwen3.6-plus) |
| PPT 渲染 | HTML + CSS (1920x1080px) |
| 图表渲染 | SVG + Chart.js |
| 存储 | 文件系统 + MinIO |

### 1.4 关键特性
- **AI 生成 HTML**：不是模板填充，而是 AI 根据内容理解生成定制化 HTML
- **四轮 Pipeline**：结构化 → 叙事框架 → 内容充实 → HTML 生成
- **批量处理**：Round 3/4 批量处理避免 JSON 截断
- **自我检查**：内置质量审计机制

---

## 2. 项目架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OREP AI PPT 系统架构                              │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                           用户层 (User Layer)                           │
  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐   │
  │  │   前端 Web  │    │  问卷表单   │    │    管理后台              │   │
  │  │  (React)    │    │  (提交数据) │    │    (任务管理)            │   │
  │  └─────────────┘    └─────────────┘    └─────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                          API 层 (API Layer)                             │
  │  ┌─────────────────────────────────────────────────────────────────┐  │
  │  │                     /app/routers/ppt_router.py                    │  │
  │  │   POST /api/ppt/v2/task/create    ← 主要入口 (触发 Pipeline)     │  │
  │  │   POST /api/ppt/v2/questionnaire/submit                          │  │
  │  │   GET  /api/ppt/task/{id}/status                                 │  │
  │  │   GET  /api/ppt/task/{id}/download                               │  │
  │  └─────────────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                    Pipeline 协调层 (Pipeline Coordinator)                 │
  │  ┌─────────────────────────────────────────────────────────────────┐  │
  │  │     /app/services/ppt/adapter_code/pipeline_coordinator.py       │  │
  │  │                                                                   │  │
  │  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
  │  │   │ Round 1  │→ │ Round 2  │→ │ Round 3  │→ │ Round 4  │      │  │
  │  │   │ 结构化   │  │ 叙事框架 │  │ 内容充实 │  │ HTML生成 │      │  │
  │  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘      │  │
  │  │         │             │             │             │              │  │
  │  │         ▼             ▼             ▼             ▼              │  │
  │  │   ┌─────────────────────────────────────────────────────────┐  │  │
  │  │   │              Prompt 模板 (prompts/)                      │  │  │
  │  │   │   round1_structurize.md                                 │  │  │
  │  │   │   round2_narrative.md                                   │  │  │
  │  │   │   round3_enrich.md                                      │  │  │
  │  │   │   round4_html_generation.md                             │  │  │
  │  │   └─────────────────────────────────────────────────────────┘  │  │
  │  └─────────────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         AI 服务层 (AI Service Layer)                      │
  │  ┌─────────────────────────────────────────────────────────────────┐  │
  │  │              /app/services/ppt/qwen_client.py                  │  │
  │  │                                                                   │  │
  │  │                    阿里云百炼 API                                 │  │
  │  │                    Qwen3.6-plus                                 │  │
  │  │                    JSON Mode                                     │  │
  │  └─────────────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         输出层 (Output Layer)                           │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
  │  │ HTML 文件    │  │  PPTX 文件   │  │  结构化 JSON             │   │
  │  │ (预览)       │  │ (最终交付)   │  │  (中间结果)              │   │
  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │
  │         │                  │                    │                   │
  │         ▼                  ▼                    ▼                   │
  │  /output/pipeline_html/  /output/*.pptx    /output/result.json    │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构详解

```
/Users/liuyixing/项目/OREP/ai-scoring/
│
├── 📁 app/                              # FastAPI 主应用
│   ├── 📁 routers/                      # API 路由层
│   │   ├── ppt_router.py               # 【主入口】PPT 任务相关 API
│   │   ├── ppt_generator_router.py     # 可配置的 PPT 生成器路由
│   │   └── scoring_router.py            # 评分相关 API
│   │
│   ├── 📁 services/ppt/                # PPT 核心服务
│   │   ├── 📁 adapter_code/           # 【核心】Pipeline 适配代码
│   │   │   ├── pipeline_coordinator.py  # ⭐ Pipeline 协调器（核心）
│   │   │   ├── input_adapter.py         # 输入适配器
│   │   │   ├── output_adapter.py        # 输出适配器
│   │   │   └── config_switch.py         # 新旧系统切换配置
│   │   │
│   │   ├── 📁 prompts/                 # 【核心】AI Prompt 模板
│   │   │   ├── round1_structurize.md   # Round 1: 数据结构化
│   │   │   ├── round2_narrative.md     # Round 2: 叙事框架生成
│   │   │   ├── round3_enrich.md        # Round 3: 内容充实
│   │   │   ├── round4_html_generation.md # Round 4: AI 生成 HTML
│   │   │   └── self_check.md           # 自我检查
│   │   │
│   │   ├── qwen_client.py              # 阿里云百炼 API 客户端
│   │   ├── deepseek_client.py          # DeepSeek API 客户端
│   │   ├── questionnaire_schema.py       # 问卷 Schema 定义
│   │   │
│   │   ├── 📁 components/              # PPT 组件库（模板渲染用）
│   │   │   ├── base.py                 # 组件基类
│   │   │   ├── cover.py               # 封面组件
│   │   │   ├── toc.py                 # 目录组件
│   │   │   ├── kpi_metrics.py         # KPI 指标组件
│   │   │   ├── bar_chart_svg.py       # 柱状图 SVG
│   │   │   ├── line_chart_svg.py      # 折线图 SVG
│   │   │   └── ...                     # 更多组件
│   │   │
│   │   ├── 📁 html_templates/         # HTML 模板
│   │   ├── html_renderer.py            # HTML 渲染器
│   │   ├── html_generator.py           # HTML 生成器
│   │   └── assembly_engine.py          # 页面组装引擎
│   │
│   └── config.py                       # 应用配置
│
├── 📁 backend/                          # 后端服务（替代入口）
│   ├── 📁 routers/
│   ├── 📁 services/
│   │   ├── round1_service.py          # Round 1 服务
│   │   ├── round2_service.py          # Round 2 服务
│   │   ├── round3_service.py          # Round 3 服务
│   │   └── html_batch_service.py      # HTML 批量服务
│   └── main.py                        # FastAPI 入口
│
├── 📁 prompts/                         # Prompt 模板（根目录）
│   ├── round1/
│   ├── round2/
│   ├── round3/
│   └── EVALUATION_CRITERIA.md         # 评分标准
│
├── 📁 standards/                       # 标准规范
│   ├── ACCEPTANCE_CRITERIA/           # 验收标准
│   ├── CODING_STANDARDS.md           # 编码规范
│   └── DATA_FORMAT_SPEC.md           # 数据格式规范
│
├── 📁 docs/                           # 文档
│
├── 📁 tests/                          # 测试
├── 📁 output/                        # 【输出】生成的文件
│   ├── pipeline_result_full.json       # 完整 Pipeline 结果
│   ├── pipeline_html/                 # HTML 页面集合
│   │   ├── page_01.html
│   │   ├── page_02.html
│   │   │   └── ... (共 37 页)
│   │   └── page_37.html
│   └── test_questionnaire_*.json     # 测试问卷数据
│
├── uploads/                           # 用户上传文件
├── .env                              # 环境变量
└── requirements.txt                   # Python 依赖
```

---

## 4. Pipeline 四轮执行流程

### 4.1 流程概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Pipeline 四轮执行流程                               │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  输入: 用户问卷数据 (JSON)                                              │
  │  例: {"project_name": "智慧农业", "team": "xxx", ...}                │
  └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Round 1: 结构化 (Structurize)                                         │
  │  ────────────────────────────────────────────────────────────────────   │
  │  提示词: round1_structurize.md                                          │
  │  目的:   将原始问卷数据转换为结构化 JSON                                   │
  │  输出:   structured_data                                                │
  │  示例:                                                                   │
  │  {                                                                        │
  │    "project": {"name": "...", "core_problem": "..."},                   │
  │    "industry": {"pain_points": [...], "market_data": {...}},            │
  │    "stories": {"scene": "...", "key_difference": "..."},                │
  │    "tech": {"architecture": "...", "algorithms": [...]}                 │
  │  }                                                                        │
  │  超时: 60 秒                                                            │
  └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Round 2: 叙事框架 (Narrative Framework)                               │
  │  ────────────────────────────────────────────────────────────────────   │
  │  提示词: round2_narrative.md                                           │
  │  目的:   生成逐页 PPT 框架（叙事结构）                                    │
  │  输出:   narrative_framework (含 pages 数组)                              │
  │  示例:                                                                   │
  │  {                                                                        │
  │    "meta": {"total_pages": 37, ...},                                   │
  │    "pages": [                                                            │
  │      {"page_number": 1, "title": "...", "ppt_text": "...",             │
  │       "slide_role": "hook", "duration_sec": 30},                        │
  │      {"page_number": 2, "title": "...", "ppt_text": "...",             │
  │       "slide_role": "toc", "duration_sec": 45},                        │
  │      ...                                                                │
  │    ]                                                                    │
  │  }                                                                        │
  │  超时: 180 秒                                                           │
  └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Round 3: 内容充实 (Content Enrich)                                     │
  │  ────────────────────────────────────────────────────────────────────   │
  │  提示词: round3_enrich.md                                              │
  │  目的:   充实每页内容（口播稿、图表定义）                                 │
  │  批次:   每批 2 页（避免 JSON 截断）                                    │
  │  输出:   enriched_pages                                                 │
  │  示例:                                                                   │
  │  {                                                                        │
  │    "page_number": 1,                                                     │
  │    "title": "每8秒，一次停机",                                          │
  │    "ppt_text": "8秒｜一次停机｜损失200万+",                             │
  │    "speech_script": {                                                   │
  │      "full_text": "大家想象一个场景：工厂里的一台关键设备...",            │
  │      "duration_sec": 30,                                                │
  │      "word_count": 82                                                   │
  │    },                                                                    │
  │    "chart": {"needed": true, "type": "bar", "definition": {...}},       │
  │    "image": {"needed": false}                                          │
  │  }                                                                        │
  │  超时: 300 秒 × 19 批 = ~95 分钟                                        │
  └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Round 4: AI 生成 HTML (AI HTML Generation)                           │
  │  ────────────────────────────────────────────────────────────────────   │
  │  提示词: round4_html_generation.md                                     │
  │  目的:   AI 根据内容理解生成定制化 HTML（不是模板填充！）                 │
  │  批次:   每批 2 页                                                     │
  │  输出:   html_pages (HTML 字符串数组)                                    │
  │  特点:                                                                   │
  │  - AI 理解页面在 PPT 中的角色                                           │
  │  - AI 选择最合适的视觉表达方式                                          │
  │  - 生成的 HTML 是量身定制，不是填充模板                                  │
  │  超时: 600 秒 × 19 批 = ~190 分钟                                       │
  └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  自我检查 (Self-Check)                                                  │
  │  ────────────────────────────────────────────────────────────────────   │
  │  提示词: self_check.md                                                 │
  │  目的:   质量审计，检查内容问题                                         │
  │  输出:   check_report                                                   │
  │  示例:                                                                   │
  │  {                                                                        │
  │    "check_summary": {"critical_issues": 0, "warnings": 2},             │
  │    "issues": [...]                                                      │
  │  }                                                                        │
  │  超时: 60 秒                                                           │
  └─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  输出: 最终结果                                                        │
  │  ────────────────────────────────────────────────────────────────────   │
  │  {                                                                        │
  │    "meta": {"task_id": 123, "completed_at": "...", "duration": 6065},   │
  │    "structured_data": {...},      // Round 1 结果                       │
  │    "narrative_framework": {...},   // Round 2 结果                       │
  │    "enriched_pages": [...],       // Round 3 结果                       │
  │    "html_pages": [...],           // Round 4 结果 (HTML 字符串)         │
  │    "check_report": {...}          // 质量报告                           │
  │  }                                                                        │
  └─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 各轮次详细说明

| 轮次 | 名称 | 输入 | 输出 | Prompt 文件 | 批次大小 | 超时 |
|------|------|------|------|-------------|----------|------|
| Round 1 | 结构化 | 原始问卷 | structured_data | round1_structurize.md | 1 | 60s |
| Round 2 | 叙事框架 | structured_data | narrative_framework | round2_narrative.md | 1 | 180s |
| Round 3 | 内容充实 | narrative_framework | enriched_pages | round3_enrich.md | 2 | 300s/批 |
| Round 4 | HTML生成 | enriched_pages | html_pages | round4_html_generation.md | 2 | 600s/批 |
| Self-Check | 质量审计 | enriched_pages | check_report | self_check.md | 1 | 60s |

### 4.3 执行状态映射

```python
class PipelineStage(Enum):
    ROUND_1_STRUCTURIZE = "structuring"      # 进度 0-10%
    ROUND_2_NARRATIVE = "narrating"          # 进度 10-30%
    ROUND_3_ENRICH = "enriching"             # 进度 30-50%
    ROUND_4_HTML_GENERATION = "html_generating" # 进度 50-80%
    SELF_CHECK = "self_checking"              # 进度 80-90%
    RENDERING = "rendering"                  # 进度 90-98%
    COMPLETED = "completed"                  # 进度 100%
```

---

## 5. 约束文档位置

### 5.1 Prompt 约束文档

| 约束类型 | 文件路径 | 说明 |
|----------|----------|------|
| **Round 1 约束** | `/app/services/ppt/prompts/round1_structurize.md` | 数据结构化规则 |
| **Round 2 约束** | `/app/services/ppt/prompts/round2_narrative.md` | 叙事框架生成规则 |
| **Round 3 约束** | `/app/services/ppt/prompts/round3_enrich.md` | 内容充实规则（口播稿、图表定义） |
| **Round 4 约束** | `/app/services/ppt/prompts/round4_html_generation.md` | AI HTML 生成设计约束 |
| **质量检查** | `/app/services/ppt/prompts/self_check.md` | 自我检查规则 |

### 5.2 评分标准文档

| 文件路径 | 说明 |
|----------|------|
| `/prompts/EVALUATION_CRITERIA.md` | 15 项评分标准 |
| `/standards/ACCEPTANCE_CRITERIA/` | 各阶段验收标准 |

### 5.3 设计规范

| 文件路径 | 说明 |
|----------|------|
| `/app/services/ppt/prompts/round4_html_generation.md` 中的**色彩系统** | primary, secondary, accent 等颜色定义 |
| `/app/services/ppt/prompts/round4_html_generation.md` 中的**字体系统** | 中文、英文、数据字体及字号规范 |
| `/app/services/ppt/prompts/round4_html_generation.md` 中的**页面类型约束** | 封面、目录、章节、内容页的具体要求 |

### 5.4 Round 4 页面类型约束（重要）

```
**封面页（cover）**
- 主标题：72-80px，font-weight: 800，line-height: 1.4
- 两行主标题要分开，使用独立的div或足够行高（≥1.4倍）
- 副标题：28-32px，与主标题保持至少60px间距
- 分隔线：与下方内容保持40px间距
- 团队信息：与分隔线保持50px间距

**目录页（toc）**
- 章节标题：36-48px，清晰列出各章节
- 与封面页风格保持一致

**章节页（section）**
- 章节编号：大号数字（120-200px），半透明背景
- 章节标题：56-72px
- 副标题说明：24-28px

**内容页（content）**
- 页面标题：48-56px
- 正文内容：20-24px，line-height: 1.6
- 图表与文字对齐

**通用约束**
- 禁止字体重叠！
- 所有文字元素必须有足够间距
- 行高不低于1.4（标题）或1.6（正文）
```

---

## 6. 核心模块说明

### 6.1 PipelineCoordinator (核心协调器)

**文件**: `/app/services/ppt/adapter_code/pipeline_coordinator.py`

```python
class PipelineCoordinator:
    """协调四轮 Pipeline 执行的核心类"""

    async def execute(
        task_id: int,
        questionnaire_data: Dict[str, Any],
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """执行完整 Pipeline"""
        # 1. Round 1: 结构化
        ctx.structured_data = await self._execute_round_1(ctx)

        # 2. Round 2: 叙事框架
        ctx.narrative_framework = await self._execute_round_2(ctx)

        # 3. Round 3: 内容充实 (分批)
        ctx.enriched_pages = await self._execute_round_3(ctx)

        # 4. Round 4: AI 生成 HTML (分批)
        ctx.html_pages = await self._execute_round_4_html(ctx)

        # 5. 自我检查
        ctx.check_report = await self._execute_self_check(ctx)

        # 6. 返回结果
        return self._build_final_output(ctx)
```

### 6.2 QwenClient (AI 客户端)

**文件**: `/app/services/ppt/qwen_client.py`

```python
class QwenClient:
    """阿里云百炼 Qwen3 API 客户端"""

    async def chat(
        messages: List[Dict],
        model: str = "qwen3.6-plus",
        temperature: float = 0.3,
        max_tokens: int = 16000,
        json_mode: bool = True
    ) -> str:
        """发送聊天请求"""
        # 使用 httpx 发送 HTTP 请求
        # 返回 AI 响应内容
```

### 6.3 InputAdapter (输入适配器)

**文件**: `/app/services/ppt/adapter_code/input_adapter.py`

将旧格式问卷数据转换为 Pipeline 所需格式。

### 6.4 OutputAdapter (输出适配器)

**文件**: `/app/services/ppt/adapter_code/output_adapter.py`

将 Pipeline 输出转换为旧系统格式。

### 6.5 ConfigSwitch (配置切换)

**文件**: `/app/services/ppt/adapter_code/config_switch.py`

```python
class PipelineMode(Enum):
    OLD = "old"      # 使用旧模板系统
    NEW = "new"      # 使用新 Pipeline
    SHADOW = "shadow" # 同时运行，返回旧结果（用于验证）
```

---

## 7. API 入口

### 7.1 主入口

**文件**: `/app/routers/ppt_router.py`

```bash
# 创建 PPT 任务 (V2 - 使用新 Pipeline)
POST /api/ppt/v2/task/create
{
  "questionnaire_id": 123,
  "user_id": "user_xxx",
  "responses": {
    "project_name": "智慧农业物联网大数据平台",
    "team_name": "田野智联团队",
    ...
  }
}

# 响应
{
  "task_id": 9999,
  "status": "generating",
  "message": "PPT 生成任务已创建"
}
```

### 7.2 任务状态查询

```bash
GET /api/ppt/task/{task_id}/status

# 响应
{
  "task_id": 9999,
  "status": "completed",
  "progress": 100,
  "stages": {
    "structuring": "completed",
    "narrating": "completed",
    "enriching": "completed",
    "html_generating": "completed"
  }
}
```

### 7.3 下载生成的 PPT

```bash
GET /api/ppt/task/{task_id}/download
# 返回 PPTX 文件或 HTML zip
```

---

## 8. 数据流

### 8.1 完整数据流

```
用户问卷数据 (JSON)
       │
       ▼
┌──────────────────┐
│   InputAdapter    │  格式转换
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  Round 1         │  AI 结构化
│  (Qwen API)       │
└──────────────────┘
       │
       ▼ structured_data
┌──────────────────┐
│  Round 2         │  AI 生成叙事框架
│  (Qwen API)       │
└──────────────────┘
       │
       ▼ narrative_framework
┌──────────────────┐
│  Round 3         │  AI 充实内容 (分批)
│  (Qwen API)       │  每批 2 页
└──────────────────┘
       │
       ▼ enriched_pages
┌──────────────────┐
│  Round 4         │  AI 生成 HTML (分批)
│  (Qwen API)       │  每批 2 页
└──────────────────┘
       │
       ▼ html_pages
┌──────────────────┐
│  Self-Check      │  AI 质量审计
│  (Qwen API)       │
└──────────────────┘
       │
       ▼ check_report
┌──────────────────┐
│  OutputAdapter    │  格式转换
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  文件输出         │
│  - HTML 文件     │
│  - PPTX 文件     │
│  - JSON 结果     │
└──────────────────┘
```

### 8.2 文件输出

| 文件类型 | 路径 | 说明 |
|----------|------|------|
| 完整结果 | `/output/pipeline_result_full.json` | 包含所有轮次结果的 JSON |
| HTML 页面 | `/output/pipeline_html/page_XX.html` | 37 个独立 HTML 文件 |
| PPTX 文件 | `/output/{task_id}.pptx` | 最终可下载的 PPTX |

---

## 9. 测试相关

### 9.1 测试脚本

| 文件 | 说明 |
|------|------|
| `test_full_pipeline.py` | 完整 Pipeline 测试 |
| `test_qwen_api.py` | Qwen API 连接测试 |
| `extract_html.py` | 提取 HTML 页面的脚本 |

### 9.2 测试问卷数据

```
/output/test_questionnaire_智慧农业.json
```

包含完整的"智慧农业物联网大数据平台"项目问卷数据。

---

## 10. 快速参考

### 10.1 核心文件路径速查

| 功能 | 文件路径 |
|------|----------|
| Pipeline 协调器 | `app/services/ppt/adapter_code/pipeline_coordinator.py` |
| Round 1 Prompt | `app/services/ppt/prompts/round1_structurize.md` |
| Round 2 Prompt | `app/services/ppt/prompts/round2_narrative.md` |
| Round 3 Prompt | `app/services/ppt/prompts/round3_enrich.md` |
| Round 4 Prompt | `app/services/ppt/prompts/round4_html_generation.md` |
| Qwen API 客户端 | `app/services/ppt/qwen_client.py` |
| API 路由 | `app/routers/ppt_router.py` |

### 10.2 环境变量

```bash
# .env 文件
DASHSCOPE_API_KEY=sk-xxxxxxxx    # 阿里云百炼 API Key
DEEPSEEK_API_KEY=sk-xxxxxxxx      # DeepSeek API Key (备用)
MINIMAX_API_KEY=xxxxxxxx         # MiniMax API Key
```

---

## 11. 附录

### 11.1 术语表

| 术语 | 说明 |
|------|------|
| Pipeline | 流水线，多阶段 AI 处理流程 |
| Round | Pipeline 的一个处理阶段 |
| structured_data | Round 1 输出的结构化数据 |
| narrative_framework | Round 2 输出的叙事框架 |
| enriched_pages | Round 3 充实后的页面内容 |
| html_pages | Round 4 AI 生成的 HTML 页面 |
| check_report | 质量审计报告 |

### 11.2 相关文档

- `/docs/ARCHITECTURE_DECISIONS.md` - 架构决策记录
- `/docs/SPRINT_PLAN.md` - Sprint 计划
- `/WORK_LOG/` - 开发工作日志

---

*文档生成时间: 2026-04-15*
