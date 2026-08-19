import request from './request'

function unwrap(response) {
  return response?.data ?? response
}

export async function createAiScoreSession(payload) {
  const safePayload = {
    sourceType: payload.sourceType || 'meeting_recording',
    sourceId: payload.sourceId || null,
    projectId: payload.projectId || null,
    teamId: payload.teamId || null,
    meetingId: payload.meetingId || null,
    recordingId: payload.recordingId || null,
    trackId: payload.trackId || '',
    trackName: payload.trackName || '',
    useHistoryMemory: payload.useHistoryMemory !== false,
    juryEnabled: Boolean(payload.juryEnabled)
  }
  return unwrap(await request.post('/api/ai-score/sessions', safePayload))
}

export async function startAiScoreSession(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/start`))
}

export async function cancelAiScoreSession(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/cancel`))
}

export async function restartAiScoreSession(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/restart`))
}

export async function getAiScoreSessionStatus(sessionId) {
  return unwrap(await request.get(`/api/ai-score/sessions/${sessionId}/status`))
}

export async function getLatestAiScoreSession(params = {}) {
  return unwrap(await request.get('/api/ai-score/sessions/latest', { params }))
}

