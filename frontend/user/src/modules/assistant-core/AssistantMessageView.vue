<template>
  <article
    class="amv"
    :class="[
      msg.role === 'user' ? 'is-user' : 'is-assistant',
      msg.status === 'streaming' ? 'is-streaming' : '',
      msg.status === 'failed' ? 'is-failed' : '',
      compact ? 'is-compact' : '',
      `phase-${livePhase}`,
    ]"
  >
    <div v-if="msg.role === 'assistant' && !showProcessTheater" class="amv__avatar" aria-hidden="true">
      <XiaoQiMark :size="compact ? 24 : 28" :hoverable="false" />
    </div>

    <div class="amv__body">
      <!-- 用户消息 -->
      <div v-if="msg.role === 'user'" class="amv__user-text">{{ displayText }}</div>

      <template v-else>
        <!--
          诚实过程条（不是假多 Agent）：
          1) 单行「思考中 · Ns」
          2) 仅真实工具行（检索 query + 条数）
          3) 仅有实质内容的备注（如命中标题）
          4) 模型 thinking 摘录（若有）
        -->
        <!-- Grok 风格思考态：单行 Thinking… / Thought for Ns，可展开真实过程 -->
        <section v-if="showProcessTheater" class="amv__theater" aria-live="polite">
          <button
            type="button"
            class="amv__think-row"
            :class="{
              'is-live': isProcessLive,
              'is-done': !isProcessLive && !isProcessFailed,
              'is-error': isProcessFailed,
              'is-open': processOpen && hasExpandableProcess,
            }"
            :aria-expanded="hasExpandableProcess ? (processOpen ? 'true' : 'false') : undefined"
            :disabled="!hasExpandableProcess"
            @click="hasExpandableProcess && (processOpen = !processOpen)"
          >
            <span
              class="amv__think-orb"
              :class="{ 'is-spinning': isProcessLive }"
              aria-hidden="true"
            />
            <span class="amv__think-label">
              <template v-if="isProcessLive">
                Thinking
                <span class="amv__think-dots" aria-hidden="true"><i /><i /><i /></span>
              </template>
              <template v-else-if="isProcessFailed">{{ processHeaderLabel }}</template>
              <template v-else>Thought for {{ processSeconds }}s</template>
            </span>
            <span v-if="isProcessLive" class="amv__think-time">{{ processSeconds }}s</span>
            <span v-if="!processOpen && !isProcessLive && processSummaryBits.length" class="amv__think-meta">
              <template v-for="(bit, i) in processSummaryBits" :key="bit">
                <span v-if="i > 0" class="amv__header-dot">·</span>{{ bit }}
              </template>
            </span>
            <span class="amv__header-spacer" />
            <svg
              v-if="hasExpandableProcess"
              class="amv__chev"
              :class="{ 'is-open': processOpen }"
              viewBox="0 0 16 16"
              width="12"
              height="12"
              aria-hidden="true"
            >
              <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            </svg>
          </button>

          <div v-show="processOpen && hasExpandableProcess" class="amv__process">
            <div
              v-for="row in toolRows"
              :key="`tool-${row.stepNo}-${row.stepKey}`"
              class="amv__tool"
              :class="`is-${row.status || 'running'}`"
            >
              <div class="amv__tool-main">
                <span class="amv__tool-icon" aria-hidden="true">
                  <svg v-if="String(row.stepKey || '').includes('web')" viewBox="0 0 16 16" width="14" height="14"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M2 8h12M8 2c2 2.2 2 9.8 0 12M8 2c-2 2.2-2 9.8 0 12" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>
                  <svg v-else viewBox="0 0 16 16" width="14" height="14"><path d="M3 4h10v9H3z" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5 4V3h6v1M5 7h6M5 10h4" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>
                </span>
                <div class="amv__tool-copy">
                  <strong>{{ row.action || row.title }}</strong>
                  <span
                    v-if="row.query"
                    class="amv__tool-query"
                    :title="row.query"
                  >{{ truncateQuery(row.query) }}</span>
                </div>
              </div>
              <div class="amv__tool-meta">
                <span v-if="row.resultCount != null" class="amv__tool-count">{{ row.resultCount }} 条</span>
                <span v-else-if="row.status === 'running'" class="amv__tool-count is-live">running</span>
              </div>
            </div>

            <div
              v-for="note in visibleAgentNotes"
              :key="note.id"
              class="amv__log"
            >
              <p>{{ note.text }}</p>
            </div>

            <div
              v-if="msg.thinkingText && msg.thinkingText !== displayText"
              class="amv__raw-think"
            >
              <span class="amv__raw-label">Reasoning</span>
              <div
                ref="reasoningScrollRef"
                class="amv__raw-think-body"
                @scroll.passive="onReasoningScroll"
              >
                {{ msg.thinkingText }}
              </div>
            </div>

            <div
              v-for="step in otherSteps"
              :key="`oth-${step.stepNo}-${step.stepKey}`"
              class="amv__misc"
              :class="`is-${step.status}`"
            >
              <span class="amv__misc-dot" />
              <span>{{ step.title }}</span>
              <small v-if="step.outputSummary">{{ step.outputSummary }}</small>
            </div>
          </div>
        </section>

        <!-- 意图（弱化，不抢思考态） -->
        <div v-if="msg.brainHints && !isProcessLive" class="amv__hints">
          <span v-if="msg.brainHints.project" class="amv__chip">项目 · {{ msg.brainHints.project }}</span>
          <span v-if="msg.brainHints.goal" class="amv__chip">{{ goalLabel(msg.brainHints.goal) }}</span>
        </div>

        <!-- 最终回答：打字机揭示 -->
        <div
          v-if="displayText || typedText"
          class="amv__answer"
          :class="{
            'is-streaming': isAnswerStreaming,
            'is-settled': !isAnswerStreaming && !isTypewriting && (msg.status === 'completed' || msg.status === 'cancelled'),
            'is-typewriting': isTypewriting,
          }"
        >
          <div class="amv__content xq-md" v-html="htmlContent" @click="onContentClick" />
        </div>
      </template>

      <!-- Plan 轻确认：草案卡 -->
      <div
        v-if="!hidePlanDraft && msg.role === 'assistant' && msg.planDrafts?.length"
        class="amv__plan-drafts"
      >
        <div
          v-for="(pd, pdi) in msg.planDrafts"
          :key="`pd-${pd.kind || pdi}`"
          class="amv__plan-draft"
          :class="`is-${pd.status || 'pending'}`"
        >
          <div class="amv__plan-draft__head">
            <strong>{{ pd.title || '草案' }}</strong>
            <span class="amv__plan-draft__badge">{{ pd.status === 'expanded' ? '已展开' : '待确认' }}</span>
          </div>
          <p class="amv__plan-draft__summary">{{ pd.summary || '确认纲要后再生成完整版，避免一次过长。' }}</p>
          <div v-if="pd.status !== 'expanded'" class="amv__plan-draft__actions">
            <button
              type="button"
              class="amv__plan-draft__btn"
              :disabled="!!pd._busy || msg.status === 'streaming'"
              @click="onExpandPlan(pd)"
            >{{ pd.confirmLabel || '展开完整版' }}</button>
          </div>
        </div>
      </div>

      <!-- 依据 -->
      <div v-if="msg.role === 'assistant' && msg.citations?.length" ref="citesRef" class="amv__cites">
        <span class="amv__cites-label">依据</span>
        <button
          v-for="c in msg.citations"
          :key="`cite-${c.index || c.title}`"
          type="button"
          class="amv__cite"
          :class="[`is-${c.sourceType || 'unknown'}`, activeCite === Number(c.index) ? 'is-active' : '']"
          :title="citeTitle(c)"
          @click="focusCite(c)"
        >
          <sup>{{ c.index || '' }}</sup>
          <span class="amv__cite-type">{{ sourceTypeLabel(c.sourceType) }}</span>
          {{ c.title || '来源' }}
        </button>
      </div>

      <div v-if="activeCiteDetail" class="amv__cite-detail">
        <strong>{{ activeCiteDetail.title }}</strong>
        <p v-if="activeCiteDetail.snippet">{{ activeCiteDetail.snippet }}</p>
        <a v-if="activeCiteDetail.url" :href="activeCiteDetail.url" target="_blank" rel="noopener noreferrer">打开链接</a>
        <RouterLink v-else-if="citeInternalPath(activeCiteDetail)" :to="citeInternalPath(activeCiteDetail)">在平台中打开</RouterLink>
      </div>

      <p v-if="msg.errorMessage" class="amv__error">{{ msg.errorMessage }}</p>

      <div
        v-if="showToolbar && msg.role === 'assistant' && displayText && (msg.status === 'completed' || msg.status === 'failed' || msg.status === 'cancelled')"
        class="amv__toolbar"
      >
        <button type="button" class="amv__tool-btn" @click="copy">复制</button>
        <button
          v-if="onRegenerate"
          type="button"
          class="amv__tool-btn"
          :disabled="regenerateDisabled"
          @click="$emit('regenerate', msg)"
        >重新生成</button>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import XiaoQiMark from '../../components/brand/XiaoQiMark.vue'
