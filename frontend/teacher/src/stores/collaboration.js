import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  acceptTeacherCollaborationRequest,
  declineTeacherCollaborationRequest,
  fetchTeacherCollaborationItems,
  fetchTeacherCollaborationSummary,
  fetchTeacherCollaborationTeams,
  fetchTeacherReviewDetail,
  publishTeacherCollaborationTask,
  submitTeacherCollaborationReview,
  withdrawTeacherCollaborationRequest,
} from '../services/collaborationClient'
import teacherWebsocket from '../utils/websocket'
import { useTeacherContextStore } from './context'

const developmentDefault = import.meta.env.DEV ? 'true' : 'false'
const featureEnabled = String(
  import.meta.env.VITE_COLLABORATION_ENABLED ?? developmentDefault
).toLowerCase() === 'true'
const NOTIFICATION_DESTINATION = '/user/queue/notifications'
const EMPTY_SUMMARY = {
  actionRequired: 0,
  inProgress: 0,
  createdByMe: 0,
  completed: 0,
  total: 0,
}

export const useTeacherCollaborationStore = defineStore('teacherCollaboration', () => {
  const isOpen = ref(false)
  const activeTab = ref('ACTION_REQUIRED')
  const activeTeamId = ref('all')
  const navigationStack = ref([])
  const items = ref([])
  const teams = ref([])
  const loading = ref(false)
  const error = ref('')
  const summary = ref({ ...EMPTY_SUMMARY })
  const started = ref(false)
  const isFeatureEnabled = computed(() => featureEnabled)
  const actionCount = computed(() => Number(summary.value.actionRequired) || 0)
  const visibleItems = computed(() => items.value)
  let notificationToken = null
  let removeConnection = null
  let returnFocusElement = null

  function open() {
    returnFocusElement = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    isOpen.value = true
    refresh().catch(() => {})
  }

  function close() {
    isOpen.value = false
    const target = returnFocusElement
    returnFocusElement = null
    queueMicrotask(() => target?.focus?.({ preventScroll: true }))
  }

  function toggle() {
    if (isOpen.value) close()
    else open()
  }

  function setTab(tab) {
    activeTab.value = tab
    loadItems().catch(() => {})
  }

  function setTeam(teamId) {
    activeTeamId.value = teamId || 'all'
    loadItems().catch(() => {})
  }

  async function loadTeams() {
    if (!teams.value.length) teams.value = await fetchTeacherCollaborationTeams()
    return teams.value
  }

  async function loadItems() {
    const payload = await fetchTeacherCollaborationItems(
      activeTab.value,
      activeTeamId.value
    )
    items.value = Array.isArray(payload?.items) ? payload.items : []
    return items.value
  }

  async function refresh() {
    if (!isFeatureEnabled.value) return
    loading.value = true
    error.value = ''
    try {
      const results = await Promise.allSettled([
        loadTeams(),
        fetchTeacherCollaborationSummary(),
        loadItems(),
      ])
      if (results[1].status === 'fulfilled') {
        summary.value = { ...EMPTY_SUMMARY, ...(results[1].value || {}) }
      }
      const failed = results.find(result => result.status === 'rejected')
      if (failed && !items.value.length) throw failed.reason
    } catch (refreshError) {
      error.value = refreshError?.message || '任务加载失败'
      throw refreshError
    } finally {
      loading.value = false
    }
  }

  function showTaskForm() {
    navigationStack.value.push({ type: 'task-form' })
  }

  async function showReview(item) {
    const submissionId = item.latestSubmissionId || item.submissionId
    if (!submissionId) return
    const reviewEntry = { type: 'review', item, loading: true }
    navigationStack.value.push(reviewEntry)
    try {
      reviewEntry.item = await fetchTeacherReviewDetail(submissionId)
    } finally {
      reviewEntry.loading = false
    }
  }

  function back() {
    navigationStack.value.pop()
  }

  async function publishTask(teamId, payload) {
    const result = await publishTeacherCollaborationTask(teamId, payload)
    navigationStack.value = []
    await refresh()
    return result
  }

  async function reviewSubmission(submissionId, status, reviewComment) {
    const result = await submitTeacherCollaborationReview(
      submissionId,
      { status, reviewComment }
    )
    navigationStack.value = []
    await refresh()
    return result
  }

  async function acceptRequest(id) {
    const result = await acceptTeacherCollaborationRequest(id)
    await refresh()
    return result
  }

  async function declineRequest(id, reason = '') {
    const result = await declineTeacherCollaborationRequest(id, reason)
    await refresh()
    return result
  }

  async function withdrawRequest(id) {
    const result = await withdrawTeacherCollaborationRequest(id)
    await refresh()
    return result
  }

  function handleNotification(notification) {
    const eventType = String(notification?.eventType || '')
    if (eventType.startsWith('COLLABORATION_')
      || eventType === 'TEACHER_TASK_ASSIGNED') {
      refresh().catch(() => {})
    }
  }

  function start() {
    if (started.value || !isFeatureEnabled.value) return
    started.value = true
    notificationToken = teacherWebsocket.subscribe(
      NOTIFICATION_DESTINATION,
      handleNotification
    )
    removeConnection = teacherWebsocket.connect(() => refresh().catch(() => {}))
    window.addEventListener('focus', handleFocus)
  }

  function handleFocus() {
    refresh().catch(() => {})
  }

  function stop() {
    if (!started.value) return
    teacherWebsocket.unsubscribe(notificationToken)
    removeConnection?.()
    window.removeEventListener('focus', handleFocus)
    notificationToken = null
    removeConnection = null
    started.value = false
  }

  function syncContextTeam() {
    const context = useTeacherContextStore()
    activeTeamId.value = context.teamId || 'all'
  }

  return {
    isOpen,
    activeTab,
    activeTeamId,
    navigationStack,
    items,
    teams,
    loading,
    error,
    summary,
    visibleItems,
    actionCount,
    isFeatureEnabled,
    open,
    close,
    toggle,
    setTab,
    setTeam,
    loadTeams,
    loadItems,
    refresh,
    showTaskForm,
    showReview,
    back,
    publishTask,
    reviewSubmission,
    acceptRequest,
    declineRequest,
    withdrawRequest,
    start,
    stop,
    syncContextTeam,
  }
})
