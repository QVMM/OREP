<template>
  <div
    class="tvk"
    :class="{
      'is-active': active,
      'is-composing': composing,
      'is-hands': showHands,
    }"
    aria-hidden="true"
  >
    <div class="tvk__glow" />
    <div class="tvk__head">
      <span class="tvk__dot" />
      <span class="tvk__title">实时键位 · 标准指法</span>
      <span class="tvk__hint">
        {{ composing ? '拼音输入中' : activeFingerHint }}
      </span>
      <button
        type="button"
        class="tvk__toggle"
        :class="{ 'is-on': showHands }"
        :aria-pressed="showHands"
        :aria-label="showHands ? '关闭指法手势' : '开启指法手势'"
        @click="showHands = !showHands"
      >
        <span class="tvk__toggle-track" aria-hidden="true" />
        <span class="tvk__toggle-label">指法{{ showHands ? '开' : '关' }}</span>
      </button>
    </div>

    <div ref="boardRef" class="tvk__board">
      <!-- 幽灵手在键帽后面，字母始终可读 -->
      <div v-if="showHands" class="tvk__hands" aria-hidden="true">
        <svg
          v-for="side in handSides"
          :key="side"
          class="tvk__hand"
          :class="`tvk__hand--${side}`"
          :style="handBoxStyle(side)"
          viewBox="0 0 240 320"
        >
          <g :transform="side === 'right' ? 'translate(240,0) scale(-1,1)' : undefined">
            <path class="tvk__hand-wrist" d="M84 286 C76 312 164 312 156 286" />
            <path class="tvk__hand-palm" d="M44 204 C36 168 54 150 80 146 L90 154 L118 150 L146 152 L172 160 C200 174 212 204 200 236 C188 274 148 292 118 294 C76 296 50 268 44 228 Z" />
            <g
              v-for="fid in fingersOf(side)"
              :key="fid"
              class="tvk__digit"
              :class="{
                'is-aim': isAimDigit(fid),
                'is-press': isPressDigit(fid),
                'is-thumb': fid === 'T',
              }"
              :style="digitStyle(side, fid)"
            >
              <path class="tvk__digit-body" :d="digitPath(fid)" />
              <ellipse
                class="tvk__digit-nail"
                :cx="digitNail(fid).cx"
                :cy="digitNail(fid).cy"
                :rx="digitNail(fid).rx"
                :ry="digitNail(fid).ry"
              />
            </g>
          </g>
        </svg>
      </div>

      <div v-for="(row, ri) in rows" :key="ri" class="tvk__row" :style="{ '--pad': row.pad }">
        <div
          v-for="key in row.keys"
          :key="key.id"
          :ref="(el) => setKeyEl(key.id, el)"
          class="tvk__key"
          :class="[
            `is-${key.size || 'std'}`,
            {
              'is-down': pressed.has(key.id),
              'is-hot': hotId === key.id,
              'is-ok': flashId === key.id && flashKind === 'ok',
              'is-bad': flashId === key.id && flashKind === 'bad',
              'is-mod': key.mod,
              'is-home': isHomeKey(key.id),
              'is-target': targetCode === key.id,
            },
          ]"
          :style="keyFingerStyle(key.id)"
        >
          <span class="tvk__key-face">
            <span class="tvk__main">{{ key.label }}</span>
            <span v-if="key.sub" class="tvk__sub">{{ key.sub }}</span>
          </span>
          <span class="tvk__ripple" />
        </div>
      </div>
    </div>

    <div v-if="showHands" class="tvk__legend">
      <span v-for="f in legendFingers" :key="f.id" class="tvk__legend-item">
        <i :style="{ background: f.color }" />{{ f.name }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  FINGERS,
  fingerColorForCode,
  fingerIdForCode,
  homeCodeForFinger,
} from './fingerMap'

const props = defineProps({
  active: { type: Boolean, default: false },
  composing: { type: Boolean, default: false },
  lastHit: { type: String, default: null },
  lastKeyCode: { type: String, default: '' },
  /** 期望按的物理键（可预示下一键，可选） */
  expectedKeyCode: { type: String, default: '' },
})

