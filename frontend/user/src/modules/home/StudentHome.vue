<template>
  <div
    ref="rootRef"
    class="student-home home-workspace"
    :class="{ 'is-ai-open': aiOpen }"
    data-testid="student-home"
  >
    <div class="home-workspace__main">
      <div class="home-dash">
        <section v-if="loading" class="home-dash__card home-dash__skeleton">
          <el-skeleton :rows="8" animated />
        </section>

        <section v-else-if="error" class="home-dash__card home-dash__error">
          <div class="home-dash__empty">
            <WarningFilled class="home-dash__empty-icon" />
            <h2>首页数据暂时没有加载出来</h2>
            <p>{{ error }}</p>
            <InteractiveHoverButton @click="load">重新加载</InteractiveHoverButton>
          </div>
        </section>

        <template v-else>
          <!-- ① 状态栏 -->
          <header class="home-status" data-testid="home-hero">
            <div class="home-status__identity">
              <p class="home-status__eyebrow">{{ statusEyebrow }}</p>
              <h1>{{ greetingLine }}</h1>
              <p class="home-status__sub">{{ statusSubline }}</p>
            </div>

            <div class="home-status__metrics" data-testid="home-countdown-panel">
              <div class="home-status__countdown">
                <span>{{ hasCamp ? '距离备赛结束' : '备赛状态' }}</span>
                <strong v-if="hasCamp && camp.remainingDays !== undefined">
                  {{ camp.remainingDays }}<small>天</small>
                </strong>
                <strong v-else class="is-empty is-soft">{{ hasCamp ? '—' : '待开启' }}</strong>
                <p>{{ countdownHint }}</p>
              </div>

              <div
                class="home-status__progress"
                aria-label="备赛进度"
                :aria-valuetext="progressAriaText"
              >
                <div class="home-status__progress-head">
                  <span>备赛进度</span>
                  <em>
                    <template v-if="progressTotal > 0">{{ progressLabel }}</template>
                    <template v-else>尚未开始</template>
                  </em>
                </div>
                <div class="home-status__track" aria-hidden="true">
                  <i :style="{ width: `${progressPercent}%` }" />
                </div>
              </div>
            </div>
          </header>

          <!-- ② 今日任务（主视觉 + 清单） -->
          <section
            class="home-primary"
            data-testid="home-today-card"
            aria-labelledby="home-primary-task-title"
          >
            <div class="home-primary__core">
              <template v-if="todayTraining.hasTrainingDay">
                <div class="home-primary__main">
                  <div class="home-primary__kicker">
                    <span class="home-primary__badge">
                      <i class="home-primary__dot" aria-hidden="true" />
                      今日任务
                    </span>
                    <span v-if="primaryAiRecommended" class="home-primary__ai">评分驱动</span>
                    <span
                      class="home-primary__focus-state"
                      :data-state="primaryTaskDone ? 'done' : 'todo'"
                    >
                      {{ primaryTaskDone ? '已完成' : '未开始' }}
                    </span>
                  </div>

                  <h2 id="home-primary-task-title" class="home-primary__title">
                    {{ primaryTaskTitle }}
                  </h2>
                  <p v-if="primaryTaskSummary" class="home-primary__summary">
                    {{ primaryTaskSummary }}
                  </p>

                  <p class="home-primary__meta">
                    <span v-if="estimatedMinutes">{{ estimatedMinutes }} 分钟</span>
                    <span v-if="primaryFocusLabel" class="home-primary__chip">{{ primaryFocusLabel }}</span>
                    <span v-if="primaryMetaNote">{{ primaryMetaNote }}</span>
                  </p>
                </div>

                <aside class="home-primary__rail">
                  <div class="home-primary__est">
                    <span>预计投入</span>
                    <strong>
                      {{ estimatedMinutes || '—' }}
                      <small v-if="estimatedMinutes">分钟</small>
                    </strong>
                  </div>
                  <div class="home-primary__cta">
                    <InteractiveHoverButton
                      :to="primaryCta.to"
                      data-testid="home-primary-cta"
                    >
                      {{ primaryCta.label }}
                    </InteractiveHoverButton>
                    <InteractiveHoverButton type="secondary" to="/training/plan">
                      查看训练计划
                    </InteractiveHoverButton>
                  </div>
                </aside>
              </template>

              <template v-else>
                <div class="home-primary__main home-primary__main--empty">
                  <div class="home-primary__kicker">
                    <span class="home-primary__badge">
                      <i class="home-primary__dot" aria-hidden="true" />
                      今日任务
                    </span>
                    <span class="home-primary__focus-state" data-state="idle">{{ primaryEmpty.badge }}</span>
                  </div>
                  <h2 id="home-primary-task-title" class="home-primary__title">{{ primaryEmpty.title }}</h2>
                  <p class="home-primary__summary">{{ primaryEmpty.summary }}</p>
                </div>
                <aside class="home-primary__rail">
                  <div class="home-primary__cta">
                    <InteractiveHoverButton :to="primaryEmpty.primary.to" data-testid="home-primary-cta">
                      {{ primaryEmpty.primary.label }}
                    </InteractiveHoverButton>
                    <InteractiveHoverButton
                      v-if="primaryEmpty.secondary"
                      type="secondary"
                      :to="primaryEmpty.secondary.to"
                    >
                      {{ primaryEmpty.secondary.label }}
                    </InteractiveHoverButton>
                  </div>
                </aside>
              </template>
            </div>

            <!-- 今日清单：交付要求 / 同日任务 / 待办明细，不与上方大标题重复 -->
            <div v-if="taskListItems.length" class="home-primary__list" data-testid="home-task-list">
              <div class="home-primary__list-head">
                <span>今日清单</span>
                <em>{{ taskListHeadMeta }}</em>
              </div>
              <ol class="home-primary__plan">
                <li
                  v-for="(item, index) in taskListItems"
                  :key="item.key || index"
                  :class="{ 'is-main': item.primary, 'has-detail': Boolean(item.detail) }"
                >
                  <span class="home-primary__mark" :class="{ 'is-opt': !item.primary }">
                    {{ item.mark || (item.primary ? '必交' : '待办') }}
                  </span>
                  <div class="home-primary__plan-body">
                    <RouterLink v-if="item.to" class="home-primary__plan-title" :to="item.to">
                      {{ item.title }}
                    </RouterLink>
                    <span v-else class="home-primary__plan-title">{{ item.title }}</span>
                    <p v-if="item.detail" class="home-primary__plan-detail">{{ item.detail }}</p>
                  </div>
                  <em>{{ item.meta }}</em>
                </li>
              </ol>
            </div>
          </section>

          <!-- ③ 双卡：近一周训练 + AI 能力诊断（开小启时诊断可保留，路演细节收进诊断卡） -->
          <section class="home-secondary" data-testid="home-grid" aria-label="备赛概况">
            <article class="home-card" data-testid="home-progress-card">
              <header class="home-card__head">
                <div class="home-card__title">
                  <span class="home-card__icon" aria-hidden="true">
                    <WorkspaceModuleIcon name="progress" variant="outline" />
                  </span>
                  <div>
                    <h2>近一周训练</h2>
                    <p>{{ hasWeeklyActivity ? '训练投入与趋势' : '完成练习后自动累计' }}</p>
                  </div>
                </div>
              </header>

              <template v-if="hasWeeklyActivity">
                <div class="home-card__stats" aria-label="近一周学习统计">
                  <div>
                    <span>近一周累计</span>
                    <strong>
                      {{ formatMinutesValue(weeklyLearning.totalSeconds) }}
                      <small>分钟</small>
                    </strong>
                  </div>
                  <div>
                    <span>今日训练</span>
                    <strong>
                      {{ formatMinutesValue(weeklyLearning.todaySeconds ?? weeklyTodaySeconds) }}
                      <small>分钟</small>
                    </strong>
                  </div>
                  <div>
                    <span>日均时长</span>
                    <strong>
                      {{ formatMinutesValue(weeklyAverageSeconds) }}
                      <small>分/天</small>
                    </strong>
                  </div>
                </div>

                <div class="home-card__chart">
                  <WeeklyLearningChart
                    v-if="weeklyChartPoints.length"
                    :points="weeklyChartPoints"
                    :scale-minutes="weeklyScaleMinutes"
                    :aria-label="weeklyChartAria"
                  />
                </div>
                <p class="home-card__foot">完成课程、练习、路演或协作后自动记录</p>
              </template>

              <div v-else class="home-card__empty">
                <span class="home-card__empty-icon" aria-hidden="true">
                  <WorkspaceModuleIcon name="learning" variant="outline" />
                </span>
                <strong>{{ weeklyEmpty.title }}</strong>
                <p>{{ weeklyEmpty.detail }}</p>
                <InteractiveHoverButton size="small" :to="weeklyEmpty.cta.to">
                  {{ weeklyEmpty.cta.label }}
                </InteractiveHoverButton>
              </div>
            </article>

            <article class="home-card home-card--score" data-testid="home-score-card">
              <header class="home-card__head">
                <div class="home-card__title">
                  <span class="home-card__icon" aria-hidden="true">
                    <WorkspaceModuleIcon name="review" variant="outline" />
                  </span>
                  <div>
                    <h2>AI 能力诊断</h2>
                    <p>
                      {{ latestScore.hasReport ? '最近一次路演 · 官方五维' : '完成路演后生成诊断' }}
                    </p>
                  </div>
                </div>
                <em
                  v-if="roadshowFocus.badge"
                  class="home-card__chip"
                  :data-tone="roadshowFocus.statusTone"
                >
                  {{ roadshowFocus.badge }}
                </em>
              </header>

              <template v-if="latestScore.hasReport">
                <div class="home-score home-score--row">
                  <div class="home-score__priority">
                    <span>综合分</span>
                    <strong>
                      {{ Number(latestScore.overallScore || 0).toFixed(1) }}
                      <small>/100</small>
                    </strong>
                    <em>优先：{{ weakestDimension?.label || '—' }} {{ weakestDimension?.shortValue || '' }}</em>
                  </div>
                  <div class="home-score__radar">
                    <HomeScoreRadar
                      v-if="scoreRadarDimensions.length"
                      :dimensions="scoreRadarDimensions"
                    />
                    <div v-else class="home-score__radar-empty">
                      <p>本场报告暂无五维数据，可打开完整报告。</p>
                    </div>
                  </div>
                </div>
                <div class="home-score__next">
                  <span>下一轮观察</span>
                  <p>{{ nextObservation }}</p>
                  <div class="home-card__actions">
                    <InteractiveHoverButton size="small" :to="scorePath">打开评分报告</InteractiveHoverButton>
                    <InteractiveHoverButton
                      type="secondary"
                      size="small"
                      :to="roadshowFocus.primary.to"
                    >
                      {{ roadshowFocus.primary.label }}
                    </InteractiveHoverButton>
                  </div>
                </div>
              </template>

              <div v-else class="home-card__empty">
                <span class="home-card__empty-icon" aria-hidden="true">
                  <WorkspaceModuleIcon name="review" variant="outline" />
                </span>
                <strong>{{ scoreEmpty.title }}</strong>
                <p>{{ scoreEmpty.detail }}</p>
                <div class="home-card__empty-actions">
                  <InteractiveHoverButton size="small" :to="scoreEmpty.cta.to">
                    {{ scoreEmpty.cta.label }}
                  </InteractiveHoverButton>
                  <InteractiveHoverButton
                    type="secondary"
                    size="small"
                    :to="roadshowFocus.primary.to"
                  >
                    {{ roadshowFocus.primary.label }}
                  </InteractiveHoverButton>
                </div>
              </div>
            </article>
          </section>
        </template>
      </div>
    </div>

    <!-- 小启：文档流内半栏，CSS Grid 平推（非 fixed 遮罩） -->
    <div class="home-workspace__ai" :aria-hidden="String(!aiOpen)">
      <HomeXiaoQiPanel
        v-if="aiMounted"
        :home="data"
        :open="aiOpen"
        @close="closeAi"
      />
    </div>

    <button
      v-show="!aiOpen && !loading && !error"
      type="button"
      class="home-xiaoqi-fab"
      title="打开小启"
      aria-label="打开小启 AI"
      @click="openAi"
    >
      <XiaoQiMark :size="64" :hoverable="true" />
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { WarningFilled } from '@element-plus/icons-vue'
import InteractiveHoverButton from '../../components/base/InteractiveHoverButton.vue'
import WeeklyLearningChart from '../../components/dashboard/WeeklyLearningChart.vue'
import HomeScoreRadar from '../../components/dashboard/HomeScoreRadar.vue'
import WorkspaceModuleIcon from '../../components/workspace/WorkspaceModuleIcon.vue'
import XiaoQiMark from '../../components/brand/XiaoQiMark.vue'
import HomeXiaoQiPanel from './HomeXiaoQiPanel.vue'
import { fetchStudentHome } from '../training/api'
import { formatDate, formatDateTime } from '../training/format'
import { dimensionDisplayName } from '../../utils/aiScoreDimensions'

