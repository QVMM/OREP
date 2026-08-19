# AI 评分“单分数、双层能力”优化设计

## 1. 目标

用户只看到一个 AI 评分。该分数是按 42 赛道版本化 Rubric、当前证据上限和有效扣分项计算的最终分，必须能与维度、观察项、扣分项和证据逐层对账。

后台保留两层能力：

- 可信判分层：产生唯一正式 AI 分数。
- 训练诊断层：评价表达、节奏、临场、说服力和改进趋势，不产生第二个总分。

## 2. 权威责任边界

### Python AI 评分服务

Python 是评分主体，负责视频、语音、材料处理，证据抽取，Rubric 匹配，Observation/Deduction 生成，证据封顶，正式规则计算，历史问题证据复检和训练诊断。

Python 输出的 `finalScore` 是用户唯一可见分数。LLM 直接给出的分数只作为 `llmRawScore` 用于后台稳定性监控。

### Java 业务后端

Java 负责评分会话、权限、项目与团队身份、历史评分链、快照、指纹、回调幂等、结构化结果落库和发布门禁。

Java 使用与 Python 一致的标准化输入独立复算。复算不一致时不得将报告标记为 `completed`。Java 不重新理解视频，也不另造一套 Rubric 语义。

### 用户前端

前端展示唯一 AI 分数、维度分、扣分项、证据、训练诊断、改进趋势和“最高可追回约 X 分”。不向普通用户展示 LLM 原始分或 Shadow 分。

## 3. 正式计分契约

每个 Observation 必须包含：

- `observationCode` 和对应 Rubric 版本；
- `maxScore`；
- 扣分前的 `baseScore`；
- 由证据等级决定的 `scoreCap`；
- 证据等级、证据锚点、理由和置信度。

每个 Deduction 必须包含：

- 后台稳定生成的 `deductionId`；
- `deductionRuleCode` 和 `observationCode`；
- 扣分类型、扣分值、理由、证据锚点；
- 修复要求、验收条件和最高可追回值。

单项计分公式：

```text
finalObservationScore =
  max(0, min(baseScore - activeDeductions + verifiedRecoveries, scoreCap))
```

总分是所有 `finalObservationScore` 之和。`baseScore` 必须是扣分前分数，禁止模型先将扣分融入 `baseScore` 后再由规则引擎重复扣减。

## 4. 证据与发布门禁

每个高影响判断必须绑定当前 Session 的有效证据。Rubric 配置决定不同证据等级下的不得分或封顶。

发布前强制校验：

- 维度合计与总分一致；
- 展示扣分与有效扣分合计一致；
- 每个扣分项存在合法 Rubric 规则和当前证据；
- 最终分不超过证据封顶和总分上限；
- Python 正式分与 Java 复算分一致。

任一校验失败时进入 `calculation_failed` 或 `review_required`，不发布用户分数。

## 5. 多轮路演

同一评分链由项目、团队、赛事、组别、赛道和可兼容 Rubric 版本组成。每轮先独立评分，再对最近上一轮的扣分项进行当前证据复检。

改善状态为 `not_checked` / `not_fixed` / `partially_fixed` / `verified_fixed` / `regressed`。只有 `verified_fixed` 可成为正式已改善结论。

“最高可追回约 X 分”通过规则引擎情景复算产生，不是简单求和。页面同时显示“最终以重新评分结果为准”。

## 6. 稳定性策略

短期不依赖专家校准集或黄金视频集。使用：

- 由 42 赛道配置自动生成的规则边界测试；
- 少量结构化 JSON 测试夹具；
- 真实评分的后台影子复算；
- 低置信度、证据冲突或边界分数的条件式双跑；
- 相同证据快照的抽样重算。

## 7. 分期

1. P0：Python 正式规则分、Java 复算门禁、报告对账。
2. P1：评分链、历史快照、稳定扣分 ID、防重复追回。
3. P2：管线拆分、条件式双跑、训练诊断和稳定性监控。
4. P3：影子放量、赛道逐步切换和快速回退。

