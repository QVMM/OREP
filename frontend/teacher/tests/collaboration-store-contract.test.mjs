import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const store = readFileSync(new URL('../src/stores/collaboration.js', import.meta.url), 'utf8')
const client = readFileSync(new URL('../src/services/collaborationClient.js', import.meta.url), 'utf8')

test('teacher collaboration store supports unified tabs team scope publish and review workflows', () => {
  assert.match(store, /const activeTab = ref\('ACTION_REQUIRED'\)/)
  assert.match(store, /const activeTeamId = ref\('all'\)/)
  assert.match(store, /fetchTeacherCollaborationItems/)
  assert.match(store, /visibleItems/)
  assert.match(store, /showTaskForm/)
  assert.match(store, /publishTask/)
  assert.match(store, /reviewSubmission/)
  assert.match(store, /acceptRequest/)
  assert.match(store, /declineRequest/)
  assert.match(store, /syncContextTeam/)
})

test('teacher client reuses unified reads formal task writes and submission review APIs', () => {
  assert.match(client, /\/api\/collaboration\/items/)
  assert.match(client, /\/api\/collaboration\/summary/)
  assert.match(client, /createTeamTask/)
  assert.match(client, /sourceType: 'TEACHER_ASSIGNMENT'/)
  assert.match(client, /reviewSubmission/)
  assert.match(client, /\/accept/)
  assert.match(client, /\/decline/)
})
