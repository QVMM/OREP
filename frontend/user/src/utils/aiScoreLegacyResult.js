function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

export function buildLegacyAiResultEndpoints({ result = {}, meetingId = null, sessionId = null } = {}) {
  const candidates = [
    firstPresent(result.meeting_id, result.meetingId, meetingId),
    firstPresent(result.session_id, result.sessionId, sessionId)
  ]
  const seen = new Set()
  return candidates
    .filter(value => value !== undefined && value !== null && value !== '')
    .map(value => String(value))
    .filter(value => {
      if (seen.has(value)) return false
      seen.add(value)
      return true
    })
    .map(value => `/api/ai/result/${value}`)
}
