import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const routerSource = readFileSync(
  new URL('../src/router/index.js', import.meta.url),
  'utf8'
)
const navigationSource = readFileSync(
  new URL('../src/composables/apple/useOrepNavigation.js', import.meta.url),
  'utf8'
)
const iconSource = readFileSync(
  new URL('../src/components/workspace/WorkspaceModuleIcon.vue', import.meta.url),
  'utf8'
)

test('resource center has a canonical route and preserves the legacy file route as a redirect', () => {
  assert.match(routerSource, /path: '\/resource-center'[\s\S]*name: 'ResourceCenter'[\s\S]*ScriptList\.vue/)
  assert.match(routerSource, /path: '\/project-team\/files'[\s\S]*redirect:.*\/resource-center/s)
  assert.match(routerSource, /path: '\/script-editor'[\s\S]*tab === 'materials'[\s\S]*\/resource-center/s)
  assert.match(routerSource, /path: '\/resources'[\s\S]*PptTemplate\.vue/s)
})

test('desktop navigation replaces collaboration with resource center without losing project-team grouping', () => {
  assert.match(navigationSource, /path: '\/resource-center', label: '资源中心'.*group: 'resources'/)
  assert.doesNotMatch(navigationSource, /\{ path: '\/project-team', label: '协作'/)
  assert.match(navigationSource, /isRouteFamily\(routePath, '\/resource-center'\).*return 'resources'/s)
  assert.match(navigationSource, /isRouteFamily\(routePath, '\/project-team'\).*return 'collaboration'/s)
})

test('resource center has dedicated outline and filled navigation icons', () => {
  assert.match(iconSource, /filledIcons = \{[\s\S]*resources:/)
  assert.match(iconSource, /outlineIcons = \{[\s\S]*resources:/)
})
