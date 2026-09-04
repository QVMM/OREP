import test from 'node:test'
import assert from 'node:assert/strict'
import {
  createTypingEngine,
  expandWithLeadingIndent,
  isLeadingIndentChar,
} from './engine.js'

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

const SAMPLE_CODE = 'export function x() {\n  const a = 1\n  return a\n}\n'

test('isLeadingIndentChar only marks spaces/tabs at line start', () => {
  const target = [...SAMPLE_CODE]
  const firstIndent = SAMPLE_CODE.indexOf('  const')
  assert.equal(isLeadingIndentChar(target, firstIndent), true)
  assert.equal(isLeadingIndentChar(target, firstIndent + 1), true)
  assert.equal(isLeadingIndentChar(target, firstIndent + 2), false) // 'c'
  const inlineSpace = SAMPLE_CODE.indexOf(' = 1')
  assert.equal(isLeadingIndentChar(target, inlineSpace), false)
  assert.equal(isLeadingIndentChar(target, 0), false)
})

test('expandWithLeadingIndent auto-inserts line-start indent and keeps inline spaces', () => {
  assert.equal(expandWithLeadingIndent('', SAMPLE_CODE), '')
  assert.equal(
    expandWithLeadingIndent('export function x() {\nconst a = 1', SAMPLE_CODE),
    'export function x() {\n  const a = 1'
  )
  assert.equal(
    expandWithLeadingIndent('export function x() {\n  const a = 1', SAMPLE_CODE),
    'export function x() {\n  const a = 1'
  )
  // 行首多敲的空格是 no-op
  assert.equal(
    expandWithLeadingIndent('export function x() {\n    const a = 1', SAMPLE_CODE),
    'export function x() {\n  const a = 1'
  )
})

test('expandWithLeadingIndent does not invent inline spaces', () => {
  const expanded = expandWithLeadingIndent('export function x() {\nconsta = 1', SAMPLE_CODE)
  assert.equal(expanded, 'export function x() {\n  consta = 1')
  assert.match(expanded, /consta/)
})

test('skipLeadingIndent seeds first-line indent and parks caret on first token', () => {
  const engine = createTypingEngine('  const x = 1\n', { skipLeadingIndent: true, mode: 'timed', durationSec: 60 })
  const snap = engine.snapshot()
  assert.equal(snap.status, 'idle')
  assert.equal(snap.committed, '  ')
  assert.equal(snap.caret, 2)
  assert.equal(snap.targetCharsList[snap.caret], 'c')
  assert.deepEqual(snap.charStates, ['correct', 'correct'])
})

test('skipLeadingIndent accepts the first token without typing indent', () => {
  const engine = createTypingEngine(SAMPLE_CODE, { skipLeadingIndent: true, mode: 'timed', durationSec: 60 })
  const t0 = 3_000_000
  const typed = 'export function x() {\nconst a = 1'
  const snap = engine.setCommitted(typed, t0)
  assert.equal(snap.committed, 'export function x() {\n  const a = 1')
  assert.equal(snap.caret, snap.committed.length)
  assert.equal(snap.incorrectChars, 0)
  assert.equal(snap.status, 'running')
})

test('skipLeadingIndent still requires inline spaces between tokens', () => {
  const engine = createTypingEngine(SAMPLE_CODE, { skipLeadingIndent: true, mode: 'count', targetCount: 80 })
  engine.setCommitted('export function x() {\nconsta = 1', 4_000_000)
  const snap = engine.snapshot(4_000_000)
  assert.ok(snap.incorrectChars >= 1)
  assert.ok(snap.errorMap[' '] >= 1 || snap.committed.includes('consta'))
})

test('skipLeadingIndent counts only user keystrokes, not auto indent', () => {
  const engine = createTypingEngine('  ab', { skipLeadingIndent: true, mode: 'count', targetCount: 10 })
  engine.setCommitted('a', 5_000_000)
  const snap = engine.snapshot(5_000_000)
  assert.equal(snap.committed, '  a')
  assert.equal(snap.totalKeystrokes, 1)
  assert.equal(snap.correctKeystrokes, 1)
  assert.equal(snap.correctChars, 3)
})

test('skipLeadingIndent Tab/spaces at line start are optional no-ops', () => {
  const engine = createTypingEngine('foo\n\tbar', { skipLeadingIndent: true, mode: 'count', targetCount: 20 })
  const snap = engine.setCommitted('foo\n\t\tbar', 6_000_000)
  assert.equal(snap.committed, 'foo\n\tbar')
  assert.equal(snap.incorrectChars, 0)
})

test('skipLeadingIndent backspace off a new line drops the newline, not the indent slot', () => {
  const engine = createTypingEngine('foo\n  bar\n  baz', { skipLeadingIndent: true, mode: 'count', targetCount: 80 })
  engine.setCommitted('foo\nbar', 7_000_000)
  assert.equal(engine.snapshot().committed, 'foo\n  bar')
  assert.equal(engine.snapshot().status, 'running')
  const after = engine.setCommitted('foo', 7_000_100)
  assert.equal(after.committed, 'foo')
  assert.equal(after.caret, 3)
})

test('skipLeadingIndent finishes when tokens and newlines are complete', () => {
  const text = 'a\n  b\n'
  const engine = createTypingEngine(text, { skipLeadingIndent: true, mode: 'count', targetCount: 80 })
  const snap = engine.setCommitted('a\nb\n', 8_000_000)
  assert.equal(snap.committed, text)
  assert.equal(snap.status, 'finished')
  assert.equal(snap.incorrectChars, 0)
})

test('without skipLeadingIndent leading spaces still must be typed', () => {
  const engine = createTypingEngine('  ab', { mode: 'count', targetCount: 10 })
  const snap = engine.setCommitted('ab', Date.now())
  assert.equal(snap.committed, 'ab')
  assert.ok(snap.incorrectChars >= 1)
  assert.notEqual(snap.caret, 4)
})
