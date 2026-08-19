<template>
  <div
    ref="rootEl"
    class="signal-mod"
    :class="[
      `is-${moodName}`,
      { 'is-tap': tapping, 'is-hover': hovering, 'is-chip-only': chipOnly }
    ]"
    role="img"
    :aria-label="ariaLabel"
    @pointerenter="onEnter"
    @pointerleave="onLeave"
    @click="onTap"
  >
    <div class="stage-wrap" :style="tiltStyle">
      <svg
        class="stage"
        :viewBox="chipOnly ? '78 78 124 124' : '0 0 280 280'"
        fill="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="bayFill" x1="30" y1="30" x2="250" y2="250" gradientUnits="userSpaceOnUse">
            <stop stop-color="#FFFCFA" stop-opacity="0.55" />
            <stop offset="0.5" stop-color="#F2E8DF" stop-opacity="0.4" />
            <stop offset="1" stop-color="#E4D2C2" stop-opacity="0.38" />
          </linearGradient>
          <linearGradient id="bayStroke" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="rgba(255,255,255,0.7)" />
            <stop offset="0.5" stop-color="rgba(232,74,28,0.28)" />
            <stop offset="1" stop-color="rgba(140,110,90,0.25)" />
          </linearGradient>
          <!-- 首页角标：略实、略亮，与 canvas-deep 分开 -->
          <linearGradient id="dieGlass" x1="0.15" y1="0.1" x2="0.9" y2="0.95">
            <stop offset="0%" stop-color="#FFF9F4" stop-opacity="0.48" />
            <stop offset="40%" stop-color="#F0DDCC" stop-opacity="0.32" />
            <stop offset="100%" stop-color="#E0C0A8" stop-opacity="0.26" />
          </linearGradient>
          <linearGradient id="dieGlassSolid" x1="0.12" y1="0.08" x2="0.92" y2="0.96">
            <stop offset="0%" stop-color="#FFFAF6" stop-opacity="0.96" />
            <stop offset="42%" stop-color="#F6E6D8" stop-opacity="0.94" />
            <stop offset="100%" stop-color="#E8C4A8" stop-opacity="0.92" />
          </linearGradient>
          <linearGradient id="dieRim" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="rgba(255,255,255,0.75)" />
            <stop offset="0.45" stop-color="rgba(232,74,28,0.4)" />
            <stop offset="1" stop-color="rgba(100,70,50,0.35)" />
          </linearGradient>
          <linearGradient id="dieRimSolid" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="rgba(255,255,255,0.9)" />
            <stop offset="0.4" stop-color="rgba(232,74,28,0.55)" />
            <stop offset="1" stop-color="rgba(120,80,55,0.4)" />
          </linearGradient>
          <!-- 整芯扫光：宽柔光覆盖整颗芯片表面 -->
          <linearGradient
            id="dieFullLight"
            gradientUnits="userSpaceOnUse"
            x1="40"
            y1="0"
            x2="120"
            y2="40"
          >
            <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0" />
            <stop offset="28%" stop-color="#FFF6EE" stop-opacity="0.06" />
            <stop offset="48%" stop-color="#FFFFFF" stop-opacity="0.42" />
            <stop offset="58%" stop-color="#FFEDE0" stop-opacity="0.2" />
            <stop offset="78%" stop-color="#FFFFFF" stop-opacity="0.05" />
            <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0" />
            <animateTransform
              attributeName="gradientTransform"
              type="translate"
              values="-130 0; 160 0; 160 0"
              keyTimes="0; 0.22; 1"
              dur="3.6s"
              repeatCount="indefinite"
              calcMode="spline"
              keySplines="0.4 0 0.2 1; 0 0 1 1"
            />
          </linearGradient>
          <linearGradient id="inFlowH" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#E84A1C" stop-opacity="0" />
            <stop offset="50%" stop-color="#FFB08A" stop-opacity="1" />
            <stop offset="100%" stop-color="#E84A1C" stop-opacity="0" />
          </linearGradient>
          <linearGradient id="inFlowV" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#E84A1C" stop-opacity="0" />
            <stop offset="50%" stop-color="#FFB08A" stop-opacity="1" />
            <stop offset="100%" stop-color="#E84A1C" stop-opacity="0" />
          </linearGradient>
          <linearGradient id="dieTrace" x1="0" y1="0" x2="1" y2="0">
            <stop stop-color="#E84A1C" stop-opacity="0.12" />
            <stop offset="0.5" stop-color="#E84A1C" stop-opacity="0.55" />
            <stop offset="1" stop-color="#E84A1C" stop-opacity="0.12" />
          </linearGradient>
          <clipPath id="dieClip">
            <rect x="86" y="86" width="108" height="108" rx="8" />
          </clipPath>
          <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#6B4030" flood-opacity="0.11" />
          </filter>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="1.4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g :style="fieldStyle">
          <template v-if="!chipOnly">
            <!-- soft bay -->
            <rect
              x="36"
              y="36"
              width="208"
              height="208"
              rx="28"
              fill="url(#bayFill)"
              stroke="url(#bayStroke)"
              stroke-width="1.2"
              filter="url(#soft)"
            />

            <!-- corner brackets -->
            <g class="brackets">
              <path d="M52 52 h16 M52 52 v16" />
              <path d="M228 52 h-16 M228 52 v16" />
              <path d="M52 228 h16 M52 228 v-16" />
              <path d="M228 228 h-16 M228 228 v-16" />
            </g>

            <!-- four-side intake rails into square die -->
            <g class="intakes">
              <line v-for="(y, i) in intakeYs" :key="'il' + i" class="rail" x1="48" :y1="y" x2="86" :y2="y" />
              <line v-for="(y, i) in intakeYs" :key="'ir' + i" class="rail" x1="194" :y1="y" x2="232" :y2="y" />
              <line v-for="(x, i) in intakeXs" :key="'it' + i" class="rail" :x1="x" y1="48" :x2="x" y2="86" />
              <line v-for="(x, i) in intakeXs" :key="'ib' + i" class="rail" :x1="x" y1="194" :x2="x" y2="232" />
            </g>

            <g class="streams">
              <line
                v-for="(s, i) in streams"
                :key="'s' + i"
                class="stream"
                :class="s.axis"
                :x1="s.x1"
                :y1="s.y1"
                :x2="s.x2"
                :y2="s.y2"
                :style="{ animationDuration: s.dur, animationDelay: `${s.delay}s` }"
              />
            </g>

            <circle
              v-for="(p, i) in packets"
              :key="'p' + i"
              class="packet"
              :r="p.r"
              filter="url(#glow)"
              :style="{ transform: `translate(${p.x}px, ${p.y}px)`, opacity: p.o }"
            />
          </template>

          <!-- SQUARE die = 真正的「芯片」本体 -->
          <g class="die" :style="chipStyle" :filter="chipOnly ? undefined : 'url(#soft)'">
            <rect
              x="86"
              y="86"
              width="108"
              height="108"
              rx="8"
              :fill="chipOnly ? 'url(#dieGlassSolid)' : 'url(#dieGlass)'"
              :stroke="chipOnly ? 'url(#dieRimSolid)' : 'url(#dieRim)'"
              :stroke-width="chipOnly ? 1.6 : 1.4"
            />
            <rect
              x="90"
              y="90"
              width="100"
              height="100"
              rx="6"
              :fill="chipOnly ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.1)'"
              stroke="rgba(255,255,255,0.22)"
              stroke-width="0.6"
            />

            <!-- dense silicon under frost -->
            <g clip-path="url(#dieClip)" class="silicon">
              <line
                v-for="(x, i) in metalV"
                :key="'mv' + i"
                class="metal-v"
                :x1="x"
                y1="90"
                :x2="x"
                y2="190"
              />
              <line
                v-for="(y, i) in metalH"
                :key="'mh' + i"
                class="metal-h"
                x1="90"
                :y1="y"
                x2="190"
                :y2="y"
              />
              <rect
                v-for="(c, i) in cells"
                :key="'c' + i"
                class="cell"
                :class="{ lit: c.lit }"
                :x="c.x"
                :y="c.y"
                :width="c.w"
                :height="c.h"
                rx="0.5"
                :style="{ animationDelay: `${c.delay}s` }"
              />
              <circle
                v-for="(v, i) in vias"
                :key="'via' + i"
                class="via"
                :cx="v.x"
                :cy="v.y"
                r="0.75"
              />
              <path
                v-for="(tr, i) in dieTraces"
                :key="'tr' + i"
                class="die-trace"
                :d="tr.d"
                :style="{ animationDuration: tr.dur, animationDelay: `${i * 0.2}s` }"
              />
            </g>

            <!-- frost: half transparent -->
            <rect x="86" y="86" width="108" height="108" rx="8" class="frost" />
            <rect x="86" y="86" width="108" height="42" rx="8" class="frost-band" />

            <!-- label：竞赛大脑英文 -->
            <text class="die-title" x="140" y="128" text-anchor="middle">Competition</text>
            <text class="die-title die-title-line2" x="140" y="144" text-anchor="middle">Brain</text>
            <text class="die-sub" x="140" y="162" text-anchor="middle">评审内核</text>

            <circle class="die-led" cx="182" cy="98" r="2.4" :class="ledClass" />

            <!-- 整颗芯片被光照过（约 3.6s 一轮，仅芯片模式） -->
            <g v-if="chipOnly" class="die-light-layer" pointer-events="none">
              <rect
                class="die-full-light"
                x="86"
                y="86"
                width="108"
                height="108"
                rx="8"
                fill="url(#dieFullLight)"
              />
              <!-- 整芯短暂抬亮，配合扫光峰值 -->
              <rect
                class="die-full-glow"
                x="86"
                y="86"
                width="108"
                height="108"
                rx="8"
                fill="rgba(255, 248, 240, 0.35)"
              />
            </g>
          </g>

          <g v-if="!chipOnly" class="ports">
            <rect x="132" y="40" width="16" height="8" rx="2" class="port" />
            <rect x="132" y="232" width="16" height="8" rx="2" class="port" />
            <rect x="40" y="132" width="8" height="16" rx="2" class="port" />
            <rect x="232" y="132" width="8" height="16" rx="2" class="port" />
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  mood: { type: Number, default: 1 },
  enableLook: { type: Boolean, default: true },
  label: { type: String, default: '大脑引擎' },
  /** 仅渲染方芯，无外湾/导轨；适合首页角标 */
  chipOnly: { type: Boolean, default: false }
})

