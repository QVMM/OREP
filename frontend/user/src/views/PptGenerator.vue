<template>
  <AiAppShell mode="task" width="standard">
    <template #header>
      <AiAppHeader
        app="ppt"
        mode="task"
        back-label="PPT 制作"
        back-to="/ppt-editor"
        title="创建 PPT"
        subtitle="填写项目信息并确认生成步骤"
      />
    </template>

    <AiAppSection title="创建进度" :description="currentStepLabel">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="选择领域" description="选择技术方向" />
        <el-step title="填写问卷" description="填写项目信息" />
        <el-step title="确认大纲" description="预览并确认" />
        <el-step title="生成 PPT" description="等待生成完成" />
      </el-steps>
    </AiAppSection>

    <div class="ppt-generator__task-content">
      <div class="step-content">
      <div v-if="currentStep === 0" class="domain-select">
        <div class="section-heading">
          <span class="section-heading__eyebrow">第一步</span>
          <h2 class="section-heading__title">选择项目技术领域</h2>
        </div>
        <div class="domain-grid">
          <button
            v-for="d in domains"
            :key="d.id"
            type="button"
            :class="['domain-card', { 'domain-card--active': selectedDomain === d.id }]"
            :aria-pressed="selectedDomain === d.id"
            @click="selectedDomain = d.id"
          >
            <div class="domain-card__icon">{{ d.icon }}</div>
            <div class="domain-card__name">{{ d.name }}</div>
          </button>
        </div>
        <div class="step-actions">
          <BaseButton type="primary" size="large" :disabled="!selectedDomain" @click="loadFormAndNext">
            下一步
          </BaseButton>
        </div>
      </div>

      <div v-if="currentStep === 1" class="questionnaire">
        <div class="section-heading">
          <span class="section-heading__eyebrow">第二步</span>
          <h2 class="section-heading__title">填写项目信息</h2>
        </div>
        <el-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-position="top"
          size="large"
        >
          <div v-for="section in formSections" :key="section.id" class="form-section">
            <h3 class="form-section__title">{{ section.title }}</h3>
            <div class="form-fields">
              <el-form-item
                v-for="field in section.fields"
                :key="field.id"
                :label="field.label"
                :prop="field.id"
                :rules="field.required ? [{ required: true, message: `请填写${field.label}` }] : []"
              >
                <el-input
                  v-if="field.type === 'text'"
                  v-model="formData[field.id]"
                  :placeholder="field.placeholder || `请输入${field.label}`"
                />
                <el-input
                  v-else-if="field.type === 'textarea'"
                  v-model="formData[field.id]"
                  type="textarea"
                  :rows="3"
                  :placeholder="field.placeholder || `请输入${field.label}`"
                />
                <el-select
                  v-else-if="field.type === 'select'"
                  v-model="formData[field.id]"
                  :placeholder="`请选择${field.label}`"
                  style="width: 100%"
                >
                  <el-option
                    v-for="opt in field.options"
                    :key="typeof opt === 'string' ? opt : opt.value"
                    :label="typeof opt === 'string' ? opt : opt.label"
                    :value="typeof opt === 'string' ? opt : opt.value"
                  />
                </el-select>
                <el-slider
                  v-else-if="field.type === 'range'"
                  v-model="formData[field.id]"
                  :min="field.min || 10"
                  :max="field.max || 30"
                  :step="1"
                  show-input
                />
              </el-form-item>
            </div>
          </div>
        </el-form>
        <div class="step-actions">
          <BaseButton type="secondary" size="large" @click="currentStep = 0">上一步</BaseButton>
          <BaseButton
            type="primary"
            size="large"
            :loading="submitBusy"
            :disabled="submitBusy"
            @click="submitQuestionnaire"
          >
            提交并生成大纲
          </BaseButton>
        </div>
      </div>

      <div v-if="currentStep === 2" class="outline-confirm">
        <div v-if="taskStatus === 'generating'" class="loading-state">
          <el-icon class="loading-spinner" :size="48"><Loading /></el-icon>
          <p class="loading-state__text">正在生成大纲，请稍候...</p>
        </div>

        <div v-else-if="taskStatus === 'outline_ready'" class="outline-preview">
          <div class="section-heading">
            <span class="section-heading__eyebrow">第三步</span>
            <h2 class="section-heading__title">大纲预览</h2>
            <p class="section-heading__tip">请确认以下大纲，确认后将开始生成 PPT。</p>
          </div>

          <BaseCard class="outline-card">
            <template #header>
              <div class="outline-card__header">
                <h3 class="outline-card__title">{{ outlineData?.project?.name }}</h3>
                <span class="page-badge">{{ outlineData?.pages?.length }} 页</span>
              </div>
            </template>
            <div class="outline-pages">
              <div
                v-for="page in outlineData?.pages"
                :key="page.page_index"
                class="outline-page"
              >
                <div class="outline-page__num">{{ page.page_index }}</div>
                <div class="outline-page__info">
                  <div class="outline-page__title">{{ page.data?.title || page.section }}</div>
                  <div class="outline-page__layout">{{ getLayoutName(page.layout) }}</div>
                </div>
              </div>
            </div>
          </BaseCard>

          <div class="theme-select">
            <h3 class="theme-select__title">选择视觉风格</h3>
            <div class="theme-grid">
              <button
                v-for="theme in themes"
                :key="theme.theme_id"
                type="button"
                :class="['theme-card', { 'theme-card--active': selectedTheme === theme.theme_id }]"
                :aria-pressed="selectedTheme === theme.theme_id"
                @click="selectedTheme = theme.theme_id"
              >
                <div class="theme-card__preview" :style="getThemeStyle(theme.theme_config)"></div>
                <div class="theme-card__name">{{ theme.name }}</div>
              </button>
            </div>
          </div>

          <div class="step-actions">
            <BaseButton type="secondary" size="large" @click="currentStep = 1">返回修改</BaseButton>
            <BaseButton
              type="primary"
              size="large"
              :loading="confirmBusy"
              :disabled="confirmBusy"
              @click="confirmAndGenerate"
            >
              确认生成 PPT
            </BaseButton>
          </div>
        </div>

        <div v-else-if="taskStatus === 'failed'" class="error-state">
          <el-icon :size="48" color="#FF3B30"><CircleClose /></el-icon>
          <p class="error-state__title">生成失败</p>
          <p class="error-state__msg">{{ taskErrorMsg }}</p>
          <BaseButton type="secondary" size="medium" @click="resetAndStartOver">重新开始</BaseButton>
        </div>
      </div>

      <div v-if="currentStep === 3" class="generating-state">
        <div v-if="taskStatus === 'rendering'" class="generating-progress">
          <el-progress
            type="circle"
            :percentage="taskProgress"
            :status="taskProgress === 100 ? 'success' : ''"
          />
          <p class="generating-progress__text">{{ currentStepText }}</p>
        </div>

        <div v-else-if="taskStatus === 'completed'" class="completed-state">
          <el-icon :size="64" color="#34C759"><CircleCheck /></el-icon>
          <h2 class="completed-state__title">生成完成！</h2>
          <p class="completed-state__desc">PPT 已生成成功，点击下方按钮下载</p>
          <div class="step-actions">
            <BaseButton
              type="primary"
              size="large"
              :loading="downloadBusy"
              :disabled="downloadBusy"
              @click="downloadPPT"
            >
              <el-icon><Download /></el-icon>
              下载 PPT
            </BaseButton>
            <BaseButton type="secondary" size="large" @click="resetAndStartOver">生成新的PPT</BaseButton>
          </div>
        </div>

        <div v-else-if="taskStatus === 'failed'" class="error-state">
          <el-icon :size="48" color="#FF3B30"><CircleClose /></el-icon>
          <p class="error-state__title">生成失败</p>
          <p class="error-state__msg">{{ taskErrorMsg }}</p>
          <BaseButton type="secondary" size="medium" @click="resetAndStartOver">重新开始</BaseButton>
        </div>
      </div>
      </div>

      <div v-if="currentStep === 0 && historyTasks.length > 0" class="history-section">
        <h3 class="history-section__title">历史生成记录</h3>
        <div class="history-list">
          <button
            v-for="task in historyTasks"
            :key="task.id"
            type="button"
            class="history-card"
            @click="viewHistoryTask(task)"
          >
            <div class="history-card__info">
              <div class="history-card__name">{{ task.project_name }}</div>
              <div class="history-card__meta">
                {{ formatDate(task.created_at) }} · {{ task.domain }}
              </div>
            </div>
            <el-tag :type="getStatusType(task.status)" size="small">
              {{ getStatusText(task.status) }}
            </el-tag>
          </button>
        </div>
      </div>
    </div>
  </AiAppShell>
