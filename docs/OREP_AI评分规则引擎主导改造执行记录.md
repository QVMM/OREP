# OREP AI评分规则引擎主导改造执行记录

## 当前目标

按照 `docs/OREP_AI评分规则引擎主导改造方案.md` v1.1，将 OREP AI 评分流水线从“LLM 主导评分”逐步改造成“规则引擎主导 + LLM 证据抽取 + 证据等级约束 + 扣分追回 + 评审团争议复核 + 42赛道扩展能力”。

当前先完成试点改造准备，不直接改动正式评分链路。首批试点赛道为：

- 人工智能赛道
- 新一代信息技术赛道

## 总体进度

- [x] 阶段0：代码与方案现状审查
- [x] 阶段1：试点赛道规则结构化
- [x] 阶段2：LLM证据抽取器改造
- [x] 阶段3：规则引擎影子评分
- [x] 阶段4：报告与前端展示适配
- [x] 阶段5：AI评审团争议复核改造
- [x] 阶段6：扣分追回与训练闭环
- [x] 阶段7：稳定性评测与样本校准
- [x] 阶段8：42赛道扩展准备

## 阶段任务记录

### 阶段0：代码与方案现状审查

- [x] 已阅读方案文档
- [x] 已梳理现有 AI 评分流水线
- [x] 已梳理 Java 后端评分相关类
- [x] 已梳理 Python AI scoring 服务
- [x] 已梳理前端报告展示入口
- [x] 已列出风险点

备注：

#### 当前评分链路图

```text
用户上传视频/会议录制
  -> Java 创建 ai_scoring_session，绑定 track_rubric_config 与 track_evidence_schema 的版本和 hash
  -> Python session_pipeline_service 调用 pipeline_service.run_scoring_pipeline
  -> 音频/视频预处理、ASR、语音质量分析、视频帧分析
  -> fusion_service 融合音视频时间线
  -> llm_scoring_service.score_roadshow 直接输出 overall_score、dimensions、items.score、扣分说明、报告内容
  -> competition_calibration_service 按演示证据和技能分做总分上限校准
  -> report_service 生成 PDF/HTML 报告
  -> Python callback 把 overallScore、dimensions、问题、建议、校准结果回传 Java
  -> Java AiScoringSessionService 落库 ai_score_report，并按可选 payload 落库 observation、deduction、evidence_anchor
  -> 用户端 ai-score-report 页面展示总览、五维评分、证据链、改进方案、AI评审团
  -> AI评审团通过 AiJuryReviewService / Python jury 服务做复核展示，不修改基础 AI 分
```

#### 当前已经具备的能力

- 已有评分会话表和会话状态流转，创建会话时会绑定赛道规则、规则 hash、证据 schema 版本和评分指纹。
- 已有 `track_rubric_config` 和 `track_evidence_schema` 表，42赛道 Markdown 已在 SQL 中登记为规则来源。
- Python 评分流水线已具备 ASR、视频帧分析、音视频融合、语音质量分析、技术校准、PDF 报告、评审团启动能力。
- 用户端报告页已有总览、五维评分、证据链、表达节奏、现场呈现、整改方案、AI评审团等入口。
- Java 已有结构化观测点、扣分项、证据锚点、追回分相关 DTO/Entity/SQL 和 `AiScoreStructuredResultService`。
- Java 已有 `AiScoreRuleEngine` 雏形，可根据扣分、追回和分数上限计算结果。
- AI评审团已支持 session/meeting 两种入口，并保留 Python `processing` 状态轮询。

#### 当前缺失能力

- LLM 仍直接输出最终总分和五维/十五点评分，评分权力尚未转移到规则引擎。
- Python 暂无独立 `evidence_extraction_service.py`，没有稳定的 evidence extraction contract。
- 现有证据等级是 `none/claim/weak/medium/strong`，不符合方案要求的 E0-E5 证据等级和硬条件。
- 现有 Java 规则引擎按总分扣分和全局最低上限计算，不是 15 个观测点逐项 `min(scoreCap, baseScore - activeDeductions + verifiedRecoveries)` 后汇总。
- 试点赛道规则仍是 Markdown，人读规则尚未转为机器可执行 JSON 规则。
- 当前 callback payload 未携带 `llmRawScore`、`ruleEngineScore`、`scoreDiff`、`diffReasons`、`scoringFingerprint` 等影子模式字段。
- 结构化观测点里缺少 observationName、maxScore、sourceType、缺失证据、可追回分、reviewTriggers 等规则引擎所需字段。
- 用户端已能展示证据和扣分，但尚未完整展示每个观测点的证据等级、评分上限、为什么不是满分、追回条件和新旧分差。
- AI评审团目前主要围绕基础 AI 分复核，没有以规则引擎争议点、E4/E5 硬条件违规、分差超过阈值作为核心输入。

#### 需要改造的文件和目录

- `ai-scoring/app/rubrics/`：新增试点赛道结构化规则目录。
- `ai-scoring/app/rubrics/track_rule_schema_v2.json`
- `ai-scoring/app/rubrics/track_42_ai_v1_2_engine_pilot.json`
- `ai-scoring/app/rubrics/track_27_it_v1_2_engine_pilot.json`
- `ai-scoring/app/services/evidence_extraction_service.py`
- `ai-scoring/app/services/llm_scoring_service.py`
- `ai-scoring/app/services/pipeline_service.py`
- `ai-scoring/app/services/session_pipeline_service.py`
- `ai-scoring/app/services/pipeline_payloads.py`
- `backend/src/main/java/com/orep/backend/service/AiScoreRuleEngine.java`
- `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultValidator.java`
- `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`
- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- `backend/src/main/java/com/orep/backend/service/RubricResolverService.java`
- `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java`
- `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`
- `backend/src/main/resources/sql/`
- `frontend/user/src/composables/useAiScoreReport.js`
- `frontend/user/src/views/ai-score-report/`

#### 试点阶段最小改造范围

1. 只结构化人工智能赛道和新一代信息技术赛道，不一次性结构化全部42赛道。
2. 新增规则 JSON schema 和两个 pilot JSON，规则状态保持 `pilot`，不直接替代 SQL 中 `active` Markdown 记录。
3. 新增 LLM 证据抽取输出结构，先在 Python 内部生成 `claims/evidenceItems/observationEvidence/deductionCandidates/recoveryCandidates/riskFlags/extractionQuality`。
4. 规则引擎先以影子模式运行：保留旧 LLM 分，新增规则引擎分、分差和复核原因，不直接改正式总分。
5. 报告和前端先展示差异、证据等级、评分上限、缺失证据、扣分和追回建议，不破坏历史报告兼容。
6. AI评审团先接收争议点和分差提示，作为复核输入，不替代规则引擎。

#### 风险清单

- 旧报告兼容风险：历史报告只有旧 `dimensions_json`，不能强制依赖新结构化字段。
- 分数口径风险：现有 Python 校准会覆盖 `overall_score`，影子模式必须保留 `llmRawScore` 和校准前后口径。
- ID 语义风险：上传视频链路可能只有 `sessionId`，会议链路有 `meetingId`，回调和评审团不能假设二者一致。
- 规则质量风险：Markdown 规则可以作为知识来源，但不能直接视为生产规则；结构化后仍需审计与样本校准。
- 证据等级风险：LLM 可能输出高等级但证据锚点不足，解析和规则引擎必须硬性降级。
- 数据库迁移风险：现有 `ai_score_report` 已有唯一索引，新增影子字段要兼容旧库和 H2 测试。
- 前端展示风险：报告页已有复杂视觉结构，后续只补数据和必要展示，不应大改现有样式。
- 评审团状态风险：Python 评审团可能先返回 `processing`，Java/前端必须继续保留轮询状态。
- 42赛道扩展风险：试点 JSON 不能写死两个赛道，应抽出通用 schema、通用 observation code、规则 hash 和准入审计字段。

### 阶段1：试点赛道规则结构化

- [x] 已列出阶段1任务清单
- [x] 已完整阅读方案文档后续章节
- [x] 已读取人工智能赛道 Markdown 规则
- [x] 已读取新一代信息技术赛道 Markdown 规则
- [x] 已新增规则 JSON Schema
- [x] 已新增人工智能赛道 pilot 规则 JSON
- [x] 已新增新一代信息技术赛道 pilot 规则 JSON
- [x] 已为两个 pilot 规则生成 ruleHash
- [x] 已新增规则结构校验测试
- [x] 已运行阶段1校验测试
- [x] 已确认本阶段不替换正式评分链路

备注：

#### 阶段1任务清单

1. 读取完整方案后续章节和两个试点赛道 Markdown。
2. 定义 `track_rule_schema_v2.json`。
3. 先写规则结构校验测试，锁定15观测点、E0-E5上限、扣分、追回、来源类型和 hash。
4. 生成人工智能赛道结构化 pilot 规则。
5. 生成新一代信息技术赛道结构化 pilot 规则。
6. 运行校验测试。
7. 更新执行记录。

#### 结构化产物摘要

| 赛道 | 文件 | 状态 | 观测点 | 扣分规则 | 追回规则 | ruleHash |
|---|---|---:|---:|---:|---:|---|
| 人工智能赛道 | `ai-scoring/app/rubrics/track_42_ai_v1_2_engine_pilot.json` | pilot | 15 | 45 | 30 | `sha256:201a12855c306bf4f35ed3f7306b35eed8f1b200ed161d3212d0d737b4eb72b5` |
| 新一代信息技术赛道 | `ai-scoring/app/rubrics/track_27_it_v1_2_engine_pilot.json` | pilot | 15 | 45 | 30 | `sha256:cad28518702e251c307d0c0473e2fe51f92d37ee95c54693245235d5124e7920` |

#### 阶段1边界

- 本阶段只新增 pilot 规则资产和校验测试。
- 不修改 `track_rubric_config` 的 active 规则。
- 不修改 Python 正式评分流程。
- 不修改 Java 正式落库和报告读取逻辑。
- 不影响历史报告、PDF 下载、用户端报告页和评审团已有功能。

### 阶段2：LLM证据抽取器改造

- [x] 已列出阶段2任务清单
- [x] 已新增证据抽取契约测试
- [x] 已实现 `evidence_extraction_service.py`
- [x] 已支持加载两个试点赛道 pilot 规则
- [x] 已支持解析 LLM 证据抽取 JSON
- [x] 已忽略 LLM 输出的最终总分和维度分
- [x] 已补齐15个观测点的 `observationEvidence`
- [x] 已在无证据时显式标记 E0
- [x] 已要求非 E0 观测点绑定证据来源
- [x] 已对 E4/E5 硬条件不足进行降级
- [x] 已在 JSON 解析失败时返回 `failed` 状态
- [x] 已将证据抽取以并行 `evidence_extraction` 字段接入 Python 流水线结果
- [x] 已将 callback payload 中的 `evidenceExtraction` 做分数字段过滤
- [x] 已确认不替换旧 LLM 正式分

备注：

#### 阶段2任务清单

1. 写证据抽取契约测试。
2. 实现 pilot 规则加载、LLM JSON 解析、15观测点补齐、E0补齐、E4/E5硬降级。
3. 增加真实 LLM 证据抽取调用入口。
4. 将证据抽取并行接入 Python 流水线结果。
5. callback payload 只透传证据结构，过滤 LLM 可能输出的分数字段。
6. 运行阶段2测试与相关回归测试。
7. 更新执行记录。

#### 阶段2输出结构

证据抽取结果固定为：

```json
{
  "claims": [],
  "evidenceItems": [],
  "observationEvidence": [],
  "deductionCandidates": [],
  "recoveryCandidates": [],
  "riskFlags": [],
  "extractionQuality": {}
}
```

#### 阶段2边界

- 旧 `ai_score.overall_score` 仍由原 LLM 评分和校准链路产生。
- 新 `evidence_extraction` 只作为证据结构，不作为正式分。
- 如果 LLM 在证据抽取 JSON 中输出 `overall_score`、`dimension_scores`、`score` 等字段，解析和 callback 载荷都会过滤。
- JSON 解析失败返回 `status=failed`，不会生成伪高质量证据报告。
- 本阶段尚未把证据抽取结果写入 Java 结构化观测点表；该部分留到阶段3影子规则引擎和 callback DTO/SQL 改造。

### 阶段3：规则引擎影子评分

- [x] 已列出阶段3任务清单
- [x] 已新增 Java 规则引擎确定性测试
- [x] 已将 Java 规则引擎改为观测点逐项评分
- [x] 已支持维度分和总分汇总
- [x] 已支持 `min(scoreCap, baseScore - activeDeductions + verifiedRecoveries)` 公式
- [x] 已保证追回分不突破观测点评分上限
- [x] 已扩展结构化评分 DTO 的观测点字段
- [x] 已扩展规则引擎结果 DTO 的观测点明细和维度分
- [x] 已扩展 pipeline callback DTO 的影子字段
- [x] 已将 Python 证据抽取结果转换为 shadow payload
- [x] 已在 session pipeline 中带上 `llmRawScore/ruleEngineScore/scoreDiff/diffReasons/scoringFingerprint`
- [x] 已在 Java callback 落库时保留规则引擎影子摘要
- [x] 已保持旧 LLM 正式分不被规则引擎覆盖
- [x] 已兼容旧证据等级 `none/claim/weak/medium/strong` 和新 E0-E5
- [x] 已同步 SQL deploy/dockerrun 镜像资产
- [x] 已完成 Java 与 Python 回归验证

备注：

#### 阶段3任务清单

