<template>
  <div class="ppt-editor">
    <section class="hero-band">
      <div>
        <p class="eyebrow">PPT Agent</p>
        <h1>智能 PPT 生成工作台</h1>
        <p class="hero-copy">上传论文、方案或比赛资料，主系统会调度 MiMo/Qwen 与视觉审查链路生成可预览、可下载的演示文稿。</p>
      </div>
      <div class="status-strip">
        <span :class="['status-dot', healthOk ? 'ok' : 'warn']"></span>
        <span>{{ healthOk ? '主服务已连接' : '等待服务响应' }}</span>
      </div>
    </section>

    <section class="workspace-grid">
      <aside class="control-panel">
        <n-space vertical size="large">
          <div class="panel-block">
            <div class="block-head">
              <h2>资料输入</h2>
              <span class="block-note">PDF / TeX / Zip</span>
            </div>
            <label class="upload-box" :class="{ ready: uploadedSession }">
              <input type="file" accept=".pdf,.tex,.zip,.tgz,.tar.gz" @change="handleFileChange" />
              <span class="upload-title">{{ uploadedSession ? uploadedFileName : '选择资料文件' }}</span>
              <span class="upload-desc">{{ uploadedSession ? uploadMetaText : '支持论文、项目说明书、附件压缩包' }}</span>
            </label>
          </div>

          <div class="panel-block">
            <div class="block-head">
              <h2>生成要求</h2>
              <span class="block-note">服务端密钥</span>
            </div>
            <n-input
              v-model:value="instruction"
              type="textarea"
              :autosize="{ minRows: 5, maxRows: 8 }"
              placeholder="写明参赛方向、项目目标、技术重点、希望强化的评审视角。不要填写姓名、学校、电话、邮箱等个人信息。"
            />
          </div>

          <div class="panel-block two-col">
            <n-form-item label="模型">
              <n-select v-model:value="selectedProviderModel" :options="providerOptions" :loading="loadingMeta" />
            </n-form-item>
            <n-form-item label="模板">
              <n-select v-model:value="selectedTemplate" :options="templateOptions" :loading="loadingMeta" clearable />
            </n-form-item>
            <n-form-item label="语言">
              <n-select v-model:value="language" :options="languageOptions" />
            </n-form-item>
            <n-form-item label="页数策略">
              <n-select v-model:value="pagePolicy" :options="pagePolicyOptions" />
            </n-form-item>
          </div>

          <div class="panel-block">
            <div class="block-head">
              <h2>增强能力</h2>
              <span class="block-note">按需开启</span>
            </div>
            <div class="toggles">
              <n-switch v-model:value="enableDeepResearch">
                <template #checked>深度研究</template>
                <template #unchecked>深度研究</template>
              </n-switch>
              <n-switch v-model:value="enableVisualCritic">
                <template #checked>视觉审查</template>
                <template #unchecked>视觉审查</template>
              </n-switch>
              <n-switch v-model:value="enableIcon">
                <template #checked>图标装饰</template>
                <template #unchecked>图标装饰</template>
              </n-switch>
            </div>
          </div>

          <div class="action-row">
            <n-button type="primary" size="large" :loading="isSubmitting" :disabled="!canGenerate" @click="startGenerate">
              开始生成
            </n-button>
            <n-button v-if="canResume" type="warning" size="large" :loading="isSubmitting" @click="resumeCurrentJob">
              从缓存继续
            </n-button>
            <n-button size="large" :disabled="!canCancel" @click="cancelCurrentJob">取消</n-button>
          </div>
        </n-space>
      </aside>

      <main class="preview-panel">
        <div class="progress-head">
          <div>
            <p class="eyebrow">生成进度</p>
            <h2>{{ jobTitle }}</h2>
          </div>
          <a v-if="canDownload" class="download-link" :href="downloadUrl" target="_blank" rel="noreferrer">下载 PPTX</a>
        </div>

        <n-progress
          type="line"
          :percentage="progressPercent"
          :status="progressStatus"
          :height="12"
          border-radius="8px"
          fill-border-radius="8px"
        />

        <div class="stage-grid">
          <div v-for="stage in stages" :key="stage.key" :class="['stage-item', stageState(stage.key)]">
            <span>{{ stage.label }}</span>
          </div>
        </div>

        <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

        <div class="slide-area" v-if="slides.length">
          <div class="thumb-rail">
            <button
              v-for="slide in slides"
              :key="slide.index"
              :class="['thumb', { active: activeSlideIndex === slide.index }]"
              @click="activeSlideIndex = slide.index"
            >
              <span>{{ String(slide.index).padStart(2, '0') }}</span>
              <div class="thumb-svg" v-html="slide.content"></div>
            </button>
          </div>
          <div class="slide-canvas">
            <div class="svg-frame" v-html="activeSlide?.content"></div>
            <p v-if="activeSlide?.notes" class="notes">{{ activeSlide.notes }}</p>
          </div>
        </div>

        <div v-else class="empty-preview">
          <div class="empty-mark">PPT</div>
          <h3>生成后将在这里实时预览页面</h3>
          <p>WebSocket 会同步进度和逐页 SVG，任务完成后可直接下载 PPTX。</p>
        </div>
      </main>

      <aside class="log-panel">
        <div class="block-head">
          <h2>代理日志</h2>
          <span class="block-note">{{ jobId || '尚未创建任务' }}</span>
        </div>
        <div class="log-list">
          <div v-for="item in logs" :key="item.id" class="log-item">
            <span class="log-stage">{{ item.stage }}</span>
            <p>{{ item.message }}</p>
          </div>
          <div v-if="!logs.length" class="muted">等待上传资料并开始生成。</div>
        </div>

        <div class="critic-block">
          <div class="block-head">
            <h2>视觉审查</h2>
            <span class="block-note">{{ criticEvents.length }} 条</span>
          </div>
          <div v-if="criticEvents.length" class="critic-list">
            <div v-for="(event, index) in criticEvents" :key="index" class="critic-item">
              <strong>{{ event.page ? `第 ${event.page} 页` : '页面审查' }}</strong>
              <span>{{ event.status || event.result || '已记录' }}</span>
            </div>
          </div>
          <div v-else class="muted">开启视觉审查后，完成任务会显示审查记录。</div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { pptApi } from '../api/pptApi'

