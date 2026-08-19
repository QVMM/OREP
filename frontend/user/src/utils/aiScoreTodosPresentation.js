/**
 * Todos presentation view-model.
 * Rule: never invent practice scripts or recovery points.
 * Improvement/suggestion/description may map to「怎么改」when dedicated action fields are empty
 * (common for dimension rubric drafts). Still never invent brand-new coaching scripts.
 *
 * Integrates formerly scattered sources into one coach queue:
 * trainingTasks + deductions + work-item drafts + action-plan coaching
 * + expression/presentation coaching moments (as practice-rich items when unmatched).
 */

import { buildTrainingTasks } from './aiScoreTrainingTasks.js'
import { normalizeCoverage } from './aiScoreCoverage.js'
import { enrichCoachingItem } from './aiScoreCoachingPresentation.js'

const PRIORITY_RANK = { P0: 0, HIGH: 0, P1: 1, MEDIUM: 1, P2: 2, LOW: 2 }

/**
 * @param {object} input plain report snapshot
 * @returns {{ items: object[], selectedId: string }}
 */
export function buildTodosPresentation(input = {}) {
  const isV3 = firstPresent(input.contractVersion, input.contract_version) === 'ai-score-report-v3'
  const items = collectTodoSources(input, isV3)
    .map((item, index) => normalizeTodoItem(item, index, input))
    .filter(Boolean)

  const sorted = sortTodos(isV3 ? dedupeV3Todos(items) : dedupeTodos(items))
    .map(item => enrichCoachingItem(item))
  return {
    items: sorted,
    selectedId: sorted[0]?.id || '',
    coverage: normalizeCoverage(firstPresent(input.coverageSummary, input.coverage_summary)),
    isV3
  }
}

/**
 * Merge all actionable sources so the 待办 page replaces the old
 * actions / voice / presentation workbenches rather than a thin subset.
 */
function collectTodoSources(input, isV3 = false) {
  if (hasOfficialTaskBook(input)) {
    return publishedTaskBookTodos(input)
  }
  if (isV3) {
    const formal = firstPresent(input.remediationTasks, input.remediation_tasks)
    return extractActionPlanTasks(arrayFrom(formal).length ? formal : firstPresent(input.actionPlan, input.action_plan))
  }
  const training = arrayFrom(input.trainingTasks).map(item => ({
    ...item,
    sourceKind: firstPresent(item?.sourceKind, item?.source_kind, 'score-deduction'),
    scoreLinked: true
  }))
  const fromDeductions = buildTrainingTasks({
    trainingTasks: [],
    training_tasks: [],
    structuredDeductions: input.currentStructuredDeductions || input.structuredDeductions,
    structured_deductions: input.currentStructuredDeductions || input.structuredDeductions
  })
  const drafts = arrayFrom(input.reportWorkItemDrafts)
  const formalActionPlan = extractActionPlanTasks(input.actionPlan || input.action_plan)
  const actionPlan = extractActionPlanTasks(input.actionPlanCoaching || input.action_plan_coaching)
  const coachingMoments = extractCoachingMomentTasks(input)
  return [...training, ...fromDeductions, ...drafts, ...formalActionPlan, ...actionPlan, ...coachingMoments]
}

