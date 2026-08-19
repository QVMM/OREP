<template>
  <div class="analytics-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">数据分析</span>
        <h1>看清训练质量、评分分布和问题处理效率</h1>
        <p>这页不只展示图表，而是帮助管理员判断：哪些会议质量低、哪些问题长期未解决、评分趋势是否在变好。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchAnalytics">刷新分析</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ overview.meetingCount || 0 }}</strong><span>会议数量</span><small>进入会议管理查看明细</small></article>
      <article class="admin-metric-card"><strong>{{ avgScoreText }}</strong><span>平均评分</span><small>低分会议需要重点复盘</small></article>
      <article class="admin-metric-card"><strong>{{ overview.totalIssues || 0 }}</strong><span>问题总数</span><small>待解决 {{ unresolvedIssues }} 个</small></article>
      <article class="admin-metric-card"><strong>{{ resolutionRate }}%</strong><span>解决率</span><small>已解决 {{ overview.resolvedIssues || 0 }} 个</small></article>
    </section>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="admin-panel">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">会议评分分布</span>
                <span class="admin-panel-subtitle">快速找出评分偏低的会议或团队。</span>
              </div>
            </div>
          </template>
          <div ref="barChartRef" style="height: 350px"></div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="admin-panel">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">问题状态占比</span>
                <span class="admin-panel-subtitle">判断后续辅导和整改是否形成闭环。</span>
              </div>
            </div>
          </template>
          <div ref="pieChartRef" style="height: 350px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card class="admin-panel">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">评分趋势分析</span>
                <span class="admin-panel-subtitle">如果连续训练后曲线没有上升，应检查课程、会议复盘和建议执行情况。</span>
              </div>
            </div>
          </template>
          <div ref="lineChartRef" style="height: 400px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import request from '../api/request'

const barChartRef = ref(null)
const pieChartRef = ref(null)
const lineChartRef = ref(null)
let barChart = null
let pieChart = null
let lineChart = null
const overview = ref({})

const avgScoreText = computed(() => Number(overview.value.avgScore || 0).toFixed(1))
const unresolvedIssues = computed(() => Math.max(0, (overview.value.totalIssues || 0) - (overview.value.resolvedIssues || 0)))
const resolutionRate = computed(() => {
  const total = overview.value.totalIssues || 0
  if (!total) return 0
  return Math.round(((overview.value.resolvedIssues || 0) / total) * 100)
})

// 获取分析数据
async function fetchAnalytics() {
  try {
    const res = await request.get('/api/statistics/overview')
    const data = res.data || res
    overview.value = data
    renderBarChart(data)
    renderPieChart(data)
    renderLineChart(data)
  } catch (err) {
    console.error('获取分析数据失败:', err)
    overview.value = {}
    // 用空数据渲染图表
    renderBarChart({})
    renderPieChart({})
    renderLineChart({})
  }
}

// 渲染柱状图 - 会议评分分布
function renderBarChart(data) {
  if (!barChartRef.value) return
  barChart = echarts.init(barChartRef.value)

  // 假设后端返回 meetingScores: [{ title, avgScore }, ...]
  const meetings = data.meetingScores || []
  const names = meetings.map(m => m.title || m.name)
  const scores = meetings.map(m => m.avgScore || m.score)

  barChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: names.length > 0 ? names : ['暂无数据'],
      axisLabel: { rotate: 30 }
    },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      name: '平均分',
      type: 'bar',
      data: scores.length > 0 ? scores : [0],
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#f36b17' },
          { offset: 1, color: '#ffb083' }
        ]),
        borderRadius: [4, 4, 0, 0]
      }
    }]
  })
}

// 渲染饼图 - 问题状态占比
function renderPieChart(data) {
  if (!pieChartRef.value) return
  pieChart = echarts.init(pieChartRef.value)

  // 假设后端返回 issueStats: { resolved, unresolved } 或 totalIssues / resolvedIssues
  const resolved = data.resolvedIssues || 0
  const total = data.totalIssues || 0
  const unresolved = Math.max(0, total - resolved)

  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: '5%' },
    series: [{
      name: '问题状态',
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%' },
      data: [
        { value: resolved, name: '已解决', itemStyle: { color: '#2f9e5f' } },
        { value: unresolved, name: '待解决', itemStyle: { color: '#f36b17' } }
      ]
    }]
  })
}

// 渲染折线图 - 评分趋势
function renderLineChart(data) {
  if (!lineChartRef.value) return
  lineChart = echarts.init(lineChartRef.value)

  const trend = data.scoreTrend || []
  const dates = trend.map(t => t.date || t.name)
  const scores = trend.map(t => t.score || t.value)

  lineChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates.length > 0 ? dates : ['暂无数据'],
      boundaryGap: false
    },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      name: '评分趋势',
      type: 'line',
      smooth: true,
      data: scores.length > 0 ? scores : [0],
      itemStyle: { color: '#f36b17' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(243, 107, 23, 0.24)' },
          { offset: 1, color: 'rgba(243, 107, 23, 0.04)' }
        ])
      }
    }]
  })
}

// 窗口大小变化时重绘
function handleResize() {
  barChart?.resize()
  pieChart?.resize()
  lineChart?.resize()
}

onMounted(() => {
  fetchAnalytics()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  barChart?.dispose()
  pieChart?.dispose()
  lineChart?.dispose()
})
</script>

<style scoped>
</style>
