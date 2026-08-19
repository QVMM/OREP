/**
 * 结论首页 6 块 view-model。
 * 未实现的硬规格不得点亮，不得把 coverageRate 当成 closureRate。
 */

const CLAIM_SPECS = [
  { claimType: 'wrapper', label: '套壳' },
  { claimType: 'advancement', label: '先进' },
  { claimType: 'value', label: '价值' }
]

const ALLOWED_BANDS = new Set(['not_reviewed', 'green', 'yellow', 'red'])
const FORBIDDEN_COPY = /法庭|开庭|落槌|已经很准|评议席已上|已联网审查|已审查全部/

export function buildConclusionHome(input = {}) {
  const result = objectFrom(input.result)
  const stabilityRaw = objectFrom(firstPresent(input.stability, result.stability))
  const officialScore = numberOrNull(firstPresent(
    input.officialScore,
    input.overallScore,
    result.officialScore,
    result.official_score,
    result.overallScore,
    result.overall_score
  ))
  const contractVersion = text(firstPresent(
    input.contractVersion,
    result.contractVersion,
    result.contract_version
  ))
  const deliberation = objectFrom(firstPresent(
    input.deliberation,
    result.deliberation
  ))
  const teacherConfirmed = Boolean(firstPresent(
    input.teacherConfirmed,
    deliberation.teacherConfirmed,
    deliberation.teacher_confirmed,
    deliberation.finalized,
    result.teacherConfirmed,
    result.teacher_confirmed
  ))

  const runCount = intOrZero(firstPresent(stabilityRaw.runCount, stabilityRaw.run_count))
  const band = normalizeBand(stabilityRaw.band, runCount)
  const headline = sanitizeHeadline(stabilityRaw.headline, band)
  const runs = arrayFrom(stabilityRaw.runs).map(toStabilityRun).filter(Boolean)

  const scoreGap = objectFrom(firstPresent(input.scoreGap, input.score_gap, result.scoreGap, result.score_gap))
  const closureRate = numberOrNull(firstPresent(
    input.closureRate,
    input.closure_rate,
    scoreGap.closureRate,
    scoreGap.closure_rate,
    result.closureRate,
    result.closure_rate
  ))
  const gapOfficial = numberOrNull(firstPresent(
    scoreGap.officialScore,
    scoreGap.official_score,
    officialScore
  ))
  const ceilingGaps = arrayFrom(firstPresent(scoreGap.ceilingGaps, scoreGap.ceiling_gaps, input.ceilingGaps))
    .map(toCeilingGap)
    .filter(Boolean)
    .slice(0, 4)
  const deltaFromLast = numberOrNull(firstPresent(
    scoreGap.deltaFromLast,
    scoreGap.delta_from_last,
    input.deltaFromLast
  ))
  const modelReviewScore = numberOrNull(firstPresent(
    scoreGap.modelReviewScore,
    scoreGap.model_review_score,
    input.modelReviewScore
  ))
  const tapeGrounded = Boolean(firstPresent(
    scoreGap.tapeGrounded,
    scoreGap.tape_grounded,
    input.tapeGrounded
  ))
  const identityReason = text(firstPresent(
    scoreGap.identityReason,
    scoreGap.identity_reason,
    input.identityReason
  ))

  const hung = hungProgress(input, result)

  return {
    officialScore,
    officialScoreDisplay: officialScore == null ? '—' : formatScore(officialScore),
    contractVersion,
    teacherConfirmed,
    teacherHeadline: teacherConfirmed
      ? '教师已确认'
      : (text(deliberation.challengeNote || deliberation.challenge_note) || text(deliberation.headline) || '教师未确认'),
    deliberationStage: text(deliberation.stage),
    finalized: teacherConfirmed,
    stability: {
      band,
      runCount,
      headline,
      identityBand: normalizeBand(
        firstPresent(stabilityRaw.identityBand, stabilityRaw.identity_band),
        intOrZero(firstPresent(stabilityRaw.identityRunCount, stabilityRaw.identity_run_count))
      ),
      identityRunCount: intOrZero(firstPresent(stabilityRaw.identityRunCount, stabilityRaw.identity_run_count)),
      identityHeadline: text(firstPresent(stabilityRaw.identityHeadline, stabilityRaw.identity_headline)),
      mixed: intOrZero(firstPresent(stabilityRaw.identityRunCount, stabilityRaw.identity_run_count)) >= 2
        && normalizeBand(
          firstPresent(stabilityRaw.identityBand, stabilityRaw.identity_band),
          intOrZero(firstPresent(stabilityRaw.identityRunCount, stabilityRaw.identity_run_count))
        ) !== normalizeBand(stabilityRaw.band, runCount),
      thisRunIndex: intOrNull(firstPresent(stabilityRaw.thisRunIndex, stabilityRaw.this_run_index)),
      newerSessionId: firstPresent(stabilityRaw.newerSessionId, stabilityRaw.newer_session_id) || null,
      newerRunIndex: intOrNull(firstPresent(stabilityRaw.newerRunIndex, stabilityRaw.newer_run_index)),
      runs,
      pinUnstable: band === 'red'
    },
    claims: CLAIM_SPECS.map((spec) => toClaim(spec, findClaim(input, result, spec.claimType))),
    gap: {
      officialScore: gapOfficial,
      officialScoreDisplay: gapOfficial == null ? '—' : formatScore(gapOfficial),
      closureRate,
      closureDisplay: closureRate == null
        ? (isTaskBookPublished(input, result) ? '下场计算' : '尚未计算')
        : formatPercent(closureRate),
      closureAvailable: closureRate != null,
      closurePendingNextRun: closureRate == null && isTaskBookPublished(input, result),
      hungCount: hung.hung,
      hungTotal: hung.total,
      hungDisplay: hung.display,
      deltaFromLast,
      modelReviewScore,
      tapeGrounded,
      identityReason: tapeGrounded
        ? (identityReason || '同一录像讲稿与同一套量表，权威分按转写钉死')
        : identityReason,
      ceilingGaps,
      trackCeiling: numberOrNull(firstPresent(scoreGap.trackCeiling, scoreGap.track_ceiling))
    },
    tasks: publishedTaskTitles(input, result),
    tasksAvailable: isTaskBookPublished(input, result),
    seatsLit: {
      record: runCount > 0,
      claims: CLAIM_SPECS.some((spec) => {
        const found = findClaim(input, result, spec.claimType)
        return found && ['seen_in_session', 'retrieved_cited'].includes(String(found.claimStatus || found.claim_status || ''))
      }),
      tasks: isTaskBookPublished(input, result),
      ceiling: ceilingGaps.length > 0
    }
  }
}

