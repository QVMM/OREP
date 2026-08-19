<template>
  <div
    ref="rootRef"
    class="training-tracing-beam"
    data-training-tracing-beam
  >
    <div class="training-tracing-beam__rail" aria-hidden="true">
      <svg
        class="training-tracing-beam__svg"
        :viewBox="`0 0 40 ${beamHeight}`"
        width="40"
        :height="beamHeight"
        preserveAspectRatio="none"
      >
        <path
          class="training-tracing-beam__path training-tracing-beam__path--base"
          :d="beamPath"
          fill="none"
        />
        <path
          class="training-tracing-beam__path training-tracing-beam__path--active"
          :d="beamPath"
          fill="none"
          :stroke="`url(#${gradientId})`"
        />
        <defs>
          <linearGradient
            :id="gradientId"
            gradientUnits="userSpaceOnUse"
            x1="0"
            x2="0"
            :y1="beamStart"
            :y2="beamEnd"
          >
            <stop offset="0" stop-color="#ffb08f" stop-opacity="0" />
            <stop offset="0.18" stop-color="#ff8a5c" />
            <stop offset="0.68" stop-color="#ff5a1f" />
            <stop offset="1" stop-color="#ff3d00" stop-opacity="0" />
          </linearGradient>
        </defs>
      </svg>
    </div>
    <div ref="contentRef" class="training-tracing-beam__content">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'

const rootRef = ref(null)
const contentRef = ref(null)
const beamHeight = ref(1)
const beamStart = ref(0)
const beamEnd = ref(1)
const beamPath = ref('M 10 0 V 1')

const gradientId = `training-beam-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`

/** 所有可能产生滚动的根（移动端是 .workspace-app，桌面是 .workspace-main） */
const scrollRoots = new Set()
let resizeObserver = null
let mutationObserver = null
let animationFrame = 0
let scrollRaf = 0
let targetStart = 0
let targetEnd = 1

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

/**
 * 找到真正会滚动的祖先。
 * 移动端 ≤1023：.workspace-app overflow:auto，.workspace-main overflow:visible
 * 桌面：.workspace-main overflow-y:auto
 */
function collectScrollRoots() {
  scrollRoots.clear()
  scrollRoots.add(window)

  let el = rootRef.value?.parentElement || null
  while (el && el !== document.documentElement) {
    const style = window.getComputedStyle(el)
    const oy = style.overflowY
    const o = style.overflow
    const canScroll =
      oy === 'auto' ||
      oy === 'scroll' ||
      oy === 'overlay' ||
      o === 'auto' ||
      o === 'scroll'
    if (canScroll) scrollRoots.add(el)
    el = el.parentElement
  }

  const main = rootRef.value?.closest('.workspace-main')
  const app = rootRef.value?.closest('.workspace-app')
  if (main) scrollRoots.add(main)
  if (app) scrollRoots.add(app)
}

function viewportMetrics() {
  // 用视觉视口：getBoundingClientRect 已相对屏幕，任意祖先滚动都会反映在 rect 上
  return { top: 0, height: window.innerHeight }
}

function animateBeam() {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const easing = reducedMotion ? 1 : 0.16
  beamStart.value += (targetStart - beamStart.value) * easing
  beamEnd.value += (targetEnd - beamEnd.value) * easing

  if (
    Math.abs(targetStart - beamStart.value) > 0.2 ||
    Math.abs(targetEnd - beamEnd.value) > 0.2
  ) {
    animationFrame = window.requestAnimationFrame(animateBeam)
  } else {
    beamStart.value = targetStart
    beamEnd.value = targetEnd
    animationFrame = 0
  }
}

function updateBeamPosition() {
  if (!rootRef.value) return
  const rect = rootRef.value.getBoundingClientRect()
  const viewport = viewportMetrics()
  // 原逻辑：视口 72% 高度处为进度头
  const progressHead = viewport.top + viewport.height * 0.72 - rect.top
  const visibleEnd = clamp(progressHead, 0, beamHeight.value)

  targetEnd = Math.max(1, visibleEnd + 72)
  targetStart = Math.max(0, visibleEnd - Math.min(280, viewport.height * 0.34))

  if (!animationFrame) animationFrame = window.requestAnimationFrame(animateBeam)
}

function schedulePositionUpdate() {
  if (scrollRaf) return
  scrollRaf = window.requestAnimationFrame(() => {
    scrollRaf = 0
    updateBeamPosition()
  })
}

