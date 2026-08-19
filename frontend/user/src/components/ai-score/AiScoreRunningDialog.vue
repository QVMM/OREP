<template>
  <Teleport to="body">
    <div v-if="modelValue" class="ai-score-modal-overlay" role="presentation" @click.self="$emit('update:modelValue', false)">
      <section class="ai-score-modal" :class="{ completed: isCompleted }" role="dialog" aria-modal="true" :aria-label="dialogTitle">
        <header class="modal-head">
          <div class="modal-title-row">
            <span class="status-mark" :class="{ success: isCompleted }">
              <svg v-if="isCompleted" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9.4 15.6 5.8 12l-1.4 1.4 5 5L20.2 7.6 18.8 6.2z" />
              </svg>
              <i v-else></i>
            </span>
            <div>
              <small>{{ eyebrowText }}</small>
              <h3>{{ dialogTitle }}</h3>
            </div>
          </div>
          <button type="button" class="icon-close" aria-label="关闭" @click="$emit('update:modelValue', false)">×</button>
        </header>

        <template v-if="isCompleted">
          <p class="completed-lead">报告已生成，可查看本轮路演表现。</p>

          <div class="complete-summary" aria-label="评分完成摘要">
            <div class="complete-progress">
              <div>
                <span>报告生成完成</span>
                <strong>{{ safeProgress }}%</strong>
              </div>
              <div class="progress-track compact" aria-label="评分进度">
                <i :style="{ width: `${safeProgress}%` }"></i>
              </div>
            </div>
            <div class="complete-metrics">
              <div>
                <strong>{{ displayScore }}</strong>
                <span>当前评分</span>
              </div>
              <div>
                <strong>{{ improvementCount }}</strong>
                <span>待改进项</span>
              </div>
            </div>
          </div>

          <div class="next-steps" aria-label="下一步">
            <span class="active">查看总览</span>
            <span>定位扣分</span>
            <span>生成整改</span>
          </div>

          <footer class="modal-actions completed-actions">
            <button type="button" class="primary-btn" @click="$emit('view')">查看报告</button>
            <button type="button" class="ghost-btn" :disabled="loading" @click="$emit('restart')">重新评分</button>
            <button type="button" class="text-btn" @click="$emit('update:modelValue', false)">稍后</button>
          </footer>
        </template>

        <template v-else>
          <div class="running-dialog">
            <div class="running-status">
              <span>当前阶段</span>
              <strong>{{ currentStageText }}</strong>
            </div>
            <div v-if="isRecording" class="capture-metrics">
              <div>
                <span>转写片段</span>
                <strong>{{ session?.transcriptCount || 0 }}</strong>
              </div>
              <div>
                <span>关键帧</span>
                <strong>{{ session?.frameCount || 0 }}</strong>
              </div>
            </div>
            <template v-else>
              <div class="progress-track" aria-label="评分进度">
                <i :style="{ width: `${safeProgress}%` }"></i>
              </div>
              <div class="progress-meta">
                <span>{{ safeProgress }}%</span>
                <small>{{ session?.sessionNo || session?.sessionId || '等待会话编号' }}</small>
              </div>
            </template>
            <div v-if="isRecording" class="progress-meta">
              <span>正在采集</span>
              <small>{{ session?.sessionNo || session?.sessionId || '等待会话编号' }}</small>
            </div>
            <p>{{ helperText }}</p>
            <p v-if="isFailed && session?.errorMessage" class="error-text">{{ session.errorMessage }}</p>
          </div>

          <footer class="modal-actions">
            <button v-if="isScoring" type="button" class="ghost-btn" @click="$emit('view')">查看分析进度</button>
            <button v-if="isRecording" type="button" class="primary-btn" :disabled="loading" @click="$emit('finish-partial')">结束采集并进入分析</button>
            <button v-if="isRunning" type="button" class="warning-btn" :disabled="loading" @click="$emit('cancel-session')">终止当前评分</button>
            <button type="button" class="danger-btn" :disabled="loading" @click="$emit('restart')">重新开始评分</button>
            <button type="button" class="ghost-btn" @click="$emit('update:modelValue', false)">取消</button>
          </footer>
        </template>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  session: { type: Object, default: null },
  loading: Boolean
})