function normalizeBand(rawBand, runCount) {
  const band = String(rawBand || '').trim().toLowerCase()
  if (runCount < 2) return 'not_reviewed'
  if (!ALLOWED_BANDS.has(band) || band === 'not_reviewed') return 'not_reviewed'
  return band
}

function sanitizeHeadline(raw, band) {
  const fallback = defaultHeadline(band)
  const textValue = text(raw)
  if (!textValue || FORBIDDEN_COPY.test(textValue)) return fallback
  if (band === 'red' && !textValue.includes('本场不稳定')) return '本场不稳定，请教师复核'
  if (band === 'not_reviewed') return '尚未复评'
  return textValue
}

function defaultHeadline(band) {
  if (band === 'red') return '本场不稳定，请教师复核'
  if (band === 'yellow') return '复评分差在黄档'
  if (band === 'green') return '复评分差在绿档'
  return '尚未复评'
}

function toStabilityRun(raw) {
  const item = objectFrom(raw)
  const runIndex = intOrNull(firstPresent(item.runIndex, item.run_index))
  if (runIndex == null) return null
  return {
    runIndex,
    officialScore: numberOrNull(firstPresent(item.officialScore, item.official_score)),
    scoreDeltaAbs: numberOrNull(firstPresent(item.scoreDeltaAbs, item.score_delta_abs)),
    transcriptCoverage: numberOrNull(firstPresent(item.transcriptCoverage, item.transcript_coverage)),
    seekableAnchorRate: numberOrNull(firstPresent(item.seekableAnchorRate, item.seekable_anchor_rate))
  }
}

