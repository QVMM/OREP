# V5 Fixed Shell + AI Composition + SVG + Safe Renderer Action Plan

## 结论

当前项目最优路线，不是继续扩“整页模板库”，也不是让 AI 直接自由生成整页 HTML/CSS。

最优方案是 4 层架构：

1. `Shell Layer`
2. `Composition Layer`
3. `Visual Layer`
4. `Renderer Layer`

目标是：

- 不再让每一页都长得像同一种模板
- 不再让 AI 自由写整页导致失控
- 保留全局统一感
- 把多样性集中到主体区
- 用 SVG 取代卡通 icon / 网页卡片感

一句话原则：

**固定壳层 + AI 编排主体区 + AI 生成 SVG + 系统安全落版**

这条路既不是“整页模板”，也不是“整页放飞”。

## 基于当前项目的判断

### 已经证实不适合继续走的路

当前项目已经验证过，这几条路会持续制造问题：

- “先生成内容，再塞进整页模板壳”
- family 注册很多，但真实 renderer 不完整
- solver / renderer / reviewer / fallback 不是同一语言
- 靠 repair / sanitizer / delivery gate 补坏页
- 用整页模板追求统一，导致 100 个用户长一个样

这些问题在旧 V4 上已经形成结构性负担。

### 当前项目里值得保留的部分

虽然旧路线要停，但当前项目不是要推倒重来。以下能力应保留并迁入新路线：

- `V5 clean pipeline` 的叙事层思想
- `narrative role -> family / variant / skeleton` 的中间决策能力
- `preview_v5_*` 独立预览入口
- V5 自己的 renderer / reviewer 基础骨架
- 定向任务验证和截图回归方法

也就是说，我们不是回到从零开始，而是把当前 V5 骨架向正确方向收敛。

## 四层架构

### 1. Shell Layer

壳层只负责全局统一，不负责主体信息组织。

固定内容：

- 背景系统
- 顶部视觉基线
- 大标题区
- 小标题区
- 页脚区
- 字体体系
- 全局色板
- 安全边距
- 页面基础节奏

壳层不能做的事：

- 不决定主体区具体布局
- 不决定内容块数量
- 不决定图文关系
- 不决定每页中间视觉长什么样
- 不允许偷偷长回“主体大模板骨架”

这条必须写死：

- `Shell Layer` 只能定义版心、标题、副标题、页脚、背景、色板、字体、边距
- 不允许在 shell 中预置“中间主体区已经排好版的卡片墙 / 双栏主体 / 时间线主体 / 指标主体”
- 一旦 shell 开始携带主体区骨架，就等于换名回到整页模板，必须视为设计违规

壳层的意义是：

- 统一视觉气质
- 控制成品稳定性
- 防止页面“散”

但绝不能退回“整页模板”。

### 2. Composition Layer

这是新路线的核心。

AI 不再直接生成整页 HTML，而是生成“主体区编排方案”。

它要回答的问题是：

- 主体区分几块
- 哪块是主视觉
- 哪块是说明
- 哪块是对照
- 哪块是数据
- 哪块是证据
- 哪块放 SVG
- 哪块占主要视觉重心
- 主体区的阅读路径是什么

输出形式不应该是自由 HTML，而应该是受控 DSL，例如：

```json
{
  "composition_id": "left_timeline_right_retro",
  "body_frame": {
    "x": 84,
    "y": 220,
    "w": 1752,
    "h": 744
  },
  "zones": [
    {
      "zone_id": "main_svg",
      "role": "timeline_visual",
      "x": 0,
      "y": 0,
      "w": 0.56,
      "h": 1.0
    },
    {
      "zone_id": "side_notes",
      "role": "retrospective_notes",
      "x": 0.60,
      "y": 0.0,
      "w": 0.40,
      "h": 1.0
    }
  ],
  "dominant_zone": "main_svg",
  "scan_pattern": "left_to_right",
  "density_mode": "balanced"
}
```

