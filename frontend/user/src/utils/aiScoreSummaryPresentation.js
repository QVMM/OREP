/**
 * Score summary presentation view-model.
 * Rule: never invent scores, recover points, or narrative copy.
 * Missing fields → omit / empty, never hard-coded sample text.
 */

import { buildTrainingTasks } from './aiScoreTrainingTasks.js'
import { findFrameByAnchor, findFrameNearSeconds, frameSeconds } from './aiScoreFrameMatching.js'
import { normalizeCoverage } from './aiScoreCoverage.js'
import { enrichCoachingItem } from './aiScoreCoachingPresentation.js'
import { dimensionDisplayName } from './aiScoreDimensions.js'

const PRIORITY_RANK = { P0: 0, HIGH: 0, P1: 1, MEDIUM: 1, P2: 2, LOW: 2 }

/**
 * @param {object} input plain snapshot (prefer unwrapped refs)
 * @returns {object} presentation model for editorial overview
 */
export function buildScoreSummaryPresentation(input = {}) {
  const overallScore = numberOrNull(input.overallScore)
  const scoreLevel = input.scoreLevel && typeof input.scoreLevel === 'object'
    ? input.scoreLevel
    : { label: '', text: '' }

  const aiScore = objectFrom(input.aiScore)
  const result = objectFrom(input.result)
  const recovery = objectFrom(input.scoreRecoverySummary)
  const ruleEngine = objectFrom(input.ruleEngineReport)
  const scoreProjection = objectFrom(input.scoreProjection)

  const overview = objectFrom(firstPresent(aiScore.score_overview, aiScore.scoreOverview, result.score_overview, result.scoreOverview))
  const firstHighlight = arrayFrom(overview.highlights)[0]
  const highlightText = typeof firstHighlight === 'string'
    ? firstHighlight
    : firstPresent(firstHighlight?.description, firstHighlight?.title, firstHighlight?.text, '')
  const headline = firstPresent(
    aiScore.overall_conclusion,
    aiScore.conclusion,
    aiScore.summary,
    result.overallConclusion,
    result.overall_conclusion,
    highlightText && String(highlightText).replace(/\s+/g, ' ').slice(0, 42),
    overview.diagnosis && String(overview.diagnosis).replace(/\s+/g, ' ').slice(0, 42)
  )
  const lead = firstPresent(
    overview.diagnosis,
    aiScore.overall_analysis,
    aiScore.analysis,
    aiScore.description,
    result.overallAnalysis,
    result.overall_analysis
  )
  const suggestion = firstPresent(
    aiScore.overall_suggestion,
    aiScore.suggestion,
    result.overallSuggestion,
    result.overall_suggestion
  )

  const goalScore = 100
  const fullGap = overallScore === null ? null : Math.max(0, goalScore - overallScore)
  const predictedScoreLower = numberOrNull(firstPresent(scoreProjection.predictedScoreLower, scoreProjection.predicted_score_lower))
  const predictedScoreUpper = numberOrNull(firstPresent(scoreProjection.predictedScoreUpper, scoreProjection.predicted_score_upper))
  const predictedGainLower = numberOrNull(firstPresent(scoreProjection.predictedGainLower, scoreProjection.predicted_gain_lower))
  const predictedGainUpper = numberOrNull(firstPresent(scoreProjection.predictedGainUpper, scoreProjection.predicted_gain_upper))

  const recoverableFromSummary = numberOrNull(firstPresent(
    recovery.recoverable_range,
    recovery.recoverableRange,
    recovery.recoverable_score,
    recovery.recoverableScore,
    recovery.total_recoverable,
    recovery.totalRecoverable
  ))
  const recoverableFromRule = numberOrNull(firstPresent(
    ruleEngine.recoverablePoints,
    ruleEngine.recoverable_points,
    ruleEngine.total_recoverable,
    ruleEngine.totalRecoverable
  ))

  const prescriptions = buildPrescriptions(input)
  const recoverableFromTasks = prescriptions.reduce((sum, item) => {
    const points = numberOrNull(item.recoverPoints)
    return points === null ? sum : sum + points
  }, 0)
  const recoverable = firstNumber(recoverableFromSummary, recoverableFromRule, recoverableFromTasks > 0 ? recoverableFromTasks : null)
  const todayCount = Math.min(3, prescriptions.length)

  const dimensions = normalizeDimensions(input.dimensions)
  const weakestKey = dimensions.length
    ? dimensions.reduce((weakest, dim) => (dim.percent < weakest.percent ? dim : weakest), dimensions[0]).key
    : ''

  const moments = buildMoments(prescriptions, {
    evidenceAnchors: arrayFrom(input.evidenceAnchors),
    evidenceFrames: arrayFrom(input.evidenceFrames),
    formatTime: typeof input.formatTime === 'function' ? input.formatTime : defaultFormatTime
  })

  const meta = {
    trackName: firstPresent(input.reportTrackName, result.track_name, result.trackName, ''),
    projectName: firstPresent(result.project_name, result.projectName, result.project?.name, ''),
    sessionLabel: firstPresent(result.session_no, result.sessionNo, input.sessionId, input.reportId, ''),
    sourceType: firstPresent(input.reportSourceType, result.source_type, result.sourceType, ''),
    completedAt: firstPresent(result.completed_at, result.completedAt, result.created_at, result.createdAt, '')
  }

  const p0Count = prescriptions.filter(item => item.priority === 'P0').length
  const juryTeaser = buildJuryTeaser(input, overallScore)
  const continueLinks = buildContinueLinks(input, prescriptions.length)
  const coverage = normalizeCoverage(firstPresent(input.coverageSummary, input.coverage_summary))

  return {
    score: {
      value: overallScore,
      display: overallScore === null ? '' : formatScore(overallScore, input.formatNumber),
      levelLabel: scoreLevel.label || '',
      levelText: scoreLevel.text || '',
      levelTone: levelTone(overallScore, scoreLevel.label)
    },
    hero: {
      headline: headline || '',
      lead: lead || '',
      suggestion: suggestion || '',
      hasNarrative: Boolean(headline || lead)
    },
    metrics: {
      goalScore,
      goalDisplay: formatScore(goalScore, input.formatNumber, 0),
      fullGap,
      fullGapDisplay: fullGap === null ? '' : formatScore(fullGap, input.formatNumber),
      predictedScoreLower,
      predictedScoreUpper,
      predictedScoreDisplay: formatRange(predictedScoreLower, predictedScoreUpper, input.formatNumber),
      predictedGainLower,
      predictedGainUpper,
      predictedGainDisplay: formatRange(predictedGainLower, predictedGainUpper, input.formatNumber, '+'),
      recoverable,
      recoverableDisplay: recoverable === null ? '' : formatSigned(Math.abs(recoverable), input.formatNumber, '+'),
      recoverableHint: recoverable === null ? '' : '最高可追回约',
      prescriptionCount: prescriptions.length,
      todayCount,
      todayDisplay: todayCount > 0 ? String(todayCount) : '',
      todayHint: todayCount > 0 ? '件优先事项' : '',
      p0Count: p0Count || null
    },
    prescriptions,
    topPrescriptions: prescriptions.slice(0, 3),
    hasMorePrescriptions: prescriptions.length > 3,
    morePrescriptionCount: Math.max(0, prescriptions.length - 3),
    dimensions,
    weakestDimensionKey: weakestKey,
    showRadar: dimensions.length >= 3,
    moments,
    journey: buildJourney(input),
    meta,
    continueLinks,
    juryTeaser,
    coverage,
    intents: [
      { key: 'dimensions', label: '深入理解', title: '规则与五维', desc: '观测点、扣分位置、验收标准——给需要较真的人。' },
      { key: 'voice', label: '训练场', title: '表达与现场', desc: '句段替换、镜头与站位——只练和处方相关的段。', also: 'presentation' }
    ]
  }
}

