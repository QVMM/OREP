<template>
  <div class="training-video-player" @contextmenu.prevent @dragstart.prevent>
    <div ref="frameRef" class="training-video-player__frame">
      <video
        ref="videoRef"
        :src="playbackSrc"
        preload="metadata"
        playsinline
        controlslist="nodownload noremoteplayback noplaybackrate"
        disablepictureinpicture
        disableremoteplayback
        :aria-label="resource.title"
        @loadedmetadata="handleLoadedMetadata"
        @play="handlePlay"
        @pause="handlePause"
        @ended="handleEnded"
        @timeupdate="handleTimeUpdate"
        @seeking="guardSeeking"
        @ratechange="enforcePlaybackRate"
        @click="togglePlayback"
      ></video>

      <span v-if="playing" class="training-video-player__watermark" aria-hidden="true">{{ watermarkText }}</span>

      <button
        v-if="!playing"
        type="button"
        class="training-video-player__center-play"
        aria-label="播放视频"
        @click.stop="togglePlayback"
      >
        <VideoPlay />
      </button>

      <div class="training-video-player__controls" @click.stop>
        <button type="button" :aria-label="playing ? '暂停视频' : '播放视频'" @click="togglePlayback">
          <VideoPause v-if="playing" />
          <VideoPlay v-else />
        </button>
        <span class="training-video-player__time">{{ formatClock(currentTime) }}</span>
        <input
          type="range"
          min="0"
          :max="Math.max(1, duration)"
          step="0.1"
          :value="currentTime"
          :style="{ '--played': `${playedPercent}%`, '--verified': `${verifiedPercent}%` }"
          aria-label="播放进度"
          @input="seekVideo"
        />
        <span class="training-video-player__time">{{ formatClock(duration) }}</span>
        <div class="training-video-player__volume">
          <button type="button" :aria-label="muted || volume === 0 ? '打开声音' : '静音'" @click="toggleMute">
            <Mute v-if="muted || volume === 0" />
            <Microphone v-else />
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            :value="muted ? 0 : volume"
            :style="{ '--volume': `${volumePercent}%` }"
            aria-label="音量"
            @input="changeVolume"
          />
        </div>
        <button type="button" :aria-label="fullscreenActive ? '退出全屏' : '全屏播放'" @click="toggleFullscreen">
          <FullScreen />
        </button>
      </div>
    </div>

    <div class="training-video-player__note">
      <span>受保护的学习视频</span>
      <p>连续播放才计入学习进度；可回看已学部分，不能向前跳过未学内容。</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { FullScreen, Microphone, Mute, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { useAuthStore } from '../../../stores/auth'
import { withAuthMediaUrl } from '../../../utils/mediaUrl'
import { resolveSeekRequest } from '../videoPlaybackPolicy'

const props = defineProps({
  resource: { type: Object, required: true }
})
const emit = defineEmits(['heartbeat', 'restricted'])

const authStore = useAuthStore()
const frameRef = ref(null)
const videoRef = ref(null)
const playing = ref(false)
const muted = ref(false)
const volume = ref(1)
const fullscreenActive = ref(false)
const currentTime = ref(0)
const localWatchedEnd = ref(0)
const duration = ref(0)
const verifiedEnd = ref(0)
const watermarkNow = ref(new Date())
const correctingSeek = ref(false)
let watermarkTimer

// <video> cannot send Authorization; learning media requires ?t= JWT
const playbackSrc = computed(() => withAuthMediaUrl(props.resource?.resourceUrl || ''))
const playedPercent = computed(() => duration.value > 0 ? Math.min(100, currentTime.value * 100 / duration.value) : 0)
const verifiedPercent = computed(() => duration.value > 0 ? Math.min(100, verifiedEnd.value * 100 / duration.value) : 0)
const volumePercent = computed(() => Math.round((muted.value ? 0 : volume.value) * 100))
const watermarkText = computed(() => {
  const user = authStore.user || {}
  const identity = user.username || user.name || `学员${user.id ? ` ${user.id}` : ''}`
  const date = watermarkNow.value
  const stamp = `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  return `${identity} · 竞赛大脑学习专用 · ${stamp}`
})

watch(
  () => [props.resource.maxWatchedPositionSeconds, props.resource.lastPositionSeconds],
  ([maxWatched, lastPosition]) => {
    verifiedEnd.value = Math.max(verifiedEnd.value, Number(maxWatched || 0), Number(lastPosition || 0))
  },
  { immediate: true }
)

onMounted(() => {
  watermarkTimer = window.setInterval(() => { watermarkNow.value = new Date() }, 60_000)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onBeforeUnmount(() => {
  if (watermarkTimer) window.clearInterval(watermarkTimer)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
})

function handleLoadedMetadata() {
  const video = videoRef.value
  if (!video || !Number.isFinite(video.duration)) return
  duration.value = video.duration
  verifiedEnd.value = Math.min(
    video.duration,
    Math.max(verifiedEnd.value, Number(props.resource.maxWatchedPositionSeconds || 0), Number(props.resource.lastPositionSeconds || 0))
  )
  const resumeAt = Math.min(Number(props.resource.lastPositionSeconds || 0), video.duration)
  if (resumeAt > 0 && resumeAt < video.duration - 2) {
    correctingSeek.value = true
    video.currentTime = resumeAt
    currentTime.value = resumeAt
    localWatchedEnd.value = Math.max(localWatchedEnd.value, resumeAt)
    queueMicrotask(() => { correctingSeek.value = false })
  }
}

function handlePlay() {
  playing.value = true
  emitHeartbeat(true, true)
}

function handlePause() {
  playing.value = false
  emitHeartbeat(true, false)
}

function handleEnded() {
  playing.value = false
  emitHeartbeat(true, false)
}

function handleTimeUpdate() {
  const video = videoRef.value
  if (!video) return
  currentTime.value = video.currentTime
  if (!video.seeking) {
    localWatchedEnd.value = Math.max(localWatchedEnd.value, video.currentTime)
  }
  if (!video.seeking && !video.paused) {
    emitHeartbeat(false, false)
  }
}

function guardSeeking() {
  const video = videoRef.value
  if (!video || correctingSeek.value) return
  const resolution = resolveSeekRequest({
    requested: video.currentTime,
    current: localWatchedEnd.value,
    duration: duration.value || video.duration,
    serverVerifiedEnd: verifiedEnd.value,
    localWatchedEnd: localWatchedEnd.value
  })
  if (!resolution.accepted) {
    correctingSeek.value = true
    video.currentTime = resolution.position
    currentTime.value = video.currentTime
    emit('restricted')
    queueMicrotask(() => { correctingSeek.value = false })
    return
  }
  currentTime.value = video.currentTime
  emitHeartbeat(true, true)
}

function seekVideo(event) {
  const video = videoRef.value
  if (!video) return
  const requested = Number(event.target.value || 0)
  const resolution = resolveSeekRequest({
    requested,
    current: currentTime.value,
    duration: duration.value || video.duration,
    serverVerifiedEnd: verifiedEnd.value,
    localWatchedEnd: localWatchedEnd.value
  })
  if (!resolution.accepted) {
    event.target.value = String(currentTime.value)
    emit('restricted')
    return
  }
  video.currentTime = resolution.position
  currentTime.value = video.currentTime
}

function enforcePlaybackRate() {
  const video = videoRef.value
  if (video && video.playbackRate !== 1) video.playbackRate = 1
}

async function togglePlayback() {
  const video = videoRef.value
  if (!video) return
  if (video.paused) {
    try {
      await video.play()
    } catch {
      playing.value = false
    }
  } else {
    video.pause()
  }
}

function toggleMute() {
  const video = videoRef.value
  if (!video) return
  video.muted = !video.muted
  muted.value = video.muted
}

function changeVolume(event) {
  const video = videoRef.value
  if (!video) return
  const nextVolume = Math.max(0, Math.min(1, Number(event.target.value || 0)))
  video.volume = nextVolume
  video.muted = nextVolume === 0
  volume.value = nextVolume
  muted.value = video.muted
}

function handleFullscreenChange() {
  fullscreenActive.value = document.fullscreenElement === frameRef.value
}

async function toggleFullscreen() {
  const target = frameRef.value
  if (document.fullscreenElement) {
    await document.exitFullscreen?.()
    return
  }
  if (target?.requestFullscreen) await target.requestFullscreen()
}

function emitHeartbeat(force, reset) {
  if (!videoRef.value) return
  emit('heartbeat', { video: videoRef.value, force, reset })
}

function formatClock(value) {
  const seconds = Math.max(0, Math.floor(Number(value || 0)))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainder = seconds % 60
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${minutes}:${String(remainder).padStart(2, '0')}`
}
</script>

<style scoped>
.training-video-player {
  min-width: 0;
}

.training-video-player__frame {
  position: relative;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 13px;
  background: #111;
  box-shadow: 0 8px 24px rgba(28, 24, 21, .14);
  isolation: isolate;
}

.training-video-player video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #111;
}

.training-video-player__watermark {
  position: absolute;
  z-index: 2;
  left: 50%;
  top: 18%;
  max-width: 72%;
  padding: 5px 8px;
  border: 1px solid rgba(255, 255, 255, .12);
  border-radius: 6px;
  color: rgba(255, 255, 255, .4);
  background: rgba(16, 18, 22, .12);
  font-size: 9px;
  line-height: 1;
  letter-spacing: .04em;
  white-space: nowrap;
  pointer-events: none;
  transform: translate(-50%, -50%);
  animation: training-watermark-drift 18s ease-in-out infinite alternate;
}

.training-video-player__center-play {
  position: absolute;
  z-index: 3;
  left: 50%;
  top: 50%;
  width: 52px;
  height: 52px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, .4);
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: rgba(18, 20, 24, .62);
  backdrop-filter: blur(8px);
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition: transform 160ms ease, background 160ms ease;
}

