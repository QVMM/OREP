<template>
  <div class="prep-page" :class="`is-${activePrepKey}`">
    <aside class="prep-rail" :class="{ collapsed: railCollapsed }">
      <div class="rail-section-title">项目准备</div>
      <button
        v-for="item in prepNavItems"
        :key="item.key"
        type="button"
        class="rail-item"
        :class="{ active: item.key === activePrepKey }"
        @click="setActivePrepKey(item.key)"
      >
        <span class="rail-icon"><el-icon><component :is="item.icon" /></el-icon></span>
        <span>{{ item.label }}</span>
      </button>

      <button type="button" class="rail-collapse" @click="railCollapsed = !railCollapsed">
        <el-icon><ArrowLeft /></el-icon>
        <span>{{ railCollapsed ? '展开导航' : '收起导航' }}</span>
      </button>
    </aside>

    <div
      class="prep-workbench"
      :class="`mode-${activePrepKey}`"
      :aria-busy="loading ? 'true' : 'false'"
    >
      <section v-if="loadError && !isAiAppPreparation" class="prep-alert">
        <div>
          <strong>准备页数据加载失败</strong>
          <span>{{ loadError }}</span>
        </div>
        <button type="button" @click="loadPrep(activeTeamId)">重试</button>
      </section>

      <AiAppShell
        v-if="isAiAppPreparation"
        mode="landing"
        width="wide"
        class="prep-ai-app-shell"
      >
        <template #header>
          <AiAppHeader
            :app="prepApp"
            mode="landing"
            back-label="AI 应用中心"
            back-to="/ai-apps"
            :title="prepTitle"
            :subtitle="prepSubtitle"
            class="prep-ai-app-header"
          />
        </template>

        <section v-if="loadError" class="prep-alert">
          <div>
            <strong>准备页数据加载失败</strong>
            <span>{{ loadError }}</span>
          </div>
          <button type="button" @click="loadPrep(activeTeamId)">重试</button>
        </section>

        <section class="planning-board">
          <PptWorkspace
            v-if="activePrepKey === 'ppt'"
            :resources="resources"
            :stages="dashboard.stages || []"
            @enter-ppt="router.push('/ppt-editor')"
          />

          <ScriptWorkspace
            v-else
            :scripts="scripts"
            :templates="templates"
            :loading="loading"
            @open-script="openScript"
            @create-blank="createBlankScript"
            @create-from-template="openTemplateDialog"
            @script-action="handleScriptAction"
          />
        </section>
      </AiAppShell>

      <template v-else>
        <section v-if="false && activePrepKey === 'topic'" class="topic-team-panel">
          <div class="team-switcher topic-team-menu">
            <div class="avatar-stack">
              <span v-for="advisor in topicAdvisors.slice(0, 4)" :key="advisor.name" class="mini-avatar" :title="advisor.name">
                {{ advisor.avatar }}
              </span>
            </div>
            <strong>选题团队（{{ topicAdvisors.length }}）</strong>
            <el-dropdown v-if="teams.length > 1" trigger="click" @command="switchTeam">
              <button type="button" class="icon-button"><el-icon><ArrowDown /></el-icon></button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="team in teams" :key="team.id" :command="team.id">
                    {{ team.name }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <small>{{ activeTeamName }}</small>
          </div>

          <button type="button" class="secondary-button" @click="setActivePrepKey('materials')">
            <el-icon><Folder /></el-icon>
            查看团队材料
          </button>
        </section>

        <section class="planning-board">
          <ResourceCenterWorkspace
            v-if="activePrepKey === 'materials'"
            :team-id="activeTeamId"
            :team-name="activeTeamName"
          />

          <RoadshowWorkspace
            v-else-if="activePrepKey === 'roadshow'"
            :roadshow="roadshow"
            :meetings="roadshowMeetings"
            :tasks="tasks"
          />

          <VersionsWorkspace
            v-else
            :documents="documents"
            :scripts="scripts"
            :ai-runs="aiRuns"
            @open-document="openDocument"
          />
        </section>

        <aside v-if="!['materials', 'ppt', 'script', 'topic'].includes(activePrepKey)" class="artifact-panel">
          <ArtifactGroup title="专家团进度" :count="latestAgentSteps.length">
            <ArtifactItem
              v-for="(step, index) in latestAgentSteps.slice(0, 5)"
              :key="step.id || step.agentKey || `${step.agentName || 'agent'}-${index}`"
              :name="step.agentName || '选题专家'"
              :meta="agentStepStatusMeta(step.status)"
              type="doc"
            />
            <EmptyBlock v-if="!latestAgentSteps.length" title="等待专家团" desc="提交选题信息后显示接力过程。" compact />
          </ArtifactGroup>

          <ArtifactGroup title="真实上下文" :count="contextCount">
            <MetricRow label="团队材料" :value="materials.length" />
            <MetricRow label="团队任务" :value="tasks.length" />
            <MetricRow label="讲稿" :value="scripts.length" />
            <MetricRow label="策划文档" :value="documents.length" />
          </ArtifactGroup>

          <ArtifactGroup title="同步团队工作项" :count="prepWorkItemDrafts.length">
            <ArtifactItem
              v-for="item in prepWorkItemDrafts.slice(0, 4)"
              :key="item.id"
              :name="item.title"
              :meta="item.stageKey === 'ROADSHOW' ? '路演准备' : '材料准备'"
              type="orange"
            />
            <EmptyBlock v-if="!prepWorkItemDrafts.length" title="暂无可同步事项" desc="生成材料、策划书或讲稿后可同步成团队工作项。" compact />
          </ArtifactGroup>

          <button type="button" class="sync-button" :disabled="syncingPrepTasks || !activeTeamId || !prepWorkItemDrafts.length" @click="syncPrepWorkItems">
            <el-icon><Connection /></el-icon>
            {{ syncingPrepTasks ? '同步中' : '生成团队工作项' }}
          </button>
          <button v-if="syncedPrepTaskCount" type="button" class="sync-button" @click="goTeamInbox">
            <el-icon><UserFilled /></el-icon>
            查看团队工作项
          </button>

          <ArtifactGroup title="方向草案" :count="directions.length">
            <ArtifactItem
              v-for="direction in directions.slice(0, 4)"
              :key="direction.id"
              :name="direction.title"
              :meta="direction.selected ? '已采纳' : matchText(direction.equipmentMatch)"
              type="orange"
            />
            <EmptyBlock v-if="!directions.length" title="暂无方向" desc="补充真实信息后生成方向池。" compact />
          </ArtifactGroup>

          <ArtifactGroup title="策划书版本" :count="documents.length">
            <ArtifactItem
              v-for="doc in documents.slice(0, 4)"
              :key="doc.id"
              :name="doc.title"
              :meta="formatDate(doc.updatedAt || doc.createdAt)"
              type="word"
            />
            <EmptyBlock v-if="!documents.length" title="暂无策划书" desc="采纳方向后可生成草稿。" compact />
          </ArtifactGroup>

          <button type="button" class="generate-button" :disabled="!selectedDirection || generatingDocument" @click="createDocument(selectedDirection?.id)">
            <el-icon><DocumentAdd /></el-icon>
            生成项目策划书
          </button>
          <button type="button" class="sync-button" @click="setActivePrepKey('versions')">
            <el-icon><Files /></el-icon>
            查看版本沉淀
          </button>
        </aside>
      </template>
    </div>

    <el-dialog v-model="showNewFromTemplate" title="新建讲稿" width="520px">
      <div class="tpl-list">
        <div class="tpl-section-label">
          <strong>从零开始</strong>
          <span>自己搭建章节、角色和讲解步骤</span>
        </div>
        <button
          type="button"
          class="tpl-item blank"
          :disabled="creatingBlankScript"
          @click="createBlankScript"
        >
          <span class="tpl-icon blank">
            <el-icon><DocumentAdd /></el-icon>
          </span>
          <span class="tpl-body">
            <strong>{{ creatingBlankScript ? '正在创建...' : '空白讲稿' }}</strong>
            <small>从一个空章节开始，不预设赛制和内容</small>
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>

        <div class="tpl-section-label template-label">
          <strong>使用模板</strong>
          <span>快速复用成熟的路演结构</span>
        </div>
        <button
          v-for="t in templates"
          :key="t.id"
          type="button"
          class="tpl-item"
          @click="createFromTemplate(t)"
        >
          <span class="tpl-icon" :class="{ default: t.isDefault }">
            <el-icon><Star v-if="t.isDefault" /><Document v-else /></el-icon>
          </span>
          <span class="tpl-body">
            <strong>{{ t.name }}</strong>
            <small v-if="t.description">{{ t.description }}</small>
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>
        <EmptyBlock v-if="!templates.length" title="暂无模板" desc="当前没有可用讲稿模板。" />
      </div>
    </el-dialog>

    <el-dialog v-model="showSaveAsTemplate" title="另存为模板" width="420px">
      <el-form label-width="70px">
        <el-form-item label="名称">
          <el-input v-model="newTemplateName" placeholder="模板名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newTemplateDesc" type="textarea" :rows="2" placeholder="简要描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="showSaveAsTemplate = false">取消</el-button>
        <el-button type="primary" round @click="confirmSaveAsTemplate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDocumentPreview" :title="documentPreview?.title || '策划书草稿'" width="720px">
      <article class="document-preview">
        <pre>{{ documentPreview?.content || '暂无正文内容' }}</pre>
      </article>
      <template #footer>
        <el-button round @click="showDocumentPreview = false">关闭</el-button>
        <el-button type="primary" round @click="setActivePrepKey('versions'); showDocumentPreview = false">查看版本</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import FilePreview from '../components/FilePreview.vue'
import DropFileUpload from '../components/base/DropFileUpload.vue'
import AiAppHeader from '../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../components/ai-apps/AiAppShell.vue'
import ResourceCenterWorkspace from '../components/resource-center/ResourceCenterWorkspace.vue'
import { authHeadersForMedia, withAuthMediaUrl } from '../utils/mediaUrl'
import { createRequestLifecycle, createSerialPoller } from '../utils/requestLifecycle.js'

/** 离开资源中心再进入：记住上次团队，减少 bootstrap 前的空闪 */
const scriptListTeamCache = {
  teamId: null,
  teamName: '',
}
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Briefcase,
  Check,
  Clock,
  Collection,
  Connection,
  Document,
  DocumentAdd,
  Files,
  Folder,
  MagicStick,
  MoreFilled,
  Promotion,
  Star,
  Tickets,
  UserFilled,
  VideoCamera
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activePrepKey = ref(route.meta.defaultPrepTab === 'materials' ? 'materials' : 'script')
const railCollapsed = ref(false)
const loading = ref(false)
const submittingPrompt = ref(false)
const generatingDocument = ref(false)
const taskGeneratingDirectionId = ref(null)
const documentGeneratingDirectionId = ref(null)
const loadError = ref('')
const teams = ref([])
/** 模块级缓存：离开再进资源中心时减少「无团队」空闪 */
const activeTeamId = ref(scriptListTeamCache.teamId)
const dashboard = ref({})
const prepSession = ref(null)
const resources = ref([])
const scripts = ref([])
const templates = ref([])
const promptText = ref('')
const showNewFromTemplate = ref(false)
const creatingBlankScript = ref(false)
const showSaveAsTemplate = ref(false)
const showDocumentPreview = ref(false)
const documentPreview = ref(null)
const newTemplateName = ref('')
const newTemplateDesc = ref('')
const savingScript = ref(null)
const syncingPrepTasks = ref(false)
const syncedPrepTaskCount = ref(0)
const prepRequestLifecycle = createRequestLifecycle()
let prepRouteMounted = false

const isAiAppPreparation = computed(() => (
  route.path === '/script-editor'
  && (activePrepKey.value === 'script' || activePrepKey.value === 'ppt')
))
const prepApp = computed(() => (activePrepKey.value === 'ppt' ? 'ppt' : 'script'))
const prepTitle = computed(() => (activePrepKey.value === 'ppt' ? 'PPT 制作' : '讲稿制作'))
const prepSubtitle = computed(() => (
  activePrepKey.value === 'ppt'
    ? '准备路演 PPT'
    : '创建、继续编辑和管理讲稿'
))

const prepNavItems = [
  { key: 'materials', label: '材料库', icon: Folder },
  { key: 'ppt', label: 'PPT 准备', icon: Collection },
  { key: 'script', label: '讲稿制作', icon: Document },
  { key: 'roadshow', label: '路演准备', icon: VideoCamera },
  { key: 'versions', label: '版本记录', icon: Files }
]
const prepNavKeys = prepNavItems.map((item) => item.key)

watch(
  () => [route.path, route.query.tab, route.meta.defaultPrepTab],
  ([, tab, defaultPrepTab], previousRouteState = []) => {
    const fallbackKey = prepNavKeys.includes(defaultPrepTab) ? defaultPrepTab : 'script'
    const nextKey = typeof tab === 'string' && prepNavKeys.includes(tab) ? tab : fallbackKey
    if (activePrepKey.value !== nextKey) activePrepKey.value = nextKey
    if (prepRouteMounted && previousRouteState.length) restartPrepLifecycle()
  },
  { immediate: true }
)

function setActivePrepKey(key) {
  activePrepKey.value = key
  if (key === 'materials') {
    const query = { ...route.query }
    delete query.tab
    router.replace({ path: '/resource-center', query })
    return
  }
  router.replace({ path: '/script-editor', query: { ...route.query, tab: key } })
}

function restartPrepLifecycle() {
  prepRequestLifecycle.invalidate()
  runPoller.stop()
  prepRequestLifecycle.activate()
  loadPrep(activeTeamId.value)
}

const topicAdvisors = [
  {
    name: '赵选题',
    role: '选题顾问',
    focus: '追问赛道与学校资源，收敛方向',
    avatar: '赵',
    active: true
  },
  {
    name: '李政策',
    role: '政策研究员',
    focus: '检索公开政策与专项要求',
    avatar: '政'
  },
  {
    name: '张调研',
    role: '行业调研员',
    focus: '汇总行业需求、产品案例和用户痛点',
    avatar: '研'
  },
  {
    name: '周可行',
    role: '可行性分析师',
    focus: '评估设备、周期、材料和展示难度',
    avatar: '行'
  },
  {
    name: '刘主编',
    role: '策划书主编',
    focus: '形成项目策划书与路演亮点',
    avatar: '编'
  }
]

const activeTeam = computed(() => {
  const fromDashboard = dashboard.value?.team
  if (fromDashboard?.id) return fromDashboard
  return teams.value.find(team => Number(team.id) === Number(activeTeamId.value)) || null
})
const activeTeamName = computed(() => (
  activeTeam.value?.name || scriptListTeamCache.teamName || '暂无团队'
))
const visibleMembers = computed(() => dashboard.value?.members || [])
const materials = computed(() => dashboard.value?.materials || [])
const tasks = computed(() => dashboard.value?.tasks || [])
const stages = computed(() => dashboard.value?.stages || [])
const roadshow = computed(() => dashboard.value?.roadshow || {})
const roadshowMeetings = computed(() => dashboard.value?.roadshowMeetings || [])
const messages = computed(() => Array.isArray(prepSession.value?.messages) ? prepSession.value.messages : [])
const directions = computed(() => Array.isArray(prepSession.value?.directions) ? prepSession.value.directions : [])
const documents = computed(() => Array.isArray(prepSession.value?.documents) ? prepSession.value.documents : [])
const generationGroups = computed(() => Array.isArray(prepSession.value?.generationGroups) ? prepSession.value.generationGroups : [])
const aiRuns = computed(() => prepSession.value?.latestRun ? [prepSession.value.latestRun] : [])
const latestRun = computed(() => prepSession.value?.latestRun || null)
const runPoller = createSerialPoller(
  () => refreshSession(prepRequestLifecycle.currentGeneration()),
  {
    delay: 2500,
    setTimer: (callback, delay) => window.setTimeout(callback, delay),
    clearTimer: timer => window.clearTimeout(timer),
    shouldRun: () => (
      prepRequestLifecycle.isActive()
      && latestRun.value?.status === 'RUNNING'
      && Boolean(prepSession.value?.id)
    ),
  },
)
const latestAgentSteps = computed(() => Array.isArray(latestRun.value?.agentSteps)
  ? latestRun.value.agentSteps.filter(step => step && typeof step === 'object' && !Array.isArray(step))
  : [])
const selectedDirection = computed(() => directions.value.find(direction => direction.selected) || null)
const contextCount = computed(() => materials.value.length + tasks.value.length + scripts.value.length + documents.value.length)
const prepWorkItemDrafts = computed(() => {
  const materialDrafts = materials.value.slice(0, 3).map((item, index) => ({
    id: `material-${item.id || index}`,
    title: `确认项目材料：${item.name || item.title || `材料 ${index + 1}`}`,
    description: `来源：准备页材料库\n材料类型：${materialTypeText(item.materialType || item.sourceType || item.type || '团队材料')}\n处理要求：确认真实性、可引用范围，并标记是否可进入 PPT/讲稿。`,
    stageKey: 'MATERIAL',
    priority: String(item.reviewStatus || item.status || '').includes('待') ? 'HIGH' : 'MEDIUM'
  }))
  const documentDrafts = documents.value.slice(0, 2).map((item, index) => ({
    id: `document-${item.id || index}`,
    title: `审核策划书版本：${item.title || `策划书 ${index + 1}`}`,
    description: `来源：准备页版本记录\n处理要求：队长确认该版本是否作为下一轮 PPT/讲稿输入。`,
    stageKey: 'MATERIAL',
    priority: index === 0 ? 'HIGH' : 'MEDIUM'
  }))
  const scriptDrafts = scripts.value.slice(0, 2).map((item, index) => ({
    id: `script-${item.id || index}`,
    title: `同步讲稿修改：${item.title || `讲稿 ${index + 1}`}`,
    description: `来源：准备页讲稿制作\n处理要求：确认讲稿是否匹配最新 PPT 和评分反馈，必要时分配成员重写。`,
    stageKey: 'ROADSHOW',
    priority: 'MEDIUM'
  }))
  return [...materialDrafts, ...documentDrafts, ...scriptDrafts].slice(0, 6)
})

const EmptyBlock = defineComponent({
  name: 'EmptyBlock',
  props: {
    title: { type: String, required: true },
    desc: { type: String, default: '' },
    compact: { type: Boolean, default: false }
  },
  setup(props) {
    return () => h('div', { class: ['empty-block', { compact: props.compact }] }, [
      h('strong', props.title),
      props.desc ? h('small', props.desc) : null
    ])
  }
})

const ArtifactGroup = defineComponent({
  name: 'ArtifactGroup',
  props: {
    title: { type: String, required: true },
    count: { type: [String, Number], default: '' }
  },
  setup(props, { slots }) {
    return () => h('section', { class: 'artifact-group' }, [
      h('div', { class: 'artifact-title' }, [
        h('strong', props.title),
        props.count !== '' ? h('span', props.count) : null
      ]),
      slots.default?.()
    ])
  }
})

const ArtifactItem = defineComponent({
  name: 'ArtifactItem',
  props: {
    name: { type: String, required: true },
    meta: { type: String, default: '' },
    type: { type: String, default: 'doc' }
  },
  setup(props) {
    return () => h('div', { class: 'artifact-item' }, [
      h('span', { class: ['doc-icon', props.type] }, iconLabel(props.type)),
      h('span', { class: 'artifact-copy' }, [
        h('strong', props.name),
        props.meta ? h('small', props.meta) : null
      ])
    ])
  }
})

const MetricRow = defineComponent({
  name: 'MetricRow',
  props: {
    label: { type: String, required: true },
    value: { type: Number, default: 0 }
  },
  setup(props) {
    return () => h('div', { class: 'metric-row' }, [
      h('span', props.label),
      h('strong', String(props.value))
    ])
  }
})

const TopicWorkspace = defineComponent({
  name: 'TopicWorkspace',
  components: { EmptyBlock },
  props: {
    session: { type: Object, default: null },
    messages: { type: Array, default: () => [] },
    directions: { type: Array, default: () => [] },
    generationGroups: { type: Array, default: () => [] },
    latestRun: { type: Object, default: null },
    promptText: { type: String, default: '' },
    submitting: { type: Boolean, default: false },
    taskLoadingId: { type: [String, Number], default: null },
    documentLoadingId: { type: [String, Number], default: null },
    advisors: { type: Array, default: () => [] }
  },
  emits: ['update:promptText', 'send', 'retry', 'selectDirection', 'createTasks', 'createDocument'],
  setup(props, { emit }) {
    const evidenceOpen = ref(false)
    const directionOpen = ref(false)
    const mainScrollRef = ref(null)
    const typedMessageKey = ref('')
    const typedText = ref('')
    let typingTimer = null
    const asArray = value => Array.isArray(value) ? value : []
    const safeMessages = () => asArray(props.messages)
    const safeDirections = () => asArray(props.directions)
    const lastUserMessage = () => [...safeMessages()].reverse().find(message => message.role === 'USER')?.content || ''
    const aiRunning = () => props.submitting || props.latestRun?.status === 'RUNNING'
    const selectedDirection = () => safeDirections().find(direction => direction.selected) || null
    const otherDirections = () => safeDirections().filter(direction => !direction.selected).slice(0, 3)
    const pendingUserText = () => props.submitting ? String(props.promptText || '').trim() : ''
    const genericAgents = [
      { name: '赵选题', role: '选题顾问', focus: '判断赛道、团队信息和方向边界' },
      { name: '李政策', role: '政策研究员', focus: '补充公开政策、赛项要求和专项趋势' },
      { name: '张调研', role: '行业调研员', focus: '查行业案例、用户痛点和竞品证据' },
      { name: '周可行', role: '可行性分析师', focus: '评估设备、数据、周期和展示难度' },
      { name: '刘主编', role: '策划书主编', focus: '整理为方向池、任务和策划书结构' }
    ]
    const defaultAgentSteps = () => (asArray(props.advisors).length ? asArray(props.advisors) : genericAgents).map((advisor, index) => ({
      id: `default-${index}`,
      agentKey: advisor.name || `agent-${index + 1}`,
      agentName: advisor.name || '选题专家',
      agentRole: advisor.role || '选题专家',
      status: aiRunning() && index === 0 ? 'RUNNING' : 'PENDING',
      inputSummary: advisor.focus || '等待本轮选题输入',
      outputSummary: '等待专家判断',
      findings: [],
      questions: [],
      sources: []
    }))
    const visibleAgentSteps = () => {
      const steps = asArray(props.latestRun?.agentSteps).filter(step => step && typeof step === 'object' && !Array.isArray(step))
      return steps.length ? steps : defaultAgentSteps()
    }
    const agentStepClass = status => String(status || 'PENDING').toLowerCase()
    const agentStatusText = status => {
      const value = String(status || 'PENDING').toUpperCase()
      if (value === 'COMPLETED') return '完成'
      if (value === 'RUNNING') return '进行中'
      if (value === 'FAILED') return '失败'
      return '等待'
    }
    const scoreLabel = key => ({
      competitionFit: '赛项匹配',
      resourceFit: '资源匹配',
      innovation: '创新表达',
      demoReadiness: '展示闭环',
      riskControl: '风险可控'
    }[key] || key)
    const scoreEntries = scores => Object.entries(scores || {}).filter(([, value]) => Number(value) > 0)
    const recommendationValue = level => String(level || 'UNKNOWN').toUpperCase()
    const recommendationClass = level => recommendationValue(level).toLowerCase()
    const recommendationText = level => ({
      STRONGLY_RECOMMENDED: '强烈推荐',
      RECOMMENDED: '优先推荐',
      OPTIONAL: '可选方向',
      NOT_RECOMMENDED: '暂不推荐',
      UNKNOWN: '待判断',
      CANDIDATE: '可选方向',
      BACKUP: '备用方向'
    }[recommendationValue(level)] || '待判断')
    const assistantMessageKey = message => `${message.id || message.createdAt || ''}:${message.content || ''}`
    const messageKey = (message, index) => message.id || assistantMessageKey(message) || `message-${index}`
    const directionKey = (direction, index) => direction.id || `${direction.generationNo || 1}:${direction.title || index}`
    const stepKey = (step, index) => step.id || step.agentKey || `${step.agentName || 'agent'}-${index}`
    const latestAssistantMessage = () => [...safeMessages()].reverse().find(message => message.role !== 'USER') || null
    const messageText = message => {
      const isLatestAssistant = message.role !== 'USER' && assistantMessageKey(message) === typedMessageKey.value
      return isLatestAssistant ? typedText.value : message.content
    }
    const startTyping = message => {
      if (typingTimer) window.clearInterval(typingTimer)
      const fullText = String(message?.content || '')
      typedMessageKey.value = assistantMessageKey(message)
      typedText.value = ''
      let index = 0
      typingTimer = window.setInterval(() => {
        index += fullText.length > 220 ? 5 : 3
        typedText.value = fullText.slice(0, index)
        if (index >= fullText.length) {
          typedText.value = fullText
          window.clearInterval(typingTimer)
          typingTimer = null
        }
      }, 22)
    }
    const scrollToLatest = () => {
      window.setTimeout(() => {
        const el = mainScrollRef.value
        if (el) el.scrollTop = el.scrollHeight
      }, 0)
    }
    watch(
      () => safeMessages().map(message => `${message.role}:${assistantMessageKey(message)}`).join('|'),
      () => {
        const latestAssistant = latestAssistantMessage()
        scrollToLatest()
        if (!latestAssistant) return
        const key = assistantMessageKey(latestAssistant)
        if (!typedMessageKey.value) {
          typedMessageKey.value = key
          typedText.value = latestAssistant.content || ''
          return
        }
        if (key !== typedMessageKey.value) {
          startTyping(latestAssistant)
        }
      },
      { immediate: true }
    )
    watch(
      () => [props.submitting, safeMessages().length, props.latestRun?.status].join('|'),
      () => scrollToLatest()
    )
    onBeforeUnmount(() => {
      if (typingTimer) window.clearInterval(typingTimer)
    })
    const sourceNode = sourceValue => {
      const source = sourceValue && typeof sourceValue === 'object' ? sourceValue : {}
      const label = source.title || source.url || '来源'
      const children = [h('b', sourceTypeText(source.sourceType)), label]
      return source.url
        ? h('a', { key: source.key || source.url || source.title, href: source.url, target: '_blank', rel: 'noreferrer' }, children)
        : h('span', { key: source.key || source.title || label }, children)
    }
    return () => h('div', { class: 'workspace-shell topic-shell' }, [
      h('div', { class: 'board-header' }, [
        h('div', [
          h('h1', props.session?.title || '选题策划'),
          h('p', props.session ? `会话状态：${statusText(props.session.status)}` : '等待真实团队上下文')
        ]),
        props.latestRun ? h('span', { class: ['run-pill', runClass(props.latestRun.status)] }, runStatusText(props.latestRun.status)) : null
      ]),
      h('div', { class: 'topic-main-scroll', ref: mainScrollRef }, [
        h('section', { class: 'agent-chain-panel' }, [
          h('div', { class: 'section-heading' }, [
            h('div', [h('strong', '选题专家团接力'), h('span', '每位专家只负责一个判断维度')])
          ]),
          h('div', { class: 'agent-chain-list' }, visibleAgentSteps().map((step, index) => h('article', { class: ['agent-step-card', agentStepClass(step.status)], key: stepKey(step, index) }, [
            h('span', { class: 'agent-step-index' }, String(index + 1)),
            h('div', { class: 'agent-step-body' }, [
              h('div', { class: 'agent-step-head' }, [
                h('strong', step.agentName || '选题专家'),
                h('span', step.agentRole || '专家'),
                h('em', agentStatusText(step.status))
              ]),
              h('p', step.outputSummary || step.inputSummary || '等待专家判断'),
              asArray(step.findings).length ? h('ul', asArray(step.findings).slice(0, 2).map((item, itemIndex) => h('li', { key: `${stepKey(step, index)}-finding-${itemIndex}` }, item))) : null,
              asArray(step.questions).length ? h('div', { class: 'agent-question-row' }, asArray(step.questions).slice(0, 2).map((item, itemIndex) => h('span', { key: `${stepKey(step, index)}-question-${itemIndex}` }, item))) : null
            ])
          ])))
        ]),
        h('div', { class: 'chat-stream' }, [
          safeMessages().length || pendingUserText() || aiRunning()
            ? [
                ...safeMessages().map((message, index) => h('div', { class: ['chat-row', message.role === 'USER' ? 'mine' : '', message.role !== 'USER' && assistantMessageKey(message) === typedMessageKey.value && typingTimer ? 'typing' : ''], key: messageKey(message, index) }, [
                h('span', { class: ['chat-avatar', message.role === 'USER' ? '' : 'ai'] }, message.role === 'USER' ? '我' : 'AI'),
                h('div', { class: 'chat-content' }, [
                  h('div', { class: 'chat-meta' }, [message.role === 'USER' ? '用户补充' : 'AI 选题策划', h('span', formatDate(message.createdAt))]),
                  h('p', messageText(message))
                ])
              ])),
                pendingUserText()
                  ? h('div', { class: 'chat-row mine pending' }, [
                      h('span', { class: 'chat-avatar' }, '我'),
                      h('div', { class: 'chat-content' }, [
                        h('div', { class: 'chat-meta' }, ['用户补充', h('span', '刚刚')]),
                        h('p', pendingUserText())
                      ])
                    ])
                  : null,
                aiRunning()
                  ? h('div', { class: 'chat-row ai-thinking' }, [
                      h('span', { class: 'chat-avatar ai' }, 'AI'),
                      h('div', { class: 'chat-content' }, [
                        h('div', { class: 'chat-meta' }, ['选题团队', h('span', '正在接力')]),
                        h('p', [
                          h('strong', currentAgentName(props.latestRun, props.submitting, props.promptText)),
                          h('span', '正在阅读材料并组织回复'),
                          h('i')
                        ])
                      ])
                    ])
                  : null
              ]
            : h(EmptyBlock, { title: '还没有选题对话', desc: '先补充赛项、设备条件、团队基础或已有想法。' })
        ]),
        props.latestRun?.status === 'FAILED'
          ? h('div', { class: 'ai-failure' }, [
              h('div', [
                h('strong', '选题专家团生成失败'),
                h('span', props.latestRun.errorMessage || 'AI 服务暂时不可用，已保留你的输入，可以直接重试。')
              ]),
              h('button', { type: 'button', disabled: props.submitting, onClick: () => emit('retry', lastUserMessage()) }, '重试')
            ])
          : null,
        props.latestRun?.researchSummary || asArray(props.latestRun?.questions).length || asArray(props.latestRun?.sources).length
          ? h('section', { class: ['evidence-panel', { collapsed: !evidenceOpen.value }] }, [
              h('div', { class: 'evidence-heading' }, [
                h('div', [
                  h('strong', '本轮依据'),
                  !evidenceOpen.value && props.latestRun?.researchSummary
                    ? h('span', compactText(props.latestRun.researchSummary, 42))
                    : null
                ]),
                h('button', { type: 'button', onClick: () => { evidenceOpen.value = !evidenceOpen.value } }, evidenceOpen.value ? '收起' : '展开')
              ]),
              evidenceOpen.value
                ? [
                    props.latestRun?.researchSummary ? h('p', props.latestRun.researchSummary) : null,
                    asArray(props.latestRun?.questions).length
                      ? h('div', { class: 'evidence-list' }, [
                          h('small', '还需要补充'),
                          ...asArray(props.latestRun?.questions).slice(0, 4).map((question, index) => h('span', { key: `question-${index}` }, question))
                        ])
                      : null,
                    asArray(props.latestRun?.sources).length
                      ? h('div', { class: 'source-row' }, asArray(props.latestRun?.sources).slice(0, 5).map((source, index) => sourceNode({ ...(source && typeof source === 'object' ? source : {}), key: source?.url || source?.title || `source-${index}` })))
                      : null
                  ]
                : null
            ])
          : null,
        h('section', { class: ['direction-section', { collapsed: !directionOpen.value }] }, [
          h('div', { class: 'section-heading' }, [
            h('div', [h('strong', '方向池'), h('span', `（${safeDirections().length} 个）真实材料与团队推理`)]),
            h('button', { type: 'button', class: 'section-toggle', onClick: () => { directionOpen.value = !directionOpen.value } }, directionOpen.value ? '收起' : '展开全部')
          ]),
          selectedDirection()
            ? h('article', { class: 'current-direction-card' }, [
                h('span', { class: 'doc-icon orange' }, '签'),
                h('div', [
                  h('strong', selectedDirection().title),
                  h('small', `已采纳 · 设备匹配 ${matchText(selectedDirection().equipmentMatch)} · 赛项匹配 ${matchText(selectedDirection().competitionMatch)}`)
                ]),
                h('button', { type: 'button', onClick: () => emit('createDocument', selectedDirection().id) }, '生成草稿')
              ])
            : null,
          safeDirections().length
            ? directionOpen.value
              ? h('div', { class: 'direction-grid' }, safeDirections().map((direction, index) => h('article', { class: ['direction-card', { selected: direction.selected }], key: directionKey(direction, index) }, [
                  direction.selected ? h('span', { class: 'selected-corner' }, [h(Check)]) : null,
                  h('em', { class: 'generation-badge' }, `第 ${direction.generationNo || 1} 轮`),
                  h('strong', direction.title),
                  h('div', { class: 'tag-row' }, asArray(direction.tags).slice(0, 3).map((tag, tagIndex) => h('span', { key: `${directionKey(direction, index)}-tag-${tagIndex}` }, tag))),
                  h('p', direction.summary || '暂无摘要'),
                  h('small', `设备匹配：${matchText(direction.equipmentMatch)} · 赛项匹配：${matchText(direction.competitionMatch)}`),
                  direction.recommendationLevel ? h('span', { class: ['recommendation-pill', recommendationClass(direction.recommendationLevel)] }, recommendationText(direction.recommendationLevel)) : null,
                  direction.expertRationale ? h('p', { class: 'expert-rationale' }, direction.expertRationale) : null,
                  scoreEntries(direction.scores).length ? h('div', { class: 'score-matrix' }, scoreEntries(direction.scores).map(([key, value]) => h('div', { class: 'score-cell', key: `${directionKey(direction, index)}-score-${key}` }, [
                    h('span', scoreLabel(key)),
                    h('strong', `${value}/10`)
                  ]))) : null,
                  asArray(direction.evidenceGaps).length ? h('ul', { class: 'gap-list' }, asArray(direction.evidenceGaps).slice(0, 2).map((gap, gapIndex) => h('li', { key: `${directionKey(direction, index)}-gap-${gapIndex}` }, gap))) : null,
                  asArray(direction.risks).length ? h('div', { class: 'detail-strip' }, [h('b', '风险'), h('span', asArray(direction.risks).slice(0, 2).join('；'))]) : null,
                  asArray(direction.nextTasks).length ? h('div', { class: 'detail-strip' }, [h('b', '任务'), h('span', asArray(direction.nextTasks).slice(0, 2).map(task => task.title || task.name || '待补任务').join('；'))]) : null,
                  asArray(direction.researchRefs).length
                    ? h('div', { class: 'source-row compact' }, asArray(direction.researchRefs).slice(0, 3).map((ref, refIndex) => sourceNode({ ...(ref && typeof ref === 'object' ? ref : {}), key: ref?.url || ref?.title || `${directionKey(direction, index)}-ref-${refIndex}` })))
                    : null,
                  h('div', { class: 'card-actions' }, [
                    h('button', {
                      type: 'button',
                      disabled: direction.selected,
                      onClick: () => {
                        emit('update:promptText', directionIntentText(direction))
                        emit('selectDirection', direction.id)
                      }
                    }, direction.selected ? '已采纳' : '选这个'),
                    h('button', { type: 'button', disabled: props.taskLoadingId === direction.id, onClick: () => emit('createTasks', direction.id) }, props.taskLoadingId === direction.id ? '生成中' : '生成任务'),
                    h('button', { type: 'button', disabled: props.documentLoadingId === direction.id, onClick: () => emit('createDocument', direction.id) }, props.documentLoadingId === direction.id ? '生成中' : '生成草稿')
                  ])
                ])))
              : h('div', { class: 'candidate-strip' }, otherDirections().map((direction, index) => h('button', {
                  type: 'button',
                  key: directionKey(direction, index),
                  onClick: () => {
                    emit('update:promptText', directionIntentText(direction))
                    emit('selectDirection', direction.id)
                  }
                }, [
                  h('strong', direction.title),
                  h('small', `${matchText(direction.equipmentMatch)} / ${matchText(direction.competitionMatch)}`)
                ])))
            : h(EmptyBlock, { title: '暂无方向池', desc: '输入补充信息后，系统会生成带证据缺口和任务建议的方向。' })
        ])
      ]),
      h('div', { class: 'prompt-box' }, [
        h('input', {
          value: props.promptText,
          disabled: props.submitting || aiRunning() || !props.session,
          placeholder: aiRunning() ? '选题团队正在协作，请稍候...' : (props.session ? '点击方向卡片的“选这个”，或补充赛项、设备条件、已有想法...' : '暂无可用会话'),
          onInput: event => emit('update:promptText', event.target.value),
          onKeydown: event => {
            if (event.key === 'Enter') emit('send')
          }
        }),
        h('button', { type: 'button', disabled: props.submitting || aiRunning() || !props.session, 'aria-label': '发送', onClick: () => emit('send') }, [
          h(Promotion)
        ])
      ]),
      h('p', { class: 'ai-note' }, 'AI 会区分已确认材料、用户输入、公开资料与团队推理；请结合实际材料判断。')
    ])
  }
})

const MaterialsWorkspace = defineComponent({
  name: 'MaterialsWorkspace',
  props: { materials: Array, resources: Array, loading: Boolean },
  emits: ['refresh'],
  setup(props, { emit }) {
    const activeFilter = ref('all')
    const activeId = ref(null)
    const previewVisible = ref(false)
    const previewUrl = ref('')
    const previewName = ref('')
    const previewType = ref('')
    const unavailableIds = ref(new Set())
    const customCategories = ref([])
    const finderQuery = ref('')
    const detailExpanded = ref(false)
    const showUploadDialog = ref(false)
    const showCategoryDialog = ref(false)
    const uploadFile = ref(null)
    const uploadCategory = ref('team')
    const uploadBusy = ref(false)
    const categoryName = ref('')
    const categoryBusy = ref(false)
    const allMaterials = () => normalizeMaterials(props.materials || [], props.resources || [])
    const recentlyUsedMaterials = () => [...allMaterials()].slice(0, 8)
    const categoryDefinitions = () => [
      ...materialCategories,
      ...customCategories.value.map(category => ({
        key: category.key,
        label: category.label,
        icon: Folder,
        custom: true
      }))
    ]
    const filteredMaterials = () => {
      let list = allMaterials()
      if (activeFilter.value === 'recent') list = recentlyUsedMaterials()
      else if (activeFilter.value === 'verified') list = list.filter(item => item.factStatus === '可直接使用')
      else if (activeFilter.value === 'pending') list = list.filter(item => item.factStatus === '待确认来源' || item.analysisStatus !== '已解析')
      else if (activeFilter.value !== 'all') list = list.filter(item => item.category === activeFilter.value)
      const query = finderQuery.value.trim().toLowerCase()
      if (!query) return list
      return list.filter(item => [
        item.name,
        item.typeLabel,
        item.factStatus,
        item.analysisStatus,
        item.summary,
        item.quote,
        item.risk,
        ...(item.usage || [])
      ].some(value => String(value || '').toLowerCase().includes(query)))
    }
    const selectedMaterial = () => filteredMaterials().find(item => item.id === activeId.value) || null
    const favoriteCount = () => allMaterials().filter(item => item.factStatus === '可直接使用').length
    const recentCount = () => Math.min(allMaterials().length, 8)
    const currentFolderMeta = () => {
      const list = filteredMaterials()
      const pending = list.filter(item => item.factStatus === '待确认来源' || item.analysisStatus !== '已解析').length
      return `${list.length} 个项目${pending ? `，${pending} 个待处理` : ''}`
    }
    const categoryItems = () => categoryDefinitions().map(category => ({
      ...category,
      count: category.key === 'all'
        ? allMaterials().length
        : category.key === 'pending'
          ? allMaterials().filter(item => item.factStatus === '待确认来源' || item.analysisStatus !== '已解析').length
        : allMaterials().filter(item => item.category === category.key).length
    }))
    const tableHeader = () => h('div', { class: 'finder-table__header' }, [
      h('span', '文件名称'),
      h('span', '状态'),
      h('span', '使用范围'),
      h('span', '更新时间'),
      h('span', '操作')
    ])
    const loadingTable = () => h('div', {
      class: 'finder-table finder-table--loading',
      'aria-label': '文件列表加载中',
      'aria-live': 'polite'
    }, [
      tableHeader(),
      ...Array.from({ length: 5 }, (_, index) => h('div', {
        class: 'finder-table__item',
        key: `loading-${index}`,
        'aria-hidden': 'true'
      }, [
        h('article', { class: 'finder-row finder-row--skeleton' }, [
          h('span', { class: 'finder-skeleton finder-skeleton--name' }),
          h('span', { class: 'finder-skeleton finder-row__status' }),
          h('span', { class: 'finder-skeleton finder-row__usage' }),
          h('span', { class: 'finder-skeleton finder-row__date' }),
          h('span', { class: 'finder-skeleton finder-row__actions' })
        ])
      ]))
    ])
    const setFilter = key => {
      activeFilter.value = key
      activeId.value = null
      detailExpanded.value = false
    }
    const activeFilterTitle = () => categoryDefinitions().find(category => category.key === activeFilter.value)?.label || '全部材料'
    const finderLocationTitle = () => ({
      all: '全部文件',
      pending: '待处理',
      recent: '最近使用',
      verified: '已确认'
    }[activeFilter.value] || activeFilterTitle())
    const toggleMaterialDetails = item => {
      const isCurrentDetailOpen = activeId.value === item.id && detailExpanded.value
      activeId.value = isCurrentDetailOpen ? null : item.id
      detailExpanded.value = !isCurrentDetailOpen
    }
    const loadMaterialCategories = async () => {
      try {
        const res = await request.get('/api/ppt-template/categories')
        if (res?.code === 200) customCategories.value = Array.isArray(res.data) ? res.data : []
      } catch (error) {
        customCategories.value = []
      }
    }
    const openUploadDialog = () => {
      uploadFile.value = null
      uploadCategory.value = activeFilter.value && !['all', 'pending'].includes(activeFilter.value) ? activeFilter.value : 'team'
      showUploadDialog.value = true
    }
    const submitUpload = async () => {
      if (!uploadFile.value) {
        ElMessage.warning('请先选择要上传的文件')
        return
      }
      uploadBusy.value = true
      try {
        const form = new FormData()
        form.append('file', uploadFile.value)
        form.append('category', uploadCategory.value || 'public')
        const res = await request.post('/api/ppt-template/upload', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000
        })
        if (res?.code === 200) {
          ElMessage.success('材料已上传并入库')
          showUploadDialog.value = false
          activeFilter.value = uploadCategory.value || 'public'
          emit('refresh')
        }
      } finally {
        uploadBusy.value = false
      }
    }
    const createMaterialCategory = async () => {
      const label = categoryName.value.trim()
      if (!label) {
        ElMessage.warning('请输入分类名称')
        return
      }
      categoryBusy.value = true
      try {
        const res = await request.post('/api/ppt-template/categories', { label })
        if (res?.code === 200) {
          ElMessage.success('分类已创建')
          categoryName.value = ''
          showCategoryDialog.value = false
          await loadMaterialCategories()
          if (res.data?.key) {
            activeFilter.value = res.data.key
            uploadCategory.value = res.data.key
          }
        }
      } finally {
        categoryBusy.value = false
      }
    }
    const markUnavailable = item => {
      unavailableIds.value = new Set([...unavailableIds.value, item.id])
    }
    const isUnavailable = item => unavailableIds.value.has(item.id)
    const cleanupPreviewBlob = () => {
      if (previewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = ''
      previewName.value = ''
      previewType.value = ''
    }
    const fetchMaterialDownloadBlob = async item => {
      const url = materialDownloadUrl(item) || materialPreviewUrl(item)
      if (!url) throw new Error('NO_FILE_URL')
      const normalized = normalizeMaterialUrl(url)
      const response = await fetch(withAuthMediaUrl(normalized), {
        headers: authHeadersForMedia(normalized)
      })
      if (response.status === 404) {
        markUnavailable(item)
        throw new Error('FILE_NOT_FOUND')
      }
      if (response.status === 401 || response.status === 403) throw new Error('FILE_FORBIDDEN')
      if (!response.ok) throw new Error('FILE_REQUEST_FAILED')
      return await response.blob()
    }
    const openExternalMaterialLink = item => {
      const url = materialExternalUrl(item)
      if (!url) {
        ElMessage.warning('这条外部链接缺少地址')
        return
      }
      window.open(url, '_blank', 'noopener,noreferrer')
    }
    const previewMaterial = async item => {
      if (isExternalMaterialLink(item)) {
        openExternalMaterialLink(item)
        return
      }
      if (!canInlinePreviewMaterial(item)) {
        await downloadMaterial(item)
        return
      }
      if (isUnavailable(item)) {
        ElMessage.warning('源文件缺失，暂时无法在线查看')
        return
      }
      const url = materialPreviewUrl(item) || materialDownloadUrl(item)
      if (!url) {
        ElMessage.warning('这份材料暂时没有可在线查看的文件地址')
        return
      }
      cleanupPreviewBlob()
      previewUrl.value = normalizeMaterialUrl(url)
      previewName.value = item.name || '材料预览'
      previewType.value = materialMimeType(item)
      previewVisible.value = true
    }
    const downloadMaterial = async item => {
      if (isExternalMaterialLink(item)) {
        openExternalMaterialLink(item)
        return
      }
      if (isUnavailable(item)) {
        ElMessage.warning('源文件缺失，暂时无法下载')
        return
      }
      try {
        const blob = await fetchMaterialDownloadBlob(item)
        const blobUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = blobUrl
        link.download = item.name || 'material'
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
      } catch (error) {
        const messages = {
          NO_FILE_URL: '这份材料暂时没有可下载的文件地址',
          FILE_NOT_FOUND: '源文件缺失，暂时无法下载',
          FILE_FORBIDDEN: '登录状态异常，请重新登录后再试'
        }
        ElMessage.warning(messages[error.message] || '文件下载失败，请稍后重试')
      }
    }
    onBeforeUnmount(cleanupPreviewBlob)
    const closePreview = visible => {
      previewVisible.value = visible
      if (!visible) cleanupPreviewBlob()
    }
    onMounted(loadMaterialCategories)
    return () => h('div', { class: 'finder-shell' }, [
      h('header', { class: 'finder-toolbar' }, [
        h('div', { class: 'finder-title' }, [
          h('h1', '资源中心'),
          h('p', '管理团队训练、项目交付与路演所需的全部资料。')
        ]),
        h('div', { class: 'finder-actions' }, [
          h('button', { type: 'button', onClick: () => { categoryName.value = ''; showCategoryDialog.value = true } }, [h(Folder), '新建分类']),
          h('button', { type: 'button', class: 'primary', onClick: openUploadDialog }, [h(DocumentAdd), '上传文件'])
        ])
      ]),
      h('section', { class: 'finder-window' }, [
        h('div', { class: 'finder-library-controls' }, [
          h('div', { class: 'finder-search' }, [
            h('span', { 'aria-hidden': 'true' }, '⌕'),
            h('input', {
              type: 'search',
              value: finderQuery.value,
              'aria-label': '搜索文件',
              placeholder: '搜索文件名称、标签或来源',
              onInput: event => { finderQuery.value = event.target.value }
            })
          ]),
          h('div', { class: 'finder-library-meta' }, [
            h('strong', props.loading ? '资料加载中' : `${allMaterials().length} 份资料`),
            h('span', '点击文件行可展开摘要、引用片段与风险提示')
          ])
        ]),
        h('nav', { class: 'finder-filterbar', 'aria-label': '文件筛选' }, [
          ...[
            { key: 'all', label: '全部文件', count: allMaterials().length },
            { key: 'pending', label: '待处理', count: categoryItems().find(item => item.key === 'pending')?.count || 0 },
            { key: 'recent', label: '最近使用', count: recentCount() },
            { key: 'verified', label: '已确认', count: favoriteCount() }
          ].map(filter => h('button', {
            type: 'button',
            class: { active: activeFilter.value === filter.key },
            onClick: () => setFilter(filter.key)
          }, [h('span', filter.label), h('em', filter.count)])),
          h('i', { class: 'finder-filterbar__divider', 'aria-hidden': 'true' }),
          h('span', { class: 'finder-filterbar__label' }, '分类'),
          ...categoryItems().filter(category => !['all', 'pending'].includes(category.key)).map(category => h('button', {
            type: 'button',
            class: { active: activeFilter.value === category.key },
            onClick: () => setFilter(category.key)
          }, [h('span', category.label), h('em', category.count)]))
        ]),
        h('main', { class: 'finder-main' }, [
          h('div', { class: 'finder-main__head' }, [
            h('div', [h('strong', finderLocationTitle()), h('small', currentFolderMeta())]),
            h('span', { class: 'finder-main__hint' }, '按最近更新排序')
          ]),
          props.loading
            ? loadingTable()
            : filteredMaterials().length
            ? h('div', { class: 'finder-table' }, [
              tableHeader(),
              ...filteredMaterials().map(item => h('div', { class: 'finder-table__item', key: item.id }, [
                h('article', {
                  class: ['finder-row', { active: selectedMaterial()?.id === item.id && detailExpanded.value }],
                  tabindex: 0,
                  'aria-expanded': selectedMaterial()?.id === item.id && detailExpanded.value ? 'true' : 'false',
                  onClick: () => toggleMaterialDetails(item),
                  onKeydown: event => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      toggleMaterialDetails(item)
                    }
                  }
                }, [
                  h('span', { class: 'finder-row__name' }, [
                    h('i', { class: ['doc-icon', item.iconType] }, iconLabel(item.iconType)),
                    h('span', [h('strong', item.name), h('small', item.typeLabel)])
                  ]),
                  h('span', { class: 'finder-row__status' }, [
                    h('b', { class: ['fact-chip', factClass(item.factStatus)] }, item.factStatus),
                    h('b', { class: ['analysis-chip', isUnavailable(item) ? 'missing' : (item.analysisStatus === '已解析' ? 'done' : 'pending')] }, isUnavailable(item) ? '缺失' : item.analysisStatus)
                  ]),
                  h('span', { class: 'finder-row__usage' }, item.usage.slice(0, 3).map(scope => h('em', scope))),
                  h('span', { class: 'finder-row__date' }, item.updatedAt),
                  h('span', { class: 'finder-row__actions' }, [
                    h('button', { type: 'button', disabled: isUnavailable(item) && !isExternalMaterialLink(item), onClick: event => { event.stopPropagation(); previewMaterial(item) } }, materialPrimaryActionText(item)),
                    !isExternalMaterialLink(item)
                      ? h('button', { type: 'button', disabled: isUnavailable(item), onClick: event => { event.stopPropagation(); downloadMaterial(item) } }, '下载')
                      : null
                  ].filter(Boolean))
                ]),
                selectedMaterial()?.id === item.id && detailExpanded.value
                  ? h('section', { class: 'finder-detail-inline', 'aria-label': `${item.name} 内容解析` }, [
                      h('div', { class: 'finder-detail-inline__top' }, [
                        h('strong', '内容解析'),
                        h('span', '再次点击当前文件可收起')
                      ]),
                      h('div', { class: 'finder-detail-inline__content' }, materialDetailNodes(item))
                    ])
                  : null
              ]))
            ])
            : h('div', { class: 'finder-empty' }, [
                h('div', { class: 'prep-dev-state__mark' }, '夹'),
                h('h2', '当前分类暂无文件'),
                h('p', '上传赛项文件、调研资料或项目附件后，会在这里统一管理。'),
                h('button', { type: 'button', onClick: openUploadDialog }, '上传文件')
              ])
        ]),
      ]),
        h(FilePreview, {
          visible: previewVisible.value,
          'onUpdate:visible': closePreview,
          fileUrl: previewUrl.value,
          fileName: previewName.value,
          fileType: previewType.value,
          onDownload: () => {}
        }),
        showUploadDialog.value ? h('div', { class: 'material-modal-backdrop' }, [
          h('section', { class: 'material-modal' }, [
            h('header', [
              h('strong', '上传材料'),
              h('button', { type: 'button', onClick: () => { showUploadDialog.value = false } }, '×')
            ]),
            h('label', { class: 'material-field' }, [
              h('span', '归入分类'),
              h('select', {
                value: uploadCategory.value,
                onChange: event => { uploadCategory.value = event.target.value }
              }, categoryDefinitions()
                .filter(category => !['all', 'pending'].includes(category.key))
                .map(category => h('option', { value: category.key }, category.label)))
            ]),
            h('div', { class: 'material-field' }, [
              h('span', '选择文件'),
              h(DropFileUpload, {
                modelValue: uploadFile.value,
                'onUpdate:modelValue': (value) => { uploadFile.value = value || null },
                accept: '.ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx',
                disabled: uploadBusy.value,
                size: 'md',
                title: '拖拽材料到此处，或点击选择',
                hint: '支持 PPT、PDF、Word、Excel',
                acceptHint: '.ppt .pptx .pdf .doc .docx .xls .xlsx'
              })
            ]),
            h('p', { class: 'material-modal-tip' }, '支持 PPT、PDF、Word、Excel。上传后会进入资源库，并可用于后续选题、PPT、讲稿生成。'),
            h('footer', [
              h('button', { type: 'button', onClick: () => { showUploadDialog.value = false } }, '取消'),
              h('button', { type: 'button', disabled: uploadBusy.value, onClick: submitUpload }, uploadBusy.value ? '上传中...' : '确认上传')
            ])
          ])
        ]) : null,
        showCategoryDialog.value ? h('div', { class: 'material-modal-backdrop' }, [
          h('section', { class: 'material-modal material-modal-narrow' }, [
            h('header', [
              h('strong', '新建分类'),
              h('button', { type: 'button', onClick: () => { showCategoryDialog.value = false } }, '×')
            ]),
            h('label', { class: 'material-field' }, [
              h('span', '分类名称'),
              h('input', {
                value: categoryName.value,
                maxlength: 30,
                placeholder: '例如：答辩素材、竞品资料',
                onInput: event => { categoryName.value = event.target.value },
                onKeydown: event => {
                  if (event.key === 'Enter') createMaterialCategory()
                }
              })
            ]),
            h('p', { class: 'material-modal-tip' }, '分类会保存到数据库，团队刷新页面后仍可继续使用。'),
            h('footer', [
              h('button', { type: 'button', onClick: () => { showCategoryDialog.value = false } }, '取消'),
              h('button', { type: 'button', disabled: categoryBusy.value, onClick: createMaterialCategory }, categoryBusy.value ? '创建中...' : '创建分类')
            ])
          ])
        ]) : null
      ])
  }
})

