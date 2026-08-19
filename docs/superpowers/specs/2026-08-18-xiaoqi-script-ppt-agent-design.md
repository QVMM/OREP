# 小启备赛改稿方案（完整规格）

> 日期：2026-08-18  
> 状态：按此实施  
> 文档性质：产品 + 工程规格，有头有尾  
> 配套计划：`docs/superpowers/plans/2026-08-18-xiaoqi-script-ppt-agent.md`  
> 范围：学生端小启对话 + 讲稿编辑器 + PPT 工作台  
> 非目标：Collabora 里让 AI 改 PPT、无边界通用 Agent、覆盖原稿、问候就读工作台、另做金山智能表格产品

---

## 0. 从哪里来

备赛真实路径是：

**模拟 / 评分 → 对照任务书改逐字稿 → 再决定 PPT 哪几页跟着改 → 队员按角色排练。**

客户反馈不是「小启再说得更多」，而是：

1. 听懂「按最新评分，结合讲稿和 PPT 优化」。
2. 对着**这一次评分、这一份任务书、这一份讲稿、这一份 PPT**做事，不能东拉西扯。
3. 改逐字稿时**分工不丢**：谁讲、哪一页、多久，改完还在表里。
4. 支持选中一句局部改，先给原因和差异，确认再写入。
5. 讲稿改完再问要不要动对应 PPT 页。
6. 用起来要快、要清楚、要敢点确认——客户能给好评。

今天的缺口（现状，不是愿景）：

| 现状 | 问题 |
|---|---|
| 讲稿真源已是 `script.content` 章节/步骤 JSON | 小启 `/改稿` 只吐散文，**不写回步骤** |
| 小启已有 L2 确认卡 `ai_assistant_action_proposal` | 只支持协同/任务/学习，**没有讲稿补丁类型** |
| 讲稿编辑器是步骤卡片 + textarea | 选中一句**不能**带上下文去问小启 |
| PPT 工作台已有按页 SVG + `/api/ppt/refine?target_pages` | 小启不会把它当成「只改已改讲稿对应页」 |
| 会话有 `context_json` | 创建会话时**不写入**讲稿/评分钉，问候仍可能空转 |
| 平台没有金山智能表格 | 用户要的「表格感」应落在讲稿步骤视图，不另开产品 |

本方案把这条路径做成可演示、可确认、可回滚的产品能力。实施按配套计划逐步打勾。

---

## 1. 到哪里去（结论）

小启是**导演**，不是第二套 Office。

| 资产 | 真源 | 小启怎么动 | 人怎么动 |
|---|---|---|---|
| 逐字稿 | 讲稿编辑器 `script` 表（章节/步骤 JSON） | 只改步骤的 `content` / `notes` / `transition` | 在讲稿编辑器里看表、对词、排练 |
| 分工 | 步骤上的 `role` + `roles` 列表 | **默认锁死，禁止改** | 只有用户明说换人时才提案改角色（本期不做） |
| PPT | PPT 工作台 `ppt_job` + 按页 SVG/备注 | 只动讲稿改过的页：改字或 refine 单页 | 启发 Office / 导出 PPTX 做最终版式 |
| 评分 | 平台评分报告，一次运行一个 ID | 只读，禁止推断扣分 | 报告页核对 |
| 任务书 | 资源中心文件或训练任务 | 只读，用来对齐评分项 | 原文不动 |

**不采用：** 把逐字稿做成自由 Word / 智能文档当主存储。散文一改，队员就不知道自己讲哪段。

**不采用：** 用启发 Office 的 Collabora 让 AI 改 PPT。Collabora 适合人拖排版，没有「改第 9 页第二条」的稳定 API。AI 走 PPT 工作台已有的按页保存和 `target_pages` refine。

**智能表格：** 平台还没有金山智能表格。本方案把讲稿步骤做成**表格视图**（一行一步：角色、页、时长、正文），满足「格式规范、分工明确」，不另开产品线。

---

## 2. 用户能感知的三条路径

### 2.1 局部改（P0，必须能演示）

人在讲稿某一步的正文里选中一句，点「问小启」，或在小启里说「这一段不连贯」。

小启必须带着：选中文本、该步骤全文、前后各一步摘要、角色、对应页（`focus`）、讲稿 ID、当前 `contentVersion`。

产出一张卡：

- 原文 / 建议稿（只动 `content`，角色列原样）
- 原因（能指到评分条目或上下文逻辑，禁止空话「更生动」）
- 按钮：确认写入 / 不要

确认后写入**该步骤**，讲稿 `contentVersion + 1`，`script_revision` 留补丁前快照。再问一句：「对应 PPT 页要不要跟着改？」默认不自动改 PPT。

### 2.2 整份对照（P1）

「按最新评分结合讲稿和 PPT 优化。」

小启先钉死四样并说出来。然后只出**诊断清单**（几步、几页、分工不动），再出讲稿改稿列表，逐条确认。全部讲稿确认后，再出 PPT 跟随清单。

来源必须带评分条目 ID。禁止推断扣分。

