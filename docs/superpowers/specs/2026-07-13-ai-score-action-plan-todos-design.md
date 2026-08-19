# AI 评分行动计划待办合并设计

## 背景与目标

会话 26 的 Python 评分结果已生成 6 条 `ai_score.action_plan`，但完成回调、Java 持久化与正式报告 API 未携带该字段。Java 只按结构化扣分生成 `trainingTasks`，前端又在存在任何 `trainingTask` 时停止补充其他整改来源，因此页面只显示 1 条待办。

本改动将建立稳定的端到端行动计划契约，把行动计划与结构化扣分任务合并为用户可理解的唯一待办队列。

## 方案选择

### 采用：独立持久化 + 统一展示层合并

- Python 回调增加 `actionPlanJson`，完整保留模型的结构化行动计划。
- Java 报告表新增 `action_plan_json` LONGTEXT，回调 DTO、实体、持久化和用户报告 API 统一使用 `actionPlanJson` / `actionPlan`。
- Java 仍保留 `trainingTasks` 作为“与真实扣分直接关联”的权威任务来源。
- 前端统一待办组装器同时合并 `trainingTasks` 和 `actionPlan`，去重后得到唯一队列。

不采用从 `improvementPriorities` 临时合成六条待办，因为它只有三条且结构不完整；不采用前端直读本地 `result_*.json`，因为该路径不适用于生产环境。

## 数据契约

`actionPlan` 每项支持：

- `id`：稳定行动项 ID。缺失时由 Python 用优先级、标题和问题文本生成确定性 ID。
- `priority`：`P0 | P1 | P2`。
- `title`、`problem`、`method`、`owner`、`timebox`、`acceptance`：用户整改所需完整字段。
- `observationCode`：可选，指向评分观测点。
- `sourceIssueKey`：可选，指向生成该行动的问题或扣分来源。
- `evidenceAnchorIds`：可选，用于与评分证据对齐。

Java 报告 API 同时返回：

- `actionPlanJson`：为兼容现有 JSON 字段模式保留的原始 JSON。
- `actionPlan`：解析后的对象数组，供前端直接消费。
- `trainingTasks`：继续只来自活动中的结构化扣分。

## 合并与去重规则

统一待办队列按以下顺序收集：

1. 结构化扣分任务 `trainingTasks`。
2. 正式报告的 `actionPlan`。
3. 表达和现场呈现训练项（仅当它们不与前两者重复时）。
4. 旧数据的工作项草稿和改进优先项只作为兼容回退。

去重使用三级键：

1. 两项具有相同 `observationCode` 时视为同一观测点问题。
2. 否则，具有相同 `sourceIssueKey` 时视为同一来源问题。
3. 旧数据缺少结构化键时，对 `title + problem` 进行规范化关键词指纹匹配；仅在有明确共享问题核心词时合并，避免把不同整改误删。

合并发生时，结构化扣分任务为主记录，补入行动计划的方法、负责人、时间和验收标准。不把两条记录累加计数。

## 分数展示规则

- `expectedRecoverPoints` 只能来自有效结构化扣分。
- 行动计划本身不接受、不推导、不累加可追回分数。
- 合并项若与结构化扣分成功对齐，可显示该扣分的“最高可追回约 X 分”。
- 其他诊断性行动只显示问题、整改方法和验收标准。

## 前端展示

- 顶部“待办 N”使用统一队列去重后的总数。
- 结果页“先做这三件”按 P0、P1、P2 和原始顺序排序，最多展示三条。
- 结果页的“还有 N 件”使用 `总数 - 3`。
- 待办页展示统一队列全部内容。
- Python 二次提分接口的 `training_tasks` 作为额外训练建议源可被识别，但不替代正式持久化的 `actionPlan`。

## 兼容与错误处理

- 历史报告 `action_plan_json` 为空时，API 返回空数组，页面仍可使用 `trainingTasks` 和旧回退源。
- 非法 JSON 不中断报告读取，Java 返回空 `actionPlan` 并保留原报告其他字段。
- Python 回调对行动计划只做结构归一化和确定性 ID 生成，不删减模型已生成的条目。

## 测试与验收

- Python 契约测试证明六条行动计划完整进入 `actionPlanJson`。
- Java 回调测试证明 `action_plan_json` 被持久化，报告 API 同时返回 JSON 和解析数组。
- 前端单元测试覆盖：6 条计划 + 1 条重复扣分任务合并后不是 7；只有扣分关联项有可追回分；顶部计数使用完整队列；结果页取前三；待办页保留全部。
- 会话 26 通过现有 `result_26.json` 重放完成回调，不重跑视频；验证报告 40 的行动计划已持久化并在用户端正确合并。

