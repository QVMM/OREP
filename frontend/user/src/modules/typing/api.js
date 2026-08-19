import request from '@/utils/request'
import { getUserToken } from '@/utils/authStorage'
import { trackFrontendEvent } from '@/utils/monitor'
import { shouldPersistTypingSession } from './sessionPersist'
import {
  buildTypingSessionTrackDetail,
  dequeueTypingSession,
  enqueueTypingSession,
  flushQueuedTypingSessions,
  resolveHttpStatus,
} from './sessionQueue'

export { shouldPersistTypingSession } from './sessionPersist'
export {
  DURATION_UNSYNCED_MESSAGE,
  flushQueuedTypingSessions,
  isTypingSessionQueued,
} from './sessionQueue'

function unwrap(res) {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) return res.data
  return res
}

function trackTypingSessionSave({
  reason,
  httpStatus,
  payload,
  rankedDowngraded,
  ok,
  queued,
  keepalive,
}) {
  trackFrontendEvent({
    source: 'user_frontend',
    actionType: 'typing_session_save',
    actionName: `typing_session ${reason || 'complete'}`,
    route: typeof window !== 'undefined' ? window.location.pathname + window.location.search : '',
    pageTitle: typeof document !== 'undefined' ? document.title : '',
    detail: buildTypingSessionTrackDetail({
      reason,
      httpStatus,
      payload,
      rankedDowngraded,
      ok,
      queued,
      keepalive,
    }),
  }, Boolean(keepalive))
}

function isRankedDowngraded(payload, remote, requestedMode) {
  if (remote?.rankedDowngraded) return true
  return requestedMode === 'ranked' && (remote?.mode || payload?.mode) === 'practice'
}

export async function saveTypingSession(payload, options = {}) {
  const reason = options.reason || 'complete'
  const requestedMode = options.requestedMode || payload?.mode
  const body = { ...payload, reason }
  try {
    const remote = unwrap(await request.post('/api/typing/sessions', body, {
      silentError: true,
      timeout: options.timeout || 20000,
    }))
    if (payload?.clientSessionId) dequeueTypingSession(payload.clientSessionId)
    trackTypingSessionSave({
      reason,
      httpStatus: 200,
      payload,
      rankedDowngraded: isRankedDowngraded(payload, remote, requestedMode),
      ok: true,
      queued: false,
      keepalive: false,
    })
    return remote
  } catch (err) {
    if (!options.fromQueue) {
      enqueueTypingSession(payload, {
        reason,
        attempted: true,
        httpStatus: resolveHttpStatus(err),
      })
    }
    trackTypingSessionSave({
      reason,
      httpStatus: resolveHttpStatus(err),
      payload,
      rankedDowngraded: isRankedDowngraded(payload, null, requestedMode),
      ok: false,
      queued: true,
      keepalive: false,
    })
    throw err
  }
}

export async function flushTypingSessionQueue() {
  return flushQueuedTypingSessions((payload, opts) => saveTypingSession(payload, {
    ...opts,
    reason: 'retry',
    fromQueue: true,
  }))
}

/** 离开页时尽量把已练时长带上鉴权发出去，避免「练了但没落库」。 */
export function flushTypingSessionKeepalive(payload, options = {}) {
  const reason = options.reason || 'pagehide'
  try {
    const token = getUserToken()
    if (!token || !payload || !shouldPersistTypingSession(payload)) return false
    if (reason === 'pagehide' && payload.clientSessionId) {
      enqueueTypingSession(payload, { reason })
    }
    fetch('/api/typing/sessions', {
      method: 'POST',
      keepalive: true,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...payload, reason }),
    }).then((res) => {
      const ok = Boolean(res?.ok)
      if (ok && payload.clientSessionId) dequeueTypingSession(payload.clientSessionId)
      if (!ok && payload.clientSessionId) {
        enqueueTypingSession(payload, { reason, attempted: true, httpStatus: res?.status || 0 })
      }
      trackTypingSessionSave({
        reason,
        httpStatus: res?.status || 0,
        payload,
        rankedDowngraded: isRankedDowngraded(payload, null, options.requestedMode || payload.mode),
        ok,
        queued: !ok,
        keepalive: true,
      })
    }).catch(() => {
      if (payload.clientSessionId) {
        enqueueTypingSession(payload, { reason, attempted: true, httpStatus: 0 })
      }
      trackTypingSessionSave({
        reason,
        httpStatus: 0,
        payload,
        rankedDowngraded: isRankedDowngraded(payload, null, options.requestedMode || payload.mode),
        ok: false,
        queued: true,
        keepalive: true,
      })
    })
    return true
  } catch {
    if (payload?.clientSessionId) enqueueTypingSession(payload, { reason, attempted: true, httpStatus: 0 })
    return false
  }
}

export async function fetchTypingLeaderboard(params = {}) {
  return unwrap(await request.get('/api/typing/leaderboard', {
    params,
    silentError: true,
  }))
}

export async function fetchTypingMyStats() {
  return unwrap(await request.get('/api/typing/me/stats', { silentError: true }))
}

/** AI 教练点评（服务端规则引擎；失败时前端本地兜底） */
export async function fetchTypingCoach(payload) {
  return unwrap(await request.post('/api/typing/coach', payload, { silentError: true }))
}

/** 账户级自定义文案 */
export async function listTypingCustomTexts() {
  const data = unwrap(await request.get('/api/typing/custom-texts', { silentError: true }))
  return Array.isArray(data) ? data : []
}

export async function createTypingCustomText({ title, content }) {
  return unwrap(await request.post('/api/typing/custom-texts', { title, content }))
}

export async function updateTypingCustomText(id, { title, content }) {
  return unwrap(await request.put(`/api/typing/custom-texts/${id}`, { title, content }))
}

export async function deleteTypingCustomText(id) {
  return unwrap(await request.delete(`/api/typing/custom-texts/${id}`))
}
