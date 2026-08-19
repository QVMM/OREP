export const SDOC_USER_COLORS = [
  '#c43a12', '#2b579a', '#217346', '#6d28d9',
  '#b45309', '#0f766e', '#be185d', '#334155',
]

export function sdocUserColor(userId) {
  const n = Number(userId)
  if (!Number.isFinite(n)) return SDOC_USER_COLORS[0]
  const idx = ((n % SDOC_USER_COLORS.length) + SDOC_USER_COLORS.length) % SDOC_USER_COLORS.length
  return SDOC_USER_COLORS[idx]
}

export function roleLabel(role) {
  const key = String(role || '').toUpperCase()
  if (key === 'TEACHER') return '教师'
  if (key === 'STUDENT') return '学生'
  if (key === 'SCHOOL_ADMIN') return '校管'
  if (key === 'ADMIN') return '管理员'
  if (key === 'REVIEWER') return '评委'
  if (key === 'EXPERT') return '专家'
  return '成员'
}

export function clipPreview(text, max = 32) {
  const t = String(text || '').replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

export function collectTextblocks(doc) {
  const blocks = []
  if (!doc?.descendants) return blocks
  doc.descendants((node, pos) => {
    if (node.isTextblock) {
      blocks.push({ node, pos })
      return false
    }
    return true
  })
  return blocks
}

function offsetInBlock(block, pos) {
  const inner = Math.max(0, pos - block.pos - 1)
  return Math.max(0, Math.min(block.node.content.size, inner))
}

export function selectionContext(editor) {
  if (!editor) {
    return { from: 0, to: 0, block: -1, offset: 0, endOffset: 0, preview: '', inProtect: false }
  }
  const { from, to, $from } = editor.state.selection
  let inProtect = false
  for (let d = $from.depth; d > 0; d -= 1) {
    if ($from.node(d).type.name === 'protectedRegion') {
      inProtect = true
      break
    }
  }
  const blocks = collectTextblocks(editor.state.doc)
  let block = -1
  let offset = 0
  let endOffset = 0
  for (let i = 0; i < blocks.length; i += 1) {
    const start = blocks[i].pos
    const end = start + blocks[i].node.nodeSize
    if (block < 0 && from >= start && from < end) {
      block = i
      offset = offsetInBlock(blocks[i], from)
    }
    if (to >= start && to <= end) {
      endOffset = offsetInBlock(blocks[i], to)
      if (block < 0) {
        block = i
        offset = endOffset
      }
    }
  }
  const raw = inProtect ? '' : editor.state.doc.textBetween(from, Math.min(to + 24, editor.state.doc.content.size), ' ')
  return {
    from,
    to,
    block,
    offset,
    endOffset,
    preview: inProtect ? '仅教师可见' : clipPreview(raw || $from.parent?.textContent || ''),
    inProtect,
  }
}

export function peerLocatorKey(peer) {
  if (!peer) return ''
  return [
    peer.sessionId, peer.userId, peer.name, peer.color,
    peer.block, peer.offset, peer.endOffset, peer.from, peer.to,
  ].map((v) => String(v ?? '')).join('\0')
}

export function peerListLocatorsEq(a, b) {
  const x = Array.isArray(a) ? a : []
  const y = Array.isArray(b) ? b : []
  if (x.length !== y.length) return false
  for (let i = 0; i < x.length; i += 1) {
    if (peerLocatorKey(x[i]) !== peerLocatorKey(y[i])) return false
  }
  return true
}

export function remoteLocatorsChanged(selfSession, prev, next) {
  const others = (list) => (Array.isArray(list) ? list : []).filter(
    (peer) => peer && String(peer.sessionId) !== String(selfSession),
  )
  return !peerListLocatorsEq(others(prev), others(next))
}

export function mergePeerList(prev, next, { now = Date.now(), graceMs = 4000 } = {}) {
  const incoming = Array.isArray(next) ? next : []
  const previous = Array.isArray(prev) ? prev : []
  const bySession = new Map()
  for (const peer of previous) {
    if (!peer?.sessionId) continue
    bySession.set(String(peer.sessionId), { ...peer, _seen: peer._seen || now })
  }
  const seenNow = new Set()
  for (const peer of incoming) {
    if (!peer?.sessionId) continue
    const id = String(peer.sessionId)
    seenNow.add(id)
    bySession.set(id, { ...peer, _seen: now })
  }
  const out = []
  for (const peer of bySession.values()) {
    if (seenNow.has(String(peer.sessionId)) || now - (peer._seen || 0) < graceMs) out.push(peer)
  }
  return out
}

export function dedupePeersByUser(peers) {
  const groups = new Map()
  for (const peer of peers || []) {
    if (!peer) continue
    const id = peer.userId != null ? String(peer.userId) : String(peer.sessionId || '')
    if (!groups.has(id)) groups.set(id, [])
    groups.get(id).push(peer)
  }
  const out = []
  for (const list of groups.values()) {
    const editing = list.filter((peer) => peer.editing)
    const pool = editing.length ? editing : list
    pool.sort((a, b) => String(a.sessionId).localeCompare(String(b.sessionId)))
    out.push(pool[0])
  }
  return out
}

export function shouldDrawRemoteCaret(caret, selection, slack = 2) {
  if (!caret || selection == null) return false
  const head = Number(selection.head)
  if (!Number.isFinite(head)) return true
  const from = Number(caret.from)
  const to = Number(caret.to)
  const near = (pos) => Number.isFinite(pos) && Math.abs(pos - head) <= slack
  return !near(from) && !near(to)
}

/** Map a peer onto this client's document. Prefer block+offset; never clamp a stale pos to the doc end. */
export function resolvePeerCaret(doc, peer) {
  if (!doc || !peer) return null
  const blocks = collectTextblocks(doc)
  const bi = Number(peer.block)
  if (Number.isInteger(bi) && bi >= 0) {
    if (!blocks[bi]) return null
    const item = blocks[bi]
    const max = item.node.content.size
    const rawOff = Number(peer.offset)
    const startOff = Number.isFinite(rawOff) ? rawOff : 0
    if (startOff < 0 || startOff > max) return null
    const rawEnd = peer.endOffset == null ? startOff : Number(peer.endOffset)
    const endOff = Number.isFinite(rawEnd) ? rawEnd : startOff
    if (endOff < startOff || endOff > max) return null
    return { from: item.pos + 1 + startOff, to: item.pos + 1 + endOff }
  }
  const size = doc.content.size
  const from = Number(peer.from)
  const to = Number(peer.to)
  if (from > 0 && to >= from && to <= size && from <= size) {
    return { from, to }
  }
  return null
}
