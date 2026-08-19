# OREP PPT 生成架构 v4.0 — 最终方案

> 版本：v4.0  
> 日期：2026-04-13  
> 定位：职业技能大赛路演 PPT 自动生成系统  
> 目标：从"AI 画师"升级为"AI 导演 + 确定性装配"

---

## 一、当前架构诊断

### 已有的正确基础

| 模块 | 状态 | 说明 |
|------|------|------|
| 组件库 (18 个) | ✅ 成熟 | cover, toc, kpi_metrics, bar_chart_svg, flow_diagram... |
| 布局系统 (10 种) | ✅ 可用 | cover_layout, data_layout, two_column_layout... |
| 锐普 Token v5/v6 | ✅ 专业 | 5 主题、比例 Token、魔法参数、字体源 |
| 组装引擎 V9 | ✅ 框架对 | layout→component 映射、智能路由 |
| 问卷 + 评分规则 | ✅ 完整 | 15 项评分标准、领域适配 |

### 三个卡脖子问题

**问题 1：AI 同时做"写什么"和"怎么摆"（最致命）**

当前 `outline_generator.py` 中，DeepSeek 一次性输出 40-50 页完整 DSL，包括 `layout_type`、`title`、`content`。AI 在做两件事情：

- 决定每页讲什么内容 ✅ AI 擅长
- 决定每页用什么布局、什么视觉结构 ❌ AI 极不稳定

后果：第 5 页和第 25 页可能是同类型内容，但用了完全不同的信息密度和视觉结构。

**问题 2：没有页面类型的语义约束**

18 个组件、10 种布局，但没有中间层告诉 AI "竞品分析页只能用 comparison_table 或 two_column_ps，不能用 full_text_page"。

后果：AI 可以用三种完全不同的方式呈现同一类内容，视觉质量随机。

**问题 3：Token 系统和组件之间是松耦合**

Token 做得很专业，但组件代码中大部分视觉参数仍是硬编码。没有显式绑定机制——改一套 Token 不能保证所有组件同步更新。

---

## 二、v4.0 目标架构

```
问卷数据
  ↓
Schema 解析
  ↓
🧠 AI 大纲生成（仅输出语义序列）        ← AI 的唯一职责：选类型 + 写标题 + 列要点
  ↓
📐 布局规则引擎（节奏控制 + 自动修复）   ← 纯代码，0 个 AI 调用
  ↓
🎯 语义→布局→组件 映射                  ← 确定性查表
  ↓
🧩 组装引擎 + 内容量自适应              ← 组件渲染 + 自动调整
  ↓
🎨 视觉 Token 系统                      ← 统一换肤
  ↓
HTML → PPTX
```

**核心原则：AI 只做分类决策，不做布局决策。**

---

## 三、12 种页面语义类型定义

### 类型枚举

