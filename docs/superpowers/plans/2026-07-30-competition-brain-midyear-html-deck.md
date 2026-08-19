# Competition Brain Midyear HTML Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, offline-capable 15-slide HTML presentation for a 30-minute company-wide midyear report about the Competition Brain project.

**Architecture:** The deliverable is a static, dependency-free HTML presentation. Slide copy and speaker notes live in semantic HTML, visual styling is isolated in one CSS file, and navigation/presenter features live in one JavaScript file. Local product screenshots are copied into the output folder so the deck remains portable.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript, Node.js built-in test runner, local browser visual QA.

---

## File Structure

- Create: `outputs/competition-brain-midyear-2026/index.html` — semantic slide content, notes, sources, controls.
- Create: `outputs/competition-brain-midyear-2026/assets/deck.css` — 16:9 canvas, typography, layouts, motion, print rules.
- Create: `outputs/competition-brain-midyear-2026/assets/deck.js` — navigation, overview, notes, fullscreen, progress, URL state.
- Create: `outputs/competition-brain-midyear-2026/assets/images/` — selected local product screenshots.
- Create: `outputs/competition-brain-midyear-2026/tests/deck.test.mjs` — structural, wording, accessibility and source checks.
- Create: `outputs/competition-brain-midyear-2026/README.txt` — concise controls and offline usage.

The workspace root is not a Git repository. Commit steps are intentionally omitted; no repository will be initialized.

### Task 1: Create the failing deck contract tests

**Files:**
- Create: `outputs/competition-brain-midyear-2026/tests/deck.test.mjs`
- Test: `outputs/competition-brain-midyear-2026/tests/deck.test.mjs`

- [ ] **Step 1: Write the failing structural tests**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");

async function read(relativePath) {
  return readFile(resolve(root, relativePath), "utf8");
}