const showHands = ref(true)
const pressed = ref(new Set())
const hotId = ref('')
const flashId = ref('')
const flashKind = ref(null)
const boardRef = ref(null)
const keyEls = reactive({})
/** fingerId → { x, y, pressing, code } 相对 board 的中心点 % 或 px */
const fingerState = reactive({})

let flashTimer = null
let hotTimer = null
let layoutRaf = 0
let boardResizeObserver = null

const HOME_CODES = new Set(['KeyA', 'KeyS', 'KeyD', 'KeyF', 'KeyJ', 'KeyK', 'KeyL', 'Semicolon', 'Space'])

const rows = computed(() => [
  {
    pad: '0px',
    keys: [
      key('Backquote', '`', '~'),
      ...numRow(),
      key('Backspace', '⌫', '', 'wide', true),
    ],
  },
  {
    pad: '18px',
    keys: [
      key('Tab', 'tab', '', 'mid', true),
      ...letterRow('QWERTYUIOP', 'qwertyuiop'),
      key('BracketLeft', '[', '{'),
      key('BracketRight', ']', '}'),
      key('Backslash', '\\', '|', 'mid'),
    ],
  },
  {
    pad: '28px',
    keys: [
      key('CapsLock', 'caps', '', 'mid', true),
      ...letterRow('ASDFGHJKL', 'asdfghjkl'),
      key('Semicolon', ';', ':'),
      key('Quote', "'", '"'),
      key('Enter', '↵', '', 'wide', true),
    ],
  },
  {
    pad: '48px',
    keys: [
      key('ShiftLeft', 'shift', '', 'wide', true),
      ...letterRow('ZXCVBNM', 'zxcvbnm'),
      key('Comma', ',', '<'),
      key('Period', '.', '>'),
      key('Slash', '/', '?'),
      key('ShiftRight', 'shift', '', 'wide', true),
    ],
  },
  {
    pad: '72px',
    keys: [
      key('ControlLeft', 'ctrl', '', 'mid', true),
      key('AltLeft', 'alt', '', 'mid', true),
      key('MetaLeft', '⌘', '', 'mid', true),
      key('Space', '', '', 'space', true),
      key('MetaRight', '⌘', '', 'mid', true),
      key('AltRight', 'alt', '', 'mid', true),
      key('ControlRight', 'ctrl', '', 'mid', true),
    ],
  },
])

const legendFingers = computed(() => FINGERS.filter((f) => f.id !== 'T').concat(FINGERS.filter((f) => f.id === 'T')))

const targetCode = computed(() => {
  if (hotId.value) return hotId.value
  if (props.expectedKeyCode) return props.expectedKeyCode
  return ''
})

const aimFingerId = computed(() => fingerIdForCode(targetCode.value) || '')

const activeFingerHint = computed(() => {
  if (!props.active && !pressed.value.size) return showHands.value ? 'ASDF / JKL; 归位 · 开始输入' : '开始输入后点亮'
  const code = hotId.value || [...pressed.value][0] || ''
  const fid = fingerIdForCode(code)
  const f = FINGERS.find((x) => x.id === fid)
  if (f) return `${f.name} · ${codeLabel(code)}`
  return '跟打反馈'
})

