<template>
  <AiAppShell class="script-editor" mode="workspace" width="fluid">
    <template #header>
      <AiAppHeader
        app="script"
        mode="workspace"
        back-label="讲稿列表"
        back-to="/script-editor"
        context="讲稿制作 · 编辑器"
        v-model:title="scriptTitle"
        :editable-title="canUseEditor"
        :title-maxlength="100"
        title-label="讲稿标题"
        :status="headerStatus"
        @title-blur="autoSave"
      >
        <template #actions>
          <el-button
            class="template-btn"
            :loading="templateSaving"
            :disabled="!hasValidContent || templateSaving || exporting"
            @click="showSaveAsTemplate = true"
          >
            <el-icon><FolderAdd /></el-icon>
            <span>存为模板</span>
          </el-button>
          <el-dropdown
            class="script-mobile-more"
            trigger="click"
            @command="handleHeaderMoreAction"
          >
            <el-button
              class="script-more-button"
              :loading="templateSaving"
              :disabled="!hasValidContent || templateSaving || exporting"
              aria-label="更多操作"
              title="更多操作"
            >
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  command="save-template"
                  :disabled="!hasValidContent || templateSaving || exporting"
                >存为模板</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button
            class="ask-xiaoqi-btn ask-xiaoqi-btn--header"
            :disabled="!scriptId || loadingScript"
            @click="askXiaoQiFromHeader"
          >问小启</el-button>
          <el-button
            class="template-btn"
            :disabled="!scriptId || loadingScript"
            @click="openSdocWorkbench"
          >在智能文档中改稿</el-button>
          <el-button
            type="primary"
            class="export-btn"
            aria-label="导出 PDF"
            :loading="exporting"
            :disabled="!hasValidContent || exporting || templateSaving"
            @click="exportPdf"
          >
            <el-icon><Download /></el-icon>
            <span>导出 PDF</span>
          </el-button>
        </template>
      </AiAppHeader>
    </template>

    <section v-if="loadingScript" class="editor-state" role="status" aria-live="polite">
      <el-icon class="editor-state-icon is-loading"><Loading /></el-icon>
      <h2>正在打开讲稿</h2>
      <p>正在同步章节、角色和最近一次保存内容。</p>
    </section>

    <section v-else-if="loadError" class="editor-state editor-state-error" role="alert">
      <el-icon class="editor-state-icon"><WarningFilled /></el-icon>
      <h2>讲稿暂时没有加载出来</h2>
      <p>{{ loadError }}</p>
      <div class="editor-state-actions">
        <el-button type="primary" @click="loadScript">重新加载</el-button>
      </div>
    </section>

    <div v-else class="editor-body">
      <aside class="chapter-nav" aria-label="讲稿章节大纲">
        <div class="nav-overview">
          <div>
            <span>讲稿总时长</span>
            <strong>{{ totalDuration }}<small>min</small></strong>
          </div>
          <div class="overview-counts">
            <span>{{ chapters.length }} 个章节</span>
            <span>{{ totalSteps }} 个步骤</span>
          </div>
        </div>

        <div class="nav-section-heading">
          <span>章节大纲</span>
          <small>点击切换</small>
        </div>
        <div class="chapter-list">
          <div
            v-for="(ch, idx) in chapters"
            :key="ch.id"
            class="chapter-item"
            :class="{ active: activeChapterIdx === idx }"
          >
            <button
              type="button"
              class="chapter-select"
              :aria-pressed="activeChapterIdx === idx"
              :aria-current="activeChapterIdx === idx ? 'true' : undefined"
              @click="activeChapterIdx = idx"
            >
              <span class="ch-label">
                <span class="ch-number">{{ idx + 1 }}</span>
                <span class="ch-name-wrap">
                  <span class="ch-name">{{ ch.title }}</span>
                  <small>{{ ch.steps?.length || 0 }} 个步骤</small>
                </span>
              </span>
              <span class="duration-pill">{{ ch.totalDuration }}min</span>
            </button>
            <button
              v-if="chapters.length > 1"
              type="button"
              class="chapter-delete"
              :aria-label="`删除章节：${ch.title}`"
              @click="removeChapter(idx)"
            >
              <el-icon><Delete /></el-icon>
            </button>
          </div>
        </div>
        <el-button class="add-chapter-btn" @click="addChapter" text type="primary">
          <el-icon><Plus /></el-icon> 添加章节
        </el-button>

        <button type="button" class="roles-entry" @click="showRolesDrawer = true">
          <span class="roles-entry-copy">
            <strong>团队角色</strong>
            <small>{{ roles.length }} 个角色已配置</small>
          </span>
          <span class="role-preview" aria-hidden="true">
            <i
              v-for="role in roles.slice(0, 4)"
              :key="role.id"
              :style="{ background: role.color }"
            ></i>
          </span>
          <span class="roles-entry-action">管理</span>
        </button>
      </aside>

      <section class="chapter-detail" v-if="activeChapter">
        <div class="detail-header">
          <div class="chapter-title-block">
            <span class="editor-kicker">当前章节 · {{ activeChapterIdx + 1 }}/{{ chapters.length }}</span>
            <el-input
              v-model="activeChapter.title"
              placeholder="章节标题"
              class="chapter-title-input"
              maxlength="80"
              @blur="autoSave"
            />
          </div>
          <div class="detail-meta">
            <span class="detail-meta-label">章节时长</span>
            <el-input-number
              v-model="activeChapter.totalDuration"
              :min="0"
              :max="120"
              size="small"
              controls-position="right"
              aria-label="章节时长（分钟）"
              @change="autoSave"
            />
            <span class="unit">分钟</span>
          </div>
        </div>

        <div class="chapter-summary-bar" aria-label="章节摘要">
          <div class="summary-item">
            <span>步骤</span>
            <strong>{{ activeChapter.steps?.length || 0 }}</strong>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-item">
            <span>本章时长</span>
            <strong>{{ activeChapter.totalDuration }} 分钟</strong>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-item summary-save">
            <span>保存状态</span>
            <strong :class="['summary-save-status', `is-${saveStatus}`]">
              {{ saveStatus === 'pending' ? '等待保存' : saveStatus === 'saving' ? '正在保存' : saveStatus === 'error' ? '保存失败' : '已自动保存' }}
            </strong>
          </div>
        </div>

        <div class="steps-container">
          <section v-if="!activeChapter.steps?.length" class="empty-steps" aria-labelledby="empty-step-title">
            <span class="empty-step-icon"><el-icon><Plus /></el-icon></span>
            <div>
              <h2 id="empty-step-title">开始写这一章节</h2>
              <p>把本章拆成清晰的讲解步骤，再为每一步补充角色、时长和讲解正文。</p>
            </div>
            <el-button type="primary" @click="addStep">
              <el-icon><Plus /></el-icon>
              添加第一个步骤
            </el-button>
          </section>

          <TransitionGroup name="step-list">
            <article
              v-for="(step, sIdx) in activeChapter.steps"
              :key="step.id"
              class="step-card"
            >
              <div class="step-header">
                <div class="step-number">
                  <span>{{ String(sIdx + 1).padStart(2, '0') }}</span>
                  <div>
                    <strong>讲解步骤 {{ sIdx + 1 }}</strong>
                    <small>{{ step.role || '未指定角色' }} · {{ step.duration || 0 }} 分钟</small>
                  </div>
                </div>
                <div class="step-actions">
                  <el-button
                    text
                    size="small"
                    :aria-label="`上移步骤 ${sIdx + 1}`"
                    @click="moveStep(sIdx, -1)"
                    :disabled="sIdx === 0"
                  >
                    <el-icon><Top /></el-icon>
                  </el-button>
                  <el-button
                    text
                    size="small"
                    :aria-label="`下移步骤 ${sIdx + 1}`"
                    @click="moveStep(sIdx, 1)"
                    :disabled="sIdx === activeChapter.steps.length - 1"
                  >
                    <el-icon><Bottom /></el-icon>
                  </el-button>
                  <el-button
                    text
                    size="small"
                    type="danger"
                    :aria-label="`删除步骤 ${sIdx + 1}`"
                    @click="removeStep(sIdx)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>

              <div class="step-fields">
                <div class="step-meta-grid">
                  <div class="field-group role-field">
                    <label>讲解角色</label>
                    <el-select v-model="step.role" placeholder="选择角色" @change="autoSave">
                      <el-option
                        v-for="r in roles"
                        :key="r.id"
                        :label="r.label"
                        :value="r.label"
                      >
                        <span class="role-option">
                          <span class="role-dot" :style="{ background: r.color }"></span>
                          {{ r.label }}
                        </span>
                      </el-option>
                    </el-select>
                  </div>
                  <div class="field-group duration-field">
                    <label>预计时长</label>
                    <el-input-number
                      v-model="step.duration"
                      :min="0"
                      :max="60"
                      size="default"
                      controls-position="right"
                      @change="autoSave"
                    >
                      <template #suffix>min</template>
                    </el-input-number>
                  </div>
                  <div class="field-group focus-field">
                    <label>讲解焦点</label>
                    <el-input v-model="step.focus" placeholder="如：开场致辞、技术架构介绍" @blur="autoSave" />
                  </div>
                </div>

                <div class="field-group script-body-field">
                  <div class="field-label-row">
                    <label>讲解正文</label>
                    <span>按现场表达方式直接书写</span>
                    <button
                      type="button"
                      class="ask-xiaoqi-btn"
                      @mousedown.prevent
                      @click="askXiaoQi(step)"
                    >问小启</button>
                  </div>
                  <el-input
                    v-model="step.content"
                    type="textarea"
                    :rows="6"
                    placeholder="在这里写下这一段现场要说的话……"
                    @blur="autoSave"
                    @mouseup="onStepContentSelect($event, step)"
                    @keyup="onStepContentSelect($event, step)"
                    class="content-textarea"
                  />
                </div>

                <details class="support-details" :open="Boolean(step.notes || step.transition)">
                  <summary>
                    <span>演示提示与转场</span>
                    <small>{{ step.notes || step.transition ? '已补充' : '可选' }}</small>
                  </summary>
                  <div class="support-fields">
                    <div class="field-group">
                      <label>演示提示</label>
                      <el-input v-model="step.notes" placeholder="如：目光交流、切换演示画面" @blur="autoSave" />
                    </div>
                    <div class="field-group">
                      <label>转场话术</label>
                      <el-input v-model="step.transition" placeholder="如：接下来请下一位介绍" @blur="autoSave" />
                    </div>
                  </div>
                </details>
              </div>
            </article>
          </TransitionGroup>
        </div>

        <el-button
          v-if="activeChapter.steps?.length"
          class="add-step-btn"
          @click="addStep"
          type="primary"
          plain
        >
          <el-icon><Plus /></el-icon> 添加步骤
        </el-button>
      </section>
    </div>

    <el-drawer
      v-model="showRolesDrawer"
      class="script-role-drawer"
      title="团队角色"
      size="380px"
      append-to-body
    >
      <div class="drawer-intro">
        <strong>管理讲解分工</strong>
        <p>角色会出现在每个讲解步骤的角色选择中。</p>
      </div>
      <div class="role-manager-list">
        <div v-for="role in roles" :key="role.id" class="role-manager-item">
          <span class="role-manager-dot" :style="{ background: role.color }"></span>
          <span>{{ role.label }}</span>
          <el-button
            text
            type="danger"
            :aria-label="`删除角色：${role.label}`"
            @click="removeRole(role.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
      <el-button class="drawer-add-role" type="primary" plain @click="addRole">
        <el-icon><Plus /></el-icon>
        添加角色
      </el-button>
    </el-drawer>

    <!-- 添加角色对话框 -->
    <el-dialog v-model="showRoleDialog" title="添加角色" width="400px">
      <el-form label-width="60px">
        <el-form-item label="名称">
          <el-input v-model="newRoleLabel" placeholder="如：项目经理" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="newRoleColor" :predefine="presetColors" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRoleDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddRole">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加章节对话框 -->
    <el-dialog v-model="showChapterDialog" title="添加章节" width="450px">
      <el-form label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="newChapterTitle" placeholder="如：技术架构详解" />
        </el-form-item>
        <el-form-item label="时长">
          <el-input-number v-model="newChapterDuration" :min="1" :max="60" />
          <span class="unit">分钟</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChapterDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddChapter">确定</el-button>
      </template>
    </el-dialog>

    <!-- 另存为模板对话框 -->
    <el-dialog v-model="showSaveAsTemplate" title="另存为模板" width="450px">
      <el-form label-width="70px">
        <el-form-item label="名称">
          <el-input v-model="newTemplateName" :placeholder="scriptTitle + ' 模板'" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newTemplateDesc" type="textarea" :rows="2" placeholder="简要描述此模板的用途" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveAsTemplate = false">取消</el-button>
        <el-button
          type="primary"
          :loading="templateSaving"
          :disabled="templateSaving || !hasValidContent"
          @click="confirmSaveAsTemplate"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </AiAppShell>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { createRequestLifecycle } from '../utils/requestLifecycle'
