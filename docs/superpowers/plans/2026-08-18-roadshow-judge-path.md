# 路演台 Implementation Plan

> **For agentic workers:** 按任务顺序做。每完成一步把本文件对应 `- [ ]` 改成 `- [x]`，并在任务下写一行「完成：日期 + 验证命令」。不要另开进度文档。

**Goal:** 学生不用填问卷。系统用讲稿 + 这次评分 + 证据，整理出这场要讲清的几件事；过闸后做成能改字的 pptx。已有 PPT 从交来到还回去是标准文件。讲稿对页靠翻页/动作记号 + 对照表，不靠猜。

**Architecture:** 编译器纯函数（Java）产出 `judge_path`。讲稿 `script.content` + 逐字稿记号是口播真源。已有 PPT 只在服务端改副本 OOXML。小启确认卡沿用 `ai_assistant_action_proposal`。Collabora 只给人精调。

**Tech Stack:** Spring Boot + Flyway V124+；Vue3 学生端；JUnit / node:test。复用 `ScriptScoreRevisePlanner`、`ScriptService`、启发 Office 存盘。

**已定规格（不要再改方向）：**

| 文档 | 管什么 |
|---|---|
| `docs/superpowers/specs/2026-08-18-judge-path-roadshow-design.md` | 提纲、闸、页型、分期 |
| `docs/superpowers/specs/2026-08-18-existing-ppt-full-chain-design.md` | 交来、分档、OOXML、交付 |
| `docs/superpowers/specs/2026-08-18-script-page-binding-design.md` | 翻页/动作/现场怎么对页 |
| `docs/superpowers/mocks/judge-path-hifi/index.html` | 文案和屏 |

**界面用词（代码注释可用内部名，UI 不许）：** 做成 PPT、这场先不写、能改字、这页是图、讲稿对哪一页。禁止：令牌、命题、印刷、L1/L2、OOXML。

---

## 文件地图（A 期）

| 路径 | 职责 |
|---|---|
| `backend/.../service/roadshow/EvidenceTokenizer.java` | 从讲稿抽数字/对比/专名 |
| `backend/.../service/roadshow/StepActClassifier.java` | 步骤分幕 |
| `backend/.../service/roadshow/ScriptCueParser.java` | 逐字稿：角色、翻页、动作、现场 |
| `backend/.../service/roadshow/JudgePathGates.java` | 闭包、禁词、念稿、回收、页数 |
| `backend/.../service/roadshow/JudgePathCompiler.java` | 装配命题/漏洞 |
| `backend/.../service/roadshow/JudgePathService.java` | 鉴权、落库、confirm |
| `backend/.../controller/RoadshowPathController.java` | `/api/roadshow/path/*` |
| `backend/src/main/resources/db/migration/V124__judge_path.sql` | 表 |
| `frontend/user/src/views/roadshow/RoadshowGate.vue` | 双门 |
| `frontend/user/src/views/roadshow/RoadshowPath.vue` | 这场怎么讲 |
| `frontend/user/src/views/roadshow/RoadshowBind.vue` | 讲稿对哪一页 |
| `frontend/user/src/services/roadshowPathClient.js` | API |
| `frontend/user/src/router/index.js` | 路由，替换 `/ppt-editor` 落地 |

---

## 阶段总表

| 期 | 状态 | 目标 | 可演示 |
|---|---|---|---|
| **A** | 完成 | 提纲能看、能过闸、讲稿能切段 | 双门 → 这场怎么讲；红闸做不成 PPT |
| **B** | 完成 | 过闸做成能改字的页 | 确认后下载标准 pptx |
| **C** | 未开始 | 已有 PPT 全链 | 交来 → 分档 → 对照 → 新文件，原件不动 |
| **D** | 未开始 | 路演台 + 改稿跟一页 | 左稿右页，改一句只问一页 |
| **E** | 未开始 | 第二次评分只重开被打穿的 | 72→76 只黄一页 |
| **F** | 可砍 | 附录、清单页型、表格视图 | — |

A 过不了，B 不许开工。

---

## A 期

