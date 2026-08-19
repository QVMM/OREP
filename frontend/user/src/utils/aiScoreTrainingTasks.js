export function buildTrainingTasks(result = {}) {
  const explicitTasks = arrayFrom(firstPresent(result.trainingTasks, result.training_tasks))
    .map(normalizeBackendTask)
    .filter(Boolean)
  if (explicitTasks.length) return explicitTasks

  return arrayFrom(firstPresent(result.structuredDeductions, result.structured_deductions))
    .filter(item => item && !truthy(firstPresent(item.recovery, item.isRecovery, item.is_recovery)))
    .filter(item => numberOrZero(firstPresent(
      item.deductedPoints,
      item.deducted_points,
      item.deducted,
      item.deduction,
      item.maxRecoverablePoints,
      item.max_recoverable_points
    )) > 0)
    .map(normalizeDeductionTask)
    .filter(Boolean)
}

function normalizeBackendTask(item, index) {
  if (!item || typeof item !== 'object') return null
  const title = firstPresent(item.title, item.taskTitle, item.task_title, `训练任务 ${index + 1}`)
  const correspondingDeduction = firstPresent(item.correspondingDeduction, item.corresponding_deduction, item.reason, title)
  const trainingAction = firstPresent(item.trainingAction, item.training_action, item.action, item.requiredFix, item.required_fix)
  return {
    id: String(firstPresent(item.taskId, item.task_id, `training-task-${index + 1}`)),
    title,
    correspondingDeduction,
    trainingAction: specificAction(trainingAction, correspondingDeduction),
    ownerRole: firstPresent(item.ownerRole, item.owner_role, item.owner, '项目负责人'),
    timeSuggestion: firstPresent(item.timeSuggestion, item.time_suggestion, item.due, '下一轮复评前完成'),
    acceptanceCriteria: firstPresent(item.acceptanceCriteria, item.acceptance_criteria, item.acceptance, '下一轮评分能提供可复核证据。'),
    expectedRecoverPoints: numberOrZero(firstPresent(item.expectedRecoverPoints, item.expected_recover_points, item.recoverableScore, item.recoverable_score)),
    evidenceAnchorIds: arrayFrom(firstPresent(item.evidenceAnchorIds, item.evidence_anchor_ids)).map(Number).filter(Number.isFinite),
    priority: normalizePriority(firstPresent(item.priority, item.level, 'P1')),
    observationCode: firstPresent(item.observationCode, item.observation_code, ''),
    sourceIssueKey: firstPresent(item.sourceIssueKey, item.source_issue_key, ''),
    sourceKind: 'score-deduction',
    scoreLinked: true
  }
}

function normalizeDeductionTask(item, index) {
  const reason = firstPresent(item.reason, item.title, item.dimensionName, item.dimension_name, '扣分项待复核')
  const requiredFix = firstPresent(item.requiredFix, item.required_fix, item.suggestion, item.improvement, item.action)
  return {
    id: `training-task-${index + 1}`,
    title: `补齐：${reason}`,
    correspondingDeduction: reason,
    trainingAction: specificAction(requiredFix, reason),
    ownerRole: ownerRoleFor(`${firstPresent(item.dimensionName, item.dimension_name, item.dimension, '')} ${reason}`),
    timeSuggestion: '下一轮复评前完成补证、彩排和验收记录',
    acceptanceCriteria: firstPresent(item.acceptanceCriteria, item.acceptance_criteria, '下一轮评分能提供可复核证据。'),
    expectedRecoverPoints: numberOrZero(firstPresent(item.maxRecoverablePoints, item.max_recoverable_points, item.deductedPoints, item.deducted_points)),
    evidenceAnchorIds: arrayFrom(firstPresent(item.evidenceAnchorIds, item.evidence_anchor_ids)).map(Number).filter(Number.isFinite),
    priority: normalizePriority(firstPresent(item.priority, item.status, numberOrZero(firstPresent(item.deductedPoints, item.deducted_points)) >= 5 ? 'P0' : 'P1')),
    observationCode: firstPresent(item.observationCode, item.observation_code, ''),
    sourceIssueKey: firstPresent(item.sourceIssueKey, item.source_issue_key, ''),
    sourceKind: 'score-deduction',
    scoreLinked: true
  }
}

function specificAction(value, reason) {
  const text = String(value || '').trim()
  if (text && !isGenericAction(text)) return text
  return `围绕「${reason || '扣分项'}」补充可展示证据，录制一轮彩排片段，并在复评时说明改动前后差异。`
}

function isGenericAction(value) {
  const text = String(value || '').replace(/\s+/g, '')
  return ['优化表达', '加强展示', '继续优化', '改进方案'].includes(text) || text.length < 6
}

function ownerRoleFor(text) {
  const value = String(text || '')
  if (/技术|算法|模型|系统|演示|稳定|准确|测试/.test(value)) return '技术负责人'
  if (/商业|客户|订单|市场|成本|收益|数据|访谈/.test(value)) return '商业负责人'
  if (/表达|路演|话术|停顿|讲解/.test(value)) return '主讲负责人'
  if (/规范|合规|安全|知识产权|标准/.test(value)) return '合规负责人'
  return '项目负责人'
}

function normalizePriority(value) {
  const text = String(value || '').toUpperCase()
  if (/P0|HIGH|CRITICAL|NEW|高|严重|关键/.test(text)) return 'P0'
  if (/P2|LOW|低/.test(text)) return 'P2'
  return 'P1'
}

function truthy(value) {
  return value === true || value === 'true' || value === 1 || value === '1'
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function numberOrZero(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}
