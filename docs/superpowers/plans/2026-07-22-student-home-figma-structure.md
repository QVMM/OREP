# 学生首页 Figma 结构稿 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个可评审的 Figma 文件，同时展示当前学生首页审计、桌面端优化结构和移动端优先级结构。

**Architecture:** 使用一个新 Figma 文件和一个主页面，主页面内以三个顶层 Section 组织交付物。先放置原始截图与问题标注，再使用组件化的卡片、按钮、状态标签、日历项和流程项组装桌面与移动端结构。每完成一个分区立即渲染截图检查，最后对整个页面做可见性和结构验收。

**Tech Stack:** Figma Plugin API via `use_figma`, Figma MCP `create_new_file` / `get_screenshot` / `get_metadata`, Auto Layout, local Figma components, existing OREP design tokens, PNG reference screenshot.

---

## File and artifact map

- Reference screenshot: `/Users/liuyixing/.codex/visualizations/2026/07/22/019f89d5-18f2-7063-9c65-f08ab60eac01/orep-student-home-audit/01-student-home.png`
- Approved design spec: `/Users/liuyixing/项目/OREP/docs/superpowers/specs/2026-07-22-student-home-figma-structure-design.md`
- Execution plan: `/Users/liuyixing/项目/OREP/docs/superpowers/plans/2026-07-22-student-home-figma-structure.md`
- Figma output: new file named `竞赛大脑 · 学生首页结构优化`
- Figma page: `学生首页优化`
- Top-level sections:
  - `01 现状与审计`
  - `02 桌面端优化结构`
  - `03 移动端与状态规则`

## Task 1: Load Figma workflows and resolve callable tools

**Files:**
- Read: `/Users/liuyixing/.codex/plugins/cache/openai-curated-remote/figma/2.0.16/skills/figma-create-new-file/SKILL.md`
- Read: `/Users/liuyixing/.codex/plugins/cache/openai-curated-remote/figma/2.0.16/skills/figma-use/SKILL.md`
- Read: `/Users/liuyixing/.codex/plugins/cache/openai-curated-remote/figma/2.0.16/skills/figma-generate-design/SKILL.md`
- Read: `/Users/liuyixing/.codex/plugins/cache/openai-curated-remote/figma/2.0.16/skills/figma-use/references/plugin-api-standalone.index.md`

- [ ] **Step 1: Read every required Figma skill completely**

Confirm the mandatory prerequisites for `create_new_file` and every `use_figma` call, including the exact `skillNames` value.

- [ ] **Step 2: Resolve the exact MCP schemas in one discovery call**

Discover `create_new_file`, `use_figma`, `get_screenshot`, `get_metadata`, and any image-upload or image-fill helper exposed by the installed Figma connector.

Expected: each needed tool has a callable schema; if image upload is unavailable, the plan must use the supported Figma image-import path documented by the connector rather than leaving the screenshot blank.

- [ ] **Step 3: Verify the reference screenshot before upload**

Open the exact local PNG and confirm it is the 3024 × 1612 student homepage screenshot with no crop, blank state, or wrong window.

Expected: the screenshot shows the left navigation, top search, today task, weekly learning chart, training calendar, roadshow card, AI score empty state, and current-actions empty state.

## Task 2: Create the Figma file and inspect its starting state

**Artifacts:**
- Create: Figma file `竞赛大脑 · 学生首页结构优化`
- Create: Figma page `学生首页优化`

- [ ] **Step 1: Create the new file**

Call `create_new_file` with the approved file name and capture the returned `fileKey` and URL.

Expected: a new editable Figma Design file is returned.

- [ ] **Step 2: Inspect existing pages, local components, variables, and styles**

Use a read-only `use_figma` call against the new file to return:

```js
return {
  pages: figma.root.children.map(page => ({ id: page.id, name: page.name })),
  localComponents: (await figma.getLocalComponentsAsync()).map(c => ({ id: c.id, name: c.name })),
  variableCollections: (await figma.variables.getLocalVariableCollectionsAsync()).map(c => ({ id: c.id, name: c.name })),
  textStyles: (await figma.getLocalTextStylesAsync()).map(s => ({ id: s.id, name: s.name })),
  effectStyles: (await figma.getLocalEffectStylesAsync()).map(s => ({ id: s.id, name: s.name }))
};
```

Expected: the file is empty or contains only the default page; record that existing-screen component discovery is not applicable when no existing screen exists.

