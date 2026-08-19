import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(
  new URL('../src/views/AiAppCenter.vue', import.meta.url),
  'utf8'
)

test('AI app center derives visible categories from available applications', () => {
  assert.match(source, /const categoryDefinitions = \[/)
  assert.match(source, /category: 'roadshow'/)
  assert.match(source, /new Set\(apps\.map\(\(app\) => app\.category\)\)/)
  assert.match(source, /\.filter\(\(category\) => usedCategoryKeys\.has\(category\.key\)\)/)
  assert.match(source, /\{ key: ALL_CATEGORY_KEY, label: '全部'/)
  assert.match(source, /label: '路演创作'/)
})

test('AI app center exposes accessible category filtering and result counts', () => {
  assert.match(source, /aria-label="AI 应用分类"/)
  assert.match(source, /:aria-pressed="activeCategory === category\.key"/)
  assert.match(source, /aria-live="polite"/)
  assert.match(source, /filteredApps\.length/)
  assert.match(source, /该分类暂时没有可用应用/)
  assert.match(source, /查看全部应用/)
})

test('AI app center keeps real app routes and omits unapproved eyebrow copy', () => {
  assert.match(source, /to: '\/ppt-editor'/)
  assert.match(source, /to: '\/script-editor\?tab=script'/)
  assert.doesNotMatch(source, /AI 创作工具/)
})

test('AI app center owns a centered responsive catalog without duplicated narrow-screen padding', () => {
  assert.match(source, /width: min\(100%, 1480px\)/)
  assert.match(source, /margin: 0 auto/)
  assert.match(source, /padding: 0 0 var\(--ds-space-8\)/)
  assert.match(source, /@media \(max-width: 920px\)[\s\S]*grid-template-columns: 1fr/)
  assert.match(source, /@media \(max-width: 600px\)[\s\S]*\.ai-app-card__category \{\s*display: none;/)
  assert.doesNotMatch(source, /width: min\(100%, var\(--ds-page-max\)\)/)
})
