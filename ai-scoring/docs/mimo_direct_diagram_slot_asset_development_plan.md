# MiMo Direct + Pure Diagram Asset 开发思路与差距清单

更新时间：2026-05-07

## 1. 当前结论

当前方向应从“本地 renderer 接管页面”和“先画一个固定 slot 再塞图”两条路彻底切回：

**系统先产出裁剪后的纯图表资产和真实尺寸，MiMo 再基于这张图自主完成整页 PPT 设计。**

也就是说：

- MiMo 决定整页布局、视觉重心、文字区、图表区、证据区、留白和节奏。
- 系统不预设图表外框、不强制 slot 尺寸、不把图表放进一个大白板区域。
- 系统在本地把 SVG 跑出来后，只保留真实图形内容，去掉无意义背景、外层空白和套娃容器。
- 系统把 cropped SVG / PNG 预览、真实宽高、比例、推荐最小展示尺寸、可读性约束交给 MiMo。
- MiMo 像顶级 PPT 设计师一样判断：这张图在这一页应该多大、放哪里、周围留多少呼吸感、哪些文字留在页面、哪些内容进入讲稿。
- 图表代码可以由 Fireworks/open graph 这类专业图表生成能力产出，也可以由 MiMo 产出后由系统审查修复。
- 系统负责检查图表自身是否溢出、重叠、裁切、文字过小、颜色不统一、内层大白板、套娃容器。
- 系统最终检查整页是否像 PPT、是否有呼吸感、是否主视觉成立、是否把详细信息合理转移到 speaker notes JSON。

这个路线比之前 schema renderer 和 locked slot 分支更符合产品目标：**页面仍然是 AI 自由设计，系统只把 AI 最容易翻车的图表生产、裁切、测量和审查补强。**

## 2. 已经验证到哪里

### 2.1 已经完成的实验能力

- 已建立隔离实验线：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/`
- 已完成 MiMo planning JSON 校验：确保 MiMo 先说明页面意图、内容分区和图表规格。
- 已完成图表资产生成链路实验：从 planning/spec 生成 SVG 图表资产。
- 已完成 SVG 裁剪与尺寸读取实验：去除大空白，保留真实图表边界。
- 已完成图表内部 fit audit：检查图表资产是否有裁切、溢出、文字过小、重叠。
- 已完成 repair routing：当图表资产不合格时，生成针对性修复 payload，而不是进入模板兜底。
- 已完成 final injection audit：模拟把 SVG 放进 MiMo 预留区域后，检查是否适配。
- 已完成 3 页效果 demo：架构页、实操流程页、指标看板页。

### 2.2 当前 demo 产物

3 页效果样张：

- HTML 入口：`/Users/liuyixing/项目/OREP/ai-scoring/experiments/mimo_direct_diagram_audit/two_step_asset_flow/effect_demo_runs/three_page_effect_demo_20260507_174918/three_page_effect_demo.html`
- 总览截图：`/Users/liuyixing/项目/OREP/ai-scoring/experiments/mimo_direct_diagram_audit/two_step_asset_flow/effect_demo_runs/three_page_effect_demo_20260507_174918/screenshots/three_page_contact_sheet.png`
- 第 1 页：技术架构主链路
- 第 2 页：传感器校准实操路径
- 第 3 页：实操成效指标看板

### 2.3 当前效果判断

已经看到的正向结果：

- 图表没有再出现明显重叠、箭头裁切、文字遮挡。
- 图表资产可以独立裁剪、测量、嵌入，具备工程闭环基础。
- 第 3 页指标看板开始接近“专业表达类型”，比纯文字卡片更像 PPT。
- 系统没有接管整页布局，只是在图表资产层做增强，方向没有偏回固定模板。

仍然明显不足：

- 第 1、2 页图表被包在大面积白色区域里，页面空间没有被充分利用，PPT 版式失衡。
- 当前 slot/asset-frame 思路仍会诱导 MiMo 把图当成网页组件，而不是 PPT 主视觉素材。
- 第 1、2 页图表视觉冲击力仍偏弱，图表本身还不够“高级 PPT”。
- 现在的 3 页 demo 只是静态效果样张，不代表真实任务端到端稳定。
- 图表生成还没有接入真实 MiMo 页面设计输入包。
- 颜色统一、字体统一、主题适配目前是实验级，不是生产级。
- 指标看板还只是第二图表类型方向样张，没有完成完整生成/修复闭环。
- 讲稿层还没有作为信息承载出口，导致页面容易为了“详细”而变满、变散、变网页化。

## 3. 推荐产品架构

### 3.1 总流程

```text
用户问卷/项目材料
  -> Outline / Narrative Graph
  -> MiMo Page Planning
  -> Diagram Asset Planning
  -> 专业图表资产生成
  -> SVG Crop + Size Audit
  -> Pure Asset Packet
  -> MiMo Direct Page Layout
  -> Asset Mount / Embed
  -> Multimodal / DOM Visual Audit
  -> Targeted Repair
  -> HTML Preview / PPTX Export + Speaker Notes JSON
