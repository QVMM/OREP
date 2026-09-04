/**
 * 纯前端打字引擎：支持中文 IME（composition 期间由 UI 暂缓 setCommitted）
 * 代码练习可选 skipLeadingIndent：行首缩进自动填入，练习流只打 token / 行内空格
 */

export function charsOf(text) {
  return [...String(text || '')]
}

export function isIndentWs(ch) {
  return ch === ' ' || ch === '\t'
}

/** 行首（文首或换行后）连续空格/Tab 中的字符 */
export function isLeadingIndentChar(target, index) {
  const chars = Array.isArray(target) ? target : charsOf(target)
  if (index < 0 || index >= chars.length) return false
  if (!isIndentWs(chars[index])) return false
  for (let i = index - 1; i >= 0; i -= 1) {
    if (chars[i] === '\n') return true
    if (!isIndentWs(chars[i])) return false
  }
  return true
}

/**
 * 将用户练习流映射到完整目标：自动插入行首缩进；
 * 用户多敲的空格/Tab 在行首视为 no-op（对齐 typing.io）。
 */
export function expandWithLeadingIndent(practice, targetChars) {
  const user = charsOf(practice)
  const target = Array.isArray(targetChars) ? targetChars : charsOf(targetChars)
  const out = []
  let ui = 0
  let ti = 0

  while (ti < target.length) {
    if (isLeadingIndentChar(target, ti)) {
      out.push(target[ti])
      if (ui < user.length && isIndentWs(user[ui])) ui += 1
      ti += 1
      continue
    }

    // 行首缩进已填完后，多余的空格/Tab 仍视为 no-op，不误伤第一个 token
    if (
      ui < user.length
      && isIndentWs(user[ui])
      && target[ti] !== '\n'
      && !isIndentWs(target[ti])
      && (ti === 0 || target[ti - 1] === '\n' || isLeadingIndentChar(target, ti - 1))
    ) {
      ui += 1
      continue
    }

    if (ui >= user.length) break
    out.push(user[ui])
    ui += 1
    ti += 1
  }
  return out.join('')
}