</template>

<script>
export function createPptTaskCoordinator({
  schedule = (callback, delay) => setTimeout(callback, delay),
  cancel = timerId => clearTimeout(timerId),
} = {}) {
  let mounted = false
  let workflow = 0
  let pollingCycle = 0
  let pollingTimer = null
  const operationLocks = new Set()

  const stopPolling = () => {
    pollingCycle += 1
    if (pollingTimer !== null) {
      cancel(pollingTimer)
      pollingTimer = null
    }
  }

  const mount = () => {
    mounted = true
  }

  const invalidateWorkflow = () => {
    workflow += 1
    stopPolling()
    return workflow
  }

  const beginWorkflow = () => invalidateWorkflow()
  const isCurrent = token => mounted && token === workflow
  const currentWorkflow = () => workflow
  const isMounted = () => mounted

  const unmount = () => {
    mounted = false
    invalidateWorkflow()
  }

  const startPolling = ({
    workflow: workflowToken,
    jobId,
    fetchStatus,
    applyStatus,
    shouldStop,
    onError = () => {},
    delay = 2000,
  }) => {
    stopPolling()
    const cycle = pollingCycle

    const scheduleNext = () => {
      if (!isCurrent(workflowToken) || cycle !== pollingCycle) return
      pollingTimer = schedule(runPoll, delay)
    }

    const runPoll = async () => {
      pollingTimer = null
      if (!isCurrent(workflowToken) || cycle !== pollingCycle) return

      try {
        const status = await fetchStatus(jobId)
        if (!isCurrent(workflowToken) || cycle !== pollingCycle) return
        applyStatus(status)
        if (shouldStop(status)) {
          stopPolling()
          return
        }
      } catch (error) {
        if (!isCurrent(workflowToken) || cycle !== pollingCycle) return
        onError(error)
      }

      scheduleNext()
    }

    scheduleNext()
  }

  const runOnce = async (key, operation) => {
    if (operationLocks.has(key)) return { started: false }
    operationLocks.add(key)
    try {
      return { started: true, value: await operation() }
    } finally {
      operationLocks.delete(key)
    }
  }

  return {
    mount,
    unmount,
    isMounted,
    beginWorkflow,
    invalidateWorkflow,
    currentWorkflow,
    isCurrent,
    startPolling,
    stopPolling,
    runOnce,
  }
}
</script>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Loading, CircleCheck, CircleClose, Download
} from '@element-plus/icons-vue'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppSection from '@/components/ai-apps/AiAppSection.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
import { useAuthStore } from '../stores/auth'
import request from '../utils/request'
import { BaseButton, BaseCard } from '../components/base'

