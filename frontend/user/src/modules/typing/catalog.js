/**
 * 通用打字题库 + 自主练习选项
 * 语言严格隔离：英文练习不会拼入中文段落。
 */

export const DIFFICULTY_OPTIONS = [
  { value: 1, label: '入门' },
  { value: 2, label: '标准' },
  { value: 3, label: '进阶' },
]

export const LANG_OPTIONS = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: '英文' },
  { value: 'mixed', label: '中英混排' },
]

/** 自主练习预设时长（秒）；也支持自定义分钟 */
export const DURATION_PRESETS = [
  { value: 60, label: '1 分钟' },
  { value: 300, label: '5 分钟' },
  { value: 600, label: '10 分钟' },
  { value: 1200, label: '20 分钟' },
  { value: 0, label: '自定义' },
]

export const COUNT_OPTIONS = [
  { value: 50, label: '50 字' },
  { value: 100, label: '100 字' },
  { value: 200, label: '200 字' },
  { value: 500, label: '500 字' },
]

const CATALOG = [
  // —— 中文 · 入门 ——
  { id: 'zh-p-01', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '今天天气很好，适合出门走走。路边的树叶绿了，风吹过来很舒服。我们约好一起去图书馆学习，路上买了一杯热豆浆。' },
  { id: 'zh-p-02', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '学习要一步一步来，不要着急。每天坚持一点点，时间久了就会看到变化。遇到不会的问题，先自己想，再去请教别人。' },
  { id: 'zh-p-03', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '早上七点起床，洗漱后吃早餐，然后去教室上课。中午休息一会儿，下午继续练习。晚上整理笔记，把重点记清楚。' },
  { id: 'zh-p-04', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '做事情要有计划。先分清轻重缓急，再安排时间。完成一件事就打勾，这样心里会更踏实，也更容易坚持下去。' },
  { id: 'zh-p-05', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '沟通很重要。说话要清楚，也要认真听对方说什么。有不同意见时，先理解再表达，这样合作会更顺利。' },
  { id: 'zh-p-06', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '读书可以打开视野。选一本喜欢的书，安静地读完一章，记下三句有启发的话。久而久之，表达会更清楚，想法也会更有条理。' },
  { id: 'zh-p-07', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '运动让人精神更好。每天散步二十分钟，或者做一组拉伸。身体轻松了，学习时也更能集中注意力，晚上也更容易入睡。' },
  { id: 'zh-p-08', lang: 'zh', tags: ['zh_passage'], difficulty: 1, text: '整理桌面是个好习惯。把用不到的东西收起来，常用文具放在顺手的位置。环境清爽了，做事也会更干脆。' },

  // —— 中文 · 标准 ——
  { id: 'zh-p-11', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '项目推进不能只靠热情，还要把目标拆成可执行的任务。每周回顾进度，及时调整计划。遇到阻塞时，尽早同步给团队，避免问题堆积到最后一刻。' },
  { id: 'zh-p-12', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '演示前要反复排练。熟悉每一页内容的衔接，控制好语速与停顿。准备好可能被问到的细节，用数据和案例支撑结论，而不是空泛的形容词。' },
  { id: 'zh-p-13', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '写作时先搭结构：提出问题、分析原因、给出方案、总结价值。每一段只表达一个中心意思，用具体例子代替抽象口号，读者才会愿意继续读下去。' },
  { id: 'zh-p-14', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '时间管理的关键是减少切换成本。同类事务集中处理，重要但不紧急的事先安排固定时段。手机通知可以暂时关闭，专注完成后的效率往往更高。' },
  { id: 'zh-p-15', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '反馈要具体、可操作。与其说「再优化一下」，不如指出哪一页逻辑跳跃、哪一组数据缺少来源。好的反馈帮助对方立刻改，而不是增加焦虑。' },
  { id: 'zh-p-16', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '技术选型要匹配场景。追求最新不一定最稳，成熟方案配合清晰边界往往更可靠。先验证核心路径，再扩展功能，能显著降低返工风险。' },
  { id: 'zh-p-17', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '路演叙事要有主线：用户是谁、痛点是什么、我们的方案如何解决、为什么现在可行。每一页都服务这条主线，观众才不会在细节里迷路。' },
  { id: 'zh-p-18', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '会议有效的前提是议程清楚、结论可追踪。会前发出材料，会中只讨论分歧，会后写下责任人与截止日期。这样会议才是推动工作，而不是消耗时间。' },
  { id: 'zh-p-19', lang: 'zh', tags: ['zh_passage'], difficulty: 2, text: '学习一门新技能时，先完成最小可用作品，再回头补理论。实践会暴露真正的卡点，带着问题去读文档，记忆会更深，也更有方向感。' },

  // —— 中文 · 进阶 ——
  { id: 'zh-p-21', lang: 'zh', tags: ['zh_passage'], difficulty: 3, text: '复杂系统的瓶颈常常不在算力，而在信息同步与决策链路。当多方协作时，要明确唯一真相来源，约定变更流程，并把异常处理路径写进预案，而不是依赖个人记忆。' },
  { id: 'zh-p-22', lang: 'zh', tags: ['zh_passage'], difficulty: 3, text: '表达专业度的方式之一，是精确使用概念边界：效率不等于效果，增长不等于健康增长，可用不等于可维护。澄清定义，讨论才能落到可验证的指标上。' },
  { id: 'zh-p-23', lang: 'zh', tags: ['zh_passage'], difficulty: 3, text: '评审材料时优先检查三件事：问题是否真实存在、方案是否覆盖关键约束、证据是否支撑结论。华丽的排版无法弥补逻辑缺口，反而会放大可信度风险。' },
  { id: 'zh-p-24', lang: 'zh', tags: ['zh_passage'], difficulty: 3, text: '产品决策应同时回答为什么做、为什么现在做、为什么由我们做。若其中一项含糊，就容易在资源分配上摇摆，最终既追不上市场，也建不起壁垒。' },
  { id: 'zh-p-25', lang: 'zh', tags: ['zh_passage'], difficulty: 3, text: '高质量交付依赖可复现的流程：版本可回滚、配置可审计、结果可度量。个人英雄主义能救急，但无法支撑规模化；制度与工具才是长期竞争力。' },

  // —— 英文 · 入门（纯英文，完整短文）——
  { id: 'en-01', lang: 'en', tags: ['en_passage'], difficulty: 1, text: 'The quick brown fox jumps over the lazy dog. Practice every day and you will get better soon. Keep your fingers on the home row and look at the screen, not the keyboard.' },
  { id: 'en-02', lang: 'en', tags: ['en_passage'], difficulty: 1, text: 'Good morning. Today is a good day to learn something new. Open your notebook, write three goals, and start with the smallest one. Small steps still move you forward.' },
  { id: 'en-03', lang: 'en', tags: ['en_passage'], difficulty: 1, text: 'Please type carefully. Speed will come later. First make fewer mistakes, then try to go a little faster. Accuracy builds confidence, and confidence builds speed.' },
  { id: 'en-04', lang: 'en', tags: ['en_passage'], difficulty: 1, text: 'She reads for twenty minutes after dinner. He reviews his notes before bed. They both sleep earlier this week. Simple habits can change a busy schedule.' },
  { id: 'en-05', lang: 'en', tags: ['en_passage'], difficulty: 1, text: 'Water the plants. Feed the cat. Check your bag for keys, phone, and wallet. Leave home five minutes early so you do not have to rush.' },
  { id: 'en-06', lang: 'en', tags: ['en_passage'], difficulty: 1, text: 'Thank you for your help. I finished the homework and sent it by email. If you have any questions, please let me know before Friday afternoon.' },

  // —— 英文 · 标准 ——
  { id: 'en-11', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'A clear plan helps the team move faster. Write down goals, track progress, and review results every week. When a task is blocked, raise it early so someone can help.' },
  { id: 'en-12', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'Please submit the report before Friday. Include key metrics, open risks, and the next action items for each owner. Keep the language simple so busy readers can scan it quickly.' },
  { id: 'en-13', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'Public speaking improves with practice. Start with a short outline, speak slowly, and pause after each main point. Record yourself once, then fix only one habit at a time.' },
  { id: 'en-14', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'Design for the user, not for the slide. Ask who will use this feature, what they need to finish, and how you will know it worked. Then cut anything that does not serve that path.' },
  { id: 'en-15', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'Email should be short. Put the request in the first line, list two or three facts, and end with a clear ask and a deadline. People reply faster when they know what to do next.' },
  { id: 'en-16', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'When you learn a new tool, build a tiny project on day one. Reading alone is not enough. Making something small will show you which parts you truly understand.' },
  { id: 'en-17', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'Meetings work better with an agenda. Share notes in advance, decide who speaks on each topic, and write decisions before people leave the room. Follow up in writing the same day.' },
  { id: 'en-18', lang: 'en', tags: ['en_passage'], difficulty: 2, text: 'Customer stories beat empty slogans. Describe the old pain, the moment of change, and the result with a number if you can. Specific details make your pitch feel real.' },

  // —— 英文 · 进阶 ——
  { id: 'en-21', lang: 'en', tags: ['en_passage'], difficulty: 3, text: 'Strategy is choosing what not to do. A team that tries to serve every request will ship nothing well. Protect focus, define success metrics, and review trade-offs in public so the whole group stays aligned.' },
  { id: 'en-22', lang: 'en', tags: ['en_passage'], difficulty: 3, text: 'Reliable systems prefer boring technology at the core. Novelty can live at the edges after the critical path is stable. Measure latency, error rate, and recovery time before you celebrate a new feature.' },
  { id: 'en-23', lang: 'en', tags: ['en_passage'], difficulty: 3, text: 'Writing forces clarity. If you cannot explain the problem in one paragraph, you do not yet own it. Draft the argument, cut adjectives, and keep only claims you can defend with evidence.' },
  { id: 'en-24', lang: 'en', tags: ['en_passage'], difficulty: 3, text: 'Feedback should name the behavior, the impact, and a concrete next step. Vague praise feels nice but teaches nothing. Specific critique is a gift when it is kind and actionable.' },
  { id: 'en-25', lang: 'en', tags: ['en_passage'], difficulty: 3, text: 'In a pitch, lead with the user problem, not the product architecture. Investors and judges follow a story: who hurts, why current options fail, why your approach wins now, and how you will grow.' },

  // —— 中英混排 ——
  { id: 'mx-01', lang: 'mixed', tags: ['mixed'], difficulty: 1, text: '打开 App 后先登录，再进入 Home 页面。点击 Start 开始练习，记得保存 Progress。如果提示 Error，请刷新后重试。' },
  { id: 'mx-02', lang: 'mixed', tags: ['mixed'], difficulty: 1, text: '今天的 To-do：写完 PPT 第 3 页，回复一封 Email，再把 Demo 录屏上传到云盘。完成一项就打勾，保持节奏。' },
  { id: 'mx-03', lang: 'mixed', tags: ['mixed'], difficulty: 2, text: '打开 Dashboard 查看今日 KPI，重点关注转化 funnel 第 2 步。如 API 超时超过 3 秒，请在 Slack 同步 oncall 同学。' },
  { id: 'mx-04', lang: 'mixed', tags: ['mixed'], difficulty: 2, text: '本次 Demo 使用 Vue3 与 FastAPI。部署环境为 staging，域名 example-test.com，账号仅限内部测试使用。' },
  { id: 'mx-05', lang: 'mixed', tags: ['mixed'], difficulty: 2, text: '请在 README 里写清：如何 install 依赖、如何 start 本地服务、如何跑 test。新同学按文档应在 15 分钟内跑通。' },
  { id: 'mx-06', lang: 'mixed', tags: ['mixed'], difficulty: 2, text: '路演时先讲 User Story，再展示 Product UI，最后用 Data 证明效果。Q and A 环节准备三个高频问题的标准回答。' },
  { id: 'mx-07', lang: 'mixed', tags: ['mixed'], difficulty: 3, text: '本次迭代目标是把 checkout 转化率从 2.1% 提升到 2.8%。核心改动包括支付 SDK 升级、表单校验优化，以及失败重试的 UX。' },
  { id: 'mx-08', lang: 'mixed', tags: ['mixed'], difficulty: 3, text: 'On-call 手册要求：收到 P1 alert 后 5 分钟内确认，15 分钟内给出临时止血方案，并在事后 24 小时内提交 postmortem。' },

  // —— 数字 / 标点（混排或中文语境）——
  { id: 'num-01', lang: 'mixed', tags: ['number'], difficulty: 1, text: '电话 138 0013 8000，房间号 1208，金额 256 元，时间 09:30，日期 2026-03-15，密码提示第 3 位是 7。' },
  { id: 'num-02', lang: 'mixed', tags: ['number'], difficulty: 2, text: '本季度完成 128 项任务，准时率 96.5%，平均响应 1.8 秒，错误率降至 0.12%，预算结余 3.4 万元，覆盖用户 2.6 万。' },
  { id: 'pu-01', lang: 'zh', tags: ['punctuation'], difficulty: 2, text: '他说：“这件事，不是做不到，而是还没找到方法。”是的——我们需要耐心、细心，还有一点勇气。' },
  { id: 'zh-c-01', lang: 'zh', tags: ['zh_common'], difficulty: 1, text: '因为所以但是然后如果虽然不过因此另外首先其次最后比如例如总之其实当然可能应该需要' },
  { id: 'zh-c-02', lang: 'zh', tags: ['zh_common'], difficulty: 2, text: '目标计划执行反馈优化协作沟通责任进度风险资源优先级里程碑验收复盘改进标准流程质量效率' },
]

