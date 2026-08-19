export function useOrepProjectContext(source = {}) {
  const priority = source.priority || {}
  const completion = Number.isFinite(priority.completion) ? priority.completion : 72

  return {
    projectName: source.projectName || priority.projectName || '智慧农业温室项目',
    projectMeta: source.projectMeta || '职业院校技能大赛 · 路演准备中',
    nextActionLabel: priority.nextActionLabel || '开始今日路演准备',
    lastProgressLabel: priority.lastProgressLabel || '脚本优化完成',
    scoreLabel: priority.scoreLabel || '上次路演 78 分',
    completion,
  }
}
