<template>
  <div class="slide-editor">
    <h3>幻灯片编辑器</h3>
    <div class="editor-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
// Slide Editor Component
</script>

<style scoped>
.slide-editor {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
}

.editor-content {
  margin-top: 1rem;
}
</style>
