<template>
  <div class="student-page training-tasks-page">
    <section v-if="loading" class="student-card student-skeleton">
      <el-skeleton :rows="12" animated />
    </section>

    <section v-else-if="error || !data.hasCamp" class="student-card student-empty">
      <div class="student-empty__content">
        <div class="student-empty__icon"><Calendar /></div>
        <h2>{{ error ? '训练任务暂时没有加载出来' : '当前没有训练任务' }}</h2>
        <p>{{ error || formatTrainingCopy(data.message) }}</p>
        <BaseButton v-if="error" @click="load">重新加载</BaseButton>
      </div>
    </section>

    <template v-else>
      <!-- 紧凑指挥条：标题 + 营信息 + 关键指标，去掉重复说明 -->
      <header class="tasks-command" aria-label="训练任务总览">
        <div class="tasks-command__identity">
          <h1>训练任务</h1>
          <p>
            <span class="tasks-command__camp">{{ formatTrainingCopy(data.camp?.campName) }}</span>
            <span class="tasks-command__sep" aria-hidden="true">·</span>
            <span>{{ campDayProgressLabel }}</span>
            <span class="tasks-command__sep" aria-hidden="true">·</span>
            <span>{{ formatDate(data.camp?.startDate) }}—{{ formatDate(data.camp?.endDate) }}</span>
          </p>
        </div>
        <div class="tasks-command__stats">
          <div class="tasks-command__progress" aria-label="整体进度">
            <div class="tasks-command__progress-copy">
              <strong>{{ completionRate }}%</strong>
              <span>已提交 {{ submittedTaskCount }} 项 · 共 {{ totalTaskCount }} 项</span>
            </div>
            <div class="tasks-progress-track" aria-hidden="true">
              <i :style="{ width: `${completionRate}%` }"></i>
            </div>
          </div>
          <div class="tasks-command__metric">
            <strong>{{ activeTaskCount }}</strong>
            <span>待完成</span>
          </div>
          <div class="tasks-command__metric">
            <strong>{{ data.camp?.remainingDays ?? '—' }}</strong>
            <span>剩余天</span>
          </div>
        </div>
      </header>

      <!-- 筛选条：只保留操作，不再占一层大标题 -->
      <section class="tasks-toolbar tasks-toolbar--compact" aria-label="筛选训练任务">
        <div class="tasks-toolbar__controls">
          <div class="tasks-filter" role="group" aria-label="按状态筛选训练任务">
            <button
              v-for="item in filters"
              :key="item.key"
              type="button"
              :aria-label="`${item.label}，${item.count} 项`"
              :aria-pressed="activeFilter === item.key"
              :class="{ 'is-active': activeFilter === item.key }"
              @click="activeFilter = item.key"
            >
              <span class="tasks-filter__label">{{ item.label }}</span>
              <span
                class="tasks-filter__count"
                :class="{ 'is-zero': item.count === 0 }"
                aria-hidden="true"
              >{{ item.count }}</span>
            </button>
          </div>
          <span class="tasks-toolbar__divider" aria-hidden="true"></span>
          <form class="tasks-search" role="search" @submit.prevent>
            <Search aria-hidden="true" />
            <input
              v-model="taskSearch"
              type="search"
              autocomplete="off"
              aria-label="搜索训练任务"
              placeholder="搜索任务"
            />
            <button
              v-if="normalizedTaskSearch"
              type="button"
              aria-label="清除任务搜索"
              @click="taskSearch = ''"
            >
              <Close />
            </button>
          </form>
          <span class="tasks-toolbar__result" aria-live="polite">
            显示 <strong>{{ visibleTaskCount }}</strong> 项
          </span>
        </div>
      </section>

      <TrainingTracingBeam v-if="timelineWeeks.length">
        <div class="tasks-timeline">
          <!-- 整段「今天之前」默认折叠：首屏只见今天与后续 -->
          <button
            v-if="pastHistoryMeta.dayCount > 0"
            type="button"
            class="tasks-history-bar"
            :class="{ 'is-remind': pastHistoryMeta.openCount > 0, 'is-open': pastHistoryOpen }"
            :aria-expanded="pastHistoryOpen"
            @click="pastHistoryOpen = !pastHistoryOpen"
          >
            <span class="tasks-history-bar__main">
              <span
                class="tasks-history-bar__icon"
                :class="pastHistoryMeta.openCount > 0 ? 'is-remind' : 'is-ok'"
                aria-hidden="true"
              >
                <WarningFilled v-if="pastHistoryMeta.openCount > 0" />
                <CircleCheck v-else />
              </span>
              <span class="tasks-history-bar__copy">
                <strong>{{ pastHistoryOpen ? '收起更早的训练' : '更早的训练' }}</strong>
                <small>{{ pastHistorySummary }}</small>
              </span>
            </span>
            <span class="tasks-history-bar__action">
              {{ pastHistoryOpen ? '收起' : (pastHistoryMeta.openCount > 0 ? '展开处理' : '展开回顾') }}
              <ArrowUp v-if="pastHistoryOpen" />
              <ArrowDown v-else />
            </span>
          </button>

          <section
            v-for="week in timelineWeeks"
            :key="`${week._segment}-${week.weekId || week.weekNo}`"
            class="tasks-week"
            :class="{ 'is-history': week._segment === 'past' }"
          >
          <header class="tasks-week__head">
            <i
              class="tasks-week__anchor"
              data-training-beam-track="week"
              aria-hidden="true"
            ></i>
            <div class="tasks-week__identity">
              <span class="tasks-week__number">第 {{ week.weekNo || 1 }} 周</span>
              <div class="tasks-week__title">
                <h2>{{ weekTitle(week) }}</h2>
                <p>{{ formatDate(week.startDate) }}—{{ formatDate(week.endDate) }}</p>
              </div>
            </div>
            <div class="tasks-week__status">
              <span class="tasks-week__summary">{{ weekTaskSummary(week) }}</span>
              <div
                v-if="weekStats(week).total > 0"
                class="tasks-week__progress"
                role="progressbar"
                aria-label="本周任务完成进度"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="weekStats(week).rate"
              >
                <i :style="{ width: `${weekStats(week).rate}%` }"></i>
              </div>
            </div>
          </header>

          <div
            class="tasks-week__days"
            :style="{ '--week-progress': `${weekStats(week).rate}%` }"
          >
            <article
              v-for="day in week.days"
              :key="day.dayId"
              class="tasks-day"
              :class="[
                `is-${dayTone(day)}`,
                {
                  'is-locked-day': isDayLocked(day),
                  'is-future-dim': isFutureTimelineDay(day) && !isDayLocked(day),
                }
              ]"
            >
              <div class="tasks-day__date">
                <span>第 {{ day.dayNo || 0 }} 天</span>
                <strong>{{ monthDay(day.trainingDate) }}</strong>
                <small>{{ weekday(day.trainingDate) }}</small>
                <i data-training-beam-track="day" aria-hidden="true"></i>
              </div>

              <div class="tasks-day__body">
                <div
                  class="task-items"
                  :class="{ 'has-learning': hasLearning(day) }"
                >
                  <!-- 锁定日：单行状态条，避免「日期 + 标题 + 说明」三重重复 -->
                  <div
                    v-if="isDayLocked(day)"
                    class="task-item is-locked task-item--locked-compact"
                    aria-disabled="true"
                    role="status"
                    :aria-label="`第 ${day.dayNo} 天，${monthDay(day.trainingDate)} ${weekday(day.trainingDate)}，${lockedDayLabel(day)}`"
                  >
                    <span class="task-item__signal is-locked" aria-hidden="true">
                      <Clock />
                    </span>
                    <div class="task-item__content">
                      <div class="task-item__title-row">
                        <h4>{{ lockedDayTitle(day) }}</h4>
                      </div>
                      <p class="task-item__locked-hint">{{ lockedDayMessage(day) }}</p>
                    </div>
                    <div class="task-item__action">
                      <span class="is-locked">{{ lockedDayLabel(day) }}</span>
                    </div>
                  </div>
                  <template v-else>
                    <RouterLink
                      v-if="hasLearning(day)"
                      :to="dayLearningRoute(day)"
                      class="task-learning-preview"
                      :aria-label="`${learningTypeLabel(day)}：${learningPreviewTitle(day)}，${learningStatusLabel(day)}`"
                    >
                      <span class="task-learning-preview__icon" aria-hidden="true">
                        <component :is="learningIcon(day)" />
                      </span>
                      <div class="task-learning-preview__content">
                        <div class="task-learning-preview__eyebrow">
                          <span>{{ learningTypeLabel(day) }}</span>
                        </div>
                        <h4>{{ learningPreviewTitle(day) }}</h4>
                        <p>
                          {{ learningResourceSummary(day) }}
                          <template v-if="learningRemaining(day) > 0"> · 完成后再开始任务</template>
                          <template v-else> · 已完成，可以开始任务</template>
                        </p>
                      </div>
                      <div class="task-learning-preview__progress">
                        <div
                          class="task-learning-preview__ring"
                          :class="{ 'is-complete': learningRate(day) >= 100 }"
                          :style="{ '--learning-progress': `${learningRate(day)}%` }"
                          role="progressbar"
                          :aria-label="`${learningStatusLabel(day)}，完成 ${learningRate(day)}%`"
                          aria-valuemin="0"
                          aria-valuemax="100"
                          :aria-valuenow="learningRate(day)"
                        >
                          <strong>
                            <CircleCheck v-if="learningRate(day) >= 100" />
                            <template v-else>{{ learningRate(day) }}%</template>
                          </strong>
                        </div>
                        <span :class="{ 'is-complete': learningRate(day) >= 100 }">{{ learningStatusLabel(day) }}</span>
                      </div>
                      <span class="task-learning-preview__action">
                        {{ learningHasProgress(day) ? '继续学习' : '开始学习' }}
                        <ArrowRight />
                      </span>
                    </RouterLink>
                    <RouterLink
                      v-for="task in day.tasks"
                      :key="task.taskId"
                      :to="`/training/tasks/${task.taskId}?dayId=${day.dayId}`"
                      class="task-item"
                      :class="`is-${taskState(task, day).tone}`"
                    >
                      <span class="task-item__signal" :class="`is-${taskState(task, day).tone}`" aria-hidden="true">
                        <CircleCheck v-if="taskState(task, day).tone === 'complete'" />
                        <Clock v-else />
                      </span>

                      <div class="task-item__content">
                        <div class="task-item__title-row">
                          <h4>{{ taskDisplayTitle(task, day) }}</h4>
                          <span v-if="Number(task.isPrimary) === 1" class="task-item__primary">核心任务</span>
                        </div>
                        <p>{{ task.description || '进入详情查看任务说明、交付要求与附件。' }}</p>
                        <div class="task-item__meta">
                          <span :class="{ 'is-high': String(task.priority || '').toUpperCase() === 'HIGH' }">
                            {{ priorityLabel(task.priority) }}
                          </span>
                          <span><b>{{ task.requirementCount || 0 }}</b> 项交付要求</span>
                          <span :class="{ 'is-urgent': ['revision', 'overdue'].includes(taskState(task, day).tone) }">
                            {{ dueLabel(task.dueAt) }}
                          </span>
                        </div>
                      </div>

                      <div class="task-item__action">
                        <span :class="`is-${taskState(task, day).tone}`">{{ taskState(task, day).label }}</span>
                        <strong>{{ taskActionLabel(task, day) }} <ArrowRight /></strong>
                      </div>
                    </RouterLink>
                  </template>
                </div>
              </div>
            </article>
          </div>
          </section>
        </div>
      </TrainingTracingBeam>

      <section v-else class="student-card tasks-filter-empty" aria-live="polite">
        <Flag />
        <h2>{{ emptyFilterCopy.title }}</h2>
        <p>{{ emptyFilterCopy.description }}</p>
        <button v-if="normalizedTaskSearch" type="button" @click="taskSearch = ''">清除搜索</button>
        <button v-else-if="activeFilter !== 'all'" type="button" @click="activeFilter = 'all'">查看全部任务</button>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Calendar,
  CircleCheck,
  Clock,
  Close,
  Document,
  Flag,
  Link as LinkIcon,
  Search,
  VideoPlay,
  WarningFilled,
} from '@element-plus/icons-vue'
import BaseButton from '../../components/base/BaseButton.vue'
import TrainingTracingBeam from './components/TrainingTracingBeam.vue'
import { fetchTrainingPlan } from './api'
import { formatDate, formatTrainingCopy } from './format'

