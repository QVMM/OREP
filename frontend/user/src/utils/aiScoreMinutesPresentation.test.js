import test from 'node:test'
import assert from 'node:assert/strict'
import { buildMinutesPresentation, resolveActiveReviewState } from './aiScoreMinutesPresentation.js'

test('keeps a single real ASR speaker and never invents team members', () => {
  const view = buildMinutesPresentation({
    sessionId: 26,
    asrSegments: [
      { start: 6.66, end: 9.22, text: '尊敬的各位评委老师，大家好。', speaker: 'SPEAKER_0' },
      { start: 9.22, end: 12.4, text: '我们带来的项目是智慧农业。', speaker: 'SPEAKER_0' }
    ]
  })

  assert.equal(view.speakers.length, 1)
  assert.equal(view.speakers[0].rawSpeaker, 'SPEAKER_0')
  assert.equal(view.speakers[0].displayName, '发言人待确认')
  assert.equal(view.transcript[1].speakerName, '发言人待确认')
})

test('uses persisted millisecond timestamps and confirmed speaker identity without rescaling errors', () => {
  const view = buildMinutesPresentation({
    asrSegments: [
      {
        id: 12,
        startMs: 1250,
        endMs: 3750,
        text: '我们展示核心算法',
        rawSpeaker: 'SPEAKER_2',
        speakerName: '3号选手',
        roleName: 'AI算法工程师'
      }
    ],
    speakerMappings: [
      { rawSpeaker: 'SPEAKER_2', displayName: '3号选手', roleName: 'AI算法工程师', status: 'CONFIRMED' }
    ]
  })

  assert.equal(view.transcript[0].startSeconds, 1.25)
  assert.equal(view.transcript[0].endSeconds, 3.75)
  assert.equal(view.transcript[0].rawSpeaker, 'SPEAKER_2')
  assert.equal(view.transcript[0].speakerName, '3号选手 / AI算法工程师')
  assert.equal(view.speakers[0].confirmed, true)
})

test('links formal deductions to real evidence time and estimates time for unanchored deductions', () => {
  const view = buildMinutesPresentation({
    mediaPlayback: { durationSeconds: 3000, streamUrl: 'https://example.com/v.mp4' },
    deductions: [
      { id: 2, dimensionName: '技能水平', deductedPoints: 2, reason: 'AI 演示中断', evidenceAnchorIds: [10] },
      { id: 3, dimensionName: '职业素养', deductedPoints: 1.5, reason: '表达证据不足', evidenceAnchorIds: [] }
    ],
    evidenceAnchors: [
      { id: 10, startMs: 2438000, endMs: 2531960, evidenceText: '现场修改代码，演示中断' }
    ]
  })

  assert.equal(view.scoreEvents.length, 2)
  const anchored = view.scoreEvents.find(item => item.id === '2')
  const estimated = view.scoreEvents.find(item => item.id === '3')
  assert.equal(anchored.timeSeconds, 2438)
  assert.equal(anchored.points, 2)
  assert.equal(anchored.evidenceText, '现场修改代码，演示中断')
  assert.equal(anchored.timeEstimated, false)
  assert.ok(estimated.timeSeconds != null)
  assert.equal(estimated.timeEstimated, true)
  assert.match(estimated.timeLabel, /^约 /)
  assert.equal(view.timelineEvents.length, 2)
})

test('estimates event time from transcript keywords when anchors are missing', () => {
  const view = buildMinutesPresentation({
    mediaPlayback: { durationSeconds: 600, streamUrl: 'https://example.com/v.mp4' },
    asrSegments: [
      { start: 10, end: 20, text: '大家好我们开始介绍项目背景', speaker: 'SPEAKER_0' },
      { start: 180, end: 200, text: '接下来展示成本测算与报价表', speaker: 'SPEAKER_0' },
      { start: 400, end: 420, text: '谢谢各位评委', speaker: 'SPEAKER_0' }
    ],
    deductions: [
      { id: 7, dimensionName: '应用价值', deductedPoints: 3, reason: '成本测算缺少客户验证', evidenceAnchorIds: [] }
    ]
  })

  assert.equal(view.scoreEvents.length, 1)
  assert.ok(view.scoreEvents[0].timeSeconds != null)
  // 应靠近「成本测算」发言段
  assert.ok(Math.abs(view.scoreEvents[0].timeSeconds - 180) < 30 || view.scoreEvents[0].timeEstimated)
})

