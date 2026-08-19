# 在线会议统一媒体网关—检查点 2 实施计划

**目标：** 在不打断现有 `MediaRecorder` 完整录制和正式评分的前提下，为在线路演增加可幂等、可重连、可冻结的音频证据通道。

**实际入口：**

- 浏览器：`frontend/user/src/utils/mediaRecorder.js`
- Python WebSocket：`ai-scoring/app/routers/scoring_router.py` 的 `/api/ai/asr/stream/{session_id}`
- 完整录制：浏览器 `MediaRecorder.start(1000)` 和会后 `/api/ai/upload-audio`
- 实时转写：DashScope `fun-asr-realtime-2026-02-28`

**核心边界：** 新网关只产生音频块审计、实时转写和临时证据，不输出正式分数、扣分或可追回分。

## 放量策略

1. `UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED=false` 为服务端默认值。
2. `VITE_UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED=false` 为前端默认值。
3. 两端同时开启才使用 v2 幂等协议；任意一端关闭时保留旧的原始 PCM 转发。
4. 新网关故障不能调用 `MediaRecorder.stop()`，不能清空完整录制 `chunks`。
5. 证据终版冻结只在明确 `stop/finish` 后发生；WebSocket 短断开不等于会议结束。

## Task 1：本地音频块日志与幂等状态机

**文件：**

- 新建 `ai-scoring/app/services/media_evidence/realtime_gateway.py`
- 新建 `ai-scoring/tests/test_realtime_audio_gateway.py`

**先写失败测试：**

- 连续 sequence 写入后返回 `accepted` 和下一个期望序号。
- 相同 sequence + 相同 hash 返回 `duplicate`，不重复写盘。
- 相同 sequence + 不同 hash 抛出 `SEQUENCE_HASH_CONFLICT`。
- 乱序块允许落盘但显式记录 gap，终版不得伪装完整。
- 声明 hash 与实际 payload 不同时拒绝。
- 时间范围无效、空块、超大块均拒绝。
- 重启日志对象后可从索引恢复去重状态。
- `finalize()` 幂等，保留覆盖率、缺口、字节数和数据 hash。

**实现约束：**

- 音频 payload 写入单个追加日志，避免一小时产生数万个小文件。
- 索引使用 JSONL，每项保存 sequence、时间、offset、length 和 SHA-256。
- 使用每会话锁防止旧连接和新连接并发追加。
- 终版摘要先写临时文件，`fsync` 后 `os.replace`。

**验证命令：**

```bash
cd ai-scoring
.venv/bin/python -m pytest -q tests/test_realtime_audio_gateway.py
```

## Task 2：WebSocket v2 兼容层

**文件：**

- 修改 `ai-scoring/app/config.py`
- 修改 `ai-scoring/app/routers/scoring_router.py`
- 新建 `ai-scoring/tests/test_realtime_asr_protocol.py`

**v2 消息序列：**

1. 客户端发送 `hello`，含 `protocol=media-evidence-v2`、采样率、声道和重连起点。
2. 服务端返回 `ready`，含 `nextSequence`。
3. 客户端先发 `audio_chunk` JSON 元数据，再发对应 binary payload；WebSocket 有序传输保证二者配对。
4. 服务端落盘后才返回 `ack`，含 sequence、hash、状态和 `nextSequence`。
5. `stop` 显式终结日志并停止供应商连接；网络 disconnect 只关闭当前供应商连接，不 finalize。

**P0 测试：**

- 开关关闭时旧 raw PCM 流不变。
- 开关开启但没有 `hello` 时拒绝 v2，不猜测消息。
- metadata 后未收到 binary、重复 metadata、binary 无 metadata 均有稳定错误码。
- 已落盘的块才转发 DashScope；DashScope 失败不删除本地日志。
- disconnect 后会话保持 `stream_interrupted`，不改为 `completed`。

## Task 3：前端块发送器、有界缓冲与重连

**文件：**

- 新建 `frontend/user/src/utils/realtimeAudioChunkSender.js`
- 新建 `frontend/user/src/utils/realtimeAudioChunkSender.test.js`
- 修改 `frontend/user/src/utils/mediaRecorder.js`

**行为：**

- 1 秒 PCM 聚合后编号，避免 85 毫秒级小块造成日志和 ACK 风暴。
- 待确认队列默认上限 30 秒；超过时实时证据通道标记降级，但完整 `MediaRecorder` 继续。
- 有限指数退避重连，每次重连后根据服务端 `nextSequence` 重放未 ACK 块。
- 重复 ACK 幂等；未知 ACK 不删除其他块。
- `stop()` 先尝试排空队列，超时则带缺口停止，不阻塞视频上传。

**测试命令：**

```bash
cd frontend/user
node --test src/utils/realtimeAudioChunkSender.test.js
```

## Task 4：会后终版证据冻结

**文件：**

- 新建 `ai-scoring/app/services/media_evidence/live_finalizer.py`
- 新建 `ai-scoring/tests/test_live_evidence_finalizer.py`
- 修改 `ai-scoring/app/routers/scoring_router.py`

**规则：**

- 实时转写是 `PROVISIONAL`；会后按时间排序、去重和质量门禁后才生成 `FINAL` 证据包。
- 断线导致存在 sequence gap 时，若完整上传音频可用，会后离线识别作为终版来源；不可用时标记 `evidence_incomplete`。
- 合并优先级：会后离线终版 > 实时 final sentence > interim sentence。
- 人工修正不原地改写快照，而是产生新版本和新 hash。
- 冻结调用幂等，相同输入多次得到同一 hash。

## Task 5：检查点 2 失败注入与回归

### Python

```bash
cd ai-scoring
.venv/bin/python -m pytest -q \
  tests/test_realtime_audio_gateway.py \
  tests/test_realtime_asr_protocol.py \
  tests/test_live_evidence_finalizer.py \
  tests/test_media_evidence_contracts.py \
  tests/test_media_evidence_speakers.py \
  tests/test_session_authoritative_callback.py
```

### 前端

```bash
cd frontend/user
node --test src/utils/realtimeAudioChunkSender.test.js
npm run build
```

### 失败注入

- 在 sequence 100 后断开，重连后从服务端返回的 `nextSequence` 继续。
- 重放 sequence 95–100，日志不增长。
- 修改 sequence 98 的 payload，稳定返回 `SEQUENCE_HASH_CONFLICT`。
- 关闭 DashScope 连接，本地日志和完整视频录制持续。
- 在网关延迟 10 秒时，浏览器录制不停止，缓冲超限只降级实时证据。
- 重复发送 `stop`，不重复 finalize 和计费。

## 检查点 2 通过条件

- 新旧协议测试均通过，两个生产开关仍为 false。
- 实时通道任意故障不会终止完整录制。
- 重连、重放、乱序、冲突、重复 stop 均有自动化测试。
- 证据包仍通过评分字段防火墙。
- 真实 60 分钟会议的网关 CPU、内存、日志大小和 ACK 数量已记录；未完成真实性能记录时不得全量开启。
