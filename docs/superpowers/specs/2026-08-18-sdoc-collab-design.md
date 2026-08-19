# 智能文档多人协同设计

> 日期：2026-08-18  
> 状态：按此实现，分两期。P6-A 在场与按人着色；P6-B 才是可同时打字的 CRDT。  
> 原则：先让人看见彼此，再让字合在一起。保护区内容不得经协同通道泄漏。

---

## 1. 为什么适合做在 sdoc，而不是 Collabora

| | Word/Excel（Collabora） | 智能文档（TipTap） |
|---|---|---|
| 编辑器 | iframe，协同是 Collabora 的 | 我们自己的 JSON + 块 |
| 头像 | 已有 WOPI `UserExtraInfo.avatar` | 复用同一套 `/api/wopi/avatars/{id}` |
| 自定义块 | 做不到按块着色 | 段落/标题可带 `authorId` |
| 保护区 | 无 | 学生不可见教师段，协同必须尊重 |

现有 `POST /documents/{id}/presence` **不是**协同。它只把心跳写进 `student_learning_session`，给教师看学习时长。房间里有谁、光标在哪，它都不知道。

当前保存是整份 JSON + `updatedAt` 乐观锁。两人同时打字会 409 或后写覆盖。所以「看见彼此」和「字合在一起」必须拆开做。

---

## 2. 用户要看到的

1. 顶栏头像堆：谁在这篇文档里，名字、角色、自己的颜色。
2. 点头像：滚到对方正在写的位置；悬停看到「正在编辑：……」。
3. 正文里对方的光标/选区，带名字条。
4. 按钮「按人物着色」：每个人的块用自己的色条+浅底，一眼看出谁写的。

不在本期：评论、跟写建议、第二个聊天窗、小启。

---

## 3. 两期

### P6-A  在场 + 着色（本期）

- STOMP 房间 `/topic/sdoc/{id}/presence`，心跳上报光标和块摘要。
- 顶栏头像、远程光标、跳转。
- 块上记 `authorId`（谁最后改了这段）。开关打开后按人着色。
- 保存仍是现在的 PUT。两人同时改同一段仍可能冲突，界面会提示。

### P6-B  同时编辑（下一期，单独开）

- Yjs（`Y.XmlFragment` + TipTap Collaboration）走同一条 STOMP，更新落 `inspire_smart_doc.yjs_update`。
- `content_json` 仍作导出/版本快照。
- 保护区：学生房间只订阅公开片段；教师段不进学生的 Y.Doc。
- 不做 Hocuspocus 云、不加第二个 Node 进程。

P6-B 不和 A 抢。A 的头像颜色、`authorId`、房间协议，B 继续用。

---

## 4. 房间协议

每个打开编辑器的标签页一个 `sessionId`。

心跳（约 2s，选区变化立即发一次，节流 200ms）：

```json
{
  "sessionId": "…",
  "from": 12,
  "to": 40,
  "preview": "拉萨解放大路…",
  "inProtect": false,
  "editing": true
}
```

服务端补：`userId, name, role, color, avatar`，广播整屋 `peers[]`。

`inProtect=true` 时 `preview` 固定为「仅教师可见」，避免答案从协同通道漏出。

超过 12s 无心跳视为离开。关页 `leave`。

颜色：`userId` 稳定哈希到 8 色，和 Collabora 一样一人一色，刷新不变。

头像：`/api/wopi/avatars/{userId}`。

---

## 5. 按人着色

- 写入时给当前段落/标题/高亮块打上 `authorId`。
- 开关打开：`data-author` → 左侧色条 + 浅底。
- 未标作者的旧段落保持白底。
- 导出 PDF/Word 不带色块，那是编辑态。

---

## 6. 权限

- 进房、订阅前走现有 `requireAccessible`。
- 学生端保护区正文仍走 `SmartDocProtect.redact`。
- 学习时长心跳保留，和协同房间分开。

---

## 7. 非目标

- 不用整份 JSON 轮询冒充协同。
- 不在编辑器里再做一套 IM。
- 不把教师保护区预览发给学生。
- 不在 A 期引入 Yjs（避免 Vite 502 和保护区泄漏）。
