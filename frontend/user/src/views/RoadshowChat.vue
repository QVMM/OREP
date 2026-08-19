<template>
  <div class="roadshow-chat">
    <!-- 顶部栏 -->
    <div class="chat-header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <span class="header-title">AI 复盘问答</span>
      <div class="header-actions">
        <el-button
          :type="voiceMode ? 'primary' : 'default'"
          circle
          size="small"
          @click="toggleVoiceMode"
          :title="voiceMode ? '关闭语音模式' : '开启语音模式'"
        >
          <el-icon><Microphone /></el-icon>
        </el-button>
        <el-button
          circle
          size="small"
          @click="showHelp = true"
          title="帮助"
        >
          <el-icon><QuestionFilled /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 聊天区域 -->
    <div class="chat-body" ref="chatBodyRef">
      <!-- 加载中 -->
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>正在加载路演数据...</p>
      </div>

      <div v-else-if="loadError" class="chat-error" role="status">
        <strong>暂时无法打开本场复盘问答</strong>
        <p>{{ loadError }}</p>
        <button type="button" @click="goBack">返回评分报告</button>
      </div>

      <!-- 消息列表 -->
      <div v-else class="messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message', msg.role]"
        >
          <!-- AI 头像 -->
          <div class="avatar" v-if="msg.role === 'assistant'">🤖</div>

          <!-- 用户头像 -->
          <div class="avatar user-avatar" v-else>🧑‍🎓</div>

          <!-- 消息内容 -->
          <div class="bubble">
            <div class="content" v-html="formatContent(msg.content)"></div>
            <!-- 加载动画 -->
            <div v-if="msg.streaming" class="typing-dots">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <!-- 追问建议 -->
        <div v-if="suggestions.length && !isResponding" class="suggestions">
          <div class="suggestions-label">💡 相关追问</div>
          <div class="suggestion-chips">
            <el-button
              v-for="(s, i) in suggestions"
              :key="i"
              size="small"
              plain
              @click="sendSuggestion(s)"
            >
              {{ s }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-footer">
      <div class="input-row">
        <el-input
          v-model="inputText"
          :placeholder="voiceMode ? '🎤 点击右侧按钮语音提问...' : '输入你的问题...'"
          @keyup.enter="handleSend"
          :disabled="isResponding || isRecording"
          size="large"
          class="chat-input"
        />
        <el-button
          v-if="voiceMode && !isRecording"
          type="danger"
          circle
          size="large"
          @click="startRecording"
          title="开始语音提问"
        >
          <el-icon size="20"><Microphone /></el-icon>
        </el-button>
        <el-button
          v-if="isRecording"
          type="danger"
          circle
          size="large"
          @click="stopRecording"
          class="recording-btn"
          title="停止录音"
        >
          <el-icon size="20"><VideoPause /></el-icon>
        </el-button>
        <el-button
          v-if="!isRecording"
          type="primary"
          circle
          size="large"
          @click="handleSend"
          :disabled="!inputText.trim() || isResponding"
          title="发送"
        >
          <el-icon size="20"><Promotion /></el-icon>
        </el-button>
      </div>

      <!-- 录音指示 -->
      <div v-if="isRecording" class="recording-indicator">
        <span class="recording-dot"></span>
        正在录音... {{ recordingTime }}s
      </div>
    </div>

    <!-- 帮助弹窗 -->
    <el-dialog v-model="showHelp" title="AI 复盘问答" width="360px">
      <div class="help-content">
        <h4>💡 怎么用？</h4>
        <p>AI 已经看过你的路演录像和评分结果，你可以自由提问，比如：</p>
        <ul>
          <li>"我哪里做得好 / 不好？"</li>
          <li>"为什么表达力分数这么低？"</li>
          <li>"技术先进性怎么改进？"</li>
          <li>"我 PPT 哪里需要优化？"</li>
          <li>"我们几个人的表情管理怎么样？"</li>
        </ul>
        <h4>🎤 语音模式</h4>
        <p>开启后可以用语音提问，AI 也会用语音朗读回答。</p>
        <h4>⚠️ 说明</h4>
        <p>AI 评委的建议基于你的路演数据和评分结果，仅供参考。</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Microphone, QuestionFilled, Loading,
  Promotion, VideoPause
} from '@element-plus/icons-vue'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'

