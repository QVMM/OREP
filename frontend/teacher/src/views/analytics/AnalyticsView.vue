<template>
  <div class="teacher-page analytics-page">
    <header class="teacher-page__head">
      <div>
        <h1>学情总览</h1>
        <p>
          图表看提交节奏、投入分布与路演表现
          <span v-if="campName" class="teacher-muted">
            · {{ campName }}
            <template v-if="camp.currentDay"> · 第 {{ camp.currentDay }}/{{ camp.totalDays || '—' }} 天</template>
          </span>
          <span v-else-if="ctx.projectName" class="teacher-muted"> · {{ ctx.projectName }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          刷新
        </button>
        <router-link class="teacher-btn teacher-btn--secondary" to="/analytics/students">学生档案</router-link>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>

    <div v-if="loading && !hasData" class="teacher-empty">正在加载图表数据…</div>

    <template v-else>
      <!-- 顶部指标：Element Statistic -->
      <el-row :gutter="12" class="stat-row">
        <el-col :xs="12" :sm="12" :md="6" v-for="item in statItems" :key="item.key">
          <el-card shadow="never" class="stat-card" :body-style="{ padding: '16px 18px' }">
            <el-statistic :title="item.title" :value="item.value" :precision="item.precision">
              <template v-if="item.suffix" #suffix>
                <span class="stat-suffix">{{ item.suffix }}</span>
              </template>
            </el-statistic>
            <p class="stat-hint">{{ item.hint }}</p>
          </el-card>
        </el-col>
      </el-row>

      <!-- 全宽：提交趋势 -->
      <el-card shadow="never" class="panel-card">
        <template #header>
          <div class="panel-head">
            <div>
              <h2>近 14 日提交趋势</h2>
              <p>看每天有没有人在交作业，曲线掉下去就要盯一下</p>
            </div>
            <span class="teacher-tag is-info">共 {{ totalSubmissions14d }} 次</span>
          </div>
        </template>
        <BaseEchart
          :option="trendOption"
          height="300px"
          aria-label="近14日提交趋势"
          :loading="loading"
        />
      </el-card>

      <!-- 四卡：2×2 -->
      <el-row :gutter="12" class="quad-row">
        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel-card panel-card--fixed">
            <template #header>
              <div class="panel-head">
                <div>
                  <h2>学情结构</h2>
                  <p>学生与任务量级一览</p>
                </div>
              </div>
            </template>
            <div class="structure-wrap">
              <div class="structure-chart">
                <BaseEchart :option="structureOption" height="220px" aria-label="学情结构" />
                <div class="structure-center" aria-hidden="true">
                  <strong>{{ studentCount }}</strong>
                  <small>学生</small>
                </div>
              </div>
              <ul class="structure-legend">
                <li v-for="row in structureLegend" :key="row.key">
                  <i :style="{ background: row.color }" />
                  <span>{{ row.label }}</span>
                  <b>{{ row.value }}</b>
                </li>
              </ul>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel-card panel-card--fixed">
            <template #header>
              <div class="panel-head">
                <div>
                  <h2>投入 TOP</h2>
                  <p>用于表扬与示范，不是竞技</p>
                </div>
                <nav class="workspace-tabs analytics-rank-tabs" aria-label="投入排行维度">
                  <button
                    type="button"
                    :class="{ 'is-active': rankTab === 'studyTime' }"
                    @click="rankTab = 'studyTime'"
                  >
                    时长
                  </button>
                  <button
                    type="button"
                    :class="{ 'is-active': rankTab === 'submissions' }"
                    @click="rankTab = 'submissions'"
                  >
                    提交
                  </button>
                  <button
                    type="button"
                    :class="{ 'is-active': rankTab === 'resources' }"
                    @click="rankTab = 'resources'"
                  >
                    资源
                  </button>
                </nav>
              </div>
            </template>
            <div v-if="rankRows.length" class="rank-list">
              <button
                v-for="(row, idx) in rankRows"
                :key="row.userId || row.name"
                type="button"
                class="rank-row"
                @click="row.userId && $router.push(`/analytics/students/${row.userId}?from=analytics`)"
              >
                <span class="rank-row__no" :data-rank="idx + 1">{{ idx + 1 }}</span>
                <span
                  class="teacher-avatar"
                  :style="{
                    width: '36px',
                    height: '36px',
                    fontSize: '14px',
                    background: avatarColor(row.userId || row.name),
                  }"
                >
                  {{ initial(row.name) }}
                </span>
                <div class="rank-row__main">
                  <div class="rank-row__meta">
                    <strong>{{ row.name }}</strong>
                    <b>{{ row.label }}</b>
                  </div>
                  <div class="rank-bar" aria-hidden="true">
                    <i :style="{ width: `${row.pct}%` }" />
                  </div>
                </div>
              </button>
            </div>
            <div v-else class="panel-empty">暂无投入数据</div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel-card panel-card--fixed">
            <template #header>
              <div class="panel-head">
                <div>
                  <h2>缺交学生</h2>
                  <p>点头像进学生档案</p>
                </div>
                <router-link class="teacher-link" to="/analytics/students">档案 ›</router-link>
              </div>
            </template>
            <div v-if="missingList.length" class="miss-grid">
              <button
                v-for="row in missingList"
                :key="row.userId"
                type="button"
                class="miss-item"
                @click="$router.push(`/analytics/students/${row.userId}?from=analytics`)"
              >
                <span
                  class="teacher-avatar"
                  :style="{
                    width: '40px',
                    height: '40px',
                    fontSize: '15px',
                    background: avatarColor(row.userId),
                  }"
                >
                  {{ initial(row.name) }}
                </span>
                <div class="miss-item__text">
                  <strong>{{ row.name }}</strong>
                  <span class="teacher-tag is-danger">缺 {{ row.missingDays }} 天</span>
                </div>
              </button>
            </div>
            <div v-else class="panel-empty">当前没有缺交学生</div>
          </el-card>
        </el-col>

        <el-col :xs="24" :md="12">
          <el-card shadow="never" class="panel-card panel-card--fixed">
            <template #header>
              <div class="panel-head">
                <div>
                  <h2>营期进度</h2>
                  <p>{{ campName || '暂无训练营' }}</p>
                </div>
                <span v-if="draftPastDays > 0" class="teacher-tag is-warn">
                  {{ draftPastDays }} 个草稿日
                </span>
              </div>
            </template>
            <BaseEchart
              v-if="campName"
              :option="campGaugeOption"
              height="280px"
              aria-label="营期进度"
            />
            <div v-else class="panel-empty panel-empty--action">
              <p>创建训练营后显示进度</p>
              <router-link class="teacher-btn teacher-btn--primary" to="/camp/create">创建训练营</router-link>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 路演 -->
      <el-card shadow="never" class="panel-card">
        <template #header>
          <div class="panel-head">
            <div>
              <h2>路演表现</h2>
              <p>薄弱维度与最近得分</p>
            </div>
            <div class="panel-head__side">
              <span v-if="scoreText !== '—'" class="teacher-tag is-info">均分 {{ scoreText }}</span>
              <router-link class="teacher-link" to="/review/reports">评分报告 ›</router-link>
            </div>
          </div>
        </template>
        <el-row :gutter="16" v-if="dimensions.length || recentScores.length">
          <el-col :xs="24" :md="dimensions.length ? 14 : 24">
            <BaseEchart
              v-if="dimensions.length"
              :option="radarOption"
              height="300px"
              aria-label="路演薄弱维度雷达图"
            />
            <div v-else class="score-only">
              <el-statistic title="最近均分" :value="Number(scoreText) || 0" :precision="1" />
            </div>
          </el-col>
          <el-col v-if="recentScores.length" :xs="24" :md="dimensions.length ? 10 : 24">
            <div class="score-list">
              <div v-for="row in recentScores" :key="row.reportId" class="score-list__item">
                <span class="teacher-tag is-warn">{{ formatScore(row.score) }}</span>
                <span>{{ shortDate(row.scoredAt) }}</span>
                <em>{{ row.teamName || '—' }}</em>
              </div>
            </div>
          </el-col>
        </el-row>
        <div v-else class="panel-empty panel-empty--action">
          <p>完成路演评分后展示雷达图与得分</p>
          <router-link class="teacher-btn teacher-btn--secondary" to="/review/reports?tab=upload">
            上传视频评分
          </router-link>
        </div>
      </el-card>

      <!-- 荣誉 / 整改：能力在别处，这里只给汇总入口 -->
      <section class="side-actions teacher-card" aria-label="荣誉与整改入口">
        <div class="side-actions__item">
          <div>
            <strong>项目荣誉</strong>
            <p>
              <template v-if="certCount > 0">已颁发 {{ certCount }} 张奖状</template>
              <template v-else>颁发与预览在项目详情</template>
            </p>
          </div>
          <router-link
            v-if="honorProjectTo"
            class="teacher-btn teacher-btn--secondary teacher-btn--sm"
            :to="honorProjectTo"
          >
            去颁发
          </router-link>
          <router-link v-else class="teacher-btn teacher-btn--secondary teacher-btn--sm" to="/projects">
            选项目
          </router-link>
        </div>
        <div class="side-actions__item">
          <div>
            <strong>整改复盘</strong>
            <p>
              <template v-if="todoPendingCount > 0">{{ todoPendingCount }} 项待你处理</template>
              <template v-else>AI 评分生成的整改在此审核发布</template>
            </p>
          </div>
          <router-link class="teacher-btn teacher-btn--primary teacher-btn--sm" to="/review/ai-todos">
            去处理
          </router-link>
        </div>
      </section>

      <nav class="quiet-links" aria-label="相关页面">
        <router-link to="/camp/review-queue">提交与批改</router-link>
        <router-link to="/camp/progress">训练进度</router-link>
        <router-link to="/review/reports">评分报告</router-link>
        <router-link to="/analytics/students">学生档案</router-link>
      </nav>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { graphic } from 'echarts/core'
