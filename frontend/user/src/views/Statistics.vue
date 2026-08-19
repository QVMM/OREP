<template>
  <component
    :is="embedded ? 'div' : 'main'"
    class="score-summary-page"
    :class="{ 'is-embedded': embedded }"
  >
    <header v-if="!embedded" class="summary-head">
      <div>
        <h1>评分报告</h1>
        <p>查看每次路演的评分结论、扣分依据和下一轮改进建议。</p>
      </div>
      <BaseButton to="/ai-score-upload">上传评分</BaseButton>
    </header>

    <section class="summary-card" aria-label="评分报告列表">
      <header class="report-toolbar">
        <div class="tabs" role="tablist" aria-label="评分报告范围">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            <span>{{ tab.label }}</span>
            <b>{{ tab.count }}</b>
          </button>
        </div>
        <BaseButton v-if="embedded" size="small" to="/ai-score-upload">上传评分</BaseButton>
      </header>

      <div v-if="activeState.loading" class="loading-state" aria-live="polite">
        <i></i>
        <span>正在加载评分报告</span>
      </div>

      <div v-else-if="activeState.error" class="empty-state">
        <strong>评分报告暂时没有加载出来</strong>
        <p>{{ activeState.error }}</p>
        <BaseButton type="secondary" @click="reloadActive">重新加载</BaseButton>
      </div>

      <div v-else-if="!activeReports.length" class="empty-state">
        <strong>{{ activeTab === 'participant' ? '还没有我参加的评分报告' : '还没有团队评分报告' }}</strong>
        <p>{{ activeTab === 'participant' ? '上传完整路演视频后，评分报告会显示在这里。' : '团队完成路演评分后，报告会显示在这里。' }}</p>
      </div>

      <div v-else class="report-list">
        <button
          v-for="report in activeReports"
          :key="report.key"
          type="button"
          class="report-row"
          @click="openReport(report)"
        >
          <span class="source-meta">来源：{{ report.sourceLabel }}</span>
          <span class="report-main">
            <strong>{{ report.title }}</strong>
            <small>
              {{ report.dateText }} · {{ report.statusText }}
              <template v-if="report.runCount > 1"> · {{ report.runCount }} 次复评</template>
              <template v-if="report.hungDisplay"> · {{ report.hungDisplay }}</template>
              · 发现 {{ report.issueCount }} 个问题
            </small>
          </span>
          <span class="report-metrics">
            <span class="score-box">
              <b>{{ report.scoreText }}</b>
              <small>总分</small>
            </span>
            <span class="risk-box" :class="report.riskTone">
              <b>{{ report.riskCount }}</b>
              <small>高风险</small>
            </span>
          </span>
          <span class="open-link">查看报告</span>
        </button>
      </div>
    </section>
  </component>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import BaseButton from '../components/base/BaseButton.vue'

