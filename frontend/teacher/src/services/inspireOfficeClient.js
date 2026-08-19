import request from '../utils/request'
import { getToken } from '../utils/auth'

function dataOf(payload) {
  if (payload && typeof payload === 'object' && 'data' in payload) {
    return payload.data
  }
  return payload
}

export async function listInspireOfficeDocuments({ scope, teamId, q } = {}) {
  const params = {}
  if (scope && scope !== 'all') params.scope = scope
  if (teamId) params.teamId = teamId
  if (q) params.q = q
  const data = dataOf(await request.get('/api/inspire-office/documents', {
    params,
    silentError: true,
  }))
  return Array.isArray(data) ? data : []
}

export async function fetchInspireOfficeEditorSession(id, mode = 'edit') {
  return dataOf(await request.get(`/api/inspire-office/documents/${id}/editor-session`, {
    params: { mode },
    timeout: 30000,
  }))
}

export async function fetchSmartDoc(id, { silent = false } = {}) {
  return dataOf(await request.get(`/api/inspire-office/sdoc/${id}`, { silentError: silent }))
}

export async function saveSmartDoc(id, { content, updatedAt } = {}) {
  try {
    return dataOf(await request.put(`/api/inspire-office/sdoc/${id}`, { content, updatedAt }))
  } catch (err) {
    const status = err?.response?.status
    if (status) err.httpStatus = status
    throw err
  }
}

export async function createBlankInspireOfficeDocument({ title, ext = 'sdoc', scope = 'project', teamId } = {}) {
  return dataOf(await request.post('/api/inspire-office/documents/blank', {
    title,
    ext,
    scope,
    teamId: teamId || null,
  }))
}

export async function renameInspireOfficeDocument(id, title) {
  return dataOf(await request.put(`/api/inspire-office/documents/${id}`, { title }))
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

export async function uploadSmartDocAsset(file, kind = 'file') {
  if (!file) throw new Error('未选择文件')
  const form = new FormData()
  form.append('file', file)
  form.append('category', kind === 'image' ? 'images' : 'files')
  const res = await request.post('/api/upload', form, { timeout: 120000 })
  const data = res?.data || res
  if (!data?.url) throw new Error(res?.message || '上传失败')
  if (String(data.url).startsWith('data:')) throw new Error('禁止把文件以 base64 写入文档')
  return {
    url: data.url,
    name: data.name || file.name || '未命名文件',
    size: Number(data.size || file.size || 0),
    type: data.type || file.type || '',
  }
}

export function documentHref(doc) {
  const id = doc?.id
  if (!id) return '#'
  const ext = String(doc.ext || '').replace(/^\./, '').toLowerCase()
  if (ext === 'sdoc' || doc.documentType === 'sdoc') return `/inspire-office/sdoc/${id}`
  return '#'
}

export function downloadInspireOfficeDocument(id, fileName) {
  const token = getToken()
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
