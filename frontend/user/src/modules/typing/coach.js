/**
 * AI 打字教练（规则引擎）
 * - 实时不打断
 * - 结算诊断 + 下一局处方
 * 后续可把同一结构交给 LLM 润色
 */

const DRILL_TEMPLATES = [
  '路演时要把重点说清楚：问题、方案、证据、下一步。',
  '开场先讲清为谁解决什么问题，再展开路径与结果。',
  '数据要有对比：提升多少、基线是什么、如何验证。',
  '团队分工明确，演示节奏稳定，问答先结论后依据。',
  '练习准确优先，再逐步提速，保持呼吸与坐姿稳定。',
]

/**
 * @param {object} result 本局成绩
 * @param {object} [ctx]
 * @param {object} [ctx.today]
 * @param {Array} [ctx.history]
 */
export function buildCoachReport(result, ctx = {}) {
  if (!result) {
    return emptyReport()
  }

  const cpm = Number(result.cpm) || 0
  const accuracy = Number(result.accuracy) || 0
  const correctChars = Number(result.correctChars) || 0
  const elapsedMs = Number(result.elapsedMs) || 0
  const isRanked = result.mode === 'ranked' || result.playMode === 'ranked'
  const errors = normalizeErrors(result)
  const today = ctx.today || {}
  const history = Array.isArray(ctx.history) ? ctx.history : []

  const issues = []
  const tips = []
  let level = 'steady' // great | steady | focus
  let headline = ''

  // —— 诊断 ——
  if (accuracy < 88) {
    level = 'focus'
    issues.push({
      id: 'accuracy_low',
      title: '准确率偏低',
      detail: `本局准确率 ${accuracy}%，建议先降速、减少回改，把正确率拉回 92% 以上。`,
    })
  } else if (accuracy < 94) {
    issues.push({
      id: 'accuracy_mid',
      title: '准确率仍有提升空间',
      detail: `准确率 ${accuracy}%，接近稳定区。可把注意力放在标点与数字上。`,
    })
  }

  if (cpm > 0 && cpm < 40 && accuracy >= 90) {
    issues.push({
      id: 'speed_low',
      title: '速度偏保守',
      detail: `净速度 ${cpm} CPM，正确率尚可。下一局可用短冲刺（1～2 分钟）找节奏。`,
    })
  }

  if (cpm >= 80 && accuracy < 92) {
    level = 'focus'
    issues.push({
      id: 'speed_over_acc',
      title: '速度压过了准确',
      detail: '冲得快但错字偏多。建议先「准」再「快」，否则排位净速度会被拖累。',
    })
  }

  if (errors.length >= 3) {
    const sample = errors.slice(0, 5).map((e) => displayChar(e.char)).join('、')
    issues.push({
      id: 'weak_chars',
      title: '存在集中易错字',
      detail: `高频错字：${sample}。建议用「薄弱攻坚」专项练这些字。`,
    })
  }

  if (isRanked && elapsedMs < 5 * 60 * 1000 && correctChars < 200) {
    issues.push({
      id: 'ranked_short',
      title: '排位有效输出不足',
      detail: '排位赛要拼持续输出。下一局尽量稳住前 5 分钟节奏，再加速。',
    })
  }

  if (today.count >= 3 && cpm > 0 && today.bestCpm && cpm < today.bestCpm * 0.75) {
    issues.push({
      id: 'fatigue',
      title: '本局明显低于今日最佳',
      detail: `今日最佳 ${today.bestCpm} CPM，本局 ${cpm}。可短暂休息，或改打 3 分钟轻量局。`,
    })
  }

  // 历史对比
  const recent = history.filter((h) => h && h !== result).slice(0, 8)
  if (recent.length >= 2) {
    const avg = Math.round(recent.reduce((s, h) => s + (Number(h.cpm) || 0), 0) / recent.length)
    if (avg > 0 && cpm >= avg + 12) {
      tips.push(`比你近期均速（约 ${avg} CPM）更快，状态不错，保持呼吸节奏。`)
      if (level === 'steady') level = 'great'
    } else if (avg > 0 && cpm + 15 <= avg) {
      tips.push(`低于近期均速（约 ${avg} CPM），下一局先保证准确，再谈提速。`)
    }
  }

  if (!issues.length) {
    issues.push({
      id: 'stable',
      title: '本局发挥稳定',
      detail: '没有突出短板。可以适当加时长，或挑战排位赛检验耐力。',
    })
    if (level === 'steady' && accuracy >= 96 && cpm >= 60) level = 'great'
  }

  // —— 标题 ——
  if (level === 'great') {
    headline = isRanked
      ? `排位发挥出色：${cpm} CPM · ${accuracy}% 准确率`
      : `状态在线：${cpm} CPM，准确率 ${accuracy}%`
  } else if (level === 'focus') {
    headline = accuracy < 90
      ? '先把准确率拉起来，速度会跟着上来'
      : '本局有明显可改进点，按处方练更有效'
  } else {
    headline = isRanked
      ? `排位已记录：${cpm} CPM · 继续稳准节奏`
      : `本局完成：${cpm} CPM · ${accuracy}% 准确率`
  }

  // —— 处方 ——
  const prescription = buildPrescription({
    level,
    accuracy,
    cpm,
    errors,
    isRanked,
    issues,
  })

  // 补充 tips
  if (accuracy >= 95 && cpm >= 50) {
    tips.push('正确率已经很好，下一局可尝试略提速，但仍以不掉准为准。')
  }
  if (isRanked) {
    tips.push('排位文案固定，多打几次会形成肌肉记忆，重点练开场与数据句。')
  }
  if (!tips.length) {
    tips.push('每天固定练几分钟，比偶尔突击更有效。')
  }

  return {
    source: 'rule_coach_v1',
    level,
    headline,
    summary: issues[0]?.detail || headline,
    issues: issues.slice(0, 3),
    tips: tips.slice(0, 3),
    weakChars: errors.slice(0, 12),
    prescription,
    generatedAt: new Date().toISOString(),
  }
}

