<template>
  <div class="profile-dashboard student-page">
    <header class="student-page__head">
      <div>
        <h1>个人中心</h1>
        <p>查看学习投入、成长记录和老师反馈。</p>
      </div>
    </header>

    <section v-if="loading" class="student-card profile-loading">
      <el-skeleton :rows="12" animated />
    </section>

    <section v-else-if="error" class="student-card profile-state">
      <WarningFilled />
      <h2>个人中心暂时没有加载出来</h2>
      <p>{{ error }}</p>
      <button class="student-primary-btn" type="button" @click="load">重新加载</button>
    </section>

    <template v-else>
      <section class="student-card profile-identity">
        <div class="profile-identity__person">
          <span class="profile-avatar">{{ initial }}</span>
          <div>
            <div class="profile-name">
              <h2>{{ profile.username || '同学' }}</h2>
              <span v-if="profile.positionName || profile.teamRole">{{ profile.positionName || roleLabel(profile.teamRole) }}</span>
            </div>
            <p>{{ [profile.teamName, profile.schoolName, profile.collegeName].filter(Boolean).join(' · ') || '尚未关联团队信息' }}</p>
            <small><i></i>今天已学习 {{ formatDuration(summary.todaySeconds) }}</small>
          </div>
        </div>

        <div class="profile-stats">
          <div v-for="item in statisticItems" :key="item.label">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </section>

      <section class="student-card profile-roadshow" aria-label="团队路演评分">
        <div>
          <h2>团队路演评分</h2>
          <p v-if="roadshow.hasReport">任意队员或老师上传的评分，全队档案同步显示。</p>
          <p v-else>团队完成路演评分后，分数会出现在每位队员的档案里。</p>
        </div>
        <div class="profile-roadshow__score">
          <strong>{{ roadshow.hasReport ? formatScore(roadshow.overallScore) : '—' }}</strong>
          <span>{{ roadshow.hasReport ? '官方综合分' : '暂无评分' }}</span>
        </div>
        <router-link
          v-if="roadshowLink"
          class="student-secondary-btn"
          :to="roadshowLink"
        >查看报告</router-link>
      </section>

      <div class="profile-learning-grid">
        <section class="student-card profile-panel profile-activity">
          <div class="profile-panel__head">
            <div>
              <h2>学习活动</h2>
              <p>近一年累计学习 {{ formatDuration(summary.totalSeconds) }}</p>
            </div>
            <div class="profile-segmented" role="tablist" aria-label="学习活动粒度">
              <button
                v-for="item in heatmapModes"
                :key="item.value"
                type="button"
                role="tab"
                :aria-selected="heatmapMode === item.value"
                :class="{ 'is-active': heatmapMode === item.value }"
                @click="heatmapMode = item.value"
              >
                {{ item.label }}
              </button>
            </div>
          </div>

          <div class="profile-heatmap-shell">
            <div class="profile-heatmap-labels">
              <span v-for="label in heatmapMonthLabels" :key="label.key" :style="{ gridColumn: label.column }">{{ label.text }}</span>
            </div>
            <div
              class="profile-heatmap"
              :class="{ 'is-aggregate': heatmapMode !== 'daily' }"
              :style="{ '--heatmap-columns': heatmapColumns }"
              aria-label="学习时长热力图"
            >
              <button
                v-for="item in visibleHeatmap"
                :key="item.key"
                class="profile-heat-cell"
                :class="`level-${item.level}`"
                type="button"
                :aria-label="item.tooltip"
                :data-tooltip="item.tooltip"
              ></button>
            </div>
          </div>
          <div class="profile-heat-legend">
            <span>少</span><i class="level-0"></i><i class="level-1"></i><i class="level-2"></i><i class="level-3"></i><i class="level-4"></i><span>多</span>
          </div>
        </section>

        <aside class="student-card profile-panel profile-distribution">
          <div class="profile-panel__head">
            <div>
              <h2>学习时长分布</h2>
              <p>累计 {{ formatDuration(summary.totalSeconds) }} · 全量计入</p>
            </div>
          </div>
          <div class="distribution-track" aria-label="学习时长分布">
            <span
              v-for="item in activeDistributionItems"
              :key="item.activityType"
              :class="`is-${item.activityType.toLowerCase()}`"
              :style="{ width: `${Math.max(item.percent, 0.8)}%` }"
              :title="`${activityLabel(item.activityType)} ${formatDuration(item.durationSeconds)}`"
            ></span>
          </div>
          <div class="distribution-list">
            <div
              v-for="item in visibleDistributionItems"
              :key="item.activityType"
              :class="{ 'is-empty': !item.durationSeconds }"
            >
              <i :class="`is-${item.activityType.toLowerCase()}`"></i>
              <span>
                {{ activityLabel(item.activityType) }}
                <small v-if="item.hint && item.durationSeconds">{{ item.hint }}</small>
              </span>
              <strong>{{ formatDuration(item.durationSeconds) }}</strong>
              <em>{{ item.percent }}%</em>
            </div>
          </div>
          <button
            v-if="emptyDistributionCount > 0"
            type="button"
            class="distribution-toggle"
            :aria-expanded="showEmptyDistribution"
            @click="showEmptyDistribution = !showEmptyDistribution"
          >
            {{ showEmptyDistribution
              ? '收起未投入类型'
              : `还有 ${emptyDistributionCount} 类暂无时长 · 展开` }}
          </button>
          <p class="distribution-note">
            {{ summary.totalSeconds
              ? '含站内/站外视频、打字、路演、任务书、Office 等。'
              : '学习后时长会自动累计到对应类型。' }}
          </p>
        </aside>
      </div>

      <div class="profile-growth-grid">
        <section class="student-card profile-panel profile-awards-panel">
          <div class="profile-panel__head">
            <div>
              <h2>我的奖状</h2>
              <p>老师发布给个人或团队的荣誉</p>
            </div>
            <span class="profile-count">{{ certificates.length }} 张</span>
          </div>
          <div v-if="certificates.length" class="certificate-list">
            <button
              v-for="item in certificates"
              :key="item.id"
              type="button"
              class="certificate-card"
              :class="{ 'is-team': item.certificateType === 'TEAM' }"
              @click="selectedCertificate = item"
            >
              <span class="certificate-preview" :class="{ 'is-team': item.certificateType === 'TEAM' }" aria-hidden="true">
                <span class="certificate-preview__corner certificate-preview__corner--tl"></span>
                <span class="certificate-preview__corner certificate-preview__corner--br"></span>
                <span class="certificate-preview__ribbon">{{ certificateSealLabel(item) }}</span>
                <i class="certificate-preview__brand">
                  <img src="/brand/competition-brain-mark.svg" alt="" />
                  <span>竞赛大脑</span>
                </i>
                <strong>奖 状</strong>
                <b>{{ item.title }}</b>
                <small>{{ item.awardLevel || (item.certificateType === 'TEAM' ? '团队荣誉' : '个人荣誉') }}</small>
                <em>{{ certificateSealLabel(item) }}</em>
              </span>
              <span class="certificate-copy">
                <span class="certificate-scope" :class="{ 'is-team': item.certificateType === 'TEAM' }">
                  {{ item.certificateType === 'TEAM' ? '团队奖状' : '个人奖状' }}
                </span>
                <strong>{{ item.title }}</strong>
                <span v-if="item.awardLevel" class="certificate-level">{{ item.awardLevel }}</span>
                <em>{{ item.issuerName || '平台老师' }} · {{ formatDate(item.issuedAt) }}</em>
                <span class="certificate-action">
                  预览奖状
                  <ArrowRight />
                </span>
              </span>
            </button>
          </div>
          <div v-else class="profile-empty profile-empty--award">
            <span class="profile-empty__badge" aria-hidden="true">
              <Trophy />
            </span>
            <strong>还没有收到奖状</strong>
            <p>老师发布个人或团队荣誉后会显示在这里。</p>
          </div>
        </section>

        <section class="student-card profile-panel">
          <div class="profile-panel__head">
            <div>
              <h2>整改通知</h2>
              <p>仅相关个人或团队成员可见</p>
            </div>
            <span class="profile-count">{{ rectifications.length }} 条</span>
          </div>
          <div v-if="rectifications.length" class="rectification-list">
            <button v-for="item in rectifications" :key="item.id" type="button" @click="selectedRectification = item">
              <span :class="['rectification-status', `is-${String(item.status).toLowerCase()}`]">
                <CircleCheck v-if="item.status === 'COMPLETED'" />
                <Warning v-else />
              </span>
              <span>
                <small>{{ rectificationStatus(item.status) }}</small>
                <strong>{{ item.title }}</strong>
                <em>{{ item.issuerName || '平台老师' }}<template v-if="item.dueAt"> · 截止 {{ formatDate(item.dueAt) }}</template></em>
              </span>
              <ArrowRight />
            </button>
          </div>
          <div v-else class="profile-empty">
            <CircleCheck />
            <strong>当前没有整改通知</strong>
            <p>如老师发布整改通知，这里会显示原因、要求和截止日期。</p>
          </div>
        </section>
      </div>
    </template>

    <el-dialog
      v-model="certificateDialog"
      width="680px"
      align-center
      append-to-body
      class="certificate-preview-dialog"
      :show-close="false"
    >
      <template #header>
        <div class="certificate-dialog-head">
          <div>
            <span class="certificate-scope" :class="{ 'is-team': selectedCertificate?.certificateType === 'TEAM' }">
              {{ selectedCertificate?.certificateType === 'TEAM' ? '团队奖状' : '个人奖状' }}
            </span>
            <h2>{{ selectedCertificate?.title || '奖状预览' }}</h2>
          </div>
          <button class="certificate-dialog-close" type="button" aria-label="关闭奖状预览" @click="selectedCertificate = null">×</button>
        </div>
      </template>
      <div v-if="selectedCertificate" class="certificate-dialog" :class="{ 'is-team': selectedCertificate.certificateType === 'TEAM' }">
        <span class="certificate-dialog__frame" aria-hidden="true"></span>
        <span class="certificate-dialog__glow" aria-hidden="true"></span>
        <div class="certificate-dialog__brand">
          <span>
            <img src="/brand/competition-brain-mark.svg" alt="竞赛大脑 Logo" />
            <b>竞赛大脑</b>
          </span>
          <em>{{ certificateDisplayNo(selectedCertificate.certificateNo) }}</em>
        </div>
        <h3 class="certificate-dialog__title">奖 状</h3>
        <p class="certificate-dialog__grant">
          兹授予
          <b>{{ selectedCertificate.certificateType === 'TEAM' ? '团队成员' : (profile.username || '同学') }}</b>
        </p>
        <h4 class="certificate-dialog__name">{{ selectedCertificate.title }}</h4>
        <p v-if="selectedCertificate.awardLevel" class="certificate-dialog__level">{{ selectedCertificate.awardLevel }}</p>
        <p class="certificate-dialog__desc">
          {{ selectedCertificate.description || '表彰在本次备赛过程中表现突出的个人或团队，特发此状，以资鼓励。' }}
        </p>
        <div class="certificate-dialog__meta">
          <span>
            <small>颁发单位</small>
            <strong>{{ selectedCertificate.issuerName || '竞赛大脑' }}</strong>
          </span>
          <span>
            <small>颁发日期</small>
            <strong>{{ formatDate(selectedCertificate.issuedAt) }}</strong>
          </span>
        </div>
        <span class="certificate-dialog__seal" aria-hidden="true">{{ certificateSealLabel(selectedCertificate) }}</span>
      </div>
      <template #footer>
        <button class="student-secondary-btn" type="button" @click="selectedCertificate = null">关闭</button>
        <a
          v-if="selectedCertificate?.pdfUrl"
          class="student-primary-btn"
          :href="selectedCertificate.pdfUrl"
          target="_blank"
          rel="noopener"
        >下载奖状</a>
      </template>
    </el-dialog>

    <el-dialog v-model="rectificationDialog" title="整改说明" width="560px" align-center append-to-body>
      <div v-if="selectedRectification" class="rectification-dialog">
        <span>{{ rectificationStatus(selectedRectification.status) }}</span>
        <h2>{{ selectedRectification.title }}</h2>
        <p>{{ selectedRectification.description || '老师暂未填写补充说明。' }}</p>
        <dl>
          <div><dt>整改要求</dt><dd>{{ selectedRectification.requirementText || '按老师要求完成相关改进。' }}</dd></div>
          <div><dt>发布老师</dt><dd>{{ selectedRectification.issuerName || '平台老师' }}</dd></div>
          <div><dt>发布日期</dt><dd>{{ formatDate(selectedRectification.issuedAt) }}</dd></div>
          <div><dt>截止日期</dt><dd>{{ selectedRectification.dueAt ? formatDate(selectedRectification.dueAt) : '未设置' }}</dd></div>
        </dl>
      </div>
      <template #footer>
        <button class="student-secondary-btn" type="button" @click="selectedRectification = null">关闭</button>
        <router-link
          v-if="selectedRectification?.relatedTaskId"
          class="student-primary-btn"
          :to="`/project-team?taskId=${selectedRectification.relatedTaskId}`"
          @click="selectedRectification = null"
        >
          查看相关任务
        </router-link>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, CircleCheck, Trophy, Warning, WarningFilled } from '@element-plus/icons-vue'
