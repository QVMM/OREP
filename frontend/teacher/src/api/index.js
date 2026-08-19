import request, { unwrap } from '../utils/request'

const TEACHER_LEARNING_UPLOAD_TIMEOUT_MS = 2 * 60 * 60 * 1000

export async function login(username, password) {
  return unwrap(await request.post('/api/auth/login', { username, password }))
}

export async function fetchMeetings() {
  return unwrap(await request.get('/api/meeting/list')) || []
}

export async function createMeeting(payload) {
  return unwrap(await request.post('/api/meeting/create', payload))
}

export async function fetchMeetingDetail(id) {
  return unwrap(await request.get(`/api/meeting/${id}/detail`))
}

export async function fetchMyTeams() {
  return unwrap(await request.get('/api/project-teams/my')) || []
}

export async function fetchTeacherReviewQueue() {
  return unwrap(await request.get('/api/teacher/review-queue')) || []
}

export async function fetchTeacherSubmission(submissionId) {
  return unwrap(await request.get(`/api/teacher/submissions/${submissionId}`))
}

export async function fetchTeamDashboard(teamId) {
  return unwrap(await request.get(`/api/project-teams/${teamId}/dashboard`))
}

export async function fetchCandidateMembers() {
  return unwrap(await request.get('/api/project-teams/candidate-members')) || []
}

export async function fetchCompetitionTracks() {
  return unwrap(await request.get('/api/project-teams/tracks')) || []
}

export async function createTeam(payload) {
  return unwrap(await request.post('/api/project-teams', payload))
}

export async function createTeamTask(teamId, payload) {
  return unwrap(await request.post(`/api/project-teams/${teamId}/tasks`, payload))
}

export async function fetchTeamTask(teamId, taskId) {
  return unwrap(await request.get(`/api/project-teams/${teamId}/tasks/${taskId}`))
}

export async function updateTeamTask(taskId, payload) {
  return unwrap(await request.patch(`/api/project-teams/tasks/${taskId}`, payload))
}

export async function reviewSubmission(submissionId, payload) {
  return unwrap(await request.post(`/api/project-teams/submissions/${submissionId}/review`, payload))
}

export async function fetchAiReportSummary() {
  return unwrap(await request.get('/api/ai-score/reports/summary'))
}

export async function fetchStatisticsOverview() {
  return unwrap(await request.get('/api/statistics/overview'))
}

export async function fetchCourses() {
  return unwrap(await request.get('/api/courses')) || []
}

export async function fetchTeacherWorkbench() {
  return unwrap(await request.get('/api/teacher/portal/workbench')) || {}
}

export async function fetchTeacherCamps() {
  return unwrap(await request.get('/api/teacher/portal/camps')) || []
}

export async function createTeacherCamp(payload) {
  return unwrap(await request.post('/api/teacher/portal/camps', payload)) || {}
}

export async function fetchTeacherCamp(campId) {
  return unwrap(await request.get('/api/teacher/portal/camp', { params: campId ? { campId } : {} })) || {}
}

export async function rescheduleTeacherCamp(campId, startDate) {
  return unwrap(await request.patch(`/api/teacher/portal/camps/${campId}/schedule`, { startDate })) || {}
}

export async function extendTeacherCamp(campId, payload) {
  return unwrap(await request.patch(`/api/teacher/portal/camps/${campId}/duration`, payload)) || {}
}

export async function deleteTeacherCamp(campId, payload) {
  return unwrap(await request.delete(`/api/teacher/portal/camps/${campId}`, { data: payload })) || {}
}

export async function updateTeacherTrainingDay(dayId, payload) {
  return unwrap(await request.patch(`/api/teacher/portal/camp/days/${dayId}`, payload))
}

export async function earlyUnlockTeacherTrainingDay(dayId) {
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/early-unlock`))
}

export async function restoreTeacherTrainingDaySchedule(dayId) {
  return unwrap(await request.delete(`/api/teacher/portal/camp/days/${dayId}/early-unlock`))
}

export async function fetchTeamCertificates(teamId) {
  return unwrap(await request.get('/api/teacher/student-growth/certificates', { params: { teamId } })) || []
}

export async function createTeamCertificate(payload) {
  return unwrap(await request.post('/api/teacher/student-growth/certificates', payload))
}

export async function uploadTeamCertificate(formData) {
  return unwrap(await request.post('/api/teacher/student-growth/certificates/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }))
}

export async function revokeTeamCertificate(certificateId) {
  return unwrap(await request.post(`/api/teacher/student-growth/certificates/${certificateId}/revoke`))
}

export async function uploadTeacherTrainingDayImage(dayId, file) {
  const form = new FormData()
  form.append('file', file)
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/content-images`, form))
}

export async function uploadTeacherTrainingDayAttachment(dayId, file) {
  const form = new FormData()
  form.append('file', file)
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/attachments`, form))
}

export async function deleteTeacherTrainingDayAttachment(dayId, attachmentId) {
  return unwrap(await request.delete(`/api/teacher/portal/camp/days/${dayId}/attachments/${attachmentId}`))
}

export async function reorderTeacherTrainingDayAttachments(dayId, attachmentIds) {
  return unwrap(await request.patch(`/api/teacher/portal/camp/days/${dayId}/attachments/order`, { attachmentIds })) || []
}

export async function uploadTeacherLearningResource(dayId, file, metadata = {}, options = {}) {
  const form = new FormData()
  form.append('file', file)
  form.append('title', metadata.title || '')
  form.append('description', metadata.description || '')
  form.append('required', String(metadata.required !== false))
  form.append('durationSeconds', String(metadata.durationSeconds || 0))
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/learning-resources/files`, form, {
    timeout: options.timeout ?? TEACHER_LEARNING_UPLOAD_TIMEOUT_MS,
    onUploadProgress: options.onUploadProgress
  }))
}