const message = useMessage()

const healthOk = ref(false)
const loadingMeta = ref(false)
const isSubmitting = ref(false)
const uploadedSession = ref('')
const uploadedFileName = ref('')
const uploadedFileSize = ref(0)
const instruction = ref('面向职业院校技能大赛作品汇报，突出项目背景、技术方案、实操闭环、数据证据、风险控制和改进方向。禁止出现姓名、学校、电话、邮箱等个人信息；数据和结论需要可追溯。')
const providers = ref([])
const templates = ref([])
const selectedProviderModel = ref('mimo::mimo-v2.5-pro')
const selectedTemplate = ref('')
const language = ref('zh')
const pagePolicy = ref('competition')
const enableDeepResearch = ref(true)
const enableVisualCritic = ref(true)
const enableIcon = ref(true)
const jobId = ref('')
const jobStatus = ref('')
const jobMessage = ref('')
const progress = ref(0)
const slidesCompleted = ref(0)
const totalSlides = ref(0)
const errorMessage = ref('')
const logs = ref([])
const slides = ref([])
const criticEvents = ref([])
const activeSlideIndex = ref(1)
let socket = null
let pollTimer = null
let pollFailureCount = 0
let lastPollErrorMessage = ''
let logSeq = 0

const stages = [
  { key: 'parsing', label: '解析' },
  { key: 'research', label: '研究' },
  { key: 'strategy', label: '策略' },
  { key: 'generation', label: '生成' },
  { key: 'postprocess', label: '修整' },
  { key: 'export', label: '导出' }
]

const languageOptions = [
  { label: '中文', value: 'zh' },
  { label: 'English', value: 'en' }
]

const pagePolicyOptions = [
  { label: '职业赛制正式稿', value: 'competition' },
  { label: '快速验证 8 页', value: 'smoke' },
  { label: '资料自适应', value: 'auto' }
]

const uploadMetaText = computed(() => {
  if (!uploadedFileSize.value) return '资料已上传'
  return `${formatFileSize(uploadedFileSize.value)}，会作为生成依据`
})

