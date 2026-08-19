<template>
  <div class="meetings-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">会议管理</span>
        <h1>创建、分发并控制路演会议</h1>
        <p>管理员常用动作集中在这里：创建会议、复制会议号和密码、开始/结束会议、清理无效会议。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchMeetings"><el-icon><RefreshRight /></el-icon>刷新列表</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ meetings.length }}</strong><span>全部会议</span><small>当前筛选显示 {{ filteredMeetings.length }} 场</small></article>
      <article class="admin-metric-card"><strong>{{ statusCounts.CREATED }}</strong><span>待开始</span><small>需要主持人启动</small></article>
      <article class="admin-metric-card"><strong>{{ statusCounts.ACTIVE }}</strong><span>进行中</span><small>注意会议秩序和评分采集</small></article>
      <article class="admin-metric-card"><strong>{{ statusCounts.FINISHED }}</strong><span>已结束</span><small>可进入评分和复盘</small></article>
    </section>

    <el-card class="admin-panel">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">创建会议</span>
            <span class="admin-panel-subtitle">建议用“赛事/团队/轮次”命名，方便后续按会议查评分和问题。</span>
          </div>
        </div>
      </template>
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="90px" class="create-form">
        <el-form-item label="会议标题" prop="title">
          <el-input v-model="createForm.title" placeholder="例如：省赛训练营 A 组第 2 轮路演" />
        </el-form-item>
        <el-form-item label="会议密码" prop="password">
          <el-input v-model="createForm.password" placeholder="用于参会验证" show-password />
        </el-form-item>
        <el-form-item label="时长" prop="duration">
          <el-input-number v-model="createForm.duration" :min="5" :max="480" />
          <span class="form-help">分钟</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creating" @click="handleCreate">创建会议</el-button>
          <span class="form-help">创建后可在下方复制会议号和密码发给参会人。</span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">会议列表</span>
            <span class="admin-panel-subtitle">先筛选状态或搜索会议号，再执行开始、结束、复制、删除。</span>
          </div>
          <div class="admin-panel-actions">
            <el-button
              size="small"
              type="danger"
              :disabled="selectedMeetings.length === 0"
              @click="handleBatchDelete"
            >
              批量删除
            </el-button>
          </div>
        </div>
      </template>
      <div class="admin-filter-bar">
        <el-input v-model.trim="keyword" clearable placeholder="搜索标题 / 会议号" />
        <div class="admin-status-tabs">
          <button v-for="item in statusFilters" :key="item.value" :class="['admin-status-tab', { 'is-active': filterStatus === item.value }]" @click="filterStatus = item.value">
            {{ item.label }} {{ item.count }}
          </button>
        </div>
      </div>
      <el-table
        :data="filteredMeetings"
        v-loading="loading"
        border
        stripe
        @selection-change="selectedMeetings = $event"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column prop="meetingCode" label="会议号" width="130">
          <template #default="{ row }">
            <el-button link type="primary" @click="copyText(row.meetingCode, '会议号')">{{ row.meetingCode }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="meetingPassword" label="密码" width="110">
          <template #default="{ row }">
            <el-button link @click="copyText(row.meetingPassword, '会议密码')">复制密码</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light" round>{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长" width="90">
          <template #default="{ row }">{{ row.duration }} 分钟</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'CREATED'"
              size="small" type="success" link
              @click="handleStart(row)"
            >开始</el-button>
            <el-button
              v-if="row.status === 'ACTIVE'"
              size="small" type="warning" link
              @click="handleEnd(row)"
            >结束</el-button>
            <el-button size="small" type="primary" link @click="copyInvite(row)">复制邀请</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filteredMeetings.length === 0 && !loading" class="admin-empty">没有匹配的会议。可以清空筛选条件，或在上方创建一场新会议。</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight } from '@element-plus/icons-vue'
import request from '../api/request'
import { batchDeleteSummary, idsFromRows } from '../utils/batchDelete'

const loading = ref(false)
const meetings = ref([])
const selectedMeetings = ref([])
const createFormRef = ref(null)
const filterStatus = ref('')
const keyword = ref('')
const creating = ref(false)

const createForm = reactive({ title: '', password: '', duration: 60 })
const createRules = {
  title: [{ required: true, message: '请输入会议标题', trigger: 'blur' }],
  password: [{ required: true, message: '请输入会议密码', trigger: 'blur' }]
}

const filteredMeetings = computed(() => {
  const q = keyword.value.toLowerCase()
  return meetings.value.filter((m) => {
    const matchStatus = !filterStatus.value || m.status === filterStatus.value
    const matchKeyword = !q || `${m.title || ''} ${m.meetingCode || ''}`.toLowerCase().includes(q)
    return matchStatus && matchKeyword
  })
})

const statusCounts = computed(() => ({
  CREATED: meetings.value.filter((m) => m.status === 'CREATED').length,
  ACTIVE: meetings.value.filter((m) => m.status === 'ACTIVE').length,
  FINISHED: meetings.value.filter((m) => m.status === 'FINISHED').length,
}))

const statusFilters = computed(() => [
  { label: '全部', value: '', count: meetings.value.length },
  { label: '待开始', value: 'CREATED', count: statusCounts.value.CREATED },
  { label: '进行中', value: 'ACTIVE', count: statusCounts.value.ACTIVE },
  { label: '已结束', value: 'FINISHED', count: statusCounts.value.FINISHED },
])

const statusType = (s) => ({ CREATED: 'info', ACTIVE: 'success', FINISHED: 'warning' }[s] || 'info')
const statusText = (s) => ({ CREATED: '待开始', ACTIVE: '进行中', FINISHED: '已结束' }[s] || s || '未知')

async function fetchMeetings() {
  loading.value = true
  try {
    const res = await request.get('/api/meeting/list')
    meetings.value = res.data || res.list || res || []
  } catch (e) { console.error(e) }
  loading.value = false
}

async function handleCreate() {
  if (!createFormRef.value) return
  await createFormRef.value.validate()
  creating.value = true
  try {
    await request.post('/api/meeting/create', createForm)
    ElMessage.success('会议创建成功')
    Object.assign(createForm, { title: '', password: '', duration: 60 })
    fetchMeetings()
  } catch (e) { console.error(e) }
  creating.value = false
}

async function copyText(text, label) {
  if (!text) return
  await navigator.clipboard.writeText(String(text))
  ElMessage.success(`${label}已复制`)
}

function copyInvite(row) {
  const text = `会议：${row.title}\n会议号：${row.meetingCode}\n会议密码：${row.meetingPassword || ''}`
  copyText(text, '会议邀请')
}

async function handleStart(row) {
  try {
    await request.post(`/api/meeting/${row.id}/start`)
    ElMessage.success('会议已开始')
    fetchMeetings()
  } catch (e) { console.error(e) }
}

async function handleEnd(row) {
  try {
    await ElMessageBox.confirm('确认结束该会议？', '提示', { type: 'warning' })
    await request.post(`/api/meeting/${row.id}/end`)
    ElMessage.success('会议已结束')
    fetchMeetings()
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除会议 "${row.title}"？`, '提示', { type: 'warning' })
    await request.delete(`/api/meeting/${row.id}`)
    ElMessage.success('已删除')
    fetchMeetings()
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

async function handleBatchDelete() {
  const ids = idsFromRows(selectedMeetings.value)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 个会议？相关评分、问题和参会记录也会同步清理。`, '批量删除会议', { type: 'warning' })
    const res = await request.post('/api/meeting/batch-delete', { ids })
    const summary = batchDeleteSummary(res, '会议')
    ElMessage[summary.type](summary.message)
    selectedMeetings.value = []
    await fetchMeetings()
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

onMounted(() => { fetchMeetings() })
</script>

<style scoped>
.create-form {
  display: grid;
  grid-template-columns: minmax(260px, 1.4fr) minmax(220px, 1fr) minmax(160px, 0.7fr) auto;
  gap: 12px;
  align-items: flex-start;
}

.create-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.form-help {
  margin-left: 8px;
  color: var(--admin-muted);
  font-size: 12px;
}

@media (max-width: 1180px) {
  .create-form {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .create-form {
    grid-template-columns: 1fr;
  }
}
</style>
