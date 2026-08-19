import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeLossLedger } from './aiScoreLossLedger.js'

test('keeps only valid loss facts in server order', () => {
  const ledger = normalizeLossLedger(JSON.stringify([
    { lossId: 'l1', lossKey: 'k1', lossType: 'evidence_limited', points: 5, observationCode: 'O01' },
    { lossId: 'broken', lossKey: '', lossType: 'performance_gap', points: 2 },
    { lossId: 'l2', lossKey: 'k2', lossType: 'performance_gap', points: 3.5, scoreBudgetKey: 'O02:performance' }
  ]))

  assert.equal(ledger.length, 2)
  assert.deepEqual(ledger.map(item => item.lossId), ['l1', 'l2'])
  assert.equal(ledger[1].points, 3.5)
})

test('malformed ledger returns an empty list', () => {
  assert.deepEqual(normalizeLossLedger('{broken'), [])
})

test('hides internal evidence grades, caps and rule percentages from user-facing reasons', () => {
  const ledger = normalizeLossLedger([{
    lossId: 'l1',
    lossKey: 'k1',
    lossType: 'evidence_limited',
    points: 0.3,
    reason: '当前绑定3条会话证据，证据等级E3，规则确认上限为2.1%；展示了成本对比，但缺少来源说明。',
    observationCode: 'O10'
  }])

  assert.equal(ledger[0].reason, '已找到相关现场材料，但其完整性和可复核性仍不足。展示了成本对比，但缺少来源说明。')
  assert.equal(/E3|2\.1%|规则确认上限|当前绑定/.test(ledger[0].reason), false)
})
