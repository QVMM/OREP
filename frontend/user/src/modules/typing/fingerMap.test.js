import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  fingerIdForCode,
  fingerReachDelta,
  keyCodeForChar,
  resolveFingerTargetCode,
} from './fingerMap.js'

describe('keyCodeForChar', () => {
  it('maps latin letters and digits', () => {
    assert.equal(keyCodeForChar('m'), 'KeyM')
    assert.equal(keyCodeForChar('M'), 'KeyM')
    assert.equal(keyCodeForChar('5'), 'Digit5')
  })

  it('maps whitespace and common punctuation', () => {
    assert.equal(keyCodeForChar(' '), 'Space')
    assert.equal(keyCodeForChar('\n'), 'Enter')
    assert.equal(keyCodeForChar('\t'), 'Tab')
    assert.equal(keyCodeForChar('{'), 'BracketLeft')
    assert.equal(keyCodeForChar(';'), 'Semicolon')
  })

  it('returns empty for CJK and unknown glyphs', () => {
    assert.equal(keyCodeForChar('中'), '')
    assert.equal(keyCodeForChar(''), '')
  })

  it('keeps QWERTY finger columns', () => {
    assert.equal(fingerIdForCode(keyCodeForChar('a')), 'L4')
    assert.equal(fingerIdForCode(keyCodeForChar('j')), 'R1')
    assert.equal(fingerIdForCode(keyCodeForChar(' ')), 'T')
  })
})

describe('resolveFingerTargetCode', () => {
  it('keeps idle fingers on home row', () => {
    assert.equal(resolveFingerTargetCode('L4', { expectedKeyCode: 'KeyP' }), 'KeyA')
    assert.equal(resolveFingerTargetCode('R4', { expectedKeyCode: 'KeyP' }), 'KeyP')
    assert.equal(resolveFingerTargetCode('T', {}), 'Space')
  })

  it('prefers a physical press over the next expected key', () => {
    assert.equal(
      resolveFingerTargetCode('R4', { pressedCodes: ['KeyP'], expectedKeyCode: 'KeyO' }),
      'KeyP'
    )
  })
})

describe('fingerReachDelta', () => {
  it('moves a finger from home toward the target key', () => {
    const d = fingerReachDelta({ x: 100, y: 200 }, { x: 130, y: 140 }, { hScale: 1, vScale: 1 })
    assert.equal(d.x, 30)
    assert.equal(d.y, -60)
  })

  it('flips X for the mirrored right hand and dips on press', () => {
    const d = fingerReachDelta(
      { x: 100, y: 200 },
      { x: 130, y: 140 },
      { hScale: 2, vScale: 2, flipX: true, press: true }
    )
    assert.equal(d.x, -15)
    assert.equal(d.y, -23)
  })
})
