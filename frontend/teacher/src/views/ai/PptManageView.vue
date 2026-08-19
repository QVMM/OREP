<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>PPT 管理</h1>
        <p>查看学生端 AI 生成的 PPT 任务（按你可访问的团队成员过滤）。</p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          刷新
        </button>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error">{{ error }}</p>

    <section class="teacher-card">
      <div class="teacher-card__body">
        <div class="manager-toolbar">
          <div class="manager-toolbar__title">
            <strong>学生 AI PPT</strong>
            <span>{{ filtered.length }} / {{ list.length }} 份</span>
          </div>
          <div class="manager-toolbar__tools">
            <input
              v-model.trim="keyword"
              type="search"
              placeholder="搜学生 / 项目名"
            />
            <select v-model="status">
              <option value="all">全部状态</option>
              <option value="completed">已完成</option>
              <option value="generating">生成中</option>
              <option value="outline_ready">大纲就绪</option>
              <option value="failed">失败</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="teacher-empty">正在加载…</div>
        <div v-else class="teacher-table-wrap">
          <table class="teacher-table">
            <thead>
              <tr>
                <th>项目</th>
                <th>学生</th>
                <th>团队</th>
                <th>状态</th>
                <th>进度</th>
                <th>更新时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered" :key="row.taskId">
                <td>
                  <strong>{{ row.projectName || '未命名项目' }}</strong>
                  <small v-if="row.domain" class="sub">{{ row.domain }}</small>
                </td>
                <td>{{ row.studentName || `用户 ${row.studentUserId}` }}</td>
                <td>{{ row.teamName || row.teamNameHint || '—' }}</td>
                <td>
                  <span
                    class="teacher-tag"
                    :class="statusClass(row.status)"
                  >
                    {{ row.statusLabel || row.status || '—' }}
                  </span>
                </td>
                <td>
                  <span class="progress">{{ Number(row.progress) || 0 }}%</span>
                  <small v-if="row.pageCount" class="sub">{{ row.pageCount }} 页</small>
                </td>
                <td>{{ formatDate(row.updatedAt || row.createdAt) }}</td>
                <td class="col-actions">
                  <a
                    class="teacher-link"
                    :href="historyUrl(row)"
                    target="_blank"
                    rel="noopener"
                  >学生端详情</a>
                  <a
                    v-if="row.hasFile && row.downloadUrl"
                    class="teacher-link"
                    :href="row.downloadUrl"
                    target="_blank"
                    rel="noopener"
                  >下载</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!loading && !filtered.length" class="teacher-empty">
          暂无学生 AI PPT 记录。学生在「AI 应用 → PPT 生成」完成后会出现在这里。
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { fetchTeacherAiPptWorks } from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import { studentAppUrl } from '../../utils/studentApp'

const ctx = useTeacherContextStore()
const loading = ref(true)
const error = ref('')
const status = ref('all')
const keyword = ref('')
const list = ref([])

const filtered = computed(() => {
  const q = keyword.value.toLowerCase()
  return list.value.filter((row) => {
    if (status.value !== 'all') {
      const st = String(row.status || '').toLowerCase()
      if (status.value === 'generating') {
        if (!['generating', 'rendering', 'pending', 'confirmed'].includes(st)) return false
      } else if (st !== status.value) {
        return false
      }
    }
    if (!q) return true
    const hay = `${row.projectName || ''} ${row.studentName || ''} ${row.teamName || ''}`.toLowerCase()
    return hay.includes(q)
  })
})

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—'
}

function statusClass(statusValue) {
  const st = String(statusValue || '').toLowerCase()
  if (st === 'completed') return 'is-ok'
  if (st === 'failed') return 'is-warn'
  if (['generating', 'rendering', 'pending'].includes(st)) return 'is-info'
  return 'is-info'
}

function historyUrl(row) {
  const path = row.historyPath || `/ppt-history/${row.taskId}`
  return studentAppUrl(path)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    list.value = (await fetchTeacherAiPptWorks()) || []
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || 'PPT 列表加载失败'
    list.value = []
  } finally {
    loading.value = false
  }
}

watch(() => [ctx.projectId, ctx.campId], load, { immediate: true })
</script>

<style scoped>
.plan-notice.is-error {
  margin: 0 0 14px;
  padding: 11px 14px;
  border-radius: 11px;
  color: #a33a24;
  background: #fff0ec;
  font-size: 12px;
  font-weight: 700;
}
.manager-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.manager-toolbar__title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.manager-toolbar__title strong {
  font-size: 14px;
}
.manager-toolbar__title span {
  color: var(--ds-muted);
  font-size: 12px;
}
.manager-toolbar__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.manager-toolbar__tools input,
.manager-toolbar__tools select {
  height: 34px;
  border: 1px solid var(--ds-line);
  border-radius: 8px;
  padding: 0 10px;
  font: inherit;
  font-size: 13px;
  background: #fff;
}
.manager-toolbar__tools input {
  min-width: 180px;
}
.sub {
  display: block;
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 11px;
}
.progress {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}
.col-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  white-space: nowrap;
}
</style>
