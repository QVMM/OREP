import assert from 'node:assert/strict'
import test from 'node:test'

import {
  createScriptSaveCoordinator,
  runAfterSuccessfulSave,
} from '../src/utils/scriptSaveCoordinator.js'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

test('serial save commits the newest snapshot after edits made during an older request', async () => {
  let title = '旧标题'
  const requests = []
  const first = deferred()
  const second = deferred()
  const coordinator = createScriptSaveCoordinator({
    snapshot: () => ({ title }),
    persist: async snapshot => {
      requests.push(snapshot)
      await (requests.length === 1 ? first.promise : second.promise)
    },
  })

  coordinator.markDirty()
  const leavingFlush = coordinator.flush()
  title = '最新标题'
  coordinator.markDirty()

  assert.deepEqual(requests, [{ title: '旧标题' }])
  first.resolve()
  await Promise.resolve()
  await Promise.resolve()
  assert.deepEqual(requests, [{ title: '旧标题' }, { title: '最新标题' }])

  second.resolve()
  await leavingFlush
  assert.equal(coordinator.dirtyRevision, 2)
  assert.equal(coordinator.committedRevision, 2)
  assert.equal(coordinator.isDirty(), false)
})

test('concurrent flush callers share one serial runner', async () => {
  const request = deferred()
  let requestCount = 0
  const coordinator = createScriptSaveCoordinator({
    snapshot: () => ({ title: '唯一快照' }),
    persist: async () => {
      requestCount += 1
      await request.promise
    },
  })

  coordinator.markDirty()
  const firstFlush = coordinator.flush()
  const secondFlush = coordinator.flush()
  assert.equal(firstFlush, secondFlush)
  assert.equal(requestCount, 1)

  request.resolve()
  await Promise.all([firstFlush, secondFlush])
  assert.equal(requestCount, 1)
})

test('a failed save prevents the protected PDF action', async () => {
  let pdfRequests = 0

  await assert.rejects(
    runAfterSuccessfulSave({
      flush: async () => {
        const error = new Error('save failed')
        error.status = 500
        throw error
      },
      action: async () => {
        pdfRequests += 1
      },
    }),
    /save failed/
  )

  assert.equal(pdfRequests, 0)
})

