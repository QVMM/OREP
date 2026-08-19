<template>
  <form class="video-score-form" @submit.prevent="submit">
    <div class="form-grid">
      <label>
        <span>项目团队</span>
        <select v-model="form.teamId" :disabled="submitting || teamLoading || !teams.length">
          <option value="" disabled>{{ teamSelectPlaceholder }}</option>
          <option v-for="team in teams" :key="team.id" :value="String(team.id)">
            {{ team.name }}{{ team.myRoleInTeam ? ` · ${team.myRoleInTeam}` : '' }}
          </option>
        </select>
      </label>
      <label>
        <span>赛道</span>
        <select v-model="form.trackName" :disabled="submitting">
          <option v-for="trackName in trackNames" :key="trackName" :value="trackName">
            {{ trackName }}
          </option>
        </select>
      </label>
    </div>

    <div class="file-list">
      <div class="file-row">
        <div>
          <strong>路演视频</strong>
          <span>{{ videoFile?.name || '选择 MP4 / WebM / MOV' }}</span>
          <small>{{ videoSizeText || '最大 5GB' }}</small>
        </div>
        <input ref="videoInput" type="file" :disabled="submitting" accept=".mp4,.webm,.mov,video/mp4,video/webm,video/quicktime" @change="pickVideo" />
        <BaseButton type="secondary" :disabled="submitting" @click="videoInput?.click()">选择视频</BaseButton>
      </div>

      <div class="file-row">
        <div>
          <strong>佐证材料</strong>
          <span>{{ materialSummary }}</span>
          <small>{{ materialSizeText || '单个最大 200MB，合计最大 1GB' }}</small>
        </div>
        <input ref="materialInput" type="file" :disabled="submitting" multiple accept=".pdf,.ppt,.pptx,.doc,.docx" @change="pickMaterials" />
        <BaseButton type="secondary" :disabled="submitting" @click="materialInput?.click()">选择材料</BaseButton>
      </div>
    </div>

    <div v-if="largeVideoHint" class="form-hint">{{ largeVideoHint }}</div>
    <div v-if="retryHint" class="form-hint retry-hint" role="status">{{ retryHint }}</div>

    <section class="preference-section">
      <button
        class="preference-toggle"
        type="button"
        :disabled="submitting"
        :aria-expanded="preferenceExpanded ? 'true' : 'false'"
        aria-controls="score-preferences"
        @click="preferenceExpanded = !preferenceExpanded"
      >
        <span>更多评分偏好</span>
        <small>{{ preferenceExpanded ? '收起' : '展开' }}</small>
      </button>
      <div v-show="preferenceExpanded" id="score-preferences" class="option-row">
        <label>
          <input v-model="form.useHistoryMemory" type="checkbox" :disabled="submitting" />
          <span>引用历史评分记忆</span>
        </label>
      </div>
    </section>

    <div v-if="error" class="form-error" role="alert">{{ error }}</div>

    <div class="submit-row">
      <BaseButton native-type="submit" type="primary" :loading="submitting">
        开始上传评分
      </BaseButton>
    </div>
  </form>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BaseButton from '../base/BaseButton.vue'
import { uploadAiScoreSession } from '../../utils/aiScoreUpload'
import request from '../../utils/request'
import { AI_SCORE_TRACK_NAMES } from '../../utils/trackCatalog'

const MAX_VIDEO_BYTES = 5 * 1024 * 1024 * 1024
const MAX_MATERIAL_BYTES = 200 * 1024 * 1024
const MAX_TOTAL_MATERIAL_BYTES = 1 * 1024 * 1024 * 1024
const LARGE_VIDEO_BYTES = 500 * 1024 * 1024
const props = defineProps({
  retryContext: {
    type: Object,
    default: null
  }
})
const emit = defineEmits(['uploaded', 'status-change'])
const route = useRoute()

const form = reactive({
  teamId: '',
  trackName: '新一代信息技术赛道',
  useHistoryMemory: true,
  juryEnabled: false
})

