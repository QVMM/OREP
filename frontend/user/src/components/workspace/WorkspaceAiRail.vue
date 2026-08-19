<template>
  <button
    class="workspace-ai-fab"
    type="button"
    :aria-expanded="String(expanded)"
    :aria-label="expanded ? '收起 AI 助手' : '展开 AI 助手'"
    @click="expanded = !expanded"
  >
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M13 2 4 14h7l-1 8 10-13h-7l0-7Z" />
    </svg>
  </button>

  <aside class="workspace-ai-rail" :class="{ 'is-expanded': expanded }" :aria-hidden="String(!expanded)">
    <div class="workspace-ai-rail__bar">
      <strong>项目 AI 助手</strong>
      <button type="button" @click="expanded = false">收起</button>
    </div>

    <section v-if="loading" class="workspace-ai-progress workspace-ai-loading">
      <el-skeleton :rows="5" animated />
    </section>

    <section v-else class="workspace-ai-progress">
      <div class="workspace-ai-progress__head">
        <strong>训练进度</strong>
        <span>{{ home.camp?.hasCamp ? `第 ${home.camp.currentDay || 0} 天` : '未安排' }}</span>
      </div>
      <div class="workspace-ai-ring" :aria-label="`训练进度 ${campProgress}%`">
        <div class="workspace-ai-ring__chart" :style="{ '--ai-progress-angle': `${campProgress * 3.6}deg` }">
          <strong>{{ campProgress }}%</strong>
          <span>训练进度</span>
        </div>
        <p v-if="home.camp?.hasCamp">
          <strong>{{ home.camp.remainingDays ?? 0 }} 天</strong> 距离备赛结束
        </p>
        <p v-else>老师关联训练营后自动显示进度</p>
      </div>
    </section>

    <section v-if="!loading" class="workspace-ai-chat workspace-scrollbar">
      <div class="workspace-ai-head">
        <span class="workspace-ai-avatar">AI</span>
        <span>
          <strong>备赛提醒</strong>
          <small>以下内容来自你的真实任务和评分记录。</small>
        </span>
      </div>

      <div v-if="primaryAction" class="workspace-ai-suggestion">
        <strong>{{ primaryAction.title }}</strong>
        <p>{{ primaryAction.description || primaryAction.meta || '打开对应页面查看并继续处理。' }}</p>
        <router-link :to="primaryAction.path || '/'" class="workspace-ai-link">去处理</router-link>
      </div>

      <div v-if="home.latestScore?.hasReport" class="workspace-ai-result">
        <div>
          <strong>最新 AI 评分</strong>
          <span>{{ formatDate(home.latestScore.scoredAt) }}</span>
        </div>
        <p>
          本次评分 {{ Number(home.latestScore.overallScore || 0).toFixed(1) }}/100。
          {{ firstImprovement }}
        </p>
        <router-link :to="scorePath" class="workspace-ai-link">查看报告</router-link>
      </div>

      <div v-if="!primaryAction && !home.latestScore?.hasReport" class="workspace-ai-empty">
        <strong>暂时没有新的提醒</strong>
        <p>完成训练提交或生成评分报告后，这里会汇总下一步建议。</p>
      </div>
    </section>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { fetchStudentHome } from '../../modules/training/api'

const expanded = ref(false)
const loading = ref(false)
const loaded = ref(false)
const home = ref({})

const campProgress = computed(() => {
  const current = Number(home.value.camp?.currentDay || 0)
  const total = Number(home.value.camp?.totalDays || 0)
  if (!total) return 0
  return Math.min(100, Math.round((current / total) * 100))
})

const primaryAction = computed(() => home.value.nextActions?.[0] || null)
const firstImprovement = computed(() => {
  const source = home.value.latestScore?.improvementPoints
  if (Array.isArray(source)) return source[0]?.title || source[0]?.content || source[0] || '打开报告查看详细改进建议。'
  return source || '打开报告查看详细改进建议。'
})

const scorePath = computed(() => {
  const score = home.value.latestScore || {}
  if (score.reportId) return `/ai-score/report-id/${score.reportId}/result`
  if (score.sessionId) return `/ai-score/report/${score.sessionId}/result`
  return '/statistics'
})

watch(expanded, async value => {
  if (!value || loaded.value) return
  loading.value = true
  try {
    home.value = await fetchStudentHome()
    loaded.value = true
  } finally {
    loading.value = false
  }
})

function formatDate(value) {
  if (!value) return '最近'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '最近'
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date)
}
</script>

<style scoped>
.workspace-ai-rail {
  position: fixed;
  top: var(--workspace-header-height);
  right: 0;
  z-index: 30;
  width: min(var(--workspace-ai-width), calc(100vw - 24px));
  min-width: 0;
  height: calc(100vh - var(--workspace-header-height));
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  border-left: 1px solid rgba(255, 255, 255, 0.76);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.66), rgba(255, 248, 242, 0.46));
  box-shadow: inset 1px 0 0 rgba(255, 255, 255, 0.58), -18px 0 42px rgba(31, 38, 51, 0.04);
  transform: translateX(calc(100% + 18px));
  opacity: 0;
  pointer-events: none;
  transition: transform var(--workspace-transition), opacity var(--workspace-transition);
}

