import request, { unwrap } from '../utils/request'
import {
  createTeamTask,
  fetchMyTeams,
  fetchTeamDashboard,
  fetchTeacherReviewQueue,
  fetchTeacherSubmission,
  reviewSubmission,
} from '../api'

export async function fetchTeacherCollaborationSummary() {
  return unwrap(await request.get('/api/collaboration/summary')) || {}
}

export async function fetchTeacherCollaborationItems(view, teamId) {
  return unwrap(await request.get('/api/collaboration/items', {
    params: {
      view,
      ...(teamId && teamId !== 'all' ? { teamId } : {}),
    },
  })) || { items: [], hasMore: false }
}

export async function acceptTeacherCollaborationRequest(id) {
  return unwrap(await request.post(`/api/collaboration/requests/${id}/accept`, {}))
}

export async function declineTeacherCollaborationRequest(id, reason = '') {
  return unwrap(await request.post(`/api/collaboration/requests/${id}/decline`, { reason }))
}

export async function withdrawTeacherCollaborationRequest(id) {
  return unwrap(await request.post(`/api/collaboration/requests/${id}/withdraw`, {}))
}

export async function fetchTeacherCollaborationTeams() {
  return fetchMyTeams()
}

export async function fetchTeacherTeamTasks(teamId) {
  const dashboard = await fetchTeamDashboard(teamId)
  return Array.isArray(dashboard?.tasks) ? dashboard.tasks : []
}

export async function fetchTeacherPendingReviews() {
  return fetchTeacherReviewQueue()
}

export async function fetchTeacherReviewDetail(submissionId) {
  return fetchTeacherSubmission(submissionId)
}

export async function publishTeacherCollaborationTask(teamId, payload) {
  return createTeamTask(teamId, {
    ...payload,
    sourceType: 'TEACHER_ASSIGNMENT',
    stageKey: 'COLLABORATION',
    reviewRequired: true,
  })
}

export async function submitTeacherCollaborationReview(submissionId, payload) {
  return reviewSubmission(submissionId, payload)
}
