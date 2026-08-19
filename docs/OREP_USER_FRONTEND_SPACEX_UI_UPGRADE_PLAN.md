# OREP 用户端 SpaceX-Inspired UI 全方位升级计划

> 状态：方案规划稿  
> 范围：`frontend/user` 用户端前端  
> 目标风格：SpaceX-inspired product UI，不复制 SpaceX 官方品牌资产  
> 参考来源：
> - SpaceX-inspired design-md: https://getdesign.md/spacex/design-md
> - SpaceX token preview: https://getdesign.md/design-md/spacex/preview

## 1. 背景与目标

OREP 用户端当前 UI 具备基础可用性，但整体视觉仍偏通用 SaaS 模板：浅灰背景、白色圆角卡片、蓝紫渐变、彩色图标、页面间风格不统一。用户在首页、会议、数据分析、PPT 生成、PPT 历史详情之间切换时，会感到产品像多个模块拼接，而不是一套完整的路演工作台。

本次升级目标不是简单替换颜色，而是将用户端重塑为一套具备明确品牌气质、任务效率和复杂流程承载能力的产品界面：

```text
OREP Mission Control
路演任务控制中心
黑白高对比
低圆角
细线边框
零/弱阴影
任务面板
遥测数据
发射流程式 PPT 生成管线
```

## 2. 当前用户端架构概览

技术栈：

- Vue 3
- Vite
- Element Plus
- Pinia
- Vue Router
- ECharts
- LiveKit 相关会议能力

核心入口：

- `frontend/user/src/main.js`
- `frontend/user/src/App.vue`
- `frontend/user/src/router/index.js`

主要页面：

- 账号入口：`Login.vue`、`Register.vue`
- 总控首页：`Dashboard.vue`
- 会议流程：`OnlineMeeting.vue`、`MeetingRoom.vue`、`MeetingHistoryDetail.vue`
- PPT 流程：`PptEditor.vue`、`PptGenerator.vue`、`PptHistoryDetail.vue`、`components/ppt/*`
- 数据与资料：`Statistics.vue`、`PptTemplate.vue`
- 个人与资源：`Profile.vue`、`MyRecordings.vue`、`ScriptList.vue`、`ScriptEditor.vue`

当前主要问题：

1. 全局设计系统缺失，页面大量 scoped CSS 各自为政。
2. 蓝紫渐变、光球、柔和大圆角过多，和“路演评审、PPT 生成、会议控制”这类高确定性任务不匹配。
3. 传统卡片堆叠过多，信息密度和工作台感不足。
4. Element Plus 默认蓝色痕迹明显，产品自有风格弱。
5. PPT 相关页面已经偏深色，但仍有蓝紫玻璃感，与 SpaceX-like 黑白工业感不一致。
6. Statistics、Profile 等页面仍保留 Element Plus 默认后台样式。

## 3. 设计定位

### 3.1 不做什么

本次升级不做以下事情：

- 不复制 SpaceX 官方 logo、图片、字体文件或品牌资产。
- 不把用户端做成官网 landing page。
- 不为了风格牺牲复杂业务界面的可读性。
- 不一次性重构所有业务逻辑。
- 不替换 Element Plus 技术底座。
- 不引入大规模 UI 框架迁移。

### 3.2 要做什么

本次升级采用“SpaceX 风格转译”的方式：

- 借鉴黑白高对比、工业字体感、ghost button、低圆角、零阴影。
- 将 SpaceX 的“发射任务”气质转译为 OREP 的“路演任务控制”。
- 将传统卡片升级为任务面板、遥测条、流程管线、清单行、工作台分栏。
- 保留 OREP 作为产品工具所必需的表单、列表、图表、弹窗、状态反馈。

最终产品气质：

```text
不是航天官网
不是普通后台
而是一个用于路演准备、会议参与、AI 评分、PPT 生成和交付质检的任务控制台
```

## 4. SpaceX Design-md 可借鉴规则

从参考页面中提炼的关键规则：

| 设计维度 | SpaceX-inspired 原规则 | OREP 转译方式 |
|---|---|---|
| 颜色 | 黑白为主，极少颜色 | 近黑背景 + 近白文字 + 少量状态色 |
| 字体 | D-DIN，uppercase，正字距 | 英文辅助标签大写；中文保持正常阅读 |
| 按钮 | 单一 ghost button | 产品化扩展为 primary / ghost / danger |
| 卡片 | 不使用传统卡片 | 用 command panel / telemetry strip 替代 |
| 表单 | ghost border，focus 白边 | Element Plus input 统一深色描边 |
| 圆角 | 4px 工具圆角，32px 按钮 | 面板 4-8px，按钮 pill 或 4px |
| 阴影 | 零阴影 | 默认零阴影，少量弹层可用边框和 overlay |
| 深度 | 依赖摄影和 overlay | 依赖背景层、边框、密度、分区 |