test("deck contains exactly 15 semantic slides", async () => {
  const html = await read("index.html");
  assert.equal((html.match(/<section class="slide\b/g) || []).length, 15);
  assert.match(html, /<main id="deck"/);
});

test("deck avoids forbidden employment timing and AI-flavored phrases", async () => {
  const html = await read("index.html");
  for (const phrase of ["2 月入职", "两个月", "1-N", "持续迭代第二个", "赋能", "生态闭环"]) {
    assert.equal(html.includes(phrase), false, `forbidden phrase: ${phrase}`);
  }
});

test("policy claims retain authoritative sources", async () => {
  const html = await read("index.html");
  assert.match(html, /教育强国建设规划纲要/);
  assert.match(html, /加快推进教育数字化/);
  assert.match(html, /2025年世界职业院校技能大赛实施方案/);
  assert.match(html, /https:\/\/www\.moe\.gov\.cn\//);
});

test("navigation script exposes required controls", async () => {
  const js = await read("assets/deck.js");
  for (const token of ["ArrowRight", "ArrowLeft", "toggleOverview", "toggleNotes", "toggleFullscreen"]) {
    assert.match(js, new RegExp(token));
  }
});

test("motion and print accessibility are present", async () => {
  const css = await read("assets/deck.css");
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /@media print/);
  assert.match(css, /:focus-visible/);
});
```

- [ ] **Step 2: Run the tests and verify the expected failure**

Run:

```bash
node --test outputs/competition-brain-midyear-2026/tests/deck.test.mjs
```

Expected: FAIL with `ENOENT` for `index.html`.

### Task 2: Build the semantic presentation content

**Files:**
- Create: `outputs/competition-brain-midyear-2026/index.html`
- Test: `outputs/competition-brain-midyear-2026/tests/deck.test.mjs`

- [ ] **Step 1: Create the document shell and 15 slide sections**

Use this exact outer structure:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#f4efe5">
  <title>竞赛大脑｜2026 年中工作汇报</title>
  <link rel="stylesheet" href="assets/deck.css">
</head>
<body>
  <a class="skip-link" href="#deck">跳到演示内容</a>
  <main id="deck" aria-live="polite">
    <!-- exactly 15 <section class="slide"> elements -->
  </main>
  <div class="deck-progress" aria-hidden="true"><i id="progressBar"></i></div>
  <div class="deck-counter"><span id="currentSlide">01</span><span>/</span><span>15</span></div>
  <nav class="deck-controls" aria-label="演示控制">
    <button type="button" data-action="prev" aria-label="上一页">←</button>
    <button type="button" data-action="overview" aria-label="查看全部页面">O</button>
    <button type="button" data-action="notes" aria-label="查看讲者备注">N</button>
    <button type="button" data-action="fullscreen" aria-label="进入全屏">F</button>
    <button type="button" data-action="next" aria-label="下一页">→</button>
  </nav>
  <aside id="notesPanel" class="notes-panel" aria-label="讲者备注" hidden></aside>
  <script src="assets/deck.js"></script>
</body>
</html>
```

- [ ] **Step 2: Add the approved audience-facing copy**

The 15 slide titles must be:

```text
01 竞赛大脑｜上半年进展与下半年计划
02 我这半年主要做了一件事
03 我们要解决的，不只是开一场线上会议
04 政策方向很明确：职业教育要更贴近产业，也要加快数字化
05 比赛是入口，真正的价值在平时训练
06 上半年先把产品框架搭起来
07 目前已经形成一条完整的路演训练主线
08 评分规则已经覆盖 42 个赛道
09 AI 评分不能只给一个分，还要把依据摆出来
10 产品能力已经不只是一张评分报告
11 现在的真实状态：能跑起来，但还需要真实使用来检验
12 做出来只是第一步，下一步是把它做实
13 下半年先抓四件具体的事
14 分三个阶段推进，每一步都要有结果
15 上半年把框架搭出来，下半年把产品做扎实
```

Slide 02 must say only:

```html
<p class="lead">上半年，我的主要工作是牵头竞赛大脑。</p>
<ul class="clean-list">
  <li>梳理产品到底要解决什么问题</li>
  <li>推进核心功能和系统链路落地</li>
  <li>把评分、证据和整改这条主线逐步做清楚</li>
</ul>
```

Slide 12 must use this plain-language transition:

```html
<blockquote>
  上半年先把产品做出来。下半年更重要的是把它真正用起来：哪里不好用就找原因，改完要验证；评分准不准要有真实案例支撑；模型要不要换，也要看它在竞赛场景里到底好不好用。
</blockquote>
```

- [ ] **Step 3: Add speaker notes and sources**

Every slide gets a hidden `<template class="speaker-notes">`. Policy slide notes must include:

```html
<p><strong>[Sources]</strong></p>
<ul>
  <li><a href="https://www.moe.gov.cn/jyb_xxgk/moe_1777/moe_1778/202501/t20250119_1176193.html">《教育强国建设规划纲要（2024—2035年）》</a></li>
  <li><a href="https://www.moe.gov.cn/srcsite/A01/s7048/202504/t20250416_1187476.html">《关于加快推进教育数字化的意见》</a></li>
  <li><a href="https://www.moe.gov.cn/srcsite/A07/s7055/202506/t20250617_1194543.html">《2025年世界职业院校技能大赛实施方案》</a></li>
</ul>
```

- [ ] **Step 4: Run the content tests**

Run:

```bash
node --test outputs/competition-brain-midyear-2026/tests/deck.test.mjs
```

Expected: content tests pass; CSS and JavaScript tests still fail because their files do not exist.

### Task 3: Copy and verify real product screenshots

**Files:**
- Create: `outputs/competition-brain-midyear-2026/assets/images/dashboard.png`
- Create: `outputs/competition-brain-midyear-2026/assets/images/meeting.png`
- Create: `outputs/competition-brain-midyear-2026/assets/images/score-overview.png`
- Create: `outputs/competition-brain-midyear-2026/assets/images/score-evidence.png`
- Create: `outputs/competition-brain-midyear-2026/assets/images/score-actions.png`
- Create: `outputs/competition-brain-midyear-2026/assets/images/project-team.png`

- [ ] **Step 1: Copy the selected workspace screenshots**

Run:

```bash
mkdir -p outputs/competition-brain-midyear-2026/assets/images
cp outputs/orep-user-ui-redesign-v2-20260701/screens/02-dashboard-reference-grade.png outputs/competition-brain-midyear-2026/assets/images/dashboard.png
cp outputs/orep-user-ui-redesign-v2-20260701/screens/12-online-meeting.png outputs/competition-brain-midyear-2026/assets/images/meeting.png
cp outputs/orep-user-ui-redesign-v2-20260701/screens/19-ai-report-overview.png outputs/competition-brain-midyear-2026/assets/images/score-overview.png
cp outputs/orep-user-ui-redesign-v2-20260701/screens/21-ai-report-evidence.png outputs/competition-brain-midyear-2026/assets/images/score-evidence.png
cp outputs/orep-user-ui-redesign-v2-20260701/screens/24-ai-report-actions.png outputs/competition-brain-midyear-2026/assets/images/score-actions.png
cp outputs/orep-user-ui-redesign-v2-20260701/screens/33-project-team.png outputs/competition-brain-midyear-2026/assets/images/project-team.png
```

- [ ] **Step 2: Verify every asset is non-empty**

Run:

```bash
find outputs/competition-brain-midyear-2026/assets/images -type f -size +10k -print
```

Expected: six image paths.

### Task 4: Implement the warm strategic visual system

**Files:**
- Create: `outputs/competition-brain-midyear-2026/assets/deck.css`
- Test: `outputs/competition-brain-midyear-2026/tests/deck.test.mjs`

- [ ] **Step 1: Define the design tokens and slide canvas**

Start with:

```css
:root {
  --paper: #f4efe5;
  --paper-2: #fbf8f1;
  --ink: #142237;
  --muted: #66707d;
  --line: rgba(20, 34, 55, 0.16);
  --copper: #a96f32;
  --copper-soft: #d9b98f;
  --deep: #0c1d34;
  --ease: cubic-bezier(.22, .8, .2, 1);
}

* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; background: #111823; color: var(--ink); }
body { overflow: hidden; font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; }
.slide {
  position: absolute;
  inset: 50% auto auto 50%;
  width: min(100vw, calc(100vh * 16 / 9));
  height: min(100vh, calc(100vw * 9 / 16));
  transform: translate(-50%, -50%);
  padding: 6.6% 7.2%;
  background: var(--paper);
  opacity: 0;
  visibility: hidden;
  overflow: hidden;
}
.slide.is-active { opacity: 1; visibility: visible; }
```

- [ ] **Step 2: Add varied presentation layouts**

Implement these layout classes:

```text
cover
statement
split
policy-rail
journey
timeline
evidence
gallery
honest-status
roadmap
closing
```

Each layout must keep at least 7% left/right margins, use one dominant composition, and avoid dashboard-like card grids.

- [ ] **Step 3: Add accessible motion and print rules**

Include:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    transition-duration: .01ms !important;
  }
}

@media print {
  @page { size: 13.333in 7.5in; margin: 0; }
  body { overflow: visible; background: #fff; }
  .slide {
    position: relative;
    inset: auto;
    width: 13.333in;
    height: 7.5in;
    transform: none;
    opacity: 1;
    visibility: visible;
    break-after: page;
  }
  .deck-controls, .deck-progress, .deck-counter, .notes-panel { display: none !important; }
}

button:focus-visible, a:focus-visible {
  outline: 3px solid var(--copper);
  outline-offset: 3px;
}
```

- [ ] **Step 4: Run the CSS contract tests**

Run:

```bash
node --test outputs/competition-brain-midyear-2026/tests/deck.test.mjs
```

Expected: all tests pass except the navigation script test.

### Task 5: Implement navigation and presenter features

**Files:**
- Create: `outputs/competition-brain-midyear-2026/assets/deck.js`
- Test: `outputs/competition-brain-midyear-2026/tests/deck.test.mjs`

- [ ] **Step 1: Implement stateful slide navigation**

Use:

```js
const slides = [...document.querySelectorAll(".slide")];
let current = Math.max(0, Math.min(slides.length - 1, Number(location.hash.slice(1)) - 1 || 0));

function showSlide(index) {
  current = Math.max(0, Math.min(slides.length - 1, index));
  slides.forEach((slide, i) => {
    slide.classList.toggle("is-active", i === current);
    slide.setAttribute("aria-hidden", i === current ? "false" : "true");
  });
  document.querySelector("#currentSlide").textContent = String(current + 1).padStart(2, "0");
  document.querySelector("#progressBar").style.width = `${((current + 1) / slides.length) * 100}%`;
  history.replaceState(null, "", `#${current + 1}`);
}
```

- [ ] **Step 2: Implement required controls**

Implement named functions:

```js
function toggleOverview() {
  document.body.classList.toggle("is-overview");
  document.querySelector("#notesPanel").hidden = true;
  document.body.classList.remove("show-notes");
}

function toggleNotes() {
  const panel = document.querySelector("#notesPanel");
  const template = slides[current].querySelector("template.speaker-notes");
  panel.replaceChildren(template ? template.content.cloneNode(true) : document.createTextNode("本页没有讲者备注。"));
  panel.hidden = !panel.hidden;
  document.body.classList.toggle("show-notes", !panel.hidden);
}

async function toggleFullscreen() {
  if (!document.fullscreenElement) {
    await document.documentElement.requestFullscreen();
  } else {
    await document.exitFullscreen();
  }
}
```

Bind:

```text
ArrowRight, ArrowDown, PageDown, Space → next
ArrowLeft, ArrowUp, PageUp → previous
Home → first
End → last
O → overview
N → notes
F → fullscreen
Escape → close overview or notes
```

- [ ] **Step 3: Populate speaker notes safely**

When notes open, clone the active slide's `template.speaker-notes` content into `#notesPanel`; do not use external data or network calls.

- [ ] **Step 4: Run all contract tests**

Run:

```bash
node --test outputs/competition-brain-midyear-2026/tests/deck.test.mjs
```

Expected: 5 tests pass, 0 fail.

### Task 6: Add the usage handoff

**Files:**
- Create: `outputs/competition-brain-midyear-2026/README.txt`

- [ ] **Step 1: Write the concise usage guide**

```text
竞赛大脑 2026 年中工作汇报

打开方式：
1. 直接双击 index.html，或使用浏览器打开。
2. 建议使用 Chrome、Edge 或 Safari，并进入全屏。

操作：
← / → / 空格：翻页
O：查看全部页面
N：查看讲者备注
F：进入或退出全屏
Esc：关闭概览或备注

导出 PDF：
浏览器打印 → 横向 → 关闭页眉页脚 → 保存为 PDF
```

- [ ] **Step 2: Verify the deliverable is self-contained**

Run:

```bash
find outputs/competition-brain-midyear-2026 -type f -maxdepth 4 -print | sort
```

Expected: HTML, CSS, JavaScript, README, tests and six local images; no remote runtime dependency.

### Task 7: Perform browser and visual QA

**Files:**
- Modify as needed: `outputs/competition-brain-midyear-2026/index.html`
- Modify as needed: `outputs/competition-brain-midyear-2026/assets/deck.css`
- Modify as needed: `outputs/competition-brain-midyear-2026/assets/deck.js`

- [ ] **Step 1: Serve the deck locally**

Run:

```bash
python3 -m http.server 4173 --directory outputs/competition-brain-midyear-2026
```

Expected: local server at `http://127.0.0.1:4173/`.

- [ ] **Step 2: Inspect all 15 slides at 1440×810**

Check:

```text
No clipped titles
No body text below the slide boundary
No unintended overlaps
All six screenshots load and crop cleanly
Policy source links appear only in notes/footer
Navigation, overview, notes and fullscreen controls work
```

- [ ] **Step 3: Verify responsive fallback at 1024×768 and 390×844**

Expected: the slide scales without horizontal scrolling; controls remain reachable; text remains legible.

- [ ] **Step 4: Re-run tests after visual fixes**

Run:

```bash
node --test outputs/competition-brain-midyear-2026/tests/deck.test.mjs
```

Expected: 5 tests pass, 0 fail.

- [ ] **Step 5: Search final output for prohibited wording and placeholders**

Run:

```bash
rg -n "2 月入职|两个月|1-N|持续迭代第二个|TBD|TODO|待补|占位|赋能|生态闭环" outputs/competition-brain-midyear-2026
```

Expected: no matches.
