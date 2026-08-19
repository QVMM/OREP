<template>
  <section class="orep-metric-strip" aria-label="关键指标">
    <article v-for="metric in metrics" :key="metric.label" class="orep-metric-strip__item">
      <span>{{ metric.label }}</span>
      <strong>{{ metric.value }}</strong>
      <small>{{ metric.hint }}</small>
    </article>
  </section>
</template>

<script setup>
defineProps({
  metrics: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.orep-metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--orep-border-soft);
  border-radius: 22px;
  background: oklch(1 0.003 255 / 0.76);
  overflow: hidden;
}

.orep-metric-strip__item {
  min-height: 118px;
  padding: 20px;
  border-right: 1px solid var(--orep-border-soft);
  display: grid;
  align-content: center;
  gap: 6px;
}

.orep-metric-strip__item:last-child {
  border-right: 0;
}

.orep-metric-strip span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 800;
}

.orep-metric-strip strong {
  color: var(--orep-text-strong);
  font-size: 30px;
  line-height: 1;
  letter-spacing: 0;
}

.orep-metric-strip small {
  color: var(--orep-faint);
  font-size: 12px;
}

@media (max-width: 820px) {
  .orep-metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .orep-metric-strip__item:nth-child(2) {
    border-right: 0;
  }
}

@media (max-width: 520px) {
  .orep-metric-strip {
    grid-template-columns: 1fr;
  }

  .orep-metric-strip__item {
    border-right: 0;
    border-bottom: 1px solid var(--orep-border-soft);
  }

  .orep-metric-strip__item:last-child {
    border-bottom: 0;
  }
}
</style>