import {
  createScriptSaveCoordinator,
  runAfterSuccessfulSave,
} from '../utils/scriptSaveCoordinator'
import AiAppHeader from '../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../components/ai-apps/AiAppShell.vue'
import { clipStepText, writeScriptStepContext } from '../modules/assistant-core/scriptStepContext'
import {
  Download, WarningFilled, Loading,
  Plus, Delete, Top, Bottom, FolderAdd, MoreFilled
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const scriptIdParam = route.params.scriptId
const templateIdParam = route.params.templateId
const scriptRequestLifecycle = createRequestLifecycle()
let currentPersistenceSignal = null

// ===== 状态 =====
const scriptId = ref(null)
const scriptTitle = ref('路演讲稿')
const scriptSourceType = ref('manual')
const scriptPptJobId = ref('')
const scriptContentVersion = ref(1)
const xiaoQiAsk = ref(null)
const chapters = ref([])
const roles = ref([])
const loadingScript = ref(true)
const loadError = ref('')
const activeChapterIdx = ref(0)
const saveStatus = ref('idle') // idle | pending | saving | saved | error
const exporting = ref(false)
const templateSaving = ref(false)

// 对话框
const showRoleDialog = ref(false)
const showRolesDrawer = ref(false)
const newRoleLabel = ref('')
const newRoleColor = ref('#409EFF')
const showChapterDialog = ref(false)
const newChapterTitle = ref('')
const newChapterDuration = ref(5)
const showSaveAsTemplate = ref(false)
const newTemplateName = ref('')
const newTemplateDesc = ref('')

const presetColors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#8B5CF6', '#EC4899', '#14B8A6']

const activeChapter = computed(() => chapters.value[activeChapterIdx.value] || null)

const totalDuration = computed(() => chapters.value.reduce((sum, ch) => sum + (Number(ch.totalDuration) || 0), 0))

const totalSteps = computed(() => chapters.value.reduce((sum, ch) => sum + (ch.steps?.length || 0), 0))

const canUseEditor = computed(() => !loadingScript.value && !loadError.value)
const hasValidContent = computed(() => (
  canUseEditor.value
  && Boolean(scriptTitle.value.trim())
  && chapters.value.length > 0
))

const saveText = computed(() => {
  if (saveStatus.value === 'pending') return '等待保存'
  if (saveStatus.value === 'saving') return '保存中...'
  if (saveStatus.value === 'saved') return '已保存'
  if (saveStatus.value === 'error') return '保存失败'
  return ''
})

const headerStatus = computed(() => {
  if (loadingScript.value) return '正在加载'
  if (loadError.value) return '加载失败'
  return saveText.value || '自动保存'
})

function handleHeaderMoreAction(command) {
  if (
    command === 'save-template'
    && hasValidContent.value
    && !templateSaving.value
    && !exporting.value
  ) {
    showSaveAsTemplate.value = true
  }
}

// ===== UUID 生成 =====
let _uid = 0
function uid() {
  return 's' + Date.now().toString(36) + (++_uid)
}

// ===== 默认模板 =====
function createDefaultTemplate() {
  return [
    {
      id: uid(), title: '开场+项目背景', totalDuration: 5,
      steps: [
        { id: uid(), role: '主讲人A', duration: 0.5, focus: '封面（P01）', content: '', notes: '自信、目光交流', transition: '' },
        { id: uid(), role: '主讲人A', duration: 0.25, focus: '目录（P02）', content: '', notes: '', transition: '首先来看项目背景。' },
        { id: uid(), role: '主讲人A', duration: 0.67, focus: '时事新闻（P03）', content: '', notes: '', transition: '' },
        { id: uid(), role: '主讲人A', duration: 0.67, focus: '政策背景（P04）', content: '', notes: '', transition: '' },
        { id: uid(), role: '主讲人A', duration: 0.67, focus: '市场考察（P05）', content: '', notes: '用数据说话', transition: '' },
      ]
    },
    {
      id: uid(), title: '研发历程+技术架构', totalDuration: 7,
      steps: [
        { id: uid(), role: '角色D', duration: 0.67, focus: '产教融合（P06）', content: '', notes: '换人话术', transition: '以上是项目背景，请D介绍校企合作情况。' },
        { id: uid(), role: '角色D', duration: 0.67, focus: '合作探究（P07）', content: '', notes: '', transition: '' },
        { id: uid(), role: '主讲人A', duration: 1.5, focus: '问题策略（P08）', content: '', notes: '用手指数痛点、技术一一对应', transition: '' },
        { id: uid(), role: '角色B', duration: 1.33, focus: '技术架构（P09）', content: '', notes: '五层架构介绍', transition: '接下来进入实操环节。' },
        { id: uid(), role: '角色C', duration: 0.67, focus: '关键技术（P11）', content: '', notes: '', transition: '' },
        { id: uid(), role: '四人轮流', duration: 0.83, focus: '团队分工（P12）', content: '', notes: '各说一句自己的职责', transition: '' },
        { id: uid(), role: '角色D', duration: 0.83, focus: '安全规范+工匠精神（P10/P13）', content: '', notes: '', transition: '' },
      ]
    },
    {
      id: uid(), title: '岗位实操', totalDuration: 36,
      steps: [
        { id: uid(), role: '主讲人A', duration: 9, focus: '产品经理实操（P14）', content: '', notes: 'PPT讲解2min → 切屏实操7min', transition: '以上是业务逻辑实操，请B进行前端开发实操。' },
        { id: uid(), role: '角色B', duration: 10, focus: '前端工程师实操（P15）', content: '', notes: 'PPT讲解2min → 切屏实操8min', transition: '以上是前端实操，请C进行后端开发实操。' },
        { id: uid(), role: '角色C', duration: 10, focus: '后端工程师实操（P16）', content: '', notes: 'PPT讲解2min → 切屏实操8min', transition: '以上是后端实操，请D进行测试实操。' },
        { id: uid(), role: '角色D', duration: 8, focus: '测试工程师实操（P17）', content: '', notes: 'PPT讲解2min → 切屏实操6min', transition: '以上是各岗位独立实操。' },
        { id: uid(), role: '四人联合', duration: 4, focus: '联调协作', content: '', notes: '预设突发问题+协同解决，体现相互补台', transition: '接下来进入创新设计环节。' },
      ]
    },
    {
      id: uid(), title: '创新设计+应用价值', totalDuration: 7,
      steps: [
        { id: uid(), role: '角色B', duration: 0.67, focus: '技术创新（P18）', content: '', notes: '量化成效', transition: '' },
        { id: uid(), role: '角色C', duration: 0.67, focus: '模式创新（P19）', content: '', notes: '', transition: '' },
        { id: uid(), role: '主讲人A', duration: 0.67, focus: '应用价值（P20）', content: '', notes: '实用性/经济性/可持续性', transition: '' },
        { id: uid(), role: '角色D', duration: 0.67, focus: '落地成果（P21）', content: '', notes: '', transition: '' },
      ]
    },
    {
      id: uid(), title: '结束', totalDuration: 5,
      steps: [
        { id: uid(), role: '主讲人A', duration: 0.33, focus: '结束页（P22）', content: '', notes: '四人齐声谢谢、鞠躬', transition: '' },
        { id: uid(), role: '按题型分工', duration: 4, focus: '答辩环节', content: '', notes: '业务→A、前端→B、后端→C、测试→D、团队→A/D', transition: '' },
      ]
    }
  ]
}

const defaultRoles = [
  { id: 'r1', label: '主讲人A', color: '#409EFF' },
  { id: 'r2', label: '角色B', color: '#67C23A' },
  { id: 'r3', label: '角色C', color: '#E6A23C' },
  { id: 'r4', label: '角色D', color: '#F56C6C' },
  { id: 'r5', label: '四人轮流', color: '#8B5CF6' },
  { id: 'r6', label: '四人联合', color: '#14B8A6' },
  { id: 'r7', label: '按题型分工', color: '#EC4899' },
]

// ===== 章节操作 =====
function addChapter() {
  newChapterTitle.value = ''
  newChapterDuration.value = 5
  showChapterDialog.value = true
}

function confirmAddChapter() {
  if (!newChapterTitle.value.trim()) {
    ElMessage.warning('请输入章节标题')
    return
  }
  chapters.value.push({
    id: uid(),
    title: newChapterTitle.value.trim(),
    totalDuration: newChapterDuration.value,
    steps: []
  })
  activeChapterIdx.value = chapters.value.length - 1
  showChapterDialog.value = false
  autoSave()
}

function removeChapter(idx) {
  chapters.value.splice(idx, 1)
  if (activeChapterIdx.value >= chapters.value.length) {
    activeChapterIdx.value = Math.max(0, chapters.value.length - 1)
  }
  autoSave()
}

// ===== 步骤操作 =====
function addStep() {
  if (!activeChapter.value) return
  const ch = activeChapter.value
  ch.steps.push({
    id: uid(),
    role: roles.value.length > 0 ? roles.value[0].label : '',
    duration: 1,
    focus: '',
    content: '',
    notes: '',
    transition: ''
  })
  autoSave()
}

function removeStep(idx) {
  activeChapter.value.steps.splice(idx, 1)
  autoSave()
}

function moveStep(idx, dir) {
  const steps = activeChapter.value.steps
  const target = idx + dir
  if (target < 0 || target >= steps.length) return
  const temp = steps[idx]
  steps[idx] = steps[target]
  steps[target] = temp
  autoSave()
}

// ===== 角色操作 =====
function addRole() {
  newRoleLabel.value = ''
  newRoleColor.value = '#409EFF'
  showRoleDialog.value = true
}

function confirmAddRole() {
  if (!newRoleLabel.value.trim()) {
    ElMessage.warning('请输入角色名称')
    return
  }
  roles.value.push({
    id: uid(),
    label: newRoleLabel.value.trim(),
    color: newRoleColor.value
  })
  showRoleDialog.value = false
  autoSave()
}

function removeRole(id) {
  roles.value = roles.value.filter(r => r.id !== id)
  autoSave()
}

// ===== 加载 =====
async function loadScript() {
  const loadRequest = scriptRequestLifecycle.open('load')
  loadingScript.value = true
  loadError.value = ''
  try {
    // 从模板创建
    if (templateIdParam) {
      const res = await request.get(`/api/script-template/${templateIdParam}`, {
        signal: loadRequest.signal,
      })
      if (!loadRequest.isCurrent()) return
      if (res.code === 200 && res.data) {
        scriptTitle.value = '新建讲稿'
        chapters.value = parseStoredValue(res.data.content, createDefaultTemplate())
        roles.value = parseStoredValue(res.data.roles, [...defaultRoles])
        saveCoordinator.markDirty()
        currentPersistenceSignal = loadRequest.signal
        try {
          await flushSaveQueue()
        } finally {
          if (currentPersistenceSignal === loadRequest.signal) currentPersistenceSignal = null
        }
        if (!loadRequest.isCurrent()) return
        await router.replace({
          name: 'ScriptEditor',
          params: { scriptId: String(scriptId.value) }
        })
        if (!loadRequest.isCurrent()) return
        return
      }
    }
    // 直接加载讲稿
    if (scriptIdParam) {
      const res = await request.get(`/api/script/${scriptIdParam}`, {
        signal: loadRequest.signal,
      })
      if (!loadRequest.isCurrent()) return
      if (res.code === 200 && res.data) {
        fillScript(res.data)
        return
      }
    }
    // 没有参数，跳转列表
    if (!loadRequest.isCurrent()) return
    await router.replace('/script-editor')
    if (!loadRequest.isCurrent()) return
  } catch (e) {
    if (!loadRequest.isCurrent()) return
    console.error('加载讲稿失败:', e)
    loadError.value = e?.message || '请检查网络连接后重试。'
  } finally {
    if (loadRequest.isCurrent()) loadingScript.value = false
    loadRequest.release()
  }
}

function fillScript(script) {
  scriptId.value = script.id
  scriptTitle.value = script.title || '路演讲稿'
  scriptSourceType.value = script.sourceType || script.source_type || 'manual'
  scriptPptJobId.value = script.pptJobId || script.ppt_job_id || ''
  scriptContentVersion.value = Number(script.contentVersion || script.content_version || 1)
  chapters.value = parseStoredValue(script.content, createDefaultTemplate())
  roles.value = parseStoredValue(script.roles, [...defaultRoles])
  saveCoordinator.markCommitted()
  saveStatus.value = 'idle'
}

function parseStoredValue(value, fallback) {
  if (Array.isArray(value)) return value
  if (!value) return fallback
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : fallback
  } catch (_) {
    return fallback
  }
}

