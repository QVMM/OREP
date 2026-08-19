/**
 * PPT编辑器状态管理
 * 对接现有的 AI PPT 生成系统
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import request from '../utils/request'
import { useAuthStore } from './auth'

export const usePptStore = defineStore('ppt', () => {
  const authStore = useAuthStore()

  // ==================== 状态 ====================

  // 当前步骤：0=选择领域, 1=填写问卷, 2=AI生成中, 3=预览编辑, 4=生成PPT
  const currentStep = ref(0)

  // 领域选择 - 与 round1_structurize.md 保持一致
  const domains = [
    { id: '智能制造', name: '智能制造', icon: ' ' },
    { id: '智慧医疗', name: '智慧医疗', icon: ' ' },
    { id: '智慧农业', name: '智慧农业', icon: ' ' },
    { id: '智慧教育', name: '智慧教育', icon: ' ' },
    { id: '金融科技', name: '金融科技', icon: ' ' },
    { id: '新能源', name: '新能源', icon: ' ' },
    { id: '其他', name: '其他领域', icon: ' ' },
  ]
  const selectedDomain = ref('')

  // 问卷相关
  const formSections = ref([])
  const formData = ref({})

  // 任务相关
  const taskId = ref(null)
  const taskStatus = ref('')
  const taskProgress = ref(0)
  const currentStepText = ref('')
  const taskErrorMsg = ref('')

  // 大纲数据（AI 生成的内容）
  const outlineData = ref(null)
  const scoringStats = ref(null)

  // 主题选择
  const themes = ref([])
  const selectedTheme = ref('deep-blue-tech')
  const stylePresets = ref([])
  const stylePreviews = ref([])
  const selectedVisualStyle = ref('')

  // 编辑状态
  const editingPages = ref([])  // 可编辑的页面数据

  // 生成状态
  const generating = ref(false)

  // ==================== Round 1-4 Pipeline 状态 ====================

  // 完整的 pipeline 数据
  const pipelineData = ref(null)

  // 轮询定时器
  let pollTimer = null

  // 问卷数据缓存
  const cachedQuestionnaire = ref(null)

  // 轮询状态
  const isPolling = ref(false)

  // 生成前资料完整度报告
  const readinessReport = ref(null)

  // 后端连通性
  const pptBackendAvailable = ref(true)

  // ==================== 计算属性 ====================

  const canProceed = computed(() => {
    if (currentStep.value === 0) return !!selectedDomain.value
    return true
  })

  const totalPages = computed(() => {
    return outlineData.value?.pages?.length || 0
  })

  // ==================== Round 1-4 Pipeline 计算属性 ====================

  /**
   * 从 pipelineData 中提取结构化数据（优先从 outlineData.meta 或 enhanced_data 提取）
   */
  const structuredData = computed(() => {
    if (!pipelineData.value) return null
    return pipelineData.value.enhanced_data || outlineData.value?.meta || null
  })

  /**
   * 从 pipelineData 中提取充实后的页面数据
   */
  const enrichedPages = computed(() => {
    if (!pipelineData.value) return []
    return normalizeHtmlPages(pipelineData.value.enriched_pages || pipelineData.value.enrichedPages || [])
  })

  // ==================== 状态持久化 ====================

const STORAGE_KEY = 'ppt_editor_state'

function saveState() {
  try {
    const state = {
      taskId: taskId.value,
      taskStatus: taskStatus.value,
      currentStep: currentStep.value,
      selectedDomain: selectedDomain.value,
      formData: formData.value,
      cachedQuestionnaire: cachedQuestionnaire.value,
      outlineData: outlineData.value,
      pipelineData: pipelineData.value,
      editingPages: editingPages.value,
      selectedVisualStyle: selectedVisualStyle.value,
      savedAt: Date.now()
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch (e) {
    console.error('保存状态失败:', e)
  }
}

function loadState() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return false
    const state = JSON.parse(saved)

    // 超过 24 小时的状态不恢复
    if (Date.now() - state.savedAt > 24 * 60 * 60 * 1000) {
      localStorage.removeItem(STORAGE_KEY)
      return false
    }

    // 检查任务状态是否有效（失败、取消的不恢复）
    if (state.taskStatus === 'failed' || state.taskStatus === 'cancelled') {
      // console.log('loadState: 任务已失败或取消，清除状态')
      localStorage.removeItem(STORAGE_KEY)
      return false
    }

    // 检查大纲是否有效
    const outlinePages = state.outlineData?.pages
    const hasValidOutline = outlinePages && outlinePages.length > 0

    // 如果状态是 outline_ready 但大纲无效，清除状态
    if (state.taskStatus === 'outline_ready' && !hasValidOutline) {
      // console.log('loadState: outline_ready但大纲无效，清除状态')
      localStorage.removeItem(STORAGE_KEY)
      return false
    }

    // 如果是 generating 且已有大纲但大纲为空，说明任务卡住了
    if (state.taskStatus === 'generating' && state.outlineData && !hasValidOutline) {
      // console.log('loadState: generating但大纲为空，清除状态')
      localStorage.removeItem(STORAGE_KEY)
      return false
    }

    taskId.value = state.taskId || null
    taskStatus.value = state.taskStatus || ''
    currentStep.value = state.currentStep ?? 0
    selectedDomain.value = state.selectedDomain || ''
    formData.value = state.formData || {}
    cachedQuestionnaire.value = state.cachedQuestionnaire || null
    outlineData.value = state.outlineData || null
    pipelineData.value = state.pipelineData || null
    editingPages.value = state.editingPages || []
    selectedVisualStyle.value = state.selectedVisualStyle || ''
    return true
  } catch (e) {
    console.error('加载状态失败:', e)
    return false
  }
}