import {
  ElCard,
  ElCol,
  ElRow,
  ElStatistic,
} from 'element-plus'
import BaseEchart from '../../components/charts/BaseEchart.vue'
import { fetchTeacherAiTodos, fetchTeacherAnalytics, fetchTeamCertificates } from '../../api'
import { useTeacherContextStore } from '../../stores/context'

const ORANGE = '#e84a1c'
const ORANGE_SOFT = '#ffb089'
const GREEN = '#0f9f6e'
const AMBER = '#f59e0b'
const BLUE = '#2563eb'
const MUTED = '#a1a1aa'
const AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777', '#0e7490']

const DIMENSION_NAMES = {
  skill_level: '技能水平',
  professionalism: '职业素养',
  application_value: '应用价值',
  teamwork: '团队合作',
  innovation: '创新创意',
  problem_solving: '问题解决',
  communication: '表达沟通',
  presentation: '呈现表达',
  coding: '工程实现',
  creativity: '创新创意',
}

const ctx = useTeacherContextStore()
const data = ref({})
const loading = ref(true)
const error = ref('')
const rankTab = ref('studyTime')
const certCount = ref(0)
const todoPendingCount = ref(0)

const hasData = computed(() => Object.keys(data.value || {}).length > 0)
const honorProjectTo = computed(() => {
  const id = ctx.projectId
  if (!id) return ''
  return `/projects/${id}`
})
const camp = computed(() => data.value.camp || {})
const campName = computed(() => data.value.campName || camp.value.campName || '')
const pendingReviews = computed(() => Number(data.value.pendingReviews || 0))
const expectedSubmissions = computed(() => Number(data.value.expectedSubmissions || 0))
const submittedSubmissions = computed(() => Number(data.value.submittedSubmissions || 0))
const missingSubmissions = computed(() => Number(data.value.missingSubmissions || 0))
const missingStudentCount = computed(() => Number(data.value.missingStudentCount || 0))
const roadshowReportCount = computed(() => Number(data.value.roadshowReportCount || 0))
const studentCount = computed(() => Number(data.value.studentCount || 0))
const draftPastDays = computed(() => Number(camp.value.draftPastDays || 0))

