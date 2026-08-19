<template>
  <div class="scores-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">评分查看</span>
        <h1>按会议查看评分结果和复盘信号</h1>
        <p>先选择会议，再看评分条目、低分项和评语。低分项应该回到问题跟踪或团队复盘中处理。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button v-if="selectedMeetingId" type="primary" @click="exportPdf">导出 PDF</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ scores.length }}</strong><span>评分条目</span><small>{{ meetingTitle || selectedMeeting?.title || '请选择会议' }}</small></article>
      <article class="admin-metric-card"><strong>{{ averageScoreText }}</strong><span>平均得分率</span><small>按得分 / 满分折算</small></article>
      <article class="admin-metric-card"><strong>{{ lowScoreCount }}</strong><span>低分项</span><small>低于 60% 的评分项</small></article>
      <article class="admin-metric-card"><strong>{{ evaluatorCount }}</strong><span>评分人</span><small>参与评分的评委或老师</small></article>
    </section>

    <el-card class="admin-panel select-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">选择会议</span>
            <span class="admin-panel-subtitle">默认会尝试选择已有评分数据的会议，也可以手动切换。</span>
          </div>
        </div>
      </template>
      <el-select
        v-model="selectedMeetingId"
        placeholder="请选择会议"
        filterable
        :loading="meetingsLoading"
        style="width: min(100%, 420px)"
        @change="fetchScores"
      >
        <el-option
          v-for="m in meetings"
          :key="m.id"
          :label="m.title"
          :value="m.id"
        />
      </el-select>
    </el-card>

    <el-card class="admin-table-card" v-if="selectedMeetingId">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">评分结果</span>
            <span v-if="meetingTitle" class="admin-panel-subtitle">{{ meetingTitle }}</span>
          </div>
          <div class="admin-panel-actions">
            <el-input v-model.trim="keyword" clearable placeholder="搜索评分人 / 类别 / 评分项 / 评语" style="width: 300px" />
          </div>
        </div>
      </template>
      <el-table
        :data="filteredScores"
        v-loading="loading"
        border
        stripe
        empty-text="暂无评分数据"
      >
        <el-table-column prop="evaluatorName" label="评分人" width="130" />
        <el-table-column prop="evaluatorRole" label="角色" width="110" />
        <el-table-column prop="category" label="评分类别" min-width="180" show-overflow-tooltip />
        <el-table-column prop="itemName" label="评分项" min-width="160" show-overflow-tooltip />
        <el-table-column prop="score" label="得分" width="120">
          <template #default="{ row }">
            <el-tag :type="scoreType(row.score, row.maxScore)">
              {{ row.score }} / {{ row.maxScore }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="评语" min-width="180" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="评分时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filteredScores.length === 0 && !loading" class="admin-empty">暂无匹配评分数据。可以切换会议或清空搜索条件。</div>
    </el-card>
    <div v-else class="admin-empty">暂无可查看会议，请先创建并完成评分。</div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { getScoreResultData, normalizeScoreRows } from '../utils/scoreResult'

const loading = ref(false)
const meetingsLoading = ref(false)
const meetings = ref([])
const scores = ref([])
const selectedMeetingId = ref(null)
const meetingTitle = ref('')
const keyword = ref('')

const selectedMeeting = computed(() => meetings.value.find((item) => item.id === selectedMeetingId.value))
const filteredScores = computed(() => {
  const q = keyword.value.toLowerCase()
  if (!q) return scores.value
  return scores.value.filter((score) => `${score.evaluatorName || ''} ${score.evaluatorRole || ''} ${score.category || ''} ${score.itemName || ''} ${score.comment || ''}`.toLowerCase().includes(q))
})
const evaluatorCount = computed(() => new Set(scores.value.map((score) => score.evaluatorName).filter(Boolean)).size)
const lowScoreCount = computed(() => scores.value.filter((score) => {
  const max = Number(score.maxScore) || 100
  return max && Number(score.score || 0) / max < 0.6
}).length)
const averageScoreText = computed(() => {
  if (!scores.value.length) return '0%'
  const ratios = scores.value.map((score) => {
    const max = Number(score.maxScore) || 100
    return max ? Number(score.score || 0) / max : 0
  })
  const avg = ratios.reduce((sum, item) => sum + item, 0) / ratios.length
  return `${Math.round(avg * 100)}%`
})

// 分数颜色
function scoreType(score, maxScore) {
  const max = Number(maxScore) || 100
  const ratio = max ? Number(score) / max : 0
  if (ratio >= 0.8) return 'success'
  if (ratio >= 0.6) return 'warning'
  return 'danger'
}

function formatDate(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

// 获取会议列表
async function fetchMeetings() {
  meetingsLoading.value = true
  try {
    const res = await request.get('/api/meeting/list')
    meetings.value = res.data || res.list || res || []
    if (!selectedMeetingId.value && meetings.value.length > 0) {
      await selectInitialMeeting()
    }
  } catch (err) {
    console.error('获取会议列表失败:', err)
  } finally {
    meetingsLoading.value = false
  }
}

async function loadScoreResult(meetingId) {
  const res = await request.get('/api/score/result', {
    params: { meetingId }
  })
  const data = getScoreResultData(res)
  return {
    data,
    rows: normalizeScoreRows(data)
  }
}

function applyScoreResult(result) {
  scores.value = result.rows
  meetingTitle.value = result.data.meetingTitle || ''
}

async function selectInitialMeeting() {
  loading.value = true
  let fallback = null
  try {
    for (const meeting of meetings.value) {
      const result = await loadScoreResult(meeting.id)
      if (!fallback) {
        fallback = { meetingId: meeting.id, result }
      }
      if (result.rows.length > 0) {
        selectedMeetingId.value = meeting.id
        applyScoreResult(result)
        return
      }
    }

    if (fallback) {
      selectedMeetingId.value = fallback.meetingId
      applyScoreResult(fallback.result)
    }
  } catch (err) {
    console.error('初始化评分会议失败:', err)
    if (meetings.value.length > 0) {
      selectedMeetingId.value = meetings.value[0].id
      scores.value = []
      meetingTitle.value = meetings.value[0].title || ''
    }
  } finally {
    loading.value = false
  }
}

// 获取评分结果
async function fetchScores(meetingId = selectedMeetingId.value) {
  if (!meetingId) {
    scores.value = []
    meetingTitle.value = ''
    return
  }
  loading.value = true
  try {
    const result = await loadScoreResult(meetingId)
    applyScoreResult(result)
  } catch (err) {
    console.error('获取评分结果失败:', err)
    scores.value = []
    meetingTitle.value = ''
  } finally {
    loading.value = false
  }
}

// 导出PDF
async function exportPdf() {
  if (!selectedMeetingId.value) return
  try {
    const res = await request.get('/api/score/export-pdf', {
      params: { meetingId: selectedMeetingId.value },
      responseType: 'blob'
    })
    const blob = res instanceof Blob ? res : new Blob([res], { type: 'application/pdf' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `评分报告_${meetingTitle.value || selectedMeetingId.value}.pdf`
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('PDF导出成功')
  } catch (err) {
    console.error('导出PDF失败:', err)
  }
}

onMounted(() => {
  fetchMeetings()
})
</script>

<style scoped>
</style>
