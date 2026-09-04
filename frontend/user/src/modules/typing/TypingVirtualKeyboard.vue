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
      <!-- 指法色带键盘 -->
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

      <!-- 标准指法手势层：指尖圆点 + 简化手掌轮廓，位置跟键实时同步 -->
      <div v-if="showHands" class="tvk__hands" aria-hidden="true">
        <!-- 左手腕轮廓 -->
        <svg class="tvk__palm tvk__palm--left" :style="palmStyle('left')" viewBox="0 0 120 90">
          <ellipse cx="58" cy="62" rx="46" ry="28" fill="currentColor" opacity="0.14" />
          <path d="M22 48 C28 28 48 18 62 22 C74 26 86 40 90 54 C78 48 66 46 54 48 C42 50 30 52 22 48Z" fill="currentColor" opacity="0.2" />
        </svg>
        <!-- 右手腕轮廓 -->
        <svg class="tvk__palm tvk__palm--right" :style="palmStyle('right')" viewBox="0 0 120 90">
          <ellipse cx="62" cy="62" rx="46" ry="28" fill="currentColor" opacity="0.14" />
          <path d="M98 48 C92 28 72 18 58 22 C46 26 34 40 30 54 C42 48 54 46 66 48 C78 50 90 52 98 48Z" fill="currentColor" opacity="0.2" />
        </svg>

        <div
          v-for="finger in visibleFingers"
          :key="finger.id"
          class="tvk__finger"
          :class="{
            'is-press': finger.pressing,
            'is-left': finger.hand === 'left',
            'is-right': finger.hand === 'right',
            'is-thumb': finger.id === 'T',
          }"
          :style="fingerStyle(finger)"
        >
          <span class="tvk__finger-tip" :style="{ background: finger.color }">
            <i>{{ finger.short }}</i>
          </span>
          <span class="tvk__finger-bone" :style="{ background: finger.color }" />
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

const activeFingerHint = computed(() => {
  if (!props.active && !pressed.value.size) return showHands.value ? 'ASDF / JKL; 归位 · 开始输入' : '开始输入后点亮'
  const code = hotId.value || [...pressed.value][0] || ''
  const fid = fingerIdForCode(code)
  const f = FINGERS.find((x) => x.id === fid)
  if (f) return `${f.name} · ${codeLabel(code)}`
  return '跟打反馈'
})

const visibleFingers = computed(() =>
  FINGERS.map((f) => {
    const st = fingerState[f.id] || { x: 0, y: 0, pressing: false, code: f.home }
    return { ...f, ...st }
  })
)

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

function keyCenter(code) {
  const el = keyEls[code]
  const board = boardRef.value
  if (!el || !board) return null
  const br = board.getBoundingClientRect()
  const kr = el.getBoundingClientRect()
  if (!br.width || !br.height) return null
  return {
    x: ((kr.left + kr.width / 2) - br.left) / br.width * 100,
    y: ((kr.top + kr.height / 2) - br.top) / br.height * 100,
  }
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
  for (const f of FINGERS) {
    const code = resolveFingerTargetCode(f.id)
    const pos = keyCenter(code) || keyCenter(f.home)
    if (!pos) continue
    // 拇指略向下，其余指尖略上移，避免完全挡住键帽字
    const yBias = f.id === 'T' ? 10 : -8
    const pressing = pressed.value.has(code) || hotId.value === code
    fingerState[f.id] = {
      x: pos.x,
      y: Math.min(96, Math.max(4, pos.y + yBias * 0.15)),
      pressing,
      code,
    }
  }
}

function scheduleFingerLayout() {
  if (layoutRaf) return
  layoutRaf = requestAnimationFrame(layoutFingers)
}

function fingerStyle(finger) {
  const st = fingerState[finger.id]
  if (!st) return { opacity: 0 }
  return {
    left: `${st.x}%`,
    top: `${st.y}%`,
    '--fc': finger.color,
    opacity: 1,
  }
}

function palmStyle(side) {
  // 掌心停在 home 行两侧
  const leftHome = keyCenter('KeyD')
  const rightHome = keyCenter('KeyK')
  const pos = side === 'left' ? leftHome : rightHome
  if (!pos) return { opacity: 0 }
  return {
    left: `${pos.x + (side === 'left' ? -6 : 6)}%`,
    top: `${Math.min(92, pos.y + 18)}%`,
    opacity: props.active || pressed.value.size ? 0.95 : 0.55,
  }
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
}

.tvk.is-hands .tvk__key:not(.is-mod) {
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--finger-soft) 55%, #fff) 0%, color-mix(in srgb, var(--finger-soft) 35%, #f1f5f9) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px color-mix(in srgb, var(--finger) 28%, var(--tvk-key-edge)),
    0 3px 0 rgba(15, 23, 42, 0.07);
}