const PptWorkspace = defineComponent({
  name: 'PptWorkspace',
  props: { resources: Array, stages: Array },
  emits: ['enterPpt'],
  setup(props, { emit }) {
    return () => h('div', { class: 'workspace-shell prep-product-workspace' }, [
      h('div', { class: 'ppt-workspace-entry' }, [
        h('div', [
          h('strong', '开始制作路演 PPT'),
          h('small', '进入工作台上传材料、生成页面并继续编辑')
        ]),
        h('button', {
          type: 'button',
          class: 'script-empty__primary',
          onClick: () => emit('enterPpt')
        }, '进入 PPT 工作台')
      ]),
      h('div', { class: 'workspace-summary' }, [
        h('div', [h('span', '可用资料'), h('strong', String(props.resources?.length || 0)), h('small', '份模板与项目素材')]),
        h('div', [h('span', '项目阶段'), h('strong', String(props.stages?.length || 0)), h('small', '个准备节点')]),
        h('div', [h('span', '工作方式'), h('strong', '生成 + 编辑'), h('small', '支持反馈后局部重做')])
      ]),
      h('div', { class: 'list-grid' }, (props.resources || []).map((item, index) => h('article', { class: 'list-card', key: item.id || item.name || index }, [
        h('strong', item.name || 'PPT 资源'),
        h('small', item.ext || '模板'),
        h('p', item.url || '可作为后续 PPT 生成素材'),
        h('span', { class: 'resource-meta' }, '来源：资源库')
      ]))),
      h('div', { class: 'stage-strip' }, (props.stages || []).map((stage, index) => h('span', { key: stage.id || stage.stageKey || stage.title || index }, `${stage.title || stage.stageKey}: ${stage.status || '-'}`))),
      !(props.resources || []).length ? h(EmptyBlock, { title: '暂无 PPT 资源', desc: '资源库里还没有真实模板或素材，暂不显示生成入口。' }) : null
    ])
  }
})