// ===== 自动保存 =====
let saveTimer = null

function snapshotScript() {
  return {
    title: scriptTitle.value,
    content: JSON.stringify(chapters.value),
    roles: JSON.stringify(roles.value),
    sourceType: normalizedSourceType(),
    pptJobId: scriptPptJobId.value || null
  }
}

async function persistScriptSnapshot(payload) {
  const res = scriptId.value
    ? await request.put(`/api/script/${scriptId.value}`, payload, {
        signal: currentPersistenceSignal || undefined,
      })
    : await request.post('/api/script', payload, {
        signal: currentPersistenceSignal || undefined,
      })

  const persistedId = res?.data?.id || scriptId.value
  if (res?.code !== 200 || !persistedId) {
    const error = new Error(res?.message || '保存讲稿失败')
    error.response = res
    throw error
  }

  scriptId.value = persistedId
  scriptSourceType.value = res.data?.sourceType || res.data?.source_type || scriptSourceType.value
  scriptPptJobId.value = res.data?.pptJobId || res.data?.ppt_job_id || scriptPptJobId.value
  if (res.data?.contentVersion != null || res.data?.content_version != null) {
    scriptContentVersion.value = Number(res.data.contentVersion || res.data.content_version)
  }
  return res.data
}

const saveCoordinator = createScriptSaveCoordinator({
  snapshot: snapshotScript,
  persist: persistScriptSnapshot,
  onState: state => {
    saveStatus.value = state
  },
})