import request from '../utils/request'

const loading = ref(true)
const error = ref('')
const data = ref({})
const heatmapMode = ref('daily')
const selectedCertificate = ref(null)
const selectedRectification = ref(null)

const profile = computed(() => data.value.profile || {})
const summary = computed(() => data.value.summary || {})
const certificates = computed(() => data.value.certificates || [])
const rectifications = computed(() => data.value.rectifications || [])
const initial = computed(() => String(profile.value.username || '同').slice(0, 1))
const certificateDialog = computed({
  get: () => Boolean(selectedCertificate.value),
  set: value => { if (!value) selectedCertificate.value = null },
})
const rectificationDialog = computed({
  get: () => Boolean(selectedRectification.value),
  set: value => { if (!value) selectedRectification.value = null },
})

const heatmapModes = [
  { label: '每日', value: 'daily' },
  { label: '每周', value: 'weekly' },
  { label: '累计', value: 'cumulative' },
]

const statisticItems = computed(() => [
  { label: '累计学习时长', value: formatDuration(summary.value.totalSeconds) },
  { label: '近一周学习时长', value: formatDuration(summary.value.weekSeconds) },
  { label: '最长单次学习', value: formatDuration(summary.value.longestSessionSeconds) },
  { label: '当前连续学习', value: `${summary.value.currentStreakDays || 0} 天` },
  { label: '最长连续学习', value: `${summary.value.longestStreakDays || 0} 天` },
])

