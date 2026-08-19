<template>
  <div class="teacher-page profile-page">
    <header class="teacher-page__head">
      <div>
        <p class="back-row">
          <router-link class="teacher-link" :to="backLink.to">‹ {{ backLink.label }}</router-link>
        </p>
        <h1>{{ student.studentName || '学生档案' }}</h1>
        <p>
          一眼看状态与待办，点进训练日或批改继续跟进
          <span v-if="camp.campName" class="teacher-muted"> · {{ camp.campName }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          刷新
        </button>
        <router-link class="teacher-btn teacher-btn--secondary" to="/camp/progress">训练进度</router-link>
        <router-link class="teacher-btn teacher-btn--primary" to="/camp/review-queue">去批改</router-link>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>
    <div v-if="loading" class="teacher-empty">正在加载个人档案…</div>

    <template v-else-if="student.userId">
      <!-- 身份 + 一句话诊断 -->
      <section class="hero-card">
        <div class="hero-card__who">
          <span
            class="teacher-avatar"
            :style="{
              width: '52px',
              height: '52px',
              fontSize: '18px',
              background: avatarColor(student.userId || student.studentName),
            }"
          >
            {{ initial(student.studentName) }}
          </span>
          <div class="hero-card__meta">
            <div class="hero-card__name-row">
              <strong>{{ student.studentName }}</strong>
              <span v-if="statusTag" class="teacher-tag" :class="statusTag.cls">
                {{ statusTag.label }}
              </span>
            </div>
            <small>
              {{ student.positionName || '未分配岗位' }}
              <template v-if="student.teamName"> · {{ student.teamName }}</template>
            </small>
          </div>
        </div>
        <p class="hero-card__one">{{ oneLiner }}</p>
        <div v-if="riskTags.length" class="tag-row">
          <span
            v-for="t in riskTags"
            :key="t"
            class="teacher-tag"
            :class="tagClass(t)"
          >
            {{ t }}
          </span>
        </div>
      </section>

      <!-- 老师要处理：有才显示 -->
      <section v-if="todoItems.length" class="todo-strip">
        <header>
          <strong>你要处理</strong>
          <span>{{ todoItems.length }} 项</span>
        </header>
        <ul>
          <li v-for="item in todoItems" :key="item.key">
            <div>
              <b>{{ item.title }}</b>
              <small>{{ item.desc }}</small>
            </div>
            <router-link class="teacher-btn teacher-btn--primary teacher-btn--sm" :to="item.to">
              {{ item.action }}
            </router-link>
          </li>
        </ul>
      </section>

      <!-- 四个核心指标 -->
      <div class="kpi-row">
        <div class="kpi">
          <small>训练提交</small>
          <strong :class="{ 'is-warn': (training.missingDays || 0) > 0 }">
            {{ rateText }}
          </strong>
          <em>
            <template v-if="training.dueDays">
              {{ training.submittedDays || 0 }}/{{ training.dueDays }} 天 · 缺 {{ training.missingDays || 0 }}
            </template>
            <template v-else>暂无应训日</template>
          </em>
        </div>
        <div class="kpi">
          <small>学习投入</small>
          <strong>{{ formatDuration(summary.studySeconds || learning.totalSeconds) }}</strong>
          <em>本周 {{ formatDuration(learning.weekSeconds) }}</em>
        </div>
        <div class="kpi">
          <small>路演</small>
          <strong>{{ scoreText(summary.latestScore ?? roadshow.averageScore) }}</strong>
          <em>{{ roadshow.scoreCount ? `${roadshow.scoreCount} 次评分` : '暂无评分' }}</em>
        </div>
        <div class="kpi">
          <small>待你处理</small>
          <strong :class="{ 'is-warn': actionCount > 0 }">{{ actionCount }}</strong>
          <em>待批 + 整改</em>
        </div>
      </div>

      <!-- 主内容：训练日 + 侧栏补充 -->
      <div class="main-grid">
        <!-- 训练日进度：老师最关心 -->
        <section class="panel">
          <header class="panel__head">
            <div>
              <h2>训练日进度</h2>
              <p>每天交没交、过没过，一眼扫完</p>
            </div>
            <span v-if="training.submissionRate != null" class="teacher-tag is-info">
              提交率 {{ training.submissionRate }}%
            </span>
          </header>

          <div v-if="trainingDays.length" class="day-board">
            <button
              v-for="d in trainingDays"
              :key="d.dayId || d.dayNo"
              type="button"
              class="day-cell"
              :data-status="dayStatusKey(d)"
              :title="dayTitle(d)"
            >
              <span class="day-cell__no">D{{ d.dayNo }}</span>
              <strong>{{ dayStatusLabel(d) }}</strong>
              <small>{{ formatDayShort(d.trainingDate) }}</small>
            </button>
          </div>
          <p v-else class="hint">暂无已发布训练日。发布每日计划后这里会显示逐日状态。</p>

          <div v-if="trainingDays.length" class="day-legend">
            <span data-status="ok">已通过</span>
            <span data-status="pending">待批改</span>
            <span data-status="submitted">已提交</span>
            <span data-status="missing">缺交</span>
            <span data-status="todo">未提交</span>
          </div>
        </section>

        <!-- 右侧：学习 + 路演 + 整改 -->
        <div class="side-stack">
          <section class="panel">
            <header class="panel__head">
              <div>
                <h2>学习节奏</h2>
                <p>综合时长与近两周投入</p>
              </div>
              <strong class="panel__num">{{ formatDuration(learning.totalSeconds || summary.studySeconds) }}</strong>
            </header>

            <div class="mini-stats">
              <div>
                <small>本周</small>
                <b>{{ formatDuration(learning.weekSeconds) }}</b>
              </div>
              <div>
                <small>今日</small>
                <b>{{ formatDuration(learning.todaySeconds) }}</b>
              </div>
              <div>
                <small>连续</small>
                <b>{{ learning.currentStreakDays || 0 }} 天</b>
              </div>
              <div>
                <small>最长</small>
                <b>{{ learning.longestStreakDays || 0 }} 天</b>
              </div>
            </div>

            <div v-if="hasDailyBars" class="bars" role="img" aria-label="近14日学习时长">
              <div v-for="row in recentDailyBars" :key="row.date" class="bars__col">
                <i :style="{ height: `${row.h}px` }" :title="`${row.date}：${formatDuration(row.sec)}`" />
                <span>{{ row.label }}</span>
              </div>
            </div>
            <p v-else class="hint">暂无有效学习时长记录。</p>

            <div v-if="distribution.length" class="dist" aria-label="学习类型占比">
              <div class="dist-track">
                <i
                  v-for="d in distribution"
                  :key="d.activityType"
                  :class="`is-${String(d.activityType || '').toLowerCase()}`"
                  :style="{ width: `${Math.max(Number(d.percent) || 0, 1.2)}%` }"
                  :title="`${activityLabel(d.activityType)} ${formatNum(d.percent)}%`"
                />
              </div>
              <ul class="dist-list">
                <li v-for="d in distribution" :key="`l-${d.activityType}`">
                  <i :class="`is-${String(d.activityType || '').toLowerCase()}`" />
                  <span>{{ activityLabel(d.activityType) }}</span>
                  <strong>{{ formatNum(d.percent) }}%</strong>
                </li>
              </ul>
            </div>

            <!-- 精准时长：默认折叠，老师需要时再展开 -->
            <details class="precise-fold">
              <summary>
                精准学习明细
                <em>合计 {{ formatDuration(preciseTotalSeconds) }}</em>
              </summary>
              <div class="precise-grid">
                <button
                  v-for="item in preciseItems"
                  :key="item.key"
                  type="button"
                  class="precise-item"
                  :class="{ 'is-active': detailTab === item.key }"
                  @click="detailTab = detailTab === item.key ? '' : item.key"
                >
                  <small>{{ item.label }}</small>
                  <strong>{{ formatDuration(item.seconds) }}</strong>
                  <em>{{ item.hint }}</em>
                </button>
              </div>
              <div v-if="detailTab" class="precise-detail">
                <header>
                  <strong>{{ detailTitle }}</strong>
                  <button type="button" class="teacher-link text-button" @click="detailTab = ''">收起</button>
                </header>
                <p v-if="!activeDetailRows.length" class="hint">{{ detailEmptyText }}</p>
                <ul v-else class="detail-list">
                  <li v-for="(row, idx) in activeDetailRows" :key="detailRowKey(row, idx)">
                    <div>
                      <strong>{{ detailRowTitle(row) }}</strong>
                      <small>{{ detailRowMeta(row) }}</small>
                    </div>
                    <b>{{ formatDuration(detailRowSeconds(row)) }}</b>
                  </li>
                </ul>
              </div>
            </details>
          </section>

          <section v-if="hasRoadshowDetail" class="panel">
            <header class="panel__head">
              <div>
                <h2>路演与评分</h2>
                <p>均分 {{ scoreText(roadshow.averageScore) }} · {{ roadshow.scoreCount || 0 }} 次</p>
              </div>
              <router-link class="teacher-link" to="/roadshow?tab=recordings">录制回放 ›</router-link>
            </header>
            <div class="score-list">
              <div v-for="s in scoreList" :key="s.reportId" class="score-row">
                <strong>{{ scoreText(s.score) }}</strong>
                <small>{{ formatDateTime(s.scoredAt) }} · {{ s.sessionNo || `报告 #${s.reportId}` }}</small>
              </div>
            </div>
            <div v-if="dimensions.length" class="dim-list">
              <div v-for="row in dimensions" :key="row.dimensionCode" class="dim-row">
                <strong>{{ dimensionName(row.dimensionCode) }}</strong>
                <div class="dim-row__bar"><i :style="{ width: `${dimWidth(row.deductedPoints)}%` }" /></div>
                <b>−{{ formatNum(row.deductedPoints) }}</b>
              </div>
            </div>
          </section>

          <section v-if="remediations.length" class="panel">
            <header class="panel__head">
              <div>
                <h2>整改项</h2>
                <p>{{ remediations.length }} 条进行中或历史</p>
              </div>
              <router-link class="teacher-link" to="/review/ai-todos">整改复盘 ›</router-link>
            </header>
            <div class="todo-list">
              <div v-for="t in remediations" :key="t.todoId" class="todo-row">
                <strong>{{ t.title || '整改项' }}</strong>
                <small>{{ t.status }} · {{ formatDateTime(t.updatedAt) }}</small>
              </div>
            </div>
          </section>

          <section v-if="hasAbility" class="panel">
            <header class="panel__head">
              <div>
                <h2>能力画像</h2>
                <p>基于真实批改/课程/路演证据</p>
              </div>
            </header>
            <div class="ability-grid">
              <div v-for="a in abilityAxes" :key="a.key" class="ability-item">
                <small>{{ a.label }}</small>
                <strong>{{ a.value }}</strong>
                <i :style="{ width: `${a.value}%` }" />
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>

    <div v-else-if="!loading && !error" class="teacher-empty students-empty">
      <p>未找到该学生档案</p>
      <router-link class="teacher-btn teacher-btn--secondary" :to="backLink.to">返回列表</router-link>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchTeacherStudentProfile } from '../../api'

const AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777', '#0e7490']

const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref({})
const detailTab = ref('')

const backLink = computed(() => {
  const from = String(route.query.from || '')
  if (from === 'members') return { to: '/members', label: '返回成员管理' }
  if (from === 'analytics') return { to: '/analytics', label: '返回学情总览' }
  if (from === 'projects' && route.query.projectId) {
    return {
      to: { path: `/projects/${route.query.projectId}`, query: { tab: 'members' } },
      label: '返回项目成员',
    }
  }
  return { to: '/analytics/students', label: '返回学生档案' }
})

const student = computed(() => data.value.student || {})
const camp = computed(() => data.value.camp || {})
const summary = computed(() => data.value.summary || {})
const training = computed(() => data.value.training || {})
const learning = computed(() => data.value.learning || {})
const roadshow = computed(() => data.value.roadshow || {})
const ability = computed(() => data.value.ability || {})
const remediations = computed(() =>
  Array.isArray(data.value.remediations) ? data.value.remediations : []
)

const trainingDays = computed(() =>
  Array.isArray(training.value.days) ? training.value.days : []
)
const scoreList = computed(() => (Array.isArray(roadshow.value.scores) ? roadshow.value.scores : []))
const dimensions = computed(() =>
  (Array.isArray(roadshow.value.dimensionStats) ? roadshow.value.dimensionStats : [])
    .map((r) => ({
      ...r,
      deductedPoints: Number(r.deductedPoints) || 0,
    }))
    .slice(0, 6)
)
const maxDeducted = computed(() => Math.max(1, ...dimensions.value.map((d) => d.deductedPoints), 1))

