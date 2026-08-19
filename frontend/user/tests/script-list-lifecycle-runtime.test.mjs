import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createRequestLifecycle,
  createSerialPoller,
} from '../src/utils/requestLifecycle.js'

function deferred() {
  let resolve
  const promise = new Promise(resolvePromise => {
    resolve = resolvePromise
  })
  return { promise, resolve }
}

test('late preparation responses are aborted and cannot commit after invalidation', async () => {
  const lifecycle = createRequestLifecycle()
  lifecycle.activate()
  const request = lifecycle.open('bootstrap')
  const response = deferred()
  let committed = 0

  const consumer = response.promise.then(() => {
    if (request.isCurrent()) committed += 1
    request.release()
  })

  lifecycle.invalidate()
  response.resolve()
  await consumer

  assert.equal(request.signal.aborted, true)
  assert.equal(committed, 0)
  assert.equal(lifecycle.isActive(), false)
})

test('a stopped serial poller does not overlap or restart after an in-flight task resolves', async () => {
  const timers = new Map()
  let nextTimerId = 1
  let taskCalls = 0
  const taskResult = deferred()
  const poller = createSerialPoller(
    async () => {
      taskCalls += 1
      await taskResult.promise
    },
    {
      delay: 2500,
      setTimer(callback) {
        const id = nextTimerId
        nextTimerId += 1
        timers.set(id, callback)
        return id
      },
      clearTimer(id) {
        timers.delete(id)
      },
    },
  )

  poller.start()
  assert.equal(timers.size, 1)

  const [timerId, callback] = timers.entries().next().value
  timers.delete(timerId)
  const tick = callback()
  assert.equal(taskCalls, 1)

  poller.start()
  assert.equal(timers.size, 0, 'an in-flight poll must not schedule an overlapping request')

  poller.stop()
  taskResult.resolve()
  await tick

  assert.equal(taskCalls, 1)
  assert.equal(timers.size, 0, 'a stopped in-flight poll must not restart itself')
  assert.equal(poller.isRunning(), false)
})
