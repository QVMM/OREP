# 五维大模型分阶段完整输出设计

## 1. 背景与根因

现有 `llm_scoring_service.score_roadshow` 在一次 DeepSeek 请求中同时要求输出：15 个评分观测点、证据审计、9 位评委、音画融合、结构对标、评委追问、行动计划、团队优化和最终结论。

2026-07-13 的 54 分钟真实视频运行中，DeepSeek 返回 8001 completion tokens，命中当前 `max_tokens=8000` 边界，JSON 在 18,035 字符处被截断。解析失败后，现有回退将 `overall_score` 设为 0，导致无效分数继续流入报告。

根因是单次响应承载了过多独立报告模块，而不是转写文本过长或 JSON 解析器本身异常。

## 2. 设计目标

1. 15 个核心观测点的分数、理由和改进建议不缩减。
2. 9 位评委、证据审计、结构对标、追问、行动计划等深度报告模块不缩减。
3. 单个模型响应不再接近 8000-token 边界。
4. 任一阶段失败时只重试该阶段，不重跑 ASR、视觉分析或其他已成功阶段。
5. 无法获得完整核心评分时，结果必须是 `review_required`，不得伪造 0 分。
6. 最终大模型原始分由 Python 根据 15 项子分重新求和，模型输出的总分不作为信任来源。

## 3. 总体架构

五维分析拆分为三个顺序阶段，共享同一份输入证据快照。

### 3.1 阶段 A：核心评分

输入：

- 赛事、赛道和时长口径。
- 完整 ASR 转写。
- 语音质量数据。
- 视觉与音画融合证据。
- 15 个观测点的完整梯度规则。

输出：

- `score_overview`。
- 5 个维度、15 个观测点的分数、理由、改进建议。
- `highlights`。
- `critical_issues`。
- `evidence_summary`。
- `improvement_priorities`。

阶段 A 是唯一的大模型原始分来源。其他阶段不得改动评分。

### 3.2 阶段 B：证据与结构深度分析

输入：共享证据快照 + 阶段 A 的核心评分摘要。

输出：

- `evidence_audit`。
- `audio_visual_fusion`。
- `pitch_structure_benchmark`。
- `judge_questioning`。

阶段 B 必须引用阶段 A 的观测点名称和已绑定证据，不得重新评分。

### 3.3 阶段 C：评委与行动方案

输入：阶段 A 核心评分 + 阶段 B 的证据与结构结论。

输出：

- 完整 9 位评委的 `jury_review`。
- `action_plan`。
- `team_optimization`。
- `final_verdict`。

9 位评委必须保持独立关注点，不得因分阶段而减少人数或字段。

## 4. 组件边界

### 4.1 `scoring_prompt_contracts.py`

新建独立的 Prompt 与输出契约模块，包含：

- 阶段 A/B/C 的输出 schema 文本。
- 阶段 A/B/C 的用户 Prompt 构建器。
- 输入证据快照构建器。

该模块不调用模型，不处理网络重试。

### 4.2 `llm_stage_runner.py`

新建通用阶段执行器，负责：

- 调用 OpenAI-compatible chat completion。
- 记录 `finish_reason`、completion tokens、响应字符数和阶段编号。
- 检测截断：`finish_reason == "length"`、completion tokens 贴近上限、JSON 未闭合。
- 仅对当前阶段执行最多 2 次重试。
- 第一次失败时使用“同一字段完整重生成”提示，禁止通过删减数组、理由或建议缩短输出。

不使用字符级 JSON 猜测修复作为正常成功路径。被截断的评分 JSON 不得部分采信。

### 4.3 `llm_scoring_service.py`

`score_roadshow` 保持对外签名和最终返回结构不变，内部改为：

1. 构建一次共享证据快照。
2. 运行阶段 A 并通过核心契约验证。
3. 运行阶段 B。
4. 运行阶段 C。
5. 确定性合并三个对象。
6. 自下而上重算维度分和总分。
7. 写入 `generation_meta`，保留每阶段的尝试次数、tokens 和完整性状态。

## 5. 输出契约与完整性门禁

