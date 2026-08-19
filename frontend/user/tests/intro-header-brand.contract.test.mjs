import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const introSource = readFileSync(
  new URL('../src/views/Intro.vue', import.meta.url),
  'utf8'
)

test('intro header uses the approved Qifa Competition Brain brand name', () => {
  assert.match(
    introSource,
    /<a class="brand" href="#top" aria-label="启发·竞赛大脑首页"[\s\S]*?<span>启发·竞赛大脑<\/span>/
  )
  assert.match(
    introSource,
    /<a class="brand footer-brand"[\s\S]*?<span>竞赛大脑<\/span>/
  )
})
