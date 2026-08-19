<template>
  <!--
    首页嵌入版 = /assistant 中栏同款表面。
    P0：clientContext 强制学生人设；不污染 user content；无假附件图标。
  -->
  <section class="assistant-pane assistant-pane--chat hxq-embed" aria-label="小启AI">
    <header class="assistant-chat-header">
      <button
        type="button"
        class="xq-icon-btn"
        title="收起"
        aria-label="收起小启"
        @click="$emit('close')"
      >
        <XqIcon name="chevron-left" />
      </button>
      <span class="title-fallback hxq-embed__brand">
        <XiaoQiMark :size="22" :hoverable="false" />
        小启AI
      </span>
      <div class="assistant-header-actions">
        <button
          type="button"
          class="xq-icon-btn"
          title="新对话"
          aria-label="新对话"
          @click="resetChat"
        >
          <XqIcon name="plus" />
        </button>
        <RouterLink
          class="xq-icon-btn"
          to="/assistant"
          title="打开完整工作台"
          aria-label="打开完整工作台"
        >
          <XqIcon name="external" />
        </RouterLink>
      </div>
    </header>

    <div ref="scrollRef" class="assistant-messages">
      <div v-if="!messages.length" class="assistant-welcome hxq-embed__welcome">
        <div class="assistant-welcome__hero">
          <XiaoQiMark :size="52" :hoverable="true" aria-label="小启AI" />
          <h1>{{ welcomeTitle }}</h1>
          <p>{{ welcomeSub }}</p>
          <button
            v-if="contextBannerVisible && hasHomeContext"
            type="button"
            class="hxq-embed__ctx-pill"
            title="点击关闭提示"
            @click="contextBannerVisible = false"
          >
            已带入今日训练 + 最近评分
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <div class="assistant-chips hxq-embed__chips">
          <button
            v-for="chip in welcomeChips"
            :key="chip.q"
            type="button"
            class="assistant-chip"
            @click="send(chip.q)"
          >
            {{ chip.label }}
          </button>
        </div>
      </div>

      <div v-else class="assistant-thread">
        <div
          v-for="(msg, index) in messages"
          :key="msg.id || msg._localId || index"
          class="assistant-msg-wrap"
        >
          <AssistantMessageView
            :msg="msg"
            :show-toolbar="msg.role === 'assistant' && !!(msg.contentText || msg.text)"
            @expand-plan="onExpandPlan"
          />
          <p
            v-if="msg.role === 'user' && msg._homeContextAttached && contextBannerVisible"
            class="hxq-embed__ctx-note"
          >
            已附带今日训练与评分
            <button type="button" class="hxq-embed__ctx-note-x" @click="contextBannerVisible = false">关闭</button>
          </p>
        </div>
      </div>
    </div>

    <footer class="assistant-composer">
      <div class="assistant-composer__shell">
        <div ref="composerBoxRef" class="assistant-composer__box assistant-composer__box--slash">
          <SkillSlashMenu
            ref="skillMenuUiRef"
            :open="skillMenuOpen && open"
            :items="skillMenuItems"
            :anchor-el="composerBoxEl"
            @pick="onPickSkill"
            @close="closeSkillMenu"
          />
          <div class="assistant-mode-tabs" role="tablist" aria-label="回答模式">
            <button
              v-for="m in modes"
              :key="m.id"
              type="button"
              role="tab"
              class="assistant-mode-tab"
              :class="{ 'is-active': mode === m.id }"
              :aria-selected="mode === m.id"
              :disabled="sending"
              @click="mode = m.id"
            >
              {{ m.label }}
            </button>
          </div>
          <textarea
            ref="inputRef"
            v-model="draft"
            rows="1"
            placeholder="问问小启… 输入 / 选技能（开场、复盘、今日、改稿）"
            :disabled="sending && !canStop"
            autocomplete="off"
            @keydown="onKeydown"
            @compositionstart="composing = true"
            @compositionend="composing = false"
            @input="onComposerInput"
            @click="onSkillMenuSelect()"
            @keyup="onSkillMenuSelect()"
          />
          <div class="assistant-composer__actions">
            <div class="composer-tools">
              <button
                type="button"
                class="xq-icon-btn"
                title="技能菜单（/）"
                aria-label="打开技能菜单"
                :disabled="sending"
                @click="openSkillMenu()"
              >
                <span class="skill-slash-trigger" aria-hidden="true">/</span>
              </button>
              <RouterLink class="hxq-embed__quiet-link" to="/assistant">
                在完整工作台上传附件
              </RouterLink>
            </div>
            <button
              v-if="sending"
              type="button"
              class="xq-icon-btn xq-icon-btn--danger"
              title="停止生成"
              aria-label="停止生成"
              @click="stopGeneration"
            >
              <XqIcon name="stop" />
            </button>
            <button
              v-else
              type="button"
              class="xq-send-btn"
              :disabled="!draft.trim()"
              title="发送"
              aria-label="发送"
              @click="submit"
            >
              <XqIcon name="send" size="md" />
            </button>
          </div>
        </div>
        <p class="composer-hint">
          {{ sending ? modeBusy : '输入 / 选技能 · Enter 发送 · Shift+Enter 换行 · 首页附带今日训练与评分' }}
        </p>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import XiaoQiMark from '../../components/brand/XiaoQiMark.vue'