const HAND_VB = { w: 240, h: 320 }
const LEFT_TIPS = {
  L4: { x: 50, y: 40 },
  L3: { x: 98, y: 22 },
  L2: { x: 146, y: 14 },
  L1: { x: 194, y: 30 },
  T: { x: 216, y: 186 },
}
const DIGIT_PATHS = {
  L4: 'M50 40 C42 42 38 54 40 72 L46 150 C48 162 68 162 68 148 L62 70 C60 50 58 38 50 40 Z',
  L3: 'M98 22 C90 24 86 36 88 56 L92 148 C94 160 114 160 114 146 L108 54 C106 34 106 20 98 22 Z',
  L2: 'M146 14 C138 16 134 28 136 48 L138 146 C140 158 160 158 160 144 L156 46 C154 26 154 12 146 14 Z',
  L1: 'M194 30 C186 28 178 40 180 60 L172 152 C170 164 190 168 194 154 L200 58 C204 40 202 28 194 30 Z',
  R4: 'M50 40 C42 42 38 54 40 72 L46 150 C48 162 68 162 68 148 L62 70 C60 50 58 38 50 40 Z',
  R3: 'M98 22 C90 24 86 36 88 56 L92 148 C94 160 114 160 114 146 L108 54 C106 34 106 20 98 22 Z',
  R2: 'M146 14 C138 16 134 28 136 48 L138 146 C140 158 160 158 160 144 L156 46 C154 26 154 12 146 14 Z',
  R1: 'M194 30 C186 28 178 40 180 60 L172 152 C170 164 190 168 194 154 L200 58 C204 40 202 28 194 30 Z',
  T: 'M168 210 C186 198 206 176 218 160 C228 146 220 134 206 142 C190 156 176 180 168 204 C164 214 164 216 168 210 Z',
}
const DIGIT_NAILS = {
  L4: { cx: 50, cy: 48, rx: 6, ry: 8 },
  L3: { cx: 98, cy: 30, rx: 6.5, ry: 8.5 },
  L2: { cx: 146, cy: 22, rx: 6.5, ry: 9 },
  L1: { cx: 192, cy: 38, rx: 6.5, ry: 8.5 },
  R4: { cx: 50, cy: 48, rx: 6, ry: 8 },
  R3: { cx: 98, cy: 30, rx: 6.5, ry: 8.5 },
  R2: { cx: 146, cy: 22, rx: 6.5, ry: 9 },
  R1: { cx: 192, cy: 38, rx: 6.5, ry: 8.5 },
  T: { cx: 214, cy: 154, rx: 7, ry: 6 },
}

const handSides = ['left', 'right']
const handMetrics = reactive({
  left: { hScale: 1, vScale: 1 },
  right: { hScale: 1, vScale: 1 },
})

function fingersOf(side) {
  return side === 'left' ? ['L4', 'L3', 'L2', 'L1', 'T'] : ['R4', 'R3', 'R2', 'R1', 'T']
}

function digitPath(fid) {
  return DIGIT_PATHS[fid] || DIGIT_PATHS.L2
}

function digitNail(fid) {
  return DIGIT_NAILS[fid] || DIGIT_NAILS.L2
}

function isAimDigit(fid) {
  return aimFingerId.value === fid
}

function isPressDigit(fid) {
  return Boolean(fingerState[fid]?.pressing)
}

function key(id, label, sub = '', size = 'std', mod = false) {
  return { id, label, sub, size, mod }
}

function numRow() {
  const tops = '!@#$%^&*()'
  return '1234567890'.split('').map((n, i) => key(`Digit${n}`, n, tops[i] || ''))
}

function letterRow(upper, lower) {
  return upper.split('').map((U, i) => {
    const L = lower[i]
    return key(`Key${U}`, U, L)
  })
}

function isHomeKey(id) {
  return HOME_CODES.has(id)
}

function keyFingerStyle(id) {
  const color = fingerColorForCode(id)
  if (!color || !showHands.value) return null
  return {
    '--finger': color,
    '--finger-soft': color + '33',
  }
}

function codeLabel(code) {
  if (!code) return ''
  if (code.startsWith('Key')) return code.slice(3)
  if (code.startsWith('Digit')) return code.slice(5)
  if (code === 'Space') return '空格'
  if (code === 'Semicolon') return ';'
  return code
}

function setKeyEl(id, el) {
  if (el) keyEls[id] = el
  else delete keyEls[id]
}

function normalizeCode(code, keyName) {
  if (!code && !keyName) return ''
  if (code) return code
  if (keyName === ' ') return 'Space'
  if (keyName.length === 1) {
    const up = keyName.toUpperCase()
    if (/[A-Z]/.test(up)) return `Key${up}`
    if (/[0-9]/.test(keyName)) return `Digit${keyName}`
  }
  return keyName
}

