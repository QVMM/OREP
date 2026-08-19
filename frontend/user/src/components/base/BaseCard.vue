<template>
  <div
    :class="[
      'base-card',
      { 'base-card--hoverable': hoverable },
      { 'base-card--elevated': elevated }
    ]"
  >
    <div v-if="$slots.header" class="base-card__header">
      <slot name="header" />
    </div>
    <div class="base-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="base-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  hoverable: {
    type: Boolean,
    default: false
  },
  elevated: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.base-card {
  color: var(--ds-ink);
  background: var(--ds-card-bg);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  box-shadow: var(--ds-card-shadow);
  overflow: hidden;
  transition:
    background-color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition),
    transform var(--ds-motion-duration-standard) var(--ds-motion-ease-out);
  transform: translateY(0);
}

.base-card--elevated {
  border-color: var(--ds-line);
  box-shadow: var(--ds-shadow-soft);
}

.base-card--hoverable:hover {
  border-color: var(--ds-line-strong);
  box-shadow: var(--ds-card-shadow);
}

:global(.workspace-app.is-motion-enabled .base-card--hoverable:hover) {
  border-color: rgba(232, 74, 28, 0.2);
  box-shadow: var(--ds-motion-card-shadow);
  transform: translateY(var(--ds-motion-hover-y));
}

.base-card__header {
  padding: var(--ds-space-5) var(--ds-space-6);
  border-bottom: 1px solid var(--ds-line);
}

.base-card__body {
  padding: var(--ds-space-6);
}

.base-card__footer {
  padding: var(--ds-space-4) var(--ds-space-6);
  border-top: 1px solid var(--ds-line);
}

@media (prefers-reduced-motion: reduce) {
  .base-card {
    transition-duration: 0.01ms;
  }

  :global(.workspace-app.is-motion-enabled .base-card--hoverable:hover) {
    transform: none;
  }
}
</style>