defineOptions({ name: 'DashboardHome' })

const rootRef = ref(null)
const loading = ref(true)
const error = ref('')
const data = ref({})
/** 小启嵌入分栏：仅 CSS 改 grid，数据仍用同一份 home payload */
const aiOpen = ref(false)
const aiMounted = ref(false)
let hasActivatedOnce = false

/** keep-alive 回填时清掉路由过渡粘在根节点上的 opacity:0 */
function scrubHomeTransitionResidue() {
  const el = rootRef.value
  if (!el) return
  el.style.opacity = ''
  el.style.transform = ''
  el.style.pointerEvents = ''
  const residue = [
    'workspace-route-enter-from',
    'workspace-route-enter-active',
    'workspace-route-enter-to',
    'workspace-route-leave-from',
    'workspace-route-leave-active',
    'workspace-route-leave-to',
  ]
  for (const c of residue) el.classList.remove(c)
}

const profile = computed(() => data.value.profile || {})
const camp = computed(() => {
  const value = data.value.camp || {}
  return Object.keys(value).length ? value : { hasCamp: false }
})
const planSummary = computed(() => data.value.planSummary || {})
const todayTraining = computed(() => data.value.todayTraining || {})
const weeklyLearning = computed(() => data.value.weeklyLearning || {})
const roadshow = computed(() => data.value.roadshow || {})
const latestScore = computed(() => data.value.latestScore || {})

const displayName = computed(() => profile.value.username || '同学')
const hasCamp = computed(() => {
  if (camp.value.hasCamp === false) return false
  return Boolean(camp.value.campId || camp.value.campName)
})
const trainingDayNumber = computed(() => {
  const value = Number(camp.value.currentDay)
  return Number.isInteger(value) && value > 0 ? value : null
})

const greetingLine = computed(() => {
  const hour = new Date().getHours()
  let prefix = '你好'
  if (hour < 11) prefix = '早上好'
  else if (hour < 14) prefix = '中午好'
  else if (hour < 18) prefix = '下午好'
  else prefix = '晚上好'
  return `${prefix}，${displayName.value}`
})

const statusEyebrow = computed(() => {
  if (trainingDayNumber.value) return `备赛第 ${trainingDayNumber.value} 天`
  if (hasCamp.value) return '备赛工作台'
  return '欢迎来到竞赛大脑'
})

