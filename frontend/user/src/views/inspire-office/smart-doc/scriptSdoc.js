export function clipStepText(text, max = 80) {
  const s = String(text || '').replace(/\s+/g, ' ').trim()
  if (s.length <= max) return s
  return `${s.slice(0, max).trim()}…`
}

export function collectNodeText(node) {
  if (!node) return ''
  if (typeof node.text === 'string') return node.text
  const kids = Array.isArray(node.content) ? node.content : []
  return kids.map((child) => {
    const part = collectNodeText(child)
    if (child.type === 'paragraph' && part) return `${part}\n`
    return part
  }).join('').replace(/\n+$/, '')
}

export function firstScriptStep(doc) {
  if (!doc) return null
  let found = null
  doc.descendants((node, pos) => {
    if (node.type?.name === 'scriptStep') {
      found = { node, pos }
      return false
    }
    return true
  })
  return found
}

export function findScriptStepAt($from) {
  for (let d = $from.depth; d > 0; d -= 1) {
    const node = $from.node(d)
    if (node?.type?.name === 'scriptStep') {
      return { node, depth: d, pos: $from.before(d) }
    }
  }
  return null
}

export function neighborStepText(doc, currentPos, dir) {
  if (!doc) return null
  let found = null
  const wantAfter = dir > 0
  let passed = false
  doc.descendants((node, pos) => {
    if (node.type?.name !== 'scriptStep') return true
    if (pos === currentPos) {
      passed = true
      return false
    }
    if (!wantAfter && !passed) found = node
    if (wantAfter && passed && !found) found = node
    return true
  })
  if (!found) return null
  return {
    id: found.attrs.stepId,
    role: found.attrs.role || '',
    content: clipStepText(found.textContent || collectNodeText(found.toJSON?.() || found)),
  }
}
