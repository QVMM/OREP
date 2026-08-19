<template>
  <div class="stage-waiting-panel">
    <div class="progress-bar-wrapper">
      <el-progress
        :percentage="percentage"
        :stroke-width="10"
        :show-text="true"
        :status="percentage === 100 ? 'success' : ''"
      />
    </div>

    <div class="current-stage">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ currentStageName }}</span>
    </div>

    <div class="stage-facts-panel">
      <div v-for="fact in facts" :key="fact.label" class="stage-fact-item">
        <span>{{ fact.label }}</span>
        <strong>{{ fact.value }}</strong>
      </div>
    </div>

    <div class="stage-interpretation">
      <strong>{{ summary.title }}</strong>
      <p>{{ summary.desc }}</p>
    </div>

    <div v-if="recoveryVisible" class="outline-recovery-card">
      <div class="recovery-copy">
        <strong>{{ recoveryTitle }}</strong>
        <span>{{ recoveryDesc }}</span>
      </div>
      <div class="recovery-actions">
        <el-button :loading="retryLoading" type="primary" @click="$emit('retry')">
          {{ retryText }}
        </el-button>
        <el-button v-if="showSnooze" @click="$emit('snooze')">继续等待</el-button>
        <el-button v-if="showPreview" :loading="previewLoading" plain @click="$emit('preview')">
          先看已生成预览
        </el-button>
        <el-button @click="$emit('cancel')">取消任务</el-button>
      </div>
    </div>
    <div v-else-if="waitingNote" class="outline-waiting-note">
      {{ waitingNote }}
    </div>

    <div v-if="pollErrorCount > 0" class="poll-warning">
      <el-icon><Warning /></el-icon>
      <span>{{ pollWarningText || `连接不稳定，已重试 ${pollErrorCount} 次` }}</span>
    </div>

    <slot name="extra" />

    <div class="stage-hints">
      <div
        v-for="(hint, index) in stageHints"
        :key="index"
        :class="['hint-item', { done: hint.done }]"
      >
        <el-icon><CircleCheck v-if="hint.done" /><Close v-else /></el-icon>
        <span>{{ hint.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { CircleCheck, Close, Loading, Warning } from '@element-plus/icons-vue'

defineEmits(['retry', 'cancel', 'snooze', 'preview'])

defineProps({
  percentage: { type: Number, default: 0 },
  currentStageName: { type: String, default: '' },
  facts: { type: Array, default: () => [] },
  summary: { type: Object, default: () => ({ title: '', desc: '' }) },
  recoveryVisible: { type: Boolean, default: false },
  recoveryTitle: { type: String, default: '等待时间偏长' },
  recoveryDesc: { type: String, default: '' },
  retryText: { type: String, default: '重新生成' },
  retryLoading: { type: Boolean, default: false },
  showSnooze: { type: Boolean, default: false },
  showPreview: { type: Boolean, default: false },
  previewLoading: { type: Boolean, default: false },
  waitingNote: { type: String, default: '' },
  pollErrorCount: { type: Number, default: 0 },
  pollWarningText: { type: String, default: '' },
  stageHints: { type: Array, default: () => [] }
})
</script>

<style scoped>
.stage-waiting-panel {
  min-width: 0;
}

.progress-bar-wrapper {
  margin-bottom: 18px;
}

.current-stage {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 18px;
  color: rgba(244, 246, 255, 0.86);
  font-size: 15px;
  font-weight: 820;
}

.stage-facts-panel {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}

.stage-fact-item {
  min-height: 96px;
  padding: 14px;
  border-radius: 0;
  border: 1px solid rgba(240, 241, 250, 0.1);
  background: rgba(240, 241, 250, 0.024);
  display: grid;
  align-content: space-between;
  gap: 8px;
}

.stage-fact-item span {
  color: rgba(240, 241, 250, 0.42);
  font-size: 12px;
  font-weight: 780;
}

.stage-fact-item strong {
  color: rgba(244, 246, 255, 0.9);
  font-size: 15px;
  line-height: 1.5;
}

.stage-interpretation {
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 0;
  background: rgba(122, 255, 180, 0.04);
  border: 1px solid rgba(122, 255, 180, 0.14);
}

.stage-interpretation strong {
  display: block;
  margin-bottom: 6px;
  color: #7affb4;
  font-size: 15px;
}

.stage-interpretation p {
  margin: 0;
  color: rgba(240, 241, 250, 0.62);
  line-height: 1.65;
}

.outline-recovery-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid rgba(250, 204, 21, 0.2);
  background: linear-gradient(135deg, rgba(113, 63, 18, 0.3), rgba(30, 41, 59, 0.82));
}

.recovery-copy {
  display: grid;
  gap: 8px;
}

.recovery-copy strong {
  color: #fde68a;
  font-size: 16px;
}

.recovery-copy span {
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.6;
}

.recovery-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.outline-waiting-note {
  margin-bottom: 14px;
  padding: 10px 12px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  background: rgba(240, 241, 250, 0.026);
  color: rgba(240, 241, 250, 0.54);
  text-align: left;
  font-size: 13px;
}

.poll-warning {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  margin-bottom: 16px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 8px;
  color: #e6a23c;
  font-size: 13px;
}

.poll-warning .el-icon {
  font-size: 16px;
}

.stage-hints {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 9px 10px;
  border: 1px solid rgba(240, 241, 250, 0.08);
  background: rgba(240, 241, 250, 0.018);
  font-size: 13px;
  color: rgba(240, 241, 250, 0.48);
}

.hint-item.done {
  border-color: rgba(122, 255, 180, 0.14);
  color: #7affb4;
}

:deep(.el-progress-bar__outer) {
  height: 8px !important;
  border-radius: 999px;
  background: rgba(240, 241, 250, 0.12);
}

:deep(.el-progress-bar__inner) {
  border-radius: 999px;
  background: linear-gradient(90deg, #23d9ff, #7affb4);
  box-shadow: 0 0 18px rgba(122, 255, 180, 0.18);
}

:deep(.el-progress__text) {
  color: rgba(244, 246, 255, 0.82);
  font-weight: 820;
}

@media (max-width: 960px) {
  .stage-facts-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .outline-recovery-card {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .stage-facts-panel,
  .stage-hints {
    grid-template-columns: 1fr;
  }
}
</style>
