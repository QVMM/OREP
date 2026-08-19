<template>
  <div class="my-recordings student-page">
    <header class="archive-page-head">
      <div>
        <h1>路演回放</h1>
        <p>回看团队路演，检查表达、节奏和现场呈现。</p>
      </div>
      <div class="archive-head-actions">
        <span class="archive-signal">
          <i :class="{ ready: readyCount > 0 }" aria-hidden="true"></i>
          {{ loading ? '正在同步' : readyCount > 0 ? `${readyCount} 条可回放` : '暂无可回放' }}
        </span>
        <router-link class="return-meeting-action" to="/online-meeting">
          返回路演训练
        </router-link>
        <button class="refresh-action" type="button" :disabled="loading" @click="fetchRecordings">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </button>
      </div>
    </header>

    <section class="archive-overview" aria-label="回放概览">
      <div>
        <span>全部录制</span>
        <strong>{{ recordings.length }}</strong>
      </div>
      <div>
        <span>可回放</span>
        <strong>{{ readyCount }}</strong>
      </div>
      <div>
        <span>生成中</span>
        <strong>{{ processingCount }}</strong>
      </div>
      <div>
        <span>累计时长</span>
        <strong>{{ formatDuration(totalDurationSeconds) || '--' }}</strong>
        <small>{{ formatSize(totalSizeBytes) }}</small>
      </div>
    </section>

    <section class="archive-command">
      <label class="search-console">
        <el-icon><Search /></el-icon>
        <input v-model.trim="query" type="search" placeholder="搜索路演标题、状态或编号" />
      </label>

      <div class="status-switch">
        <button
          v-for="tab in statusTabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeStatus === tab.key }"
          @click="activeStatus = tab.key"
        >
          <span>{{ tab.label }}</span>
          <strong>{{ tab.count }}</strong>
        </button>
      </div>

    </section>

    <section v-loading="loading" class="recording-manifest">
      <div v-if="!loading && recordings.length === 0" class="archive-empty">
        <span class="archive-empty__icon"><VideoCamera /></span>
        <h2>还没有路演回放</h2>
        <p>完成一次路演并录制后，视频、音频和共享屏幕会出现在这里。</p>
        <router-link class="empty-action" to="/online-meeting">发起一场路演</router-link>
      </div>

      <div v-else-if="!loading && filteredRecordings.length === 0" class="archive-empty compact">
        <span class="archive-empty__icon"><Search /></span>
        <h2>没有匹配的录制</h2>
        <p>换一个关键词或状态筛选，再找找看。</p>
      </div>

      <article
        v-for="(rec, index) in filteredRecordings"
        :key="rec.id"
        class="recording-row"
        :class="{ active: playingRecId === rec.id }"
      >
        <div class="row-index">{{ String(index + 1).padStart(2, '0') }}</div>

        <div class="recording-body">
          <div class="recording-summary">
            <div class="summary-main">
              <div class="recording-topline">
                <div>
                  <p class="row-kicker">{{ rec.sourceLabel || (rec.source === 'AI_UPLOAD' ? '评分视频' : '路演录制') }}</p>
                  <h2>{{ displayTitle(rec) }}</h2>
                </div>
                <span class="status-pill" :class="statusClass(rec.status)">
                  {{ statusText(rec.status) }}
                </span>
              </div>

              <div class="recording-meta">
                <span>
                  <el-icon><Clock /></el-icon>
                  {{ formatDate(rec.recordedAt) }}
                </span>
                <span v-if="recordingSize(rec)">大小 {{ formatSize(recordingSize(rec)) }}</span>
                <span v-if="rec.durationSeconds">时长 {{ formatDuration(rec.durationSeconds) }}</span>
                <span v-if="rec.filePath && rec.hasAudio" class="signal-good">含音频轨道</span>
                <span v-if="rec.meetingId">路演编号 {{ rec.meetingId }}</span>
                <span class="recording-id">录制编号 {{ rec.id }}</span>
              </div>
            </div>

            <button class="detail-toggle" type="button" @click="toggleRecording(rec.id)">
              <span>{{ isRecordingExpanded(rec.id) ? '收起' : '展开' }}</span>
              <svg
                class="detail-chevron"
                :class="{ open: isRecordingExpanded(rec.id) }"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M7 10l5 5 5-5" />
              </svg>
            </button>
          </div>

          <div v-if="isRecordingExpanded(rec.id)" class="recording-detail">
            <p v-if="rec.errorMessage && statusGroup(rec.status) === 'FAILED'" class="recording-error">
              {{ rec.errorMessage }}
            </p>
            <div class="asset-actions">
              <button
                v-if="hasMainVideo(rec)"
                class="asset-btn primary"
                type="button"
                :class="{ active: playingRecId === rec.id && playbackType === 'video' }"
                :disabled="!isPlaybackReady(rec)"
                @click="playFile(rec.id, 'video')"
              >
                <el-icon><VideoCamera /></el-icon>
                <span>回放视频</span>
                <small>主画面</small>
              </button>
              <button
                v-if="rec.audioFile"
                class="asset-btn"
                type="button"
                :class="{ active: playingRecId === rec.id && playbackType === 'audio' }"
                @click="playFile(rec.id, 'audio')"
              >
                <el-icon><Microphone /></el-icon>
                <span>音频</span>
                <small>声音</small>
              </button>
              <button
                v-if="rec.cameraFile"
                class="asset-btn"
                type="button"
                :class="{ active: playingRecId === rec.id && playbackType === 'camera' }"
                @click="playFile(rec.id, 'camera')"
              >
                <el-icon><VideoCamera /></el-icon>
                <span>摄像头</span>
                <small>人物画面</small>
              </button>
              <button
                v-if="rec.screenFile"
                class="asset-btn"
                type="button"
                :class="{ active: playingRecId === rec.id && playbackType === 'screen' }"
                @click="playFile(rec.id, 'screen')"
              >
                <el-icon><Monitor /></el-icon>
                <span>屏幕共享</span>
                <small>共享画面</small>
              </button>

              <button
                v-if="rec.source !== 'AI_UPLOAD'"
                class="delete-action"
                type="button"
                @click="deleteRecording(rec.id)"
              >
                <el-icon><Delete /></el-icon>
                <span>删除</span>
              </button>
            </div>

            <div v-if="playingRecId === rec.id && playbackUrl" class="playback">
              <div class="playback-header">
                <span>{{ playbackTypeLabel(playbackType) }}</span>
                <button type="button" @click="playFile(rec.id, playbackType)">关闭回放</button>
              </div>

              <div v-if="playbackType !== 'audio'" class="video-player">
                <video
                  :ref="setVideoRef"
                  :src="playbackUrl"
                  class="playback-video"
                  playsinline
                  preload="metadata"
                  @loadedmetadata="syncVideoState"
                  @timeupdate="syncVideoState"
                  @play="isVideoPlaying = true"
                  @pause="isVideoPlaying = false"
                  @ended="handleVideoEnded"
                  @click="toggleVideoPlayback"
                />
                <div class="custom-controls">
                  <button class="control-btn" type="button" @click="toggleVideoPlayback">
                    <el-icon>
                      <VideoPause v-if="isVideoPlaying" />
                      <VideoPlay v-else />
                    </el-icon>
                  </button>
                  <span class="time-text">{{ formatPlayerTime(currentTime) }}</span>
                  <input
                    class="progress-range"
                    type="range"
                    min="0"
                    :max="videoDuration || 0"
                    step="0.1"
                    :value="currentTime"
                    :style="{ '--progress': progressPercent + '%' }"
                    @input="seekVideo"
                  />
                  <span class="time-text">{{ formatPlayerTime(videoDuration) }}</span>
                  <button class="control-btn" type="button" @click="toggleFullscreen">
                    <el-icon><FullScreen /></el-icon>
                  </button>
                </div>
              </div>
              <audio
                v-else
                :src="playbackUrl"
                controls
                class="playback-audio"
              />
            </div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock,
  Delete,
  FullScreen,
  Microphone,
  Monitor,
  Refresh,
  Search,
  VideoCamera,
  VideoPause,
  VideoPlay
} from '@element-plus/icons-vue'
import request from '../utils/request'
import { withAuthMediaUrl } from '../utils/mediaUrl'

