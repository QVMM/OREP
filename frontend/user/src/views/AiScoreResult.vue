<template>
  <div class="ai-score-redirect">正在进入新版 AI 评分报告...</div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  if (route.params.sessionId) {
    router.replace(`/ai-score/report/${route.params.sessionId}/overview`)
    return
  }
  if (route.params.reportId) {
    router.replace(`/ai-score/report-id/${route.params.reportId}/overview`)
    return
  }
  if (route.params.meetingId) {
    router.replace(`/ai-score/${route.params.meetingId}/overview`)
  }
})
</script>

<style scoped>
.ai-score-redirect {
  min-height: calc(100vh - var(--header-height));
  display: grid;
  place-items: center;
  color: #66728a;
  background-color: #ffffff;
  background-image: none;
}
</style>
