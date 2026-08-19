<template>
  <main class="meeting-replay">
    <header class="replay-head">
      <div>
        <button type="button" class="back-link" @click="router.push('/my-recordings')">返回路演回放</button>
        <span class="eyebrow">路演回放</span>
        <h1>{{ meetingTitle }}</h1>
        <p>{{ meetingMeta }}</p>
      </div>
      <span class="record-count">{{ recordings.length }} 份录制</span>
    </header>

    <section v-if="loading" class="replay-state" aria-live="polite">
      <strong>正在加载路演回放</strong>
      <p>正在获取录制文件和语音转录。</p>
    </section>

    <section v-else-if="loadError && !recordings.length" class="replay-state" aria-live="polite">
      <strong>暂时无法打开这场回放</strong>
      <p>{{ loadError }}</p>
      <button type="button" @click="loadReplay">重新加载</button>
    </section>

    <section v-else class="replay-layout">
      <div class="video-column">
        <section class="video-panel">
          <video
            v-if="playbackUrl"
            :src="playbackUrl"
            controls
            playsinline
            preload="metadata"
          />
          <div v-else class="video-empty">
            <strong>{{ playbackLoading ? '正在准备视频' : playbackError ? '录制文件暂时无法读取' : '暂无可播放视频' }}</strong>
            <p>{{ playbackLoading ? '录制文件加载完成后即可观看。' : playbackError || '本场路演还没有生成可播放的录制文件。' }}</p>
            <button
              v-if="playbackError && selectedRecording"
              type="button"
              class="retry-playback"
              @click="selectRecording(selectedRecording)"
            >
              重新加载视频
            </button>
          </div>
        </section>

        <section class="recording-list">
          <header>
            <div>
              <h2>录制文件</h2>
              <p>选择一份录制进行回看。</p>
            </div>
          </header>
          <button
            v-for="recording in recordings"
            :key="recording.id"
            type="button"
            class="recording-item"
            :class="{ active: selectedRecordingId === recording.id }"
            :disabled="recording.status !== 'READY' || !recording.filePath"
            @click="selectRecording(recording)"
          >
            <span>
              <strong>{{ recording.meetingTitle || meetingTitle }}</strong>
              <small>{{ formatDate(recording.recordedAt) }} · {{ formatDuration(recording.durationSeconds) }}</small>
            </span>
            <em>{{ recordingStatus(recording) }}</em>
          </button>
          <div v-if="!recordings.length" class="list-empty">暂无录制文件</div>
        </section>
      </div>

      <aside class="transcript-panel">
        <header>
          <div>
            <h2>语音转录</h2>
            <p>{{ transcriptSegments.length ? `${transcriptSegments.length} 段内容` : '暂无转录信息' }}</p>
          </div>
        </header>

        <div v-if="transcriptSegments.length" class="transcript-list">
          <article v-for="(segment, index) in transcriptSegments" :key="segment.id || index">
            <div class="segment-meta">
              <strong>{{ segment.speakerName || segment.roleName || `发言 ${index + 1}` }}</strong>
              <span>{{ formatTimestamp(segment.startMs) }}</span>
            </div>
            <p>{{ segment.text }}</p>
          </article>
        </div>
        <div v-else class="transcript-empty">
          <strong>暂无语音转录</strong>
          <p>完成语音识别后，转录内容会显示在这里。</p>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '../utils/request'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const playbackLoading = ref(false)
const loadError = ref('')
const meeting = ref(null)
const recordings = ref([])
const report = ref(null)
const selectedRecordingId = ref(null)
const playbackUrl = ref('')
const playbackError = ref('')

const selectedRecording = computed(() =>
  recordings.value.find(item => item.id === selectedRecordingId.value) || null
)

const meetingTitle = computed(() =>
  meeting.value?.title
  || recordings.value[0]?.meetingTitle
  || `路演 ${route.params.id}`
)

const meetingMeta = computed(() => {
  const start = meeting.value?.startTime || recordings.value[0]?.recordedAt
  return start ? formatDate(start) : '路演时间待确认'
})

const transcriptSegments = computed(() => {
  const structured = report.value?.finalSpeakerSegments?.length
    ? report.value.finalSpeakerSegments
    : report.value?.asrSegments || []
  if (structured.length) {
    return structured
      .filter(item => String(item?.text || '').trim())
      .map(item => ({
        ...item,
        text: String(item.text).trim()
      }))
  }
  return String(report.value?.transcript || '')
    .split(/\n+/)
    .map(text => text.trim())
    .filter(Boolean)
    .map((text, index) => ({ id: `plain-${index}`, text, startMs: null }))
})

onMounted(loadReplay)
onBeforeUnmount(clearPlayback)