defineProps({
  embedded: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()
const activeTab = ref('participant')
const states = reactive({
  participant: { loading: true, error: '', reports: [] },
  team: { loading: true, error: '', reports: [] }
})

const tabs = computed(() => [
  { key: 'participant', label: '我参与的路演', count: states.participant.reports.length },
  { key: 'team', label: '我队伍的路演', count: states.team.reports.length }
])
const activeState = computed(() => states[activeTab.value])
const activeReports = computed(() => activeState.value.reports)

onMounted(() => {
  loadReports('participant')
  loadReports('team')
})

async function loadReports(scope) {
  const state = states[scope]
  state.loading = true
  state.error = ''
  try {
    const reports = await fetchAiScoreReports(scope)
    state.reports = normalizeReports(reports, scope)
  } catch {
    try {
      const res = await request.get(`/api/statistics/overview?scope=${scope}`)
      const data = res.data || res || {}
      state.reports = normalizeReports(data.recentMeetings || [], scope)
    } catch {
      state.error = '暂时无法获取评分报告列表，请稍后重试。'
      state.reports = []
    }
  } finally {
    state.loading = false
  }
}

async function fetchAiScoreReports(scope) {
  const res = await request.get(`/api/ai-score/reports/summary?scope=${scope}`, { silentError: true })
  const data = res.data || res || []
  return Array.isArray(data) ? data : []
}

function normalizeReports(items, scope) {
  return items.map((item, index) => {
    const sessionId = firstPresent(item.sessionId, item.session_id, item.aiSessionId, item.ai_session_id)
    const reportId = firstPresent(item.reportId, item.report_id, item.aiReportId, item.ai_report_id)
    const meetingId = firstPresent(item.meetingId, item.meeting_id, item.id)
    const sourceType = firstPresent(item.sourceType, item.source_type, item.type, '')
    const score = firstPresent(item.totalScore, item.overallScore, item.aiScore, item.score)
    const riskCount = Number(firstPresent(item.highRiskCount, item.riskCount, item.issueCount, 0))
    return {
      key: `${scope}-${sessionId || reportId || meetingId || index}`,
      sessionId,
      reportId,
      meetingId,
      title: firstPresent(item.title, item.meetingTitle, item.projectName, item.project_name, '未命名路演'),
      dateText: formatDateTime(firstPresent(item.date, item.completedAt, item.completed_at, item.createdAt, item.created_at)),
      statusText: statusText(firstPresent(item.status, item.aiStatus, item.state, 'completed')),
      sourceLabel: sourceLabel(sourceType),
      scoreText: formatScore(score),
      issueCount: Number(firstPresent(item.issueCount, item.issuesTotal, item.problemCount, 0)),
      runCount: Number(firstPresent(item.runCount, item.run_count, 0)),
      hungDisplay: firstPresent(item.hungDisplay, item.hung_display, ''),
      riskCount,
      riskTone: riskCount >= 5 ? 'danger' : riskCount > 0 ? 'warning' : 'ok'
    }
  }).filter(report => hasScore(report.scoreText))
}

function openReport(report) {
  if (report.sessionId) {
    router.push(`/ai-score/report/${report.sessionId}/result`)
    return
  }
  if (report.reportId) {
    router.push(`/ai-score/report-id/${report.reportId}/result`)
    return
  }
  if (report.meetingId) {
    router.push(`/ai-score/${report.meetingId}/result`)
  }
}

function reloadActive() {
  loadReports(activeTab.value)
}

function statusText(value) {
  const status = String(value || '').toLowerCase()
  if (status === 'completed' || status === 'success') return '已完成'
  if (status === 'scoring' || status === 'processing') return '评分中'
  if (status === 'failed') return '失败'
  return value || '已完成'
}

function sourceLabel(value) {
  const text = String(value || '').toLowerCase()
  if (text.includes('upload')) return '上传视频'
  if (text.includes('local') || text.includes('backup') || text.includes('import')) return '本地导入'
  if (text.includes('meeting') || text.includes('live')) return '路演录制'
  return '评分报告'
}

function formatScore(value) {
  if (value === undefined || value === null || value === '') return '-'
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(1) : String(value || '-')
}

function hasScore(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0
}

function formatDateTime(value) {
  if (!value) return '时间待确认'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date).replaceAll('/', '.')
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}
</script>

<style scoped>
.score-summary-page {
  min-height: calc(100vh - 104px);
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  background: transparent;
  color: #111827;
  box-sizing: border-box;
}

.summary-hero,
.summary-card {
  width: 100%;
  margin: 0;
}

.summary-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: clamp(14px, 1.4vw, 22px);
  margin-bottom: 18px;
}

.eyebrow {
  color: #f15a24;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
}

h1 {
  margin: 8px 0 7px;
  color: #111827;
  font-size: clamp(22px, 1.45vw, 26px);
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: -0.01em;
}

p {
  margin: 0;
  color: #667085;
  font-size: clamp(12px, 0.8vw, 14px);
  font-weight: 600;
  line-height: 1.65;
}

.hero-actions,
.empty-actions {
  display: flex;
  gap: 10px;
}