export function createTypingEngine(targetText, options = {}) {
  const target = charsOf(targetText)
  const skipLeadingIndent = Boolean(options.skipLeadingIndent)
  const mode = options.mode === 'count' ? 'count' : 'timed'
  const durationSec = Math.max(5, Number(options.durationSec) || 60)
  const targetCount = options.targetCount != null
    ? Math.max(1, Number(options.targetCount) || 1)
    : 100

  let committed = skipLeadingIndent ? expandWithLeadingIndent('', target) : ''
  let startedAt = null
  let endedAt = null
  let pausedAt = null
  let pausedMs = 0
  let status = 'idle' // idle | running | paused | finished
  let totalKeystrokes = 0
  let correctKeystrokes = 0
  const errorMap = Object.create(null)

  function elapsedMs(now = Date.now()) {
    if (!startedAt) return 0
    const end = endedAt || (status === 'paused' && pausedAt ? pausedAt : now)
    return Math.max(0, end - startedAt - pausedMs)
  }

  function elapsedMinutes(now = Date.now()) {
    return Math.max(elapsedMs(now) / 60000, 1 / 60000)
  }

  function compare(input) {
    const inputChars = charsOf(input)
    const states = []
    let correct = 0
    let incorrect = 0
    const len = Math.min(inputChars.length, target.length)
    for (let i = 0; i < len; i += 1) {
      const ok = inputChars[i] === target[i]
      states.push(ok ? 'correct' : 'incorrect')
      if (ok) correct += 1
      else incorrect += 1
    }
    return {
      inputChars,
      states,
      correct,
      incorrect,
      caret: Math.min(inputChars.length, target.length),
    }
  }

  function metrics(now = Date.now()) {
    const snap = compare(committed)
    const minutes = elapsedMinutes(now)
    const cpm = Math.round(snap.correct / minutes)
    const wpm = Math.round(cpm / 5)
    const accuracy = totalKeystrokes > 0
      ? Math.round((correctKeystrokes / totalKeystrokes) * 1000) / 10
      : 100
    const progress = mode === 'count'
      ? Math.min(1, snap.correct / targetCount)
      : Math.min(1, elapsedMs(now) / (durationSec * 1000))
    return {
      cpm: startedAt ? cpm : 0,
      wpm: startedAt ? wpm : 0,
      accuracy,
      correctChars: snap.correct,
      incorrectChars: snap.incorrect,
      typedChars: snap.inputChars.length,
      targetChars: target.length,
      totalKeystrokes,
      correctKeystrokes,
      progress,
      remainingSec: mode === 'timed'
        ? Math.max(0, Math.ceil(durationSec - elapsedMs(now) / 1000))
        : null,
      remainingCount: mode === 'count'
        ? Math.max(0, targetCount - snap.correct)
        : null,
    }
  }

  function shouldFinish(now = Date.now()) {
    if (status === 'finished') return true
    const snap = compare(committed)
    if (mode === 'timed' && startedAt && elapsedMs(now) >= durationSec * 1000) return true
    if (mode === 'count' && snap.correct >= targetCount) return true
    // 文本全部打完（含排位固定赛题提前完成）
    if (
      snap.inputChars.length >= target.length
      && target.length > 0
      && snap.correct === target.length
      && snap.incorrect === 0
    ) {
      return true
    }
    return false
  }

  function start(now = Date.now()) {
    if (status === 'running' || status === 'finished') return
    if (status === 'paused' && pausedAt) {
      pausedMs += now - pausedAt
      pausedAt = null
      status = 'running'
      return
    }
    if (!startedAt) startedAt = now
    status = 'running'
  }

  function pause(now = Date.now()) {
    if (status !== 'running') return
    status = 'paused'
    pausedAt = now
  }

  function resume(now = Date.now()) {
    if (status !== 'paused') return
    if (pausedAt) {
      pausedMs += now - pausedAt
      pausedAt = null
    }
    status = 'running'
  }

  function finish(now = Date.now()) {
    if (status === 'finished') return snapshot(now)
    if (status === 'paused' && pausedAt) {
      pausedMs += now - pausedAt
      pausedAt = null
    }
    if (!startedAt) startedAt = now
    status = 'finished'
    endedAt = now
    return snapshot(now)
  }

  /** 提交已确认输入（composition 结束后） */
  function setCommitted(nextValue, now = Date.now()) {
    if (status === 'finished') return snapshot(now)
    if (status === 'paused') return snapshot(now)

    let nextRaw = String(nextValue ?? '')
    if (skipLeadingIndent) {
      nextRaw = expandWithLeadingIndent(nextRaw, target)
    }
    const clipped = charsOf(nextRaw).slice(0, target.length).join('')
    const prevChars = charsOf(committed)
    const nextChars = charsOf(clipped)

    if (status === 'idle' && clipped !== committed) start(now)

    if (nextChars.length > prevChars.length) {
      for (let i = prevChars.length; i < nextChars.length; i += 1) {
        if (skipLeadingIndent && isLeadingIndentChar(target, i)) continue
        totalKeystrokes += 1
        if (i < target.length && nextChars[i] === target[i]) {
          correctKeystrokes += 1
        } else if (i < target.length) {
          const expected = target[i]
          errorMap[expected] = (errorMap[expected] || 0) + 1
        }
      }
    } else if (nextChars.length === prevChars.length && clipped !== committed) {
      for (let i = 0; i < nextChars.length; i += 1) {
        if (nextChars[i] !== prevChars[i]) {
          if (skipLeadingIndent && isLeadingIndentChar(target, i)) continue
          totalKeystrokes += 1
          if (i < target.length && nextChars[i] === target[i]) {
            correctKeystrokes += 1
          } else if (i < target.length) {
            const expected = target[i]
            errorMap[expected] = (errorMap[expected] || 0) + 1
          }
        }
      }
    }

    committed = clipped
    if (shouldFinish(now)) return finish(now)
    return snapshot(now)
  }

  function snapshot(now = Date.now()) {
    const snap = compare(committed)
    const m = metrics(now)
    return {
      status,
      mode,
      durationSec,
      targetCount,
      target: target.join(''),
      targetCharsList: target,
      committed,
      skipLeadingIndent,
      caret: snap.caret,
      charStates: snap.states,
      startedAt,
      endedAt,
      elapsedMs: elapsedMs(now),
      errorMap: { ...errorMap },
      ...m,
    }
  }

  function topErrors(limit = 8) {
    return Object.entries(errorMap)
      .filter(([ch]) => ch && ch !== ' ' && ch !== '\n')
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit)
      .map(([char, count]) => ({ char, count }))
  }

  function buildResult(meta = {}) {
    const now = endedAt || Date.now()
    if (status !== 'finished') finish(now)
    const s = snapshot(now)
    return {
      id: meta.id || `local_${Date.now()}`,
      mode: s.mode,
      durationSec: s.durationSec,
      targetCount: s.targetCount,
      lang: meta.lang || 'zh',
      difficulty: meta.difficulty || 2,
      sourceType: meta.sourceType || 'catalog',
      cpm: s.cpm,
      wpm: s.wpm,
      accuracy: s.accuracy,
      correctChars: s.correctChars,
      incorrectChars: s.incorrectChars,
      typedChars: s.typedChars,
      totalKeystrokes: s.totalKeystrokes,
      elapsedMs: s.elapsedMs,
      errorMap: s.errorMap,
      topErrors: topErrors(10),
      textPreview: target.slice(0, 48).join('') + (target.length > 48 ? '…' : ''),
      createdAt: new Date(now).toISOString(),
    }
  }

  return {
    start,
    pause,
    resume,
    finish,
    setCommitted,
    snapshot,
    metrics,
    topErrors,
    buildResult,
    getStatus: () => status,
    getTarget: () => target.join(''),
  }
}

export function formatDuration(ms) {
  const sec = Math.max(0, Math.round(Number(ms) / 1000))
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}
