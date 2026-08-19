import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const brand = readFileSync(
  new URL('../src/components/collaboration/CollaborationBrandMark.vue', import.meta.url),
  'utf8'
)
const hub = readFileSync(
  new URL('../src/components/collaboration/CollaborationHub.vue', import.meta.url),
  'utf8'
)
const row = readFileSync(
  new URL('../src/components/collaboration/CollaborationItemRow.vue', import.meta.url),
  'utf8'
)

test('collaboration mark uses the approved connected-node svg with brand gradient', () => {
  assert.match(brand, /M654\.108444 517\.12L499\.143111 458\.24/)
  assert.match(brand, /collaboration-network-gradient/)
  assert.match(brand, /stroke-width: 18/)
  assert.match(brand, /width: 40px/)
  assert.match(brand, /height: 40px/)
  assert.match(brand, /border: 0/)
  assert.match(brand, /background: transparent/)
  assert.doesNotMatch(brand, /is-orange|is-blue|is-green|is-purple/)
})

test('student hub routes tasks directly while request items keep request detail actions', () => {
  assert.match(hub, /item\.entityType === 'TASK'/)
  assert.match(hub, /item\.targetPath/)
  assert.match(hub, /item\.key/)
  assert.match(row, /item\.sourceLabel/)
  assert.match(row, /TRAINING_DAY/)
  assert.match(row, /TEACHER_ASSIGNMENT/)
  assert.match(row, /PEER_COLLABORATION/)
})