function updateBeamHeight() {
  if (!contentRef.value) return
  beamHeight.value = Math.max(contentRef.value.offsetHeight, 1)
  const contentRect = contentRef.value.getBoundingClientRect()
  // 原路径样式：week x=10，day x=30，带圆角转折
  const points = [...contentRef.value.querySelectorAll('[data-training-beam-track]')]
    .map(node => {
      const rect = node.getBoundingClientRect()
      return {
        x: node.dataset.trainingBeamTrack === 'week' ? 10 : 30,
        y: clamp(rect.top - contentRect.top + rect.height / 2, 0, beamHeight.value)
      }
    })
    .sort((a, b) => a.y - b.y)

  if (points.length) {
    const first = points[0]
    beamPath.value = points.slice(1).reduce((path, point, index) => {
      const previous = points[index]
      if (point.x === previous.x) return `${path} V ${point.y}`

      const distance = Math.max(point.y - previous.y, 1)
      const turnHeight = Math.min(48, Math.max(24, distance * 0.45))

      if (previous.x < point.x) {
        const turnEnd = Math.min(point.y, previous.y + turnHeight)
        const curve = Math.max(8, (turnEnd - previous.y) * 0.38)
        return `${path} C ${previous.x} ${previous.y + curve} ${point.x} ${turnEnd - curve} ${point.x} ${turnEnd} V ${point.y}`
      }

      const turnStart = Math.max(previous.y, point.y - turnHeight)
      const curve = Math.max(8, (point.y - turnStart) * 0.38)
      return `${path} V ${turnStart} C ${previous.x} ${turnStart + curve} ${point.x} ${point.y - curve} ${point.x} ${point.y}`
    }, `M ${first.x} ${first.y}`)
  } else {
    beamPath.value = `M 10 0 V ${beamHeight.value}`
  }

  updateBeamPosition()
}

function bindScrollListeners() {
  collectScrollRoots()
  for (const root of scrollRoots) {
    root.addEventListener('scroll', schedulePositionUpdate, { passive: true })
  }
}

function unbindScrollListeners() {
  for (const root of scrollRoots) {
    root.removeEventListener('scroll', schedulePositionUpdate)
  }
  scrollRoots.clear()
}

onMounted(async () => {
  await nextTick()
  await new Promise((r) => requestAnimationFrame(() => r()))

  bindScrollListeners()
  window.addEventListener('resize', updateBeamHeight, { passive: true })
  window.visualViewport?.addEventListener('resize', schedulePositionUpdate, { passive: true })
  window.visualViewport?.addEventListener('scroll', schedulePositionUpdate, { passive: true })

  if (contentRef.value) {
    resizeObserver = new ResizeObserver(updateBeamHeight)
    resizeObserver.observe(contentRef.value)

    mutationObserver = new MutationObserver(() => {
      unbindScrollListeners()
      bindScrollListeners()
      updateBeamHeight()
    })
    mutationObserver.observe(contentRef.value, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style', 'hidden'],
    })
  }

  updateBeamHeight()
})

onBeforeUnmount(() => {
  unbindScrollListeners()
  window.removeEventListener('resize', updateBeamHeight)
  window.visualViewport?.removeEventListener('resize', schedulePositionUpdate)
  window.visualViewport?.removeEventListener('scroll', schedulePositionUpdate)
  resizeObserver?.disconnect()
  mutationObserver?.disconnect()
  if (animationFrame) window.cancelAnimationFrame(animationFrame)
  if (scrollRaf) window.cancelAnimationFrame(scrollRaf)
})
</script>

<style scoped>
.training-tracing-beam {
  --training-beam-left: 0px;
  position: relative;
  min-width: 0;
}

.training-tracing-beam__rail {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--training-beam-left);
  z-index: 3;
  width: 40px;
  pointer-events: none;
}

.training-tracing-beam__svg {
  display: block;
  overflow: visible;
}

.training-tracing-beam__path {
  vector-effect: non-scaling-stroke;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.training-tracing-beam__path--base {
  stroke: #cfd2d8;
  stroke-width: 1.25;
  stroke-opacity: 0.7;
}

.training-tracing-beam__path--active {
  stroke-width: 2;
  filter: drop-shadow(0 0 5px rgba(255, 90, 31, 0.4));
}

@media (max-width: 760px) {
  .training-tracing-beam__rail {
    opacity: 0.78;
  }
}

@media (prefers-reduced-motion: reduce) {
  .training-tracing-beam__path--active {
    filter: none;
  }
}
</style>