## 5. 全局设计 Token 规范

第一阶段必须建立全局样式文件：

```text
frontend/user/src/assets/styles/mission-control.css
```

并在 `frontend/user/src/main.js` 引入：

```js
import './assets/styles/mission-control.css'
```

### 5.1 颜色

建议 token：

```css
:root {
  --orep-bg: #050608;
  --orep-bg-soft: #0b0d10;
  --orep-bg-raised: #111419;

  --orep-panel: rgba(240, 240, 250, 0.045);
  --orep-panel-strong: rgba(240, 240, 250, 0.08);
  --orep-panel-inverse: #f0f0fa;

  --orep-border: rgba(240, 240, 250, 0.14);
  --orep-border-strong: rgba(240, 240, 250, 0.28);
  --orep-border-subtle: rgba(240, 240, 250, 0.08);

  --orep-text: #f0f0fa;
  --orep-text-muted: rgba(240, 240, 250, 0.62);
  --orep-text-dim: rgba(240, 240, 250, 0.38);
  --orep-text-inverse: #050608;

  --orep-accent: #d7e8ff;
  --orep-success: #7cffb2;
  --orep-warning: #ffd36e;
  --orep-danger: #ff5d5d;
  --orep-info: #9ecbff;

  --orep-overlay: rgba(0, 0, 0, 0.62);
}
```

说明：

- 不直接使用纯黑 `#000000` 作为大面积产品背景，避免长时间使用疲劳。
- 保留接近 SpaceX 的 `#f0f0fa` 作为主文字。
- 状态色只用于状态，不用于装饰。
- 禁止继续使用蓝紫渐变作为品牌主视觉。

### 5.2 字体

建议字体栈：

```css
--orep-font:
  "DIN Alternate",
  "D-DIN",
  "Arial Narrow",
  "Inter",
  "Noto Sans SC",
  "PingFang SC",
  "Microsoft YaHei",
  system-ui,
  sans-serif;
```

使用规则：

- 中文正文：正常字重、正常字距。
- 英文小标签：uppercase + 正字距。
- 数字：使用 `font-variant-numeric: tabular-nums`。
- 禁止负字距。
- 避免大段中文使用过窄字体造成阅读压力。

建议类：

```css
.mc-kicker {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--orep-text-dim);
}

.mc-number {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}
```

### 5.3 圆角

```css
--orep-radius-xs: 4px;
--orep-radius-sm: 6px;
--orep-radius-md: 8px;
--orep-radius-pill: 999px;
```

规则：

- 普通面板：4px 或 6px。
- 大工作台：8px。
- 按钮：pill 或 4px，按页面统一。
- 不再使用 16px、24px 作为默认卡片圆角。

### 5.4 阴影

默认禁止传统卡片阴影。层级通过以下方式表达：

1. 背景亮度差。
2. 细线边框。
3. 分区间距。
4. overlay。
5. 只有弹层、dropdown 可以保留非常克制的 shadow。

### 5.5 间距

参考 SpaceX token 的紧凑 spacing，产品化扩展为：

```css
--orep-space-1: 4px;
--orep-space-2: 8px;
--orep-space-3: 12px;
--orep-space-4: 16px;
--orep-space-5: 24px;
--orep-space-6: 32px;
--orep-space-7: 48px;
```

## 6. 全局组件规范

### 6.1 App Shell

目标：

- 从“白色 sticky SaaS 顶栏”升级为“Mission Control 顶栏”。
- 导航更像 SpaceX 官网式文字导航，但保留产品可用性。

结构：

```text
┌─────────────────────────────────────────────────────────────┐
│ OREP  ROADSHOW OPERATIONS PLATFORM     首页 会议 录制 数据 PPT │
└─────────────────────────────────────────────────────────────┘
```

视觉规则：

- 背景：`rgba(5, 6, 8, 0.92)`。
- 边框：底部 1px `--orep-border-subtle`。
- logo：纯文字，不用蓝紫渐变图标。
- 当前导航：底部细线或文字变白。
- hover：轻微白色透明底，不使用蓝色胶囊。

### 6.2 Button

按钮类型：

| 类型 | 用途 | 样式 |
|---|---|---|
| Primary | 关键动作，如加入会议、继续生成、下载 | 白底黑字 |
| Ghost | 次级动作，如查看、返回、刷新 | 透明底 + 白色细边 |
| Text | 低优先级动作 | 透明，无边框 |
| Danger | 退出会议、删除、取消任务 | 红色描边或红底 |
| Warning | 风险处理、继续下载当前版 | 黄色描边 |

Element Plus 覆盖方向：

- `.el-button--primary` 改为白底黑字。
- `.el-button` 默认为 ghost。
- `.el-button.is-text` 保持轻量。
- 不使用渐变按钮。

