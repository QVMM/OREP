import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

function unwrap(response) {
  return response.data
}

export const pptApi = {
  health() {
    return apiClient.get('/ppt/health').then(unwrap)
  },

  getFormConfig(domain) {
    return apiClient.get(`/ppt/forms/${domain}`).then(unwrap)
  },

  submitQuestionnaire(data) {
    return apiClient.post('/ppt/questionnaire/submit', data).then(unwrap)
  },

  createTask(data) {
    return apiClient.post('/ppt/v2/task/create', data).then(unwrap)
  },

  getTask(taskId) {
    return apiClient.get(`/ppt/task/${taskId}`).then(unwrap)
  },

  getTaskStatus(taskId) {
    return apiClient.get(`/ppt/task/${taskId}/status`).then(unwrap)
  },

  confirmOutline(taskId, data) {
    return apiClient.post(`/ppt/task/${taskId}/confirm`, data).then(unwrap)
  },

  getHtmlPages(taskId) {
    return apiClient.get(`/ppt/task/${taskId}/html-pages`).then(unwrap)
  },

  cancelTask(taskId) {
    return apiClient.post(`/ppt/task/${taskId}/cancel`).then(unwrap)
  },

  getUserTasks(userId, status) {
    return apiClient.get(`/ppt/user/${userId}/tasks`, {
      params: status ? { status } : {}
    }).then(unwrap)
  },

  getThemes() {
    return apiClient.get('/ppt/themes').then(unwrap)
  },

  getDownloadUrl(taskId) {
    return `/api/ppt/task/${taskId}/download`
  },

  fetchAgentProviders() {
    return apiClient.get('/ppt/providers').then(unwrap)
  },

  fetchAgentTemplates() {
    return apiClient.get('/ppt/templates').then(unwrap)
  },

  uploadAgentFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/ppt/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000
    }).then(unwrap)
  },

  generateAgentPresentation(payload) {
    return apiClient.post('/ppt/generate', payload, {
      timeout: 120000
    }).then(unwrap)
  },

  resumeAgentGeneration(jobId) {
    return apiClient.post(`/ppt/generate/${jobId}/resume`, {}, {
      timeout: 120000
    }).then(unwrap)
  },

  getAgentJobStatus(jobId) {
    return apiClient.get(`/ppt/status/${jobId}`).then(unwrap)
  },

  cancelAgentJob(jobId) {
    return apiClient.post(`/ppt/status/${jobId}/cancel`).then(unwrap)
  },

  getAgentPreview(jobId) {
    return apiClient.get(`/ppt/preview/${jobId}`, {
      timeout: 120000
    }).then(unwrap)
  },

  getAgentCritic(jobId) {
    return apiClient.get(`/ppt/critic/${jobId}`).then(unwrap)
  },

  getAgentDownloadUrl(jobId) {
    return `/api/ppt/download/${jobId}`
  },

  getAgentWebSocketUrl(jobId, sinceSeq = 0) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/api/ppt/ws/${jobId}?since_seq=${sinceSeq}`
  }
}

export default {
  pptApi
}
