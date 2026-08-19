/**
 * 小启 AI 回答 Markdown 渲染（对齐 Grok Build / Grok.com 可读性思路）
 * - GFM：表格 / 删除线 / 任务列表
 * - 快捷键 → <kbd> 键帽
 * - 代码块：语言标签 + 复制按钮（SVG）
 * - 流式半成品围栏自动补齐
 * - highlight.js 高亮（可用时）
 * - DOMPurify 消毒
 */
import { marked } from 'marked'
import DOMPurifyImport from 'dompurify'
import hljs from 'highlight.js/lib/core'

// Vite/browser: default export; Node tests: sometimes { default }
const DOMPurify = DOMPurifyImport?.sanitize
  ? DOMPurifyImport
  : (DOMPurifyImport?.default || DOMPurifyImport)
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import java from 'highlight.js/lib/languages/java'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import sql from 'highlight.js/lib/languages/sql'
import markdown from 'highlight.js/lib/languages/markdown'

let hljsReady = false
function ensureHljs() {
  if (hljsReady) return
  hljs.registerLanguage('javascript', javascript)
  hljs.registerLanguage('js', javascript)
  hljs.registerLanguage('typescript', typescript)
  hljs.registerLanguage('ts', typescript)
  hljs.registerLanguage('python', python)
  hljs.registerLanguage('py', python)
  hljs.registerLanguage('java', java)
  hljs.registerLanguage('json', json)
  hljs.registerLanguage('bash', bash)
  hljs.registerLanguage('shell', bash)
  hljs.registerLanguage('sh', bash)
  hljs.registerLanguage('xml', xml)
  hljs.registerLanguage('html', xml)
  hljs.registerLanguage('css', css)
  hljs.registerLanguage('sql', sql)
  hljs.registerLanguage('markdown', markdown)
  hljs.registerLanguage('md', markdown)
  hljsReady = true
}

const renderer = new marked.Renderer()

renderer.link = function link({ href, title, tokens }) {
  const text = this.parser.parseInline(tokens)
  const t = title ? ` title="${escapeAttr(title)}"` : ''
  const h = escapeAttr(href || '#')
  return `<a href="${h}"${t} target="_blank" rel="noopener noreferrer">${text}</a>`
}

renderer.code = function code({ text, lang }) {
  ensureHljs()
  const language = (lang || '').trim()
  const raw = String(text ?? '')
  let highlighted = escapeHtml(raw)
  let detected = language
  if (language && hljs.getLanguage(language)) {
    try {
      highlighted = hljs.highlight(raw, { language }).value
    } catch {
      highlighted = escapeHtml(raw)
    }
  } else if (!language && raw.length < 4000) {
    try {
      const auto = hljs.highlightAuto(raw, ['javascript', 'python', 'java', 'json', 'bash', 'sql'])
      if (auto?.value && auto.relevance > 5) {
        highlighted = auto.value
        detected = auto.language || ''
      }
    } catch {
      /* keep escaped */
    }
  }
  const cls = detected ? ` class="language-${escapeAttr(detected)} hljs"` : ' class="hljs"'
  const label = detected
    ? `<span class="xq-code-lang">${escapeHtml(detected)}</span>`
    : '<span class="xq-code-lang">code</span>'
  // Grok-like toolbar: lang + copy (SVG)
  const copySvg = `<svg class="xq-copy-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3.5 10.5V3.5A1 1 0 0 1 4.5 2.5h7" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`
  const checkSvg = `<svg class="xq-copy-check" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3.5 8.5l3 3 6-6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`
  return (
    `<div class="xq-code-block">`
    + `<div class="xq-code-bar">`
    + label
    + `<button type="button" class="xq-code-copy" data-xq-copy="1" title="复制代码" aria-label="复制代码">`
    + `${copySvg}${checkSvg}<span class="xq-code-copy-label">复制</span>`
    + `</button>`
    + `</div>`
    + `<pre><code${cls}>${highlighted}</code></pre>`
    + `</div>`
  )
}

