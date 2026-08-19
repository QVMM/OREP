import test from 'node:test'
import assert from 'node:assert/strict'
import { buildTodosPresentation } from './aiScoreTodosPresentation.js'

test('does not invent practice when no trainingAction/coaching script data', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 't1',
      title: '补客户访谈',
      correspondingDeduction: '客户访谈证据不足',
      trainingAction: '补充访谈纪要',
      acceptanceCriteria: '可出示原始访谈记录|评委可复核',
      priority: 'P0',
      expectedRecoverPoints: 4
    }]
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].how, '补充访谈纪要')
  assert.deepEqual(view.items[0].doneLines, ['可出示原始访谈记录', '评委可复核'])
  assert.equal(view.items[0].practice, null)
  assert.equal(view.selectedId, 't1')
})

test('sorts P0 before P1/P2 then recover points desc', () => {
  const view = buildTodosPresentation({
    trainingTasks: [
      { id: 'b', title: '低优', priority: 'P2', expectedRecoverPoints: 9 },
      { id: 'a', title: '成本收益', priority: 'P0', expectedRecoverPoints: 4.2 },
      { id: 'c', title: '开场', priority: 'P1', expectedRecoverPoints: 3 },
      { id: 'd', title: 'P0 高分', priority: 'P0', expectedRecoverPoints: 8 }
    ]
  })

  assert.deepEqual(view.items.map(item => item.id), ['d', 'a', 'c', 'b'])
  assert.equal(view.selectedId, 'd')
})

test('empty input yields empty items and empty selectedId', () => {
  const view = buildTodosPresentation({})
  assert.deepEqual(view.items, [])
  assert.equal(view.selectedId, '')
})

test('practice only when real say/stage coaching fields exist', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 'p1',
      title: '开场节奏',
      priority: 'P1',
      expectedRecoverPoints: 2,
      practice: {
        say: '先报项目名，再报场景',
        stage: '面向评委，停两秒'
      }
    }]
  })

  assert.deepEqual(view.items[0].practice, {
    say: '先报项目名，再报场景',
    stage: '面向评委，停两秒'
  })
})

test('scheme 1: work-item description/suggestion maps to how, not stuck as empty 怎么改', () => {
  const view = buildTodosPresentation({
    trainingTasks: [],
    reportWorkItemDrafts: [{
      id: 'rubric-skill-0',
      title: '处理评分项：技能熟练度',
      description: '增加快捷键操作、批量处理、脚本自动化等高阶技能展示，减少填充词，优化讲解节奏。',
      priority: 'HIGH'
    }]
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].title, '技能熟练度')
  assert.equal(
    view.items[0].how,
    '增加快捷键操作、批量处理、脚本自动化等高阶技能展示，减少填充词，优化讲解节奏。'
  )
  // how and why should not be the same wall of fix text
  assert.notEqual(view.items[0].why, view.items[0].how)
})

test('scheme 1: suggestion field maps to how when trainingAction missing', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 't-sugg',
      title: '任务难易度',
      reason: '难度论证不足',
      suggestion: '补充任务分解与难度梯度说明',
      priority: 'P1'
    }]
  })

  assert.equal(view.items[0].how, '补充任务分解与难度梯度说明')
  assert.equal(view.items[0].why, '难度论证不足')
})

test('extracts action text when trainingAction contains a serialized task object', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 'serialized-action',
      title: '提升技能熟练度的现场达成度',
      trainingAction: "{'title': '补齐技能熟练度证据链', 'action': '请补充现场操作脚本、异常处理预案、关键工具配置说明。', 'acceptanceCriteria': ['形成主张-证据-时间戳/页码对应表', '下一轮路演主动说明补证内容'], 'sourceType': 'orep_training'}",
      acceptanceCriteria: '操作路径、工具名称、关键配置、异常处理、时间控制',
      priority: 'P0'
    }]
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].how, '请补充现场操作脚本、异常处理预案、关键工具配置说明。')
  assert.equal(view.items[0].how.includes("'sourceType'"), false)
  assert.deepEqual(view.items[0].doneLines, ['操作路径、工具名称、关键配置、异常处理、时间控制'])
})

