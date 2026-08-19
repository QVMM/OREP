import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const editorSource = readFileSync(
  new URL('../src/components/training/TrainingLearningResourcesEditor.vue', import.meta.url),
  'utf8'
)
const serviceSource = readFileSync(
  new URL('../../../backend/src/main/java/com/orep/backend/service/TrainingDayLearningResourceService.java', import.meta.url),
  'utf8'
)

test('uploaded learning files default to the original file name without its extension', () => {
  assert.match(editorSource, /title:\s*defaultFileTitle\(file\)/)
  assert.match(editorSource, /replace\(\/\\\.\[\^\.\]\+\$\/,\s*''\)/)
  assert.match(serviceSource, /if \(title == null\) title = stripExtension\(displayName\)/)
})

test('teacher resource rows clearly expose an editable video name', () => {
  assert.match(editorSource, /视频名称/)
  assert.match(editorSource, /placeholder="请输入学生看到的名称"/)
  assert.match(editorSource, /updateField\(item,\s*'title'/)
  assert.match(editorSource, /名称默认取自原文件名，可直接修改/)
})