function matchesLang(item, langPref) {
  if (!langPref || langPref === 'all') return true
  if (langPref === 'zh') return item.lang === 'zh'
  if (langPref === 'en') return item.lang === 'en'
  if (langPref === 'mixed') {
    return item.lang === 'mixed' || item.tags?.includes('mixed') || item.tags?.includes('number')
  }
  return true
}

function matchesDifficulty(item, difficulty) {
  if (!difficulty) return true
  return Number(item.difficulty) === Number(difficulty)
}

/**
 * 严格按语言取篇：绝不跨语言回退（避免英文练习拼出中文）。
 * 同语言题库用尽时允许重复抽取。
 */
export function pickPassage({ lang = 'zh', difficulty = 2, excludeIds = [] } = {}) {
  const exclude = new Set(excludeIds)
  const byLang = CATALOG.filter((item) => matchesLang(item, lang))
  if (!byLang.length) {
    // 理论上不应发生；兜底仍保持中文而非乱拼
    const zh = CATALOG.filter((i) => i.lang === 'zh')
    return zh[Math.floor(Math.random() * zh.length)] || CATALOG[0]
  }

  let pool = byLang.filter(
    (item) => matchesDifficulty(item, difficulty) && !exclude.has(item.id)
  )
  if (!pool.length) {
    pool = byLang.filter((item) => matchesDifficulty(item, difficulty))
  }
  if (!pool.length) {
    pool = byLang.filter((item) => !exclude.has(item.id))
  }
  if (!pool.length) {
    pool = byLang
  }
  return pool[Math.floor(Math.random() * pool.length)]
}

function joinSeparator(lang) {
  if (lang === 'en') return ' '
  if (lang === 'mixed') return ' '
  return ''
}

/** 为限时练习拼接足够长文本；同语言内循环，不串语种 */
export function buildPracticeText({ lang = 'zh', difficulty = 2, targetChars = 400 } = {}) {
  const parts = []
  const used = []
  let total = 0
  let guard = 0
  const sep = joinSeparator(lang)
  while (total < targetChars && guard < 80) {
    // 用尽后清空近期排除，允许同语言重复（仍不会串语种）
    const exclude = used.length >= 12 ? used.slice(-4) : used.slice(-12)
    const item = pickPassage({ lang, difficulty, excludeIds: exclude })
    used.push(item.id)
    const chunk = String(item.text || '').trim()
    if (!chunk) {
      guard += 1
      continue
    }
    parts.push(chunk)
    total += [...chunk].length + (parts.length > 1 ? [...sep].length : 0)
    guard += 1
  }
  return {
    text: parts.join(sep),
    sourceIds: used,
  }
}

export { CATALOG }
