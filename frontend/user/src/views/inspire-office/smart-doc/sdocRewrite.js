const WHY_RE = /\n(?:为什么|原因)[：:]\s*(.+)$/

export function extractSuggestedRewrite(raw, original = '') {
  const text = String(raw || '').trim()
  if (!text) return { after: '', reason: '' }
  const labeled = text.match(/(?:建议稿|改后|改成)[：:]\s*([\s\S]+?)(?:\n(?:为什么|原因)[：:]|$)/)
  if (labeled) {
    const why = text.match(WHY_RE)
    return { after: labeled[1].trim(), reason: why ? why[1].trim() : '' }
  }
  const why = text.match(WHY_RE)
  if (why) {
    return { after: text.slice(0, why.index).trim(), reason: why[1].trim() }
  }
  const origin = String(original || '').trim()
  const tooLong = text.length > Math.max(origin.length * 3, 480)
  const looksLikeEssay = /[？?]/.test(text) || text.split('\n').length > 8
  if (tooLong || looksLikeEssay) return { after: '', reason: '' }
  return { after: text, reason: '' }
}

export function formatScoreBrief(score) {
  if (!score || !score.hasReport) return ''
  const total = Number(score.overallScore)
  const bits = []
  if (Number.isFinite(total)) bits.push(`总分 ${total.toFixed(1)}`)
  const dims = score.dimensions
  if (dims && typeof dims === 'object') {
    const rows = Array.isArray(dims) ? dims : Object.entries(dims).map(([k, v]) => ({ key: k, ...(v || {}) }))
    const weak = rows
      .map((d) => ({
        name: d.name || d.label || d.key || '',
        score: Number(d.score ?? d.value),
      }))
      .filter((d) => d.name && Number.isFinite(d.score))
      .sort((a, b) => a.score - b.score)
      .slice(0, 3)
      .map((d) => `${d.name}${d.score}`)
    if (weak.length) bits.push(`短板：${weak.join('、')}`)
  }
  const priors = Array.isArray(score.improvementPriorities) ? score.improvementPriorities : []
  const tips = priors.slice(0, 4).map((item) => {
    if (typeof item === 'string') return item
    return item?.issue || item?.suggestion || item?.title || item?.description || ''
  }).filter(Boolean)
  if (tips.length) bits.push(`改进点：${tips.join('；')}`)
  return bits.join('。')
}

export function clipScriptAround(fullText, selection, limit = 7000) {
  const all = String(fullText || '')
  const sel = String(selection || '').trim()
  if (all.length <= limit) return all
  if (!sel) return `${all.slice(0, limit)}\n…（后文已截断）`
  const at = all.indexOf(sel)
  if (at < 0) return `${all.slice(0, limit)}\n…（后文已截断）`
  const pad = Math.floor((limit - sel.length) / 2)
  const from = Math.max(0, at - pad)
  const to = Math.min(all.length, at + sel.length + pad)
  return `${from > 0 ? '…' : ''}${all.slice(from, to)}${to < all.length ? '…' : ''}`
}

export function buildAskPrompt(ctx, hint, brief = {}) {
  const want = String(hint || '').trim()
  const sel = String(ctx?.selection || '').trim()
  if (!sel) return want
  return [
    '你是备赛导演，在智能文档里改用户选中的这一段。先对照评分、项目和整篇讲稿想清楚，再一次给出可落稿的建议。',
    '不要出「改稿草案」，不要让用户再点展开。思考过程留在思考里，正文只给建议稿。',
    '',
    `【用户要求】${want}`,
    '',
    '【选中原文】只许改这一段，其它句子一个字都不要动',
    sel,
    ctx.speaker ? `说话人：${ctx.speaker}` : '',
    ctx.nearby?.prev ? `上一段：${ctx.nearby.prev}` : '',
    ctx.nearby?.next ? `下一段：${ctx.nearby.next}` : '',
    brief.scoreText ? `\n【最近一次评分】\n${brief.scoreText}` : '',
    brief.projectText ? `\n【项目】\n${brief.projectText}` : '',
    brief.scriptText ? `\n【整篇讲稿】\n${brief.scriptText}` : '',
    '',
    '输出格式：',
    '建议稿：<改好的这一段，可保留「角色名：」>',
    '为什么：<一句具体原因，能指到评分或上下文，禁止「更生动」>',
  ].filter((line) => line !== '').join('\n')
}
