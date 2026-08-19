import request from './request'

function unwrap(response) {
  return response?.data ?? response
}

export async function getEvidenceBundle(sessionId) {
  return unwrap(await request.get(`/api/ai-score/sessions/${sessionId}/evidence-bundle`))
}

export async function prepareEvidenceBundle(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/prepare-evidence`))
}