const precise = computed(() => data.value.preciseDurations || {})
const roadshow = computed(() => data.value.roadshow || {})
const roadshowLink = computed(() => {
  if (roadshow.value.sessionId) return `/ai-score/report/${roadshow.value.sessionId}/result`
  if (roadshow.value.reportId) return `/ai-score/report-id/${roadshow.value.reportId}/result`
  return ''
})
/** 0 时长类型默认折叠，避免右侧列表把整页撑高、左侧大片空白 */
const showEmptyDistribution = ref(false)

const distributionItems = computed(() => {
  const items = data.value.distribution || []
  // 完整口径：与后端 distribution 顺序一致
  const order = [
    'TRAINING',
    'TYPING',
    'COURSE',
    'EXAM',
    'ROADSHOW',
    'TASK_BOOK',
    'INSPIRE_OFFICE',
    'COLLABORATION',
  ]
  const embedSec = Number(precise.value.embedVideoSeconds || 0)
  const platformSec = Number(precise.value.platformVideoSeconds || 0)
  return order.map((type) => {
    const found = items.find((item) => item.activityType === type) || {
      activityType: type,
      durationSeconds: 0,
      percent: 0,
    }
    let hint = ''
    if (type === 'TRAINING' && (embedSec > 0 || platformSec > 0)) {
      const parts = []
      if (platformSec > 0) parts.push(`站内 ${formatDuration(platformSec)}`)
      if (embedSec > 0) parts.push(`站外 ${formatDuration(embedSec)}`)
      hint = parts.join(' · ')
    }
    if (type === 'TYPING' && Number(precise.value.typingSeconds || 0) > 0 && !found.durationSeconds) {
      const typing = Number(precise.value.typingSeconds || 0)
      const total = Math.max(1, Number(summary.value.totalSeconds || 0) + typing)
      return {
        activityType: type,
        durationSeconds: typing,
        percent: Math.round((typing * 1000) / total) / 10,
        hint: '自主/代码/排位',
      }
    }
    if (type === 'TYPING' && found.durationSeconds > 0) {
      hint = '自主/代码/排位'
    }
    return { ...found, hint }
  })
})