const recordings = ref([])
const loading = ref(false)
const playingRecId = ref(null)
const playbackUrl = ref(null)
const playbackType = ref('')
const videoRef = ref(null)
const isVideoPlaying = ref(false)
const currentTime = ref(0)
const videoDuration = ref(0)
const query = ref('')
const activeStatus = ref('ALL')
const expandedRecordings = ref(new Set())

const progressPercent = computed(() => {
  if (!videoDuration.value) return 0
  return Math.min(100, Math.max(0, (currentTime.value / videoDuration.value) * 100))
})

const readyCount = computed(() => recordings.value.filter(rec => isPlaybackReady(rec)).length)
const processingCount = computed(() => recordings.value.filter(rec => statusGroup(rec.status) === 'PROCESSING').length)
const failedCount = computed(() => recordings.value.filter(rec => statusGroup(rec.status) === 'FAILED').length)
const legacyCount = computed(() => recordings.value.filter(rec => statusGroup(rec.status) === 'LEGACY').length)
const totalSizeBytes = computed(() => recordings.value.reduce((sum, rec) => sum + recordingSize(rec), 0))
const totalDurationSeconds = computed(() => recordings.value.reduce((sum, rec) => sum + (Number(rec.durationSeconds) || 0), 0))

const statusTabs = computed(() => {
  const tabs = [
    { key: 'ALL', label: '全部', code: 'ALL', count: recordings.value.length },
    { key: 'READY', label: '可回放', code: 'READY', count: readyCount.value },
    { key: 'PROCESSING', label: '生成中', code: 'BUILDING', count: processingCount.value },
    { key: 'FAILED', label: '异常', code: 'FAILED', count: failedCount.value }
  ]
  if (legacyCount.value) tabs.push({ key: 'LEGACY', label: '旧版', code: 'LEGACY', count: legacyCount.value })
  return tabs
})

const filteredRecordings = computed(() => {
  const keyword = query.value.toLowerCase()
  return recordings.value.filter(rec => {
    const group = statusGroup(rec.status)
    const matchStatus = activeStatus.value === 'ALL'
      || activeStatus.value === rec.status
      || activeStatus.value === group
    if (!matchStatus) return false
    if (!keyword) return true
    return [
      rec.meetingTitle,
      rec.title,
      rec.sourceLabel,
      rec.teamName,
      rec.id,
      statusText(rec.status),
      formatDate(rec.recordedAt)
    ].some(item => String(item || '').toLowerCase().includes(keyword))
  })
})

function isPlaybackReady(rec) {
  if (!rec) return false
  if (rec.ready === true) return true
  if (rec.status === 'READY' && (rec.playUrl || rec.filePath || rec.streamApi || rec.cameraFile || rec.screenFile)) return true
  return false
}

function displayTitle(rec) {
  return rec?.meetingTitle || rec?.title || '未知路演'
}

function hasMainVideo(rec) {
  return !!(rec?.playUrl || rec?.filePath || rec?.streamApi)
}

function setVideoRef(el) {
  videoRef.value = el || null
}

function isRecordingExpanded(id) {
  return expandedRecordings.value.has(id) || playingRecId.value === id
}

function expandRecording(id) {
  const next = new Set(expandedRecordings.value)
  next.add(id)
  expandedRecordings.value = next
}

function closePlayback() {
  if (playbackUrl.value?.startsWith('blob:')) URL.revokeObjectURL(playbackUrl.value)
  playingRecId.value = null
  playbackUrl.value = null
  playbackType.value = ''
  resetVideoState()
}

function toggleRecording(id) {
  const next = new Set(expandedRecordings.value)
  if (isRecordingExpanded(id)) {
    next.delete(id)
    if (playingRecId.value === id) closePlayback()
  } else {
    next.add(id)
  }
  expandedRecordings.value = next
}

onMounted(fetchRecordings)
onUnmounted(() => {
  if (playbackUrl.value?.startsWith('blob:')) URL.revokeObjectURL(playbackUrl.value)
})

async function fetchRecordings() {
  loading.value = true
  try {
    const res = await request.get('/api/recording/my')
    recordings.value = res.data || []
  } catch (e) {
    ElMessage.error('加载录制列表失败')
  } finally {
    loading.value = false
  }
}

