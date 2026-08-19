export function isScoreReviseIntent(text) {
  const raw = String(text || '').trim()
  if (!raw) return false
  return /按(?:最新)?评分|对照评分|评分对照|结合讲稿.*优化|按评分改/.test(raw)
}

export function formatScoreReviseDiagnosis(brief) {
  if (!brief) return '没有对照结果。'
  if (!brief.hasReport) {
    return '没有找到最近一次评分，无法对照改稿。先完成一场路演评分。'
  }
  const items = Array.isArray(brief.diagnosis) ? brief.diagnosis : []
  const mapped = items.filter((d) => d.mapped)
  const unmapped = items.filter((d) => !d.mapped)
  const score = brief.overallScore != null ? `总分 ${Number(brief.overallScore).toFixed(1)}` : '已完成评分'
  const lines = [
    `已钉住：讲稿「${brief.scriptTitle || brief.scriptId}」v${brief.contentVersion || 1}；评分 #${brief.scoreReportId || '—'}（${score}${brief.meetingTitle ? ` · ${brief.meetingTitle}` : ''}）。`,
    `评分点了 ${items.length} 条。定位到 ${mapped.length} 步，分工不动。`,
  ]
  if (mapped.length) {
    lines.push('将改：')
    mapped.forEach((d, i) => {
      lines.push(`${i + 1}. ${d.role || '未指定角色'} · ${d.focus || '未指定页'} ← 评分 ${d.id}「${d.title}」`)
    })
  }
  if (unmapped.length) {
    lines.push('对不上步骤、本轮不改：')
    unmapped.forEach((d) => {
      lines.push(`- 评分 ${d.id}「${d.title}」`)
    })
  }
  if (!mapped.length) {
    lines.push('没有能对上讲稿步骤的评分条目，不生成改稿。')
  } else {
    lines.push('下面按条给出建议稿，确认后才写入该步。')
  }
  return lines.join('\n')
}

export function buildScoreItemRewritePrompt(item, brief) {
  return [
    '请只改写当前这一格讲稿正文，不要改角色、时长、页码，不要输出整份讲稿。',
    `讲稿：${brief.scriptTitle || brief.scriptId}`,
    `步骤角色：${item.role || '未指定'}`,
    `对应页：${item.focus || '未指定'}`,
    `步骤全文：${item.stepContent || ''}`,
    `评分条目 ID：${item.id}`,
    `评分指出：${item.title || ''}${item.reason ? `。${item.reason}` : ''}`,
    '不要新增评分里没有写的扣分。原因里必须带上这条评分条目 ID。',
    '请按下面格式回答：',
    '建议稿：<改好后的整段步骤正文>',
    '原因：评分条目 <ID>：<一句具体原因>',
  ].filter(Boolean).join('\n')
}
