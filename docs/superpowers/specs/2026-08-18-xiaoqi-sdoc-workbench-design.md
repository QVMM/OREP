# 小启改稿工作台：智能文档

> 日期：2026-08-18  
> 状态：按此实施  
> 前提：`2026-08-18-xiaoqi-script-ppt-agent-design.md` 的补丁闸、确认卡、版本快照全部保留  
> 决策：智能文档是改稿工作台；讲稿 `script.content` 仍是分工真源

---

## 1. 为什么改

只把小启写回讲稿编辑器的 textarea，智能文档就停在「另一套 Office」——协同、分屏、金山式纸张都进不了备赛主路径。客户看到的改稿现场必须是智能文档。

## 2. 角色

| 东西 | 职责 |
|---|---|
| `script.content` 步骤 JSON | 真源：谁讲、哪一页、多久、正文 |
| 智能文档 sdoc | 人写、人协、小启写入的工作台 |
| 讲稿编辑器 | 排练、导出 PDF、改角色/增删步骤 |
| PPT 分屏 | 对照已绑定的 PPT / 启发 Office 演示 |

## 3. 用户看见什么

1. 启发 Office 打开或新建智能文档，它就是默认讲稿，不必先去讲稿编辑器。
2. 文档里自动挂上步骤表——角色 / 页 / 时长锁定，正文可改。顶栏常驻「问小启」。
3. 选中一句，点「问小启」，走已有确认卡。
4. 确认后这一格正文变了，角色没变；文档和讲稿表一致。
5. 可左右分屏对照 PPT。

## 4. 绑定

`script.sdoc_document_id` → `inspire_office_document.id`。

`POST /api/script/{id}/workbench-sdoc`：已绑定且仍可访问则打开；否则新建个人 sdoc，用步骤生成 `scriptSheet`，写回绑定。

`GET /api/script/from-sdoc/{documentId}`：编辑器用来认出这是改稿文档。

## 5. 文档结构

自定义节点：

- `scriptSheet`：整张表，attrs 带 `scriptId`
- `scriptStep`：一行，attrs：`stepId, role, duration, focus, chapterId`；正文是内部 paragraph

小启只改 `scriptStep` 里的正文。角色/页/时长在节点视图里只读。

## 6. 双写

- 确认 `apply_script_patch`：先改 `script`，再改绑定 sdoc 里对应 `scriptStep`。
- 人在文档里改正文并保存：`POST /api/script/{id}/sync-from-sdoc` 只回写 `content`，不改 role/duration/focus。
- 增删步骤、换角色：仍在讲稿编辑器做，再重新打开工作台时按讲稿刷新表（保留已有正文若 stepId 仍在）。

## 7. 不做

- 用自由散文 sdoc 当逐字稿真源
- 小启改任意无关智能文档（本期）
- 废掉讲稿编辑器
- Collabora 里改 PPT

## 8. 验收

打开自己的讲稿 → 在智能文档中改稿 → 看见分工表 → 选中一句问小启 → 确认 → 回文档该格已变、角色未变 → 回讲稿编辑器刷新一致。
