# Team Work Item Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `ProjectTeam.vue` into a Linear-like OREP work item hub where the main visual focus is a unified actionable work list with left-side views/stage filters and right-side details.

**Architecture:** Keep the first implementation frontend-only and reuse existing dashboard data from `ProjectTeam.vue`. Add a small normalized work item layer inside the component, replace only the current new three-column redesign shell, and leave the older hidden template intact to avoid broad regressions. Use existing actions such as `inspectDelivery`, `goVideoScoreUpload`, `openTaskDialog`, `previewAttachment`, and section switching instead of introducing backend workflow mutations.

**Tech Stack:** Vue 3 Composition API single-file component, existing `request` utility, Element Plus messages, Vite user frontend build.

---

## File Structure

- Modify: `frontend/user/src/views/ProjectTeam.vue`
  - Add state for active work view, active stage filter, and selected work item.
  - Add computed work item normalization from existing tasks, delivery items, roadshow issues/actions, and system suggestions.
  - Replace the current overview card area with the work item hub list.
  - Replace the right-side “当前待处理” card with selected work item details.
  - Update the left rail to show work views and stage filters, while keeping secondary views for materials, members, versions, and review.
  - Add compact Linear-like CSS for dense rows and detail panels.
- Modify: `docs/superpowers/specs/2026-06-26-team-work-item-hub-design.md`
  - No required change unless implementation discovers a spec mismatch.

No new backend files are required for the first version.

---

### Task 1: Add Work Hub State And Navigation Model

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] **Step 1: Add state near existing refs**

Insert after `const activeTeamSection = ref('overview')`:

```js
const activeWorkView = ref('inbox')
const activeStageFilter = ref('ALL')
const selectedWorkItemId = ref('')
```

- [ ] **Step 2: Replace `teamNavItems` with work-first entries plus secondary entries**

Replace the existing `teamNavItems` constant with:

```js
const teamNavItems = [
  { key: 'overview', label: '工作中枢', icon: '工' },
  { key: 'materials', label: '资料库', icon: '资' },
  { key: 'tasks', label: '任务管理', icon: '任' },
  { key: 'members', label: '团队成员', icon: '员' },
  { key: 'versions', label: '作品版本', icon: '版' },
  { key: 'review', label: '路演复盘', icon: '复' }
]
```

- [ ] **Step 3: Add work view and fallback stage constants after `teamNavItems`**

```js
const workViewItems = [
  { key: 'inbox', label: '收件箱', icon: '收' },
  { key: 'mine', label: '我的工作', icon: '我' },
  { key: 'review', label: '待审核', icon: '审' },
  { key: 'score', label: '评分扣分项', icon: '评' },
  { key: 'blocked', label: '逾期/阻塞', icon: '阻' }
]

const fallbackStageFilters = [
  { key: 'COURSE', label: '课程学习' },
  { key: 'ABILITY', label: '能力测评' },
  { key: 'MATERIAL', label: '材料准备' },
  { key: 'ROADSHOW', label: '路演展示' },
  { key: 'REVIEW', label: '复盘提升' }
]
```

- [ ] **Step 4: Add helper functions near `handleActionItem`**

```js
function selectWorkView(key) {
  activeTeamSection.value = 'overview'
  activeWorkView.value = key
}

function selectStageFilter(key) {
  activeTeamSection.value = 'overview'
  activeStageFilter.value = key
}
```

- [ ] **Step 5: Do not run build yet**

This task only introduces state and constants. Build after Task 3 when template bindings exist.

---

### Task 2: Normalize Existing Data Into Work Items

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] **Step 1: Add work item computed block after `currentSideItems`**

