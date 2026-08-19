<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>讲稿管理</h1>
        <p>查看学生端 AI/编辑器产生的讲稿（按你可访问的团队成员过滤）。</p>
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
            <strong>学生讲稿</strong>
            <span>{{ filtered.length }} / {{ list.length }} 份</span>
          </div>
          <div class="manager-toolbar__tools">
            <input
              v-model.trim="keyword"
              type="search"
              placeholder="搜学生 / 标题"
            />
            <select v-model="source">
              <option value="all">全部来源</option>
              <option value="ppt">来自 PPT</option>
              <option value="manual">独立讲稿</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="teacher-empty">正在加载…</div>
        <div v-else class="teacher-table-wrap">
          <table class="teacher-table">
            <thead>
              <tr>
                <th>讲稿</th>
                <th>学生</th>
                <th>团队</th>
                <th>来源</th>
                <th>内容</th>
                <th>更新时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filtered" :key="row.scriptId">
                <td>
                  <strong>{{ row.title || '未命名讲稿' }}</strong>
                  <small v-if="row.contentVersion" class="sub">版本 {{ row.contentVersion }}</small>
                </td>
                <td>{{ row.studentName || `用户 ${row.studentUserId}` }}</td>
                <td>{{ row.teamName || '—' }}</td>
                <td>
                  <span class="teacher-tag is-info">{{ row.sourceLabel || row.sourceType || '—' }}</span>
                </td>
                <td>
                  <span class="progress">{{ contentHint(row.contentLength) }}</span>
                </td>
                <td>{{ formatDate(row.updatedAt || row.createdAt) }}</td>
                <td class="col-actions">
                  <a
                    class="teacher-link"
                    :href="editorUrl(row)"
                    target="_blank"
                    rel="noopener"
                  >学生端打开</a>
                  <a
                    class="teacher-link"
                    :href="row.pdfUrl"
                    target="_blank"
                    rel="noopener"
                  >导出 PDF</a>
                  <a
                    v-if="row.pptHistoryPath"
                    class="teacher-link"
                    :href="pptUrl(row)"
                    target="_blank"
                    rel="noopener"
                  >关联 PPT</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!loading && !filtered.length" class="teacher-empty">
          暂无学生讲稿记录。学生在讲稿编辑器保存后会出现在这里。
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { fetchTeacherAiScripts } from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import { studentAppUrl } from '../../utils/studentApp'

const ctx = useTeacherContextStore()
const loading = ref(true)
const error = ref('')
const source = ref('all')
const keyword = ref('')
const list = ref([])

const filtered = computed(() => {
  const q = keyword.value.toLowerCase()
  return list.value.filter((row) => {
    if (source.value !== 'all') {
      const st = String(row.sourceType || 'manual').toLowerCase()
      if (source.value === 'ppt' && st !== 'ppt') return false
      if (source.value === 'manual' && st === 'ppt') return false
    }
    if (!q) return true
    const hay = `${row.title || ''} ${row.studentName || ''} ${row.teamName || ''}`.toLowerCase()
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

function contentHint(len) {
  const n = Number(len) || 0
  if (n <= 0) return '空'
  if (n < 200) return `${n} 字 · 很短`
  if (n < 2000) return `约 ${Math.round(n / 100) / 10}k 字`
  return `约 ${Math.round(n / 1000)}k 字`
}

function editorUrl(row) {
  const path = row.editorPath || `/script-editor/detail/${row.scriptId}`
  return studentAppUrl(path)
}

function pptUrl(row) {
  return studentAppUrl(row.pptHistoryPath || `/ppt-history/${row.pptTaskId}`)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    list.value = (await fetchTeacherAiScripts()) || []
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '讲稿列表加载失败'
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
  font-weight: 650;
  font-size: 12px;
  color: var(--ds-ink-2);
}
.col-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  white-space: nowrap;
}
</style>
