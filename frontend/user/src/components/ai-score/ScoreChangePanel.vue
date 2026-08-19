<template>
  <section class="score-change-panel" aria-label="连续评分复核">
    <header>
      <div>
        <span class="eyebrow">ROADSHOW MEMORY</span>
        <h3>上轮问题复核</h3>
      </div>
      <strong>追回 {{ formatScore(summary.recoveredPoints) }} 分</strong>
    </header>
    <div class="change-metrics">
      <div>
        <b>{{ summary.recoveredCount || 0 }}</b>
        <span>已复核修复</span>
      </div>
      <div>
        <b>{{ formatScore(summary.currentDeductedPoints) }}</b>
        <span>本轮扣分</span>
      </div>
      <div>
        <b>{{ summary.newIssueCount || 0 }}</b>
        <span>新增问题</span>
      </div>
    </div>
    <div v-if="recoveries.length" class="recovery-list">
      <article v-for="item in recoveries" :key="item.id">
        <b>{{ item.dimensionName || '上轮扣分项' }}</b>
        <strong>+{{ formatScore(item.recoveredPoints) }}</strong>
        <p>{{ item.acceptanceCriteria || item.reason || '本轮证据已通过恢复复核。' }}</p>
      </article>
    </div>
    <div v-else class="empty">暂无已追回扣分项。</div>
  </section>
</template>

<script setup>
defineProps({
  summary: { type: Object, default: () => ({}) },
  recoveries: { type: Array, default: () => [] }
})

function formatScore(value) {
  const number = Number(value || 0)
  return Number.isFinite(number) ? number.toFixed(2) : '0.00'
}
</script>

<style scoped>
.score-change-panel {
  padding: 18px;
  border: 1px solid rgba(126, 231, 176, 0.18);
  border-radius: 8px;
  background: rgba(9, 20, 16, 0.94);
}

header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.eyebrow {
  color: #7ee7b0;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

h3,
b,
strong {
  color: #f5fff8;
}

h3,
p {
  margin: 0;
}

header strong {
  color: #7ee7b0;
  font-size: 22px;
}

.change-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.change-metrics div,
.recovery-list article {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.055);
}

.change-metrics b {
  display: block;
  font-size: 24px;
}

span,
p,
.empty {
  color: rgba(232, 245, 237, 0.66);
}

.recovery-list {
  display: grid;
  gap: 8px;
}

.recovery-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.recovery-list p {
  grid-column: 1 / -1;
  line-height: 1.6;
}
</style>
