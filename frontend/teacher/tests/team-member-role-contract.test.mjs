import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  new URL('../src/views/team/TeamWorkspaceView.vue', import.meta.url),
  'utf8'
)

test('member table exposes the authoritative global role', () => {
  assert.match(source, /<th>系统角色<\/th>/)
  assert.match(source, /v-model="member\.systemRole"/)
  assert.match(source, /@change="changeMemberSystemRole\(member\)"/)
})

test('candidate members use automatic detection with a per-user override', () => {
  assert.match(source, /v-model="member\.roleOverride"/)
  assert.match(source, /<option value="">自动识别/)
  assert.match(source, /systemRole:\s*selectedRoleFor\(candidate\)/)
})

test('role changes tell the operator that a new login is required', () => {
  assert.match(source, /重新登录后教师权限生效/)
})
