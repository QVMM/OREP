import { zipStore } from './zipStore.js'
import { flowChartSvg, mindMapSvg } from './smartDocReading.js'

function xml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function textOf(node) {
  if (!node) return ''
  if (node.type === 'text') return node.text || ''
  if (node.type === 'dateChip') return node.attrs?.value || ''
  if (node.type === 'hardBreak') return '\n'
  return (node.content || []).map(textOf).join('')
}

function isBlank(node) {
  if (!node) return true
  if (['image', 'fileCard', 'cloudDoc', 'mediaBlock', 'table', 'horizontalRule', 'mindMap', 'flowChart'].includes(node.type)) {
    return false
  }
  const text = textOf(node).replace(/\s+/g, '')
  return !text && !(node.content || []).some((child) => !isBlank(child) && child.type !== 'paragraph')
}

function cssHex(value) {
  const raw = String(value || '').replace('#', '').trim()
  return /^[0-9a-fA-F]{6}$/.test(raw) ? raw.toUpperCase() : ''
}

function wText(text, marks = [], extra = {}) {
  const style = marks.find((m) => m.type === 'textStyle')?.attrs || {}
  const color = extra.color || cssHex(style.color)
  const fontSize = extra.size || (style.fontSize ? Math.round(parseFloat(style.fontSize) * 2) : '')
  const chunks = String(text).split('\n')
  return chunks.map((chunk, i) => {
    const rPr = [
      extra.bold || marks.some((m) => m.type === 'bold') ? '<w:b/>' : '',
      marks.some((m) => m.type === 'italic') ? '<w:i/>' : '',
      marks.some((m) => m.type === 'underline') ? '<w:u w:val="single"/>' : '',
      marks.some((m) => m.type === 'highlight') ? '<w:highlight w:val="yellow"/>' : '',
      marks.some((m) => m.type === 'superscript') ? '<w:vertAlign w:val="superscript"/>' : '',
      color ? `<w:color w:val="${color}"/>` : '',
      extra.underline === false ? '<w:u w:val="none"/>' : '',
      fontSize ? `<w:sz w:val="${fontSize}"/><w:szCs w:val="${fontSize}"/>` : '',
      '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>',
    ].filter(Boolean).join('')
    const run = `<w:r><w:rPr>${rPr}</w:rPr><w:t xml:space="preserve">${xml(chunk)}</w:t></w:r>`
    return i === 0 ? run : `<w:r><w:br/></w:r>${run}`
  }).join('')
}

function inlineRuns(node, extra = {}) {
  if (!node) return wText('', [], extra)
  if (node.type === 'text') return wText(node.text || '', node.marks || [], extra)
  if (node.type === 'dateChip') return wText(node.attrs?.value || '', [], { ...extra, color: 'C43A12' })
  if (node.type === 'hardBreak') return '<w:r><w:br/></w:r>'
  const inner = (node.content || []).map((child) => inlineRuns(child, extra)).join('')
  return inner || wText('')
}

function p(inner, { style, before = 0, after = 160, indent, borderLeft, shade, align } = {}) {
  const pPr = [
    style ? `<w:pStyle w:val="${style}"/>` : '',
    align ? `<w:jc w:val="${align}"/>` : '',
    indent != null ? `<w:ind w:left="${indent}"/>` : '',
    `<w:spacing w:before="${before}" w:after="${after}" w:line="360" w:lineRule="auto"/>`,
    borderLeft ? `<w:pBdr><w:left w:val="single" w:sz="${borderLeft.size}" w:space="8" w:color="${borderLeft.color}"/></w:pBdr>` : '',
    shade ? `<w:shd w:val="clear" w:color="auto" w:fill="${shade}"/>` : '',
  ].filter(Boolean).join('')
  return `<w:p><w:pPr>${pPr}</w:pPr>${inner}</w:p>`
}

function tcBorders(color = 'D0D2D8', sz = 4) {
  return `<w:tcBorders>
    <w:top w:val="single" w:sz="${sz}" w:color="${color}"/>
    <w:left w:val="single" w:sz="${sz}" w:color="${color}"/>
    <w:bottom w:val="single" w:sz="${sz}" w:color="${color}"/>
    <w:right w:val="single" w:sz="${sz}" w:color="${color}"/>
  </w:tcBorders>`
}