export function buildPrescriptions(input = {}) {
  const fromUnified = arrayFrom(input.unifiedTodos).map((task, index) => normalizeTaskPrescription(task, index)).filter(Boolean)
  if (fromUnified.length) return sortPrescriptions(fromUnified).map(enrichPrescription)

  const fromTasks = arrayFrom(input.trainingTasks).map((task, index) => normalizeTaskPrescription(task, index)).filter(Boolean)
  if (fromTasks.length) return sortPrescriptions(fromTasks).map(enrichPrescription)

  const built = buildTrainingTasks({
    training_tasks: input.trainingTasks,
    trainingTasks: input.trainingTasks,
    structured_deductions: input.currentStructuredDeductions || input.structuredDeductions,
    structuredDeductions: input.currentStructuredDeductions || input.structuredDeductions
  }).map((task, index) => normalizeTaskPrescription(task, index)).filter(Boolean)
  if (built.length) return sortPrescriptions(built).map(enrichPrescription)

  const drafts = arrayFrom(input.reportWorkItemDrafts).map((item, index) => normalizeDraftPrescription(item, index)).filter(Boolean)
  return sortPrescriptions(drafts).map(enrichPrescription)
}

function enrichPrescription(item) {
  const enriched = enrichCoachingItem({
    ...item,
    why: item.reason || item.why || '',
    how: item.action || item.how || '',
    doneLines: item.doneLines || (item.acceptance ? String(item.acceptance).split(/\n+|\s*\|\s*/u).filter(Boolean) : []),
    dimension: item.dimension || item.dimensionName || '',
    coveredGapPoints: item.coveredGapPoints,
    scoreImpactLabel: item.scoreImpactLabel,
    ownerRole: item.ownerRole
  })
  return {
    ...item,
    reason: enriched.issueParagraph || item.reason || '',
    issueParagraph: enriched.issueParagraph || '',
    howSteps: enriched.howSteps || [],
    references: enriched.references || [],
    priorityLabel: enriched.priorityLabel || '',
    howPreview: enriched.howPreview || '',
    desc: enriched.issueParagraph || item.reason || ''
  }
}

