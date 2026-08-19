<template>
  <div ref="el" class="base-echart" :style="{ height }" role="img" :aria-label="ariaLabel" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { init, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, GaugeChart, LineChart, PieChart, RadarChart } from 'echarts/charts'
import {
  DatasetComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  RadarComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { LabelLayout, UniversalTransition } from 'echarts/features'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  RadarChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  RadarComponent,
  GraphicComponent,
  DatasetComponent,
  LabelLayout,
  UniversalTransition,
])

const props = defineProps({
  option: { type: Object, default: () => ({}) },
  height: { type: String, default: '280px' },
  ariaLabel: { type: String, default: '图表' },
  loading: { type: Boolean, default: false },
})

const el = ref(null)
const chart = shallowRef(null)
let ro = null

function render() {
  if (!el.value) return
  if (!chart.value) {
    chart.value = init(el.value, undefined, { renderer: 'canvas' })
  }
  if (props.loading) {
    chart.value.showLoading('default', {
      text: '',
      color: '#e84a1c',
      maskColor: 'rgba(255,255,255,0.6)',
    })
  } else {
    chart.value.hideLoading()
  }
  chart.value.setOption(props.option || {}, { notMerge: true })
}

function resize() {
  chart.value?.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
  if (typeof ResizeObserver !== 'undefined' && el.value) {
    ro = new ResizeObserver(() => resize())
    ro.observe(el.value)
  }
})

watch(
  () => [props.option, props.loading, props.height],
  () => render(),
  { deep: true }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  ro?.disconnect()
  chart.value?.dispose()
  chart.value = null
})

defineExpose({ resize, getInstance: () => chart.value })
</script>

<style scoped>
.base-echart {
  width: 100%;
  min-height: 120px;
}
</style>
