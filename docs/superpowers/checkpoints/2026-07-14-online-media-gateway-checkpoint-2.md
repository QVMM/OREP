# 在线会议统一媒体网关—检查点 2 报告

**日期：** 2026-07-14  
**结论：** 代码与本地耐久性检查通过；双端生产开关保持关闭，真实会议 + DashScope 长连接尚未完成影子放量，因此不进入全量开启。

## 1. 已完成

- 新增 1 秒 PCM 块 v2 协议：sequence、start/end ms、SHA-256、JSON metadata + binary payload。
- 新增单文件追加音频日志与 JSONL 索引，避免数万个小文件。
- ACK 在音频 payload 和索引 `fsync` 后返回；重放不重复写盘。
- 相同 sequence 不同 hash 稳定拒绝，乱序和缺口保留审计。
- WebSocket 断开只标记 `stream_interrupted`，不再把 v2 短断线伪装为 completed。
- 客户端待 ACK 队列为有界 30 秒；超限只降级实时证据，不停止完整 `MediaRecorder` WebM 录制。
- 断线重连根据服务端 `nextSequence` 重放未 ACK 块，已落盘块不重复转发。
- 供应商转发失败时本地音频日志仍保留，ACK 显式返回 `providerStatus=degraded`。
- 会后终版冻结优先离线终版转写，其次才是实时 final sentence；interim 不进终版。
- 缺口导致 `evidence_incomplete`，不伪装证据完整；终版仍通过评分字段防火墙。

## 2. 自动化证据

### Python 回归

```text
69 passed in 0.91s
```

覆盖音频日志、v2 协议、会后冻结、finish 集成、证据契约、说话人安全、回调终态、影子评分流水线和原有 ASR/评分 payload。

### 前端协议

```text
6 passed
```

覆盖 1 秒聚合、ACK、重连重放、有界队列降级、partial flush 和服务端续传点。

### 前端构建

```text
vite build: success, 3711 modules transformed
```

现有大 chunk 警告仍存在，本次没有引入新构建错误。

### 本地 60 分钟网关耐久性模拟

```text
chunks=3600
bytes=115200000
elapsed_seconds=1.202
peak_python_memory_mb=3.74
data_file_mb=109.86
integrity=complete
```

该数据只证明本地日志结构没有把一小时 PCM 整体载入 Python 内存，不代替真实浏览器、网络和 DashScope 长连接压测。

## 3. 开关状态

```text
UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED=False
UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED=False
```

前端 `VITE_UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED` 未配置时亦默认为 false。只有双端同时开启才会请求 `media-evidence-v2`；否则保留旧 raw PCM 路径。

## 4. 未通过的放量门禁

- 真实 Chrome + 一小时 LiveKit 混音 + 断网/重连还未运行。
- 真实 DashScope 长连接在 429、5xx、超时和中途断开下的行为还未影子验证。
- 现有实时 Fun-ASR 不代表会后说话人分离已经生效；最终发言人簇仍需要会后离线 Fun-ASR 真实任务验证。
- 本地录音失败的前端可见报警还未进入本检查点。

## 5. 变更文件

- `ai-scoring/app/config.py`
- `ai-scoring/app/routers/scoring_router.py`
- `ai-scoring/app/services/media_evidence/realtime_gateway.py`
- `ai-scoring/app/services/media_evidence/live_finalizer.py`
- `ai-scoring/app/services/media_evidence/shadow_store.py`
- `ai-scoring/tests/test_realtime_audio_gateway.py`
- `ai-scoring/tests/test_realtime_asr_protocol.py`
- `ai-scoring/tests/test_live_evidence_finalizer.py`
- `ai-scoring/tests/test_live_evidence_finish_integration.py`
- `frontend/user/src/utils/realtimeAudioChunkSender.js`
- `frontend/user/src/utils/realtimeAudioChunkSender.test.js`
- `frontend/user/src/utils/mediaRecorder.js`