function normalizeTaskPrescription(task, index) {
  if (!task || typeof task !== 'object') return null
  const title = firstPresent(task.title, task.correspondingDeduction, '')
  if (!title) return null
  const recoverPoints = numberOrNull(firstPresent(
    task.expectedRecoverPoints,
    task.expected_recover_points,
    task.maxRecoverablePoints,
    task.max_recoverable_points,
    task.recoverableScore,
    task.recoverPoints
  ))
  const action = firstPresent(task.trainingAction, task.training_action, task.action, task.requiredFix, task.required_fix, task.how, '')
  const acceptance = firstPresent(
    task.acceptanceCriteria,
    task.acceptance_criteria,
    task.acceptance,
    Array.isArray(task.doneLines) ? task.doneLines.join('|') : '',
    ''
  )
  return {
    id: String(firstPresent(task.id, task.taskId, task.task_id, `rx-${index + 1}`)),
    index: index + 1,
    title: stripPrefix(title),
    reason: firstPresent(
      task.issueParagraph,
      task.why,
      task.problem,
      task.correspondingDeduction,
      task.reason,
      ''
    ),
    action,
    acceptance,
    hasAction: Boolean(action),
    hasAcceptance: Boolean(acceptance),
    ownerRole: firstPresent(task.ownerRole, task.owner_role, ''),
    priority: normalizePriority(task.priority),
    recoverPoints,
    recoverDisplay: recoverPoints === null ? '' : formatSigned(Math.abs(recoverPoints), null, '+'),
    evidenceAnchorIds: arrayFrom(firstPresent(task.evidenceAnchorIds, task.evidence_anchor_ids)).map(Number).filter(Number.isFinite),
    scoreImpactLabel: firstPresent(task.scoreImpactLabel, ''),
    coveredGapPoints: numberOrNull(firstPresent(task.coveredGapPoints, task.covered_gap_points)),
    dimension: firstPresent(task.dimension, task.dimensionName, task.dimension_name, ''),
    doneLines: arrayFrom(task.doneLines),
    howSteps: arrayFrom(task.howSteps),
    references: arrayFrom(task.references),
    status: firstPresent(task.status, 'not_started'),
    source: 'training'
  }
}

function normalizeDraftPrescription(item, index) {
  if (!item || typeof item !== 'object') return null
  const title = firstPresent(item.title, '')
  if (!title) return null
  const recoverPoints = numberOrNull(firstPresent(item.expectedRecoverPoints, item.recoverPoints))
  return {
    id: String(firstPresent(item.id, `draft-${index + 1}`)),
    index: index + 1,
    title: stripPrefix(title),
    reason: firstPresent(item.description, ''),
    action: firstPresent(item.description, ''),
    acceptance: firstPresent(item.acceptanceCriteria, ''),
    hasAction: Boolean(item.description),
    hasAcceptance: Boolean(item.acceptanceCriteria),
    ownerRole: firstPresent(item.ownerRole, ''),
    priority: normalizePriority(item.priority),
    recoverPoints,
    recoverDisplay: recoverPoints === null ? '' : formatSigned(Math.abs(recoverPoints), null, '+'),
    evidenceAnchorIds: arrayFrom(item.evidenceAnchorIds).map(Number).filter(Number.isFinite),
    source: 'draft'
  }
}

function sortPrescriptions(list) {
  return [...list].sort((a, b) => {
    const pr = (PRIORITY_RANK[a.priority] ?? 1) - (PRIORITY_RANK[b.priority] ?? 1)
    if (pr !== 0) return pr
    return (numberOrZero(b.recoverPoints) - numberOrZero(a.recoverPoints))
  }).map((item, index) => ({ ...item, index: index + 1 }))
}

