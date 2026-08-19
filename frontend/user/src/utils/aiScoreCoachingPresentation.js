/**
 * Student-facing coaching copy helpers for 结果 / 待办.
 * Rule: never invent scores or external links. Templates are offline checklists only.
 */

/**
 * Expand a short reason into a readable paragraph for students.
 * Uses only provided fields; does not invent scoring claims.
 */
export function buildIssueParagraph({
  title = '',
  why = '',
  problem = '',
  how = '',
  dimension = '',
  priority = '',
  coveredGapPoints = null,
  scoreImpactLabel = ''
} = {}) {
  const body = firstLongText(problem, why, how)
  const cleanTitle = String(title || '').trim()
  const dim = String(dimension || '').trim()
  const bits = []

  if (body) {
    bits.push(body)
  } else if (cleanTitle) {
    bits.push(`本场在「${cleanTitle}」上暴露出明显短板，现场表达或证据还不足以支撑更高得分。`)
  }

  if (dim && !bits.join('').includes(dim)) {
    bits.push(`主要影响「${dim}」相关评分。`)
  }

  const gap = numberOrNull(coveredGapPoints)
  if (gap !== null && gap > 0) {
    bits.push(`该问题关联当前约 ${formatPoints(gap)} 分差距，建议优先处理。`)
  } else if (String(priority || '').toUpperCase() === 'P0' && !/优先/.test(bits.join(''))) {
    bits.push('属于本场优先整改项，建议先完成再处理其他事项。')
  }

  if (scoreImpactLabel && !bits.join('').includes(scoreImpactLabel)) {
    bits.push(scoreImpactLabel)
  }

  let text = bits.filter(Boolean).join('')
  text = text.replace(/\s+/g, ' ').trim()
  // Avoid ultra-short card copy that looks unprofessional.
  if (text && text.length < 36 && cleanTitle) {
    text = `${text}下一轮路演中需要把问题讲清楚、材料补齐，并在演示里可被评委直接核验。`
  }
  return text
}

/**
 * Split free-form method text into step rows for a student checklist table.
 */
export function buildHowSteps(how, {
  owner = '',
  acceptanceLines = [],
  timebox = ''
} = {}) {
  const explicit = extractStructuredSteps(how)
  const lines = explicit.length ? explicit : splitActionLines(how)
  if (!lines.length) return []

  const acceptPool = arrayFrom(acceptanceLines).map(String).filter(Boolean)
  return lines.slice(0, 8).map((line, index) => {
    const parsed = splitActionDeliverable(stripStepPrefix(line))
    return {
      step: index + 1,
      action: parsed.action,
      deliverable: parsed.deliverable || defaultDeliverable(index, parsed.action),
      owner: owner || guessOwner(parsed.action),
      timebox: timebox || '',
      acceptance: acceptPool[index] || acceptPool[0] || defaultStepAcceptance(index, parsed.action)
    }
  })
}

/** 去掉正文里自带的 1. / 1) / 3) 3) 等序号，避免和列表序号叠成「2. 2) …」 */
export function stripStepPrefix(text) {
  let s = String(text || '').trim()
  // 连续剥多层：如 "3) 3) 展示" → "展示"
  for (let i = 0; i < 4; i += 1) {
    const next = s
      .replace(/^(?:第[一二三四五六七八九十\d]+[步点条项])[：:\s]*/u, '')
      .replace(/^[（(]?[一二三四五六七八九十\d]+[）)、．.、]\s*/u, '')
      .replace(/^\d+\s*[)）\]］]\s*/u, '')
      .replace(/^\d+\s*[.．、:：]\s*/u, '')
      .trim()
    if (next === s) break
    s = next
  }
  return s
}

/**
 * Build student-usable references:
 * - real https links from report payload
 * - full copyable offline templates (body required; never title-only "假模板")
 * Never fabricate external URLs.
 */