/** 结束日用「X月X日」，避免 8/16 被误读 */
function formatMonthDayCn(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

const countdownHint = computed(() => {
  if (hasCamp.value && camp.value.endDate) return `${formatMonthDayCn(camp.value.endDate)}结束`
  if (hasCamp.value) return '训练营已开启，加油'
  return '加入训练营后开始计时'
})

const primaryTask = computed(() => todayTraining.value.primaryTask || {})
const primaryRequirements = computed(() => primaryTask.value.requirements || [])
const primaryTaskDone = computed(() => Boolean(primaryTask.value.latestSubmissionId))

const primaryTaskTitle = computed(() => (
  todayTraining.value.title
  || primaryTask.value.title
  || '完成今日训练'
))

const primaryTaskSummary = computed(() => (
  todayTraining.value.summary
  || primaryTask.value.description
  || firstImprovement.value
  || '按老师发布的要求完成交付，稳稳拿下今天的进度。'
))

const primaryFocusLabel = computed(() => {
  const required = primaryRequirements.value.find(item => item?.required)
  const first = required || primaryRequirements.value[0]
  if (first?.title) return first.title
  if (weakestDimension.value?.label) return weakestDimension.value.label
  return ''
})

const primaryAiRecommended = computed(() => (
  Boolean(latestScore.value.hasReport && (weakestDimension.value || firstImprovement.value))
))

const estimatedMinutes = computed(() => {
  const explicit = Number(
    primaryTask.value.estimatedMinutes
    || primaryTask.value.estimateMinutes
    || todayTraining.value.estimatedMinutes
    || 0
  )
  if (Number.isFinite(explicit) && explicit > 0) return Math.round(explicit)
  // 按交付项粗估：每项约 10 分钟，至少 15
  const count = primaryRequirements.value.length
  if (count > 0) return Math.max(15, count * 10)
  return 20
})

const primaryMetaNote = computed(() => {
  if (primaryTaskDone.value) return '已提交，可回看反馈'
  if (latestScore.value.hasReport) return '完成后再录完整路演'
  return todayTraining.value.dueAt
    ? `截止 ${formatDateTime(todayTraining.value.dueAt)}`
    : '完成后标记提交'
})

const primaryCta = computed(() => {
  if (primaryTaskDone.value) {
    const id = primaryTask.value.latestSubmissionId
    return {
      label: '查看提交',
      to: id ? `/training/submissions/${id}` : '/training/today'
    }
  }
  return {
    label: latestScore.value.hasReport ? '开始专项复练' : '去完成',
    to: '/training/today'
  }
})

/** 是否为已过期团队待办（无今日训练时不进「今日清单」） */
function isExpiredNextAction(action) {
  if (!action || typeof action !== 'object') return false
  if (String(action.priority || '').toUpperCase() === 'EXPIRED') return true
  const meta = String(action.meta || '')
  return meta.includes('已过期')
}

function normalizeListText(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

function isDailyReportRequirement(item = {}) {
  const asset = String(item.assetType || item.asset_type || '').toUpperCase()
  if (asset === 'DAILY_REPORT') return true
  const title = String(item.title || '')
  return /日报/.test(title)
}

function isTypingPracticeRequirement(item = {}) {
  const asset = String(item.assetType || item.asset_type || '').toUpperCase()
  if (asset === 'TYPING_PRACTICE') return true
  const title = String(item.title || '')
  return /打字/.test(title)
}

function requirementHref(item = {}) {
  if (isDailyReportRequirement(item)) return '/daily-reports/write'
  if (isTypingPracticeRequirement(item)) return '/typing-practice'
  return '/training/today'
}

function clipDetail(text, max = 96) {
  const value = normalizeListText(text)
  if (!value) return ''
  // keep original spacing for display, only clip length
  const raw = String(text || '').replace(/\s+/g, ' ').trim()
  if (raw.length <= max) return raw
  return `${raw.slice(0, max - 1)}…`
}

/**
 * 今日清单：交付要求 / 同日其他任务 / 未过期待办
 * - 不再把上方「今日任务」大标题再列一行（信息重复）
 * - 优先展示老师拆好的交付要求（含说明）
 */
const taskListItems = computed(() => {
  const items = []
  const seen = new Set()
  const hasDay = Boolean(todayTraining.value.hasTrainingDay)
  const heroTitle = normalizeListText(primaryTaskTitle.value)
  const primaryTaskId = primaryTask.value.taskId ?? primaryTask.value.id ?? null

  const pushItem = (item) => {
    if (!item?.title) return
    const title = String(item.title).trim()
    if (!title) return
    // 与主视觉标题同文案的「任务行」不进清单；交付要求即使同名也保留（少见）
    if (item.kind !== 'requirement' && heroTitle && normalizeListText(title) === heroTitle) return
    const key = `${item.kind || 'item'}|${title}|${item.to || ''}`
    if (seen.has(key)) return
    seen.add(key)
    items.push({ ...item, title })
  }

  if (hasDay) {
    // 1) 老师拆的交付要求 —— 清单主体
    primaryRequirements.value.forEach((req, index) => {
      if (!req?.title) return
      const required = req.required !== false && req.required !== 0 && req.required !== '0'
      pushItem({
        key: `req-${req.id || index}`,
        kind: 'requirement',
        primary: required,
        mark: required ? '必交' : '可选',
        title: req.title,
        detail: clipDetail(req.description),
        meta: isDailyReportRequirement(req)
          ? '写日报'
          : isTypingPracticeRequirement(req)
            ? '去练习'
            : (required ? '交付要求' : '可选'),
        to: requirementHref(req),
      })
    })

    // 2) 同日其他任务（非主任务）
    const dayTasks = Array.isArray(todayTraining.value.tasks) ? todayTraining.value.tasks : []
    dayTasks.forEach((task, index) => {
      if (!task?.title) return
      const taskId = task.taskId ?? task.id
      const isPrimary = Number(task.isPrimary) === 1
        || (primaryTaskId != null && String(taskId) === String(primaryTaskId))
      if (isPrimary) return
      pushItem({
        key: `task-${taskId || index}`,
        kind: 'task',
        primary: false,
        mark: '任务',
        title: task.title,
        detail: clipDetail(task.description),
        meta: task.latestSubmissionId ? '已提交' : '同日任务',
        to: taskId
          ? `/training/tasks/${taskId}${todayTraining.value.dayId ? `?dayId=${todayTraining.value.dayId}` : ''}`
          : '/training/today',
      })
    })

    // 3) 若老师没拆交付要求：用任务说明作一条「按说明完成」，仍不重复大标题
    if (!primaryRequirements.value.length) {
      const brief = clipDetail(
        primaryTask.value.description || todayTraining.value.summary || '',
        120
      )
      if (brief && normalizeListText(brief) !== heroTitle) {
        pushItem({
          key: 'task-brief',
          kind: 'brief',
          primary: true,
          mark: '说明',
          title: '按任务说明完成交付',
          detail: brief,
          meta: primaryTaskDone.value ? '已提交' : '查看任务书',
          to: primaryCta.value.to,
        })
      }
    }
  }

  ;(data.value.nextActions || []).forEach((action, index) => {
    if (!action?.title) return
    if (action.priority === 'PRIMARY' && hasDay) return
    if (isExpiredNextAction(action)) return
    // 有今日训练时，跳过与主任务同名的 nextAction（后端会把 primary 再塞进 nextActions）
    if (hasDay && heroTitle && normalizeListText(action.title) === heroTitle) return
    pushItem({
      key: `action-${action.taskId || index}`,
      kind: 'action',
      primary: false,
      mark: action.type === 'TASK_BOOK' ? '任务书' : '待办',
      title: action.title,
      detail: clipDetail(action.detail || action.description || ''),
      meta: action.meta || (action.type === 'TASK_BOOK' ? '本场任务书' : action.type === 'TASK' ? '团队待办' : '待办'),
      to: action.path || '/project-team',
    })
  })

  return items.slice(0, 8)
})

const taskListHeadMeta = computed(() => {
  const items = taskListItems.value
  if (!items.length) return ''
  const reqCount = items.filter((item) => item.kind === 'requirement').length
  if (reqCount > 0) {
    const other = items.length - reqCount
    return other > 0
      ? `${reqCount} 项交付 · ${other} 项待办`
      : `${reqCount} 项交付要求`
  }
  return `${items.length} 项 · 待办与说明`
})

/** 分栏宽度变化后强制 ECharts 重算，避免图表横向画穿/被裁 */
function notifyLayoutResize() {
  const fire = () => {
    try {
      window.dispatchEvent(new Event('resize'))
    } catch {
      /* ignore */
    }
  }
  requestAnimationFrame(() => {
    requestAnimationFrame(fire)
  })
  window.setTimeout(fire, 80)
  window.setTimeout(fire, 420)
}

function openAi() {
  aiMounted.value = true
  // 双 rAF：先挂载再切换 class，避免首帧闪烁与重排卡顿
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      aiOpen.value = true
      notifyLayoutResize()
    })
  })
}

