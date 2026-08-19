# 小启讲稿/PPT 改稿 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 小启能对讲稿步骤做「选中 → 建议+原因 → 确认写入」，不丢角色分工；随后接评分对照和 PPT 按页跟随。

**Architecture:** 讲稿 `script.content` 是真源。纯函数 `ScriptPatchApplier` 只改 `content|notes|transition`。确认走现有 `ai_assistant_action_proposal`，新类型 `apply_script_patch`。讲稿编辑器选区带 `context.type=script_step` 进小启。P0 用 JWT `POST /api/assistant/script-patch/propose` 组卡，不依赖 Python 先改编排。PPT 跟随走现有 refine/按页保存，不进 Collabora。

**Tech Stack:** Spring Boot + 现有 `/api/script` + `/api/assistant`；Vue 3 讲稿编辑器与 AssistantWorkspace；JUnit / node:test。

**规格：** `docs/superpowers/specs/2026-08-18-xiaoqi-script-ppt-agent-design.md`

---

## 文件地图

| 路径 | 职责 |
|---|---|
| `backend/.../service/ScriptPatchApplier.java` | 纯函数：应用补丁、锁角色 |
| `backend/.../service/ScriptService.java` | `applyPatches` + 升版本 |
| `backend/.../service/ScriptRevisionService.java` | 确认前快照 |
| `backend/.../service/assistant/AssistantActionService.java` | `apply_script_patch` |
| `backend/.../controller/assistant/AssistantController.java` | JWT propose |
| `backend/src/main/resources/db/migration/V121__script_revision.sql` | 补丁前 JSON |
| `frontend/user/src/views/ScriptEditor.vue` | 选区「问小启」 |
| `frontend/user/src/views/assistant/AssistantWorkspace.vue` | 展示讲稿补丁卡、消费入口上下文 |
| `frontend/user/src/services/assistantClient.js` | `proposeScriptPatch` |
| `frontend/user/src/modules/assistant-core/*` | `script_step` 上下文 / 卡片展示 |
| `frontend/user/tests/script-patch.test.mjs` | 补丁契约（与 Java 规则对齐） |
| `backend/src/test/java/.../ScriptPatchApplierTest.java` | 单元测试 |
| `backend/src/test/java/.../ScriptServiceApplyPatchesTest.java` | 升版本 / 409 |

---

## 阶段

| 阶段 | 目标 | 可演示 |
|---|---|---|
| **P0** | 局部改稿确认写回 | 选中一句 → 确认 → 该步骤变了、角色没变 |
| **P1** | 评分对照多步清单 | 「按评分改讲稿」出列表，逐条确认 |
| **P2** | PPT 跟随已改页 | 确认后问是否改对应页，refine/改字 |
| **P3** | 讲稿表格视图 | 一行一步，看起来像智能表格 |

---