export function buildReferences(task = {}) {
  const refs = []
  const seen = new Set()

  const push = (item) => {
    if (!item?.title) return
    const kind = item.kind || (item.url ? 'link' : (item.body ? 'template' : 'note'))
    // Only surface templates when full body exists — avoid misleading title+one-liner cards.
    if (kind === 'template' && !String(item.body || '').trim()) return
    // Drop empty notes that look like fake resources.
    if (kind === 'note' && !String(item.note || item.body || '').trim() && !item.url) return
    const key = `${item.title}|${item.url || ''}|${kind}|${String(item.body || '').slice(0, 40)}`
    if (seen.has(key)) return
    seen.add(key)
    refs.push({
      title: String(item.title),
      url: String(item.url || ''),
      kind,
      note: String(item.note || item.summary || '').trim(),
      body: String(item.body || '').trim(),
      copyable: Boolean(item.body) || Boolean(item.url)
    })
  }

  for (const raw of arrayFrom(firstPresent(
    task.references,
    task.referenceLinks,
    task.reference_links,
    task.resources,
    task.links
  ))) {
    if (typeof raw === 'string') {
      const text = raw.trim()
      if (!text) continue
      if (/^https?:\/\//i.test(text)) {
        push({ title: '参考链接', url: text, kind: 'link' })
      }
      // Ignore bare one-line strings — they look like fake templates.
      continue
    }
    if (!raw || typeof raw !== 'object') continue
    const title = firstPresent(raw.title, raw.name, raw.label, '参考材料')
    const url = firstPresent(raw.url, raw.href, raw.link, '')
    const body = firstPresent(raw.body, raw.content, raw.template, raw.text, '')
    const note = firstPresent(raw.note, raw.description, raw.desc, raw.summary, '')
    if (url) {
      push({ title: String(title), url: String(url), kind: 'link', note })
    } else if (String(body || '').trim().length >= 80) {
      push({ title: String(title), kind: 'template', body: String(body), note })
    }
    // Skip object-only titles/notes without real body or url.
  }

  // Keyword-matched full offline templates (copy-ready).
  const blob = [
    task.title,
    task.why,
    task.how,
    task.problem,
    task.dimension,
    task.observationCode
  ].map(v => String(v || '')).join(' ')

  const matched = matchOfflineTemplates(blob)
  for (const tpl of matched) push(tpl)

  return refs.slice(0, 4)
}

