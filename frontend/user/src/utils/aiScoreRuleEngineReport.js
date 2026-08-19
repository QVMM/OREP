const EVIDENCE_LEVELS = {
  E0: { label: 'E0 无证据', cap: '不超过20%' },
  E1: { label: 'E1 口号式主张', cap: '不超过30%' },
  E2: { label: 'E2 解释性证据', cap: '不超过50%' },
  E3: { label: 'E3 内部量化证据', cap: '不超过70%' },
  E4: { label: 'E4 场景验证证据', cap: '不超过85%' },
  E5: { label: 'E5 独立可核验证据', cap: '可进入高分档' },
  none: { label: '无证据', cap: '不超过20%' },
  claim: { label: '口头主张', cap: '不超过30%' },
  weak: { label: '弱证据', cap: '不超过50%' },
  medium: { label: '中等证据', cap: '不超过70%' },
  strong: { label: '强证据', cap: '可进入高分档' }
}

const DIFF_REASONS = {
  score_diff_exceeds_10: '证据规则校验与当前展示分差异较大',
  evidence_cap: '证据等级触发评分上限',
  current_deductions: '存在未追回扣分项',
  low_evidence_quality: '证据质量不足',
  missing_observation_evidence: '部分观测点缺少证据'
}

export function buildRuleEngineReport(result = {}) {
  const shadow = firstPresent(result.ruleEngineShadow, result.rule_engine_shadow, result.structuredResult, result.structured_result) || {}
  const ruleEngineScore = numberOrNull(firstPresent(shadow.ruleEngineScore, shadow.rule_engine_score, result.ruleEngineScore, result.rule_engine_score))
  const llmRawScore = numberOrNull(firstPresent(shadow.llmRawScore, shadow.llm_raw_score, result.llmRawScore, result.llm_raw_score, result.overallScore, result.overall_score))
  const scoreDiff = numberOrNull(firstPresent(shadow.scoreDiff, shadow.score_diff, result.scoreDiff, result.score_diff))
  const diffReasons = arrayFrom(firstPresent(shadow.diffReasons, shadow.diff_reasons, result.diffReasons, result.diff_reasons))
  const deductions = arrayFrom(firstPresent(result.structuredDeductions, result.structured_deductions)).map(normalizeDeduction)
  const observations = arrayFrom(firstPresent(result.structuredObservations, result.structured_observations)).map((item, index) => {
    const observation = normalizeObservation(item, index)
    observation.deductions = deductionsForObservation(observation, deductions)
    observation.deductedPoints = observation.deductions.reduce((sum, deduction) => sum + deduction.deductedPoints, 0)
    observation.recoverablePoints = observation.deductions.reduce((sum, deduction) => sum + deduction.maxRecoverablePoints, 0)
    return observation
  })

  const hasShadow = ruleEngineScore !== null
  const hasLargeDiff = scoreDiff !== null && Math.abs(scoreDiff) >= 10
  return {
    hasShadow,
    statusText: hasShadow ? (hasLargeDiff ? '需要复核' : '差异正常') : '未完成校验',
    checkTitle: hasShadow ? '评分一致性校验' : '评分校验待生成',
    llmRawLabel: '当前展示分',
    ruleEngineLabel: '证据规则参考',
    scoreDiffLabel: '校验差异',
    llmRawScore,
    ruleEngineScore,
    scoreDiff,
    scoreDiffText: scoreDiff === null ? '-' : signedNumber(scoreDiff, 1),
    diffReasons,
    diffReasonText: diffReasons.length
      ? diffReasons.map(reason => DIFF_REASONS[reason] || reason).join('、')
      : hasShadow ? '证据规则校验与当前展示分差异在观察范围内' : '当前报告尚未生成证据规则校验结果',
    scoringFingerprint: firstPresent(shadow.scoringFingerprint, shadow.scoring_fingerprint, result.scoringFingerprint, result.scoring_fingerprint, ''),
    observations,
    deductions,
    cappedObservationCount: observations.filter(item => item.isCapped).length,
    currentDeductionCount: deductions.filter(item => !item.recovery).length,
    recoverablePoints: deductions.reduce((sum, item) => sum + item.maxRecoverablePoints, 0)
  }
}