### 6.3 Form

深色表单规则：

- input 背景：`rgba(240, 240, 250, 0.04)`。
- input border：`--orep-border`。
- focus border：`--orep-text`。
- placeholder：`--orep-text-dim`。
- label：小号高对比，必要时配英文 kicker。

表单布局建议：

```text
┌─────────────────────────────┬──────────────────────────┐
│ 主输入区                     │ 状态说明 / 最近任务        │
│ meeting code                 │ LAST JOINED               │
│ password                     │ SECURITY NOTE             │
│ remember                     │ QUICK HELP                │
└─────────────────────────────┴──────────────────────────┘
```

### 6.4 Status

状态色规则：

| 状态 | 颜色 | 用途 |
|---|---|---|
| running | `--orep-success` | 会议进行中、生成中 |
| pending | `--orep-warning` | 待处理、待确认 |
| failed | `--orep-danger` | 失败、风险、删除 |
| ready | `--orep-info` | 可下载、已准备 |
| idle | `--orep-text-dim` | 未开始 |

状态呈现方式：

- 小圆点。
- 细线 badge。
- 不使用大面积彩色背景。

### 6.5 Element Plus 统一覆盖

第一阶段在全局 CSS 中覆盖：

- `el-button`
- `el-input`
- `el-select`
- `el-dropdown`
- `el-card`
- `el-tag`
- `el-tabs` 或自定义 tab
- `el-empty`
- `el-dialog`
- `el-message`

原则：

- 先覆盖可见基础组件。
- 不对每个页面重复写深色 Element Plus override。
- 复杂页面允许局部覆盖，但必须使用 token。

## 7. 版式系统：替代传统卡片

当前页面大量使用传统矩形卡片。升级后改为以下版式单元。

### 7.1 Hero Command Band

用途：

- Login
- Register
- Dashboard 顶部
- 资源页顶部

特点：

- 大面积深色背景。
- 文案直接落在背景上。
- 可使用 CSS 轨道线、扫描线、细网格。
- 不用漂浮卡片承载主标题。

线框：

```text
┌─────────────────────────────────────────────────────────┐
│ MISSION CONTROL                                         │
│ 路演任务控制中心                                         │
│ AI scoring / PPT launch / meeting telemetry             │
│                                                         │
│ [JOIN MISSION] [BUILD PPT]                              │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Telemetry Strip

用途：

- 首页指标。
- 数据分析概览。
- PPT 历史摘要。

替代：

- 四张统计卡片。

线框：

```text
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ TOTAL MEET   │ AVG SCORE    │ PPT BUILDS   │ OPEN RISKS   │
│ 12           │ 86.4         │ 7            │ 3            │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

视觉：

- 同一个横向容器。
- 内部分割线。
- 数字大，label 小且 uppercase。
- 不给每个指标单独做圆角卡。

### 7.3 Mission Manifest

用途：

- 最近参与。
- 会议历史。
- 我的录制。
- PPT 历史记录。

替代：

- 一条记录一张卡片。

线框：

```text
┌────┬──────────┬───────────────────────┬──────────────┬────────┐
│ 01 │ RUNNING  │ 智慧农业项目路演会议     │ 2026-05-11   │ 查看    │
│ 02 │ ENDED    │ AI PPT 复盘会议         │ 2026-05-10   │ 详情    │
└────┴──────────┴───────────────────────┴──────────────┴────────┘
```

视觉：

- 行式布局。
- hover 时行背景轻微变亮。
- 状态列固定宽度。
- 不使用重阴影。

### 7.4 Pipeline Board

用途：

- PPT 生成。
- AI 评分流程。
- 会议录制处理流程。

替代：

- Element Plus 默认 steps。

线框：

```text
INPUT ━━━━━ OUTLINE ━━━━━ RENDER ━━━━━ QA ━━━━━ EXPORT
 01          02           03          04        05
```

视觉：

- 细线连接。
- 当前步骤白色高亮。
- 完成步骤用 success 状态点。
- 失败步骤用 danger 状态点。

### 7.5 Command Split

用途：

- OnlineMeeting 加入会议。
- Login/Register。
- PPT 问卷填写。
- ScriptEditor。

线框：

```text
┌──────────────────────────────────────┬────────────────────────┐
│ PRIMARY TASK                         │ CONTEXT                │
│ 表单 / 编辑器 / 当前操作              │ 最近记录 / 规则 / 状态   │
└──────────────────────────────────────┴────────────────────────┘
```

### 7.6 Docked Workspace

用途：

- MeetingRoom。
- PptEditor。
- PptHistoryDetail。

线框：