```

### 3.2 三步核心链路

#### Step 1：MiMo Planning

MiMo 先输出页面计划和讲稿框架，不直接生成最终 HTML。

输出内容应包括：

- 页面类型：封面、目录、架构、流程、证据、指标、成果、总结等。
- 页面核心信息：标题、副标题、主论点、裁判关注点。
- 内容分区：文字说明、证据材料、图表说明、结论句。
- 图表需求：是否需要架构图、流程图、时间线、指标看板、证据链。
- 图表规格：图表类型、节点、关系、重点标注、密度、方向、证据来源。
- 页面展示层：哪些内容必须上屏，哪些内容只进入讲稿。
- speaker notes JSON：先保持简版，只记录讲述要点、证据补充、转场提示，不做最终呈现设计。

关键原则：

- MiMo 用专业编辑和竞赛评委视角判断“这一页该怎么讲”。
- 页面不是资料全文搬运。上屏内容只留重点和主视觉，细节留给讲稿。
- 系统只校验 planning/notes 是否完整，不改写核心内容。

#### Step 2：System Diagram Asset

系统根据 `diagram_spec` 生成或修复图表资产。

可以接入的图表能力：

- Fireworks-tech-graph：优先用于架构图、流程图、时序图、网络拓扑、业务链路。
- MiMo diagram-only generation：用于更自由的图形表达，但必须经过 asset audit。
- 系统 SVG post-processing：只做裁剪、主题变量注入、字体统一、尺寸测量、危险元素移除。

系统禁止做的事：

- 禁止把整页改成固定模板。
- 禁止重新安排 MiMo 页面的文字和图表位置。
- 禁止因为图表太大就擅自压扁到不可读。
- 禁止用省略号牺牲核心图表文字。
- 禁止给图表套一个固定白色面板、网页卡片或 asset-frame 外壳。
- 禁止把图表外部留白当成资产的一部分交给 MiMo。

#### Step 3：Pure Asset Packet

系统把图表资产处理成可以交给 MiMo 排版的纯素材包。

资产包必须包含：

- `asset_id`
- `cropped_svg`
- `preview_png`
- `actual_width`
- `actual_height`
- `aspect_ratio`
- `recommended_display_width`
- `recommended_display_height`
- `minimum_readable_width`
- `minimum_readable_height`
- `visual_role_hint`: `dominant` / `balanced` / `support`
- `density`: `low` / `medium` / `high`
- `readability_notes`
- `theme_tokens`

资产包禁止包含：

- 本地路径。
- 页面坐标。
- slot 坐标。
- 外层白底面板。
- 上传框/网页组件提示。
- 任何让 MiMo 误以为必须保留外部容器的样式。

#### Step 4：MiMo Layout + Asset Mount

MiMo 拿到纯图、真实尺寸和最小可读约束后，再设计整页 HTML。

MiMo 需要判断：

- 这张图是全页主视觉、半页主视觉，还是辅助证据图。
- 图表应该横向铺开、居中悬浮、和证据点并列，还是切成局部叙事。
- 页面上只保留哪些关键词、指标、结论句。
- 哪些详细解释进入 speaker notes JSON。
- 如何利用留白形成呼吸感，而不是用白色卡片占住空间。
- 图表不能被拉伸变形，不能缩到低于最小可读尺寸。

系统最终只检查：

- 图表是否完整显示。
- 图表展示尺寸是否不低于最小可读尺寸。
- 页面是否出现图表和文字重叠。
- 图表是否与整页配色冲突。
- 是否出现大白板、上传控件、网页卡片感。
- 是否出现内容过密、讲稿缺失、上屏文字抢走主视觉。

## 4. 关键模块设计

### 4.0 产品级设计边界更新

根据 2026-05-07 的 pure asset / director / master 三轮样张观察，必须收回一个关键边界：

**MiMo 只能改中间内容区，不能改标题、页脚、页码、全局背景、全局字体、页面边距和整套 deck 的主题系统。**

这意味着：

- 标题区由 MiMo 原页面或上游 page shell 决定，content-region pass 不重写标题。
- 页脚、页码、项目名、品牌信息保持原样。
- 中间区域可以重新组织图表、短说明、证据锚点、局部强调和留白。
- 中间区域不能变成封面式大色块、巨型装饰数字或与整套 PPT 不一致的新风格。
- 设计感不是“每页都变一个样”，而是在统一 deck shell 内提升内容区的层级、节奏、清晰度和讲述性。

从 Impeccable 可以迁移的产品级原则：

- **先有产品/设计系统上下文，再做设计。** 对 PPT 来说就是先锁定 deck shell、字体、主题色、页眉页脚、边距和常用组件。
- **设计服务任务。** 我们这是产品型生成工具，不是品牌海报生成器；一致性比惊喜更重要。
- **空间是设计材料。** 空白必须有目的：引导视线、分隔信息组、制造停顿；不能只是没用掉。
- **卡片不是默认答案。** 图表不能被大白板、asset-frame、网页卡片壳包住；也不能卡片套卡片。
- **节奏来自紧密分组和组间留白。** 不是平均铺满，也不是大面积空着。
- **Polish 必须对齐设计系统。** 如果某页变得“好看但不像这一套 deck”，仍然失败。

建议增加一个 content-region design gate：

```json
{
  "shell_locked": true,
  "title_modified": false,
  "footer_modified": false,
  "page_number_modified": false,
  "background_modified": false,
  "content_region_only": true,
  "visible_text_budget_pass": true,
  "negative_space_has_intent": true,
  "deck_consistency_pass": true,
  "anti_patterns": []
}
```

### 4.1 MiMo Planning Prompt

目标：让 MiMo 先“想清楚这一页要讲什么、看什么、哪些不该上屏”，再进入页面设计。

必须强化：

- 职业院校技能大赛评委视角。
- 实操讲解和证据链视角。
- 架构师视角。
- 编辑视角。
- 反向审查：这页是否能被评委快速看懂并相信。
- PPT 讲看结合视角：页面负责抓重点和建立视觉记忆，讲稿负责承接详细说明。
- 信息分层视角：主标题、主视觉、关键结论、补充证据、讲稿细节必须分层。

必须禁止：

- 空泛总结。
- 重复页面标题。
- 只输出普通左右卡片。
- 把图表描述成装饰元素。
- 伪造证据。
- 把详细资料全部堆到页面上。
- 为了装满画布而牺牲呼吸感。

建议 planning JSON 增加：

```json
{
  "screen_content": {
    "must_show": ["本页必须上屏的主结论或关键指标"],
    "should_show": ["可上屏的短标签或证据锚点"],
    "move_to_speaker_notes": ["详细解释、过程背景、口头补充"]
  },
  "speaker_notes": {
    "talk_track": ["讲述顺序要点"],
    "evidence_expansion": ["证据如何解释"],
    "transition": "这一页如何过渡到下一页"
  }
}
```

### 4.2 Diagram Spec Validator

目标：在生成图表前，先确保图表任务足够完整。

检查内容：

- 图表类型是否合法。
- 节点/步骤/指标是否足够。
- 是否有主信息和重点标注。
- 是否有证据来源或评分映射。
- 是否带有密度、方向、层级、关系。
- 是否出现 HTML/SVG/CSS/坐标/生产链路越界字段。

### 4.3 Diagram Asset Generator

目标：把 `diagram_spec` 转成专业 SVG。

候选能力：

- Fireworks-tech-graph：作为优先实验对象。
- MiMo diagram-only：作为备用/增强对象。
- 自研 post-processor：做主题适配和安全修复，不接管设计风格。

生成要求：

- SVG 必须可独立裁剪。
- SVG 不能带大白底。
- SVG 文本不能依赖省略号。
- SVG 内部组之间不能重叠。
- 同类文字字号必须统一缩放。
- 箭头、marker、边框不能裁切。

### 4.4 SVG Crop + Size Engine

目标：拿到图表真实内容边界，避免图表带着巨大空白嵌入页面。

要做：

- 移除无意义背景 rect。
- 计算真实 bbox。
- 保留 marker、阴影、文字边界 padding。
- 输出 cropped SVG、actual_width、actual_height、aspect_ratio。
- 给 MiMo 提供推荐展示尺寸。

### 4.5 Pure Asset Packet Contract

目标：让 MiMo 拿到的是“可设计的纯图素材”，不是“必须塞进去的容器”。

建议结构：

```json
{
  "asset_id": "architecture_agriculture_flow__diagram_asset_001",
  "diagram_type": "architecture_flow",
  "delivery": {
    "cropped_svg": "<svg ...>",
    "preview_png_ref": "safe_preview_asset_ref",
    "background": "transparent",
    "outer_frame_removed": true
  },
  "geometry": {
    "actual_width": 1320,
    "actual_height": 246,
    "aspect_ratio": 5.37,
    "recommended_display_width": 860,
    "recommended_display_height": 160,
    "minimum_readable_width": 720,
    "minimum_readable_height": 135
  },
  "layout_guidance": {
    "visual_role_hint": "dominant",
    "preferred_compositions": ["wide_center_visual", "diagram_with_sparse_callouts"],
    "forbidden_compositions": ["small_card_grid", "white_panel_inside_white_panel", "corner_decoration"]
  },
  "readability": {
    "min_internal_text_size_px": 12,
    "density": "medium",
    "notes": ["图表是横向主链路，适合横向铺开，不适合压缩成窄卡片。"]
  }
}
```

MiMo 输出页面时可以声明一个 asset mount point，但这个 mount point 只是替换锚点，不是视觉外框：

```html
<figure
  data-diagram-asset-id="architecture_agriculture_flow__diagram_asset_001"
  data-asset-mount="true"
  data-asset-role="main-visual"
  data-asset-ratio="5.37"
  data-min-readable-width="720"
  data-layout-intent="以横向主链路承载本页技术架构记忆点"
