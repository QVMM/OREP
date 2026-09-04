const HISTORY_KEY = 'orep_typing_history_v2'
const PREFS_KEY = 'orep_typing_prefs_v2'
const LAST_RESULT_KEY = 'orep_typing_last_result_v2'
const MAX_HISTORY = 50

/** Keybr 风格空格可视化：bullet=中间点 ·（默认） / bar=1ch 下划线槽 / invisible=纯空隙 */
export const SPACE_GLYPH_OPTIONS = [
  { value: 'bullet', label: '空格·', hint: '中间点' },
  { value: 'bar', label: '空格_', hint: '下划线' },
  { value: 'invisible', label: '空格隐', hint: '不显示' },
]

export function normalizeSpaceGlyph(value) {
  if (value === 'bar' || value === 'invisible' || value === 'bullet') return value
  return 'bullet'
}

/**
 * 代码练习固定 invisible：不下划线（像 `_`）、不中间点（像真实 `·`）。
 * 散文/排位仍用用户偏好。
 */
export function resolveSpaceGlyph(value, { code = false } = {}) {
  if (code) return 'invisible'
  return normalizeSpaceGlyph(value)
}

export function spaceGlyphOptionsForMode({ code = false } = {}) {
  if (code) return []
  return SPACE_GLYPH_OPTIONS
}

function safeParse(raw, fallback) {
  try {
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

export function loadPrefs() {
  const defaults = {
    playMode: 'practice', // practice | code | ranked
    practiceKind: 'timed', // timed | count
    durationSec: 300,
    customMinutes: 5,
    useCustomDuration: false,
    targetCount: 100,
    lang: 'zh',
    difficulty: 2,
    codeLang: 'javascript',
    codeSource: 'sample', // sample | paste
    spaceGlyph: 'bullet', // bullet | bar | invisible
  }
  const merged = { ...defaults, ...safeParse(localStorage.getItem(PREFS_KEY), {}) }
  merged.spaceGlyph = normalizeSpaceGlyph(merged.spaceGlyph)
  return merged
}

export function savePrefs(prefs) {
  const current = loadPrefs()
  const next = { ...current, ...prefs }
  localStorage.setItem(PREFS_KEY, JSON.stringify(next))
  return next
}

export function loadHistory() {
  const list = safeParse(localStorage.getItem(HISTORY_KEY), [])
  return Array.isArray(list) ? list : []
}

export function saveHistoryEntry(entry) {
  const list = loadHistory()
  list.unshift(entry)
  const trimmed = list.slice(0, MAX_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed))
  return trimmed
}

export function saveLastResult(result) {
  sessionStorage.setItem(LAST_RESULT_KEY, JSON.stringify(result))
  saveHistoryEntry(result)
  return result
}

export function loadLastResult() {
  return safeParse(sessionStorage.getItem(LAST_RESULT_KEY), null)
    || loadHistory()[0]
    || null
}

function startOfLocalDay(d = new Date()) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

function isSameLocalDay(iso, dayStart = startOfLocalDay()) {
  const t = Date.parse(iso || 0)
  if (Number.isNaN(t)) return false
  return t >= dayStart && t < dayStart + 24 * 3600 * 1000
}

/** 今日练习汇总（本机历史） */
export function summarizeToday(history = loadHistory()) {
  const dayStart = startOfLocalDay()
  const today = history.filter((h) => isSameLocalDay(h.createdAt, dayStart))
  if (!today.length) {
    return {
      count: 0,
      practiceCount: 0,
      rankedCount: 0,
      totalElapsedMs: 0,
      totalCorrectChars: 0,
      avgCpm: 0,
      avgAccuracy: 0,
      bestCpm: 0,
      bestRankedCpm: 0,
      durationLabel: '0 分钟',
    }
  }

  let totalElapsedMs = 0
  let totalCorrectChars = 0
  let practiceCount = 0
  let rankedCount = 0
  let bestCpm = 0
  let bestRankedCpm = 0
  let sumCpm = 0
  let sumAcc = 0

  for (const h of today) {
    const cpm = Number(h.cpm) || 0
    const acc = Number(h.accuracy) || 0
    const elapsed = Number(h.elapsedMs) || 0
    const correct = Number(h.correctChars) || 0
    const mode = h.mode === 'ranked' || h.playMode === 'ranked'
      ? 'ranked'
      : (h.playMode === 'code' || h.sourceType === 'code' ? 'code' : 'practice')
    totalElapsedMs += elapsed
    totalCorrectChars += correct
    sumCpm += cpm
    sumAcc += acc
    if (cpm > bestCpm) bestCpm = cpm
    if (mode === 'ranked') {
      rankedCount += 1
      if (cpm > bestRankedCpm) bestRankedCpm = cpm
    } else {
      practiceCount += 1
    }
  }

  const n = today.length
  return {
    count: n,
    practiceCount,
    rankedCount,
    totalElapsedMs,
    totalCorrectChars,
    avgCpm: Math.round(sumCpm / n),
    avgAccuracy: Math.round((sumAcc / n) * 10) / 10,
    bestCpm,
    bestRankedCpm,
    durationLabel: formatDurationMinutes(totalElapsedMs),
  }
}

export function formatDurationMinutes(ms) {
  const totalSec = Math.max(0, Math.round(Number(ms) / 1000))
  if (totalSec < 60) return `${totalSec} 秒`
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (s === 0) return `${m} 分钟`
  return `${m} 分 ${s} 秒`
}

export function summarizeHistory(history = loadHistory()) {
  if (!history.length) {
    return {
      count: 0,
      recentCount: 0,
      avgCpm: 0,
      avgAccuracy: 0,
      bestCpm: 0,
      weakChars: [],
      today: summarizeToday([]),
    }
  }
  const last7Days = Date.now() - 7 * 24 * 3600 * 1000
  const recent = history.filter((h) => {
    const t = Date.parse(h.createdAt || 0)
    return !Number.isNaN(t) && t >= last7Days
  })
  const pool = recent.length ? recent : history.slice(0, 10)
  const avgCpm = Math.round(pool.reduce((s, h) => s + (Number(h.cpm) || 0), 0) / pool.length)
  const avgAccuracy = Math.round(
    (pool.reduce((s, h) => s + (Number(h.accuracy) || 0), 0) / pool.length) * 10
  ) / 10
  const bestCpm = Math.max(...history.map((h) => Number(h.cpm) || 0))

  const err = Object.create(null)
  for (const h of history.slice(0, 20)) {
    const map = h.errorMap || {}
    for (const [ch, n] of Object.entries(map)) {
      if (!ch || ch === ' ' || ch === '\n') continue
      err[ch] = (err[ch] || 0) + Number(n || 0)
    }
  }
  const weakChars = Object.entries(err)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([char, count]) => ({ char, count }))

  return {
    count: history.length,
    recentCount: recent.length,
    avgCpm,
    avgAccuracy,
    bestCpm,
    weakChars,
    today: summarizeToday(history),
  }
}

