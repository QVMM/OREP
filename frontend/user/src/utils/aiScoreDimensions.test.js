import assert from 'node:assert/strict'
import test from 'node:test'

import { buildAuthoritativeDimensions, dimensionDisplayName } from './aiScoreDimensions.js'

test('authoritative dimension scores win while diagnostic details are preserved', () => {
  const dimensions = buildAuthoritativeDimensions({
    authoritative: {
      skill_level: { score: 28, max_score: 60 },
      professionalism: { score: 2.1, max_score: 10 }
    },
    diagnostic: {
      skill_level: { name: '专业技能', score: 37.5, max_score: 60, items: [{ name: '技能展示' }] },
      professionalism: { name: '职业素养', score: 5.75, max_score: 10 }
    }
  })

  assert.deepEqual(dimensions.map(item => [item.key, item.name, item.score, item.maxScore]), [
    ['skill_level', '专业技能', 28, 60],
    ['professionalism', '职业素养', 2.1, 10]
  ])
  assert.deepEqual(dimensions[0].items, [{ name: '技能展示' }])
  assert.equal(dimensions.reduce((total, item) => total + item.score, 0), 30.1)
})

test('diagnostic dimensions remain a compatibility fallback', () => {
  const dimensions = buildAuthoritativeDimensions({
    diagnostic: {
      innovation: { name: '创新能力', score: 6, max_score: 10 }
    }
  })

  assert.equal(dimensions[0].score, 6)
  assert.equal(dimensions[0].name, '创新能力')
})

test('maps canonical dimension field names to user-facing Chinese labels', () => {
  assert.equal(dimensionDisplayName('skill_level'), '技能水平')
  assert.equal(dimensionDisplayName('professionalism'), '职业素养')
  assert.equal(dimensionDisplayName('application_value'), '应用价值')
  assert.equal(dimensionDisplayName('teamwork'), '团队协作')
  assert.equal(dimensionDisplayName('innovation'), '创新能力')
  // 后端把 key 写进 name 时仍显示中文
  assert.equal(dimensionDisplayName('skill_level', 'skill_level'), '技能水平')
  assert.equal(dimensionDisplayName('professionalism', 'professionalism'), '职业素养')
  assert.equal(dimensionDisplayName('skill_level', '专业技能'), '专业技能')
})
