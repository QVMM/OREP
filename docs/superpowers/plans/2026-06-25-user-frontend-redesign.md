# User Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the user frontend pages for 首页、课程学习、考试系统、在线会议入口、项目团队 while preserving existing working business behavior, routes, API calls, permissions, dialogs, uploads, meeting entry, exam flows, and course playback.

**Architecture:** Keep the current Vue/Vite/Element Plus application, routing, stores, and page-level data logic. Add a small OREP UI layer for the new orange visual language, then update each target page template and styles around the existing methods and state. Meeting room `/meeting/:id` is intentionally left unchanged except for navigation compatibility.

**Tech Stack:** Vue 3 `<script setup>`, Vue Router, Pinia, Element Plus, existing `frontend/user/src/components/apple/*`, Vite, existing REST/WebSocket utilities.

---

## Implementation Principles

- Preserve existing routes in `frontend/user/src/router/index.js`.
- Preserve existing API calls and mutations unless a bug is discovered during integration.
- Preserve usable buttons and workflows: course progress, lesson playback, exam start/practice/take/wrong-book/favorites, online meeting create/join/history, project team task submission/review/file preview.
- Do not convert pages into static mockups. Every redesigned area must connect to the current data source or current fallback/demo data.
- Keep the orange style restrained: white surface, light warm background, black primary action, orange active/accent states.
- Use Chinese-only visible page labels. No English section eyebrow text.
- Keep `/meeting/:id` meeting room visual style intact.
- Verify after every page with `npm run build` and manual route checks.

---

## File Structure

### Shared UI Foundation

- Modify: `frontend/user/src/styles/apple-tokens.css`
  - Add orange-based tokens and refined neutral colors.
- Modify: `frontend/user/src/theme.css`
  - Align global background, text, borders, shadows.
- Modify: `frontend/user/src/components/apple/OrepTopNav.vue`
  - Keep navigation routes, update brand and active state style.
- Modify: `frontend/user/src/components/apple/OrepPageShell.vue`
  - Keep shell behavior, adjust layout width and background.
- Create: `frontend/user/src/components/orep-ui/OrepSectionHeader.vue`
  - Shared title, subtitle, right actions.
- Create: `frontend/user/src/components/orep-ui/OrepActionButton.vue`
  - Shared black/white/orange button patterns.
- Create: `frontend/user/src/components/orep-ui/OrepStatusPill.vue`
  - Shared small status chips.

### Homepage

- Modify: `frontend/user/src/views/Dashboard.vue`
- Reuse: `frontend/user/src/components/dashboard/HeroCarousel.vue`
- Reuse: `frontend/user/src/components/dashboard/TaskCard.vue`
- Reuse: `frontend/user/src/components/dashboard/RecentActivity.vue`

### Course Learning

- Modify: `frontend/user/src/views/CourseLearning.vue`
- Modify: `frontend/user/src/views/CourseLessonPlayer.vue`
- Create: `frontend/user/src/components/course/CourseCategoryRail.vue`
- Create: `frontend/user/src/components/course/CourseCard.vue`
- Create: `frontend/user/src/components/course/CourseChapterPanel.vue`

### Exam System

- Modify: `frontend/user/src/views/ExamSystem.vue`
- Modify: `frontend/user/src/views/ExamTaking.vue`
- Modify: `frontend/user/src/views/ExamPractice.vue`
- Modify: `frontend/user/src/views/ExamWrongBook.vue`
- Modify: `frontend/user/src/views/ExamFavorites.vue`
- Reuse: `frontend/user/src/components/exam/QuestionReviewDesk.vue`

### Online Meeting

- Modify: `frontend/user/src/views/OnlineMeeting.vue`
- Do not redesign: `frontend/user/src/views/MeetingRoom.vue`

### Project Team

- Modify: `frontend/user/src/views/ProjectTeam.vue`
- Reuse: `frontend/user/src/components/FilePreview.vue`
- Create: `frontend/user/src/components/project-team/TeamConsoleNav.vue`
- Create: `frontend/user/src/components/project-team/TeamConsoleHome.vue`
- Create: `frontend/user/src/components/project-team/TeamMaterialWorkspace.vue`
- Create: `frontend/user/src/components/project-team/TeamTaskDelivery.vue`
- Create: `frontend/user/src/components/project-team/TeamReviewWorkspace.vue`

---

## Task 1: Stabilize Shared Visual System