import { formatAssistantMarkdown } from '../../utils/assistantMarkdown'
import 'highlight.js/styles/github-dark.min.css'

/** 一眼假的模板备注：前端过滤，绝不展示 */
const FAKE_NOTE_RE = /组织协作|先拆题|再取依据|最后综合|进入分步推理|正在汇总各方|将更多依赖对话|通用推理|深度推理准备|综合依据并生成|按「.+」组织/

/** 假编排步骤：不展示 */
const FAKE_STEP_KEYS = new Set([
  'orchestrate',
  'synthesize',
  'think_prep',
  'intent',
  'context_tool',
  'get_scores',
])

const props = defineProps({
  msg: { type: Object, required: true },
  compact: { type: Boolean, default: false },
  showToolbar: { type: Boolean, default: true },
  regenerateDisabled: { type: Boolean, default: false },
  onRegenerate: { type: Boolean, default: false },
  hidePlanDraft: { type: Boolean, default: false },
})

const emit = defineEmits(['regenerate', 'expand-plan'])

function onExpandPlan(pd) {
  if (!pd || pd._busy || pd.status === 'expanded') return
  pd._busy = true
  pd.status = 'expanded'
  emit('expand-plan', {
    expandText: pd.expandText || (pd.kind === 'rewrite' ? '展开完整改稿' : '展开完整计划'),
    kind: pd.kind,
    draft: pd,
  })
}

