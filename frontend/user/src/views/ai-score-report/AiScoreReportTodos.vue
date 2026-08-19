<template>
  <AiScoreReportShell title="待办" mode="editorial">
    <div class="todos-page coach-report-page is-split" data-testid="todos-workspace">
      <div class="todos-frame coach-report-scroll">
        <AiScoreReportCoachChrome
          active="todos"
          title="整改待办"
          :description="todoLead"
          :score-display="scoreDisplay"
          :todo-count="openCount"
          @sync="openSyncAll"
        />

        <div v-if="!items.length" class="todo-empty">
          <p>{{ emptyTodosCopy }}</p>
          <div class="todo-empty__actions">
            <RouterLink class="todo-link" :to="report.sectionPath('result')">回结果</RouterLink>
            <RouterLink class="todo-link" :to="report.sectionPath('why')">看依据</RouterLink>
          </div>
        </div>

        <!-- Linear 式：左列表（只读标题）+ 右详情（只读当前一条） -->
        <div v-else class="linear-board" data-testid="todos-layout">
          <aside class="linear-list" aria-label="待办列表">
            <div class="linear-list__toolbar">
              <div class="linear-views" role="tablist" aria-label="视图">
                <button
                  v-for="view in views"
                  :key="view.key"
                  type="button"
                  class="linear-view"
                  :class="{ 'is-on': activeView === view.key }"
                  role="tab"
                  :aria-selected="activeView === view.key"
                  @click="activeView = view.key"
                >
                  {{ view.label }}
                  <span v-if="view.count != null">{{ view.count }}</span>
                </button>
              </div>
            </div>

            <div
              v-if="showNotices && report.contractVersion.value === 'ai-score-report-v3' && activeView === 'all'"
              class="linear-note"
              data-testid="todo-coverage-strip"
            >
              <template v-if="coverage.canClaimCompleteTodos">
                已覆盖约 {{ formatPoints(coverage.coveredGapPoints) }} 分差距（多条可能对应同一失分）
              </template>
              <template v-else>
                清单可能未覆盖全部失分，可结合结果页优先问题
              </template>
            </div>

            <div class="linear-list__scroll" data-testid="todo-list">
              <template v-if="listSections.length">
                <section
                  v-for="section in listSections"
                  :key="section.key"
                  class="linear-section"
                >
                  <header class="linear-section__head">
                    <span>{{ section.label }}</span>
                    <span>{{ section.items.length }}</span>
                  </header>
                  <button
                    v-for="item in section.items"
                    :key="item.id"
                    type="button"
                    class="linear-row"
                    data-testid="todo-row"
                    :class="{ 'is-selected': selectedId === item.id }"
                    :aria-selected="selectedId === item.id"
                    @click="selectItem(item.id)"
                  >
                    <span class="linear-row__priority" :class="priorityDotClass(item)" :title="item.priorityLabel || item.priority" />
                    <span class="linear-row__title">{{ item.title }}</span>
                    <span class="linear-row__status">{{ statusShort(item) }}</span>
                  </button>
                </section>
              </template>
              <div v-else class="linear-list__empty">
                这个视图下没有任务
              </div>
            </div>
          </aside>

          <section class="linear-detail" aria-label="当前待办详情" data-testid="todo-detail">
            <Transition :name="detailTransition" mode="out-in">
            <div v-if="selected" :key="selected.id" class="linear-detail__panel">
              <header class="linear-detail__head">
                <div class="linear-detail__meta">
                  <span class="todo-tag" :class="tagClass(selected)">{{ selected.priorityLabel || priorityLabelFallback(selected) }}</span>
                  <span class="todo-tag is-status">{{ selected.hungEvidence ? '已回挂' : statusLabel(selected.status) }}</span>
                  <span v-if="selected.dimension" class="linear-detail__dim">{{ selected.dimension }}</span>
                </div>
                <h2>{{ selected.title }}</h2>
              </header>

              <div class="linear-detail__scroll">
                <p class="linear-detail__why">
                  {{ selected.issueParagraph || selected.why || '本场在该点上证据或表达不足，按下面步骤补齐即可。' }}
                </p>

                <section v-if="selected.howSteps?.length" class="todo-block">
                  <h3>怎么改</h3>
                  <ol class="todo-steps" data-testid="how-steps-table">
                    <li v-for="row in selected.howSteps" :key="row.step">
                      <div class="todo-steps__action">{{ row.action }}</div>
                      <div class="todo-steps__meta">
                        <span v-if="row.deliverable">产出：{{ row.deliverable }}</span>
                        <span v-if="row.owner || selected.ownerRole">谁来做：{{ row.owner || selected.ownerRole }}</span>
                        <span v-if="row.acceptance">算过：{{ row.acceptance }}</span>
                      </div>
                    </li>
                  </ol>
                </section>
                <section v-else-if="selected.how" class="todo-block">
                  <h3>怎么改</h3>
                  <p>{{ selected.how }}</p>
                </section>

                <section v-if="selected.sourceKind === 'task-book'" class="todo-block" data-testid="task-book-hang">
                  <h3>回挂证据</h3>
                  <p class="todo-muted">{{ selected.evidenceNeeded || '下场补上可跳转的运行/对比证据' }}。只打勾不算过。</p>
                  <p v-if="selected.hungEvidence" class="todo-hung">已回挂：{{ selected.hungEvidence }}</p>
                  <textarea
                    v-model="hangDraft"
                    class="todo-hang-input"
                    rows="3"
                    maxlength="500"
                    placeholder="粘贴仓库地址、对比页或可跳转秒数说明"
                  />
                  <button
                    type="button"
                    class="todo-btn todo-btn--primary"
                    :disabled="hangUpdating || !hangDraft.trim()"
                    @click="hangEvidence(selected)"
                  >
                    {{ hangUpdating ? '保存中…' : '回挂证据' }}
                  </button>
                </section>

                <section v-if="selected.doneLines?.length" class="todo-block">
                  <h3>怎样算完成</h3>
                  <ul>
                    <li v-for="(line, i) in selected.doneLines" :key="i">{{ line }}</li>
                  </ul>
                </section>

                <section v-if="selected.practice?.say || selected.practice?.stage" class="todo-block">
                  <h3>练一练</h3>
                  <p v-if="selected.practice.say">{{ selected.practice.say }}</p>
                  <p v-if="selected.practice.stage" class="todo-muted">{{ selected.practice.stage }}</p>
                  <button
                    v-if="selected.practice.say"
                    type="button"
                    class="todo-text-btn"
                    @click="copySay(selected)"
                  >
                    {{ copyHint || '复制说法' }}
                  </button>
                </section>

                <section v-if="selected.references?.length" class="todo-block">
                  <h3>可复制模板</h3>
                  <div
                    v-for="(ref, i) in selected.references"
                    :key="i"
                    class="todo-ref"
                  >
                    <div class="todo-ref__head">
                      <div>
                        <a
                          v-if="ref.url"
                          :href="ref.url"
                          target="_blank"
                          rel="noopener noreferrer"
                        >{{ ref.title }}</a>
                        <strong v-else>{{ ref.title }}</strong>
                        <p v-if="ref.note" class="todo-muted">{{ ref.note }}</p>
                      </div>
                      <div v-if="ref.body" class="todo-ref__actions">
                        <button type="button" class="todo-text-btn" @click="toggleRef(refKey(selected.id, i))">
                          {{ openRefKey === refKey(selected.id, i) ? '收起' : '展开' }}
                        </button>
                        <button type="button" class="todo-text-btn" @click="copyTemplate(ref, selected.id, i)">
                          {{ copyRefHintKey === refKey(selected.id, i) ? '已复制' : '复制' }}
                        </button>
                      </div>
                    </div>
                    <pre
                      v-if="ref.body && openRefKey === refKey(selected.id, i)"
                      class="todo-ref__body"
                      data-testid="ref-template-body"
                    >{{ ref.body }}</pre>
                  </div>
                </section>
              </div>

              <footer class="linear-detail__foot">
                <button
                  v-if="selected.taskRecordId && selected.status === 'not_started'"
                  type="button"
                  class="todo-btn todo-btn--primary"
                  :disabled="statusUpdating"
                  @click="startTask(selected)"
                >
                  {{ statusUpdating ? '更新中…' : '开始改' }}
                </button>
                <button
                  v-else-if="selected.taskRecordId && selected.status === 'in_progress'"
                  type="button"
                  class="todo-btn todo-btn--primary"
                  :disabled="statusUpdating"
                  @click="finishTask(selected)"
                >
                  {{ statusUpdating ? '提交中…' : '改完了，等复评' }}
                </button>
                <button type="button" class="todo-btn todo-btn--secondary" @click="openSyncOne(selected)">派给队友</button>
                <button
                  v-if="selected.evidenceAnchorIds?.length || selected.clipLabel"
                  type="button"
                  class="todo-btn todo-btn--ghost"
                  @click="goWhy(selected)"
                >
                  看录像
                </button>
                <span class="linear-detail__nav">
                  <button type="button" class="todo-nav-btn" :disabled="!prevId" @click="selectItem(prevId, 'prev')">
                    ↑ 上一条
                  </button>
                  <button type="button" class="todo-nav-btn" :disabled="!nextId" @click="selectItem(nextId, 'next')">
                    下一条 ↓
                  </button>
                </span>
              </footer>
            </div>
            </Transition>

            <div v-if="!selected" class="linear-detail__empty">
              <p>从左侧点一条待办，这里只展开这一条的改法。</p>
            </div>
          </section>
        </div>
      </div>

      <AiScoreTeamSyncDialog
        v-model="syncOpen"
        :items="syncItems"
        :preselected-ids="syncPreselectedIds"
        @success="onSyncSuccess"
      />
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreReportCoachChrome from '../../components/ai-score/report/AiScoreReportCoachChrome.vue'
import AiScoreTeamSyncDialog from '../../components/ai-score/report/AiScoreTeamSyncDialog.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'
import { buildVerificationSummary } from '../../utils/aiScoreVerification'

