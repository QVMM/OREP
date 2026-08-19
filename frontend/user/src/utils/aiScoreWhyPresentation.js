/**
 * Why (依据) presentation view-model.
 * Rule: analysis only from real caption/ocr/description/modelReason — never invent narrative.
 */

import { findFrameNearSeconds, frameSeconds } from './aiScoreFrameMatching.js'
import { normalizeLossLedger } from './aiScoreLossLedger.js'
import { dimensionDisplayName } from './aiScoreDimensions.js'

const DEFAULT_STRIP_LIMIT = 10

/**
 * @param {object} input
 * @param {Array} [input.evidenceFrames]
 * @param {Array} [input.dimensions]
 * @param {Array} [input.deductions]
 * @param {Array} [input.evidenceAnchors]
 * @param {string|number} [input.selectedFrameId]
 * @param {Function} [input.formatTime]
 * @param {number} [input.stripLimit]
 * @returns {object}
 */
export function buildWhyPresentation(input = {}) {
  const formatTime = typeof input.formatTime === 'function' ? input.formatTime : defaultFormatTime
  const stripLimit = Number.isFinite(Number(input.stripLimit)) ? Number(input.stripLimit) : DEFAULT_STRIP_LIMIT

  const dimensions = normalizeDimensions(input.dimensions)
  const deductions = arrayFrom(input.deductions || input.currentStructuredDeductions || input.structuredDeductions)
  const anchors = arrayFrom(input.evidenceAnchors)
  const rawFrames = arrayFrom(input.evidenceFrames || input.visualFrames)

  const prioritized = prioritizeFrames(rawFrames, anchors, deductions)
  const frames = prioritized.map((frame, index) => normalizeFrame(frame, index, {
    deductions,
    anchors,
    formatTime
  }))

  const selectedFrame = resolveSelectedFrame(frames, input.selectedFrameId)
  const total = frames.length
  const { groups: lossGroups, total: lossTotal } = buildLossGroups(
    normalizeLossLedger(input.lossLedger),
    arrayFrom(input.remediationTasks)
  )

  return {
    lossGroups,
    lossTotal,
    dimensions,
    frames,
    selectedFrame,
    showMoreHint: total > stripLimit,
    stripLimit,
    totalFrameCount: total
  }
}

function buildLossGroups(lossLedger, remediationTasks) {
  const groups = {
    performance: { key: 'performance', label: '表现差距', description: '当前表现与该观测点满分标准之间的差距。', items: [], points: 0 },
    evidence: { key: 'evidence', label: '证据上限', description: '主张缺少可定位证据，按规则封顶形成的差距。', items: [], points: 0 },
    violation: { key: 'violation', label: '规则惩罚', description: '触发明确违规、故障或硬性惩罚规则。', items: [], points: 0 }
  }
  const taskLinks = new Map()
  for (const task of remediationTasks) {
    const taskId = String(firstPresent(task.taskId, task.task_id, task.id, ''))
    if (!taskId) continue
    for (const lossId of arrayFrom(firstPresent(task.coveredLossIds, task.covered_loss_ids))) {
      const key = String(lossId)
      if (!taskLinks.has(key)) taskLinks.set(key, [])
      taskLinks.get(key).push({ taskId, taskTitle: firstPresent(task.title, '') })
    }
  }

  for (const loss of lossLedger) {
    const groupKey = lossGroupKey(loss.lossType)
    const links = taskLinks.get(loss.lossId) || []
    const item = {
      ...loss,
      observationName: firstPresent(loss.observationName, loss.observation_name, loss.observationCode, '未命名观测点'),
      reason: firstPresent(loss.reason, '报告未返回失分原因'),
      taskId: links[0]?.taskId || '',
      taskTitle: links[0]?.taskTitle || '',
      taskLinks: links
    }
    groups[groupKey].items.push(item)
    groups[groupKey].points += loss.points
  }

  const total = lossLedger.reduce((sum, item) => sum + item.points, 0)
  return { groups, total: roundPoint(total) }
}

function lossGroupKey(lossType) {
  const value = String(lossType || '').toLowerCase()
  if (/violation|penalty|hard/.test(value)) return 'violation'
  if (/evidence|cap|missing/.test(value)) return 'evidence'
  return 'performance'
}

function roundPoint(value) {
  return Math.round((Number(value) || 0) * 100) / 100
}

function normalizeDimensions(list) {
  const dims = arrayFrom(list).map((dim, index) => {
    const maxScore = numberOrNull(firstPresent(dim.maxScore, dim.max_score)) || 0
    const score = numberOrZero(dim.score)
    const percent = maxScore > 0 ? Math.min(100, (score / maxScore) * 100) : numberOrZero(dim.percent)
    const key = String(firstPresent(dim.key, `dim-${index}`))
    return {
      key,
      name: dimensionDisplayName(key, firstPresent(dim.name, '')),
      score,
      maxScore,
      percent,
      scoreDisplay: formatScore(score),
      weak: false
    }
  })

  if (!dims.length) return dims

  const weakest = dims.reduce((min, dim) => (dim.percent < min.percent ? dim : min), dims[0])
  return dims.map(dim => ({
    ...dim,
    weak: dim.key === weakest.key
  }))
}

function prioritizeFrames(frames, anchors, deductions) {
  if (!frames.length) return []

  const prioritySeconds = collectPrioritySeconds(anchors, deductions)
  if (!prioritySeconds.length) return frames

  const ranked = frames.map((frame, index) => {
    const seconds = frameSeconds(frame)
    const nearest = prioritySeconds.reduce((best, target) => {
      const distance = Math.abs(seconds - target)
      return distance < best.distance ? { distance, target } : best
    }, { distance: Infinity, target: null })
    const isHit = nearest.distance <= 3
    return { frame, index, isHit, distance: nearest.distance }
  })

  return ranked
    .sort((a, b) => {
      if (a.isHit !== b.isHit) return a.isHit ? -1 : 1
      if (a.isHit && b.isHit && a.distance !== b.distance) return a.distance - b.distance
      return a.index - b.index
    })
    .map(item => item.frame)
}

