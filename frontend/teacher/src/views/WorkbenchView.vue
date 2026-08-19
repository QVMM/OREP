<template>
  <div class="teacher-page workbench-page">
    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>

    <section v-if="!loading && !ctx.hasProjects" class="teacher-card workbench-empty">
      <h2>还没有关联项目</h2>
      <p>当前账号下没有可管理的项目数据。请先创建项目或确认教师账号已绑定项目指导关系。</p>
      <router-link class="teacher-btn teacher-btn--primary" to="/projects/create">新建项目</router-link>
    </section>

    <template v-else>
      <!-- ① 状态栏：对齐学生端 home-status，无卡通 emoji -->
      <header class="wb-status" data-testid="teacher-home-hero">
        <div class="wb-status__identity">
          <p class="wb-status__eyebrow">{{ statusEyebrow }}</p>
          <h1>{{ greetingLine }}</h1>
          <p class="wb-status__sub">{{ statusSubline }}</p>
        </div>
        <div class="wb-status__metrics">
          <div class="wb-status__metric">
            <span>今日在线</span>
            <strong>
              {{ workbench.onlineToday ?? 0 }}<small>人</small>
            </strong>
            <p>备赛学生活跃</p>
          </div>
          <div class="wb-status__metric">
            <span>{{ hasCamp ? '进行到' : '备赛状态' }}</span>
            <strong v-if="hasCamp" class="wb-status__day">
              <template v-if="camp.currentDay != null">
                <span class="wb-status__day-unit">第</span>
                <span class="wb-status__day-num">{{ camp.currentDay }}</span>
                <span class="wb-status__day-unit">天</span>
              </template>
              <template v-else>—</template>
            </strong>
            <strong v-else class="is-empty">待开启</strong>
            <p v-if="hasCamp && camp.totalDays">
              共 {{ camp.totalDays }} 天
              <template v-if="camp.remainingDays != null"> · 剩 {{ camp.remainingDays }} 天</template>
            </p>
            <p v-else-if="!hasCamp">关联训练营后显示</p>
          </div>
        </div>
      </header>

      <!-- ② 三入口 -->
      <section class="wb-entry" aria-label="快捷入口">
        <router-link class="wb-entry__card" to="/members">
          <span class="wb-entry__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </span>
          <span class="wb-entry__meta">
            <small>候选学生</small>
            <strong>{{ num(workbench.candidateCount) }}<em>人待选</em></strong>
          </span>
          <svg class="wb-entry__chev" viewBox="0 0 20 20" aria-hidden="true">
            <path d="m7 5 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </router-link>

        <router-link class="wb-entry__card" to="/analytics">
          <span class="wb-entry__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 19V5" />
              <path d="M4 19h16" />
              <path d="M8 16V10" />
              <path d="M12 16V7" />
              <path d="M16 16v-4" />
            </svg>
          </span>
          <span class="wb-entry__meta">
            <small>训练数据</small>
            <strong>{{ num(workbench.onlineToday) }}<em>人今日在线</em></strong>
          </span>
          <svg class="wb-entry__chev" viewBox="0 0 20 20" aria-hidden="true">
            <path d="m7 5 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </router-link>

        <router-link class="wb-entry__card" to="/review/reports">
          <span class="wb-entry__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" />
              <circle cx="12" cy="12" r="4" />
              <path d="M12 3v2" />
              <path d="M12 19v2" />
              <path d="M3 12h2" />
              <path d="M19 12h2" />
            </svg>
          </span>
          <span class="wb-entry__meta">
            <small>AI 评分</small>
            <strong>{{ num(workbench.newReportCount) }}<em>份近7日报告</em></strong>
          </span>
          <svg class="wb-entry__chev" viewBox="0 0 20 20" aria-hidden="true">
            <path d="m7 5 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </router-link>
      </section>

      <!-- ③ 学习时长 + 进步之星 -->
      <section class="wb-mid">
        <article class="teacher-card wb-card">
          <div class="wb-card__head">
            <h2>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M4 19V5" stroke-linecap="round" />
                <path d="M4 19h16" stroke-linecap="round" />
                <path d="M8 15V9" stroke-linecap="round" />
                <path d="M12 15V7" stroke-linecap="round" />
                <path d="M16 15v-3" stroke-linecap="round" />
              </svg>
              学习时长趋势
            </h2>
            <span class="wb-card__hint">近 7 天全队 · {{ chartUnitLabel }}</span>
          </div>
          <div class="wb-chart" role="img" :aria-label="chartAria">
            <div class="wb-chart__y" aria-hidden="true">
              <span>{{ chartMaxLabel }}</span>
              <span>{{ chartMidLabel }}</span>
              <span>0</span>
            </div>
            <div class="wb-chart__bars">
              <div
                v-for="p in weeklyLearning"
                :key="p.date || p.label"
                class="wb-chart__col"
                :class="{ 'is-today': p.isToday, 'is-future': p.isFuture }"
                :title="barTooltip(p)"
              >
                <div class="wb-chart__bar-wrap">
                  <span class="wb-chart__val" :class="{ 'is-zero': !p.isFuture && Number(p.minutes || 0) <= 0 }">
                    {{ barValueLabel(p) }}
                  </span>
                  <i class="wb-chart__bar" :style="{ height: barHeight(p) }" />
                </div>
                <span class="wb-chart__x">{{ p.label }}</span>
              </div>
            </div>
          </div>
        </article>

        <article class="teacher-card wb-card">
          <div class="wb-card__head">
            <h2>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M12 3l2.2 4.6L19 8.3l-3.5 3.4.8 4.8L12 14.2 7.7 16.5l.8-4.8L5 8.3l4.8-.7L12 3z" stroke-linejoin="round" />
              </svg>
              进步之星
            </h2>
            <span class="wb-card__hint">按本周学习时长</span>
          </div>
          <ul v-if="progressStars.length" class="wb-people">
            <li
              v-for="(s, idx) in progressStars"
              :key="s.userId || idx"
              class="wb-person"
              :class="{ 'is-top': idx === 0 }"
            >
              <span class="wb-person__rank" :data-rank="idx + 1" aria-hidden="true">{{ idx + 1 }}</span>
              <span
                class="teacher-avatar wb-person__avatar"
                :style="{
                  width: '36px',
                  height: '36px',
                  fontSize: '14px',
                  background: avatarColor(s.userId || s.studentName),
                }"
                aria-hidden="true"
              >
                {{ initial(s.studentName) }}
              </span>
              <span class="wb-person__meta">
                <strong :title="s.studentName">{{ s.studentName }}</strong>
                <small>本周 {{ formatCompactDuration(s.thisWeekMinutes) }}</small>
              </span>
              <span
                class="wb-person__delta"
                :class="deltaClass(s.deltaMinutes)"
                :title="formatDeltaMinutes(s.deltaMinutes)"
              >
                {{ formatDeltaCompact(s.deltaMinutes) }}
              </span>
            </li>
          </ul>
          <div v-else class="wb-empty">本周暂无学习记录</div>
        </article>
      </section>

      <!-- ④ 关注 · 日志 · 评分 -->
      <section class="wb-bottom">
        <article class="teacher-card wb-card">
          <div class="wb-card__head">
            <h2>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M12 9v4" stroke-linecap="round" />
                <path d="M12 17h.01" stroke-linecap="round" />
                <path d="M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0z" stroke-linejoin="round" />
              </svg>
              需要关注
            </h2>
            <router-link
              v-if="attention.length"
              class="teacher-link"
              to="/camp/review-queue"
            >去处理</router-link>
          </div>
          <ul v-if="attention.length" class="wb-people">
            <li
              v-for="row in attention"
              :key="`${row.userId}-${row.level}`"
              class="wb-person wb-person--plain"
              :class="{ 'is-risk': row.level === 'critical' || row.level === 'watch' }"
            >
              <span
                class="teacher-avatar wb-person__avatar"
                :style="{
                  width: '36px',
                  height: '36px',
                  fontSize: '14px',
                  background: avatarColor(row.userId || row.studentName),
                }"
                aria-hidden="true"
              >
                {{ initial(row.studentName) }}
              </span>
              <span class="wb-person__meta">
                <strong :title="row.studentName">{{ row.studentName }}</strong>
                <small>{{ row.reason }}</small>
              </span>
              <span class="wb-chip" :data-level="normalizeLevel(row.level)">{{ row.tag || '关注' }}</span>
            </li>
          </ul>
          <div v-else class="wb-empty">暂无需要特别跟进的学生</div>
        </article>

        <article class="teacher-card wb-card">
          <div class="wb-card__head">
            <h2>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M8 7h8" stroke-linecap="round" />
                <path d="M8 12h8" stroke-linecap="round" />
                <path d="M8 17h5" stroke-linecap="round" />
                <rect x="4" y="3" width="16" height="18" rx="2" />
              </svg>
              训练日志
            </h2>
          </div>
          <ul v-if="trainingLog.length" class="wb-log">
            <li v-for="row in trainingLog" :key="row.date" class="wb-log__item">
              <span class="wb-log__time">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v5l3 2" stroke-linecap="round" />
                </svg>
                {{ row.label }}
              </span>
              <strong>{{ num(row.submitterCount) }} 人提交</strong>
            </li>
          </ul>
          <div v-else class="wb-empty">近几日暂无提交</div>
        </article>

        <article class="teacher-card wb-card">
          <div class="wb-card__head">
            <h2>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" stroke-linecap="round" />
              </svg>
              最新评分
            </h2>
            <router-link class="teacher-link" to="/review/reports">查看全部</router-link>
          </div>
          <ul v-if="latestScores.length" class="wb-people">
            <li v-for="row in latestScores" :key="row.reportId" class="wb-person wb-person--plain">
              <span
                class="teacher-avatar wb-person__avatar"
                :style="{
                  width: '36px',
                  height: '36px',
                  fontSize: '14px',
                  background: avatarColor(row.userId || row.studentName),
                }"
                aria-hidden="true"
              >
                {{ initial(row.studentName) }}
              </span>
              <span class="wb-person__meta">
                <strong :title="row.studentName">{{ row.studentName }}</strong>
                <small>
                  <template v-if="row.title">{{ shortTitle(row.title) }} · </template>
                  <template v-if="row.runCount > 1">{{ row.runCount }} 次复评</template>
                  <template v-else>第{{ row.attemptNo || 1 }}次</template>
                  <template v-if="row.relativeTime"> · {{ row.relativeTime }}</template>
                  <template v-if="row.hungDisplay"> · {{ row.hungDisplay }}</template>
                </small>
              </span>
              <span class="wb-score">
                <b>{{ formatScore(row.score) }}</b>
                <em v-if="row.grade && String(row.grade).length <= 2">{{ row.grade }}</em>
                <small v-if="Number(row.delta)" :class="Number(row.delta) > 0 ? 'is-up' : 'is-down'">
                  {{ Number(row.delta) > 0 ? '+' : '' }}{{ Math.round(Number(row.delta)) }}
                </small>
              </span>
            </li>
          </ul>
          <div v-else class="wb-empty">暂无已完成的 AI 评分报告</div>
        </article>
      </section>

      <p v-if="loading" class="wb-loading" aria-live="polite">正在加载首页数据…</p>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { fetchTeacherWorkbench } from '../api'
