export function formatDate(value, withYear = false) {
  if (!value) return '未设置'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', {
    ...(withYear ? { year: 'numeric' } : {}),
    month: 'numeric',
    day: 'numeric'
  }).format(date)
}

export function formatTrainingCopy(value) {
  return String(value || '').replaceAll('集训', '训练')
}

export function trainingDayLockLabel(day = {}) {
  if (!day || !day.locked) return ''
  if (String(day.lockReason || '').toUpperCase() === 'NOT_PUBLISHED') return '训练日尚未发布'
  const when = day.effectiveUnlockAt || day.scheduledUnlockAt || day.trainingDate
  if (when) return `${formatDate(when, true)} 开放`
  return '训练日尚未开放'
}

export function trainingDayLockMessage(day = {}) {
  if (!day || !day.locked) return ''
  if (String(day.lockReason || '').toUpperCase() === 'NOT_PUBLISHED') {
    return '老师还没有发布这一天，发布后再来提交成果。'
  }
  const when = day.effectiveUnlockAt || day.scheduledUnlockAt || day.trainingDate
  if (when) return `这一天将在 ${formatDate(when, true)} 开放，到时再进入详情完成交付。`
  return '训练日尚未开放，暂时不能提交。'
}

export function formatDateTime(value) {
  if (!value) return '未设置'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}

export function submissionStatusLabel(status) {
  return {
    PENDING_REVIEW: '等待老师反馈',
    REVIEWING: '审核中',
    APPROVED: '已通过',
    CHANGES_REQUESTED: '需要修改',
    REJECTED: '未通过'
  }[String(status || '').toUpperCase()] || '未提交'
}

export function scoreTone(score) {
  const numeric = Number(score || 0)
  if (numeric >= 85) return '表现优秀'
  if (numeric >= 70) return '继续提升'
  if (numeric > 0) return '重点改进'
  return '暂无评分'
}
