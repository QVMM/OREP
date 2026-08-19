import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '../utils/request'
import { clearUserAuth, getStoredUser, getUserToken, setUserAuth } from '../utils/authStorage'
import { useCollaborationStore } from './collaboration'

// 认证状态管理
export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref(getUserToken())
  const user = ref(getStoredUser())

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)

  // 登录
  async function login(username, password) {
    const res = await request.post('/api/auth/login', { username, password })
    token.value = res.data.token
    user.value = res.data.user
    setUserAuth(res.data.token, res.data.user)
    return res.data
  }

  // 退出登录
  function logout() {
    useCollaborationStore().reset()
    token.value = ''
    user.value = null
    clearUserAuth()
  }

  // 修改密码
  async function changePassword(oldPassword, newPassword) {
    return await request.post('/api/auth/change-password', {
      oldPassword,
      newPassword
    })
  }

  return {
    token,
    user,
    isLoggedIn,
    login,
    logout,
    changePassword
  }
})
