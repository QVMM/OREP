import test from 'node:test'
import assert from 'node:assert/strict'
import { buildScoreSummaryPresentation, buildPrescriptions } from './aiScoreSummaryPresentation.js'

test('does not invent headline or sample analysis when fields missing', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 62.3,
    scoreLevel: { label: '风险较高', text: '需优化' },
    aiScore: {},
    result: {},
    trainingTasks: []
  })

  assert.equal(view.score.display, '62.3')
  assert.equal(view.hero.headline, '')
  assert.equal(view.hero.lead, '')
  assert.equal(view.hero.hasNarrative, false)
})

test('always uses 100 as the full-score reference instead of the next score band', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 62.3,
    scoreLevel: { label: '待提升', text: '需优化' },
    aiScore: {},
    result: {},
    trainingTasks: []
  })

  assert.equal(view.metrics.goalScore, 100)
  assert.equal(view.metrics.fullGap, 37.7)
  assert.equal(view.metrics.predictedScoreDisplay, '')
  assert.equal(view.metrics.predictedGainDisplay, '')
  assert.equal(view.metrics.targetScore, undefined)
  assert.equal(view.metrics.targetSource, undefined)
})

test('uses the backend portfolio projection and ignores legacy stage targets', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 49.5,
    scoreLevel: { label: '待提升', text: '' },
    scoreRecoverySummary: { target_score: 75 },
    scoreProjection: {
      goalScore: 100,
      currentScore: 49.5,
      fullGap: 50.5,
      predictedScoreLower: 61,
      predictedScoreUpper: 67.5,
      predictedGainLower: 11.5,
      predictedGainUpper: 18
    }
  })

  assert.equal(view.metrics.goalScore, 100)
  assert.equal(view.metrics.fullGap, 50.5)
  assert.equal(view.metrics.predictedScoreDisplay, '61.0～67.5')
  assert.equal(view.metrics.predictedGainDisplay, '+11.5～+18.0')
})

test('prescriptions prefer training tasks sorted by priority then recover points', () => {
  const list = buildPrescriptions({
    trainingTasks: [
      { id: 'b', title: '低优', priority: 'P2', expectedRecoverPoints: 9 },
      { id: 'a', title: '成本收益', priority: 'P0', expectedRecoverPoints: 4.2, trainingAction: '补三联表', acceptanceCriteria: '能复述投入产出' },
      { id: 'c', title: '开场', priority: 'P1', expectedRecoverPoints: 3 }
    ]
  })

  assert.equal(list[0].id, 'a')
  assert.equal(list[0].priority, 'P0')
  assert.equal(list[0].action, '补三联表')
  assert.equal(list[1].id, 'c')
  assert.equal(list[2].id, 'b')
})

test('summary counts the full unified queue but exposes only the top three prescriptions', () => {
  const unifiedTodos = Array.from({ length: 6 }, (_, index) => ({
    id: `todo-${index + 1}`,
    title: `待办 ${index + 1}`,
    priority: index < 2 ? 'P0' : index < 4 ? 'P1' : 'P2',
    how: `整改动作 ${index + 1}`,
    doneLines: [`验收标准 ${index + 1}`],
    recoverPoints: index === 0 ? 2 : null,
    recoverDisplay: index === 0 ? '+2.0' : ''
  }))

  const view = buildScoreSummaryPresentation({
    overallScore: 49.5,
    unifiedTodos,
    trainingTasks: [{ id: 'legacy-only', title: '不应覆盖统一队列' }]
  })

  assert.equal(view.metrics.prescriptionCount, 6)
  assert.equal(view.topPrescriptions.length, 3)
  assert.equal(view.morePrescriptionCount, 3)
  assert.equal(view.topPrescriptions[0].recoverPoints, 2)
  assert.equal(view.topPrescriptions[1].recoverPoints, null)
})

test('v3 summary explains the complete 100-point gap while showing three priorities', () => {
  const unifiedTodos = Array.from({ length: 23 }, (_, index) => ({
    id: `task-${index + 1}`,
    title: `整改 ${index + 1}`,
    priority: index < 3 ? 'P0' : 'P1',
    how: '按验收标准整改',
    doneLines: ['重新评分验证'],
    scoreImpactLabel: index < 18 ? '最低验收通过后，保守预计 +1.0～+2.0 分' : ''
  }))
  const view = buildScoreSummaryPresentation({
    overallScore: 49.5,
    unifiedTodos,
    lossLedger: Array.from({ length: 19 }, (_, index) => ({ lossId: `l${index}`, points: 1 })),
    coverageSummary: {
      lossItemCount: 19,
      remediationTaskCount: 23,
      coveredGapPoints: 50.5,
      coverageRate: 1,
      status: 'complete'
    },
    scoreProjection: { predictedScoreLower: 81, predictedScoreUpper: 96.5, predictedGainLower: 31.5, predictedGainUpper: 47 }
  })

  assert.equal(view.metrics.goalScore, 100)
  assert.equal(view.metrics.fullGap, 50.5)
  assert.equal(view.topPrescriptions.length, 3)
  assert.equal(view.metrics.prescriptionCount, 23)
  assert.equal(view.coverage.lossItemCount, 19)
  assert.equal(view.coverage.canClaimCompleteTodos, true)
})