const report = useAiScoreReportContext()
const router = useRouter()
const route = useRoute()

const DONE = new Set(['verified', 'superseded'])
const activeView = ref('active') // active | p0 | done | all
const selectedId = ref('')
const detailDirection = ref('next') // next | prev — drives slide direction
const syncedIds = ref([])
const syncOpen = ref(false)
const syncItems = ref([])
const syncPreselectedIds = ref([])
const copyHint = ref('')
const openRefKey = ref('')
const copyRefHintKey = ref('')
const statusUpdating = ref(false)
const hangUpdating = ref(false)
const hangDraft = ref('')

const detailTransition = computed(() => (
  detailDirection.value === 'prev' ? 'detail-slide-prev' : 'detail-slide-next'
))

const items = computed(() => report.unifiedTodos.value || [])
const emptyTodosCopy = computed(() => {
  const book = report.taskBook?.value || {}
  if (book.published !== true && book.published !== 'true') {
    return '任务书尚未发布。教师发布后才会出现在这里。'
  }
  return '这一场还没有可执行的待办。'
})
const coverage = computed(() => report.coverageSummary.value || {})
const verificationSummary = computed(() => buildVerificationSummary(report.taskVerifications.value || []))
const scoreDisplay = computed(() => {
  const value = Number(report.overallScore.value)
  return Number.isFinite(value) ? value.toFixed(1) : '—'
})

