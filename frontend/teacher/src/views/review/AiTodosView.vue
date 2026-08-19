<template>
  <div class="teacher-page remediation-page">
    <header class="teacher-page__head">
      <div>
        <h1>整改复盘</h1>
        <p>审核 AI 根据评分生成的整改建议：改写成学生能执行的任务后发布到协作台。</p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          刷新
        </button>
      </div>
    </header>

    <p v-if="msg" class="plan-notice is-ok" role="status">{{ msg }}</p>
    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>

    <section class="kpi-strip" aria-label="整改概览">
      <article class="teacher-card teacher-metric-card">
        <small>待处理</small>
        <strong class="is-accent">{{ pendingCount }}</strong>
        <em>需你审核或发布</em>
      </article>
      <article class="teacher-card teacher-metric-card">
        <small>当前选中</small>
        <strong>{{ current ? '1' : '0' }}</strong>
        <em>{{ current?.teamName || '从左侧选择一项' }}</em>
      </article>
      <article class="teacher-card teacher-metric-card">
        <small>优先级</small>
        <strong>{{ current ? priorityLabel(current.priority) : '—' }}</strong>
        <em>越紧急越优先发布</em>
      </article>
      <article class="teacher-card teacher-metric-card">
        <small>关联报告</small>
        <strong class="kpi-text">{{ reportRef }}</strong>
        <em>来自 AI 评分整改</em>
      </article>
    </section>

    <div v-if="loading" class="teacher-empty">正在加载整改待办…</div>

    <div v-else-if="!items.length" class="teacher-card empty-panel">
      <strong>当前没有待审核的 AI 整改</strong>
      <p>学生完成路演评分后，系统会把扣分点生成整改建议。你也可以先去查看评分报告。</p>
      <div class="empty-actions">
        <router-link class="teacher-btn teacher-btn--primary" to="/review/reports">去评分报告</router-link>
        <router-link class="teacher-btn teacher-btn--secondary" to="/review/reports?tab=upload">上传视频评分</router-link>
      </div>
    </div>

    <div v-else class="remediation-layout">
      <!-- 左侧队列 -->
      <aside class="teacher-card queue-panel">
        <div class="teacher-card__head">
          <h2>待审队列</h2>
          <span>{{ filteredItems.length }} / {{ items.length }}</span>
        </div>
        <div class="queue-filters">
          <button
            v-for="f in filters"
            :key="f.key"
            type="button"
            :class="{ 'is-active': filter === f.key }"
            @click="filter = f.key"
          >
            {{ f.label }}
          </button>
        </div>
        <div class="teacher-card__body queue-list">
          <button
            v-for="item in filteredItems"
            :key="item.id"
            type="button"
            class="queue-item"
            :class="{ 'is-active': current?.id === item.id }"
            @click="select(item)"
          >
            <div class="queue-item__top">
              <strong>{{ item.title || '未命名整改' }}</strong>
              <span class="priority-pill" :data-level="priorityLevel(item.priority)">
                {{ priorityLabel(item.priority) }}
              </span>
            </div>
            <small>
              {{ item.teamName || '未关联项目' }}
              <template v-if="item.latestReportId || item.sourceReportId">
                · 报告 #{{ item.latestReportId || item.sourceReportId }}
              </template>
            </small>
            <span class="status-chip">{{ todoStatusLabel(item.status) }}</span>
          </button>
          <div v-if="!filteredItems.length" class="queue-empty">该筛选下没有项</div>
        </div>
      </aside>

      <!-- 右侧编辑 -->
      <section class="teacher-card editor-panel">
        <template v-if="current">
          <div class="teacher-card__head">
            <div>
              <h2>审核并发布</h2>
              <p class="head-sub">改写成学生能执行的任务，再发布到协作台</p>
            </div>
            <div class="head-actions">
              <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="restore">
                用 AI 原文填充
              </button>
              <button
                type="button"
                class="teacher-btn teacher-btn--primary teacher-btn--sm"
                :disabled="publishing || !publishReady"
                @click="publish"
              >
                {{ publishing ? '发布中…' : '发布到学生' }}
              </button>
            </div>
          </div>

          <div class="teacher-card__body editor-body">
            <label class="field">
              <span>任务标题</span>
              <input v-model.trim="title" maxlength="120" placeholder="学生在协作台看到的标题" />
            </label>

            <div v-if="showOrigin" class="origin-box">
              <div class="origin-box__head">
                <span>AI 原始建议（只读参考）</span>
                <button type="button" class="teacher-link text-button" @click="originOpen = !originOpen">
                  {{ originOpen ? '收起' : '展开' }}
                </button>
              </div>
              <p v-show="originOpen">{{ current.origin }}</p>
            </div>

            <label class="field">
              <span>发给学生的任务说明</span>
              <textarea
                v-model="draft"
                rows="7"
                maxlength="2000"
                placeholder="写清：要改什么、验收标准、参考材料页/时间点"
              />
              <small class="field-hint">发布后会出现在学生端「协作 → 任务」</small>
            </label>

            <div class="field-row">
              <label class="field">
                <span>负责人</span>
                <select v-model="owner">
                  <option value="">暂不指派（全员可见）</option>
                  <option v-for="member in members" :key="member.userId" :value="member.userId">
                    {{ member.username }}{{ member.positionName ? ` · ${member.positionName}` : '' }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span>截止时间</span>
                <input v-model="due" type="datetime-local" />
              </label>
            </div>

            <div class="editor-footer">
              <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="!current" @click="saveDraft">
                暂存编辑
              </button>
              <span class="footer-tip">暂存仅保存在本页，刷新后会从服务端重新加载</span>
            </div>
          </div>
        </template>

        <div v-else class="editor-empty">
          <strong>选择左侧一条整改建议</strong>
          <p>对照 AI 原文改写后，指派负责人并发布。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fetchTeacherAiTodos, fetchTeamDashboard, publishTeacherAiTodo } from '../../api'
