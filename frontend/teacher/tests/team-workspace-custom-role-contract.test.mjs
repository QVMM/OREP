import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  new URL('../src/views/team/TeamWorkspaceView.vue', import.meta.url),
  'utf8'
)

test('workspace member positions support searching and creating custom roles', () => {
  assert.match(source, /class="inline-position-select"/)
  assert.match(source, /filterable/)
  assert.match(source, /allow-create/)
  assert.match(source, /default-first-option/)
  assert.match(source, /@change="changeMemberRole\(member, \$event\)"/)
  assert.match(source, /<el-option v-for="role in roles"/)
})

test('new member positions are normalized, validated, and saved to the tenant library', () => {
  assert.match(source, /const MAX_POSITION_NAME_LENGTH = 80/)
  assert.match(source, /normalizePositionName/)
  assert.match(source, /createPositionRole\(\{ name: nextRole \}\)/)
  assert.match(source, /岗位名称最多 \$\{MAX_POSITION_NAME_LENGTH\} 个字符/)
  assert.match(source, /roleOptions\.value = \[\.\.\.roleOptions\.value/)
})

test('member position updates keep per-row save and rollback state', () => {
  assert.match(source, /savedRole: member\.positionName \|\| '项目成员'/)
  assert.match(source, /savingPosition: false/)
  assert.match(source, /member\.savingPosition = true/)
  assert.match(source, /updateTeamMemberPosition\(teamId\.value, member\.id, \{ positionName: member\.role \}\)/)
  assert.match(source, /member\.role = previousRole/)
})

test('mentor positions remain read-only', () => {
  assert.match(source, /:disabled="member\.roleInTeam === 'MENTOR' \|\| member\.savingPosition"/)
})
