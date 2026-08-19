<template>
  <section class="metric-strip" aria-label="报告关键指标">
    <article v-for="metric in metrics" :key="metric.label" class="metric-item" :class="metric.tone">
      <span>{{ metric.label }}</span>
      <strong>{{ metric.value }}</strong>
      <small>{{ metric.hint }}</small>
    </article>
  </section>
</template>

<script setup>
defineProps({
  metrics: { type: Array, default: () => [] }
})
</script>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  overflow: hidden;
  border: 1px solid #ded6ce;
  border-radius: 8px;
  background: #fff;
}

.metric-item {
  min-height: 94px;
  padding: 16px 18px;
  border-right: 1px solid #eee5dc;
}

.metric-item:last-child {
  border-right: 0;
}

.metric-item span,
.metric-item small {
  display: block;
  color: #66728a;
  font-size: 12px;
}

.metric-item strong {
  display: block;
  margin: 7px 0 4px;
  color: #111827;
  font-size: 24px;
  line-height: 1;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.metric-item.success strong { color: #0a8f55; }
.metric-item.warning strong { color: #f26a21; }
.metric-item.danger strong { color: #e43d30; }
.metric-item.primary strong { color: #f15a24; }

@media (max-width: 720px) {
  .metric-strip {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
