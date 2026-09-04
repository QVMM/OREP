<template>
  <AiAppShell mode="workspace" width="fluid" class="typing-play-shell">
    <template #header>
      <AiAppHeader
        app="typing"
        mode="workspace"
        :title="headerTitle"
        :subtitle="headerSubtitle"
        :status="statusLabel"
        back-label="退出"
        back-to="/typing-practice"
      >
        <template #actions>
          <button
            v-if="engineStatus === 'running'"
            type="button"
            class="typing-mini-btn"
            @click="pause"
          >
            暂停
          </button>
          <button
            v-else-if="engineStatus === 'paused'"
            type="button"
            class="typing-mini-btn"
            @click="resume"
          >
            继续
          </button>
          <button type="button" class="typing-mini-btn typing-mini-btn--danger" @click="endEarly">
            结束并提交
          </button>
        </template>
      </AiAppHeader>
    </template>

    <div
      ref="playRootRef"
      class="typing-play"
      :class="{ 'is-code-session': isCodeMode }"
      :style="layoutStyle"
    >
      <!-- 金山式顶栏指标 -->
      <div class="typing-play__hud" aria-live="polite">
        <div class="hud-item hud-item--time">
          <strong>{{ timeDisplay }}</strong>
          <span>{{ isRanked ? '剩余时间' : '剩余' }}</span>
        </div>
        <div class="hud-item">
          <strong>{{ live.cpm }}</strong>
          <span>速度 CPM</span>
        </div>
        <div class="hud-item">
          <strong>{{ live.accuracy }}%</strong>
          <span>正确率</span>
        </div>
        <div class="hud-item">
          <strong>{{ live.correctChars }}</strong>
          <span>正确字</span>
        </div>
        <div class="hud-item">
          <strong>{{ progressLabel }}</strong>
          <span>进度</span>
        </div>
        <div v-if="isCodeMode" class="hud-item">
          <strong>{{ caretLineDisplay }}</strong>
          <span>当前行</span>
        </div>
      </div>

      <!--
        金山打字通形态：
        - 正文即练习区，已打/未打/错误直接着色
        - 散文空格按 spaceGlyph：bullet · / bar 下划线 / invisible 空隙
        - 代码模式空格强制 invisible；行首缩进自动跳过
        - 布局随视口动态缩放
      -->
      <div
        ref="boardRef"
        class="typing-play__board"
        :class="{
          'is-paused': engineStatus === 'paused',
          'is-idle': engineStatus === 'idle',
          'is-composing': composing,
          'is-code-board': isCodeMode,
        }"
        role="region"
        aria-label="打字练习区"
        @mousedown.prevent="focusInput"
        @click="focusInput"
      >
        <div class="typing-play__status-row">
          <span v-if="engineStatus === 'idle'">{{ isCodeMode ? '点击编辑器开始输入' : '点击文案开始输入' }}</span>
          <span v-else-if="engineStatus === 'paused'">已暂停 · 点击继续 · Esc 暂停</span>
          <span v-else-if="isRanked">排位赛 · 10 分钟 · 1500 字</span>
          <span v-else-if="isCodeMode">{{ codeLangLabel }} · 自动缩进 · Tab={{ codeIndentHint }}</span>
          <span v-else>自主练习</span>
          <div
            v-if="!isCodeMode"
            class="space-glyph-switch"
            role="group"
            aria-label="空格显示"
          >
            <button
              v-for="opt in spaceGlyphOptions"
              :key="opt.value"
              type="button"
              class="space-glyph-switch__btn"
              :class="{ 'is-active': spaceGlyph === opt.value }"
              :title="opt.hint"
              :aria-pressed="spaceGlyph === opt.value"
              @click.stop="setSpaceGlyph(opt.value)"
            >{{ opt.label }}</button>
          </div>
          <span v-if="composing" class="typing-play__composing-tag">输入中…</span>
        </div>

        <div
          v-if="isCodeMode && codeTips.length && showCodeTips"
          class="typing-code-tips"
          aria-label="编码规范"
        >
          <span class="typing-code-tips__tag">规范</span>
          <span
            v-for="(tip, i) in codeTips"
            :key="i"
            class="typing-code-tips__item"
          >{{ tip }}</span>
          <button
            type="button"
            class="typing-code-tips__hide"
            @click.stop="showCodeTips = false"
          >收起</button>
        </div>

        <div
          ref="viewportRef"
          class="typing-viewport"
          :class="{
            'is-latin': !isCodeMode && (cfg.lang === 'en' || cfg.lang === 'mixed'),
            'is-en': !isCodeMode && cfg.lang === 'en',
            'is-code': isCodeMode,
            [`space-glyph-${effectiveSpaceGlyph}`]: true,
          }"
          :style="codeViewportStyle"
        >
          <div
            class="typing-lines"
            :style="{ transform: `translateY(-${scrollLine * lineHeightPx}px)` }"
          >
            <div
              v-for="(line, lineIdx) in textLines"
              :key="lineIdx"
              class="typing-line"
              :class="{
                'is-code-line': isCodeMode,
                'is-active-line': isCodeMode && lineIdx === caretLine,
              }"
              :style="{ height: `${lineHeightPx}px` }"
            >
              <span
                v-if="isCodeMode"
                class="typing-gutter"
                aria-hidden="true"
              >{{ lineIdx + 1 }}</span>
              <span
                v-for="(ch, chIdx) in line.chars"
                :key="line.start + chIdx"
                :ref="(el) => setCharRef(line.start + chIdx, el)"
                class="typing-ch"
                :class="[
                  charClass(line.start + chIdx),
                  {
                    'is-space': ch === ' ',
                    'is-tab': ch === '\t',
                    'is-newline': ch === '\n',
                    'is-auto-indent': isAutoIndentAt(line.start + chIdx),
                    'is-auto-indent-start': isAutoIndentStart(line.start + chIdx),
                  },
                ]"
                :data-idx="line.start + chIdx"
                :aria-label="charAriaLabel(ch, line.start + chIdx)"
              >{{ displayChar(ch, line.start + chIdx) }}</span>
            </div>
          </div>
        </div>

        <!-- 透明输入：跟在当前字后面，承接 IME 候选 -->
        <textarea
          ref="inputRef"
          class="typing-caret-input"
          :value="inputValue"
          :style="caretInputStyle"
          autocomplete="off"
          autocorrect="off"
          autocapitalize="off"
          spellcheck="false"
          :disabled="engineStatus === 'finished'"
          aria-label="打字输入"
          @input="onInput"
          @compositionstart="onCompositionStart"
          @compositionupdate="onCompositionUpdate"
          @compositionend="onCompositionEnd"
          @keydown="onKeydown"
          @blur="onInputBlur"
        />

        <!-- composition 时在光标下展示临时拼音，贴近金山体验 -->
        <div
          v-if="composing && compositionText"
          class="typing-composition"
          :style="compositionStyle"
        >
          {{ compositionText }}
        </div>
      </div>

      <div class="typing-play__progress" aria-hidden="true">
        <div class="typing-play__bar" :style="{ width: `${Math.round((live.progress || 0) * 100)}%` }" />
      </div>

      <!-- 模拟键盘 + 手势反馈（自主练习 / 代码练习都保留） -->
      <TypingVirtualKeyboard
        ref="keyboardRef"
        :active="engineStatus === 'running' || composing"
        :composing="composing"
        :last-hit="kbLastHit"
        :last-key-code="kbLastKeyCode"
      />
    </div>
  </AiAppShell>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue'
