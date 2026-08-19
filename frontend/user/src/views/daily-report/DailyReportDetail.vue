<template>
  <div class="student-page drd">
    <header class="student-page__head">
      <div>
        <h1>日报详情</h1>
        <p v-if="report">{{ dateLabel }} · {{ statusLabel }} · {{ contextLabel }}</p>
      </div>
      <div class="drd-actions">
        <router-link class="student-secondary-btn" to="/daily-reports">日报中心</router-link>
        <router-link
          v-if="canEdit"
          class="student-primary-btn"
          :to="editPath"
        >
          {{ isToday ? '修改今日' : '编辑' }}
        </router-link>
      </div>
    </header>

    <section v-if="loading" class="student-card drd-card drd-muted">加载中…</section>
    <section v-else-if="error" class="student-card drd-card" role="alert">
      <strong>无法打开这篇日报</strong>
      <p>{{ error }}</p>
      <router-link class="student-secondary-btn" to="/daily-reports">返回列表</router-link>
    </section>
    <template v-else-if="report">
      <section class="student-card drd-card">
        <div class="drd-meta">
          <span class="pill" :class="report.status === 'SUBMITTED' ? 'is-ok' : 'is-draft'">
            {{ statusLabel }}
          </span>
          <span v-if="report.hasImages" class="pill is-img">含图</span>
          <span class="pill is-ctx">{{ contextLabel }}</span>
          <small v-if="report.submittedAt">提交于 {{ formatTime(report.submittedAt) }}</small>
          <small v-else-if="report.updatedAt">更新于 {{ formatTime(report.updatedAt) }}</small>
        </div>

        <article class="drd-block">
          <h2>今天做了什么</h2>
          <div class="drd-html" v-html="htmlDone" />
        </article>

        <article class="drd-block">
          <h2>卡点 / 需要帮助</h2>
          <div v-if="htmlBlocker" class="drd-html" v-html="htmlBlocker" />
          <p v-else class="drd-empty-field">未填写</p>
        </article>

        <article class="drd-block">
          <h2>明天计划</h2>
          <div class="drd-html" v-html="htmlNext" />
        </article>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchDailyReportDetail } from '../../services/dailyReportClient'
import { sanitizeDailyHtml, isHtmlEmpty } from '../../utils/dailyReportHtml'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const report = ref(null)

const htmlDone = computed(() => sanitizeDailyHtml(report.value?.contentDone || ''))
const htmlBlocker = computed(() => {
  const raw = report.value?.contentBlocker || ''
  if (isHtmlEmpty(raw)) return ''
  return sanitizeDailyHtml(raw)
})
const htmlNext = computed(() => sanitizeDailyHtml(report.value?.contentNext || ''))

const dateLabel = computed(() => {
  const d = report.value?.reportDate
  if (!d) return ''
  const dt = new Date(`${String(d).slice(0, 10)}T00:00:00`)
  const mm = String(dt.getMonth() + 1).padStart(2, '0')
  const dd = String(dt.getDate()).padStart(2, '0')
  const week = ['日', '一', '二', '三', '四', '五', '六'][dt.getDay()]
  return `${mm}月${dd}日 · 周${week}`
})

const statusLabel = computed(() => (
  report.value?.status === 'SUBMITTED' ? '已提交' : '草稿'
))

const contextLabel = computed(() => {
  const t = report.value?.contextType
  if (t === 'CAMP') return '集训'
  if (t === 'ROADSHOW') return '路演'
  return '备赛'
})

const isToday = computed(() => {
  const today = new Date()
  const y = today.getFullYear()
  const m = String(today.getMonth() + 1).padStart(2, '0')
  const d = String(today.getDate()).padStart(2, '0')
  return String(report.value?.reportDate || '').slice(0, 10) === `${y}-${m}-${d}`
})

const canEdit = computed(() => Boolean(report.value?.id))
const editPath = computed(() => (
  isToday.value
    ? '/daily-reports/write'
    : `/daily-reports/${report.value?.id}/edit`
))

onMounted(load)
watch(() => route.params.id, load)

async function load() {
  loading.value = true
  error.value = ''
  report.value = null
  try {
    report.value = await fetchDailyReportDetail(route.params.id)
  } catch (e) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function formatTime(v) {
  if (!v) return ''
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.drd-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.drd-card {
  padding: 18px 20px 22px;
  display: grid;
  gap: 18px;
}

.drd-muted {
  color: var(--ds-muted);
}

.drd-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.drd-meta small {
  color: var(--ds-muted);
  font-size: 12px;
}

.pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 750;
  background: #f3f4f6;
}

.pill.is-ok { background: #d1fae5; color: #047857; }
.pill.is-draft { color: #6b7280; }
.pill.is-img { background: #e0e7ff; color: #3730a3; }
.pill.is-ctx { background: #ffedd5; color: #9a3412; }

.drd-block h2 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 750;
  color: var(--ds-ink-2);
}

.drd-html {
  font-size: 14px;
  line-height: 1.7;
  color: var(--ds-ink);
  word-break: break-word;
}

.drd-html :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 12px;
  margin: 8px 0;
  display: block;
}

.drd-html :deep(ul),
.drd-html :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.4em;
}

.drd-html :deep(a) {
  color: var(--ds-orange-700, #c2410c);
}

.drd-empty-field {
  margin: 0;
  color: var(--ds-faint, #9ca3af);
  font-size: 13px;
}
</style>
