import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

let createPptTaskCoordinator

test.before(async () => {
  const source = await readFile(
    new URL('../src/views/PptGenerator.vue', import.meta.url),
    'utf8'
  )
  const normalScript = source.match(/<script>\s*([\s\S]*?)\s*<\/script>/)
  if (!normalScript) return
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(normalScript[1]).toString('base64')}`
  const module = await import(moduleUrl)
  createPptTaskCoordinator = module.createPptTaskCoordinator
})

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function createTimerHarness() {
  const timers = new Map()
  let id = 0
  return {
    schedule(callback) {
      id += 1
      timers.set(id, callback)
      return id
    },
    cancel(timerId) {
      timers.delete(timerId)
    },
    takeNext() {
      const entry = timers.entries().next().value
      assert.ok(entry, 'expected a scheduled poll')
      timers.delete(entry[0])
      return entry[1]
    },
    count() {
      return timers.size
    },
  }
}

test('leaving during a delayed submit invalidates the workflow before polling starts', async () => {
  const timer = createTimerHarness()
  const coordinator = createPptTaskCoordinator({
    schedule: timer.schedule,
    cancel: timer.cancel,
  })
  coordinator.mount()
  const workflow = coordinator.beginWorkflow()
  const taskCreation = deferred()
  let statusRequests = 0

  const submit = async () => {
    const jobId = await taskCreation.promise
    if (!coordinator.isCurrent(workflow)) return
    coordinator.startPolling({
      workflow,
      jobId,
      fetchStatus: async () => {
        statusRequests += 1
        return { status: 'completed' }
      },
      applyStatus: () => {},
      shouldStop: task => task.status === 'completed',
    })
  }

  const pendingSubmit = submit()
  coordinator.unmount()
  taskCreation.resolve(42)
  await pendingSubmit

  assert.equal(timer.count(), 0)
  assert.equal(statusRequests, 0)
})

test('serial polling schedules the next status request only after the slow request settles', async () => {
  const timer = createTimerHarness()
  const coordinator = createPptTaskCoordinator({
    schedule: timer.schedule,
    cancel: timer.cancel,
  })
  coordinator.mount()
  const workflow = coordinator.beginWorkflow()
  const statusResponse = deferred()
  let concurrent = 0
  let maximumConcurrent = 0
  let requestCount = 0

  coordinator.startPolling({
    workflow,
    jobId: 7,
    fetchStatus: async () => {
      requestCount += 1
      concurrent += 1
      maximumConcurrent = Math.max(maximumConcurrent, concurrent)
      const status = await statusResponse.promise
      concurrent -= 1
      return status
    },
    applyStatus: () => {},
    shouldStop: () => false,
  })

  const firstPoll = timer.takeNext()()
  assert.equal(timer.count(), 0)
  assert.equal(requestCount, 1)
  statusResponse.resolve({ status: 'generating' })
  await firstPoll

  assert.equal(maximumConcurrent, 1)
  assert.equal(timer.count(), 1)
})

test('reset invalidates an in-flight status response before it can mutate fresh state', async () => {
  const timer = createTimerHarness()
  const coordinator = createPptTaskCoordinator({
    schedule: timer.schedule,
    cancel: timer.cancel,
  })
  coordinator.mount()
  const workflow = coordinator.beginWorkflow()
  const statusResponse = deferred()
  let appliedStatusCount = 0

  coordinator.startPolling({
    workflow,
    jobId: 9,
    fetchStatus: () => statusResponse.promise,
    applyStatus: () => {
      appliedStatusCount += 1
    },
    shouldStop: () => false,
  })

  const inFlightPoll = timer.takeNext()()
  coordinator.invalidateWorkflow()
  statusResponse.resolve({ status: 'completed' })
  await inFlightPoll

  assert.equal(appliedStatusCount, 0)
  assert.equal(timer.count(), 0)
})

test('independent single-flight locks keep duplicate backend actions to one request each', async () => {
  const coordinator = createPptTaskCoordinator()
  const submitResponse = deferred()
  const confirmResponse = deferred()
  let submitRequests = 0
  let confirmRequests = 0

  const submit = () => coordinator.runOnce('submit', async () => {
    submitRequests += 1
    return submitResponse.promise
  })
  const confirm = () => coordinator.runOnce('confirm', async () => {
    confirmRequests += 1
    return confirmResponse.promise
  })

  const submitOne = submit()
  const submitTwo = submit()
  const confirmOne = confirm()
  const confirmTwo = confirm()
  assert.equal(submitRequests, 1)
  assert.equal(confirmRequests, 1)

  submitResponse.resolve('submitted')
  confirmResponse.resolve('confirmed')
  const [, duplicateSubmit, , duplicateConfirm] = await Promise.all([
    submitOne,
    submitTwo,
    confirmOne,
    confirmTwo,
  ])

  assert.equal(duplicateSubmit.started, false)
  assert.equal(duplicateConfirm.started, false)
})