const providerOptions = computed(() => {
  return providers.value.flatMap((provider) => {
    return (provider.models || []).map((model) => ({
      label: `${provider.display_name || provider.name} / ${model.display_name || model.id}`,
      value: `${provider.name}::${model.id}`,
      provider,
      model
    }))
  })
})

const templateOptions = computed(() => {
  return templates.value.map((template) => ({
    label: template.label ? `${template.label} (${template.template_id})` : template.template_id,
    value: template.template_id
  }))
})

const selectedProvider = computed(() => {
  const [providerName, modelId] = selectedProviderModel.value.split('::')
  const provider = providers.value.find((item) => item.name === providerName)
  return {
    provider: providerName || 'mimo',
    model: modelId || 'mimo-v2.5-pro',
    baseUrl: provider?.default_base_url || null
  }
})

const canGenerate = computed(() => Boolean(uploadedSession.value && selectedProviderModel.value && !isRunning.value))
const canCancel = computed(() => Boolean(jobId.value && isRunning.value))
const canResume = computed(() => Boolean(jobId.value && jobStatus.value === 'error' && slidesCompleted.value > 0 && totalSlides.value > slidesCompleted.value && !isRunning.value))
const isRunning = computed(() => ['pending', 'parsing', 'research', 'strategy', 'generation', 'postprocess', 'export'].includes(jobStatus.value))
const canDownload = computed(() => Boolean(jobId.value && jobStatus.value === 'complete'))
const downloadUrl = computed(() => (jobId.value ? pptApi.getAgentDownloadUrl(jobId.value) : ''))
const progressPercent = computed(() => Math.max(0, Math.min(100, Math.round((progress.value || 0) * 100))))
const progressStatus = computed(() => {
  if (jobStatus.value === 'error') return 'error'
  if (jobStatus.value === 'complete') return 'success'
  return 'default'
})
const jobTitle = computed(() => {
  if (!jobId.value) return '等待创建任务'
  if (jobStatus.value === 'complete') return '生成完成'
  if (jobStatus.value === 'error') return '生成失败'
  return jobMessage.value || '任务运行中'
})
const activeSlide = computed(() => slides.value.find((slide) => slide.index === activeSlideIndex.value) || slides.value[0])

onMounted(async () => {
  await loadMeta()
})

onBeforeUnmount(() => {
  closeSocket()
  stopPolling()
})

async function loadMeta() {
  loadingMeta.value = true
  try {
    const [health, providerRes, templateRes] = await Promise.all([
      pptApi.health(),
      pptApi.fetchAgentProviders(),
      pptApi.fetchAgentTemplates()
    ])
    healthOk.value = health.status === 'ok'
    providers.value = providerRes.providers || []
    templates.value = templateRes || []
    const mimoOption = providerOptions.value.find((item) => item.value.startsWith('mimo::'))
    if (mimoOption) selectedProviderModel.value = mimoOption.value
    const preferredTemplate = templates.value.find((item) => item.template_id === 'ai_ops') || templates.value[0]
    if (preferredTemplate) selectedTemplate.value = preferredTemplate.template_id
  } catch (error) {
    healthOk.value = false
    message.error(readError(error, 'PPT Agent 元信息加载失败'))
  } finally {
    loadingMeta.value = false
  }
}

async function handleFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    isSubmitting.value = true
    const result = await pptApi.uploadAgentFile(file)
    uploadedSession.value = result.session_id
    uploadedFileName.value = result.file_info?.name || file.name
    uploadedFileSize.value = result.file_info?.size || file.size
    message.success('资料上传完成')
  } catch (error) {
    message.error(readError(error, '上传失败'))
  } finally {
    isSubmitting.value = false
    event.target.value = ''
  }
}

