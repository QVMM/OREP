import axios from 'axios'
import { clearAuth, getToken } from './auth'
import router from '../router'

const request = axios.create({
  timeout: 20000,
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data && typeof data.code === 'number' && data.code !== 200) {
      if (!response.config?.silentError) {
        // 业务错误交给调用方展示；这里不弹全局 toast，保持与页面内提示一致
      }
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data
  },
  (error) => {
    if (
      axios.isCancel(error)
      || error?.code === 'ERR_CANCELED'
      || error?.name === 'CanceledError'
    ) {
      return Promise.reject(error)
    }

    const status = error.response?.status
    const silent = Boolean(error.config?.silentError)
    // 学生端同源约定：silentError 时默认不强制登出，除非显式 handleUnauthorized
    const forceUnauthorized = error.config?.handleUnauthorized === true

    if (status === 401 && (!silent || forceUnauthorized)) {
      clearAuth()
      if (router.currentRoute.value.path !== '/login') {
        router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }

    if (silent && !(status === 401 && forceUnauthorized)) {
      return Promise.reject(error)
    }

    const msg =
      error.response?.data?.message ||
      error.response?.data?.detail ||
      error.message ||
      '网络错误'
    return Promise.reject(new Error(msg))
  }
)

export function unwrap(response) {
  return response?.data ?? response ?? null
}

export default request