const activeDistributionItems = computed(() =>
  distributionItems.value.filter((item) => Number(item.durationSeconds || 0) > 0)
)

const emptyDistributionItems = computed(() =>
  distributionItems.value.filter((item) => !Number(item.durationSeconds || 0))
)

const emptyDistributionCount = computed(() => emptyDistributionItems.value.length)

const visibleDistributionItems = computed(() => {
  if (showEmptyDistribution.value) return distributionItems.value
  // 全 0 时仍展示全部类型，方便空状态引导
  if (!activeDistributionItems.value.length) return distributionItems.value
  return activeDistributionItems.value
})

const dailyHeatmap = computed(() => {
  const durationByDate = new Map((data.value.heatmap || []).map(item => [item.date, Number(item.durationSeconds || 0)]))
  const end = parseDate(data.value.serverDate) || new Date()
  const start = new Date(end)
  start.setDate(start.getDate() - 364)
  const values = []
  for (let index = 0; index < 365; index += 1) {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const dateKey = toDateKey(date)
    const seconds = durationByDate.get(dateKey) || 0
    values.push({
      key: dateKey,
      date,
      seconds,
      level: heatLevel(seconds),
      tooltip: `${formatDate(dateKey)} · 学习 ${formatDuration(seconds)}`,
    })
  }
  return values
})

const weeklyHeatmap = computed(() => {
  const groups = []
  for (let index = 0; index < dailyHeatmap.value.length; index += 7) {
    const days = dailyHeatmap.value.slice(index, index + 7)
    const seconds = days.reduce((total, item) => total + item.seconds, 0)
    groups.push({
      key: `week-${days[0].key}`,
      seconds,
      level: heatLevel(seconds / 3),
      tooltip: `${formatDate(days[0].key)}–${formatDate(days.at(-1).key)} · 学习 ${formatDuration(seconds)}`,
    })
  }
  return groups
})

const cumulativeHeatmap = computed(() => {
  let running = 0
  return dailyHeatmap.value.map(item => {
    running += item.seconds
    return {
      ...item,
      level: heatLevel(running / 20),
      tooltip: `截至 ${formatDate(item.key)} · 累计学习 ${formatDuration(running)}`,
    }
  })
})

const visibleHeatmap = computed(() => {
  if (heatmapMode.value === 'weekly') return weeklyHeatmap.value
  if (heatmapMode.value === 'cumulative') return cumulativeHeatmap.value
  return dailyHeatmap.value
})

const heatmapColumns = computed(() => heatmapMode.value === 'weekly' ? weeklyHeatmap.value.length : Math.ceil(dailyHeatmap.value.length / 7))
const heatmapMonthLabels = computed(() => {
  if (heatmapMode.value === 'weekly') return []
  const labels = []
  let previousMonth = -1
  dailyHeatmap.value.forEach((item, index) => {
    const month = item.date.getMonth()
    if (month === previousMonth) return
    previousMonth = month
    if (index === 0 && item.date.getDate() > 7) return
    labels.push({ key: item.key, text: `${month + 1}月`, column: Math.floor(index / 7) + 1 })
  })
  return labels
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const response = await request.get('/api/student/profile/dashboard')
    data.value = response?.data ?? response ?? {}
  } catch (cause) {
    error.value = cause?.message || '请稍后重试'
  } finally {
    loading.value = false
  }
}

