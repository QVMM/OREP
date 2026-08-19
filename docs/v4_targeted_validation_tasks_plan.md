# V4 Targeted Validation Tasks Plan

## 目标

为 `bridge_story / collaboration_matrix / journey_timeline` 设计 3 个定向验证任务，避免真实任务测试继续“碰运气”。

这 3 个任务的用途不是评估整套 PPT，而是专门验证：

1. solver 是否能稳定命中目标 family
2. narrative role 是否能稳定命中目标职责
3. renderer 是否能稳定落到目标 skeleton
4. reviewer / regression 是否能识别出结构差异，而不是只看到 family 名不同

## 原则

- 每个任务只主打一个 family
- 文案必须足够“诱发”目标 narrative role
- 不能把 3 类语义混在同一个任务里，否则 solver 命中结果不纯
- 每个任务都要有：
  - `推荐任务标题`
  - `建议项目背景`
  - `建议页面段落描述`
  - `预期命中的 page series / narrative role / skeleton`
  - `通过标准`

---

## 任务 A：Bridge Story 定向验证

### 任务目标

验证 `bridge_story` 是否能稳定区分：

- `solution_narrative`
- `feedback_bridge`
- `industry_translation`

优先验证本轮新增的 `feedback_bridge -> feedback_loop_board`。

### 推荐任务标题

`产教融合实训平台：执行反馈到育人成效的闭环验证`

### 建议项目背景

一个面向职业教育的实训平台，核心卖点不是单纯“系统功能”，而是：

- 课堂任务如何对接行业场景
- 执行反馈如何回流到教学改进
- 最终如何沉淀为育人成效

### 建议输入文案

可直接作为任务问卷/项目简介的核心文本：

```text
项目名称：产教融合实训平台

项目简介：
本项目面向职业教育与产业协同实训场景，重点解决“课堂能力培养”和“行业真实任务”脱节的问题。平台将课程训练任务映射到行业场景任务，再把执行反馈、过程评价和结果表现回流到教学改进，形成“能力训练—真实任务—反馈回流—育人成效”的闭环。

希望重点表达的内容：
1. 课程能力如何桥接到行业任务
2. 学生执行过程中的反馈如何回流
3. 教学侧如何根据反馈做调整
4. 最终形成哪些育人成效
```

### 建议观察页

- 正文中应至少出现 1 页 `bridge_story`
- 如果命中“反馈闭环”表达，应优先看：
  - 是否落到 `feedback_bridge`
  - 是否落到 `feedback_loop_board`

### 预期命中

- `page_series_type`
  - `bridge_story`
- `narrative_role`
  - 优先：`feedback_bridge`
  - 次优：`industry_translation`
- `layout_skeleton`
  - 优先：`feedback_loop_board`
  - 次优：`bridge_arc_flow`

### 通过标准

- 主目标：
  - 必须稳定命中 `bridge_story`
  - 在同一任务 `3` 次重跑，或 `2-3` 个轻微改写版本下：
    - `feedback_bridge` 应达到多数命中
    - `feedback_loop_board` 应达到多数命中
- 次优降级：
  - 若未命中 `feedback_bridge / feedback_loop_board`
  - 但稳定命中 `industry_translation / bridge_arc_flow`
  - 只能算“降级通过”，不能等同于主目标通过
- 最终 HTML 中应能看到：
  - `data-layout-skeleton="feedback_loop_board"` 或降级的 `bridge_arc_flow`
  - 肉眼可见的“闭环”或“桥接主线”结构
- 不接受退回成普通支撑卡页或 generic 卡片墙

---

## 任务 B：Collaboration Matrix 定向验证

### 任务目标

验证 `collaboration_matrix` 是否能稳定区分：

- `role_responsibility`
- `handoff_chain`
- `coordination_resilience`

优先验证本轮新增的 `handoff_chain -> handoff_chain_board`。

### 推荐任务标题

`智慧巡检平台：岗位交接、应急补位与协同机制设计`

### 建议项目背景

一个多岗位协同的智慧巡检/应急处置平台，重点不在产品功能本身，而在：

- 岗位职责如何划分
- 任务如何交接
- 发生异常时如何补位
- 协同后如何形成稳定结果

### 建议输入文案

```text
项目名称：智慧巡检平台

项目简介：
本项目服务于多岗位协同巡检与应急处置场景，涉及现场巡检员、值班员、研判人员和管理人员等多类角色。平台不仅需要明确各岗位职责，还需要支持任务交接、异常升级、应急补位和协同结果留痕，确保在高强度运转中仍能稳定完成闭环处置。

希望重点表达的内容：
1. 各岗位职责边界
2. 任务交接和升级链路
3. 应急情况下的补位机制
4. 协同后形成的处置结果
```

### 建议观察页

- 正文中应至少出现 1 页 `collaboration_matrix`
- 如果命中“交接/补位/升级链路”表达，应优先看：
  - 是否落到 `handoff_chain`
  - 是否落到 `handoff_chain_board`

