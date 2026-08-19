# AI 评分功能升级方案

| 文档属性 | 内容 |
|----------|------|
| 产品 | 竞赛大脑 / OREP |
| 模块 | AI 评分（上传路演 → 流水线 → 评分报告 → 改进） |
| 版本 | v1.0 |
| 状态 | 已合并进 2.0；本文保留作工程现状长描述 |
| 日期 | 2026-08-08 |
| 范围 | 后端 Java、`ai-scoring` Python、学生/教师前端评分报告与上传 |
| **执行主文档** | **[`AI评分功能升级方案-v2.0.md`](./AI评分功能升级方案-v2.0.md)**（评价议会 × 工程底座） |

---

## 0. 执行摘要

### 0.1 问题定义

市场与通用 Agent（Codex、Cursor、通用多模态助手）已能在**单次会话**内完成「视频/转写 + 评分表 → 中文评分报告」。用户若仅以「能否生成一份像样的报告」评价产品，会将竞赛大脑与通用工具**等价化**。

本方案的目标不是在「文笔更好」上与通用模型竞赛，而是将 AI 评分从：

> **一次性报告生成器**

升级为：

> **证据驱动的路演能力账本（Score Ledger）+ 组织内可审计评价 + 改进闭环操作系统**

### 0.2 结论（给决策用）

| 判断 | 说明 |
|------|------|
| 当前资产 | 已具备完整 **上传 → Session → Python 流水线 → 回调落库 → 报告 API → 四 Tab UI**，并含 **loss ledger / 改进任务 v3 / 证据锚点 / 说话人归因 / 评审团** 等超前基建 |
| 核心风险 | 产品叙事与默认体验仍偏「结果页像报告」；证据可点击回放、跨次对比、任务→再评闭环未成为**硬约束与默认路径** |
| 升级方向 | L1 感知层可插拔（跟进民用模型）；差异化押注 **L2 账本 / L3 闭环 / L4 组织治理** |
| 周期建议 | P0 体验与契约加固 6–10 周；P1 闭环与对比 1–2 季度；P2 组织与常模 2–4 季度 |

### 0.3 本文结构

1. **现状**：结构、逻辑、能力与缺口（基于当前代码）  
2. **方向**：目标架构、产品原则、非目标  
3. **实现路径**：阶段、关键节点、依赖、风险  
4. **基准与验收**：量化指标与质量门禁  

---

## 1. 现状：结构、逻辑与能力边界

