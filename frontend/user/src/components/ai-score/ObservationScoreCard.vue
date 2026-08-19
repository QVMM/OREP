<template>
  <section class="observation-panel" aria-label="观察点评分">
    <header>
      <div>
        <span class="eyebrow">OBSERVATIONS</span>
        <h3>观察点评分</h3>
      </div>
      <small>{{ observations.length }} 项</small>
    </header>
    <div v-if="observations.length" class="observation-grid">
      <article v-for="item in observations" :key="item.id || item.dimensionName">
        <div>
          <b>{{ item.dimensionName || '评分观察点' }}</b>
          <span>{{ evidenceLabel(item) }}</span>
        </div>
        <strong>{{ scoreText(item) }}</strong>
        <p>{{ item.modelReason || '暂无模型解释。' }}</p>
      </article>
    </div>
    <div v-else class="empty">暂无结构化观察点评分。</div>
  </section>
</template>

<script setup>
defineProps({
  observations: { type: Array, default: () => [] }
})

function scoreText(item) {
  const score = Number(item.rawScore ?? 0)
  const cap = Number(item.scoreCap ?? 100)
  return `${score.toFixed(1)} / 上限 ${cap.toFixed(1)}`
}

function evidenceLabel(item) {
  const levelMap = {
    strong: '强证据',
    medium: '中等证据',
    weak: '弱证据',
    claim: '口头主张',
    none: '无证据'
  }
  const confidence = item.confidence == null ? '' : ` · ${Math.round(Number(item.confidence) * 100)}%`
  return `${levelMap[item.evidenceLevel] || item.evidenceLevel || '待验证'}${confidence}`
}
</script>

<style scoped>
.observation-panel {
  padding: 18px;
  border: 1px solid rgba(113, 196, 255, 0.16);
  border-radius: 8px;
  background: rgba(12, 18, 26, 0.94);
}

header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.eyebrow {
  color: #73c7ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

h3 {
  margin: 6px 0 0;
  color: #f3f9ff;
}

header small,
p,
span,
.empty {
  color: rgba(230, 238, 248, 0.66);
}

.observation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

article {
  min-height: 150px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
}

article div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

b {
  color: #f3f9ff;
}

strong {
  color: #7ee7b0;
  font-size: 20px;
}

p {
  margin: 0;
  line-height: 1.65;
}
</style>
