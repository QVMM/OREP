function nid(prefix = 'n') {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

export function defaultMindMap() {
  return {
    root: {
      id: 'root',
      text: '中心主题',
      children: [
        { id: 'c1', text: '分支一', children: [] },
        { id: 'c2', text: '分支二', children: [] },
      ],
    },
  }
}

export function createMindMapJSON(data = defaultMindMap()) {
  return {
    type: 'mindMap',
    attrs: { data },
  }
}

export function walkMind(node, visit, parent = null) {
  if (!node) return
  visit(node, parent)
  ;(node.children || []).forEach((child) => walkMind(child, visit, node))
}

export function findMindNode(root, id) {
  let found = null
  walkMind(root, (node, parent) => {
    if (node.id === id) found = { node, parent }
  })
  return found
}

export function addMindChild(data, parentId) {
  const next = clone(data || defaultMindMap())
  const hit = findMindNode(next.root, parentId || next.root.id)
  if (!hit) return next
  if (depthOf(next.root, hit.node.id) >= 3) return next
  hit.node.children = hit.node.children || []
  hit.node.children.push({ id: nid('m'), text: '新节点', children: [] })
  return next
}

export function addMindSibling(data, nodeId) {
  const next = clone(data || defaultMindMap())
  const hit = findMindNode(next.root, nodeId)
  if (!hit?.parent) return next
  const list = hit.parent.children || []
  const idx = list.findIndex((n) => n.id === nodeId)
  list.splice(idx + 1, 0, { id: nid('m'), text: '新节点', children: [] })
  return next
}

export function removeMindNode(data, nodeId) {
  const next = clone(data || defaultMindMap())
  if (!nodeId || nodeId === next.root.id) return next
  const hit = findMindNode(next.root, nodeId)
  if (!hit?.parent) return next
  hit.parent.children = (hit.parent.children || []).filter((n) => n.id !== nodeId)
  return next
}

export function renameMindNode(data, nodeId, text) {
  const next = clone(data || defaultMindMap())
  const hit = findMindNode(next.root, nodeId)
  if (!hit) return next
  hit.node.text = String(text || '').slice(0, 24) || '未命名'
  return next
}

function depthOf(root, id, depth = 1) {
  if (root.id === id) return depth
  for (const child of root.children || []) {
    const d = depthOf(child, id, depth + 1)
    if (d) return d
  }
  return 0
}

const MM_H = 32
const MM_GAP_Y = 14
const MM_GAP_X = 52
const MM_MIN_W = 76
const MM_MAX_W = 168
const MM_PAD = 20

function measureMind(text) {
  const w = Math.min(MM_MAX_W, Math.max(MM_MIN_W, 20 + String(text || '').length * 13))
  return { w, h: MM_H }
}

function subtreeHeight(node) {
  const kids = node.children || []
  if (!kids.length) return MM_H
  return Math.max(
    MM_H,
    kids.reduce((sum, child) => sum + subtreeHeight(child), 0) + MM_GAP_Y * (kids.length - 1)
  )
}

export function layoutMindMap(data) {
  const root = (data && data.root) || defaultMindMap().root
  const acc = { nodes: [], edges: [], width: MM_PAD, height: MM_PAD }
  const totalH = subtreeHeight(root)
  placeMind(root, MM_PAD, MM_PAD + totalH / 2, acc)
  acc.width = Math.max(acc.width + MM_PAD, 280)
  acc.height = Math.max(acc.height + MM_PAD, 120)
  return acc
}

function placeMind(node, x, yCenter, acc) {
  const { w, h } = measureMind(node.text)
  const y = yCenter - h / 2
  acc.nodes.push({ id: node.id, x, y, w, h, text: node.text || '未命名' })
  acc.width = Math.max(acc.width, x + w)
  acc.height = Math.max(acc.height, y + h)
  const kids = node.children || []
  if (!kids.length) return
  let top = yCenter - subtreeHeight(node) / 2
  for (const child of kids) {
    const ch = subtreeHeight(child)
    const cy = top + ch / 2
    acc.edges.push({
      x1: x + w,
      y1: yCenter,
      x2: x + w + MM_GAP_X,
      y2: cy,
    })
    placeMind(child, x + w + MM_GAP_X, cy, acc)
    top += ch + MM_GAP_Y
  }
}

export function defaultFlowChart() {
  return {
    nodes: [
      { id: 'a', text: '开始', x: 28, y: 20, kind: 'start' },
      { id: 'b', text: '步骤', x: 28, y: 104, kind: 'rect' },
      { id: 'c', text: '结束', x: 28, y: 188, kind: 'end' },
    ],
    edges: [
      { from: 'a', to: 'b' },
      { from: 'b', to: 'c' },
    ],
  }
}

export function createFlowChartJSON(data = defaultFlowChart()) {
  return {
    type: 'flowChart',
    attrs: { data },
  }
}

export function addFlowNode(data, kind = 'rect', x = 180, y = 40) {
  const next = clone(data || defaultFlowChart())
  next.nodes = next.nodes || []
  const label = kind === 'diamond' ? '判断' : kind === 'start' ? '开始' : kind === 'end' ? '结束' : '步骤'
  next.nodes.push({ id: nid('f'), text: label, x, y, kind })
  return next
}

export function moveFlowNode(data, id, x, y) {
  const next = clone(data || defaultFlowChart())
  const node = (next.nodes || []).find((n) => n.id === id)
  if (!node) return next
  node.x = Math.max(8, Math.round(x))
  node.y = Math.max(8, Math.round(y))
  return next
}

export function connectFlow(data, from, to) {
  const next = clone(data || defaultFlowChart())
  if (!from || !to || from === to) return next
  next.edges = next.edges || []
  if (next.edges.some((e) => e.from === from && e.to === to)) return next
  next.edges.push({ from, to })
  return next
}

export function removeFlowSelection(data, nodeId, edgeKey) {
  const next = clone(data || defaultFlowChart())
  if (nodeId) {
    next.nodes = (next.nodes || []).filter((n) => n.id !== nodeId)
    next.edges = (next.edges || []).filter((e) => e.from !== nodeId && e.to !== nodeId)
  }
  if (edgeKey) {
    const [from, to] = String(edgeKey).split('>')
    next.edges = (next.edges || []).filter((e) => !(e.from === from && e.to === to))
  }
  return next
}

export function renameFlowNode(data, id, text) {
  const next = clone(data || defaultFlowChart())
  const node = (next.nodes || []).find((n) => n.id === id)
  if (!node) return next
  node.text = String(text || '').slice(0, 20) || '未命名'
  return next
}

export function flowNodeBox(node) {
  const kind = node.kind || 'rect'
  const w = kind === 'diamond' ? 112 : 108
  const h = kind === 'diamond' ? 64 : 40
  return { ...node, w, h }
}

export function flowEdgePath(from, to) {
  const a = flowNodeBox(from)
  const b = flowNodeBox(to)
  const acx = a.x + a.w / 2
  const acy = a.y + a.h / 2
  const bcx = b.x + b.w / 2
  const bcy = b.y + b.h / 2
  const vertical = Math.abs(bcy - acy) >= Math.abs(bcx - acx)
  let x1
  let y1
  let x2
  let y2
  if (vertical) {
    const down = bcy >= acy
    x1 = acx
    y1 = down ? a.y + a.h : a.y
    x2 = bcx
    y2 = down ? b.y : b.y + b.h
  } else {
    const right = bcx >= acx
    x1 = right ? a.x + a.w : a.x
    y1 = acy
    x2 = right ? b.x : b.x + b.w
    y2 = bcy
  }
  const mx = (x1 + x2) / 2
  const my = (y1 + y2) / 2
  return { x1, y1, x2, y2, mx, my, d: `M ${x1} ${y1} L ${x2} ${y2}` }
}

export function flowBounds(data) {
  const nodes = (data?.nodes || []).map(flowNodeBox)
  if (!nodes.length) return { width: 280, height: 160 }
  const maxX = Math.max(...nodes.map((n) => n.x + n.w))
  const maxY = Math.max(...nodes.map((n) => n.y + n.h))
  return { width: Math.max(280, maxX + 24), height: Math.max(160, maxY + 24) }
}