function closeAi() {
  aiOpen.value = false
  notifyLayoutResize()
}

function onKeydown(event) {
  if (event.key === 'Escape' && aiOpen.value) closeAi()
}

/** 问候区副文案：务实、不灌鸡汤；眉题已有「备赛第 N 天」，此处不重复 */
const statusSubline = computed(() => {
  const hour = new Date().getHours()
  const inCamp = hasCamp.value && trainingDayNumber.value

  if (!hasCamp.value) {
    return '先确认项目与训练安排，再选一件今天能推进的事。'
  }

  if (hour < 11) {
    if (inCamp) return '今天优先把主线任务推进到位，完成一项再开下一项。'
    return '先看清今天要做什么，再动手会更省时间。'
  }
  if (hour < 14) {
    if (inCamp) return '中午前尽量把关键交付往前推一截，午后也好接着做。'
    return '午间可短歇，回来继续把待办清掉。'
  }
  if (hour < 18) {
    if (inCamp) return '下午适合攻难点：先完成一件，再切换其他事项。'
    return '把待办按优先级排一下，先做最影响进度的那件。'
  }
  if (inCamp) return '收工前核对提交与截止项，有缺口就记下明天接着做。'
  return '今天到这里也可以，明天从最紧的一项接着推进。'
})

/** 今日任务空状态：无训练日 / 无训练营 / 新用户 */
const primaryEmpty = computed(() => {
  if (!hasCamp.value) {
    return {
      badge: '待开启',
      title: '还没有加入训练营',
      summary: '先完成项目组队，或等待老师把你加入训练营。准备好之后，今天的任务会出现在这里。',
      primary: { label: '去项目团队', to: '/project-team' },
      secondary: { label: '看看训练计划', to: '/training/plan' }
    }
  }
  if (todayTraining.value.nextDay?.trainingDate) {
    return {
      badge: '休息日',
      title: '今天暂未安排训练',
      summary: `下一次在 ${formatDate(todayTraining.value.nextDay.trainingDate)}。可以先回看计划，或练一场路演保持手感。`,
      primary: { label: '查看训练计划', to: '/training/plan' },
      secondary: { label: '开始路演', to: '/online-meeting' }
    }
  }
  return {
    badge: '待发布',
    title: '今天暂未安排训练',
    summary: '老师还没有发布今日训练。先把节奏放缓，或者主动练一场路演，也是很好的准备。',
    primary: { label: '查看训练计划', to: '/training/plan' },
    secondary: { label: '开始路演', to: '/online-meeting' }
  }
})

const hasWeeklyActivity = computed(() => Number(weeklyLearning.value.totalSeconds || 0) > 0)

const weeklyEmpty = computed(() => ({
  title: '近一周还没有学习记录',
  detail: hasCamp.value
    ? '打开课程、完成今日训练或练一场路演，时长会自动累计。不用着急，从一件小事开始就好。'
    : '加入训练营并开始练习后，这里会记录你的投入。先去熟悉一下环境吧。',
  cta: hasCamp.value
    ? { label: '查看今日训练', to: '/training/today' }
    : { label: '去项目团队', to: '/project-team' }
}))

const progressCurrent = computed(() => {
  const fromCamp = Number(camp.value.currentDay)
  if (Number.isFinite(fromCamp) && fromCamp >= 0) return fromCamp
  const fromPlan = Number(planSummary.value.completedDays)
  if (Number.isFinite(fromPlan) && fromPlan >= 0) return fromPlan
  return 0
})

const progressTotal = computed(() => {
  const fromCamp = Number(camp.value.totalDays)
  if (Number.isFinite(fromCamp) && fromCamp > 0) return fromCamp
  const fromPlan = Number(planSummary.value.totalDays)
  if (Number.isFinite(fromPlan) && fromPlan > 0) return fromPlan
  return 0
})

const progressPercent = computed(() => {
  if (!progressTotal.value) return 0
  return Math.max(0, Math.min(100, (progressCurrent.value / progressTotal.value) * 100))
})

/** 避免「17/21天」被误读为分数；用「第 N 天 · 共 M 天」 */
const progressLabel = computed(() => {
  const cur = progressCurrent.value
  const total = progressTotal.value
  if (!total) return '尚未开始'
  // 眉题已写「备赛第 N 天」时，进度只补总天数，避免重复抢眼
  if (trainingDayNumber.value && trainingDayNumber.value === cur) {
    return `全程共 ${total} 天`
  }
  return `第 ${cur} 天 · 共 ${total} 天`
})

const progressAriaText = computed(() => {
  if (!progressTotal.value) return '备赛进度尚未开始'
  return `备赛第 ${progressCurrent.value} 天，全程共 ${progressTotal.value} 天`
})

const elapsedWeekDays = computed(() => {
  const start = parseLocalDate(weeklyLearning.value.weekStart)
  const today = parseLocalDate(weeklyLearning.value.serverDate)
  if (!start || !today) return 1
  return Math.max(1, Math.min(7, Math.round((today - start) / 86400000) + 1))
})

const weeklyAverageSeconds = computed(() => (
  Number(weeklyLearning.value.totalSeconds || 0) / elapsedWeekDays.value
))

const weeklyTodaySeconds = computed(() => {
  const serverDate = String(weeklyLearning.value.serverDate || '').slice(0, 10)
  const row = (weeklyLearning.value.daily || []).find(
    item => String(item.date || '').slice(0, 10) === serverDate
  )
  return Number(row?.durationSeconds || 0)
})

const weeklyScaleMinutes = computed(() => {
  const maxMinutes = Math.max(
    0,
    ...(weeklyLearning.value.daily || []).map(item => Math.ceil(Number(item.durationSeconds || 0) / 60))
  )
  const step = maxMinutes <= 30 ? 15 : maxMinutes <= 120 ? 30 : 60
  return Math.max(30, Math.ceil(maxMinutes / step) * step)
})

const weeklyChartPoints = computed(() => buildWeeklyChartPoints(weeklyLearning.value, weeklyScaleMinutes.value))

const weeklyChartAria = computed(() => (
  `近一周学习时长：累计 ${formatMinutesValue(weeklyLearning.value.totalSeconds)} 分钟，日均 ${formatMinutesValue(weeklyAverageSeconds.value)} 分`
))

const scorePath = computed(() => {
  if (latestScore.value.sessionId) return `/ai-score/report/${latestScore.value.sessionId}/result`
  if (latestScore.value.reportId) return `/ai-score/report-id/${latestScore.value.reportId}/result`
  return '/online-meeting'
})

const firstImprovement = computed(() => {
  const first = latestScore.value.improvementPriorities?.[0]
  if (typeof first === 'string') return first
  return first?.issue || first?.suggestion || first?.title || first?.description || ''
})

const scoreRadarDimensions = computed(() => {
  const source = latestScore.value.dimensions
  if (!source || typeof source !== 'object') return []

  const entries = Array.isArray(source)
    ? source.map((item, index) => [item.key || item.name || `d-${index}`, item])
    : Object.entries(source)

  return entries.map(([key, raw]) => {
    if (raw && typeof raw === 'object') {
      const score = Number(raw.score ?? raw.value ?? 0)
      const maxScore = Number(raw.max_score || raw.maxScore || 0)
      return {
        key,
        label: dimensionDisplayName(key, raw.name || raw.label),
        shortValue: formatScoreShort(score),
        percent: maxScore
          ? Math.max(0, Math.min(100, (score / maxScore) * 100))
          : Math.max(0, Math.min(100, score))
      }
    }
    const score = Number(raw || 0)
    return {
      key,
      label: dimensionDisplayName(key),
      shortValue: formatScoreShort(score),
      percent: Math.max(0, Math.min(100, score))
    }
  })
})

const weakestDimension = computed(() => {
  if (!scoreRadarDimensions.value.length) return null
  return [...scoreRadarDimensions.value].sort((a, b) => a.percent - b.percent)[0]
})

const nextObservation = computed(() => {
  if (firstImprovement.value) return firstImprovement.value
  if (weakestDimension.value?.label) {
    return `${weakestDimension.value.label}是否提升：专项复练完成后，用新一轮评分验证。`
  }
  return '完成一场完整路演后，会在这里给出下一轮观察点。'
})

