import { createRequire } from 'node:module'
import test from 'node:test'
import assert from 'node:assert/strict'

const require = createRequire(import.meta.url)

const storage = new Map()
globalThis.localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key)
}

const {
  clearSubmissionDraft,
  loadSubmissionDraft,
  saveSubmissionDraft,
  uploadTimeoutMs
} = require('./submissionDraft.js')

test('draft persists uploaded asset for retry', () => {
  storage.clear()
  saveSubmissionDraft(88, {
    content: '说明',
    pendingAsset: { fileUrl: '/uploads/a.pdf', fileName: 'a.pdf' }
  })
  const draft = loadSubmissionDraft(88)
  assert.equal(draft.content, '说明')
  assert.equal(draft.pendingAsset.fileUrl, '/uploads/a.pdf')
  clearSubmissionDraft(88)
  assert.equal(loadSubmissionDraft(88), null)
})

test('upload timeout grows with file size and has a floor', () => {
  assert.equal(uploadTimeoutMs({ size: 1024 }), 180000)
  const large = uploadTimeoutMs({ size: 400 * 1024 * 1024 })
  assert.ok(large > 180000)
  assert.ok(large <= 15 * 60 * 1000)
})
