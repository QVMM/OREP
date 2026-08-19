import test from 'node:test'
import assert from 'node:assert/strict'

import MeetingMediaRecorder from './mediaRecorder.js'

test('server media clock is retained instead of being replaced by a local clock', () => {
  const recorder = new MeetingMediaRecorder({ clockIdFactory: () => 'local-clock' })

  recorder.setMediaClockId('server-clock')

  assert.equal(recorder.getMediaClockId(), 'server-clock')
  assert.equal(recorder._resolveMediaClockId(), 'server-clock')
})

test('clearing the session clock allows a fresh local clock for legacy callers', () => {
  const recorder = new MeetingMediaRecorder({ clockIdFactory: () => 'local-clock' })

  recorder.setMediaClockId(null)

  assert.equal(recorder._resolveMediaClockId(), 'local-clock')
})

test('authoritative meeting session uploads media to the unified Java pipeline', async () => {
  const recorder = new MeetingMediaRecorder()
  recorder.setAuthoritativeSessionId(26)
  let requestedUrl = ''
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (url) => {
    requestedUrl = String(url)
    return new Response(JSON.stringify({ code: 200, data: { status: 'scoring' } }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  try {
    await recorder._uploadWithProgress(new FormData(), '', 1)
  } finally {
    globalThis.fetch = originalFetch
  }
  assert.equal(requestedUrl, '/api/ai-score/sessions/26/meeting-media')
})
