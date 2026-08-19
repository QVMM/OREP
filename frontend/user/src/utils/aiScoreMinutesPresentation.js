const numberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const firstPresent = (...values) => values.find(value => value !== undefined && value !== null && value !== '')

const arrayFrom = (value) => Array.isArray(value) ? value : []

export function buildMinutesPresentation(input = {}) {
  const media = normalizeMedia(input.mediaPlayback)
  const attributionStatus = String(firstPresent(
    input.speakerAttributionStatus,
    input.speaker_attribution_status,
    'LEGACY'
  ) || 'LEGACY').toUpperCase()
  const stablePeople = normalizeStablePeople(firstPresent(input.stablePeople, input.stable_people))
  const mappings = normalizeSpeakerMappings(input.speakerMappings)
  const finalSegments = arrayFrom(firstPresent(input.finalSpeakerSegments, input.final_speaker_segments))
  const transcriptSource = attributionStatus === 'FINAL' && finalSegments.length
    ? finalSegments
    : input.asrSegments
  const transcript = normalizeTranscript(transcriptSource, mappings, stablePeople, attributionStatus)
  const speakers = stablePeople.length ? stablePeople : uniqueSpeakers(transcript)
  const isStableFinal = attributionStatus === 'FINAL' && stablePeople.length > 0
  const chapters = normalizeChapters(input.pitchChapters)
  const prelimDuration = Math.max(
    media.durationSeconds || 0,
    ...transcript.map(item => item.endSeconds || item.startSeconds || 0),
    ...chapters.map(item => item.endSeconds || 0),
    // 无片长时也给估计落点一个可用区间（常见路演 8–15 分钟）
    8 * 60
  )
  const scoreEvents = normalizeScoreEvents(
    input.deductions,
    input.lossLedger,
    input.evidenceAnchors,
    input.observations,
    { transcript, chapters, durationSeconds: prelimDuration }
  )
  const diagnosticItems = arrayFrom(input.diagnosticIssues)
    .map((issue, index) => normalizeDiagnostic(issue, index))
    .filter(item => item.title)
  const durationSeconds = Math.max(
    media.durationSeconds || 0,
    ...transcript.map(item => item.endSeconds || item.startSeconds || 0),
    ...chapters.map(item => item.endSeconds || 0),
    ...scoreEvents.map(item => item.endSeconds || item.timeSeconds || 0),
    0
  )

  return {
    media,
    attributionStatus,
    isStableFinal,
    stablePeople,
    speakers,
    transcript,
    chapters,
    scoreEvents,
    // 全部事件都带时间（含估计），时间轴可全部点击跳转
    timelineEvents: scoreEvents.filter(event => event.timeSeconds != null),
    diagnosticItems,
    durationSeconds
  }
}

function normalizeStablePeople(value) {
  const typeOrder = { CONTESTANT: 0, VISITOR: 1, OFFSCREEN: 2 }
  return arrayFrom(value)
    .map((person, index) => {
      const personId = String(firstPresent(person.personId, person.person_id, '') || '').trim()
      if (!personId) return null
      const personType = String(firstPresent(person.personType, person.person_type, '') || '').toUpperCase()
      const contestantSlot = numberOrNull(firstPresent(person.contestantSlot, person.contestant_slot))
      if (!['CONTESTANT', 'VISITOR', 'OFFSCREEN'].includes(personType)) return null
      if (personType === 'CONTESTANT' && (!Number.isInteger(contestantSlot) || contestantSlot < 1 || contestantSlot > 4)) return null
      const displayName = String(firstPresent(person.displayName, person.display_name, '') || '').trim()
      const roleName = String(firstPresent(person.roleName, person.role_name, '') || '').trim()
      // OFFSCREEN = 本场未归入队员/外部的稳定声纹，展示「未识别说话人」而非「外部人员」
      const fallbackName = personType === 'CONTESTANT' && contestantSlot !== null
        ? `${contestantSlot}号选手`
        : personType === 'VISITOR'
          ? '外部人员'
          : personType === 'OFFSCREEN'
            ? '未识别说话人'
            : '发言人待确认'
      const typeLabel = ({
        CONTESTANT: '参赛选手',
        VISITOR: '外部人员',
        OFFSCREEN: '未识别',
      })[personType] || '待确认'
      return {
        personId,
        personType,
        contestantSlot,
        displayName: displayName || fallbackName,
        roleName,
        speakerName: [displayName || fallbackName, roleName].filter(Boolean).join(' / '),
        typeLabel,
        personState: String(firstPresent(person.personState, person.person_state, '') || ''),
        confidence: numberOrNull(person.confidence),
        firstSeenMs: numberOrNull(firstPresent(person.firstSeenMs, person.first_seen_ms)),
        _index: index
      }
    })
    .filter(Boolean)
    .sort((left, right) => {
      const typeDiff = (typeOrder[left.personType] ?? 9) - (typeOrder[right.personType] ?? 9)
      if (typeDiff) return typeDiff
      const slotDiff = (left.contestantSlot ?? Number.MAX_SAFE_INTEGER) - (right.contestantSlot ?? Number.MAX_SAFE_INTEGER)
      if (slotDiff) return slotDiff
      const timeDiff = (left.firstSeenMs ?? Number.MAX_SAFE_INTEGER) - (right.firstSeenMs ?? Number.MAX_SAFE_INTEGER)
      return timeDiff || left._index - right._index
    })
    .map(({ _index, ...person }) => person)
}