test('scheme 2: merges drafts when sparse trainingTasks would have blocked them', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 'sparse-1',
      title: '技能熟练度',
      priority: 'P0'
      // no how fields
    }],
    reportWorkItemDrafts: [{
      id: 'draft-skill',
      title: '技能熟练度',
      description: '增加快捷键操作与批量处理演示',
      priority: 'HIGH'
    }]
  })

  const skill = view.items.find(item => item.title === '技能熟练度')
  assert.ok(skill)
  assert.equal(skill.how, '增加快捷键操作与批量处理演示')
})

test('scheme 2: dedupes same title keeping richer item', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 'a',
      title: '开场定位',
      priority: 'P1'
    }],
    reportWorkItemDrafts: [{
      id: 'b',
      title: '开场定位',
      description: '开场只留对象、痛点、交付三句',
      acceptanceCriteria: '陌生人30秒能复述',
      priority: 'HIGH'
    }]
  })

  const openers = view.items.filter(item => item.title === '开场定位')
  assert.equal(openers.length, 1)
  assert.equal(openers[0].how, '开场只留对象、痛点、交付三句')
  assert.deepEqual(openers[0].doneLines, ['陌生人30秒能复述'])
})

test('integrates action-plan coaching tasks into one todo queue', () => {
  const view = buildTodosPresentation({
    trainingTasks: [],
    reportWorkItemDrafts: [],
    actionPlanCoaching: {
      tasks: [{
        id: 'ap1',
        title: '补经营闭环表',
        reason: '利润测算缺位',
        action: '补一张投入产出与风险兜底表',
        priority: 'HIGH',
        dimension: '应用价值'
      }]
    }
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].title, '补经营闭环表')
  assert.equal(view.items[0].how, '补一张投入产出与风险兜底表')
  assert.equal(view.items[0].why, '利润测算缺位')
  assert.equal(view.items[0].dimension, '应用价值')
})

test('merges six formal action plans with one score-linked duplicate into six todos', () => {
  const actionPlan = [
    {
      id: 'action-ai',
      priority: 'P0',
      title: 'AI问答模块稳定性加固与备用方案',
      problem: 'AI模块演示严重故障',
      method: '增加离线知识库和备用视频',
      acceptance: '连续5次演示零故障',
      observationCode: 'O02',
      sourceIssueKey: 'SKILL_DEMO_FAILURE',
      expectedRecoverPoints: 99
    },
    { id: 'action-code', priority: 'P0', title: '精简代码讲解', problem: '代码讲解过长', method: '只讲核心逻辑', acceptance: '讲解不超过5分钟' },
    { id: 'action-data', priority: 'P1', title: '补充数据来源', problem: '数据缺乏来源', method: '标注数据来源', acceptance: '每个数据可追溯' },
    { id: 'action-business', priority: 'P1', title: '完善商业模式', problem: '商业路线不完整', method: '补充商业模式画布', acceptance: '可说清收入来源' },
    { id: 'action-security', priority: 'P2', title: '补安全测试', problem: '安全证据缺失', method: '补漏洞扫描报告', acceptance: '报告可复核' },
    { id: 'action-speed', priority: 'P2', title: '优化语速', problem: '语速过快', method: '按220至250字每分钟彩排', acceptance: '填充词减少50%' }
  ]
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 'training-task-1',
      title: '技能熟练度缺少可定位证据',
      correspondingDeduction: '技能熟练度缺少可定位证据',
      trainingAction: '补齐技能熟练度证据链',
      acceptanceCriteria: '证据可定位且能支撑观测点',
      priority: 'P0',
      expectedRecoverPoints: 2,
      observationCode: 'O02',
      sourceIssueKey: 'score-deduction:O02'
    }],
    actionPlan
  })

  assert.equal(view.items.length, 6)
  assert.equal(view.items.filter(item => item.recoverPoints !== null).length, 1)
  const linked = view.items.find(item => item.observationCode === 'O02')
  assert.ok(linked)
  assert.equal(linked.recoverPoints, 2)
  assert.equal(linked.how.includes('离线知识库') || linked.how.includes('证据链'), true)
  assert.equal(view.items.find(item => item.id === 'action-code').recoverPoints, null)
})