function formatDuration(value) {
  const totalMinutes = Math.max(0, Math.round(Number(value || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (!hours) return `${minutes} 分钟`
  return `${hours} 小时 ${minutes} 分`
}

function formatScore(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(1)
}

function formatDate(value) {
  if (!value) return '—'
  const date = parseDate(value)
  if (!date) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date)
}

function parseDate(value) {
  if (!value) return null
  const date = new Date(String(value).length === 10 ? `${value}T00:00:00` : value)
  return Number.isNaN(date.getTime()) ? null : date
}

function toDateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function heatLevel(seconds) {
  const minutes = seconds / 60
  if (!minutes) return 0
  if (minutes < 20) return 1
  if (minutes < 45) return 2
  if (minutes < 90) return 3
  return 4
}

function activityLabel(type) {
  return {
    COURSE: '课程学习',
    TRAINING: '训练营学习',
    TYPING: '打字练习',
    EXAM: '练习考试',
    ROADSHOW: '路演训练',
    TASK_BOOK: '任务书研读',
    INSPIRE_OFFICE: '启发 Office',
    COLLABORATION: '协作复盘',
  }[type] || type
}

function certificateSealLabel(item) {
  const level = String(item?.awardLevel || '').trim()
  if (level) return level.slice(0, 2)
  return item?.certificateType === 'TEAM' ? '团队' : '荣誉'
}

function certificateDisplayNo(value) {
  const number = String(value || '').trim().replace(/^OREP-/i, '')
  return number || '荣誉证明'
}

function roleLabel(role) {
  return { CAPTAIN: '项目负责人', MEMBER: '团队成员', MENTOR: '指导老师' }[role] || role || '团队成员'
}

function rectificationStatus(status) {
  return { PENDING: '待整改', IN_PROGRESS: '整改中', COMPLETED: '已完成', CANCELLED: '已撤销' }[status] || status || '待整改'
}

onMounted(load)
</script>

<style scoped>
.profile-dashboard {
  width: 100%;
  max-width: none;
}

.profile-loading,
.profile-state {
  min-height: 420px;
}

.profile-state {
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 12px;
  text-align: center;
}

.profile-state > svg {
  width: 32px;
  color: #e84a1c;
}

.profile-state h2,
.profile-state p {
  margin: 0;
}

.profile-state p {
  color: #7a7a7f;
}

.profile-identity {
  overflow: hidden;
}

.profile-identity__person {
  min-height: 102px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px 24px;
}

.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, #f66b38, #e84113);
  box-shadow: 0 12px 28px rgba(232, 74, 28, 0.2);
  font-size: 26px;
  font-weight: 700;
}

.profile-name {
  display: flex;
  align-items: center;
  gap: 10px;
}

.profile-name h2 {
  margin: 0;
  color: #1d1d1f;
  font-size: 22px;
}

.profile-name span,
.profile-count {
  padding: 5px 9px;
  border-radius: 999px;
  color: #d94417;
  background: #fff1eb;
  font-size: 11px;
  font-weight: 700;
}

.profile-identity__person p {
  margin: 5px 0;
  color: #6f6f74;
  font-size: 13px;
}

.profile-identity__person small {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #747479;
}

.profile-identity__person small i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #20a974;
}

.profile-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  border-top: 1px solid #eeeeef;
}

.profile-stats > div {
  min-height: 72px;
  display: grid;
  place-content: center;
  gap: 5px;
  text-align: center;
  border-right: 1px solid #eeeeef;
}

.profile-stats > div:last-child {
  border-right: 0;
}

.profile-stats strong {
  color: #222225;
  font-size: 18px;
}

.profile-stats span {
  color: #8b8b90;
  font-size: 11px;
}

