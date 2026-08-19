import assert from 'node:assert/strict'
import test from 'node:test'
import {
  addFlowNode,
  addMindChild,
  connectFlow,
  createFlowChartJSON,
  createMindMapJSON,
  defaultFlowChart,
  defaultMindMap,
  layoutMindMap,
  removeMindNode,
} from '../src/views/inspire-office/smart-doc/schema/smartDocDiagrams.js'

test('mind map JSON stores a tree, not a bitmap', () => {
  const block = createMindMapJSON()
  assert.equal(block.type, 'mindMap')
  assert.equal(block.attrs.data.root.text, '中心主题')
  assert.equal(block.attrs.data.root.children.length, 2)
  assert.equal(JSON.stringify(block).includes('data:image'), false)
})

test('mind map can add a child and refuses to delete the root', () => {
  const grown = addMindChild(defaultMindMap(), 'root')
  assert.equal(grown.root.children.length, 3)
  const same = removeMindNode(grown, 'root')
  assert.equal(same.root.id, 'root')
  assert.ok(same.root.children.length >= 2)
})

test('mind map layout returns node positions and edges', () => {
  const laid = layoutMindMap(defaultMindMap())
  assert.ok(laid.nodes.length >= 3)
  assert.ok(laid.edges.length >= 2)
  assert.ok(laid.width > 100)
  assert.ok(laid.nodes.every((n) => typeof n.x === 'number' && typeof n.y === 'number'))
})

test('flowchart JSON stores nodes and edges only', () => {
  const block = createFlowChartJSON()
  assert.equal(block.type, 'flowChart')
  assert.equal(block.attrs.data.nodes.length, 3)
  assert.equal(block.attrs.data.edges.length, 2)
  const extra = addFlowNode(defaultFlowChart(), 'diamond', 200, 40)
  assert.equal(extra.nodes.length, 4)
  const linked = connectFlow(extra, 'a', extra.nodes[3].id)
  assert.ok(linked.edges.some((e) => e.from === 'a' && e.to === extra.nodes[3].id))
})
