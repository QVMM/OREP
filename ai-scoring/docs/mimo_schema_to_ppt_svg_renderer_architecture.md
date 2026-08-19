# MiMo Schema To PPT SVG Renderer Architecture

## 目标

这份方案的目标不是继续修某一个任务，也不是继续加固定模板，而是重构 HTML PPT 的生成方式：

> MiMo 负责理解内容、判断表达方式和规划图解语义；系统负责可控排版、专业 SVG 渲染、稳定落版和自动验收。

核心原则：

- 不让 MiMo 直接自由生成整页 HTML。
- 不让系统用固定整页模板套内容。
- 不让 MiMo 直接自由绘制复杂 SVG。
- 系统固定的是安全规则、图解语法、视觉 token 和审查标准，不固定每页长相。
- 页面主体区应像 PPT，不像网页容器、后台页面或模板卡片堆叠。

## 总体架构

新的生成链路拆成 8 层：

```text
1. Content Understanding Pass
   理解每页内容、删减冗余、提炼主论点

2. Page Expression Planner
   判断每页应该用什么专业表达方式

3. Composition Director
   生成页面主体区构图意图，不生成 HTML

4. Layout Solver
   系统根据构图意图计算安全区域和元素尺寸

5. Diagram Schema Planner
   MiMo 为架构图/流程图/图表/证据板输出结构化 schema

6. PPT SVG Renderer
   系统根据 schema 和区域尺寸生成专业 SVG

7. Safe Page Renderer
   系统把标题、副标题、页脚、SVG、文字、图片证据位安全落版

8. Visual Auditor + Repair Loop
   截图/DOM 审查，不通过则局部返工或重排
```

关键变化：

- MiMo 不再直接生成整页 HTML。
- MiMo 不再直接控制最终坐标。
- MiMo 不再直接自由画复杂 SVG。
- 系统不再套固定模板。
- 系统只做可变构图、安全排版、专业图解渲染和质量验收。

## 1. Content Understanding Pass

输入是 Round 3 或 MiMo 生成后的每页内容。

示例输入：

```json
{
  "page_index": 11,
  "title": "端-边-云三层架构",
  "raw_points": [
    "端侧采集传感器数据",
    "边缘网关完成协议适配和预处理",
    "云端平台完成模型分析和可视化"
  ],
  "speaker_intent": "说明系统如何稳定完成从采集到决策的闭环"
}
```

这一层做：

- 去重。
- 清理提示词污染。
- 提炼主论点。
- 判断内容密度。
- 判断是否需要图片证据。
- 判断是否需要专业图解。
- 判断是否需要拆页。

示例输出：

```json
{
  "core_message": "端-边-云协同形成从采集到决策的闭环",
  "supporting_facts": [
    "端侧负责多源数据采集",
    "边缘侧完成协议适配与预处理",
    "云端完成 AI 分析与可视化"
  ],
  "content_density": "medium",
  "needs_evidence_image": false,
  "needs_diagram": true
}
```

## 2. Page Expression Planner

这一层判断页面最适合的专业表达方式。

表达类型包括：

```text
cover_hero
agenda_navigation
architecture_diagram
process_flow
timeline_gantt
chart_dashboard
comparison_matrix
evidence_board
risk_radar
value_chain
collaboration_map
closing_signal
```

示例输出：

```json
{
  "expression_type": "architecture_diagram",
  "main_focus": "system_layers",
  "secondary_focus": ["key_modules", "data_flow"],
  "avoid": ["card_grid", "long_paragraph", "tiny_icon"]
}
```

作用：

- 决定页面应该由哪种专业表达主导。
- 避免所有内容页都退化为左右布局或卡片网格。
- 为后续 Layout Solver 和 Diagram Renderer 提供方向。

## 3. Composition Director

MiMo 在这一层只负责页面表达策略，不写 HTML。

它输出构图意图：

```json
{
  "composition_intent": "center_large_architecture_with_right_insights",
  "dominant_element": "architecture_diagram",
  "visual_weight": {
    "architecture_diagram": 0.55,
    "key_insight": 0.18,
    "module_notes": 0.17,
    "evidence_badge": 0.10
  },
  "reading_order": [
    "architecture_diagram",
    "key_insight",
    "module_notes",
    "evidence_badge"
  ],
  "spatial_preference": "center_heavy",
  "density": "balanced",
  "mood": "professional_tech"
}
```

MiMo 可以决定：