const openItems = computed(() => {
  const rank = { P0: 0, P1: 1, P2: 2 }
  return [...items.value]
    .filter(item => !DONE.has(item.status))
    .sort((a, b) => (rank[a.priority] ?? 1) - (rank[b.priority] ?? 1))
})

const doneItems = computed(() => items.value.filter(item => DONE.has(item.status) || item.status === 'awaiting_rerun' || item.status === 'submitted'))
const openCount = computed(() => openItems.value.length)
const p0OpenCount = computed(() => openItems.value.filter(i => i.priority === 'P0').length)

const views = computed(() => [
  { key: 'active', label: '待处理', count: openCount.value },
  { key: 'p0', label: '先改', count: p0OpenCount.value },
  { key: 'done', label: '已提交/完成', count: doneItems.value.length || null },
  { key: 'all', label: '全部', count: items.value.length }
])

const showNotices = computed(() => {
  return report.contractVersion.value === 'ai-score-report-v3' || Boolean(verificationSummary.value.total)
})

const todoLead = computed(() => {
  if (!items.value.length) return '有待办时，左侧点标题，右侧只看这一条。'
  if (activeView.value === 'active') {
    return `待处理 ${openCount.value} 项。左侧像清单一样扫标题，点开后再看怎么改。`
  }
  if (activeView.value === 'p0') {
    return `优先 ${p0OpenCount.value} 项。先改这些通常对分数帮助最大。`
  }
  return `共 ${items.value.length} 项。建议优先用「待处理」视图，做完的会离开当前列表。`
})

