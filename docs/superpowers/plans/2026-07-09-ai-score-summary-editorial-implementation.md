# 评分总结编辑叙事 · 代码落地计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户端 AI 评分总结从「七 Tab 后台摊开」落地为原型 v5：全局一层侧栏 + 结果/待办/依据三情境 + 多维评委/对比为入口 + 真数据不 invent。

**Architecture:** 继续 `AiScoreReportLayout` + `useAiScoreReport` 单例数据层；新增 presentation 纯函数映射 UI；新增 `AiScoreSummaryChrome`（三情境顶栏）与结果/待办/依据三页（或一页三态）；旧七路由 redirect 兼容；深潜用抽屉组件，不嵌第二侧栏。

**Tech Stack:** Vue 3 + Vue Router + 现有 `useAiScoreReport.js` + `node:test` 单测 + OREP workspace tokens（`workspace-tokens.css`）

**Prototype reference:** `prototypes/ai-score-summary-editorial/index.html`（v5 一张纸）  
**Design specs:**  
- `docs/superpowers/specs/2026-07-09-ai-score-summary-editorial-design.md`  
- `docs/superpowers/specs/2026-07-09-ai-score-summary-full-ia-design.md`（含 §0 三情境、多维评委正确定义）

---

## 0. 已定产品约束（实现时不可回退）

| 约束 | 说明 |
|------|------|
| 顶栏仅 3 项 | **结果 · 待办 · 依据** |
| 无台中台 | 不用报告内第二侧栏 |
| 无硬编码业务文案 | 缺字段空态/隐藏，禁止「展示不完整…」类 fallback |
| 多维评委 | 16 抽 9、独立打分、去极值均分、**不改官方分**；不是模拟问答 |
| 表达/现场 | 嵌在待办条目「练一练」，不独立顶栏 |
| 视觉 | 一张纸；无浅色总分水印、无装饰点轨；数字 meta 在 hero 内 |
| 数据 | 只读现有 API / composable，本计划默认不改后端 |

---

## 1. 文件结构（创建 / 修改）

### 新建

| 路径 | 职责 |
|------|------|
| `frontend/user/src/components/ai-score/report/AiScoreSummaryChrome.vue` | 报告情境顶栏：标题、分数 pill、操作按钮、三情境 seg |
| `frontend/user/src/components/ai-score/report/AiScoreTodoDrawer.vue` | 单条待办深潜抽屉（可选，先页内详情也行） |
| `frontend/user/src/components/ai-score/report/AiScoreClipDrawer.vue` | 关键帧/发言抽屉 |
| `frontend/user/src/components/ai-score/report/AiScoreTeamSyncDialog.vue` | 同步团队任务弹窗 |
| `frontend/user/src/utils/aiScoreSummaryPresentation.js` | **扩展**（已有）：结果/待办/依据/评委入口的 view-model |
| `frontend/user/src/utils/aiScoreTodosPresentation.js` | 待办队列 + 单条叙事（why/how/practice/done） |
| `frontend/user/src/utils/aiScoreWhyPresentation.js` | 依据：维度 + filmstrip 帧列表 + 当前帧分析 |
| `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue` | **结果**页（替换 overview 主呈现） |
| `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue` | **待办**页 |
| `frontend/user/src/views/ai-score-report/AiScoreReportWhy.vue` | **依据**页（合并 dimensions 内容 + evidence 帧） |
| `frontend/user/src/utils/aiScoreTodosPresentation.test.js` | 待办映射单测 |
| `frontend/user/src/utils/aiScoreWhyPresentation.test.js` | 帧/分析映射单测 |

### 修改

| 路径 | 职责 |
|------|------|
| `frontend/user/src/router/index.js` | 三主路由 + 旧七路由 redirect |
| `frontend/user/src/views/ai-score-report/AiScoreReportLayout.vue` | 挂 Chrome；子路由 |
| `frontend/user/src/components/ai-score/report/AiScoreReportShell.vue` | 保留 `editorial`；三页用 Chrome 替代旧 title+tabs |
| `frontend/user/src/composables/useAiScoreReport.js` | `navItems` 改为三情境；`sectionPath` 映射；导出已有 jury/tasks |
| `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue` | 改为 redirect 到 `result` 或薄包装 |
| `frontend/user/src/views/ai-score-report/AiScoreReportJury.vue` | 文案与入口对齐「多维评委」；去「答辩」主叙事 |
| `frontend/user/src/views/ai-score-report/AiScoreReportActions.vue` 等 | 可保留文件，路由指向新页；逐步删死代码 |