function buildMoments(prescriptions, { evidenceAnchors, evidenceFrames, formatTime }) {
  const moments = []
  for (const rx of prescriptions) {
    if (moments.length >= 3) break
    const anchor = resolveAnchor(rx.evidenceAnchorIds, evidenceAnchors)
    let frame = anchor ? findFrameByAnchor(anchor, evidenceFrames) : null
    const anchorSeconds = secondsFromAnchor(anchor)
    if (!frame && anchorSeconds !== null) {
      frame = findFrameNearSeconds(anchorSeconds, evidenceFrames)
    }
    const seconds = frame ? frameSeconds(frame) : anchorSeconds
    const image = frameImage(frame)
    const title = rx.title
    const summary = firstPresent(rx.reason, rx.action, '')
    if (!anchor && !frame && !summary && !title) continue
    // Only surface a moment when we have at least a time/image or tied prescription text
    if (!frame && !anchor && !title) continue
    moments.push({
      id: `moment-${rx.id}`,
      prescriptionId: rx.id,
      prescriptionIndex: rx.index,
      timeLabel: seconds !== null ? formatTime(seconds) : '',
      title,
      summary: summary || '',
      image,
      hasVisual: Boolean(image)
    })
  }
  return moments
}

function resolveAnchor(ids, anchors) {
  if (!ids?.length || !anchors?.length) return null
  for (const id of ids) {
    const hit = anchors.find(a => Number(firstPresent(a.id, a.anchorId, a.anchor_id)) === Number(id)
      || String(firstPresent(a.id, a.anchorId, a.anchor_id)) === String(id))
    if (hit) return hit
  }
  // Some reports store anchor objects without numeric id match — use first id as seconds-less stub
  return { id: ids[0] }
}

