<template>
  <component
    :is="title ? 'section' : 'div'"
    class="ai-app-section"
    :class="`is-${density}`"
    :aria-label="title || undefined"
  >
    <header v-if="title || description || $slots.actions" class="ai-app-section__header">
      <div v-if="title || description" class="ai-app-section__heading">
        <h2 v-if="title">{{ title }}</h2>
        <p v-if="description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="ai-app-section__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="ai-app-section__body">
      <slot />
    </div>
  </component>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
  description: {
    type: String,
    default: '',
  },
  density: {
    type: String,
    default: 'default',
    validator: value => ['default', 'compact'].includes(value),
  },
})
</script>