const ScriptWorkspace = defineComponent({
  name: 'ScriptWorkspace',
  props: { scripts: Array, templates: Array, loading: Boolean },
  emits: ['openScript', 'createBlank', 'createFromTemplate', 'scriptAction'],
  setup(props, { emit }) {
    return () => h('div', { class: 'workspace-shell prep-product-workspace script-product-workspace' }, [
      props.loading
        ? h('div', { class: 'script-list-loading', role: 'status', 'aria-live': 'polite' }, [
            h('span'),
            h('span'),
            h('span')
          ])
        : (props.scripts || []).length
          ? h('div', { class: 'script-library' }, [
            h('div', { class: 'script-library-head' }, [
              h('div', [h('strong', '我的讲稿'), h('small', '按最近更新时间排列')]),
              h('div', { class: 'script-library-head__actions' }, [
                h('span', `${props.scripts?.length || 0} 份`),
                h('button', {
                  type: 'button',
                  class: 'script-empty__primary',
                  onClick: () => emit('createBlank')
                }, '新建讲稿')
              ])
            ]),
            h('div', { class: 'script-list' }, (props.scripts || []).map((script, index) => h('div', {
              class: 'script-row',
              key: script.id || script.title || index,
            }, [
              h('button', {
                type: 'button',
                class: 'script-row-open',
                'aria-label': `打开讲稿：${script.title || '未命名讲稿'}`,
                onClick: () => emit('openScript', script.id),
              }, [
                h('span', { class: 'script-row-index' }, String(index + 1).padStart(2, '0')),
                h('div', { class: 'script-row-copy' }, [
                  h('strong', script.title || '未命名讲稿'),
                  h('small', `更新于 ${formatDate(script.updatedAt || script.createdAt)}`)
                ]),
                h('span', { class: 'script-row-source' }, script.sourceType === 'ppt' ? 'PPT 同步' : '手动编辑'),
                h('span', { class: 'script-row-arrow', 'aria-hidden': 'true' }, '→')
              ]),
              h('button', {
                type: 'button',
                class: 'text-button',
                onClick: () => emit('scriptAction', 'save-template', script)
              }, '另存模板')
            ])))
          ])
          : h('section', { class: 'script-empty', 'aria-labelledby': 'script-empty-title' }, [
              h('span', { class: 'script-empty__icon', 'aria-hidden': 'true' }, [
                h(DocumentAdd)
              ]),
              h('div', { class: 'script-empty__copy' }, [
                h('h2', { id: 'script-empty-title' }, '创建第一份讲稿'),
                h('p', '从空白讲稿开始，或使用模板快速搭好路演结构。内容会自动保存，之后可以随时继续。')
              ]),
              h('div', { class: 'script-empty__actions' }, [
                h('button', {
                  type: 'button',
                  class: 'script-empty__primary',
                  onClick: () => emit('createBlank')
                }, '创建空白讲稿'),
                h('button', {
                  type: 'button',
                  class: 'script-empty__secondary',
                  onClick: () => emit('createFromTemplate')
                }, `使用模板${props.templates?.length ? `（${props.templates.length}）` : ''}`)
              ])
            ])
    ])
  }
})