```python
# page_semantics.py

PAGE_SEMANTICS = {
    # ===== 固定结构页（AI 不需要选择，代码自动插入） =====
    "COVER": {
        "description": "封面页：项目名称、团队、学校、赛事名称",
        "allowed_layouts": ["cover_layout"],
        "allowed_components": ["cover"],
        "required": True,  # 必须出现在第 1 页
        "max_count": 1,
    },
    "TOC": {
        "description": "目录页：章节概览",
        "allowed_layouts": ["toc_layout"],
        "allowed_components": ["toc"],
        "required": True,  # 必须出现在第 2 页
        "max_count": 1,
    },
    "SECTION_DIVIDER": {
        "description": "章节分隔页：大标题 + 章节序号",
        "allowed_layouts": ["section_layout"],
        "allowed_components": ["section_divider"],
        "max_count": 8,  # 最多 8 个章节
    },
    "ENDING": {
        "description": "结尾页：感谢/联系方式",
        "allowed_layouts": ["ending_layout"],
        "allowed_components": ["ending"],
        "required": True,  # 必须是最后一页
        "max_count": 1,
    },

    # ===== 内容页（AI 选择的核心战场） =====
    "BACKGROUND_DATA": {
        "description": "背景数据页：市场规模、政策数据、行业趋势（用数字说话）",
        "allowed_layouts": ["data_layout", "content_layout"],
        "allowed_components": ["kpi_metrics", "bar_chart_svg", "pie_chart_svg", "full_text_page"],
        "preferred_component": "kpi_metrics",  # 首选组件
    },
    "PAIN_POINTS": {
        "description": "痛点分析页：核心问题列举，每个痛点配说明",
        "allowed_layouts": ["two_column_layout", "content_layout"],
        "allowed_components": ["three_column_cards", "two_column_ps", "full_text_page"],
        "preferred_component": "three_column_cards",
    },
    "SOLUTION_ARCH": {
        "description": "方案架构页：系统架构图、技术路线、模块关系",
        "allowed_layouts": ["two_column_layout", "content_layout"],
        "allowed_components": ["flow_diagram", "two_column_ps", "full_text_page"],
        "preferred_component": "flow_diagram",
    },
    "SKILL_STEPS": {
        "description": "技能操作页：标准化操作流程、步骤分解",
        "allowed_layouts": ["timeline_layout"],
        "allowed_components": ["timeline_vertical", "flow_diagram"],
        "preferred_component": "timeline_vertical",
        "content_schema": {  # 强制结构化内容格式
            "step_name": "str  — 技能名称",
            "sub_steps": [
                {
                    "action": "str — 标准化动作描述",
                    "key_point": "str — 关键控制点/得分点",
                    "result": "str — 预期结果/判定标准",
                }
            ],
        },
    },
    "DATA_COMPARE": {
        "description": "数据对比页：竞品对比、前后对比、A/B 测试结果",
        "allowed_layouts": ["data_layout"],
        "allowed_components": ["comparison_table", "bar_chart_svg", "kpi_metrics"],
        "preferred_component": "comparison_table",
    },
    "TEAM_INTRO": {
        "description": "团队介绍页：成员角色、分工、能力",
        "allowed_layouts": ["team_layout"],
        "allowed_components": ["team_cards"],
        "max_count": 1,
    },
    "ACHIEVEMENT": {
        "description": "成果展示页：已取得的成果、奖项、数据验证",
        "allowed_layouts": ["data_layout", "two_column_layout"],
        "allowed_components": ["kpi_metrics", "pie_chart_svg", "comparison_table"],
        "preferred_component": "kpi_metrics",
    },
    "TEXT_CONTENT": {
        "description": "纯文字内容页：政策背景、方法论说明、总结陈述（兜底类型）",
        "allowed_layouts": ["content_layout"],
        "allowed_components": ["full_text_page"],
        "preferred_component": "full_text_page",
    },
}
```

### 职业技能大赛的典型语义序列

一个标准的 40 页竞赛 PPT 的语义序列大致如下：

```
页号  语义类型           说明
───────────────────────────────────────────
1     COVER             封面（自动插入）
2     TOC               目录（自动插入）
3     SECTION_DIVIDER   "一、项目背景"（自动插入）
4     BACKGROUND_DATA   社会现状数据
5     BACKGROUND_DATA   政策背景
6     BACKGROUND_DATA   市场规模
7     SECTION_DIVIDER   "二、痛点分析"
8     PAIN_POINTS       四大核心痛点
9     PAIN_POINTS       痛点深挖（细分场景）
10    SECTION_DIVIDER   "三、解决方案"
11    SOLUTION_ARCH     系统架构总览
12    SOLUTION_ARCH     技术路线图
13    SKILL_STEPS       核心技能操作 1
14    SKILL_STEPS       核心技能操作 2
15    SKILL_STEPS       核心技能操作 3
16    SECTION_DIVIDER   "四、功能实现"
17    TEXT_CONTENT       功能模块说明
18    DATA_COMPARE      核心功能对比
19    SOLUTION_ARCH     数据库/接口设计
20    SECTION_DIVIDER   "五、成果展示"
21    ACHIEVEMENT       关键指标达成
22    ACHIEVEMENT       获奖/认证情况
23    DATA_COMPARE      与同类方案对比
24    SECTION_DIVIDER   "六、团队介绍"
25    TEAM_INTRO        团队成员
26    SECTION_DIVIDER   "七、总结展望"
27    TEXT_CONTENT       项目总结
28    BACKGROUND_DATA   未来规划数据
29    ENDING            感谢页（自动插入）
```