```js
const workStageFilters = computed(() => {
  const fromStages = stages.value.map((stage) => ({
    key: String(stage.stageKey || '').toUpperCase(),
    label: stage.title || stage.stageKey || '未命名阶段'
  })).filter((item) => item.key)
  return [{ key: 'ALL', label: '全部阶段' }, ...(fromStages.length ? fromStages : fallbackStageFilters)]
})

const workItems = computed(() => {
  const taskItems = tasks.value.map((task) => createTaskWorkItem(task))
  const deliveryWorkItems = deliveryItems.value
    .filter((item) => ['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED', 'REJECTED', 'DRAFT'].includes(normalStatus(item.status)))
    .map((item) => createDeliveryWorkItem(item))
  const scoreItems = activeRoadshowProblems.value.map((item, index) => createRoadshowWorkItem(item, index, 'score'))
  const reviewItems = activeRoadshowActions.value.map((item, index) => createRoadshowWorkItem(item, index, 'review'))
  const systemItems = createSystemWorkItems()
  return [...taskItems, ...deliveryWorkItems, ...scoreItems, ...reviewItems, ...systemItems]
    .filter(Boolean)
    .sort(compareWorkItems)
})

const filteredWorkItems = computed(() => {
  return workItems.value.filter((item) => {
    if (activeStageFilter.value !== 'ALL' && normalStageKey(item.stageKey) !== normalStageKey(activeStageFilter.value)) return false
    if (activeWorkView.value === 'mine') return Number(item.ownerUserId) === Number(currentUserId.value)
    if (activeWorkView.value === 'review') return ['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED'].includes(item.status)
    if (activeWorkView.value === 'score') return item.type === 'score'
    if (activeWorkView.value === 'blocked') return item.isOverdue || item.status === 'BLOCKED'
    return item.status !== 'DONE'
  })
})

const selectedWorkItem = computed(() => {
  const list = filteredWorkItems.value
  return list.find((item) => item.id === selectedWorkItemId.value) || list[0] || null
})

const workViewCounts = computed(() => {
  const openItems = workItems.value.filter((item) => item.status !== 'DONE')
  return {
    inbox: openItems.length,
    mine: openItems.filter((item) => Number(item.ownerUserId) === Number(currentUserId.value)).length,
    review: openItems.filter((item) => ['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED'].includes(item.status)).length,
    score: openItems.filter((item) => item.type === 'score').length,
    blocked: openItems.filter((item) => item.isOverdue || item.status === 'BLOCKED').length
  }
})
```

- [ ] **Step 2: Add normalization helpers after the computed block**