### 1.1 总体架构（当前）

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│ 学生/教师前端    │────▶│  Java Backend     │────▶│  ai-scoring (FastAPI)   │
│ 上传 + 报告 UI   │◀────│  /api/ai-score/*  │◀────│  /api/ai/score-session  │
└─────────────────┘     │  Session/Report   │     │  ASR·视觉·LLM·规则·账本 │
                        │  落库 + 权限       │     │  pipeline-callback      │
                        └──────────────────┘     └─────────────────────────┘
```

| 层 | 职责 | 关键路径 |
|----|------|----------|
| 前端用户端 | 上传、轮询状态、报告四 Tab、待办状态 | `frontend/user/src/views/VideoScoreUpload.vue`、`views/ai-score-report/*`、`composables/useAiScoreReport.js` |
| 前端教师端 | 上传与任务队列；报告深链进学生端 | `frontend/teacher/.../VideoScoreUploadView.vue` |
| Java API | Session 生命周期、媒体存储、回调落库、报告聚合、权限 | `AiScoreUploadController`、`AiScoreController`、`AiScoringSessionService` |
| Python 流水线 | 媒体理解、评分、账本与改进包、进度回调 | `session_pipeline_service.py`、`pipeline_service.py` |
| 数据层 | Session / Report / 锚点 / 任务 / 说话人 / 评审团 | `ai_scoring_session`、`ai_score_report`、`ai_score_evidence_anchor` 等 |

### 1.2 主路径逻辑（上传评分 · 现行主链路）

```text
1. POST /api/ai-score/upload-session
     · 创建 AiScoringSession（绑定赛道 track + 量表 rubric 版本/哈希）
     · 存储视频/材料 → ai_score_media_asset
     · status: created → uploaded → scoring(stage=queued)

2. Java AiScoringPipelineClient
     · POST {AI_SCORING_BASE_URL}/api/ai/score-session
     · 携带 sessionId、track/rule 绑定、视频路径、材料、juryEnabled
     · callbackUrl = {BACKEND}/api/ai-score/sessions/{id}/pipeline-callback
     · 注意：当前固定 publishOfficialScore=false（诊断权限，非官方终态锁分）

3. Python run_session_pipeline
     · 抽帧 → 隔离子进程跑 run_scoring_pipeline
     · 进度写 progress 文件并回调 Java（asr / frame / model_scoring / report…）
     · 完成：构建 finalResult（分、账本、锚点、转写、说话人…）+ 完成回调

4. Java processPipelineCallback
     · 对账校验 → 转写/说话人落库 → upsert ai_score_report
     · v3：remediation 任务、loss 关联、证据锚点、observation/deduction
     · session → completed + reportId

5. 前端
     · 轮询 GET /sessions/{id}/status
     · GET /reports/by-session/{id}
     · Tab：结果 / 待办 / 依据 / 评审团（+ 对比路由）
```

**并行路径（需在方案中统一，避免双真相）：**

- Java `POST .../structured-result` + `AiScoreRuleEngine`（p8-c）：服务端规则算分  
- 遗留 meeting 维度 `POST /api/ai-score/callback`、`GET /report/{meetingId}`  
- 实时会议评分 / WebSocket ASR（`scoring_router` 等，与上传 Session 主产品并存）

### 1.3 Python 流水线阶段（感知与评分）

| 阶段 | 内容 | 代表模块 |
|------|------|----------|
| 音轨 | 转码 WAV | `audio_service` |
| ASR + 说话人 | 转写、分离、主动说话人融合、3D-Speaker 等 | `media_evidence/*`、`asr_service` |
| 语音质量 | 语速/停顿等 | `speech_analysis_service` |
| 视觉 | 抽帧 / VLM 分析 | `video_analysis_service`、`visual_frame_selector` |
| 融合 | 音视频证据融合 | `fusion_service` |
| LLM 评分 | 大模型打分与叙述 | `llm_scoring_service` |
| 结构化证据 | 观察/扣分/锚点抽取 | `evidence_extraction_service` |
| 规则/账本 | 规则 shadow、loss ledger、改进图、覆盖率 | `scoring/*`、`pipeline_payloads` |
| 校准 / 画像 | 竞赛校准、角色画像 | `competition_calibration_service`、`character_profile_service` |
| 报告 | PDF 等产物 | `report_service` |
| 评审团（可选） | 多 Persona 并行评 | `jury/*` |

**分权（authority）现状要点：**

- 有可发布的结构化规则结果时，倾向 **structured / diagnostic_rule_engine**  
- Java 现网客户端 **`publishOfficialScore=false`** → 多为 **诊断权限**，与产品口语「官方分」可能不一致  
- 提取失败可进入 `review_required`，避免硬给权威总分  

### 1.4 报告与「半闭环」数据模型（已有）

| 概念 | 存储 / 契约 | 用途 |
|------|-------------|------|
| 维度分与叙述 | `ai_score_report` JSON 字段 | 结果页 |
| 证据锚点 | `ai_score_evidence_anchor` + 回调 `evidenceAnchors[]` | 「依据」Tab |
| 观察 / 扣分 | `ai_score_observation` / `ai_score_deduction` | 结构化理由 |
| Loss 账本 | `loss_ledger` + v3 规范化 | 可行动损失项 |
| 改进任务 | `action_plan` + `ai_score_remediation_task` 等 | 「待办」Tab |
| 覆盖率 / 回分投影 | `coverage_summary` / `score_projection` | 若改完可回多少分 |
| 任务状态 | PATCH remediation-tasks status；可标 awaiting_rerun | 弱闭环 |
| 跨次核验 | `AiScoreRemediationService` 新 Session 完成时逻辑 | 有限 |
| 说话人 | identity / turn / transcript segment | 归因与展示 |
| 评审团 | 独立 jury 表，**不替代** report 主分 | 多视角评语 |
| 量表绑定 | `track_rubric_config` + ruleVersion/hash | 赛道规则 |

前端路由形态（用户端）：

- `/ai-score/report/:sessionId/{result|todos|why|jury|compare}`  
- 数据编排：`useAiScoreReport.js`（轮询 + 报告 + 可选遗留 Python result 补全）

### 1.5 现状能力评估（相对目标态）

| 能力 | 成熟度 | 说明 |
|------|--------|------|
| 端到端出报告 | ★★★★☆ | 主链路完整，生产可用 |
| 赛道量表绑定 | ★★★★☆ | 版本/哈希绑定；执行质量因赛道可能不均 |
| 多模态感知 | ★★★★☆ | ASR/分离/抽帧/VLM 栈深，运维成本高 |
| Loss 账本 + 待办 | ★★★☆☆ | v3 契约与表已有；与训练系统耦合弱 |
| 证据可回放 | ★★☆☆☆ | 有锚点与 Why；与视频秒级强绑定、FK 完整性不足 |
| 跨次对比 | ★★☆☆☆ | 有 Compare 路由与工具函数；非常模化主路径 |
| 教师共评审计 | ★★☆☆☆ | 说话人可改；改分/驳回证据未成完整协议 |
| 官方锁分 / 责任边界 | ★☆☆☆☆ | 诊断分默认；组织治理层薄 |
| 与通用 Agent 差异的**用户可感知度** | ★★☆☆☆ | 基建超前于叙事与默认 UI |

### 1.6 结构性问题（必须在升级中处理）

1. **双引擎 / 多入口**：Python 账本路径、Java p8-c、遗留 meeting 回调并存 → 真相源不清。  
2. **证据层未「契约化」**：`prepare-evidence` 多只冻媒体哈希；锚点与 transcript/frame 关联弱 → 难做「点哪跳哪」的硬体验。  
3. **闭环断在「再上传整场」**：待办状态有了，但缺少「任务包 → 定向补录 → 仅核验关联 loss」的产品状态机。  
4. **评审团旁路**：不进入 ledger / 不驱动任务。  
5. **诊断 vs 官方**：代码与产品话术可能冲突，影响 ToB 信任。  
6. **运维脆弱点**：如 PDF 本地路径硬编码、共享卷 `file-root`、重模型依赖等。  

### 1.7 与「通用 Agent 出报告」的真实差距（基于现状）

| 维度 | 通用 Agent | 竞赛大脑现状 | 用户是否容易感知 |
|------|------------|--------------|------------------|
| 单次文案报告 | 强 | 强 | 否（像） |
| 赛道量表版本绑定 | 弱 | 强 | 弱（需 UI 明示） |
| 结构化 loss + 待办 | 弱 | 中强 | 中（有 Todos） |
| 可点击证据回放 | 弱 | 中弱 | **关键缺口** |
| 班级/营期口径 | 无 | 中（有数据位） | 弱 |
| 改进是否进入训练系统 | 无 | 弱耦合 | **关键缺口** |
| 教师责任与审计 | 无 | 弱 | **关键缺口** |

---

## 2. 升级方向

### 2.1 目标陈述

**将 AI 评分升级为「路演能力卷宗（Score Session Dossier）系统」：**

- 每一次评分是一份**可审计卷宗**，不是一篇可复制长文。  
- 每一条关键结论绑定**可回放证据**（时间轴优先）。  
- 每一次结果默认进入**改进动作**，并支持**复评核验**。  
- 面向班级/营期提供**统一口径与教师共评**，形成不得不买的组织理由。

### 2.2 分层目标架构（3 年形态，分阶段落地）

```text
L4 组织层   租户/营期/权限/量表版本治理/导出/审计/常模
L3 闭环层   问题→任务→训练/补录→再评→兑现率
L2 账本层   维度分 + Loss + 证据锚点 + 历史轨迹 + 基线对比
L1 感知层   ASR / 视觉 / 说话人 / 材料解析（模型可替换）
```

| 层 | 1–3 年策略 |
|----|------------|
| L1 | **跟随民用最强模型**；标准化 I/O；崩溃隔离与降级已有基础，继续工程化 |
| L2 | **主战场**：证据契约、不可篡改 loss、跨次对比 API |
| L3 | **留存战场**：与训练日/任务/资源中心打通；状态机产品化 |
| L4 | **采购战场**：教师工作台、口径、审计、导出 |

### 2.3 产品原则（铁律）

1. **证据优先于文案**：无合格证据不得输出决断性极端分（标「信息不足 / 待人工」）。  
2. **单一评分真相源**：明确「主引擎」；废弃或降级双写路径。  
3. **账本不可悄悄改写**：改分/驳回必须审计；历史报告冻结。  
4. **闭环默认开启**：完成评分默认生成可执行任务，而非仅展示段落。  
5. **模型可插拔，契约不可插拔**：换 LLM 不得破坏 anchor / loss / task schema。  
6. **对内指标优先于「像评委」观感**：见第 4 章基准。

### 2.4 非目标（本阶段不做或明确延后）

- 与通用模型比拼「散文评语文采」作为 KPI。  
- 全自动替代教师终裁（做**共评**，不做甩锅全自动）。  
- 一次上线完美 42 赛道同等深度（按赛道分优先级）。  
- 在本方案内重做整站训练系统（只定义**评分侧对接契约**）。

### 2.5 目标用户价值（不得不买）

| 角色 | 不得不买的理由 |
|------|----------------|
| 学生 | 知道「哪一秒、哪条证据」导致失分；看得见进步；自动知道下一步练什么 |
| 教师 | 全班同口径；可改判可追溯；批改时间下降；可导出教务材料 |
| 机构 | 过程可审计；量表版本可控；数据在组织内沉淀，不在个人对话框蒸发 |

---

## 3. 实现路径与关键节点

### 3.1 总览：四期路线

| 阶段 | 周期（建议） | 主题 | 用户可感知结果 |
|------|--------------|------|----------------|
| **P0** | 6–10 周 | 契约统一 + 证据优先体验 + 叙事纠偏 | 「这不是 ChatGPT 粘贴」 |
| **P1** | 1–2 季度 | 对比账本 + 改进闭环打通训练 | 「评完就有练、再录能对照」 |
| **P2** | 2–3 季度 | 教师共评与组织治理 | 「班/营必须用系统」 |
| **P3** | 并行 entring P2 | 常模/API/多模型治理 | 「越用越像我们的标准」 |

以下节点均绑定**现有模块**，避免空中楼阁。

---

### 3.2 P0 — 夯实差异可感知（必做）

#### 节点 P0-1：评分真相源裁决

| 项 | 内容 |
|----|------|
| 动作 | 文档化并代码固化：**主路径 = Python Session 流水线 + `ai-score-report-v3` 回调**；Java `structured-result` 标记为兼容/内部；遗留 meeting 回调进入 deprecation 清单 |
| 涉及 | `AiScoringPipelineClient`、`AiScoringSessionService`、`AiScoreRuleEngine`、前端 `useAiScoreReport` 对遗留 `/api/ai/result` 的补全策略 |
| 产出 | 《评分权威（Authority）说明》：diagnostic vs official 字段与 UI 文案一致 |
| 验收 | 新 Session 100% 可追溯 `contractVersion` + `scoreAuthority`；双引擎同 Session 不打架 |

#### 节点 P0-2：证据契约 v1（Evidence Contract）

| 项 | 内容 |
|----|------|
| 动作 | 规范锚点最小字段：`dimensionKey?`、`lossId?`、`startMs/endMs`、`quote/text`、`mediaRef`、`confidence`、`validity`；回调写入后尽量回填 `transcriptSegmentId` / `frameId` |
| 涉及 | `evidence_extraction_service`、回调 DTO、`persistEvidenceAnchors`、`AiScoreReportWhy` |
| 产出 | OpenAPI/JSON Schema；无效锚点过滤规则 |
| 验收 | 见 §4.2 证据覆盖率门禁 |

#### 节点 P0-3：报告 UI — 证据优先信息架构

| 项 | 内容 |
|----|------|
| 动作 | 结果页默认：**视频时间轴 + 维度条 + 证据卡**；综评折叠；无证据维度展示「信息不足」而非硬分 |
| 涉及 | `AiScoreReportResult.vue`、`AiScoreReportWhy.vue`、`useAiScoreReport.js`、播放器跳转 |
| 产出 | 交互稿 + 前端实现；埋点：证据点击率 |
| 验收 | §4.3 体验基准 |

#### 节点 P0-4：产品叙事与入口

| 项 | 内容 |
|----|------|
| 动作 | 介绍页/上传页/报告标题：从「AI 生成报告」改为「路演诊断与改进账本」；明示量表版本与诊断/正式状态 |
| 涉及 | 学生端文案、教师上传页 |
| 验收 | 关键文案评审通过；无「一键秒出官方终裁」误导 |

#### 节点 P0-5：可观测与对账

| 项 | 内容 |
|----|------|
| 动作 | Session 级：阶段耗时、authority、锚点数量、ledger 条数、回调失败重试；统一失败码 |
| 涉及 | `pipeline-callback`、progress、日志/指标 |
| 验收 | 任一失败 Session 可在 5 分钟内定位阶段 |

**P0 退出标准：** 新用户完成一次上传后，**无需讲解**即可完成「点证据跳转视频」；对内证据覆盖率达标。

---

### 3.3 P1 — 账本对比与改进闭环（护城河）

#### 节点 P1-1：跨次对比 API 与 UI 主路径化

| 项 | 内容 |
|----|------|
| 动作 | `GET` 同用户/同项目下历史 Session 维度差分、弱项兑现；Compare Tab 成为默认推荐入口（第二次及以后） |
| 涉及 | `reports/summary`、新 comparison API、`AiScoreReportCompare.vue` |
| 验收 | §4.4 对比基准 |

#### 节点 P1-2：Loss → 训练任务对接

| 项 | 内容 |
|----|------|
| 动作 | remediation task 生成时写入**可执行链接**：训练日 / 资源 / 限时补录任务；状态与 `AiScoreRemediationService` 对齐 |
| 涉及 | `remediation_planner`、Java remediation 表、训练模块 API |
| 验收 | §4.5 闭环基准（生成率） |

#### 节点 P1-3：复评状态机（最小闭环）

| 状态 | 含义 |
|------|------|
| `open` | 待完成 |
| `done_pending_rerun` | 学生声称完成，等待再评 |
| `verified_improved` | 新 Session 核验改善 |
| `verified_not_improved` | 核验未改善 |
| `dismissed` | 教师关闭 |

| 项 | 内容 |
|----|------|
| 动作 | 再上传/再评时自动关联 prior session + open losses；报告增加「改进对照」块 |
| 验收 | §4.5 核验基准 |

#### 节点 P1-4：材料证据一等公民（可选并行）

| 项 | 内容 |
|----|------|
| 动作 | PPT/PDF 关键页/条款进入锚点类型；与视频锚点并列展示 |
| 验收 | 材料类赛道锚点占比门槛 |

**P1 退出标准：** 同一学生两次路演后，系统**自动**展示弱项是否改善，且至少一类任务可从报告跳进训练完成。

---

### 3.4 P2 — 教师共评与组织治理（采购理由）

#### 节点 P2-1：共评协议

| 动作 | AI 初评 + 证据；教师：采信 / 驳回锚点 / 改分 / 必填理由；全量审计日志 |
| 涉及 | 新 API + 教师端审阅 UI（可深链增强，不必重做整站报告） |
| 验收 | §4.6 |

#### 节点 P2-2：官方锁分模式

| 动作 | 配置项：`publishOfficialScore` 按租户/营开启；锁分后只读 + 变更走申诉流 |
| 涉及 | `AiScoringPipelineClient`、Session 状态机 |
| 验收 | 锁分后学生端不可静默变更总分 |

#### 节点 P2-3：量表版本治理

| 动作 | 历史报告冻结 ruleHash；切换 v1.2 新版不影响旧档案展示 |
| 验收 | 旧报告打开仍显示评分时版本元数据 |

#### 节点 P2-4：班级/营导出

| 动作 | 汇总表、个人卷宗 PDF/ZIP、抽检清单 |
| 验收 | 教师 30 人班导出 < 3 分钟（性能基线可调） |

**P2 退出标准：** 教师可用系统完成「抽检 20% + 改判 + 导出」完整教务动作，无需导出到 ChatGPT。

---

### 3.5 P3 — 常模、开放与长期壁垒（前瞻）

- 租户内/跨租户匿名赛道分位（合规前提）  
- 租户级「改判样本」反哺规则权重或 few-shot（非玄学黑盒）  
- Score Ledger API：训练行为写入、外部系统只读成长曲线  
- L1 多模型路由与 A/B（质量门禁卡发布）  

---

### 3.6 工程关键依赖与风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 流水线过重（本地分离/ASD） | 成本与稳定性 | 分级：快评模式 / 精评模式；云端可关重模型 |
| 双引擎残留 | 数据混乱 | P0-1 强制收敛 |
| 训练模块接口不齐 | 闭环空转 | P1 允许「站内待办」降级，接口就绪再深链 |
| 证据幻觉 | 信任崩盘 | 覆盖率 + 无效锚点剔除 + 抽检 |
| 通用 Agent 叙事战 | 获客 | P0-4 必须与研发同步上线 |
| DDL 与 Flyway 不统一 | 环境漂移 | 专项：AI 评分表纳入可控迁移 |

### 3.7 建议组织方式

| 角色 | 职责 |
|------|------|
| 产品 | 铁律、文案、Tab 信息架构、教师流程 |
| 后端 | 权威字段、锚点落库、对比 API、审计、状态机 |
| AI | 证据抽取质量、ledger 完整性、降级策略 |
| 前端 | 证据优先 UI、跳秒、对比与任务 CTA |
| 质量 | §4 门禁自动化 + 人工抽检集 |

---

## 4. 基准与具体要求

### 4.1 指标分层

| 类型 | 用途 |
|------|------|
| **门禁指标（Go/No-Go）** | 未达标不得发版宣传「证据/闭环」 |
| **健康指标** | 周会追踪 |
| **北向指标** | 季度看产品是否跑赢「通用 Agent 心智」 |

---

### 4.2 证据与结构化（P0 门禁）

在**金标评测集**（建议 ≥ 30 场、覆盖 ≥ 5 赛道、含单人/多人）上：

| 指标 | 定义 | P0 目标 | P1 目标 |
|------|------|---------|---------|
| **维度证据覆盖率** | 有分数的维度中，存在 ≥1 条 `validity=valid` 且含时间或可定位引用的锚点占比 | ≥ **70%** | ≥ **85%** |
| **无证据决断率** | 无 valid 锚点却给极端分（如满分或零分档）的维度占比 | ≤ **5%** | ≤ **2%** |
| **锚点可跳转率** | 前端点击后成功落到视频时间或转写句的占比 | ≥ **90%** | ≥ **95%** |
| **Loss 可行动率** | ledger 中带可执行 acceptance / 任务映射的条目占比 | ≥ **80%** | ≥ **90%** |
| **契约完整率** | 完成态报告含 `contractVersion` + authority + ledger 或明确 `review_required` | **100%** | **100%** |

人工抽检（每版本 ≥ 20 条锚点）：

| 指标 | 要求 |
|------|------|
| 锚点时间误差 | 中位误差 ≤ **3s**（口播类）；画面类按帧索引可接受 ≤ **1 关键帧间隔** |
| 锚点与结论相关性 | 抽检相关率 ≥ **80%**（双人标注一致） |

---

### 4.3 体验与性能（P0）

| 指标 | 要求 |
|------|------|
| 首次结果可交互 | 进度回调阶段可见；不出现长时间无阶段的「假死」 |
| 报告首屏 | 有分、有维度、有「依据」入口；综评不占据首屏 50% 以上 |
| 证据点击 | 从列表到起播/高亮 ≤ **2s**（媒体已缓存时） |
| 端到端时长 | 在现行硬件基线上：相对升级前 **不劣化 > 15%**；提供「快评」可选降级 |
| 失败可理解 | 失败页展示阶段 + 建议动作（重试 / 检查音频 / 联系老师） |

---

### 4.4 对比与档案（P1）

| 指标 | 要求 |
|------|------|
| 二次路演自动对比 | 同用户存在 prior completed session 时，**默认展示**对比模块 |
| 弱项追踪 | 上次低于阈值的维度，下次报告必须出现 improve / stagnate / worsen 三态之一 |
| 历史查询 | 支持按项目/队伍筛选最近 N 次（N≥5） |

---

### 4.5 闭环（P1–P2）

| 指标 | 定义 | 目标 |
|------|------|------|
| **任务生成率** | completed 且非 review_only 的报告中，生成 ≥1 条 open 任务占比 | ≥ **90%** |
| **任务可到达率** | 任务 CTA 可进入站内可完成对象（训练/补录/资源）占比 | P1 ≥ **60%**；P2 ≥ **85%** |
| **再评关联率** | 标记 awaiting_rerun 后新 Session 成功关联 prior losses 占比 | ≥ **95%** |
| **兑现可计算** | verified_* 状态可由系统自动给出，不依赖纯人工填「是否进步」 | P1 试点赛道打通 |

---

### 4.6 教师与组织（P2）

| 指标 | 要求 |
|------|------|
| 改判审计 | 100% 改分/驳回有 actor、时间、前后值、理由 |
| 抽检工作流 | 支持按维度/低置信度筛选待审列表 |
| 锁分 | 官方模式下锁分后学生 API 只读 |
| 导出 | 营期汇总 + 个人要点导出格式固定并文档化 |

---

### 4.7 质量与安全（持续）

| 项 | 要求 |
|----|------|
| 回归集 | 流水线关键阶段单测 + 契约测试（callback schema）PR 必过 |
| 密钥 | 生产禁用仓库默认 JWT/模型 Key；环境变量注入 |
| 权限 | Session/Report 访问继续走 `AiScoreAccessControlService`；无越权读他人卷宗 |
| 隐私 | 导出与常模需脱敏策略评审 |

---

### 4.8 北向成功标准（12 个月，产品是否「跑赢 Agent 心智」）

同时满足视为升级战略成功：

1. **证据点击率**：报告访问中 ≥ **40%** 产生至少一次证据/时间轴交互（说明用户在用卷宗而非只读作文）。  
2. **二次上传率**：完成首次评分的用户 30 天内再次评分 ≥ 基线 **+50%**（相对升级前）。  
3. **教师周活审阅**：试点营教师使用审阅/导出 ≥ 约定频次。  
4. **定性**：可用性访谈中，≥ **70%** 受试在盲测描述中能说出「和 ChatGPT 的差别是能定位到视频/有任务/有对比」中的至少两点。

---

## 5. 里程碑与交付物清单

| 里程碑 | 交付物 |
|--------|--------|
| M0 评审通过 | 本文档评审纪要；权威策略签字；评测集清单 |
| M1 P0 完成 | 证据契约 + 证据优先 UI + 权威字段一致 + 门禁报告 |
| M2 P1 完成 | 对比主路径 + 任务对接 + 复评状态机 + 闭环指标看板 |
| M3 P2 完成 | 共评 + 锁分 + 导出 + 教师验收记录 |
| M4 P3 试点 | 常模/API 设计与小流量 |

---

## 6. 附录

### 6.1 关键代码索引

| 区域 | 路径 |
|------|------|
| 上传与分发 | `backend/.../AiScoreUploadController.java`、`AiScoringPipelineClient.java` |
| Session/回调/报告 | `backend/.../AiScoreController.java`、`AiScoringSessionService.java` |
| 改进 v3 | `backend/.../AiScoreRemediationService.java` |
| 规则引擎（Java） | `backend/.../AiScoreRuleEngine.java` |
| 会话流水线 | `ai-scoring/app/services/session_pipeline_service.py` |
| 核心流水线 | `ai-scoring/app/services/pipeline_service.py` |
| 账本/改进 | `ai-scoring/app/services/scoring/*` |
| 媒体证据 | `ai-scoring/app/services/media_evidence/*` |
| 报告 UI | `frontend/user/src/views/ai-score-report/*` |
| 报告数据 | `frontend/user/src/composables/useAiScoreReport.js` |

### 6.2 术语表

| 术语 | 含义 |
|------|------|
| Score Session | 一次评分会话（卷宗根） |
| Authority | 分数权限：官方 / 诊断 / 待审 |
| Evidence Anchor | 可定位证据单元（时间/文本/帧） |
| Loss Ledger | 结构化失分账本 |
| Remediation Task | 改进任务 |
| Rule Hash | 量表内容指纹，用于绑定与防串味 |

### 6.3 文档维护

- 重大契约变更（callback / v3 schema）必须同步更新本文 §1 与 §4。  
- 每季度回顾北向指标，倒逼 P1/P2 优先级。

---

**文档结束。**
