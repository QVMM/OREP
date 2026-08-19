import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  acceptCollaborationRequest,
  createCollaborationRequest,
  createCollaborationRequests,
  declineCollaborationRequest,
  fetchCollaborationItems,
  fetchCollaborationRequest,
  fetchCollaborationSummary,
  fetchCollaborationTeamDashboard,
  fetchCollaborationTeams,
  withdrawCollaborationRequest,
} from '../services/collaborationClient'
import { fetchDailyReportToday } from '../services/dailyReportClient'
import { fetchTodayTraining } from '../modules/training/api'
import { getUserToken } from '../utils/authStorage'
import websocketClient from '../utils/websocket'

const collaborationEnabled = String(
  import.meta.env.VITE_COLLABORATION_ENABLED ?? 'true'
).toLowerCase() === 'true'
const NOTIFICATION_DESTINATION = '/user/queue/notifications'
const EMPTY_SUMMARY = {
  actionRequired: 0,
  inProgress: 0,
  createdByMe: 0,
  completed: 0,
  total: 0,
  todayPending: 0,
}

export const useCollaborationStore = defineStore('collaboration', () => {
  const isOpen = ref(false)
  /** 待办中心默认打开「今日必做」 */
  const activeTab = ref('TODAY')
  const activeTeamId = ref(null)
  const navigationStack = ref([])
  const navigationDirection = ref('forward')
  const drafts = ref({})
  const scrollPositions = ref({})
  const summary = ref({ ...EMPTY_SUMMARY })
  const itemsByTab = ref({})
  const loadingByTab = ref({})
  const errorByTab = ref({})
  const lastRefreshedAt = ref(null)
  const teams = ref([])
  const membersByTeam = ref({})
  const started = ref(false)
  /** 今日必做：日报 + 训练 */
  const todayBundle = ref({
    dailyReport: null,
    training: null,
    pendingCount: 0,
  })
  const dailyReportOpen = ref(false)
  const isFeatureEnabled = computed(() => collaborationEnabled)
  /** 侧栏红点 = 待我处理 + 今日未完成 */
  const actionCount = computed(() => (
    (Number(summary.value.actionRequired) || 0)
    + (Number(summary.value.todayPending) || Number(todayBundle.value.pendingCount) || 0)
  ))
  let notificationToken = null
  let removeConnectionListeners = null
  let returnFocusElement = null

  function open() {
    returnFocusElement = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    isOpen.value = true
    if (isFeatureEnabled.value) refreshCurrent().catch(() => {})
  }

  function close() {
    isOpen.value = false
    const focusTarget = returnFocusElement
    returnFocusElement = null
    queueMicrotask(() => focusTarget?.focus?.({ preventScroll: true }))
  }

  function toggle() {
    if (isOpen.value) close()
    else open()
  }

  function setActionCount(value) {
    summary.value.actionRequired = Math.max(0, Number(value) || 0)
  }

  function setActiveTab(value) {
    navigationDirection.value = 'forward'
    activeTab.value = value
    if (value === 'TODAY') {
      loadTodayBundle({ force: true }).catch(() => {})
      return
    }
    if (isFeatureEnabled.value && !itemsByTab.value[cacheKey(value)]) {
      loadItems(value).catch(() => {})
    }
  }

  function openDailyReport() {
    dailyReportOpen.value = true
  }

  function closeDailyReport() {
    dailyReportOpen.value = false
  }

  async function loadTodayBundle({ force = false } = {}) {
    if (!force && todayBundle.value.dailyReport != null) return todayBundle.value
    loadingByTab.value['TODAY:all'] = true
    errorByTab.value['TODAY:all'] = ''
    try {
      const [reportRes, trainingRes] = await Promise.allSettled([
        fetchDailyReportToday(),
        fetchTodayTraining(),
      ])
      const dailyReport = reportRes.status === 'fulfilled' ? reportRes.value : null
      const training = trainingRes.status === 'fulfilled' ? trainingRes.value : null
      let pending = 0
      if (!dailyReport?.submitted) pending += 1
      if (training?.hasTrainingDay) {
        const primary = training.primaryTask || {}
        const tasks = Array.isArray(training.tasks) ? training.tasks : []
        const unfinished = tasks.some((t) => !t.latestSubmissionId)
          || (tasks.length === 0 && !primary.latestSubmissionId)
        // 有训练日且主任务未交
        if (tasks.length) {
          if (tasks.every((t) => !t.latestSubmissionId)) pending += 1
          else if (tasks.some((t) => !t.latestSubmissionId)) pending += 1
        } else if (training.hasTrainingDay && !primary.latestSubmissionId) {
          pending += 1
        }
        void unfinished
      }
      todayBundle.value = {
        dailyReport,
        training,
        pendingCount: pending,
      }
      summary.value.todayPending = pending
      return todayBundle.value
    } catch (error) {
      errorByTab.value['TODAY:all'] = error?.message || '今日待办加载失败'
      throw error
    } finally {
      loadingByTab.value['TODAY:all'] = false
    }
  }

  function setActiveTeam(teamId) {
    activeTeamId.value = teamId ? Number(teamId) : null
    loadItems(activeTab.value, { force: true }).catch(() => {})
  }

  function cacheKey(tab = activeTab.value) {
    return `${tab}:${activeTeamId.value || 'all'}`
  }

  async function loadSummary() {
    const collab = await fetchCollaborationSummary().catch(() => ({}))
    summary.value = {
      ...EMPTY_SUMMARY,
      ...collab,
      todayPending: summary.value.todayPending || 0,
    }
    lastRefreshedAt.value = Date.now()
    // 同步刷新今日待办计数（不切换 tab）
    loadTodayBundle({ force: true }).catch(() => {})
    return summary.value
  }

  async function loadItems(tab = activeTab.value, { force = false } = {}) {
    if (tab === 'TODAY') {
      await loadTodayBundle({ force })
      return []
    }
    const key = cacheKey(tab)
    if (loadingByTab.value[key]) return itemsByTab.value[key] || []
    if (!force && itemsByTab.value[key]) return itemsByTab.value[key]
    loadingByTab.value[key] = true
    errorByTab.value[key] = ''
    try {
      const payload = await fetchCollaborationItems(tab, activeTeamId.value)
      itemsByTab.value[key] = Array.isArray(payload?.items) ? payload.items : []
      return itemsByTab.value[key]
    } catch (error) {
      errorByTab.value[key] = error?.message || '待办加载失败'
      throw error
    } finally {
      loadingByTab.value[key] = false
    }
  }

  async function refreshCurrent() {
    await Promise.allSettled([loadSummary()])
    if (activeTab.value === 'TODAY') {
      await Promise.allSettled([loadTodayBundle({ force: true })])
    } else {
      await Promise.allSettled([loadItems(activeTab.value, { force: true })])
    }
  }

  async function loadTeams() {
    if (!teams.value.length) teams.value = await fetchCollaborationTeams()
    return teams.value
  }

  async function loadMembers(teamId) {
    const key = String(teamId)
    if (!membersByTeam.value[key]) {
      const dashboard = await fetchCollaborationTeamDashboard(teamId)
      membersByTeam.value[key] = Array.isArray(dashboard?.members) ? dashboard.members : []
    }
    return membersByTeam.value[key]
  }

  async function createRequest(payload) {
    const idempotencyKey = globalThis.crypto?.randomUUID?.()
      || `collaboration-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const result = await createCollaborationRequest(payload, idempotencyKey)
    delete drafts.value.request
    navigationStack.value = [{ type: 'detail', id: result.id, item: result }]
    await refreshCurrent()
    return result
  }

  async function createRequests(payload, idempotencyKey) {
    const result = await createCollaborationRequests(payload, idempotencyKey)
    delete drafts.value.request
    activeTab.value = 'CREATED_BY_ME'
    await refreshCurrent()
    return result
  }

  async function loadDetail(id) {
    const detail = await fetchCollaborationRequest(id)
    navigationDirection.value = 'forward'
    navigationStack.value.push({ type: 'detail', id, item: detail })
    return detail
  }

  function showRequestForm() {
    navigationDirection.value = 'forward'
    navigationStack.value.push({ type: 'request-form' })
  }

  function showDetail(item) {
    navigationDirection.value = 'forward'
    navigationStack.value.push({ type: 'detail', id: item.id, item })
  }

  function back() {
    navigationDirection.value = 'back'
    navigationStack.value.pop()
  }

  function clearNavigation() {
    navigationDirection.value = 'back'
    navigationStack.value = []
  }

  async function accept(id) {
    const result = await acceptCollaborationRequest(id)
    updateCurrentDetail(result)
    await refreshCurrent()
    return result
  }

  async function decline(id, reason) {
    const result = await declineCollaborationRequest(id, reason)
    updateCurrentDetail(result)
    await refreshCurrent()
    return result
  }

  async function withdraw(id) {
    const result = await withdrawCollaborationRequest(id)
    updateCurrentDetail(result)
    await refreshCurrent()
    return result
  }

  function updateCurrentDetail(item) {
    const current = navigationStack.value.at(-1)
    if (current?.type === 'detail') current.item = item
  }

  function handleRealtime(notification) {
    if (!notification?.eventType?.startsWith('COLLABORATION_')
      && notification?.eventType !== 'TEACHER_TASK_ASSIGNED') return
    refreshCurrent().catch(() => {})
  }

  function handleFocus() {
    if (isFeatureEnabled.value) loadSummary().catch(() => {})
  }

  function start() {
    if (started.value || !isFeatureEnabled.value) return
    // 未登录不拉摘要/WebSocket，避免引导页无意义 401
    if (!getUserToken()) return
    started.value = true
    window.addEventListener('focus', handleFocus)
    notificationToken = websocketClient.subscribe(
      NOTIFICATION_DESTINATION,
      handleRealtime
    )
    removeConnectionListeners = websocketClient.connect(
      () => loadSummary().catch(() => {}),
      () => {}
    )
    loadSummary().catch(() => {})
  }

  function stop() {
    if (!started.value) return
    window.removeEventListener('focus', handleFocus)
    websocketClient.unsubscribe(notificationToken)
    removeConnectionListeners?.()
    notificationToken = null
    removeConnectionListeners = null
    started.value = false
  }

  function reset() {
    close()
    stop()
    activeTab.value = 'TODAY'
    activeTeamId.value = null
    navigationStack.value = []
    navigationDirection.value = 'forward'
    drafts.value = {}
    scrollPositions.value = {}
    summary.value = { ...EMPTY_SUMMARY }
    itemsByTab.value = {}
    loadingByTab.value = {}
    errorByTab.value = {}
    teams.value = []
    membersByTeam.value = {}
    todayBundle.value = { dailyReport: null, training: null, pendingCount: 0 }
    dailyReportOpen.value = false
    lastRefreshedAt.value = null
  }

  return {
    isOpen,
    actionCount,
    activeTab,
    activeTeamId,
    navigationStack,
    navigationDirection,
    drafts,
    scrollPositions,
    summary,
    itemsByTab,
    loadingByTab,
    errorByTab,
    lastRefreshedAt,
    teams,
    membersByTeam,
    todayBundle,
    dailyReportOpen,
    isFeatureEnabled,
    open,
    close,
    toggle,
    setActionCount,
    setActiveTab,
    setActiveTeam,
    openDailyReport,
    closeDailyReport,
    loadTodayBundle,
    cacheKey,
    loadSummary,
    loadItems,
    refreshCurrent,
    loadTeams,
    loadMembers,
    createRequest,
    createRequests,
    loadDetail,
    showRequestForm,
    showDetail,
    back,
    clearNavigation,
    accept,
    decline,
    withdraw,
    start,
    stop,
    reset,
  }
})