const chipOnly = computed(() => props.chipOnly)

const emit = defineEmits(['tap'])

const rootEl = ref(null)
const look = ref({ x: 0, y: 0 })
const smooth = ref({ x: 0, y: 0 })
const hovering = ref(false)
const tapping = ref(false)
const localMood = ref(props.mood)
const t = ref(0)

let raf = 0
let tapTimer = 0
let celebrateTimer = 0

const DIE = { x: 86, y: 86, s: 108, c: 140 }
const intakeYs = [100, 118, 136, 154, 172]
const intakeXs = [100, 118, 136, 154, 172]

const streams = [
  // left → die
  ...intakeYs.map((y, i) => ({
    axis: 'h',
    x1: 48,
    y1: y,
    x2: 86,
    y2: y,
    dur: `${2.2 + (i % 3) * 0.35}s`,
    delay: i * 0.15
  })),
  // right → die
  ...intakeYs.map((y, i) => ({
    axis: 'h',
    x1: 232,
    y1: y,
    x2: 194,
    y2: y,
    dur: `${2.4 + (i % 3) * 0.3}s`,
    delay: 0.1 + i * 0.14
  })),
  // top → die
  ...intakeXs.map((x, i) => ({
    axis: 'v',
    x1: x,
    y1: 48,
    x2: x,
    y2: 86,
    dur: `${2.3 + (i % 3) * 0.32}s`,
    delay: 0.05 + i * 0.13
  })),
  // bottom → die
  ...intakeXs.map((x, i) => ({
    axis: 'v',
    x1: x,
    y1: 232,
    x2: x,
    y2: 194,
    dur: `${2.5 + (i % 3) * 0.28}s`,
    delay: 0.08 + i * 0.12
  }))
]

