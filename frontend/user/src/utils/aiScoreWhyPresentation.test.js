import test from 'node:test'
import assert from 'node:assert/strict'
import { buildWhyPresentation } from './aiScoreWhyPresentation.js'

test('frames never invent analysis when caption/ocr/description/modelReason missing', () => {
  const view = buildWhyPresentation({
    evidenceFrames: [
      { id: 1, timestamp: 10, image_url: 'https://example.com/a.jpg' },
      { id: 2, timestamp: 40, caption: '屏幕展示成本表' }
    ],
    dimensions: [
      { key: 'biz', name: '商业', score: 12, maxScore: 20 },
      { key: 'tech', name: '技术', score: 8, maxScore: 20 }
    ],
    deductions: []
  })

  assert.equal(view.frames.length, 2)
  assert.equal(view.frames[0].analysis, '')
  assert.equal(view.frames[1].analysis, '屏幕展示成本表')
  assert.equal(view.selectedFrame.id, '1')
  assert.equal(view.selectedFrame.analysis, '')
})

test('weak dimension is the lowest percent', () => {
  const view = buildWhyPresentation({
    evidenceFrames: [],
    dimensions: [
      { key: 'a', name: 'A', score: 18, maxScore: 20 },
      { key: 'b', name: 'B', score: 6, maxScore: 20 },
      { key: 'c', name: 'C', score: 14, maxScore: 20 }
    ]
  })

  const weak = view.dimensions.filter(d => d.weak)
  assert.equal(weak.length, 1)
  assert.equal(weak[0].key, 'b')
  assert.equal(view.dimensions.find(d => d.key === 'a').weak, false)
})

test('prefer frames near deduction times and set showMoreHint when over strip limit', () => {
  const frames = Array.from({ length: 12 }, (_, i) => ({
    id: i + 1,
    timestamp: i * 10,
    description: i === 5 ? '关键帧说明' : ''
  }))
  const view = buildWhyPresentation({
    evidenceFrames: frames,
    deductions: [{ reason: '证据不足', timestamp_seconds: 50, max_recoverable_points: 3 }],
    stripLimit: 10
  })

  assert.equal(view.frames[0].id, '6')
  assert.equal(view.frames[0].analysis, '关键帧说明')
  assert.equal(view.frames[0].todoTitle, '证据不足')
  assert.equal(view.showMoreHint, true)
  assert.equal(view.totalFrameCount, 12)
})

test('groups the complete loss ledger without losing points and links tasks by loss id', () => {
  const view = buildWhyPresentation({
    lossLedger: [
      { lossId: 'l1', lossKey: 'k1', lossType: 'performance_gap', points: 4, observationCode: 'O01', observationName: '操作规范', reason: '表现未达到满分标准' },
      { lossId: 'l2', lossKey: 'k2', lossType: 'evidence_limited', points: 5, observationCode: 'O02', reason: '证据等级封顶' },
      { lossId: 'l3', lossKey: 'k3', lossType: 'hard_violation', points: 3.5, observationCode: 'O02', reason: '触发故障惩罚' }
    ],
    remediationTasks: [
      { taskId: 'task-a', title: '加固演示', coveredLossIds: ['l2', 'l3'] }
    ]
  })

  assert.equal(view.lossGroups.performance.items.length, 1)
  assert.equal(view.lossGroups.evidence.items.length, 1)
  assert.equal(view.lossGroups.violation.items.length, 1)
  assert.equal(view.lossTotal, 12.5)
  assert.equal(view.lossGroups.evidence.items[0].taskId, 'task-a')
  assert.equal(view.lossGroups.performance.items[0].taskId, '')
})