import { aiTodoStatusLabel, priorityLabel } from '../../utils/labels'

const items = ref([])
const current = ref(null)
const members = ref([])
const title = ref('')
const draft = ref('')
const owner = ref('')
const due = ref('')
const msg = ref('')
const error = ref('')
const loading = ref(false)
const publishing = ref(false)
const filter = ref('pending')
const originOpen = ref(true)

const filters = [
  { key: 'pending', label: '待处理' },
  { key: 'all', label: '全部' },
]

const pendingCount = computed(
  () => items.value.filter((x) => !isPublished(x.status)).length
)

const filteredItems = computed(() => {
  if (filter.value === 'all') return items.value
  return items.value.filter((x) => !isPublished(x.status))
})

const reportRef = computed(() => {
  if (!current.value) return '—'
  const id = current.value.latestReportId || current.value.sourceReportId
  return id ? `#${id}` : '—'
})

const showOrigin = computed(() => {
  const o = String(current.value?.origin || '').trim()
  if (!o) return false
  // 原文与说明相同则不重复展示
  return o !== String(draft.value || '').trim()
})

const publishReady = computed(() => Boolean(title.value.trim() && draft.value.trim() && current.value?.teamId))

function isPublished(status) {
  const s = String(status || '').toLowerCase()
  return s === 'published' || s === 'done' || s === '已发布'
}

function todoStatusLabel(value) {
  return aiTodoStatusLabel(value)
}

function priorityLevel(value) {
  const p = String(value || '').toUpperCase()
  if (['P0', 'URGENT', '0', 'HIGH'].includes(p)) return 'high'
  if (['P1', '1', 'MEDIUM'].includes(p)) return 'mid'
  return 'low'
}

function select(item) {
  current.value = item
  title.value = item.title || ''
  // 发布说明优先用 origin（问题描述），否则用 draft 字段
  const origin = String(item.origin || '').trim()
  const draftRaw = String(item.draft || '').trim()
  draft.value = origin || draftRaw || item.title || ''
  owner.value = ''
  due.value = ''
  msg.value = ''
  originOpen.value = true
  loadMembers(item.teamId)
}

function saveDraft() {
  if (!current.value) return
  current.value.title = title.value.trim() || current.value.title
  current.value.draft = draft.value
  current.value.status = 'teacher_edited'
  msg.value = '已暂存在本页。点「发布到学生」才会同步协作任务。'
}

function restore() {
  if (!current.value) return
  draft.value = String(current.value.origin || current.value.title || '')
  msg.value = '已用 AI 原文填充任务说明，可继续修改后发布。'
}

async function loadMembers(teamId) {
  if (!teamId) {
    members.value = []
    return
  }
  try {
    const dashboard = await fetchTeamDashboard(teamId)
    members.value = (dashboard.members || []).filter((m) => m.systemRole === 'STUDENT')
  } catch {
    members.value = []
  }
}

async function load() {
  loading.value = true
  error.value = ''
  msg.value = ''
  try {
    const rows = await fetchTeacherAiTodos()
    items.value = (Array.isArray(rows) ? rows : []).filter((x) => !isPublished(x.status))
    if (current.value) {
      const still = items.value.find((x) => x.id === current.value.id)
      if (still) select(still)
      else current.value = items.value[0] || null
      if (current.value && !still) select(current.value)
    } else if (items.value[0]) {
      select(items.value[0])
    } else {
      current.value = null
    }
  } catch (err) {
    error.value = err?.message || '整改待办加载失败'
    items.value = []
    current.value = null
  } finally {
    loading.value = false
  }
}