const riskTags = computed(() => {
  const tags = summary.value.riskTags || student.value.riskTags || []
  return Array.isArray(tags) ? tags : []
})

const actionCount = computed(
  () => (training.value.pendingReviews || summary.value.pendingReviews || 0)
    + remediations.value.filter((t) => !/DONE|CLOSED|完成|关闭/i.test(String(t.status || ''))).length
)

const oneLiner = computed(() => {
  if (summary.value.oneLiner) return summary.value.oneLiner
  const miss = training.value.missingDays || 0
  const pending = training.value.pendingReviews || summary.value.pendingReviews || 0
  const openTodo = remediations.value.length
  if (miss >= 2) return `已缺交 ${miss} 天，建议今天催交或约谈`
  if (miss === 1) return '有 1 天缺交，留意是否掉队'
  if (pending > 0) return `有 ${pending} 份提交等你批改`
  if (openTodo > 0) return `有 ${openTodo} 条整改相关记录`
  if (riskTags.value.includes('学习时长偏低')) return '学习投入偏低，可抽查学习记录'
  if (training.value.dueDays && (training.value.submissionRate ?? 0) >= 90) {
    return '提交稳定，可重点看质量与路演'
  }
  if (!training.value.dueDays) return '暂无应训日数据，发布训练后会更新'
  return '状态平稳，可按需查看详情'
})

const statusTag = computed(() => {
  const miss = training.value.missingDays || 0
  const pending = training.value.pendingReviews || summary.value.pendingReviews || 0
  if (miss >= 2) return { label: '重点关注', cls: 'is-danger' }
  if (miss === 1) return { label: '有缺交', cls: 'is-warn' }
  if (pending > 0) return { label: '待批改', cls: 'is-warn' }
  if (remediations.value.length) return { label: '有整改', cls: 'is-warn' }
  if (riskTags.value.length) return { label: '留意', cls: 'is-info' }
  return { label: '平稳', cls: 'is-ok' }
})