import { useRouter } from 'vue-router'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
import {
  DURATION_UNSYNCED_MESSAGE,
  flushTypingSessionKeepalive,
  flushTypingSessionQueue,
  saveTypingSession,
} from '@/modules/typing/api'
import { buildPracticeText } from '@/modules/typing/catalog'
import {
  CODE_LANG_OPTIONS,
  buildCodeTokenClasses,
  detectCodeLanguage,
  getStyleTips,
  indentUnitForLang,
  looksLikeCode,
  normalizeCodeText,
} from '@/modules/typing/codePractice'
import { charsOf, createTypingEngine, isLeadingIndentChar } from '@/modules/typing/engine'
import { RANKED_TEXT_VERSION } from '@/modules/typing/rankedText'
import {
  buildTypingSessionPayload,
  newClientSessionId,
  resolveVisibilityAction,
  shouldPersistTypingSession,
} from '@/modules/typing/sessionPersist'
import {
  loadPrefs,
  normalizeSpaceGlyph,
  resolveSpaceGlyph,
  saveLastResult,
  savePrefs,
  SPACE_GLYPH_OPTIONS,
} from '@/modules/typing/storage'
import TypingVirtualKeyboard from '@/modules/typing/TypingVirtualKeyboard.vue'

/** 视口默认显示 4 行；代码模式更多上下文 */
const VISIBLE_LINES = 4
const CODE_VISIBLE_LINES = 8
/** 前 FIXED_LINES 行固定不滚；caret 进入第 FIXED_LINES+1 行起才滚动 */
const FIXED_LINES = 3
const CODE_FIXED_LINES = 4

const router = useRouter()
const playRootRef = ref(null)
const boardRef = ref(null)
const viewportRef = ref(null)
const inputRef = ref(null)
const keyboardRef = ref(null)
const inputValue = ref('')
const composing = ref(false)
const compositionText = ref('')
const engineStatus = ref('idle')
const targetChars = ref([])
const charStates = ref([])
const caret = ref(0)
const charsPerLine = ref(28)
/** 随屏幕动态调整 */
const lineHeightPx = ref(48)
const boardFontPx = ref(24)
const layoutStyle = computed(() => ({
  '--line-h': `${lineHeightPx.value}px`,
  '--board-font': `${boardFontPx.value}px`,
  '--hud-num': `${Math.round(boardFontPx.value * 0.95)}px`,
}))
const caretInputStyle = ref({
  left: '16px',
  top: '52px',
  width: '2px',
  height: '48px',
})
const compositionStyle = ref({
  left: '16px',
  top: '96px',
})

/** 虚拟键盘：最近一次落字反馈 */
const kbLastHit = ref(null)
const kbLastKeyCode = ref('')
let lastPhysicalCode = ''
let prevCaret = 0
let prevCorrect = 0

/** 字符 DOM 引用，用于把输入框锚到当前光标字 */
const charEls = new Map()

const cfg = reactive({
  playMode: 'practice',
  mode: 'timed',
  durationSec: 300,
  lang: 'zh',
  difficulty: 2,
  sourceType: 'catalog',
  customText: '',
  textVersion: null,
  codeLang: 'javascript',
})

/** 代码练习：每个字符的语法 token 类名 */
const tokenClasses = ref([])
const showCodeTips = ref(true)
const spaceGlyph = ref(normalizeSpaceGlyph(loadPrefs().spaceGlyph))
const spaceGlyphOptions = SPACE_GLYPH_OPTIONS

function setSpaceGlyph(mode) {
  spaceGlyph.value = normalizeSpaceGlyph(mode)
  savePrefs({ spaceGlyph: spaceGlyph.value })
}

const live = reactive({
  cpm: 0,
  accuracy: 100,
  correctChars: 0,
  remainingSec: 300,
  progress: 0,
  typedChars: 0,
  targetChars: 0,
})

let engine = null
let tickTimer = null
let finished = false
let resizeObserver = null
let refocusTimer = null
let clientSessionId = ''
let pauseReason = ''
let lastCheckpointAt = 0

const isRanked = computed(() => cfg.playMode === 'ranked')

/** 代码练习：保留换行/缩进，等宽 + 行号 + 语法高亮 */
const isCodeMode = computed(() => {
  if (isRanked.value) return false
  if (cfg.playMode === 'code' || cfg.sourceType === 'code') return true
  return looksLikeCode(cfg.customText || targetChars.value.join(''))
})

/** 代码练习强制 invisible，避免空格看起来像 `_` 或真实 `·` */
const effectiveSpaceGlyph = computed(() =>
  resolveSpaceGlyph(spaceGlyph.value, { code: isCodeMode.value })
)

const codeLangLabel = computed(() => {
  const lang = cfg.codeLang || 'javascript'
  return CODE_LANG_OPTIONS.find((o) => o.value === lang)?.label || lang
})

const codeTips = computed(() => {
  if (!isCodeMode.value) return []
  return getStyleTips(cfg.codeLang || 'javascript').slice(0, 3)
})

/** 按语言约定缩进：JS/HTML/CSS/JSON 2 空格；Python/Java 4 空格 */
const codeIndentUnit = computed(() => indentUnitForLang(cfg.codeLang || 'javascript'))

const codeIndentHint = computed(() => {
  const unit = codeIndentUnit.value
  if (unit === '\t') return 'Tab'
  return `${unit.length} 空格`
})

const caretLineDisplay = computed(() => {
  const total = Math.max(1, textLines.value.length)
  return `${(caretLine.value || 0) + 1}/${total}`
})

const codeViewportStyle = computed(() => {
  if (!isCodeMode.value) return undefined
  const lines = CODE_VISIBLE_LINES
  return { height: `calc(var(--line-h, 48px) * ${lines})` }
})

const headerTitle = computed(() => {
  if (isRanked.value) return '排位赛'
  if (isCodeMode.value) return '代码练习'
  return '自主练习'
})
const headerSubtitle = computed(() => {
  if (isRanked.value) return '路演赛题 · 10 分钟 · 1500 字'
  if (isCodeMode.value) {
    const m = Math.floor(cfg.durationSec / 60)
    const s = cfg.durationSec % 60
    const dur = s ? `${m} 分 ${s} 秒` : `${m} 分钟`
    return `${codeLangLabel.value} · 语法高亮 · ${dur}`
  }
  const m = Math.floor(cfg.durationSec / 60)
  const s = cfg.durationSec % 60
  return s ? `${m} 分 ${s} 秒` : `${m} 分钟`
})