### 暂不新建后端

本计划零后端改动。Coaching 无 meetingId 时诚实空态。

---

## 2. 路由映射

```
# 新主路径（session / reportId / meeting 三套父路由各一套）
.../result     → AiScoreReportResult.vue     # 结果
.../todos      → AiScoreReportTodos.vue      # 待办
.../why        → AiScoreReportWhy.vue        # 依据

# 次级（仍可进，不在顶栏三 seg）
.../jury       → AiScoreReportJury.vue       # 多维评委
.../compare    → AiScoreReportCompare.vue    # 可选 Phase 后置；无数据时结果页隐藏入口

# 兼容 redirect
overview       → result
dimensions     → why
evidence       → why
voice|presentation → todos  (?focus=voice|stage 可选)
actions        → todos
''             → result
```

`sectionPath('result'|'todos'|'why'|'jury'|'compare')` 在 composable 中统一生成。

---

## 3. 数据映射（实现清单）

### 结果页

| UI | 来源 | 空态 |
|----|------|------|
| 大分 | `overallScore` | Layout 错误态 |
| 等级/旁注 | `scoreLevel` | 仅显示分 |
| 标题句 | `ai_score.overall_conclusion` 等 | 不显示假标题 |
| 导语 | `overall_analysis` | 隐藏 |
| meta 四数 | `scoreRecoverySummary` + 待办数 | 单项无则不渲染该 metric |
| Top3 待办 | `trainingTasks` → deductions → drafts | 空列表 + 链到 why |
| 多维评委卡 | `overallScore` + jury 均分/分差（有则填，无则 CTA「生成」） | 显示官方分 + 生成按钮 |
| 五维列表 | `dimensions` | 整段隐藏 |
| 继续 | 固定导航文案（产品 chrome，非业务数据） | — |

### 待办页

| UI | 来源 |
|----|------|
| 队列 | 同 Top3 全量列表，排序 P0→可追回分 |
| 为什么 | `reason` / `correspondingDeduction` |
| 怎么改 | `trainingAction` / `required_fix` |
| 怎样算好了 | `acceptanceCriteria`（字符串拆条或单段） |
| 练一练 | expression/presentation coaching 按时间/标题弱匹配；无则**不显示练一练块** |
| 派任务 | `createTeamTasksFromReport` + 团队列表 |

### 依据页

| UI | 来源 |
|----|------|
| filmstrip | `evidenceFrames` + `visualFrames`，优先带 anchor 关联的帧置前 |
| 当前分析 | frame caption/ocr + 关联 deduction reason + observation modelReason |
| 维度侧栏 | `dimensions` |
| 关联待办 | 由 anchorIds / 时间近邻匹配到 deduction/task |

**禁止：** 无分析时编造画面解读；可显示「本帧暂无文字分析」。

### 多维评委

沿用现有 jury API；UI 文案改为 16/9/独立分/去极值/不改官方分。

---

## 4. 实施任务

### Task 1: 路由与 nav 三情境

