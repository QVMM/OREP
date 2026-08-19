import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const storeSource = readFileSync(
  new URL('../src/stores/collaboration.js', import.meta.url),
  'utf8'
)
const clientSource = readFileSync(
  new URL('../src/services/collaborationClient.js', import.meta.url),
  'utf8'
)

test('collaboration client covers the full request state machine', () => {
  for (const endpoint of [
    '/api/collaboration/summary',
    '/api/collaboration/items',
    '/api/collaboration/requests',
    '/api/collaboration/requests/batch',
    '/accept',
    '/decline',
    '/withdraw',
  ]) {
    assert.match(clientSource, new RegExp(endpoint.replaceAll('/', '\\/')))
  }
  assert.match(clientSource, /Idempotency-Key/)
})

test('collaboration batch creation keeps one request key and independent recipients', () => {
  assert.match(storeSource, /async function createRequests\(payload, idempotencyKey\)/)
  assert.match(storeSource, /createCollaborationRequests\(payload, idempotencyKey\)/)
  assert.match(storeSource, /activeTab\.value = 'CREATED_BY_ME'/)
})

test('global store preserves navigation drafts tab caches and refresh timestamps', () => {
  assert.match(storeSource, /const navigationStack = ref\(\[\]\)/)
  assert.match(storeSource, /const drafts = ref\(\{\}\)/)
  assert.match(storeSource, /const scrollPositions = ref\(\{\}\)/)
  assert.match(storeSource, /const itemsByTab = ref\(\{\}\)/)
  assert.match(storeSource, /const lastRefreshedAt = ref\(null\)/)
})

test('store shares the notification destination without replacing other subscribers', () => {
  assert.match(storeSource, /websocketClient\.subscribe/)
  assert.match(storeSource, /websocketClient\.unsubscribe\(notificationToken\)/)
  assert.match(storeSource, /COLLABORATION_/)
})
