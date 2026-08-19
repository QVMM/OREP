<template>
  <div class="roadshow-page student-page">
    <div class="page-inner">
      <!-- 页头 -->
      <header class="page-head">
        <div>
          <h1>路演训练</h1>
          <p class="sub">发起或加入线上路演，反复练习、回看表现并获得评分反馈</p>
        </div>
        <div class="head-actions">
          <span class="live-pill" aria-label="路演服务可用">
            <i class="led led-ok" aria-hidden="true" />
            路演服务可用
          </span>
          <button type="button" class="btn soft" @click="goRecordings">路演回放</button>
          <BaseButton type="primary" @click="openCreateModal">发起路演</BaseButton>
        </div>
      </header>

      <!-- 主路径：加入（浅色主卡 + 会议室图标） -->
      <section class="join-card" aria-labelledby="joinTitle">
        <div class="label-row">
          <div class="title-block">
            <span class="join-mark" aria-hidden="true">
              <!-- 会议室 / 视频路演 -->
              <svg viewBox="0 0 24 24" fill="none">
                <rect x="2.5" y="5" width="13.5" height="14" rx="2.2" stroke="currentColor" stroke-width="1.75" />
                <path d="M16 10.2 21.5 7.4v9.2L16 13.8" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round" />
                <circle cx="9.2" cy="11" r="1.7" fill="currentColor" />
                <path d="M6.4 15.6c.5-1.3 1.5-2 2.8-2s2.3.7 2.8 2" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" />
              </svg>
            </span>
            <div class="title-copy">
              <span class="eyebrow">快速加入</span>
              <h2 id="joinTitle">加入路演</h2>
            </div>
          </div>
          <span class="hint">使用老师或队友分享的路演信息</span>
        </div>

        <el-form
          ref="joinFormRef"
          :model="joinForm"
          :rules="joinRules"
          label-position="top"
          require-asterisk-position="right"
          class="join-form"
          @submit.prevent
        >
          <div class="fields">
            <el-form-item prop="meetingCode" class="field" label="路演号">
              <el-input
                v-model="joinForm.meetingCode"
                placeholder="6 位路演号"
                maxlength="6"
                size="large"
                :prefix-icon="Grid"
                @input="onCodeInput"
                @keyup.enter="handleJoin"
              />
            </el-form-item>
            <el-form-item prop="password" class="field" label="路演密码">
              <el-input
                v-model="joinForm.password"
                placeholder="密码"
                maxlength="6"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleJoin"
              />
            </el-form-item>
            <div class="field cta-wrap">
              <span class="cta-spacer" aria-hidden="true">进入</span>
              <BaseButton
                type="primary"
                size="large"
                class="join-cta"
                :loading="joining"
                @click="handleJoin"
              >
                进入路演
              </BaseButton>
            </div>
          </div>

          <div class="join-foot">
            <button
              type="button"
              class="remember"
              :class="{ on: rememberCredentials }"
              role="checkbox"
              :aria-checked="rememberCredentials"
              @click="rememberCredentials = !rememberCredentials"
            >
              <span class="box" aria-hidden="true" />
              记住路演号与密码
            </button>
          </div>
        </el-form>
      </section>

      <!-- 进行中扁条 -->
      <section
        v-if="activeRunning"
        class="continue"
        aria-label="进行中的路演"
      >
        <div class="continue-left">
          <i class="led led-pulse" aria-hidden="true" />
          <strong>{{ activeRunning.title }}</strong>
          <small class="n">
            <template v-if="getMeetingCode(activeRunning)">{{ getMeetingCode(activeRunning) }} · </template>
            {{ formatDateTime(activeRunning.joinedAt) }} · 进行中
          </small>
        </div>
        <div class="continue-right">
          <button
            type="button"
            class="btn soft sm"
            @click="copyHistoryInfo(activeRunning)"
          >
            复制号
          </button>
          <button
            type="button"
            class="btn soft sm"
            @click="rejoinMeeting(activeRunning)"
          >
            进入
          </button>
        </div>
      </section>

      <!-- 最近参与与评分报告 -->
      <section
        class="list-card neo-raised"
        :class="{ 'is-report-view': activeContentTab === 'reports' }"
        aria-label="路演记录与评分"
      >
        <div class="content-tabs" role="tablist" aria-label="路演训练内容">
          <button
            id="reports-tab"
            type="button"
            role="tab"
            aria-controls="reports-panel"
            :aria-selected="activeContentTab === 'reports'"
            :class="{ active: activeContentTab === 'reports' }"
            @click="selectContentTab('reports')"
          >
            评分报告
          </button>
          <button
            id="meetings-tab"
            type="button"
            role="tab"
            aria-controls="meetings-panel"
            :aria-selected="activeContentTab === 'meetings'"
            :class="{ active: activeContentTab === 'meetings' }"
            @click="selectContentTab('meetings')"
          >
            路演记录
          </button>
        </div>

        <div
          v-if="activeContentTab === 'meetings'"
          id="meetings-panel"
          role="tabpanel"
          aria-labelledby="meetings-tab"
        >
          <div class="list-head is-filter-only">
            <div class="tabs" role="tablist" aria-label="筛选参与记录">
              <button
                type="button"
                role="tab"
                :class="{ on: historyFilter === 'all' }"
                :aria-selected="historyFilter === 'all'"
                @click="historyFilter = 'all'"
              >
                全部
              </button>
              <button
                type="button"
                role="tab"
                :class="{ on: historyFilter === 'running' }"
                :aria-selected="historyFilter === 'running'"
                @click="historyFilter = 'running'"
              >
                进行中
              </button>
              <button
                type="button"
                role="tab"
                :class="{ on: historyFilter === 'ended' }"
                :aria-selected="historyFilter === 'ended'"
                @click="historyFilter = 'ended'"
              >
                已结束
              </button>
            </div>
          </div>

          <div v-loading="historyLoading" class="list-body">
            <div v-if="!historyLoading && filteredHistory.length === 0" class="list-empty">
              暂无路演记录。加入或发起路演后会出现在这里。
            </div>

            <button
              v-for="item in filteredHistory"
              :key="item.meetingId"
              type="button"
              class="row"
              @click="onRowPrimary(item)"
            >
              <span class="st" :class="statusTone(item.status)">
                <i aria-hidden="true" />
                {{ getStatusText(item.status) }}
              </span>
              <span class="title">{{ item.title }}</span>
              <span class="row-acts" @click.stop>
                <template v-if="item.status === 'RUNNING' || item.status === 'CREATED'">
                  <button type="button" class="act" @click="rejoinMeeting(item)">进入</button>
                </template>
                <template v-else>
                  <button type="button" class="act muted" @click="goAiScore(item)">评分</button>
                  <button type="button" class="act" @click="goToDetail(item)">详情</button>
                </template>
              </span>
              <span class="meta">
                <span v-if="getMeetingCode(item)" class="code">{{ getMeetingCode(item) }}</span>
                <template v-if="getMeetingCode(item)"> · </template>
                {{ formatDateTime(item.joinedAt) }}
              </span>
            </button>
          </div>
        </div>
        <Statistics
          v-else
          id="reports-panel"
          embedded
          role="tabpanel"
          aria-labelledby="reports-tab"
        />
      </section>
    </div>

    <!-- 创建本场：弹窗，全员可建 -->
    <el-dialog
      v-model="createModalOpen"
      title="发起路演"
      width="400px"
      align-center
      class="create-dialog"
      :close-on-click-modal="true"
      @closed="onCreateDialogClosed"
    >
      <p class="dialog-lead">所有人都可以发起。生成路演号后发给队友。</p>

      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-position="top"
        class="create-form"
        @submit.prevent
      >
        <el-form-item label="路演主题" prop="title">
          <el-input
            v-model="createForm.title"
            placeholder="例如：复赛彩排 · 智慧养老"
            maxlength="40"
            size="large"
            :prefix-icon="VideoCamera"
          />
        </el-form-item>

        <div class="duration">
          <div>
            <span>预计时长</span>
            <small>5–480 分钟</small>
          </div>
          <div class="ctrl">
            <button type="button" class="step" aria-label="减少 5 分钟" @click="adjustDuration(-5)">−</button>
            <div class="val n">{{ createForm.durationMinutes }}</div>
            <button type="button" class="step" aria-label="增加 5 分钟" @click="adjustDuration(5)">+</button>
          </div>
        </div>

        <div class="checks">
          <button
            type="button"
            class="check"
            :class="{ on: createOptions.autoRecord }"
            @click="createOptions.autoRecord = !createOptions.autoRecord"
          >
            <span class="dot" />
            路演中自动录制（便于回放与评分）
          </button>
          <button
            type="button"
            class="check"
            :class="{ on: createOptions.guideScore }"
            @click="createOptions.guideScore = !createOptions.guideScore"
          >
            <span class="dot" />
            结束后引导生成 AI 评分
          </button>
          <button
            type="button"
            class="check"
            :class="{ on: createOptions.membersOnly }"
            @click="createOptions.membersOnly = !createOptions.membersOnly"
          >
            <span class="dot" />
            仅项目成员可加入
          </button>
        </div>
      </el-form>

      <template #footer>
        <button type="button" class="btn soft" @click="createModalOpen = false">取消</button>
        <BaseButton type="primary" :loading="creating" @click="handleCreate">
          发起并进入
        </BaseButton>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoCamera, Grid, Lock } from '@element-plus/icons-vue'