function extractActionPlanTasks(plan) {
  if (!plan || typeof plan !== 'object') return []
  const list = Array.isArray(plan) ? plan : arrayFrom(firstPresent(
    plan.tasks,
    plan.task_list,
    plan.taskList,
    plan.training_tasks,
    plan.trainingTasks,
    plan.action_items,
    plan.actionItems,
    plan.work_items,
    plan.workItems,
    plan.plan,
    plan.items
  ))
  return list.map((item, index) => {
    if (!item || typeof item !== 'object') {
      const text = String(item || '').trim()
      if (!text) return null
      return {
        id: `action-plan-${index}`,
        title: text.slice(0, 40),
        description: text,
        priority: index < 2 ? 'P0' : 'P1',
        sourceKind: 'action-plan',
        scoreLinked: false
      }
    }
    const changeActions = arrayFrom(firstPresent(item.change_actions, item.changeActions))
      .map(value => String(value || '').trim())
      .filter(Boolean)
      .join('\n')
    const steps = arrayFrom(firstPresent(item.steps, item.howSteps, item.how_steps, item.change_actions, item.changeActions))
    return {
      ...item,
      id: firstPresent(item.id, item.taskId, item.task_id, `action-plan-${index}`),
      title: firstPresent(item.title, item.name, item.issue, item.task, item.problem, `提分任务 ${index + 1}`),
      reason: firstPresent(item.reason, item.detail, item.problem, item.issue, item.why_it_matters, item.whyItMatters, ''),
      problem: firstPresent(item.problem, item.issue, item.reason, ''),
      description: firstPresent(item.method, item.action, item.suggestion, item.improvement, item.fix, item.solution, item.description, changeActions, ''),
      trainingAction: firstPresent(item.method, item.action, item.suggestion, item.improvement, item.fix, changeActions, ''),
      acceptanceCriteria: firstPresent(item.acceptanceCriteria, item.acceptance_criteria, item.acceptance, item.acceptance_standard, item.acceptanceStandard, ''),
      priority: firstPresent(item.priority, item.level, item.severity, index < 2 ? 'P0' : 'P1'),
      ownerRole: firstPresent(item.ownerRole, item.owner_role, item.owner, ''),
      timeSuggestion: firstPresent(item.timeSuggestion, item.time_suggestion, item.timebox, ''),
      dimensionName: firstPresent(item.dimensionName, item.dimension_name, item.dimension, ''),
      observationCode: firstPresent(item.observationCode, item.observation_code, ''),
      sourceIssueKey: firstPresent(item.sourceIssueKey, item.source_issue_key, ''),
      evidenceAnchorIds: firstPresent(item.evidenceAnchorIds, item.evidence_anchor_ids, []),
      scoreImpact: objectFrom(firstPresent(item.scoreImpact, item.score_impact)),
      references: firstPresent(item.references, item.referenceLinks, item.reference_links, item.resources, []),
      howSteps: steps,
      sourceKind: 'action-plan',
      scoreLinked: objectFrom(firstPresent(item.scoreImpact, item.score_impact)).scoreLinkStatus === 'linked'
    }
  }).filter(Boolean)
}

function extractCoachingMomentTasks(input) {
  const moments = [
    ...arrayFrom(input.expressionCoaching?.moments || input.expressionCoaching?.items),
    ...arrayFrom(input.presentationCoaching?.moments || input.presentationCoaching?.items),
    ...arrayFrom(input.coachingMoments)
  ]
  return moments.map((item, index) => {
    if (!item || typeof item !== 'object') return null
    const title = firstPresent(item.title, item.issue, item.topic, item.name, '')
    const say = firstPresent(item.say, item.script, item.suggestedScript, item.suggested_script, item.replacement, '')
    const stage = firstPresent(item.stage, item.stageAction, item.stage_action, item.stageHint, '')
    const how = firstPresent(item.suggestion, item.improvement, item.action, item.fix, item.how, '')
    const why = firstPresent(item.reason, item.detail, item.problem, item.comment, item.evaluation, '')
    if (!title && !say && !stage && !how) return null
    return {
      id: firstPresent(item.id, `coaching-moment-${index}`),
      title: title || (say ? '表达练一练' : '台上练一练'),
      reason: why,
      trainingAction: how,
      description: how,
      practice: (say || stage) ? { say, stage } : undefined,
      practiceSay: say,
      practiceStage: stage,
      priority: firstPresent(item.priority, index < 2 ? 'P0' : 'P1'),
      dimensionName: firstPresent(item.dimensionName, item.dimension, item.category, say ? '表达' : '台上呈现'),
      sourceKind: 'coaching'
    }
  }).filter(Boolean)
}

