/**
 * 小启 SSE 事件 → 消息对象状态机（首页 / 工作台共用）
 * @param {string} event
 * @param {object} data
 * @param {object} last assistant message (mutated)
 * @param {{ onUserMessageId?: (id: number, runId?: number) => void }} [hooks]
 */
export function applyAssistantStreamEvent(event, data, last, hooks = {}) {
  if (!last || last.role !== 'assistant') return

  if (event === 'run_started') {
    last.status = 'streaming'
    last.runId = data?.runId != null ? Number(data.runId) : last.runId
    if (!last.streamStartedAt) last.streamStartedAt = Date.now()
    if (data?.assistantMessageId != null) last.id = Number(data.assistantMessageId)
    if (data?.userMessageId != null) {
      last.parentUserMessageId = Number(data.userMessageId)
      hooks.onUserMessageId?.(Number(data.userMessageId), last.runId)
    }
    return
  }

  if (event === 'thinking_delta') {
    if (!last.thinkingStartedAt) last.thinkingStartedAt = Date.now()
    if (!last.streamStartedAt) last.streamStartedAt = Date.now()
    last.thinkingText = `${last.thinkingText || ''}${data?.text || ''}`
    // 正文未开始前保持 thinking；一旦已有正文，勿把 phase 打回 thinking
    if (last.phase !== 'answering' && !(last.contentText || last.text)) {
      last.phase = 'thinking'
    }
    return
  }

  if (event === 'thinking_done') {
    last.thinkingDone = true
    if (last.thinkingStartedAt && last.thinkingDurationMs == null) {
      last.thinkingDurationMs = Math.max(0, Date.now() - last.thinkingStartedAt)
    }
    return
  }

  if (event === 'content_replace') {
    // 用清洗后的全文覆盖（如去掉模型幻觉的 <function=search>）
    const text = data?.text != null ? String(data.text) : ''
    if (!last.answerStartedAt && text) {
      last.answerStartedAt = Date.now()
      last.thinkingDone = true
      if (last.thinkingStartedAt && last.thinkingDurationMs == null) {
        last.thinkingDurationMs = Math.max(0, Date.now() - last.thinkingStartedAt)
      }
    }
    last.phase = 'answering'
    last.contentText = text
    last.text = text
    return
  }

  if (event === 'content_delta') {
    const chunk = data?.text || ''
    if (!last.answerStartedAt && chunk) {
      last.answerStartedAt = Date.now()
      last.thinkingDone = true
      // 进入回答阶段时冻结思考用时
      if (last.thinkingStartedAt && last.thinkingDurationMs == null) {
        last.thinkingDurationMs = Math.max(0, Date.now() - last.thinkingStartedAt)
      }
      // 综合步骤标完成
      const synth = (last.steps || []).find((s) => s.stepKey === 'synthesize' && s.status === 'running')
      if (synth) {
        synth.status = 'completed'
        synth.outputSummary = '开始输出'
      }
    }
    last.phase = 'answering'
    last.contentText = `${last.contentText || ''}${chunk}`
    // 兼容首页旧字段
    last.text = last.contentText
    // 流式过程中若已出现伪工具调用，做轻量剥除（最终 content_replace 会再盖一次）
    if (/<function\s*=/i.test(last.contentText) || /<parameter\s*=/i.test(last.contentText)) {
      last.contentText = last.contentText
        .replace(/<function\s*=[^>]*>[\s\S]*?(?:<\/function>|$)/gi, '')
        .replace(/<parameter\s*=[^>]*>[^\n]*/gi, '')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
      last.text = last.contentText
    }
    return
  }

  if (event === 'intent') {
    if (data?.assumptions?.length || data?.projectHint || data?.slots?.project_name || data?.goal) {
      last.brainHints = {
        project: data.projectHint || data.slots?.project_name || '',
        goal: data.goal || '',
        assumptions: data.assumptions || [],
        softIntent: !!data.softIntent,
      }
    }
    last.intent = data || {}
    return
  }

  if (event === 'step_start') {
    last.steps = last.steps || []
    last.phase = last.phase === 'answering' ? 'answering' : 'thinking'
    if (!last.streamStartedAt) last.streamStartedAt = Date.now()
    if (!last.thinkingStartedAt) last.thinkingStartedAt = Date.now()
    const patch = normalizeStep(data, 'running')
    const existing = last.steps.find(
      (s) => s.stepNo === patch.stepNo && s.stepKey === patch.stepKey
    )
    if (existing) Object.assign(existing, patch)
    else last.steps.push(patch)
    return
  }

  if (event === 'step_end') {
    const step = (last.steps || []).find((s) => s.stepNo === data?.stepNo)
    if (step) {
      Object.assign(step, normalizeStep({ ...step, ...data }, data?.status || 'completed'))
    } else if (data) {
      last.steps = last.steps || []
      last.steps.push(normalizeStep(data, data?.status || 'completed'))
    }
    return
  }

  if (event === 'agent_note') {
    last.agentNotes = last.agentNotes || []
    last.agentNotes.push({
      id: `note-${Date.now()}-${last.agentNotes.length}`,
      agent: data?.agent || '小启',
      agentKey: data?.agentKey || 'captain',
      text: data?.text || '',
      at: Date.now(),
    })
    if (last.agentNotes.length > 12) last.agentNotes = last.agentNotes.slice(-12)
    last.phase = last.phase === 'answering' ? 'answering' : 'thinking'
    if (!last.thinkingStartedAt) last.thinkingStartedAt = Date.now()
    return
  }

  if (event === 'agent_kickoff') {
    last.status = 'streaming'
    last.phase = 'thinking'
    if (!last.streamStartedAt) last.streamStartedAt = Date.now()
    if (!last.thinkingStartedAt) last.thinkingStartedAt = Date.now()
    if (Array.isArray(data?.agents) && data.agents.length) {
      last.kickoffAgents = data.agents
    }
    last.processLabel = data?.label || '代理思考中'
    return
  }

  if (event === 'skill_match') {
    const skills = Array.isArray(data?.skills) ? data.skills : []
    last.skills = skills
    if (skills.length) {
      last.agentNotes = last.agentNotes || []
      const labels = skills
        .map((s) => (s.slash ? `/${s.slash}` : s.name) + (s.description ? ` · ${s.description}` : ''))
        .filter(Boolean)
      last.agentNotes.push({
        id: `skill-${Date.now()}`,
        agent: '技能',
        agentKey: 'skills',
        text: `启用：${labels.join('；')}`,
        at: Date.now(),
      })
      if (last.agentNotes.length > 12) last.agentNotes = last.agentNotes.slice(-12)
    }
    last.phase = last.phase === 'answering' ? 'answering' : 'thinking'
    if (!last.thinkingStartedAt) last.thinkingStartedAt = Date.now()
    return
  }

  if (event === 'process_done') {
    last.processSummary = {
      durationMs: data?.durationMs != null ? Number(data.durationMs) : null,
      stepCount: data?.stepCount != null ? Number(data.stepCount) : 0,
      sourceCount: data?.sourceCount != null ? Number(data.sourceCount) : 0,
      siteCount: data?.siteCount != null ? Number(data.siteCount) : 0,
      webCount: data?.webCount != null ? Number(data.webCount) : 0,
    }
    if (last.processSummary.durationMs != null && last.thinkingDurationMs == null) {
      last.thinkingDurationMs = Math.max(0, last.processSummary.durationMs)
    }
    last.processPhase = 'done'
    return
  }

  if (event === 'tool_start' || event === 'tool_result') {
    // 归一化为 step_start / step_end 形状
    last.steps = last.steps || []
    if (!last.streamStartedAt) last.streamStartedAt = Date.now()
    if (!last.thinkingStartedAt) last.thinkingStartedAt = Date.now()
    const status = event === 'tool_result' ? (data?.status || 'completed') : 'running'
    const patch = normalizeStep({
      ...data,
      kind: 'tool',
      stepKey: data?.stepKey || data?.tool || 'tool',
      action: data?.action || data?.title || (event === 'tool_result' ? '已检索' : '检索中'),
      query: data?.query || '',
      resultCount: data?.resultCount,
    }, status)
    const existing = last.steps.find(
      (s) => (s.stepNo != null && s.stepNo === patch.stepNo)
        || (s.stepKey && s.stepKey === patch.stepKey && s.status === 'running')
    )
    if (existing) Object.assign(existing, patch)
    else last.steps.push(patch)
    last.phase = last.phase === 'answering' ? 'answering' : 'thinking'
    return
  }

  if (event === 'ocr_progress') {
    last.ocrLogs = last.ocrLogs || []
    const label = data?.label || '解析资料中…'
    last.ocrLogs.push(label)
    if (last.ocrLogs.length > 12) last.ocrLogs = last.ocrLogs.slice(-12)
    last.steps = last.steps || []
    let step = last.steps.find((s) => s.stepKey === 'extract' || s.stepNo === 0)
    if (!step) {
      last.steps.unshift({
        stepNo: 0,
        stepKey: 'extract',
        title: label,
        status: 'running',
        agent: '资料',
      })
    } else {
      step.title = label
      step.status = 'running'
    }
    return
  }

  if (event === 'citation') {
    last.citations = last.citations || []
    const index = last.citations.length + 1
    last.citations.push({
      index: data?.index != null ? Number(data.index) : index,
      title: data?.title || '来源',
      snippet: data?.snippet || '',
      url: data?.url || '',
      sourceType: data?.sourceType || (data?.resourceId ? 'resource' : data?.url ? 'web' : 'unknown'),
      resourceId: data?.resourceId,
      fileId: data?.fileId,
      reportId: data?.reportId,
      sessionId: data?.sessionId,
      ocr: data?.ocr,
      method: data?.method,
      fromCache: data?.fromCache,
    })
    return
  }

  if (event === 'message_completed') {
    if (data?.contentText != null) {
      last.contentText = data.contentText
      last.text = data.contentText
    }
    if (Array.isArray(data?.citations) && data.citations.length) {
      last.citations = data.citations.map((c, i) => ({
        index: c.index != null ? Number(c.index) : i + 1,
        title: c.title || '来源',
        snippet: c.snippet || '',
        url: c.url || '',
        sourceType: c.sourceType || (c.resourceId ? 'resource' : c.url ? 'web' : 'unknown'),
        resourceId: c.resourceId,
        fileId: c.fileId,
        reportId: c.reportId,
        sessionId: c.sessionId,
        ocr: c.ocr,
        method: c.method,
        fromCache: c.fromCache,
      }))
    }
    if (Array.isArray(data?.files) && data.files.length) {
      last.files = data.files.map((f) => ({
        ...f,
        fileId: f.fileId || f.id,
        id: f.id || f.fileId,
      }))
    }
    last.status = 'completed'
    last.phase = 'done'
    last.thinkingDone = true
    if (last.thinkingStartedAt && last.thinkingDurationMs == null) {
      last.thinkingDurationMs = Math.max(
        0,
        (last.answerStartedAt || Date.now()) - last.thinkingStartedAt
      )
    }
    promoteReasoningToAnswerIfNeeded(last)
    return
  }

  if (event === 'run_completed') {
    const st = data?.status
    if (st === 'failed') last.status = 'failed'
    else if (st === 'cancelled') last.status = 'cancelled'
    else if (last.status === 'streaming') last.status = 'completed'
    last.phase = last.status === 'completed' ? 'done' : last.phase
    last.thinkingDone = true
    if (last.thinkingStartedAt && last.thinkingDurationMs == null) {
      last.thinkingDurationMs = Math.max(0, Date.now() - last.thinkingStartedAt)
    }
    // 不要覆盖 error 事件已经写好的真实原因
    if (st === 'failed' && !last.contentText && !last.text && !last.errorMessage) {
      last.errorMessage = data?.message || '生成失败，请稍后重试。'
    } else if (st === 'failed' && data?.message && !last.errorMessage) {
      last.errorMessage = data.message
    }
    if (last.status === 'completed') {
      promoteReasoningToAnswerIfNeeded(last)
    }
    return
  }

  if (event === 'error' || event === 'run_failed') {
    last.status = 'failed'
    last.errorMessage = data?.message || '小启暂时无法回答，请稍后重试。'
    return
  }

  if (event === 'plan_draft') {
    last.planDrafts = last.planDrafts || []
    const kind = data?.kind || 'plan'
    if (!last.planDrafts.some((d) => d.kind === kind && d.status === 'pending')) {
      last.planDrafts.push({
        kind,
        title: data?.title || (kind === 'rewrite' ? '改稿草案' : '计划草案'),
        summary: data?.summary || '确认后展开完整版',
        confirmLabel: data?.confirmLabel || '展开完整版',
        expandText: data?.expandText || (kind === 'rewrite' ? '展开完整改稿' : '展开完整计划'),
        status: data?.status || 'pending',
      })
    }
    last.brainHints = {
      ...(last.brainHints || {}),
      needLightConfirm: true,
      lightConfirmKind: kind,
    }
    return
  }

  if (event === 'action_proposal') {
    last.actionProposals = last.actionProposals || []
    const id = data?.proposalId
    if (id != null && !last.actionProposals.some((p) => String(p.proposalId) === String(id))) {
      last.actionProposals.push({
        proposalId: id,
        actionType: data.actionType,
        title: data.title,
        summary: data.summary,
        args: data.args,
        confirmLabel: data.confirmLabel || '确认执行',
        cancelLabel: data.cancelLabel || '取消',
        status: data.status || 'pending',
        expiresAt: data.expiresAt,
        resultMessage: '',
        _busy: false,
      })
    }
    return
  }

  if (event === 'file' || event === 'artifact') {
    last.files = last.files || []
    last.files.push(data)
  }
}