/** Full offline templates — each has a complete body students can copy into docs/PPT. */
export function getOfflineTemplateLibrary() {
  return {
    techCompare: {
      id: 'tech-compare',
      title: '技术对比与测试记录模板（可复制）',
      kind: 'template',
      note: '用于论证“为什么比常见方案更先进/更合适”。路演时做成 1 页表 + 1 组截图即可。',
      body: `【技术对比与测试记录】

一、要证明的结论（一句话）
- 我们要让评委相信：________ 比 ________ 更适合本场景，因为 ________。

二、对比对象（至少 1 个真实基线）
| 对比项 | 本方案 | 基线方案（写清名称/版本） | 说明 |
| --- | --- | --- | --- |
| 方案名称 |  |  |  |
| 核心思路 |  |  |  |
| 关键依赖/硬件 |  |  |  |
| 适用边界 |  |  |  |
| 主要风险 |  |  |  |

三、测试条件（必须可复核）
- 测试日期：____年__月__日
- 硬件环境：CPU/内存/设备型号：________
- 软件环境：系统/框架/版本：________
- 数据规模：________
- 测试工具：________（如 JMeter / 浏览器性能面板 / 自研脚本）
- 测试人：________

四、指标结果（填真实数字，并保留原始截图）
| 指标 | 本方案 | 基线方案 | 提升/差距 | 证据位置（截图编号） |
| --- | --- | --- | --- | --- |
| 响应时间 |  |  |  | 图1 |
| 吞吐/帧率 |  |  |  | 图2 |
| 资源占用 |  |  |  | 图3 |
| 准确率/稳定性 |  |  |  | 图4 |

五、路演讲法（30 秒）
1. 先报结论：我们比基线好在 ____。
2. 再报条件：同样在 ____ 环境下测。
3. 最后指证据：请看这张对比表/截图。

六、验收自检
□ 有明确基线，不是只列技术名词
□ 有测试条件，不是只报百分比
□ 有可展示截图或原始数据
□ 讲清适用边界与风险`
    },
    collabRetro: {
      id: 'collab-retro',
      title: '问题复盘与协作证据清单（可复制）',
      kind: 'template',
      note: '用于证明“团队真的协作过、问题真的闭环过”，不是只有角色介绍。',
      body: `【问题复盘与协作证据】

一、协作总览（路演 20 秒能讲完）
- 项目周期：____ 天 / 人周：____
- 角色分工：________（谁负责演示/代码/材料/测试）
- 协作工具：________（Git / 看板 / 文档）
- 例会频率：________

二、任务看板证据（贴截图）
| 任务 | 负责人 | 状态 | 起止时间 | 完成标准 |
| --- | --- | --- | --- | --- |
|  |  | 待办/进行中/完成 |  |  |
|  |  |  |  |  |

三、代码协作证据（贴截图）
- 仓库地址或本地提交记录：________
- 关键提交（3 条即可）：
  1) 日期____ 作者____ 说明____
  2) 日期____ 作者____ 说明____
  3) 日期____ 作者____ 说明____
- 代码评审/合并记录：有 / 无（有则截图）

四、问题闭环复盘（现场出过错更要写）
1. 现象：发生了什么？影响了哪一步演示？
2. 定位：谁发现、用什么方法定位、花了多久？
3. 根因：真正原因是什么？（配置/依赖/沟通/流程）
4. 修复：怎么修的？谁改的？
5. 验证：怎么证明已修好？
6. 预防：下次如何避免？（检查清单/自动化/双人复核）

五、交接话术（台上用）
- “这一段由 ____ 负责；我先讲结论，细节请 ____ 补充。”
- “刚才异常我们已定位到 ____，备选方案是 ____。”

六、验收自检
□ 能出示看板或提交记录截图
□ 至少 1 个真实问题有完整闭环
□ 台上能说清谁做什么、如何交接`
    },
    compliance: {
      id: 'compliance',
      title: '数据授权与合规声明模板（可复制）',
      kind: 'template',
      note: '用于补齐职业道德/隐私/授权类证据。可直接放进 PPT 或附录页。',
      body: `【数据来源、授权与合规声明】

一、项目使用的数据/素材清单
| 名称 | 类型（公开/采集/第三方） | 来源 | 是否含个人/敏感信息 | 授权/协议 | 用途 |
| --- | --- | --- | --- | --- | --- |
|  |  |  | 是/否 |  | 训练/演示/评测 |
|  |  |  |  |  |  |

二、授权与协议
1. 公开数据集：名称____，许可协议____，是否允许商用/参赛展示：____
2. 第三方 API/模型：名称____，调用范围____，密钥是否脱敏展示：是/否
3. 自行采集数据：采集对象____，告知方式____，是否取得同意：是/否
4. 代码与开源组件：主要依赖____，许可证____

三、隐私与安全处理
- 存储位置：________
- 访问控制：________
- 脱敏措施：________（打码/哈希/最小化字段）
- 演示环境是否使用真实隐私数据：是/否；若是，保护措施：________

四、学生真实贡献声明
- 本项目学生独立完成部分：________
- 教师/企业支持范围：________（指导/设备/数据，不含代做）
- 生成式 AI 使用说明：用于____；人工复核方式：____

五、路演讲法（15 秒）
“本项目数据来自 ____；展示已做 ____ 脱敏；第三方组件遵循 ____ 协议；核心实现由团队完成。”

六、验收自检
□ 数据来源说得清
□ 授权/协议可出示或可指认
□ 隐私处理说得清
□ 学生贡献边界清楚`
    },
    demoFallback: {
      id: 'demo-fallback',
      title: '演示容灾与彩排检查表（可复制）',
      kind: 'template',
      note: '用于减少现场中断。按表彩排 5 次，把结果填进右侧栏。',
      body: `【演示容灾与彩排检查表】

一、主流程脚本（按时间）
| 时间 | 讲解人 | 屏幕要展示的内容 | 必须说出的结论 | 失败时切换到 |
| --- | --- | --- | --- | --- |
| 0:00-0:30 |  | 封面/场景 |  | 备用页A |
|  |  |  |  |  |
|  |  |  |  |  |

二、容灾资产（必须提前准备）
□ 离线录屏（完整主路径，时长____秒，文件名____）
□ 关键截图包（不少于 6 张，按步骤编号）
□ 备用账号/本地数据（账号____，是否已登录验证）
□ 异常过渡话术（见下）
□ 网络失败预案：切换到____
□ 服务崩溃预案：切换到____

三、异常过渡话术（直接背）
1. “现场服务波动，我们切换到预录完整流程，结论不变：________。”
2. “当前环境限制 ____，请看这组离线结果，对应指标是 ____。”
3. “问题已定位为 ____，修复方案是 ____，不影响核心价值 ____。”

四、彩排记录（至少 5 次）
| 次数 | 日期 | 是否中断 | 中断点 | 切换是否顺利 | 总时长 | 改进点 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 |  | 是/否 |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |

五、验收自检
□ 连续 5 次彩排可完整走完或可无缝切备用
□ 备用材料与主讲结论一致
□ 每人知道自己在异常时说什么、点什么`
    },
    evidencePage: {
      id: 'evidence-page',
      title: '可复核证据页结构模板（可复制）',
      kind: 'template',
      note: '用于把“口头结论”变成“评委能当场核对的一页证据”。',
      body: `【可复核证据页（建议 1 结论 = 1 证据块）】

页面标题：________（例如：病害识别准确率证据）

1. 结论（大字，一句）
- ________

2. 证据（紧挨结论，不要翻很多页）
- 类型：□截图 □录屏时间点 □代码片段 □测试报告 □数据表
- 内容说明：________
- 来源：________（文件名/仓库路径/实验编号）
- 时间：________

3. 读图指引（告诉评委看哪里）
- 请看红框/第____行/第____列：________
- 关键数字：________
- 和基线对比：________

4. 局限与边界（主动说，避免被追问打穿）
- 本证据不覆盖：________
- 已知限制：________

5. 台上指证话术
“结论是 ____；证据在这里；来源是 ____；适用条件是 ____。”

6. 验收自检
□ 结论和证据在同一视野
□ 数字/截图可当场读懂
□ 来源可指认，不是“我们测过”
□ 有边界说明`
    }
  }
}

