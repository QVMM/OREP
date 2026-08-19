import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildHowSteps,
  buildIssueParagraph,
  buildReferences,
  enrichCoachingItem,
  getOfflineTemplateLibrary,
  priorityLabel
} from './aiScoreCoachingPresentation.js'

test('buildIssueParagraph expands short issue into a readable paragraph', () => {
  const text = buildIssueParagraph({
    title: '技术先进性论证不足',
    why: '仅罗列技术栈，缺少对照基准。',
    dimension: '技能水平',
    priority: 'P0',
    coveredGapPoints: 7.5
  })
  assert.ok(text.includes('对照基准') || text.includes('技术栈'))
  assert.ok(text.includes('技能水平'))
  assert.ok(text.length >= 36)
})

test('buildHowSteps splits numbered Chinese method into table rows', () => {
  const steps = buildHowSteps(
    '1. 编写技术对比表，明确基线方案。2. 用相同环境做性能测试并截图。3. 在讲稿增加一页先进性论证。',
    { owner: '技术', acceptanceLines: ['能展示对照表', '有测试截图', '讲稿可演示'] }
  )
  assert.ok(steps.length >= 3)
  assert.equal(steps[0].step, 1)
  assert.ok(steps[0].action.includes('对比') || steps[0].action.includes('技术'))
  assert.ok(steps[0].owner)
  assert.ok(steps[0].acceptance)
})

test('buildReferences returns full copyable templates, not title-only cards', () => {
  const refs = buildReferences({
    title: '补齐合规与隐私声明',
    how: '整理数据授权与隐私保护说明'
  })
  assert.ok(refs.length >= 1)
  for (const item of refs) {
    if (item.kind === 'template') {
      assert.ok(String(item.body || '').length >= 200, 'template must include full body')
      assert.ok(item.title.includes('可复制') || item.copyable)
    }
  }
  assert.ok(refs.every(item => !item.url || /^https?:\/\//i.test(item.url)))
})

test('buildReferences drops fake title-only template objects', () => {
  const refs = buildReferences({
    title: '随便',
    references: [
      { title: '假模板', kind: 'template', note: '只有一句话' },
      { title: '真链接', url: 'https://example.com/guide' }
    ]
  })
  assert.equal(refs.some(item => item.title === '假模板'), false)
  assert.equal(refs.some(item => item.url === 'https://example.com/guide'), true)
})

test('offline template library bodies are substantial', () => {
  const lib = getOfflineTemplateLibrary()
  for (const item of Object.values(lib)) {
    assert.ok(item.body.length >= 300)
    assert.ok(item.body.includes('验收自检') || item.body.includes('自检'))
  }
})

test('enrichCoachingItem returns issueParagraph, howSteps and full template body', () => {
  const item = enrichCoachingItem({
    title: '团队协作机制未展示',
    why: '有分工介绍但没有协作过程证据。',
    how: '1. 截取任务看板。2. 写问题复盘。3. 路演中增加协作页。',
    priority: 'P0',
    dimension: '团队协作',
    doneLines: ['可出示协作截图', '有复盘记录']
  })
  assert.ok(item.issueParagraph.length >= 24)
  assert.ok(item.howSteps.length >= 3)
  assert.equal(item.priorityLabel, '先改')
  assert.ok(item.references.length >= 1)
  assert.ok(item.references[0].body.length >= 200)
  assert.ok(item.howPreview)
  // 步骤正文不再自带序号，避免「2. 2) …」
  for (const step of item.howSteps) {
    assert.ok(!/^\d+[\.\)、]/.test(step.action), `action should not start with number: ${step.action}`)
  }
})

test('enrichCoachingItem strips duplicated step prefixes from howSteps', () => {
  const item = enrichCoachingItem({
    title: '补工程深度证据',
    why: '技能熟练度失分',
    how: '',
    howSteps: [
      '1. 录制一个5分钟演示视频',
      '2) 蓝牙数据解析的核心代码',
      { step: 3, action: '3) 3) 展示一个关键配置文件' },
      { step: 4, action: '4) 模拟传感器断连异常' }
    ],
    priority: 'P0'
  })
  assert.equal(item.howSteps.length, 4)
  assert.equal(item.howSteps[0].action, '录制一个5分钟演示视频')
  assert.equal(item.howSteps[1].action, '蓝牙数据解析的核心代码')
  assert.equal(item.howSteps[2].action, '展示一个关键配置文件')
  assert.equal(item.howSteps[3].action, '模拟传感器断连异常')
  assert.deepEqual(item.howSteps.map(s => s.step), [1, 2, 3, 4])
})

test('priorityLabel maps P0/P1/P2 to student language', () => {
  assert.equal(priorityLabel('P0'), '先改')
  assert.equal(priorityLabel('P1'), '建议改')
  assert.equal(priorityLabel('P2'), '可后改')
})
