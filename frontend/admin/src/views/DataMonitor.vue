<template>
  <div class="monitor-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">数据监控</span>
        <h1>查看在线用户、访问来源和操作日志</h1>
        <p>用于排查异常访问、定位用户最近行为和查看接口耗时。点击用户行后可聚焦查看该用户操作记录。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="refreshAll"><el-icon><Refresh /></el-icon>刷新监控</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ dashboard.onlineUsers || 0 }}</strong><span>当前在线</span><small>正在访问平台的用户</small></article>
      <article class="admin-metric-card"><strong>{{ dashboard.todayActions || 0 }}</strong><span>今日操作</span><small>前后端行为合计</small></article>
      <article class="admin-metric-card"><strong>{{ dashboard.frontendActions || 0 }}</strong><span>前端操作</span><small>页面访问、点击和请求</small></article>
      <article class="admin-metric-card"><strong>{{ dashboard.backendActions || 0 }}</strong><span>接口访问</span><small>后端接口记录</small></article>
    </section>

    <el-card class="admin-table-card monitor-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">用户在线与访问来源</span>
            <span class="admin-panel-subtitle">按用户查看在线状态、最近 IP、归属地和当前页面。</span>
          </div>
          <div class="admin-panel-actions">
            <el-input
              v-model="keyword"
              clearable
              placeholder="搜索用户 / 邮箱 / ID"
              style="width: 220px"
              @keyup.enter="loadUsers"
              @clear="loadUsers"
            />
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="loadingUsers" border stripe @row-click="selectUser">
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="Number(row.online) ? 'success' : 'info'" effect="light">
              {{ Number(row.online) ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户" min-width="130" />
        <el-table-column prop="role" label="角色" width="130" />
        <el-table-column prop="lastIp" label="最近 IP" min-width="140" show-overflow-tooltip />
        <el-table-column prop="ipLocation" label="IP 归属地" min-width="180" show-overflow-tooltip />
        <el-table-column prop="currentPage" label="当前页面" min-width="160" show-overflow-tooltip />
        <el-table-column prop="currentRoute" label="当前路由" min-width="180" show-overflow-tooltip />
        <el-table-column prop="actionCount" label="操作数" width="90" />
        <el-table-column prop="lastSeenAt" label="最近活跃" width="170" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click.stop="selectUser(row)">查看记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="admin-table-card monitor-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">操作记录</span>
            <span class="admin-panel-subtitle">{{ selectedUser ? `${selectedUser.username} 的操作记录` : '全部用户最近操作' }}</span>
          </div>
          <div class="admin-panel-actions">
            <el-select v-model="logSource" clearable placeholder="来源" style="width: 150px" @change="loadLogs">
              <el-option label="用户前端" value="user_frontend" />
              <el-option label="管理后台" value="admin_frontend" />
              <el-option label="后端接口" value="backend" />
            </el-select>
            <el-select v-model="logActionType" clearable placeholder="操作类型" style="width: 160px" @change="loadLogs">
              <el-option label="页面访问" value="page_view" />
              <el-option label="点击操作" value="click" />
              <el-option label="前端请求" value="api_request" />
              <el-option label="后端接口" value="backend_api" />
            </el-select>
            <el-button v-if="selectedUser" @click="clearSelectedUser">看全部</el-button>
            <el-button @click="loadLogs">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loadingLogs" border stripe>
        <el-table-column prop="createdAt" label="时间" width="170" />
        <el-table-column prop="username" label="用户" width="120" />
        <el-table-column prop="source" label="来源" width="120">
          <template #default="{ row }">
            <el-tag :type="sourceType(row.source)" effect="light">{{ sourceLabel(row.source) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actionType" label="类型" width="120" />
        <el-table-column prop="actionName" label="操作" min-width="220" show-overflow-tooltip />
        <el-table-column prop="route" label="前端路由" min-width="170" show-overflow-tooltip />
        <el-table-column prop="path" label="接口路径" min-width="180" show-overflow-tooltip />
        <el-table-column prop="ipAddress" label="IP" width="135" />
        <el-table-column prop="ipLocation" label="归属地" min-width="160" show-overflow-tooltip />
        <el-table-column prop="statusCode" label="状态码" width="90" />
        <el-table-column prop="durationMs" label="耗时(ms)" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import request from '../api/request'

const dashboard = ref({})
const users = ref([])
const logs = ref([])
const keyword = ref('')
const selectedUser = ref(null)
const logSource = ref('')
const logActionType = ref('')
const loadingUsers = ref(false)
const loadingLogs = ref(false)

function ensureSuccess(res) {
  if (res?.code && res.code !== 200) {
    throw new Error(res.message || '请求失败')
  }
  return res
}

async function loadDashboard() {
  const res = ensureSuccess(await request.get('/api/admin/monitor/dashboard'))
  dashboard.value = res.data || {}
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const res = ensureSuccess(await request.get('/api/admin/monitor/users', {
      params: { keyword: keyword.value || undefined }
    }))
    users.value = res.data || []
  } finally {
    loadingUsers.value = false
  }
}

async function loadLogs() {
  loadingLogs.value = true
  try {
    const res = ensureSuccess(await request.get('/api/admin/monitor/logs', {
      params: {
        userId: selectedUser.value?.id,
        source: logSource.value || undefined,
        actionType: logActionType.value || undefined,
        limit: 200
      }
    }))
    logs.value = res.data || []
  } finally {
    loadingLogs.value = false
  }
}

async function refreshAll() {
  await Promise.all([loadDashboard(), loadUsers(), loadLogs()])
}

function selectUser(row) {
  selectedUser.value = row
  loadLogs()
}

function clearSelectedUser() {
  selectedUser.value = null
  loadLogs()
}

function sourceLabel(source) {
  if (source === 'user_frontend') return '用户前端'
  if (source === 'admin_frontend') return '管理后台'
  if (source === 'backend') return '后端接口'
  return source || '未知'
}

function sourceType(source) {
  if (source === 'user_frontend') return 'success'
  if (source === 'admin_frontend') return 'warning'
  if (source === 'backend') return 'info'
  return ''
}

onMounted(refreshAll)
</script>

<style scoped>
</style>