function tc(inner, { w, fill, borderColor = 'D0D2D8', borderSz = 4, align, span } = {}) {
  return `<w:tc>
    <w:tcPr>
      <w:tcW w:w="${w}" w:type="dxa"/>
      ${span ? `<w:gridSpan w:val="${span}"/>` : ''}
      ${tcBorders(borderColor, borderSz)}
      ${fill ? `<w:shd w:val="clear" w:color="auto" w:fill="${fill}"/>` : ''}
      <w:vAlign w:val="center"/>
    </w:tcPr>
    ${inner || p(wText(''), { after: 40 })}
  </w:tc>`
}

function tbl(gridCols, rowsXml, { width = 9360 } = {}) {
  const grid = gridCols.map((w) => `<w:gridCol w:w="${w}"/>`).join('')
  return `<w:tbl>
    <w:tblPr>
      <w:tblW w:w="${width}" w:type="dxa"/>
      <w:tblLayout w:type="fixed"/>
    </w:tblPr>
    <w:tblGrid>${grid}</w:tblGrid>
    ${rowsXml}
  </w:tbl>${p('', { after: 80 })}`
}

function tableXml(node) {
  const rows = node.content || []
  if (!rows.length) return ''
  const cols = Math.max(1, ...rows.map((r) => (r.content || []).length))
  const colW = Math.floor(9360 / cols)
  const body = rows.map((row, ri) => {
    const cells = [...(row.content || [])]
    while (cells.length < cols) cells.push({ type: 'tableCell', content: [] })
    const tcs = cells.map((cell) => tc(
      p(inlineRuns(cell, { size: ri === 0 ? 21 : 20, bold: ri === 0 }), { after: 40 }),
      { w: colW, fill: ri === 0 ? 'F7F7F8' : 'FFFFFF' },
    )).join('')
    return `<w:tr>${tcs}</w:tr>`
  }).join('')
  return tbl(Array.from({ length: cols }, () => colW), body)
}

function formatFileSize(size) {
  const n = Number(size) || 0
  if (n >= 1048576) return `${(n / 1048576).toFixed(1)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`
  return n ? `${n} B` : ''
}

function markColor(kind) {
  if (kind === 'sdoc') return 'C43A12'
  if (kind === 'word') return '2B579A'
  if (kind === 'sheet') return '217346'
  if (kind === 'slide') return 'B7472A'
  return '5B6472'
}

function absUrl(href) {
  if (!href || href === '#') return ''
  if (/^https?:\/\//i.test(href)) return href
  if (href.startsWith('/') && typeof location !== 'undefined' && location.origin) {
    return `${location.origin}${href}`
  }
  return ''
}

function cardTable(mark, kind, title, sub, linkId) {
  const titleInner = linkId
    ? `<w:hyperlink r:id="${linkId}">${wText(title, [], { bold: true, size: 21, color: '1D1D1F', underline: false })}</w:hyperlink>`
    : wText(title, [], { bold: true, size: 21 })
  const icon = p(wText(mark, [], { bold: true, size: 20, color: 'FFFFFF' }), { after: 0, align: 'center' })
  const meta = p(titleInner, { after: 20 }) + p(wText(sub, [], { size: 18, color: '8E8E93' }), { after: 0 })
  return tbl([900, 8460], `<w:tr>${
    tc(icon, { w: 900, fill: markColor(kind), borderColor: 'E8EAED', borderSz: 8 })
  }${
    tc(meta, { w: 8460, fill: 'FFFFFF', borderColor: 'E8EAED', borderSz: 8 })
  }</w:tr>`)
}

function nodeBox(text, { fill = 'FFFFFF', border = 'D0D2D8', width = 3600 } = {}) {
  return tbl([width], `<w:tr>${
    tc(p(wText(text || '未命名', [], { bold: true, size: 20 }), { after: 40, align: 'center' }), {
      w: width,
      fill,
      borderColor: border,
      borderSz: 8,
    })
  }</w:tr>`, { width })
}

function mindMapFallback(data) {
  const root = data?.root
  if (!root) return ''
  const kids = root.children || []
  const parts = [nodeBox(root.text || '中心主题', { fill: 'FFF4EE', border: 'C43A12', width: 4200 })]
  kids.forEach((child) => {
    parts.push(p(wText(''), { after: 40 }))
    parts.push(nodeBox(child.text || '分支', { width: 3600 }))
    ;(child.children || []).forEach((grand) => {
      parts.push(nodeBox(`　${grand.text || '节点'}`, { fill: 'F7F7F8', width: 3200 }))
    })
  })
  return parts.join('')
}

function flowChartFallback(data) {
  const nodes = [...(data?.nodes || [])].sort((a, b) => (a.y - b.y) || (a.x - b.x))
  if (!nodes.length) return ''
  return nodes.map((n, i) => {
    const fill = n.kind === 'start' || n.kind === 'end' ? 'F6F7F8' : n.kind === 'diamond' ? 'FFF8EC' : 'FFFFFF'
    const box = nodeBox(n.text || n.id, { fill, width: 3600 })
    if (i === nodes.length - 1) return box
    return box + p(wText('↓', [], { size: 28, color: '8E8E93' }), { after: 40, align: 'center' })
  }).join('')
}

function createAssets() {
  const images = []
  const links = []
  return {
    addImage(bytes, ext = 'png') {
      const i = images.length + 1
      const id = `rIdImg${i}`
      images.push({ id, name: `image${i}.${ext}`, bytes, ext })
      return id
    },
    addLink(url) {
      const i = links.length + 1
      const id = `rIdLnk${i}`
      links.push({ id, url })
      return id
    },
    images,
    links,
  }
}

async function rasterizeSvg(svg, width, height) {
  if (typeof document === 'undefined' || typeof Image === 'undefined') return null
  const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  try {
    const img = new Image()
    img.src = url
    await img.decode()
    const scale = 2
    const w = Math.max(8, Math.round((width || img.width || 280) * scale))
    const h = Math.max(8, Math.round((height || img.height || 160) * scale))
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(img, 0, 0, w, h)
    const png = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!png) return null
    return { bytes: new Uint8Array(await png.arrayBuffer()), width: w / scale, height: h / scale }
  } catch {
    return null
  } finally {
    URL.revokeObjectURL(url)
  }
}

