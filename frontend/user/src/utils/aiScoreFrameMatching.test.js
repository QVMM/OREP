import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildVisualFrameEndpoints,
  findFrameByAnchor,
  findFrameNearSeconds,
  frameSeconds
} from './aiScoreFrameMatching.js'

test('uploaded video frames only load from session endpoint', () => {
  assert.deepEqual(
    buildVisualFrameEndpoints({
      effectiveSessionId: 19,
      effectiveMeetingId: -19,
      sourceType: 'uploaded_video'
    }),
    ['/api/ai/session/19/visual-frames']
  )
})

test('session-only reports do not fall back to meeting frames when source type is missing', () => {
  assert.deepEqual(
    buildVisualFrameEndpoints({
      effectiveSessionId: 19,
      effectiveMeetingId: -19,
      sourceType: ''
    }),
    ['/api/ai/session/19/visual-frames']
  )

  assert.deepEqual(
    buildVisualFrameEndpoints({
      effectiveSessionId: 19,
      effectiveMeetingId: null,
      sourceType: ''
    }),
    ['/api/ai/session/19/visual-frames']
  )
})

test('meeting recording may fall back to meeting frame endpoints', () => {
  assert.deepEqual(
    buildVisualFrameEndpoints({
      effectiveSessionId: 8,
      effectiveMeetingId: 18,
      sourceType: 'meeting_recording'
    }),
    [
      '/api/ai/session/8/visual-frames',
      '/api/ai/meeting/18/visual-frames'
    ]
  )
})

test('anchor frame matching prefers hard frame id', () => {
  const frames = [
    { id: 'wrong', timestamp: 10, sessionId: '19' },
    { frame_id: 'frame-a', timestamp: 99, session_id: '19' }
  ]

  assert.equal(findFrameByAnchor({ frameId: 'frame-a', startMs: 10_000, sessionId: '19' }, frames, { sessionId: '19' }), frames[1])
})

test('anchor without hard frame id only falls back within three seconds and same session', () => {
  const frames = [
    { frame_id: 'same-near', timestamp: 10.8, session_id: '19' },
    { frame_id: 'same-far', timestamp: 20, session_id: '19' },
    { frame_id: 'other-near', timestamp: 10.1, session_id: 'old' }
  ]

  assert.equal(findFrameByAnchor({ startMs: 10_000, sessionId: '19' }, frames, { sessionId: '19' }), frames[0])
  assert.equal(findFrameByAnchor({ startMs: 10_000, sessionId: 'missing' }, frames, { sessionId: 'missing' }), null)
})

test('frameSeconds accepts both seconds and milliseconds fields', () => {
  assert.equal(frameSeconds({ timestamp_ms: 12_000 }), 12)
  assert.equal(frameSeconds({ timestampMs: 8_500 }), 8.5)
  assert.equal(frameSeconds({ timestamp: 7 }), 7)
})

test('nearest frame rejects matches outside threshold', () => {
  const frames = [{ frame_id: 'far', timestamp: 15, session_id: '19' }]
  assert.equal(findFrameNearSeconds(10, frames, { sessionId: '19' }), null)
})

test('nearest frame requires frame session when session is specified', () => {
  const frames = [{ frame_id: 'missing-session', timestamp: 10.2 }]
  assert.equal(findFrameNearSeconds(10, frames, { sessionId: '19' }), null)
})