- 哪个内容是页面主角。
- 哪些内容需要弱化。
- 页面适合什么专业表达方式。
- 页面重心是左重、中重、上重还是分布式。
- 阅读路径如何组织。
- 大致视觉权重如何分配。

MiMo 不允许输出：

- 绝对坐标。
- 整页 HTML。
- 复杂 SVG 源码。
- 大白板容器。
- 任意字号。
- 任意全局背景。

## 4. Layout Solver

系统根据 MiMo 的构图意图计算安全区域。

主体区示例：

```json
{
  "body_frame": { "x": 84, "y": 224, "w": 1752, "h": 764 }
}
```

系统生成多个候选布局：

```json
[
  {
    "layout_id": "center_visual_right_notes",
    "regions": {
      "architecture_diagram": { "x": 120, "y": 260, "w": 1050, "h": 570 },
      "key_insight": { "x": 1210, "y": 270, "w": 520, "h": 130 },
      "module_notes": { "x": 1210, "y": 430, "w": 520, "h": 260 },
      "evidence_badge": { "x": 1210, "y": 720, "w": 520, "h": 120 }
    }
  },
  {
    "layout_id": "top_statement_center_visual",
    "regions": {
      "key_insight": { "x": 120, "y": 240, "w": 1580, "h": 110 },
      "architecture_diagram": { "x": 170, "y": 390, "w": 1360, "h": 460 },
      "module_notes": { "x": 120, "y": 875, "w": 1580, "h": 90 }
    }
  }
]
```

候选布局评分项：

```text
不越界 +20
不重叠 +20
主视觉面积足够 +20
文字容量安全 +15
留白比例合理 +10
阅读路径清楚 +10
和前后页不重复 +5
```

Layout Solver 固定的是“物理规则”，不是固定页面模板。

同样是架构页，可能被排成：

- 中央大架构图 + 右侧洞察。
- 顶部结论 + 中央架构图。
- 横向端-边-云通道。
- 核心节点放射图。
- 分层模块矩阵。

## 5. Diagram Schema Planner

即使系统给架构图分配了 50% 区域，也不能让 MiMo 直接画 SVG。MiMo 应该输出图解 schema。

### 架构图 Schema

```json
{
  "diagram_type": "layered_architecture",
  "title": "端-边-云协同架构",
  "layers": [
    {
      "name": "端侧采集层",
      "modules": [
        { "name": "温湿度传感器", "role": "采集环境数据" },
        { "name": "摄像头", "role": "采集图像数据" },
        { "name": "无人机", "role": "补充巡检数据" }
      ]
    },
    {
      "name": "边缘处理层",
      "modules": [
        { "name": "协议适配", "role": "MQTT / LoRa / HTTP" },
        { "name": "数据清洗", "role": "去噪与格式化" },
        { "name": "异常预警", "role": "本地快速响应" }
      ]
    },
    {
      "name": "云端平台层",
      "modules": [
        { "name": "数据湖", "role": "统一存储" },
        { "name": "AI识别", "role": "病害与长势分析" },
        { "name": "决策看板", "role": "可视化管理" }
      ]
    }
  ],
  "flows": [
    { "from": "端侧采集层", "to": "边缘处理层", "label": "原始数据" },
    { "from": "边缘处理层", "to": "云端平台层", "label": "清洗后数据" }
  ],
  "emphasis": ["AI识别", "异常预警"]
}
```

### 流程图 Schema

```json
{
  "diagram_type": "process_flow",
  "steps": [
    { "name": "数据采集", "output": "环境/图像/设备数据" },
    { "name": "边缘预处理", "output": "清洗后的标准数据" },
    { "name": "AI识别", "output": "病害/长势判断" },
    { "name": "可视化决策", "output": "预警与处置建议" }
  ],
  "feedback_loop": {
    "from": "可视化决策",
    "to": "数据采集",
    "label": "结果反馈优化模型"
  }
}
```

### 证据板 Schema

```json
{
  "diagram_type": "evidence_board",
  "evidence_slots": [
    {
      "type": "system_screenshot",
      "title": "系统界面截图",
      "purpose": "证明平台已完成可视化数据展示",
      "ratio": "16:9",
      "importance": "primary"
    },
    {
      "type": "practice_photo",
      "title": "实操现场照片",
      "purpose": "证明团队完成线下部署调试",
      "ratio": "4:3",
      "importance": "secondary"
    }
  ],
  "supporting_notes": [
    "现场采集真实数据",
    "系统展示实时预警结果"
  ]
}
```