const router = useRouter()
const authStore = useAuthStore()

const currentStep = ref(0)
const stepLabels = ['选择领域', '填写问卷', '确认大纲', '生成 PPT']
const currentStepLabel = computed(() => stepLabels[currentStep.value] || '任务准备')

const domains = [
  { id: 'ai_iot', name: 'AI + 物联网', icon: 'AI' },
  { id: 'fintech', name: '金融科技', icon: 'FT' },
  { id: 'healthcare', name: '智慧医疗', icon: 'HC' },
  { id: 'education', name: '智慧教育', icon: 'ED' },
  { id: 'other', name: '其他领域', icon: 'OT' },
]
const selectedDomain = ref('')

const formRef = ref(null)
const formSections = ref([])
const formData = ref({})
const formRules = ref({})

const currentTaskId = ref(null)
const taskStatus = ref('')
const taskProgress = ref(0)
const currentStepText = ref('')
const taskErrorMsg = ref('')
const outlineData = ref(null)

const themes = ref([])
const selectedTheme = ref('dark_tech')

const historyTasks = ref([])
const submitBusy = ref(false)
const confirmBusy = ref(false)
const downloadBusy = ref(false)
const taskCoordinator = createPptTaskCoordinator()

onMounted(() => {
  taskCoordinator.mount()
  loadThemes()
  loadHistoryTasks()
})