- [ ] **Step 3: Rename the page and create the three top-level sections**

Create the sections at fixed positions:

```text
01 现状与审计          x=0,    y=0
02 桌面端优化结构      x=1800, y=0
03 移动端与状态规则  x=3500, y=0
```

Expected: all later frames are created directly inside their target section; no top-level orphan frames are created and reparented later.

## Task 3: Establish the OREP visual foundation and reusable components

**Artifacts:**
- Create local variables: `Color/*`, `Space/*`, `Radius/*`
- Create local components: `Card`, `Button`, `Status Tag`, `Meta Item`, `Calendar Day`, `Stage Step`, `Audit Note`

- [ ] **Step 1: Check Code Connect for the required components**

Run:

```bash
rg --files /Users/liuyixing/项目/OREP/frontend/user | rg '(BaseButton|StudentHome|Workspace).*\.figma\.(ts|tsx|js)$'
```

Expected: if no matching Code Connect files exist, record `Code Connect: none for required components` and continue to local-component creation.

- [ ] **Step 2: Check the new file for existing-screen instances**

Because Task 2 creates a new file, this step is expected to be N/A unless the connector inserted starter content. If starter content exists, inspect instances and record any authoritative component keys before creating local components.

- [ ] **Step 3: Create local variable collections**

Create and bind these exact foundations from the existing product tokens:

```text
Canvas        #F3F4F6
Surface       #FFFFFF
Ink           #12141A
Ink Secondary #2C3038
Muted         #6B7280
Faint         #9AA1AD
Line          rgba(28,26,22,0.09)
Orange 50     #FFF7F2
Orange 100    #FEE9DF
Orange 500    #E84A1C
Orange 700    #C43A12
Green         #0F9F6E
Blue          #3F63F3
Amber         #D98200
Red           #D83A45
Space         4, 8, 12, 16, 20, 24, 32, 40
Radius        8, 12, 16, 20, 999
```

Expected: variables exist in the new file and scene-node fills, spacing, and radii use bindings where the API supports them.

- [ ] **Step 4: Create reusable local components once**

Build component masters before placing screen instances:

```text
Card / Default
Button / Primary
Button / Secondary
Button / Text
Status Tag / Active
Status Tag / Neutral
Status Tag / Success
Meta Item / Default
Calendar Day / Today
Calendar Day / Future
Stage Step / Complete
Stage Step / Current
Stage Step / Locked
Audit Note / P0
Audit Note / P1
```

Expected: repeated screen elements are component instances, not copied one-off frames.

- [ ] **Step 5: Render the component foundation**

Call `get_screenshot` on the component area.

Expected: text is not clipped, primary button has one high-emphasis orange fill, secondary and text actions are visually weaker, and all component labels are readable.

## Task 4: Build `01 现状与审计`

**Artifacts:**
- Create frame: `当前学生首页`
- Create frame: `高优先级问题`

- [ ] **Step 1: Import the accepted PNG into Figma**

Place the 3024 × 1612 image proportionally inside a 1200px-wide frame without distortion.

Expected: the exact screenshot is visibly placed, not merely uploaded as an unused image resource.

- [ ] **Step 2: Add numbered overlays 1–5**

Place numbered markers on the screenshot at these semantic targets:

```text
1  顶部“查看今日任务”与中部今日任务重复
2  左中“本周学习时长 0 分”大卡
3  右下“当前没有待办”
4  左下“去练一场路演”高强度按钮
5  中下 AI 评分大面积空状态
```

- [ ] **Step 3: Add the corresponding audit-note instances**

Use these exact note titles:

```text
P0 · 同一任务三个入口
P0 · 今日有训练但显示“无待办”
P1 · 0 数据图表占用黄金位置
P1 · 未到路演阶段却提前强推路演
P1 · 大面积空状态稀释主任务
```

- [ ] **Step 4: Render and inspect the audit section**

Expected: screenshot is visible, markers point to the correct UI regions, and every marker has one matching note.

## Task 5: Build `02 桌面端优化结构`

**Artifacts:**
- Create frame: `学生首页 · Desktop`
- Size: 1440 × 900

- [ ] **Step 1: Build the existing desktop shell**

Create the left 72px navigation, 64px top bar, search field, notification/help icons, user area, and light-gray content canvas. Use symbols from an available icon library or Figma-native approved icons; do not draw custom SVG icons.

Expected: the shell preserves the current product family and does not introduce a new navigation model.