button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.hero-actions button,
.empty-actions button,
.empty-state > button {
  height: 36px;
  padding: 0 14px;
  border: 1px solid #e2d9d2;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  font-size: 13px;
  font-weight: 850;
}

button.primary {
  border-color: #f15a24;
  background: #f15a24;
  color: #fff;
}

.summary-card {
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(255, 255, 255, 0.56));
  box-shadow: 0 12px 28px rgba(116, 71, 39, 0.055), inset 0 1px 0 rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(18px) saturate(1.1);
  -webkit-backdrop-filter: blur(18px) saturate(1.1);
  overflow: hidden;
}

.tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0;
  padding: 6px;
  border-bottom: 1px solid rgba(240, 222, 213, 0.62);
  background: linear-gradient(90deg, rgba(255, 253, 251, 0.72), rgba(255, 248, 242, 0.5));
}

.tabs button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 38px;
  border-radius: 9px;
  background: transparent;
  color: #647086;
  font-size: 13px;
  font-weight: 850;
}

.tabs button.active {
  background: rgba(255, 255, 255, 0.82);
  color: #f15a24;
  box-shadow: 0 8px 18px rgba(116, 71, 39, 0.055), inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.tabs b {
  display: inline-grid;
  min-width: 22px;
  height: 22px;
  place-items: center;
  padding: 0 6px;
  border-radius: 999px;
  background: #fff1eb;
  color: #f15a24;
  font-size: 11px;
}

.loading-state,
.empty-state {
  display: grid;
  place-items: center;
  gap: 12px;
  min-height: 260px;
  padding: 32px;
  text-align: center;
}

.loading-state i {
  width: 34px;
  height: 34px;
  border: 3px solid #f1e5dd;
  border-top-color: #f15a24;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.empty-state strong {
  font-size: 16px;
  line-height: 1.35;
}

.report-list {
  display: grid;
  padding: 12px;
  gap: 8px;
}

.report-row {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr) 72px 72px 128px;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid rgba(240, 222, 213, 0.78);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.52));
  color: #111827;
  text-align: left;
  box-shadow: 0 8px 18px rgba(116, 71, 39, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.72);
  transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease, transform 160ms ease;
}

.report-row:hover {
  border-color: rgba(234, 88, 12, 0.42);
  background: linear-gradient(135deg, rgba(255, 250, 247, 0.95), rgba(255, 244, 237, 0.78));
  box-shadow: 0 12px 26px rgba(234, 88, 12, 0.07), inset 0 1px 0 rgba(255, 255, 255, 0.82);
  transform: translateY(-1px);
}

.report-row:nth-child(4n) {
  border-color: rgba(255, 190, 156, 0.72);
  background: linear-gradient(135deg, rgba(255, 249, 245, 0.94), rgba(255, 241, 232, 0.72));
}