.training-video-player__center-play:hover {
  background: rgba(217, 57, 20, .86);
  transform: translate(-50%, -50%) scale(1.05);
}

.training-video-player__center-play svg {
  width: 24px;
}

.training-video-player__controls {
  position: absolute;
  z-index: 4;
  right: 0;
  bottom: 0;
  left: 0;
  min-height: 48px;
  padding: 17px 12px 7px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  background: linear-gradient(transparent, rgba(10, 12, 16, .88));
}

.training-video-player__controls button {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 0;
  border-radius: 8px;
  display: grid;
  flex: 0 0 30px;
  place-items: center;
  color: #fff;
  background: transparent;
  cursor: pointer;
}

.training-video-player__controls button:hover,
.training-video-player__controls button:focus-visible {
  background: rgba(255, 255, 255, .14);
  outline: none;
}

.training-video-player__controls svg {
  width: 18px;
}

.training-video-player__controls input[type="range"] {
  height: 4px;
  min-width: 0;
  margin: 0;
  flex: 1 1 auto;
  border-radius: 999px;
  appearance: none;
  background:
    linear-gradient(90deg,
      var(--ds-orange) 0 var(--played),
      rgba(255, 255, 255, .52) var(--played) var(--verified),
      rgba(255, 255, 255, .22) var(--verified) 100%);
  cursor: pointer;
}