import { useTeacherContextStore } from '../stores/context'
import { getUser } from '../utils/auth'

const ctx = useTeacherContextStore()
const loading = ref(true)
const error = ref('')
const workbench = ref({})

const weeklyLearning = computed(() => workbench.value.weeklyLearning || [])
const progressStars = computed(() => workbench.value.progressStars || [])
const attention = computed(() => workbench.value.attention || [])
const trainingLog = computed(() => workbench.value.trainingLog || [])
const latestScores = computed(() => workbench.value.latestScores || [])
const camp = computed(() => workbench.value.camp || {})
const hasCamp = computed(() => Boolean(camp.value?.campId))

const teacherName = computed(() => {
  const fromApi = String(workbench.value.teacherName || '').trim()
  if (fromApi) return fromApi
  const u = getUser() || {}
  return String(u.username || u.name || '老师').trim() || '老师'
})

const statusEyebrow = computed(() => {
  if (!hasCamp.value) return '教学首页'
  const name = camp.value.teamName || camp.value.campName || ctx.projectName
  const day = camp.value.currentDay
  return day ? `${name} · 备赛第 ${day} 天` : String(name || '备赛中')
})

const greetingLine = computed(() => {
  const hour = new Date().getHours()
  const hi = hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好'
  return `${hi}，${teacherName.value}`
})

