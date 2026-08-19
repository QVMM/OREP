import request from '../utils/request'

export async function getResourceCenterWorkspace(teamId) {
  return request.get('/api/resource-center', {
    params: { teamId },
    silentError: true
  })
}

export async function createResourceFolder(teamId, label) {
  return request.post('/api/resource-center/folders', { teamId, label })
}

export async function renameResourceFolder(teamId, folderId, label) {
  return request.patch(`/api/resource-center/folders/${folderId}`, { teamId, label })
}

export async function deleteResourceFolder(teamId, folderId) {
  return request.delete(`/api/resource-center/folders/${folderId}`, {
    params: { teamId }
  })
}

export async function uploadResourceFile(teamId, folderKey, file, onProgress) {
  const form = new FormData()
  form.append('file', file)
  return request.post('/api/resource-center/files', form, {
    params: { teamId, folderKey },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 2 * 60 * 60 * 1000,
    onUploadProgress: onProgress
  })
}

export async function moveResourceFile(teamId, resourceId, folderKey) {
  return request.patch(`/api/resource-center/files/${resourceId}/folder`, {
    teamId,
    folderKey
  }, {
    silentError: true
  })
}

export async function deleteResourceFile(teamId, resourceId) {
  return request.delete(`/api/resource-center/files/${resourceId}`, {
    params: { teamId }
  })
}
