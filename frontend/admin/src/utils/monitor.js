import { getAdminToken } from './authStorage'

const HEARTBEAT_INTERVAL = 30000
let heartbeatTimer = null
let lastClickAt = 0

export function initFrontendMonitor(router, source = 'admin_frontend') {
  router.afterEach((to) => {
    trackFrontendEvent({
      source,
      actionType: 'page_view',
      actionName: `访问后台页面 ${to.path}`,
      route: to.fullPath,
      pageTitle: to.meta?.title || document.title
    })
    sendHeartbeat(source, to)
  })

  document.addEventListener('click', (event) => {
    const now = Date.now()
    if (now - lastClickAt < 800) return
    const target = event.target?.closest?.('button,a,[role="button"],.el-menu-item')
    if (!target) return
    lastClickAt = now
    const text = (target.innerText || target.getAttribute('aria-label') || target.getAttribute('title') || '').trim()
    trackFrontendEvent({
      source,
      actionType: 'click',
      actionName: text ? `点击 ${text.slice(0, 60)}` : '点击后台控件',
      route: window.location.pathname + window.location.search,
      pageTitle: document.title,
      detail: {
        tag: target.tagName?.toLowerCase(),
        href: target.getAttribute?.('href') || ''
      }
    })
  }, true)

  stopFrontendMonitor()
  sendHeartbeat(source, router.currentRoute.value)
  heartbeatTimer = window.setInterval(() => sendHeartbeat(source, router.currentRoute.value), HEARTBEAT_INTERVAL)
}

export function stopFrontendMonitor() {
  if (heartbeatTimer) {
    window.clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

export function trackApiRequest(config, status, durationMs, errorMessage = '') {
  const url = normalizeUrl(config?.url || '')
  if (!url || url.includes('/api/monitor/')) return
  trackFrontendEvent({
    source: 'admin_frontend',
    actionType: 'api_request',
    actionName: `${(config?.method || 'GET').toUpperCase()} ${url}`,
    route: window.location.pathname + window.location.search,
    pageTitle: document.title,
    detail: {
      status,
      durationMs,
      errorMessage: errorMessage || ''
    }
  })
}

export function trackFrontendEvent(payload, keepalive = false) {
  const token = getAdminToken()
  if (!token) return
  fetch('/api/monitor/track', {
    method: 'POST',
    keepalive,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  }).catch(() => {})
}

function sendHeartbeat(source, route) {
  const token = getAdminToken()
  if (!token) return
  fetch('/api/monitor/heartbeat', {
    method: 'POST',
    keepalive: true,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      source,
      actionType: 'heartbeat',
      actionName: '后台在线心跳',
      route: route?.fullPath || window.location.pathname + window.location.search,
      pageTitle: route?.meta?.title || document.title
    })
  }).catch(() => {})
}

function normalizeUrl(url) {
  if (!url) return ''
  try {
    return new URL(url, window.location.origin).pathname
  } catch (_) {
    return String(url).split('?')[0]
  }
}
