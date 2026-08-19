import request from '../../utils/request'
import { uploadTimeoutMs } from './submissionDraft'

export function unwrap(response) {
  return response?.data ?? response ?? {}
}

export async function fetchStudentHome() {
  return unwrap(await request.get('/api/student/home'))
}

export async function fetchCurrentTraining() {
  return unwrap(await request.get('/api/training-camps/current'))
}

export async function fetchTodayTraining() {
  return unwrap(await request.get('/api/training-camps/current/today'))
}

export async function fetchTodayTrainingOverview() {
  return unwrap(await request.get('/api/training-camps/current/today-overview'))
}

export async function fetchTrainingPlan() {
  return unwrap(await request.get('/api/training-camps/current/plan'))
}

export async function fetchTrainingDay(dayId) {
  return unwrap(await request.get(`/api/training-days/${dayId}`))
}

export async function fetchTrainingDayOverview(dayId) {
  return unwrap(await request.get(`/api/training-days/${dayId}/overview`))
}

export async function fetchTrainingSubmission(submissionId) {
  return unwrap(await request.get(`/api/training-submissions/${submissionId}`))
}

export async function fetchTrainingFeedback(submissionId) {
  return unwrap(await request.get(`/api/training-submissions/${submissionId}/feedback`))
}

export async function updateTrainingLearningProgress(resourceId, payload) {
  return unwrap(await request.patch(`/api/training-learning-resources/${resourceId}/progress`, payload))
}

export async function completeTrainingLearningResource(resourceId) {
  return unwrap(await request.post(`/api/training-learning-resources/${resourceId}/complete`))
}

/** 任务书驻留心跳（教师档案「任务书驻留时长」） */
export async function reportTaskBookDwell(dayId, payload) {
  if (!dayId) return null
  return unwrap(await request.post(`/api/training-days/${dayId}/dwell`, payload, { silentError: true }))
}

export async function uploadTrainingFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', 'task-submission')
  // 成果文件可能较大，避免全局 10s 超时被当成提交失败
  const response = await request.post('/api/upload', formData, { timeout: uploadTimeoutMs(file) })
  const data = unwrap(response)
  const fileUrl = data.url || data.fileUrl
  if (!fileUrl) {
    throw new Error('文件已上传，但服务器未返回文件地址，请重试')
  }
  return {
    fileUrl,
    fileName: data.name || file.name,
    fileSize: Number(data.size || file.size || 0),
    fileType: data.type || file.type || '',
    assetKind: 'MAIN'
  }
}

export async function submitTrainingTask(taskId, payload) {
  const id = Number(taskId)
  if (!Number.isFinite(id) || id <= 0) {
    throw new Error('缺少有效的训练任务，请从训练日重新进入提交页')
  }
  return unwrap(await request.post(`/api/project-teams/tasks/${id}/submissions`, payload, { timeout: 30000 }))
}