function cleanDrawing(rid, widthPx, heightPx, name) {
  const maxW = 620
  let w = Number(widthPx) || 400
  let h = Number(heightPx) || 240
  if (w > maxW) {
    h = (h * maxW) / w
    w = maxW
  }
  const cx = Math.max(1, Math.round(w * 9525))
  const cy = Math.max(1, Math.round(h * 9525))
  return `<w:p>
    <w:pPr><w:spacing w:before="80" w:after="160"/></w:pPr>
    <w:r>
      <w:drawing>
        <wp:inline distT="0" distB="0" distL="0" distR="0">
          <wp:extent cx="${cx}" cy="${cy}"/>
          <wp:docPr id="${String(rid).replace(/\D/g, '') || '1'}" name="${xml(name)}"/>
          <a:graphic>
            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:pic>
                <pic:nvPicPr>
                  <pic:cNvPr id="0" name="${xml(name)}"/>
                  <pic:cNvPicPr/>
                </pic:nvPicPr>
                <pic:blipFill>
                  <a:blip r:embed="${rid}"/>
                  <a:stretch><a:fillRect/></a:stretch>
                </pic:blipFill>
                <pic:spPr>
                  <a:xfrm>
                    <a:off x="0" y="0"/>
                    <a:ext cx="${cx}" cy="${cy}"/>
                  </a:xfrm>
                  <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                </pic:spPr>
              </pic:pic>
            </a:graphicData>
          </a:graphic>
        </wp:inline>
      </w:drawing>
    </w:r>
  </w:p>`
}

async function probeImageSize(src) {
  if (typeof Image === 'undefined') return { width: 480, height: 280 }
  try {
    const img = new Image()
    img.src = src
    await img.decode()
    return { width: img.naturalWidth || 480, height: img.naturalHeight || 280 }
  } catch {
    return { width: 480, height: 280 }
  }
}

async function embedFetchedImage(src, assets, name = '图片') {
  const url = absUrl(src) || src
  if (!url || typeof fetch === 'undefined') return ''
  try {
    const res = await fetch(url)
    if (!res.ok) return ''
    const bytes = new Uint8Array(await res.arrayBuffer())
    if (!bytes.length) return ''
    const ct = res.headers.get('content-type') || ''
    const ext = ct.includes('jpeg') || ct.includes('jpg') || /\.jpe?g(\?|$)/i.test(url)
      ? 'jpeg'
      : ct.includes('gif') || /\.gif(\?|$)/i.test(url)
        ? 'gif'
        : 'png'
    const size = await probeImageSize(url)
    const id = assets.addImage(bytes, ext)
    return cleanDrawing(id, size.width, size.height, name)
  } catch {
    return ''
  }
}