const route = useRoute()
const router = useRouter()

// 状态
const loading = ref(true)
const loadError = ref('')
const sessionId = ref('')
const messages = ref([])
const suggestions = ref([])
const inputText = ref('')
const isResponding = ref(false)
const remainingTurns = ref(20)
const chatBodyRef = ref(null)
const showHelp = ref(false)
const voiceMode = ref(false)
const audioChunks = ref([])
const isRecording = ref(false)
const recordingTime = ref(0)

// Speech Recognition
let recognition = null
let recordingTimer = null

// 初始化
onMounted(async () => {
  const meetingId = route.params.meetingId || route.query.meetingId
  if (!meetingId) {
    ElMessage.error('缺少 meetingId')
    router.back()
    return
  }
  try {
    // 先尝试从数据库加载历史会话
    const latest = await request.get(`/api/ai-chat/latest/${meetingId}`, { silentError: true })
    const existingSession = latest?.session
    const existingMessages = latest?.messages || []

    if (existingSession && existingMessages.length > 0) {
      // 数据库有历史 → 直接加载
      sessionId.value = existingSession.sessionKey
      messages.value = existingMessages.map(m => ({
        role: m.role,
        content: m.content,
        streaming: false,
      }))
      // 同步历史到 Python 服务，让 LLM 有上下文
      try {
        const res = await request.post('/api/ai/chat/create', {
          meeting_id: meetingId,
          project_name: existingSession.projectName || '',
          track: route.query.track || '',
          team_size: parseInt(route.query.teamSize) || 4,
        }, { silentError: true })
        sessionId.value = res.session_id
      } catch { /* Python 会话创建失败不影响已有历史显示 */ }
    } else {
      // 无历史 → 新建会话
      const res = await request.post('/api/ai/chat/create', {
        meeting_id: meetingId,
        project_name: route.query.projectName || '',
        track: route.query.track || '',
        team_size: parseInt(route.query.teamSize) || 4,
      }, { silentError: true })
      sessionId.value = res.session_id
      suggestions.value = res.suggestions || []
      messages.value.push({
        role: 'assistant',
        content: res.welcome_message,
        streaming: false,
      })
    }

    loading.value = false
    await nextTick()
    scrollToBottom()
  } catch (err) {
    loadError.value = err.response?.data?.detail || err.response?.data?.message || '本场还没有可用于问答的评分数据。'
    loading.value = false
  }
})

onUnmounted(() => {
  if (recognition) recognition.abort()
  if (recordingTimer) clearInterval(recordingTimer)
})