/**
 * 部分模型把整段回答打进 reasoning_content，正文 content 为空。
 * 结束后把可用 reasoning 提升为正文，避免一直卡在 Thinking。
 */
export function promoteReasoningToAnswerIfNeeded(last) {
  if (!last || last.role !== 'assistant') return
  const content = String(last.contentText || last.text || '').trim()
  const think = String(last.thinkingText || '').trim()
  if (content || think.length < 24) return
  last.contentText = think
  last.text = think
  last.answerStartedAt = last.answerStartedAt || Date.now()
  last.phase = 'done'
  // 避免「推理区 + 正文」重复全文：推理区只留摘要
  if (think.length > 360) {
    last.thinkingText = `${think.slice(0, 280).trim()}…`
  }
}

function normalizeStep(data = {}, status = 'running') {
  const kind = data.kind
    || (String(data.stepKey || '').includes('search') ? 'tool' : 'agent')
  const resultCount = data.resultCount != null
    ? Number(data.resultCount)
    : parseResultCount(data.outputSummary)
  return {
    stepNo: data.stepNo,
    stepKey: data.stepKey,
    kind,
    action: data.action || data.title || '处理中',
    query: data.query || '',
    title: data.title || data.action || '处理中…',
    status,
    resultCount: Number.isFinite(resultCount) ? resultCount : null,
    outputSummary: data.outputSummary || '',
    agent: data.agent || '',
    agentKey: data.agentKey || '',
  }
}

function parseResultCount(summary) {
  if (!summary) return null
  const m = String(summary).match(/(\d+)\s*(结果|条)/)
  return m ? Number(m[1]) : null
}

export function createEmptyAssistantMessage(localId) {
  return {
    _localId: localId || `a-${Date.now()}`,
    role: 'assistant',
    contentText: '',
    text: '',
    thinkingText: '',
    steps: [],
    agentNotes: [],
    ocrLogs: [],
    citations: [],
    files: [],
    brainHints: null,
    actionProposals: [],
    planDrafts: [],
    status: 'streaming',
    phase: 'starting',
    streamStartedAt: Date.now(),
    thinkingStartedAt: Date.now(),
    answerStartedAt: null,
    thinkingDurationMs: null,
    thinkingDone: false,
    errorMessage: '',
  }
}

export function createUserMessage(content, localId) {
  return {
    _localId: localId || `u-${Date.now()}`,
    role: 'user',
    contentText: content,
    text: content,
    status: 'completed',
  }
}