const roadshowDurationLabel = computed(() => {
  const minutes = Number(roadshow.value.durationMinutes || 0)
  if (!Number.isFinite(minutes) || minutes <= 0) return ''
  // 展示为「实际 / 建议区间」风格，若无建议则只写分钟
  if (minutes >= 50) return `${minutes} 分钟`
  return `${minutes} / 50–60 分钟`
})

/** Backend state, with safe fallback for older payloads. */
const roadshowState = computed(() => {
  if (roadshow.value.state) return roadshow.value.state
  if (roadshow.value.hasTeam === false || (!roadshow.value.hasTeam && !profile.value.teamName && !profile.value.teamId)) {
    return 'NO_TEAM'
  }
  const status = String(roadshow.value.status || '').toUpperCase()
  if (status === 'RUNNING') return 'LIVE'
  if (latestScore.value.hasReport || roadshow.value.hasScoreReport) return 'HAS_SCORE'
  if (roadshow.value.hasRoadshow) return 'RECORDED_NO_SCORE'
  return 'NEVER_PRACTICED'
})

const roadshowHasRecord = computed(() => (
  ['LIVE', 'HAS_SCORE', 'RECORDED_NO_SCORE'].includes(roadshowState.value)
))

const scoreEmpty = computed(() => {
  if (roadshowState.value === 'NO_TEAM') {
    return {
      title: '组队后才能生成诊断',
      detail: 'AI 能力诊断会跟项目与路演绑定。先完成组队，再录一场完整路演即可解锁。',
      cta: { label: '去项目团队', to: '/project-team' }
    }
  }
  if (roadshowState.value === 'RECORDED_NO_SCORE' || roadshowState.value === 'LIVE') {
    return {
      title: '路演已在路上，评分稍后生成',
      detail: '完成路演并生成评分后，这里会给出五维诊断与优先提升点。',
      cta: { label: '查看路演记录', to: '/my-recordings' }
    }
  }
  return {
    title: '还没有 AI 能力诊断',
    detail: '完成一场完整路演并生成评分后，这里会显示五维雷达与优先提升建议。第一次不必追求完美。',
    cta: { label: '开始第一场路演', to: '/online-meeting' }
  }
})

const roadshowFocus = computed(() => {
  const title = roadshow.value.title || '路演练习'
  const meetingId = roadshow.value.meetingId
  const startLabel = roadshow.value.startTime ? formatDateTime(roadshow.value.startTime) : ''
  const duration = Number(roadshow.value.durationMinutes || 0)
  const durationLabel = duration > 0 ? `${duration} 分钟` : ''

  switch (roadshowState.value) {
    case 'NO_TEAM':
      return {
        badge: '待组队',
        statusTone: 'neutral',
        headline: '先完成项目组队',
        detail: '路演需要挂到项目上，才能被老师看见并生成 AI 评分。组好队之后，你的第一场练习就会出现在这里。',
        primary: { label: '去项目团队', to: '/project-team' },
        secondary: { label: '了解训练计划', to: '/training/plan' }
      }
    case 'LIVE':
      return {
        badge: '进行中',
        statusTone: 'live',
        headline: title || '路演进行中',
        detail: [startLabel && `开始于 ${startLabel}`].filter(Boolean).join(' · ') || '队伍正在房间里，现在加入还来得及。',
        primary: { label: '进入房间', to: meetingId ? `/meeting/${meetingId}` : '/online-meeting' },
        secondary: { label: '会议列表', to: '/online-meeting' }
      }
    case 'HAS_SCORE': {
      const issue = firstImprovement.value || '根据评分反馈改一处再练'
      return {
        badge: '待复练',
        statusTone: 'warn',
        headline: `本轮只改一个问题：${issue}`,
        detail: '专项复练完成后，再录制一轮完整路演。小步改进，比一次做完更有效。',
        primary: { label: '再练一场', to: '/online-meeting' },
        secondary: { label: '查看报告', to: scorePath.value }
      }
    }
    case 'RECORDED_NO_SCORE':
      return {
        badge: '待评分',
        statusTone: 'warn',
        headline: title || '最近一场还在等待评分',
        detail: [startLabel, durationLabel].filter(Boolean).join(' · ') || '可先回看录像，评分生成后会同步到这里。',
        primary: {
          label: '查看回放',
          to: meetingId ? `/meeting-history/${meetingId}` : '/my-recordings'
        },
        secondary: { label: '再练一场', to: '/online-meeting' }
      }
    case 'NEVER_PRACTICED':
    default:
      return {
        badge: '待开练',
        statusTone: 'todo',
        headline: '还没有正式路演记录',
        detail: '第一次完整讲一遍项目就很了不起。结束后可生成 AI 评分，帮你看清下一步。',
        primary: { label: '开始第一场路演', to: '/online-meeting' },
        secondary: hasCamp.value
          ? { label: '先看训练计划', to: '/training/plan' }
          : { label: '去项目团队', to: '/project-team' }
      }
  }
})

function parseLocalDate(value) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

function formatScoreShort(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return '—'
  return Number.isInteger(num) ? String(num) : num.toFixed(1)
}

function formatMinutesValue(seconds) {
  return String(Math.max(0, Math.round(Number(seconds || 0) / 60)))
}

function formatLearningDuration(value) {
  const totalMinutes = Math.max(0, Math.round(Number(value || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (!hours) return `${minutes} 分`
  if (!minutes) return `${hours} 小时`
  return `${hours} 小时 ${minutes} 分`
}

/** 近一周起点：含今天共 7 天（today-6） */
function startOfRollingWeek(today) {
  if (!today) return null
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 6)
}

function buildWeeklyChartPoints(weekly, scaleMinutes) {
  const scale = Math.max(30, Number(scaleMinutes || 30))
  const serverDate = String(weekly?.serverDate || '').slice(0, 10)
  const today = parseLocalDate(serverDate) || new Date()
  const weekStart = parseLocalDate(weekly?.weekStart) || startOfRollingWeek(today)
  if (!weekStart) return []

  const dailyMap = new Map(
    (weekly?.daily || []).map(item => [String(item.date || '').slice(0, 10), item])
  )

  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + index)
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    const seconds = Math.max(0, Number(dailyMap.get(key)?.durationSeconds || 0))
    const minutes = seconds / 60
    const isFuture = key > serverDate
    const isToday = key === serverDate
    return {
      dateKey: key,
      weekday: isToday
        ? '今天'
        : new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(date).replace('周', ''),
      dateLabel: `${date.getMonth() + 1}/${date.getDate()}`,
      barRatio: isFuture ? 0 : Math.min(1, minutes / scale),
      isToday,
      isFuture,
      valueLabel: isFuture ? '未到' : formatLearningDuration(seconds),
      accessibleLabel: `${date.getMonth() + 1}月${date.getDate()}日${isFuture ? '未到' : `学习${formatLearningDuration(seconds)}`}`
    }
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchStudentHome()
  } catch (loadError) {
    error.value = loadError?.message || '请检查网络连接后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKeydown)
  scrubHomeTransitionResidue()
})

onActivated(() => {
  scrubHomeTransitionResidue()
  nextTick(scrubHomeTransitionResidue)
  // 再次进入：轻量触发图表 resize，避免缓存尺寸错误造成一帧闪动
  if (hasActivatedOnce) {
    window.dispatchEvent(new Event('resize'))
  }
  hasActivatedOnce = true
})

