import assert from 'node:assert/strict'
import test from 'node:test'
import {
  clipPreview,
  dedupePeersByUser,
  mergePeerList,
  peerListLocatorsEq,
  remoteLocatorsChanged,
  resolvePeerCaret,
  roleLabel,
  sdocUserColor,
  shouldDrawRemoteCaret,
} from '../src/views/inspire-office/smart-doc/collab/sdocCollab.js'
import { isSdocKind, officeKind, officeKindLabel } from '../src/views/inspire-office/smart-doc/sdocSplit.js'
import { decideRemoteApply, dirtyBlockIndices, planSyncPayload } from '../src/views/inspire-office/smart-doc/collab/sdocSync.js'
import { readFileSync } from 'node:fs'

test('user color is stable and aligned with 8-slot palette', () => {
  assert.equal(sdocUserColor(1), sdocUserColor(1))
  assert.equal(sdocUserColor(1), '#2b579a')
  assert.equal(sdocUserColor(8), sdocUserColor(0))
  assert.notEqual(sdocUserColor(1), sdocUserColor(2))
})

test('preview clips and role labels stay short', () => {
  assert.equal(clipPreview('短'), '短')
  assert.equal(clipPreview('x'.repeat(40)).length, 33)
  assert.match(clipPreview('x'.repeat(40)), /…$/)
  assert.equal(roleLabel('TEACHER'), '教师')
  assert.equal(roleLabel('STUDENT'), '学生')
})

test('self locator changes must not count as remote caret movement', () => {
  const li = { sessionId: 'li', userId: 10, name: '李', block: 5, offset: 10, endOffset: 10, from: 80, to: 80 }
  const zhang = { sessionId: 'z', userId: 16, name: '张申', block: 2, offset: 4, endOffset: 4, from: 30, to: 30 }
  const liTyped = { ...li, offset: 11, endOffset: 11, from: 81, to: 81 }
  assert.equal(remoteLocatorsChanged('li', [li, zhang], [liTyped, zhang]), false)
  assert.equal(remoteLocatorsChanged('li', [li, zhang], [liTyped, { ...zhang, offset: 5 }]), true)
})

test('one avatar and caret per person, and never draw on the local caret', () => {
  const a = { sessionId: 'z1', userId: 16, name: '张申', editing: false }
  const b = { sessionId: 'z2', userId: 16, name: '张申', editing: true }
  const c = { sessionId: 'li', userId: 10, name: '李' }
  assert.deepEqual(dedupePeersByUser([a, b, c]).map((p) => p.sessionId), ['z2', 'li'])
  assert.equal(dedupePeersByUser([a, { ...a, sessionId: 'z9' }, c])[0].sessionId, 'z1')
  assert.equal(shouldDrawRemoteCaret({ from: 10, to: 10 }, { head: 10 }), false)
  assert.equal(shouldDrawRemoteCaret({ from: 9, to: 9 }, { head: 10 }), false)
  assert.equal(shouldDrawRemoteCaret({ from: 4, to: 4 }, { head: 10 }), true)
})

test('split pane classifies sdoc vs Word/PPT/sheet', () => {
  assert.equal(officeKind({ ext: 'sdoc' }), 'sdoc')
  assert.equal(officeKind({ ext: 'docx' }), 'word')
  assert.equal(officeKind({ documentType: 'slide', ext: 'pptx' }), 'slide')
  assert.equal(officeKind({ ext: 'xlsx' }), 'sheet')
  assert.equal(isSdocKind({ ext: 'pptx' }), false)
  assert.equal(officeKindLabel('word'), 'Word')
})

test('peer merge keeps avatars through a blank heartbeat', () => {
  const li = { sessionId: 'li', userId: 10, name: '李' }
  const zhang = { sessionId: 'z', userId: 16, name: '张申' }
  const kept = mergePeerList([li, zhang], [], { now: 1000, graceMs: 4000 })
  assert.equal(kept.length, 2)
  const later = mergePeerList(kept, [{ ...zhang, preview: '额' }], { now: 1500, graceMs: 4000 })
  assert.equal(later.find((p) => p.userId === 16).preview, '额')
  assert.ok(later.some((p) => p.userId === 10))
  assert.equal(mergePeerList(later, [], { now: 6000, graceMs: 4000 }).length, 0)
})

test('peer locator compare ignores heartbeat-only fields so typing does not rebuild carets', () => {
  const zhang = { sessionId: 'z', userId: 16, name: '张申', color: '#c43a12', block: 2, offset: 4, endOffset: 4, from: 30, to: 30 }
  const sameSpot = { ...zhang, editing: true, preview: '额' }
  const moved = { ...zhang, offset: 5, endOffset: 5, to: 31 }
  assert.equal(peerListLocatorsEq([zhang], [sameSpot]), true)
  assert.equal(peerListLocatorsEq([zhang], [moved]), false)
  assert.equal(peerListLocatorsEq([zhang], []), false)
})