const teams = ref([])
const teamLoading = ref(false)
const trackNames = AI_SCORE_TRACK_NAMES
const videoInput = ref(null)
const materialInput = ref(null)
const videoFile = ref(null)
const materials = ref([])
const submitting = ref(false)
const preferenceExpanded = ref(false)
const retryHint = ref('')
const error = ref('')
let retryApplied = false
let uploadStartedAt = 0
let lastProgressAt = 0
let lastLoadedBytes = 0
let smoothedSpeedBytes = 0

const teamSelectPlaceholder = computed(() => {
  if (teamLoading.value) return '正在读取项目团队'
  return teams.value.length ? '请选择项目团队' : '暂无可用项目团队'
})
const materialSummary = computed(() => {
  if (!materials.value.length) return '可选 PDF / PPT / Word'
  if (materials.value.length === 1) return materials.value[0].name
  return `${materials.value.length} 个文件`
})
const videoSizeText = computed(() => videoFile.value ? formatBytes(videoFile.value.size) : '')
const materialSizeText = computed(() => {
  const total = materials.value.reduce((sum, file) => sum + Number(file.size || 0), 0)
  return total ? `合计 ${formatBytes(total)}` : ''
})
const largeVideoHint = computed(() => {
  if (!videoFile.value) return ''
  if (videoFile.value.size >= LARGE_VIDEO_BYTES) return '当前视频较大，上传和服务端登记可能需要较长时间，请勿关闭页面。'
  return ''
})

watch(
  () => props.retryContext,
  (context) => {
    if (!context) return
    retryApplied = true
    form.teamId = String(context.teamId ?? context.projectTeamId ?? '')
    form.trackName = context.trackName || context.track || form.trackName
    form.useHistoryMemory = Boolean(context.useHistoryMemory)
    form.juryEnabled = false
    preferenceExpanded.value = true
    videoFile.value = null
    if (videoInput.value) videoInput.value.value = ''
    materials.value = []
    if (materialInput.value) materialInput.value.value = ''
    retryHint.value = '请重新选择本地视频文件'
    error.value = ''
    emit('status-change', {
      status: 'idle',
      progress: 0,
      stage: '等待重新选择视频',
      totalBytes: 0,
      loadedBytes: 0
    })
  }
)

function pickVideo(event) {
  error.value = ''
  retryHint.value = ''
  const selected = event.target.files?.[0] || null
  if (selected && selected.size > MAX_VIDEO_BYTES) {
    videoFile.value = null
    event.target.value = ''
    error.value = '路演视频最大5GB，请压缩后上传'
    emit('status-change', emptyFailedTelemetry())
    return
  }
  videoFile.value = selected
  if (videoFile.value) {
    resetUploadTelemetry()
    emit('status-change', {
      status: 'selected',
      progress: 0,
      stage: '文件已选择',
      totalBytes: 0,
      loadedBytes: 0
    })
  }
}

function pickMaterials(event) {
  error.value = ''
  const selected = Array.from(event.target.files || [])
  const limitError = materialLimitError(selected)
  if (limitError) {
    materials.value = []
    event.target.value = ''
    error.value = limitError
    emit('status-change', emptyFailedTelemetry())
    return
  }
  materials.value = selected
  emit('status-change', {
    status: videoFile.value ? 'selected' : 'idle',
    progress: 0,
    stage: videoFile.value ? '文件已选择' : '等待上传',
    totalBytes: 0,
    loadedBytes: 0
  })
}

function appendIfPresent(formData, key, value) {
  if (value !== null && value !== undefined && String(value).trim() !== '') {
    formData.append(key, value)
  }
}

function materialLimitError(files) {
  const oversized = files.find((file) => file.size > MAX_MATERIAL_BYTES)
  if (oversized) return `单个佐证材料最大200MB：${oversized.name}`
  const totalBytes = files.reduce((sum, file) => sum + Number(file.size || 0), 0)
  if (totalBytes > MAX_TOTAL_MATERIAL_BYTES) return '佐证材料合计最大1GB，请减少文件后重试'
  return ''
}