function normalizeTodoItem(task, index, input) {
  if (!task || typeof task !== 'object') return null
  const title = stripPrefix(firstPresent(
    task.title,
    task.correspondingDeduction,
    task.reason,
    task.name,
    ''
  ))
  if (!title) return null

  const dimensionHint = firstPresent(
    task.dimensionName,
    task.dimension_name,
    task.dimension,
    task.dimName,
    ''
  )

  // Dedicated reason fields (真正「为什么」)
  const reasonText = firstPresent(
    task.reason,
    task.detail,
    task.issue,
    task.evaluation,
    task.comment,
    ''
  )

  // Dedicated action fields + improvement/suggestion (真正「怎么改」)
  const explicitHow = firstPresent(
    task.trainingAction,
    task.training_action,
    task.requiredFix,
    task.required_fix,
    task.action,
    task.fix,
    task.suggestion,
    task.improvement,
    ''
  )

  // Work-item drafts often only have description = suggestion text
  const description = String(firstPresent(task.description, '') || '').trim()
  const corresponding = String(firstPresent(task.correspondingDeduction, '') || '').trim()

  let how = actionTextFromValue(explicitHow)
  let why = String(reasonText || '').trim()

  // Scheme 1: map description / corresponding to how when action fields empty
  if (!how && description && !isGenericFiller(description)) {
    how = description
  }
  if (!how && corresponding && corresponding !== title && !isGenericFiller(corresponding)) {
    // correspondingDeduction sometimes carries long fix text on sparse payloads
    if (looksLikeActionText(corresponding)) {
      how = corresponding
    }
  }

  // why: prefer real reason; then corresponding if not used as how; then dimension
  if (!why && corresponding && normalizeKey(corresponding) !== normalizeKey(how) && normalizeKey(corresponding) !== normalizeKey(title)) {
    if (!looksLikeActionText(corresponding) || !how) {
      why = corresponding
    }
  }
  if (!why && dimensionHint && normalizeKey(dimensionHint) !== normalizeKey(title)) {
    why = `「${dimensionHint}」相关得分不足`
  }

  // Avoid duplicating the same paragraph under why + how
  if (why && how && normalizeKey(why) === normalizeKey(how)) {
    why = dimensionHint && normalizeKey(dimensionHint) !== normalizeKey(title)
      ? `「${dimensionHint}」相关得分不足`
      : ''
  }

  // If how still empty but description is generic filler, leave empty (honest empty)
  const acceptance = firstPresent(
    objectFrom(firstPresent(task.minimumAcceptance, task.minimum_acceptance)).summary,
    task.acceptanceCriteria,
    task.acceptance_criteria,
    task.acceptance,
    ''
  )
  const scoreImpact = objectFrom(firstPresent(task.scoreImpact, task.score_impact))
  const explicitScoreLinkStatus = firstPresent(scoreImpact.scoreLinkStatus, scoreImpact.score_link_status, '')
  const legacyScoreLinked = truthy(firstPresent(task.scoreLinked, task.score_linked)) || firstPresent(task.sourceKind, task.source_kind) === 'score-deduction'
  const scoreLinked = explicitScoreLinkStatus
    ? explicitScoreLinkStatus === 'linked'
    : legacyScoreLinked
  const legacyRecoverPoints = scoreLinked ? numberOrNull(firstPresent(
    task.expectedRecoverPoints,
    task.expected_recover_points,
    task.maxRecoverablePoints,
    task.max_recoverable_points,
    task.recoverableScore,
    task.recoverPoints,
    task.deductedPoints,
    task.deducted_points,
    task.deducted,
    task.deduction
  )) : null
  const scoreImpactLower = scoreLinked
    ? numberOrNull(firstPresent(scoreImpact.lower, scoreImpact.scoreImpactLower, scoreImpact.score_impact_lower, legacyRecoverPoints))
    : null
  const scoreImpactUpper = scoreLinked
    ? numberOrNull(firstPresent(scoreImpact.upper, scoreImpact.scoreImpactUpper, scoreImpact.score_impact_upper, legacyRecoverPoints))
    : null
  const scoreImpactType = firstPresent(
    scoreImpact.impactType,
    scoreImpact.impact_type,
    legacyScoreLinked ? 'deduction_recovery' : ''
  )
  const recoverPoints = scoreImpactUpper
  const scoreImpactLabel = buildScoreImpactLabel(
    scoreImpactType,
    scoreImpactLower,
    scoreImpactUpper,
    scoreLinked,
    firstPresent(input.contractVersion, input.contract_version) === 'ai-score-report-v3'
  )

  const practice = extractPractice(task, input)
  const clipLabel = firstPresent(
    task.clipLabel,
    task.clip_label,
    task.timeLabel,
    task.time_label,
    task.timestampLabel,
    task.timestamp_label,
    task.clip,
    ''
  )

  return {
    id: String(firstPresent(task.taskId, task.task_id, task.id, `todo-${index + 1}`)),
    title,
    dimension: String(dimensionHint || '').trim(),
    why: why || '',
    how: how || '',
    doneLines: splitDoneLines(acceptance),
    practice,
    ownerRole: firstPresent(task.ownerRole, task.owner_role, task.owner, ''),
    recoverPoints,
    recoverDisplay: recoverPoints === null ? '' : formatSigned(Math.abs(recoverPoints), '+'),
    priority: normalizePriority(task.priority),
    evidenceAnchorIds: arrayFrom(firstPresent(task.evidenceAnchorIds, task.evidence_anchor_ids))
      .map(Number)
      .filter(Number.isFinite),
    clipLabel: String(clipLabel || '').trim(),
    sourceKind: firstPresent(task.sourceKind, task.source_kind, ''),
    observationCode: String(firstPresent(task.observationCode, task.observation_code, '') || '').trim(),
    sourceIssueKey: String(firstPresent(task.sourceIssueKey, task.source_issue_key, '') || '').trim(),
    rootCauseKey: String(firstPresent(task.rootCauseKey, task.root_cause_key, '') || '').trim(),
    coveredLossIds: arrayFrom(firstPresent(task.coveredLossIds, task.covered_loss_ids)).map(String),
    coveredGapPoints: numberOrNull(firstPresent(task.coveredGapPoints, task.covered_gap_points)) || 0,
    minimumAcceptance: objectFrom(firstPresent(task.minimumAcceptance, task.minimum_acceptance)),
    fullScoreCriteria: objectFrom(firstPresent(task.fullScoreCriteria, task.full_score_criteria)),
    status: normalizeStatus(firstPresent(task.status, 'not_started')),
    taskRecordId: numberOrNull(firstPresent(task.taskRecordId, task.task_record_id)),
    scoreLinked,
    scoreImpactType,
    scoreImpactLower,
    scoreImpactUpper,
    scoreImpactLabel,
    sourceLabel: scoreLinked
      ? '计分待办'
      : firstPresent(input.contractVersion, input.contract_version) === 'ai-score-report-v3'
        ? '诊断整改'
        : firstPresent(task.sourceKind, task.source_kind) === 'action-plan'
          ? '额外训练建议'
          : '',
    timeSuggestion: firstPresent(task.timeSuggestion, task.time_suggestion, task.timebox, ''),
    evidenceNeeded: firstPresent(task.evidenceNeeded, task.evidence_needed, ''),
    hungEvidence: firstPresent(task.hungEvidence, task.hung_evidence, ''),
    itemIndex: numberOrNull(firstPresent(task.itemIndex, task.item_index)),
    _richness: scoreRichness({ how, why, acceptance, recoverPoints, practice })
  }
}

