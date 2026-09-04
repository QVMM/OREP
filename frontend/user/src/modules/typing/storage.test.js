import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeSpaceGlyph, SPACE_GLYPH_OPTIONS } from './storage.js'

test('normalizeSpaceGlyph defaults unknown values to bullet', () => {
  assert.equal(normalizeSpaceGlyph('bullet'), 'bullet')
  assert.equal(normalizeSpaceGlyph('bar'), 'bar')
  assert.equal(normalizeSpaceGlyph('invisible'), 'invisible')
  assert.equal(normalizeSpaceGlyph(''), 'bullet')
  assert.equal(normalizeSpaceGlyph('dot'), 'bullet')
  assert.equal(normalizeSpaceGlyph(undefined), 'bullet')
})

test('SPACE_GLYPH_OPTIONS cover the three Keybr-style modes', () => {
  assert.deepEqual(
    SPACE_GLYPH_OPTIONS.map((o) => o.value),
    ['bullet', 'bar', 'invisible']
  )
  assert.ok(SPACE_GLYPH_OPTIONS.every((o) => o.label.startsWith('空格')))
})