export function resolveActiveReviewState(view, seconds) {
  const current = Math.max(0, numberOrNull(seconds) || 0)
  const transcript = arrayFrom(view?.transcript).find(item =>
    current >= item.startSeconds && current < item.endSeconds
  ) || null
  const chapter = arrayFrom(view?.chapters)
    .filter(item => current >= item.startSeconds && current < item.endSeconds)
    .sort((left, right) => (left.endSeconds - left.startSeconds) - (right.endSeconds - right.startSeconds))[0] || null
  const scoreEvent = arrayFrom(view?.timelineEvents)
    .filter(item => item.timeSeconds <= current)
    .sort((left, right) => right.timeSeconds - left.timeSeconds)[0] || null
  return { transcript, chapter, scoreEvent }
}

export function formatReviewTime(value) {
  const seconds = Math.max(0, Math.floor(numberOrNull(value) || 0))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  const parts = hours > 0 ? [hours, minutes, rest] : [minutes, rest]
  return parts.map((part, index) => index === 0 ? String(part) : String(part).padStart(2, '0')).join(':')
}

function normalizeMedia(value) {
  const source = value && typeof value === 'object' ? value : {}
  const streamUrl = String(firstPresent(source.streamUrl, source.stream_url, '') || '')
  return {
    available: Boolean(streamUrl),
    assetId: firstPresent(source.assetId, source.asset_id, null),
    contentType: String(firstPresent(source.contentType, source.content_type, 'video/mp4')),
    sizeBytes: numberOrNull(firstPresent(source.sizeBytes, source.size_bytes)),
    durationSeconds: numberOrNull(firstPresent(source.durationSeconds, source.duration_seconds)),
    streamUrl
  }
}

function normalizeSpeakerMappings(value) {
  const map = new Map()
  for (const item of arrayFrom(value)) {
    const raw = String(firstPresent(item.rawSpeaker, item.raw_speaker, item.speaker, '') || '').trim()
    if (!raw) continue
    const person = String(firstPresent(item.personName, item.person_name, item.displayName, item.display_name, '') || '').trim()
    const role = String(firstPresent(item.roleName, item.role_name, item.role, '') || '').trim()
    const displayName = [person, role].filter(Boolean).join(' / ')
    if (displayName) map.set(raw, displayName)
  }
  return map
}