const activeCite = ref(null)
const citesRef = ref(null)
const reasoningScrollRef = ref(null)
const processOpen = ref(true)
const nowTick = ref(Date.now())
/** 打字机已揭示的纯文本前缀（对 displayText 做 catch-up） */
const typedText = ref('')
const isTypewriting = ref(false)
/** 本组件生命周期内是否经历过流式输出（历史消息不打字） */
const hasBeenLive = ref(false)
/** 父级消息列表滚到底（首页 / 工作台 provide） */
const scrollParentToBottom = inject('assistantScrollToBottom', null)
/** 用户是否刚在 Reasoning 区内手动上滑（短暂停跟底，避免抢滚轮） */
const reasoningStickBottom = ref(true)
let tickTimer = null
let typeRaf = 0
let typeLastTs = 0
let scrollThrottle = 0
let reasoningScrollThrottle = 0

function requestScrollToLatest() {
  if (typeof scrollParentToBottom !== 'function') return
  const now = Date.now()
  if (now - scrollThrottle < 48) return
  scrollThrottle = now
  try {
    scrollParentToBottom(true)
  } catch {
    /* ignore */
  }
}

/** Reasoning 内部滚动区跟到底（max-height 盒子，外层滚动管不到） */
function scrollReasoningToLatest(force = false) {
  const el = reasoningScrollRef.value
  if (!el) return
  if (!force && !reasoningStickBottom.value) return
  const now = Date.now()
  if (!force && now - reasoningScrollThrottle < 32) return
  reasoningScrollThrottle = now
  // 同步设 scrollTop，避免 rAF 晚一帧用户看到旧底
  el.scrollTop = el.scrollHeight + 80
}

function onReasoningScroll() {
  const el = reasoningScrollRef.value
  if (!el) return
  const dist = el.scrollHeight - el.scrollTop - el.clientHeight
  // 离底 > 40px 视为用户在往回看，暂停跟底
  reasoningStickBottom.value = dist < 40
}

const displayText = computed(() => props.msg.contentText || props.msg.text || '')

const livePhase = computed(() => {
  if (props.msg.phase) return props.msg.phase
  if (props.msg.status === 'streaming') {
    if (displayText.value) return 'answering'
    return 'thinking'
  }
  return 'done'
})

const isAnswerStreaming = computed(() => (
  props.msg.status === 'streaming' && livePhase.value === 'answering'
))

/** 是否走打字机揭示（流式中或尚未追上全文） */
const useTypewriterReveal = computed(() => (
  hasBeenLive.value
  || props.msg.status === 'streaming'
  || isTypewriting.value
))

const toolRows = computed(() => (
  (props.msg.steps || []).filter((s) => {
    const key = String(s.stepKey || '')
    if (FAKE_STEP_KEYS.has(key)) return false
    return s.kind === 'tool'
      || key.includes('search')
      || String(s.action || '').includes('检索')
      || String(s.action || '').includes('搜索')
  })
))

const visibleAgentNotes = computed(() => (
  (props.msg.agentNotes || []).filter((n) => {
    const t = String(n?.text || '').trim()
    if (!t || t.length < 4) return false
    if (FAKE_NOTE_RE.test(t)) return false
    return true
  })
))

const otherSteps = computed(() => (
  (props.msg.steps || []).filter((s) => {
    const key = String(s.stepKey || '')
    if (FAKE_STEP_KEYS.has(key)) return false
    if (s.kind === 'tool' || key.includes('search')) return false
    // 仅保留有实质摘要的非工具步骤
    return !!(s.outputSummary && String(s.outputSummary).length > 2)
  })
))

const hasExpandableProcess = computed(() => (
  toolRows.value.length > 0
  || visibleAgentNotes.value.length > 0
  || !!props.msg.thinkingText
  || otherSteps.value.length > 0
))

const hasProcess = computed(() => hasExpandableProcess.value || !!props.msg.streamStartedAt)

const showProcessTheater = computed(() => (
  props.msg.role === 'assistant' && (
    hasExpandableProcess.value
    || (props.msg.status === 'streaming' && !displayText.value)
    || (props.msg.processSummary && (props.msg.status === 'completed' || props.msg.status === 'failed'))
  )
))

/**
 * 仅在「还在出 reasoning、正文尚未开始」时显示 Thinking 动画。
 * thinkingDone / 已有正文 → 不再无限 Thinking（解决首页卡 30s）。
 */
const isProcessLive = computed(() => {
  if (props.msg.status !== 'streaming') return false
  if (displayText.value) return false
  if (props.msg.phase === 'answering' || props.msg.answerStartedAt) return false
  if (props.msg.thinkingDone) return false
  return true
})

const isProcessFailed = computed(() => (
  props.msg.status === 'failed' || props.msg.status === 'cancelled'
))

