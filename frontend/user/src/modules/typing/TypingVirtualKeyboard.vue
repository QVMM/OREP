<template>
  <div
    class="tvk"
    :class="rootClassList"
    :data-hands="showHands ? 'on' : 'off'"
    :data-expected="targetCode || ''"
    :data-aim-finger="aimFingerId || ''"
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
        @click="toggleHands"
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
            <path class="tvk__hand-wrist" d="M82 278 C74 308 166 308 158 278" />
            <path class="tvk__hand-palm" :d="PALM_PATH" />
            <path class="tvk__hand-palm-line" :d="PALM_CREASE" />
            <g
              v-for="fid in fingersOf(side)"
              :key="fid"
              :class="digitClassName(fid)"
              :data-fid="fid"
              :data-aim="aimFingerId === fid ? '1' : '0'"
              :data-press="isPressDigit(fid) ? '1' : '0'"
              :style="digitStyle(side, fid)"
            >
              <path class="tvk__digit-body" :d="digitPath(fid)" />
              <path v-if="digitCrease(fid)" class="tvk__digit-crease" :d="digitCrease(fid)" />
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
              'is-target': isTargetKey(key.id),
            },
          ]"
          :data-target="isTargetKey(key.id) ? '1' : '0'"
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
  fingerReachDelta,
  homeCodeForFinger,
  resolveFingerTargetCode as resolveFingerTarget,
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
/** fingerId → { pressing, code } */
const fingerState = reactive({})
/** 布局代数：几何量测完成后强制重绘手指位移 */
const layoutGen = ref(0)

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
  if (props.expectedKeyCode) return props.expectedKeyCode
  if (hotId.value) return hotId.value
  return ''
})

const aimFingerId = computed(() => fingerIdForCode(targetCode.value) || '')

const rootClassList = computed(() => ({
  'is-active': props.active,
  'is-composing': props.composing,
  'is-hands': showHands.value,
  'is-plain': !showHands.value,
}))

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
  L4: { x: 48, y: 46 },
  L3: { x: 96, y: 20 },
  L2: { x: 144, y: 10 },
  L1: { x: 192, y: 28 },
  T: { x: 214, y: 168 },
}
const PALM_PATH = 'M40 172 C32 148 52 138 78 136 L92 146 L118 144 L146 146 L172 154 C198 166 214 192 206 226 C196 264 160 286 122 288 C78 290 46 268 38 228 C34 204 36 186 40 172 Z'
const PALM_CREASE = 'M78 168 C96 186 128 192 158 178'
const DIGIT_PATHS = {
  L4: 'M48 46 C38 50 34 64 36 86 C38 116 42 146 48 164 C50 176 70 176 72 162 C66 142 62 112 60 86 C58 64 58 44 48 46 Z',
  L3: 'M96 20 C86 24 82 38 84 60 C86 96 90 136 94 160 C96 172 116 172 118 158 C112 134 108 94 106 60 C104 38 106 18 96 20 Z',
  L2: 'M144 10 C134 14 130 28 132 50 C134 90 136 138 140 162 C142 174 162 174 164 160 C160 134 156 88 154 50 C152 28 154 8 144 10 Z',
  L1: 'M192 28 C180 26 174 40 176 62 C170 102 164 144 168 164 C170 176 192 180 196 166 C198 144 202 100 204 62 C206 42 204 26 192 28 Z',
  R4: 'M48 46 C38 50 34 64 36 86 C38 116 42 146 48 164 C50 176 70 176 72 162 C66 142 62 112 60 86 C58 64 58 44 48 46 Z',
  R3: 'M96 20 C86 24 82 38 84 60 C86 96 90 136 94 160 C96 172 116 172 118 158 C112 134 108 94 106 60 C104 38 106 18 96 20 Z',
  R2: 'M144 10 C134 14 130 28 132 50 C134 90 136 138 140 162 C142 174 162 174 164 160 C160 134 156 88 154 50 C152 28 154 8 144 10 Z',
  R1: 'M192 28 C180 26 174 40 176 62 C170 102 164 144 168 164 C170 176 192 180 196 166 C198 144 202 100 204 62 C206 42 204 26 192 28 Z',
  T: 'M164 198 C184 182 204 164 216 152 C230 140 234 154 222 164 C206 178 188 198 176 216 C170 226 160 222 164 208 Z',
}
const DIGIT_CREASES = {
  L4: 'M40 88 C50 84 62 84 68 88 M42 124 C52 120 64 120 70 124',
  L3: 'M86 64 C96 60 110 60 116 64 M88 108 C98 104 112 104 116 108',
  L2: 'M134 54 C144 50 158 50 164 54 M136 100 C146 96 158 96 162 100',
  L1: 'M176 68 C186 64 200 64 206 68 M174 112 C184 108 198 110 204 114',
  R4: 'M40 88 C50 84 62 84 68 88 M42 124 C52 120 64 120 70 124',
  R3: 'M86 64 C96 60 110 60 116 64 M88 108 C98 104 112 104 116 108',
  R2: 'M134 54 C144 50 158 50 164 54 M136 100 C146 96 158 96 162 100',
  R1: 'M176 68 C186 64 200 64 206 68 M174 112 C184 108 198 110 204 114',
  T: 'M186 176 C196 168 206 162 214 158',
}
const DIGIT_NAILS = {
  L4: { cx: 48, cy: 54, rx: 6.2, ry: 8.2 },
  L3: { cx: 96, cy: 28, rx: 6.6, ry: 8.8 },
  L2: { cx: 144, cy: 18, rx: 6.8, ry: 9.2 },
  L1: { cx: 192, cy: 36, rx: 6.6, ry: 8.8 },
  R4: { cx: 48, cy: 54, rx: 6.2, ry: 8.2 },
  R3: { cx: 96, cy: 28, rx: 6.6, ry: 8.8 },
  R2: { cx: 144, cy: 18, rx: 6.8, ry: 9.2 },
  R1: { cx: 192, cy: 36, rx: 6.6, ry: 8.8 },
  T: { cx: 216, cy: 156, rx: 7.2, ry: 6.2 },
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

function digitCrease(fid) {
  return DIGIT_CREASES[fid] || ''
}

function digitNail(fid) {
  return DIGIT_NAILS[fid] || DIGIT_NAILS.L2
}

function digitClassName(fid) {
  return [
    'tvk__digit',
    aimFingerId.value === fid ? 'is-aim' : '',
    fingerState[fid]?.pressing ? 'is-press' : '',
    fid === 'T' ? 'is-thumb' : '',
  ].filter(Boolean).join(' ')
}

function isPressDigit(fid) {
  return Boolean(fingerState[fid]?.pressing)
}

function isTargetKey(id) {
  return Boolean(targetCode.value) && targetCode.value === id
}

function toggleHands() {
  showHands.value = !showHands.value
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
  if (!showHands.value) {
    return {
      '--finger': 'transparent',
      '--finger-soft': 'transparent',
    }
  }
  const color = fingerColorForCode(id)
  if (!color) return null
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
  const _tick = layoutGen.value
  const home = homePointForDigit(side, fid)
  const target = pointForDigit(side, fid)
  const { hScale, vScale } = handMetrics[side]
  const { x, y } = fingerReachDelta(home, target, {
    hScale,
    vScale,
    flipX: side === 'right',
    press: Boolean(_tick && isPressDigit(fid)),
  })
  return { transform: `translate(${x}px, ${y}px)` }
}

function resolveFingerTargetCode(fingerId) {
  return resolveFingerTarget(fingerId, {
    pressedCodes: [...pressed.value],
    hotId: hotId.value,
    expectedKeyCode: props.expectedKeyCode,
  })
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
  layoutGen.value += 1
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

.tvk.is-hands {
  padding-bottom: 12px;
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

.tvk.is-hands[data-hands="on"] .tvk__key:not(.is-mod) {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--finger) 36%, rgba(255, 255, 255, 0.4)) 0%,
      color-mix(in srgb, var(--finger) 22%, rgba(248, 250, 252, 0.28)) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.88) inset,
    0 0 0 1.5px color-mix(in srgb, var(--finger) 48%, var(--tvk-key-edge)),
    0 3px 0 color-mix(in srgb, var(--finger) 22%, rgba(15, 23, 42, 0.08));
}