### 5.1 核心评分门禁

阶段 A 必须满足：

- 5 个固定维度全部存在。
- 15 个固定观测点全部存在且仅出现一次。
- 每项具有 `score`、`max_score`、非空 `reason`、非空 `improvement`。
- 观测点满分之和为 100。
- 每个分数位于 `[0, max_score]`。
- Python 重算的维度分之和与总分一致。

任一条不满足时，阶段 A 失败，禁止生成可发布分数。

### 5.2 深度报告门禁

阶段 B 必须包含 4 个完整模块。阶段 C 必须包含 9 位评委和 3 个行动/结论模块。

阶段 B 或 C 经两次尝试仍失败时：

- 核心分数可保留为 `scoring_completed_report_review_required`。
- 不使用泛化模板冒充模型完整分析。
- 失败模块显式标记为待重生成，背景任务可仅重跑该阶段。

## 6. Token 与并发策略

- 阶段 A 上限：5000 completion tokens。
- 阶段 B 上限：4500 completion tokens。
- 阶段 C 上限：5500 completion tokens。
- 不通过降低理由数量、评委数量或建议数量来满足上限。
- 阶段 B 依赖 A，阶段 C 依赖 A+B，因此三阶段顺序执行；单阶段内不拆分为不可复算的多个竞争分数。

## 7. 失败状态

### 7.1 核心评分失败

返回：

```json
{
  "overall_score": null,
  "status": "review_required",
  "score_authority": "none",
  "error_code": "core_scoring_incomplete",
  "dimensions": {},
  "generation_meta": {
    "core": {"status": "failed", "attempts": 2}
  }
}
```

禁止返回 `overall_score: 0`，因为 0 分是业务判定，不是技术失败状态。

### 7.2 深度报告失败

保留通过门禁的核心分数，状态为 `scoring_completed_report_review_required`，且不允许报告生成器将缺失模块包装成完整报告。

## 8. 测试设计

### 8.1 单元测试

1. 阶段 A 完整响应通过契约并重算总分。
2. 阶段 A 缺少任一观测点时拒绝发布。
3. `finish_reason=length` 即使 JSON 恰好可解析，仍视为截断风险并重试。
4. JSON 未闭合时仅重试当前阶段。
5. 第二次仍失败时返回 `overall_score=null`，不返回 0。
6. 阶段 B 缺少模块时不影响阶段 A 分数，但最终报告状态不可标记为完整。
7. 阶段 C 评委数不是 9 时重试，禁止自动复制填满。
8. 合并器不允许 B/C 覆盖 `dimensions` 或 `overall_score`。

### 8.2 真实长视频回归

使用：

`/Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4`

复用已生成的 246 个 ASR 片段和 110 帧视觉分析结果，只重跑五维评分阶段。验收：

- 三阶段均产生合法 JSON。
- 没有任一阶段命中 completion token 上限。
- 完整 15 个观测点、9 位评委、4 个证据/结构模块、3 个行动/结论模块。
- 最终总分等于 15 个观测点子分之和。
- 不存在技术失败生成的 0 分。

## 9. 兼容性

- `score_roadshow` 公开函数签名保持不变。
- 成功时的顶层业务字段保持不变。
- 新增 `status`、`generation_meta`和 `error_code` 用于可观测性。
- 旧调用方仍可读取 `dimensions`、`overall_score`、`critical_issues` 和 `improvement_priorities`。

## 10. 非目标

- 不修改当前 42 赛道评分规则。
- 不调整观测点分值或证据封顶逻辑。
- 不引入第二个模型作为隐式分数修正。
- 不以减少报告字段、评委数量或理由长度作为解决手段。

## 11. 验收标准

1. 模拟 8000-token 截断时，只重试失败阶段。
2. 两次失败后不生成 0 分。
3. 成功结果同时包含 15 个观测点和 9 位评委。
4. 成功结果包含原有全部深度分析模块。
5. 各阶段的 tokens、尝试次数、截断检测结果可审计。
6. 真实 54 分钟视频的五维评分不再因响应截断回退为 0。
