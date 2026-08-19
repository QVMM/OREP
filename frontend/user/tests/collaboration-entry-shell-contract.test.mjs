import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const shellSource = readFileSync(
  new URL('../src/components/workspace/WorkspaceShell.vue', import.meta.url),
  'utf8'
)
const sidebarSource = readFileSync(
  new URL('../src/components/workspace/WorkspaceSidebar.vue', import.meta.url),
  'utf8'
)
const mobileSource = readFileSync(
  new URL('../src/components/workspace/WorkspaceMobileNav.vue', import.meta.url),
  'utf8'
)
const storeSource = readFileSync(
  new URL('../src/stores/collaboration.js', import.meta.url),
  'utf8'
)
const entrySource = readFileSync(
  new URL('../src/components/collaboration/CollaborationEntryButton.vue', import.meta.url),
  'utf8'
)

test('workspace shell owns one persistent collaboration hub and no collaboration module rail', () => {
  assert.match(shellSource, /<CollaborationHub \/>/)
  assert.doesNotMatch(shellSource, /<WorkspaceModuleNav/)
  assert.doesNotMatch(shellSource, /hasModuleNav/)
})

test('desktop sidebar exposes collaboration as a separate bottom action', () => {
  assert.match(sidebarSource, /<CollaborationEntryButton/)
  assert.match(sidebarSource, /class="workspace-collaboration-entry"/)
  assert.match(sidebarSource, /@click="openCollaboration"/)
})

test('desktop collaboration mark stays prominent without a card shell', () => {
  assert.match(entrySource, /\.is-desktop \.collaboration-entry-button__mark/)
  assert.match(entrySource, /width: 38px/)
  assert.match(entrySource, /height: 38px/)
  assert.match(entrySource, /border: 0/)
  assert.match(entrySource, /background: transparent/)
  assert.match(entrySource, /box-shadow: none/)
})

test('mobile dock inserts collaboration without creating a seventh compressed item', () => {
  assert.match(mobileSource, /kind: 'collaboration'/)
  assert.match(mobileSource, /grid-template-columns: repeat\(6, minmax\(0, 1fr\)\)/)
  assert.doesNotMatch(mobileSource, /repeat\(7,/)
  assert.doesNotMatch(mobileSource, /grid-template-columns: repeat\(4,/)
})

test('collaboration store persists open state independently from routes', () => {
  assert.match(storeSource, /defineStore\('collaboration'/)
  assert.match(storeSource, /const isOpen = ref\(false\)/)
  assert.match(storeSource, /VITE_COLLABORATION_ENABLED \?\? 'true'/)
  assert.doesNotMatch(storeSource, /import\.meta\.env\.DEV \? 'true' : 'false'/)
  assert.match(storeSource, /function open\(\)/)
  assert.match(storeSource, /function close\(\)/)
  assert.match(storeSource, /function toggle\(\)/)
})