import XqIcon from '../../components/assistant/XqIcon.vue'
import AssistantMessageView from '../assistant-core/AssistantMessageView.vue'
import SkillSlashMenu from '../assistant-core/SkillSlashMenu.vue'
import { useSkillSlashMenu } from '../assistant-core/useSkillSlashMenu'
import {
  applyAssistantStreamEvent,
  createEmptyAssistantMessage,
  createUserMessage,
  promoteReasoningToAnswerIfNeeded,
} from '../assistant-core/handleStreamEvent'
import * as assistantApi from '../../services/assistantClient'
import { getStoredUser } from '../../utils/authStorage'
import '../../styles/assistant.css'

/** 固定前缀；完整 key 必须带 userId，禁止跨账号串缓存 */
const STORAGE_PREFIX = 'orep.home.xiaoqi.thread.v1'
const LEGACY_STORAGE_KEY = STORAGE_PREFIX

function currentUserId() {
  const user = getStoredUser()
  const id = user?.id ?? user?.userId
  return id != null && String(id).trim() !== '' ? String(id) : ''
}

function storageKeyForUser(userId = currentUserId()) {
  if (!userId) return ''
  return `${STORAGE_PREFIX}.u${userId}`
}

const props = defineProps({
  home: { type: Object, default: () => ({}) },
  open: { type: Boolean, default: false },
})
defineEmits(['close'])

const modes = [
  { id: 'fast', label: '快速' },
  { id: 'think', label: '思考' },
  { id: 'deep_search', label: '联网' },
]

const draft = ref('')
const mode = ref('fast')
const sending = ref(false)
const canStop = ref(false)
const composing = ref(false)
const messages = ref([])
const scrollRef = ref(null)
const inputRef = ref(null)
const skillMenuUiRef = ref(null)
const composerBoxRef = ref(null)
const composerBoxEl = computed(() => composerBoxRef.value)
const sessionId = ref(null)
const contextBannerVisible = ref(true)
let abortController = null
let localIdSeq = 0
let persistTimer = null

const {
  menuOpen: skillMenuOpen,
  menuItems: skillMenuItems,
  menuRef: skillMenuInnerRef,
  closeMenu: closeSkillMenu,
  openMenuFromButton: openSkillMenu,
  pickSkill,
  onKeydown: onSkillMenuKeydown,
  onInput: onSkillMenuInput,
  onSelect: onSkillMenuSelect,
} = useSkillSlashMenu({
  textRef: draft,
  inputRef,
  audience: 'student',
  isDisabled: () => sending.value,
})
watch(skillMenuUiRef, (el) => {
  skillMenuInnerRef.value = el
})

function onPickSkill(skill) {
  pickSkill(skill)
  nextTick(() => autoGrow())
}

function onComposerInput() {
  autoGrow()
  onSkillMenuInput()
}

const modeBusy = computed(() => {
  if (mode.value === 'think') return '深度思考中…'
  if (mode.value === 'deep_search') return '联网检索中…'
  return '生成中…'
})

const teamId = computed(() => {
  const fromCamp = props.home?.camp?.teamId
  const fromProfile = props.home?.profile?.teamId
  const fromTeam = props.home?.team?.teamId
  return fromCamp || fromProfile || fromTeam || null
})
const latestScore = computed(() => props.home?.latestScore || {})
const todayTraining = computed(() => props.home?.todayTraining || {})
const primaryTask = computed(() => todayTraining.value.primaryTask || {})