></figure>
```

约束：

- 系统可以替换 mount point 的内部内容，但不设计整页。
- mount point 不能自带大白板、固定卡片壳、上传控件、slot 提示语。
- 如果 MiMo 把 mount point 做得太小，系统返回 layout repair。
- repair 不是“扩大 slot”，而是要求 MiMo 重新思考整页视觉重心和内容取舍。

### 4.6 Asset Mount + Page Visual Audit

目标：图表嵌入后同时检查图表安全和 PPT 设计质量。

硬失败：

- 图表裁切。
- 图表溢出 mount 区域。
- 图表文字小于最低字号。
- 图表内部重叠。
- 图表与页面文字重叠。
- 图表被拉伸变形。
- 出现二次大白板。
- 出现“请上传/占位图/系统提示语”。
- content-region pass 改动标题、页脚、页码、背景或全局主题。
- 页面风格与整套 deck shell 不一致。
- 使用封面式大色块、巨型装饰数字等破坏正文页一致性的手法。
- 页面上屏文字过密，且没有进入 speaker notes JSON。
- 主视觉低于页面视觉权重下限。

软警告：

- 图表占比偏小。
- 图表视觉权重不足。
- 颜色和整页主题轻微不一致。
- 边距过大。
- 辅助说明过多。
- 留白看起来是没用掉的空白，而不是设计呼吸感。
- 中间区构图连续多页重复，缺少轻微节奏变化。

### 4.7 Targeted Repair

目标：失败后只修失败点，不回到模板。

修复路线：

- 图表内部问题：回到 diagram generator repair。
- 图表尺寸问题：重新 crop 或要求图表生成器改变密度。
- mount 太小或页面失衡：回到 MiMo layout repair。
- 页面整体问题：回到 MiMo direct page repair。

禁止：

- 不允许进入本地固定模板 fallback。
- 不允许系统重排整页。
- 不允许把图表强行压缩到不可读。

## 5. 还差什么

### 5.1 P0：从 demo 到真实链路还差的关键块

1. **Pure Asset Packet 到 MiMo Layout 的真实接入**

当前还没有让 MiMo 在真实页面设计时稳定消费“纯图 + 真实宽高 + 最小可读尺寸”的资产包。

必须补：

- MiMo 页面 prompt 增加 pure asset packet 输入说明。
- asset mount parser/validator 接入真实 HTML。
- 禁止 MiMo 自己重写 SVG 或给图表套固定外框。
- 禁止图表外部出现 asset-frame、大白板、网页卡片壳。
- 输出 speaker notes JSON，承接页面未展示的详细内容。

2. **Fireworks 图表生成接入标准化**

当前已经看到 Fireworks 生成 SVG 的方向可行，但还没有标准化接入。

必须补：

- 输入 payload 标准。
- 输出 SVG 标准。
- 错误处理。
- 主题色注入。
- 字体统一。

3. **图表资产自动裁剪生产化**

当前裁剪是实验级。

必须补：

- 更准确的 bbox 计算。
- marker/阴影/文字保护。
- 对复杂 path、foreignObject、clipPath 的处理。
- 裁剪失败时的 repair route。

4. **图表展示与整页 PPT 感 audit**

必须能自动判断：

- 是否重叠。
- 是否裁切。
- 是否溢出。
- 是否字号过小。
- 是否大面积空白。
- 是否颜色突兀。
- 是否图表被容器白板包住。
- 是否页面留白失衡。
- 是否上屏文字过密但讲稿为空。

5. **MiMo layout repair**

如果 MiMo 把纯图摆得太小、页面失衡，或用容器浪费空间，系统必须能把问题反馈给 MiMo。

例如：

```text
当前 architecture_flow 图表推荐展示宽高为 860x160，最低可读宽度为 720。
你的页面把图表放在 420x180 的白色卡片里，图表自身只占卡片 45% 宽度，导致页面右侧和下方空白失衡。
请重新设计页面主体区：让图表作为主视觉直接参与版式，去掉图表外层白板，减少旁侧文字密度，把详细说明移入 speaker_notes JSON。
```

### 5.2 P1：让真实 PPT 质量明显提升还差的关键块

1. **封面 Director**

封面不能像正文页。

需要：

- 独立 prompt。
- 独立 shell。
- 禁止页码。
- 禁止图片占位符。
- 强主视觉、项目定位、一句话价值、团队/赛事信息。

2. **Agenda Director**

目录不能再让 MiMo 猜。

需要：

- 从真实 outline/narrative graph 抽章节。
- 页码范围真实计算。
- 每章一句目标。
- 汇报节奏。
- MiMo 再自由设计目录页。

3. **Professional Expression Planner**

每页先判断专业表达类型：

- 架构图。
- 流程图。
- 时间线。
- 甘特图。
- 指标看板。
- 证据板。
- 对比矩阵。
- 风险雷达。
- 路线图。

这个 planner 不是选模板，而是告诉 MiMo 和图表系统“这一页应该用什么专业表达”。

4. **Evidence Placeholder Schema**

图片位置要像 PPT 证据位，不像网页上传框。

需要区分：

- 政策网页截图。
- 设备照片。
- 实操照片。
- 系统截图。
- 数据样例。
- 证书/专利。
- 现场/人物/团队照片。

5. **Multimodal Visual Audit**

最终必须用视觉模型审查整页截图。

检查：

- 像不像 PPT。
- 有没有呼吸感。
- 主视觉是否成立。
- 图表是否专业。
- 内容是否可信。
- 是否有网页感。
- 是否套娃。
- 是否大面积空白。

### 5.3 P2：稳定进入产品还差的关键块

1. **真实问卷端到端回归**

至少跑：

- 智慧农业。
- 非农业技术项目。
- 实操证据较多的项目。
- 内容较少但需要美化的项目。
- 40 页左右长 deck。

2. **失败页自动返工**

不能生成坏页就落盘。

必须：

- 每页生成后立刻保存中间状态。
- 每页单独超时。
- 每页单独 repair。
- 整套任务不能卡死。
- runner 失败必须写 failed/timeout。

3. **质量分不能再只看结构**

必须改成：

- 结构分。
- 图表安全分。
- 视觉审美分。
- PPT 感分。
- 竞赛可讲解性分。
- 证据可信度分。

4. **灰度接入主链**

不能一次性替换全量生产。

建议：

- 只对开启 VNext/experiment flag 的任务启用。
- 只对识别出图表页的页面启用 pure diagram asset pipeline。
- 失败时不回旧模板，而是降级为 MiMo direct 无图表增强，并标记质量风险。

## 6. 下一步开发顺序

### P0-1：补 Pure Asset Packet Contract

目标：让 MiMo 页面稳定消费纯图资产包，并输出 asset mount 与 speaker notes JSON。

要做：

- 修改 MiMo direct page prompt。
- 增加 pure asset packet 输入约束。
- 写 asset mount parser/validator。
- 增加 speaker notes JSON 输出约束。
- 增加 bad fixtures：无 mount、mount 太小、mount 嵌套、mount 含 SVG、图表外白板、asset-frame、讲稿缺失、上屏文字过密、带 production 字段。

验收：

- MiMo 页面能声明 asset mount。
- 系统能识别 mount。
- 系统不设计整页，只替换 mount 内部资产。
- 不生成图表时也能输出明确 asset report。
- 每页都有简版 speaker notes JSON。

### P0-2：接 Fireworks Isolated Adapter

目标：把 Fireworks 作为图表资产生成候选能力标准化。

要做：

- 定义 Fireworks input adapter。
- 定义 SVG output contract。
- 注入 deck palette。
- 注入全局字体变量。
- 产出 SVG + raw metadata。

验收：

- architecture_flow 可生成。
- process_flow 可生成。
- metric_dashboard 暂不强求 Fireworks，先保留实验方向。

### P0-3：生产级 SVG Crop + Fit Audit

目标：图表资产不会带巨大空白，也不会裁切关键元素。

要做：

- 完善 bbox 计算。
- 增加 marker/阴影保护。
- 增加文字可读性检查。
- 增加 group overlap 检查。
- 增加 theme contrast 检查。

验收：

- 箭头不裁切。
- 文字不省略。
- 组之间不重叠。
- 图表不带大白板。

### P0-4：MiMo Layout With Asset Size

目标：MiMo 根据 SVG 实际尺寸设计页面。

要做：

- 把 cropped SVG width/height/aspect_ratio 传给 MiMo。
- 告诉 MiMo 推荐最小展示尺寸。
- 告诉 MiMo 图表应作为主视觉还是辅助视觉。
- 禁止 MiMo 把图表缩成角落装饰。

验收：

- 图表页主体区域充分利用。
- 不出现图表被缩小到不可读。
- 不出现图表外层大白板。
- 不出现图表和文字重叠。
- 页面有明显 PPT 呼吸感，不是网页卡片堆叠。

### P0-5：Asset Mount + Repair Loop

目标：最终落页前发现问题并返工。

要做：

- 将 SVG 挂载到 MiMo asset mount。
- DOM + screenshot audit。
- 图表内部问题回 diagram repair。
- mount/layout/讲稿问题回 MiMo layout repair。
- 每页最多 initial + 1 repair，超过则标记 failed_page。

验收：

- 不把坏页直接落盘。
- 不进入固定模板 fallback。
- repair 原因可追踪。

## 7. 风险与规避

### 风险 1：Fireworks 风格和 PPT 全局风格冲突

规避：

- 图表 SVG 禁止硬编码大面积背景。
- 使用 CSS variables 注入 deck palette。
- 统一字体。
- 图表色彩限制在主色、强调色、辅助色、警示色内。

### 风险 2：MiMo 把纯图又包回网页容器

规避：

- 系统不强行压缩图表。
- mount 太小直接返回 MiMo repair。
- 出现图表外层白板、asset-frame、上传框、网页卡片壳直接 hard fail。
- repair prompt 明确给出 recommended width/height。

### 风险 3：系统又滑回模板

规避：

- 系统禁止生成整页布局。
- 系统禁止移动 mount。
- 系统只处理图表资产。
- 所有 page-level renderer 产物标记为 reference-only，不进入主线。

### 风险 4：图表安全了但不好看

规避：

- 建立专业图表视觉 rubric。
- 引入人工样张对比。
- 每类图表保留多种视觉 grammar。
- 图表 generator prompt 强化“PPT 高级感、专业感、竞赛讲解性”。

### 风险 5：速度慢

规避：

- 先只对图表页启用二阶段。
- 非图表页继续 MiMo direct。
- 图表资产生成和 MiMo 页面生成按页并发。
- 每页独立落盘、独立超时、独立 repair。

## 8. 阶段性验收标准

### 第一阶段：实验可用

- 能生成 3 类图表资产。
- 能 crop。
- 能 fit audit。
- 能注入样张。
- 人眼看比 MiMo 原始图表更稳定。

当前状态：基本达到 60%-70%。

### 第二阶段：真实任务可用

- 能处理真实 MiMo 页面 asset mount。
- 能对 38-40 页 deck 自动识别图表页。
- 图表页不重叠、不溢出、不裁切。
- 图表不被大白板容器包裹，页面空间被设计性利用。
- 页面重点清晰，细节进入 speaker notes JSON。
- 失败页能 repair。
- 能生成完整截图审查包。

当前状态：尚未达到。

### 第三阶段：产品灰度可用

- 真实问卷多项目回归。
- 坏页率低于可接受阈值。
- 视觉审查明显优于 V5/V6 旧链路。
- runner 不超时卡死。
- 能导出 HTML/PPTX。
- 支持开关灰度。

当前状态：还需要主链集成与真实回归。

## 9. 当前完整产品进度判断

如果把“真实 AI PPT 成品可用”拆成 12 段：

1. 产品目标和反模板边界明确。
2. MiMo direct 页面方向确认。
3. 纯图资产和页面设计边界确认。
4. 图表资产实验链路跑通。
5. 图表裁剪和 fit audit 跑通。
6. 真实 MiMo pure asset packet 接入。
7. Fireworks/diagram generator 标准化接入。
8. Asset mount + targeted repair。
9. Cover/Agenda/证据位专项增强。
10. 多项目真实问卷回归。
11. 主链灰度接入。
12. 稳定导出 HTML/PPTX 并可产品化。

当前大致处于：**第 5 / 12 段末尾，第 6 段之前。**

完整产品进度粗估：**约 38%-42%**。

当前分支进度：**Pure Diagram Asset Pipeline 约 60%-65%**。

要看到“真实任务生成效果明显提升”，还差：

- 真实 MiMo pure asset packet 消费。
- Fireworks adapter 标准化。
- SVG crop/fit audit 生产化。
- asset mount repair loop。
- speaker notes JSON 简版链路。
- 至少一套真实问卷完整回归。

要达到“可灰度给用户试用”，还差：

- 封面和目录 director。
- 图片/证据位 schema。
- 多模态视觉审查。
- runner 超时和分阶段落盘。
- HTML/PPTX 导出稳定性。

## 10. 最推荐的下一步

2026-05-07 追加结论：下一步不要再继续把旧 SVG 放进不同版式里，也不要扩更多本地图表模板。

已经做了一个 P0 单页实验：

- 实验脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_creative_brief_visual_grammar_experiment.py`
- 实验 run：`effect_demo_runs/creative_brief_visual_grammar_20260507_195339/`
- 输入：一页架构页 creative brief。
- 候选 visual grammar：`system_map`、`layered_stack`、`evidence_path`。
- 输出：`creative_brief.json`、三张截图、`rubric_scores.json`、`speaker_notes.json`。

