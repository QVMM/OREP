# Overview Video Process Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the overview evidence snippet with a video process audit that shows stages, roles, performance, scoring-point tags, and risk/deduction ownership without duplicating five-dimension scoring details.

**Architecture:** Keep the change inside `AiScoreReportOverview.vue` and derive process-audit view models from existing report context. Build stage rows from business-stage signals first, then time fallback, and use visual frames as the primary media surface. Use route navigation to connect scoring-point tags to the dimensions page and independent risks to evidence/actions pages.

**Tech Stack:** Vue 3 Composition API, Vue Router, existing `useAiScoreReportContext`, Vite build verification.

---

## File Structure

- Modify `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`: replace the current evidence section template, add process-audit computed view models, stage expand/select state, navigation helpers, and scoped CSS.
- No new component in the first pass. The module is still local to overview. Extract later only if another page needs the same process audit.
- No backend change required for this pass. Use current report data: `evidenceFrames`, `fusion`, `video`, `speaker_scores`, `dimensions`, `priorities`, `structuredEvidenceAnchors`, and ASR.

## Task 1: Build Process-Audit View Models

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`

- [ ] **Step 1: Add state for selected stage and expanded stages**

Add after existing `selectedEvidenceId`:

```js
const selectedStageId = ref('')
const expandedStageIds = ref([])
```

- [ ] **Step 2: Add stage-level computed models**

Add computed models that produce:

```js
const processStages = computed(() => buildProcessStages())
const selectedStage = computed(() => processStages.value.find(stage => stage.id === selectedStageId.value) || processStages.value[0] || null)
const selectedStageItems = computed(() => selectedStage.value?.items || [])
const selectedProcessItem = computed(() => selectedStageItems.value.find(item => item.id === selectedEvidenceId.value) || selectedStageItems.value[0] || null)
```

The selected process item replaces `selectedEvidence` as the primary view model.

- [ ] **Step 3: Build stages from business signals first**

Implement `buildProcessStages()` so it groups items by stage name and time:

```js
function buildProcessStages() {
  const items = buildProcessItems()
  if (!items.length) return []
  const groups = new Map()
  items.forEach(item => {
    const key = item.stageKey || fallbackStageKey(item.seconds)
    if (!groups.has(key)) groups.set(key, stageShell(key, item))
    groups.get(key).items.push(item)
  })
  return [...groups.values()].map(finalizeStage).sort((a, b) => a.startSeconds - b.startSeconds)
}
```

- [ ] **Step 4: Implement process item sources**

Use sources in this order:

```js
function buildProcessItems() {
  const items = [
    ...itemsFromStructuredAnchors(),
    ...itemsFromVisualDescriptions(),
    ...itemsFromCollaborationDetections(),
    ...itemsFromSpeakerQuotes(),
    ...itemsFromDimensionRisks(),
    ...itemsFromFrames()
  ]
  return dedupeProcessItems(items).sort((a, b) => a.seconds - b.seconds)
}
```

Each item must include:

```js
{
  id,
  seconds,
  time,
  type,
  stageName,
  stageKey,
  summary,
  roles,
  performanceTags,
  scoringTags,
  riskTags,
  frame,
  image
}
```

- [ ] **Step 5: Add scoring tag model**

Scoring tags are short navigation labels:

```js
{
  label: '技能水平 / 操作规范性',
  dimensionKey: 'skill_level',
  itemKey: 'operation_norms',
  kind: 'scoring'
}
```

If item-level key is unavailable, set only `dimensionKey`.

- [ ] **Step 6: Add risk tag model**

Risk tags distinguish scoring deductions from independent risks:

```js
{
  label: '操作规范性扣分',
  type: 'scoring-deduction',
  dimensionKey: 'skill_level',
  itemKey: 'operation_norms'
}
```

```js
{
  label: '证据链不足',
  type: 'independent-risk',
  target: 'evidence'
}
```

## Task 2: Replace Evidence Section Template

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`

- [ ] **Step 1: Rename section title**

Change:

```vue
<h2>证据片段 <span>（AI 已定位关键片段）</span></h2>
```

to:

```vue
<h2>视频过程审计 <span>（按时间定位角色、表现与风险）</span></h2>
```

- [ ] **Step 2: Replace right-side clip card**

Render selected process item fields:

```vue
<div class="audit-card">
  <header>
    <strong>{{ selectedProcessItem?.stageName || '未识别阶段' }}</strong>
    <b>{{ selectedProcessItem?.time || '-' }}</b>
  </header>
  <p>{{ selectedProcessItem?.summary || '暂无片段摘要。' }}</p>
  <dl>
    <div><dt>参与角色</dt><dd><button v-for="role in selectedProcessItem?.roles || []" :key="role">{{ role }}</button></dd></div>
    <div><dt>综合表现</dt><dd><span v-for="tag in selectedProcessItem?.performanceTags || []" :key="tag">{{ tag }}</span></dd></div>
  </dl>
  <div class="audit-tags">
    <button v-for="tag in selectedProcessItem?.scoringTags || []" :key="tag.label" type="button" @click="openScoringTag(tag)">{{ tag.label }} ↗</button>
    <button v-for="tag in selectedProcessItem?.riskTags || []" :key="tag.label" type="button" :class="tag.type" @click="openRiskTag(tag)">{{ tag.label }} ↗</button>
  </div>
</div>
```

