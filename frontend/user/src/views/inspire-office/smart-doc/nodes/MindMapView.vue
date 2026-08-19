<template>
  <node-view-wrapper as="figure" class="sdoc-diagram" data-kind="mind" contenteditable="false">
    <div class="sdoc-diagram__bar" @mousedown.stop>
      <strong>思维导图</strong>
      <button type="button" :disabled="!selectedId" @click="addChild">加子节点</button>
      <button type="button" :disabled="!selectedId || selectedId === rootId" @click="addSibling">加同级</button>
      <button type="button" :disabled="!selectedId || selectedId === rootId" @click="removeNode">删除</button>
    </div>
    <svg
      class="sdoc-diagram__svg"
      :width="layout.width"
      :height="layout.height"
      :viewBox="`0 0 ${layout.width} ${layout.height}`"
      @mousedown.stop
    >
      <path
        v-for="(edge, i) in layout.edges"
        :key="`e-${i}`"
        class="sdoc-diagram__link"
        :d="`M ${edge.x1} ${edge.y1} C ${(edge.x1 + edge.x2) / 2} ${edge.y1}, ${(edge.x1 + edge.x2) / 2} ${edge.y2}, ${edge.x2} ${edge.y2}`"
        fill="none"
      />
      <g
        v-for="node in layout.nodes"
        :key="node.id"
        class="sdoc-diagram__node"
        :class="{ 'is-on': selectedId === node.id, 'is-root': node.id === rootId }"
        @click.stop="select(node.id)"
      >
        <rect :x="node.x" :y="node.y" :width="node.w" :height="node.h" rx="8" />
        <foreignObject :x="node.x" :y="node.y" :width="node.w" :height="node.h">
          <div xmlns="http://www.w3.org/1999/xhtml" class="sdoc-diagram__fo">
            <input
              class="sdoc-diagram__input"
              :value="node.text"
              maxlength="24"
              @mousedown.stop
              @keydown.stop
              @focus="select(node.id)"
              @change="rename(node.id, $event.target.value)"
            />
          </div>
        </foreignObject>
      </g>
    </svg>
  </node-view-wrapper>
</template>

<script setup>
import { computed, ref } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
import {
  addMindChild,
  addMindSibling,
  defaultMindMap,
  layoutMindMap,
  removeMindNode,
  renameMindNode,
} from '../schema/smartDocDiagrams'

const props = defineProps(nodeViewProps)
const selectedId = ref('root')

const data = computed(() => props.node.attrs.data || defaultMindMap())
const rootId = computed(() => data.value.root?.id || 'root')
const layout = computed(() => layoutMindMap(data.value))

function commit(next) {
  props.updateAttributes({ data: next })
}

function select(id) {
  selectedId.value = id
}

function addChild() {
  if (!selectedId.value) return
  commit(addMindChild(data.value, selectedId.value))
}

function addSibling() {
  if (!selectedId.value) return
  commit(addMindSibling(data.value, selectedId.value))
}

function removeNode() {
  if (!selectedId.value) return
  commit(removeMindNode(data.value, selectedId.value))
  selectedId.value = rootId.value
}

function rename(id, text) {
  commit(renameMindNode(data.value, id, text))
}
</script>
