/** 打字时长落库策略：离开页/切后台也能记时间，且排位未达标仍按练习计时。 */

export const MIN_PERSIST_ELAPSED_MS = 2000
export const RANKED_MIN_ELAPSED_MS = 120_000
export const RANKED_MIN_CORRECT_CHARS = 20

export function shouldPersistTypingSession(result) {
  if (!result) return false
  const elapsedMs = Number(result.elapsedMs) || 0
  const correctChars = Number(result.correctChars) || 0
  return elapsedMs >= MIN_PERSIST_ELAPSED_MS || correctChars > 0
}

/** hidden=true 时暂停；切回仅恢复「因不可见而暂停」的场次，手动暂停保持暂停。 */
export function resolveVisibilityAction({ hidden, status, pauseReason } = {}) {
  if (hidden) return status === 'running' ? 'pause-visibility' : 'none'
  if (status === 'paused' && pauseReason === 'visibility') return 'resume'
  return 'none'
}

export function resolveSaveMode({ requestedMode, elapsedMs, correctChars, textVersion } = {}) {
  if (requestedMode !== 'ranked') return 'practice'
  const elapsed = Number(elapsedMs) || 0
  const correct = Number(correctChars) || 0
  const version = textVersion == null ? '' : String(textVersion).trim()
  if (elapsed < RANKED_MIN_ELAPSED_MS || correct < RANKED_MIN_CORRECT_CHARS || !version) {
    return 'practice'
  }
  return 'ranked'
}

export function buildTypingSessionPayload(result) {
  const mode = resolveSaveMode({
    requestedMode: result?.mode,
    elapsedMs: result?.elapsedMs,
    correctChars: result?.correctChars,
    textVersion: result?.textVersion,
  })
  const clientSessionId = result?.clientSessionId ? String(result.clientSessionId).slice(0, 64) : null
  return {
    clientSessionId,
    mode,
    durationSec: Number(result?.durationSec) || 0,
    cpm: Number(result?.cpm) || 0,
    accuracy: Number(result?.accuracy) || 0,
    correctChars: Number(result?.correctChars) || 0,
    totalKeystrokes: Number(result?.totalKeystrokes) || 0,
    elapsedMs: Number(result?.elapsedMs) || 0,
    lang: result?.lang || 'zh',
    difficulty: Number(result?.difficulty) || 2,
    textVersion: result?.textVersion || null,
    sourceType: result?.sourceType || 'catalog',
  }
}

export function newClientSessionId(now = Date.now()) {
  const rand = Math.random().toString(36).slice(2, 10)
  return `tp_${now}_${rand}`
}

/** 学情时长只认实际 elapsed，不用配置的目标 duration_sec。 */
export function typingActualSeconds(elapsedMs) {
  const ms = Number(elapsedMs) || 0
  if (ms <= 0) return 0
  return Math.floor(ms / 1000)
}
