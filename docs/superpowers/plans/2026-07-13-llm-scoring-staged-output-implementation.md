# 五维大模型分阶段完整输出实施计划

**目标：** 消除单次 8000-token 响应截断，同时保留 15 个观测点、9 位评委和全部深度报告模块；技术失败不得再伪装成 0 分。

**架构：** `score_roadshow` 保持公开签名不变。新增 Prompt 契约模块和通用阶段执行器，依次生成核心评分、证据/结构分析、评委/行动方案，逐阶段校验并确定性合并。核心分由 Python 根据 15 项子分重算。

## 任务 1：阶段执行器（测试先行）

- 新增 `tests/test_llm_stage_runner.py`，覆盖 `finish_reason=length`、非法 JSON、仅重试当前阶段、两次失败及审计元数据。
- 新增 `app/services/llm_stage_runner.py`，统一调用、截断检测、JSON 解析、阶段级重试和 token 审计。

## 任务 2：三个输出契约（测试先行）

- 新增 `tests/test_scoring_prompt_contracts.py`，覆盖 5 维 15 项完整性、分数边界、B 阶段四模块、C 阶段九评委与三个行动模块。
- 新增 `app/services/scoring_prompt_contracts.py`，提供共享证据快照、A/B/C Prompt 构建器、校验器和确定性合并器。

## 任务 3：接入主评分逻辑（测试先行）

- 新增 `tests/test_llm_scoring_staged_output.py`，以假客户端验证三次阶段调用、B/C 不可覆盖分数、核心失败返回 `overall_score=null`、深度失败保留核心分但标记待复核。
- 修改 `app/services/llm_scoring_service.py`，将单次 8000-token 调用替换为 A/B/C 顺序执行，并写入 `generation_meta`。
- 移除成功路径上的深度模块模板补齐；缺失模块必须显式标记待重生成。

## 任务 4：流水线失败语义与兼容验证

- 调整流水线对 `review_required` 的判断，避免将 `null` 分数继续包装为完成报告。
- 运行新增测试、相关评分/报告测试和 Python 全量测试。

## 任务 5：长视频回归

- 复用会话 25 已生成的 ASR、语音与视觉结果，仅重跑五维生成阶段。
- 验证 15 个观测点、9 位评委、完整深度模块、阶段 token 审计及非 0 技术失败语义。