export async function createTeacherLearningLink(dayId, payload) {
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/learning-resources/links`, payload))
}

export async function parseTeacherLearningEmbed(dayId, url) {
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/learning-resources/embed/parse`, { url }))
}

export async function createTeacherLearningEmbed(dayId, payload) {
  return unwrap(await request.post(`/api/teacher/portal/camp/days/${dayId}/learning-resources/embed`, payload))
}

export async function updateTeacherLearningResource(dayId, resourceId, payload) {
  return unwrap(await request.patch(`/api/teacher/portal/camp/days/${dayId}/learning-resources/${resourceId}`, payload))
}

export async function deleteTeacherLearningResource(dayId, resourceId) {
  return unwrap(await request.delete(`/api/teacher/portal/camp/days/${dayId}/learning-resources/${resourceId}`))
}

export async function reorderTeacherLearningResources(dayId, resourceIds) {
  return unwrap(await request.patch(`/api/teacher/portal/camp/days/${dayId}/learning-resources/order`, { resourceIds })) || []
}

export async function fetchTeacherRecordings() {
  return unwrap(await request.get('/api/teacher/portal/recordings')) || []
}

export async function fetchTeacherResources() {
  return unwrap(await request.get('/api/teacher/portal/resources')) || []
}

/** 学生 AI PPT 生成记录 */
export async function fetchTeacherAiPptWorks() {
  return unwrap(await request.get('/api/teacher/portal/ai-ppt')) || []
}

/** 学生 AI/编辑器讲稿 */
export async function fetchTeacherAiScripts() {
  return unwrap(await request.get('/api/teacher/portal/ai-scripts')) || []
}

export async function fetchTeacherExams() {
  return unwrap(await request.get('/api/teacher/portal/exams')) || {}
}

export async function fetchTeacherAiTodos() {
  return unwrap(await request.get('/api/teacher/portal/ai-todos')) || []
}

export async function publishTeacherAiTodo(todoId, payload) {
  return unwrap(await request.post(`/api/teacher/portal/ai-todos/${todoId}/publish`, payload))
}

export async function publishAiScoreTaskBook(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/task-book/publish`))
}

export async function confirmAiScoreSession(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/confirm`))
}

export async function resolveAiScoreChallenge(sessionId, challengeId, action, reason = '') {
  return unwrap(await request.post(
    `/api/ai-score/sessions/${sessionId}/challenges/${encodeURIComponent(challengeId)}/resolve`,
    { action, reason }
  ))
}

export async function fetchTeacherAnalytics() {
  return unwrap(await request.get('/api/teacher/portal/analytics')) || {}
}

/** 学生档案列表（训练/学习/路演摘要） */
export async function fetchTeacherStudents() {
  return unwrap(await request.get('/api/teacher/portal/students')) || { students: [], camp: {} }
}

/** 单个学生详细档案 */
export async function fetchTeacherStudentProfile(studentUserId) {
  return unwrap(await request.get(`/api/teacher/portal/students/${studentUserId}`)) || {}
}

export async function sendTeacherReminder(payload) {
  return unwrap(await request.post('/api/teacher/portal/reminders', payload))
}

export async function fetchPositionRoles() {
  return unwrap(await request.get('/api/project-teams/position-roles')) || []
}

export async function createPositionRole(payload) {
  return unwrap(await request.post('/api/project-teams/position-roles', payload))
}

export async function updateTeamMemberPosition(teamId, memberUserId, payload) {
  return unwrap(await request.patch(`/api/project-teams/${teamId}/members/${memberUserId}/position`, payload))
}

export async function addTeamMember(teamId, payload) {
  return unwrap(await request.post(`/api/project-teams/${teamId}/members`, payload))
}

export async function removeTeamMember(teamId, memberUserId) {
  return unwrap(await request.delete(`/api/project-teams/${teamId}/members/${memberUserId}`))
}

export async function createTeamMaterial(teamId, payload) {
  return unwrap(await request.post(`/api/project-teams/${teamId}/materials`, payload))
}

/** 团队共享资源：实际上传文件 */
export async function uploadTeamMaterial(teamId, { file, name, materialType, description }) {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  if (materialType) form.append('materialType', materialType)
  if (description) form.append('description', description)
  return unwrap(await request.post(`/api/project-teams/${teamId}/materials/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 5 * 60 * 1000,
  }))
}

/** 本组织/本班用户列表（教师按数据范围过滤） */
export async function fetchOrgUsers() {
  return unwrap(await request.get('/api/user/list')) || []
}

/** 组织架构选项 + 当前操作者归属范围 */
export async function fetchOrganizationOptions() {
  return unwrap(await request.get('/api/user/organization/options')) || { units: [], groups: [], operatorScope: null }
}

/** 创建账号（教师端仅能落到本组织本班，后端强制） */
export async function createOrgUser(payload) {
  return unwrap(await request.post('/api/user', payload))
}
