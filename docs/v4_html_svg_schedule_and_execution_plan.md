# V4 HTML SVG 化开发排期与执行方案

## 范围调整

本轮方案基于 [v4_html_executable_remediation_checklist.md](/Users/liuyixing/项目/OREP/docs/v4_html_executable_remediation_checklist.md) 执行，但做两点收敛：

1. 先不做爆炸图、3D 拟态建模、产品结构自由建模。
2. 只保留 `SVG` 方向，且将 `anime.js` 限定为 `SVG 技术图解增强器`，不做全页炫技动画库。

目标不是“让页面更动”，而是把页面从 `HTML 卡片感` 推向 `PPT 技术图解感`。

---

## 总体目标

本轮开发分两条主线并行推进：

1. `主线 A：P0/P1 基线治理`
   - 修内部字段泄漏
   - 修 family/debug 信息上屏
   - 修占位词、溢出、repair 跑偏
   - 补 family renderer，减少 `_render_generic`

2. `主线 B：SVG 图解体系`
   - 用 SVG 取代一部分 icon-card / div-card
   - 为技术架构、流程桥、时间线、协作图建立统一 SVG renderer
   - 用 `anime.js` 做轻量线稿绘制、路径高亮、节点依次出现

---

## 设计原则

### 1. anime.js 的定位

- 不是通用动画库
- 不是网页 hover 增强器
- 不是自由生成 JS 的容器
- 只用于 `SVG 图解的 reveal / draw / highlight`

### 2. SVG 的定位

- 不是插图装饰
- 是页面核心信息结构
- 用来承载：
  - 架构图
  - 流程桥
  - 时间线
  - 协作关系
  - 证据标注

### 3. 输出形态

- `preview`：允许 SVG 轻动效
- `capture/export`：直接渲染终态，禁止截图截到半动画

---

## 里程碑排期

## 第一阶段：止血与基线收敛

### 时间

- `第 1 周`

### 目标

- 完成 checklist 的 `P0`
- 把 `preview_157` 这类显性问题先压下去
- 给后续 SVG 改造打稳定底座

### 任务

1. `P0-1` 渲染输入白名单化
2. `P0-2` 去掉可见 family/debug 信息
3. `P0-3` 禁止占位词上屏
4. `P0-5` repair 继承同一 deck shell
5. `P0-6` 加 preview 前自动验收骨架
6. `P0-4` 先修最明显的溢出/SVG 黑块

### 交付物

- 正式页不再显示：
  - `transition_role`
  - `visual_intent`
  - `*_anchor / *_proof / *_execution`
  - `family_id`
- preview 写盘前有最小页级质检
- repair 不再切换另一套壳

---

## 第二阶段：页面去模板感

### 时间

- `第 2 周`

### 目标

- 把已注册 family 从 `_render_generic` 里拉出来
- 让 family 真正有自己的构图
- 为后续 SVG family 接入预留接口

### 任务

1. `P1-1` 补齐 family renderer
2. `P1-2` 从顺序切片改为 slot mapping
3. `P1-3` 抽 formal shell
4. `P1-5` 布局内容预算

### 优先补齐的 family

- `architecture_system`
- `practice_evidence`
- `value_matrix`
- `closing_board`
- `protocol_board`
- `collaboration_matrix`
- `journey_timeline`
- `bridge_story`
- `innovation_compare`

### 交付物

- 正式交付页基本不再走 `_render_generic`
- 同 family 至少有 2 个真实变体
- 页面结构开始从“卡片壳”转向“职责驱动构图”

---

## 第三阶段：SVG 图解体系 Batch 1

### 时间

- `第 3 周`

### 目标

- 让最适合的 family 先从 div/card 语言切到 SVG 语言
- anime.js 只在 SVG 图解里做专业、克制的辅助动效

### 任务

1. 建 `SVG primitive kit`
2. 建 `SVG renderer protocol`
3. 建 `motion mode` 三态
4. 先接 3 个 family

### 首批 family

1. `architecture_system`
   - 分层结构
   - 数据流向
   - 模块边界
2. `mapping_bridge`
   - old -> new
   - before / after
   - 路径桥接
3. `journey_timeline`
   - rail
   - milestone
   - evidence checkpoint

### 交付物

- `SVG primitive kit v1`
- `SVG renderer v1`
- `anime.js motion runtime v1`
- 3 个 family 的 SVG 化版本

---

## 第四阶段：SVG 图解体系 Batch 2

### 时间

- `第 4 周`