const statusLabel = computed(() => {
  if (engineStatus.value === 'paused') return '已暂停'
  if (engineStatus.value === 'running') return '进行中'
  if (engineStatus.value === 'finished') return '已结束'
  return '准备就绪'
})

const timeDisplay = computed(() => {
  const sec = Math.max(0, live.remainingSec ?? 0)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
})

const progressLabel = computed(() => {
  const total = live.targetChars || targetChars.value.length || 1
  const done = Math.min(live.typedChars || 0, total)
  return `${done}/${total}`
})


const textLines = computed(() => {
  const all = targetChars.value
  const cpl = Math.max(8, charsPerLine.value)
  if (isCodeMode.value) return buildCodeLines(all, cpl)
  const lines = []
  for (let i = 0; i < all.length; i += cpl) {
    lines.push({ start: i, chars: all.slice(i, i + cpl) })
  }
  if (!lines.length) lines.push({ start: 0, chars: [] })
  return lines
})

const caretLine = computed(() => {
  const lines = textLines.value
  const c = caret.value || 0
  for (let i = 0; i < lines.length; i += 1) {
    const start = lines[i].start
    const end = start + lines[i].chars.length
    // caret 落在本行范围内，或落在末行之后
    if (c < end || i === lines.length - 1) return i
  }
  return 0
})

/**
 * 前 FIXED 行固定（scroll=0）；
 * 之后：scroll = caretLine - (fixed - 1)，
 * 使当前行落在视口靠前位置，上方保留上下文。
 */
const scrollLine = computed(() => {
  const line = caretLine.value
  const fixed = isCodeMode.value ? CODE_FIXED_LINES : FIXED_LINES
  if (line < fixed) return 0
  return line - (fixed - 1)
})

/** 按真实换行折行；过长行再按列软折 */
function buildCodeLines(chars, maxCols) {
  const lines = []
  let start = 0
  let col = 0
  let buf = []
  const flush = (nextStart) => {
    lines.push({ start, chars: buf })
    start = nextStart
    buf = []
    col = 0
  }
  for (let i = 0; i < chars.length; i += 1) {
    const ch = chars[i]
    if (ch === '\n') {
      buf.push(ch)
      flush(i + 1)
      continue
    }
    const w = ch === '\t' ? 2 : 1
    if (col + w > maxCols && buf.length) {
      flush(i)
    }
    buf.push(ch)
    col += w
  }
  if (buf.length || !lines.length) lines.push({ start, chars: buf })
  return lines
}

function setCharRef(idx, el) {
  if (el) charEls.set(idx, el)
  else charEls.delete(idx)
}

function isAutoIndentAt(idx) {
  return isCodeMode.value && isLeadingIndentChar(targetChars.value, idx)
}

function isAutoIndentStart(idx) {
  return isAutoIndentAt(idx) && (idx === 0 || !isLeadingIndentChar(targetChars.value, idx - 1))
}

/** 光标已落在行首缩进之后的第一个实义字符（空格/Tab 视为可选 no-op） */
function isAfterAutoIndent(idx = caret.value) {
  if (!isCodeMode.value) return false
  const target = targetChars.value
  if (idx <= 0 || idx >= target.length) return false
  if (isLeadingIndentChar(target, idx)) return false
  const ch = target[idx]
  if (ch === '\n') return false
  return isLeadingIndentChar(target, idx - 1)
}

function displayChar(ch, idx) {
  if (ch === '\n') return '↵'
  if (isAutoIndentAt(idx)) return '\u00a0'
  if (ch === '\t') return '····'
  if (ch === ' ') {
    if (effectiveSpaceGlyph.value === 'bullet') return '·'
    return '\u00a0'
  }
  return ch
}

function charAriaLabel(ch, idx) {
  if (isAutoIndentAt(idx)) return '自动缩进'
  if (ch === ' ') return '空格'
  if (ch === '\t') return 'Tab'
  if (ch === '\n') return '换行'
  return undefined
}

function charClass(idx) {
  const tokens = isCodeMode.value
    ? String(tokenClasses.value[idx] || '').split(/\s+/).filter(Boolean)
    : []
  if (idx === caret.value && engineStatus.value !== 'finished') {
    return [
      'is-caret',
      composing.value ? 'is-composing' : '',
      ...tokens,
    ].filter(Boolean)
  }
  const state = charStates.value[idx]
  if (state === 'correct') return ['is-correct', ...tokens]
  if (state === 'incorrect') return ['is-wrong']
  return ['is-pending', ...tokens]
}

async function loadTokenHighlight(text) {
  if (!isCodeMode.value) {
    tokenClasses.value = []
    return
  }
  const lang = cfg.codeLang || detectCodeLanguage(text) || 'javascript'
  cfg.codeLang = lang
  try {
    tokenClasses.value = await buildCodeTokenClasses(text, lang)
  } catch {
    tokenClasses.value = []
  }
}

/** 根据视口宽高动态调整字号与行高，大屏放大、小屏收紧 */
function updateLayoutMetrics() {
  const w = window.innerWidth || 1200
  const h = window.innerHeight || 800
  // 以宽度为主、高度为辅的字号：大屏可读，小屏不挤
  const byW = w / 52
  const byH = h / 36
  let font = Math.round(Math.min(40, Math.max(18, Math.min(byW, byH))))
  // 代码：略小字号、更密行高，多看几行
  if (isCodeMode.value) {
    font = Math.round(Math.min(22, Math.max(14, font * 0.72)))
  }
  const line = Math.round(font * (isCodeMode.value ? 1.7 : 1.95))
  boardFontPx.value = font
  lineHeightPx.value = line
  measureCharsPerLine()
  nextTick(() => positionCaretInput())
}

function measureCharsPerLine() {
  const el = viewportRef.value
  if (!el) return
  const width = el.clientWidth
  if (!width) return
  const fontSize = boardFontPx.value || parseFloat(getComputedStyle(el).fontSize) || 24
  // 代码模式：等宽、略收字距，并预留行号 gutter
  if (isCodeMode.value) {
    const gutter = 36
    const unit = fontSize * 0.62 // mono ch 宽约 0.6em
    const next = Math.max(24, Math.floor((width - gutter) / unit))
    if (next !== charsPerLine.value) {
      charsPerLine.value = next
      nextTick(() => positionCaretInput())
    }
    return
  }
  const letterSpacing = 0.02 * fontSize
  const unit = fontSize + letterSpacing
  const next = Math.max(8, Math.floor(width / unit))
  if (next !== charsPerLine.value) {
    charsPerLine.value = next
    nextTick(() => positionCaretInput())
  }
}