const welcomeTitle = computed(() => '今天想推进哪一步？')
const welcomeSub = computed(() => (
  todayTraining.value.hasTrainingDay
    ? '结合训练、评分与待办真实数据回答。点下方示例，或直接输入。'
    : '写讲稿、改开场、看评分、排备赛都可以。点下方示例，或直接输入。'
))

const hasHomeContext = computed(() => {
  const camp = props.home?.camp
  const hasCamp = camp && (camp.campId || camp.campName || camp.currentDay != null)
  return !!(hasCamp || todayTraining.value.hasTrainingDay || latestScore.value.hasReport
    || (props.home?.nextActions || []).length)
})

const welcomeChips = computed(() => {
  const list = []
  if (todayTraining.value.hasTrainingDay && primaryTask.value.title) {
    const t = String(primaryTask.value.title)
    list.push({
      label: `为什么要做「${t.slice(0, 18)}${t.length > 18 ? '…' : ''}」？`,
      q: `结合我首页的今日训练，解释为什么要做「${primaryTask.value.title}」，以及怎么算完成。`,
    })
  } else {
    list.push({
      label: '/开场 · 30 秒示例',
      q: '/开场 先给一版 30 秒路演开场示例，再按我的项目改。',
    })
  }
  if (latestScore.value.hasReport) {
    const score = Number(latestScore.value.overallScore)
    list.push({
      label: '/复盘 · 优先补哪维',
      q: `/复盘 我最近一次 AI 评分综合约 ${Number.isFinite(score) ? score.toFixed(1) : '—'} 分，请基于五维说明优先短板和下一步。`,
    })
  } else {
    list.push({
      label: '/复盘 · 按评分改讲稿',
      q: '/复盘 根据我最近的 AI 评分，指出讲稿最该改的两处，并给出改写示例。',
    })
  }
  if ((props.home?.nextActions || []).length) {
    list.push({
      label: '/今日 · 下一步优先',
      q: '/今日 根据我当前的训练营进度、今日任务和待办，列出优先级最高的下一步。',
    })
  } else {
    list.push({
      label: '/今日 · 训练计划要点',
      q: '/今日 结合我的备赛进度，生成本周训练计划要点（不并行摊薄）。',
    })
  }
  list.push({
    label: '/改稿 · 润色开场',
    q: '/改稿 帮我润色一版更口语的 30 秒开场（先给示例）。',
  })
  return list.slice(0, 4)
})

/** 结构化上下文：只走 clientContext，绝不拼进 content */
function buildClientContext() {
  return {
    source: 'home',
    audience: 'student',
    camp: props.home?.camp || null,
    todayTraining: props.home?.todayTraining || null,
    latestScore: props.home?.latestScore || null,
    nextActions: (props.home?.nextActions || []).slice(0, 5),
    profile: props.home?.profile
      ? { username: props.home.profile.username, teamId: props.home.profile.teamId }
      : null,
  }
}

/**
 * 始终跟到底（首页半栏无「用户上滑暂停」语义；过程展开/打字机会反复增高）
 */
function scrollBottom(_force = true) {
  nextTick(() => {
    requestAnimationFrame(() => {
      const el = scrollRef.value
      if (!el) return
      el.scrollTop = el.scrollHeight + 120
    })
  })
}

provide('assistantScrollToBottom', scrollBottom)