import request from '../utils/request'
import { BaseButton } from '../components/base'
import Statistics from './Statistics.vue'

const router = useRouter()
const route = useRoute()

const joinFormRef = ref(null)
const joining = ref(false)
const rememberCredentials = ref(true)

const joinForm = reactive({
  meetingCode: '',
  password: ''
})

const joinRules = {
  meetingCode: [
    { required: true, message: '请输入路演号', trigger: 'blur' },
    { len: 6, message: '路演号为 6 位数字', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入路演密码', trigger: 'blur' }
  ]
}

const createModalOpen = ref(false)
const createFormRef = ref(null)
const creating = ref(false)

const createForm = reactive({
  title: '',
  durationMinutes: 60
})

const createOptions = reactive({
  autoRecord: true,
  guideScore: true,
  membersOnly: false
})

const createRules = {
  title: [
    { required: true, message: '请输入路演主题', trigger: 'blur' },
    { min: 2, max: 40, message: '主题为 2-40 个字符', trigger: 'blur' }
  ]
}

const historyLoading = ref(false)
const historyList = ref([])
const historyFilter = ref('all')

const activeContentTab = computed(() =>
  route.query.tab === 'meetings' ? 'meetings' : 'reports'
)

function selectContentTab(tab) {
  const canonicalTab = tab === 'reports' ? 'reports' : 'meetings'
  if (route.query.tab === canonicalTab) return
  router.push({
    query: {
      ...route.query,
      tab: canonicalTab
    }
  })
}

const filteredHistory = computed(() => {
  const list = historyList.value
  if (historyFilter.value === 'running') {
    return list.filter((item) => item.status === 'RUNNING' || item.status === 'CREATED')
  }
  if (historyFilter.value === 'ended') {
    return list.filter((item) => item.status === 'ENDED')
  }
  return list
})

const activeRunning = computed(() =>
  historyList.value.find((item) => item.status === 'RUNNING') || null
)

function adjustDuration(delta) {
  const current = Number(createForm.durationMinutes) || 60
  createForm.durationMinutes = Math.min(480, Math.max(5, current + delta))
}

function openCreateModal() {
  createModalOpen.value = true
}

function onCreateDialogClosed() {
  createFormRef.value?.clearValidate?.()
}

const openMeetingRoom = (meetingId) => {
  if (!meetingId) return
  router.push(`/meeting/${meetingId}`)
}

const setVerifiedMeetingAccess = (meetingId) => {
  const access = {
    meetingId: String(meetingId),
    verifiedAt: Date.now()
  }
  localStorage.setItem('verifiedMeetingAccess', JSON.stringify(access))
  sessionStorage.setItem('verifiedMeetingId', String(meetingId))
}

onMounted(() => {
  const queryCode = String(route.query.meetingCode || '')
  const queryPassword = String(route.query.password || '')
  const savedCode = localStorage.getItem('savedMeetingCode')
  const savedPwd = localStorage.getItem('savedPassword')
  if (queryCode) joinForm.meetingCode = queryCode
  else if (savedCode) joinForm.meetingCode = savedCode

  if (queryPassword) joinForm.password = queryPassword
  else if (savedPwd) joinForm.password = savedPwd

  fetchHistory()
})

const onCodeInput = () => {
  const savedPairs = JSON.parse(localStorage.getItem('meetingCredentials') || '{}')
  if (savedPairs[joinForm.meetingCode]) {
    joinForm.password = savedPairs[joinForm.meetingCode]
  }
}

const persistCredentials = (code, password) => {
  if (!rememberCredentials.value) {
    localStorage.removeItem('savedMeetingCode')
    localStorage.removeItem('savedPassword')
    return
  }
  localStorage.setItem('savedMeetingCode', code)
  localStorage.setItem('savedPassword', password)
  const savedPairs = JSON.parse(localStorage.getItem('meetingCredentials') || '{}')
  savedPairs[code] = password
  localStorage.setItem('meetingCredentials', JSON.stringify(savedPairs))
}

const handleJoin = async () => {
  if (!joinFormRef.value) return
  await joinFormRef.value.validate(async (valid) => {
    if (!valid) return
    joining.value = true
    try {
      const res = await request.post('/api/meeting/join-by-code', {
        meetingCode: joinForm.meetingCode,
        password: joinForm.password
      })
      const data = res.data || res
      persistCredentials(joinForm.meetingCode, joinForm.password)
      ElMessage.success('正在加入路演...')
      setVerifiedMeetingAccess(data.meetingId)
      openMeetingRoom(data.meetingId)
      fetchHistory()
    } catch {
      // interceptor
    } finally {
      joining.value = false
    }
  })
}

const handleCreate = async () => {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    const res = await request.post('/api/meeting/create', {
      title: createForm.title.trim(),
      durationMinutes: createForm.durationMinutes
      // autoRecord / guideScore / membersOnly 为前端偏好位，后端尚未字段时先不传
    })
    const data = res.data || res
    const code = data.meetingCode || ''
    const pwd = data.meetingPassword || ''
    if (code) joinForm.meetingCode = code
    if (pwd) joinForm.password = pwd
    if (code && pwd) persistCredentials(code, pwd)

    ElMessage.success('路演已发起')
    createModalOpen.value = false
    Object.assign(createForm, { title: '', durationMinutes: 60 })
    createFormRef.value?.clearValidate?.()

    if (data.meetingId || data.id) {
      const meetingId = data.meetingId || data.id
      setVerifiedMeetingAccess(meetingId)
      openMeetingRoom(meetingId)
    }
    fetchHistory()
  } catch {
    // interceptor
  } finally {
    creating.value = false
  }
}

