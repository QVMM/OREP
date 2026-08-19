<template>
  <div class="page-header">
    <div class="page-header-left">
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
    </div>
    <div class="page-header-right">
      <slot name="extra"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 24px;
  background: var(--bg-color-container, #12122a);
  border-bottom: 1px solid var(--border-color, #2a2a4a);
  margin-bottom: 24px;
}

.page-header-left {
  flex: 1;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-color-1, #ffffff);
}

.page-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--text-color-2, #b0b0b0);
}

.page-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