/** 把透明输入框锚定到当前光标字符（相对 board） */
function positionCaretInput() {
  const board = boardRef.value
  if (!board) return

  let el = charEls.get(caret.value)
  // 打到末尾时锚定最后一个字
  if (!el && targetChars.value.length) {
    el = charEls.get(Math.max(0, targetChars.value.length - 1))
  }
  const lh = lineHeightPx.value || 48
  if (!el) {
    // 首屏未渲染完：放在视口左上
    const vp = viewportRef.value
    if (vp) {
      const b = board.getBoundingClientRect()
      const v = vp.getBoundingClientRect()
      caretInputStyle.value = {
        left: `${v.left - b.left}px`,
        top: `${v.top - b.top}px`,
        width: '12px',
        height: `${lh}px`,
      }
    }
    return
  }

  const b = board.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  const left = r.left - b.left
  const top = r.top - b.top

  // 输入框盖在当前字上，宽度略宽以便 IME 定位；视觉透明
  caretInputStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    width: `${Math.max(r.width, 14)}px`,
    height: `${Math.max(r.height, lh)}px`,
  }
  compositionStyle.value = {
    left: `${left}px`,
    top: `${top + Math.max(r.height, lh) - 2}px`,
  }
}

function loadConfig() {
  const prefs = loadPrefs()
  cfg.durationSec = 300
  cfg.lang = prefs.lang || 'zh'
  cfg.difficulty = prefs.difficulty || 2
  spaceGlyph.value = normalizeSpaceGlyph(prefs.spaceGlyph)
  try {
    const raw = sessionStorage.getItem('orep_typing_session_cfg')
    if (raw) Object.assign(cfg, JSON.parse(raw))
  } catch {
    /* ignore */
  }
}

function initEngine() {
  loadConfig()
  let text = cfg.customText || ''
  const forceCode = cfg.playMode === 'code' || cfg.sourceType === 'code'
  // 代码练习：只去掉首尾空行，保留内部缩进与换行
  if (forceCode || looksLikeCode(text) || cfg.sourceType === 'paste') {
    text = normalizeCodeText(text)
    if (forceCode || looksLikeCode(text)) {
      cfg.sourceType = 'code'
      if (!cfg.codeLang || cfg.codeLang === 'auto') {
        cfg.codeLang = detectCodeLanguage(text)
      }
    }
  } else {
    text = text.trim()
  }
  if (!text) {
    const need = Math.max(cfg.durationSec * 5, 400)
    text = buildPracticeText({
      lang: cfg.lang,
      difficulty: cfg.difficulty,
      targetChars: need,
    }).text
    cfg.sourceType = 'catalog'
  }
  // 统一换行符，避免 Windows \r\n 导致对不齐
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  clientSessionId = newClientSessionId()
  pauseReason = ''
  lastCheckpointAt = 0
  const skipLeadingIndent = !isRanked.value && (
    cfg.playMode === 'code' || cfg.sourceType === 'code' || looksLikeCode(text)
  )
  engine = createTypingEngine(text, {
    mode: 'timed',
    durationSec: cfg.durationSec,
    skipLeadingIndent,
  })
  targetChars.value = charsOf(text)
  applySnap(engine.snapshot())
  loadTokenHighlight(text)
  nextTick(() => {
    updateLayoutMetrics()
  })
}

function applySnap(snap) {
  if (!snap) return
  const nextCaret = snap.caret || 0
  const nextCorrect = snap.correctChars || 0

  // 有新字符落定 → 驱动键盘对错闪烁
  if (nextCaret > prevCaret && lastPhysicalCode) {
    const ok = nextCorrect > prevCorrect
    kbLastKeyCode.value = lastPhysicalCode
    kbLastHit.value = ok ? 'ok' : 'bad'
    // 触发 watch：轻微错开引用
    requestAnimationFrame(() => {
      kbLastHit.value = ok ? 'ok' : 'bad'
    })
  }
  prevCaret = nextCaret
  prevCorrect = nextCorrect

  engineStatus.value = snap.status
  charStates.value = snap.charStates || []
  caret.value = nextCaret
  live.cpm = snap.cpm
  live.accuracy = snap.accuracy
  live.correctChars = nextCorrect
  live.remainingSec = snap.remainingSec
  live.progress = snap.progress || 0
  live.typedChars = snap.typedChars
  live.targetChars = snap.targetChars
  nextTick(() => positionCaretInput())
  if (snap.status === 'finished') complete()
}

function focusInput() {
  if (engineStatus.value === 'finished') return
  if (engineStatus.value === 'paused') {
    resume()
    return
  }
  inputRef.value?.focus({ preventScroll: true })
  positionCaretInput()
}

function onInputBlur() {
  // 练习进行中尽量保持焦点（点击空白会再 focus）
  if (engineStatus.value === 'running' && !finished) {
    clearTimeout(refocusTimer)
    refocusTimer = setTimeout(() => {
      if (engineStatus.value === 'running' && document.activeElement !== inputRef.value) {
        inputRef.value?.focus({ preventScroll: true })
      }
    }, 80)
  }
}

function onCompositionStart(e) {
  composing.value = true
  compositionText.value = e?.data || ''
  positionCaretInput()
}

function onCompositionUpdate(e) {
  compositionText.value = e?.data || compositionText.value || ''
  positionCaretInput()
}

function onCompositionEnd(e) {
  composing.value = false
  compositionText.value = ''
  const value = e?.target?.value ?? inputValue.value
  inputValue.value = value
  if (engine) applySnap(engine.setCommitted(value))
  nextTick(() => {
    positionCaretInput()
    focusInput()
  })
}

function onInput(e) {
  const value = e?.target?.value ?? ''
  inputValue.value = value
  if (composing.value) {
    positionCaretInput()
    return
  }
  // 开始输入后收起规范条，把空间留给代码
  if (isCodeMode.value && showCodeTips.value && value.length > 0) {
    showCodeTips.value = false
  }
  if (engine) applySnap(engine.setCommitted(value))
  nextTick(() => positionCaretInput())
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    pause()
    return
  }
  // 代码练习：行首缩进已自动跳过时，Tab / 空格为可选 no-op
  if (
    isCodeMode.value
    && !composing.value
    && isAfterAutoIndent()
    && (e.key === 'Tab' || e.key === ' ')
  ) {
    e.preventDefault()
    lastPhysicalCode = e.key === 'Tab' ? 'Tab' : 'Space'
    return
  }
  // 代码练习：Tab 插入语言约定缩进（空格优先，与样例一致）
  if (e.key === 'Tab' && isCodeMode.value && !composing.value) {
    e.preventDefault()
    lastPhysicalCode = 'Tab'
    const unit = codeIndentUnit.value
    // 若目标当前位置是 \t 则仍敲 \t，否则按约定空格
    const expected = targetChars.value[caret.value]
    const insert = expected === '\t' ? '\t' : unit
    // 若目标是多个空格缩进，一次 Tab 尽量对齐到缩进边界
    let chunk = insert
    if (expected === ' ' && unit.startsWith(' ')) {
      let n = 0
      while (targetChars.value[caret.value + n] === ' ' && n < unit.length) n += 1
      chunk = unit.slice(0, Math.max(1, n)) || unit
    }
    const next = `${inputValue.value}${chunk}`
    inputValue.value = next
    if (inputRef.value) inputRef.value.value = next
    if (engine) applySnap(engine.setCommitted(next))
    nextTick(() => positionCaretInput())
    return
  }
  // 记录物理键，供虚拟键盘对错反馈
  if (e.code) {
    lastPhysicalCode = e.code
  } else if (e.key && e.key.length === 1 && /[a-zA-Z]/.test(e.key)) {
    lastPhysicalCode = `Key${e.key.toUpperCase()}`
  } else if (e.key === ' ') {
    lastPhysicalCode = 'Space'
  } else if (e.key === 'Backspace') {
    lastPhysicalCode = 'Backspace'
  } else if (e.key === 'Enter') {
    lastPhysicalCode = 'Enter'
  }
}

