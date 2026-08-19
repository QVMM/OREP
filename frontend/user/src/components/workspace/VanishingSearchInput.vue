<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowRight, Search } from '@element-plus/icons-vue'

defineOptions({ name: 'VanishingSearchInput' })

const props = defineProps({
  placeholders: {
    type: Array,
    default: () => ['搜索课程、任务、文件、报告']
  },
  active: {
    type: Boolean,
    default: false
  },
  ariaLabel: {
    type: String,
    default: '搜索课程、任务、文件、报告'
  }
})

const emit = defineEmits(['focus', 'submit', 'change', 'clear', 'vanish-complete'])
const model = defineModel({ type: String, default: '' })
const inputRef = ref(null)
const canvasRef = ref(null)
const placeholderIndex = ref(0)
const animating = ref(false)
const particles = ref([])
let placeholderTimer = null
let animationFrame = null
let boundary = 0

function focus() {
  inputRef.value?.focus()
}

defineExpose({ focus })

function startPlaceholderRotation() {
  stopPlaceholderRotation()
  if (props.placeholders.length < 2) return
  placeholderTimer = window.setInterval(() => {
    if (!model.value && !animating.value && document.visibilityState === 'visible') {
      placeholderIndex.value = (placeholderIndex.value + 1) % props.placeholders.length
    }
  }, 10000)
}

function stopPlaceholderRotation() {
  if (!placeholderTimer) return
  window.clearInterval(placeholderTimer)
  placeholderTimer = null
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') startPlaceholderRotation()
  else stopPlaceholderRotation()
}

function drawTextParticles() {
  const input = inputRef.value
  const canvas = canvasRef.value
  if (!input || !canvas) return []

  const canvasRect = canvas.getBoundingClientRect()
  const width = Math.max(1, Math.round(canvasRect.width))
  const height = Math.max(1, Math.round(canvasRect.height))
  const context = canvas.getContext('2d', { willReadFrequently: true })
  if (!context) return []

  canvas.width = width
  canvas.height = height
  context.clearRect(0, 0, width, height)

  const styles = window.getComputedStyle(input)
  context.font = `${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`
  context.fillStyle = styles.color
  context.textBaseline = 'middle'
  context.fillText(model.value, 0, height / 2)

  const imageData = context.getImageData(0, 0, width, height).data
  const result = []
  for (let y = 0; y < height; y += 2) {
    for (let x = 0; x < width; x += 2) {
      const offset = (y * width + x) * 4
      const alpha = imageData[offset + 3]
      if (alpha < 80) continue
      result.push({
        x,
        y,
        originX: x,
        originY: y,
        alpha: alpha / 255,
        size: 1.35
      })
    }
  }
  return result
}

function renderParticles() {
  const canvas = canvasRef.value
  const context = canvas?.getContext('2d')
  if (!canvas || !context) return

  context.clearRect(0, 0, canvas.width, canvas.height)
  context.fillStyle = '#252a34'
  for (const particle of particles.value) {
    context.globalAlpha = Math.max(0, particle.alpha)
    context.fillRect(particle.x, particle.y, particle.size, particle.size)
  }
  context.globalAlpha = 1
}

function finishAnimation() {
  if (animationFrame) window.cancelAnimationFrame(animationFrame)
  animationFrame = null
  particles.value = []
  model.value = ''
  animating.value = false
  canvasRef.value?.getContext('2d')?.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  emit('vanish-complete')
  window.setTimeout(() => inputRef.value?.focus(), 80)
}

function animateParticles() {
  animationFrame = window.requestAnimationFrame(() => {
    boundary -= 9
    let visibleCount = 0

    for (const particle of particles.value) {
      if (particle.originX >= boundary) {
        particle.x += (Math.random() - 0.35) * 2.4
        particle.y += (Math.random() - 0.5) * 2.2
        particle.alpha -= 0.055 + Math.random() * 0.07
        particle.size = Math.max(0.2, particle.size - Math.random() * 0.08)
      }
      if (particle.alpha > 0) visibleCount += 1
    }

    renderParticles()
    if (visibleCount && boundary > -36) animateParticles()
    else finishAnimation()
  })
}

function submit() {
  const value = model.value.trim()
  if (!value || animating.value) return

  emit('submit', value)
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduceMotion) {
    model.value = ''
    emit('vanish-complete')
    return
  }

  particles.value = drawTextParticles()
  if (!particles.value.length) {
    model.value = ''
    emit('vanish-complete')
    return
  }

  animating.value = true
  boundary = Math.max(...particles.value.map(particle => particle.originX)) + 12
  renderParticles()
  animateParticles()
}

function clear() {
  if (animating.value) return
  model.value = ''
  emit('clear')
  focus()
}

watch(model, value => {
  if (!animating.value) emit('change', value)
})