const submissionRate = computed(() => {
  const raw = Number(data.value.submissionRate)
  if (!Number.isFinite(raw)) return 0
  return Math.min(100, Math.max(0, Math.round(raw)))
})

const scoreText = computed(() => {
  const s = data.value.averageScore
  if (s === null || s === undefined || s === '') return '—'
  const n = Number(s)
  return Number.isFinite(n) ? (Number.isInteger(n) ? String(n) : n.toFixed(1)) : '—'
})

const statItems = computed(() => [
  {
    key: 'rate',
    title: '提交率',
    value: submissionRate.value,
    suffix: '%',
    precision: 0,
    hint: expectedSubmissions.value
      ? `已交 ${submittedSubmissions.value} · 缺 ${missingSubmissions.value} 人次`
      : '暂无已发布应训日',
  },
  {
    key: 'students',
    title: '学生人数',
    value: studentCount.value,
    precision: 0,
    hint: `${data.value.teamCount ?? 0} 个可见项目`,
  },
  {
    key: 'score',
    title: '路演均分',
    value: scoreText.value === '—' ? 0 : Number(scoreText.value),
    precision: scoreText.value.includes('.') ? 1 : 0,
    hint: roadshowReportCount.value ? `${roadshowReportCount.value} 份报告` : '暂无评分',
  },
  {
    key: 'pending',
    title: '待批改',
    value: pendingReviews.value,
    precision: 0,
    hint: `${missingStudentCount.value} 人有缺交`,
  },
])