test('describes recoverable points as a maximum rather than a promise', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 72,
    scoreLevel: { label: '良好', text: '' },
    scoreRecoverySummary: { totalRecoverable: 6.5 },
    trainingTasks: []
  })

  assert.equal(view.metrics.recoverable, 6.5)
  assert.equal(view.metrics.recoverableHint, '最高可追回约')
})

test('falls back to structured deductions via training task builder without inventing action fluff when present', () => {
  const list = buildPrescriptions({
    trainingTasks: [],
    currentStructuredDeductions: [{
      reason: '客户访谈证据不足',
      required_fix: '补充访谈纪要与客户确认截图',
      acceptance_criteria: '可出示原始访谈记录',
      max_recoverable_points: 4,
      recovery: false,
      priority: 'P0'
    }]
  })

  assert.equal(list.length, 1)
  assert.match(list[0].title, /客户访谈/)
  assert.equal(list[0].recoverPoints, 4)
  assert.ok(list[0].action)
})

test('moments only attach when anchors or prescription text exists; no fake transcript', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 70,
    trainingTasks: [{
      id: 't1',
      title: '数据来源',
      expectedRecoverPoints: 3,
      evidenceAnchorIds: [10],
      trainingAction: '补来源说明'
    }],
    evidenceAnchors: [{ id: 10, timestamp_seconds: 222 }],
    evidenceFrames: [{ id: 99, timestamp: 222, image_url: 'https://example.com/f.jpg' }],
    formatTime: (s) => `t:${s}`
  })

  assert.equal(view.moments.length, 1)
  assert.equal(view.moments[0].timeLabel, 't:222')
  assert.equal(view.moments[0].image, 'https://example.com/f.jpg')
  assert.equal(view.moments[0].title, '数据来源')
})

test('uses real overall_conclusion when present', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 80,
    aiScore: {
      overall_conclusion: '商业闭环基本成立，证据等级仍偏低',
      overall_analysis: '团队协作稳定。'
    }
  })
  assert.equal(view.hero.headline, '商业闭环基本成立，证据等级仍偏低')
  assert.equal(view.hero.lead, '团队协作稳定。')
  assert.equal(view.hero.hasNarrative, true)
})

test('continueLinks include compare only when previous delta or recovery exists', () => {
  const withoutCompare = buildScoreSummaryPresentation({
    overallScore: 70,
    trainingTasks: []
  })
  assert.equal(withoutCompare.continueLinks.length, 3)
  assert.equal(withoutCompare.continueLinks[0].key, 'todos')
  assert.equal(withoutCompare.continueLinks[1].key, 'why')
  assert.equal(withoutCompare.continueLinks[2].show, false)

  const withDelta = buildScoreSummaryPresentation({
    overallScore: 70,
    previousScoreDelta: 3.5,
    trainingTasks: [{ id: 't1', title: '补证据', priority: 'P0', expectedRecoverPoints: 2 }]
  })
  assert.equal(withDelta.continueLinks[2].show, true)
  assert.match(withDelta.continueLinks[0].desc, /1/)

  const withRecovery = buildScoreSummaryPresentation({
    overallScore: 70,
    scoreRecoverySummary: { recoveredCount: 2 },
    trainingTasks: []
  })
  assert.equal(withRecovery.continueLinks[2].show, true)
})

test('conclusion first screen does not advertise jury as a product path', () => {
  const view = buildScoreSummaryPresentation({
    overallScore: 72,
    previousScoreDelta: 3.5,
    juryResult: {
      officialScore: 72,
      juryAverageScore: 68.5,
      scoreDiffFromOfficial: -3.5,
      judgeCount: 9,
      status: 'completed'
    },
    trainingTasks: [{ id: 't1', title: '补证据', priority: 'P0', expectedRecoverPoints: 2 }]
  })
  assert.equal(view.continueLinks.some(link => link.key === 'jury'), false)
  assert.equal((view.intents || []).some(item => item.key === 'jury'), false)
  assert.equal((view.intents || []).some(item => String(item.title || '').includes('席')), false)
})

test('juryTeaser fills real numbers only and does not invent jury average', () => {
  const empty = buildScoreSummaryPresentation({
    overallScore: 72,
    trainingTasks: []
  })
  assert.equal(empty.juryTeaser.officialScore, 72)
  assert.equal(empty.juryTeaser.juryAverage, null)
  assert.equal(empty.juryTeaser.hasJuryResult, false)

  const withJury = buildScoreSummaryPresentation({
    overallScore: 72,
    juryResult: {
      officialScore: 72,
      juryAverageScore: 68.5,
      scoreDiffFromOfficial: -3.5,
      judgeCount: 9,
      status: 'completed'
    },
    trainingTasks: []
  })
  assert.equal(withJury.juryTeaser.officialScore, 72)
  assert.equal(withJury.juryTeaser.juryAverage, 68.5)
  assert.equal(withJury.juryTeaser.diff, -3.5)
  assert.equal(withJury.juryTeaser.memberCount, 9)
  assert.equal(withJury.juryTeaser.hasJuryResult, true)
})
