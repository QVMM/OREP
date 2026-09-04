import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { fingerIdForCode, keyCodeForChar } from './fingerMap.js'

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