onMounted(() => {
  startPlaceholderRotation()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  stopPlaceholderRotation()
  if (animationFrame) window.cancelAnimationFrame(animationFrame)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <form
    class="vanishing-search"
    :class="{
      'is-active': active,
      'has-value': model,
      'is-animating': animating
    }"
    role="search"
    @submit.prevent="submit"
  >
    <Search class="vanishing-search__search-icon" aria-hidden="true" />

    <canvas
      ref="canvasRef"
      class="vanishing-search__canvas"
      :class="{ 'is-visible': animating }"
      aria-hidden="true"
    ></canvas>

    <input
      ref="inputRef"
      v-model.trim="model"
      type="search"
      name="orep-workspace-command-search"
      autocomplete="one-time-code"
      spellcheck="false"
      :aria-label="ariaLabel"
      :disabled="animating"
      @focus="emit('focus')"
    >

    <div v-if="!model && !animating" class="vanishing-search__placeholder" aria-hidden="true">
      <Transition name="vanishing-placeholder" mode="out-in">
        <span :key="placeholderIndex">{{ placeholders[placeholderIndex] }}</span>
      </Transition>
    </div>

    <button
      v-if="model && !animating"
      class="vanishing-search__clear"
      type="button"
      aria-label="清空搜索"
      @click="clear"
    >
      ×
    </button>

    <button
      class="vanishing-search__submit"
      type="submit"
      :disabled="!model || animating"
      aria-label="提交搜索"
    >
      <ArrowRight />
    </button>
  </form>
</template>

<style scoped>
.vanishing-search {
  position: relative;
  width: min(460px, 45vw);
  height: 44px;
  overflow: hidden;
  border: 1px solid var(--ds-input-border, #d4d4d8);
  border-radius: 999px;
  display: flex;
  align-items: center;
  color: var(--ds-ink, #0a0a0a);
  background: #ffffff;
  box-shadow: none;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background-color 180ms ease;
}

.vanishing-search.is-active,
.vanishing-search:focus-within {
  border-color: var(--ds-orange-700, #c43a12);
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(196, 58, 18, 0.16);
}

.vanishing-search.has-value {
  background: #ffffff;
}

.vanishing-search__search-icon {
  position: absolute;
  left: 13px;
  z-index: 4;
  width: 17px;
  height: 17px;
  color: var(--ds-faint);
  pointer-events: none;
}

.vanishing-search input {
  position: relative;
  z-index: 3;
  width: 100%;
  height: 100%;
  border: 0;
  outline: 0;
  padding: 0 84px 0 40px;
  color: var(--ds-ink);
  background: transparent;
  font-family: var(--ds-font-sans);
  font-size: 13px;
  font-weight: 500;
}

.vanishing-search input::-webkit-search-cancel-button {
  display: none;
}

.vanishing-search.is-animating input {
  color: transparent;
  caret-color: transparent;
}

.vanishing-search__canvas {
  position: absolute;
  left: 40px;
  right: 84px;
  top: 0;
  z-index: 4;
  width: calc(100% - 124px);
  height: 100%;
  opacity: 0;
  pointer-events: none;
}

.vanishing-search__canvas.is-visible {
  opacity: 1;
}

.vanishing-search__placeholder {
  position: absolute;
  inset: 0 84px 0 40px;
  z-index: 2;
  overflow: hidden;
  display: flex;
  align-items: center;
  color: var(--ds-muted);
  pointer-events: none;
  font-size: 13px;
  font-weight: 500;
}

.vanishing-search__placeholder span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vanishing-placeholder-enter-active,
.vanishing-placeholder-leave-active {
  transition:
    opacity 300ms ease,
    transform 300ms cubic-bezier(0.22, 1, 0.36, 1);
}

.vanishing-placeholder-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.vanishing-placeholder-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

.vanishing-search__clear,
.vanishing-search__submit {
  position: absolute;
  z-index: 6;
  border: 0;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.vanishing-search__clear {
  right: 43px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--ds-faint);
  background: transparent;
  font-size: 17px;
}

.vanishing-search__clear:hover {
  color: var(--ds-ink);
  background: #eceef2;
}

.vanishing-search__submit {
  right: 5px;
  top: 50%;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: #fff;
  background: var(--ds-orange-action);
  transform: translateY(-50%);
  transition:
    color 180ms ease,
    background-color 180ms ease,
    transform 180ms ease;
}

.vanishing-search__submit:disabled {
  color: #a8adb8;
  background: #f0f1f4;
  cursor: default;
}

.vanishing-search__submit:not(:disabled):hover {
  background: var(--ds-orange-deep);
  transform: translateY(-50%) scale(1.05);
}

.vanishing-search__submit svg {
  width: 15px;
  height: 15px;
}

.vanishing-search__clear:focus-visible,
.vanishing-search__submit:focus-visible {
  outline: 2px solid rgba(232, 74, 28, 0.3);
  outline-offset: 1px;
}

@media (max-width: 720px) {
  .vanishing-search {
    width: min(320px, 56vw);
  }
}

@media (prefers-reduced-motion: reduce) {
  .vanishing-search,
  .vanishing-placeholder-enter-active,
  .vanishing-placeholder-leave-active,
  .vanishing-search__submit {
    transition-duration: 0.01ms;
  }
}
</style>