async function loadReplay() {
  loading.value = true
  loadError.value = ''
  clearPlayback()
  const meetingId = route.params.id
  const [meetingResult, recordingResult, reportResult] = await Promise.allSettled([
    request.get(`/api/meeting/${meetingId}/detail`, { silentError: true }),
    request.get(`/api/recording/meeting/${meetingId}`, { silentError: true }),
    request.get(`/api/ai-score/reports/by-meeting/${meetingId}`, { silentError: true })
  ])

  if (meetingResult.status === 'fulfilled') {
    meeting.value = meetingResult.value?.data || meetingResult.value || null
  }
  if (recordingResult.status === 'fulfilled') {
    const data = recordingResult.value?.data || recordingResult.value || []
    recordings.value = Array.isArray(data) ? data : []
  } else {
    recordings.value = []
  }
  if (reportResult.status === 'fulfilled') {
    report.value = reportResult.value?.data || reportResult.value || null
  } else {
    report.value = null
  }

  const firstReady = recordings.value.find(item => item.status === 'READY' && item.filePath)
  if (firstReady) await selectRecording(firstReady)

  if (
    meetingResult.status === 'rejected'
    && recordingResult.status === 'rejected'
    && reportResult.status === 'rejected'
  ) {
    loadError.value = '没有找到可访问的路演记录、录制文件或转录信息。'
  }
  loading.value = false
}

async function selectRecording(recording) {
  if (!recording?.id || recording.status !== 'READY' || !recording.filePath) return
  playbackLoading.value = true
  playbackError.value = ''
  clearPlayback()
  selectedRecordingId.value = recording.id
  try {
    const response = await request.get(`/api/recording/${recording.id}/stream?file=video`, {
      responseType: 'blob',
      timeout: 60000,
      silentError: true
    })
    const blob = response instanceof Blob ? response : response?.data
    if (!(blob instanceof Blob) || blob.size === 0) {
      throw new Error('录制文件为空')
    }
    playbackUrl.value = URL.createObjectURL(blob)
  } catch {
    playbackError.value = '当前录制的文件存储不可用，请稍后重试或联系管理员检查录制存储。'
  } finally {
    playbackLoading.value = false
  }
}

function clearPlayback() {
  if (playbackUrl.value?.startsWith('blob:')) URL.revokeObjectURL(playbackUrl.value)
  playbackUrl.value = ''
}

function recordingStatus(recording) {
  if (recording.status === 'READY' && recording.filePath) return '可播放'
  if (['STARTING', 'RECORDING', 'PROCESSING'].includes(recording.status)) return '生成中'
  if (recording.status === 'FAILED') return '生成失败'
  return '暂不可用'
}

function formatDate(value) {
  if (!value) return '时间待确认'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间待确认'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  if (!total) return '时长待确认'
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return `${minutes} 分 ${rest} 秒`
}

function formatTimestamp(milliseconds) {
  if (milliseconds === undefined || milliseconds === null) return ''
  const seconds = Math.max(0, Math.floor(Number(milliseconds) / 1000))
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}
</script>

