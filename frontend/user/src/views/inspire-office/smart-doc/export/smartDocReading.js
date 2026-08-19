import { defaultFlowChart, defaultMindMap, flowBounds, flowEdgePath, flowNodeBox, layoutMindMap } from '../schema/smartDocDiagrams.js'

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function isEmptyBlock(node) {
  if (!node) return true
  if (['image', 'fileCard', 'cloudDoc', 'mediaBlock', 'table', 'horizontalRule', 'mindMap', 'flowChart'].includes(node.type)) {
    return false
  }
  const text = collectText(node).replace(/\s+/g, '')
  return !text && !(node.content || []).some((child) => !isEmptyBlock(child) && child.type !== 'paragraph')
}

function collectText(node) {
  if (!node) return ''
  if (node.type === 'text') return node.text || ''
  if (node.type === 'dateChip') return node.attrs?.value || ''
  return (node.content || []).map(collectText).join('')
}

export function inlineHtml(node) {
  if (!node) return ''
  if (node.type === 'hardBreak') return '<br>'
  if (node.type === 'dateChip') {
    return `<span class="sdoc-date">${escapeHtml(node.attrs?.value || '')}</span>`
  }
  if (node.type === 'text') {
    let html = escapeHtml(node.text || '')
    for (const mark of node.marks || []) {
      if (mark.type === 'bold') html = `<strong>${html}</strong>`
      else if (mark.type === 'italic') html = `<em>${html}</em>`
      else if (mark.type === 'underline') html = `<u>${html}</u>`
      else if (mark.type === 'code') html = `<code>${html}</code>`
      else if (mark.type === 'highlight') {
        const bg = mark.attrs?.color
        html = bg ? `<mark style="background:${escapeHtml(bg)}">${html}</mark>` : `<mark>${html}</mark>`
      }
      else if (mark.type === 'superscript') html = `<sup>${html}</sup>`
      else if (mark.type === 'textStyle') {
        if (mark.attrs?.color) html = `<span style="color:${escapeHtml(mark.attrs.color)}">${html}</span>`
        if (mark.attrs?.fontSize) html = `<span style="font-size:${escapeHtml(mark.attrs.fontSize)}">${html}</span>`
      }
      else if (mark.type === 'link' && mark.attrs?.href) {
        html = `<a href="${escapeHtml(mark.attrs.href)}">${html}</a>`
      }
    }
    return html
  }
  return (node.content || []).map(inlineHtml).join('')
}

function renderBlocks(nodes = []) {
  return nodes.map(renderBlock).filter(Boolean).join('')
}