const statusSubline = computed(() => {
  const parts = []
  const online = workbench.value.onlineToday
  const pending = workbench.value.pendingReviews
  const missing = workbench.value.missingToday
  if (online != null) parts.push(`今日在线 ${online} 人`)
  if (pending != null && Number(pending) > 0) parts.push(`待批改 ${pending} 份`)
  if (missing != null && Number(missing) > 0) parts.push(`今日未交 ${missing} 人`)
  if (!parts.length) {
    return workbench.value.statusDetail || '队伍数据来自训练提交、学习时长与 AI 评分真实记录。'
  }
  return parts.join(' · ')
})

/** 纵轴单位：最大不足 2 小时用分钟，否则用小时 */
const useMinutesAxis = computed(() => {
  const maxMin = Math.max(0, ...weeklyLearning.value.map((p) => Number(p.minutes || 0)))
  return maxMin < 120
})
const chartUnitLabel = computed(() => (useMinutesAxis.value ? '单位：分钟' : '单位：小时'))
const chartMaxValue = computed(() => {
  if (useMinutesAxis.value) {
    const max = Math.max(0, ...weeklyLearning.value.map((p) => Number(p.minutes || 0)))
    return Math.max(30, Math.ceil(max / 30) * 30)
  }
  const max = Math.max(0, ...weeklyLearning.value.map((p) => Number(p.hours || 0)))
  return Math.max(1, Math.ceil(max))
})
const chartMaxLabel = computed(() =>
  useMinutesAxis.value ? `${chartMaxValue.value}分` : `${chartMaxValue.value}小时`
)
const chartMidLabel = computed(() => {
  const mid = Math.round(chartMaxValue.value / 2)
  return useMinutesAxis.value ? `${mid}分` : `${mid}小时`
})
const chartAria = computed(() => {
  const bits = weeklyLearning.value
    .filter((p) => !p.isFuture)
    .map((p) => `${p.label}${formatDuration(p.minutes)}`)
  return bits.length ? `近7天学习时长：${bits.join('，')}` : '近7天暂无学习时长'
})

const AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777', '#0e7490']

function num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

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

function normalizeLevel(level) {
  const lv = String(level || '').toLowerCase()
  if (lv === 'critical' || lv === 'danger' || lv === 'high') return 'critical'
  if (lv === 'good' || lv === 'ok' || lv === 'success') return 'good'
  return 'watch'
}

function barHeight(point) {
  if (point?.isFuture) return '0%'
  const value = useMinutesAxis.value ? Number(point?.minutes || 0) : Number(point?.hours || 0)
  if (value <= 0) return '0%'
  const max = Number(chartMaxValue.value || 1)
  return `${Math.min(100, Math.max(4, (value / max) * 100))}%`
}

/** 柱顶数值：一眼可读，不全靠纵轴估 */
function barValueLabel(p) {
  if (p?.isFuture) return '—'
  const minutes = Math.max(0, Math.round(Number(p?.minutes || 0)))
  if (minutes <= 0) return '0'
  if (useMinutesAxis.value) {
    if (minutes < 60) return `${minutes}分`
    return formatBarHours(minutes / 60)
  }
  const hours = Number(p?.hours)
  if (Number.isFinite(hours) && hours > 0) return formatBarHours(hours)
  return formatBarHours(minutes / 60)
}

function formatBarHours(hours) {
  const h = Math.max(0, Number(hours) || 0)
  if (h < 10) {
    // 一位小数更贴全队合计，如 4.2h / 18.5h
    const t = Math.round(h * 10) / 10
    return Number.isInteger(t) ? `${t}h` : `${t.toFixed(1)}h`
  }
  return `${Math.round(h)}h`
}