async function submit() {
  error.value = ''
  if (!form.teamId) {
    error.value = '请选择项目团队'
    emit('status-change', { status: 'failed', progress: 0 })
    return
  }
  if (!videoFile.value) {
    error.value = '请先选择路演视频'
    emit('status-change', { status: 'failed', progress: 0 })
    return
  }
  if (videoFile.value.size > MAX_VIDEO_BYTES) {
    error.value = '路演视频最大5GB，请压缩后上传'
    emit('status-change', emptyFailedTelemetry())
    return
  }
  const materialError = materialLimitError(materials.value)
  if (materialError) {
    error.value = materialError
    emit('status-change', emptyFailedTelemetry())
    return
  }
  if (!form.trackName.trim()) {
    error.value = '请选择赛道'
    emit('status-change', { status: 'failed', progress: 0 })
    return
  }

  const selectedVideo = videoFile.value
  const selectedMaterials = [...materials.value]
  const formData = new FormData()
  appendIfPresent(formData, 'projectId', form.teamId)
  appendIfPresent(formData, 'teamId', form.teamId)
  formData.append('trackName', form.trackName)
  formData.append('useHistoryMemory', String(form.useHistoryMemory))
  formData.append('juryEnabled', 'false')
  formData.append('video', selectedVideo)
  selectedMaterials.forEach((file) => formData.append('materials', file))

  submitting.value = true
  try {
    resetUploadTelemetry()
    emit('status-change', {
      status: 'preparing',
      progress: 0,
      stage: '校验登录状态并准备上传',
      totalBytes: 0,
      loadedBytes: 0,
      elapsedSeconds: 0
    })
    const session = await uploadAiScoreSession(formData, {
      onUploadProgress(progressEvent) {
        emit('status-change', buildUploadTelemetry(
          progressEvent,
          '正在上传视频到服务器',
          selectedVideo.size
        ))
      }
    })
    emit('status-change', {
      status: 'creating',
      progress: 0,
      stage: '正在创建评分任务',
      totalBytes: 0,
      loadedBytes: 0
    })
    emit('uploaded', session)
  } catch (err) {
    error.value = uploadErrorMessage(err)
    emit('status-change', {
      status: 'failed',
      progress: 0,
      stage: '上传失败',
      totalBytes: selectedVideo.size,
      loadedBytes: Math.min(lastLoadedBytes, selectedVideo.size),
      speedBytesPerSecond: smoothedSpeedBytes,
      elapsedSeconds: elapsedSeconds()
    })
  } finally {
    submitting.value = false
  }
}

async function loadTeams() {
  teamLoading.value = true
  try {
    const res = await request.get('/api/project-teams/my')
    teams.value = Array.isArray(res.data) ? res.data : []
    if (!retryApplied) {
      const preferredTeamId = String(route.query.teamId || '')
      const preferred = teams.value.find((team) => String(team.id) === preferredTeamId)
      form.teamId = String(preferred?.id || teams.value[0]?.id || '')
    }
  } catch (err) {
    teams.value = []
    error.value = err?.message || '项目团队读取失败'
  } finally {
    teamLoading.value = false
  }
}

onMounted(loadTeams)

function uploadErrorMessage(err) {
  if (err?.response?.status === 413) {
    return '上传内容超过限制：视频最大5GB，单个材料最大200MB'
  }
  return err?.message || '上传失败'
}

function emptyFailedTelemetry() {
  return {
    status: 'failed',
    progress: 0,
    totalBytes: 0,
    loadedBytes: 0,
    speedBytesPerSecond: 0,
    elapsedSeconds: 0,
    remainingSeconds: null
  }
}

function resetUploadTelemetry() {
  uploadStartedAt = Date.now()
  lastProgressAt = uploadStartedAt
  lastLoadedBytes = 0
  smoothedSpeedBytes = 0
}

function elapsedSeconds() {
  if (!uploadStartedAt) return 0
  return Math.max(0, Math.round((Date.now() - uploadStartedAt) / 1000))
}

