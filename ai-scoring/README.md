# OREP AI PPT 智能生成系统

> 项目代号：PitchForge
> 版本：1.0.0
> 描述：基于 AI 的 PPT 智能生成系统，支持多行业、多场景的演示文稿自动生成

---

## 项目概述

OREP AI PPT 智能生成系统是一款基于大语言模型（LLM）的智能 PPT 生成平台。系统通过多阶段 Pipeline 架构，将用户输入的数据自动转换为高质量的演示文稿。

### 核心能力

- **智能大纲生成**：基于语义分析自动生成 PPT 结构
- **多组件渲染引擎**：支持 KPI 卡片、SVG 图表、时间线、对比表格等多种组件
- **主题风格适配**：支持多种行业和场景的主题样式
- **数据驱动生成**：确保每页内容充实，避免空壳页

### 质量指标

| 指标 | 目标 | 描述 |
|------|------|------|
| 有效页数 | >=35 | 非空壳页 |
| 空壳页 | <=3 | 少于 20 字且少于 3 个图形元素 |
| SVG 图表 | >=10 | 嵌入式 SVG 图形 |
| KPI 页面 | >=8 | KPI 指标页面 |
| 乱码字符 | =0 | 无编码错误 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (前端开发)
- Docker (可选)

### 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 激活虚拟环境
source .venv/bin/activate
```

### 运行服务

```bash
# 启动后端服务
python main.py

# 或使用 Docker
docker build -t orep-ai-scoring .
docker run -p 8000:8000 orep-ai-scoring
```

### 访问 API

服务启动后，访问 `http://localhost:8000/docs` 查看 API 文档。

---

## 架构说明

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户请求                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: Outline Generation               │
│                    (AI 调用 - outline_generator.py)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 2: Data Validation & Enhancement          │
│                    (0 次 AI - data_validator.py)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 3: Layout & Structure                     │
│                    (0 次 AI - layout_rules.py)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Phase 4: Background Generation                  │
│              (AI 调用 - bg_generator.py, 可选)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Phase 5: Assembly & Render                  │
│                 (0 次 AI - assembly_engine.py)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       PPT 文件输出                           │
└─────────────────────────────────────────────────────────────┘
```

### 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| outline_generator | app/services/ppt/outline_generator.py | AI 大纲生成 |
| layout_rules | app/services/ppt/layout_rules.py | 布局规则引擎 |
| assembly_engine | app/services/ppt/assembly_engine.py | 组件装配引擎 |
| bg_generator | app/services/ppt/bg_generator.py | 背景图生成 |
| ppt_service | app/services/ppt/ppt_service.py | PPT 主服务 |

### 组件类型

| 组件 | 描述 |
|------|------|
| kpi_metrics | KPI 指标卡片 |
| bar_chart_svg | 柱状图 |
| pie_chart_svg | 饼图/圆环图 |
| line_chart_svg | 折线图 |
| comparison_table | 对比表格 |
| timeline_vertical | 垂直时间线 |
| section_divider | 章节分隔页 |
| cover | 封面页 |
| ending | 结束页 |

---

## 目录结构

```
ai-scoring/
├── app/                        # 应用代码
│   ├── routers/               # API 路由
│   ├── services/              # 业务服务
│   │   └── ppt/               # PPT 生成服务
│   │       ├── outline_generator.py
│   │       ├── layout_rules.py
│   │       ├── assembly_engine.py
│   │       ├── bg_generator.py
│   │       └── ppt_service.py
│   ├── models/                # 数据模型
│   └── utils/                  # 工具函数
├── docs/                       # 文档目录
├── standards/                  # 规范目录
├── prompts/                    # Prompt 模板
├── backend/                    # 后端代码
├── frontend/                   # 前端代码
├── qa/                         # QA 相关
├── tests/                      # 测试目录
│   └── integration/           # 集成测试
├── tools/                      # 工具脚本
├── WORK_LOG/                   # 工作日志
├── ORCHESTRATOR_BOARD.md       # 调度看板
├── DECISIONS_LOG.md            # 决策记录
├── AGENTS.md                   # Agent 团队协作总则
├── CHANGELOG.md                # 变更日志
└── README.md                   # 本文件
```

---

## 联系方式

- **项目维护者**：Tech Lead
- **Orchestrator**：项目调度中心
- **问题反馈**：通过 TASK_QUEUE 提交问题

---

## 变更历史

请参阅 [CHANGELOG.md](./CHANGELOG.md) 查看完整变更历史。