function barTooltip(p) {
  if (p?.isFuture) return `${p.label}（未到）`
  return `${p.label} ${formatDuration(p.minutes)}`
}

function formatDuration(minutes) {
  const m = Math.max(0, Math.round(Number(minutes || 0)))
  if (m < 60) return `${m} 分钟`
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest ? `${h} 小时 ${rest} 分` : `${h} 小时`
}

/** 紧凑中文时长：3小时 / 3.2小时 / 45分钟（不用 h/m 缩写） */
function formatCompactDuration(minutes) {
  const m = Math.max(0, Math.round(Number(minutes || 0)))
  if (m < 60) return `${m}分钟`
  const h = m / 60
  if (Math.abs(h - Math.round(h)) < 0.05) return `${Math.round(h)}小时`
  return `${h.toFixed(1)}小时`
}

function formatDeltaMinutes(min) {
  const n = Math.round(Number(min || 0))
  if (n > 0) return `较上周 +${formatDuration(n)}`
  if (n < 0) return `较上周 -${formatDuration(Math.abs(n))}`
  return '与上周持平'
}

function formatDeltaCompact(min) {
  const n = Math.round(Number(min || 0))
  if (n === 0) return '持平'
  const sign = n > 0 ? '+' : '−'
  return `${sign}${formatCompactDuration(Math.abs(n))}`
}

function deltaClass(min) {
  const n = Number(min || 0)
  if (n > 0) return 'is-up'
  if (n < 0) return 'is-down'
  return ''
}

function formatScore(score) {
  const n = Number(score)
  if (Number.isNaN(n)) return '—'
  return n % 1 === 0 ? String(n) : n.toFixed(1)
}

function shortTitle(title) {
  const s = String(title || '').trim()
  if (s.length <= 18) return s
  return `${s.slice(0, 18)}…`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const wb = await fetchTeacherWorkbench()
    workbench.value = wb || {}
    if (!ctx.campId && workbench.value.camp?.campId) {
      if (workbench.value.camp.teamId) ctx.setProject(String(workbench.value.camp.teamId))
      ctx.setCamp(String(workbench.value.camp.campId))
    }
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '首页数据加载失败'
    workbench.value = {}
  } finally {
    loading.value = false
  }
}

watch(() => [ctx.campId, ctx.projectId, ctx.loaded], load, { immediate: true })
</script>

<style scoped>
.plan-notice {
  margin: 0 0 14px;
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}
.workbench-empty {
  padding: 48px 24px;
  text-align: center;
}
.workbench-empty h2 {
  margin: 0 0 8px;
}
.workbench-empty p {
  margin: 0 0 18px;
  color: var(--ds-muted);
}
.wb-loading {
  margin: 12px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 650;
}