- [ ] **Step 3: Replace bottom evidence table with stage list**

Render stages:

```vue
<div class="stage-list">
  <button v-for="stage in processStages" :key="stage.id" type="button" class="stage-row" @click="toggleStage(stage)">
    <b>{{ stage.timeRange }}</b>
    <span>{{ stage.title }}</span>
    <em>{{ stage.roleSummary }}</em>
    <strong>{{ stage.scoringCount }} 评分点</strong>
    <i>{{ stage.riskCount }} 风险 / {{ stage.deductionCount }} 扣分</i>
  </button>
  <div v-if="isStageExpanded(stage)" class="stage-items">
    <button v-for="item in stage.items" :key="item.id" type="button" @click="selectProcessItem(item, stage)">
      <b>{{ item.time }}</b>
      <span>{{ item.type }}</span>
      <p>{{ item.summary }}</p>
      <em>{{ item.roles.join('、') || '未识别角色' }}</em>
      <strong>{{ item.scoringTags.map(tag => tag.label).join('、') || '未命中评分点' }}</strong>
    </button>
  </div>
</div>
```

- [ ] **Step 4: Keep detail link**

Keep:

```vue
<RouterLink :to="report.sectionPath('evidence')" class="more-link">查看完整证据链 ›</RouterLink>
```

## Task 3: Navigation and Selection Behavior

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`

- [ ] **Step 1: Sync default selected stage**

Watch stages:

```js
watch(processStages, (stages) => {
  if (!stages.length) {
    selectedStageId.value = ''
    selectedEvidenceId.value = ''
    return
  }
  if (!stages.some(stage => stage.id === selectedStageId.value)) selectedStageId.value = stages[0].id
  if (!selectedEvidenceId.value && stages[0].items[0]) selectedEvidenceId.value = stages[0].items[0].id
}, { immediate: true })
```

- [ ] **Step 2: Implement stage interactions**

```js
function toggleStage(stage) {
  selectedStageId.value = stage.id
  if (stage.items[0]) selectProcessItem(stage.items[0], stage)
  expandedStageIds.value = isStageExpanded(stage)
    ? expandedStageIds.value.filter(id => id !== stage.id)
    : [...expandedStageIds.value, stage.id]
}

function isStageExpanded(stage) {
  return expandedStageIds.value.includes(stage.id)
}

function selectProcessItem(item, stage = selectedStage.value) {
  selectedStageId.value = stage?.id || selectedStageId.value
  selectedEvidenceId.value = item.id
  if (item.frame) report.selectedEvidenceFrame.value = item.frame
}
```

- [ ] **Step 3: Implement tag navigation**

```js
function openScoringTag(tag) {
  if (tag.dimensionKey) report.selectedDimensionKey.value = tag.dimensionKey
  router.push(report.sectionPath('dimensions'))
}

function openRiskTag(tag) {
  if (tag.type === 'scoring-deduction') return openScoringTag(tag)
  router.push(report.sectionPath(tag.target === 'evidence' ? 'evidence' : 'actions'))
}
```

## Task 4: Styling and Density Control

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`

- [ ] **Step 1: Remove old table-heavy styles from the evidence section**

Keep video frame styles. Replace `.clip-card`, `.evidence-table`, `.table-row` usage with `.audit-card`, `.stage-list`, `.stage-row`, `.stage-items`.

- [ ] **Step 2: Add audit card styles**

Use compact tags and short summaries. Text should not exceed 2-3 lines visually.

- [ ] **Step 3: Add stage list styles**

Use a table-like grid:

```css
.stage-row { grid-template-columns: 110px minmax(0, 1fr) 150px 110px 130px; }
.stage-items button { grid-template-columns: 72px 70px minmax(0, 1fr) 130px 180px; }
```

- [ ] **Step 4: Mobile behavior**

At `max-width: 760px`, stack stage row fields into one column and keep the video frame above the audit card.

## Task 5: Verification

**Files:**
- Verify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`

- [ ] **Step 1: Build frontend**

Run:

```bash
npm run build
```

Workdir:

```bash
frontend/user
```

Expected: build passes. Existing large chunk warning is acceptable.

- [ ] **Step 2: Manual smoke test for meeting 20**

Open:

```text
https://localhost:5174/ai-score/20/overview
```

Expected:

- The module title is `视频过程审计`.
- A video frame is visible.
- Current audit card shows stage, roles, performance, scoring tags, and risk tags.
- Stage list appears below the video area.
- Expanding a stage shows frame/segment rows.
- Clicking a scoring tag routes to five-dimension scoring.
- Clicking independent risk routes to evidence or actions.

## Self-Review

- Spec coverage: The plan covers hybrid stage grouping, role participation, performance tags, scoring-point tags, risk/deduction ownership, expandable stage list, and navigation boundaries.
- Placeholder scan: No TBD/TODO placeholders.
- Type consistency: The plan consistently uses `processStages`, `selectedProcessItem`, `scoringTags`, `riskTags`, and `frameForEvidence` as the local overview view model names.