async function startGenerate() {
  if (!canGenerate.value) return
  resetJobState()
  isSubmitting.value = true
  const currentProvider = selectedProvider.value
  const payload = {
    session_id: uploadedSession.value,
    instruction: instruction.value,
    model_config: {
      provider: currentProvider.provider,
      model: currentProvider.model,
      api_key: '',
      base_url: currentProvider.baseUrl
    },
    options: {
      canvas_format: 'ppt169',
      style: 'academic',
      num_pages: resolvePageCount(),
      language: language.value,
      detail_level: pagePolicy.value === 'smoke' ? 'brief' : 'normal',
      icon_library: 'chunk',
      max_critic_attempts: enableVisualCritic.value ? 3 : 1,
      enable_deep_research: enableDeepResearch.value,
      enable_visual_critic: enableVisualCritic.value,
      visual_qa_max_attempts: enableVisualCritic.value ? 1 : 0,
      enable_icon: enableIcon.value,
      enable_icon_rag: enableIcon.value,
      template_id: selectedTemplate.value || null,
      research_config: {
        arxiv_search_enabled: false,
        semantic_scholar_enabled: false,
        web_search_enabled: enableDeepResearch.value,
        web_search_provider: 'mimo',
        max_results_per_source: 10,
        relevance_filter: true
      }
    }
  }
  try {
    const result = await pptApi.generateAgentPresentation(payload)
    jobId.value = result.job_id
    jobStatus.value = 'pending'
    jobMessage.value = '任务已入队'
    appendLog('pending', `任务 ${result.job_id} 已创建`)
    connectSocket(result.job_id)
    startPolling(result.job_id)
  } catch (error) {
    errorMessage.value = readError(error, '创建生成任务失败')
    message.error(errorMessage.value)
  } finally {
    isSubmitting.value = false
  }
}

async function cancelCurrentJob() {
  if (!jobId.value) return
  try {
    await pptApi.cancelAgentJob(jobId.value)
    appendLog('cancelled', '已请求取消任务')
  } catch (error) {
    message.error(readError(error, '取消失败'))
  }
}

async function resumeCurrentJob() {
  if (!jobId.value) return
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    const result = await pptApi.resumeAgentGeneration(jobId.value)
    jobStatus.value = result.status === 'running' ? 'generation' : 'pending'
    jobMessage.value = '已从缓存页继续生成'
    appendLog('resume', `任务 ${jobId.value} 已从 ${slidesCompleted.value}/${totalSlides.value} 页继续`)
    connectSocket(jobId.value)
    startPolling(jobId.value)
  } catch (error) {
    errorMessage.value = readError(error, '恢复任务失败')
    message.error(errorMessage.value)
  } finally {
    isSubmitting.value = false
  }
}

function connectSocket(id) {
  closeSocket()
  socket = new WebSocket(pptApi.getAgentWebSocketUrl(id))
  socket.onmessage = (event) => {
    try {
      handleAgentEvent(JSON.parse(event.data))
    } catch (_) {
      appendLog('ws', '收到无法解析的进度消息')
    }
  }
  socket.onerror = () => appendLog('ws', '进度连接异常，已启用轮询兜底')
}

function closeSocket() {
  if (socket) {
    socket.close()
    socket = null
  }
}

