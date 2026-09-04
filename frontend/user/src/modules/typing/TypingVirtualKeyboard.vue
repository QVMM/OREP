<template>
  <div
    class="tvk"
    :class="{
      'is-active': active,
      'is-composing': composing,
      'is-hands': showHands,
      'is-plain': !showHands,
    }"
    :data-hands="showHands ? 'on' : 'off'"
    :data-expected="targetCode || ''"
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
        :aria-label="showHands ? '关闭指法标注' : '开启指法标注'"
        @click="showHands = !showHands"
      >
        <span class="tvk__toggle-track" aria-hidden="true" />
        <span class="tvk__toggle-label">指法{{ showHands ? '开' : '关' }}</span>
      </button>
    </div>

    <div class="tvk__board">
      <div v-for="(row, ri) in rows" :key="ri" class="tvk__row" :style="{ '--pad': row.pad }">
        <div
          v-for="key in row.keys"
          :key="key.id"
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
              'has-badge': Boolean(badgeFor(key)),
            },
          ]"
          :data-target="isTargetKey(key.id) ? '1' : '0'"
          :style="keyFingerStyle(key.id)"
        >
          <span class="tvk__key-face">
            <span class="tvk__main">{{ key.label }}</span>
            <span v-if="key.sub" class="tvk__sub">{{ key.sub }}</span>
          </span>
          <span
            v-if="badgeFor(key)"
            class="tvk__badge"
            :class="{
              'is-home': isHomeKey(key.id),
              'is-aim': isTargetKey(key.id),
            }"
            :style="{ background: badgeFor(key).color }"
            :data-fid="badgeFor(key).id"
          >{{ badgeFor(key).short }}</span>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  FINGERS,
  fingerColorForCode,
  fingerForCode,
  fingerIdForCode,
} from './fingerMap'

const props = defineProps({
  active: { type: Boolean, default: false },
  composing: { type: Boolean, default: false },
  lastHit: { type: String, default: null },
  lastKeyCode: { type: String, default: '' },
  expectedKeyCode: { type: String, default: '' },
})

const showHands = ref(true)
const pressed = ref(new Set())
const hotId = ref('')
const flashId = ref('')
const flashKind = ref(null)

let flashTimer = null
let hotTimer = null

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

const legendFingers = computed(() =>
  FINGERS.filter((f) => f.id !== 'T').concat(FINGERS.filter((f) => f.id === 'T'))
)

const targetCode = computed(() => {
  if (props.expectedKeyCode) return props.expectedKeyCode
  if (hotId.value) return hotId.value
  return ''
})

const activeFingerHint = computed(() => {
  if (!props.active && !pressed.value.size) {
    return showHands.value ? 'ASDF / JKL; 归位 · 开始输入' : '开始输入后点亮'
  }
  const code = hotId.value || [...pressed.value][0] || ''
  const fid = fingerIdForCode(code)
  const f = FINGERS.find((x) => x.id === fid)
  if (f) return `${f.name} · ${codeLabel(code)}`
  return '跟打反馈'
})

function key(id, label, sub = '', size = 'std', mod = false) {
  return { id, label, sub, size, mod }
}

function numRow() {
  const tops = '!@#$%^&*()'
  return '1234567890'.split('').map((n, i) => key(`Digit${n}`, n, tops[i] || ''))
}

function letterRow(upper, lower) {
  return upper.split('').map((U, i) => key(`Key${U}`, U, lower[i]))
}

function isHomeKey(id) {
  return HOME_CODES.has(id)
}

function isTargetKey(id) {
  return Boolean(targetCode.value) && targetCode.value === id
}

/** 字母/数字/符号键 + 空格显示指法圆标；功能键只靠色带，避免挡住字 */
function badgeFor(keyItem) {
  if (!showHands.value || !keyItem || keyItem.mod) return null
  return fingerForCode(keyItem.id)
}

function keyFingerStyle(id) {
  if (!showHands.value) {
    return { '--finger': 'transparent', '--finger-soft': 'transparent' }
  }
  const color = fingerColorForCode(id)
  if (!color) return null
  return { '--finger': color, '--finger-soft': `${color}33` }
}

function codeLabel(code) {
  if (!code) return ''
  if (code.startsWith('Key')) return code.slice(3)
  if (code.startsWith('Digit')) return code.slice(5)
  if (code === 'Space') return '空格'
  if (code === 'Semicolon') return ';'
  return code
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
  clearTimeout(hotTimer)
  hotTimer = setTimeout(() => {
    if (hotId.value === id) hotId.value = ''
  }, 220)
}