**Files:**
- Modify: `frontend/user/src/styles/apple-tokens.css`
- Modify: `frontend/user/src/theme.css`
- Modify: `frontend/user/src/components/apple/OrepTopNav.vue`
- Modify: `frontend/user/src/components/apple/OrepPageShell.vue`
- Create: `frontend/user/src/components/orep-ui/OrepSectionHeader.vue`
- Create: `frontend/user/src/components/orep-ui/OrepActionButton.vue`
- Create: `frontend/user/src/components/orep-ui/OrepStatusPill.vue`

- [ ] **Step 1: Add shared orange tokens**

Add token aliases in `frontend/user/src/styles/apple-tokens.css`:

```css
:root {
  --orep-brand: oklch(66% 0.19 43);
  --orep-brand-soft: oklch(96% 0.04 55);
  --orep-brand-wash: oklch(98.4% 0.025 55);
  --orep-paper: oklch(99.2% 0.006 55);
  --orep-surface: oklch(97.4% 0.008 55);
  --orep-ink: oklch(17% 0.012 45);
  --orep-muted: oklch(50% 0.018 55);
  --orep-line: oklch(91.5% 0.01 55);
  --orep-line-strong: oklch(86.5% 0.016 55);
  --orep-shadow-soft: 0 20px 58px oklch(20% 0.015 45 / 0.06);
}
```

- [ ] **Step 2: Update global background without changing app routing**

In `frontend/user/src/theme.css`, map existing page variables to the new restrained warm style. Keep existing variable names that current pages use.

- [ ] **Step 3: Create shared OREP UI components**

Create the three small components under `frontend/user/src/components/orep-ui/`. Keep them presentation-only with props and slots. They must not fetch data.

- [ ] **Step 4: Update the top navigation**

In `frontend/user/src/components/apple/OrepTopNav.vue`, preserve existing route link definitions and dropdown behavior. Replace only visual structure and labels to match the confirmed top navigation style.

- [ ] **Step 5: Build check**

Run:

```bash
cd frontend/user
npm run build
```

Expected: Vite build succeeds and no routes are removed.

---

## Task 2: Implement Confirmed Homepage UI

**Files:**
- Modify: `frontend/user/src/views/Dashboard.vue`
- Modify only if needed: `frontend/user/src/components/dashboard/HeroCarousel.vue`
- Modify only if needed: `frontend/user/src/components/dashboard/TaskCard.vue`

- [ ] **Step 1: Map existing homepage data to the confirmed design**

Use the confirmed HTML reference:

```text
/Users/liuyixing/项目/OREP/.superpowers/brainstorm/7346-1782323770/content/homepage-final-v1.html
```

Keep the current Dashboard data sources and navigation handlers. Replace the template with the approved homepage sections:

- carousel / hero operational banner
- next recommendation
- progress / weekly plan / team collaboration cards
- 备赛地图 cards with bottom-left summary and bottom-right element

- [ ] **Step 2: Preserve homepage click behavior**

Keep existing buttons routing to course, exam, script, meeting, statistics, and project team routes. Any old method used by a button must remain wired to the equivalent new button.

- [ ] **Step 3: Remove English visible labels**

Replace labels such as `Today's Path`, `Roadshow Flow`, or `OREP Agent` with Chinese labels.

- [ ] **Step 4: Verify homepage manually**

Run dev server:

```bash
cd frontend/user
npm run dev
```

Open `/`. Verify carousel, route buttons, cards, and responsive layout.

- [ ] **Step 5: Build check**

Run:

```bash
cd frontend/user
npm run build
```

Expected: build succeeds.

---

## Task 3: Implement Course Learning List, Detail, Chapter, and Player

**Files:**
- Modify: `frontend/user/src/views/CourseLearning.vue`
- Modify: `frontend/user/src/views/CourseLessonPlayer.vue`
- Create: `frontend/user/src/components/course/CourseCategoryRail.vue`
- Create: `frontend/user/src/components/course/CourseCard.vue`
- Create: `frontend/user/src/components/course/CourseChapterPanel.vue`

- [ ] **Step 1: Preserve current course data and progress logic**

Before editing, identify existing course arrays, API calls, progress fields, route pushes, and lesson completion behavior in `CourseLearning.vue` and `CourseLessonPlayer.vue`. Keep those names and methods unless extracting them into props.

- [ ] **Step 2: Extract course category rail**

Create `CourseCategoryRail.vue` to support many categories. Use vertical list or collapsible groups depending on current category count. The component receives:

```js
defineProps({
  categories: { type: Array, required: true },
  activeCategory: { type: [String, Number], required: true }
})

defineEmits(['select'])
```

- [ ] **Step 3: Extract course card**

Create `CourseCard.vue` with image, title, progress bar, chapter count, duration, and action. It emits `open`.

- [ ] **Step 4: Update course list page**