const todoItems = computed(() => {
  const items = []
  const pending = training.value.pendingReviews || summary.value.pendingReviews || 0
  const miss = training.value.missingDays || 0
  if (pending > 0) {
    items.push({
      key: 'pending',
      title: `${pending} 份待批改`,
      desc: '学生已提交，等你通过或打回',
      action: '去批改',
      to: '/camp/review-queue',
    })
  }
  if (miss > 0) {
    items.push({
      key: 'missing',
      title: `${miss} 天缺交`,
      desc: '可在批改页提醒未提交同学',
      action: '看进度',
      to: '/camp/progress',
    })
  }
  if (remediations.value.length) {
    items.push({
      key: 'todo',
      title: `${remediations.value.length} 条整改`,
      desc: '跟进学生是否完成修改',
      action: '整改复盘',
      to: '/review/ai-todos',
    })
  }
  return items
})

const rateText = computed(() => {
  if (training.value.submissionRate == null || !training.value.dueDays) return '—'
  return `${training.value.submissionRate}%`
})

const preciseRaw = computed(() => {
  const l = learning.value || {}
  if (l.precise && typeof l.precise === 'object') return l.precise
  return l
})
const precise = computed(() => {
  const p = preciseRaw.value || {}
  const s = summary.value || {}
  return {
    platformVideoSeconds: Number(p.platformVideoSeconds ?? s.platformVideoSeconds) || 0,
    embedVideoSeconds: Number(p.embedVideoSeconds ?? s.embedVideoSeconds) || 0,
    taskBookDwellSeconds: Number(p.taskBookDwellSeconds ?? s.taskBookDwellSeconds) || 0,
    typingSeconds: Number(p.typingSeconds ?? s.typingSeconds) || 0,
    inspireOfficeSeconds: Number(p.inspireOfficeSeconds ?? s.inspireOfficeSeconds) || 0,
    inspireOfficeEditSeconds: Number(p.inspireOfficeEditSeconds ?? s.inspireOfficeEditSeconds) || 0,
  }
})
const details = computed(() => {
  const d = preciseRaw.value?.details
  return d && typeof d === 'object'
    ? {
        platformVideos: Array.isArray(d.platformVideos) ? d.platformVideos : [],
        embedVideos: Array.isArray(d.embedVideos) ? d.embedVideos : [],
        taskBookDays: Array.isArray(d.taskBookDays) ? d.taskBookDays : [],
        typingSessions: Array.isArray(d.typingSessions) ? d.typingSessions : [],
        inspireDocuments: Array.isArray(d.inspireDocuments) ? d.inspireDocuments : [],
      }
    : {
        platformVideos: [],
        embedVideos: [],
        taskBookDays: [],
        typingSessions: [],
        inspireDocuments: [],
      }
})
const preciseTotalSeconds = computed(() =>
  precise.value.platformVideoSeconds
  + precise.value.embedVideoSeconds
  + precise.value.taskBookDwellSeconds
  + precise.value.typingSeconds
  + precise.value.inspireOfficeSeconds
)

const preciseItems = computed(() => [
  {
    key: 'platform',
    label: '平台视频',
    seconds: precise.value.platformVideoSeconds,
    hint: `${details.value.platformVideos.length} 条`,
  },
  {
    key: 'embed',
    label: '站外视频',
    seconds: precise.value.embedVideoSeconds,
    hint: `${details.value.embedVideos.length} 条`,
  },
  {
    key: 'dwell',
    label: '任务书',
    seconds: precise.value.taskBookDwellSeconds,
    hint: `${details.value.taskBookDays.length} 天`,
  },
  {
    key: 'typing',
    label: '打字',
    seconds: precise.value.typingSeconds,
    hint: `${details.value.typingSessions.length} 次`,
  },
  {
    key: 'inspire',
    label: '启发 Office',
    seconds: precise.value.inspireOfficeSeconds,
    hint: `编辑 ${formatDuration(precise.value.inspireOfficeEditSeconds)}`,
  },
])

const detailTitle = computed(() => ({
  platform: '平台内视频明细',
  embed: '站外视频明细',
  dwell: '任务书驻留明细',
  typing: '打字练习明细',
  inspire: '启发 Office 明细',
}[detailTab.value] || '明细'))

const detailEmptyText = computed(() => ({
  platform: '暂无平台内视频学习记录。',
  embed: '暂无站外视频学习记录。',
  dwell: '暂无任务书驻留记录。',
  typing: '暂无打字练习记录。',
  inspire: '暂无启发 Office 记录。',
}[detailTab.value] || '暂无明细。'))

