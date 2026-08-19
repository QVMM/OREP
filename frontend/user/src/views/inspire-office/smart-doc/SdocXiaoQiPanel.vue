<template>
  <aside class="assistant-pane assistant-pane--chat sdoc-xq" aria-label="小启AI">
    <header class="assistant-chat-header">
      <span class="title-fallback" style="display:inline-flex;align-items:center;gap:8px">
        <XiaoQiMark :size="22" :hoverable="false" />
        小启AI
      </span>
      <div class="assistant-header-actions">
        <button type="button" class="xq-icon-btn" title="关闭" aria-label="关闭" @click="$emit('close')">
          <XqIcon name="close" />
        </button>
      </div>
    </header>

    <div v-if="ctx.selection && messages.length" class="sdoc-xq__cite">
      <span class="sdoc-xq__cite-mark">↗</span>
      <p>{{ excerpt }}</p>
    </div>

    <div ref="scrollRef" class="assistant-messages">
      <div v-if="!messages.length" class="assistant-welcome" style="padding-top: 12px">
        <p style="margin: 0 0 12px; color: var(--ds-muted, #6b7280); font-size: 13px; line-height: 1.55">
          问这段怎么改，或点一颗快捷说法。
        </p>
        <div class="assistant-chips">
          <button
            v-for="chip in chips"
            :key="chip"
            type="button"
            class="assistant-chip"
            @click="$emit('send', chip)"
          >{{ chip }}</button>
        </div>
      </div>
      <div v-else class="assistant-thread">
        <div
          v-for="(msg, index) in messages"
          :key="msg._localId || index"
          class="assistant-msg-wrap"
        >
          <AssistantMessageView
            :msg="msg"
            compact
            hide-plan-draft
            :show-toolbar="msg.role === 'assistant' && msg.status !== 'streaming'"
          />
          <div
            v-if="msg.role === 'assistant' && msg.actionProposals?.length"
            class="assistant-action-cards"
            style="padding: 8px 0 0"
          >
            <div
              v-for="ap in msg.actionProposals"
              :key="ap.proposalId"
              class="assistant-action-card"
              :class="`is-${ap.status || 'pending'}`"
            >
              <div class="assistant-action-card__head">
                <strong>{{ ap.title || '待确认操作' }}</strong>
                <span class="assistant-action-card__badge">{{ actionStatusLabel(ap.status) }}</span>
              </div>
              <p class="assistant-action-card__summary">{{ ap.summary || '确认后才会写入这一格。' }}</p>
              <div v-if="firstPatch(ap)" class="assistant-action-card__diff">
                <p><strong>原文</strong>{{ firstPatch(ap).before }}</p>
                <p><strong>建议</strong>{{ firstPatch(ap).after }}</p>
                <p v-if="firstPatch(ap).reason"><strong>原因</strong>{{ firstPatch(ap).reason }}</p>
              </div>
              <div v-if="ap.status === 'pending' || !ap.status" class="assistant-action-card__actions">
                <button
                  type="button"
                  class="xq-text-btn assistant-action-card__confirm"
                  :disabled="busy || ap._busy"
                  @click="$emit('confirm-proposal', msg, ap)"
                >确认写入</button>
                <button
                  type="button"
                  class="xq-text-btn"
                  :disabled="busy || ap._busy"
                  @click="$emit('reject-proposal', msg, ap)"
                >不要</button>
              </div>
              <p v-if="ap.resultMessage" class="assistant-action-card__result">{{ ap.resultMessage }}</p>
            </div>
          </div>
        </div>
      </div>
      <p v-if="error" class="amv__error" style="padding: 0 16px">{{ error }}</p>
    </div>

    <p v-if="status === 'streaming'" class="sdoc-xq__wait">
      正在对照评分、项目和整篇讲稿想这一段，过程会写在上面。
    </p>

    <div v-if="showApplyCard" class="assistant-action-cards" style="padding: 0 16px 8px">
      <div class="assistant-action-card" :class="applied ? 'is-confirmed' : 'is-pending'">
        <div class="assistant-action-card__head">
          <strong>{{ applied ? (status === 'done' ? '已确定修改' : '已写入原文') : '确认写入这段' }}</strong>
          <span class="assistant-action-card__badge">{{ applied ? (status === 'done' ? '已确定' : '已写入') : '待确认' }}</span>
        </div>
        <div class="assistant-action-card__diff">
          <p>
            <strong>原文</strong>
            {{ preview.before || ctx.selection }}
          </p>
          <p>
            <strong>建议稿</strong>
            {{ preview.after }}
          </p>
        </div>
        <p v-if="applied && status !== 'done'" class="assistant-action-card__summary">文档里那一段已改，可点确定修改或撤回。</p>
        <p v-else-if="preview.reason" class="assistant-action-card__summary">{{ preview.reason }}</p>
        <p v-else-if="!applied" class="assistant-action-card__summary">只改你选中的原文，其它句子不动。</p>
        <div v-if="!applied" class="assistant-action-card__actions">
          <button
            type="button"
            class="xq-text-btn assistant-action-card__confirm"
            :disabled="busy"
            @click="$emit('apply')"
          >{{ status === 'writing' ? '写入中…' : '确认' }}</button>
          <button
            type="button"
            class="xq-text-btn"
            :disabled="busy"
            @click="$emit('reject')"
          >不要</button>
        </div>
      </div>
    </div>

    <footer class="assistant-composer">
      <div class="assistant-composer__shell">
        <div v-if="ctx.selection" class="assistant-composer__cite">
          <span>↗ {{ excerpt }}</span>
        </div>
        <div class="assistant-composer__box">
          <textarea
            ref="boxRef"
            :value="draft"
            rows="1"
            placeholder="询问任何问题，或选择技能"
            :disabled="busy && status === 'streaming'"
            @input="$emit('update:draft', $event.target.value)"
            @keydown.enter.exact.prevent="onEnter"
          />
          <div class="assistant-composer__actions">
            <div class="composer-tools" />
            <button
              v-if="status === 'streaming'"
              type="button"
              class="xq-icon-btn xq-icon-btn--danger"
              title="停止生成"
              aria-label="停止生成"
              @click="$emit('stop')"
            >
              <XqIcon name="stop" />
            </button>
            <button
              v-else
              type="button"
              class="xq-send-btn"
              :disabled="!String(draft || '').trim() && !showApplyCard"
              title="发送"
              aria-label="发送"
              @click="onEnter"
            >
              <XqIcon name="send" size="md" />
            </button>
          </div>
        </div>
        <p class="composer-hint">Enter 发送 · Shift+Enter 换行</p>
      </div>
    </footer>
  </aside>
