<template>
  <div
    ref="chartRef"
    class="home-score-radar"
    role="img"
    :aria-label="ariaLabel"
  ></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dimensions: {
    type: Array,
    default: () => []
  }
})

const chartRef = ref(null)
let chart = null
let resizeObserver = null

const ariaLabel = 'AI 路演评分维度雷达图'

function renderChart() {
  if (!chartRef.value || !props.dimensions.length) return
  if (!chart) chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })

  chart.setOption({
    animationDuration: 560,
    animationEasing: 'cubicOut',
    radar: {
      center: ['50%', '54%'],
      radius: '58%',
      splitNumber: 4,
      shape: 'polygon',
      indicator: props.dimensions.map(item => ({
        name: item.label,
        max: 100
      })),
      axisName: {
        color: '#4a5363',
        fontSize: 11,
        fontWeight: 600,
        lineHeight: 14,
        formatter: (name) => {
          const dim = props.dimensions.find(item => item.label === name)
          const score = dim?.shortValue ?? ''
          return `{name|${name}}\n{score|${score}}`
        },
        rich: {
          name: { color: '#4a5363', fontSize: 11, fontWeight: 600, lineHeight: 15 },
          score: { color: '#ff5526', fontSize: 11, fontWeight: 700, lineHeight: 14 }
        }
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(255, 90, 42, 0.03)', 'rgba(255,255,255,.95)', 'rgba(255, 90, 42, 0.04)', 'rgba(255,255,255,.98)']
        }
      },
      splitLine: {
        lineStyle: { color: 'rgba(255, 90, 42, 0.16)', width: 1 }
      },
      axisLine: {
        lineStyle: { color: 'rgba(72, 82, 98, 0.18)' }
      }
    },
    series: [{
      type: 'radar',
      silent: true,
      data: [{
        value: props.dimensions.map(item => item.percent),
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#ff5a2a', width: 2.2 },
        itemStyle: {
          color: '#fff',
          borderColor: '#ff5a2a',
          borderWidth: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255, 90, 42, 0.42)' },
            { offset: 1, color: 'rgba(255, 90, 42, 0.12)' }
          ])
        }
      }]
    }]
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

watch(() => props.dimensions, renderChart, { deep: true })

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.home-score-radar {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  min-height: 200px;
  height: 100%;
  box-sizing: border-box;
}
</style>