function dedupeV3Todos(items) {
  const seen = new Set()
  return items.filter((item) => {
    if (!item.id || seen.has(item.id)) return false
    seen.add(item.id)
    return true
  }).map(item => {
    const { _richness, ...rest } = item
    return rest
  })
}

function dedupeTodos(items) {
  const deduped = []
  for (const item of items) {
    const index = deduped.findIndex(existing => sameTodoIssue(existing, item))
    if (index < 0) deduped.push(item)
    else deduped[index] = mergeTodoItems(deduped[index], item)
  }

  return deduped.map(item => {
    const { _richness, ...rest } = item
    return rest
  })
}

function sameTodoIssue(left, right) {
  if (left.id && right.id && String(left.id) === String(right.id)) return true
  if (left.observationCode && right.observationCode && left.observationCode === right.observationCode) return true
  if (left.sourceIssueKey && right.sourceIssueKey && left.sourceIssueKey === right.sourceIssueKey) return true
  const leftTitle = normalizeKey(left.title)
  const rightTitle = normalizeKey(right.title)
  if (leftTitle && leftTitle === rightTitle) return true
  return issueFingerprintMatches(left, right)
}

function issueFingerprintMatches(left, right) {
  const leftText = normalizeKey(`${left.title || ''}${left.why || ''}`)
  const rightText = normalizeKey(`${right.title || ''}${right.why || ''}`)
  if (leftText.length < 8 || rightText.length < 8) return false
  const leftPairs = ngrams(leftText, 2)
  const rightPairs = ngrams(rightText, 2)
  const common = [...leftPairs].filter(value => rightPairs.has(value)).length
  const denominator = Math.min(leftPairs.size, rightPairs.size)
  return denominator >= 4 && common / denominator >= 0.72
}

function ngrams(value, size) {
  const result = new Set()
  for (let index = 0; index <= value.length - size; index += 1) result.add(value.slice(index, index + size))
  return result
}

