<template>
  <div class="audio-recorder" :class="`rec-state-${status}`">
    <button
      v-if="status === 'idle'"
      type="button"
      @click="openStartDialog"
      :disabled="!canRecord"
      :title="recordHint"
      class="ai-score-control"
    >
      <span class="ai-score-mark">
        <el-icon><DataAnalysis /></el-icon>
      </span>
      <span class="ai-score-copy">
        <strong>AI 评分</strong>
        <small>点击录制</small>
      </span>
    </button>

    <button
      v-else-if="status === 'recording'"
      type="button"
      @click="runningDialogVisible = true"
      title="查看 AI 评分采集进度"
      class="ai-score-control is-recording"
    >
      <span class="ai-score-mark">
        <span class="rec-dot"></span>
      </span>
      <span class="ai-score-copy">
        <strong>正在采集</strong>
        <small>{{ formattedDuration }}</small>
      </span>
      <span class="score-wave" aria-hidden="true">
        <AgentVisualizer variant="wave" state="recording" compact />
      </span>
      <span class="score-observe" aria-hidden="true">
        <span :class="{ active: realtimeAsrStatus === 'ready' || realtimeAsrStatus === 'streaming' }">转写 {{ transcriptFinalCount }}</span>
        <span>帧 {{ visualFrameCount }}</span>
      </span>
    </button>

    <button
      v-else-if="status === 'uploading'"
      type="button"
      class="ai-score-control is-progress"
      title="查看 AI 评分上传进度"
      @click="runningDialogVisible = true"
    >
      <span class="ai-score-mark">
        <el-icon><DataAnalysis /></el-icon>
      </span>
      <span class="ai-score-copy">
        <strong>上传样本</strong>
        <small>{{ uploadPercent }}%</small>
      </span>
      <el-progress
        class="mini-progress"
        :percentage="uploadPercent"
        :show-text="false"
        :stroke-width="3"
        color="#1fd5f9"
      />
    </button>

    <button
      v-else-if="status === 'processing'"
      type="button"
      class="ai-score-control is-processing"
      title="查看 AI 评分进度"
      @click="runningDialogVisible = true"
    >
      <span class="ai-score-mark">
        <AgentVisualizer variant="grid" state="processing" compact />
      </span>
      <span class="ai-score-copy">
        <strong>{{ analysisLabel }}</strong>
        <small>{{ analysisStatusText }}</small>
      </span>
      <el-progress
        class="mini-progress"
        :percentage="analysisProgress"
        :color="analysisColor"
        :stroke-width="3"
        :show-text="false"
        :indeterminate="analysisIndeterminate"
      />
    </button>

    <button
      v-else-if="status === 'done'"
      type="button"
      @click="runningDialogVisible = true"
      class="ai-score-control is-done"
      title="查看评分结果或重新评分"
    >
      <span class="ai-score-mark">
        <el-icon><DataAnalysis /></el-icon>
      </span>
      <span class="ai-score-copy">
        <strong>评分完成</strong>
        <small>查看结果</small>
      </span>
    </button>

    <button
      v-else-if="status === 'failed'"
      type="button"
      class="ai-score-control is-failed"
      title="查看失败原因或重新开始"
      @click="runningDialogVisible = true"
    >
      <span class="ai-score-mark">
        <el-icon><RefreshRight /></el-icon>
      </span>
      <span class="ai-score-copy">
        <strong>分析失败</strong>
        <small>点击重试</small>
      </span>
    </button>
  </div>

  <AiScoreStartDialog
    v-model="startDialogVisible"
    v-model:use-history-memory="useHistoryMemory"
    v-model:jury-enabled="juryEnabled"
    :loading="dialogLoading"
    source-label="当前路演"
    :project-name="projectName"
    :team-name="teamName"
    :track-name="trackName"
    :disabled="Boolean(startDialogError)"
    :error-message="startDialogError"
    @confirm="confirmStartRecording"
  />

  <AiScoreRunningDialog
    v-model="runningDialogVisible"
    :loading="dialogLoading"
    :session="runningDialogSession"
    @view="viewScoreResult"
    @finish-recording="finishRecordingFromDialog"
    @cancel-session="cancelRunningScoring"
    @restart="restartScoring"
  />
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { DataAnalysis, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MeetingMediaRecorder from '@/utils/mediaRecorder'
import AgentVisualizer from './AgentVisualizer.vue'
import AiScoreStartDialog from './ai-score/AiScoreStartDialog.vue'
import AiScoreRunningDialog from './ai-score/AiScoreRunningDialog.vue'
import {
  cancelAiScoreSession,
  createAiScoreSession,
  getAiScoreSessionStatus,
  startAiScoreSession
} from '../utils/aiScoreSession'

const props = defineProps({
  meetingId: { type: [String, Number], required: true },
  projectId: { type: [String, Number], default: null },
  teamId: { type: [String, Number], default: null },
  room: { type: Object, default: null },
  cameraMeta: { type: Object, default: () => ({}) },
  trackId: { type: [String, Number], default: '' },
  trackName: { type: String, default: '新一代信息技术赛道' },
  projectName: { type: String, default: '' },
  teamName: { type: String, default: '' }
})

const emit = defineEmits(['recording-status-change'])
const router = useRouter()

// --- 状态 ---
const status = ref('idle') // idle | recording | uploading | processing | done | failed
const duration = ref(0)
let durationTimer = null
let availabilityTimer = null
let sessionPollTimer = null
const currentRoom = ref(null)
const currentSessionId = ref('')
const authoritativeSessionId = ref(null)
const realtimeAsrStatus = ref('idle')
const sessionSnapshot = ref(null)
const transcriptFinalCount = ref(0)
const visualFrameCount = ref(0)
const startDialogVisible = ref(false)
const runningDialogVisible = ref(false)
const dialogLoading = ref(false)
const useHistoryMemory = ref(true)
const juryEnabled = ref(false)
const startDialogError = ref('')
const mediaAvailability = ref({
  hasRoom: false,
  hasAudio: false,
  hasVideo: false,
  audioCount: 0,
  videoCount: 0
})

// --- 上传进度 ---
const uploadPercent = ref(0)

// --- 分析进度 ---
const analysisStep = ref('')       // asr | speech | llm
const analysisLabel = ref('分析中...')
const analysisProgress = ref(0)    // 0-100
const analysisIndeterminate = ref(true)
let pollTimer = null
const analysisStartTime = ref(0)
let restoredMeetingId = ''

const sessionStorageKey = computed(() => `orep:ai-scoring-session:${props.meetingId}`)

const analysisColor = computed(() => {
  if (analysisStep.value === 'asr') return '#409eff'
  if (analysisStep.value === 'speech') return '#67c23a'
  return '#e6a23c'
})

const canRecord = computed(() => {
  return status.value === 'idle' &&
    mediaAvailability.value.hasRoom &&
    mediaAvailability.value.hasAudio &&
    mediaAvailability.value.hasVideo
})

function mediaPrecheckMessage() {
  if (!mediaAvailability.value.hasRoom) return '请先连接到路演后再开始 AI 评分。'
  if (!mediaAvailability.value.hasAudio && !mediaAvailability.value.hasVideo) {
    return '请先开启麦克风，并开启摄像头或共享屏幕后再开始 AI 评分。'
  }
  if (!mediaAvailability.value.hasAudio) return '请先开启麦克风或确认路演中存在有效音频。'
  if (!mediaAvailability.value.hasVideo) return '请先开启摄像头或共享屏幕后再开始 AI 评分。'
  return ''
}

const recordHint = computed(() => {
  const message = mediaPrecheckMessage()
  if (message) return message
  return 'AI评分（录制后自动分析）'
})

const analysisStatusText = computed(() => {
  if (!sessionSnapshot.value) return 'AI 评分中'
  if (analysisProgress.value > 0 && analysisProgress.value < 100) {
    return `${analysisProgress.value}% · ${sessionSnapshot.value.step_label || '处理中'}`
  }
  const asrSource = sessionSnapshot.value.asr_source
  const videoSource = sessionSnapshot.value.video_source
  if (asrSource || videoSource) {
    const asr = asrSource === 'realtime' ? '实时转写' : asrSource === 'file' ? '文件转写' : '转写'
    const video = videoSource === 'session_capture' ? '关键帧' : videoSource === 'video_file' ? '完整视频' : '视频'
    return `${asr} / ${video}`
  }
  return `转写 ${transcriptFinalCount.value} · 帧 ${visualFrameCount.value}`
})

const formattedDuration = computed(() => {
  const m = Math.floor(duration.value / 60).toString().padStart(2, '0')
  const s = Math.floor(duration.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const runningDialogSession = computed(() => ({
  sessionId: authoritativeSessionId.value || currentSessionId.value,
  sessionNo: sessionSnapshot.value?.session_no || sessionSnapshot.value?.sessionNo || currentSessionId.value,
  status: status.value === 'processing' ? 'scoring' : status.value,
  currentStage: status.value === 'recording'
    ? `采集中 ${formattedDuration.value}`
    : analysisLabel.value || sessionSnapshot.value?.current_step || status.value,
  progressPercent: status.value === 'recording'
    ? 0
    : status.value === 'done'
      ? 100
      : analysisProgress.value || uploadPercent.value || 0,
  transcriptCount: transcriptFinalCount.value,
  frameCount: visualFrameCount.value,
  errorMessage: sessionSnapshot.value?.error || sessionSnapshot.value?.error_message || sessionSnapshot.value?.message || ''
}))

// --- 分析步骤标签 ---
const STEP_LABELS = {
  converting: '音频转码',
  asr: '语音识别',
  speech: '语音分析',
  video_analysis: '视频分析',
  fusion: '音视频融合',
  llm: 'AI评分',
  profile: '生成画像',
  report: '生成报告',
  completed: '已完成'
}

const STEP_PROGRESS = {
  converting: 8,
  asr: 18,
  speech: 30,
  video_analysis: 48,
  fusion: 62,
  llm: 74,
  profile: 84,
  report: 92,
  completed: 100
}

// --- 创建录音器 ---
const recorder = new MeetingMediaRecorder({
  meetingId: props.meetingId,
  onStatusChange: (s) => {
    // 录音器状态 → 组件状态映射
    if (s === 'recording' || s === 'stopping') {
      status.value = s
    } else if (s === 'uploading') {
      status.value = 'uploading'
      uploadPercent.value = 0
    } else if (s === 'uploaded') {
      status.value = 'processing'
      startPolling()
    } else if (s === 'upload_failed') {
      status.value = 'failed'
    } else if (s === 'idle') {
      // idle 且不在其他状态时才重置
      if (status.value !== 'processing' && status.value !== 'done') {
        status.value = 'idle'
      }
    }
    emit('recording-status-change', s)
  },
  onUploadProgress: (percent, loaded, total) => {
    uploadPercent.value = percent
  },
  onUploadComplete: (result) => {
    ElMessage.success('音频已上传，AI 正在分析...')
  },
  onError: (msg) => {
    status.value = 'failed'
    ElMessage.warning(msg)
  },
  onRealtimeAsrStatusChange: (nextStatus) => {
    realtimeAsrStatus.value = nextStatus
    if (nextStatus === 'failed') {
      ElMessage.warning('实时转写连接异常，结束后将使用完整录制文件兜底分析')
    }
  }
})

// 监听 room 变化，传给 recorder（用于获取摄像头/屏幕共享视频轨）
function setRecorderRoom(room) {
  currentRoom.value = room
  if (room) recorder.setRoom(room)
  refreshMediaAvailability()
}

watch(() => props.room, (r) => { if (r) setRecorderRoom(r) }, { immediate: true })

watch(() => props.cameraMeta, (meta) => {
  recorder.setVideoTransform?.(meta || {})
}, { immediate: true, deep: true })

watch(mediaAvailability, () => {
  if (startDialogVisible.value) {
    startDialogError.value = mediaPrecheckMessage()
  }
}, { deep: true })

function refreshMediaAvailability() {
  mediaAvailability.value = recorder.getMediaAvailability()
}

availabilityTimer = setInterval(refreshMediaAvailability, 1500)

// --- 轮询分析状态 ---
let pollRetryCount = 0
const MAX_POLL_RETRIES = 5

function startPolling() {
  stopPolling()
  if (!analysisStartTime.value) analysisStartTime.value = Date.now()
  if (!analysisStep.value) analysisStep.value = 'asr'
  if (!analysisLabel.value) analysisLabel.value = '识别中...'
  analysisIndeterminate.value = false
  if (!analysisProgress.value) analysisProgress.value = 6
  pollRetryCount = 0

  pollTimer = setInterval(pollStatus, 3000)
  pollStatus() // 立即查一次
}

async function pollStatus() {
  try {
    if (authoritativeSessionId.value) {
      const authoritative = await getAiScoreSessionStatus(authoritativeSessionId.value)
      sessionSnapshot.value = authoritative
      analysisStep.value = authoritative.currentStage || analysisStep.value
      analysisLabel.value = STEP_LABELS[authoritative.currentStage] || authoritative.currentStage || '分析中...'
      analysisProgress.value = Number(authoritative.progressPercent || 0)
      analysisIndeterminate.value = false
      if (authoritative.status === 'completed') {
        status.value = 'done'
        analysisProgress.value = 100
        clearStoredSession()
        stopSessionPolling()
        stopPolling()
        ElMessage.success('AI 评分完成！')
      } else if (authoritative.status === 'failed') {
        status.value = 'failed'
        clearStoredSession()
        stopSessionPolling()
        stopPolling()
        ElMessage.error(`AI 分析失败: ${authoritative.errorMessage || '未知错误'}`)
      }
      return
    }
    const res = await fetch(`/api/ai/status/${props.meetingId}`)
    if (!res.ok) {
      // 502/503/504 通常是代理超时，自动重试
      if ([502, 503, 504].includes(res.status)) {
        pollRetryCount++
        // console.warn(`[AI评分] 状态查询 ${res.status}，重试 ${pollRetryCount}/${MAX_POLL_RETRIES}`)
        if (pollRetryCount >= MAX_POLL_RETRIES) {
          status.value = 'failed'
          stopPolling()
          ElMessage.error('AI 服务暂时无法响应，请稍后查看报告')
        }
        return
      }
      return
    }
    pollRetryCount = 0 // 成功则重置计数
    const data = await res.json()
    applyAnalysisStatus(data)

    if (data.status === 'completed') {
      status.value = 'done'
      analysisProgress.value = 100
      analysisIndeterminate.value = false
      clearStoredSession()
      stopSessionPolling()
      stopPolling()
      ElMessage.success('AI 评分完成！')
      return
    }

    if (data.status === 'failed') {
      status.value = 'failed'
      clearStoredSession()
      stopSessionPolling()
      stopPolling()
      ElMessage.error(`AI 分析失败: ${data.error || '未知错误'}`)
      return
    }
  } catch (e) {
    // 静默处理轮询错误
  }
}

function applyAnalysisStatus(data = {}) {
  sessionSnapshot.value = { ...(sessionSnapshot.value || {}), ...data }
  const nextStep = data.current_step || analysisStep.value
  if (nextStep) {
    analysisStep.value = nextStep
    analysisLabel.value = data.step_label || STEP_LABELS[nextStep] || '分析中...'
  } else {
    analysisLabel.value = data.step_label || '分析中...'
  }

  const serverProgress = Number(data.progress_percent)
  if (Number.isFinite(serverProgress) && serverProgress > 0) {
    analysisProgress.value = Math.max(0, Math.min(100, Math.round(serverProgress)))
    analysisIndeterminate.value = false
    return
  }

  if (nextStep && STEP_PROGRESS[nextStep]) {
    analysisProgress.value = STEP_PROGRESS[nextStep]
    analysisIndeterminate.value = false
    return
  }

  const elapsed = analysisStartTime.value ? (Date.now() - analysisStartTime.value) / 1000 : 0
  analysisProgress.value = Math.min(88, Math.max(8, Math.round(elapsed / 6)))
  analysisIndeterminate.value = false
}

function startSessionPolling() {
  stopSessionPolling()
  sessionPollTimer = setInterval(pollSessionStatus, 3000)
  pollSessionStatus()
}

function stopSessionPolling() {
  if (sessionPollTimer) {
    clearInterval(sessionPollTimer)
    sessionPollTimer = null
  }
}

async function pollSessionStatus() {
  if (!currentSessionId.value) return
  try {
    const res = await fetch(`/api/ai/session/${currentSessionId.value}/status`)
    if (!res.ok) return
    const data = await res.json()
    sessionSnapshot.value = data
    const obs = data.observability || {}
    transcriptFinalCount.value = obs.transcript_final_count || 0
    visualFrameCount.value = obs.visual_frame_count || 0
    if (data.transcript_status) realtimeAsrStatus.value = data.transcript_status
    if (status.value === 'processing' || data.current_step) {
      applyAnalysisStatus(data)
    }
  } catch {}
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// --- 录制控制 ---
function openStartDialog() {
  refreshMediaAvailability()
  startDialogError.value = mediaPrecheckMessage()
  startDialogVisible.value = true
}

async function confirmStartRecording() {
  refreshMediaAvailability()
  startDialogError.value = mediaPrecheckMessage()
  if (startDialogError.value) return
  dialogLoading.value = true
  try {
    await startRecording()
    if (status.value === 'recording') {
      startDialogVisible.value = false
    }
  } finally {
    dialogLoading.value = false
  }
}

async function startRecording() {
  refreshMediaAvailability()
  startDialogError.value = mediaPrecheckMessage()
  if (startDialogError.value) {
    return
  }

  const session = await createScoringSession()
  if (!session) return

  currentSessionId.value = session.session_id
  authoritativeSessionId.value = session.authoritative_session_id || null
  storeSessionReference(session.session_id, authoritativeSessionId.value)
  recorder.setSessionId(session.session_id)
  recorder.setAuthoritativeSessionId(authoritativeSessionId.value)
  recorder.setMediaClockId(session.media_clock_id)
  sessionSnapshot.value = session
  transcriptFinalCount.value = 0
  visualFrameCount.value = 0
  startSessionPolling()

  if (await recorder.startRecording()) {
    duration.value = 0
    status.value = 'recording'
    durationTimer = setInterval(() => {
      duration.value = recorder.getDuration()
    }, 1000)
    ElMessage.info('已开始采集音视频（用于 AI 评分）')
  } else {
    await finishScoringSession('failed', '录制启动失败')
    startDialogError.value = '录制启动失败，请检查浏览器麦克风、摄像头或屏幕共享权限。'
    currentSessionId.value = ''
    authoritativeSessionId.value = null
    recorder.setSessionId(null)
    recorder.setAuthoritativeSessionId(null)
    recorder.setMediaClockId(null)
  }
}

async function cancelRunningScoring() {
  runningDialogVisible.value = false
  await nextTick()
  try {
    await ElMessageBox.confirm('终止后本轮评分不会继续生成完整报告，确认终止？', '终止当前评分', {
      confirmButtonText: '终止评分',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    runningDialogVisible.value = true
    return
  }
  dialogLoading.value = true
  try {
    if (status.value === 'recording') {
      await finishScoringSession('cancelled', '用户终止评分')
      recorder.stopRecording()
    } else if (currentSessionId.value) {
      await finishScoringSession('cancelled', '用户终止评分')
    }
    if (authoritativeSessionId.value) {
      try { await cancelAiScoreSession(authoritativeSessionId.value) } catch {}
    }
    resetRuntimeState()
    clearStoredSession()
    runningDialogVisible.value = false
    ElMessage.success('已终止当前评分')
  } finally {
    dialogLoading.value = false
  }
}

async function restartScoring() {
  runningDialogVisible.value = false
  await nextTick()
  try {
    await ElMessageBox.confirm('重新开始会终止当前评分采集或分析进度，确认继续？', '重新开始评分', {
      confirmButtonText: '重新开始',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    runningDialogVisible.value = true
    return
  }
  await stopCurrentScoringForRestart()
  refreshMediaAvailability()
  startDialogError.value = mediaPrecheckMessage()
  startDialogVisible.value = true
}

async function stopCurrentScoringForRestart() {
  dialogLoading.value = true
  try {
    if (status.value === 'recording') {
      await finishScoringSession('cancelled', '用户重新开始评分')
      recorder.stopRecording()
    } else if (['uploading', 'processing'].includes(status.value) && currentSessionId.value) {
      await finishScoringSession('cancelled', '用户重新开始评分')
    }
    resetRuntimeState()
    clearStoredSession()
    runningDialogVisible.value = false
  } finally {
    dialogLoading.value = false
  }
}

async function createScoringSession() {
  let authoritative = null
  try {
    authoritative = await createAiScoreSession({
      sourceType: 'meeting_recording',
      sourceId: Date.now(),
      meetingId: Number(props.meetingId),
      projectId: props.projectId ? Number(props.projectId) : null,
      teamId: props.teamId ? Number(props.teamId) : null,
      trackId: String(props.trackId || props.trackName),
      trackName: props.trackName,
      useHistoryMemory: useHistoryMemory.value,
      juryEnabled: false
    })
    await startAiScoreSession(authoritative.sessionId)
    const res = await fetch('/api/ai/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meeting_id: String(props.meetingId),
        has_audio: mediaAvailability.value.hasAudio,
        has_video: mediaAvailability.value.hasVideo
      })
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || `HTTP ${res.status}`)
    }
    const liveSession = await res.json()
    return {
      ...liveSession,
      authoritative_session_id: authoritative.sessionId,
      authoritative_session_no: authoritative.sessionNo
    }
  } catch (e) {
    if (authoritative?.sessionId) {
      try { await cancelAiScoreSession(authoritative.sessionId) } catch {}
    }
    startDialogError.value = 'AI 评分会话创建失败，请稍后重试。'
    ElMessage.error(startDialogError.value)
    // console.error('[AI评分] 创建 session 失败:', e)
    return null
  }
}

async function finishScoringSession(nextStatus = 'finished', errorMessage = '') {
  if (!currentSessionId.value) return
  try {
    await fetch(`/api/ai/session/${currentSessionId.value}/finish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: nextStatus,
        error_message: errorMessage || null
      })
    })
  } catch (e) {
    // console.warn('[AI评分] 结束 session 失败:', e)
  }
}

async function stopRecording() {
  await finishScoringSession('finished')
  recorder.stopRecording()
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
}

async function finishRecordingFromDialog() {
  dialogLoading.value = true
  try {
    await stopRecording()
    runningDialogVisible.value = false
  } finally {
    dialogLoading.value = false
  }
}

function resetStatus() {
  resetRuntimeState()
  clearStoredSession()
  refreshMediaAvailability()
}

function resetRuntimeState() {
  status.value = 'idle'
  duration.value = 0
  uploadPercent.value = 0
  analysisStep.value = ''
  analysisLabel.value = '分析中...'
  analysisProgress.value = 0
  analysisIndeterminate.value = true
  analysisStartTime.value = 0
  currentSessionId.value = ''
  authoritativeSessionId.value = null
  realtimeAsrStatus.value = 'idle'
  sessionSnapshot.value = null
  transcriptFinalCount.value = 0
  visualFrameCount.value = 0
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
  stopSessionPolling()
  stopPolling()
  recorder.setSessionId(null)
  recorder.setAuthoritativeSessionId(null)
  recorder.setMediaClockId(null)
}

function storeSessionReference(sessionId, authoritativeId = authoritativeSessionId.value) {
  if (!sessionId) return
  localStorage.setItem(sessionStorageKey.value, JSON.stringify({
    meetingId: String(props.meetingId),
    sessionId,
    authoritativeSessionId: authoritativeId || null,
    savedAt: Date.now()
  }))
}

function clearStoredSession() {
  localStorage.removeItem(sessionStorageKey.value)
}

function readStoredSessionId() {
  try {
    const raw = localStorage.getItem(sessionStorageKey.value)
    if (!raw) return ''
    const parsed = JSON.parse(raw)
    return parsed?.meetingId === String(props.meetingId) ? parsed.sessionId || '' : ''
  } catch {
    return ''
  }
}

function readStoredAuthoritativeSessionId() {
  try {
    const raw = localStorage.getItem(sessionStorageKey.value)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed?.meetingId === String(props.meetingId)
      ? parsed.authoritativeSessionId || null
      : null
  } catch {
    return null
  }
}

async function restoreScoringSession() {
  if (!props.meetingId) return
  const meetingKey = String(props.meetingId)
  restoredMeetingId = meetingKey
  try {
    let data = null
    const latestRes = await fetch(`/api/ai/session/latest/${meetingKey}`)
    if (latestRes.ok) {
      data = await latestRes.json()
    } else {
      const storedSessionId = readStoredSessionId()
      if (storedSessionId) {
        const storedRes = await fetch(`/api/ai/session/${storedSessionId}/status`)
        if (storedRes.ok) data = await storedRes.json()
      }
    }

    if (!data?.session_id) {
      const statusRes = await fetch(`/api/ai/status/${meetingKey}`)
      if (statusRes.ok) {
        const run = await statusRes.json()
        if (restoredMeetingId !== meetingKey) return
        if (run.status === 'completed') {
          status.value = 'done'
          applyAnalysisStatus(run)
        } else if (run.status === 'processing' && (run.progress_updated_at || run.report_url)) {
          status.value = 'processing'
          applyAnalysisStatus(run)
          startPolling()
        }
      }
      return
    }

    if (restoredMeetingId !== meetingKey) return
    currentSessionId.value = data.session_id
    authoritativeSessionId.value = readStoredAuthoritativeSessionId()
    storeSessionReference(data.session_id)
    sessionSnapshot.value = data
    recorder.setSessionId(data.session_id)
    recorder.setAuthoritativeSessionId(authoritativeSessionId.value)
    recorder.setMediaClockId(data.media_clock_id)
    const obs = data.observability || {}
    transcriptFinalCount.value = obs.transcript_final_count || 0
    visualFrameCount.value = obs.visual_frame_count || 0
    if (data.transcript_status) realtimeAsrStatus.value = data.transcript_status
    startSessionPolling()

    const finalStatus = data.final_score_status
    if (finalStatus === 'completed' || data.current_step === 'completed') {
      status.value = 'done'
      applyAnalysisStatus(data)
      clearStoredSession()
      stopSessionPolling()
    } else if (finalStatus === 'failed') {
      status.value = 'failed'
      clearStoredSession()
      stopSessionPolling()
    } else if (finalStatus === 'processing' || data.current_step || data.recording_status === 'uploaded') {
      status.value = 'processing'
      applyAnalysisStatus(data)
      startPolling()
    }
  } catch (e) {
    // console.warn('[AI评分] 恢复评分会话失败:', e)
  }
}

function handleBeforeUnload(event) {
  if (status.value !== 'recording') return
  event.preventDefault()
  event.returnValue = 'AI 评分正在采集音视频，刷新会中断本地采集。'
}

// --- 查看评分结果 ---
function viewScoreResult() {
  if (authoritativeSessionId.value) {
    router.push(`/ai-score/report/${authoritativeSessionId.value}/result`)
    return
  }
  router.push(`/ai-score/${props.meetingId}`)
}

// 暴露方法
defineExpose({
  startRecording,
  stopRecording,
  getRecorder: () => recorder,
  setRoom: setRecorderRoom,
  addRemoteTrack: (track, sid) => recorder.addRemoteTrack(track, sid),
  removeRemoteTrack: (sid) => recorder.removeRemoteTrack(sid),
  addLocalTrack: (track) => recorder.addLocalTrack(track),
  setVideoTrack: (track) => recorder.setVideoTrack(track),
  isRecording: computed(() => status.value === 'recording')
})

onUnmounted(() => {
  if (durationTimer) clearInterval(durationTimer)
  if (availabilityTimer) clearInterval(availabilityTimer)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  stopSessionPolling()
  stopPolling()
  recorder.destroy()
})

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
  restoreScoringSession()
})

watch(
  () => String(props.meetingId || ''),
  (nextMeetingId, previousMeetingId) => {
    if (!nextMeetingId || nextMeetingId === previousMeetingId) return
    restoredMeetingId = nextMeetingId
    resetRuntimeState()
    refreshMediaAvailability()
    restoreScoringSession()
  }
)
</script>

<style scoped>
.audio-recorder {
  position: relative;
  display: flex;
  align-items: center;
  height: 42px;
}

.ai-score-control {
  position: relative;
  isolation: isolate;
  min-width: 138px;
  height: 42px;
  padding: 0 12px 0 8px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  overflow: hidden;
  border: 1px solid rgba(31, 213, 249, .22);
  border-radius: 999px;
  color: #d8fbff;
  background:
    radial-gradient(circle at 16px -8px, rgba(31, 213, 249, .24), transparent 45%),
    linear-gradient(135deg, rgba(10, 34, 44, .94), rgba(14, 18, 26, .94));
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .08),
    0 10px 24px rgba(0, 0, 0, .22);
  cursor: pointer;
  text-align: left;
  transition:
    transform .2s cubic-bezier(.19, 1, .22, 1),
    border-color .2s ease,
    background .2s ease,
    box-shadow .2s ease;
}

.ai-score-control::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background: linear-gradient(115deg, transparent 8%, rgba(240, 241, 250, .16) 44%, transparent 72%);
  transform: translateX(-120%);
  transition: transform .44s cubic-bezier(.19, 1, .22, 1);
}

.ai-score-control:hover {
  transform: translateY(-1px);
  border-color: rgba(31, 213, 249, .48);
  background:
    radial-gradient(circle at 16px -8px, rgba(31, 213, 249, .34), transparent 48%),
    linear-gradient(135deg, rgba(12, 42, 54, .98), rgba(17, 21, 29, .98));
  box-shadow:
    inset 0 1px 0 rgba(240, 241, 250, .1),
    0 12px 28px rgba(0, 0, 0, .28),
    0 0 0 1px rgba(31, 213, 249, .08);
}

.ai-score-control:hover::before {
  transform: translateX(120%);
}

.ai-score-control:disabled {
  cursor: not-allowed;
  opacity: .48;
  transform: none;
}

.ai-score-mark {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 50%;
  color: #9bf0ff;
  background: rgba(31, 213, 249, .12);
  box-shadow: inset 0 0 0 1px rgba(31, 213, 249, .18);
}

.ai-score-mark .el-icon {
  font-size: 16px;
}

.ai-score-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1;
}

.ai-score-copy strong {
  color: #f0f1fa;
  font-size: 13px;
  font-weight: 820;
  white-space: nowrap;
}

.ai-score-copy small {
  color: rgba(216, 251, 255, .58);
  font-size: 10px;
  font-weight: 760;
  font-variant-numeric: tabular-nums;
  letter-spacing: .04em;
  white-space: nowrap;
}

.score-wave {
  width: 44px;
  height: 18px;
  margin-left: 2px;
  color: #ff9a9a;
  opacity: .92;
}

.score-observe {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  margin-left: 2px;
  padding-left: 8px;
  border-left: 1px solid rgba(255, 255, 255, .12);
  color: rgba(255, 208, 208, .62);
  font-size: 9px;
  font-weight: 780;
  line-height: 1;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.score-observe .active {
  color: #7affb4;
}

.is-recording {
  min-width: 216px;
  border-color: rgba(255, 107, 107, .38);
  color: #ffd0d0;
  background:
    radial-gradient(circle at 16px -8px, rgba(255, 107, 107, .26), transparent 46%),
    linear-gradient(135deg, rgba(72, 22, 30, .96), rgba(18, 19, 26, .96));
  animation: pulse-border 1.8s infinite;
}

.is-recording .ai-score-mark {
  background: rgba(255, 107, 107, .13);
  box-shadow: inset 0 0 0 1px rgba(255, 107, 107, .22);
}

.is-recording .ai-score-copy small {
  color: #ff9a9a;
}

.rec-dot {
  display: inline-block;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #ff8c8c;
  box-shadow: 0 0 0 0 rgba(255, 140, 140, .42);
  animation: live-dot 1.2s cubic-bezier(.19, 1, .22, 1) infinite;
}

.is-progress,
.is-processing {
  min-width: 158px;
  cursor: default;
}

.is-processing {
  border-color: rgba(122, 255, 180, .28);
  background:
    radial-gradient(circle at 16px -8px, rgba(122, 255, 180, .22), transparent 46%),
    linear-gradient(135deg, rgba(13, 43, 35, .95), rgba(17, 21, 29, .95));
}

.is-processing .ai-score-mark {
  color: #7affb4;
  background: rgba(122, 255, 180, .12);
  box-shadow: inset 0 0 0 1px rgba(122, 255, 180, .18);
}

.is-done {
  border-color: rgba(122, 255, 180, .34);
  background:
    radial-gradient(circle at 16px -8px, rgba(122, 255, 180, .24), transparent 46%),
    linear-gradient(135deg, rgba(12, 49, 38, .96), rgba(17, 21, 29, .96));
}

.is-done .ai-score-mark,
.is-done .ai-score-copy small {
  color: #7affb4;
}

.is-failed {
  border-color: rgba(255, 107, 107, .34);
  background:
    radial-gradient(circle at 16px -8px, rgba(255, 107, 107, .22), transparent 46%),
    linear-gradient(135deg, rgba(71, 22, 29, .94), rgba(17, 21, 29, .94));
}

.is-failed .ai-score-mark,
.is-failed .ai-score-copy small {
  color: #ff9a9a;
}

.mini-progress {
  width: 42px;
  margin-left: auto;
}

.mini-progress :deep(.el-progress-bar__outer) {
  background-color: rgba(240, 241, 250, .12);
}

.mini-progress :deep(.el-progress-bar__inner) {
  transition: width .3s ease;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 107, 107, .32); }
  50% { box-shadow: 0 0 0 7px rgba(255, 107, 107, 0); }
}

@keyframes live-dot {
  0% { transform: scale(.9); box-shadow: 0 0 0 0 rgba(255, 140, 140, .42); }
  100% { transform: scale(1); box-shadow: 0 0 0 8px rgba(255, 140, 140, 0); }
}

@media (prefers-reduced-motion: reduce) {
  .ai-score-control,
  .rec-dot,
  .is-recording {
    animation: none !important;
    transition: none !important;
  }
}
</style>