test('dedupes by sourceIssueKey and ignores action-plan recovery claims', () => {
  const view = buildTodosPresentation({
    actionPlan: [{
      id: 'formal-1',
      title: '补经营闭环表',
      problem: '利润测算缺位',
      method: '补投入产出表',
      sourceIssueKey: 'business-loop',
      expectedRecoverPoints: 8
    }],
    reportWorkItemDrafts: [{
      id: 'draft-1',
      title: '商业模式补证',
      description: '补一张投入产出与风险兜底表',
      sourceIssueKey: 'business-loop'
    }]
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].recoverPoints, null)
})

test('recognizes Python action-plan coaching training_tasks contract', () => {
  const view = buildTodosPresentation({
    actionPlanCoaching: {
      training_tasks: [{
        id: 'coach-1',
        title: '演示故障切换彩排',
        why_it_matters: '现场中断会削弱可信度',
        change_actions: ['准备离线版', '准备录屏'],
        acceptance_standard: '10秒内完成备用方案切换'
      }]
    }
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].title, '演示故障切换彩排')
  assert.deepEqual(view.items[0].doneLines, ['10秒内完成备用方案切换'])
})

test('integrates expression/presentation coaching moments as practice-rich todos', () => {
  const view = buildTodosPresentation({
    trainingTasks: [],
    expressionCoaching: {
      moments: [{
        id: 'm1',
        title: '开场三句',
        reason: '前30秒信息过载',
        suggestion: '只留对象、痛点、交付',
        say: '我们帮谁，痛在哪，交付什么。',
        stage: '三句之间留半秒停顿'
      }]
    }
  })

  assert.equal(view.items.length, 1)
  assert.equal(view.items[0].title, '开场三句')
  assert.equal(view.items[0].how, '只留对象、痛点、交付')
  assert.deepEqual(view.items[0].practice, {
    say: '我们帮谁，痛在哪，交付什么。',
    stage: '三句之间留半秒停顿'
  })
})

test('exports dimension on normalized items', () => {
  const view = buildTodosPresentation({
    trainingTasks: [{
      id: 'd1',
      title: '合规专段',
      dimensionName: '职业素养',
      trainingAction: '中段留40秒专段',
      priority: 'P1'
    }]
  })
  assert.equal(view.items[0].dimension, '职业素养')
})

test('renders rule-backed score impact language and never scores unlinked advice', () => {
  const view = buildTodosPresentation({
    actionPlan: [
      {
        id: 'deduction',
        title: '修复演示故障',
        observationCode: 'O1',
        scoreImpact: {
          scoreLinkStatus: 'linked',
          impactType: 'deduction_recovery',
          lower: 2,
          upper: 2
        }
      },
      {
        id: 'evidence',
        title: '补充数据来源',
        observationCode: 'O2',
        scoreImpact: {
          scoreLinkStatus: 'linked',
          impactType: 'evidence_unlock',
          lower: 1,
          upper: 2
        }
      },
      {
        id: 'performance',
        title: '优化讲解节奏',
        observationCode: 'O3',
        scoreImpact: {
          scoreLinkStatus: 'linked',
          impactType: 'performance_improvement',
          lower: 2,
          upper: 4
        }
      },
      {
        id: 'unlinked',
        title: '额外训练建议',
        scoreImpact: {
          scoreLinkStatus: 'unlinked',
          lower: null,
          upper: null,
          reason: 'no_scoring_rule_link'
        }
      }
    ]
  })

  const byId = Object.fromEntries(view.items.map(item => [item.id, item]))
  assert.equal(byId.deduction.scoreImpactLabel, '最高可追回约 2.0 分')
  assert.equal(byId.evidence.scoreImpactLabel, '补证并核验通过后，预计可争取 1.0～2.0 分')
  assert.equal(byId.performance.scoreImpactLabel, '达到验收标准后，预计可提升 2.0～4.0 分')
  assert.equal(byId.unlinked.scoreImpactLabel, '')
  assert.equal(byId.unlinked.scoreLinked, false)
  assert.equal(byId.unlinked.sourceLabel, '额外训练建议')
})

