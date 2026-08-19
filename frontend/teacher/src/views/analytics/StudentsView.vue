<template>
  <div class="teacher-page students-page">
    <header class="teacher-page__head">
      <div>
        <h1>学生档案</h1>
        <p>
          先看谁需要关注，再点进详情做辅导
          <span v-if="camp.campName" class="teacher-muted"> · {{ camp.campName }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          刷新
        </button>
        <router-link class="teacher-btn teacher-btn--secondary" to="/analytics">学情总览</router-link>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>

    <!-- 筛选：沿用 workspace-tabs 分段样式 -->
    <nav v-if="!loading && rows.length" class="workspace-tabs students-filter-tabs" aria-label="学生筛选">
      <button
        type="button"
        :class="{ 'is-active': filterKey === 'all' }"
        @click="filterKey = 'all'"
      >
        全部 {{ rows.length }}
      </button>
      <button
        type="button"
        :class="{ 'is-active': filterKey === 'attention' }"
        @click="filterKey = 'attention'"
      >
        需关注 {{ attentionCount }}
      </button>
      <button
        type="button"
        :class="{ 'is-active': filterKey === 'missing' }"
        @click="filterKey = 'missing'"
      >
        有缺交 {{ missingCount }}
      </button>
      <button
        type="button"
        :class="{ 'is-active': filterKey === 'pending' }"
        @click="filterKey = 'pending'"
      >
        有待批 {{ pendingCount }}
      </button>
      <button
        type="button"
        :class="{ 'is-active': filterKey === 'ok' }"
        @click="filterKey = 'ok'"
      >
        状态平稳 {{ okCount }}
      </button>
    </nav>

    <div class="toolbar">
      <input
        v-model="keyword"
        type="search"
        class="toolbar__search"
        placeholder="搜索姓名、岗位、项目、标签"
        autocomplete="off"
      />
      <nav class="workspace-tabs students-sort-tabs" aria-label="排序方式">
        <button
          v-for="opt in sortOptions"
          :key="opt.value"
          type="button"
          :class="{ 'is-active': sortKey === opt.value }"
          @click="sortKey = opt.value"
        >
          {{ opt.label }}
        </button>
      </nav>
    </div>

    <div v-if="loading" class="teacher-empty">正在加载学生档案…</div>

    <section v-else-if="filtered.length" class="student-grid">
      <article
        v-for="m in filtered"
        :key="m.userId"
        class="student-card"
        role="button"
        tabindex="0"
        @click="openProfile(m.userId)"
        @keydown.enter="openProfile(m.userId)"
      >
        <header class="student-card__head">
          <span
            class="teacher-avatar"
            :style="{
              width: '44px',
              height: '44px',
              fontSize: '16px',
              background: avatarColor(m.userId || m.studentName),
            }"
          >
            {{ initial(m.studentName) }}
          </span>
          <div class="student-card__who">
            <div class="student-card__name-row">
              <strong>{{ m.studentName }}</strong>
              <span v-if="statusTag(m)" class="teacher-tag" :class="statusTag(m).cls">
                {{ statusTag(m).label }}
              </span>
            </div>
            <small>
              {{ m.positionName || '未分配岗位' }}
              <template v-if="m.teamName"> · {{ m.teamName }}</template>
            </small>
          </div>
          <button
            type="button"
            class="teacher-btn teacher-btn--secondary teacher-btn--sm"
            @click.stop="openProfile(m.userId)"
          >
            查看
          </button>
        </header>

        <p class="student-card__one">{{ oneLiner(m) }}</p>

        <div v-if="displayTags(m).length" class="tag-row">
          <span
            v-for="t in displayTags(m)"
            :key="t"
            class="teacher-tag"
            :class="tagClass(t)"
          >
            {{ t }}
          </span>
        </div>

        <div class="metric-row">
          <div>
            <small>训练提交</small>
            <strong :class="{ 'is-warn': (m.missingDays || 0) > 0 }">{{ rateText(m) }}</strong>
            <em>
              <template v-if="m.dueDays">{{ m.submittedDays || 0 }}/{{ m.dueDays }} 天</template>
              <template v-else>暂无应训</template>
            </em>
          </div>
          <div>
            <small>学习投入</small>
            <strong>{{ formatDuration(m.studySeconds) }}</strong>
            <em>本周 {{ formatDuration(m.weekStudySeconds) }}</em>
          </div>
          <div>
            <small>路演</small>
            <strong>{{ scoreText(m.latestScore) }}</strong>
            <em>{{ m.scoreCount ? `${m.scoreCount} 次` : '未评分' }}</em>
          </div>
          <div>
            <small>你要处理</small>
            <strong :class="{ 'is-warn': todoCount(m) > 0 }">{{ todoCount(m) }}</strong>
            <em>待批 + 整改</em>
          </div>
        </div>
      </article>
    </section>

    <div v-else class="teacher-empty students-empty">
      <p>{{ emptyText }}</p>
      <button
        v-if="filterKey !== 'all' || keyword"
        type="button"
        class="teacher-btn teacher-btn--secondary"
        @click="resetFilters"
      >
        查看全部学生
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchTeacherStudents } from '../../api'
import { useTeacherContextStore } from '../../stores/context'