function markDown(id) {
  if (!id) return
  const next = new Set(pressed.value)
  next.add(id)
  pressed.value = next
  hotId.value = id
  scheduleFingerLayout()
  clearTimeout(hotTimer)
  hotTimer = setTimeout(() => {
    if (hotId.value === id) hotId.value = ''
    scheduleFingerLayout()
  }, 220)
}

function markUp(id) {
  if (!id) return
  const next = new Set(pressed.value)
  next.delete(id)
  pressed.value = next
  scheduleFingerLayout()
}

function onKeyDown(e) {
  if (e.repeat) return
  const id = normalizeCode(e.code, e.key)
  markDown(id)
  if (e.key && e.key.length === 1 && /[a-zA-Z]/.test(e.key)) {
    markDown(`Key${e.key.toUpperCase()}`)
  }
}

function onKeyUp(e) {
  const id = normalizeCode(e.code, e.key)
  markUp(id)
  if (e.key && e.key.length === 1 && /[a-zA-Z]/.test(e.key)) {
    markUp(`Key${e.key.toUpperCase()}`)
  }
}

function keyCenterPx(code) {
  const el = keyEls[code]
  const board = boardRef.value
  if (!el || !board) return null
  const br = board.getBoundingClientRect()
  const kr = el.getBoundingClientRect()
  if (!br.width || !br.height) return null
  return {
    x: kr.left + kr.width / 2 - br.left,
    y: kr.top + kr.height / 2 - br.top,
  }
}

function spacePoint(side) {
  const el = keyEls.Space
  const board = boardRef.value
  if (!el || !board) return null
  const br = board.getBoundingClientRect()
  const kr = el.getBoundingClientRect()
  return {
    x: kr.left - br.left + kr.width * (side === 'left' ? 0.28 : 0.72),
    y: kr.top - br.top + kr.height * 0.42,
  }
}

function resolveThumbCode(side) {
  const code = resolveFingerTargetCode('T')
  if (!code || code === 'Space') return 'Space'
  if (side === 'left' && /Left/.test(code)) return code
  if (side === 'right' && /Right/.test(code)) return code
  return 'Space'
}

function pointForDigit(side, fid) {
  if (fid === 'T') {
    const code = resolveThumbCode(side)
    if (code === 'Space') return spacePoint(side)
    return keyCenterPx(code) || spacePoint(side)
  }
  const code = resolveFingerTargetCode(fid)
  return keyCenterPx(code) || keyCenterPx(homeCodeForFinger(fid))
}

function homePointForDigit(side, fid) {
  if (fid === 'T') return spacePoint(side)
  return keyCenterPx(homeCodeForFinger(fid))
}

function computeHandScale(side) {
  const pinky = keyCenterPx(side === 'left' ? 'KeyA' : 'Semicolon')
  const index = keyCenterPx(side === 'left' ? 'KeyF' : 'KeyJ')
  const keyEl = keyEls.KeyA || keyEls.KeyJ
  const keyH = keyEl ? keyEl.getBoundingClientRect().height : 56
  const hScale = pinky && index
    ? Math.abs(index.x - pinky.x) / (LEFT_TIPS.L1.x - LEFT_TIPS.L4.x)
    : 1
  const vScale = (keyH * 2.75) / 160
  return { hScale, vScale }
}

function handBoxStyle(side) {
  const pinky = keyCenterPx(side === 'left' ? 'KeyA' : 'Semicolon')
  if (!pinky) return { opacity: 0 }
  const { hScale, vScale } = handMetrics[side]
  const tipX = side === 'left' ? LEFT_TIPS.L4.x : (HAND_VB.w - LEFT_TIPS.L4.x)
  return {
    left: `${pinky.x - tipX * hScale}px`,
    top: `${pinky.y - LEFT_TIPS.L4.y * vScale}px`,
    width: `${HAND_VB.w * hScale}px`,
    height: `${HAND_VB.h * vScale}px`,
    opacity: 1,
  }
}