function normalizeTranscript(value, mappings, stablePeople = [], attributionStatus = 'LEGACY') {
  const personById = new Map(stablePeople.map(person => [person.personId, person]))
  const isStableFinal = attributionStatus === 'FINAL' && stablePeople.length > 0
  return arrayFrom(value)
    .map((segment, index) => {
      const startMs = numberOrNull(firstPresent(segment.startMs, segment.start_ms))
      const endMs = numberOrNull(firstPresent(segment.endMs, segment.end_ms))
      const startSeconds = startMs !== null
        ? startMs / 1000
        : numberOrNull(firstPresent(segment.start, segment.startSeconds, segment.start_seconds, 0)) || 0
      const endCandidate = endMs !== null
        ? endMs / 1000
        : numberOrNull(firstPresent(segment.end, segment.endSeconds, segment.end_seconds))
      const endSeconds = endCandidate !== null && endCandidate >= startSeconds ? endCandidate : startSeconds
      const rawSpeaker = String(firstPresent(
        segment.rawSpeaker,
        segment.raw_speaker,
        segment.speaker,
        segment.speakerId,
        segment.speaker_id,
        'UNKNOWN'
      ) || 'UNKNOWN')
      const text = String(firstPresent(segment.text, segment.transcript, '') || '').trim()
      const personIdValue = String(firstPresent(segment.personId, segment.person_id, '') || '').trim()
      const personId = personIdValue || null
      const person = personId ? personById.get(personId) : null
      const speakerState = String(firstPresent(segment.speakerState, segment.speaker_state, '') || '').toUpperCase()
      const displaySpeaker = String(firstPresent(segment.displaySpeaker, segment.display_speaker, '') || '').trim()
      const directPerson = String(firstPresent(segment.speakerName, segment.speaker_name, '') || '').trim()
      const directRole = String(firstPresent(segment.roleName, segment.role_name, '') || '').trim()
      const directDisplay = [displaySpeaker || directPerson, directRole]
        .filter(value => value && value !== '发言人待确认' && !/^SPEAKER[_-]?\d+$/i.test(value))
        .join(' / ')
      const stateDisplay = speakerState === 'OVERLAP'
        ? '多人同时发言'
        : speakerState === 'UNKNOWN'
          ? '发言人待确认'
          : null
      const stableDisplay = person?.speakerName || stateDisplay
      return {
        id: String(firstPresent(segment.id, segment.segmentId, segment.segment_id, `asr-${index + 1}`)),
        startSeconds,
        endSeconds,
        timeLabel: formatReviewTime(startSeconds),
        text,
        ...(isStableFinal ? {} : { rawSpeaker }),
        personId,
        personType: person?.personType || String(firstPresent(segment.personType, segment.person_type, '') || ''),
        contestantSlot: person?.contestantSlot ?? numberOrNull(firstPresent(segment.contestantSlot, segment.contestant_slot)),
        speakerState,
        speakerName: stableDisplay || mappings.get(rawSpeaker) || directDisplay || '发言人待确认',
        typeLabel: person?.typeLabel || (speakerState === 'OVERLAP' ? '重叠发言' : speakerState === 'UNKNOWN' ? '待确认' : ''),
        confidence: numberOrNull(segment.confidence)
      }
    })
    .filter(segment => segment.text)
    .sort((left, right) => left.startSeconds - right.startSeconds)
}

function uniqueSpeakers(transcript) {
  const seen = new Map()
  for (const segment of transcript) {
    if (!seen.has(segment.rawSpeaker)) {
      seen.set(segment.rawSpeaker, {
        rawSpeaker: segment.rawSpeaker,
        displayName: segment.speakerName,
        confirmed: segment.speakerName !== '发言人待确认'
      })
    }
  }
  return [...seen.values()]
}

function normalizeChapters(value) {
  return arrayFrom(value)
    .map((chapter, index) => {
      const parsed = parseTimeRange(firstPresent(chapter.time_range, chapter.timeRange, ''))
      const startSeconds = numberOrNull(firstPresent(chapter.startSeconds, chapter.start_seconds, parsed?.start))
      const endSeconds = numberOrNull(firstPresent(chapter.endSeconds, chapter.end_seconds, parsed?.end))
      const title = String(firstPresent(chapter.stage, chapter.title, chapter.name, '') || '').trim()
      if (!title || startSeconds === null || endSeconds === null || endSeconds <= startSeconds) return null
      return {
        id: String(firstPresent(chapter.id, `chapter-${index + 1}`)),
        title,
        startSeconds,
        endSeconds,
        timeLabel: `${formatReviewTime(startSeconds)}–${formatReviewTime(endSeconds)}`,
        summary: String(firstPresent(chapter.actual, chapter.summary, '') || ''),
        gap: String(firstPresent(chapter.gap, '') || ''),
        fix: String(firstPresent(chapter.fix, '') || ''),
        diagnosticScore: numberOrNull(chapter.score)
      }
    })
    .filter(Boolean)
}

