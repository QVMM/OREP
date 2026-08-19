import assert from 'node:assert/strict'
import test from 'node:test'
import { collectOfficeBlocks } from '../src/views/inspire-office/smart-doc/export/smartDocDocx.js'
import { smartDocToHtml, smartDocToMarkdown } from '../src/views/inspire-office/smart-doc/export/smartDocExport.js'
import { smartDocToReadingHtml } from '../src/views/inspire-office/smart-doc/export/smartDocReading.js'

const sample = {
  type: 'doc',
  content: [
    { type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: '备赛说明' }] },
    { type: 'paragraph', content: [{ type: 'text', text: '公开段落', marks: [{ type: 'bold' }] }] },
    {
      type: 'protectedRegion',
      attrs: { sealed: true, label: '仅教师可见' },
      content: [{ type: 'paragraph', content: [{ type: 'text', text: '答案' }] }],
    },
    {
      type: 'mindMap',
      attrs: { data: { root: { id: 'root', text: '主题', children: [{ id: 'c1', text: '分支', children: [] }] } } },
    },
  ],
}

test('markdown export maps headings and keeps protected placeholder', () => {
  const md = smartDocToMarkdown(sample, { title: '测试文档' })
  assert.match(md, /^# 测试文档/m)
  assert.match(md, /^## 备赛说明/m)
  assert.match(md, /\*\*公开段落\*\*/)
  assert.match(md, /此段仅教师可见/)
  assert.doesNotMatch(md, /答案/)
  assert.match(md, /- 主题/)
  assert.match(md, /分支/)
})

test('html export is a printable document without leaking sealed text', () => {
  const html = smartDocToHtml(sample, { title: '测试文档', mode: 'print' })
  assert.match(html, /<!doctype html>/i)
  assert.match(html, /<h1>测试文档<\/h1>/)
  assert.match(html, /<h2>备赛说明<\/h2>/)
  assert.match(html, /<strong>公开段落<\/strong>/)
  assert.match(html, /此段仅教师可见/)
  assert.match(html, /@page/)
  assert.match(html, /size: A4/)
  assert.doesNotMatch(html, /答案/)
})

test('office block outline keeps structure for Word/PDF mapping', () => {
  const blocks = collectOfficeBlocks(sample)
  assert.ok(blocks.includes('heading'))
  assert.ok(blocks.includes('paragraph'))
  assert.ok(blocks.includes('protectedRegion'))
  assert.ok(blocks.includes('mindMap'))
})

test('reading HTML is document-like: no editor chrome, keeps callout and file card', () => {
  const html = smartDocToReadingHtml({
    type: 'doc',
    content: [
      { type: 'paragraph' },
      { type: 'highlightBlock', content: [{ type: 'paragraph', content: [{ type: 'text', text: '注意这点' }] }] },
      {
        type: 'columns',
        attrs: { count: 3 },
        content: [
          { type: 'column', content: [{ type: 'paragraph' }] },
          { type: 'column', content: [{ type: 'fileCard', attrs: { name: '竞赛大脑-技术参数.pdf', size: 24166 } }] },
          { type: 'column', content: [{ type: 'paragraph' }] },
        ],
      },
      { type: 'flowChart', attrs: { data: { nodes: [{ id: 'a', text: '开始', x: 0, y: 0, kind: 'start' }], edges: [] } } },
    ],
  }, { title: '你好' })
  assert.match(html, /你好/)
  assert.match(html, /注意这点/)
  assert.match(html, /竞赛大脑-技术参数/)
  assert.doesNotMatch(html, /输入正文或/)
  assert.doesNotMatch(html, /加步骤/)
  assert.doesNotMatch(html, /加判断/)
  assert.doesNotMatch(html, /sdoc-columns/)
  assert.match(html, /sdoc-callout/)
  assert.match(html, /开始/)
  assert.match(html, /sdoc-card__name/)
  assert.match(html, /<table class="sdoc-card"/)
})

test('reading HTML skips empty highlight and keeps full file name', () => {
  const html = smartDocToReadingHtml({
    type: 'doc',
    content: [
      { type: 'highlightBlock', content: [{ type: 'paragraph' }] },
      { type: 'fileCard', attrs: { name: '竞赛大脑-技术参数.pdf', size: 24166 } },
    ],
  }, { title: '你好' })
  assert.doesNotMatch(html, /sdoc-callout/)
  assert.match(html, /竞赛大脑-技术参数\.pdf/)
  assert.match(html, /本地文件 · 23\.6 KB/)
  assert.doesNotMatch(html, /white-space:nowrap/)
})

test('Word export produces a real docx zip without leaking sealed text', async () => {
  const { smartDocToDocxBlob } = await import('../src/views/inspire-office/smart-doc/export/smartDocDocx.js')
  const blob = await smartDocToDocxBlob(sample, { title: '测试文档' })
  const buf = Buffer.from(await blob.arrayBuffer())
  assert.ok(buf.length > 800)
  assert.equal(buf.subarray(0, 2).toString(), 'PK')
  const xml = buf.toString('utf8')
  assert.match(xml, /测试文档/)
  assert.match(xml, /此段仅教师可见/)
  assert.doesNotMatch(xml, /答案/)
  assert.match(xml, /主题/)
  assert.match(xml, /分支/)
  assert.doesNotMatch(xml, /• 主题/)
  assert.doesNotMatch(xml, /思维导图/)
})

test('Word export keeps file cards readable and skips dump-style extras', async () => {
  const { smartDocToDocxBlob } = await import('../src/views/inspire-office/smart-doc/export/smartDocDocx.js')
  const blob = await smartDocToDocxBlob({
    type: 'doc',
    content: [
      { type: 'paragraph' },
      { type: 'highlightBlock', content: [{ type: 'paragraph' }] },
      {
        type: 'columns',
        attrs: { count: 3 },
        content: [
          { type: 'column', content: [{ type: 'paragraph' }] },
          {
            type: 'column',
            content: [{
              type: 'fileCard',
              attrs: {
                name: '竞赛大脑-技术参数_修订版.docx',
                size: 24166,
                url: '/uploads/chat/files/2026/08/17/34bca08fb00b4cd497743b0bdc94e72c.docx',
              },
            }],
          },
          { type: 'column', content: [{ type: 'paragraph' }] },
        ],
      },
      {
        type: 'flowChart',
        attrs: {
          data: {
            nodes: [
              { id: 'a', text: '开始', x: 0, y: 0, kind: 'start' },
              { id: 'b', text: '步骤', x: 0, y: 80, kind: 'rect' },
              { id: 'c', text: '结束', x: 0, y: 160, kind: 'end' },
            ],
            edges: [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }],
          },
        },
      },
    ],
  }, { title: '你好' })
  const xml = Buffer.from(await blob.arrayBuffer()).toString('utf8')
  assert.match(xml, /你好/)
  assert.match(xml, /竞赛大脑-技术参数_修订版\.docx/)
  assert.match(xml, /本地文件/)
  assert.doesNotMatch(xml, /\/uploads\//)
  assert.doesNotMatch(xml, /栏 1/)
  assert.doesNotMatch(xml, /栏 2/)
  assert.doesNotMatch(xml, /栏 3/)
  assert.match(xml, /开始/)
  assert.match(xml, /结束/)
  assert.doesNotMatch(xml, /• 开始/)
  assert.doesNotMatch(xml, /开始 →/)
  assert.doesNotMatch(xml, /流程图/)
})
