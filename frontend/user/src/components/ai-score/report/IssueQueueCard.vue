<template>
  <button
    type="button"
    :class="['issue-queue-card', `priority-${issue.tone || 'p1'}`, { active }]"
    @click="$emit('select')"
  >
    <span class="priority-pill">{{ issue.level }}</span>
    <div class="issue-main">
      <header>
        <strong>{{ issue.id }}</strong>
        <b>{{ riskText }}</b>
      </header>
      <p>{{ issue.title }}</p>
      <footer>
        <span class="impact-chip">
          <small>扣分</small>
          <em>{{ impact }}</em>
        </span>
        <span class="dimension-chip">
          <small>影响</small>
          <em>{{ dimensions }}</em>
        </span>
      </footer>
    </div>
  </button>
</template>

<script setup>
defineProps({
  issue: { type: Object, required: true },
  active: { type: Boolean, default: false },
  impact: { type: String, default: '-' },
  dimensions: { type: String, default: '待识别' },
  riskText: { type: String, default: '高风险' }
})

defineEmits(['select'])
</script>

<style scoped>
.issue-queue-card {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 10px;
  width: 100%;
  min-width: 0;
  padding: 12px;
  border: 1px solid #e4ebf3;
  border-radius: 8px;
  background: #ffffff;
  color: #172033;
  text-align: left;
  cursor: pointer;
  transition: border-color .18s ease, background .18s ease, box-shadow .18s ease, transform .18s ease;
}

.issue-queue-card:hover {
  border-color: #ffc6b2;
  transform: translateY(-1px);
}

.issue-queue-card.active {
  border-color: #ff8d6b;
  background: #fffaf7;
  box-shadow: 0 0 0 2px rgba(241, 90, 36, .08);
}

.priority-pill {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 7px;
  background: #ff7a1a;
  color: #fffaf7;
  font-size: 12px;
  font-weight: 900;
}

.issue-main {
  min-width: 0;
}

.issue-main header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.issue-main strong {
  color: #253149;
  font-size: 13px;
  letter-spacing: .01em;
}

.issue-main b {
  flex: 0 0 auto;
  padding: 3px 7px;
  border-radius: 6px;
  color: #d92d20;
  background: #fff0ed;
  font-size: 12px;
  font-weight: 850;
}

.issue-main p {
  display: -webkit-box;
  margin: 8px 0 10px;
  overflow: hidden;
  color: #344054;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.issue-main footer {
  display: grid;
  gap: 5px;
}

.impact-chip,
.dimension-chip {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: #647086;
}

.impact-chip small,
.dimension-chip small {
  color: #98a2b3;
  font-size: 11px;
  font-weight: 800;
}

.impact-chip em,
.dimension-chip em {
  min-width: 0;
  overflow: hidden;
  font-style: normal;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.impact-chip em {
  color: #d92d20;
}

.dimension-chip em {
  color: #667085;
}
</style>
