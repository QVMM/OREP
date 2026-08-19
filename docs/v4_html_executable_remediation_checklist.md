# V4 HTML 可执行改造清单

## 目标

这份清单聚焦三个问题：

1. 修掉 `preview_157` 已经暴露出来的线上级问题：内部字段泄漏、占位词上屏、页面溢出、修复后风格跑偏。
2. 解决“AI 内容塞进固定 HTML 模板”的强烈模板感，让页面变成“按页职责生成构图”，而不是“按固定壳填文案”。
3. 建立 deck 级风格分配与验收机制，避免 100 个用户最后拿到的是同一种 PPT。

---

## 成功标准

### P0 完成标准

- `preview_157` 同类问题清零：
  - 页面中不再出现 `transition_role / visual_intent / *_anchor / *_proof / *_execution / family_id`
  - 页面中不再出现 `请上传 / 请替换 / placeholder / screenshot` 等终稿禁用词
  - 页面无底部截断、无卡片超高、无 SVG 黑块
- 修复后的页面仍保持与原 deck 一致的主题、字体、页眉页脚和版式语言
- 新生成 deck 进入 `preview_*` 前，必须经过自动验收

### P1 完成标准

- `architecture_system / practice_evidence / value_matrix / closing_board / protocol_board / collaboration_matrix / journey_timeline / bridge_story / innovation_compare` 不再走 `_render_generic`
- 每个 family 至少有 2 个真实变体
- 页面主内容不再依赖 `_semantic_pool` 的“顺序切片填卡片”

### P2 完成标准

- deck 内同一 family 连续页数不超过 2
- deck 内同一结构占比不超过 30%
- 每套 deck 至少覆盖 1 张证据页、1 张图表页、1 张流程/架构页、1 张总结页
- style preset 不再只是换色，而是能切换整套视觉语言

---

## P0 修 Bug

### P0-1 渲染输入白名单化，阻断内部字段泄漏

**改动目标**

不要再把内部控制字段当作可渲染文案源。正式渲染层只吃“用户可见语义字段”。

**代码触点**

- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`
  - `_semantic_pool()` 目前把 `transition_role`、`visual_intent` 直接并入内容池
- `ai-scoring/app/services/ppt/v4/formal_page_sequence.py`
  - `_merge_page_meta()` 目前把 `transition_role`、`visual_intent`、`layout_family_id`、`layout_variant` 继续挂到页面元数据上
- `ai-scoring/app/services/ppt/presentation_sanitizer.py`
  - 目前是“生成后正则擦屁股”，但还没覆盖这一批新泄漏词

**具体改法**

- 在 `formal_render_engine.py` 新增 `_visible_semantic_pool()`，仅允许以下字段进入最终文案池：
  - `title`
  - `subtitle`
  - `page_goal`
  - `core_argument`
  - `audience_takeaway`
  - `content_points`
  - `evidence_hints`
- 明确禁止以下字段进入渲染：
  - `transition_role`
  - `visual_intent`
  - `emphasis_mode`
  - `contract_id`
  - `layout_family_id`
  - `layout_variant`
  - 任意命中 `*_anchor / *_proof / *_execution / *_flow / *_orbit / *_landing` 的系统 token
- `formal_page_sequence.py` 保留这些字段给调度层使用，但新增 `render_safe_meta` 或 `visible_content_meta`，把正式渲染输入和内部控制输入分离
- `presentation_sanitizer.py` 增加统一黑名单正则，兜底擦除系统 token

**验收标准**

- 跑一次 `preview_157` 回归检查，0 页出现上述内部字段
- `page_3 / page_7 / page_40` 这类页面不再出现 contract token

---

### P0-2 去掉正式页可见调试信息

**改动目标**

`family_id`、variant、空 eyebrow 不能出现在用户页面上。

**代码触点**

- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`
  - `_page_shell()` 当前会把 `family_id` 直接输出到 footer
- `ai-scoring/app/services/ppt/v4/render_engine.py`
  - 旧渲染器也会输出 `data-family-id` 和页面内 family 信息

**具体改法**

- `formal_render_engine.py`
  - footer 仅保留项目名、页码、章节信息
  - `family_id` 和 `variant` 仅允许保存在 `data-*` 属性中，且默认不展示
  - `_eyebrow()` 增加空值和系统值过滤，空时直接不渲染