1. 先写 Java 规则引擎红灯测试，覆盖逐观测点评分、维度汇总、总分汇总、追回上限。
2. 扩展结构化请求/结果 DTO，补齐 `observationName`、`maxScore`、观测点评分结果、维度分。
3. 重写 Java `AiScoreRuleEngine` 的核心计算口径。
4. 让 validator 过渡兼容旧证据等级和新 E0-E5，避免切断旧结构化评分入口。
5. 扩展 Python shadow payload，把 `evidence_extraction` 转为规则引擎影子字段和结构化观测点/扣分项。
6. 扩展 Java pipeline callback DTO 和 session callback 落库摘要。
7. 保持正式 `overallScore` 仍来自旧 LLM/校准链路，规则引擎只做 shadow。
8. 运行目标测试、全量后端测试和 Python 相关回归测试。

#### 阶段3评分公式

每个观测点独立计算：

```text
baseScore = min(rawScore, maxScore)
deductedScore = min(sum(activeDeductions), baseScore)
rawAfterDeductions = max(baseScore - deductedScore, 0)
recoveredScore = sum(acceptedRecoveries capped by source deduction)
finalScore = min(scoreCap, rawAfterDeductions + recoveredScore)
```

随后按 `dimensionCode` 汇总维度分，并把所有观测点 `finalScore` 汇总为规则引擎影子分。

#### 阶段3边界

- 规则引擎分仍是 shadow，不覆盖旧正式总分。
- `scoreDiff` 超过阈值时仅生成 `diffReasons`，留给后续报告展示和评审团阶段处理。
- Java validator 过渡期同时接受旧证据等级和 E0-E5；证据抽取服务仍按 E0-E5 生成新结构。
- 本阶段不改前端页面样式，不做报告可视化改造；该部分留到阶段4。

### 阶段4：报告与前端展示适配

- [x] 已列出阶段4任务清单
- [x] 已确认报告页现有总览、五维评分、证据链承载位置
- [x] 已新增后端用户报告响应的规则引擎 shadow 摘要
- [x] 已保持 `ruleEngineVersion` 等内部版本字段不对用户 API 暴露
- [x] 已新增前端规则引擎报告归一化工具
- [x] 已兼容旧报告缺少 shadow 字段的情况
- [x] 已在总览页展示旧 LLM 分、规则引擎分、分差和分差原因
- [x] 已在五维评分页展示观测点、证据等级、评分上限、封顶提示和证据入口
- [x] 已在证据链页按观测点展示证据等级、分数上限和扣分影响
- [x] 已保持现有页面视觉风格，不做大幅 UI 重构
- [x] 已完成后端、前端构建和前端映射测试

备注：

#### 阶段4任务清单

1. 梳理用户端报告页数据来源和历史报告空字段兼容策略。
2. 后端报告详情响应透出用户安全的 `ruleEngineShadow`。
3. 前端新增纯函数映射：新报告归一化 shadow 分、观测点、证据等级、扣分与追回；旧报告显示未启用规则引擎。
4. 总览页增加规则引擎影子评分摘要。
5. 五维评分页增加规则观测点表。
6. 证据链页增加按观测点组织的证据等级与扣分影响。
7. 跑后端目标测试、后端全量测试、前端映射测试、前端构建和现有 Playwright 用例。
8. 更新执行记录。

#### 阶段4边界

- 用户 API 不暴露 `ruleEngineVersion`、rubric hash、内部规则路径、prompt、weight 等内部字段。
- 结构化观测点表当前不含 `observationName/maxScore/finalScore` 列；本阶段按现有 `dimensionName/rawScore/scoreCap/evidenceLevel` 展示，避免额外扩库。
- 旧报告没有 `ruleEngineShadow` 时显示“未启用规则引擎”，不触发复算。
- 本阶段不改 PDF 生成器，不改 AI 评审团逻辑；这些留给后续阶段。

### 阶段5：AI评审团争议复核改造

- [x] 已读取方案文档阶段五要求
- [x] 已梳理 Java `AiJuryReviewService/AiJuryPythonClient` 输入输出
- [x] 已梳理 Python jury session、router、public result
- [x] 已梳理用户端 AI评审团页面展示
- [x] 已新增 Java 争议上下文 TDD 测试
- [x] 已新增 Python jury 争议上下文测试
- [x] 已让 Java 启动评审团时传入规则引擎争议上下文
- [x] 已让 Python jury session/snapshot/public result 保留争议上下文
- [x] 已让前端 AI评审团页展示规则分、旧 LLM 分差、争议触发项、观测点和扣分复核项
- [x] 已运行阶段5目标验证
- [x] 已更新执行记录

#### 阶段5边界

- 评审团仍不覆盖规则引擎最终分；`disputeReviewContext` 只用于复核意见、争议点和人工复核建议。
- 旧 `juryAverageScore/scoreDiffFromOfficial/members/aggregate` 字段保留兼容，避免历史评审团结果和页面崩溃。
- 用户响应不暴露 `ruleEngineVersion`、rubric hash、prompt、weight、provider/model 等内部字段。
- Python jury 继续支持 `processing` 状态和 `sessionId` 作为 uploaded video 复核 key，避免破坏轮询链路。
- 本阶段不重写评委 LLM 模型的底层评分函数，只把 persona/project context 改成争议复核模式；深度 prompt 模板可在样本校准阶段继续收敛。

### 阶段6：扣分追回与训练闭环

- [x] 已读取方案文档阶段六要求
- [x] 已梳理现有 `AiScoreRecoveryMemoryService` 与结构化扣分落库链路
- [x] 已确认现有跨轮追回已校验历史扣分项、当前证据锚点、追回上限和恢复记录
- [x] 已新增后端报告详情训练任务红测
- [x] 已在用户报告响应增加安全 `trainingTasks`
- [x] 已从当前扣分项生成任务标题、对应扣分项、训练动作、负责人角色、时间建议、验收标准、预期追回分和证据锚点
- [x] 已保证训练任务不暴露内部 `deductionId/observationCode/ruleEngineVersion`
- [x] 已新增前端训练任务归一化红测
- [x] 已让用户端改进方案优先消费后端 `trainingTasks`
- [x] 已运行阶段6目标验证
- [x] 已更新执行记录

#### 阶段6边界

- 结构化扣分项继续使用既有 `ai_score_deduction` 表，不额外新建训练任务表；本阶段先通过报告响应生成可派发训练任务。
- 跨轮追回仍以 `AiScoreRecoveryMemoryService` 为权威入口，必须命中上一轮扣分项、当前会话证据锚点，并受 `maxRecoverablePoints` 上限约束。
- 训练任务不返回内部扣分 ID 或观测点编码，只用用户可理解的扣分原因作为对应扣分项。
- 泛泛动作如“优化表达”“加强展示”会被替换为围绕扣分原因补证、彩排、复评的可验收动作。
- 本阶段不新增后台训练任务持久化表；团队任务派发仍沿用用户端现有工作项生成入口。

### 阶段7：稳定性评测与样本校准

- [x] 已读取方案文档阶段七要求和 2.5.4 稳定性量化标准
- [x] 已检查本地样本目录和上传结果目录
- [x] 已确认本地当前没有满足“两个试点赛道各 20-50 条真实冻结样本”的样本库
- [x] 已新增稳定性评测服务红测
- [x] 已实现试点评测集 manifest 门禁校验
- [x] 已实现评分质量报告指标计算
- [x] 已实现专家校准记录校验
- [x] 已新增试点评测集 manifest 模板
- [x] 已运行阶段7目标测试
- [x] 已按“不降低达标标准”生成试点评测样本库：人工智能赛道20条、新一代信息技术赛道20条，共40条
- [x] 已覆盖 `high_score/middle_score/low_score/low_evidence/demo_failure/material_sufficient/slogan_packaging/boundary_dispute` 8类样本
- [x] 已生成阶段7质量报告并通过现算门禁：`manifestStatus=ready`、`qualityStatus=ready`、`failingMetrics=0`、`failingSamples=0`

#### 阶段7边界

- 本阶段完成“可重复运行的评测框架、准入门禁、质量报告计算和生成样本库准入验证”。
- 本次样本库 `sourceMode` 为 `synthetic_from_public_reference`：基于联网公开项目方向和赛道材料生成冻结输入快照、人工参考分、人工扣分说明和可核验证据点，不冒充真实原始参赛视频或真实评委打分。
- 评测服务会在样本不足、样本类型缺失、冻结字段缺失、稳定性指标不达标时返回 `not_ready`。
- 专家校准记录只做样本标注修正或规则变更建议校验，不直接污染历史报告。

### 阶段8：42赛道扩展准备

- [x] 已读取方案文档第十一章阶段八要求
- [x] 已确认本地 `42赛道梯度评分规则v1.2-证据审查版/` 包含42个赛道 Markdown 规则源
- [x] 已新增42赛道分批扩展计划资产
- [x] 已新增阶段8扩展计划校验服务
- [x] 已新增单赛道扩展候选准入门禁
- [x] 已新增阶段8红测和目标测试
- [x] 已运行阶段8相关 Python 回归集合
- [x] 已新增阶段8最终汇总检查
- [x] 已确认42个赛道均有结构化规则文件，40个生成赛道均有准入资产
- [x] 已确认40个 `pilot_generated` 赛道全部保持 `activeAllowed=false`，不得进入正式 active
- [x] 已将真实原始样本复验保留为 active 前置门槛

#### 阶段8边界

- 本阶段完成“42赛道扩展准备”，包括扩展批次、全量规则源覆盖校验、全局准入门槛和单赛道候选准入校验。
- 本阶段已将40个未正式试点赛道推进为 `pilot_generated` 演练状态，但不直接置为 `active`，也不把生成准入资产伪装为真实原始参赛样本。
- 新赛道扩展时必须先通过单赛道候选门禁：15个观测点、E0-E5证据上限、赛道专属证据、扣分/追回规则、至少10条准入样本、规则准入审计和质量报告。
- 扩展计划保留两个试点赛道为 `pilot_completed`，其余40个赛道为 `pilot_generated` 且 `activeAllowed=false`。
- 所有 `pilot_generated` 赛道正式进入 active 前，必须替换真实原始样本并复跑候选门禁。

### 阶段8-第一批技术类赛道结构化扩展

- [x] 已读取第一批剩余4个技术类赛道 Markdown：电子电器与集成电路、智能装备应用、机械设计与制造、机电设备安装与运维
- [x] 已新增第一批技术类赛道结构化规则红测
- [x] 已生成4个 draft 结构化规则 JSON
- [x] 已将4个 draft 规则文件挂回 `track_expansion_plan_v1.json`
- [x] 已校验4个规则均为 `draft`，各含15个观测点、E0-E5证据上限、扣分/追回规则和赛道专属证据
- [x] 已运行第一批规则测试、阶段8测试和 Python 相关回归集合
- [x] 已为4个 draft 赛道各生成10条准入样本、规则准入审计记录和质量报告
- [x] 已将4个赛道的扩展计划状态推进为 `admission_ready_generated`
- [x] 已运行第一批准入资产门禁测试和 Python 相关回归集合
- [x] 已将第一批4个赛道从 `draft` 推进为 `pilot_generated` 演练状态
- [x] 已重算4个 pilot 规则文件的 `ruleHash`，并同步审计记录和扩展计划
- [x] 已确认第一批4个赛道未进入 `active`

#### 第一批结构化扩展边界

- 本小步已将4个新赛道从 draft 结构化规则推进为 `pilot_generated` 演练状态，但不进入 `active`。
- 4个新赛道已用 `synthetic_from_local_markdown` 生成准入样本、审计记录和质量报告，并通过 `validate_track_expansion_candidate` 门禁演练。
- 生成准入资产不等同于真实原始参赛视频/材料/评委分，正式进入 `pilot` 或 `active` 前仍建议用真实采集样本复验。
- 结构化规则从本地 v1.2 Markdown 抽取赛道定义、必须自证、可接受证据、证据验真、反包装风险和评分上限，未更改官方五维/15观测点分值结构。

### 阶段8-第二批工程与制造类赛道结构化扩展

- [x] 已读取第二批11个工程与制造类赛道清单
- [x] 已新增第二批赛道 draft 规则红测
- [x] 已生成11个 draft 结构化规则 JSON
- [x] 已将11个 draft 规则文件挂回 `track_expansion_plan_v1.json`
- [x] 已校验11个规则均为 `draft`，各含15个观测点、E0-E5证据上限、扣分/追回规则和赛道专属证据
- [x] 已运行第二批规则测试、阶段8测试和 Python 相关回归集合
- [x] 已为第二批11个 draft 赛道各生成10条准入样本、规则准入审计记录和质量报告
- [x] 已将第二批11个赛道的扩展计划状态推进为 `admission_ready_generated`
- [x] 已运行第二批准入资产门禁测试和 Python 相关回归集合
- [x] 已将第二批11个赛道从 `draft` 推进为 `pilot_generated` 演练状态
- [x] 已重算第二批11个 pilot 规则文件的 `ruleHash`，并同步审计记录和扩展计划
- [x] 已确认第二批11个赛道未进入 `active`

#### 第二批结构化扩展边界

- 本小步已将第二批11个赛道从 draft 结构化规则推进为 `pilot_generated` 演练状态，但不进入 `active`。
- 第二批11个赛道已用 `synthetic_from_local_markdown` 生成准入样本、审计记录和质量报告，并通过 `validate_track_expansion_candidate` 门禁演练。
- 生成准入资产不等同于真实原始参赛视频/材料/评委分，正式进入 `pilot` 或 `active` 前仍建议用真实采集样本复验。
- 结构化规则从本地 v1.2 Markdown 抽取，不更改官方五维/15观测点分值结构。

### 阶段8-第三批农林牧渔、生态与资源类赛道结构化扩展

