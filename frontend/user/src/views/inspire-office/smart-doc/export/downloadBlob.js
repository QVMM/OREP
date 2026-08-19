export function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function safeFileName(name, ext) {
  const base = String(name || '未命名文档').replace(/[\\/:*?"<>|]+/g, '_').trim() || '未命名文档'
  return `${base}.${ext}`
}