function markDirtyAndSchedule() {
  if (!canUseEditor.value) return
  saveCoordinator.markDirty()
  if (saveStatus.value !== 'saving') saveStatus.value = 'pending'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    flushSaveQueue().catch(error => {
      console.error('自动保存失败:', error)
    })
  }, 3000)
}

function autoSave() {
  markDirtyAndSchedule()
}

function onStepContentSelect(event, step) {
  const el = event?.target
  if (!el || el.tagName !== 'TEXTAREA' || !step?.id) {
    return
  }
  const start = Number(el.selectionStart || 0)
  const end = Number(el.selectionEnd || 0)
  const selection = String(step.content || '').slice(start, end).trim()
  if (!selection) {
    if (xiaoQiAsk.value?.stepId === step.id) xiaoQiAsk.value = null
    return
  }
  xiaoQiAsk.value = { stepId: step.id, selection, start, end }
}

async function askXiaoQiFromHeader() {
  const steps = chapters.value[activeChapterIdx.value]?.steps || []
  const selected = xiaoQiAsk.value?.stepId
    ? steps.find((s) => s.id === xiaoQiAsk.value.stepId)
    : null
  const step = selected || steps[0]
  if (!step) {
    ElMessage.warning('先加一个讲解步骤')
    return
  }
  await askXiaoQi(step)
}