const RoadshowWorkspace = defineComponent({
  name: 'RoadshowWorkspace',
  props: { roadshow: Object, meetings: Array, tasks: Array },
  setup(props) {
    const hasRoadshow = props.roadshow && Object.keys(props.roadshow).length
    return () => h('div', { class: 'workspace-shell' }, [
      h('div', { class: 'board-header' }, [h('div', [h('h1', '路演准备'), h('p', '展示已绑定路演、会议记录和需要推进的联调任务')])]),
      hasRoadshow ? h('section', { class: 'workspace-section' }, [
        h('div', { class: 'subsection-heading' }, [h('strong', props.roadshow.title || props.roadshow.name || '已绑定路演'), h('span', props.roadshow.status || '进行中')]),
        h('p', { class: 'workspace-copy' }, props.roadshow.description || '暂无路演说明')
      ]) : null,
      h('div', { class: 'list-grid' }, [
        ...(props.meetings || []).map((meeting, index) => h('article', { class: 'list-card', key: meeting.id || meeting.title || meeting.name || index }, [
          h('strong', meeting.title || meeting.name || '路演会议'),
          h('small', formatDate(meeting.startTime || meeting.createdAt)),
          h('p', meeting.status || '会议记录')
        ])),
        ...(props.tasks || []).slice(0, 6).map((task, index) => h('article', { class: 'list-card', key: task.id || task.title || task.name || index }, [
          h('strong', task.title || '任务'),
          h('small', task.status || '待推进'),
          h('p', task.description || '暂无说明')
        ]))
      ]),
      !hasRoadshow && !(props.meetings || []).length ? h(EmptyBlock, { title: '暂无路演联调记录', desc: '绑定会议或创建联调任务后会在这里展示。' }) : null
    ])
  }
})

const VersionsWorkspace = defineComponent({
  name: 'VersionsWorkspace',
  props: { documents: Array, scripts: Array, aiRuns: Array },
  emits: ['openDocument'],
  setup(props, { emit }) {
    return () => h('div', { class: 'workspace-shell' }, [
      h('div', { class: 'board-header' }, [h('div', [h('h1', '版本记录'), h('p', '方向、策划文档、讲稿和 AI 运行记录')])]),
      h('div', { class: 'list-grid' }, [
        ...(props.documents || []).map((doc, index) => h('article', { class: 'list-card', key: doc.id || doc.title || index }, [
          h('strong', doc.title || '策划文档'),
          h('small', formatDate(doc.updatedAt || doc.createdAt)),
          h('p', doc.status || 'DRAFT'),
          h('button', { type: 'button', class: 'text-button', onClick: () => emit('openDocument', doc.id) }, '查看正文')
        ])),
        ...(props.scripts || []).slice(0, 6).map((script, index) => h('article', { class: 'list-card', key: script.id || script.title || index }, [
          h('strong', script.title || '讲稿'),
          h('small', formatDate(script.updatedAt || script.createdAt)),
          h('p', script.syncStatus || '讲稿版本')
        ])),
        ...(props.aiRuns || []).map((run, index) => h('article', { class: 'list-card', key: run.id || run.startedAt || index }, [
          h('strong', runStatusText(run.status)),
          h('small', formatDate(run.completedAt || run.startedAt)),
          h('p', run.errorMessage || 'AI 运行记录')
        ]))
      ]),
      !(props.documents || []).length && !(props.scripts || []).length && !(props.aiRuns || []).length
        ? h(EmptyBlock, { title: '暂无版本记录', desc: '生成方向、讲稿或策划书后会沉淀在这里。' })
        : null
    ])
  }
})

async function loadPrep(teamId = null) {
  const requestContext = prepRequestLifecycle.open('bootstrap')
  loading.value = true
  loadError.value = ''
  try {
    const res = await request.get('/api/project-prep/bootstrap', {
      params: teamId ? { teamId } : {},
      signal: requestContext.signal,
    })
    if (!requestContext.isCurrent()) return
    if (res.code === 200) {
      applyBootstrap(res.data || {})
    }
  } catch (e) {
    if (!requestContext.isCurrent()) return
    loadError.value = e?.message || '无法连接准备页服务'
  } finally {
    const requestIsCurrent = requestContext.isCurrent()
    requestContext.release()
    if (requestIsCurrent) loading.value = false
  }
}

function applyBootstrap(data) {
  teams.value = data.teams || []
  activeTeamId.value = data.activeTeamId || null
  dashboard.value = data.dashboard || {}
  prepSession.value = data.prepSession || null
  scripts.value = data.scripts || data.userAssets?.scripts || []
  templates.value = data.scriptTemplates || data.userAssets?.scriptTemplates || []
  resources.value = data.resources || data.userAssets?.pptTemplates || []
  // 缓存供下次进入资源中心秒开
  const team = (data.teams || []).find((t) => String(t.id) === String(data.activeTeamId))
  scriptListTeamCache.teamId = data.activeTeamId || null
  scriptListTeamCache.teamName = team?.name || ''
  ensureRunPolling()
}

async function switchTeam(teamId) {
  const requestContext = prepRequestLifecycle.open('team')
  try {
    const res = await request.get(`/api/project-prep/teams/${teamId}`, {
      signal: requestContext.signal,
    })
    if (!requestContext.isCurrent()) return
    if (res.code === 200) {
      activeTeamId.value = Number(teamId)
      dashboard.value = res.data?.dashboard || {}
      prepSession.value = res.data?.prepSession || null
      ensureRunPolling()
    }
  } finally {
    requestContext.release()
  }
}

async function refreshSession(requestGeneration = prepRequestLifecycle.currentGeneration()) {
  if (!prepRequestLifecycle.isCurrent(requestGeneration) || !prepSession.value?.id) return

  const requestContext = prepRequestLifecycle.open('session')
  const previousStatus = latestRun.value?.status
  try {
    const res = await request.get(`/api/project-prep/sessions/${prepSession.value.id}`, {
      signal: requestContext.signal,
    })
    if (!requestContext.isCurrent()) return
    if (res.code === 200) {
      prepSession.value = res.data
      if (previousStatus === 'RUNNING' && latestRun.value?.status === 'COMPLETED') {
        ElMessage.success('AI 已生成选题建议')
      }
      if (previousStatus === 'RUNNING' && latestRun.value?.status === 'FAILED') {
        ElMessage.warning(latestRun.value?.errorMessage || 'AI 生成失败，请稍后重试')
      }
      ensureRunPolling()
    }
  } catch {
    // Polling is best-effort. The serial poller will retry only while this
    // preparation lifecycle and the running session are still current.
  } finally {
    requestContext.release()
  }
}

async function sendPrompt(contentOverride = null) {
  if (!prepSession.value?.id) return
  const content = String(contentOverride || promptText.value).trim()
  if (!content) {
    ElMessage.warning('请先补充选题信息')
    return
  }
  submittingPrompt.value = true
  try {
    const res = await request.post(`/api/project-prep/sessions/${prepSession.value.id}/messages`, { content }, { timeout: 20000 })
    if (res.code === 200) {
      prepSession.value = res.data?.session || prepSession.value
      if (res.data?.accepted === false) {
        ElMessage.warning(res.data.message || 'AI 生成失败，请稍后重试')
      } else {
        promptText.value = ''
        ensureRunPolling()
        ElMessage.success(res.data?.message || '已提交选题策划生成')
      }
    }
  } finally {
    submittingPrompt.value = false
  }
}

async function retryLastPrompt(content) {
  if (content) promptText.value = content
  await sendPrompt(content)
}

async function selectDirection(directionId) {
  if (!prepSession.value?.id || !directionId) return
  const res = await request.post(`/api/project-prep/sessions/${prepSession.value.id}/directions/${directionId}/select`)
  if (res.code === 200) {
    prepSession.value = res.data
    ElMessage.success('已采纳方向')
  }
}

async function createTasksFromDirection(directionId) {
  if (!prepSession.value?.id || !directionId) return
  taskGeneratingDirectionId.value = directionId
  try {
    const res = await request.post(`/api/project-prep/sessions/${prepSession.value.id}/directions/${directionId}/tasks`)
    if (res.code === 200) {
      dashboard.value = res.data?.dashboard || dashboard.value
      if (res.data?.alreadyGenerated) {
        ElMessage.info(`该方向已生成过 ${res.data?.createdTasks?.length || 0} 个任务`)
      } else {
        ElMessage.success(`已生成 ${res.data?.createdTasks?.length || 0} 个团队任务`)
      }
    }
  } finally {
    taskGeneratingDirectionId.value = null
  }
}

async function syncPrepWorkItems() {
  if (!activeTeamId.value) {
    ElMessage.warning('请先选择项目团队')
    return
  }
  if (!prepWorkItemDrafts.value.length) {
    ElMessage.info('暂无可同步成团队工作项的事项')
    return
  }
  syncingPrepTasks.value = true
  syncedPrepTaskCount.value = 0
  try {
    for (const item of prepWorkItemDrafts.value) {
      await request.post(`/api/project-teams/${activeTeamId.value}/tasks`, {
        title: item.title,
        description: `${item.description}\n\n来源：准备页内容同步\n处理要求：在团队工作项中确认负责人、状态和下一步动作。`,
        ownerUserId: null,
        stageKey: item.stageKey || 'MATERIAL',
        priority: item.priority || 'MEDIUM',
        dueAt: null
      })
      syncedPrepTaskCount.value += 1
    }
    ElMessage.success(`已生成 ${syncedPrepTaskCount.value} 个团队工作项`)
    await loadPrep(activeTeamId.value)
  } finally {
    syncingPrepTasks.value = false
  }
}

function goTeamInbox() {
  router.push({ path: '/project-team', query: { workView: 'inbox', teamId: activeTeamId.value || undefined } })
}

async function createDocument(directionId) {
  if (!prepSession.value?.id) return
  generatingDocument.value = true
  documentGeneratingDirectionId.value = directionId
  try {
    const res = await request.post(`/api/project-prep/sessions/${prepSession.value.id}/document`, { directionId })
    if (res.code === 200) {
      await refreshSession()
      documentPreview.value = res.data?.document || null
      showDocumentPreview.value = Boolean(documentPreview.value)
      activePrepKey.value = 'versions'
      if (res.data?.alreadyGenerated) ElMessage.info('已打开该方向已有策划书草稿')
      else ElMessage.success('已生成策划书草稿')
    }
  } finally {
    generatingDocument.value = false
    documentGeneratingDirectionId.value = null
  }
}

async function openDocument(documentId) {
  if (!prepSession.value?.id || !documentId) return
  const res = await request.get(`/api/project-prep/sessions/${prepSession.value.id}/documents/${documentId}`)
  if (res.code === 200) {
    documentPreview.value = res.data?.document || null
    showDocumentPreview.value = Boolean(documentPreview.value)
  }
}

function openTemplateDialog() {
  showNewFromTemplate.value = true
}

function openScript(id) {
  router.push(`/script-editor/detail/${id}`)
}

async function createFromTemplate(template) {
  showNewFromTemplate.value = false
  const res = await request.post('/api/script', {
    title: template.name || '新建讲稿',
    content: template.content,
    roles: template.roles,
    sourceType: 'manual'
  })
  if (res.code === 200) {
    ElMessage.success('已创建讲稿')
    router.push(`/script-editor/detail/${res.data.id}`)
  }
}

async function createBlankScript() {
  if (creatingBlankScript.value) return
  creatingBlankScript.value = true
  const stamp = Date.now().toString(36)
  try {
    const res = await request.post('/api/script', {
      title: '未命名讲稿',
      content: JSON.stringify([
        {
          id: `chapter-${stamp}`,
          title: '新章节',
          totalDuration: 5,
          steps: []
        }
      ]),
      roles: JSON.stringify([
        {
          id: `role-${stamp}`,
          label: '主讲人',
          color: '#c43a12'
        }
      ]),
      sourceType: 'manual'
    })
    if (res.code === 200 && res.data?.id) {
      showNewFromTemplate.value = false
      ElMessage.success('空白讲稿已创建')
      router.push(`/script-editor/detail/${res.data.id}`)
      return
    }
    ElMessage.error(res.message || '创建空白讲稿失败')
  } catch (error) {
    ElMessage.error(error?.message || '创建空白讲稿失败')
  } finally {
    creatingBlankScript.value = false
  }
}

function handleScriptAction(action, script) {
  if (action === 'delete') {
    ElMessageBox.confirm('确定删除此讲稿？', '提示', { type: 'warning' }).then(async () => {
      const res = await request.delete(`/api/script/${script.id}`)
      if (res.code === 200) {
        ElMessage.success('已删除')
        await loadPrep(activeTeamId.value)
      }
    }).catch(() => {})
  } else if (action === 'save-template') {
    savingScript.value = script
    newTemplateName.value = `${script.title || '讲稿'} 模板`
    newTemplateDesc.value = ''
    showSaveAsTemplate.value = true
  }
}

