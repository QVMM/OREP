import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const client = readFileSync(join(root, 'src/services/assistantClient.js'), 'utf8')
const workspace = readFileSync(join(root, 'src/views/assistant/AssistantWorkspace.vue'), 'utf8')
const homePanel = readFileSync(join(root, 'src/modules/home/HomeXiaoQiPanel.vue'), 'utf8')

test('小启 client talks to Java /api/assistant, not Python /v1 or :stream', () => {
  assert.match(client, /const base = '\/api\/assistant'/)
  assert.match(client, /\$\{base\}\/sessions/)
  assert.match(client, /\$\{base\}\/folders/)
  assert.match(client, /\$\{base\}\/memories/)
  assert.match(client, /\$\{base\}\/teams/)
  assert.match(client, /\$\{base\}\/skills/)
  assert.match(client, /\$\{base\}\/sessions\/\$\{sessionId\}\/messages\/stream/)
  assert.doesNotMatch(client, /messages:stream/)
  assert.doesNotMatch(client, /\/api\/assistant\/v1\//)
})

test('工作台与首页半栏都走 assistantClient，不另写死路径', () => {
  assert.match(workspace, /from '\.\.\/\.\.\/services\/assistantClient'/)
  assert.match(homePanel, /from '\.\.\/\.\.\/services\/assistantClient'/)
  assert.doesNotMatch(workspace, /\/api\/assistant\/v1\//)
  assert.doesNotMatch(homePanel, /\/api\/assistant\/v1\//)
})
