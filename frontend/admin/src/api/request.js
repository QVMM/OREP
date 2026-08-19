import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { trackApiRequest } from '../utils/monitor'
import { clearAdminAuth, getAdminToken } from '../utils/authStorage'

// 创建 axios 实例
const request = axios.create({
  baseURL: '',
  timeout: 15000,
})

// 请求拦截器：自动携带 token
request.interceptors.request.use(
  (config) => {
    config.metadata = { startTime: Date.now() }
    const token = getAdminToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (response) => {
    trackApiRequest(response.config, response.status, Date.now() - (response.config.metadata?.startTime || Date.now()))
    return response.data
  },
  (error) => {
    if (error.config) {
      trackApiRequest(
        error.config,
        error.response?.status || 0,
        Date.now() - (error.config.metadata?.startTime || Date.now()),
        error.response?.data?.message || error.message || ''
      )
    }
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        clearAdminAuth()
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
      } else if (status === 403) {
        ElMessage.error(data?.message || '无权执行该操作')
      } else if (status === 500 && !data?.message) {
        ElMessage.error('后端服务异常或未启动，请检查 8080 端口')
      } else {
        ElMessage.error(data?.message || `请求失败 (${status})`)
      }
    } else {
      ElMessage.error('无法连接后端服务（8080），请确认 backend 已启动')
    }
    return Promise.reject(error)
  }
)

export default request