> 注意：AI 只输出中间的内容页语义（4-28），封面/目录/分隔/结尾由代码自动插入。

---

## 四、大纲生成 Prompt 重写

### 原 Prompt 问题

当前 `outline_generator.py` 的 Prompt 让 AI 输出完整 DSL，包含 layout_type、content 结构、甚至 CSS 建议。AI 需要做 40-50 次布局决策，每次都有 10+ 种选择——这是不确定性的根源。

### 新 Prompt（AI 仅输出语义序列）

```python
OUTLINE_SYSTEM_PROMPT_V4 = """
你是职业技能大赛路演 PPT 的"内容规划师"。

你的职责：根据问卷数据，规划 40-50 页 PPT 的内容序列。
你的输出：只输出语义类型和内容要点，不要指定布局、组件或视觉样式。

## 可用的页面语义类型（只能从以下 12 种中选择）

| 语义类型 | 适用场景 |
|----------|----------|
| BACKGROUND_DATA | 用数字/数据说明背景（市场规模、政策条数、用户数量） |
| PAIN_POINTS | 列举核心问题/痛点（每个痛点一句话 + 影响） |
| SOLUTION_ARCH | 系统架构、技术路线、模块关系图 |
| SKILL_STEPS | 标准化操作流程（必须按 action/key_point/result 格式） |
| DATA_COMPARE | 竞品对比、前后对比、方案对比 |
| TEAM_INTRO | 团队成员角色与分工 |
| ACHIEVEMENT | 已取得的成果、奖项、数据验证 |
| TEXT_CONTENT | 纯文字说明（政策分析、方法论、总结，兜底类型） |

注意：COVER、TOC、SECTION_DIVIDER、ENDING 由系统自动插入，你不需要规划。

## 输出格式

```json
{
  "pages": [
    {
      "semantic": "BACKGROUND_DATA",
      "title": "页面标题",
      "key_points": ["要点1", "要点2", "要点3"]
    },
    {
      "semantic": "SKILL_STEPS",
      "title": "工业机器人坐标系校准",
      "key_points": ["确定基准点", "手动示教", "自动校准"],
      "steps_detail": [
        {"action": "确定基准点", "key_point": "偏差<0.02mm", "result": "校准成功"},
        {"action": "手动示教", "key_point": "安全距离10cm", "result": "路径录入"},
        {"action": "自动校准", "key_point": "精度验证", "result": "误差<0.01mm"}
      ]
    }
  ]
}
```

## 竞赛 PPT 的叙事节奏（必须遵守）

1. **项目背景**（4-6页）：用数据建立紧迫感
   - BACKGROUND_DATA × 3~4 → 说明"为什么要做这件事"
   
2. **痛点分析**（2-3页）：直击要害
   - PAIN_POINTS × 2~3 → 每个痛点对应一个具体场景
   
3. **解决方案**（5-8页）：核心展示
   - SOLUTION_ARCH × 1~2 → 总体架构
   - SKILL_STEPS × 3~5 → 核心技能操作（这是竞赛的重点！）
   
4. **功能实现**（4-6页）：技术深度
   - TEXT_CONTENT × 1~2 → 功能模块说明
   - DATA_COMPARE × 1~2 → 技术对比
   - SOLUTION_ARCH × 1 → 数据库/接口设计
   
5. **成果展示**（3-5页）：用结果说话
   - ACHIEVEMENT × 2~3 → 关键指标
   - DATA_COMPARE × 1 → 与同类方案对比
   
6. **团队与总结**（3-4页）
   - TEAM_INTRO × 1
   - TEXT_CONTENT × 1~2 → 总结展望

## 硬性规则

- 总页数（不含自动插入页）：35-42 页
- SKILL_STEPS 必须有 steps_detail（技能操作是竞赛核心得分点）
- 同一语义类型连续出现不超过 2 次
- 每个章节至少包含 2 种不同语义类型
- 不要出现连续 3 页以上的 TEXT_CONTENT（会视觉疲劳）
"""

OUTLINE_USER_PROMPT_TEMPLATE = """
项目名称：{project_name}
团队名称：{team_name}
学校：{school_name}
行业领域：{industry}
评分规则：{scoring_rules}

问卷内容：
{questionnaire_responses}

请根据以上信息，规划 PPT 的页面语义序列。
"""
```