.tvk.is-hands .tvk__key.is-home:not(.is-mod)::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: 5px;
  width: 10px;
  height: 2px;
  border-radius: 2px;
  background: color-mix(in srgb, var(--finger) 70%, #64748b);
  transform: translateX(-50%);
  opacity: 0.75;
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

.tvk__key.is-target:not(.is-down) {
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1.5px color-mix(in srgb, var(--finger, var(--tvk-accent)) 65%, transparent),
    0 0 16px color-mix(in srgb, var(--finger, var(--tvk-accent)) 35%, transparent);
}

.tvk__key.is-hot:not(.is-down) {
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px rgba(249, 115, 22, 0.28),
    0 0 16px rgba(249, 115, 22, 0.18);
}

.tvk__key.is-ok { animation: tvk-ok 0.32s ease; }
.tvk__key.is-bad { animation: tvk-bad 0.32s ease; }

/* —— 指法手势层 —— */
.tvk__hands {
  pointer-events: none;
  position: absolute;
  inset: 0;
  z-index: 3;
  overflow: visible;
}

.tvk__palm {
  position: absolute;
  width: 88px;
  height: 66px;
  color: #64748b;
  transform: translate(-50%, -30%);
  transition: left 0.18s cubic-bezier(0.22, 0.9, 0.3, 1), top 0.18s cubic-bezier(0.22, 0.9, 0.3, 1), opacity 0.25s ease;
}

.tvk__finger {
  position: absolute;
  width: 0;
  height: 0;
  transform: translate(-50%, -50%);
  transition:
    left 0.14s cubic-bezier(0.22, 0.9, 0.3, 1),
    top 0.14s cubic-bezier(0.22, 0.9, 0.3, 1);
  will-change: left, top;
}

.tvk__finger-tip {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 22px;
  height: 26px;
  border-radius: 50% 50% 46% 46%;
  transform: translate(-50%, -58%);
  box-shadow:
    0 2px 0 rgba(255, 255, 255, 0.35) inset,
    0 4px 10px rgba(15, 23, 42, 0.18);
  border: 1.5px solid rgba(255, 255, 255, 0.55);
  display: grid;
  place-items: center;
  transition: transform 0.1s ease, filter 0.1s ease;
}

.tvk__finger-tip i {
  font-style: normal;
  font-size: 9px;
  font-weight: 800;
  color: rgba(15, 23, 42, 0.78);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.35);
}

.tvk__finger-bone {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 10px;
  height: 18px;
  border-radius: 8px;
  transform: translate(-50%, 10%);
  opacity: 0.45;
  filter: saturate(0.9);
}

.tvk__finger.is-press .tvk__finger-tip {
  transform: translate(-50%, -42%) scale(0.88);
  filter: brightness(1.05);
}

.tvk__finger.is-thumb .tvk__finger-tip {
  width: 26px;
  height: 20px;
  border-radius: 40%;
  transform: translate(-50%, -40%) rotate(-18deg);
}

.tvk__finger.is-thumb.is-press .tvk__finger-tip {
  transform: translate(-50%, -28%) rotate(-18deg) scale(0.9);
}

.tvk__finger.is-left .tvk__finger-bone {
  transform: translate(-50%, 8%) rotate(8deg);
}

.tvk__finger.is-right .tvk__finger-bone {
  transform: translate(-50%, 8%) rotate(-8deg);
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
    --tvk-key-h: clamp(30px, 4.55vh, 40px);
    --tvk-key-fs: clamp(11.5px, 1.45vh, 13.5px);
    --tvk-row-gap: clamp(3px, 0.55vh, 7px);
    padding: 10px 16px 8px;
  }
  .tvk__row {
    justify-content: stretch;
    gap: clamp(3px, 0.5vh, 7px);
    padding-right: 0;
  }
  .tvk__key {
    flex: 1 1 0;
    width: auto;
    min-width: 0;
    border-radius: 9px;
  }
  .tvk__key.is-mid { flex: 1.45 1 0; }
  .tvk__key.is-wide { flex: 2.05 1 0; }
  .tvk__key.is-space { flex: 6.6 1 0; --w: auto; }
  .tvk__key.is-mod .tvk__main { font-size: 11px; }
  .tvk__finger-tip { width: 24px; height: 28px; }
  .tvk__finger-tip i { font-size: 10px; }
  .tvk__finger.is-thumb .tvk__finger-tip { width: 28px; height: 20px; }
  .tvk__palm { width: 96px; height: 70px; }
}

@media (min-width: 1100px) and (max-height: 820px) {
  .tvk {
    --tvk-key-h: clamp(28px, 4.15vh, 34px);
    --tvk-key-fs: 12px;
    --tvk-row-gap: 3px;
    padding: 8px 14px 6px;
  }
  .tvk__head { margin-bottom: 6px; }
  .tvk__toggle { min-height: 30px; padding: 0 10px 0 7px; }
  .tvk__legend { display: none; }
  .tvk__palm { width: 80px; height: 56px; }
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
  .tvk__finger-tip { width: 18px; height: 22px; }
  .tvk__finger-tip i { font-size: 8px; }
  .tvk__palm { width: 64px; height: 48px; }
  .tvk__hint { display: none; }
  .tvk__legend { gap: 4px 8px; }
  .tvk__toggle {
    min-height: 32px;
    font-size: 12px;
    padding: 0 10px 0 7px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tvk__finger,
  .tvk__palm,
  .tvk__key {
    transition-duration: 0.01ms !important;
  }
  .tvk.is-active .tvk__dot { animation: none; }
}
</style>