function buildPrescription({ level, accuracy, cpm, errors, isRanked, issues }) {
  const weak = errors.slice(0, 10).map((e) => e.char).filter(Boolean)
  const needDrill = weak.length >= 2 || issues.some((i) => i.id === 'weak_chars' || i.id === 'accuracy_low')

  if (needDrill && weak.length) {
    return {
      id: 'drill_weak',
      mode: 'practice',
      label: '薄弱攻坚',
      title: '按薄弱字专项练 3 分钟',
      reason: '集中消灭本局/近期易错字，比重复舒适区更有效。',
      durationSec: 180,
      lang: 'zh',
      difficulty: 2,
      drill: true,
      weakChars: weak,
      customText: buildDrillText(weak, 280),
      cta: '开始薄弱攻坚',
    }
  }

  if (accuracy < 92) {
    return {
      id: 'slow_acc',
      mode: 'practice',
      label: '稳准练习',
      title: '5 分钟稳准局（降难度）',
      reason: '准确率未达标时，优先降速练准，避免错误动力定型。',
      durationSec: 300,
      lang: 'zh',
      difficulty: 1,
      drill: false,
      weakChars: weak,
      customText: '',
      cta: '开始稳准练习',
    }
  }

  if (cpm < 45 && accuracy >= 92) {
    return {
      id: 'speed_burst',
      mode: 'practice',
      label: '速度冲刺',
      title: '2 分钟速度冲刺',
      reason: '正确率尚可，用短冲刺唤醒指速，再回到常规时长。',
      durationSec: 120,
      lang: 'zh',
      difficulty: 2,
      drill: false,
      weakChars: weak,
      customText: '',
      cta: '开始速度冲刺',
    }
  }

  if (!isRanked && (level === 'great' || (cpm >= 55 && accuracy >= 94))) {
    return {
      id: 'go_ranked',
      mode: 'ranked',
      label: '排位检验',
      title: '去打一局排位赛',
      reason: '自主练习状态不错，用 10 分钟固定赛题检验持续输出。',
      durationSec: 600,
      lang: 'zh',
      difficulty: 2,
      drill: false,
      weakChars: weak,
      customText: '',
      cta: '进入排位赛',
    }
  }

  return {
    id: 'balanced',
    mode: 'practice',
    label: '均衡巩固',
    title: '再来 5 分钟均衡练习',
    reason: '保持当前节奏，巩固手感即可。',
    durationSec: 300,
    lang: 'zh',
    difficulty: 2,
    drill: false,
    weakChars: weak,
    customText: '',
    cta: '按建议再练',
  }
}

