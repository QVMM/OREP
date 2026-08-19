<template>
  <section class="review-task-panel" aria-label="当前扣分复盘任务">
    <header>
      <div>
        <span class="eyebrow">REVIEW TASKS</span>
        <h3>当前扣分项</h3>
      </div>
      <small>{{ deductions.length }} 项</small>
    </header>
    <div v-if="deductions.length" class="task-list">
      <article v-for="item in deductions" :key="item.id">
        <div class="task-head">
          <span>{{ item.dimensionName || '综合维度' }}</span>
          <strong>-{{ formatScore(item.deductedPoints) }}</strong>
        </div>
        <b>{{ item.reason || '未说明扣分原因' }}</b>
        <dl>
          <div>
            <dt>整改动作</dt>
            <dd>{{ item.requiredFix || '补充材料并复盘演示流程。' }}</dd>
          </div>
          <div>
            <dt>验收标准</dt>
            <dd>{{ item.acceptanceCriteria || '下轮评分需要可打开的证据锚点。' }}</dd>
          </div>
        </dl>
      </article>
    </div>
    <div v-else class="empty">暂无当前扣分项。</div>
  </section>
</template>

<script setup>
defineProps({
  deductions: { type: Array, default: () => [] }
})

function formatScore(value) {
  const number = Number(value || 0)
  return Number.isFinite(number) ? number.toFixed(2) : '0.00'
}
</script>

<style scoped>
.review-task-panel {
  padding: 18px;
  border: 1px solid rgba(255, 126, 126, 0.16);
  border-radius: 8px;
  background: rgba(24, 13, 15, 0.94);
}

header,
.task-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

header {
  margin-bottom: 14px;
}

.eyebrow {
  color: #ff8d8d;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

h3,
b,
strong,
dd {
  color: #fff7f7;
}

h3,
dl {
  margin: 0;
}

header small,
span,
dt,
.empty {
  color: rgba(248, 232, 232, 0.66);
}

.task-list {
  display: grid;
  gap: 10px;
}

article {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.055);
}

.task-head {
  margin-bottom: 8px;
}

strong {
  color: #ff9f9f;
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

dl div {
  padding: 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.16);
}

dd {
  margin: 4px 0 0;
  line-height: 1.55;
}

@media (max-width: 760px) {
  dl {
    grid-template-columns: 1fr;
  }
}
</style>
