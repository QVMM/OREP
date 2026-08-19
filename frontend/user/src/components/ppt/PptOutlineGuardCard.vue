<template>
  <div class="outline-guard-card" :class="{ 'has-warning': warnings.length }">
    <div class="guard-head">
      <div>
        <span class="guard-kicker">60 MINUTE P0 CHECK</span>
        <h3>{{ summary.title }}</h3>
        <p>{{ summary.desc }}</p>
      </div>
      <div class="guard-score">
        <div class="score-badge" :class="{ warning: warnings.length }">
          <strong>{{ passedCount }}/{{ checks.length }}</strong>
          <small>通过项</small>
        </div>
        <el-button
          size="small"
          type="primary"
          plain
          :loading="applying"
          @click="$emit('apply')"
        >
          自动应用P0结构修复
        </el-button>
      </div>
    </div>
    <div class="guard-checks">
      <div
        v-for="(check, index) in checks"
        :key="check.key"
        :class="['guard-check', { pass: check.pass, risk: !check.pass }]"
      >
        <span class="check-index">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="check-icon">
          <el-icon><CircleCheck v-if="check.pass" /><Close v-else /></el-icon>
        </span>
        <span class="check-label">{{ check.label }}</span>
      </div>
    </div>
    <div v-if="warnings.length" class="guard-warning">
      <strong>ATTENTION QUEUE</strong>
      <span>{{ warnings.join('；') }}</span>
    </div>
  </div>
</template>

<script setup>
import { CircleCheck, Close } from '@element-plus/icons-vue'

defineEmits(['apply'])

defineProps({
  summary: {
    type: Object,
    default: () => ({ title: '', desc: '' })
  },
  checks: {
    type: Array,
    default: () => []
  },
  warnings: {
    type: Array,
    default: () => []
  },
  passedCount: {
    type: Number,
    default: 0
  },
  applying: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.outline-guard-card {
  position: relative;
  overflow: hidden;
  margin-bottom: 26px;
  padding: 22px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  background:
    radial-gradient(circle at 88% 0%, rgba(122, 255, 180, 0.07), transparent 30%),
    linear-gradient(rgba(240, 241, 250, 0.018) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, 0.018) 1px, transparent 1px),
    rgba(8, 10, 14, 0.78);
  background-size: auto, 52px 52px, 52px 52px, auto;
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, 0.04);
}

.outline-guard-card.has-warning {
  border-color: rgba(255, 211, 138, 0.18);
}

.guard-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  justify-content: space-between;
  gap: 22px;
  align-items: start;
}

.guard-kicker {
  display: inline-flex;
  color: rgba(122, 255, 180, 0.78);
  font-size: 11px;
  line-height: 1;
  font-weight: 860;
  letter-spacing: 0.18em;
}

.guard-head h3 {
  margin: 12px 0 9px;
  color: #f4f6ff;
  font-size: 24px;
  line-height: 1.18;
  font-weight: 850;
}

.guard-head p {
  margin: 0;
  max-width: 820px;
  color: rgba(240, 241, 250, 0.54);
  line-height: 1.7;
  font-size: 14px;
}

.guard-score {
  display: grid;
  gap: 10px;
  justify-items: end;
}

.score-badge {
  min-width: 92px;
  display: grid;
  justify-items: center;
  gap: 4px;
  padding: 12px 16px;
  border: 1px solid rgba(122, 255, 180, 0.2);
  background: rgba(122, 255, 180, 0.045);
}

.score-badge strong {
  color: #7affb4;
  font-size: 24px;
  line-height: 1;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.score-badge small {
  color: rgba(240, 241, 250, 0.42);
  font-size: 11px;
  font-weight: 760;
}

.score-badge.warning {
  border-color: rgba(255, 211, 138, 0.24);
  background: rgba(255, 211, 138, 0.055);
}

.score-badge.warning strong {
  color: #ffd38a;
}

.guard-checks {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.guard-check {
  min-height: 56px;
  display: grid;
  grid-template-columns: 34px 22px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  background: rgba(240, 241, 250, 0.024);
  color: rgba(240, 241, 250, 0.62);
  font-weight: 760;
}

.guard-check.risk {
  border-color: rgba(255, 122, 122, 0.18);
  background: rgba(255, 122, 122, 0.045);
}

.guard-check.pass {
  border-color: rgba(122, 255, 180, 0.16);
  background: rgba(122, 255, 180, 0.04);
}

.check-index {
  color: rgba(240, 241, 250, 0.34);
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
}

.check-icon {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  color: #ffb4b4;
}

.guard-check.pass .check-icon {
  color: #7affb4;
}

.check-label {
  min-width: 0;
  color: rgba(244, 246, 255, 0.82);
  font-size: 14px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guard-warning {
  margin-top: 12px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid rgba(255, 211, 138, 0.2);
  background: rgba(255, 211, 138, 0.055);
  color: rgba(255, 211, 138, 0.88);
  line-height: 1.6;
}

.guard-warning strong {
  color: #ffd38a;
  font-size: 11px;
  font-weight: 860;
  letter-spacing: 0.16em;
  white-space: nowrap;
}

.guard-warning span {
  min-width: 0;
  color: rgba(255, 225, 176, 0.8);
  font-size: 14px;
}

.guard-score :deep(.el-button) {
  border-radius: 999px;
  border-color: rgba(122, 255, 180, 0.28);
  background: rgba(122, 255, 180, 0.065);
  color: #7affb4;
  font-weight: 820;
}

.guard-score :deep(.el-button:hover) {
  border-color: rgba(122, 255, 180, 0.55);
  background: rgba(122, 255, 180, 0.1);
  color: #b8ffd4;
}

@media (max-width: 1180px) {
  .guard-checks {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .guard-head {
    grid-template-columns: 1fr;
  }

  .guard-score {
    width: 100%;
    justify-items: start;
  }

  .guard-checks {
    grid-template-columns: 1fr;
  }
}
</style>
