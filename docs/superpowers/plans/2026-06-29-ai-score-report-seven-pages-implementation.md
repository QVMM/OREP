# AI Score Report Seven Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the current monolithic OREP AI score report into seven maintainable, shallow-light report pages while preserving existing report data, PDF download, evidence bundle, team task, and AI jury behavior.

**Architecture:** Create a shared report context in `useAiScoreReport.js`, mount it once in `AiScoreReportLayout.vue`, and render seven child route pages through a common shell. Keep `AiScoreResult.vue` as a compatibility wrapper until all new routes are verified.

**Tech Stack:** Vue 3 Composition API, Vue Router, Element Plus, ECharts, existing `request` utility, existing AI score and AI jury APIs.

---

## Source Of Truth

Design spec: `docs/superpowers/specs/2026-06-29-ai-score-report-seven-pages-design.md`

Existing implementation to migrate from: `frontend/user/src/views/AiScoreResult.vue`

Existing route file: `frontend/user/src/router/index.js`

Build command: `npm run build` from `frontend/user`

## File Structure

Create:

- `frontend/user/src/composables/useAiScoreReport.js` - Shared report state, data loading, normalization, and actions.
- `frontend/user/src/views/ai-score-report/AiScoreReportLayout.vue` - Parent route component, loading/error/progress shell, provides report context.
- `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue` - 总览 page.
- `frontend/user/src/views/ai-score-report/AiScoreReportDimensions.vue` - 五维评分 page.
- `frontend/user/src/views/ai-score-report/AiScoreReportEvidence.vue` - 证据链 page.
- `frontend/user/src/views/ai-score-report/AiScoreReportVoice.vue` - 表达节奏 page.
- `frontend/user/src/views/ai-score-report/AiScoreReportPresentation.vue` - 现场呈现 page.
- `frontend/user/src/views/ai-score-report/AiScoreReportActions.vue` - 改进方案 page.
- `frontend/user/src/views/ai-score-report/AiScoreReportJury.vue` - AI 评审团 page.
- `frontend/user/src/components/ai-score/report/AiScoreReportShell.vue` - Shared white report layout.
- `frontend/user/src/components/ai-score/report/AiScoreMetricStrip.vue` - Shared metric strip.
- `frontend/user/src/components/ai-score/report/AiScoreReportCard.vue` - Shared card wrapper.
- `frontend/user/src/components/ai-score/report/AiScoreEmptyState.vue` - Shared empty state.

Modify:

- `frontend/user/src/router/index.js` - Add child routes and compatibility redirects.
- `frontend/user/src/views/AiScoreResult.vue` - Convert to a lightweight compatibility wrapper after new pages work.

Do not modify backend APIs in this plan.

## Task 1: Add Shared Report Context Skeleton

**Files:**
- Create: `frontend/user/src/composables/useAiScoreReport.js`

- [ ] **Step 1: Create the composable with route identity and stable public API**

Use this initial file content:

```js
import { computed, nextTick, onUnmounted, provide, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { getEvidenceBundle, prepareEvidenceBundle } from '../utils/aiScoreEvidence'
import {
  getJuryReviewBySession,
  startJuryReviewBySession,
  getLegacyJuryReviewByMeeting,
  startLegacyJuryReviewByMeeting
} from '../utils/aiJuryReview'

const AiScoreReportContextKey = Symbol('AiScoreReportContext')

export function provideAiScoreReportContext(context) {
  provide(AiScoreReportContextKey, context)
}

export function useAiScoreReportContext() {
  const context = inject(AiScoreReportContextKey)
  if (!context) throw new Error('useAiScoreReportContext must be used inside AiScoreReportLayout')
  return context
}

export function useAiScoreReport() {
  const route = useRoute()
  const router = useRouter()

  const meetingId = computed(() => route.params.meetingId)
  const sessionId = computed(() => route.params.sessionId)
  const reportId = computed(() => route.params.reportId)
  const effectiveMeetingId = computed(() => result.value.meeting_id || result.value.meetingId || meetingId.value)

  const loading = ref(true)
  const error = ref('')
  const result = ref({})
  const visualFrames = ref([])
  const selectedEvidenceFrame = ref(null)
  const selectedDimensionKey = ref('')
  const selectedAuditEventId = ref('')

  const expressionCoaching = ref(null)
  const expressionCoachingLoading = ref(false)
  const expressionCoachingError = ref('')
  const presentationCoaching = ref(null)
  const presentationCoachingLoading = ref(false)
  const presentationCoachingError = ref('')
  const actionPlanCoaching = ref(null)
  const actionPlanCoachingLoading = ref(false)
  const actionPlanCoachingError = ref('')

  const juryResult = ref(null)
  const juryLoading = ref(false)
  const juryStarting = ref(false)
  const juryError = ref('')

  const evidenceBundle = ref(null)
  const evidenceBundleLoading = ref(false)
  const availableTeams = ref([])
  const selectedTeamIdForTasks = ref(String(route.query.teamId || ''))
  const selectedReportWorkItemIds = ref([])
  const creatingTeamTasks = ref(false)
  const createdTeamTaskCount = ref(0)

  const sessionStatus = ref(null)
  const sessionProgress = ref(0)
  const sessionStage = ref('')
  const sessionErrorMessage = ref('')
  const progressPollingTimer = ref(null)

  const aiScore = computed(() => result.value.ai_score || {})
  const overallScore = computed(() => Number(aiScore.value.overall_score ?? result.value.overallScore ?? 0))
  const scoreCalibration = computed(() => result.value.score_calibration || {})
  const rawOverallScore = computed(() => Number(aiScore.value.raw_overall_score ?? scoreCalibration.value.original_score ?? overallScore.value))
  const scoreLevel = computed(() => {
    if (overallScore.value >= 85) return { label: '优秀', text: '具备示范性，可继续打磨答辩细节' }
    if (overallScore.value >= 70) return { label: '良好', text: '竞争力较强，需补齐关键证据' }
    if (overallScore.value >= 60) return { label: '待提升', text: '基础完整，需要专项优化' }
    return { label: '风险较高', text: '建议重构路演结构与演示稳定性' }
  })
  const dimensions = computed(() => {
    const source = aiScore.value.dimensions || {}
    return Object.entries(source).map(([key, dim]) => {
      const score = Number(dim.score || 0)
      const maxScore = Number(dim.max_score || dim.maxScore || 100)
      return {
        key,
        name: dim.name || key,
        score,
        maxScore,
        percent: maxScore ? Math.min(100, (score / maxScore) * 100) : 0,
        items: dim.items || [],
        improvement: dim.improvement || dim.suggestions || []
      }
    })
  })
  const selectedDimension = computed(() => dimensions.value.find(item => item.key === selectedDimensionKey.value) || dimensions.value[0] || null)
  const selectedItems = computed(() => selectedDimension.value?.items || [])
  const issues = computed(() => (aiScore.value.critical_issues || []).slice(0, 4))
  const priorities = computed(() => {
    const list = aiScore.value.improvement_priorities || []
    if (list.length) return list.slice(0, 8)
    return issues.value.map((item, index) => ({ priority: index + 1, dimension: '关键问题', issue: item }))
  })
  const structuredObservations = computed(() => result.value.structured_observations || result.value.structuredObservations || [])
  const structuredDeductions = computed(() => result.value.structured_deductions || result.value.structuredDeductions || [])
  const structuredEvidenceAnchors = computed(() => result.value.evidence_anchors || result.value.evidenceAnchors || [])
  const scoreRecoverySummary = computed(() => result.value.score_recovery_summary || result.value.scoreRecoverySummary || {})
  const currentStructuredDeductions = computed(() => structuredDeductions.value.filter(item => !item.recovery))
  const recoveryStructuredDeductions = computed(() => structuredDeductions.value.filter(item => item.recovery))
  const structuredEvidenceConfidence = computed(() => {
    const values = [
      ...structuredObservations.value.map(item => Number(item.confidence || 0)),
      ...structuredEvidenceAnchors.value.map(item => Number(item.confidence || 0))
    ].filter(value => value > 0)
    if (!values.length) return 0
    return values.reduce((sum, value) => sum + value, 0) / values.length
  })
  const reportTrackName = computed(() => result.value.track_name || result.value.trackName || '')
  const reportSourceType = computed(() => result.value.source_type || result.value.sourceType || '')

  const speech = computed(() => result.value.speech_quality || {})
  const video = computed(() => result.value.video_analysis || {})
  const videoAgg = computed(() => video.value.aggregates || {})
  const fusion = computed(() => result.value.fusion || {})
  const timelinePoints = computed(() => fusion.value.timeline || [])
  const contradictions = computed(() => (fusion.value.contradictions || []).slice(0, 6))
  const asrSegments = computed(() => Array.isArray(result.value.asr?.segments) ? result.value.asr.segments : [])
  const pauseTotal = computed(() => speech.value.pauses?.total_pauses || 0)
  const longestPause = computed(() => formatNumber(speech.value.pauses?.longest_pause, 1))
  const fillerTotal = computed(() => speech.value.fillers?.total_fillers || 0)
  const topPauses = computed(() => (speech.value.pauses?.details || [])
    .filter(item => Number(item.duration || 0) >= 3)
    .sort((a, b) => Number(b.duration || 0) - Number(a.duration || 0))
    .slice(0, 8))

  const evidenceFrames = computed(() => visualFrames.value.map((frame, index) => ({
    ...frame,
    id: frame.id || `frame-${index}`,
    timeLabel: formatTime(frame.timestamp || frame.time || frame.position_seconds || 0),
    title: frame.title || frame.caption || frame.screen_type || '关键帧',
    caption: frame.caption || frame.ocr_text || frame.description || '暂无画面说明。'
  })))

  const reportWorkItemDrafts = computed(() => {
    const deductionDrafts = currentStructuredDeductions.value.slice(0, 4).map((item, index) => ({
      id: `deduction-${index}`,
      badge: '扣',
      title: `处理扣分项：${item.title || item.dimension || item.name || '关键问题'}`,
      description: item.reason || item.detail || item.improvement || item.suggestion || '补齐评分报告指出的证据缺口。',
      stageKey: 'ROADSHOW',
      priority: Number(item.deducted || item.deduction || 0) >= 5 ? 'HIGH' : 'MEDIUM'
    }))
    return deductionDrafts.slice(0, 8)
  })

  const navItems = computed(() => [
    { key: 'overview', label: '总览', count: '' },
    { key: 'dimensions', label: '五维评分', count: dimensions.value.length || '' },
    { key: 'evidence', label: '证据链', count: structuredEvidenceAnchors.value.length || evidenceFrames.value.length || '' },
    { key: 'voice', label: '表达节奏', count: topPauses.value.length || '' },
    { key: 'presentation', label: '现场呈现', count: contradictions.value.length || '' },
    { key: 'actions', label: '改进方案', count: reportWorkItemDrafts.value.length || '' },
    { key: 'jury', label: 'AI评审团', count: juryResult.value?.members?.length || '' }
  ])

  const isSessionProgressView = computed(() => ['created', 'uploaded', 'scoring', 'failed'].includes(sessionStatus.value))

  async function loadAvailableTeams() {
    try {
      const res = await request.get('/api/project-teams/my')
      availableTeams.value = res.data || []
      if (!selectedTeamIdForTasks.value && availableTeams.value.length === 1) selectedTeamIdForTasks.value = String(availableTeams.value[0].id)
    } catch {
      availableTeams.value = []
    }
  }

  async function loadResult() {
    loading.value = true
    error.value = ''
    try {
      if (sessionId.value || reportId.value) {
        await loadSessionOrReportResult()
      } else if (meetingId.value) {
        await loadLegacyMeetingResult()
      }
      selectedDimensionKey.value = dimensions.value[0]?.key || ''
      await loadVisualFrames()
      await loadEvidenceBundle()
      selectedEvidenceFrame.value = evidenceFrames.value[0] || null
      loading.value = false
      await nextTick()
      loadExpressionCoaching()
      loadPresentationCoaching()
      loadActionPlanCoaching()
      loadJuryReview()
    } catch {
      error.value = '未找到评分结果'
      loading.value = false
    }
  }

  async function loadSessionOrReportResult() {
    if (sessionId.value) {
      const statusRes = await request.get(`/api/ai-score/sessions/${sessionId.value}/status`)
      if (statusRes.code === 200 && statusRes.data) {
        sessionStatus.value = statusRes.data.status
        sessionProgress.value = statusRes.data.progressPercent || 0
        sessionStage.value = statusRes.data.currentStage || ''
        sessionErrorMessage.value = statusRes.data.errorMessage || ''
        const status = statusRes.data.status
        if (status === 'failed') return
        if (['created', 'uploaded', 'scoring'].includes(status) || (status !== 'completed' && !statusRes.data.reportId)) {
          startProgressPolling(sessionId.value)
          return
        }
      }
    }
    const endpoint = sessionId.value
      ? `/api/ai-score/reports/by-session/${sessionId.value}`
      : `/api/ai-score/reports/by-report/${reportId.value}`
    const sessionReport = await request.get(endpoint)
    result.value = normalizeCompetitionDuration(normalizeLegacyResult(sessionReport.data || sessionReport))
  }

  async function loadLegacyMeetingResult() {
    const res = await fetch(`/api/ai/result/${meetingId.value}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    result.value = normalizeCompetitionDuration(await res.json())
  }

  async function pollSessionProgress(sid) {
    try {
      const res = await request.get(`/api/ai-score/sessions/${sid}/status`)
      if (res.code === 200 && res.data) {
        sessionStatus.value = res.data.status
        sessionProgress.value = res.data.progressPercent || 0
        sessionStage.value = res.data.currentStage || ''
        sessionErrorMessage.value = res.data.errorMessage || ''
        if (res.data.status === 'completed' && res.data.reportId) {
          stopProgressPolling()
          await loadResult()
        } else if (res.data.status === 'failed') {
          stopProgressPolling()
        }
      }
    } catch (err) {
      console.warn('AI score progress polling failed:', err)
    }
  }

  function startProgressPolling(sid) {
    stopProgressPolling()
    pollSessionProgress(sid)
    progressPollingTimer.value = setInterval(() => pollSessionProgress(sid), 3000)
  }

  function stopProgressPolling() {
    if (progressPollingTimer.value) clearInterval(progressPollingTimer.value)
    progressPollingTimer.value = null
  }

  async function loadEvidenceBundle() {
    if (!sessionId.value) return
    try {
      evidenceBundle.value = await getEvidenceBundle(sessionId.value)
    } catch {
      evidenceBundle.value = { sessionId: sessionId.value, snapshotStatus: 'missing' }
    }
  }

  async function handlePrepareEvidenceBundle() {
    if (!sessionId.value) return
    evidenceBundleLoading.value = true
    try {
      evidenceBundle.value = await prepareEvidenceBundle(sessionId.value)
      ElMessage.success('证据快照已生成')
    } finally {
      evidenceBundleLoading.value = false
    }
  }

  async function loadVisualFrames() {
    if (!effectiveMeetingId.value) {
      visualFrames.value = []
      return
    }
    try {
      const res = await fetch(`/api/ai/meeting/${effectiveMeetingId.value}/visual-frames`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      visualFrames.value = (data.frames || []).sort((a, b) => Number(a.timestamp || 0) - Number(b.timestamp || 0))
    } catch {
      visualFrames.value = []
    }
  }

  async function loadExpressionCoaching(refresh = false) {
    if (!effectiveMeetingId.value) return
    expressionCoachingLoading.value = true
    expressionCoachingError.value = ''
    try {
      const res = await fetch(`/api/ai/coaching/expression/${effectiveMeetingId.value}${refresh ? '?refresh=true' : ''}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      expressionCoaching.value = await res.json()
    } catch {
      expressionCoaching.value = null
      expressionCoachingError.value = '模型表达训练建议暂未生成，请检查后端模型服务或稍后重试。'
    } finally {
      expressionCoachingLoading.value = false
    }
  }

  async function loadPresentationCoaching(refresh = false) {
    if (!effectiveMeetingId.value) return
    presentationCoachingLoading.value = true
    presentationCoachingError.value = ''
    try {
      const res = await fetch(`/api/ai/coaching/presentation/${effectiveMeetingId.value}${refresh ? '?refresh=true' : ''}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      presentationCoaching.value = await res.json()
    } catch {
      presentationCoaching.value = null
      presentationCoachingError.value = '模型现场呈现建议暂未生成，请检查后端模型服务或稍后重试。'
    } finally {
      presentationCoachingLoading.value = false
    }
  }

  async function loadActionPlanCoaching(refresh = false) {
    if (!effectiveMeetingId.value) return
    actionPlanCoachingLoading.value = true
    actionPlanCoachingError.value = ''
    try {
      const res = await fetch(`/api/ai/coaching/action-plan/${effectiveMeetingId.value}${refresh ? '?refresh=true' : ''}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      actionPlanCoaching.value = await res.json()
    } catch {
      actionPlanCoaching.value = null
      actionPlanCoachingError.value = '模型提分方案暂未生成，请检查后端模型服务或稍后重试。'
    } finally {
      actionPlanCoachingLoading.value = false
    }
  }

  async function loadJuryReview() {
    juryLoading.value = true
    juryError.value = ''
    try {
      if (sessionId.value) juryResult.value = sanitizeInternalAiScoreFields(await getJuryReviewBySession(sessionId.value))
      else if (effectiveMeetingId.value) juryResult.value = sanitizeInternalAiScoreFields(await getLegacyJuryReviewByMeeting(effectiveMeetingId.value))
      else juryResult.value = { status: 'empty' }
    } catch {
      juryResult.value = { status: 'empty' }
      juryError.value = 'AI评审团复核暂未生成。'
    } finally {
      juryLoading.value = false
    }
  }

  async function startJuryReview() {
    juryStarting.value = true
    juryError.value = ''
    try {
      if (sessionId.value) juryResult.value = sanitizeInternalAiScoreFields(await startJuryReviewBySession(sessionId.value))
      else if (effectiveMeetingId.value) juryResult.value = sanitizeInternalAiScoreFields(await startLegacyJuryReviewByMeeting(effectiveMeetingId.value))
    } catch {
      juryError.value = 'AI评审团复核启动失败，请稍后重试。'
    } finally {
      juryStarting.value = false
    }
  }

  async function createTeamTasksFromReport() {
    if (!selectedTeamIdForTasks.value) {
      ElMessage.warning('请先选择项目团队')
      return
    }
    const selected = reportWorkItemDrafts.value.filter(item => selectedReportWorkItemIds.value.includes(item.id))
    if (!selected.length) {
      ElMessage.warning('请选择要生成的工作项')
      return
    }
    creatingTeamTasks.value = true
    createdTeamTaskCount.value = 0
    try {
      for (const item of selected) {
        await request.post(`/api/project-teams/${selectedTeamIdForTasks.value}/tasks`, {
          title: item.title,
          description: buildTeamTaskDescription(item),
          ownerUserId: null,
          stageKey: item.stageKey || 'REVIEW',
          priority: item.priority || 'MEDIUM',
          dueAt: null
        })
        createdTeamTaskCount.value += 1
      }
      ElMessage.success(`已生成 ${createdTeamTaskCount.value} 个团队工作项`)
    } finally {
      creatingTeamTasks.value = false
    }
  }

  function buildTeamTaskDescription(item) {
    const reportLabel = result.value.session_no || result.value.sessionNo || sessionId.value || reportId.value || effectiveMeetingId.value || '当前评分报告'
    return [
      item.description,
      '',
      `来源：AI 路演评分报告 ${reportLabel}`,
      `综合评分：${formatNumber(overallScore.value, 2)}/100`,
      '处理要求：补齐证据、修改材料或完成下一轮彩排后，回到团队工作项更新状态。'
    ].filter(Boolean).join('\n')
  }

  async function downloadPdf() {
    const pdfUrl = sessionId.value
      ? `/api/ai-score/reports/by-session/${sessionId.value}/pdf`
      : effectiveMeetingId.value
        ? `/api/ai-score/pdf/${effectiveMeetingId.value}`
        : ''
    if (!pdfUrl) {
      ElMessage.warning('当前报告暂未关联可下载的 PDF')
      return
    }
    const blob = await request.get(pdfUrl, { responseType: 'blob', timeout: 60000 })
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = `${result.value.session_no || result.value.sessionNo || `AI评分报告_${sessionId.value || effectiveMeetingId.value}`}.pdf`
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
  }

  function goBack() {
    router.back()
  }

  function goMeeting() {
    if (effectiveMeetingId.value) router.push(`/meeting/${effectiveMeetingId.value}`)
  }

  function goTeamScoreWorkItems() {
    router.push({ path: '/project-team', query: { workView: 'score', teamId: selectedTeamIdForTasks.value || undefined } })
  }

  function sectionPath(section) {
    if (sessionId.value) return `/ai-score/report/${sessionId.value}/${section}`
    if (reportId.value) return `/ai-score/report-id/${reportId.value}/${section}`
    return `/ai-score/${meetingId.value}/${section}`
  }

  watch(reportWorkItemDrafts, items => {
    selectedReportWorkItemIds.value = items.map(item => item.id)
  }, { immediate: true })

  onUnmounted(stopProgressPolling)

  return {
    route,
    router,
    meetingId,
    sessionId,
    reportId,
    effectiveMeetingId,
    loading,
    error,
    result,
    visualFrames,
    selectedEvidenceFrame,
    selectedDimensionKey,
    selectedAuditEventId,
    expressionCoaching,
    expressionCoachingLoading,
    expressionCoachingError,
    presentationCoaching,
    presentationCoachingLoading,
    presentationCoachingError,
    actionPlanCoaching,
    actionPlanCoachingLoading,
    actionPlanCoachingError,
    juryResult,
    juryLoading,
    juryStarting,
    juryError,
    evidenceBundle,
    evidenceBundleLoading,
    availableTeams,
    selectedTeamIdForTasks,
    selectedReportWorkItemIds,
    creatingTeamTasks,
    createdTeamTaskCount,
    sessionStatus,
    sessionProgress,
    sessionStage,
    sessionErrorMessage,
    isSessionProgressView,
    aiScore,
    overallScore,
    rawOverallScore,
    scoreCalibration,
    scoreLevel,
    dimensions,
    selectedDimension,
    selectedItems,
    issues,
    priorities,
    structuredObservations,
    structuredDeductions,
    structuredEvidenceAnchors,
    scoreRecoverySummary,
    currentStructuredDeductions,
    recoveryStructuredDeductions,
    structuredEvidenceConfidence,
    reportTrackName,
    reportSourceType,
    speech,
    video,
    videoAgg,
    fusion,
    timelinePoints,
    contradictions,
    asrSegments,
    pauseTotal,
    longestPause,
    fillerTotal,
    topPauses,
    evidenceFrames,
    reportWorkItemDrafts,
    navItems,
    loadResult,
    loadAvailableTeams,
    loadExpressionCoaching,
    loadPresentationCoaching,
    loadActionPlanCoaching,
    loadJuryReview,
    startJuryReview,
    handlePrepareEvidenceBundle,
    createTeamTasksFromReport,
    downloadPdf,
    goBack,
    goMeeting,
    goTeamScoreWorkItems,
    sectionPath,
    formatNumber,
    formatSignedNumber,
    formatDateTime,
    formatTime,
    formatDuration,
    clipText
  }
}

function normalizeLegacyResult(data) {
  data = sanitizeInternalAiScoreFields(data || {})
  const dimensions = parseJsonValue(data.dimensions ?? data.dimensionsJson, {})
  const highlights = parseJsonValue(data.highlights ?? data.highlightsJson, [])
  const criticalIssues = parseJsonValue(data.criticalIssues ?? data.criticalIssuesJson ?? data.issues, [])
  const improvementPriorities = parseJsonValue(data.improvementPriorities ?? data.improvementPrioritiesJson ?? data.suggestions, [])
  const scoreCalibration = parseJsonValue(data.scoreCalibration ?? data.scoreCalibrationJson, {})
  const speechQuality = parseJsonValue(data.speechQuality ?? data.speechQualityJson, {})
  return {
    ...data,
    meeting_id: data.meetingId || data.meeting_id,
    session_id: data.sessionId || data.session_id,
    session_no: data.sessionNo || data.session_no || data.scoringConsistencyNo,
    track_name: data.trackName || data.track_name,
    source_type: data.sourceType || data.source_type,
    completed_at: data.completedAt || data.completed_at,
    structured_observations: parseJsonValue(data.structuredObservations ?? data.structured_observations, []),
    structured_deductions: parseJsonValue(data.structuredDeductions ?? data.structured_deductions, []),
    evidence_anchors: parseJsonValue(data.evidenceAnchors ?? data.evidence_anchors, []),
    score_recovery_summary: parseJsonValue(data.scoreRecoverySummary ?? data.score_recovery_summary, {}),
    score_calibration: scoreCalibration,
    speech_quality: speechQuality,
    ai_score: data.ai_score || {
      overall_score: data.overallScore || 0,
      raw_overall_score: scoreCalibration.original_score,
      dimensions,
      highlights,
      critical_issues: criticalIssues,
      improvement_priorities: improvementPriorities
    }
  }
}

function normalizeCompetitionDuration(data) {
  const cloned = sanitizeInternalAiScoreFields(clonePlain(data || {}))
  const duration = Number(cloned.audio_info?.duration || cloned.asr?.duration || 0)
  const durationMinutes = duration / 60
  if (durationMinutes < 50 || durationMinutes > 60) return cloned
  const score = cloned.ai_score || {}
  score.critical_issues = normalizeDurationIssues(score.critical_issues || [])
  score.improvement_priorities = normalizeDurationValue(score.improvement_priorities || [])
  score.dimensions = normalizeDurationValue(score.dimensions || {})
  cloned.ai_score = score
  return cloned
}

function clonePlain(value) {
  try {
    return JSON.parse(JSON.stringify(value))
  } catch {
    return value
  }
}

function parseJsonValue(value, fallback) {
  if (value == null || value === '') return fallback
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

function sanitizeInternalAiScoreFields(value) {
  const forbidden = new Set(['rubric_hash', 'rubrichash', 'rubric_path', 'rubricpath', 'internal_version', 'internalversion', 'ruleengineversion', 'rule_engine_version', 'prompt', 'weight', 'model', 'provider'])
  if (Array.isArray(value)) return value.map(item => sanitizeInternalAiScoreFields(item))
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !forbidden.has(String(key).replace(/[-\s]/g, '').toLowerCase()))
    .map(([key, item]) => [key, sanitizeInternalAiScoreFields(item)]))
}

function normalizeDurationIssues(items) {
  if (!Array.isArray(items)) return []
  return items.map(item => normalizeDurationValue(item))
}

function normalizeDurationValue(value) {
  if (Array.isArray(value)) return value.map(item => normalizeDurationValue(item))
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalizeDurationValue(item)]))
  if (typeof value === 'string') return normalizeDurationText(value)
  return value
}

function normalizeDurationText(text) {
  if (!/远超常规|严重超时|10\s*-\s*15\s*分钟|时间控制不合理/.test(text)) return text
  return text
    .replace(/严格控制路演时间在\s*10\s*-\s*15\s*分钟内/g, '按60分钟赛制优化各模块时间分配')
    .replace(/控制路演时间在\s*10\s*-\s*15\s*分钟内/g, '按60分钟赛制优化各模块时间分配')
    .replace(/控制在\s*10\s*-\s*15\s*分钟内/g, '按60分钟赛制优化各模块时间分配')
    .replace(/远超常规比赛时间/g, '符合60分钟赛制时长要求')
    .replace(/远超常规/g, '符合60分钟赛制时长要求')
    .replace(/严重超时/g, '环节分配不均衡')
    .replace(/时间控制不合理/g, '节奏分配仍需优化')
}

function formatNumber(value, digits = 1) {
  const number = Number(value || 0)
  return Number.isFinite(number) ? number.toFixed(digits) : '-'
}

function formatSignedNumber(value, digits = 1) {
  const number = Number(value || 0)
  if (!Number.isFinite(number)) return '-'
  return `${number > 0 ? '+' : ''}${number.toFixed(digits)}`
}

function formatDateTime(value) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds || 0)))
  const mins = Math.floor(total / 60)
  const secs = total % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function formatDuration(seconds) {
  const value = Number(seconds || 0)
  if (!value) return '-'
  if (value < 60) return `${Math.round(value)} 秒`
  return `${Math.floor(value / 60)}分${Math.round(value % 60)}秒`
}

function clipText(value, max = 80) {
  const text = String(value || '')
  return text.length > max ? `${text.slice(0, max)}...` : text
}
```

- [ ] **Step 2: Run build and capture first errors**

Run: `npm run build`

Workdir: `frontend/user`

Expected: It may still pass because the new composable is unused. If it fails, fix syntax/import errors in `useAiScoreReport.js` before continuing.

## Task 2: Add Shared Report UI Components

**Files:**
- Create: `frontend/user/src/components/ai-score/report/AiScoreReportCard.vue`
- Create: `frontend/user/src/components/ai-score/report/AiScoreMetricStrip.vue`
- Create: `frontend/user/src/components/ai-score/report/AiScoreEmptyState.vue`
- Create: `frontend/user/src/components/ai-score/report/AiScoreReportShell.vue`

- [ ] **Step 1: Create `AiScoreReportCard.vue`**

```vue
<template>
  <section class="report-card" :class="tone">
    <slot />
  </section>
</template>

<script setup>
defineProps({
  tone: { type: String, default: '' }
})
</script>

<style scoped>
.report-card {
  min-width: 0;
  padding: 18px;
  border: 1px solid #dde5f2;
  border-radius: 12px;
  background: #fff;
}

.report-card.soft {
  background: #f8fbff;
}

.report-card.warning {
  border-color: #ffd7bd;
  background: #fffaf6;
}

.report-card.success {
  border-color: #bfe8cf;
  background: #f6fdf8;
}
</style>
```

- [ ] **Step 2: Create `AiScoreMetricStrip.vue`**

```vue
<template>
  <section class="metric-strip" aria-label="报告关键指标">
    <article v-for="metric in metrics" :key="metric.label" class="metric-item" :class="metric.tone">
      <span>{{ metric.label }}</span>
      <strong>{{ metric.value }}</strong>
      <small>{{ metric.hint }}</small>
    </article>
  </section>
</template>

<script setup>
defineProps({
  metrics: { type: Array, default: () => [] }
})
</script>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  overflow: hidden;
  border: 1px solid #dde5f2;
  border-radius: 12px;
  background: #fff;
}

.metric-item {
  min-height: 94px;
  padding: 16px 18px;
  border-right: 1px solid #edf1f7;
}

.metric-item:last-child {
  border-right: 0;
}

.metric-item span,
.metric-item small {
  display: block;
  color: #66728a;
  font-size: 12px;
}

.metric-item strong {
  display: block;
  margin: 7px 0 4px;
  color: #0d1b3d;
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.metric-item.success strong { color: #0a8f55; }
.metric-item.warning strong { color: #f26a21; }
.metric-item.danger strong { color: #e43d30; }
.metric-item.primary strong { color: #155dfc; }

@media (max-width: 720px) {
  .metric-strip {
    grid-template-columns: 1fr 1fr;
  }
}
```

- [ ] **Step 3: Create `AiScoreEmptyState.vue`**

```vue
<template>
  <div class="empty-state">
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '报告生成后会在这里展示分析结果。' }
})
</script>

<style scoped>
.empty-state {
  display: grid;
  place-items: center;
  min-height: 180px;
  padding: 24px;
  border: 1px dashed #cbd6e8;
  border-radius: 12px;
  background: #f8fbff;
  text-align: center;
}

.empty-state strong {
  color: #0d1b3d;
  font-size: 16px;
}

.empty-state p {
  max-width: 420px;
  margin: 8px 0 0;
  color: #66728a;
  line-height: 1.7;
}
</style>
```

- [ ] **Step 4: Create `AiScoreReportShell.vue`**

```vue
<template>
  <div class="report-shell">
    <aside class="report-rail">
      <div class="rail-card session-card">
        <span>AI评分会话</span>
        <strong>{{ sessionTitle }}</strong>
        <small>{{ completedAt }}</small>
      </div>

      <nav class="report-nav" aria-label="AI评分报告导航">
        <RouterLink
          v-for="item in navItems"
          :key="item.key"
          :to="sectionPath(item.key)"
          class="nav-item"
          active-class="active"
        >
          <span>{{ item.label }}</span>
          <em v-if="item.count !== ''">{{ item.count }}</em>
        </RouterLink>
      </nav>

      <div class="rail-card cycle-card">
        <span>整改周期</span>
        <div class="cycle-dots">
          <i class="active"></i><i></i><i></i><i></i><i></i>
        </div>
        <small>今天 / D1 / D2 / D3 / 重评</small>
      </div>
    </aside>

    <main class="report-main">
      <header class="report-header">
        <div>
          <h1>{{ title }}</h1>
          <p>{{ subtitle }}</p>
        </div>
        <div class="report-actions">
          <button type="button" class="secondary" @click="goMeeting">返回会议</button>
          <button type="button" class="secondary" @click="downloadPdf">下载 PDF</button>
          <slot name="actions" />
        </div>
      </header>

      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAiScoreReportContext } from '../../../composables/useAiScoreReport'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
})

const report = useAiScoreReportContext()

const navItems = report.navItems
const sectionPath = report.sectionPath
const goMeeting = report.goMeeting
const downloadPdf = report.downloadPdf
const sessionTitle = computed(() => report.result.value.session_no ? `S-${report.result.value.session_no}` : `#${report.sessionId.value || report.reportId.value || report.meetingId.value || '-'}`)
const completedAt = computed(() => report.formatDateTime(report.result.value.completed_at || report.result.value.completedAt))
</script>

<style scoped>
.report-shell {
  min-height: calc(100vh - var(--header-height));
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  background: #f6f8fc;
  color: #0d1b3d;
}

.report-rail {
  position: sticky;
  top: var(--header-height);
  height: calc(100vh - var(--header-height));
  padding: 18px;
  border-right: 1px solid #dde5f2;
  background: #fff;
}

.rail-card {
  padding: 14px;
  border: 1px solid #dde5f2;
  border-radius: 10px;
  background: #fbfdff;
}

.rail-card span,
.rail-card small {
  display: block;
  color: #66728a;
  font-size: 12px;
}

.rail-card strong {
  display: block;
  margin: 6px 0;
  font-size: 18px;
}

.report-nav {
  display: grid;
  gap: 8px;
  margin: 18px 0;
}

.nav-item {
  display: flex;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-radius: 9px;
  color: #22314f;
  text-decoration: none;
  font-weight: 700;
}

.nav-item:hover,
.nav-item.active {
  color: #155dfc;
  background: #eaf1ff;
}

.nav-item em {
  min-width: 24px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #fff;
  color: #66728a;
  font-size: 12px;
  font-style: normal;
  text-align: center;
}

.cycle-dots {
  display: flex;
  gap: 10px;
  margin: 12px 0;
}

.cycle-dots i {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #c8d2e3;
}

.cycle-dots i.active {
  background: #155dfc;
}

.report-main {
  min-width: 0;
  padding: 24px;
}

.report-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.report-header h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.15;
}

.report-header p {
  margin: 8px 0 0;
  color: #55627a;
}

.report-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.report-actions button,
.report-actions :deep(button) {
  height: 38px;
  padding: 0 15px;
  border: 1px solid #cbd6e8;
  border-radius: 8px;
  background: #fff;
  color: #0d1b3d;
  font-weight: 750;
  cursor: pointer;
}

.report-actions :deep(.primary) {
  border-color: #155dfc;
  background: #155dfc;
  color: #fff;
}

@media (max-width: 960px) {
  .report-shell {
    grid-template-columns: 1fr;
  }

  .report-rail {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid #dde5f2;
  }

  .report-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .report-header {
    flex-direction: column;
  }
}
</style>
```

- [ ] **Step 5: Build**

Run: `npm run build`

Expected: PASS. If the build fails on path aliases or imports, fix exact relative import paths before continuing.

## Task 3: Add Layout And Routes

**Files:**
- Create: `frontend/user/src/views/ai-score-report/AiScoreReportLayout.vue`
- Create: seven placeholder page files under `frontend/user/src/views/ai-score-report/`
- Modify: `frontend/user/src/router/index.js`

- [ ] **Step 1: Create `AiScoreReportLayout.vue`**

```vue
<template>
  <div class="report-layout">
    <section v-if="report.loading.value" class="state-view">
      <strong>正在载入评分报告</strong>
      <p>系统正在读取评分、证据、表达、现场呈现和改进建议。</p>
    </section>

    <section v-else-if="report.error.value" class="state-view">
      <strong>{{ report.error.value }}</strong>
      <p>当前会议暂未生成 AI 评分结果。</p>
      <button type="button" @click="report.loadResult">重新加载</button>
    </section>

    <section v-else-if="report.isSessionProgressView.value" class="state-view">
      <strong>{{ report.sessionStatus.value === 'failed' ? 'AI分析未启动' : 'AI 评分进行中' }}</strong>
      <p>当前阶段：{{ report.sessionStage.value || '-' }}，进度 {{ report.sessionProgress.value }}%</p>
      <p v-if="report.sessionErrorMessage.value">{{ report.sessionErrorMessage.value }}</p>
    </section>

    <RouterView v-else />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { provideAiScoreReportContext, useAiScoreReport } from '../../composables/useAiScoreReport'

const report = useAiScoreReport()
provideAiScoreReportContext(report)

onMounted(() => {
  report.loadAvailableTeams()
  report.loadResult()
})
</script>

<style scoped>
.report-layout {
  min-height: calc(100vh - var(--header-height));
  background: #f6f8fc;
}

.state-view {
  min-height: calc(100vh - var(--header-height));
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  padding: 32px;
  color: #0d1b3d;
  text-align: center;
}

.state-view strong {
  font-size: 22px;
}

.state-view p {
  margin: 0;
  color: #66728a;
}

.state-view button {
  height: 38px;
  padding: 0 16px;
  border: 0;
  border-radius: 8px;
  background: #155dfc;
  color: #fff;
  font-weight: 800;
}
</style>
```

- [ ] **Step 2: Create seven placeholder pages**

Use this pattern for each page and change title/subtitle:

```vue
<template>
  <AiScoreReportShell title="总览" subtitle="AI评分会话 · 当前报告总览">
    <AiScoreReportCard>
      <strong>页面正在迁移</strong>
      <p>共享报告壳和数据已就绪，本页内容将在后续任务中迁移。</p>
    </AiScoreReportCard>
  </AiScoreReportShell>
</template>

<script setup>
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreReportCard from '../../components/ai-score/report/AiScoreReportCard.vue'
</script>
```

Create files with these titles:

- `AiScoreReportOverview.vue`: `总览`
- `AiScoreReportDimensions.vue`: `五维评分`
- `AiScoreReportEvidence.vue`: `证据链`
- `AiScoreReportVoice.vue`: `表达节奏`
- `AiScoreReportPresentation.vue`: `现场呈现`
- `AiScoreReportActions.vue`: `改进方案`
- `AiScoreReportJury.vue`: `AI评审团`

- [ ] **Step 3: Modify router**

In `frontend/user/src/router/index.js`, replace the existing AI score report route block with child routes:

```js
  {
    path: '/ai-score/report/:sessionId',
    component: () => import('../views/ai-score-report/AiScoreReportLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: to => `/ai-score/report/${to.params.sessionId}/overview` },
      { path: 'overview', name: 'AiScoreReportOverview', component: () => import('../views/ai-score-report/AiScoreReportOverview.vue') },
      { path: 'dimensions', name: 'AiScoreReportDimensions', component: () => import('../views/ai-score-report/AiScoreReportDimensions.vue') },
      { path: 'evidence', name: 'AiScoreReportEvidence', component: () => import('../views/ai-score-report/AiScoreReportEvidence.vue') },
      { path: 'voice', name: 'AiScoreReportVoice', component: () => import('../views/ai-score-report/AiScoreReportVoice.vue') },
      { path: 'presentation', name: 'AiScoreReportPresentation', component: () => import('../views/ai-score-report/AiScoreReportPresentation.vue') },
      { path: 'actions', name: 'AiScoreReportActions', component: () => import('../views/ai-score-report/AiScoreReportActions.vue') },
      { path: 'jury', name: 'AiScoreReportJury', component: () => import('../views/ai-score-report/AiScoreReportJury.vue') }
    ]
  },
  {
    path: '/ai-score/report-id/:reportId',
    component: () => import('../views/ai-score-report/AiScoreReportLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: to => `/ai-score/report-id/${to.params.reportId}/overview` },
      { path: 'overview', component: () => import('../views/ai-score-report/AiScoreReportOverview.vue') },
      { path: 'dimensions', component: () => import('../views/ai-score-report/AiScoreReportDimensions.vue') },
      { path: 'evidence', component: () => import('../views/ai-score-report/AiScoreReportEvidence.vue') },
      { path: 'voice', component: () => import('../views/ai-score-report/AiScoreReportVoice.vue') },
      { path: 'presentation', component: () => import('../views/ai-score-report/AiScoreReportPresentation.vue') },
      { path: 'actions', component: () => import('../views/ai-score-report/AiScoreReportActions.vue') },
      { path: 'jury', component: () => import('../views/ai-score-report/AiScoreReportJury.vue') }
    ]
  },
```

Keep `/ai-score/:meetingId` on `AiScoreResult.vue` for now. Do not migrate the legacy meeting route in this task.

- [ ] **Step 4: Build**

Run: `npm run build`

Expected: PASS. The route table must compile and the placeholder pages must import correctly.

## Task 4: Implement Overview Page

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`

- [ ] **Step 1: Replace placeholder with overview content**

```vue
<template>
  <AiScoreReportShell title="路演整改周期" :subtitle="subtitle">
    <template #actions>
      <button type="button" class="primary" @click="goActions">新建周期任务</button>
    </template>

    <div class="page-stack">
      <AiScoreMetricStrip :metrics="metrics" />

      <section class="overview-grid">
        <AiScoreReportCard class="score-card">
          <span class="kicker">当前结论</span>
          <h2>{{ verdictTitle }}</h2>
          <p>{{ verdictSummary }}</p>
          <div class="score-row">
            <strong>{{ report.formatNumber(report.overallScore.value, 1) }}</strong>
            <span>/100 · {{ report.scoreLevel.value.label }}</span>
          </div>
        </AiScoreReportCard>

        <AiScoreReportCard tone="warning">
          <span class="kicker">风险与阻塞</span>
          <div class="issue-list">
            <article v-for="issue in topIssues" :key="issue.title">
              <b>{{ issue.title }}</b>
              <p>{{ issue.summary }}</p>
            </article>
          </div>
        </AiScoreReportCard>
      </section>

      <section class="content-grid">
        <AiScoreReportCard>
          <div class="card-head">
            <h3>五维评分概览</h3>
            <RouterLink :to="report.sectionPath('dimensions')">查看五维评分</RouterLink>
          </div>
          <div class="dimension-list">
            <button v-for="dim in report.dimensions.value" :key="dim.key" type="button" @click="openDimension(dim.key)">
              <span>{{ dim.name }}</span>
              <i><em :style="{ width: `${dim.percent}%` }"></em></i>
              <strong>{{ report.formatNumber(dim.score, 1) }}/{{ dim.maxScore }}</strong>
            </button>
          </div>
        </AiScoreReportCard>

        <AiScoreReportCard>
          <div class="card-head">
            <h3>下一步优先处理</h3>
            <RouterLink :to="report.sectionPath('actions')">进入改进方案</RouterLink>
          </div>
          <div class="priority-list">
            <article v-for="item in priorities" :key="item.key">
              <span>{{ item.rank }}</span>
              <div>
                <b>{{ item.title }}</b>
                <p>{{ item.detail }}</p>
              </div>
            </article>
          </div>
        </AiScoreReportCard>
      </section>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreMetricStrip from '../../components/ai-score/report/AiScoreMetricStrip.vue'
import AiScoreReportCard from '../../components/ai-score/report/AiScoreReportCard.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const router = useRouter()
const report = useAiScoreReportContext()

const subtitle = computed(() => `AI评分会话 ${report.result.value.session_no || report.sessionId.value || '-'} · 目标重评 T-3天 · 当前 ${report.reportTrackName.value || '未绑定赛道'}`)
const recoverable = computed(() => report.scoreRecoverySummary.value.recoverable_range || '+18 ~ +24')
const unresolvedP0 = computed(() => report.currentStructuredDeductions.value.filter(item => Number(item.deducted || item.deduction || 0) >= 5).length || report.issues.value.length)
const evidenceConfidence = computed(() => report.structuredEvidenceConfidence.value ? `${Math.round(report.structuredEvidenceConfidence.value * 100)}%` : '待采样')
const juryConsensus = computed(() => report.juryResult.value?.aggregate?.consensus_rate ? `${Math.round(report.juryResult.value.aggregate.consensus_rate * 100)}%` : '待复核')

const metrics = computed(() => [
  { label: '当前分', value: `${report.formatNumber(report.overallScore.value, 1)}/100`, hint: report.scoreLevel.value.label, tone: 'primary' },
  { label: '目标分', value: '88/100', hint: '进入高分档' },
  { label: '可追回分', value: recoverable.value, hint: '基于历史回收率', tone: 'success' },
  { label: '未解决 P0', value: `${unresolvedP0.value} 项`, hint: '高影响未处理', tone: 'danger' },
  { label: '证据置信度', value: evidenceConfidence.value, hint: '较上次 +6%' },
  { label: '评审团共识', value: juryConsensus.value, hint: '中等一致' }
])

const verdictTitle = computed(() => {
  if (report.overallScore.value >= 85) return '当前路演已具备较强竞争力'
  if (report.overallScore.value >= 70) return '基础表现稳定，关键证据仍需补齐'
  if (report.overallScore.value >= 60) return '项目有基础，需要优先修复高影响问题'
  return '当前风险较高，需要重构演示与证据链'
})
const verdictSummary = computed(() => report.scoreLevel.value.text)
const topIssues = computed(() => report.issues.value.slice(0, 3).map((item, index) => ({ title: `问题 ${index + 1}`, summary: item })))
const priorities = computed(() => report.priorities.value.slice(0, 5).map((item, index) => ({
  key: `${index}-${item.issue || item.dimension || item.title}`,
  rank: index + 1,
  title: item.issue || item.title || item.dimension || '提分任务',
  detail: item.suggestion || item.detail || item.dimension || '补齐评分报告指出的关键证据。'
})))

function openDimension(key) {
  report.selectedDimensionKey.value = key
  router.push(report.sectionPath('dimensions'))
}

function goActions() {
  router.push(report.sectionPath('actions'))
}
</script>

<style scoped>
.page-stack { display: grid; gap: 16px; }
.overview-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(320px, .85fr); gap: 16px; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(340px, .72fr); gap: 16px; }
.kicker { color: #155dfc; font-size: 12px; font-weight: 800; }
.score-card h2 { margin: 10px 0; font-size: 26px; }
.score-card p { color: #55627a; line-height: 1.7; }
.score-row { display: flex; align-items: baseline; gap: 10px; margin-top: 18px; }
.score-row strong { color: #155dfc; font-size: 52px; line-height: 1; }
.score-row span { color: #66728a; font-weight: 700; }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.card-head h3 { margin: 0; font-size: 18px; }
.card-head a { color: #155dfc; font-weight: 750; text-decoration: none; }
.issue-list, .priority-list, .dimension-list { display: grid; gap: 10px; }
.issue-list article, .priority-list article { padding: 12px; border: 1px solid #edf1f7; border-radius: 10px; background: #fff; }
.issue-list b, .priority-list b { color: #0d1b3d; }
.issue-list p, .priority-list p { margin: 6px 0 0; color: #66728a; line-height: 1.6; }
.dimension-list button { display: grid; grid-template-columns: 150px minmax(0, 1fr) 90px; gap: 12px; align-items: center; padding: 12px; border: 1px solid #edf1f7; border-radius: 10px; background: #fff; cursor: pointer; }
.dimension-list i { height: 8px; overflow: hidden; border-radius: 999px; background: #e8edf6; }
.dimension-list em { display: block; height: 100%; border-radius: inherit; background: #155dfc; }
.dimension-list strong { text-align: right; font-variant-numeric: tabular-nums; }
.priority-list article { display: grid; grid-template-columns: 32px minmax(0, 1fr); align-items: start; }
.priority-list span { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: #155dfc; color: #fff; font-weight: 800; }
@media (max-width: 1100px) { .overview-grid, .content-grid { grid-template-columns: 1fr; } }
</style>
```

- [ ] **Step 2: Build**

Run: `npm run build`

Expected: PASS. Fix any Composition API `.value` mistakes before continuing.

## Task 5: Implement Dimensions And Evidence Pages

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportDimensions.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportEvidence.vue`

- [ ] **Step 1: Implement dimensions page using existing context**

Use these required sections in `AiScoreReportDimensions.vue`:

```vue
<template>
  <AiScoreReportShell title="五维评分" subtitle="维度拆解与整改映射">
    <div class="page-stack">
      <AiScoreMetricStrip :metrics="metrics" />
      <section class="dimensions-layout">
        <AiScoreReportCard>
          <h3>五维能力地图</h3>
          <button v-for="dim in report.dimensions.value" :key="dim.key" class="dim-row" :class="{ active: dim.key === report.selectedDimensionKey.value }" type="button" @click="report.selectedDimensionKey.value = dim.key">
            <span>{{ dim.name }}</span>
            <i><em :style="{ width: `${dim.percent}%` }"></em></i>
            <strong>{{ report.formatNumber(dim.score, 1) }}/{{ dim.maxScore }}</strong>
          </button>
        </AiScoreReportCard>
        <AiScoreReportCard>
          <h3>当前选中：{{ selectedName }}</h3>
          <div class="focus-score">{{ selectedScore }}</div>
          <p>{{ focusSummary }}</p>
          <div class="focus-actions">
            <RouterLink :to="report.sectionPath('evidence')">查看证据锚点</RouterLink>
            <RouterLink :to="report.sectionPath('actions')">创建团队任务</RouterLink>
          </div>
        </AiScoreReportCard>
      </section>
      <AiScoreReportCard>
        <h3>评分项到任务映射</h3>
        <div class="score-table">
          <div class="score-head"><span>评分项</span><span>得分</span><span>扣分原因</span><span>验收标准</span></div>
          <div v-for="item in report.selectedItems.value" :key="item.name" class="score-row">
            <b>{{ item.name }}</b>
            <strong>{{ item.score ?? '-' }}/{{ item.max_score || item.maxScore || '-' }}</strong>
            <p>{{ item.reason || item.evaluation || item.comment || '暂无评价' }}</p>
            <p>{{ item.improvement || '补齐证据并完成下一轮彩排验证。' }}</p>
          </div>
        </div>
      </AiScoreReportCard>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreMetricStrip from '../../components/ai-score/report/AiScoreMetricStrip.vue'
import AiScoreReportCard from '../../components/ai-score/report/AiScoreReportCard.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()
const selectedName = computed(() => report.selectedDimension.value?.name || '评分维度')
const selectedScore = computed(() => `${report.formatNumber(report.selectedDimension.value?.score, 1)}/${report.selectedDimension.value?.maxScore || 100}`)
const maxGap = computed(() => [...report.dimensions.value].sort((a, b) => a.percent - b.percent)[0])
const focusSummary = computed(() => report.selectedDimension.value?.improvement?.[0] || '该维度需要补齐评分证据、明确表达结构，并在下一轮重评前完成验收。')
const metrics = computed(() => [
  { label: '当前评分', value: `${report.formatNumber(report.overallScore.value, 1)}/100`, hint: report.scoreLevel.value.label, tone: 'primary' },
  { label: '目标评分', value: '88/100', hint: '冲击优秀' },
  { label: '最大差距', value: maxGap.value?.name || '-', hint: '优先修复', tone: 'warning' },
  { label: '最易追回', value: '证据补齐 +8', hint: '回报最高', tone: 'success' },
  { label: '待验收维度', value: `${report.dimensions.value.filter(dim => dim.percent < 80).length} 个`, hint: '需重点突破' }
])
</script>
```

Add scoped CSS using the same class names. Use white cards, `#155dfc` active rows, and single-level grids. Do not introduce new dependencies.

- [ ] **Step 2: Implement evidence page using existing components**

`AiScoreReportEvidence.vue` must use `EvidenceBundlePanel` and `EvidenceAnchorList` to preserve current behavior:

```vue
<template>
  <AiScoreReportShell title="证据链" subtitle="正式证据快照与扣分依据">
    <template #actions>
      <button type="button" class="primary" :disabled="report.evidenceBundleLoading.value" @click="report.handlePrepareEvidenceBundle">
        {{ report.evidenceBundleLoading.value ? '生成中' : '生成证据快照' }}
      </button>
    </template>
    <div class="page-stack">
      <AiScoreMetricStrip :metrics="metrics" />
      <section class="evidence-layout">
        <AiScoreReportCard>
          <h3>证据时间线</h3>
          <button v-for="anchor in anchors" :key="anchor.id" class="anchor-row" type="button">
            <span>{{ anchor.time }}</span>
            <div><b>{{ anchor.title }}</b><p>{{ anchor.summary }}</p></div>
          </button>
        </AiScoreReportCard>
        <AiScoreReportCard>
          <h3>当前证据详情</h3>
          <img v-if="selectedFrame?.image_url" :src="selectedFrame.image_url" alt="评分关键帧" class="frame-img" />
          <AiScoreEmptyState v-else title="暂无关键帧" description="该报告暂未关联可展示的视觉证据。" />
          <p class="frame-caption">{{ selectedFrame?.caption || '请选择左侧证据点查看详情。' }}</p>
        </AiScoreReportCard>
      </section>
      <EvidenceBundlePanel v-if="report.sessionId.value" :bundle="report.evidenceBundle.value" :loading="report.evidenceBundleLoading.value" @prepare="report.handlePrepareEvidenceBundle" />
      <EvidenceAnchorList :anchors="report.structuredEvidenceAnchors.value" />
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed } from 'vue'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreMetricStrip from '../../components/ai-score/report/AiScoreMetricStrip.vue'
import AiScoreReportCard from '../../components/ai-score/report/AiScoreReportCard.vue'
import AiScoreEmptyState from '../../components/ai-score/report/AiScoreEmptyState.vue'
import EvidenceBundlePanel from '../../components/ai-score/EvidenceBundlePanel.vue'
import EvidenceAnchorList from '../../components/ai-score/EvidenceAnchorList.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()
const selectedFrame = computed(() => report.selectedEvidenceFrame.value)
const anchors = computed(() => report.structuredEvidenceAnchors.value.slice(0, 8).map((item, index) => ({
  id: item.id || `anchor-${index}`,
  time: item.time || item.timeLabel || '-',
  title: item.title || item.dimension || '证据锚点',
  summary: item.summary || item.reason || item.detail || '暂无证据说明。'
})))
const metrics = computed(() => [
  { label: '证据快照', value: report.evidenceBundle.value?.snapshotStatus || '待生成', hint: '用于本轮正式评分' },
  { label: '转写片段', value: report.asrSegments.value.length || '-', hint: '语音证据' },
  { label: '关键帧', value: report.evidenceFrames.value.length || '-', hint: '画面证据' },
  { label: '证据锚点', value: report.structuredEvidenceAnchors.value.length || '-', hint: '可定位依据', tone: 'primary' },
  { label: '弱证据阻塞', value: report.currentStructuredDeductions.value.length || 0, hint: '影响提分', tone: 'warning' }
])
</script>
```

Add scoped CSS for `.page-stack`, `.evidence-layout`, `.anchor-row`, `.frame-img`, and `.frame-caption`.

- [ ] **Step 3: Build**

Run: `npm run build`

Expected: PASS.

## Task 6: Implement Voice And Presentation Pages

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportVoice.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportPresentation.vue`

- [ ] **Step 1: Voice page content**

Implement `AiScoreReportVoice.vue` with these sections:

- Metric strip: expression stability, speech rate, severe pauses, longest pause, filler count, recoverable score.
- Left card: selected or top pause sentence list from `report.topPauses.value`.
- Right card: coaching advice from `report.expressionCoaching.value` and `report.expressionCoachingError.value`.
- Bottom card: simple rehearsal list derived from `expressionCoaching.training` if present, otherwise a fallback training message.

Use computed values:

```js
const speechRate = computed(() => report.formatNumber(report.speech.value.speech_rate?.global_chars_per_minute, 1))
const severePauses = computed(() => report.topPauses.value.filter(item => item.severity === '严重').length)
const moments = computed(() => report.topPauses.value.slice(0, 8).map((pause, index) => ({
  id: `pause-${index}`,
  time: report.formatTime(pause.position_seconds),
  title: `${report.formatNumber(pause.duration, 1)}s ${pause.severity || '停顿'}`,
  text: report.clipText(`${pause.context_before || ''} ${pause.context_after || ''}`, 120),
  action: '拆成“结论、证据、价值”三拍重新练习。'
})))
```

- [ ] **Step 2: Presentation page content**

Implement `AiScoreReportPresentation.vue` with these sections:

- Metric strip: visual average, audio-video conflicts, key frames, main screen type, recoverable score.
- Left card: selected key frame from `report.selectedEvidenceFrame.value`.
- Middle card: contradiction list from `report.contradictions.value`.
- Right card: presentation coaching summary from `report.presentationCoaching.value` and fallback text.
- Bottom card: next rehearsal plan derived from `presentationCoaching.actions` or `presentationCoaching.phases` if present.

Use safe fallbacks and do not assume model fields exist.

- [ ] **Step 3: Build**

Run: `npm run build`

Expected: PASS.

## Task 7: Implement Actions And Jury Pages

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportActions.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportJury.vue`

- [ ] **Step 1: Actions page must preserve team task generation**

Implement `AiScoreReportActions.vue` with:

- Metric strip: recoverable score, selected work items, P0 tasks, today tasks, review date, evidence confidence.
- Team selector bound to `report.selectedTeamIdForTasks.value`.
- Work item checkbox list bound to `report.selectedReportWorkItemIds.value`.
- Primary button calls `report.createTeamTasksFromReport`.
- If `report.createdTeamTaskCount.value > 0`, show a button calling `report.goTeamScoreWorkItems`.
- Priority list from `report.priorities.value`.

The checkbox binding must look like:

```vue
<label v-for="item in report.reportWorkItemDrafts.value" :key="item.id" class="workitem-row">
  <input v-model="report.selectedReportWorkItemIds.value" type="checkbox" :value="item.id" />
  <span>{{ item.badge }}</span>
  <div>
    <b>{{ item.title }}</b>
    <p>{{ item.description }}</p>
  </div>
</label>
```

- [ ] **Step 2: Jury page must preserve existing jury component**

Implement `AiScoreReportJury.vue` using the existing component first:

```vue
<template>
  <AiScoreReportShell title="AI评审团" subtitle="评审团只做复核，不修改基础分">
    <AiScoreMetricStrip :metrics="metrics" />
    <JuryPerspectivePanel
      :review="report.juryResult.value || { status: 'empty' }"
      :loading="report.juryLoading.value"
      :starting="report.juryStarting.value"
      :error="report.juryError.value"
      :can-start="Boolean(report.sessionId.value || report.effectiveMeetingId.value)"
      @start="report.startJuryReview"
    />
  </AiScoreReportShell>
</template>

<script setup>
import { computed } from 'vue'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreMetricStrip from '../../components/ai-score/report/AiScoreMetricStrip.vue'
import JuryPerspectivePanel from '../../components/ai-score/JuryPerspectivePanel.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()
const juryAverage = computed(() => report.juryResult.value?.jury?.trimmed_average_score || '-')
const juryDiff = computed(() => report.juryResult.value?.jury?.score_diff_from_official)
const metrics = computed(() => [
  { label: '官方评分', value: `${report.formatNumber(report.overallScore.value, 1)}/100`, hint: '基础分不修改', tone: 'primary' },
  { label: '评审团均分', value: juryAverage.value, hint: '去高低分后' },
  { label: '分差', value: juryDiff.value == null ? '-' : report.formatSignedNumber(juryDiff.value, 1), hint: '相对官方' },
  { label: '评委数', value: report.juryResult.value?.members?.length || 0, hint: '已生成评委' },
  { label: '共识度', value: report.juryResult.value?.aggregate?.consensus_rate ? `${Math.round(report.juryResult.value.aggregate.consensus_rate * 100)}%` : '-', hint: '共识问题' }
])
</script>
```

- [ ] **Step 3: Build**

Run: `npm run build`

Expected: PASS.

## Task 8: Compatibility Wrapper And Cleanup

**Files:**
- Modify: `frontend/user/src/views/AiScoreResult.vue`
- Optionally modify: `frontend/user/src/router/index.js`

- [ ] **Step 1: Convert `AiScoreResult.vue` to redirect wrapper only after new routes pass build**

Replace the old file with:

```vue
<template>
  <div class="ai-score-redirect">正在进入新版 AI 评分报告...</div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  if (route.params.sessionId) {
    router.replace(`/ai-score/report/${route.params.sessionId}/overview`)
    return
  }
  if (route.params.reportId) {
    router.replace(`/ai-score/report-id/${route.params.reportId}/overview`)
    return
  }
  if (route.params.meetingId) {
    router.replace(`/ai-score/${route.params.meetingId}/overview`)
  }
})
</script>

<style scoped>
.ai-score-redirect {
  min-height: calc(100vh - var(--header-height));
  display: grid;
  place-items: center;
  color: #66728a;
  background: #f6f8fc;
}
</style>
```

- [ ] **Step 2: Add child routes for `/ai-score/:meetingId`**

Change the legacy route to the new layout with the same children as report-id routes:

```js
  {
    path: '/ai-score/:meetingId',
    component: () => import('../views/ai-score-report/AiScoreReportLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: to => `/ai-score/${to.params.meetingId}/overview` },
      { path: 'overview', component: () => import('../views/ai-score-report/AiScoreReportOverview.vue') },
      { path: 'dimensions', component: () => import('../views/ai-score-report/AiScoreReportDimensions.vue') },
      { path: 'evidence', component: () => import('../views/ai-score-report/AiScoreReportEvidence.vue') },
      { path: 'voice', component: () => import('../views/ai-score-report/AiScoreReportVoice.vue') },
      { path: 'presentation', component: () => import('../views/ai-score-report/AiScoreReportPresentation.vue') },
      { path: 'actions', component: () => import('../views/ai-score-report/AiScoreReportActions.vue') },
      { path: 'jury', component: () => import('../views/ai-score-report/AiScoreReportJury.vue') }
    ]
  },
```

- [ ] **Step 3: Build**

Run: `npm run build`

Expected: PASS.

## Task 9: Final Verification

**Files:**
- No code changes unless verification reveals defects.

- [ ] **Step 1: Build verification**

Run: `npm run build`

Workdir: `frontend/user`

Expected: Build completes without Vue template or route errors.

- [ ] **Step 2: Route smoke test by static inspection**

Verify `frontend/user/src/router/index.js` contains routes for:

- `/ai-score/report/:sessionId/overview`
- `/ai-score/report/:sessionId/dimensions`
- `/ai-score/report/:sessionId/evidence`
- `/ai-score/report/:sessionId/voice`
- `/ai-score/report/:sessionId/presentation`
- `/ai-score/report/:sessionId/actions`
- `/ai-score/report/:sessionId/jury`
- `/ai-score/report-id/:reportId/overview`
- `/ai-score/:meetingId/overview`

- [ ] **Step 3: Manual browser verification if dev server is available**

Run: `npm run dev`

Workdir: `frontend/user`

Open one known report URL and verify:

- Left nav renders seven pages.
- Refreshing a child page still loads report data.
- Download PDF button calls without JS error.
- Actions page can select work items.
- Jury page can show empty/loading/error states.

- [ ] **Step 4: Self-review changed files**

Check:

- No internal AI scoring fields are displayed.
- No backend endpoint was changed.
- No route loops exist.
- New pages use `useAiScoreReportContext()` instead of requesting full report again.
- Empty states exist for missing frames, missing anchors, missing coaching, and missing jury.

## Known Follow-Ups After First Ship

1. Replace remaining simplistic placeholder visualizations with richer tables and timelines matching the prototype screenshots.
2. Move chart-specific logic into page-level components only where charts are still needed.
3. Add Playwright coverage for seven report routes once stable report fixture IDs exist.
4. Remove compatibility wrapper if no external links still point to old route names.