const getSavedMeetingPassword = (meetingCode) => {
  if (!meetingCode) return ''
  try {
    const savedPairs = JSON.parse(localStorage.getItem('meetingCredentials') || '{}')
    return savedPairs[meetingCode] || ''
  } catch {
    return ''
  }
}

const getMeetingCode = (item) =>
  item?.meetingCode || item?.meeting_code || item?.code || ''

const getMeetingPassword = (item) => {
  const meetingCode = getMeetingCode(item)
  return (
    item?.meetingPassword ||
    item?.meeting_password ||
    item?.joinCredential ||
    item?.join_credential ||
    item?.password ||
    getSavedMeetingPassword(meetingCode) ||
    ''
  )
}

const buildJoinUrl = (item) => {
  const params = new URLSearchParams()
  const meetingCode = getMeetingCode(item)
  const password = getMeetingPassword(item)
  if (meetingCode) params.set('meetingCode', meetingCode)
  if (password) params.set('password', password)
  return `${window.location.origin}/online-meeting${params.toString() ? `?${params.toString()}` : ''}`
}

const writeClipboard = async (text) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

const copyHistoryInfo = async (item) => {
  const meetingCode = getMeetingCode(item)
  const password = getMeetingPassword(item)
  const text = [
    `路演名称：${item.title || '-'}`,
    `路演号：${meetingCode || '-'}`,
    `路演密码：${password || '-'}`,
    `加入地址：${buildJoinUrl(item)}`
  ].join('\n')

  try {
    await writeClipboard(text)
    ElMessage.success(meetingCode ? '路演号等信息已复制' : '路演信息已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

const rejoinMeeting = async (item) => {
  const code = getMeetingCode(item)
  const pwd = getMeetingPassword(item)
  if (code && pwd) {
    joinForm.meetingCode = code
    joinForm.password = pwd
    await handleJoin()
    return
  }
  if (item.meetingId) {
    setVerifiedMeetingAccess(item.meetingId)
    openMeetingRoom(item.meetingId)
    return
  }
  ElMessage.warning('缺少路演号或密码，请手动填写后加入')
}

const fetchHistory = async () => {
  historyLoading.value = true
  try {
    const res = await request.get('/api/meeting/my-history')
    historyList.value = Array.isArray(res) ? res : (res.data || [])
  } catch (error) {
    console.error('获取参与记录失败:', error)
  } finally {
    historyLoading.value = false
  }
}

const goToDetail = (item) => {
  router.push(`/meeting-history/${item.meetingId}`)
}

const goAiScore = (item) => {
  const id = item?.meetingId || item?.id
  if (!id) return
  router.push(`/ai-score/${id}`)
}

const goRecordings = () => {
  router.push('/my-recordings')
}

const onRowPrimary = (item) => {
  if (item.status === 'RUNNING' || item.status === 'CREATED') {
    rejoinMeeting(item)
  } else {
    goToDetail(item)
  }
}

const getStatusText = (status) => {
  const map = { CREATED: '待开始', RUNNING: '进行中', ENDED: '已结束' }
  return map[status] || status
}

const statusTone = (status) => {
  if (status === 'RUNNING') return 'live'
  if (status === 'CREATED') return 'ready'
  return 'done'
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return '-'
  const now = new Date()
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  if (sameDay) {
    return `今天 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped>
.roadshow-page {
  --canvas: #ffffff;
  --ink: var(--ds-ink, #12141a);
  --ink-2: var(--ds-ink-2, #2c3038);
  --muted: #7a7580;
  --faint: #a39aa3;
  --line: rgba(120, 90, 70, 0.08);
  --line-strong: rgba(120, 90, 70, 0.12);
  --orange: var(--ds-orange, #e84a1c);
  --orange-deep: var(--ds-orange-deep, #c43a12);
  --orange-wash: #fff4ee;
  --green: var(--ds-green, #0f9f6e);
  --font: var(--ds-font-sans, "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", system-ui, sans-serif);
  --num: var(--ds-font-num, "DIN Alternate", "SF Pro Text", "Helvetica Neue", Arial, sans-serif);
  --max: var(--ds-page-max, 1280px);
  --neo-dark: rgba(232, 74, 28, 0.05);
  --neo-dark-soft: rgba(232, 74, 28, 0.03);

  color: var(--ink);
  font-family: var(--font);
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
  /* 用户端页面底：纯白，无渐变 */
  background-color: #ffffff;
  background-image: none;
  /* 整页不滚：占满主栏高度，列表区内滚 */
  height: calc(100vh - var(--workspace-header-height, 64px));
  max-height: calc(100vh - var(--workspace-header-height, 64px));
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px) 40px;
}

.roadshow-page :deep(em),
.roadshow-page :deep(i) {
  font-style: normal;
}

.page-inner {
  max-width: none;
  width: 100%;
  margin: 0;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.n {
  font-family: var(--num);
  font-variant-numeric: tabular-nums;
}

/* 对齐 biji：白底 + #e2e4ea 线 + 轻 elevation */
.neo-raised {
  background: #ffffff;
  border: 1px solid var(--ds-card-border, #e2e4ea);
  border-radius: var(--ds-card-radius, 14px);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: none;
}

.led {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #c5c9d1;
}
.led-ok {
  background: var(--green);
  box-shadow: 0 0 0 2px rgba(15, 159, 110, 0.14);
}
.led-pulse {
  background: var(--green);
  box-shadow: 0 0 0 0 rgba(15, 159, 110, 0.35);
  animation: ledPulse 2.4s ease infinite;
}
@keyframes ledPulse {
  0% { box-shadow: 0 0 0 0 rgba(15, 159, 110, 0.35); }
  70% { box-shadow: 0 0 0 6px rgba(15, 159, 110, 0); }
  100% { box-shadow: 0 0 0 0 rgba(15, 159, 110, 0); }
}

/* 页头 */
.page-head {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.page-head h1 {
  margin: 0;
  font-size: var(--ds-text-h1, clamp(22px, 1.8vw, 28px));
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
}
.page-head .sub {
  margin: 4px 0 0;
  font-size: 13.5px;
  color: var(--muted);
  font-weight: 500;
  line-height: 1.4;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.5);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
}

/* 按钮 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 0;
  background: none;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 700;
  color: inherit;
  cursor: pointer;
}
.btn.soft {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--line-strong);
  color: var(--ink-2);
  font-weight: 600;
}
.btn.soft:hover {
  color: var(--orange-deep);
  border-color: rgba(232, 74, 28, 0.22);
}
.btn.sm {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
}

/*
  主卡：对齐首页项目卡的软渐变
  左暖桃 → 右近白，顶部细橙线点缀；整体仍浅、不突兀
*/
.join-card {
  position: relative;
  flex-shrink: 0;
  padding: 18px 20px 14px;
  margin-bottom: 10px;
  border-radius: 16px;
  overflow: hidden;
  background:
    radial-gradient(ellipse 55% 90% at 0% 30%, rgba(255, 200, 165, 0.28), transparent 58%),
    linear-gradient(
      105deg,
      #fff0e6 0%,
      #fff5ee 32%,
      #fffcfa 62%,
      #ffffff 100%
    );
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow:
    0 12px 32px rgba(232, 74, 28, 0.06),
    0 2px 10px rgba(232, 74, 28, 0.035),
    inset 0 1px 0 rgba(255, 255, 255, 0.95);
}
/* 与首页项目卡同款：顶边左侧细橙条 */
.join-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: min(36%, 220px);
  height: 3px;
  border-radius: 16px 0 8px 0;
  background: linear-gradient(90deg, #e84a1c 0%, #f08a5a 55%, transparent 100%);
  pointer-events: none;
}
.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.title-block {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.join-mark {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--orange);
  background: var(--orange-wash);
  border: 1px solid rgba(232, 74, 28, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}
.join-mark svg {
  width: 24px;
  height: 24px;
}
.title-copy {
  min-width: 0;
}
.eyebrow {
  display: block;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--orange-deep);
  margin-bottom: 3px;
}
.join-card h2 {
  margin: 0;
  font-size: clamp(18px, 1.6vw, 22px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--ink);
}
.hint {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
  flex-shrink: 0;
}

.join-form {
  width: 100%;
}
.fields {
  display: grid;
  grid-template-columns: 1fr 1fr minmax(132px, auto);
  gap: 12px 12px;
  align-items: start;
}
.field {
  margin-bottom: 0 !important;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
/* 强制顶置标签，避免与输入框重叠 */
.field :deep(.el-form-item__label) {
  position: static !important;
  float: none !important;
  display: block !important;
  width: auto !important;
  max-width: none !important;
  margin: 0 0 6px !important;
  padding: 0 !important;
  height: auto !important;
  line-height: 1.3 !important;
  font-size: 12.5px !important;
  font-weight: 700 !important;
  color: var(--ink-2) !important;
  text-align: left !important;
  justify-content: flex-start !important;
}
.field :deep(.el-form-item__label .el-form-item__asterisk),
.field :deep(.el-form-item.is-required:not(.is-no-asterisk) > .el-form-item__label::before) {
  color: var(--orange) !important;
}
.field :deep(.el-form-item__label-wrap) {
  margin: 0 !important;
}
.field :deep(.el-form-item__content) {
  display: block;
  line-height: normal;
  margin-left: 0 !important;
}
.field :deep(.el-input) {
  width: 100%;
}
.field :deep(.el-input__wrapper) {
  height: 46px;
  padding: 0 14px;
  border-radius: 12px;
  background: #fff !important;
  box-shadow:
    0 0 0 1px rgba(120, 90, 70, 0.12),
    0 1px 2px rgba(40, 30, 24, 0.03) !important;
}
.field :deep(.el-input__wrapper:hover) {
  box-shadow:
    0 0 0 1px rgba(120, 90, 70, 0.18),
    0 1px 2px rgba(40, 30, 24, 0.03) !important;
}
.field :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(232, 74, 28, 0.4),
    0 0 0 3px rgba(232, 74, 28, 0.1) !important;
}
.field :deep(.el-input__inner) {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--ink);
  height: 100%;
}
.field :deep(.el-input__prefix) {
  color: var(--faint);
}
.field :deep(.el-form-item__error) {
  position: static;
  padding-top: 4px;
  font-size: 12px;
}

.cta-wrap {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-width: 0;
}
/* 与左侧 label 等高，保证按钮与输入框底对齐 */
.cta-spacer {
  display: block;
  margin-bottom: 6px;
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1.3;
  color: transparent;
  user-select: none;
  pointer-events: none;
}
.join-cta {
  height: 46px !important;
  min-width: 132px;
  width: 100%;
  padding: 0 22px !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  border-radius: 999px !important;
  box-shadow: 0 10px 22px rgba(232, 74, 28, 0.22) !important;
}
.join-cta:hover {
  transform: translateY(-1px);
}

.join-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  gap: 8px 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(120, 90, 70, 0.08);
}
.remember {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 0;
  background: none;
  padding: 0;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
}
.remember .box {
  width: 15px;
  height: 15px;
  border-radius: 4px;
  border: 1.5px solid var(--line-strong);
  background: #fff;
  position: relative;
}
.remember.on .box {
  background: var(--orange);
  border-color: var(--orange);
}
.remember.on .box::after {
  content: "";
  position: absolute;
  left: 4px;
  top: 1px;
  width: 4px;
  height: 8px;
  border: solid #fff;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg);
}
/* 进行中 */
.continue {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  padding: 8px 12px;
  margin-bottom: 10px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid var(--line);
}
.continue-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.continue strong {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.continue small {
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.continue-right {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

/* 最近列表：占满剩余高度，仅 body 滚动 */
.list-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 4px 6px 6px;
  overflow: hidden;
}
.list-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 10px 6px;
}
.list-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-2);
}
.tabs {
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.5);
}
.tabs button {
  height: 26px;
  padding: 0 10px;
  border: 0;
  border-radius: 999px;
  background: none;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
}
.tabs button.on {
  background: var(--ink);
  color: #fff;
  font-weight: 700;
}
.list-body {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  padding-bottom: 4px;
}
.list-body :deep(.el-loading-mask) {
  border-radius: 10px;
}
.list-empty {
  padding: 28px 12px;
  text-align: center;
  font-size: 13px;
  color: var(--faint);
  font-weight: 500;
}
.row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  gap: 4px 10px;
  align-items: center;
  width: 100%;
  text-align: left;
  padding: 9px 10px;
  border: 0;
  border-radius: 10px;
  background: none;
  font-family: inherit;
  color: inherit;
  cursor: pointer;
}
.row:hover {
  background: rgba(255, 255, 255, 0.35);
}
.row:hover .title {
  color: var(--orange);
}
.st {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--muted);
}
.st i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #c5c9d1;
}
.st.live {
  color: var(--green);
}
.st.live i {
  background: var(--green);
  box-shadow: 0 0 0 2px rgba(15, 159, 110, 0.12);
}
.st.ready {
  color: var(--orange-deep);
}
.st.ready i {
  background: var(--orange);
}
.st.done i {
  background: #c5c9d1;
}
.title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  grid-column: 2;
  font-size: 12px;
  color: var(--faint);
  font-weight: 500;
}
.code {
  font-family: var(--num);
  font-size: 12px;
  font-weight: 700;
  color: var(--orange-deep);
}
.row-acts {
  grid-row: 1 / 3;
  grid-column: 3;
  display: flex;
  align-items: center;
  gap: 6px;
}
.row-acts .act {
  border: 0;
  background: none;
  padding: 4px 2px;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--orange);
  white-space: nowrap;
  cursor: pointer;
}
.row-acts .act.muted {
  color: var(--muted);
  font-weight: 600;
}
.row-acts .act.muted:hover {
  color: var(--orange);
}

/* 创建弹窗 */
.dialog-lead {
  margin: -4px 0 14px;
  font-size: 12.5px;
  color: var(--muted);
  font-weight: 500;
  line-height: 1.45;
}
.create-form :deep(.el-form-item__label) {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-2);
  margin-bottom: 5px !important;
  padding: 0 !important;
  height: auto !important;
  line-height: 1.3 !important;
}
.create-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9) !important;
  box-shadow: 0 0 0 1px var(--line-strong) !important;
}
.create-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(232, 74, 28, 0.4),
    0 0 0 3px rgba(232, 74, 28, 0.08) !important;
}
.duration {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 11px;
  border-radius: 10px;
  background: rgba(255, 248, 244, 0.65);
  border: 1px solid var(--line);
  margin-bottom: 12px;
}
.duration span {
  font-size: 13px;
  font-weight: 700;
}
.duration small {
  display: block;
  font-size: 11px;
  color: var(--faint);
  font-weight: 500;
}
.duration .ctrl {
  display: flex;
  align-items: center;
  gap: 4px;
}
.duration .step {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid var(--line-strong);
  background: #fff;
  font-weight: 700;
  font-size: 14px;
  font-family: inherit;
  color: var(--ink-2);
  cursor: pointer;
}
.duration .val {
  min-width: 56px;
  text-align: center;
  font-family: var(--num);
  font-size: 16px;
  font-weight: 800;
}
.checks {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 4px;
}
.check {
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
  width: 100%;
  padding: 8px 10px;
  border-radius: 9px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.45);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-2);
  cursor: pointer;
}
.check.on {
  background: var(--orange-wash);
  border-color: rgba(232, 74, 28, 0.08);
}
.check .dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1.5px solid var(--line-strong);
  flex-shrink: 0;
}
.check.on .dot {
  background: var(--orange);
  border-color: var(--orange);
  box-shadow: inset 0 0 0 2px #fff;
}

:deep(.create-dialog) {
  border-radius: 16px;
  overflow: hidden;
}
:deep(.create-dialog .el-dialog__header) {
  padding: 18px 18px 0;
  margin: 0;
}
:deep(.create-dialog .el-dialog__title) {
  font-size: 17px;
  font-weight: 800;
  color: var(--ink);
}
:deep(.create-dialog .el-dialog__body) {
  padding: 8px 18px 4px;
}
:deep(.create-dialog .el-dialog__footer) {
  padding: 8px 18px 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
:deep(.create-dialog .el-dialog) {
  background: var(--ds-surface-solid, #fff);
  border: 1px solid var(--ds-line, rgba(28, 26, 22, 0.09));
  box-shadow: var(--ds-shadow-soft, 0 18px 48px rgba(28, 26, 22, 0.14));
}

/* Roadshow visual system: keep the existing structure and behavior, only
   converge colors, surfaces and control states with the student home. */
.roadshow-page {
  --muted: var(--ds-muted, #6b7280);
  --faint: var(--ds-faint, #9aa1ad);
  --line: var(--ds-line, rgba(28, 26, 22, 0.09));
  --line-strong: var(--ds-line-strong, rgba(28, 26, 22, 0.13));
  --orange: var(--ds-orange-action, #cf3d12);
  --orange-deep: var(--ds-orange-800, #b12f0a);
  --orange-wash: var(--ds-orange-50, #fff7f2);
  background: transparent;
}

.neo-raised,
.join-card,
.continue,
.list-card {
  border: 1px solid var(--ds-card-border, var(--line));
  background: var(--ds-card-bg, var(--ds-surface, rgba(255, 255, 255, 0.9)));
  box-shadow: var(--ds-card-shadow, none);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.join-card {
  border-radius: var(--ds-radius-lg, 16px);
}

.join-card::before {
  display: none;
}

.join-mark {
  color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-50, #fff7f2);
  border-color: var(--ds-orange-100, #fee9df);
  box-shadow: none;
}

.live-pill,
.tabs {
  border-color: var(--line);
  background: var(--ds-surface-solid, #fff);
}

.btn,
.tabs button,
.row-acts .act,
.remember,
.duration .step,
.check {
  transition: color 150ms ease-in-out, background-color 150ms ease-in-out, border-color 150ms ease-in-out;
}

.btn.soft {
  height: 34px;
  padding: 0 14px;
  color: var(--ds-ink-2, #2c3038);
  border: 1px solid var(--ds-btn-secondary-border, var(--line-strong));
  background: var(--ds-btn-secondary-bg, var(--ds-surface-solid, #fff));
}

.btn.soft:hover {
  color: var(--ds-orange-800, #b12f0a);
  border-color: var(--ds-orange-action, #cf3d12);
  background: var(--ds-orange-50, #fff7f2);
}

.btn:focus-visible,
.tabs button:focus-visible,
.row:focus-visible,
.row-acts .act:focus-visible,
.remember:focus-visible,
.duration .step:focus-visible,
.check:focus-visible {
  outline: 2px solid var(--ds-orange-action, #cf3d12);
  outline-offset: 2px;
}

.field :deep(.el-input__wrapper),
.create-form :deep(.el-input__wrapper) {
  height: 44px;
  padding: 0 14px;
  border-radius: var(--ds-input-radius, 12px);
  background: var(--ds-input-bg, var(--ds-surface-solid, #fff)) !important;
  box-shadow: 0 0 0 1px var(--ds-input-border, var(--line-strong)) !important;
}

.field :deep(.el-input__wrapper:hover),
.create-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--ds-input-border-hover, rgba(28, 26, 22, 0.2)) !important;
}

.field :deep(.el-input__wrapper.is-focus),
.create-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--ds-orange-action, #cf3d12), 0 0 0 3px rgba(207, 61, 18, 0.12) !important;
}

.join-cta {
  height: 44px !important;
  color: var(--ds-btn-primary-fg, #fffaf7) !important;
  background: var(--ds-btn-primary-bg, var(--ds-orange-action, #cf3d12)) !important;
  border-color: var(--ds-btn-primary-bg, var(--ds-orange-action, #cf3d12)) !important;
  box-shadow: none !important;
}

.join-cta:hover {
  color: var(--ds-btn-primary-fg, #fffaf7) !important;
  background: var(--ds-btn-primary-bg-hover, var(--ds-orange-700, #c2370e)) !important;
  border-color: var(--ds-btn-primary-bg-hover, var(--ds-orange-700, #c2370e)) !important;
  transform: none;
}

.join-cta:active {
  background: var(--ds-btn-primary-bg-active, var(--ds-orange-800, #b12f0a)) !important;
  border-color: var(--ds-btn-primary-bg-active, var(--ds-orange-800, #b12f0a)) !important;
}

.remember.on .box,
.check.on .dot {
  background: var(--ds-orange-action, #cf3d12);
  border-color: var(--ds-orange-action, #cf3d12);
}

.continue {
  border-radius: var(--ds-radius-md, 12px);
}

.tabs button.on {
  color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-50, #fff7f2);
  box-shadow: inset 0 0 0 1px var(--ds-orange-100, #fee9df);
}

.row:hover {
  background: var(--ds-orange-50, #fff7f2);
}

.row:hover .title,
.row-acts .act {
  color: var(--ds-orange-800, #b12f0a);
}

.duration,
.check.on {
  background: var(--ds-orange-50, #fff7f2);
  border-color: var(--ds-orange-100, #fee9df);
}

.check {
  background: var(--ds-surface-solid, #fff);
  border-color: var(--line);
}

:deep(.create-dialog) {
  border-radius: var(--ds-radius-lg, 16px);
}

@media (max-width: 640px) {
  .roadshow-page {
    height: auto;
    max-height: none;
    overflow: visible;
    min-height: 100%;
  }
  .page-inner {
    overflow: visible;
  }
  .list-card {
    flex: none;
    max-height: min(52vh, 420px);
  }
  .fields {
    grid-template-columns: 1fr;
  }
  .cta-spacer {
    display: none;
  }
  .cta-wrap :deep(.base-button),
  .join-cta {
    width: 100%;
  }
  .label-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .page-head {
    align-items: flex-start;
    flex-shrink: 0;
  }
  .join-card,
  .continue {
    flex-shrink: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .led-pulse {
    animation: none;
  }
  .join-cta:hover {
    transform: none;
  }
}
</style>

<style scoped>
/* Final workspace alignment: page spacing belongs to WorkspaceShell. */
.roadshow-page {
  width: 100%;
  min-height: 100%;
  height: auto;
  max-height: none;
  padding: 0 0 var(--ds-space-6, 24px);
  overflow: visible;
  color: var(--ds-ink);
  background: transparent;
}

.page-inner {
  display: block;
  min-height: 0;
  overflow: visible;
}

.page-head {
  align-items: flex-end;
  margin: 0 0 var(--ds-space-5, 20px);
  padding: 0;
  border: 0;
}

.page-head h1 {
  font-size: var(--ds-text-h1, 28px);
  letter-spacing: -0.02em;
}

.page-head .sub {
  margin-top: 6px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption, 13px);
}

.head-actions {
  gap: var(--ds-space-2, 8px);
}

.head-actions :deep(.base-button) {
  height: var(--ds-btn-height, 40px);
}

.live-pill {
  height: 36px;
  padding: 0 12px;
  color: var(--ds-muted);
  border: 0;
  background: transparent;
}

.btn.soft,
.btn.soft.sm {
  height: 40px;
  padding: 0 16px;
  color: var(--ds-ink-2);
  border: 1px solid var(--ds-btn-secondary-border);
  background: var(--ds-btn-secondary-bg);
}

.join-card {
  margin: 0;
  padding: var(--ds-space-6, 24px);
  overflow: visible;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: none;
}

.label-row {
  margin-bottom: var(--ds-space-5, 20px);
}

.join-mark {
  width: 48px;
  height: 48px;
  border-radius: var(--ds-radius-md);
}

.join-card h2 {
  font-size: var(--ds-text-h2, 22px);
}

.hint {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption, 13px);
}

.fields {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 148px;
  gap: var(--ds-space-4, 16px);
}

.field :deep(.el-input__wrapper) {
  height: var(--ds-input-height, 44px);
}

.field :deep(.el-input__inner) {
  font-size: 15px;
  letter-spacing: 0.02em;
}

.join-cta {
  min-width: 148px;
  height: var(--ds-input-height, 44px) !important;
}

.join-foot {
  margin-top: var(--ds-space-4, 16px);
  padding-top: var(--ds-space-4, 16px);
  border-top-color: var(--ds-line);
}

.remember {
  min-height: 40px;
}

.continue {
  margin: var(--ds-space-4, 16px) 0 0;
  padding: 12px 16px;
  border-color: rgba(15, 159, 110, 0.18);
  background: var(--ds-status-success-bg);
}

.list-card {
  display: block;
  min-height: 0;
  margin-top: var(--ds-space-4, 16px);
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: none;
}

.content-tabs {
  min-height: 56px;
  padding: 0 var(--ds-space-6, 24px);
  border-bottom: 1px solid var(--ds-line);
  display: flex;
  align-items: flex-end;
  gap: var(--ds-space-6, 24px);
  background: var(--ds-card-bg);
}

.content-tabs button {
  min-height: 56px;
  padding: 0 2px;
  border: 0;
  border-bottom: 3px solid transparent;
  background: transparent;
  color: var(--ds-muted);
  font: inherit;
  font-size: var(--ds-text-body-sm);
  font-weight: var(--ds-weight-bold);
  cursor: pointer;
}

.content-tabs button.active {
  border-bottom-color: var(--ds-orange-action);
  color: var(--ds-ink);
}

.content-tabs button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: -4px;
}

.list-head {
  padding: var(--ds-space-5, 20px) var(--ds-space-6, 24px);
  border-bottom: 1px solid var(--ds-line);
}

.list-head.is-filter-only {
  justify-content: flex-start;
}

.list-head h2 {
  color: var(--ds-ink);
  font-size: var(--ds-text-h3, 16px);
}

.list-head p {
  margin: 5px 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-label, 12px);
}

.tabs {
  padding: 3px;
  border-color: var(--ds-line);
  background: var(--ds-input-readonly-bg);
}

.tabs button {
  min-height: 32px;
  height: 32px;
  padding: 0 12px;
}

.list-body {
  min-height: 160px;
  max-height: 360px;
  overflow-x: hidden;
  overflow-y: auto;
}

.list-empty {
  min-height: 160px;
  padding: 56px 24px;
  display: grid;
  place-items: center;
  color: var(--ds-muted);
}

.row {
  min-height: 68px;
  padding: 13px var(--ds-space-6, 24px);
  border-radius: 0;
  border-bottom: 1px solid var(--ds-line);
}

.row:last-child {
  border-bottom: 0;
}

.row:hover {
  background: var(--ds-orange-wash);
}

.row-acts .act {
  min-height: 36px;
  padding: 0 8px;
}

@media (max-width: 820px) {
  .fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cta-wrap {
    grid-column: 1 / -1;
  }

  .cta-spacer {
    display: none;
  }

  .join-cta {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .list-card.is-report-view {
    max-height: none;
    overflow: visible;
  }

  .content-tabs {
    padding: 0 var(--ds-space-4, 16px);
  }

  .content-tabs button {
    flex: 1;
  }

  .page-head,
  .label-row,
  .list-head,
  .join-foot {
    align-items: flex-start;
    flex-direction: column;
  }

  .head-actions,
  .head-actions :deep(.base-button),
  .head-actions .btn {
    width: 100%;
  }

  .live-pill {
    width: auto;
  }

  .fields {
    grid-template-columns: 1fr;
  }

  .cta-wrap {
    grid-column: auto;
  }

  .join-card {
    padding: var(--ds-space-5, 20px);
  }

  .tabs {
    width: 100%;
  }

  .tabs button {
    flex: 1;
  }

  .row {
    grid-template-columns: 68px minmax(0, 1fr);
  }

  .row-acts {
    grid-column: 2;
    grid-row: auto;
    justify-content: flex-start;
  }
}
</style>
