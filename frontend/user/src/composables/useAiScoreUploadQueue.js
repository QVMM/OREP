import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getAiScoreUploadTasks } from '../utils/aiScoreUpload'

const POLL_INTERVAL_MS = 3000
const MAX_CONSECUTIVE_FAILURES = 2
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled'])

function normalizeStatus(status) {
  return String(status || '').trim().toLowerCase()
}

function isTerminalStatus(status) {
  return TERMINAL_STATUSES.has(normalizeStatus(status))
}

function createUploadedTask(session) {
  const now = new Date().toISOString()
  const sessionId = session.sessionId
  const status = session.status || 'queued'
  const fileSize = Number(session.fileSize ?? session.videoFileSize ?? session.videoSize ?? 0)

  return {
    ...session,
    sessionId,
    sessionNo: session.sessionNo || String(sessionId),
    fileName: session.fileName || session.videoFileName || session.originalFileName || '未命名视频',
    fileSize: Number.isFinite(fileSize) && fileSize >= 0 ? fileSize : 0,
    projectId: session.projectId ?? null,
    teamId: session.teamId ?? session.projectTeamId ?? null,
    teamName: session.teamName || session.projectTeamName || '',
    trackName: session.trackName || session.track || '',
    status,
    currentStage: session.currentStage || status,
    progressPercent: Math.max(0, Math.min(100, Number(session.progressPercent) || 0)),
    useHistoryMemory: session.useHistoryMemory ?? false,
    juryEnabled: session.juryEnabled ?? false,
    reportId: session.reportId ?? null,
    errorMessage: session.errorMessage || '',
    createdAt: session.createdAt || now,
    updatedAt: session.updatedAt || now
  }
}

export function useAiScoreUploadQueue() {
  const tasks = ref([])
  const loading = ref(true)
  const syncing = ref(false)
  const error = ref('')
  const hasActiveTasks = computed(() => tasks.value.some(task => !isTerminalStatus(task?.status)))
  let timer = null
  let requestInFlight = false
  let consecutiveFailures = 0
  let disposed = false
  let trailingRefreshRequested = false
  let trailingRefreshSilent = true
  let localRevision = 0

  function clearScheduledRefresh() {
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
  }

  function schedule() {
    clearScheduledRefresh()
    if (disposed || document.hidden || !hasActiveTasks.value || consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) return

    timer = window.setTimeout(() => {
      timer = null
      void refresh({ silent: true })
    }, POLL_INTERVAL_MS)
  }

  async function refresh({ silent = false } = {}) {
    if (disposed) return
    if (requestInFlight) {
      trailingRefreshRequested = true
      if (!silent) trailingRefreshSilent = false
      return
    }

    requestInFlight = true
    const revisionAtRequestStart = localRevision
    if (silent) syncing.value = true
    else loading.value = true

    try {
      const data = await getAiScoreUploadTasks()
      if (disposed) return
      if (revisionAtRequestStart === localRevision) {
        tasks.value = Array.isArray(data) ? data : []
      }
      error.value = ''
      consecutiveFailures = 0
    } catch (requestError) {
      if (disposed) return
      consecutiveFailures += 1
      if (tasks.value.length === 0) {
        error.value = requestError?.message || '获取上传评分任务失败，请稍后重试。'
      }
    } finally {
      requestInFlight = false
      if (disposed) return
      if (silent) syncing.value = false
      else loading.value = false
      if (trailingRefreshRequested) {
        const trailingSilent = trailingRefreshSilent
        trailingRefreshRequested = false
        trailingRefreshSilent = true
        void refresh({ silent: trailingSilent })
        return
      }
      schedule()
    }
  }

  function mergeUploadedSession(session = {}) {
    if (disposed || session.sessionId === undefined || session.sessionId === null || session.sessionId === '') return

    const uploadedTask = createUploadedTask(session)
    localRevision += 1
    tasks.value = [
      uploadedTask,
      ...tasks.value.filter(task => String(task?.sessionId) !== String(uploadedTask.sessionId))
    ]
    error.value = ''
    schedule()
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      clearScheduledRefresh()
      return
    }
    void refresh({ silent: true })
  }

  function handleWindowFocus() {
    if (!document.hidden) void refresh({ silent: true })
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleWindowFocus)
    void refresh()
  })

  onUnmounted(() => {
    disposed = true
    trailingRefreshRequested = false
    trailingRefreshSilent = true
    clearScheduledRefresh()
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('focus', handleWindowFocus)
  })

  return {
    tasks,
    loading,
    syncing,
    error,
    hasActiveTasks,
    refresh,
    mergeUploadedSession
  }
}