const loading = ref(true)
const error = ref('')
const data = ref({})
/** 默认待完成（宣传/日常都优先看本周可做的） */
const activeFilter = ref('current')

/** 避免「17/21天」误读成分数 */
const campDayProgressLabel = computed(() => {
  const cur = Number(data.value.camp?.currentDay || 0)
  const total = Number(data.value.totalDays || data.value.camp?.totalDays || 0)
  if (total > 0 && cur > 0) return `第 ${cur} 天 · 共 ${total} 天`
  if (total > 0) return `全程共 ${total} 天`
  if (cur > 0) return `第 ${cur} 天`
  return '进度待开始'
})
const taskSearch = ref('')
/** 更早的整段时间线默认折叠，只露出今天与后续 */
const pastHistoryOpen = ref(false)

const allDays = computed(() => (data.value.weeks || []).flatMap(week => week.days || []))
const allTasks = computed(() => allDays.value.flatMap(day => (day.tasks || []).map(task => ({ task, day }))))
/** 未发布日不计入宣传面数量 */
const lockedDayCount = computed(() => allDays.value.filter((day) => isDayLocked(day) && !isUnpublishedDay(day)).length)
const totalTaskCount = computed(() => Number(data.value.totalTasks ?? allTasks.value.length) + lockedDayCount.value)
const submittedTaskCount = computed(() => Number(data.value.completedTasks ?? allTasks.value.filter(({ task, day }) => ['complete', 'review'].includes(taskState(task, day).tone)).length))
const completionRate = computed(() => totalTaskCount.value ? Math.round((submittedTaskCount.value / totalTaskCount.value) * 100) : 0)
/** 待完成计数：仅本周、今天及之后、非未发布、未完成 */
const activeTaskCount = computed(() => countByFilter('current'))

const filters = computed(() => [
  { key: 'current', label: '待完成', count: activeTaskCount.value },
  { key: 'completed', label: '已提交', count: countByFilter('completed') },
  { key: 'upcoming', label: '稍后开始', count: countByFilter('upcoming') + lockedDayCount.value },
  { key: 'all', label: '全部', count: allTasks.value.filter(({ day }) => !isUnpublishedDay(day)).length + lockedDayCount.value },
])

const normalizedTaskSearch = computed(() => taskSearch.value.trim().toLocaleLowerCase())

const emptyFilterCopy = computed(() => {
  if (normalizedTaskSearch.value) {
    return {
      title: `没有找到“${taskSearch.value.trim()}”`,
      description: '可以更换关键词，或清除搜索查看当前状态下的全部任务。'
    }
  }
  return {
    current: {
      title: '当前没有待完成任务',
      description: '很好，你暂时没有需要立即处理的训练任务。'
    },
    completed: {
      title: '还没有已提交任务',
      description: '完成任务并提交成果后，可以在这里集中查看。'
    },
    upcoming: {
      title: '暂时没有后续任务',
      description: '新的训练安排开放后，会显示在这里。'
    },
    all: {
      title: '当前没有训练任务',
      description: '训练安排发布后，会按周和训练日显示在这里。'
    }
  }[activeFilter.value] || {
    title: '该状态下暂无任务',
    description: '切换其他状态，查看完整训练安排。'
  }
})

const visibleWeeks = computed(() => (data.value.weeks || []).map(week => ({
  ...week,
  days: (week.days || []).map(day => {
    // 宣传向：未发布日整卡不展示（避免「待教师发布」占版）
    if (isUnpublishedDay(day)) return null

    // 待完成：只看本周，且不展示今天之前的天
    if (activeFilter.value === 'current') {
      if (!isInThisCalendarWeek(day)) return null
      if (isPastTimelineDay(day)) return null
    }

    if (isDayLocked(day)) {
      if (activeFilter.value === 'completed' || activeFilter.value === 'current') return null
      if (!matchesDaySearch(day)) return null
      return { ...day, tasks: [] }
    }
    const tasks = (day.tasks || []).filter(task =>
      matchesFilter(task, day, activeFilter.value) && matchesTaskSearch(task, day)
    )
    // 待完成里：未来日即使暂无 task 行也要占位灰度？（仅有任务时展示）
    if (!tasks.length) return null
    return { ...day, tasks }
  }).filter(Boolean)
})).filter(week => week.days.length))

