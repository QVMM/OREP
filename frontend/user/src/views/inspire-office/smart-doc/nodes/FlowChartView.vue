<template>
  <node-view-wrapper as="figure" class="sdoc-diagram" data-kind="flow" contenteditable="false">
    <div class="sdoc-diagram__bar" @mousedown.stop>
      <strong>流程图</strong>
      <button type="button" @click="add('rect')">加步骤</button>
      <button type="button" @click="add('diamond')">加判断</button>
      <button type="button" :class="{ 'is-on': linking }" @click="linking = !linking">
        {{ linking ? '连线中…' : '连线' }}
      </button>
      <button type="button" :disabled="!selectedId && !selectedEdge" @click="removeSel">删除</button>
    </div>
    <svg
      class="sdoc-diagram__svg"
      :width="bounds.width"
      :height="bounds.height"
      :viewBox="`0 0 ${bounds.width} ${bounds.height}`"
      @mousedown.stop="onBg"
    >
      <defs>
        <marker id="sdoc-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#8e8e93" />
        </marker>
      </defs>
      <g
        v-for="edge in edgePaths"
        :key="`${edge.from}>${edge.to}`"
        class="sdoc-diagram__edge"
        :class="{ 'is-on': selectedEdge === `${edge.from}>${edge.to}` }"
        @mousedown.stop="selectEdge(edge)"
      >
        <path :d="edge.d" fill="none" marker-end="url(#sdoc-arrow)" />
      </g>
      <g
        v-for="node in boxes"
        :key="node.id"
        class="sdoc-diagram__shape"
        :class="{ 'is-on': selectedId === node.id, [`is-${node.kind}`]: true }"
        @mousedown.stop="onNodeDown($event, node)"
      >
        <polygon v-if="node.kind === 'diamond'" :points="diamondPoints(node)" />
        <rect v-else :x="node.x" :y="node.y" :width="node.w" :height="node.h" :rx="node.kind === 'rect' ? 8 : 20" />
        <foreignObject :x="node.x" :y="node.y" :width="node.w" :height="node.h">
          <div xmlns="http://www.w3.org/1999/xhtml" class="sdoc-diagram__fo">
            <input
              class="sdoc-diagram__input"
              :value="node.text"
              maxlength="20"
              @mousedown.stop
              @keydown.stop
              @focus="selectedId = node.id"
              @change="rename(node.id, $event.target.value)"
            />
          </div>
        </foreignObject>
      </g>
    </svg>
  </node-view-wrapper>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
import {
  addFlowNode,
  connectFlow,
  defaultFlowChart,
  flowBounds,
  flowEdgePath,
  flowNodeBox,
  moveFlowNode,
  removeFlowSelection,
  renameFlowNode,
} from '../schema/smartDocDiagrams'

const props = defineProps(nodeViewProps)
const selectedId = ref('')
const selectedEdge = ref('')
const linking = ref(false)
const linkFrom = ref('')
let drag = null

const data = computed(() => props.node.attrs.data || defaultFlowChart())
const boxes = computed(() => (data.value.nodes || []).map(flowNodeBox))
const bounds = computed(() => flowBounds(data.value))
const edgePaths = computed(() => {
  const map = Object.fromEntries(boxes.value.map((n) => [n.id, n]))
  return (data.value.edges || [])
    .map((edge) => {
      const from = map[edge.from]
      const to = map[edge.to]
      if (!from || !to) return null
      return { ...edge, ...flowEdgePath(from, to) }
    })
    .filter(Boolean)
})

function commit(next) {
  props.updateAttributes({ data: next })
}

function add(kind) {
  const offset = (data.value.nodes || []).length * 16
  commit(addFlowNode(data.value, kind, 160 + (offset % 80), 28 + offset))
}

function rename(id, text) {
  commit(renameFlowNode(data.value, id, text))
}

function selectEdge(edge) {
  selectedEdge.value = `${edge.from}>${edge.to}`
  selectedId.value = ''
  linking.value = false
}

function removeSel() {
  commit(removeFlowSelection(data.value, selectedId.value, selectedEdge.value))
  selectedId.value = ''
  selectedEdge.value = ''
}

function onBg() {
  if (linking.value) {
    linkFrom.value = ''
    return
  }
  selectedId.value = ''
  selectedEdge.value = ''
}

function onNodeDown(event, node) {
  selectedEdge.value = ''
  if (linking.value) {
    if (!linkFrom.value) {
      linkFrom.value = node.id
      selectedId.value = node.id
      return
    }
    commit(connectFlow(data.value, linkFrom.value, node.id))
    linkFrom.value = ''
    linking.value = false
    selectedId.value = node.id
    return
  }
  selectedId.value = node.id
  drag = {
    id: node.id,
    startX: event.clientX,
    startY: event.clientY,
    ox: node.x,
    oy: node.y,
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

function onMove(event) {
  if (!drag) return
  commit(moveFlowNode(
    data.value,
    drag.id,
    drag.ox + event.clientX - drag.startX,
    drag.oy + event.clientY - drag.startY
  ))
}

function onUp() {
  drag = null
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUp)
}

function diamondPoints(node) {
  const cx = node.x + node.w / 2
  const cy = node.y + node.h / 2
  return `${cx},${node.y} ${node.x + node.w},${cy} ${cx},${node.y + node.h} ${node.x},${cy}`
}

onBeforeUnmount(onUp)
</script>
