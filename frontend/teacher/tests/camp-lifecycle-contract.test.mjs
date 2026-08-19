import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const viewSource = readFileSync(
  new URL('../src/views/camp/CampWorkspaceView.vue', import.meta.url),
  'utf8'
)
const apiSource = readFileSync(
  new URL('../src/api/index.js', import.meta.url),
  'utf8'
)

test('camp workspace exposes schedule, extend and deletion management', () => {
  assert.match(viewSource, /延长训练天数/)
  assert.match(viewSource, /调整开始日期/)
  assert.match(viewSource, /删除训练营/)
  assert.match(viewSource, /归档保留记录/)
  assert.match(viewSource, /彻底删除全部信息/)
})

test('permanent deletion requires the exact camp name', () => {
  assert.match(viewSource, /confirmationName/)
  assert.match(viewSource, /请输入完整集训名称/)
  assert.match(viewSource, /campMeta\.campName/)
})

test('rescheduling explains submission protection and previews the end date', () => {
  assert.match(viewSource, /已有学生提交，不能直接改期/)
  assert.match(viewSource, /newEndDate/)
  assert.match(viewSource, /totalDays/)
})

test('extending days only appends and previews the new total', () => {
  assert.match(viewSource, /再增加天数/)
  assert.match(viewSource, /只在营期后面追加新的训练日草稿/)
  assert.match(viewSource, /previewTotalDays/)
  assert.match(viewSource, /extendTeacherCamp/)
})

test('teacher API exposes reschedule, extend and two-mode deletion', () => {
  assert.match(apiSource, /rescheduleTeacherCamp/)
  assert.match(apiSource, /\/schedule/)
  assert.match(apiSource, /extendTeacherCamp/)
  assert.match(apiSource, /\/duration/)
  assert.match(apiSource, /deleteTeacherCamp/)
  assert.match(apiSource, /data:\s*payload/)
})
