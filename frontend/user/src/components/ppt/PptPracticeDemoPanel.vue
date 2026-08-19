<template>
  <div class="practice-panel">
    <div class="practice-hero" :class="{ 'needs-evidence': practiceDemo.completeness_status === 'needs_evidence' }">
      <div>
        <span class="quality-eyebrow">技术实操演示模块</span>
        <h2>{{ practiceDemo.demo_title }}</h2>
        <p>{{ practiceDemo.demo_goal }}。推荐场景：{{ practiceDemo.demo_scene }}。</p>
      </div>
      <strong>{{ practiceDemo.step_count || 0 }} 步</strong>
    </div>

    <div class="practice-loop-board">
      <div class="practice-loop-head">
        <div>
          <span class="quality-eyebrow">输入-操作-输出-证据-评分点闭环</span>
          <h3>实操演示要让评委看到“我做了什么、结果是什么、凭什么可信”</h3>
          <p>每一步至少要能说清输入、现场操作、输出结果、证据素材和对应评分点。</p>
        </div>
        <strong>{{ practiceLoopSummary.complete }}/{{ practiceLoopSummary.total }}</strong>
      </div>
      <div class="practice-loop-grid">
        <div
          v-for="item in practiceLoopItems"
          :key="item.step_id"
          class="practice-loop-card"
          :class="{ complete: item.complete, warning: !item.complete }"
          :data-step-id="item.step_id"
        >
          <div class="practice-loop-title">
            <span>Step {{ item.step_order }}</span>
            <strong>{{ item.complete ? '闭环较完整' : '需补闭环' }}</strong>
          </div>
          <h4>{{ item.step_title }}</h4>
          <div class="practice-loop-checks">
            <span v-for="check in item.checks" :key="check.key" :class="{ pass: check.pass }">
              {{ check.label }}
            </span>
          </div>
          <p>{{ item.next_action }}</p>
          <div class="practice-loop-actions">
            <el-button
              v-if="item.target_pages.length"
              size="small"
              text
              @click="$emit('preview-page', item.target_pages[0])"
            >
              查看页面
            </el-button>
            <el-button
              v-if="item.missing_evidence.length"
              size="small"
              type="primary"
              plain
              @click="$emit('prepare-evidence', item)"
            >
              补证据
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="practice-list">
      <div
        v-for="step in practiceDemo.steps"
        :key="step.step_id"
        class="practice-step-card"
        :class="{ 'needs-evidence': step.missing_evidence?.length }"
      >
        <div class="practice-step-index">{{ step.step_order }}</div>
        <div class="practice-step-main">
          <div class="practice-step-head">
            <div>
              <span>{{ demoModeText(step.demo_mode) }} · {{ targetPagesText(step.target_pages) }}</span>
              <h3>{{ step.step_title }}</h3>
            </div>
            <strong>{{ step.missing_evidence?.length ? '需补证据' : '证据较完整' }}</strong>
          </div>
          <p class="practice-goal">{{ step.operation_goal }}</p>
          <div class="practice-tags">
            <span v-for="point in step.technical_points" :key="point">{{ point }}</span>
          </div>
          <div class="evidence-grid">
            <div>
              <label>建议证据</label>
              <p>{{ listText(step.required_evidence) }}</p>
            </div>
            <div>
              <label>缺失提醒</label>
              <p>{{ listText(step.missing_evidence) || '暂无明显缺口' }}</p>
            </div>
          </div>
          <div class="script-box">
            <label>现场讲法</label>
            <p>{{ step.speaker_script }}</p>
          </div>
          <div class="script-box fallback">
            <label>兜底讲法</label>
            <p>{{ step.fallback_script }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['preview-page', 'prepare-evidence'])

defineProps({
  practiceDemo: { type: Object, required: true },
  practiceLoopSummary: { type: Object, default: () => ({ complete: 0, total: 0 }) },
  practiceLoopItems: { type: Array, default: () => [] },
  demoModeText: { type: Function, required: true },
  targetPagesText: { type: Function, required: true },
  listText: { type: Function, required: true }
})
</script>

<style scoped>
.practice-panel {
  display: grid;
  gap: 20px;
}

.practice-hero,
.practice-loop-board {
  padding: 22px 24px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.practice-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
}

.practice-hero.needs-evidence {
  border-color: rgba(250, 204, 21, 0.24);
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.92), rgba(255, 255, 255, 0.98));
}

.practice-hero h2,
.practice-loop-head h3 {
  margin: 6px 0 10px;
  color: #0f172a;
}

.practice-hero p,
.practice-loop-head p,
.practice-loop-card p,
.practice-goal,
.script-box p,
.evidence-grid p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.practice-hero strong,
.practice-loop-head strong {
  color: #0f172a;
  font-size: 42px;
  line-height: 1;
}

.practice-loop-head,
.practice-step-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.practice-loop-grid,
.practice-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.practice-loop-card,
.practice-step-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.98);
}

.practice-loop-card.complete {
  border-color: rgba(74, 222, 128, 0.24);
}

.practice-loop-card.warning,
.practice-step-card.needs-evidence {
  border-color: rgba(250, 204, 21, 0.24);
}

.practice-loop-title,
.practice-step-head span,
.practice-step-index {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.practice-loop-title,
.practice-loop-actions,
.practice-tags,
.practice-loop-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.practice-loop-card h4,
.practice-step-head h3 {
  margin: 10px 0;
  color: #0f172a;
}

.practice-loop-checks span,
.practice-tags span,
.practice-step-index {
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.practice-loop-checks span.pass {
  background: rgba(74, 222, 128, 0.16);
  color: #166534;
}

.practice-step-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
}

.practice-step-index {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.evidence-grid label,
.script-box label {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.script-box {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.script-box.fallback {
  background: rgba(248, 250, 252, 0.96);
}

@media (max-width: 980px) {
  .practice-hero,
  .practice-loop-head,
  .practice-step-card,
  .practice-step-head {
    grid-template-columns: 1fr;
    display: grid;
  }

  .evidence-grid {
    grid-template-columns: 1fr;
  }
}
</style>