const activeDetailRows = computed(() => {
  if (detailTab.value === 'platform') return details.value.platformVideos
  if (detailTab.value === 'embed') return details.value.embedVideos
  if (detailTab.value === 'dwell') return details.value.taskBookDays
  if (detailTab.value === 'typing') return details.value.typingSessions
  if (detailTab.value === 'inspire') return details.value.inspireDocuments
  return []
})

const hasRoadshowDetail = computed(() => scoreList.value.length > 0 || dimensions.value.length > 0)
const hasAbility = computed(() => {
  const a = ability.value
  if (!a || !a.hasRealEvidence) return false
  return abilityAxes.value.length > 0
})

const DIMENSION_NAMES = {
  skill_level: '技能水平',
  professionalism: '职业素养',
  application_value: '应用价值',
  teamwork: '团队合作',
  innovation: '创新创意',
  problem_solving: '问题解决',
  communication: '表达沟通',
  presentation: '呈现表达',
  coding: '工程实现',
  creativity: '创新创意',
}

const ACTIVITY_NAMES = {
  COURSE: '课程学习',
  TRAINING: '训练营学习',
  TYPING: '打字练习',
  EXAM: '练习考试',
  ROADSHOW: '路演训练',
  TASK_BOOK: '任务书研读',
  INSPIRE_OFFICE: '启发 Office',
  COLLABORATION: '协作复盘',
}

const recentDaily = computed(() =>
  Array.isArray(learning.value.recentDaily) ? learning.value.recentDaily : []
)

const recentDailyBars = computed(() => {
  const map = new Map()
  for (const r of recentDaily.value) {
    const key = String(r.date || '').slice(0, 10)
    if (key) map.set(key, Number(r.durationSeconds) || 0)
  }
  const days = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  for (let i = 13; i >= 0; i -= 1) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    const key = formatISODate(d)
    const sec = map.get(key) || 0
    days.push({ date: key, sec, label: `${d.getMonth() + 1}/${d.getDate()}` })
  }
  const max = Math.max(1, ...days.map((x) => x.sec), 1)
  return days.map((x) => ({
    ...x,
    h: Math.max(3, Math.round((x.sec / max) * 56)),
  }))
})

const hasDailyBars = computed(() => recentDailyBars.value.some((d) => d.sec > 0))

const distribution = computed(() =>
  (Array.isArray(learning.value.distribution) ? learning.value.distribution : [])
    .filter((d) => Number(d.percent) > 0)
    .slice()
    .sort((a, b) => Number(b.percent) - Number(a.percent))
)

const abilityAxes = computed(() => {
  const a = ability.value
  if (!a || !a.hasRealEvidence) return []
  const keys = [
    ['problemSolving', '解题'],
    ['coding', '编码'],
    ['communication', '沟通'],
    ['teamwork', '协作'],
    ['presentation', '呈现'],
    ['creativity', '创意'],
  ]
  return keys
    .filter(([key]) => a[key] !== undefined && a[key] !== null)
    .map(([key, label]) => ({
      key,
      label,
      value: Math.min(100, Math.max(0, Number(a[key]) || 0)),
    }))
})

function initial(name) {
  const s = String(name || '?').trim()
  return s ? s.slice(0, 1) : '?'
}

function avatarColor(seed) {
  const s = String(seed ?? '')
  let hash = 0
  for (let i = 0; i < s.length; i += 1) hash = (hash * 31 + s.charCodeAt(i)) >>> 0
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

function tagClass(t) {
  if (/缺交|待批|整改/.test(t)) return 'is-danger'
  if (/偏低|未路演/.test(t)) return 'is-warn'
  return 'is-info'
}

function dimensionName(code) {
  const key = String(code || '')
  return DIMENSION_NAMES[key] || DIMENSION_NAMES[key.toLowerCase()] || key || '维度'
}
function activityLabel(t) {
  return ACTIVITY_NAMES[t] || t
}
function formatNum(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '0'
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}
function scoreText(v) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? (Number.isInteger(n) ? String(n) : n.toFixed(1)) : '—'
}
function formatDuration(seconds) {
  const n = Math.max(0, Math.round(Number(seconds) || 0))
  if (!n) return '0 分'
  const h = Math.floor(n / 3600)
  const m = Math.floor((n % 3600) / 60)
  if (h > 0) return m ? `${h}时${m}分` : `${h}时`
  if (m > 0) return `${m} 分`
  return `${n} 秒`
}
function formatDay(v) {
  if (!v) return '—'
  return String(v).slice(0, 10)
}
function formatDayShort(v) {
  if (!v) return ''
  const s = String(v).slice(0, 10)
  const parts = s.split('-')
  if (parts.length === 3) return `${Number(parts[1])}/${Number(parts[2])}`
  return s
}
function formatDateTime(v) {
  if (!v) return '—'
  return String(v).replace('T', ' ').slice(0, 16)
}
function formatISODate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function dayStatusKey(d) {
  const st = String(d.status || '').toUpperCase()
  if (d.submissionId) {
    if (['PENDING_REVIEW', 'REVIEWING'].includes(st)) return 'pending'
    if (['APPROVED', 'PASSED', 'REVIEWED'].includes(st)) return 'ok'
    return 'submitted'
  }
  if (st === 'EXPIRED') return 'missing'
  return 'todo'
}
function dayStatusLabel(d) {
  const map = {
    pending: '待批',
    ok: '通过',
    submitted: '已交',
    missing: '缺交',
    todo: '未交',
  }
  return map[dayStatusKey(d)] || String(d.status || '—')
}
function dayTitle(d) {
  return `第 ${d.dayNo} 天 · ${dayStatusLabel(d)} · ${formatDay(d.trainingDate)}`
}
function dimWidth(p) {
  return Math.max(4, Math.round((Number(p) / maxDeducted.value) * 100))
}