function clearState() {
  localStorage.removeItem(STORAGE_KEY)
}

function isTaskNotFoundError(error) {
  return error?.response?.status === 404
}

function isBackendUnavailableError(error) {
  const status = error?.response?.status
  return !status || status === 502 || status === 503 || status === 504
}

async function checkPptBackendAvailability(timeout = 2500) {
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
  const timer = setTimeout(() => controller?.abort(), timeout)

  try {
    const response = await fetch('/api/ppt/health', {
      method: 'GET',
      cache: 'no-store',
      signal: controller?.signal
    })
    pptBackendAvailable.value = response.ok
    return response.ok
  } catch (e) {
    pptBackendAvailable.value = false
    return false
  } finally {
    clearTimeout(timer)
  }
}

async function validateActiveTask() {
  if (!taskId.value) {
    return { ok: false, reason: 'no_task' }
  }

  const backendReady = await checkPptBackendAvailability()
  if (!backendReady) {
    return { ok: false, reason: 'backend_unavailable' }
  }

  try {
    const response = await fetch(`/api/ppt/task/${taskId.value}`, {
      method: 'GET',
      cache: 'no-store'
    })

    if (response.status === 404) {
      return { ok: false, reason: 'not_found' }
    }

    if (!response.ok) {
      if ([502, 503, 504].includes(response.status)) {
        pptBackendAvailable.value = false
        return { ok: false, reason: 'backend_unavailable' }
      }
      let payload = null
      try {
        payload = await response.json()
      } catch {
        payload = null
      }
      return { ok: false, reason: 'request_failed', error: payload }
    }

    const payload = await response.json()
    const task = payload?.data || payload
    pptBackendAvailable.value = true
    return { ok: true, task }
  } catch (e) {
    pptBackendAvailable.value = false
    return { ok: false, reason: 'backend_unavailable' }
  }
}

// ==================== 历史任务恢复 ====================

async function restoreLatestTask() {
  const userId = authStore.user?.id
  if (!userId) return false

  try {
    const res = await request.get(`/api/ppt/user/${userId}/latest-task`)
    const task = res?.data || res
    if (!task) return false

    // console.log('服务器获取的任务:', task)

    // 检查任务是否有效（失败、取消的任务不恢复）
    if (task.status === 'failed' || task.status === 'cancelled') {
      // console.log('任务已失败或取消，不恢复')
      return false
    }

    // 检查大纲是否有效
    const outlinePages = task.outline_json?.pages
    const hasValidOutline = outlinePages && outlinePages.length > 0
    // console.log('大纲有效性:', { hasValidOutline, pagesCount: outlinePages?.length })

    // 如果是 outline_ready 状态但大纲无效，不恢复
    if (task.status === 'outline_ready' && !hasValidOutline) {
      // console.log('大纲无效（pages为空），不恢复')
      return false
    }

    // 如果是 generating 状态但已经有 outline_json 且 pages 为空，说明任务卡住了，不恢复
    if (task.status === 'generating' && task.outline_json && !hasValidOutline) {
      // console.log('任务卡住（generating但大纲为空），不恢复')
      return false
    }

    taskId.value = task.id
    taskStatus.value = task.status
    taskProgress.value = task.progress || 0
    currentStepText.value = task.current_step || ''
    taskErrorMsg.value = task.error_msg || ''
    outlineData.value = task.outline_json || null
    pipelineData.value = task
      scoringStats.value = task.scoring_stats || null
      selectedVisualStyle.value = task.theme || selectedVisualStyle.value

    // 根据任务状态恢复步骤
    if (task.status === 'outline_ready' && hasValidOutline) {
      currentStep.value = 1 // 大纲确认（只有大纲有效时）
    } else if (task.status === 'generating' || task.status === 'rendering') {
      currentStep.value = 1 // 生成中，显示大纲生成进度
    } else if (task.status === 'completed') {
      currentStep.value = 3 // 预览
    } else {
      currentStep.value = 0 // 其他情况从第一步开始
    }

    saveState()
    return true
  } catch (e) {
    // 404 表示没有历史任务，这是正常情况
    if (e.response?.status === 404) {
      // console.log('没有历史任务')
      return false
    }
    // 其他错误才输出日志
    console.warn('恢复任务失败:', e.message || e)
    return false
  }
}

