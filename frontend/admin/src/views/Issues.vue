<template>
  <div class="issues-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">问题跟踪</span>
        <h1>把评分和会议复盘变成可处理事项</h1>
        <p>先看待解决问题，再按会议、团队、指导老师或分类定位责任人。问题解决后及时标记，形成训练闭环。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchIssues">刷新问题</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ issues.length }}</strong><span>当前列表</span><small>受状态筛选影响</small></article>
      <article class="admin-metric-card"><strong>{{ openIssueCount }}</strong><span>待解决</span><small>优先跟进这些事项</small></article>
      <article class="admin-metric-card"><strong>{{ resolvedIssueCount }}</strong><span>已解决</span><small>已完成闭环</small></article>
      <article class="admin-metric-card"><strong>{{ categoryCount }}</strong><span>问题分类</span><small>用于识别集中短板</small></article>
    </section>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">问题列表</span>
            <span class="admin-panel-subtitle">先筛选待解决，再按会议、团队、老师或分类定位具体问题。</span>
          </div>
        </div>
      </template>
      <div class="admin-filter-bar">
        <el-input v-model.trim="keyword" clearable placeholder="搜索标题 / 会议 / 团队 / 老师" />
        <div class="admin-status-tabs">
          <button v-for="item in statusFilters" :key="item.value" :class="['admin-status-tab', { 'is-active': filterStatus === item.value }]" @click="changeStatus(item.value)">
            {{ item.label }} {{ item.count }}
          </button>
        </div>
      </div>
      <el-table :data="filteredIssues" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="问题标题" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="meetingTitle" label="关联会议" min-width="180" show-overflow-tooltip />
        <el-table-column prop="teamName" label="所属团队" min-width="150" show-overflow-tooltip />
        <el-table-column prop="mentorName" label="指导老师" width="120">
          <template #default="{ row }">
            {{ row.mentorName || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="reporterName" label="提出人" width="120" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'RESOLVED' ? 'success' : 'warning'">
              {{ row.status === 'RESOLVED' ? '已解决' : '待解决' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'RESOLVED'"
              size="small"
              type="success"
              @click="handleResolve(row)"
            >
              标记解决
            </el-button>
            <el-tag v-else type="info">已处理</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filteredIssues.length === 0 && !loading" class="admin-empty">没有匹配的问题。可以清空搜索条件或切换状态。</div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const loading = ref(false)
const issues = ref([])
const filterStatus = ref('')
const keyword = ref('')

const filteredIssues = computed(() => {
  const q = keyword.value.toLowerCase()
  return issues.value.filter((issue) => {
    if (!q) return true
    return `${issue.title || ''} ${issue.description || ''} ${issue.meetingTitle || ''} ${issue.teamName || ''} ${issue.mentorName || ''} ${issue.category || ''}`.toLowerCase().includes(q)
  })
})

const openIssueCount = computed(() => issues.value.filter((issue) => issue.status !== 'RESOLVED').length)
const resolvedIssueCount = computed(() => issues.value.filter((issue) => issue.status === 'RESOLVED').length)
const categoryCount = computed(() => new Set(issues.value.map((issue) => issue.category).filter(Boolean)).size)
const statusFilters = computed(() => [
  { label: '全部', value: '', count: issues.value.length },
  { label: '待解决', value: 'OPEN', count: openIssueCount.value },
  { label: '已解决', value: 'RESOLVED', count: resolvedIssueCount.value },
])

function changeStatus(status) {
  filterStatus.value = status
  fetchIssues()
}

// 获取问题列表
async function fetchIssues() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    const res = await request.get('/api/issue/list', { params })
    issues.value = res.data || res.list || res || []
  } catch (err) {
    console.error('获取问题列表失败:', err)
  } finally {
    loading.value = false
  }
}

// 标记问题为已解决
async function handleResolve(row) {
  try {
    await ElMessageBox.confirm(
      `确认将「${row.meetingTitle || '关联会议'}」中的问题 "${row.title}" 标记为已解决？`,
      '解决问题',
      { type: 'warning' }
    )
    await request.post('/api/issue/resolve', { id: row.id })
    ElMessage.success('问题已标记为已解决')
    fetchIssues()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('解决问题失败:', err)
    }
  }
}

onMounted(() => {
  fetchIssues()
})
</script>

<style scoped>
</style>