```text
┌─────────────────────────────────────────────────────────┐
│ TOP COMMAND BAR                                         │
├──────────────┬──────────────────────────┬───────────────┤
│ NAV / STEPS   │ MAIN WORKSPACE           │ STATUS PANEL   │
│              │                          │               │
└──────────────┴──────────────────────────┴───────────────┘
```

### 7.7 Telemetry Matrix

用途：

- Statistics。
- PPT 质检矩阵。
- 评分覆盖矩阵。

线框：

```text
┌──────────────┬───────────────────────────────┐
│ SCORE 86.4   │ TREND CHART                   │
├──────────────┼───────────────────────────────┤
│ RISKS 3      │ ISSUE DISTRIBUTION            │
├──────────────┴───────────────────────────────┤
│ DIMENSION MATRIX                              │
└───────────────────────────────────────────────┘
```

## 8. 页面级改造方案

### 8.1 `App.vue`

目标：

- 建立全局 Mission Control 外壳。
- 去除蓝紫渐变 logo。
- 统一主背景。

改造点：

1. `app-container` 背景改为 `--orep-bg`。
2. header 改为深色半透明顶栏。
3. logo 改为纯文字：

```text
OREP
ROADSHOW OPERATIONS PLATFORM
```

4. nav item 改为文字导航 + 细线 active。
5. 用户头像改为线框或白底黑字小方块。
6. dropdown 覆盖为深色菜单。

验收：

- 登录后所有页面顶部风格一致。
- 无蓝紫渐变 logo。
- 移动端导航不溢出。

### 8.2 `Login.vue`

目标：

- 做成强品牌入口。
- 让用户第一眼感知 OREP 是专业路演任务系统。

版式：

```text
┌──────────────────────────────┬──────────────────────┐
│ OREP                         │ LOGIN                │
│ ROADSHOW OPERATIONS PLATFORM │ username             │
│ MISSION CONTROL              │ password             │
│ AI SCORING / PPT LAUNCH      │ [SIGN IN]            │
└──────────────────────────────┴──────────────────────┘
```

改造点：

1. 左侧大面积黑色 command band。
2. 背景加入 CSS 轨道线或细网格，不使用真实 SpaceX 图片。
3. 右侧表单改为深色 ghost form。
4. 登录按钮改为白底黑字。
5. “立即注册”改为 ghost link。

验收：

- 视觉上不再像蓝紫 SaaS 登录页。
- 表单错误、loading、enter 登录可用。
- 1024px 以下自动单列。

### 8.3 `Register.vue`

目标：

- 与 Login 使用同一入口系统。
- 修复当前注册页默认 `el-card` 风格。

改造点：

1. 复用 Login 的 page shell。
2. 验证码输入和按钮放在同一 control row。
3. 倒计时按钮有 disabled 态。
4. 保持邮箱、验证码、用户名、密码、确认密码完整流程。

验收：

- Login/Register 切换时风格连续。
- 验证码按钮在移动端不挤压输入框。

### 8.4 `Dashboard.vue`

目标：

- 从普通首页改为 `MISSION CONTROL` 总控台。
- 重点解决“传统卡片网格”问题。

新版信息架构：

```text
┌─────────────────────────────────────────────────────────┐
│ MISSION CONTROL                                         │
│ 晚上好，用户                                             │
│ [JOIN MISSION] [BUILD PPT]                              │
├─────────────────────────────────────────────────────────┤
│ TELEMETRY STRIP: meetings / score / ppt / risks         │
├───────────────────────────────┬─────────────────────────┤
│ MISSION MODULES               │ LAUNCH ACTIONS          │
│ Online Meeting                │ AI PPT                  │
│ PPT Pipeline                  │ Resources               │
│ Script                        │ Script Editor           │
│ Analytics                     │                         │
├───────────────────────────────┴─────────────────────────┤
│ RECENT MISSION MANIFEST                                  │
└─────────────────────────────────────────────────────────┘
```

改造点：

1. 去除当前 `.visual-orb`、渐变 hero。
2. 功能模块从 4 张彩色卡片改为 mission modules：
   - 编号：`01`
   - 英文 kicker：`MEETING`
   - 中文标题：`在线会议`
   - 状态/说明：一行短文本
3. 最近参与改成 manifest row。
4. 快捷操作改成 launch actions 列表。
5. 状态颜色仅用于小点或小标签。

验收：

- 首屏看起来像任务控制台，而非营销首页。
- 功能入口点击路径保持不变。
- recentHistory 空状态有深色适配。

### 8.5 `OnlineMeeting.vue`

目标：

- 将“加入会议”升级为 `JOIN MISSION`。
- 历史记录改成 manifest。

版式：