.report-main {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.report-main strong {
  font-size: 14px;
  line-height: 1.35;
  font-weight: 760;
}

.report-main strong,
.report-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-main small,
.score-box small,
.risk-box small {
  color: #7b8797;
  font-size: 11px;
  font-weight: 620;
}

.score-box,
.risk-box {
  display: grid;
  gap: 3px;
  text-align: right;
}

.score-box b,
.risk-box b {
  font-size: 18px;
  line-height: 1;
}

.risk-box.danger b { color: #ef4444; }
.risk-box.warning b { color: #f97316; }
.risk-box.ok b { color: #0b8580; }

.open-link {
  color: #f15a24;
  font-size: 13px;
  font-weight: 850;
  text-align: right;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 820px) {
  .score-summary-page {
    padding: 22px 16px 40px;
  }

  .summary-hero,
  .hero-actions,
  .empty-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .report-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .score-box,
  .risk-box,
  .open-link {
    text-align: left;
  }
}

/* Align the review workspace with the home and training surfaces. */
.score-summary-page {
  min-height: 0;
  padding: 0 0 var(--ds-space-10);
  color: var(--ds-ink-2);
  font-family: var(--ds-font-sans);
}

.summary-head {
  margin-bottom: var(--ds-space-5);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--ds-space-6);
}

.summary-head h1 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-h1);
  font-weight: var(--ds-weight-bold);
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.summary-head p,
.report-toolbar p {
  margin: 6px 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-medium);
  line-height: 1.55;
}

.summary-card {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.report-toolbar {
  min-height: 76px;
  padding: 0 var(--ds-space-6);
  border-bottom: 1px solid var(--ds-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-5);
}

.score-summary-page.is-embedded {
  min-height: 0;
  padding: 0;
}

.score-summary-page.is-embedded .summary-card {
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.tabs {
  width: auto;
  padding: 4px;
  border: 0;
  border-radius: var(--ds-radius-pill);
  display: inline-flex;
  grid-template-columns: none;
  gap: 2px;
  background: var(--ds-status-neutral-bg);
}

.tabs button {
  min-width: 136px;
  height: var(--ds-btn-height-sm);
  padding: 0 var(--ds-space-4);
  border-radius: var(--ds-radius-pill);
  color: var(--ds-muted);
  font-size: var(--ds-btn-font-sm);
  font-weight: var(--ds-weight-semibold);
}

.tabs button.active {
  background: var(--ds-surface-solid);
  color: var(--ds-orange-deep);
  box-shadow: 0 1px 3px rgba(18, 20, 26, 0.1);
}

.tabs b {
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}

.loading-state,
.empty-state {
  min-height: 320px;
  padding: var(--ds-space-8);
}

.empty-state strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-h3);
}

.empty-state p {
  max-width: 480px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.report-list {
  gap: 0;
  padding: var(--ds-space-2) var(--ds-space-4) var(--ds-space-4);
}

.report-row {
  min-height: 82px;
  padding: var(--ds-space-4) var(--ds-space-3);
  border: 0;
  border-radius: var(--ds-radius-md);
  grid-template-columns: 96px minmax(0, 1fr) 152px 96px;
  gap: var(--ds-space-4);
  background: transparent;
  box-shadow: none;
  transition: background-color var(--ds-control-transition);
}

.report-row + .report-row {
  border-top: 1px solid var(--ds-line);
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

.report-row:hover,
.report-row:nth-child(4n) {
  border-color: transparent;
  background: var(--ds-orange-wash);
  box-shadow: none;
  transform: none;
}

.report-row:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: -2px;
}

.source-meta {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  font-weight: var(--ds-weight-medium);
  line-height: var(--ds-leading-body);
  text-align: left;
  white-space: nowrap;
}

.report-main {
  gap: 5px;
}

.report-main strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-bold);
}

.report-main small,
.score-box small,
.risk-box small {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  font-weight: var(--ds-weight-medium);
}

.report-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ds-space-5);
}

.score-box,
.risk-box {
  text-align: left;
}

.score-box b,
.risk-box b {
  color: var(--ds-ink);
  font-family: var(--ds-font-num);
  font-size: 20px;
}

.risk-box.danger b { color: var(--ds-red); }
.risk-box.warning b { color: var(--ds-amber); }
.risk-box.ok b { color: var(--ds-green); }

.open-link {
  color: var(--ds-orange-deep);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-bold);
  text-align: right;
}

@media (max-width: 900px) {
  .report-toolbar {
    padding: var(--ds-space-4);
    align-items: stretch;
    flex-direction: column;
  }

  .report-toolbar :deep(.base-button) {
    width: 100%;
  }

  .tabs {
    width: 100%;
  }

  .tabs button {
    flex: 1;
    min-width: 0;
  }

  .report-row {
    grid-template-columns: 88px minmax(0, 1fr) 120px;
  }

  .open-link {
    display: none;
  }
}

@media (max-width: 640px) {
  .score-summary-page {
    padding-bottom: var(--ds-space-8);
  }

  .summary-head {
    align-items: stretch;
    flex-direction: column;
  }

  .report-row {
    grid-template-columns: 1fr;
  }

  .report-metrics {
    max-width: 180px;
  }
}
</style>
