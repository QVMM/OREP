import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizeScoreProjection } from './aiScoreProjection.js'

test('normalizes object and serialized score projections without throwing', () => {
  assert.deepEqual(normalizeScoreProjection({ goalScore: 100 }), { goalScore: 100 })
  assert.deepEqual(
    normalizeScoreProjection('{"predictedScoreLower":56.6,"predictedScoreUpper":60}'),
    { predictedScoreLower: 56.6, predictedScoreUpper: 60 }
  )
  assert.deepEqual(normalizeScoreProjection('not-json'), {})
  assert.deepEqual(normalizeScoreProjection(null), {})
})