// ==================== 动作 ====================

  /**
   * 初始化
   */
  async function initialize() {
    await loadThemes()
  }

  /**
   * 加载主题列表
   */
  async function loadThemes() {
    try {
      const res = await request.get('/api/ppt/themes')
      themes.value = res.data || []
    } catch (e) {
      console.error('加载主题失败:', e)
    }
  }

  async function loadStylePresets() {
    const res = await request.get('/api/ppt/style-presets')
    stylePresets.value = res.data || res || []
    return stylePresets.value
  }

  async function generateStylePreviews() {
    if (!taskId.value) return []
    const validation = await validateActiveTask()
    if (!validation.ok) {
      if (validation.reason === 'not_found') {
        resetPipeline()
      }
      stylePreviews.value = []
      return []
    }
    const res = await request.post(`/api/ppt/task/${taskId.value}/style-preview`, {})
    stylePreviews.value = res.data || res || []
    if (!selectedVisualStyle.value && stylePreviews.value.length) {
      selectedVisualStyle.value = stylePreviews.value[0].style_id
      await selectVisualStyle(selectedVisualStyle.value)
    }
    saveState()
    return stylePreviews.value
  }

  async function selectVisualStyle(styleId) {
    if (!taskId.value || !styleId) return null
    const res = await request.patch(`/api/ppt/task/${taskId.value}/visual-style`, {
      style_id: styleId
    })
    selectedVisualStyle.value = styleId
    saveState()
    return res.data || res
  }

  async function applyOutlineStorylineGuard() {
    if (!taskId.value) return null
    const res = await request.post(`/api/ppt/task/${taskId.value}/outline/storyline-guard`)
    const result = res.data || res
    if (result?.outline) {
      outlineData.value = result.outline
      if (!pipelineData.value) {
        pipelineData.value = {}
      }
      pipelineData.value.outline_json = result.outline
      editingPages.value = result.outline.pages || []
      saveState()
    }
    return result
  }

  /**
   * 加载表单配置
   */
  async function loadForm(domain) {
    try {
      const res = await request.get(`/api/ppt/forms/${domain}`)
      const formConfig = res.data?.form_schema
      if (formConfig?.sections) {
        formSections.value = formConfig.sections
        // 初始化表单数据
        const data = {}
        formConfig.sections.forEach(section => {
          section.fields.forEach(field => {
            if (field.default !== undefined) {
              data[field.id] = field.default
            }
          })
        })
        formData.value = data
      }
    } catch (e) {
      // 如果没有表单配置，使用默认问卷
      formSections.value = getDefaultSections()
      formData.value = {}
    }
  }

  /**
   * 提交问卷并创建任务
   */
  async function submitAndCreateTask() {
    const userId = authStore.user?.id
    const tenantId = authStore.user?.tenantId || 1

    // 提交问卷
    const questionnaireRes = await request.post('/api/ppt/questionnaire/submit', {
      user_id: userId,
      tenant_id: tenantId,
      domain: selectedDomain.value,
      project_name: formData.value.project_name || '项目路演',
      team_name: formData.value.team_name || '',
      responses: formData.value
    })

    const questionnaireId = questionnaireRes.data?.questionnaire_id

    // 创建任务
    const taskRes = await request.post('/api/ppt/task/create', {
      questionnaire_id: questionnaireId,
      user_id: userId,
      tenant_id: tenantId,
      theme: selectedTheme.value
    })

    taskId.value = taskRes.data?.task_id
    taskStatus.value = 'generating'
    currentStep.value = 2
  }

  /**
   * 查询任务状态
   */
  async function pollStatus() {
    if (!taskId.value) return null

    try {
      const res = await request.get(`/api/ppt/task/${taskId.value}`)
      const task = res.data

      taskStatus.value = task.status
      taskProgress.value = task.progress || 0
      currentStepText.value = task.current_step || ''
      taskErrorMsg.value = task.error_msg || ''

      if (task.outline_json) {
        outlineData.value = task.outline_json
      }

      if (task.scoring_stats) {
        scoringStats.value = task.scoring_stats
      }

      return task
    } catch (e) {
      console.error('轮询状态失败:', e)
      return null
    }
  }

  /**
   * 确认大纲并生成PPT
   */
  async function confirmAndGenerate() {
    if (!taskId.value) return

    // 如果用户修改了大纲，传递修改后的版本
    const outlineToSend = editingPages.value.length > 0
      ? { ...outlineData.value, pages: editingPages.value }
      : null

    await request.post(`/api/ppt/task/${taskId.value}/confirm`, {
      outline_json: outlineToSend,
      confirmed: true
    })

    taskStatus.value = 'rendering'
    currentStep.value = 4
    taskProgress.value = 60
    currentStepText.value = '正在渲染PPT...'
  }

  /**
   * 更新页面内容
   */
  function updatePageContent(pageIndex, data) {
    if (!outlineData.value?.pages) return

    // 复制当前大纲
    if (editingPages.value.length === 0) {
      editingPages.value = JSON.parse(JSON.stringify(outlineData.value.pages))
    }

    // 更新指定页面
    const page = editingPages.value.find(p => p.page_index === pageIndex)
    if (page) {
      page.data = { ...page.data, ...data }
    }
    saveState()
  }

  /**
   * 更新大纲页面（支持编辑标题和内容要点）
   * @param {number} pageIndex - 页面索引
   * @param {Object} updates - 要更新的字段 { title, content, section, ... }
   */
  function updateOutlinePage(pageIndex, updates) {
    if (!outlineData.value?.pages) return

    // 确保 editingPages 有数据
    if (editingPages.value.length === 0) {
      editingPages.value = JSON.parse(JSON.stringify(outlineData.value.pages))
    }

    // 找到并更新指定页面
    const pageIdx = editingPages.value.findIndex((p, index) => {
      return p.page_index === pageIndex || p.page_index === pageIndex + 1 || index === pageIndex
    })
    if (pageIdx !== -1) {
      editingPages.value[pageIdx] = {
        ...editingPages.value[pageIdx],
        ...updates,
        // 保留原始 page_index
        page_index: pageIndex
      }
      saveState()
    }
  }

  /**
   * 重新排序大纲页面
   * @param {number} fromIndex - 原始索引
   * @param {number} toIndex - 目标索引
   */
  function reorderOutlinePages(fromIndex, toIndex) {
    if (!outlineData.value?.pages) return

    // 确保 editingPages 有数据
    if (editingPages.value.length === 0) {
      editingPages.value = JSON.parse(JSON.stringify(outlineData.value.pages))
    }

    // 移动元素
    const [movedItem] = editingPages.value.splice(fromIndex, 1)
    editingPages.value.splice(toIndex, 0, movedItem)

    // 更新 page_index
    editingPages.value.forEach((page, idx) => {
      page.page_index = idx
    })

    saveState()
  }

  /**
   * 获取HTML页面内容
   * @returns {Promise<Array>} - 返回HTML页面数组
   */
  async function fetchHtmlPages() {
    if (!taskId.value) return []

    try {
      const res = await request.get(`/api/ppt/task/${taskId.value}/html-pages`)
      const rawPages = Array.isArray(res) ? res : (res.data || [])
      const pages = normalizeHtmlPages(rawPages)

      // 更新 enrichedPages 数据
      if (pages.length > 0) {
        if (!pipelineData.value) {
          pipelineData.value = {}
        }
        pipelineData.value.enriched_pages = pages
        saveState()
      }

      return pages
    } catch (e) {
      console.error('获取HTML页面失败:', e)
      return []
    }
  }

  async function fetchTaskDetail() {
    if (!taskId.value) return null
    try {
      const res = await request.get(`/api/ppt/task/${taskId.value}`)
      const task = res.data || res
      if (task) {
        pipelineData.value = {
          ...(pipelineData.value || {}),
          ...task
        }
        if (task.outline_json) {
          outlineData.value = task.outline_json
        }
        taskStatus.value = task.status || taskStatus.value
        taskProgress.value = task.progress || taskProgress.value
        currentStepText.value = task.current_step || currentStepText.value
        taskErrorMsg.value = task.error_msg || taskErrorMsg.value
      }
      return task
    } catch (e) {
      console.error('获取任务详情失败:', e)
      return null
    }
  }

  async function refreshDeliverability() {
    const task = await fetchTaskDetail()
    return task?.deliverability || pipelineData.value?.deliverability || null
  }

  /**
   * 更换主题
   */
  async function changeTheme(theme) {
    selectedTheme.value = theme
    // 如果已有大纲，需要重新生成
    if (taskId.value && outlineData.value) {
      // TODO: 调用后端重新生成
    }
  }

  /**
   * 下载PPT
   */
  async function downloadPPT() {
    if (!taskId.value) return

    const token = authStore.token
    const response = await fetch(`/api/ppt/task/${taskId.value}/download`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error('下载失败')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ppt_${taskId.value}.pptx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  /**
   * 重置状态
   */
  function reset() {
    currentStep.value = 0
    selectedDomain.value = ''
    formData.value = {}
    formSections.value = []
    taskId.value = null
    taskStatus.value = ''
    taskProgress.value = 0
    outlineData.value = null
    scoringStats.value = null
    editingPages.value = []
  }

  /**
   * 进入预览编辑步骤
   */
  function goToPreview() {
    currentStep.value = 3
  }

  // ==================== Round 1-4 Pipeline 方法 ====================

  /**
   * 启动 Round 1-4 Pipeline
   * @param {Object} questionnaireData - 问卷数据（包含 project_name, team_name 等）
   * @returns {Promise<Object>} - 返回任务信息
   */
  async function startPipeline(questionnaireData) {
    const userId = authStore.user?.id
    const tenantId = authStore.user?.tenantId || 1

    // 缓存问卷数据
    cachedQuestionnaire.value = questionnaireData

    try {
      // 1. 提交问卷
      const questionnaireRes = await request.post('/api/ppt/v2/questionnaire/submit', {
        user_id: userId,
        tenant_id: tenantId,
        project_name: questionnaireData.project_name || questionnaireData.projectName || '项目路演',
        team_name: questionnaireData.team_name || questionnaireData.teamName || '',
        industry: questionnaireData.industry || 'tech',
        responses: questionnaireData
      })

      const questionnaireId = questionnaireRes.data?.questionnaire_id

      // 2. 创建任务
      const taskRes = await request.post('/api/ppt/v2/task/create', {
        questionnaire_id: questionnaireId,
        user_id: userId,
        tenant_id: tenantId,
        industry: questionnaireData.industry || 'tech'
      })

      const taskIdFromRes = taskRes.data?.task_id || taskRes.data?.id
      taskId.value = taskIdFromRes
      taskStatus.value = 'generating'

      // 3. 获取初始任务数据
      if (taskIdFromRes) {
        const taskRes = await request.get(`/api/ppt/task/${taskIdFromRes}`)
        pipelineData.value = taskRes.data
      }

      return { task_id: taskIdFromRes, success: true }
    } catch (e) {
      console.error('启动 Pipeline 失败:', e)
      throw e
    }
  }

  /**
   * 生成前资料完整度评估
   * @param {Object} questionnaireData - 问卷数据
   * @returns {Promise<Object>} - 完整度报告
   */
  async function evaluateQuestionnaireReadiness(questionnaireData) {
    const res = await request.post('/api/ppt/v2/questionnaire/readiness', {
      project_name: questionnaireData.project_name || questionnaireData.projectName || '',
      team_name: questionnaireData.team_name || questionnaireData.teamName || '',
      industry: questionnaireData.industry || 'tech',
      responses: questionnaireData
    })
    const report = res.data || res
    readinessReport.value = report
    return report
  }

  /**
   * 轮询 Pipeline 状态
   * @returns {Promise<Object>} - 返回状态信息
   */
  async function pollPipelineStatus() {
    if (!taskId.value) return null

    try {
      const res = await request.get(`/api/ppt/task/${taskId.value}`)
      // res 已经是 response.data (经过拦截器处理)
      const task = res.data || res

      // 调试日志
      // console.log('[PPT] 轮询返回:', { status: task.status, progress: task.progress, outlineExists: !!task.outline_json, pagesCount: task.outline_json?.pages?.length })

      // 更新状态
      taskStatus.value = task.status
      taskProgress.value = task.progress || 0
      currentStepText.value = task.current_step || ''
      taskErrorMsg.value = task.error_msg || ''

      // 更新 pipelineData
      pipelineData.value = task

      // 更新 outlineData（只要 outline_json 存在就更新，不依赖 status）
      if (task.outline_json) {
        outlineData.value = task.outline_json
        // console.log('[PPT] outlineData 已更新, 页数:', task.outline_json?.pages?.length)
      }

      // 更新评分统计
      if (task.scoring_stats) {
        scoringStats.value = task.scoring_stats
      }

      return {
        status: task.status,
        progress: task.progress || 0,
        current_step: task.current_step || '',
        repair_substep: task.repair_substep || '',
        error_msg: task.error_msg || '',
        deliverability: task.deliverability || null,
        preview_recommendations: task.preview_recommendations || []
      }
    } catch (e) {
      console.error('轮询状态失败:', e)
      return null
    }
  }

  /**
   * 重新触发大纲生成
   * @returns {Promise<Object>}
   */
  async function retryOutlineGeneration() {
    if (!taskId.value) {
      throw new Error('当前没有可重试的任务')
    }

    const res = await request.post(`/api/ppt/task/${taskId.value}/outline/retry`)
    const result = res.data || res

    taskStatus.value = result.status || 'generating'
    taskProgress.value = result.progress || 5
    currentStepText.value = result.current_step || result.message || '正在重新生成大纲...'
    taskErrorMsg.value = ''

    if (result.outline_json) {
      outlineData.value = result.outline_json
    } else {
      outlineData.value = null
    }

    saveState()
    return result
  }

  /**
   * 重新触发 Round 3 + Round 4 内容与 HTML 生成
   * @returns {Promise<Object>}
   */
  async function retryContentGeneration() {
    if (!taskId.value) {
      throw new Error('当前没有可重试的任务')
    }

    const outlineToSend = editingPages.value.length > 0
      ? { ...outlineData.value, pages: editingPages.value }
      : (outlineData.value || null)

    const res = await request.post(`/api/ppt/task/${taskId.value}/confirm`, {
      outline_json: outlineToSend,
      confirmed: true
    })
    const result = res.data || res

    taskStatus.value = result.status || 'generating'
    taskProgress.value = result.progress || 40
    currentStepText.value = result.current_step || result.message || '正在重新生成内容与 HTML...'
    taskErrorMsg.value = ''
    saveState()
    return result
  }

  /**
   * 确认大纲并开始 Round 3 + Round 4 生成
   * @returns {Promise<void>}
   */
  async function confirmOutline() {
    if (!taskId.value) {
      throw new Error('没有活动任务')
    }

    try {
      // 如果用户修改了大纲，传递修改后的版本
      const outlineToSend = editingPages.value.length > 0
        ? { ...outlineData.value, pages: editingPages.value }
        : null

      await request.post(`/api/ppt/task/${taskId.value}/confirm`, {
        outline_json: outlineToSend,
        confirmed: true
      })

      taskStatus.value = 'rendering'
      taskProgress.value = 60
      currentStepText.value = '正在生成 PPT...'
    } catch (e) {
      console.error('确认大纲失败:', e)
      throw e
    }
  }

  /**
   * 下载 PPT
   * @returns {Promise<void>}
   */
  async function downloadPpt() {
    if (!taskId.value) return

    const token = authStore.token
    const response = await fetch(`/api/ppt/task/${taskId.value}/download`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error('下载失败')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ppt_${taskId.value}.pptx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  }

  /**
   * 取消任务
   * @returns {Promise<boolean>}
   */
  async function cancelTask() {
    if (!taskId.value) return true

    try {
      await request.post(`/api/ppt/task/${taskId.value}/cancel`)

      // 更新本地状态
      taskStatus.value = 'cancelled'
      resetPipeline()

      return true
    } catch (e) {
      // 404 表示任务不存在（可能已经被删除），也算取消成功
      if (e.response?.status === 404) {
        resetPipeline()
        return true
      }
      throw e
    }
  }

  /**
   * 删除任务
   * @returns {Promise<boolean>}
   */
  async function deleteTask() {
    if (!taskId.value) {
      resetPipeline()
      return { success: true, remoteDeleted: false, reason: 'no_task' }
    }

    const backendReady = await checkPptBackendAvailability()
    if (!backendReady) {
      resetPipeline()
      return { success: true, remoteDeleted: false, reason: 'backend_unavailable' }
    }

    try {
      await request.delete(`/api/ppt/task/${taskId.value}`)
      resetPipeline()
      return { success: true, remoteDeleted: true }
    } catch (e) {
      if (isTaskNotFoundError(e)) {
        resetPipeline()
        return { success: true, remoteDeleted: false, reason: 'not_found' }
      }
      if (isBackendUnavailableError(e)) {
        resetPipeline()
        return { success: true, remoteDeleted: false, reason: 'backend_unavailable' }
      }
      throw e
    }
  }

  /**
   * 重置 Pipeline 状态
   */
  function resetPipeline() {
    // 清除轮询定时器
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }

    // 清除本地存储
    localStorage.removeItem(STORAGE_KEY)

    // 重置基本状态
    currentStep.value = 0
    selectedDomain.value = ''
    formData.value = {}
    formSections.value = []
    taskId.value = null
    taskStatus.value = ''
    taskProgress.value = 0
    currentStepText.value = ''
    taskErrorMsg.value = ''
    outlineData.value = null
    scoringStats.value = null
    editingPages.value = []
    generating.value = false
    stylePreviews.value = []
    selectedVisualStyle.value = ''
    pptBackendAvailable.value = true

    // 重置 Pipeline 状态
    pipelineData.value = null
    cachedQuestionnaire.value = null
    isPolling.value = false
  }

  // ==================== 辅助函数 ====================

  function normalizeHtmlPages(pages) {
    if (!Array.isArray(pages)) return []

    const outlinePages = outlineData.value?.pages || []

    return pages
      .map((page, index) => {
        const outlinePage = outlinePages[index] || {}

        if (typeof page === 'string') {
          return {
            page_index: index + 1,
            title: outlinePage.title || outlinePage.section || `第 ${index + 1} 页`,
            section: outlinePage.section || outlinePage.phase || '',
            html_content: page
          }
        }

        if (page && typeof page === 'object') {
          return {
            ...outlinePage,
            ...page,
            page_index: page.page_index ?? outlinePage.page_index ?? index + 1,
            title: page.title || outlinePage.title || outlinePage.section || `第 ${index + 1} 页`,
            section: page.section || outlinePage.section || outlinePage.phase || '',
            html_content: page.html_content || page.html || page.content || ''
          }
        }

        return null
      })
      .filter(page => page?.html_content)
  }

  // 默认表单配置 - 与 round1_structurize.md 保持一致，并补充测试JSON中的重要字段
  function getDefaultSections() {
    return [
      {
        id: 'basic_info',
        title: '一、项目基本信息',
        description: '填写项目的核心信息',
        fields: [
          { id: 'project_name', label: '项目名称', type: 'text', required: true, placeholder: '如：智耘—智慧农业病虫害监测与决策平台' },
          { id: 'team_name', label: '团队名称', type: 'text', required: true, placeholder: '如：田野智联团队' },
          { id: 'school_name', label: '学校名称', type: 'text', required: true, placeholder: '如：华东职业技术学院' },
          { id: 'competition', label: '参赛赛项', type: 'text', required: true, placeholder: '如：人工智能赛项、物联网技术应用' },
          { id: 'industry', label: '所属行业/领域', type: 'select', options: ['智能制造', '智慧医疗', '智慧农业', '智慧教育', '金融科技', '新能源', '其他'], required: true },
          { id: 'one_liner', label: '一句话描述', type: 'text', required: true, placeholder: '用XX技术，解决XX问题，实现XX效果' }
        ]
      },
      {
        id: 'background',
        title: '二、项目背景与意义',
        description: '描述项目的背景、社会需求和战略意义',
        fields: [
          { id: 'strategic_alignment', label: '战略对接', type: 'textarea', placeholder: '描述项目与国家政策、行业规划的对接点\n如：对接《十四五数字乡村发展战略》...', rows: 3 },
          { id: 'social_need', label: '社会需求', type: 'textarea', required: true, placeholder: '描述当前社会面临的痛点和需求\n如：农村劳动力老龄化严重，作物病虫害频发...', rows: 4 },
          { id: 'project_significance', label: '项目意义', type: 'textarea', placeholder: '描述项目的价值和意义\n如：可帮助农民降低农药使用量30%，提高产量15%...', rows: 3 }
        ]
      },
      {
        id: 'problem_solution',
        title: '三、问题与解决方案',
        description: '描述项目要解决的问题和解决方案',
        fields: [
          { id: 'core_problem', label: '核心问题', type: 'textarea', required: true, placeholder: '描述项目要解决的核心问题，如：大田病虫害发现滞后、人工巡田效率低，错过最佳防治窗口' },
          { id: 'user_pain_points', label: '用户痛点', type: 'textarea', required: true, placeholder: '列出目标用户的核心痛点，每行一个\n如：监测困难：大田环境复杂，人工巡田费时费力\n病虫害发现晚：错过最佳防治窗口', rows: 4 },
          { id: 'scene_description', label: '使用场景描述', type: 'textarea', required: true, placeholder: '描述谁+在什么场景+遇到什么+用方案后得到什么结果', rows: 4 },
          { id: 'solution', label: '解决方案概述', type: 'textarea', required: true, placeholder: '描述您的解决方案，包含核心技术架构\n如：基于物联网+大数据+AI的智慧农业管理平台...', rows: 4 },
          { id: 'key_difference', label: '核心突破/方案差异', type: 'textarea', required: true, placeholder: '描述本项目相较传统方式或同类方案的关键突破点，如：弱网环境下仍可稳定采集、低成本覆盖小农户场景' },
          { id: 'target_users', label: '目标用户群体', type: 'text', required: true, placeholder: '如：县域农业服务中心、合作社与规模种植户' }
        ]
      },
      {
        id: 'market',
        title: '四、行业依据与方案对照',
        description: '填写行业数据、应用依据和传统方式/同类方案对照',
        fields: [
          { id: 'industry_trend', label: '行业趋势', type: 'textarea', placeholder: '描述行业现状和发展趋势\n如：数字乡村、农业现代化政策持续推动智慧农业落地，物联网采集与AI诊断需求快速增长...', rows: 3 },
          { id: 'market_size', label: '行业/应用价值数据', type: 'text', placeholder: '如：试点区域覆盖面积约4.5万亩，单季可减少人工巡检成本30%' },
          { id: 'market_research', label: '行业/应用数据补充', type: 'textarea', placeholder: '描述可核实的行业数据、覆盖范围或试点依据\n如：某地水稻主产区约120万亩，合作社数字化管理覆盖率不足15%...', rows: 3 },
          { id: 'competitor_analysis', label: '传统方式/同类方案对照', type: 'textarea', placeholder: '说明传统方式或同类方案的局限，以及本项目的差异化价值\n如：人工巡田周期长、病虫害发现滞后；现有方案偏重硬件，缺少平台化数据闭环...', rows: 4 }
        ]
      },
      {
        id: 'tech_innovation',
        title: '五、技术与创新',
        description: '填写技术方案和创新点',
        fields: [
          { id: 'tech_direction', label: '技术方向', type: 'text', required: true, placeholder: '如：AI视觉、物联网、大数据' },
          { id: 'tech_stack', label: '技术栈', type: 'text', required: true, placeholder: '如：Python, PyTorch, OpenCV, STM32, MQTT（逗号分隔）' },
          { id: 'tech_highlights', label: '技术创新点', type: 'textarea', required: true, placeholder: '列出项目的核心创新点，每行一个\n如：视觉+振动双源融合\n模型轻量化压缩\n边缘实时推理' },
          { id: 'key_metrics', label: '关键指标', type: 'text', placeholder: '如：故障检测准确率96.8%，预警提前量72小时' },
          { id: 'innovation_value', label: '创新价值', type: 'textarea', placeholder: '描述技术创新的价值\n如：技术价值：在弱网环境下实现稳定感知与识别\n应用价值：可服务县域农业服务中心、合作社和示范基地...', rows: 3 },
          { id: 'patent_status', label: '知识产权', type: 'textarea', placeholder: '描述专利、软著等知识产权情况\n如：已申请发明专利1项，获得软著3项...', rows: 2 },
          { id: 'biggest_challenge', label: '最大技术挑战', type: 'textarea', placeholder: '描述您遇到的最大技术难题及如何解决的', rows: 3 }
        ]
      },
      {
        id: 'achievements',
        title: '六、成果与数据',
        description: '填写项目成果和关键数据',
        fields: [
          { id: 'stage', label: '项目阶段', type: 'select', options: ['概念', '原型', '开发中', '已上线'], required: true },
          { id: 'achievements', label: '获奖/成果', type: 'textarea', placeholder: '列出项目获奖情况或重要成果\n如：省级职业技能大赛二等奖（2025）' },
          { id: 'key_data', label: '关键数据', type: 'textarea', placeholder: '列出项目的关键数据指标\n如：用户量10万+\n日活用户5000+\n准确率98%' },
          { id: 'user_feedback', label: '用户反馈', type: 'textarea', placeholder: '描述用户使用反馈和满意度\n如：用户满意度89%（来自3个试点基地50位农户反馈）...', rows: 3 },
          { id: 'application_scenarios', label: '应用场景', type: 'textarea', placeholder: '描述项目的应用场景和落地情况\n如：水稻种植区：全国约4.5亿亩\n已落地：安徽省3个县级示范点...', rows: 3 }
        ]
      },
      {
        id: 'business',
        title: '七、应用价值与推广路径',
        description: '填写应用价值、社会价值和后续推广路径',
        fields: [
          { id: 'business_model', label: '推广/成果转化路径', type: 'textarea', placeholder: '描述项目如何试点落地、校企合作、成果转化或持续推广\n如：先在2个示范基地试点，再通过校企合作推广到县域合作社...', rows: 3 },
          { id: 'economic_value', label: '经济价值', type: 'textarea', placeholder: '描述项目的经济价值\n如：病虫害识别后农药使用量下降20%，单亩综合成本降低80元，合作社管理效率提升30%...', rows: 3 },
          { id: 'social_value', label: '社会价值', type: 'textarea', placeholder: '描述项目的社会价值\n如：推动农业数字化转型，提升生产效率20%\n减少农药化肥使用，助力绿色发展...', rows: 3 },
          { id: 'promotion_plan', label: '推广计划', type: 'textarea', placeholder: '描述项目的推广策略\n如：先在示范基地试点，再通过校地合作推广到县域服务中心和合作社\n两年内形成区域化复制路径...', rows: 3 }
        ]
      },
      {
        id: 'team',
        title: '八、团队信息',
        description: '填写团队成员信息',
        fields: [
          { id: 'team_size', label: '团队人数', type: 'range', min: 1, max: 10, default: 4 },
          { id: 'team_members', label: '团队成员及分工', type: 'textarea', required: true, placeholder: '描述团队成员的角色和分工\n如：项目经理1人：负责项目规划、部门对接\n前端开发1人：负责Vue3界面开发...', rows: 4 },
          { id: 'member_backgrounds', label: '成员背景', type: 'textarea', placeholder: '描述团队成员的专业背景\n如：成员A：农学专业背景，熟悉农业场景\n成员B：计算机专业，精通Vue3...', rows: 3 }
        ]
      },
      {
        id: 'output_config',
        title: '九、输出配置',
        description: '配置PPT生成参数',
        fields: [
          {
            id: 'theme',
            label: '视觉风格',
            type: 'select',
            options: [
              { label: '深色科技', value: 'dark_tech' },
              { label: '清爽蓝白', value: 'fresh_blue' },
              { label: '浅色专业', value: 'business' }
            ],
            default: 'dark_tech'
          }
        ]
      }
    ]
  }

  // ==================== 导出 ====================

  return {
    // 状态
    currentStep,
    domains,
    selectedDomain,
    formSections,
    formData,
    taskId,
    taskStatus,
    taskProgress,
    currentStepText,
    taskErrorMsg,
    outlineData,
    scoringStats,
    themes,
    selectedTheme,
    stylePresets,
    stylePreviews,
    selectedVisualStyle,
    editingPages,
    generating,

    // Pipeline 状态
    pipelineData,
    isPolling,
    readinessReport,
    pptBackendAvailable,

    // 计算属性
    canProceed,
    totalPages,
    structuredData,
    enrichedPages,

    // 动作
    initialize,
    loadThemes,
    loadStylePresets,
    generateStylePreviews,
    selectVisualStyle,
    applyOutlineStorylineGuard,
    loadForm,
    submitAndCreateTask,
    pollStatus,
    confirmAndGenerate,
    updatePageContent,
    changeTheme,
    downloadPPT,
    reset,
    goToPreview,

    // Round 1-4 Pipeline 方法
    startPipeline,
    evaluateQuestionnaireReadiness,
    pollPipelineStatus,
    retryOutlineGeneration,
    retryContentGeneration,
    confirmOutline,
    downloadPpt,
    cancelTask,
    deleteTask,
    resetPipeline,

    // 大纲编辑方法
    updateOutlinePage,
    reorderOutlinePages,
    fetchHtmlPages,
    fetchTaskDetail,
    refreshDeliverability,
    validateActiveTask,

    // 状态恢复方法
    restoreLatestTask,
    saveState,
    loadState
  }
})
