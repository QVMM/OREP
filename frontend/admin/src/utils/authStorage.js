const ADMIN_TOKEN_KEY = 'orep_admin_token'
const ADMIN_USERNAME_KEY = 'orep_admin_username'
const ADMIN_ROLE_KEY = 'orep_admin_role'
const ADMIN_TENANT_ID_KEY = 'orep_admin_tenant_id'
const LEGACY_TOKEN_KEY = 'token'
const LEGACY_USERNAME_KEY = 'username'

export function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN_KEY) || ''
}

export function getAdminUsername() {
  return localStorage.getItem(ADMIN_USERNAME_KEY) || localStorage.getItem(LEGACY_USERNAME_KEY) || ''
}

export function getAdminRole() {
  return localStorage.getItem(ADMIN_ROLE_KEY) || ''
}

export function getAdminTenantId() {
  const raw = localStorage.getItem(ADMIN_TENANT_ID_KEY)
  if (!raw) return null
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

export function setAdminAuth({ token, username, role, tenantId }) {
  if (token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token)
  }
  if (username) {
    localStorage.setItem(ADMIN_USERNAME_KEY, username)
  }
  if (role) {
    localStorage.setItem(ADMIN_ROLE_KEY, role)
  }
  if (tenantId != null) {
    localStorage.setItem(ADMIN_TENANT_ID_KEY, String(tenantId))
  }
}

export function clearAdminAuth() {
  localStorage.removeItem(ADMIN_TOKEN_KEY)
  localStorage.removeItem(ADMIN_USERNAME_KEY)
  localStorage.removeItem(ADMIN_ROLE_KEY)
  localStorage.removeItem(ADMIN_TENANT_ID_KEY)
  localStorage.removeItem(LEGACY_TOKEN_KEY)
  localStorage.removeItem(LEGACY_USERNAME_KEY)
}
