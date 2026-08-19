export function createEmptyTableJSON(rows = 3, cols = 3, withHeaderRow = true) {
  const makeCell = (type) => ({
    type,
    content: [{ type: 'paragraph' }],
  })
  const makeRow = (type) => ({
    type: 'tableRow',
    content: Array.from({ length: cols }, () => makeCell(type)),
  })
  const content = []
  if (withHeaderRow) content.push(makeRow('tableHeader'))
  const bodyRows = withHeaderRow ? rows - 1 : rows
  for (let i = 0; i < Math.max(1, bodyRows); i += 1) content.push(makeRow('tableCell'))
  return { type: 'table', content }
}

export function createColumnsJSON(count = 2) {
  const n = count === 3 ? 3 : 2
  return {
    type: 'columns',
    attrs: { count: n },
    content: Array.from({ length: n }, () => ({
      type: 'column',
      content: [{ type: 'paragraph' }],
    })),
  }
}

export function createFileCardJSON({ url, name, size, mime } = {}) {
  return {
    type: 'fileCard',
    attrs: {
      url: url || '',
      name: name || '附件',
      size: Number(size) || 0,
      mime: mime || '',
    },
  }
}

export function createCloudDocJSON(doc = {}) {
  return {
    type: 'cloudDoc',
    attrs: {
      documentId: String(doc.id || ''),
      title: doc.title || '云文档',
      ext: String(doc.ext || '').replace(/^\./, ''),
      kind: doc.documentType || (String(doc.ext || '').includes('sdoc') ? 'sdoc' : 'word'),
      href: doc.href || '#',
    },
  }
}

export function createDateChipJSON(value) {
  return { type: 'dateChip', attrs: { value: value || '' } }
}

export function createProtectedRegionJSON({ id, minRole = 'TEACHER', label = '仅教师可见' } = {}) {
  return {
    type: 'protectedRegion',
    attrs: {
      id: id || `pr_${Date.now().toString(36)}`,
      minRole,
      label,
      sealed: false,
    },
    content: [{ type: 'paragraph' }],
  }
}

export function createMediaBlockJSON({ src, kind, name } = {}) {
  return {
    type: 'mediaBlock',
    attrs: {
      src: src || '',
      kind: kind === 'audio' ? 'audio' : 'video',
      name: name || '',
    },
  }
}

export const SLASH_GROUP_ORDER = ['基础', '结构', '图示', '媒体']

export const SLASH_CATALOG = [
  { key: 'paragraph', label: '正文', group: '基础', icon: 'paragraph' },
  { key: 'h1', label: '标题 1', group: '基础', icon: 'h1' },
  { key: 'h2', label: '标题 2', group: '基础', icon: 'h2' },
  { key: 'h3', label: '标题 3', group: '基础', icon: 'h3' },
  { key: 'bullet', label: '无序列表', group: '基础', icon: 'bullet' },
  { key: 'ordered', label: '有序列表', group: '基础', icon: 'ordered' },
  { key: 'task', label: '待办列表', group: '基础', icon: 'task' },
  { key: 'quote', label: '引用', group: '基础', icon: 'quote' },
  { key: 'code', label: '代码块', group: '基础', icon: 'codeBlock' },
  { key: 'hr', label: '分隔线', group: '基础', icon: 'hr' },
  { key: 'callout', label: '高亮块', group: '基础', icon: 'callout' },
  { key: 'table', label: '表格', group: '结构', icon: 'table' },
  { key: 'cols2', label: '两栏', group: '结构', icon: 'cols2' },
  { key: 'cols3', label: '三栏', group: '结构', icon: 'cols3' },
  { key: 'protect', label: '内容保护区', group: '结构', icon: 'protect' },
  { key: 'mindmap', label: '思维导图', group: '图示', icon: 'mindmap' },
  { key: 'flow', label: '流程图', group: '图示', icon: 'flow' },
  { key: 'image', label: '图片', group: '媒体', action: 'image', icon: 'image' },
  { key: 'file', label: '本地文件', group: '媒体', action: 'file', icon: 'file' },
  { key: 'cloud', label: '云文档', group: '媒体', action: 'cloud', icon: 'cloud' },
  { key: 'media', label: '音视频', group: '媒体', action: 'media', icon: 'media' },
  { key: 'date', label: '日期', group: '媒体', action: 'date', icon: 'date' },
  { key: 'emoji', label: '表情', group: '媒体', action: 'emoji', icon: 'emoji' },
]

export function groupSlashItems(items) {
  const map = new Map()
  for (const item of items) {
    const g = item.group || '基础'
    if (!map.has(g)) map.set(g, [])
    map.get(g).push(item)
  }
  return SLASH_GROUP_ORDER.filter((name) => map.has(name)).map((name) => ({
    name,
    items: map.get(name),
  }))
}

export const EMOJI_ITEMS = ['😀', '🙂', '😊', '😍', '🤔', '👍', '👎', '❤️', '🎉', '✅', '❌', '⚠️', '📌', '📎', '🔥', '💡', '📝', '🎯', '🏆', '📅', '📚', '🎵', '🎬']
