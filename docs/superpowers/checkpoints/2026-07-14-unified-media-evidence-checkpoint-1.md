# 统一媒体证据流水线—检查点 1 报告

**日期：** 2026-07-14  
**范围：** Python 证据核心、上传视频影子接入  
**结论：** 检查点 1 通过；生产开关继续关闭，不改变现有官方评分和回调契约。

## 1. 已完成

- 建立 `media-evidence-v1` 版本化证据契约与确定性 `snapshotHash`。
- 建立递归评分字段防火墙，禁止媒体证据输出总分、维度分、扣分、预测分和可追回分。
- 建立说话人安全归一化：缺失说话人时保留为未知，不再伪造为 `SPEAKER_0`；重叠和过短音频有独立状态。
- 建立离线 Fun-ASR 供应商边界，包含参数、HTTP/业务状态、任务状态、结果 JSON 和说话人字段解析。
- 建立有界并发证据编排器，保证输出顺序稳定、分支超时可定位且不共享可变对象。
- 建立旧 ASR/语音/视觉/融合结果的白名单适配器；历史 `score` 字段只可转为非计分 `signalValue`。
- 建立影子快照原子替换；序列化失败保留上一个有效快照并清理临时文件。
- 上传视频在评分前增加隔离的影子写入点；失败只记影子告警，不改变正式评分终态。

## 2. 测试证据

### 2.1 新证据层

```text
35 passed in 0.10s
```

覆盖契约、hash、时间范围、说话人归一化、Fun-ASR 边界、有界并发、旧结果适配和原子存储。

### 2.2 影子流水线接入

```text
3 passed in 0.83s
```

覆盖默认关闭、开启后写入、影子失败不影响官方流水线。

### 2.3 原有评分回归

```text
32 passed in 0.91s
```

覆盖 ASR 并发、视觉采样、后端回调、三阶段 LLM、评分完整性门禁、视频 payload 和会话权威回调。

### 2.4 静态契约扫描

`app/services/media_evidence` 中未发现 `overall_score` / `dimension_score` / `deducted_points` / `max_recoverable_points` / `predicted_score` / `audio_score` / `visual_score` 的输出构造。

### 2.5 运行时开关

```text
UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED=False
EVIDENCE_CONTRACT_VERSION=media-evidence-v1
UPLOAD_RECORDED_ASR_MODEL=fun-asr
```

## 3. 变更文件

- `ai-scoring/app/config.py`
- `ai-scoring/app/services/pipeline_service.py`
- `ai-scoring/app/services/media_evidence/__init__.py`
- `ai-scoring/app/services/media_evidence/contracts.py`
- `ai-scoring/app/services/media_evidence/speaker_reconciliation.py`
- `ai-scoring/app/services/media_evidence/dashscope_recorded.py`
- `ai-scoring/app/services/media_evidence/orchestrator.py`
- `ai-scoring/app/services/media_evidence/legacy_adapter.py`
- `ai-scoring/app/services/media_evidence/shadow_store.py`
- `ai-scoring/tests/test_media_evidence_contracts.py`
- `ai-scoring/tests/test_media_evidence_speakers.py`
- `ai-scoring/tests/test_dashscope_recorded_asr.py`
- `ai-scoring/tests/test_media_evidence_orchestrator.py`
- `ai-scoring/tests/test_media_evidence_legacy_adapter.py`
- `ai-scoring/tests/test_evidence_shadow_integration.py`

## 4. 未满足的外部集成门禁

以下项目不属于检查点 1 的完成声明，在对外开启前必须单独验证：

- 尚未使用真实 DashScope 凭证和可访问的私有 OSS 音频执行离线 Fun-ASR 任务。
- 尚未验证真实返回中 `speaker_id` 及整场声音簇一致性。
- 尚未实现临时私有 OSS 传输、最小权限、短效签名和成败均删除。
- 尚未实现在线会议媒体网关、音频块幂等、断线续传和会后终版冻结。
- 尚未进行真实 60 分钟视频的 P50/P95 耗时、峰值内存、临时磁盘和外部限流测试。
- 尚未进入 Java 快照/说话人身份持久化、报告 API 和前端人工修正。

## 5. 回滚与放量

- 当前回滚动作为保持 `UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED=false`。
- 检查点 2/3 未通过前，不得将影子证据包传入官方评分、Java 正式报告或用户页面。
- 因工作区不是 Git 仓库，本报告以精确文件清单、功能开关和测试输出作为本检查点的回滚与审计基线。
