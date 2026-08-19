<template>
  <Teleport to="body">
    <button v-if="collapsed" class="assistant-launcher" type="button" @click="$emit('toggle')" title="展开 AI 评分助手">
      <span class="launcher-icon">
        <el-icon><Expand /></el-icon>
      </span>
      <span class="launcher-copy">
        <b>AI 评分助手</b>
        <small>追问依据</small>
      </span>
    </button>

    <div v-else class="assistant-scrim" aria-hidden="true"></div>
    <section v-if="!collapsed" class="assistant-window" aria-label="AI 分析助手">
      <div class="assistant-header">
        <div>
          <span class="eyebrow">AI 分析助手</span>
          <strong>围绕本次评分追问</strong>
        </div>
        <button class="assistant-collapse" type="button" @click="$emit('toggle')" title="收起 AI 助手">
          <el-icon><Fold /></el-icon>
        </button>
      </div>

      <div class="assistant-body">
        <div ref="messageListRef" class="message-list" @scroll="handleMessageScroll">
          <div v-for="(msg, index) in messages" :key="index" class="message-row" :class="msg.role">
            <p v-html="formatContent(msg.content)"></p>
          </div>
          <div ref="bottomRef" class="message-bottom" aria-hidden="true"></div>
        </div>

        <footer class="assistant-footer">
          <div v-if="suggestions.length" class="suggestion-strip">
            <button v-for="item in suggestions" :key="item" type="button" @click="sendUserMessage(item)">
              {{ item }}
            </button>
          </div>

          <form class="input-row" @submit.prevent="sendUserMessage(inputText)">
            <el-input
              v-model="inputText"
              :placeholder="sessionId ? '追问评分依据或训练方案' : 'AI 助手暂不可用'"
              :disabled="!sessionId || isResponding"
            />
            <el-button native-type="submit" type="primary" :loading="isResponding" :disabled="!sessionId || !inputText.trim()">
              <el-icon><Promotion /></el-icon>
            </el-button>
          </form>
        </footer>
      </div>
    </section>
  </Teleport>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Expand, Fold, Promotion } from '@element-plus/icons-vue'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'

const props = defineProps({
  meetingId: {
    type: [String, Number],
    required: true
  },
  projectName: {
    type: String,
    default: ''
  },
  collapsed: {
    type: Boolean,
    default: true
  }
})

defineEmits(['toggle'])

const sessionId = ref('')
const messages = ref([])
const suggestions = ref([])
const inputText = ref('')
const isResponding = ref(false)
const messageListRef = ref(null)
const bottomRef = ref(null)
const shouldStickToBottom = ref(true)
let autoFollowFrame = 0
let abortController = null

