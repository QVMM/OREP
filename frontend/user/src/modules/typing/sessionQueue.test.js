import test from 'node:test'
import assert from 'node:assert/strict'

const storage = new Map()
globalThis.localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
}

import {
  DURATION_UNSYNCED_MESSAGE,
  enqueueTypingSession,
  dequeueTypingSession,
  isTypingSessionQueued,
  listQueuedTypingSessions,
  upsertQueuedSessions,
  buildTypingSessionTrackDetail,
  flushQueuedTypingSessions,
} from './sessionQueue.js'

function payload(patch = {}) {
  return {
    clientSessionId: 'tp_1_abc',
    mode: 'practice',
    elapsedMs: 15_000,
    correctChars: 8,
    durationSec: 300,
    ...patch,
  }
}

test('enqueue then lookup by clientSessionId', () => {
  storage.clear()
  enqueueTypingSession(payload(), { reason: 'complete' })
  assert.equal(isTypingSessionQueued('tp_1_abc'), true)
  assert.equal(listQueuedTypingSessions().length, 1)
})

test('same clientSessionId keeps the longer elapsedMs', () => {
  storage.clear()
  enqueueTypingSession(payload({ elapsedMs: 8_000 }), { reason: 'checkpoint' })
  enqueueTypingSession(payload({ elapsedMs: 20_000 }), { reason: 'pagehide' })
  enqueueTypingSession(payload({ elapsedMs: 12_000 }), { reason: 'complete' })
  const [item] = listQueuedTypingSessions()
  assert.equal(item.payload.elapsedMs, 20_000)
  assert.equal(item.reason, 'complete')
  assert.equal(listQueuedTypingSessions().length, 1)
})

test('dequeue removes only that session', () => {
  storage.clear()
  enqueueTypingSession(payload({ clientSessionId: 'a' }), { reason: 'pagehide' })
  enqueueTypingSession(payload({ clientSessionId: 'b', elapsedMs: 4000 }), { reason: 'complete' })
  dequeueTypingSession('a')
  assert.equal(isTypingSessionQueued('a'), false)
  assert.equal(isTypingSessionQueued('b'), true)
})

test('track detail carries reason, httpStatus, elapsedMs, downgrade', () => {
  const detail = buildTypingSessionTrackDetail({
    reason: 'complete',
    httpStatus: 500,
    payload: payload({ elapsedMs: 90_000, mode: 'practice' }),
    rankedDowngraded: true,
    ok: false,
    queued: true,
  })
  assert.deepEqual(detail, {
    reason: 'complete',
    httpStatus: 500,
    elapsedMs: 90_000,
    rankedDowngraded: true,
    ok: false,
    queued: true,
    keepalive: false,
    mode: 'practice',
    clientSessionId: 'tp_1_abc',
  })
})

test('unsynced copy is explicit, not a raw network error', () => {
  assert.match(DURATION_UNSYNCED_MESSAGE, /时长未同步/)
})

test('upsertQueuedSessions is a pure merge used by retry flush', () => {
  const next = upsertQueuedSessions(
    [{ clientSessionId: 'a', payload: payload({ clientSessionId: 'a', elapsedMs: 3000 }), reason: 'checkpoint', attempts: 1 }],
    payload({ clientSessionId: 'a', elapsedMs: 9000 }),
    { reason: 'retry', attempted: true },
  )
  assert.equal(next[0].payload.elapsedMs, 9000)
  assert.equal(next[0].attempts, 2)
  assert.equal(next[0].reason, 'retry')
})

test('flushQueuedTypingSessions drops successes and keeps failures', async () => {
  storage.clear()
  enqueueTypingSession(payload({ clientSessionId: 'ok' }), { reason: 'pagehide' })
  enqueueTypingSession(payload({ clientSessionId: 'bad', elapsedMs: 4000 }), { reason: 'complete' })
  const results = await flushQueuedTypingSessions(async (body) => {
    if (body.clientSessionId === 'bad') {
      const err = new Error('fail')
      err.httpStatus = 500
      throw err
    }
    return { id: 9 }
  })
  assert.equal(results.filter((r) => r.ok).length, 1)
  assert.equal(isTypingSessionQueued('ok'), false)
  assert.equal(isTypingSessionQueued('bad'), true)
  assert.equal(listQueuedTypingSessions()[0].attempts, 1)
})
