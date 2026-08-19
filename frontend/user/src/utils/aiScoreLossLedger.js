export function normalizeLossLedger(value) {
  const list = arrayFrom(value)
  return list.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const lossId = text(item.lossId ?? item.loss_id)
    const lossKey = text(item.lossKey ?? item.loss_key)
    const lossType = text(item.lossType ?? item.loss_type)
    const points = Number(item.points)
    if (!lossId || !lossKey || !lossType || !Number.isFinite(points) || points <= 0) return []
    return [{
      ...item,
      lossId,
      lossKey,
      lossType,
      points,
      reason: publicReason(item.reason, lossType),
      observationCode: text(item.observationCode ?? item.observation_code),
      scoreBudgetKey: text(item.scoreBudgetKey ?? item.score_budget_key),
      evidenceAnchorIds: Array.isArray(item.evidenceAnchorIds ?? item.evidence_anchor_ids)
        ? (item.evidenceAnchorIds ?? item.evidence_anchor_ids)
        : []
    }]
  })
}

function publicReason(value, lossType) {
  const reason = text(value)
  if (!reason) return ''

  const internalPrefix = /^当前绑定\d+条会话证据，证据等级E\d+，规则确认上限为[\d.]+[%％][；;]?/u
  if (internalPrefix.test(reason)) {
    const userDetail = reason.replace(internalPrefix, '').trim()
    return userDetail
      ? `已找到相关现场材料，但其完整性和可复核性仍不足。${userDetail}`
      : '现有材料能够支持部分结论，但仍需补充更完整、可复核的证明材料。'
  }

  if (lossType === 'evidence_limited' && /证据等级E\d+|规则确认上限|较低确认上限/u.test(reason)) {
    return '现有材料尚不足以完整支撑该结论，建议补充可定位、可复核的证明材料。'
  }
  return reason
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (typeof value !== 'string' || !value.trim()) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function text(value) {
  return String(value ?? '').trim()
}