```text
┌─────────────────────────────────────────────────────────┐
│ JOIN MISSION                                            │
│ 输入会议号和密码进入路演会议                              │
├────────────────────────────────┬────────────────────────┤
│ MEETING ACCESS                 │ LAST MISSIONS          │
│ meeting code                   │ 01 RUNNING xxx         │
│ password                       │ 02 ENDED xxx           │
│ remember                       │                        │
│ [JOIN MISSION]                 │                        │
└────────────────────────────────┴────────────────────────┘
```

改造点：

1. Tab 改为 command switch。
2. 加入会议表单改为 Command Split。
3. 参与记录改为 Manifest Row。
4. 会议状态 tag 改为细线状态 badge。

验收：

- 加入会议流程不变。
- 历史列表可读，移动端自动堆叠。

### 8.6 `Statistics.vue`

目标：

- 从 Element Plus 默认统计页升级为 `ROADSHOW TELEMETRY`。

版式：

```text
┌─────────────────────────────────────────────────────────┐
│ ROADSHOW TELEMETRY                                      │
├─────────────────────────────────────────────────────────┤
│ TELEMETRY STRIP                                         │
├──────────────────────────────────┬──────────────────────┤
│ SCORE TREND                      │ ISSUE STATUS          │
│ ECharts line                     │ ECharts pie/matrix    │
└──────────────────────────────────┴──────────────────────┘
```

改造点：

1. 去掉 `el-card` 默认白卡。
2. 指标卡改为 telemetry strip。
3. ECharts 改深色主题：
   - background transparent
   - axis line 使用弱白
   - split line 使用低透明白
   - tooltip 深色
   - line 使用 `--orep-accent`
4. 问题统计尽量减少大面积彩色。

验收：

- 图表在深色背景可读。
- resize 后图表正常。
- 无 Element Plus 默认白底残留。

### 8.7 `MeetingRoom.vue`

目标：

- 保留会议软件可用性。
- 统一 Mission Control 视觉。

改造点：

1. 背景色统一为 `--orep-bg` / `--orep-bg-soft`。
2. 顶部 room header 改为 command bar。
3. 控制栏按钮使用统一 ghost/active/danger。
4. 聊天区、参会者、评分弹窗统一 panel 和 border。
5. 网络状态保留颜色，但降低饱和面积。

验收：

- 视频会议核心操作不受影响。
- 全屏模式正常。
- 录制、评分、聊天状态清晰。

### 8.8 `PptEditor.vue`

目标：

- 打造最核心的 `PPT LAUNCH PIPELINE`。
- 将生成流程做成发射流程工作台。

新版信息架构：

```text
┌─────────────────────────────────────────────────────────┐
│ PPT LAUNCH PIPELINE       [历史] [返回]                  │
├─────────────────────────────────────────────────────────┤
│ INPUT ━ OUTLINE ━ RENDER ━ QA ━ EXPORT                  │
├───────────────────────────────┬─────────────────────────┤
│ CURRENT STEP WORKSPACE        │ MISSION STATUS          │
│ 问卷 / 大纲 / 预览 / 导出       │ 生成状态 / 风险 / 下一步  │
└───────────────────────────────┴─────────────────────────┘
```

改造点：

1. 替换现有蓝紫玻璃背景为黑白细线系统。
2. pipeline steps 改成 SpaceX-like 发射流程条。
3. step panel 圆角降低，去掉大阴影。
4. domain cards 改为 module selector。
5. outline info 改为 telemetry summary。
6. 预览工作台保留 docked workspace。
7. 错误弹窗、readiness dialog 深色统一。

验收：

- 所有 5 个步骤视觉统一。
- 生成中、失败、完成、导出状态清楚。
- 不影响现有 API 调用和状态流。

### 8.9 `components/ppt/*`

目标：

- 为 PptEditor 和 PptHistoryDetail 提供一致的组件层视觉。

优先组件：

1. `PptPreviewWorkspace.vue`
2. `PptDownloadReadinessCard.vue`
3. `PptQualityReportPanel.vue`
4. `PptHtmlWorkbench.vue`
5. `PptOutlineEditor.vue`
6. `PptScoringCoveragePanel.vue`
7. `PptMaterialsAdvancedPanel.vue`

改造原则：

- `quality-eyebrow` 统一为 `.mc-kicker`。
- card 改为 panel。
- badge 改为 outline status。
- 列表改 manifest row。
- 上传区改 ghost dropzone。

### 8.10 `PptHistoryDetail.vue`

目标：

- 信息很多，但不能继续堆卡片。
- 改成“交付质检控制台”。

新版版式：

```text
┌─────────────────────────────────────────────────────────┐
│ PROJECT DELIVERY CONTROL                                │
├──────────────┬──────────────────────────────┬───────────┤
│ SECTION NAV   │ MAIN REPORT                  │ DOWNLOAD  │
│ 摘要/质量/素材 │ 质量矩阵/页面详情/修复建议     │ 条件/动作  │
└──────────────┴──────────────────────────────┴───────────┘
```

