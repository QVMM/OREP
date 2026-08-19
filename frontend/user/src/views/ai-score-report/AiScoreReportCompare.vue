<template>
  <AiScoreReportShell title="对比" mode="editorial">
    <div class="compare-page">
      <AiScoreSummaryChrome
        active-key="result"
        :score="scoreDisplay"
        :level-label="levelLabel"
        :subtitle="chromeSubtitle"
        @sync="onChromeSync"
      />

      <div class="compare-scroll">
      <div class="page">
        <p class="block-label">和上一轮比</p>
        <h2 class="block-title">这轮比上轮，好在哪。</h2>

        <template v-if="hasCompareData">
          <div v-if="deltaDisplay" class="delta" :class="deltaTone">{{ deltaDisplay }}</div>
          <p class="block-lead">{{ leadText }}</p>

          <div class="split">
            <section class="panel">
              <h3>已经补上</h3>
              <ul v-if="recoveredItems.length">
                <li v-for="item in recoveredItems" :key="item.id">
                  <strong>{{ item.title }}</strong>
                  <span v-if="item.pointsDisplay" class="pts up">{{ item.pointsDisplay }}</span>
                  <p v-if="item.detail">{{ item.detail }}</p>
                </li>
              </ul>
              <p v-else class="empty-inline">暂无标记为已追回的扣分项。</p>
            </section>

            <section class="panel">
              <h3>还在 / 新问题</h3>
              <ul v-if="newIssueItems.length">
                <li v-for="item in newIssueItems" :key="item.id">
                  <strong>{{ item.title }}</strong>
                  <span v-if="item.pointsDisplay" class="pts down">{{ item.pointsDisplay }}</span>
                  <p v-if="item.detail">{{ item.detail }}</p>
                </li>
              </ul>
              <p v-else class="empty-inline">暂无标记为新增的问题。</p>
            </section>
          </div>

          <div class="actions">
            <RouterLink class="chip primary" :to="report.sectionPath('result')">回结果</RouterLink>
            <RouterLink class="chip" :to="report.sectionPath('todos')">继续改待办</RouterLink>
          </div>
        </template>

        <div v-else class="empty-wrap">
          <p>暂无历史对比数据</p>
          <p class="empty-hint">完成复评或出现可追回项后，这里会显示分差、已补上与新问题。</p>
          <div class="actions">
            <RouterLink class="chip primary" :to="report.sectionPath('result')">回结果</RouterLink>
            <RouterLink class="chip" :to="report.sectionPath('todos')">去待办</RouterLink>
          </div>
        </div>
      </div>
      </div>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreSummaryChrome from '../../components/ai-score/report/AiScoreSummaryChrome.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()

const result = computed(() => report.result.value || {})
const recovery = computed(() => report.scoreRecoverySummary.value || {})

const previousScoreDelta = computed(() => numberOrNull(firstPresent(
  result.value.previous_score_delta,
  result.value.previousScoreDelta,
  result.value.score_delta,
  result.value.scoreDelta,
  recovery.value.previous_score_delta,
  recovery.value.previousScoreDelta,
  recovery.value.score_delta,
  recovery.value.scoreDelta,
  objectFrom(result.value.previousScore).delta,
  objectFrom(result.value.previous_score).delta,
  objectFrom(result.value.scoreComparison).delta,
  objectFrom(result.value.scoreComparison).scoreDelta,
  objectFrom(result.value.scoreComparison).score_delta,
  objectFrom(result.value.score_comparison).delta,
  objectFrom(result.value.score_comparison).scoreDelta,
  objectFrom(result.value.score_comparison).score_delta
)))

const recoveredCount = computed(() => numberOrNull(firstPresent(
  recovery.value.recoveredCount,
  recovery.value.recovered_count
)))

const recoveredPoints = computed(() => numberOrNull(firstPresent(
  recovery.value.recoveredPoints,
  recovery.value.recovered_points,
  recovery.value.recoveredScore,
  recovery.value.recovered_score
)))

const newIssueCount = computed(() => numberOrNull(firstPresent(
  recovery.value.newIssueCount,
  recovery.value.new_issue_count
)))

const recoveredItems = computed(() => {
  const rows = arrayFrom(report.recoveryStructuredDeductions?.value)
  if (rows.length) {
    return rows.map((item, index) => normalizeDeductionItem(item, index, 'recovered')).filter(Boolean)
  }
  return []
})

const newIssueItems = computed(() => {
  const current = arrayFrom(report.currentStructuredDeductions?.value)
  const markedNew = current
    .filter(item => isNewIssue(item))
    .map((item, index) => normalizeDeductionItem(item, index, 'new'))
    .filter(Boolean)
  if (markedNew.length) return markedNew

  // If summary says there are new issues but status flags are missing, surface current non-recovery rows honestly as open issues
  if ((newIssueCount.value || 0) > 0 && current.length) {
    return current
      .slice(0, Math.min(current.length, newIssueCount.value || current.length))
      .map((item, index) => normalizeDeductionItem(item, index, 'open'))
      .filter(Boolean)
  }
  return []
})

const hasCompareData = computed(() => {
  if (previousScoreDelta.value !== null) return true
  if ((recoveredCount.value || 0) > 0) return true
  if ((recoveredPoints.value || 0) > 0) return true
  if (recoveredItems.value.length > 0) return true
  if ((newIssueCount.value || 0) > 0) return true
  if (newIssueItems.value.length > 0) return true
  return false
})

const deltaDisplay = computed(() => {
  if (previousScoreDelta.value === null) return ''
  return formatSigned(previousScoreDelta.value)
})

const deltaTone = computed(() => {
  const n = previousScoreDelta.value
  if (n === null) return ''
  if (n > 0) return 'up'
  if (n < 0) return 'down'
  return 'flat'
})

