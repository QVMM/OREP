<template>
  <RouterLink
    v-if="to"
    :class="buttonClasses"
    :to="to"
    :aria-disabled="disabled || loading ? 'true' : undefined"
    :aria-busy="loading ? 'true' : undefined"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__spinner"></span>
    <span :class="['base-button__content', { 'base-button__content--hidden': loading }]">
      <slot />
    </span>
  </RouterLink>
  <a
    v-else-if="href"
    :class="buttonClasses"
    :href="href"
    :target="target || undefined"
    :rel="rel || undefined"
    :aria-disabled="disabled || loading ? 'true' : undefined"
    :aria-busy="loading ? 'true' : undefined"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__spinner"></span>
    <span :class="['base-button__content', { 'base-button__content--hidden': loading }]">
      <slot />
    </span>
  </a>
  <button
    v-else
    :class="buttonClasses"
    :type="nativeType"
    :disabled="disabled || loading"
    :aria-busy="loading ? 'true' : undefined"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__spinner"></span>
    <span :class="['base-button__content', { 'base-button__content--hidden': loading }]">
      <slot />
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  type: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'ghost', 'text', 'danger'].includes(value)
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large', 'icon'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  to: {
    type: [String, Object],
    default: ''
  },
  href: {
    type: String,
    default: ''
  },
  target: {
    type: String,
    default: ''
  },
  rel: {
    type: String,
    default: ''
  },
  nativeType: {
    type: String,
    default: 'button',
    validator: (value) => ['button', 'submit', 'reset'].includes(value)
  }
})

const emit = defineEmits(['click'])
const buttonClasses = computed(() => [
  'base-button',
  `base-button--${props.type}`,
  `base-button--${props.size}`,
  { 'base-button--disabled': props.disabled },
  { 'base-button--loading': props.loading }
])

const handleClick = (event) => {
  if (props.disabled || props.loading) {
    event.preventDefault()
    return
  }
  emit('click', event)
}
</script>

<style scoped>
.base-button {
  box-sizing: border-box;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-btn-icon-gap);
  border: 1px solid transparent;
  border-radius: var(--ds-radius-pill);
  font-family: var(--ds-font-sans);
  font-weight: var(--ds-weight-bold);
  line-height: 1;
  cursor: pointer;
  transition:
    color var(--ds-control-transition),
    background-color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition),
    transform var(--ds-motion-duration-fast) var(--ds-motion-ease-out);
  position: relative;
  user-select: none;
  white-space: nowrap;
  box-shadow: none;
  transform: none;
  text-decoration: none;
}

.base-button:active:not(.base-button--disabled):not(.base-button--loading) {
  transform: none;
}

:global(.workspace-app.is-motion-enabled .base-button:active:not(.base-button--disabled):not(.base-button--loading)) {
  transform: translateY(var(--ds-motion-press-y));
}

.base-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
  box-shadow: var(--ds-btn-focus-ring);
}

.base-button--primary {
  background-color: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
}

.base-button--primary:hover:not(.base-button--disabled):not(.base-button--loading) {
  background-color: var(--ds-btn-primary-bg-hover);
}

.base-button--primary:active:not(.base-button--disabled):not(.base-button--loading) {
  background-color: var(--ds-btn-primary-bg-active);
}

.base-button--secondary {
  background-color: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
  border-color: var(--ds-btn-secondary-border);
}

.base-button--secondary:hover:not(.base-button--disabled):not(.base-button--loading) {
  color: var(--ds-orange-500);
  background-color: var(--ds-btn-secondary-bg-hover);
  border-color: var(--ds-btn-secondary-border-hover);
}

.base-button--secondary:active:not(.base-button--disabled):not(.base-button--loading) {
  background-color: var(--ds-btn-secondary-bg-active);
  border-color: var(--ds-btn-secondary-border-active);
}

.base-button--ghost {
  color: var(--ds-muted);
  background: transparent;
}

.base-button--ghost:hover:not(.base-button--disabled):not(.base-button--loading) {
  color: var(--ds-ink-2);
  background: var(--ds-btn-ghost-bg-hover);
}

.base-button--ghost:active:not(.base-button--disabled):not(.base-button--loading) {
  background: var(--ds-btn-ghost-bg-active);
}

.base-button--text {
  background-color: transparent;
  color: var(--ds-btn-selected-fg);
  padding-left: var(--ds-space-2);
  padding-right: var(--ds-space-2);
}

.base-button--text:hover:not(.base-button--disabled):not(.base-button--loading) {
  color: var(--ds-orange-800);
  background-color: var(--ds-orange-wash);
}

.base-button--text:active:not(.base-button--disabled):not(.base-button--loading) {
  background-color: var(--ds-orange-soft);
}

.base-button--danger {
  background-color: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-danger-fg);
  border-color: var(--ds-btn-danger-border);
}

.base-button--danger:hover:not(.base-button--disabled):not(.base-button--loading) {
  background-color: var(--ds-btn-danger-bg-hover);
  border-color: var(--ds-btn-danger-fg);
}

.base-button--danger:active:not(.base-button--disabled):not(.base-button--loading) {
  background-color: var(--ds-btn-danger-bg-active);
}

.base-button--danger:focus-visible {
  outline-color: var(--ds-red);
  box-shadow: var(--ds-danger-focus-ring);
}

.base-button[aria-pressed="true"]:not(.base-button--disabled):not(.base-button--loading) {
  color: var(--ds-btn-selected-fg);
  background: var(--ds-btn-selected-bg);
  border-color: var(--ds-btn-selected-border);
}

.base-button--small {
  min-height: var(--ds-btn-height-sm);
  height: var(--ds-btn-height-sm);
  padding: 0 var(--ds-btn-padding-x-sm);
  font-size: var(--ds-btn-font-sm);
}

.base-button--medium {
  min-height: var(--ds-btn-height);
  height: var(--ds-btn-height);
  padding: 0 var(--ds-btn-padding-x);
  font-size: var(--ds-btn-font);
}

.base-button--large {
  min-height: var(--ds-btn-height);
  height: var(--ds-btn-height);
  padding: 0 var(--ds-btn-padding-x);
  font-size: var(--ds-btn-font);
}

.base-button--icon {
  width: var(--ds-btn-height-icon);
  min-width: var(--ds-btn-height-icon);
  height: var(--ds-btn-height-icon);
  padding: 0;
}

.base-button--disabled,
.base-button:disabled:not(.base-button--loading) {
  color: var(--ds-btn-disabled-fg);
  background: var(--ds-btn-disabled-bg);
  border-color: var(--ds-btn-disabled-border);
  opacity: 1;
  cursor: not-allowed;
  box-shadow: none;
}

.base-button--loading {
  pointer-events: none;
  cursor: wait;
}

.base-button__content {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-btn-icon-gap);
}

.base-button__content :deep(svg) {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
}

.base-button__spinner {
  position: absolute;
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: base-button-spin 0.72s linear infinite;
}

.base-button__content--hidden {
  opacity: 0;
}

@keyframes base-button-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .base-button {
    transition-duration: 0.01ms;
  }

  :global(.workspace-app.is-motion-enabled .base-button:active:not(.base-button--disabled):not(.base-button--loading)) {
    transform: none;
  }
}
</style>