- `render_engine.py`
  - 旧链路同样移除页面内可见的 `family_id`
- 增加 `debug_render` 开关
  - 本地调试时可显示 family
  - 生产输出强制隐藏

**验收标准**

- `preview_157` 任意页底部不再出现 `evidence_board.caption_grid` 这类信息

---

### P0-3 占位词、提示词、修复提示语彻底禁止上屏

**改动目标**

终稿页不能出现“请上传”“请替换”“支持上传”“截图占位”等任何占位语。

**代码触点**

- `ai-scoring/app/services/ppt/presentation_sanitizer.py`
- `ai-scoring/app/services/ppt/html_generator.py`
  - `_series_slot_placeholder_body()`
  - `_should_use_series_placeholder_body()`
- `ai-scoring/app/services/ppt/adapter_code/output_adapter.py`
  - `image_placeholder` 会把占位信息继续传到后面

**具体改法**

- 在 `presentation_sanitizer.py` 增加一组终稿禁用词：
  - `请上传`
  - `请替换`
  - `placeholder`
  - `需现场上传`
  - `支持上传`
  - `自动替换为真实证据图`
  - `dashboard screenshot`
  - `policy screenshot`
- 将占位逻辑分成两层：
  - 编辑态可保留占位语
  - 交付态统一转换为“缺图降级组件”
- 缺图时不展示提示文案，改为：
  - 证据页显示“已验证结论 + 来源类型 + 数据摘要”
  - 截图位退化成无图卡片或文字摘要卡片

**验收标准**

- `page_35` 这类页不再出现“请上传/请替换”
- 搜索 `preview_*` 目录，终稿 HTML 中 0 次命中禁用词

---

### P0-4 溢出、截断、SVG 黑块问题单独修

**改动目标**

先把当前明显坏页修掉，避免继续用“overflow:hidden 把问题藏起来”。

**代码触点**

- `ai-scoring/app/services/ppt/ppt_service.py`
  - `_analyze_html_page_quality()`
  - `_finalize_v4_formal_page()`
- `ai-scoring/app/services/ppt/html_renderer.py`
  - Playwright 截图链路
- `preview_157/page_35.html`
- `preview_157/page_36.html`

**具体改法**

- 在质检阶段加入 DOM 级溢出检查
  - 检测 `scrollHeight > clientHeight`
  - 检测绝对定位元素是否超出 1920x1080 安全边界
  - 检测 footer 是否被遮挡
- 为 SVG 页面加单独规则
  - 不允许把 HTML 卡片样式直接套到 SVG `<rect>`
  - SVG 节点颜色、圆角、标签必须走 SVG 属性生成
- 对协作矩阵、时间线、图文混排页增加“内容预算”
  - 最大卡片数
  - 最大段落数
  - 最大行数
  - 超限时自动摘要

**验收标准**

- `page_35 / page_36` 截图回归通过
- 质检报告能明确标记 `overflow / footer_cutoff / svg_style_mismatch`

---

### P0-5 修复链路必须继承原 deck 的主题和壳

**改动目标**

页面一旦进入 rebuild / repair，不能换成另一套 UI。

**代码触点**

- `ai-scoring/app/services/ppt/ppt_service.py`
  - `_finalize_v4_formal_page()`
  - `_render_v4_formal_html_deck()`
- `ai-scoring/app/services/ppt/v4/quality_bridge.py`
- `ai-scoring/app/services/ppt/v4/repair_planner.py`
- `ai-scoring/app/services/ppt/v4/deck_blueprint_planner.py`

**具体改法**

- 在 `_finalize_v4_formal_page()` 的 repair 上下文中强制注入：
  - `style_preset_id`
  - `requested_theme`
  - `theme_tokens`
  - `typography`
  - `surface`
  - `signature_elements`
  - `layout_family_id`
  - `layout_variant`
- rebuild 后的页面必须经过统一的 `formal shell wrap`
  - 使用同一套页边距、topbar、footer、标题层级和配色变量
- 如果 repair 输出不是 `data-v4-formal`，不直接落盘
  - 先走 normalize/wrap
  - 仍不通过则回退到同 family 的降级变体，而不是旧模板页

**验收标准**

