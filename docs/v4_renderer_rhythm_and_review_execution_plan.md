# V4 Renderer Rhythm And Review Execution Plan

## 目标

把 V4 从“solver 会选 family/variant”推进到“用户肉眼能看到像 PPT 的版式差异”，并且让系统自己能审查这种差异是否真实存在。

## 文档状态

这份文档包含两部分：

- 上半部分：已完成轮次的实现依据与历史记录，主要覆盖 `architecture_system / mapping_bridge / value_matrix / closing_board`
- 下半部分：当前待执行轮次，也就是 `cover_keynote / agenda_navigation + 结构/语义反同质化 + 真实任务集回归`

当前真正待执行、待审核的轮次以下半部分“下一波：Opening Rhythm Extension”为准。

## 已完成轮次范围

上一轮不扩 family，重点是把已经开始的节奏系统真正闭环。

当前状态：

- `layout_solver.py` 已经会输出 `focus_strategy / density_mode / scan_pattern / selection_trace`
- `formal_render_engine.py` 第一批 family 已开始消费这些信号
- 但 page/deck reviewer 和正式 acceptance 还没有完整接入这套节奏规则

所以本轮只继续推进 3 件事：

1. 完成 Batch 1 的 renderer 信号消费收口与回归
2. 落地 Batch 2 / Batch 3 / Batch 4，让 reviewer 与 acceptance 真正检查节奏差异
3. 用系统级回归证明“不是 trace 变复杂了，而是最终 HTML 真的更像 PPT 了”

本阶段只做三件事，而且顺序固定：

1. 让 formal renderer 真正消费 solver 输出的 `focus_strategy / density_mode / scan_pattern / layout_variant`
2. 把“呼吸感、重点、扫描路径”的差异渲染出来，而不是只停留在 metadata
3. 升级 page/deck reviewer，让系统能检查这些视觉节奏，而不是只看 family 覆盖率

---

## 为什么这三步必须按这个顺序做

当前系统的真实状态是：

- solver 已经能输出更聪明的选择和 `selection_trace`
- `layout_region_plan` 已经写进 `page_meta`
- 但 formal renderer 还没有系统消费这些信号
- reviewer 也还不会检查这些新信号是否真的变成了可见页面差异

如果先做 reviewer，不做 renderer，审查不到真实视觉变化。

如果只做 renderer，不做 reviewer，系统以后会慢慢退回“能跑就行”的状态。

所以正确顺序只能是：

- `renderer consumption`
- `visual rhythm rendering`
- `reviewer enforcement`

---

## 第一阶段：Renderer Consumption

### 目标

把 solver 输出的抽象信号，映射成 formal renderer 能用的真实排版决策。

### 当前输入

- `page_meta["layout_variant"]`
- `page_meta["layout_region_plan"]["focus_strategy"]`
- `page_meta["layout_region_plan"]["density_mode"]`
- `page_meta["layout_region_plan"]["scan_pattern"]`
- `page_meta["layout_region_plan"]["body"]`
- `page_meta["layout_region_plan"]["title"]`

### 先接入的页系

优先改 4 个最能体现“PPT 感、呼吸感、重点差异”的 family。

这是第一波高杠杆 family，不是全部范围：

1. `architecture_system`
2. `mapping_bridge`
3. `value_matrix`
4. `closing_board`

紧随其后的下一波必须补：

5. `cover_keynote`
6. `agenda_navigation`

### 每个信号的落地语义

#### `focus_strategy`

- `diagram_first`
  - 主图更大，副卡更少，图与文主次更明确
  - 适用于 `architecture_system / mapping_bridge`
- `metric_first`
  - 指标条/指标岛优先进入首屏视觉中心
  - 适用于 `value_matrix / closing_board(metric_recap)`
- `evidence_first`
  - 证据区面积扩大，说明文案退后
  - 适用于后续 `evidence_board / practice_evidence`
- `hero_first`
  - 核心结论优先，支撑模块收束为侧栏或下栏
  - 适用于 `closing_board / definition_canvas / cover`

#### `density_mode`

- `spacious`
  - 更大留白
  - 卡片数更少
  - 间距增大
  - 正文裁切更激进
- `balanced`
  - 正常双区或三段布局
- `dense`
  - 更高效的栅格
  - 更紧凑的侧栏
  - 更严格的摘要长度控制

#### `scan_pattern`

- `single_anchor`
  - 一主视觉锚点，辅以 2-4 个解释卡
- `split_compare`
  - 左右或前后对照结构
- `staged_progression`
  - 阶段推进式阅读路径
- `grid_scan`
  - 规则矩阵型扫描路径

### 代码触点

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v4/formal_render_engine.py`

### 实施方式

#### `architecture_system`

- `layer_stack_center` + `diagram_first`
  - 放大 SVG 主图，支持卡压缩成 3 张以内侧栏
- `layer_stack_with_sidebar` + `dense`
  - 主图缩窄，侧栏展开更多支撑说明
- `protocol_matrix_*`
  - 协议/接口/安全信号强时，把下部说明改成协议带或矩阵辅助区

#### `mapping_bridge`

- `before_after_*` + `split_compare`
  - 强化左右对照，不再只是横向流程
- `flow_map_*` + `staged_progression`
  - 强化桥接路径与阶段推进
- `spacious`
  - 减少说明卡数量，放大阶段节点
- `dense`
  - 四阶段节点保留，但右侧细节卡数量增加

#### `value_matrix`

- `score_board_*` + `metric_first`
  - 首屏先给指标和关键收益
- `scenario_map_*` + `grid_scan`
  - 先给对象/场景，再给价值卡
- `spacious`
  - 控制 3-4 张主卡，不堆满价值项
- `dense`
  - 增加 proof/metric 辅助块，但保持不滚动

#### `closing_board`

- `statement_anchor_*` + `hero_first`
  - 一句总结做主视觉，回扣卡弱化
- `metric_recap_*` + `metric_first`
  - 数值回顾先行，结论句做二级重心
- `spacious`
  - 更大的 hero 区和更少的 recap 卡
- `dense`
  - recap strip 更紧凑，支持 3-4 条回顾

---

## 第二阶段：Visual Rhythm Rendering

### 目标

确保这些差异不仅存在于 trace，而是肉眼可见。

### 需要达成的可见变化

- 同一页系的不同 variant，骨架不能只差一个类名
- 不同 `focus_strategy`，主重心必须明显不同
- 不同 `density_mode`，留白、卡片数量、卡片宽高、摘要长度必须显著不同
- 不同 `scan_pattern`，阅读顺序必须不同

### 具体实现要求

#### 版式差异必须至少落在这 4 个层面中的 2 个以上

- 主图尺寸
- 区块顺序
- 卡片数量
- 边栏/底栏位置
- 标题与副标题宽度
- 摘要长度与裁切策略
- 指标区是否前置

#### 不能接受的伪差异

- 只改 class 名
- 只改边距 4-8px
- 只改颜色
- 只换一条细分割线

### 代码触点

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v4/formal_render_engine.py`

