<template>
  <button
    class="collaboration-entry-button"
    :class="[`is-${variant}`, { 'is-pressed': pressed }]"
    type="button"
    :aria-label="accessibleLabel"
    :aria-expanded="pressed"
  >
    <CollaborationBrandMark class="collaboration-entry-button__mark" />
    <span v-if="variant === 'mobile'" class="collaboration-entry-button__label">{{ label }}</span>
    <span v-if="count > 0" class="collaboration-entry-button__badge" aria-hidden="true">
      {{ count > 99 ? '99+' : count }}
    </span>
    <span v-if="variant === 'desktop'" class="collaboration-entry-button__tooltip" aria-hidden="true">
      {{ label }}
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import CollaborationBrandMark from './CollaborationBrandMark.vue'

const props = defineProps({
  count: { type: Number, default: 0 },
  pressed: { type: Boolean, default: false },
  label: { type: String, default: '待办中心' },
  variant: { type: String, default: 'desktop' },
})

const accessibleLabel = computed(() => (
  props.count > 0 ? `${props.label}，${props.count} 项待处理` : props.label
))
</script>

<style scoped>
.collaboration-entry-button {
  position: relative;
  border: 0;
  padding: 0;
  color: var(--ds-ink-2);
  background: transparent;
  font: inherit;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.collaboration-entry-button.is-desktop {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  transition:
    background-color var(--ds-transition),
    transform var(--ds-transition);
}

.collaboration-entry-button.is-desktop:hover,
.collaboration-entry-button.is-desktop.is-pressed {
  background: transparent;
  box-shadow: none;
}

.collaboration-entry-button.is-desktop:active {
  transform: translateY(1px);
}

.collaboration-entry-button.is-mobile {
  min-width: 0;
  border-radius: 18px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 2px;
  transform: translateY(-4px);
}

.collaboration-entry-button__mark {
  flex: 0 0 auto;
}

.is-desktop .collaboration-entry-button__mark {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.is-desktop :deep(.collaboration-entry-button__mark svg) {
  width: 100%;
  height: 100%;
}

.is-mobile .collaboration-entry-button__mark {
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 11px;
  box-shadow: 0 5px 16px rgba(45, 108, 223, 0.14);
}

.collaboration-entry-button__label {
  color: var(--ds-ink-2);
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
}

.collaboration-entry-button__badge {
  position: absolute;
  top: -2px;
  right: -5px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border: 2px solid #fff;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange-700);
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
}

.is-mobile .collaboration-entry-button__badge {
  top: -4px;
  right: calc(50% - 24px);
}

.collaboration-entry-button__tooltip {
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  min-height: 36px;
  padding: 0 13px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  color: #fff;
  background: #292b31;
  box-shadow: 0 8px 24px rgba(18, 20, 26, 0.18);
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(-50%);
  transition: opacity var(--ds-transition), visibility var(--ds-transition);
}

.collaboration-entry-button__tooltip::before {
  content: "";
  position: absolute;
  right: 100%;
  top: 50%;
  width: 8px;
  height: 8px;
  background: inherit;
  transform: translate(4px, -50%) rotate(45deg);
}

.is-desktop:hover .collaboration-entry-button__tooltip,
.is-desktop:focus-visible .collaboration-entry-button__tooltip {
  opacity: 1;
  visibility: visible;
}

.collaboration-entry-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

@media (prefers-reduced-motion: reduce) {
  .collaboration-entry-button {
    transition-duration: 0.01ms;
  }
}
</style>
