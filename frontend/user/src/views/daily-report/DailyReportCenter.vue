<template>
  <div class="student-page drc">
    <header class="student-page__head">
      <div>
        <h1>日报中心</h1>
        <p>记录每天备赛推进，可回看历史、查看连续打卡与完成率。</p>
      </div>
      <div class="drc-head-actions">
        <router-link class="student-secondary-btn" to="/">返回首页</router-link>
        <router-link class="student-primary-btn" to="/daily-reports/write">
          {{ stats.todaySubmitted ? '修改今日日报' : '写今日日报' }}
        </router-link>
      </div>
    </header>

    <section v-if="loadError" class="student-card drc-error" role="alert">
      <strong>加载失败</strong>
      <p>{{ loadError }}</p>
      <button type="button" class="student-secondary-btn" @click="load">重试</button>
    </section>

    <template v-else>
      <section class="drc-stats" aria-label="日报统计">
        <article class="drc-stat">
          <span>连续打卡</span>
          <strong>{{ stats.streakDays ?? 0 }}</strong>
          <small>天</small>
        </article>
        <article class="drc-stat">
          <span>近 7 天</span>
          <strong>{{ stats.last7Submitted ?? 0 }}</strong>
          <small>/ 7 · {{ stats.last7Rate ?? 0 }}%</small>
        </article>
        <article class="drc-stat">
          <span>近 30 天</span>
          <strong>{{ stats.last30Submitted ?? 0 }}</strong>
          <small>/ 30 · {{ stats.last30Rate ?? 0 }}%</small>
        </article>
        <article class="drc-stat">
          <span>累计提交</span>
          <strong>{{ stats.totalSubmitted ?? 0 }}</strong>
          <small>篇</small>
        </article>
      </section>

      <section class="student-card drc-cal" aria-label="近 14 天打卡">
        <div class="drc-cal__head">
          <h2>近 14 天</h2>
          <span :class="stats.todaySubmitted ? 'is-ok' : 'is-todo'">
            {{ stats.todaySubmitted ? '今日已交' : '今日待交' }}
          </span>
        </div>
        <div class="drc-cal__grid">
          <button
            v-for="cell in calendar"
            :key="cell.date"
            type="button"
            class="drc-cal__cell"
            :class="{
              'is-on': cell.submitted,
              'is-today': cell.isToday,
              'is-miss': !cell.submitted && !cell.isToday,
            }"
            :title="cell.submitted ? cell.date : `${cell.date} · 点击补写`"
            @click="onCalendarClick(cell)"
          >
            <em>{{ dayLabel(cell.date) }}</em>
            <i aria-hidden="true" />
          </button>
        </div>
      </section>

      <section class="student-card drc-list" aria-label="历史日报">
        <div class="drc-list__head">
          <h2>历史日报</h2>
          <small>{{ loading ? '加载中…' : `${history.length} 条记录` }}</small>
        </div>

        <div v-if="loading" class="drc-skeleton">
          <span v-for="n in 4" :key="n" />
        </div>

        <div v-else-if="!history.length" class="drc-empty">
          <strong>还没有日报</strong>
          <p>从今天开始写第一篇，提交后会出现在这里。</p>
          <router-link class="student-primary-btn" to="/daily-reports/write">写今日日报</router-link>
        </div>

        <ul v-else class="drc-rows">
          <li v-for="item in history" :key="item.id">
            <button type="button" class="drc-row" @click="openDetail(item)">
              <div class="drc-row__date">
                <strong>{{ formatDate(item.reportDate) }}</strong>
                <small>{{ weekday(item.reportDate) }}</small>
              </div>
              <div class="drc-row__body">
                <p class="drc-row__preview">{{ item.preview || '（无摘要）' }}</p>
                <div class="drc-row__meta">
                  <span class="pill" :class="item.status === 'SUBMITTED' ? 'is-ok' : 'is-draft'">
                    {{ item.status === 'SUBMITTED' ? '已提交' : '草稿' }}
                  </span>
                  <span v-if="item.hasImages" class="pill is-img">含图</span>
                  <span v-if="item.contextType" class="pill is-ctx">{{ contextLabel(item.contextType) }}</span>
                </div>
              </div>
              <span class="drc-row__go">详情 →</span>
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchDailyReportHistory,
  fetchDailyReportStats,
} from '../../services/dailyReportClient'

const router = useRouter()
const loading = ref(true)
const loadError = ref('')
const stats = ref({})
const history = ref([])

const calendar = computed(() => Array.isArray(stats.value.calendar14) ? stats.value.calendar14 : [])

