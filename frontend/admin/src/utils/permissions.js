const ADMIN_PANEL_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'EXPERT', 'REVIEWER']
const WRITE_ROLES = ['ADMIN', 'SCHOOL_ADMIN']
const USER_MANAGEMENT_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER']
const ISSUE_MANAGEMENT_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'EXPERT', 'REVIEWER']
const TEACHER_ASSIGNABLE_ROLES = ['STUDENT', 'TEACHER', 'REVIEWER', 'EXPERT']

export function normalizeRole(role) {
  return String(role || '').trim().toUpperCase()
}

export function canAccessAdmin(role) {
  return ADMIN_PANEL_ROLES.includes(normalizeRole(role))
}

export function canWriteAdmin(role) {
  return WRITE_ROLES.includes(normalizeRole(role))
}

export function canManageUsers(role) {
  return USER_MANAGEMENT_ROLES.includes(normalizeRole(role))
}

export function canManageIssues(role) {
  return ISSUE_MANAGEMENT_ROLES.includes(normalizeRole(role))
}

export function isSuperAdmin(role) {
  return normalizeRole(role) === 'ADMIN'
}

export function roleLabel(role) {
  const map = {
    ADMIN: '平台管理员',
    SCHOOL_ADMIN: '学校领导',
    TEACHER: '教师',
    STUDENT: '学生',
    REVIEWER: '评委',
    EXPERT: '专家',
  }
  return map[normalizeRole(role)] || role || '未知'
}

const ALL_ROLE_OPTIONS = [
  { label: '平台管理员 (ADMIN)', value: 'ADMIN', tag: 'danger' },
  { label: '学校领导 (SCHOOL_ADMIN)', value: 'SCHOOL_ADMIN', tag: 'warning' },
  { label: '教师 (TEACHER)', value: 'TEACHER', tag: 'success' },
  { label: '学生 (STUDENT)', value: 'STUDENT', tag: 'primary' },
  { label: '评委 (REVIEWER)', value: 'REVIEWER', tag: 'info' },
  { label: '专家 (EXPERT)', value: 'EXPERT', tag: 'success' },
]

/** 当前角色可分配的用户角色选项 */
export function assignableRoleOptions(role) {
  const normalized = normalizeRole(role)
  if (normalized === 'ADMIN') {
    return ALL_ROLE_OPTIONS
  }
  if (normalized === 'SCHOOL_ADMIN') {
    return ALL_ROLE_OPTIONS.filter(item => item.value !== 'ADMIN')
  }
  if (normalized === 'TEACHER') {
    return ALL_ROLE_OPTIONS.filter(item => TEACHER_ASSIGNABLE_ROLES.includes(item.value))
  }
  return []
}

/** 路由 meta.roles 校验 */
export function canAccessRoute(role, routeRoles) {
  if (!routeRoles || routeRoles.length === 0) return true
  return routeRoles.includes(normalizeRole(role))
}
