import assert from 'node:assert/strict'
import test from 'node:test'
import {
  createCloudDocJSON,
  createColumnsJSON,
  createDateChipJSON,
  createEmptyTableJSON,
  createFileCardJSON,
  createMediaBlockJSON,
  createProtectedRegionJSON,
  groupSlashItems,
  SLASH_CATALOG,
} from '../src/views/inspire-office/smart-doc/schema/smartDocBlocks.js'

test('empty table JSON is 3x3 with a header row', () => {
  const table = createEmptyTableJSON(3, 3, true)
  assert.equal(table.type, 'table')
  assert.equal(table.content.length, 3)
  assert.equal(table.content[0].type, 'tableRow')
  assert.equal(table.content[0].content[0].type, 'tableHeader')
  assert.equal(table.content[1].content[0].type, 'tableCell')
  assert.equal(table.content[0].content.length, 3)
})

test('columns JSON is a block container of 2 or 3 columns', () => {
  const two = createColumnsJSON(2)
  const three = createColumnsJSON(3)
  assert.equal(two.type, 'columns')
  assert.equal(two.attrs.count, 2)
  assert.equal(two.content.length, 2)
  assert.equal(two.content[0].type, 'column')
  assert.equal(three.content.length, 3)
})

test('file, cloud, date and media JSON only store URLs and meta', () => {
  const file = createFileCardJSON({ url: '/uploads/general/files/a.pdf', name: '评分表.pdf', size: 2048, mime: 'application/pdf' })
  const cloud = createCloudDocJSON({ id: 9, title: '路演提纲', ext: 'sdoc', documentType: 'sdoc', href: '/inspire-office/sdoc/9' })
  const date = createDateChipJSON('2026-08-17')
  const media = createMediaBlockJSON({ src: '/uploads/general/files/a.mp4', kind: 'video', name: '示范.mp4' })
  assert.equal(file.type, 'fileCard')
  assert.equal(file.attrs.url.startsWith('data:'), false)
  assert.equal(cloud.attrs.documentId, '9')
  assert.equal(date.attrs.value, '2026-08-17')
  assert.equal(media.attrs.kind, 'video')
  assert.match(media.attrs.src, /^\/uploads\//)
})

test('slash catalog groups include structure and media items', () => {
  const groups = groupSlashItems(SLASH_CATALOG)
  const names = groups.map((g) => g.name)
  assert.deepEqual(names, ['基础', '结构', '图示', '媒体'])
  const keys = SLASH_CATALOG.map((i) => i.key)
  for (const key of ['table', 'cols2', 'file', 'cloud', 'media', 'date', 'emoji', 'image', 'protect', 'mindmap', 'flow']) {
    assert.ok(keys.includes(key), `missing slash item ${key}`)
  }
  const protect = createProtectedRegionJSON({ id: 'p1' })
  assert.equal(protect.type, 'protectedRegion')
  assert.equal(protect.attrs.minRole, 'TEACHER')
  assert.equal(protect.attrs.sealed, false)
})
