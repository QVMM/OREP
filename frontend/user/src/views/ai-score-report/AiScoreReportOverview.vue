<script setup>
/**
 * Legacy overview entry — result is the editorial "一张纸" page.
 * Keep this file so any stale deep imports still land on /result.
 */
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const { sessionId, reportId, meetingId } = route.params
  if (sessionId) {
    router.replace(`/ai-score/report/${sessionId}/result`)
    return
  }
  if (reportId) {
    router.replace(`/ai-score/report-id/${reportId}/result`)
    return
  }
  if (meetingId) {
    router.replace(`/ai-score/${meetingId}/result`)
    return
  }
  router.replace({ path: route.path.replace(/\/overview\/?$/, '/result') })
})
</script>

<template>
  <div class="overview-redirect" aria-hidden="true" />
</template>