async function confirmSaveAsTemplate() {
  if (!newTemplateName.value.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  const s = savingScript.value
  const res = await request.post('/api/script-template/from-script', {
    name: newTemplateName.value.trim(),
    description: newTemplateDesc.value,
    content: s.content,
    roles: s.roles
  })
  if (res.code === 200) {
    ElMessage.success('模板已保存')
    showSaveAsTemplate.value = false
    await loadPrep(activeTeamId.value)
  }
}

function iconLabel(type) {
  if (type === 'pdf') return 'PDF'
  if (type === 'word') return 'W'
  if (type === 'excel') return '表'
  if (type === 'orange') return '签'
  return '文'
}

const materialCategories = [
  { key: 'all', label: '全部材料', icon: Files },
  { key: 'competition', label: '赛项文件', icon: Tickets },
  { key: 'team', label: '团队项目材料', icon: Briefcase },
  { key: 'research', label: '调研资料', icon: Connection },
  { key: 'proof', label: '成果证明', icon: Star },
  { key: 'content', label: 'PPT/讲稿素材', icon: Collection },
  { key: 'public', label: '公共资源', icon: Folder },
  { key: 'pending', label: '待处理', icon: MoreFilled }
]

function avatarText(text) {
  return String(text || '员').slice(0, 1)
}

function normalizeMaterials(materials = [], resources = []) {
  const teamItems = materials.map((item, index) => {
    const name = item.name || item.title || `团队材料 ${index + 1}`
    const category = item.category || inferMaterialCategory(name, item.materialType || item.sourceType || item.type)
    return {
      id: `m-${item.id || index}`,
      raw: item,
      name,
      category,
      typeLabel: materialTypeText(item.materialType || item.sourceType || item.type || '团队材料'),
      iconType: materialIconType(name, item.ext || item.fileType),
      factStatus: inferFactStatus(item.reviewStatus || item.status || '待确认来源', true),
      analysisStatus: item.summary || item.description ? '已解析' : '待解析',
      updatedAt: formatMaterialDate(item.updatedAt || item.createdAt || item.uploadedAt),
      summary: item.summary || item.description || '这份材料还没有解析摘要。建议先确认来源和真实性，再用于选题、PPT 或讲稿。',
      usage: inferMaterialUsage(category, true),
      quote: safeMaterialQuote(item.description || item.summary, name, true),
      risk: inferMaterialRisk(category, item.reviewStatus || item.status),
      fileUrl: resolveMaterialPreviewUrl(item),
      downloadUrl: resolveMaterialDownloadUrl(item)
    }
  })
  const publicItems = resources.map((item, index) => {
    const name = item.name || item.title || `公共资源 ${index + 1}`
    const category = item.category || 'public'
    const isTeamScoped = category !== 'public'
    return {
      id: `r-${item.id || index}`,
      raw: item,
      name,
      category,
      typeLabel: resourceTypeText(item.ext || item.fileType || item.type || category),
      iconType: materialIconType(name, item.ext || item.fileType),
      factStatus: isTeamScoped ? '待确认来源' : '参考资料',
      analysisStatus: item.description ? '已解析' : '待解析',
      updatedAt: formatMaterialDate(item.updatedAt || item.createdAt),
      summary: item.description || (item.fileSize ? `资源库文件，大小 ${item.fileSize}。` : '这份材料已进入资源库，使用前需要确认来源、真实性和可引用范围。'),
      usage: inferMaterialUsage(category, isTeamScoped),
      quote: safeMaterialQuote(item.description, name, isTeamScoped),
      risk: isTeamScoped ? '需要确认它能证明哪些团队信息，再进入后续生成流程。' : '不能直接写成团队已有成果，需要在生成前和已确认材料分开。',
      fileUrl: resolveMaterialPreviewUrl(item),
      downloadUrl: resolveMaterialDownloadUrl(item)
    }
  })
  return [...teamItems, ...publicItems]
}

function resolveMaterialPreviewUrl(item = {}) {
  const rawUrl = item.fileUrl || item.previewUrl || item.path || item.filePath || item.url || item.downloadUrl
  if (!rawUrl) return ''
  const value = String(rawUrl)
  if (/^https?:\/\//.test(value) || value.startsWith('blob:') || value.startsWith('data:')) return value
  const normalized = value.startsWith('/') ? value : `/${value}`
  if (normalized.startsWith('/uploads/')) return encodePathSegments(normalized)
  return encodePptTemplateUrl(normalized)
}

function resolveMaterialDownloadUrl(item = {}) {
  const rawUrl = item.downloadUrl || item.url || item.fileUrl || item.previewUrl || item.path || item.filePath
  if (!rawUrl) return ''
  const value = String(rawUrl)
  if (/^https?:\/\//.test(value) || value.startsWith('blob:') || value.startsWith('data:')) return value
  const normalized = value.startsWith('/') ? value : `/${value}`
  if (normalized.startsWith('/uploads/')) return encodePathSegments(normalized)
  return encodePptTemplateUrl(normalized)
}

function materialPreviewUrl(item) {
  return item?.fileUrl || resolveMaterialPreviewUrl(item?.raw || {})
}

function materialDownloadUrl(item) {
  return item?.downloadUrl || resolveMaterialDownloadUrl(item?.raw || {})
}

function materialExternalUrl(item) {
  const raw = item?.raw || {}
  const rawUrl = raw.linkUrl || raw.externalUrl || raw.url || item?.fileUrl || raw.fileUrl || item?.downloadUrl || raw.downloadUrl || item?.previewUrl || raw.previewUrl
  return normalizeMaterialUrl(String(rawUrl || '').trim())
}

function isExternalMaterialLink(item) {
  const raw = item?.raw || {}
  const typeValue = [
    item?.typeLabel,
    raw.materialType,
    raw.sourceType,
    raw.type,
    raw.ext,
    raw.fileType,
    raw.category
  ].filter(Boolean).join(' ').toUpperCase()
  return /(^|\s)(LINK|URL)(\s|$)|外部链接/.test(typeValue)
}

function materialPrimaryActionText(item) {
  if (isExternalMaterialLink(item)) return '打开链接'
  return canInlinePreviewMaterial(item) ? '预览' : '下载查看'
}

function normalizeMaterialUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//.test(url) || url.startsWith('blob:') || url.startsWith('data:')) return url
  return url.startsWith('/') ? url : `/${url}`
}

function encodePathSegments(url) {
  return url.split('/').map((part, index) => {
    if (index === 0 || !part) return part
    try {
      return encodeURIComponent(decodeURIComponent(part))
    } catch (error) {
      return encodeURIComponent(part)
    }
  }).join('/')
}

function encodePptTemplateUrl(url) {
  const prefix = '/api/ppt-template/download/'
  if (!url.startsWith(prefix)) return url
  let filename = url.slice(prefix.length)
  try {
    filename = decodeURIComponent(filename)
  } catch (error) {
    // Keep the original segment when it is not a valid encoded string.
  }
  return `${prefix}${encodeURIComponent(filename)}`
}

function safeMaterialQuote(text, name, isTeamMaterial) {
  const value = String(text || '').trim()
  if (value && !/^\/?api\//.test(value) && !/^https?:\/\//.test(value)) return value
  return isTeamMaterial
    ? `可从「${name}」中提取团队信息，使用前需要确认材料来源和真实性。`
    : `「${name}」属于公共参考资源，可用于版式、表达或外部依据，不可直接写成团队已有成果。`
}

function materialMimeType(item, blob = null) {
  if (blob?.type && blob.type !== 'application/octet-stream') return blob.type
  const ext = String(item?.name || item?.typeLabel || '').split('.').pop()?.toLowerCase()
  const map = {
    pdf: 'application/pdf',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    doc: 'application/msword',
    pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ppt: 'application/vnd.ms-powerpoint',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    xls: 'application/vnd.ms-excel'
  }
  return map[ext] || ''
}

function materialExtension(item) {
  const name = String(item?.name || item?.typeLabel || '')
  return name.includes('.') ? name.split('.').pop().toLowerCase() : String(item?.typeLabel || '').toLowerCase()
}

function canInlinePreviewMaterial(item) {
  return ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'txt', 'md', 'docx', 'xlsx', 'pptx'].includes(materialExtension(item))
}

function inferMaterialCategory(name, type) {
  const value = `${name || ''} ${type || ''}`
  if (/赛项|规程|任务书|评分|规则|通知/.test(value)) return 'competition'
  if (/调研|行业|需求|竞品|公开|案例|政策/.test(value)) return 'research'
  if (/证书|获奖|专利|软著|证明|成果/.test(value)) return 'proof'
  if (/PPT|讲稿|图片|素材|模板|路演|展示/.test(value)) return 'content'
  return 'team'
}

function materialIconType(name, type) {
  const value = `${name || ''} ${type || ''}`.toLowerCase()
  if (/pdf/.test(value)) return 'pdf'
  if (/doc|word/.test(value)) return 'word'
  if (/xls|excel/.test(value)) return 'excel'
  return 'doc'
}

function materialTypeText(type) {
  const value = String(type || '').toUpperCase()
  const map = {
    TEAM_MATERIAL: '团队材料',
    PUBLIC_WEB: '公开资料',
    USER_INPUT: '用户补充',
    MODEL_INFERENCE: '模型推理',
    OTHER: '其他材料',
    LINK: '外部链接',
    PROGRESS: '项目进度',
    DOCS: '项目文档',
    DOCUMENT: '项目文档',
    DOCUMENTS: '项目文档',
    FILE: '普通文件',
    MATERIAL: '项目材料',
    PROJECT_MATERIAL: '项目材料',
    TASK_SUBMISSION: '任务提交',
    SUBMISSION: '任务提交',
    PACKAGE: '压缩包',
    PPT: 'PPT 文件',
    PPTX: 'PPT 文件',
    PDF: 'PDF 文档',
    DOC: 'Word 文档',
    DOCX: 'Word 文档',
    IMAGE: '图片素材',
    PNG: '图片素材',
    JPG: '图片素材',
    JPEG: '图片素材',
    CODE: '代码材料',
    DATA: '数据材料'
  }
  return map[value] || resourceTypeText(type) || '材料'
}

function resourceTypeText(type) {
  const value = String(type || '').trim()
  const normalized = value.toUpperCase().replace(/^\./, '')
  const map = {
    PUBLIC: '公共资源',
    TEAM: '团队材料',
    COMPETITION: '赛项文件',
    RESEARCH: '调研资料',
    PROOF: '成果证明',
    CONTENT: 'PPT/讲稿素材',
    LINK: '外部链接',
    URL: '外部链接',
    OTHER: '其他材料',
    PROGRESS: '项目进度',
    DOCS: '项目文档',
    PDF: 'PDF 文档',
    PPT: 'PPT 文件',
    PPTX: 'PPT 文件',
    DOC: 'Word 文档',
    DOCX: 'Word 文档',
    XLS: 'Excel 表格',
    XLSX: 'Excel 表格',
    PNG: '图片素材',
    JPG: '图片素材',
    JPEG: '图片素材',
    GIF: '图片素材',
    WEBP: '图片素材',
    ZIP: '压缩包',
    RAR: '压缩包',
    TXT: '文本文件',
    MD: 'Markdown 文档'
  }
  return map[normalized] || value
}

function inferFactStatus(status, isTeamMaterial) {
  const value = String(status || '').toUpperCase()
  if (!isTeamMaterial) return '参考资料'
  if (/APPROVED|VERIFIED|CONFIRMED|完成|已确认|已审核/.test(value)) return '可直接使用'
  return '待确认来源'
}

function factClass(status) {
  if (status === '可直接使用') return 'fact'
  if (status === '参考资料') return 'reference'
  return 'pending'
}

function inferMaterialUsage(category, isTeamMaterial) {
  if (!isTeamMaterial) return ['PPT', '讲稿']
  if (category === 'competition') return ['选题', '策划', 'PPT']
  if (category === 'research') return ['选题', '策划']
  if (category === 'proof') return ['策划', '讲稿']
  if (category === 'content') return ['PPT', '讲稿']
  return ['选题', '策划', 'PPT', '讲稿']
}

function inferMaterialRisk(category, status) {
  if (String(status || '').includes('待')) return '需要人工确认真实性与使用范围，避免把未核实内容写入最终产物。'
  if (category === 'public') return '公共资料只能作为外部依据，不能表述为团队已有成果。'
  if (category === 'research') return '调研资料需要补充来源或时间，避免引用过期结论。'
  return '建议标注出处和可引用范围，便于后续生成时追溯。'
}

function formatMaterialDate(dt) {
  if (!dt) return '最近更新'
  return formatDate(dt)
}

function filterTitle(key) {
  return materialCategories.find(category => category.key === key)?.label || '全部材料'
}

function materialDetailNodes(item) {
  return [
    h('section', { class: 'material-detail-section' }, [
      h('h3', 'AI 摘要'),
      h('p', item.summary)
    ]),
    h('section', { class: 'material-detail-section' }, [
      h('h3', '风险与缺口'),
      h('p', item.risk)
    ])
  ]
}

function matchText(value) {
  const map = { HIGH: '高', MEDIUM: '中', LOW: '低', UNKNOWN: '未知' }
  return map[String(value || 'UNKNOWN').toUpperCase()] || '未知'
}

function statusText(status) {
  const map = { DRAFT: '待补充', ACTIVE: '进行中', AI_RUNNING: 'AI 生成中', AI_FAILED: '生成失败' }
  return map[status] || status || '未开始'
}

function runStatusText(status) {
  const map = { RUNNING: 'AI 生成中', COMPLETED: 'AI 已完成', FAILED: 'AI 失败' }
  return map[status] || status || 'AI 状态'
}

function runClass(status) {
  if (status === 'COMPLETED') return 'success'
  if (status === 'FAILED') return 'danger'
  return 'running'
}

function agentStepStatusMeta(status) {
  const value = String(status || '').toUpperCase()
  if (value === 'COMPLETED') return '已完成'
  if (value === 'RUNNING') return '进行中'
  if (value === 'FAILED') return '失败'
  return '等待'
}

function ensureRunPolling() {
  if (
    !prepRequestLifecycle.isActive()
    || latestRun.value?.status !== 'RUNNING'
    || !prepSession.value?.id
  ) {
    runPoller.stop()
    return
  }
  runPoller.start()
}

function directionIntentText(direction) {
  const title = direction?.title || '这个方向'
  return `我选择「${title}」作为深化方向，请选题团队基于这个方向继续推进。`
}

function compactText(text, max = 48) {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  return value.length > max ? `${value.slice(0, max)}...` : value
}

function requestedAgentIndex(text) {
  const value = String(text || '')
  if (/张调研|调研|案例|公开|证据|竞品|行业/.test(value)) return 2
  if (/李政策|政策|赛项|要求|规则|申报/.test(value)) return 1
  if (/周可行|可行|设备|周期|数据条件|传感器|难度|展示/.test(value)) return 3
  if (/刘主编|主编|草稿|策划书|文档|结构|生成/.test(value)) return 4
  if (/赵选题|选题|方向|赛道|边界/.test(value)) return 0
  return 0
}

function currentAgentName(latestRun, submitting = false, prompt = '') {
  const agentNames = ['赵选题', '李政策', '张调研', '周可行', '刘主编']
  if (submitting) return agentNames[requestedAgentIndex(prompt)]
  if (latestRun?.status === 'RUNNING') return '选题团队'
  return 'AI 选题策划'
}

function topicAgentSteps(latestRun, directions = [], selectedDirection = null, submitting = false, prompt = '') {
  const runStatus = latestRun?.status || ''
  const hasDirections = directions.length > 0
  const isRunning = submitting || runStatus === 'RUNNING'
  const isFailed = runStatus === 'FAILED'
  const isCompleted = runStatus === 'COMPLETED'
  const hasSelection = Boolean(selectedDirection)
  const requestedIndex = submitting ? requestedAgentIndex(prompt) : -1
  const statuses = [
    isRunning ? 'running' : (hasDirections || isCompleted || hasSelection ? 'done' : 'pending'),
    isRunning ? 'pending' : (hasDirections || isCompleted ? 'done' : 'pending'),
    isRunning ? 'pending' : (hasDirections || isCompleted ? 'done' : 'pending'),
    isRunning ? 'pending' : (hasDirections || isCompleted ? 'done' : 'pending'),
    hasSelection ? 'running' : (hasDirections || isCompleted ? 'pending' : 'pending')
  ]
  if (requestedIndex >= 0) {
    statuses.fill('pending')
    statuses[requestedIndex] = 'running'
  }
  if (isFailed) statuses.fill('failed')
  return [
    {
      avatar: '赵',
      name: '赵选题',
      task: hasSelection ? `确认采纳「${selectedDirection.title}」` : '判断赛道、团队信息和方向边界',
      status: statuses[0],
    },
    {
      avatar: '政',
      name: '李政策',
      task: '补公开政策、赛项要求和专项趋势',
      status: statuses[1],
    },
    {
      avatar: '研',
      name: '张调研',
      task: '查行业案例、用户痛点和竞品证据',
      status: statuses[2],
    },
    {
      avatar: '行',
      name: '周可行',
      task: '评估设备、数据、周期和展示难度',
      status: statuses[3],
    },
    {
      avatar: '编',
      name: '刘主编',
      task: hasSelection ? '等待生成任务或策划书草稿' : '整理为方向池、任务和策划书结构',
      status: statuses[4],
    }
  ].map(step => ({
    ...step,
    statusText: step.status === 'done' ? '完成' : step.status === 'running' ? '进行中' : step.status === 'failed' ? '失败' : '待处理'
  }))
}

function sourceTypeText(type) {
  const map = {
    PUBLIC_WEB: '公开',
    USER_INPUT: '输入',
    TEAM_MATERIAL: '材料',
    MODEL_INFERENCE: '推理'
  }
  return map[String(type || '').toUpperCase()] || '来源'
}

function formatDate(dt) {
  if (!dt) return '最近更新'
  const d = new Date(dt)
  if (Number.isNaN(d.getTime())) return String(dt)
  const diff = Date.now() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN')
}

onMounted(() => {
  prepRouteMounted = true
  prepRequestLifecycle.activate()
  loadPrep()
})

onBeforeUnmount(() => {
  prepRequestLifecycle.invalidate()
  prepRouteMounted = false
  runPoller.stop()
})
</script>

<style>
.prep-page {
  min-height: calc(100vh - var(--header-height));
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  background-color: #ffffff;
  background-image: none;
  color: var(--orep-text-strong);
}

.prep-rail {
  display: none !important;
}

.prep-rail {
  position: sticky;
  top: var(--header-height);
  min-height: calc(100vh - var(--header-height));
  max-height: calc(100vh - var(--header-height));
  padding: 34px 12px 22px;
  border-right: 1px solid var(--orep-border-soft);
  background: oklch(0.991 0.006 55 / 0.86);
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
}

.prep-rail.collapsed {
  align-items: center;
}

.prep-rail.collapsed .rail-section-title,
.prep-rail.collapsed .rail-item span:last-child,
.prep-rail.collapsed .rail-collapse span {
  display: none;
}

.rail-section-title {
  padding: 0 14px 14px;
  color: var(--orep-text);
  font-size: 14px;
  font-weight: 760;
}

.prep-page button {
  font: inherit;
}

.rail-item,
.rail-collapse,
.icon-button,
.secondary-button,
.header-button,
.generate-button,
.sync-button,
.tpl-item,
.text-button,
.topic-shell .card-actions button {
  border: 0;
  cursor: pointer;
}

.rail-item {
  min-height: 42px;
  padding: 0 14px;
  border-radius: 8px;
  background: transparent;
  color: var(--orep-text);
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 720;
}

.rail-item.active {
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
}

.rail-icon {
  width: 18px;
  display: inline-flex;
  justify-content: center;
}

.rail-collapse {
  margin-top: auto;
  padding: 0 14px;
  min-height: 38px;
  background: transparent;
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.prep-workbench {
  min-width: 0;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  display: grid;
  grid-template-columns: 280px minmax(620px, 1fr) 310px;
  gap: 18px;
}

.prep-workbench.mode-topic {
  height: calc(100vh - var(--header-height));
  padding: 12px 24px 18px 8px;
  grid-template-columns: minmax(620px, 1fr) 390px;
  grid-template-rows: 48px minmax(0, 1fr);
  grid-template-areas:
    "team team"
    "board artifacts";
  overflow: hidden;
}

.prep-workbench:not(.mode-topic) {
  grid-template-columns: minmax(0, 1fr) 300px;
  padding-left: var(--ds-page-margin-x, 40px);
}

.prep-workbench.mode-materials {
  grid-template-columns: minmax(0, 1fr);
}

.prep-alert {
  grid-column: 1 / -1;
  min-height: 54px;
  padding: 10px 14px;
  border: 1px solid oklch(0.82 0.09 32);
  border-radius: 9px;
  background: oklch(0.975 0.035 42);
  color: var(--orep-text-strong);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.prep-alert strong,
.prep-alert span {
  display: block;
}

.prep-alert span {
  margin-top: 3px;
  color: var(--orep-muted);
  font-size: 12px;
}

.prep-alert button,
.ai-failure button {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  font-weight: 760;
  cursor: pointer;
}

.topic-team-panel,
.planning-board,
.artifact-panel {
  min-width: 0;
}

.mode-topic .topic-team-panel {
  grid-area: team;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 2px 0 0;
}

.mode-topic .planning-board {
  grid-area: board;
  min-height: 0;
}

.mode-topic .artifact-panel {
  grid-area: artifacts;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}

.team-switcher,
.team-card,
.planning-board,
.artifact-group {
  border: 1px solid var(--orep-border-soft);
  background: oklch(0.997 0.004 55 / 0.94);
  box-shadow: 0 14px 38px oklch(0.2 0.012 45 / 0.04);
}

.team-switcher {
  height: 48px;
  padding: 0 16px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-topic .team-switcher {
  height: 40px;
  min-width: 0;
  max-width: 430px;
  border-radius: 10px;
}

.topic-team-menu {
  box-shadow: none;
}

.topic-team-menu small {
  min-width: 0;
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--orep-muted);
  font-size: 12px;
}

.team-switcher strong {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-button {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: var(--orep-bg-soft);
  color: var(--orep-text);
}

.avatar-stack {
  display: flex;
}

.mini-avatar {
  width: 22px;
  height: 22px;
  margin-left: -5px;
  border: 2px solid var(--orep-surface-raised);
  border-radius: 999px;
  background: #ece6de;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
}

.mini-avatar:first-child {
  margin-left: 0;
}

.team-card,
.artifact-group,
.planning-board {
  border-radius: 10px;
}

.team-card {
  margin-top: 12px;
  padding: 16px;
}

.topic-advisor-card {
  padding-bottom: 14px;
}

.mode-topic .topic-advisor-card {
  height: 54px;
  margin-top: 0;
  padding: 0 12px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  overflow: hidden;
}

.mode-topic .topic-advisor-card .panel-title {
  flex: 0 0 auto;
  gap: 8px;
}

.mode-topic .topic-advisor-card .panel-title span {
  display: none;
}

.mode-topic .topic-advisor-card .advisor-summary,
.mode-topic .topic-advisor-card .member-heading {
  display: none;
}

.mode-topic .advisor-list {
  margin-top: 0;
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.panel-title,
.member-heading,
.artifact-title,
.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-title span,
.artifact-title span {
  min-width: 24px;
  height: 22px;
  padding: 0 7px;
  border-radius: 6px;
  background: var(--orep-bg-soft);
  color: var(--orep-text);
  display: inline-grid;
  place-items: center;
  font-size: 12px;
  font-weight: 800;
}

.team-summary {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
}

.advisor-summary {
  background: oklch(0.982 0.018 55);
}

.team-summary strong,
.team-summary small {
  display: block;
}

.team-summary small {
  margin-top: 6px;
  color: var(--orep-muted);
  line-height: 1.55;
}

.member-heading {
  justify-content: flex-start;
  gap: 5px;
  margin-top: 16px;
  color: var(--orep-muted);
  font-size: 12px;
}

.member-list {
  margin-top: 10px;
  display: grid;
  gap: 10px;
}

.member-card {
  min-height: 78px;
  padding: 12px 10px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 10px;
}

.advisor-card {
  grid-template-columns: 42px minmax(0, 1fr) 16px;
  align-items: center;
}

.mode-topic .advisor-card {
  flex: 0 0 140px;
  min-height: 38px;
  padding: 6px 8px;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 8px;
}

.mode-topic .advisor-card .el-icon,
.mode-topic .advisor-card .member-body span {
  display: none;
}

.advisor-card.active {
  border-color: oklch(0.78 0.14 45);
  background: oklch(0.982 0.024 48);
  box-shadow: inset 0 0 0 1px oklch(0.86 0.08 45);
}

.advisor-card .el-icon {
  color: var(--orep-muted);
}

.member-avatar,
.chat-avatar {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #e8edf2;
  font-weight: 850;
}

.mode-topic .advisor-card .member-avatar {
  width: 30px;
  height: 30px;
  font-size: 12px;
}

.advisor-avatar {
  background: oklch(0.91 0.045 225);
  color: oklch(0.35 0.035 245);
}

.member-body {
  min-width: 0;
}

.member-body strong,
.member-body small,
.member-body span {
  display: block;
}

.member-body em {
  margin-left: 6px;
  padding: 1px 5px;
  border: 1px solid oklch(0.86 0.08 45);
  border-radius: 5px;
  color: var(--orep-orange);
  font-style: normal;
  font-size: 10px;
  font-weight: 820;
}

.mode-topic .member-body em {
  display: none;
}

.mode-topic .member-body small {
  margin-top: 2px;
  font-size: 10px;
}

.member-body small {
  margin-top: 4px;
  color: var(--orep-text);
  font-size: 12px;
  font-weight: 760;
}

.member-body span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 11px;
  line-height: 1.35;
}

.secondary-button {
  width: 100%;
  height: 34px;
  margin-top: 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 720;
}

.mode-topic .secondary-button {
  width: auto;
  height: 40px;
  margin-top: 0;
  padding: 0 14px;
  border-radius: 10px;
  white-space: nowrap;
}

.planning-board {
  padding: 20px;
}

.mode-topic .planning-board {
  padding: 0;
  overflow: hidden;
}

.workspace-shell {
  min-width: 0;
}

.topic-shell {
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.topic-main-scroll {
  min-height: 0;
  overflow: auto;
  padding: 18px 20px;
}

.board-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--orep-border-soft);
  padding: 0 0 18px;
  margin-bottom: 16px;
}

.mode-topic .board-header {
  margin-bottom: 0;
  padding: 18px 20px 14px;
  background: oklch(0.997 0.004 55 / 0.98);
  position: sticky;
  top: 0;
  z-index: 2;
}

.board-header h1 {
  margin: 0;
  font-size: 21px;
  line-height: 1.25;
}

.board-header p {
  margin: 6px 0 0;
  color: var(--orep-muted);
  font-size: 13px;
}

.header-button {
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  background: var(--orep-orange);
  color: white;
  font-weight: 760;
}

.run-pill {
  align-self: flex-start;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-text);
  font-size: 12px;
  font-weight: 800;
}

.run-pill.success {
  background: var(--orep-green-soft);
  color: var(--orep-green);
}

.run-pill.danger {
  background: oklch(0.97 0.035 28);
  color: var(--orep-red);
}

.agent-workflow {
  margin-bottom: 14px;
  padding: 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 10px;
  background: oklch(0.99 0.008 55);
}

.agent-workflow__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.agent-workflow__head strong,
.agent-workflow__head span {
  display: block;
}

.agent-workflow__head span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.agent-workflow__head em {
  padding: 5px 8px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-style: normal;
  font-size: 11px;
  font-weight: 760;
  white-space: nowrap;
}

.agent-step-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(116px, 1fr));
  gap: 8px;
}

.agent-step {
  min-width: 0;
  min-height: 96px;
  padding: 10px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: var(--orep-surface-raised);
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 8px;
  align-content: start;
}

.agent-step.done {
  border-color: oklch(0.83 0.08 145);
  background: oklch(0.975 0.028 145);
}

.agent-step.running {
  border-color: oklch(0.82 0.12 48);
  background: oklch(0.98 0.03 48);
}

.agent-step.failed {
  border-color: oklch(0.82 0.09 32);
  background: oklch(0.976 0.03 38);
}

.agent-step__avatar {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: oklch(0.9 0.05 225);
  color: oklch(0.35 0.035 245);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 850;
}

.agent-step__copy {
  min-width: 0;
}

.agent-step__copy strong,
.agent-step__copy small,
.agent-step b {
  display: block;
}

.agent-step__copy strong {
  font-size: 12px;
}

.agent-step__copy small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 11px;
  line-height: 1.35;
}

