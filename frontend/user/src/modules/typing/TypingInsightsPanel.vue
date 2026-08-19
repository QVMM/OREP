<template>
  <section class="ti" aria-label="练习数据与历史">
    <!-- KPI 条 -->
    <div class="ti-kpis" role="list">
      <div v-for="item in kpis" :key="item.key" class="ti-kpi" role="listitem">
        <span class="ti-kpi__label">{{ item.label }}</span>
        <strong class="ti-kpi__value">
          {{ item.value }}
          <small v-if="item.unit">{{ item.unit }}</small>
        </strong>
        <em v-if="item.hint" class="ti-kpi__hint">{{ item.hint }}</em>
      </div>
    </div>

    <div class="ti-body">
      <!-- 趋势图 -->
      <div class="ti-panel ti-trend">
        <header class="ti-panel__head">
          <div>
            <h3>每日速度趋势</h3>
            <p>近 {{ trendDays }} 天 · 按日均 CPM</p>
          </div>
          <span v-if="hasTrendData" class="ti-panel__meta">
            峰值 <b>{{ peakCpm || '—' }}</b>
          </span>
        </header>

        <div v-if="hasTrendData" ref="chartRef" class="ti-chart" role="img" :aria-label="chartAria" />
        <div v-else class="ti-empty">
          <p class="ti-empty__title">还没有足够的练习数据</p>
          <p class="ti-empty__desc">完成几场练习后，这里会显示每日速度走势。</p>
        </div>
      </div>

      <!-- 历史记录 -->
      <div class="ti-panel ti-history">
        <header class="ti-panel__head">
          <div>
            <h3>最近练习</h3>
            <p>{{ sessions.length ? `共 ${sessions.length} 条最近记录` : '暂无记录' }}</p>
          </div>
        </header>

        <ul v-if="sessions.length" class="ti-list">
          <li v-for="row in sessions" :key="row.id">
            <div class="ti-list__main">
              <span class="ti-list__mode" :data-mode="row.mode">
                {{ row.mode === 'ranked' ? '排位' : row.mode === 'code' ? '代码' : '练习' }}
              </span>
              <strong class="ti-list__cpm">{{ row.cpm }}<small>CPM</small></strong>
              <span class="ti-list__acc">{{ formatAcc(row.accuracy) }}%</span>
            </div>
            <div class="ti-list__meta">
              <span>{{ formatWhen(row.createdAt) }}</span>
              <span>{{ formatDuration(row.elapsedMs) }}</span>
            </div>
          </li>
        </ul>
        <div v-else class="ti-empty ti-empty--compact">
          <p class="ti-empty__title">还没有历史记录</p>
          <p class="ti-empty__desc">练完一场后，速度与正确率会出现在这里。</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  /** 服务端 /me/stats 或合并后的洞察数据 */
  stats: {
    type: Object,
    default: () => ({})
  },
  /** 本地兜底趋势 */
  localTrend: {
    type: Array,
    default: () => []
  },
  /** 本地兜底会话 */
  localSessions: {
    type: Array,
    default: () => []
  }
})

const chartRef = ref(null)
let chart = null
let resizeObserver = null

const dailyTrend = computed(() => {
  const remote = props.stats?.dailyTrend
  if (Array.isArray(remote) && remote.length) return remote
  return props.localTrend || []
})

const sessions = computed(() => {
  const remote = props.stats?.recentSessions
  if (Array.isArray(remote) && remote.length) return remote.slice(0, 10)
  return (props.localSessions || []).slice(0, 10)
})

const hasTrendData = computed(() =>
  dailyTrend.value.some(d => Number(d.sessionCount || 0) > 0 || Number(d.avgCpm || 0) > 0)
)

const trendDays = computed(() => Math.max(7, dailyTrend.value.length || 14))

const peakCpm = computed(() => {
  const nums = dailyTrend.value.map(d => Number(d.bestCpm || d.avgCpm || 0))
  return nums.length ? Math.max(0, ...nums) : 0
})

const avgCpm = computed(() => {
  const s = props.stats || {}
  if (Number(s.avgCpm7d) > 0) return Number(s.avgCpm7d)
  if (Number(s.avgCpm) > 0) return Number(s.avgCpm)
  const active = dailyTrend.value.filter(d => Number(d.sessionCount) > 0)
  if (!active.length) return 0
  return Math.round(active.reduce((sum, d) => sum + Number(d.avgCpm || 0), 0) / active.length)
})

const bestCpm = computed(() => {
  const s = props.stats || {}
  const fromStats = Math.max(Number(s.bestCpm) || 0, Number(s.bestPracticeCpm) || 0, Number(s.bestRankedCpm) || 0)
  return Math.max(fromStats, peakCpm.value)
})

