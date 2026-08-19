import test from 'node:test'
import assert from 'node:assert/strict'
import {
  isEmbedLearningActive,
  readOrCreateEmbedSessionId,
  embedSessionStorageKey,
} from './embedPlaybackPolicy.js'

test('iframe watch counts while page is visible after start', () => {
  assert.equal(isEmbedLearningActive({ pageVisible: true, activated: true }), true)
})

test('hidden tab or not started does not count', () => {
  assert.equal(isEmbedLearningActive({ pageVisible: false, activated: true }), false)
  assert.equal(isEmbedLearningActive({ pageVisible: true, activated: false }), false)
})

test('same resource reuses session id so remount does not reset heartbeat chain', () => {
  const storage = new Map()
  const api = {
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
  }
  const first = readOrCreateEmbedSessionId(api, 88, () => 'embed_aaaa1111')
  const second = readOrCreateEmbedSessionId(api, 88, () => 'embed_bbbb2222')
  assert.equal(first, 'embed_aaaa1111')
  assert.equal(second, 'embed_aaaa1111')
  assert.equal(storage.get(embedSessionStorageKey(88)), 'embed_aaaa1111')
})