onDeactivated(() => {
  // 离开前把缓存实例恢复为「可见」状态，避免下次 activate 仍是 opacity:0
  scrubHomeTransitionResidue()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
/*
 * 首页布局：
 * - 整页不滚动；左右栏固定高度，内容局部滚
 * - 开小启：严格 50/50 文档流分栏（非悬浮遮罩）
 * - 左栏 min-width:0 + 卡 overflow，图表不得横向溢出被裁
 * - 左栏禁止再套大白壳
 */
.home-workspace {
  --home-ai-radius: 20px;
  --home-card-radius: 16px;
  --home-chip-radius: 12px;
  --home-panel-gap: 16px;
  --home-ease: cubic-bezier(0.22, 1, 0.36, 1);
  --home-duration: 0.42s;

  display: grid;
  grid-template-columns: minmax(0, 1fr) 0px;
  grid-template-rows: minmax(0, 1fr);
  gap: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  align-items: stretch;
  overflow: hidden;
  box-sizing: border-box;
  /* 路由 keep-alive：根节点必须始终可见，禁止继承 leave opacity */
  opacity: 1;
  transform: none;
  transition:
    grid-template-columns var(--home-duration) var(--home-ease),
    gap var(--home-duration) var(--home-ease);
  /* 仅在开合小启时需要；常驻 will-change 会增加合成层开销导致切换卡顿 */
}
/* 各占一半：禁止再把小启压成窄助手条 */
.home-workspace.is-ai-open {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--home-panel-gap);
  will-change: grid-template-columns;
}

/* 左栏：固定高度 + 局部滚动；预留滚动条槽，避免挡字 */
.home-workspace__main {
  min-width: 0;
  max-width: 100%;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  /* 经典做法：给滚动条留稳定槽位，内容不钻到条下面 */
  scrollbar-gutter: stable;
  padding-right: 4px;
}

/* 右栏：文档流分栏，与左栏同高同权 */
.home-workspace__ai {
  min-width: 0;
  max-width: 100%;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--home-ai-radius);
  box-shadow: none;
  position: relative;
  z-index: 1;
  transition:
    opacity 0.28s var(--home-ease),
    border-color 0.24s var(--home-ease),
    background-color 0.24s var(--home-ease);
  will-change: opacity;
  contain: layout paint;
}
.home-workspace.is-ai-open .home-workspace__ai {
  opacity: 1;
  pointer-events: auto;
  /* 与 /assistant 同级白舞台，不再套「卡片阴影」显得像低配弹层 */
  background: #ffffff;
  border-color: rgba(15, 23, 42, 0.06);
  box-shadow: none;
}

/* 无圆框：独立吉祥物 + 脚下投影（对齐 ai-mascot 悬浮球） */
.home-xiaoqi-fab {
  position: fixed;
  right: 20px;
  bottom: 16px;
  z-index: 40;
  width: 88px;
  height: 88px;
  border: 0;
  border-radius: 0;
  padding: 0;
  background: transparent;
  box-shadow: none;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition:
    transform 0.22s var(--home-ease),
    opacity 0.22s var(--home-ease);
}
.home-xiaoqi-fab:hover {
  transform: scale(1.06);
  box-shadow: none;
}
.home-xiaoqi-fab:focus-visible {
  outline: 3px solid #ffad66;
  outline-offset: 4px;
  border-radius: 16px;
}
.home-xiaoqi-fab :deep(.xiaoqi-mark) {
  transform: none;
}
.home-xiaoqi-fab :deep(.xiaoqi-mark__img) {
  object-position: center bottom;
  filter: drop-shadow(0 8px 10px rgba(100, 55, 10, 0.2));
}
.home-workspace.is-ai-open .home-xiaoqi-fab {
  opacity: 0;
  pointer-events: none;
  transform: scale(0.88);
  transition-delay: 0s;
}
.home-workspace:not(.is-ai-open) .home-xiaoqi-fab {
  transition-delay: 0.08s;
}