function pause(reason = 'user') {
  if (!engine || engineStatus.value !== 'running') return
  // @click="pause" 会传入 MouseEvent，不能当成暂停原因
  const why = reason === 'visibility' ? 'visibility' : 'user'
  engine.pause()
  pauseReason = why
  applySnap(engine.snapshot())
  inputRef.value?.blur()
}

function resume() {
  if (!engine || engineStatus.value !== 'paused') return
  engine.resume()
  pauseReason = ''
  applySnap(engine.snapshot())
  nextTick(() => focusInput())
}

function currentPersistResult() {
  if (!engine) return null
  const snap = engine.snapshot()
  return {
    clientSessionId,
    mode: cfg.playMode === 'ranked' ? 'ranked' : 'practice',
    durationSec: cfg.durationSec,
    cpm: snap.cpm,
    accuracy: snap.accuracy,
    correctChars: snap.correctChars,
    totalKeystrokes: snap.totalKeystrokes,
    elapsedMs: snap.elapsedMs,
    lang: cfg.lang,
    difficulty: cfg.difficulty,
    textVersion: cfg.playMode === 'ranked' ? (cfg.textVersion || RANKED_TEXT_VERSION) : null,
    sourceType: isCodeMode.value ? (cfg.sourceType || 'code') : (cfg.sourceType || 'catalog'),
  }
}

function persistCheckpoint({ keepalive = false, force = false, reason = 'checkpoint' } = {}) {
  const result = currentPersistResult()
  if (!shouldPersistTypingSession(result)) return false
  const now = Date.now()
  if (!force && keepalive && now - lastCheckpointAt < 3000) return false
  lastCheckpointAt = now
  const payload = buildTypingSessionPayload(result)
  const requestedMode = result.mode === 'ranked' ? 'ranked' : 'practice'
  if (keepalive) return flushTypingSessionKeepalive(payload, { reason, requestedMode })
  return saveTypingSession(payload, { reason, requestedMode })
}

function endEarly() {
  if (!engine || finished) return
  if (engineStatus.value === 'idle' && !inputValue.value) {
    router.replace({ name: 'TypingPractice' })
    return
  }
  applySnap(engine.finish())
}

async function complete() {
  if (finished || !engine) return
  finished = true
  stopTick()
  const result = engine.buildResult({
    lang: cfg.lang,
    difficulty: cfg.difficulty,
    sourceType: cfg.sourceType,
  })
  result.playMode = cfg.playMode === 'code' ? 'code' : cfg.playMode
  result.mode = cfg.playMode === 'ranked' ? 'ranked' : 'practice'
  result.durationSec = cfg.durationSec
  result.textVersion = cfg.playMode === 'ranked' ? (cfg.textVersion || RANKED_TEXT_VERSION) : null
  result.clientSessionId = clientSessionId
  if (isCodeMode.value) {
    result.codeLang = cfg.codeLang
    result.sourceType = result.sourceType || 'code'
  }

  try {
    if (shouldPersistTypingSession(result)) {
      const remote = await saveTypingSession(buildTypingSessionPayload(result), {
        reason: 'complete',
        requestedMode: result.mode,
      })
      if (remote) {
        result.serverId = remote.id
        result.rank = remote.rank
        result.leaderboard = remote.leaderboard
        if (remote.mode === 'practice' && result.mode === 'ranked') {
          result.rankedDowngraded = true
        }
        result.mode = remote.mode || result.mode
        result.durationUnsynced = false
      } else {
        result.durationUnsynced = true
        result.syncError = DURATION_UNSYNCED_MESSAGE
      }
    }
  } catch {
    result.durationUnsynced = true
    result.syncError = DURATION_UNSYNCED_MESSAGE
    persistCheckpoint({ keepalive: true, force: true, reason: 'complete' })
  }

  saveLastResult(result)
  router.replace({ name: 'TypingResult' })
}

function startTick() {
  stopTick()
  tickTimer = window.setInterval(() => {
    if (!engine) return
    applySnap(engine.snapshot())
    if (engineStatus.value === 'running' && Date.now() - lastCheckpointAt >= 15_000) {
      persistCheckpoint({ keepalive: true, force: true, reason: 'checkpoint' })
      flushTypingSessionQueue()
    }
  }, 200)
}

function stopTick() {
  if (tickTimer) {
    clearInterval(tickTimer)
    tickTimer = null
  }
}

function onVisibility() {
  const action = resolveVisibilityAction({
    hidden: document.hidden,
    status: engineStatus.value,
    pauseReason,
  })
  if (action === 'pause-visibility') {
    pause('visibility')
    persistCheckpoint({ keepalive: true, reason: 'checkpoint' })
    return
  }
  if (action === 'resume') resume()
}

function onPageHide() {
  if (finished) return
  persistCheckpoint({ keepalive: true, force: true, reason: 'pagehide' })
}

watch([caret, scrollLine, textLines], () => {
  nextTick(() => positionCaretInput())
})

function onWindowResize() {
  updateLayoutMetrics()
}

onMounted(async () => {
  initEngine()
  startTick()
  flushTypingSessionQueue().catch(() => [])
  document.addEventListener('visibilitychange', onVisibility)
  window.addEventListener('pagehide', onPageHide)
  await nextTick()
  updateLayoutMetrics()
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => updateLayoutMetrics())
    if (playRootRef.value) resizeObserver.observe(playRootRef.value)
    if (viewportRef.value) resizeObserver.observe(viewportRef.value)
  }
  window.addEventListener('resize', onWindowResize)
  requestAnimationFrame(() => focusInput())
})

onBeforeUnmount(() => {
  if (!finished) persistCheckpoint({ keepalive: true, force: true, reason: 'pagehide' })
  stopTick()
  clearTimeout(refocusTimer)
  document.removeEventListener('visibilitychange', onVisibility)
  window.removeEventListener('pagehide', onPageHide)
  window.removeEventListener('resize', onWindowResize)
  resizeObserver?.disconnect()
  charEls.clear()
})
</script>

<style scoped>
.typing-play {
  --line-h: 48px;
  --board-font: 24px;
  --hud-num: 22px;
  display: grid;
  gap: clamp(10px, 1.2vw, 16px);
  width: 100%;
  max-width: min(1100px, 96vw);
  margin: 0 auto;
  min-height: 0;
  box-sizing: border-box;
}

.typing-play__hud {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  border: 1px solid var(--ds-card-border, var(--ds-line));
  border-radius: var(--ds-radius-lg);
  background: #fff;
  box-shadow: var(--ds-card-shadow);
  overflow: hidden;
}