.agent-step b {
  grid-column: 1 / -1;
  justify-self: start;
  margin-top: 4px;
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-size: 11px;
}

.agent-step.done b {
  background: var(--orep-green-soft);
  color: var(--orep-green);
}

.agent-step.running b {
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
}

.agent-step.running .agent-step__avatar {
  box-shadow: 0 0 0 4px oklch(0.94 0.05 48);
}

.topic-shell .agent-chain-panel {
  margin-bottom: 14px;
  padding: 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 10px;
  background: oklch(0.995 0.004 55);
}

.topic-shell .agent-chain-list {
  display: grid;
  gap: 10px;
}

.topic-shell .agent-step-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: var(--orep-surface-raised);
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
}

.topic-shell .agent-step-card.running {
  border-color: oklch(0.82 0.12 48);
  background: oklch(0.98 0.03 48);
}

.topic-shell .agent-step-card.completed {
  border-color: oklch(0.83 0.08 145);
  background: oklch(0.985 0.02 145);
}

.topic-shell .agent-step-card.failed {
  border-color: oklch(0.82 0.09 32);
  background: oklch(0.976 0.03 38);
}

.topic-shell .agent-step-index {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: oklch(0.95 0.02 55);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 820;
  font-size: 12px;
}

.topic-shell .agent-step-body {
  min-width: 0;
}

.topic-shell .agent-step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.topic-shell .agent-step-head strong {
  font-size: 13px;
}

.topic-shell .agent-step-head span,
.topic-shell .agent-step-head em {
  color: var(--orep-muted);
  font-size: 12px;
  font-style: normal;
}

.topic-shell .agent-step-head em {
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  font-weight: 760;
}

.topic-shell .agent-step-body p {
  margin: 7px 0 0;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.55;
}

.topic-shell .agent-step-body ul {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--orep-text);
  font-size: 12px;
  line-height: 1.55;
}

.topic-shell .agent-question-row,
.topic-shell .score-matrix {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-shell .agent-question-row span,
.topic-shell .score-cell,
.topic-shell .recommendation-pill {
  max-width: 100%;
  min-height: 26px;
  padding: 5px 8px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  background: oklch(0.985 0.008 55);
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  line-height: 1.35;
}

.topic-shell .recommendation-pill {
  width: fit-content;
  margin-top: 10px;
  color: var(--orep-orange);
  background: var(--orep-orange-soft);
  font-weight: 800;
}

.topic-shell .recommendation-pill.recommended {
  color: var(--orep-green);
  background: var(--orep-green-soft);
}

.topic-shell .recommendation-pill.not_recommended {
  color: var(--orep-red);
  background: oklch(0.97 0.035 28);
}

.topic-shell .score-cell strong {
  margin-left: 6px;
  color: var(--orep-text);
}

.topic-shell .expert-rationale {
  color: var(--orep-muted);
}

.chat-stream {
  padding: 2px 0 14px;
  display: grid;
  gap: 14px;
}

.chat-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.chat-row.mine {
  justify-content: flex-end;
}

.chat-row.pending {
  opacity: 0.78;
}

.chat-avatar.ai {
  background: oklch(0.91 0.035 225);
}

.chat-meta {
  margin-bottom: 6px;
  color: var(--orep-text);
  font-size: 13px;
  font-weight: 780;
}

.chat-meta span {
  margin-left: 8px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 560;
}

.chat-content > p {
  max-width: 560px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.chat-row.typing .chat-content > p::after {
  content: "";
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 3px;
  border-radius: 999px;
  background: var(--orep-orange);
  vertical-align: -2px;
  animation: cursorPulse 0.8s ease-in-out infinite;
}

.chat-row.ai-thinking .chat-content > p {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--orep-muted);
}

.chat-row.ai-thinking .chat-content strong {
  color: var(--orep-text);
}

.chat-row.ai-thinking .chat-content i,
.chat-row.ai-thinking .chat-content i::before,
.chat-row.ai-thinking .chat-content i::after {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: var(--orep-orange);
  display: inline-block;
  animation: typingDot 1s ease-in-out infinite;
}

.chat-row.ai-thinking .chat-content i {
  position: relative;
  margin-left: 2px;
}

.chat-row.ai-thinking .chat-content i::before,
.chat-row.ai-thinking .chat-content i::after {
  content: "";
  position: absolute;
  top: 0;
}

.chat-row.ai-thinking .chat-content i::before {
  left: 9px;
  animation-delay: 0.16s;
}

.chat-row.ai-thinking .chat-content i::after {
  left: 18px;
  animation-delay: 0.32s;
}

.chat-row.mine .chat-content > p {
  border-color: oklch(0.84 0.08 48);
  background: var(--orep-orange-wash);
}

@keyframes cursorPulse {
  0%,
  100% {
    opacity: 0.2;
  }
  45% {
    opacity: 1;
  }
}

@keyframes typingDot {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  45% {
    transform: translateY(-3px);
    opacity: 1;
  }
}

.ai-failure {
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid oklch(0.82 0.09 32);
  border-radius: 9px;
  background: oklch(0.976 0.03 38);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.ai-failure strong,
.ai-failure span {
  display: block;
}

.ai-failure span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.5;
}

.topic-shell .evidence-panel {
  margin-bottom: 14px;
  padding: 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: oklch(0.992 0.006 55);
}

.topic-shell .evidence-panel.collapsed {
  padding: 12px 14px;
}

.mode-topic .topic-shell .evidence-panel p {
  max-height: 116px;
  overflow: auto;
}

.topic-shell .evidence-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.topic-shell .evidence-heading > div {
  min-width: 0;
}

.topic-shell .evidence-heading strong,
.topic-shell .evidence-heading span {
  display: block;
}

.topic-shell .evidence-heading span {
  max-width: 520px;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--orep-muted);
  font-size: 12px;
}

.topic-shell .evidence-heading button,
.topic-shell .section-toggle,
.topic-shell .current-direction-card button {
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  font: inherit;
  font-size: 12px;
  font-weight: 760;
  cursor: pointer;
}

.topic-shell .evidence-heading button,
.topic-shell .section-toggle {
  min-height: 30px;
  padding: 0 10px;
}

.topic-shell .evidence-panel p {
  margin: 10px 0 0;
  color: var(--orep-text);
  font-size: 13px;
  line-height: 1.65;
}

.topic-shell .evidence-list,
.topic-shell .source-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.topic-shell .evidence-list small {
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 26px;
}

.topic-shell .evidence-list span,
.topic-shell .source-row span,
.topic-shell .source-row a {
  max-width: 100%;
  min-height: 26px;
  padding: 5px 8px;
  border-radius: 7px;
  background: var(--orep-bg-soft);
  color: var(--orep-text);
  font-size: 12px;
  line-height: 1.35;
  text-decoration: none;
}

.topic-shell .source-row b {
  margin-right: 5px;
  color: var(--orep-orange);
}

.topic-shell .source-row.compact {
  margin-top: 8px;
}

.topic-shell .source-row.compact span,
.topic-shell .source-row.compact a {
  font-size: 11px;
}

.topic-shell .direction-section {
  border-top: 1px solid var(--orep-border-soft);
  padding-top: 14px;
}

.topic-shell .direction-section.collapsed {
  padding-top: 12px;
}

.section-heading {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-heading strong {
  font-size: 16px;
}

.section-heading span {
  margin-left: 8px;
  color: var(--orep-muted);
  font-size: 12px;
}

.topic-shell .current-direction-card {
  min-height: 58px;
  margin-bottom: 10px;
  padding: 10px 12px;
  border: 1px solid oklch(0.82 0.12 48);
  border-radius: 9px;
  background: oklch(0.985 0.02 48);
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}

.topic-shell .current-direction-card strong,
.topic-shell .current-direction-card small {
  display: block;
}

.topic-shell .current-direction-card strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.topic-shell .current-direction-card small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.topic-shell .current-direction-card button {
  min-height: 30px;
  padding: 0 10px;
  border-color: var(--orep-orange);
  background: var(--orep-orange);
  color: oklch(0.99 0.005 55);
}

.topic-shell .candidate-strip {
  display: grid;
  gap: 8px;
}

.topic-shell .candidate-strip button {
  min-height: 46px;
  padding: 9px 10px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  text-align: left;
  cursor: pointer;
}

.topic-shell .candidate-strip strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.topic-shell .candidate-strip small {
  color: var(--orep-muted);
  font-size: 11px;
}

.generation-strip {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.generation-strip span {
  min-height: 24px;
  margin-left: 0;
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-text);
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 720;
}

.generation-strip b {
  color: var(--orep-orange);
}

.topic-shell .direction-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.mode-topic .topic-shell .direction-grid {
  grid-template-columns: 1fr;
}

.topic-shell .direction-card {
  min-height: 0;
  position: relative;
  padding: 16px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: var(--orep-surface-raised);
}

.mode-topic .topic-shell .direction-card {
  padding: 14px;
}

.mode-topic .topic-shell .direction-card p {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mode-topic .topic-shell .direction-card .gap-list,
.mode-topic .topic-shell .direction-card .detail-strip,
.mode-topic .topic-shell .direction-card .source-row {
  display: none;
}

.topic-shell .generation-badge {
  display: inline-flex;
  min-height: 22px;
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
  font-style: normal;
  font-size: 11px;
  font-weight: 780;
  margin-bottom: 9px;
}

.topic-shell .direction-card.selected {
  border-color: var(--orep-orange);
  box-shadow: inset 0 0 0 1px var(--orep-orange);
}

.topic-shell .selected-corner {
  position: absolute;
  top: 0;
  right: 0;
  width: 28px;
  height: 28px;
  border-radius: 0 8px 0 8px;
  background: var(--orep-orange);
  color: white;
  display: grid;
  place-items: center;
}

.topic-shell .direction-card strong {
  display: block;
  padding-right: 24px;
  font-size: 15px;
}

.topic-shell .tag-row {
  margin-top: 9px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.topic-shell .tag-row span {
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-size: 11px;
}

.topic-shell .direction-card p,
.list-card p {
  margin: 12px 0 0;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.65;
}

.topic-shell .direction-card small,
.list-card small {
  display: block;
  margin-top: 8px;
  color: var(--orep-text);
  font-size: 12px;
}

.topic-shell .gap-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.6;
}

.topic-shell .detail-strip {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 8px;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.45;
}

.topic-shell .detail-strip b {
  color: var(--orep-text);
}

.topic-shell .card-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.topic-shell .card-actions button {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 7px;
  border: 1px solid var(--orep-border-soft);
  background: var(--orep-bg-soft);
  color: var(--orep-text);
  font-size: 12px;
  font-weight: 760;
}

.topic-shell .card-actions button:first-child:not(:disabled) {
  border-color: oklch(0.8 0.12 48);
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
}

.topic-shell .card-actions button:disabled,
.generate-button:disabled,
.prompt-box button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.prompt-box {
  height: 62px;
  margin: 0 20px 18px;
  padding: 0 12px 0 16px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 12px;
  background: var(--orep-surface-raised);
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-topic .prompt-box {
  box-shadow: 0 -10px 24px oklch(0.2 0.012 45 / 0.035);
}

.prompt-box input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--orep-text-strong);
  font: inherit;
}

.prompt-box button {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--orep-text);
}

.ai-note {
  margin: 12px 0 0;
  color: var(--orep-faint);
  text-align: center;
  font-size: 12px;
}

.mode-topic .ai-note {
  display: none;
}

.list-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.workspace-section {
  margin-top: 16px;
}

.workspace-section:first-of-type {
  margin-top: 0;
}

