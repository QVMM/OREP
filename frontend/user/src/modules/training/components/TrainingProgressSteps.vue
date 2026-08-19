<template>
  <div class="training-progress-steps" :aria-label="label" data-testid="training-progress-steps">
    <ol class="training-progress-steps__list">
      <li
        v-for="(step, index) in steps"
        :key="step.key || step.title"
        class="training-progress-steps__item"
        :class="[
          `is-${step.state}`,
          `has-${connectorState(index)}-connector`
        ]"
        :aria-current="step.state === 'current' ? 'step' : undefined"
      >
        <span class="training-progress-steps__connector" aria-hidden="true"></span>
        <span class="training-progress-steps__node" aria-hidden="true">
          <Check v-if="step.state === 'done'" />
          <span v-else>{{ index + 1 }}</span>
        </span>
        <strong>{{ step.title }}</strong>
        <small>{{ step.label }}</small>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { Check } from '@element-plus/icons-vue'

const props = defineProps({
  steps: {
    type: Array,
    required: true
  },
  label: {
    type: String,
    default: '训练进度'
  }
})

function connectorState(index) {
  if (index >= props.steps.length - 1) return 'none'

  const current = props.steps[index]
  const next = props.steps[index + 1]

  if (current.state === 'done' && next.state === 'done') return 'done'
  if (current.state === 'done' && next.state === 'current') return 'active'
  return 'idle'
}
</script>

<style scoped>
.training-progress-steps {
  width: 100%;
  margin: var(--ds-space-4) 0 var(--ds-space-3);
  overflow: visible;
  scrollbar-width: none;
}

.training-progress-steps::-webkit-scrollbar {
  display: none;
}

.training-progress-steps__list {
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(96px, 1fr));
  list-style: none;
}

.training-progress-steps__item {
  position: relative;
  min-width: 0;
  display: grid;
  justify-items: center;
  text-align: center;
}

.training-progress-steps__connector {
  position: absolute;
  z-index: 0;
  top: 15px;
  left: calc(50% + 16px);
  width: calc(100% - 32px);
  height: 2px;
  background: var(--ds-line-strong);
  transition: background-color 180ms ease;
}

.training-progress-steps__item:last-child .training-progress-steps__connector {
  display: none;
}

.training-progress-steps__item.has-done-connector .training-progress-steps__connector {
  background: var(--ds-green);
}

.training-progress-steps__item.has-active-connector .training-progress-steps__connector {
  background: var(--ds-line-strong);
}

.training-progress-steps__node {
  position: relative;
  z-index: 1;
  width: 32px;
  height: 32px;
  border: 2px solid var(--ds-line-strong);
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--ds-faint);
  background: var(--ds-card-bg);
  font-size: var(--ds-text-micro);
  font-weight: 700;
  line-height: 1;
  transition:
    color 180ms ease,
    background-color 180ms ease,
    border-color 180ms ease,
    transform 180ms cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 180ms ease;
}

.training-progress-steps__node svg {
  width: 16px;
  height: 16px;
  color: currentColor;
  stroke-width: 2.5;
}

.training-progress-steps__item strong {
  margin-top: 6px;
  color: var(--ds-ink-2);
  font-size: var(--ds-text-micro);
  line-height: 1.35;
}

.training-progress-steps__item small {
  margin-top: 2px;
  color: var(--ds-faint);
  font-size: 10px;
  line-height: 1.35;
}

.training-progress-steps__item.is-current .training-progress-steps__node {
  border-color: var(--ds-orange-action);
  color: #fff;
  background: var(--ds-orange-action);
  box-shadow: 0 4px 10px rgba(232, 74, 28, 0.16);
}

.training-progress-steps__item.is-current small {
  color: var(--ds-orange-action);
  font-weight: 700;
}

.training-progress-steps__item.is-done small,
.training-progress-steps__item.is-available small {
  color: var(--ds-status-success-fg);
}

.training-progress-steps__item.is-done .training-progress-steps__node {
  border-color: var(--ds-green);
  color: #fff;
  background: var(--ds-green);
  box-shadow: 0 3px 8px rgba(15, 159, 110, 0.12);
}

.training-progress-steps__item.is-available .training-progress-steps__node {
  border-color: var(--ds-green);
  color: var(--ds-green);
}

@media (max-width: 720px) {
  .training-progress-steps {
    padding-top: 4px;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .training-progress-steps__list {
    min-width: 440px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .training-progress-steps__connector,
  .training-progress-steps__node {
    transition: none;
  }
}
</style>