function normalizeScoreEvents(deductionsValue, lossLedgerValue, anchorsValue, observationsValue, context = {}) {
  const anchors = new Map(arrayFrom(anchorsValue).map(anchor => [String(anchor.id), anchor]))
  const observationAnchors = new Map(arrayFrom(observationsValue).map(observation => [
    String(firstPresent(observation.observationCode, observation.observation_code, '')),
    arrayFrom(firstPresent(observation.evidenceAnchorIds, observation.evidence_anchor_ids))
  ]).filter(([code]) => code))
  const structuredDeductions = arrayFrom(deductionsValue).filter(deduction => !Boolean(deduction.recovery))
  const structuredByKey = new Map(structuredDeductions.map(deduction => [deductionKey(deduction), deduction]))
  const ledgerDeductions = arrayFrom(lossLedgerValue).map(item => ({
    ...item,
    id: firstPresent(item.lossId, item.loss_id),
    reason: item.reason,
    dimensionName: firstPresent(item.observationName, item.observation_name, item.observationCode, item.observation_code),
    deductedPoints: item.points,
    evidenceAnchorIds: firstPresent(item.evidenceAnchorIds, item.evidence_anchor_ids),
    requiredFix: firstPresent(item.requiredFix, item.required_fix),
    acceptanceCriteria: firstPresent(item.acceptanceCriteria, item.acceptance_criteria),
    lossType: firstPresent(item.lossType, item.loss_type)
  })).map(ledger => {
    const structured = structuredByKey.get(deductionKey(ledger))
    if (!structured) return ledger
    const ledgerAnchorIds = arrayFrom(ledger.evidenceAnchorIds)
    const ledgerHasResolvableAnchor = ledgerAnchorIds.some(id => anchors.has(String(id)))
    const remappedObservationAnchorIds = observationAnchors.get(String(firstPresent(
      ledger.observationCode,
      ledger.observation_code,
      structured.observationCode,
      structured.observation_code,
      ''
    ))) || []
    return {
      ...structured,
      ...ledger,
      id: ledger.id,
      dimensionName: firstPresent(ledger.dimensionName, structured.dimensionName, structured.dimension_name),
      evidenceAnchorIds: ledgerHasResolvableAnchor
        ? ledgerAnchorIds
        : remappedObservationAnchorIds.some(id => anchors.has(String(id)))
          ? remappedObservationAnchorIds
          : arrayFrom(firstPresent(structured.evidenceAnchorIds, structured.evidence_anchor_ids)),
      requiredFix: firstPresent(ledger.requiredFix, structured.requiredFix, structured.required_fix),
      acceptanceCriteria: firstPresent(ledger.acceptanceCriteria, structured.acceptanceCriteria, structured.acceptance_criteria)
    }
  })
  const ledgerKeys = new Set(ledgerDeductions.map(deduction => deductionKey(deduction)))
  const extraStructured = structuredDeductions.filter(deduction => !ledgerKeys.has(deductionKey(deduction)))
  const rawEvents = [...ledgerDeductions, ...extraStructured]
    .map((deduction, index) => {
      const rawAnchorIds = arrayFrom(firstPresent(deduction.evidenceAnchorIds, deduction.evidence_anchor_ids))
      const observationCode = String(firstPresent(deduction.observationCode, deduction.observation_code, ''))
      const fallbackAnchorIds = observationAnchors.get(observationCode) || []
      const anchorIds = rawAnchorIds.some(id => anchors.has(String(id))) ? rawAnchorIds : fallbackAnchorIds
      const linked = anchorIds.map(id => anchors.get(String(id))).filter(Boolean)
      const positioned = linked
        .map(anchor => ({
          anchor,
          start: resolveAnchorStartSeconds(anchor),
          end: resolveAnchorEndSeconds(anchor)
        }))
        .filter(item => item.start !== null)
        .sort((left, right) => left.start - right.start)[0]
      const directTime = resolveDirectEventSeconds(deduction)
      const points = numberOrNull(firstPresent(deduction.deductedPoints, deduction.deducted_points))
      const title = String(firstPresent(deduction.reason, '评分扣分') || '评分扣分')
      const dimensionName = String(firstPresent(deduction.dimensionName, deduction.dimension_name, deduction.dimensionCode, deduction.dimension_code, '') || '')
      let timeSeconds = null
      let endSeconds = null
      let timeSource = 'none'
      if (positioned?.start != null) {
        timeSeconds = positioned.start
        endSeconds = positioned.end ?? positioned.start
        timeSource = 'anchor'
      } else if (directTime != null) {
        timeSeconds = directTime
        endSeconds = directTime
        timeSource = 'field'
      }
      return {
        id: String(firstPresent(deduction.id, `deduction-${index + 1}`)),
        kind: 'formal_deduction',
        title,
        dimensionName,
        points,
        timeSeconds,
        endSeconds,
        timeSource,
        timeEstimated: false,
        timeLabel: timeSeconds != null ? formatReviewTime(timeSeconds) : '未定位到视频时间',
        evidenceText: String(firstPresent(positioned?.anchor?.evidenceText, positioned?.anchor?.evidence_text, '') || ''),
        requiredFix: String(firstPresent(deduction.requiredFix, deduction.required_fix, '') || ''),
        acceptanceCriteria: String(firstPresent(deduction.acceptanceCriteria, deduction.acceptance_criteria, '') || ''),
        lossType: String(firstPresent(deduction.lossType, deduction.loss_type, '') || ''),
        evidenceAnchorIds: anchorIds.map(String),
        _index: index
      }
    })

  return assignEstimatedTimes(rawEvents, context)
}

