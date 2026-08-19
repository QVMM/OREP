import assert from 'node:assert/strict'
import test from 'node:test'

const ALLOWED = new Set(['content', 'notes', 'transition'])

function applyPatches(content, patches) {
  const chapters = JSON.parse(content)
  for (const patch of patches) {
    if (!ALLOWED.has(patch.field)) throw new Error('不允许修改字段: ' + patch.field)
    let found = null
    for (const ch of chapters) {
      found = (ch.steps || []).find((s) => s.id === patch.stepId)
      if (found) break
    }
    if (!found) throw new Error('找不到步骤')
    if (String(found[patch.field] || '') !== String(patch.before || '')) {
      throw new Error('原文已变化，请刷新后再确认')
    }
    found[patch.field] = patch.after
  }
  return JSON.stringify(chapters)
}

const DOC = JSON.stringify([{
  id: 'c1',
  title: '开场',
  steps: [
    { id: 's1', role: '主讲人A', duration: 0.5, focus: '封面（P01）', content: '各位评委好', notes: '自信', transition: '接下来看背景' },
    { id: 's2', role: '角色B', duration: 1, focus: '架构（P09）', content: '这是架构', notes: '', transition: '' },
  ],
}])

test('script patch keeps role and rewrites content', () => {
  const out = JSON.parse(applyPatches(DOC, [{
    stepId: 's1', field: 'content', before: '各位评委好', after: '各位评委老师好', reason: '开场',
  }]))
  assert.equal(out[0].steps[0].content, '各位评委老师好')
  assert.equal(out[0].steps[0].role, '主讲人A')
  assert.equal(out[0].steps[1].role, '角色B')
})

test('extracts after/reason and keeps full-step before', async () => {
  const { extractScriptPatchFromReply } = await import('../src/modules/assistant-core/scriptStepContext.js')
  const ctx = {
    stepContent: '各位评委好，今天我们汇报智慧农业。',
    selection: '各位评委好',
  }
  const out = extractScriptPatchFromReply('建议稿：各位评委老师好，今天我们汇报智慧农业。\n原因：开场没报身份', ctx)
  assert.equal(out.after, '各位评委老师好，今天我们汇报智慧农业。')
  assert.equal(out.reason, '开场没报身份')
  const spliced = extractScriptPatchFromReply('建议稿：各位评委老师好\n原因：补身份', ctx)
  assert.equal(spliced.after, '各位评委老师好，今天我们汇报智慧农业。')
})

test('script patch rejects role field and stale before', () => {
  assert.throws(() => applyPatches(DOC, [{
    stepId: 's1', field: 'role', before: '主讲人A', after: '角色B',
  }]))
  assert.throws(() => applyPatches(DOC, [{
    stepId: 's1', field: 'content', before: '过期', after: '新稿',
  }]))
})
