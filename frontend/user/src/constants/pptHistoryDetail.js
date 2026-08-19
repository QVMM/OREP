export const ROADSHOW_STORY_PHASES = [
  {
    key: 'opening',
    order: '01',
    name: '开场定调',
    minutes: '3-5',
    required: true,
    roles: ['cover', 'agenda'],
    module_keys: [],
    goal: '让裁判快速知道项目名称、团队定位、汇报路径和比赛节奏。',
    missing_hint: '建议补首页和目录页。'
  },
  {
    key: 'problem_policy',
    order: '02',
    name: '政策背景与行业问题',
    minutes: '8-10',
    required: true,
    roles: ['policy_context', 'project_definition', 'market_pain'],
    module_keys: ['policy_context', 'problem_market'],
    goal: '先说明为什么这个项目值得做，用政策、行业需求和痛点建立必要性。',
    missing_hint: '建议补政策依据、项目定义和痛点需求页。'
  },
  {
    key: 'solution_tech',
    order: '03',
    name: '方案与核心技术',
    minutes: '12-15',
    required: true,
    roles: ['solution_overview', 'technical_architecture'],
    module_keys: ['solution_overview', 'technical_architecture'],
    goal: '展示方案闭环、关键技术、技术先进性和任务难度。',
    missing_hint: '建议补方案总览、架构图和核心技术页。'
  },
  {
    key: 'practice_demo',
    order: '04',
    name: '实操演示与证据',
    minutes: '18-22',
    required: true,
    roles: ['practice_demo'],
    module_keys: ['practice_demo'],
    goal: '用输入、操作、输出、证据证明技能熟练度和任务完成度。',
    missing_hint: '建议补实操步骤、系统截图、设备照片和结果证据。'
  },
  {
    key: 'value_innovation',
    order: '05',
    name: '应用价值与创新',
    minutes: '8-10',
    required: true,
    roles: ['application_value', 'innovation', 'future_plan'],
    module_keys: ['application_value', 'innovation_value'],
    goal: '回答项目对产业、社会、区域或民生有什么帮助，以及创新在哪里。',
    missing_hint: '建议补应用价值、创新成效和可持续发展页。'
  },
  {
    key: 'team_norms',
    order: '06',
    name: '团队协作与职业素养',
    minutes: '4-6',
    required: true,
    roles: ['team_collaboration', 'safety_norms', 'rd_journey', 'industry_education'],
    module_keys: ['team_collaboration', 'safety_norms', 'rd_journey', 'industry_education'],
    goal: '体现岗位职责、沟通协作、研发过程、安全规范和产教融合。',
    missing_hint: '建议补团队分工、安全规范、研发历程和产教融合页。'
  },
  {
    key: 'closing',
    order: '07',
    name: '总结答辩',
    minutes: '3-5',
    required: true,
    roles: ['summary'],
    module_keys: ['summary'],
    goal: '收束评分点、强化项目价值，为评委提问留下清晰锚点。',
    missing_hint: '建议补成果总结和答辩引导页。'
  }
]

export const JUDGE_SCORING_CATEGORIES = [
  {
    key: 'skill',
    name: '技能水平',
    weight: 60,
    keywords: ['操作规范', '技能熟练', '任务难易', '技术先进', '现场讲解', '技能水平'],
    description: '比赛最大权重，重点看实操规范、技术难度、先进性和现场表达。'
  },
  {
    key: 'professional',
    name: '职业素养',
    weight: 10,
    keywords: ['职业道德', '行为规范', '工匠精神', '安全意识', '安全规范', '知识产权'],
    description: '体现诚信守法、知识产权、安全规范、质量意识和职业风貌。'
  },
  {
    key: 'value',
    name: '应用价值',
    weight: 10,
    keywords: ['实用性', '经济性', '可持续', '应用价值', '乡村振兴', '高质量就业'],
    description: '判断项目能否解决真实问题，是否契合产业、区域和社会价值。'
  },
  {
    key: 'team',
    name: '团队合作',
    weight: 10,
    keywords: ['团队精神', '沟通协作', '岗位职责', '团队合作', '分工'],
    description: '看团队目标、角色定位、协作补位和现场配合是否清晰。'
  },
  {
    key: 'innovation',
    name: '创新创意',
    weight: 10,
    keywords: ['创新意识', '创新成效', '创新创意', '原创', '工艺创新', '服务模式'],
    description: '看原始创意、技术改良、流程优化和民生应用创新成效。'
  }
]