/** 为仍无时间的评分事件分配「相对合适」的可跳转时间 */
function assignEstimatedTimes(events, context = {}) {
  const transcript = arrayFrom(context.transcript)
  const chapters = arrayFrom(context.chapters)
  const duration = Math.max(30, numberOrNull(context.durationSeconds) || 8 * 60)
  const used = events
    .map(event => numberOrNull(event.timeSeconds))
    .filter(value => value != null)
  const unpositioned = events.filter(event => event.timeSeconds == null)
  const total = Math.max(1, events.length)

  for (const event of unpositioned) {
    let estimated = estimateTimeFromTranscript(event.title, transcript)
    let source = 'transcript'
    if (estimated == null) {
      estimated = estimateTimeFromChapters(event.dimensionName, event.title, chapters)
      source = 'chapter'
    }
    if (estimated == null) {
      // 按事件序号均匀落在片长 10%–90% 区间，避免全堆在 0
      const slot = (event._index + 0.5) / total
      estimated = duration * (0.1 + slot * 0.8)
      source = 'spread'
    }
    estimated = avoidTimeCollision(estimated, used, duration)
    used.push(estimated)
    event.timeSeconds = estimated
    event.endSeconds = Math.min(duration, estimated + 12)
    event.timeSource = source
    event.timeEstimated = true
    event.timeLabel = `约 ${formatReviewTime(estimated)}`
  }

  return events
    .map(({ _index, ...event }) => event)
    .sort((left, right) => (left.timeSeconds ?? 0) - (right.timeSeconds ?? 0) || String(left.id).localeCompare(String(right.id)))
}

function resolveDirectEventSeconds(deduction) {
  const startMs = numberOrNull(firstPresent(deduction.startMs, deduction.start_ms, deduction.timestampMs, deduction.timestamp_ms))
  if (startMs != null) return startMs / 1000
  return numberOrNull(firstPresent(
    deduction.timestamp_seconds,
    deduction.timestampSeconds,
    deduction.time_seconds,
    deduction.timeSeconds,
    deduction.position_seconds,
    deduction.positionSeconds,
    deduction.start_seconds,
    deduction.startSeconds,
    deduction.timestamp,
    deduction.time
  ))
}

function resolveAnchorStartSeconds(anchor) {
  const startMs = numberOrNull(firstPresent(anchor.startMs, anchor.start_ms, anchor.timestampMs, anchor.timestamp_ms))
  if (startMs != null) return startMs / 1000
  return numberOrNull(firstPresent(
    anchor.timestamp_seconds,
    anchor.timestampSeconds,
    anchor.time_seconds,
    anchor.timeSeconds,
    anchor.position_seconds,
    anchor.positionSeconds,
    anchor.start_seconds,
    anchor.startSeconds,
    anchor.timestamp,
    anchor.time
  ))
}

function resolveAnchorEndSeconds(anchor) {
  const endMs = numberOrNull(firstPresent(anchor.endMs, anchor.end_ms))
  if (endMs != null) return endMs / 1000
  return numberOrNull(firstPresent(anchor.end_seconds, anchor.endSeconds, anchor.end))
}

