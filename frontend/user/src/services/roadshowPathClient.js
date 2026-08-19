import request from '../utils/request'

export function getScriptMeter(scriptId) {
  return request.get(`/api/roadshow/path/script/${scriptId}/meter`, { silentError: true })
}

export function compilePath(scriptId) {
  return request.post('/api/roadshow/path/compile', { scriptId })
}

export function getPath(id) {
  return request.get(`/api/roadshow/path/${id}`)
}

export function ackHole(id, holeId) {
  return request.post(`/api/roadshow/path/${id}/ack-hole`, { holeId })
}

export function confirmPath(id) {
  return request.post(`/api/roadshow/path/${id}/confirm`)
}

export function printPath(id) {
  return request.post(`/api/roadshow/path/${id}/print`, {}, { timeout: 60000 })
}

export async function downloadPptx(id, fileName) {
  const blob = await request.get(`/api/roadshow/path/${id}/download`, {
    responseType: 'blob',
    timeout: 60000,
    silentError: true,
  })
  if (blob && typeof blob.type === 'string' && blob.type.includes('json')) {
    const text = await blob.text()
    let message = '下载失败'
    try {
      const json = JSON.parse(text)
      message = json.message || json.detail || message
    } catch {
      /* keep default */
    }
    throw new Error(message)
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName || '路演台.pptx'
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function listMyScripts() {
  return request.get('/api/script/my', { silentError: true })
}

export function listLegacyCandidates() {
  return request.get('/api/roadshow/legacy/candidates', { silentError: true })
}

export function listMyDecks() {
  return request.get('/api/roadshow/legacy/mine', { silentError: true })
}

export function ingestLegacyFile(file) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/api/roadshow/legacy/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function ingestLegacyDocument(documentId) {
  return request.post('/api/roadshow/legacy/from-document', { documentId })
}

export function attachDeck(pathId, deckId) {
  return request.post(`/api/roadshow/path/${pathId}/attach-deck`, { deckId })
}

export function getLegacyPages(deckId) {
  return request.get(`/api/roadshow/legacy/${deckId}/pages`)
}

export function alignPath(pathId) {
  return request.get(`/api/roadshow/path/${pathId}/align`)
}

export function slidePreviewUrl(deckId, page, bust) {
  const token = localStorage.getItem('orep_user_token') || localStorage.getItem('token') || ''
  const q = new URLSearchParams({ t: token })
  if (bust) q.set('v', String(bust))
  return `/api/roadshow/legacy/${deckId}/slide/${page}?${q.toString()}`
}

export function applyLegacyPage(deckId, payload) {
  return request.post(`/api/roadshow/legacy/${deckId}/apply`, payload)
}

export async function downloadLegacyDeck(deckId, fileName) {
  const blob = await request.get(`/api/roadshow/legacy/${deckId}/download`, {
    responseType: 'blob',
    timeout: 60000,
    silentError: true,
  })
  if (blob && typeof blob.type === 'string' && blob.type.includes('json')) {
    const text = await blob.text()
    throw new Error(text || '下载失败')
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName || '改过的PPT.pptx'
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