onUnmounted(() => {
  taskCoordinator.unmount()
})

const loadThemes = async () => {
  try {
    const res = await request.get('/api/ppt/themes', { silentError: true })
    themes.value = res.data || []
  } catch (e) {
    console.error('加载主题失败:', e)
  }
}

const loadHistoryTasks = async (workflow = taskCoordinator.currentWorkflow()) => {
  try {
    if (!taskCoordinator.isCurrent(workflow)) return
    const userId = authStore.user?.id
    if (!userId) return
    const res = await request.get(`/api/ppt/user/${userId}/tasks`, { silentError: true })
    if (!taskCoordinator.isCurrent(workflow)) return
    historyTasks.value = res.data || []
  } catch (e) {
    if (taskCoordinator.isCurrent(workflow)) {
      console.error('加载历史任务失败:', e)
    }
  }
}

const loadFormAndNext = async () => {
  try {
    const res = await request.get(`/api/ppt/forms/${selectedDomain.value}`)
    const formConfig = res.data?.form_schema
    if (formConfig?.sections) {
      formSections.value = formConfig.sections
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
    currentStep.value = 1
  } catch (e) {
    ElMessage.error('加载表单失败')
  }
}

const submitQuestionnaire = async () => {
  if (submitBusy.value || !taskCoordinator.isMounted()) return
  submitBusy.value = true
  const workflow = taskCoordinator.beginWorkflow()

  try {
    await taskCoordinator.runOnce('submit', async () => {
      await formRef.value?.validate()
      if (!taskCoordinator.isCurrent(workflow)) return

      const userId = authStore.user?.id
      const tenantId = authStore.user?.tenantId || 1
      const questionnaireRes = await request.post('/api/ppt/questionnaire/submit', {
        user_id: userId,
        tenant_id: tenantId,
        domain: selectedDomain.value,
        project_name: formData.value.project_name || '项目路演',
        team_name: formData.value.team_name || '',
        responses: formData.value
      })
      if (!taskCoordinator.isCurrent(workflow)) return

      const taskRes = await request.post('/api/ppt/task/create', {
        questionnaire_id: questionnaireRes.data?.questionnaire_id,
        user_id: userId,
        tenant_id: tenantId,
        theme: selectedTheme.value
      })
      if (!taskCoordinator.isCurrent(workflow)) return

      const taskId = taskRes.data?.task_id
      if (!taskId) throw new Error('创建 PPT 任务失败')
      currentTaskId.value = taskId
      taskStatus.value = 'generating'
      currentStep.value = 2
      startStatusPolling(taskId, workflow)
    })
  } catch (e) {
    if (!taskCoordinator.isCurrent(workflow)) return
    ElMessage.error(e?.message || '提交失败，请检查表单')
  } finally {
    submitBusy.value = false
  }
}

const startStatusPolling = (taskId, workflow) => {
  taskCoordinator.startPolling({
    workflow,
    jobId: taskId,
    fetchStatus: async activeTaskId => {
      const res = await request.get(`/api/ppt/task/${activeTaskId}`)
      return res.data
    },
    applyStatus: task => {
      taskStatus.value = task.status
      taskProgress.value = task.progress || 0
      currentStepText.value = task.current_step || ''
      taskErrorMsg.value = task.error_msg || ''

      if (task.outline_json) {
        outlineData.value = task.outline_json
      }

      if (task.status === 'completed') {
        taskProgress.value = 100
      }

      if (task.status === 'rendering') {
        currentStep.value = 3
      }
      if (task.status === 'completed') {
        currentStep.value = 3
        loadHistoryTasks(workflow)
      }
    },
    shouldStop: task => ['outline_ready', 'completed', 'failed'].includes(task.status),
    onError: e => {
      console.error('轮询状态失败:', e)
    },
  })
}

const confirmAndGenerate = async () => {
  if (confirmBusy.value || !currentTaskId.value) return
  const taskId = currentTaskId.value
  const workflow = taskCoordinator.currentWorkflow()
  if (!taskCoordinator.isCurrent(workflow)) return
  confirmBusy.value = true

  try {
    await taskCoordinator.runOnce('confirm', async () => {
      await request.post(`/api/ppt/task/${taskId}/confirm`, {
        confirmed: true
      })
      if (!taskCoordinator.isCurrent(workflow) || currentTaskId.value !== taskId) return

      taskStatus.value = 'rendering'
      currentStep.value = 3
      taskProgress.value = 60
      currentStepText.value = '正在渲染 PPT...'
      startStatusPolling(taskId, workflow)
      ElMessage.success('已确认，开始生成 PPT')
    })
  } catch (e) {
    if (!taskCoordinator.isCurrent(workflow)) return
    ElMessage.error('确认失败')
  } finally {
    confirmBusy.value = false
  }
}

const downloadPPT = async () => {
  if (downloadBusy.value || !currentTaskId.value) return
  const taskId = currentTaskId.value
  const workflow = taskCoordinator.currentWorkflow()
  if (!taskCoordinator.isCurrent(workflow)) return
  downloadBusy.value = true

  try {
    await taskCoordinator.runOnce('download', async () => {
      const response = await fetch(`/api/ppt/task/${taskId}/download`, {
        headers: {
          'Authorization': `Bearer ${authStore.token}`
        }
      })
      if (!response.ok) throw new Error('下载失败')

      const blob = await response.blob()
      if (!taskCoordinator.isCurrent(workflow) || currentTaskId.value !== taskId) return
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ppt_${taskId}.pptx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      ElMessage.success('下载成功')
    })
  } catch (e) {
    if (!taskCoordinator.isCurrent(workflow)) return
    ElMessage.error('下载失败')
  } finally {
    downloadBusy.value = false
  }
}

const viewHistoryTask = (task) => {
  const id = task?.id ?? task?.task_id ?? task?.taskId
  const jobId = task?.job_id ?? task?.jobId
  // Prefer agent job_id → editor. Hex-like ids are also jobs (not legacy numeric tasks).
  const preferred = jobId || id
  if (preferred != null && preferred !== '') {
    const asStr = String(preferred)
    const looksLikeAgentJob = !/^\d+$/.test(asStr)
    if (jobId || looksLikeAgentJob) {
      router.push({ path: '/ppt-editor', query: { job: asStr } })
      return
    }
  }
  if (id != null) {
    // Legacy numeric task → detail page (auto-fallback to editor if agent job)
    router.push(`/ppt-history/${id}`)
    return
  }
  ElMessage.warning('该历史记录缺少任务 ID')
}

const resetAndStartOver = () => {
  taskCoordinator.invalidateWorkflow()
  currentStep.value = 0
  selectedDomain.value = ''
  formData.value = {}
  formSections.value = []
  currentTaskId.value = null
  taskStatus.value = ''
  taskProgress.value = 0
  currentStepText.value = ''
  taskErrorMsg.value = ''
  outlineData.value = null
}

const getLayoutName = (layout) => {
  const names = {
    cover_page: '封面页',
    toc_page: '目录页',
    full_text_page: '文字页',
    two_column_contrast: '双栏对比',
    triple_icon_cards: '三卡片',
    team_member_cards: '团队卡片',
    section_divider: '章节过渡',
    ending_page: '结束页',
    infographic_flow: '信息图流程',
    kpi_dashboard: '数据仪表盘',
    bar_chart_insight: '柱状图分析',
  }
  return names[layout] || layout
}

const getThemeStyle = (config) => {
  if (!config || !config.colors) return {}
  return {
    background: `linear-gradient(135deg, ${config.colors.bg} 0%, ${config.colors.card_bg} 100%)`,
    border: `2px solid ${config.colors.primary}`
  }
}

const getStatusType = (status) => {
  const types = {
    pending: 'info',
    generating: 'warning',
    outline_ready: 'primary',
    rendering: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    generating: '生成中',
    outline_ready: '待确认',
    rendering: '渲染中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}
</script>

<style scoped>
.ppt-generator__task-content {
  display: grid;
  gap: var(--ds-space-6);
  margin-top: var(--ds-space-6);
}

.step-content,
.history-section {
  width: 100%;
  margin-inline: 0;
}

:deep(.el-step__title) {
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-step__description) {
  color: var(--text-tertiary);
}

:deep(.el-step__title.is-process),
:deep(.el-step__title.is-success),
:deep(.el-step__description.is-process),
:deep(.el-step__description.is-success) {
  color: var(--text-primary);
}

:deep(.el-step__head.is-process),
:deep(.el-step__head.is-success) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

:deep(.el-step__line) {
  background-color: var(--border-light);
}

:deep(.el-step__line-inner) {
  border-color: var(--color-primary);
}

.step-content {
  min-height: 420px;
  padding: clamp(var(--spacing-lg), 3vw, var(--spacing-2xl));
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.section-heading {
  margin-bottom: var(--spacing-xl);
}

.section-heading__eyebrow {
  display: inline-flex;
  margin-bottom: var(--spacing-sm);
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  letter-spacing: 2px;
}

.section-heading__title {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(var(--font-size-xl), 4vw, var(--font-size-3xl));
  line-height: var(--line-height-tight);
  font-weight: var(--font-weight-bold);
}

.section-heading__tip {
  margin: var(--spacing-sm) 0 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.domain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.domain-card {
  appearance: none;
  width: 100%;
  padding: var(--ds-space-6);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  color: var(--ds-ink);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  font: inherit;
  cursor: pointer;
  text-align: center;
  transition:
    color var(--ds-control-transition),
    background-color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.domain-card:hover {
  border-color: var(--ds-line-strong);
}

.domain-card--active {
  border-color: var(--ds-orange-500);
  background: var(--ds-orange-wash);
}

.domain-card__icon {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--spacing-sm);
  display: grid;
  place-items: center;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  color: var(--color-primary);
  background: rgba(0, 122, 255, 0.06);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.08em;
}

.domain-card__name {
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

.form-section {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.form-section__title,
.theme-select__title,
.history-section__title {
  margin: 0 0 var(--spacing-md);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

.form-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-md);
}

.questionnaire :deep(.el-form-item__label) {
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

.questionnaire :deep(.el-input__wrapper),
.questionnaire :deep(.el-textarea__inner),
.questionnaire :deep(.el-select__wrapper) {
  min-height: 48px;
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  box-shadow: 0 0 0 1px var(--border-light) inset;
  color: var(--text-primary);
}

.questionnaire :deep(.el-textarea__inner) {
  padding: var(--spacing-md);
}

.questionnaire :deep(.el-input__wrapper.is-focus),
.questionnaire :deep(.el-select__wrapper.is-focused),
.questionnaire :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px var(--border-focus) inset, 0 0 0 4px rgba(0, 122, 255, 0.1);
}

.questionnaire :deep(.el-input__inner),
.questionnaire :deep(.el-select__placeholder),
.questionnaire :deep(.el-select__selected-item),
.questionnaire :deep(.el-textarea__inner) {
  color: var(--text-primary);
}

.questionnaire :deep(.el-input__inner::placeholder),
.questionnaire :deep(.el-textarea__inner::placeholder) {
  color: var(--text-tertiary);
}

.questionnaire :deep(.el-slider__runway) {
  background: var(--border-light);
}

.questionnaire :deep(.el-slider__bar) {
  background: var(--color-primary);
}

.questionnaire :deep(.el-slider__button) {
  border-color: var(--color-primary);
}

.outline-confirm {
  text-align: left;
}

.loading-state,
.generating-state {
  min-height: 340px;
  display: grid;
  place-items: center;
  text-align: center;
}

.loading-spinner {
  animation: spin 1s linear infinite;
  color: var(--color-primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-state__text,
.generating-progress__text,
.completed-state__desc {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.outline-card {
  margin-bottom: var(--spacing-lg);
}

.outline-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
}

.outline-card__title {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.page-badge {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 0 11px;
  border: 1px solid rgba(0, 122, 255, 0.2);
  border-radius: var(--radius-full);
  color: var(--color-primary);
  background: rgba(0, 122, 255, 0.06);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
}

.outline-pages {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: var(--spacing-sm);
}

.outline-page {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: var(--spacing-md);
  align-items: center;
  min-height: 68px;
  padding: var(--spacing-md);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
}

.outline-page__num {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(0, 122, 255, 0.2);
  border-radius: var(--radius-full);
  color: var(--color-primary);
  background: rgba(0, 122, 255, 0.06);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.outline-page__title {
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.outline-page__layout {
  margin-top: var(--spacing-xs);
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
}

.theme-select {
  margin-bottom: var(--spacing-lg);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--spacing-md);
}

.theme-card {
  appearance: none;
  width: 100%;
  padding: var(--ds-space-5);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  color: var(--ds-ink);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  font: inherit;
  cursor: pointer;
  text-align: center;
  transition:
    color var(--ds-control-transition),
    background-color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.theme-card:hover {
  border-color: var(--ds-line-strong);
}

.theme-card--active {
  border-color: var(--ds-orange-500);
  background: var(--ds-orange-wash);
}

.theme-card__preview {
  width: 100%;
  height: 58px;
  margin-bottom: var(--spacing-sm);
  border-radius: var(--radius-sm);
}

.theme-card__name {
  color: var(--text-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.generating-progress {
  display: grid;
  place-items: center;
  gap: var(--spacing-lg);
}

.generating-progress :deep(.el-progress__text) {
  color: var(--text-primary);
}

.completed-state {
  display: grid;
  place-items: center;
  gap: var(--spacing-md);
  text-align: center;
}

.completed-state__title {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
}

.step-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

.error-state {
  min-height: 300px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--spacing-md);
  text-align: center;
}

.error-state__title {
  margin: 0;
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

.error-state__msg {
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.history-section {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.history-list {
  display: grid;
  gap: var(--spacing-sm);
}

.history-card {
  appearance: none;
  width: 100%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
  padding: var(--ds-space-5);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  color: var(--ds-ink);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  font: inherit;
  text-align: left;
  transition:
    color var(--ds-control-transition),
    background-color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.history-card:hover {
  border-color: var(--ds-line-strong);
}

.domain-card:focus-visible,
.theme-card:focus-visible,
.history-card:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
  box-shadow: var(--ds-btn-focus-ring);
}

.history-card__name {
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

.history-card__meta {
  margin-top: var(--spacing-xs);
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
}

@media (max-width: 860px) {
  .step-content {
    padding: var(--spacing-md);
  }

  .form-fields,
  .outline-pages,
  .domain-grid,
  .theme-grid {
    grid-template-columns: 1fr;
  }

  .outline-card__header,
  .history-card {
    grid-template-columns: 1fr;
  }
}
</style>