---

## 五、布局规则引擎

### 设计原则

- **纯代码，0 个 AI 调用**
- 输入：AI 输出的语义序列
- 输出：修正后的语义序列（含布局和组件选择）
- 不改内容，只改结构

### 规则定义

```python
# layout_rules.py

class LayoutRuleEngine:
    """布局规则引擎 — 控制 PPT 叙事节奏"""

    # ===== 规则 1：连续性检查 =====
    # 同一语义类型不能连续出现超过 N 次
    MAX_CONSECUTIVE_SAME_SEMANTIC = 2

    # ===== 规则 2：章节完整性 =====
    # 每个 SECTION_DIVIDER 之后，到下一个 SECTION_DIVIDER 之前，
    # 至少包含 2 种不同的语义类型
    MIN_UNIQUE_SEMANTICS_PER_SECTION = 2

    # ===== 规则 3：呼吸感控制 =====
    # 每 N 页内容密集型页面后，强制插入一个视觉变化页
    # 视觉变化页 = 信息密度低的页面（有图表、大数字、或分隔页）
    BREATH_PAGE_INTERVAL = 5
    BREATH_PAGE_TYPES = ["BACKGROUND_DATA", "ACHIEVEMENT", "SECTION_DIVIDER"]

    # ===== 规则 4：章节节奏模板 =====
    # 定义标准章节的"推荐节奏"
    SECTION_RHYTHM_TEMPLATES = {
        "项目背景": ["BACKGROUND_DATA", "BACKGROUND_DATA", "BACKGROUND_DATA"],
        "痛点分析": ["PAIN_POINTS", "PAIN_POINTS"],
        "解决方案": ["SOLUTION_ARCH", "SKILL_STEPS", "SKILL_STEPS", "SKILL_STEPS"],
        "功能实现": ["TEXT_CONTENT", "DATA_COMPARE", "SOLUTION_ARCH"],
        "成果展示": ["ACHIEVEMENT", "ACHIEVEMENT", "DATA_COMPARE"],
        "团队总结": ["TEAM_INTRO", "TEXT_CONTENT"],
    }

    # ===== 规则 5：内容量自适应（在组装阶段执行） =====
    CONTENT_LENGTH_THRESHOLDS = {
        "overflow": 2000,   # 字符数超过此值 → 自动切分栏
        "sparse": 200,      # 字符数低于此值 → 简化布局
    }

    def process(self, semantic_pages: list, section_titles: list = None) -> list:
        """
        主入口：接收 AI 输出的语义序列，返回修正后的序列
        
        修正内容：
        1. 插入封面、目录、章节分隔、结尾（自动页）
        2. 检查连续性，插入变化页
        3. 检查章节完整性
        4. 为每页分配 layout_id 和 component_id
        """
        result = []

        # Step 1: 插入固定页
        result.append({"semantic": "COVER", "auto": True})
        result.append({"semantic": "TOC", "auto": True})

        # Step 2: 插入章节分隔 + 内容页
        pages_with_sections = self._insert_section_dividers(
            semantic_pages, section_titles
        )

        # Step 3: 连续性检查 — 同类型不超过 2 次
        pages_with_sections = self._enforce_consecutive_limit(
            pages_with_sections
        )

        # Step 4: 呼吸感检查 — 每 5 页内容密集型后插变化页
        pages_with_sections = self._enforce_breath_rhythm(
            pages_with_sections
        )

        result.extend(pages_with_sections)

        # Step 5: 插入结尾
        result.append({"semantic": "ENDING", "auto": True})

        # Step 6: 为每页分配 layout + component
        result = self._assign_layouts_and_components(result)

        return result

    def _insert_section_dividers(self, pages, section_titles):
        """根据语义变化自动插入章节分隔"""
        # 逻辑：检测语义类型的"大跳变"，如从 BACKGROUND_DATA 跳到 PAIN_POINTS
        # 说明进入了新章节，插入 SECTION_DIVIDER
        result = []
        section_idx = 0
        last_category = None

        CATEGORY_MAP = {
            "BACKGROUND_DATA": "项目背景",
            "PAIN_POINTS": "痛点分析",
            "SOLUTION_ARCH": "解决方案",
            "SKILL_STEPS": "解决方案",
            "DATA_COMPARE": "功能实现",
            "TEXT_CONTENT": None,  # 跟随上一个分类
            "ACHIEVEMENT": "成果展示",
            "TEAM_INTRO": "团队总结",
        }

        for page in pages:
            semantic = page["semantic"]
            category = CATEGORY_MAP.get(semantic)

            if category and category != last_category:
                title = section_titles[section_idx] if section_titles and section_idx < len(section_titles) else f"第{'一二三四五六七八'[section_idx]}章：{category}"
                result.append({
                    "semantic": "SECTION_DIVIDER",
                    "title": title,
                    "auto": True,
                })
                section_idx += 1
                last_category = category

            result.append(page)

        return result

    def _enforce_consecutive_limit(self, pages):
        """连续性检查：同类型不超过 2 次"""
        result = []
        consecutive_count = 0
        last_semantic = None

        for page in pages:
            if page["semantic"] == last_semantic:
                consecutive_count += 1
            else:
                consecutive_count = 1
                last_semantic = page["semantic"]

            if consecutive_count > self.MAX_CONSECUTIVE_SAME_SEMANTIC:
                # 插入一个变化页
                change_page = self._get_breath_page(page)
                result.append(change_page)
                consecutive_count = 1

            result.append(page)

        return result

    def _enforce_breath_rhythm(self, pages):
        """呼吸感控制：每 5 页内容密集型后插变化页"""
        result = []
        content_page_count = 0

        for page in pages:
            semantic = page["semantic"]

            # 非内容页（分隔、封面等）不计入
            if semantic not in ("SECTION_DIVIDER", "COVER", "TOC", "ENDING"):
                content_page_count += 1

            # 达到呼吸间隔
            if content_page_count >= self.BREATH_PAGE_INTERVAL:
                if semantic not in self.BREATH_PAGE_TYPES:
                    breath_page = self._get_breath_page(page)
                    result.append(breath_page)
                    content_page_count = 0

            result.append(page)

        return result

    def _get_breath_page(self, context_page):
        """生成一个"呼吸页"——低信息密度的视觉变化页"""
        # 根据上下文选择：如果有数据，用 BACKGROUND_DATA；否则用 TEXT_CONTENT
        return {
            "semantic": "BACKGROUND_DATA",
            "title": "关键数据概览",
            "key_points": ["[系统自动生成：在此插入核心数据摘要]"],
            "auto": True,
            "is_breath_page": True,
        }

    def _assign_layouts_and_components(self, pages):
        """为每页分配 layout_id 和 component_id"""
        from page_semantics import PAGE_SEMANTICS

        for page in pages:
            sem = page["semantic"]
            spec = PAGE_SEMANTICS.get(sem, {})

            # 使用首选组件，否则选第一个允许的
            page["layout_id"] = spec.get("allowed_layouts", ["content_layout"])[0]
            page["component_id"] = spec.get("preferred_component") or spec.get("allowed_components", ["full_text_page"])[0]

        return pages
```