/* —— 状态栏（学生端 home-status 气质） —— */
.wb-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 4px 2px 8px;
  margin-bottom: 16px;
  background: transparent;
  border: 0;
}
.wb-status__identity {
  min-width: 0;
  flex: 1;
}
.wb-status__eyebrow {
  margin: 0 0 6px;
  color: var(--ds-muted, #71717a);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.02em;
}
.wb-status h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 750;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--ds-ink, #0a0a0a);
}
.wb-status__sub {
  margin: 8px 0 0;
  color: var(--ds-muted, #71717a);
  font-size: 13px;
  line-height: 1.5;
  max-width: 56ch;
}
.wb-status__metrics {
  display: flex;
  align-items: flex-start;
  gap: 28px;
  flex: 0 0 auto;
}
.wb-status__metric {
  text-align: right;
  min-width: 88px;
}
.wb-status__metric > span {
  display: block;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 650;
}
.wb-status__metric strong {
  display: block;
  margin-top: 2px;
  color: var(--ds-ink, #0a0a0a);
  font-size: 28px;
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1.05;
}
.wb-status__metric strong small {
  margin-left: 2px;
  font-size: 13px;
  font-weight: 700;
}
/* 日程：避免分数误读；数字大、「第/天」小 */
.wb-status__day {
  font-size: 22px !important;
  letter-spacing: -0.02em !important;
  white-space: nowrap;
}
.wb-status__day-num {
  font-size: 28px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  margin: 0 1px;
}
.wb-status__day-unit {
  font-size: 13px;
  font-weight: 700;
  color: var(--ds-muted, #71717a);
  letter-spacing: 0;
  vertical-align: 0.08em;
}
.wb-status__metric strong.is-empty {
  color: var(--ds-faint, #8b8b93);
}
.wb-status__metric p {
  margin: 4px 0 0;
  color: var(--ds-muted, #71717a);
  font-size: 11px;
  font-weight: 600;
}

/* —— 入口卡 —— */
.wb-entry {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.wb-entry__card {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--ds-card-border, #e4e4e7);
  border-radius: var(--ds-card-radius, 16px);
  background: var(--ds-card-bg, #fff);
  box-shadow: var(--ds-card-shadow, 0 1px 2px rgba(0, 0, 0, 0.04));
  text-decoration: none;
  color: inherit;
  transition: border-color 0.18s ease, box-shadow 0.2s ease;
}
.wb-entry__card:hover {
  border-color: rgba(29, 29, 31, 0.12);
  box-shadow: 0 8px 24px rgba(18, 20, 26, 0.06);
}
.wb-entry__icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep, #c2410c);
  background: var(--ds-orange-wash, #fff4ed);
}
.wb-entry__meta {
  min-width: 0;
  display: grid;
  gap: 4px;
}
.wb-entry__meta small {
  font-size: 12px;
  font-weight: 650;
  color: var(--ds-muted, #71717a);
}
.wb-entry__meta strong {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--ds-ink, #0a0a0a);
  line-height: 1.15;
}
.wb-entry__meta em {
  margin-left: 4px;
  font-style: normal;
  font-size: 13px;
  font-weight: 650;
  color: var(--ds-ink-2, #3f3f46);
}
.wb-entry__chev {
  width: 16px;
  height: 16px;
  color: var(--ds-faint, #a1a1aa);
}

.wb-mid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.9fr);
  gap: 12px;
  margin-bottom: 12px;
}
.wb-bottom {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.wb-card {
  overflow: hidden;
}
.wb-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  padding: 14px 18px 8px;
}
.wb-card__head h2 {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 800;
  color: var(--ds-ink, #0a0a0a);
  letter-spacing: -0.01em;
}
.wb-card__head h2 svg {
  color: var(--ds-muted, #71717a);
  flex: none;
}
.wb-card__hint {
  font-size: 12px;
  font-weight: 650;
  color: var(--ds-muted, #71717a);
}
.wb-empty {
  padding: 28px 18px 32px;
  text-align: center;
  color: var(--ds-muted, #71717a);
  font-size: 13px;
  font-weight: 600;
}

/* Chart */
.wb-chart {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 6px;
  padding: 4px 16px 16px;
  min-height: 240px;
}
.wb-chart__y {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 4px 0 28px;
  font-size: 11px;
  font-weight: 650;
  color: var(--ds-muted, #a1a1aa);
  text-align: right;
}
.wb-chart__bars {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  align-items: end;
  gap: 8px;
  min-height: 200px;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}
.wb-chart__col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  height: 100%;
  min-height: 0;
}
.wb-chart__bar-wrap {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-height: 160px;
}
.wb-chart__val {
  font-size: 11px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  color: var(--ds-text, #18181b);
  letter-spacing: -0.02em;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.wb-chart__val.is-zero {
  color: var(--ds-muted, #a1a1aa);
  font-weight: 650;
}
.wb-chart__col.is-today .wb-chart__val {
  color: #c2410c;
}
.wb-chart__bar {
  display: block;
  width: 42%;
  min-width: 14px;
  max-width: 28px;
  border-radius: 6px 6px 3px 3px;
  background: linear-gradient(180deg, rgba(255, 106, 56, 0.88) 0%, rgba(232, 74, 28, 0.45) 100%);
  transition: height 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}
.wb-chart__col.is-today .wb-chart__bar {
  background: linear-gradient(180deg, #ff6a38 0%, #e84312 100%);
}
.wb-chart__col.is-future .wb-chart__bar {
  background: rgba(207, 213, 222, 0.35);
}
.wb-chart__x {
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted, #71717a);
}

/* 人员行：排名/头像/文案/右侧动作，列数固定不拉长标签 */
.wb-people,
.wb-log {
  list-style: none;
  margin: 0;
  padding: 4px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.wb-person {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 12px;
  transition: background 0.15s ease;
}
.wb-person:hover {
  background: rgba(15, 23, 42, 0.03);
}
/* 无排名：头像 | 文案 | 右侧动作 */
.wb-person--plain {
  grid-template-columns: auto minmax(0, 1fr) auto;
}
.wb-person.is-top {
  background: #fff7ed;
}
.wb-person.is-top:hover {
  background: #ffedd5;
}
.wb-person.is-risk {
  background: transparent;
}
.wb-person__rank {
  width: 22px;
  height: 22px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  color: var(--ds-muted);
  background: #f4f4f5;
  flex: none;
}
.wb-person__rank[data-rank='1'] {
  color: #fff;
  background: linear-gradient(135deg, #f59e0b, #e84a1c);
}
.wb-person__rank[data-rank='2'] {
  color: #92400e;
  background: #fde68a;
}
.wb-person__rank[data-rank='3'] {
  color: #9a3412;
  background: #fed7aa;
}
.wb-person__avatar {
  flex: none;
}
.wb-person__meta {
  min-width: 0;
  display: grid;
  gap: 2px;
  overflow: hidden;
}
.wb-person__meta strong {
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wb-person__meta small {
  font-size: 12px;
  font-weight: 600;
  color: var(--ds-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.wb-person__delta {
  flex: none;
  justify-self: end;
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--ds-muted);
  text-align: right;
  white-space: nowrap;
  line-height: 1.2;
}
.wb-person__delta.is-up {
  color: #16a34a;
}
.wb-person__delta.is-down {
  color: #dc2626;
}

/* 紧凑状态胶囊，绝不被网格拉宽 */
.wb-chip {
  flex: none;
  justify-self: end;
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 750;
  line-height: 1;
  white-space: nowrap;
  max-width: 100%;
}
.wb-chip[data-level='critical'] {
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid rgba(185, 28, 28, 0.12);
}
.wb-chip[data-level='watch'] {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid rgba(180, 83, 9, 0.12);
}
.wb-chip[data-level='good'] {
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid rgba(21, 128, 61, 0.12);
}

.wb-log__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
  padding: 8px 4px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
}
.wb-log__item:last-child {
  border-bottom: 0;
}
.wb-log__time {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 650;
  color: var(--ds-ink-2, #3f3f46);
}
.wb-log__time svg {
  color: var(--ds-muted);
}
.wb-log__item strong {
  font-size: 13px;
  font-weight: 750;
}

.wb-score {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  flex: none;
  justify-self: end;
}
.wb-score b {
  font-size: 17px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--ds-ink);
}
.wb-score em {
  font-style: normal;
  font-size: 11px;
  font-weight: 800;
  color: #c2410c;
  background: #fff7ed;
  border-radius: 6px;
  padding: 2px 6px;
}
.wb-score small.is-up {
  color: #16a34a;
  font-weight: 800;
}
.wb-score small.is-down {
  color: #dc2626;
  font-weight: 800;
}

@media (max-width: 1100px) {
  .wb-mid,
  .wb-bottom {
    grid-template-columns: 1fr;
  }
  .wb-status {
    flex-direction: column;
    align-items: stretch;
  }
  .wb-status__metrics {
    justify-content: space-between;
  }
  .wb-status__metric {
    text-align: left;
  }
}
@media (max-width: 720px) {
  .wb-entry {
    grid-template-columns: 1fr;
  }
  .wb-status h1 {
    font-size: 20px;
  }
}
</style>
