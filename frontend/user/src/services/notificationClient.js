import request from '../utils/request'
import websocketClient from '../utils/websocket'

const NOTIFICATION_DESTINATION = '/user/queue/notifications'

function normalizeSnapshot(response) {
  const payload = response?.data ?? response
  return {
    items: Array.isArray(payload?.items) ? payload.items : [],
    unreadCount: Number(payload?.unreadCount) || 0
  }
}

export function createNotificationClient({
  onSnapshot,
  onRealtimeNotification,
  onConnectionChange
} = {}) {
  let stopped = false
  let bootstrapped = false
  let removeConnectionListeners = null
  let subscriptionToken = null

  async function refresh() {
    const response = await request.get('/api/notifications', { silentError: true })
    const snapshot = normalizeSnapshot(response)
    if (!stopped) onSnapshot?.(snapshot)
    return snapshot
  }

  function handleRealtime(notification) {
    if (!stopped && notification && typeof notification === 'object') {
      onRealtimeNotification?.(notification)
    }
  }

  async function handleFocus() {
    try {
      await refresh()
    } catch {
      // 页面重新聚焦时静默回补，失败不打断用户当前操作。
    }
  }

  async function start() {
    stopped = false
    window.addEventListener('focus', handleFocus)
    subscriptionToken = websocketClient.subscribe(NOTIFICATION_DESTINATION, handleRealtime)
    removeConnectionListeners = websocketClient.connect(
      async () => {
        onConnectionChange?.(true)
        if (bootstrapped) await handleFocus()
      },
      () => onConnectionChange?.(false)
    )

    try {
      const snapshot = await refresh()
      bootstrapped = true
      return snapshot
    } catch (error) {
      bootstrapped = true
      throw error
    }
  }

  function stop() {
    stopped = true
    window.removeEventListener('focus', handleFocus)
    websocketClient.unsubscribe(subscriptionToken)
    subscriptionToken = null
    removeConnectionListeners?.()
    removeConnectionListeners = null
  }

  async function markRead(id) {
    return request.patch(`/api/notifications/${id}/read`, {}, { silentError: true })
  }

  async function markAllRead() {
    return request.patch('/api/notifications/read-all', {}, { silentError: true })
  }

  return {
    start,
    stop,
    refresh,
    markRead,
    markAllRead
  }
}
