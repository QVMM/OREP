# OREP AI 生成 PPT 式 HTML 页系回归清单 V1

## 目标

这份清单用于验证 `page_series_type + page_template_contract + layout_slots` 是否已经真正落到：

- Round 2 页面定义
- Round 3 enriched page
- Round 4 主生成器
- rebuild 重建链路
- fallback 兜底链路
- 视觉审查 / 质检链路

并确保页面不会退化成“更稳定的普通 HTML”。

---

## 第一批重点页系

### 1. `architecture_system`

目标：

- 看起来像“系统架构页”，而不是普通技术说明页
- 应具备：
  - 系统主图 / 架构分层主视觉
  - 技术支撑说明块
  - 分层职责、关键链路、模块边界表达

不应退化成：

- 输入-操作-输出实操闭环页
- 普通信息卡拼贴页
- 内部契约词直接泄露到页面上

抽样页：

- task `107` page `10`
- task `106` page `10`
- task `102` page `10`

验收标准：

- repair preview 不引入 `operation_io_evidence`
- 视觉成品里能看到：
  - 主系统图区
  - 技术支撑块
  - 架构页侧栏要求
- 页面不出现：
  - `system_diagram`
  - `supporting_argument`
  - `主视觉职责：xxx`

---

### 2. `practice_evidence`

目标：

- 看起来像“实操证据页”，而不是普通说明页
- 应具备：
  - 输入 / 操作 / 输出闭环
  - 参数、结果、证据位
  - 右侧闭环要求或评分支撑区

抽样页：

- task `107` page `18`
- task `106` page `18`
- task `102` page `18`

验收标准：

- repair preview 不退化成普通技术卡片页
- 至少表现出：
  - 3 段闭环节点
  - 证据 chips / 截图位
  - 实操闭环说明区

---

### 3. `evidence_board`

目标：

- 看起来像“证据墙页”
- 应具备：
  - 多证据块
  - 可核验感
  - 证据链闭环说明

抽样页：

- task `107` page `3`
- task `106` page `3`
- task `102` page `3`

验收标准：

- 同一页里能看到多块证据位
- 至少一个主证据块跨列或形成显著主视觉
- 不应只是四个普通说明卡片

---

### 4. `value_matrix`

目标：

- 看起来像“价值矩阵页”
- 应具备：
  - 可比较的 2x2 / 4 象限价值表达
  - 实用性 / 经济性 / 可持续性 / 服务对象等价值分面
  - 右侧价值收束或评分支撑说明

抽样页：

- task `107` page `28`
- task `106` page `28`
- task `102` page `28`

验收标准：

- 不是普通“应用价值段落页”
- 至少形成 4 个稳定价值格
- 有明显“价值矩阵”而非散点说明

---

### 5. `closing_board`

目标：

- 看起来像“总结收束页”
- 应具备：
  - 收束主视觉
  - Q&A / 收口感
  - 不是普通信息收尾页

抽样页：

- task `107` page `38`
- task `106` page `38`
- task `102` page `38`

验收标准：

- 能一眼看出“结束感”
- 有主收束区和问答感
- 不应只是“最后几张普通卡片”

---

## 本轮验证结论（2026-04-27）

### 已基本通过

- `evidence_board`
- `practice_evidence`
- `value_matrix`
- `closing_board`

这些页系已经明显摆脱了“普通 HTML 卡片页”的主问题。

### 已修复的关键缺陷

#### `architecture_system` 被 repair 链路误重建成“技术操作页”

表现：

- page 10 原本是系统架构页
- `structure_rebuild` 后被压成“输入-操作-输出”页
- 引入 `operation_io_evidence`

根因：

- old repair path 用的 `page_meta` 没默认化
- `technical_architecture` 被旧规则路由到技术操作闭环页
- `_is_operation_demo_page()` 错把架构页当实操页

修复：

- repair 前补齐 outline defaults
- `technical_architecture` 优先走 `architecture_system`
- 质检不再把架构页判成实操页

结果：

- `107 page 10` repair A/B 从 `100 -> 80` 修回 `100 -> 100`
- `106 page 10` repair A/B `44 -> 100`
- `102 page 10` repair A/B `90 -> 100`

#### 内部契约词泄露到页面

表现：

- 页面直接出现：
  - `system_diagram`
  - `主视觉职责：system_diagram`
  - `本页主视觉区域：承担 system_diagram`

修复：

- rebuild / fallback / main generator 三条路径统一改成人话标签

结果：

- 页面中不再直接出现系统内部枚举词

---

## 每次改页系模板后的复验步骤

### 步骤 1：主生成器抽样

对以下页做主生成抽样：

- `107/3`
- `107/10`
- `107/18`
- `107/28`
- `107/38`

检查：

- `data-slot-role`
- 是否仍按对应页系骨架生成

### 步骤 2：repair A/B 预览

对以下页至少跑一轮：

- `107/10`
- `107/18`
- `107/28`

使用：

- `strategy = structure_rebuild`
- `use_ai = false`
- `preview_only = true`

检查：

- `after_score`
- `introduced_checks`
- 页面截图是否仍保持页系语义

### 步骤 3：截图级人工检查

截图后至少确认：

- 有没有明显的“普通 HTML 味”
- 有没有掉错页系
- 有没有内部系统词泄露
- 有没有丢主视觉焦点

### 步骤 4：交叉任务验证

除了 `107`，至少抽：

- `106`
- `102`

避免某一套任务数据偶然通过，但规则其实不稳。

---

## 后续优先观察项

1. `practice_evidence` 是否还会在某些任务里退化成普通技术说明页  
2. `value_matrix` 是否会在弱数据任务里退化成四块空卡  
3. `closing_board` 是否会在 repair 后丢失结束感  
4. `architecture_system` 是否还会被新的 repair 策略重新误判成实操页  
5. 页面内部是否再次出现契约字段、角色字段、人类不可读的系统词

---

## 结论

当前页系骨架已经从“概念设计”进入“真实任务可验证”阶段。  
后续每次继续改：

- Round 3
- Round 4
- rebuild
- fallback
- visual repair

都应按本清单回归一次，避免重新掉回“更稳定的普通 HTML”。
