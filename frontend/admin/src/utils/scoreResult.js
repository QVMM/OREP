export function normalizeScoreRows(payload) {
  const data = payload?.data && !Array.isArray(payload.data) ? payload.data : payload
  const records = Array.isArray(data?.records) ? data.records : []

  return records.flatMap((record) => {
    const details = Array.isArray(record?.details) ? record.details : []
    return details.map((detail) => ({
      id: `${record.userId ?? 'unknown'}_${detail.itemName || detail.category || detail.score || 'score'}`,
      evaluatorName: record.username || '未知评分人',
      evaluatorRole: record.role || '-',
      category: detail.category || '-',
      itemName: detail.itemName || '-',
      score: Number(detail.score) || 0,
      maxScore: Number(detail.maxScore) || 0,
      comment: detail.comment || '',
      createdAt: record.submittedAt || '',
      totalScore: Number(record.totalScore) || 0
    }))
  })
}

export function getScoreResultData(payload) {
  return payload?.data && !Array.isArray(payload.data) ? payload.data : payload || {}
}
