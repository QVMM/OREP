import { inject } from 'vue'

export const SDOC_SPLIT_KEY = 'sdocSplit'

export function useSdocSplit() {
  return inject(SDOC_SPLIT_KEY, null)
}

export function officeKind(doc) {
  const raw = String(doc?.documentType || doc?.documentKind || doc?.ext || '')
    .replace(/^\./, '')
    .toLowerCase()
  if (raw === 'sdoc') return 'sdoc'
  if (['pptx', 'ppt', 'odp', 'slide'].includes(raw)) return 'slide'
  if (['xlsx', 'xls', 'ods', 'csv', 'sheet', 'cell'].includes(raw)) return 'sheet'
  if (['docx', 'doc', 'odt', 'word'].includes(raw)) return 'word'
  if (!raw) return 'sdoc'
  return 'word'
}

export function officeKindLabel(kind) {
  return ({ sdoc: '智能文档', word: 'Word', slide: '演示', sheet: '表格' })[kind] || '文档'
}

export function isSdocKind(doc) {
  return officeKind(doc) === 'sdoc'
}