---

## 六、内容量自适应（组装阶段）

在 `assembly_engine.py` 的组件选择逻辑中，加一个内容量检查：

```python
# 在 assembly_engine.py 的 _select_component 方法中追加

def _auto_adjust_by_content_length(self, component_id: str, data: dict) -> str:
    """根据内容量自动调整组件选择"""
    content_str = json.dumps(data, ensure_ascii=False)
    length = len(content_str)

    # 内容过溢：full_text_page → two_column_ps
    if length > 2000 and component_id == "full_text_page":
        return "two_column_ps"

    # 内容过少：three_column_cards → full_text_page（别硬撑三张卡）
    if length < 200 and component_id == "three_column_cards":
        return "full_text_page"

    # 内容过少：comparison_table → kpi_metrics
    if length < 300 and component_id == "comparison_table":
        return "kpi_metrics"

    return component_id
```

---

## 七、组件 Token 显式绑定

### 每个组件声明所需 Token

```python
# components/base.py — 基类增加 token 依赖声明

class BaseComponent:
    """所有组件的基类"""

    # 子类必须声明需要哪些 Token
    REQUIRED_TOKENS: list = []

    def __init__(self, theme: ThemeContext):
        self.theme = theme
        self._validate_tokens()

    def _validate_tokens(self):
        """校验当前主题是否提供了所有必需的 Token"""
        missing = []
        for token_path in self.REQUIRED_TOKENS:
            value = self.theme.get_token(token_path)
            if value is None:
                missing.append(token_path)

        if missing:
            logger.warning(
                f"组件 {self.__class__.__name__} 缺少 Token: {missing}，"
                f"将使用硬编码默认值"
            )
```