const metalV = Array.from({ length: 18 }, (_, i) => 94 + i * 5.4)
const metalH = Array.from({ length: 18 }, (_, i) => 94 + i * 5.4)

const cells = (() => {
  const list = []
  let n = 0
  for (let row = 0; row < 14; row++) {
    for (let col = 0; col < 14; col++) {
      const x = 94 + col * 6.8
      const y = 94 + row * 6.8
      // leave center clearer for label
      const inLabel = x > 108 && x < 172 && y > 118 && y < 158
      if (inLabel && (row + col) % 2 === 0) continue
      list.push({
        x,
        y,
        w: 4 + (col % 4 === 0 ? 1.4 : 0),
        h: 3.2 + (row % 3 === 0 ? 1 : 0),
        lit: (row * 5 + col * 3) % 8 === 0,
        delay: (n++ % 20) * 0.11
      })
    }
  }
  return list
})()

const vias = Array.from({ length: 36 }, (_, i) => ({
  x: 98 + (i % 9) * 10.5 + (Math.floor(i / 9) % 2) * 2,
  y: 100 + Math.floor(i / 9) * 20
}))

const dieTraces = [
  { d: 'M96 100 H130 V120 H170', dur: '3s' },
  { d: 'M180 100 V140 H140 V170', dur: '3.6s' },
  { d: 'M100 170 H150 V140 H175', dur: '3.2s' },
  { d: 'M110 105 V155 H160', dur: '4s' }
]

