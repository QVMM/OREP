<template>
  <div class="training-embed-player">
    <div class="training-embed-player__frame" :class="{ 'is-active': activated }">
      <iframe
        v-if="activated && embedSrc"
        :src="embedSrc"
        :title="resource.title || '站外视频'"
        allow="fullscreen; picture-in-picture"
        allowfullscreen
        scrolling="no"
        frameborder="0"
        sandbox="allow-scripts allow-same-origin allow-popups allow-presentation allow-forms"
        @load="onFrameLoad"
      />
      <button
        v-else
        type="button"
        class="training-embed-player__start"
        @click="activate"
      >
        <span class="training-embed-player__play" aria-hidden="true">▶</span>
        <strong>在平台内开始学习</strong>
        <small>{{ providerLabel }} · 开始后累计学习时长</small>
      </button>
      <span v-if="providerLabel" class="training-embed-player__badge">{{ providerLabel }}</span>
    </div>

    <div class="training-embed-player__meter" aria-live="polite">
      <div class="training-embed-player__bar">
        <i :style="{ width: `${progress}%` }" />
      </div>
      <div class="training-embed-player__stats">
        <span>已学 {{ formatDuration(actualSeconds) }}</span>
        <span>目标约 {{ formatDuration(targetSeconds) }}</span>
        <strong :class="{ 'is-done': complete }">{{ complete ? '已完成' : `${progress}%` }}</strong>
      </div>
      <p>
        请在本页观看；切换到其他标签页不会计入时长。
        达到预计时长的 {{ completePercent }}% 自动完成。看一遍即可累计，不必重刷。
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { updateTrainingLearningProgress } from '../api'
import {
  EMBED_HEARTBEAT_MS,
  isEmbedLearningActive,
  readOrCreateEmbedSessionId,
} from '../embedPlaybackPolicy'

const props = defineProps({
  resource: { type: Object, required: true },
})
const emit = defineEmits(['change'])

const activated = ref(false)
const pageVisible = ref(typeof document === 'undefined' ? true : !document.hidden)
const actualSeconds = ref(Number(props.resource?.actualLearningSeconds || 0))
const progress = ref(Number(props.resource?.progressPercent || 0))
const sessionId = readOrCreateEmbedSessionId(
  typeof sessionStorage === 'undefined' ? null : sessionStorage,
  props.resource?.id,
  () => globalThis.crypto?.randomUUID?.() || `embed_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`,
)
let timer = null
let lastPointerAt = Date.now()

const embedSrc = computed(() => props.resource?.embedUrl || '')
const targetSeconds = computed(() => Math.max(60, Number(props.resource?.durationSeconds || 0)))
const completeRatio = computed(() => {
  const r = Number(props.resource?.completeRatio)
  return Number.isFinite(r) && r > 0 ? Math.min(1, Math.max(0.5, r)) : 0.8
})
const completePercent = computed(() => Math.round(completeRatio.value * 100))
const complete = computed(() => (
  props.resource?.learningStatus === 'COMPLETED' || progress.value >= 100
))
const providerLabel = computed(() => {
  const p = String(props.resource?.provider || '').toUpperCase()
  if (p === 'BILIBILI') return 'B站'
  if (props.resource?.resourceType === 'EMBED_VIDEO') return '站外视频'
  return ''
})

watch(
  () => [props.resource?.actualLearningSeconds, props.resource?.progressPercent, props.resource?.learningStatus],
  ([a, p]) => {
    actualSeconds.value = Number(a || 0)
    progress.value = Number(p || 0)
  }
)

onMounted(() => {
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('pointerdown', onPointer, { passive: true })
  window.addEventListener('keydown', onPointer)
})

onBeforeUnmount(() => {
  stopTimer()
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('pointerdown', onPointer)
  window.removeEventListener('keydown', onPointer)
  // 收工时再同步一次
  if (activated.value) {
    sync(true).catch(() => {})
  }
})

function activate() {
  if (!embedSrc.value) return
  activated.value = true
  lastPointerAt = Date.now()
  startTimer()
  sync(true).catch(() => {})
}

function onFrameLoad() {
  lastPointerAt = Date.now()
}

function onVisibility() {
  pageVisible.value = !document.hidden
  if (!pageVisible.value) {
    sync(true).catch(() => {})
  }
}

function onPointer() {
  lastPointerAt = Date.now()
}

function startTimer() {
  stopTimer()
  timer = window.setInterval(() => {
    sync(false).catch(() => {})
  }, EMBED_HEARTBEAT_MS)
}

function stopTimer() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

function isUserActive() {
  // iframe 内操作到不了父页面；页可见且已点开始即视为在学
  return isEmbedLearningActive({ pageVisible: pageVisible.value, activated: activated.value })
}

async function sync(force) {
  if (!activated.value || complete.value) return
  const visible = pageVisible.value
  const active = isUserActive()
  if (!force && (!visible || !active)) return
  try {
    const updated = await updateTrainingLearningProgress(props.resource.id, {
      mode: 'EMBED',
      sessionId,
      visible,
      active: active && visible,
      reset: false,
    })
    actualSeconds.value = Number(updated?.actualLearningSeconds || actualSeconds.value)
    progress.value = Number(updated?.progressPercent || progress.value)
    emit('change', updated)
  } catch {
    // 网络抖动时静默，下次心跳重试
  }
}

function formatDuration(value) {
  const seconds = Math.max(0, Math.floor(Number(value || 0)))
  if (seconds < 60) return `${seconds} 秒`
  const minutes = Math.floor(seconds / 60)
  const rem = seconds % 60
  return rem ? `${minutes} 分 ${rem} 秒` : `${minutes} 分钟`
}
</script>

<style scoped>
.training-embed-player {
  display: grid;
  gap: 10px;
}

.training-embed-player__frame {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 14px;
  overflow: hidden;
  background: #0f172a;
  border: 1px solid var(--ds-line, #e5e7eb);
}

.training-embed-player__frame iframe {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}

.training-embed-player__start {
  position: absolute;
  inset: 0;
  border: 0;
  display: grid;
  place-content: center;
  gap: 6px;
  color: #fff;
  background:
    radial-gradient(circle at 30% 20%, rgba(232, 74, 28, 0.35), transparent 45%),
    linear-gradient(160deg, #1e293b, #0f172a 70%);
  cursor: pointer;
  font: inherit;
}

.training-embed-player__play {
  width: 56px;
  height: 56px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  margin: 0 auto 4px;
  background: var(--ds-orange, #e84a1c);
  font-size: 18px;
  box-shadow: 0 10px 28px rgba(232, 74, 28, 0.35);
}

.training-embed-player__start strong {
  font-size: 15px;
}

.training-embed-player__start small {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}

.training-embed-player__badge {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  backdrop-filter: blur(6px);
}

.training-embed-player__meter {
  display: grid;
  gap: 6px;
}

.training-embed-player__bar {
  height: 6px;
  border-radius: 999px;
  background: #eceef1;
  overflow: hidden;
}

.training-embed-player__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--ds-orange, #e84a1c), #ff966f);
  transition: width 0.25s ease;
}

.training-embed-player__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 700;
}

.training-embed-player__stats strong {
  margin-left: auto;
  color: var(--ds-orange-deep, #c2410c);
}

.training-embed-player__stats strong.is-done {
  color: #0b7753;
}

.training-embed-player__meter p {
  margin: 0;
  color: var(--ds-faint, #9ca3af);
  font-size: 11px;
  line-height: 1.45;
}
</style>