async function askXiaoQi(step) {
  const ask = xiaoQiAsk.value
  const selection = (ask?.stepId === step.id && ask.selection)
    || String(step.content || '').trim()
  if (!selection || !step?.id) {
    ElMessage.warning('这一步还没有正文，先写一句再问小启')
    return
  }
  if (!scriptId.value) {
    ElMessage.warning('请先保存讲稿')
    return
  }
  try {
    await flushSaveQueue()
  } catch (e) {
    ElMessage.error('请先保存讲稿再问小启')
    return
  }
  const steps = chapters.value[activeChapterIdx.value]?.steps || []
  const idx = steps.findIndex((s) => s.id === step.id)
  const prev = idx > 0 ? steps[idx - 1] : null
  const next = idx >= 0 ? steps[idx + 1] : null
  writeScriptStepContext({
    type: 'script_step',
    intent: 'script_local_edit',
    scriptId: scriptId.value,
    scriptTitle: scriptTitle.value,
    contentVersion: scriptContentVersion.value,
    pptJobId: scriptPptJobId.value || null,
    stepId: step.id,
    role: step.role || '',
    focus: step.focus || '',
    duration: step.duration,
    selection,
    stepContent: step.content || '',
    prevStep: prev ? { id: prev.id, role: prev.role || '', content: clipStepText(prev.content) } : null,
    nextStep: next ? { id: next.id, role: next.role || '', content: clipStepText(next.content) } : null,
  })
  xiaoQiAsk.value = null
  await router.push({ path: '/assistant', query: { from: 'script' } })
}

