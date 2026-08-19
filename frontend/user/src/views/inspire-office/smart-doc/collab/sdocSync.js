export function jsonEq(a, b) {
  return JSON.stringify(a) === JSON.stringify(b)
}

export function planSyncPayload(acked, next) {
  const prev = Array.isArray(acked?.content) ? acked.content : []
  const blocks = Array.isArray(next?.content) ? next.content : []
  if (jsonEq(prev, blocks)) return null
  return { snapshot: blocks, blockCount: blocks.length }
}

/**
 * Decide how a client should treat an incoming snapshot.
 * ack  = ours / already applied — advance rev, never overwrite local typing
 * skip = stale, or we have unsent keystrokes
 * apply = replace the editor with remote content
 */
export function decideRemoteApply({
  incomingRev,
  lastRev,
  incomingSession,
  selfSession,
  localDirty,
  incomingContent,
  localContent,
} = {}) {
  const rev = Number(incomingRev)
  const known = Number(lastRev)
  const hasRev = Number.isFinite(rev)
  const self = incomingSession != null && String(incomingSession) === String(selfSession)
  if (self) return hasRev && Number.isFinite(known) && rev < known ? 'skip' : 'ack'
  if (hasRev && Number.isFinite(known) && rev <= known) return 'skip'
  if (jsonEq(incomingContent, localContent)) return 'ack'
  if (localDirty) return 'skip'
  return 'apply'
}

export function dirtyBlockIndices(localBlocks, ackedBlocks) {
  const dirty = new Set()
  const acked = Array.isArray(ackedBlocks) ? ackedBlocks : []
  if (!acked.length) return dirty
  const local = Array.isArray(localBlocks) ? localBlocks : []
  for (let i = 0; i < local.length; i += 1) {
    if (acked[i] && !jsonEq(local[i], acked[i])) dirty.add(i)
  }
  return dirty
}

export function blockRange(doc, index) {
  if (!doc?.forEach) return null
  let found = null
  let i = 0
  doc.forEach((node, offset) => {
    if (i === index) found = { pos: offset, node }
    i += 1
  })
  return found
}
