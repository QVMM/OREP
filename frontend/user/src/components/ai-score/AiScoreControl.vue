<template>
  <div class="ai-score-control">
    <el-button :type="buttonType" :loading="loading" @click="handleClick">
      {{ buttonText }}
    </el-button>
    <span v-if="session?.sessionNo" class="session-chip">{{ session.sessionNo }}</span>

    <AiScoreStartDialog
      v-model="startDialogVisible"
      v-model:use-history-memory="useHistoryMemory"
      v-model:jury-enabled="juryEnabled"
      :loading="loading"
      :source-label="sourceLabel"
      :project-name="projectName"
      :team-name="teamName"
      :track-name="trackName"
      @confirm="createAndStart"
    />
    <AiScoreRunningDialog
      v-model="runningDialogVisible"
      :loading="loading"
      :session="session"
      @view="openReport"
      @finish-partial="openReport"
      @cancel-session="cancelCurrentSession"
      @restart="confirmRestart"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AiScoreStartDialog from './AiScoreStartDialog.vue'
import AiScoreRunningDialog from './AiScoreRunningDialog.vue'
import {
  cancelAiScoreSession,
  createAiScoreSession,
  restartAiScoreSession,
  startAiScoreSession
} from '../../utils/aiScoreSession'

const props = defineProps({
  meetingId: { type: [String, Number], default: null },
  projectId: { type: [String, Number], default: null },
  teamId: { type: [String, Number], default: null },
  recordingId: { type: [String, Number], default: null },
  trackId: { type: String, default: '' },
  trackName: { type: String, default: '新一代信息技术赛道' },
  projectName: { type: String, default: '' },
  teamName: { type: String, default: '' },
  sourceType: { type: String, default: 'meeting_recording' },
  sourceLabel: { type: String, default: '路演录制' }
})

const emit = defineEmits(['session-created', 'session-updated'])
const router = useRouter()
const startDialogVisible = ref(false)
const runningDialogVisible = ref(false)
const loading = ref(false)
const session = ref(null)
const useHistoryMemory = ref(true)
const juryEnabled = ref(false)

const isRunning = computed(() => ['created', 'scoring', 'processing'].includes(session.value?.status))
const buttonType = computed(() => isRunning.value ? 'warning' : 'primary')
const buttonText = computed(() => {
  if (session.value?.status === 'scoring') return 'AI评分中'
  if (session.value?.status === 'created') return '继续AI评分'
  if (session.value?.status === 'completed') return '查看AI报告'
  return 'AI评分'
})

function handleClick() {
  if (session.value?.status === 'completed') {
    openReport()
    return
  }
  if (isRunning.value) {
    runningDialogVisible.value = true
    return
  }
  startDialogVisible.value = true
}

async function createAndStart() {
  loading.value = true
  try {
    const created = await createAiScoreSession({
      sourceType: props.sourceType,
      meetingId: props.meetingId ? Number(props.meetingId) : null,
      projectId: props.projectId ? Number(props.projectId) : null,
      teamId: props.teamId ? Number(props.teamId) : null,
      recordingId: props.recordingId ? Number(props.recordingId) : null,
      trackId: props.trackId || props.trackName,
      trackName: props.trackName,
      useHistoryMemory: useHistoryMemory.value,
      juryEnabled: false
    })
    session.value = created
    emit('session-created', created)
    if (created?.cached) {
      ElMessage.info(created.message || '检测到相同评分输入，已返回已有报告')
      startDialogVisible.value = false
      openReport()
      return
    }
    const started = await startAiScoreSession(created.sessionId)
    session.value = started
    emit('session-updated', started)
    startDialogVisible.value = false
    runningDialogVisible.value = true
    ElMessage.success('AI评分任务已创建')
  } catch (err) {
    ElMessage.error(err?.message || 'AI评分任务创建失败')
  } finally {
    loading.value = false
  }
}

async function cancelCurrentSession() {
  if (!session.value?.sessionId) return
  loading.value = true
  try {
    session.value = await cancelAiScoreSession(session.value.sessionId)
    emit('session-updated', session.value)
    runningDialogVisible.value = false
    ElMessage.success('已终止当前评分')
  } catch (err) {
    ElMessage.error(err?.message || '终止评分失败')
  } finally {
    loading.value = false
  }
}

async function confirmRestart() {
  if (!session.value?.sessionId) return
  try {
    await ElMessageBox.confirm('重新开始会废弃当前评分任务进度，确认继续？', '重新开始评分', {
      confirmButtonText: '重新开始',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  loading.value = true
  try {
    session.value = await restartAiScoreSession(session.value.sessionId)
    emit('session-updated', session.value)
    runningDialogVisible.value = false
    startDialogVisible.value = true
  } catch (err) {
    ElMessage.error(err?.message || '重新开始评分失败')
  } finally {
    loading.value = false
  }
}

function openReport() {
  if (session.value?.sessionId) {
    router.push(`/ai-score/report/${session.value.sessionId}`)
  } else if (props.meetingId) {
    router.push(`/ai-score/${props.meetingId}`)
  }
}
</script>

<style scoped>
.ai-score-control { display: inline-flex; align-items: center; gap: 8px; }
.session-chip { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #667085; }
</style>