test('publishes the complete loss ledger and deduplicates an equivalent structured deduction', () => {
  const view = buildMinutesPresentation({
    lossLedger: [
      { lossId: 'loss-1', lossKey: 'O1:performance', lossType: 'performance_gap', points: 4, observationName: '操作规范', reason: '演示流程不稳定', evidenceAnchorIds: [2] },
      { lossId: 'loss-2', lossKey: 'O2:evidence', lossType: 'evidence_limited', points: 5, observationName: '应用价值', reason: '缺少客户验证证据' }
    ],
    deductions: [
      { id: 9, dimensionName: '技能水平', deductedPoints: 4, reason: '演示流程不稳定', evidenceAnchorIds: [88] }
    ],
    evidenceAnchors: [
      { id: 88, startMs: 2400000, endMs: 2430000, evidenceText: 'AI 模块现场故障' }
    ]
  })

  assert.equal(view.scoreEvents.length, 2)
  assert.equal(view.scoreEvents.reduce((sum, item) => sum + item.points, 0), 9)
  const demo = view.scoreEvents.find(item => item.title === '演示流程不稳定')
  const evidence = view.scoreEvents.find(item => item.title === '缺少客户验证证据')
  assert.equal(demo.timeSeconds, 2400)
  assert.equal(demo.evidenceText, 'AI 模块现场故障')
  assert.ok(evidence.timeSeconds != null)
  assert.equal(evidence.timeEstimated, true)
})

test('uses remapped observation anchors when loss ledger still carries pipeline-local anchor ids', () => {
  const view = buildMinutesPresentation({
    lossLedger: [{
      lossId: 'loss-o2',
      observationCode: 'O02',
      observationName: '技能熟练度',
      points: 7.5,
      reason: 'AI 演示中断 94 秒',
      evidenceAnchorIds: [1, 2, 3, 4]
    }],
    observations: [{
      observationCode: 'O02',
      evidenceAnchorIds: [291, 292, 293, 294]
    }],
    evidenceAnchors: [
      { id: 291, startMs: 480000, endMs: 510000, evidenceText: '现场操作片段' },
      { id: 294, startMs: 2340000, endMs: 2370000, evidenceText: 'AI 演示故障片段' }
    ]
  })

  assert.equal(view.scoreEvents.length, 1)
  assert.equal(view.timelineEvents.length, 1)
  assert.equal(view.scoreEvents[0].timeSeconds, 480)
  assert.deepEqual(view.scoreEvents[0].evidenceAnchorIds, ['291', '292', '293', '294'])
})

test('diagnostic advice never promises points when it has no formal scoring link', () => {
  const view = buildMinutesPresentation({
    diagnosticIssues: ['商业模式缺少客户获取策略']
  })

  assert.equal(view.diagnosticItems.length, 1)
  assert.equal(view.diagnosticItems[0].points, null)
  assert.equal(view.diagnosticItems[0].kind, 'diagnostic')
})

test('normalizes real pitch chapter ranges and resolves the active transcript and chapter', () => {
  const view = buildMinutesPresentation({
    asrSegments: [
      { start: 130, end: 140, text: '下面介绍总体方案。', speaker: 'SPEAKER_0' }
    ],
    pitchChapters: [
      { stage: '破冰钩子', time_range: '00:00-00:30', actual: '团队自我介绍' },
      { stage: '方案展示', time_range: '02:00-10:00', actual: '展示总体思路' },
      { stage: '团队致胜', time_range: '00:00-54:00（贯穿）', actual: '团队协作' }
    ]
  })

  assert.equal(view.chapters[1].startSeconds, 120)
  assert.equal(view.chapters[1].endSeconds, 600)
  const active = resolveActiveReviewState(view, 135)
  assert.equal(active.transcript.text, '下面介绍总体方案。')
  assert.equal(active.chapter.title, '方案展示')
})

test('uses only an explicit media contract and otherwise returns an honest empty media state', () => {
  const withoutMedia = buildMinutesPresentation({ sessionId: 26 })
  assert.equal(withoutMedia.media.available, false)
  assert.equal(withoutMedia.media.streamUrl, '')

  const withMedia = buildMinutesPresentation({
    sessionId: 26,
    mediaPlayback: {
      assetId: 77,
      contentType: 'video/mp4',
      durationSeconds: 3270.592,
      streamUrl: '/api/ai-score/sessions/26/media/video'
    }
  })
  assert.equal(withMedia.media.available, true)
  assert.equal(withMedia.media.durationSeconds, 3270.592)
})

