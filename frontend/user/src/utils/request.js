import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { trackApiRequest } from './monitor'
import { clearUserAuth, getUserToken } from './authStorage'

// 创建 axios 实例
const request = axios.create({
  timeout: 10000
})

/** 并行 401 只提示一次，避免引导页刷屏 */
let lastUnauthorizedToastAt = 0

function toastUnauthorizedOnce(message = '登录已过期，请重新登录') {
  const now = Date.now()
  if (now - lastUnauthorizedToastAt < 2500) return
  lastUnauthorizedToastAt = now
  ElMessage.error(message)
}

function extractErrorMessage(error) {
  if (!error) return ''
  if (error.code === 'ECONNABORTED') {
    return '请求响应较慢，请稍后查看结果或重试'
  }
  const status = error.response?.status
  const responseData = error.response?.data
  if (status === 423) {
    return (
      (typeof responseData?.message === 'string' && responseData.message.trim()) ||
      (typeof responseData?.detail === 'string' && responseData.detail.trim()) ||
      '训练日尚未开放，暂时不能提交'
    )
  }
  if (status === 409) {
    return (
      (typeof responseData?.message === 'string' && responseData.message.trim()) ||
      (typeof responseData?.detail === 'string' && responseData.detail.trim()) ||
      '还有必学内容未完成，请先完成学习再提交'
    )
  }
  if (typeof responseData?.detail === 'string' && responseData.detail.trim()) {
    return responseData.detail
  }
  if (typeof responseData?.message === 'string' && responseData.message.trim()) {
    return responseData.message
  }
  if (typeof error.message === 'string' && error.message.trim()) {
    return error.message
  }
  return ''
}

function requestHadAuthHeader(config) {
  if (!config?.headers) return false
  const h = config.headers
  // axios 可能把 headers 做成 AxiosHeaders
  const auth =
    (typeof h.get === 'function' ? h.get('Authorization') || h.get('authorization') : null) ||
    h.Authorization ||
    h.authorization
  return Boolean(auth)
}

function isPublicShellRoute() {
  const route = router.currentRoute?.value
  if (!route) return false
  if (route.meta?.publicShell) return true
  const path = route.path || ''
  return path === '/login' || path === '/intro'
}

// 请求拦截器：添加 token
request.interceptors.request.use(
  (config) => {
    config.metadata = { startTime: Date.now() }
    const token = getUserToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误
request.interceptors.response.use(
  (response) => {
    trackApiRequest(response.config, response.status, Date.now() - (response.config.metadata?.startTime || Date.now()))
    const data = response.data
    // 统一处理业务错误码（后端 HTTP 200 但 body.code !== 200）
    if (data && typeof data.code === 'number' && data.code !== 200) {
      const err = new Error(data.message || '操作失败')
      err.httpStatus = response.status || 200
      err.bizCode = data.code
      if (!response.config?.silentError) {
        ElMessage.error(data.message || '操作失败')
        err.alreadyToasted = true
      }
      return Promise.reject(err)
    }
    return data
  },
  (error) => {
    if (
      axios.isCancel(error) ||
      error?.code === 'ERR_CANCELED' ||
      error?.name === 'CanceledError'
    ) {
      return Promise.reject(error)
    }
    if (error.config) {
      trackApiRequest(
        error.config,
        error.response?.status || 0,
        Date.now() - (error.config.metadata?.startTime || Date.now()),
        extractErrorMessage(error)
      )
    }

    const status = error.response?.status
    if (status != null) error.httpStatus = status
    else if (error.httpStatus == null) error.httpStatus = 0
    const silent = Boolean(error.config?.silentError)
    const hadAuth = requestHadAuthHeader(error.config)

    // —— 401：仅「带 token 仍被拒」才算登录过期 ——
    // 未登录时静默接口（通知/协作摘要等）也会 401，绝不能提示「登录已过期」
    if (status === 401) {
      if (hadAuth) {
        clearUserAuth()
        if (!isPublicShellRoute()) {
          router.replace('/login')
        }
        toastUnauthorizedOnce()
      }
      return Promise.reject(error)
    }

    if (silent) {
      return Promise.reject(error)
    }

    if (error.response) {
      const { data } = error.response
      const message = extractErrorMessage(error) || (status === 403 ? '没有权限访问' : '请求失败')
      ElMessage.error(status === 403 && !data?.message && !data?.detail ? '没有权限访问' : message)
      error.alreadyToasted = true
    } else {
      ElMessage.error(extractErrorMessage(error) || '网络错误，请检查网络连接')
      error.alreadyToasted = true
    }
    return Promise.reject(error)
  }
)

export default request