```js
function createTaskWorkItem(task) {
  const status = normalStatus(task.status || task.latestSubmissionStatus || 'TODO')
  const dueAt = task.dueAt || task.updatedAt || ''
  return {
    id: `task-${task.id}`,
    type: 'task',
    typeLabel: '任务',
    badge: '任',
    title: task.title || '未命名任务',
    summary: task.description || deliveryText(task),
    status,
    statusLabel: taskStatusText(status),
    priority: normalPriority(task.priority || (isOverdueDate(dueAt, status) ? 'HIGH' : 'MEDIUM')),
    ownerName: task.ownerName || '未分配',
    ownerUserId: task.ownerUserId,
    stageKey: task.stageKey || team.value.currentStage || 'MATERIAL',
    stageLabel: stageTitle(task.stageKey),
    dueAt,
    sourceLabel: '团队任务',
    sourceMeta: task.latestSubmissionStatus ? `交付状态：${materialStatusText(task.latestSubmissionStatus)}` : '任务推进',
    isOverdue: isOverdueDate(dueAt, status),
    raw: task,
    actions: [
      { key: 'open-task', label: '查看任务', kind: 'primary' },
      ...(canSubmitTask(task) ? [{ key: 'submit-task', label: '提交成果', kind: 'secondary' }] : [])
    ],
    links: task.latestAttachmentUrl ? [{ label: task.latestAttachmentName || '任务附件', action: 'preview-task' }] : []
  }
}

function createDeliveryWorkItem(item) {
  const status = normalStatus(item.status || 'PENDING_REVIEW')
  return {
    id: `delivery-${item.deliveryId}`,
    type: 'material',
    typeLabel: '资料',
    badge: '资',
    title: item.title || '项目资料',
    summary: item.description || `${item.typeLabel} · ${materialStatusText(status)}`,
    status,
    statusLabel: materialStatusText(status),
    priority: ['CHANGES_REQUESTED', 'REJECTED'].includes(status) ? 'HIGH' : 'MEDIUM',
    ownerName: item.actorName || '团队成员',
    ownerUserId: item.raw?.ownerUserId || item.raw?.submitterUserId,
    stageKey: item.raw?.stageKey || team.value.currentStage || 'MATERIAL',
    stageLabel: stageTitle(item.raw?.stageKey || 'MATERIAL'),
    dueAt: item.updatedAt,
    sourceLabel: item.typeLabel || '项目资料',
    sourceMeta: `${item.actorName || '团队成员'} · ${formatDate(item.updatedAt)}`,
    isOverdue: false,
    raw: item,
    actions: [
      { key: 'open-material', label: '打开资料', kind: 'primary' },
      ...(canPreviewAttachment(item) ? [{ key: 'preview-material', label: '预览文件', kind: 'secondary' }] : [])
    ],
    links: attachmentUrl(item) ? [{ label: item.attachmentName || item.title || '资料文件', action: 'preview-material' }] : []
  }
}

function createRoadshowWorkItem(item, index, kind) {
  const isScore = kind === 'score'
  return {
    id: `${kind}-${index}-${slugText(item.title || item.description || index)}`,
    type: isScore ? 'score' : 'review',
    typeLabel: isScore ? '评分' : '复盘',
    badge: isScore ? '评' : '复',
    title: item.title || (isScore ? '评分扣分项待处理' : '复盘建议待处理'),
    summary: item.description || (isScore ? '来自 AI 评分报告的扣分原因' : '来自路演复盘的改进建议'),
    status: 'TODO',
    statusLabel: '待处理',
    priority: normalPriority(item.severity || (isScore ? 'HIGH' : 'MEDIUM')),
    ownerName: '团队',
    ownerUserId: null,
    stageKey: isScore ? 'ROADSHOW' : 'REVIEW',
    stageLabel: isScore ? '路演展示' : '复盘提升',
    dueAt: activeRoadshow.value?.updatedAt || activeRoadshow.value?.startedAt || '',
    sourceLabel: isScore ? 'AI 评分扣分项' : '路演复盘建议',
    sourceMeta: activeRoadshow.value?.meetingTitle || '路演评分报告',
    isOverdue: false,
    raw: item,
    actions: [
      { key: 'open-review', label: '查看复盘', kind: 'primary' },
      { key: 'create-task', label: '拆成任务', kind: 'secondary' }
    ],
    links: [{ label: activeRoadshow.value?.meetingTitle || '评分报告', action: 'open-review' }]
  }
}

function createSystemWorkItems() {
  const items = []
  const videoMaterial = deliveryItems.value.find((item) => materialFilterKey(item) === 'VIDEO')
  if (videoMaterial && !activeRoadshowProblems.value.length) {
    items.push({
      id: `system-video-score-${videoMaterial.deliveryId}`,
      type: 'system',
      typeLabel: '建议',
      badge: '建',
      title: '已上传路演视频，建议发起 AI 评分',
      summary: `可基于「${videoMaterial.title}」生成评分报告和扣分项`,
      status: 'TODO',
      statusLabel: '建议',
      priority: 'MEDIUM',
      ownerName: '系统',
      ownerUserId: null,
      stageKey: 'ROADSHOW',
      stageLabel: '路演展示',
      dueAt: videoMaterial.updatedAt,
      sourceLabel: '系统建议',
      sourceMeta: '视频资料已就绪',
      isOverdue: false,
      raw: videoMaterial,
      actions: [{ key: 'upload-score', label: '上传视频评分', kind: 'primary' }],
      links: [{ label: videoMaterial.title, action: 'open-material' }]
    })
  }
  return items
}
```

- [ ] **Step 3: Add utility helpers after existing helpers**