const leadText = computed(() => {
  const parts = []
  if (previousScoreDelta.value !== null) {
    parts.push(`相对上一轮 ${formatSigned(previousScoreDelta.value)} 分`)
  }
  if ((recoveredCount.value || recoveredItems.value.length) > 0) {
    const n = recoveredCount.value ?? recoveredItems.value.length
    parts.push(`已追回 ${n} 项`)
  } else if ((recoveredPoints.value || 0) > 0) {
    parts.push(`已追回约 ${formatScore(recoveredPoints.value)} 分`)
  }
  if ((newIssueCount.value || newIssueItems.value.length) > 0) {
    const n = newIssueCount.value ?? newIssueItems.value.length
    parts.push(`新冒出 ${n} 项`)
  }
  if (!parts.length) return '对照本轮已追回项与仍在的问题。'
  return parts.join(' · ')
})

const scoreDisplay = computed(() => {
  const n = numberOrNull(report.overallScore?.value)
  if (n === null) return ''
  return formatScore(n)
})

const levelLabel = computed(() => String(report.scoreLevel?.value?.label || ''))

const chromeSubtitle = computed(() => {
  const r = result.value
  const track = firstPresent(report.reportTrackName?.value, r.track_name, r.trackName)
  const project = firstPresent(r.project_name, r.projectName, r.project?.name)
  const session = firstPresent(r.session_no, r.sessionNo)
  return [track, project, session].filter(Boolean).join(' · ')
})

function onChromeSync() {
  ElMessage.info('请到结果页或待办页同步任务')
}

function normalizeDeductionItem(item, index, kind) {
  if (!item || typeof item !== 'object') return null
  const title = firstPresent(item.reason, item.title, item.dimensionName, item.dimension_name, kind === 'recovered' ? '已追回项' : '问题项')
  if (!title) return null
  const points = numberOrNull(firstPresent(
    item.recoveredPoints,
    item.recovered_points,
    item.deductedPoints,
    item.deducted_points,
    item.maxRecoverablePoints,
    item.max_recoverable_points
  ))
  let pointsDisplay = ''
  if (points !== null) {
    if (kind === 'recovered') pointsDisplay = `+${formatScore(Math.abs(points))}`
    else pointsDisplay = `−${formatScore(Math.abs(points))}`
  }
  return {
    id: String(firstPresent(item.id, `${kind}-${index}`)),
    title: String(title),
    detail: firstPresent(item.acceptanceCriteria, item.acceptance_criteria, item.requiredFix, item.required_fix, item.detail, ''),
    pointsDisplay
  }
}

function isNewIssue(item) {
  const status = String(firstPresent(item?.status, item?.issueStatus, item?.issue_status, '')).toLowerCase()
  if (status === 'new') return true
  if (item?.isNew === true || item?.is_new === true) return true
  if (item?.new === true) return true
  return false
}

function formatSigned(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  const body = formatScore(Math.abs(n))
  if (n > 0) return `+${body}`
  if (n < 0) return `−${body}`
  return body
}

function formatScore(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function objectFrom(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}
</script>

<style scoped>
.compare-page {
  --canvas: #fffbf7;
  --paper: #ffffff;
  --ink: #171a24;
  --ink-2: #343a49;
  --muted: #697386;
  --faint: #a9b0bc;
  --line: rgba(219, 205, 194, 0.7);
  --orange: #f04b18;
  --green: #169b68;
  --shadow: 0 16px 40px rgba(116, 71, 39, 0.08);
  --max-work: 960px;
  --gutter: clamp(28px, 4vw, 48px);
  --font: "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", "Noto Sans SC",
    -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --num: "DIN Alternate", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;

  color: var(--ink);
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #ffffff;
  background-image: none;
  font-family: var(--font);
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
}

.compare-page :deep(em),
.compare-page :deep(i) {
  font-style: normal;
}

.compare-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.page {
  max-width: var(--max-work);
  margin: 0 auto;
  padding: 32px var(--gutter) 80px;
}

.block-label {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.1em;
}

.block-title {
  margin: 0 0 12px;
  max-width: 14em;
  font-size: clamp(22px, 2.8vw, 28px);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: 0;
}

.block-lead {
  margin: 0 0 24px;
  max-width: 36em;
  font-size: 14px;
  line-height: 1.65;
  color: var(--muted);
  font-weight: 500;
}

.delta {
  margin: 8px 0 6px;
  font-family: var(--num);
  font-size: clamp(48px, 8vw, 72px);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--orange);
}

.delta.up { color: var(--green); }
.delta.down { color: var(--orange); }
.delta.flat { color: var(--muted); }

.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 640px;
}

.panel {
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
  box-shadow: var(--shadow);
}

.panel h3 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-2);
}

.panel ul {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.panel li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 10px;
}

.panel li strong {
  font-size: 14px;
  font-weight: 650;
  color: var(--ink);
  line-height: 1.4;
}

.panel li p {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: var(--muted);
  font-weight: 500;
}

.pts {
  font-family: var(--num);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.pts.up { color: var(--green); }
.pts.down { color: var(--orange); }

.empty-inline {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
  font-weight: 500;
}

.empty-wrap {
  margin-top: 12px;
  padding: 28px 22px;
  border: 1px dashed var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.empty-wrap > p:first-child {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.empty-hint {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--muted);
  font-weight: 500;
  max-width: 32em;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
}

.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-2);
  font-size: 13px;
  font-weight: 650;
  text-decoration: none;
  font-family: inherit;
}

.chip.primary {
  border-color: var(--orange);
  background: var(--orange);
  color: #fff;
}

@media (max-width: 720px) {
  .split { grid-template-columns: 1fr; }
}
</style>
