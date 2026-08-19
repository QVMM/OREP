export const FORBIDDEN_UI = ['令牌', '命题', '印刷', 'L1', 'L2', 'OOXML', '评委路径编译', '双门', '回双门']

export function assertSafeCopy(text) {
  const raw = String(text || '')
  return FORBIDDEN_UI.filter((w) => raw.includes(w))
}

export function holeTitle(hole) {
  const dim = String(hole?.scoreDimension || hole?.dimension || '')
  if (dim.includes('经济')) return '没有成本数字，这场先别写进 PPT'
  if (dim.includes('知识产权') || dim.includes('职业')) return '没有证书，就不要单独做一页'
  return String(hole?.why || '这场先别写上 PPT')
}

export function actLabel(act) {
  return {
    hook: '开场',
    problem: '问题',
    cause: '原因',
    method: '方案',
    demo: '演示',
    evidence: '证据',
    craft: '规范',
    team: '分工',
    close: '收束',
    logistics: '现场交接',
  }[act] || '这一段'
}

export function canMakePpt(path) {
  if (!path) return false
  if (path.canPrint === true) return true
  const holes = Array.isArray(path.holes) ? path.holes : []
  return holes.length === 0 || holes.every((h) => h.acked)
}

export function pageHealth(pageCount) {
  const n = Math.max(0, Number(pageCount) || 0)
  if (n <= 0) return { status: 'empty', label: '还看不出页数' }
  if (n < 38) return { status: 'low', label: `${n} 页，偏少。健康是 38–45 页` }
  if (n > 45) return { status: 'high', label: `${n} 页，偏多。健康是 38–45 页` }
  return { status: 'ok', label: `${n} 页，健康` }
}

export function minutesLabel(pageCount) {
  const n = Math.max(0, Number(pageCount) || 0)
  if (n === 0) return '还没有页'
  return `大约讲 ${Math.max(1, Math.round(n * 1.5))} 分钟，不含演示`
}

export function phaseChips(pages) {
  const groups = []
  for (const page of pages || []) {
    const kicker = page?.kicker || '页'
    const n = Number(page?.page) || groups.length + 1
    const last = groups[groups.length - 1]
    if (last && last.kicker === kicker) last.end = n
    else groups.push({ kicker, start: n, end: n })
  }
  return groups.map((g) => (g.start === g.end ? `${g.kicker} ${g.start}` : `${g.kicker} ${g.start}–${g.end}`))
}

export function padPage(n) {
  return String(Number(n) || 0).padStart(2, '0')
}

export function deckSummary(deck) {
  const n = Number(deck?.pageCount) || (deck?.pages || []).length
  const edit = Number(deck?.editable) || 0
  const part = Number(deck?.partial) || 0
  const pic = Number(deck?.picture) || 0
  const empty = Number(deck?.empty) || 0
  if (!n) return '还没看清这份 PPT'
  const bits = []
  if (edit) bits.push(`${edit} 页能改字`)
  if (part) bits.push(`${part} 页能改一部分`)
  if (pic) bits.push(`${pic} 页是图`)
  if (empty) bits.push(`${empty} 页是空的`)
  return bits.length ? `${n} 页里，${bits.join('，')}` : `${n} 页已经收下`
}

export function prettyDeckTitle(name) {
  const raw = String(name || '').replace(/\.pptx$/i, '')
  if (/^presentation_[0-9a-f-]{8,}/i.test(raw)) return '文档库里的一份演示'
  return raw || '这份 PPT'
}

export function actionLabel(action) {
  return {
    edit: '改几个字',
    replace: '换成另一页',
    drop: '拿掉这页',
    add: '补一页',
    hold: '先不动',
  }[action] || '先看一眼'
}
