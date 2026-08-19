import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const extSource = [
  readFileSync(new URL('../views/inspire-office/smart-doc/schema/smartDocExtensions.js', import.meta.url), 'utf8'),
  readFileSync(new URL('../views/inspire-office/smart-doc/schema/smartDocBlocks.js', import.meta.url), 'utf8'),
].join('\n')
const editorSource = readFileSync(
  new URL('../views/inspire-office/smart-doc/SmartDocEditor.vue', import.meta.url),
  'utf8'
)

test('smart doc schema includes highlight block and slash catalog', () => {
  assert.match(extSource, /HighlightBlock/)
  assert.match(extSource, /SLASH_ITEMS/)
  assert.match(extSource, /高亮块/)
})

test('smart doc editor matches Kingsoft layout landmarks', () => {
  assert.match(editorSource, /sdoc-fmt/)
  assert.match(editorSource, /目录/)
  assert.match(editorSource, /输入标题/)
  assert.match(extSource, /输入正文或/)
  assert.doesNotMatch(editorSource, /WPS AI/)
  assert.doesNotMatch(editorSource, /小启/)
})