// 发送消息
async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isResponding.value) return

  inputText.value = ''
  suggestions.value = []

  // 添加用户消息
  messages.value.push({ role: 'user', content: text, streaming: false })

  // 添加 AI 占位消息
  const aiMsgIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', streaming: true })
  isResponding.value = true

  await nextTick()
  scrollToBottom()

  try {
    // SSE 流式请求
    const response = await fetch(
      `${window.location.protocol}//${window.location.host}/api/ai/chat/${sessionId.value}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': getUserToken() ? `Bearer ${getUserToken()}` : '',
        },
        body: JSON.stringify({ message: text, stream: true }),
      }
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

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
            messages.value[aiMsgIdx].content += data.delta
            scrollToBottom()
          }
          if (data.audio_delta) {
            audioChunks.value.push(data.audio_delta)
          }
          if (data.done) {
            messages.value[aiMsgIdx].streaming = false
            suggestions.value = data.suggestions || []
            remainingTurns.value = 999
            // 播放语音（Omni 模型）
            if (data.audio_base64) {
              playAudioFromBase64(data.audio_base64)
            }
          }
        } catch { /* ignore parse errors */ }
      }
    }
  } catch (err) {
    messages.value[aiMsgIdx].content = '抱歉，遇到了问题，请稍后再试。'
    messages.value[aiMsgIdx].streaming = false
    ElMessage.error('发送失败: ' + err.message)
  } finally {
    isResponding.value = false
  }
}

// 发送建议追问
function sendSuggestion(text) {
  inputText.value = text
  handleSend()
}

// 语音
function toggleVoiceMode() {
  voiceMode.value = !voiceMode.value
  if (!voiceMode.value && isRecording.value) {
    stopRecording()
  }
}

function startRecording() {
  if (!('webkitSpeechRecognition' in window)) {
    ElMessage.warning('当前浏览器不支持语音识别')
    return
  }
  recognition = new window.webkitSpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = false

  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript
    inputText.value = text
    handleSend()
  }

  recognition.onerror = (e) => {
    ElMessage.error('语音识别失败: ' + e.error)
    stopRecording()
  }

  recognition.onend = () => {
    stopRecording()
  }

  isRecording.value = true
  recordingTime.value = 0
  recordingTimer = setInterval(() => {
    recordingTime.value++
  }, 1000)

  recognition.start()
}

function stopRecording() {
  isRecording.value = false
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  if (recognition) {
    recognition.stop()
    recognition = null
  }
}

// 语音朗读 AI 回复
function speakText(text) {
  if (!voiceMode.value || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'zh-CN'
  utterance.rate = 1.2
  window.speechSynthesis.speak(utterance)
}

// 格式化内容（支持 Markdown 粗体和换行）
function formatContent(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

function playAudioFromBase64(base64Data) {
  try {
    // DashScope Omni 返回的 base64 是 WAV 格式
    const byteChars = atob(base64Data)
    const byteArray = new Uint8Array(byteChars.length)
    for (let i = 0; i < byteChars.length; i++) {
      byteArray[i] = byteChars.charCodeAt(i)
    }
    const blob = new Blob([byteArray], { type: 'audio/wav' })
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audio.play().catch(() => {})
    audio.onended = () => URL.revokeObjectURL(url)
  } catch (e) {
    console.error('播放音频失败:', e)
  }
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.roadshow-chat {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  max-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  background: transparent;
}

/* 顶部 */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 58px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  flex-shrink: 0;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
}
.header-actions {
  display: flex;
  gap: 4px;
}

/* 聊天区 */
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.62);
}
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}
.loading-state .el-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

/* 消息 */
.messages {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.message {
  display: flex;
  gap: 8px;
  max-width: 85%;
}
.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.message.assistant {
  align-self: flex-start;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  background: #f0f0f0;
}
.user-avatar {
  background: #e8f4fd;
}
.bubble {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
}
.message.assistant .bubble {
  background: #fff;
  color: #333;
  border: 1px solid #eee;
  border-top-left-radius: 4px;
}
.message.user .bubble {
  background: var(--ds-orange, #f4511e);
  color: #fff;
  border-top-right-radius: 4px;
}

/* 打字动画 */
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ccc;
  animation: typing 1.4s infinite both;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

/* 追问建议 */
.suggestions {
  margin-top: 8px;
}
.suggestions-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}
.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.suggestion-chips .el-button {
  font-size: 13px;
}

/* 输入区 */
.chat-footer {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  flex-shrink: 0;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.chat-input {
  flex: 1;
}

/* 录音 */
.recording-btn {
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}
.recording-indicator {
  text-align: center;
  font-size: 13px;
  color: #f56c6c;
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.recording-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
  animation: blink 1s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 帮助 */
.help-content h4 {
  margin: 12px 0 6px;
}
.help-content ul {
  padding-left: 20px;
  margin: 4px 0;
}
.help-content li {
  margin: 4px 0;
  font-size: 14px;
}

.chat-error {
  height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
  color: var(--ds-muted, #6e6e73);
}

.chat-error strong {
  color: var(--ds-ink, #1d1d1f);
  font-size: 18px;
}

.chat-error p {
  margin: 0 0 6px;
}

.chat-error button {
  min-height: 40px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  background: var(--ds-orange, #f4511e);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
</style>