```js
function normalStatus(value) {
  const status = String(value || '').toUpperCase()
  if (status === 'PENDING') return 'TODO'
  if (status === 'REVIEWING') return 'PENDING_REVIEW'
  return status || 'TODO'
}

function normalPriority(value) {
  const priority = String(value || '').toUpperCase()
  if (['CRITICAL', 'HIGH'].includes(priority)) return 'HIGH'
  if (['LOW'].includes(priority)) return 'LOW'
  return 'MEDIUM'
}

function normalStageKey(value) {
  return String(value || '').toUpperCase()
}

function stageTitle(stageKey) {
  const key = normalStageKey(stageKey)
  const stage = stages.value.find((item) => normalStageKey(item.stageKey) === key)
  const fallback = fallbackStageFilters.find((item) => item.key === key)
  return stage?.title || fallback?.label || currentStageTitle.value || '未设置阶段'
}

function isOverdueDate(value, status) {
  if (!value || ['DONE', 'APPROVED'].includes(normalStatus(status))) return false
  const time = new Date(value).getTime()
  return Number.isFinite(time) && time < Date.now()
}

function priorityRank(priority) {
  return { HIGH: 3, MEDIUM: 2, LOW: 1 }[normalPriority(priority)] || 0
}

function statusRank(status) {
  const normalized = normalStatus(status)
  if (['BLOCKED'].includes(normalized)) return 5
  if (['PENDING_REVIEW', 'REVIEWING', 'CHANGES_REQUESTED', 'REJECTED'].includes(normalized)) return 4
  if (['TODO', 'IN_PROGRESS'].includes(normalized)) return 3
  if (['DRAFT'].includes(normalized)) return 2
  if (['DONE', 'APPROVED'].includes(normalized)) return 0
  return 1
}

function compareWorkItems(a, b) {
  if (a.isOverdue !== b.isOverdue) return a.isOverdue ? -1 : 1
  const statusDiff = statusRank(b.status) - statusRank(a.status)
  if (statusDiff) return statusDiff
  const priorityDiff = priorityRank(b.priority) - priorityRank(a.priority)
  if (priorityDiff) return priorityDiff
  return new Date(b.dueAt || 0).getTime() - new Date(a.dueAt || 0).getTime()
}

function slugText(value) {
  return String(value || '').replace(/\s+/g, '-').slice(0, 24)
}
```

- [ ] **Step 4: Add work item action handler after `handleActionItem`**

```js
function selectWorkItem(item) {
  selectedWorkItemId.value = item?.id || ''
}

function runWorkItemAction(item, actionKey) {
  if (!item) return
  const key = actionKey || item.actions?.[0]?.key
  if (key === 'open-task' || key === 'submit-task') {
    activeTeamSection.value = 'tasks'
    return
  }
  if (key === 'open-material') return inspectDelivery(item.raw)
  if (key === 'preview-material') return previewAttachment(item.raw)
  if (key === 'preview-task') return previewAttachment(item.raw)
  if (key === 'open-review') {
    activeTeamSection.value = 'review'
    return
  }
  if (key === 'create-task') return openTaskDialog()
  if (key === 'upload-score') return goVideoScoreUpload()
}
```

- [ ] **Step 5: Build-check after helpers are added**

Run: `npm run build`

Working directory: `frontend/user`

Expected: build succeeds. Existing chunk-size warnings are acceptable.

---

### Task 3: Replace Overview Cards With Work Item List

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] **Step 1: Replace overview section template**

Replace the current block beginning with:

```vue
<section v-if="activeTeamSection === 'overview' || activeTeamSection === 'profile'" class="team-overview-board">
```

and ending before:

```vue
<section v-else-if="activeTeamSection === 'materials' || activeTeamSection === 'versions'" class="console-card material-console-card">
```

with:

```vue
<section v-if="activeTeamSection === 'overview' || activeTeamSection === 'profile'" class="work-hub-panel">
  <div class="work-hub-head">
    <div>
      <span>{{ workViewItems.find((item) => item.key === activeWorkView)?.label || '收件箱' }}</span>
      <h2>团队工作项</h2>
      <p>任务、资料审核、评分扣分和复盘建议统一进入这里。</p>
    </div>
    <button type="button" v-if="canAssignTask" @click="openTaskDialog">新建工作项</button>
  </div>

  <div class="work-list-table" aria-label="团队工作项列表">
    <div class="work-list-head">
      <span>类型</span>
      <span>标题</span>
      <span>负责人</span>
      <span>截止</span>
      <span>状态</span>
    </div>
    <button
      v-for="item in filteredWorkItems"
      :key="item.id"
      type="button"
      class="work-item-row"
      :class="[{ active: selectedWorkItem?.id === item.id, overdue: item.isOverdue }, `priority-${item.priority.toLowerCase()}`]"
      @click="selectWorkItem(item)"
      @dblclick="runWorkItemAction(item)"
    >
      <span class="work-type"><i>{{ item.badge }}</i>{{ item.typeLabel }}</span>
      <span class="work-title"><strong>{{ item.title }}</strong><small>{{ item.summary }}</small></span>
      <span>{{ item.ownerName }}</span>
      <span>{{ formatDate(item.dueAt) }}</span>
      <span class="work-status">{{ item.isOverdue ? '已逾期' : item.statusLabel }}</span>
    </button>
    <div v-if="!filteredWorkItems.length" class="work-empty-state">
      <strong>当前视图暂无工作项</strong>
      <span>切换左侧视图或阶段筛选，查看其他团队事项。</span>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Keep materials/tasks/members/review sections unchanged**

Do not delete existing secondary sections in this task. They are still needed when users choose lower-priority views.

- [ ] **Step 3: Build-check template syntax**

Run: `npm run build`

Working directory: `frontend/user`

Expected: build succeeds. If it fails on optional chaining in template, replace `workViewItems.find(...)?` expression with a computed `activeWorkViewLabel`.

---

### Task 4: Replace Left Rail With Work Views And Stage Filters

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] **Step 1: Replace the first left rail group**

Inside `<aside class="linear-team-rail">`, replace the first `.linear-rail-group` that loops over `teamNavItems` with:

```vue
<div class="linear-rail-group">
  <span>工作视图</span>
  <button
    v-for="item in workViewItems"
    :key="`work-view-${item.key}`"
    type="button"
    :class="{ active: activeTeamSection === 'overview' && activeWorkView === item.key }"
    @click="selectWorkView(item.key)"
  >
    <i>{{ item.icon }}</i>
    <b>{{ item.label }}</b>
    <em>{{ workViewCounts[item.key] || 0 }}</em>
  </button>
</div>

<div class="linear-rail-group stage-filter-group">
  <span>阶段筛选</span>
  <button
    v-for="item in workStageFilters"
    :key="`stage-filter-${item.key}`"
    type="button"
    :class="{ active: activeTeamSection === 'overview' && activeStageFilter === item.key }"
    @click="selectStageFilter(item.key)"
  >
    <i>{{ item.key === 'ALL' ? '全' : '阶' }}</i>
    <b>{{ item.label }}</b>
  </button>
</div>

<div class="linear-rail-group muted">
  <span>资料与团队</span>
  <button
    v-for="item in teamNavItems.filter((nav) => nav.key !== 'overview')"
    :key="`rail-${item.key}`"
    type="button"
    :class="{ active: activeTeamSection === item.key }"
    @click="activeTeamSection = item.key"
  >
    <i>{{ item.icon }}</i>
    <b>{{ item.label }}</b>
  </button>
