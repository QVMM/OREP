import request from '../utils/request'

function dataOf(response) {
  return response?.data ?? response
}

export async function fetchCollaborationSummary() {
  // silentError：后台摘要失败不弹「请求失败」；
  // 真正的登录过期由 request 拦截器在「带 Authorization 仍 401」时处理
  return dataOf(await request.get('/api/collaboration/summary', {
    silentError: true,
  }))
}

export async function fetchCollaborationItems(view, teamId, cursor) {
  return dataOf(await request.get('/api/collaboration/items', {
    params: {
      view,
      ...(teamId ? { teamId } : {}),
      ...(cursor ? { cursor } : {}),
    },
    silentError: true,
  }))
}

export async function createCollaborationRequest(payload, idempotencyKey) {
  return dataOf(await request.post('/api/collaboration/requests', payload, {
    headers: { 'Idempotency-Key': idempotencyKey },
    silentError: true,
  }))
}

export async function createCollaborationRequests(payload, idempotencyKey) {
  return dataOf(await request.post('/api/collaboration/requests/batch', payload, {
    headers: { 'Idempotency-Key': idempotencyKey },
    silentError: true,
  }))
}

export async function fetchCollaborationRequest(id) {
  return dataOf(await request.get(`/api/collaboration/requests/${id}`, {
    silentError: true,
  }))
}

export async function acceptCollaborationRequest(id) {
  return dataOf(await request.post(
    `/api/collaboration/requests/${id}/accept`,
    {},
    { silentError: true }
  ))
}

export async function declineCollaborationRequest(id, reason = '') {
  return dataOf(await request.post(
    `/api/collaboration/requests/${id}/decline`,
    { reason },
    { silentError: true }
  ))
}

export async function withdrawCollaborationRequest(id) {
  return dataOf(await request.post(
    `/api/collaboration/requests/${id}/withdraw`,
    {},
    { silentError: true }
  ))
}

export async function fetchCollaborationTeams() {
  const payload = dataOf(await request.get('/api/project-teams/my', { silentError: true }))
  return Array.isArray(payload) ? payload : []
}

export async function fetchCollaborationTeamDashboard(teamId) {
  return dataOf(await request.get(
    `/api/project-teams/${teamId}/dashboard`,
    { silentError: true }
  ))
}
