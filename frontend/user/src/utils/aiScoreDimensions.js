const DIMENSION_NAMES = {
  skill_level: '技能水平',
  professionalism: '职业素养',
  application_value: '应用价值',
  teamwork: '团队协作',
  innovation: '创新能力',
  // 兼容偶发别名
  skill: '技能水平',
  professional: '职业素养',
  application: '应用价值',
  team: '团队协作',
  innovate: '创新能力',
  creativity: '创新能力'
}

const DIMENSION_SHORT_NAMES = {
  skill_level: '技能',
  professionalism: '素养',
  application_value: '应用',
  teamwork: '协作',
  innovation: '创新'
}

/** 后端偶发把 key 写进 name；英文 key / 蛇形字段对学生不可读，统一映射中文。 */
export function dimensionDisplayName(key, name = '') {
  const k = String(key || '').trim()
  const explicitName = String(name || '').trim()
  if (DIMENSION_NAMES[k]) {
    // name 为空、等于 key、或本身就是英文蛇形字段时，用中文映射
    if (!explicitName || explicitName === k || isMachineDimensionToken(explicitName)) {
      return DIMENSION_NAMES[k]
    }
    // 中文名优先；若 name 也是已知 key 则映射
    if (DIMENSION_NAMES[explicitName]) return DIMENSION_NAMES[explicitName]
    return explicitName
  }
  if (DIMENSION_NAMES[explicitName]) return DIMENSION_NAMES[explicitName]
  if (explicitName && !isMachineDimensionToken(explicitName)) return explicitName
  return DIMENSION_NAMES[k] || explicitName || k || '维度'
}

/** 雷达图短标签：中文 2 字优先 */
export function dimensionShortName(key, name = '') {
  const k = String(key || '').trim()
  if (DIMENSION_SHORT_NAMES[k]) return DIMENSION_SHORT_NAMES[k]
  const full = dimensionDisplayName(key, name)
  if (/[\u4e00-\u9fff]/.test(full)) return full.slice(0, 2)
  return full.length > 4 ? full.slice(0, 4) : full
}

function isMachineDimensionToken(value) {
  const text = String(value || '').trim()
  if (!text) return true
  if (DIMENSION_NAMES[text] || DIMENSION_SHORT_NAMES[text]) return true
  // skill_level / professionalism / application_value
  if (/^[a-z][a-z0-9_]*$/i.test(text) && /[_A-Z]/.test(text.slice(1))) return true
  if (/^[a-z]+$/i.test(text) && text.length <= 12 && !/[\u4e00-\u9fff]/.test(text)) {
    // bare english like "skill" / "prof"
    return Boolean(DIMENSION_NAMES[text] || Object.keys(DIMENSION_NAMES).some(k => k.startsWith(text) || text.startsWith(k.slice(0, 4))))
  }
  return false
}

export function buildAuthoritativeDimensions({ authoritative, diagnostic } = {}) {
  const authoritativeSource = isNonEmptyObject(authoritative) ? authoritative : null
  const diagnosticSource = isNonEmptyObject(diagnostic) ? diagnostic : {}
  const source = authoritativeSource || diagnosticSource

  return Object.entries(source).map(([key, dimension]) => {
    const detail = diagnosticSource[key] || {}
    const score = Number(dimension.score || 0)
    const maxScore = Number(dimension.max_score || dimension.maxScore || detail.max_score || detail.maxScore || 100)
    return {
      key,
      name: dimensionDisplayName(key, dimension.name || detail.name),
      score,
      maxScore,
      percent: maxScore ? Math.min(100, (score / maxScore) * 100) : 0,
      items: dimension.items || detail.items || [],
      improvement: dimension.improvement || dimension.suggestions || detail.improvement || detail.suggestions || []
    }
  })
}

function isNonEmptyObject(value) {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length)
}
