<template>
  <section class="score-summary-header" aria-label="AI评分报告摘要">
    <div>
      <span class="eyebrow">SCORING SUMMARY</span>
      <h2>{{ title }}</h2>
      <p>{{ subtitle }}</p>
    </div>
    <div class="summary-score">
      <span>综合评分</span>
      <strong>{{ formatScore(score) }}</strong>
      <small>/100</small>
    </div>
    <dl>
      <div>
        <dt>评分一致性编号</dt>
        <dd>{{ sessionNo || '-' }}</dd>
      </div>
      <div>
        <dt>赛道</dt>
        <dd>{{ trackName || '未绑定赛道' }}</dd>
      </div>
      <div>
        <dt>评分来源</dt>
        <dd>{{ sourceLabel }}</dd>
      </div>
      <div>
        <dt>证据置信度</dt>
        <dd>{{ evidenceConfidenceLabel }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  rawScore: { type: Number, default: 0 },
  sessionNo: { type: String, default: '' },
  trackName: { type: String, default: '' },
  sourceType: { type: String, default: '' },
  evidenceConfidence: { type: Number, default: 0 },
  completedAt: { type: [String, Date], default: '' }
})

const title = computed(() => {
  if (props.score >= 85) return '具备较强竞争力，继续补强证据闭环'
  if (props.score >= 70) return '基础表现稳定，关键扣分项需要专项修复'
  if (props.score >= 60) return '项目有基础，需要优先修复高影响问题'
  return '当前风险较高，需要重构演示与证据链'
})

const subtitle = computed(() => {
  const date = props.completedAt ? `完成于 ${formatDate(props.completedAt)}` : '报告已生成'
  const raw = props.rawScore && props.rawScore !== props.score ? `，原始 ${formatScore(props.rawScore)} 分` : ''
  return `${date}${raw}。本页仅展示用户可见评分依据，不展示内部规则版本、权重或 prompt。`
})

const sourceLabel = computed(() => {
  const source = props.sourceType || ''
  if (source === 'uploaded_video') return '上传视频'
  if (source === 'local_backup') return '本地导入'
  if (source === 'meeting_recording') return '路演录制'
  return source || '-'
})

const evidenceConfidenceLabel = computed(() => {
  if (!props.evidenceConfidence) return '待采样'
  return `${Math.round(props.evidenceConfidence * 100)}%`
})

function formatScore(value) {
  const number = Number(value || 0)
  return Number.isFinite(number) ? number.toFixed(2) : '0.00'
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}
</script>

<style scoped>
.score-summary-header {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) 180px minmax(280px, 1fr);
  gap: 18px;
  align-items: stretch;
  padding: 20px;
  border: 1px solid rgba(125, 255, 178, 0.18);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(9, 16, 22, 0.96), rgba(18, 25, 34, 0.9));
}

.eyebrow {
  color: #72f0a3;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

h2 {
  margin: 8px 0;
  color: #f7fbff;
  font-size: 24px;
}

p,
dt {
  color: rgba(229, 236, 246, 0.68);
}

p {
  margin: 0;
  line-height: 1.7;
}

.summary-score {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 16px;
  border-radius: 8px;
  background: rgba(102, 240, 160, 0.1);
}

.summary-score span,
.summary-score small {
  color: rgba(229, 236, 246, 0.7);
}

.summary-score strong {
  color: #73f5a7;
  font-size: 42px;
  line-height: 1;
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

dl div {
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
}

dt {
  font-size: 12px;
}

dd {
  margin: 5px 0 0;
  color: #f7fbff;
  font-weight: 700;
}

@media (max-width: 900px) {
  .score-summary-header {
    grid-template-columns: 1fr;
  }
}
</style>
