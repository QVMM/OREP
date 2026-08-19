import test from 'node:test'
import assert from 'node:assert/strict'
import {
  shouldPersistTypingSession,
  resolveVisibilityAction,
  resolveSaveMode,
  buildTypingSessionPayload,
  typingActualSeconds,
} from './sessionPersist.js'

test('practice with 2s elapsed persists even if no correct chars', () => {
  assert.equal(shouldPersistTypingSession({ mode: 'practice', elapsedMs: 2000, correctChars: 0 }), true)
})

test('sub-2s practice without correct chars is not persisted', () => {
  assert.equal(shouldPersistTypingSession({ mode: 'practice', elapsedMs: 1999, correctChars: 0 }), false)
})

test('any correct char persists so a short burst still counts', () => {
  assert.equal(shouldPersistTypingSession({ mode: 'practice', elapsedMs: 400, correctChars: 1 }), true)
})

test('ranked under 2 minutes is saved as practice so time still counts', () => {
  assert.equal(resolveSaveMode({
    requestedMode: 'ranked',
    elapsedMs: 90_000,
    correctChars: 80,
    textVersion: 'v1',
  }), 'practice')
})

test('ranked meeting 2 minutes and 20 correct chars stays ranked', () => {
  assert.equal(resolveSaveMode({
    requestedMode: 'ranked',
    elapsedMs: 120_000,
    correctChars: 20,
    textVersion: 'v1',
  }), 'ranked')
})

test('ranked without text version cannot enter the board', () => {
  assert.equal(resolveSaveMode({
    requestedMode: 'ranked',
    elapsedMs: 180_000,
    correctChars: 40,
    textVersion: '  ',
  }), 'practice')
})

test('payload uses resolved mode and keeps clientSessionId', () => {
  const payload = buildTypingSessionPayload({
    clientSessionId: 'tp_1_abc',
    mode: 'ranked',
    durationSec: 600,
    elapsedMs: 15_000,
    correctChars: 9,
    cpm: 36,
    accuracy: 90,
    totalKeystrokes: 10,
    lang: 'zh',
    difficulty: 2,
    textVersion: 'v1',
    sourceType: 'ranked',
  })
  assert.equal(payload.mode, 'practice')
  assert.equal(payload.clientSessionId, 'tp_1_abc')
  assert.equal(payload.elapsedMs, 15_000)
})

test('tab hide pauses a running session', () => {
  assert.equal(resolveVisibilityAction({
    hidden: true,
    status: 'running',
    pauseReason: '',
  }), 'pause-visibility')
})

test('tab show resumes only visibility pauses, not Esc pauses', () => {
  assert.equal(resolveVisibilityAction({
    hidden: false,
    status: 'paused',
    pauseReason: 'visibility',
  }), 'resume')
  assert.equal(resolveVisibilityAction({
    hidden: false,
    status: 'paused',
    pauseReason: 'user',
  }), 'none')
})

test('analytics seconds come from elapsed_ms only, never target duration', () => {
  assert.equal(typingActualSeconds(15_400), 15)
  assert.equal(typingActualSeconds(0), 0)
  assert.equal(typingActualSeconds(null), 0)
})
