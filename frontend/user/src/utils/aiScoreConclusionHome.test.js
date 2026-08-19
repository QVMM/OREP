import test from 'node:test'
import assert from 'node:assert/strict'
import { buildConclusionHome } from './aiScoreConclusionHome.js'

test('missing stability is 尚未复评 and never green', () => {
  const home = buildConclusionHome({ overallScore: 82, contractVersion: 'ai-score-report-v3' })
  assert.equal(home.officialScoreDisplay, '82')
  assert.equal(home.contractVersion, 'ai-score-report-v3')
  assert.equal(home.stability.band, 'not_reviewed')
  assert.equal(home.stability.headline, '尚未复评')
  assert.equal(home.stability.pinUnstable, false)
  assert.equal(home.teacherHeadline, '教师未确认')
  assert.equal(home.finalized, false)
  assert.equal(home.tasksAvailable, false)
  assert.deepEqual(home.tasks, [])
  assert.equal(home.gap.closureAvailable, false)
  assert.equal(home.gap.closureDisplay, '尚未计算')
})

test('single run cannot be green even if API says green', () => {
  const home = buildConclusionHome({
    overallScore: 80,
    stability: { band: 'green', runCount: 1, headline: '已经很准', runs: [{ runIndex: 1, officialScore: 80, scoreDeltaAbs: 0 }] }
  })
  assert.equal(home.stability.band, 'not_reviewed')
  assert.equal(home.stability.headline, '尚未复评')
  assert.equal(home.stability.runs[0].runIndex, 1)
})

test('older docket run keeps its score and points to a newer session', () => {
  const home = buildConclusionHome({
    overallScore: 48.3,
    stability: {
      band: 'red',
      runCount: 9,
      thisRunIndex: 7,
      newerSessionId: 47,
      newerRunIndex: 9,
      runs: [{ runIndex: 7, officialScore: 48.3, scoreDeltaAbs: 7.4 }]
    }
  })
  assert.equal(home.officialScore, 48.3)
  assert.equal(home.stability.thisRunIndex, 7)
  assert.equal(home.stability.newerSessionId, 47)
  assert.equal(home.stability.newerRunIndex, 9)
})

test('mixed identity band does not un-pin a red docket', () => {
  const home = buildConclusionHome({
    overallScore: 48.3,
    stability: {
      band: 'red',
      runCount: 9,
      headline: '本场不稳定，请教师复核',
      identityBand: 'green',
      identityRunCount: 3,
      identityHeadline: '最近权威分连续 3 次相同',
      runs: [
        { runIndex: 1, officialScore: 40.9, scoreDeltaAbs: 0 },
        { runIndex: 9, officialScore: 48.3, scoreDeltaAbs: 7.4 }
      ]
    }
  })
  assert.equal(home.stability.band, 'red')
  assert.equal(home.stability.pinUnstable, true)
  assert.equal(home.stability.mixed, true)
  assert.equal(home.stability.identityBand, 'green')
  assert.equal(home.stability.identityRunCount, 3)
  assert.match(home.stability.identityHeadline, /连续 3 次相同/)
})

test('stability runs keep coverage and seekable rates', () => {
  const home = buildConclusionHome({
    overallScore: 48.3,
    stability: {
      band: 'green',
      runCount: 2,
      headline: '复评分差在绿档',
      runs: [{
        runIndex: 2,
        officialScore: 48.3,
        scoreDeltaAbs: 0,
        transcriptCoverage: 0.98,
        seekableAnchorRate: 0.75
      }]
    }
  })
  assert.equal(home.stability.runs[0].transcriptCoverage, 0.98)
  assert.equal(home.stability.runs[0].seekableAnchorRate, 0.75)
})

test('red pins required teacher review copy', () => {
  const home = buildConclusionHome({
    overallScore: 80,
    stability: {
      band: 'red',
      runCount: 3,
      headline: '分数略有波动',
      runs: [
        { runIndex: 1, officialScore: 80, scoreDeltaAbs: 0 },
        { runIndex: 2, officialScore: 84, scoreDeltaAbs: 4 }
      ]
    }
  })
  assert.equal(home.stability.band, 'red')
  assert.equal(home.stability.headline, '本场不稳定，请教师复核')
  assert.equal(home.stability.pinUnstable, true)
})

test('does not treat coverageRate as closureRate', () => {
  const home = buildConclusionHome({
    overallScore: 70,
    coverageRate: 1,
    coverageSummary: { coverageRate: 1, status: 'complete' },
    result: { coverageSummary: { coverageRate: 1 } }
  })
  assert.equal(home.gap.closureAvailable, false)
  assert.equal(home.gap.officialScore, 70)
  assert.doesNotMatch(JSON.stringify(home), /完成度/)
})

test('tape grounded official keeps model review as a side number', () => {
  const home = buildConclusionHome({
    overallScore: 46,
    scoreGap: {
      officialScore: 46,
      modelReviewScore: 51.2,
      tapeGrounded: true,
      identityReason: '同一录像讲稿与同一套量表，权威分按转写命中词钉死，不跟模型每次重读走'
    }
  })
  assert.equal(home.gap.tapeGrounded, true)
  assert.equal(home.gap.modelReviewScore, 51.2)
  assert.match(home.gap.identityReason, /转写/)
})

