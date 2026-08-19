const TOKEN_KEY = 'orep_user_token'
const USER_KEY = 'orep_user'
const LEGACY_TOKEN = 'token'
const LEGACY_USER = 'user'

/** 允许进入教师端的系统角色（与后端 AdminAccess.TEACHER_PORTAL_ROLES 对齐） */
export const TEACHER_PORTAL_ROLES = new Set(['TEACHER', 'ADMIN', 'SCHOOL_ADMIN'])

function parseJson(value) {
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN) || ''
}

export function getUser() {
  return parseJson(localStorage.getItem(USER_KEY)) || parseJson(localStorage.getItem(LEGACY_USER))
}

export function getUserRole(user = getUser()) {
  const raw = user?.role || user?.userRole || user?.roleName || ''
  return String(raw).trim().toUpperCase()
}

export function canAccessTeacherPortal(user = getUser()) {
  return TEACHER_PORTAL_ROLES.has(getUserRole(user))
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user || {}))
  localStorage.setItem(LEGACY_USER, JSON.stringify(user || {}))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(LEGACY_USER)
  localStorage.removeItem(LEGACY_TOKEN)
}

export function isLoggedIn() {
  return Boolean(getToken())
}
