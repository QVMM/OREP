const PREFIX = 'orep:training-submit-draft:v1'

function userScope() {
  try {
    const raw = localStorage.getItem('orep_user') || localStorage.getItem('user')
    const user = raw ? JSON.parse(raw) : null
    return String(user?.id || user?.userId || user?.username || 'anon')
  } catch {
    return 'anon'
  }
}

export function submissionDraftKey(taskId) {
  return `${PREFIX}:${userScope()}:${taskId}`
}

export function loadSubmissionDraft(taskId) {
  if (!taskId) return null
  try {
    const raw = localStorage.getItem(submissionDraftKey(taskId))
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data || typeof data !== 'object') return null
    return data
  } catch {
    return null
  }
}

export function saveSubmissionDraft(taskId, patch) {
  if (!taskId) return
  const prev = loadSubmissionDraft(taskId) || {}
  const next = { ...prev, ...patch, updatedAt: Date.now() }
  try {
    localStorage.setItem(submissionDraftKey(taskId), JSON.stringify(next))
  } catch {
    // ignore quota
  }
}

export function clearSubmissionDraft(taskId) {
  if (!taskId) return
  try {
    localStorage.removeItem(submissionDraftKey(taskId))
  } catch {
    // ignore
  }
}

export function uploadTimeoutMs(file) {
  const size = Number(file?.size || 0)
  const mb = size / (1024 * 1024)
  return Math.min(15 * 60 * 1000, Math.max(180000, Math.ceil(mb * 2500)))
}