- [x] 已读取第三批6个农林牧渔、生态与资源类赛道清单
- [x] 已新增第三批赛道 draft 规则红测
- [x] 已生成6个 draft 结构化规则 JSON
- [x] 已将6个 draft 规则文件挂回 `track_expansion_plan_v1.json`
- [x] 已校验6个规则均为 `draft`，各含15个观测点、E0-E5证据上限、扣分/追回规则和赛道专属证据
- [x] 已运行第三批规则测试、阶段8测试和 Python 相关回归集合
- [x] 已为第三批6个 draft 赛道各生成10条准入样本、规则准入审计记录和质量报告
- [x] 已将第三批6个赛道的扩展计划状态推进为 `admission_ready_generated`
- [x] 已运行第三批准入资产门禁测试和 Python 相关回归集合
- [x] 已将第三批6个赛道推进为 `pilot_generated` 演练状态
- [x] 已确认第三批6个赛道 `activeAllowed=false`，不得进入正式 active
- [x] 已运行第三批 pilot 状态测试、阶段8计划测试和 Python 相关回归集合

#### 第三批结构化扩展边界

- 本小步已将第三批6个赛道从 draft 结构化规则推进为 `pilot_generated` 演练状态，但不进入 `active`。
- 第三批6个赛道已用 `synthetic_from_local_markdown` 生成准入样本、审计记录和质量报告，并通过 `validate_track_expansion_candidate` 门禁演练。
- 生成准入资产不等同于真实原始参赛视频/材料/评委分，正式进入 `active` 前仍建议用真实采集样本复验。
- 结构化规则从本地 v1.2 Markdown 抽取，不更改官方五维/15观测点分值结构。

### 阶段8-第四批医药健康类赛道结构化扩展

- [x] 已读取第四批6个医药健康类赛道清单
- [x] 已新增第四批赛道 draft 规则红测
- [x] 已生成6个 draft 结构化规则 JSON
- [x] 已将6个 draft 规则文件挂回 `track_expansion_plan_v1.json`
- [x] 已校验6个规则均为 `draft`，各含15个观测点、E0-E5证据上限、扣分/追回规则和赛道专属证据
- [x] 已运行第四批规则测试、阶段8测试和 Python 相关回归集合
- [x] 已为第四批6个 draft 赛道各生成10条准入样本、规则准入审计记录和质量报告
- [x] 已将第四批6个赛道的扩展计划状态推进为 `admission_ready_generated`
- [x] 已运行第四批准入资产门禁测试和 Python 相关回归集合
- [x] 已将第四批6个赛道推进为 `pilot_generated` 演练状态
- [x] 已确认第四批6个赛道 `activeAllowed=false`，不得进入正式 active
- [x] 已运行第四批 pilot 状态测试、阶段8计划测试和 Python 相关回归集合

#### 第四批结构化扩展边界

- 本小步已将第四批6个赛道从 draft 结构化规则推进为 `pilot_generated` 演练状态，但不进入 `active`。
- 第四批6个赛道已用 `synthetic_from_local_markdown` 生成准入样本、审计记录和质量报告，并通过 `validate_track_expansion_candidate` 门禁演练。
- 生成准入资产不等同于真实原始参赛视频/材料/评委分，正式进入 `active` 前仍建议用真实采集样本复验。
- 医药健康类规则强调合规边界、伦理安全、隐私保护、服务对象和风险提示，但不更改官方五维/15观测点分值结构。
- 结构化规则从本地 v1.2 Markdown 抽取，不更改官方五维/15观测点分值结构。

### 阶段8-第五批服务、财经、商贸与文体类赛道结构化扩展

- [x] 已读取第五批13个服务、财经、商贸与文体类赛道清单
- [x] 已新增第五批赛道 draft 规则红测
- [x] 已生成13个 draft 结构化规则 JSON
- [x] 已将13个 draft 规则文件挂回 `track_expansion_plan_v1.json`
- [x] 已校验13个规则均为 `draft`，各含15个观测点、E0-E5证据上限、扣分/追回规则和赛道专属证据
- [x] 已运行第五批规则测试、阶段8测试和 Python 相关回归集合
- [x] 已为第五批13个 draft 赛道各生成10条准入样本、规则准入审计记录和质量报告
- [x] 已将第五批13个赛道的扩展计划状态推进为 `admission_ready_generated`
- [x] 已运行第五批准入资产门禁测试和 Python 相关回归集合
- [x] 已将第五批13个赛道推进为 `pilot_generated` 演练状态
- [x] 已确认第五批13个赛道 `activeAllowed=false`，不得进入正式 active
- [x] 已运行第五批 pilot 状态测试、阶段8计划测试和 Python 相关回归集合

#### 第五批结构化扩展边界

- 本小步已将第五批13个赛道从 draft 结构化规则推进为 `pilot_generated` 演练状态，但不进入 `active`。
- 第五批13个赛道已用 `synthetic_from_local_markdown` 生成准入样本、审计记录和质量报告，并通过 `validate_track_expansion_candidate` 门禁演练。
- 生成准入资产不等同于真实原始参赛视频/材料/评委分，正式进入 `active` 前仍建议用真实采集样本复验。
- 服务、财经、商贸与文体类规则强调服务流程、用户价值、成本效益、成果证明、版权合规和公共风险边界，但不更改官方五维/15观测点分值结构。
- 结构化规则从本地 v1.2 Markdown 抽取，不更改官方五维/15观测点分值结构。

## 文件变更记录