async function openSdocWorkbench() {
  if (!scriptId.value) {
    ElMessage.warning('请先保存讲稿')
    return
  }
  try {
    await flushSaveQueue()
    const res = await request.post(`/api/script/${scriptId.value}/workbench-sdoc`)
    const documentId = res?.data?.documentId
    if (!documentId) throw new Error(res?.message || '打开改稿文档失败')
    await router.push({ path: `/inspire-office/sdoc/${documentId}`, query: { from: 'script' } })
  } catch (e) {
    ElMessage.error(e.message || '打开智能文档失败')
  }
}

async function flushSaveQueue() {
  clearTimeout(saveTimer)
  saveTimer = null
  return saveCoordinator.flush()
}

function normalizedSourceType() {
  if (scriptPptJobId.value) return 'ppt'
  return 'manual'
}

// ===== 导出 PDF =====
async function exportPdf() {
  if (exporting.value || !hasValidContent.value) return
  exporting.value = true
  try {
    await runAfterSuccessfulSave({
      flush: flushSaveQueue,
      action: async () => {
        const res = await request.get(`/api/script/${scriptId.value}/pdf`, { responseType: 'blob' })
        const url = window.URL.createObjectURL(new Blob([res]))
        const link = document.createElement('a')
        link.href = url
        link.download = `${scriptTitle.value}.pdf`
        link.click()
        window.URL.revokeObjectURL(url)
      },
    })
    ElMessage.success('PDF 已导出')
  } catch (e) {
    if (saveCoordinator.isDirty() || saveStatus.value === 'error') {
      ElMessage.error('保存失败，未导出 PDF')
    } else {
      ElMessage.error('导出失败')
    }
  } finally {
    exporting.value = false
  }
}

