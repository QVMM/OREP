import test from 'node:test'
import assert from 'node:assert/strict'
import { trainingDayLockLabel, trainingDayLockMessage } from './format.js'

test('lock label uses open date for scheduled days', () => {
  const label = trainingDayLockLabel({
    locked: true,
    lockReason: 'SCHEDULED',
    trainingDate: '2026-09-01'
  })
  assert.match(label, /开放/)
})

test('unpublished days do not expose a submit date', () => {
  const label = trainingDayLockLabel({ locked: true, lockReason: 'NOT_PUBLISHED' })
  assert.equal(label, '训练日尚未发布')
  assert.match(trainingDayLockMessage({ locked: true, lockReason: 'NOT_PUBLISHED' }), /发布后再来/)
})

test('unlocked days have empty lock copy', () => {
  assert.equal(trainingDayLockLabel({ locked: false }), '')
  assert.equal(trainingDayLockMessage({}), '')
})
