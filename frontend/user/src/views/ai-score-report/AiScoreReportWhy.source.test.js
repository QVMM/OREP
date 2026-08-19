import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./AiScoreReportWhy.vue', import.meta.url), 'utf8')

test('user report consumes only stable final speaker contract fields', () => {
  assert.match(source, /speakerAttributionStatus/)
  assert.match(source, /stablePeople/)
  assert.match(source, /finalSpeakerSegments/)
  assert.match(source, /minutes\.isStableFinal/)
  assert.match(source, /minutes\.stablePeople/)
})

test('user report never exposes acoustic cluster labels or user-side correction controls', () => {
  assert.doesNotMatch(source, /segment\.rawSpeaker/)
  assert.doesNotMatch(source, /原始声音簇/)
  assert.doesNotMatch(source, /speaker-edit/)
  assert.doesNotMatch(source, /openSpeakerEditor/)
})

test('transcript panel omits the redundant stable-person roster while keeping confirmation status', () => {
  assert.match(source, /已确认 \{\{ minutes\.stablePeople\.length \}\} 位稳定人物/)
  assert.match(source, /recompute-speaker-attribution/)
  assert.match(source, /重算人物归属/)
  assert.match(source, /recomputeSpeakerAttribution/)
  assert.doesNotMatch(source, /class="person-roster"/)
  assert.doesNotMatch(source, /class="person-chip"/)
})