改造点：

1. summary grid 改为 telemetry matrix。
2. readiness dashboard 改为 control dashboard。
3. download checklist 固定为右侧 action panel。
4. 页面列表改 manifest / matrix。
5. 风险、缺失、警告用小状态色，不用大块彩色背景。

验收：

- 大量质量信息更可扫读。
- 下载条件始终明确。
- 修复动作入口保留。

## 9. 分阶段实施计划

### Phase 0：准备与基线记录

目标：

- 确保改造前有可回看基线。
- 明确页面路径和关键流程。

行动：

1. 记录当前 git 状态。
2. 启动用户端 dev server。
3. 截图以下页面：
   - `/login`
   - `/register`
   - `/`
   - `/online-meeting`
   - `/statistics`
   - `/ppt-editor`
   - `/my-recordings`
4. 记录主要交互：
   - 登录表单。
   - 加入会议表单。
   - 首页跳转。
   - 统计图表渲染。

验收：

- 有改造前截图。
- dev server 可正常启动。

### Phase 1：全局视觉系统 + 关键页面

目标：

- 建立 Mission Control 视觉基准。
- 先完成用户最容易感知的页面。

文件：

```text
frontend/user/src/assets/styles/mission-control.css
frontend/user/src/main.js
frontend/user/src/App.vue
frontend/user/src/views/Login.vue
frontend/user/src/views/Register.vue
frontend/user/src/views/Dashboard.vue
frontend/user/src/views/OnlineMeeting.vue
frontend/user/src/views/Statistics.vue
```

行动：

1. 新增全局 token 和 Element Plus 基础覆盖。
2. 改造 App Shell。
3. 改造登录/注册入口。
4. 改造 Dashboard。
5. 改造 OnlineMeeting。
6. 改造 Statistics 深色图表。

验收：

- 第一眼风格明显转向 Mission Control。
- 蓝紫渐变主视觉消失。
- 首页不再是传统圆角彩色卡片。
- `npm run build` 通过。
- 桌面和移动端主要页面无文字溢出。

### Phase 2：PPT 生成工作台

目标：

- 将 OREP 最复杂、最核心的 PPT 流程升级为发射流程式工作台。

文件：

```text
frontend/user/src/views/PptEditor.vue
frontend/user/src/components/ppt/PptPreviewWorkspace.vue
frontend/user/src/components/ppt/PptDownloadReadinessCard.vue
frontend/user/src/components/ppt/PptQualityReportPanel.vue
frontend/user/src/components/ppt/PptHtmlWorkbench.vue
frontend/user/src/components/ppt/PptOutlineEditor.vue
frontend/user/src/components/ppt/PptStageWaitingPanel.vue
frontend/user/src/components/ppt/PptStylePreviewSection.vue
```

行动：

1. 统一 PptEditor 外壳。
2. 改造 pipeline steps。
3. 改造 step panels。
4. 改造等待、错误、完成、导出状态。
5. 改造 preview workspace。
6. 改造质量报告和下载条件。

验收：

- 每个步骤视觉一致。
- loading、error、retry、success 状态完整。
- 复杂内容不因深色主题降低可读性。
- 不破坏现有 PPT 生成状态机。

### Phase 3：PPT 历史详情与交付质检

目标：

- 将 `PptHistoryDetail.vue` 从信息堆叠页升级为交付控制台。

文件：

```text
frontend/user/src/views/PptHistoryDetail.vue
frontend/user/src/components/ppt/PptPracticeDemoPanel.vue
frontend/user/src/components/ppt/PptRoadshowPanel.vue
frontend/user/src/components/ppt/PptMaterialsAdvancedPanel.vue
frontend/user/src/components/ppt/PptScoringCoveragePanel.vue
frontend/user/src/components/ppt/PptOutlineGuardCard.vue
```

行动：

1. 建立三栏 docked layout。
2. summary grid 改 telemetry matrix。
3. download readiness 固定化、工作台化。
4. 质量、素材、评分覆盖组件统一 token。

验收：

- 信息密度提高但不混乱。
- 下载条件和修复动作更突出。
- 大页面滚动体验可控。

### Phase 4：会议室与其他页面收口

目标：

- 把剩余页面全部纳入同一视觉系统。

文件：

```text
frontend/user/src/views/MeetingRoom.vue
frontend/user/src/views/MeetingHistoryDetail.vue
frontend/user/src/views/MyRecordings.vue
frontend/user/src/views/PptTemplate.vue
frontend/user/src/views/Profile.vue
frontend/user/src/views/ScriptList.vue
frontend/user/src/views/ScriptEditor.vue
frontend/user/src/views/AiScoreResult.vue
frontend/user/src/views/ScoreResult.vue
frontend/user/src/views/RoadshowChat.vue
```