function detailRowKey(row, idx) {
  return row.resourceId || row.sessionId || row.documentId || row.dayId || idx
}
function detailRowTitle(row) {
  if (detailTab.value === 'platform' || detailTab.value === 'embed') {
    return row.title || '未命名视频'
  }
  if (detailTab.value === 'dwell') {
    const day = row.dayNo ? `第 ${row.dayNo} 天` : `训练日 #${row.dayId}`
    return row.dayTitle ? `${day} · ${row.dayTitle}` : day
  }
  if (detailTab.value === 'typing') {
    return row.mode === 'ranked' ? '排位赛' : '自主练习'
  }
  if (detailTab.value === 'inspire') {
    return row.title || `文档 #${row.documentId}`
  }
  return '记录'
}
function detailRowMeta(row) {
  if (detailTab.value === 'platform' || detailTab.value === 'embed') {
    const parts = []
    if (row.dayNo) parts.push(`第 ${row.dayNo} 天`)
    if (row.dayTitle) parts.push(row.dayTitle)
    if (row.trainingDate) parts.push(formatDay(row.trainingDate))
    parts.push(`进度 ${row.progressPercent || 0}%`)
    return parts.join(' · ')
  }
  if (detailTab.value === 'dwell') {
    const parts = [formatDay(row.trainingDate)]
    if (row.endedAt) parts.push(`最近 ${formatDateTime(row.endedAt)}`)
    return parts.join(' · ')
  }
  if (detailTab.value === 'typing') {
    return `${formatDateTime(row.createdAt)} · ${row.cpm || 0} CPM · 正确率 ${formatAcc(row.accuracy)}%`
  }
  if (detailTab.value === 'inspire') {
    const parts = [inspireKindLabel(row.documentKind)]
    if (row.documentExt) parts.push(String(row.documentExt).replace(/^\./, ''))
    if (row.documentScope) parts.push(inspireScopeLabel(row.documentScope))
    if (row.endedAt) parts.push(`最近 ${formatDateTime(row.endedAt)}`)
    parts.push(`编辑 ${formatDuration(row.editSeconds)}`)
    return parts.join(' · ')
  }
  return ''
}
function detailRowSeconds(row) {
  if (detailTab.value === 'inspire') return row.onlineSeconds ?? row.seconds
  return row.seconds
}
function formatAcc(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return Math.round(n * 10) / 10
}
function inspireKindLabel(kind) {
  return ({ word: '文档', sheet: '表格', slide: '演示' }[String(kind || '').toLowerCase()] || '文档')
}
function inspireScopeLabel(scope) {
  return ({ personal: '个人', project: '项目', team: '团队' }[String(scope || '').toLowerCase()] || scope || '')
}

async function load() {
  const id = route.params.userId
  if (!id) {
    error.value = '缺少学生 ID'
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    data.value = (await fetchTeacherStudentProfile(id)) || {}
    detailTab.value = ''
  } catch (err) {
    error.value = err?.message || '档案加载失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

watch(() => route.params.userId, load, { immediate: true })
</script>

<style scoped>
.teacher-muted {
  color: var(--ds-muted);
}
.back-row {
  margin: 0 0 4px;
}
.plan-notice {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}
.students-empty {
  display: grid;
  gap: 12px;
  justify-items: center;
}
.students-empty p {
  margin: 0;
}

/* 身份卡 */
.hero-card {
  padding: 16px 18px;
  border: 1px solid var(--ds-line);
  border-radius: 16px;
  background: #fff;
  margin-bottom: 12px;
}
.hero-card__who {
  display: flex;
  align-items: center;
  gap: 14px;
}
.hero-card__meta {
  min-width: 0;
}
.hero-card__name-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.hero-card__name-row strong {
  font-size: 18px;
  font-weight: 800;
}
.hero-card__meta small {
  display: block;
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 13px;
}
.hero-card__one {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fafbfc;
  border: 1px solid var(--ds-line);
  font-size: 13px;
  line-height: 1.5;
  color: var(--ds-ink-2);
  font-weight: 600;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

/* 待办条 */
.todo-strip {
  margin-bottom: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(232, 74, 28, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, #fff8f5, #fff);
}
.todo-strip > header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}
.todo-strip > header strong {
  font-size: 14px;
  font-weight: 800;
  color: var(--ds-orange-deep);
}
.todo-strip > header span {
  font-size: 12px;
  color: var(--ds-muted);
  font-weight: 700;
}
.todo-strip ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.todo-strip li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid var(--ds-line);
}
.todo-strip b {
  display: block;
  font-size: 13px;
  font-weight: 800;
}
.todo-strip small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--ds-muted);
}

