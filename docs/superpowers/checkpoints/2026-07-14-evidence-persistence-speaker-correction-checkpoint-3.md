# 证据持久化与发言人修正—检查点 3 报告

**日期：** 2026-07-14  
**结论：** 本地代码、数据契约、权限接口和前端构建通过；新转写不再伪造发言人或占位证据。本检查点不等于云端说话人分离已生产放量。

## 1. 已完成

- Java completed 回调正式持久化 `asrSegments`，统一转换为毫秒、按时间排序并通过 hash 实现重放幂等。
- 供应商没有 speaker 时保持 `null`，不再伪造 `SPEAKER_0`。
- 删除 Java 占位转写、占位关键帧、虚拟 OCR 和虚拟时间锚点生成代码。
- 新增 `ai_score_speaker_identity`，原始声音簇与显示名称/团队角色分离保存。
- 人工修正保留 raw speaker，记录 `CONFIRMED/USER/revision/updated_by`，且只允许修正当前会话转写真实存在的声音簇。
- 新增受现有 session 访问控制保护的 `PATCH /api/ai-score/sessions/{sessionId}/speakers/{rawSpeaker}`。
- 报告 API 返回用户安全的 `asrSegments` 和 `speakerMappings`，不返回本机路径、segment hash 或内部来源字段。
- 依据页优先使用 Java 真实分段，兼容旧 `asr.segments`；毫秒时间戳显式除以 1000，防止视频跳转 1000 倍偏移。
- 依据页新增发言人修正对话框；一次修正会用 mapping 覆盖全文同一 raw speaker 的显示值。
- 媒体证据契约仍无正式分数字段，本次没有改动 42 个赛道规则、正式总分或扣分引擎。

## 2. 自动化验收证据

### Java

```text
mvn -q test: PASS
```

包括真实转写替换/重放、无 speaker 保留未知、身份 revision、接口权限、报告字段脱敏和旧功能全量回归。

### Python

```text
59 passed in 0.36s
```

覆盖证据契约、说话人安全、离线 Fun-ASR 解析、有界并发编排、旧流适配、实时音频网关、终版冻结和现有 ASR 并发。

### 前端

```text
aiScoreMinutesPresentation: 7 passed
vite build: success, 3711 modules transformed
```

新增契约测试明确断言 `1250 ms -> 1.25 s`，并确认已修正姓名/角色传播到全文。现有大 chunk 警告仍存在，没有新构建错误。

### 静态门禁

```text
media_evidence 内禁用评分字段扫描：0 命中
Java 伪转写/伪帧生成标识扫描：0 命中
```

## 3. 本检查点已通过的 P0

- raw speaker 不被人工修正覆盖。
- 无身份锚点时显示“发言人待确认”，不猜姓名。
- 同一 session completed 回调重放不增加重复转写。
- 转写时间边界使用毫秒，前端播放使用秒。
- 发言人修正接口经过 session 访问控制。
- 报告 API 不暴露内部文件路径和 segment hash。
- 音视频证据仍只提供事实，不产生、修改或承诺分数。

## 4. 仍未通过的生产放量门禁

- 尚未用真实 DashScope 离线 Fun-ASR 对长视频验证 `speaker_id` 返回与全局一致性。
- 本地文件到私有 OSS 临时对象的凭证、地域、删除审计和孤儿清理尚未配置。
- 尚未进行真实 Chrome + 在线会议 + 断网重连 + DashScope 长连接的一小时测试。
- 人工修正界面尚未在已重启的本地 Java/前端服务上完成真实数据点击验收。
- 两个功能开关继续保持默认关闭，不可因本地单测通过就全量开启。

## 5. 下一检查点

检查点 4 是“真实离线 ASR 影子接入与数据安全门禁”：先建立临时对象上传/删除的可审计实现，再用真实长视频影子运行。在这些门禁通过前，不替换当前正式 ASR，不改变用户正式分数。
