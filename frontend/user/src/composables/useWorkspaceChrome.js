import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { createNotificationClient } from '../services/notificationClient'
import { getUserToken } from '../utils/authStorage'

const SEARCH_ITEMS = [
  { title: '训练任务', desc: '查看每日学习内容、任务要求和完成状态', group: '训练营', path: '/training/today' },
  { title: '路演训练', desc: '发起路演、回看并获取评分', group: '路演训练', path: '/online-meeting' },
  { title: '评分报告', desc: '查看评分结论和改进建议', group: '复盘', path: '/statistics' },
  { title: '任务管理', desc: '查看团队任务和成员分工', group: '待办', path: '/project-team' },
  { title: '日报中心', desc: '写日报、看历史与统计', group: '待办', path: '/daily-reports' },
  { title: '资源中心', desc: '管理项目文件和成果材料', group: '资源', path: '/resource-center' },
  { title: '个人中心', desc: '查看学习时长、奖状和整改记录', group: '我的', path: '/profile' },
]

const SEARCH_PLACEHOLDERS = [
  '搜索课程、任务、文件、报告',
  '搜索今天的训练任务',
  '查找路演训练、回放或评分',
  '查找 AI 评分与改进建议',
  '搜索团队文件与成果',
]

/**
 * 工作区顶栏 / 侧栏共用：搜索、消息、账户、改密、退出。
 * @param {{ rootRef: import('vue').Ref<HTMLElement|null>, searchInputRef?: import('vue').Ref<any> }} options
 */