function secondsFromAnchor(anchor) {
  if (!anchor) return null
  const value = firstPresent(
    anchor.timestamp_seconds,
    anchor.timestampSeconds,
    anchor.time_seconds,
    anchor.timeSeconds,
    anchor.timestamp,
    anchor.time
  )
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function frameImage(frame) {
  if (!frame) return ''
  return firstPresent(
    frame.image_url,
    frame.imageUrl,
    frame.frame_url,
    frame.frameUrl,
    frame.url,
    frame.screenshot_url,
    frame.screenshotUrl,
    ''
  )
}

function normalizeDimensions(list) {
  return arrayFrom(list).map((dim, index) => {
    const maxScore = numberOrNull(firstPresent(dim.maxScore, dim.max_score)) || 0
    const score = numberOrZero(dim.score)
    const percent = maxScore > 0 ? Math.min(100, (score / maxScore) * 100) : 0
    const key = String(firstPresent(dim.key, `dim-${index}`))
    return {
      key,
      name: dimensionDisplayName(key, firstPresent(dim.name, '')),
      score,
      maxScore,
      percent,
      scoreDisplay: formatScore(score),
      maxDisplay: maxScore ? formatScore(maxScore, null, 0) : ''
    }
  })
}

function buildJourney(input) {
  // Labels are product chrome; completion flags only when real signals exist.
  const hasTasks = arrayFrom(input.trainingTasks).length > 0
    || arrayFrom(input.reportWorkItemDrafts).length > 0
    || arrayFrom(input.currentStructuredDeductions).length > 0
  const synced = numberOrZero(input.createdTeamTaskCount) > 0
  return {
    steps: [
      {
        key: 'today',
        title: '今天',
        desc: hasTasks ? '锁定处方，同步任务' : '等待可执行问题清单',
        active: true,
        done: synced
      },
      {
        key: 'day12',
        title: 'Day 1–2',
        desc: '补材料 · 改话术 · 证据入页',
        active: false,
        done: false
      },
      {
        key: 'day3',
        title: 'Day 3',
        desc: '完整彩排 · 按验收清单过一遍',
        active: false,
        done: false
      },
      {
        key: 'rescore',
        title: '重评',
        desc: '同一标尺，看见涨分与剩余洞',
        active: false,
        done: false
      }
    ]
  }
}

function buildContinueLinks(input, prescriptionCount) {
  const recoveredCount = numberOrNull(firstPresent(
    objectFrom(input.scoreRecoverySummary).recoveredCount,
    objectFrom(input.scoreRecoverySummary).recovered_count
  ))
  const previousDelta = numberOrNull(firstPresent(
    input.previousScoreDelta,
    input.previous_score_delta,
    objectFrom(input.previousScore).delta,
    objectFrom(input.scoreComparison).delta,
    objectFrom(input.scoreComparison).scoreDelta,
    objectFrom(input.scoreComparison).score_delta
  ))
  const showCompare = previousDelta !== null || (recoveredCount !== null && recoveredCount > 0)

  return [
    {
      key: 'todos',
      title: '处理全部待办',
      desc: prescriptionCount > 0
        ? `按优先级推进 ${prescriptionCount} 项可执行整改`
        : '查看待办队列与验收标准'
    },
    {
      key: 'why',
      title: '看评分依据',
      desc: '关键帧、维度与扣分位置——只读真实分析字段'
    },
    {
      key: 'compare',
      title: '和上一轮比一比',
      desc: showCompare
        ? '对照上一轮分数变化与已追回项'
        : '完成复评后可对比涨分',
      show: showCompare
    }
  ]
}

function buildJuryTeaser(input, overallScore) {
  const jury = objectFrom(input.juryResult)
  const nestedJury = objectFrom(jury.jury)
  const members = arrayFrom(firstPresent(jury.members, jury.memberList, jury.member_list, nestedJury.members))

  const officialScore = numberOrNull(firstPresent(
    jury.officialScore,
    jury.official_score,
    nestedJury.officialScore,
    nestedJury.official_score,
    overallScore
  ))
  const juryAverage = numberOrNull(firstPresent(
    jury.juryAverageScore,
    jury.jury_average_score,
    jury.juryAverage,
    jury.jury_average,
    nestedJury.trimmed_average_score,
    nestedJury.trimmedAverageScore,
    nestedJury.averageScore,
    nestedJury.average_score
  ))
  const diff = numberOrNull(firstPresent(
    jury.scoreDiffFromOfficial,
    jury.score_diff_from_official,
    jury.diff,
    nestedJury.score_diff_from_official,
    nestedJury.scoreDiffFromOfficial,
    officialScore !== null && juryAverage !== null ? juryAverage - officialScore : null
  ))
  const memberCount = numberOrNull(firstPresent(
    jury.judgeCount,
    jury.judge_count,
    jury.successfulCount,
    jury.successful_count,
    members.length || null
  ))

  const hasJuryResult = Boolean(
    juryAverage !== null
    || memberCount !== null
    || members.length
    || firstPresent(jury.status, '') === 'completed'
    || firstPresent(jury.status, '') === 'ready'
  )

  return {
    officialScore,
    juryAverage,
    diff,
    hasJuryResult,
    memberCount
  }
}

function levelTone(score, label) {
  const text = String(label || '')
  if (/优秀|良好/.test(text)) return 'good'
  if (/待提升/.test(text)) return 'mid'
  if (/风险/.test(text)) return 'risk'
  if (score === null) return 'mid'
  if (score >= 85) return 'good'
  if (score >= 70) return 'mid'
  return 'risk'
}

function stripPrefix(title) {
  return String(title || '')
    .replace(/^处理(扣分项|评分项|优先问题)[:：]\s*/u, '')
    .replace(/^补齐[:：]\s*/u, '')
    .trim()
}

function normalizePriority(value) {
  const text = String(value || '').toUpperCase()
  if (/P0|HIGH|CRITICAL|高|严重/.test(text)) return 'P0'
  if (/P2|LOW|低/.test(text)) return 'P2'
  if (/MEDIUM|中/.test(text)) return 'P1'
  if (/P1/.test(text)) return 'P1'
  return 'P1'
}

function formatScore(value, formatter, digits = 1) {
  if (typeof formatter === 'function') return formatter(value, digits)
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return digits === 0 ? String(Math.round(n)) : n.toFixed(digits)
}

function formatSigned(value, formatter, forceSign = '') {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  const abs = formatScore(Math.abs(n), formatter)
  if (forceSign === '+') return `+${abs}`
  if (n > 0) return `+${abs}`
  if (n < 0) return `−${abs}`
  return abs
}

function formatRange(lower, upper, formatter, forceSign = '') {
  const low = numberOrNull(lower)
  const high = numberOrNull(upper)
  if (low === null || high === null) return ''
  const format = value => forceSign === '+'
    ? formatSigned(value, formatter, '+')
    : formatScore(value, formatter)
  return low === high ? format(low) : `${format(low)}～${format(high)}`
}

function defaultFormatTime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function firstNumber(...values) {
  for (const value of values) {
    const n = numberOrNull(value)
    if (n !== null) return n
  }
  return null
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function numberOrZero(value) {
  const n = numberOrNull(value)
  return n === null ? 0 : n
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function objectFrom(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}