function digitStyle(side, fid) {
  const home = homePointForDigit(side, fid)
  const target = pointForDigit(side, fid)
  const { hScale, vScale } = handMetrics[side]
  if (!home || !target || !hScale) return { transform: 'translate(0px, 0px)' }
  let dx = (target.x - home.x) / hScale
  let dy = (target.y - home.y) / vScale
  if (side === 'right') dx = -dx
  if (isPressDigit(fid)) dy += 7
  return { transform: `translate(${dx}px, ${dy}px)` }
}

/** 根据当前按下的键，为每个手指选目标键：优先本指正在按的键，否则 home */
function resolveFingerTargetCode(fingerId) {
  const activeCodes = [...pressed.value]
  const pressing = activeCodes.find((c) => fingerIdForCode(c) === fingerId)
  if (pressing) return pressing
  if (hotId.value && fingerIdForCode(hotId.value) === fingerId) return hotId.value
  if (props.expectedKeyCode && fingerIdForCode(props.expectedKeyCode) === fingerId) {
    return props.expectedKeyCode
  }
  return homeCodeForFinger(fingerId)
}

function layoutFingers() {
  layoutRaf = 0
  if (!showHands.value || !boardRef.value) return
  Object.assign(handMetrics.left, computeHandScale('left'))
  Object.assign(handMetrics.right, computeHandScale('right'))
  for (const f of FINGERS) {
    const code = resolveFingerTargetCode(f.id)
    fingerState[f.id] = {
      pressing: pressed.value.has(code) || hotId.value === code,
      code,
    }
  }
}

function scheduleFingerLayout() {
  if (layoutRaf) return
  layoutRaf = requestAnimationFrame(layoutFingers)
}

watch(
  () => [props.lastHit, props.lastKeyCode],
  ([hit, code]) => {
    if (!hit || !code) return
    flashId.value = code
    flashKind.value = hit
    markDown(code)
    clearTimeout(flashTimer)
    flashTimer = setTimeout(() => {
      markUp(code)
      flashId.value = ''
      flashKind.value = null
    }, 320)
  }
)

watch(showHands, async (on) => {
  if (on) {
    await nextTick()
    scheduleFingerLayout()
  }
})

watch(
  () => props.expectedKeyCode,
  () => scheduleFingerLayout()
)

function onResize() {
  scheduleFingerLayout()
}

onMounted(async () => {
  window.addEventListener('keydown', onKeyDown, true)
  window.addEventListener('keyup', onKeyUp, true)
  window.addEventListener('resize', onResize)
  await nextTick()
  // 初始化 home 位
  for (const f of FINGERS) {
    fingerState[f.id] = { x: 50, y: 70, pressing: false, code: f.home }
  }
  if (typeof ResizeObserver !== 'undefined' && boardRef.value) {
    boardResizeObserver = new ResizeObserver(() => scheduleFingerLayout())
    boardResizeObserver.observe(boardRef.value)
  }
  scheduleFingerLayout()
  // 布局稳定后再算一次
  setTimeout(scheduleFingerLayout, 80)
  setTimeout(scheduleFingerLayout, 300)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown, true)
  window.removeEventListener('keyup', onKeyUp, true)
  window.removeEventListener('resize', onResize)
  boardResizeObserver?.disconnect()
  clearTimeout(flashTimer)
  clearTimeout(hotTimer)
  if (layoutRaf) cancelAnimationFrame(layoutRaf)
})

defineExpose({
  pulse(code, kind = 'ok') {
    if (!code) return
    markDown(code)
    flashId.value = code
    flashKind.value = kind
    clearTimeout(flashTimer)
    flashTimer = setTimeout(() => {
      markUp(code)
      flashId.value = ''
      flashKind.value = null
    }, 280)
  },
})
</script>