### 各组件声明示例

```python
# components/cover.py
class CoverComponent(BaseComponent):
    REQUIRED_TOKENS = [
        "colors.bg_primary",
        "colors.bg_secondary",
        "colors.primary_gradient",
        "colors.accent",
        "typography.title_font",
        "typography.title_size",
        "typography.subtitle_font",
        "effects.glass_blur",
        "effects.glow_color",
        "spacing.page_padding",
    ]

# components/kpi_metrics.py
class KpiMetricsComponent(BaseComponent):
    REQUIRED_TOKENS = [
        "colors.bg_primary",
        "colors.primary",
        "colors.accent",
        "colors.text_primary",
        "colors.text_secondary",
        "typography.number_font",
        "typography.label_font",
        "effects.card_bg",
        "effects.card_border_radius",
        "spacing.card_gap",
    ]

# components/timeline_vertical.py (技能操作页核心组件)
class TimelineVerticalComponent(BaseComponent):
    REQUIRED_TOKENS = [
        "colors.bg_primary",
        "colors.primary",
        "colors.accent",
        "colors.text_primary",
        "colors.text_secondary",
        "typography.step_number_font",
        "typography.body_font",
        "effects.timeline_line_color",
        "effects.step_dot_size",
        "effects.card_shadow",
        "spacing.step_gap",
    ]
```

### Token Manager 加载校验

```python
# ruipu_token.py — 加载时自动校验

class TokenManager:
    def validate_for_components(self, component_classes: list):
        """校验当前 Token 是否满足所有组件需求"""
        all_missing = {}
        for cls in component_classes:
            missing = []
            for token_path in cls.REQUIRED_TOKENS:
                if self.get(token_path) is None:
                    missing.append(token_path)
            if missing:
                all_missing[cls.__name__] = missing

        if all_missing:
            logger.error(f"Token 校验失败，以下组件缺少 Token：")
            for comp, tokens in all_missing.items():
                logger.error(f"  {comp}: {tokens}")
            return False
        return True
```

