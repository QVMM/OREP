/**
 * 小启 AI 回答 Markdown 渲染（教师端，与学生端同构）
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const renderer = new marked.Renderer()

renderer.link = function link({ href, title, tokens }) {
  const text = this.parser.parseInline(tokens)
  const t = title ? ` title="${escapeAttr(title)}"` : ''
  const h = escapeAttr(href || '#')
  return `<a href="${h}"${t} target="_blank" rel="noopener noreferrer">${text}</a>`
}

renderer.code = function code({ text, lang }) {
  const language = (lang || '').trim()
  const cls = language ? ` class="language-${escapeAttr(language)}"` : ''
  const label = language
    ? `<div class="xq-code-lang">${escapeHtml(language)}</div>`
    : ''
  return `<div class="xq-code-block">${label}<pre><code${cls}>${escapeHtml(text)}</code></pre></div>`
}

renderer.codespan = function codespan({ text }) {
  return `<code class="xq-inline-code">${escapeHtml(text)}</code>`
}

const baseTable = renderer.table?.bind(renderer)
if (typeof renderer.table === 'function') {
  renderer.table = function table(token) {
    const inner = baseTable ? baseTable(token) : marked.Renderer.prototype.table.call(this, token)
    return `<div class="xq-table-wrap">${inner}</div>`
  }
}

marked.setOptions({
  gfm: true,
  breaks: true,
  pedantic: false,
  renderer,
})

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, '&#39;')
}

export function stabilizeStreamingMarkdown(text) {
  if (!text) return ''
  let s = String(text)
  const fences = s.match(/```/g)
  if (fences && fences.length % 2 === 1) s += '\n```'
  return s
}

export function formatAssistantMarkdown(text, opts = {}) {
  if (!text) return ''
  const raw = opts.streaming ? stabilizeStreamingMarkdown(text) : String(text)
  let html
  try {
    html = marked.parse(raw, { async: false })
  } catch {
    html = `<p>${escapeHtml(raw).replace(/\n/g, '<br/>')}</p>`
  }
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel', 'class'],
    ALLOWED_URI_REGEXP:
      /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  })
}

export function formatMarkdown(text, opts) {
  return formatAssistantMarkdown(text, opts)
}
