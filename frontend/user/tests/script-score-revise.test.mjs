import test from 'node:test'
import assert from 'node:assert/strict'
import {
  isScoreReviseIntent,
  formatScoreReviseDiagnosis,
  buildScoreItemRewritePrompt,
} from '../src/modules/assistant-core/scriptScoreRevise.js'

test('detects score revise intent and ignores local rewrite', () => {
  assert.equal(isScoreReviseIntent('按最新评分结合讲稿优化'), true)
  assert.equal(isScoreReviseIntent('对照评分改讲稿'), true)
  assert.equal(isScoreReviseIntent('这部分会不会太生硬'), false)
})

test('diagnosis lists mapped and unmapped without inventing items', () => {
  const text = formatScoreReviseDiagnosis({
    hasReport: true,
    scriptTitle: '智慧农业',
    scriptId: 12,
    contentVersion: 7,
    scoreReportId: 45,
    overallScore: 55.2,
    diagnosis: [
      { id: 'sp-1', title: '协作太书面', mapped: true, role: '项目经理', focus: 'P03' },
      { id: 'sp-2', title: '数据不足', mapped: false },
    ],
  })
  assert.match(text, /评分 #45/)
  assert.match(text, /定位到 1 步/)
  assert.match(text, /项目经理/)
  assert.match(text, /对不上步骤/)
  assert.doesNotMatch(text, /表达不生动/)
})

test('rewrite prompt cites score item id', () => {
  const prompt = buildScoreItemRewritePrompt(
    { id: 'sp-1', title: '协作太书面', role: '项目经理', focus: 'P03', stepContent: '协作机制如下' },
    { scriptTitle: '智慧农业', scriptId: 12 },
  )
  assert.match(prompt, /评分条目 ID：sp-1/)
  assert.match(prompt, /不要新增评分里没有写的扣分/)
})