const mood = computed(() => localMood.value)
const moodName = computed(() => {
  const map = { 0: 'standby', 1: 'online', 2: 'nudge', 3: 'celebrate', 4: 'think', 5: 'alert' }
  return map[mood.value] || 'online'
})

const ariaLabel = computed(() => {
  const map = {
    0: `${props.label}，Competition Brain 评审内核待命`,
    1: `${props.label}，Competition Brain 评审内核运行中，信息从四周汇入`,
    2: `${props.label}，评审内核负载升高`,
    3: `${props.label}，评审内核已响应`,
    4: `${props.label}，评审内核处理中`,
    5: `${props.label}，需注意`
  }
  return map[mood.value] || 'Competition Brain 评审内核'
})

const energy = computed(() => {
  if (mood.value === 0) return 0.28
  if (mood.value === 3) return 1.5
  if (mood.value === 2) return 1.2
  if (mood.value === 4) return 1.1
  return 0.95
})

const ledClass = computed(() => {
  if (mood.value === 0) return 'off'
  if (mood.value === 5) return 'warn'
  if (mood.value === 2) return 'busy'
  return 'on'
})

/** packets from 4 sides into die edges */
const packets = computed(() => {
  const speed = t.value * 0.0012 * energy.value
  const list = []
  // left → right into die
  intakeYs.forEach((y, i) => {
    const s = (speed * (0.9 + i * 0.05) + i * 0.13) % 1
    list.push({
      x: 48 + s * 38,
      y: y + smooth.value.y * 2,
      r: i % 2 ? 1.5 : 2.1,
      o: mood.value === 0 ? 0.12 : 0.35 + s * 0.55
    })
  })
  // right → left
  intakeYs.forEach((y, i) => {
    const s = (speed * (0.85 + i * 0.04) + 0.2 + i * 0.11) % 1
    list.push({
      x: 232 - s * 38,
      y: y + smooth.value.y * 2,
      r: 1.6,
      o: mood.value === 0 ? 0.1 : 0.3 + s * 0.55
    })
  })
  // top → down
  intakeXs.forEach((x, i) => {
    const s = (speed * (0.88 + i * 0.05) + 0.08 + i * 0.12) % 1
    list.push({
      x: x + smooth.value.x * 2,
      y: 48 + s * 38,
      r: 1.7,
      o: mood.value === 0 ? 0.1 : 0.32 + s * 0.55
    })
  })
  // bottom → up
  intakeXs.forEach((x, i) => {
    const s = (speed * (0.92 + i * 0.04) + 0.15 + i * 0.1) % 1
    list.push({
      x: x + smooth.value.x * 2,
      y: 232 - s * 38,
      r: 1.5,
      o: mood.value === 0 ? 0.1 : 0.3 + s * 0.55
    })
  })
  return list
})

