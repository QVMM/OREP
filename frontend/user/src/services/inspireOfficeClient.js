import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'

function dataOf(payload) {
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return payload.data
  }
  return payload
}

export async function fetchInspireOfficeStatus() {
  return dataOf(await request.get('/api/inspire-office/status', { silentError: true }))
}

export async function listInspireOfficeDocuments({ scope, teamId, q } = {}) {
  const params = {}
  if (scope && scope !== 'all') params.scope = scope
  if (teamId) params.teamId = teamId
  if (q) params.q = q
  const data = dataOf(await request.get('/api/inspire-office/documents', {
    params,
    // 列表失败由页面文案处理，避免全局「操作失败」无上下文
    silentError: true,
  }))
  return Array.isArray(data) ? data : []
}

export async function fetchSmartDoc(id, { silent = false } = {}) {
  return dataOf(await request.get(`/api/inspire-office/sdoc/${id}`, { silentError: silent }))
}

export async function saveSmartDoc(id, { content, updatedAt } = {}) {
  return dataOf(await request.put(`/api/inspire-office/sdoc/${id}`, { content, updatedAt }))
}

export async function createBlankInspireOfficeDocument({ title, ext = 'docx', scope = 'personal', teamId } = {}) {
  return dataOf(await request.post('/api/inspire-office/documents/blank', {
    title,
    ext,
    scope,
    teamId: teamId || null,
  }))
}

export async function uploadInspireOfficeDocument({ file, title, scope = 'personal', teamId }) {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  form.append('scope', scope || 'personal')
  if (teamId) form.append('teamId', String(teamId))
  return dataOf(await request.post('/api/inspire-office/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  }))
}

export async function renameInspireOfficeDocument(id, title) {
  return dataOf(await request.put(`/api/inspire-office/documents/${id}`, { title }))
}

/** 迁移归属：personal | project | team */
export async function moveInspireOfficeDocument(id, { scope, teamId, syncResource = true } = {}) {
  return dataOf(await request.patch(`/api/inspire-office/documents/${id}/location`, {
    scope,
    teamId: teamId || null,
    syncResource,
  }))
}

/** 项目/团队文档：把当前内容再同步一份到资源中心 */
export async function syncInspireOfficeToResource(id) {
  return dataOf(await request.post(`/api/inspire-office/documents/${id}/sync-resource`))
}

export async function duplicateInspireOfficeDocument(id, { title, scope = 'personal', teamId } = {}) {
  return dataOf(await request.post(`/api/inspire-office/documents/${id}/duplicate`, {
    title: title || null,
    scope,
    teamId: teamId || null,
  }))
}

export async function deleteInspireOfficeDocument(id) {
  return dataOf(await request.delete(`/api/inspire-office/documents/${id}`))
}

/** 浏览器下载：带 token 打开下载 URL */
export function downloadInspireOfficeDocument(id, fileName) {
  const token = getUserToken()
  const base = `/api/inspire-office/documents/${id}/download`
  const url = token
    ? `${base}${base.includes('?') ? '&' : '?'}t=${encodeURIComponent(token)}`
    : base
  const a = document.createElement('a')
  a.href = url
  a.download = fileName || 'document'
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
}

export async function fetchInspireOfficeEditorSession(id, mode = 'edit') {
  return dataOf(await request.get(`/api/inspire-office/documents/${id}/editor-session`, {
    params: { mode },
    timeout: 30000,
  }))
}

/**
 * 启发 Office 在线/编辑时长心跳。
 * @param {string|number} id 文档 ID
 * @param {{ sessionId: string, visible?: boolean, active?: boolean, editing?: boolean, reset?: boolean }} payload
 */
export async function reportInspireOfficePresence(id, payload = {}) {
  return dataOf(await request.post(`/api/inspire-office/documents/${id}/presence`, {
    sessionId: payload.sessionId,
    visible: payload.visible !== false,
    active: payload.active !== false,
    editing: !!payload.editing,
    reset: !!payload.reset,
  }, {
    silentError: true,
    timeout: 12000,
  }))
}

export async function joinSdocCollab(id, sessionId) {
  return dataOf(await request.post(`/api/inspire-office/sdoc/${id}/collab/join`, { sessionId }, { silentError: true }))
}

export async function reportSdocCollabState(id, payload = {}) {
  return dataOf(await request.post(`/api/inspire-office/sdoc/${id}/collab/state`, payload, { silentError: true, timeout: 8000 }))
}

export async function fetchSdocCollabSnapshot(id) {
  return dataOf(await request.get(`/api/inspire-office/sdoc/${id}/collab/snapshot`, { silentError: true }))
}

export async function syncSdocCollab(id, payload = {}) {
  return dataOf(await request.post(`/api/inspire-office/sdoc/${id}/collab/sync`, payload, { silentError: true, timeout: 12000 }))
}

export async function leaveSdocCollab(id, sessionId) {
  return dataOf(await request.post(`/api/inspire-office/sdoc/${id}/collab/leave`, { sessionId }, { silentError: true }))
}

export async function listInspireOfficeVersions(id) {
  const data = dataOf(await request.get(`/api/inspire-office/documents/${id}/versions`))
  return Array.isArray(data) ? data : []
}

export async function createInspireOfficeSnapshot(id, label) {
  return dataOf(await request.post(`/api/inspire-office/documents/${id}/versions`, { label: label || null }))
}

export async function restoreInspireOfficeVersion(id, versionNo) {
  return dataOf(await request.post(`/api/inspire-office/documents/${id}/versions/${versionNo}/restore`))
}

export async function fetchMyProjectTeams() {
  const payload = dataOf(await request.get('/api/project-teams/my', { silentError: true }))
  return Array.isArray(payload) ? payload : []
}