</template>

<script setup>
import { computed, nextTick, provide, ref, watch } from 'vue'
import '../../../styles/assistant.css'
import XiaoQiMark from '../../../components/brand/XiaoQiMark.vue'
import XqIcon from '../../../components/assistant/XqIcon.vue'
import AssistantMessageView from '../../../modules/assistant-core/AssistantMessageView.vue'

const props = defineProps({
  ctx: { type: Object, required: true },
  messages: { type: Array, default: () => [] },
  draft: { type: String, default: '' },
  busy: { type: Boolean, default: false },
  status: { type: String, default: 'idle' },
  error: { type: String, default: '' },
  preview: { type: Object, default: () => ({ after: '', reason: '' }) },
})

const emit = defineEmits(['close', 'send', 'apply', 'reject', 'stop', 'update:draft', 'confirm-proposal', 'reject-proposal'])
const scrollRef = ref(null)
const boxRef = ref(null)
const chips = ['按最新评分改讲稿', '更口语', '再短一点', '补具体', '去掉翻页提示']

function firstPatch(ap) {
  const patches = ap?.args?.patches
  return Array.isArray(patches) && patches[0] ? patches[0] : null
}

function actionStatusLabel(status) {
  return ({
    pending: '待确认',
    confirmed: '已执行',
    rejected: '已取消',
    expired: '已过期',
    failed: '失败',
  })[status] || '待确认'
}

const excerpt = computed(() => {
  const raw = String(props.ctx.selection || '').replace(/\s+/g, ' ').trim()
  return raw.length > 72 ? `${raw.slice(0, 70)}…` : raw
})

const applied = computed(() => props.status === 'preview' || props.status === 'done')
const showApplyCard = computed(() => {
  if (props.status === 'streaming') return false
  return Boolean(String(props.preview?.after || '').trim()) && props.status !== 'idle'
})

function scrollToBottom() {
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

provide('assistantScrollToBottom', scrollToBottom)

function onEnter() {
  emit('send', String(props.draft || '').trim())
}

watch(
  () => props.messages.map((m) => `${m.contentText || m.text}|${m.status}`).join('\n'),
  async () => {
    await nextTick()
    scrollToBottom()
  },
)
</script>
