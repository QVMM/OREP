import request from '../../../../utils/request'

const CATEGORY = {
  image: 'images',
  file: 'files',
  media: 'files',
}

export async function uploadSmartDocAsset(file, kind = 'file') {
  if (!file) throw new Error('未选择文件')
  const form = new FormData()
  form.append('file', file)
  form.append('category', CATEGORY[kind] || 'files')
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

export function formatBytes(size) {
  const n = Number(size) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function cloudDocHref(doc) {
  const id = doc?.id
  if (!id) return '#'
  const ext = String(doc.ext || '').replace(/^\./, '').toLowerCase()
  if (ext === 'sdoc' || doc.documentType === 'sdoc') return `/inspire-office/sdoc/${id}`
  return `/inspire-office/workbench?focus=${encodeURIComponent(id)}`
}
