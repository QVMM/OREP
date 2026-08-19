import request from './request'

const AI_SCORE_UPLOAD_TIMEOUT_MS = 2 * 60 * 60 * 1000
const AI_SCORE_UPLOAD_BASE_URL = import.meta.env.VITE_AI_SCORE_UPLOAD_BASE_URL || ''

function unwrap(response) {
  return response?.data ?? response
}

function uploadUrl(path) {
  return AI_SCORE_UPLOAD_BASE_URL ? `${AI_SCORE_UPLOAD_BASE_URL}${path}` : path
}

export async function uploadAiScoreSession(formData, options = {}) {
  return unwrap(await request.post(uploadUrl('/api/ai-score/upload-session'), formData, {
    timeout: AI_SCORE_UPLOAD_TIMEOUT_MS,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: options.onUploadProgress
  }))
}

export async function createAiScorePreprocessJob(formData, options = {}) {
  return unwrap(await request.post(uploadUrl('/api/ai-score/preprocess-jobs'), formData, {
    timeout: AI_SCORE_UPLOAD_TIMEOUT_MS,
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: options.onUploadProgress
  }))
}

export async function getAiScorePreprocessJob(jobId) {
  return unwrap(await request.get(uploadUrl(`/api/ai-score/preprocess-jobs/${jobId}`)))
}

export async function getAiScoreUploadTasks(completedLimit = 10) {
  return unwrap(await request.get(uploadUrl('/api/ai-score/upload-tasks'), {
    params: { completedLimit },
    silentError: true,
    handleUnauthorized: true
  }))
}
