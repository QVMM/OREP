import { getToken } from './auth'

export function isProtectedUploadUrl(url) {
  if (!url || typeof url !== 'string') return false
  try {
    const path = /^https?:\/\//i.test(url)
      ? new URL(url).pathname
      : (url.startsWith('/') ? url.split('?')[0] : `/${url.split('?')[0]}`)
    return path.startsWith('/uploads/training/learning/')
      || path.startsWith('/uploads/task/instructions/')
  } catch {
    return String(url).includes('/uploads/training/learning/')
      || String(url).includes('/uploads/task/instructions/')
  }
}

export function normalizeMediaUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('blob:') || url.startsWith('data:')) return url
  return url.startsWith('/') ? url : `/${url}`
}

export function withAuthMediaUrl(url) {
  const normalized = normalizeMediaUrl(url)
  if (!normalized || !isProtectedUploadUrl(normalized)) return normalized
  const token = getToken()
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

export function withAuthMediaHtml(html) {
  if (!html) return ''
  return String(html).replace(
    /((?:src|href)=)(["'])(\/uploads\/task\/instructions\/[^"']+)\2/gi,
    (_, attr, quote, url) => `${attr}${quote}${withAuthMediaUrl(url)}${quote}`
  )
}

export function stripAuthQueryFromHtml(html) {
  if (!html) return ''
  return String(html).replace(
    /((?:src|href)=)(["'])(\/uploads\/task\/instructions\/[^"']+)\2/gi,
    (_, attr, quote, url) => `${attr}${quote}${String(url).split('#')[0].split('?')[0]}${quote}`
  )
}
