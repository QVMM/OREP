<template>
  <div class="report-layout">
    <section v-if="report.loading.value" class="state-view">
      <strong>正在载入评分报告</strong>
      <p>系统正在读取评分、证据、表达、现场呈现和改进建议。</p>
    </section>

    <section v-else-if="report.error.value" class="state-view">
      <strong>{{ report.error.value }}</strong>
      <p>当前会议暂未生成 AI 评分结果。</p>
      <button type="button" @click="report.loadResult">重新加载</button>
    </section>

    <section v-else-if="report.isSessionProgressView.value" class="state-view">
      <strong>{{ report.sessionStatus.value === 'failed' ? 'AI分析未启动' : 'AI 评分进行中' }}</strong>
      <p>当前阶段：{{ report.sessionStage.value || '-' }}，进度 {{ report.sessionProgress.value }}%</p>
      <p v-if="report.sessionErrorMessage.value">{{ report.sessionErrorMessage.value }}</p>
    </section>

    <RouterView v-else />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { provideAiScoreReportContext, useAiScoreReport } from '../../composables/useAiScoreReport'

const report = useAiScoreReport()
provideAiScoreReportContext(report)

onMounted(() => {
  report.loadAvailableTeams()
  report.loadResult()
})
</script>

<style scoped>
.report-layout {
  box-sizing: border-box;
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

/* RouterView 出口：把定高与 flex 传给报告壳层 */
.report-layout > :deep(.report-shell),
.report-layout > :deep(.state-view) {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  width: 100%;
}

.state-view {
  min-height: calc(100vh - var(--workspace-header-height, var(--header-height, 64px)));
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  padding: 32px;
  color: #0d1b3d;
  text-align: center;
}

.state-view strong {
  font-size: 22px;
}

.state-view p {
  margin: 0;
  color: #66728a;
}

.state-view button {
  height: 38px;
  padding: 0 16px;
  border: 0;
  border-radius: 8px;
  background: #f15a24;
  color: #fff;
  font-weight: 800;
}
</style>