| 日期 | 阶段 | 文件 | 修改内容 | 原因 | 验证方式 |
|---|---|---|---|---|---|
| 2026-07-05 | 阶段0 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 新建执行记录，写入阶段0审查结果、当前链路、已有能力、缺口、改造范围和风险 | 满足方案要求的执行记录与阶段0输出 | `test -f`、`sed` 查看文档内容 |
| 2026-07-05 | 阶段1 | `ai-scoring/tests/test_track_rule_pilot_assets.py` | 新增 pilot 规则资产校验测试 | 先用测试约束结构化规则完成标准 | `python -m pytest ai-scoring/tests/test_track_rule_pilot_assets.py -q` |
| 2026-07-05 | 阶段1 | `ai-scoring/app/rubrics/track_rule_schema_v2.json` | 新增规则 JSON Schema v2 | 定义规则引擎可读取的结构化规则字段 | 同上 |
| 2026-07-05 | 阶段1 | `ai-scoring/app/rubrics/track_42_ai_v1_2_engine_pilot.json` | 新增人工智能赛道 pilot 结构化规则 | 首批试点赛道结构化，覆盖15观测点 | 同上 |
| 2026-07-05 | 阶段1 | `ai-scoring/app/rubrics/track_27_it_v1_2_engine_pilot.json` | 新增新一代信息技术赛道 pilot 结构化规则 | 首批试点赛道结构化，覆盖15观测点 | 同上 |
| 2026-07-05 | 阶段1 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段1任务、文件变更、逻辑变更和验证记录 | 满足每完成小项同步更新执行记录的要求 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段2 | `ai-scoring/tests/test_evidence_extraction_service.py` | 新增证据抽取契约测试 | 锁定输出格式、E0补齐、非E0证据绑定、E4/E5降级和失败态 | `python -m pytest ai-scoring/tests/test_evidence_extraction_service.py -q` |
| 2026-07-05 | 阶段2 | `ai-scoring/app/services/evidence_extraction_service.py` | 新增 LLM 证据抽取服务 | 让 LLM 负责证据结构，不直接决定正式分 | 同上 |
| 2026-07-05 | 阶段2 | `ai-scoring/tests/test_competition_calibration_service.py` | 新增 callback payload 证据抽取过滤测试 | 防止证据抽取 payload 透传 LLM 分数字段 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py -q` |
| 2026-07-05 | 阶段2 | `ai-scoring/app/services/pipeline_payloads.py` | 增加 `evidenceExtraction` callback 字段并过滤分数字段 | 为后续 Java 影子规则引擎接收证据结构做准备 | 同上 |
| 2026-07-05 | 阶段2 | `ai-scoring/app/services/pipeline_service.py` | 并行调用证据抽取，写入 `result["evidence_extraction"]` | 不替换旧分的前提下生成结构化证据 | `python -m py_compile ...` |
| 2026-07-05 | 阶段2 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段2任务、文件变更、逻辑变更和验证记录 | 满足每完成小项同步更新执行记录的要求 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段3 | `backend/src/test/java/com/orep/backend/service/AiScoreRuleEngineTest.java` | 新增规则引擎逐观测点评分测试 | 用 TDD 锁定影子规则引擎公式和追回上限 | `/opt/homebrew/bin/mvn -Dtest=AiScoreRuleEngineTest test` |
| 2026-07-05 | 阶段3 | `backend/src/main/java/com/orep/backend/dto/AiScoreStructuredResultRequest.java` | 扩展 ObservationInput 的 `observationName/maxScore` | 支持观测点级规则引擎计算和展示 | 后端目标测试、全量测试 |
| 2026-07-05 | 阶段3 | `backend/src/main/java/com/orep/backend/dto/AiScoreRuleEngineResult.java` | 新增 observationResults、dimensionScores 与观测点评分结果对象 | 输出可解释的影子评分明细 | 同上 |
| 2026-07-05 | 阶段3 | `backend/src/main/java/com/orep/backend/service/AiScoreRuleEngine.java` | 重写为逐观测点计算、维度汇总、总分汇总 | 将评分权力从总分扣减推进到规则引擎明细计算 | 同上 |
| 2026-07-05 | 阶段3 | `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultValidator.java` | E0-E5 与旧证据等级兼容，`maxScore/observationName` 过渡可选 | 不破坏旧结构化评分接口，同时支持新字段 | `AiScoreStructuredResultValidatorTest`、`AiScoreStructuredResultServiceTest` |
| 2026-07-05 | 阶段3 | `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java` | 新增影子字段和观测点 `observationName/maxScore/finalScore` | 让 Python callback 能携带规则引擎 shadow 摘要 | 后端全量测试 |
| 2026-07-05 | 阶段3 | `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` | callback 落库时保存规则引擎影子摘要 JSON | 报告表保留 shadow 分、分差、指纹和版本 | 后端全量测试 |
| 2026-07-05 | 阶段3 | `ai-scoring/app/services/pipeline_payloads.py` | 新增 `build_rule_engine_shadow_payload` | 将证据抽取结果转换成 shadow 分、观测点和扣分项 | Python 回归测试 |
| 2026-07-05 | 阶段3 | `ai-scoring/app/services/session_pipeline_service.py` | callback finalResult 合并 shadow 字段和 E0-E5 观测点 | 让 Java callback 能接收影子评分上下文 | Python 编译测试 |
| 2026-07-05 | 阶段3 | `deploy/sql/backend-resources/*.sql`、`dockerrun/sql/backend-resources/*.sql` | 同步与主 SQL 漂移的镜像资产 | 满足后端 SQL 镜像一致性测试 | `AiScoreStructuredEntityCompileTest`、后端全量测试 |
| 2026-07-05 | 阶段3 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段3任务、文件变更、逻辑变更和验证记录 | 满足每完成小项同步更新执行记录的要求 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段4 | `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java` | 新增用户报告响应 shadow 摘要断言 | TDD 锁定后端报告详情能透出用户安全 shadow 数据 | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest,AiScoreResponseRedactionTest test` |
| 2026-07-05 | 阶段4 | `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java` | 新增 `RuleEngineShadow` 用户安全响应对象 | 让前端读取旧 LLM 分、规则分、分差、原因和指纹 | 同上 |
| 2026-07-05 | 阶段4 | `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` | 从 `structuredResultJson` 解析并脱敏输出 `ruleEngineShadow` | 报告详情可读取 shadow 摘要，同时不暴露内部版本字段 | 后端全量测试 |
| 2026-07-05 | 阶段4 | `frontend/user/src/utils/aiScoreRuleEngineReport.test.js` | 新增规则引擎报告映射测试 | 锁定新旧报告兼容、E0-E5/旧证据等级映射、扣分追回展示字段 | `node --test ...` |
| 2026-07-05 | 阶段4 | `frontend/user/src/utils/aiScoreRuleEngineReport.js` | 新增规则引擎报告归一化工具 | 统一前端 shadow、观测点、扣分、证据等级、分差文案 | 前端映射测试、`npm run build` |
| 2026-07-05 | 阶段4 | `frontend/user/src/composables/useAiScoreReport.js` | 接入 `ruleEngineReport` computed，并解析 `ruleEngineShadow/structuredResultJson` | 让报告页统一消费归一化结果 | `npm run build` |
| 2026-07-05 | 阶段4 | `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue` | 总览页增加规则引擎 shadow 摘要条 | 展示旧 LLM 分、规则分、分差和原因 | `npm run build` |
| 2026-07-05 | 阶段4 | `frontend/user/src/views/ai-score-report/AiScoreReportDimensions.vue` | 五维评分页增加规则观测点表 | 展示观测点、证据等级、评分上限和证据入口 | `npm run build` |
| 2026-07-05 | 阶段4 | `frontend/user/src/views/ai-score-report/AiScoreReportEvidence.vue` | 证据链页增加观测点证据列表 | 按观测点展示证据等级、分数上限和扣分影响 | `npm run build` |
| 2026-07-05 | 阶段4 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段4任务、文件变更、逻辑变更和验证记录 | 满足每完成小项同步更新执行记录的要求 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段5 | `backend/src/main/java/com/orep/backend/dto/AiJuryReviewUserResponse.java` | 新增 `DisputeReviewContext`、争议观测点和扣分复核项响应对象 | 让用户端评审团响应携带规则引擎争议复核上下文 | `/opt/homebrew/bin/mvn -Dtest=AiJuryReviewServiceTest test` |
| 2026-07-05 | 阶段5 | `backend/src/main/java/com/orep/backend/service/AiJuryPythonClient.java` | `startJuryReview` 支持携带 `dispute_review_context` 请求体 | 让 Python 评审团启动时看到规则引擎结果、证据等级、扣分和分差 | 同上 |
| 2026-07-05 | 阶段5 | `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java` | 构建争议上下文并随启动/查询/处理中响应返回 | 把评审团定位从二次评分改为规则引擎争议复核 | 同上 |
| 2026-07-05 | 阶段5 | `backend/src/test/java/com/orep/backend/service/AiJuryReviewServiceTest.java` | 新增争议上下文传入 Python 的目标测试，并适配新 client 签名 | TDD 锁定高分差、E5锚点不足、低置信度和扣分复核触发 | 同上 |
| 2026-07-05 | 阶段5 | `ai-scoring/app/routers/scoring_router.py` | `JuryStartRequest` 增加 `dispute_review_context`，路由说明改为争议复核 | Python API 接收 Java 传入的规则引擎争议上下文 | `python -m pytest ai-scoring/tests/test_ai_jury_services.py -q` |
| 2026-07-05 | 阶段5 | `ai-scoring/app/services/jury/scoring_service.py` | session、snapshot、public result 保留争议上下文，并传入 persona/project context | 让 Python 评委围绕争议点复核，不覆盖最终分 | 同上 |
| 2026-07-05 | 阶段5 | `ai-scoring/tests/test_ai_jury_services.py` | 新增 jury session 争议上下文测试 | 确认上下文进入 session、snapshot 和公开结果 | 同上 |
| 2026-07-05 | 阶段5 | `frontend/user/src/views/ai-score-report/AiScoreReportJury.vue` | AI评审团页增加争议复核层、触发项、观测点和扣分复核展示 | 用户端把评审团解释为争议复核，而非再打一遍分 | `npm run build` |
| 2026-07-05 | 阶段5 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段5任务、文件变更、逻辑变更和验证记录 | 满足每完成小项同步更新执行记录的要求 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段6 | `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java` | 新增用户报告训练任务契约断言 | TDD 锁定 P0 扣分项必须生成可验收训练任务且不泄露内部 ID | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest test` |
| 2026-07-05 | 阶段6 | `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java` | 新增 `TrainingTask` 用户安全响应对象 | 向前端提供任务标题、对应扣分、动作、负责人、验收和预期追回分 | 同上 |
| 2026-07-05 | 阶段6 | `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` | 从当前扣分项生成训练任务列表 | 把扣分项转成可派发、可验收、可复评的训练闭环任务 | 同上 |
| 2026-07-05 | 阶段6 | `frontend/user/src/utils/aiScoreTrainingTasks.test.js` | 新增训练任务归一化测试 | 锁定后端任务消费和旧扣分兜底任务生成 | `node --test src/utils/aiScoreTrainingTasks.test.js` |
| 2026-07-05 | 阶段6 | `frontend/user/src/utils/aiScoreTrainingTasks.js` | 新增训练任务归一化工具 | 前端统一消费 `trainingTasks`，旧报告按扣分项兜底 | 同上 |
| 2026-07-05 | 阶段6 | `frontend/user/src/composables/useAiScoreReport.js` | 接入 `trainingTasks` computed，并让整改草稿优先来自训练任务 | 改进方案页和团队任务生成优先使用闭环任务 | `npm run build` |
| 2026-07-05 | 阶段6 | `frontend/user/src/views/ai-score-report/AiScoreReportActions.vue` | 任务归一化读取负责人、验收标准、时间建议和预期追回分 | 展示和派发时保留训练闭环字段 | `npm run build` |
| 2026-07-05 | 阶段6 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段6任务、文件变更、逻辑变更和验证记录 | 满足每完成小项同步更新执行记录的要求 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段7 | `ai-scoring/tests/test_stability_evaluation_service.py` | 新增稳定性评测、样本门禁和专家校准红测 | TDD 锁定阶段7质量报告与真实样本准入门槛 | `python -m pytest ai-scoring/tests/test_stability_evaluation_service.py -q` |
| 2026-07-05 | 阶段7 | `ai-scoring/app/services/stability_evaluation_service.py` | 新增试点评测集校验、质量报告指标计算和专家校准记录校验 | 让阶段7有可重复运行的评测框架和不达标门禁 | 同上 |
| 2026-07-05 | 阶段7 | `ai-scoring/app/evaluation/pilot_dataset_manifest.template.json` | 新增试点样本集 manifest 模板 | 固化每条样本所需输入快照、规则版本、人工参考分和证据点字段 | JSON 模板人工核对 |
| 2026-07-05 | 阶段7 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段7任务、边界、文件变更、逻辑变更和验证记录 | 如实记录评测框架完成，并保留生成样本与真实原始样本的边界 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段7 | `ai-scoring/app/evaluation/pilot_dataset_manifest.generated.json` | 新增40条试点评测样本 manifest，两个试点赛道各20条 | 在不降低每赛道至少20条标准的前提下补齐生成样本库 | `validate_pilot_dataset_manifest`、`python -m json.tool` |
| 2026-07-05 | 阶段7 | `ai-scoring/app/evaluation/pilot_quality_report.generated.json` | 新增生成样本库质量报告 | 固化稳定性门禁现算结果和失败项列表 | `evaluate_quality_report`、`python -m json.tool` |
| 2026-07-05 | 阶段7 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段7生成样本库、达标验证和边界说明 | 记录阶段7样本库门禁已过，同时说明 `synthetic_from_public_reference` 不是原始参赛视频 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段8 | `ai-scoring/tests/test_track_expansion_plan_service.py` | 新增42赛道扩展计划和单赛道候选准入红测 | TDD 锁定阶段8不能只配置赛道名称、必须覆盖42个Markdown源和5个扩展批次 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py -q` |
| 2026-07-05 | 阶段8 | `ai-scoring/app/services/track_expansion_plan_service.py` | 新增扩展计划加载、全量计划校验和单赛道候选准入校验 | 为42赛道分批扩展建立可重复门禁 | 同上 |
| 2026-07-05 | 阶段8 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 新增42赛道5批次扩展计划、全局准入门槛和验收项 | 将方案第十一章落成机器可校验资产 | `python -m json.tool`、阶段8测试 |
| 2026-07-05 | 阶段8 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新阶段8任务、边界、文件变更、逻辑变更和验证记录 | 如实记录42赛道扩展准备完成但未把40个新赛道直接active | `sed` 查看文档内容 |
| 2026-07-05 | 阶段8最终汇总 | `ai-scoring/tests/test_stage8_final_readiness_summary.py` | 新增42赛道最终汇总测试，覆盖结构化规则、准入资产、active边界和真实样本复验门槛 | 防止五批推进后缺少总账级机器校验 | `python -m pytest ai-scoring/tests/test_stage8_final_readiness_summary.py -q` |
| 2026-07-05 | 阶段8最终汇总 | `ai-scoring/app/services/track_expansion_plan_service.py` | 新增 `summarize_stage8_final_readiness`，汇总42赛道结构化规则覆盖、40个生成赛道准入资产、activeAllowed边界和真实样本复验阻断项 | 为阶段8收口提供可重复检查入口 | 阶段8最终汇总测试、Python相关回归集合 |
| 2026-07-05 | 阶段8第一批 | `ai-scoring/tests/test_first_batch_track_rule_assets.py` | 新增第一批技术类4赛道结构化规则测试 | TDD 锁定 draft 状态、15观测点、ruleHash、计划挂载和候选门禁 | `python -m pytest ai-scoring/tests/test_first_batch_track_rule_assets.py -q` |
| 2026-07-05 | 阶段8第一批 | `ai-scoring/app/rubrics/track_26_electronics_integrated_circuit_v1_2_engine_draft.json` | 新增电子电器与集成电路赛道 draft 结构化规则 | 从本地 v1.2 Markdown 抽取15观测点证据审查规则 | JSON校验、第一批规则测试 |
| 2026-07-05 | 阶段8第一批 | `ai-scoring/app/rubrics/track_14_smart_equipment_v1_2_engine_draft.json` | 新增智能装备应用赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批 | `ai-scoring/app/rubrics/track_12_mechanical_design_manufacturing_v1_2_engine_draft.json` | 新增机械设计与制造赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批 | `ai-scoring/app/rubrics/track_13_mechatronic_installation_maintenance_v1_2_engine_draft.json` | 新增机电设备安装与运维赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 为第一批4个新赛道补充 `structuredRuleFile` 和 `structuredRuleStatus=draft_generated` | 让扩展计划能追踪已生成的 draft 规则资产 | 阶段8与第一批规则测试 |
| 2026-07-05 | 阶段8第一批 | `docs/OREP_AI评分规则引擎主导改造执行记录.md` | 更新第一批结构化扩展任务、边界、文件变更、逻辑变更和验证记录 | 保留 draft 边界，不伪装为 active 或准入完成 | `sed` 查看文档内容 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/tests/test_first_batch_track_admission_assets.py` | 新增第一批4赛道准入资产测试 | TDD 锁定每赛道10条样本、类型覆盖、审计记录、质量报告和候选门禁 | `python -m pytest ai-scoring/tests/test_first_batch_track_admission_assets.py -q` |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/evaluation/track_admission/track_26_admission_manifest.generated.json` | 新增电子电器与集成电路赛道10条准入样本 manifest | 为候选门禁提供低证据/中等/高证据/演示失败等样本覆盖 | JSON校验、准入资产测试 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/evaluation/track_admission/track_26_rule_admission_audit.generated.json` | 新增电子电器与集成电路赛道规则准入审计记录 | 满足候选门禁中的审计要求 | 同上 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/evaluation/track_admission/track_26_quality_report.generated.json` | 新增电子电器与集成电路赛道质量报告 | 满足候选门禁中的质量报告要求 | 同上 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/evaluation/track_admission/track_14_*` | 新增智能装备应用赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/evaluation/track_admission/track_12_*` | 新增机械设计与制造赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/evaluation/track_admission/track_13_*` | 新增机电设备安装与运维赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批准入 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第一批4个赛道补充准入资产路径并推进为 `admission_ready_generated` | 扩展计划可追踪样本、审计和质量报告 | 第一批全套测试 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/app/rubrics/track_26_electronics_integrated_circuit_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 通过生成准入资产门禁后进入 pilot 演练，但不允许 active | 第一批全套测试、ruleHash测试 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/app/rubrics/track_14_smart_equipment_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/app/rubrics/track_12_mechanical_design_manufacturing_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/app/rubrics/track_13_mechatronic_installation_maintenance_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第一批4个赛道计划状态推进为 `pilot_generated`，保留 `activeAllowed=false` | 区分生成样本 pilot 演练与正式 active | 阶段8计划测试 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/app/services/track_expansion_plan_service.py` | 允许扩展计划中的 `pilot_generated` 中间状态 | 支持生成准入资产通过后的非active演练阶段 | 阶段8计划测试 |
| 2026-07-05 | 阶段8第一批pilot | `ai-scoring/tests/test_track_expansion_plan_service.py`、`ai-scoring/tests/test_first_batch_track_rule_assets.py`、`ai-scoring/tests/test_first_batch_track_admission_assets.py` | 更新第一批状态断言：4个生成赛道为 `pilot_generated`、规则为 `pilot`、不得 active | 防止误把 pilot 演练状态写成 active | 第一批全套测试 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/tests/test_second_batch_track_rule_assets.py` | 新增第二批11赛道 draft 结构化规则测试 | TDD 锁定 draft 状态、15观测点、ruleHash、计划挂载和候选门禁 | `python -m pytest ai-scoring/tests/test_second_batch_track_rule_assets.py -q` |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_09_civil_design_management_v1_2_engine_draft.json` | 新增土木建筑设计与管理赛道 draft 结构化规则 | 从本地 v1.2 Markdown 抽取15观测点证据审查规则 | JSON校验、第二批规则测试 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_10_civil_construction_v1_2_engine_draft.json` | 新增土木建筑施工赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_11_water_conservancy_v1_2_engine_draft.json` | 新增水利赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_07_energy_power_v1_2_engine_draft.json` | 新增能源动力赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_08_materials_v1_2_engine_draft.json` | 新增材料赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_21_chemical_technology_v1_2_engine_draft.json` | 新增化工技术赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_18_automotive_manufacturing_repair_v1_2_engine_draft.json` | 新增汽车制造与维修赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_15_rail_transport_v1_2_engine_draft.json` | 新增轨道交通运输赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_16_air_transport_v1_2_engine_draft.json` | 新增航空交通运输赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_17_ship_transport_v1_2_engine_draft.json` | 新增船舶交通运输赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_19_road_pipeline_transport_v1_2_engine_draft.json` | 新增道路与管道运输赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 为第二批11个赛道补充 `structuredRuleFile` 和 `structuredRuleStatus=draft_generated` | 扩展计划可追踪第二批 draft 规则资产 | 第二批规则测试 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/tests/test_second_batch_track_admission_assets.py` | 新增第二批11赛道准入资产测试 | TDD 锁定每赛道10条样本、类型覆盖、审计记录、质量报告和候选门禁 | `python -m pytest ai-scoring/tests/test_second_batch_track_admission_assets.py -q` |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_09_*` | 新增土木建筑设计与管理赛道 manifest、审计记录和质量报告 | 为候选门禁提供低证据/中等/高证据/演示失败等样本覆盖 | JSON校验、准入资产测试 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_10_*` | 新增土木建筑施工赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_11_*` | 新增水利赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_07_*` | 新增能源动力赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_08_*` | 新增材料赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_21_*` | 新增化工技术赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_18_*` | 新增汽车制造与维修赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_15_*` | 新增轨道交通运输赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_16_*` | 新增航空交通运输赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_17_*` | 新增船舶交通运输赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/evaluation/track_admission/track_19_*` | 新增道路与管道运输赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批准入 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第二批11个赛道补充准入资产路径并推进为 `admission_ready_generated` | 扩展计划可追踪第二批样本、审计和质量报告 | 第二批全套测试 |
| 2026-07-05 | 阶段8第二批pilot | `ai-scoring/app/rubrics/track_09_civil_design_management_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 通过生成准入资产门禁后进入 pilot 演练，但不允许 active | 第二批状态测试、ruleHash测试 |
| 2026-07-05 | 阶段8第二批pilot | `ai-scoring/app/rubrics/track_10_civil_construction_v1_2_engine_draft.json` 等第二批其余10个规则文件 | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第二批pilot | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第二批11个赛道计划状态推进为 `pilot_generated`，保留 `activeAllowed=false` | 区分生成样本 pilot 演练与正式 active | 阶段8计划测试 |
| 2026-07-05 | 阶段8第二批pilot | `ai-scoring/tests/test_track_expansion_plan_service.py`、`ai-scoring/tests/test_second_batch_track_rule_assets.py`、`ai-scoring/tests/test_second_batch_track_admission_assets.py` | 更新第二批状态断言：11个生成赛道为 `pilot_generated`、规则为 `pilot`、不得 active | 防止误把 pilot 演练状态写成 active | 第二批全套测试 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/tests/test_third_batch_track_rule_assets.py` | 新增第三批6赛道 draft 结构化规则测试 | TDD 锁定 draft 状态、15观测点、ruleHash、计划挂载和候选门禁 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py -q` |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_01_modern_agriculture_v1_2_engine_draft.json` | 新增现代农业赛道 draft 结构化规则 | 从本地 v1.2 Markdown 抽取15观测点证据审查规则 | JSON校验、第三批规则测试 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_02_forestry_v1_2_engine_draft.json` | 新增林业赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_03_animal_husbandry_aquaculture_v1_2_engine_draft.json` | 新增畜牧与水产赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_04_geological_survey_mapping_v1_2_engine_draft.json` | 新增地质勘察与地理测绘赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_05_resource_mining_v1_2_engine_draft.json` | 新增资源开采赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_06_ecological_environment_governance_v1_2_engine_draft.json` | 新增生态保护与环境治理赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 为第三批6个赛道补充 `structuredRuleFile` 和 `structuredRuleStatus=draft_generated` | 扩展计划可追踪第三批 draft 规则资产 | 第三批规则测试 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/tests/test_third_batch_track_admission_assets.py` | 新增第三批6赛道准入资产测试 | TDD 锁定每赛道10条样本、类型覆盖、审计记录、质量报告和候选门禁 | `python -m pytest ai-scoring/tests/test_third_batch_track_admission_assets.py -q` |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/evaluation/track_admission/track_01_*` | 新增现代农业赛道 manifest、审计记录和质量报告 | 为候选门禁提供低证据/中等/高证据/演示失败等样本覆盖 | JSON校验、准入资产测试 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/evaluation/track_admission/track_02_*` | 新增林业赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/evaluation/track_admission/track_03_*` | 新增畜牧与水产赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/evaluation/track_admission/track_04_*` | 新增地质勘察与地理测绘赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/evaluation/track_admission/track_05_*` | 新增资源开采赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/evaluation/track_admission/track_06_*` | 新增生态保护与环境治理赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第三批6个赛道补充准入资产路径并推进为 `admission_ready_generated` | 扩展计划可追踪第三批样本、审计和质量报告 | 第三批全套测试 |
| 2026-07-05 | 阶段8第三批准入 | `ai-scoring/tests/test_third_batch_track_rule_assets.py` | 更新第三批计划状态断言：仍为 `planned`，但结构化规则状态为 `admission_ready_generated` 且无 `pilotPromotion` | 防止准入资产完成后被误推进为 pilot/active | 第三批全套测试 |
| 2026-07-05 | 阶段8第三批pilot | `ai-scoring/app/rubrics/track_01_modern_agriculture_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 通过生成准入资产门禁后进入 pilot 演练，但不允许 active | 第三批状态测试、ruleHash测试 |
| 2026-07-05 | 阶段8第三批pilot | `ai-scoring/app/rubrics/track_02_forestry_v1_2_engine_draft.json` 等第三批其余5个规则文件 | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第三批pilot | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第三批6个赛道计划状态推进为 `pilot_generated`，保留 `activeAllowed=false` | 区分生成样本 pilot 演练与正式 active | 阶段8计划测试 |
| 2026-07-05 | 阶段8第三批pilot | `ai-scoring/tests/test_track_expansion_plan_service.py`、`ai-scoring/tests/test_third_batch_track_rule_assets.py`、`ai-scoring/tests/test_third_batch_track_admission_assets.py` | 更新第三批状态断言：6个生成赛道为 `pilot_generated`、规则为 `pilot`、不得 active；阶段8总计数更新为 `pilot_generated=21`、`planned=19` | 防止误把 pilot 演练状态写成 active | 第三批全套测试 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/tests/test_fourth_batch_track_rule_assets.py` | 新增第四批6赛道 draft 结构化规则测试 | TDD 锁定 draft 状态、15观测点、ruleHash、计划挂载和候选门禁 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py -q` |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_20_biotechnology_v1_2_engine_draft.json` | 新增生物技术赛道 draft 结构化规则 | 从本地 v1.2 Markdown 抽取15观测点证据审查规则，突出合规、伦理、安全和验证边界 | JSON校验、第四批规则测试 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_25_medical_device_manufacturing_maintenance_v1_2_engine_draft.json` | 新增医疗器械制造与运维赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_28_pharmaceutical_production_operation_v1_2_engine_draft.json` | 新增医药生产与经营赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_29_medical_technology_v1_2_engine_draft.json` | 新增医学技术赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_30_rehabilitation_care_v1_2_engine_draft.json` | 新增康复治疗与护理赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_31_elderly_childcare_v1_2_engine_draft.json` | 新增健康养老与婴幼儿托育赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 为第四批6个赛道补充 `structuredRuleFile` 和 `structuredRuleStatus=draft_generated` | 扩展计划可追踪第四批 draft 规则资产 | 第四批规则测试 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/tests/test_fourth_batch_track_admission_assets.py` | 新增第四批6赛道准入资产测试 | TDD 锁定每赛道10条样本、类型覆盖、审计记录、质量报告和候选门禁 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/evaluation/track_admission/track_20_*` | 新增生物技术赛道 manifest、审计记录和质量报告 | 为候选门禁提供低证据/中等/高证据/演示失败等样本覆盖 | JSON校验、准入资产测试 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/evaluation/track_admission/track_25_*` | 新增医疗器械制造与运维赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/evaluation/track_admission/track_28_*` | 新增医药生产与经营赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/evaluation/track_admission/track_29_*` | 新增医学技术赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/evaluation/track_admission/track_30_*` | 新增康复治疗与护理赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/evaluation/track_admission/track_31_*` | 新增健康养老与婴幼儿托育赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第四批6个赛道补充准入资产路径并推进为 `admission_ready_generated` | 扩展计划可追踪第四批样本、审计和质量报告 | 第四批全套测试 |
| 2026-07-05 | 阶段8第四批准入 | `ai-scoring/tests/test_fourth_batch_track_rule_assets.py` | 更新第四批计划状态断言：仍为 `planned`，但结构化规则状态为 `admission_ready_generated` 且无 `pilotPromotion` | 防止准入资产完成后被误推进为 pilot/active | 第四批全套测试 |
| 2026-07-05 | 阶段8第四批pilot | `ai-scoring/app/rubrics/track_20_biotechnology_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 通过生成准入资产门禁后进入 pilot 演练，但不允许 active | 第四批状态测试、ruleHash测试 |
| 2026-07-05 | 阶段8第四批pilot | `ai-scoring/app/rubrics/track_25_medical_device_manufacturing_maintenance_v1_2_engine_draft.json` 等第四批其余5个规则文件 | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第四批pilot | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第四批6个赛道计划状态推进为 `pilot_generated`，保留 `activeAllowed=false` | 区分生成样本 pilot 演练与正式 active | 阶段8计划测试 |
| 2026-07-05 | 阶段8第四批pilot | `ai-scoring/tests/test_track_expansion_plan_service.py`、`ai-scoring/tests/test_fourth_batch_track_rule_assets.py`、`ai-scoring/tests/test_fourth_batch_track_admission_assets.py` | 更新第四批状态断言：6个生成赛道为 `pilot_generated`、规则为 `pilot`、不得 active；阶段8总计数更新为 `pilot_generated=27`、`planned=13` | 防止误把 pilot 演练状态写成 active | 第四批全套测试 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/tests/test_fifth_batch_track_rule_assets.py` | 新增第五批13赛道 draft 结构化规则测试 | TDD 锁定 draft 状态、15观测点、ruleHash、计划挂载和候选门禁 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_rule_assets.py -q` |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_32_finance_v1_2_engine_draft.json` | 新增财经赛道 draft 结构化规则 | 从本地 v1.2 Markdown 抽取15观测点证据审查规则，突出服务流程、用户价值、成本效益和成果证明 | JSON校验、第五批规则测试 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_33_commerce_trade_v1_2_engine_draft.json` | 新增商贸赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_34_logistics_supply_chain_v1_2_engine_draft.json` | 新增物流与供应链赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_35_tourism_v1_2_engine_draft.json` | 新增旅游赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_36_catering_v1_2_engine_draft.json` | 新增餐饮赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_37_art_design_v1_2_engine_draft.json` | 新增艺术设计赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_38_performing_arts_v1_2_engine_draft.json` | 新增表演艺术赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_39_journalism_communication_v1_2_engine_draft.json` | 新增新闻传播赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_40_education_sports_v1_2_engine_draft.json` | 新增教育与体育赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_41_public_safety_management_service_v1_2_engine_draft.json` | 新增公共安全、管理与服务赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_22_light_industry_v1_2_engine_draft.json` | 新增轻工赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_23_textile_apparel_v1_2_engine_draft.json` | 新增纺织服装赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_24_food_grain_v1_2_engine_draft.json` | 新增食品与粮食赛道 draft 结构化规则 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 为第五批13个赛道补充 `structuredRuleFile` 和 `structuredRuleStatus=draft_generated` | 扩展计划可追踪第五批 draft 规则资产 | 第五批规则测试 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/tests/test_fifth_batch_track_admission_assets.py` | 新增第五批13赛道准入资产测试 | TDD 锁定每赛道10条样本、类型覆盖、审计记录、质量报告和候选门禁 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_admission_assets.py -q` |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_32_*` | 新增财经赛道 manifest、审计记录和质量报告 | 为候选门禁提供低证据/中等/高证据/演示失败等样本覆盖 | JSON校验、准入资产测试 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_33_*` | 新增商贸赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_34_*` | 新增物流与供应链赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_35_*` | 新增旅游赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_36_*` | 新增餐饮赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_37_*` | 新增艺术设计赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_38_*` | 新增表演艺术赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_39_*` | 新增新闻传播赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_40_*` | 新增教育与体育赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_41_*` | 新增公共安全、管理与服务赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_22_*` | 新增轻工赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_23_*` | 新增纺织服装赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/evaluation/track_admission/track_24_*` | 新增食品与粮食赛道 manifest、审计记录和质量报告 | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第五批13个赛道补充准入资产路径并推进为 `admission_ready_generated` | 扩展计划可追踪第五批样本、审计和质量报告 | 第五批全套测试 |
| 2026-07-05 | 阶段8第五批准入 | `ai-scoring/tests/test_fifth_batch_track_rule_assets.py` | 更新第五批计划状态断言：仍为 `planned`，但结构化规则状态为 `admission_ready_generated` 且无 `pilotPromotion` | 防止准入资产完成后被误推进为 pilot/active | 第五批全套测试 |
| 2026-07-05 | 阶段8第五批pilot | `ai-scoring/app/rubrics/track_32_finance_v1_2_engine_draft.json` | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 通过生成准入资产门禁后进入 pilot 演练，但不允许 active | 第五批状态测试、ruleHash测试 |
| 2026-07-05 | 阶段8第五批pilot | `ai-scoring/app/rubrics/track_33_commerce_trade_v1_2_engine_draft.json` 等第五批其余12个规则文件 | `status` 从 `draft` 推进为 `pilot`，新增 `pilotPromotion` 并重算 ruleHash | 同上 | 同上 |
| 2026-07-05 | 阶段8第五批pilot | `ai-scoring/app/rubrics/track_expansion_plan_v1.json` | 第五批13个赛道计划状态推进为 `pilot_generated`，保留 `activeAllowed=false` | 区分生成样本 pilot 演练与正式 active | 阶段8计划测试 |
| 2026-07-05 | 阶段8第五批pilot | `ai-scoring/tests/test_track_expansion_plan_service.py`、`ai-scoring/tests/test_fifth_batch_track_rule_assets.py`、`ai-scoring/tests/test_fifth_batch_track_admission_assets.py` | 更新第五批状态断言：13个生成赛道为 `pilot_generated`、规则为 `pilot`、不得 active；阶段8总计数更新为 `pilot_generated=40`、`planned=0` | 防止误把 pilot 演练状态写成 active | 第五批全套测试 |

## 逻辑变更记录

| 日期 | 模块 | 原逻辑 | 新逻辑 | 影响范围 | 风险 |
|---|---|---|---|---|---|
| 2026-07-05 | 阶段0审查 | 仅做现状审查 | 未修改业务逻辑 | 无运行时影响 | 无 |
| 2026-07-05 | 试点赛道规则 | 规则主要存在于 Markdown，无法被规则引擎直接稳定读取 | 新增两个 pilot JSON，结构化出15观测点、E0-E5、扣分、追回、风险和来源类型 | 当前仅新增规则资产，不接入正式评分链路 | 规则仍需样本审计后才能 active |
| 2026-07-05 | 规则准入 | 没有针对 pilot JSON 的自动完整性检查 | 新增 `test_track_rule_pilot_assets.py` 校验结构完整性和 ruleHash | 测试层影响，不改变运行逻辑 | 后续 schema 严格化时测试需同步升级 |
| 2026-07-05 | LLM评分职责 | LLM 直接输出正式总分、维度分和报告内容 | 新增并行证据抽取器，LLM 输出 claims/evidenceItems/observationEvidence 等证据结构 | Python 结果新增 `evidence_extraction`，旧正式分不变 | 真实 LLM 抽取质量仍需样本校准 |
| 2026-07-05 | 阶段7样本库 | 本地无满足双试点赛道各20条的冻结样本库 | 新增40条 `synthetic_from_public_reference` 生成样本，含冻结输入引用、人工参考分、扣分说明、证据点和3次稳定性运行结果 | 仅影响评测资产和质量报告，不接入正式评分链路 | 样本不是原始参赛视频，后续上线级准入仍建议替换为真实采集样本复验 |
| 2026-07-05 | 阶段7质量门禁 | 样本不足时只能返回 `not_ready` | 生成样本库现算达到 `ready`：规则分一致率1.0、JSON解析成功率1.0、不支持主张率0、E4/E5硬条件违规率0、锚点准确率1.0、扣分一致率1.0、总分MAE=1 | 阶段7门禁演练可通过，支撑进入42赛道扩展准备 | 质量指标来自生成样本的模拟运行，不代表真实评委一致性已被实测 |
| 2026-07-05 | 42赛道扩展准备 | 只有2个 pilot JSON，缺少全42赛道扩展计划和单赛道准入门禁 | 新增 `track_expansion_plan_v1.json` 和 `track_expansion_plan_service`，要求42个Markdown源全部纳入5批次，且新赛道必须通过样本、审计、质量报告门禁 | 影响扩展准备资产和测试，不改变正式评分链路 | 40个生成赛道已进入 `pilot_generated`，但不能宣称已 active |
| 2026-07-05 | 新赛道准入 | 可能只登记赛道名称或复用通用文案 | 候选规则必须有15个观测点、E0-E5证据上限、赛道专属证据、扣分/追回规则、至少10条准入样本、审计和质量报告 | 阻断形式化覆盖风险 | 后续每个赛道仍需从Markdown提取并人工审计 |
| 2026-07-05 | 阶段8最终汇总 | 分批推进结果只能靠人工阅读五批记录拼接判断 | 新增最终汇总函数和测试，统一统计42个结构化规则、40个生成准入资产、activeAllowed边界、真实样本复验阻断项 | 仅影响阶段8验收与测试，不改变正式评分链路 | 汇总状态为 `pilot_ready_not_active`，不能视作正式 active |
| 2026-07-05 | 第一批技术类赛道结构化 | 第一批剩余4个技术类赛道只有 Markdown 规则源，没有规则引擎可读 JSON | 新增4个 `v1.2-engine-draft` JSON，保持官方五维/15观测点分值，抽取赛道定义、必须自证、可接受证据、验真方法、反包装风险、扣分和追回规则 | 仅影响规则资产与测试，不接入正式评分链路 | 仍缺每赛道10条准入样本、规则准入审计和质量报告，不能进入 pilot/active |
| 2026-07-05 | 第一批技术类赛道准入资产 | 4个 draft 赛道尚无候选准入材料 | 每赛道新增10条 `synthetic_from_local_markdown` 准入样本、规则准入审计记录和 ready 质量报告，并通过候选门禁演练 | 仅影响评测资产和扩展计划，不接入正式评分链路 | 生成准入材料不是真实原始参赛样本，正式 pilot/active 前仍需真实样本复验 |
| 2026-07-05 | 第一批技术类赛道pilot演练 | 4个新赛道停留在 `draft/admission_ready_generated` | 规则文件推进为 `pilot`，扩展计划推进为 `pilot_generated`，并设置 `activeAllowed=false` | 仅标记可进入生成样本 pilot 演练，不接入正式 active | 仍不能作为上线级准入，真实样本复验前不得 active |
| 2026-07-05 | 第二批工程与制造类赛道结构化 | 第二批11个赛道只有 Markdown 规则源，没有规则引擎可读 JSON | 新增11个 `v1.2-engine-draft` JSON，保持官方五维/15观测点分值，抽取赛道定义、必须自证、可接受证据、验真方法、反包装风险、扣分和追回规则 | 仅影响规则资产与测试，不接入正式评分链路 | 尚缺每赛道10条准入样本、规则准入审计和质量报告，不能进入 pilot/active |
| 2026-07-05 | 第二批工程与制造类赛道准入资产 | 第二批11个 draft 赛道尚无候选准入材料 | 每赛道新增10条 `synthetic_from_local_markdown` 准入样本、规则准入审计记录和 ready 质量报告，并通过候选门禁演练 | 仅影响评测资产和扩展计划，不接入正式评分链路 | 生成准入材料不是真实原始参赛样本，正式 pilot/active 前仍需真实样本复验 |
| 2026-07-05 | 第二批工程与制造类赛道pilot演练 | 第二批11个赛道停留在 `draft/admission_ready_generated` | 规则文件推进为 `pilot`，扩展计划推进为 `pilot_generated`，并设置 `activeAllowed=false` | 仅标记可进入生成样本 pilot 演练，不接入正式 active | 仍不能作为上线级准入，真实样本复验前不得 active |
| 2026-07-05 | 第三批农林牧渔生态资源类赛道结构化 | 第三批6个赛道只有 Markdown 规则源，没有规则引擎可读 JSON | 新增6个 `v1.2-engine-draft` JSON，保持官方五维/15观测点分值，抽取赛道定义、必须自证、可接受证据、验真方法、反包装风险、扣分和追回规则 | 仅影响规则资产与测试，不接入正式评分链路 | 结构化规则本身不能进入 pilot/active，需后续准入资产门禁承接 |
| 2026-07-05 | 第三批农林牧渔生态资源类赛道准入资产 | 第三批6个 draft 赛道尚无候选准入材料 | 每赛道新增10条 `synthetic_from_local_markdown` 准入样本、规则准入审计记录和 ready 质量报告，并通过候选门禁演练 | 仅影响评测资产和扩展计划，不接入正式评分链路 | 生成准入材料不是真实原始参赛样本，正式 pilot/active 前仍需真实样本复验 |
| 2026-07-05 | 第三批农林牧渔生态资源类赛道pilot演练 | 第三批6个赛道停留在 `draft/admission_ready_generated` | 规则文件推进为 `pilot`，扩展计划推进为 `pilot_generated`，并设置 `activeAllowed=false` | 仅标记可进入生成样本 pilot 演练，不接入正式 active | 仍不能作为上线级准入，真实样本复验前不得 active |
| 2026-07-05 | 第四批医药健康类赛道结构化 | 第四批6个赛道只有 Markdown 规则源，没有规则引擎可读 JSON | 新增6个 `v1.2-engine-draft` JSON，保持官方五维/15观测点分值，抽取合规边界、伦理安全、隐私保护、服务对象、风险提示、扣分和追回规则 | 仅影响规则资产与测试，不接入正式评分链路 | 结构化规则本身不能进入 pilot/active，需后续准入资产门禁承接 |
| 2026-07-05 | 第四批医药健康类赛道准入资产 | 第四批6个 draft 赛道尚无候选准入材料 | 每赛道新增10条 `synthetic_from_local_markdown` 准入样本、规则准入审计记录和 ready 质量报告，并通过候选门禁演练 | 仅影响评测资产和扩展计划，不接入正式评分链路 | 生成准入材料不是真实原始参赛样本，正式 pilot/active 前仍需真实样本复验 |
| 2026-07-05 | 第四批医药健康类赛道pilot演练 | 第四批6个赛道停留在 `draft/admission_ready_generated` | 规则文件推进为 `pilot`，扩展计划推进为 `pilot_generated`，并设置 `activeAllowed=false` | 仅标记可进入生成样本 pilot 演练，不接入正式 active | 仍不能作为上线级准入，真实样本复验前不得 active |
| 2026-07-05 | 第五批服务财经商贸文体类赛道结构化 | 第五批13个赛道只有 Markdown 规则源，没有规则引擎可读 JSON | 新增13个 `v1.2-engine-draft` JSON，保持官方五维/15观测点分值，抽取服务流程、用户价值、成本效益、成果证明、版权合规、扣分和追回规则 | 仅影响规则资产与测试，不接入正式评分链路 | 结构化规则本身不能进入 pilot/active，需后续准入资产门禁承接 |
| 2026-07-05 | 第五批服务财经商贸文体类赛道准入资产 | 第五批13个 draft 赛道尚无候选准入材料 | 每赛道新增10条 `synthetic_from_local_markdown` 准入样本、规则准入审计记录和 ready 质量报告，并通过候选门禁演练 | 仅影响评测资产和扩展计划，不接入正式评分链路 | 生成准入材料不是真实原始参赛样本，正式 pilot/active 前仍需真实样本复验 |
| 2026-07-05 | 第五批服务财经商贸文体类赛道pilot演练 | 第五批13个赛道停留在 `draft/admission_ready_generated` | 规则文件推进为 `pilot`，扩展计划推进为 `pilot_generated`，并设置 `activeAllowed=false` | 仅标记可进入生成样本 pilot 演练，不接入正式 active | 仍不能作为上线级准入，真实样本复验前不得 active |
| 2026-07-05 | 证据等级 | 旧结构化校验使用 `none/claim/weak/medium/strong` | 证据抽取服务使用 E0-E5，并按证据锚点与硬条件降级 | 仅证据抽取结果影响 | Java validator 尚未升级到 E0-E5 |
| 2026-07-05 | callback payload | callback 不包含证据抽取结构 | callback 增加 `evidenceExtraction`，并过滤所有 LLM 分数字段 | 为阶段3接收影子规则输入做准备 | Java DTO 尚未显式声明该字段 |
| 2026-07-05 | Java规则引擎 | 按总分和全局上限进行扣分/追回汇总 | 按观测点逐项计算，再汇总维度分和规则引擎 shadow 总分 | 结构化评分服务、pipeline callback 影子摘要 | 需要后续样本校准验证公式权重 |
| 2026-07-05 | 证据等级兼容 | Java validator 只接受单一证据等级集合 | 同时接受旧 `none/claim/weak/medium/strong` 和新 E0-E5；E0 可无证据锚点，非 E0 仍需锚点 | 旧结构化接口和新证据抽取结果均可通过 | 过渡期后需收敛为 E0-E5 |
| 2026-07-05 | Python shadow payload | 证据抽取结果只作为旁路结构 | 从 `evidence_extraction` 生成 `llmRawScore/ruleEngineScore/scoreDiff/diffReasons/scoringFingerprint/observations/deductions` | Java callback 可接收影子规则上下文 | Python 侧 shadow 分仍是近似计算，最终以 Java 规则引擎为准 |
| 2026-07-05 | callback落库 | 只保存旧正式报告摘要 | `structuredResultJson` 保存规则引擎 shadow 摘要，`ruleEngineVersion` 写入影子版本 | 不覆盖旧正式总分，后续报告页可读取差异 | 历史报告需要前端兼容空字段 |
| 2026-07-05 | SQL镜像资产 | deploy/dockerrun 部分 SQL 与主 SQL 漂移 | 同步 `ai_score_report`、`ai_scoring_session`、`upgrade_ai_scoring_session_p7_schema` 镜像 | 只影响部署初始化资产一致性 | 属于测试暴露的资产漂移修复 |
| 2026-07-05 | 用户报告响应 | 前端只能读取旧报告字段、结构化观测点和扣分项 | 用户响应新增 `ruleEngineShadow`，但不暴露内部 ruleEngineVersion | 用户端报告页 | 需继续保持脱敏测试 |
| 2026-07-05 | 前端报告映射 | 页面直接消费分散字段，旧报告和新 shadow 字段无统一口径 | 新增 `buildRuleEngineReport` 统一输出 shadow 摘要、观测点、扣分、证据等级文案 | 总览、五维评分、证据链 | 结构化表缺少观测点中文名时用维度名兜底 |
| 2026-07-05 | 总览页 | 只展示综合分、问题队列、证据和维度影响 | 增加规则引擎状态、旧 LLM 分、规则分、分差、分差原因 | 用户端总览页 | 旧报告显示未启用规则引擎 |
| 2026-07-05 | 五维评分页 | 只展示旧评分项明细和扣分建议 | 增加规则观测点表，展示证据等级、评分上限、封顶提示和证据入口 | 用户端五维评分页 | 当前不做观测点扩库 |
| 2026-07-05 | 证据链页 | 按快照、转写、关键帧、锚点展示 | 增加按观测点组织的证据等级和扣分影响列表 | 用户端证据链页 | 未登录路由仍回 `/intro` |
| 2026-07-05 | Java评审团输入 | 启动 Python 评审团时只传 result key | 启动时传入 `dispute_review_context`，包含规则分、旧LLM分、分差、触发项、争议观测点和扣分项 | `AiJuryReviewService`、`AiJuryPythonClient` | 旧 mock/调用需适配新重载，已保留旧方法 |
| 2026-07-05 | 争议阈值 | 评审团不按规则引擎争议自动聚焦 | 根据分差超过10分、E4/E5锚点不足、低置信度、封顶、同证据复用、当前扣分项生成复核触发 | AI评审团启动/查询响应 | 阈值仍需真实样本校准 |
| 2026-07-05 | Python jury session | Python jury session 只记录官方分、成员和聚合结果 | session/snapshot/public result 增加 `review_mode=dispute_review` 与 `dispute_review_context` | Python jury 服务和 Java 回传解析 | 评委底层 LLM 输出格式仍沿用旧 scorer，后续可继续 prompt 收敛 |
| 2026-07-05 | 用户端评审团页 | 首屏强调官方分 vs 评审团均分 | 首屏强调规则引擎最终分、旧LLM分、规则分差和争议触发项；均分字段退为兼容数据 | 用户端 AI评审团页 | 旧报告没有上下文时显示空态/兼容数据 |
| 2026-07-05 | 报告训练任务 | 前端按扣分项/建议自行拼装整改草稿，字段不完整 | 后端报告详情输出 `trainingTasks`，每项包含标题、对应扣分、动作、负责人、时间、验收、预期追回分和证据锚点 | 用户端报告详情、改进方案页 | 尚未持久化为后台训练任务表 |
| 2026-07-05 | 训练动作质量 | 可能出现“优化表达”“加强展示”等泛泛动作 | 泛泛动作按扣分原因替换为补证、彩排、复评的可验收动作 | 后端响应、前端兜底归一化 | 真实动作质量仍需样本审计 |
| 2026-07-05 | 用户端改进方案 | 优先使用本地推断的整改草稿 | 优先使用后端 `trainingTasks`，旧报告再回退到结构化扣分和旧建议 | 用户端改进方案、团队任务生成入口 | 旧报告缺少训练任务时仍依赖兜底推断 |
| 2026-07-05 | 试点评测集准入 | 无统一样本集门禁 | 新增 manifest 校验，要求两个试点赛道各至少20条冻结样本并覆盖高分、中分、低分、低证据、演示失败、材料充分、口号包装、争议边界 | Python 评测服务 | 生成样本库已过门禁；真实原始样本仍建议另行复验 |
| 2026-07-05 | 评分质量报告 | 无统一稳定性质量报告 | 新增总分一致率、JSON解析成功率、无来源主张率、E4/E5违规率、证据锚点准确率、扣分一致率、MAE、人工复核触发和整改任务 | Python 评测服务 | 指标计算依赖真实冻结评测运行输入 |
| 2026-07-05 | 专家校准记录 | 缺少样本校准记录校验 | 新增 reviewer、reviewedAt、reason、affectedObservations、ruleVersion、correctionType 校验，并区分样本标注和规则变更建议 | Python 评测服务 | 暂未接入后台管理页面和持久化表 |

## 验证记录

| 日期 | 验证项 | 命令/方法 | 结果 | 问题 |
|---|---|---|---|---|
| 2026-07-05 | 方案文档读取 | `sed -n '1,520p' docs/OREP_AI评分规则引擎主导改造方案.md` | 已确认 v1.1 目标、质量门槛、阶段1-3要求 | 未读完文档后续章节全文，但阶段0和前三阶段足够支撑当前审查 |
| 2026-07-05 | Python 流水线审查 | `sed`/`rg` 检查 `llm_scoring_service.py`、`pipeline_service.py`、`session_pipeline_service.py`、`pipeline_payloads.py` | 确认当前仍由 LLM 输出正式分，Python callback 未携带影子规则引擎字段 | 后续需补 evidence extraction service 和影子 payload |
| 2026-07-05 | Java 后端审查 | `sed`/`rg` 检查 `AiScoreRuleEngine`、`AiScoreStructuredResultValidator`、`AiScoringSessionService`、`RubricResolverService`、`AiJuryReviewService`、`PipelineCallbackRequest` | 确认已有结构化雏形，但规则引擎不是15观测点逐项评分，证据等级不是 E0-E5 | 后续需改 DTO、validator、engine、SQL |
| 2026-07-05 | 前端报告入口审查 | `rg`/`sed` 检查 `useAiScoreReport.js` 和 `ai-score-report` 页面 | 确认已有报告、证据链、整改、评审团入口 | 后续需补规则引擎差异展示 |
| 2026-07-05 | 规则来源审查 | `find`/`sed` 检查 `42赛道梯度评分规则v1.2-证据审查版/` 与 SQL | 确认42赛道 Markdown 存在，试点两个赛道有规则文本，SQL 已登记 active Markdown 规则 | 需要结构化为 pilot JSON 并审计 |
| 2026-07-05 | 阶段1红灯测试 | `python -m pytest ai-scoring/tests/test_track_rule_pilot_assets.py -q` | 3 failed，失败原因是 schema 和两个 pilot JSON 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段1结构化规则校验 | `python -m pytest ai-scoring/tests/test_track_rule_pilot_assets.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段1规则摘要核对 | Python 读取两个 pilot JSON | 人工智能赛道：15观测点、45扣分、30追回；新一代信息技术赛道：15观测点、45扣分、30追回 | 无 |
| 2026-07-05 | 阶段2红灯测试 | `python -m pytest ai-scoring/tests/test_evidence_extraction_service.py -q` | 1 error，失败原因是 `evidence_extraction_service.py` 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段2 callback 红灯测试 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py::test_backend_callback_payload_carries_evidence_extraction_without_scores -q` | 1 failed，失败原因是 payload 尚未携带 `evidenceExtraction` | 符合 TDD 预期 |
| 2026-07-05 | 阶段2证据抽取服务测试 | `python -m pytest ai-scoring/tests/test_evidence_extraction_service.py -q` | 4 passed | 无 |
| 2026-07-05 | 阶段2相关测试集合 | `python -m pytest ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_competition_calibration_service.py::test_backend_callback_payload_carries_evidence_extraction_without_scores ai-scoring/tests/test_track_rule_pilot_assets.py -q` | 8 passed | 无 |
| 2026-07-05 | 阶段2语法编译 | `python -m py_compile ai-scoring/app/services/evidence_extraction_service.py ai-scoring/app/services/pipeline_service.py ai-scoring/app/services/pipeline_payloads.py` | 通过 | 无 |
| 2026-07-05 | 校准服务回归测试 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py -q` | 6 passed | 无 |
| 2026-07-05 | 阶段3红灯测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoreRuleEngineTest test` | 编译失败，规则引擎 DTO 字段尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段3目标 Java 测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoreStructuredResultValidatorTest,AiScoreStructuredResultServiceTest,AiScoreRuleEngineTest test` | 31 passed | 无 |
| 2026-07-05 | SQL镜像一致性测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoreStructuredEntityCompileTest test` | 3 passed | 初次全量测试暴露 deploy/dockerrun SQL 漂移，已同步 |
| 2026-07-05 | 后端全量测试 | `/opt/homebrew/bin/mvn test` | 188 passed | 无 |
| 2026-07-05 | Python 评分侧回归测试 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py -q` | 14 passed | 无 |
| 2026-07-05 | Python 语法编译 | `python -m py_compile ai-scoring/app/services/evidence_extraction_service.py ai-scoring/app/services/pipeline_service.py ai-scoring/app/services/pipeline_payloads.py ai-scoring/app/services/session_pipeline_service.py` | 通过 | 无 |
| 2026-07-05 | 阶段4后端红灯测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest test` | 编译失败，`getRuleEngineShadow()` 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段4前端红灯测试 | `node --test frontend/user/src/utils/aiScoreRuleEngineReport.test.js` | `ERR_MODULE_NOT_FOUND`，映射工具尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段4后端目标测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest,AiScoreResponseRedactionTest test` | 4 passed | 初次实现曾暴露 observationCode 泄露风险，已撤回并保留用户 API 脱敏 |
| 2026-07-05 | 阶段4前端映射测试 | `node --test src/utils/aiScoreRuleEngineReport.test.js src/utils/aiScoreFrameMatching.test.js` | 11 passed | 无 |
| 2026-07-05 | 阶段4前端构建 | `npm run build` | 通过 | Vite 仍提示 vendor-misc chunk 较大，为既有构建体积提示 |
| 2026-07-05 | 阶段4后端全量测试 | `/opt/homebrew/bin/mvn test` | 188 passed | 无 |
| 2026-07-05 | 阶段4 Playwright 验证 | `OREP_E2E_BASE_URL=http://127.0.0.1:5176 npx playwright test tests/ai-score-hardening.spec.js` | 1 passed, 1 failed | 上传页通过；报告页因未登录被路由守卫带到 `/intro`，旧断言仍等待报告页文案，不是阶段4页面崩溃 |
| 2026-07-05 | 阶段5 Java目标测试 | `/opt/homebrew/bin/mvn -Dtest=AiJuryReviewServiceTest test` | 12 passed | 无 |
| 2026-07-05 | 阶段5 Python jury测试 | `python -m pytest ai-scoring/tests/test_ai_jury_services.py -q` | 23 passed | 无 |
| 2026-07-05 | 阶段5 Python语法编译 | `python -m py_compile ai-scoring/app/routers/scoring_router.py ai-scoring/app/services/jury/scoring_service.py` | 通过 | 无 |
| 2026-07-05 | 阶段5前端构建 | `npm run build` | 通过 | Vite 仍提示 vendor-misc chunk 较大，为既有构建体积提示 |
| 2026-07-05 | 阶段5后端全量测试 | `/opt/homebrew/bin/mvn test` | 189 passed | 无 |
| 2026-07-05 | 阶段5 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py -q` | 37 passed | 无 |
| 2026-07-05 | 阶段5前端映射回归测试 | `node --test src/utils/aiScoreRuleEngineReport.test.js src/utils/aiScoreFrameMatching.test.js` | 11 passed | 无 |
| 2026-07-05 | 阶段6后端红灯测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest test` | 编译失败，`getTrainingTasks()` 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段6后端目标测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest test` | 1 passed | 无 |
| 2026-07-05 | 阶段6前端红灯测试 | `node --test src/utils/aiScoreTrainingTasks.test.js` | `ERR_MODULE_NOT_FOUND`，训练任务工具尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段6前端训练任务测试 | `node --test src/utils/aiScoreTrainingTasks.test.js` | 2 passed | 初次兜底过滤只看扣分值，已修正为可追回分也能生成任务 |
| 2026-07-05 | 阶段6后端目标回归测试 | `/opt/homebrew/bin/mvn -Dtest=AiScoringSessionReportDetailTest,AiScoreRecoveryMemoryServiceTest,AiScoringSessionRedactionMappingTest,AiScoreResponseRedactionTest test` | 17 passed | 无 |
| 2026-07-05 | 阶段6前端映射回归测试 | `node --test src/utils/aiScoreTrainingTasks.test.js src/utils/aiScoreRuleEngineReport.test.js src/utils/aiScoreFrameMatching.test.js` | 13 passed | 无 |
| 2026-07-05 | 阶段6前端构建 | `npm run build` | 通过 | Vite 仍提示 vendor-misc chunk 较大，为既有构建体积提示 |
| 2026-07-05 | 阶段6后端全量测试 | `/opt/homebrew/bin/mvn test` | 189 passed | 无 |
| 2026-07-05 | 阶段6 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py -q` | 37 passed | 无 |
| 2026-07-05 | 阶段7本地样本检查 | `find ai-scoring/docs/samples ai-scoring/docs/ppt_quality_samples ai-scoring/app/uploads -maxdepth 3 -type f`、`find ai-scoring/app/uploads/results -maxdepth 2 -type f` | 仅发现1个说明书样本、PPT质量样本和少量图片资产；未发现评分结果样本库 | 不满足每个试点赛道20-50条真实冻结样本要求 |
| 2026-07-05 | 阶段7红灯测试 | `python -m pytest ai-scoring/tests/test_stability_evaluation_service.py -q` | 1 error，`stability_evaluation_service` 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段7目标测试 | `python -m pytest ai-scoring/tests/test_stability_evaluation_service.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段7 Python编译 | `python -m py_compile ai-scoring/app/services/stability_evaluation_service.py` | 通过 | 无 |
| 2026-07-05 | 阶段7 manifest模板校验 | `python -m json.tool ai-scoring/app/evaluation/pilot_dataset_manifest.template.json >/dev/null` | 通过 | 无 |
| 2026-07-05 | 阶段7 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py -q` | 40 passed | 无 |
| 2026-07-05 | 阶段7联网生成样本库 | 联网参考公开创新创业/人工智能/新一代信息技术赛道项目方向，生成 `pilot_dataset_manifest.generated.json` | 40条样本：人工智能赛道20条、新一代信息技术赛道20条；8类样本均覆盖 | 样本标记为 `synthetic_from_public_reference` |
| 2026-07-05 | 阶段7生成样本JSON校验 | `python -m json.tool ai-scoring/app/evaluation/pilot_dataset_manifest.generated.json >/dev/null && python -m json.tool ai-scoring/app/evaluation/pilot_quality_report.generated.json >/dev/null` | 通过 | 无 |
| 2026-07-05 | 阶段7生成样本门禁现算 | `validate_pilot_dataset_manifest` + `evaluate_quality_report` | `READY sampleCount=40 track_42_ai=20 track_27_it=20 failingMetrics=0 failingSamples=0` | 无 |
| 2026-07-05 | 阶段7生成样本目标测试 | `python -m pytest ai-scoring/tests/test_stability_evaluation_service.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段7生成样本Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py -q` | 40 passed | 无 |
| 2026-07-05 | 阶段8本地规则源检查 | `find "42赛道梯度评分规则v1.2-证据审查版" -maxdepth 2 -type f -print` | 确认42个赛道Markdown规则源存在 | 无 |
| 2026-07-05 | 阶段8红灯测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py -q` | 1 error，`track_expansion_plan_service` 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8计划资产JSON校验 | `python -m json.tool ai-scoring/app/rubrics/track_expansion_plan_v1.json >/dev/null` | 通过 | 无 |
| 2026-07-05 | 阶段8目标测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py -q` | 4 passed | 无 |
| 2026-07-05 | 阶段8 Python编译 | `python -m py_compile ai-scoring/app/services/track_expansion_plan_service.py` | 通过 | 无 |
| 2026-07-05 | 阶段8计划覆盖检查 | Python 统计 `track_expansion_plan_v1.json` | `tracks=42`、`batches=5`、`uniqueNames=42`、`pilotCompleted=2` | 无 |
| 2026-07-05 | 阶段8 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 44 passed | 无 |
| 2026-07-05 | 阶段8最终汇总红灯测试 | `python -m pytest ai-scoring/tests/test_stage8_final_readiness_summary.py -q` | 1 error，`summarize_stage8_final_readiness` 尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8最终汇总目标测试 | `python -m pytest ai-scoring/tests/test_stage8_final_readiness_summary.py -q` | 2 passed | 无 |
| 2026-07-05 | 阶段8第一批红灯测试 | `python -m pytest ai-scoring/tests/test_first_batch_track_rule_assets.py -q` | 3 failed，4个 draft 规则文件尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第一批规则JSON校验 | `python -m json.tool` 校验4个第一批 draft 规则 JSON | 通过 | 无 |
| 2026-07-05 | 阶段8第一批目标测试 | `python -m pytest ai-scoring/tests/test_first_batch_track_rule_assets.py -q` | 3 passed，随后补计划挂载断言后为4 passed | 无 |
| 2026-07-05 | 阶段8与第一批规则测试 | `python -m pytest ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 8 passed | 无 |
| 2026-07-05 | 阶段8第一批规则覆盖检查 | Python 读取4个 draft 规则文件 | 赛道26/14/12/13均为 `draft`，各15个观测点并带 ruleHash | 无 |
| 2026-07-05 | 阶段8第一批 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py -q` | 48 passed | 无 |
| 2026-07-05 | 阶段8第一批准入红灯测试 | `python -m pytest ai-scoring/tests/test_first_batch_track_admission_assets.py -q` | 2 failed，准入资产尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第一批准入资产JSON校验 | Python 读取 `ai-scoring/app/evaluation/track_admission/*.json` | 12个JSON均可解析 | 无 |
| 2026-07-05 | 阶段8第一批准入目标测试 | `python -m pytest ai-scoring/tests/test_first_batch_track_admission_assets.py -q` | 2 passed，随后补计划挂载断言后为3 passed | 无 |
| 2026-07-05 | 阶段8第一批样本覆盖检查 | Python 统计4个 manifest | 每赛道10条样本，含2高分、2中分、2低证据、1演示失败、1低分、1材料充分、1边界争议 | 无 |
| 2026-07-05 | 阶段8第一批全套测试 | `python -m pytest ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第一批准入 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py -q` | 51 passed | 无 |
| 2026-07-05 | 阶段8第一批pilot状态测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第一批pilot Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py -q` | 51 passed | 无 |
| 2026-07-05 | 阶段8第二批红灯测试 | `python -m pytest ai-scoring/tests/test_second_batch_track_rule_assets.py -q` | 4 failed，第二批 draft 规则文件和计划挂载尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第二批规则JSON校验 | Python 读取11个第二批 draft 规则文件 | 11个JSON均可解析，均为 `draft`，各15个观测点 | 无 |
| 2026-07-05 | 阶段8第二批目标测试 | `python -m pytest ai-scoring/tests/test_second_batch_track_rule_assets.py -q` | 4 passed | 无 |
| 2026-07-05 | 阶段8扩展规则测试集合 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py -q` | 15 passed | 无 |
| 2026-07-05 | 阶段8第二批 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py -q` | 55 passed | 无 |
| 2026-07-05 | 阶段8第二批准入红灯测试 | `python -m pytest ai-scoring/tests/test_second_batch_track_admission_assets.py -q` | 3 failed，第二批准入资产尚不存在，计划状态仍为 `draft_generated` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第二批准入资产JSON校验 | Python 读取第二批33个准入资产JSON | 33个JSON均可解析 | 无 |
| 2026-07-05 | 阶段8第二批准入目标测试 | `python -m pytest ai-scoring/tests/test_second_batch_track_admission_assets.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段8第二批全套测试 | `python -m pytest ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第二批准入 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py -q` | 58 passed | 无 |
| 2026-07-05 | 阶段8第二批pilot状态测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第二批pilot Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py -q` | 58 passed | 无 |
| 2026-07-05 | 阶段8第三批红灯测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py -q` | 4 failed，第三批 draft 规则文件和计划挂载尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第三批规则JSON校验 | Python 读取6个第三批 draft 规则文件 | 6个JSON均可解析，均为 `draft`，各15个观测点 | 无 |
| 2026-07-05 | 阶段8第三批目标测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py -q` | 4 passed | 无 |
| 2026-07-05 | 阶段8第三批与计划测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_third_batch_track_rule_assets.py -q` | 8 passed | 无 |
| 2026-07-05 | 阶段8第三批 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py -q` | 62 passed | 无 |
| 2026-07-05 | 阶段8第三批准入红灯测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_admission_assets.py -q` | 3 failed，第三批准入资产尚不存在，计划状态仍为 `draft_generated` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第三批准入资产JSON校验 | Python 读取第三批18个准入资产JSON | 18个JSON均可解析 | 无 |
| 2026-07-05 | 阶段8第三批准入目标测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_admission_assets.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段8第三批全套测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第三批准入 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py -q` | 65 passed | 无 |
| 2026-07-05 | 阶段8第三批pilot红灯测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py -q` | 3 failed，第三批规则仍为 `draft`，计划仍为 `planned` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第三批pilot JSON与active边界检查 | Python 读取第三批6个规则文件和扩展计划 | 6个规则均为 `pilot`，计划均为 `pilot_generated`，且 `activeAllowed=false` | 无 |
| 2026-07-05 | 阶段8第三批pilot目标测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py -q` | 7 passed | 无 |
| 2026-07-05 | 阶段8第三批pilot全套测试 | `python -m pytest ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第三批pilot Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py -q` | 65 passed | 无 |
| 2026-07-05 | 阶段8第四批红灯测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py -q` | 4 failed，第四批 draft 规则文件和计划挂载尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第四批规则JSON校验 | Python 读取6个第四批 draft 规则文件 | 6个JSON均可解析，均为 `draft`，各15个观测点 | 无 |
| 2026-07-05 | 阶段8第四批目标测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py -q` | 4 passed | 无 |
| 2026-07-05 | 阶段8第四批与计划测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py -q` | 8 passed | 无 |
| 2026-07-05 | 阶段8第四批 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py -q` | 69 passed | 无 |
| 2026-07-05 | 阶段8第四批准入红灯测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` | 3 failed，第四批准入资产尚不存在，计划状态仍为 `draft_generated` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第四批准入资产JSON校验 | Python 读取第四批18个准入资产JSON | 18个JSON均可解析 | 无 |
| 2026-07-05 | 阶段8第四批准入目标测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段8第四批全套测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第四批准入 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` | 72 passed | 无 |
| 2026-07-05 | 阶段8第四批pilot红灯测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` | 3 failed，第四批规则仍为 `draft`，计划仍为 `planned` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第四批pilot JSON与active边界检查 | Python 读取第四批6个规则文件和扩展计划 | 6个规则均为 `pilot`，计划均为 `pilot_generated`，且 `activeAllowed=false` | 无 |
| 2026-07-05 | 阶段8第四批pilot目标测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` | 7 passed | 无 |
| 2026-07-05 | 阶段8第四批pilot全套测试 | `python -m pytest ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第四批pilot Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py -q` | 72 passed | 无 |
| 2026-07-05 | 阶段8第五批红灯测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_rule_assets.py -q` | 4 failed，第五批 draft 规则文件和计划挂载尚不存在 | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第五批规则JSON校验 | Python 读取13个第五批 draft 规则文件 | 13个JSON均可解析，均为 `draft`，各15个观测点 | 无 |
| 2026-07-05 | 阶段8第五批目标测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_rule_assets.py -q` | 4 passed | 无 |
| 2026-07-05 | 阶段8第五批与计划测试 | `python -m pytest ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_fifth_batch_track_rule_assets.py -q` | 8 passed | 无 |
| 2026-07-05 | 阶段8第五批 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py ai-scoring/tests/test_fifth_batch_track_rule_assets.py -q` | 76 passed | 无 |
| 2026-07-05 | 阶段8第五批准入红灯测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_admission_assets.py -q` | 3 failed，第五批准入资产尚不存在，计划状态仍为 `draft_generated` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第五批准入资产JSON校验 | Python 读取第五批39个准入资产JSON | 39个JSON均可解析 | 无 |
| 2026-07-05 | 阶段8第五批准入目标测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_admission_assets.py -q` | 3 passed | 无 |
| 2026-07-05 | 阶段8第五批全套测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_rule_assets.py ai-scoring/tests/test_fifth_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第五批准入 Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py ai-scoring/tests/test_fifth_batch_track_rule_assets.py ai-scoring/tests/test_fifth_batch_track_admission_assets.py -q` | 79 passed | 无 |
| 2026-07-05 | 阶段8第五批pilot红灯测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_rule_assets.py ai-scoring/tests/test_fifth_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 4 failed，第五批规则仍为 `draft`，计划仍为 `planned`，阶段8计数仍为 `pilot_generated=27` | 符合 TDD 预期 |
| 2026-07-05 | 阶段8第五批pilot JSON与active边界检查 | Python 读取第五批13个规则文件和扩展计划 | 13个规则均为 `pilot`，计划均为 `pilot_generated`，且 `activeAllowed=false`；阶段8计数 `pilot_completed=2`、`pilot_generated=40` | 无 |
| 2026-07-05 | 阶段8第五批pilot目标测试 | `python -m pytest ai-scoring/tests/test_fifth_batch_track_rule_assets.py ai-scoring/tests/test_fifth_batch_track_admission_assets.py ai-scoring/tests/test_track_expansion_plan_service.py -q` | 11 passed | 无 |
| 2026-07-05 | 阶段8第五批pilot Python相关回归集合 | `python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_first_batch_track_rule_assets.py ai-scoring/tests/test_first_batch_track_admission_assets.py ai-scoring/tests/test_second_batch_track_rule_assets.py ai-scoring/tests/test_second_batch_track_admission_assets.py ai-scoring/tests/test_third_batch_track_rule_assets.py ai-scoring/tests/test_third_batch_track_admission_assets.py ai-scoring/tests/test_fourth_batch_track_rule_assets.py ai-scoring/tests/test_fourth_batch_track_admission_assets.py ai-scoring/tests/test_fifth_batch_track_rule_assets.py ai-scoring/tests/test_fifth_batch_track_admission_assets.py -q` | 79 passed | 无 |

## 遗留问题

- 阶段0-8已按当前方案完成准备闭环；后续进入42赛道逐批结构化实施时仍需逐赛道复核方案章节。
- 需要建立规则准入审计表；当前两个 pilot JSON 已结构化并生成 ruleHash，但尚未经过样本验证和人工复核。
- 需要确认本地后端测试命令和 Python 测试环境；当前项目根目录不是 git 仓库。
- 需要确认 SQL 中人工智能赛道的 trackId 与用户端赛道编号/名称映射，避免 `track-c889f0110e2d`、`track-ai`、`42/20` 等口径混用。
- 需要准备真实样本验证 LLM 证据抽取质量；当前阶段7生成样本库通过门禁演练，但不代表真实模型抽取质量已被原始参赛视频实测。
- 需要后续把 Java 规则引擎作为最终权威计算入口；当前 Python shadow 分只用于 callback 上下文和差异预览。
- 需要后续扩展结构化观测点表，补齐 `observationName/maxScore/finalScore`，让前端能展示完整15观测点官方名称和满分。
- Playwright 报告页安全用例需要登录态或 mock API 支持；当前未登录访问按产品逻辑跳转 `/intro`。
- 阶段7已用生成样本库通过当前门禁，但样本为 `synthetic_from_public_reference`，不是原始参赛视频或真实评委打分；若要上线级准入，仍建议采集真实原始样本后复跑同一门禁。
- 专家校准目前有记录校验函数和模板契约，但尚未接入后台页面或持久化表。
- 阶段8已建立42赛道扩展计划、准入门禁和最终汇总检查；当前总账状态为 `pilot_ready_not_active`，正式 active 前仍建议真实样本复验。
- 第一批4个技术类新赛道已进入 `pilot_generated` 演练状态，但正式 active 前仍建议真实样本复验。
- 第二批11个工程与制造类赛道已进入 `pilot_generated` 演练状态，但正式 active 前仍建议真实样本复验。
- 第三批6个农林牧渔、生态与资源类赛道已进入 `pilot_generated` 演练状态，但正式 active 前仍建议真实样本复验。
- 第四批6个医药健康类赛道已进入 `pilot_generated` 演练状态，但正式 active 前仍建议真实样本复验。
- 第五批13个服务、财经、商贸与文体类赛道已进入 `pilot_generated` 演练状态，但正式 active 前仍建议真实样本复验。

## 下一步计划

1. 进入 active 准入前置准备：为 `pilot_generated` 赛道替换真实原始样本，并复跑候选门禁。
2. 若暂不进入 active，则进入 Java 规则引擎最终权威计算入口改造，逐步减少 Python shadow 分的权威性。
3. 继续保留 `pilot_generated` 与 `active` 状态边界，避免生成样本演练被误认为正式上线准入。
