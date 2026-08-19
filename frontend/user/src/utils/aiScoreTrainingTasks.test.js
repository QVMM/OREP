import test from 'node:test'
import assert from 'node:assert/strict'
import { buildTrainingTasks } from './aiScoreTrainingTasks.js'

test('normalizes backend training tasks with owner and acceptance contract', () => {
  const tasks = buildTrainingTasks({
    trainingTasks: [{
      taskId: 'training-task-1',
      title: '补齐：关键算法测试数据不足',
      correspondingDeduction: '关键算法测试数据不足',
      trainingAction: '补充稳定性和准确率测试记录',
      ownerRole: '技术负责人',
      timeSuggestion: '下一轮复评前完成补证、彩排和验收记录',
      acceptanceCriteria: '测试记录能证明核心演示稳定跑通',
      expectedRecoverPoints: 5,
      evidenceAnchorIds: [10],
      priority: 'P0'
    }]
  })

  assert.equal(tasks.length, 1)
  assert.equal(tasks[0].id, 'training-task-1')
  assert.equal(tasks[0].title, '补齐：关键算法测试数据不足')
  assert.equal(tasks[0].ownerRole, '技术负责人')
  assert.equal(tasks[0].trainingAction, '补充稳定性和准确率测试记录')
  assert.equal(tasks[0].expectedRecoverPoints, 5)
  assert.deepEqual(tasks[0].evidenceAnchorIds, [10])
  assert.equal(tasks[0].priority, 'P0')
})

test('builds verifiable fallback tasks from current deductions', () => {
  const tasks = buildTrainingTasks({
    structuredDeductions: [{
      reason: '客户访谈证据不足',
      requiredFix: '优化表达',
      acceptanceCriteria: '提供客户访谈截图并能说明来源',
      maxRecoverablePoints: 4,
      evidenceAnchorIds: [11],
      recovery: false,
      status: 'new'
    }]
  })

  assert.equal(tasks.length, 1)
  assert.match(tasks[0].trainingAction, /客户访谈证据不足/)
  assert.notEqual(tasks[0].trainingAction, '优化表达')
  assert.equal(tasks[0].ownerRole, '商业负责人')
  assert.equal(tasks[0].acceptanceCriteria, '提供客户访谈截图并能说明来源')
  assert.equal(tasks[0].expectedRecoverPoints, 4)
})
