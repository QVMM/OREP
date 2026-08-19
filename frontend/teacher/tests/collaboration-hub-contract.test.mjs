import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const shell = readFileSync(new URL('../src/components/TeacherShell.vue', import.meta.url), 'utf8')
const nav = readFileSync(new URL('../src/config/nav.js', import.meta.url), 'utf8')
const hub = readFileSync(
  new URL('../src/components/collaboration/TeacherCollaborationHub.vue', import.meta.url),
  'utf8'
)
const brand = readFileSync(
  new URL('../src/components/collaboration/CollaborationBrandMark.vue', import.meta.url),
  'utf8'
)

test('teacher shell owns a separate collaboration action outside normal route configuration', () => {
  assert.match(shell, /<TeacherCollaborationEntry \/>/)
  assert.match(shell, /<TeacherCollaborationHub \/>/)
  assert.doesNotMatch(nav, /key: 'collaboration'/)
})

test('teacher hub exposes unified task tabs team scope publication and compact platform sizing', () => {
  assert.match(hub, /团队范围/)
  assert.match(hub, /待我处理/)
  assert.match(hub, /我发起的/)
  assert.match(hub, /发布任务/)
  assert.match(hub, /item\.sourceLabel/)
  assert.match(hub, /item\.primaryAction === 'REVIEW'/)
  assert.match(hub, /width: min\(448px/)
  assert.match(hub, /border-radius: 16px/)
})

test('teacher collaboration entry uses the approved connected-node brand mark', () => {
  assert.match(brand, /M654\.108444 517\.12L499\.143111 458\.24/)
  assert.match(brand, /teacher-collaboration-network-gradient/)
  assert.match(brand, /stroke-width: 18/)
  assert.match(brand, /width: 40px/)
  assert.match(brand, /height: 40px/)
  assert.match(brand, /border: 0/)
  assert.match(brand, /background: transparent/)
  assert.doesNotMatch(brand, /nth-child/)
})