onMounted(load)

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [s, h] = await Promise.all([
      fetchDailyReportStats(),
      fetchDailyReportHistory(60),
    ])
    stats.value = s || {}
    history.value = Array.isArray(h) ? h : []
  } catch (e) {
    loadError.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function openDetail(item) {
  if (!item?.id) return
  router.push(`/daily-reports/${item.id}`)
}

function onCalendarClick(cell) {
  if (!cell?.date) return
  const hit = history.value.find((x) => String(x.reportDate).slice(0, 10) === cell.date)
  if (hit?.id) {
    router.push(`/daily-reports/${hit.id}`)
    return
  }
  if (cell.isToday) {
    router.push('/daily-reports/write')
    return
  }
  router.push({ path: '/daily-reports/write', query: { date: cell.date } })
}

function formatDate(d) {
  if (!d) return '—'
  const s = String(d).slice(0, 10)
  const [, m, day] = s.split('-')
  return `${Number(m)}月${Number(day)}日`
}

function weekday(d) {
  if (!d) return ''
  const dt = new Date(`${String(d).slice(0, 10)}T00:00:00`)
  return `周${['日', '一', '二', '三', '四', '五', '六'][dt.getDay()]}`
}

function dayLabel(d) {
  if (!d) return ''
  return String(Number(String(d).slice(8, 10)))
}

function contextLabel(t) {
  if (t === 'CAMP') return '集训'
  if (t === 'ROADSHOW') return '路演'
  return '备赛'
}
</script>

<style scoped>
.drc-head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.drc-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.drc-stat {
  border: 1px solid var(--ds-card-border);
  border-radius: 14px;
  background: var(--ds-card-bg, #fff);
  padding: 14px 16px;
  display: grid;
  gap: 4px;
}

.drc-stat span {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}

.drc-stat strong {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.drc-stat small {
  color: var(--ds-faint, #9ca3af);
  font-size: 12px;
}

.drc-cal {
  padding: 16px 18px 18px;
  margin-bottom: 16px;
}

.drc-cal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.drc-cal__head h2 {
  margin: 0;
  font-size: 16px;
}

.drc-cal__head span {
  font-size: 12px;
  font-weight: 750;
  padding: 4px 10px;
  border-radius: 999px;
}

.drc-cal__head span.is-ok {
  color: #047857;
  background: #d1fae5;
}

.drc-cal__head span.is-todo {
  color: #9a3412;
  background: #ffedd5;
}

.drc-cal__grid {
  display: grid;
  grid-template-columns: repeat(14, minmax(0, 1fr));
  gap: 6px;
}

.drc-cal__cell {
  border: 1px solid var(--ds-line, #e8eaee);
  border-radius: 10px;
  background: #f8fafc;
  padding: 8px 2px;
  display: grid;
  gap: 6px;
  place-items: center;
  cursor: pointer;
}

.drc-cal__cell em {
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}

.drc-cal__cell i {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #e5e7eb;
}

.drc-cal__cell.is-on {
  background: #fff7ed;
  border-color: #fdba74;
}

.drc-cal__cell.is-on i {
  background: var(--ds-orange-600, #ea580c);
}

.drc-cal__cell.is-today {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--ds-orange-500, #f97316) 35%, transparent);
}

.drc-cal__cell.is-miss i {
  background: #fde68a;
}

.drc-list {
  padding: 16px 18px 8px;
}

.drc-list__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}

.drc-list__head h2 {
  margin: 0;
  font-size: 16px;
}

.drc-list__head small {
  color: var(--ds-muted);
  font-size: 12px;
}

.drc-rows {
  list-style: none;
  margin: 0;
  padding: 0;
}

.drc-row {
  width: 100%;
  display: grid;
  grid-template-columns: 88px 1fr auto;
  gap: 14px;
  align-items: center;
  padding: 14px 4px;
  border: 0;
  border-bottom: 1px solid var(--ds-line, #eceff3);
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
}

.drc-row:hover {
  background: #fafbfc;
}

.drc-row__date strong {
  display: block;
  font-size: 14px;
}

.drc-row__date small {
  color: var(--ds-muted);
  font-size: 12px;
}

.drc-row__preview {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--ds-ink);
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.drc-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 750;
  background: #f3f4f6;
  color: var(--ds-ink-2);
}

.pill.is-ok {
  background: #d1fae5;
  color: #047857;
}

.pill.is-draft {
  background: #f3f4f6;
  color: #6b7280;
}

.pill.is-img {
  background: #e0e7ff;
  color: #3730a3;
}

.pill.is-ctx {
  background: #ffedd5;
  color: #9a3412;
}

.drc-row__go {
  color: var(--ds-orange-700, #c2410c);
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
}

.drc-empty {
  padding: 36px 16px;
  text-align: center;
  display: grid;
  gap: 8px;
  justify-items: center;
}

.drc-empty strong {
  font-size: 15px;
}

.drc-empty p {
  margin: 0 0 8px;
  color: var(--ds-muted);
  font-size: 13px;
}

.drc-skeleton {
  display: grid;
  gap: 10px;
  padding: 8px 0 16px;
}

.drc-skeleton span {
  height: 64px;
  border-radius: 10px;
  background: #f1f5f9;
  animation: pulse 1.2s ease-in-out infinite alternate;
}

.drc-error {
  padding: 24px;
  text-align: center;
}

@keyframes pulse {
  to { opacity: 0.55; }
}

@media (max-width: 900px) {
  .drc-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .drc-cal__grid {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }

  .drc-row {
    grid-template-columns: 72px 1fr;
  }

  .drc-row__go {
    display: none;
  }
}
</style>
