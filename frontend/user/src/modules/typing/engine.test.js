import test from 'node:test'
import assert from 'node:assert/strict'
import { createTypingEngine } from './engine.js'

test('counts correct chars and stays running before timed limit', () => {
  const engine = createTypingEngine('你好世界', { mode: 'timed', durationSec: 60 })
  const t0 = 1_000_000
  engine.start(t0)
  engine.setCommitted('你好', t0 + 1000)
  const snap = engine.snapshot(t0 + 1000)
  assert.equal(snap.correctChars, 2)
  assert.equal(snap.status, 'running')
  assert.ok(snap.cpm > 0)
})

test('finishes count mode when correct chars reach target', () => {
  const engine = createTypingEngine('abcdefghij', { mode: 'count', targetCount: 4 })
  engine.setCommitted('abcd', 2_000_000)
  const snap = engine.snapshot(2_000_000)
  assert.equal(snap.status, 'finished')
  assert.equal(snap.correctChars, 4)
})

test('tracks wrong chars in errorMap', () => {
  const engine = createTypingEngine('abc', { mode: 'count', targetCount: 10 })
  engine.setCommitted('ax', Date.now())
  const result = engine.buildResult({ lang: 'en' })
  assert.equal(result.errorMap.b, 1)
  assert.ok(result.accuracy < 100)
})

test('does not count paused time toward elapsedMs', () => {
  const engine = createTypingEngine('你好世界', { mode: 'timed', durationSec: 300 })
  const t0 = 5_000_000
  engine.start(t0)
  engine.setCommitted('你', t0 + 10_000)
  engine.pause(t0 + 10_000)
  const paused = engine.snapshot(t0 + 70_000)
  assert.equal(paused.status, 'paused')
  assert.equal(paused.elapsedMs, 10_000)
  engine.resume(t0 + 70_000)
  const resumed = engine.snapshot(t0 + 80_000)
  assert.equal(resumed.status, 'running')
  assert.equal(resumed.elapsedMs, 20_000)
})

test('ignores typing while paused so elapsed stays frozen', () => {
  const engine = createTypingEngine('你好世界', { mode: 'timed', durationSec: 300 })
  const t0 = 8_000_000
  engine.start(t0)
  engine.setCommitted('你', t0 + 1000)
  engine.pause(t0 + 1000)
  const after = engine.setCommitted('你好', t0 + 4000)
  assert.equal(after.status, 'paused')
  assert.equal(after.committed, '你')
  assert.equal(after.elapsedMs, 1000)
})

test('snapshot while paused does not grow elapsed as wall clock moves', () => {
  const engine = createTypingEngine('abcde', { mode: 'timed', durationSec: 300 })
  const t0 = 9_000_000
  engine.start(t0)
  engine.pause(t0 + 5000)
  assert.equal(engine.snapshot(t0 + 5000).elapsedMs, 5000)
  assert.equal(engine.snapshot(t0 + 65_000).elapsedMs, 5000)
})