const visibleItems = computed(() => {
  if (activeView.value === 'p0') return openItems.value.filter(i => i.priority === 'P0')
  if (activeView.value === 'done') return doneItems.value
  if (activeView.value === 'all') {
    const rank = { P0: 0, P1: 1, P2: 2 }
    return [...items.value].sort((a, b) => (rank[a.priority] ?? 1) - (rank[b.priority] ?? 1))
  }
  return openItems.value
})

/** Linear-style sections: group only when list is long enough to need structure */
const listSections = computed(() => {
  const list = visibleItems.value
  if (!list.length) return []

  if (activeView.value === 'done') {
    return [{ key: 'done', label: '已提交 / 已验证', items: list }]
  }

  // Active / all: group by priority, but skip empty groups
  const groups = [
    { key: 'P0', label: '先改' },
    { key: 'P1', label: '建议改' },
    { key: 'P2', label: '可后改' }
  ]
  const sections = groups
    .map(g => ({
      key: g.key,
      label: g.label,
      items: list.filter(i => i.priority === g.key)
    }))
    .filter(s => s.items.length)

  // If single priority filter, one flat section without redundant label noise
  if (activeView.value === 'p0') {
    return [{ key: 'p0', label: '先改', items: list }]
  }

  // If very few items, one section
  if (list.length <= 4) {
    return [{ key: 'flat', label: activeView.value === 'all' ? '全部' : '待处理', items: list }]
  }

  return sections.length ? sections : [{ key: 'flat', label: '待办', items: list }]
})

const selected = computed(() =>
  visibleItems.value.find(i => i.id === selectedId.value)
  || items.value.find(i => i.id === selectedId.value)
  || null
)

const selectedIndex = computed(() => visibleItems.value.findIndex(i => i.id === selectedId.value))
const prevId = computed(() => {
  const i = selectedIndex.value
  return i > 0 ? visibleItems.value[i - 1].id : ''
})
const nextId = computed(() => {
  const i = selectedIndex.value
  return i >= 0 && i < visibleItems.value.length - 1 ? visibleItems.value[i + 1].id : ''
})

function selectItem(id, direction) {
  if (!id || id === selectedId.value) return
  if (direction === 'prev' || direction === 'next') {
    detailDirection.value = direction
  } else {
    const current = selectedIndex.value
    const next = visibleItems.value.findIndex(i => i.id === id)
    if (current >= 0 && next >= 0) {
      detailDirection.value = next < current ? 'prev' : 'next'
    } else {
      detailDirection.value = 'next'
    }
  }
  selectedId.value = id
  openRefKey.value = ''
  copyRefHintKey.value = ''
}

watch(
  [visibleItems, () => route.query.task],
  ([list]) => {
    if (!list.length) {
      selectedId.value = ''
      return
    }
    const requested = String(route.query.task || '')
    if (requested && list.some(i => i.id === requested)) {
      selectedId.value = requested
      return
    }
    if (!list.some(i => i.id === selectedId.value)) {
      selectedId.value = list[0].id
    }
  },
  { immediate: true }
)

watch(activeView, () => {
  openRefKey.value = ''
  if (visibleItems.value.length && !visibleItems.value.some(i => i.id === selectedId.value)) {
    selectedId.value = visibleItems.value[0].id
  }
})

function formatPoints(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(1) : '—'
}

function refKey(todoId, index) {
  return `${todoId || 'todo'}:${index}`
}

function toggleRef(key) {
  openRefKey.value = openRefKey.value === key ? '' : key
}

async function copyTemplate(ref, todoId, index = 0) {
  const text = String(ref?.body || '').trim()
  if (!text) {
    ElMessage.warning('没有可复制的完整模板正文')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    const key = refKey(todoId, index)
    copyRefHintKey.value = key
    ElMessage.success('已复制')
    window.setTimeout(() => {
      if (copyRefHintKey.value === key) copyRefHintKey.value = ''
    }, 2000)
  } catch {
    ElMessage.error('复制失败')
  }
}