const visibleTaskCount = computed(() => timelineWeeks.value.reduce((weekTotal, week) => (
  weekTotal + (week.days || []).reduce((dayTotal, day) => (
    dayTotal + (isDayLocked(day) ? 1 : (day.tasks || []).length)
  ), 0)
), 0))

/**
 * 将时间线拆成「更早」与「今天起」两段。
 * 默认只渲染今天起；更早整段收起，有未交时在条上提醒。
 */
const timelineSplit = computed(() => {
  const past = []
  const focus = []
  for (const week of visibleWeeks.value) {
    const pastDays = []
    const focusDays = []
    for (const day of week.days || []) {
      if (isPastTimelineDay(day)) pastDays.push(day)
      else focusDays.push(day)
    }
    if (pastDays.length) {
      past.push({
        ...week,
        days: pastDays,
        _segment: 'past',
      })
    }
    if (focusDays.length) {
      focus.push({
        ...week,
        days: focusDays,
        _segment: 'focus',
      })
    }
  }
  return { past, focus }
})

const pastHistoryMeta = computed(() => {
  let dayCount = 0
  let openCount = 0
  let taskCount = 0
  for (const week of timelineSplit.value.past) {
    for (const day of week.days || []) {
      dayCount += 1
      if (isDayLocked(day)) continue
      const tasks = day.tasks || []
      taskCount += tasks.length
      openCount += tasks.filter((task) => !['complete', 'review'].includes(taskState(task, day).tone)).length
    }
  }
  return { dayCount, openCount, taskCount }
})

const pastHistorySummary = computed(() => {
  const { dayCount, openCount, taskCount } = pastHistoryMeta.value
  if (openCount > 0) {
    return `${dayCount} 天 · ${openCount} 项未提交`
  }
  if (taskCount > 0) {
    return `${dayCount} 天 · 均已提交`
  }
  return `${dayCount} 天`
})

/** 首屏：今天+后续；展开历史时再 prepend 更早整段。仅有历史时（如筛「已提交」）自动露出历史 */
const timelineWeeks = computed(() => {
  const { past, focus } = timelineSplit.value
  if (!past.length) return focus
  if (!focus.length) return past
  if (pastHistoryOpen.value) return [...past, ...focus]
  return focus
})

function isDayLocked(day) {
  return Boolean(day?.locked) || day?.published === false || String(day?.status || '').toUpperCase() === 'DRAFT'
}

/** 老师尚未发布：宣传场景不展示，避免「待发布」标签 */
function isUnpublishedDay(day) {
  if (!day) return false
  if (day.published === false) return true
  if (String(day.lockReason || '').toUpperCase() === 'NOT_PUBLISHED') return true
  if (String(day.status || '').toUpperCase() === 'DRAFT') return true
  return false
}

function lockedDayLabel(day) {
  if (isUnpublishedDay(day)) {
    return '未开放'
  }
  const value = day?.scheduledUnlockAt || day?.trainingDate
  if (!value) return '未开放'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未开放'
  return `${date.getMonth() + 1}月${date.getDate()}日 00:00开放`
}

function lockedDayMessage(day) {
  if (isUnpublishedDay(day)) {
    return '开放后会显示在这里。'
  }
  return `${lockedDayLabel(day)}，到时再进入详情完成交付。`
}

function startOfCalendarWeek(date) {
  const x = new Date(date)
  x.setHours(0, 0, 0, 0)
  const day = x.getDay() // 0=周日
  const diff = day === 0 ? -6 : 1 - day // 周一为一周起点
  x.setDate(x.getDate() + diff)
  return x
}

function dayDateOnly(day) {
  if (!day?.trainingDate) return null
  const d = new Date(day.trainingDate)
  if (Number.isNaN(d.getTime())) return null
  d.setHours(0, 0, 0, 0)
  return d
}

/** 是否本自然周（周一—周日，含今天） */
function isInThisCalendarWeek(day) {
  const d = dayDateOnly(day)
  if (!d) {
    return String(day?.progressStatus || '').toUpperCase() === 'TODAY'
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const weekStart = startOfCalendarWeek(today)
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekEnd.getDate() + 6)
  return d.getTime() >= weekStart.getTime() && d.getTime() <= weekEnd.getTime()
}

/** 今天之后的训练日（本周内灰度） */
function isFutureTimelineDay(day) {
  if (!day || isPastTimelineDay(day)) return false
  const ps = String(day.progressStatus || '').toUpperCase()
  if (ps === 'TODAY') return false
  if (ps === 'UPCOMING') return true
  const d = dayDateOnly(day)
  if (!d) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return d.getTime() > today.getTime()
}

/** 锁定日标题：去掉与日期行重复的「第 N 天」前缀 */
function lockedDayTitle(day) {
  const raw = String(day?.title || '').trim()
  const dayNo = Number(day?.dayNo)
  if (!raw) return '训练任务未开放'
  if (!dayNo) return raw
  const stripped = raw
    .replace(new RegExp(`^第\\s*${dayNo}\\s*天[：:·\\-—\\s]*训练任务\\s*$`), '')
    .replace(new RegExp(`^第\\s*${dayNo}\\s*天[：:·\\-—\\s]*`), '')
    .trim()
  return stripped || '训练任务未开放'
}

function taskState(task, day) {
  if (isDayLocked(day)) return { tone: 'locked', label: lockedDayLabel(day) }
  const status = String(task.latestSubmissionStatus || '').toUpperCase()
  if (status === 'APPROVED') return { tone: 'complete', label: '已完成' }
  if (['PENDING_REVIEW', 'REVIEWING'].includes(status)) return { tone: 'review', label: '待批改' }
  if (['CHANGES_REQUESTED', 'REJECTED'].includes(status)) return { tone: 'revision', label: '需修改' }
  if (String(day.progressStatus).toUpperCase() === 'EXPIRED') return { tone: 'overdue', label: '待补交' }
  if (String(day.progressStatus).toUpperCase() === 'TODAY') return { tone: 'active', label: '进行中' }
  return { tone: 'upcoming', label: '未开始' }
}

function taskActionLabel(task, day) {
  return {
    complete: '查看成果',
    review: '查看提交',
    revision: '去修改',
    overdue: '去补交',
    active: '开始任务',
    upcoming: '查看要求',
    locked: '暂不可进入'
  }[taskState(task, day).tone] || '进入任务'
}

function taskDisplayTitle(task, day) {
  const title = String(task?.title || '').trim()
  const dayNo = Number(day?.dayNo)
  if (!title || !dayNo) return title
  return title.replace(new RegExp(`^第\\s*${dayNo}\\s*天[：:·\\-—\\s]*`), '').trim() || title
}

function hasLearning(day) {
  return !isDayLocked(day) && Number(day?.learningResourceCount || 0) > 0
}

function completedLearningCount(day) {
  return Number(day?.completedLearningCount ?? day?.learningCompletedCount ?? 0)
}

function estimatedLearningMinutes(day) {
  const aggregateMinutes = Number(day?.estimatedLearningMinutes ?? day?.learningEstimatedMinutes ?? 0)
  const previewSeconds = Number(day?.learningPreview?.durationSeconds || 0)
  return aggregateMinutes || (previewSeconds > 0 ? Math.ceil(previewSeconds / 60) : 0)
}

function learningRate(day) {
  const total = Number(day?.learningResourceCount || 0)
  const completed = completedLearningCount(day)
  if (total <= 0) return 0
  const previewCompleted = String(day?.learningPreview?.learningStatus || '').toUpperCase() === 'COMPLETED'
  const previewProgress = previewCompleted
    ? 0
    : Math.min(100, Math.max(0, Number(day?.learningPreview?.progressPercent || 0)))
  return Math.min(100, Math.round(((completed + previewProgress / 100) / total) * 100))
}

function learningRemaining(day) {
  return Math.max(0, Number(day?.learningResourceCount || 0) - completedLearningCount(day))
}

