import { getUserToken } from './authStorage'

/**
 * Paths under /uploads/training/learning/** require JWT (Bearer or ?t=).
 * Native media tags (<video>/<img>/<a>) cannot send Authorization headers,
 * so callers must append the query token for those use-cases.
 */
export function isProtectedUploadUrl(url) {
  if (!url || typeof url !== 'string') return false
  try {
    const path = /^https?:\/\//i.test(url)
      ? new URL(url).pathname
      : (url.startsWith('/') ? url.split('?')[0] : `/${url.split('?')[0]}`)
    return path.startsWith('/uploads/training/learning/')
      || path.startsWith('/uploads/chat/')
      || path.startsWith('/uploads/ai-score/')
      || path.startsWith('/uploads/assistant/')
      || path.startsWith('/uploads/resource-center/')
      || path.startsWith('/uploads/office/versions/')
      || path.startsWith('/uploads/course-videos/')
      || path.startsWith('/uploads/course-attachments/')
      || path.startsWith('/uploads/course-covers/')
      || path.startsWith('/uploads/ppt-templates/')
      || path.startsWith('/uploads/task/instructions/')
      || /^\/uploads\/\d{4}\//.test(path)
  } catch {
    return String(url).includes('/uploads/training/learning/')
      || String(url).includes('/uploads/chat/')
  }
}

export function normalizeMediaUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('blob:') || url.startsWith('data:')) return url
  return url.startsWith('/') ? url : `/${url}`
}

/**
 * Return a URL safe for browser-native media requests (video/audio/img/a).
 * For protected upload paths, appends the current user JWT as ?t=.
 */
export function withAuthMediaUrl(url) {
  const normalized = normalizeMediaUrl(url)
  const needsQueryToken = isProtectedUploadUrl(normalized)
    || normalized.startsWith('/api/resource-center/files/')
    || normalized.startsWith('/api/ppt-template/download/')
    || normalized.startsWith('/api/ppt-template/preview/')
  if (!normalized || !needsQueryToken) return normalized

  const token = getUserToken()
  if (!token) return normalized

  try {
    const absolute = /^https?:\/\//i.test(normalized)
    const parsed = absolute
      ? new URL(normalized)
      : new URL(normalized, typeof window !== 'undefined' ? window.location.origin : 'http://local')
    parsed.searchParams.set('t', token)
    if (absolute) return parsed.toString()
    return `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    const bare = normalized.split('#')[0]
    const hash = normalized.includes('#') ? `#${normalized.split('#').slice(1).join('#')}` : ''
    const sep = bare.includes('?') ? '&' : '?'
    return `${bare}${sep}t=${encodeURIComponent(token)}${hash}`
  }
}

/** Rewrite img/src and a/href of protected instruction files so native HTML can load them. */
export function withAuthMediaHtml(html) {
  if (!html) return ''
  return String(html).replace(
    /((?:src|href)=)(["'])(\/uploads\/task\/instructions\/[^"']+)\2/gi,
    (_, attr, quote, url) => `${attr}${quote}${withAuthMediaUrl(url)}${quote}`
  )
}

/** Authorization headers for fetch/XHR against API or protected uploads. */
export function authHeadersForMedia(url) {
  const normalized = normalizeMediaUrl(url)
  const token = getUserToken()
  if (!token) return {}
  if (normalized.startsWith('/api/') || isProtectedUploadUrl(normalized)) {
    return { Authorization: `Bearer ${token}` }
  }
  return {}
}
