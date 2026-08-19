function textOf(node) {
  if (!node) return ''
  if (node.type === 'text') return node.text || ''
  if (node.type === 'hardBreak') return '\n'
  return (node.content || []).map(textOf).join('')
}

function marksWrapMd(text, marks = []) {
  let out = text
  for (const mark of marks) {
    if (mark.type === 'bold') out = `**${out}**`
    else if (mark.type === 'italic') out = `*${out}*`
    else if (mark.type === 'underline') out = `<u>${out}</u>`
    else if (mark.type === 'code') out = `\`${out}\``
    else if (mark.type === 'highlight') out = `==${out}==`
    else if (mark.type === 'link' && mark.attrs?.href) out = `[${out}](${mark.attrs.href})`
  }
  return out
}

function inlineMd(node) {
  if (!node) return ''
  if (node.type === 'text') return marksWrapMd(node.text || '', node.marks)
  if (node.type === 'hardBreak') return '  \n'
  if (node.type === 'dateChip') return node.attrs?.value || ''
  return (node.content || []).map(inlineMd).join('')
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function inlineHtml(node) {
  if (!node) return ''
  if (node.type === 'hardBreak') return '<br>'
  if (node.type === 'dateChip') return `<time>${escapeHtml(node.attrs?.value || '')}</time>`
  if (node.type === 'text') {
    let html = escapeHtml(node.text || '')
    for (const mark of node.marks || []) {
      if (mark.type === 'bold') html = `<strong>${html}</strong>`
      else if (mark.type === 'italic') html = `<em>${html}</em>`
      else if (mark.type === 'underline') html = `<u>${html}</u>`
      else if (mark.type === 'code') html = `<code>${html}</code>`
      else if (mark.type === 'highlight') html = `<mark>${html}</mark>`
      else if (mark.type === 'link' && mark.attrs?.href) {
        html = `<a href="${escapeHtml(mark.attrs.href)}">${html}</a>`
      }
    }
    return html
  }
  return (node.content || []).map(inlineHtml).join('')
}

function tableMd(node) {
  const rows = node.content || []
  if (!rows.length) return ''
  const cells = (row) => (row.content || []).map((cell) => inlineMd(cell).replace(/\|/g, '\\|') || ' ')
  const head = cells(rows[0])
  const lines = [
    `| ${head.join(' | ')} |`,
    `| ${head.map(() => '---').join(' | ')} |`,
  ]
  for (const row of rows.slice(1)) lines.push(`| ${cells(row).join(' | ')} |`)
  return lines.join('\n')
}

function tableHtml(node) {
  const rows = node.content || []
  const body = rows.map((row, i) => {
    const tag = i === 0 ? 'th' : 'td'
    const tds = (row.content || []).map((cell) => `<${tag}>${inlineHtml(cell) || '&nbsp;'}</${tag}>`).join('')
    return `<tr>${tds}</tr>`
  }).join('')
  return `<table>${body}</table>`
}

function mindMd(data) {
  const lines = []
  const walk = (node, depth) => {
    if (!node) return
    lines.push(`${'  '.repeat(depth)}- ${node.text || '未命名'}`)
    ;(node.children || []).forEach((child) => walk(child, depth + 1))
  }
  walk(data?.root, 0)
  return lines.join('\n')
}

function flowMd(data) {
  const nodes = data?.nodes || []
  const edges = data?.edges || []
  const name = Object.fromEntries(nodes.map((n) => [n.id, n.text || n.id]))
  const lines = nodes.map((n) => `- ${n.text || n.id}`)
  for (const e of edges) lines.push(`- ${name[e.from] || e.from} → ${name[e.to] || e.to}`)
  return lines.join('\n')
}

export function smartDocToMarkdown(doc, { title = '' } = {}) {
  const lines = []
  if (title) lines.push(`# ${title}`, '')

  const walk = (node, ctx = {}) => {
    if (!node) return
    const type = node.type
    if (type === 'doc') {
      ;(node.content || []).forEach((child) => walk(child, ctx))
      return
    }
    if (type === 'heading') {
      lines.push(`${'#'.repeat(node.attrs?.level || 1)} ${inlineMd(node)}`, '')
      return
    }
    if (type === 'paragraph') {
      const t = inlineMd(node)
      if (t) lines.push(t, '')
      return
    }
    if (type === 'blockquote') {
      const inner = (node.content || []).map((c) => inlineMd(c)).filter(Boolean)
      inner.forEach((row) => lines.push(`> ${row}`))
      lines.push('')
      return
    }
    if (type === 'codeBlock') {
      lines.push('```', textOf(node), '```', '')
      return
    }
    if (type === 'horizontalRule') {
      lines.push('---', '')
      return
    }
    if (type === 'bulletList' || type === 'orderedList' || type === 'taskList') {
      ;(node.content || []).forEach((item, i) => {
        const prefix = type === 'orderedList'
          ? `${i + 1}. `
          : type === 'taskList'
            ? `- [${item.attrs?.checked ? 'x' : ' '}] `
            : '- '
        lines.push(prefix + inlineMd(item))
      })
      lines.push('')
      return
    }
    if (type === 'highlightBlock') {
      lines.push('> ' + (inlineMd(node) || '高亮块'), '')
      return
    }
    if (type === 'table') {
      lines.push(tableMd(node), '')
      return
    }
    if (type === 'image') {
      lines.push(`![${node.attrs?.alt || ''}](${node.attrs?.src || ''})`, '')
      return
    }
    if (type === 'fileCard') {
      lines.push(`[${node.attrs?.name || '附件'}](${node.attrs?.url || '#'})`, '')
      return
    }
    if (type === 'cloudDoc') {
      lines.push(`[${node.attrs?.title || '云文档'}](${node.attrs?.href || '#'})`, '')
      return
    }
    if (type === 'mediaBlock') {
      lines.push(`[${node.attrs?.name || '音视频'}](${node.attrs?.src || '#'})`, '')
      return
    }
    if (type === 'columns') {
      ;(node.content || []).forEach((col, i) => {
        lines.push(`**栏 ${i + 1}**`, '')
        walk(col, ctx)
      })
      return
    }
    if (type === 'column') {
      ;(node.content || []).forEach((child) => walk(child, ctx))
      return
    }
    if (type === 'protectedRegion') {
      if (node.attrs?.sealed) {
        lines.push('*[此段仅教师可见]*', '')
        return
      }
      lines.push(`**${node.attrs?.label || '内容保护区'}**`, '')
      ;(node.content || []).forEach((child) => walk(child, ctx))
      return
    }
    if (type === 'mindMap') {
      lines.push(mindMd(node.attrs?.data), '')
      return
    }
    if (type === 'flowChart') {
      lines.push(flowMd(node.attrs?.data), '')
      return
    }
    ;(node.content || []).forEach((child) => walk(child, ctx))
  }

  walk(doc)
  return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n'
}

export function smartDocToHtml(doc, { title = '', mode = 'screen' } = {}) {
  const parts = []
  if (title) parts.push(`<h1>${escapeHtml(title)}</h1>`)

  const walk = (node) => {
    if (!node) return
    const type = node.type
    if (type === 'doc') {
      ;(node.content || []).forEach(walk)
      return
    }
    if (type === 'heading') {
      const lv = Math.min(3, Math.max(1, node.attrs?.level || 1))
      parts.push(`<h${lv}>${inlineHtml(node)}</h${lv}>`)
      return
    }
    if (type === 'paragraph') {
      parts.push(`<p>${inlineHtml(node) || '<br>'}</p>`)
      return
    }
    if (type === 'blockquote') {
      parts.push(`<blockquote>${(node.content || []).map((c) => `<p>${inlineHtml(c)}</p>`).join('')}</blockquote>`)
      return
    }
    if (type === 'codeBlock') {
      parts.push(`<pre><code>${escapeHtml(textOf(node))}</code></pre>`)
      return
    }
    if (type === 'horizontalRule') {
      parts.push('<hr>')
      return
    }
    if (type === 'bulletList') {
      parts.push(`<ul>${(node.content || []).map((item) => `<li>${inlineHtml(item)}</li>`).join('')}</ul>`)
      return
    }
    if (type === 'orderedList') {
      parts.push(`<ol>${(node.content || []).map((item) => `<li>${inlineHtml(item)}</li>`).join('')}</ol>`)
      return
    }
    if (type === 'taskList') {
      parts.push(`<ul>${(node.content || []).map((item) => `<li>${item.attrs?.checked ? '☑' : '☐'} ${inlineHtml(item)}</li>`).join('')}</ul>`)
      return
    }
    if (type === 'highlightBlock') {
      parts.push(`<aside class="callout">${(node.content || []).map((c) => `<p>${inlineHtml(c)}</p>`).join('')}</aside>`)
      return
    }
    if (type === 'table') {
      parts.push(tableHtml(node))
      return
    }
    if (type === 'image') {
      parts.push(`<p><img src="${escapeHtml(node.attrs?.src || '')}" alt="${escapeHtml(node.attrs?.alt || '')}"></p>`)
      return
    }
    if (type === 'fileCard' || type === 'cloudDoc' || type === 'mediaBlock') {
      const href = node.attrs?.url || node.attrs?.href || node.attrs?.src || '#'
      const name = node.attrs?.name || node.attrs?.title || '附件'
      parts.push(`<p><a href="${escapeHtml(href)}">${escapeHtml(name)}</a></p>`)
      return
    }
    if (type === 'columns') {
      parts.push('<div class="cols">')
      ;(node.content || []).forEach((col) => {
        parts.push('<div class="col">')
        walk(col)
        parts.push('</div>')
      })
      parts.push('</div>')
      return
    }
    if (type === 'column') {
      ;(node.content || []).forEach(walk)
      return
    }
    if (type === 'protectedRegion') {
      if (node.attrs?.sealed) {
        parts.push('<p><em>此段仅教师可见</em></p>')
        return
      }
      parts.push(`<section class="protect"><strong>${escapeHtml(node.attrs?.label || '内容保护区')}</strong>`)
      ;(node.content || []).forEach(walk)
      parts.push('</section>')
      return
    }
    if (type === 'mindMap') {
      parts.push(`<pre>${escapeHtml(mindMd(node.attrs?.data))}</pre>`)
      return
    }
    if (type === 'flowChart') {
      parts.push(`<pre>${escapeHtml(flowMd(node.attrs?.data))}</pre>`)
      return
    }
    ;(node.content || []).forEach(walk)
  }

  walk(doc)
  const body = parts.join('\n')
  const print = mode === 'print'
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${escapeHtml(title || '智能文档')}</title>
<style>
  @page { size: A4; margin: 18mm 16mm 20mm; }
  html,body{background:#fff;}
  body{
    font:16px/1.75 "PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif;
    color:#1d1d1f;
    max-width:${print ? '100%' : '760px'};
    margin:${print ? '0' : '40px auto'};
    padding:${print ? '0' : '0 20px'};
    word-break:break-word;
  }
  h1{font-size:26px;line-height:1.3;margin:0 0 16px;letter-spacing:-.02em;}
  h2{font-size:20px;margin:22px 0 8px;page-break-after:avoid;}
  h3{font-size:17px;margin:18px 0 8px;page-break-after:avoid;}
  p{margin:0 0 10px;}
  table{border-collapse:collapse;width:100%;margin:10px 0 16px;page-break-inside:avoid;}
  th,td{border:1px solid #d0d2d8;padding:8px 10px;text-align:left;vertical-align:top;font-size:14px;}
  th{background:#f7f7f8;font-weight:600;}
  aside.callout,section.protect{background:#fff8ec;border-left:3px solid #c43a12;padding:8px 12px;margin:12px 0;page-break-inside:avoid;}
  blockquote{margin:12px 0;padding:0 0 0 12px;border-left:3px solid #d0d2d8;color:#4b4b50;}
  .cols{display:flex;gap:16px;page-break-inside:avoid;} .col{flex:1;min-width:0;}
  img{max-width:100%;height:auto;}
  pre{background:#f5f5f7;padding:12px;border-radius:8px;overflow:auto;font-size:13px;page-break-inside:avoid;}
  a{color:#c43a12;text-decoration:none;}
  .doc-meta{color:#8e8e93;font-size:12px;margin:0 0 24px;}
  @media print {
    a{color:#1d1d1f;}
    .cols{display:flex !important;}
  }
</style>
</head>
<body>
${body}
${print ? `<p class="doc-meta">由启发 Office 智能文档导出</p>` : ''}
</body>
</html>
`
}

export function downloadTextFile(filename, text, mime = 'text/plain;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
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
