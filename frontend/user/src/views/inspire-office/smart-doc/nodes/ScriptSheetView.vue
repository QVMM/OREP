<template>
  <node-view-wrapper as="section" class="sdoc-script-sheet" data-sdoc-script-sheet>
    <header class="sdoc-script-sheet__head" contenteditable="false">
      <strong>逐字稿</strong>
      <span>角色 / 页 / 时长锁定，只改正文</span>
    </header>
    <div class="sdoc-script-sheet__cols" contenteditable="false">
      <span>角色</span>
      <span>页</span>
      <span>时长</span>
      <span>正文</span>
    </div>
    <node-view-content class="sdoc-script-sheet__body" />
  </node-view-wrapper>
</template>

<script setup>
import { NodeViewContent, NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

defineProps(nodeViewProps)
</script>
