<template>
  <div class="ai-app-shell" :class="`is-${mode}`">
    <AiAppContent :width="width">
      <slot name="header" />
      <div class="ai-app-shell__body">
        <slot />
      </div>
    </AiAppContent>
  </div>
</template>

<script setup>
import AiAppContent from './AiAppContent.vue'

defineProps({
  mode: {
    type: String,
    required: true,
    validator: value => ['landing', 'task', 'workspace'].includes(value),
  },
  width: {
    type: String,
    default: 'wide',
    validator: value => ['wide', 'standard', 'reading', 'fluid'].includes(value),
  },
})
</script>