const processSeconds = computed(() => {
  if (props.msg.processSummary?.durationMs != null && !isProcessLive.value) {
    return Math.max(1, Math.round(props.msg.processSummary.durationMs / 1000))
  }
  if (props.msg.thinkingDurationMs != null && !isProcessLive.value) {
    return Math.max(1, Math.round(props.msg.thinkingDurationMs / 1000))
  }
  const start = props.msg.thinkingStartedAt || props.msg.streamStartedAt || Date.now()
  return Math.max(0, Math.floor((nowTick.value - start) / 1000))
})

const processHeaderLabel = computed(() => {
  if (props.msg.status === 'cancelled') return 'Stopped'
  if (props.msg.status === 'failed') return 'Failed'
  if (isProcessLive.value) return 'Thinking'
  return `Thought for ${processSeconds.value}s`
})

const processSummaryBits = computed(() => {
  const bits = []
  const ps = props.msg.processSummary || {}
  let site = Number(ps.siteCount)
  let web = Number(ps.webCount)
  if (!Number.isFinite(site)) site = 0
  if (!Number.isFinite(web)) web = 0
  if (site === 0 && web === 0) {
    for (const row of toolRows.value) {
      const key = String(row.stepKey || '')
      const n = row.resultCount != null ? Number(row.resultCount) : 0
      if (!Number.isFinite(n) || n <= 0) continue
      if (key.includes('web')) web += n
      else site += n
    }
  }
  if (site > 0) bits.push(`站内${site}`)
  if (web > 0) bits.push(`网页${web}`)
  return bits
})

const htmlContent = computed(() => {
  // 关键：`typedText || displayText` 在 typedText==='' 时会立刻露出全文
  const source = useTypewriterReveal.value
    ? typedText.value
    : (displayText.value || '')
  let html = formatAssistantMarkdown(source, {
    streaming: isAnswerStreaming.value || isTypewriting.value,
    citations: props.msg.citations || [],
  })
  // 把光标插在 Markdown 末尾，保证在最后一行文字旁
  if (isAnswerStreaming.value || isTypewriting.value) {
    html += '<span class="amv-type-caret" aria-hidden="true"></span>'
  }
  return html
})

const activeCiteDetail = computed(() => {
  if (activeCite.value == null) return null
  return (props.msg.citations || []).find((c) => Number(c.index) === Number(activeCite.value)) || null
})

function stopTypewriter() {
  if (typeRaf) {
    cancelAnimationFrame(typeRaf)
    typeRaf = 0
  }
  typeLastTs = 0
  isTypewriting.value = false
}

/**
 * 打字机：追赶 displayText。
 * - 流式中：约 28–48 字/秒，落后多时略加速
 * - 流结束后：仍继续打完（不因 completed 整段闪出）
 * - 历史消息：ensureTypewriter 里直接灌满
 */
function pumpTypewriter(ts) {
  typeRaf = 0
  const target = displayText.value || ''
  const current = typedText.value
  if (!target) {
    typedText.value = ''
    isTypewriting.value = false
    return
  }
  if (current.length >= target.length) {
    typedText.value = target
    // 流式中等更多 token；已完成则收光标
    if (props.msg.status === 'streaming') {
      isTypewriting.value = true
      typeRaf = requestAnimationFrame(pumpTypewriter)
    } else {
      isTypewriting.value = false
    }
    return
  }

  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    typedText.value = target
    isTypewriting.value = props.msg.status === 'streaming'
    return
  }

  const lag = target.length - current.length
  const stillStreaming = props.msg.status === 'streaming'
  // 可见的打字速度；落后很多时稍微加快，但完成后也不要「刷屏」
  let cps
  if (stillStreaming) {
    cps = lag > 200 ? 56 : lag > 80 ? 42 : 30
  } else {
    // 流已结束：稳定打完剩余，约 48 字/秒
    cps = lag > 400 ? 72 : 48
  }

  if (!typeLastTs) typeLastTs = ts
  const dt = Math.min(50, Math.max(0, ts - typeLastTs))
  typeLastTs = ts
  // 保证每帧至少 1 字，避免 dt 很小卡住
  let step = Math.max(1, Math.round((cps * dt) / 1000) || 1)
  // 中文阅读感：单帧别蹦太多
  if (stillStreaming) step = Math.min(step, 3)
  else step = Math.min(step, 6)

  let nextLen = Math.min(target.length, current.length + step)
  if (nextLen < target.length) {
    const code = target.charCodeAt(nextLen - 1)
    if (code >= 0xd800 && code <= 0xdbff) nextLen += 1
  }
  typedText.value = target.slice(0, nextLen)
  isTypewriting.value = true
  requestScrollToLatest()
  typeRaf = requestAnimationFrame(pumpTypewriter)
}

