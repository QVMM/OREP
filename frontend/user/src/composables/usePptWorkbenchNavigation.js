export function usePptWorkbenchNavigation(options) {
  const {
    route,
    nextTick,
    request,
    ElMessage,
    activeTab,
    currentPageIndex,
    selectedScoringPoints,
    linkedStepId,
    pendingFocusIntent,
    lastDeliverabilityIntent,
    task,
    detail,
    optimizationQueue,
    qualityPages,
    qualityPriorityGroups,
    deliverabilityBlockerActions,
    judgeScoringCategories,
    practiceLoopItems,
    evidenceChainItems,
    roadshowStoryPhases,
    materialAssetType,
    materialDescription,
    queueIntentFocusMessage,
    qualityPriorityLevel,
    repairPage
  } = options

  function escapeSelectorValue(value) {
    if (typeof window !== 'undefined' && window.CSS?.escape) {
      return window.CSS.escape(String(value))
    }
    return String(value).replace(/["\\]/g, '\\$&')
  }

  function pulseFocusTarget(element) {
    if (!element) return
    element.classList.remove('focus-pulse')
    void element.offsetWidth
    element.classList.add('focus-pulse')
    window.setTimeout(() => {
      element.classList.remove('focus-pulse')
    }, 1800)
  }

  async function queueIntentFocus() {
    if (!pendingFocusIntent.value) return
    await nextTick()
    const intent = pendingFocusIntent.value
    let selector = ''
    if (intent.tab === 'quality' && intent.pageIndex) {
      selector = `.quality-page-card[data-quality-page="${escapeSelectorValue(intent.pageIndex)}"]`
    } else if (intent.tab === 'coverage' && intent.relatedPoints?.length) {
      selector = `.coverage-card[data-scoring-point="${escapeSelectorValue(intent.relatedPoints[0])}"], .missing-item[data-scoring-point="${escapeSelectorValue(intent.relatedPoints[0])}"]`
    } else if (intent.tab === 'practice' && intent.stepId) {
      selector = `.practice-loop-card[data-step-id="${escapeSelectorValue(intent.stepId)}"]`
    } else if (intent.tab === 'materials') {
      selector = '[data-focus-anchor="material-upload"]'
    } else if (intent.tab === 'roadshow') {
      selector = '.roadshow-story-map'
    } else if (intent.tab === 'health') {
      selector = '.health-hero'
    }
    const element = selector ? document.querySelector(selector) : null
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      pulseFocusTarget(element)
    }
    pendingFocusIntent.value = null
  }

  function applyInitialFocusFromRoute() {
    const query = route.query || {}
    const focusIntent = {
      tab: query.tab ? String(query.tab) : null,
      pageIndex: null,
      relatedPoints: [],
      stepId: query.step_id ? String(query.step_id) : '',
      title: query.intent ? String(query.intent) : ''
    }
    if (query.tab) {
      activeTab.value = String(query.tab)
    }
    if (query.page) {
      const page = Number(query.page)
      if (page > 0) {
        currentPageIndex.value = page
        focusIntent.pageIndex = page
      }
    }
    if (query.points) {
      focusIntent.relatedPoints = String(query.points)
        .split(',')
        .map(item => item.trim())
        .filter(Boolean)
      selectedScoringPoints.value = focusIntent.relatedPoints
    }
    if (query.step_id) {
      linkedStepId.value = String(query.step_id)
    }
    if (focusIntent.tab || focusIntent.pageIndex || focusIntent.relatedPoints.length || focusIntent.stepId) {
      pendingFocusIntent.value = focusIntent
      queueIntentFocus()
    }
  }

  function intentTaskTypes(intent = {}) {
    const tab = intent.tab || 'quality'
    const map = {
      quality: ['page_quality', 'pacing', 'quality'],
      materials: ['evidence'],
      coverage: ['scoring'],
      practice: ['practice'],
      roadshow: ['roadshow'],
      health: ['health', 'roadshow', 'quality']
    }
    return map[tab] || ['quality']
  }

  function queueTaskMatchesIntent(taskItem, intent = {}) {
    if (!taskItem || taskItem.status === 'done' || taskItem.status === 'skipped') return false

    const typeMatched = intentTaskTypes(intent).includes(taskItem.task_type)
    if (!typeMatched) return false

    const intentPages = [
      intent.pageIndex,
      ...(Array.isArray(intent.targetPages) ? intent.targetPages : [])
    ].map(Number).filter(Boolean)
    const taskPages = Array.isArray(taskItem.related_pages) ? taskItem.related_pages.map(Number).filter(Boolean) : []
    const pageMatched = !intentPages.length || taskPages.some(page => intentPages.includes(page))

    const intentPoints = Array.isArray(intent.relatedPoints) ? intent.relatedPoints.map(point => String(point)) : []
    const taskPoints = Array.isArray(taskItem.related_points) ? taskItem.related_points.map(point => String(point)) : []
    const pointMatched = !intentPoints.length || taskPoints.some(point => intentPoints.includes(point))

    return pageMatched && pointMatched
  }

  async function markOptimizationTasksInProgressByIntent(intent = {}, options = {}) {
    if (!task.value?.id) return 0
    const tasks = optimizationQueue.value?.tasks || []
    let matchedTasks = []

    if (intent.taskId) {
      matchedTasks = tasks.filter(item => item.task_id === intent.taskId && item.status !== 'done' && item.status !== 'skipped')
    } else {
      matchedTasks = tasks.filter(item => queueTaskMatchesIntent(item, intent))
    }

    if (!matchedTasks.length) return 0

    const note = options.note || `${intent.title || '当前优化项'} 已进入处理阶段`
    const results = await Promise.allSettled(matchedTasks.map(item => {
      return request.patch(`/api/ppt/task/${task.value.id}/optimization-queue/tasks/${item.task_id}/status`, {
        status: 'in_progress',
        note
      })
    }))
    const lastFulfilled = [...results].reverse().find(item => item.status === 'fulfilled')
    if (lastFulfilled) {
      detail.value.optimization_queue = lastFulfilled.value.data || lastFulfilled.value
    }
    return results.filter(item => item.status === 'fulfilled').length
  }

  async function openWorkbenchIntent(intent = {}, options = {}) {
    if (!intent) return
    const tab = intent.tab || 'health'
    if (Array.isArray(intent.relatedPoints)) {
      selectedScoringPoints.value = intent.relatedPoints.map(point => String(point))
    }
    if (intent.stepId) {
      linkedStepId.value = String(intent.stepId)
    }
    if (intent.pageIndex) {
      currentPageIndex.value = Number(intent.pageIndex)
    }
    activeTab.value = tab
    pendingFocusIntent.value = {
      tab,
      pageIndex: intent.pageIndex ? Number(intent.pageIndex) : null,
      relatedPoints: Array.isArray(intent.relatedPoints) ? intent.relatedPoints.map(point => String(point)) : [],
      targetPages: Array.isArray(intent.targetPages) ? intent.targetPages.map(Number).filter(Boolean) : [],
      stepId: intent.stepId || '',
      title: intent.title || ''
    }
    await markOptimizationTasksInProgressByIntent(intent, {
      note: options.note || `已从工作台进入处理：${intent.title || '当前项'}`
    })
    queueIntentFocus()
    if (options.message) {
      ElMessage.info(options.message)
    }
  }

  async function openDeliverabilityBlocker(item) {
    if (!item) return
    lastDeliverabilityIntent.value = {
      title: item.title || item.hint || '交付阻塞项',
      tab: item.tab || 'quality'
    }
    selectedScoringPoints.value = Array.isArray(item.relatedPoints) ? item.relatedPoints.map(point => String(point)) : []
    activeTab.value = item.tab || 'quality'
    const targetPage = item.pageIndex || item.targetPages?.[0] || null
    if (targetPage) {
      currentPageIndex.value = targetPage
    }
    pendingFocusIntent.value = {
      tab: item.tab || 'quality',
      pageIndex: targetPage,
      relatedPoints: Array.isArray(item.relatedPoints) ? item.relatedPoints.map(point => String(point)) : [],
      targetPages: Array.isArray(item.targetPages) ? item.targetPages.map(Number).filter(Boolean) : [],
      stepId: item.stepId || '',
      title: item.title || item.hint || ''
    }
    await markOptimizationTasksInProgressByIntent({
      tab: item.tab || 'quality',
      pageIndex: targetPage,
      targetPages: Array.isArray(item.targetPages) ? item.targetPages.map(Number).filter(Boolean) : [],
      relatedPoints: Array.isArray(item.relatedPoints) ? item.relatedPoints.map(point => String(point)) : [],
      title: item.title || item.hint || '交付阻塞项'
    }, {
      note: `已从交付阻塞项进入处理：${item.title || item.hint || '交付阻塞项'}`
    })
    queueIntentFocus()
    if (item.tab === 'quality') {
      const qualityPage = qualityPages.value.find(page => Number(page.page_index) === Number(targetPage))
        || qualityPages.value.find(page => qualityPriorityLevel(page) === 'P0')
      if (qualityPage && qualityPage.status !== 'pass') {
        await repairPage(qualityPage)
        return
      }
    }
    if (item.tab === 'materials' && item.stepId) {
      linkedStepId.value = item.stepId
      materialAssetType.value = 'screenshot'
      materialDescription.value = `对应实操步骤：${item.stepTitle || item.stepId}\n对应页面：${targetPage ? `第${targetPage}页` : '待绑定页面'}\n证明内容：`
    }
    if (item.tab === 'coverage' && item.relatedPoints?.length) {
      ElMessage.info(`已高亮 ${item.relatedPoints.slice(0, 3).join('、')} 等评分点，请优先补齐支撑页和证据`)
      return
    }
    ElMessage.info(item.hint || queueIntentFocusMessage || '已跳到对应处理区域')
  }

  async function handleReadinessAction(action) {
    if (!action) return
    const qualityP0Page = qualityPriorityGroups.value.find(group => group.level === 'P0')?.pages?.[0]
    const firstHighRiskCategory = judgeScoringCategories.value.find(category => category.high_risk_count > 0)
    const firstPracticeGap = practiceLoopItems.value.find(item => !item.complete)
    const firstEvidenceGap = evidenceChainItems.value.find(item => item.status !== 'ready')
    const firstMissingStory = roadshowStoryPhases.value.find(phase => phase.status !== 'ready')
    const firstBlocked = deliverabilityBlockerActions.value[0]

    if (action.key === 'deliverability' && firstBlocked) {
      await openDeliverabilityBlocker(firstBlocked)
      return
    }

    if (action.key === 'quality-p0' && qualityP0Page) {
      await openWorkbenchIntent({
        tab: 'quality',
        pageIndex: qualityP0Page.page_index,
        title: action.title,
        targetPages: [qualityP0Page.page_index]
      }, {
        message: '已定位到最优先的页面硬伤，请先处理该页。'
      })
      return
    }

    if (action.key === 'scoring-risk' && firstHighRiskCategory) {
      await openWorkbenchIntent({
        tab: 'coverage',
        relatedPoints: firstHighRiskCategory.points
          .filter(point => point.risk_level === 'high' || point.covered === false)
          .slice(0, 3)
          .map(point => point.point_name),
        title: action.title
      }, {
        message: '已高亮评分高风险项，请先补齐这些评分点的支撑页和证据。'
      })
      return
    }

    if (action.key === 'story-missing' && firstMissingStory) {
      await openWorkbenchIntent({
        tab: 'roadshow',
        targetPages: firstMissingStory.page_indices || [],
        title: action.title
      }, {
        message: '已切到路演结构页，请优先补齐缺失的故事线阶段。'
      })
      return
    }

    if (action.key === 'practice-loop' && firstPracticeGap) {
      await openWorkbenchIntent({
        tab: 'practice',
        stepId: firstPracticeGap.step_id,
        pageIndex: firstPracticeGap.target_pages?.[0] || null,
        targetPages: firstPracticeGap.target_pages || [],
        title: action.title
      }, {
        message: '已定位到需要补强的实操步骤，请先补闭环。'
      })
      return
    }

    if (action.key === 'evidence-chain' && firstEvidenceGap) {
      await openWorkbenchIntent({
        tab: 'materials',
        pageIndex: firstEvidenceGap.target_pages?.[0] || null,
        targetPages: firstEvidenceGap.target_pages || [],
        stepId: firstEvidenceGap.linked_step_id || '',
        title: action.title
      }, {
        message: '已切到素材证据区，请优先补当前缺口。'
      })
      return
    }

    await openWorkbenchIntent({
      tab: action.tab || 'health',
      title: action.title || action.hint || '下一步建议'
    })
  }

  async function handleFinalReviewItem(item) {
    if (!item) return
    if (item.key === 'deliverability' && deliverabilityBlockerActions.value.length) {
      await openDeliverabilityBlocker(deliverabilityBlockerActions.value[0])
      return
    }

    if (item.key === 'quality') {
      const firstPage = qualityPriorityGroups.value.find(group => group.level === 'P0')?.pages?.[0]
        || qualityPriorityGroups.value.find(group => group.pages.length)?.pages?.[0]
      await openWorkbenchIntent({
        tab: 'quality',
        pageIndex: firstPage?.page_index || null,
        targetPages: firstPage?.page_index ? [firstPage.page_index] : [],
        title: item.label
      }, {
        message: '已切到质量报告，请优先处理最关键的页面问题。'
      })
      return
    }

    if (item.key === 'scoring') {
      await handleReadinessAction({ key: 'scoring-risk', title: item.label, tab: 'coverage' })
      return
    }

    if (item.key === 'practice') {
      await handleReadinessAction({ key: 'practice-loop', title: item.label, tab: 'practice' })
      return
    }

    if (item.key === 'evidence') {
      await handleReadinessAction({ key: 'evidence-chain', title: item.label, tab: 'materials' })
      return
    }

    if (item.key === 'roadshow') {
      await handleReadinessAction({ key: 'story-missing', title: item.label, tab: 'roadshow' })
      return
    }

    await openWorkbenchIntent({
      tab: item.tab || 'health',
      title: item.label
    })
  }

  return {
    applyInitialFocusFromRoute,
    queueIntentFocus,
    markOptimizationTasksInProgressByIntent,
    openWorkbenchIntent,
    handleReadinessAction,
    handleFinalReviewItem,
    openDeliverabilityBlocker
  }
}
