import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildRuleEngineReport,
  normalizeEvidenceLevel
} from './aiScoreRuleEngineReport.js'

test('normalizes rule engine shadow summary for new reports', () => {
  const report = buildRuleEngineReport({
    overallScore: 86,
    ruleEngineShadow: {
      llmRawScore: 91.5,
      ruleEngineScore: 78,
      scoreDiff: -13.5,
      diffReasons: ['score_diff_exceeds_10'],
      scoringFingerprint: 'fp-101'
    },
    structuredObservations: [
      {
        id: 1,
        observationCode: 'O01',
        dimensionName: '技能水平',
        rawScore: 8,
        scoreCap: 5,
        evidenceLevel: 'E2',
        confidence: 0.82,
        modelReason: '只有流程解释，缺少现场验证',
        evidenceAnchorIds: [10]
      }
    ],
    structuredDeductions: [
      {
        id: 2,
        observationCode: 'O01',
        dimensionName: '技能水平',
        deductedPoints: 2,
        maxRecoverablePoints: 2,
        reason: '缺少可复现实验',
        requiredFix: '补充实验记录',
        acceptanceCriteria: '能复现实验并提供截图',
        evidenceLevel: 'E2',
        evidenceAnchorIds: [10],
        recovery: false
      }
    ]
  })

  assert.equal(report.hasShadow, true)
  assert.equal(report.llmRawScore, 91.5)
  assert.equal(report.ruleEngineScore, 78)
  assert.equal(report.scoreDiff, -13.5)
  assert.equal(report.scoreDiffText, '-13.5')
  assert.equal(report.statusText, '需要复核')
  assert.equal(report.checkTitle, '评分一致性校验')
  assert.equal(report.llmRawLabel, '当前展示分')
  assert.equal(report.ruleEngineLabel, '证据规则参考')
  assert.equal(report.scoreDiffLabel, '校验差异')
  assert.equal(report.diffReasonText, '证据规则校验与当前展示分差异较大')
  assert.equal(report.observations.length, 1)
  assert.equal(report.observations[0].evidenceLevelLabel, 'E2 解释性证据')
  assert.equal(report.observations[0].capText, '5.0')
  assert.equal(report.observations[0].deductions.length, 1)
  assert.equal(report.observations[0].deductions[0].recoverableText, '2.0')
})

test('keeps legacy reports readable without shadow fields', () => {
  const report = buildRuleEngineReport({
    overallScore: 82,
    structuredObservations: [],
    structuredDeductions: []
  })

  assert.equal(report.hasShadow, false)
  assert.equal(report.statusText, '未完成校验')
  assert.equal(report.observations.length, 0)
  assert.equal(report.diffReasonText, '当前报告尚未生成证据规则校验结果')
})

test('normalizes old and new evidence levels', () => {
  assert.equal(normalizeEvidenceLevel('E4').label, 'E4 场景验证证据')
  assert.equal(normalizeEvidenceLevel('medium').label, '中等证据')
  assert.equal(normalizeEvidenceLevel('').label, '未标注')
})