async function playFile(recId, fileType) {
  try {
    // 同一个文件再次点击则关闭
    if (playingRecId.value === recId && playbackType.value === fileType) {
      closePlayback()
      return
    }
    expandRecording(recId)
    if (playbackUrl.value?.startsWith('blob:')) URL.revokeObjectURL(playbackUrl.value)
    resetVideoState()

    const rec = recordings.value.find((r) => String(r.id) === String(recId))
    // 统一回放库：上传评分视频可直接用 playUrl（/uploads/...），避免重复录制
    const directUrl = fileType === 'audio'
      ? null
      : (rec?.playUrl || (String(rec?.filePath || '').startsWith('/uploads/') ? rec.filePath : ''))
    if (directUrl) {
      playbackUrl.value = withAuthMediaUrl(directUrl)
      playbackType.value = fileType
      playingRecId.value = recId
      await nextTick()
      syncVideoState()
      return
    }

    // 会议录制：走鉴权 stream；兼容旧数字 id 与新的 mr- 前缀
    const streamId = rec?.recordingId || String(recId).replace(/^mr-/, '')
    const streamPath = rec?.streamApi || `/api/recording/${streamId}/stream?file=${fileType}`
    const res = await request.get(streamPath, {
      responseType: 'blob',
      timeout: 60000
    })
    const blob = res instanceof Blob ? res : res.data
    const expectedType = fileType === 'audio' ? 'audio/webm' : 'video/webm'
    const playableBlob = blob.type && blob.type !== 'application/octet-stream'
      ? blob
      : new Blob([blob], { type: expectedType })
    playbackUrl.value = URL.createObjectURL(playableBlob)
    playbackType.value = fileType
    playingRecId.value = recId
    await nextTick()
    syncVideoState()
  } catch (e) {
    ElMessage.error('获取播放地址失败')
  }
}

function resetVideoState() {
  isVideoPlaying.value = false
  currentTime.value = 0
  videoDuration.value = 0
}

function syncVideoState() {
  const video = videoRef.value
  if (!(video instanceof HTMLVideoElement)) return
  currentTime.value = Number.isFinite(video.currentTime) ? video.currentTime : 0
  videoDuration.value = Number.isFinite(video.duration) ? video.duration : 0
  isVideoPlaying.value = !video.paused && !video.ended
}

function toggleVideoPlayback() {
  const video = videoRef.value
  if (!(video instanceof HTMLVideoElement)) return
  if (video.paused || video.ended) {
    video.play().catch(() => ElMessage.error('播放失败'))
  } else {
    video.pause()
  }
}

function seekVideo(event) {
  const video = videoRef.value
  if (!(video instanceof HTMLVideoElement)) return
  const nextTime = Number(event.target.value)
  if (!Number.isFinite(nextTime)) return
  video.currentTime = nextTime
  currentTime.value = nextTime
}

function handleVideoEnded() {
  isVideoPlaying.value = false
  syncVideoState()
}

function toggleFullscreen() {
  const video = videoRef.value
  if (!(video instanceof HTMLVideoElement)) return
  if (document.fullscreenElement) {
    document.exitFullscreen?.()
  } else {
    video.requestFullscreen?.()
  }
}