test('closure 100 still keeps official score below ceiling and lists gaps', () => {
  const home = buildConclusionHome({
    overallScore: 88,
    scoreGap: {
      closureRate: 1,
      officialScore: 88,
      trackCeiling: 100,
      deltaFromLast: 8,
      ceilingGaps: [{ title: '运行演示仍缺', whyNotFull: '本场没有稳定演示证据。', relatedDimension: '职业素养' }]
    }
  })
  assert.equal(home.gap.closureAvailable, true)
  assert.equal(home.gap.closureDisplay, '100%')
  assert.equal(home.gap.officialScore, 88)
  assert.ok(home.gap.officialScore < home.gap.trackCeiling)
  assert.equal(home.gap.ceilingGaps.length, 1)
  assert.equal(home.seatsLit.ceiling, true)
  assert.doesNotMatch(JSON.stringify(home), /完成度 100%|完成度/)
})

test('always shows three unverified claims when none were computed', () => {
  const home = buildConclusionHome({ overallScore: 70 })
  assert.equal(home.claims.length, 3)
  assert.deepEqual(home.claims.map((item) => item.claimType), ['wrapper', 'advancement', 'value'])
  for (const claim of home.claims) {
    assert.equal(claim.claimStatus, 'unverified')
    assert.equal(claim.verdict, 'insufficient')
    assert.equal(claim.statement, '本场未核验')
    assert.equal(claim.lit, false)
  }
  assert.equal(home.seatsLit.claims, false)
  assert.equal(home.seatsLit.tasks, false)
})

test('seen_in_session claims stay visible and do not invent retrieved_cited', () => {
  const home = buildConclusionHome({
    overallScore: 37.6,
    verifyClaims: [
      { claimType: 'wrapper', verdict: 'fail', claimStatus: 'seen_in_session', statement: '本场有运行演示，但未说明差异。' },
      { claimType: 'advancement', verdict: 'fail', claimStatus: 'unverified', statement: '本场未核验先进性对照。' },
      { claimType: 'value', verdict: 'insufficient', claimStatus: 'seen_in_session', statement: '本场说清了服务谁。' }
    ]
  })
  assert.equal(home.claims[0].statement, '本场有运行演示，但未说明差异。')
  assert.equal(home.claims[0].lit, true)
  assert.equal(home.claims[1].claimStatus, 'unverified')
  assert.equal(home.seatsLit.claims, true)
  assert.doesNotMatch(JSON.stringify(home), /retrieved_cited/)
})

test('hung progress is not treated as closureRate', () => {
  const home = buildConclusionHome({
    overallScore: 43.2,
    taskBook: {
      published: true,
      items: [
        { title: '补齐差异与仓库证据', hungEvidence: '仓库页' },
        { title: '补齐对比测试证据' }
      ]
    },
    scoreGap: { officialScore: 43.2, closureRate: null }
  })
  assert.equal(home.gap.closureDisplay, '下场计算')
  assert.equal(home.gap.closureAvailable, false)
  assert.equal(home.gap.hungDisplay, '已回挂 1/2')
  assert.equal(home.gap.officialScore, 43.2)
})

test('published book with no prior run says 下场计算 not 尚未计算', () => {
  const awaiting = buildConclusionHome({
    overallScore: 43.2,
    taskBook: { published: true, items: [{ title: '补齐差异与仓库证据' }] },
    scoreGap: { officialScore: 43.2, closureRate: null }
  })
  assert.equal(awaiting.gap.closureAvailable, false)
  assert.equal(awaiting.gap.closureDisplay, '下场计算')
  assert.equal(awaiting.gap.closurePendingNextRun, true)
  assert.equal(awaiting.gap.officialScore, 43.2)

  const noBook = buildConclusionHome({
    overallScore: 43.2,
    scoreGap: { officialScore: 43.2 }
  })
  assert.equal(noBook.gap.closureDisplay, '尚未计算')
  assert.equal(noBook.gap.closurePendingNextRun, false)
})

test('unpublished task book stays hidden from the conclusion and student todos', () => {
  const hidden = buildConclusionHome({
    overallScore: 70,
    taskBook: { published: false, items: [{ title: '补齐仓库提交记录', expectedGain: '+2~4，下场对照，不保证' }] }
  })
  assert.equal(hidden.tasksAvailable, false)
  assert.deepEqual(hidden.tasks, [])
  assert.equal(hidden.gap.closureDisplay, '尚未计算')
  assert.equal(hidden.gap.closurePendingNextRun, false)
  const shown = buildConclusionHome({
    overallScore: 70,
    taskBook: { published: true, items: [{ title: '补齐仓库提交记录', expectedGain: '+2~4，下场对照，不保证' }] }
  })
  assert.equal(shown.tasksAvailable, true)
  assert.equal(shown.tasks[0].title, '补齐仓库提交记录')
})

test('unconfirmed deliberation is not final even if a task book exists', () => {
  const home = buildConclusionHome({
    overallScore: 70,
    deliberation: { stage: 'challenge', teacherConfirmed: false, finalized: false, challengeNote: '本场未完成质询' },
    taskBook: { published: true, items: [{ title: '补齐仓库提交记录' }] }
  })
  assert.equal(home.finalized, false)
  assert.equal(home.teacherHeadline, '本场未完成质询')
})

test('empty successful challenge scan is not incomplete', () => {
  const home = buildConclusionHome({
    overallScore: 48.3,
    deliberation: { stage: 'await_teacher', teacherConfirmed: false, finalized: false, challengeNote: '本场未发现可核验争议' }
  })
  assert.equal(home.finalized, false)
  assert.equal(home.teacherHeadline, '本场未发现可核验争议')
})

test('strips courtroom and overclaim copy', () => {
  const home = buildConclusionHome({
    overallScore: 88,
    stability: { band: 'yellow', runCount: 2, headline: '开庭后已经很准' }
  })
  assert.equal(home.stability.headline, '复评分差在黄档')
  assert.doesNotMatch(JSON.stringify(home), /法庭|开庭|落槌|已经很准|评议席已上/)
})
