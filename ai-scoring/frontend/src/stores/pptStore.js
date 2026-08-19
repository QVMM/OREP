import { defineStore } from 'pinia'
import { ref } from 'vue'
import { pptApi } from '@/api/pptApi'

const DEFAULT_USER_ID = 1
const DEFAULT_TENANT_ID = 1
const DEFAULT_INDUSTRY = 'tech'

function assertSuccess(response, fallbackMessage) {
  if (!response?.success) {
    throw new Error(response?.message || response?.detail || fallbackMessage)
  }
  return response.data
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function getSlidesFromOutline(outlineData) {
  if (!outlineData) return []
  if (Array.isArray(outlineData)) return outlineData
  return outlineData.pages || outlineData.outline || outlineData.slides || []
}

function normalizeSlide(slide, index) {
  return {
    slide: slide.slide || slide.page_index || slide.page || index + 1,
    title: slide.title || slide.section || `第 ${index + 1} 页`,
    type: slide.type || slide.slide_type || slide.layout || slide.slide_role || 'content',
    content: slide.content || slide.ppt_text || slide.summary || slide.description || '',
    bullet_points: slide.bullet_points || slide.key_points || slide.points || [],
    notes: slide.notes || slide.speech_script || ''
  }
}

function normalizeOutline(taskStatus) {
  const outlineJson = taskStatus?.outline_json || taskStatus || {}
  const slides = getSlidesFromOutline(outlineJson).map(normalizeSlide)

  return {
    ...outlineJson,
    task_id: taskStatus?.task_id || taskStatus?.id || outlineJson.task_id,
    status: taskStatus?.status || outlineJson.status,
    progress: taskStatus?.progress ?? outlineJson.progress,
    current_step: taskStatus?.current_step || outlineJson.current_step,
    project_name: taskStatus?.project_name || outlineJson.project_name,
    team_name: taskStatus?.team_name || outlineJson.team_name,
    outline: slides,
    slides
  }
}

export const usePPTStore = defineStore('ppt', () => {
  const taskId = ref(null)
  const questionnaireId = ref(null)
  const currentPhase = ref(1)
  const currentRound = ref(1)
  const outline = ref(null)
  const content = ref(null)
  const preview = ref(null)
  const currentPPT = ref(null)
  const pptList = ref([])
  const loading = ref(false)
  const error = ref(null)
  const taskStatus = ref(null)
  const downloadUrl = ref('')

  const surveyData = ref({
    project_name: '',
    team_name: '',
    team_size: 0,
    core_problem: '',
    target_market: '',
    solution_description: '',
    business_model: '',
    competitive_advantage: '',
    funding_stage: '',
    key_metrics: '',
    domain: DEFAULT_INDUSTRY,
    industry: DEFAULT_INDUSTRY
  })

  function setCurrentPPT(ppt) {
    currentPPT.value = ppt
  }

  function setPptList(list) {
    pptList.value = list
  }

  function setLoading(isLoading) {
    loading.value = isLoading
  }

  function setError(err) {
    error.value = err
  }

  function setCurrentPhase(phase) {
    currentPhase.value = phase
  }

  function setCurrentRound(round) {
    currentRound.value = round
  }

  function setTaskId(id) {
    taskId.value = id
  }

  function setSurveyData(data) {
    surveyData.value = { ...surveyData.value, ...data }
  }

  function setOutline(outlineData) {
    const mergedOutline = { ...outlineData }
    if (Array.isArray(outlineData?.pages) && Array.isArray(outlineData?.outline)) {
      mergedOutline.pages = outlineData.pages.map((page, index) => ({
        ...page,
        ...outlineData.outline[index]
      }))
    }

    outline.value = normalizeOutline({
      ...mergedOutline,
      task_id: taskId.value || mergedOutline?.task_id
    })
  }

  function setContent(contentData) {
    content.value = contentData
  }

  function setPreview(previewData) {
    preview.value = previewData
  }

  function updateSlide(slideIndex, slideData) {
    if (currentPPT.value && currentPPT.value.slides) {
      currentPPT.value.slides[slideIndex] = {
        ...currentPPT.value.slides[slideIndex],
        ...slideData
      }
    }
  }

  function addSlide(slideData) {
    if (currentPPT.value) {
      currentPPT.value.slides.push(slideData)
    }
  }

  function removeSlide(slideIndex) {
    if (currentPPT.value && currentPPT.value.slides) {
      currentPPT.value.slides.splice(slideIndex, 1)
    }
  }

  async function pollTaskUntil(doneStatuses, options = {}) {
    const {
      interval = 3000,
      timeout = 10 * 60 * 1000,
      onProgress
    } = options

    const startedAt = Date.now()
    while (Date.now() - startedAt < timeout) {
      const response = await pptApi.getTaskStatus(taskId.value)
      const statusData = assertSuccess(response, '获取任务状态失败')
      taskStatus.value = statusData
      onProgress?.(statusData)

      if (doneStatuses.includes(statusData.status)) {
        return statusData
      }

      if (['failed', 'cancelled'].includes(statusData.status)) {
        throw new Error(statusData.error_msg || `任务已${statusData.status}`)
      }

      await sleep(interval)
    }

    throw new Error('任务等待超时，请稍后在任务列表中查看结果')
  }

  async function generateOutline(taskData) {
    loading.value = true
    error.value = null
    preview.value = null
    content.value = null

    try {
      setSurveyData(taskData)
      const userId = taskData.user_id || DEFAULT_USER_ID
      const tenantId = taskData.tenant_id || DEFAULT_TENANT_ID
      const industry = taskData.industry || taskData.domain || DEFAULT_INDUSTRY

      const questionnaireResponse = await pptApi.submitQuestionnaire({
        user_id: userId,
        tenant_id: tenantId,
        domain: industry,
        project_name: taskData.project_name,
        team_name: taskData.team_name || '',
        responses: {
          ...taskData,
          industry
        }
      })
      const questionnaire = assertSuccess(questionnaireResponse, '提交问卷失败')
      questionnaireId.value = questionnaire.questionnaire_id

      const taskResponse = await pptApi.createTask({
        questionnaire_id: questionnaireId.value,
        user_id: userId,
        tenant_id: tenantId,
        industry
      })
      const task = assertSuccess(taskResponse, '创建PPT任务失败')
      taskId.value = task.task_id

      const outlineStatus = await pollTaskUntil(['outline_ready'], {
        interval: 3000,
        timeout: 10 * 60 * 1000
      })

      outline.value = normalizeOutline(outlineStatus)
      return outline.value
    } catch (err) {
      error.value = err.message || '网络错误'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generateContent(outlineData) {
    if (!taskId.value) {
      throw new Error('缺少任务ID，请先生成大纲')
    }

    loading.value = true
    error.value = null

    try {
      const currentOutline = {
        ...(outline.value || {}),
        pages: getSlidesFromOutline(outlineData || outline.value)
      }

      const confirmResponse = await pptApi.confirmOutline(taskId.value, {
        outline_json: currentOutline,
        confirmed: true
      })
      assertSuccess(confirmResponse, '确认大纲失败')

      const completedStatus = await pollTaskUntil(['completed'], {
        interval: 5000,
        timeout: 15 * 60 * 1000
      })

      const slides = getSlidesFromOutline(outline.value).map((slide, index) => ({
        ...normalizeSlide(slide, index),
        status: 'generated'
      }))

      content.value = {
        task_id: taskId.value,
        status: completedStatus.status,
        progress: completedStatus.progress,
        current_step: completedStatus.current_step,
        slides
      }

      await generatePreview()
      downloadUrl.value = pptApi.getDownloadUrl(taskId.value)
      return content.value
    } catch (err) {
      error.value = err.message || '网络错误'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generatePreview() {
    if (!taskId.value) {
      throw new Error('缺少任务ID，请先生成PPT任务')
    }

    loading.value = true
    error.value = null

    try {
      const response = await pptApi.getHtmlPages(taskId.value)
      const pages = assertSuccess(response, '获取HTML预览失败')
      const htmlPages = Array.isArray(pages) ? pages : []

      preview.value = {
        task_id: taskId.value,
        html_pages: htmlPages,
        pages: htmlPages.map((html, index) => ({
          page_index: index + 1,
          title: getSlidesFromOutline(outline.value)[index]?.title || `第 ${index + 1} 页`,
          html
        }))
      }

      return preview.value
    } catch (err) {
      error.value = err.message || '网络错误'
      throw err
    } finally {
      loading.value = false
    }
  }

  function resetState() {
    taskId.value = null
    questionnaireId.value = null
    currentPhase.value = 1
    currentRound.value = 1
    outline.value = null
    content.value = null
    preview.value = null
    currentPPT.value = null
    taskStatus.value = null
    downloadUrl.value = ''
    error.value = null
    surveyData.value = {
      project_name: '',
      team_name: '',
      team_size: 0,
      core_problem: '',
      target_market: '',
      solution_description: '',
      business_model: '',
      competitive_advantage: '',
      funding_stage: '',
      key_metrics: '',
      domain: DEFAULT_INDUSTRY,
      industry: DEFAULT_INDUSTRY
    }
  }

  return {
    taskId,
    questionnaireId,
    currentPhase,
    currentRound,
    outline,
    content,
    preview,
    currentPPT,
    pptList,
    loading,
    error,
    taskStatus,
    downloadUrl,
    surveyData,
    setCurrentPPT,
    setPptList,
    setLoading,
    setError,
    setCurrentPhase,
    setCurrentRound,
    setTaskId,
    setSurveyData,
    setOutline,
    setContent,
    setPreview,
    updateSlide,
    addSlide,
    removeSlide,
    generateOutline,
    generateContent,
    generatePreview,
    resetState
  }
})