<style scoped>
.tvk {
  --tvk-bg0: rgba(255, 255, 255, 0.72);
  --tvk-bg1: rgba(248, 250, 252, 0.9);
  --tvk-ink: #1f2937;
  --tvk-muted: #94a3b8;
  --tvk-line: rgba(15, 23, 42, 0.08);
  --tvk-key: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
  --tvk-key-edge: rgba(15, 23, 42, 0.1);
  --tvk-accent: #f97316;
  --tvk-accent-soft: rgba(249, 115, 22, 0.18);
  --tvk-ok: #10b981;
  --tvk-bad: #ef4444;
  --tvk-key-h: 40px;
  --tvk-key-fs: 12.5px;
  --tvk-row-gap: 8px;
  position: relative;
  overflow: hidden;
  padding: 10px 14px 8px;
  border-radius: 18px;
  border: 1px solid var(--tvk-line);
  background: linear-gradient(145deg, var(--tvk-bg0), var(--tvk-bg1));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.85) inset,
    0 12px 40px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

.tvk.is-active {
  border-color: rgba(249, 115, 22, 0.22);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 16px 48px rgba(249, 115, 22, 0.08),
    0 8px 24px rgba(15, 23, 42, 0.05);
}

.tvk__glow {
  pointer-events: none;
  position: absolute;
  inset: -40% -20% auto;
  height: 80%;
  background: radial-gradient(ellipse at 50% 0%, rgba(249, 115, 22, 0.12), transparent 65%);
  opacity: 0.55;
}

.tvk.is-active .tvk__glow { opacity: 1; }

.tvk__head {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tvk__dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #cbd5e1;
  box-shadow: 0 0 0 3px rgba(203, 213, 225, 0.35);
  transition: background 0.25s ease, box-shadow 0.25s ease;
}

.tvk.is-active .tvk__dot {
  background: var(--tvk-accent);
  box-shadow: 0 0 0 3px var(--tvk-accent-soft), 0 0 12px rgba(249, 115, 22, 0.45);
  animation: tvk-pulse 1.6s ease-in-out infinite;
}

.tvk.is-composing .tvk__dot {
  background: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.tvk__title {
  font-size: 12px;
  font-weight: 750;
  letter-spacing: 0.04em;
  color: var(--tvk-ink);
}

.tvk__hint {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  color: var(--tvk-muted);
  max-width: 46%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}

.tvk__toggle {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 12px 0 8px;
  border: 1.5px solid #cbd5e1;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  font: inherit;
  font-size: 13px;
  font-weight: 750;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}

.tvk__toggle:hover {
  border-color: #94a3b8;
  background: #f8fafc;
}

.tvk__toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.32);
}

.tvk__toggle.is-on {
  border-color: #ea580c;
  background: #f97316;
  color: #fff;
  box-shadow: 0 1px 2px rgba(234, 88, 12, 0.28);
}

.tvk__toggle.is-on:hover {
  background: #ea580c;
  border-color: #c2410c;
}

.tvk__toggle-track {
  position: relative;
  width: 28px;
  height: 16px;
  flex: none;
  border-radius: 999px;
  background: #e2e8f0;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.12);
}

.tvk__toggle-track::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.22);
  transition: left 0.15s ease;
}

.tvk__toggle.is-on .tvk__toggle-track {
  background: rgba(255, 255, 255, 0.38);
}

.tvk__toggle.is-on .tvk__toggle-track::after {
  left: 14px;
}

.tvk__board {
  position: relative;
  z-index: 1;
  display: grid;
  gap: var(--tvk-row-gap);
  isolation: isolate;
  width: 100%;
}

.tvk__row {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  gap: 7px;
  padding-left: var(--pad, 0);
  padding-right: var(--pad, 0);
}

.tvk__key {
  --w: 38px;
  --finger: transparent;
  --finger-soft: transparent;
  position: relative;
  width: var(--w);
  height: var(--tvk-key-h);
  min-height: var(--tvk-key-h);
  flex: 0 0 auto;
  border-radius: 8px;
  background: var(--tvk-key);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px var(--tvk-key-edge),
    0 3px 0 rgba(15, 23, 42, 0.08),
    0 6px 12px rgba(15, 23, 42, 0.04);
  transform: translateY(0);
  transition:
    transform 0.08s cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 0.12s ease,
    background 0.12s ease;
  overflow: hidden;
  z-index: 1;
}