实验观察：

- `system_map` 得分最高，说明“系统地图”比普通横向流程条更像架构页主视觉。
- `evidence_path` 更适合实操讲解和评分映射页。
- `layered_stack` 适合技术能力页，但视觉记忆点弱于 system map。
- 真正的质变来自“先选 visual grammar”，不是来自把旧图裁得更干净或放得更大。

最推荐直接做：

**Creative Brief + Visual Grammar Selector 接入实验。**

具体交付：

1. 每页先生成 `creative_brief.json`：页面只讲一个判断、评委 3 秒 takeaway、讲述模式、上屏内容、speaker notes。
2. 根据 page_type 和 creative brief 生成 2-3 个 `visual_grammar` 候选，而不是直接生成横向流程图。
3. 每个候选生成 visual object preview：例如 `system_map`、`layered_stack`、`evidence_path`。
4. 用 rubric 打分：PPT 感、主视觉、信息清晰、内容密度、deck 一致性、anti-web-ui、speaker support。
5. 只把最高分 visual object 交给 MiMo content-region pass。
6. MiMo 只改中间内容区，标题、页脚、页码、背景和 deck shell 全部锁定。
7. 截图审查失败则回到 visual grammar 或 content-region repair，而不是系统套模板。

这一步做完，才能证明这条路线不是“实验里好看”，而是真的能进入 AI PPT 主流程。