---

## 八、SKILL_STEPS 内容结构规范

技能操作页是竞赛 PPT 的核心得分点，必须强制结构化：

```python
# 技能操作页的 AI 输出格式（在大纲 Prompt 中约束）

{
    "semantic": "SKILL_STEPS",
    "title": "工业机器人坐标系校准",
    "key_points": ["确定基准点", "手动示教", "自动校准", "精度验证"],
    "steps_detail": [
        {
            "step_number": 1,
            "action": "确定基准点",
            "key_point": "使用激光跟踪仪，偏差 < 0.02mm",
            "result": "基准坐标系建立完成",
            "tool": "激光跟踪仪 Leica AT960"
        },
        {
            "step_number": 2,
            "action": "手动示教",
            "key_point": "安全距离 ≥ 10cm，速度限制 50mm/s",
            "result": "6 个路径点录入完成",
            "tool": "示教器 FANUC iPendant"
        },
        {
            "step_number": 3,
            "action": "自动校准",
            "key_point": "运行校准程序，实时监控偏差",
            "result": "全轴误差 < 0.01mm",
            "tool": "校准软件 DynaCal"
        },
        {
            "step_number": 4,
            "action": "精度验证",
            "key_point": "标准球测试，重复 5 次取均值",
            "result": "重复定位精度 ±0.005mm",
            "tool": "标准球 + 三坐标测量机"
        }
    ]
}
```

### timeline_vertical 组件渲染逻辑

```python
def render(self, data: dict) -> str:
    """渲染技能操作页"""
    steps = data.get("steps_detail", [])

    # 如果没有 steps_detail，退化为 key_points 简单列表
    if not steps:
        steps = [{"step_number": i+1, "action": p, "key_point": "", "result": ""}
                 for i, p in enumerate(data.get("key_points", []))]

    html_parts = []
    for step in steps:
        html_parts.append(f"""
        <div class="step-item">
            <div class="step-number">{step['step_number']}</div>
            <div class="step-content">
                <div class="step-action">{step['action']}</div>
                <div class="step-keypoint">⚡ {step['key_point']}</div>
                <div class="step-result">✓ {step['result']}</div>
                {f'<div class="step-tool">🔧 {step["tool"]}</div>' if step.get('tool') else ''}
            </div>
        </div>
        """)

    return f"""
    <div class="skill-steps-page">
        <h2 class="page-title">{data.get('title', '')}</h2>
        <div class="steps-timeline">
            {''.join(html_parts)}
        </div>
    </div>
    """
```

---

## 九、实施路径

### Phase 1：语义类型 + Prompt 重写（1-2 天）

**做什么：**
1. 创建 `page_semantics.py`，定义 12 种语义类型
2. 重写 `outline_generator.py` 的 Prompt，AI 只输出语义序列
3. 修改 `_generate_outline_async` 解析新格式

**改动文件：**
- `app/services/ppt/page_semantics.py` — 新建
- `app/services/ppt/outline_generator.py` — 重写 Prompt + 解析逻辑

**验收标准：**
- AI 输出的 JSON 中只有 `semantic`、`title`、`key_points`、`steps_detail`
- 没有 `layout_type`、`component_id`、CSS 相关内容
- 输出的语义类型全部在 12 种之内

### Phase 2：布局规则引擎（1 天）

**做什么：**
1. 创建 `layout_rules.py`，实现 `LayoutRuleEngine` 类
2. 在 `ppt_service.py` 的生成流程中插入规则引擎
3. 实现连续性检查、呼吸感控制、章节分隔插入

**改动文件：**
- `app/services/ppt/layout_rules.py` — 新建
- `app/services/ppt/ppt_service.py` — 在 outline 生成后、HTML 生成前插入规则引擎

