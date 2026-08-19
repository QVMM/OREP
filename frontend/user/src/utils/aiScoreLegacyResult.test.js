import assert from 'node:assert/strict'
import test from 'node:test'

import { buildLegacyAiResultEndpoints } from './aiScoreLegacyResult.js'

test('session-only uploaded reports can enrich from session result json', () => {
  assert.deepEqual(
    buildLegacyAiResultEndpoints({
      result: { session_id: 20, meeting_id: null },
      sessionId: 20,
      meetingId: null
    }),
    ['/api/ai/result/20']
  )
})

test('meeting reports prefer meeting result and avoid duplicate session fallback', () => {
  assert.deepEqual(
    buildLegacyAiResultEndpoints({
      result: { session_id: 20, meeting_id: 88 },
      sessionId: 20,
      meetingId: 88
    }),
    ['/api/ai/result/88', '/api/ai/result/20']
  )

  assert.deepEqual(
    buildLegacyAiResultEndpoints({
      result: { session_id: 88, meeting_id: 88 },
      sessionId: 88,
      meetingId: 88
    }),
    ['/api/ai/result/88']
  )
})