</div>
```

- [ ] **Step 2: Keep progress, stats, and quick entrance groups**

Do not remove `linear-rail-progress`, `linear-rail-stats`, or quick entrance buttons yet. They remain low-priority sidebar context.

- [ ] **Step 3: Build-check**

Run: `npm run build`

Working directory: `frontend/user`

Expected: build succeeds.

---

### Task 5: Replace Right Aside With Selected Work Item Detail

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] **Step 1: Replace right aside card template**

Replace the current `<section class="side-card action-aside-card">` inside `<aside class="team-action-aside">` with:

```vue
<section class="side-card work-detail-card" v-if="activeTeamSection === 'overview' && selectedWorkItem">
  <div class="work-detail-kicker">当前工作项</div>
  <h2>{{ selectedWorkItem.title }}</h2>
  <p>{{ selectedWorkItem.summary }}</p>

  <div class="work-detail-fields">
    <div><span>状态</span><strong>{{ selectedWorkItem.isOverdue ? '已逾期' : selectedWorkItem.statusLabel }}</strong></div>
    <div><span>负责人</span><strong>{{ selectedWorkItem.ownerName }}</strong></div>
    <div><span>阶段</span><strong>{{ selectedWorkItem.stageLabel }}</strong></div>
    <div><span>优先级</span><strong>{{ selectedWorkItem.priority === 'HIGH' ? '高' : selectedWorkItem.priority === 'LOW' ? '低' : '中' }}</strong></div>
    <div><span>截止</span><strong>{{ formatDate(selectedWorkItem.dueAt) }}</strong></div>
    <div><span>来源</span><strong>{{ selectedWorkItem.sourceLabel }}</strong></div>
  </div>

  <div class="work-detail-section">
    <span>关联内容</span>
    <button
      v-for="link in selectedWorkItem.links"
      :key="`${selectedWorkItem.id}-${link.label}`"
      type="button"
      @click="runWorkItemAction(selectedWorkItem, link.action)"
    >
      {{ link.label }}
    </button>
    <small v-if="!selectedWorkItem.links.length">暂无关联文件或报告。</small>
  </div>

  <div class="work-detail-actions">
    <button
      v-for="action in selectedWorkItem.actions"
      :key="`${selectedWorkItem.id}-${action.key}`"
      type="button"
      :class="{ primary: action.kind === 'primary' }"
      @click="runWorkItemAction(selectedWorkItem, action.key)"
    >
      {{ action.label }}
    </button>
  </div>
</section>

<section class="side-card action-aside-card" v-else>
  <div class="side-card-head">
    <h2>当前待处理</h2>
    <strong>{{ currentSideItems.length }} 项</strong>
  </div>
  <div class="missing-list">
    <button v-for="item in currentSideItems" :key="`${item.type}-${item.title}`" type="button" @click="handleActionItem(item)">
      <span>{{ item.badge }}</span>
      <strong>{{ item.title }}</strong>
      <small>{{ item.note }}</small>
    </button>
    <div v-if="!currentSideItems.length" class="console-empty">当前分区暂无待处理事项。</div>
  </div>
</section>
```

- [ ] **Step 2: Build-check**

Run: `npm run build`

Working directory: `frontend/user`

Expected: build succeeds.

---

### Task 6: Add Linear-Like Work Hub Styles

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] **Step 1: Append final CSS override before `</style>`**

```css
/* Work item hub final layout */
.work-hub-panel {
  overflow: hidden;
  border: 1px solid #e8dfd7;
  border-radius: 12px;
  background: #fff;
}

.work-hub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid #eee7e0;
}

.work-hub-head span {
  color: #8a8179;
  font-size: 12px;
  font-weight: 800;
}

.work-hub-head h2 {
  margin: 2px 0 0;
  color: #17120f;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.work-hub-head p {
  margin: 4px 0 0;
  color: #8a8179;
  font-size: 13px;
}

.work-hub-head button,
.work-detail-actions button,
.work-detail-section button {
  border: 1px solid #e4dbd2;
  border-radius: 8px;
  background: #fff;
  color: #332b26;
  font-weight: 850;
}

.work-hub-head button {
  height: 34px;
  padding: 0 12px;
}

.work-list-table {
  display: grid;
}

.work-list-head,
.work-item-row {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr) 92px 90px 82px;
  gap: 12px;
  align-items: center;
}

.work-list-head {
  padding: 8px 14px;
  border-bottom: 1px solid #eee7e0;
  background: #fbfaf8;
  color: #8a8179;
  font-size: 11px;
  font-weight: 900;
}

.work-item-row {
  width: 100%;
  min-height: 58px;
  padding: 9px 14px;
  border: 0;
  border-bottom: 1px solid #f0ebe6;
  background: #fff;
  color: #463d36;
  text-align: left;
}

.work-item-row:hover,
.work-item-row.active {
  background: #fff8f3;
}

.work-item-row.overdue {
  box-shadow: inset 3px 0 0 #f25b0c;
}

.work-type {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #6f665e;
  font-size: 12px;
  font-weight: 900;
}

