import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeCoverage } from './aiScoreCoverage.js'

test('normalizes complete v3 coverage without inventing counts', () => {
  const coverage = normalizeCoverage('{"lossItemCount":19,"remediationTaskCount":23,"coveredGapPoints":50.5,"coverageRate":1,"status":"complete"}')
  assert.equal(coverage.lossItemCount, 19)
  assert.equal(coverage.remediationTaskCount, 23)
  assert.equal(coverage.canClaimCompleteTodos, true)
})

test('never calls an incomplete portfolio complete', () => {
  const coverage = normalizeCoverage({ coverageRate: 0.95, status: 'complete', uncoveredLossIds: ['l1'] })
  assert.equal(coverage.canClaimCompleteTodos, false)
})

test('malformed coverage is explicitly incomplete', () => {
  const coverage = normalizeCoverage('{broken')
  assert.equal(coverage.status, 'incomplete')
  assert.equal(coverage.canClaimCompleteTodos, false)
})