test('peer caret maps by block index and ignores stale absolute positions', () => {
  const p1 = { isTextblock: true, nodeSize: 10, content: { size: 8 } }
  const p2 = { isTextblock: true, nodeSize: 6, content: { size: 4 } }
  const doc = {
    content: { size: 16 },
    descendants(fn) {
      fn(p1, 0)
      fn(p2, 10)
    },
  }
  const onSecond = resolvePeerCaret(doc, { block: 1, offset: 2, endOffset: 2 })
  assert.deepEqual(onSecond, { from: 13, to: 13 })
  assert.equal(resolvePeerCaret(doc, { from: 99, to: 120 }), null)
  assert.deepEqual(resolvePeerCaret(doc, { from: 3, to: 5 }), { from: 3, to: 5 })
  assert.equal(
    resolvePeerCaret(doc, { block: 0, offset: 99, endOffset: 99 }),
    null,
    'stale offset must not snap to the block end (the typist caret)',
  )
})

test('sync payload always sends a full snapshot so the other client cannot miss a paragraph', () => {
  const a = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: '一' }] }] }
  const b = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: '二' }] }] }
  const c = { type: 'doc', content: [
    { type: 'paragraph', content: [{ type: 'text', text: '一' }] },
    { type: 'paragraph', content: [{ type: 'text', text: '新' }] },
  ] }
  assert.equal(planSyncPayload(a, a), null)
  const changed = planSyncPayload(a, b)
  assert.ok(changed.snapshot)
  assert.equal(changed.snapshot[0].content[0].text, '二')
  const inserted = planSyncPayload(a, c)
  assert.ok(inserted.snapshot)
  assert.equal(inserted.blockCount, 2)
  assert.equal(dirtyBlockIndices([{ type: 'paragraph' }], []).size, 0)
})

test('remote apply uses rev + localDirty, not wall-clock timestamps', () => {
  const local = [{ type: 'paragraph', content: [{ type: 'text', text: '旧' }] }]
  const remote = [{ type: 'paragraph', content: [{ type: 'text', text: '新' }] }]
  assert.equal(decideRemoteApply({
    incomingRev: 3, lastRev: 2, incomingSession: 'b', selfSession: 'a',
    localDirty: false, incomingContent: remote, localContent: local,
  }), 'apply')
  assert.equal(decideRemoteApply({
    incomingRev: 2, lastRev: 2, incomingSession: 'b', selfSession: 'a',
    localDirty: false, incomingContent: remote, localContent: local,
  }), 'skip')
  assert.equal(decideRemoteApply({
    incomingRev: 3, lastRev: 2, incomingSession: 'a', selfSession: 'a',
    localDirty: true, incomingContent: local, localContent: remote,
  }), 'ack')
  assert.equal(decideRemoteApply({
    incomingRev: 4, lastRev: 2, incomingSession: '__poll__', selfSession: 'a',
    localDirty: true, incomingContent: remote, localContent: remote,
  }), 'ack')
  assert.equal(decideRemoteApply({
    incomingRev: 4, lastRev: 2, incomingSession: '__poll__', selfSession: 'a',
    localDirty: true, incomingContent: remote, localContent: local,
  }), 'skip')
  assert.equal(decideRemoteApply({
    incomingRev: 4, lastRev: -1, incomingSession: '__poll__', selfSession: 'a',
    localDirty: false, incomingContent: remote, localContent: local,
  }), 'apply')
})

test('editor has presence bar and author-color toggle, no AI chrome', () => {
  const editor = readFileSync(new URL('../src/views/inspire-office/smart-doc/SmartDocEditor.vue', import.meta.url), 'utf8')
  const ext = readFileSync(new URL('../src/views/inspire-office/smart-doc/schema/smartDocExtensions.js', import.meta.url), 'utf8')
  const awareness = readFileSync(new URL('../src/views/inspire-office/smart-doc/collab/sdocAwareness.js', import.meta.url), 'utf8')
  assert.match(editor, /SdocPresenceBar/)
  assert.match(editor, /tocOpen/)
  assert.match(editor, /sdoc-fmt__row/)
  assert.match(editor, /splitHost/)
  assert.match(editor, /左右分屏/)
  assert.match(editor, /按人物着色|colorByPerson/)
  assert.match(editor, /joinCollab/)
  assert.match(editor, /decideRemoteApply/)
  assert.match(editor, /subscribeCollab/)
  assert.match(editor, /remoteLocatorsChanged/)
  assert.match(editor, /if \(applyingRemote\) return/)
  assert.match(ext, /SdocAwareness/)
  assert.match(awareness, /authorId/)
  assert.match(awareness, /tr\.getMeta\(key\)/)
  assert.doesNotMatch(awareness, /tr\.docChanged \|\| tr\.selectionSet/)
  assert.match(awareness, /side: -1/)
  assert.doesNotMatch(editor, /小启/)
  assert.doesNotMatch(editor, /WPS AI/)
})