.training-video-player__controls input[type="range"]::-webkit-slider-thumb {
  width: 12px;
  height: 12px;
  border: 2px solid #fff;
  border-radius: 50%;
  appearance: none;
  background: var(--ds-orange);
  box-shadow: 0 1px 4px rgba(0, 0, 0, .32);
}

.training-video-player__controls input[type="range"]:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 4px;
}

.training-video-player__volume {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 2px;
}

.training-video-player__volume input[type="range"] {
  width: 58px;
  flex: 0 0 58px;
  background: linear-gradient(90deg, #fff 0 var(--volume), rgba(255, 255, 255, .28) var(--volume) 100%);
}

.training-video-player__time {
  min-width: 32px;
  color: rgba(255, 255, 255, .88);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.training-video-player__note {
  min-height: 30px;
  padding: 7px 2px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  color: var(--ds-muted);
  font-size: 10px;
}

.training-video-player__note span {
  flex: 0 0 auto;
  color: var(--ds-ink-soft);
  font-weight: 750;
}

.training-video-player__note span::before {
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 50%;
  display: inline-block;
  background: #16a071;
  content: "";
  vertical-align: 1px;
}

.training-video-player__note p {
  margin: 0;
  text-align: right;
}

@keyframes training-watermark-drift {
  0% { left: 26%; top: 18%; }
  48% { left: 72%; top: 42%; }
  100% { left: 38%; top: 70%; }
}

@media (max-width: 620px) {
  .training-video-player__watermark {
    max-width: 84%;
    font-size: 8px;
  }

  .training-video-player__controls {
    gap: 4px;
    padding-inline: 7px;
  }

  .training-video-player__volume input[type="range"] {
    width: 42px;
    flex-basis: 42px;
  }

  .training-video-player__note {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }

  .training-video-player__note p {
    text-align: left;
  }
}

@media (prefers-reduced-motion: reduce) {
  .training-video-player__watermark {
    animation: none;
  }
}
</style>