.subsection-heading {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.subsection-heading strong {
  font-size: 14px;
}

.subsection-heading span {
  padding: 4px 7px;
  border-radius: 7px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.workspace-copy {
  margin: 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.65;
}

.material-header {
  align-items: center;
}

.material-actions {
  display: flex;
  gap: 8px;
}

.material-actions button {
  min-width: 96px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 760;
  white-space: nowrap;
  cursor: pointer;
}

.material-actions button svg {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.material-actions button:first-child {
  border-color: oklch(0.74 0.17 43);
  background: var(--orep-orange);
  color: white;
}

.material-workbench {
  min-height: 610px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 316px;
  grid-template-areas:
    "filters filters"
    "list detail";
  gap: 12px 14px;
}

.material-filter,
.material-list-panel,
.material-detail-panel {
  min-width: 0;
  border: 1px solid var(--orep-border-soft);
  border-radius: 10px;
  background: oklch(0.997 0.004 55 / 0.94);
}

.material-filter {
  grid-area: filters;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
}

.material-search {
  flex: 0 0 180px;
  min-height: 36px;
  padding: 0 11px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  color: var(--orep-muted);
  display: flex;
  align-items: center;
  font-size: 12px;
}

.material-filter button {
  flex: 0 0 auto;
  min-height: 36px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--orep-text);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  cursor: pointer;
  white-space: nowrap;
}

.material-filter button.active {
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
}

.material-filter button span {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 740;
}

.material-filter button b {
  min-width: 24px;
  height: 22px;
  border-radius: 6px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  display: inline-grid;
  place-items: center;
  font-size: 11px;
}

.material-list-panel {
  grid-area: list;
  padding: 14px;
}

.material-list-head {
  min-height: 42px;
  margin-bottom: 10px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.material-list-head strong,
.material-list-head span {
  display: block;
}

.material-list-head strong {
  font-size: 16px;
}

.material-list-head span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.material-scope-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.material-scope-legend span {
  margin-top: 0;
  padding: 4px 7px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
}

.material-table {
  display: grid;
  gap: 7px;
}

.material-row {
  min-width: 0;
  min-height: 62px;
  padding: 9px 10px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  display: grid;
  grid-template-columns: 34px minmax(0, 1.3fr) auto auto minmax(90px, 0.7fr) auto;
  gap: 10px;
  align-items: center;
  text-align: left;
  cursor: pointer;
}

.material-row.active {
  border-color: oklch(0.82 0.12 48);
  background: oklch(0.985 0.02 48);
}

.material-main {
  min-width: 0;
}

.material-main strong,
.material-main small {
  display: block;
}

.material-main strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.material-main small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.fact-chip,
.analysis-chip {
  min-height: 26px;
  padding: 5px 8px;
  border-radius: 7px;
  display: inline-grid;
  place-items: center;
  font-size: 12px;
  font-weight: 780;
  white-space: nowrap;
}

.fact-chip.fact {
  background: var(--orep-green-soft);
  color: var(--orep-green);
}

.fact-chip.reference {
  background: oklch(0.94 0.018 245);
  color: oklch(0.42 0.055 245);
}

.fact-chip.pending,
.analysis-chip.pending {
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
}

.analysis-chip.done {
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
}

.analysis-chip.missing {
  background: oklch(0.97 0.035 28);
  color: var(--orep-red);
}

.material-usage {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--orep-muted);
  font-size: 12px;
}

.material-row-actions {
  display: inline-flex;
  justify-content: flex-end;
  gap: 6px;
}

.material-row-actions button,
.material-detail-actions button {
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 7px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  font: inherit;
  font-size: 12px;
  font-weight: 760;
  cursor: pointer;
  white-space: nowrap;
}

.material-row-actions button:first-child,
.material-detail-actions button:first-child {
  border-color: oklch(0.82 0.12 48);
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
}

.material-row-actions button:disabled,
.material-detail-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.material-detail-panel {
  grid-area: detail;
  padding: 14px;
  align-self: start;
  position: sticky;
  top: calc(var(--header-height) + 18px);
}

.material-detail-head {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.material-detail-head strong,
.material-detail-head small {
  display: block;
}

.material-detail-head strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.material-detail-head small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.material-detail-actions {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.material-status-row,
.usage-list {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.material-status-row > span:not(.fact-chip):not(.analysis-chip),
.usage-list span {
  min-height: 26px;
  padding: 5px 8px;
  border-radius: 7px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 720;
}

.material-detail-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--orep-border-soft);
}

.material-detail-section h3 {
  margin: 0 0 8px;
  font-size: 13px;
}

.material-detail-section p,
.material-detail-section blockquote {
  margin: 0;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.65;
}

.material-detail-section blockquote {
  padding: 10px;
  border-radius: 8px;
  background: var(--orep-bg-soft);
  color: var(--orep-text);
}

.material-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 60;
  padding: 24px;
  background: rgb(18 18 18 / 0.26);
  display: grid;
  place-items: center;
}

.material-modal {
  width: min(520px, calc(100vw - 40px));
  padding: 18px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 12px;
  background: var(--orep-surface);
  box-shadow: 0 18px 60px rgb(20 20 20 / 0.18);
}

.material-modal-narrow {
  width: min(420px, calc(100vw - 40px));
}

.material-modal header,
.material-modal footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.material-modal header {
  margin-bottom: 16px;
}

.material-modal header strong {
  font-size: 18px;
}

.material-modal header button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 8px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-size: 18px;
  cursor: pointer;
}

.material-field {
  margin-top: 12px;
  display: grid;
  gap: 8px;
}

.material-field span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.material-field input,
.material-field select {
  width: 100%;
  min-height: 40px;
  padding: 0 11px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  font: inherit;
}

.material-field input[type="file"] {
  padding: 8px 11px;
}

.material-modal-tip {
  margin: 12px 0 0;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.6;
}

.material-modal footer {
  margin-top: 18px;
  justify-content: flex-end;
}

.material-modal footer button {
  min-width: 90px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  font-weight: 780;
  cursor: pointer;
}

.material-modal footer button:last-child {
  border-color: oklch(0.74 0.17 43);
  background: var(--orep-orange);
  color: white;
}

.material-modal footer button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.status-stack {
  margin-bottom: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-chip,
.resource-meta {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 5px 8px;
  border-radius: 7px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 720;
}

.resource-meta {
  margin-top: 12px;
  color: var(--orep-orange);
}

.list-card {
  min-height: 112px;
  padding: 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: var(--orep-surface-raised);
}

.list-card.clickable {
  cursor: pointer;
}

.list-card strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-strip {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stage-strip span {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  font-size: 12px;
}

.artifact-panel {
  display: grid;
  gap: 16px;
  align-content: start;
}

.artifact-group {
  padding: 18px;
}

.artifact-title {
  margin-bottom: 14px;
}

.metric-row {
  min-height: 34px;
  color: var(--orep-muted);
  font-size: 13px;
}

.metric-row strong {
  color: var(--orep-text-strong);
}

.artifact-item {
  min-height: 50px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.artifact-copy {
  min-width: 0;
}

.artifact-copy strong,
.artifact-copy small {
  display: block;
}

.artifact-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.artifact-copy small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.doc-icon {
  width: 32px;
  height: 32px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: var(--orep-surface-raised);
  color: var(--orep-text);
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 850;
}

.doc-icon.word {
  color: oklch(0.5 0.2 260);
}

.doc-icon.orange {
  color: var(--orep-orange);
}

.generate-button,
.sync-button {
  width: 100%;
  height: 38px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 820;
}

.generate-button {
  border: 1px solid var(--orep-orange);
  background: var(--orep-orange);
  color: white;
}

.sync-button {
  border: 1px solid var(--orep-border-soft);
  background: var(--orep-surface-raised);
  color: var(--orep-text);
}

.tpl-list {
  display: grid;
  gap: 10px;
}

.tpl-section-label {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-top: 2px;
}

.tpl-section-label strong {
  color: var(--orep-text-strong);
  font-size: 13px;
  font-weight: 820;
}

.tpl-section-label span {
  color: var(--orep-muted);
  font-size: 12px;
}

.tpl-section-label.template-label {
  margin-top: 8px;
  padding-top: 14px;
  border-top: 1px solid var(--orep-border-soft);
}

.tpl-item {
  width: 100%;
  min-height: 64px;
  padding: 10px 12px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 10px;
  background: var(--orep-surface-raised);
  color: var(--orep-text-strong);
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 18px;
  gap: 12px;
  align-items: center;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease-out,
    background-color 160ms ease-out;
}

.tpl-item:hover:not(:disabled) {
  border-color: oklch(0.66 0.19 43 / 0.36);
  background: var(--orep-orange-soft);
}

.tpl-item.blank {
  border-color: oklch(0.66 0.19 43 / 0.28);
  background: var(--orep-orange-soft);
}

.tpl-item:disabled {
  cursor: wait;
  opacity: 0.68;
}

.tpl-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
  display: grid;
  place-items: center;
}

.tpl-icon.blank {
  background: var(--orep-surface-raised);
  color: var(--orep-orange);
  box-shadow: inset 0 0 0 1px oklch(0.66 0.19 43 / 0.2);
}

.tpl-icon.default {
  background: var(--orep-green-soft);
  color: var(--orep-green);
}

.tpl-body strong,
.tpl-body small {
  display: block;
}

.tpl-body small,
.empty-block small {
  color: var(--orep-muted);
  font-size: 13px;
}

.empty-block {
  min-height: 116px;
  padding: 18px;
  border: 1px dashed var(--orep-border-soft);
  border-radius: 9px;
  background: oklch(0.99 0.004 55 / 0.75);
  display: grid;
  place-content: center;
  gap: 6px;
  text-align: center;
}

.empty-block.compact {
  min-height: 70px;
  padding: 12px;
}

.text-button {
  margin-top: 12px;
  padding: 0;
  background: transparent;
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 760;
}

.document-preview {
  max-height: 62vh;
  overflow: auto;
  padding: 18px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: oklch(0.992 0.004 55);
}

.document-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--orep-text-strong);
  font: 14px/1.8 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

@media (max-width: 1280px) {
  .prep-page {
    grid-template-columns: 76px minmax(0, 1fr);
  }

  .prep-rail .rail-section-title,
  .prep-rail .rail-item span:last-child,
  .prep-rail .rail-collapse span {
    display: none;
  }

  .prep-workbench.mode-topic {
    grid-template-columns: minmax(560px, 1fr) 330px;
  }

  .prep-workbench:not(.mode-topic) {
    grid-template-columns: minmax(0, 1fr);
  }

  .artifact-panel {
    grid-column: 1 / -1;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .mode-topic .artifact-panel {
    grid-column: auto;
    grid-template-columns: 1fr;
  }

  .agent-step-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .prep-page {
    display: block;
  }

  .prep-rail {
    position: sticky;
    top: var(--header-height);
    min-height: auto;
    max-height: none;
    padding: 12px;
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    border-right: 0;
    border-bottom: 1px solid var(--orep-border-soft);
  }

  .rail-item {
    flex: 0 0 auto;
  }

  .prep-workbench {
    padding: 14px;
    display: grid;
    grid-template-columns: 1fr;
  }

  .prep-workbench.mode-topic {
    height: auto;
    min-height: calc(100vh - var(--header-height));
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    grid-template-areas:
      "team"
      "board"
      "artifacts";
    overflow: visible;
  }

  .mode-topic .topic-team-panel {
    grid-template-columns: 1fr;
  }

  .mode-topic .topic-advisor-card {
    height: auto;
    min-height: 54px;
    align-items: flex-start;
    padding: 12px;
  }

  .mode-topic .planning-board {
    max-height: none;
  }

  .topic-shell {
    height: auto;
  }

  .topic-main-scroll {
    overflow: visible;
  }

  .artifact-panel {
    grid-template-columns: 1fr;
  }

  .direction-grid,
  .list-grid,
  .agent-step-list {
    grid-template-columns: 1fr;
  }

  .board-header,
  .section-heading {
    display: grid;
  }
}

.prep-dev-state {
  min-height: min(520px, calc(100vh - 220px));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 24px;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 24px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.76), rgba(255, 248, 242, 0.58));
  color: #253040;
  text-align: center;
  box-shadow: var(--workspace-shadow-soft, 0 18px 46px rgba(49, 32, 22, 0.06));
}

.prep-dev-state__mark {
  width: 58px;
  height: 58px;
  border-radius: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff1e8;
  color: var(--workspace-primary, #f04b23);
  font-size: 16px;
  font-weight: 900;
  box-shadow: inset 0 0 0 1px rgba(240, 75, 35, 0.12);
}

.prep-dev-state h2 {
  margin: 6px 0 0;
  color: #1d2530;
  font-size: 22px;
  line-height: 1.25;
}

.prep-dev-state p {
  max-width: 420px;
  margin: 0;
  color: #7c8796;
  font-size: 14px;
  line-height: 1.7;
}

/* Training topic route: consume the shared workspace surface and card rules. */
.prep-page {
  background: transparent;
}

.prep-workbench.mode-topic {
  height: auto;
  min-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  display: block;
  overflow: visible;
}

.mode-topic .planning-board {
  min-height: min(520px, calc(100vh - 180px));
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
  overflow: hidden;
}

.mode-topic .prep-dev-state {
  min-height: min(520px, calc(100vh - 180px));
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.mode-topic .prep-dev-state__mark {
  border-radius: var(--ds-radius-md);
  color: var(--ds-btn-selected-fg);
  background: var(--ds-orange-wash);
  box-shadow: inset 0 0 0 1px var(--ds-btn-selected-border);
}

.mode-topic .prep-dev-state h2 {
  color: var(--ds-ink-1);
  font-size: var(--ds-text-h2);
}

.mode-topic .prep-dev-state p {
  color: var(--ds-muted);
  font-size: var(--ds-text-body);
}

.mode-script .prep-dev-state {
  min-height: min(520px, calc(100vh - 180px));
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.mode-script .prep-dev-state__mark {
  width: 52px;
  height: 52px;
  border-radius: var(--ds-radius-md, 12px);
  color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-50, #fff7f2);
  box-shadow: inset 0 0 0 1px var(--ds-orange-100, #fee9df);
}

.mode-script .prep-dev-state h2 {
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-h2, 26px);
}

.mode-script .prep-dev-state p {
  color: var(--ds-muted, #6b7280);
  font-size: var(--ds-text-body, 15px);
}

.prep-alert button {
  min-height: var(--ds-btn-height-sm);
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
  padding: 0 var(--ds-btn-padding-x-sm);
  font-size: var(--ds-btn-font-sm);
  font-weight: var(--ds-weight-bold);
}

.prep-alert button:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-btn-secondary-bg-hover);
}

.prep-alert button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.finder-shell {
  min-height: min(720px, calc(100vh - 150px));
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 12px;
  color: #253040;
}

.finder-toolbar {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(240px, 380px) auto;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: var(--workspace-shadow-soft, 0 18px 46px rgba(49, 32, 22, 0.06));
}

.finder-title h1 {
  margin: 0;
  color: #1d2530;
  font-size: 22px;
  line-height: 1.25;
}

.finder-title p {
  margin: 5px 0 0;
  color: #7c8796;
  font-size: 13px;
  line-height: 1.45;
}

.finder-search {
  height: 40px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  padding: 0 12px;
  border: 1px solid rgba(224, 211, 198, 0.72);
  border-radius: 14px;
  background: rgba(255, 252, 248, 0.86);
  color: #9aa2af;
}

.finder-search input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #253040;
  font-size: 13px;
}

.finder-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.finder-actions button,
.finder-row__actions button,
.finder-empty button {
  height: 36px;
  padding: 0 13px;
  border: 1px solid rgba(224, 211, 198, 0.82);
  border-radius: 12px;
  background: rgba(255, 252, 248, 0.9);
  color: #4a5565;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.finder-actions button.primary,
.finder-empty button {
  border-color: transparent;
  background: var(--workspace-primary, #f04b23);
  color: #fff;
}

.finder-actions svg {
  width: 15px;
  height: 15px;
}

.finder-pathbar {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.48);
  color: #7c8796;
  font-size: 13px;
}

.finder-pathbar strong {
  color: #253040;
}

.finder-pathbar i,
.finder-pathbar em {
  color: #9aa2af;
  font-style: normal;
}

.finder-pathbar em {
  margin-left: auto;
}

.finder-window {
  min-height: 0;
  display: grid;
  grid-template-columns: 220px minmax(420px, 1fr) 300px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.64);
  box-shadow: var(--workspace-shadow-soft, 0 18px 46px rgba(49, 32, 22, 0.06));
}

.finder-sidebar,
.finder-inspector {
  min-height: 0;
  overflow: auto;
  background: rgba(255, 248, 242, 0.58);
}

.finder-sidebar {
  padding: 14px 10px;
  border-right: 1px solid rgba(224, 211, 198, 0.58);
}

.finder-sidebar__section {
  display: grid;
  gap: 5px;
  margin-bottom: 16px;
}

.finder-sidebar__section > span {
  padding: 0 10px 4px;
  color: #9aa2af;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.finder-sidebar button {
  width: 100%;
  min-height: 34px;
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #566171;
  text-align: left;
  cursor: pointer;
}

.finder-sidebar button.active,
.finder-sidebar button:hover {
  background: #fff2ea;
  color: var(--workspace-primary, #f04b23);
}

.finder-sidebar svg {
  width: 15px;
  height: 15px;
}

.finder-sidebar b {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.finder-sidebar em {
  min-width: 22px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.74);
  color: #8a94a3;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
  text-align: center;
}

.finder-main {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background: rgba(255, 255, 255, 0.48);
}

.finder-main__head {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(224, 211, 198, 0.58);
}

.finder-main__head strong,
.finder-main__head small {
  display: block;
}

.finder-main__head strong {
  color: #1d2530;
  font-size: 15px;
}

.finder-main__head small {
  margin-top: 3px;
  color: #8a94a3;
  font-size: 12px;
}

.finder-view-toggle {
  display: flex;
  padding: 3px;
  border-radius: 12px;
  background: #f6eee8;
}

.finder-view-toggle button {
  height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #7c8796;
  font-size: 12px;
  font-weight: 800;
}

.finder-view-toggle button.active {
  background: #fff;
  color: #253040;
  box-shadow: 0 2px 8px rgba(49, 32, 22, 0.06);
}

.finder-table {
  min-height: 0;
  overflow: auto;
}

.finder-grid {
  min-height: 0;
  overflow: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
  gap: 12px;
  align-content: start;
  padding: 16px;
}

.finder-file-card {
  min-width: 0;
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(234, 217, 203, 0.72);
  border-radius: 18px;
  background: rgba(255, 252, 248, 0.78);
  cursor: pointer;
}

.finder-file-card:hover,
.finder-file-card.active {
  border-color: rgba(240, 75, 35, 0.28);
  background: #fff5ed;
}

.finder-file-card__preview {
  width: 58px;
  height: 58px;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.finder-file-card__preview .doc-icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  font-size: 16px;
}

.finder-file-card strong,
.finder-file-card small {
  min-width: 0;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.finder-file-card strong {
  color: #1d2530;
  font-size: 13px;
}

.finder-file-card small {
  color: #8a94a3;
  font-size: 12px;
}

.finder-file-card__chips,
.finder-file-card__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.finder-file-card__actions button {
  height: 28px;
  padding: 0 9px;
  border: 1px solid rgba(224, 211, 198, 0.82);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.75);
  color: #4a5565;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.finder-file-card__actions button:disabled,
.finder-file-card__preview:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.finder-table__header,
.finder-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) 150px 160px 112px 128px;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
}

.finder-table__header {
  height: 34px;
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(255, 251, 247, 0.96);
  border-bottom: 1px solid rgba(224, 211, 198, 0.56);
  color: #9aa2af;
  font-size: 12px;
  font-weight: 900;
}

.finder-row {
  min-height: 64px;
  border-bottom: 1px solid rgba(238, 228, 218, 0.72);
  cursor: pointer;
}

.finder-row:hover,
.finder-row.active {
  background: #fff5ed;
}

.finder-row__name {
  min-width: 0;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.finder-row__name strong,
.finder-row__name small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.finder-row__name strong {
  color: #1d2530;
  font-size: 13px;
}

.finder-row__name small,
.finder-row__date {
  color: #8a94a3;
  font-size: 12px;
}

.finder-row__status,
.finder-row__usage,
.finder-row__actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.finder-row__usage em {
  padding: 3px 7px;
  border-radius: 999px;
  background: #fff3ea;
  color: #a14621;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.finder-row__actions button {
  height: 30px;
  padding: 0 9px;
  border-radius: 10px;
  font-size: 12px;
}

.finder-row__actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.finder-inspector {
  padding: 16px;
  border-left: 1px solid rgba(224, 211, 198, 0.58);
}

.finder-inspector .material-detail-head {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 8px 0 16px;
  text-align: center;
}

.finder-inspector .material-detail-head .doc-icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  font-size: 16px;
}

.finder-inspector .material-detail-head strong {
  display: block;
  color: #1d2530;
  font-size: 14px;
  line-height: 1.4;
}

.finder-inspector .material-detail-head small {
  display: block;
  margin-top: 4px;
  color: #8a94a3;
  font-size: 12px;
}

.finder-inspector .material-detail-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}

.finder-inspector .material-detail-actions button {
  height: 34px;
  border: 1px solid rgba(224, 211, 198, 0.82);
  border-radius: 11px;
  background: rgba(255, 252, 248, 0.9);
  color: #4a5565;
  font-size: 12px;
  font-weight: 800;
}

.finder-inspector .material-status-row,
.finder-inspector .usage-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.finder-inspector .material-status-row span,
.finder-inspector .usage-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff3ea;
  color: #a14621;
  font-size: 11px;
  font-weight: 800;
}

.finder-inspector .material-detail-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(224, 211, 198, 0.58);
}

.finder-inspector .material-detail-section h3 {
  margin: 0 0 7px;
  color: #566171;
  font-size: 12px;
}

.finder-inspector .material-detail-section p,
.finder-inspector .material-detail-section blockquote {
  margin: 0;
  color: #6f7a89;
  font-size: 12px;
  line-height: 1.65;
}

