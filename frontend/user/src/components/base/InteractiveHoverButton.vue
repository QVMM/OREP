<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

defineOptions({
  name: 'InteractiveHoverButton',
  inheritAttrs: false
})

const props = defineProps({
  type: {
    type: String,
    default: 'primary',
    validator: value => ['primary', 'secondary'].includes(value)
  },
  size: {
    type: String,
    default: 'medium',
    validator: value => ['small', 'medium', 'large'].includes(value)
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
  nativeType: {
    type: String,
    default: 'button',
    validator: value => ['button', 'submit', 'reset'].includes(value)
  }
})

const emit = defineEmits(['click'])

const buttonClasses = computed(() => [
  'interactive-hover-button',
  `interactive-hover-button--${props.type}`,
  `interactive-hover-button--${props.size}`,
  {
    'interactive-hover-button--disabled': props.disabled,
    'interactive-hover-button--loading': props.loading
  }
])

function handleClick(event) {
  if (props.disabled || props.loading) {
    event.preventDefault()
    return
  }
  emit('click', event)
}
</script>

<template>
  <RouterLink
    v-if="to"
    v-bind="$attrs"
    :class="buttonClasses"
    :to="to"
    :aria-disabled="disabled || loading ? 'true' : undefined"
    :aria-busy="loading ? 'true' : undefined"
    @click="handleClick"
  >
    <span class="interactive-hover-button__fill" aria-hidden="true"></span>
    <span
      :class="[
        'interactive-hover-button__default',
        { 'interactive-hover-button__content--hidden': loading }
      ]"
    >
      <slot />
    </span>
    <span
      :class="[
        'interactive-hover-button__reveal',
        { 'interactive-hover-button__content--hidden': loading }
      ]"
      aria-hidden="true"
    >
      <span><slot /></span>
      <ArrowRight />
    </span>
    <span v-if="loading" class="interactive-hover-button__spinner"></span>
  </RouterLink>

  <a
    v-else-if="href"
    v-bind="$attrs"
    :class="buttonClasses"
    :href="href"
    :aria-disabled="disabled || loading ? 'true' : undefined"
    :aria-busy="loading ? 'true' : undefined"
    @click="handleClick"
  >
    <span class="interactive-hover-button__fill" aria-hidden="true"></span>
    <span
      :class="[
        'interactive-hover-button__default',
        { 'interactive-hover-button__content--hidden': loading }
      ]"
    >
      <slot />
    </span>
    <span
      :class="[
        'interactive-hover-button__reveal',
        { 'interactive-hover-button__content--hidden': loading }
      ]"
      aria-hidden="true"
    >
      <span><slot /></span>
      <ArrowRight />
    </span>
    <span v-if="loading" class="interactive-hover-button__spinner"></span>
  </a>

  <button
    v-else
    v-bind="$attrs"
    :class="buttonClasses"
    :type="nativeType"
    :disabled="disabled || loading"
    :aria-busy="loading ? 'true' : undefined"
    @click="handleClick"
  >
    <span class="interactive-hover-button__fill" aria-hidden="true"></span>
    <span
      :class="[
        'interactive-hover-button__default',
        { 'interactive-hover-button__content--hidden': loading }
      ]"
    >
      <slot />
    </span>
    <span
      :class="[
        'interactive-hover-button__reveal',
        { 'interactive-hover-button__content--hidden': loading }
      ]"
      aria-hidden="true"
    >
      <span><slot /></span>
      <ArrowRight />
    </span>
    <span v-if="loading" class="interactive-hover-button__spinner"></span>
  </button>
</template>

