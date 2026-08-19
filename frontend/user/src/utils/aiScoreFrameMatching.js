const FRAME_MATCH_THRESHOLD_SECONDS = 3

export function isUploadedVideoSource(sourceType) {
  return String(sourceType || '').toLowerCase().includes('upload')
}

export function buildVisualFrameEndpoints({ effectiveSessionId, effectiveMeetingId, sourceType }) {
  const endpoints = []
  if (effectiveSessionId) endpoints.push(`/api/ai/session/${effectiveSessionId}/visual-frames`)
  if (isUploadedVideoSource(sourceType) || isSessionOnlyReport(effectiveSessionId, effectiveMeetingId)) return endpoints

  const meetingIds = uniqueValues([
    effectiveMeetingId,
    Number(effectiveMeetingId) < 0 ? Math.abs(Number(effectiveMeetingId)) : undefined
  ])
  endpoints.push(...meetingIds.map(id => `/api/ai/meeting/${id}/visual-frames`))
  return endpoints
}

function isSessionOnlyReport(effectiveSessionId, effectiveMeetingId) {
  if (!effectiveSessionId) return false
  if (effectiveMeetingId === undefined || effectiveMeetingId === null || effectiveMeetingId === '') return true
  return Number(effectiveMeetingId) < 0
}

export function normalizeVisualFrame(frame, index = 0, sessionId = '') {
  const backendId = firstPresent(frame.id, frame.frame_id, frame.frameId, frame.visual_frame_id, frame.visualFrameId)
  return {
    ...frame,
    backendId,
    sessionId: firstPresent(frame.sessionId, frame.session_id, sessionId),
    id: backendId || `frame-${index}`,
    timestampSeconds: frameSeconds(frame)
  }
}

export function findFrameByAnchor(anchor, frames, options = {}) {
  if (!anchor) return null
  if (anchor.frame && typeof anchor.frame === 'object') return anchor.frame

  const hardMatch = findFrameByHardId(anchor, frames)
  if (hardMatch) return hardMatch

  const seconds = secondsFromEvidence(anchor)
  if (seconds === null) return null
  return findFrameNearSeconds(seconds, frames, options)
}

export function findFrameByHardId(anchor, frames) {
  const frameId = firstPresent(anchor.frame_id, anchor.frameId, anchor.visual_frame_id, anchor.visualFrameId)
  if (frameId === undefined) return null
  return frames.find(frame => String(frameToken(frame)) === String(frameId)) || null
}

export function findFrameNearSeconds(seconds, frames, options = {}) {
  const value = Number(seconds)
  if (!Number.isFinite(value)) return null
  const sessionId = options.sessionId == null ? '' : String(options.sessionId)
  const threshold = Number(options.thresholdSeconds ?? FRAME_MATCH_THRESHOLD_SECONDS)
  const candidates = frames
    .filter(frame => {
      if (!sessionId) return true
      const frameSessionId = firstPresent(frame.sessionId, frame.session_id)
      return frameSessionId !== undefined && String(frameSessionId) === sessionId
    })
    .map(frame => ({ frame, distance: Math.abs(frameSeconds(frame) - value) }))
    .sort((a, b) => a.distance - b.distance)
  const nearest = candidates[0]
  return nearest && nearest.distance <= threshold ? nearest.frame : null
}

export function frameSeconds(frame) {
  if (!frame) return 0
  const seconds = firstPresent(frame.timestamp, frame.time_seconds, frame.timeSeconds, frame.position_seconds, frame.positionSeconds, frame.time)
  if (seconds !== undefined) return Number(seconds || 0)
  const ms = firstPresent(frame.timestamp_ms, frame.timestampMs)
  if (ms !== undefined) return Number(ms || 0) / 1000
  return 0
}

export function secondsFromEvidence(item) {
  const seconds = firstPresent(item?.timestamp, item?.time_seconds, item?.timeSeconds, item?.position_seconds, item?.positionSeconds)
  if (seconds !== undefined) return Number(seconds)
  const startMs = firstPresent(item?.startMs, item?.start_ms)
  if (startMs !== undefined) return Number(startMs || 0) / 1000
  return null
}

export function frameToken(frame) {
  return firstPresent(frame?.backendId, frame?.frame_id, frame?.frameId, frame?.visual_frame_id, frame?.visualFrameId, frame?.id)
}

function uniqueValues(values) {
  return [...new Set(values.filter(value => value !== undefined && value !== null && value !== '').map(String))]
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}
