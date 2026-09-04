import test from 'node:test'
import assert from 'node:assert/strict'
import {
  normalizeSpaceGlyph,
  resolveSpaceGlyph,
  SPACE_GLYPH_OPTIONS,
  spaceGlyphOptionsForMode,
} from './storage.js'

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

test('resolveSpaceGlyph forces invisible in code mode (never bullet or bar)', () => {
  assert.equal(resolveSpaceGlyph('bar', { code: true }), 'invisible')
  assert.equal(resolveSpaceGlyph('bullet', { code: true }), 'invisible')
  assert.equal(resolveSpaceGlyph('invisible', { code: true }), 'invisible')
  assert.equal(resolveSpaceGlyph('bar', { code: false }), 'bar')
  assert.equal(resolveSpaceGlyph('bullet', { code: false }), 'bullet')
})

test('spaceGlyphOptionsForMode hides the toggle on code practice', () => {
  assert.deepEqual(spaceGlyphOptionsForMode({ code: true }), [])
  assert.deepEqual(
    spaceGlyphOptionsForMode({ code: false }).map((o) => o.value),
    ['bullet', 'bar', 'invisible']
  )
})
