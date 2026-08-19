<template>
  <div class="score-result-container">
    <header class="score-page-head">
      <div>
        <span>评分记录</span>
        <h1>{{ meetingTitle || '评分结果' }}</h1>
        <p>查看本场路演的人工评分明细与评语。</p>
      </div>
      <button type="button" class="back-button" @click="goBack">返回</button>
    </header>

    <el-card class="score-result-card">
      <template #header>
        <div class="card-header">
          <h2>评分明细</h2>
          <div>
            <el-button type="primary" :disabled="!scoreResults.length" @click="exportPDF">导出 PDF</el-button>
            <el-button v-if="scoreResults.length" @click="openChat">AI 复盘问答</el-button>
          </div>
        </div>
      </template>

      <div v-if="loadError" class="score-error" role="status">
        <strong>暂时无法查看这场评分</strong>
        <p>{{ loadError }}</p>
        <button type="button" @click="fetchScoreResults">重新加载</button>
      </div>

      <el-table v-else v-loading="loading" :data="scoreResults" stripe style="width: 100%">
        <el-table-column prop="evaluatorName" label="评分人" width="120" />
        <el-table-column prop="evaluatorRole" label="角色" width="100" />
        <el-table-column prop="category" label="评分类别" width="200" show-overflow-tooltip />
        <el-table-column prop="itemName" label="评分项" />
        <el-table-column prop="score" label="得分" width="100">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.score, row.maxScore)">
              {{ row.score }} / {{ row.maxScore }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="评语" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="评分时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !loadError && scoreResults.length === 0" description="暂无评分结果" />

      <!-- 评分统计 -->
      <div v-if="scoreResults.length > 0" class="score-summary">
        <h4>评分统计</h4>
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-label">平均分</span>
            <span class="stat-value">{{ averageScore }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">最高分</span>
            <span class="stat-value">{{ maxScore }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">最低分</span>
            <span class="stat-value">{{ minScore }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">评分人数</span>
            <span class="stat-value">{{ uniqueEvaluators }}</span>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'

const route = useRoute()
const router = useRouter()
const meetingId = computed(() => route.params.meetingId)

// 评分结果列表
const scoreResults = ref([])
// 会议标题
const meetingTitle = ref('')
// 加载状态
const loading = ref(false)
const loadError = ref('')

// 获取评分结果
const fetchScoreResults = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const res = await request.get(`/api/score/result?meetingId=${meetingId.value}`, { silentError: true })
    const data = res.data || res
    // 后端返回嵌套结构: { meetingId, meetingTitle, records: [{ userId, username, totalScore, details: [...] }] }
    // 前端需要扁平化为一维数组
    const records = data.records || []
    const flat = []
    records.forEach(record => {
      ;(record.details || []).forEach(detail => {
        flat.push({
          id: `${record.userId}_${detail.itemName}`,
          itemName: detail.itemName,
          category: detail.category,
          score: Number(detail.score) || 0,
          maxScore: Number(detail.maxScore) || 0,
          comment: detail.comment || '',
          evaluatorName: record.username,
          evaluatorRole: record.role,
          createdAt: record.submittedAt
        })
      })
    })
    scoreResults.value = flat
    meetingTitle.value = data.meetingTitle || ''
  } catch (error) {
    console.error('获取评分结果失败:', error)
    loadError.value = error?.response?.data?.message || '评分记录暂不可用，请稍后重试。'
  } finally {
    loading.value = false
  }
}

// 计算统计数据
const averageScore = computed(() => {
  if (scoreResults.value.length === 0) return 0
  const sum = scoreResults.value.reduce((acc, item) => acc + (item.score || 0), 0)
  return (sum / scoreResults.value.length).toFixed(1)
})

const maxScore = computed(() => {
  if (scoreResults.value.length === 0) return 0
  return Math.max(...scoreResults.value.map((item) => item.score || 0))
})

const minScore = computed(() => {
  if (scoreResults.value.length === 0) return 0
  return Math.min(...scoreResults.value.map((item) => item.score || 0))
})

const uniqueEvaluators = computed(() => {
  const evaluators = new Set(scoreResults.value.map((item) => item.evaluatorName))
  return evaluators.size
})

// 获取分数标签类型（基于得分率）
const getScoreType = (score, maxScore) => {
  const max = Number(maxScore) || 100
  const ratio = Number(score) / max
  if (ratio >= 0.8) return 'success'
  if (ratio >= 0.6) return 'warning'
  return 'danger'
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 导出PDF
const exportPDF = () => {
  // 通过后端接口导出PDF
  const token = getUserToken()
  const url = `/api/score/export-pdf?meetingId=${meetingId.value}`
  fetch(url, {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(res => res.blob())
    .then(blob => {
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `评分报告_${meetingTitle.value || meetingId.value}.pdf`
      link.click()
      URL.revokeObjectURL(link.href)
    })
    .catch(() => {
      ElMessage.error('PDF导出失败')
    })
}

// 打开 AI 复盘问答
const openChat = () => {
  router.push({
    name: 'RoadshowChat',
    params: { meetingId: meetingId.value },
    query: { projectName: meetingTitle.value }
  })
}

// 返回
const goBack = () => {
  router.back()
}

onMounted(() => {
  fetchScoreResults()
})
</script>

<style scoped>
.score-result-container {
  width: 100%;
  min-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  color: var(--ds-ink, #1d1d1f);
}

.score-page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.score-page-head span {
  color: var(--ds-orange, #f4511e);
  font-size: 12px;
  font-weight: 800;
}

.score-page-head h1 {
  margin: 6px 0;
  font-size: 26px;
}

.score-page-head p {
  color: var(--ds-muted, #6e6e73);
}

.back-button,
.score-error button {
  min-height: 40px;
  padding: 0 18px;
  border: 1px solid var(--ds-line-strong, #d2d2d7);
  border-radius: 999px;
  color: var(--ds-ink, #1d1d1f);
  background: #fff;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.score-result-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 22px;
  box-shadow: 0 10px 28px rgba(29, 29, 31, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
}

.score-error {
  min-height: 180px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  text-align: center;
  color: var(--ds-muted, #6e6e73);
}

.score-error strong {
  color: var(--ds-ink, #1d1d1f);
  font-size: 18px;
}

.score-error p {
  margin: 0 0 8px;
}

.score-summary {
  margin-top: 24px;
  padding: 20px;
  background: #f7f7f8;
  border-radius: 16px;
}

.score-summary h4 {
  margin: 0 0 16px 0;
  color: #303133;
}

.summary-stats {
  display: flex;
  gap: 40px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--ds-orange, #f4511e);
}
</style>
