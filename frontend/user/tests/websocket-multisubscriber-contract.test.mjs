import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const websocketSource = readFileSync(
  new URL('../src/utils/websocket.js', import.meta.url),
  'utf8'
)
const notificationSource = readFileSync(
  new URL('../src/services/notificationClient.js', import.meta.url),
  'utf8'
)

test('one destination keeps one active subscription and multiple callbacks', () => {
  assert.match(websocketSource, /import\.meta\.env\.DEV \? '\/ws' : '\/ws-stomp'/)
  assert.match(websocketSource, /callbacks: new Map\(\)/)
  assert.match(websocketSource, /activeSubscription: null/)
  assert.match(websocketSource, /entry\.callbacks\.set\(subscriberId, callback\)/)
  assert.match(websocketSource, /entry\.callbacks\.forEach\(\(callback\) => callback\(data\)\)/)
  assert.doesNotMatch(websocketSource, /previous\?\.subscription\?\.unsubscribe/)
})

test('unsubscribe removes one callback and releases transport only after the final listener', () => {
  assert.match(websocketSource, /entry\.callbacks\.delete\(subscriberId\)/)
  assert.match(websocketSource, /if \(entry\.callbacks\.size === 0\)/)
  assert.match(websocketSource, /entry\.activeSubscription\?\.unsubscribe\(\)/)
})

test('notification client owns and releases its unique subscription token', () => {
  assert.match(notificationSource, /subscriptionToken = websocketClient\.subscribe/)
  assert.match(notificationSource, /websocketClient\.unsubscribe\(subscriptionToken\)/)
})
