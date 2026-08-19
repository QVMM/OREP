<template>
  <div
    ref="chartRef"
    class="weekly-learning-chart"
    role="img"
    :aria-label="ariaLabel"
  ></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  points: {
    type: Array,
    default: () => []
  },
  scaleMinutes: {
    type: Number,
    default: 30
  },
  ariaLabel: {
    type: String,
    default: '近一周学习时长'
  }
})

const chartRef = ref(null)
let chart = null
let resizeObserver = null

function renderChart() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })

  const maxValue = Math.max(30, Number(props.scaleMinutes || 30))
  const middleValue = maxValue / 2

  const barData = props.points.map((point) => {
    const minutes = Number((Number(point.barRatio || 0) * maxValue).toFixed(2))
    return {
      value: point.isFuture ? 0 : minutes,
      itemStyle: {
        color: point.isFuture
          ? 'rgba(207, 213, 222, 0.35)'
          : point.isToday
            ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#ff6a38' },
                { offset: 1, color: '#e84312' }
              ])
            : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(255, 90, 42, 0.72)' },
                { offset: 1, color: 'rgba(255, 90, 42, 0.38)' }
              ]),
        borderRadius: [4, 4, 2, 2]
      }
    }
  })

  const lineData = props.points.map((point) => (
    point.isFuture
      ? null
      : Number((Number(point.barRatio || 0) * maxValue).toFixed(2))
  ))

  chart.setOption({
    animationDuration: 520,
    animationEasing: 'cubicOut',
    grid: { left: 40, right: 12, top: 28, bottom: 44, containLabel: false },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(18, 20, 26, 0.92)',
      borderWidth: 0,
      padding: [8, 10],
      textStyle: { color: '#fff', fontSize: 12 },
      axisPointer: {
        type: 'shadow',
        shadowStyle: { color: 'rgba(255, 85, 38, 0.06)' }
      },
      formatter: (items) => {
        const index = items?.[0]?.dataIndex ?? 0
        const point = props.points[index]
        return point ? `${point.dateLabel} · ${point.valueLabel}` : ''
      }
    },
    xAxis: {
      type: 'category',
      data: props.points.map(point => point.dateLabel),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d7dce4' } },
      axisLabel: {
        interval: 0,
        margin: 10,
        formatter: (value, index) => {
          const point = props.points[index]
          const week = point?.isToday ? '今天' : (point?.weekday || '')
          return `{date|${value}}\n{week|${week}}`
        },
        rich: {
          date: { color: '#384050', fontSize: 11, fontWeight: 650, lineHeight: 17 },
          week: { color: '#9aa3b2', fontSize: 10, lineHeight: 15 }
        }
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: maxValue,
      interval: middleValue,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: {
        color: '#98a1b0',
        fontSize: 10,
        margin: 10,
        formatter: value => `${Math.round(value)} 分`
      },
      splitLine: {
        lineStyle: {
          color: '#e6eaef',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '学习时长',
        type: 'bar',
        barWidth: '42%',
        barMaxWidth: 28,
        data: barData,
        z: 2,
        emphasis: {
          itemStyle: {
            shadowBlur: 8,
            shadowColor: 'rgba(255, 85, 38, 0.22)'
          }
        }
      },
      {
        name: '趋势',
        type: 'line',
        data: lineData,
        smooth: 0.28,
        connectNulls: false,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 6,
        z: 3,
        lineStyle: { width: 2.2, color: '#ff5526' },
        itemStyle: {
          color: '#fff',
          borderColor: '#ff5526',
          borderWidth: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255, 85, 38, 0.10)' },
            { offset: 1, color: 'rgba(255, 85, 38, 0)' }
          ])
        },
        emphasis: { scale: 1.2 }
      }
    ]
  }, true)
}

function handleResize() {
  if (!chart || !chartRef.value) return
  chart.resize({ width: 'auto', height: 'auto' })
}

onMounted(() => {
  renderChart()
  if (typeof ResizeObserver !== 'undefined' && chartRef.value) {
    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(chartRef.value)
  }
  window.addEventListener('resize', handleResize)
})

watch(() => [props.points, props.scaleMinutes], renderChart, { deep: true })

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.weekly-learning-chart {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 168px;
  height: 100%;
  box-sizing: border-box;
}
</style>