关键约束：

- AI 只能在主体区内编排
- 不能覆盖标题区和页脚区
- 不能自由创造超出 DSL 的布局类型
- 不能绕过安全边界直接写 HTML

### 3. Visual Layer

主体视觉优先使用 SVG。

来源有两种：

1. AI 直接生成 SVG
2. AI 生成 `SVG schema`，系统再参数化生成 SVG

结合当前项目阶段，建议优先顺序是：

- 短期：AI 生成 `SVG schema`，系统生成 SVG
- 中期：AI 直接生成部分受约束 SVG

更适合先上的 SVG 类型：

- 时间线
- 协作链路
- 架构分层
- 闭环流程
- 价值/证据关系图
- 对照型图示

不建议继续强化的方向：

- 卡通 icon
- 网页式信息卡
- 按钮感组件
- hover / dashboard 味

### 4. Renderer Layer

Renderer 不再是“把内容塞进整页模板”，而是：

- 读取 shell
- 读取 composition DSL
- 读取 SVG/schema
- 读取 text blocks
- 在安全边界内完成落版

它的职责是：

- 对齐主体区坐标系
- 控制元素尺寸
- 控制文本换行和上限
- 控制 SVG 占比
- 防止溢出和遮挡
- 输出最终 HTML

必须明确：

- AI 不直接控制最终 DOM
- Renderer 才是唯一能把主体区落成 HTML 的层
- 任何超界、溢出、重叠都必须由 renderer 拦住

## 新的数据链

新的主链应该是：

`outline/content`
-> `narrative graph`
-> `composition intent`
-> `visual intent`
-> `render contract`
-> `final html`

比当前 V5 再细一层：

- 原来 V5 更偏 `narrative -> layout skeleton`
- 新路线要把中间“主体区编排”单独抽出来

这一步非常关键，因为它决定我们以后不是“切 family”，而是“设计主体区”。

## 结合当前代码的落地方式

### 当前 V5 可作为新路线的基础层

现有模块：

- [clean_pipeline.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/clean_pipeline.py)
- [narrative_graph.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/narrative_graph.py)
- [layout_engine.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/layout_engine.py)
- [render_contracts.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/render_contracts.py)
- [render_engine.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/render_engine.py)
- [reviewer.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/reviewer.py)

这些模块不需要推翻，但需要重构职责：

- `layout_engine.py`
  - 未来不再直接给出最终 skeleton
  - 改成优先给出 `composition family`
- 新增 `composition_engine.py`
  - 输出主体区 DSL
- `render_contracts.py`
  - 改成基于 `composition + visual` 生成 contract
- `render_engine.py`
  - 改成“壳层 + 主体区布局 + SVG + 文本”组合渲染
- `reviewer.py`
  - 增加“成品视觉分”，不只看结构对齐

### 当前 V4 不再承担设计演进

V4 后续仅保留：

- 老任务兼容读取
- 应急 fallback
- 对照验证

不再：

- 承担新设计能力
- 承担新 family 演进
- 承担新视觉语言试验

## 最优行动顺序

### Phase 1：冻结错误方向

立刻停止继续扩以下能力：

- 扩整页模板
- 扩 V4 family renderer
- 扩基于旧 fallback 的修复逻辑
- 扩 anime.js 动效主线

保留 V5 作为唯一新设计主线。

### Phase 2：新增 Composition Layer

新增模块建议：

- `app/services/ppt/v5/shell_system.py`
- `app/services/ppt/v5/composition_engine.py`
- `app/services/ppt/v5/svg_schema_builder.py`
- `app/services/ppt/v5/safe_body_renderer.py`

第一步先不追求所有页系，只跑 5 类关键页：

- `cover_keynote`
- `agenda_navigation`
- `journey_timeline`
- `collaboration_matrix`
- `value_matrix`

### Phase 3：从固定 skeleton 升级到主体区编排

重点不是“多几个 skeleton”，而是：

