export const verificationLabels = Object.freeze({
  verified: '复评已验证',
  partial: '部分通过，仍有差距',
  failed: '复评未通过',
  not_observable: '本轮无法同口径验证',
  regressed: '问题再次出现'
})

export function buildVerificationSummary(value) {
  const items = Array.isArray(value) ? value.filter(item => item && verificationLabels[item.status]) : []
  const counts = Object.fromEntries(Object.keys(verificationLabels).map(status => [status, 0]))
  for (const item of items) counts[item.status] += 1
  return { items, counts, total: items.length }
}