**验收标准：**
- 自动生成封面、目录、章节分隔、结尾
- 没有连续 3 页同类型
- 每 5 页内容密集型后有呼吸页
- 章节之间有明确分隔

### Phase 2.5：内容量自适应（0.5 小时）

**做什么：**
1. 在 `assembly_engine.py` 的 `_select_component` 中加内容量检查

**改动文件：**
- `app/services/ppt/assembly_engine.py` — 追加 `_auto_adjust_by_content_length` 方法

**验收标准：**
- 内容超过 2000 字符的 full_text_page 自动转 two_column_ps
- 内容不足 200 字符的 three_column_cards 自动转 full_text_page

### Phase 3：Token 显式绑定（0.5 天）

**做什么：**
1. 在 `components/base.py` 加 `REQUIRED_TOKENS` 声明和校验
2. 给 5 个核心组件（cover, kpi_metrics, timeline_vertical, three_column_cards, comparison_table）声明 Token 依赖
3. Token Manager 加载时校验

**改动文件：**
- `app/services/ppt/components/base.py` — 加基类校验逻辑
- `app/services/ppt/components/cover.py` — 声明 Token 依赖
- `app/services/ppt/components/kpi_metrics.py` — 声明 Token 依赖
- `app/services/ppt/components/timeline_vertical.py` — 声明 Token 依赖
- `app/services/ppt/components/three_column_cards.py` — 声明 Token 依赖
- `app/services/ppt/components/comparison_table.py` — 声明 Token 依赖
- `app/services/ppt/ruipu_token.py` — 加 `validate_for_components` 方法

**验收标准：**
- 换一套 Token 主题，组件渲染时自动校验完整性
- 缺少 Token 时有明确 warning，不静默 fallback

### Phase 4（可选）：变体系统（2-3 天）

**暂不做。等 Phase 1-3 跑通、39 页能稳定输出后再考虑。**

---

## 十、文件变更总览

| 文件 | 操作 | Phase |
|------|------|-------|
| `app/services/ppt/page_semantics.py` | 新建 | 1 |
| `app/services/ppt/outline_generator.py` | 重写 Prompt + 解析 | 1 |
| `app/services/ppt/layout_rules.py` | 新建 | 2 |
| `app/services/ppt/ppt_service.py` | 插入规则引擎 | 2 |
| `app/services/ppt/assembly_engine.py` | 加内容量自适应 | 2.5 |
| `app/services/ppt/components/base.py` | 加 Token 校验基类 | 3 |
| `app/services/ppt/components/cover.py` | 声明 Token 依赖 | 3 |
| `app/services/ppt/components/kpi_metrics.py` | 声明 Token 依赖 | 3 |
| `app/services/ppt/components/timeline_vertical.py` | 声明 Token 依赖 | 3 |
| `app/services/ppt/components/three_column_cards.py` | 声明 Token 依赖 | 3 |
| `app/services/ppt/components/comparison_table.py` | 声明 Token 依赖 | 3 |
| `app/services/ppt/ruipu_token.py` | 加组件校验方法 | 3 |

---

## 十一、预期效果

| 维度 | 当前 (v3) | v4.0 目标 |
|------|-----------|-----------|
| 页面一致性 | 随机（AI 发挥不稳定） | 确定性（代码保证同类页同风格） |
| 叙事节奏 | 无控制，可能出现连续 5 页文字 | 规则引擎强制节奏 + 呼吸感 |
| 技能操作页质量 | AI 自由发挥格式 | 强制 action/key_point/result 结构 |
| 换肤能力 | Token 存在但松耦合 | 组件显式声明依赖，换肤即生效 |
| AI 调用成本 | 1 次输出 40 页完整 DSL | 1 次输出 35 个语义标签（token 消耗降低 60-70%） |
| 可维护性 | 加新页面类型需改 Prompt | 加新语义类型只需在 page_semantics.py 加一条 |