export function normalizeEvidenceLevel(level) {
  const key = String(level || '').trim()
  return EVIDENCE_LEVELS[key] || { label: key || '未标注', cap: key ? '按报告返回' : '未标注' }
}

function normalizeObservation(item, index) {
  const level = normalizeEvidenceLevel(firstPresent(item.evidenceLevel, item.evidence_level))
  const rawScore = numberOrNull(firstPresent(item.rawScore, item.raw_score))
  const scoreCap = numberOrNull(firstPresent(item.scoreCap, item.score_cap))
  const confidence = numberOrNull(item.confidence)
  return {
    raw: item,
    id: String(firstPresent(item.id, item.observationId, item.observation_id, `observation-${index}`)),
    code: firstPresent(item.observationCode, item.observation_code, ''),
    name: firstPresent(item.observationName, item.observation_name, item.name, item.dimensionName, item.dimension_name, `观测点 ${index + 1}`),
    dimensionName: firstPresent(item.dimensionName, item.dimension_name, item.dimension, '未标注维度'),
    rawScore,
    scoreCap,
    rawScoreText: scoreText(rawScore),
    capText: scoreText(scoreCap),
    evidenceLevel: firstPresent(item.evidenceLevel, item.evidence_level, ''),
    evidenceLevelLabel: level.label,
    evidenceCapText: level.cap,
    confidence,
    confidenceText: confidence === null ? '-' : `${Math.round(confidence <= 1 ? confidence * 100 : confidence)}%`,
    validityStatus: firstPresent(item.validityStatus, item.validity_status, ''),
    modelReason: firstPresent(item.modelReason, item.model_reason, '报告未返回该观测点解释。'),
    evidenceAnchorIds: arrayFrom(firstPresent(item.evidenceAnchorIds, item.evidence_anchor_ids)),
    isCapped: rawScore !== null && scoreCap !== null && rawScore > scoreCap
  }
}

function normalizeDeduction(item, index) {
  const deductedPoints = numberOrZero(firstPresent(item.deductedPoints, item.deducted_points, item.deducted, item.deduction))
  const maxRecoverablePoints = numberOrZero(firstPresent(item.maxRecoverablePoints, item.max_recoverable_points, item.recoverablePoints, item.recoverable_points))
  const recoveredPoints = numberOrZero(firstPresent(item.recoveredPoints, item.recovered_points))
  const level = normalizeEvidenceLevel(firstPresent(item.evidenceLevel, item.evidence_level))
  return {
    raw: item,
    id: String(firstPresent(item.id, item.deductionId, item.deduction_id, `deduction-${index}`)),
    observationCode: firstPresent(item.observationCode, item.observation_code, ''),
    dimensionName: firstPresent(item.dimensionName, item.dimension_name, item.dimension, '未标注维度'),
    deductedPoints,
    deductedText: scoreText(deductedPoints),
    recoveredPoints,
    recoveredText: scoreText(recoveredPoints),
    maxRecoverablePoints,
    recoverableText: scoreText(maxRecoverablePoints),
    reason: firstPresent(item.reason, item.issue, item.detail, '报告未返回扣分原因。'),
    requiredFix: firstPresent(item.requiredFix, item.required_fix, item.fix, item.suggestion, '补齐该扣分项对应证据。'),
    acceptanceCriteria: firstPresent(item.acceptanceCriteria, item.acceptance_criteria, item.acceptance, '补证后需能被证据链核验。'),
    evidenceLevelLabel: level.label,
    evidenceAnchorIds: arrayFrom(firstPresent(item.evidenceAnchorIds, item.evidence_anchor_ids)),
    recovery: Boolean(item.recovery),
    status: firstPresent(item.status, '')
  }
}

function deductionsForObservation(observation, deductions) {
  return deductions.filter(item => {
    if (observation.code && item.observationCode) return item.observationCode === observation.code
    return item.dimensionName === observation.dimensionName
  })
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function numberOrZero(value) {
  return numberOrNull(value) ?? 0
}

function scoreText(value) {
  const number = numberOrNull(value)
  return number === null ? '-' : number.toFixed(1)
}

function signedNumber(value, digits) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '-'
  return `${number > 0 ? '+' : ''}${number.toFixed(digits)}`
}