## 11. 参考驱动表达页实验结论

2026-05-07 继续追加：参考 Rapidesign 案例时，不能只截取动图/短视频开头帧。应抽取 25%、55%、85% 等中后段帧，观察最终信息如何完整出现。

多帧观察后得到的关键判断：

- 专业 PPT 不是“图表页”，而是“表达页”：封面、章节页、时间线、系统模型、人物/现场、地图、研究成果、指标证据都属于不同表达类型。
- 视觉质感来自场景素材、结构模型、主张文字、数据锚点和讲稿分工的组合，不来自给 SVG 外面换一个容器。
- 页面必须有一个记忆点：场景、主视觉模型、强标题、关键数据、时间轴或对比结构至少命中一个。
- 页面详细不等于上屏文字详细。上屏保留判断和证据锚点，细节进入 speaker notes JSON。
- MiMo 仍然只改中间内容区；标题、页脚、页码、全页背景和 deck shell 必须锁定。

新增 P0 单页实验：

- 脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_reference_driven_expression_page.py`
- 运行目录：`effect_demo_runs/reference_driven_expression_20260507_201341/`
- 截图：`effect_demo_runs/reference_driven_expression_20260507_201341/screenshots/reference_driven_expression.png`
- 讲稿：`effect_demo_runs/reference_driven_expression_20260507_201341/speaker_notes.json`
- 页面表达 brief：`effect_demo_runs/reference_driven_expression_20260507_201341/page_expression_brief.json`
- 使用素材：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/reference_assets/smart_agriculture_editorial_bg.png`