function learningPreviewTitle(day) {
  const title = String(day?.learningPreview?.title || '').trim()
  const looksMachineGenerated = /^[a-f0-9_-]{24,}$/i.test(title)
    || /\.(mp4|webm|mov|pdf|pptx?|docx?)$/i.test(title)
  if (title && !looksMachineGenerated) return title
  const firstTask = Array.isArray(day?.tasks) ? day.tasks[0] : null
  const taskTitle = firstTask ? taskDisplayTitle(firstTask, day) : ''
  return {
    VIDEO: taskTitle ? `${taskTitle}操作演示` : '观看任务操作演示',
    DOCUMENT: taskTitle ? `${taskTitle}学习资料` : '阅读任务学习资料',
    LINK: taskTitle ? `${taskTitle}在线学习` : '完成在线学习'
  }[learningType(day)] || '查看今天的学习内容'
}

function learningType(day) {
  return String(day?.learningPreview?.resourceType || '').toUpperCase()
}

function learningIcon(day) {
  return {
    VIDEO: VideoPlay,
    DOCUMENT: Document,
    LINK: LinkIcon
  }[learningType(day)] || VideoPlay
}

function learningTypeLabel(day) {
  const videoCount = Number(day?.videoResourceCount || 0)
  const documentCount = Number(day?.documentResourceCount || 0)
  const linkCount = Number(day?.linkResourceCount || 0)
  const kinds = [videoCount > 0, documentCount > 0, linkCount > 0].filter(Boolean).length
  if (kinds > 1) return '学习资料'
  return {
    VIDEO: '视频学习',
    DOCUMENT: '资料阅读',
    LINK: '在线学习',
    EMBED_VIDEO: '站外视频'
  }[learningType(day)] || '学习内容'
}

function learningResourceSummary(day) {
  const parts = []
  const videoCount = Number(day?.videoResourceCount || 0)
  const documentCount = Number(day?.documentResourceCount || 0)
  const linkCount = Number(day?.linkResourceCount || 0)
  if (videoCount) parts.push(`${videoCount} 个视频`)
  if (documentCount) parts.push(`${documentCount} 份资料`)
  if (linkCount) parts.push(`${linkCount} 个链接`)
  if (!parts.length) parts.push(`${Number(day?.learningResourceCount || 0)} 项学习内容`)
  const minutes = estimatedLearningMinutes(day)
  if (minutes > 0) parts.push(`预计 ${minutes} 分钟`)
  return parts.join(' · ')
}

function learningStatusLabel(day) {
  const rate = learningRate(day)
  if (rate >= 100) return '已完成'
  if (learningHasProgress(day)) return '学习中'
  return '未开始'
}

function learningHasProgress(day) {
  const status = String(day?.learningPreview?.learningStatus || '').toUpperCase()
  return completedLearningCount(day) > 0
    || Number(day?.learningPreview?.progressPercent || 0) > 0
    || ['IN_PROGRESS', 'LEARNING'].includes(status)
}

function dayLearningRoute(day) {
  const firstTask = Array.isArray(day?.tasks) ? day.tasks[0] : null
  return firstTask?.taskId
    ? `/training/tasks/${firstTask.taskId}?dayId=${day.dayId}#training-learning`
    : '/training/today'
}

function matchesFilter(task, day, filter) {
  if (isUnpublishedDay(day)) return false
  if (isDayLocked(day)) return filter === 'all' || filter === 'upcoming'
  const tone = taskState(task, day).tone
  if (filter === 'current') {
    // 待完成：本周今天+未来未完成（含未开始的灰度日）；过去补交不进默认列表
    if (!isInThisCalendarWeek(day) || isPastTimelineDay(day)) return false
    return ['active', 'revision', 'upcoming'].includes(tone)
  }
  if (filter === 'upcoming') return tone === 'upcoming'
  if (filter === 'completed') return ['complete', 'review'].includes(tone)
  return true
}

function matchesTaskSearch(task, day) {
  if (!normalizedTaskSearch.value) return true
  const haystack = [
    taskDisplayTitle(task, day),
    task?.title,
    task?.description,
    taskState(task, day).label,
    priorityLabel(task?.priority),
    day?.title,
    monthDay(day?.trainingDate),
    weekday(day?.trainingDate)
  ].filter(Boolean).join(' ').toLocaleLowerCase()
  return haystack.includes(normalizedTaskSearch.value)
}

function matchesDaySearch(day) {
  if (!normalizedTaskSearch.value) return true
  const haystack = [
    day?.title,
    lockedDayLabel(day),
    lockedDayMessage(day),
    monthDay(day?.trainingDate),
    weekday(day?.trainingDate)
  ].filter(Boolean).join(' ').toLocaleLowerCase()
  return haystack.includes(normalizedTaskSearch.value)
}

function countByFilter(filter) {
  return allTasks.value.filter(({ task, day }) => matchesFilter(task, day, filter)).length
}

function weekStats(week) {
  const entries = (week.days || []).flatMap(day => (day.tasks || []).map(task => ({ task, day })))
  const submitted = entries.filter(({ task, day }) => ['complete', 'review'].includes(taskState(task, day).tone)).length
  const total = entries.length
  return {
    submitted,
    total,
    rate: total ? Math.round((submitted / total) * 100) : 0
  }
}

function weekTaskSummary(week) {
  const { submitted, total } = weekStats(week)
  const locked = (week.days || []).filter((day) => isDayLocked(day)).length
  // 全是未开放天：0/0 无意义，改为「N 天未开放」
  if (total === 0 && locked > 0) return `${locked} 天未开放`
  if (total === 0) return '暂无任务'
  return `${submitted} / ${total} 项已提交`
}

function weekTitle(week) {
  const weekNo = Number(week?.weekNo) || 1
  const customTitle = String(week?.title || '').trim()
  const normalizedTitle = customTitle.replace(/\s+/g, '')
  if (!customTitle || normalizedTitle === `第${weekNo}周`) return '本周训练'
  return customTitle
}

function dayTone(day) {
  if (isUnpublishedDay(day)) return 'locked'
  if (isDayLocked(day)) return 'locked'
  return { SUBMITTED: 'complete', TODAY: 'active', EXPIRED: 'overdue', UPCOMING: 'upcoming' }[String(day.progressStatus || '').toUpperCase()] || 'upcoming'
}

/** 是否属于「今天之前」时间线（整段可折叠） */
function isPastTimelineDay(day) {
  if (!day) return false
  const ps = String(day.progressStatus || '').toUpperCase()
  if (ps === 'TODAY') return false
  if (ps === 'UPCOMING') return false
  if (ps === 'SUBMITTED' || ps === 'EXPIRED') return true
  // 未发布但日期已过，仍算更早
  if (day.trainingDate) {
    const d = new Date(day.trainingDate)
    if (!Number.isNaN(d.getTime())) {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      d.setHours(0, 0, 0, 0)
      return d.getTime() < today.getTime()
    }
  }
  return false
}

function priorityLabel(priority) {
  return { HIGH: '高优先级', MEDIUM: '中优先级', LOW: '常规任务' }[String(priority || '').toUpperCase()] || '常规任务'
}

function dueLabel(value) {
  if (!value) return '截止时间待定'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '截止时间待定'
  return `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')} 截止`
}