**Files:**
- Modify: `frontend/user/src/router/index.js`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`（`navItems` / `sectionPath`）

- [ ] **Step 1:** 在三套父路由 children 中增加 `result` / `todos` / `why`，默认 `''` → `result`。
- [ ] **Step 2:** 将 `overview`、`dimensions`、`evidence`、`voice`、`presentation`、`actions` 改为 redirect（见 §2）。
- [ ] **Step 3:** `navItems` 改为：

```js
[
  { key: 'result', label: '结果' },
  { key: 'todos', label: '待办', count: todoCount },
  { key: 'why', label: '依据' }
]
```

- [ ] **Step 4:** 本地访问 `/ai-score/report/:id/overview` 应落到 result（临时可用旧 Overview 组件挂在 result 上，下一步替换）。
- [ ] **Step 5:** Commit `feat(ai-score): three-context routes result/todos/why`

---

### Task 2: Summary Chrome 组件

**Files:**
- Create: `frontend/user/src/components/ai-score/report/AiScoreSummaryChrome.vue`
- Modify: `AiScoreReportLayout.vue` 或各页引入

- [ ] **Step 1:** 实现 props：`title`、`score`、`levelLabel`、`subtitle`、`activeKey`、`todoCount`。
- [ ] **Step 2:** 三 seg `RouterLink` 到 `sectionPath`；右侧：下载报告、返回会议、同步到任务（emit 或调 context）。
- [ ] **Step 3:** 样式对齐 workspace tokens + 原型顶栏（无七 Tab）。
- [ ] **Step 4:** Commit `feat(ai-score): summary chrome with three segments`

---

### Task 3: 扩展 presentation 层（TDD）

**Files:**
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.js`
- Create: `aiScoreTodosPresentation.js` + test
- Create: `aiScoreWhyPresentation.js` + test

- [ ] **Step 1:** 写 `buildTodosPresentation` 失败测试：无 invent、排序、TopN。

```js
// 断言：无 trainingAction 时 practice 为空对象/不出现假话术
// 断言：P0 优先于 P2
```

- [ ] **Step 2:** 实现至测试通过。
- [ ] **Step 3:** 写 `buildWhyPresentation`：帧列表、选中帧分析字段仅来自真实 caption/reason。
- [ ] **Step 4:** 扩展 `buildScoreSummaryPresentation`：增加 `continueLinks`、`juryTeaser`（仅数字有则填）。
- [ ] **Step 5:** Run:

```bash
cd frontend/user && node --test src/utils/aiScoreSummaryPresentation.test.js src/utils/aiScoreTodosPresentation.test.js src/utils/aiScoreWhyPresentation.test.js
```

- [ ] **Step 6:** Commit `feat(ai-score): presentation mappers for result/todos/why`

---

### Task 4: 结果页 AiScoreReportResult.vue

**Files:**
- Create: `AiScoreReportResult.vue`
- Modify: router `result` 指向新组件
- Deprecate: `AiScoreReportOverview.vue` 改为 redirect 或删除引用

- [ ] **Step 1:** 结构：Chrome + scroll：hero（大分、标题、导语、metrics 横排）→ Top3 列表 → 多维评委浅色卡 → 五维列表 → 继续链接。
- [ ] **Step 2:** 绑定 `buildScoreSummaryPresentation` + context 操作。
- [ ] **Step 3:** 禁止假 fallback 文案；对照现有 overview 删除硬编码。
- [ ] **Step 4:** 视觉：一张纸、无水印/点轨；tokens 来自 workspace。
- [ ] **Step 5:** 手测 session 真实报告 + 空字段报告。
- [ ] **Step 6:** Commit `feat(ai-score): editorial result page`

---

### Task 5: 待办页 + 同步弹窗

**Files:**
- Create: `AiScoreReportTodos.vue`
- Create: `AiScoreTeamSyncDialog.vue`

- [ ] **Step 1:** 左队列 + 右教练叙事（为什么 / 怎么改 / 怎样算好了 / 练一练条件渲染）。
- [ ] **Step 2:** 无四宫格；`练一练` 仅当有 coaching 或明确话术字段。
- [ ] **Step 3:** `AiScoreTeamSyncDialog`：真 `availableTeams`、勾选 workItem drafts、`createTeamTasksFromReport`。
- [ ] **Step 4:** 结果页「同步到任务」「派给队友」共用 Dialog。
- [ ] **Step 5:** Commit `feat(ai-score): todos page and team sync dialog`

---

### Task 6: 依据页（帧条 + 分析）

**Files:**
- Create: `AiScoreReportWhy.vue`
- Optional: `AiScoreClipDrawer.vue`