function ensureTypewriter() {
  const target = displayText.value || ''
  if (!target) {
    // 还在 thinking、尚无正文
    if (props.msg.status === 'streaming') {
      hasBeenLive.value = true
      typedText.value = ''
    }
    return
  }

  // 历史消息（打开时已是终态、且本实例未经历流式）：直接全文
  if (
    !hasBeenLive.value
    && props.msg.status !== 'streaming'
    && (props.msg.status === 'completed' || props.msg.status === 'failed' || props.msg.status === 'cancelled')
  ) {
    typedText.value = target
    isTypewriting.value = false
    return
  }

  // 本轮活流：即使后端已标 completed，只要还没追上就继续打
  if (typedText.value.length < target.length) {
    if (!typeRaf) {
      typeLastTs = 0
      isTypewriting.value = true
      typeRaf = requestAnimationFrame(pumpTypewriter)
    }
  }
}

let collapseTimer = null
watch(
  () => [
    props.msg.status,
    displayText.value,
    props.msg.processSummary,
    props.msg.thinkingText,
    props.msg.thinkingDone,
    props.msg.phase,
  ],
  () => {
    if (props.msg.status === 'streaming') {
      hasBeenLive.value = true
    }
    if (collapseTimer) {
      clearTimeout(collapseTimer)
      collapseTimer = null
    }
    // 正文开始输出：收起过程面板，把视口让给回答
    if (displayText.value || props.msg.phase === 'answering') {
      if (processOpen.value && displayText.value) {
        collapseTimer = window.setTimeout(() => {
          processOpen.value = false
        }, 280)
      }
    } else if (isProcessLive.value) {
      processOpen.value = hasExpandableProcess.value
    } else if (props.msg.status === 'failed' || props.msg.status === 'cancelled') {
      processOpen.value = false
    } else if (displayText.value && props.msg.status !== 'streaming' && !isTypewriting.value) {
      collapseTimer = window.setTimeout(() => {
        processOpen.value = false
      }, 350)
    }
    ensureTypewriter()
    requestScrollToLatest()
    // Reasoning 流式增长：内部容器跟底 + 外层列表跟底
    if (props.msg.thinkingText && props.msg.status === 'streaming') {
      nextTick(() => scrollReasoningToLatest())
    }
  },
  { immediate: true }
)

watch(
  () => props.msg.thinkingText,
  (next, prev) => {
    if (!next) return
    if (next === prev) return
    // 新一轮思考开始时恢复跟底
    if (!prev || (typeof next === 'string' && typeof prev === 'string' && next.length < prev.length)) {
      reasoningStickBottom.value = true
    }
    nextTick(() => {
      scrollReasoningToLatest()
      requestScrollToLatest()
    })
  }
)

watch(
  () => props.msg.status,
  (status, prev) => {
    if (status === 'streaming' && prev !== 'streaming') {
      hasBeenLive.value = true
      // 新一轮流式：若正文还没开始，清空揭示缓冲
      if (!displayText.value) {
        typedText.value = ''
        stopTypewriter()
      }
    }
  }
)

// 正文从空→有字：确保立刻启动打字机（不依赖 status 变化时机）
watch(
  () => displayText.value,
  (next, prev) => {
    if (next && (!prev || next.length > (prev || '').length)) {
      if (props.msg.status === 'streaming' || hasBeenLive.value) {
        hasBeenLive.value = true
        ensureTypewriter()
      }
    }
  }
)

onMounted(() => {
  if (props.msg.status === 'streaming') hasBeenLive.value = true
  tickTimer = window.setInterval(() => {
    if (props.msg.status === 'streaming' || isTypewriting.value) nowTick.value = Date.now()
  }, 250)
  ensureTypewriter()
})
onBeforeUnmount(() => {
  if (tickTimer) window.clearInterval(tickTimer)
  if (collapseTimer) clearTimeout(collapseTimer)
  stopTypewriter()
})

function truncateQuery(q, max = 56) {
  const s = String(q || '')
  if (s.length <= max) return s
  return `${s.slice(0, max)}…`
}

function goalLabel(goal) {
  const map = { answer: '对话', rewrite: '改稿', plan: '计划', score_review: '评分复盘', artifact: '生成产物', clarify: '补全意图' }
  return map[goal] || goal || '对话'
}
function sourceTypeLabel(t) {
  const map = {
    web: '联网',
    resource: '资料',
    training: '训练',
    score: '评分',
    report: '评分',
    task: '任务',
    collab: '协同',
    teacher: '教学',
    unknown: '来源',
  }
  return map[t] || '来源'
}
function citeTitle(c) {
  return [c.title, c.snippet, c.url].filter(Boolean).join(' · ')
}
function citeInternalPath(c) {
  if (c?.reportId) return `/ai-score/report-id/${c.reportId}/result`
  if (c?.sessionId) return `/ai-score/report/${c.sessionId}/result`
  if (c?.resourceId) return `/resource-center?highlight=${c.resourceId}`
  return null
}
function focusCite(c) {
  activeCite.value = Number(c.index)
}
function onContentClick(e) {
  // 代码块复制（Grok-like 工具栏 SVG 按钮）
  const copyBtn = e.target?.closest?.('[data-xq-copy]')
  if (copyBtn) {
    e.preventDefault()
    const block = copyBtn.closest?.('.xq-code-block')
    const code = block?.querySelector?.('code')
    const text = code?.textContent || ''
    if (text) {
      navigator.clipboard?.writeText(text).then(() => {
        copyBtn.classList.add('is-copied')
        window.setTimeout(() => copyBtn.classList.remove('is-copied'), 1400)
      }).catch(() => { /* ignore */ })
    }
    return
  }
  const btn = e.target?.closest?.('[data-cite-index]')
  if (!btn) return
  const n = Number(btn.getAttribute('data-cite-index'))
  if (!Number.isFinite(n)) return
  activeCite.value = n
  citesRef.value?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
}
async function copy() {
  try { await navigator.clipboard.writeText(displayText.value) } catch { /* ignore */ }
}
</script>