.tvk.is-hands .tvk__key:not(.is-mod) {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--finger) 42%, rgba(255, 255, 255, 0.72)) 0%,
      color-mix(in srgb, var(--finger) 28%, rgba(248, 250, 252, 0.62)) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.88) inset,
    0 0 0 1.5px color-mix(in srgb, var(--finger) 48%, var(--tvk-key-edge)),
    0 3px 0 color-mix(in srgb, var(--finger) 22%, rgba(15, 23, 42, 0.08));
}

.tvk.is-hands .tvk__key.is-home:not(.is-mod) {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--finger) 58%, rgba(255, 255, 255, 0.7)) 0%,
      color-mix(in srgb, var(--finger) 38%, rgba(248, 250, 252, 0.58)) 100%);
}

.tvk.is-hands .tvk__key.is-home:not(.is-mod)::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: 5px;
  width: 16px;
  height: 3px;
  border-radius: 2px;
  background: var(--finger);
  transform: translateX(-50%);
  opacity: 0.95;
}

.tvk__key.is-mid { --w: 54px; }
.tvk__key.is-wide { --w: 76px; }
.tvk__key.is-space { --w: min(320px, 42vw); }

.tvk__key-face {
  position: relative;
  z-index: 1;
  height: 100%;
  display: grid;
  place-content: center;
  color: var(--tvk-ink);
  font-size: var(--tvk-key-fs);
  font-weight: 700;
  user-select: none;
}
.tvk.is-hands .tvk__key-face {
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.72);
}

.tvk__key.is-mod .tvk__main {
  font-size: 11px;
  font-weight: 650;
  color: #64748b;
  text-transform: lowercase;
}

.tvk__sub { display: none; }

.tvk__ripple {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 60%, rgba(249, 115, 22, 0.35), transparent 62%);
  opacity: 0;
  transform: scale(0.6);
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.tvk__key.is-down {
  transform: translateY(2px) scale(0.98);
  background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.7) inset,
    0 0 0 1px rgba(249, 115, 22, 0.35),
    0 1px 0 rgba(15, 23, 42, 0.06),
    0 0 18px rgba(249, 115, 22, 0.25);
}

.tvk__key.is-down .tvk__ripple {
  opacity: 1;
  transform: scale(1);
}

.tvk.is-hands .tvk__key.is-target:not(.is-down) {
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 2.5px var(--finger, var(--tvk-accent)),
    0 0 0 5px color-mix(in srgb, var(--finger, var(--tvk-accent)) 28%, transparent),
    0 0 22px color-mix(in srgb, var(--finger, var(--tvk-accent)) 55%, transparent);
}

.tvk__key.is-hot:not(.is-down) {
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px rgba(249, 115, 22, 0.28),
    0 0 16px rgba(249, 115, 22, 0.18);
}

.tvk__key.is-ok { animation: tvk-ok 0.32s ease; }
.tvk__key.is-bad { animation: tvk-bad 0.32s ease; }

/* —— 指法手势层：永远在键帽下面 —— */
.tvk__hands {
  pointer-events: none;
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: visible;
}

.tvk__hand {
  position: absolute;
  overflow: visible;
  pointer-events: none;
  transform-box: view-box;
}
.tvk__hand-palm,
.tvk__hand-wrist,
.tvk__digit-body {
  fill: rgba(248, 250, 252, 0.42);
  stroke: #3f3f46;
  stroke-width: 2.4;
  stroke-linejoin: round;
  stroke-linecap: round;
}
.tvk__hand-wrist {
  fill: none;
  stroke-width: 3;
}
.tvk__digit {
  transform-box: view-box;
  transform-origin: center bottom;
  transition: transform 0.16s cubic-bezier(0.22, 0.9, 0.3, 1);
  will-change: transform;
}
.tvk__digit-nail {
  fill: rgba(255, 255, 255, 0.55);
  stroke: #52525b;
  stroke-width: 1.4;
}
.tvk__digit.is-aim .tvk__digit-body,
.tvk__digit.is-press .tvk__digit-body {
  fill: rgba(255, 247, 237, 0.62);
  stroke: #1f2937;
  stroke-width: 3;
  filter: drop-shadow(0 0 8px rgba(249, 115, 22, 0.45));
}
.tvk__digit.is-press {
  transition-duration: 0.1s;
}