### 目标

- 扩更多适合 SVG 的 family
- 建立 deck 内图解风格的一致性

### 任务

1. 扩展 `collaboration_matrix`
2. 扩展 `value_matrix`
3. 扩展 `evidence_board`
4. 接入 `preview / capture / export` 动态终态控制

### 交付物

- 6 个 family 具备 SVG 渲染能力
- preview 动效和导出终态可分离

---

## 第五阶段：风格多样化与反同质化

### 时间

- `第 5 周 - 第 6 周`

### 目标

- 完成 checklist 的 `P2`
- 把 SVG 图解纳入 deck DNA 与 layout solver

### 任务

1. Deck DNA
2. family/variant 打分求解
3. deck consistency 反同质化 gate
4. style pack 扩展
5. 回归样本库

### 交付物

- 不同项目的 deck 会在 family 分布、SVG 图解语言、节奏上产生明显差异

---

## 技术拆分

## A. 基线治理层

### 代码触点

- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`
- `ai-scoring/app/services/ppt/v4/formal_page_sequence.py`
- `ai-scoring/app/services/ppt/presentation_sanitizer.py`
- `ai-scoring/app/services/ppt/ppt_service.py`
- `ai-scoring/app/services/ppt/html_renderer.py`

### 责任

- 保证内容干净
- 保证壳统一
- 保证 preview 交付前过质检

---

## B. SVG 图解层

### 建议新增模块

- `ai-scoring/app/services/ppt/v4/svg_primitives.py`
- `ai-scoring/app/services/ppt/v4/svg_renderer.py`
- `ai-scoring/app/services/ppt/v4/svg_layouts.py`
- `ai-scoring/app/services/ppt/v4/motion_runtime.py`

### 责任

- 输出稳定 SVG
- 用参数化方式构建技术图解
- 不允许 AI 自由拼任意 JS/SVG

---

## C. Motion 层

### 建议新增模块

- `ai-scoring/app/services/ppt/v4/motion_contracts.py`
- `ai-scoring/app/services/ppt/v4/motion_runtime.py`

### 模式

- `off`
- `preview`
- `capture`

### 规则

- `preview`：播放轻动效
- `capture`：seek 到终态
- `export`：等同 `capture`

---

## SVG 方案定义

## 什么内容该用 SVG

- 架构关系
- 数据流
- 时间线
- 协作链路
- 证据指引
- 价值闭环

## 什么内容不该用 SVG

- 普通文字摘要页
- 大段说明页
- 已经拥挤的内容页
- 只是为了“炫”而加的无信息图形

## anime.js 在 SVG 里只做这些

- 轮廓线绘制
- 路径高亮
- 节点依次出现
- 标签轻 reveal
- 重点流向渐进强调

## 明确禁止

- bounce
- 无限循环
- 大范围 hover
- 粒子特效
- 漂浮装饰
- 卡通 icon 运动

---

## 风险与约束

### 风险 1

如果先上 anime.js，不先修 formal renderer，最终只会把模板感动起来。

### 风险 2

如果 SVG renderer 不做参数化约束，AI 自由生成的 SVG 会再次失控。

### 风险 3

如果 preview 和 export 不分离，PPT 导出会截到半动画状态。

### 风险 4

如果 SVG 只是“替代 icon”，但没有承担结构信息，产品收益有限。

---

## 验收指标

## 第一阶段验收

- `preview_157` 类问题显著下降
- 内部 token 泄漏清零
- family/debug 信息不再可见

## 第二阶段验收

- 正式交付页 0 次或极低比例使用 `_render_generic`
- family renderer 覆盖率明显提升

## 第三阶段验收

- 首批 3 个 family 能稳定产出 SVG 图解页
- preview 可播轻动效，export 稳定为终态

## 第四阶段验收

- SVG family 扩展到 6 个
- deck 中图解语言开始统一

## 第五阶段验收

- 100 个不同项目不会都长成同一种 HTML/PPT

---

## 执行顺序

1. 先做 `P0`
2. 再做 `P1`
3. 再做 `SVG Batch 1`
4. 再做 `SVG Batch 2`
5. 最后做 `P2`

---

## 这一轮立刻开工的范围

本轮先直接进入：

1. `P0-1` 渲染输入白名单化
2. `P0-2` 去掉 formal 页可见 family/debug 信息
3. `P0-3` 补强终稿净化规则

这三项是后续所有 SVG 改造的基线前提。SVG 不该建立在脏内容和 generic 壳上。