const avgAccuracy = computed(() => {
  const s = props.stats || {}
  if (s.avgAccuracy != null && Number(s.avgAccuracy) > 0) {
    return Math.round(Number(s.avgAccuracy) * 10) / 10
  }
  const active = dailyTrend.value.filter(d => Number(d.sessionCount) > 0)
  if (!active.length) return 0
  return Math.round(
    (active.reduce((sum, d) => sum + Number(d.avgAccuracy || 0), 0) / active.length) * 10
  ) / 10
})

const sessionCount = computed(() => {
  const s = props.stats || {}
  return Number(s.sessionCount || s.practiceCount || 0)
    || sessions.value.length
    || dailyTrend.value.reduce((sum, d) => sum + Number(d.sessionCount || 0), 0)
})

const totalDurationLabel = computed(() => {
  const ms = Number(props.stats?.totalElapsedMs || 0)
    || dailyTrend.value.reduce((sum, d) => sum + Number(d.totalElapsedMs || 0), 0)
  return formatDuration(ms)
})

const kpis = computed(() => [
  {
    key: 'avg',
    label: '近均速度',
    value: avgCpm.value || '—',
    unit: avgCpm.value ? 'CPM' : '',
    hint: avgCpm.value ? '近 7 日优先' : '练过才有'
  },
  {
    key: 'best',
    label: '最高速度',
    value: bestCpm.value || '—',
    unit: bestCpm.value ? 'CPM' : '',
    hint: '历史峰值'
  },
  {
    key: 'acc',
    label: '平均正确率',
    value: avgAccuracy.value || '—',
    unit: avgAccuracy.value ? '%' : '',
    hint: '全部练习'
  },
  {
    key: 'time',
    label: '累计练习',
    value: sessionCount.value || '—',
    unit: sessionCount.value ? '场' : '',
    hint: totalDurationLabel.value !== '0 秒' ? totalDurationLabel.value : '时长累计'
  }
])

const chartAria = computed(() =>
  `近 ${trendDays.value} 天打字速度趋势，峰值 ${peakCpm.value || 0} CPM`
)

function formatAcc(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return Math.round(n * 10) / 10
}

function formatDuration(ms) {
  const totalSec = Math.max(0, Math.round(Number(ms || 0) / 1000))
  if (totalSec < 60) return `${totalSec} 秒`
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (m < 60) return s ? `${m} 分 ${s} 秒` : `${m} 分钟`
  const h = Math.floor(m / 60)
  const rm = m % 60
  return rm ? `${h} 小时 ${rm} 分` : `${h} 小时`
}

function formatWhen(iso) {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return '—'
  const d = new Date(t)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const yest = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)
  const isYest = d.toDateString() === yest.toDateString()
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  if (sameDay) return `今天 ${hm}`
  if (isYest) return `昨天 ${hm}`
  return `${d.getMonth() + 1}/${d.getDate()} ${hm}`
}

function shortDateLabel(dateKey) {
  const m = String(dateKey || '').match(/(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return dateKey || ''
  return `${Number(m[2])}/${Number(m[3])}`
}

function renderChart() {
  if (!chartRef.value || !hasTrendData.value) return
  if (!chart) chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })

  const points = dailyTrend.value
  const avgData = points.map(p => (Number(p.sessionCount) > 0 ? Number(p.avgCpm || 0) : null))
  const bestData = points.map(p => (Number(p.sessionCount) > 0 ? Number(p.bestCpm || 0) : null))
  const maxY = Math.max(40, ...points.map(p => Math.max(Number(p.bestCpm || 0), Number(p.avgCpm || 0))))

  chart.setOption({
    animationDuration: 480,
    animationEasing: 'cubicOut',
    grid: { left: 36, right: 12, top: 28, bottom: 28, containLabel: false },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 24, 39, 0.92)',
      borderWidth: 0,
      padding: [8, 10],
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (items) => {
        const idx = items?.[0]?.dataIndex ?? 0
        const p = points[idx]
        if (!p) return ''
        if (!Number(p.sessionCount)) return `${shortDateLabel(p.date)} · 未练习`
        return [
          `${shortDateLabel(p.date)} · ${p.sessionCount} 场`,
          `日均 ${p.avgCpm} CPM`,
          `最高 ${p.bestCpm} CPM`,
          `正确率 ${formatAcc(p.avgAccuracy)}%`
        ].join('<br/>')
      }
    },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 6,
      textStyle: { color: '#6b7280', fontSize: 11 }
    },
    xAxis: {
      type: 'category',
      data: points.map(p => shortDateLabel(p.date)),
      boundaryGap: false,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e8eaed' } },
      axisLabel: {
        color: '#9ca3af',
        fontSize: 10,
        interval: points.length > 10 ? 1 : 0
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: Math.ceil(maxY / 20) * 20,
      splitNumber: 3,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: '#9ca3af', fontSize: 10 },
      splitLine: { lineStyle: { color: '#eef0f3', type: 'dashed' } }
    },
    series: [
      {
        name: '日均',
        type: 'line',
        data: avgData,
        smooth: 0.35,
        connectNulls: false,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2.2, color: '#e5481d' },
        itemStyle: { color: '#fff', borderColor: '#e5481d', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(229, 72, 29, 0.14)' },
            { offset: 1, color: 'rgba(229, 72, 29, 0)' }
          ])
        }
      },
      {
        name: '最高',
        type: 'line',
        data: bestData,
        smooth: 0.35,
        connectNulls: false,
        showSymbol: false,
        lineStyle: { width: 1.4, color: 'rgba(17, 24, 39, 0.22)', type: 'dashed' },
        itemStyle: { color: 'rgba(17, 24, 39, 0.35)' }
      }
    ]
  }, true)
}