### 预期命中

- `page_series_type`
  - `collaboration_matrix`
- `narrative_role`
  - 优先：`handoff_chain`
  - 次优：`coordination_resilience`
- `layout_skeleton`
  - 优先：`handoff_chain_board`
  - 次优：`role_grid_board`

### 通过标准

- 主目标：
  - 必须稳定命中 `collaboration_matrix`
  - 在同一任务 `3` 次重跑，或 `2-3` 个轻微改写版本下：
    - `handoff_chain` 应达到多数命中
    - `handoff_chain_board` 应达到多数命中
- 次优降级：
  - 若未命中 `handoff_chain / handoff_chain_board`
  - 但稳定命中 `coordination_resilience / role_grid_board`
  - 只能算“降级通过”，不能等同于主目标通过
- 最终 HTML 中应能看到：
  - `data-layout-skeleton="handoff_chain_board"` 或降级的 `role_grid_board`
  - 肉眼可见的“流程交接”或“职责矩阵”差异
- 不接受退回成普通说明卡片页

---

## 任务 C：Journey Timeline 定向验证

### 任务目标

验证 `journey_timeline` 是否能稳定区分：

- `milestone_progress`
- `iteration_evidence`
- `retrospective_improvement`

优先验证本轮新增的 `retrospective_improvement -> retrospective_split`。

### 推荐任务标题

`农业监测终端：研发历程、问题复盘与质量改进记录`

### 建议项目背景

一个硬件+平台结合的研发项目，重点不只是展示“做过哪些阶段”，而是：

- 阶段推进
- 测试验证
- 暴露问题
- 质量改进
- 迭代收敛

### 建议输入文案

```text
项目名称：农业监测终端

项目简介：
本项目经历了需求调研、原型设计、测试验证、问题复盘和质量改进多个阶段。研发过程中既要展示关键里程碑，也要说明每轮测试暴露的问题、后续改进动作以及最终形成的稳定版本，突出项目不是一次性完成，而是通过复盘和迭代持续收敛。

希望重点表达的内容：
1. 关键里程碑推进
2. 每轮测试与验证产出
3. 暴露的关键问题
4. 后续质量改进动作
5. 最终形成的稳定结果
```

### 建议观察页

- 正文中应至少出现 1 页 `journey_timeline`
- 如果命中“问题复盘/质量改进”表达，应优先看：
  - 是否落到 `retrospective_improvement`
  - 是否落到 `retrospective_split`

### 预期命中

- `page_series_type`
  - `journey_timeline`
- `narrative_role`
  - 优先：`retrospective_improvement`
  - 次优：`iteration_evidence`
- `layout_skeleton`
  - 优先：`retrospective_split`
  - 次优：`milestone_rail`

### 通过标准

- 主目标：
  - 必须稳定命中 `journey_timeline`
  - 在同一任务 `3` 次重跑，或 `2-3` 个轻微改写版本下：
    - `retrospective_improvement` 应达到多数命中
    - `retrospective_split` 应达到多数命中
- 次优降级：
  - 若未命中 `retrospective_improvement / retrospective_split`
  - 但稳定命中 `iteration_evidence / milestone_rail`
  - 只能算“降级通过”，不能等同于主目标通过
- 最终 HTML 中应能看到：
  - `data-layout-skeleton="retrospective_split"` 或降级的 `milestone_rail`
  - 肉眼可见的“阶段推进”或“复盘改进”差异
- 不接受只落成普通时间线说明卡

---

## 执行建议

### 第一步：单任务验证

分别创建 3 个定向任务：

1. `bridge_story` 任务
2. `collaboration_matrix` 任务
3. `journey_timeline` 任务

每个任务只验证一个主 family，不混测。

### 第二步：记录结果

每个任务至少记录：

- 实际命中的 `page_series_type`
- 实际命中的 `narrative_role`
- 实际命中的 `layout_skeleton`
- HTML 页面截图
- 是否触发 reviewer / regression 告警
- 同一任务的 `3` 次重跑结果
- 同一任务 `2-3` 个轻微改写版本的命中结果

### 第三步：混合 deck 验证

在单任务验证通过后，再构造 1 个综合任务，把：

- `bridge_story`
- `collaboration_matrix`
- `journey_timeline`

放进同一套 deck，看它们在同一个 `solution cluster` 里会不会重新收敛成一套默认结构。

## 审核问题

给 `Euler` 的审核问题：

1. 这 3 个定向验证任务的输入文案，是否足够稳定地诱发目标 family 与目标 narrative role？
2. 每个任务只验证一个主 family 的拆法，是否合理，能否避免“混合语义导致命中不纯”？
3. 当前定义的通过标准，在加入“多次重跑 / 轻微改写版本 / 主目标与降级目标分层”之后，是否足够判断“能力已经真正稳定生效”，而不是只是碰巧命中一次？