<style scoped>
.amv {
  display: flex;
  gap: 12px;
  max-width: 100%;
  min-width: 0;
}
.amv.is-user { justify-content: flex-end; }
.amv.is-assistant { align-items: flex-start; }
.amv__avatar {
  flex: none;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  margin-top: 2px;
}
.amv__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.amv.is-user .amv__body {
  flex: 0 1 auto;
  max-width: min(88%, 360px);
}

.amv__user-text {
  background: linear-gradient(135deg, #e84a1c, #c43a12);
  color: #fff;
  border-radius: 16px 16px 6px 16px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.5;
  font-weight: 500;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 6px 16px rgba(196, 58, 18, 0.12);
}

/* —— Grok-style thinking row —— */
.amv__theater {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}

.amv__think-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: transparent;
  padding: 4px 0 8px;
  cursor: default;
  color: #71717a;
  text-align: left;
  min-height: 28px;
}
.amv__think-row:not(:disabled) {
  cursor: pointer;
}
.amv__think-row:not(:disabled):hover .amv__think-label {
  color: #3f3f46;
}
.amv__think-row.is-live {
  color: #52525b;
}
.amv__think-row.is-error .amv__think-label {
  color: #b91c1c;
}

.amv__think-orb {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid #a1a1aa;
  border-top-color: #27272a;
  opacity: 0.85;
}
.amv__think-orb.is-spinning {
  animation: amv-orb-spin 0.75s linear infinite;
  border-color: rgba(161, 161, 170, 0.35);
  border-top-color: #27272a;
}
.amv__think-row.is-done .amv__think-orb {
  border: 0;
  background: #d4d4d8;
  width: 6px;
  height: 6px;
  margin: 0 2px;
  opacity: 0.9;
}

.amv__think-label {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: -0.01em;
  color: inherit;
  font-style: italic;
  display: inline-flex;
  align-items: baseline;
  gap: 1px;
}
.amv__think-row.is-done .amv__think-label {
  font-style: normal;
  font-weight: 550;
  color: #71717a;
}

.amv__think-dots {
  display: inline-flex;
  gap: 2px;
  margin-left: 2px;
  width: 14px;
}
.amv__think-dots i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.25;
  animation: amv-dot-pulse 1.2s ease-in-out infinite;
}
.amv__think-dots i:nth-child(2) { animation-delay: 0.15s; }
.amv__think-dots i:nth-child(3) { animation-delay: 0.3s; }

.amv__think-time {
  font-size: 12px;
  font-weight: 550;
  font-variant-numeric: tabular-nums;
  color: #a1a1aa;
}
.amv__think-meta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 550;
  color: #a1a1aa;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.amv__header-dot {
  opacity: 0.55;
  margin: 0 1px;
}
.amv__header-spacer { flex: 1; }
.amv__chev {
  color: #a1a1aa;
  transition: transform 0.2s ease;
  opacity: 0.8;
}
.amv__chev.is-open { transform: rotate(180deg); }

.amv__process {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 0 4px;
}