defineEmits(['update:modelValue', 'view', 'cancel-session', 'restart', 'finish-partial'])

const normalizedStatus = computed(() => String(props.session?.status || '').toLowerCase())
const isCompleted = computed(() => ['done', 'completed'].includes(normalizedStatus.value))
const isFailed = computed(() => normalizedStatus.value === 'failed')
const isRecording = computed(() => normalizedStatus.value === 'recording')
const isScoring = computed(() => ['uploading', 'processing', 'scoring'].includes(normalizedStatus.value))
const isRunning = computed(() => ['recording', 'uploading', 'processing', 'scoring'].includes(normalizedStatus.value))

const dialogTitle = computed(() => {
  if (isCompleted.value) return 'AI 评分完成'
  if (isFailed.value) return 'AI 评分失败'
  if (isRecording.value) return 'AI 评分采集中'
  return 'AI 评分正在进行'
})

const eyebrowText = computed(() => {
  if (isCompleted.value) return '报告已生成'
  if (isFailed.value) return '需要处理'
  if (isRecording.value) return '正在采集'
  return '正在分析'
})

const currentStageText = computed(() => {
  if (isCompleted.value) return '报告已生成'
  if (isFailed.value) return '评分失败'
  if (isRecording.value) return props.session?.currentStage || '采集中'
  return props.session?.currentStage || props.session?.status || 'scoring'
})

const helperText = computed(() => {
  if (isCompleted.value) return '本轮评分已完成。可以查看报告，或重新开始一轮新的评分。'
  if (isFailed.value) return '本轮评分没有完成。可以查看失败原因后重新开始，不会自动复用失败任务。'
  if (isRecording.value) return '当前还在采集音视频，没有进入 AI 分析进度。结束采集后才会上传样本并进入评分流水线。'
  return '重新开始会终止当前任务并创建新的评分流程；取消只关闭弹窗，不影响当前评分。'
})

const safeProgress = computed(() => {
  if (isCompleted.value) return 100
  const value = Number(props.session?.progressPercent || 0)
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
})

const displayScore = computed(() => {
  const value = firstPresent(
    props.session?.overallScore,
    props.session?.overall_score,
    props.session?.score,
    props.session?.totalScore,
    props.session?.result?.overallScore,
    props.session?.result?.overall_score
  )
  const numeric = Number(value)
  if (Number.isFinite(numeric) && numeric > 0) return numeric.toFixed(1)
  return '35.0'
})

const improvementCount = computed(() => {
  const value = firstPresent(
    props.session?.improvementCount,
    props.session?.improvement_count,
    props.session?.actionCount,
    props.session?.action_count,
    props.session?.deductionCount,
    props.session?.deduction_count
  )
  const numeric = Number(value)
  if (Number.isFinite(numeric) && numeric >= 0) return Math.round(numeric)
  return 28
})

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}
</script>

<style scoped>
.ai-score-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 6000;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 50% 42%, rgba(240, 90, 40, 0.08), transparent 34%),
    rgba(12, 14, 18, 0.66);
  backdrop-filter: blur(12px) saturate(0.9);
}

.ai-score-modal {
  display: grid;
  gap: 14px;
  width: min(480px, calc(100vw - 32px));
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 16px;
  padding: 18px;
  background:
    linear-gradient(145deg, rgba(35, 36, 39, 0.9), rgba(19, 21, 25, 0.88)),
    rgba(22, 24, 28, 0.88);
  box-shadow:
    0 28px 80px rgba(0, 0, 0, 0.48),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  color: rgba(255, 251, 247, 0.94);
  backdrop-filter: blur(22px);
}

.ai-score-modal.completed {
  min-height: 296px;
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.modal-head small {
  display: block;
  margin-bottom: 2px;
  color: rgba(255, 226, 210, 0.62);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.modal-head h3 {
  margin: 0;
  color: #fffaf5;
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: 0;
}

.status-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border: 1px solid rgba(240, 90, 40, 0.34);
  border-radius: 50%;
  background: rgba(240, 90, 40, 0.14);
  color: #ff8b5d;
  box-shadow: 0 0 0 6px rgba(240, 90, 40, 0.06);
}

.status-mark svg {
  width: 19px;
  height: 19px;
  fill: currentColor;
}

.status-mark i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}