function monthDay(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : `${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
}

function weekday(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()]
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchTrainingPlan()
  } catch (loadError) {
    error.value = loadError?.message || '请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.training-tasks-page {
  --tasks-orange: #ff6a2a;
  --tasks-orange-soft: #fff1e8;
  --tasks-ink: #1f2430;
  --tasks-muted: #6f7684;
  --tasks-line: #e8e3dc;
}

/* 本周未来训练日：灰度，弱化为「预告」 */
.tasks-day.is-future-dim {
  opacity: 0.55;
  filter: grayscale(0.35);
}

.tasks-day.is-future-dim .task-item {
  background: #f8f9fb;
  border-color: #e6e8ee;
}

.tasks-day.is-future-dim .task-item__action strong {
  color: var(--tasks-muted, #6f7684);
}

.tasks-day.is-future-dim .tasks-day__date strong,
.tasks-day.is-future-dim .tasks-day__date small {
  color: var(--tasks-muted, #6f7684);
}

.task-item.is-locked {
  cursor: not-allowed;
  opacity: 0.9;
  background: #f8fafc;
  border-color: #d8dee6;
  pointer-events: none;
}

.task-item--locked-compact {
  min-height: 0;
  align-items: center;
}

.task-item--locked-compact .task-item__content p.task-item__locked-hint {
  display: -webkit-box;
  margin-top: 4px;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: #8b929e;
  font-size: 12px;
  line-height: 1.4;
}

.task-item--locked-compact .task-item__action {
  align-content: center;
  gap: 0;
}

.task-item--locked-compact .task-item__action strong {
  display: none;
}

/* 桌面：锁定卡稍扁，少占竖向 */
@media (min-width: 761px) {
  .task-item--locked-compact {
    min-height: 72px;
    padding: 14px 16px;
  }
}

.task-item__signal.is-locked,
.task-item__action .is-locked {
  color: #64748b;
  background: #e2e8f0;
}

.tasks-day.is-locked {
  opacity: 0.96;
}

/* 紧凑指挥条：一屏内完成总览，把纵向空间留给时间线 */
.tasks-command {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px 24px;
  min-height: 0;
  padding: 10px 0 12px;
  border-bottom: 1px solid var(--tasks-line);
}

.tasks-command__identity {
  min-width: 0;
  flex: 1 1 auto;
}

.tasks-command__identity h1 {
  margin: 0;
  color: var(--tasks-ink);
  font-size: 20px;
  font-weight: 760;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.tasks-command__identity p {
  margin: 5px 0 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  color: var(--tasks-muted);
  font-size: 12px;
  line-height: 1.4;
}

.tasks-command__camp {
  color: var(--tasks-ink);
  font-weight: 650;
}

.tasks-command__sep {
  color: #c8cdd6;
}

.tasks-command__stats {
  flex: 0 1 auto;
  display: flex;
  align-items: center;
  gap: 0;
  min-width: 0;
}

.tasks-command__progress {
  min-width: 148px;
  max-width: 200px;
  margin-right: 4px;
  display: grid;
  gap: 6px;
}

.tasks-command__progress-copy {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.tasks-command__progress-copy strong {
  color: var(--tasks-orange);
  font-size: 14px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.tasks-command__progress-copy span {
  color: var(--tasks-muted);
  font-size: 11px;
  white-space: nowrap;
}

.tasks-progress-track {
  overflow: hidden;
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: #ece8e3;
}

.tasks-progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--tasks-orange);
}

.tasks-command__metric {
  min-width: 72px;
  padding: 2px 14px;
  border-left: 1px solid var(--tasks-line);
  text-align: center;
}

.tasks-command__metric strong {
  display: block;
  color: var(--tasks-ink);
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.tasks-command__metric span {
  display: block;
  margin-top: 3px;
  color: var(--tasks-muted);
  font-size: 11px;
}

.tasks-toolbar {
  margin: 12px 0 12px;
  display: grid;
  gap: 0;
}

.tasks-toolbar--compact {
  margin-top: 10px;
}

.tasks-toolbar__controls {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  min-height: 44px;
  padding: 3px;
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid rgba(31, 36, 48, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 4px 14px rgba(31, 36, 48, 0.03),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.tasks-filter {
  box-sizing: border-box;
  flex: 0 0 auto;
  max-width: min(100%, 440px);
  padding: 0;
  display: flex;
  align-items: center;
  gap: 2px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  box-shadow: none;
}

.tasks-filter button {
  box-sizing: border-box;
  min-height: 40px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 1px solid transparent;
  border-radius: 10px;
  color: #596170;
  background: transparent;
  font: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition:
    color 160ms ease,
    background-color 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.tasks-filter__label {
  font-size: 13px;
  font-weight: 650;
  line-height: 1;
  letter-spacing: -0.01em;
}

.tasks-filter__count {
  min-width: 12px;
  height: auto;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0;
  color: #818793;
  background: transparent;
  font-size: 10px;
  font-weight: 750;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.tasks-filter__count.is-zero {
  color: #a0a5ae;
  background: transparent;
}

.tasks-filter button:hover:not(.is-active) {
  color: var(--tasks-ink);
  background: rgba(255, 255, 255, 0.78);
}

.tasks-filter button.is-active {
  color: #c94512;
  border-color: rgba(255, 106, 42, 0.16);
  background: var(--tasks-orange-soft);
  box-shadow:
    0 3px 9px rgba(120, 53, 23, 0.055),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.tasks-filter button.is-active .tasks-filter__count {
  color: #c94512;
  border-color: transparent;
  background: transparent;
}

.tasks-filter button:active {
  transform: scale(0.98);
}

.tasks-filter button:focus-visible {
  outline: 2px solid var(--tasks-orange);
  outline-offset: 2px;
}

.tasks-toolbar__divider {
  width: 1px;
  height: 24px;
  margin: 0 10px;
  flex: 0 0 1px;
  background: rgba(31, 36, 48, 0.1);
}

.tasks-search {
  box-sizing: border-box;
  min-width: 180px;
  min-height: 40px;
  padding: 0 8px 0 10px;
  flex: 1 1 280px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  box-shadow: none;
  transition:
    background-color 160ms ease;
}

.tasks-search:focus-within {
  background: rgba(255, 106, 42, 0.045);
  box-shadow: inset 0 0 0 1px rgba(255, 106, 42, 0.13);
}

.tasks-search > svg {
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  color: #4f5663;
}

.tasks-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: var(--tasks-ink);
  background: transparent;
  font: inherit;
  font-size: 13px;
}

.tasks-search input::placeholder {
  color: #9298a3;
}

.tasks-search input::-webkit-search-cancel-button {
  display: none;
}

.tasks-search button {
  width: 30px;
  height: 30px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 8px;
  color: #737a87;
  background: transparent;
  cursor: pointer;
}

.tasks-search button:hover {
  color: var(--tasks-ink);
  background: rgba(31, 36, 48, 0.055);
}

.tasks-search button:focus-visible {
  outline: 2px solid var(--tasks-orange);
  outline-offset: 1px;
}

.tasks-search button svg {
  width: 15px;
  height: 15px;
}

.tasks-toolbar__result {
  margin-left: auto;
  padding: 0 13px;
  flex: 0 0 auto;
  color: #818793;
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
}

.tasks-toolbar__result strong {
  margin: 0 2px;
  color: var(--tasks-ink);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.tasks-timeline {
  display: grid;
  gap: 36px;
}

.tasks-week {
  position: relative;
  min-width: 0;
}

.tasks-week__head {
  position: relative;
  z-index: 2;
  min-width: 0;
  min-height: 56px;
  padding: 8px 0 18px 42px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(132px, 180px);
  align-items: center;
  gap: 24px;
}

.tasks-week__anchor {
  position: absolute;
  top: 25px;
  left: 10px;
  z-index: 2;
  box-sizing: border-box;
  width: 9px;
  height: 9px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: var(--tasks-orange);
  box-shadow:
    0 0 0 1px rgba(255, 106, 42, 0.42),
    0 0 14px rgba(255, 106, 42, 0.22);
  transform: translate(-50%, -50%);
}

.tasks-week__identity {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.tasks-week__number {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: 999px;
  color: var(--tasks-orange);
  background: #fff4ee;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0;
}

.tasks-week__title h2,
.tasks-week__title p {
  margin: 0;
}

.tasks-week__title {
  min-width: 0;
}

.tasks-week__title h2 {
  color: var(--tasks-ink);
  font-size: 15px;
  line-height: 1.45;
}

.tasks-week__title p {
  display: block;
  margin-top: 3px;
  color: var(--tasks-muted);
  font-size: 11px;
  line-height: 1.5;
}

.tasks-week__status {
  min-width: 0;
}

.tasks-week__summary {
  display: block;
  color: var(--tasks-muted);
  font-size: 11px;
  line-height: 1.5;
  text-align: right;
}

.tasks-week__progress {
  width: 100%;
  height: 2px;
  margin-top: 8px;
  overflow: hidden;
  background: #dfe1e5;
}

.tasks-week__progress i {
  display: block;
  height: 100%;
  background: var(--tasks-orange);
  transition: width 320ms ease;
}

.tasks-week__days {
  position: relative;
  min-width: 0;
  padding-left: 60px;
}

.tasks-week__days::before,
.tasks-week__days::after {
  content: none;
}

.tasks-day {
  position: relative;
  z-index: 1;
  margin-bottom: 16px;
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
}

.tasks-day:last-child {
  margin-bottom: 0;
}

.tasks-day__date {
  position: relative;
  padding: 22px 18px 22px 0;
}

.tasks-day__date > span,
.tasks-day__date strong,
.tasks-day__date small {
  display: block;
}

.tasks-day__date > span {
  color: #9a9fa8;
  font-size: 10px;
  font-weight: 700;
}

.tasks-day__date strong {
  margin-top: 7px;
  color: var(--tasks-ink);
  font-size: 19px;
}

.tasks-day__date small {
  margin-top: 4px;
  color: var(--tasks-muted);
  font-size: 11px;
}

.tasks-day__date i {
  position: absolute;
  top: 28px;
  left: -30px;
  z-index: 2;
  box-sizing: border-box;
  width: 7px;
  height: 7px;
  border: 1.5px solid #fff;
  border-radius: 50%;
  background: #c7c9ce;
  box-shadow: 0 0 0 1px #c7c9ce;
  transform: translateX(-50%);
}

.tasks-day.is-active .tasks-day__date i {
  background: var(--tasks-orange);
  box-shadow: 0 0 0 1px var(--tasks-orange);
}

.tasks-day.is-active .tasks-day__date i::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 14px;
  height: 14px;
  border: 1px solid rgba(255, 106, 42, 0.44);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(255, 106, 42, 0.2);
  transform: translate(-50%, -50%) scale(0.72);
  animation: tasks-node-breathe 2.4s ease-out infinite;
}

.tasks-day.is-complete .tasks-day__date i {
  background: #2e966a;
  box-shadow: 0 0 0 1px #2e966a;
}

.tasks-day.is-overdue .tasks-day__date i {
  background: #c75a50;
  box-shadow: 0 0 0 1px #c75a50;
}

.tasks-day__body {
  min-width: 0;
  padding: 0 0 2px;
}

/* 更早训练：降权为次级入口，不抢当前任务主视觉 */
.tasks-history-bar {
  box-sizing: border-box;
  width: 100%;
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 0;
  padding: 6px 2px 6px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: color 0.15s ease, opacity 0.15s ease;
  opacity: 0.88;
}

.tasks-history-bar:hover {
  opacity: 1;
  background: transparent;
}

.tasks-history-bar.is-remind {
  border: 0;
  background: transparent;
  opacity: 0.95;
}

.tasks-history-bar.is-remind:hover {
  box-shadow: none;
}

.tasks-history-bar.is-open {
  margin-bottom: 12px;
  opacity: 1;
  background: transparent;
}

.tasks-history-bar__main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tasks-history-bar__icon {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border-radius: 0;
  display: grid;
  place-items: center;
  background: transparent !important;
}

.tasks-history-bar__icon.is-remind {
  color: #b45309;
}

.tasks-history-bar__icon.is-ok {
  color: #94a3b8;
}

.tasks-history-bar__icon :deep(svg) {
  width: 14px;
  height: 14px;
}

.tasks-history-bar__copy {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
}

.tasks-history-bar__copy strong {
  font-size: 12px;
  font-weight: 650;
  color: #6f7684;
}

.tasks-history-bar__copy small {
  font-size: 11px;
  color: #9aa3b2;
  line-height: 1.3;
  font-weight: 500;
}

.tasks-history-bar.is-remind .tasks-history-bar__copy strong {
  color: #7c6a5c;
}

.tasks-history-bar.is-remind .tasks-history-bar__copy small {
  color: #a18b7a;
  font-weight: 550;
}

.tasks-history-bar__action {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 650;
  color: #9aa3b2;
  white-space: nowrap;
}

.tasks-history-bar.is-remind .tasks-history-bar__action {
  color: #9a7b62;
}

.tasks-history-bar__action :deep(svg) {
  width: 12px;
  height: 12px;
}

.tasks-week.is-history {
  opacity: 0.98;
}

.task-item__action > span {
  flex: 0 0 auto;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
}

.task-items {
  display: grid;
  gap: 10px;
}

.task-items.has-learning {
  overflow: hidden;
  gap: 0;
  border: 1px solid #ddd8d1;
  border-radius: 18px;
  background: #fffdfa;
  box-shadow:
    0 1px 2px rgba(31, 36, 48, 0.03),
    0 8px 24px rgba(70, 51, 36, 0.05);
}

.task-learning-preview {
  min-height: 92px;
  padding: 16px 18px;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 58px auto;
  align-items: center;
  gap: 15px;
  color: inherit;
  background:
    radial-gradient(circle at 0 0, rgba(255, 120, 55, 0.08), transparent 34%),
    #fffdfb;
  text-decoration: none;
  transition: background-color 180ms ease;
}

.task-learning-preview:hover,
.task-learning-preview:focus-visible {
  background-color: #fff9f4;
}

.task-learning-preview:focus-visible {
  position: relative;
  z-index: 1;
  outline: 2px solid var(--tasks-orange);
  outline-offset: -2px;
}

.task-learning-preview__icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(231, 87, 30, 0.13);
  border-radius: 13px;
  color: #d9531d;
  background: #fff1e9;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.task-learning-preview__icon svg {
  width: 19px;
  height: 19px;
}

.task-learning-preview__content {
  min-width: 0;
}

.task-learning-preview__eyebrow {
  display: flex;
  align-items: center;
  color: #9a5a3c;
  font-size: 10px;
  font-weight: 750;
}

.task-learning-preview__eyebrow span {
  padding: 3px 7px;
  border-radius: 999px;
  color: #c44d1c;
  background: #fff0e7;
}

.task-learning-preview h4,
.task-learning-preview p {
  margin: 0;
}

.task-learning-preview h4 {
  overflow: hidden;
  margin-top: 6px;
  color: var(--tasks-ink);
  font-size: 14px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-learning-preview p {
  overflow: hidden;
  margin-top: 5px;
  color: var(--tasks-muted);
  font-size: 10px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-learning-preview__progress {
  min-width: 58px;
  display: grid;
  justify-items: center;
  align-items: center;
  gap: 5px;
}

.task-learning-preview__progress > span {
  color: #7f858e;
  font-size: 9px;
  font-weight: 700;
}

.task-learning-preview__progress > span.is-complete {
  color: #24805b;
}

.task-learning-preview__ring {
  position: relative;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(#e75b22 var(--learning-progress), #e9e6e2 0);
  transition: background 220ms ease;
}

.task-learning-preview__ring::before {
  position: absolute;
  inset: 4px;
  border-radius: inherit;
  background: #fffdfb;
  box-shadow: inset 0 0 0 1px rgba(31, 36, 48, 0.035);
  content: '';
}

.task-learning-preview__ring.is-complete {
  background: #2e966a;
}

.task-learning-preview__ring strong {
  position: relative;
  z-index: 1;
  color: #555b65;
  font-size: 10px;
  font-weight: 800;
}

.task-learning-preview__ring.is-complete strong {
  color: #24805b;
}

.task-learning-preview__ring svg {
  width: 16px;
  height: 16px;
}

.task-learning-preview__action {
  min-height: 34px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 5px;
  border: 1px solid rgba(31, 36, 48, 0.09);
  border-radius: 999px;
  color: #454b55;
  background: rgba(255, 255, 255, 0.84);
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
  transition: color 180ms ease, border-color 180ms ease, transform 180ms ease;
}

.task-learning-preview__action svg {
  width: 12px;
}

.task-learning-preview:hover .task-learning-preview__action {
  border-color: rgba(217, 67, 25, 0.25);
  color: #c94e18;
  transform: translateX(2px);
}

.task-items.has-learning .task-item {
  border-width: 1px 0 0;
  border-color: rgba(31, 36, 48, 0.09);
  border-radius: 0;
  box-shadow: none;
}

.task-items.has-learning .task-item:hover,
.task-items.has-learning .task-item:focus-visible {
  border-color: rgba(31, 36, 48, 0.09);
  box-shadow: inset 3px 0 0 rgba(232, 74, 28, 0.42);
}

.task-item {
  min-height: 126px;
  padding: 18px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) minmax(132px, 154px);
  align-items: stretch;
  gap: 16px;
  /* 边框略加深一档，再加极轻阴影，轮廓更清楚但不抢戏 */
  border: 1px solid #ddd7cf;
  border-radius: 16px;
  color: inherit;
  background: #fffdfa;
  box-shadow:
    0 1px 1px rgba(31, 36, 48, 0.025),
    0 2px 8px rgba(70, 51, 36, 0.035);
  text-decoration: none;
  transition: border-color 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
}

.task-item.is-active {
  border-color: rgba(232, 74, 28, 0.3);
  background: #fffaf6;
  box-shadow:
    0 1px 1px rgba(31, 36, 48, 0.03),
    0 3px 10px rgba(232, 74, 28, 0.06);
}

.task-item.is-revision,
.task-item.is-overdue {
  border-color: rgba(200, 78, 54, 0.28);
  background: #fff9f7;
}

.task-item.is-complete,
.task-item.is-review {
  border-color: rgba(36, 128, 91, 0.22);
  background: #fbfdfb;
}

.task-item:hover,
.task-item:focus-visible {
  border-color: rgba(255, 106, 42, 0.38);
  box-shadow: 0 6px 18px rgba(78, 52, 33, 0.07);
}

.task-item:focus-visible {
  outline: 2px solid var(--tasks-orange);
  outline-offset: 2px;
}

.task-item:hover {
  outline: none;
}

.task-item__signal {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  align-self: start;
  border-radius: 50%;
  color: #8b9099;
  background: #f1f2f4;
}

.task-item__signal svg {
  width: 16px;
}

.task-item__signal.is-active,
.task-item__signal.is-revision {
  color: #d4561e;
  background: var(--tasks-orange-soft);
}

.task-item__signal.is-complete,
.task-item__signal.is-review {
  color: #24805b;
  background: #eaf7f0;
}

.task-item__signal.is-overdue {
  color: #b04f46;
  background: #fff0ee;
}

.task-item__content {
  min-width: 0;
  align-self: center;
}

.task-item__title-row {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
}

.task-item h4,
.task-item p {
  margin: 0;
}

.task-item h4 {
  color: var(--tasks-ink);
  font-size: 15px;
  line-height: 1.4;
}

.task-item__primary {
  flex: 0 0 auto;
  padding: 3px 6px;
  border-radius: 5px;
  color: #d5551c;
  background: var(--tasks-orange-soft);
  font-size: 9px;
  font-weight: 750;
}

.task-item p {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 8px;
  color: var(--tasks-muted);
  font-size: 12px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.task-item__meta {
  margin-top: 12px;
  padding-top: 11px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px 14px;
  border-top: 1px solid rgba(31, 36, 48, 0.07);
  color: #8a9099;
  font-size: 10px;
}

.task-item__meta b {
  color: #4d535e;
  font: inherit;
  font-weight: 800;
}

.task-item__meta .is-high,
.task-item__meta .is-urgent {
  color: #b84b29;
  font-weight: 700;
}

.task-item__meta span {
  position: relative;
}

.task-item__meta span + span::before {
  position: absolute;
  top: 50%;
  left: -8px;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #babdc3;
  content: '';
}

.task-item__action {
  min-width: 0;
  padding-left: 18px;
  display: grid;
  align-content: center;
  justify-items: end;
  gap: 14px;
  border-left: 1px solid rgba(31, 36, 48, 0.08);
}

.task-item__action > span {
  padding: 4px 8px;
  color: #747a84;
  background: #f1f2f4;
}

.task-item__action > span.is-active,
.task-item__action > span.is-revision {
  color: #c94e18;
  background: var(--tasks-orange-soft);
}

.task-item__action > span.is-complete,
.task-item__action > span.is-review {
  color: #19714d;
  background: #eaf7f0;
}

.task-item__action > span.is-overdue {
  color: #a94841;
  background: #fff0ee;
}

.task-item__action strong {
  box-sizing: border-box;
  min-height: 36px;
  padding: 0 13px;
  display: flex;
  align-items: center;
  gap: 5px;
  border-radius: 999px;
  color: #363b45;
  background: #f1f1f0;
  font-size: 12px;
  font-weight: 750;
}

.task-item.is-active .task-item__action strong,
.task-item.is-revision .task-item__action strong,
.task-item.is-overdue .task-item__action strong {
  color: #fffaf7;
  background: #d94319;
}

.task-item.is-complete .task-item__action strong,
.task-item.is-review .task-item__action strong {
  color: #176548;
  background: #eaf7f0;
}

.task-item__action svg {
  width: 13px;
  transition: transform 180ms ease;
}

.task-item:hover .task-item__action svg {
  transform: translateX(3px);
}

.tasks-filter-empty {
  min-height: 280px;
  display: grid;
  place-items: center;
  align-content: center;
  text-align: center;
}

.tasks-filter-empty > svg {
  width: 30px;
  color: var(--tasks-orange);
}

.tasks-filter-empty h2 {
  margin: 14px 0 0;
  font-size: 17px;
}

.tasks-filter-empty p {
  margin: 7px 0 15px;
  color: var(--tasks-muted);
  font-size: 12px;
}

.tasks-filter-empty button {
  border: 0;
  color: var(--tasks-orange);
  background: transparent;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

@supports (animation-timeline: view()) {
  .tasks-day {
    animation: tasks-day-enter both;
    animation-timeline: view();
    animation-range: entry 5% entry 32%;
  }
}

@keyframes tasks-day-enter {
  from {
    opacity: 0;
    transform: translateY(12px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes tasks-node-breathe {
  0% {
    opacity: 0.78;
    transform: translate(-50%, -50%) scale(0.72);
  }

  72%,
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(1);
  }
}

@media (max-width: 960px) {
  .tasks-command {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .tasks-command__stats {
    justify-content: flex-start;
  }

  .tasks-command__progress {
    flex: 1;
    max-width: none;
  }
}

@media (max-width: 760px) {
  /* —— 总览：一行标题 + 紧凑进度条，去掉大白块 —— */
  .tasks-command {
    gap: 8px;
    padding: 2px 0 8px;
  }

  .tasks-command__identity h1 {
    font-size: 17px;
    letter-spacing: -0.02em;
  }

  .tasks-command__identity p {
    margin-top: 3px;
    font-size: 11px;
    gap: 2px 4px;
    line-height: 1.35;
  }

  .tasks-command__stats {
    flex-wrap: nowrap;
    align-items: center;
    width: 100%;
    padding: 8px 10px;
    border: 1px solid rgba(31, 36, 48, 0.07);
    border-radius: 12px;
    background: #fff;
    gap: 0;
  }

  .tasks-command__progress {
    flex: 1 1 auto;
    width: auto;
    max-width: none;
    min-width: 0;
    margin: 0 8px 0 0;
  }

  .tasks-command__progress-copy strong {
    font-size: 13px;
  }

  .tasks-command__progress-copy span {
    font-size: 10px;
  }

  .tasks-progress-track {
    height: 3px;
  }

  .tasks-command__metric {
    flex: 0 0 auto;
    min-width: 44px;
    border-left: 1px solid var(--tasks-line);
    padding: 0 0 0 10px;
    text-align: center;
  }

  .tasks-command__metric strong {
    font-size: 15px;
  }

  .tasks-command__metric span {
    font-size: 10px;
    margin-top: 1px;
  }

  /* —— 筛选：chips 横滑 + 搜索一行紧贴 —— */
  .tasks-toolbar {
    margin: 6px 0 8px;
  }

  .tasks-toolbar__controls {
    flex-wrap: wrap;
    min-height: 0;
    padding: 4px;
    gap: 4px;
    border-radius: 12px;
  }

  .tasks-filter {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    padding: 0;
    overflow-x: auto;
    border-bottom: 0;
    border-radius: 0;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;
  }

  .tasks-filter::-webkit-scrollbar {
    display: none;
  }

  .tasks-filter button {
    flex: 0 0 auto;
    min-height: 32px;
    padding: 0 8px;
  }

  .tasks-filter__label {
    font-size: 12px;
  }

  .tasks-filter__count {
    font-size: 10px;
  }

  .tasks-toolbar__divider {
    display: none;
  }

  .tasks-search {
    flex: 1 1 auto;
    width: 100%;
    min-width: 0;
    min-height: 34px;
    padding: 0 8px 0 10px;
    border-radius: 9px;
    background: rgba(31, 36, 48, 0.045);
  }

  .tasks-search > svg {
    width: 15px;
    height: 15px;
    flex: 0 0 15px;
    color: #6b7280;
  }

  .tasks-search input {
    font-size: 12px;
  }

  .tasks-toolbar__result {
    display: none;
  }

  /*
   * 时间线对齐（保持光束 week=x10 / day=x30 原路径样式）：
   * - 周锚点 left:10
   * - 日节点中心落在 x=30（padding-left 36 → left -6）
   */
  .tasks-timeline {
    gap: 14px;
  }

  .tasks-week {
    min-width: 0;
  }

  .tasks-week__head {
    min-height: 0;
    padding: 2px 0 6px 36px;
    grid-template-columns: 1fr auto;
    gap: 6px 10px;
    align-items: center;
  }

  .tasks-week__anchor {
    top: 50%;
    left: 10px;
    width: 9px;
    height: 9px;
  }

  .tasks-week__identity {
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .tasks-week__number {
    padding: 2px 6px;
    font-size: 10px;
  }

  .tasks-week__title h2 {
    font-size: 13px;
    line-height: 1.3;
  }

  .tasks-week__title p {
    display: none;
  }

  .tasks-week__status {
    max-width: 96px;
    width: auto;
  }

  .tasks-week__summary {
    text-align: right;
    font-size: 10px;
    white-space: nowrap;
    color: #8b929e;
  }

  .tasks-week__progress {
    margin-top: 4px;
    height: 2px;
  }

  .tasks-week__days {
    padding-left: 36px;
    display: grid;
    gap: 0;
  }

  /* —— 日行：日期 + 内容，锁定日压成单行 —— */
  .tasks-day {
    grid-template-columns: 1fr;
    margin-bottom: 0;
  }

  .tasks-day:not(.is-locked-day) {
    margin-bottom: 10px;
  }

  .tasks-day__date {
    position: relative;
    padding: 0 0 6px;
    display: flex;
    align-items: center;
    flex-wrap: nowrap;
    gap: 6px;
  }

  .tasks-day__date > span {
    order: 1;
    padding: 1px 6px;
    border-radius: 999px;
    background: #eef0f3;
    color: #6b7280;
    font-size: 10px;
    font-weight: 700;
  }

  .tasks-day__date strong {
    order: 2;
    margin: 0;
    font-size: 13px;
    font-weight: 700;
  }

  .tasks-day__date small {
    order: 3;
    margin: 0;
    font-size: 11px;
    color: #9aa3b2;
  }

  /* day 节点中心 ≈ 30px，对应光束 day track */
  .tasks-day__date i {
    top: 50%;
    left: -6px;
    width: 7px;
    height: 7px;
    transform: translate(-50%, -50%);
  }

  .tasks-day.is-active .tasks-day__date i::after {
    width: 12px;
    height: 12px;
  }

  .tasks-day__body {
    padding: 0;
  }

  /*
   * 锁定日单行：
   *  [●] 第12天  08.07 周五          待教师发布
   * 去掉白卡片 / 时钟图标 / 重复标题 / 长说明
   */
  .tasks-day.is-locked-day {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 40px;
    margin: 0;
    padding: 0 4px 0 0;
    border-bottom: 1px solid rgba(31, 36, 48, 0.06);
  }

  .tasks-day.is-locked-day:last-child {
    border-bottom: 0;
  }

  .tasks-day.is-locked-day .tasks-day__date {
    flex: 1 1 auto;
    min-width: 0;
    padding: 10px 0;
    gap: 6px;
  }

  .tasks-day.is-locked-day .tasks-day__date > span {
    background: transparent;
    padding: 0;
    color: #6f7684;
    font-size: 12px;
    font-weight: 650;
  }

  .tasks-day.is-locked-day .tasks-day__date strong {
    font-size: 13px;
    font-weight: 700;
    color: var(--tasks-ink);
  }

  .tasks-day.is-locked-day .tasks-day__date small {
    font-size: 11px;
  }

  .tasks-day.is-locked-day .tasks-day__date i {
    top: 50%;
  }

  .tasks-day.is-locked-day .tasks-day__body {
    flex: 0 0 auto;
  }

  .tasks-day.is-locked-day .task-items {
    gap: 0;
  }

  .tasks-day.is-locked-day .task-item--locked-compact {
    display: flex;
    align-items: center;
    min-height: 0;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    opacity: 1;
    grid-template-columns: none;
  }

  .tasks-day.is-locked-day .task-item__signal,
  .tasks-day.is-locked-day .task-item__content {
    display: none;
  }

  .tasks-day.is-locked-day .task-item__action {
    display: flex;
    margin: 0;
    padding: 0;
    border: 0;
    grid-column: auto;
  }

  .tasks-day.is-locked-day .task-item__action > span {
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
    background: #eef1f5;
    white-space: nowrap;
  }

  .task-items {
    gap: 6px;
  }

  .task-items.has-learning {
    border-radius: 12px;
  }

  /* 学习预览：更扁 */
  .task-learning-preview {
    min-height: 0;
    padding: 10px;
    grid-template-columns: 32px minmax(0, 1fr) auto;
    gap: 8px;
    align-items: center;
  }

  .task-learning-preview__icon {
    width: 32px;
    height: 32px;
    border-radius: 9px;
  }

  .task-learning-preview__icon svg {
    width: 15px;
    height: 15px;
  }

  .task-learning-preview h4 {
    margin-top: 2px;
    font-size: 13px;
    white-space: normal;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
  }

  .task-learning-preview p {
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
    -webkit-line-clamp: unset;
  }

  .task-learning-preview__progress {
    grid-column: auto;
    grid-row: auto;
    justify-self: end;
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .task-learning-preview__ring {
    width: 30px;
    height: 30px;
  }

  .task-learning-preview__action {
    display: none;
  }

  /* 可进入任务：图标 + 正文，底栏状态/操作 */
  .task-item {
    min-height: 0;
    padding: 10px 12px;
    grid-template-columns: 28px minmax(0, 1fr);
    gap: 6px 10px;
    border-radius: 12px;
    align-items: start;
  }

  .task-item__signal {
    width: 28px;
    height: 28px;
    align-self: start;
  }

  .task-item__signal svg {
    width: 13px;
  }

  .task-item__content h4 {
    font-size: 13px;
    line-height: 1.3;
  }

  .task-item__content p {
    margin-top: 2px;
    font-size: 11px;
    line-height: 1.4;
    -webkit-line-clamp: 1;
  }

  .task-item__meta {
    margin-top: 4px;
    padding-top: 0;
    border-top: 0;
    gap: 4px 10px;
    font-size: 10px;
  }

  .task-item__meta span + span::before {
    left: -6px;
  }

  .task-item__action {
    grid-column: 1 / -1;
    min-width: 0;
    margin: 0;
    padding: 6px 0 0;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    border-top: 1px solid rgba(31, 36, 48, 0.06);
    border-left: 0;
  }

  .task-item__action > span {
    font-size: 10px;
    padding: 3px 7px;
  }

  .task-item__action strong {
    min-height: 28px;
    padding: 0 10px;
    font-size: 11px;
  }

  /* 桌面锁卡在移动端已被 is-locked-day 覆盖；此块兜底 */
  .task-item--locked-compact {
    opacity: 1;
  }

  .tasks-history-bar {
    padding: 6px 0 6px 36px;
    margin-bottom: 2px;
  }

  .tasks-history-bar__copy {
    flex-direction: row;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 2px 6px;
  }

  .tasks-history-bar__copy strong {
    font-size: 12px;
  }

  .tasks-history-bar__copy small {
    font-size: 10px;
  }
}

/* 更窄屏：保持 week=10 / day=30 对齐 */
@media (max-width: 420px) {
  .tasks-week__days,
  .tasks-week__head {
    padding-left: 34px;
  }

  .tasks-week__anchor {
    left: 10px;
  }

  .tasks-day__date i {
    left: -4px;
  }

  .tasks-history-bar {
    padding-left: 34px;
  }

  .task-item:not(.task-item--locked-compact),
  .task-learning-preview {
    padding: 9px 10px;
  }

  .task-item__action strong {
    font-size: 11px;
    padding: 0 8px;
  }

  .tasks-command__metric {
    min-width: 40px;
    padding-left: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tasks-day {
    animation: none;
  }

  .tasks-day.is-active .tasks-day__date i::after {
    opacity: 0.48;
    transform: translate(-50%, -50%) scale(0.8);
    animation: none;
  }

  .tasks-week__progress i,
  .tasks-filter button,
  .tasks-search,
  .task-learning-preview,
  .task-learning-preview__action,
  .task-learning-preview__ring,
  .task-item,
  .task-item__action svg {
    transition: none;
  }

  .tasks-filter button:active {
    transform: none;
  }
}
</style>