function mergeTodoItems(left, right) {
  const base = left.scoreLinked ? left : right.scoreLinked ? right : left._richness >= right._richness ? left : right
  const extra = base === left ? right : left
  const recoverPoints = base.scoreLinked
    ? base.recoverPoints
    : extra.scoreLinked
      ? extra.recoverPoints
      : null
  const merged = {
    ...extra,
    ...base,
    why: base.why || extra.why,
    how: base.how || extra.how,
    doneLines: base.doneLines?.length ? base.doneLines : extra.doneLines,
    practice: base.practice || extra.practice,
    ownerRole: base.ownerRole || extra.ownerRole,
    timeSuggestion: base.timeSuggestion || extra.timeSuggestion,
    dimension: base.dimension || extra.dimension,
    observationCode: base.observationCode || extra.observationCode,
    sourceIssueKey: base.sourceIssueKey || extra.sourceIssueKey,
    evidenceAnchorIds: [...new Set([...(base.evidenceAnchorIds || []), ...(extra.evidenceAnchorIds || [])])],
    scoreLinked: Boolean(base.scoreLinked || extra.scoreLinked),
    scoreImpactType: base.scoreImpactType || extra.scoreImpactType,
    scoreImpactLower: base.scoreLinked ? base.scoreImpactLower : extra.scoreImpactLower,
    scoreImpactUpper: base.scoreLinked ? base.scoreImpactUpper : extra.scoreImpactUpper,
    scoreImpactLabel: base.scoreLinked ? base.scoreImpactLabel : extra.scoreImpactLabel,
    sourceLabel: base.scoreLinked ? base.sourceLabel : (extra.sourceLabel || base.sourceLabel),
    recoverPoints,
    recoverDisplay: recoverPoints === null ? '' : formatSigned(Math.abs(recoverPoints), '+'),
    _richness: Math.max(base._richness, extra._richness)
  }
  return merged
}

function scoreRichness({ how, why, acceptance, recoverPoints, practice }) {
  let score = 0
  if (how) score += 4
  if (why) score += 2
  if (acceptance) score += 2
  if (recoverPoints !== null && recoverPoints !== undefined) score += 1
  if (practice?.say || practice?.stage) score += 3
  return score
}

function looksLikeActionText(text) {
  const value = String(text || '')
  if (value.length >= 16) return true
  return /增加|补充|优化|改|加|减少|展示|说明|补齐|建议|需要|应|要/.test(value)
}

