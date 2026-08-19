/** 打字落库失败队列：本机重试 + 结果页「时长未同步」文案 + 打点字段。 */

export const DURATION_UNSYNCED_MESSAGE = '时长未同步，已保存在本机，回到练习页后会自动补记'
export const TYPING_SESSION_QUEUE_PREFIX = 'orep_typing_session_queue_v1'
const MAX_ITEMS = 20
const MAX_ATTEMPTS = 8

function userScope() {
  try {
    const raw = localStorage.getItem('orep_user') || localStorage.getItem('user')
    const user = raw ? JSON.parse(raw) : null
    return String(user?.id || user?.userId || user?.username || 'anon')
  } catch {
    return 'anon'
  }
}

export function typingSessionQueueKey() {
  return `${TYPING_SESSION_QUEUE_PREFIX}:${userScope()}`
}

export function listQueuedTypingSessions() {
  try {
    const raw = localStorage.getItem(typingSessionQueueKey())
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function persistQueue(list) {
  try {
    localStorage.setItem(typingSessionQueueKey(), JSON.stringify(list.slice(-MAX_ITEMS)))
  } catch {
    // quota
  }
}

export function isTypingSessionQueued(clientSessionId) {
  const id = clientSessionId ? String(clientSessionId) : ''
  if (!id) return false
  return listQueuedTypingSessions().some((item) => item.clientSessionId === id)
}

export function upsertQueuedSessions(queue, payload, meta = {}) {
  if (!payload || !payload.clientSessionId) return Array.isArray(queue) ? queue : []
  const id = String(payload.clientSessionId).slice(0, 64)
  const now = Date.now()
  const list = Array.isArray(queue) ? queue.map((item) => ({ ...item })) : []
  const idx = list.findIndex((item) => item.clientSessionId === id)
  const incomingMs = Number(payload.elapsedMs) || 0
  if (idx < 0) {
    list.push({
      clientSessionId: id,
      payload: { ...payload, clientSessionId: id },
      reason: meta.reason || 'complete',
      attempts: meta.attempted ? 1 : 0,
      lastHttpStatus: meta.httpStatus ?? null,
      queuedAt: now,
      updatedAt: now,
    })
    return list.slice(-MAX_ITEMS)
  }
  const prev = list[idx]
  const prevMs = Number(prev.payload?.elapsedMs) || 0
  list[idx] = {
    ...prev,
    payload: incomingMs >= prevMs ? { ...payload, clientSessionId: id } : prev.payload,
    reason: meta.reason || prev.reason,
    attempts: meta.attempted ? (Number(prev.attempts) || 0) + 1 : (Number(prev.attempts) || 0),
    lastHttpStatus: meta.httpStatus ?? prev.lastHttpStatus,
    updatedAt: now,
  }
  return list
}

export function enqueueTypingSession(payload, meta = {}) {
  if (!payload?.clientSessionId) return listQueuedTypingSessions()
  const next = upsertQueuedSessions(listQueuedTypingSessions(), payload, meta)
  persistQueue(next)
  return next
}

export function dequeueTypingSession(clientSessionId) {
  const id = clientSessionId ? String(clientSessionId) : ''
  if (!id) return listQueuedTypingSessions()
  const next = listQueuedTypingSessions().filter((item) => item.clientSessionId !== id)
  persistQueue(next)
  return next
}

export function buildTypingSessionTrackDetail({
  reason = 'complete',
  httpStatus = 0,
  payload = {},
  rankedDowngraded = false,
  ok = false,
  queued = false,
  keepalive = false,
} = {}) {
  return {
    reason,
    httpStatus: Number(httpStatus) || 0,
    elapsedMs: Number(payload?.elapsedMs) || 0,
    rankedDowngraded: Boolean(rankedDowngraded),
    ok: Boolean(ok),
    queued: Boolean(queued),
    keepalive: Boolean(keepalive),
    mode: payload?.mode || '',
    clientSessionId: payload?.clientSessionId || '',
  }
}

export function resolveHttpStatus(error) {
  if (error == null) return 0
  if (Number.isFinite(error.httpStatus)) return Number(error.httpStatus)
  if (Number.isFinite(error.response?.status)) return Number(error.response.status)
  if (error.code === 'ECONNABORTED') return 0
  return 0
}

export function shouldRetryQueuedItem(item) {
  return Boolean(item?.payload?.clientSessionId) && (Number(item.attempts) || 0) < MAX_ATTEMPTS
}

let flushInFlight = null

/** saveFn(payload, { reason }) → Promise. 成功由调用方 dequeue，失败再记一次 attempts。 */
export async function flushQueuedTypingSessions(saveFn) {
  if (typeof saveFn !== 'function') return []
  if (flushInFlight) return flushInFlight
  flushInFlight = (async () => {
    const results = []
    const items = listQueuedTypingSessions().filter(shouldRetryQueuedItem)
    for (const item of items) {
      try {
        const remote = await saveFn(item.payload, { reason: 'retry' })
        dequeueTypingSession(item.clientSessionId)
        results.push({ clientSessionId: item.clientSessionId, ok: true, remote })
      } catch (err) {
        enqueueTypingSession(item.payload, {
          reason: 'retry',
          attempted: true,
          httpStatus: resolveHttpStatus(err),
        })
        results.push({
          clientSessionId: item.clientSessionId,
          ok: false,
          httpStatus: resolveHttpStatus(err),
        })
      }
    }
    return results
  })()
  try {
    return await flushInFlight
  } finally {
    flushInFlight = null
  }
}