function renderBlock(node) {
  if (!node) return ''
  const type = node.type
  if (type === 'paragraph') {
    const html = inlineHtml(node)
    if (!html.trim()) return ''
    return `<p>${html}</p>`
  }
  if (type === 'heading') {
    const lv = Math.min(3, Math.max(1, node.attrs?.level || 1))
    const html = inlineHtml(node)
    if (!html.trim()) return ''
    return `<h${lv}>${html}</h${lv}>`
  }
  if (type === 'blockquote') {
    const inner = renderBlocks(node.content)
    return inner ? `<blockquote>${inner}</blockquote>` : ''
  }
  if (type === 'codeBlock') {
    return `<pre><code>${escapeHtml(collectText(node))}</code></pre>`
  }
  if (type === 'horizontalRule') return '<hr>'
  if (type === 'bulletList') {
    return `<ul>${(node.content || []).map((item) => `<li>${itemHasBlocks(item) ? renderBlocks(item.content) : inlineHtml(item)}</li>`).join('')}</ul>`
  }
  if (type === 'orderedList') {
    return `<ol>${(node.content || []).map((item) => `<li>${itemHasBlocks(item) ? renderBlocks(item.content) : inlineHtml(item)}</li>`).join('')}</ol>`
  }
  if (type === 'taskList') {
    return `<ul class="sdoc-tasks">${(node.content || []).map((item) => {
      const mark = item.attrs?.checked ? '☑' : '☐'
      return `<li>${mark} ${inlineHtml(item)}</li>`
    }).join('')}</ul>`
  }
  if (type === 'highlightBlock') {
    const inner = renderBlocks(node.content)
    return inner ? `<aside class="sdoc-callout">${inner}</aside>` : ''
  }
  if (type === 'scriptSheet') {
    return `<section class="sdoc-script-sheet">${renderBlocks(node.content)}</section>`
  }
  if (type === 'scriptStep') {
    const role = escapeHtml(node.attrs?.role || '未指定角色')
    const focus = escapeHtml(node.attrs?.focus || '未指定页')
    return `<article class="sdoc-script-step"><div class="sdoc-script-step__meta">${role} · ${focus}</div>${renderBlocks(node.content)}</article>`
  }
  if (type === 'table') return renderTable(node)
  if (type === 'image' && node.attrs?.src) {
    return `<p><img class="sdoc-image" src="${escapeHtml(node.attrs.src)}" alt="${escapeHtml(node.attrs.alt || '')}"></p>`
  }
  if (type === 'fileCard') return renderFileCard(node)
  if (type === 'cloudDoc') return renderCloudCard(node)
  if (type === 'mediaBlock') {
    return renderCard('媒', 'file', node.attrs?.name || '音视频', '音视频')
  }
  if (type === 'columns') return renderColumns(node)
  if (type === 'column') return renderBlocks(node.content)
  if (type === 'protectedRegion') {
    if (node.attrs?.sealed) {
      return `<section class="sdoc-protect is-sealed"><div class="sdoc-protect__seal">此段仅教师可见</div></section>`
    }
    const inner = renderBlocks(node.content)
    const label = escapeHtml(node.attrs?.label || '仅教师可见')
    return `<section class="sdoc-protect"><div class="sdoc-protect__bar">${label}</div><div class="sdoc-protect__body">${inner}</div></section>`
  }
  if (type === 'mindMap') return renderMindSvg(node.attrs?.data)
  if (type === 'flowChart') return renderFlowSvg(node.attrs?.data)
  if (node.content) return renderBlocks(node.content)
  return ''
}

function itemHasBlocks(item) {
  return (item.content || []).some((child) => child.type && child.type !== 'text' && child.type !== 'dateChip' && child.type !== 'hardBreak')
}

function renderTable(node) {
  const rows = node.content || []
  if (!rows.length) return ''
  const body = rows.map((row, i) => {
    const tag = i === 0 ? 'th' : 'td'
    const cells = (row.content || []).map((cell) => `<${tag}>${inlineHtml(cell) || '&nbsp;'}</${tag}>`).join('')
    return `<tr>${cells}</tr>`
  }).join('')
  return `<table class="sdoc-table">${body}</table>`
}

function formatFileSize(size) {
  const n = Number(size) || 0
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`
  return n ? `${n} B` : ''
}

/** Table layout: html2canvas clips/shifts flex+nowrap cards. */
function renderCard(mark, kind, title, sub) {
  return `<table class="sdoc-card" cellspacing="0" cellpadding="0">
    <tr>
      <td class="sdoc-card__icon"><span class="sdoc-card__mark" data-kind="${escapeHtml(kind)}">${escapeHtml(mark)}</span></td>
      <td class="sdoc-card__meta">
        <div class="sdoc-card__name">${escapeHtml(title)}</div>
        <div class="sdoc-card__sub">${escapeHtml(sub)}</div>
      </td>
    </tr>
  </table>`
}

function renderFileCard(node) {
  const name = node.attrs?.name || '附件'
  const sizeLabel = formatFileSize(node.attrs?.size)
  return renderCard('文', 'file', name, sizeLabel ? `本地文件 · ${sizeLabel}` : '本地文件')
}

function renderCloudCard(node) {
  const title = node.attrs?.title || '云文档'
  const ext = node.attrs?.ext || '文档'
  const kind = node.attrs?.kind || 'word'
  const mark = kind === 'sdoc' ? '智' : kind === 'sheet' ? 'X' : kind === 'slide' ? 'P' : 'W'
  return renderCard(mark, kind, title, `启发 Office · ${ext}`)
}

function renderColumns(node) {
  const cols = (node.content || []).filter((col) => !isEmptyBlock(col))
  if (!cols.length) return ''
  if (cols.length === 1) return renderBlocks(cols[0].content)
  return `<div class="sdoc-columns" data-count="${cols.length}">${
    cols.map((col) => `<div class="sdoc-column">${renderBlocks(col.content)}</div>`).join('')
  }</div>`
}

export function mindMapSvg(data) {
  const laid = layoutMindMap(data || defaultMindMap())
  const edges = laid.edges.map((e) => {
    const mx = (e.x1 + e.x2) / 2
    return `<path d="M ${e.x1} ${e.y1} C ${mx} ${e.y1}, ${mx} ${e.y2}, ${e.x2} ${e.y2}" fill="none" stroke="#c5c6cb" stroke-width="1.6"/>`
  }).join('')
  const nodes = laid.nodes.map((n, i) => {
    const root = i === 0
    return `<g>
      <rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="8" fill="${root ? '#fff4ee' : '#fff'}" stroke="${root ? '#c43a12' : '#d0d2d8'}"/>
      <text x="${n.x + n.w / 2}" y="${n.y + n.h / 2 + 4}" text-anchor="middle" font-size="12" font-weight="600" fill="#1d1d1f" font-family="PingFang SC, Microsoft YaHei, sans-serif">${escapeHtml(n.text)}</text>
    </g>`
  }).join('')
  return {
    width: laid.width,
    height: laid.height,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${laid.width}" height="${laid.height}" viewBox="0 0 ${laid.width} ${laid.height}">${edges}${nodes}</svg>`,
  }
}