.finder-inspector .material-detail-section blockquote {
  padding: 10px;
  border-left: 3px solid rgba(240, 75, 35, 0.32);
  border-radius: 10px;
  background: rgba(255, 252, 248, 0.76);
}

.finder-empty {
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 24px;
  text-align: center;
}

.finder-empty h2 {
  margin: 4px 0 0;
  color: #1d2530;
  font-size: 20px;
}

.finder-empty p {
  max-width: 360px;
  margin: 0;
  color: #7c8796;
  font-size: 13px;
  line-height: 1.65;
}

@media (max-width: 1280px) {
  .finder-toolbar {
    grid-template-columns: 1fr;
  }

  .finder-actions {
    justify-content: flex-start;
  }

  .finder-window {
    grid-template-columns: 200px minmax(0, 1fr);
  }

  .finder-inspector {
    display: none;
  }
}

@media (max-width: 900px) {
  .finder-window {
    grid-template-columns: 1fr;
  }

  .finder-sidebar {
    display: none;
  }

  .finder-table__header,
  .finder-row {
    grid-template-columns: minmax(180px, 1fr) 120px 100px;
  }

  .finder-table__header span:nth-child(3),
  .finder-table__header span:nth-child(4),
  .finder-row__usage,
  .finder-row__date {
    display: none;
  }
}

/* File center: a single business-library surface aligned with home/training. */
.prep-page {
  background: transparent;
}

.prep-page.is-materials {
  display: block;
  min-height: 100%;
  grid-template-columns: minmax(0, 1fr);
}

.prep-workbench.mode-materials {
  width: 100%;
  padding: 0;
  display: block;
}

.mode-materials .planning-board {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.finder-shell {
  min-height: min(720px, calc(100vh - 168px));
  grid-template-rows: auto minmax(520px, 1fr);
  gap: var(--ds-space-5, 20px);
  color: var(--ds-ink-soft, #343944);
}

.finder-toolbar {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--ds-space-4, 16px);
  padding: 0 0 var(--ds-space-1, 4px);
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.finder-title h1 {
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-h1, 24px);
  line-height: 1.2;
  font-weight: var(--ds-weight-bold, 760);
}

.finder-title p {
  margin-top: 7px;
  color: var(--ds-muted, #6b7280);
  font-size: var(--ds-text-caption, 13px);
}

.finder-search {
  height: var(--ds-btn-height-md, 40px);
  width: min(100%, 500px);
  border-color: var(--ds-field-border, #d9dde5);
  border-radius: var(--ds-radius-pill, 999px);
  background: var(--ds-field-bg, #fff);
  color: var(--ds-muted, #6b7280);
}

.finder-search:focus-within {
  border-color: var(--ds-orange-400, #f47b4f);
  box-shadow: 0 0 0 3px rgba(240, 75, 24, 0.1);
}

.finder-actions button,
.finder-row__actions button,
.finder-empty button {
  height: var(--ds-btn-height-md, 40px);
  border-color: var(--ds-btn-secondary-border, #d9dde5);
  border-radius: var(--ds-radius-pill, 999px);
  background: var(--ds-btn-secondary-bg, #fff);
  color: var(--ds-btn-secondary-fg, #343944);
  box-shadow: none;
}

.finder-actions button:hover,
.finder-row__actions button:hover:not(:disabled) {
  border-color: var(--ds-btn-secondary-border-hover, #c8cdd7);
  background: var(--ds-btn-secondary-bg-hover, #f7f8fa);
}

.finder-actions button.primary,
.finder-empty button {
  border-color: var(--ds-orange-700, #d94312);
  background: var(--ds-orange-700, #d94312);
}

.finder-actions button.primary:hover,
.finder-empty button:hover {
  border-color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-800, #b12f0a);
}

.finder-window {
  min-height: 520px;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto minmax(0, 1fr);
  border: 1px solid var(--ds-card-border, #e5e7eb);
  border-radius: 18px;
  background: var(--ds-card-bg, #fff);
  box-shadow: var(--ds-card-shadow, 2px 4px 12px rgba(18, 20, 26, 0.08));
}

.finder-library-controls {
  display: grid;
  grid-template-columns: minmax(280px, 500px) minmax(220px, 1fr);
  align-items: center;
  gap: var(--ds-space-5, 20px);
  padding: var(--ds-space-5, 20px) 22px var(--ds-space-4, 16px);
}

.finder-library-meta {
  display: grid;
  justify-items: end;
  gap: 4px;
  text-align: right;
}

.finder-library-meta strong {
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-body, 15px);
}

.finder-library-meta span {
  color: var(--ds-muted, #6b7280);
  font-size: var(--ds-text-caption, 13px);
}

.finder-filterbar {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 22px var(--ds-space-4, 16px);
  border-bottom: 1px solid var(--ds-line-soft, #eceef2);
}

.finder-filterbar button {
  min-width: max-content;
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid transparent;
  border-radius: var(--ds-radius-sm, 8px);
  background: var(--ds-surface-subtle, #f5f6f8);
  color: var(--ds-muted, #6b7280);
  font-size: var(--ds-text-caption, 13px);
  font-weight: var(--ds-weight-semibold, 650);
  cursor: pointer;
}

.finder-filterbar button:hover {
  color: var(--ds-ink-soft, #343944);
  background: #eef0f3;
}

.finder-filterbar button.active {
  border-color: var(--ds-orange-100, #fee9df);
  color: var(--ds-orange-800, #b12f0a);
  background: var(--ds-orange-50, #fff7f2);
}

.finder-filterbar button em {
  min-width: 18px;
  font-size: 11px;
  font-style: normal;
  text-align: center;
}

.finder-filterbar__divider {
  width: 1px;
  height: 20px;
  flex: 0 0 auto;
  margin: 0 4px;
  background: var(--ds-line, #e5e7eb);
}

.finder-filterbar__label {
  flex: 0 0 auto;
  margin-right: 2px;
  color: var(--ds-muted-light, #8b919d);
  font-size: 12px;
  font-weight: var(--ds-weight-semibold, 650);
}

.finder-main {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background: var(--ds-card-bg, #fff);
}

.finder-main__head {
  min-height: 64px;
  padding: 12px 22px;
  border-bottom-color: var(--ds-line-soft, #eceef2);
}

.finder-main__head strong {
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-h3, 17px);
}

.finder-main__hint {
  color: var(--ds-muted-light, #8b919d);
  font-size: var(--ds-text-caption, 13px);
}

.finder-table__header,
.finder-row {
  grid-template-columns: minmax(260px, 1.7fr) minmax(130px, 0.85fr) minmax(120px, 0.85fr) 92px 124px;
  gap: 16px;
  padding-right: 22px;
  padding-left: 22px;
}

.finder-table__header {
  height: 40px;
  background: var(--ds-surface-subtle, #f8f9fb);
  border-bottom-color: var(--ds-line-soft, #eceef2);
  color: var(--ds-muted-light, #8b919d);
}

.finder-table__item:last-child .finder-row {
  border-bottom: 0;
}

.finder-table--loading {
  pointer-events: none;
}

.finder-row--skeleton {
  cursor: default;
}

.finder-row--skeleton:hover {
  background: transparent;
}

.finder-skeleton {
  width: 78%;
  height: 12px;
  border-radius: var(--ds-radius-pill, 999px);
  background: linear-gradient(
    90deg,
    var(--ds-surface-subtle, #f4f5f7) 0%,
    var(--ds-line-soft, #e8eaee) 45%,
    var(--ds-surface-subtle, #f4f5f7) 100%
  );
  background-size: 220% 100%;
  animation: finder-skeleton-shift 1.4s ease-in-out infinite;
}

.finder-skeleton--name {
  width: min(82%, 320px);
  height: 14px;
}

.finder-row--skeleton .finder-row__status {
  width: 74%;
}

.finder-row--skeleton .finder-row__usage {
  width: 68%;
}

.finder-row--skeleton .finder-row__date {
  width: 64%;
}

.finder-row--skeleton .finder-row__actions {
  width: 84px;
  justify-self: end;
}

@keyframes finder-skeleton-shift {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .finder-skeleton {
    animation: none;
  }
}

.finder-row {
  min-height: 72px;
  border-bottom-color: var(--ds-line-soft, #eceef2);
}

.finder-row:focus-visible {
  position: relative;
  z-index: 1;
  outline: var(--ds-focus-outline, 2px solid #f47b4f);
  outline-offset: -2px;
}

.finder-row:hover,
.finder-row.active {
  background: var(--ds-orange-50, #fff7f2);
}

.finder-row__actions {
  justify-content: flex-end;
}

.finder-row__actions button {
  height: 30px;
  padding: 0 9px;
  border-radius: var(--ds-radius-sm, 8px);
}

.finder-detail-inline {
  margin: 12px 16px 18px;
  padding: 0 18px 18px;
  border: 1px solid var(--ds-line-soft, #eceef2);
  border-radius: var(--ds-radius-md, 12px);
  background: var(--ds-surface-subtle, #f7f8fa);
}

.finder-detail-inline__top {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--ds-line-soft, #eceef2);
}

.finder-detail-inline__top > strong {
  color: var(--ds-ink, #12141a);
  font-size: var(--ds-text-body, 15px);
}

.finder-detail-inline__top > span {
  color: var(--ds-muted-light, #8b919d);
  font-size: var(--ds-text-caption, 13px);
}

.finder-detail-inline__content {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 32px;
  padding: 16px 0 0;
}

.finder-detail-inline .material-detail-section {
  grid-column: auto;
  margin: 0;
  padding: 0;
  border-top: 0;
  border-bottom: 0;
}

.finder-detail-inline .material-detail-section h3 {
  margin: 0 0 7px;
  color: var(--ds-ink-soft, #343944);
  font-size: 12px;
}

.finder-detail-inline .material-detail-section p {
  margin: 0;
  color: var(--ds-muted, #6b7280);
  font-size: 13px;
  line-height: 1.65;
}

@media (max-width: 1180px) {
  .finder-table__header,
  .finder-row {
    grid-template-columns: minmax(220px, 1fr) 132px 92px 124px;
  }

  .finder-table__header span:nth-child(3),
  .finder-row__usage {
    display: none;
  }
}

@media (max-width: 900px) {
  .finder-library-controls {
    grid-template-columns: 1fr;
  }

  .finder-library-meta {
    justify-items: start;
    text-align: left;
  }

  .finder-table__header,
  .finder-row {
    grid-template-columns: minmax(200px, 1fr) 92px 124px;
  }

  .finder-table__header span:nth-child(2),
  .finder-row__status {
    display: none;
  }

  .finder-detail-inline__content {
    grid-template-columns: 1fr;
  }

  .finder-detail-inline .material-detail-section {
    grid-column: 1;
  }
}

@media (max-width: 720px) {
  .prep-workbench.mode-materials {
    padding: 0;
  }

  .finder-shell {
    min-height: auto;
    grid-template-rows: auto minmax(480px, auto);
  }

  .finder-toolbar {
    grid-template-columns: 1fr;
  }

  .finder-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    justify-content: stretch;
  }

  .finder-library-controls {
    padding: 16px 14px 12px;
  }

  .finder-library-meta span,
  .finder-main__hint,
  .finder-table__header {
    display: none;
  }

  .finder-filterbar {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 0 14px 12px;
    scrollbar-width: thin;
  }

  .finder-main__head {
    min-height: 58px;
    padding: 10px 14px;
  }

  .finder-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    min-height: 72px;
    padding: 10px 14px;
  }

  .finder-row__status,
  .finder-row__usage,
  .finder-row__date,
  .finder-row__actions button:first-child {
    display: none;
  }

  .finder-detail-inline {
    margin: 10px 10px 14px;
    padding: 0 14px 14px;
  }

  .finder-detail-inline__content {
    padding: 14px 0 0;
  }
}

/* 讲稿与 PPT 准备工作台：与首页、训练营共用暖中性画布和橙色行动体系。 */
.prep-workbench.mode-script,
.prep-workbench.mode-ppt {
  box-sizing: border-box;
  min-height: calc(100vh - var(--workspace-header-height));
  padding: 0;
  display: block;
  background: transparent;
}

.prep-ai-app-shell {
  min-height: calc(100vh - var(--workspace-header-height));
}

.prep-ai-app-shell .planning-board {
  min-height: 0;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.prep-ai-app-header .header-button {
  min-height: var(--ds-btn-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: 0 var(--ds-btn-padding-x);
  border: 1px solid var(--ds-btn-primary-bg);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
  font-size: var(--ds-btn-font);
  font-weight: var(--ds-weight-bold);
}

.prep-ai-app-header .header-button:hover {
  border-color: var(--ds-btn-primary-bg-hover);
  background: var(--ds-btn-primary-bg-hover);
}

.prep-ai-app-header .header-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.prep-product-workspace {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-6);
  color: var(--ds-ink-2);
}

.ppt-workspace-entry {
  min-height: 88px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
  padding: var(--ds-space-5) var(--ds-space-6);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
}

.ppt-workspace-entry strong,
.ppt-workspace-entry small {
  display: block;
}

.ppt-workspace-entry small {
  margin-top: var(--ds-space-1);
  color: var(--ds-muted);
}

.script-row-open:focus-visible,
.script-row .text-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.workspace-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--ds-line);
  border-bottom: 1px solid var(--ds-line);
}

.workspace-summary > div {
  min-height: 104px;
  padding: var(--ds-space-5) var(--ds-space-6);
  border-right: 1px solid var(--ds-line);
}

.workspace-summary > div:first-child {
  padding-left: 0;
}

.workspace-summary > div:last-child {
  border-right: 0;
}

.workspace-summary span,
.workspace-summary small {
  display: block;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.workspace-summary strong {
  display: block;
  margin: var(--ds-space-2) 0 var(--ds-space-1);
  color: var(--ds-ink);
  font-family: var(--ds-font-num);
  font-size: 22px;
  line-height: 1.2;
  font-weight: var(--ds-weight-bold);
}

.script-library {
  overflow: hidden;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.script-empty {
  min-height: min(520px, calc(100vh - var(--workspace-header-height) - 180px));
  display: grid;
  align-content: center;
  justify-items: center;
  gap: var(--ds-space-5);
  padding: var(--ds-space-10) var(--ds-space-6);
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-surface-solid);
  text-align: center;
}

.script-empty__icon {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border: 1px solid var(--ds-orange-100);
  border-radius: var(--ds-radius-md);
  background: var(--ds-orange-50);
  color: var(--ds-orange-700);
}

.script-empty__icon svg {
  width: 24px;
  height: 24px;
}

.script-empty__copy {
  max-width: 560px;
}

.script-empty__copy h2,
.script-empty__copy p {
  margin: 0;
}

.script-empty__copy h2 {
  color: var(--ds-ink);
  font-size: var(--ds-text-h2);
  line-height: 1.3;
}

.script-empty__copy p {
  margin-top: var(--ds-space-2);
  color: var(--ds-muted);
  font-size: var(--ds-text-body);
  line-height: 1.65;
}

.script-empty__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
}

.script-empty__primary,
.script-empty__secondary {
  min-height: var(--ds-btn-height);
  padding: 0 var(--ds-btn-padding-x);
  border-radius: var(--ds-radius-pill);
  font-size: var(--ds-btn-font);
  font-weight: var(--ds-weight-bold);
  cursor: pointer;
}

.script-empty__primary {
  border: 1px solid var(--ds-btn-primary-bg);
  background: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
}

.script-empty__primary:hover {
  border-color: var(--ds-btn-primary-bg-hover);
  background: var(--ds-btn-primary-bg-hover);
}

.script-empty__secondary {
  border: 1px solid var(--ds-btn-secondary-border);
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
}

.script-empty__secondary:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-btn-secondary-bg-hover);
}

.script-empty__primary:focus-visible,
.script-empty__secondary:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.script-library-head {
  min-height: 68px;
  padding: 0 var(--ds-space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-line);
}

.script-library-head strong,
.script-library-head small {
  display: block;
}

.script-library-head strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-h3);
}

.script-library-head small,
.script-library-head > span {
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.script-library-head__actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.script-library-head__actions > span {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.script-list {
  display: grid;
}

.script-row {
  min-height: 76px;
  padding: 0 var(--ds-space-6);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-line);
  transition: background-color var(--ds-control-transition);
}

.script-row-open {
  min-width: 0;
  min-height: 76px;
  padding: 0;
  display: grid;
  grid-template-columns: 44px minmax(220px, 1fr) 96px 24px;
  align-items: center;
  gap: var(--ds-space-4);
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.script-row:last-child {
  border-bottom: 0;
}

.script-row:hover {
  background: var(--ds-orange-50);
}

.script-row-index {
  color: var(--ds-faint);
  font-family: var(--ds-font-num);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-bold);
}

.script-row-copy {
  min-width: 0;
}

.script-row-copy strong,
.script-row-copy small {
  display: block;
}

.script-row-copy strong {
  overflow: hidden;
  color: var(--ds-ink);
  font-size: var(--ds-text-body);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-row-copy small,
.script-row-source {
  margin-top: 5px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.script-row-source {
  margin-top: 0;
}

.script-row .text-button {
  min-height: var(--ds-btn-height-sm);
  padding: 0 var(--ds-btn-padding-x-sm);
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
  font-size: var(--ds-btn-font-sm);
  font-weight: var(--ds-weight-bold);
}

.script-row .text-button:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-btn-secondary-bg-hover);
}

.script-row-arrow {
  color: var(--ds-orange-700);
  font-size: 18px;
}

.script-list-loading {
  display: grid;
  gap: var(--ds-space-3);
}

.script-list-loading span {
  height: 76px;
  border-radius: var(--ds-radius-md);
  background: linear-gradient(90deg, #eceef1 20%, #f6f6f8 50%, #eceef1 80%);
  background-size: 240% 100%;
  animation: prep-list-loading 1.4s ease-in-out infinite;
}

@keyframes prep-list-loading {
  to { background-position: -160% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .script-list-loading span {
    animation: none;
  }
}

@media (max-width: 900px) {
  .workspace-summary {
    grid-template-columns: 1fr;
  }

  .workspace-summary > div,
  .workspace-summary > div:first-child {
    min-height: 84px;
    padding: var(--ds-space-4) 0;
    border-right: 0;
    border-bottom: 1px solid var(--ds-line);
  }

  .workspace-summary > div:last-child {
    border-bottom: 0;
  }

  .script-row {
    grid-template-columns: minmax(0, 1fr);
    padding: var(--ds-space-3) var(--ds-space-4);
  }

  .script-row-open {
    min-height: 52px;
    grid-template-columns: 34px minmax(0, 1fr) 24px;
  }

  .script-row-source,
  .script-row .text-button {
    display: none;
  }
}

@media (max-width: 600px) {
  .prep-ai-app-header .header-button {
    width: var(--ds-btn-height);
    min-width: var(--ds-btn-height);
    padding: 0;
  }

  .prep-ai-app-header .header-button span {
    display: none;
  }

  .script-empty {
    min-height: 420px;
    padding: var(--ds-space-8) var(--ds-space-4);
  }

  .script-empty__actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
  }

  .script-empty__primary,
  .script-empty__secondary {
    width: 100%;
  }

  .ppt-workspace-entry,
  .script-library-head {
    align-items: stretch;
    flex-direction: column;
    padding: var(--ds-space-4);
  }

  .ppt-workspace-entry .script-empty__primary,
  .script-library-head__actions .script-empty__primary {
    width: 100%;
  }

  .script-library-head__actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