const sortOptions = [
  { value: 'risk', label: '风险优先' },
  { value: 'missing', label: '缺交' },
  { value: 'study', label: '学习时长' },
  { value: 'score', label: '路演分' },
  { value: 'name', label: '姓名' },
]

const AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777', '#0e7490']

const ctx = useTeacherContextStore()
const router = useRouter()
const loading = ref(true)
const error = ref('')
const keyword = ref('')
const sortKey = ref('risk')
const filterKey = ref('attention')
const camp = ref({})
const rows = ref([])

const attentionCount = computed(
  () => rows.value.filter((m) => isAttention(m)).length
)
const missingCount = computed(() => rows.value.filter((m) => (m.missingDays || 0) > 0).length)
const pendingCount = computed(
  () => rows.value.filter((m) => (m.pendingReviews || 0) + (m.openRemediations || 0) > 0).length
)
const okCount = computed(() => rows.value.filter((m) => !isAttention(m)).length)

const filtered = computed(() => {
  const q = keyword.value.toLowerCase().trim()
  let list = rows.value.slice()

  if (filterKey.value === 'attention') list = list.filter(isAttention)
  else if (filterKey.value === 'missing') list = list.filter((m) => (m.missingDays || 0) > 0)
  else if (filterKey.value === 'pending') {
    list = list.filter((m) => (m.pendingReviews || 0) + (m.openRemediations || 0) > 0)
  } else if (filterKey.value === 'ok') list = list.filter((m) => !isAttention(m))

  if (q) {
    list = list.filter((m) =>
      `${m.studentName} ${m.positionName || ''} ${m.teamName || ''} ${(m.riskTags || []).join(' ')}`
        .toLowerCase()
        .includes(q)
    )
  }

  list.sort((a, b) => {
    if (sortKey.value === 'missing') return (b.missingDays || 0) - (a.missingDays || 0)
    if (sortKey.value === 'study') return (b.studySeconds || 0) - (a.studySeconds || 0)
    if (sortKey.value === 'score') {
      const as = a.latestScore == null ? -1 : Number(a.latestScore)
      const bs = b.latestScore == null ? -1 : Number(b.latestScore)
      return bs - as
    }
    if (sortKey.value === 'name') {
      return String(a.studentName || '').localeCompare(String(b.studentName || ''), 'zh')
    }
    return riskWeight(b) - riskWeight(a)
  })
  return list
})

const emptyText = computed(() => {
  if (keyword.value) return '没有匹配的学生'
  if (filterKey.value === 'attention') return '当前没有需要重点关注的学生'
  if (filterKey.value === 'missing') return '当前没有缺交学生'
  if (filterKey.value === 'pending') return '没有待你处理的批改/整改'
  if (filterKey.value === 'ok') return '没有状态平稳的学生（可能都在关注列表）'
  return '当前范围内暂无学生数据'
})

function isAttention(m) {
  return (
    (m.missingDays || 0) > 0 ||
    (m.pendingReviews || 0) > 0 ||
    (m.openRemediations || 0) > 0 ||
    (m.riskTags || []).length > 0
  )
}

function riskWeight(m) {
  return (
    (m.riskTags || []).length * 10 +
    (m.missingDays || 0) * 4 +
    (m.pendingReviews || 0) * 3 +
    (m.openRemediations || 0) * 2
  )
}

function todoCount(m) {
  return (m.pendingReviews || 0) + (m.openRemediations || 0)
}

function oneLiner(m) {
  if ((m.missingDays || 0) >= 2) return `已连续缺交 ${m.missingDays} 天，建议今天催交或约谈`
  if ((m.missingDays || 0) === 1) return '有 1 天缺交，留意是否掉队'
  if ((m.pendingReviews || 0) > 0) return `有 ${m.pendingReviews} 份提交等你批改`
  if ((m.openRemediations || 0) > 0) return `有 ${m.openRemediations} 条整改进行中`
  if ((m.riskTags || []).includes('学习时长偏低')) return '学习投入偏低，可抽查学习记录'
  if ((m.riskTags || []).includes('未路演评分')) return '还没有路演评分记录'
  if (m.dueDays && m.submissionRate >= 90) return '提交稳定，可重点看质量与路演'
  if (!m.dueDays) return '暂无应训日数据，发布训练后会更新'
  return '状态平稳，可按需查看详情'
}