function priorityDotClass(item) {
  if (item.priority === 'P0') return 'is-p0'
  if (item.priority === 'P2') return 'is-p2'
  return 'is-p1'
}

function tagClass(item) {
  if (item.priority === 'P0') return 'is-p0'
  if (item.priority === 'P2') return 'is-p2'
  return ''
}

function priorityLabelFallback(item) {
  if (item.priority === 'P0') return '先改'
  if (item.priority === 'P2') return '可后改'
  return '建议改'
}

function statusShort(item) {
  if (item?.hungEvidence) return '已回挂'
  const status = item?.status
  return ({
    not_started: '',
    in_progress: '进行中',
    submitted: '已提交',
    awaiting_rerun: '待复评',
    verified: '完成',
    partial: '部分',
    failed: '未过',
    not_observable: '—',
    regressed: '回退',
    superseded: '—'
  })[status] || ''
}

function statusLabel(status) {
  return ({
    not_started: '未开始',
    in_progress: '进行中',
    submitted: '已提交',
    awaiting_rerun: '待复评',
    verified: '已验证',
    partial: '部分通过',
    failed: '未通过',
    not_observable: '本轮不可观测',
    regressed: '出现回退',
    superseded: '已被替代'
  })[status] || '未开始'
}

watch([selectedId, items], () => {
  const current = items.value.find(item => item.id === selectedId.value)
  hangDraft.value = current?.hungEvidence || ''
}, { immediate: true })

async function hangEvidence(item) {
  if (item?.itemIndex == null) return
  hangUpdating.value = true
  try {
    await report.hangTaskBookEvidence(item.itemIndex, hangDraft.value)
    ElMessage.success('已回挂。下场对照时才会计入闭环，本场分数不变。')
  } catch (error) {
    ElMessage.error(error?.message || '回挂失败')
  } finally {
    hangUpdating.value = false
  }
}

async function startTask(item) {
  statusUpdating.value = true
  try {
    await report.updateRemediationTaskStatus(item, 'in_progress')
    ElMessage.success('已开始')
  } catch (error) {
    ElMessage.error(error?.message || '状态更新失败')
  } finally {
    statusUpdating.value = false
  }
}

async function finishTask(item) {
  statusUpdating.value = true
  try {
    await report.submitRemediationTaskForRerun(item)
    ElMessage.success('已提交复评')
    // After finish, prefer next open item (Linear: done leaves active list)
    if (nextId.value) selectItem(nextId.value)
  } catch (error) {
    ElMessage.error(error?.message || '提交失败')
  } finally {
    statusUpdating.value = false
  }
}

async function copySay(item) {
  const text = item?.practice?.say
  if (!text) return
  try {
    if (navigator?.clipboard?.writeText) await navigator.clipboard.writeText(text)
    copyHint.value = '已复制'
    window.setTimeout(() => { copyHint.value = '' }, 1600)
  } catch {
    copyHint.value = '复制失败'
    window.setTimeout(() => { copyHint.value = '' }, 1600)
  }
}

function draftItemsForSync() {
  const drafts = report.reportWorkItemDrafts.value || []
  const todoById = new Map(items.value.map((item) => [item.id, item]))
  return drafts.map((draft) => {
    const todo = todoById.get(draft.id)
    return {
      id: String(draft.id),
      title: String(draft.title || todo?.title || draft.id),
      recoverDisplay: todo?.recoverDisplay || ''
    }
  })
}

function openSyncAll() {
  const drafts = draftItemsForSync()
  syncItems.value = drafts
  syncPreselectedIds.value = drafts.map((d) => d.id)
  syncOpen.value = true
}

function openSyncOne(item) {
  const drafts = draftItemsForSync()
  const draftIds = new Set(drafts.map((d) => d.id))
  syncItems.value = drafts
  if (draftIds.has(item.id)) {
    syncPreselectedIds.value = [item.id]
  } else {
    const idx = items.value.findIndex((row) => row.id === item.id)
    const fallback = drafts[Math.min(Math.max(idx, 0), Math.max(drafts.length - 1, 0))]
    syncPreselectedIds.value = fallback ? [fallback.id] : drafts.map((d) => d.id)
  }
  syncOpen.value = true
}