const tiltStyle = computed(() => {
  const rx = (-smooth.value.y * 7).toFixed(2)
  const ry = (smooth.value.x * 9).toFixed(2)
  return {
    transform: `perspective(960px) rotateX(${rx}deg) rotateY(${ry}deg)`
  }
})

const fieldStyle = computed(() => ({
  transform: `translate(${smooth.value.x * 3}px, ${smooth.value.y * 2.5}px)`
}))

const chipStyle = computed(() => ({
  transform: `translate(${smooth.value.x * 2}px, ${smooth.value.y * 1.8}px)`
}))

watch(() => props.mood, (v) => { localMood.value = v })

function onEnter() { hovering.value = true }
function onLeave() {
  hovering.value = false
  look.value = { x: 0, y: 0 }
}
function onTap() {
  tapping.value = true
  emit('tap')
  clearTimeout(tapTimer)
  tapTimer = window.setTimeout(() => { tapping.value = false }, 480)
}

function celebrate() {
  localMood.value = 3
  clearTimeout(celebrateTimer)
  celebrateTimer = window.setTimeout(() => {
    localMood.value = props.mood === 3 ? 1 : props.mood
  }, 1100)
}

defineExpose({ celebrate })

function onPointerMove(e) {
  if (!props.enableLook || !rootEl.value) return
  const rect = rootEl.value.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  look.value = {
    x: Math.max(-1, Math.min(1, (e.clientX - cx) / (rect.width * 0.9))),
    y: Math.max(-1, Math.min(1, (e.clientY - cy) / (rect.height * 0.9)))
  }
}

function tick(now) {
  t.value = now
  const k = 0.1
  smooth.value = {
    x: smooth.value.x + (look.value.x - smooth.value.x) * k,
    y: smooth.value.y + (look.value.y - smooth.value.y) * k
  }
  raf = requestAnimationFrame(tick)
}

onMounted(() => {
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  raf = requestAnimationFrame(tick)
})

onUnmounted(() => {
  window.removeEventListener('pointermove', onPointerMove)
  cancelAnimationFrame(raf)
  clearTimeout(tapTimer)
  clearTimeout(celebrateTimer)
})
</script>