实验观察：

- 只去掉 SVG 背景不够，必须给页面一个场景语境或主视觉组织方式。
- “场景图 + 结构模型 + 三个证据锚点 + 简短讲稿 JSON”比“中间白板 + 右侧说明卡”更接近专业 PPT。
- 这仍然不是最终方案，因为当前只是单页手工实验；产品化时必须让系统先产生 `page_expression_brief`，再生成/选择 visual object，再交给 MiMo content-region pass。

推荐把下一阶段名称从 `Creative Brief + Visual Grammar Selector` 升级为：

**Page Expression Director + Visual Asset Planner + MiMo Content Region Pass。**

主流程建议：

1. `page_expression_brief.json`：每页先判断表达类型、观众 takeaway、页面记忆点、上屏内容和讲稿内容。
2. `visual_asset_plan.json`：判断是否需要场景图、现场照片、地图、人物、纹理、品牌图形、系统模型或指标证据图。
3. `visual_object_candidates`：每页生成 2-3 个不同表达候选，不再默认横向流程图。
4. `rubric_scores.json`：按 PPT 感、主视觉、内容取舍、讲稿支撑、统一性、反网页 UI、可讲性评分。
5. `mimo_content_region_pass`：只把最高分候选交给 MiMo，让 MiMo 调中间区域布局。
6. `content_region_validator`：硬拦截改标题、改页脚、改全页背景、文字过多、空白无意图、卡片套卡片、asset-frame。
7. `speaker_notes.json`：先返回简版 JSON，后续再规划如何进入 PPT 备注或讲稿系统。