function hungProgress(input, result) {
  if (!isTaskBookPublished(input, result)) {
    return { hung: 0, total: 0, display: '' }
  }
  const book = objectFrom(firstPresent(input.taskBook, input.task_book, result.taskBook, result.task_book))
  const items = arrayFrom(book.items).filter((item) => text(objectFrom(item).title))
  const hung = items.filter((item) => {
    const row = objectFrom(item)
    return Boolean(text(firstPresent(row.hungEvidence, row.hung_evidence)))
  }).length
  return {
    hung,
    total: items.length,
    display: items.length ? `已回挂 ${hung}/${items.length}` : ''
  }
}

function isTaskBookPublished(input, result) {
  const book = objectFrom(firstPresent(input.taskBook, input.task_book, result.taskBook, result.task_book))
  return book.published === true || book.published === 'true'
}

function toCeilingGap(raw) {
  const row = objectFrom(raw)
  const title = text(row.title)
  const whyNotFull = text(firstPresent(row.whyNotFull, row.why_not_full))
  if (!title && !whyNotFull) return null
  return {
    title,
    whyNotFull,
    relatedClaimType: text(firstPresent(row.relatedClaimType, row.related_claim_type)),
    relatedDimension: text(firstPresent(row.relatedDimension, row.related_dimension))
  }
}

function publishedTaskTitles(input, result) {
  if (!isTaskBookPublished(input, result)) return []
  const book = objectFrom(firstPresent(input.taskBook, input.task_book, result.taskBook, result.task_book))
  return arrayFrom(book.items).slice(0, 4).map((item) => {
    const row = objectFrom(item)
    return {
      title: text(row.title),
      expectedGain: text(row.expectedGain || row.expected_gain)
    }
  }).filter((item) => item.title)
}

function findClaim(input, result, claimType) {
  const lists = [
    input.verifyClaims,
    input.verify_claims,
    input.claims,
    result.verifyClaims,
    result.verify_claims,
    result.claims
  ]
  for (const list of lists) {
    const found = arrayFrom(list).find((item) => objectFrom(item).claimType === claimType || objectFrom(item).claim_type === claimType)
    if (found) return objectFrom(found)
  }
  return null
}

function toClaim(spec, raw) {
  if (!raw) {
    return {
      claimType: spec.claimType,
      label: spec.label,
      verdict: 'insufficient',
      claimStatus: 'unverified',
      statement: '本场未核验',
      lit: false
    }
  }
  const claimStatus = text(firstPresent(raw.claimStatus, raw.claim_status)) || 'unverified'
  const verdict = text(raw.verdict) || 'insufficient'
  let statement = text(raw.statement)
  if (claimStatus === 'unverified') {
    if (!statement || FORBIDDEN_COPY.test(statement) || /赋能|领先|填补空白|已验证/.test(statement)) {
      statement = '本场未核验'
    }
  }
  return {
    claimType: spec.claimType,
    label: spec.label,
    verdict,
    claimStatus,
    statement: statement || '本场未核验',
    lit: claimStatus === 'retrieved_cited' || claimStatus === 'seen_in_session'
  }
}

function objectFrom(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function arrayFrom(value) {
  return Array.isArray(value) ? value : []
}

function firstPresent(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== '')
}

function text(value) {
  return value == null ? '' : String(value).trim()
}

function numberOrNull(value) {
  if (value == null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function intOrZero(value) {
  const number = numberOrNull(value)
  return number == null ? 0 : Math.max(0, Math.trunc(number))
}

function intOrNull(value) {
  const number = numberOrNull(value)
  return number == null ? null : Math.trunc(number)
}

function formatScore(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function formatPercent(value) {
  const pct = value <= 1 ? value * 100 : value
  return `${Math.round(pct)}%`
}