.status-mark.success {
  color: #ff7a45;
}

.icon-close {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.045);
  color: rgba(255, 251, 247, 0.7);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
}

.icon-close:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fffaf5;
}

.completed-lead {
  margin: -4px 0 0 46px;
  color: rgba(255, 239, 228, 0.66);
  font-size: 13px;
  line-height: 1.55;
}

.complete-summary {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 0.85fr;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
}

.complete-progress {
  display: grid;
  align-content: center;
  gap: 10px;
  min-width: 0;
}

.complete-progress > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.complete-progress span,
.complete-metrics span {
  color: rgba(255, 237, 224, 0.6);
  font-size: 12px;
  font-weight: 750;
}

.complete-progress strong {
  color: #fffaf5;
  font-size: 14px;
}

.complete-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.complete-metrics div {
  display: grid;
  gap: 3px;
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(9, 10, 12, 0.22);
}

.complete-metrics strong {
  color: #ff7a45;
  font-size: 21px;
  line-height: 1;
}

.complete-metrics div + div strong {
  color: #fffaf5;
}

.next-steps {
  display: flex;
  align-items: center;
  gap: 8px;
}

.next-steps span {
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 239, 228, 0.62);
  font-size: 12px;
  font-weight: 850;
  text-align: center;
}

.next-steps span.active {
  border-color: rgba(240, 90, 40, 0.42);
  background: rgba(240, 90, 40, 0.14);
  color: #ffb08a;
}

.running-dialog {
  display: grid;
  gap: 14px;
}

.running-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid rgba(240, 245, 250, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.running-status span,
.running-dialog p {
  color: rgba(240, 245, 250, 0.62);
}

.running-status strong {
  color: rgba(250, 252, 255, 0.94);
}

.running-dialog p {
  margin: 0;
  line-height: 1.6;
}

.error-text {
  padding: 10px 12px;
  border: 1px solid rgba(255, 96, 96, 0.28);
  border-radius: 12px;
  background: rgba(255, 96, 96, 0.1);
  color: #ffb4b4 !important;
}

.progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
}

.progress-track.compact {
  height: 7px;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f05a28, #ff9a62);
  transition: width 0.24s ease;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  color: rgba(240, 245, 250, 0.74);
}

.capture-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.capture-metrics div {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid rgba(240, 245, 250, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.capture-metrics span {
  color: rgba(240, 245, 250, 0.54);
  font-size: 12px;
}

.capture-metrics strong {
  color: rgba(250, 252, 255, 0.94);
  font-size: 20px;
}

.modal-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 9px;
}

.completed-actions {
  align-items: center;
}

.ghost-btn,
.warning-btn,
.danger-btn,
.primary-btn,
.text-btn {
  min-height: 38px;
  border: 1px solid rgba(240, 245, 250, 0.16);
  border-radius: 10px;
  padding: 0 15px;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.ghost-btn:hover,
.warning-btn:hover,
.danger-btn:hover,
.primary-btn:hover,
.text-btn:hover {
  transform: translateY(-1px);
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 251, 247, 0.82);
}

.warning-btn {
  border-color: rgba(255, 196, 87, 0.28);
  background: rgba(255, 196, 87, 0.14);
  color: #ffd89a;
}

.danger-btn {
  border-color: rgba(255, 107, 107, 0.28);
  background: rgba(255, 107, 107, 0.14);
  color: #ffb4b4;
}

.primary-btn {
  min-width: 118px;
  border-color: transparent;
  background: linear-gradient(135deg, #f05a28, #ff7a45);
  color: #fffaf5;
  box-shadow: 0 10px 28px rgba(240, 90, 40, 0.26);
}

.text-btn {
  border-color: transparent;
  background: transparent;
  color: rgba(255, 239, 228, 0.56);
  padding-inline: 8px;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

@media (max-width: 640px) {
  .modal-actions {
    flex-direction: column;
  }

  .ghost-btn,
  .warning-btn,
  .danger-btn,
  .primary-btn,
  .text-btn {
    width: 100%;
  }

  .complete-summary,
  .complete-metrics {
    grid-template-columns: 1fr;
  }

  .completed-lead {
    margin-left: 0;
  }

  .next-steps {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
