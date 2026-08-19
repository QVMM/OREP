<template>
  <node-view-wrapper
    as="section"
    class="sdoc-protect"
    :class="{ 'is-sealed': sealed }"
    :data-label="label"
  >
    <div v-if="sealed" class="sdoc-protect__seal" contenteditable="false">
      <i aria-hidden="true">锁</i>
      <span>{{ label }}</span>
    </div>
    <template v-else>
      <div class="sdoc-protect__bar" contenteditable="false">
        <i aria-hidden="true">锁</i>
        <span>{{ label }}</span>
      </div>
      <node-view-content class="sdoc-protect__body" />
    </template>
  </node-view-wrapper>
</template>

<script setup>
import { computed } from 'vue'
import { NodeViewContent, NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

const label = computed(() => props.node.attrs.label || '此段仅教师可见')
const sealed = computed(() => {
  if (props.node.attrs.sealed) return true
  return !props.extension.options.canEditProtected
})
</script>
