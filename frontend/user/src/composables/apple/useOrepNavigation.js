export const OREP_NAV_ITEMS = [
  { path: '/', label: '首页', code: 'Home', group: 'home' },
  { path: '/training/today', label: '训练营', code: 'Training', group: 'training' },
  { path: '/online-meeting', label: '路演训练', code: 'Roadshow', group: 'roadshow' },
  { path: '/assistant', label: '小启AI', code: 'XiaoQiAI', group: 'assistant' },
  { path: '/resource-center', label: '资源中心', code: 'Resources', group: 'resources' },
  { path: '/ai-apps', label: 'AI应用中心', code: 'AI Apps', group: 'aiApps' },
  { path: '/profile', label: '我的', code: 'Profile', group: 'profile' },
  // 紧挨「我的」下方；点击打开待办中心（非纯路由页）
  {
    path: '/project-team',
    label: '待办中心',
    code: 'Todo',
    group: 'collaboration',
    action: 'collaboration',
  },
]

export function isRouteFamily(path, prefix) {
  return path === prefix || path.startsWith(`${prefix}/`)
}

export function resolveOrepRouteGroup(route) {
  const routePath = typeof route === 'string' ? route : route.path
  const routeQuery = typeof route === 'string' ? {} : route.query || {}

  if (routePath === '/') return 'home'
  if (isRouteFamily(routePath, '/training')) return 'training'
  if ([
    '/online-meeting',
    '/meeting',
    '/meeting-history',
    '/my-recordings',
    '/statistics',
    '/score-result',
    '/ai-score-upload',
    '/ai-score',
    '/roadshow-chat',
  ].some(prefix => isRouteFamily(routePath, prefix))) return 'roadshow'
  if (isRouteFamily(routePath, '/assistant')) return 'assistant'
  if (isRouteFamily(routePath, '/resource-center')) return 'resources'
  if (
    isRouteFamily(routePath, '/project-team')
    || (isRouteFamily(routePath, '/script-editor') && routeQuery.tab === 'materials')
  ) return 'collaboration'
  if (
    isRouteFamily(routePath, '/ai-apps')
    || routePath.startsWith('/ppt-')
    || isRouteFamily(routePath, '/resources')
    || isRouteFamily(routePath, '/typing-practice')
    || isRouteFamily(routePath, '/inspire-office')
    || (
      isRouteFamily(routePath, '/script-editor')
      && routeQuery.tab !== 'materials'
    )
  ) return 'aiApps'
  if (isRouteFamily(routePath, '/profile')) return 'profile'
  return ''
}

export function isOrepRouteActive(route, itemPath) {
  const routePath = typeof route === 'string' ? route : route.path
  const routeQuery = typeof route === 'string' ? {} : route.query || {}

  const primaryItem = OREP_NAV_ITEMS.find(item => item.path === itemPath)
  if (primaryItem) return resolveOrepRouteGroup(route) === primaryItem.group

  if (itemPath.startsWith('/script-editor?tab=')) {
    if (isRouteFamily(routePath, '/script-editor/detail') || isRouteFamily(routePath, '/script-editor/template')) return itemPath.endsWith('tab=script')
    if (!isRouteFamily(routePath, '/script-editor')) return false
    const itemTab = new URLSearchParams(itemPath.split('?')[1]).get('tab')
    return (routeQuery.tab || 'script') === itemTab
  }

  if (itemPath === '/script-editor') {
    return isRouteFamily(routePath, '/script-editor')
  }

  if (itemPath === '/resources') return isRouteFamily(routePath, '/resources')
  if (itemPath === '/resource-center') return isRouteFamily(routePath, '/resource-center')
  if (itemPath === '/ppt-editor') {
    return ['/ppt-generator', '/ppt-editor', '/ppt-history']
      .some(prefix => isRouteFamily(routePath, prefix))
  }
  if (itemPath === '/roadshow') {
    return isRouteFamily(routePath, '/roadshow') && !isRouteFamily(routePath, '/roadshow-chat')
  }
  return isRouteFamily(routePath, itemPath)
}

export function shouldUseImmersiveShell(routePath) {
  return isRouteFamily(routePath, '/meeting')
}