行动：

1. 统一深色背景和 panel。
2. 统一列表为 manifest rows。
3. 统一表单、弹窗、按钮。
4. 会议室保留操作效率优先。

验收：

- 全用户端无明显“旧白色后台页”。
- 所有可访问路由视觉统一。

## 10. 第一阶段详细行动清单

### 10.1 创建全局样式

文件：`frontend/user/src/assets/styles/mission-control.css`

内容模块：

1. CSS variables。
2. base reset。
3. Element Plus dark overrides。
4. 通用 utilities：
   - `.mc-page`
   - `.mc-shell`
   - `.mc-panel`
   - `.mc-kicker`
   - `.mc-telemetry-strip`
   - `.mc-manifest`
   - `.mc-status`
   - `.mc-command-grid`
5. responsive helpers。

### 10.2 修改 `main.js`

行动：

- 在 Element Plus 样式之后引入 mission-control.css，确保覆盖生效。

风险：

- 如果覆盖太强，可能影响 MeetingRoom 或 PptEditor 的局部样式。

规避：

- 全局覆盖只处理 Element Plus 基础组件。
- 页面级布局类使用 `.mc-*`，不污染所有 div。

### 10.3 修改 `App.vue`

行动：

- 替换 logo SVG。
- 替换 header CSS。
- 导航加入英文辅助可选字段。
- 用户 dropdown 深色化。

保留：

- route guard 不变。
- navItems 路径不变。
- logout 逻辑不变。

### 10.4 修改 `Login.vue`

行动：

- 改造为 split auth layout。
- 删除蓝紫渐变装饰圆。
- 表单控件使用全局 Element Plus 覆盖。
- CTA 改为 Mission Control 按钮语言。

保留：

- `authStore.login` 不变。
- 校验规则不变。
- `ElMessage` 不变。

### 10.5 修改 `Register.vue`

行动：

- 复用 auth split layout。
- 移除 `el-card` 默认注册卡。
- 验证码 row 响应式处理。

保留：

- `sendCode`、倒计时、register 逻辑不变。

### 10.6 修改 `Dashboard.vue`

行动：

- 重写模板结构为 hero command band + telemetry + mission modules + manifest。
- 删除 visual orb。
- features 数据增加 `code` / `kicker` 字段。
- recent list 改 manifest rows。

保留：

- `fetchRecentHistory` 不变。
- 路由跳转不变。

### 10.7 修改 `OnlineMeeting.vue`

行动：

- page header 改 command header。
- tab bar 改 command switch。
- join card 改 command split。
- history card 改 manifest rows。

保留：

- join API 逻辑不变。
- remember credentials 逻辑不变。

### 10.8 修改 `Statistics.vue`

行动：

- overview 改 telemetry strip。
- `el-card` 改 panel。
- ECharts option 深色化。
- 响应式从 `el-row/el-col` 可保留，也可局部改 CSS grid。

保留：

- `fetchStatistics` 不变。
- chart init / resize / unmount 不变。

## 11. 验收标准

### 11.1 视觉验收

必须满足：

- 用户端主色从浅色蓝紫转为黑白高对比。
- 首屏不再出现蓝紫渐变 hero 和装饰光球。
- 默认卡片阴影显著减少或消失。
- 圆角明显降低。
- Element Plus 默认蓝色大幅减少。
- 主要按钮有清晰主次。
- 状态色不滥用。

### 11.2 版式验收

必须满足：

- Dashboard 不再是四个普通彩色卡片 + 两个白卡。
- Statistics 不再是 Element Plus 默认 `el-card` 看板。
- OnlineMeeting 不再是居中的白色加入会议卡。
- Login/Register 风格一致。
- App Header 与页面主题一致。

### 11.3 功能验收

必须满足：

- 登录、注册、验证码、退出登录功能不受影响。
- 首页所有跳转不受影响。
- 加入会议功能不受影响。
- 历史记录请求不受影响。
- 数据统计图表正常渲染。
- `npm run build` 通过。

### 11.4 响应式验收

检查宽度：

- 1440px
- 1280px
- 1024px
- 768px
- 390px

必须满足：

- 顶栏不溢出。
- 表单按钮不挤压。
- telemetry strip 在移动端自动换行或纵向堆叠。
- manifest row 在移动端变为两行或卡片式行，但不回到旧大圆角卡片。

## 12. 测试与验证命令

在 `frontend/user` 执行：

```bash
npm run build
```

本地预览：

```bash
npm run dev
```

建议人工检查路由：

```text
/login
/register
/
/online-meeting
/statistics
/ppt-editor
/my-recordings
/profile
```

如果有测试账号，第一阶段至少走通：

1. 登录。
2. 首页进入在线会议。
3. 切换参与记录。
4. 查看数据分析。
5. 退出登录。