- 同一页系允许多个主体区构图
- 同一 narrative role 不再只能长一个样
- 视觉多样性从 composition 层来，不从整页模板来

比如：

- `journey_timeline`
  - `left_timeline_right_retro`
  - `top_timeline_bottom_findings`
- `collaboration_matrix`
  - `center_chain_side_roles`
  - `left_roles_right_handoff`
- `value_matrix`
  - `scenario_board_metric_side`
  - `top_value_statement_bottom_evidence`

### Phase 4：SVG 成为主体视觉默认解

每个 composition 都明确：

- 是否需要 SVG
- SVG 放哪个 zone
- SVG 占比范围
- 文本与 SVG 的相对主次

SVG 先从 schema 生成开始，不直接全面开放自由 SVG。

### Phase 5：Reviewer 升级成双评分

以后必须分两套分：

1. 工程结构分
2. 成品视觉分

成品视觉分至少看：

- 主体区内容占比
- 空白是否失衡
- 文案重复率
- 图示是否拥挤
- 主次是否明确
- 是否像 PPT 成品而不是线框页

不能再出现“工程 80 分，但肉眼只有 30 分”的误导。

## 关键边界

### 绝不能做的事

- 不能回到整页模板库
- 不能让 AI 直接写整页 HTML/CSS
- 不能让 AI 越过 renderer 控制 DOM
- 不能把 V5 设计演进又做回 V4 repair/fallback
- 不能让 `Shell Layer` 侵入主体区骨架定义

### 允许的自由度

- AI 可以自由决定主体区构图类型
- AI 可以自由决定主体区内容块关系
- AI 可以决定 SVG 类型和图示意图

但这些都必须在：

- 固定壳层
- 固定主体区边界
- 固定 renderer 规则

之内进行。

## 当前阶段的最优开发任务

如果按当前项目现状排优先级，最优顺序是：

1. 新增 `Composition Layer` DSL
2. 把 V5 renderer 从“直接按 skeleton 出页”改成“壳层 + 主体区编排”
3. 给 5 类关键页接 `SVG schema -> safe render`
4. 重构 V5 reviewer，引入成品视觉分
5. 用 `preview_v5_*` 做持续截图回归

## 首批 5 类页切流与回退标准

首批切入 V5 的页系固定为：

- `cover_keynote`
- `agenda_navigation`
- `journey_timeline`
- `collaboration_matrix`
- `value_matrix`

切流规则：

- 新生成的这 5 类页，默认优先走 V5 主路径
- V4 仅保留老任务对照读取、应急回看和回归比较用途
- 这 5 类页不再继续向 V4 投入新的设计演进

允许短期回退到 V4 的条件：

- V5 渲染失败，无法产出合法 HTML
- V5 reviewer 的工程结构 gate 未通过
- V5 reviewer 的成品视觉分低于上线阈值
- 截图回归出现主体区严重空洞、溢出、遮挡、结构错位

回退规则：

- 回退必须记录页系、任务、失败原因、截图证据
- 回退只作为临时保底，不得因为回退存在而停止修复 V5
- 同一页系连续达到稳定阈值后，应逐步关闭 V4 主路径保底

建议的稳定阈值：

- 首批 5 类页在定向任务和真实任务回归中，连续两轮通过工程结构 gate
- 成品视觉分连续两轮达到目标线
- 截图回归无严重空白页、无溢出页、无主体区错位页

达到以上阈值后：

- 这 5 类页默认只走 V5 主路径
- V4 对应页系降级为兼容读取和紧急人工干预工具，不再作为默认输出链路

## 可行性结论

这条方案可行，而且是当前项目最优方向。

原因：

- 它避免了整页模板同质化
- 它避免了 AI 直接自由写整页导致失控
- 它能承接当前 V5 已有基础
- 它能逐步切走旧 V4，而不是长期双链打架

它不是最省事的方案，但它是最像真正产品路线的方案。
