<template>
  <div class="video-score-page">
    <header class="upload-page-head">
      <div>
        <h1>上传评分</h1>
        <p>上传完整路演视频与可选佐证材料，系统会持续更新分析任务。</p>
      </div>
      <BaseButton type="secondary" to="/online-meeting?tab=reports">返回评分报告</BaseButton>
    </header>

    <main ref="uploadCard" class="upload-main-card">
      <div class="section-title">
        <h2>上传材料</h2>
        <p>确认项目团队与赛道后，选择需要评分的路演视频。</p>
      </div>

      <VideoScoreUploadForm
        :retry-context="retryContext"
        @status-change="handleStatusChange"
        @uploaded="handleUploaded"
      />

      <div v-if="isLocalUploadVisible" class="upload-transfer">
        <div class="transfer-summary">
          <strong>{{ uploadMeta.stage || '本地文件待上传' }}</strong>
          <span>{{ uploadProgress }}%</span>
        </div>
        <div
          class="transfer-track"
          role="progressbar"
          aria-label="本地文件上传进度"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="uploadProgress"
        >
          <i :style="{ width: `${uploadProgress}%` }"></i>
        </div>
        <div class="transfer-metrics">
          <span>已传 {{ uploadedBytesText }} / {{ totalBytesText }}</span>
          <span>速度 {{ uploadSpeedText }}</span>
          <span>剩余 {{ remainingText }}</span>
        </div>
      </div>
    </main>

    <AiScoreUploadTaskQueue
      :tasks="tasks"
      :loading="loading"
      :syncing="syncing"
      :error="queueError"
      :actions-disabled="isUploadBusy"
      @reload="refreshUploadQueue()"
      @retry="retryTask"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AiScoreUploadTaskQueue from '../components/ai-score/AiScoreUploadTaskQueue.vue'
import VideoScoreUploadForm from '../components/ai-score/VideoScoreUploadForm.vue'
import BaseButton from '../components/base/BaseButton.vue'
import { useAiScoreUploadQueue } from '../composables/useAiScoreUploadQueue'

const {
  tasks,
  loading,
  syncing,
  error: queueError,
  refresh: refreshUploadQueue,
  mergeUploadedSession
} = useAiScoreUploadQueue()

const uploadCard = ref(null)
const retryContext = ref(null)
const uploadStatus = ref('idle')
const uploadProgress = ref(0)
const uploadMeta = ref({})
const isUploadBusy = computed(() => ['preparing', 'uploading', 'creating', 'preprocessing'].includes(uploadStatus.value))

const hasUploadBytes = computed(() => Number(uploadMeta.value.totalBytes || 0) > 0)
const isLocalUploadVisible = computed(() => uploadStatus.value === 'uploading' && hasUploadBytes.value)
const uploadedBytesText = computed(() => formatBytes(uploadMeta.value.loadedBytes))
const totalBytesText = computed(() => formatBytes(uploadMeta.value.totalBytes))
const uploadSpeedText = computed(() => {
  const speed = Number(uploadMeta.value.speedBytesPerSecond || 0)
  return speed > 0 ? `${formatBytes(speed)}/s` : '计算中'
})
const remainingText = computed(() => {
  const remaining = uploadMeta.value.remainingSeconds
  return Number.isFinite(Number(remaining)) && Number(remaining) >= 0
    ? formatDuration(remaining)
    : '计算中'
})

function handleStatusChange(event = {}) {
  uploadStatus.value = event.status || uploadStatus.value
  uploadProgress.value = Math.max(0, Math.min(100, Number(event.progress ?? uploadProgress.value) || 0))
  const telemetryFields = [
    'stage',
    'loadedBytes',
    'totalBytes',
    'speedBytesPerSecond',
    'elapsedSeconds',
    'remainingSeconds'
  ]
  const hasTransferTelemetry = telemetryFields
    .filter(field => field !== 'stage')
    .some(field => Object.prototype.hasOwnProperty.call(event, field))
  const shouldResetMeta = event.status === 'idle'
    || event.status === 'selected'
    || (event.status === 'failed' && !hasTransferTelemetry)
  const nextMeta = shouldResetMeta ? {} : { ...uploadMeta.value }
  for (const field of telemetryFields) {
    if (Object.prototype.hasOwnProperty.call(event, field)) {
      nextMeta[field] = event[field]
    }
  }
  uploadMeta.value = {
    ...nextMeta
  }
}