export function useWorkspaceChrome(options = {}) {
  const { rootRef, searchInputRef } = options
  const router = useRouter()
  const authStore = useAuthStore()

  const query = ref('')
  const activePanel = ref(null)
  const passwordDialog = ref(false)
  const changingPassword = ref(false)
  const notifications = ref([])
  const unreadCount = ref(0)
  const messagesLoading = ref(false)
  const messagesError = ref('')
  const passwordForm = ref({ oldPassword: '', newPassword: '', confirmPassword: '' })

  let notificationClient = null
  let searchNavigationTimer = null

  const username = computed(() => authStore.user?.username || '用户')
  const userInitial = computed(() => username.value.slice(0, 1))
  const roleLabel = computed(() => {
    const role = String(authStore.user?.role || '').toUpperCase()
    if (role === 'TEACHER') return '教师'
    if (role === 'ADMIN') return '管理员'
    return '学生'
  })

  const searchPlaceholders = SEARCH_PLACEHOLDERS
  const filteredResults = computed(() => {
    const term = query.value.toLowerCase()
    if (!term) return SEARCH_ITEMS.slice(0, 6)
    return SEARCH_ITEMS.filter((item) =>
      `${item.title}${item.desc}${item.group}`.toLowerCase().includes(term)
    ).slice(0, 8)
  })

  async function togglePanel(panel) {
    activePanel.value = activePanel.value === panel ? null : panel
    if (activePanel.value === 'messages') await refreshNotifications()
    if (activePanel.value === 'search') {
      queueMicrotask(() => searchInputRef?.value?.focus?.())
    }
  }

  function closePanel() {
    activePanel.value = null
  }

  function applyNotificationSnapshot(snapshot) {
    notifications.value = snapshot.items
    unreadCount.value = snapshot.unreadCount
  }

  async function refreshNotifications() {
    if (!notificationClient) return
    messagesLoading.value = true
    messagesError.value = ''
    try {
      await notificationClient.refresh()
    } catch (error) {
      messagesError.value = error?.response?.data?.message || '请稍后重试'
    } finally {
      messagesLoading.value = false
    }
  }

  function handleRealtimeNotification(item) {
    const index = notifications.value.findIndex(
      (notification) => String(notification.id) === String(item.id)
    )
    const existedUnread = index >= 0 && !notifications.value[index].isRead
    if (index >= 0) {
      notifications.value.splice(index, 1, item)
    } else {
      notifications.value.unshift(item)
      notifications.value = notifications.value.slice(0, 20)
    }
    if (!item.isRead && !existedUnread) unreadCount.value += 1

    if (activePanel.value !== 'messages') {
      ElNotification({
        title: item.title || '新消息',
        message: item.message || '你收到了一条新通知',
        type: 'info',
        position: 'top-right',
        duration: 5000,
        onClick: () => openNotification(item),
      })
    }
  }

  function safeNotificationPath(value) {
    if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) {
      return '/training/today'
    }
    return value
  }

  async function openNotification(item) {
    activePanel.value = null
    if (!item.isRead) {
      item.isRead = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
      notificationClient?.markRead(item.id).catch(() => refreshNotifications())
    }
    await router.push(safeNotificationPath(item.targetPath))
  }

  async function markAllNotificationsRead() {
    const previousUnreadCount = unreadCount.value
    notifications.value = notifications.value.map((item) => ({ ...item, isRead: true }))
    unreadCount.value = 0
    try {
      await notificationClient?.markAllRead()
    } catch {
      unreadCount.value = previousUnreadCount
      await refreshNotifications()
      ElMessage.warning('全部已读设置失败，请重试')
    }
  }

  function formatMessageTime(value) {
    if (!value) return ''
    const date = new Date(value)
    return Number.isNaN(date.getTime())
      ? String(value)
      : date.toLocaleString('zh-CN', {
          month: 'numeric',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
  }

  function go(path) {
    activePanel.value = null
    router.push(path)
  }

  function openFirstSearchResult() {
    const first = filteredResults.value[0]
    if (!first) return
    if (searchNavigationTimer) window.clearTimeout(searchNavigationTimer)
    searchNavigationTimer = window.setTimeout(() => {
      searchNavigationTimer = null
      go(first.path)
    }, 420)
  }

  function openPasswordDialog() {
    activePanel.value = null
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    passwordDialog.value = true
  }

  async function changePassword() {
    const { oldPassword, newPassword, confirmPassword } = passwordForm.value
    if (!oldPassword || !newPassword) {
      ElMessage.warning('请填写当前密码和新密码')
      return
    }
    if (newPassword !== confirmPassword) {
      ElMessage.warning('两次输入的新密码不一致')
      return
    }
    changingPassword.value = true
    try {
      await authStore.changePassword(oldPassword, newPassword)
      passwordDialog.value = false
      ElMessage.success('密码已修改')
    } catch (error) {
      ElMessage.error(error?.message || '修改密码失败')
    } finally {
      changingPassword.value = false
    }
  }

  async function handleLogout() {
    activePanel.value = null
    try {
      await ElMessageBox.confirm('退出后需要重新登录才能继续使用。', '确认退出登录？', {
        confirmButtonText: '退出登录',
        cancelButtonText: '继续使用',
        type: 'warning',
      })
      authStore.logout()
      router.replace('/login')
    } catch (error) {
      if (error !== 'cancel' && error !== 'close') console.warn(error)
    }
  }

  function handleKeydown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      activePanel.value = 'search'
      queueMicrotask(() => searchInputRef?.value?.focus?.())
    }
    if (event.key === 'Escape') activePanel.value = null
  }

  function handlePointerdown(event) {
    if (!activePanel.value || rootRef?.value?.contains(event.target)) return
    activePanel.value = null
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
    document.addEventListener('pointerdown', handlePointerdown, true)
    notificationClient = createNotificationClient({
      onSnapshot: applyNotificationSnapshot,
      onRealtimeNotification: handleRealtimeNotification,
    })
    if (!getUserToken()) return
    notificationClient.start().catch((error) => {
      messagesError.value = error?.response?.data?.message || '请稍后重试'
    })
  })

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown)
    document.removeEventListener('pointerdown', handlePointerdown, true)
    notificationClient?.stop()
    if (searchNavigationTimer) window.clearTimeout(searchNavigationTimer)
  })

  return {
    query,
    activePanel,
    passwordDialog,
    changingPassword,
    notifications,
    unreadCount,
    messagesLoading,
    messagesError,
    passwordForm,
    username,
    userInitial,
    roleLabel,
    searchPlaceholders,
    filteredResults,
    togglePanel,
    closePanel,
    refreshNotifications,
    openNotification,
    markAllNotificationsRead,
    formatMessageTime,
    go,
    openFirstSearchResult,
    openPasswordDialog,
    changePassword,
    handleLogout,
  }
}
