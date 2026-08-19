const USER_TOKEN_KEY = 'orep_user_token'
const USER_KEY = 'orep_user'
const LEGACY_TOKEN_KEY = 'token'
const LEGACY_USER_KEY = 'user'

function parseJson(value) {
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function decodeJwtPayload(token) {
  if (!token || typeof token !== 'string') return null
  const parts = token.split('.')
  if (parts.length < 2) return null
  try {
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + (4 - base64.length % 4) % 4, '=')
    return JSON.parse(decodeURIComponent(escape(window.atob(padded))))
  } catch {
    return null
  }
}

function sameUser(token, user) {
  if (!token || !user?.id) return true
  const payload = decodeJwtPayload(token)
  return String(payload?.sub || '') === String(user.id)
}

function isTokenExpired(token) {
  const payload = decodeJwtPayload(token)
  if (!payload?.exp) return false
  return payload.exp * 1000 <= Date.now()
}

export function getStoredUser() {
  return parseJson(localStorage.getItem(USER_KEY)) || parseJson(localStorage.getItem(LEGACY_USER_KEY))
}

export function getUserToken() {
  const user = getStoredUser()
  const token = localStorage.getItem(USER_TOKEN_KEY)
  if (token && sameUser(token, user)) {
    if (isTokenExpired(token)) {
      clearUserAuth()
      return ''
    }
    return token
  }

  const legacyToken = localStorage.getItem(LEGACY_TOKEN_KEY)
  if (legacyToken && sameUser(legacyToken, user)) {
    if (isTokenExpired(legacyToken)) {
      clearUserAuth()
      return ''
    }
    localStorage.setItem(USER_TOKEN_KEY, legacyToken)
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    return legacyToken
  }

  return ''
}

export function setUserAuth(token, user) {
  localStorage.setItem(USER_TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
  localStorage.setItem(LEGACY_USER_KEY, JSON.stringify(user))
}

/** 退出时清掉本机「按账号隔离」的小启缓存，避免下一账号误读 */
function clearXiaoQiLocalCaches() {
  try {
    localStorage.removeItem('orep.home.xiaoqi.thread.v1')
    const keys = []
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)
      if (key && key.startsWith('orep.home.xiaoqi.thread.v1')) keys.push(key)
    }
    keys.forEach((key) => localStorage.removeItem(key))
  } catch {
    /* private mode / blocked storage */
  }
}

export function clearUserAuth() {
  localStorage.removeItem(USER_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(LEGACY_USER_KEY)
  localStorage.removeItem(LEGACY_TOKEN_KEY)
  clearXiaoQiLocalCaches()
}