## 6. PPT 专用 SVG Renderer

系统根据 schema 和区域尺寸画 SVG。

Renderer 应该是一组专业图解 renderer：

```text
ArchitectureRenderer
ProcessFlowRenderer
TimelineRenderer
GanttRenderer
ChartRenderer
EvidenceBoardRenderer
RiskRadarRenderer
ComparisonRenderer
ValueChainRenderer
CollaborationMapRenderer
```

每个 renderer 都做 4 件事。

### 6.1 Fit To Region

根据区域宽高和内容复杂度自动适配：

```text
区域宽高
内容数量
最长文字
节点层级
箭头数量
图片位数量
```

决定：

```text
横向 / 纵向
几列 / 几行
字号
节点尺寸
箭头路径
是否折叠
是否移旁注
```

### 6.2 Auto Simplify

内容太多时不能硬塞：

```text
模块超过 5 个 -> 分组
文字超过 14 字 -> 换行或截断
层级超过 4 层 -> 合并辅助层
流程超过 6 步 -> 主链 + 次级说明
证据超过 3 张 -> 主证据 + 辅助证据角标
```

### 6.3 Professional Visual Tokens

高级感来自统一的图解 token：

```json
{
  "stroke_width": 1.4,
  "node_radius": 18,
  "group_radius": 28,
  "shadow": "soft_depth",
  "gradient": "controlled_accent",
  "line_style": "thin_precise",
  "label_style": "technical_caption",
  "emphasis_style": "glow_edge"
}
```

设计原则：

- 线条干净。
- 层级明确。
- 关键节点突出。
- 背景克制。
- 标签像 PPT 标注，不像网页按钮。
- 图表有专业信息密度。
- 光效、渐变、阴影克制使用，不做廉价炫技。

### 6.4 Internal Audit

SVG 内部也要审查：

```text
节点是否重叠
文字是否超出节点
箭头是否穿过文字
字号是否小于阈值
主视觉是否太空
模块是否太拥挤
```

不合格时 renderer 自己重排：

```text
换方向
减少节点
扩大主区域
折叠模块
把细节移到旁注
请求页面 solver 重新分配区域
```

## 7. Safe Page Renderer

最终页面由系统组装：

```text
Shell:
背景、标题、副标题、页脚、页码、全局字体、主题色

Body:
Layout Solver 计算出的区域

Region:
SVG / 文本标注 / 证据位 / 指标 / 图片占位

Final:
安全 HTML 页面
```

输出结构示例：

```html
<main class="slide">
  <header class="shell-title">端-边-云三层架构</header>
  <section class="shell-subtitle">说明系统如何完成从采集到决策的闭环</section>

  <section class="shell-body">
    <div class="ppt-body-root">
      <div class="region region-main-visual">
        <!-- 系统生成的 architecture SVG -->
      </div>

      <div class="region region-key-insight">
        <!-- MiMo 生成的短结论，但系统控制字号和容量 -->
      </div>

      <div class="region region-notes">
        <!-- 系统筛选后的 3 条标注 -->
      </div>
    </div>
  </section>

  <footer>项目名称 / 页码</footer>
</main>
```

MiMo 不能再写：

```text
整个 body 背景
全屏白板
任意绝对定位
任意超大 padding
任意小字
任意 SVG 坐标
```

## 8. 图片和证据位处理

职业院校技能大赛强调“实操+讲解”，所以证据位必须是系统级能力。

系统先判断图片类型：

```text
政策网页截图
设备照片
实操现场照片
系统界面截图
数据样例截图
证书/专利图片
团队协作照片
```

每类图片有尺寸规则：

```text
系统截图：16:9，大图，适合 35%-55% 主体区
实操照片：4:3 或 16:9，适合 30%-50%
证书专利：3:4，适合 20%-32%
政策截图：21:9 或 16:9，适合横向证据板
设备照片：4:3，适合和说明并排
```

没有真实图片时，渲染 PPT 证据位，而不是网页上传框。

证据位必须包含：

```text
证据标题
建议图片类型
推荐比例
证据用途
来源说明
角标
裁切提示
```

示例：

```text
系统界面截图
用途：展示平台实时预警和数据看板
建议比例：16:9
建议来源：平台后台 / 大屏页面
```

## 9. Visual Auditor

生成后必须用 Playwright 截图和 DOM 审查。

检查项：