.workspace-ai-rail.is-expanded {
  transform: translateX(0);
  opacity: 1;
  pointer-events: auto;
}

.workspace-ai-fab {
  position: fixed;
  right: -12px;
  top: 50%;
  z-index: 31;
  width: 30px;
  min-width: 0;
  height: 54px;
  border: 0;
  border-radius: 14px 0 0 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, var(--workspace-orange-600), #ff7a45);
  box-shadow: -8px 12px 26px rgba(240, 75, 24, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.24);
  cursor: pointer;
  transform: translateY(-50%);
  transition: transform var(--workspace-transition), box-shadow var(--workspace-transition), opacity var(--workspace-transition);
  opacity: 0.9;
}

.workspace-ai-fab:hover,
.workspace-ai-fab[aria-expanded="true"] {
  transform: translate(-12px, -50%);
  opacity: 1;
}

.workspace-ai-fab svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.workspace-ai-rail__bar {
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.workspace-ai-rail__bar strong {
  color: var(--workspace-ink-900);
  font-size: 14px;
}

.workspace-ai-rail__bar button {
  border: 0;
  background: transparent;
  color: var(--workspace-orange-600);
  cursor: pointer;
  font-weight: 800;
}

.workspace-ai-progress,
.workspace-ai-chat {
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 24px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.74), rgba(255, 247, 241, 0.48));
  box-shadow: 0 12px 26px rgba(118, 72, 35, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.86);
}

.workspace-ai-progress {
  padding: 12px;
}

.workspace-ai-loading {
  min-height: 190px;
}

.workspace-ai-progress__head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--workspace-ink-900);
  font-size: 12px;
}

.workspace-ai-progress__head span {
  color: var(--workspace-ink-500);
  font-weight: 500;
}

.workspace-ai-ring {
  min-height: 122px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  gap: 4px;
  text-align: center;
  background: rgba(255, 255, 255, 0.46);
}

.workspace-ai-ring__chart {
  width: 86px;
  height: 86px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  align-content: center;
  background:
    radial-gradient(circle, rgba(255, 255, 255, 0.96) 0 56%, transparent 57%),
    conic-gradient(
      var(--workspace-orange-600) 0 var(--ai-progress-angle, 0deg),
      rgba(255, 224, 209, 0.86) var(--ai-progress-angle, 0deg) 360deg
    );
}

.workspace-ai-ring__chart strong {
  color: var(--workspace-ink-900);
  font: 800 21px/1 var(--workspace-font-number);
}

.workspace-ai-ring__chart span,
.workspace-ai-ring p {
  color: var(--workspace-ink-500);
  font-size: 10px;
}

.workspace-ai-chat {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 13px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workspace-ai-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workspace-ai-avatar {
  width: 34px;
  height: 34px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, var(--workspace-orange-600), #ff8050);
  font-size: 11px;
  font-weight: 800;
}

.workspace-ai-head span:last-child {
  display: grid;
  gap: 2px;
}

.workspace-ai-head strong {
  color: var(--workspace-ink-900);
  font-size: 15px;
}

.workspace-ai-head small {
  color: var(--workspace-ink-500);
  font-size: 12px;
  line-height: 1.45;
}

.workspace-ai-suggestion,
.workspace-ai-result {
  border: 1px solid rgba(255, 174, 142, 0.3);
  border-radius: 18px;
  padding: 13px;
  background: linear-gradient(145deg, rgba(255, 247, 243, 0.78), rgba(255, 255, 255, 0.52));
}

.workspace-ai-suggestion strong,
.workspace-ai-result strong {
  color: var(--workspace-ink-900);
  font-size: 14px;
}

.workspace-ai-suggestion p,
.workspace-ai-result p {
  margin-top: 6px;
  color: var(--workspace-ink-500);
  font-size: 12px;
  line-height: 1.55;
}

.workspace-ai-result div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.workspace-ai-result span {
  color: var(--workspace-ink-500);
  font-size: 10px;
}

.workspace-ai-link {
  display: inline-flex;
  margin-top: 8px;
  color: var(--workspace-orange-600);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.workspace-ai-empty {
  min-height: 140px;
  display: grid;
  place-content: center;
  gap: 6px;
  padding: 18px;
  text-align: center;
  color: var(--workspace-ink-500);
}

.workspace-ai-empty strong {
  color: var(--workspace-ink-900);
  font-size: 14px;
}

.workspace-ai-empty p {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
}

@media (max-width: 1279px) {
  .workspace-ai-rail {
    top: 0;
    height: 100vh;
  }

  .workspace-ai-fab {
    top: auto;
    bottom: 92px;
    transform: none;
  }

  .workspace-ai-fab:hover,
  .workspace-ai-fab[aria-expanded="true"] {
    transform: translateX(-12px);
  }
}
</style>
