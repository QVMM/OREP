<template>
  <section class="orep-flow-rail" aria-label="路演准备流程">
    <article
      v-for="(step, index) in steps"
      :key="step.key"
      class="orep-flow-rail__step"
      :class="{ 'is-current': step.current, 'is-done': step.done }"
    >
      <span class="orep-flow-rail__index">{{ String(index + 1).padStart(2, '0') }}</span>
      <div>
        <strong>{{ step.title }}</strong>
        <small>{{ step.description }}</small>
      </div>
    </article>
  </section>
</template>

<script setup>
defineProps({
  steps: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.orep-flow-rail {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.orep-flow-rail__step {
  min-height: 112px;
  padding: 16px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 18px;
  background: oklch(1 0.003 255 / 0.78);
  display: grid;
  align-content: space-between;
  gap: 14px;
}

.orep-flow-rail__step.is-current {
  border-color: oklch(0.74 0.12 255);
  background: var(--orep-blue-soft);
}

.orep-flow-rail__step.is-done .orep-flow-rail__index {
  color: var(--orep-green);
}

.orep-flow-rail__index {
  color: var(--orep-faint);
  font-size: 12px;
  font-weight: 900;
}

.orep-flow-rail strong {
  display: block;
  color: var(--orep-text-strong);
  font-size: 14px;
  line-height: 1.3;
}

.orep-flow-rail small {
  display: block;
  margin-top: 5px;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.45;
}

@media (max-width: 1120px) {
  .orep-flow-rail {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .orep-flow-rail {
    grid-template-columns: 1fr;
  }
}
</style>
