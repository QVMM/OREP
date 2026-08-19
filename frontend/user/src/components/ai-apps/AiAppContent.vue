<template>
  <div class="ai-app-content" :class="`is-${width}`">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  width: {
    type: String,
    default: 'wide',
    validator: value => ['wide', 'standard', 'reading', 'fluid'].includes(value),
  },
})
</script>