### 2.3 PPT 跟随（P2）

只对讲稿已确认改过的 `focus` 页：改该页可见文字，或「重生成这一页」。禁止一次重做整份 PPT。版式/UI 不在对话里做细调。

---

## 3. 意图与会话钉

先只认三类，其它当普通问答：

| 意图 | 触发 | 行为 |
|---|---|---|
| `script_local_edit` | 选区、「问小启」，或「这段/这句」+ 不满意 | 只提案改当前步骤 |
| `script_score_revise` | 「按评分改讲稿/优化」 | 钉评分+讲稿，出多步清单 |
| `ppt_follow_script` | 「PPT 也改一下」、或讲稿确认后的追问 | 只动已改步骤对应页 |

问候、闲聊、无关问题：**不准**读工作台、缺交、全队材料。

会话钉住（写入 `ai_assistant_session.context_json`，换一句还在）：

```json
{
  "type": "script_step",
  "intent": "script_local_edit",
  "scriptId": 12,
  "scriptTitle": "智慧农业路演",
  "contentVersion": 7,
  "pptJobId": "job_xxx",
  "scoreReportId": null,
  "taskBookRef": null,
  "stepId": "s1",
  "role": "主讲人A",
  "focus": "封面（P01）",
  "duration": 0.5,
  "selection": "各位评委好",
  "stepContent": "各位评委好，今天我们汇报……",
  "prevStep": { "id": null, "role": "", "content": "" },
  "nextStep": { "id": "s2", "role": "角色B", "content": "这是架构" }
}
```

个人偏好小抄继续独立，不和团队事实混用。

---

## 4. 讲稿数据与写回规则

现有 `script.content` 为章节数组，每步至少：

`id, role, duration, focus, content, notes, transition`

小启补丁：

```json
{
  "scriptId": 12,
  "expectedVersion": 7,
  "patches": [
    {
      "stepId": "abc",
      "field": "content",
      "before": "各位评委好，今天我们汇报……",
      "after": "各位评委老师好，我们汇报智慧农业项目……",
      "reason": "开场没报项目名，评委对不上号"
    }
  ]
}
```

硬规则：

1. 只允许改 `content` / `notes` / `transition`。`role`、`duration`、`focus`、步骤顺序、增删步骤，默认拒绝。
2. `before` 必须与库里**该字段当前全文**一致（不是只比选中句），否则 409，提示刷新后再确认。
3. `expectedVersion` 必须等于当前 `contentVersion`。
4. 默认写回同一条 `script` 记录并升版本，**不覆盖无版本历史**——每次确认在 `script_revision` 留一份补丁前快照（JSON）。
5. 确认走现有 `ai_assistant_action_proposal`，新类型 `apply_script_patch`。不确认不落盘。
6. 选中句改写时：`before` = 步骤当前全文，`after` = 把选中句替换后的全文。补丁永远按整格写，避免半句对不上。

`script_revision`：

| 列 | 含义 |
|---|---|
| `script_id` | 讲稿 |
| `content_version` | 快照时的版本（补丁前） |
| `content` / `roles` | 补丁前 JSON |
| `source` | `apply_script_patch` 等 |
| `created_by` | 确认人 |

---

## 5. 端到端时序（P0）

```
讲稿编辑器                 小启工作台              Java /api/assistant          ScriptService
    | 选中一句，点「问小启」      |                         |                          |
    |-- sessionStorage 上下文 -->|                         |                          |
    | 跳转 /assistant?from=script |                         |                          |
    |                        建会话+写入 context_json      |                          |
    |                        自动发改写请求 --------------->| 现有 stream              |
    |                        模型回建议稿+原因              |                          |
    |                        JWT propose 补丁卡 ---------->| action_proposal          |
    |                        展示 原文/建议/原因/确认        |                          |
    |                        点确认 ---------------------->| apply_script_patch       |
    |                                                    |-- 鉴权/版本/快照/Applier ->|
    |                                                    |<-- 新 version -------------|
    | 回讲稿刷新，该步变了、角色没变                           |                          |
    |                        追问：对应页要不要改 PPT？       |  （P2 才真改页）            |
```

P0 不改 Python 编排也能演示：工作台在模型返回后，用 JWT `POST /api/assistant/script-patch/propose` 组提案。以后 AI 服务若能直接发 `action_proposal`，走同一张卡。

---

## 6. API

### 6.1 内部（已有）

`POST /api/assistant/internal/actions/propose`  
internal token。本期把 `apply_script_patch` 加入 ALLOWED，AI 服务以后可直接提案。

### 6.2 用户 JWT（本期新增）

`POST /api/assistant/script-patch/propose`

```json
{
  "sessionId": 1,
  "title": "改写开场第一句",
  "summary": "开场补上项目名，角色不变",
  "args": {
    "scriptId": 12,
    "expectedVersion": 7,
    "patches": [{ "stepId": "s1", "field": "content", "before": "…", "after": "…", "reason": "…" }]
  }
}
```

只允许 `actionType=apply_script_patch`。校验讲稿归属后再入库。返回与现有提案卡相同结构。

