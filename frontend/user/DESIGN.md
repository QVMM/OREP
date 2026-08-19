# 竞赛大脑 · 用户端设计规则

> **标杆页面**：首页（`StudentHome`）、评分总结系列（结果 / 待办 / 依据 / 多维评委）  
> **视觉标杆**：浅色工作台 + 轻灰阶层级；**对比度目标 WCAG AA（正文 ≥4.5:1）**  
> **品牌**：Logo `#e84a1c`；主按钮 `#c43a12`（白字 AA）  
> **实现入口**：`src/styles/workspace-tokens.css` + `workspace-components.css`

---

## 0. 规范依据与本地化结论

本规范不是照搬单一品牌，而是基于公开生产级规范提取共同原则，再结合竞赛大脑的桌面工作台场景和橙色品牌体系定值。

| 公开依据 | 采用的共同原则 | 本项目落地 |
|---|---|---|
| [Apple Human Interface Guidelines · Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) | 控件要有舒适的点击区域，控件之间要有足够间距 | 主要按钮 40px；触控密集场景扩大到 44px 有效区域；图标按钮 36×36px |
| [Apple HIG · Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | 对齐、分组、留白和响应式稳定性优先 | 统一 40px 页面边距，4px 间距阶梯，多列随视口逐级降列 |
| [Carbon · Button](https://carbondesignsystem.com/components/button/style/) | 32/40/48px 是成熟产品常用按钮尺寸，40px 是标准生产型尺寸 | 本项目收敛为 34px Compact、40px Default，不引入过多尺寸 |
| [Carbon · Text input](https://carbondesignsystem.com/components/text-input/usage/) | 同页表单高度保持一致；标签常驻；错误包含描边、图标和文字 | 默认输入 44px、紧凑输入 36px，纯白底，禁止 placeholder 代替标签 |
| [WCAG 2.2 · Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum) | 指针目标至少 24×24 CSS px，密集小目标需提供间距 | 所有独立按钮均高于 24px；相邻紧凑按钮至少留 8px |
| [WCAG 2.2 · Focus Appearance](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance) | 键盘焦点必须具有足够面积和可见对比 | 使用 2px 实线橙色 outline + 2px offset，不用浅色阴影代替焦点 |
| [WCAG 2.2 · Contrast](https://www.w3.org/TR/WCAG22/#contrast-minimum) | 普通文本至少 4.5:1，大文本与非文本关键边界至少 3:1 | 辅助文字不得继续淡化；按钮文字、输入边界和状态图标纳入对比度检查 |

### 0.1 适用优先级

1. 产品逻辑和真实数据正确；
2. 无障碍和可操作性通过；
3. 页面结构忠实于已确认原型；
4. 组件遵守本规范；
5. 最后才允许页面级视觉微调。

当页面局部样式与本规范冲突时，以本规范为准；沉浸式会议室和 PPT 画布只能改变表面颜色，不能改变控件尺寸、状态和交互逻辑。

---

## 1. 产品气质

| 维度 | 规则 |
|------|------|
| 气质 | 冷静工作台 + 评分大脑；**简约、方便、好用、美观**；不赛博、不厚重新拟态 |
| 表面 | 主区纯白；侧栏 `#f5f5f5`；弱底 `#f5f7fa`；卡片白 + `#e5e6ea` 线 + 轻阴影 |
| 信息 | 主判断大、扫读中、详情下；指示灯辅助状态，不装饰滥用 |
| 首页 | 主区默认 **分屏舞台**；右上角可切 **拼图布局**（`orep-home-layout`） |
| 壳 | `WorkspaceShell`；无毛玻璃、无页面渐变底 |
| 兼容 | 旧页面可暂时保留 `workspace-card`；评分总结优先开放排版 |

### 1.1 卡片与阴影（硬规则 · 来自 biji 实机 CSS）

实机片段：

```css
.editor-wrapper.mini {
  background: #fff;
  border: 1px solid #e2e4ea;
  border-radius: 14px;
}
/* 全局默认 --tw-shadow: 0 0（内容层默认无投影） */
```

| 层级 | 边框 | 阴影 | 说明 |
|------|------|------|------|
| 页面画布 | 无 | 无 | 纯白 `#ffffff` |
| 侧栏/会话列表底 | 无 | 无 | `#f5f5f5` 分区 |
| 编辑器/内容卡 | `1px #e2e4ea` | **none** | 与 `.editor-wrapper.mini` 一致 |
| 交互 hover | `#d5d8e0` | **none** | 只加深描边，不抬起 |
| 下拉/弹层 | 可选 | `--ds-shadow-float` | **仅浮层**可有阴影 |

---

## 2. 颜色

> 下列值对齐得到大脑 `home` 静态 CSS 高频色与 `/note` 截图像素抽样。

### 2.1 画布与表面

| Token | 值 | 用途 |
|-------|-----|------|
| `--ds-canvas` | `#ffffff` | 主内容区纯白画布 |
| `--ds-canvas-deep` | `#ffffff` | 同画布，禁止再铺渐变 |
| `--ds-canvas-background` | `none` | 无渐变背景 |
| `--ds-sidebar-bg` | `#f5f5f5` | 左侧导航浅灰分区 |
| `--ds-soft` | `#f5f7fa` | chip / 弱底 / meta 条 |
| `--ds-soft-2` | `#f2f2f3` | 次级浅底 |
| `--ds-surface` / `--ds-card-bg` | `#ffffff` | 卡片与输入纯白 |
| `--ds-card-border` | `#e2e4ea` | 卡片/编辑器描边（editor-wrapper） |
| `--ds-card-radius` | `14px` | 内容框圆角 |
| `--ds-card-shadow` | `none` | 内容层默认无投影 |
| `--ds-border` | `#e5e7eb` | 全局兜底线（Tailwind 默认） |

### 2.2 文字

| Token | 值 | 用途 |
|-------|-----|------|
| `--ds-ink` | `#1d2129` | 标题、主数字、强调 |
| `--ds-ink-2` | `#292d34` | 次级标题、列表主文 |
| `--ds-muted` | `#8a8f99` | 正文说明、lead |
| `--ds-faint` | `#adb3be` | 标签、辅助、时间 |

### 2.3 线

| Token | 值 | 用途 |
|-------|-----|------|
| `--ds-line` | `#e5e6ea` | 默认分隔 / 卡片线 |
| `--ds-line-strong` | `#dadce2` | 主区块分隔 / hover 线 |

### 2.4 品牌与状态

品牌展示色与行动色统一为主题橙。Logo、主按钮默认均使用 Orange 500（`#E84A1C`）；hover 用 600、active 用 700，与首页主按钮及高保真原型一致。

| Token | 值 | 用途 |
|-------|-----|------|
| `--ds-orange-50` | `#fff7f2` | 极浅行动底 |
| `--ds-orange-100` | `#fee9df` | 选中、标签弱底 |
| `--ds-orange-500` / `--ds-orange` | `#e84a1c` | Logo、装饰（勿作小字色） |
| `--ds-orange-900` / `--ds-orange-action` | `#9a3412` | 链接字、主按钮底（白字 ≈7.3:1 AAA） |
| `--ds-orange-deep` | `#7c2d12` | 主按钮 hover / active |
| `--ds-orange-900` | `#85270d` | 极深强调，谨慎使用 |
| `--ds-violet` | `#766af6` | AI/能力强调（对齐得到大脑品牌紫） |
| `--ds-violet-soft` | `#f0effe` | AI 弱底、能力 chip |
| `--ds-green` | `#0f9f6e` | 成功、在线、正向差 |
| `--ds-blue` | `#5182ff` | 链接/信息（对齐 biji 蓝） |
| `--ds-amber` | `#d98200` | 中性提醒（可选） |
| `--ds-red` | `#d83a45` | 错误、危险 |

主按钮使用暖白字 `#fffaf7` 时，默认、hover、active 对比度依次约为 `4.68:1`、`5.27:1`、`6.18:1`。三种状态全部达到普通文字 `4.5:1` 基线，并形成清楚但不过度跳变的明度阶梯。

### 2.5 指示灯（6px）

| 类 | 色 | 语义 |
|----|-----|------|
| `led-ok` | green | 正常 / 已就绪 |
| `led-warn` | orange | 需关注 |
| `led-idle` | `#c5c9d1` | 待命 / 中性 |
| `led-pulse` | green + 微脉冲 | 仅「大脑引擎在线」等一处 |

---

## 3. 字体

### 3.1 字体族

```text
正文/UI：
"PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", "Noto Sans SC",
-apple-system, BlinkMacSystemFont, system-ui, sans-serif

数字/分数：
"DIN Alternate", "SF Pro Text", "Helvetica Neue", Arial, sans-serif
```

- 禁止正文默认斜体；`em`/`i` 在产品 UI 中 `font-style: normal`
- 数字用 `--ds-font-num` + `tabular-nums`（分数、进度）

### 3.2 字号阶梯（桌面主区）

| 阶 | Token | 大小 | 用途 |
|----|-------|------|------|
| Display | `--ds-text-display` | `clamp(56px, 7vw, 80px)` | 本场得分等主数字 |
| H1 | `--ds-text-h1` | `clamp(22px, 1.8vw, 28px)` | 页面问候、主标题 |
| H2 | `--ds-text-h2` | `clamp(20px, 2vw, 26px)` | 区块主判断标题 |
| H3 | `--ds-text-h3` | `16px` | 栏目标题 |
| Metric | `--ds-text-metric` | `46px` | 首页倒计时、卡片主指标 |
| Body | `--ds-text-body` | `15px` | 主说明、lead |
| Body-sm | `--ds-text-body-sm` | `14px` | 列表、右栏正文 |
| Caption | `--ds-text-caption` | `13px` | 次要说明 |
| Label | `--ds-text-label` | `12px` | 区标签、指标名、图例 |
| Micro | `--ds-text-micro` | `11px` | 极少用：角标、极次要 |

### 3.3 字重

| 用途 | 字重 |
|------|------|
| 主标题 / 主数字 | 700 |
| 按钮 / 强调 | 700 |
| 正文 | 500 |
| 标签 / 辅助 | 600–700 |

### 3.4 行高

| 用途 | 行高 |
|------|------|
| 标题 | 1.2–1.32 |
| 正文 | 1.55–1.65 |
| 列表 | 1.45–1.5 |

---

## 4. 间距与版心

### 4.1 4px 基础间距阶梯

| Token | 值 | 常见用途 |
|---|---:|---|
| `--ds-space-1` | 4px | 图标内部微调、紧凑标签 |
| `--ds-space-2` | 8px | 按钮图文、相邻紧凑控件 |
| `--ds-space-3` | 12px | 字段标签与输入、紧凑列表 |
| `--ds-space-4` | 16px | 常规组件内部间距 |
| `--ds-space-5` | 20px | 卡片间距、页头到首区块 |
| `--ds-space-6` | 24px | 卡片内边距、区块间距 |
| `--ds-space-8` | 32px | 大区块内部留白 |
| `--ds-space-10` | 40px | 桌面页面四边距 |

禁止新增不属于阶梯的 7px、11px、19px、23px 等孤立间距；确有视觉校正需求时，必须在组件说明中写明原因。

| Token | 值 | 用途 |
|-------|-----|------|
| `--ds-page-max` | `1280px` | 阅读型、编辑型窄版内容的可选最大宽度；首页和工作台根容器禁用 |
| `--ds-page-margin-x` | `40px` | 桌面端主内容区左右边距，由 `.workspace-main` 唯一提供 |
| `--ds-page-margin-y` | `40px` | 桌面端主内容区上下边距，由 `.workspace-main` 唯一提供 |
| `--ds-page-content-inset-top` | `0px` | 业务页根容器顶部附加间距；必须为 0 |
| `--ds-gutter` | `clamp(24px, 3vw, 40px)` | 栏间距 |
| `--ds-section-gap` | `20–28px` | 大区块间距 |
| `--ds-stack-sm` | `8px` | 紧凑堆叠 |
| `--ds-stack-md` | `12–16px` | 常规堆叠 |

**规则**

1. 主内容区只套 **一层** 水平 padding，避免 `workspace-page` + 内层双重 gutter。  
2. 首页和工作台根内容必须 `width: 100%; max-width: none; margin: 0`，完整使用主区宽度；仅阅读型、编辑型窄版内容可在内部使用 `--ds-page-max`。  
3. 侧栏宽度：`clamp(216px, 13vw, 260px)`（现有 shell）。
4. 桌面端页面四边统一由 `.workspace-main` 提供 **40px** 外边距，首页是唯一基准。
5. 页面根容器必须 `padding-top: var(--ds-page-content-inset-top)`，不得再叠加 `margin-top` 或第二层顶部 padding。
6. 页面首个可见内容（标题、项目上下文、面包屑或首张主卡）必须从 `.workspace-main` 顶部 40px 基线开始；后续间距属于组件内部节奏。
7. 禁止使用“根容器最大宽度 + 居中”再次放大页面左右留白；在桌面宽屏下，顶部、左侧、右侧的可见外边距都必须保持 40px。
8. `.student-page`、`.workspace-page` 等页面根容器必须全宽，不得设置 `max-width` 或 `margin: 0 auto`；最大宽度只允许用于阅读正文、编辑器等页面内部内容。

---

## 5. 圆角与阴影

| Token | 值 | 用途 |
|-------|-----|------|
| `--ds-radius-pill` | `999px` | 主/次按钮、搜索 |
| `--ds-radius-md` | `12px` | 输入、轻面板 |
| `--ds-radius-lg` | `16px` | 需要容器时 |
| `--ds-radius-xl` | `20px` | 场景带等特例 |
| `--ds-shadow-none` | 默认 | 开放排版默认无阴影 |
| `--ds-shadow-soft` | 极轻 | 仅浮层/下拉 |

**规则**：

- 按钮、输入框、标签默认无投影，保持扁平。
- 常规内容卡片允许使用 `--ds-card-shadow` 的双层极轻阴影，不能页面自行发明更重阴影。
- 下拉、弹窗等真正浮层使用 `--ds-shadow-soft`；普通卡片不得与浮层使用同一阴影强度。
- hover 不通过上浮和放大制造反馈，只调整描边或背景。

### 5.1 最小实现入口

- Vue 页面使用 `components/base/BaseCard.vue`；默认消费 `--ds-card-bg / --ds-card-border / --ds-card-shadow`。
- 学生流程兼容页使用 `.student-card`，视觉参数必须与 `BaseCard` 同源。
- 页面只能控制卡片的业务布局和内容间距，不得重新声明通用圆角、投影或 hover 位移。
- `hoverable` 只增强描边，不上浮；`elevated` 仅用于真正需要层级的浮层式内容。

---

## 6. 按钮

### 6.1 尺寸

| 规格 | 高度 | 水平内边距 | 字号 | 用途 |
|---|---:|---:|---:|---|
| Default | `40px` | `18px` | `14px / 700` | 页面主要操作、表单提交、英雄区 CTA |
| Compact | `36px` | `14px` | `13px / 700` | 卡片标题操作、列表行操作、筛选按钮 |
| Icon | `36 × 36px` | `0` | — | 仅图标操作 |

- 图标与文字间距固定为 `8px`。
- 相邻按钮间距默认 `8px`，主次按钮组可使用 `12px`。
- 所有按钮使用 `box-sizing: border-box`、单行文本和 `--ds-radius-pill`。
- 不允许页面用文字长度反向决定高度，也不允许用额外 `margin` 修补按钮内部间距。

### 6.2 类型

| 类型 | 样式 |
|------|------|
| **Primary** | 背景 `--ds-btn-primary-bg`，暖白字，无投影；hover / active 使用行动色色阶 |
| **Secondary** | 暖白底 + `--ds-btn-secondary-border`，字 `--ds-ink` |
| **Ghost** | 透明底，无描边，字 `--ds-muted`；hover 只加极浅中性底 |
| **Text** | 无容器，橙色或中性色文字；只能用于低优先级动作 |
| **Danger** | 默认白底红字红描边；只有最终危险确认才允许红色实底 |
| **Disabled** | 明确使用禁用背景、文字和描边 Token，`cursor: not-allowed`；不使用整体透明度造成底色漂移 |

### 6.3 状态

状态优先级固定为：`disabled > loading > active > focus-visible > hover > default`。同一个控件同时命中多个状态时，必须按此顺序覆盖。

| 状态 | Primary | Secondary / Compact | Ghost / Text | 行为 |
|---|---|---|---|---|
| Default | 行动橙实底，文字对比度 ≥ 4.5:1 | 暖白底细描边 | 透明底 | 可点击 |
| Hover | 加深一级至 `--ds-btn-primary-bg-hover`，文字仍 ≥ 4.5:1 | 极浅中性底、描边明确增强 | 极浅中性底 | 不上浮、不放大 |
| Active | `--ds-btn-primary-bg-active` | `--ds-btn-secondary-bg-active` | 中性底再加深一级 | 不改变尺寸和位置 |
| Focus visible | 2px 橙色 outline + 2px offset + 弱 ring | 同左 | 同左 | 只在键盘聚焦时显示 |
| Loading | 保持原尺寸、原文案宽度，前置 14px spinner | 同左 | 同左 | `aria-busy="true"`，禁止重复触发 |
| Disabled | 禁用背景、文字、描边三项 Token | 同左 | 同左 | 使用原生 `disabled` 或 `aria-disabled="true"` |
| Selected / Pressed | 橙色弱底 + 橙色描边 + 深橙文字 | 同左 | 同左 | 用于筛选、切换按钮，配合 `aria-pressed="true"` |

- hover、active、loading、disabled 均不得出现位移、缩放或重阴影。
- loading 必须保留按钮原宽度；spinner 不能代替可读按钮文本。
- 危险按钮默认使用白底红字红描边；只有最终不可逆确认动作才允许红色实底。
- 首页是按钮视觉基准；其他页面只能消费 `BaseButton`、`.ds-button`、`student-*`、`workspace-*` 或统一后的 Element Plus 按钮，不得另造相近规格。
- Element Plus 的 `plain`、`text`、`link` 必须保留各自语义，禁止被 `.el-button--primary` 统一改成实底按钮。
- Logo 与侧栏品牌块继续使用 `--ds-orange`；任何含 13–15px 反白文字的实底行动控件必须使用 `--ds-orange-action` 或更深色阶。

### 6.4 最小实现入口

| 场景 | 唯一入口 |
|---|---|
| Vue 基础组件 | `components/base/BaseButton.vue` |
| 新业务页面 | `.ds-button` + `--primary / --secondary / --ghost / --danger / --compact / --icon` |
| 学生流程兼容 | `.student-primary-btn / .student-secondary-btn / .student-quiet-btn` |
| 工作台兼容 | `.workspace-primary-btn / .workspace-secondary-btn / .workspace-ghost-btn` |
| Element Plus | 由 `styles/control-primitives.css` 统一适配，页面不得覆盖内部状态 |

状态样式集中在 `workspace-tokens.css` 与 `control-primitives.css`。业务页面只负责选择语义类型、大小和禁用/加载状态，不得重新声明背景色、圆角、内边距、焦点环和动画。

## 6A. 输入框

| 属性 | 规范 |
|---|---|
| 背景 | `--ds-input-bg`，视觉为白色的暖白底；禁止蓝灰填充底 |
| 高度 | 默认 `44px`；紧凑表格可使用 `36px` |
| 圆角 | `--ds-input-radius`，即 `12px` |
| 描边 | `1px solid --ds-input-border` |
| 内边距 | 水平 `14px`；有前后图标时保持文字起点一致 |
| 聚焦 | 2px 橙色可见 outline 或等效描边 + 弱 ring，禁止蓝色大面积填充高亮 |
| 错误 | 红色描边 + 错误图标 + 输入框下方文字说明，不能只靠红色 |
| 禁用 | 浅灰背景 + 禁用文字 + 禁用描边，保留内容可读性 |
| 只读 | 中性浅底，允许选择复制，光标保持默认 |

- 每个输入框必须有持续可见的标签；placeholder 只能给示例，不能替代标签。
- 同一表单中同类输入框必须等高并沿网格对齐。
- Helper text 默认持续显示；出现错误时由错误说明替换，避免两段提示争抢注意力。
- 密码框的可见性按钮必须保留至少 36×36px 点击区域，并提供可读标签。
- 原生输入、下拉和多行输入分别使用 `.ds-input`、`.ds-select`、`.ds-textarea`；Vue 封装输入使用 `BaseInput.vue`。页面不得重复实现这三类控件的描边、圆角、聚焦和禁用状态。

路演中心的会议号、入会密码，以及 PPT 模板、生成、编辑页面的表单控件，必须迁移到本规范。PPT 编辑画布可以保持沉浸式背景，但工具栏、表单、按钮与弹窗仍须遵守统一控件规范。

## 6B. 标签、状态与选择控件

| 类型 | 背景 | 文字 | 使用场景 |
|---|---|---|---|
| Neutral | `--ds-status-neutral-bg` | `--ds-status-neutral-fg` | 未开始、普通信息 |
| Info | `--ds-status-info-bg` | `--ds-status-info-fg` | 处理中、系统信息 |
| Success | `--ds-status-success-bg` | `--ds-status-success-fg` | 已完成、在线、通过 |
| Warning | `--ds-status-warning-bg` | `--ds-status-warning-fg` | 待处理、临近截止 |
| Danger | `--ds-status-danger-bg` | `--ds-status-danger-fg` | 失败、阻塞、严重问题 |

- 标签默认高度 `24px`，pill 圆角，字号 `12px / 600`；标签不是按钮，不得添加 hover。
- 可点击筛选必须使用按钮语义和 `aria-pressed`，不能把静态标签直接做成点击控件。
- Checkbox、Radio、Switch 的选中态统一使用品牌橙；禁用态必须同时改变控件和标签文字。
- 成功、警告、危险等状态不得只靠颜色，必须同时出现文字或图标。

---

## 7. 链接与可点行

- 行动链接：橙色、字重 600–700  
- 次要：「全部 →」用 faint，hover 变橙  
- 列表行 hover：主文案变橙，不整行铺底（开放排版）

---

## 8. 布局模式

### 8.1 开放主舞台（首页 / 评分总结）

```
[ 上下文一行 ]
[ 主判断区 | 右栏扫读 ]   ← 细竖线分隔
[ 能力/工具横带 ]
[ 下半多栏概览 ]
```

### 8.2 通用内容页

```
[ 页标题 H1 + 可选操作 ]
[ 可选说明 body ]
[ 内容：线分隔或轻面板，忌嵌套三层卡片 ]
```

---

## 9. 文案语气（产品规则）

1. 称「**大脑引擎**」，不说空泛「AI 很智能」。  
2. 情绪价值用**人话**，忌鸡汤/模板感。  
3. 首页下半、动态、任务：**类型级描述**，不泄密、不展开敏感详情。  
4. 缺数据：**隐藏或「—」**，禁止编造分数/均分。

---

## 10. 无障碍与质感

- 状态色不单靠颜色：配合文字（待提升 / 在线）。  
- `font-synthesis: none`，中文 UI 不伪斜体。  
- 动效：`180ms` 级；指示灯脉冲仅限关键在线态。
- 普通文本与背景对比度至少 4.5:1；大文本、控件边界和状态图形至少 3:1。
- 独立点击目标不得小于 24×24px；项目默认使用 34px 以上可见按钮，并为相邻控件保留至少 8px 间距。
- 键盘焦点不能被顶部栏、弹窗或滚动容器遮挡；弹窗打开时，背景控件不得继续接受焦点。
- 页面在 200% 文本缩放下不得丢失按钮、字段标签和核心操作。

### 10.1 图标体系

- 一级侧边导航统一使用 **面型图标**，24px 画布、同一视觉重量；选中态橙底白图标。
- 首页及工作台卡片标题统一使用 **线型图标**：34×34px 弱语义色容器、20×20px 图形、1.8px 描边、10px 容器圆角，采用圆角端点和圆角连接。
- 图标尺寸固定分为三档：16px 用于按钮和行内辅助信息，20px 用于卡片标题，24px 用于一级侧边导航；业务页面不得用 transform 或孤立像素值缩放图标。
- 首页模块图标可按训练、学习、路演、评分、节奏、任务使用不同弱语义色；按钮与主要行动仍只使用品牌橙。
- 模块图标使用项目统一的 `WorkspaceModuleIcon`；Element Plus 图标只用于日历、箭头、提醒等通用操作语义，不能替代模块身份图标。
- 禁止在同一导航层级混用线型、面型、文字首字母和表情符号。

### 10.2 页面背景

- 非沉浸式页面不得自行铺设页面级背景，由 `.workspace-main` 唯一提供 `--ds-canvas-background`。
- 页面根容器必须透明；白色只用于卡片、输入框和浮层。
- 会中路演、讲稿编辑器和 PPT 编辑器可保留专用沉浸式画布。

---

## 11. 标杆页改动纪律

| 页面 | 纪律 |
|------|------|
| 首页 Dashboard | **小改**：token 引用、边距/字号与规则对齐；不改信息架构 |
| 评分总结（result/todos/why/jury…） | **小改**：token 对齐；结构与已确认原型不动 |
| 其余用户端 | 按本规则收敛颜色、按钮、字号、页边距 |

### 11.1 控件迁移纪律

1. 按 `docs/plans/2026-07-21-student-ui-control-unification.md` 从小页面到复杂工作台逐页迁移。
2. 每次只迁移一个页面或一组共享同一组件的小页面，不允许用高优先级全局选择器一次覆盖全部旧页面。
3. 当前批次页面必须完成默认、hover、focus、disabled、loading、弹窗状态检查后才能进入下一批。
4. 任何页面级覆盖若与本规范冲突，必须删除冲突来源，不能继续叠加 `!important`。

---

## 12. 实现检查清单

- [ ] 颜色是否全部来自 `--ds-*` / `--workspace-*` 映射，无随手 hex  
- [ ] 主按钮是否 solid 橙、40px、pill  
- [ ] 紧凑按钮是否 34px、图标按钮是否 36×36px  
- [ ] 次按钮是否白底细描边，所有按钮是否无位移/重阴影  
- [ ] 输入框是否白底、44px、12px 圆角并使用橙色 focus ring  
- [ ] 输入框是否有常驻标签，错误是否同时包含描边、图标和文字  
- [ ] 独立点击目标是否 ≥ 24×24px，相邻紧凑操作是否至少间隔 8px  
- [ ] 普通文本是否达到 4.5:1，对焦点和控件边界是否达到 3:1  
- [ ] 页边距是否仅一层  
- [ ] 正文字号 ≥ 14px（桌面）  
- [ ] 是否避免新增大白卡片墙  
- [ ] 侧栏是否全部为面型图标，首页模块是否全部为线型图标  
- [ ] 卡片标题图标是否使用 34px 容器 / 20px 图形，且未被页面局部缩小  
- [ ] 页面根容器是否透明并继承统一工作区背景  

---

*版本：2026-07 · 对齐首页 v4.1 适配稿 + 评分总结 editorial*