function onSyncSuccess({ ids = [] } = {}) {
  syncedIds.value = [...new Set([...syncedIds.value, ...ids.map(String)])]
}

function goWhy(item) {
  const path = report.sectionPath('why')
  const anchor = item.evidenceAnchorIds?.[0]
  if (anchor != null) router.push({ path, query: { anchor: String(anchor) } })
  else router.push(path)
}
</script>

<style scoped>
.todos-page {
  color: var(--ds-ink);
  background: transparent;
  font-family: var(--ds-font-sans);
}

.todos-frame {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
}

.todo-empty {
  padding: var(--ds-space-8) 0;
  color: var(--ds-muted);
}

.todo-empty__actions {
  display: flex;
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-3);
}

.todo-link {
  color: var(--ds-orange-deep);
  font-weight: var(--ds-weight-semibold);
  text-decoration: none;
  transition: color var(--ds-control-transition);
}

.todo-link:hover {
  color: var(--ds-orange-800, #b12f0a);
}

/* —— Board shell —— */
.linear-board {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(280px, 32%) minmax(0, 1fr);
  border: 1px solid var(--ds-card-border, var(--ds-line));
  border-radius: var(--ds-radius-lg);
  background: var(--ds-surface-solid);
  box-shadow: var(--ds-card-shadow, none);
  overflow: hidden;
}

.linear-list {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  border-right: 1px solid var(--ds-line);
  background: linear-gradient(180deg, #fafafb 0%, var(--ds-canvas) 100%);
}

.linear-list__toolbar {
  flex: 0 0 auto;
  padding: var(--ds-space-3);
  border-bottom: 1px solid var(--ds-line);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
}

.linear-views {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 3px;
  border-radius: var(--ds-radius-md);
  background: var(--ds-canvas-deep);
}

.linear-view {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 30px;
  padding: 0 11px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ds-muted);
  font: inherit;
  font-size: var(--ds-text-label);
  font-weight: var(--ds-weight-semibold);
  cursor: pointer;
  transition:
    background var(--ds-control-transition),
    color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.linear-view span {
  min-width: 1.1em;
  color: var(--ds-faint);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}

.linear-view:hover {
  color: var(--ds-ink);
  background: rgba(255, 255, 255, 0.55);
}

.linear-view.is-on {
  background: var(--ds-surface-solid);
  color: var(--ds-orange-deep);
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.06);
}

.linear-view.is-on span {
  color: var(--ds-orange-deep);
}

.linear-note {
  flex: 0 0 auto;
  margin: 0;
  padding: 8px 12px;
  border-bottom: 1px solid var(--ds-line);
  color: var(--ds-faint);
  font-size: 11px;
  line-height: 1.45;
  background: var(--ds-surface-solid);
}

.linear-list__scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.linear-list__scroll::-webkit-scrollbar {
  width: 8px;
}

.linear-list__scroll::-webkit-scrollbar-thumb {
  background: rgba(18, 20, 26, 0.12);
  border-radius: 999px;
}

.linear-list__empty {
  padding: 32px 16px;
  color: var(--ds-faint);
  font-size: 13px;
  text-align: center;
}

.linear-section__head {
  display: flex;
  justify-content: space-between;
  padding: 12px 14px 6px;
  color: var(--ds-faint);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: none;
  position: sticky;
  top: 0;
  z-index: 1;
  background: linear-gradient(180deg, #fafafb 70%, rgba(250, 250, 251, 0));
}

.linear-row {
  width: 100%;
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-height: 40px;
  margin: 0 6px 2px;
  padding: 0 10px 0 12px;
  width: calc(100% - 12px);
  border: 0;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: var(--ds-ink-2);
  transition:
    background var(--ds-control-transition),
    transform var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.linear-row:hover {
  background: rgba(255, 255, 255, 0.85);
}

.linear-row:active {
  transform: scale(0.995);
}

.linear-row.is-selected {
  background: var(--ds-surface-solid);
  box-shadow:
    inset 3px 0 0 var(--ds-orange),
    0 1px 2px rgba(18, 20, 26, 0.04);
  color: var(--ds-ink);
}

.linear-row__priority {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ds-faint);
  flex-shrink: 0;
  box-shadow: 0 0 0 3px transparent;
  transition: box-shadow var(--ds-control-transition);
}

.linear-row.is-selected .linear-row__priority {
  box-shadow: 0 0 0 3px var(--ds-orange-wash);
}

.linear-row__priority.is-p0 {
  background: var(--ds-orange);
}

.linear-row__priority.is-p1 {
  background: #8b93a0;
}

.linear-row__priority.is-p2 {
  background: #c5cad3;
}

.linear-row__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  transition: font-weight var(--ds-control-transition);
}

.linear-row.is-selected .linear-row__title {
  font-weight: 650;
}

.linear-row__status {
  color: var(--ds-faint);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

/* Detail */
.linear-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: var(--ds-surface-solid);
  position: relative;
}

.linear-detail__panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1 1 auto;
  height: 100%;
}

