const DEFAULT_SUGGESTIONS = {
  dashboard: [
    { title: '补齐项目亮点', description: '把技术方案、市场价值和团队分工合成一页路演要点。' },
    { title: '生成练习任务', description: '根据最近一次评分生成 3 个高优先级练习目标。' },
    { title: '检查 PPT 节奏', description: '确认 8 分钟路演稿与页面切换节奏是否匹配。' },
  ],
}

export function useOrepAgentSuggestions(page = 'dashboard') {
  return {
    page,
    suggestions: DEFAULT_SUGGESTIONS[page] || DEFAULT_SUGGESTIONS.dashboard,
  }
}