function handleUploaded(session) {
  uploadStatus.value = 'completed'
  uploadProgress.value = 0
  uploadMeta.value = {}
  mergeUploadedSession(session)
  void refreshUploadQueue({ silent: true })
  ElMessage.success('上传视频评分会话已创建')
}

function retryTask(task) {
  if (isUploadBusy.value) return
  uploadStatus.value = 'idle'
  uploadProgress.value = 0
  uploadMeta.value = {}
  retryContext.value = {
    ...task,
    retryKey: `${task.sessionId}-${Date.now()}`
  }
  nextTick(() => {
    uploadCard.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function formatBytes(bytes) {
  const value = Number(bytes || 0)
  if (!Number.isFinite(value) || value <= 0) return '0 MB'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = value
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size >= 10 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`
}

function formatDuration(seconds) {
  const value = Math.max(0, Math.round(Number(seconds || 0)))
  const minutes = Math.floor(value / 60)
  const restSeconds = value % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const restMinutes = minutes % 60
    return `${hours}:${String(restMinutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`
  }
  return `${String(minutes).padStart(2, '0')}:${String(restSeconds).padStart(2, '0')}`
}
</script>

<style scoped>
.video-score-page {
  box-sizing: border-box;
  width: 100%;
  margin: 0;
  padding: 0;
  background: transparent;
  color: var(--ds-ink-2);
  font-family: var(--ds-font-sans);
}

.upload-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ds-space-6);
  margin-bottom: var(--ds-space-5);
}

.upload-page-head h1 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-h1);
  font-weight: var(--ds-weight-bold);
  line-height: var(--ds-leading-title);
}

.upload-page-head p,
.section-title p {
  margin: var(--ds-space-1) 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: var(--ds-leading-body);
}

.upload-main-card {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  padding: var(--ds-space-6);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.section-title {
  margin-bottom: var(--ds-space-5);
}

.section-title h2 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-h2);
  font-weight: var(--ds-weight-bold);
  line-height: var(--ds-leading-title);
}

.upload-task-queue {
  margin-top: var(--ds-space-5);
}

.upload-transfer {
  display: grid;
  gap: var(--ds-space-2);
  margin-top: var(--ds-space-5);
  padding-top: var(--ds-space-4);
  border-top: 1px solid var(--ds-line);
}

.transfer-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-3);
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
}

.transfer-summary strong {
  overflow-wrap: anywhere;
}

.transfer-summary span {
  flex: 0 0 auto;
  color: var(--ds-orange-deep);
  font-family: var(--ds-font-num);
  font-weight: var(--ds-weight-bold);
}

.upload-transfer.completed .transfer-summary strong {
  color: var(--ds-status-success-fg);
}

.upload-transfer.failed .transfer-summary strong {
  color: var(--ds-status-danger-fg);
}

.transfer-track {
  width: 100%;
  height: 4px;
  overflow: hidden;
  border-radius: var(--ds-radius-pill);
  background: var(--ds-line-strong);
}

.transfer-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ds-orange-action);
  transition: width var(--ds-transition);
}

.upload-transfer.completed .transfer-track i {
  background: var(--ds-green);
}

.upload-transfer.failed .transfer-track i {
  background: var(--ds-red);
}

.transfer-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2) var(--ds-space-5);
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  line-height: var(--ds-leading-body);
}

@media (max-width: 720px) {
  .upload-page-head {
    align-items: stretch;
    flex-direction: column;
  }

  .upload-page-head :deep(.base-button) {
    align-self: flex-start;
  }

  .upload-main-card {
    padding: var(--ds-space-4);
  }
}
</style>
