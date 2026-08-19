# 启发 Office 智能文档 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在启发 Office 中新增金山式智能文档（TipTap Block 编辑器），布局对标金山、视觉用竞赛大脑 DESIGN.md，并与小启 AI 读写联动。

**Architecture:** `ext=sdoc` 走独立 TipTap 编辑器，不进 Collabora。元数据沿用 `inspire_office_document`，正文 JSON 存 `inspire_smart_doc`。小启通过 `context.type=inspire_sdoc` 读选区、确认后写回块。

**Tech Stack:** Vue 3 + TipTap 2/3 + 现有 Spring Boot `/api/inspire-office` + `/api/assistant` + `--ds-*` tokens。

**规格：** `docs/superpowers/specs/2026-08-17-inspire-smart-doc-design.md`

---

## 文件地图

| 路径 | 职责 |
|---|---|
| `frontend/user/src/views/inspire-office/smart-doc/*` | 编辑器全部 UI |
| `frontend/user/src/styles/smart-doc.css` | 纸张/块/菜单，只用 `--ds-*` |
| `frontend/user/src/services/inspireOfficeClient.js` | 增加 sdoc API |
| `frontend/user/src/views/inspire-office/InspireOfficeList.vue` | 新建类型 |
| `frontend/user/src/views/inspire-office/InspireOfficeWorkbench.vue` | `sdoc` 窗格切 TipTap |
| `frontend/user/src/router/index.js` | `/inspire-office/sdoc/:id` |
| `backend/.../service/SmartDocService.java` | JSON 读写、乐观锁、快照 |
| `backend/.../controller/InspireOfficeController.java` | `/sdoc` 端点 |
| SQL migration | `inspire_smart_doc` 表 |
| `frontend/user/src/modules/assistant-core/*` | 文档上下文与写回确认 |
| `frontend/user/tests/smart-doc-*.mjs` | schema / 保存 / slash 契约 |

---

## 阶段总览

| 阶段 | 目标 | 可演示 |
|---|---|---|
| **P0 能写能存** | 对标截图的壳 + 基础块 + 自动保存 | 新建、打字、高亮块、刷新还在 |
| **P1 金山常用块** | 表/分栏/文件/日期音视频，**不含 AI** | 日常备赛说明 |
| **P2 结构与权限** | 目录可用、保护区、版本 | 团队文档可用 |
| **P3 图类块** | 思维导图、流程图 | 块内嵌编辑 |
| **P4 教师端与导出** | 教师打开、Markdown/HTML | 师生同一文档 |
| **P5 小启** | 选区问小启、写回、侧栏 | 文档做好后再做 |

一次只做一个阶段。P0 完成再开 P1。

---

## P0 — 能写能存（约 5–7 日）

### Task 1: 依赖与空 schema

**Files:**
- Modify: `frontend/user/package.json`
- Create: `frontend/user/src/views/inspire-office/smart-doc/schema/smartDocExtensions.js`
- Create: `frontend/user/tests/smart-doc-schema.test.mjs`

- [ ] 安装 `@tiptap/vue-3` `@tiptap/starter-kit` `@tiptap/extension-placeholder` `@tiptap/extension-link` `@tiptap/extension-underline` `@tiptap/extension-task-list` `@tiptap/extension-task-item`
- [ ] `smartDocExtensions.js` 导出 `createSmartDocExtensions()`，包含 StarterKit（关 heading 以外的多余）、Placeholder「输入 / 插入」
- [ ] 测试：extensions 创建不抛错；文档空 doc 合法
- [ ] 命令：`cd frontend/user && node --test tests/smart-doc-schema.test.mjs`

### Task 2: 存储表与 API

**Files:**
- Create: `backend/src/main/resources/db/migration/Vxxx__inspire_smart_doc.sql`
- Create: `backend/.../entity/InspireSmartDoc.java`
- Create: `backend/.../service/SmartDocService.java`
- Modify: `InspireOfficeController.java`、`InspireOfficeService.createBlank` 允许 `ext=sdoc`

```sql
CREATE TABLE IF NOT EXISTS inspire_smart_doc (
  document_id BIGINT PRIMARY KEY,
  content_json MEDIUMTEXT NOT NULL,
  schema_version INT NOT NULL DEFAULT 1,
  updated_at DATETIME NOT NULL,
  CONSTRAINT fk_sdoc_doc FOREIGN KEY (document_id) REFERENCES inspire_office_document(id)
);
```