export function flowChartSvg(data, { markerId = 'sdoc-arrow' } = {}) {
  const graph = data || defaultFlowChart()
  const boxes = (graph.nodes || []).map(flowNodeBox)
  const map = Object.fromEntries(boxes.map((n) => [n.id, n]))
  const { width, height } = flowBounds(graph)
  const edges = (graph.edges || []).map((edge) => {
    const from = map[edge.from]
    const to = map[edge.to]
    if (!from || !to) return ''
    const p = flowEdgePath(from, to)
    return `<path d="${p.d}" fill="none" stroke="#8e8e93" stroke-width="1.6" marker-end="url(#${markerId})"/>`
  }).join('')
  const nodes = boxes.map((n) => {
    const shape = n.kind === 'diamond'
      ? `<polygon points="${n.x + n.w / 2},${n.y} ${n.x + n.w},${n.y + n.h / 2} ${n.x + n.w / 2},${n.y + n.h} ${n.x},${n.y + n.h / 2}" fill="#fff" stroke="#d0d2d8"/>`
      : `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="${n.kind === 'rect' ? 8 : 20}" fill="${n.kind === 'start' ? '#f6f7f8' : '#fff'}" stroke="#d0d2d8"/>`
    return `<g>${shape}<text x="${n.x + n.w / 2}" y="${n.y + n.h / 2 + 4}" text-anchor="middle" font-size="12" font-weight="600" fill="#1d1d1f" font-family="PingFang SC, Microsoft YaHei, sans-serif">${escapeHtml(n.text)}</text></g>`
  }).join('')
  return {
    width,
    height,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <defs><marker id="${markerId}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8e8e93"/></marker></defs>
      ${edges}${nodes}
    </svg>`,
  }
}

function renderMindSvg(data) {
  return `<div class="sdoc-diagram sdoc-diagram--read">${mindMapSvg(data).svg}</div>`
}

function renderFlowSvg(data) {
  return `<div class="sdoc-diagram sdoc-diagram--read">${flowChartSvg(data, { markerId: 'sdoc-pdf-arrow' }).svg}</div>`
}

export const READING_CSS = `
.sdoc-read{--sdoc-line:#e8eaed;--sdoc-ink:#1d1d1f;--sdoc-muted:#8e8e93;--sdoc-accent:#c43a12;color:var(--sdoc-ink);font:16px/1.75 "PingFang SC","Microsoft YaHei",sans-serif;}
.sdoc-read h1.sdoc-paper__h1{font:700 36px/1.25 "PingFang SC","Microsoft YaHei",sans-serif;margin:0 0 24px;letter-spacing:-.02em;}
.sdoc-read p{margin:0 0 8px;}
.sdoc-read h1{font-size:28px;margin:20px 0 10px;}
.sdoc-read h2{font-size:22px;margin:18px 0 8px;}
.sdoc-read h3{font-size:18px;margin:16px 0 8px;}
.sdoc-read blockquote{margin:12px 0;padding:4px 0 4px 14px;border-left:3px solid #d0d2d8;color:#4b4b50;}
.sdoc-read pre{margin:12px 0;padding:14px 16px;border-radius:10px;background:#f5f5f7;overflow:auto;}
.sdoc-read ul,.sdoc-read ol{padding-left:22px;margin:8px 0;}
.sdoc-read hr{border:0;border-top:1px solid #e8eaed;margin:20px 0;}
.sdoc-read mark{background:#fff3bf;}
.sdoc-callout{margin:12px 0;padding:12px 14px;border-radius:10px;background:#fff8ec;border-left:3px solid #c43a12;}
.sdoc-read img{max-width:100%;height:auto;border-radius:8px;margin:10px 0;}
.sdoc-read table{width:100%;border-collapse:collapse;margin:12px 0;table-layout:fixed;}
.sdoc-read th,.sdoc-read td{border:1px solid #e5e6ea;padding:8px 10px;vertical-align:top;background:#fff;}
.sdoc-read th{background:#f7f7f8;font-weight:600;}
.sdoc-columns{display:block;margin:12px 0;}
.sdoc-column{display:inline-block;vertical-align:top;width:48%;box-sizing:border-box;padding-right:12px;}
.sdoc-columns[data-count="3"] .sdoc-column{width:32%;}
.sdoc-read table.sdoc-card{width:100%;border-collapse:separate;border-spacing:0;table-layout:auto;margin:10px 0;border:1px solid #e8eaed;border-radius:12px;background:#fff;}
.sdoc-read table.sdoc-card td{border:0;background:#fff;vertical-align:middle;padding:12px 14px 12px 0;}
.sdoc-read table.sdoc-card td.sdoc-card__icon{width:56px;padding:12px 10px 12px 14px;text-align:center;}
.sdoc-card__mark{display:inline-block;width:32px;height:32px;line-height:32px;text-align:center;border-radius:8px;color:#fff;font-size:13px;font-weight:800;background:#5b6472;overflow:visible;}
.sdoc-card__mark[data-kind='file']{background:#5b6472;}
.sdoc-card__mark[data-kind='sdoc']{background:#c43a12;}
.sdoc-card__mark[data-kind='word']{background:#2b579a;}
.sdoc-card__mark[data-kind='sheet']{background:#217346;}
.sdoc-card__mark[data-kind='slide']{background:#b7472a;}
.sdoc-card__name{display:block;font-size:14px;font-weight:700;line-height:1.4;white-space:normal;word-break:break-all;}
.sdoc-card__sub{display:block;margin-top:2px;color:#8e8e93;font-size:12px;line-height:1.4;}
.sdoc-date{display:inline-flex;align-items:center;height:24px;padding:0 8px;border-radius:999px;background:#fff4ee;color:#c43a12;font-size:13px;}
.sdoc-protect{margin:12px 0;border:1px dashed #e2c4b0;border-radius:10px;background:#fffaf6;overflow:hidden;}
.sdoc-protect.is-sealed{background:#f4f4f5;border-color:#e5e6ea;}
.sdoc-protect__bar,.sdoc-protect__seal{padding:8px 12px;color:#c43a12;font-size:12px;font-weight:700;}
.sdoc-protect.is-sealed .sdoc-protect__seal{color:#8e8e93;}
.sdoc-protect__body{padding:0 12px 10px;}
.sdoc-diagram--read{margin:12px 0;}
.sdoc-diagram--read svg{display:block;max-width:100%;height:auto;}
`

export function smartDocToReadingHtml(doc, { title = '' } = {}) {
  const body = renderBlocks(doc?.content || [])
  const heading = title
    ? `<h1 class="sdoc-paper__h1">${escapeHtml(title)}</h1>`
    : ''
  return `<div class="sdoc-read">${heading}${body || '<p></p>'}</div>`
}