/* —— 14 日趋势 —— */
const chartDays = computed(() => {
  const map = new Map()
  for (const row of data.value.dailySubmissions || []) {
    const key = String(row.date || '').slice(0, 10)
    if (key) map.set(key, Number(row.count) || 0)
  }
  const days = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  for (let i = 13; i >= 0; i -= 1) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    const key = formatISODate(d)
    days.push({
      date: key,
      count: map.get(key) || 0,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
    })
  }
  return days
})
const totalSubmissions14d = computed(() => chartDays.value.reduce((s, d) => s + d.count, 0))

const trendOption = computed(() => {
  const labels = chartDays.value.map((d) => d.label)
  const values = chartDays.value.map((d) => d.count)
  return {
    color: [ORANGE],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(18,20,26,0.9)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
    },
    grid: { left: 36, right: 16, top: 28, bottom: 28 },
    xAxis: {
      type: 'category',
      data: labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e4e4e7' } },
      axisTick: { show: false },
      axisLabel: { color: MUTED, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f0f0f2', type: 'dashed' } },
      axisLabel: { color: MUTED, fontSize: 11 },
    },
    series: [
      {
        name: '提交次数',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: values,
        lineStyle: { width: 3, color: ORANGE },
        itemStyle: { color: ORANGE, borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(232,74,28,0.28)' },
            { offset: 1, color: 'rgba(232,74,28,0.02)' },
          ]),
        },
      },
    ],
  }
})

/* —— 结构饼图：中心数字用 HTML 叠层，避免 graphic 偏移 —— */
const structureLegend = computed(() => {
  const ok = Math.max(0, studentCount.value - missingStudentCount.value)
  return [
    { key: 'ok', label: '无缺交学生', value: ok, color: GREEN },
    { key: 'miss', label: '有缺交学生', value: missingStudentCount.value, color: ORANGE },
    { key: 'pending', label: '待批改(份)', value: pendingReviews.value, color: AMBER },
    { key: 'reports', label: '路演报告', value: roadshowReportCount.value, color: BLUE },
  ]
})

const structureOption = computed(() => {
  const pieData = structureLegend.value
    .filter((d) => d.value > 0)
    .map((d) => ({ name: d.label, value: d.value, itemStyle: { color: d.color } }))
  const has = pieData.length > 0
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c}（{d}%）' },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: ['56%', '78%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 3 },
        label: { show: false },
        labelLine: { show: false },
        data: has ? pieData : [{ name: '暂无数据', value: 1, itemStyle: { color: '#e4e4e7' } }],
      },
    ],
  }
})