- [ ] **Step 2: Build the single primary-task card**

Use the exact content:

```text
应用攻坚队 · 训练第 1 天
今天只做一件事：确定项目问题与用户需求
用真实访谈和场景证据，讲清服务对象、核心问题与项目边界。
截止 7/22 22:00
必交 2 项
7 人协作
继续完成任务
先看课程
```

Expected: `继续完成任务` is the only filled orange CTA in the desktop frame.

- [ ] **Step 3: Build the training-rhythm card**

Show `距离备赛结束 20 天`, `第 1 周`, and seven compact calendar-day instances with 7/22 highlighted as today. Add a secondary `查看完整计划` action.

- [ ] **Step 4: Build the preparation-loop card**

Place four stage-step instances:

```text
准备内容   已完成
练一场路演   下一阶段
查看 AI 评分  待解锁
按反馈整改   待解锁
```

Use only neutral or text-level actions in this card.

- [ ] **Step 5: Build compact secondary information**

Create:

```text
其他团队待办：今日主任务之外暂无其他任务
本周学习：0 分 · 完成今日任务后开始记录
```

Expected: neither item uses an independent 300px-high empty card, and the zero-learning state does not show an empty chart.

- [ ] **Step 6: Render and inspect the desktop frame**

Expected:

```text
1440 × 900 frame is complete
one filled orange CTA
task title, deadline, required count, team count, and CTA are above the fold
no duplicate today-task entry
no contradictory no-todo message
no large AI-score empty card
```

## Task 6: Build `03 移动端与状态规则`

**Artifacts:**
- Create frame: `学生首页 · Mobile`
- Size: 390 × 844
- Create frame: `状态规则`

- [ ] **Step 1: Build the mobile shell**

Use a compact top bar and preserve the existing seven-item floating bottom navigation. At 390px, arrange the bottom navigation as the product currently does for widths up to 420px: four columns with wrapping.

- [ ] **Step 2: Build the mobile primary-task card first**

Use the same exact task content as the desktop version. Keep the task title, `截止 7/22 22:00`, `必交 2 项`, and the `继续完成任务` button visible before the bottom of the 844px viewport.

- [ ] **Step 3: Stack secondary cards in the approved order**

Use this exact order below the primary card:

```text
其他团队待办
训练日历
路演与 AI 评分闭环
学习数据
```

- [ ] **Step 4: Add the four state-rule cards**

Create concise rule cards for:

```text
有今日训练：今日训练是唯一主行动
无今日训练：过期团队任务 → 下一训练日 → 继续学习
无路演或评分：显示阶段和解锁条件
无其他待办：显示一行紧凑状态
```

- [ ] **Step 5: Render and inspect the mobile frame**

Expected:

```text
390 × 844 frame is complete
primary task title is not clipped
deadline and primary CTA are visible in the first viewport
bottom navigation does not cover the CTA
one filled orange CTA
tap targets are at least 44px high
```

## Task 7: Final visual QA and handoff

**Artifacts:**
- Save QA screenshots locally in `/Users/liuyixing/.codex/visualizations/2026/07/22/019f89d5-18f2-7063-9c65-f08ab60eac01/orep-student-home-figma/`

- [ ] **Step 1: Render every top-level section**

Capture `01 现状与审计`, `02 桌面端优化结构`, and `03 移动端与状态规则` separately.

- [ ] **Step 2: Inspect every saved screenshot**

Reject and repair any render that contains:

```text
blank or missing reference image
cropped task title
overlapping cards
orphan frames outside sections
more than one filled orange CTA per target frame
missing mobile bottom navigation
missing audit-note mapping
```

- [ ] **Step 3: Inspect file metadata**

Verify the page contains the three named sections, the desktop and mobile target frames, and the local component masters.

- [ ] **Step 4: Return the Figma URL and inline previews**

The final handoff must include:

```text
clickable Figma file URL
desktop frame preview
mobile frame preview
brief list of what changed
named evidence limit: static structure draft does not verify keyboard, screen reader, or production performance
```

## Execution notes

- The current workspace is not a Git repository, so commit steps cannot be executed. Do not initialize a repository solely for this artifact.
- No production code changes are authorized in this plan.
- Do not substitute a browser screenshot or local HTML mockup for the requested Figma artifact.
- If the Figma connector cannot create files or place the PNG, stop after exhausting the documented Figma path and report the exact missing capability.