// ===== 另存为模板 =====
async function confirmSaveAsTemplate() {
  if (templateSaving.value || !hasValidContent.value) return
  templateSaving.value = true
  const name = newTemplateName.value.trim() || scriptTitle.value + ' 模板'
  try {
    const res = await request.post('/api/script-template/from-script', {
      name,
      description: newTemplateDesc.value,
      content: JSON.stringify(chapters.value),
      roles: JSON.stringify(roles.value)
    })
    if (res.code === 200) {
      ElMessage.success('已保存为模板')
      showSaveAsTemplate.value = false
      newTemplateName.value = ''
      newTemplateDesc.value = ''
    }
  } catch (e) {
    ElMessage.error('保存模板失败')
  } finally {
    templateSaving.value = false
  }
}

// ===== 初始化 =====
watch(
  [scriptTitle, chapters, roles],
  () => {
    markDirtyAndSchedule()
  },
  { deep: true, flush: 'sync' }
)

function handleBeforeUnload(event) {
  if (!saveCoordinator.isDirty()) return
  event.preventDefault()
  event.returnValue = ''
}

onMounted(() => {
  scriptRequestLifecycle.activate()
  window.addEventListener('beforeunload', handleBeforeUnload)
  loadScript()
})

onBeforeRouteLeave(async () => {
  scriptRequestLifecycle.invalidate()
  if (loadingScript.value) return true
  if (!saveCoordinator.isDirty()) return true
  try {
    await flushSaveQueue()
    return true
  } catch (error) {
    scriptRequestLifecycle.activate()
    console.error('离开前保存失败:', error)
    ElMessage.error('保存失败，已留在当前页面，请重试')
    return false
  }
})

onBeforeUnmount(() => {
  scriptRequestLifecycle.invalidate()
  clearTimeout(saveTimer)
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<style scoped src="../styles/script-editor-v2.css"></style>