/* 模块流：宽度锁在左栏内；右侧留白避开滚动条 */
.home-dash {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 1120px;
  min-width: 0;
  margin: 0 auto;
  padding: 0 10px 24px 2px;
  color: var(--ds-ink, #0a0a0a);
  font-family: var(--ds-font-sans);
  box-sizing: border-box;
}
.home-workspace.is-ai-open .home-dash {
  max-width: none;
  width: 100%;
  padding: 0 10px 20px 2px;
}

.home-dash__card {
  background: var(--ds-surface, #fff);
  border: 1px solid var(--ds-card-border, #e4e4e7);
  border-radius: var(--home-card-radius);
  box-shadow: var(--ds-card-shadow);
}

.home-dash__skeleton,
.home-dash__error {
  padding: 28px 24px;
}

.home-dash__empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  max-width: 42ch;
}

.home-dash__empty-icon {
  width: 28px;
  height: 28px;
  color: var(--ds-orange-500, #e84a1c);
}

.home-dash__empty h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.home-dash__empty p {
  margin: 0;
  color: var(--ds-muted, #71717a);
  font-size: 13px;
  line-height: 1.6;
}

/* ——— 状态栏：轻量问候区，不做第三张主卡 ——— */
.home-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 4px 4px 2px;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.home-status__identity {
  min-width: 0;
  flex: 1;
}

.home-status__eyebrow {
  margin: 0 0 6px;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.home-status h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--ds-ink, #0a0a0a);
}

.home-status__sub {
  margin: 8px 0 0;
  color: var(--ds-muted, #71717a);
  font-size: 13px;
  line-height: 1.5;
  max-width: 52ch;
}

.home-status__metrics {
  display: flex;
  align-items: center;
  gap: 28px;
  flex: 0 0 auto;
}

.home-status__countdown {
  text-align: right;
  min-width: 96px;
}

.home-status__countdown > span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-status__countdown strong {
  display: block;
  margin-top: 2px;
  color: var(--ds-ink, #0a0a0a);
  font-family: var(--ds-font-num, inherit);
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1.05;
}

.home-status__countdown strong small {
  margin-left: 2px;
  font-size: 13px;
  font-weight: 700;
}

.home-status__countdown strong.is-empty {
  color: var(--ds-faint, #8b8b93);
}

.home-status__countdown strong.is-soft {
  font-size: 20px;
  letter-spacing: -0.02em;
  font-weight: 700;
}

.home-status__countdown p {
  margin: 4px 0 0;
  color: var(--ds-faint, #8b8b93);
  font-size: 11px;
  font-weight: 600;
}

.home-status__progress {
  width: 168px;
}

.home-status__progress-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.home-status__progress-head span {
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-status__progress-head em {
  color: var(--ds-ink-2, #3f3f46);
  font-style: normal;
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.home-status__track {
  height: 8px;
  border-radius: 999px;
  background: #ececef;
  overflow: hidden;
}

.home-status__track > i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff9a62, #e84a1c);
  box-shadow: 0 1px 4px rgba(232, 74, 28, 0.18);
  transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

/* ——— 今日任务 · 主卡 ———
 * 左文案 / 右行动：顶对齐 + 列间距均匀，不挤、不上下乱飞
 */
.home-primary {
  margin: 0;
  padding: 0;
  position: relative;
  overflow: hidden;
  min-width: 0;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
  border-radius: 18px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background:
    radial-gradient(110% 90% at 8% -10%, rgba(255, 146, 96, 0.08), transparent 52%),
    #ffffff;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.95) inset,
    0 2px 4px rgba(15, 23, 42, 0.03),
    0 10px 28px rgba(15, 23, 42, 0.045);
}

.home-primary__core {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(168px, 200px);
  gap: 20px 28px;
  align-items: start;
  padding: 24px 24px 20px;
  box-sizing: border-box;
}

.home-primary__main,
.home-primary__rail {
  position: relative;
  z-index: 1;
  min-width: 0;
}

.home-primary__main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 0;
}

.home-primary__list {
  border-top: 1px solid rgba(15, 23, 42, 0.05);
  padding: 12px 24px 16px;
  background: rgba(250, 250, 250, 0.72);
}
.home-primary__list-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.home-primary__list-head span {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ds-faint, #8b8b93);
}
.home-primary__list-head em {
  font-style: normal;
  font-size: 11px;
  font-weight: 600;
  color: var(--ds-faint, #8b8b93);
}
.home-primary__plan {
  list-style: none;
  margin: 0;
  padding: 0;
}
.home-primary__plan li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
}
.home-primary__plan li:last-child { border-bottom: 0; }
.home-primary__mark {
  height: 20px;
  margin-top: 1px;
  padding: 0 7px;
  border-radius: 6px;
  font-size: 10.5px;
  font-weight: 700;
  line-height: 20px;
  color: var(--ds-orange-700, #c43a12);
  background: rgba(232, 74, 28, 0.08);
  white-space: nowrap;
}
.home-primary__mark.is-opt {
  color: var(--ds-faint, #8b8b93);
  background: rgba(15, 23, 42, 0.04);
}
.home-primary__plan-body {
  min-width: 0;
  display: grid;
  gap: 3px;
}
.home-primary__plan-title {
  min-width: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--ds-ink-2, #3f3f46);
  text-decoration: none;
  line-height: 1.4;
}
.home-primary__plan li.is-main .home-primary__plan-title {
  color: var(--ds-ink, #0a0a0a);
  font-weight: 700;
}
a.home-primary__plan-title:hover {
  color: var(--ds-orange-700, #c43a12);
}
.home-primary__plan-detail {
  margin: 0;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
}
.home-primary__plan em {
  font-style: normal;
  font-size: 11px;
  color: var(--ds-faint, #8b8b93);
  white-space: nowrap;
  margin-top: 2px;
}

.home-primary__chip {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(15, 23, 42, 0.06);
  color: var(--ds-ink-2, #3f3f46);
  font-size: 11px;
  font-weight: 600;
}

.home-primary__main--empty {
  justify-content: flex-start;
  min-height: 0;
}

.home-primary__kicker {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.home-primary__badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ds-orange-700, #c43a12);
  font-size: 12.5px;
  font-weight: 750;
  letter-spacing: 0.01em;
}

.home-primary__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ds-orange-500, #e84a1c);
  box-shadow: 0 0 0 4px rgba(232, 74, 28, 0.12);
  flex: none;
}

.home-primary__ai {
  font-size: 10.5px;
  font-weight: 750;
  color: var(--ds-orange-700, #c43a12);
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(232, 74, 28, 0.16);
  border-radius: 999px;
  padding: 3px 9px;
  line-height: 1.2;
}

.home-primary__title {
  margin: 0;
  max-width: 22em;
  font-size: 22px;
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.28;
  color: var(--ds-ink, #0a0a0a);
}

.home-primary__summary {
  margin: 0;
  color: var(--ds-ink-2, #3f3f46);
  font-size: 13.5px;
  line-height: 1.6;
  max-width: 48ch;
}

/* 本轮重点：轻内嵌，不抢标题 */
.home-primary__focus {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 18px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: 12px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset;
}

.home-primary__focus-main {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 12px;
  min-width: 0;
}

.home-primary__focus-label {
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.home-primary__focus-title {
  min-width: 0;
  color: var(--ds-ink, #0a0a0a);
  font-size: 13.5px;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.35;
}

.home-primary__focus-state {
  flex: none;
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
  border-radius: 999px;
  padding: 4px 10px;
  line-height: 1.2;
}

.home-primary__focus-state[data-state='todo'] {
  color: var(--ds-orange-700, #c43a12);
  background: rgba(232, 74, 28, 0.08);
  border: 1px solid transparent;
}

.home-primary__focus-state[data-state='done'] {
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid transparent;
}

.home-primary__focus-state[data-state='idle'] {
  color: var(--ds-muted, #71717a);
  background: #ffffff;
  border: 1px solid #e4e4e7;
}

.home-primary__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 2px 0 0;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  line-height: 1.4;
}

.home-primary__meta-sep {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #d4d4d8;
  flex: none;
}

/* 右侧行动区：与左侧顶对齐，间距均匀，不拉满整卡高度 */
.home-primary__rail {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  align-self: start;
  gap: 16px;
  width: 100%;
  padding: 2px 0 0;
  background: transparent;
  box-shadow: none;
}

.home-primary__est {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0;
}

.home-primary__est span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.01em;
}

.home-primary__est strong {
  display: block;
  margin: 0;
  color: var(--ds-orange-700, #c43a12);
  font-family: var(--ds-font-num, inherit);
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1.05;
}

.home-primary__est strong small {
  margin-left: 3px;
  color: var(--ds-orange-700, #c43a12);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
  opacity: 0.85;
}

.home-primary__cta {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.home-primary__cta :deep(.interactive-hover-button) {
  width: 100%;
}

.home-primary__cta :deep(.interactive-hover-button--primary) {
  min-height: 40px;
  height: 40px;
  font-size: 13.5px;
  box-shadow: 0 8px 18px rgba(196, 58, 18, 0.16);
}

.home-primary__cta :deep(.interactive-hover-button--secondary) {
  min-height: 40px;
  height: 40px;
  background: #fff;
  border-color: #e4e4e7;
}

/* ——— 双卡：近一周训练 + AI 能力诊断（平级次卡，直接坐画布） ——— */
.home-secondary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
  margin-top: 0;
  min-width: 0;
  max-width: 100%;
  width: 100%;
}

/* 开栏 50% 宽：双卡纵向，避免横向挤爆；主任务仍文左/行动右 */
.home-workspace.is-ai-open .home-secondary {
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
}
.home-workspace.is-ai-open .home-primary__core {
  grid-template-columns: minmax(0, 1fr) minmax(140px, 168px);
  gap: 16px 20px;
  padding: 20px 18px 16px;
  align-items: start;
}
.home-workspace.is-ai-open .home-primary__main {
  padding: 0;
  min-width: 0;
  gap: 10px;
}
.home-workspace.is-ai-open .home-primary__rail {
  padding: 0;
  min-width: 0;
  gap: 12px;
}
.home-workspace.is-ai-open .home-primary__title {
  font-size: 20px;
}
.home-workspace.is-ai-open .home-primary__cta :deep(.interactive-hover-button) {
  width: 100%;
  min-width: 0;
}
.home-workspace.is-ai-open .home-card {
  min-height: 0;
  min-width: 0;
  max-width: 100%;
  padding: 14px 14px 12px;
  overflow: hidden;
}
.home-workspace.is-ai-open .home-card__chart {
  min-height: 140px;
  min-width: 0;
  width: 100%;
  overflow: hidden;
}
.home-workspace.is-ai-open .home-card__chart :deep(.weekly-learning-chart) {
  min-height: 140px;
  width: 100% !important;
  max-width: 100%;
}
.home-workspace.is-ai-open .home-score {
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  min-width: 0;
}
.home-workspace.is-ai-open .home-score__radar {
  min-width: 0;
  overflow: hidden;
}
.home-workspace.is-ai-open .home-score__radar :deep(.home-score-radar) {
  min-height: 160px;
  width: 100% !important;
  max-width: 100%;
}
.home-workspace.is-ai-open .home-card__actions {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  min-width: 0;
  width: 100%;
}
.home-workspace.is-ai-open .home-card__actions :deep(.interactive-hover-button) {
  min-width: 0;
  width: 100%;
  max-width: 100%;
}
.home-workspace.is-ai-open .home-status {
  padding: 0 2px;
  gap: 12px;
  min-width: 0;
}
.home-workspace.is-ai-open .home-status h1 {
  font-size: 20px;
}
.home-workspace.is-ai-open .home-status__sub {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.home-workspace.is-ai-open .home-status__metrics {
  min-width: 0;
  flex-shrink: 1;
}
.home-workspace.is-ai-open .home-status__progress {
  width: min(140px, 28vw);
}

.home-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 260px;
  min-width: 0;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
  padding: 16px 16px 14px;
  overflow: hidden;
  background: var(--ds-surface, #fff);
  border: 1px solid var(--ds-card-border, #e4e4e7);
  border-radius: var(--home-card-radius, 16px);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03), 0 4px 14px rgba(15, 23, 42, 0.03);
}

.home-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.home-card__title {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.home-card__icon {
  flex: none;
  width: 28px;
  height: 28px;
  margin-top: 1px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--ds-ink-2, #3f3f46);
  background: #f4f4f5;
}

.home-card__icon :deep(.workspace-module-icon) {
  width: 16px;
  height: 16px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.home-card__title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 750;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.home-card__title p {
  margin: 3px 0 0;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  line-height: 1.4;
}

.home-card__chip {
  flex: none;
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 4px 9px;
  white-space: nowrap;
}

.home-card__chip[data-tone='todo'],
.home-card__chip[data-tone='warn'] {
  color: #b45309;
  background: #fff7ed;
}

.home-card__chip[data-tone='live'] {
  color: #c43a12;
  background: #fff1eb;
}

.home-card__chip[data-tone='done'] {
  color: #0f766e;
  background: #ecfdf5;
}

.home-card__chip[data-tone='neutral'] {
  color: var(--ds-muted, #71717a);
  background: #f4f4f5;
}

.home-card__stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.home-card__stats > div {
  min-width: 0;
}

.home-card__stats span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-card__stats strong {
  display: block;
  margin-top: 4px;
  color: var(--ds-ink, #0a0a0a);
  font-family: var(--ds-font-num, inherit);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.home-card__stats strong small {
  margin-left: 2px;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-card__chart {
  flex: 1;
  min-height: 148px;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}

.home-card__chart :deep(.weekly-learning-chart) {
  min-height: 148px;
  width: 100%;
  max-width: 100%;
  height: 100%;
}

.home-card__empty-note,
.home-card__foot {
  margin: 0;
  color: var(--ds-faint, #8b8b93);
  font-size: 11px;
  line-height: 1.45;
}

.home-card__foot {
  margin-top: auto;
}

/* 路演卡 */
.home-roadshow {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.home-roadshow__score > span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-roadshow__score > strong {
  display: block;
  margin-top: 4px;
  color: var(--ds-ink, #0a0a0a);
  font-family: var(--ds-font-num, inherit);
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1;
}

.home-roadshow__score > strong small {
  margin-left: 2px;
  color: var(--ds-muted, #71717a);
  font-size: 13px;
  font-weight: 650;
}

.home-roadshow__score > strong.is-empty {
  color: var(--ds-faint, #8b8b93);
}

.home-roadshow__duration {
  margin-top: 14px;
}

.home-roadshow__duration span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-roadshow__duration em {
  display: block;
  margin-top: 3px;
  font-style: normal;
  color: var(--ds-ink-2, #3f3f46);
  font-size: 13px;
  font-weight: 700;
}

.home-roadshow__tip {
  padding: 12px;
  background: #f7f7f8;
  border: 1px solid #ececef;
  border-radius: 12px;
  min-width: 0;
}

.home-roadshow__tip strong {
  display: block;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.4;
  color: var(--ds-ink, #0a0a0a);
}

.home-roadshow__tip p {
  margin: 6px 0 0;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-card__actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  margin-top: auto;
  min-width: 0;
}

.home-card__actions :deep(.interactive-hover-button) {
  width: 100%;
  min-width: 0;
}

/* AI 诊断卡 */
.home-score {
  display: grid;
  grid-template-columns: minmax(0, 0.72fr) minmax(0, 1.28fr);
  gap: 10px;
  flex: 1;
  min-height: 0;
  min-width: 0;
  max-width: 100%;
  width: 100%;
}
.home-score--row {
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  align-items: center;
}
.home-score__priority,
.home-score__radar {
  min-width: 0;
  max-width: 100%;
}
.home-score__radar {
  overflow: hidden;
}
.home-score__priority strong small {
  margin-left: 2px;
  font-size: 13px;
  font-weight: 650;
  color: var(--ds-muted, #71717a);
}

.home-score__priority span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}

.home-score__priority strong {
  display: block;
  margin-top: 4px;
  color: var(--ds-ink, #0a0a0a);
  font-family: var(--ds-font-num, inherit);
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1;
}

.home-score__priority em {
  display: block;
  margin-top: 4px;
  font-style: normal;
  color: var(--ds-ink-2, #3f3f46);
  font-size: 12px;
  font-weight: 700;
}

.home-score__radar {
  min-height: 160px;
}

.home-score__radar :deep(.home-score-radar) {
  min-height: 160px;
}

.home-score__radar-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 140px;
  color: var(--ds-muted, #71717a);
  background: #fafafa;
  border: 1px dashed var(--ds-line, #e4e4e7);
  border-radius: 12px;
  font-size: 12px;
  text-align: center;
  padding: 14px;
  line-height: 1.5;
}

.home-score__radar-empty p {
  margin: 0;
  max-width: 22ch;
}

.home-score__next {
  margin-top: auto;
  padding-top: 4px;
}

.home-score__next > span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 700;
}

.home-score__next p {
  margin: 4px 0 8px;
  color: var(--ds-ink-2, #3f3f46);
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.home-score__link {
  color: var(--ds-ink-2, #3f3f46);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.home-score__link:hover {
  color: var(--ds-orange-700, #c43a12);
  text-decoration: underline;
}

.home-card__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 0 4px;
  min-height: 160px;
}

.home-card__empty-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: var(--ds-ink-2, #3f3f46);
  background: #f4f4f5;
  margin-bottom: 2px;
}

.home-card__empty-icon.is-inline {
  width: 28px;
  height: 28px;
  margin-bottom: 0;
}

.home-card__empty-icon :deep(.workspace-module-icon) {
  width: 18px;
  height: 18px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.home-card__empty-icon.is-inline :deep(.workspace-module-icon) {
  width: 14px;
  height: 14px;
}

.home-card__empty strong {
  color: var(--ds-ink, #0a0a0a);
  font-size: 14px;
  font-weight: 750;
  line-height: 1.35;
}

.home-card__empty p {
  margin: 0;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  line-height: 1.55;
  max-width: 36ch;
}

.home-card__empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.home-roadshow__score > strong.is-soft {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ds-muted, #71717a);
}

@media (prefers-reduced-motion: reduce) {
  .home-status__track > i,
  .home-workspace,
  .home-workspace__ai,
  .home-xiaoqi-fab {
    transition: none !important;
  }
}

/* 左栏滚动条：占独立槽位，不压在文字上 */
.home-workspace__main {
  scrollbar-width: thin;
  scrollbar-color: rgba(15, 23, 42, 0.22) transparent;
}
.home-workspace__main::-webkit-scrollbar {
  width: 10px;
}
.home-workspace__main::-webkit-scrollbar-thumb {
  background: rgba(15, 23, 42, 0.18);
  border-radius: 999px;
  border: 2px solid transparent;
  background-clip: content-box;
}
.home-workspace__main::-webkit-scrollbar-track {
  background: transparent;
  margin: 4px 0;
}

@media (max-width: 1100px) {
  .home-secondary {
    grid-template-columns: 1fr;
  }

  .home-card {
    min-height: 240px;
  }

  .home-score {
    grid-template-columns: minmax(120px, 0.7fr) minmax(0, 1.3fr);
  }
}

@media (max-width: 860px) {
  .home-workspace {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr);
    min-height: 0;
    height: 100%;
    gap: 0;
  }
  .home-workspace.is-ai-open {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) minmax(38vh, 44vh);
    gap: var(--home-panel-gap);
  }
  .home-workspace__main {
    min-height: 0;
  }
  .home-workspace__ai {
    min-height: 0;
    height: auto;
  }
  .home-dash {
    padding: 0 0 20px;
  }
  .home-xiaoqi-fab {
    right: 16px;
    bottom: 16px;
  }

  .home-status {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }

  .home-status__metrics {
    justify-content: space-between;
  }

  .home-status__countdown {
    text-align: left;
  }

  .home-primary__core,
  .home-workspace.is-ai-open .home-primary__core {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 20px 18px 16px;
  }

  .home-primary__rail,
  .home-workspace.is-ai-open .home-primary__rail {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px 16px;
    padding: 0;
    width: 100%;
    border-top: 1px solid rgba(15, 23, 42, 0.05);
    padding-top: 14px;
  }

  .home-primary__cta {
    flex: 1 1 180px;
    max-width: 240px;
  }

  .home-dash {
    padding: 0 8px 20px 0;
  }

  .home-primary__focus {
    align-items: flex-start;
  }

  .home-roadshow {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .home-status__metrics {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }

  .home-status__progress {
    width: 100%;
  }

  .home-primary__rail {
    flex-direction: column;
    align-items: stretch;
  }

  .home-primary__cta {
    flex: none;
    width: 100%;
  }

  .home-primary__title {
    font-size: 18px;
  }

  .home-card__stats {
    grid-template-columns: 1fr 1fr 1fr;
  }

  .home-score {
    grid-template-columns: 1fr;
  }

  .home-score__radar :deep(.home-score-radar) {
    min-height: 200px;
  }

  .home-card__actions {
    grid-template-columns: 1fr;
  }
}
</style>