- [ ] `POST /documents/blank` 支持 `ext=sdoc`：写元数据 + 插入默认 `{"type":"doc","content":[{"type":"paragraph"}]}`
- [ ] `GET /api/inspire-office/sdoc/{id}` 返回 `{ document, content, updatedAt }`
- [ ] `PUT /api/inspire-office/sdoc/{id}` body `{ content, updatedAt }`，乐观锁：传入的 `updatedAt` 落后则 409
- [ ] 权限复用现有 inspire office 读/写校验
- [ ] 后端单测：create + get + put + 409（可 H2，对标 `TeacherPortalCampLifecycleTest` 风格）

### Task 3: 列表「新建智能文档」

**Files:**
- Modify: `InspireOfficeList.vue`、`inspireOfficeClient.js`

- [ ] 新建菜单三项：智能文档 / Word / 表格（PPT 保持原入口）
- [ ] 智能文档 `createBlank({ ext: 'sdoc' })` 后 `router.push('/inspire-office/sdoc/' + id)`
- [ ] 列表类型标记：`sdoc` 用文档块图标，文案「智能文档」
- [ ] Word/Excel 行为不变

### Task 4: 纸张编辑器壳

**Files:**
- Create: `SmartDocEditor.vue`、`SmartDocCanvas.vue`、`smart-doc.css`
- Modify: `router/index.js`

布局硬规则：

- 页衬 `--ds-canvas-sidebar` 或 `#f5f5f5`
- 纸宽 `min(760px, 100% - 48px)`，水平居中，白底，无阴影
- 顶栏高 52px，返回、标题、保存态（已保存 / 保存中 / 未保存）、小启按钮
- 正文 16px / line-height 1.75，`padding: 48px 64px 96px`
- 控件尺寸走 DESIGN.md（按钮 40px，焦点橙圈）

- [ ] 路由 `/inspire-office/sdoc/:id`，meta 与启发 Office 同组
- [ ] 打开拉 GET，挂 TipTap
- [ ] 标题点击即改，调现有 rename API
- [ ] 移动端纸张左右 padding 16px

### Task 5: 自动保存

**Files:**
- Create: `persist/useSmartDocSave.js`
- Test: `tests/smart-doc-save.test.mjs`（测 debounce 与 409 不覆盖，可抽纯函数）

- [ ] 文档 `update` 后 1s debounce PUT
- [ ] 顶栏显示保存态
- [ ] 409：提示「已在其他处更新」，提供「重新加载」
- [ ] `beforeunload` 有未保存则拦截
- [ ] presence 心跳沿用 `/documents/{id}/presence`，kind=`sdoc`

### Task 6: `/` 菜单与选区条

**Files:**
- Create: `slash/SlashMenu.vue`、`bubble/SelectionToolbar.vue`

- [ ] 空段 `/` 弹出：段落、标题、列表、待办、引用、代码、高亮块、分隔线、图片
- [ ] 键盘上下 + Enter，Esc 关闭
- [ ] 选区浮层：粗 / 斜 / 删 / 链 / 高亮
- [ ] 样式：白底 `#e2e4ea` 边框，仅浮层可用 `--ds-shadow-float`

### Task 7: P0 自定义块 — 高亮块 + 图片

**Files:**
- Create: `nodes/HighlightBlock.ts` 或 `.js` + `HighlightBlockView.vue`
- 图片：TipTap Image + 上传走现有 upload API

- [ ] 高亮块：左侧色条 + 可选 emoji + 内容可再写段落
- [ ] 色板用设计规范浅底，不要彩虹
- [ ] 图片：粘贴/上传，存 URL，禁止 base64 进 JSON

### Task 8: P0 验收

- [ ] 新建智能文档 → 输入标题和三段正文 → 插高亮块和一张图 → 刷新仍在
- [ ] Word 文档仍走 Collabora
- [ ] 学生端 375 宽可编辑
- [ ] `node --test tests/smart-doc-*.mjs` 通过

---

## P1 — 金山常用块（约 5–7 日，不含 AI）

### Task 9: 表格、分栏

