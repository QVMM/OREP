<template>
  <div class="teacher-page review-reports-page">
    <header class="teacher-page__head">
      <div>
        <h1>评分报告</h1>
        <p>
          {{
            activeTab === 'upload'
              ? '上传完整路演视频发起 AI 评分，任务进度与学生端一致'
              : '查看 AI / 手工评分；正式结果需老师确认后进入学生端'
          }}
          <span v-if="activeTab === 'list' && sourceLabel" class="teacher-muted"> · {{ sourceLabel }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button
          v-if="activeTab === 'list'"
          type="button"
          class="teacher-btn teacher-btn--secondary"
          :disabled="loading"
          @click="load"
        >
          刷新
        </button>
      </div>
    </header>

    <div class="reports-tabs" role="tablist" aria-label="评分报告分区">
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'list'"
        :class="{ 'is-active': activeTab === 'list' }"
        @click="setTab('list')"
      >
        报告列表
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'upload'"
        :class="{ 'is-active': activeTab === 'upload' }"
        @click="setTab('upload')"
      >
        上传评分
      </button>
    </div>

    <p v-if="error && activeTab === 'list'" class="teacher-tag is-warn" style="margin-bottom: 12px">{{ error }}</p>

    <!-- 报告列表 -->
    <section v-if="activeTab === 'list'" class="teacher-card">
      <div class="teacher-card__body" style="padding-top: 8px">
        <div v-if="loading" class="teacher-empty">加载报告…</div>
        <table v-else class="teacher-table">
          <thead>
            <tr>
              <th>报告</th>
              <th>关联</th>
              <th>总分</th>
              <th>时间</th>
              <th>状态</th>
              <th>任务书</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reports" :key="r.key">
              <td>
                {{ r.title }}
                <span v-if="r.runCount > 1" class="teacher-muted"> · {{ r.runCount }} 次复评</span>
              </td>
              <td>{{ r.ref }}</td>
              <td><strong style="color: var(--ds-orange)">{{ r.score ?? '—' }}</strong></td>
              <td>{{ r.at }}</td>
              <td>
                <span class="teacher-tag" :class="r.teacherConfirmed ? 'is-ok' : 'is-warn'">
                  {{ r.teacherConfirmed ? '已确认' : '待确认' }}
                </span>
              </td>
              <td>
                <span class="teacher-tag" :class="r.taskBookPublished ? 'is-ok' : 'is-warn'">
                  {{ r.taskBookPublished ? (r.hungDisplay ? `已发布 · ${r.hungDisplay}` : '已发布') : '未发布' }}
                </span>
              </td>
              <td>
                <button
                  v-if="r.sessionId && !r.teacherConfirmed"
                  type="button"
                  class="teacher-btn teacher-btn--primary teacher-btn--sm"
                  :disabled="confirmingId === r.sessionId"
                  @click="confirmSession(r)"
                >
                  {{ confirmingId === r.sessionId ? '确认中…' : '确认本场' }}
                </button>
                <button
                  v-if="r.sessionId && !r.taskBookPublished"
                  type="button"
                  class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                  :disabled="publishingId === r.sessionId"
                  @click="publishBook(r)"
                >
                  {{ publishingId === r.sessionId ? '发布中…' : '发布任务书' }}
                </button>
                <a
                  v-if="r.href"
                  class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                  :href="r.href"
                  target="_blank"
                  rel="noopener"
                >打开</a>
                <button v-else type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" disabled>
                  打开
                </button>
              </td>
            </tr>
            <tr v-if="!reports.length">
              <td colspan="7" class="teacher-empty">
                暂无报告。可切换到「上传评分」提交路演视频。
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 上传评分（嵌入子页） -->
    <section v-else class="teacher-card reports-upload-card">
      <div class="teacher-card__body">
        <VideoScoreUploadView embedded />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAiReportSummary, publishAiScoreTaskBook, confirmAiScoreSession } from '../../api'
