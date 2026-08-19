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
import {
  buildVisualFrameEndpoints,
  frameSeconds,
  normalizeVisualFrame
} from '../utils/aiScoreFrameMatching'
import { buildLegacyAiResultEndpoints } from '../utils/aiScoreLegacyResult'
import { buildRuleEngineReport } from '../utils/aiScoreRuleEngineReport'
import { buildTrainingTasks } from '../utils/aiScoreTrainingTasks'
import { buildAuthoritativeDimensions } from '../utils/aiScoreDimensions'
import { buildTodosPresentation } from '../utils/aiScoreTodosPresentation'
import { normalizeScoreProjection } from '../utils/aiScoreProjection'
import { normalizeLossLedger } from '../utils/aiScoreLossLedger'
import { normalizeCoverage } from '../utils/aiScoreCoverage'

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
  const effectiveReportId = computed(() => reportId.value || result.value.reportId || result.value.report_id)

  const loading = ref(true)
  const error = ref('')
  const result = ref({})
  const effectiveSessionId = computed(() => sessionId.value || result.value.session_id || result.value.sessionId || result.value.session?.id || result.value.session?.sessionId)
  const effectiveMeetingId = computed(() => result.value.meeting_id || result.value.meetingId || meetingId.value)
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
  const scoreAuthority = computed(() => String(
    result.value.scoreAuthority
    || result.value.score_authority
    || aiScore.value.scoreAuthority
    || aiScore.value.score_authority
    || ''
  ))
  const overallScore = computed(() => {
    if (scoreAuthority.value === 'review_required') return null
    const raw = result.value.overallScore ?? result.value.overall_score ?? aiScore.value.overall_score
    if (raw === null || raw === undefined || raw === '') return null
    const number = Number(raw)
    return Number.isFinite(number) ? number : null
  })
  const scoreCalibration = computed(() => result.value.score_calibration || {})
  const rawOverallScore = computed(() => {
    const raw = aiScore.value.raw_overall_score
      ?? result.value.llmRawScore
      ?? result.value.llm_raw_score
      ?? scoreCalibration.value.original_score
      ?? overallScore.value
    if (raw === null || raw === undefined || raw === '') return null
    const number = Number(raw)
    return Number.isFinite(number) ? number : null
  })
  const scoreLevel = computed(() => {
    if (scoreAuthority.value === 'review_required' || overallScore.value == null) {
      return { label: '待复核', text: '规则分不可发布，暂不展示正式 AI 分（大模型分仅作诊断）' }
    }
    if (overallScore.value >= 85) return { label: '优秀', text: '具备示范性，可继续打磨答辩细节' }
    if (overallScore.value >= 70) return { label: '良好', text: '竞争力较强，需补齐关键证据' }
    if (overallScore.value >= 60) return { label: '待提升', text: '基础完整，需要专项优化' }
    return { label: '风险较高', text: '建议重构路演结构与演示稳定性' }
  })
  const dimensions = computed(() => {
    const officialDimensions = scoreCalibration.value.official_rubric?.dimensions || scoreCalibration.value.officialRubric?.dimensions
    return buildAuthoritativeDimensions({
      authoritative: aiScore.value.dimensions,
      diagnostic: officialDimensions
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
  const ruleEngineReport = computed(() => buildRuleEngineReport(result.value || {}))
  const trainingTasks = computed(() => buildTrainingTasks(result.value || {}))
  const contractVersion = computed(() => firstPresent(result.value.contractVersion, result.value.contract_version, ''))
  const lossLedger = computed(() => normalizeLossLedger(firstPresent(
    result.value.lossLedger,
    result.value.loss_ledger,
    result.value.lossLedgerJson,
    result.value.loss_ledger_json
  )))
  const coverageSummary = computed(() => normalizeCoverage(firstPresent(
    result.value.coverageSummary,
    result.value.coverage_summary,
    result.value.coverageSummaryJson,
    result.value.coverage_summary_json
  )))
  const remediationTasks = computed(() => arrayFrom(firstPresent(
    result.value.remediationTasks,
    result.value.remediation_tasks
  )))
  const taskVerifications = computed(() => arrayFrom(firstPresent(
    result.value.taskVerifications,
    result.value.task_verifications
  )))
  const todoPortfolioStatus = computed(() => firstPresent(
    result.value.todoPortfolioStatus,
    result.value.todo_portfolio_status,
    coverageSummary.value.status,
    'incomplete'
  ))
  const actionPlan = computed(() => arrayFrom(firstPresent(
    contractVersion.value === 'ai-score-report-v3' && remediationTasks.value.length ? remediationTasks.value : undefined,
    result.value.actionPlan,
    result.value.action_plan,
    aiScore.value.action_plan,
    aiScore.value.actionPlan
  )))
  const scoreProjection = computed(() => normalizeScoreProjection(firstPresent(
    result.value.scoreProjection,
    result.value.score_projection,
    result.value.scoreProjectionJson,
    result.value.score_projection_json
  )))
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
  const asrSegments = computed(() => arrayFrom(firstPresent(
    result.value.asrSegments,
    result.value.asr_segments,
    result.value.asr?.segments
  )))
  const speakerMappings = computed(() => arrayFrom(firstPresent(
    result.value.speakerMappings,
    result.value.speaker_mappings
  )))
  const speakerAttributionStatus = computed(() => String(firstPresent(
    result.value.speakerAttributionStatus,
    result.value.speaker_attribution_status,
    'LEGACY'
  ) || 'LEGACY').toUpperCase())
  const stablePeople = computed(() => arrayFrom(firstPresent(
    result.value.stablePeople,
    result.value.stable_people
  )))
  const finalSpeakerSegments = computed(() => arrayFrom(firstPresent(
    result.value.finalSpeakerSegments,
    result.value.final_speaker_segments
  )))

  async function updateSpeakerIdentity(rawSpeaker, displayName, roleName) {
    const sessionKey = effectiveSessionId.value
    if (!sessionKey) throw new Error('当前报告缺少评分会话 ID')
    const raw = String(rawSpeaker || '').trim()
    if (!raw) throw new Error('原始发言人标签不能为空')
    const response = await request.patch(
      `/api/ai-score/sessions/${sessionKey}/speakers/${encodeURIComponent(raw)}`,
      { displayName, roleName }
    )
    const mapping = response?.data
    if (!mapping) throw new Error('发言人修正结果为空')
    const current = speakerMappings.value.filter(item => String(firstPresent(
      item.rawSpeaker,
      item.raw_speaker,
      ''
    )) !== raw)
    result.value = {
      ...result.value,
      speakerMappings: [...current, mapping]
    }
    return mapping
  }

  const recomputingSpeakerAttribution = ref(false)

  async function recomputeSpeakerAttribution() {
    const sessionKey = effectiveSessionId.value
    if (!sessionKey) throw new Error('当前报告缺少评分会话 ID')
    if (recomputingSpeakerAttribution.value) return null
    recomputingSpeakerAttribution.value = true
    try {
      const response = await request.post(
        `/api/ai-score/sessions/${sessionKey}/recompute-speaker-attribution`,
        {}
      )
      const report = response?.data
      if (!report) throw new Error('人物归属重算结果为空')
      // Merge into current report state so transcript / stable people refresh immediately.
      result.value = {
        ...result.value,
        ...report,
        speakerAttributionStatus: report.speakerAttributionStatus
          ?? report.speaker_attribution_status
          ?? result.value.speakerAttributionStatus,
        speakerAttributionRevision: report.speakerAttributionRevision
          ?? report.speaker_attribution_revision
          ?? result.value.speakerAttributionRevision,
        stablePeople: report.stablePeople ?? report.stable_people ?? result.value.stablePeople,
        finalSpeakerSegments: report.finalSpeakerSegments
          ?? report.final_speaker_segments
          ?? result.value.finalSpeakerSegments,
        asrSegments: report.asrSegments ?? report.asr_segments ?? result.value.asrSegments,
        speakerMappings: report.speakerMappings
          ?? report.speaker_mappings
          ?? result.value.speakerMappings
      }
      ElMessage.success('人物归属已重算')
      return report
    } catch (error) {
      const message = error?.response?.data?.message
        || error?.message
        || '人物归属重算失败'
      ElMessage.error(message)
      throw error
    } finally {
      recomputingSpeakerAttribution.value = false
    }
  }
  const mediaPlayback = computed(() => result.value.mediaPlayback || result.value.media_playback || {})
  const stability = computed(() => result.value.stability || {})
  const verifyClaims = computed(() => result.value.verifyClaims || result.value.verify_claims || [])
  const taskBook = computed(() => result.value.taskBook || result.value.task_book || { published: false, items: [] })
  const scoreGap = computed(() => result.value.scoreGap || result.value.score_gap || {})
  const deliberation = computed(() => result.value.deliberation || {})
  const teacherConfirmed = computed(() => Boolean(
    result.value.teacherConfirmed ?? result.value.teacher_confirmed ?? deliberation.value.teacherConfirmed
  ))
  const challenges = computed(() => {
    const raw = result.value.challenges || { scanned: false, items: [] }
    return {
      scanned: raw.scanned === true,
      note: raw.note || '',
      items: Array.isArray(raw.items) ? raw.items : [],
      acceptedAdjustment: raw.acceptedAdjustment ?? raw.accepted_adjustment ?? null,
      adjustedDraftScore: raw.adjustedDraftScore ?? raw.adjusted_draft_score ?? null
    }
  })
  const pitchChapters = computed(() => arrayFrom(firstPresent(
    aiScore.value.pitch_structure_benchmark,
    aiScore.value.pitchStructureBenchmark
  )))
  const visualFrameAnalyses = computed(() => arrayFrom(firstPresent(
    video.value.per_frame,
    video.value.perFrame,
    videoAgg.value.per_frame,
    videoAgg.value.perFrame
  )).map(normalizeVisualFrameAnalysis))
  const pauseTotal = computed(() => speech.value.pauses?.total_pauses || 0)
  const longestPause = computed(() => formatNumber(speech.value.pauses?.longest_pause, 1))
  const fillerTotal = computed(() => speech.value.fillers?.total_fillers || 0)
  const topPauses = computed(() => (speech.value.pauses?.details || [])
    .filter(item => Number(item.duration || 0) >= 3)
    .sort((a, b) => Number(b.duration || 0) - Number(a.duration || 0))
    .slice(0, 8))

  const evidenceFrames = computed(() => visualFrames.value.map((frame, index) => {
    const analysis = visualAnalysisForFrame(frame, index, visualFrameAnalyses.value)
    const caption = firstPresent(
      frame.caption,
      frame.description,
      frame.ocr_text,
      frame.ocrText,
      analysis?.summary,
      analysis?.ocrText,
      ''
    )
    const screenType = firstPresent(frame.screen_type, frame.screenType, analysis?.screenType, frame.frame_type, frame.frameType)
    return {
      ...frame,
      timeLabel: formatTime(frameSeconds(frame)),
      title: frame.title || caption || screenType || '关键帧',
      caption: caption || '暂无画面说明。',
      ocr_text: firstPresent(frame.ocr_text, frame.ocrText, analysis?.ocrText, ''),
      screen_type: screenType,
      analysis
    }
  }))

  const legacyReportWorkItemDrafts = computed(() => {
    const trainingTaskDrafts = trainingTasks.value.map((item, index) => ({
      id: item.id || `training-task-${index}`,
      badge: '训',
      title: item.title || `训练任务 ${index + 1}`,
      description: item.trainingAction || item.correspondingDeduction || '补齐评分报告指出的证据缺口。',
      stageKey: 'ROADSHOW',
      priority: item.priority === 'P0' ? 'HIGH' : item.priority === 'P2' ? 'LOW' : 'MEDIUM',
      ownerRole: item.ownerRole,
      acceptanceCriteria: item.acceptanceCriteria,
      expectedRecoverPoints: item.expectedRecoverPoints,
      timeSuggestion: item.timeSuggestion,
      evidenceAnchorIds: item.evidenceAnchorIds
    }))
    if (trainingTaskDrafts.length) return trainingTaskDrafts.slice(0, 8)

    const deductionDrafts = currentStructuredDeductions.value.slice(0, 4).map((item, index) => ({
      id: `deduction-${index}`,
      badge: '扣',
      title: `处理扣分项：${item.title || item.dimension || item.name || '关键问题'}`,
      description: item.reason || item.detail || item.improvement || item.suggestion || '补齐评分报告指出的证据缺口。',
      stageKey: 'ROADSHOW',
      priority: Number(item.deducted || item.deduction || 0) >= 5 ? 'HIGH' : 'MEDIUM'
    }))
    if (deductionDrafts.length) return deductionDrafts.slice(0, 8)

    const rubricDrafts = []
    dimensions.value.forEach(dimension => {
      ;(dimension.items || []).forEach((item, index) => {
        const score = Number(firstPresent(item.score, item.value, item.current_score, item.currentScore, 0))
        const maxScore = Number(firstPresent(item.max_score, item.maxScore, item.full_score, item.fullScore, 0))
        const reason = firstPresent(item.reason, item.evaluation, item.comment, item.detail, item.issue, item.description, '')
        if (!reason && !(maxScore && score < maxScore)) return
        rubricDrafts.push({
          id: `rubric-${dimension.key}-${index}`,
          badge: '评',
          title: `处理评分项：${firstPresent(item.name, item.title, item.item, dimension.name || '评分项')}`,
          description: firstPresent(item.suggestion, item.improvement, item.action, item.fix, reason, '补齐评分表指出的证据缺口。'),
          stageKey: 'ROADSHOW',
          priority: maxScore && maxScore - score >= 5 ? 'HIGH' : 'MEDIUM'
        })
      })
    })
    if (rubricDrafts.length) return rubricDrafts.slice(0, 8)

    return priorities.value.slice(0, 4).map((item, index) => ({
      id: `priority-${index}`,
      badge: '改',
      title: `处理优先问题：${firstPresent(item.issue, item.title, item.dimension, '关键问题')}`,
      description: firstPresent(item.suggestion, item.improvement, item.detail, item.reason, '补齐评分报告指出的关键证据，并在下一轮彩排中验证。'),
      stageKey: 'ROADSHOW',
      priority: index < 2 ? 'HIGH' : 'MEDIUM'
    }))
  })

  const unifiedTodos = computed(() => buildTodosPresentation({
    contractVersion: contractVersion.value,
    remediationTasks: remediationTasks.value,
    coverageSummary: coverageSummary.value,
    trainingTasks: trainingTasks.value,
    currentStructuredDeductions: currentStructuredDeductions.value,
    reportWorkItemDrafts: legacyReportWorkItemDrafts.value,
    actionPlan: actionPlan.value,
    taskBook: taskBook.value
  }).items)

  const reportWorkItemDrafts = computed(() => unifiedTodos.value.map((item, index) => ({
    id: item.id || `unified-todo-${index}`,
    badge: item.scoreLinked ? '训' : '改',
    title: item.title || `整改任务 ${index + 1}`,
    description: item.how || item.why || '按报告验收标准完成整改。',
    stageKey: 'ROADSHOW',
    priority: item.priority === 'P0' ? 'HIGH' : item.priority === 'P2' ? 'LOW' : 'MEDIUM',
    ownerRole: item.ownerRole,
    acceptanceCriteria: arrayFrom(item.doneLines).join('|'),
    expectedRecoverPoints: item.scoreLinked ? item.recoverPoints : null,
    timeSuggestion: item.timeSuggestion,
    evidenceAnchorIds: item.evidenceAnchorIds
  })))

  const navItems = computed(() => [
    { key: 'result', label: '结果', count: '' },
    { key: 'todos', label: '待办', count: unifiedTodos.value.length || '' },
    { key: 'why', label: '依据', count: structuredEvidenceAnchors.value.length || evidenceFrames.value.length || '' }
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
        const reportLoaded = await loadSessionOrReportResult()
        if (!reportLoaded) {
          loading.value = false
          return
        }
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

  async function resolveChallenge(challengeId, action, reason = '') {
    const sid = effectiveSessionId.value
    if (!sid) throw new Error('当前报告没有会话')
    const response = await request.post(
      `/api/ai-score/sessions/${sid}/challenges/${encodeURIComponent(challengeId)}/resolve`,
      { action, reason }
    )
    result.value = normalizeCompetitionDuration(normalizeLegacyResult(response.data || response))
    return result.value
  }

  async function hangTaskBookEvidence(itemIndex, evidence) {
    const sid = effectiveSessionId.value
    if (!sid) throw new Error('当前报告没有会话')
    const response = await request.post(
      `/api/ai-score/sessions/${sid}/task-book/items/${itemIndex}/hang`,
      { evidence }
    )
    result.value = normalizeCompetitionDuration(normalizeLegacyResult(response.data || response))
    return result.value
  }

  async function updateRemediationTaskStatus(task, status) {
    const reportKey = effectiveReportId.value
    const taskRecordId = task?.taskRecordId || task?.task_record_id
    if (!reportKey || !taskRecordId) throw new Error('当前任务缺少可更新的持久化标识')
    await request.patch(`/api/ai-score/reports/${reportKey}/remediation-tasks/${taskRecordId}/status`, { status })
    await loadResult()
  }

  async function submitRemediationTaskForRerun(task) {
    const reportKey = effectiveReportId.value
    const taskRecordId = task?.taskRecordId || task?.task_record_id
    if (!reportKey || !taskRecordId) throw new Error('当前任务缺少可更新的持久化标识')
    await request.patch(`/api/ai-score/reports/${reportKey}/remediation-tasks/${taskRecordId}/status`, { status: 'submitted' })
    await request.patch(`/api/ai-score/reports/${reportKey}/remediation-tasks/${taskRecordId}/status`, { status: 'awaiting_rerun' })
    await loadResult()
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
        if (status === 'failed') {
          stopProgressPolling()
          return false
        }
        if (['created', 'uploaded', 'scoring'].includes(status) || (status !== 'completed' && !statusRes.data.reportId)) {
          startProgressPolling(sessionId.value)
          return false
        }
      }
    }
    const endpoint = sessionId.value
      ? `/api/ai-score/reports/by-session/${sessionId.value}`
      : `/api/ai-score/reports/by-report/${reportId.value}`
    const sessionReport = await request.get(endpoint)
    result.value = normalizeCompetitionDuration(normalizeLegacyResult(sessionReport.data || sessionReport))
    await enrichWithLegacyAiResult()
    return true
  }

  async function loadLegacyMeetingResult() {
    try {
      const reportRes = await request.get(`/api/ai-score/reports/by-meeting/${meetingId.value}`, { silentError: true })
      result.value = normalizeCompetitionDuration(normalizeLegacyResult(reportRes.data || reportRes))
      await enrichWithLegacyAiResult()
      return
    } catch {
      // Older reports may only exist in the legacy AI result endpoint.
    }
    const res = await fetch(`/api/ai/result/${meetingId.value}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    result.value = normalizeCompetitionDuration(normalizeLegacyResult(await res.json()))
  }

  async function enrichWithLegacyAiResult() {
    if (hasRichAiEvidence(result.value)) return
    const endpoints = buildLegacyAiResultEndpoints({
      result: result.value,
      meetingId: meetingId.value,
      sessionId: sessionId.value
    })
    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint)
        if (!res.ok) continue
        const legacy = normalizeCompetitionDuration(normalizeLegacyResult(await res.json()))
        result.value = mergeLegacyAnalysisFields(result.value, legacy)
        if (hasRichAiEvidence(result.value)) return
      } catch {
        // Legacy enrichment is best effort for historical reports.
      }
    }
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
    if (!effectiveSessionId.value) return
    try {
      evidenceBundle.value = await getEvidenceBundle(effectiveSessionId.value)
    } catch {
      evidenceBundle.value = { sessionId: effectiveSessionId.value, snapshotStatus: 'missing' }
    }
  }

  async function handlePrepareEvidenceBundle() {
    if (!effectiveSessionId.value) return
    evidenceBundleLoading.value = true
    try {
      evidenceBundle.value = await prepareEvidenceBundle(effectiveSessionId.value)
      ElMessage.success('证据快照已生成')
    } finally {
      evidenceBundleLoading.value = false
    }
  }

  async function loadVisualFrames() {
    if (!effectiveSessionId.value && !effectiveMeetingId.value) {
      visualFrames.value = []
      return
    }
    const endpoints = buildVisualFrameEndpoints({
      effectiveSessionId: effectiveSessionId.value,
      effectiveMeetingId: effectiveMeetingId.value,
      sourceType: reportSourceType.value
    })
    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const frames = (data.frames || [])
          .map((frame, index) => normalizeVisualFrame(frame, index, data.session_id || effectiveSessionId.value))
          .sort((a, b) => frameSeconds(a) - frameSeconds(b))
        if (frames.length) {
          visualFrames.value = frames
          return
        }
      } catch {
        // Try the next allowed source. Uploaded-video reports intentionally do not fall back to meeting frames.
      }
    }
    visualFrames.value = []
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
      if (effectiveSessionId.value) juryResult.value = sanitizeInternalAiScoreFields(await getJuryReviewBySession(effectiveSessionId.value))
      else if (effectiveMeetingId.value) juryResult.value = sanitizeInternalAiScoreFields(await getLegacyJuryReviewByMeeting(effectiveMeetingId.value))
      else juryResult.value = { status: 'empty' }
    } catch (error) {
      juryResult.value = { status: 'empty' }
      juryError.value = requestErrorMessage(error, 'AI评审团复核暂未生成。')
    } finally {
      juryLoading.value = false
    }
  }

  async function startJuryReview() {
    juryStarting.value = true
    juryError.value = ''
    try {
      if (effectiveSessionId.value) juryResult.value = sanitizeInternalAiScoreFields(await startJuryReviewBySession(effectiveSessionId.value))
      else if (effectiveMeetingId.value) juryResult.value = sanitizeInternalAiScoreFields(await startLegacyJuryReviewByMeeting(effectiveMeetingId.value))
      if (isJuryProcessing(juryResult.value)) {
        juryResult.value = sanitizeInternalAiScoreFields(await pollJuryReviewResult())
      }
    } catch (error) {
      juryError.value = requestErrorMessage(error, 'AI评审团复核启动失败，请稍后重试。')
    } finally {
      juryStarting.value = false
    }
  }

  async function pollJuryReviewResult(maxAttempts = 20, intervalMs = 3000) {
    let latest = juryResult.value
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await wait(intervalMs)
      if (effectiveSessionId.value) latest = await getJuryReviewBySession(effectiveSessionId.value)
      else if (effectiveMeetingId.value) latest = await getLegacyJuryReviewByMeeting(effectiveMeetingId.value)
      juryResult.value = sanitizeInternalAiScoreFields(latest)
      if (!isJuryProcessing(juryResult.value)) return juryResult.value
    }
    return juryResult.value
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
    const pdfUrl = effectiveSessionId.value
      ? `/api/ai-score/reports/by-session/${effectiveSessionId.value}/pdf`
      : effectiveMeetingId.value
        ? `/api/ai-score/pdf/${effectiveMeetingId.value}`
        : ''
    if (!pdfUrl) {
      ElMessage.warning('当前报告暂未关联可下载的 PDF')
      return
    }
    try {
      ElMessage.info('正在生成下载…')
      const blob = await request.get(pdfUrl, { responseType: 'blob', timeout: 60000 })
      // 后端失败时有时仍返回 JSON blob，避免保存成坏 PDF
      if (blob && String(blob.type || '').includes('json')) {
        const text = await blob.text()
        let message = '报告 PDF 暂不可用'
        try {
          const parsed = JSON.parse(text)
          message = parsed?.message || parsed?.msg || message
        } catch {
          /* keep default */
        }
        ElMessage.warning(message)
        return
      }
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = `${result.value.session_no || result.value.sessionNo || `AI评分报告_${effectiveSessionId.value || effectiveMeetingId.value}`}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
      ElMessage.success('已开始下载报告')
    } catch (error) {
      let message = error?.message || '下载失败，请稍后重试'
      const data = error?.response?.data
      try {
        if (typeof data === 'string' && data.trim()) {
          message = data.trim()
        } else if (data instanceof Blob) {
          const text = (await data.text()).trim()
          if (text) message = text.length > 120 ? text.slice(0, 120) : text
        }
      } catch {
        /* keep message */
      }
      if (/status code 404/i.test(message)) {
        message = '报告 PDF 不存在或路径未配置，请稍后重试或联系管理员'
      }
      ElMessage.error(message)
    }
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
    effectiveReportId,
    effectiveSessionId,
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
    scoreAuthority,
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
    ruleEngineReport,
    trainingTasks,
    actionPlan,
    scoreProjection,
    contractVersion,
    lossLedger,
    coverageSummary,
    remediationTasks,
    taskVerifications,
    todoPortfolioStatus,
    unifiedTodos,
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
    speakerMappings,
    speakerAttributionStatus,
    stablePeople,
    finalSpeakerSegments,
    updateSpeakerIdentity,
    recomputingSpeakerAttribution,
    recomputeSpeakerAttribution,
    mediaPlayback,
    stability,
    verifyClaims,
    taskBook,
    scoreGap,
    deliberation,
    teacherConfirmed,
    challenges,
    hangTaskBookEvidence,
    resolveChallenge,
    pitchChapters,
    pauseTotal,
    longestPause,
    fillerTotal,
    topPauses,
    evidenceFrames,
    reportWorkItemDrafts,
    navItems,
    loadResult,
    updateRemediationTaskStatus,
    submitRemediationTaskForRerun,
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
  const actionPlan = parseJsonValue(data.actionPlan ?? data.actionPlanJson ?? data.action_plan ?? data.ai_score?.action_plan, [])
  const scoreProjection = parseJsonValue(data.scoreProjection ?? data.scoreProjectionJson ?? data.score_projection ?? data.score_projection_json, {})
  const scoreCalibration = parseJsonValue(data.scoreCalibration ?? data.scoreCalibrationJson, {})
  const speechQuality = parseJsonValue(data.speechQuality ?? data.speechQualityJson, {})
  const lossLedger = parseJsonValue(data.lossLedger ?? data.lossLedgerJson ?? data.loss_ledger ?? data.loss_ledger_json, [])
  const coverageSummary = parseJsonValue(data.coverageSummary ?? data.coverageSummaryJson ?? data.coverage_summary ?? data.coverage_summary_json, {})
  const remediationTasks = parseJsonValue(data.remediationTasks ?? data.remediation_tasks, [])
  const taskVerifications = parseJsonValue(data.taskVerifications ?? data.task_verifications, [])
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
    action_plan: actionPlan,
    score_projection: scoreProjection,
    contractVersion: data.contractVersion ?? data.contract_version,
    todoPortfolioStatus: data.todoPortfolioStatus ?? data.todo_portfolio_status,
    lossLedger,
    coverageSummary,
    remediationTasks,
    taskVerifications,
    ruleEngineShadow: data.ruleEngineShadow ?? data.rule_engine_shadow ?? parseJsonValue(data.structuredResultJson ?? data.structured_result_json, null),
    score_calibration: scoreCalibration,
    speech_quality: speechQuality,
    scoreAuthority: data.scoreAuthority ?? data.score_authority,
    reviewReason: data.reviewReason ?? data.review_reason,
    llmRawScore: data.llmRawScore ?? data.llm_raw_score,
    ai_score: data.ai_score || {
      overall_score: data.overallScore == null ? null : data.overallScore,
      raw_overall_score: data.llmRawScore ?? data.llm_raw_score ?? scoreCalibration.original_score,
      dimensions,
      highlights,
      critical_issues: criticalIssues,
      improvement_priorities: improvementPriorities,
      action_plan: actionPlan,
      score_projection: scoreProjection,
      score_authority: data.scoreAuthority ?? data.score_authority,
    }
  }
}

function mergeLegacyAnalysisFields(base, legacy) {
  const merged = clonePlain(base || {})
  const source = legacy || {}
  const fields = [
    ['video_analysis', 'video_analysis'],
    ['fusion', 'fusion'],
    ['asr', 'asr'],
    ['audio_info', 'audio_info'],
    ['speaker_scores', 'speaker_scores'],
    ['character_profile', 'character_profile'],
    ['project_info', 'project_info'],
    ['jury_summary', 'jury_summary']
  ]
  fields.forEach(([targetKey, sourceKey]) => {
    if (isEmptyValue(merged[targetKey]) && !isEmptyValue(source[sourceKey])) merged[targetKey] = source[sourceKey]
  })
  if (isEmptyValue(merged.speech_quality) && !isEmptyValue(source.speech_quality)) merged.speech_quality = source.speech_quality
  if (merged.ai_score && source.ai_score) {
    merged.ai_score = {
      ...source.ai_score,
      ...merged.ai_score,
      highlights: arrayFrom(firstPresent(merged.ai_score.highlights, source.ai_score.highlights)),
      critical_issues: arrayFrom(firstPresent(merged.ai_score.critical_issues, source.ai_score.critical_issues)),
      improvement_priorities: arrayFrom(firstPresent(merged.ai_score.improvement_priorities, source.ai_score.improvement_priorities))
    }
  }
  return merged
}

function hasRichAiEvidence(value) {
  const video = value?.video_analysis || value?.videoAnalysis || {}
  const fusion = value?.fusion || {}
  const asr = value?.asr || {}
  return arrayFrom(firstPresent(video.per_frame, video.perFrame)).length > 0 ||
    arrayFrom(firstPresent(fusion.timeline, fusion.visual_descriptions, fusion.visualDescriptions)).length > 0 ||
    arrayFrom(asr.segments).length > 0
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

function normalizeVisualFrameAnalysis(item, index) {
  const screen = item?.screen_content || item?.screenContent || {}
  const scene = item?.scene || {}
  const speaker = item?.active_speaker || item?.activeSpeaker || {}
  const team = item?.team_collaboration || item?.teamCollaboration || {}
  const seconds = secondsFromAnalysisFrame(item, index)
  return {
    raw: item,
    id: frameTokenFromAnalysis(item),
    index,
    seconds,
    screenType: firstPresent(screen.screen_type, screen.screenType, scene.type, item?.frame_type, item?.frameType, ''),
    summary: firstPresent(
      item?.impression,
      screen.visible_text_summary,
      screen.visibleTextSummary,
      speaker.description,
      team.desc,
      screen.ppt_title,
      screen.pptTitle,
      ''
    ),
    ocrText: firstPresent(screen.visible_text_summary, screen.visibleTextSummary, screen.ppt_title, screen.pptTitle, '')
  }
}

function visualAnalysisForFrame(frame, index, analyses = []) {
  if (!analyses.length) return null
  const token = frameTokenFromFrame(frame)
  if (token) {
    const byId = analyses.find(item => item.id && item.id === token)
    if (byId) return byId
  }
  const seconds = frameSeconds(frame)
  const byIndex = analyses[index]
  if (byIndex && Math.abs((byIndex.seconds || 0) - seconds) <= 12) return byIndex
  const nearest = analyses
    .map(item => ({ item, distance: Math.abs((item.seconds || 0) - seconds) }))
    .sort((a, b) => a.distance - b.distance)[0]
  return nearest && nearest.distance <= 18 ? nearest.item : null
}

function secondsFromAnalysisFrame(item, index = 0) {
  const seconds = firstPresent(item?.timestamp, item?.time_seconds, item?.timeSeconds, item?.position_seconds, item?.positionSeconds)
  if (seconds !== undefined) return Number(seconds)
  const minutes = firstPresent(item?.timestamp_min, item?.timestampMin)
  if (minutes !== undefined) return Number(minutes) * 60
  return index * 30
}

function frameTokenFromFrame(frame) {
  if (!frame) return ''
  return String(firstPresent(frame.backendId, frame.frame_id, frame.frameId, frame.visual_frame_id, frame.visualFrameId, frame.id, frameTokenFromPath(frame.image_url || frame.imageUrl || frame.frame_url || frame.frameUrl || frame.url)) || '')
}

function frameTokenFromAnalysis(item) {
  return String(firstPresent(item?.frame_id, item?.frameId, item?.visual_frame_id, item?.visualFrameId, frameTokenFromPath(item?.image_path || item?.imagePath || item?.image_url || item?.imageUrl)) || '')
}

function frameTokenFromPath(value) {
  const text = String(value || '')
  const match = text.match(/([a-f0-9]{32})(?:\.(?:jpg|jpeg|png))?(?:$|[/?#])/i) || text.match(/_([a-f0-9]{32})\.(?:jpg|jpeg|png)$/i)
  return match ? match[1] : ''
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

function isJuryProcessing(value) {
  const status = String(value?.status || '').toLowerCase()
  return ['processing', 'pending', 'running'].includes(status)
}

function requestErrorMessage(error, fallback) {
  return error?.response?.data?.message || error?.message || fallback
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
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
  if (value === null || value === undefined || value === '') return '-'
  const number = Number(value)
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

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function isEmptyValue(value) {
  if (value === undefined || value === null || value === '') return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}

function clipText(value, max = 80) {
  const text = String(value || '')
  return text.length > max ? `${text.slice(0, max)}...` : text
}
