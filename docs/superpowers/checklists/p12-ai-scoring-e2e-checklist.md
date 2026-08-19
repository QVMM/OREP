# P12 AI评分上线前手工验收清单

## 环境

- 日期：
- 验收人：
- 前端地址：
- 后端地址：
- 测试账号 A：
- 测试账号 B：
- 测试项目/团队/赛道：

## 会议评分链路

- [ ] 进入会议室页面，绑定项目、团队、赛道。
- [ ] 点击 AI评分，开始弹窗不出现评分规则版本、规则 hash、prompt、权重。
- [ ] 评分中再次点击 AI评分，出现运行中弹窗，包含查看进度、结束并生成已有证据报告、终止当前评分、重新开始评分、取消。
- [ ] 结束会议后可进入 `/ai-score/report/:sessionId`。
- [ ] 报告页显示评分一致性编号。
- [ ] 报告页显示为什么不是 100、观察点评分、当前扣分项、上轮问题复核、证据锚点。

## 上传视频链路

- [ ] 进入 `/ai-score-upload`。
- [ ] 页面不出现评分规则版本选择。
- [ ] 上传合法视频后创建 session。
- [ ] 无 `meetingId` 仍能进入 `/ai-score/report/:sessionId`。
- [ ] 上传失败时显示明确错误，session 状态为 failed 或可解释失败。

## 多轮复评

- [ ] 第一轮扣分项出现在连续评分记忆。
- [ ] 第二轮修复项只追回对应扣分，不直接冲到 100。
- [ ] 第二轮新增扣分项单独展示。
- [ ] 本轮上限说明能解释"为什么不是 100"。

## 评审团复核

- [ ] 生成 AI评审团复核后，报告页显示"只做复核，不修改基础分"。
- [ ] 评审团意见包含质疑点、表达风险、训练建议、共识问题。
- [ ] 评审团生成失败不影响基础评分报告。
- [ ] 评审团均分或参考分不覆盖基础 `overallScore`。

## 黑盒与权限

- [ ] Chrome Network 搜索 `rubric_hash` 无结果。
- [ ] Chrome Network 搜索 `rubric_path` 无结果。
- [ ] Chrome Network 搜索 `internal_version` 无结果。
- [ ] Chrome Network 搜索 `prompt` 无内部字段结果。
- [ ] Chrome Network 搜索 `weight` 无内部字段结果。
- [ ] A 团队用户不能访问 B 团队 `/api/ai-score/sessions/{sessionId}/status`。
- [ ] A 团队用户不能访问 B 团队 `/api/ai-score/reports/by-session/{sessionId}`。
- [ ] A 团队用户不能访问 B 团队 `/api/ai-score/sessions/{sessionId}/jury/result`。

## 结论

- [ ] 通过，可以进入下一阶段。
- [ ] 不通过，阻断原因：
