import assert from 'node:assert/strict'
import { normalizeScoreRows } from '../src/utils/scoreResult.js'

const apiResult = {
  meetingId: 9,
  meetingTitle: '6.9',
  records: [
    {
      userId: 12,
      username: 'teacher',
      role: 'TEACHER',
      totalScore: 88,
      submittedAt: '2026-06-16T09:30:00',
      details: [
        {
          category: '技能水平',
          itemName: '操作规范性',
          maxScore: 10,
          score: 8,
          comment: '流程清晰'
        },
        {
          category: '职业素养',
          itemName: '安全意识',
          maxScore: 3,
          score: 3,
          comment: ''
        }
      ]
    }
  ]
}

assert.deepEqual(normalizeScoreRows(apiResult), [
  {
    id: '12_操作规范性',
    evaluatorName: 'teacher',
    evaluatorRole: 'TEACHER',
    category: '技能水平',
    itemName: '操作规范性',
    score: 8,
    maxScore: 10,
    comment: '流程清晰',
    createdAt: '2026-06-16T09:30:00',
    totalScore: 88
  },
  {
    id: '12_安全意识',
    evaluatorName: 'teacher',
    evaluatorRole: 'TEACHER',
    category: '职业素养',
    itemName: '安全意识',
    score: 3,
    maxScore: 3,
    comment: '',
    createdAt: '2026-06-16T09:30:00',
    totalScore: 88
  }
])

assert.deepEqual(normalizeScoreRows({ records: null }), [])
assert.deepEqual(normalizeScoreRows(null), [])