- [ ] **Step 1:** 主舞台 + 分析栏 + 横向 filmstrip（默认展示关联优先的 N 帧，N≈8–12）。
- [ ] **Step 2:** 「浏览全部」展开更多或提高 N（注意性能：v-for 可截断 + 按钮加载）。
- [ ] **Step 3:** 帧切换更新分析；无分析显示诚实空态。
- [ ] **Step 4:** 下方：五维摘要 + 关联待办跳转 `todos`。
- [ ] **Step 5:** Commit `feat(ai-score): why page with keyframe filmstrip`

---

### Task 7: 多维评委页文案与入口

**Files:**
- Modify: `AiScoreReportJury.vue`
- Result 页 feature 卡 → `sectionPath('jury')`

- [ ] **Step 1:** 文案统一：16 人格池、抽 9、独立分、去极值、不改官方分。
- [ ] **Step 2:** 去掉「模拟答辩/预演质疑」作为主标题。
- [ ] **Step 3:** 结果页浅色 feature 卡展示官方分/均分/分差（有 jury 数据时）；无则 CTA 生成。
- [ ] **Step 4:** Commit `feat(ai-score): jury as multi-persona scoring feature`

---

### Task 8: 对比入口（轻量）

**Files:**
- Create: `AiScoreReportCompare.vue`（可极简）
- Result「继续」第三项：仅当 `previous_score_delta` 或 recovery 有数据时显示

- [ ] **Step 1:** 有数据渲染分差 + 已追回/新问题列表（来自 structured deductions recovery 标记）。
- [ ] **Step 2:** 无数据：结果页不展示入口。
- [ ] **Step 3:** Commit `feat(ai-score): optional compare entry`

---

### Task 9: 清理与验收

- [ ] **Step 1:** 旧七 Tab Shell 模式：深页若仍用 Shell，tabs 改为隐藏（仅 Chrome 导航）。
- [ ] **Step 2:** `npm run build`（`frontend/user`）通过。
- [ ] **Step 3:** 手测清单：

```
- [ ] /result 滚动一体、无水印
- [ ] Top3 / 待办数据与 API 一致
- [ ] 缺 conclusion 不显示假标题
- [ ] 同步任务成功跳转或 toast
- [ ] /why 帧切换与空分析
- [ ] /jury 不改官方分文案正确
- [ ] 旧 /overview /dimensions 链接不 404
- [ ] 上传 session 无 meeting 时 coaching 空态不崩
```

- [ ] **Step 4:** Commit `chore(ai-score): cleanup nav and verify build`

---

## 5. 分期交付（可合并 PR）

| Phase | 任务 | 用户可见 |
|-------|------|----------|
| **P1** | 1–4 | 新结果页 + 三路由壳 |
| **P2** | 5–6 | 待办 + 依据完整 |
| **P3** | 7–8 | 多维评委打磨 + 对比 |
| **P4** | 9 | 清理兼容 |

建议每个 Phase 单独 PR，避免巨型 diff。

---

## 6. 风险

| 风险 | 缓解 |
|------|------|
| 处方 id 与 workItem 对不齐 | Dialog 以 `reportWorkItemDrafts` 为准；映射失败提示去待办勾选 |
| 帧过多卡顿 | 默认 N 帧 + 「更多」；图片 lazy |
| 旧书签失效 | redirect 全覆盖 |
| Overview 已有半套 editorial | Result 以原型 v5 为准重写，勿叠旧 KPI 卡片 |

---

## 7. Spec 覆盖自检

| Spec 要点 | Task |
|-----------|------|
| 三情境顶栏 | 1, 2 |
| 结果一张纸 | 4 |
| 待办教练流无四宫格 | 5 |
| 依据帧条 + 分析 | 6 |
| 多维评委 16/9 | 7 |
| 对比条件入口 | 8 |
| 不 invent | 3 单测 + 全页空态 |
| 旧路由兼容 | 1, 9 |

---

## 8. 执行方式

Plan 已保存至 `docs/superpowers/plans/2026-07-09-ai-score-summary-editorial-implementation.md`。

**可选执行方式：**

1. **Subagent-Driven（推荐）** — 每任务新开 subagent，任务间 review  
2. **Inline Execution** — 本会话按 executing-plans 连续做，设 checkpoint  

回复 **1** 或 **2**（或「从 P1 开始」）即可开工。