export function collectOfficeBlocks(doc) {
  const blocks = []
  const walk = (node) => {
    if (!node) return
    if (node.type === 'doc') {
      ;(node.content || []).forEach(walk)
      return
    }
    blocks.push(node.type || 'unknown')
    if (node.type === 'columns' || node.type === 'column' || node.type === 'protectedRegion') {
      ;(node.content || []).forEach(walk)
    }
  }
  walk(doc)
  return blocks
}

async function emitAll(nodes, parts, assets) {
  for (const node of nodes || []) await emit(node, parts, assets)
}

async function emit(node, parts, assets) {
  if (!node) return
  const type = node.type
  if (type === 'doc') {
    await emitAll(node.content, parts, assets)
    return
  }
  if (type === 'heading') {
    const html = textOf(node).trim()
    if (!html) return
    const lv = Math.min(3, Math.max(1, node.attrs?.level || 1))
    parts.push(p(inlineRuns(node, { bold: true, size: lv === 1 ? 32 : lv === 2 ? 26 : 24 }), {
      style: `Heading${lv}`,
      before: lv === 1 ? 280 : 200,
      after: 140,
    }))
    return
  }
  if (type === 'paragraph') {
    if (!textOf(node).trim()) return
    parts.push(p(inlineRuns(node)))
    return
  }
  if (type === 'blockquote') {
    for (const child of node.content || []) {
      if (isBlank(child)) continue
      parts.push(p(inlineRuns(child, { color: '4B4B50' }), {
        indent: 240,
        borderLeft: { size: 12, color: 'D0D2D8' },
      }))
    }
    return
  }
  if (type === 'codeBlock') {
    const code = textOf(node)
    if (!code.trim()) return
    parts.push(p(wText(code, [], { size: 20 }), { shade: 'F5F5F7', after: 200 }))
    return
  }
  if (type === 'horizontalRule') {
    parts.push(`<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="D0D2D8"/></w:pBdr><w:spacing w:after="200"/></w:pPr></w:p>`)
    return
  }
  if (type === 'bulletList' || type === 'orderedList' || type === 'taskList') {
    ;(node.content || []).forEach((item, i) => {
      if (isBlank(item)) return
      const mark = type === 'orderedList' ? `${i + 1}. ` : type === 'taskList' ? (item.attrs?.checked ? '☑ ' : '☐ ') : '• '
      parts.push(p(wText(mark, [], { size: 22 }) + inlineRuns(item), { indent: 420, after: 80 }))
    })
    return
  }
  if (type === 'highlightBlock') {
    const text = textOf(node).trim()
    if (!text) return
    parts.push(p(inlineRuns(node), {
      shade: 'FFF8EC',
      borderLeft: { size: 16, color: 'C43A12' },
      after: 200,
    }))
    return
  }
  if (type === 'table') {
    parts.push(tableXml(node))
    return
  }
  if (type === 'image') {
    const src = node.attrs?.src || ''
    const drawn = await embedFetchedImage(src, assets, node.attrs?.alt || '图片')
    if (drawn) {
      parts.push(drawn)
      return
    }
    const alt = (node.attrs?.alt || '').trim()
    if (alt) parts.push(p(wText(alt, [], { color: '6B6B70', size: 20 })))
    return
  }
  if (type === 'fileCard') {
    const name = node.attrs?.name || '附件'
    const sizeLabel = formatFileSize(node.attrs?.size)
    const href = absUrl(node.attrs?.url)
    const linkId = href ? assets.addLink(href) : ''
    parts.push(cardTable('文', 'file', name, sizeLabel ? `本地文件 · ${sizeLabel}` : '本地文件', linkId))
    return
  }
  if (type === 'cloudDoc') {
    const title = node.attrs?.title || '云文档'
    const ext = node.attrs?.ext || '文档'
    const kind = node.attrs?.kind || 'word'
    const mark = kind === 'sdoc' ? '智' : kind === 'sheet' ? 'X' : kind === 'slide' ? 'P' : 'W'
    const href = absUrl(node.attrs?.href || node.attrs?.url)
    const linkId = href ? assets.addLink(href) : ''
    parts.push(cardTable(mark, kind, title, `启发 Office · ${ext}`, linkId))
    return
  }
  if (type === 'mediaBlock') {
    parts.push(cardTable('媒', 'file', node.attrs?.name || '音视频', '音视频'))
    return
  }
  if (type === 'columns') {
    const cols = (node.content || []).filter((col) => !isBlank(col))
    if (!cols.length) return
    if (cols.length === 1) {
      await emitAll(cols[0].content, parts, assets)
      return
    }
    const colW = Math.floor(9360 / cols.length)
    const cells = []
    for (const col of cols) {
      const inner = []
      await emitAll(col.content, inner, assets)
      cells.push(tc(inner.join('') || p(wText(''), { after: 40 }), { w: colW, fill: 'FFFFFF', borderColor: 'F0F1F3' }))
    }
    parts.push(tbl(cols.map(() => colW), `<w:tr>${cells.join('')}</w:tr>`))
    return
  }
  if (type === 'column') {
    await emitAll(node.content, parts, assets)
    return
  }
  if (type === 'protectedRegion') {
    if (node.attrs?.sealed) {
      parts.push(p(wText('此段仅教师可见', [], { color: '6B6B70', size: 22 }), { shade: 'F4F4F5', after: 200 }))
      return
    }
    if (isBlank(node)) return
    parts.push(p(wText(node.attrs?.label || '仅教师可见', [], { bold: true, color: 'C43A12', size: 20 }), {
      shade: 'FFFAF6',
      after: 60,
    }))
    await emitAll(node.content, parts, assets)
    return
  }
  if (type === 'mindMap') {
    const drawn = mindMapSvg(node.attrs?.data)
    const img = await rasterizeSvg(drawn.svg, drawn.width, drawn.height)
    if (img) {
      const id = assets.addImage(img.bytes, 'png')
      parts.push(cleanDrawing(id, img.width, img.height, '思维导图'))
    } else {
      parts.push(mindMapFallback(node.attrs?.data))
    }
    return
  }
  if (type === 'flowChart') {
    const drawn = flowChartSvg(node.attrs?.data, { markerId: `sdoc-docx-${assets.images.length}` })
    const img = await rasterizeSvg(drawn.svg, drawn.width, drawn.height)
    if (img) {
      const id = assets.addImage(img.bytes, 'png')
      parts.push(cleanDrawing(id, img.width, img.height, '流程图'))
    } else {
      parts.push(flowChartFallback(node.attrs?.data))
    }
    return
  }
  if (node.content) await emitAll(node.content, parts, assets)
}

