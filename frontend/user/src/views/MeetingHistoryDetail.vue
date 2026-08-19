<template>
  <div class="detail-page" v-loading="loading">
    <div v-if="detail" class="detail-shell">
      <header class="detail-toolbar">
        <el-button text @click="router.back()" class="back-btn" aria-label="返回参与记录">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回记录</span>
        </el-button>
        <div class="detail-route">
          <span>在线路演</span>
          <i></i>
          <strong>参与记录详情</strong>
        </div>
      </header>

      <section class="recap-layout">
        <main class="recap-main">
          <section class="record-hero">
            <div class="hero-main">
              <span class="hero-kicker">路演复盘</span>
              <h1>{{ detail.title }}</h1>
              <p>系统已整理本次参与记录、聊天证据、评分结果和待复盘问题，可继续进入 AI 评分报告或同步到团队任务。</p>
              <div class="hero-meta">
                <span class="status-pill" :class="`status-${detail.status || 'UNKNOWN'}`">
                  {{ getStatusText(detail.status) }}
                </span>
                <span>{{ formatDateTime(detail.startTime) }}</span>
                <span v-if="detail.endTime">结束 {{ formatTime(detail.endTime) }}</span>
              </div>
            </div>

            <aside class="hero-ai-card">
              <span>AI 复盘状态</span>
              <strong>{{ detail.totalScore != null ? `${detail.totalScore}` : '待生成' }}</strong>
              <small>{{ detail.totalScore != null ? `满分 ${maxScoreText}` : '等待评分结果' }}</small>
              <button type="button" @click="goAiScore">查看 AI 评分报告</button>
            </aside>
          </section>

          <section class="summary-grid" aria-label="会议数据概览">
            <article class="summary-card">
              <div class="summary-icon summary-icon-time"><el-icon><Timer /></el-icon></div>
              <div>
                <span>参与时长</span>
                <strong>{{ formatDuration(detail.durationSeconds) }}</strong>
                <small>会议时长</small>
              </div>
            </article>
            <article class="summary-card">
              <div class="summary-icon summary-icon-chat"><el-icon><ChatDotRound /></el-icon></div>
              <div>
                <span>聊天消息</span>
                <strong>{{ detail.chatMessages?.length || 0 }}</strong>
                <small>沟通记录</small>
              </div>
            </article>
            <article class="summary-card">
              <div class="summary-icon summary-icon-score"><el-icon><Histogram /></el-icon></div>
              <div>
                <span>评分结果</span>
                <strong>{{ detail.totalScore != null ? detail.totalScore : '--' }}</strong>
                <small>评分数据</small>
              </div>
            </article>
            <article class="summary-card">
              <div class="summary-icon summary-icon-issue"><el-icon><Warning /></el-icon></div>
              <div>
                <span>存在问题</span>
                <strong>{{ detail.issues?.length || 0 }}</strong>
                <small>待复盘项</small>
              </div>
            </article>
          </section>

          <section class="action-band">
            <div class="action-mark"><el-icon><Star /></el-icon></div>
            <div>
              <span>评分闭环</span>
              <strong>把会议证据转成可执行的评分报告和团队任务</strong>
              <p>查看 AI 评分报告后，可将扣分项转成团队工作项；若本次会议没有完整评分，也可以上传完整路演视频重新分析。</p>
            </div>
            <div class="action-buttons">
              <button type="button" class="primary-action" @click="goAiScore">查看 AI 评分报告</button>
              <button type="button" @click="goTeamScoreItems">团队扣分项</button>
              <button type="button" @click="goVideoScoreUpload">上传视频评分</button>
            </div>
          </section>

          <section class="detail-workspace">
            <div class="workspace-main">
          <div class="content-tabs" role="tablist" aria-label="详情内容切换">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              type="button"
              class="ctab"
              :class="{ active: activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              <span class="ctab-en">{{ tab.hint }}</span>
              <strong>{{ tab.label }}</strong>
              <span class="ctab-badge" v-if="tab.count > 0">{{ tab.count }}</span>
            </button>
          </div>

          <div class="detail-body">
            <div v-show="activeTab === 'chat'" class="tab-panel">
              <div class="section-head">
                <span>沟通记录</span>
                <strong>聊天记录</strong>
              </div>
              <div v-if="!detail.chatMessages?.length" class="panel-empty">
                <span class="empty-mark">空</span>
                <strong>暂无聊天记录</strong>
                <p>会议期间没有产生可回放的文本消息。</p>
              </div>
              <div v-else class="chat-list">
                <div
                  v-for="msg in detail.chatMessages"
                  :key="msg.id"
                  class="chat-item"
                >
                  <div class="chat-avatar">{{ (msg.senderName || 'U').slice(0, 1) }}</div>
                  <div class="chat-card">
                    <div class="chat-head">
                      <span class="chat-sender">{{ msg.senderName }}</span>
                      <span class="chat-time">{{ formatTime(msg.createdAt) }}</span>
                    </div>
                    <div v-if="isAttachmentMessage(msg)" class="chat-attachment" :class="`attachment-${getAttachmentKind(msg)}`">
                      <div class="attachment-mark">{{ getAttachmentLabel(msg) }}</div>
                      <div class="attachment-main">
                        <strong>{{ getAttachmentName(msg) }}</strong>
                        <small>{{ getAttachmentHint(msg) }}</small>
                      </div>
                      <button type="button" @click="openChatAttachment(msg)">
                        {{ getAttachmentAction(msg) }}
                      </button>
                    </div>
                    <div v-else class="chat-content">{{ msg.content }}</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-show="activeTab === 'score'" class="tab-panel">
              <div class="section-head">
                <span>评分明细</span>
                <strong>评分结果</strong>
              </div>
              <div v-if="!detail.scoreDetails?.length" class="panel-empty">
                <span class="empty-mark">分</span>
                <strong>暂无评分数据</strong>
                <p>评分提交后，这里会展示各项得分和评语。</p>
              </div>
              <div v-else>
                <div v-if="detail.totalScore != null" class="total-score-bar">
                  <div>
                    <span class="ts-label">综合评分</span>
                    <strong>总分</strong>
                  </div>
                  <span class="ts-value">{{ detail.totalScore }}</span>
                </div>
                <div class="score-groups">
                  <div
                    v-for="(items, category) in groupedScores"
                    :key="category"
                    class="score-group"
                  >
                    <div class="sg-title">{{ category }}</div>
                    <div
                      v-for="item in items"
                      :key="item.itemName"
                      class="score-row"
                    >
                      <div class="score-row-top">
                        <span class="sr-name">{{ item.itemName }}</span>
                        <span class="sr-score">
                          <span class="sr-value">{{ item.score }}</span>
                          <span class="sr-max">/ {{ item.maxScore }}</span>
                        </span>
                      </div>
                      <div class="sr-meter">
                        <span :style="{ width: getScorePercent(item) + '%' }"></span>
                      </div>
                      <div class="sr-comment" v-if="item.comment">{{ item.comment }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-show="activeTab === 'issues'" class="tab-panel">
              <div class="section-head section-head-action">
                <div>
                  <span>问题清单</span>
                  <strong>存在问题</strong>
                </div>
                <el-button v-if="detail.issues?.length" type="primary" plain round size="small" class="export-btn" @click="exportIssueReport">
                  <el-icon><Download /></el-icon>
                  导出问题报告
                </el-button>
              </div>
              <div v-if="!detail.issues?.length" class="panel-empty">
                <span class="empty-mark">清</span>
                <strong>暂无问题记录</strong>
                <p>当前路演记录没有关联待复盘问题。</p>
              </div>
              <div v-else class="issue-list">
                <article
                  v-for="issue in detail.issues"
                  :key="issue.id"
                  class="issue-card"
                  :class="{ resolved: issue.status === 1 }"
                >
                  <div class="issue-header">
                    <span class="issue-status">{{ issue.status === 1 ? '已解决' : '待解决' }}</span>
                    <span class="issue-category" v-if="issue.category">{{ issue.category }}</span>
                  </div>
                  <div class="issue-desc">{{ issue.description }}</div>
                  <div class="issue-time">{{ formatDateTime(issue.createdAt) }}</div>
                </article>
              </div>
            </div>
          </div>
            </div>
          </section>
        </main>

        <aside class="workspace-side">
          <section class="side-card ai-card">
            <div class="side-card-head">
              <span class="side-icon"><el-icon><Tickets /></el-icon></span>
              <span>AI 评分报告</span>
            </div>
            <strong>评分报告</strong>
            <p>基于本次会议证据生成 AI 分析，继续查看分数、扣分项、建议和可转任务。</p>
            <button type="button" @click="goAiScore">进入 AI 报告</button>
          </section>

          <section class="side-card">
            <div class="side-card-head">
              <span class="side-icon"><el-icon><Camera /></el-icon></span>
              <span>记录快照</span>
            </div>
            <div class="snapshot-list">
              <div>
                <small>开始时间</small>
                <strong>{{ formatDateTime(detail.startTime) }}</strong>
              </div>
              <div>
                <small>结束时间</small>
                <strong>{{ detail.endTime ? formatTime(detail.endTime) : '未结束' }}</strong>
              </div>
              <div>
                <small>总分上限</small>
                <strong>{{ maxScoreText }}</strong>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </div>

    <div v-else-if="!loading" class="detail-empty-state">
      <strong>未找到参与记录</strong>
      <p>请返回在线路演参与记录列表重新选择。</p>
      <button type="button" @click="router.back()">返回记录</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  Camera,
  ChatDotRound,
  Download,
  Histogram,
  Star,
  Tickets,
  Timer,
  Warning
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const detail = ref(null)
const activeTab = ref('chat')

const tabs = computed(() => [
  { key: 'chat', hint: '沟通', label: '聊天记录', count: detail.value?.chatMessages?.length || 0 },
  { key: 'score', hint: '评分', label: '评分结果', count: detail.value?.scoreDetails?.length || 0 },
  { key: 'issues', hint: '问题', label: '存在问题', count: detail.value?.issues?.length || 0 }
])

const maxScoreText = computed(() => {
  if (!detail.value?.scoreDetails?.length) return '100'
  const total = detail.value.scoreDetails.reduce((sum, item) => sum + (Number(item.maxScore) || 0), 0)
  return total || '100'
})

// 按分类分组评分
const groupedScores = computed(() => {
  if (!detail.value?.scoreDetails) return {}
  const groups = {}
  for (const item of detail.value.scoreDetails) {
    const cat = item.category || '其他'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(item)
  }
  return groups
})

onMounted(async () => {
  try {
    const meetingId = route.params.id
    const res = await request.get(`/api/meeting/${meetingId}/detail`)
    detail.value = res.data || res
    // 默认选中第一个有内容的 tab
    if (detail.value?.chatMessages?.length) activeTab.value = 'chat'
    else if (detail.value?.scoreDetails?.length) activeTab.value = 'score'
    else if (detail.value?.issues?.length) activeTab.value = 'issues'
  } catch (e) {
    console.error('获取详情失败:', e)
  } finally {
    loading.value = false
  }
})

function goAiScore() {
  const id = detail.value?.meetingId || route.params.id
  router.push({
    name: 'AiScoreResult',
    params: { meetingId: id }
  })
}

function goTeamScoreItems() {
  router.push({ path: '/project-team', query: { workView: 'score' } })
}

function goVideoScoreUpload() {
  router.push('/ai-score-upload')
}

const getStatusType = (status) => {
  const map = { CREATED: 'info', RUNNING: 'success', ENDED: 'danger' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { CREATED: '待开始', RUNNING: '进行中', ENDED: '已结束' }
  return map[status] || status
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatDuration = (seconds) => {
  if (!seconds) return '--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

const getScorePercent = (item) => {
  const score = Number(item.score) || 0
  const max = Number(item.maxScore) || 100
  if (!max) return 0
  return Math.max(0, Math.min(100, (score / max) * 100))
}

function isAttachmentMessage(msg) {
  const type = msg?.messageType || msg?.type
  return type === 'image' || type === 'file' || looksLikeUploadPath(msg?.content)
}

function looksLikeUploadPath(value) {
  return typeof value === 'string' && /^\/?uploads\//.test(value.trim())
}

function getAttachmentName(msg) {
  const raw = msg?.fileName || msg?.name || extractNameFromPath(msg?.content)
  return sanitizeFileName(raw) || '会议附件'
}

function extractNameFromPath(value) {
  if (typeof value !== 'string') return ''
  const clean = value.split('?')[0].split('#')[0]
  const last = clean.split('/').filter(Boolean).pop() || ''
  try {
    return decodeURIComponent(last)
  } catch {
    return last
  }
}

function sanitizeFileName(value) {
  return String(value || '')
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80)
}

function getAttachmentKind(msg) {
  const type = msg?.messageType || msg?.type
  const name = getAttachmentName(msg).toLowerCase()
  if (type === 'image' || /\.(png|jpe?g|gif|webp|bmp|svg)$/.test(name)) return 'image'
  if (/\.(zip|rar|7z|tar|gz)$/.test(name)) return 'archive'
  if (/\.(docx?|pptx?|xlsx?|pdf|txt|md)$/.test(name)) return 'document'
  return 'file'
}

function getAttachmentLabel(msg) {
  const map = {
    image: '图',
    document: '文',
    archive: '压',
    file: '附'
  }
  return map[getAttachmentKind(msg)] || '附'
}

function getAttachmentHint(msg) {
  const map = {
    image: '图片附件，点击后通过权限校验预览',
    document: '文件附件，点击后通过权限校验下载',
    archive: '压缩包附件，点击后通过权限校验下载',
    file: '会议附件，点击后通过权限校验下载'
  }
  return map[getAttachmentKind(msg)] || map.file
}

function getAttachmentAction(msg) {
  return getAttachmentKind(msg) === 'image' ? '查看' : '下载'
}

async function openChatAttachment(msg) {
  if (!msg?.id) {
    ElMessage.warning('缺少附件记录编号，无法安全打开')
    return
  }
  const meetingId = detail.value?.meetingId || route.params.id
  const token = getUserToken()
  try {
    const res = await fetch(`/api/meeting/${meetingId}/chat-attachment/${msg.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('附件读取失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const name = getAttachmentName(msg)
    if (getAttachmentKind(msg) === 'image') {
      window.open(url, '_blank', 'noopener,noreferrer')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
      return
    }
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('打开聊天附件失败:', e)
    ElMessage.error('附件打开失败，请确认是否仍有访问权限')
  }
}

async function exportIssueReport() {
  const meetingId = route.params.id
  const token = getUserToken()
  try {
    const res = await fetch(`/api/issue/export-pdf?meetingId=${meetingId}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${detail.value.title || '会议'}_问题报告.pdf`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('导出问题报告失败:', e)
  }
}
</script>

<style scoped>
.detail-page {
  position: relative;
  min-height: 100vh;
  padding: 40px 36px 72px;
  overflow: hidden auto;
  background:
    radial-gradient(circle at 78% 10%, rgba(71, 255, 172, .12), transparent 24%),
    radial-gradient(circle at 92% 48%, rgba(71, 255, 172, .08), transparent 30%),
    radial-gradient(circle at 20% 12%, rgba(255, 255, 255, .055), transparent 24%),
    linear-gradient(rgba(240, 246, 255, .032) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 246, 255, .032) 1px, transparent 1px),
    #030509;
  background-size: auto, auto, auto, 88px 88px, 88px 88px, auto;
  color: #f0f1fa;
}

.detail-page::before,
.detail-page::after {
  content: "";
  position: fixed;
  pointer-events: none;
  z-index: 0;
}

.detail-page::before {
  inset: 0;
  background:
    linear-gradient(90deg, rgba(3, 5, 9, .92), rgba(3, 5, 9, .28) 36%, rgba(3, 5, 9, .78)),
    radial-gradient(circle at 72% 18%, rgba(49, 255, 157, .13), transparent 30%);
}

.detail-page::after {
  right: -260px;
  top: 190px;
  width: 640px;
  height: 640px;
  border: 1px solid rgba(174, 255, 211, .08);
  border-radius: 50%;
  box-shadow: inset 0 0 90px rgba(71, 255, 172, .025);
}

.detail-orbit {
  position: absolute;
  pointer-events: none;
  border: 1px solid rgba(240, 241, 250, .08);
  border-radius: 50%;
  opacity: .6;
}

.detail-orbit-one {
  right: -220px;
  top: 170px;
  width: 560px;
  height: 560px;
}

.detail-orbit-two {
  left: -260px;
  bottom: -330px;
  width: 620px;
  height: 620px;
}

.detail-shell {
  position: relative;
  z-index: 1;
  width: min(1440px, 100%);
  margin: 0 auto;
}

.detail-header {
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
}

.back-btn {
  justify-self: start;
  height: 42px;
  padding: 0 18px !important;
  border: 1px solid rgba(240, 246, 255, .13);
  border-radius: 999px;
  background: rgba(240, 246, 255, .06);
  color: rgba(240, 246, 255, .72);
  font-size: 14px;
  font-weight: 760;
  backdrop-filter: blur(14px);
  transition: background .18s ease, color .18s ease, transform .18s ease;
}

.back-btn:hover {
  background: rgba(122, 255, 180, .1);
  color: #f4fff8;
  transform: translateX(-2px);
}

.hero-panel {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  gap: 36px;
  align-items: stretch;
  min-height: 268px;
  padding: 48px 54px;
  border: 1px solid rgba(240, 246, 255, .12);
  background:
    linear-gradient(90deg, rgba(255, 255, 255, .07), transparent 44%),
    radial-gradient(circle at 80% 34%, rgba(122, 255, 180, .16), transparent 36%),
    rgba(13, 15, 21, .82);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .06),
    0 28px 90px rgba(0, 0, 0, .36);
  overflow: hidden;
}

.hero-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  border: 1px solid rgba(255, 255, 255, .035);
  pointer-events: none;
}

.hero-panel::after {
  content: "";
  position: absolute;
  right: 210px;
  top: -120px;
  width: 380px;
  height: 380px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(111, 255, 184, .14), transparent 62%);
  filter: blur(2px);
  pointer-events: none;
}

.hero-copy {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.mission-kicker,
.ov-kicker,
.ctab-en,
.section-head span,
.ts-label {
  color: rgba(240, 241, 250, .42);
  font-size: 11px;
  font-weight: 820;
  letter-spacing: .18em;
}

.hero-copy h1 {
  margin: 12px 0 18px;
  color: #f4f6ff;
  font-size: clamp(48px, 5.2vw, 86px);
  line-height: .98;
  font-weight: 900;
  letter-spacing: 0;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-text {
  font-size: 13px;
  color: rgba(240, 241, 250, .54);
}

.status-pill {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border: 1px solid rgba(122, 255, 180, .26);
  border-radius: 999px;
  color: #7affb4;
  background: rgba(122, 255, 180, .075);
  font-size: 12px;
  font-weight: 820;
}

.status-ENDED {
  color: rgba(240, 241, 250, .68);
  background: rgba(240, 241, 250, .06);
  border-color: rgba(240, 241, 250, .16);
}

.status-CREATED {
  color: #ffd38a;
  background: rgba(255, 211, 138, .08);
  border-color: rgba(255, 211, 138, .22);
}

.hero-status {
  position: relative;
  z-index: 1;
  min-width: 256px;
  padding: 28px;
  display: grid;
  align-content: center;
  justify-items: start;
  border: 1px solid rgba(122, 255, 180, .2);
  background:
    radial-gradient(circle at 50% 0%, rgba(122, 255, 180, .16), transparent 58%),
    rgba(6, 7, 10, .62);
  box-shadow: inset 0 1px 0 rgba(122, 255, 180, .06);
}

.hero-status-label {
  color: rgba(122, 255, 180, .72);
  font-size: 11px;
  font-weight: 820;
  letter-spacing: .18em;
}

.hero-status strong {
  margin-top: 14px;
  color: #7affb4;
  font-size: 54px;
  line-height: 1;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.hero-status small {
  margin-top: 6px;
  color: rgba(240, 241, 250, .52);
  font-size: 13px;
  font-weight: 700;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) minmax(220px, .9fr);
  border: 1px solid rgba(240, 246, 255, .11);
  border-top: 0;
  background: rgba(7, 9, 13, .78);
  margin-bottom: 22px;
}

.ov-card {
  min-height: 150px;
  padding: 28px 22px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border: 0;
  border-right: 1px solid rgba(240, 246, 255, .095);
  background: transparent;
  text-align: left;
  color: inherit;
  appearance: none;
}

.ov-card:last-child {
  border-right: 0;
}

.ov-value {
  margin-top: 14px;
  color: #f4f6ff;
  font-size: clamp(32px, 3vw, 48px);
  line-height: 1;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.ov-label {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(240, 241, 250, .54);
}

.ai-score-card {
  cursor: pointer;
  background:
    radial-gradient(circle at 76% 18%, rgba(122, 255, 180, .2), transparent 48%),
    rgba(122, 255, 180, .055);
  transition: background .18s ease, transform .18s ease;
}

.ai-score-card:hover {
  background:
    radial-gradient(circle at 78% 18%, rgba(122, 255, 180, .2), transparent 44%),
    rgba(122, 255, 180, .075);
  transform: translateY(-2px);
}

.ai-score-card .ov-value {
  color: #7affb4;
}

.ai-score-card .ov-hint {
  margin-top: 10px;
  color: rgba(122, 255, 180, .78);
  font-size: 12px;
  font-weight: 760;
}

.score-closure-strip {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 28px;
  align-items: center;
  margin-bottom: 22px;
  padding: 28px 30px;
  border: 1px solid rgba(255, 126, 66, .24);
  border-radius: 18px;
  background:
    linear-gradient(90deg, rgba(255, 126, 66, .13), rgba(255, 126, 66, .05) 54%, rgba(255, 126, 66, .09)),
    rgba(13, 8, 6, .78);
  box-shadow: 0 24px 80px rgba(255, 84, 18, .08);
  overflow: hidden;
}

.score-closure-strip::after {
  content: "";
  position: absolute;
  right: -120px;
  top: -120px;
  width: 330px;
  height: 330px;
  border-radius: 50%;
  border: 1px solid rgba(255, 126, 66, .09);
  pointer-events: none;
}

.score-closure-strip span {
  color: #ff9b66;
  font-size: 12px;
  font-weight: 900;
}

.score-closure-strip strong {
  display: block;
  margin-top: 6px;
  color: #f4f6ff;
  font-size: 20px;
}

.score-closure-strip p {
  margin: 6px 0 0;
  color: rgba(240, 241, 250, .66);
  line-height: 1.65;
}

.score-closure-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.score-closure-actions button {
  min-height: 44px;
  padding: 0 18px;
  border: 1px solid rgba(255, 126, 66, .3);
  border-radius: 12px;
  background: rgba(255, 255, 255, .04);
  color: #ffb28c;
  font-weight: 850;
  cursor: pointer;
  transition: transform .18s ease, border-color .18s ease, background .18s ease;
}

.score-closure-actions button:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 156, 104, .54);
  background: rgba(255, 255, 255, .07);
}

.score-closure-actions button:first-child {
  border-color: #ff7e42;
  background: #f25b0c;
  color: #fff;
}

.content-tabs {
  display: flex;
  gap: 0;
  padding: 0;
  border: 1px solid rgba(240, 246, 255, .1);
  background: rgba(7, 8, 11, .82);
  margin-bottom: 0;
}

.ctab {
  position: relative;
  min-height: 72px;
  padding: 14px 28px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  flex: 1;
  color: rgba(240, 241, 250, .56);
  cursor: pointer;
  border: 1px solid transparent;
  border-right-color: rgba(240, 246, 255, .07);
  transition: background .18s ease, border-color .18s ease, color .18s ease;
  font-size: 14px;
  font-weight: 780;
}

.ctab:last-child {
  border-right-color: transparent;
}

.ctab:hover {
  color: #f4f6ff;
  background: rgba(240, 241, 250, .045);
}

.ctab.active {
  color: #f4fff8;
  border-color: rgba(122, 255, 180, .22);
  background: rgba(122, 255, 180, .075);
}

.ctab.active .ctab-en {
  color: #7affb4;
}

.ctab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  margin-left: auto;
  font-size: 11px;
  font-weight: 820;
  color: #7affb4;
  background: rgba(122, 255, 180, .1);
  border: 1px solid rgba(122, 255, 180, .2);
  border-radius: 999px;
}

.detail-body {
  border: 1px solid rgba(240, 246, 255, .11);
  border-top: 0;
  background:
    radial-gradient(circle at 78% 18%, rgba(122, 255, 180, .045), transparent 32%),
    rgba(9, 10, 13, .86);
  box-shadow: 0 22px 70px rgba(0, 0, 0, .28);
}

.tab-panel {
  min-height: 520px;
  padding: 36px 34px;
}

.section-head {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 20px;
}

.section-head strong {
  color: #f4f6ff;
  font-size: 24px;
  line-height: 1;
  font-weight: 850;
}

.section-head-action {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-item {
  position: relative;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 12px;
}

.chat-item::before {
  content: "";
  position: absolute;
  left: 8px;
  top: 24px;
  bottom: -18px;
  width: 1px;
  background: rgba(240, 241, 250, .08);
}

.chat-item:last-child::before {
  display: none;
}

.chat-node {
  width: 10px;
  height: 10px;
  margin-top: 18px;
  border-radius: 50%;
  background: #7affb4;
  box-shadow: 0 0 0 6px rgba(122, 255, 180, .09);
}

.chat-card {
  padding: 18px 20px;
  border: 1px solid rgba(240, 241, 250, .1);
  background:
    linear-gradient(135deg, rgba(240, 241, 250, .06), rgba(240, 241, 250, .025));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .035);
}

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.chat-sender {
  font-size: 14px;
  font-weight: 820;
  color: #f4f6ff;
}

.chat-time {
  font-size: 12px;
  color: rgba(240, 241, 250, .42);
  font-variant-numeric: tabular-nums;
}

.chat-content {
  font-size: 14px;
  color: rgba(240, 241, 250, .74);
  line-height: 1.6;
  word-break: break-word;
}

.total-score-bar {
  min-height: 96px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  border: 1px solid rgba(122, 255, 180, .16);
  background:
    radial-gradient(circle at 70% 0%, rgba(122, 255, 180, .14), transparent 50%),
    rgba(240, 241, 250, .045);
}

.total-score-bar strong {
  display: block;
  margin-top: 8px;
  color: #f4f6ff;
  font-size: 18px;
  font-weight: 820;
}

.ts-value {
  color: #7affb4;
  font-size: 48px;
  line-height: 1;
  font-weight: 880;
  font-variant-numeric: tabular-nums;
}

.score-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.score-group {
  padding: 18px;
  border: 1px solid rgba(240, 241, 250, .1);
  background: rgba(240, 241, 250, .035);
}

.sg-title {
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(122, 255, 180, .14);
  color: #7affb4;
  font-size: 14px;
  font-weight: 820;
  letter-spacing: .08em;
}

.score-row {
  padding: 14px 0;
  border-bottom: 1px solid rgba(240, 241, 250, .075);
}

.score-row:last-child {
  border-bottom: none;
}

.score-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sr-name {
  font-size: 14px;
  color: rgba(240, 241, 250, .82);
  font-weight: 760;
  flex: 1;
  min-width: 0;
}

.sr-score {
  flex-shrink: 0;
  min-width: 72px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.sr-value {
  color: #f4f6ff;
  font-size: 18px;
  font-weight: 850;
}

.sr-max {
  font-size: 13px;
  color: rgba(240, 241, 250, .42);
  font-weight: 760;
}

.sr-meter {
  height: 4px;
  margin-top: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(240, 241, 250, .1);
}

.sr-meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1fd5f9, #7affb4);
}

.sr-comment {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(240, 241, 250, .08);
  background: rgba(5, 6, 9, .42);
  font-size: 13px;
  color: rgba(240, 241, 250, .58);
  line-height: 1.55;
}

.export-btn {
  height: 34px;
  border-color: rgba(122, 255, 180, .28) !important;
  background: rgba(122, 255, 180, .08) !important;
  color: #7affb4 !important;
  font-weight: 760;
}

.issue-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.issue-card {
  padding: 18px 20px;
  border: 1px solid rgba(255, 211, 138, .18);
  background:
    linear-gradient(90deg, rgba(255, 211, 138, .065), transparent 45%),
    rgba(240, 241, 250, .032);
}

.issue-card.resolved {
  border-color: rgba(122, 255, 180, .16);
  background:
    linear-gradient(90deg, rgba(122, 255, 180, .055), transparent 45%),
    rgba(240, 241, 250, .032);
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.issue-status {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(255, 211, 138, .1);
  border: 1px solid rgba(255, 211, 138, .22);
  color: #ffd38a;
  font-size: 12px;
  font-weight: 820;
}

.issue-card.resolved .issue-status {
  background: rgba(122, 255, 180, .1);
  border-color: rgba(122, 255, 180, .22);
  color: #7affb4;
}

.issue-category {
  font-size: 13px;
  color: rgba(240, 241, 250, .48);
}

.issue-desc {
  font-size: 14px;
  color: rgba(240, 241, 250, .82);
  line-height: 1.6;
  margin-bottom: 8px;
}

.issue-time {
  font-size: 12px;
  color: rgba(240, 241, 250, .4);
  font-variant-numeric: tabular-nums;
}

.panel-empty {
  min-height: 300px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
  border: 1px solid rgba(240, 241, 250, .09);
  background:
    radial-gradient(circle at 50% 46%, rgba(122, 255, 180, .05), transparent 34%),
    rgba(240, 241, 250, .028);
}

.empty-mark {
  width: 74px;
  height: 74px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(122, 255, 180, .18);
  border-radius: 50%;
  color: #7affb4;
  background: rgba(122, 255, 180, .06);
  font-size: 12px;
  font-weight: 880;
  letter-spacing: .12em;
}

.panel-empty strong {
  color: #f4f6ff;
  font-size: 18px;
}

.panel-empty p {
  margin: 0;
  color: rgba(240, 241, 250, .46);
  font-size: 13px;
}

.detail-page :deep(.el-loading-mask) {
  background: rgba(5, 6, 9, .72);
  backdrop-filter: blur(8px);
}

.detail-page :deep(.el-loading-spinner .path) {
  stroke: #7affb4;
}

@media (max-width: 900px) {
  .detail-page {
    padding: 22px 14px 42px;
  }

  .hero-panel {
    grid-template-columns: 1fr;
    padding: 28px 24px;
  }

  .hero-status {
    min-width: 0;
  }

  .overview-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-top: 1px solid rgba(240, 241, 250, .12);
  }

  .ov-card {
    border-right: 0;
    border-bottom: 1px solid rgba(240, 241, 250, .1);
  }

  .score-closure-strip {
    grid-template-columns: 1fr;
  }

  .score-closure-actions {
    justify-content: flex-start;
  }

  .content-tabs {
    flex-direction: column;
  }

  .tab-panel {
    padding: 20px 14px;
  }

  .score-groups,
  .issue-list {
    grid-template-columns: 1fr;
  }

  .section-head-action {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 520px) {
  .hero-copy h1 {
    font-size: 34px;
  }

  .overview-cards {
    grid-template-columns: 1fr;
  }

  .chat-head,
  .score-row-top,
  .total-score-bar {
    align-items: flex-start;
    flex-direction: column;
  }
}

/* HTML Glass v3 rewrite */
.detail-page {
  min-height: 100vh;
  padding: 26px 30px 56px;
  overflow: visible;
  background:
    radial-gradient(circle at 16% 8%, rgba(255, 100, 46, .16), transparent 28%),
    radial-gradient(circle at 82% 4%, rgba(255, 174, 142, .16), transparent 26%),
    linear-gradient(135deg, #fff8f3 0%, #fff1e8 48%, #fce7d8 100%);
  color: #343a49;
}

.detail-page::before,
.detail-page::after,
.detail-orbit {
  display: none;
}

.detail-shell {
  width: min(1280px, 100%);
  margin: 0 auto;
}

.detail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.back-btn {
  height: 40px;
  padding: 0 16px !important;
  border: 1px solid rgba(255, 255, 255, .78);
  border-radius: 999px;
  background: rgba(255, 255, 255, .58);
  color: #697386;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .86), 0 8px 20px rgba(31, 38, 51, .04);
  font-size: 13px;
  font-weight: 700;
  backdrop-filter: blur(20px) saturate(1.12);
}

.back-btn:hover {
  background: rgba(255, 255, 255, .84);
  color: #f04b18;
  transform: translateX(-2px);
}

.detail-route {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #a9b0bc;
  font-size: 12px;
  font-weight: 600;
}

.detail-route i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #ffae8e;
}

.detail-route strong {
  color: #697386;
}

.record-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 26px;
  min-height: 256px;
  padding: 38px 42px;
  border: 1px solid rgba(255, 255, 255, .82);
  border-radius: 30px;
  background:
    radial-gradient(circle at 8% 12%, rgba(255, 100, 46, .18), transparent 32%),
    radial-gradient(circle at 80% 18%, rgba(255, 174, 142, .18), transparent 34%),
    linear-gradient(135deg, rgba(255, 255, 255, .88), rgba(255, 255, 255, .58));
  box-shadow: 0 18px 42px rgba(116, 71, 39, .09), inset 0 1px 0 rgba(255, 255, 255, .9);
  backdrop-filter: blur(24px) saturate(1.18);
  overflow: hidden;
}

.record-hero::before {
  content: "";
  position: absolute;
  top: 24px;
  left: 42px;
  width: 112px;
  height: 5px;
  border-radius: 999px;
  background: linear-gradient(90deg, #f04b18, rgba(255, 174, 142, .62));
}

.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.hero-kicker,
.summary-card small,
.ctab-en,
.section-head span,
.ts-label,
.side-card > span {
  color: #f04b18;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.hero-main h1 {
  margin: 14px 0 12px;
  color: #171a24;
  font-size: clamp(38px, 5vw, 68px);
  line-height: 1.04;
  font-weight: 850;
  letter-spacing: 0;
}

.hero-main p {
  max-width: 680px;
  margin: 0;
  color: #697386;
  font-size: 14px;
  line-height: 1.75;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 22px;
  color: #697386;
  font-size: 13px;
}

.status-pill {
  min-height: 28px;
  padding: 0 12px;
  border-color: rgba(22, 155, 104, .22);
  background: rgba(227, 246, 238, .9);
  color: #169b68;
  border-radius: 999px;
}

.status-ENDED {
  color: #697386;
  background: rgba(255, 255, 255, .62);
  border-color: rgba(199, 207, 220, .62);
}

.status-CREATED {
  color: #d98200;
  background: #fff3dc;
  border-color: rgba(217, 130, 0, .22);
}

.hero-ai-card {
  position: relative;
  z-index: 1;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 26px;
  border: 1px solid rgba(255, 255, 255, .78);
  border-radius: 24px;
  background:
    radial-gradient(circle at 70% 0%, rgba(240, 75, 24, .13), transparent 52%),
    rgba(255, 255, 255, .62);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .86), 0 12px 28px rgba(31, 38, 51, .05);
}

.hero-ai-card span {
  color: #697386;
  font-size: 12px;
  font-weight: 700;
}

.hero-ai-card strong {
  margin-top: 12px;
  color: #f04b18;
  font-size: 44px;
  line-height: 1;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.hero-ai-card small {
  margin-top: 6px;
  color: #697386;
  font-size: 12px;
}

.hero-ai-card button,
.side-card button,
.action-buttons button {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.hero-ai-card button {
  width: fit-content;
  height: 36px;
  margin-top: 22px;
  padding: 0 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f04b18, #ff7a45);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 10px 20px rgba(240, 75, 24, .16), inset 0 1px 0 rgba(255, 255, 255, .24);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.summary-card {
  min-height: 116px;
  padding: 22px;
  border: 1px solid rgba(255, 255, 255, .74);
  border-radius: 24px;
  background: rgba(255, 255, 255, .48);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .78), 0 10px 28px rgba(31, 38, 51, .05);
  backdrop-filter: blur(18px) saturate(1.12);
}

.summary-card span {
  color: #697386;
  font-size: 13px;
  font-weight: 700;
}

.summary-card strong {
  display: block;
  margin-top: 14px;
  color: #171a24;
  font-size: clamp(26px, 3vw, 38px);
  line-height: 1;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.summary-card small {
  display: block;
  margin-top: 10px;
  color: #a9b0bc;
}

.action-band {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20px;
  align-items: center;
  margin-top: 14px;
  padding: 22px 24px;
  border: 1px solid rgba(255, 174, 142, .34);
  border-radius: 24px;
  background:
    radial-gradient(circle at 12% 14%, rgba(255, 100, 46, .13), transparent 30%),
    linear-gradient(135deg, rgba(255, 247, 243, .82), rgba(255, 255, 255, .54));
  box-shadow: 0 14px 28px rgba(240, 75, 24, .08), inset 0 1px 0 rgba(255, 255, 255, .82);
}

.action-band span {
  color: #f04b18;
  font-size: 12px;
  font-weight: 800;
}

.action-band strong {
  display: block;
  margin-top: 6px;
  color: #171a24;
  font-size: 18px;
}

.action-band p {
  margin: 6px 0 0;
  color: #697386;
  line-height: 1.65;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.action-buttons button {
  min-height: 38px;
  padding: 0 15px;
  border: 1px solid rgba(240, 75, 24, .2);
  border-radius: 14px;
  background: rgba(255, 255, 255, .58);
  color: #d94312;
  font-weight: 750;
}

.action-buttons .primary-action {
  border-color: transparent;
  background: linear-gradient(135deg, #f04b18, #ff7a45);
  color: #fff;
  box-shadow: 0 10px 20px rgba(240, 75, 24, .16), inset 0 1px 0 rgba(255, 255, 255, .24);
}

.detail-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  margin-top: 16px;
  align-items: start;
}

.workspace-main,
.workspace-side {
  min-width: 0;
}

.content-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, .74);
  border-radius: 24px;
  background: rgba(255, 255, 255, .42);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .78), 0 10px 28px rgba(31, 38, 51, .05);
  backdrop-filter: blur(18px) saturate(1.12);
}

.ctab {
  min-height: 70px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, .58);
  border-radius: 18px;
  background: rgba(255, 255, 255, .4);
  color: #697386;
  cursor: pointer;
  text-align: left;
}

.ctab strong {
  display: block;
  margin-top: 2px;
  color: #343a49;
  font-size: 14px;
}

.ctab.active {
  border-color: rgba(255, 174, 142, .34);
  background: rgba(255, 247, 243, .82);
  box-shadow: 0 10px 20px rgba(116, 71, 39, .07);
}

.ctab.active strong,
.ctab.active .ctab-en {
  color: #f04b18;
}

.ctab-badge {
  float: right;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(240, 75, 24, .18);
  border-radius: 999px;
  background: #fff7f3;
  color: #f04b18;
  font-size: 11px;
  font-weight: 800;
}

.detail-body {
  margin-top: 12px;
  border: 1px solid rgba(255, 255, 255, .78);
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, .76), rgba(255, 255, 255, .52));
  box-shadow: 0 12px 28px rgba(116, 71, 39, .055), inset 0 1px 0 rgba(255, 255, 255, .84);
  backdrop-filter: blur(20px) saturate(1.12);
  overflow: hidden;
}

.tab-panel {
  min-height: 430px;
  padding: 24px;
}

.section-head {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 20px;
}

.section-head strong {
  color: #171a24;
  font-size: 22px;
}

.section-head-action {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-item {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
}

.chat-item::before,
.chat-node {
  display: none;
}

.chat-avatar {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #ffe7dc;
  color: #f04b18;
  font-weight: 800;
}

.chat-card {
  padding: 15px 16px;
  border: 1px solid rgba(255, 255, 255, .74);
  border-radius: 18px;
  background: rgba(255, 255, 255, .54);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .78);
}

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.chat-sender {
  color: #171a24;
  font-size: 14px;
  font-weight: 800;
}

.chat-time,
.issue-time,
.issue-category {
  color: #a9b0bc;
  font-size: 12px;
}

.chat-content,
.issue-desc {
  color: #343a49;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.chat-attachment {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 72px;
  padding: 12px;
  border: 1px solid rgba(255, 174, 142, .25);
  border-radius: 18px;
  background:
    radial-gradient(circle at 12% 0%, rgba(255, 100, 46, .12), transparent 36%),
    rgba(255, 247, 243, .74);
}

.attachment-mark {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: #f04b18;
  color: #fff;
  font-weight: 850;
  box-shadow: 0 10px 20px rgba(240, 75, 24, .16);
}

.attachment-document .attachment-mark {
  background: #4b6fff;
  box-shadow: 0 10px 20px rgba(75, 111, 255, .16);
}

.attachment-archive .attachment-mark {
  background: #d98200;
  box-shadow: 0 10px 20px rgba(217, 130, 0, .16);
}

.attachment-file .attachment-mark {
  background: #697386;
  box-shadow: 0 10px 20px rgba(105, 115, 134, .14);
}

.attachment-main {
  min-width: 0;
}

.attachment-main strong {
  display: block;
  overflow: hidden;
  color: #171a24;
  font-size: 14px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-main small {
  display: block;
  margin-top: 4px;
  color: #697386;
  font-size: 12px;
  line-height: 1.5;
}

.chat-attachment button {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(240, 75, 24, .2);
  border-radius: 13px;
  background: rgba(255, 255, 255, .66);
  color: #d94312;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
}

.chat-attachment button:hover {
  background: #f04b18;
  color: #fff;
}

.total-score-bar {
  min-height: 96px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  border: 1px solid rgba(255, 174, 142, .28);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(255, 247, 243, .82), rgba(255, 255, 255, .56));
}

.total-score-bar strong {
  display: block;
  margin-top: 8px;
  color: #171a24;
  font-size: 18px;
}

.ts-value {
  color: #f04b18;
  font-size: 48px;
  line-height: 1;
  font-weight: 850;
}

.score-groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.score-group,
.issue-card {
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, .72);
  border-radius: 18px;
  background: rgba(255, 255, 255, .48);
}

.sg-title {
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(240, 75, 24, .12);
  color: #f04b18;
  font-size: 14px;
  font-weight: 800;
}

.score-row {
  padding: 12px 0;
  border-bottom: 1px solid rgba(199, 207, 220, .35);
}

.score-row:last-child {
  border-bottom: 0;
}

.score-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sr-name {
  color: #343a49;
  font-size: 14px;
  font-weight: 750;
}

.sr-value {
  color: #171a24;
  font-size: 18px;
  font-weight: 850;
}

.sr-max {
  color: #a9b0bc;
  font-size: 13px;
}

.sr-meter {
  height: 5px;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(214, 220, 229, .58);
  overflow: hidden;
}

.sr-meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f04b18, #ffae8e);
}

.sr-comment {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 174, 142, .2);
  border-radius: 14px;
  background: rgba(255, 247, 243, .62);
  color: #697386;
  font-size: 13px;
}

.issue-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.issue-card.resolved {
  background: rgba(227, 246, 238, .58);
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.issue-status {
  min-height: 24px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(217, 130, 0, .22);
  border-radius: 999px;
  background: #fff3dc;
  color: #d98200;
  font-size: 12px;
  font-weight: 800;
}

.issue-card.resolved .issue-status {
  border-color: rgba(22, 155, 104, .22);
  background: #e3f6ee;
  color: #169b68;
}

.export-btn {
  border-color: rgba(240, 75, 24, .22) !important;
  background: #fff7f3 !important;
  color: #f04b18 !important;
  font-weight: 750;
}

.panel-empty {
  min-height: 280px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
  border: 1px dashed rgba(199, 207, 220, .72);
  border-radius: 20px;
  background: rgba(255, 255, 255, .34);
}

.empty-mark {
  width: 70px;
  height: 70px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(240, 75, 24, .18);
  border-radius: 50%;
  color: #f04b18;
  background: #fff7f3;
  font-size: 12px;
  font-weight: 850;
}

.panel-empty strong {
  color: #171a24;
  font-size: 18px;
}

.panel-empty p {
  margin: 0;
  color: #697386;
}

.workspace-side {
  display: grid;
  gap: 12px;
}

.side-card {
  padding: 22px;
  border: 1px solid rgba(255, 255, 255, .74);
  border-radius: 24px;
  background: rgba(255, 255, 255, .5);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .78), 0 10px 28px rgba(31, 38, 51, .05);
  backdrop-filter: blur(18px) saturate(1.12);
}

.side-card strong {
  display: block;
  margin-top: 8px;
  color: #171a24;
  font-size: 20px;
}

.side-card p {
  margin: 10px 0 0;
  color: #697386;
  line-height: 1.65;
}

.ai-card {
  background:
    radial-gradient(circle at 80% 0%, rgba(255, 100, 46, .16), transparent 34%),
    rgba(255, 255, 255, .56);
}

.side-card button {
  height: 38px;
  margin-top: 18px;
  padding: 0 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f04b18, #ff7a45);
  color: #fff;
  font-weight: 750;
}

.snapshot-list {
  display: grid;
  gap: 14px;
  margin-top: 16px;
}

.snapshot-list div {
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, .46);
}

.snapshot-list small {
  display: block;
  color: #a9b0bc;
  font-size: 11px;
}

.snapshot-list strong {
  margin-top: 4px;
  font-size: 13px;
  color: #343a49;
  word-break: break-word;
}

.detail-empty-state {
  width: min(520px, 100%);
  margin: 12vh auto 0;
  padding: 34px;
  border: 1px solid rgba(255, 255, 255, .76);
  border-radius: 28px;
  background: rgba(255, 255, 255, .62);
  text-align: center;
  box-shadow: 0 18px 42px rgba(116, 71, 39, .09);
}

.detail-empty-state strong {
  color: #171a24;
  font-size: 22px;
}

.detail-empty-state p {
  color: #697386;
}

.detail-empty-state button {
  height: 38px;
  padding: 0 18px;
  border: 0;
  border-radius: 14px;
  background: #f04b18;
  color: #fff;
  font-weight: 750;
}

.detail-page :deep(.el-loading-mask) {
  background: rgba(255, 245, 238, .72);
  backdrop-filter: blur(8px);
}

.detail-page :deep(.el-loading-spinner .path) {
  stroke: #f04b18;
}

@media (max-width: 1180px) {
  .record-hero,
  .action-band,
  .detail-workspace {
    grid-template-columns: 1fr;
  }

  .workspace-side {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .detail-page {
    padding: 18px 12px 34px;
  }

  .detail-toolbar,
  .hero-meta,
  .action-buttons {
    align-items: flex-start;
    flex-direction: column;
  }

  .record-hero {
    padding: 28px 22px;
  }

  .summary-grid,
  .content-tabs,
  .score-groups,
  .issue-list,
  .workspace-side {
    grid-template-columns: 1fr;
  }

  .section-head-action,
  .total-score-bar {
    align-items: flex-start;
    flex-direction: column;
  }
}

/* Align with CourseLearning page density */
.detail-page {
  --detail-bg: oklch(0.985 0.005 55);
  --detail-surface: #fffaf6;
  --detail-surface-raised: rgba(255, 255, 255, .82);
  --detail-border: rgba(232, 214, 202, .8);
  --detail-text: #1f2430;
  --detail-muted: #7c8493;
  --detail-orange: #f04b18;
  min-height: 100vh;
  padding: 28px 0 72px;
  background: var(--detail-bg);
}

.detail-shell {
  width: min(1520px, calc(100% - 56px));
}

.detail-toolbar {
  margin-bottom: 14px;
  padding: 0 2px;
}

.back-btn {
  height: 34px;
  padding: 0 12px !important;
  border-color: var(--detail-border);
  border-radius: 8px;
  background: var(--detail-surface-raised);
  box-shadow: none;
  color: var(--detail-muted);
  font-size: 13px;
}

.detail-route {
  color: var(--detail-muted);
  font-size: 13px;
}

.record-hero {
  min-height: 154px;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 0;
  padding: 0;
  border: 1px solid var(--detail-border);
  border-radius: 18px;
  background: linear-gradient(90deg, var(--detail-surface-raised) 0%, var(--detail-surface-raised) 72%, #fff1e8 100%);
  box-shadow: none;
  backdrop-filter: none;
}

.record-hero::before {
  display: none;
}

.hero-main {
  justify-content: flex-start;
  padding: 28px 34px;
}

.hero-kicker,
.summary-card small,
.ctab-en,
.section-head span,
.ts-label,
.side-card > span {
  color: var(--detail-orange);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: none;
}

.hero-main h1 {
  margin: 10px 0 8px;
  color: var(--detail-text);
  font-size: 32px;
  line-height: 1.15;
  font-weight: 850;
}

.hero-main p {
  max-width: 780px;
  color: var(--detail-muted);
  font-size: 14px;
  line-height: 1.65;
}

.hero-meta {
  margin-top: 16px;
  font-size: 13px;
}

.status-pill {
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 850;
}

.hero-ai-card {
  border: 0;
  border-left: 1px solid var(--detail-border);
  border-radius: 0;
  background: linear-gradient(135deg, #fff1e8, oklch(0.965 0.008 55));
  box-shadow: none;
  padding: 24px 30px;
}

.hero-ai-card span {
  color: var(--detail-muted);
  font-size: 13px;
  font-weight: 820;
}

.hero-ai-card strong {
  margin-top: 8px;
  color: var(--detail-text);
  font-size: 24px;
  line-height: 1.2;
}

.hero-ai-card small {
  margin-top: 2px;
  color: var(--detail-muted);
  font-size: 13px;
  line-height: 1.55;
}

.hero-ai-card button,
.side-card button,
.action-buttons button,
.chat-attachment button {
  min-height: 38px;
  height: auto;
  border-radius: 8px;
  box-shadow: none;
  font-size: 13px;
}

.hero-ai-card button {
  margin-top: 16px;
  padding: 0 14px;
}

.summary-grid {
  gap: 12px;
  margin-top: 14px;
}

.summary-card {
  min-height: 88px;
  padding: 18px;
  border: 1px solid var(--detail-border);
  border-radius: 18px;
  background: var(--detail-surface-raised);
  box-shadow: none;
  backdrop-filter: none;
}

.summary-card span {
  color: var(--detail-muted);
  font-size: 13px;
  font-weight: 820;
}

.summary-card strong {
  margin-top: 8px;
  color: var(--detail-text);
  font-size: 28px;
  line-height: 1.05;
}

.summary-card small {
  margin-top: 6px;
  color: #a9a095;
}

.action-band {
  margin-top: 14px;
  padding: 18px 20px;
  border: 1px solid var(--detail-border);
  border-radius: 18px;
  background: var(--detail-surface-raised);
  box-shadow: none;
}

.action-band span {
  font-size: 12px;
}

.action-band strong {
  margin-top: 5px;
  color: var(--detail-text);
  font-size: 17px;
  line-height: 1.35;
}

.action-band p {
  max-width: 840px;
  color: var(--detail-muted);
  font-size: 14px;
  line-height: 1.65;
}

.action-buttons {
  gap: 10px;
}

.action-buttons button {
  padding: 0 14px;
  border-color: rgba(240, 75, 24, .18);
  background: #fffaf6;
  font-weight: 850;
}

.detail-workspace {
  grid-template-columns: minmax(0, 1fr) clamp(280px, 22vw, 360px);
  gap: 18px;
  margin-top: 18px;
}

.content-tabs {
  gap: 8px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.ctab {
  min-height: 58px;
  padding: 12px 16px;
  border: 1px solid var(--detail-border);
  border-radius: 16px;
  background: var(--detail-surface-raised);
}

.ctab strong {
  margin-top: 2px;
  color: var(--detail-text);
  font-size: 14px;
}

.ctab.active {
  border-color: var(--detail-text);
  background: #fff;
  box-shadow: none;
}

.ctab-badge {
  height: 20px;
  min-width: 20px;
  border-color: rgba(240, 75, 24, .18);
  font-size: 11px;
}

.detail-body,
.side-card {
  border: 1px solid var(--detail-border);
  border-radius: 18px;
  background: var(--detail-surface-raised);
  box-shadow: none;
  backdrop-filter: none;
}

.detail-body {
  margin-top: 12px;
}

.tab-panel {
  min-height: 336px;
  padding: 22px;
}

.section-head {
  gap: 5px;
  margin-bottom: 16px;
}

.section-head strong {
  color: var(--detail-text);
  font-size: 24px;
  line-height: 1.25;
}

.chat-list {
  gap: 10px;
}

.chat-item {
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
}

.chat-avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: #ffeadf;
}

.chat-card {
  padding: 14px 14px;
  border: 1px solid rgba(238, 223, 214, .72);
  border-radius: 14px;
  background: #fffdfb;
  box-shadow: none;
}

.chat-head {
  margin-bottom: 8px;
}

.chat-sender {
  color: var(--detail-text);
  font-size: 13px;
  font-weight: 850;
}

.chat-time,
.issue-time,
.issue-category {
  font-size: 12px;
}

.chat-attachment {
  min-height: 66px;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  padding: 10px;
  border-color: rgba(238, 223, 214, .8);
  border-radius: 14px;
  background: #fff9f5;
}

.attachment-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  box-shadow: none;
}

.attachment-main strong {
  font-size: 13px;
}

.attachment-main small {
  font-size: 12px;
}

.chat-attachment button {
  min-height: 32px;
  padding: 0 12px;
}

.workspace-side {
  display: grid;
  gap: 12px;
}

.side-card {
  padding: 20px;
}

.side-card strong {
  margin-top: 8px;
  color: var(--detail-text);
  font-size: 18px;
  line-height: 1.25;
}

.side-card p {
  margin-top: 10px;
  color: var(--detail-muted);
  font-size: 14px;
  line-height: 1.65;
}

.side-card button {
  margin-top: 16px;
}

.snapshot-list {
  gap: 10px;
  margin-top: 14px;
}

.snapshot-list div {
  padding: 12px;
  border-radius: 12px;
  background: #fffdfb;
}

@media (max-width: 1180px) {
  .record-hero,
  .action-band,
  .detail-workspace {
    grid-template-columns: 1fr;
  }

  .hero-ai-card {
    border-left: 0;
    border-top: 1px solid var(--detail-border);
  }
}

@media (max-width: 760px) {
  .detail-page {
    padding: 18px 0 42px;
  }

  .detail-shell {
    width: min(100% - 28px, 1520px);
  }

  .hero-main,
  .hero-ai-card {
    padding: 22px;
  }

  .hero-main h1 {
    font-size: 28px;
  }

  .summary-grid,
  .content-tabs,
  .workspace-side {
    grid-template-columns: 1fr;
  }
}

/* ImageGen direction: polished AI roadshow recap */
.detail-page {
  --ig-bg: #fffaf5;
  --ig-card: #fffefd;
  --ig-soft: #fff6ef;
  --ig-line: #f0e4dc;
  --ig-line-strong: #ead4c6;
  --ig-text: #1f2633;
  --ig-muted: #6f7a8b;
  --ig-faint: #9aa4b4;
  --ig-orange: #f15623;
  --ig-orange-dark: #dc4314;
  --ig-green: #32b977;
  min-height: 100vh;
  padding: 26px 0 60px;
  background:
    radial-gradient(circle at 78% 8%, rgba(255, 118, 66, .09), transparent 28%),
    linear-gradient(180deg, #fffdf9 0%, var(--ig-bg) 100%);
  color: var(--ig-text);
}

.detail-shell {
  width: min(1568px, calc(100% - 44px));
  margin: 0 auto;
}

.recap-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 24px;
  align-items: start;
}

.recap-main {
  min-width: 0;
}

.detail-toolbar {
  align-items: center;
  margin-bottom: 18px;
  padding: 0 10px;
}

.back-btn {
  height: 36px;
  padding: 0 14px !important;
  border: 1px solid var(--ig-line);
  border-radius: 999px;
  background: rgba(255, 255, 255, .82);
  color: #7b8493;
  box-shadow: 0 8px 22px rgba(89, 61, 39, .04);
  font-size: 14px;
  font-weight: 760;
}

.detail-route {
  gap: 9px;
  color: #8c95a5;
  font-size: 14px;
  font-weight: 780;
}

.detail-route strong {
  color: var(--ig-orange);
}

.detail-route i {
  width: 5px;
  height: 5px;
  background: var(--ig-orange);
}

.record-hero {
  position: relative;
  min-height: 218px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 328px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--ig-line-strong);
  border-radius: 18px;
  background:
    radial-gradient(circle at 58% 74%, rgba(255, 118, 66, .12), transparent 23%),
    linear-gradient(90deg, #fffdfb 0%, #fff9f4 62%, #fff4ea 100%);
  box-shadow: 0 18px 45px rgba(70, 45, 24, .07);
}

.record-hero::before {
  content: "";
  position: absolute;
  right: 330px;
  bottom: -18px;
  width: 210px;
  height: 150px;
  display: block;
  border-radius: 40px 40px 0 0;
  background:
    linear-gradient(135deg, rgba(241, 86, 35, .12), rgba(241, 86, 35, .03));
  transform: skewX(-16deg);
  opacity: .72;
}

.record-hero::after {
  content: "";
  position: absolute;
  right: 392px;
  bottom: 44px;
  width: 62px;
  height: 62px;
  border: 16px solid rgba(241, 86, 35, .18);
  border-radius: 50%;
  opacity: .65;
}

.hero-main {
  position: relative;
  z-index: 1;
  justify-content: center;
  padding: 34px 42px;
}

.hero-kicker,
.action-band span,
.section-head span,
.side-card-head > span:last-child {
  color: var(--ig-orange);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: none;
}

.hero-main h1 {
  margin: 10px 0 10px;
  color: var(--ig-text);
  font-size: 40px;
  line-height: 1.12;
  font-weight: 900;
}

.hero-main p {
  max-width: 720px;
  color: #596577;
  font-size: 16px;
  line-height: 1.7;
}

.hero-meta {
  gap: 12px;
  margin-top: 18px;
  color: #758092;
  font-size: 15px;
}

.status-pill {
  min-height: 28px;
  padding: 0 12px;
  border: 0;
  background: #e7f7ed;
  color: var(--ig-green);
  font-size: 14px;
  font-weight: 850;
}

.hero-ai-card {
  z-index: 1;
  justify-content: center;
  padding: 34px 42px;
  border: 0;
  border-left: 1px solid #f3d7c3;
  border-radius: 0;
  background: linear-gradient(140deg, #fff3e8 0%, #ffe3cf 100%);
  box-shadow: none;
}

.hero-ai-card span {
  color: #717b8d;
  font-size: 14px;
  font-weight: 850;
}

.hero-ai-card strong {
  margin-top: 12px;
  color: var(--ig-orange);
  font-size: 34px;
  line-height: 1.1;
  font-weight: 900;
}

.hero-ai-card small {
  margin-top: 4px;
  color: #7f8795;
  font-size: 14px;
}

.hero-ai-card button,
.action-buttons .primary-action,
.side-card button {
  border: 0;
  border-radius: 10px;
  background: linear-gradient(180deg, #ff6f35 0%, var(--ig-orange-dark) 100%);
  color: #fff;
  box-shadow: 0 12px 24px rgba(220, 67, 20, .22);
  font-weight: 850;
}

.hero-ai-card button {
  width: fit-content;
  min-height: 42px;
  margin-top: 22px;
  padding: 0 18px;
  font-size: 14px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.summary-card {
  min-height: 122px;
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  padding: 24px;
  border: 1px solid var(--ig-line);
  border-radius: 18px;
  background: var(--ig-card);
  box-shadow: 0 16px 35px rgba(70, 45, 24, .045);
}

.summary-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(241, 86, 35, .2);
  border-radius: 50%;
  background: #fff4ed;
  color: var(--ig-orange);
  font-size: 25px;
}

.summary-card span {
  color: #7c8492;
  font-size: 14px;
  font-weight: 780;
}

.summary-card strong {
  display: block;
  margin-top: 5px;
  color: var(--ig-text);
  font-size: 26px;
  line-height: 1.05;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.summary-card small {
  display: block;
  margin-top: 5px;
  color: #8e98a8;
  font-size: 13px;
  font-weight: 760;
}

.action-band {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding: 22px 26px;
  border: 1px solid var(--ig-line);
  border-radius: 18px;
  background: var(--ig-card);
  box-shadow: 0 14px 32px rgba(70, 45, 24, .045);
}

.action-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #fff0e7;
  color: var(--ig-orange);
  font-size: 18px;
}

.action-band strong {
  display: block;
  margin-top: 4px;
  color: var(--ig-text);
  font-size: 17px;
  line-height: 1.35;
  font-weight: 900;
}

.action-band p {
  margin: 5px 0 0;
  color: #768091;
  font-size: 14px;
  line-height: 1.55;
}

.action-buttons {
  gap: 12px;
}

.action-buttons button {
  min-height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(241, 86, 35, .24);
  border-radius: 10px;
  background: #fffdfb;
  color: var(--ig-orange-dark);
  font-size: 14px;
  font-weight: 850;
  box-shadow: none;
}

.detail-workspace {
  display: block;
  margin-top: 16px;
}

.content-tabs {
  display: flex;
  gap: 34px;
  padding: 0 22px;
  border: 1px solid var(--ig-line);
  border-bottom: 0;
  border-radius: 18px 18px 0 0;
  background: var(--ig-card);
  box-shadow: none;
}

.ctab {
  position: relative;
  min-height: 64px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: #687386;
  text-align: left;
}

.ctab::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  border-radius: 999px;
  background: transparent;
}

.ctab-en {
  color: inherit;
  font-size: 15px;
  font-weight: 900;
}

.ctab strong {
  margin: 0;
  color: inherit;
  font-size: 16px;
  font-weight: 850;
}

.ctab.active {
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--ig-orange);
}

.ctab.active::after {
  background: var(--ig-orange);
}

.ctab:hover,
.ctab:focus,
.ctab:focus-visible {
  color: #465163;
  background: transparent;
  outline: none;
}

.ctab:hover .ctab-en,
.ctab:hover strong,
.ctab:focus .ctab-en,
.ctab:focus strong,
.ctab:focus-visible .ctab-en,
.ctab:focus-visible strong {
  color: inherit;
}

.ctab.active:hover,
.ctab.active:focus,
.ctab.active:focus-visible {
  color: var(--ig-orange);
}

.ctab.active:hover .ctab-en,
.ctab.active:hover strong,
.ctab.active:focus .ctab-en,
.ctab.active:focus strong,
.ctab.active:focus-visible .ctab-en,
.ctab.active:focus-visible strong {
  color: var(--ig-orange);
}

.ctab-badge {
  height: 22px;
  min-width: 22px;
  border: 0;
  background: #fff0e7;
  color: var(--ig-orange);
}

.detail-body {
  margin-top: 0;
  border: 1px solid var(--ig-line);
  border-radius: 0 0 18px 18px;
  background: var(--ig-card);
  box-shadow: 0 14px 34px rgba(70, 45, 24, .04);
  overflow: hidden;
}

.tab-panel {
  min-height: 336px;
  padding: 24px 34px 34px;
}

.section-head {
  gap: 4px;
  margin-bottom: 18px;
}

.section-head strong {
  color: var(--ig-text);
  font-size: 23px;
  line-height: 1.2;
  font-weight: 900;
}

.chat-list {
  display: grid;
  gap: 12px;
}

.chat-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 14px;
}

.chat-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #ffeadf;
  color: var(--ig-orange);
  font-size: 16px;
  font-weight: 900;
}

.chat-card {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 8px;
}

.chat-sender {
  color: #4d586a;
  font-size: 14px;
  font-weight: 850;
}

.chat-time {
  color: #9aa4b4;
  font-size: 13px;
}

.chat-attachment {
  min-height: 72px;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid #f1e2d8;
  border-radius: 14px;
  background: linear-gradient(90deg, #fff7f1 0%, #fffdfb 100%);
}

.attachment-mark {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: linear-gradient(180deg, #ff6f35, #dd4316);
  color: #fff;
  box-shadow: 0 10px 20px rgba(220, 67, 20, .14);
  font-size: 17px;
}

.attachment-document .attachment-mark {
  background: linear-gradient(180deg, #5c79ff, #3154e8);
  box-shadow: 0 10px 20px rgba(49, 84, 232, .14);
}

.attachment-main strong {
  color: var(--ig-text);
  font-size: 14px;
  font-weight: 900;
}

.attachment-main small {
  color: #818b9a;
  font-size: 13px;
}

.chat-attachment button {
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid #f0d5c5;
  border-radius: 10px;
  background: #fffdfb;
  color: var(--ig-orange-dark);
  font-size: 14px;
  font-weight: 850;
  box-shadow: none;
}

.workspace-side {
  display: grid;
  gap: 20px;
}

.side-card {
  padding: 30px 28px;
  border: 1px solid var(--ig-line);
  border-radius: 18px;
  background: var(--ig-card);
  box-shadow: 0 18px 42px rgba(70, 45, 24, .055);
}

.side-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.side-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #fff0e7;
  color: var(--ig-orange);
  font-size: 22px;
}

.side-card strong {
  display: block;
  margin-top: 20px;
  color: var(--ig-text);
  font-size: 24px;
  line-height: 1.2;
  font-weight: 900;
}

.side-card p {
  margin-top: 16px;
  color: #687386;
  font-size: 16px;
  line-height: 1.75;
}

.side-card button {
  min-height: 42px;
  margin-top: 24px;
  padding: 0 18px;
  font-size: 15px;
}

.snapshot-list {
  display: grid;
  gap: 0;
  margin-top: 22px;
}

.snapshot-list div {
  padding: 18px 0;
  border-bottom: 1px solid var(--ig-line);
  border-radius: 0;
  background: transparent;
}

.snapshot-list div:last-child {
  border-bottom: 0;
}

.snapshot-list small {
  color: #9aa4b4;
  font-size: 13px;
}

.snapshot-list strong {
  display: block;
  margin-top: 8px;
  color: var(--ig-text);
  font-size: 16px;
  font-weight: 900;
}

@media (max-width: 1180px) {
  .record-hero,
  .action-band,
  .recap-layout {
    grid-template-columns: 1fr;
  }

  .detail-workspace {
    display: block;
  }

  .hero-ai-card {
    border-left: 0;
    border-top: 1px solid #f3d7c3;
  }
}

@media (max-width: 760px) {
  .detail-shell {
    width: min(100% - 28px, 1568px);
  }

  .hero-main,
  .hero-ai-card {
    padding: 24px;
  }

  .hero-main h1 {
    font-size: 30px;
  }

  .summary-grid,
  .content-tabs {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    display: grid;
  }

  .content-tabs {
    display: grid;
    gap: 0;
  }

  .ctab {
    min-height: 52px;
  }

  .tab-panel {
    padding: 22px;
  }
}
</style>