Apply the approved course page design. Keep existing search/filter/course click behavior. Course cards must include images with fallback visual blocks when no image URL exists.

- [ ] **Step 5: Update course detail and chapter area**

Use `CourseChapterPanel.vue` for chapter list, lesson state, duration, progress, and current lesson route. Preserve route:

```text
/course-learning/:courseId/lesson/:lessonId
```

- [ ] **Step 6: Update player page**

In `CourseLessonPlayer.vue`, remove any prominent “标记完成” manual action. Use passive completion copy:

```text
播放达到 90% 后自动完成本节
```

Keep practice, next lesson, playback, and progress behavior.

- [ ] **Step 7: Manual verification**

Open:

```text
/course-learning
/course-learning/1/lesson/1
```

Verify category switching, course entry, chapter entry, playback page, progress display, and next lesson action.

- [ ] **Step 8: Build check**

Run:

```bash
cd frontend/user
npm run build
```

Expected: build succeeds.

---

## Task 4: Implement Exam System UI While Preserving Exam Workflows

**Files:**
- Modify: `frontend/user/src/views/ExamSystem.vue`
- Modify: `frontend/user/src/views/ExamTaking.vue`
- Modify: `frontend/user/src/views/ExamPractice.vue`
- Modify: `frontend/user/src/views/ExamWrongBook.vue`
- Modify: `frontend/user/src/views/ExamFavorites.vue`
- Reuse: `frontend/user/src/components/exam/QuestionReviewDesk.vue`

- [ ] **Step 1: Apply selected exam system hero**

Use the selected reference:

```text
/Users/liuyixing/项目/OREP/.superpowers/brainstorm/32278-1782327352/content/exam-hero-balanced-v2-layout-refined.html
```

Do not use trend charts. Keep balanced right-side metrics: 最近正确率、最近得分、待复盘、高频错题、收藏题、薄弱点标签.

- [ ] **Step 2: Preserve existing exam entry actions**

Keep routes and handlers for:

```text
/exam-system/take/:paperId
/exam-system/practice/:source
/exam-system/wrong-book
/exam-system/favorites
```

- [ ] **Step 3: Update answer-taking page**

In `ExamTaking.vue`, keep timer, autosave, submit, question switching, and result route behavior. Redesign only the shell, question card, answer area, question navigation, marked status, and submit affordance.

- [ ] **Step 4: Update practice page**

In `ExamPractice.vue`, keep answer-after-analysis behavior. Make practice mode visually distinct from simulation mode through copy and status, not through a different route model.

- [ ] **Step 5: Expand wrong-book and favorites pages**

Current files are short. Replace placeholder-like views with functional list/detail shells that reuse existing route/data assumptions and `QuestionReviewDesk.vue` where appropriate.

- [ ] **Step 6: Manual verification**

Open:

```text
/exam-system
/exam-system/wrong-book
/exam-system/favorites
/exam-system/practice/wrong
```

Start at least one available paper from `/exam-system` and verify answering, marking, submitting, and navigation.

- [ ] **Step 7: Build check**

Run:

```bash
cd frontend/user
npm run build
```

Expected: build succeeds.

---

## Task 5: Implement Online Meeting Entry Only

**Files:**
- Modify: `frontend/user/src/views/OnlineMeeting.vue`
- Do not modify for redesign: `frontend/user/src/views/MeetingRoom.vue`

- [ ] **Step 1: Preserve create and join meeting behavior**

Before replacing template, identify existing create meeting, join meeting, meeting list, history, validation, and error methods in `OnlineMeeting.vue`. Keep those methods and data calls.

- [ ] **Step 2: Apply confirmed online meeting entry UI**

Use the saved reference:

```text
/Users/liuyixing/项目/OREP/.superpowers/brainstorm/32278-1782327352/content/online-meeting-entry-design.html
```

Only redesign `/online-meeting`.

- [ ] **Step 3: Preserve meeting room**

Confirm `/meeting/:id` still renders through `MeetingRoom.vue` with the existing immersive shell behavior from `App.vue`.

- [ ] **Step 4: Manual verification**

Open:

```text
/online-meeting
```

Verify create meeting, join meeting, recent meeting/history entry, and route transition to `/meeting/:id`.

- [ ] **Step 5: Build check**

Run:

```bash
cd frontend/user
npm run build
```

Expected: build succeeds.

---