function matchOfflineTemplates(blob) {
  const lib = getOfflineTemplateLibrary()
  const out = []
  if (/先进|对比|基准|性能|测试|选型|技术栈/.test(blob)) out.push(lib.techCompare)
  if (/协作|分工|复盘|交接|看板|Git|闭环|团队/.test(blob)) out.push(lib.collabRetro)
  if (/合规|授权|隐私|伦理|知识产权|版权|安全|职业道德/.test(blob)) out.push(lib.compliance)
  if (/演示|容灾|兜底|中断|录像|离线|彩排/.test(blob)) out.push(lib.demoFallback)
  if (/证据|截图|报告|可复核|代码|证明材料/.test(blob)) out.push(lib.evidencePage)
  return out
}

export function priorityLabel(priority) {
  const value = String(priority || '').toUpperCase()
  if (value === 'P0' || value === 'HIGH') return '先改'
  if (value === 'P2' || value === 'LOW') return '可后改'
  return '建议改'
}

export function enrichCoachingItem(item = {}) {
  const why = String(item.why || item.problem || item.reason || item.desc || '').trim()
  const how = String(item.how || item.action || item.method || '').trim()
  const title = String(item.title || '').trim()
  // Prefer dedicated why/problem; only fall back to short how when why is empty.
  const issue = buildIssueParagraph({
    title,
    why,
    problem: item.problem,
    how: why ? '' : (how.length <= 120 ? how : ''),
    dimension: item.dimension,
    priority: item.priority,
    coveredGapPoints: item.coveredGapPoints,
    scoreImpactLabel: item.scoreImpactLabel
  })

  let howSteps = []
  if (Array.isArray(item.howSteps) && item.howSteps.length) {
    howSteps = item.howSteps.map((row, index) => {
      if (typeof row === 'string') {
        const text = stripStepPrefix(row)
        if (!text) return null
        return {
          step: index + 1,
          action: text,
          deliverable: defaultDeliverable(index, text),
          owner: String(item.ownerRole || item.owner || ''),
          timebox: String(item.timeSuggestion || item.timebox || ''),
          acceptance: ''
        }
      }
      if (row && typeof row === 'object') {
        const action = stripStepPrefix(firstPresent(row.action, row.method, row.text, row.title, ''))
        if (!action) return null
        return {
          step: Number(row.step) > 0 ? Number(row.step) : index + 1,
          action,
          deliverable: String(row.deliverable || row.output || ''),
          owner: String(row.owner || item.ownerRole || item.owner || ''),
          timebox: String(row.timebox || item.timeSuggestion || ''),
          acceptance: String(row.acceptance || '')
        }
      }
      return null
    }).filter(Boolean)
    // 重新顺号，避免 step 字段本身乱序/重复
    howSteps = howSteps.map((row, index) => ({ ...row, step: index + 1 }))
  }
  if (!howSteps.length) {
    howSteps = buildHowSteps(how, {
      owner: item.ownerRole || item.owner || '',
      acceptanceLines: item.doneLines || [],
      timebox: item.timeSuggestion || item.timebox || ''
    })
  }

  // Always normalize references: keep real links / full-body templates only.
  const references = buildReferences({
    ...item,
    why,
    how,
    title,
    references: item.references
  })

  return {
    ...item,
    issueParagraph: issue,
    why: why || issue,
    how,
    howSteps,
    references,
    priorityLabel: priorityLabel(item.priority),
    howPreview: howSteps[0]?.action || (how ? String(how).slice(0, 80) : '')
  }
}

