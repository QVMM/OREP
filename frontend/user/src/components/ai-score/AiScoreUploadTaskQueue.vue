<template>
  <section
    class="upload-task-queue"
    aria-labelledby="upload-task-queue-title"
    :aria-busy="loading || syncing ? 'true' : 'false'"
  >
    <header class="queue-header">
      <div>
        <h2 id="upload-task-queue-title">评分任务</h2>
        <p>分析任务会持续保留，刷新或重新登录后仍可查看。</p>
      </div>
      <BaseButton type="secondary" :loading="loading || syncing" @click="emit('reload')">
        刷新任务
      </BaseButton>
    </header>

    <span class="sync-status" aria-live="polite">{{ syncing ? '正在同步任务' : '' }}</span>

    <div
      v-if="loading && !tasks.length"
      class="queue-skeleton"
      role="status"
      aria-live="polite"
      aria-label="正在读取评分任务"
    >
      <div v-for="index in 3" :key="index" class="skeleton-row">
        <i></i><i></i><i></i>
      </div>
    </div>

    <div v-else-if="error && !tasks.length" class="queue-feedback queue-error" role="alert">
      <div>
        <strong>任务暂时无法读取</strong>
        <p>{{ error }}</p>
      </div>
      <BaseButton type="secondary" @click="emit('reload')">重新加载</BaseButton>
    </div>

    <div v-else-if="!tasks.length" class="queue-feedback" role="status">
      <strong>还没有评分任务</strong>
      <p>上传路演视频后，分析进度和评分报告会显示在这里。</p>
    </div>

    <div v-else class="task-list">
      <article v-for="task in tasks" :key="task.sessionId" class="task-row">
        <div class="task-summary">
          <strong>{{ task.fileName || task.sessionNo || '未命名评分任务' }}</strong>
          <span>{{ task.teamName || '未关联团队' }} · {{ task.trackName || '未选择赛道' }}</span>
          <small>{{ formatTime(task.updatedAt || task.createdAt) }}</small>
        </div>

        <div class="task-progress">
          <div class="task-progress-head">
            <span class="status-label" :class="statusClass(task)">{{ statusLabel(task) }}</span>
            <b v-if="showsProgress(task)">{{ progressValue(task) }}%</b>
          </div>
          <div
            v-if="showsProgress(task)"
            class="task-progress-track"
            role="progressbar"
            :aria-label="`${task.fileName || task.sessionNo || '评分任务'} 分析进度`"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="progressValue(task)"
          >
            <i :style="{ width: `${progressValue(task)}%` }"></i>
          </div>
          <small v-if="normalizedStatus(task) === 'failed'" class="task-error">
            {{ task.errorMessage || '任务处理失败，请重新上传。' }}
          </small>
        </div>

        <div class="task-actions">
          <BaseButton
            v-if="normalizedStatus(task) === 'completed'"
            type="secondary"
            :to="`/ai-score/report/${task.sessionId}`"
          >
            查看报告
          </BaseButton>
          <BaseButton
            v-else-if="normalizedStatus(task) === 'failed'"
            type="secondary"
            :disabled="actionsDisabled"
            @click="emit('retry', task)"
          >
            重新上传
          </BaseButton>
          <span v-else-if="normalizedStatus(task) === 'cancelled'" class="terminal-note">已取消</span>
          <span v-else class="active-note">系统处理中</span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import BaseButton from '../base/BaseButton.vue'

defineProps({
  tasks: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  syncing: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  actionsDisabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['reload', 'retry'])

const STAGE_LABELS = {
  created: '等待上传',
  uploaded: '等待分析',
  queued: '排队中',
  audio_extracting: '音频处理中',
  asr_processing: '语音识别中',
  frame_extracting: '画面提取中',
  ocr_processing: '文字识别中',
  evidence_building: '证据整理中',
  model_scoring: '模型评分中',
  rule_calibrating: '评分校准中',
  report_generating: '报告生成中'
}

function normalizedStatus(task = {}) {
  return String(task.status || '').trim().toLowerCase()
}

function normalizedStage(task = {}) {
  return String(task.currentStage || '').trim().toLowerCase()
}

function progressValue(task = {}) {
  return Math.max(0, Math.min(100, Number(task.progressPercent) || 0))
}

function showsProgress(task = {}) {
  const status = normalizedStatus(task)
  const stage = normalizedStage(task)
  return !['created', 'uploaded', 'queued'].includes(status)
    && !['created', 'uploaded', 'queued'].includes(stage)
}

function statusLabel(task = {}) {
  const status = normalizedStatus(task)
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '处理失败'
  if (status === 'cancelled') return '已取消'
  return STAGE_LABELS[normalizedStage(task)] || '分析处理中'
}

function statusClass(task = {}) {
  const status = normalizedStatus(task)
  if (status === 'completed') return 'is-success'
  if (status === 'failed') return 'is-danger'
  if (status === 'cancelled') return 'is-neutral'
  return 'is-active'
}

function formatTime(value) {
  if (!value) return '时间待同步'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)
}
</script>