test('renders final stable people in contestant visitor offscreen order without inventing unknown people', () => {
  const view = buildMinutesPresentation({
    speakerAttributionStatus: 'FINAL',
    stablePeople: [
      { personId: 'VISITOR_1', personType: 'VISITOR', displayName: '现场指导老师', personState: 'STABLE' },
      { personId: 'CONTESTANT_2', personType: 'CONTESTANT', contestantSlot: 2, displayName: '2号选手', roleName: '产品负责人' },
      { personId: 'OFFSCREEN_1', personType: 'OFFSCREEN', displayName: '画外发言人 1' },
      { personId: 'CONTESTANT_1', personType: 'CONTESTANT', contestantSlot: 1, displayName: '1号选手', roleName: '主讲人' }
    ],
    finalSpeakerSegments: [
      { segmentId: 'seg-1', startMs: 0, endMs: 1200, text: '各位评委好。', personId: 'CONTESTANT_1', speakerState: 'CONFIRMED', finalSegment: true },
      { segmentId: 'seg-2', startMs: 1200, endMs: 2000, text: '这里需要补充。', personId: 'VISITOR_1', speakerState: 'CONFIRMED', finalSegment: true },
      { segmentId: 'seg-3', startMs: 2000, endMs: 2600, text: '听不清是谁。', speakerState: 'UNKNOWN', finalSegment: true },
      { segmentId: 'seg-4', startMs: 2600, endMs: 3200, text: '多人同时回应。', speakerState: 'OVERLAP', finalSegment: true }
    ]
  })

  assert.equal(view.attributionStatus, 'FINAL')
  assert.equal(view.isStableFinal, true)
  assert.equal(view.stablePeople.length, 4)
  assert.deepEqual(view.speakers.map(item => item.personId), [
    'CONTESTANT_1', 'CONTESTANT_2', 'VISITOR_1', 'OFFSCREEN_1'
  ])
  assert.deepEqual(view.speakers.map(item => item.typeLabel), [
    '参赛选手', '参赛选手', '外部人员', '未识别'
  ])
  assert.equal(view.transcript[0].speakerName, '1号选手 / 主讲人')
  assert.equal(view.transcript[1].speakerName, '现场指导老师')
  assert.equal(view.transcript[2].speakerName, '发言人待确认')
  assert.equal(view.transcript[2].personId, null)
  assert.equal(view.transcript[3].speakerName, '多人同时发言')
  assert.equal(view.speakers.some(item => item.personId === 'UNKNOWN'), false)
})

test('stable presentation never exposes acoustic cluster labels in user-facing text', () => {
  const view = buildMinutesPresentation({
    speakerAttributionStatus: 'FINAL',
    stablePeople: [
      { personId: 'CONTESTANT_1', personType: 'CONTESTANT', contestantSlot: 1, displayName: '1号选手' }
    ],
    finalSpeakerSegments: [
      { segmentId: 'seg-1', startMs: 0, endMs: 1000, text: '开始汇报。', rawSpeaker: 'SPEAKER_8', personId: 'CONTESTANT_1', speakerState: 'CONFIRMED', finalSegment: true }
    ]
  })

  assert.equal(view.transcript[0].speakerName, '1号选手')
  assert.equal(JSON.stringify({ speakers: view.speakers, transcript: view.transcript }).includes('SPEAKER_8'), false)
})

test('final safe-unknown snapshot still renders every transcript segment without inventing people', () => {
  const view = buildMinutesPresentation({
    speakerAttributionStatus: 'FINAL',
    stablePeople: [],
    finalSpeakerSegments: [
      { segmentId: 'seg-1', startMs: 0, endMs: 1000, text: '第一段真实转写', speakerState: 'UNKNOWN', finalSegment: true },
      { segmentId: 'seg-2', startMs: 1000, endMs: 2000, text: '第二段真实转写', speakerState: 'UNKNOWN', finalSegment: true }
    ]
  })

  assert.equal(view.transcript.length, 2)
  assert.equal(view.speakers.length, 1)
  assert.equal(view.stablePeople.length, 0)
  assert.equal(view.isStableFinal, false)
  assert.equal(view.transcript[0].speakerName, '发言人待确认')
  assert.equal(JSON.stringify(view).includes('SPEAKER_'), false)
})

test('invalid legacy placeholder is never counted as a confirmed stable person', () => {
  const view = buildMinutesPresentation({
    speakerAttributionStatus: 'FINAL',
    stablePeople: [
      { personId: 'LEGACY_PLACEHOLDER', displayName: '发言人待确认' }
    ],
    finalSpeakerSegments: [
      { segmentId: 'seg-1', startMs: 0, endMs: 1000, text: '真实转写', speakerState: 'UNKNOWN', finalSegment: true }
    ]
  })

  assert.equal(view.stablePeople.length, 0)
  assert.equal(view.isStableFinal, false)
  assert.equal(view.speakers[0].displayName, '发言人待确认')
})