.hud-item {
  flex: 1 1 0;
  min-width: 88px;
  padding: 12px 14px;
  border-left: 1px solid var(--ds-line);
}

.hud-item:first-child {
  border-left: 0;
}

.hud-item strong {
  display: block;
  font-size: var(--hud-num, 22px);
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--ds-ink);
  line-height: 1.15;
}

.hud-item span {
  display: block;
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 600;
}

.hud-item--time strong {
  color: var(--ds-orange-700, #c2410c);
}

/* 金山式主练习板：大字正文，点击即打；随屏缩放 */
.typing-play__board {
  position: relative;
  min-height: calc(var(--line-h, 48px) * 4 + 56px);
  padding: clamp(12px, 1.4vw, 20px) clamp(14px, 1.8vw, 24px);
  border: 1px solid var(--ds-card-border, var(--ds-line));
  border-radius: var(--ds-radius-lg);
  background: #fffef8;
  box-shadow: var(--ds-card-shadow);
  cursor: text;
  user-select: none;
}
.typing-play__board.is-code-board {
  min-height: calc(var(--line-h, 28px) * 8 + 72px);
}

/* 代码：IDE 暗色底板 */
.typing-play__board.is-code-board {
  background: #0f172a;
  border-color: #1e293b;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.18);
}
.typing-play__board.is-code-board.is-paused,
.typing-play__board.is-code-board.is-idle {
  box-shadow:
    inset 0 0 0 1px color-mix(in srgb, #fbbf24 35%, transparent),
    0 12px 40px rgba(15, 23, 42, 0.18);
}
.typing-play__board.is-code-board .typing-play__status-row {
  color: #94a3b8;
}
.typing-play.is-code-session {
  max-width: min(1180px, 96vw);
}

.typing-play__board.is-paused,
.typing-play__board.is-idle {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ds-orange-400, #fb923c) 30%, transparent);
}

.typing-play__status-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  min-height: 22px;
  margin-bottom: 8px;
  color: var(--ds-muted);
  font-size: clamp(11px, 1.1vw, 13px);
  font-weight: 650;
}

.space-glyph-switch {
  display: inline-flex;
  margin-left: auto;
  padding: 2px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  border: 1px solid var(--ds-line, #e5e7eb);
}
.space-glyph-switch__btn {
  appearance: none;
  border: 0;
  background: transparent;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  color: var(--ds-muted);
  font: 650 11px/1 inherit;
  cursor: pointer;
}
.space-glyph-switch__btn.is-active {
  background: #fff;
  color: var(--ds-ink, #111827);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}
.typing-play__board.is-code-board .space-glyph-switch {
  background: rgba(148, 163, 184, 0.12);
  border-color: #334155;
}
.typing-play__board.is-code-board .space-glyph-switch__btn {
  color: #94a3b8;
}
.typing-play__board.is-code-board .space-glyph-switch__btn.is-active {
  background: #1e293b;
  color: #e2e8f0;
  box-shadow: none;
}

.typing-play__composing-tag {
  color: var(--ds-orange-700, #c2410c);
}

.typing-viewport {
  position: relative;
  /* 默认显示 4 行，行高随屏幕变化 */
  height: calc(var(--line-h, 48px) * 4);
  overflow: hidden;
  font-size: var(--board-font, 24px);
  line-height: var(--line-h, 48px);
  letter-spacing: 0.02em;
  /* 拉丁优先：Segoe UI / Verdana 对 I、l、1 区分明显；中文回退到系统黑体 */
  font-family:
    "Segoe UI",
    Verdana,
    Tahoma,
    "Helvetica Neue",
    Arial,
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans SC",
    "Microsoft YaHei",
    sans-serif;
  font-variant-ligatures: none;
  font-feature-settings: "liga" 0, "clig" 0;
}

/* 英文/混排：等宽字体，I / l / 1 最易辨认（打字练习标准做法） */
.typing-viewport.is-latin {
  letter-spacing: 0.04em;
  font-family:
    ui-monospace,
    "Cascadia Mono",
    "Cascadia Code",
    "SF Mono",
    "JetBrains Mono",
    Consolas,
    "Liberation Mono",
    Menlo,
    Monaco,
    "Courier New",
    monospace;
}

/* 编码规范条（暗色板上的暖色提示） */
.typing-code-tips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.28);
  font-size: 11.5px;
  line-height: 1.4;
  color: #fde68a;
}
.typing-code-tips__tag {
  flex: none;
  padding: 2px 7px;
  border-radius: 999px;
  background: #f59e0b;
  color: #1c1917;
  font-weight: 750;
  font-size: 11px;
  letter-spacing: 0.02em;
}
.typing-code-tips__item {
  position: relative;
  padding-left: 10px;
  font-weight: 550;
  color: #fde68a;
}
.typing-code-tips__item::before {
  content: '·';
  position: absolute;
  left: 0;
  color: #fbbf24;
  font-weight: 800;
}
.typing-code-tips__hide {
  margin-left: auto;
  appearance: none;
  border: 0;
  background: transparent;
  color: #fcd34d;
  font: 650 11px/1 inherit;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
}
.typing-code-tips__hide:hover {
  background: rgba(251, 191, 36, 0.15);
}

/* 代码练习：等宽 + 紧字距 + 行号 · 暗色 IDE */
.typing-viewport.is-code {
  letter-spacing: 0;
  font-variant-ligatures: none;
  font-feature-settings: "liga" 0, "calt" 0;
  font-family:
    ui-monospace,
    "JetBrains Mono",
    "Cascadia Code",
    "SF Mono",
    "Fira Code",
    Consolas,
    "Liberation Mono",
    Menlo,
    Monaco,
    "Courier New",
    monospace;
  font-size: var(--board-font, 16px);
  line-height: var(--line-h, 28px);
  background:
    linear-gradient(90deg, #0b1220 0, #0b1220 42px, transparent 42px);
  border-radius: 10px;
  padding-left: 0;
  border: 1px solid #1e293b;
  /* 高度由 codeViewportStyle 覆盖默认 4 行 */
}

.typing-line.is-active-line {
  background: rgba(56, 189, 248, 0.07);
  box-shadow: inset 2px 0 0 0 #38bdf8;
}
.typing-line.is-active-line .typing-gutter {
  color: #e2e8f0;
  opacity: 1;
  font-weight: 750;
}

.typing-viewport.is-code .typing-gutter {
  width: 40px;
  margin-right: 12px;
  color: #475569;
  border-right-color: #1e293b;
}

/* 语法高亮 · 暗色：未敲略淡 / 敲对更亮 / 错红 */
.typing-viewport.is-code .typing-ch.is-pending {
  color: #64748b;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-keyword,
.typing-viewport.is-code .typing-ch.is-pending.hljs-built_in,
.typing-viewport.is-code .typing-ch.is-pending.hljs-selector-tag {
  color: #8b7cc9;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-string,
.typing-viewport.is-code .typing-ch.is-pending.hljs-template-string,
.typing-viewport.is-code .typing-ch.is-pending.hljs-attr {
  color: #4d9f7a;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-comment,
.typing-viewport.is-code .typing-ch.is-pending.hljs-quote {
  color: #475569;
  font-style: italic;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-number,
.typing-viewport.is-code .typing-ch.is-pending.hljs-literal {
  color: #b4923a;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-title,
.typing-viewport.is-code .typing-ch.is-pending.function_,
.typing-viewport.is-code .typing-ch.is-pending.hljs-section {
  color: #5a9fbf;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-type,
.typing-viewport.is-code .typing-ch.is-pending.hljs-class,
.typing-viewport.is-code .typing-ch.is-pending.hljs-params {
  color: #4d9eab;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-meta,
.typing-viewport.is-code .typing-ch.is-pending.hljs-name,
.typing-viewport.is-code .typing-ch.is-pending.hljs-tag {
  color: #b87a9a;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-variable,
.typing-viewport.is-code .typing-ch.is-pending.hljs-template-variable,
.typing-viewport.is-code .typing-ch.is-pending.hljs-property {
  color: #b8865a;
}
.typing-viewport.is-code .typing-ch.is-pending.hljs-punctuation,
.typing-viewport.is-code .typing-ch.is-pending.hljs-operator {
  color: #64748b;
}

.typing-viewport.is-code .typing-ch.is-correct {
  color: #e2e8f0;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-keyword,
.typing-viewport.is-code .typing-ch.is-correct.hljs-built_in,
.typing-viewport.is-code .typing-ch.is-correct.hljs-selector-tag {
  color: #c4b5fd;
  font-weight: 650;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-string,
.typing-viewport.is-code .typing-ch.is-correct.hljs-template-string,
.typing-viewport.is-code .typing-ch.is-correct.hljs-attr {
  color: #6ee7b7;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-comment,
.typing-viewport.is-code .typing-ch.is-correct.hljs-quote {
  color: #64748b;
  font-style: italic;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-number,
.typing-viewport.is-code .typing-ch.is-correct.hljs-literal {
  color: #fbbf24;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-title,
.typing-viewport.is-code .typing-ch.is-correct.function_,
.typing-viewport.is-code .typing-ch.is-correct.hljs-section {
  color: #7dd3fc;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-type,
.typing-viewport.is-code .typing-ch.is-correct.hljs-class,
.typing-viewport.is-code .typing-ch.is-correct.hljs-params {
  color: #67e8f9;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-meta,
.typing-viewport.is-code .typing-ch.is-correct.hljs-name,
.typing-viewport.is-code .typing-ch.is-correct.hljs-tag {
  color: #f9a8d4;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-variable,
.typing-viewport.is-code .typing-ch.is-correct.hljs-template-variable,
.typing-viewport.is-code .typing-ch.is-correct.hljs-property {
  color: #fdba74;
}
.typing-viewport.is-code .typing-ch.is-correct.hljs-punctuation,
.typing-viewport.is-code .typing-ch.is-correct.hljs-operator {
  color: #cbd5e1;
}

/* 错字始终盖过高亮 */
.typing-viewport.is-code .typing-ch.is-wrong {
  color: #fecaca !important;
  background: rgba(239, 68, 68, 0.35);
  font-style: normal;
  font-weight: 650;
}

.typing-viewport.is-code .typing-ch.is-caret {
  color: #f8fafc !important;
  background: rgba(56, 189, 248, 0.28);
  box-shadow: inset 0 -2px 0 0 #38bdf8;
}
.typing-viewport.is-code .typing-ch.is-caret.is-composing {
  background: rgba(167, 139, 250, 0.35);
  box-shadow: inset 0 -2px 0 0 #a78bfa;
}

.typing-viewport.is-code .typing-ch.is-space.is-caret {
  background: rgba(56, 189, 248, 0.18) !important;
  box-shadow: none;
}
.typing-viewport.is-code .typing-ch.is-tab.is-pending {
  color: #334155;
}
.typing-viewport.is-code .typing-ch.is-tab.is-correct {
  color: #64748b;
  background: rgba(51, 65, 85, 0.45);
}
.typing-viewport.is-code .typing-ch.is-newline.is-pending {
  color: #334155;
}
.typing-viewport.is-code .typing-ch.is-newline.is-correct {
  color: #64748b;
}

.typing-play.is-code-session .typing-play__progress {
  background: #1e293b;
}
.typing-play.is-code-session .typing-play__bar {
  background: linear-gradient(90deg, #38bdf8, #818cf8);
}
.typing-play.is-code-session .typing-caret-input {
  caret-color: #38bdf8;
}

.typing-lines {
  will-change: transform;
  transition: transform 0.16s ease;
}

.typing-line {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  box-sizing: border-box;
}

.typing-line.is-code-line {
  display: flex;
  align-items: stretch;
  white-space: pre;
  overflow: hidden;
  padding-right: 8px;
}

.typing-gutter {
  flex: none;
  width: 34px;
  margin-right: 10px;
  padding-right: 8px;
  text-align: right;
  font-size: 0.72em;
  font-weight: 600;
  line-height: inherit;
  color: #94a3b8;
  border-right: 1px solid #e2e8f0;
  user-select: none;
  opacity: 0.9;
}

.typing-ch {
  display: inline-block;
  min-width: 0.95em;
  text-align: center;
  border-radius: 2px;
  vertical-align: top;
  transition: color 0.05s linear, background-color 0.05s linear;
  position: relative;
}

.typing-viewport.is-code .typing-ch {
  min-width: 0.6em;
  text-align: left;
  padding: 0 0.02em;
}

/* Tab：浅底槽，便于对齐缩进 */
.typing-ch.is-tab {
  min-width: 2.4em;
  color: #94a3b8;
  letter-spacing: -0.08em;
  opacity: 0.85;
}
.typing-ch.is-tab.is-pending {
  color: #cbd5e1;
}
.typing-ch.is-tab.is-correct {
  color: #64748b;
  background: rgba(148, 163, 184, 0.12);
  border-radius: 3px;
}
.typing-ch.is-tab.is-wrong {
  color: #b91c1c;
  background: rgba(254, 202, 202, 0.75);
}
.typing-ch.is-tab.is-caret {
  background: rgba(255, 214, 102, 0.55);
  color: #475569;
}

/* 换行符：行末轻标记 */
.typing-ch.is-newline {
  min-width: 1.1em;
  font-size: 0.78em;
  font-weight: 700;
  color: #cbd5e1;
  opacity: 0.9;
}
.typing-ch.is-newline.is-pending {
  color: #e2e8f0;
}
.typing-ch.is-newline.is-correct {
  color: #94a3b8;
}
.typing-ch.is-newline.is-wrong {
  color: #b91c1c;
  background: rgba(254, 202, 202, 0.75);
}
.typing-ch.is-newline.is-caret {
  color: #f59e0b;
  background: rgba(255, 214, 102, 0.45);
}

/* 空格槽：三种模式共用 1ch 节奏，避免旧版 0.65em 弱下划线 */
.typing-ch.is-space {
  width: 1ch;
  min-width: 1ch;
  text-align: center;
}

/* bullet（默认，Keybr）：浅灰中间点 */
.space-glyph-bullet .typing-ch.is-space {
  color: #c5c9d1;
  background: transparent;
}
.space-glyph-bullet .typing-ch.is-space::after {
  content: none;
}
.space-glyph-bullet .typing-ch.is-space.is-pending {
  color: #c5c9d1;
}
.space-glyph-bullet .typing-ch.is-space.is-correct {
  color: #9ca3af;
  opacity: 0.42;
}
.space-glyph-bullet .typing-ch.is-space.is-wrong {
  color: #ef4444;
  opacity: 1;
  background: rgba(254, 202, 202, 0.7);
  border-radius: 3px;
}
.space-glyph-bullet .typing-ch.is-space.is-caret {
  color: #4b5563;
  font-weight: 800;
  opacity: 1;
  background: rgba(255, 214, 102, 0.75);
  border-radius: 3px;
  box-shadow: inset 0 -2px 0 0 #f59e0b;
}

/* bar：1ch 下划线槽（改进旧版 underline） */
.space-glyph-bar .typing-ch.is-space {
  color: transparent;
  background: transparent;
}
.space-glyph-bar .typing-ch.is-space::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0.18em;
  height: 0;
  border-bottom: 2.5px solid rgba(156, 163, 175, 0.95);
  border-radius: 1px;
  pointer-events: none;
}
.space-glyph-bar .typing-ch.is-space.is-pending::after {
  border-bottom-color: rgba(156, 163, 175, 0.9);
}
.space-glyph-bar .typing-ch.is-space.is-correct::after {
  border-bottom-color: rgba(75, 85, 99, 0.45);
  border-bottom-width: 2px;
}
.space-glyph-bar .typing-ch.is-space.is-wrong {
  background: rgba(254, 202, 202, 0.55);
  border-radius: 3px;
}
.space-glyph-bar .typing-ch.is-space.is-wrong::after {
  border-bottom-color: #ef4444;
  border-bottom-width: 3px;
}
.space-glyph-bar .typing-ch.is-space.is-caret {
  background: rgba(255, 214, 102, 0.28);
  border-radius: 3px;
}
.space-glyph-bar .typing-ch.is-space.is-caret::after {
  border-bottom-color: #f59e0b;
  border-bottom-width: 3px;
}

/* invisible（Monkeytype）：纯空隙，无字形 */
.space-glyph-invisible .typing-ch.is-space {
  color: transparent;
  background: transparent;
}
.space-glyph-invisible .typing-ch.is-space::after {
  content: none;
}
.space-glyph-invisible .typing-ch.is-space.is-wrong {
  background: rgba(254, 202, 202, 0.55);
  border-radius: 3px;
}
.space-glyph-invisible .typing-ch.is-space.is-caret {
  background: rgba(255, 214, 102, 0.4);
  border-radius: 3px;
  box-shadow: inset 0 -2px 0 0 #f59e0b;
}

/* 代码行首自动缩进：连续闷色条，不用 `_` / `·` */
.typing-ch.is-auto-indent {
  color: transparent !important;
  background: rgba(51, 65, 85, 0.28) !important;
  border-radius: 0;
  box-shadow: none !important;
  opacity: 1 !important;
  min-width: 1ch;
}
.typing-ch.is-auto-indent::after {
  content: none !important;
  border: 0 !important;
}
.typing-ch.is-auto-indent.is-tab {
  min-width: 2.4em;
}
.typing-viewport.is-code .typing-ch.is-auto-indent {
  background: rgba(51, 65, 85, 0.42) !important;
}
.typing-viewport.is-code .typing-ch.is-auto-indent.is-auto-indent-start {
  box-shadow: inset 2px 0 0 0 rgba(148, 163, 184, 0.4) !important;
}
.typing-viewport.is-code .typing-ch.is-auto-indent.is-caret {
  background: rgba(56, 189, 248, 0.16) !important;
}

/* 代码空格：永远无字形、无下划线（即使偏好是 bullet/bar） */
.typing-viewport.is-code .typing-ch.is-space {
  color: transparent !important;
  background: transparent;
}
.typing-viewport.is-code .typing-ch.is-space::after {
  content: none !important;
  border: 0 !important;
}
.typing-viewport.is-code .typing-ch.is-space.is-wrong {
  background: rgba(239, 68, 68, 0.35);
  border-radius: 3px;
}

/* 金山式配色：未打浅灰，已打深色，错字红底 */
.typing-ch.is-pending {
  color: #b8bcc4;
}

.typing-ch.is-correct {
  color: #1f2937;
}

.typing-ch.is-wrong {
  color: #b91c1c;
  background: rgba(254, 202, 202, 0.85);
}

.typing-ch.is-caret {
  color: #111827;
  background: rgba(255, 214, 102, 0.75);
  box-shadow: inset 0 -2px 0 0 #f59e0b;
}

.typing-ch.is-caret.is-composing {
  background: rgba(191, 219, 254, 0.75);
  box-shadow: inset 0 -2px 0 0 #3b82f6;
}

/* 透明输入框：叠在当前字符上，承接系统 IME */
.typing-caret-input {
  position: absolute;
  z-index: 5;
  margin: 0;
  padding: 0;
  border: 0;
  outline: none;
  resize: none;
  overflow: hidden;
  background: transparent;
  color: transparent;
  caret-color: #f59e0b;
  font: inherit;
  font-size: inherit;
  line-height: inherit;
  letter-spacing: inherit;
  /* 几乎不可见，但仍可聚焦与弹出候选 */
  opacity: 0.02;
  white-space: pre;
}

.typing-caret-input:focus {
  opacity: 0.03;
}

.typing-composition {
  position: absolute;
  z-index: 6;
  max-width: 60%;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
  pointer-events: none;
  transform: translateY(2px);
}

.typing-play__progress {
  height: 6px;
  border-radius: 999px;
  background: #f3f4f6;
  overflow: hidden;
}

.typing-play__bar {
  height: 100%;
  background: linear-gradient(90deg, #fb923c, #ea580c);
  transition: width 0.15s linear;
}

.typing-mini-btn {
  appearance: none;
  border: 1px solid var(--ds-line);
  background: rgba(255, 255, 255, 0.75);
  color: var(--ds-ink-2);
  border-radius: 999px;
  min-height: 34px;
  padding: 0 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.typing-mini-btn--danger {
  border-color: color-mix(in srgb, #fecaca 70%, var(--ds-line));
  color: #b91c1c;
}

/* 大屏：练习区尽量吃满可用高度 */
.typing-play-shell :deep(.ai-app-shell__body) {
  min-height: 0;
}
.typing-play-shell :deep(.ai-app-content) {
  height: 100%;
  min-height: 0;
}

@media (min-width: 1280px) {
  .typing-play {
    max-width: min(1280px, 94vw);
  }
}

@media (max-width: 640px) {
  .hud-item {
    min-width: 46%;
    border-left: 0;
    border-top: 1px solid var(--ds-line);
  }

  .hud-item:nth-child(-n + 2) {
    border-top: 0;
  }

}
</style>
