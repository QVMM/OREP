<template>
  <section class="training-panel" aria-label="下一轮训练计划">
    <header>
      <div>
        <span class="eyebrow">NEXT TRAINING</span>
        <h3>下一轮训练计划</h3>
      </div>
      <small>{{ tasks.length }} 项</small>
    </header>
    <ol v-if="tasks.length">
      <li v-for="task in tasks" :key="task.key">
        <b>{{ task.title }}</b>
        <p>{{ task.detail }}</p>
        <span>{{ task.acceptance }}</span>
      </li>
    </ol>
    <div v-else class="empty">暂无训练计划。完成结构化评分后会自动生成。</div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  priorities: { type: Array, default: () => [] },
  deductions: { type: Array, default: () => [] }
})

const tasks = computed(() => {
  const fromPriorities = props.priorities.map((item, index) => ({
    key: `priority-${index}`,
    title: item.issue || item.title || item.dimension || `训练任务 ${index + 1}`,
    detail: item.suggestion || item.action || item.description || '下一轮彩排复检该问题。',
    acceptance: item.acceptance || item.done_standard || '能提供可复核证据并稳定复现。'
  }))
  if (fromPriorities.length) return fromPriorities.slice(0, 6)
  return props.deductions.slice(0, 6).map((item, index) => ({
    key: `deduction-${item.id || index}`,
    title: item.requiredFix || item.reason || `扣分项 ${index + 1}`,
    detail: item.reason || '按扣分原因进行专项训练。',
    acceptance: item.acceptanceCriteria || '下轮评分需提供对应证据锚点。'
  }))
})
</script>

<style scoped>
.training-panel {
  padding: 18px;
  border: 1px solid rgba(115, 199, 255, 0.18);
  border-radius: 8px;
  background: rgba(10, 17, 26, 0.94);
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

h3,
b {
  color: #f3f9ff;
}

h3,
p,
ol {
  margin: 0;
}

header small,
p,
span,
.empty {
  color: rgba(230, 238, 248, 0.66);
}

ol {
  display: grid;
  gap: 10px;
  padding: 0;
  list-style: none;
}

li {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.055);
}

p {
  margin: 6px 0;
  line-height: 1.6;
}
</style>