---

## 第三阶段：Review Upgrade

### 目标

让系统能自动检查“视觉节奏有没有真正落地”。

### Page Reviewer 增强

文件：

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v4/visual_review_v4.py`

新增检查：

- `selection_trace` 是否存在且字段完整
- `focus_strategy` 与最终 family/variant 是否一致
- `density_mode` 是否落到了 renderer 可见结构
- `scan_pattern` 是否匹配对应页系结构
- 变体是否只是 metadata 差异，没有真实结构差异

### Formal Acceptance 增强

文件：

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v4/page_acceptance.py`

新增检查：

- 正式页是否消费了 `layout_region_plan`
- sibling variant 是否只改 metadata 没改结构
- 不同 `focus_strategy` 是否在正式 HTML 中产生可见结构差异
- `density_mode` 是否只停留在 trace，而没有转成区块数量/间距/摘要长度差异
- `scan_pattern` 是否在正式页中形成对应的 DOM 结构顺序

目的：

- 让新节奏规则进入正式交付门禁
- 防止 shadow reviewer 看懂了，但 formal delivery 仍然放过“模板味页面”

### Deck Reviewer 增强

文件：

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v4/deck_consistency_service.py`

新增检查：

- 相邻页 `focus_strategy` 是否过于单一
- 同一 deck 的 `density_mode` 是否全部一样
- family 不同但骨架仍高度同构
- 开场、中段、收尾是否有节奏分层
- 同系列连续页是否存在“该切不切”的版式重复

### Reviewer 输出的新增建议

- `rebalance_focus_strategy`
- `spread_density_modes`
- `force_variant_diversity`
- `reduce_structural_homogeneity`
- `strengthen_opening_mid_closing_rhythm`

### Reviewer 的证据模型

这一阶段的 reviewer 不能只检查 metadata 一致性。

必须以最终 HTML / DOM / 结构指纹为主，以 `selection_trace` 为辅。

至少要基于以下证据中的 2 类以上做判断：

- 区块数量与顺序
- 主区/侧区/底区占位比例
- 指标区是否前置
- 主图与说明区面积比例
- 卡片数量与摘要长度
- 结构指纹或 DOM pattern

`selection_trace` 只能作为“预期意图”，不能作为“结果已落地”的证据。

---

## 验收标准

### 功能验收

1. `architecture_system`
   - `layer_stack_center` 和 `layer_stack_with_sidebar` 必须有显著结构差异
   - `protocol_matrix_*` 必须与 `layer_stack_*` 有显著结构差异

2. `mapping_bridge`
   - `before_after_*` 必须明显是对照页
   - `flow_map_*` 必须明显是阶段推进页

3. `value_matrix`
   - `score_board_*` 必须突出指标
   - `scenario_map_*` 必须突出对象/场景扩展

4. `closing_board`
   - `statement_anchor_*` 必须是一句总结主导
   - `metric_recap_*` 必须是指标回顾主导

### 体验验收

1. 同一 deck 中，不允许连续 3 页维持相同 `focus_strategy`
2. 同一 deck 中，不允许同一 family 连续 3 页
3. 同一 family 的 sibling variants 不能只是 metadata 不同
4. 不同项目在相同页数下，family/variant 序列不能高度一致

### 技术验收

1. renderer 使用 `layout_region_plan`
2. `page_acceptance.py` 使用正式页的 rhythm/variant 验收规则
3. reviewer 使用最终 HTML/DOM 证据，并辅以 `selection_trace`
3. regression tests 覆盖：
   - family semantic split
   - variant rhythm split
   - focus/density/scan rendering split
   - formal acceptance rhythm gate
   - deck-level rhythm review

---

## 执行顺序

### Batch 1

- `formal_render_engine.py`
  - 先接 `architecture_system / mapping_bridge / value_matrix / closing_board`
  - 当前状态：已起步，继续收口结构差异与 regression

### Batch 2

- `visual_review_v4.py`
  - 升级 page-level 节奏与 variant 审查
  - 重点：必须基于最终 HTML / DOM 结构证据，不允许只看 `selection_trace`

### Batch 3

- `page_acceptance.py`
  - 把新 rhythm/variant gate 接入正式交付门禁
  - 重点：registered family 若未产生可见节奏差异，正式页直接不放行

### Batch 4

- `deck_consistency_service.py`
  - 升级 deck-level 节奏与同构风险审查
  - 重点：检查相邻页 focus/density 单一化、结构指纹过度重复、opening-middle-closing 节奏塌缩

### Batch 5

- tests
  - `test_v4_structure_pipeline.py`
  - 新增 renderer/reviewer rhythm regression

---

## 结论

这不是补样式，而是把：

- `solver`
- `renderer`
- `reviewer`

三层重新闭环。

只有这样，V4 才会真正从“会生成 HTML”走向“会生成像 PPT 的、按内容智能布局的 HTML”。

---

## 当前待执行轮次：Opening Rhythm Extension

在上一轮完成 `architecture_system / mapping_bridge / value_matrix / closing_board` 之后，下一波只推进：

1. `cover_keynote`
2. `agenda_navigation`
3. 反同质化 reviewer 从“粗规则”升级到“结构 + 语义”判断
4. 真实任务集回归，检查开场锚点与章节呼吸感是否稳定提升

### 为什么先做这两类页

- `cover_keynote` 决定整套 deck 的第一印象和项目气质
- `agenda_navigation` 决定章节切换时是否像 PPT，而不是像网页目录
- 这两页如果还停留在单骨架，即使中段内容页做得更聪明，整套 deck 依然会显得模板味重

### 本轮目标

- 开场页必须出现明确的主锚点差异，而不是统一的居中大标题壳
- 目录页必须根据章节数量、章节语义和叙事节奏切换不同阅读路径
- deck reviewer 不再只按 family/variant 粗看重复，而是开始判断“结构指纹重复 + 语义上也高度重复”才算危险同质化

### Cover 方案

当前 [formal_render_engine.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v4/formal_render_engine.py) 的 `cover_keynote` 仍是单一中心型封面，尚未消费 registry 里的：

- `cover_keynote.hero_split`
- `cover_keynote.hero_stack`

#### 本轮改法

- `hero_split_left / hero_split_center`
  - 适合长标题、较强技术感、需要主副信息分栏的项目
  - 主视觉锚点前置，标题不再统一居中
- `hero_stack_bottom / hero_stack_right`
  - 适合关键词较多、亮点较多、需要“标题 + 关键词带 + 结论锚点”结构的项目
  - 更强调项目标签、关键词密度和情绪收束

#### Cover 的 rhythm 信号落地

- `focus_strategy=hero_first`
  - hero 区必须绝对主导
- `density_mode=spacious`
  - 减少 chips 数量，扩大标题留白
- `density_mode=dense`
  - 保留项目标签，但严格控制 subtitle 长度和 chip 行数
- `scan_pattern=single_anchor`
  - 单锚点封面
- `scan_pattern=grid_scan`
  - 用于更偏标签化、竞赛型封面

#### Cover 的可见差异要求

- 标题对齐方式必须变化
- hero 区占比必须变化
- keyword strip / chip row 的位置必须变化
- subtitle 最大宽度与裁切策略必须变化

### Agenda 方案

当前 `agenda_navigation` 仍是统一四卡网格，没有真正消费：

- `agenda_navigation.chapter_cards`
- `agenda_navigation.route_board`

#### 本轮改法

- `chapter_cards_grid`
  - 适合标准章节目录
  - 突出章节标题和章节主次
- `chapter_cards_timeline`
  - 适合分阶段答辩、路演节奏更强的 deck
- `route_board_horizontal`
  - 适合路线型、流程型议程
- `route_board_vertical`
  - 适合章节较长、解释较多的目录页

#### Agenda 的 rhythm 信号落地

- `focus_strategy=hero_first`
  - 先强调本次章节主线，再展开目录卡
- `focus_strategy=diagram_first`
  - 先强调路线板，再给章节辅助卡
- `density_mode=spacious`
  - 3-4 个主章节，间距更大
- `density_mode=dense`
  - 5-6 个章节时切换更紧凑路径板或更高效网格
- `scan_pattern=grid_scan`
  - 目录卡扫描
- `scan_pattern=staged_progression`
  - 路线板/时间线阅读路径

#### Agenda 的可见差异要求

- 网格目录和路线目录必须是两种明显不同骨架
- 章节数变化必须触发不同布局策略
- 当前章节/重点章节必须有明确强调，不允许所有目录卡一个重量

### 反同质化规则升级

上一轮已经能检查：

- `focus_strategy` 是否连续过长
- `density_mode` 是否过于单一
- `structure_fingerprint` 是否高度重复

这一轮继续升级成“结构 + 语义”的组合判断。

#### 新增判断原则

- 只有“结构指纹重复”不够，必须叠加语义相似度高，才判高风险同质化
- 连续章节页如果语义上属于同一大章节展开，可以容忍更高的结构相似度
- 开场页、目录页、收尾页的同质化权重更高，因为它们对整套 deck 的气质影响更大

#### 新增证据

- `semantic_signature`
  - 根据 `page_series_type / slide_role / page_goal / core_argument / content_points` 归一化生成
- `opening_rhythm_signature`
  - 只对封面 + 目录页做结构和语义联合判断
- `chapter_transition_signature`
  - 用于判断 agenda 到正文的切换是否有节奏断点

#### `semantic_signature` 生成规则

- 输入字段固定为：
  - `page_series_type`
  - `slide_role`
  - `page_goal`
  - `core_argument`
  - `content_points`
- 归一化方式：
  - 去停用词和空洞词
  - 统一数字与量纲表达
  - 合并高频同义词
    - 例如：`方案/解决方案/平台方案`
    - `目录/议程/章节导航`
    - `推广/复制/扩展`
- 输出形式：
  - `semantic_role_tokens`
  - `semantic_intent_tokens`
  - `semantic_density_tokens`
  - `semantic_signature_hash`

#### 结构 + 语义联合判断规则

- `structure_fingerprint` 高重复，但 `semantic_signature_hash` 差异明显
  - 默认放过，只记轻度提醒
- `structure_fingerprint` 高重复，且 `semantic_role_tokens + semantic_intent_tokens` 高度重合
  - 判为高风险同质化
- 结构不同，但 `semantic_signature` 高度相似
  - 只记“内容展开重复”风险，不直接判模板化
- 连续章节页如果：
  - `page_series_type` 相同
  - `slide_role` 属于同一章节展开
  - 且页码连续
  - 则允许更高的结构相似度，不直接打回

#### Opening 页的加权规则

- `cover_keynote`
  - 结构重复权重最高
- `agenda_navigation`
  - 结构重复和语义重复同权
- `closing_board`
  - 次高权重
- 中段内容页
  - 更强调“结构 + 语义”同时重复才触发硬风险

### 真实任务集回归

这一轮不只跑单测，还要跑真实任务集回归。

#### 回归目标

- 检查 `cover_keynote / agenda_navigation` 是否真正提升了首屏质感
- 检查不同任务下的开场 family/variant 是否仍然高度一致
- 检查目录页是否仍然全部退化为“四卡均匀网格”

#### 回归维度

- 不同项目类型
  - 科研答辩
  - 商业路演
  - 政务/产业方案
- 不同页数区间
  - 10-15 页
  - 20-30 页
  - 35-40 页
- 不同章节密度
  - 3 段目录
  - 4-5 段目录
  - 6 段以上目录

#### 通过标准

- `cover_keynote`
  - 不同真实任务样本里，不允许 80% 以上都落到同一 `layout_skeleton`
  - 不允许标题对齐方式全部一致
  - 不允许 chip/keyword 区位置全部一致
- `agenda_navigation`
  - 不允许 80% 以上都退化为均匀四卡网格
  - 当章节数 >= 5 时，至少要有一部分样本切换到 `route_board` 或更高密度路径型骨架
  - 当前章节强调必须在最终 HTML 中有明确结构/样式证据
- `opening rhythm`
  - `cover -> agenda -> 正文第一页` 三页必须形成至少两种不同骨架
  - 不允许这三页都保持同一 `focus_strategy`
- `review gate`
  - 真实任务集中，如果 opening rhythm 失败样本超过阈值，则阻塞本轮合并
  - 默认阈值：失败样本占比 > 20% 即判未通过

#### 回归结果记录

- 每个任务记录：
  - `cover skeleton`
  - `cover focus/density/scan`
  - `agenda skeleton`
  - `agenda focus/density/scan`
  - `opening_rhythm_signature`
  - 是否触发 `semantic_homogeneity_warning`
- 输出聚合结论：
  - `pass`
  - `warning`
  - `block`

### 执行顺序

#### Batch 6

- `formal_render_engine.py`
  - 接入 `cover_keynote / agenda_navigation` 的 family + variant + rhythm 信号消费

#### Batch 7

- `rhythm_audit.py`
  - 补 `cover / agenda` skeleton 和 `semantic_signature`

#### Batch 8

- `visual_review_v4.py`
  - 增加 opening rhythm 审查

#### Batch 9

- `page_acceptance.py`
  - 增加 `cover / agenda` 的正式 gate

#### Batch 10

- `deck_consistency_service.py`
  - 用“结构 + 语义”替换当前更粗的 opening/deck 同质化判断

#### Batch 11

- tests + 真实任务集回归

### 本轮审核问题

给盯审 agent 的审核问题更新为：

1. `cover_keynote / agenda_navigation` 的差异化目标是否足够具体，能避免继续停留在单骨架？
2. 反同质化从“结构指纹”升级到“结构 + 语义”的判断，是否方向正确且不会过度机械？
3. 真实任务集回归的维度和通过标准，是否足够判断“开场节奏”和“章节呼吸感”有没有提升？
4. 这轮是否真正贴近用户要求的“PPT 式 HTML、开场有锚点、章节有呼吸感、不同项目不会都长一个样”？

---

## 当前待执行轮次：Opening Follow-up

基于真实任务 `157` 的第一次 opening regression 结果，当前还剩 3 个明确问题：

1. `agenda_navigation` 还不够积极地切到 `diagram_first / staged_progression`
2. opening 第三页缺少 skeleton 证据，导致 `cover -> agenda -> 正文第一页` 只有前两页能被稳定识别
3. 真实任务回归目前只有 `157`，还不能证明改善具有普适性

### 当前观察结论

来自真实任务 `157` 的 opening snapshot：

- `cover_keynote -> hero_split`
- `agenda_navigation -> chapter_cards_timeline`
- opening 第三页为 `evidence_board`
- `unique_skeleton_count = 2`
- `unique_focus_count = 1`

这说明：

- 开场骨架已经开始拉开
- 但 `focus_strategy` 还没有真正拉开
- opening 第三页仍然没有进入节奏证据体系

### 本轮目标

1. 让 agenda 在“章节流程明显 / 章节数较多 / 路演感较强”的场景里，更主动切到：
   - `focus_strategy = diagram_first`
   - `scan_pattern = staged_progression`
   - `family = agenda_navigation.route_board`
2. 给 opening 第三页补 skeleton 证据，优先覆盖：
   - `evidence_board`
   - 若真实任务样本显示 opening 第三页常落到其他 family，再按样本扩
3. 选择第二批真实任务样本，验证 opening 改善不是只发生在 `157`

### Agenda 跟进方案

#### 问题

当前真实任务 `157` 中，agenda 已切到 `chapter_cards_timeline`，但仍保持：

- `focus_strategy = hero_first`
- `scan_pattern = single_anchor`

这代表 solver 和 renderer 还没有把“议程页本质是路由页、阶段页”的信号放大到足够程度。

#### 改法

- 在 `layout_solver.py` 中强化 `agenda_navigation` 的 family/variant/focus/scan 分流：
  - 当 `content_points >= 4`
  - 或命中 `阶段 / 流程 / 路线 / 路演结构 / 汇报安排 / 章节推进`
  - 则优先提高：
    - `focus_strategy = diagram_first`
    - `scan_pattern = staged_progression`
    - `family = agenda_navigation.route_board`
  - `页码为 2` 只作为弱 bonus / tie-breaker
    - 不能单独触发 `route_board`
    - 只能在语义和章节密度已经接近阈值时，帮助 agenda 往更强的路径型表达倾斜
- 在 `formal_render_engine.py` 中，若 agenda 已命中上述信号：
  - route board 主板面积继续放大
  - 主线箭头/路径板成为一眼主锚点
  - 卡片从“平铺说明”转成“路径节点”

#### 验收标准

- 真实任务中章节数 `>= 4` 的 agenda，不允许全部保持 `hero_first + single_anchor`
- 命中“流程/阶段/路线”语义的 agenda，至少一部分要落到 `route_board`

### Opening 第三页方案

#### 问题

当前 opening regression 只稳定识别前两页，第三页若是 `evidence_board`，还没有 skeleton 标记，导致：

- opening signature 不完整
- deck reviewer 无法判断“目录之后有没有真正进入正文断点”

#### 改法

- 优先给 `evidence_board` 补：
  - `data-layout-skeleton`
  - `data-emphasis-zone`
  - 对应的 `rhythm_audit` skeleton requirements
- 若第二批真实任务显示 opening 第三页高频落到：
  - `definition_canvas`
  - `architecture_system`
  - `content_support`
  - 则再按频次补第二层

#### `evidence_board` skeleton 初版

- `caption_grid`
  - 左证据 / 中逻辑 / 右价值 三段证据骨架
- 若后续出现明显两列或马赛克证据墙，再分化 sibling skeleton

#### 验收标准

- opening 第三页若属于已注册 formal family，不允许继续没有 skeleton 证据
- `cover -> agenda -> 正文第一页` 三页必须都能进入 opening rhythm snapshot

### 第二批真实任务回归方案

#### 样本选择

优先从当前本地已存在的 preview 任务里选第二批：

1. `157`
   - 作为已建立基线的对照样本
2. `156`
   - 接近同阶段近期任务
3. `155`
   - 用于看相邻任务是否仍高度收敛
4. `140`
   - 页数更长、已有多种 render 目录，适合看 opening 稳定性
5. `153`
   - 作为另一组普通 preview 样本

如果其中某个任务缺少可用 outline 或任务数据，则按优先级替补：

- `154`
- `139`
- `138`

#### 回归输出

每个任务输出：

- `cover skeleton`
- `agenda skeleton`
- opening 第三页 skeleton
- `cover/agenda/third` 的 `focus_strategy`
- `cover/agenda/third` 的 `scan_pattern`
- `unique_skeleton_count`
- `unique_focus_count`
- `status`

#### 通过标准

- 第二批样本中，不允许只有 `157` 从 `warning` 改善，其他任务仍全部退回同一开场模式
- 至少 60% 样本的 agenda 应出现：
  - `diagram_first`
  - 或 `staged_progression`
  - 或 `route_board`
- 至少 80% 样本的 opening 第三页应具备 skeleton 证据
- 若第二批样本中 `cover + agenda` 仍大面积收敛到同一组合：
  - `hero_split + chapter_cards_timeline`
  - 且 `focus_strategy` 一致
  - 则本轮判定未完成

### 执行顺序

#### Batch 12

- `layout_solver.py`
  - 强化 agenda 的 `diagram_first / staged_progression / route_board` 触发条件

#### Batch 13

- `formal_render_engine.py`
  - 强化 agenda route board 的主锚点表达
  - 给 `evidence_board` 补 skeleton 标记

#### Batch 14

- `rhythm_audit.py`
  - 增加 `evidence_board` skeleton requirements
  - opening snapshot 记录第三页 skeleton

#### Batch 15

- `tests`
  - 增加 agenda 更积极切 flow/path 的回归
  - 增加 third-page skeleton 回归

#### Batch 16

- 第二批真实任务回归
  - 先跑 `157 / 156 / 155 / 140 / 153`
  - 输出聚合结果

### 本轮审核问题

给盯审 agent 的审核问题更新为：

1. agenda 更积极切到 `diagram_first / staged_progression / route_board` 的策略，是否足够具体且不会过度激进？
2. opening 第三页优先给 `evidence_board` 补 skeleton 证据，这个优先级是否合理？
3. 第二批真实任务样本选择和通过标准，是否足够判断“不是只有 157 有改善”？
4. 这轮执行完后，是否会更接近“开场节奏稳定提升，而不是只修一个案例”？

---

## 当前待执行轮次：Front-Segment By Narrative Roles

在 `Opening Follow-up` 之后，系统已经证明：

- `opening` 三页可以不再是单一模板节奏
- `cover -> agenda -> evidence/content` 可以形成更明确的重心切换

但这还不等于“整份 PPT 已经像 PPT”。当前真正的风险不是“第几页不好”，而是：

- `opening cluster` 已经拉开
- 进入正文前半段后，又重新收敛到几种固定骨架
- 用户会感觉“开头像 PPT，前半段正文还是模板复制”

所以这一轮不再按固定页码推进，而是改成按 `narrative roles` 和 `segment responsibilities` 推进。

### 本轮目标

1. 扩 `solver`
   - 按叙事簇和职责簇分流，而不是按固定页码分流
   - 让“定义 / 方案 / 价值 / 证据 / 收束”这些职责在不同项目、不同页数下都能主动切到更合适的 family / variant / focus / density / scan
2. 扩 `renderer`
   - 让职责差异在最终 HTML 中真正可见
   - 不允许只是 metadata 变了、用户肉眼看起来还是差不多
3. 扩 `reviewer / regression`
   - 把当前只看 `opening` 的节奏回归，升级成检查“前半段叙事簇”
   - 确认不是 `opening` 好了，进入正文前半段又模板化

### 第一部分：扩 Solver

#### 问题

当前 `layout_solver.py` 已经能把 `cover / agenda / evidence` 拉开，但它接下来需要判断的，不应该是“第几页”，而应该是：

- 这页属于哪个叙事簇
- 这页在该叙事簇里承担什么职责
- 这页与前后页是延续关系、过渡关系，还是职责切换关系

如果还用“第 4 到第 6 页”这种思路去写生产逻辑，就会天然不适配不同项目、不同页数、不同顺序的 deck。

#### 目标叙事簇

优先覆盖 `opening` 之后最常见的三个前半段叙事簇：

这些叙事簇有一个前提必须写清楚：

- 它们是 `可缺省`、`可跳过`、`可合并` 的
- 不是所有项目都必须完整经过 `opening -> definition -> solution -> proof_value`
- 系统要做的是：在当前项目真实存在的叙事簇之间，识别职责差异并拉开版式
- 不是把所有 deck 都硬套进同一条隐性流程模板

1. `definition cluster`
   - 常见页系：
     - `definition_canvas`
     - `content_support`
     - `evidence_board`
   - 职责：
     - 定义问题
     - 交代背景
     - 建立认知边界

2. `solution cluster`
   - 常见页系：
     - `mapping_bridge`
     - `architecture_system`
     - `bridge_story`
   - 职责：
     - 给方案路径
     - 解释系统结构
     - 建立桥接逻辑

3. `proof_value cluster`
   - 常见页系：
     - `value_matrix`
     - `practice_evidence`
     - `innovation_compare`
   - 职责：
     - 给验证
     - 给量化结果
     - 给创新对照和落地价值

#### 具体改法

- 在 `layout_solver.py` 中增加“叙事簇识别”：
  - 不看绝对页码
  - 主要看：
    - `slide_role`
    - `page_series_type`
    - `section / chapter` 语义
    - `core_argument / page_goal / content_points` 的职责语义
    - 与前后页的职责过渡
- 增加“职责型语义偏置”：
  - `definition/problem framing`
    - 优先 `single_anchor / hero_first / structured_explanation`
  - `solution/system explanation`
    - 优先 `diagram_first / staged_progression / layered_system`
  - `proof/value/validation`
    - 优先 `metric_first / evidence_first / grid_scan / split_compare`
- 增加“叙事段重复惩罚”：
  - 在同一前半段叙事簇内，如果职责已经切换，但结构重心还连续重复，则降分
  - 例如：
    - 已从 `definition` 切到 `solution`
    - 但仍连续保留同一 `focus_strategy / scan_pattern / skeleton family`
    - 则需要更积极地拉开结构

#### 验收标准

- 若两个相邻页面职责明显不同，不允许仍落在同一 `focus_strategy + scan_pattern` 组合
- 不能只靠 family 名不同来伪装多样性，必须连 `focus / scan / density` 也能拉开
- 同项目页数不同，只要叙事职责相近，仍应得到类似的高质量布局判断

### 第二部分：扩 Renderer

#### 问题

就算 solver 选对了叙事簇和职责簇，如果 renderer 不真正把差异画出来，用户看到的仍然可能是：

- 都是同一种双栏
- 都是同一种卡片组
- 都是同一种留白和信息密度

这会让“职责切换”在视觉上完全不成立。

#### 目标

把前半段常见 family 的“职责差异”真正变成可见版式差异，而不是让不同页系都共享一套模板骨架。

#### 优先消费的 family

1. `definition_canvas`
2. `content_support`
3. `mapping_bridge`
4. `architecture_system`
5. `value_matrix`
6. `practice_evidence`

#### 具体改法

- `definition_canvas`
  - 强化“认知边界页”的克制感
  - `hero_first` 时主定义块更集中，支撑点更少
  - `dense` 时改成更紧凑的双栏解释，而不是继续堆大卡片
- `content_support`
  - 区分“摘要支撑页”和“证据支撑页”
  - `focus` 变体要明显比 `grid` 变体更有主次，不只是列数不同
- `mapping_bridge / architecture_system`
  - 强化“进入方案正文”的结构感
  - 让它们真正成为桥接页、系统页，而不是又回到说明卡片页
- `value_matrix / practice_evidence`
  - 强化“验证 / 量化 / 证据收束”感
  - `metric_first` 时指标区前置
  - `evidence_first` 时证据区主导，不允许和定义页长得像

#### 强制原则

- 任意两个不同职责页，至少在以下 4 个层面中的 2 个以上不同：
  - 主区块顺序
  - 主视觉面积
  - 卡片数量
  - 信息密度
  - 摘要长度
  - 边栏/底栏位置

#### 验收标准

- 前半段正文不能继续只是“同一种模板换文案”
- 同一页系 sibling variant 必须出现骨架级差异，而不是只差 class 名

### 第三部分：扩 Reviewer / Regression

#### 问题

当前 regression 已经能看 `opening`，但还不能回答更关键的问题：

- 进入正文前半段后，是否又收敛回模板化？
- 虽然 family 变了，但 `focus / scan / density` 是否没变？
- 用户肉眼看到的前半段是否真的像一套有节奏的 PPT？

#### 目标

把回归从 `opening rhythm` 扩成 `front-segment rhythm`。

#### 具体改法

- 在 `rhythm_audit.py` 中增加前半段叙事簇需要的 skeleton / structure evidence 抽取
- 在 `deck_consistency_service.py` 中加入“front-segment rhythm”专门检查：
  - 前半段叙事簇内 `focus_strategy` 的唯一值数量
  - 前半段叙事簇内 `scan_pattern` 的唯一值数量
  - 结构职责组的切换次数
  - 是否出现“opening 拉开，但进入正文后重新收敛”的情况
- 在当前 `opening_rhythm_regression.py` 基础上扩一个新报告：
  - `build_front_segment_rhythm_snapshot`
  - `build_front_segment_rhythm_batch_report`

#### Front-Segment 回归输出

每个任务至少输出：

- `opening cluster`
- `definition cluster`
- `solution cluster`
- `proof_value cluster`

每个 cluster 记录：

- 实际命中的页面
- `page_series_type`
- `layout_skeleton`
- `focus_strategy`
- `density_mode`
- `scan_pattern`
- `semantic_signature`

聚合输出：

- `unique_skeleton_count`
- `unique_focus_count`
- `unique_density_count`
- `unique_scan_count`
- `role_transition_count`
- `front_segment_status`

#### 通过标准

- 前半段有效样本中，不允许多数任务仍只有 `1` 种 `focus_strategy`
- 前半段有效样本中，不允许多数任务仍只有 `1` 种 `density_mode`
- 若同时覆盖“定义 / 方案 / 价值”三类职责，不允许结构节奏仍只有单一路径
- 若真实任务中 `opening` 已拉开，但 `definition -> solution -> proof_value` 又全部退回到单一支撑卡模式，则本轮判失败
- 若结构与重心已切换，但密度始终完全不变，导致前半段仍缺少“呼吸感”，则本轮不能判通过

### 建议执行顺序

#### Batch 17

- `layout_solver.py`
  - 扩叙事簇识别
  - 引入职责型语义偏置和叙事段重复惩罚

#### Batch 18

- `formal_render_engine.py`
  - 优先补 `definition_canvas / content_support / practice_evidence`
  - 把职责差异做成真实结构差异

#### Batch 19

- `rhythm_audit.py`
  - 补叙事簇需要的 skeleton 识别和结构证据
- `deck_consistency_service.py`
  - 增加 front-segment rhythm 专项审查

#### Batch 20

- `tests`
  - 增加 solver 叙事簇分流测试
  - 增加 renderer 骨架差异测试
  - 增加 front-segment regression 聚合测试

#### Batch 21

- 真实任务 batch regression
  - 优先继续用 `157 / 156 / 155`
  - 再补 2 到 3 个不同项目任务，避免只在同一批智慧农业样本上成立

### 本轮审核问题

给 `Euler` 的审核问题更新为：

1. 用 `opening / definition / solution / proof_value` 做叙事簇分流，是否比按页码分流更合理？
2. `solver` 增加职责型语义偏置和叙事段重复惩罚，是否足够克制，不会演变成机械反模板？
3. `renderer` 优先补 `definition_canvas / content_support / practice_evidence`，是否命中前半段最关键的模板味来源？
4. 把回归从 `opening` 扩成 `front-segment`，并把 `density_mode` 作为聚合 gate 之一，是否足够判断“不同项目、不同篇幅下，前半段整组页面不像模板复制且有呼吸感”？

---

## 当前待执行轮次：Narrative Families Extension

在 `Front-Segment By Narrative Roles` 第一轮落地后，当前系统已经具备：

- `narrative_segment / narrative_role` 的基础识别
- `definition / content_support / practice_evidence` 的第一批 signal consumption
- `front-segment rhythm` 的基础回归与 gate

但还存在一个明显缺口：

- `bridge_story / collaboration_matrix / journey_timeline` 这些正文 family 虽然已经有 formal renderer
- 但它们还没有完全吃满 `narrative_segment / narrative_role / focus / density / scan`
- 结果是这些页一旦落在不同项目里，仍容易表现成“默认结构 + 支撑卡”的轻模板化状态

这一轮的目标不是继续扩概念，而是把这套叙事簇能力真正扩到更多正文 family，尤其是：

1. `bridge_story`
2. `collaboration_matrix`
3. `journey_timeline`

### 第一部分：扩 Solver

#### 问题

这三个 family 当前在 solver 里虽然能按 `page_series_type` 选中，但它们的职责分流还不够细：

- `bridge_story`
  - 既可能是“能力到场景的桥接页”
  - 也可能是“反馈闭环页”
  - 还可能是“产教融合 / 课程到行业”的转译页
- `collaboration_matrix`
  - 既可能是“岗位职责页”
  - 也可能是“交接链路页”
  - 还可能是“协作机制 + 应急补位”的责任分工页
- `journey_timeline`
  - 既可能是“阶段里程碑页”
  - 也可能是“研发推进 + 验证证据页”
  - 还可能是“问题复盘 + 质量改进”的迭代历程页

如果 solver 只把它们当成单一页系，renderer 再努力，也容易长成“默认结构”。

#### 具体改法

- 在 `layout_solver.py` 中细分 narrative role 偏置：
  - `bridge_story`
    - `solution_narrative`
    - `feedback_bridge`
    - `industry_translation`
  - `collaboration_matrix`
    - `role_responsibility`
    - `handoff_chain`
    - `coordination_resilience`
  - `journey_timeline`
    - `milestone_progress`
    - `iteration_evidence`
    - `retrospective_improvement`
- 根据 role 不同，调整：
  - `focus_strategy`
  - `scan_pattern`
  - `density_mode`
  - family/variant 选择分数

#### 目标语义

- `bridge_story`
  - 能力桥接类：优先 `diagram_first / staged_progression`
  - 反馈闭环类：优先 `diagram_first / single_anchor`
- `collaboration_matrix`
  - 职责分工类：优先 `grid_scan / balanced`
  - 交接链路类：优先 `staged_progression / diagram_first`
- `journey_timeline`
  - 里程碑推进类：优先 `staged_progression`
  - 复盘改进类：优先 `split_compare` 或更强的阶段对照感

#### 验收标准

- 同一个 family 在不同 narrative role 下，不能继续稳定输出同一套 `focus + density + scan`
- 不同项目只要叙事职责相近，应该得到相近的高质量判断；职责不同，则应稳定拉开

### 第二部分：扩 Renderer

#### 问题

这三个 family 当前都有正式渲染，但骨架差异还不够强：

- `bridge_story`
  - 现在更像“桥接弧线 + 侧栏卡片”
  - 还没有明显区分“桥接主线”和“反馈闭环”
- `collaboration_matrix`
  - 现在更像“角色卡 + 交接卡”
  - 还没有明显区分“职责矩阵”和“交接流程”
- `journey_timeline`
  - 现在更像“时间线主图 + 侧栏说明”
  - 还没有明显区分“里程碑推进”和“复盘改进”

#### 具体改法

- `bridge_story`
  - 新增至少两种 skeleton：
    - `bridge_arc_flow`
    - `feedback_loop_board`
  - 前者强调“能力 -> 任务 -> 结果”的桥接主线
  - 后者强调“执行 -> 反馈 -> 调整 -> 育人成效”的闭环
- `collaboration_matrix`
  - 新增至少两种 skeleton：
    - `role_grid_board`
    - `handoff_chain_board`
  - 前者强调职责并列
  - 后者强调交接顺序和补位机制
- `journey_timeline`
  - 新增至少两种 skeleton：
    - `milestone_rail`
    - `retrospective_split`
  - 前者强调推进节奏
  - 后者强调“问题复盘 / 质量改进”的前后分层

#### 强制原则

- 不允许只是把现有布局多套一层 class
- 这三类页至少要在以下维度里的 2 个以上形成真实差异：
  - 主图路径形态
  - 侧栏与主板关系
  - 并列 vs 流程
  - 线性推进 vs 闭环反馈
  - 时间推进 vs 复盘对照

### 第三部分：扩 Reviewer / Regression

#### 问题

如果 reviewer 还只知道第一批 skeleton，就会出现一种假象：

- 页面已经在视觉上切了一点
- 但系统自己看不出差异
- 或者系统只看到了 family 名不同，看不到职责型结构是否真的拉开

#### 具体改法

- 在 `rhythm_audit.py` 中补这三类页的新 skeleton markers 和 requirements
- 在 `deck_consistency_service.py` 中加入更细的 narrative-role drift 检查：
  - 同属 `solution` 簇，但如果 `bridge_story / collaboration / architecture / mapping` 之间职责不同，仍然需要拉开
- 在 `front-segment regression` 中补对这三类页的 cluster 识别与聚合观测

#### 回归输出补充

每个任务除原有 `front-segment` 指标外，再补：

- `solution_cluster_family_mix`
- `solution_cluster_skeleton_mix`
- `timeline_vs_bridge_vs_collaboration_drift`

#### 通过标准

- 若真实任务前半段含有 `bridge_story / collaboration_matrix / journey_timeline` 中任意两类，不允许它们仍共用近似同构 skeleton
- 若 `solution cluster` 已覆盖多个职责角色，但 `focus / density / scan / skeleton` 仍没有明显切换，则本轮判失败

### 建议执行顺序

#### Batch 22

- `layout_solver.py`
  - 增加 `bridge_story / collaboration_matrix / journey_timeline` 的 narrative-role 分流偏置

#### Batch 23

- `formal_render_engine.py`
  - 为上述三类页分别补第二骨架，并消费 `focus / density / scan`

#### Batch 24

- `rhythm_audit.py`
  - 补三类页的新 skeleton requirements
- `deck_consistency_service.py`
  - 增加 solution-cluster 内部职责切换检查

#### Batch 25

- `tests`
  - 增加 solver narrative-role 分流测试
  - 增加 renderer skeleton 差异测试
  - 增加 regression 聚合测试

#### Batch 26

- 真实任务回归
  - 优先找包含 `bridge_story / collaboration_matrix / journey_timeline` 的任务样本
  - 若本地样本不足，再从现有 preview 任务中补相近项目做 smoke check

### 本轮审核问题

给 `Euler` 的审核问题更新为：

1. 把 `bridge_story / collaboration_matrix / journey_timeline` 作为下一批 narrative families 扩展目标，是否命中了当前正文 family 最明显的“还没吃满信号”的缺口？
2. 这三类页按职责进一步细分 narrative role，是否合理，还是哪里还不够克制？
3. 给这三类页分别补“桥接主线 / 反馈闭环 / 职责矩阵 / 交接链路 / 里程碑推进 / 复盘改进”这些 skeleton，是否足以让它们真正摆脱默认模板感？
4. 把回归扩展到 `solution cluster` 内部职责切换，是否足够判断“正文 family 扩展后，页面不会又重新长成一套默认结构”？

## 当前待执行轮次：Targeted Family Remediation After Real-Task Validation

### 真实任务结论

`bridge_story / collaboration_matrix / journey_timeline` 的首轮定向真实任务已经跑完，结果不是“都命中”，而是出现了明显分化：

- `bridge_story`
  - `task 158`
  - `primary_pass`
  - 真正命中页不是封面误判，而是 `page 2 / 35 / 36`
  - 命中为 `feedback_bridge -> feedback_loop_board`
- `collaboration_matrix`
  - `task 159`
  - `miss`
  - 仅出现 1 个目标页：`page 35`
  - 实际落点为 `role_responsibility -> role_grid_board`
  - 没有进入目标的 `handoff_chain -> handoff_chain_board`
- `journey_timeline`
  - `task 160`
  - `miss`
  - 出现 3 个目标页，但 role 与 skeleton 没有稳定绑定
  - `page 25`: `iteration_evidence -> retrospective_split`
  - `page 30`: `milestone_progress -> retrospective_split`
  - `page 34`: `milestone_progress -> milestone_rail`

这轮结果说明：

- `bridge_story` 已具备真实落地能力
- `collaboration_matrix` 当前更容易滑回“职责矩阵”
- `journey_timeline` 当前存在“role 选到了 A，skeleton 却落到 B”的错配

### 根因判断

#### collaboration_matrix

当前更像是“交接链路诱发不够强”，而不是 renderer 完全不可用：

- solver 仍更容易把“岗位职责 / 多角色 / 协同”理解为 `role_responsibility`
- `handoff / escalation / backup / resilience` 这些词还没有足够强地压过“职责矩阵”语义
- 所以真实任务会稳定滑回 `role_grid_board`

#### journey_timeline

当前不是“timeline family 不会出”，而是“role 与 skeleton 没绑死”：

- solver 已能识别出 `iteration_evidence / milestone_progress`
- renderer 也会产出 `retrospective_split / milestone_rail`
- 但两者之间仍允许交叉错配
- 最终会出现：
  - `iteration_evidence + retrospective_split`
  - `milestone_progress + retrospective_split`
  - `milestone_progress + milestone_rail`

这说明当前系统缺的是“role -> variant -> skeleton”强绑定，不是单纯再多加一个时间线样式。

### 第一部分：收紧 Solver

#### collaboration_matrix

目标不是让它“更常命中 collaboration_matrix”，而是让已经命中的 `collaboration_matrix` 更稳定切到 `handoff_chain`。

具体改法：

- 对以下语义词组增加显著权重：
  - `交接`
  - `升级`
  - `补位`
  - `接力`
  - `应急`
  - `链路`
  - `值班`
  - `轮转`
- 如果同页同时出现：
  - 多角色名
  - 交接动作
  - 异常升级/补位表达
  - 则优先推向 `handoff_chain`
- 仅当页面主要是：
  - 职责边界
  - 角色分工
  - 岗位说明
  - 才保留 `role_responsibility`

#### journey_timeline

目标不是扩大时间线 family 覆盖，而是让“复盘类语义”稳定压到 `retrospective_improvement`。

具体改法：

- 对以下词组提高 `retrospective_improvement` 权重：
  - `复盘`
  - `问题`
  - `改进`
  - `修复`
  - `返工`
  - `优化`
  - `收敛`
  - `稳定版本`
- 若页面同时出现：
  - 阶段推进
  - 问题暴露
  - 改进行动
  - 则优先判成 `retrospective_improvement`
- 仅当页面主要是：
  - 节点推进
  - 里程碑
  - 阶段产出
  - 才保留 `milestone_progress`

### 第二部分：收紧 Renderer

#### collaboration_matrix

当前要避免“role 变了，视觉上还是角色卡片矩阵”。

具体改法：

- `role_grid_board`
  - 继续服务 `role_responsibility`
  - 强调并列角色、职责边界、分工说明
- `handoff_chain_board`
  - 只服务 `handoff_chain`
  - 强调顺序链路、升级箭头、补位节点、兜底关系

强制规则：

- `handoff_chain` 不允许回落成并列 2x2 角色卡矩阵
- 必须出现明显的顺序或接力关系证据：
  - 主链
  - 升级支线
  - 补位节点

#### journey_timeline

当前要避免“复盘页只是普通时间线换个标题”。

具体改法：

- `milestone_rail`
  - 只服务 `milestone_progress`
  - 强调节点推进、阶段顺序、版本里程碑
- `retrospective_split`
  - 只服务 `retrospective_improvement`
  - 强调“问题暴露 / 改进行动”成对结构

强制规则：

- `retrospective_improvement` 不允许再落到纯线性时间轴说明页
- `retrospective_split` 至少要有 2 组“问题 -> 改进”可见结构

### 第三部分：收紧 Acceptance / Reviewer

#### collaboration_matrix

- 若 `narrative_role = handoff_chain`
  - 交付门禁必须要求：
    - `data-layout-skeleton="handoff_chain_board"`
    - 明确链路型 structure markers
  - 不允许 `role_grid_board` 通过

#### journey_timeline

- 若 `narrative_role = retrospective_improvement`
  - 交付门禁必须要求：
    - `data-layout-skeleton="retrospective_split"`
    - 可见问题/改进双列或双区结构
- 若 `narrative_role = milestone_progress`
  - 交付门禁必须要求：
    - `data-layout-skeleton="milestone_rail"`

这一步的目的不是更严格地“拦页”，而是阻止 role/skeleton 错配被静默放过。

### 第四部分：修正定向任务文案

真实任务已经证明，当前 `collaboration_matrix` 文案还不够把 solver 推到 `handoff_chain`。

#### collaboration_matrix 任务文案修正

- 减少“岗位职责边界”在描述中的占比
- 提高以下表达占比：
  - `跨班次交接`
  - `异常升级`
  - `临时补位`
  - `接力处置`
  - `谁接谁`
  - `断点如何补`

#### journey_timeline 任务文案修正

- 减少“里程碑推进”的中性表述
- 提高以下表达占比：
  - `哪一轮测试暴露了什么问题`
  - `如何修复`
  - `改进后指标如何变化`
  - `如何从问题版本收敛到稳定版本`

### 建议执行顺序

#### Batch 27

- `layout_solver.py`
  - 收紧 `collaboration_matrix / journey_timeline` 的 role 权重
- `narrative_roles.py`
  - 必要时补更明确的词组映射

#### Batch 28

- `formal_render_engine.py`
  - 强化 `handoff_chain_board / retrospective_split` 的结构差异
  - 建立 role -> variant -> skeleton 的硬绑定

#### Batch 29

- `rhythm_audit.py`
  - 增加 `handoff_chain_board / retrospective_split` 的必需结构标记
- `page_acceptance.py`
  - 阻止 role/skeleton 错配静默通过

#### Batch 30

- `docs/v4_targeted_validation_tasks_plan.md`
  - 修正文案，做第二轮 targeted rerun 准备

#### Batch 31

- 第二轮真实任务回归
  - 先重跑 `collaboration_matrix / journey_timeline`
  - 若两者转正，再进入 `3` 次稳定性重跑

### 本轮审核问题

给 `Euler` 的审核问题更新为：

1. 这版修正方案是否真正对准了 `task 159 / 160` 的真实 miss，而不是泛泛补 family？
2. 先收紧 `solver -> renderer -> acceptance`，再做第二轮 targeted rerun，这个顺序是否正确？
3. 对 `collaboration_matrix` 来说，把“职责矩阵”和“交接链路”严格拆开，是否足以避免再次滑回 `role_grid_board`？
4. 对 `journey_timeline` 来说，用 role -> skeleton 强绑定来解决错配，是否比继续加更多 skeleton 更合理？