.linear-detail__head {
  flex: 0 0 auto;
  padding: var(--ds-space-5) var(--ds-space-5) var(--ds-space-4);
  border-bottom: 1px solid var(--ds-line);
  background: linear-gradient(180deg, #fff 0%, #fffcfa 100%);
}

.linear-detail__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.linear-detail__dim {
  color: var(--ds-faint);
  font-size: 12px;
}

.linear-detail__head h2 {
  margin: 0;
  color: var(--ds-ink);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: -0.01em;
}

.linear-detail__scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  padding: var(--ds-space-5);
  scrollbar-gutter: stable;
}

.linear-detail__why {
  margin: 0 0 var(--ds-space-5);
  max-width: 44em;
  color: var(--ds-ink-2);
  font-size: 15px;
  line-height: 1.7;
}

.linear-detail__foot {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 12px var(--ds-space-5);
  border-top: 1px solid var(--ds-line);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}

.linear-detail__nav {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.linear-detail__empty {
  display: grid;
  place-items: center;
  min-height: 240px;
  flex: 1;
  color: var(--ds-faint);
  font-size: 14px;
  padding: 24px;
  text-align: center;
}

/* Tags */
.todo-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: var(--ds-radius-pill);
  background: var(--ds-status-neutral-bg);
  color: var(--ds-status-neutral-fg);
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
}

.todo-tag.is-p0 {
  background: var(--ds-orange-soft);
  color: var(--ds-btn-selected-fg);
}

.todo-tag.is-status {
  background: transparent;
  color: var(--ds-faint);
  padding-left: 0;
}

/* Content blocks */
.todo-block {
  margin: 0 0 var(--ds-space-5);
  max-width: 44em;
}

.todo-block h3 {
  margin: 0 0 10px;
  color: var(--ds-ink);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.todo-block p,
.todo-block li {
  color: var(--ds-ink-2);
  font-size: 14px;
  line-height: 1.65;
}

.todo-block ul {
  margin: 0;
  padding-left: 1.2em;
}

.todo-steps {
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: step;
}

.todo-steps li {
  position: relative;
  margin: 0 0 10px;
  padding: 14px 14px 14px 44px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-canvas);
  counter-increment: step;
  transition:
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.todo-steps li:hover {
  border-color: var(--ds-line-strong);
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.03);
}

.todo-steps li::before {
  content: counter(step);
  position: absolute;
  top: 14px;
  left: 14px;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--ds-orange-200, #fbd0bf);
  color: var(--ds-orange-deep);
  font-size: 11px;
  font-weight: 700;
}

.todo-steps__action {
  color: var(--ds-ink);
  font-weight: 600;
  font-size: 14px;
}

.todo-steps__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 6px;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.5;
}

.todo-muted {
  color: var(--ds-muted) !important;
}

.todo-hung {
  margin: 8px 0 !important;
  color: var(--ds-text) !important;
}

.todo-hang-input {
  display: block;
  width: 100%;
  margin: 8px 0 12px;
  padding: 8px 10px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  font: inherit;
  resize: vertical;
}

.todo-ref {
  margin-bottom: 10px;
  padding: 12px 14px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: #fff;
  transition: border-color var(--ds-control-transition);
}

.todo-ref:hover {
  border-color: var(--ds-line-strong);
}