function formatContent(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

function handleMessageScroll() {
  if (isResponding.value) return
  const el = messageListRef.value
  if (!el) return
  shouldStickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 96
}

function scrollMessagesToBottom(force = false) {
  if (!force && !shouldStickToBottom.value) return
  nextTick(() => {
    const el = messageListRef.value
    if (!el) return

    const pin = () => {
      el.scrollTop = el.scrollHeight - el.clientHeight
      shouldStickToBottom.value = true
    }

    pin()
    requestAnimationFrame(() => {
      pin()
      requestAnimationFrame(pin)
    })
  })
}

function startAutoFollow() {
  stopAutoFollow()
  shouldStickToBottom.value = true
  const tick = () => {
    scrollMessagesToBottom(true)
    autoFollowFrame = isResponding.value ? requestAnimationFrame(tick) : 0
  }
  autoFollowFrame = requestAnimationFrame(tick)
}

function stopAutoFollow() {
  if (autoFollowFrame) cancelAnimationFrame(autoFollowFrame)
  autoFollowFrame = 0
}

async function createChatSession() {
  if (!props.meetingId) return
  abortController?.abort()
  abortController = null
  sessionId.value = ''
  suggestions.value = []
  messages.value = [{ role: 'assistant', content: '正在载入本次评分上下文...', welcome: true }]

  try {
    const createRes = await request.post('/api/ai/chat/create', {
      meeting_id: props.meetingId,
      project_name: props.projectName || ''
    })
    sessionId.value = createRes.session_id
    suggestions.value = createRes.suggestions || [
      '为什么技能水平扣分最多？',
      '哪些画面证据影响了评分？',
      '下一次路演优先练什么？'
    ]
    messages.value = [{
      role: 'assistant',
      content: createRes.welcome_message || '评分结果已加载，可以追问评分依据、证据画面和训练方案。',
      welcome: true
    }]
  } catch {
    messages.value = [{ role: 'assistant', content: '评分结果已加载，AI 追问服务暂不可用。', welcome: true }]
  } finally {
    scrollMessagesToBottom(true)
  }
}

async function sendUserMessage(text) {
  if (!text?.trim() || isResponding.value || !sessionId.value) return
  const content = text.trim()
  inputText.value = ''
  suggestions.value = []
  messages.value = messages.value.filter(msg => !msg.welcome)
  messages.value.push({ role: 'user', content })
  const aiIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '正在分析...', streaming: true })
  isResponding.value = true
  startAutoFollow()
  scrollMessagesToBottom(true)

  abortController = new AbortController()

  try {
    const resp = await fetch(`${window.location.protocol}//${window.location.host}/api/ai/chat/${sessionId.value}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: getUserToken() ? `Bearer ${getUserToken()}` : ''
      },
      body: JSON.stringify({ message: content, stream: true }),
      signal: abortController.signal
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    messages.value[aiIdx].content = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.delta) {
            messages.value[aiIdx].content += data.delta
            scrollMessagesToBottom(true)
          }
          if (data.done) {
            messages.value[aiIdx].streaming = false
            suggestions.value = data.suggestions || []
            scrollMessagesToBottom(true)
          }
        } catch {}
      }
    }
  } catch (err) {
    if (err?.name !== 'AbortError') {
      messages.value[aiIdx].content = '追问服务暂时不可用，请稍后重试。'
    }
  } finally {
    messages.value[aiIdx].streaming = false
    isResponding.value = false
    stopAutoFollow()
    scrollMessagesToBottom(true)
  }
}

watch(() => props.meetingId, createChatSession)

watch(() => props.collapsed, collapsed => {
  if (!collapsed) scrollMessagesToBottom(true)
})

onMounted(() => {
  createChatSession()
})

onUnmounted(() => {
  abortController?.abort()
  stopAutoFollow()
})
</script>

<style scoped>
.assistant-launcher {
  position: fixed;
  right: 24px;
  bottom: 28px;
  z-index: 86;
  min-width: 154px;
  height: 58px;
  padding: 8px 14px 8px 9px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  border: 1px solid oklch(78% 0.13 166 / .5);
  border-radius: 999px;
  color: oklch(94% 0.014 190);
  background:
    radial-gradient(circle at 12% 20%, oklch(78% 0.16 166 / .32), transparent 36%),
    linear-gradient(135deg, oklch(23% 0.036 190), oklch(15% 0.022 220));
  box-shadow:
    0 18px 45px oklch(0% 0 0 / .38),
    0 0 0 5px oklch(72% 0.12 165 / .08);
  cursor: pointer;
  transition: transform .18s ease-out, border-color .18s ease-out, box-shadow .18s ease-out;
}

.assistant-launcher:hover {
  transform: translateY(-2px);
  border-color: oklch(82% 0.15 166 / .75);
  box-shadow:
    0 24px 58px oklch(0% 0 0 / .46),
    0 0 0 7px oklch(72% 0.12 165 / .12);
}

.launcher-icon {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: oklch(13% 0.018 190);
  background: oklch(79% 0.14 164);
  box-shadow: inset 0 -10px 16px oklch(48% 0.12 178 / .18);
}

.launcher-copy {
  display: grid;
  gap: 1px;
  text-align: left;
  line-height: 1.1;
}

.launcher-copy b {
  font-size: 14px;
  font-weight: 880;
  letter-spacing: 0;
}

.launcher-copy small {
  color: oklch(72% 0.04 205);
  font-size: 11px;
  font-weight: 760;
}

.assistant-scrim {
  position: fixed;
  inset: 90px 0 0 0;
  z-index: 84;
  pointer-events: none;
  background:
    linear-gradient(90deg, transparent 0 58%, oklch(5% 0.008 230 / .48) 78%, oklch(4% 0.006 230 / .72) 100%);
}

.assistant-window {
  position: fixed;
  top: 116px;
  right: 24px;
  bottom: 28px;
  z-index: 85;
  width: min(460px, calc(100vw - 48px));
  min-width: 320px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid oklch(84% 0.035 200 / .22);
  border-radius: 14px;
  background:
    radial-gradient(circle at 16% 0%, oklch(28% 0.052 178 / .35), transparent 42%),
    linear-gradient(180deg, oklch(13% 0.02 210 / .99), oklch(9% 0.014 222 / .99));
  box-shadow:
    0 36px 100px oklch(0% 0 0 / .58),
    0 0 0 1px oklch(100% 0 0 / .03) inset;
}

.assistant-header {
  flex: 0 0 auto;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px;
  gap: 12px;
  align-items: center;
  padding: 22px 22px 20px 24px;
  border-bottom: 1px solid oklch(84% 0.035 200 / .13);
  background: oklch(15% 0.018 215 / .72);
}

.eyebrow {
  display: block;
  margin-bottom: 8px;
  color: oklch(64% 0.018 220);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .28em;
  text-transform: uppercase;
}

.assistant-header strong {
  display: block;
  color: oklch(94% 0.012 210);
  font-size: 20px;
  line-height: 1.35;
}

.assistant-collapse {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid oklch(82% 0.04 205 / .18);
  border-radius: 10px;
  color: oklch(90% 0.018 205);
  background: oklch(21% 0.022 215 / .88);
  cursor: pointer;
  transition: background .16s ease-out, transform .16s ease-out;
}

.assistant-collapse:hover {
  transform: translateY(-1px);
  background: oklch(26% 0.03 205 / .96);
}

.assistant-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-list {
  height: 100%;
  min-height: 0;
  flex: 1 1 auto;
  display: block;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 20px 20px 16px;
  background: linear-gradient(180deg, oklch(10% 0.012 218 / .72), oklch(7% 0.01 225 / .84));
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  -webkit-overflow-scrolling: touch;
}

.message-row {
  display: block;
  margin-bottom: 10px;
}

.message-row p {
  margin: 0;
  padding: 15px 16px;
  border: 1px solid oklch(84% 0.035 200 / .1);
  border-radius: 10px;
  color: oklch(80% 0.018 220);
  background: oklch(18% 0.018 212 / .9);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.message-row.user p {
  margin-left: 34px;
  color: oklch(12% 0.012 180);
  border-color: oklch(80% 0.14 160 / .34);
  background: linear-gradient(135deg, oklch(78% 0.14 160), oklch(72% 0.12 188));
}

.message-bottom {
  display: block;
  width: 100%;
  min-height: 1px;
}

.assistant-footer {
  flex: 0 0 auto;
  min-height: 0;
  border-top: 1px solid oklch(84% 0.035 200 / .13);
  background:
    linear-gradient(180deg, oklch(12% 0.016 218 / .98), oklch(9% 0.012 224 / .98));
}

.suggestion-strip {
  display: flex;
  gap: 8px;
  padding: 12px 18px 14px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: oklch(67% 0.1 170 / .52) oklch(92% 0.012 210 / .08);
}

.suggestion-strip::-webkit-scrollbar {
  display: block;
  height: 6px;
}

.suggestion-strip::-webkit-scrollbar-track {
  border-radius: 999px;
  background: oklch(92% 0.012 210 / .07);
}

.suggestion-strip::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: linear-gradient(90deg, oklch(70% 0.12 165 / .66), oklch(68% 0.1 205 / .58));
}

.suggestion-strip::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(90deg, oklch(76% 0.14 160 / .82), oklch(72% 0.12 205 / .75));
}

.suggestion-strip button {
  flex: 0 0 auto;
  max-width: 210px;
  min-height: 38px;
  padding: 8px 14px;
  border: 1px solid oklch(76% 0.14 160 / .24);
  border-radius: 10px;
  color: oklch(83% 0.024 200);
  background:
    linear-gradient(180deg, oklch(19% 0.026 190 / .95), oklch(14% 0.02 215 / .95));
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px oklch(100% 0 0 / .02);
  transition: color .16s ease-out, border-color .16s ease-out, background .16s ease-out, transform .16s ease-out;
}

.suggestion-strip button:hover {
  transform: translateY(-1px);
  color: oklch(94% 0.014 190);
  border-color: oklch(78% 0.14 160 / .56);
  background:
    linear-gradient(180deg, oklch(26% 0.055 174 / .95), oklch(17% 0.026 210 / .95));
}

.input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 48px;
  gap: 12px;
  padding: 10px 18px 18px;
  align-items: center;
}

.input-row :deep(.el-input__wrapper) {
  min-height: 46px;
  padding: 0 16px;
  border: 1px solid oklch(78% 0.045 205 / .2);
  border-radius: 12px;
  background:
    radial-gradient(circle at 10% 0%, oklch(26% 0.045 178 / .26), transparent 34%),
    oklch(14% 0.017 218 / .98);
  box-shadow:
    0 12px 30px oklch(0% 0 0 / .16) inset,
    0 0 0 1px oklch(100% 0 0 / .02);
  transition: border-color .16s ease-out, box-shadow .16s ease-out, background .16s ease-out;
}

.input-row :deep(.el-input__wrapper.is-focus) {
  border-color: oklch(78% 0.14 160 / .72);
  background:
    radial-gradient(circle at 10% 0%, oklch(34% 0.08 166 / .32), transparent 38%),
    oklch(16% 0.02 214 / .98);
  box-shadow:
    0 0 0 3px oklch(76% 0.14 160 / .13),
    0 12px 30px oklch(0% 0 0 / .12) inset;
}

.input-row :deep(.el-input__inner) {
  color: oklch(92% 0.014 205);
  font-size: 15px;
  font-weight: 620;
}

.input-row :deep(.el-input__inner::placeholder) {
  color: oklch(64% 0.022 220);
}

.input-row :deep(.el-button) {
  width: 48px;
  height: 46px;
  border: 0;
  border-radius: 14px;
  color: oklch(13% 0.018 180);
  background:
    radial-gradient(circle at 30% 22%, oklch(96% 0.05 170 / .7), transparent 30%),
    linear-gradient(135deg, oklch(80% 0.14 160), oklch(74% 0.13 190));
  box-shadow:
    0 14px 32px oklch(72% 0.13 170 / .22),
    inset 0 -10px 16px oklch(40% 0.1 180 / .16);
  transition: transform .16s ease-out, box-shadow .16s ease-out, filter .16s ease-out;
}

.input-row :deep(.el-button:hover),
.input-row :deep(.el-button:focus) {
  transform: translateY(-1px);
  color: oklch(11% 0.018 180);
  filter: saturate(1.08);
  box-shadow:
    0 18px 40px oklch(72% 0.13 170 / .3),
    inset 0 -10px 16px oklch(40% 0.1 180 / .14);
}

.input-row :deep(.el-button.is-disabled) {
  color: oklch(62% 0.015 220);
  background: oklch(22% 0.018 218);
  box-shadow: none;
  opacity: .68;
  transform: none;
}

.input-row :deep(.el-button .el-icon) {
  font-size: 18px;
}

@media (max-width: 980px) {
  .assistant-scrim {
    inset: 76px 0 0 0;
    background: oklch(4% 0.006 230 / .54);
  }

  .assistant-window {
    top: 88px;
    right: 12px;
    bottom: 12px;
    width: min(420px, calc(100vw - 24px));
    min-width: 0;
    border-radius: 12px;
  }

  .assistant-launcher {
    right: 14px;
    bottom: 18px;
    min-width: 142px;
  }
}

@media (max-width: 560px) {
  .assistant-window {
    inset: 78px 10px 10px 10px;
    width: auto;
  }

  .assistant-launcher {
    min-width: 58px;
    padding-right: 9px;
  }

  .launcher-copy {
    display: none;
  }
}
</style>