function bindResize() {
  resizeObserver?.disconnect()
  if (typeof ResizeObserver === 'undefined' || !chartRef.value) return
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartRef.value)
}

async function refreshChart() {
  if (!hasTrendData.value) {
    chart?.clear()
    return
  }
  await nextTick()
  renderChart()
  bindResize()
}

onMounted(() => {
  refreshChart()
})

watch(() => dailyTrend.value, () => {
  refreshChart()
}, { deep: true })

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.ti {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.ti-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.ti-kpi {
  padding: 14px 14px 12px;
  border: 1px solid #e8eaed;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  min-width: 0;
}

.ti-kpi__label {
  display: block;
  color: #6b7280;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.02em;
}

.ti-kpi__value {
  display: block;
  margin-top: 6px;
  color: #111827;
  font-size: 24px;
  font-weight: 760;
  letter-spacing: -0.04em;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.ti-kpi__value small {
  margin-left: 3px;
  color: #6b7280;
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0;
}

.ti-kpi__hint {
  display: block;
  margin-top: 4px;
  color: #9ca3af;
  font-size: 10.5px;
  font-style: normal;
  font-weight: 500;
}

.ti-body {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(240px, 0.9fr);
  gap: 12px;
  align-items: stretch;
}

.ti-panel {
  box-sizing: border-box;
  min-width: 0;
  min-height: 280px;
  padding: 14px 14px 12px;
  border: 1px solid #e8eaed;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  display: flex;
  flex-direction: column;
}

.ti-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.ti-panel__head h3 {
  margin: 0;
  color: #111827;
  font-size: 14px;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.ti-panel__head p {
  margin: 3px 0 0;
  color: #9ca3af;
  font-size: 11px;
  line-height: 1.35;
}

.ti-panel__meta {
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  padding-top: 2px;
}

.ti-panel__meta b {
  color: #e5481d;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.ti-chart {
  flex: 1;
  width: 100%;
  min-height: 200px;
}

.ti-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 6px;
  padding: 20px 4px;
  min-height: 180px;
}

.ti-empty--compact {
  min-height: 140px;
}

.ti-empty__title {
  margin: 0;
  color: #111827;
  font-size: 13px;
  font-weight: 700;
}

.ti-empty__desc {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.55;
  max-width: 28ch;
}

.ti-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: auto;
  max-height: 240px;
  flex: 1;
}

.ti-list li {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 8px;
  border-radius: 10px;
  transition: background 0.15s ease;
}

.ti-list li:hover {
  background: #f8f9fb;
}

.ti-list__main {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.ti-list__mode {
  flex: none;
  min-width: 36px;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 750;
  text-align: center;
  color: #4b5563;
  background: #f3f4f6;
}

.ti-list__mode[data-mode='ranked'] {
  color: #c2410c;
  background: #fff7ed;
}

.ti-list__cpm {
  color: #111827;
  font-size: 16px;
  font-weight: 760;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.ti-list__cpm small {
  margin-left: 2px;
  color: #9ca3af;
  font-size: 10px;
  font-weight: 650;
}

.ti-list__acc {
  margin-left: auto;
  color: #6b7280;
  font-size: 12px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
}

.ti-list__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding-left: 46px;
  color: #9ca3af;
  font-size: 11px;
}

@media (max-width: 860px) {
  .ti-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ti-body {
    grid-template-columns: 1fr;
  }

  .ti-panel {
    min-height: 0;
  }

  .ti-list {
    max-height: none;
  }
}

@media (max-width: 480px) {
  .ti-kpi__value {
    font-size: 20px;
  }
}
</style>
