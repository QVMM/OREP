export function normalizeCoverage(value) {
  const data = objectFrom(value)
  const coverageRate = finiteNumber(data.coverageRate ?? data.coverage_rate, 0)
  const uncoveredLossIds = arrayFrom(data.uncoveredLossIds ?? data.uncovered_loss_ids)
  const status = String(data.status || 'incomplete')
  return {
    ...data,
    status,
    lossItemCount: finiteNumber(data.lossItemCount ?? data.loss_item_count, 0),
    remediationTaskCount: finiteNumber(data.remediationTaskCount ?? data.remediation_task_count, 0),
    coveredLossItemCount: finiteNumber(data.coveredLossItemCount ?? data.covered_loss_item_count, 0),
    coveredGapPoints: finiteNumber(data.coveredGapPoints ?? data.covered_gap_points, 0),
    fullGap: finiteNumber(data.fullGap ?? data.full_gap, 0),
    coverageRate,
    uncoveredLossIds,
    canClaimCompleteTodos: status === 'complete' && coverageRate === 1 && uncoveredLossIds.length === 0
  }
}

function objectFrom(value) {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value
  if (typeof value !== 'string' || !value.trim()) return {}
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
}

function arrayFrom(value) {
  return Array.isArray(value) ? value : []
}

function finiteNumber(value, fallback) {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}