这条路线的本质不是套本地模板，而是让 AI 在每页生成前先做“表达导演”判断：这一页该用什么形式让观众记住，而不是把所有内容平均塞进页面。

## 12. 内容仍未达到锐普级别的原因与补救

2026-05-07 最新判断：上一轮 `reference_driven_expression` 仍然达不到锐普级别，核心原因不是配色或 SVG 外框，而是内容表达深度还停留在“清楚说明”层面，没有进入“作品叙事”层面。

锐普案例的内容特征：

- 页标题常常是观点或命题，不只是章节名。
- 页面会选择一种内容体裁：使命愿景、发展时间轴、研究洞察、地图叙事、人物历史、成果证明、行业定位。
- 每页有一个 proof object：照片、地图、时间轴、人物、数据环、事件链、模型、奖项或第三方背书。
- 文字不是少就高级，而是被分层：主张、标签、证据、注释、讲稿各自承担不同任务。
- 动效不是装饰，它让信息按叙事顺序出现；最终帧只是故事的完成状态。

新增内容级实验：

- 脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_rapidesign_level_content_experiment.py`
- 运行目录：`effect_demo_runs/rapidesign_level_content_20260507_201846/`
- Contact sheet：`effect_demo_runs/rapidesign_level_content_20260507_201846/screenshots/rapidesign_level_content_contact_sheet.png`
- 内容 brief：`effect_demo_runs/rapidesign_level_content_20260507_201846/content_expression_brief.json`
- 讲稿：`effect_demo_runs/rapidesign_level_content_20260507_201846/speaker_notes.json`

三页实验的表达体裁：

1. `manifesto_scene`：先提出“数据不是屏幕，而是现场证据”。
2. `research_insight_orbit`：把平台模块改写成“现场可信度”的证据闭环。
3. `acceptance_storyline`：用一次设备异常事件证明平台可验收，而不是罗列功能。

结论：

- 比前一版更接近专业 PPT，但仍不能直接宣称达到锐普级。
- 差距主要在真实素材和真实事实密度：锐普页面往往有学校历史、地图、人物、Logo、奖项、年份、第三方媒体、真实照片等强证据。
- 如果源材料只有抽象功能点，AI 必须先提出 `content_gap`，不能靠版式把内容空洞包装成高级。

因此产品链路必须增加一个硬前置：

**Content Director Pass。**

输出字段建议：

- `claim`: 本页主张，必须是判断句。
- `proof_object`: 用什么证明主张，例如系统模型、事件链、数据环、地图、时间线、人物/现场、对比结构、证据矩阵。
- `source_facts`: 上屏或讲稿可引用的事实。
- `visual_asset_need`: 需要哪些照片、地图、人物、设备、截图、Logo、纹理或品牌图形。
- `screen_text_budget`: 上屏文字预算。
- `speaker_notes`: 讲稿承载的细节。
- `content_gap`: 缺什么事实或素材才可能达到作品级。

只有 `Content Director Pass` 通过后，才进入 `Page Expression Director` 和 `MiMo Content Region Pass`。否则 MiMo 只能把普通内容排得更整齐，无法生成锐普级内容。

## 13. 视觉主角规则

2026-05-07 对比锐普参考和本地生成页后，继续修正判断：锐普级页面不只是有素材、有版式，而是每页都有一个明确的视觉主角。观众缩略图扫一眼就知道该看什么。

新增实验：

- 脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_focal_point_design_experiment.py`
- 运行目录：`effect_demo_runs/focal_point_design_20260507_202652/`
- Contact sheet：`effect_demo_runs/focal_point_design_20260507_202652/screenshots/focal_point_contact_sheet.png`
- Brief：`effect_demo_runs/focal_point_design_20260507_202652/focal_point_brief.json`

实验规则：

- 每页只能有一个第一视觉重点。
- 第一视觉重点必须在 contact sheet 缩略图里仍然可识别。
- 其它信息只能证明、解释或承托主角，不能和主角抢注意力。
- 大数字、地图、人物、照片、时间轴、事件环、关键截图、品牌口号都可以成为主角。
- 如果页面没有视觉主角，即使排版干净，也只能算说明页，不是作品页。

三页实验结果：

1. `98.6%` 作为现场可信度主角，比上一版更明确。
2. `1次异常处理链路` 作为事件主角，但视觉压场仍偏弱，说明事件页还需要更强的图形或真实截图支撑。
3. `42s` 作为告警响应主角，缩略图识别度明显高于前一版。

因此 `Content Director Pass` 必须新增字段：

- `visual_protagonist`: 本页第一视觉重点。
- `thumbnail_test`: 在 contact sheet 尺寸下是否仍能一眼看出重点。
- `supporting_hierarchy`: 哪些元素必须退后，避免抢主角。

产品级结论：

MiMo prompt 不能只要求“设计感”“呼吸感”“高级感”。这些词太虚。必须变成可验证规则：

