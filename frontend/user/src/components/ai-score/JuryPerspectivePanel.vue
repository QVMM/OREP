<template>
  <section class="jury-perspective-panel" aria-label="AI评审团复核">
    <!-- Empty state -->
    <div v-if="isEmpty" class="jury-empty">
      <p>当前评分会话暂未生成 AI 评审团复核</p>
      <button
        v-if="canStart"
        class="jury-start-btn"
        :disabled="starting"
        @click="$emit('start')"
      >
        {{ starting ? '生成中…' : '生成评审团复核' }}
      </button>
    </div>

    <!-- Loading state -->
    <div v-else-if="loading" class="jury-loading">
      <p>正在加载评审团复核…</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="jury-error">
      <p>{{ error }}</p>
      <button v-if="canStart" class="jury-start-btn" @click="$emit('start')">重试</button>
    </div>

    <!-- Review content -->
    <template v-else>
      <header class="jury-header">
        <div>
          <span class="eyebrow">JURY REVIEW</span>
          <h3>评审团只做复核，不修改基础分</h3>
          <p class="jury-explanation">{{ review.explanation || 'AI评审团只提供复核视角、表达盲区和训练建议，不修改基础AI评分。' }}</p>
        </div>
        <div class="jury-metrics">
          <div class="metric-item">
            <span class="metric-label">本场得分</span>
            <strong class="metric-value">{{ formatScore(review.officialScore) }}</strong>
          </div>
          <div class="metric-item">
            <span class="metric-label">评审团均分</span>
            <strong class="metric-value">{{ formatScore(review.juryAverageScore) }}</strong>
          </div>
          <div class="metric-item">
            <span class="metric-label">分差</span>
            <strong class="metric-value">{{ formatDiff(review.scoreDiffFromOfficial) }}</strong>
          </div>
          <div class="metric-item">
            <span class="metric-label">评委数</span>
            <strong class="metric-value">{{ review.successfulCount || 0 }}/{{ review.judgeCount || 0 }}</strong>
          </div>
        </div>
      </header>

      <!-- Member list -->
      <div v-if="review.members && review.members.length" class="jury-members">
        <h4>评审视角</h4>
        <div class="member-grid">
          <div
            v-for="(member, idx) in review.members"
            :key="idx"
            class="member-card"
            @click="$emit('select-member', member)"
          >
            <div class="member-header">
              <span class="member-code">{{ member.personaCode }}</span>
              <span class="member-score">{{ formatScore(member.referenceScore) }}分</span>
            </div>
            <p class="member-name">{{ member.displayName }}</p>
            <p class="member-role">{{ member.roleLabel }}</p>
            <p class="member-relation">{{ member.scoreRelationToOfficial }}</p>

            <div v-if="member.perspectiveQuestions && member.perspectiveQuestions.length" class="member-section">
              <span class="section-tag">质疑点</span>
              <ul>
                <li v-for="(q, qi) in member.perspectiveQuestions.slice(0, 2)" :key="qi">{{ q }}</li>
              </ul>
            </div>

            <div v-if="member.trainingSuggestions && member.trainingSuggestions.length" class="member-section">
              <span class="section-tag">训练建议</span>
              <ul>
                <li v-for="(s, si) in member.trainingSuggestions.slice(0, 2)" :key="si">{{ s }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Aggregate review -->
      <div v-if="review.aggregate" class="jury-aggregate">
        <div v-if="review.aggregate.consensusIssues && review.aggregate.consensusIssues.length" class="aggregate-card">
          <h4>共识问题</h4>
          <ul>
            <li v-for="(item, i) in review.aggregate.consensusIssues" :key="i">{{ item }}</li>
          </ul>
        </div>
        <div v-if="review.aggregate.disagreementFocus && review.aggregate.disagreementFocus.length" class="aggregate-card">
          <h4>分歧焦点</h4>
          <ul>
            <li v-for="(item, i) in review.aggregate.disagreementFocus" :key="i">{{ item }}</li>
          </ul>
        </div>
        <div v-if="review.aggregate.nextTrainingPriorities && review.aggregate.nextTrainingPriorities.length" class="aggregate-card">
          <h4>训练优先级</h4>
          <ul>
            <li v-for="(item, i) in review.aggregate.nextTrainingPriorities" :key="i">{{ item }}</li>
          </ul>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  review: { type: Object, default: () => ({ status: 'empty' }) },
  loading: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  error: { type: String, default: '' },
  canStart: { type: Boolean, default: true }
})

defineEmits(['start', 'select-member'])

const isEmpty = computed(() => {
  return !props.review || props.review.status === 'empty' || !props.review.members
})

function formatScore(value) {
  if (value == null) return '-'
  return Number(value).toFixed(1)
}

function formatDiff(value) {
  if (value == null) return '-'
  const num = Number(value)
  if (num === 0) return '±0.0'
  return (num > 0 ? '+' : '') + num.toFixed(1)
}
</script>

<style scoped>
.jury-perspective-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 14px;
}

.jury-empty,
.jury-loading,
.jury-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 42px 20px;
  border: 1px solid #dfe6f0;
  border-radius: 8px;
  background: #fff;
  color: #526070;
  text-align: center;
}

.jury-start-btn {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid #f15a24;
  border-radius: 6px;
  background: #f15a24;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.jury-start-btn:hover:not(:disabled) {
  background: #c2410c;
}

.jury-start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.jury-header {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr);
  gap: 14px;
  padding: 16px;
  border: 1px solid #dfe6f0;
  border-radius: 8px;
  background: #fff;
}

.eyebrow {
  color: #647086;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

h3 {
  margin: 6px 0;
  color: #172033;
  font-size: 16px;
}

h4 {
  margin: 0 0 12px;
  color: #172033;
  font-size: 16px;
  font-weight: 800;
}

.jury-explanation {
  margin: 0;
  color: #526070;
  line-height: 1.65;
  font-size: 12px;
}

.jury-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fbfdff;
}

.metric-label {
  color: #647086;
  font-size: 12px;
}

.metric-value {
  color: #f15a24;
  font-size: 20px;
  font-weight: 800;
}

.jury-members {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.member-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.member-card:hover {
  border-color: #cbd6e8;
  background: #fbfdff;
}

.member-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.member-code {
  color: #f15a24;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.member-score {
  color: #0a8f55;
  font-size: 16px;
  font-weight: 800;
}

.member-name {
  margin: 0;
  color: #172033;
  font-size: 14px;
  font-weight: 800;
}

.member-role {
  margin: 0;
  color: #526070;
  font-size: 12px;
}

.member-relation {
  margin: 0;
  color: #647086;
  font-size: 12px;
}

.member-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid #edf2f7;
}

.section-tag {
  color: #0b8580;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.member-section ul {
  margin: 0;
  padding-left: 16px;
  list-style: disc;
}

.member-section li {
  color: #526070;
  font-size: 12px;
  line-height: 1.6;
}

.jury-aggregate {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

.aggregate-card {
  padding: 12px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fbfdff;
}

.aggregate-card ul {
  margin: 0;
  padding-left: 16px;
  list-style: disc;
}

.aggregate-card li {
  color: #526070;
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .jury-header {
    grid-template-columns: 1fr;
  }

  .member-grid {
    grid-template-columns: 1fr;
  }

  .jury-aggregate {
    grid-template-columns: 1fr;
  }
}
</style>