## Task 6: Implement Project Team Console With Functional Work Areas

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`
- Reuse: `frontend/user/src/components/FilePreview.vue`
- Create: `frontend/user/src/components/project-team/TeamConsoleNav.vue`
- Create: `frontend/user/src/components/project-team/TeamConsoleHome.vue`
- Create: `frontend/user/src/components/project-team/TeamMaterialWorkspace.vue`
- Create: `frontend/user/src/components/project-team/TeamTaskDelivery.vue`
- Create: `frontend/user/src/components/project-team/TeamReviewWorkspace.vue`

- [ ] **Step 1: Preserve existing ProjectTeam business logic**

`ProjectTeam.vue` is large and already handles teams, stages, tasks, delivery review, roadshow memory, teacher observation, members, ability evidence, permissions, dialogs, uploads, preview, download, and submission. Do not delete existing methods. Move only display chunks into child components with explicit props and emits.

- [ ] **Step 2: Create console navigation**

`TeamConsoleNav.vue` receives:

```js
defineProps({
  team: { type: Object, default: null },
  activeTab: { type: String, required: true },
  counts: { type: Object, required: true }
})

defineEmits(['change'])
```

Tabs:

```js
['overview', 'materials', 'tasks', 'review']
```

- [ ] **Step 3: Create console home**

`TeamConsoleHome.vue` shows the default control-console home: project summary, primary actions, next rehearsal, current focus, teacher comments, progress, material completeness, pending versions, review issues, stages, and today priorities. It emits existing parent actions such as create task, invite member, enter materials.

- [ ] **Step 4: Create material workspace**

`TeamMaterialWorkspace.vue` shows files, PPT, scripts, PDF, video/materials, preview, collaboration state, autosave status, version history, and comments. It reuses parent methods for preview/download/upload and `FilePreview.vue` for previewable files.

- [ ] **Step 5: Create task delivery workspace**

`TeamTaskDelivery.vue` wraps existing task list, submission form, selected file upload, delivery status, review actions, and assignment entry. Existing task submit/review methods stay in parent and are passed down.

- [ ] **Step 6: Create review workspace**

`TeamReviewWorkspace.vue` wraps roadshow score, issue list, AI generated improvement tasks, evidence links, and next practice actions. Keep existing roadshow/review data and methods.

- [ ] **Step 7: Replace ProjectTeam template with console layout**

In `ProjectTeam.vue`, keep state and methods, replace the top-level template with:

```vue
<section class="team-console">
  <TeamConsoleNav
    :team="team"
    :active-tab="activeTeamTab"
    :counts="teamConsoleCounts"
    @change="activeTeamTab = $event"
  />
  <TeamConsoleHome v-if="activeTeamTab === 'overview'" />
  <TeamMaterialWorkspace v-else-if="activeTeamTab === 'materials'" />
  <TeamTaskDelivery v-else-if="activeTeamTab === 'tasks'" />
  <TeamReviewWorkspace v-else />
</section>
```

Use the actual props and emits needed by the preserved parent methods when implementing.

- [ ] **Step 8: Manual verification**

Open:

```text
/project-team
```

Verify team switching, stage display, task submit, file upload, file preview, download, delivery review, task assignment, roadshow review, member and permission paths that remain present.

- [ ] **Step 9: Build check**

Run:

```bash
cd frontend/user
npm run build
```

Expected: build succeeds.

---

## Task 7: Full Flow Regression

**Files:**
- Modify only if a regression is found in target files.

- [ ] **Step 1: Run production build**

Run:

```bash
cd frontend/user
npm run build
```

Expected: build succeeds.

- [ ] **Step 2: Start dev server**

Run:

```bash
cd frontend/user
npm run dev
```

- [ ] **Step 3: Manual route checklist**

Verify:

```text
/
/course-learning
/course-learning/1/lesson/1
/exam-system
/exam-system/wrong-book
/exam-system/favorites
/online-meeting
/project-team
```

- [ ] **Step 4: Preserve meeting room**

Enter or navigate to a real `/meeting/:id` route and confirm the current meeting-room style and behavior are not replaced by the new entry-page UI.

- [ ] **Step 5: Check Chinese-only visible headings**

Scan target pages in browser and remove English section labels from visible UI.

- [ ] **Step 6: Responsive smoke test**

Use browser device widths around 1440px, 1024px, and 390px. Verify text does not overlap, navigation remains accessible, and card/button text fits.

---

## Self-Review

- Spec coverage: Covers 首页、课程学习、考试系统、在线会议入口、项目团队.
- Function preservation: Each page task includes explicit preservation of routes, methods, API calls, and current workflows.
- Scope control: `/meeting/:id` is excluded from redesign except route compatibility.
- Risk: `ProjectTeam.vue` and `OnlineMeeting.vue` are large files. The plan mitigates this by extracting only presentation components and keeping parent data/methods.
- No placeholders: The plan names exact target files, saved mockup references, route checks, and build commands.
