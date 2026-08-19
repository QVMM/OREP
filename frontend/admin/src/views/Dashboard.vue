<template>
  <div class="dashboard admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">管理工作台</span>
        <h1>先处理影响训练闭环的事项</h1>
        <p>把会议、评分、问题和资源维护放在同一张工作台里。管理员进入后台后先看风险和待办，再进入具体模块处理。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button type="primary" @click="router.push('/meetings')">创建或管理会议</el-button>
        <el-button plain @click="router.push('/issues')">查看问题跟踪</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card">
        <strong>{{ stats.meetingCount || 0 }}</strong>
        <span>会议总数</span>
        <small>{{ activeMeetingCount }} 场进行中，{{ pendingMeetingCount }} 场待开始</small>
      </article>
      <article class="admin-metric-card">
        <strong>{{ avgScoreText }}</strong>
        <span>平均评分</span>
        <small>低于 80 分的团队建议优先复盘</small>
      </article>
      <article class="admin-metric-card">
        <strong>{{ unresolvedIssues }}</strong>
        <span>待处理问题</span>
        <small>来自评分报告、会议复盘和人工跟进</small>
      </article>
      <article class="admin-metric-card">
        <strong>{{ resolutionRate }}%</strong>
        <span>问题解决率</span>
        <small>已解决 {{ stats.resolvedIssues || 0 }} / 总计 {{ stats.totalIssues || 0 }}</small>
      </article>
    </section>

    <section class="quick-grid">
      <button v-for="item in quickActions" :key="item.path" class="quick-card" @click="router.push(item.path)">
        <span :class="['quick-dot', item.tone]"></span>
        <strong>{{ item.title }}</strong>
        <small>{{ item.desc }}</small>
      </button>
    </section>

    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="16">
        <el-card class="admin-panel">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">评分趋势</span>
                <span class="admin-panel-subtitle">观察训练质量是否持续提升，发现异常下滑后进入评分查看。</span>
              </div>
              <el-button text type="primary" @click="router.push('/scores')">查看评分</el-button>
            </div>
          </template>
          <div ref="chartRef" style="height: 360px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="admin-panel recent-card">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">最近会议</span>
                <span class="admin-panel-subtitle">优先关注进行中的会议和刚结束的复盘。</span>
              </div>
              <el-button text type="primary" size="small" @click="router.push('/meetings')">查看全部</el-button>
            </div>
          </template>
          <div class="recent-list">
            <div v-for="m in recentMeetings" :key="m.id" class="recent-item">
              <div class="ri-dot" :class="dotClass(m.status)" />
              <div class="ri-body">
                <div class="ri-title">{{ m.title }}</div>
                <div class="ri-meta">{{ m.meetingCode }}</div>
              </div>
              <el-tag :type="statusType(m.status)" size="small" effect="light" round>
                {{ statusText(m.status) }}
              </el-tag>
            </div>
            <el-empty v-if="recentMeetings.length === 0" description="暂无会议" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { VideoCamera, TrendCharts, Warning, CircleCheck } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import request from '../api/request'

const router = useRouter()
const chartRef = ref(null)
const stats = ref({})
const recentMeetings = ref([])
let chartInstance = null

const activeMeetingCount = computed(() => recentMeetings.value.filter((item) => item.status === 'ACTIVE').length)
const pendingMeetingCount = computed(() => recentMeetings.value.filter((item) => item.status === 'CREATED').length)
const unresolvedIssues = computed(() => Math.max(0, (stats.value.totalIssues || 0) - (stats.value.resolvedIssues || 0)))
const resolutionRate = computed(() => {
  const total = stats.value.totalIssues || 0
  if (!total) return 0
  return Math.round(((stats.value.resolvedIssues || 0) / total) * 100)
})
const avgScoreText = computed(() => Number(stats.value.avgScore || 0).toFixed(1))

const quickActions = [
  { title: '会议管理', desc: '创建会议、开始/结束会议、复制会议口令', path: '/meetings', tone: 'orange' },
  { title: '问题跟踪', desc: '处理评分和复盘产生的待办问题', path: '/issues', tone: 'red' },
  { title: '评分查看', desc: '查看团队评分结果和趋势变化', path: '/scores', tone: 'green' },
  { title: '资源维护', desc: '上传课程、PPT 和备赛资料', path: '/resources', tone: 'gray' },
]

const statusType = (s) => ({ CREATED: 'info', ACTIVE: 'success', FINISHED: 'warning' }[s] || 'info')
const statusText = (s) => ({ CREATED: '待开始', ACTIVE: '进行中', FINISHED: '已结束' }[s] || s)
const dotClass = (s) => ({ CREATED: 'dot-idle', ACTIVE: 'dot-active', FINISHED: 'dot-done' }[s] || 'dot-idle')

async function fetchStats() {
  try {
    const res = await request.get('/api/statistics/overview')
    const data = res.data || res
    stats.value = data
    renderChart(data)
  } catch (err) { console.error(err) }
}

async function fetchRecentMeetings() {
  try {
    const res = await request.get('/api/meeting/list')
    const list = res.data || res.list || res || []
    recentMeetings.value = Array.isArray(list) ? list.slice(0, 6) : []
  } catch (err) { console.error(err) }
}

function renderChart(data) {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)

  const trend = data.scoreTrend || []
  const dates = trend.map(i => i.date || i.name)
  const scores = trend.map(i => i.score || i.value)

  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: dates.length > 0 ? dates : ['暂无数据'], boundaryGap: false },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      name: '平均分', type: 'line', smooth: true,
      data: scores.length > 0 ? scores : [0],
      itemStyle: { color: '#f36b17' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(243, 107, 23, 0.24)' },
        { offset: 1, color: 'rgba(243, 107, 23, 0.02)' }
      ])}
    }]
  })
}

function handleResize() { chartInstance?.resize() }

onMounted(() => {
  fetchStats()
  fetchRecentMeetings()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.quick-card {
  min-height: 112px;
  border: 1px solid var(--admin-border-soft);
  border-radius: var(--admin-radius-md);
  padding: 16px;
  background: var(--admin-surface);
  text-align: left;
  cursor: pointer;
  box-shadow: var(--admin-shadow-soft);
  transition: transform 180ms var(--admin-ease), border-color 180ms var(--admin-ease);
}

.quick-card:hover {
  transform: translateY(-2px);
  border-color: var(--admin-primary);
}

.quick-card strong,
.quick-card small {
  display: block;
}

.quick-card strong {
  margin-top: 12px;
  color: var(--admin-text-strong);
  font-size: 16px;
}

.quick-card small {
  margin-top: 6px;
  color: var(--admin-muted);
  line-height: 1.5;
}

.quick-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.quick-dot.orange { background: var(--admin-primary); }
.quick-dot.red { background: var(--admin-red); }
.quick-dot.green { background: var(--admin-green); }
.quick-dot.gray { background: var(--admin-faint); }

@media (max-width: 1100px) {
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}

.recent-item:hover { background: var(--admin-primary-soft); }

.ri-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-idle { background: #c0c4cc; }
.dot-active { background: var(--admin-green); box-shadow: 0 0 0 3px rgba(47, 158, 95, 0.15); }
.dot-done { background: var(--admin-primary); }

.ri-body { flex: 1; min-width: 0; }

.ri-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--admin-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ri-meta {
  font-size: 12px;
  color: var(--admin-faint);
  margin-top: 2px;
}
</style>
