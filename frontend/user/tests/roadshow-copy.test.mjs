import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { assertSafeCopy, canMakePpt, deckSummary, holeTitle, minutesLabel, pageHealth, phaseChips, prettyDeckTitle } from '../src/views/roadshow/roadshowCopy.js'

const dir = dirname(fileURLToPath(import.meta.url))

test('helper copy has no forbidden words', () => {
  assert.deepEqual(assertSafeCopy(holeTitle({ scoreDimension: '应用价值/经济性' })), [])
})

test('cannot make ppt until holes acked', () => {
  assert.equal(canMakePpt({ holes: [{ id: 'h1', acked: false }] }), false)
  assert.equal(canMakePpt({ holes: [{ id: 'h1', acked: true }] }), true)
  assert.equal(canMakePpt({ canPrint: true, holes: [{ acked: false }] }), true)
})

test('vue screens do not leak internal words', () => {
  const files = ['RoadshowGate.vue', 'RoadshowPath.vue', 'RoadshowBind.vue', 'RoadshowPrint.vue', 'RoadshowSlide.vue', 'RoadshowIngest.vue', 'RoadshowAnalyze.vue', 'RoadshowFix.vue']
  for (const name of files) {
    const text = readFileSync(join(dir, '../src/views/roadshow', name), 'utf8')
    const hits = assertSafeCopy(text)
    assert.deepEqual(hits, [], name)
  }
})

test('deck titles stay human', () => {
  assert.equal(prettyDeckTitle('番茄 8-18-草稿.pptx'), '番茄 8-18-草稿')
  assert.equal(prettyDeckTitle('presentation_6241d0a2-5b1f-48dc-8976-3226725b5d2b'), '文档库里的一份演示')
})

test('deck summary counts partial pages', () => {
  assert.equal(
    deckSummary({ pageCount: 38, editable: 0, partial: 38, picture: 0, empty: 0 }),
    '38 页里，38 页能改一部分'
  )
  assert.deepEqual(assertSafeCopy(deckSummary({ pageCount: 38, partial: 38 })), [])
})

test('page health band is 38 to 45', () => {
  assert.equal(pageHealth(38).status, 'ok')
  assert.equal(pageHealth(45).status, 'ok')
  assert.equal(pageHealth(15).status, 'low')
  assert.equal(pageHealth(46).status, 'high')
  assert.match(pageHealth(15).label, /38–45/)
  assert.deepEqual(assertSafeCopy(pageHealth(38).label), [])
})

test('print helper copy stays everyday', () => {
  assert.equal(minutesLabel(10), '大约讲 15 分钟，不含演示')
  assert.deepEqual(assertSafeCopy(minutesLabel(10)), [])
  assert.deepEqual(phaseChips([
    { page: 1, kicker: '封面' },
    { page: 3, kicker: '问题' },
    { page: 4, kicker: '问题' },
  ]), ['封面 1', '问题 3–4'])
})
