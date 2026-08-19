/**
 * 小启技能目录（与 ai-scoring skills/catalog 下各 SKILL.md 对齐）。
 * 前端 slash 菜单用；真正匹配/注入仍在后端。
 *
 * 增删技能时：改后端 catalog + 同步本文件。
 */

/** @typedef {{ name: string, slash: string, description: string, audience: 'student'|'teacher'|'any', priority?: number, group?: string }} SkillPublic */

/** @type {SkillPublic[]} */
export const BUILTIN_SKILLS = [
  {
    name: 'opening',
    slash: '开场',
    description: '30 秒路演开场词（赛场匿名：禁止真名真校）',
    audience: 'student',
    priority: 20,
    group: '备赛',
  },
  {
    name: 'score-review',
    slash: '复盘',
    description: '根据 AI 评分报告做复盘：扣分、优先改什么、怎么练',
    audience: 'student',
    priority: 25,
    group: '备赛',
  },
  {
    name: 'daily-agenda',
    slash: '今日',
    description: '今日安排 / 下一步优先：结合训练营、任务、协同',
    audience: 'student',
    priority: 30,
    group: '备赛',
  },
  {
    name: 'rewrite-script',
    slash: '改稿',
    description: '润色/改写讲稿、开场、路演词（赛场匿名）',
    audience: 'student',
    priority: 18,
    group: '备赛',
  },
  {
    name: 'teacher-desk',
    slash: '工作台',
    description: '教师工作台：待批改、未交、进度、今日带队重点',
    audience: 'teacher',
    priority: 30,
    group: '教学',
  },
]

/**
 * @param {string} audience
 * @param {SkillPublic[]} [catalog]
 */
export function skillsForAudience(audience = 'student', catalog = BUILTIN_SKILLS) {
  const a = String(audience || 'student').toLowerCase()
  return catalog
    .filter((s) => s.audience === 'any' || s.audience === a)
    .slice()
    .sort((x, y) => (y.priority || 0) - (x.priority || 0))
}

/**
 * 检测光标前是否处于 `/技能` 补全态。
 * 规则：行首或空白后的 `/`，后接 0～24 个中文/字母/数字/下划线。
 *
 * @param {string} text
 * @param {number} cursor
 * @returns {{ start: number, end: number, query: string } | null}
 */
export function detectSlashQuery(text, cursor) {
  const value = String(text ?? '')
  const pos = Math.max(0, Math.min(Number(cursor) || 0, value.length))
  const before = value.slice(0, pos)
  // 半角 / 与全角 ／ 都认
  const m = before.match(/(?:^|[\s\n])([/／])([\u4e00-\u9fffA-Za-z0-9_]{0,24})$/)
  if (!m) return null
  const token = m[2] ?? ''
  const slashChar = m[1]
  const slashIndex = before.lastIndexOf(`${slashChar}${token}`)
  if (slashIndex < 0) return null
  return {
    start: slashIndex,
    end: pos,
    query: token,
  }
}

/**
 * @param {SkillPublic[]} skills
 * @param {string} query
 */
export function filterSkillsByQuery(skills, query) {
  const q = String(query || '').trim().toLowerCase()
  if (!q) return skills
  return skills.filter((s) => {
    const slash = String(s.slash || '').toLowerCase()
    const name = String(s.name || '').toLowerCase()
    const desc = String(s.description || '').toLowerCase()
    return slash.includes(q) || name.includes(q) || desc.includes(q)
  })
}

/**
 * 用选中技能替换文本中的 `/query` 片段。
 * @returns {{ text: string, cursor: number }}
 */
export function applySkillSlash(text, range, skill) {
  const value = String(text ?? '')
  const start = range.start
  const end = range.end
  const insert = `/${skill.slash} `
  const next = value.slice(0, start) + insert + value.slice(end)
  return { text: next, cursor: start + insert.length }
}
