export const SCRIPT_STEP_STORAGE_KEY = 'orep.xiaoqi.scriptStep'

export function clipStepText(text, max = 80) {
  const s = String(text || '').replace(/\s+/g, ' ').trim()
  if (s.length <= max) return s
  return `${s.slice(0, max).trim()}…`
}

export function readScriptStepContext() {
  try {
    const raw = sessionStorage.getItem(SCRIPT_STEP_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || parsed.type !== 'script_step' || !parsed.scriptId || !parsed.stepId) return null
    return parsed
  } catch {
    return null
  }
}

export function writeScriptStepContext(ctx) {
  sessionStorage.setItem(SCRIPT_STEP_STORAGE_KEY, JSON.stringify(ctx))
}

export function clearScriptStepContext() {
  sessionStorage.removeItem(SCRIPT_STEP_STORAGE_KEY)
}

export function buildScriptRewritePrompt(ctx) {
  const sel = String(ctx.selection || '').trim()
  const prev = ctx.prevStep?.content ? clipStepText(ctx.prevStep.content, 60) : '（无）'
  const next = ctx.nextStep?.content ? clipStepText(ctx.nextStep.content, 60) : '（无）'
  return [
    '请只改写当前这一格讲稿正文，不要改角色、时长、页码，不要输出整份讲稿。',
    `讲稿：${ctx.scriptTitle || ctx.scriptId}`,
    `步骤角色：${ctx.role || '未指定'}`,
    `对应页：${ctx.focus || '未指定'}`,
    `步骤全文：${ctx.stepContent || ''}`,
    sel ? `选中句：${sel}` : '',
    `上一句摘要：${prev}`,
    `下一句摘要：${next}`,
    '请按下面格式回答：',
    '建议稿：<把选中句改好后的整段步骤正文>',
    '原因：<一句具体原因，禁止只说更生动/更通顺>',
  ].filter(Boolean).join('\n')
}

export function extractScriptPatchFromReply(text, ctx) {
  const raw = String(text || '').trim()
  const step = String(ctx?.stepContent || '')
  const sel = String(ctx?.selection || '').trim()
  let after = raw
  let reason = ''
  const reasonMatch = raw.match(/原因[：:]\s*(.+)/)
  if (reasonMatch) reason = reasonMatch[1].trim().split('\n')[0]
  const afterMatch = raw.match(/建议稿[：:]?\s*([\s\S]+?)(?:\n+原因[：:]|$)/)
  if (afterMatch) after = afterMatch[1].trim()
  after = after.replace(/^["「]|["」]$/g, '').trim()
  const remainder = sel ? step.replace(sel, '').trim() : ''
  const looksLikeFullStep = !remainder
    || (remainder.length >= 4 && after.includes(remainder.slice(0, Math.min(8, remainder.length))))
  if (sel && step.includes(sel) && after && after !== step && !looksLikeFullStep && after.length <= sel.length + 48) {
    after = step.replace(sel, after)
  }
  if (!after) after = step
  if (!reason) reason = sel ? `针对选中句「${clipStepText(sel, 24)}」按上下文改写` : '按当前步骤上下文改写'
  return { after, reason }
}

export function firstScriptPatch(ap) {
  const patches = ap?.args?.patches
  if (Array.isArray(patches) && patches[0]) return patches[0]
  return null
}