## 13. 执行纪律

### 13.1 改造原则

1. 先 token，后页面。
2. 先全局壳，后局部组件。
3. 先静态结构，后交互动效。
4. 先关键路径，后边缘页面。
5. 不在第一阶段重构业务逻辑。
6. 不修改 API 请求路径。
7. 不删除现有功能入口。
8. 不引入未必要的新依赖。

### 13.2 CSS 纪律

1. 新样式优先使用 `mission-control.css` 的 token。
2. 页面 scoped CSS 可以保留，但颜色必须从 token 取。
3. 禁止新增蓝紫渐变作为主视觉。
4. 禁止新增大面积阴影卡片。
5. 禁止新增装饰光球、bokeh、随机渐变背景。
6. 禁止使用负字距。
7. 避免 `!important`，只有覆盖 Element Plus 必要状态时使用。

### 13.3 组件纪律

1. 按钮语义必须明确。
2. 主要动作每屏最多 1-2 个。
3. 状态 feedback 必须清晰。
4. loading / empty / error 状态必须深色适配。
5. 不让英文 uppercase 破坏中文阅读。

## 14. 风险与规避

| 风险 | 说明 | 规避 |
|---|---|---|
| 深色主题可读性下降 | 表单、图表、列表可能对比不足 | 建立 token，对每页截图验证 |
| Element Plus 覆盖污染 | 全局 override 可能影响复杂页面 | 覆盖范围控制在基础组件，复杂页面逐步适配 |
| SpaceX 风格太官网化 | OREP 是产品工具，不是品牌页 | 保留产品工作台布局，不照搬 full-bleed photography |
| 卡片减少后信息散 | 传统卡片去掉后层级可能不清 | 使用 panel、分割线、telemetry、manifest 替代 |
| PPT 页面体量巨大 | `PptEditor.vue` 和 `PptHistoryDetail.vue` 很大 | 分阶段处理，先做外壳和关键组件 |
| 移动端溢出 | 高密度 command UI 容易挤 | 每个阶段做 390px 检查 |

## 15. 推荐最终产物结构

第一阶段后：

```text
frontend/user/src/assets/styles/
└── mission-control.css

frontend/user/src/App.vue
frontend/user/src/main.js
frontend/user/src/views/Login.vue
frontend/user/src/views/Register.vue
frontend/user/src/views/Dashboard.vue
frontend/user/src/views/OnlineMeeting.vue
frontend/user/src/views/Statistics.vue
```

第二阶段后可考虑继续拆分：

```text
frontend/user/src/assets/styles/
├── mission-control.css
├── mission-layouts.css
└── mission-element-plus.css
```

只有当 `mission-control.css` 过大且难维护时再拆分。

## 16. 设计语言速查表

| 旧 UI | 新 UI |
|---|---|
| 蓝紫渐变 logo | 黑白 OREP 字标 |
| 白色圆角卡片 | 深色细线 command panel |
| 彩色功能 icon card | mission module |
| 统计卡片 | telemetry strip |
| 最近记录卡片 | mission manifest |
| 默认 Element Plus steps | launch pipeline |
| 蓝色 primary button | 白底黑字 primary |
| 柔和 SaaS hero | command band |
| 装饰光球 | 轨道线、细网格、扫描线 |
| 大阴影 | 无阴影，靠边框和层级 |

## 17. 第一阶段完成定义

当以下条件全部满足，Phase 1 才算完成：

- [ ] `mission-control.css` 已建立并被 `main.js` 引入。
- [ ] `App.vue` 顶栏已升级为 Mission Control 外壳。
- [ ] `Login.vue` 与 `Register.vue` 已统一为 SpaceX-inspired 入口。
- [ ] `Dashboard.vue` 已使用 command band、telemetry strip、mission manifest。
- [ ] `OnlineMeeting.vue` 已使用 command split 和 manifest row。
- [ ] `Statistics.vue` 已改为深色 telemetry dashboard。
- [ ] 主要页面无蓝紫渐变主视觉。
- [ ] 主要页面无默认白色 Element Plus 卡片残留。
- [ ] `npm run build` 通过。
- [ ] 桌面和移动端截图验收通过。

## 18. 后续建议

第一阶段完成后，不急着立刻全量改复杂 PPT 页面。建议先让用户确认整体气质：

1. 是否认可黑白高对比方向。
2. 是否认可低圆角、零阴影、少卡片的产品气质。
3. 首页的信息密度是否合适。
4. 登录/注册是否过于冷峻。
5. 数据分析图表是否足够清晰。

确认后再进入 Phase 2，对 `PptEditor.vue` 做更深的工作台化升级。PPT 相关页面是 OREP 的核心能力，值得在第一阶段视觉基准稳定后再精修。