async function publish() {
  if (!current.value || !publishReady.value || publishing.value) return
  publishing.value = true
  error.value = ''
  try {
    const selected = current.value
    await publishTeacherAiTodo(selected.id, {
      teamId: selected.teamId,
      ownerUserId: owner.value || null,
      title: title.value.trim(),
      description: draft.value.trim(),
      dueAt: due.value || null,
    })
    items.value = items.value.filter((x) => x.id !== selected.id)
    current.value = items.value[0] || null
    if (current.value) select(current.value)
    msg.value = '已发布到学生端「协作 → 任务」'
  } catch (err) {
    error.value = err?.message || '发布失败'
  } finally {
    publishing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.plan-notice {
  margin: 0 0 14px;
  padding: 11px 14px;
  border-radius: 11px;
  font-size: 12px;
  font-weight: 700;
}
.plan-notice.is-ok {
  color: #0f6b4c;
  background: #e8f8f0;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.kpi-text {
  font-size: 18px !important;
  letter-spacing: 0 !important;
}

.remediation-layout {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.queue-panel .teacher-card__body {
  padding-top: 8px;
}
.queue-filters {
  display: flex;
  gap: 6px;
  padding: 0 14px 10px;
}
.queue-filters button {
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--ds-line);
  border-radius: 999px;
  background: #fff;
  color: var(--ds-ink-2);
  font: 700 12px var(--ds-font-sans);
  cursor: pointer;
}
.queue-filters button.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.queue-list {
  display: grid;
  gap: 8px;
  max-height: min(68vh, 720px);
  overflow: auto;
}
.queue-item {
  width: 100%;
  padding: 12px 12px 10px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  display: grid;
  gap: 6px;
  font: inherit;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}
.queue-item:hover {
  border-color: rgba(232, 74, 28, 0.35);
}
.queue-item.is-active {
  border-color: var(--ds-orange);
  background: #fffaf7;
  box-shadow: inset 3px 0 0 var(--ds-orange);
}
.queue-item__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.queue-item strong {
  font-size: 13px;
  color: var(--ds-ink);
  line-height: 1.35;
}
.queue-item small {
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.4;
}
.priority-pill {
  flex: 0 0 auto;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  background: #f3f4f6;
  color: #4b5563;
}
.priority-pill[data-level='high'] {
  background: #fff1f0;
  color: #d14343;
}
.priority-pill[data-level='mid'] {
  background: #fff7ed;
  color: #c2410c;
}
.status-chip {
  justify-self: start;
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}
.queue-empty {
  padding: 24px 8px;
  text-align: center;
  color: var(--ds-muted);
  font-size: 12px;
}

.editor-panel .teacher-card__head {
  align-items: flex-start;
}
.head-sub {
  margin: 4px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 500;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.editor-body {
  display: grid;
  gap: 16px;
}
.field {
  display: grid;
  gap: 7px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.field input,
.field select,
.field textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-line-strong, rgba(29, 29, 31, 0.14));
  border-radius: 12px;
  padding: 10px 12px;
  font: 500 14px/1.5 var(--ds-font-sans);
  color: var(--ds-ink);
  background: #fff;
}
.field textarea {
  min-height: 140px;
  resize: vertical;
}
.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  border-color: var(--ds-orange);
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.12);
}
.field-hint {
  font-size: 11px;
  font-weight: 500;
  color: var(--ds-muted);
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.origin-box {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f7f8f9;
  border: 1px solid var(--ds-line);
}
.origin-box__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.origin-box__head span {
  font-size: 11px;
  font-weight: 800;
  color: var(--ds-muted);
}
.origin-box p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ds-ink-2);
  white-space: pre-wrap;
}
.editor-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding-top: 4px;
  border-top: 1px solid var(--ds-line);
}
.footer-tip {
  color: var(--ds-muted);
  font-size: 11px;
}
.editor-empty {
  padding: 56px 24px;
  text-align: center;
  display: grid;
  gap: 8px;
  justify-items: center;
}
.editor-empty strong {
  font-size: 15px;
}
.editor-empty p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 13px;
}

.empty-panel {
  padding: 48px 24px;
  text-align: center;
  display: grid;
  gap: 10px;
  justify-items: center;
}
.empty-panel strong {
  font-size: 16px;
}
.empty-panel p {
  margin: 0;
  max-width: 420px;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.55;
}
.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
}

@media (max-width: 960px) {
  .kpi-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .remediation-layout {
    grid-template-columns: 1fr;
  }
  .queue-list {
    max-height: 280px;
  }
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