- [x] `@tiptap/extension-table`：插入 3×3，增删行列，表头行
- [x] 表样式：细线 `#e5e6ea`，选中单元格淡橙底
- [x] 分栏节点 `columns`：2 栏 / 3 栏，每栏仍是块容器
- [x] `/` 菜单加入「表格」「分栏」

### Task 10: 文件与云文档卡片

- [x] `fileCard`：上传本地文件，展示名/大小/下载
- [x] `cloudDoc`：从启发 Office 或资源中心挑一篇，卡片打开
- [x] 日期节点、emoji、音视频（`<video>`/`<audio>` src 为上传 URL）

### Task 13: 工作台兼容

- [x] `InspireOfficeWorkbench`：若 tab.ext===`sdoc`，窗格渲染 `SmartDocEditor` embed 模式，不加载 Collabora
- [x] 分屏：一边 Word 一边智能文档允许

### Task 14: P1 验收

- [ ] 一份「备赛说明」：标题、分栏、表、附件、高亮，保存再开
- [ ] 选中一段 → 小启改写成清单 → 确认写回
- [ ] Collabora 文档不受影响

---

## P2 — 结构、版本、保护区（约 5–7 日）

### Task 15: 标题目录

- [x] 左侧可选目录，扫 heading 1–3，点击滚动
- [x] 窄屏隐藏

### Task 16: 版本快照

- [x] 沿用列表里的版本入口：对 sdoc 存 JSON 快照
- [x] 恢复覆盖当前 `content_json`，写审计

### Task 17: 内容保护区

- [x] 节点 `protectedRegion`：attrs `{ minRole, label }`
- [x] 无权限：灰占位「此段仅教师可见」
- [x] 有权限：正常编辑，左边锁标
- [x] 后端 GET 按角色剥离或打标（P2 至少前端按 role 隐藏，P2.1 后端剥离防泄露）

### Task 18: 乐观锁与离线

- [x] 409 提供「保留我的 / 用服务器的」
- [x] localStorage 暂存未发出的 JSON，重开可恢复

---

## P3 — 图类块（约 5 日，可后置）

### Task 19: 思维导图块

- [x] 自定义节点，块内嵌轻量导图（候选：自研二级节点 或 现成 MIT 库）
- [x] JSON 只存导图数据，不存画布位图
- [x] `/` → 思维导图

### Task 20: 流程图块

- [x] 同样嵌独立图编辑（节点/边 JSON）
- [x] 不做 Visio 级，P3 只求能画框和箭头

---

## P4 — 教师端与导出（约 3–4 日）

### Task 21: 教师端打开

- [x] 教师启发 Office 或资源中心打开 sdoc 用同一套 `SmartDocEditor`（抽到两边可 import 的目录，或教师端 iframe 学生编辑器路由——优先抽 shared 模块）
- [x] 权限：团队教师可编

### Task 22: 导出

- [x] 导出 Markdown（块映射）
- [x] 导出 HTML（打印/交作业）
- [x] Word 导出不承诺保真，有再说

---

## P6 — 多人协同（在场先于合稿）

规格：`docs/superpowers/specs/2026-08-18-sdoc-collab-design.md`

### P6-A 在场与按人着色

- [x] STOMP 房间 + 头像堆 + 远程光标
- [x] 按人物着色（`authorId` + 开关）
- [x] 保护区预览不泄漏

### P6-B 同时打字（未开始）

- [ ] Yjs 走 STOMP，保护区分房间

---

## 设计对照清单（每阶段结束过一遍）

对照金山交互、我们的视觉：

- [ ] 居中纸，不是通栏 Word
- [ ] 无 Office Ribbon
- [ ] `/` 与块手柄在，不靠顶栏堆图标
- [ ] 颜色/字号/按钮只用来自 `DESIGN.md` 的 token
- [ ] 主按钮白字深橙，焦点可见
- [ ] 内容层无投影

对照小启：

- [ ] 不出现第二套 AI 聊天 UI
- [ ] 写文档必须确认
- [ ] 会话能回到该文档

---

## 建议开工顺序（本周）

1. Task 2 表 + API（先有存的地方）  
2. Task 1 + 4 + 5（先能打开一张纸）  
3. Task 3 列表入口  
4. Task 6–7 `/` 和高亮  
5. Task 8 验收后再动 P1 小启  

不要先做导图、协同、导出 Word。