test('v3 uses the formal remediation queue only and preserves same-title task ids', () => {
  const view = buildTodosPresentation({
    contractVersion: 'ai-score-report-v3',
    remediationTasks: [
      {
        taskId: 'task-a', title: '补齐证据', priority: 'P0', coveredLossIds: ['l1'], coveredGapPoints: 5,
        minimumAcceptance: { summary: '材料可定位' }, fullScoreCriteria: { summary: '现场可复核' },
        status: 'not_started', scoreImpact: { scoreLinkStatus: 'linked', impactType: 'mixed', lower: 2, upper: 4 }
      },
      {
        taskId: 'task-b', title: '补齐证据', priority: 'P1', coveredLossIds: ['l2'], coveredGapPoints: 3,
        acceptance: '完成彩排', status: 'in_progress', scoreImpact: { scoreLinkStatus: 'unlinked' }
      }
    ],
    trainingTasks: [{ id: 'legacy', title: '旧任务不应混入' }],
    coverageSummary: { lossItemCount: 2, remediationTaskCount: 2, coveredGapPoints: 8, coverageRate: 1, status: 'complete' }
  })

  assert.equal(view.items.length, 2)
  assert.deepEqual(view.items.map(item => item.id), ['task-a', 'task-b'])
  assert.equal(view.items[0].coveredGapPoints, 5)
  assert.deepEqual(view.items[0].coveredLossIds, ['l1'])
  assert.equal(view.items[0].scoreImpactLabel, '最低验收通过后，保守预计 +2.0～+4.0 分')
  assert.equal(view.items[1].scoreImpactLabel, '')
  assert.equal(view.items[1].status, 'in_progress')
  assert.equal(view.coverage.canClaimCompleteTodos, true)
})

test('unpublished task book hides student todos even when remediation exists', () => {
  const hidden = buildTodosPresentation({
    contractVersion: 'ai-score-report-v3',
    taskBook: { published: false, items: [{ title: '补齐仓库提交记录', expectedGain: '+2~4，下场对照，不保证' }] },
    remediationTasks: [{ taskId: 'task-a', title: '补齐证据', priority: 'P0' }]
  })
  assert.equal(hidden.items.length, 0)
  const shown = buildTodosPresentation({
    contractVersion: 'ai-score-report-v3',
    taskBook: { published: true, items: [{ title: '补齐仓库提交记录', expectedGain: '+2~4，下场对照，不保证', steps: ['列出缺口', '补上证据'] }] }
  })
  assert.equal(shown.items.length, 1)
  assert.equal(shown.items[0].title, '补齐仓库提交记录')
})

test('published task book exposes hang fields', () => {
  const view = buildTodosPresentation({
    taskBook: {
      published: true,
      items: [{
        title: '补齐差异与仓库证据',
        evidenceNeeded: '仓库提交页',
        hungEvidence: 'https://git.example/diff'
      }]
    }
  })
  assert.equal(view.items[0].itemIndex, 0)
  assert.equal(view.items[0].evidenceNeeded, '仓库提交页')
  assert.equal(view.items[0].hungEvidence, 'https://git.example/diff')
})
