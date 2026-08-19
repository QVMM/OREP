import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const extSource = readFileSync(
  new URL('../src/views/inspire-office/smart-doc/schema/smartDocExtensions.js', import.meta.url),
  'utf8'
)
const blockSource = readFileSync(
  new URL('../src/views/inspire-office/smart-doc/schema/smartDocBlocks.js', import.meta.url),
  'utf8'
)
const schemaSource = `${extSource}\n${blockSource}`
const editorSource = readFileSync(
  new URL('../src/views/inspire-office/smart-doc/SmartDocEditor.vue', import.meta.url),
  'utf8'
)
const paneSource = readFileSync(
  new URL('../src/components/inspire-office/InspireOfficePane.vue', import.meta.url),
  'utf8'
)
const workbenchSource = readFileSync(
  new URL('../src/views/inspire-office/InspireOfficeWorkbench.vue', import.meta.url),
  'utf8'
)

test('smart doc schema includes highlight block and slash catalog', () => {
  assert.match(schemaSource, /HighlightBlock/)
  assert.match(schemaSource, /SLASH_ITEMS/)
  assert.match(schemaSource, /高亮块/)
  assert.match(schemaSource, /输入正文或/)
})

test('P1 schema has table, columns, file, cloud, date and media blocks', () => {
  assert.match(schemaSource, /extension-table/)
  assert.match(schemaSource, /name: 'columns'/)
  assert.match(schemaSource, /name: 'fileCard'/)
  assert.match(schemaSource, /name: 'cloudDoc'/)
  assert.match(schemaSource, /name: 'dateChip'/)
  assert.match(schemaSource, /name: 'mediaBlock'/)
  assert.match(schemaSource, /allowBase64: false/)
  assert.match(schemaSource, /label: '表格'/)
  assert.match(schemaSource, /label: '两栏'/)
  assert.match(schemaSource, /label: '本地文件'/)
  assert.match(schemaSource, /label: '云文档'/)
  assert.match(schemaSource, /label: '音视频'/)
})

test('smart doc editor matches Kingsoft layout landmarks and has no AI chrome', () => {
  assert.match(editorSource, /sdoc-fmt/)
  assert.match(editorSource, /目录/)
  assert.match(editorSource, /输入标题/)
  assert.match(editorSource, /格式刷/)
  assert.match(editorSource, /SdocIcon/)
  assert.match(editorSource, /toggleFind/)
  assert.match(editorSource, /toggleSuperscript/)
  assert.doesNotMatch(editorSource, /WPS AI/)
  assert.doesNotMatch(editorSource, /小启/)
  assert.match(editorSource, /embedded/)
  assert.match(editorSource, /insertTable|表格/)
})

test('toolbar format marks include color, size, superscript and indent', () => {
  assert.match(schemaSource, /name: 'superscript'/)
  assert.match(schemaSource, /name: 'fontSize'/)
  assert.match(schemaSource, /indentBlock/)
  assert.match(schemaSource, /multicolor: true/)
})

test('P4 editor can export and teacher host does not use student request', () => {
  assert.match(editorSource, /exportAs\('docx'\)/)
  assert.match(editorSource, /exportAs\('pdf'\)/)
  assert.match(editorSource, /exportAs\('md'\)/)
  assert.match(editorSource, /exportAs\('html'\)/)
  assert.match(editorSource, /useSdocHost/)
  const pageSource = readFileSync(
    new URL('../src/views/inspire-office/smart-doc/SmartDocPage.vue', import.meta.url),
    'utf8'
  )
  assert.match(pageSource, /SdocStudentHost/)
})

test('P3 schema has mind map and flowchart blocks', () => {
  assert.match(schemaSource, /name: 'mindMap'/)
  assert.match(schemaSource, /name: 'flowChart'/)
  assert.match(schemaSource, /label: '思维导图'/)
  assert.match(schemaSource, /label: '流程图'/)
})

test('P2 has clickable TOC, versions and protected region', () => {
  assert.match(schemaSource, /protectedRegion|内容保护区/)
  assert.match(editorSource, /scrollToHeading\(h.pos\)/)
  assert.match(editorSource, /toggleVersions/)
  assert.match(editorSource, /keepMine/)
  assert.match(editorSource, /inspire-sdoc-draft/)
  assert.doesNotMatch(editorSource, /小启/)
})

test('workbench pane renders SmartDocEditor for sdoc instead of Collabora', () => {
  assert.match(paneSource, /SmartDocEditor/)
  assert.match(paneSource, /isSmartDoc/)
  assert.match(workbenchSource, /ext: 'sdoc'/)
  assert.match(workbenchSource, /tabById\(paneA\)\?\.ext/)
})