确认 / 拒绝继续用：

- `POST /api/assistant/actions/{id}/confirm`
- `POST /api/assistant/actions/{id}/reject`

### 6.3 写回（Service，不单独给前端裸 PATCH）

`ScriptService.applyPatches(scriptId, userId, expectedVersion, patches)`

- 无权：404「讲稿不存在或无权访问」
- 版本不符或 `before` 过期：409
- 非法字段：400
- 成功：更新 `script.content`，`contentVersion+1`，插入 `script_revision`

---

## 7. 对话界面（好评标准）

一次复杂任务只许五段，且要短：

1. **钉住了什么**（讲稿名、步骤角色、对应页）
2. **打算做什么**（只改这一格正文）
3. **进行到哪**（生成建议 / 待确认）
4. **结果卡**（原文 / 建议 / 原因 / 确认）
5. **回执**（改了哪个 stepId、新版本号；PPT 默认不动）

禁止：把整份评分贴进聊天、展示 Thought、一次吐出整份新讲稿当正文。

选区入口在讲稿编辑器步骤正文：浮层「问小启」。打开小启并带上 `context.type = script_step`。

确认卡对 `apply_script_patch` 必须画出 before/after，不能只显示一句 summary。

---

## 8. PPT 怎么改才有效果（P2）

| 手段 | 何时 | 效果 |
|---|---|---|
| 改页上文字 / speaker notes | 讲稿改的是说法，页结构还对 | 快，用户对得上 |
| `POST /api/ppt/refine` + `target_pages` | 字太多、层次不清、要重排该页 | 该页视觉更新 |
| 整份重生成 | 用户明确说重做 | 例外 |
| 启发 Office Collabora | 人决赛前微调版式 | AI 不进 iframe 改 |

小启出 PPT 提案时必须带页码、改前要点、改后要点、原因、手段（改字 / 重生成该页）。确认后调 PPT 工作台 API，不调 Collabora。

`focus` → 页码：解析 `封面（P01）` / `P9` / `第9页`；解不出就问用户，不许猜。

---

## 9. 权限、错误、回滚

- 只能改当前用户 `createdBy` 的讲稿。本期不放宽团队共享。
- 评分、任务书只读当前团队。
- 删除、覆盖、改角色、改顺序本期不做提案。
- 所有确认写入记 `ai_assistant_action_proposal` + `script_revision`。
- 409：提示「讲稿已更新，请刷新后再确认」，卡作废。
- 回滚：用 `script_revision` 最近一条覆盖回去（P0 可先库内可查，界面回滚按钮可放 P1）。
- 提案 30 分钟过期，沿用现有 TTL。

---

## 10. 分期与验收

### P0 局部改稿（本期先做完）

- 讲稿选中 → 小启出一处差异和原因 → 确认写入该步骤。
- 角色列不变。刷新讲稿还在。
- 不点确认，库里一步都不变。
- 问候不读业务数据（改稿会话只带钉住的讲稿上下文）。

### P1 评分对照讲稿

- 钉住一份评分 + 一份讲稿。
- 多步清单，逐条确认。
- 来源必须带评分条目 ID。

### P2 PPT 跟随

- 已确认讲稿步骤 → 对应页改字或 refine。
- 对话里可继续说「第 9 页字太多」只动该页。

### P3 表格视图

- 讲稿编辑器增加一行一步的表格视图（角色、页、时长、正文）。
- 与卡片视图共用同一份 steps。
- 不另做金山智能表格产品。

---

## 11. 明确不做

- 用 Collabora 当 AI 改 PPT 的引擎。
- 用智能文档 / Word 当逐字稿真源。
- 一次生成全新讲稿 + 全新 PPT。
- 无确认覆盖原稿。
- 学校级 Agent 治理、定时巡检、OCR 全量佐证图谱。

---

## 12. 成功标准（客户好评）

1. 改完打开讲稿，角色和页码还在，队员知道自己讲哪段。
2. 局部改从选中到看到建议小于 8 秒（模型超时另说，界面不得假死）。
3. 不点确认，库里一步都不变。
4. 原因能指到评分或上下文，不能只有「更通顺」。
5. PPT 不会在用户没点的情况下整份重做。

---

## 13. 风险与对策

| 风险 | 对策 |
|---|---|
| 模型吐整份新稿 | 卡片只接受单步 `after`；Applier 拒绝结构变更 |
| 自动保存与确认抢版本 | 问小启前先 flush 保存；`expectedVersion` + `before` 双闸 |
| AI 服务暂时发不出提案事件 | P0 用 JWT propose，同一张确认卡 |
| 选区是半句、before 对不上 | 补丁永远写整格；选区只用于提示模型 |
| 用户以为点了小启就改完了 | 卡上写清「确认后才会写入讲稿」 |

---

## 14. 收尾

P0 做完的标志：队员能在自己的讲稿里选一句，让小启给出可确认的差异，点确认后这一格变了、角色没变、版本可查。

P1–P3 在此真源和确认闸上长，不再另起一套改稿产品。