.tvk.is-hands[data-hands="on"] .tvk__key.is-home:not(.is-mod) {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--finger) 48%, rgba(255, 255, 255, 0.36)) 0%,
      color-mix(in srgb, var(--finger) 30%, rgba(248, 250, 252, 0.24)) 100%);
}

.tvk.is-plain,
.tvk[data-hands="off"] {
  --finger: transparent;
  --finger-soft: transparent;
}

.tvk.is-plain .tvk__key:not(.is-mod),
.tvk[data-hands="off"] .tvk__key:not(.is-mod) {
  background: var(--tvk-key);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px var(--tvk-key-edge),
    0 3px 0 rgba(15, 23, 42, 0.08),
    0 6px 12px rgba(15, 23, 42, 0.04);
}

.tvk.is-hands[data-hands="on"] .tvk__key.is-home:not(.is-mod)::after {
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
.tvk.is-hands[data-hands="on"] .tvk__key-face {
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.86);
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

.tvk.is-hands[data-hands="on"] .tvk__key.is-target:not(.is-down) {
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
  fill: rgba(255, 255, 255, 0.34);
  stroke: #27272a;
  stroke-width: 2.8;
  stroke-linejoin: round;
  stroke-linecap: round;
  paint-order: stroke fill;
}
.tvk__hand-palm,
.tvk__digit-body {
  filter: drop-shadow(0 0 0.7px #fff) drop-shadow(0 1px 1px rgba(15, 23, 42, 0.16));
}
.tvk__hand-wrist {
  fill: none;
  stroke-width: 3.2;
}
.tvk__hand-palm-line,
.tvk__digit-crease {
  fill: none;
  stroke: #3f3f46;
  stroke-width: 1.35;
  stroke-linecap: round;
  opacity: 0.72;
}
.tvk__digit {
  transform-box: view-box;
  transform-origin: center bottom;
  transition: transform 0.16s cubic-bezier(0.22, 0.9, 0.3, 1);
  will-change: transform;
}
.tvk__digit-nail {
  fill: rgba(255, 255, 255, 0.62);
  stroke: #3f3f46;
  stroke-width: 1.35;
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
  .tvk__digit-body { stroke-width: 3; }
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
