export function idsFromRows(rows) {
  return Array.from(new Set((rows || []).map(row => row?.id).filter(id => id != null)))
}

export function batchDeleteSummary(result, entityName = '记录') {
  const data = result?.data || result || {}
  const deleted = Number(data.deleted || 0)
  const failed = Array.isArray(data.failed) ? data.failed : []
  if (failed.length > 0) {
    return {
      type: deleted > 0 ? 'warning' : 'error',
      message: `已删除 ${deleted} 条${entityName}，${failed.length} 条失败`
    }
  }
  return {
    type: 'success',
    message: `已删除 ${deleted} 条${entityName}`
  }
}