function collectPrioritySeconds(anchors, deductions) {
  const values = []
  for (const anchor of anchors) {
    const seconds = numberOrNull(firstPresent(
      anchor.timestamp_seconds,
      anchor.timestampSeconds,
      anchor.time_seconds,
      anchor.timeSeconds,
      anchor.timestamp,
      anchor.time
    ))
    if (seconds !== null) values.push(seconds)
  }
  for (const deduction of deductions) {
    const seconds = numberOrNull(firstPresent(
      deduction.timestamp_seconds,
      deduction.timestampSeconds,
      deduction.time_seconds,
      deduction.timeSeconds,
      deduction.timestamp,
      deduction.time
    ))
    if (seconds !== null) values.push(seconds)
  }
  return values
}

function normalizeFrame(frame, index, { deductions, anchors, formatTime }) {
  const id = String(firstPresent(
    frame.backendId,
    frame.id,
    frame.frame_id,
    frame.frameId,
    frame.visual_frame_id,
    frame.visualFrameId,
    `frame-${index + 1}`
  ))
  const seconds = frameSeconds(frame)
  const analysis = extractAnalysis(frame)
  const linked = findLinkedTodo(frame, seconds, deductions, anchors)

  return {
    id,
    timeLabel: formatTime(seconds),
    title: firstPresent(frame.title, frame.screen_type, frame.screenType, frame.label, ''),
    analysis,
    image: frameImage(frame),
    todoTitle: linked.todoTitle,
    recoverDisplay: linked.recoverDisplay,
    dimensionHint: linked.dimensionHint
  }
}

function extractAnalysis(frame) {
  return firstPresent(
    frame.caption,
    frame.ocr_text,
    frame.ocrText,
    frame.description,
    frame.modelReason,
    frame.model_reason,
    frame.reason,
    frame.analysis,
    ''
  ) || ''
}

function findLinkedTodo(frame, seconds, deductions, anchors) {
  const empty = { todoTitle: '', recoverDisplay: '', dimensionHint: '' }
  if (!deductions.length && !anchors.length) return empty

  const frameIds = new Set([
    frame.backendId,
    frame.id,
    frame.frame_id,
    frame.frameId
  ].filter(v => v !== undefined && v !== null && v !== '').map(String))

  for (const deduction of deductions) {
    const anchorIds = arrayFrom(firstPresent(deduction.evidenceAnchorIds, deduction.evidence_anchor_ids))
    const linkedAnchor = anchors.find(anchor => {
      const aid = String(firstPresent(anchor.id, anchor.anchorId, anchor.anchor_id, ''))
      return anchorIds.some(id => String(id) === aid)
    })
    const anchorFrameId = linkedAnchor
      ? firstPresent(linkedAnchor.frame_id, linkedAnchor.frameId, linkedAnchor.visual_frame_id)
      : firstPresent(deduction.frame_id, deduction.frameId)
    if (anchorFrameId !== undefined && frameIds.has(String(anchorFrameId))) {
      return todoFieldsFromDeduction(deduction)
    }

    const deductionSeconds = numberOrNull(firstPresent(
      deduction.timestamp_seconds,
      deduction.timestampSeconds,
      deduction.time_seconds,
      deduction.timeSeconds,
      deduction.timestamp,
      deduction.time,
      linkedAnchor?.timestamp_seconds,
      linkedAnchor?.timestampSeconds
    ))
    if (deductionSeconds !== null && Math.abs(seconds - deductionSeconds) <= 3) {
      return todoFieldsFromDeduction(deduction)
    }
  }

  // Weak near-match via findFrameNearSeconds only for seconds listed on deductions
  for (const deduction of deductions) {
    const deductionSeconds = numberOrNull(firstPresent(
      deduction.timestamp_seconds,
      deduction.timestampSeconds,
      deduction.time_seconds,
      deduction.timeSeconds,
      deduction.timestamp,
      deduction.time
    ))
    if (deductionSeconds === null) continue
    const near = findFrameNearSeconds(deductionSeconds, [frame])
    if (near) return todoFieldsFromDeduction(deduction)
  }

  return empty
}

function todoFieldsFromDeduction(deduction) {
  const recoverPoints = numberOrNull(firstPresent(
    deduction.maxRecoverablePoints,
    deduction.max_recoverable_points,
    deduction.expectedRecoverPoints,
    deduction.deductedPoints,
    deduction.deducted_points
  ))
  return {
    todoTitle: stripPrefix(firstPresent(deduction.reason, deduction.title, deduction.requiredFix, deduction.required_fix, '')),
    recoverDisplay: recoverPoints === null ? '' : `+${formatScore(Math.abs(recoverPoints))}`,
    dimensionHint: firstPresent(deduction.dimensionName, deduction.dimension_name, deduction.dimension, '')
  }
}

function resolveSelectedFrame(frames, selectedFrameId) {
  if (!frames.length) return null
  if (selectedFrameId === undefined || selectedFrameId === null || selectedFrameId === '') {
    return frames[0]
  }
  return frames.find(frame => String(frame.id) === String(selectedFrameId)) || frames[0]
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

function stripPrefix(title) {
  return String(title || '')
    .replace(/^处理(扣分项|评分项|优先问题)[:：]\s*/u, '')
    .replace(/^补齐[:：]\s*/u, '')
    .trim()
}

function formatScore(value, digits = 1) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return digits === 0 ? String(Math.round(n)) : n.toFixed(digits)
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
