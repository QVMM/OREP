import { computed } from 'vue'

function blockerTabLabel(tab) {
  const map = {
    quality: '页面质量',
    materials: '素材证据',
    coverage: '评分覆盖',
    health: '总报告',
    practice: '实操演示',
    roadshow: '路演结构'
  }
  return map[tab] || '质量报告'
}

function blockerActionabilityScore(item = {}) {
  let score = 0
  if (Number(item.pageIndex || 0) > 0) score += 40
  if (Array.isArray(item.targetPages) && item.targetPages.length) score += 30
  if (item.stepId) score += 20
  if (Array.isArray(item.relatedPoints) && item.relatedPoints.length) score += 10
  if (item.tab === 'quality') score += 8
  if (item.tab === 'html') score += 6
  if (item.tab === 'coverage') score += 5
  if (item.tab === 'practice') score += 4
  if (item.tab === 'materials') score += 3
  if (item.tab === 'health') score -= 5
  return score
}

export function usePptDownloadReadiness(options) {
  const {
    detail,
    qualityPages,
    pageIssueProfiles,
    qualityReport,
    optimizationQueue,
    scoringCoverage,
    missingRequiredScoringPoints,
    scoringCoverageTargetPages,
    qualityPriorityGroups,
    p0TargetPages,
    targetPagesText
  } = options

  const deliverabilityVerdict = computed(() => {
    const backend = detail.value?.deliverability
    if (backend?.status) {
      const blockerDetails = Array.isArray(backend.blocker_details) ? backend.blocker_details : []
      const blockerTitles = blockerDetails
        .map(item => item?.title)
        .filter(Boolean)
      const computedShortHint = backend.status === 'warning' && blockerTitles.length
        ? `当前版可下，建议先处理：${blockerTitles.slice(0, 2).join('、')}`
        : (backend.short_hint || backend.shortHint || '待复查')
      const computedSummary = backend.status === 'warning' && blockerTitles.length
        ? `页面当前已具备下载基础，但仍建议继续处理：${blockerTitles.join('；')}。`
        : (backend.summary || '请结合质量报告继续处理风险页。')
      return {
        status: backend.status,
        label: backend.label || '待判断',
        shortHint: computedShortHint,
        summary: computedSummary,
        blockers: backend.blockers || [],
        blockerDetails
      }
    }

    const taskStatus = detail.value?.task?.status || ''
    if (taskStatus === 'completed') {
      return {
        status: 'warning',
        label: '交付状态待刷新',
        shortHint: '正在同步最新结论',
        summary: '当前任务已完成，但后端交付状态尚未回传，请稍后刷新。若持续存在，请重新打开本页。',
        blockers: [],
        blockerDetails: []
      }
    }

    if (['rendering', 'generating', 'outline_ready'].includes(taskStatus)) {
      return {
        status: 'warning',
        label: '生成中',
        shortHint: '等待后端完成评估',
        summary: '当前任务仍在生成或确认阶段，交付门禁将在生成完成后自动评估。',
        blockers: [],
        blockerDetails: []
      }
    }

    return {
      status: 'warning',
      label: '可预览但需补强',
      shortHint: '先补证据与弱页',
      summary: '页面已具备预览基础，但仍建议继续补素材证据、弱评分项和关键页面表达后再正式交付。',
      blockers: [],
      blockerDetails: []
    }
  })

  const deliverabilityBlockerActions = computed(() => {
    const details = Array.isArray(deliverabilityVerdict.value.blockerDetails)
      ? deliverabilityVerdict.value.blockerDetails
      : []
    if (details.length) {
      return details.map((item, index) => ({
        key: item.type || `detail-${index}`,
        priority: item.priority || 'P1',
        tab: item.tab || 'quality',
        tabLabel: blockerTabLabel(item.tab),
        title: item.title || '需要处理的交付阻塞项',
        hint: item.hint || '请先处理当前阻塞项',
        pageIndex: Number(item.page_index || 0) || null,
        pageTitle: item.page_title || '',
        relatedPoints: Array.isArray(item.related_points) ? item.related_points : [],
        targetPages: Array.isArray(item.target_pages) ? item.target_pages.map(Number).filter(Boolean) : [],
        stepId: item.step_id || '',
        stepTitle: item.step_title || ''
      }))
        .sort((a, b) => blockerActionabilityScore(b) - blockerActionabilityScore(a))
        .slice(0, 6)
    }

    const blockers = Array.isArray(deliverabilityVerdict.value.blockers)
      ? deliverabilityVerdict.value.blockers
      : []
    return blockers.map((message, index) => {
      const text = `${message || ''}`.toLowerCase()
      if (text.includes('占位') || text.includes('跨行业') || text.includes('p0') || text.includes('基础质量')) {
        return {
          key: `quality-${index}`,
          priority: 'P0',
          tab: 'quality',
          tabLabel: '页面质量',
          title: message,
          hint: '进入质量报告，优先处理终稿占位词、跨行业污染和页面级硬伤。'
        }
      }
      if (text.includes('证据')) {
        return {
          key: `materials-${index}`,
          priority: 'P1',
          tab: 'materials',
          tabLabel: '素材证据',
          title: message,
          hint: '进入素材证据区，补齐实操截图、政策截图或数据图。'
        }
      }
      if (text.includes('覆盖率') || text.includes('评分点')) {
        return {
          key: `coverage-${index}`,
          priority: 'P1',
          tab: 'coverage',
          tabLabel: '评分覆盖',
          title: message,
          hint: '进入评分点总控，补齐必备评分点支撑页和证据。'
        }
      }
      if (text.includes('体检') || text.includes('ready')) {
        return {
          key: `health-${index}`,
          priority: 'P1',
          tab: 'health',
          tabLabel: '总报告',
          title: message,
          hint: '进入总报告，按体检建议继续补结构、页面和讲稿。'
        }
      }
      return {
        key: `general-${index}`,
        priority: 'P1',
        tab: 'quality',
        tabLabel: '质量报告',
        title: message,
        hint: '先从质量报告开始处理当前阻塞项。'
      }
    }).slice(0, 6)
  })

  const warningSuggestionCount = computed(() => {
    if (deliverabilityVerdict.value.status !== 'warning') return 0
    return deliverabilityBlockerActions.value.length
  })

  const CONTRACT_RISK_LABELS = {
    contract_mismatch: '页面不像它声明的页面类型',
    series_language_missing: '缺少页系样张的家族视觉语言',
    visual_role_not_realized: '主视觉没有承担应有职责'
  }

  function normalizeContractProblemTypes(profile) {
    const problems = Array.isArray(profile?.visual_problems) ? profile.visual_problems : []
    return problems
      .map(problem => {
        if (typeof problem === 'string') return problem
        return problem?.type || ''
      })
      .filter(Boolean)
  }

  const contractRiskPages = computed(() => {
    const profiles = Array.isArray(pageIssueProfiles?.value) ? pageIssueProfiles.value : []
    return profiles.filter(profile => {
      const problemTypes = normalizeContractProblemTypes(profile)
      return problemTypes.some(problem => ['contract_mismatch', 'series_language_missing', 'visual_role_not_realized'].includes(problem))
    })
  })

  const contractRiskTargetPages = computed(() => (
    contractRiskPages.value
      .map(profile => Number(profile.page_index || 0))
      .filter(Boolean)
      .slice(0, 6)
  ))

  const contractRiskPriorityLabels = computed(() => {
    const labels = []
    contractRiskPages.value.forEach(profile => {
      normalizeContractProblemTypes(profile).forEach(type => {
        const label = CONTRACT_RISK_LABELS[type]
        if (label && !labels.includes(label)) labels.push(label)
      })
    })
    return labels.slice(0, 3)
  })

  const contractRiskRejectedPages = computed(() => {
    return contractRiskPages.value
      .filter(profile => {
        const rejection = profile?.last_contract_rejection || {}
        return Boolean(
          rejection.reason
          || (Array.isArray(rejection.missing_expected_roles) && rejection.missing_expected_roles.length)
          || (Array.isArray(rejection.internal_leaks) && rejection.internal_leaks.length)
        )
      })
      .slice(0, 4)
  })

  const downloadChecklist = computed(() => {
    const placeholderPages = qualityPages.value
      .filter(page => (page.failed_checks || []).includes('placeholder_content'))
      .map(page => page.page_index)
    const failPages = qualityPages.value
      .filter(page => page.status === 'fail')
      .map(page => page.page_index)
    const practiceTemplateBlocker = deliverabilityBlockerActions.value.find(item => item.key === 'practice_template_risk' || item.key === 'detail-practice_template_risk' || item.title?.includes('模板化过重'))
    const requiredCoverage = Number.parseFloat(`${scoringCoverage.value?.required_coverage_rate || 0}`) || 0
    const p0Count = Number(optimizationQueue.value?.p0_count || 0)
    const practiceTemplateCount = practiceTemplateBlocker?.targetPages?.length || (practiceTemplateBlocker ? 1 : 0)
    const qualityOk = qualityReport.value?.overall_status !== 'fail'
    const contractRiskCount = contractRiskPages.value.length
    const contractRiskRejectedCount = contractRiskRejectedPages.value.length

    return [
      {
        key: 'quality-status',
        title: '基础质量不能是 fail',
        done: qualityOk,
        progressText: qualityOk ? '基础质量 1/1' : '基础质量 0/1',
        progressPercent: qualityOk ? 100 : 0,
        detail: !qualityOk
          ? `当前仍为 fail，需先处理失败页：${failPages.length ? targetPagesText(failPages.slice(0, 6)) : '请进入质量报告查看失败页'}。`
          : '当前基础质量已不再阻止下载。',
        actionable: !qualityOk,
        tab: 'quality',
        pageIndex: failPages[0] || null
      },
      {
        key: 'placeholder',
        title: '终稿占位词必须清零',
        done: placeholderPages.length === 0,
        progressText: `占位词 ${placeholderPages.length}/0`,
        progressPercent: placeholderPages.length === 0 ? 100 : 0,
        detail: placeholderPages.length
          ? `当前还有 ${placeholderPages.length} 页含待补充/截图位等占位词：${targetPagesText(placeholderPages.slice(0, 6))}。`
          : '当前未检测到终稿占位词。',
        actionable: placeholderPages.length > 0,
        tab: 'quality',
        pageIndex: placeholderPages[0] || null,
        targetPages: placeholderPages.slice(0, 6),
        actionText: '一键清占位词',
        actionHint: `共剩 ${placeholderPages.length} 页`
      },
      {
        key: 'practice-template',
        title: '实操关键页不能模板化',
        done: !practiceTemplateBlocker,
        progressText: `模板化页 ${practiceTemplateCount}/0`,
        progressPercent: !practiceTemplateBlocker ? 100 : 0,
        detail: practiceTemplateBlocker
          ? `当前仍有实操关键页模板化过重，重点页：${targetPagesText(practiceTemplateBlocker.targetPages || (practiceTemplateBlocker.pageIndex ? [practiceTemplateBlocker.pageIndex] : []))}。`
          : '当前未发现会阻止下载的实操模板页。',
        actionable: Boolean(practiceTemplateBlocker),
        tab: practiceTemplateBlocker?.tab || 'quality',
        pageIndex: practiceTemplateBlocker?.pageIndex || null,
        targetPages: practiceTemplateBlocker?.targetPages || (practiceTemplateBlocker?.pageIndex ? [practiceTemplateBlocker.pageIndex] : []),
        actionText: '一键重做模板页',
        actionHint: `共剩 ${practiceTemplateCount} 页`
      },
      {
        key: 'page-contract',
        title: '页面设计契约需要兑现',
        done: contractRiskCount === 0,
        progressText: `契约风险 ${contractRiskCount}/0`,
        progressPercent: contractRiskCount === 0 ? 100 : 0,
        detail: contractRiskCount === 0
          ? '当前未发现页面契约、页系语言或主视觉职责失配问题。'
          : `当前仍有 ${contractRiskCount} 页看起来不像它声明的页面类型或视觉职责，重点页：${targetPagesText(contractRiskTargetPages.value)}。${contractRiskRejectedCount ? ` 其中 ${contractRiskRejectedCount} 页最近一次候选页仍未通过比赛页契约验收。` : ''}`,
        actionable: contractRiskCount > 0,
        tab: 'quality',
        pageIndex: contractRiskTargetPages.value[0] || null,
        targetPages: contractRiskTargetPages.value,
        relatedPoints: contractRiskPriorityLabels.value,
        actionText: '一键重做契约页',
        actionHint: `共剩 ${contractRiskCount} 页；优先修“页面不像该页 / 缺页系语言 / 主视觉没落地”${contractRiskRejectedCount ? `；其中 ${contractRiskRejectedCount} 页最近一次候选页未过契约门` : ''}`
      },
      {
        key: 'scoring-coverage',
        title: '比赛必备评分点覆盖建议达到 85% 以上',
        done: requiredCoverage >= 85,
        progressText: `评分覆盖 ${Math.round(requiredCoverage)}/85`,
        progressPercent: Math.max(0, Math.min(100, Math.round(requiredCoverage / 85 * 100))),
        detail: requiredCoverage >= 85
          ? `当前比赛必备评分点覆盖率 ${scoringCoverage.value?.required_coverage_rate || '0%'}，已达到下载建议线。`
          : `当前比赛必备评分点覆盖率仅 ${scoringCoverage.value?.required_coverage_rate || '0%'}，建议先提升到 85% 以上。${missingRequiredScoringPoints.value.length ? ` 当前优先补强的比赛评分证据：${missingRequiredScoringPoints.value.slice(0, 3).join('、')}。` : ''}`,
        actionable: requiredCoverage < 85,
        tab: 'coverage',
        pageIndex: null,
        relatedPoints: missingRequiredScoringPoints.value.slice(0, 3),
        targetPages: scoringCoverageTargetPages.value,
        actionText: '一键补比赛评分证据',
        actionHint: `共缺 ${missingRequiredScoringPoints.value.length || 0} 个比赛必备评分点`
      },
      {
        key: 'p0',
        title: 'P0 阻塞项需要清零',
        done: p0Count === 0,
        progressText: `P0 阻塞 ${p0Count}/0`,
        progressPercent: p0Count === 0 ? 100 : 0,
        detail: p0Count === 0
          ? '当前没有待处理的 P0 阻塞项。'
          : `当前仍有 ${p0Count} 个 P0 任务未处理，下载门禁不会放开。${p0TargetPages.value.length ? ` 建议先处理：${targetPagesText(p0TargetPages.value.slice(0, 4))}。` : ''}`,
        actionable: p0Count > 0,
        tab: deliverabilityBlockerActions.value[0]?.tab || 'quality',
        pageIndex: deliverabilityBlockerActions.value[0]?.pageIndex || null,
        relatedPoints: deliverabilityBlockerActions.value[0]?.relatedPoints || [],
        targetPages: p0TargetPages.value.length ? p0TargetPages.value : (deliverabilityBlockerActions.value[0]?.targetPages || []),
        actionText: '一键处理 P0',
        actionHint: `共剩 ${p0Count} 个 P0 任务`
      }
    ]
  })

  const downloadReadinessSummary = computed(() => {
    const pending = downloadChecklist.value.filter(item => !item.done)
    if (!pending.length) {
      if (deliverabilityVerdict.value.status === 'warning' && warningSuggestionCount.value > 0) {
        return `当前关键下载条件已经满足，可以先下载当前版本；仍建议继续处理 ${warningSuggestionCount.value} 项补强建议。`
      }
      return '当前关键下载条件已经满足，可以直接导出。'
    }
    return `当前还差 ${pending.length} 项：${pending.map(item => item.title).join('；')}。`
  })

  function buildDownloadChecklistSnapshot(items = []) {
    return items.map(item => ({
      key: item.key,
      title: item.title,
      done: Boolean(item.done),
      progressText: item.progressText || '',
      detail: item.detail || ''
    }))
  }

  function compareDownloadChecklistProgress(previous = [], next = []) {
    const prevMap = new Map(previous.map(item => [item.key, item]))
    const nextMap = new Map(next.map(item => [item.key, item]))
    const resolved = []
    const improved = []

    for (const [key, nextItem] of nextMap.entries()) {
      const prevItem = prevMap.get(key)
      if (!prevItem) continue
      if (!prevItem.done && nextItem.done) {
        resolved.push(nextItem.title)
        continue
      }
      if (!nextItem.done && prevItem.progressText !== nextItem.progressText) {
        improved.push(`${nextItem.title}：${prevItem.progressText} → ${nextItem.progressText}`)
      }
    }

    return { resolved, improved }
  }

  function buildChecklistProgressFeedback(delta, after = [], intentLabel = '') {
    const resolved = delta?.resolved || []
    const improved = delta?.improved || []
    if (!resolved.length && !improved.length) return null

    const remaining = after.filter(item => !item.done).length
    const nextPendingItem = after.find(item => !item.done && item.actionable)
      || after.find(item => !item.done)
    const focusPrefix = intentLabel ? `本次${intentLabel}` : '本次处理'

    if (resolved.length) {
      const remainingCount = after.filter(item => !item.done).length
      return {
        type: 'success',
        title: '下载条件已有进展',
        summary: `${focusPrefix}已解除 ${resolved.length} 条下载条件${remaining ? `，当前还剩 ${remaining} 条未满足` : '，当前关键下载条件已全部满足'}。`,
        points: [
          `已解除：${resolved.slice(0, 2).join('、')}`,
          improved[0] || ''
        ].filter(Boolean),
        allowDownload: remainingCount === 0,
        nextPendingItem: remainingCount > 0 ? nextPendingItem : null
      }
    }

    return {
      type: 'info',
      title: '下载条件进度已更新',
      summary: `${focusPrefix}已推动下载条件进度变化，但还没有新增解除项。`,
      points: improved.slice(0, 2),
      allowDownload: after.filter(item => !item.done).length === 0,
      nextPendingItem: remaining > 0 ? nextPendingItem : null
    }
  }

  return {
    deliverabilityVerdict,
    deliverabilityBlockerActions,
    contractRiskPages,
    contractRiskTargetPages,
    downloadChecklist,
    downloadReadinessSummary,
    warningSuggestionCount,
    buildDownloadChecklistSnapshot,
    compareDownloadChecklistProgress,
    buildChecklistProgressFeedback
  }
}
