import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  new URL('../src/views/team/TeamCreateView.vue', import.meta.url),
  'utf8'
)

test('team create form grid prevents controls from overflowing into adjacent columns', () => {
  assert.match(
    source,
    /\.form-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s
  )
  assert.match(source, /\.wizard-field\s*\{[^}]*min-width:\s*0/s)
  assert.match(
    source,
    /\.wizard-field input[^}]*box-sizing:\s*border-box/s
  )
})

test('team create form still collapses to one column on narrow screens', () => {
  assert.match(
    source,
    /@media\s*\(max-width:\s*760px\)[^{]*\{[^}]*\.form-grid\s*\{[^}]*grid-template-columns:\s*1fr/s
  )
})
