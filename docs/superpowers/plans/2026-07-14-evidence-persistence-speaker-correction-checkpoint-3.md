# Java 证据持久化与发言人修正—检查点 3 计划

## 目标

将 Python 回调中的真实 `asrSegments` 正式写入 Java 数据库和报告 API，使依据页不再依赖本地 `result_*.json` 才能显示转写；保留原始声音簇并支持用户修正显示姓名/角色。

## 已发现的现实问题

1. `AiScoreEvidenceBundleService.prepareEvidence()` 在 ASR 尚未执行时写入 3 条“后续 ASR 会替换”的伪转写和 3 张伪关键帧，与“测试数据必须真实”冲突。
2. Python 终版回调已包含 `asrSegments`，但 `AiScoringSessionService.processPipelineCallback()` 只保存整段 transcript，忽略分段、时间和说话人。
3. 报告 API 只返回 transcript 字符串，前端依据页主要靠 Python 旧结果补齐 `asr.segments`。
4. 现有 `roadshow_speaker_score` 是会议+团队的个人诊断表，不能覆盖未绑定团队的上传视频，也不应与证据快照身份混用。

## Task 1：删除伪证据生成

- `prepareEvidence` 只固化真实媒体资产 hash；ASR/关键帧未产生时计数为 0。
- 不再写入 `mock_asr_snapshot`、伪 OCR 文字或 `#frame-1` 虚拟路径。
- 更新 Java 测试，明确断言没有 segment/frame/anchor insert。

## Task 2：真实转写回调持久化

- 新增 `AiScoreTranscriptService`，对 `asrSegments` 做白名单解析、毫秒转换、排序、hash 和幂等替换。
- 保留 `speaker_id/speakerId/speaker`；缺失时存 null，不伪造 `SPEAKER_0`。
- completed 回调重放时先删后插，依赖 session+segmentNo 唯一约束保证幂等。
- 时间无效的分段拒绝整个 completed 回调，不保存一半。

## Task 3：发言人身份与人工修正

- 新增 `ai_score_speaker_identity`：session_id、raw_speaker_label、display_name、role_name、status、source、confidence、revision、updated_by、updated_at。
- raw label 不可修改；只允许修正 display name / role。
- 状态为 `AUTO/CONFIRMED/REJECTED`，人工确认后同版自动任务不得覆盖。
- PATCH API 通过现有 session 访问控制，不信任前端 session/user 字段。

## Task 4：报告 API 与前端

- `AiScoreReportUserResponse` 新增 `asrSegments` 和 `speakerMappings`，均为用户安全字段。
- segment 只返回 id、segmentNo、start/end、text、rawSpeaker、speakerName、roleName、confidence。
- 前端分钟级页优先使用 Java `asrSegments`，兼容旧 `asr.segments`。
- 支持 `startMs/endMs/rawSpeakerId/displaySpeaker`，避免把毫秒当秒导致跳转错位。
- 发言人修正使用小型对话框；不新增虚构的“声纹认证”能力。

## Task 5：回归与门禁

```bash
cd backend
mvn -q -Dtest=AiScoreEvidenceBundleServiceTest,AiScoreTranscriptServiceTest,AiScoringSessionReportDetailTest test

cd ../frontend/user
node --test src/utils/aiScoreMinutesPresentation.test.js
npm run build
```

P0 断言：

- Java 不再生成伪转写/伪帧。
- 回调重放不增加重复分段。
- 缺失 speaker 保持未知。
- 人工修正不覆盖 raw speaker label。
- 前端毫秒/秒转换正确，视频跳转无 1000 倍偏移。
- 报告 JSON 不暴露媒体本机路径、内部 hash 或评分规则。