<style scoped>
.meeting-replay {
  min-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  color: var(--ds-ink, #1d1d1f);
  background: transparent;
}

.replay-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.back-link {
  display: block;
  margin-bottom: 14px;
  padding: 0;
  border: 0;
  min-height: 34px;
  color: var(--ds-orange-800, #b12f0a);
  background: none;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: color 150ms ease-in-out;
}

.back-link:hover {
  color: var(--ds-orange-action, #cf3d12);
}

.back-link:focus-visible,
.retry-playback:focus-visible,
.replay-state button:focus-visible,
.recording-item:focus-visible {
  outline: 2px solid var(--ds-orange-action, #cf3d12);
  outline-offset: 2px;
}

.eyebrow {
  color: var(--ds-orange-800, #b12f0a);
  font-size: 12px;
  font-weight: 800;
}

.replay-head h1 {
  margin: 6px 0;
  font-size: var(--ds-text-h1, 28px);
  line-height: 1.24;
  letter-spacing: -0.02em;
}

.replay-head p,
.recording-list header p,
.transcript-panel header p {
  margin: 0;
  color: var(--ds-muted, #6e6e73);
  font-size: 13px;
}

.record-count {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--ds-line, rgba(28, 26, 22, 0.09));
  color: var(--ds-ink-2, #2c3038);
  background: var(--ds-surface-solid, #fff);
  font-size: 13px;
  font-weight: 700;
}

.replay-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.75fr);
  gap: 18px;
  align-items: start;
}

.video-column {
  display: grid;
  gap: 18px;
}

.video-panel,
.recording-list,
.transcript-panel,
.replay-state {
  border: 1px solid var(--ds-card-border, var(--ds-line));
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-card-bg, var(--ds-surface));
  box-shadow: var(--ds-card-shadow, none);
}

.video-panel {
  min-height: 420px;
  overflow: hidden;
  background: #101012;
}

.video-panel video {
  display: block;
  width: 100%;
  min-height: 420px;
  max-height: 68vh;
  object-fit: contain;
  background: #101012;
}

.video-empty,
.transcript-empty,
.replay-state {
  min-height: 260px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  padding: 28px;
  text-align: center;
}

.video-empty {
  min-height: 420px;
  color: rgba(255, 255, 255, 0.68);
}

.video-empty strong {
  color: #fff;
  font-size: 18px;
}

.video-empty p,
.transcript-empty p,
.replay-state p {
  margin: 0;
  color: var(--ds-muted, #6e6e73);
}

.retry-playback {
  margin-top: 16px;
  min-height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: var(--ds-radius-pill, 999px);
  background: var(--ds-btn-primary-bg, var(--ds-orange-action, #cf3d12));
  color: var(--ds-btn-primary-fg, #fffaf7);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 150ms ease-in-out;
}

.retry-playback:hover {
  background: var(--ds-btn-primary-bg-hover, var(--ds-orange-700, #c2370e));
}

.retry-playback:active {
  background: var(--ds-btn-primary-bg-active, var(--ds-orange-800, #b12f0a));
}

.recording-list,
.transcript-panel {
  padding: 22px;
}

.recording-list header,
.transcript-panel header {
  margin-bottom: 14px;
}

.recording-list h2,
.transcript-panel h2 {
  margin: 0 0 5px;
  font-size: 18px;
}

.recording-item {
  width: 100%;
  min-height: 66px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 14px;
  border: 1px solid var(--ds-line, rgba(28, 26, 22, 0.09));
  border-radius: var(--ds-radius-md, 12px);
  color: var(--ds-ink, #1d1d1f);
  background: var(--ds-surface-solid, #fff);
  text-align: left;
  font: inherit;
  cursor: pointer;
  transition: border-color 150ms ease-in-out, background-color 150ms ease-in-out;
}

.recording-item + .recording-item {
  margin-top: 8px;
}

.recording-item.active {
  border-color: var(--ds-orange-action, #cf3d12);
  background: var(--ds-orange-50, #fff7f2);
}

.recording-item:not(:disabled):hover {
  border-color: var(--ds-line-strong, rgba(28, 26, 22, 0.13));
  background: var(--ds-orange-50, #fff7f2);
}

.recording-item:disabled {
  cursor: not-allowed;
  color: var(--ds-faint, #9aa1ad);
  background: var(--ds-disabled-bg, #f4f4f5);
  border-color: var(--ds-disabled-border, #e5e7eb);
}

.recording-item span,
.recording-item strong,
.recording-item small {
  display: block;
}

.recording-item small {
  margin-top: 5px;
  color: var(--ds-muted, #6e6e73);
}

.recording-item em {
  color: var(--ds-orange-800, #b12f0a);
  font-size: 13px;
  font-style: normal;
  font-weight: 700;
}

.list-empty {
  min-height: 84px;
  display: grid;
  place-items: center;
  color: var(--ds-muted, #6e6e73);
}

.transcript-panel {
  position: sticky;
  top: 18px;
}

.transcript-list {
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  padding-right: 4px;
}

.transcript-list article {
  padding: 14px 0;
  border-top: 1px solid var(--ds-line, rgba(28, 26, 22, 0.09));
}

.segment-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.segment-meta strong {
  font-size: 13px;
}

.segment-meta span {
  color: var(--ds-faint, #9a9aa0);
  font-size: 12px;
}

.transcript-list p {
  margin: 7px 0 0;
  color: var(--ds-ink-2, #3a3a3c);
  font-size: 14px;
  line-height: 1.7;
}

.transcript-empty {
  min-height: 360px;
}

.replay-state button {
  min-height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  color: var(--ds-btn-primary-fg, #fffaf7);
  background: var(--ds-btn-primary-bg, var(--ds-orange-action, #cf3d12));
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 150ms ease-in-out;
}

.replay-state button:hover {
  background: var(--ds-btn-primary-bg-hover, var(--ds-orange-700, #c2370e));
}

.replay-state button:active {
  background: var(--ds-btn-primary-bg-active, var(--ds-orange-800, #b12f0a));
}

@media (max-width: 980px) {
  .meeting-replay {
    padding: 24px 20px 80px;
  }

  .replay-layout {
    grid-template-columns: 1fr;
  }

  .transcript-panel {
    position: static;
  }
}
</style>