function actionTextFromValue(value) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return String(firstPresent(
      value.action,
      value.trainingAction,
      value.training_action,
      value.method,
      value.suggestion,
      value.improvement,
      value.fix,
      value.description,
      ''
    ) || '').trim()
  }

  const text = String(value || '').trim()
  if (!text || !/^\s*\{[\s\S]*\}\s*$/u.test(text)) return text

  try {
    const parsed = JSON.parse(text)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return actionTextFromValue(parsed) || text
    }
  } catch {
    // Some pipeline payloads contain Python dict repr with single-quoted keys.
  }

  const match = text.match(/['"](?:action|trainingAction|training_action|method|suggestion|improvement|fix|description)['"]\s*:\s*(['"])([\s\S]*?)\1\s*(?:,|\})/u)
  return match?.[2]?.replace(/\\(['"\\])/g, '$1').trim() || text
}

function isGenericFiller(text) {
  const value = String(text || '').replace(/\s+/g, '')
  return [
    '补齐评分报告指出的证据缺口。',
    '补齐评分表指出的证据缺口。',
    '补齐评分报告指出的关键证据，并在下一轮彩排中验证。'
  ].includes(value) || value.length < 4
}

/**
 * Only surface practice when real coaching / script fields exist.
 * Never invent say/stage from trainingAction or generic fluff.
 */
function extractPractice(task, input = {}) {
  const practice = objectFrom(task.practice)
  const coaching = objectFrom(firstPresent(task.coaching, task.expressionCoaching, task.presentationCoaching))
  const coachingList = arrayFrom(firstPresent(
    input.expressionCoaching?.moments,
    input.presentationCoaching?.moments,
    input.coachingMoments,
    task.coachingMoments
  ))

  let matchedCoaching = null
  if (coachingList.length) {
    const title = String(firstPresent(task.title, task.correspondingDeduction, '')).toLowerCase()
    matchedCoaching = coachingList.find(item => {
      if (!item || typeof item !== 'object') return false
      const text = String(firstPresent(item.title, item.issue, item.topic, item.script, item.say, '')).toLowerCase()
      return title && text && (text.includes(title.slice(0, 8)) || title.includes(text.slice(0, 8)))
    }) || null
  }

  const say = firstPresent(
    practice.say,
    practice.script,
    practice.suggestedScript,
    practice.suggested_script,
    coaching.say,
    coaching.script,
    coaching.suggestedScript,
    coaching.suggested_script,
    coaching.replacement,
    matchedCoaching?.say,
    matchedCoaching?.script,
    matchedCoaching?.suggestedScript,
    matchedCoaching?.replacement,
    task.practiceSay,
    task.practice_say,
    task.script,
    task.suggestedScript,
    task.suggested_script,
    ''
  )
  const stage = firstPresent(
    practice.stage,
    practice.stageAction,
    practice.stage_action,
    practice.stageHint,
    coaching.stage,
    coaching.stageAction,
    coaching.stage_action,
    coaching.stageHint,
    matchedCoaching?.stage,
    matchedCoaching?.stageAction,
    matchedCoaching?.stage_action,
    task.practiceStage,
    task.practice_stage,
    task.stageAction,
    task.stage_action,
    ''
  )

  const sayText = String(say || '').trim()
  const stageText = String(stage || '').trim()
  if (!sayText && !stageText) return null

  return {
    say: sayText,
    stage: stageText
  }
}

function splitDoneLines(acceptance) {
  const text = String(acceptance || '').trim()
  if (!text) return []
  return text
    .split(/\n+|\s*\|\s*/u)
    .map(line => line.trim())
    .filter(Boolean)
}

function sortTodos(list) {
  return [...list].sort((a, b) => {
    const pr = (PRIORITY_RANK[a.priority] ?? 1) - (PRIORITY_RANK[b.priority] ?? 1)
    if (pr !== 0) return pr
    return numberOrZero(b.recoverPoints) - numberOrZero(a.recoverPoints)
  })
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

function normalizeKey(value) {
  return String(value || '').replace(/\s+/g, '').toLowerCase()
}

function formatSigned(value, forceSign = '') {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  const abs = n.toFixed(1)
  if (forceSign === '+') return `+${abs}`
  if (n > 0) return `+${abs}`
  if (n < 0) return `−${abs}`
  return abs
}

function buildScoreImpactLabel(type, lower, upper, linked, isV3 = false) {
  if (!linked || lower === null || upper === null) return ''
  const low = Number(lower).toFixed(1)
  const high = Number(upper).toFixed(1)
  const range = Number(lower) === Number(upper) ? high : `${low}～${high}`
  if (isV3) return Number(lower) === Number(upper)
    ? `最低验收通过后，保守预计 +${high} 分`
    : `最低验收通过后，保守预计 +${low}～+${high} 分`
  if (type === 'deduction_recovery') return `最高可追回约 ${high} 分`
  if (type === 'evidence_unlock') return `补证并核验通过后，预计可争取 ${range} 分`
  if (type === 'performance_improvement') return `达到验收标准后，预计可提升 ${range} 分`
  return ''
}

function normalizeStatus(value) {
  const status = String(value || 'not_started')
  return ['not_started', 'in_progress', 'submitted', 'awaiting_rerun', 'verified', 'partial', 'failed', 'not_observable', 'regressed', 'superseded'].includes(status)
    ? status
    : 'not_started'
}

function hasOfficialTaskBook(input) {
  return Object.prototype.hasOwnProperty.call(input || {}, 'taskBook')
    || Object.prototype.hasOwnProperty.call(input || {}, 'task_book')
}

function publishedTaskBookTodos(input) {
  const book = objectFrom(firstPresent(input.taskBook, input.task_book))
  if (book.published !== true && book.published !== 'true') return []
  return arrayFrom(book.items).slice(0, 4).map((item, index) => {
    const row = objectFrom(item)
    const title = String(firstPresent(row.title, '') || '').trim()
    if (!title) return null
    return {
      id: firstPresent(row.id, `task-book-${index}`),
      title,
      goal: firstPresent(row.goal, ''),
      why: firstPresent(row.goal, ''),
      how: arrayFrom(row.steps).join('\n'),
      howSteps: arrayFrom(row.steps),
      acceptance: firstPresent(row.acceptance, ''),
      evidenceNeeded: firstPresent(row.evidenceNeeded, row.evidence_needed, ''),
      hungEvidence: firstPresent(row.hungEvidence, row.hung_evidence, ''),
      itemIndex: index,
      expectedGain: firstPresent(row.expectedGain, row.expected_gain, ''),
      ownerRole: firstPresent(row.ownerRole, row.owner_role, ''),
      timeSuggestion: firstPresent(row.dueHint, row.due_hint, ''),
      sourceRefs: arrayFrom(row.sourceRefs || row.source_refs),
      sourceKind: 'task-book',
      scoreLinked: true,
      priority: index === 0 ? 'P0' : 'P1'
    }
  }).filter(Boolean)
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function truthy(value) {
  return value === true || value === 'true' || value === 1 || value === '1'
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