/* KPI */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.kpi {
  padding: 12px 14px;
  border: 1px solid var(--ds-line);
  border-radius: 14px;
  background: #fff;
  display: grid;
  gap: 2px;
}
.kpi small {
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}
.kpi strong {
  font-size: 22px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
  color: var(--ds-ink);
}
.kpi strong.is-warn {
  color: var(--ds-orange-deep);
}
.kpi em {
  font-style: normal;
  font-size: 11px;
  color: var(--ds-muted);
}

/* 主栅格 */
.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.9fr);
  gap: 12px;
  align-items: start;
}
.side-stack {
  display: grid;
  gap: 12px;
}

.panel {
  padding: 14px 16px 16px;
  border: 1px solid var(--ds-line);
  border-radius: 16px;
  background: #fff;
}
.panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.panel__head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}
.panel__head p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--ds-muted);
}
.panel__num {
  font-size: 16px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--ds-ink);
  white-space: nowrap;
}

/* 训练日色块 */
.day-board {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 8px;
}
.day-cell {
  appearance: none;
  font: inherit;
  text-align: left;
  padding: 10px 8px;
  border-radius: 12px;
  border: 1px solid var(--ds-line);
  background: #fafbfc;
  display: grid;
  gap: 2px;
  cursor: default;
  min-width: 0;
}
.day-cell__no {
  font-size: 10px;
  font-weight: 800;
  color: var(--ds-muted);
  letter-spacing: 0.02em;
}
.day-cell strong {
  font-size: 13px;
  font-weight: 800;
}
.day-cell small {
  font-size: 10px;
  color: var(--ds-muted);
}
.day-cell[data-status='ok'] {
  background: #f0fdf6;
  border-color: rgba(15, 159, 110, 0.22);
}
.day-cell[data-status='ok'] strong {
  color: #0f6b4c;
}
.day-cell[data-status='pending'] {
  background: #fff7ed;
  border-color: rgba(194, 65, 12, 0.22);
}
.day-cell[data-status='pending'] strong {
  color: #c2410c;
}
.day-cell[data-status='submitted'] {
  background: #eff6ff;
  border-color: rgba(37, 99, 235, 0.2);
}
.day-cell[data-status='submitted'] strong {
  color: #1d4ed8;
}
.day-cell[data-status='missing'] {
  background: #fff1f0;
  border-color: rgba(209, 67, 67, 0.22);
}
.day-cell[data-status='missing'] strong {
  color: #d14343;
}
.day-cell[data-status='todo'] {
  background: #f7f8f9;
}

.day-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 12px;
  font-size: 11px;
  color: var(--ds-muted);
  font-weight: 600;
}
.day-legend span::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 5px;
  vertical-align: 0;
  background: #e5e7eb;
}
.day-legend span[data-status='ok']::before {
  background: #34d399;
}
.day-legend span[data-status='pending']::before {
  background: #fb923c;
}
.day-legend span[data-status='submitted']::before {
  background: #60a5fa;
}
.day-legend span[data-status='missing']::before {
  background: #f87171;
}

