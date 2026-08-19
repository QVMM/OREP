import DOMPurify from 'dompurify'

const PURIFY = {
  USE_PROFILES: { html: true },
  ADD_ATTR: ['target', 'rel', 'style'],
}

/** 渲染安全 HTML */
export function sanitizeDailyHtml(html) {
  return DOMPurify.sanitize(html || '', PURIFY)
}

/** 从 HTML 提取纯文本 */
export function plainFromHtml(html) {
  if (!html) return ''
  const tmp = document.createElement('div')
  tmp.innerHTML = sanitizeDailyHtml(html)
  return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim()
}

export function isHtmlEmpty(html) {
  return !plainFromHtml(html)
}
