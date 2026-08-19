<template>
  <div class="student-page drw">
    <header class="student-page__head">
      <div>
        <h1>{{ pageTitle }}</h1>
        <p>{{ dateLabel }} · {{ contextHint }} · 支持文字与图片</p>
      </div>
      <div class="drw-actions">
        <router-link class="student-secondary-btn" to="/daily-reports">日报中心</router-link>
        <button type="button" class="student-secondary-btn" :disabled="saving" @click="saveDraft">存草稿</button>
        <button type="button" class="student-primary-btn" :disabled="saving" @click="submit">
          {{ saving ? '提交中…' : '提交日报' }}
        </button>
      </div>
    </header>

    <section v-if="loading" class="student-card drw-card drw-muted">加载中…</section>
    <section v-else class="student-card drw-card">
      <p v-if="status === 'SUBMITTED'" class="drw-banner is-ok">本篇已提交，修改后再次提交即可覆盖更新。</p>
      <p v-else-if="!isToday" class="drw-banner">正在补写 {{ dateLabel }} 的日报，提交后会计入当天打卡。</p>
      <p v-else class="drw-banner">写清今天做了什么、明天计划；可插入截图/配图，提交后红点会消失。</p>

      <label class="drw-field">
        <span>今天做了什么 <em>必填</em></span>
        <RichTextEditor
          v-model="form.contentDone"
          :placeholder="placeholderDone"
          label="今天做了什么"
        />
      </label>

      <label class="drw-field">
        <span>卡点 / 需要帮助 <em class="opt">选填</em></span>
        <RichTextEditor
          v-model="form.contentBlocker"
          placeholder="没有就写「无」或留空；可附图说明卡点"
          label="卡点 / 需要帮助"
        />
      </label>

      <label class="drw-field">
        <span>明天计划 <em>必填</em></span>
        <RichTextEditor
          v-model="form.contentNext"
          :placeholder="placeholderNext"
          label="明天计划"
        />
      </label>

      <p v-if="error" class="drw-error" role="alert">{{ error }}</p>

      <footer class="drw-footer">
        <button type="button" class="student-secondary-btn" :disabled="saving" @click="saveDraft">存草稿</button>
        <button type="button" class="student-primary-btn" :disabled="saving" @click="submit">
          {{ saving ? '提交中…' : '提交日报' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RichTextEditor from '../../components/daily-report/RichTextEditor.vue'
import {
  fetchDailyReportDetail,
  fetchDailyReportForDate,
  fetchDailyReportToday,
  saveDailyReport,
} from '../../services/dailyReportClient'
import { isHtmlEmpty } from '../../utils/dailyReportHtml'
import { useCollaborationStore } from '../../stores/collaboration'

const route = useRoute()
const router = useRouter()
const collab = useCollaborationStore()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const status = ref('DRAFT')
const contextType = ref('FREE')
const reportDate = ref('')
const reportId = ref(null)

const form = reactive({
  contentDone: '',
  contentBlocker: '',
  contentNext: '',
})

const isToday = computed(() => {
  const today = new Date()
  const y = today.getFullYear()
  const m = String(today.getMonth() + 1).padStart(2, '0')
  const d = String(today.getDate()).padStart(2, '0')
  return reportDate.value === `${y}-${m}-${d}`
})

const pageTitle = computed(() => {
  if (isToday.value) return '写今日日报'
  return reportDate.value ? '补写日报' : '编辑日报'
})

const dateLabel = computed(() => {
  const d = reportDate.value ? new Date(`${reportDate.value}T00:00:00`) : new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${mm}月${dd}日 · 周${week}`
})

const contextHint = computed(() => {
  if (contextType.value === 'CAMP') return '结合今日训练与备赛进展'
  if (contextType.value === 'ROADSHOW') return '可写路演练习、改稿、演示情况'
  return '记录今天的备赛推进即可'
})

const placeholderDone = computed(() => {
  if (contextType.value === 'ROADSHOW') return '例如：路演练了 3 遍，改了开场与第 2 页数据…可附图'
  if (contextType.value === 'CAMP') return '例如：完成第 N 天训练任务，看完材料并提交成果…'
  return '用几句话写下今天做了什么，可插入图片'
})

const placeholderNext = computed(() => {
  if (contextType.value === 'ROADSHOW') return '例如：明天精修讲稿后半段，再完整彩排一次'
  return '明天最想推进的一件事'
})

onMounted(load)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id
    const queryDate = String(route.query.date || '').slice(0, 10)
    // /daily-reports/:id/edit 走详情编辑；/daily-reports/write?date= 补某一天
    if (id && /^\d+$/.test(String(id))) {
      const r = await fetchDailyReportDetail(id)
      applyReport(r)
      reportDate.value = String(r?.reportDate || '').slice(0, 10)
      contextType.value = r?.contextType || 'FREE'
    } else if (/^\d{4}-\d{2}-\d{2}$/.test(queryDate)) {
      const data = await fetchDailyReportForDate(queryDate)
      reportDate.value = data?.reportDate || queryDate
      contextType.value = data?.contextType || 'FREE'
      applyReport(data?.report)
    } else {
      const data = await fetchDailyReportToday()
      reportDate.value = data?.reportDate || new Date().toISOString().slice(0, 10)
      contextType.value = data?.contextType || 'FREE'
      applyReport(data?.report)
    }
  } catch (e) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function applyReport(r) {
  if (!r) {
    form.contentDone = ''
    form.contentBlocker = ''
    form.contentNext = ''
    status.value = 'DRAFT'
    reportId.value = null
    return
  }
  form.contentDone = r.contentDone || ''
  form.contentBlocker = r.contentBlocker || ''
  form.contentNext = r.contentNext || ''
  status.value = r.status || 'DRAFT'
  reportId.value = r.id || null
}

async function saveDraft() {
  await persist(false)
}

async function submit() {
  await persist(true)
}

async function persist(submitFlag) {
  error.value = ''
  if (submitFlag) {
    if (isHtmlEmpty(form.contentDone)) {
      error.value = '请填写「今天做了什么」'
      return
    }
    if (isHtmlEmpty(form.contentNext)) {
      error.value = '请填写「明天计划」'
      return
    }
  }
  saving.value = true
  try {
    const saved = await saveDailyReport({
      reportDate: reportDate.value,
      contentDone: form.contentDone,
      contentBlocker: form.contentBlocker,
      contentNext: form.contentNext,
      submit: submitFlag,
    })
    status.value = saved?.status || (submitFlag ? 'SUBMITTED' : 'DRAFT')
    reportId.value = saved?.id || reportId.value
    collab.loadTodayBundle?.({ force: true })?.catch?.(() => {})
    collab.loadSummary?.()?.catch?.(() => {})
    if (submitFlag && saved?.id) {
      router.replace(`/daily-reports/${saved.id}`)
    }
  } catch (e) {
    error.value = e?.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.drw-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.drw-card {
  padding: 18px 20px 20px;
  display: grid;
  gap: 16px;
}

.drw-muted {
  color: var(--ds-muted);
  font-size: 13px;
}

.drw-banner {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.5;
}

.drw-banner.is-ok {
  background: #ecfdf5;
  color: #047857;
}

.drw-field {
  display: grid;
  gap: 8px;
}

.drw-field > span {
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink-2);
}

.drw-field em {
  margin-left: 4px;
  color: var(--ds-orange-700, #c2410c);
  font-style: normal;
  font-weight: 650;
}

.drw-field em.opt {
  color: var(--ds-muted);
  font-weight: 600;
}

.drw-error {
  margin: 0;
  color: #b91c1c;
  font-size: 13px;
}

.drw-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 4px;
}

@media (max-width: 720px) {
  .drw-actions .student-secondary-btn:first-child {
    display: none;
  }
}
</style>