.profile-roadshow {
  margin-top: 16px;
  padding: 16px 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.profile-roadshow h2 {
  margin: 0 0 4px;
  font-size: 16px;
}

.profile-roadshow p {
  margin: 0;
  color: #8b8b90;
  font-size: 12px;
}

.profile-roadshow__score {
  margin-left: auto;
  text-align: right;
}

.profile-roadshow__score strong {
  display: block;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.profile-roadshow__score span {
  color: #8b8b90;
  font-size: 12px;
}

.profile-learning-grid,
.profile-growth-grid {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(320px, 3fr);
  gap: 16px;
  margin-top: 16px;
}

.profile-panel {
  padding: 20px;
}

.profile-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.profile-panel__head h2 {
  margin: 0;
  color: #1f1f22;
  font-size: 17px;
}

.profile-panel__head p {
  margin: 5px 0 0;
  color: #8b8b90;
  font-size: 11px;
}

.profile-segmented {
  display: flex;
  gap: 3px;
  padding: 3px;
  border-radius: 10px;
  background: #f4f4f6;
}

.profile-segmented button {
  height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  color: #78787d;
  background: transparent;
  cursor: pointer;
  font-size: 11px;
}

.profile-segmented button.is-active {
  color: #1d1d1f;
  background: #fff;
  box-shadow: 0 2px 7px rgba(15, 23, 42, 0.08);
  font-weight: 700;
}

.profile-heatmap-shell {
  min-width: 0;
  min-height: 204px;
  display: grid;
  align-content: center;
  margin-top: 8px;
  overflow: visible;
}

.profile-heatmap-labels {
  width: 100%;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(53, minmax(0, 1fr));
  gap: 4px;
  margin-bottom: 6px;
}

.profile-heatmap-labels span {
  color: #9a9aa0;
  font-size: 10px;
  white-space: nowrap;
}

.profile-heatmap {
  width: 100%;
  min-width: 0;
  display: grid;
  grid-template-rows: repeat(7, 12px);
  grid-template-columns: repeat(var(--heatmap-columns), minmax(0, 1fr));
  grid-auto-flow: column;
  gap: 4px;
}

.profile-heatmap.is-aggregate {
  grid-template-rows: 16px;
  grid-auto-flow: row;
  min-width: 0;
}

.profile-heat-cell {
  position: relative;
  width: 100%;
  min-width: 0;
  border: 0;
  border-radius: 3px;
  padding: 0;
  background: #f0f0f2;
  cursor: pointer;
}

.profile-heat-cell.level-1,
.profile-heat-legend i.level-1 { background: #ffe1d5; }
.profile-heat-cell.level-2,
.profile-heat-legend i.level-2 { background: #ffb397; }
.profile-heat-cell.level-3,
.profile-heat-legend i.level-3 { background: #fa8056; }
.profile-heat-cell.level-4,
.profile-heat-legend i.level-4 { background: #ed4b1b; }

.profile-heat-cell::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  z-index: 20;
  width: max-content;
  max-width: 230px;
  padding: 7px 9px;
  border-radius: 8px;
  color: #fff;
  background: rgba(29, 29, 31, 0.92);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  font-size: 11px;
  line-height: 1.4;
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, 4px);
  transition: opacity 120ms ease, transform 120ms ease;
}

.profile-heat-cell:hover::after,
.profile-heat-cell:focus-visible::after {
  opacity: 1;
  transform: translate(-50%, 0);
}

.profile-heat-legend {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 4px;
  color: #9a9aa0;
  font-size: 10px;
}

.profile-heat-legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: #f0f0f2;
}

.profile-distribution {
  align-self: start;
}

.distribution-track {
  height: 8px;
  display: flex;
  overflow: hidden;
  margin: 12px 0 10px;
  border-radius: 999px;
  background: #ececef;
}

.distribution-list {
  display: grid;
  gap: 0;
}

.distribution-list > div {
  min-height: 0;
  display: grid;
  grid-template-columns: 7px minmax(0, 1fr) auto 40px;
  align-items: center;
  gap: 7px;
  padding: 6px 0;
  border-bottom: 1px solid #f3f3f4;
  font-size: 11px;
}

.distribution-list > div:last-child {
  border-bottom: 0;
}

.distribution-list > div.is-empty {
  opacity: 0.48;
}

.distribution-list i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #d7d7dc;
}

.distribution-list span {
  display: grid;
  gap: 1px;
  color: #68686d;
  line-height: 1.25;
  font-weight: 600;
  min-width: 0;
}

.distribution-list span small {
  color: #9a9aa0;
  font-size: 10px;
  font-weight: 550;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.distribution-list strong {
  color: #29292c;
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
}

.distribution-list em {
  color: #e84a1c;
  font-style: normal;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}

.distribution-toggle {
  appearance: none;
  width: 100%;
  margin-top: 6px;
  padding: 6px 8px;
  border: 0;
  border-radius: 8px;
  background: #f6f6f7;
  color: #6b7280;
  font: 600 11px/1.3 inherit;
  cursor: pointer;
  text-align: center;
}

.distribution-toggle:hover {
  background: #efeff1;
  color: #374151;
}

.distribution-list i.is-course,
.distribution-track .is-course { background: #ed4b1b; }
.distribution-list i.is-training,
.distribution-track .is-training { background: #ea580c; }
.distribution-list i.is-typing,
.distribution-track .is-typing { background: #0ea5e9; }
.distribution-list i.is-exam,
.distribution-track .is-exam { background: #f77a50; }
.distribution-list i.is-roadshow,
.distribution-track .is-roadshow { background: #f5aa8e; }
.distribution-list i.is-task_book,
.distribution-track .is-task_book { background: #8b5cf6; }
.distribution-list i.is-inspire_office,
.distribution-track .is-inspire_office { background: #14b8a6; }
.distribution-list i.is-collaboration,
.distribution-track .is-collaboration { background: #d7d7dc; }

.distribution-note {
  margin: 8px 0 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  color: #9a9aa0;
  background: transparent;
  font-size: 10px;
  line-height: 1.4;
}

.profile-awards-panel {
  position: relative;
}

.certificate-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.certificate-card {
  min-width: 0;
  min-height: 156px;
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  padding: 0;
  overflow: hidden;
  border: 1px solid rgba(232, 74, 28, 0.12);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 252, 250, 0.96));
  box-shadow: 0 10px 24px rgba(148, 80, 45, 0.06);
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.certificate-card:hover {
  transform: translateY(-2px);
  border-color: rgba(232, 74, 28, 0.24);
  box-shadow: 0 16px 28px rgba(148, 80, 45, 0.1);
}

.certificate-card.is-team {
  border-color: rgba(180, 120, 28, 0.16);
}

.certificate-preview {
  position: relative;
  min-height: 156px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 18px 12px 16px;
  overflow: hidden;
  border-right: 1px solid rgba(232, 74, 28, 0.12);
  color: #7d321c;
  background:
    radial-gradient(circle at 20% 18%, rgba(255, 214, 186, 0.55), transparent 42%),
    radial-gradient(circle at 82% 88%, rgba(255, 188, 148, 0.35), transparent 36%),
    linear-gradient(160deg, #fff8f4 0%, #fff1e8 55%, #fffdfb 100%);
  text-align: center;
}

.certificate-preview.is-team {
  color: #704e17;
  border-right-color: rgba(163, 112, 28, 0.16);
  background:
    radial-gradient(circle at 18% 16%, rgba(255, 228, 170, 0.55), transparent 42%),
    radial-gradient(circle at 84% 86%, rgba(245, 196, 112, 0.28), transparent 36%),
    linear-gradient(160deg, #fffaf0 0%, #fff4df 55%, #fffdf8 100%);
}

.certificate-preview__corner {
  position: absolute;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(232, 74, 28, 0.22);
  transform: rotate(45deg);
  pointer-events: none;
}

.certificate-preview.is-team .certificate-preview__corner {
  border-color: rgba(163, 112, 28, 0.28);
}

.certificate-preview__corner--tl {
  top: -24px;
  left: -24px;
}

.certificate-preview__corner--br {
  right: -24px;
  bottom: -24px;
}

.certificate-preview__ribbon {
  position: absolute;
  top: 12px;
  left: -18px;
  min-width: 78px;
  padding: 4px 18px;
  transform: rotate(-28deg);
  color: #fff;
  background: linear-gradient(90deg, #e84a1c, #f0733d);
  box-shadow: 0 4px 10px rgba(232, 74, 28, 0.22);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-align: center;
}

.certificate-preview.is-team .certificate-preview__ribbon {
  background: linear-gradient(90deg, #c28a1c, #e0b04a);
  box-shadow: 0 4px 10px rgba(194, 138, 28, 0.22);
}

.certificate-preview i,
.certificate-preview strong,
.certificate-preview b,
.certificate-preview small {
  position: relative;
  z-index: 1;
}

.certificate-preview i {
  font-style: normal;
  opacity: 0.82;
}

.certificate-preview__brand {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.certificate-preview__brand img {
  width: 12px;
  height: 12px;
  object-fit: contain;
}

.certificate-preview strong {
  font-size: 22px;
  letter-spacing: 0.22em;
  line-height: 1;
}

.certificate-preview b {
  max-width: 128px;
  margin-top: 2px;
  overflow: hidden;
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.certificate-preview small {
  color: rgba(125, 50, 28, 0.72);
  font-size: 9px;
}

.certificate-preview.is-team small {
  color: rgba(112, 78, 23, 0.72);
}

.certificate-preview em {
  position: absolute;
  right: 12px;
  bottom: 12px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 2px solid rgba(196, 58, 18, 0.42);
  border-radius: 50%;
  color: rgba(196, 58, 18, 0.68);
  background: rgba(255, 255, 255, 0.45);
  font-size: 9px;
  font-style: normal;
  font-weight: 800;
  transform: rotate(-12deg);
  z-index: 1;
}

.certificate-preview.is-team em {
  border-color: rgba(163, 112, 28, 0.45);
  color: rgba(128, 93, 29, 0.72);
}

.certificate-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 7px;
  padding: 16px 16px 16px 14px;
  min-width: 0;
}

.certificate-scope {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  color: #d94417;
  background: #fff1eb;
  font-size: 10px;
  font-weight: 700;
}

.certificate-scope.is-team {
  color: #805d1d;
  background: #fff7e6;
}

.certificate-copy strong {
  overflow: hidden;
  max-width: 100%;
  color: #1f1f23;
  font-size: 15px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.certificate-level {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 8px;
  color: #9a4a1f;
  background: rgba(232, 74, 28, 0.08);
  font-size: 11px;
  font-weight: 700;
}

.certificate-copy em {
  color: #8c8c91;
  font-size: 11px;
  font-style: normal;
  line-height: 1.4;
}

.certificate-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  color: #e84a1c;
  font-size: 12px;
  font-weight: 700;
}

.certificate-action svg {
  width: 14px;
  height: 14px;
}

.profile-empty--award {
  border: 1px dashed rgba(232, 74, 28, 0.18);
  border-radius: 14px;
  background: linear-gradient(180deg, #fffaf7, #fff);
}

.profile-empty__badge {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: #e84a1c;
  background: linear-gradient(145deg, #fff1eb, #fff8f4);
  box-shadow: inset 0 0 0 1px rgba(232, 74, 28, 0.12);
}

.profile-empty__badge svg {
  width: 22px;
  height: 22px;
}

.rectification-list {
  display: grid;
  gap: 9px;
  margin-top: 18px;
}

.rectification-list > button {
  min-height: 64px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #eeeef0;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.rectification-status {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: #e6481a;
  background: #fff1ec;
}

.rectification-status.is-completed {
  color: #16885f;
  background: #e9f7f1;
}

.rectification-status svg,
.rectification-list > button > svg {
  width: 15px;
}

.rectification-list small,
.rectification-list em {
  display: block;
  color: #8b8b90;
  font-size: 9px;
  font-style: normal;
}

.rectification-list strong {
  display: block;
  margin: 3px 0;
  color: #2a2a2d;
  font-size: 12px;
}

.rectification-list > button > svg {
  color: #a5a5aa;
}

.profile-empty {
  min-height: 154px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 7px;
  text-align: center;
  color: #929297;
}

.profile-empty svg {
  width: 25px;
  color: #e84a1c;
}

.profile-empty strong {
  color: #39393c;
  font-size: 13px;
}

.profile-empty p {
  margin: 0;
  font-size: 10px;
}

.certificate-dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
}

.certificate-dialog-head h2 {
  margin: 8px 0 0;
  color: #1f1f23;
  font-size: 20px;
  line-height: 1.3;
}

.certificate-dialog-close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  color: #8b8b90;
  background: #f5f5f6;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.certificate-dialog-close:hover {
  color: #e84a1c;
  background: #fff1eb;
}

.certificate-dialog {
  position: relative;
  min-height: 360px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  margin: 4px 2px 8px;
  padding: 42px 40px 36px;
  overflow: hidden;
  border: 1px solid rgba(232, 74, 28, 0.28);
  outline: 1px solid rgba(232, 74, 28, 0.12);
  outline-offset: -8px;
  color: #6d2b18;
  background:
    radial-gradient(circle at 12% 12%, rgba(255, 214, 186, 0.42), transparent 28%),
    radial-gradient(circle at 88% 86%, rgba(255, 188, 148, 0.28), transparent 30%),
    linear-gradient(160deg, #fffaf7 0%, #fff4ed 48%, #fffdfb 100%);
  text-align: center;
}

.certificate-dialog.is-team {
  border-color: rgba(180, 120, 28, 0.28);
  outline-color: rgba(180, 120, 28, 0.12);
  color: #6d4c16;
  background:
    radial-gradient(circle at 12% 12%, rgba(255, 228, 170, 0.45), transparent 28%),
    radial-gradient(circle at 88% 86%, rgba(245, 196, 112, 0.24), transparent 30%),
    linear-gradient(160deg, #fffdf7 0%, #fff6e4 48%, #fffdf9 100%);
}

.certificate-dialog__frame,
.certificate-dialog__glow {
  position: absolute;
  inset: 14px;
  pointer-events: none;
}

.certificate-dialog__frame {
  border: 1px dashed rgba(232, 74, 28, 0.18);
}

.certificate-dialog.is-team .certificate-dialog__frame {
  border-color: rgba(180, 120, 28, 0.2);
}

.certificate-dialog__glow {
  inset: 0;
  background:
    linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35), transparent);
  opacity: 0.55;
}

.certificate-dialog__brand {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 4px;
  justify-items: center;
}

.certificate-dialog__brand span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.certificate-dialog__brand img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.certificate-dialog__brand b {
  font: inherit;
}

.certificate-dialog__brand em {
  color: #9b766a;
  font-size: 10px;
  font-style: normal;
}

.certificate-dialog__title {
  position: relative;
  z-index: 1;
  margin: 8px 0 0;
  font-size: 34px;
  letter-spacing: 0.28em;
  line-height: 1;
}

.certificate-dialog__grant {
  position: relative;
  z-index: 1;
  margin: 10px 0 0;
  color: #7f574a;
  font-size: 13px;
}

.certificate-dialog__grant b {
  color: #6d2b18;
  font-size: 15px;
}

.certificate-dialog__name {
  position: relative;
  z-index: 1;
  margin: 8px 0 0;
  color: #e84a1c;
  font-size: 22px;
  line-height: 1.35;
}

.certificate-dialog.is-team .certificate-dialog__name {
  color: #b37a12;
}

.certificate-dialog__level {
  position: relative;
  z-index: 1;
  margin: 4px 0 0;
  min-height: 24px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  color: #9a4a1f;
  background: rgba(232, 74, 28, 0.08);
  font-size: 12px;
  font-weight: 700;
}

.certificate-dialog__desc {
  position: relative;
  z-index: 1;
  margin: 12px 0 0;
  max-width: 440px;
  color: #805546;
  font-size: 13px;
  line-height: 1.75;
}

.certificate-dialog__meta {
  position: relative;
  z-index: 1;
  width: min(100%, 420px);
  margin-top: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.certificate-dialog__meta span {
  display: grid;
  gap: 4px;
  text-align: left;
}

.certificate-dialog__meta small {
  color: #9b766a;
  font-size: 11px;
}

.certificate-dialog__meta strong {
  color: #6d2b18;
  font-size: 13px;
}

.certificate-dialog__seal {
  position: absolute;
  right: 38px;
  bottom: 42px;
  width: 64px;
  height: 64px;
  display: grid;
  place-items: center;
  border: 3px solid rgba(196, 58, 18, 0.36);
  border-radius: 50%;
  color: rgba(196, 58, 18, 0.55);
  background: rgba(255, 255, 255, 0.42);
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.04em;
  transform: rotate(-12deg);
  z-index: 1;
  box-shadow: inset 0 0 0 4px rgba(196, 58, 18, 0.08);
}

.certificate-dialog.is-team .certificate-dialog__seal {
  border-color: rgba(163, 112, 28, 0.4);
  color: rgba(128, 93, 29, 0.58);
  box-shadow: inset 0 0 0 4px rgba(163, 112, 28, 0.08);
}

.rectification-dialog > span {
  display: inline-flex;
  padding: 5px 9px;
  border-radius: 999px;
  color: #d94417;
  background: #fff1eb;
  font-size: 10px;
  font-weight: 700;
}

.rectification-dialog h2 {
  margin: 12px 0 8px;
  font-size: 20px;
}

.rectification-dialog > p {
  color: #6f6f74;
  line-height: 1.65;
}

.rectification-dialog dl {
  display: grid;
  margin: 18px 0 0;
  border-top: 1px solid #eeeef0;
}

.rectification-dialog dl > div {
  display: grid;
  grid-template-columns: 86px 1fr;
  padding: 12px 0;
  border-bottom: 1px solid #eeeef0;
}

.rectification-dialog dt {
  color: #8b8b90;
}

.rectification-dialog dd {
  margin: 0;
  color: #29292c;
}

@media (max-width: 1120px) {
  .profile-learning-grid,
  .profile-growth-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .profile-stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .profile-stats > div {
    border-bottom: 1px solid #eeeeef;
  }

  .certificate-list {
    grid-template-columns: 1fr;
  }

  .certificate-card {
    grid-template-columns: 132px minmax(0, 1fr);
  }

  .certificate-preview {
    min-height: 148px;
    padding-inline: 10px;
  }

  .certificate-preview strong {
    font-size: 18px;
    letter-spacing: 0.16em;
  }

  .certificate-dialog {
    padding: 30px 18px 28px;
  }

  .certificate-dialog__title {
    font-size: 28px;
    letter-spacing: 0.2em;
  }

  .certificate-dialog__name {
    font-size: 18px;
  }

  .certificate-dialog__seal {
    right: 16px;
    bottom: 28px;
    width: 52px;
    height: 52px;
    font-size: 13px;
  }

  .profile-heatmap-labels,
  .profile-heatmap {
    gap: 2px;
  }

  .profile-heatmap {
    grid-template-rows: repeat(7, 9px);
  }
}
</style>

<style>
.certificate-preview-dialog.el-dialog {
  border-radius: 18px;
  overflow: hidden;
}

.certificate-preview-dialog .el-dialog__header {
  margin: 0;
  padding: 18px 20px 10px;
}

.certificate-preview-dialog .el-dialog__body {
  padding: 4px 16px 8px;
}

.certificate-preview-dialog .el-dialog__footer {
  padding: 12px 20px 18px;
}
</style>
