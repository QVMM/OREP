<template>
  <svg
    :class="['base-icon', `base-icon--${size}`]"
    :width="sizeValue"
    :height="sizeValue"
    :style="{ color: color }"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <use :href="`#icon-${name}`" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  color: {
    type: String,
    default: 'currentColor'
  }
})

const sizeValue = computed(() => {
  const sizes = {
    small: 16,
    medium: 20,
    large: 24
  }
  return sizes[props.size]
})
</script>

<style scoped>
.base-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