/* 工具行 */
.amv__tool {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.amv__tool-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.amv__tool-icon {
  flex: none;
  width: 18px;
  height: 18px;
  margin-top: 1px;
  color: var(--ds-muted, #71717a);
  display: grid;
  place-items: center;
}
.amv__tool-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.amv__tool-copy strong {
  font-size: 12.5px;
  font-weight: 650;
  color: var(--ds-ink-2, #3f3f46);
}
.amv__tool-query {
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--ds-ink, #0a0a0a);
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.amv__tool,
.amv__agent,
.amv__misc {
  animation: amv-card-in 0.18s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.amv__tool-meta {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 1px;
}
.amv__tool-count {
  font-size: 12px;
  font-weight: 650;
  color: var(--ds-faint, #8b8b93);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.amv__tool-count.is-live {
  color: var(--ds-orange-700, #c43a12);
}
.amv__tool-pills {
  display: inline-flex;
  align-items: center;
}
.amv__tool-pills i {
  width: 14px;
  height: 14px;
  margin-left: -5px;
  border-radius: 999px;
  border: 1.5px solid #fff;
  display: block;
  opacity: 0.85;
}
.amv__tool-pills i:first-child { margin-left: 0; }
.amv__tool.is-running .amv__tool-query {
  color: var(--ds-muted, #71717a);
}

/* 工作日志式备注（单主体，不演多角色） */
.amv__log {
  padding: 0 0 0 26px;
  animation: amv-card-in 0.18s ease both;
}
.amv__log p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: #52525b;
  font-weight: 500;
}

.amv__raw-think {
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.03);
  border: 1px solid rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.amv__raw-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-faint, #8b8b93);
  margin-bottom: 4px;
  flex: none;
}
.amv__raw-think-body {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #64748b;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: min(220px, 36vh);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.18) transparent;
}

.amv__misc {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
  color: var(--ds-muted, #71717a);
}
.amv__misc-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d4d4d8;
  flex: none;
}
.amv__misc.is-running .amv__misc-dot {
  background: #e84a1c;
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.12);
}
.amv__misc small {
  color: var(--ds-faint, #8b8b93);
}

.amv__hints {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.amv__chip {
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.06);
  color: #52525b;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

.amv__answer {
  position: relative;
  display: block;
}
.amv__content {
  font-size: 14.5px;
  line-height: 1.72;
  color: #1c1917;
  word-break: break-word;
  letter-spacing: -0.011em;
  font-weight: 450;
}
.amv.is-compact .amv__content {
  font-size: 13.5px;
  line-height: 1.65;
}

/* Grok-like caret（插在 markdown 末尾） */
.amv__content :deep(.amv-type-caret) {
  display: inline-block;
  width: 2px;
  height: 1.05em;
  margin-left: 2px;
  vertical-align: text-bottom;
  border-radius: 1px;
  background: #18181b;
  animation: amv-caret-blink 1.05s step-end infinite;
}

.amv__plan-drafts {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}
.amv__plan-draft {
  border: 1px solid rgba(232, 74, 28, 0.22);
  background: color-mix(in srgb, #e84a1c 6%, #fff);
  border-radius: 12px;
  padding: 10px 12px;
}
.amv__plan-draft.is-expanded {
  opacity: 0.72;
  border-color: rgba(0, 0, 0, 0.08);
  background: #f7f7f8;
}
.amv__plan-draft__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: #1a1d24;
}
.amv__plan-draft__badge {
  font-size: 11px;
  font-weight: 650;
  color: #e84a1c;
  background: rgba(232, 74, 28, 0.1);
  padding: 2px 8px;
  border-radius: 999px;
}
.amv__plan-draft.is-expanded .amv__plan-draft__badge {
  color: #71717a;
  background: rgba(0, 0, 0, 0.06);
}
.amv__plan-draft__summary {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: #5c6370;
  line-height: 1.45;
}
.amv__plan-draft__actions {
  margin-top: 10px;
}
.amv__plan-draft__btn {
  border: 0;
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 650;
  color: #fff;
  background: linear-gradient(135deg, #e84a1c, #c43a12);
  cursor: pointer;
}
.amv__plan-draft__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.amv__cites {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.amv__cites-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted, #71717a);
}
.amv__cite {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ds-ink-2, #3f3f46);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.amv__cite sup {
  font-weight: 750;
  color: var(--ds-orange-700, #c43a12);
}
.amv__cite-type {
  font-size: 10px;
  font-weight: 700;
  color: var(--ds-muted, #71717a);
}
.amv__cite.is-web { border-color: rgba(37, 99, 235, 0.25); }
.amv__cite.is-score,
.amv__cite.is-report { border-color: rgba(232, 74, 28, 0.25); }
.amv__cite.is-active {
  background: #fff7f2;
  border-color: rgba(232, 74, 28, 0.4);
}
.amv__cite-detail {
  padding: 10px 12px;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid rgba(15, 23, 42, 0.06);
  font-size: 12px;
  line-height: 1.5;
}
.amv__cite-detail strong { display: block; margin-bottom: 4px; }
.amv__cite-detail p { margin: 0 0 6px; color: var(--ds-muted, #71717a); }
.amv__cite-detail a {
  color: var(--ds-orange-700, #c43a12);
  font-weight: 650;
  text-decoration: none;
}
.amv__error { margin: 0; font-size: 12px; color: #b91c1c; }
.amv__toolbar { display: flex; gap: 8px; }
.amv__tool-btn {
  border: 0;
  background: transparent;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  padding: 2px 0;
}
.amv__tool-btn:hover { color: var(--ds-orange-700, #c43a12); }
.amv__tool-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.amv__content :deep(.xq-cite-mark) {
  display: inline;
  border: 0;
  background: rgba(232, 74, 28, 0.1);
  color: var(--ds-orange-700, #c43a12);
  border-radius: 4px;
  padding: 0 3px;
  margin: 0 1px;
  font-size: 0.85em;
  font-weight: 750;
  cursor: pointer;
  vertical-align: super;
}
/* —— Grok-like prose —— */
.amv__content :deep(.xq-code-block) {
  margin: 12px 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #0c0e12;
  color: #e2e8f0;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.04) inset;
}
.amv__content :deep(.xq-code-bar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(255, 255, 255, 0.03);
}
.amv__content :deep(.xq-code-lang) {
  font-size: 11px;
  font-weight: 650;
  color: #94a3b8;
  letter-spacing: 0.02em;
  text-transform: lowercase;
}
.amv__content :deep(.xq-code-copy) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 0;
  background: transparent;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 6px;
  transition: color 0.15s ease, background 0.15s ease;
}
.amv__content :deep(.xq-code-copy:hover) {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.06);
}
.amv__content :deep(.xq-code-copy .xq-copy-check) { display: none; }
.amv__content :deep(.xq-code-copy.is-copied) {
  color: #4ade80;
}
.amv__content :deep(.xq-code-copy.is-copied .xq-copy-icon) { display: none; }
.amv__content :deep(.xq-code-copy.is-copied .xq-copy-check) { display: block; }
.amv__content :deep(.xq-code-copy.is-copied .xq-code-copy-label)::after {
  content: none;
}
.amv__content :deep(.xq-code-copy.is-copied .xq-code-copy-label) {
  /* label stays 复制 → 可改文案 via attr; keep simple */
}
.amv__content :deep(.xq-code-block pre) {
  margin: 0;
  padding: 12px 14px;
  overflow: auto;
  font-size: 12.5px;
  line-height: 1.55;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.amv__content :deep(.xq-code-block code.hljs) {
  background: transparent;
  padding: 0;
  color: inherit;
}
.amv__content :deep(.xq-inline-code) {
  padding: 1px 6px;
  border-radius: 5px;
  background: rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(15, 23, 42, 0.06);
  font-size: 0.9em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 快捷键键帽（Grok / 桌面软件常见样式） */
.amv__content :deep(.xq-kbd-cluster) {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  vertical-align: baseline;
  margin: 0 1px;
  white-space: nowrap;
}
.amv__content :deep(.xq-kbd) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.35em;
  height: 1.35em;
  padding: 0 5px;
  border-radius: 5px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-bottom-width: 2px;
  background: linear-gradient(180deg, #fafafa 0%, #f1f1f3 100%);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
  color: #27272a;
  font-size: 0.78em;
  font-weight: 700;
  font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
  letter-spacing: 0.01em;
  line-height: 1;
}
.amv__content :deep(.xq-kbd-plus) {
  font-size: 0.72em;
  font-weight: 700;
  color: #a1a1aa;
  padding: 0 1px;
}

.amv__content :deep(p) { margin: 0 0 0.75em; }
.amv__content :deep(p:last-child) { margin-bottom: 0; }
.amv__content :deep(ul),
.amv__content :deep(ol) { margin: 0.35em 0 0.85em; padding-left: 1.35em; }
.amv__content :deep(li) { margin: 0.2em 0; }
.amv__content :deep(li::marker) { color: #a1a1aa; }
.amv__content :deep(h1),
.amv__content :deep(h2),
.amv__content :deep(h3) {
  margin: 1em 0 0.4em;
  font-weight: 750;
  letter-spacing: -0.02em;
  color: var(--ds-ink, #0a0a0a);
  line-height: 1.3;
}
.amv__content :deep(h1) { font-size: 1.2em; }
.amv__content :deep(h2) { font-size: 1.08em; }
.amv__content :deep(h3) { font-size: 1.02em; }
.amv__content :deep(strong) { font-weight: 700; color: #18181b; }
.amv__content :deep(blockquote) {
  margin: 0.6em 0;
  padding: 6px 12px;
  border-left: 3px solid rgba(232, 74, 28, 0.45);
  color: #52525b;
  background: rgba(15, 23, 42, 0.02);
  border-radius: 0 8px 8px 0;
}
.amv__content :deep(hr) {
  border: 0;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  margin: 1em 0;
}
.amv__content :deep(a) {
  color: var(--ds-orange-700, #c43a12);
  font-weight: 600;
  text-decoration: none;
}
.amv__content :deep(a:hover) { text-decoration: underline; text-underline-offset: 2px; }

/* 表格：可扫读、可横向滚动 */
.amv__content :deep(.xq-table-wrap) {
  overflow: auto;
  margin: 0.75em 0;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  -webkit-overflow-scrolling: touch;
}
.amv__content :deep(table) {
  width: 100%;
  min-width: 280px;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}
.amv__content :deep(th),
.amv__content :deep(td) {
  padding: 9px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
  text-align: left;
  vertical-align: top;
  line-height: 1.45;
}
.amv__content :deep(th) {
  background: #fafafa;
  font-weight: 700;
  color: #3f3f46;
  font-size: 12px;
  letter-spacing: 0.01em;
  position: sticky;
  top: 0;
  z-index: 1;
}
.amv__content :deep(tbody tr:last-child td) {
  border-bottom: 0;
}
.amv__content :deep(tbody tr:hover td) {
  background: rgba(255, 247, 242, 0.55);
}
.amv__content :deep(th:not(:last-child)),
.amv__content :deep(td:not(:last-child)) {
  border-right: 1px solid rgba(15, 23, 42, 0.04);
}

@keyframes amv-card-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: none; }
}
@keyframes amv-orb-spin {
  to { transform: rotate(360deg); }
}
@keyframes amv-dot-pulse {
  0%, 80%, 100% { opacity: 0.2; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-1px); }
}
@keyframes amv-caret-blink {
  50% { opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .amv__agent,
  .amv__think-orb.is-spinning,
  .amv__think-dots i,
  .amv__content :deep(.amv-type-caret) {
    animation: none !important;
  }
  .amv__content :deep(.amv-type-caret) {
    opacity: 0.85;
  }
}
</style>