import { studentAiReportUrl } from '../../utils/studentApp'
import VideoScoreUploadView from './VideoScoreUploadView.vue'

const route = useRoute()
const router = useRouter()

const reports = ref([])
const loading = ref(false)
const error = ref('')
const sourceLabel = ref('')
const publishingId = ref(null)
const confirmingId = ref(null)
const activeTab = ref(normalizeTab(route.query.tab))

function normalizeTab(tab) {
  return String(tab || '') === 'upload' ? 'upload' : 'list'
}

function setTab(tab) {
  activeTab.value = tab
  const query = tab === 'upload' ? { tab: 'upload' } : {}
  router.replace({ path: '/review/reports', query })
}

function pickScore(item) {
  return item.totalScore ?? item.score ?? item.finalScore ?? item.overallScore ?? null
}

function pickHref(item) {
  return studentAiReportUrl({
    reportId: item.reportId,
    sessionId: item.sessionId,
    meetingId: item.meetingId,
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchAiReportSummary()
    const rows = Array.isArray(data)
      ? data
      : data?.reports || data?.list || data?.items || data?.records || []
    if (!rows.length) {
      reports.value = []
      sourceLabel.value = '尚无真实评分报告'
      return
    }
    reports.value = rows.map((item, idx) => ({
      key: String(item.reportId || item.sessionId || item.meetingId || idx),
      title: item.title || item.meetingTitle || `报告 ${item.reportId || item.sessionId || idx + 1}`,
      ref: item.teamName || item.projectName || item.meetingId || '—',
      score: pickScore(item),
      at: String(item.createdAt || item.finishedAt || item.updatedAt || '—').replace('T', ' ').slice(0, 16),
      status: item.confirmed || item.teacherConfirmed || item.status === 'CONFIRMED' ? '已确认' : '待确认',
      teacherConfirmed: item.teacherConfirmed === true || item.confirmed === true || item.teacher_confirmed === true,
      taskBookPublished: item.taskBookPublished === true || item.taskBookPublished === 1 || item.task_book_published === true,
      hungDisplay: item.hungDisplay || item.hung_display || '',
      sessionId: item.sessionId || item.session_id || null,
      runCount: Number(item.runCount || item.run_count || 1),
      href: pickHref(item),
    }))
    sourceLabel.value = '已连接 /api/ai-score/reports/summary'
  } catch (e) {
    error.value = e.message
    reports.value = []
    sourceLabel.value = '评分报告加载失败'
  } finally {
    loading.value = false
  }
}

async function confirmSession(row) {
  if (!row?.sessionId) return
  confirmingId.value = row.sessionId
  error.value = ''
  try {
    await confirmAiScoreSession(row.sessionId)
    row.teacherConfirmed = true
    row.status = '已确认'
  } catch (e) {
    error.value = e.message || '确认失败'
  } finally {
    confirmingId.value = null
  }
}

async function publishBook(row) {
  if (!row?.sessionId) return
  publishingId.value = row.sessionId
  error.value = ''
  try {
    await publishAiScoreTaskBook(row.sessionId)
    row.taskBookPublished = true
  } catch (e) {
    error.value = e.message || '任务书发布失败'
  } finally {
    publishingId.value = null
  }
}

watch(
  () => route.query.tab,
  (tab) => {
    activeTab.value = normalizeTab(tab)
  }
)

onMounted(load)
</script>

<style scoped>
.reports-tabs {
  display: inline-flex;
  gap: 4px;
  margin: 0 0 16px;
  padding: 4px;
  border-radius: 12px;
  background: #f3f4f6;
}

.reports-tabs button {
  height: 34px;
  padding: 0 16px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--ds-ink-2);
  font: 700 13px var(--ds-font-sans);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.reports-tabs button.is-active {
  background: #fff;
  color: var(--ds-orange-deep);
  box-shadow: 0 1px 4px rgba(29, 29, 31, 0.08);
}

.reports-upload-card .teacher-card__body {
  padding-top: 12px;
}
</style>
