<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>协作任务</h1>
        <p>来自当前项目工作台的真实任务列表</p>
      </div>
      <div class="teacher-page__actions">
        <router-link class="teacher-btn teacher-btn--secondary" to="/review/ai-todos">从 AI 待办导入</router-link>
        <router-link v-if="ctx.projectId" class="teacher-btn teacher-btn--primary" :to="`/projects/${ctx.projectId}`">
          在项目中发布
        </router-link>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error">{{ error }}</p>
    <section class="teacher-card">
      <div class="teacher-card__body" style="padding-top: 8px">
        <div v-if="loading" class="teacher-empty">正在加载任务…</div>
        <table v-else class="teacher-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>负责人</th>
              <th>截止</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.id || t.taskId">
              <td>{{ t.title }}</td>
              <td>{{ t.ownerName || t.owner || '—' }}</td>
              <td>{{ formatDate(t.dueAt || t.due) }}</td>
              <td>{{ taskStatusLabel(t.status) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!loading && !tasks.length" class="teacher-empty">当前项目暂无协作任务</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { fetchTeacherTeamTasks } from '../../services/collaborationClient'
import { useTeacherContextStore } from '../../stores/context'
import { taskStatusLabel } from '../../utils/labels'

const ctx = useTeacherContextStore()
const tasks = ref([])
const loading = ref(true)
const error = ref('')

function formatDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (!ctx.projectId) {
      tasks.value = []
      return
    }
    tasks.value = await fetchTeacherTeamTasks(ctx.projectId)
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '任务加载失败'
    tasks.value = []
  } finally {
    loading.value = false
  }
}

watch(() => ctx.projectId, load, { immediate: true })
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
</style>