renderer.codespan = function codespan({ text }) {
  const raw = String(text ?? '')
  // 快捷键风格的 inline code → 键帽
  if (looksLikeShortcut(raw)) {
    return renderKbdCluster(raw)
  }
  return `<code class="xq-inline-code">${escapeHtml(raw)}</code>`
}

// 表格包装
const baseTable = renderer.table?.bind(renderer)
if (typeof renderer.table === 'function') {
  renderer.table = function table(token) {
    const inner = baseTable
      ? baseTable(token)
      : marked.Renderer.prototype.table.call(this, token)
    return `<div class="xq-table-wrap" role="region" aria-label="表格" tabindex="0">${inner}</div>`
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

/** Ctrl+K / ⌘⇧P / Cmd+Shift+Enter / Esc / F5 等 */
const SHORTCUT_RE = /^(?:(?:Ctrl|Control|Cmd|Command|Alt|Option|Shift|Meta|Win|Super|⌘|⌃|⌥|⇧|⊞)\s*[+＋]\s*)+(?:[A-Za-z0-9]|F\d{1,2}|Enter|Return|Tab|Esc|Escape|Space|Backspace|Delete|Del|Home|End|PageUp|PageDown|↑|↓|←|→|ArrowUp|ArrowDown|ArrowLeft|ArrowRight)$/i
const SHORTCUT_LOOSE_RE = /^(?:Esc|Escape|Enter|Return|Tab|Space|Backspace|Delete|Home|End|PageUp|PageDown|F\d{1,2})$/i

function looksLikeShortcut(text) {
  const t = String(text || '').trim()
  if (!t || t.length > 48) return false
  if (SHORTCUT_LOOSE_RE.test(t)) return true
  if (SHORTCUT_RE.test(t)) return true
  // 中文场景：「Ctrl + K」
  if (/^(?:Ctrl|Cmd|Alt|Shift|⌘|⌃|⌥|⇧)(?:\s*[+＋]\s*[A-Za-z0-9⌘⌃⌥⇧]|)/i.test(t) && /[+＋]/.test(t)) {
    return t.split(/[+＋]/).length >= 2 && t.split(/[+＋]/).length <= 4
  }
  return false
}

const KEY_LABEL = {
  ctrl: 'Ctrl',
  control: 'Ctrl',
  cmd: '⌘',
  command: '⌘',
  meta: '⌘',
  alt: '⌥',
  option: '⌥',
  shift: '⇧',
  win: '⊞',
  super: '⊞',
  enter: 'Enter',
  return: 'Enter',
  esc: 'Esc',
  escape: 'Esc',
  tab: 'Tab',
  space: 'Space',
  backspace: '⌫',
  delete: 'Del',
  del: 'Del',
  '⌘': '⌘',
  '⌃': '⌃',
  '⌥': '⌥',
  '⇧': '⇧',
  '⊞': '⊞',
}

function normalizeKeyPart(part) {
  const p = String(part || '').trim()
  if (!p) return ''
  const lower = p.toLowerCase()
  if (KEY_LABEL[lower]) return KEY_LABEL[lower]
  if (KEY_LABEL[p]) return KEY_LABEL[p]
  if (/^f\d{1,2}$/i.test(p)) return p.toUpperCase()
  if (p.length === 1) return p.toUpperCase()
  return p
}

function renderKbdCluster(raw) {
  const parts = String(raw)
    .split(/\s*[+＋]\s*/)
    .map(normalizeKeyPart)
    .filter(Boolean)
  if (!parts.length) return `<code class="xq-inline-code">${escapeHtml(raw)}</code>`
  const keys = parts
    .map((k) => `<kbd class="xq-kbd">${escapeHtml(k)}</kbd>`)
    .join('<span class="xq-kbd-plus" aria-hidden="true">+</span>')
  return `<span class="xq-kbd-cluster" title="${escapeAttr(raw)}">${keys}</span>`
}

/**
 * 正文中裸露的快捷键（不在 code/fence 内）→ 键帽。
 * 只处理常见组合，避免误伤普通词。
 */
export function enhanceKeyboardShortcuts(html) {
  if (!html) return html
  // 跳过已在标签内的文本：用占位保护 pre/code/a/kbd
  const slots = []
  const protectedHtml = String(html).replace(
    /<(pre|code|kbd|a|button|script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,
    (m) => {
      const i = slots.length
      slots.push(m)
      return `\u0000SLOT${i}\u0000`
    }
  )
  const shortcutToken = /(?<![\w`])((?:(?:Ctrl|Control|Cmd|Command|Alt|Option|Shift|Meta|⌘|⌃|⌥|⇧)(?:\s*[+＋]\s*)?)+(?:[A-Za-z0-9]|F\d{1,2}|Enter|Tab|Esc|Escape|Space|Backspace|Delete)|Esc|F\d{1,2})(?![\w`])/g
  let out = protectedHtml.replace(shortcutToken, (full) => {
    if (!looksLikeShortcut(full) && !/^(?:Ctrl|Cmd|Alt|Shift|⌘)/i.test(full)) {
      // Esc / F5 alone
      if (/^(?:Esc|Escape|F\d{1,2})$/i.test(full)) return renderKbdCluster(full)
      return full
    }
    return renderKbdCluster(full)
  })
  out = out.replace(/\u0000SLOT(\d+)\u0000/g, (_, n) => slots[Number(n)] || '')
  return out
}

/** 流式输出时补齐未闭合的 ``` / 列表后多余空白 */
export function stabilizeStreamingMarkdown(text) {
  if (!text) return ''
  let s = String(text)
  const fences = s.match(/```/g)
  if (fences && fences.length % 2 === 1) s += '\n```'
  return s
}

/**
 * 将正文中的 [1] / [1][2] 转为可点角标（与 citations 索引对齐）
 */
export function injectCitationMarks(html, citations = []) {
  if (!html || !citations?.length) return html
  const max = citations.length
  return String(html).replace(/\[(\d{1,2})\]/g, (full, num) => {
    const n = Number(num)
    if (!Number.isFinite(n) || n < 1 || n > max) return full
    const c = citations[n - 1] || {}
    const title = escapeAttr(c.title || `来源 ${n}`)
    return `<button type="button" class="xq-cite-mark" data-cite-index="${n}" title="${title}" aria-label="查看来源 ${n}"><sup>${n}</sup></button>`
  })
}

/**
 * @param {string} text raw markdown
 * @param {{ streaming?: boolean, citations?: array }} [opts]
 * @returns {string} safe HTML
 */
export function formatAssistantMarkdown(text, opts = {}) {
  if (!text) return ''
  const raw = opts.streaming ? stabilizeStreamingMarkdown(text) : String(text)
  let html
  try {
    html = marked.parse(raw, { async: false })
  } catch {
    html = `<p>${escapeHtml(raw).replace(/\n/g, '<br/>')}</p>`
  }
  html = enhanceKeyboardShortcuts(html)
  if (opts.citations?.length) {
    html = injectCitationMarks(html, opts.citations)
  }
  if (typeof DOMPurify?.sanitize !== 'function') {
    // Node 单测无 window 时跳过消毒（浏览器路径必走 purify）
    return html
  }
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    ADD_ATTR: [
      'target', 'rel', 'class', 'data-cite-index', 'data-xq-copy',
      'type', 'title', 'aria-label', 'aria-hidden', 'role', 'tabindex',
      'viewBox', 'width', 'height', 'fill', 'stroke', 'stroke-width',
      'stroke-linecap', 'stroke-linejoin', 'rx', 'ry', 'x', 'y', 'd', 'cx', 'cy', 'r',
    ],
    ADD_TAGS: ['button', 'sup', 'kbd', 'svg', 'path', 'rect', 'circle', 'span'],
    ALLOWED_URI_REGEXP:
      /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  })
}

/** 兼容旧名 */
export function formatMarkdown(text, opts) {
  return formatAssistantMarkdown(text, opts)
}