async function deleteRecording(id) {
  try {
    const rec = recordings.value.find((r) => String(r.id) === String(id))
    if (rec?.source === 'AI_UPLOAD') {
      ElMessage.warning('评分视频请在评分任务中管理，不支持在此删除')
      return
    }
    await ElMessageBox.confirm('确定删除此录制文件？此操作不可恢复。', '确认删除', {
      type: 'warning'
    })
    const recordingId = rec?.recordingId || String(id).replace(/^mr-/, '')
    await request.delete(`/api/recording/${recordingId}`)
    ElMessage.success('已删除')
    recordings.value = recordings.value.filter(r => r.id !== id)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatDuration(sec) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}分${s}秒`
}

function formatPlayerTime(sec) {
  const total = Math.max(0, Math.floor(Number(sec) || 0))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function statusText(status) {
  const map = {
    STARTING: '启动中',
    RECORDING: '录制中',
    PROCESSING: '生成中',
    READY: '可回放',
    FAILED: '失败',
    MISSING: '文件缺失',
    STORAGE_UNAVAILABLE: '存储不可用'
  }
  return map[status] || '旧版录制'
}

function statusGroup(status) {
  if (['STARTING', 'RECORDING', 'PROCESSING'].includes(status)) return 'PROCESSING'
  if (status === 'READY') return 'READY'
  if (['FAILED', 'MISSING', 'STORAGE_UNAVAILABLE'].includes(status)) return 'FAILED'
  return 'LEGACY'
}

function statusClass(status) {
  return `status-${statusGroup(status).toLowerCase()}`
}

function playbackTypeLabel(type) {
  const map = {
    video: '主视频回放',
    audio: '音频轨道',
    camera: '摄像头画面',
    screen: '屏幕共享'
  }
  return map[type] || '录制回放'
}

function recordingSize(rec) {
  return Number(rec?.sizeBytes || rec?.audioSizeBytes || 0)
}
</script>

<style scoped>
.my-recordings {
  position: relative;
  min-height: calc(100vh - 72px);
  padding: 48px 32px 64px;
  color: var(--ds-ink, #1d1d1f);
  background-color: #ffffff;
  background-image: none;
  font-family: var(--ds-font-sans, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif);
  overflow: hidden;
}

.recording-grid-bg,
.recording-orbit {
  position: absolute;
  pointer-events: none;
}

.recording-grid-bg {
  inset: 0;
  z-index: 0;
  background-image:
    linear-gradient(rgba(240, 240, 250, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 240, 250, 0.045) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.82), transparent 86%);
}

.recording-orbit {
  width: 720px;
  height: 720px;
  right: -280px;
  top: 112px;
  z-index: 0;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 50%;
}

.recording-orbit::before,
.recording-orbit::after {
  content: "";
  position: absolute;
  border: 1px solid rgba(240, 240, 250, 0.075);
  border-radius: 50%;
}

.recording-orbit::before { inset: 108px; }
.recording-orbit::after { inset: 216px; }

.archive-hero,
.archive-telemetry,
.archive-command,
.recording-manifest {
  position: relative;
  z-index: 1;
  max-width: 1180px;
  margin: 0 auto;
}

.archive-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px;
  gap: 28px;
  align-items: end;
  padding: 38px 42px;
  border: 1px solid rgba(240, 240, 250, 0.16);
  background: rgba(240, 240, 250, 0.035);
}

.mission-kicker,
.row-kicker {
  margin: 0;
  color: rgba(240, 240, 250, 0.48);
  font-size: 11px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin: 16px 0 12px;
  color: #f0f0fa;
  font-size: 46px;
  line-height: 1.08;
  font-weight: 900;
  letter-spacing: 0;
}

.hero-subtitle {
  max-width: 640px;
  margin: 0;
  color: rgba(240, 240, 250, 0.62);
  font-size: 15px;
  line-height: 1.7;
  font-weight: 600;
}

.archive-signal {
  min-width: 200px;
  min-height: auto;
  padding: 18px;
  border: 1px solid rgba(124, 255, 178, 0.22);
  background: rgba(240, 240, 250, 0.04);
}

.archive-signal span,
.archive-signal small,
.metric-code {
  display: block;
  color: rgba(240, 240, 250, 0.42);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.archive-signal strong {
  display: block;
  margin-top: 16px;
  color: #7cffb2;
  font-size: 18px;
  font-weight: 850;
  letter-spacing: 0;
}

.archive-signal small {
  margin-top: 6px;
}

.archive-telemetry {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 28px;
  border: 1px solid rgba(240, 240, 250, 0.16);
  background: rgba(240, 240, 250, 0.035);
}

.metric-cell {
  display: flex;
  flex-direction: column;
  min-height: 104px;
  padding: 18px 20px;
  background: transparent;
}

.metric-cell + .metric-cell {
  border-left: 1px solid rgba(240, 240, 250, 0.12);
}

.metric-label {
  display: block;
  color: rgba(240, 240, 250, 0.78);
  font-size: 14px;
  font-weight: 780;
}

.metric-code {
  margin-top: 7px;
}

.metric-cell strong {
  display: block;
  margin-top: auto;
  color: #f0f0fa;
  font-size: 22px;
  line-height: 1;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.metric-note {
  display: block;
  margin-top: 6px;
  color: rgba(240, 240, 250, 0.42);
  font-size: 12px;
  font-weight: 700;
}

.archive-command {
  display: grid;
  grid-template-columns: minmax(260px, 330px) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: stretch;
  margin-top: 28px;
}

.search-console,
.refresh-action,
.status-switch {
  min-height: 58px;
  border: 1px solid rgba(240, 240, 250, 0.14);
  background: rgba(240, 240, 250, 0.035);
}

.search-console {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  color: rgba(240, 240, 250, 0.56);
}

.search-console input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  color: #f0f0fa;
  background: transparent;
  font-size: 15px;
  font-weight: 700;
}

.search-console input::placeholder {
  color: rgba(240, 240, 250, 0.34);
}

.status-switch {
  display: flex;
  overflow: hidden;
}

.status-switch button,
.refresh-action,
.asset-btn,
.delete-action,
.playback-header button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.status-switch button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-rows: auto auto;
  align-content: center;
  column-gap: 16px;
  flex: 1;
  min-width: 86px;
  min-height: 58px;
  padding: 10px 16px;
  color: rgba(240, 240, 250, 0.52);
  background: transparent;
  text-align: left;
  transition: background 0.18s ease, color 0.18s ease;
}

.status-switch button + button {
  border-left: 1px solid rgba(240, 240, 250, 0.12);
}

.status-switch button span {
  display: block;
  grid-column: 1;
  grid-row: 1;
  font-size: 14px;
  font-weight: 850;
  line-height: 1.2;
}

.status-switch button small {
  display: block;
  grid-column: 1;
  grid-row: 2;
  margin-top: 4px;
  color: rgba(240, 240, 250, 0.42);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.14em;
}

.status-switch button strong {
  display: block;
  grid-column: 2;
  grid-row: 1 / span 2;
  align-self: center;
  justify-self: end;
  margin: 0;
  color: rgba(240, 240, 250, 0.72);
  font-size: 18px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.status-switch button:hover,
.status-switch button.active {
  color: #f0f0fa;
  background: rgba(240, 240, 250, 0.08);
}

.status-switch button:hover strong,
.status-switch button.active strong {
  color: #f0f0fa;
}

.status-switch button.active {
  box-shadow: inset 0 -2px 0 #7cffb2;
}

.refresh-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 22px;
  color: #f0f0fa;
  font-weight: 850;
  transition: border-color 0.18s ease, transform 0.18s ease, color 0.18s ease;
}

.refresh-action:hover {
  color: #7cffb2;
  border-color: rgba(124, 255, 178, 0.38);
  transform: translateY(-1px);
}

.refresh-action:disabled {
  cursor: wait;
  opacity: 0.56;
}

.recording-manifest {
  min-height: 360px;
  margin-top: 18px;
}

.recording-row {
  position: relative;
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 0;
  margin-bottom: 14px;
  border: 1px solid rgba(244, 246, 255, 0.14);
  background:
    linear-gradient(110deg, rgba(244, 246, 255, 0.045), transparent 58%),
    rgba(8, 10, 13, 0.78);
  box-shadow: inset 0 0 28px rgba(255, 255, 255, 0.014);
  transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease;
}

.recording-row:hover,
.recording-row.active {
  border-color: rgba(112, 255, 174, 0.34);
  background:
    linear-gradient(110deg, rgba(112, 255, 174, 0.075), transparent 58%),
    rgba(8, 10, 13, 0.84);
}

.recording-row:hover {
  transform: translateY(-1px);
}

.row-index {
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(244, 246, 255, 0.12);
  color: rgba(244, 246, 255, 0.32);
  font-size: 18px;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.08em;
}

.recording-body {
  padding: 22px 28px;
}

.recording-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: center;
}

.summary-main {
  min-width: 0;
}

.recording-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.row-kicker {
  color: rgba(244, 246, 255, 0.38);
  font-size: 11px;
}

.recording-topline h2 {
  margin: 8px 0 0;
  color: #f4f6ff;
  font-size: clamp(22px, 2.2vw, 30px);
  line-height: 1.15;
  letter-spacing: 0;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 86px;
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(244, 246, 255, 0.18);
  border-radius: 999px;
  color: rgba(244, 246, 255, 0.68);
  background: rgba(244, 246, 255, 0.045);
  font-size: 13px;
  font-weight: 850;
}

.status-ready {
  color: #6effad;
  border-color: rgba(112, 255, 174, 0.34);
  background: rgba(112, 255, 174, 0.08);
}

.status-processing {
  color: #ffd27d;
  border-color: rgba(255, 210, 125, 0.34);
  background: rgba(255, 210, 125, 0.08);
}

.status-failed {
  color: #ff8a8a;
  border-color: rgba(255, 92, 92, 0.38);
  background: rgba(255, 92, 92, 0.09);
}

.recording-meta {
  display: flex;
  align-items: center;
  gap: 12px 18px;
  flex-wrap: wrap;
  margin-top: 14px;
  color: rgba(244, 246, 255, 0.48);
  font-size: 13px;
  font-weight: 760;
}

.recording-meta span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.signal-good {
  color: #6effad;
}

.recording-id {
  color: rgba(244, 246, 255, 0.3);
}

.detail-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-width: 72px;
  height: 36px;
  border: 0;
  color: rgba(124, 255, 178, 0.82);
  background: transparent;
  font: inherit;
  font-size: 14px;
  font-weight: 850;
  cursor: pointer;
  transition: color 0.18s ease, transform 0.18s ease;
}

.detail-toggle:hover {
  color: #7cffb2;
  transform: translateY(-1px);
}

.detail-toggle span {
  letter-spacing: 0.04em;
}

.detail-chevron {
  width: 18px;
  height: 18px;
  overflow: visible;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), filter 0.2s ease;
}

.detail-chevron.open {
  transform: rotate(180deg);
}

.detail-toggle:hover .detail-chevron {
  filter: drop-shadow(0 0 8px rgba(124, 255, 178, 0.38));
}

.recording-detail {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid rgba(240, 240, 250, 0.1);
}

.asset-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 0;
}

.asset-btn {
  display: inline-grid;
  grid-template-columns: 20px auto;
  grid-template-rows: auto auto;
  column-gap: 10px;
  min-width: 130px;
  min-height: 58px;
  padding: 10px 16px;
  border: 1px solid rgba(244, 246, 255, 0.16);
  color: rgba(244, 246, 255, 0.84);
  background: rgba(244, 246, 255, 0.045);
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.asset-btn .el-icon {
  grid-row: 1 / span 2;
  align-self: center;
  font-size: 18px;
}

.asset-btn span {
  font-size: 14px;
  font-weight: 850;
  line-height: 1.2;
}

.asset-btn small {
  color: rgba(244, 246, 255, 0.38);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.18em;
}

.asset-btn.primary,
.asset-btn:hover,
.asset-btn.active {
  color: #f4f6ff;
  border-color: rgba(112, 255, 174, 0.34);
  background: rgba(112, 255, 174, 0.08);
}

.asset-btn:hover,
.delete-action:hover {
  transform: translateY(-1px);
}

.asset-btn:disabled {
  cursor: not-allowed;
  color: rgba(244, 246, 255, 0.28);
  border-color: rgba(244, 246, 255, 0.1);
  background: rgba(244, 246, 255, 0.025);
  transform: none;
}

.delete-action {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 42px;
  margin-left: auto;
  padding: 0 16px;
  border: 1px solid rgba(255, 92, 92, 0.28);
  color: #ffb7b7;
  background: rgba(255, 92, 92, 0.055);
  font-weight: 850;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.delete-action:hover {
  border-color: rgba(255, 92, 92, 0.54);
  background: rgba(255, 92, 92, 0.12);
}

.archive-empty {
  display: grid;
  place-items: center;
  min-height: 360px;
  padding: 48px;
  border: 1px solid rgba(244, 246, 255, 0.14);
  background: rgba(8, 10, 13, 0.7);
  text-align: center;
}

.archive-empty.compact {
  min-height: 240px;
}

.archive-empty h2 {
  margin: 14px 0 8px;
  font-size: 32px;
}

.archive-empty p:last-child {
  max-width: 520px;
  margin: 0;
  color: rgba(244, 246, 255, 0.52);
  font-weight: 700;
}
.playback {
  margin-top: 26px;
  border: 1px solid rgba(244, 246, 255, 0.14);
  overflow: hidden;
  background: #050608;
}

.playback-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 52px;
  padding: 0 16px 0 18px;
  border-bottom: 1px solid rgba(244, 246, 255, 0.12);
  color: rgba(244, 246, 255, 0.72);
  background: rgba(244, 246, 255, 0.035);
  font-size: 13px;
  font-weight: 850;
}

.playback-header button {
  color: rgba(244, 246, 255, 0.58);
  background: transparent;
  font-weight: 850;
}

.playback-header button:hover {
  color: #6effad;
}
.video-player {
  position: relative;
  background: #050608;
}
.playback-video {
  display: block;
  width: 100%;
  max-height: min(560px, 58vh);
  background: #050608;
  cursor: pointer;
}
.playback-audio {
  width: 100%;
  min-height: 64px;
  padding: 18px;
  background: #050608;
}
.custom-controls {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  direction: ltr;
  display: grid;
  grid-template-columns: 42px 48px minmax(0, 1fr) 48px 42px;
  align-items: center;
  gap: 10px;
  min-height: 64px;
  padding: 14px 18px;
  color: #f4f6ff;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.82), rgba(0, 0, 0, 0.38), rgba(0, 0, 0, 0));
}
.control-btn {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #f4f6ff;
  background: rgba(244, 246, 255, 0.14);
  cursor: pointer;
}
.control-btn:hover {
  background: rgba(244, 246, 255, 0.22);
}
.time-text {
  min-width: 42px;
  color: rgba(244, 246, 255, 0.92);
  font-size: 13px;
  font-weight: 720;
  font-variant-numeric: tabular-nums;
  text-align: center;
}
.progress-range {
  direction: ltr;
  appearance: none;
  -webkit-appearance: none;
  width: 100%;
  height: 18px;
  margin: 0;
  background: transparent;
  cursor: pointer;
}
.progress-range::-webkit-slider-runnable-track {
  height: 5px;
  border-radius: 999px;
  background:
    linear-gradient(to right, #f4f6ff 0%, #f4f6ff var(--progress), rgba(244, 246, 255, 0.34) var(--progress), rgba(244, 246, 255, 0.34) 100%);
}
.progress-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  margin-top: -4.5px;
  border-radius: 50%;
  background: #f4f6ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.34);
}
.progress-range::-moz-range-track {
  height: 5px;
  border-radius: 999px;
  background: rgba(244, 246, 255, 0.34);
}
.progress-range::-moz-range-progress {
  height: 5px;
  border-radius: 999px;
  background: #f4f6ff;
}
.progress-range::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border: 0;
  border-radius: 50%;
  background: #f4f6ff;
}

:deep(.el-loading-mask) {
  background: rgba(3, 5, 7, 0.64);
  backdrop-filter: blur(8px);
}

:deep(.el-loading-spinner .path) {
  stroke: #6effad;
}

@media (max-width: 1180px) {
  .archive-hero {
    grid-template-columns: 1fr;
    gap: 28px;
    padding: 44px;
  }

  .archive-signal {
    max-width: 360px;
  }

  .archive-telemetry {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-cell + .metric-cell {
    border-left: 0;
  }

  .metric-cell:nth-child(even) {
    border-left: 1px solid rgba(240, 240, 250, 0.12);
  }

  .metric-cell:nth-child(n + 3) {
    border-top: 1px solid rgba(240, 240, 250, 0.12);
  }

  .archive-command {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .my-recordings {
    padding: 28px 16px 54px;
  }

  .archive-hero {
    min-height: 0;
    padding: 34px 24px;
  }

  .hero-copy h1 {
    font-size: 34px;
  }

  .hero-subtitle {
    font-size: 15px;
  }

  .archive-telemetry {
    grid-template-columns: 1fr;
  }

  .metric-cell {
    min-height: 112px;
    border-left: 0;
  }

  .metric-cell:nth-child(even) {
    border-left: 0;
  }

  .metric-cell + .metric-cell {
    border-top: 1px solid rgba(240, 240, 250, 0.12);
  }

  .status-switch {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-switch button {
    min-height: 54px;
  }

  .status-switch button + button {
    border-left: 0;
  }

  .recording-row {
    grid-template-columns: 1fr;
  }

  .row-index {
    justify-content: flex-start;
    min-height: 46px;
    padding-left: 22px;
    border-right: 0;
    border-bottom: 1px solid rgba(244, 246, 255, 0.12);
  }

  .recording-body {
    padding: 22px;
  }

  .recording-summary {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .recording-topline {
    display: grid;
  }

  .detail-toggle {
    width: 100%;
  }

  .asset-actions {
    align-items: stretch;
  }

  .asset-btn,
  .delete-action {
    flex: 1 1 100%;
    margin-left: 0;
  }

  .custom-controls {
    grid-template-columns: 38px 42px minmax(0, 1fr) 42px 38px;
    gap: 8px;
    padding: 12px;
  }
}

/* Recording replay is a student workspace page, not a cyber control panel. */
.my-recordings {
  min-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  overflow: visible;
  color: var(--ds-ink, #1d1d1f);
  background: transparent;
  font-family: var(--ds-font-sans, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif);
}

.recording-grid-bg,
.recording-orbit {
  display: none;
}

.archive-hero,
.archive-telemetry,
.archive-command,
.recording-manifest {
  max-width: none;
  margin-left: 0;
  margin-right: 0;
}

.archive-hero {
  grid-template-columns: minmax(0, 1fr) 210px;
  align-items: center;
  padding: 28px 32px;
  border-color: var(--ds-card-border, var(--ds-line));
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-card-bg, var(--ds-surface));
  box-shadow: var(--ds-card-shadow, none);
}

.mission-kicker,
.row-kicker,
.metric-code,
.status-switch button small {
  color: var(--ds-orange-800, #b12f0a);
  letter-spacing: 0;
}

.hero-copy h1 {
  margin: 10px 0 8px;
  color: var(--ds-ink, #1d1d1f);
  font-size: var(--ds-text-h1, 28px);
  line-height: 1.24;
  font-weight: 700;
}

.hero-subtitle {
  color: var(--ds-muted, #6e6e73);
  line-height: 1.65;
}

.archive-signal {
  min-height: 116px;
  border-color: var(--ds-orange-100, #fee9df);
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-orange-50, #fff7f2);
}

.archive-signal span,
.archive-signal small {
  color: var(--ds-muted, #6e6e73);
}

.archive-signal strong {
  margin-top: 12px;
  color: var(--ds-orange-800, #b12f0a);
}

.archive-telemetry {
  margin-top: 14px;
  overflow: hidden;
  border-color: var(--ds-line, rgba(28, 26, 22, 0.09));
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-surface, rgba(255, 255, 255, 0.9));
}

.metric-cell {
  min-height: 92px;
}

.metric-cell + .metric-cell {
  border-left-color: rgba(0, 0, 0, 0.06);
}

.metric-label {
  color: var(--ds-muted, #6e6e73);
}

.metric-cell strong {
  color: var(--ds-ink, #1d1d1f);
}

.metric-note {
  color: var(--ds-faint, #9a9aa0);
}

.archive-command {
  margin-top: 14px;
}

.search-console,
.refresh-action,
.status-switch {
  min-height: 44px;
  overflow: hidden;
  border-color: var(--ds-line-strong, rgba(28, 26, 22, 0.13));
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-surface-solid, #fff);
}

.search-console {
  color: var(--ds-faint, #9a9aa0);
}

.search-console input {
  color: var(--ds-ink, #1d1d1f);
}

.search-console input::placeholder {
  color: var(--ds-faint, #9a9aa0);
}

.status-switch button {
  color: var(--ds-muted, #6e6e73);
}

.status-switch button + button {
  border-left-color: rgba(0, 0, 0, 0.06);
}

.status-switch button strong {
  color: var(--ds-ink, #1d1d1f);
}

.status-switch button:hover,
.status-switch button.active {
  color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-50, #fff7f2);
}

.status-switch button:hover strong,
.status-switch button.active strong {
  color: var(--ds-orange-800, #b12f0a);
}

.status-switch button.active {
  box-shadow: inset 0 0 0 1px var(--ds-orange-100, #fee9df);
}

.refresh-action {
  color: var(--ds-ink, #1d1d1f);
}

.refresh-action:hover {
  color: var(--ds-orange-800, #b12f0a);
  border-color: var(--ds-orange-action, #cf3d12);
  background: var(--ds-orange-50, #fff7f2);
  transform: none;
}

.recording-manifest {
  margin-top: 14px;
}

.recording-row,
.recording-row:hover,
.recording-row.active {
  overflow: hidden;
  border-color: var(--ds-line, rgba(28, 26, 22, 0.09));
  border-radius: var(--ds-radius-lg, 16px);
  background: var(--ds-surface, rgba(255, 255, 255, 0.9));
  box-shadow: var(--ds-card-shadow, none);
}

.recording-row:hover,
.recording-row.active {
  border-color: var(--ds-orange-100, #fee9df);
  background: var(--ds-surface-solid, #fff);
}

.recording-row:hover {
  transform: none;
}

.row-index {
  border-right-color: rgba(0, 0, 0, 0.06);
  color: var(--ds-faint, #9a9aa0);
  background: var(--ds-canvas, #f3f4f6);
}

.recording-topline h2 {
  color: var(--ds-ink, #1d1d1f);
  font-size: var(--ds-text-h3, 16px);
}

.recording-meta,
.recording-id {
  color: var(--ds-muted, #6e6e73);
}

.signal-good,
.status-ready {
  color: var(--ds-green, #0f9f6e);
}

.status-ready {
  border-color: rgba(15, 159, 110, 0.22);
  background: rgba(15, 159, 110, 0.08);
}

.status-processing {
  color: #a96800;
  border-color: rgba(169, 104, 0, 0.2);
  background: rgba(255, 176, 32, 0.1);
}

.status-failed {
  color: #c43d35;
  border-color: rgba(196, 61, 53, 0.2);
  background: rgba(196, 61, 53, 0.08);
}

.detail-toggle {
  min-height: 34px;
  color: var(--ds-orange-800, #b12f0a);
}

.detail-toggle:hover {
  color: var(--ds-orange-deep, #d94112);
  transform: none;
}

.recording-detail {
  border-top-color: rgba(0, 0, 0, 0.07);
}

.asset-btn {
  border-color: rgba(0, 0, 0, 0.08);
  border-radius: var(--ds-radius-md, 12px);
  color: var(--ds-ink, #1d1d1f);
  background: #fafafa;
}

.asset-btn small {
  color: var(--ds-faint, #9a9aa0);
}

.asset-btn.primary,
.asset-btn:hover,
.asset-btn.active {
  color: var(--ds-orange-800, #b12f0a);
  border-color: var(--ds-orange-action, #cf3d12);
  background: var(--ds-orange-50, #fff7f2);
}

.asset-btn:hover,
.delete-action:hover {
  transform: none;
}

.asset-btn:disabled {
  color: var(--ds-faint, #9a9aa0);
  border-color: rgba(0, 0, 0, 0.06);
  background: #f5f5f7;
}

.delete-action {
  border-color: rgba(196, 61, 53, 0.2);
  border-radius: var(--ds-radius-pill, 999px);
  color: var(--ds-red, #d83a45);
  background: var(--ds-surface-solid, #fff);
}

.archive-empty {
  border-color: rgba(0, 0, 0, 0.07);
  border-radius: var(--ds-radius-lg, 16px);
  color: var(--ds-ink, #1d1d1f);
  background: var(--ds-surface, rgba(255, 255, 255, 0.9));
}

.archive-empty h2 {
  color: var(--ds-ink, #1d1d1f);
}

.archive-empty p:last-child {
  color: var(--ds-muted, #6e6e73);
}

:deep(.el-loading-mask) {
  background: rgba(245, 245, 247, 0.7);
}

:deep(.el-loading-spinner .path) {
  stroke: var(--ds-orange-action, #cf3d12);
}

.search-console:focus-within,
.status-switch button:focus-visible,
.refresh-action:focus-visible,
.detail-toggle:focus-visible,
.asset-btn:focus-visible,
.delete-action:focus-visible,
.control-btn:focus-visible {
  outline: 2px solid var(--ds-orange-action, #cf3d12);
  outline-offset: 2px;
}

.status-switch button,
.refresh-action,
.detail-toggle,
.asset-btn,
.delete-action,
.control-btn {
  transition: color 150ms ease-in-out, background-color 150ms ease-in-out, border-color 150ms ease-in-out;
}

.refresh-action:disabled,
.asset-btn:disabled,
.control-btn:disabled {
  color: var(--ds-disabled-fg, var(--ds-faint, #9aa1ad));
  border-color: var(--ds-disabled-border, #e5e7eb);
  background: var(--ds-disabled-bg, #f4f4f5);
  cursor: not-allowed;
}
</style>

<style scoped>
/* Final workspace alignment: same spacing, surfaces and controls as Home/Training. */
.my-recordings {
  width: 100%;
  min-height: 100%;
  padding: 0 0 var(--ds-space-6, 24px);
  overflow: visible;
  color: var(--ds-ink);
  background: transparent;
  font-family: var(--ds-font-sans);
}

.archive-page-head {
  margin-bottom: var(--ds-space-5, 20px);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--ds-space-5, 20px);
}

.archive-page-head h1 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-h1, 28px);
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.archive-page-head p {
  margin: 6px 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption, 13px);
  line-height: 1.55;
}

.archive-head-actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 8px);
}

.archive-signal {
  min-width: 0;
  min-height: 36px;
  padding: 0 12px;
  border: 0;
  border-radius: var(--ds-radius-pill);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ds-muted);
  background: transparent;
  font-size: var(--ds-text-label, 12px);
  font-weight: 700;
}

.archive-signal i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ds-faint);
}

.archive-signal i.ready {
  background: var(--ds-green);
  box-shadow: 0 0 0 3px rgba(15, 159, 110, 0.12);
}

.return-meeting-action,
.refresh-action {
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: var(--ds-radius-pill);
  color: var(--ds-ink-2);
  background: var(--ds-btn-secondary-bg);
  font-size: var(--ds-text-caption, 13px);
  font-weight: 700;
}

.return-meeting-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  white-space: nowrap;
}

.return-meeting-action:hover,
.refresh-action:hover:not(:disabled) {
  color: var(--ds-orange-deep);
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-btn-secondary-bg-hover);
}

.refresh-action:disabled {
  color: var(--ds-btn-disabled-fg);
  border-color: var(--ds-btn-disabled-border);
  background: var(--ds-btn-disabled-bg);
  opacity: 1;
}

.archive-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.archive-overview > div {
  min-height: 82px;
  padding: 16px 20px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-content: center;
  align-items: baseline;
  gap: 7px 12px;
}

.archive-overview > div + div {
  border-left: 1px solid var(--ds-line);
}

.archive-overview span {
  color: var(--ds-muted);
  font-size: var(--ds-text-label, 12px);
  font-weight: 600;
}

.archive-overview strong {
  color: var(--ds-ink);
  font-size: 22px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.archive-overview small {
  grid-column: 1 / -1;
  color: var(--ds-faint);
  font-size: var(--ds-text-micro, 11px);
}

.archive-command {
  grid-template-columns: minmax(220px, 1fr) auto;
  gap: var(--ds-space-3, 12px);
  margin-top: var(--ds-space-4, 16px);
}

.search-console,
.status-switch {
  min-height: 44px;
  border: 1px solid var(--ds-line-strong);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
}

.search-console {
  padding: 0 14px;
  color: var(--ds-faint);
}

.search-console:focus-within {
  border-color: var(--ds-orange-action);
  box-shadow: 0 0 0 3px rgba(207, 61, 18, 0.1);
}

.search-console input {
  color: var(--ds-ink);
  font-size: var(--ds-text-body-sm, 14px);
  font-weight: 500;
}

.search-console input::placeholder {
  color: var(--ds-faint);
}

.status-switch {
  padding: 3px;
  gap: 2px;
}

.status-switch button {
  min-width: 78px;
  min-height: 36px;
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  border-radius: 9px;
  color: var(--ds-muted);
  background: transparent;
  text-align: center;
}

.status-switch button + button {
  border-left: 0;
}

.status-switch button span,
.status-switch button strong {
  display: inline;
  color: inherit;
  font-size: var(--ds-text-label, 12px);
  font-weight: 700;
}

.status-switch button.active,
.status-switch button:hover {
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
  box-shadow: none;
}

.recording-manifest {
  min-height: 0;
  margin-top: var(--ds-space-4, 16px);
}

.archive-empty {
  min-height: 320px;
  padding: 48px 24px;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.archive-empty.compact {
  min-height: 240px;
}

.archive-empty__icon {
  width: 52px;
  height: 52px;
  margin-bottom: 18px;
  border-radius: var(--ds-radius-lg);
  display: grid;
  place-items: center;
  color: var(--ds-orange-action);
  background: var(--ds-orange-wash);
}

.archive-empty__icon svg {
  width: 24px;
  height: 24px;
}

.archive-empty h2 {
  margin: 0 0 10px;
  color: var(--ds-ink);
  font-size: var(--ds-text-h2, 22px);
}

.archive-empty p:last-of-type {
  max-width: 460px;
  margin: 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-body-sm, 14px);
  font-weight: 500;
  line-height: 1.7;
}

.empty-action {
  min-height: 40px;
  margin-top: 20px;
  padding: 0 18px;
  border-radius: var(--ds-radius-pill);
  display: inline-flex;
  align-items: center;
  color: var(--ds-btn-primary-fg);
  background: var(--ds-btn-primary-bg);
  font-size: var(--ds-text-body-sm, 14px);
  font-weight: 700;
  text-decoration: none;
}

.recording-row,
.recording-row:hover,
.recording-row.active {
  grid-template-columns: 54px minmax(0, 1fr);
  margin-bottom: var(--ds-space-3, 12px);
  overflow: hidden;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  transform: none;
}

.recording-row:hover,
.recording-row.active {
  border-color: var(--ds-orange-100);
  background: var(--ds-surface-solid);
}

.row-index {
  border-right: 1px solid var(--ds-line);
  color: var(--ds-faint);
  background: var(--ds-input-readonly-bg);
  font-size: var(--ds-text-label, 12px);
}

.recording-body {
  padding: 20px 24px;
}

.row-kicker {
  color: var(--ds-orange-deep);
  font-size: var(--ds-text-micro, 11px);
  letter-spacing: 0;
}

.recording-topline h2 {
  color: var(--ds-ink);
  font-size: var(--ds-text-h3, 16px);
}

.recording-meta,
.recording-id {
  color: var(--ds-muted);
  font-size: var(--ds-text-label, 12px);
}

.detail-toggle {
  min-height: 40px;
  color: var(--ds-orange-deep);
}

.detail-toggle:hover {
  color: var(--ds-orange-action);
  transform: none;
}

.recording-detail {
  border-top-color: var(--ds-line);
}

.recording-error {
  margin: 0 0 14px;
  padding: 10px 12px;
  border: 1px solid var(--ds-btn-danger-border);
  border-radius: var(--ds-radius-md);
  color: var(--ds-btn-danger-fg);
  background: var(--ds-btn-danger-bg);
  font-size: var(--ds-text-label, 12px);
  line-height: 1.5;
}

.asset-btn {
  border-color: var(--ds-line-strong);
  border-radius: var(--ds-radius-md);
  color: var(--ds-ink-2);
  background: var(--ds-surface-solid);
}

.asset-btn small {
  color: var(--ds-muted);
  letter-spacing: 0;
}

.asset-btn.primary,
.asset-btn:hover,
.asset-btn.active {
  color: var(--ds-orange-deep);
  border-color: var(--ds-orange-100);
  background: var(--ds-orange-wash);
}

.asset-btn:hover,
.delete-action:hover {
  transform: none;
}

.asset-btn:disabled {
  color: var(--ds-btn-disabled-fg);
  border-color: var(--ds-btn-disabled-border);
  background: var(--ds-btn-disabled-bg);
}

.delete-action {
  min-height: 40px;
  border: 1px solid var(--ds-btn-danger-border);
  border-radius: var(--ds-radius-pill);
  color: var(--ds-btn-danger-fg);
  background: var(--ds-btn-danger-bg);
}

.delete-action:hover {
  border-color: var(--ds-red);
  background: var(--ds-btn-danger-bg-hover);
}

.playback {
  border-radius: var(--ds-radius-md);
}

:is(.return-meeting-action, .refresh-action, .status-switch button, .detail-toggle, .asset-btn, .delete-action, .empty-action):focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

:deep(.el-loading-mask) {
  background: rgba(243, 244, 246, 0.78);
  backdrop-filter: none;
}

:deep(.el-loading-spinner .path) {
  stroke: var(--ds-orange-action);
}

@media (max-width: 900px) {
  .archive-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .archive-overview > div:nth-child(3) {
    border-left: 0;
  }

  .archive-overview > div:nth-child(n + 3) {
    border-top: 1px solid var(--ds-line);
  }

  .archive-command {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .archive-page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .archive-head-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .archive-signal {
    flex: 1 1 100%;
  }

  .return-meeting-action,
  .refresh-action {
    flex: 1 1 0;
    margin-left: 0;
  }

  .archive-overview {
    grid-template-columns: 1fr;
  }

  .archive-overview > div + div,
  .archive-overview > div:nth-child(3) {
    border-left: 0;
    border-top: 1px solid var(--ds-line);
  }

  .status-switch {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-switch button {
    min-width: 0;
  }

  .recording-row,
  .recording-row:hover,
  .recording-row.active {
    grid-template-columns: 1fr;
  }

  .row-index {
    min-height: 38px;
    padding-left: 20px;
    justify-content: flex-start;
    border-right: 0;
    border-bottom: 1px solid var(--ds-line);
  }

  .recording-body {
    padding: 18px 20px;
  }

  .recording-summary,
  .recording-topline {
    grid-template-columns: 1fr;
  }
}
</style>