- `preview_157` 中“跑偏”的 6 页不再切换成另一套视觉体系

---

### P0-6 增加交付前自动验收，失败页禁止进入 preview

**改动目标**

把人工发现问题，改成生成链路自动拦截问题。

**代码触点**

- `ai-scoring/app/services/ppt/html_renderer.py`
- `ai-scoring/app/services/ppt/vision_judge_service.py`
- `ai-scoring/app/services/ppt/ppt_service.py`
- 建议新增：
  - `ai-scoring/app/services/ppt/v4/page_acceptance.py`
  - `ai-scoring/scripts/check_preview_deck.py`

**具体改法**

- 每页生成后自动做 4 类检查：
  - DOM 检查：系统 token、占位词、空 eyebrow、空标题
  - 布局检查：溢出、遮挡、超边界
  - 截图检查：大面积空白、重叠、底部截断
  - 结构检查：是否保留 formal shell 和 deck 主题变量
- 自动验收失败时：
  - 不写入 `preview_*`
  - 进入“同 family 重排”
  - 重排失败再进入“同 style 的降级变体”

**验收标准**

- 本地可执行一次整套 deck 验收命令，并返回页级失败原因

---

## P1 去模板感

### P1-1 补齐 family renderer，停止大面积 fallback 到 `_render_generic`

**改动目标**

所有已注册 family 都要有真实渲染实现，不能注册了却最后还是 generic。

**代码触点**

- `ai-scoring/app/services/ppt/v4/layout_grammar_registry.py`
- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`

**必须补齐的 family**

- `architecture_system`
- `practice_evidence`
- `value_matrix`
- `closing_board`
- `protocol_board`
- `collaboration_matrix`
- `journey_timeline`
- `bridge_story`
- `innovation_compare`

**具体改法**

- `formal_render_engine.py` 从 if/elif 分发改成 renderer registry
- 每个 family 独立一个 renderer 函数
- 每个 family 至少 2 个 variant
  - 例如 `practice_evidence`
    - `ioe_board`
    - `timeline_demo`
  - `closing_board`
    - `statement_anchor`
    - `metric_recap`
- `_render_generic` 只保留给真正未注册 family，且打日志，不允许进入正式交付

**验收标准**

- `render_formal_v4_pages()` 中，正式交付页 0 次使用 `_render_generic`

---

### P1-2 从“顺序切片填卡片”改成“按槽位组装页面”

**改动目标**

不要再把一堆句子从 `_semantic_pool` 顺序切到卡片里，这正是模板味最强的来源。

**代码触点**

- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`
- `ai-scoring/app/services/ppt/v4/page_blueprint_builder.py`
- 建议新增：
  - `ai-scoring/app/services/ppt/v4/slot_mapper.py`

**具体改法**

- 每个 family 定义自己的内容槽位 schema，例如：
  - `evidence_board`
    - `headline`
    - `claim`
    - `evidence_cards`
    - `source_note`
  - `architecture_system`
    - `north_star`
    - `layer_blocks`
    - `data_flow`
    - `operating_constraints`
  - `closing_board`
    - `closing_statement`
    - `metric_recap`
    - `next_step`
- `page_blueprint_builder.py` 输出结构化槽位原料，不再只给扁平 `content_points`
- renderer 只消费明确槽位，不再猜测哪一句塞哪块

**验收标准**

- 页面结构和内容职责一一对应
- 同 family 的不同项目页不再只是“相同壳子 + 不同文案”

---

### P1-3 抽出统一的 formal shell，repair 与正常渲染共用

**改动目标**

正常页和修复页必须共用一个 deck shell，而不是各自长各自的。

**代码触点**

- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`
- `ai-scoring/app/services/ppt/ppt_service.py`
- 建议新增：
  - `ai-scoring/app/services/ppt/v4/formal_shell.py`

**具体改法**

- 把 `_page_shell()` 抽成独立模块
- shell 层统一负责：
  - 1920x1080 画布
  - deck 主题变量
  - 字体系统
  - 页边距
  - 页眉页脚
  - 安全区
- 所有 repair/rebuild 页最终都通过 shell 包一层再出库

**验收标准**

- deck 内不存在“同一套文稿，两种壳”的情况

---

### P1-4 去掉明显网页味的视觉默认值

**改动目标**

PPT 页面要像路演页，不要像 dashboard 或营销站落地页截图。

**代码触点**

- `ai-scoring/app/services/ppt/v4/formal_render_engine.py`
- `ai-scoring/app/services/ppt/html_generator.py`
- `ai-scoring/app/services/ppt/html_renderer.py`

**具体改法**

- 降低以下网页味元素的默认出现率：
  - hover 动效
  - `backdrop-filter`
  - 全页玻璃卡
  - 类导航栏 topbar 视觉
  - dashboard 式 KPI 卡铺满
- 强化 PPT 语言：
  - 大标题锚点
  - 明确的证据主视觉
  - 单页节奏起承转合
  - 版式重心与视线引导
- `style_presets` 不再只输出颜色，也输出：
  - 字体组合
  - 边框/阴影策略
  - 面层材质策略
  - 图表风格
  - 图形语言

**验收标准**

- 像 `page_29` 这种页面，保留高级感，但明显减少“网页组件感”

---

### P1-5 给布局器增加内容预算，而不是只靠 CSS 裁剪

**改动目标**

溢出问题要在布局决策时解决，而不是最后 `overflow:hidden`。

**代码触点**

- `ai-scoring/app/services/ppt/v4/layout_solver.py`
- `ai-scoring/app/services/ppt/v4/schemas.py`
- `ai-scoring/app/services/ppt/v4/deck_blueprint_planner.py`

**具体改法**

- 在 `LayoutPlan.region_plan` 里增加每类版面的内容预算：
  - `max_cards`
  - `max_metrics`
  - `max_paragraphs`
  - `max_lines_per_block`
  - `image_slots`
- renderer 超预算时不硬塞，改走摘要或减项
- 把 safe margin、标题区高度、footer 保护区也纳入预算

**验收标准**

- 页面的“能放下”是由布局器保证，而不是靠最终裁切

---

## P2 做风格多样化

### P2-1 在 DeckBlueprint 里正式引入 Deck DNA

**改动目标**

先确定这套 deck 的整体视觉人格，再决定页面长什么样。

**代码触点**

- `ai-scoring/app/services/ppt/v4/schemas.py`
- `ai-scoring/app/services/ppt/v4/deck_blueprint_planner.py`
- `ai-scoring/app/services/ppt/v4/preference_resolver.py`

**建议新增字段**

- `deck_dna.visual_mode`
  - `gov_evidence`
  - `industrial_execution`
  - `research_story`
  - `commercial_growth`
- `deck_dna.tone`
  - `calm`
  - `assertive`
  - `technical`
  - `ceremonial`
- `deck_dna.surface_mode`
  - `paper`
  - `solid_panel`
  - `soft_light`
  - `editorial`
- `deck_dna.chart_style`
- `deck_dna.typography_pair`
- `deck_dna.shape_language`
- `deck_dna.imagery_policy`

**具体改法**

- `preference_resolver.py` 根据用户风格选择、项目类型、比赛场景推导 DNA
- `deck_blueprint_planner.py` 把 DNA 放进 `DeckBlueprint`
- 渲染器、布局器、修复器都从 deck DNA 读风格约束

**验收标准**

- 不同项目即使内容结构类似，整套 deck 的气质也会明显不同

---

### P2-2 布局求解从“取第一个”升级为“带约束打分选择”

**改动目标**

彻底解决“所有人都用第一个 family、第一个 variant”的同质化问题。

**代码触点**

- `ai-scoring/app/services/ppt/v4/layout_solver.py`
- `ai-scoring/app/services/ppt/v4/layout_grammar_registry.py`
- `ai-scoring/app/services/ppt/v4/variant_history.py`

**具体改法**

- `layout_solver.py` 不再直接使用：
  - `allowed_layout_families[0]`
  - `candidate_variants[0]`
- 改成 family/variant 打分机制，评分输入至少包括：
  - `page_series_type`
  - `page_role`
  - `deck_dna`
  - `recent_families`
  - `recent_variants`
  - `content_density`
  - `evidence_needed`
  - `chart_needed`
- 加硬约束：
  - 同 family 连续不超过 2 页
  - 同 variant 连续不超过 1 页
  - 同结构占比不超过 30%

**验收标准**

- 两套不同项目的 deck，family/variant 序列明显不同

---

### P2-3 在 deck consistency 层增加反同质化检查

**改动目标**

让“风格重复”和“结构单一”成为可被机器拦截的问题。

**代码触点**

- `ai-scoring/app/services/ppt/v4/deck_consistency_service.py`

**具体改法**

- 新增检查项：
  - `max_same_family_run`
  - `same_structure_ratio`
  - `required_page_type_mix`
  - `ending_strength`
  - `evidence_page_presence`
  - `chart_page_presence`
  - `process_page_presence`
- 报告中直接返回建议动作：
  - `rebalance_family_distribution`
  - `insert_evidence_page`
  - `replace_repeated_variant`
  - `strengthen_closing_type_mix`

**验收标准**

- 一套 deck 即使单页评分都高，也不能因为“长得都一样”而直接过 gate

---

### P2-4 做 style pack，不再只是换配色

**改动目标**

一个 style preset 要能改变整套 deck 的视觉语言，而不是只换主色。

**代码触点**

- `ai-scoring/app/services/ppt/v4/style_presets.py`
- `ai-scoring/app/services/ppt/v4/preference_resolver.py`

**建议至少提供 4 套**

- 政策证据型
- 产业落地型
- 科研答辩型
- 商业增长型

**每套 style pack 必须控制**

- 字体组合
- 颜色系统
- 面层材质
- 阴影与边框强度
- 图表默认样式
- 主视觉构图偏好
- family 选择倾向

**验收标准**

- 用户切不同风格时，不是“同一页换个蓝色/绿色”，而是整套 deck 的视觉性格改变

---

### P2-5 建立回归样本库和截图基准

**改动目标**

后面每次改样式或布局器，都能自动知道有没有把 deck 又改回“模板味”。

**代码触点**

- `ai-scoring/app/services/ppt/html_renderer.py`
- `ai-scoring/app/services/ppt/vision_judge_service.py`
- 建议新增：
  - `ai-scoring/tests/fixtures/ppt_previews/`
  - `ai-scoring/tests/test_v4_preview_acceptance.py`

**具体改法**

- 固定一组回归样本：
  - `preview_157`
  - 再补 3 到 5 个不同项目类型 deck
- 保存每页截图和页级诊断结果
- 每次改动后自动检查：
  - 是否泄漏系统词
  - 是否溢出
  - 是否出现大面积空白
  - 是否结构重复率过高

**验收标准**

- 新版本上线前可以跑一次 deck 回归，快速判断是否倒退

---

## 推荐实施顺序

### 第一阶段，先止血，3 到 5 天

1. P0-1 渲染输入白名单化
2. P0-2 去掉可见 family/debug 信息
3. P0-3 禁止占位词上屏
4. P0-5 修复链路继承 theme shell
5. P0-6 自动验收接到 preview 写盘前

### 第二阶段，修结构，5 到 10 天

1. P0-4 溢出与 SVG bug 修复
2. P1-1 补 family renderer
3. P1-2 引入 slot mapper
4. P1-3 抽 formal shell
5. P1-5 布局内容预算

### 第三阶段，拉开上限，1 到 2 周

1. P1-4 去网页味
2. P2-1 引入 deck DNA
3. P2-2 升级 layout solver
4. P2-3 增加反同质化 gate
5. P2-4 扩 style pack
6. P2-5 建回归样本库

---

## 建议新增的最小技术对象

- `ai-scoring/app/services/ppt/v4/page_acceptance.py`
  - 负责页级硬验收
- `ai-scoring/app/services/ppt/v4/slot_mapper.py`
  - 负责 family 槽位映射
- `ai-scoring/app/services/ppt/v4/formal_shell.py`
  - 负责统一 deck shell
- `ai-scoring/tests/test_v4_preview_acceptance.py`
  - 负责回归测试

---

## 最后判断

当前问题不是单个页面“提示词没清掉”这么简单，而是渲染架构还停留在：

- 结构层注册了一堆 family
- 求解层默认选第一个
- 渲染层大面积 fallback generic
- 修复层又换一套壳
- 交付前缺少截图验收

所以这次改造要按“渲染输入治理 + family 渲染补齐 + deck DNA + 自动验收”四条线一起推进。只修词、修 CSS、修 157 这一套，治不了根。