function statusTag(m) {
  if ((m.missingDays || 0) >= 2) return { label: '重点关注', cls: 'is-danger' }
  if ((m.missingDays || 0) === 1) return { label: '有缺交', cls: 'is-warn' }
  if ((m.pendingReviews || 0) > 0) return { label: '待批改', cls: 'is-warn' }
  if ((m.openRemediations || 0) > 0) return { label: '整改中', cls: 'is-warn' }
  if ((m.riskTags || []).length) return { label: '留意', cls: 'is-info' }
  return { label: '平稳', cls: 'is-ok' }
}

function displayTags(m) {
  const tags = Array.isArray(m.riskTags) ? m.riskTags.slice(0, 3) : []
  return tags
}

function tagClass(t) {
  if (/缺交|待批|整改/.test(t)) return 'is-danger'
  if (/偏低|未路演/.test(t)) return 'is-warn'
  return 'is-info'
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

function rateText(m) {
  if (m.submissionRate == null || !m.dueDays) return '—'
  return `${m.submissionRate}%`
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

function openProfile(id) {
  router.push(`/analytics/students/${id}?from=students`)
}

function resetFilters() {
  filterKey.value = 'all'
  keyword.value = ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchTeacherStudents()
    camp.value = data?.camp || {}
    rows.value = Array.isArray(data?.students) ? data.students : []
    // 若没有需关注的，默认看全部，避免空列表挫败感
    if (filterKey.value === 'attention' && !rows.value.some(isAttention) && rows.value.length) {
      filterKey.value = 'all'
    }
  } catch (err) {
    error.value = err?.message || '学生档案加载失败'
    rows.value = []
    camp.value = {}
  } finally {
    loading.value = false
  }
}

watch(() => [ctx.projectId, ctx.campId, ctx.loaded], load, { immediate: true })
</script>

<style scoped>
.teacher-muted {
  color: var(--ds-muted);
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

.students-filter-tabs {
  margin-bottom: 12px;
}
.students-sort-tabs {
  flex-shrink: 0;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
}
.toolbar__search {
  flex: 1;
  min-width: 220px;
  max-width: 360px;
  box-sizing: border-box;
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--ds-line-strong, #d4d4d8);
  border-radius: 999px;
  background: #fff;
  font: inherit;
  font-size: 13px;
  color: var(--ds-ink);
  outline: none;
  transition: border-color 0.15s ease;
}
.toolbar__search::placeholder {
  color: var(--ds-muted);
}
.toolbar__search:focus {
  border-color: var(--ds-orange);
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.12);
}

.students-empty {
  display: grid;
  gap: 12px;
  justify-items: center;
}
.students-empty p {
  margin: 0;
}

.student-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.student-card {
  padding: 16px 16px 14px;
  border: 1px solid var(--ds-line);
  border-radius: 16px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
}
.student-card:hover {
  border-color: rgba(232, 74, 28, 0.32);
  box-shadow: 0 10px 28px rgba(18, 20, 26, 0.06);
  transform: translateY(-1px);
}
.student-card:focus-visible {
  outline: 2px solid var(--ds-orange);
  outline-offset: 2px;
}

.student-card__head {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}
.student-card__who {
  min-width: 0;
}
.student-card__name-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.student-card__name-row strong {
  font-size: 15px;
  font-weight: 800;
}
.student-card__who small {
  display: block;
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.student-card__one {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fafbfc;
  border: 1px solid var(--ds-line);
  font-size: 12px;
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

.metric-row {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.metric-row > div {
  padding: 8px 10px;
  border-radius: 10px;
  background: #f7f8f9;
  border: 1px solid var(--ds-line);
  display: grid;
  gap: 2px;
  min-width: 0;
}
.metric-row small {
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}
.metric-row strong {
  font-size: 15px;
  font-weight: 800;
  color: var(--ds-ink);
  font-variant-numeric: tabular-nums;
}
.metric-row strong.is-warn {
  color: var(--ds-orange-deep);
}
.metric-row em {
  font-style: normal;
  font-size: 10px;
  color: var(--ds-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .student-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .metric-row {
    grid-template-columns: 1fr 1fr;
  }
  .toolbar__search {
    max-width: none;
  }
}
</style>
