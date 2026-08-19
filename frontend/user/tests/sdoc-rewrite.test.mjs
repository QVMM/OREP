import test from 'node:test'
import assert from 'node:assert/strict'
import {
  extractSuggestedRewrite,
  formatScoreBrief,
  clipScriptAround,
  buildAskPrompt,
} from '../src/views/inspire-office/smart-doc/sdocRewrite.js'

test('extracts labeled rewrite and reason', () => {
  const got = extractSuggestedRewrite('建议稿：项目经理：我们用任务看板分活。\n为什么：原句太书面，评分扣表达')
  assert.equal(got.after, '项目经理：我们用任务看板分活。')
  assert.match(got.reason, /书面/)
})

test('does not treat long Q&A as rewrite', () => {
  const essay = '这段偏硬。为什么会这样？因为协作机制写成了制度说明，评委听着像念稿。建议先说人怎么配合，再补工具。'
  const got = extractSuggestedRewrite(essay, '我们的协作机制如下')
  assert.equal(got.after, '')
})

test('formats score brief from latest report', () => {
  const text = formatScoreBrief({
    hasReport: true,
    overallScore: 55.2,
    dimensions: { expression: { name: '表达', score: 8 }, logic: { name: '逻辑', score: 14 } },
    improvementPriorities: [{ issue: '开场没报项目名' }],
  })
  assert.match(text, /55\.2/)
  assert.match(text, /表达/)
  assert.match(text, /开场没报项目名/)
})

test('clips long script around the selection', () => {
  const full = `${'前'.repeat(4000)}选中句${'后'.repeat(4000)}`
  const clipped = clipScriptAround(full, '选中句', 200)
  assert.match(clipped, /选中句/)
  assert.ok(clipped.length < 400)
})

test('prompt forbids draft and pins selected range', () => {
  const prompt = buildAskPrompt(
    { selection: '协作机制如下', speaker: '项目经理' },
    '会不会太生硬',
    { scoreText: '总分 55.2', scriptText: '全文……' },
  )
  assert.match(prompt, /不要出「改稿草案」/)
  assert.match(prompt, /只许改这一段/)
  assert.match(prompt, /总分 55\.2/)
  assert.match(prompt, /建议稿：/)
})