/** 用薄弱字拼出可读练习短文 */
export function buildDrillText(weakChars, targetLen = 240) {
  const chars = (weakChars || [])
    .map((c) => (typeof c === 'string' ? c : c?.char))
    .filter((c) => c && c !== ' ' && c !== '\n')
    .slice(0, 16)

  if (!chars.length) {
    return DRILL_TEMPLATES.join('')
  }

  const fillers = ['的', '了', '是', '在', '和', '与', '及', '就', '都', '要', '会', '能', '把', '被', '对', '从']
  const parts = []
  let guard = 0
  while (parts.join('').length < targetLen && guard < 80) {
    guard += 1
    // 模板句 + 插入薄弱字串
    const base = DRILL_TEMPLATES[guard % DRILL_TEMPLATES.length]
    const cluster = chars
      .slice(0, 4 + (guard % 3))
      .map((ch, i) => ch + (fillers[(guard + i) % fillers.length] || ''))
      .join('')
    parts.push(base)
    parts.push(cluster)
    parts.push(chars.join('') + chars.slice().reverse().join(''))
  }

  let text = parts.join('').replace(/\s+/g, '')
  // 保证薄弱字出现频率
  const boost = chars.join('').repeat(3)
  text = (text + boost).slice(0, Math.max(targetLen, 120))
  return text
}

function normalizeErrors(result) {
  if (Array.isArray(result.topErrors) && result.topErrors.length) {
    return result.topErrors
      .map((e) => ({ char: e.char, count: Number(e.count) || 1 }))
      .filter((e) => e.char && e.char !== ' ' && e.char !== '\n')
  }
  const map = result.errorMap || {}
  return Object.entries(map)
    .filter(([ch]) => ch && ch !== ' ' && ch !== '\n')
    .map(([char, count]) => ({ char, count: Number(count) || 1 }))
    .sort((a, b) => b.count - a.count)
}

function displayChar(ch) {
  if (ch === ' ') return '空格'
  if (ch === '\n') return '换行'
  return ch
}

function emptyReport() {
  return {
    source: 'rule_coach_v1',
    level: 'steady',
    headline: '暂无本局数据',
    summary: '完成一局练习后，AI 教练会给出诊断与处方。',
    issues: [],
    tips: [],
    weakChars: [],
    prescription: null,
    generatedAt: new Date().toISOString(),
  }
}

/** 将会话处方写入 sessionStorage 配置 */
export function prescriptionToSessionCfg(prescription) {
  if (!prescription) return null
  if (prescription.mode === 'ranked') {
    return { playMode: 'ranked' }
  }
  return {
    playMode: 'practice',
    mode: 'timed',
    durationSec: prescription.durationSec || 300,
    lang: prescription.lang || 'zh',
    difficulty: prescription.difficulty || 2,
    customText: prescription.customText || '',
    sourceType: prescription.drill ? 'drill' : (prescription.customText ? 'paste' : 'catalog'),
    drill: !!prescription.drill,
    weakChars: prescription.weakChars || [],
  }
}
