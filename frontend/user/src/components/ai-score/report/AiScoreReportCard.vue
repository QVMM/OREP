<template>
  <section class="report-card" :class="tone">
    <slot />
  </section>
</template>

<script setup>
defineProps({
  tone: { type: String, default: '' }
})
</script>

<style scoped>
.report-card {
  min-width: 0;
  padding: 18px;
  border: 1px solid #dde5f2;
  border-radius: 12px;
  background: #fff;
}

.report-card.soft {
  background: #f8fbff;
}

.report-card.warning {
  border-color: #ffd7bd;
  background: #fffaf6;
}

.report-card.success {
  border-color: #bfe8cf;
  background: #f6fdf8;
}
</style>