/* —— 投入排行（头像 + 进度条） —— */
const rankRows = computed(() => {
  const lb = data.value.leaderboards || {}
  let rows = []
  if (rankTab.value === 'submissions') {
    rows = (lb.submissions || [])
      .map((r) => ({
        userId: r.userId,
        name: r.studentName || r.username || '学生',
        value: Number(r.submissionCount) || 0,
        label: `${Number(r.submissionCount) || 0} 次`,
      }))
      .filter((r) => r.value > 0)
  } else if (rankTab.value === 'resources') {
    rows = (lb.resources || [])
      .map((r) => ({
        userId: r.userId,
        name: r.studentName || r.username || '学生',
        value: Number(r.completedCount) || 0,
        label: `${Number(r.completedCount) || 0} 项`,
      }))
      .filter((r) => r.value > 0)
  } else {
    rows = (lb.studyTime || [])
      .map((r) => ({
        userId: r.userId,
        name: r.studentName || r.username || '学生',
        value: Number(r.totalSeconds) || 0,
        label: formatDurationLabel(Number(r.totalSeconds) || 0),
      }))
      .filter((r) => r.value > 0)
  }
  const max = Math.max(1, ...rows.map((r) => r.value), 1)
  return rows.slice(0, 6).map((r) => ({
    ...r,
    pct: Math.max(4, Math.round((r.value / max) * 100)),
  }))
})

/* —— 营期进度仪表 —— */
const campGaugeOption = computed(() => {
  const total = Math.max(1, Number(camp.value.totalDays) || 1)
  const current = Math.min(total, Math.max(0, Number(camp.value.currentDay) || 0))
  const pct = Math.round((current / total) * 100)
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: '90%',
        center: ['50%', '55%'],
        progress: {
          show: true,
          width: 14,
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: ORANGE_SOFT },
              { offset: 1, color: ORANGE },
            ]),
          },
        },
        axisLine: { lineStyle: { width: 14, color: [[1, '#f0f0f2']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: true, offsetCenter: [0, '28%'], color: MUTED, fontSize: 12, fontWeight: 600 },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '-8%'],
          formatter: () => `{a|第 ${current}/${total} 天}\n{b|${pct}%}`,
          rich: {
            a: { fontSize: 20, fontWeight: 800, color: '#18181b', lineHeight: 28 },
            b: { fontSize: 13, color: ORANGE, fontWeight: 700, lineHeight: 22 },
          },
        },
        data: [{ value: pct, name: camp.value.remainingDays != null ? `剩余 ${camp.value.remainingDays} 天` : '营期进度' }],
      },
    ],
  }
})

/* —— 缺交列表 —— */
const missingList = computed(() => {
  const rows = Array.isArray(data.value.missingStudents) ? data.value.missingStudents : []
  return rows
    .map((r) => ({
      userId: r.userId,
      name: r.studentName || r.username || `学生 #${r.userId}`,
      missingDays: Number(r.missingDays) || 0,
    }))
    .filter((r) => r.missingDays > 0)
    .slice(0, 8)
})

/* —— 路演雷达 —— */
const recentScores = computed(() => {
  const rows = Array.isArray(data.value.recentScores) ? data.value.recentScores : []
  return rows.slice(0, 8)
})
const dimensions = computed(() => {
  const rows = Array.isArray(data.value.dimensionStats) ? data.value.dimensionStats : []
  return rows
    .map((r) => ({
      name: dimensionName(r.dimensionCode),
      value: Number(r.deductedPoints) || 0,
      sampleCount: Number(r.sampleCount) || 0,
    }))
    .filter((r) => r.name)
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)
})

const radarOption = computed(() => {
  const dims = dimensions.value
  if (!dims.length) return {}
  const max = Math.max(1, ...dims.map((d) => d.value))
  return {
    tooltip: {},
    radar: {
      indicator: dims.map((d) => ({ name: d.name, max })),
      center: ['50%', '52%'],
      radius: '68%',
      axisName: { color: '#71717a', fontSize: 11, fontWeight: 600 },
      splitArea: {
        areaStyle: {
          color: ['rgba(232,74,28,0.02)', 'rgba(232,74,28,0.05)'],
        },
      },
      axisLine: { lineStyle: { color: '#eceef1' } },
      splitLine: { lineStyle: { color: '#e8eaed' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: dims.map((d) => d.value),
            name: '扣分',
            areaStyle: { color: 'rgba(232,74,28,0.18)' },
            lineStyle: { color: ORANGE, width: 2 },
            itemStyle: { color: ORANGE },
            symbol: 'circle',
            symbolSize: 6,
          },
        ],
      },
    ],
  }
})

