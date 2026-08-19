# 终版说话人分离检查点 4D 报告

**日期：** 2026-07-14  
**结论：** 代码接入与本地自动化门禁通过；生产开关保持关闭，等待私有 OSS 配置和真实一小时素材验收。

## 已完成

- 上传视频与在线会议会后终版都通过 `_run_authoritative_asr` 选择同一套完整录音转写入口。
- 严格模式只上传派生 WAV 到私有临时对象，使用无业务信息的 UUID 对象名和短时签名 URL。
- Fun-ASR 请求开启 `diarization_enabled` 与 `timestamp_alignment_enabled`；无 speaker_id 时明确标记证据不完整，不伪造 `SPEAKER_0`。
- 临时对象在成功、调用失败和调用方异常后都执行有限重试删除；审计只记录对象键哈希。
- 单视频并行执行音频终版分析与视觉分析；双路会议并行执行音频、全景和屏幕三条分支，统一超时 900 秒。
- Python 不再运行第二套发言人 LLM 数值评分，不再生成或回调 `speaker_scores`。
- Java completed 回调接收 `speakerEvidence`，按 `(session_id, raw_speaker_label)` 幂等写入 AUTO 人物映射。
- completed 回调重放不会重复插入，AUTO 结果不会覆盖 CONFIRMED/REJECTED 人工结论。
- 历史 `roadshow_speaker_score.dimensions_json` 仍可审计，但新写入不再保存人物维度分，个人能力画像不再读取它。
- PDF 的旧隐藏人物评分训练页已强制停用。

## 自动化结果

- Python 评分与媒体证据测试：`291 passed`。
- 并发、终版 ASR、人物证据与回调关键组合：全部通过。
- Java 全量：`mvn -q test` 通过。
- 用户端工具测试：`69 passed`。
- 用户端生产构建：通过。
- Python `compileall`：通过。
- 静态扫描：正式流水线无 `speaker_scoring_service`、`result["speaker_scores"]`、旧 `payload["speakers"]` 或 `speakerDimensionScore`。

## 已知基线问题

直接执行 `pytest -q` 会在收集阶段遇到仓库既有的 PPT 测试模块缺失，例如 `app.services.ppt.v5`、`v6`、`qwen_client` 和内嵌 `paper-ppt-agent` 的导入路径。这些用例未进入执行阶段，与本次评分流变更无关；排除这些已失效 PPT 用例后，评分相关 `tests/` 全部通过。

## 生产放量门禁

当前本地只有 DashScope API Key，未配置以下私有 OSS 参数，因此不能声称真实云端链路已跑通：

- `TEMP_AUDIO_OSS_ENDPOINT`
- `TEMP_AUDIO_OSS_BUCKET`
- `TEMP_AUDIO_OSS_ACCESS_KEY_ID`
- `TEMP_AUDIO_OSS_ACCESS_KEY_SECRET`（或临时 STS）

配置完成后按以下顺序放量：

1. 使用测试私有 bucket，确认公共读取关闭、签名 URL TTL 不超过 15 分钟。
2. 用 5～10 分钟多人单轨素材跑上传与在线会议会后两条链路，核对 speaker_id、时间戳和对象删除。
3. 用真实 60 分钟素材各跑 3 次，记录 ASR、视觉、融合、评分、回调分段耗时以及说话人错分/漏分。
4. 确认报告 API、人物人工修正、completed 回调重放均通过后，设置 `FINAL_RECORDED_DIARIZATION_ENABLED=true`。
5. 若云端失败，终版任务必须明确失败并可重试，不得静默退回单人伪标签。

## 评分权威说明

人物分离只产生“谁在什么时间说了什么”的证据。正式分数仍只来自 42 赛道版本化规则与结构化扣分账目；声纹、音频和视频不会建立另一套隐藏分数。