<style scoped>
.upload-task-queue {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  color: var(--ds-ink-2);
  font-family: var(--ds-font-sans);
}

.queue-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ds-space-5);
  padding: var(--ds-space-5) var(--ds-space-6);
  border-bottom: 1px solid var(--ds-line);
}

.queue-header h2 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-h2);
  font-weight: var(--ds-weight-bold);
  line-height: var(--ds-leading-title);
}

.queue-header p,
.queue-feedback p,
.queue-error p {
  margin: var(--ds-space-1) 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: var(--ds-leading-body);
}

.sync-status {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.task-list {
  padding: 0 var(--ds-space-6);
}

.task-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) minmax(260px, 1fr) auto;
  align-items: center;
  gap: var(--ds-space-6);
  min-width: 0;
  padding: var(--ds-space-5) 0;
  border-bottom: 1px solid var(--ds-line);
}

.task-row:last-child {
  border-bottom: 0;
}

.task-summary,
.task-progress {
  display: grid;
  min-width: 0;
  gap: var(--ds-space-1);
}

.task-summary strong {
  overflow-wrap: anywhere;
  color: var(--ds-ink);
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-bold);
}

.task-summary span,
.task-summary small,
.task-progress small {
  overflow-wrap: anywhere;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: var(--ds-leading-body);
}

.task-summary small {
  color: var(--ds-faint);
  font-size: var(--ds-text-micro);
}

.task-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-3);
}

.task-progress-head b {
  color: var(--ds-ink-2);
  font-family: var(--ds-font-num);
  font-size: var(--ds-text-caption);
}

.status-label {
  display: inline-flex;
  width: fit-content;
  border-radius: var(--ds-radius-pill);
  padding: var(--ds-space-1) var(--ds-space-2);
  font-size: var(--ds-text-micro);
  font-weight: var(--ds-weight-bold);
}

.status-label.is-active {
  color: var(--ds-status-info-fg);
  background: var(--ds-status-info-bg);
}

.status-label.is-success {
  color: var(--ds-status-success-fg);
  background: var(--ds-status-success-bg);
}

.status-label.is-danger {
  color: var(--ds-status-danger-fg);
  background: var(--ds-status-danger-bg);
}

.status-label.is-neutral {
  color: var(--ds-status-neutral-fg);
  background: var(--ds-status-neutral-bg);
}

.task-progress-track {
  width: 100%;
  height: 4px;
  overflow: hidden;
  border-radius: var(--ds-radius-pill);
  background: var(--ds-line-strong);
}

.task-progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ds-orange-action);
  transition: width var(--ds-transition);
}

.task-progress .task-error {
  color: var(--ds-status-danger-fg);
}

.task-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 104px;
}

.active-note,
.terminal-note {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-semibold);
}

.terminal-note {
  color: var(--ds-status-neutral-fg);
}

.queue-feedback {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-5);
  padding: var(--ds-space-6);
}

.queue-feedback strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-body-sm);
}

.queue-error strong {
  color: var(--ds-status-danger-fg);
}

.queue-skeleton {
  padding: 0 var(--ds-space-6);
}

.skeleton-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 104px;
  align-items: center;
  gap: var(--ds-space-6);
  padding: var(--ds-space-5) 0;
  border-bottom: 1px solid var(--ds-line);
}

.skeleton-row:last-child {
  border-bottom: 0;
}

.skeleton-row i {
  display: block;
  height: var(--ds-space-3);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-status-neutral-bg);
}

@media (max-width: 720px) {
  .queue-header {
    align-items: stretch;
    flex-direction: column;
    padding: var(--ds-space-4);
  }

  .queue-header :deep(.base-button) {
    align-self: flex-start;
  }

  .task-list,
  .queue-skeleton {
    padding: 0 var(--ds-space-4);
  }

  .task-row,
  .skeleton-row {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--ds-space-4);
  }

  .task-actions {
    justify-content: flex-start;
  }

  .queue-feedback {
    align-items: flex-start;
    flex-direction: column;
    padding: var(--ds-space-5) var(--ds-space-4);
  }
}
</style>