.work-type i {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: #faf3ed;
  color: #ef5a10;
  font-style: normal;
}

.work-title {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.work-title strong {
  overflow: hidden;
  color: #17120f;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-title small,
.work-item-row > span:not(.work-title):not(.work-type) {
  overflow: hidden;
  color: #8a8179;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-status {
  font-weight: 900;
}

.priority-high .work-status,
.work-item-row.overdue .work-status {
  color: #f25b0c;
}

.work-empty-state {
  display: grid;
  place-items: center;
  gap: 6px;
  min-height: 220px;
  color: #8a8179;
}

.work-empty-state strong {
  color: #17120f;
}

.linear-rail-group button em {
  justify-self: end;
  color: #9a9088;
  font-size: 12px;
  font-style: normal;
  font-weight: 900;
}

.linear-rail-group button:has(em) {
  grid-template-columns: 24px minmax(0, 1fr) auto;
}

.work-detail-card {
  display: grid;
  gap: 12px;
}

.work-detail-kicker,
.work-detail-section > span {
  color: #8a8179;
  font-size: 12px;
  font-weight: 900;
}

.work-detail-card h2 {
  margin: 0;
  color: #17120f;
  font-size: 18px;
  line-height: 1.35;
  letter-spacing: -0.03em;
}

.work-detail-card p {
  margin: 0;
  color: #6f665e;
  font-size: 13px;
  line-height: 1.65;
}

.work-detail-fields {
  display: grid;
  gap: 8px;
  padding: 10px 0;
  border-top: 1px solid #eee7e0;
  border-bottom: 1px solid #eee7e0;
}

.work-detail-fields div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #8a8179;
  font-size: 12px;
}

.work-detail-fields strong {
  color: #17120f;
  text-align: right;
}

.work-detail-section,
.work-detail-actions {
  display: grid;
  gap: 8px;
}

.work-detail-section button,
.work-detail-actions button {
  min-height: 34px;
  padding: 0 10px;
  text-align: left;
}

.work-detail-actions button.primary {
  border-color: #f25b0c;
  background: #f25b0c;
  color: #fff;
  text-align: center;
}

@media (max-width: 760px) {
  .work-list-head {
    display: none;
  }

  .work-item-row {
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .work-item-row > span:nth-child(n+3) {
    display: none;
  }
}
```

- [ ] **Step 2: Build-check styles**

Run: `npm run build`

Working directory: `frontend/user`

Expected: build succeeds. Existing chunk-size warnings are acceptable.

---

### Task 7: Self-Review And Acceptance Checks

**Files:**
- Inspect: `frontend/user/src/views/ProjectTeam.vue`
- Inspect: `docs/superpowers/specs/2026-06-26-team-work-item-hub-design.md`

- [ ] **Step 1: Verify the spec acceptance criteria manually in code**

Confirm these are true in `ProjectTeam.vue`:

- Default overview section renders `.work-hub-panel`.
- `项目阶段 / 最近资料 / 任务推进` overview cards are no longer in the active new overview template.
- Left rail renders `workViewItems` and `workStageFilters`.
- `filteredWorkItems` includes tasks, delivery items, roadshow score problems, roadshow action suggestions, and system suggestions.
- Right aside renders `.work-detail-card` for selected work items.

- [ ] **Step 2: Run final build**

Run: `npm run build`

Working directory: `frontend/user`

Expected: build succeeds. Existing chunk-size warnings are acceptable.

- [ ] **Step 3: Report outcome**

Report changed file paths, what shipped, build result, and any remaining limitation such as frontend-only aggregation or missing backend persistence for generated work items.

---

## Plan Self-Review

- Spec coverage: The plan covers the A+C layout, 5 work item sources, left work views, stage filters, central unified list, selected right detail, visual de-emphasis of old cards, and build verification.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: Work item properties are consistently named `id`, `type`, `typeLabel`, `badge`, `title`, `summary`, `status`, `priority`, `ownerName`, `ownerUserId`, `stageKey`, `stageLabel`, `dueAt`, `sourceLabel`, `sourceMeta`, `isOverdue`, `raw`, `actions`, and `links`.
