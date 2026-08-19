# Data Format Specification

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

## 一、用户输入数据 Schema

### 1.1 问卷提交请求 (QuestionnaireSubmitRequest)

用户通过问卷表单提交的数据，作为 PPT 生成的输入。

```json
{
    "user_id": 123,
    "tenant_id": 1,
    "project_name": "智能医疗诊断系统",
    "team_name": "创新先锋队",
    "industry": "medical",
    "responses": {
        "section_id": {
            "field_id": "field_value"
        }
    }
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | integer | 是 | 用户ID，> 0 |
| tenant_id | integer | 是 | 租户ID，> 0 |
| project_name | string | 是 | 项目名称，2-50字符 |
| team_name | string | 否 | 团队名称 |
| industry | string | 是 | 行业领域，枚举值 |
| responses | object | 是 | 问卷答案，key为section_id，value为该section的答案 |

**industry 枚举值**：

| 值 | 说明 |
|----|------|
| tech | 信息技术/软件 |
| ai_iot | 人工智能/物联网 |
| education | 教育培训 |
| medical | 医疗健康 |
| finance | 金融科技 |
| manufacturing | 智能制造 |
| agriculture | 智慧农业 |
| logistics | 智慧物流 |
| energy | 新能源/环保 |
| other | 其他 |

### 1.2 task_data 内部存储格式

系统内部存储的完整任务数据。

```json
{
    "task_id": 123,
    "questionnaire_id": 456,
    "user_id": 123,
    "tenant_id": 1,
    "status": "pending|processing|completed|failed",
    "industry": "medical",
    "project_name": "智能医疗诊断系统",
    "team_name": "创新先锋队",
    "theme": "dark_tech",
    "outline_json": {
        "pages": [
            {
                "page_index": 1,
                "semantic": "COVER",
                "title": "智能医疗诊断系统",
                "data": {}
            }
        ]
    },
    "created_at": "2026-04-15T10:30:00Z",
    "updated_at": "2026-04-15T10:35:00Z"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | integer | 是 | 任务ID |
| questionnaire_id | integer | 是 | 问卷ID |
| user_id | integer | 是 | 用户ID |
| tenant_id | integer | 是 | 租户ID |
| status | string | 是 | 任务状态枚举 |
| industry | string | 是 | 行业领域 |
| project_name | string | 是 | 项目名称 |
| team_name | string | 否 | 团队名称 |
| theme | string | 否 | 主题名称，默认 "dark_tech" |
| outline_json | object | 是 | 大纲JSON结构 |
| created_at | datetime | 是 | 创建时间 ISO 8601 |
| updated_at | datetime | 是 | 更新时间 ISO 8601 |

**status 枚举值**：

| 值 | 说明 |
|----|------|
| pending | 等待处理 |
| processing | 处理中 |
| completed | 已完成 |
| failed | 失败 |

---

## 二、PPT 内部数据 Schema

### 2.1 Page 结构

PPT 由多个 Page 组成，每个 Page 包含以下结构：

```json
{
    "page_index": 1,
    "semantic": "COVER",
    "layout_id": "cover_layout",
    "title": "页面标题",
    "subtitle": "副标题（可选）",
    "key_points": ["要点1", "要点2", "要点3"],
    "data": {
        "component_specific_data": {}
    },
    "bg_image_url": "https://...",
    "auto": false
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page_index | integer | 是 | 页码，从1开始 |
| semantic | string | 是 | 语义类型，12种枚举 |
| layout_id | string | 是 | 布局ID |
| title | string | 是 | 页面标题 |
| subtitle | string | 否 | 副标题 |
| key_points | array | 否 | 要点列表 |
| data | object | 否 | 组件特定数据 |
| bg_image_url | string | 否 | AI生成的背景图URL |
| auto | boolean | 否 | 是否为空壳页（auto=true表示无实质数据） |

### 2.2 语义类型 (Semantic Types)

| 语义类型 | 说明 | 固定页 | 最大页数 |
|----------|------|--------|----------|
| COVER | 封面页 | 是(第1页) | 1 |
| TOC | 目录页 | 是(第2页) | 1 |
| SECTION_DIVIDER | 章节分隔页 | 自动插入 | 8 |
| ENDING | 结尾页 | 是(最后页) | 1 |
| BACKGROUND_DATA | 背景数据页 | 否 | 不限 |
| PAIN_POINTS | 痛点分析页 | 否 | 不限 |
| SOLUTION_ARCH | 方案架构页 | 否 | 不限 |
| SKILL_STEPS | 技能操作页 | 否 | 不限 |
| DATA_COMPARE | 数据对比页 | 否 | 不限 |
| TEAM_INTRO | 团队介绍页 | 否 | 1 |
| ACHIEVEMENT | 成果展示页 | 否 | 不限 |
| FUTURE_PLAN | 未来规划页 | 否 | 不限 |

### 2.3 component_data 结构

组件数据根据组件类型有不同的结构。

**KPI Metrics 组件 (kpi_metrics)**：

```json
{
    "metrics": [
        {
            "value": "5000",
            "unit": "亿元",
            "label": "市场规模",
            "source": "艾瑞咨询2024"
        },
        {
            "value": "35%",
            "unit": "",
            "label": "年增长率",
            "source": "行业报告"
        }
    ]
}
```

**Bar Chart 组件 (bar_chart_svg)**：

```json
{
    "items": [
        {"label": "2021", "value": 100},
        {"label": "2022", "value": 150},
        {"label": "2023", "value": 220},
        {"label": "2024", "value": 350}
    ],
    "title": "市场规模增长趋势",
    "unit": "亿元"
}
```

**Pie Chart 组件 (pie_chart_svg)**：

```json
{
    "segments": [
        {"label": "市场份额A", "value": 35, "color": "#1E88E5"},
        {"label": "市场份额B", "value": 25, "color": "#00E5FF"},
        {"label": "市场份额C", "value": 20, "color": "#7C4DFF"},
        {"label": "其他", "value": 20, "color": "#6B8299"}
    ],
    "title": "市场竞争格局"
}
```

**Timeline 组件 (timeline_vertical)**：

```json
{
    "steps": [
        {
            "step_name": "数据采集",
            "sub_steps": [
                {
                    "action": "使用传感器采集原始数据",
                    "key_point": "采样频率不低于100Hz",
                    "result": "获取10000+条有效数据",
                    "tool": "高精度传感器"
                }
            ]
        }
    ]
}
```

**Comparison Table 组件 (comparison_table)**：

```json
{
    "headers": ["指标", "我们的方案", "竞品A", "竞品B"],
    "rows": [
        ["准确率", "98.5%", "92%", "95%"],
        ["响应时间", "<100ms", "<500ms", "<300ms"],
        ["成本", "降低40%", "基准", "降低10%"]
    ],
    "title": "方案对比"
}
```

### 2.4 主题变量 (Theme Variables)

主题定义了 PPT 的视觉风格，包括颜色、字体、阴影等。

**颜色变量 (color)**：

```json
{
    "bg_primary": "#0B1A2B",
    "bg_secondary": "#0F2744",
    "primary": "#1E88E5",
    "accent": "#00E5FF",
    "secondary": "#FFFFFF",
    "text_primary": "#FFFFFF",
    "text_secondary": "#B0C4DE",
    "text_muted": "#6B8299",
    "glow_color": "rgba(0,229,255,0.4)"
}
```

**阴影变量 (shadow)**：

```json
{
    "layered": "0 2px 4px rgba(0,0,0,0.5)",
    "glow": "0 0 20px rgba(0,86,211,0.4)"
}
```

**形状变量 (shape)**：

```json
{
    "border_radius": "8px"
}
```

**字体变量 (font)**：

```json
{
    "title": {
        "font": "'Noto Sans SC', sans-serif",
        "weight": "700",
        "size": "36px"
    },
    "body": {
        "font": "'Noto Sans SC', sans-serif",
        "weight": "400",
        "size": "16px"
    }
}
```

---

## 三、API 请求/响应 Schema

### 3.1 端点格式

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/ppt/health | 健康检查 |
| GET | /api/ppt/forms/{domain} | 获取领域表单配置 |
| POST | /api/ppt/questionnaire/submit | 提交问卷数据 |
| POST | /api/ppt/task/create | 创建PPT生成任务 |
| GET | /api/ppt/task/{task_id} | 获取任务详情 |
| GET | /api/ppt/task/{task_id}/status | 获取任务状态 |
| POST | /api/ppt/task/{task_id}/confirm | 确认大纲并生成PPT |
| GET | /api/ppt/task/{task_id}/download | 下载PPT文件 |
| GET | /api/ppt/user/{user_id}/tasks | 获取用户任务列表 |
| GET | /api/ppt/themes | 获取可用主题列表 |
| GET | /api/ppt/questionnaire/schema | 获取完整问卷Schema |
| GET | /api/ppt/scoring/criteria | 获取评分标准 |

### 3.2 通用响应格式

**成功响应**：

```json
{
    "success": true,
    "data": {
        // 业务数据
    }
}
```

**分页响应**：

```json
{
    "success": true,
    "data": {
        "items": [],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5
    }
}
```

### 3.3 错误响应格式

```json
{
    "success": false,
    "error": {
        "code": "TASK_NOT_FOUND",
        "message": "任务不存在",
        "details": {
            "task_id": 123
        }
    }
}
```

### 3.4 错误码定义

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| UNAUTHORIZED | 401 | 未认证 |
| FORBIDDEN | 403 | 无权限 |
| TASK_NOT_FOUND | 404 | 任务不存在 |
| QUESTIONNAIRE_NOT_FOUND | 404 | 问卷不存在 |
| FORM_NOT_FOUND | 404 | 表单配置不存在 |
| THEME_NOT_FOUND | 404 | 主题不存在 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| AI_SERVICE_ERROR | 500 | AI服务调用失败 |
| DATABASE_ERROR | 500 | 数据库操作失败 |

### 3.5 关键 API 详细 Schema

#### POST /api/ppt/questionnaire/submit

**请求体**：

```json
{
    "user_id": 123,
    "tenant_id": 1,
    "domain": "medical",
    "project_name": "智能医疗诊断系统",
    "team_name": "创新先锋队",
    "responses": {
        "basic_info": {
            "project_name": "智能医疗诊断系统",
            "team_name": "创新先锋队",
            "school_name": "XX职业技术学院",
            "industry": "medical",
            "team_members": "4人团队，包含..."
        },
        "background": {
            "strategic_alignment": "对接《十四五》...",
            "industry_trend": "市场规模...",
            "social_need": "解决...",
            "project_significance": "..."
        }
    }
}
```

**响应**：

```json
{
    "success": true,
    "data": {
        "questionnaire_id": 456,
        "status": "submitted",
        "created_at": "2026-04-15T10:30:00Z"
    }
}
```

#### POST /api/ppt/task/create

**请求体**：

```json
{
    "questionnaire_id": 456,
    "user_id": 123,
    "tenant_id": 1,
    "theme": "dark_tech"
}
```

**响应**：

```json
{
    "success": true,
    "data": {
        "task_id": 123,
        "status": "pending",
        "created_at": "2026-04-15T10:30:00Z"
    }
}
```

#### GET /api/ppt/task/{task_id}

**响应**：

```json
{
    "success": true,
    "data": {
        "task_id": 123,
        "questionnaire_id": 456,
        "user_id": 123,
        "tenant_id": 1,
        "status": "completed",
        "industry": "medical",
        "project_name": "智能医疗诊断系统",
        "theme": "dark_tech",
        "outline_json": {
            "pages": [...]
        },
        "created_at": "2026-04-15T10:30:00Z",
        "updated_at": "2026-04-15T10:35:00Z"
    }
}
```

#### GET /api/ppt/themes

**响应**：

```json
{
    "success": true,
    "data": {
        "themes": [
            {
                "id": "tech_dark",
                "name": "科技深蓝",
                "description": "科技、互联网、AI项目",
                "preview_url": "/themes/tech_dark.png"
            },
            {
                "id": "tech_purple",
                "name": "科技紫蓝",
                "description": "创新科技、未来感项目",
                "preview_url": "/themes/tech_purple.png"
            }
        ]
    }
}
```

---

## 四、数据库表结构

### 4.1 ppt_questionnaire 表

存储用户提交的问卷数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| user_id | INT | 用户ID |
| tenant_id | INT | 租户ID |
| domain | VARCHAR(50) | 行业领域 |
| project_name | VARCHAR(100) | 项目名称 |
| team_name | VARCHAR(100) | 团队名称 |
| responses | JSON | 问卷答案JSON |
| status | VARCHAR(20) | 状态 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### 4.2 ppt_task 表

存储 PPT 生成任务。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| questionnaire_id | INT | 关联问卷ID |
| user_id | INT | 用户ID |
| tenant_id | INT | 租户ID |
| status | VARCHAR(20) | 任务状态 |
| industry | VARCHAR(50) | 行业 |
| project_name | VARCHAR(100) | 项目名称 |
| theme | VARCHAR(50) | 主题 |
| outline_json | JSON | 大纲JSON |
| ppt_file_path | VARCHAR(500) | PPT文件路径 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

---

## 五、附录

### A. 可用主题列表

| 主题ID | 名称 | 适用场景 |
|--------|------|----------|
| tech_dark | 科技深蓝 | 科技、互联网、AI项目 |
| tech_purple | 科技紫蓝 | 创新科技、未来感项目 |
| business_dark | 商务深灰 | 企业汇报、商务项目 |
| launch_black | 发布会黑 | 产品发布、路演竞赛 |
| education_blue | 教育蓝绿 | 教育、培训、院校项目 |
| medical_clean | 医疗洁净 | 医疗健康、生物科技 |
| finance_gold | 金融金蓝 | 金融、保险、投资 |
| agriculture_green | 农业绿金 | 农业、环保、可持续发展 |
|物流_blue | 物流蓝 | 物流、运输、供应链 |

### B. 页面尺寸规范

| 属性 | 值 |
|------|-----|
| 宽度 | 1280px |
| 高度 | 720px |
| 比例 | 16:9 |