<style scoped>
.signal-mod {
  width: min(100%, 300px);
  margin: 0 auto;
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
.signal-mod.is-chip-only {
  width: 100%;
  margin: 0;
}
.signal-mod.is-chip-only .stage {
  display: block;
  width: 100%;
  height: 100%;
}

.stage-wrap {
  transition: transform 110ms ease-out;
  transform-style: preserve-3d;
  will-change: transform;
}

.stage {
  width: 100%;
  height: auto;
  display: block;
  overflow: visible;
}

.brackets path {
  fill: none;
  stroke: rgba(232, 74, 28, 0.4);
  stroke-width: 1.5;
  stroke-linecap: round;
}

.rail {
  stroke: rgba(28, 26, 22, 0.07);
  stroke-width: 1;
}

.stream {
  stroke-linecap: round;
  stroke-dasharray: 10 36;
  animation: streamIn linear infinite;
}
.stream.h {
  stroke: url(#inFlowH);
  stroke-width: 2;
}
.stream.v {
  stroke: url(#inFlowV);
  stroke-width: 2;
}
@keyframes streamIn {
  to { stroke-dashoffset: -46; }
}

.packet {
  fill: #ffb08a;
  stroke: #e84a1c;
  stroke-width: 0.55;
}

/* square die silicon */
.metal-v {
  stroke: rgba(175, 85, 48, 0.32);
  stroke-width: 0.65;
}
.metal-h {
  stroke: rgba(150, 95, 65, 0.26);
  stroke-width: 0.6;
}
.cell {
  fill: rgba(232, 74, 28, 0.12);
  stroke: rgba(232, 74, 28, 0.18);
  stroke-width: 0.3;
}
.cell.lit {
  fill: rgba(232, 74, 28, 0.3);
  animation: cellPulse 2.6s ease-in-out infinite;
}
@keyframes cellPulse {
  0%, 100% { fill: rgba(232, 74, 28, 0.14); }
  50% { fill: rgba(232, 74, 28, 0.4); }
}
.via {
  fill: rgba(90, 60, 40, 0.32);
}
.die-trace {
  fill: none;
  stroke: url(#dieTrace);
  stroke-width: 1.1;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 7 22;
  animation: dieTrace linear infinite;
  opacity: 0.8;
}
@keyframes dieTrace {
  to { stroke-dashoffset: -32; }
}

.frost {
  fill: rgba(255, 250, 246, 0.4);
  pointer-events: none;
}
.frost-band {
  fill: rgba(255, 252, 249, 0.28);
  pointer-events: none;
}

.die-title {
  fill: rgba(36, 26, 20, 0.8);
  font-size: 9.5px;
  font-weight: 800;
  letter-spacing: 0.04em;
  font-family: var(--ds-font-sans, "PingFang SC", "Helvetica Neue", system-ui, sans-serif);
}
.die-title-line2 {
  font-size: 11px;
  letter-spacing: 0.12em;
}
.die-sub {
  fill: rgba(232, 74, 28, 0.88);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.18em;
  font-family: var(--ds-font-sans, "PingFang SC", "Helvetica Neue", system-ui, sans-serif);
}
/* 仅芯片角标时字略收紧，保证方芯内可读 */
.signal-mod.is-chip-only .die-title {
  font-size: 8.5px;
  letter-spacing: 0.02em;
}
.signal-mod.is-chip-only .die-title-line2 {
  font-size: 10px;
  letter-spacing: 0.1em;
}
.signal-mod.is-chip-only .die-sub {
  font-size: 8.5px;
  letter-spacing: 0.14em;
}

/* 整芯光照：柔光覆盖整颗方芯表面，约 3.6s 一轮 */
.die-light-layer {
  pointer-events: none;
}
.die-full-light {
  mix-blend-mode: soft-light;
}
.die-full-glow {
  mix-blend-mode: soft-light;
  opacity: 0;
  animation: dieWholeGlow 3.6s ease-in-out infinite;
}
@keyframes dieWholeGlow {
  /* 扫光经过时整芯一起微微抬亮 */
  0%,
  4% {
    opacity: 0;
  }
  12% {
    opacity: 0.55;
  }
  22% {
    opacity: 0.2;
  }
  28%,
  100% {
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .die-full-glow {
    animation: none !important;
    opacity: 0 !important;
  }
  .die-full-light {
    display: none;
  }
}

.die-led {
  fill: #c5c9d0;
  stroke: rgba(255, 255, 255, 0.55);
  stroke-width: 0.6;
}
.die-led.on {
  fill: #34d399;
  filter: drop-shadow(0 0 3px rgba(15, 159, 110, 0.55));
}
.die-led.busy {
  fill: #e84a1c;
  animation: led 1.05s ease-in-out infinite;
}
.die-led.warn {
  fill: #f87171;
}
.die-led.off {
  fill: #c5c9d0;
  opacity: 0.6;
}
@keyframes led {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.port {
  fill: #c8b4a4;
  stroke: rgba(28, 26, 22, 0.08);
  stroke-width: 0.5;
}

/* moods */
.is-standby {
  filter: saturate(0.78);
}
.is-standby .stream,
.is-standby .packet,
.is-standby .die-trace,
.is-standby .cell.lit {
  opacity: 0.22 !important;
  animation-duration: 9s !important;
}

.is-nudge .stream {
  animation-duration: 1.5s !important;
}
.is-nudge .cell.lit {
  animation-duration: 1.2s;
}

.is-celebrate .stream {
  animation-duration: 1.15s !important;
  stroke-width: 2.5;
}
.is-celebrate .packet {
  filter: drop-shadow(0 0 4px rgba(232, 74, 28, 0.55));
}
.is-celebrate .die {
  filter: drop-shadow(0 0 16px rgba(232, 74, 28, 0.2));
}

.is-hover .frost {
  fill: rgba(255, 250, 246, 0.3);
}
.is-tap .stage-wrap {
  transform: perspective(960px) scale(0.98) !important;
}
</style>
