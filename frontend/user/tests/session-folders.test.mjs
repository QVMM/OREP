import test from 'node:test'
import assert from 'node:assert/strict'
import { groupSessionsByFolder } from '../src/modules/assistant-core/sessionFolders.js'

test('groups sessions into folders and unfiled', () => {
  const folders = [
    { id: 1, name: '讲稿', slug: 'script' },
    { id: 2, name: '路演', slug: 'roadshow' },
  ]
  const sessions = [
    { id: 10, title: '改稿 · 讲稿', folderId: 1 },
    { id: 11, title: '路演复盘', folderId: 2 },
    { id: 12, title: '随便问问', folderId: null },
  ]
  const { groups, unfiled } = groupSessionsByFolder(folders, sessions)
  assert.equal(groups[0].sessions[0].id, 10)
  assert.equal(groups[1].sessions[0].id, 11)
  assert.equal(unfiled[0].id, 12)
})