function autoGrow() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(140, Math.max(28, el.scrollHeight))}px`
}

function onKeydown(e) {
  if (onSkillMenuKeydown(e)) return
  if (e.key !== 'Enter' || e.shiftKey) return
  if (composing.value || e.isComposing) return
  e.preventDefault()
  submit()
}

async function ensureSession({ forceNew = false } = {}) {
  if (!forceNew && sessionId.value) return sessionId.value
  const body = teamId.value ? { teamId: Number(teamId.value) } : {}
  const res = await assistantApi.createSession(body)
  const session = res?.data ?? res
  const id = session?.id ?? session?.sessionId
  if (!id) throw new Error('无法创建小启会话')
  sessionId.value = id
  schedulePersist()
  return id
}

function isSessionGoneError(error) {
  if (Number(error?.status) === 404) return true
  const msg = String(error?.message || error || '')
  return /HTTP\s*404|会话不存在|NOT_FOUND|404/.test(msg)
}

function schedulePersist() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(persistThread, 200)
}

function persistThread() {
  try {
    const userId = currentUserId()
    const key = storageKeyForUser(userId)
    if (!key) return
    // 清理旧版无用户维度的 key，避免换号后仍被读到
    try { localStorage.removeItem(LEGACY_STORAGE_KEY) } catch { /* ignore */ }
    if (!messages.value.length && !sessionId.value) {
      localStorage.removeItem(key)
      return
    }
    const payload = {
      userId,
      sessionId: sessionId.value,
      mode: mode.value,
      messages: messages.value.map(serializeMsg),
      savedAt: Date.now(),
    }
    localStorage.setItem(key, JSON.stringify(payload))
  } catch {
    /* quota / private mode */
  }
}

function serializeMsg(m) {
  return {
    id: m.id,
    _localId: m._localId,
    role: m.role,
    contentText: m.contentText || m.text || '',
    text: m.contentText || m.text || '',
    status: m.status === 'streaming' ? 'completed' : m.status,
    thinkingText: m.thinkingText || '',
    thinkingDurationMs: m.thinkingDurationMs,
    steps: m.steps || [],
    agentNotes: m.agentNotes || [],
    citations: m.citations || [],
    processSummary: m.processSummary || null,
    brainHints: m.brainHints || null,
    phase: m.phase || 'done',
    errorMessage: m.errorMessage || '',
    _homeContextAttached: !!m._homeContextAttached,
  }
}

function restoreThread() {
  try {
    // 旧 key 无账号隔离：一律丢弃，防止 A 账号聊天被 B 看到
    try { localStorage.removeItem(LEGACY_STORAGE_KEY) } catch { /* ignore */ }

    const userId = currentUserId()
    const key = storageKeyForUser(userId)
    if (!key) return

    const raw = localStorage.getItem(key)
    if (!raw) return
    const data = JSON.parse(raw)
    if (!data || !Array.isArray(data.messages) || !data.messages.length) return
    // 双重校验：payload.userId 必须对应当前登录用户
    if (data.userId != null && String(data.userId) !== userId) {
      localStorage.removeItem(key)
      return
    }
    // 超过 7 天丢弃
    if (data.savedAt && Date.now() - data.savedAt > 7 * 24 * 3600 * 1000) {
      localStorage.removeItem(key)
      return
    }
    sessionId.value = data.sessionId || null
    if (data.mode) mode.value = data.mode
    messages.value = data.messages.map((m) => ({
      ...m,
      status: m.status === 'streaming' ? 'completed' : (m.status || 'completed'),
    }))
  } catch {
    /* ignore */
  }
}

function onExpandPlan(payload) {
  const text = String(payload?.expandText || '展开完整计划').trim()
  if (!text || sending.value) return
  send(text)
}

async function send(text) {
  const content = String(text || '').trim()
  if (!content || sending.value) return

  sending.value = true
  canStop.value = true
  const userMsg = createUserMessage(content, `u-${++localIdSeq}`)
  const isFirstTurn = messages.value.filter((m) => m.role === 'user').length === 0
  if (isFirstTurn && hasHomeContext.value) {
    userMsg._homeContextAttached = true
  }
  const aiMsg = createEmptyAssistantMessage(`a-${++localIdSeq}`)
  messages.value.push(userMsg, aiMsg)
  schedulePersist()
  scrollBottom()

  abortController?.abort()
  abortController = new AbortController()

  try {
    const clientContext = buildClientContext()
    const payload = {
      // 干净用户原文，绝不拼【首页上下文】
      content,
      clientMessageId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
      teamId: teamId.value ? Number(teamId.value) : undefined,
      mode: mode.value,
      audience: 'student',
      clientContext,
      options: {
        mode: mode.value,
        audience: 'student',
        forceStudent: true,
        clientContext,
      },
    }
    const onEvent = (eventName, data) => {
      applyAssistantStreamEvent(eventName, data, aiMsg, {
        onUserMessageId: (uid, runId) => {
          userMsg.id = uid
          if (runId != null) userMsg.runId = runId
        },
      })
      // 触发列表重绘（防止深层字段偶发不刷新）
      const idx = messages.value.findIndex((m) => m === aiMsg || m._localId === aiMsg._localId)
      if (idx >= 0) messages.value[idx] = aiMsg
      schedulePersist()
      scrollBottom(true)
    }

    let id = await ensureSession()
    try {
      await assistantApi.streamMessage(id, payload, {
        signal: abortController.signal,
        onEvent,
      })
    } catch (streamErr) {
      // 首页 localStorage 可能残留已删除/他端清掉的 sessionId → 404
      if (!isSessionGoneError(streamErr) || abortController.signal.aborted) throw streamErr
      sessionId.value = null
      id = await ensureSession({ forceNew: true })
      // 重试时清空半拉子流式状态
      Object.assign(aiMsg, createEmptyAssistantMessage(aiMsg._localId))
      await assistantApi.streamMessage(id, payload, {
        signal: abortController.signal,
        onEvent,
      })
    }

    // 流结束：强制收尾，避免永远卡在 Thinking
    if (aiMsg.status === 'streaming' || aiMsg.status === 'pending') {
      applyAssistantStreamEvent('run_completed', { status: 'completed' }, aiMsg)
    }
    promoteReasoningToAnswerIfNeeded(aiMsg)
    if (!aiMsg.contentText && !aiMsg.errorMessage) {
      aiMsg.contentText = '我已收到你的问题。若没有完整回复，请打开完整工作台继续。'
      aiMsg.text = aiMsg.contentText
    }
    aiMsg.phase = aiMsg.status === 'failed' ? aiMsg.phase : 'done'
  } catch (error) {
    if (error?.name === 'AbortError') {
      if (aiMsg.status === 'streaming') aiMsg.status = 'cancelled'
      promoteReasoningToAnswerIfNeeded(aiMsg)
      if (!aiMsg.contentText) {
        aiMsg.contentText = '已停止生成。'
        aiMsg.text = aiMsg.contentText
      }
    } else {
      aiMsg.status = 'failed'
      aiMsg.errorMessage = error?.message || '发送失败。请检查登录状态与网络。'
    }
  } finally {
    sending.value = false
    canStop.value = false
    // 再刷一次消息引用，确保 UI 离开 Thinking / 生成中
    messages.value = messages.value.map((m) => (
      m._localId === aiMsg._localId || m === aiMsg ? { ...aiMsg } : m
    ))
    schedulePersist()
    scrollBottom(true)
  }
}

function submit() {
  const value = draft.value
  if (!String(value || '').trim() || sending.value) return
  draft.value = ''
  nextTick(() => autoGrow())
  send(value)
}

function stopGeneration() {
  abortController?.abort()
  canStop.value = false
  sending.value = false
}

function resetChat() {
  abortController?.abort()
  messages.value = []
  sessionId.value = null
  sending.value = false
  canStop.value = false
  draft.value = ''
  contextBannerVisible.value = true
  try {
    localStorage.removeItem(LEGACY_STORAGE_KEY)
    const key = storageKeyForUser()
    if (key) localStorage.removeItem(key)
  } catch { /* ignore */ }
  nextTick(() => autoGrow())
}

/** 当前登录用户变化时：内存态也要切走，不能沿用上一账号 UI */
const boundUserId = ref(currentUserId())

function switchToCurrentUserThread() {
  const nextId = currentUserId()
  if (nextId === boundUserId.value) return
  abortController?.abort()
  messages.value = []
  sessionId.value = null
  sending.value = false
  canStop.value = false
  draft.value = ''
  boundUserId.value = nextId
  restoreThread()
}

watch(
  () => props.open,
  (open) => {
    if (!open) {
      // Teleport 到 body：半栏收起时必须关掉技能浮层，否则会残留在首页上
      closeSkillMenu()
      abortController?.abort()
    } else {
      switchToCurrentUserThread()
      nextTick(() => inputRef.value?.focus())
    }
  }
)

// 登录用户 id 变化（同页换号 / token 刷新后）立即隔离
watch(
  () => currentUserId(),
  () => switchToCurrentUserThread()
)

onMounted(() => {
  boundUserId.value = currentUserId()
  restoreThread()
})

onBeforeUnmount(() => {
  closeSkillMenu()
  abortController?.abort()
  if (persistTimer) clearTimeout(persistTimer)
  // 仅当前账号落盘，避免把未隔离内容写回
  persistThread()
})
</script>

<style scoped>
/*
 * 半栏 token：只做适配，视觉语言交给全局 assistant.css。
 */
.hxq-embed {
  --hxq-space-1: 8px;
  --hxq-space-2: 12px;
  --hxq-space-3: 16px;
  --hxq-space-4: 24px;
  --hxq-title: clamp(22px, 2.2vw, 24px);
  --hxq-sub: 13.5px;
  --hxq-chip: 13px;
  --hxq-process: 13px;
  --hxq-tool: 12px;

  height: 100%;
  min-height: 0;
  border-radius: inherit;
  overflow: hidden;
  background: #fff;
}

.hxq-embed__brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.hxq-embed :deep(a.xq-icon-btn) {
  text-decoration: none;
  color: inherit;
  box-sizing: border-box;
}

.hxq-embed :deep(.assistant-messages) {
  padding: var(--hxq-space-2) var(--hxq-space-3) var(--hxq-space-2);
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.14) transparent;
}

.hxq-embed__welcome {
  margin: 0 auto;
  min-height: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--hxq-space-2) var(--hxq-space-1) var(--hxq-space-1);
  box-sizing: border-box;
}

.hxq-embed :deep(.assistant-welcome h1) {
  font-size: var(--hxq-title);
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.hxq-embed :deep(.assistant-welcome p) {
  font-size: var(--hxq-sub);
  line-height: 1.45;
  max-width: 36ch;
}

.hxq-embed__ctx-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: var(--hxq-space-2);
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: #fafafa;
  color: #71717a;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
}
.hxq-embed__ctx-pill:hover {
  border-color: rgba(232, 74, 28, 0.22);
  color: #c43a12;
}
.hxq-embed__ctx-pill span {
  opacity: 0.55;
  font-weight: 700;
}

.hxq-embed__chips {
  display: grid !important;
  grid-template-columns: 1fr 1fr;
  gap: var(--hxq-space-1);
  max-width: 420px;
  margin: var(--hxq-space-3) auto 0;
  justify-content: stretch;
}

.hxq-embed :deep(.assistant-chip) {
  max-width: none;
  width: 100%;
  font-size: var(--hxq-chip);
  padding: 10px 12px;
  border-radius: 14px;
  min-height: 44px;
}

.hxq-embed :deep(.assistant-thread),
.hxq-embed :deep(.assistant-msg-wrap),
.hxq-embed :deep(.assistant-composer__shell) {
  max-width: 100%;
}

.hxq-embed :deep(.assistant-msg-wrap) {
  margin-bottom: var(--hxq-space-3);
}

.hxq-embed :deep(.assistant-composer) {
  padding: var(--hxq-space-1) var(--hxq-space-2) var(--hxq-space-3);
}

.hxq-embed :deep(.assistant-composer textarea) {
  max-height: 140px;
  min-height: 28px;
  font-size: 14.5px;
}

.hxq-embed__quiet-link {
  font-size: 11.5px;
  font-weight: 600;
  color: #a1a1aa;
  text-decoration: none;
  padding: 4px 2px;
  border-radius: 6px;
  transition: color 0.15s ease;
}
.hxq-embed__quiet-link:hover {
  color: #c43a12;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.hxq-embed__ctx-note {
  margin: 4px 0 0;
  padding-left: 2px;
  font-size: 11px;
  font-weight: 600;
  color: #a1a1aa;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}
.hxq-embed__ctx-note-x {
  border: 0;
  background: transparent;
  color: #c43a12;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}

.hxq-embed :deep(.xq-icon-btn--danger) {
  color: #b91c1c;
}
.hxq-embed :deep(.xq-icon-btn--danger:hover:not(:disabled)) {
  background: rgba(185, 28, 28, 0.08);
  color: #991b1b;
}

/* 过程/正文垂直节奏更紧 */
.hxq-embed :deep(.amv__body) {
  gap: 8px;
}
.hxq-embed :deep(.amv__process) {
  gap: 8px;
}
.hxq-embed :deep(.amv__think-label),
.hxq-embed :deep(.amv__think-time) {
  font-size: var(--hxq-process);
}
.hxq-embed :deep(.amv__tool-copy strong),
.hxq-embed :deep(.amv__tool-query) {
  font-size: var(--hxq-tool);
}
</style>
