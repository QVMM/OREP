import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  clearAdminAuth,
  getAdminRole,
  getAdminTenantId,
  getAdminToken,
  getAdminUsername,
  setAdminAuth,
} from '../utils/authStorage'
import { canAccessAdmin, canManageIssues, canManageUsers, canWriteAdmin, isSuperAdmin, normalizeRole, roleLabel } from '../utils/permissions'

export const useUserStore = defineStore('user', () => {
  const token = ref(getAdminToken())
  const username = ref(getAdminUsername())
  const role = ref(getAdminRole())
  const tenantId = ref(getAdminTenantId())

  const normalizedRole = computed(() => normalizeRole(role.value))
  const canAccess = computed(() => canAccessAdmin(role.value))
  const canWrite = computed(() => canWriteAdmin(role.value))
  const canManageUsersFlag = computed(() => canManageUsers(role.value))
  const canManageIssuesFlag = computed(() => canManageIssues(role.value))
  const readOnlyMode = computed(() => !canWrite.value && !canManageUsersFlag.value && !canManageIssuesFlag.value)
  const isPlatformAdmin = computed(() => isSuperAdmin(role.value))
  const roleDisplay = computed(() => roleLabel(role.value))

  function setLoginInfo({ token: newToken, username: newUsername, role: newRole, tenantId: newTenantId }) {
    token.value = newToken || ''
    username.value = newUsername || ''
    role.value = normalizeRole(newRole)
    tenantId.value = newTenantId ?? null
    setAdminAuth({
      token: token.value,
      username: username.value,
      role: role.value,
      tenantId: tenantId.value,
    })
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    tenantId.value = null
    clearAdminAuth()
  }

  return {
    token,
    username,
    role,
    tenantId,
    normalizedRole,
    canAccess,
    canWrite,
    canManageUsers: canManageUsersFlag,
    canManageIssues: canManageIssuesFlag,
    readOnlyMode,
    isPlatformAdmin,
    roleDisplay,
    setLoginInfo,
    logout,
  }
})