### Task A1: 令牌抽取

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/roadshow/EvidenceTokenizer.java`
- Create: `backend/src/test/java/com/orep/backend/service/roadshow/EvidenceTokenizerTest.java`

- [x] **Step 1: 失败测试** — 讲稿「损耗 23%」「三个试点」抽出 metric 23%、不含金额；「节约 12 万」无资源时不建金额令牌
- [x] **Step 2: 实现 tokenizer**
- [x] **Step 3: 单测通过** `mvn -q -Dtest=EvidenceTokenizerTest test`
- [x] **本任务勾选**

完成：2026-08-18 · `mvn -q -Dtest=EvidenceTokenizerTest test` 通过

### Task A2: 步骤分幕 + 逐字稿切段

**Files:**
- Create: `StepActClassifier.java` + `ScriptCueParser.java` + 对应 Test

- [x] **Step 1: 分类测试** — 损耗/痛点→problem；交给下一位→logistics；演示/拔线→demo
- [x] **Step 2: 番茄稿切段测试** — 收齐 `（翻页）`；「PPT 同步展示团队分工表」为 ppt_show；代码/拔线/现场结果为 live；产业→工程中心标 fat
- [x] **Step 3: 实现并跑通** `mvn -q -Dtest=StepActClassifierTest,ScriptCueParserTest test`
- [x] **本任务勾选**

完成：2026-08-18 · 番茄稿切段 + 分幕单测通过

### Task A3: 编译器 + 闸

**Files:**
- Create: `JudgePathGates.java` `JudgePathCompiler.java` + Test

- [x] **Step 1: 规格第 4.6 七条闸的失败测试**（闭包、禁词、念稿、回收、覆盖、logistics 无页、页数）
- [x] **Step 2: 实现 compile(steps, scoreItems, tokens) → propositions + holes + gateReport**
- [x] **Step 3: 无评分时 coverage=`unpinned` 仍能出最小幕**
- [x] **Step 4:** `mvn -q -Dtest=JudgePathCompilerTest test`（闸合在此文件）
- [x] **本任务勾选**

完成：2026-08-18 · 经济性无金额出漏洞；认账后才 canPrint；23% 无回收不过闸

### Task A4: 落库 + API

**Files:**
- Create: `V124__judge_path.sql` `JudgePathService.java` `RoadshowPathController.java` + 服务测试

- [x] **Step 1: 表 judge_path / judge_path_revision**
- [x] **Step 2: POST `/api/roadshow/path/compile` GET `/api/roadshow/path/{id}` POST confirm（红闸 409）**
- [x] **Step 3: 鉴权同讲稿 createdBy；钉 scriptId + scoreReportId**
- [x] **本任务勾选**

完成：2026-08-18 · Flyway 已到 v124（`Migrating schema orep to version "124 - judge path"`）。

### Task A5: 双门 + 这场怎么讲 + 对照表

**Files:**
- Create: `frontend/user/src/views/roadshow/*` `roadshowPathClient.js` `tests/roadshow-copy.test.mjs`
- Modify: `frontend/user/src/router/index.js`、`AiAppCenter.vue`（**另加**「路演台」，不替换 PPT 制作）

- [x] **Step 1: 路由 `/roadshow` 双门、`/roadshow/path/:id`、`/roadshow/bind/:id`**
- [x] **Step 2: 文案测试禁止「令牌/命题/印刷/L1」出现在 UI 字符串**
- [x] **Step 3: 红闸时主按钮禁用，文案「还有内容没有出处」**
- [x] **Step 4: 对照表按提纲段列出；现场/无页标「不配新页」**
- [x] **本任务勾选**

完成：2026-08-18 · 旧 PPT 制作入口保留。应用中心新增「路演台」→ `/roadshow`。`node --test tests/roadshow-copy.test.mjs` 通过。

**A 期验收：** 番茄逐字稿切段测试绿；智慧农业讲稿 compile 出漏洞；UI 红闸点不了做成 PPT。

---

## B 期 · 过闸做成能改字的页

旧「PPT 制作」入口不动。路演台确认后才出页。

### Task B1: 页型规划纯函数

**Files:** `PageTypePlanner.java` + `PageTypePlannerTest.java`

- [x] 按 act 选出 cover/problem/contrast/architecture/process/demo/evidence/list/close
- [x] 无 printPage 的段不进页
- [x] 有「23% → 9%」走 contrast
- [x] 本任务勾选

完成：2026-08-18 · `mvn -q -Dtest=PageTypePlannerTest test` 通过。对比令牌写入 onSlide.number，规划器走 contrast。

### Task B2: 标准 pptx 写出

**Files:** `RoadshowPptxWriter.java` + Test；`JudgePathService.print/download`

- [x] zip 包含 ppt/slides/slideN.xml，标题是真实 `<a:t>`
- [x] 未过闸 print → 409
- [x] GET `/api/roadshow/path/{id}/download`
- [x] 本任务勾选

完成：2026-08-18 · `mvn -q -Dtest=RoadshowPptxWriterTest,JudgePathServicePrintTest test` 通过。slide XML 有 `<a:t>`、无 `a:blip`；未认账 print 抛 409。

### Task B3: 预览屏

**Files:** `RoadshowPrint.vue` `RoadshowSlide.vue`；路由 `/roadshow/print/:id`

- [x] 确认后进入预览
- [x] 下载走标准 pptx
- [x] 本任务勾选

完成：2026-08-18 · 确认 → `/roadshow/print/:id`；下载 GET `/api/roadshow/path/{id}/download`。`node --test tests/roadshow-copy.test.mjs` 通过。旧 `/ppt-editor` 入口未动。

## C 期

- [x] C1 ingest：文档库/上传/拒密码与超大

完成：2026-08-18 · 文档库列出已有 pptx；拖入本机；密码/超大/PDF 用人话拒。`mvn -q -Dtest=LegacyDeckInspectorTest test` 通过。
- [x] C2 每页阅读档：能改字 / 部分 / 图 / 空

完成：2026-08-18 · 收下后进分档页。单测锁死文字页/图页/空页。旧整页图稿会标「这页是图」，不装已识别。
- [x] C3 对照表对齐讲稿段

完成：2026-08-18 · 交完 PPT 后主按钮是「对着讲稿改」。对照页列出改字/换页/拿掉/补页/先不动。未改文件。`mvn -q -Dtest=LegacyAlignerTest test` 通过。
- [ ] C4 OOXML 改副本：改字/换页/拿掉/补页
- [ ] C5 新版本 + 下载，原件 hash 不变

## D 期

- [ ] D1 启发 Office 路演台布局
- [ ] D2 改讲稿后只问对应一页
- [ ] D3 现场段不换页

## E 期

- [ ] E1 replay diff：kept / broken / new
- [ ] E2 只重开被打穿的段

## F 期（可砍）

- [ ] 清单页型、附录、讲稿表格视图（原 Task 8）

---

## 实行记录

| 时间 | 任务 | 结果 |
|---|---|---|
| 2026-08-18 | A1 令牌抽取 | 通过 |
| 2026-08-18 | A2 分幕 + 番茄稿切段 | 通过 |
| 2026-08-18 | A3 编译器 + 闸 | 通过 |
| 2026-08-18 | A4 落库 + API | Flyway v124 已上 |
| 2026-08-18 | A5 路演台入口 | 应用中心另开「路演台」，旧 PPT 制作保留 |
| 2026-08-18 | B1 页型规划 | 无 printPage 不进页；23% → 9% 走 contrast |
| 2026-08-18 | B2 标准 pptx | 文本框写出；未过闸 print 409 |
| 2026-08-18 | B3 预览下载 | 确认进预览，下载能改字的 pptx |
| 2026-08-18 | 路演台 UI 对齐用户端 | AiAppShell + 学生按钮/卡片；去掉「回双门」 |
| 2026-08-18 | C1 交 PPT | 文档库/拖入；密码、超大、PDF 拒收 |
| 2026-08-18 | C2 阅读档 | 能改字 / 这页是图 / 空页 |
