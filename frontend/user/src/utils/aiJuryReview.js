import request from './request'

export async function getJuryReviewBySession(sessionId) {
  if (!sessionId) return { status: 'empty' }
  const res = await request.get(`/api/ai-score/sessions/${sessionId}/jury/result`)
  return res.data || res
}

export async function startJuryReviewBySession(sessionId) {
  const res = await request.post(`/api/ai-score/sessions/${sessionId}/jury/start`)
  return res.data || res
}

export async function getLegacyJuryReviewByMeeting(meetingId) {
  if (!meetingId) return { status: 'empty' }
  const res = await request.get(`/api/ai/jury/${meetingId}/result`)
  return res.data || res
}

export async function startLegacyJuryReviewByMeeting(meetingId) {
  const res = await request.post(`/api/ai/jury/${meetingId}/start`, {})
  return res.data || res
}
