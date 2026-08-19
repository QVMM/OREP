import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const editorSource = readFileSync(
  new URL('../src/components/training/TrainingLearningResourcesEditor.vue', import.meta.url),
  'utf8'
)
const apiSource = readFileSync(
  new URL('../src/api/index.js', import.meta.url),
  'utf8'
)

test('learning resource uploads use a dedicated long timeout and expose progress', () => {
  assert.match(
    apiSource,
    /TEACHER_LEARNING_UPLOAD_TIMEOUT_MS\s*=\s*2\s*\*\s*60\s*\*\s*60\s*\*\s*1000/
  )
  assert.match(apiSource, /onUploadProgress:\s*options\.onUploadProgress/)
  assert.match(apiSource, /timeout:\s*options\.timeout\s*\?\?\s*TEACHER_LEARNING_UPLOAD_TIMEOUT_MS/)
})

test('the learning editor shows an accessible upload state and disables duplicate uploads', () => {
  assert.match(editorSource, /uploading\s*\?\s*'上传中…'\s*:\s*'上传视频或资料'/)
  assert.match(editorSource, /class="learning-editor__upload-progress"/)
  assert.match(editorSource, /aria-live="polite"/)
  assert.match(editorSource, /:role="error\s*\?\s*'alert'\s*:\s*'status'"/)
})

test('successful files are committed immediately and the batch produces one global result message', () => {
  assert.match(editorSource, /commit\(\[\.\.\.resources\.value,\s*uploaded\]\)/)
  assert.match(editorSource, /failures\.push\(/)
  assert.match(editorSource, /ElMessage\.success\(/)
  assert.match(editorSource, /ElMessage\.warning\(/)
  assert.match(editorSource, /ElMessage\.error\(/)
})