function buildUploadTelemetry(progressEvent, stage, selectedVideoSize) {
  const now = Date.now()
  if (!uploadStartedAt) resetUploadTelemetry()
  const loaded = Number(progressEvent.loaded || 0)
  const total = Number(progressEvent.total || selectedVideoSize || 0)
  const deltaBytes = Math.max(0, loaded - lastLoadedBytes)
  const deltaSeconds = Math.max(0.001, (now - lastProgressAt) / 1000)
  const instantSpeed = deltaBytes / deltaSeconds
  if (instantSpeed > 0) {
    smoothedSpeedBytes = smoothedSpeedBytes
      ? smoothedSpeedBytes * 0.72 + instantSpeed * 0.28
      : instantSpeed
  }
  lastLoadedBytes = loaded
  lastProgressAt = now

  const uploadRatio = total > 0 ? Math.max(0, Math.min(1, loaded / total)) : 0
  const remainingBytes = total > 0 ? Math.max(0, total - loaded) : 0
  const remainingSeconds = smoothedSpeedBytes > 0 && remainingBytes > 0
    ? Math.round(remainingBytes / smoothedSpeedBytes)
    : null

  return {
    status: 'uploading',
    progress: Math.round(uploadRatio * 100),
    stage,
    loadedBytes: loaded,
    totalBytes: total,
    speedBytesPerSecond: smoothedSpeedBytes,
    elapsedSeconds: elapsedSeconds(),
    remainingSeconds
  }
}

function formatBytes(bytes) {
  const value = Number(bytes || 0)
  if (!Number.isFinite(value) || value <= 0) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let size = value
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size >= 10 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`
}
</script>

<style scoped>
.video-score-form {
  display: grid;
  gap: var(--ds-space-5);
  color: var(--ds-ink-2);
  font-family: var(--ds-font-sans);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ds-space-4);
}

.form-grid label {
  display: grid;
  gap: var(--ds-space-2);
  min-width: 0;
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-semibold);
}

.form-grid select {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  height: var(--ds-input-height);
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  padding: 0 var(--ds-input-padding-x);
  background: var(--ds-input-bg);
  color: var(--ds-ink);
  font: inherit;
  outline: none;
}

.form-grid select:hover {
  border-color: var(--ds-input-border-hover);
}

.form-grid select:focus-visible {
  border-color: var(--ds-input-focus-border);
  box-shadow: var(--ds-input-focus-ring);
}

.form-grid select:disabled {
  color: var(--ds-input-disabled-fg);
  background: var(--ds-input-disabled-bg);
}

.file-list {
  border-top: 1px solid var(--ds-line);
  border-bottom: 1px solid var(--ds-line);
}

.file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-5);
  min-width: 0;
  padding: var(--ds-space-4) 0;
  border-bottom: 1px solid var(--ds-line);
}

.file-row:last-child {
  border-bottom: 0;
}

.file-row > div {
  display: grid;
  min-width: 0;
  gap: var(--ds-space-1);
}

.file-row strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-body-sm);
}

.file-row span {
  overflow-wrap: anywhere;
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
}

.file-row small {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
}

.file-row input {
  display: none;
}

.form-hint,
.form-error {
  border-radius: var(--ds-radius-sm);
  padding: var(--ds-space-3);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-semibold);
  line-height: var(--ds-leading-body);
}

.form-hint {
  color: var(--ds-status-warning-fg);
  background: var(--ds-status-warning-bg);
}

.retry-hint {
  color: var(--ds-status-info-fg);
  background: var(--ds-status-info-bg);
}

.form-error {
  color: var(--ds-status-danger-fg);
  background: var(--ds-status-danger-bg);
}

.preference-section {
  border-top: 1px solid var(--ds-line);
  border-bottom: 1px solid var(--ds-line);
}

.preference-toggle {
  box-sizing: border-box;
  width: 100%;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--ds-ink);
  font-family: var(--ds-font-sans);
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-bold);
  cursor: pointer;
}

.preference-toggle small {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
}

.preference-toggle:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.option-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-5);
  padding: 0 0 var(--ds-space-4);
}

.option-row label {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  min-height: 40px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-medium);
}

.option-row input {
  accent-color: var(--ds-orange-action);
}

.submit-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
}

.submit-row small {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .file-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .submit-row {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