async function bodyXml(doc, title, assets) {
  const parts = []
  if (title) {
    parts.push(p(wText(title, [], { bold: true, size: 36 }), { style: 'Heading1', after: 200 }))
  }
  await emit(doc, parts, assets)
  return parts.join('') || p(wText('（空文档）'))
}

export async function smartDocToDocxBlob(doc, { title = '未命名文档' } = {}) {
  const assets = createAssets()
  const body = await bodyXml(doc, title, assets)

  const imageOverrides = assets.images.map((img) => {
    const ct = img.ext === 'jpeg' ? 'image/jpeg' : img.ext === 'gif' ? 'image/gif' : 'image/png'
    return `<Override PartName="/word/media/${img.name}" ContentType="${ct}"/>`
  }).join('')

  const rels = [
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
    ...assets.images.map((img) => `<Relationship Id="${img.id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/${img.name}"/>`),
    ...assets.links.map((link) => `<Relationship Id="${link.id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="${xml(link.url)}" TargetMode="External"/>`),
  ].join('')

  const documentXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    ${body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>
    </w:sectPr>
  </w:body>
</w:document>`

  const stylesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>
      <w:sz w:val="22"/><w:szCs w:val="22"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:outlineLvl w:val="0"/><w:spacing w:before="280" w:after="160"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:outlineLvl w:val="1"/><w:spacing w:before="240" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/><w:pPr><w:outlineLvl w:val="2"/><w:spacing w:before="200" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
</w:styles>`

  const files = [
    {
      name: '[Content_Types].xml',
      data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="gif" ContentType="image/gif"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  ${imageOverrides}
</Types>`,
    },
    {
      name: '_rels/.rels',
      data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`,
    },
    {
      name: 'word/_rels/document.xml.rels',
      data: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  ${rels}
</Relationships>`,
    },
    { name: 'word/document.xml', data: documentXml },
    { name: 'word/styles.xml', data: stylesXml },
    ...assets.images.map((img) => ({ name: `word/media/${img.name}`, data: img.bytes })),
  ]

  return zipStore(files)
}
