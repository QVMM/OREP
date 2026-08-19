import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('../src/utils/websocket.js', import.meta.url), 'utf8')

test('teacher realtime client uses authenticated shared notification channel semantics', () => {
  assert.match(source, /import\.meta\.env\.DEV \? '\/ws' : '\/ws-stomp'/)
  assert.match(source, /new SockJS\(websocketEndpoint\)/)
  assert.match(source, /Authorization: `Bearer \$\{getToken\(\)\}`/)
  assert.match(source, /callbacks: new Map\(\)/)
  assert.match(source, /activeSubscription: null/)
  assert.match(source, /entry\.callbacks\.forEach/)
})