.tvk__legend {
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed rgba(15, 23, 42, 0.08);
}

.tvk__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 650;
  color: var(--tvk-muted);
}

.tvk__legend-item i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.08);
}

@keyframes tvk-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.75; transform: scale(0.92); }
}

@keyframes tvk-aim {
  0%, 100% { filter: brightness(1.12) saturate(1.2); }
  50% { filter: brightness(1.28) saturate(1.35); }
}

@keyframes tvk-ok {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
  40% {
    background: linear-gradient(180deg, #ecfdf5, #d1fae5);
    box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.45), 0 0 20px rgba(16, 185, 129, 0.35);
  }
  100% { box-shadow: 0 3px 0 rgba(15, 23, 42, 0.08); }
}

@keyframes tvk-bad {
  0% { transform: translateY(0); }
  25% {
    transform: translateY(2px) translateX(-1px);
    background: linear-gradient(180deg, #fef2f2, #fecaca);
    box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.45), 0 0 18px rgba(239, 68, 68, 0.3);
  }
  50% { transform: translateY(2px) translateX(1px); }
  100% { transform: translateY(0); }
}

@media (min-width: 1100px) {
  .tvk {
    /* 铺满卡片宽度，但键高跟字母键宽度走，避免「又宽又扁」 */
    --tvk-key-h: 56px;
    --tvk-key-fs: 14px;
    --tvk-row-gap: 6px;
    flex: 0 0 auto;
    padding: 8px 16px 10px;
  }
  .tvk__row {
    justify-content: stretch;
    align-items: stretch;
    gap: 6px;
    padding-right: 0;
  }
  .tvk__key {
    flex: 1 1 0;
    width: auto;
    min-width: 0;
    height: var(--tvk-key-h);
    min-height: 56px;
    border-radius: 10px;
  }
  .tvk__key.is-mid { flex: 1.45 1 0; }
  .tvk__key.is-wide { flex: 2.05 1 0; }
  .tvk__key.is-space { flex: 6.6 1 0; --w: auto; }
  .tvk__key.is-mod .tvk__main { font-size: 12px; }
  .tvk__hand-palm,
  .tvk__digit-body { stroke-width: 2.6; }
}

@media (min-width: 1100px) and (max-height: 920px) {
  /* 矮屏只收图例与头栏，绝不压键高 */
  .tvk__head { margin-bottom: 6px; }
  .tvk__legend { display: none; }
}

@media (max-width: 720px) {
  .tvk { padding: 12px 10px 10px; }
  .tvk__key {
    flex: 0 0 auto;
    --w: 28px;
    width: var(--w);
    height: 32px;
    border-radius: 6px;
  }
  .tvk__key.is-mid { --w: 38px; }
  .tvk__key.is-wide { --w: 52px; }
  .tvk__key.is-space { --w: min(180px, 38vw); }
  .tvk__key-face { font-size: 10px; }
  .tvk__key.is-mod .tvk__main { font-size: 9px; }
  .tvk__row { gap: 4px; justify-content: center; }
  .tvk__hand-palm,
  .tvk__digit-body { stroke-width: 2; }
  .tvk__hint { display: none; }
  .tvk__legend { gap: 4px 8px; }
  .tvk__toggle {
    min-height: 32px;
    font-size: 12px;
    padding: 0 10px 0 7px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tvk__digit,
  .tvk__key {
    transition-duration: 0.01ms !important;
  }
  .tvk.is-active .tvk__dot { animation: none; }
}
</style>
