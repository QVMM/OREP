import request from '../utils/request'
import { getToken } from '../utils/auth'

const base = '/api/assistant'

function getUserToken() {
  return getToken()
}

export function listSessions(params = {}) {
  return request.get(`${base}/sessions`, { params })
}

export function createSession(body = {}) {
  return request.post(`${base}/sessions`, {
    ...body,
    context: { ...(body.context || {}), audience: 'teacher', client: 'teacher-web' },
  })
}

export function getSession(id) {
  return request.get(`${base}/sessions/${id}`)
}

export function patchSession(id, body) {
  return request.patch(`${base}/sessions/${id}`, body)
}

export function deleteSession(id) {
  return request.delete(`${base}/sessions/${id}`)
}

export function listMessages(sessionId, params = {}) {
  return request.get(`${base}/sessions/${sessionId}/messages`, { params })
}

export function cancelRun(runId) {
  return request.post(`${base}/runs/${runId}/cancel`)
}

export function listFiles(sessionId) {
  return request.get(`${base}/sessions/${sessionId}/files`)
}

export function uploadFile(sessionId, file) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`${base}/sessions/${sessionId}/files`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function deleteFile(fileId) {
  return request.delete(`${base}/files/${fileId}`)
}

export function saveCodeAsFile(body) {
  return request.post(`${base}/code/save-as-file`, body)
}

export function saveFileToResource(fileId, body) {
  return request.post(`${base}/files/${fileId}/save-to-resource`, body)
}

export function saveReply(sessionId, body) {
  return request.post(`${base}/sessions/${sessionId}/save-reply`, body)
}

export function listMemories() {
  return request.get(`${base}/memories`)
}

export function createMemory(body) {
  return request.post(`${base}/memories`, body)
}

export function deleteMemory(id) {
  return request.delete(`${base}/memories/${id}`)
}

export function shareSession(sessionId, body) {
  return request.post(`${base}/sessions/${sessionId}/share`, body)
}

export function exportSessionPdf(sessionId) {
  return request.post(`${base}/sessions/${sessionId}/export-pdf`, {}, { timeout: 60000 })
}

export function listTeams() {
  return request.get(`${base}/teams`)
}

/** 确认小启提出的写操作 */
export function confirmAction(proposalId) {
  return request.post(`${base}/actions/${proposalId}/confirm`)
}

/** 取消写操作提案 */
export function rejectAction(proposalId) {
  return request.post(`${base}/actions/${proposalId}/reject`)
}

export function resourcePicker(teamId) {
  return request.get(`${base}/resource-picker`, { params: { teamId } })
}

/**
 * SSE stream via fetch (supports Authorization header).
 * onEvent(eventName, dataObject)
 */
async function consumeSse(res, onEvent) {
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventName = 'message'
  let dataLines = []

  const flush = () => {
    if (!dataLines.length) return
    const raw = dataLines.join('\n')
    dataLines = []
    let data = raw
    try {
      data = JSON.parse(raw)
    } catch {
      /* keep string */
    }
    onEvent?.(eventName, data)
    eventName = 'message'
  }

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split(/\r?\n/)
    buffer = parts.pop() || ''
    for (const line of parts) {
      if (line === '') {
        flush()
        continue
      }
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim())
      }
    }
  }
  flush()
}

export async function streamMessage(sessionId, body, { signal, onEvent } = {}) {
  const token = getUserToken()
  const res = await fetch(`${base}/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      ...body,
      options: { ...(body?.options || {}), audience: 'teacher' },
    }),
    signal,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  await consumeSse(res, onEvent)
}

export async function regenerateMessage(sessionId, userMessageId, { signal, onEvent } = {}) {
  const token = getUserToken()
  const res = await fetch(
    `${base}/sessions/${sessionId}/messages/${userMessageId}/regenerate/stream`,
    {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal,
    }
  )
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  await consumeSse(res, onEvent)
}

/** 重连进行中的 run，收实时进度（刷新后恢复） */
export async function subscribeRun(runId, { signal, onEvent } = {}) {
  const token = getUserToken()
  const res = await fetch(`${base}/runs/${runId}/events/stream`, {
    method: 'GET',
    headers: {
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  await consumeSse(res, onEvent)
}

export function filePreviewUrl(fileId) {
  const token = getUserToken()
  return `${base}/files/${fileId}/preview?t=${encodeURIComponent(token || '')}`
}

export function fileDownloadUrl(fileId) {
  const token = getUserToken()
  return `${base}/files/${fileId}/download?t=${encodeURIComponent(token || '')}`
}
