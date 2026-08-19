<template>
  <section class="why-panel" aria-label="为什么不是100分">
    <header>
      <div>
        <span class="eyebrow">WHY NOT 100</span>
        <h3>为什么不是 100</h3>
      </div>
      <strong>{{ finalScoreLabel }}</strong>
    </header>

    <div class="reason-grid">
      <article v-for="reason in displayReasons" :key="reason.title">
        <b>{{ reason.title }}</b>
        <p>{{ reason.text }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  calibration: { type: Object, default: () => ({}) },
  summary: { type: Object, default: () => ({}) },
  deductions: { type: Array, default: () => [] },
  observations: { type: Array, default: () => [] },
  finalScore: { type: Number, default: 0 }
})

const finalScoreLabel = computed(() => `${Number(props.finalScore || 0).toFixed(2)} / 100`)

const displayReasons = computed(() => {
  const reasons = []
  const rawReasons = props.summary?.notPerfectReasons || props.calibration?.notPerfectReasons || props.calibration?.ceiling_reasons || []
  rawReasons.forEach(item => {
    reasons.push({
      title: normalizeReasonTitle(item),
      text: normalizeReasonText(item)
    })
  })
  const cappedObservation = props.observations.find(item => Number(item.scoreCap ?? 100) < 100)
  if (cappedObservation) {
    reasons.push({
      title: '证据上限限制',
      text: `${cappedObservation.dimensionName || '部分维度'} 的可验证证据不足，本轮暂不能进入满分档。`
    })
  }
  if (props.deductions.length) {
    reasons.push({
      title: '当前扣分项仍存在',
      text: `本轮仍有 ${props.deductions.length} 个扣分项，需要按证据锚点逐项修复。`
    })
  }
  if (!reasons.length) {
    reasons.push({
      title: '证据尚未完整入库',
      text: '当前报告缺少结构化扣分或证据上限原因，请先生成 evidence bundle 或等待评分流水线完成。'
    })
  }
  return reasons.slice(0, 5)
})

function normalizeReasonTitle(value) {
  const text = String(value || '')
  if (text === 'evidence_cap') return '证据上限限制'
  if (text === 'current_deductions') return '当前扣分项'
  return text.length > 18 ? text.slice(0, 18) : text || '评分限制'
}

function normalizeReasonText(value) {
  const text = String(value || '')
  if (text === 'evidence_cap') return '本轮证据不足以支撑更高分，需补充可复核材料、演示画面或测试记录。'
  if (text === 'current_deductions') return '本轮仍存在未解决扣分项，恢复分不会抵消新问题。'
  return text || '需要补充更强证据后再进入高分档。'
}
</script>

<style scoped>
.why-panel {
  padding: 18px;
  border: 1px solid rgba(255, 179, 102, 0.2);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(31, 20, 13, 0.94), rgba(17, 19, 24, 0.94));
}

header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
  margin-bottom: 14px;
}

.eyebrow {
  color: #ffbd73;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

h3 {
  margin: 6px 0 0;
  color: #fff9f0;
}

header strong {
  color: #ffcf8a;
  font-size: 24px;
}

.reason-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

article {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.055);
}

b {
  color: #fff6e8;
}

p {
  margin: 6px 0 0;
  color: rgba(255, 246, 232, 0.68);
  line-height: 1.65;
}
</style>