function startPolling(id) {
  stopPolling()
  pollFailureCount = 0
  lastPollErrorMessage = ''
  pollTimer = window.setInterval(() => syncJob(id), 5000)
  syncJob(id)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

async function syncJob(id) {
  try {
    const status = await pptApi.getAgentJobStatus(id)
    if (pollFailureCount >= 3) {
      appendLog('poll', '状态同步已恢复，继续保留当前生成进度')
    }
    pollFailureCount = 0
    lastPollErrorMessage = ''
    applyStatus(status)
    if (['complete', 'error', 'cancelled'].includes(status.status)) {
      stopPolling()
      closeSocket()
      await loadPreviewAndCritic(id)
    }
  } catch (error) {
    pollFailureCount += 1
    lastPollErrorMessage = readError(error, '状态同步失败')
    if (pollFailureCount === 3 || pollFailureCount % 6 === 0) {
      appendLog(
        'poll',
        `状态同步暂时失败，正在重试；后台任务进度不会被重置（${lastPollErrorMessage}）`
      )
    }
  }
}

function handleAgentEvent(event) {
  if (event.type === 'ping') return
  if (event.type === 'slide_ready' && event.data?.svg) {
    upsertSlide({
      index: Number(event.data.page || slides.value.length + 1),
      name: `slide_${event.data.page || slides.value.length + 1}`,
      content: event.data.svg,
      notes: ''
    })
  }
  if (event.type === 'progress' || event.type === 'complete' || event.type === 'error') {
    applyStatus(event)
    appendLog(event.stage || event.type, event.message || event.status || event.type)
  }
  if (event.type === 'complete' || event.type === 'error') {
    loadPreviewAndCritic(jobId.value)
    stopPolling()
  }
}

function applyStatus(status) {
  jobStatus.value = status.status === 'progress' ? status.stage : status.status
  jobMessage.value = status.message || jobMessage.value
  progress.value = Math.max(Number(progress.value || 0), Number(status.progress || 0))
  slidesCompleted.value = Math.max(Number(slidesCompleted.value || 0), Number(status.slides_completed || 0))
  totalSlides.value = Math.max(Number(totalSlides.value || 0), Number(status.total_slides || 0))
  if (status.error || status.type === 'error') {
    errorMessage.value = status.error || status.message || '生成失败'
  }
}

async function loadPreviewAndCritic(id) {
  if (!id) return
  try {
    const preview = await pptApi.getAgentPreview(id)
    if (preview.slides?.length) {
      slides.value = preview.slides
      activeSlideIndex.value = preview.slides[0].index
    }
  } catch (error) {
    appendLog('preview', readError(error, '预览尚不可用'))
  }
  try {
    const critic = await pptApi.getAgentCritic(id)
    criticEvents.value = critic.events || []
  } catch (_) {
    criticEvents.value = []
  }
}

function upsertSlide(slide) {
  const next = [...slides.value]
  const index = next.findIndex((item) => item.index === slide.index)
  if (index >= 0) {
    next.splice(index, 1, slide)
  } else {
    next.push(slide)
  }
  slides.value = next.sort((a, b) => a.index - b.index)
  if (!activeSlideIndex.value) activeSlideIndex.value = slide.index
}

function appendLog(stage, text) {
  if (!text) return
  logs.value.unshift({
    id: ++logSeq,
    stage,
    message: text
  })
  logs.value = logs.value.slice(0, 80)
}

function resetJobState() {
  closeSocket()
  stopPolling()
  jobId.value = ''
  jobStatus.value = ''
  jobMessage.value = ''
  progress.value = 0
  slidesCompleted.value = 0
  totalSlides.value = 0
  errorMessage.value = ''
  logs.value = []
  slides.value = []
  criticEvents.value = []
  activeSlideIndex.value = 1
}

function stageState(stageKey) {
  const currentIndex = stages.findIndex((stage) => stage.key === jobStatus.value)
  const stageIndex = stages.findIndex((stage) => stage.key === stageKey)
  if (jobStatus.value === 'complete') return 'done'
  if (jobStatus.value === 'error') return stageIndex <= currentIndex ? 'warn' : ''
  if (stageIndex < currentIndex) return 'done'
  if (stageIndex === currentIndex) return 'active'
  return ''
}

function resolvePageCount() {
  if (pagePolicy.value === 'smoke') return 8
  return null
}

function formatFileSize(size) {
  if (size > 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(size / 1024))} KB`
}

function readError(error, fallback) {
  const data = error?.response?.data
  if (typeof data === 'string') return data
  if (data?.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
  return error?.message || fallback
}
</script>

<style scoped>
.ppt-editor {
  min-height: calc(100vh - 112px);
  color: #172033;
}

.hero-band {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  padding: 28px 32px;
  border: 1px solid #dbe6f5;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(6, 91, 135, 0.14), rgba(60, 160, 122, 0.12)),
    #f7fbff;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: #0a8f95;
}

h1,
h2,
h3,
p {
  margin: 0;
}

.hero-band h1 {
  font-size: 32px;
  line-height: 1.2;
  font-weight: 800;
}

.hero-copy {
  max-width: 760px;
  margin-top: 10px;
  line-height: 1.7;
  color: #526276;
}

.status-strip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 13px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid #dbe6f5;
  white-space: nowrap;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #f59e0b;
}

.status-dot.ok {
  background: #10b981;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(560px, 1fr) minmax(260px, 320px);
  gap: 18px;
  margin-top: 18px;
}

.control-panel,
.preview-panel,
.log-panel {
  border: 1px solid #dbe6f5;
  border-radius: 8px;
  background: #fff;
}

.control-panel,
.log-panel {
  padding: 18px;
}

.preview-panel {
  min-height: 720px;
  padding: 20px;
}

.panel-block {
  padding-bottom: 16px;
  border-bottom: 1px solid #ecf1f7;
}

.panel-block:last-child {
  border-bottom: 0;
}

.block-head,
.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
}

.block-head h2,
.progress-head h2 {
  font-size: 18px;
  font-weight: 800;
}

.block-note,
.muted {
  font-size: 12px;
  color: #718096;
}

.upload-box {
  display: grid;
  gap: 8px;
  min-height: 126px;
  padding: 18px;
  border: 1px dashed #9db2ca;
  border-radius: 8px;
  background: #f8fbff;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-box.ready {
  border-color: #0a8f95;
  background: #f0fdfa;
}

.upload-box input {
  display: none;
}

.upload-title {
  align-self: end;
  font-size: 17px;
  font-weight: 800;
}

.upload-desc {
  color: #5f6f83;
  line-height: 1.55;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: 12px;
}

.two-col :deep(.n-form-item) {
  margin-bottom: 0;
}

.toggles {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.action-row {
  display: grid;
  grid-template-columns: 1fr 96px;
  gap: 10px;
}

.download-link {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 6px;
  background: #0a8f95;
  color: #fff;
  text-decoration: none;
  font-weight: 700;
}

.stage-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  margin: 18px 0;
}

.stage-item {
  min-height: 42px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: #f1f5f9;
  color: #64748b;
  font-weight: 700;
}

.stage-item.active {
  background: #dff7f3;
  color: #04777a;
}

.stage-item.done {
  background: #e7f7ef;
  color: #13834f;
}

.stage-item.warn {
  background: #fff2df;
  color: #b45309;
}

.error-box {
  padding: 12px 14px;
  margin-bottom: 16px;
  border-radius: 6px;
  background: #fff1f2;
  color: #b42318;
  border: 1px solid #fecdd3;
}

.slide-area {
  display: grid;
  grid-template-columns: 144px 1fr;
  gap: 16px;
  min-height: 560px;
}

.thumb-rail {
  display: grid;
  align-content: start;
  gap: 10px;
  max-height: 680px;
  overflow: auto;
  padding-right: 4px;
}

.thumb {
  padding: 7px;
  border: 1px solid #dbe6f5;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  text-align: left;
}

.thumb.active {
  border-color: #0a8f95;
  box-shadow: 0 0 0 2px rgba(10, 143, 149, 0.12);
}

.thumb span {
  display: block;
  margin-bottom: 5px;
  font-size: 12px;
  font-weight: 800;
  color: #526276;
}

.thumb-svg {
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #f8fafc;
}

.thumb-svg :deep(svg),
.svg-frame :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.slide-canvas {
  min-width: 0;
}

.svg-frame {
  aspect-ratio: 16 / 9;
  width: 100%;
  overflow: hidden;
  border: 1px solid #dbe6f5;
  border-radius: 8px;
  background: #f8fafc;
}

.notes {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 6px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.6;
}

.empty-preview {
  min-height: 520px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fbff;
  text-align: center;
}

.empty-mark {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 900;
}

.empty-preview p {
  color: #64748b;
}

.log-list,
.critic-list {
  display: grid;
  gap: 10px;
  max-height: 390px;
  overflow: auto;
}

.log-item,
.critic-item {
  padding: 10px 12px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fbfdff;
}

.log-stage {
  display: inline-block;
  margin-bottom: 6px;
  color: #0a8f95;
  font-size: 12px;
  font-weight: 800;
}

.log-item p {
  line-height: 1.55;
  color: #435266;
}

.critic-block {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid #ecf1f7;
}

.critic-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

@media (max-width: 1280px) {
  .workspace-grid {
    grid-template-columns: 330px 1fr;
  }

  .log-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 880px) {
  .hero-band,
  .workspace-grid,
  .slide-area {
    grid-template-columns: 1fr;
  }

  .hero-band {
    display: grid;
    align-items: start;
  }

  .two-col,
  .stage-grid {
    grid-template-columns: 1fr;
  }

  .preview-panel {
    min-height: auto;
  }
}
</style>
