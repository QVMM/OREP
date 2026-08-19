/**
 * 教师端导航 · 对齐功能清单与可交互原型
 * 原则：以项目为业务上下文，以训练营为训练执行上下文
 */

export const TEACHER_NAV = [
  {
    key: 'workbench',
    label: '首页',
    path: '/',
    exact: true,
  },
  {
    key: 'projects',
    label: '项目团队',
    children: [
      { key: 'project-list', label: '项目管理', path: '/projects' },
      { key: 'members', label: '成员管理', path: '/members' },
    ],
  },
  {
    key: 'training',
    label: '训练管理',
    children: [
      /** 计划 + 概览合并为「训练营」；默认进计划 */
      { key: 'camp', label: '训练营', path: '/camp' },
      { key: 'review-queue', label: '提交与批改', path: '/camp/review-queue' },
      { key: 'progress', label: '训练进度', path: '/camp/progress' },
    ],
  },
  {
    key: 'roadshow',
    label: '路演管理',
    children: [
      // 录制回放已并入「路演场次」子页（?tab=recordings），不再单独占一级菜单
      { key: 'sessions', label: '路演场次', path: '/roadshow' },
      { key: 'reports', label: '评分报告', path: '/review/reports' },
      { key: 'remediation', label: '整改复盘', path: '/review/ai-todos' },
    ],
  },
  {
    key: 'ai',
    label: 'AI应用',
    children: [
      { key: 'ppt', label: 'PPT管理', path: '/ai/ppt' },
      { key: 'scripts', label: '讲稿管理', path: '/ai/scripts' },
    ],
  },
  {
    key: 'resources',
    label: '资源管理',
    children: [
      { key: 'project-resources', label: '团队资源', path: '/resources', query: { scope: 'team' } },
      { key: 'public-resources', label: '公共资源', path: '/resources', query: { scope: 'public' } },
      { key: 'inspire-office', label: '启发 Office', path: '/inspire-office' },
    ],
  },
  {
    key: 'analytics',
    label: '学情分析',
    children: [
      { key: 'overview', label: '学情总览', path: '/analytics' },
      { key: 'students', label: '学生档案', path: '/analytics/students' },
    ],
  },
  {
    key: 'assistant',
    label: '小启AI',
    path: '/assistant',
    exact: false,
    /** 使用 XiaoQiMark 品牌图标，与学生端一致 */
    icon: 'xiaoqi',
  },
]

/** 页签 / 文档标题 */
export const ROUTE_TITLES = {
  '/': '首页',
  '/projects': '项目管理',
  '/projects/create': '新建项目',
  '/members': '成员管理',
  '/camp': '训练营',
  '/camp/create': '创建训练营',
  '/camp/plan': '训练营',
  '/camp/review-queue': '提交与批改',
  '/camp/progress': '训练进度',
  '/camp/exams': '题库与考试',
  '/roadshow': '路演场次',
  '/roadshow/recordings': '录制回放',
  '/roadshow/materials': '路演材料',
  '/review/reports': '评分报告',
  '/review/ai-todos': '整改复盘',
  '/assistant': '小启AI',
  '/ai/assistant': '小启AI',
  '/ai/ppt': 'PPT管理',
  '/ai/scripts': '讲稿管理',
  '/resources': '资源管理',
  '/inspire-office': '启发 Office',
  '/analytics': '学情总览',
  '/analytics/students': '学生档案',
}

export function pathTitle(path, query = {}) {
  if (path === '/resources') {
    if (query.scope === 'public') return '公共资源'
    return '团队资源'
  }
  if (path.startsWith('/inspire-office/sdoc/')) return '智能文档'
  if (path === '/roadshow' && query.tab === 'recordings') return '录制回放'
  if (path.startsWith('/projects/') && path !== '/projects/create') return '项目详情'
  if (/^\/analytics\/students\/[^/]+$/.test(path)) return '学生详情'
  return ROUTE_TITLES[path] || '教师端'
}

export function resolveModuleKey(path) {
  if (path === '/' || path === '') return 'workbench'
  if (path === '/assistant' || path.startsWith('/assistant/') || path.startsWith('/ai/assistant')) return 'assistant'
  if (path.startsWith('/projects') || path.startsWith('/members') || path.startsWith('/team')) return 'projects'
  if (path.startsWith('/camp')) return 'training'
  if (path.startsWith('/ai')) return 'ai'
  if (path.startsWith('/roadshow') || path.startsWith('/review')) return 'roadshow'
  if (path.startsWith('/resources') || path.startsWith('/inspire-office')) return 'resources'
  if (path.startsWith('/analytics')) return 'analytics'
  return 'workbench'
}

export function childPathActive(childPath, currentPath, childQuery = null, currentQuery = {}) {
  if (childPath === '/resources' && childQuery?.scope) {
    return currentPath === '/resources' && String(currentQuery.scope || 'team') === String(childQuery.scope)
  }
  if (childPath === '/projects') {
    return currentPath === '/projects' || currentPath === '/projects/create' || /^\/projects\/[^/]+$/.test(currentPath)
  }
  if (childPath === '/camp') {
    // 训练营工作台含 plan 旧路径、创建页、题库；不含批改/进度（独立菜单）
    if (currentPath === '/camp/review-queue' || currentPath === '/camp/progress') return false
    return (
      currentPath === '/camp' ||
      currentPath === '/camp/create' ||
      currentPath === '/camp/plan' ||
      currentPath === '/camp/exams' ||
      currentPath.startsWith('/camp/')
    )
  }
  if (childPath === '/roadshow') {
    // 录制回放是场次子 tab，仍高亮「路演场次」
    return currentPath === '/roadshow' || currentPath === '/roadshow/recordings'
  }
  if (childPath === '/analytics') {
    return currentPath === '/analytics'
  }
  if (childPath === '/analytics/students') {
    return currentPath === '/analytics/students' || currentPath.startsWith('/analytics/students/')
  }
  return currentPath === childPath || currentPath.startsWith(`${childPath}/`)
}

export function toLocation(path, query) {
  if (query && Object.keys(query).length) return { path, query }
  return path
}

// —— 兼容旧引用 ——
export const TEACHER_RAIL = TEACHER_NAV.map((item) => ({
  key: item.key,
  label: item.label,
  path: item.path || item.children?.[0]?.path || '/',
  match: item.path ? [item.path] : (item.children || []).map((c) => c.path),
  exact: Boolean(item.exact),
}))

export const TEACHER_SUBNAV = Object.fromEntries(
  TEACHER_NAV.filter((g) => g.children?.length).map((g) => [
    g.key,
    {
      title: g.label,
      subtitle: '',
      items: g.children.map((c) => ({
        key: c.key,
        label: c.label,
        hint: '',
        to: c.query ? { path: c.path, query: c.query } : c.path,
      })),
    },
  ])
)

export function isRailActive(item, path) {
  return resolveModuleKey(path) === item.key
}

export function isSubnavActive(to, path) {
  const target = typeof to === 'string' ? to : to?.path
  const query = typeof to === 'object' ? to?.query : null
  return childPathActive(target, path, query, {})
}