```text
1. 页面是否越界
2. 元素是否重叠
3. 字号是否过小
4. 主视觉面积是否足够
5. 留白是否过多
6. 页面是否太挤
7. 是否重复标题
8. 是否出现大白板/二次画布
9. 图片占位是否太小/太大
10. 目录是否像目录
11. 封面是否像封面
12. 结束页是否有错误证据位
13. SVG 内部节点是否重叠
14. 箭头是否穿字
15. 图解是否过于简陋
```

审查输出示例：

```json
{
  "pass": false,
  "issues": [
    "主视觉面积不足",
    "架构图节点文字溢出",
    "图片证据位过小",
    "页面右侧文字密度过高"
  ],
  "repair_target": "diagram_schema",
  "repair_action": "reduce_modules_and_switch_to_vertical_layered_layout"
}
```

## 10. Repair Loop

返工不能让 MiMo 重新整页乱画，必须分层 repair。

### 10.1 页面区域问题

例如主视觉太小、留白太多。

处理方式：

```text
回到 Layout Solver
重新分配区域
主视觉从 45% 提到 60%
辅助文字减少
```

### 10.2 SVG 内部问题

例如节点重叠、箭头穿字。

处理方式：

```text
回到 Diagram Renderer
换布局方向
折叠模块
减少标签
```

### 10.3 内容过多

例如文字放不下。

处理方式：

```text
回到 MiMo
要求压缩内容
每个模块最多 8-12 字
只保留 3 个重点
```

### 10.4 表达类型错误

例如本该是流程图却生成了卡片。

处理方式：

```text
回到 Page Expression Planner
重新选择 process_flow
```

### 10.5 仍然装不下

系统建议拆页：

```text
架构总览页
关键模块详解页
```

## 11. 为什么这不是模板化

固定模板是：

```text
架构页 = 左图右文
流程页 = 横向五节点
证据页 = 三卡片
```

新方案是：

```text
架构页可能是：
中心层级架构
左侧主链路 + 右侧证据
顶部结论 + 中央架构
端-边-云横向通道
核心节点放射图
分层模块矩阵

具体用哪种，由内容、权重、区域、前后页节奏共同决定
```

系统只固定：

```text
安全规则
视觉 token
图解语法
审查标准
```

不固定整页长相。

## 12. 开发落地阶段

### P0：建立基础闭环

目标：不再让 MiMo 直接控制整页 HTML。

改动：

```text
1. 新增 Page Expression Planner
2. 新增 Composition Schema
3. 新增 Layout Solver v1
4. 新增 Diagram Schema Planner prompt
5. 新增 ArchitectureRenderer / ProcessFlowRenderer / EvidenceBoardRenderer
6. Safe Page Renderer 改为 region-based
7. Visual Auditor 接入 region/SVG 检查
```

首批覆盖 5 类页：

```text
cover
agenda
architecture_system
practice_evidence
value_matrix
```

### P1：扩展专业图解

新增：

```text
TimelineRenderer
ChartDashboardRenderer
RiskRadarRenderer
ComparisonMatrixRenderer
CollaborationMapRenderer
```

增强：

```text
图解自动折叠
箭头避让
节点分组
图片证据位智能比例
```

### P2：建立高级视觉系统

新增多套视觉 DNA：

```text
浅色科技风
深色路演风
政务证据风
工程实操风
商业增长风
科研展示风
```

同一个 schema 可以渲染成不同风格。

### P3：质量闭环

新增：

```text
截图 contact sheet
逐页评分
失败页 debug 保留
多轮 repair 限时
真实任务回归集
人工审美标注
```

## 13. 最终理想链路

```text
用户问卷
  ↓
MiMo 生成内容大纲
  ↓
MiMo 富化每页内容
  ↓
系统清洗/去重/提炼
  ↓
MiMo 判断每页表达方式
  ↓
MiMo 输出 composition intent
  ↓
系统 layout solver 计算区域
  ↓
MiMo 输出 diagram schema / evidence schema / text brief
  ↓
系统 PPT SVG renderer 生成专业图解
  ↓
系统 safe renderer 组装页面
  ↓
Playwright 截图审查
  ↓
局部 repair / schema repair / layout repair
  ↓
通过后落盘 preview
  ↓
生成 PPTX
```

## 14. 一句话总结

MiMo 不再是 HTML 页面工人，而是内容导演和图解策划。

系统不再是模板容器，而是 PPT 排版与图解编译器。

这条路线的目标是同时解决：

```text
不模板化
不失控
能逐步接近专业 PPT 水平
```
