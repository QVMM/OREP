import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const viewSource = readFileSync(
  new URL('../src/views/team/TeamCreateView.vue', import.meta.url),
  'utf8'
)
const apiSource = readFileSync(
  new URL('../src/api/index.js', import.meta.url),
  'utf8'
)

test('team creation role picker supports searching and creating positions', () => {
  assert.match(viewSource, /<el-select[\s\S]*?filterable[\s\S]*?allow-create[\s\S]*?default-first-option/)
  assert.match(viewSource, /@change="setRole\(member\.id, \$event\)"/)
  assert.match(viewSource, /<el-option v-for="role in roles"/)
})

test('custom positions are normalized, length checked, persisted, and reused', () => {
  assert.match(viewSource, /const MAX_ROLE_NAME_LENGTH = 80/)
  assert.match(viewSource, /normalizeRoleName/)
  assert.match(viewSource, /createPositionRole\(\{ name: role \}\)/)
  assert.match(viewSource, /岗位名称最多 \$\{MAX_ROLE_NAME_LENGTH\} 个字符/)
  assert.match(viewSource, /roles\.value\.includes\(role\)/)
  assert.match(viewSource, /roles\.value = \[\.\.\.roles\.value, savedRole\]/)
})

test('teacher API exposes tenant position creation', () => {
  assert.match(apiSource, /export async function createPositionRole\(payload\)/)
  assert.match(apiSource, /request\.post\('\/api\/project-teams\/position-roles', payload\)/)
})

test('team creation payload still sends actual member position names', () => {
  assert.match(viewSource, /captainPositionName: memberRole\(form\.captainId\)/)
  assert.match(viewSource, /positionName: m\.role/)
})