### Task 1: 补丁纯函数与测试

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/ScriptPatchApplier.java`
- Create: `backend/src/test/java/com/orep/backend/service/ScriptPatchApplierTest.java`
- Create: `frontend/user/tests/script-patch.test.mjs`

- [x] **Step 1: 写 Java 失败测试**（先写测试再实现）
- [x] **Step 2: 实现 `ScriptPatchApplier`：只改 content/notes/transition，before 不一致抛错，role 出现在补丁里拒绝**
- [x] **Step 3: 跑通 `ScriptPatchApplierTest`**
- [x] **Step 4: 同步一份 node 契约测试，规则与 Java 一致**
- [x] **Step 5: 本任务完成后在本文件勾选**

**验证：**
```
cd backend && mvn -q -Dtest=ScriptPatchApplierTest test
cd frontend/user && node --test tests/script-patch.test.mjs
```

---

### Task 2: ScriptService.applyPatches + 版本快照表

**Files:**
- Modify: `ScriptService.java`（构造注入 + `applyPatches`）
- Create: `ScriptRevisionService.java`
- Create: `V121__script_revision.sql`
- Create: `ScriptServiceApplyPatchesTest.java`

- [x] **Step 1: Flyway 建 `script_revision`**
- [x] **Step 2: `ScriptRevisionService.snapshot` 写入补丁前 JSON**
- [x] **Step 3: `applyPatches(scriptId, userId, expectedVersion, patches)` 鉴权、版本闸、快照、Applier、updateById**
- [x] **Step 4: 版本冲突 / 无权 / before 过期分别 409/404/409**
- [x] **Step 5: 单测覆盖升版本与 409**
- [x] **Step 6: 勾选本任务**

**验证：**
```
cd backend && mvn -q -Dtest=ScriptPatchApplierTest,ScriptServiceApplyPatchesTest test
```

---

### Task 3: 小启确认类型 `apply_script_patch`

**Files:**
- Modify: `AssistantActionService.java` ALLOWED / validateArgs / execute / confirmLabel
- Modify: `AssistantController.java` 增加 JWT `POST /api/assistant/script-patch/propose`

- [x] **Step 1: ALLOWED 加入 `apply_script_patch`**
- [x] **Step 2: args 校验 scriptId、expectedVersion、patches[]**
- [x] **Step 3: execute 调 ScriptService.applyPatches**
- [x] **Step 4: JWT propose 只允许该类型，并校验讲稿归属**
- [x] **Step 5: 勾选本任务**

---

### Task 4: 讲稿编辑器选区「问小启」

**Files:**
- Modify: `ScriptEditor.vue` + `script-editor-v2.css`
- Modify: `AssistantService.createSession` / `patchSession` 可写 `context_json`

- [x] **Step 1: 记住 `contentVersion`，问小启前 flush 自动保存**
- [x] **Step 2: 步骤正文选中后浮层「问小启」**
- [x] **Step 3: sessionStorage 写入 scriptId、stepId、role、focus、selection、步骤全文、前后步、contentVersion**
- [x] **Step 4: 跳转 `/assistant?from=script`**
- [x] **Step 5: 勾选本任务**

---

### Task 5: 小启出补丁卡并确认

**Files:**
- Modify: `assistantClient.js` + `AssistantWorkspace.vue` + 卡片模板
- Modify: `createSession` 接受 `contextJson`

- [x] **Step 1: 消费 `from=script` 上下文，建会话并钉住 context_json**
- [x] **Step 2: 自动发改写请求（只改这一格，锁角色）**
- [x] **Step 3: 模型返回后 JWT propose，聊天展示原文/建议/原因/确认**
- [x] **Step 4: 确认后讲稿该格更新，角色不变；回执带新版本**
- [x] **Step 5: 勾选本任务**

**P0 验收：**
1. 打开自己的讲稿，选中一句，点「问小启」。
2. 小启出卡，角色仍显示原角色。
3. 不点确认，刷新讲稿原文不变。
4. 点确认，该步正文变、角色/页码不变，`contentVersion` +1。

---

### Task 6: P1 评分对照清单

- [x] **Step 1: 钉住 scoreReportId + scriptId**
- [x] **Step 2: 只对评分点名的步骤出多条 patch**
- [x] **Step 3: 逐条确认，禁止推断扣分**
- [x] **Step 4: 勾选本任务**

---

### Task 7: P2 PPT 跟随

- [ ] **Step 1: 已确认步骤的 focus → 页码**
- [ ] **Step 2: 提案改字或 refine `target_pages`**
- [ ] **Step 3: 不自动整份重生成**
- [ ] **Step 4: 勾选本任务**

---

### Task 8: P3 讲稿表格视图

- [ ] **Step 1: ScriptEditor 增加表格视图（角色/页/时长/正文）**
- [ ] **Step 2: 与现有卡片视图共用同一份 steps**
- [ ] **Step 3: 勾选本任务**

---

## 进度

当前执行：**下一期 Task 7（P2 PPT 跟随）**  
已完成：Task 1–6（P0 确认写回 + P1 评分对照）、Task 9（智能文档改稿工作台）  
方案已落盘：`docs/superpowers/specs/2026-08-18-xiaoqi-script-ppt-agent-design.md`  
工作台规格：`docs/superpowers/specs/2026-08-18-xiaoqi-sdoc-workbench-design.md`

---

### Task 9: 智能文档当改稿工作台

**Files:**
- Create: `V122__script_sdoc_bind.sql`
- Create: `ScriptSdocCodec.java` + 测试
- Modify: `Script.java` / `ScriptService` / `ScriptController`
- Create: `scriptSdoc.js` + TipTap `scriptSheet` / `scriptStep`
- Modify: `ScriptEditor.vue` 入口
- Modify: `SmartDocEditor.vue` 问小启

- [x] **Step 1: `script.sdoc_document_id` + Codec 讲稿↔文档**
- [x] **Step 2: `POST /api/script/{id}/workbench-sdoc` 打开或创建绑定文档**
- [x] **Step 3: 编辑器渲染步骤表（角色/页/时长锁）**
- [x] **Step 4: 文档里选中「问小启」，确认后双写讲稿和 sdoc**
- [x] **Step 5: 勾选本任务**
