import test from 'node:test'
import assert from 'node:assert/strict'
import { buildVerificationSummary, verificationLabels } from './aiScoreVerification.js'

test('summarizes only persisted rerun verification facts', () => {
  const summary = buildVerificationSummary([
    { taskRecordId: 1, status: 'verified' },
    { taskRecordId: 2, status: 'partial' },
    { taskRecordId: 3, status: 'failed' },
    { taskRecordId: 4, status: 'not_observable' },
    { taskRecordId: 5, status: 'regressed' }
  ])

  assert.equal(summary.total, 5)
  assert.equal(summary.counts.verified, 1)
  assert.equal(summary.counts.regressed, 1)
  assert.equal(verificationLabels.not_observable, '本轮无法同口径验证')
})
