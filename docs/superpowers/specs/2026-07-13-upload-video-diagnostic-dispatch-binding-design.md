# 上传视频评分诊断绑定派发设计

## 问题

用户已在前端选择赛道，Java 也已为评分会话解析出赛道、规则版本和规则 Hash，但 Java 调用 Python `/api/ai/score-session` 时只发送 `trackName`。Python 因 `publishOfficialScore` 默认为 `true` 而按正式发布门禁校验，最终返回 `track_confirmation_required`。

Java 将这个业务拒绝统一包装为“本地 ai-scoring 服务未连接 / 任务派发失败”，导致前端误判为连接故障。

## 当前阶段决策

当用户已选择赛道，但系统尚无赛事与组别绑定条件时：

- 允许启动完整 AI 评分流水线。
- 必须使用 `diagnostic_override`。
- 必须使用 `publishOfficialScore=false`。
- 结果只能标记为诊断分，不得冒充已完成赛事/组别绑定的正式分。

## Java 内部派发契约

Java 必须使用会话中已解析的数据，而不是继续使用前端原始表单值。内部请求增加：

```json
{
  "trackId": "track-it",
  "trackName": "新一代信息技术赛道",
  "competitionBinding": {
    "trackId": "track-it",
    "trackName": "新一代信息技术赛道",
    "ruleVersion": "v1.2",
    "ruleHash": "<internal-rule-hash>",
    "selectionSource": "diagnostic_override"
  },
  "publishOfficialScore": false
}
```

`ruleHash`、内部版本和规则路径仍通过 `@JsonIgnore` 或内部 DTO 隔离，不返回用户前端。

## 错误分类

- HTTP 连接异常、超时、5xx：“AI 服务连接失败”。
- `track_confirmation_required`：“评分绑定信息不完整”。
- 其他 `accepted=false`：“AI 任务未启动”，并保留服务端理由。

## 验收

1. Java 客户端测试验证内部 JSON 包含完整诊断绑定且 `publishOfficialScore=false`。
2. 上传控制器必须使用会话已解析的赛道和规则数据。
3. `track_confirmation_required` 不再显示为本地服务断开。
4. Python 路由接受 Java 新请求并创建后台任务。
5. 会话 25 使用已上传视频重新派发，不再返回 `track_confirmation_required`。