/** 解析自主练习最终时长（秒） */
export function resolvePracticeDurationSec(prefs) {
  if (prefs.useCustomDuration || prefs.durationSec === 0) {
    const mins = Math.min(60, Math.max(1, Number(prefs.customMinutes) || 5))
    return mins * 60
  }
  return Math.min(3600, Math.max(30, Number(prefs.durationSec) || 300))
}

function padDateKey(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/**
 * 本机历史 → 近 N 天每日趋势（无服务端数据时的兜底）
 */
export function buildLocalDailyTrend(history = loadHistory(), days = 14) {
  const n = Math.max(7, Math.min(30, Number(days) || 14))
  const map = new Map()
  for (const h of history) {
    const t = Date.parse(h.createdAt || 0)
    if (Number.isNaN(t)) continue
    const key = padDateKey(new Date(t))
    const cur = map.get(key) || {
      date: key,
      sessionCount: 0,
      sumCpm: 0,
      bestCpm: 0,
      sumAcc: 0,
      totalElapsedMs: 0,
      totalCorrectChars: 0,
    }
    const cpm = Number(h.cpm) || 0
    const acc = Number(h.accuracy) || 0
    cur.sessionCount += 1
    cur.sumCpm += cpm
    cur.sumAcc += acc
    cur.bestCpm = Math.max(cur.bestCpm, cpm)
    cur.totalElapsedMs += Number(h.elapsedMs) || 0
    cur.totalCorrectChars += Number(h.correctChars) || 0
    map.set(key, cur)
  }

  const today = new Date()
  const list = []
  for (let i = n - 1; i >= 0; i -= 1) {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i)
    const key = padDateKey(d)
    const cur = map.get(key)
    if (!cur || !cur.sessionCount) {
      list.push({
        date: key,
        sessionCount: 0,
        avgCpm: 0,
        bestCpm: 0,
        avgAccuracy: 0,
        totalElapsedMs: 0,
        totalCorrectChars: 0,
      })
    } else {
      list.push({
        date: key,
        sessionCount: cur.sessionCount,
        avgCpm: Math.round(cur.sumCpm / cur.sessionCount),
        bestCpm: cur.bestCpm,
        avgAccuracy: Math.round((cur.sumAcc / cur.sessionCount) * 10) / 10,
        totalElapsedMs: cur.totalElapsedMs,
        totalCorrectChars: cur.totalCorrectChars,
      })
    }
  }
  return list
}

/** 本机历史 → 最近会话列表 */
export function listLocalRecentSessions(history = loadHistory(), limit = 12) {
  return history.slice(0, limit).map((h, index) => ({
    id: h.id || `local-${index}`,
    mode: h.mode === 'ranked' || h.playMode === 'ranked'
      ? 'ranked'
      : (h.playMode === 'code' || h.sourceType === 'code' ? 'code' : 'practice'),
    cpm: Number(h.cpm) || 0,
    accuracy: Math.round((Number(h.accuracy) || 0) * 10) / 10,
    correctChars: Number(h.correctChars) || 0,
    elapsedMs: Number(h.elapsedMs) || 0,
    createdAt: h.createdAt || null,
    sourceType: h.sourceType || 'catalog',
  }))
}
