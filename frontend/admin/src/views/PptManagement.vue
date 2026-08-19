<template>
  <div class="ppt-management admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">PPT 任务</span>
        <h1>监控智能 PPT 生成任务</h1>
        <p>查看任务状态、生成进度、大纲和下载结果。优先关注失败任务和长时间处理中任务。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="refreshAll">刷新任务</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ stats.total || 0 }}</strong><span>总任务数</span><small>所有 PPT 生成任务</small></article>
      <article class="admin-metric-card"><strong>{{ stats.by_status?.completed || 0 }}</strong><span>已完成</span><small>可下载 PPT</small></article>
      <article class="admin-metric-card"><strong>{{ processingCount }}</strong><span>处理中</span><small>生成中或渲染中</small></article>
      <article class="admin-metric-card"><strong>{{ stats.by_status?.failed || 0 }}</strong><span>失败</span><small>需要排查输入或服务</small></article>
    </section>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">任务列表</span>
            <span class="admin-panel-subtitle">按状态和领域筛选任务，完成后下载，待确认任务可查看大纲。</span>
          </div>
        </div>
      </template>
    <div class="admin-filter-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="loadTasks">
        <el-option label="待处理" value="pending" />
        <el-option label="生成中" value="generating" />
        <el-option label="待确认" value="outline_ready" />
        <el-option label="渲染中" value="rendering" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-select v-model="filterDomain" placeholder="领域筛选" clearable @change="loadTasks">
        <el-option label="AI + 物联网" value="ai_iot" />
        <el-option label="金融科技" value="fintech" />
        <el-option label="智慧医疗" value="healthcare" />
        <el-option label="智慧教育" value="education" />
      </el-select>
    </div>

    <el-table
      :data="tasks"
      v-loading="loading"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="project_name" label="项目名称" min-width="180">
        <template #default="{ row }">
          <div class="project-name">{{ row.project_name }}</div>
          <div class="project-team">{{ row.team_name }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="username" label="创建者" width="120" />
      <el-table-column prop="domain" label="领域" width="120">
        <template #default="{ row }">
          {{ getDomainName(row.domain) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="120">
        <template #default="{ row }">
          <el-progress
            :percentage="row.progress || 0"
            :stroke-width="8"
            :show-text="false"
          />
          <span class="progress-text">{{ row.progress || 0 }}%</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'completed'"
            type="primary"
            link
            @click="downloadPPT(row)"
          >
            下载
          </el-button>
          <el-button
            v-if="row.outline_json"
            type="info"
            link
            @click="viewOutline(row)"
          >
            大纲
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="tasks.length === 0 && !loading" class="admin-empty">暂无匹配 PPT 任务。可以调整筛选条件后刷新。</div>

    <div class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadTasks"
        @current-change="loadTasks"
      />
    </div>
    </el-card>

    <!-- Outline Dialog -->
    <el-dialog v-model="outlineDialogVisible" title="大纲预览" width="600px">
      <div v-if="currentOutline" class="outline-view">
        <div class="outline-header">
          <h3>{{ currentOutline.project?.name }}</h3>
          <span>{{ currentOutline.pages?.length }} 页</span>
        </div>
        <div class="outline-pages">
          <div
            v-for="page in currentOutline.pages"
            :key="page.page_index"
            class="outline-page-item"
          >
            <span class="page-num">{{ page.page_index }}</span>
            <span class="page-title">{{ page.data?.title || page.section }}</span>
            <span class="page-layout">{{ page.layout }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { getAdminToken } from '../utils/authStorage'

const loading = ref(false)
const tasks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const filterDomain = ref('')

const stats = ref({})
const outlineDialogVisible = ref(false)
const currentOutline = ref(null)
const processingCount = computed(() => (stats.value.by_status?.generating || 0) + (stats.value.by_status?.rendering || 0))

onMounted(() => {
  refreshAll()
})

const refreshAll = () => {
  loadStats()
  loadTasks()
}

const loadStats = async () => {
  try {
    const res = await request.get('/api/ppt/admin/statistics')
    stats.value = res.data || {}
  } catch (e) {
    console.error('加载统计失败:', e)
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/ppt/admin/tasks', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        status: filterStatus.value || undefined,
        domain: filterDomain.value || undefined
      }
    })
    tasks.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    ElMessage.error('加载任务列表失败')
  }
  loading.value = false
}

const downloadPPT = async (task) => {
  try {
    const token = getAdminToken()
    const response = await fetch(`/api/ppt/task/${task.id}/download`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error('下载失败')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${task.project_name}.pptx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)

    ElMessage.success('下载成功')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

const viewOutline = (task) => {
  currentOutline.value = task.outline_json
  outlineDialogVisible.value = true
}

const getDomainName = (domain) => {
  const names = {
    ai_iot: 'AI + 物联网',
    fintech: '金融科技',
    healthcare: '智慧医疗',
    education: '智慧教育',
    other: '其他领域'
  }
  return names[domain] || domain
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    generating: 'warning',
    outline_ready: 'primary',
    rendering: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    generating: '生成中',
    outline_ready: '待确认',
    rendering: '渲染中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}
</script>

<style scoped>
.project-name {
  font-weight: 500;
  color: var(--admin-text-strong);
}

.project-team {
  font-size: 12px;
  color: var(--admin-muted);
}

.progress-text {
  font-size: 12px;
  color: var(--admin-muted);
  margin-left: 8px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.outline-view {
  max-height: 400px;
  overflow-y: auto;
}

.outline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--admin-border-soft);
}

.outline-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--admin-text-strong);
}

.outline-pages {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.outline-page-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--admin-surface-muted);
  border-radius: var(--admin-radius-sm);
}

.page-num {
  width: 24px;
  height: 24px;
  background: var(--admin-primary);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.page-title {
  flex: 1;
  font-size: 14px;
  color: var(--admin-text-strong);
}

.page-layout {
  font-size: 12px;
  color: var(--admin-muted);
}
</style>
