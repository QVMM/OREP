<template>
  <node-view-wrapper as="article" class="sdoc-script-step" data-sdoc-script-step>
    <div class="sdoc-script-step__meta" contenteditable="false">
      <strong>{{ role || '未指定角色' }}</strong>
      <span>{{ focus || '未指定页' }}</span>
      <span>{{ durationLabel }}</span>
      <button type="button" class="sdoc-script-step__ask" @mousedown.prevent @click="onAsk">问小启</button>
    </div>
    <node-view-content class="sdoc-script-step__body" />
  </node-view-wrapper>
</template>

<script setup>
import { computed, inject } from 'vue'
import { NodeViewContent, NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)
const askXiaoQi = inject('sdocAskXiaoQi', null)

const role = computed(() => props.node.attrs.role || '')
const focus = computed(() => props.node.attrs.focus || '')
const durationLabel = computed(() => {
  const raw = props.node.attrs.duration
  if (raw === '' || raw == null) return '—'
  return `${raw} 分钟`
})

function onAsk() {
  const pos = typeof props.getPos === 'function' ? props.getPos() : 0
  askXiaoQi?.(props.node, pos)
}
</script>