function extractStructuredSteps(how) {
  if (Array.isArray(how)) {
    return how.map(row => {
      if (typeof row === 'string') return stripStepPrefix(row)
      if (row && typeof row === 'object') {
        return stripStepPrefix(firstPresent(row.action, row.method, row.text, row.title, ''))
      }
      return ''
    }).map(String).map(s => s.trim()).filter(Boolean)
  }
  if (how && typeof how === 'object') {
    const list = arrayFrom(firstPresent(how.steps, how.items, how.actions, how.change_actions, how.changeActions))
    return list.map(row => {
      if (typeof row === 'string') return stripStepPrefix(row)
      if (row && typeof row === 'object') {
        return stripStepPrefix(firstPresent(row.action, row.method, row.text, row.title, ''))
      }
      return ''
    }).map(String).map(s => s.trim()).filter(Boolean)
  }
  return []
}

function splitActionLines(how) {
  const text = String(how || '').trim()
  if (!text) return []

  // Numbered / bullet lists
  const numbered = text
    .split(/(?:^|\n)\s*(?:\d+[\.、\)］)]\s+|[-*•]\s+)/u)
    .map(s => s.trim())
    .filter(Boolean)
  if (numbered.length >= 2) return numbered

  // Chinese sequence markers: 1. 2. or 第一步
  const seq = text
    .split(/(?=(?:^|[\s；;。])(?:\d+[\.、]|[一二三四五六七八九十]+[、.．]|第[一二三四五六七八九十\d]+[步点条]))/u)
    .map(s => s.replace(/^(?:\d+[\.、]|[一二三四五六七八九十]+[、.．]|第[一二三四五六七八九十\d]+[步点条])\s*/u, '').trim())
    .filter(Boolean)
  if (seq.length >= 2) return seq

  // Sentence-ish split for long paragraphs
  if (text.length >= 48) {
    const parts = text
      .split(/[；;\n]+|(?<=[。！？])\s*/u)
      .map(s => s.trim())
      .filter(s => s.length >= 6)
    if (parts.length >= 2) return parts
  }

  return [text]
}

function splitActionDeliverable(line) {
  const text = String(line || '').trim()
  // Patterns like "做X，形成Y" / "做X并输出Y"
  const match = text.match(/^(.+?)(?:，形成|，产出|，附上|并输出|并整理|→|->|=>)(.+)$/u)
  if (match) {
    return { action: match[1].trim(), deliverable: match[2].trim() }
  }
  return { action: text, deliverable: '' }
}

function defaultDeliverable(index, action) {
  if (/截图|录屏|视频/.test(action)) return '可演示文件/截图'
  if (/文档|说明|声明|报告|清单|表格|对比/.test(action)) return '一页可展示材料'
  if (/彩排|演练|话术/.test(action)) return '彩排记录或话术稿'
  if (/代码|仓库|测试/.test(action)) return '代码片段/测试结果'
  return index === 0 ? '可展示材料' : '整改产出'
}

function defaultStepAcceptance(index, action) {
  if (/测试|对比|基准/.test(action)) return '评委能看到对照数据与测试条件'
  if (/授权|隐私|合规/.test(action)) return '有明确声明且可当场出示'
  if (/协作|看板|复盘/.test(action)) return '有过程截图或复盘记录'
  if (index === 0) return '材料可在路演中直接展示'
  return '下一轮彩排中可被核验'
}

function guessOwner(action) {
  if (/代码|测试|算法|架构|技术|接口|仓库/.test(action)) return '技术'
  if (/讲解|话术|开场|表达|PPT|演示/.test(action)) return '主讲'
  if (/协作|分工|复盘|管理|进度/.test(action)) return '项目负责人'
  if (/合规|授权|隐私|声明/.test(action)) return '项目负责人'
  return '项目负责人'
}

function firstLongText(...values) {
  for (const value of values) {
    const text = String(value || '').trim()
    if (text.length >= 12) return text
  }
  for (const value of values) {
    const text = String(value || '').trim()
    if (text) return text
  }
  return ''
}

function formatPoints(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}