function markUp(id) {
  if (!id) return
  const next = new Set(pressed.value)
  next.delete(id)
  pressed.value = next
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

onMounted(() => {
  window.addEventListener('keydown', onKeyDown, true)
  window.addEventListener('keyup', onKeyUp, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown, true)
  window.removeEventListener('keyup', onKeyUp, true)
  clearTimeout(flashTimer)
  clearTimeout(hotTimer)
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
}
.tvk__toggle:hover { border-color: #94a3b8; background: #f8fafc; }
.tvk__toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.32);
}
.tvk__toggle.is-on {
  border-color: #ea580c;
  background: #f97316;
  color: #fff;
}
.tvk__toggle-track {
  position: relative;
  width: 28px;
  height: 16px;
  flex: none;
  border-radius: 999px;
  background: #e2e8f0;
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
.tvk__toggle.is-on .tvk__toggle-track { background: rgba(255, 255, 255, 0.38); }
.tvk__toggle.is-on .tvk__toggle-track::after { left: 14px; }

.tvk__board {
  position: relative;
  z-index: 1;
  display: grid;
  gap: var(--tvk-row-gap);
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
  min-height: var(--tvk-key-h);
  flex: 0 0 auto;
  border-radius: 8px;
  background: var(--tvk-key);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px var(--tvk-key-edge),
    0 3px 0 rgba(15, 23, 42, 0.08),
    0 6px 12px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.tvk:has(.tvk__badge) .tvk__key:not(.is-mod) {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--finger) 38%, #fff) 0%,
      color-mix(in srgb, var(--finger) 22%, #f8fafc) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 0 0 1.5px color-mix(in srgb, var(--finger) 42%, var(--tvk-key-edge)),
    0 3px 0 color-mix(in srgb, var(--finger) 18%, rgba(15, 23, 42, 0.08));
}

.tvk:has(.tvk__badge) .tvk__key.is-home:not(.is-mod) {
  background:
    linear-gradient(180deg,
      color-mix(in srgb, var(--finger) 52%, #fff) 0%,
      color-mix(in srgb, var(--finger) 32%, #f8fafc) 100%);
}

.tvk:not(:has(.tvk__badge)) .tvk__key:not(.is-mod) {
  --finger: transparent;
  background: var(--tvk-key);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 1px var(--tvk-key-edge),
    0 3px 0 rgba(15, 23, 42, 0.08),
    0 6px 12px rgba(15, 23, 42, 0.04);
}

.tvk__key.is-mid { --w: 54px; }
.tvk__key.is-wide { --w: 76px; }
.tvk__key.is-space { --w: min(320px, 42vw); }

.tvk__key-face {
  position: relative;
  z-index: 2;
  height: 100%;
  display: grid;
  place-content: center;
  padding-bottom: 0;
  color: var(--tvk-ink);
  font-size: var(--tvk-key-fs);
  font-weight: 700;
  user-select: none;
}
.tvk__key.has-badge .tvk__key-face {
  padding-bottom: 13px;
}

.tvk__key.is-mod .tvk__main {
  font-size: 11px;
  font-weight: 650;
  color: #64748b;
  text-transform: lowercase;
}

.tvk__sub { display: none; }

/* 指法圆标贴在键帽底边，绝不盖住中间字母 */
.tvk__badge {
  pointer-events: none;
  position: absolute;
  left: 50%;
  bottom: 3px;
  z-index: 1;
  width: 15px;
  height: 15px;
  border-radius: 999px;
  transform: translateX(-50%);
  display: grid;
  place-items: center;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
  color: #1f2937;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.7) inset,
    0 1px 2px rgba(15, 23, 42, 0.18);
}
.tvk__badge.is-home,
.tvk__badge.is-aim {
  width: 16px;
  height: 16px;
  font-size: 10px;
}
.tvk__badge.is-aim {
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.85) inset,
    0 0 0 2px color-mix(in srgb, var(--finger) 55%, transparent),
    0 0 10px color-mix(in srgb, var(--finger) 45%, transparent);
}

.tvk__ripple {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 60%, rgba(249, 115, 22, 0.35), transparent 62%);
  opacity: 0;
}

.tvk__key.is-down {
  transform: translateY(2px) scale(0.98);
  background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%);
}
.tvk__key.is-down .tvk__ripple { opacity: 1; }

.tvk:has(.tvk__badge) .tvk__key.is-target:not(.is-down) {
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 0 0 2.5px var(--finger, var(--tvk-accent)),
    0 0 0 5px color-mix(in srgb, var(--finger, var(--tvk-accent)) 28%, transparent);
}

.tvk__key.is-ok { animation: tvk-ok 0.32s ease; }
.tvk__key.is-bad { animation: tvk-bad 0.32s ease; }

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
}

@keyframes tvk-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.75; transform: scale(0.92); }
}
@keyframes tvk-ok {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
  40% {
    background: linear-gradient(180deg, #ecfdf5, #d1fae5);
    box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.45);
  }
  100% { box-shadow: 0 3px 0 rgba(15, 23, 42, 0.08); }
}
@keyframes tvk-bad {
  0% { transform: translateY(0); }
  25% { transform: translateY(2px) translateX(-1px); background: linear-gradient(180deg, #fef2f2, #fecaca); }
  100% { transform: translateY(0); }
}

@media (min-width: 1100px) {
  .tvk {
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
  .tvk__badge { width: 16px; height: 16px; font-size: 10px; bottom: 4px; }
  .tvk__key.has-badge .tvk__key-face { padding-bottom: 16px; }
}

@media (min-width: 1100px) and (max-height: 920px) {
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
  .tvk__hint { display: none; }
  .tvk__badge { width: 12px; height: 12px; font-size: 8px; bottom: 2px; }
  .tvk__key.has-badge .tvk__key-face { padding-bottom: 11px; }
  .tvk__toggle { min-height: 32px; font-size: 12px; padding: 0 10px 0 7px; }
}

@media (prefers-reduced-motion: reduce) {
  .tvk__key { transition-duration: 0.01ms !important; }
  .tvk.is-active .tvk__dot { animation: none; }
}
</style>