function dimensionName(code) {
  const key = String(code || '')
  return DIMENSION_NAMES[key] || DIMENSION_NAMES[key.toLowerCase()] || key || '未知'
}

function formatScore(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function shortDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).slice(0, 10)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatDurationLabel(seconds) {
  const n = Math.max(0, Math.round(Number(seconds) || 0))
  if (!n) return '0 分'
  const h = Math.floor(n / 3600)
  const m = Math.floor((n % 3600) / 60)
  if (h > 0) return m ? `${h}h${m}m` : `${h}h`
  if (m > 0) return `${m} 分`
  return `${n}s`
}

function formatISODate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function initial(name) {
  const s = String(name || '').trim()
  return s ? s.slice(0, 1) : '?'
}

function avatarColor(seed) {
  const s = String(seed ?? '')
  let hash = 0
  for (let i = 0; i < s.length; i += 1) hash = (hash * 31 + s.charCodeAt(i)) >>> 0
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

function isTodoPending(item) {
  const st = String(item?.status || '').toUpperCase()
  // 待审 / 草稿 / 未发布 算「要你处理」；已发布完成则不计
  if (!st) return true
  if (/DONE|CLOSED|COMPLETED|PUBLISHED|已完成|已关闭|已发布/.test(st)) return false
  return true
}

async function loadSideCounts() {
  const teamId = ctx.projectId || ''
  const [certs, todos] = await Promise.all([
    teamId ? fetchTeamCertificates(teamId).catch(() => []) : Promise.resolve([]),
    fetchTeacherAiTodos().catch(() => []),
  ])
  certCount.value = Array.isArray(certs) ? certs.length : 0
  const list = Array.isArray(todos) ? todos : []
  todoPendingCount.value = list.filter(isTodoPending).length
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [analytics] = await Promise.all([
      fetchTeacherAnalytics(),
      loadSideCounts(),
    ])
    data.value = analytics || {}
  } catch (err) {
    error.value = err?.message || '学情数据加载失败'
    data.value = {}
  } finally {
    loading.value = false
  }
}

watch(() => [ctx.projectId, ctx.campId, ctx.loaded], load, { immediate: true })
</script>

<style scoped>
.analytics-page :deep(.teacher-page__head) {
  margin-bottom: 14px;
}
.teacher-muted {
  color: var(--ds-muted);
}
.plan-notice {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}
.analytics-rank-tabs {
  flex-shrink: 0;
}
.panel-empty {
  padding: 36px 16px;
  text-align: center;
  color: var(--ds-muted);
  font-size: 13px;
  font-weight: 600;
}
.panel-empty--action {
  display: grid;
  gap: 12px;
  justify-items: center;
}
.panel-empty--action p {
  margin: 0;
}
.rank-bar {
  height: 8px;
  border-radius: 999px;
  background: #f1f2f4;
  overflow: hidden;
}
.rank-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ffb089, var(--ds-orange, #e84a1c));
  min-width: 4px;
}

.stat-row {
  margin-bottom: 12px !important;
}
.stat-card {
  border-radius: 14px;
  border: 1px solid var(--ds-line);
  height: 100%;
}
.stat-card :deep(.el-statistic__head) {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}
.stat-card :deep(.el-statistic__number) {
  font-size: 28px;
  font-weight: 800;
  color: var(--ds-ink);
}
.stat-suffix {
  font-size: 16px;
  font-weight: 800;
  margin-left: 2px;
}
.stat-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--ds-faint);
  line-height: 1.4;
}

.panel-card {
  border-radius: 16px;
  border: 1px solid var(--ds-line);
  margin-bottom: 12px;
}
.panel-card :deep(.el-card__header) {
  padding: 14px 18px 8px;
  border-bottom: 0;
}
.panel-card :deep(.el-card__body) {
  padding: 4px 12px 16px;
}
.panel-card--fixed {
  height: 100%;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
}
.panel-card--fixed :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
}
.quad-row {
  margin-bottom: 0 !important;
}
.quad-row .el-col {
  margin-bottom: 12px;
}

.panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px 12px;
}
.panel-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--ds-ink);
  line-height: 1.3;
}
.panel-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ds-muted);
  line-height: 1.4;
}
.panel-head__side {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 学情结构：饼图居中 + 侧栏图例 */
.structure-wrap {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(140px, 0.9fr);
  gap: 8px 16px;
  align-items: center;
  min-height: 240px;
  padding: 4px 8px 8px;
}
.structure-chart {
  position: relative;
  min-width: 0;
}
.structure-center {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
  pointer-events: none;
  gap: 2px;
}
.structure-center strong {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  color: var(--ds-ink);
  font-variant-numeric: tabular-nums;
}
.structure-center small {
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.structure-legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}
.structure-legend li {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}
.structure-legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}
.structure-legend b {
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--ds-ink-2);
}

/* 投入 TOP：头像 + 进度 */
.rank-list {
  display: grid;
  gap: 10px;
  padding: 4px 8px 8px;
  min-height: 240px;
  align-content: start;
}
.rank-row {
  display: grid;
  grid-template-columns: 22px 36px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  width: 100%;
  padding: 8px 6px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: background 0.12s;
}
.rank-row:hover {
  background: rgba(15, 23, 42, 0.04);
}
.rank-row__no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  background: #f0f0f2;
  color: #71717a;
}
.rank-row__no[data-rank='1'] {
  background: linear-gradient(145deg, #fbbf24, #f59e0b);
  color: #fff;
}
.rank-row__no[data-rank='2'] {
  background: linear-gradient(145deg, #d1d5db, #9ca3af);
  color: #fff;
}
.rank-row__no[data-rank='3'] {
  background: linear-gradient(145deg, #fdba74, #ea580c);
  color: #fff;
}
.rank-row__main {
  min-width: 0;
  display: grid;
  gap: 6px;
}
.rank-row__meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.rank-row__meta strong {
  font-size: 13px;
  font-weight: 750;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rank-row__meta b {
  flex: none;
  font-size: 12px;
  font-weight: 800;
  color: var(--ds-orange-deep);
  font-variant-numeric: tabular-nums;
}
.rank-row :deep(.el-progress__outer) {
  background: #f0f0f2;
}

.miss-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 4px 6px 8px;
  min-height: 240px;
  align-content: start;
}
.miss-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #fffaf8;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
}
.miss-item:hover {
  border-color: rgba(232, 74, 28, 0.35);
  box-shadow: 0 8px 18px rgba(18, 20, 26, 0.06);
  transform: translateY(-1px);
}
.miss-item__text {
  min-width: 0;
  display: grid;
  gap: 6px;
}
.miss-item__text strong {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score-list {
  display: grid;
  gap: 8px;
  padding: 8px 4px;
}
.score-list__item {
  display: grid;
  grid-template-columns: auto 64px 1fr;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--ds-line);
  background: #fafbfc;
  font-size: 12px;
}
.score-list__item em {
  font-style: normal;
  color: var(--ds-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.score-only {
  display: grid;
  place-items: center;
  min-height: 220px;
}

.side-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  margin-bottom: 12px;
  padding: 0;
  overflow: hidden;
}
.side-actions__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
}
.side-actions__item + .side-actions__item {
  border-left: 1px solid var(--ds-line);
}
.side-actions__item strong {
  display: block;
  font-size: 14px;
  font-weight: 800;
}
.side-actions__item p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ds-muted);
  line-height: 1.4;
}
@media (max-width: 720px) {
  .side-actions {
    grid-template-columns: 1fr;
  }
  .side-actions__item + .side-actions__item {
    border-left: 0;
    border-top: 1px solid var(--ds-line);
  }
}

.quiet-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin-top: 4px;
  padding: 4px 2px 8px;
}
.quiet-links a {
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-faint);
  text-decoration: none;
}
.quiet-links a:hover {
  color: var(--ds-orange-deep);
}

@media (max-width: 768px) {
  .miss-grid {
    grid-template-columns: 1fr;
  }
  .structure-wrap {
    grid-template-columns: 1fr;
  }
  .structure-legend {
    grid-template-columns: 1fr 1fr;
    gap: 10px 14px;
  }
}
</style>
