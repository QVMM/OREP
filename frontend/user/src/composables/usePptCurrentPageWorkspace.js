import { computed } from 'vue'

export function usePptCurrentPageWorkspace(options) {
  const {
    currentPageIndex,
    previewScale,
    pageActionFeedback,
    htmlPages,
    outlinePages,
    qualityPages,
    htmlQualityGateItems,
    roadshowSequenceEvents,
    currentPageMaterialTask,
    materialAssets,
    policyEvidenceAssets,
    getPageLinkedAssets,
    pageHasEvidenceFailure,
    repairActionButtonText,
    resolvedRepairRouteReason,
    pageRoleText,
    failedCheckMessages,
    isPolicyOutlinePage
  } = options

  const currentHtml = computed(() => {
    return htmlPages.value.find(page => page.page_index === currentPageIndex.value)?.html_content || ''
  })

  const previewCanvasStyle = computed(() => ({
    transform: `scale(${previewScale.value})`
  }))

  const currentOutlinePage = computed(() => {
    return outlinePages.value[currentPageIndex.value - 1]
      || htmlPages.value.find(page => page.page_index === currentPageIndex.value)
      || {}
  })

  const currentPageQuality = computed(() => {
    return qualityPages.value.find(page => page.page_index === currentPageIndex.value) || null
  })

  const currentPageActionFeedback = computed(() => {
    return pageActionFeedback.value?.[currentPageIndex.value] || null
  })

  const currentPageLinkedAssets = computed(() => {
    return getPageLinkedAssets(currentPageIndex.value)
  })

  const currentPageRecommendedAssets = computed(() => {
    return (materialAssets.value || []).filter(asset => {
      const analysis = asset.analysis_result || {}
      const confirmed = (analysis.confirmed_page_indices || []).map(Number)
      if (confirmed.includes(Number(currentPageIndex.value))) return false
      return (analysis.recommended_page_bindings || []).some(binding =>
        Number(binding.page_index) === Number(currentPageIndex.value)
      )
    }).slice(0, 3)
  })

  const currentPagePrimaryAction = computed(() => {
    const qualityPage = currentPageQuality.value
    const materialTask = currentPageMaterialTask.value
    const visualProblems = new Set(qualityPage?.visual_problems || [])
    const hasContractVisualRisk = [...visualProblems].some(type =>
      ['contract_mismatch', 'series_language_missing', 'visual_role_not_realized'].includes(type)
    )
    if (qualityPage?.auto_fix_suspended) {
      return {
        mode: 'history',
        label: '查看修复历史',
        hint: '这页已多次修复未收敛，先看历史版本或恢复较优版本更稳。'
      }
    }
    if (qualityPage && hasContractVisualRisk) {
      return {
        mode: 'contract',
        label: '重做契约页',
        hint: '这页已经不像它声明的页面类型或页系样张，优先按页面契约整页重做。'
      }
    }
    if (qualityPage && pageHasEvidenceFailure(qualityPage)) {
      return {
        mode: 'material',
        label: '给当前页补图',
        hint: materialTask?.summary || '这页当前更缺截图、结果图或政策来源，先补素材比继续空修更有效。'
      }
    }
    if (qualityPage && qualityPage.status !== 'pass') {
      return {
        mode: 'repair',
        label: repairActionButtonText(qualityPage),
        hint: resolvedRepairRouteReason(qualityPage) || '这页还有质量问题，先按系统推荐动作处理。'
      }
    }
    if (materialTask && materialTask.status !== 'ready') {
      return {
        mode: 'material',
        label: '预填本页补图',
        hint: materialTask.summary || '这页还有待补素材，先把对应截图或数据图传上来。'
      }
    }
    return {
      mode: 'quality',
      label: '查看质量结论',
      hint: '当前页没有明显硬伤，先查看质检结论和讲稿支点即可。'
    }
  })

  const currentPageScript = computed(() => {
    const page = currentOutlinePage.value || {}
    return page.speaker_notes || page.speech_script || page.notes || page.script || ''
  })

  const currentPageGoal = computed(() => {
    const page = currentOutlinePage.value || {}
    return page.page_goal || page.core_argument || page.summary || page.content || '建议补充本页要证明的评分点和讲解目标。'
  })

  const currentPageFailedMessages = computed(() => failedCheckMessages(currentPageQuality.value))

  const currentPageGateItems = computed(() => {
    return htmlQualityGateItems.value.filter(item => Number(item.page_index) === Number(currentPageIndex.value))
  })

  const currentPageSequenceEvents = computed(() => {
    return roadshowSequenceEvents.value.filter(event => {
      if (Number(event.page_index) === Number(currentPageIndex.value)) return true
      return Array.isArray(event.related_pages) && event.related_pages.map(Number).includes(Number(currentPageIndex.value))
    })
  })

  const currentPageTemplateContract = computed(() => {
    const page = currentOutlinePage.value || {}
    return page.page_template_contract || page.template_contract || page.visual_contract || null
  })

  const currentPageTemplateChips = computed(() => {
    const page = currentOutlinePage.value || {}
    const contract = currentPageTemplateContract.value || {}
    return [
      pageRoleText(page.slide_role || page.page_role),
      contract.template_name || contract.name,
      contract.layout_pattern || contract.design_pattern,
      contract.visual_focus || contract.hero_visual,
      ...(Array.isArray(contract.required_blocks) ? contract.required_blocks.slice(0, 2) : []),
      ...(Array.isArray(contract.required_visual_blocks) ? contract.required_visual_blocks.slice(0, 2) : [])
    ].filter(Boolean).slice(0, 6)
  })

  const currentPracticeContract = computed(() => {
    const page = currentOutlinePage.value || {}
    return page.practice_execution_contract || page.operation_contract || null
  })

  const currentPracticeRows = computed(() => {
    const contract = currentPracticeContract.value || {}
    const rows = [
      { label: '输入', value: contract.input || contract.input_data || contract.before_state },
      { label: '操作', value: contract.operation || contract.key_operation || contract.action },
      { label: '输出', value: contract.output || contract.output_result || contract.after_state },
      { label: '证据', value: contract.evidence_slot || contract.evidence || contract.screenshot_slot },
      { label: '评分点', value: contract.scoring_point || contract.scoring_observation || contract.score_point }
    ]
    return rows.filter(row => row.value).slice(0, 5)
  })

  const currentPageEvidenceHints = computed(() => {
    const page = currentOutlinePage.value || {}
    const hints = []
    const boundAssets = currentPageLinkedAssets.value
    const currentQuality = currentPageQuality.value
    const evidenceStillMissing = pageHasEvidenceFailure(currentQuality || {})

    if (!evidenceStillMissing) return []
    if (boundAssets.length) {
      hints.push(`本页已绑定 ${boundAssets.length} 份素材，但系统仍检测到证据缺口，建议刷新质检后确认是否还缺特定类型素材。`)
    }
    if (!boundAssets.length && evidenceStillMissing && isPolicyOutlinePage(page) && policyEvidenceAssets.value.length === 0) {
      hints.push('政策页缺少官方截图或政策文件，建议上传官网截图并写清官方链接。')
    }
    if (!boundAssets.length && evidenceStillMissing && currentPracticeRows.value.length) {
      hints.push('实操页尚未绑定截图/设备照片/数据图，建议补充操作证据；测试阶段可先用临时演示图。')
    }
    return hints.slice(0, 3)
  })

  return {
    currentHtml,
    previewCanvasStyle,
    currentOutlinePage,
    currentPageQuality,
    currentPageActionFeedback,
    currentPagePrimaryAction,
    currentPageScript,
    currentPageGoal,
    currentPageFailedMessages,
    currentPageGateItems,
    currentPageSequenceEvents,
    currentPageTemplateChips,
    currentPracticeRows,
    currentPageEvidenceHints,
    currentPageLinkedAssets,
    currentPageRecommendedAssets
  }
}