- 本页第一眼看哪里？
- 为什么看那里？
- 这个重点证明什么主张？
- 其它信息是否都在服务它？
- 缩略图里还能不能看出来？

这比继续要求 MiMo “更像大师”更可靠。

## 14. 比赛页真实性规则

2026-05-07 再次修正：视觉主角不能靠胡编数字获得冲击力。比赛页面尤其不能把没有来源的百分比、秒数、排名、金额、年份、认证或业务成效写成事实。

新增实验：

- 脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_realistic_scenario_focal_experiment.py`
- 运行目录：`effect_demo_runs/realistic_scenario_focal_20260507_203657/`
- Contact sheet：`effect_demo_runs/realistic_scenario_focal_20260507_203657/screenshots/realistic_scenario_contact_sheet.png`
- Brief：`effect_demo_runs/realistic_scenario_focal_20260507_203657/realistic_scenario_brief.json`

实验改法：

- 删除无来源的 `98.6%`、`42s` 等效果数字。
- 改成“土壤墒情传感器异常告警”的现场模拟场景。
- 页面主角从虚构指标改为真实可讲的演示对象：异常告警、校准记录、评分点覆盖。
- 明确标注 `现场模拟`、`演示证据表`、`真实项目接入后替换为后台导出的记录`。

新增硬规则：

- 数字、年份、金额、排名、认证、获奖、第三方机构名称必须来自输入事实。
- 没有来源时，页面可以做“场景模拟”，但必须诚实标注，不能包装成真实成效。
- 如果需要强视觉主角，优先选择场景、事件、记录、截图、地图、结构或评分点，不要编大数字。
- `Content Director Pass` 必须输出 `source_status` 和 `unsupported_claims_removed`。

推荐字段：

```json
{
  "visual_protagonist": "本页第一视觉重点",
  "source_status": "verified | provided_by_user | simulation | missing_source",
  "unsupported_claims_removed": true,
  "claim": "本页主张",
  "proof_object": "证明对象",
  "content_gap": "缺少哪些事实或素材",
  "speaker_notes": {}
}
```

这条规则优先级高于“设计感”。宁可页面少一个震撼数字，也不能在比赛页上制造不可信内容。

## 15. 项目叙事规则：不要把台下话写上屏

2026-05-07 继续修正：比赛专用 PPT 是讲项目，不是讲评分策略。页面不能出现“评分点覆盖、评委追问、比赛现场、拿分逻辑、讲稿 JSON、页面主角”等内部话术。这类内容可以影响生成策略，但不能出现在成品页可见文案中。

新增实验：

- 脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_project_story_focal_experiment.py`
- 运行目录：`effect_demo_runs/project_story_focal_20260507_204250/`
- Contact sheet：`effect_demo_runs/project_story_focal_20260507_204250/screenshots/project_story_contact_sheet.png`
- Brief：`effect_demo_runs/project_story_focal_20260507_204250/project_story_brief.json`

改法：

- 删除“评分点、评委、比赛现场、答辩追问”等元话术。
- 删除“这一页的主角、页面只保留”等生成提示式文案。
- 保留真实场景模拟，但改成项目叙事：
  - 棚内土壤偏干预警。
  - 土壤墒情传感器校准记录。
  - 从预警到灌溉建议的农事闭环。

新增硬规则：

- `Content Director Pass` 可以考虑比赛场景和评分关注点，但 `visible_text` 必须只讲项目本身。
- 可见页面禁止出现内部策略词：评分点、评委、答辩追问、比赛现场、打分逻辑、页面主角、缩略图、讲稿 JSON、生成规则。
- 如果需要回应比赛关注点，应用项目语言表达：数据可信、现场闭环、处理留痕、部署价值、业务成效。
- 讲稿里可以解释页面如何支撑答辩，但上屏不能把评委当成需要被提醒的人。

推荐验证项：

```json
{
  "visible_text_is_project_facing": true,
  "meta_language_removed": true,
  "forbidden_visible_terms": ["评分点", "评委", "答辩追问", "比赛现场", "打分逻辑", "页面主角", "缩略图", "讲稿 JSON"]
}
```

## 16. 标题、空白和图表碰撞规则

2026-05-07 继续修正：项目叙事方向正确后，还必须解决页面基本设计质量问题。

最新实验：

- 脚本：`experiments/mimo_direct_diagram_audit/two_step_asset_flow/run_project_story_focal_experiment.py`
- 运行目录：`effect_demo_runs/project_story_focal_20260507_204859/`
- Contact sheet：`effect_demo_runs/project_story_focal_20260507_204859/screenshots/project_story_contact_sheet.png`

修正点：

- 第 1 页保留明确标题区，并补充“地块状态 -> 阈值判断 -> 农事建议 -> 处理留痕”的中间主图表。
- 第 2 页补充“设备核验 -> 现场参照 -> 复核沉淀”的证据层，减少左侧空白。
- 第 3 页把流程节点改成卡片，线条下移，避免连线穿过文字。

新增硬规则：

- 标题区必须清楚可见，不能因为中间区重构导致页面像无标题散页。
- 中间区域不能出现没有设计用途的大空白。
- 图表必须作为完整视觉对象设计，节点、连线、标注、说明文字不得互相重叠。
- 线条不能穿过文字，说明文字不能压住图形，节点之间要有稳定间距。

推荐字段：

```json
{
  "title_region_preserved": true,
  "negative_space_intent": "说明留白用途",
  "collision_check": "nodes/lines/labels separated",
  "content_area_density": "balanced"
}
```