/* 学习节奏 */
.mini-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.mini-stats > div {
  padding: 8px;
  border-radius: 10px;
  background: #f7f8f9;
  border: 1px solid var(--ds-line);
  display: grid;
  gap: 2px;
  min-width: 0;
}
.mini-stats small {
  font-size: 10px;
  font-weight: 700;
  color: var(--ds-muted);
}
.mini-stats b {
  font-size: 13px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.bars {
  height: 72px;
  display: flex;
  align-items: flex-end;
  gap: 3px;
  margin-bottom: 10px;
}
.bars__col {
  flex: 1;
  min-width: 0;
  display: grid;
  justify-items: center;
  gap: 3px;
}
.bars__col i {
  width: min(14px, 70%);
  border-radius: 3px 3px 1px 1px;
  background: linear-gradient(180deg, var(--ds-orange), #ff8a5c);
}
.bars__col span {
  font-size: 9px;
  color: var(--ds-muted);
  white-space: nowrap;
}

.dist {
  display: grid;
  gap: 8px;
  margin: 2px 0 8px;
}
.dist-track {
  display: flex;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #ececef;
}
.dist-track i {
  display: block;
  min-width: 2px;
  height: 100%;
}
.dist-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}
.dist-list li {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  line-height: 1.3;
}
.dist-list i,
.dist-track i {
  background: #d7d7dc;
}
.dist-list i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}
.dist-list span {
  color: var(--ds-ink-2);
  font-weight: 650;
  min-width: 0;
}
.dist-list strong {
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  color: var(--ds-ink);
}
.dist-track i.is-training,
.dist-list i.is-training { background: #fb923c; }
.dist-track i.is-typing,
.dist-list i.is-typing { background: #60a5fa; }
.dist-track i.is-task_book,
.dist-list i.is-task_book { background: #34d399; }
.dist-track i.is-inspire_office,
.dist-list i.is-inspire_office { background: #a78bfa; }
.dist-track i.is-course,
.dist-list i.is-course { background: #fbbf24; }
.dist-track i.is-exam,
.dist-list i.is-exam { background: #f472b6; }
.dist-track i.is-roadshow,
.dist-list i.is-roadshow { background: #f87171; }
.dist-track i.is-collaboration,
.dist-list i.is-collaboration { background: #94a3b8; }

.precise-fold {
  margin-top: 8px;
  border-top: 1px solid var(--ds-line);
  padding-top: 8px;
}
.precise-fold > summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  font-weight: 750;
  color: var(--ds-ink-2);
  padding: 6px 0;
  user-select: none;
}
.precise-fold > summary::-webkit-details-marker {
  display: none;
}
.precise-fold > summary em {
  font-style: normal;
  font-weight: 700;
  color: var(--ds-muted);
}
.precise-fold > summary::before {
  content: '▸';
  margin-right: 6px;
  color: var(--ds-muted);
}
.precise-fold[open] > summary::before {
  content: '▾';
}
.precise-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}
.precise-item {
  appearance: none;
  text-align: left;
  font: inherit;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--ds-line);
  background: #f7f8f9;
  display: grid;
  gap: 2px;
  cursor: pointer;
  min-width: 0;
}
.precise-item:hover {
  border-color: rgba(232, 74, 28, 0.28);
}
.precise-item.is-active {
  border-color: rgba(232, 74, 28, 0.45);
  background: #fff7f3;
}
.precise-item small {
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}
.precise-item strong {
  font-size: 15px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.precise-item em {
  font-style: normal;
  font-size: 10px;
  color: var(--ds-muted);
}
.precise-detail {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--ds-line);
}
.precise-detail header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.precise-detail header strong {
  font-size: 12px;
}
.text-button {
  border: 0;
  background: none;
  padding: 0;
  cursor: pointer;
  font: inherit;
}
.detail-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 240px;
  overflow: auto;
}
.detail-list li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f1f3;
}
.detail-list li:last-child {
  border-bottom: 0;
}
.detail-list strong {
  display: block;
  font-size: 12px;
  font-weight: 700;
}
.detail-list small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--ds-muted);
  line-height: 1.4;
}
.detail-list b {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.score-list {
  display: grid;
  gap: 6px;
  margin-bottom: 10px;
}
.score-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--ds-line);
  background: #fffaf7;
}
.score-row strong {
  font-size: 16px;
  color: var(--ds-orange-deep);
  font-variant-numeric: tabular-nums;
}
.score-row small {
  font-size: 11px;
  color: var(--ds-muted);
}

.dim-list {
  display: grid;
  gap: 8px;
}
.dim-row {
  display: grid;
  grid-template-columns: minmax(0, 88px) minmax(0, 1fr) 36px;
  gap: 8px;
  align-items: center;
}
.dim-row strong {
  font-size: 12px;
}
.dim-row__bar {
  height: 6px;
  border-radius: 999px;
  background: #f1f2f4;
  overflow: hidden;
}
.dim-row__bar i {
  display: block;
  height: 100%;
  background: var(--ds-orange);
}
.dim-row > b {
  text-align: right;
  font-size: 12px;
  color: #d14343;
  font-variant-numeric: tabular-nums;
}

.ability-grid {
  display: grid;
  gap: 8px;
}
.ability-item {
  display: grid;
  grid-template-columns: 40px 32px 1fr;
  gap: 8px;
  align-items: center;
  font-size: 12px;
}
.ability-item small {
  color: var(--ds-muted);
  font-weight: 700;
}
.ability-item strong {
  font-variant-numeric: tabular-nums;
}
.ability-item i {
  display: block;
  height: 6px;
  border-radius: 999px;
  background: linear-gradient(90deg, #ffb089, var(--ds-orange));
}

.todo-list {
  display: grid;
  gap: 6px;
}
.todo-row {
  padding: 8px 10px;
  border: 1px solid var(--ds-line);
  border-radius: 10px;
  background: #fafbfc;
  display: grid;
  gap: 2px;
}
.todo-row strong {
  font-size: 13px;
}
.todo-row small {
  font-size: 11px;
  color: var(--ds-muted);
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--ds-muted);
  line-height: 1.5;
}

@media (max-width: 960px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
  .kpi-row {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 520px) {
  .kpi-row {
    grid-template-columns: 1fr;
  }
  .mini-stats {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