.todo-ref__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.todo-ref__head a,
.todo-ref__head strong {
  color: var(--ds-ink);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.todo-ref__head a {
  color: var(--ds-orange-deep);
}

.todo-ref__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.todo-ref__body {
  margin-top: 10px;
  padding: 12px;
  max-height: 240px;
  overflow: auto;
  border-radius: var(--ds-radius-sm);
  background: var(--ds-canvas);
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  animation: ref-expand var(--ds-motion-duration-standard) var(--ds-motion-ease-out);
}

@keyframes ref-expand {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Buttons — align DESIGN.md */
.todo-btn {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--ds-btn-height-sm);
  padding: 0 var(--ds-btn-padding-x-sm);
  border-radius: var(--ds-radius-pill);
  border: 1px solid transparent;
  font: inherit;
  font-size: var(--ds-btn-font-sm);
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition:
    background var(--ds-control-transition),
    border-color var(--ds-control-transition),
    color var(--ds-control-transition),
    box-shadow var(--ds-control-transition),
    transform var(--ds-control-transition);
}

.todo-btn:active:not(:disabled) {
  transform: translateY(var(--ds-motion-press-y));
}

.todo-btn:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.todo-btn--primary {
  background: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
  border-color: transparent;
}

.todo-btn--primary:hover:not(:disabled) {
  background: var(--ds-btn-primary-bg-hover);
}

.todo-btn--primary:active:not(:disabled) {
  background: var(--ds-btn-primary-bg-active);
}

.todo-btn--secondary {
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
  border-color: var(--ds-btn-secondary-border);
}

.todo-btn--secondary:hover:not(:disabled) {
  background: var(--ds-btn-secondary-bg-hover);
  border-color: var(--ds-btn-secondary-border-hover);
}

.todo-btn--ghost {
  background: transparent;
  color: var(--ds-ink-2);
  border-color: transparent;
}

.todo-btn--ghost:hover:not(:disabled) {
  background: var(--ds-btn-ghost-bg-hover);
}

.todo-btn:disabled {
  background: var(--ds-btn-disabled-bg);
  color: var(--ds-btn-disabled-fg);
  border-color: var(--ds-btn-disabled-border);
  cursor: not-allowed;
  transform: none;
}

.todo-nav-btn {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-sm);
  background: #fff;
  color: var(--ds-muted);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition:
    color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    background var(--ds-control-transition);
}

.todo-nav-btn:hover:not(:disabled) {
  color: var(--ds-ink);
  border-color: var(--ds-line-strong);
  background: var(--ds-canvas);
}

.todo-nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.todo-text-btn {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--ds-orange-deep);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: color var(--ds-control-transition);
}

.todo-text-btn:hover {
  color: var(--ds-orange-800, #b12f0a);
}

/* Detail slide transitions */
.detail-slide-next-enter-active,
.detail-slide-next-leave-active,
.detail-slide-prev-enter-active,
.detail-slide-prev-leave-active {
  transition:
    opacity var(--ds-motion-duration-standard) var(--ds-motion-ease-out),
    transform var(--ds-motion-duration-standard) var(--ds-motion-ease-out);
}

.detail-slide-next-enter-from {
  opacity: 0;
  transform: translateX(16px);
}

.detail-slide-next-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}

.detail-slide-prev-enter-from {
  opacity: 0;
  transform: translateX(-16px);
}

.detail-slide-prev-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

@media (max-width: 900px) {
  .linear-board {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(200px, 38vh) minmax(0, 1fr);
  }

  .linear-list {
    border-right: 0;
    border-bottom: 1px solid var(--ds-line);
  }

  .linear-detail__nav {
    margin-left: 0;
    width: 100%;
    justify-content: flex-end;
  }
}

@media (prefers-reduced-motion: reduce) {
  .linear-row,
  .todo-btn,
  .todo-nav-btn,
  .todo-steps li,
  .todo-ref,
  .detail-slide-next-enter-active,
  .detail-slide-next-leave-active,
  .detail-slide-prev-enter-active,
  .detail-slide-prev-leave-active,
  .todo-ref__body {
    transition: none !important;
    animation: none !important;
  }

  .detail-slide-next-enter-from,
  .detail-slide-next-leave-to,
  .detail-slide-prev-enter-from,
  .detail-slide-prev-leave-to {
    transform: none;
  }
}
</style>