function estimateTimeFromTranscript(reason, transcript) {
  if (!transcript.length || !reason) return null
  const tokens = tokenizeForMatch(reason)
  if (!tokens.length) return null
  let best = null
  let bestScore = 0
  for (const segment of transcript) {
    const text = String(segment.text || '')
    if (!text) continue
    let score = 0
    for (const token of tokens) {
      if (text.includes(token)) score += token.length >= 2 ? 2 : 1
    }
    if (score > bestScore) {
      bestScore = score
      best = segment.startSeconds
    }
  }
  return bestScore >= 2 ? best : null
}

function estimateTimeFromChapters(dimensionName, reason, chapters) {
  if (!chapters.length) return null
  const hay = `${dimensionName || ''} ${reason || ''}`
  const tokens = tokenizeForMatch(hay)
  if (!tokens.length) return null
  let best = null
  let bestScore = 0
  for (const chapter of chapters) {
    const text = `${chapter.title || ''} ${chapter.summary || ''}`
    let score = 0
    for (const token of tokens) {
      if (text.includes(token)) score += 1
    }
    // 维度关键词弱匹配
    if (dimensionName && chapter.title && dimensionName.includes(chapter.title.slice(0, 2))) score += 1
    if (score > bestScore) {
      bestScore = score
      // 落在章节前 1/3，更像「问题出现处」
      best = chapter.startSeconds + Math.max(0, (chapter.endSeconds - chapter.startSeconds) * 0.25)
    }
  }
  return bestScore > 0 ? best : null
}

function tokenizeForMatch(text) {
  const raw = String(text || '')
  const parts = raw
    .replace(/[，。；、！？,.!?;:：()（）【】\[\]"'“”‘’]/g, ' ')
    .split(/\s+/)
    .flatMap((part) => {
      // 中文按 2 字滑动取词，英文按整词
      if (/[\u4e00-\u9fff]/.test(part)) {
        const chars = [...part].filter(ch => /[\u4e00-\u9fff]/.test(ch))
        const grams = []
        for (let i = 0; i < chars.length - 1; i += 1) grams.push(chars[i] + chars[i + 1])
        if (chars.length >= 3) {
          for (let i = 0; i < chars.length - 2; i += 1) grams.push(chars[i] + chars[i + 1] + chars[i + 2])
        }
        return grams
      }
      return part.length >= 2 ? [part.toLowerCase()] : []
    })
    .filter(token => token && !STOP_TOKENS.has(token))
  return [...new Set(parts)].slice(0, 24)
}

const STOP_TOKENS = new Set([
  '不足', '缺少', '需要', '可以', '进行', '问题', '证据', '评分', '扣分', '表达',
  '现场', '演示', '说明', '展示', '结果', '没有', '未能', '不够', '一般', '相关'
])

function avoidTimeCollision(seconds, used, duration) {
  let value = clampNumber(seconds, 0, Math.max(0, duration - 1))
  if (!used.length) return value
  const sorted = [...used].sort((a, b) => a - b)
  let guard = 0
  while (guard < 40 && sorted.some(item => Math.abs(item - value) < 8)) {
    value = clampNumber(value + 11, 0, Math.max(0, duration - 1))
    guard += 1
  }
  return value
}

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function deductionKey(value) {
  const reason = String(firstPresent(value.reason, '') || '').trim().replace(/\s+/g, ' ')
  const points = numberOrNull(firstPresent(value.deductedPoints, value.deducted_points, value.points))
  return `${reason}|${points ?? ''}`
}

function normalizeDiagnostic(value, index) {
  const source = value && typeof value === 'object' ? value : { title: value }
  return {
    id: String(firstPresent(source.id, `diagnostic-${index + 1}`)),
    kind: 'diagnostic',
    title: String(firstPresent(source.title, source.issue, source.reason, '') || '').trim(),
    acceptanceCriteria: String(firstPresent(source.acceptanceCriteria, source.acceptance_criteria, source.fix, '') || ''),
    points: null
  }
}

function parseTimeRange(value) {
  const text = String(value || '')
  const matches = [...text.matchAll(/(\d{1,2}):(\d{2})/g)]
  if (matches.length < 2) return null
  return {
    start: Number(matches[0][1]) * 60 + Number(matches[0][2]),
    end: Number(matches[1][1]) * 60 + Number(matches[1][2])
  }
}

function millisecondsToSeconds(value) {
  const number = numberOrNull(value)
  return number === null ? null : number / 1000
}
