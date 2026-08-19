import { computed } from 'vue'

export function usePptRepairWorkspace(options) {
  const {
    repairHistory,
    repairCandidate,
    repairPreviewNextActionText,
    strategyText,
    pageRoleText,
    failedCheckMessages,
    gateActionText,
    gateCheckText,
    sequenceSeverityText
  } = options

  const repairHistoryItems = computed(() => repairHistory.value?.items || [])
  const repairHistoryRecommendation = computed(() => repairHistory.value?.recommendation || null)
  const repairHistoryRecommendationActionText = computed(() => {
    const mode = repairHistoryRecommendation.value?.mode
    const map = {
      restore_best_repaired: '恢复推荐版本',
      attach_evidence: '去补素材证据',
      structure_rebuild: '升级重做此页',
      regenerate_html: '重新生成修复预览'
    }
    return map[mode] || '执行推荐动作'
  })

  const repairPreviewContext = computed(() => repairCandidate.value?.repair_context || {})
  const repairPreviewAssessment = computed(() => repairCandidate.value?.repair_assessment || null)
  const repairPreviewAutoEscalation = computed(() => repairCandidate.value?.auto_escalation || null)
  const repairPreviewAutoEscalationText = computed(() => {
    const escalation = repairPreviewAutoEscalation.value
    if (!escalation?.triggered) return ''
    return `系统检测到首次修复收益不足，已自动从「${strategyText(escalation.from_strategy) || escalation.from_strategy}」升级为「${strategyText(escalation.to_strategy) || escalation.to_strategy}」。`
  })
  const repairPreviewBeforeIssues = computed(() => {
    const contextIssues = repairPreviewContext.value?.failed_messages || []
    if (contextIssues.length) return contextIssues
    return failedCheckMessages(repairCandidate.value?.quality_before || {})
  })
  const repairPreviewAfterIssues = computed(() => {
    return failedCheckMessages(repairCandidate.value?.quality_preview || {})
  })
  const repairPreviewContextItems = computed(() => {
    const context = repairPreviewContext.value || {}
    const items = []

    if (context.slide_role) {
      items.push(`页面角色：${pageRoleText(context.slide_role)}`)
    }
    if (context.page_goal) {
      items.push(`页面目标：${context.page_goal}`)
    }
    ;(context.generation_gate_events || []).slice(0, 2).forEach(event => {
      const failed = Array.isArray(event.failed_checks) && event.failed_checks.length
        ? `，触发项：${event.failed_checks.map(gateCheckText).join('、')}`
        : ''
      items.push(`生成期门禁：${gateActionText(event.action)}${failed}`)
    })
    ;(context.sequence_events || []).slice(0, 2).forEach(event => {
      items.push(`结构提醒：${sequenceSeverityText(event.severity)}，${event.message || event.suggestion || '建议调整前后衔接'}`)
    })
    if (context.practice_execution_contract) {
      items.push('实操闭环：本页需要体现输入、操作、输出、证据或评分点之间的关系。')
    }
    if (context.speaker_script_available === false) {
      items.push('讲稿提醒：原页面缺少可沉淀讲稿，需要补充现场讲解支点。')
    }
    return items.slice(0, 6)
  })
  const repairPreviewTemplateChips = computed(() => {
    const context = repairPreviewContext.value || {}
    const contract = context.template_contract || {}
    return [
      pageRoleText(context.slide_role),
      contract.template_name || contract.name,
      contract.layout_pattern || contract.design_pattern,
      contract.visual_focus || contract.hero_visual,
      ...(Array.isArray(contract.required_blocks) ? contract.required_blocks.slice(0, 2) : []),
      ...(Array.isArray(contract.required_visual_blocks) ? contract.required_visual_blocks.slice(0, 2) : [])
    ].filter(Boolean).slice(0, 6)
  })
  const repairPreviewEvidenceHints = computed(() => {
    return (repairPreviewContext.value?.evidence_hints || []).slice(0, 3)
  })
  const repairPreviewNextAction = computed(() => repairPreviewAssessment.value?.next_action || '')
  const repairPreviewSeriesValidation = computed(() => repairCandidate.value?.series_validation || repairPreviewAssessment.value?.series_validation || null)
  const repairPreviewAcceptable = computed(() => repairPreviewAssessment.value?.accept_candidate !== false)
  const repairPreviewSeriesIssues = computed(() => {
    const validation = repairPreviewSeriesValidation.value || {}
    const roleLabels = {
      system_diagram: '系统主图',
      supporting_argument: '技术支撑说明',
      operation_stage_board: '实操闭环主区',
      evidence_wall: '证据墙主区',
      value_matrix: '价值矩阵主区',
      closing_signal: '收束主视觉'
    }
    const issues = []
    ;(validation.missing_expected_roles || []).forEach(role => {
      issues.push(`缺少关键块位：${roleLabels[role] || role}`)
    })
    ;(validation.internal_leaks || []).forEach(token => {
      issues.push(`仍暴露内部设计词：${token}`)
    })
    return issues
  })
  const repairPreviewSeriesSummary = computed(() => {
    const validation = repairPreviewSeriesValidation.value || {}
    if (!validation.page_series_type) return ''
    if (validation.pass) {
      return '页系契约检查通过，候选页已具备当前页面类型应有的关键块位和视觉语义。'
    }
    return validation.summary || '页系契约尚未兑现，这页仍然更像普通 HTML，而不是目标比赛页。'
  })
  const repairPreviewNextActionButton = computed(() => {
    const action = repairPreviewNextAction.value
    if (!action || action === 'accept_candidate') return ''
    return repairPreviewNextActionText(action)
  })
  const repairPreviewNextActionHint = computed(() => {
    const action = repairPreviewNextAction.value
    if (!action || action === 'accept_candidate') return ''
    const hints = {
      attach_evidence: '这次修复收益有限，当前页更缺证据，建议先补截图、政策来源或数据图；测试阶段可先用临时演示图。',
      structure_rebuild: '这次修复没有真正解决结构问题，建议直接走整页重做，不要继续在原 HTML 上补丁式修复。',
      retry_or_restore: '这次修复收益不足，建议先查看修复历史，必要时恢复较优版本，再决定下一步。',
      restore_best_repaired: '系统判断历史版本里可能有更优候选，优先恢复推荐版本会比继续空修更稳。',
      repair_html: '当前页仍属于 HTML 呈现问题，可以再尝试一次页面级修复。'
    }
    return hints[action] || ''
  })
  const repairPreviewDeltaText = computed(() => {
    if (repairPreviewAssessment.value?.summary) {
      return repairPreviewAssessment.value.summary
    }
    const before = repairPreviewBeforeIssues.value.length
    const after = repairPreviewAfterIssues.value.length
    if (!repairCandidate.value) return ''
    if (before && !after) return `已尝试消除 ${before} 个前置风险，候选页暂未发现硬性失败项。`
    if (before && after < before) return `已从 ${before} 个风险降到 ${after} 个风险，建议人工确认残留项。`
    if (!before && after) return `候选页仍有 ${after} 个风险，建议谨慎采用。`
    if (after >= before && before) return '候选页风险未明显下降，建议继续重试或改用补证据方式。'
    return '本次修复主要优化视觉层级、叙事表达和投屏可读性。'
  })

  return {
    repairHistoryItems,
    repairHistoryRecommendation,
    repairHistoryRecommendationActionText,
    repairPreviewContext,
    repairPreviewAssessment,
    repairPreviewAutoEscalation,
    repairPreviewAutoEscalationText,
    repairPreviewBeforeIssues,
    repairPreviewAfterIssues,
    repairPreviewContextItems,
    repairPreviewTemplateChips,
    repairPreviewEvidenceHints,
    repairPreviewSeriesValidation,
    repairPreviewAcceptable,
    repairPreviewSeriesIssues,
    repairPreviewSeriesSummary,
    repairPreviewNextAction,
    repairPreviewNextActionButton,
    repairPreviewNextActionHint,
    repairPreviewDeltaText
  }
}
