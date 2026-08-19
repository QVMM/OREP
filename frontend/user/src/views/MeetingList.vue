<template>
  <div class="meeting-list-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>会议列表</h3>
          <el-button type="primary" :icon="Refresh" @click="fetchMeetings">刷新</el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="meetings"
        stripe
        style="width: 100%"
        @row-click="enterMeeting"
      >
        <el-table-column prop="id" label="会议ID" width="80" />
        <el-table-column prop="title" label="会议标题" />
        <el-table-column prop="meetingCode" label="会议编号" width="140" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== 'ENDED'"
              type="primary"
              size="small"
              @click.stop="enterMeeting(row)"
            >进入会议</el-button>
            <el-button
              v-if="row.status === 'ENDED' || row.status === 'RUNNING'"
              type="success"
              size="small"
              plain
              @click.stop="viewScore(row)"
            >查看评分</el-button>
            <el-button
              v-if="row.status === 'ENDED'"
              type="warning"
              size="small"
              plain
              @click.stop="viewAiScore(row)"
            >🤖 AI 评分</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && meetings.length === 0" description="暂无会议" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import request from '../utils/request'

const router = useRouter()

// 会议列表
const meetings = ref([])
// 加载状态
const loading = ref(false)

// 获取会议列表
const fetchMeetings = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/meeting/list')
    meetings.value = Array.isArray(res) ? res : (res.data || [])
  } catch (error) {
    console.error('获取会议列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 进入会议
const enterMeeting = (row) => {
  const routeData = router.resolve(`/meeting/${row.id}`)
  window.open(routeData.href, '_blank', 'noopener')
}

// 查看评分
const viewScore = (row) => {
  router.push(`/score-result/${row.id}`)
}

// 查看 AI 评分
const viewAiScore = (row) => {
  router.push(`/ai-score/${row.id}`)
}

// 获取状态类型
const getStatusType = (status) => {
  const map = {
    CREATED: 'info',
    RUNNING: 'success',
    ENDED: 'danger'
  }
  return map[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const map = {
    CREATED: '待开始',
    RUNNING: '进行中',
    ENDED: '已结束'
  }
  return map[status] || status
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchMeetings()
})
</script>

<style scoped>
.meeting-list-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
}

.el-table :deep(.el-table__row) {
  cursor: pointer;
}
</style>