<style scoped>
.interactive-hover-button {
  --interactive-bg: var(--ds-btn-primary-bg);
  --interactive-fg: var(--ds-btn-primary-fg);
  --interactive-fill: #fff;
  --interactive-reveal-fg: var(--ds-orange-deep);
  position: relative;
  isolation: isolate;
  box-sizing: border-box;
  min-width: 0;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: var(--ds-radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--interactive-fg);
  background: var(--interactive-bg);
  box-shadow: none;
  cursor: pointer;
  font-family: var(--ds-font-sans);
  font-weight: var(--ds-weight-bold);
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
  user-select: none;
  transition:
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition),
    transform var(--ds-motion-duration-fast) var(--ds-motion-ease-out);
}

.interactive-hover-button--secondary {
  --interactive-bg: var(--ds-btn-secondary-bg);
  --interactive-fg: var(--ds-btn-secondary-fg);
  --interactive-fill: var(--ds-canvas-deep);
  --interactive-reveal-fg: var(--ds-ink-2);
  border-color: var(--ds-btn-secondary-border);
}

.interactive-hover-button--small {
  min-height: var(--ds-btn-height-sm);
  height: var(--ds-btn-height-sm);
  padding: 0 var(--ds-btn-padding-x-sm);
  font-size: var(--ds-btn-font-sm);
}

.interactive-hover-button--medium,
.interactive-hover-button--large {
  min-height: var(--ds-btn-height);
  height: var(--ds-btn-height);
  padding: 0 var(--ds-btn-padding-x);
  font-size: var(--ds-btn-font);
}

.interactive-hover-button__fill {
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background: var(--interactive-fill);
  clip-path: circle(4px at 20px 50%);
  transform: translateZ(0);
  transition: clip-path 340ms cubic-bezier(0.22, 1, 0.36, 1);
}

.interactive-hover-button__default,
.interactive-hover-button__reveal {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition:
    opacity 280ms ease,
    transform 340ms cubic-bezier(0.22, 1, 0.36, 1);
}

.interactive-hover-button__default {
  padding-left: 13px;
}

.interactive-hover-button__reveal {
  position: absolute;
  inset: 0;
  z-index: 2;
  color: var(--interactive-reveal-fg);
  opacity: 0;
  transform: translateX(42px);
}

.interactive-hover-button__reveal svg {
  width: 15px;
  height: 15px;
  flex: 0 0 15px;
  transition: transform 340ms cubic-bezier(0.22, 1, 0.36, 1);
}

.interactive-hover-button:hover:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__fill,
.interactive-hover-button:focus-visible:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__fill {
  clip-path: circle(150% at 20px 50%);
}

.interactive-hover-button:hover:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__default,
.interactive-hover-button:focus-visible:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__default {
  opacity: 0;
  transform: translateX(38px);
}

.interactive-hover-button:hover:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__reveal,
.interactive-hover-button:focus-visible:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__reveal {
  opacity: 1;
  transform: translateX(0);
}

.interactive-hover-button:hover:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__reveal svg,
.interactive-hover-button:focus-visible:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) .interactive-hover-button__reveal svg {
  transform: translateX(2px);
}

.interactive-hover-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
  box-shadow: var(--ds-btn-focus-ring);
}

.interactive-hover-button:active:not(.interactive-hover-button--disabled):not(.interactive-hover-button--loading) {
  transform: translateY(1px);
}

.interactive-hover-button--disabled,
.interactive-hover-button:disabled,
.interactive-hover-button--loading {
  color: var(--ds-btn-disabled-fg);
  background: var(--ds-btn-disabled-bg);
  border-color: var(--ds-btn-disabled-border);
  cursor: not-allowed;
}

.interactive-hover-button--loading {
  cursor: wait;
}

.interactive-hover-button__content--hidden {
  opacity: 0;
}

.interactive-hover-button__spinner {
  position: absolute;
  z-index: 3;
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: interactive-button-spin 0.72s linear infinite;
}

@keyframes interactive-button-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .interactive-hover-button,
  .interactive-hover-button__fill,
  .interactive-hover-button__default,
  .interactive-hover-button__reveal,
  .interactive-hover-button__reveal svg {
    transition-duration: 0.01ms;
  }
}
</style>
