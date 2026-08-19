<template>
  <n-spin :show="show" class="loading-overlay">
    <div class="loading-content">
      <slot></slot>
    </div>
  </n-spin>
</template>

<script setup lang="ts">
import { NSpin } from 'naive-ui'

interface Props {
  show: boolean
}

defineProps<Props>()
</script>

<style scoped>
.loading-overlay {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.loading-content {
  width: 100%;
  height: 100%;
}

:deep(.n-spin-container) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 10, 26, 0.8);
  border-radius: inherit;
}

:deep(.n-spin-content) {
  width: 100%;
  height: 100%;
}
</style>
