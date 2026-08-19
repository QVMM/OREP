<template>
  <AiAppShell
    :mode="pptShellMode"
    :width="pptShellWidth"
  >
    <template #header>
      <AiAppHeader
        app="ppt"
        :mode="pptShellMode"
        :back-label="pptBackLabel"
        :back-to="pptBackTo"
        :context="pptHeaderContext"
        :title="pptHeaderTitle"
        :subtitle="pptHeaderSubtitle"
        :status="pptHeaderStatus"
      >
        <template #actions>
          <button
            type="button"
            class="ppt-icon-button ppt-workspace-secondary-action"
            aria-label="最近记录"
            title="最近记录"
            @click="openHistoryDrawer"
          >
            <el-icon><FolderOpened /></el-icon>
          </button>
          <button
            v-if="pptView === 'workspace'"
            type="button"
            class="ppt-icon-button ppt-workspace-secondary-action"
            aria-label="调整生成设置"
            title="调整生成设置"
            @click="openSetup"
          >
            <el-icon><Setting /></el-icon>
          </button>
          <button
            v-if="pptView === 'workspace'"
            type="button"
            class="ppt-icon-button ppt-workspace-primary-action"
            aria-label="新建 PPT"
            title="新建 PPT"
            @click="createNewPpt"
          >
            <el-icon><Plus /></el-icon>
          </button>
          <el-dropdown
            v-if="pptView === 'workspace'"
            class="ppt-mobile-more"
            trigger="click"
            @command="handleWorkspaceMoreAction"
          >
            <button
              type="button"
              class="ppt-icon-button"
              aria-label="更多操作"
              title="更多操作"
            >
              <el-icon><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="history">最近记录</el-dropdown-item>
                <el-dropdown-item command="settings">调整生成设置</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </AiAppHeader>
    </template>

    <div :class="['ppt-agent-page', `is-${pptView}-view`]">
      <section v-if="pptView === 'landing'" class="creation-landing" aria-labelledby="ppt-create-title">
        <div class="creation-landing__content">
          <div class="creation-landing__intro">
            <div class="creation-file-mark" aria-hidden="true">
              <el-icon><MagicStick /></el-icon>
            </div>
            <span class="creation-kicker">AI 路演材料生成</span>
            <h2 id="ppt-create-title">把项目资料变成一套能讲清楚的路演 PPT</h2>
            <p>上传已有材料，系统会整理汇报结构、页面内容和配套讲稿。</p>
            <button type="button" class="creation-start-button" @click="openSetup">
              开始创建
            </button>
            <small class="creation-start-note">没有完整资料，也可以先补充项目信息</small>
          </div>
  
          <div class="creation-landing__process" aria-label="创建流程">
            <div class="creation-process-head">
              <strong>创建流程</strong>
              <span>三步完成设置</span>
            </div>
            <ol class="creation-steps">
              <li v-for="step in creationSteps" :key="step.index" class="creation-step">
                <span>{{ step.index }}</span>
                <div>
                  <strong>{{ step.title }}</strong>
                  <small>{{ step.description }}</small>
                </div>
              </li>
            </ol>
            <p class="creation-result-note">生成后进入工作台，可继续编辑、下载和管理版本。</p>
          </div>
        </div>
      </section>
  
      <section v-else-if="pptView === 'setup'" class="creation-setup-shell">
        <aside class="creation-setup-guide" aria-label="PPT 创建流程">
          <span class="creation-guide-kicker">创建流程</span>
          <h2>先准备内容，再开始生成</h2>
          <p>默认设置已经可用。上传资料，或补充项目信息后即可生成。</p>
  
          <ol class="creation-guide-steps">
            <li
              v-for="step in creationSteps"
              :key="step.index"
              :class="{
                'is-complete': Number(step.index) < setupActiveStep,
                'is-current': Number(step.index) === setupActiveStep
              }"
            >
              <span>{{ step.index }}</span>
              <div>
                <strong>{{ step.title }}</strong>
                <small>{{ step.description }}</small>
              </div>
            </li>
          </ol>
  
          <div class="creation-guide-note">
            <strong>资料不完整也可以继续</strong>
            <span>先补充项目信息，系统会根据缺失内容给出提示。</span>
          </div>
        </aside>
  
        <aside
          id="ppt-material-setup"
          class="agent-panel control-panel creation-setup-panel"
          role="region"
          aria-label="PPT 创建设置"
        >
          <div v-if="selectedDeckType === 'roadshow'" class="form-block output-type-block">
            <div class="output-type-heading">
              <label id="ppt-output-type-label">成品形式</label>
              <span v-if="outputSelectionLocked">当前任务已锁定</span>
            </div>
            <div class="output-type-options" role="radiogroup" aria-labelledby="ppt-output-type-label">
              <button
                v-for="option in roadshowOutputOptions"
                :key="option.value"
                type="button"
                role="radio"
                :aria-checked="roadshowOutputType === option.value ? 'true' : 'false'"
                :disabled="outputSelectionLocked || (option.value === 'image' && !image2Available)"
                :class="['output-type-card', roadshowOutputType === option.value ? 'active' : '']"
                @click="roadshowOutputType = option.value"
              >
                <span class="output-type-copy">
                  <strong>{{ option.label }}</strong>
                  <small>{{ option.description }}</small>
                </span>
                <span class="output-type-check" aria-hidden="true">
                  {{ roadshowOutputType === option.value ? '✓' : '' }}
                </span>
              </button>
            </div>
          </div>
  
          <DropFileUpload
            :key="`main-${uploadResetKey}`"
            size="lg"
            :accept="fileAccept"
            :multiple="selectedDeckType === 'roadshow'"
            :disabled="submitting"
            :title="uploadedFileName || uploadTitle"
            :hint="uploadedSession ? uploadedFileMeta : uploadHint"
            @change="onMainDropFiles"
            @error="(err) => ElMessage.warning(err?.message || '文件不符合要求')"
          />
  
          <button
            v-if="selectedDeckType === 'roadshow'"
            type="button"
            class="project-info-summary"
            @click="openQuestionnaireSection()"
          >
            <div>
              <strong>项目信息</strong>
              <span>{{ completedQuestionSections ? `已完成 ${completedQuestionSections}/6 项` : '尚未填写' }}</span>
            </div>
            <span class="project-info-summary__action">去补充</span>
          </button>
  
          <div v-else class="paper-upload-guide">
            <strong>论文 PPT 资料</strong>
            <span>上传论文 PDF、TeX 或源码压缩包后，将按 paper-ppt-agent 原始论文逻辑生成。</span>
          </div>
  
          <button
            type="button"
            class="advanced-settings-toggle"
            :aria-expanded="advancedSettingsOpen ? 'true' : 'false'"
            aria-controls="ppt-advanced-settings"
            @click="advancedSettingsOpen = !advancedSettingsOpen"
          >
            <span>
              <el-icon><Setting /></el-icon>
              高级设置
            </span>
            <span aria-hidden="true">{{ advancedSettingsOpen ? '⌃' : '⌄' }}</span>
          </button>
  
          <div v-show="advancedSettingsOpen" id="ppt-advanced-settings" class="advanced-settings-panel">
            <div class="advanced-settings-grid">
              <div class="form-block generation-target">
                <label>PPT 类型</label>
                <el-radio-group v-model="selectedDeckType">
                  <el-radio-button value="roadshow">路演</el-radio-button>
                  <el-radio-button value="paper">论文</el-radio-button>
                </el-radio-group>
              </div>
              <div class="form-block">
                <label>视觉模板</label>
                <el-select v-model="selectedTemplate" clearable filterable placeholder="系统智能匹配">
                  <el-option
                    v-for="option in templateOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
              <div class="form-block">
                <label>篇幅</label>
                <el-select v-model="pagePolicy" placeholder="选择页数策略">
                  <el-option
                    v-for="option in pagePolicyOptions"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </div>
            </div>
  
            <div v-if="selectedDeckType !== 'roadshow'" class="form-block extra-notes">
              <label>生成要求</label>
              <el-input
                v-model="instruction"
                type="textarea"
                :rows="3"
                resize="none"
                :placeholder="instructionPlaceholder"
              />
            </div>
          </div>
  
          <p class="creation-save-note" role="status">
            <el-icon aria-hidden="true"><Check /></el-icon>
            项目信息和生成设置会自动保存在本机；上传文件需重新选择。
          </p>
  
          <div v-if="!healthOk" class="creation-service-warning" role="status" aria-live="polite">
            生成服务暂不可用，可以先完成资料设置。
          </div>
  
          <div class="action-dock">
            <div class="action-row" :class="{ 'has-secondary': canResume || canCancel }">
              <el-button
                v-if="hasPendingRoadshowCards"
                type="primary"
                size="large"
                :loading="renderingFromCards"
                :disabled="!canConfirmCards"
                @click="confirmCardsAndRender"
              >
                确认并进入设计渲染
              </el-button>
              <el-button
                v-else
                type="primary"
                size="large"
                :class="{ 'is-generating-action': isRunning }"
                :loading="submitting || isRunning"
                :disabled="!canGenerate"
                @click="startGenerate"
              >
                {{ primaryGenerateLabel }}
              </el-button>
              <el-button
                v-if="canResume"
                type="warning"
                size="large"
                :loading="submitting"
                @click="resumeJob"
              >
                {{ isRestartInterruptedError ? '从中断处重试' : '从缓存继续' }}
              </el-button>
              <el-button
                v-if="canRetryGenerate && !canResume"
                type="primary"
                plain
                size="large"
                :loading="submitting"
                @click="startGenerate"
              >
                使用当前资料重新生成
              </el-button>
              <el-button v-if="canCancel" size="large" type="danger" plain @click="cancelJob">取消生成</el-button>
            </div>
          </div>
        </aside>
      </section>
  
      <section v-else class="agent-layout">
        <div :class="['agent-panel', 'preview-panel', isRunning ? 'is-running' : '']">
          <div class="preview-head">
            <div class="pipeline-meta">
              <span class="eyebrow">生成流程</span>
              <span class="pipeline-status">{{ jobTitle }}</span>
              <small v-if="jobId">{{ jobSubtitle }}</small>
            </div>
            <button
              v-if="canDownload"
              class="download-button"
              type="button"
              :disabled="downloadingPpt"
              @click="downloadPpt"
            >
              {{ downloadingPpt ? '正在导出...' : '下载 PPTX' }}
            </button>
          </div>
  
          <el-progress
            :percentage="progressPercent"
            :status="progressState"
            :stroke-width="12"
            striped
            striped-flow
          />
  
          <div class="stage-row">
            <div
              v-for="stage in stages"
              :key="stage.key"
              :class="['stage-card', stageClass(stage.key)]"
            >
              <span>{{ stage.label }}</span>
            </div>
          </div>
  
          <div v-if="errorMessage" class="error-box" :title="errorMessage">
            {{ errorMessage }}
          </div>
  
          <section v-if="showCardPlanning" class="content-card-panel">
            <div class="content-card-toolbar">
              <div>
                <strong>页面内容卡片</strong>
                <span>
                  {{ roadshowCards.length }} 页 · 已按职业院校技能大赛正式路演逻辑生成，确认后再进入视觉渲染。
                </span>
              </div>
              <div class="card-actions">
                <el-button :loading="savingCards" plain @click="saveRoadshowCards">保存卡片</el-button>
                <el-button
                  type="primary"
                  :loading="renderingFromCards"
                  :disabled="!canConfirmCards"
                  @click="confirmCardsAndRender"
                >
                  确认并进入设计渲染
                </el-button>
              </div>
            </div>
  
            <div class="plan-summary-grid">
              <div class="plan-summary-block">
                <b>推荐页数</b>
                <span>{{ materialDiagnosis.page_count_decision?.recommended_pages || roadshowCards.length }} 页</span>
                <small>{{ materialDiagnosis.page_count_decision?.reason || '根据素材完整度与项目复杂度自适应。' }}</small>
              </div>
              <div class="plan-summary-block">
                <b>讲述时长</b>
                <span>55 分钟内容 + 5 分钟容错</span>
                <small>受众固定为职业院校技能大赛评审专家。</small>
              </div>
              <div class="plan-summary-block">
                <b>故事线</b>
                <span>{{ storylinePlan.phases?.length || 5 }} 段</span>
                <small>{{ storylinePlan.storyline_principle || '按成立、研发、实施、验证、价值推进。' }}</small>
              </div>
            </div>
  
            <div class="storyline-strip">
              <div v-for="phase in storylinePlan.phases || []" :key="phase.name" class="storyline-step">
                <b>{{ phase.name }}</b>
                <span>第 {{ phase.page_range?.[0] }}-{{ phase.page_range?.[1] }} 页</span>
              </div>
            </div>
  
            <div class="content-card-list">
              <article v-for="card in roadshowCards" :key="card.page" class="page-content-card">
                <div class="page-card-head">
                  <span>Page {{ card.page }}</span>
                  <b>{{ card.page_type }}</b>
                  <small>{{ card.section || '未分段' }}</small>
                </div>
                <div class="page-card-fields">
                  <label>
                    正式标题
                    <el-input v-model="card.formal_title" size="small" />
                  </label>
                  <label>
                    核心句
                    <el-input v-model="card.core_sentence" size="small" />
                  </label>
                  <label class="wide-field">
                    页面正文
                    <el-input v-model="card.visible_content" type="textarea" :rows="3" resize="none" />
                  </label>
                  <label>
                    主视觉
                    <el-input v-model="card.main_visual.type" size="small" placeholder="svg_diagram / screenshot / chart" />
                  </label>
                  <label>
                    素材状态
                    <el-select v-model="card.asset_status" size="small">
                      <el-option label="已有真实素材" value="provided" />
                      <el-option label="缺少真实素材" value="missing" />
                      <el-option label="使用 SVG 示意" value="needs_svg" />
                      <el-option label="公开来源补充" value="public_source" />
                    </el-select>
                  </label>
                  <label class="wide-field">
                    素材引用 / 需求
                    <el-input
                      :model-value="(card.required_assets || []).join('；')"
                      size="small"
                      @update:model-value="card.required_assets = splitCardAssets($event)"
                    />
                  </label>
                </div>
                <div v-if="card.quality_flags?.length" class="card-flags">
                  <span v-for="flag in card.quality_flags" :key="flag">{{ flag }}</span>
                </div>
              </article>
            </div>
          </section>
  
          <ReactPptWorkspace
            v-else
            :slides="slides"
            :selected-index="activeSlideIndex"
            :editable="canEditSlides"
            :download-url="canDownload ? downloadUrl : ''"
            :loading="isRunning && !slides.length"
            :create-slide="createBlankSlide"
            :delete-slide="deleteSlideByIndex"
            :refresh-preview="refreshCurrentPreview"
            :save-slide="handleEditorSave"
            :save-notes="saveSlideNotes"
            :draft-key-prefix="`ppt-notes:${jobId || 'draft'}`"
            @select="handleSlideSelect"
          />
  
        </div>
  
        <aside class="agent-panel log-panel">
          <div class="feedback-panel">
            <div class="panel-title compact-title">
              <span>反馈优化</span>
              <small>{{ slides.length ? `当前第 ${activeSlideIndex} 页` : '无页面' }}</small>
            </div>
            <el-radio-group v-model="regenScope" class="regen-scope">
              <el-radio-button value="current">当前页</el-radio-button>
              <el-radio-button value="all">全部页面</el-radio-button>
            </el-radio-group>
            <div class="switch-row compact-switch">
              <div>
                <strong>允许结构调整</strong>
                <span>可增删页或重排结构</span>
              </div>
              <el-switch v-model="allowStructureChanges" />
            </div>
            <el-input
              v-model="regenFeedback"
              type="textarea"
              :rows="5"
              maxlength="800"
              show-word-limit
              resize="none"
              placeholder="例如：第3页文字太多，突出现场实操步骤；把支撑材料区改成日志、截图、验收信号三栏。"
            />
            <el-button
              type="primary"
              class="full-button"
              :loading="refineSubmitting"
              :disabled="!canRefine"
              @click="submitFeedbackRefine"
            >
              提交反馈并重新生成
            </el-button>
          </div>
  
          <div class="panel-title">
            <span>代理日志</span>
            <small>{{ jobId || '未创建任务' }}</small>
          </div>
  
          <div class="log-list">
            <div v-for="item in logs" :key="item.id" class="log-item">
              <b>{{ item.stage }}</b>
              <p>{{ item.message }}</p>
            </div>
            <div v-if="!logs.length" class="muted">等待上传资料并开始生成。</div>
          </div>
        </aside>
      </section>
  
      <el-drawer
        v-model="historyDrawer"
        title="历史生成记录"
        size="420px"
        direction="ltr"
        class="history-drawer"
        @close="invalidateHistoryDetailIntent"
        @closed="handleHistoryDrawerClosed"
      >
        <div class="history-head">
          <span>包含 PPT、源文件、日志和版本信息</span>
          <el-button size="small" :loading="loadingHistory" :icon="Refresh" @click="loadHistory">刷新</el-button>
        </div>
        <div v-if="loadingHistory" class="history-loading" role="status" aria-live="polite">
          <span class="history-loading-dot"></span>
          <div>
            <strong>正在读取最近记录</strong>
            <small>请稍候，历史任务会显示在这里。</small>
          </div>
        </div>
        <div v-else-if="historyJobs.length" class="history-list">
          <button
            v-for="item in historyJobs"
            :key="item.job_id"
            type="button"
            :class="['history-card', item.job_id === jobId ? 'active' : '']"
            @click="openHistoryJob(item)"
          >
            <div>
              <strong>{{ item.file?.name || item.job_id }}</strong>
              <span>
                {{ item.deck_type === 'roadshow' ? '路演 PPT' : item.deck_type === 'paper' ? '论文 PPT' : 'PPT' }}
                · {{ item.render_engine === 'svg' ? '可编辑' : item.render_engine === 'image2' ? '图片型' : '旧版' }}
                · {{ item.status }}
              </span>
            </div>
            <small>{{ item.slide_count || item.total_slides || 0 }} 页 · {{ formatTime(item.updated_at) }}</small>
          </button>
        </div>
        <div v-else-if="historyError" class="history-error">
          <strong>历史记录加载失败</strong>
          <span>{{ historyError }}</span>
        </div>
        <div v-else class="muted">暂无历史任务。</div>
      </el-drawer>
  
      <el-drawer
        v-model="questionnaireDrawer"
        title="路演资料问卷"
        size="560px"
        direction="ltr"
        class="questionnaire-drawer"
      >
        <div class="drawer-intro">
          <strong>{{ readinessTitle }}</strong>
          <span>{{ readinessHint }}</span>
        </div>
        <section class="material-basket">
          <div class="material-basket-head">
            <div>
              <strong>分类材料篮子</strong>
              <span>把截图、代码、日志、成果材料按用途放好，生成时会一起写入资料包。</span>
            </div>
            <DropFileUpload
              :key="`basket-${uploadResetKey}-${activeMaterialCategory}`"
              size="sm"
              multiple
              :accept="fileAccept"
              title="拖拽材料到此处，或点击上传"
              :hint="`上传到「${activeMaterialCategoryInfo?.label || '当前分类'}」`"
              @change="onBasketDropFiles"
              @error="(err) => ElMessage.warning(err?.message || '文件不符合要求')"
            />
          </div>
          <div class="material-category-tabs">
            <button
              v-for="category in materialUploadCategories"
              :key="category.key"
              type="button"
              :class="['material-category-tab', activeMaterialCategory === category.key ? 'active' : '']"
              @click="activeMaterialCategory = category.key"
            >
              <strong>{{ category.label }}</strong>
              <span>{{ materialCategoryCounts[category.key] || 0 }} 个</span>
            </button>
          </div>
          <p class="material-category-hint">{{ activeMaterialCategoryInfo.desc }}</p>
          <div v-if="categorizedMaterialFiles.length" class="material-file-list">
            <div v-for="item in categorizedMaterialFiles" :key="item.id" class="material-file-item">
              <div>
                <strong>{{ item.file.name }}</strong>
                <span>{{ materialCategoryLabel(item.category) }} · {{ formatFileSize(item.file.size) }}</span>
              </div>
              <button type="button" @click="removeCategorizedMaterialFile(item.id)">删除</button>
            </div>
          </div>
          <div v-else class="material-empty">
            没有附件也可以生成；真实图片、日志和代码越清楚，PPT 越不像空泛汇报。
          </div>
        </section>
        <el-collapse v-model="activeQuestionSections" class="questionnaire-collapse in-drawer">
          <el-collapse-item
            v-for="section in roadshowQuestionnaire"
            :key="section.key"
            :name="section.key"
            class="question-section"
          >
            <template #title>
              <div class="question-title">
                <span>{{ section.title }}</span>
                <small>{{ section.hint }}</small>
              </div>
            </template>
            <div class="question-body">
              <div class="question-list">
                <div v-for="field in section.fields" :key="field.key" class="form-block compact-field">
                  <label>{{ field.label }}</label>
                  <el-input
                    v-model="materialForm[field.key]"
                    :type="field.rows > 1 ? 'textarea' : 'text'"
                    :rows="field.rows || 1"
                    resize="none"
                    :placeholder="field.placeholder"
                  />
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-drawer>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Check,
  FolderOpened,
  MagicStick,
  MoreFilled,
  Plus,
  Refresh,
  Setting,
  Upload
} from '@element-plus/icons-vue'
import { getStoredUser, getUserToken } from '@/utils/authStorage'
import request from '@/utils/request'
import { createRequestLifecycle } from '@/utils/requestLifecycle'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
import DropFileUpload from '@/components/base/DropFileUpload.vue'
import ReactPptWorkspace from '@/components/ppt/ReactPptWorkspace.vue'

const lastPptJobKeyPrefix = 'orep:ppt-editor:last-job'
const pptSetupDraftKeyPrefix = 'orep:ppt-editor:setup-draft'
const route = useRoute()
const router = useRouter()
const pptRequestLifecycle = createRequestLifecycle()
const skipInitialJobRestore = ['landing', 'setup', 'history'].includes(String(route.query.view || ''))
  || Boolean(route.query.job)
let pptViewIntentVersion = 0
let pptHistoryIntentVersion = 0
/** 主动打开历史任务时，关闭抽屉不要中断请求 */
let suppressHistoryInvalidate = false
const pptView = ref('landing')
const pptShellMode = computed(() => {
  if (pptView.value === 'workspace') return 'workspace'
  if (pptView.value === 'setup') return 'task'
  return 'landing'
})
const pptShellWidth = computed(() => (
  pptView.value === 'workspace' ? 'fluid' : pptView.value === 'setup' ? 'standard' : 'wide'
))
const pptBackLabel = computed(() => (
  pptView.value === 'workspace'
    ? 'PPT 列表'
    : pptView.value === 'setup'
      ? 'PPT 制作'
      : 'AI 应用中心'
))
const pptBackTo = computed(() => (
  pptView.value === 'workspace'
    ? { path: '/ppt-editor', query: { view: 'history' } }
    : pptView.value === 'setup'
      ? { path: '/ppt-editor', query: { view: 'landing' } }
      : '/ai-apps'
))
const pptHeaderContext = computed(() => (
  pptView.value === 'workspace' ? 'PPT 制作 · 编辑器' : ''
))
const pptHeaderTitle = computed(() => {
  if (pptView.value === 'workspace') {
    return String(materialForm.value.project_name || '').trim() || '未命名 PPT'
  }
  return pptView.value === 'setup' ? '创建 PPT' : 'PPT 制作'
})
const pptHeaderSubtitle = computed(() => {
  if (pptView.value === 'landing') return '把项目资料整理成可编辑的路演 PPT'
  if (pptView.value === 'setup') return '上传材料并确认生成设置'
  return ''
})
const pptHeaderStatus = computed(() => {
  if (pptView.value !== 'workspace') return ''
  if (isRunning.value) return jobSubtitle.value
  return jobId.value ? '已保存到最近记录' : ''
})
const creationSteps = [
  { index: '1', title: '选择成品形式', description: '选择整页成图或可继续编辑' },
  { index: '2', title: '准备资料', description: '上传材料，缺少内容时补充项目信息' },
  { index: '3', title: '自动生成', description: '确认设置后生成结构、页面和讲稿' }
]
const advancedSettingsOpen = ref(false)

const healthOk = ref(false)
const image2Available = ref(true)
const loadingMeta = ref(false)
const submitting = ref(false)
const generateLocked = ref(false)
const downloadingPpt = ref(false)
const uploadedSession = ref('')
const uploadedFileName = ref('')
const uploadedFileSize = ref(0)
const uploadResetKey = ref(0)
const mainUploadInput = ref(null)
const basketUploadInput = ref(null)
const selectedDeckType = ref('roadshow')
const roadshowOutputType = ref('image')
const currentJobRenderEngine = ref('')
const materialFiles = ref([])
const activeMaterialCategory = ref('demo')
const categorizedMaterialFiles = ref([])
const activeQuestionSections = ref(['basic', 'background', 'solution'])
const questionnaireDrawer = ref(false)
const roadshowInstruction = '面向职业院校技能大赛作品汇报，突出项目背景、政策和市场依据、技术方案、现场实操、运行记录、风险控制、团队匿名分工、应用价值、就业和行业帮助。禁止出现姓名、学校、电话、邮箱等个人信息；数据和结论需要可追溯；按55分钟现场讲解和自带设备实操准备。'
const paperInstruction = '面向论文汇报生成 PPT，突出研究问题、方法、实验、结果、贡献和局限。保留论文逻辑，不强行改成比赛路演结构。'
const instruction = ref(roadshowInstruction)
const materialForm = ref({
  idea_brief: '',
  project_name: '',
  domain: '',
  scene: '',
  target_users: '',
  positioning: '',
  pain_points: '',
  solution: '',
  current_news: '',
  policy_context: '',
  market_research: '',
  motivation: '',
  system_form: '',
  modules: '',
  architecture: '',
  key_technology: '',
  code_material: '',
  equipment: '',
  demo_flow: '',
  fallback_plan: '',
  test_environment: '',
  test_cases: '',
  test_results: '',
  team_roles: '',
  enterprise_value: '',
  school_value: '',
  employment_value: '',
  ip_cooperation: '',
  material_status: '',
  extra_requirements: ''
})
const providers = ref([])
const templates = ref([])
const selectedProviderModel = ref('mimo::mimo-v2.5-pro')
const selectedTemplate = ref('')
const pagePolicy = ref('competition')
const language = ref('zh')
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
const linkedPptScript = ref(null)
const criticEvents = ref([])
const activeSlideIndex = ref(1)
const historyDrawer = ref(false)
const loadingHistory = ref(false)
const historyJobs = ref([])
const historyError = ref('')
let pptMounted = false
const versions = ref([])
const editingText = ref(false)
const textItems = ref([])
const slideNotes = ref('')
const savingSlide = ref(false)
const followGeneratedSlides = ref(true)
const editorCommand = ref(null)
const editorCommandSeq = ref(0)
const editorState = ref({
  selectedType: '',
  autoSave: true,
  saveState: 'idle',
  canEdit: false,
  canUndo: false,
  canRedo: false
})
const regenScope = ref('current')
const regenFeedback = ref('')
const allowStructureChanges = ref(false)
const refineSubmitting = ref(false)
const materialDiagnosis = ref({})
const storylinePlan = ref({})
const roadshowCards = ref([])
const savingCards = ref(false)
const renderingFromCards = ref(false)

watch(
  () => route.query.view,
  async view => {
    if (view === 'landing') {
      pptViewIntentVersion += 1
      pptView.value = 'landing'
      historyDrawer.value = false
      await router.replace('/ppt-editor')
      return
    }
    if (view === 'history') {
      if (pptMounted && pptView.value === 'workspace') {
        pptRequestLifecycle.activate()
      }
      pptViewIntentVersion += 1
      pptView.value = 'landing'
      historyDrawer.value = true
      if (pptMounted) await loadHistory()
      return
    }
    if (view === 'setup') {
      if (pptView.value !== 'setup') pptViewIntentVersion += 1
      historyDrawer.value = false
      pptView.value = 'setup'
      return
    }
    if (!view && pptView.value !== 'workspace') {
      pptViewIntentVersion += 1
      historyDrawer.value = false
      pptView.value = jobId.value ? 'workspace' : 'landing'
    }
  },
  { immediate: true }
)

let socket = null
let socketRetryTimer = null
let pollTimer = null
let pass2HeartbeatTimer = null
let pass4HeartbeatTimer = null
let pollFailureCount = 0
let lastPollErrorMessage = ''
let lastLoggedProgressKey = ''
let lastLoggedSlidesCompleted = 0
let lastResearchProgressAt = 0
let pass2HeartbeatIndex = 0
let pass4HeartbeatIndex = 0
let lastPreviewRefreshAt = 0
let renderReadyRefreshAttempts = 0
let lastPreviewSignature = ''
let statusSyncInFlight = false
let logId = 0
let materialFileUid = 0
const autoPersistedScriptKeys = new Set()

const stages = [
  { key: 'parsing', label: '解析资料' },
  { key: 'research', label: '深度研究' },
  { key: 'content_cards', label: '内容卡片' },
  { key: 'waiting_confirmation', label: '等待确认' },
  { key: 'strategy', label: '叙事策略' },
  { key: 'generation', label: '页面生成' },
  { key: 'postprocess', label: '视觉修整' },
  { key: 'export', label: '导出文件' }
]

const roadshowOutputOptions = [
  {
    value: 'image',
    label: '整页成图',
    description: '视觉还原更完整，下载后以整页图片呈现'
  },
  {
    value: 'editable',
    label: '可继续编辑',
    description: '文字和图形可拆分，下载后仍可修改'
  }
]

const pass2SafeHeartbeatMessages = [
  '正在整理比赛汇报的五段故事线，不展示素材原文',
  '正在匹配页数区间与板块承载量，避免内容过密',
  '正在校验故事线是否从问题推进到价值',
  '正在标记需要真实素材承载的页面类型',
  '正在精简重复信息，保留正式汇报主线'
]

const pass4SafeHeartbeatMessages = [
  '正在为每页补充选手讲述目标，不展示素材原文',
  '正在匹配每页需要讲清楚的支撑材料',
  '正在检查评委最需要看到的页面信息重点',
  '正在给现场演示页补充承接关系和交接话术',
  '正在校准页面证明逻辑与支撑材料对应关系'
]

const materialUploadCategories = [
  { key: 'project_docs', label: '项目说明', desc: '说明书、需求文档、已有 PPT/PDF、README、项目背景材料。' },
  { key: 'technical', label: '系统技术', desc: '架构图、接口文档、数据库表结构、核心代码、算法或配置文件。' },
  { key: 'demo', label: '现场实操', desc: 'APP、后台、小程序、设备、传感器、演示步骤和运行截图。' },
  { key: 'test', label: '测试结果', desc: '测试用例、测试结果、运行日志、异常处理记录和复测材料。' },
  { key: 'research_value', label: '调研价值', desc: '调研记录、用户反馈、合作材料、应用价值、经济性和行业帮助。' },
  { key: 'fallback', label: '备用方案', desc: '设备清单、应急预案、故障排查、现场备用材料和恢复流程。' }
]

const roadshowQuestionnaire = [
  {
    key: 'basic',
    title: '1. 项目基础',
    hint: '先让系统知道你到底做了什么',
    fields: [
      { key: 'project_name', label: '项目名称', placeholder: '例如：智能温室环境监测与安全作业辅助系统' },
      { key: 'domain', label: '所属方向', placeholder: '例如：智慧农业、智能制造、智慧康养' },
      { key: 'scene', label: '应用场景', rows: 2, placeholder: '项目在哪个真实场景中使用，现场对象是什么' },
      { key: 'target_users', label: '目标用户 / 受益对象', rows: 2, placeholder: '例如：农户、企业技术员、学校实训课程、行业岗位' },
      { key: 'positioning', label: '一句话定位', rows: 2, placeholder: '一句话说明项目解决什么问题，带来什么改变' }
    ]
  },
  {
    key: 'background',
    title: '2. 背景与痛点',
    hint: 'Mimo 会据此联网补政策、行业和市场材料',
    fields: [
      { key: 'pain_points', label: '行业痛点', rows: 3, placeholder: '写真实痛点，最好能一条痛点对应一个解决策略' },
      { key: 'current_news', label: '时事/行业现象', rows: 2, placeholder: '不知道可以空着，竞赛大脑联网补充，但不会写成项目自有成果' },
      { key: 'policy_context', label: '政策方向', rows: 2, placeholder: '知道政策名就写，不知道可写“需联网补充”' },
      { key: 'market_research', label: '调研或用户反馈', rows: 3, placeholder: '调研了谁、发现什么问题、有没有用户反馈或访谈记录' },
      { key: 'motivation', label: '研发动因', rows: 2, placeholder: '为什么要做这个项目，为什么现在做' }
    ]
  },
  {
    key: 'solution',
    title: '3. 系统与技术',
    hint: '用于生成架构图、代码还原页和接口/数据库材料',
    fields: [
      { key: 'system_form', label: '系统形态', rows: 2, placeholder: 'APP、后台、小程序、设备、算法服务、传感器、机器人等' },
      { key: 'modules', label: '核心功能模块', rows: 4, placeholder: '每行一个模块：模块名 + 价值 + 输入/输出' },
      { key: 'architecture', label: '技术架构', rows: 3, placeholder: '前端、后端、数据库、设备通信、AI算法、部署和安全' },
      { key: 'key_technology', label: '关键技术', rows: 3, placeholder: '接口、协议、算法、数据库、任务调度、权限、日志等' },
      { key: 'code_material', label: '关键代码/接口素材', rows: 2, placeholder: '有代码文件可上传；没有就写关键逻辑，系统只能生成说明或伪代码' }
    ]
  },
  {
    key: 'demo',
    title: '4. 现场实操',
    hint: '比赛 PPT 必须像能上台演示',
    fields: [
      { key: 'equipment', label: '设备清单', rows: 2, placeholder: '电脑、手机、传感器、网关、网络、账号、备用材料' },
      { key: 'demo_flow', label: '演示流程', rows: 4, placeholder: '按“输入 -> 操作 -> 输出 -> 运行记录”写现场演示步骤' },
      { key: 'fallback_plan', label: '异常和备用方案', rows: 3, placeholder: '断网、设备失败、接口失败、数据缺失时如何排查、修复、复测' }
    ]
  },
  {
    key: 'test',
    title: '5. 测试与成果',
    hint: '无真实数据时只生成验证方法，不伪造成果',
    fields: [
      { key: 'test_environment', label: '测试环境', rows: 2, placeholder: '设备数量、样本、网络、版本、测试账号、场景' },
      { key: 'test_cases', label: '测试用例', rows: 3, placeholder: '测试什么、输入条件是什么、预期输出是什么' },
      { key: 'test_results', label: '已有测试结果', rows: 3, placeholder: '只写真实来源数据；没有就写待实测指标或验证口径' },
      { key: 'material_status', label: '真实材料状态', rows: 2, placeholder: '有哪些真实截图、日志、代码、证明；哪些需要系统生成示意图' }
    ]
  },
  {
    key: 'value',
    title: '6. 价值与团队',
    hint: '让 PPT 不只是功能说明，而是比赛路演',
    fields: [
      { key: 'team_roles', label: '团队匿名分工', rows: 3, placeholder: '只写岗位和模块，例如项目统筹、前端实现、设备接入、测试保障' },
      { key: 'enterprise_value', label: '企业/行业价值', rows: 2, placeholder: '经济性、合作应用、帮助哪些行业、可复制性' },
      { key: 'school_value', label: '学校/教学价值', rows: 2, placeholder: '课程转化、实训资源、产教融合' },
      { key: 'employment_value', label: '团队成长/就业价值', rows: 2, placeholder: '带动哪些岗位能力、新职业方向、学生技能成长' },
      { key: 'ip_cooperation', label: '知识产权/合作', rows: 2, placeholder: '真实软著/专利/协议可写状态；没有就写申报或合作规划' }
    ]
  }
]

const uploadHint = computed(() => {
  return selectedDeckType.value === 'roadshow'
    ? '支持 PDF、压缩包、图片、代码、表格、日志；没有文件也可先填问卷'
    : '支持论文 PDF、TeX 或源码压缩包'
})

const uploadTitle = computed(() => {
  if (selectedDeckType.value !== 'roadshow') return '选择资料文件'
  const total = materialFiles.value.length + categorizedMaterialFiles.value.length
  if (total) return `${total} 个补充文件待打包`
  return '上传已有资料或补充文件'
})

const materialCategoryCounts = computed(() => {
  return categorizedMaterialFiles.value.reduce((result, item) => {
    result[item.category] = (result[item.category] || 0) + 1
    return result
  }, {})
})

const activeMaterialCategoryInfo = computed(() => {
  return materialUploadCategories.find((item) => item.key === activeMaterialCategory.value) || materialUploadCategories[0]
})

const fileAccept = computed(() => {
  return selectedDeckType.value === 'roadshow'
    ? '.pdf,.tex,.zip,.tgz,.tar.gz,.png,.jpg,.jpeg,.webp,.svg,.md,.txt,.csv,.log,.py,.js,.ts,.java,.sql,.json,.yaml,.yml,.ppt,.pptx,.doc,.docx,.xls,.xlsx'
    : '.pdf,.tex,.zip,.tgz,.tar.gz'
})

const instructionPlaceholder = computed(() => {
  return selectedDeckType.value === 'roadshow'
    ? '写明参赛方向、项目目标、技术重点、现场实操、运行记录、设备环境、团队分工和评审关注点。不要填写姓名、学校、电话、邮箱等个人信息。'
    : '写明论文汇报对象、听众、希望强调的方法、实验、结果或应用价值。'
})

const pagePolicyOptions = computed(() => {
  if (selectedDeckType.value === 'roadshow') {
    return [
      { label: '职业赛制正式稿', value: 'competition' },
      { label: '快速验证 8 页', value: 'smoke' },
      { label: '资料自适应', value: 'auto' }
    ]
  }
  return [
    { label: '资料自适应', value: 'auto' },
    { label: '快速验证 8 页', value: 'smoke' }
  ]
})

const providerOptions = computed(() => {
  return providers.value.flatMap((provider) => {
    return (provider.models || []).map((model) => ({
      label: `${provider.display_name || provider.name} / ${model.display_name || model.id}`,
      value: `${provider.name}::${model.id}`
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

const uploadedFileMeta = computed(() => {
  return uploadedFileSize.value ? `${formatFileSize(uploadedFileSize.value)}，资料已上传` : '资料已上传'
})

const activeRenderEngine = computed(() => {
  if (selectedDeckType.value !== 'roadshow') return 'svg'
  return roadshowOutputType.value === 'editable' ? 'svg' : 'image2'
})

const isRunning = computed(() => {
  return ['queued', 'pending', 'running', 'parsing', 'research', 'content_cards', 'strategy', 'generation', 'postprocess', 'export', 'cancelling'].includes(jobStatus.value)
})
const isFinished = computed(() => ['complete', 'error', 'cancelled'].includes(jobStatus.value))
const hasGeneratedPptContent = computed(() => {
  if (slidesCompleted.value > 0 || totalSlides.value > 0) return true
  return slides.value.some((slide) => {
    return String(slide?.content || slide?.document || '').trim().length > 0
  })
})
const primaryGenerateLabel = computed(() => {
  if (isRunning.value) return '正在生成'
  const outputLabel = selectedDeckType.value === 'roadshow'
    ? (roadshowOutputType.value === 'image' ? '图片 PPT' : '可编辑 PPT')
    : '论文 PPT'
  if (hasGeneratedPptContent.value) return `重新生成${outputLabel}`
  return uploadedSession.value ? `开始生成${outputLabel}` : `生成资料包并开始生成${outputLabel}`
})
const renderFromCardsStatuses = ['pending', 'strategy', 'generation', 'postprocess', 'export']
const waitingForCardConfirmation = computed(() => {
  return selectedDeckType.value === 'roadshow'
    && Boolean(jobId.value)
    && jobStatus.value === 'waiting_confirmation'
})
const hasPendingRoadshowCards = computed(() => {
  return waitingForCardConfirmation.value
    && roadshowCards.value.length > 0
    && !slides.value.length
})
const outputSelectionLocked = computed(() => {
  return isRunning.value
    || waitingForCardConfirmation.value
    || renderingFromCards.value
    || submitting.value
    || refineSubmitting.value
})
const outputTypeHint = computed(() => {
  if (!image2Available.value && roadshowOutputType.value === 'image') {
    return '图片生成暂不可用，请改选「可编辑 PPT」。'
  }
  if (roadshowOutputType.value === 'image') {
    return '下载后每一页是完整图片，适合直接播放。'
  }
  return '下载后可继续改文字和版式，适合再编辑。'
})

const canGenerate = computed(() => {
  if (generateLocked.value || submitting.value) return false
  if (hasPendingRoadshowCards.value) return false
  if (!selectedProviderModel.value || isRunning.value) return false
  if (selectedDeckType.value !== 'roadshow') return Boolean(uploadedSession.value)
  if (roadshowOutputType.value === 'image' && !image2Available.value) return false
  return Boolean(uploadedSession.value || materialReadiness.value.score >= 3)
})
const setupActiveStep = computed(() => canGenerate.value ? 3 : 2)
const canCancel = computed(() => Boolean(jobId.value && isRunning.value))
const jobRecovery = ref({
  session_id: '',
  session_alive: false,
  can_resume: false,
  can_retry: false,
  project_dir_exists: false
})
const isRestartInterruptedError = computed(() => {
  const text = String(errorMessage.value || jobMessage.value || '')
  return /server restarted|生成服务已重启|任务中断/i.test(text)
})
const canResume = computed(() => {
  if (!jobId.value || jobStatus.value !== 'error' || isRunning.value || submitting.value) return false
  if (jobRecovery.value.can_resume) return true
  // Partial progress: continue from generated pages
  if (slidesCompleted.value > 0 && totalSlides.value > slidesCompleted.value) return true
  // Restart mid-run often leaves a workspace with 0 slides — still try resume once
  return isRestartInterruptedError.value
})
const canRetryGenerate = computed(() => {
  if (!jobId.value || jobStatus.value !== 'error' || isRunning.value || submitting.value) return false
  if (jobRecovery.value.can_retry) return true
  return Boolean(uploadedSession.value) || isRestartInterruptedError.value
})
const canDownload = computed(() => Boolean(jobId.value && jobStatus.value === 'complete'))
const canEditSlides = computed(() => Boolean(
  jobId.value
  && isFinished.value
  && activeSlide.value
  && (currentJobRenderEngine.value || activeRenderEngine.value) === 'svg'
))
const canRefine = computed(() => Boolean(jobId.value && isFinished.value && regenFeedback.value.trim() && !isRunning.value))
const showCardPlanning = computed(() => waitingForCardConfirmation.value && roadshowCards.value.length > 0 && !slides.value.length)
const canConfirmCards = computed(() => Boolean(jobId.value && roadshowCards.value.length && waitingForCardConfirmation.value && !renderingFromCards.value))
const downloadUrl = computed(() => jobId.value ? `/api/ppt/download/${jobId.value}` : '')
const progressPercent = computed(() => Math.max(0, Math.min(100, Math.round((progress.value || 0) * 100))))
const progressState = computed(() => {
  if (jobStatus.value === 'complete') return 'success'
  if (jobStatus.value === 'error') return 'exception'
  return undefined
})
const jobTitle = computed(() => {
  if (!jobId.value) return '等待创建任务'
  if (jobStatus.value === 'complete') return '生成完成'
  if (jobStatus.value === 'error') return '生成失败'
  return jobMessage.value || '任务运行中'
})
const jobSubtitle = computed(() => {
  if (!jobId.value) return '上传资料后即可开始生成'
  const count = totalSlides.value ? `${slidesCompleted.value}/${totalSlides.value} 页` : `${slidesCompleted.value} 页`
  const typeLabel = selectedDeckType.value === 'roadshow' ? '路演 PPT' : '论文 PPT'
  return `${typeLabel}任务 ${jobId.value}，已生成 ${count}`
})
const activeSlide = computed(() => slides.value.find((slide) => slide.index === activeSlideIndex.value) || slides.value[0])

const materialReadiness = computed(() => {
  const groups = [
    ['idea_brief', 'project_name', 'scene', 'target_users', 'positioning'],
    ['pain_points', 'solution', 'modules'],
    ['system_form', 'architecture', 'key_technology'],
    ['equipment', 'demo_flow', 'fallback_plan'],
    ['test_environment', 'test_cases', 'test_results'],
    ['team_roles', 'enterprise_value', 'school_value', 'employment_value', 'ip_cooperation']
  ]
  const completeGroups = groups.filter((keys) => keys.some((key) => String(materialForm.value[key] || '').trim().length >= 8)).length
  const fileBoost = uploadedSession.value || materialFiles.value.length || categorizedMaterialFiles.value.length ? 2 : 0
  const score = Math.min(10, Math.round((completeGroups / groups.length) * 8 + fileBoost))
  const missing = []
  if (!String(materialForm.value.idea_brief || materialForm.value.project_name || '').trim()) missing.push('项目想法或项目名称')
  if (!String(materialForm.value.modules || '').trim()) missing.push('核心模块')
  if (!String(materialForm.value.demo_flow || '').trim()) missing.push('实操流程')
  if (!String(materialForm.value.team_roles || '').trim()) missing.push('团队分工')
  return { score, missing }
})

const readinessScore = computed(() => materialReadiness.value.score)
const readinessTitle = computed(() => {
  if (readinessScore.value >= 8) return '资料基础较完整'
  if (readinessScore.value >= 5) return '可以生成，但建议再补几项'
  return '先补关键事实，PPT 才不会空'
})
const readinessHint = computed(() => {
  const missing = materialReadiness.value.missing
  if (!missing.length) return '系统会生成标准素材包，并在生成链路中补充政策、市场和文档材料。'
  return `建议补充：${missing.slice(0, 4).join('、')}`
})

const sectionSummaries = computed(() => {
  return roadshowQuestionnaire.map((section, index) => {
    const filled = section.fields.filter((field) => String(materialForm.value[field.key] || '').trim().length >= 8).length
    return {
      key: section.key,
      index: String(index + 1).padStart(2, '0'),
      shortTitle: section.title.replace(/^\d+\.\s*/, ''),
      done: filled > 0
    }
  })
})
const completedQuestionSections = computed(() => {
  return sectionSummaries.value.filter((item) => item.done).length
})

onMounted(async () => {
  pptRequestLifecycle.activate()
  pptMounted = true
  const restoreIntentVersion = pptViewIntentVersion
  restoreSetupDraft()
  loadMeta()
  await loadHistory()
  const jobFromQuery = String(route.query.job || '').trim()
  if (jobFromQuery) {
    await openHistoryJob({ job_id: jobFromQuery }, { inPlace: true, silent: false })
    return
  }
  if (!skipInitialJobRestore && isAutomaticRestoreCurrent(restoreIntentVersion)) {
    await restoreLastOpenedJob(restoreIntentVersion)
  }
})

watch(
  () => route.query.job,
  async (job, prev) => {
    const next = String(job || '').trim()
    if (!next || next === String(prev || '').trim()) return
    if (!pptMounted) return
    await openHistoryJob({ job_id: next }, { inPlace: true, silent: false })
  }
)

watch(selectedDeckType, (type) => {
  if (type === 'roadshow') {
    if (instruction.value === paperInstruction || !instruction.value.trim()) {
      instruction.value = roadshowInstruction
    }
    if (!pagePolicyOptions.value.some((item) => item.value === pagePolicy.value)) {
      pagePolicy.value = 'competition'
    }
    if (pagePolicy.value === 'auto') pagePolicy.value = 'competition'
    return
  }
  if (instruction.value === roadshowInstruction || !instruction.value.trim()) {
    instruction.value = paperInstruction
  }
  if (!pagePolicyOptions.value.some((item) => item.value === pagePolicy.value)) {
    pagePolicy.value = 'auto'
  }
  if (pagePolicy.value === 'competition') pagePolicy.value = 'auto'
})

watch(activeSlide, () => {
  refreshActiveSlideEditors()
})

watch(activeSlideIndex, () => {
  if (jobId.value) rememberLastOpenedJob()
})

watch(
  [
    selectedDeckType,
    roadshowOutputType,
    selectedTemplate,
    pagePolicy,
    instruction,
    materialForm
  ],
  persistSetupDraft,
  { deep: true }
)

onBeforeUnmount(() => {
  pptRequestLifecycle.invalidate()
  pptViewIntentVersion += 1
  closeSocket()
  stopPolling()
  stopPass2Heartbeat()
  pptMounted = false
})

function pptSetupDraftStorageKey() {
  const user = getStoredUser()
  const owner = user?.id || user?.username || 'anonymous'
  return `${pptSetupDraftKeyPrefix}:${owner}`
}

function persistSetupDraft() {
  try {
    window.localStorage.setItem(pptSetupDraftStorageKey(), JSON.stringify({
      deckType: selectedDeckType.value,
      outputType: roadshowOutputType.value,
      template: selectedTemplate.value,
      pagePolicy: pagePolicy.value,
      instruction: instruction.value,
      projectInfo: materialForm.value,
      updatedAt: Date.now()
    }))
  } catch (_) {
    // 本地草稿失败不阻断创建流程。
  }
}

function restoreSetupDraft() {
  try {
    const raw = window.localStorage.getItem(pptSetupDraftStorageKey())
    const saved = raw ? JSON.parse(raw) : null
    if (!saved || typeof saved !== 'object') return
    if (saved.deckType === 'roadshow' || saved.deckType === 'paper') {
      selectedDeckType.value = saved.deckType
    }
    if (saved.outputType === 'image' || saved.outputType === 'editable') {
      roadshowOutputType.value = saved.outputType
    }
    if (typeof saved.template === 'string') selectedTemplate.value = saved.template
    if (typeof saved.pagePolicy === 'string') pagePolicy.value = saved.pagePolicy
    if (typeof saved.instruction === 'string' && saved.instruction.trim()) {
      instruction.value = saved.instruction
    }
    if (saved.projectInfo && typeof saved.projectInfo === 'object') {
      materialForm.value = {
        ...materialForm.value,
        ...saved.projectInfo
      }
    }
  } catch (_) {
    // 无效或过期草稿直接忽略。
  }
}

async function loadMeta() {
  loadingMeta.value = true
  try {
    const [health, providerRes, templateRes] = await Promise.all([
      apiGet('/api/ppt/health'),
      apiGet('/api/ppt/providers'),
      apiGet('/api/ppt/templates')
    ])
    healthOk.value = health.status === 'ok'
    image2Available.value = health.image2_configured !== false
    if (!image2Available.value && roadshowOutputType.value === 'image') {
      roadshowOutputType.value = 'editable'
    }
    providers.value = providerRes.providers || []
    templates.value = templateRes || []
    const mimo = providerOptions.value.find((item) => item.value.startsWith('mimo::'))
    if (mimo) selectedProviderModel.value = mimo.value
    if (
      selectedTemplate.value
      && !templateOptions.value.some((item) => item.value === selectedTemplate.value)
    ) {
      selectedTemplate.value = ''
    }
  } catch (error) {
    healthOk.value = false
    appendLog('service', readError(error, 'PPT 生成服务暂不可用'))
  } finally {
    loadingMeta.value = false
  }
}

async function loadHistory() {
  loadingHistory.value = true
  historyError.value = ''
  try {
    const result = await apiGet('/api/ppt/history')
    historyJobs.value = result.jobs || []
  } catch (error) {
    historyError.value = readError(error, '历史记录加载失败')
    appendLog('history', historyError.value)
  } finally {
    loadingHistory.value = false
  }
}

async function openHistoryDrawer() {
  if (route.query.view === 'history') {
    historyDrawer.value = true
    await loadHistory()
    return
  }
  await router.push({ path: '/ppt-editor', query: { view: 'history' } })
}

function handleHistoryDrawerClosed() {
  if (route.query.view === 'history') {
    // 保留 job 参数（若正在打开某条历史）
    const job = route.query.job
    router.replace(job ? { path: '/ppt-editor', query: { job: String(job) } } : '/ppt-editor')
  }
}

function handleWorkspaceMoreAction(command) {
  if (command === 'history') {
    openHistoryDrawer()
    return
  }
  if (command === 'settings') openSetup()
}

function isAutomaticRestoreCurrent(intentVersion) {
  return route.path === '/ppt-editor'
    && intentVersion === pptViewIntentVersion
    && !route.query.view
    && pptView.value === 'landing'
}

function openSetup() {
  const fromWorkspace = pptView.value === 'workspace'
  if (fromWorkspace) pptRequestLifecycle.activate()
  pptViewIntentVersion += 1
  advancedSettingsOpen.value = false
  pptView.value = 'setup'
  const target = { path: '/ppt-editor', query: { view: 'setup' } }
  if (fromWorkspace) router.push(target)
  else router.replace(target)
}

function openWorkspaceView() {
  pptViewIntentVersion += 1
  pptView.value = 'workspace'
  if (route.query.view) router.replace('/ppt-editor')
}

async function createNewPpt() {
  if (isRunning.value) {
    ElMessage.warning('当前任务正在生成，请先取消或等待完成后再新建 PPT。')
    return
  }
  if (jobId.value || hasGeneratedPptContent.value) {
    try {
      await ElMessageBox.confirm(
        '新建 PPT 会清空当前预览、任务状态和素材上传区；已生成记录仍可在“最近记录”中打开。项目问卷内容会保留。',
        '新建 PPT',
        {
          confirmButtonText: '新建 PPT',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    } catch (_) {
      return
    }
  }
  resetJobState()
  resetUploadedMaterials()
  roadshowOutputType.value = 'image'
  linkedPptScript.value = null
  advancedSettingsOpen.value = false
  forgetLastOpenedJob()
  pptViewIntentVersion += 1
  pptView.value = 'landing'
  ElMessage.success('已返回创建首页，可以开始新的 PPT。')
}

function resetUploadedMaterials() {
  uploadedSession.value = ''
  uploadedFileName.value = ''
  uploadedFileSize.value = 0
  materialFiles.value = []
  categorizedMaterialFiles.value = []
  materialFileUid = 0
  uploadResetKey.value += 1
  if (mainUploadInput.value) {
    mainUploadInput.value.value = ''
  }
  if (basketUploadInput.value) {
    basketUploadInput.value.value = ''
  }
  syncRoadshowFileSummary()
}

function openMainUploadPicker() {
  mainUploadInput.value?.click()
}

async function openQuestionnaireSection(key) {
  if (key) {
    activeQuestionSections.value = Array.from(new Set([...activeQuestionSections.value, key]))
  }
  questionnaireDrawer.value = true
}

function handleMaterialBasketChange(event) {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  const category = activeMaterialCategory.value
  categorizedMaterialFiles.value = [
    ...categorizedMaterialFiles.value,
    ...files.map((file) => ({
      id: ++materialFileUid,
      file,
      category
    }))
  ]
  uploadedSession.value = ''
  syncRoadshowFileSummary()
  ElMessage.success(`已加入 ${files.length} 个${materialCategoryLabel(category)}材料`)
  if (event.target) event.target.value = ''
}

function removeCategorizedMaterialFile(id) {
  categorizedMaterialFiles.value = categorizedMaterialFiles.value.filter((item) => item.id !== id)
  syncRoadshowFileSummary()
}

function materialCategoryLabel(key) {
  return materialUploadCategories.find((item) => item.key === key)?.label || '补充材料'
}

function syncRoadshowFileSummary() {
  const allFiles = [
    ...materialFiles.value,
    ...categorizedMaterialFiles.value.map((item) => item.file)
  ]
  if (!allFiles.length) {
    if (!uploadedSession.value) {
      uploadedFileName.value = ''
      uploadedFileSize.value = 0
    }
    return
  }
  uploadedFileName.value = allFiles.map((file) => file.name).slice(0, 2).join('、') + (allFiles.length > 2 ? ` 等 ${allFiles.length} 个` : '')
  uploadedFileSize.value = allFiles.reduce((sum, file) => sum + file.size, 0)
}

async function openHistoryJob(item, options = {}) {
  const jobKey = item?.job_id || item?.jobId || item?.id
  if (!jobKey) {
    if (!options.silent) ElMessage.warning('该记录缺少任务 ID，无法打开')
    return false
  }
  // 通过路由打开：避免抽屉关闭时中断请求，也保证可刷新/分享
  if (!options.inPlace && !options.silent) {
    suppressHistoryInvalidate = true
    historyDrawer.value = false
    const query = { job: String(jobKey) }
    if (String(route.query.job || '') === String(jobKey) && !route.query.view) {
      // 已在目标路由，直接原地加载
      return openHistoryJob(item, { ...options, inPlace: true, silent: false })
    }
    await router.push({ path: '/ppt-editor', query })
    return true
  }

  const intentVersion = ++pptHistoryIntentVersion
  if (!pptRequestLifecycle.isActive()) pptRequestLifecycle.activate()
  const operation = pptRequestLifecycle.open('history-detail')
  closeSocket()
  stopPolling()
  try {
    const detail = await apiGet(`/api/ppt/history/${jobKey}`, {
      signal: operation.signal
    })
    if (!operation.isCurrent() || intentVersion !== pptHistoryIntentVersion) return false
    if (
      options.restoreIntentVersion !== undefined
      && !isAutomaticRestoreCurrent(options.restoreIntentVersion)
    ) {
      return false
    }
    const job = detail.job || item
    jobId.value = job.job_id || jobKey
    uploadedSession.value = job.session_id || ''
    uploadedFileName.value = job.file?.name || ''
    uploadedFileSize.value = job.file?.size || 0
    selectedDeckType.value = job.deck_type === 'paper' ? 'paper' : 'roadshow'
    roadshowOutputType.value = job.render_engine === 'svg' ? 'editable' : 'image'
    currentJobRenderEngine.value = job.render_engine === 'svg' ? 'svg' : (selectedDeckType.value === 'roadshow' ? 'image2' : 'svg')
    instruction.value = job.instruction || instruction.value
    jobStatus.value = job.status || ''
    jobMessage.value = cleanPptMessage(job.message || '')
    progress.value = Number(job.progress || 0)
    slidesCompleted.value = Number(job.slides_completed || 0)
    totalSlides.value = Number(job.total_slides || job.slide_count || 0)
    errorMessage.value = job.status === 'error' || job.status === 'failed'
      ? cleanPptMessage(job.message || job.last_event || '任务失败')
      : ''
    logs.value = (detail.events || []).slice(-80).reverse().map((event) => ({
      id: ++logId,
      stage: displayPptStage(event.stage || event.type || 'event'),
      message: cleanPptMessage(event.message || event.status || event.type || '已记录')
    }))
    rememberLastOpenedJob(jobId.value)
    // 先进入工作台，再拉预览；避免用户感觉“点了没反应”
    openWorkspaceView()
    suppressHistoryInvalidate = true
    historyDrawer.value = false
    if (selectedDeckType.value === 'roadshow') {
      await loadRoadshowPlan(jobId.value)
    }
    if (!operation.isCurrent() || intentVersion !== pptHistoryIntentVersion) return false
    await loadPreviewAndCritic(jobId.value)
    if (isRunning.value) {
      connectSocket(jobId.value)
      startPolling(jobId.value)
    }
    if (!options.silent) {
      ElMessage.success('历史任务已打开')
    }
    return true
  } catch (error) {
    if (!operation.isCurrent() || intentVersion !== pptHistoryIntentVersion) return false
    if (options.silent) {
      forgetLastOpenedJob()
    } else {
      ElMessage.error(readError(error, '打开历史任务失败，请确认该任务属于当前账号'))
    }
    return false
  } finally {
    operation.release()
    window.setTimeout(() => {
      suppressHistoryInvalidate = false
    }, 400)
  }
}

function invalidateHistoryDetailIntent() {
  if (suppressHistoryInvalidate) return
  pptHistoryIntentVersion += 1
  pptRequestLifecycle.open('history-detail').release()
}

function lastPptJobStorageKey() {
  const user = getStoredUser()
  const owner = user?.id || user?.username || 'anonymous'
  return `${lastPptJobKeyPrefix}:${owner}`
}

function rememberLastOpenedJob(id = jobId.value) {
  if (!id) return
  try {
    window.localStorage.setItem(lastPptJobStorageKey(), JSON.stringify({
      jobId: id,
      deckType: selectedDeckType.value,
      activePage: activeSlideIndex.value,
      updatedAt: Date.now()
    }))
  } catch (_) {
    // 本地恢复失败不影响生成和保存链路。
  }
}

function forgetLastOpenedJob() {
  try {
    window.localStorage.removeItem(lastPptJobStorageKey())
  } catch (_) {
    // ignore
  }
}

async function restoreLastOpenedJob(restoreIntentVersion) {
  try {
    if (!isAutomaticRestoreCurrent(restoreIntentVersion)) return
    const raw = window.localStorage.getItem(lastPptJobStorageKey())
    const saved = raw ? JSON.parse(raw) : null
    if (jobId.value) return
    if (saved?.jobId) {
      const restored = await openHistoryJob(
        { job_id: saved.jobId },
        { silent: true, restoreIntentVersion }
      )
      if (restored) {
        if (saved.activePage) {
          activeSlideIndex.value = Number(saved.activePage) || activeSlideIndex.value
        }
        return
      }
    }
    const restorableStatuses = new Set([
      'pending',
      'parsing',
      'research',
      'content_cards',
      'waiting_confirmation',
      'strategy',
      'generation',
      'postprocess',
      'export',
      'complete',
      'completed',
      'success'
    ])
    const latestJob = historyJobs.value.find((item) => restorableStatuses.has(String(item.status || '')))
    if (latestJob?.job_id && isAutomaticRestoreCurrent(restoreIntentVersion)) {
      await openHistoryJob(latestJob, { silent: true, restoreIntentVersion })
    }
  } catch (_) {
    forgetLastOpenedJob()
  }
}

async function loadVersions(id) {
  if (!id) {
    versions.value = []
    return
  }
  try {
    const result = await apiGet(`/api/ppt/versions/${id}`)
    versions.value = result.versions || []
  } catch (_) {
    versions.value = []
  }
}

function onMainDropFiles(value) {
  const files = Array.isArray(value) ? value : value ? [value] : []
  handleFileChange({ target: { files, value: '' } })
}

function onBasketDropFiles(value) {
  const files = Array.isArray(value) ? value : value ? [value] : []
  handleMaterialBasketChange({ target: { files, value: '' } })
}

async function handleFileChange(event) {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  if (selectedDeckType.value === 'roadshow') {
    const directFile = files.length === 1 && isDirectUploadFile(files[0])
    if (!directFile) {
      materialFiles.value = files
      uploadedSession.value = ''
      syncRoadshowFileSummary()
      ElMessage.success('补充文件已选择，将与问卷一起生成资料包')
      if (event.target) event.target.value = ''
      return
    }
  }
  const file = files[0]
  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const result = await apiFetch('/api/ppt/upload', {
      method: 'POST',
      body: formData
    })
    uploadedSession.value = result.session_id
    uploadedFileName.value = result.file_info?.name || file.name
    uploadedFileSize.value = result.file_info?.size || file.size
    materialFiles.value = []
    categorizedMaterialFiles.value = []
    ElMessage.success('资料上传完成')
  } catch (error) {
    ElMessage.error(readError(error, '上传失败'))
  } finally {
    submitting.value = false
    if (event.target) event.target.value = ''
  }
}

function isDirectUploadFile(file) {
  const name = String(file?.name || '').toLowerCase()
  return ['.pdf', '.tex', '.zip', '.tgz', '.tar.gz'].some((suffix) => name.endsWith(suffix))
}

async function startGenerate() {
  if (generateLocked.value || !canGenerate.value) return
  generateLocked.value = true
  const operation = pptRequestLifecycle.open('generate')
  try {
    if (hasPendingRoadshowCards.value) {
      ElMessage.warning('当前内容卡片正在等待确认，请先确认后进入设计渲染。')
      return
    }
    if (hasGeneratedPptContent.value) {
      try {
        await ElMessageBox.confirm(
          '重新生成会基于当前资料和问卷创建新任务；当前已生成内容仍可在“最近记录”中打开。',
          '重新生成 PPT',
          {
            confirmButtonText: '重新生成',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        if (!operation.isCurrent()) return
      } catch (_) {
        return
      }
    }
    resetJobState()
    submitting.value = true
    const currentProvider = selectedProvider.value
    let sessionId = uploadedSession.value
    const payload = {
      session_id: sessionId,
      instruction: buildGenerationInstruction(),
      model_config: {
        provider: currentProvider.provider,
        model: currentProvider.model,
        api_key: '',
        base_url: currentProvider.baseUrl
      },
      options: {
        deck_type: selectedDeckType.value,
        mode: selectedDeckType.value === 'roadshow' ? 'plan_only' : 'full',
        render_engine: activeRenderEngine.value,
        canvas_format: 'ppt169',
        style: selectedDeckType.value === 'roadshow' ? 'roadshow' : 'academic',
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

    if (selectedDeckType.value === 'roadshow' && !sessionId) {
      const prepared = await prepareMaterialSession(operation)
      if (!operation.isCurrent()) return
      sessionId = prepared.session_id
      uploadedSession.value = sessionId
      uploadedFileName.value = prepared.file_info?.name || 'roadshow_materials.zip'
      uploadedFileSize.value = prepared.file_info?.size || 0
      payload.session_id = sessionId
      appendLog('materials', '已根据问卷生成标准项目资料包')
    }
    const result = await apiFetch('/api/ppt/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: operation.signal
    })
    if (!operation.isCurrent()) return
    jobId.value = result.job_id
    currentJobRenderEngine.value = activeRenderEngine.value
    jobStatus.value = 'pending'
    jobMessage.value = '任务已入队'
    rememberLastOpenedJob(result.job_id)
    openWorkspaceView()
    appendLog('pending', `任务 ${result.job_id} 已创建`)
    connectSocket(result.job_id)
    startPolling(result.job_id)
  } catch (error) {
    if (!operation.isCurrent()) return
    errorMessage.value = readError(error, '创建生成任务失败')
    // Upload session lives on the AI service process; after restart / multi-worker
    // mismatch the id becomes invalid — force re-upload on next try.
    if (/session not found/i.test(String(errorMessage.value || ''))) {
      uploadedSession.value = ''
      errorMessage.value = '上传会话已失效，请重新选择/上传资料后再生成'
    }
    ElMessage.error(errorMessage.value)
  } finally {
    if (operation.isCurrent()) submitting.value = false
    generateLocked.value = false
    operation.release()
  }
}

async function prepareMaterialSession(operation) {
  const formData = new FormData()
  formData.append('questionnaire_json', JSON.stringify(normalizedMaterialForm()))
  formData.append('additional_notes', instruction.value || '')
  const categoryRecords = []
  for (const file of materialFiles.value) {
    formData.append('files', file)
    categoryRecords.push({ name: file.name, size: file.size, category: 'general' })
  }
  for (const item of categorizedMaterialFiles.value) {
    formData.append('files', item.file)
    categoryRecords.push({ name: item.file.name, size: item.file.size, category: item.category })
  }
  formData.append('file_categories_json', JSON.stringify(categoryRecords))
  return apiFetch('/api/ppt/materials/prepare', {
    method: 'POST',
    body: formData,
    signal: operation.signal
  })
}

function normalizedMaterialForm() {
  const data = { ...materialForm.value }
  data.extra_requirements = instruction.value || ''
  return data
}

function buildGenerationInstruction() {
  if (selectedDeckType.value !== 'roadshow') return instruction.value
  const fields = normalizedMaterialForm()
  const questionnaireText = Object.entries(fields)
    .filter(([, value]) => String(value || '').trim())
    .map(([key, value]) => `- ${key}: ${String(value).trim()}`)
    .join('\n')
  return [
    roadshowInstruction,
    '',
    '资料准备要求：如果用户没有上传真实截图、日志、合作证明、证书、专利或测试结果，只能生成示意视觉、验证方法、待采集口径或材料模板，不得写成已完成事实。',
    '必须补齐项目说明书、界面/设备示意、关键代码或接口说明、数据库表结构、测试用例、实操流程、团队匿名分工、调研/反馈、成果规划、现场设备清单和备用方案。',
    '可见 PPT 禁止出现姓名、学校、电话、邮箱；禁止出现“证据”二字，改用支撑材料、运行记录、验证结果、成果材料、资料来源。',
    '',
    questionnaireText ? `用户问卷信息：\n${questionnaireText}` : '',
    '',
    instruction.value ? `用户补充说明：\n${instruction.value}` : ''
  ].filter(Boolean).join('\n')
}

async function cancelJob() {
  if (!jobId.value) return
  try {
    const result = await apiFetch(`/api/ppt/status/${jobId.value}/cancel`, { method: 'POST' })
    const nextStatus = result?.status || 'cancelling'
    jobStatus.value = nextStatus === 'cancelled' ? 'cancelled' : 'cancelling'
    jobMessage.value = nextStatus === 'cancelled' ? '已取消生成' : '正在取消生成…'
    appendLog('cancelled', nextStatus === 'cancelled' ? '任务已取消' : '已请求取消任务，等待 worker 停止')
    if (nextStatus === 'cancelled') {
      stopPolling()
      closeSocket()
    } else {
      // Keep polling briefly so UI flips to cancelled when worker acknowledges.
      startPolling(jobId.value)
    }
    ElMessage.success(nextStatus === 'cancelled' ? '已取消生成' : '正在取消…')
  } catch (error) {
    ElMessage.error(readError(error, '取消失败'))
  }
}

async function resumeJob() {
  if (!jobId.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const result = await apiFetch(`/api/ppt/generate/${jobId.value}/resume`, {
      method: 'POST'
    })
    jobStatus.value = result.status === 'running' ? 'generation' : 'pending'
    jobMessage.value = '已从缓存页继续生成'
    openWorkspaceView()
    appendLog('resume', `任务 ${jobId.value} 已从 ${slidesCompleted.value}/${totalSlides.value} 页继续`)
    connectSocket(jobId.value)
    startPolling(jobId.value)
  } catch (error) {
    errorMessage.value = readError(error, '恢复任务失败')
    ElMessage.error(errorMessage.value)
  } finally {
    submitting.value = false
  }
}

function connectSocket(id, retryCount = 0) {
  if (route.path !== '/ppt-editor') return
  closeSocket()
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = getUserToken()
  const params = new URLSearchParams({ since_seq: '0' })
  if (token) params.set('t', token)
  socket = new WebSocket(`${protocol}//${window.location.host}/api/ppt/ws/${id}?${params.toString()}`)
  socket.onopen = () => {
    socketRetryTimer = null
  }
  socket.onmessage = (event) => {
    try {
      handleAgentEvent(JSON.parse(event.data))
    } catch (_) {
      appendLog('ws', '收到无法解析的进度消息')
    }
  }
  socket.onerror = () => {
    if (retryCount < 2) {
      socketRetryTimer = window.setTimeout(() => connectSocket(id, retryCount + 1), 1200)
      return
    }
    appendLog('ws', '实时通道暂不可用，已自动切换轮询')
  }
}

function closeSocket() {
  if (socketRetryTimer) {
    window.clearTimeout(socketRetryTimer)
    socketRetryTimer = null
  }
  if (socket) {
    socket.close()
    socket = null
  }
}

function startPolling(id) {
  if (route.path !== '/ppt-editor') return
  stopPolling()
  pollFailureCount = 0
  lastPollErrorMessage = ''
  stopPass2Heartbeat()
  pollTimer = window.setInterval(() => syncStatus(id), 5000)
  syncStatus(id)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function isPass2ResearchActive() {
  if (!isRunning.value || jobStatus.value !== 'research') return false
  return /Pass 2\/8|比赛大纲|五大板块/.test(jobMessage.value || '')
}

function isPass4ResearchActive() {
  if (!isRunning.value || jobStatus.value !== 'research') return false
  return /Pass 4\/8|选手视角|支撑对象/.test(jobMessage.value || '')
}

function syncPass2Heartbeat() {
  if (isPass2ResearchActive()) {
    if (!pass2HeartbeatTimer) {
      pass2HeartbeatIndex = 0
      pass2HeartbeatTimer = window.setInterval(emitPass2Heartbeat, 5000)
    }
  } else if (pass2HeartbeatTimer) {
    window.clearInterval(pass2HeartbeatTimer)
    pass2HeartbeatTimer = null
  }

  if (isPass4ResearchActive()) {
    if (!pass4HeartbeatTimer) {
      pass4HeartbeatIndex = 0
      pass4HeartbeatTimer = window.setInterval(emitPass4Heartbeat, 5000)
    }
  } else if (pass4HeartbeatTimer) {
    window.clearInterval(pass4HeartbeatTimer)
    pass4HeartbeatTimer = null
  }
}

function stopPass2Heartbeat() {
  if (pass2HeartbeatTimer) {
    window.clearInterval(pass2HeartbeatTimer)
    pass2HeartbeatTimer = null
  }
  if (pass4HeartbeatTimer) {
    window.clearInterval(pass4HeartbeatTimer)
    pass4HeartbeatTimer = null
  }
}

function emitPass2Heartbeat() {
  if (!isPass2ResearchActive()) {
    stopPass2Heartbeat()
    return
  }
  if (Date.now() - lastResearchProgressAt < 15000) return
  const message = pass2SafeHeartbeatMessages[Math.min(pass2HeartbeatIndex, pass2SafeHeartbeatMessages.length - 1)]
  const suffix = pass2HeartbeatIndex >= pass2SafeHeartbeatMessages.length
    ? `，已持续处理 ${Math.round((pass2HeartbeatIndex + 1) * 15)} 秒，任务仍在后台运行`
    : ''
  const safeMessage = `${message}${suffix}`
  jobMessage.value = safeMessage
  appendLog('research', safeMessage)
  pass2HeartbeatIndex += 1
}

function emitPass4Heartbeat() {
  if (!isPass4ResearchActive()) {
    stopPass2Heartbeat()
    return
  }
  if (Date.now() - lastResearchProgressAt < 15000) return
  const message = pass4SafeHeartbeatMessages[Math.min(pass4HeartbeatIndex, pass4SafeHeartbeatMessages.length - 1)]
  const suffix = pass4HeartbeatIndex >= pass4SafeHeartbeatMessages.length
    ? `，已持续处理 ${Math.round((pass4HeartbeatIndex + 1) * 15)} 秒，任务仍在后台运行`
    : ''
  const safeMessage = `${message}${suffix}`
  jobMessage.value = safeMessage
  appendLog('research', safeMessage)
  pass4HeartbeatIndex += 1
}

function svgHasExternalImageRefs(svg) {
  return /href=["'](?!data:|https?:|blob:|\/)([^"']+\.(?:png|jpe?g|gif|webp|pdf))["']/i.test(svg || '')
}

function shouldRefreshPreviewDuringGeneration(status, completed) {
  if (status.status !== 'generation') return false
  if (completed > slides.value.length) {
    renderReadyRefreshAttempts = 0
    return true
  }
  if (!slides.value.length) return false
  const needsRenderReadyRefresh = slides.value.some((slide) => svgHasExternalImageRefs(slide.content))
  if (!needsRenderReadyRefresh) {
    renderReadyRefreshAttempts = 0
    return false
  }
  const now = Date.now()
  if (now - lastPreviewRefreshAt < 15000) return false
  if (renderReadyRefreshAttempts >= 4) return false
  renderReadyRefreshAttempts += 1
  return true
}

async function syncStatus(id) {
  if (statusSyncInFlight) return
  statusSyncInFlight = true
  try {
    const previousCompleted = Number(slidesCompleted.value || 0)
    const status = await apiGet(`/api/ppt/status/${id}`)
    if (id !== jobId.value) return
    if (pollFailureCount >= 3) {
      appendLog('poll', '状态同步已恢复，继续保留当前生成进度')
    }
    pollFailureCount = 0
    lastPollErrorMessage = ''
    applyStatus(status)
    recordProgressLog(status, previousCompleted)
    const completed = Number(status.slides_completed || 0)
    if (shouldRefreshPreviewDuringGeneration(status, completed)) {
      await loadPreviewSlides(id)
    }
    if (status.status === 'waiting_confirmation') {
      stopPolling()
      closeSocket()
      await loadRoadshowPlan(id)
    }
    if (['complete', 'error', 'cancelled'].includes(status.status)) {
      stopPolling()
      closeSocket()
      if (selectedDeckType.value === 'roadshow') {
        await loadRoadshowPlan(id)
      }
      await loadPreviewAndCritic(id)
    }
  } catch (error) {
    pollFailureCount += 1
    lastPollErrorMessage = readError(error, '状态同步失败')
    // Debounce: first warn at 3 failures (~15s), then every ~30s — avoid log spam on 502.
    if (pollFailureCount === 3 || (pollFailureCount > 3 && pollFailureCount % 6 === 0)) {
      appendLog(
        'poll',
        `状态同步暂时失败，正在重试；后台任务进度不会被重置（${lastPollErrorMessage}）`
      )
    }
  } finally {
    statusSyncInFlight = false
  }
}

function handleAgentEvent(event) {
  if (event.type === 'ping') return
  if (event.type === 'slide_ready' && event.data?.svg) {
    const page = Number(event.data.page || slides.value.length + 1)
    const slide = {
      index: page,
      name: `slide_${page}`,
      content: sanitizeCoverSvgContent(event.data.svg, page),
      notes: '',
      document: null
    }
    upsertSlide(slide, { follow: true })
    logSlideReady(page, Number(event.total_slides || totalSlides.value || 0))
  }
  if (event.type === 'progress' || event.type === 'complete' || event.type === 'error') {
    const previousCompleted = Number(slidesCompleted.value || 0)
    applyStatus(event)
    recordProgressLog(event, previousCompleted)
  }
  if (event.stage === 'content_cards' || event.stage === 'waiting_confirmation') {
    loadRoadshowPlan(jobId.value)
  }
  if (event.stage === 'waiting_confirmation') {
    stopPolling()
    closeSocket()
  }
  if (event.type === 'complete' || event.type === 'error') {
    if (selectedDeckType.value === 'roadshow') {
      loadRoadshowPlan(jobId.value).finally(() => loadPreviewAndCritic(jobId.value))
    } else {
      loadPreviewAndCritic(jobId.value)
    }
    stopPolling()
  }
}

function applyStatus(status) {
  const renderEngine = status.render_engine || status.data?.render_engine
  if (selectedDeckType.value === 'roadshow' && ['svg', 'image2'].includes(renderEngine)) {
    roadshowOutputType.value = renderEngine === 'svg' ? 'editable' : 'image'
    currentJobRenderEngine.value = renderEngine
  }
  jobStatus.value = status.type === 'complete'
    ? 'complete'
    : (status.stage || status.status)
  jobMessage.value = cleanPptMessage(status.message || jobMessage.value)
  progress.value = Math.max(Number(progress.value || 0), Number(status.progress || 0))
  slidesCompleted.value = Math.max(Number(slidesCompleted.value || 0), Number(status.slides_completed || 0))
  totalSlides.value = Math.max(Number(totalSlides.value || 0), Number(status.total_slides || 0))
  jobRecovery.value = {
    session_id: status.session_id || jobRecovery.value.session_id || '',
    session_alive: Boolean(status.session_alive),
    can_resume: Boolean(status.can_resume),
    can_retry: Boolean(status.can_retry),
    project_dir_exists: Boolean(status.project_dir_exists)
  }
  if (status.session_id && status.session_alive && !uploadedSession.value) {
    uploadedSession.value = String(status.session_id)
  }
  // Only surface hard failures. Stale error text left on a healthy mid-run job
  // (e.g. after worker restart + requeue) must not paint the UI as 异常.
  const hardFailed = status.type === 'error' || status.status === 'error' || jobStatus.value === 'error'
  if (hardFailed) {
    errorMessage.value = cleanPptMessage(status.error || status.message || '生成失败')
  } else if (status.error && !['cancelled', 'cancelling'].includes(jobStatus.value)) {
    // Non-terminal progress with leftover error field: ignore for banner.
    errorMessage.value = ''
  }
  syncPass2Heartbeat()
}

async function loadPreviewAndCritic(id) {
  if (!id) return
  await loadPreviewSlides(id, { forceFirst: true })
  try {
    const critic = await apiGet(`/api/ppt/critic/${id}`)
    criticEvents.value = critic.events || []
  } catch (_) {
    criticEvents.value = []
  }
  await loadVersions(id)
}

async function loadPreviewSlides(id, options = {}) {
  if (!id) return
  try {
    lastPreviewRefreshAt = Date.now()
    const preview = await apiGet(`/api/ppt/preview/${id}?render_ready=true`)
    if (id !== jobId.value) return false
    if (preview.slides?.length) {
      const persistedScripts = await loadPersistedSlideScripts(id)
      const incomingSlides = preview.slides.map(sanitizeCoverSlide)
      const mergedSlides = mergeGeneratedScriptDrafts(mergePersistedSlideScripts(incomingSlides, persistedScripts))
      await syncAutoGeneratedSlideScripts(id, mergedSlides, persistedScripts)
      await flushPendingSlideScripts(id)
      const nextSlides = mergeStablePreviewSlides(slides.value, mergedSlides)
      const nextSignature = slidesRevisionKey(nextSlides)
      if (nextSignature !== lastPreviewSignature) {
        slides.value = nextSlides
        lastPreviewSignature = nextSignature
      }
      if (options.forceFirst) {
        activeSlideIndex.value = mergedSlides[0].index
      } else if (followGeneratedSlides.value) {
        activeSlideIndex.value = mergedSlides[mergedSlides.length - 1].index
      }
    }
  } catch (error) {
    appendLog('preview', readError(error, '预览暂不可用'))
  }
}

function mergeStablePreviewSlides(currentSlides, incomingSlides) {
  const currentByIndex = new Map(currentSlides.map((slide) => [Number(slide.index), slide]))
  return incomingSlides.map((slide) => {
    const current = currentByIndex.get(Number(slide.index))
    if (!current) return slide
    if (hasRenderableSlideContent(current) && !hasRenderableSlideContent(slide)) return current
    return slideRevisionKey(current) === slideRevisionKey(slide) ? current : slide
  })
}

function hasRenderableSlideContent(slide) {
  const content = String(slide?.content || '').trim()
  return content.length > 120 && /<svg[\s>]/i.test(content)
}

function slidesRevisionKey(items) {
  return items.map(slideRevisionKey).join('|')
}

function slideRevisionKey(slide) {
  return [
    Number(slide?.index || 0),
    hashString(slide?.content || ''),
    hashString(slide?.notes || ''),
    hashString(stableJson(slide?.document || null))
  ].join(':')
}

function stableJson(value) {
  if (!value || typeof value !== 'object') return String(value || '')
  try {
    return JSON.stringify(value)
  } catch (_) {
    return ''
  }
}

function hashString(value) {
  const text = String(value || '')
  let hash = 0
  for (let i = 0; i < text.length; i += 1) {
    hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0
  }
  return `${text.length}:${hash}`
}

function sanitizeCoverSlide(slide) {
  return slide
}

function sanitizeCoverSvgContent(content, page) {
  return content
}

async function loadPersistedSlideScripts(id) {
  try {
    const result = await slideScriptGet(`/${id}`)
    const data = unwrapPlatformResult(result)
    linkedPptScript.value = data?.script || null
    const pages = Array.isArray(data?.pages) ? data.pages : []
    return new Map(pages.map((page) => [Number(page.pageIndex || page.page_index), page]))
  } catch (_) {
    linkedPptScript.value = null
    return new Map()
  }
}

function mergePersistedSlideScripts(rawSlides, persistedScripts) {
  if (!persistedScripts?.size) return rawSlides
  return rawSlides.map((slide) => {
    const persisted = persistedScripts.get(Number(slide.index))
    if (!persisted || typeof persisted.notes !== 'string') return slide
    const generatedNotes = typeof slide.notes === 'string' ? slide.notes : ''
    const manualEdited = persisted.manualEdited === true || persisted.manual_edited === true
    const persistedNotes = persisted.notes.trim()
    const persistedWeak = !manualEdited && isWeakGeneratedScript(persistedNotes)
    const preferGenerated = shouldPreviewScriptReplacePersisted(generatedNotes, persisted)
    const notes = preferGenerated
      ? generatedNotes.trim()
      : (persistedWeak ? generatedNotes.trim() : (persistedNotes || generatedNotes))
    const document = withSlideSpeakerNotes(slide.document, notes)
    return { ...slide, notes, document, scriptManualEdited: manualEdited }
  })
}

function mergeGeneratedScriptDrafts(rawSlides) {
  return rawSlides.map((slide) => {
    if (slide.scriptManualEdited || looksLikeReadableScript(slide.notes)) return slide
    const notes = buildGeneratedSlideScriptDraft(slide.index)
    if (notes) {
      const document = withSlideSpeakerNotes(slide.document, notes)
      return { ...slide, notes, document }
    }
    if (!String(slide.notes || '').trim() || isWeakGeneratedScript(slide.notes)) {
      const document = withSlideSpeakerNotes(slide.document, '')
      return { ...slide, notes: '', document }
    }
    return slide
  })
}

async function syncAutoGeneratedSlideScripts(id, slideItems, persistedScripts = new Map()) {
  if (!id || id !== jobId.value || selectedDeckType.value !== 'roadshow') return
  const tasks = slideItems
    .map((slide) => persistAutoGeneratedSlideScript(id, slide, persistedScripts))
    .filter(Boolean)
  if (!tasks.length) return
  await Promise.allSettled(tasks)
  await refreshLinkedPptScript(id)
}

function persistAutoGeneratedSlideScript(id, slide, persistedScripts = new Map()) {
  if (!id || id !== jobId.value || !slide || slide.scriptManualEdited) return
  const notes = String(slide.notes || '').trim()
  if (!shouldPersistGeneratedScript(notes) || isWeakGeneratedScript(notes)) return
  const persisted = persistedScripts.get(Number(slide.index))
  const persistedNotes = String(persisted?.notes || '').trim()
  const persistedManual = persisted?.manualEdited === true || persisted?.manual_edited === true
  if (persistedManual) return
  if (persistedNotes && persistedNotes === notes) return
  if (persistedNotes && !shouldPreviewScriptReplacePersisted(notes, persisted)) return
  const key = `${id}:${Number(slide.index || 0)}:${hashString(notes)}`
  if (autoPersistedScriptKeys.has(key)) return
  autoPersistedScriptKeys.add(key)
  const document = withSlideSpeakerNotes(slide.document, notes) || { speakerNotes: notes, title: titleFromRoadshowCard(slide.index) }
  return persistSlideScript(slide, notes, document, 'roadshow-script-skill', false).catch(() => null)
}

function shouldPreviewScriptReplacePersisted(generatedNotes, persisted) {
  const generated = String(generatedNotes || '').trim()
  const persistedNotes = String(persisted?.notes || '').trim()
  if (!generated || isWeakGeneratedScript(generated) || persisted?.manualEdited === true || persisted?.manual_edited === true) return false
  if (!persistedNotes) return true
  if (isWeakGeneratedScript(persistedNotes) && !isWeakGeneratedScript(generated)) return true
  return generated.length > persistedNotes.length + 120 && !isWeakGeneratedScript(generated)
}

async function hydrateSlideScriptsFromRoadshowCards(id) {
  if (!id || id !== jobId.value || selectedDeckType.value !== 'roadshow' || !roadshowCards.value.length || !slides.value.length) return
  const persistedScripts = await loadPersistedSlideScripts(id)
  let changed = false
  const persistTasks = []
  const nextSlides = slides.value.map((slide) => {
    const page = Number(slide.index)
    const persisted = persistedScripts.get(page)
    const persistedNotes = String(persisted?.notes || '').trim()
    const persistedManual = persisted?.manualEdited === true || persisted?.manual_edited === true
    if (persistedNotes) {
      if (!persistedManual && isWeakGeneratedScript(persistedNotes)) {
        changed = changed || Boolean(slide.notes)
        return { ...slide, notes: '', document: withSlideSpeakerNotes(slide.document, ''), scriptManualEdited: false }
      }
      const document = withSlideSpeakerNotes(slide.document, persistedNotes)
      changed = changed || persistedNotes !== String(slide.notes || '') || Boolean(slide.scriptManualEdited) !== persistedManual
      return { ...slide, notes: persistedNotes, document, scriptManualEdited: persistedManual }
    }
    if (slide.scriptManualEdited || looksLikeReadableScript(slide.notes)) return slide
    const notes = buildGeneratedSlideScriptDraft(page)
    if (!notes) return slide
    const document = withSlideSpeakerNotes(slide.document, notes) || { speakerNotes: notes, title: titleFromRoadshowCard(page) }
    const updated = { ...slide, notes, document }
    const persistTask = persistAutoGeneratedSlideScript(id, updated, persistedScripts)
    if (persistTask) persistTasks.push(persistTask)
    changed = true
    return updated
  })
  if (changed) {
    slides.value = nextSlides
    lastPreviewSignature = slidesRevisionKey(nextSlides)
  }
  if (persistTasks.length) {
    await Promise.allSettled(persistTasks)
    await refreshLinkedPptScript(id)
  }
}

async function refreshLinkedPptScript(id) {
  if (!id || id !== jobId.value) return
  try {
    const bundle = unwrapPlatformResult(await slideScriptGet(`/${id}`))
    linkedPptScript.value = bundle?.script || null
  } catch (_) {}
}

function pendingSlideScriptStorageKey(id = jobId.value) {
  return id ? `orep:ppt-script-pending:${id}` : ''
}

function readPendingSlideScripts(id = jobId.value) {
  const key = pendingSlideScriptStorageKey(id)
  if (!key) return {}
  try {
    return JSON.parse(localStorage.getItem(key) || '{}') || {}
  } catch (_) {
    return {}
  }
}

function writePendingSlideScripts(id, records) {
  const key = pendingSlideScriptStorageKey(id)
  if (!key) return
  const values = Object.values(records || {}).filter(Boolean)
  if (!values.length) {
    localStorage.removeItem(key)
    return
  }
  localStorage.setItem(key, JSON.stringify(records))
}

function enqueuePendingSlideScript(slide, notes, document, source, manualEdited) {
  if (!jobId.value || !slide || !notes) return
  const page = Number(slide.index || 0)
  if (!page) return
  const records = readPendingSlideScripts(jobId.value)
  records[String(page)] = {
    slide: {
      index: page,
      name: slide.name || `slide_${page}`,
      content: slide.content || ''
    },
    notes,
    document: document || null,
    source,
    manualEdited: Boolean(manualEdited),
    queuedAt: Date.now()
  }
  writePendingSlideScripts(jobId.value, records)
}

function removePendingSlideScript(id, page) {
  const records = readPendingSlideScripts(id)
  delete records[String(Number(page || 0))]
  writePendingSlideScripts(id, records)
}

async function flushPendingSlideScripts(id = jobId.value) {
  if (!id || id !== jobId.value) return
  const records = readPendingSlideScripts(id)
  const items = Object.values(records).sort((a, b) => Number(a?.slide?.index || 0) - Number(b?.slide?.index || 0))
  if (!items.length) return
  await Promise.allSettled(items.map((item) => persistSlideScript(
    item.slide,
    item.notes,
    item.document,
    item.source || 'roadshow-script-skill',
    Boolean(item.manualEdited),
    { queueOnFail: false }
  )))
  await refreshLinkedPptScript(id)
}

function withSlideSpeakerNotes(document, notes) {
  if (!document || typeof document !== 'object') return document
  return { ...document, speakerNotes: notes }
}

function unwrapPlatformResult(result) {
  if (result && typeof result === 'object' && 'code' in result) {
    if (Number(result.code) !== 200) {
      throw new Error(result.message || '平台接口返回异常')
    }
    return result.data
  }
  return result
}

async function persistSlideScript(slide, notes, document, source = 'ppt-editor', manualEdited = source === 'ppt-editor', options = {}) {
  if (!jobId.value || !slide) return null
  const queueOnFail = options.queueOnFail !== false
  try {
    const result = await slideScriptPut(`/${jobId.value}/pages/${slide.index}`, {
      pageName: slide.name || '',
      pageTitle: resolveSlideTitle(slide, document),
      notes,
      documentJson: document ? JSON.stringify(document) : '',
      source,
      manualEdited
    })
    const page = unwrapPlatformResult(result)
    removePendingSlideScript(jobId.value, slide.index)
    if (!linkedPptScript.value) {
      try {
        const bundle = unwrapPlatformResult(await slideScriptGet(`/${jobId.value}`))
        linkedPptScript.value = bundle?.script || null
      } catch (_) {}
    }
    return page
  } catch (error) {
    if (queueOnFail) {
      enqueuePendingSlideScript(slide, notes, document, source, manualEdited)
    }
    if (isSlideScriptEndpointUnavailable(error)) {
      const message = '讲稿后台同步暂未完成，当前页内容已保存，稍后可再次保存讲稿。'
      appendLog('script', message)
      ElMessage.warning(message)
      return null
    }
    const message = readError(error, '讲稿同步暂不可用')
    appendLog('script', message)
    ElMessage.warning(message)
    return null
  }
}

function resolveSlideTitle(slide, document) {
  if (typeof document?.title === 'string' && document.title.trim()) return document.title.trim()
  const text = String(slide?.content || '')
  const match = text.match(/<text[^>]*>([^<]{2,80})<\/text>/i)
  return match ? match[1].trim() : `第 ${slide?.index || ''} 页`
}

function titleFromRoadshowCard(page) {
  const card = roadshowCards.value.find((item) => Number(item.page) === Number(page))
  return card?.formal_title || card?.title || `第 ${page} 页`
}

function buildGeneratedSlideScriptDraft(page) {
  const cards = roadshowCards.value || []
  const card = cards.find((item) => Number(item.page) === Number(page))
  if (!card) return ''
  const directNotes = [
    card.speaker_notes,
    card.speech_script,
    card.script
  ].map(cleanScriptLine).find(Boolean)
  if (looksLikeSkillGeneratedScript(directNotes)) return sanitizeGeneratedSpeakerScript(directNotes)
  return ''
}

function cleanScriptLine(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\[\[(?:ASSET|FIG):[^\]]+\]\]/gi, '')
    .replace(/^(?:main_script|sub_script|transition|next_slide_bridge|speaker_notes|speech_script|script|speaker_goal|judge_focus)\s*[:：]\s*/i, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function sanitizeGeneratedSpeakerScript(value) {
  const text = polishOralScript(value)
    .replace(/接下来继续汇报目录，把内容落到材料和系统能力上[。！？!?]?/g, '接下来，我们先看本次汇报的整体结构。')
    .replace(/首先[，,]?\s*项目名称[、，,]\s*一句定位语[^。！？!?]*[。！？!?]?/g, '')
    .replace(/项目名称[、，,]\s*一句定位语[^。！？!?]*[。！？!?]?/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return limitScriptLength(text)
}

function looksLikeReadableScript(value) {
  const text = cleanScriptLine(value)
  if (!text) return false
  if (containsScriptMetaText(text)) return false
  if (isLegacyTemplateScript(text)) return false
  const sentenceCount = text.split(/[。！？!?；;\n]+/).filter((item) => item.trim().length > 8).length
  const hasSpeechTone = /各位|评委|老师|我们|接下来|首先|其次|最后|下面|汇报|展示|说明/.test(text)
  const hasRoadshowShape = /系统|项目|功能|数据|结果|现场|价值|能力|管理|温室|农业/.test(text)
  return text.length >= 220 && sentenceCount >= 4 && hasSpeechTone && hasRoadshowShape
}

function looksLikeSkillGeneratedScript(value) {
  const text = cleanScriptLine(value)
  if (!text || containsScriptMetaText(text) || isLegacyTemplateScript(text)) return false
  const sentenceCount = text.split(/[。！？!?；;\n]+/).filter((item) => item.trim().length > 6).length
  const hasSpeechTone = /各位|评委|老师|我们|接下来|首先|其次|最后|下面|汇报|展示|说明|请看|进入|感谢/.test(text)
  const hasRoadshowShape = /系统|项目|功能|数据|结果|现场|价值|能力|管理|温室|农业|研发|方案|问题|背景|政策|市场|演示/.test(text)
  return text.length >= 35 && sentenceCount >= 1 && (hasSpeechTone || hasRoadshowShape)
}

function shouldPersistGeneratedScript(value) {
  const text = cleanScriptLine(value)
  if (!text || containsScriptMetaText(text)) return false
  if (looksLikeSkillGeneratedScript(text)) return true
  if (looksLikeReadableScript(text)) return true
  const sentenceCount = text.split(/[。！？!?；;\n]+/).filter((item) => item.trim().length > 6).length
  const hasSpeechTone = /各位|评委|老师|我们|接下来|首先|其次|最后|下面|汇报|展示|说明|请看|进入/.test(text)
  const hasRoadshowShape = /系统|项目|功能|数据|结果|现场|价值|能力|管理|温室|农业|研发|方案|问题|背景/.test(text)
  return text.length >= 80 && sentenceCount >= 2 && hasSpeechTone && hasRoadshowShape
}

function isWeakGeneratedScript(value) {
  const text = cleanScriptLine(value)
  if (!text) return true
  if (containsScriptMetaText(text)) return true
  if (isLegacyTemplateScript(text)) return true
  if (/也就是说|职业院校技能大赛作品汇报/.test(text)) return true
  if (text.length < 35) return true
  const sentenceCount = text.split(/[。！？!?；;\n]+/).filter((item) => item.trim().length > 6).length
  const hasSpeechTone = /各位|评委|老师|我们|接下来|首先|其次|最后|下面|汇报|展示|说明|请看|进入|感谢/.test(text)
  const hasRoadshowShape = /系统|项目|功能|数据|结果|现场|价值|能力|管理|温室|农业|研发|方案|问题|背景|政策|市场|演示/.test(text)
  return sentenceCount < 1 || (!hasSpeechTone && !hasRoadshowShape)
}

function isLegacyTemplateScript(value) {
  const text = cleanScriptLine(value)
  if (!text) return false
  const patterns = [
    /也就是说/,
    /项目主线继续向前推进/,
    /这里我们重点说明/,
    /接下来[，,]?\s*我们继续汇报/,
    /从评审关注看/,
    /不是孤立功能/,
    /不是为了做一个演示界面/,
    /说明为什么要做；第二是总体方案/,
    /政策支持[、，,]?\s*市场广阔[、，,]?\s*痛点明显/,
    /职业院校技能大赛作品汇报/,
    /让评委老师看到的不是/,
    /把做成的依据讲清楚/
  ]
  const hits = patterns.reduce((count, pattern) => count + (pattern.test(text) ? 1 : 0), 0)
  return hits >= 2 || /首先[，,]\s*国家政策明确支持.*其次[，,]\s*传统.*同时[，,]\s*项目/.test(text)
}

function containsScriptMetaText(value) {
  const text = String(value || '')
  return /speaker_notes|main_script|sub_script|next_slide_bridge|字段|备注|待补充|主视觉|版式|布局|占位|素材引用|一句定位语|继续汇报目录|把内容落到|设计思路|页面分析|可见正文|底部任务|prompt/i.test(text)
    || /(?:本页|这一页|这页|页面).{0,18}(?:核心观点|核心结论|核心信息|证明任务|证明对象|设计思路|可见正文)/.test(text)
    || /(?:核心观点|核心结论|核心信息|证明任务|证明对象)[:：]/.test(text)
}

function stripMetaPhrases(value) {
  return cleanScriptLine(value)
    .replace(/^(?:本页|这一页|这页)?(?:核心观点|核心结论|核心信息|证明任务)(?:是|为)?[:：]?\s*/g, '')
    .replace(/^(?:从)?评委视角(?:看)?[,，：:]?\s*/g, '')
    .replace(/^(?:首先|其次|同时|最后)[，,]?\s*(?:项目名称|一句定位语|主视觉|页面|版式|布局).*$/g, '')
    .replace(/^它的作用是/g, '')
    .replace(/讲解时(?:先)?/g, '')
    .replace(/可以自然提示[:：]?/g, '')
    .trim()
}

function polishOralScript(value) {
  return String(value || '')
    .split(/\n+/)
    .map((paragraph) => paragraph
      .split(/(?<=[。！？!?])/)
      .map(stripMetaPhrases)
      .filter((item) => item && !isScriptMetaOnly(item))
      .join(''))
    .filter(Boolean)
    .join('\n\n')
    .replace(/本页/g, '这部分')
    .replace(/这一页/g, '这部分')
    .replace(/这页/g, '这部分')
    .replace(/页面/g, '内容')
    .replace(/评委视角/g, '各位评委老师')
    .replace(/留下的判断/g, '看到的结果')
    .replace(/如果现场进入/g, '下面进入')
    .replace(/如果评委老师关注/g, '对于')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function firstOralCandidate(items) {
  return items.map(stripMetaPhrases).find((item) => item && !isScriptMetaOnly(item)) || ''
}

function isScriptMetaOnly(value) {
  const text = cleanScriptLine(value)
  if (!text) return true
  if (/^(项目名称|一句定位语|主视觉|页面|版式|布局|字段|备注|素材引用|证明对象)/.test(text)) return true
  if (/项目名称[、，,].*一句定位语/.test(text)) return true
  if (/继续汇报目录|把内容落到|生成器|提示词|口径/.test(text)) return true
  if (/主视觉|页面分析|设计思路|可见正文|字段|素材引用|占位|待补充|证明任务|证明对象/.test(text)) return true
  if (/^(首先|其次|同时|最后)[，,]?\s*(项目名称|一句定位语|主视觉|页面|版式|布局)/.test(text)) return true
  return false
}

function ensureSentence(value) {
  const text = cleanScriptLine(value)
  if (!text) return ''
  return /[。！？!?]$/.test(text) ? text : `${text}。`
}

function limitScriptLength(value, max = 4000) {
  const text = String(value || '').replace(/\n{3,}/g, '\n\n').trim()
  if (text.length <= max) return text
  const sentences = text.split(/(?<=[。！？!?])/)
  let result = ''
  for (const sentence of sentences) {
    if ((result + sentence).length > max) break
    result += sentence
  }
  return (result || text.slice(0, max - 1)).trim()
}

async function loadRoadshowPlan(id) {
  if (!id || selectedDeckType.value !== 'roadshow') return
  try {
    const plan = await apiGet(`/api/ppt/roadshow/plan/${id}`)
    materialDiagnosis.value = plan.material_diagnosis || {}
    storylinePlan.value = plan.storyline_plan || {}
    roadshowCards.value = normalizeClientCards(plan.page_content_cards?.cards || [])
    if (renderFromCardsStatuses.includes(plan.status)) {
      jobStatus.value = plan.status
      jobMessage.value = plan.status === 'generation'
        ? '已进入逐页生成，页面完成后会自动出现'
        : '已确认内容卡片，正在进入设计渲染'
      progress.value = Math.max(Number(progress.value || 0), 0.35)
      startPolling(id)
    }
    if (roadshowCards.value.length) {
      totalSlides.value = Math.max(totalSlides.value || 0, roadshowCards.value.length)
      await hydrateSlideScriptsFromRoadshowCards(id)
    }
  } catch (error) {
    appendLog('content_cards', readError(error, '内容卡片暂不可用'))
  }
}

function normalizeClientCards(cards) {
  return cards.map((card, index) => ({
    ...card,
    page: Number(card.page || index + 1),
    formal_title: card.formal_title || card.title || `第 ${index + 1} 页`,
    core_sentence: card.core_sentence || card.page_core_sentence || '',
    visible_content: card.visible_content || '',
    main_visual: card.main_visual || {},
    required_assets: Array.isArray(card.required_assets) ? card.required_assets : splitCardAssets(card.required_assets || ''),
    quality_flags: Array.isArray(card.quality_flags) ? card.quality_flags : []
  }))
}

function splitCardAssets(value) {
  return String(value || '')
    .split(/[；;,\n]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

async function saveRoadshowCards() {
  if (!jobId.value || !roadshowCards.value.length) return
  savingCards.value = true
  try {
    const result = await apiFetch(`/api/ppt/roadshow/plan/${jobId.value}/cards`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cards: roadshowCards.value })
    })
    roadshowCards.value = normalizeClientCards(result.page_content_cards?.cards || roadshowCards.value)
    ElMessage.success('页面内容卡片已保存')
  } catch (error) {
    ElMessage.error(readError(error, '保存内容卡片失败'))
  } finally {
    savingCards.value = false
  }
}

function enterCardRenderState(message = '已提交内容卡片，正在进入设计渲染') {
  jobStatus.value = 'pending'
  jobMessage.value = message
  errorMessage.value = ''
  progress.value = Math.max(Number(progress.value || 0), 0.35)
  slides.value = []
  slidesCompleted.value = 0
  lastLoggedSlidesCompleted = 0
  lastLoggedProgressKey = ''
  lastPreviewRefreshAt = 0
  renderReadyRefreshAttempts = 0
  lastPreviewSignature = ''
  followGeneratedSlides.value = true
  totalSlides.value = Math.max(Number(totalSlides.value || 0), roadshowCards.value.length)
  connectSocket(jobId.value)
  startPolling(jobId.value)
}

async function confirmCardsAndRender() {
  if (!canConfirmCards.value) return
  renderingFromCards.value = true
  enterCardRenderState('已提交内容卡片，正在进入设计渲染')
  try {
    const result = await apiFetch(`/api/ppt/roadshow/plan/${jobId.value}/confirm-render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cards: roadshowCards.value,
        render_engine: activeRenderEngine.value
      })
    })
    if (renderFromCardsStatuses.includes(result.status)) {
      currentJobRenderEngine.value = activeRenderEngine.value
      jobStatus.value = result.status
      jobMessage.value = result.status === 'generation'
        ? '已进入逐页生成，页面完成后会自动出现'
        : '已确认内容卡片，正在进入设计渲染'
    }
    appendLog('content_cards', `已确认 ${result.cards || roadshowCards.value.length} 页内容卡片，进入设计渲染`)
    await syncStatus(jobId.value)
  } catch (error) {
    const message = readError(error, '确认并渲染失败')
    if (/already running/i.test(message) || message.includes('任务已在运行')) {
      appendLog('content_cards', '任务已进入设计渲染，正在同步当前进度')
      await syncStatus(jobId.value)
      ElMessage.info('任务已进入设计渲染，请等待页面生成')
    } else {
      jobStatus.value = 'waiting_confirmation'
      jobMessage.value = '内容卡片已生成，请确认故事线、页面内容和素材引用后进入设计渲染。'
      ElMessage.error(message)
    }
  } finally {
    renderingFromCards.value = false
  }
}

async function downloadPpt() {
  if (!jobId.value || downloadingPpt.value) return
  downloadingPpt.value = true
  const operation = pptRequestLifecycle.open('download')
  try {
    const token = getUserToken()
    const response = await fetch(downloadUrl.value, {
      method: 'GET',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: operation.signal
    })
    if (!operation.isCurrent()) return
    if (!response.ok) {
      const detail = await readResponseDetail(response, 'PPT 下载失败')
      if (!operation.isCurrent()) return
      throw new Error(detail)
    }
    const blob = await response.blob()
    if (!operation.isCurrent()) return
    const fileName = resolveDownloadFileName(response) || `orep_ppt_${jobId.value}.pptx`
    const objectUrl = URL.createObjectURL(blob)
    if (!operation.isCurrent()) {
      URL.revokeObjectURL(objectUrl)
      return
    }
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(objectUrl)
    ElMessage.success('PPTX 已开始下载')
  } catch (error) {
    if (!operation.isCurrent()) return
    ElMessage.error(readError(error, 'PPT 下载失败'))
  } finally {
    downloadingPpt.value = false
    operation.release()
  }
}

function refreshActiveSlideEditors() {
  const slide = activeSlide.value
  slideNotes.value = slide?.notes || ''
  textItems.value = parseSvgTextItems(slide?.content || '')
}

function parseSvgTextItems(svg) {
  if (!svg) return []
  try {
    const doc = new DOMParser().parseFromString(svg, 'image/svg+xml')
    if (doc.querySelector('parsererror')) return []
    return Array.from(doc.querySelectorAll('text'))
      .map((node, index) => ({
        index,
        text: (node.textContent || '').trim(),
        x: node.getAttribute('x') || '',
        y: node.getAttribute('y') || ''
      }))
      .filter((item) => item.text)
  } catch (_) {
    return []
  }
}

function updateSvgText(textIndex, value) {
  const slide = activeSlide.value
  if (!slide?.content) return
  try {
    const doc = new DOMParser().parseFromString(slide.content, 'image/svg+xml')
    if (doc.querySelector('parsererror')) throw new Error('SVG 解析失败')
    const nodes = Array.from(doc.querySelectorAll('text'))
    const target = nodes[textIndex]
    if (!target) return
    target.textContent = value
    const nextSvg = new XMLSerializer().serializeToString(doc.documentElement)
    upsertSlide({ ...slide, content: nextSvg, notes: slideNotes.value })
    textItems.value = parseSvgTextItems(nextSvg)
  } catch (error) {
    ElMessage.error(readError(error, '文字更新失败'))
  }
}

function runEditorCommand(type) {
  editorCommand.value = { id: ++editorCommandSeq.value, type }
}

function updateEditorState(state) {
  editorState.value = {
    selectedType: state?.selectedType || '',
    autoSave: Boolean(state?.autoSave),
    saveState: state?.saveState || 'idle',
    canEdit: Boolean(state?.canEdit),
    canUndo: Boolean(state?.canUndo),
    canRedo: Boolean(state?.canRedo)
  }
}

async function handleEditorSave(slide, content, document, notes = '') {
  savingSlide.value = true
  try {
    const saved = await apiFetch(`/api/ppt/preview/${jobId.value}/slides/${slide.index}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: sanitizeCoverSvgContent(content, slide.index),
        document: document ? { ...document, speakerNotes: notes } : null,
        notes
      })
    })
    await persistSlideScript(saved, notes, document, 'ppt-editor')
    upsertSlide(saved)
    return saved
  } catch (error) {
    ElMessage.error(readError(error, '保存当前页失败'))
    throw error
  } finally {
    savingSlide.value = false
  }
}

async function saveSlideNotes(slide, notes) {
  if (!canEditSlides.value || !slide) return { scriptSynced: false }
  savingSlide.value = true
  try {
    const document = slide.document ? { ...slide.document, speakerNotes: notes } : null
    const saved = await apiFetch(`/api/ppt/preview/${jobId.value}/slides/${slide.index}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: sanitizeCoverSvgContent(slide.content, slide.index),
        document,
        notes
      })
    })
    const scriptPage = await persistSlideScript(saved, notes, document, 'ppt-editor')
    upsertSlide(saved)
    return { scriptSynced: Boolean(scriptPage) }
  } catch (error) {
    ElMessage.error(readError(error, '保存备注失败'))
    throw error
  } finally {
    savingSlide.value = false
  }
}

async function saveActiveSlide() {
  const slide = activeSlide.value
  if (!canEditSlides.value || !slide) return
  savingSlide.value = true
  try {
    const document = slide.document ? { ...slide.document, speakerNotes: slideNotes.value } : null
    const saved = await apiFetch(`/api/ppt/preview/${jobId.value}/slides/${slide.index}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: sanitizeCoverSvgContent(slide.content, slide.index),
        document,
        notes: slideNotes.value
      })
    })
    await persistSlideScript(saved, slideNotes.value, document, 'ppt-editor')
    upsertSlide(saved)
    ElMessage.success('当前页已保存')
  } catch (error) {
    ElMessage.error(readError(error, '保存当前页失败'))
  } finally {
    savingSlide.value = false
  }
}

async function createBlankSlide() {
  if (!canEditSlides.value) return
  try {
    const created = await apiFetch(`/api/ppt/preview/${jobId.value}/slides`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
    upsertSlide(created)
    activeSlideIndex.value = created.index
    ElMessage.success('已新增空白页')
  } catch (error) {
    ElMessage.error(readError(error, '新增页面失败'))
  }
}

async function deleteActiveSlide() {
  if (!canEditSlides.value || slides.value.length <= 1) return
  await deleteSlideByIndex(activeSlideIndex.value)
}

async function deleteSlideByIndex(slideIndex) {
  if (!canEditSlides.value || slides.value.length <= 1) return
  try {
    const preview = await apiFetch(`/api/ppt/preview/${jobId.value}/slides/${slideIndex}`, {
      method: 'DELETE'
    })
    try {
      await slideScriptDelete(`/${jobId.value}/pages/${slideIndex}`)
    } catch (_) {
      // 讲稿记录删除失败不阻断页面删除；下次保存会以当前页面结构为准。
    }
    slides.value = preview.slides || []
    activeSlideIndex.value = slides.value[0]?.index || 1
    ElMessage.success('页面已删除')
  } catch (error) {
    ElMessage.error(readError(error, '删除页面失败'))
  }
}

async function refreshCurrentPreview() {
  if (!jobId.value) return
  await loadPreviewAndCritic(jobId.value)
}

async function submitFeedbackRefine() {
  if (!canRefine.value) return
  refineSubmitting.value = true
  const currentProvider = selectedProvider.value
  const targetPages = regenScope.value === 'current' ? [activeSlideIndex.value] : []
  try {
    const result = await apiFetch('/api/ppt/refine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: jobId.value,
        feedback: regenFeedback.value.trim(),
        target_pages: targetPages,
        allow_structure_changes: allowStructureChanges.value,
        model_config: {
          provider: currentProvider.provider,
          model: currentProvider.model,
          api_key: '',
          base_url: currentProvider.baseUrl
        },
        options: {
          deck_type: selectedDeckType.value,
          render_engine: activeRenderEngine.value,
          canvas_format: 'ppt169',
          style: selectedDeckType.value === 'roadshow' ? 'roadshow' : 'academic',
          language: language.value,
          detail_level: 'normal',
          icon_library: 'chunk',
          max_critic_attempts: enableVisualCritic.value ? 3 : 1,
          enable_visual_critic: enableVisualCritic.value,
          visual_qa_max_attempts: enableVisualCritic.value ? 1 : 0,
          enable_icon: enableIcon.value,
          enable_icon_rag: enableIcon.value,
          template_id: selectedTemplate.value || null
        }
      })
    })
    const nextJobId = result.job_id
    appendLog('refine', `已创建反馈优化任务 ${nextJobId}`)
    regenFeedback.value = ''
    jobId.value = nextJobId
    currentJobRenderEngine.value = activeRenderEngine.value
    jobStatus.value = 'pending'
    jobMessage.value = '反馈优化任务已入队'
    progress.value = 0
    rememberLastOpenedJob(nextJobId)
    connectSocket(nextJobId)
    startPolling(nextJobId)
    await loadHistory()
    ElMessage.success('已开始重新生成')
  } catch (error) {
    ElMessage.error(readError(error, '提交反馈失败'))
  } finally {
    refineSubmitting.value = false
  }
}

function handleSlideSelect(index) {
  activeSlideIndex.value = index
  followGeneratedSlides.value = false
}

function upsertSlide(slide, options = {}) {
  const safeSlide = sanitizeCoverSlide(slide)
  const normalizedSlide = safeSlide
  const next = [...slides.value]
  const existingIndex = next.findIndex((item) => item.index === normalizedSlide.index)
  if (existingIndex >= 0) next.splice(existingIndex, 1, normalizedSlide)
  else next.push(normalizedSlide)
  slides.value = next.sort((a, b) => a.index - b.index)
  lastPreviewSignature = slidesRevisionKey(slides.value)
  if (options.follow && followGeneratedSlides.value) activeSlideIndex.value = normalizedSlide.index
  else if (!activeSlideIndex.value) activeSlideIndex.value = normalizedSlide.index
}

function logSlideReady(page, total) {
  if (!page || page <= lastLoggedSlidesCompleted) return
  lastLoggedSlidesCompleted = page
  appendLog('generation', total ? `第 ${page}/${total} 页已生成并加入预览` : `第 ${page} 页已生成并加入预览`)
}

function recordProgressLog(status, previousCompleted = 0) {
  const stage = status.stage || status.status || status.type || ''
  const completed = Number(status.slides_completed || 0)
  const total = Number(status.total_slides || totalSlides.value || 0)
  if (stage === 'generation' && completed > Math.max(previousCompleted, lastLoggedSlidesCompleted)) {
    logSlideReady(completed, total)
    return
  }
  const message = cleanPptMessage(status.message || status.status || stage)
  // Collapse heartbeat spam: "仍在生成/修复中，已等待 N 秒" updates in place.
  const throttleKey = `${stage}:${message
    .replace(/已等待\s*\d+\s*秒/g, '已等待')
    .replace(/第\s*\d+\s*次尝试/g, '尝试')
    .replace(/\s+/g, ' ')
    .trim()}:${completed}:${total}`
  if (!message) return
  if (throttleKey === lastLoggedProgressKey && logs.value[0]) {
    logs.value[0].message = message
    return
  }
  lastLoggedProgressKey = throttleKey
  if (['parsing', 'research', 'content_cards', 'waiting_confirmation', 'script', 'strategy', 'generation', 'postprocess', 'export', 'complete', 'error', 'queued', 'cancelling'].includes(stage)) {
    appendLog(stage, message)
  }
}

function appendLog(stage, message) {
  if (!message) return
  if (stage === 'research') lastResearchProgressAt = Date.now()
  logs.value.unshift({ id: ++logId, stage: displayPptStage(stage), message: cleanPptMessage(message) })
  logs.value = logs.value.slice(0, 80)
}

function resetJobState() {
  closeSocket()
  stopPolling()
  stopPass2Heartbeat()
  jobId.value = ''
  currentJobRenderEngine.value = ''
  jobStatus.value = ''
  jobMessage.value = ''
  progress.value = 0
  slidesCompleted.value = 0
  totalSlides.value = 0
  errorMessage.value = ''
  logs.value = []
  slides.value = []
  linkedPptScript.value = null
  lastLoggedProgressKey = ''
  lastLoggedSlidesCompleted = 0
  lastResearchProgressAt = 0
  pass2HeartbeatIndex = 0
  lastPreviewRefreshAt = 0
  renderReadyRefreshAttempts = 0
  lastPreviewSignature = ''
  followGeneratedSlides.value = true
  criticEvents.value = []
  versions.value = []
  materialDiagnosis.value = {}
  storylinePlan.value = {}
  roadshowCards.value = []
  textItems.value = []
  slideNotes.value = ''
  editorCommand.value = null
  editorState.value = {
    selectedType: '',
    autoSave: true,
    saveState: 'idle',
    canEdit: false,
    canUndo: false,
    canRedo: false
  }
  regenFeedback.value = ''
  editingText.value = false
  activeSlideIndex.value = 1
}

function stageClass(stageKey) {
  const currentIndex = stages.findIndex((stage) => stage.key === jobStatus.value)
  const stageIndex = stages.findIndex((stage) => stage.key === stageKey)
  if (jobStatus.value === 'complete') return 'done'
  if (jobStatus.value === 'error') return stageIndex <= currentIndex ? 'warn' : ''
  if (stageIndex < currentIndex) return 'done'
  if (stageIndex === currentIndex) return 'active'
  return ''
}

function resolvePageCount() {
  if (pagePolicy.value === 'competition') return null
  if (pagePolicy.value === 'smoke') return 8
  return null
}

function formatFileSize(size) {
  if (size > 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.round(size / 1024))} KB`
}

function formatTime(timestamp) {
  const value = Number(timestamp || 0)
  if (!value) return '未知时间'
  return new Date(value * 1000).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function apiGet(url, options = {}) {
  return apiFetch(url, { ...options, method: 'GET' })
}

function slideScriptGet(path) {
  return request.get(`/api/slide-script${path}`, { timeout: 0 })
}

function slideScriptPut(path, data) {
  return request.put(`/api/slide-script${path}`, data, { timeout: 0 })
}

function slideScriptDelete(path) {
  return request.delete(`/api/slide-script${path}`, { timeout: 0 })
}

async function apiFetch(url, options = {}) {
  const token = getUserToken()
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  })
  if (!response.ok) {
    let detail = ''
    try {
      const raw = await response.text()
      if (raw) {
        try {
          const data = JSON.parse(raw)
          detail = typeof data.detail === 'string' ? data.detail : data.message || JSON.stringify(data)
        } catch (_) {
          detail = raw
        }
      }
    } catch (_) {
      detail = ''
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  if (response.status === 204) return null
  return response.json()
}

async function readResponseDetail(response, fallback) {
  try {
    const raw = await response.text()
    if (!raw) return fallback
    try {
      const data = JSON.parse(raw)
      if (typeof data.detail === 'string') return data.detail
      return data.message || JSON.stringify(data)
    } catch (_) {
      return raw
    }
  } catch (_) {
    return fallback
  }
}

function resolveDownloadFileName(response) {
  const disposition = response.headers.get('content-disposition') || ''
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].replace(/"/g, ''))
  const asciiMatch = disposition.match(/filename="?([^";]+)"?/i)
  if (asciiMatch?.[1]) return asciiMatch[1]
  return ''
}

function readError(error, fallback) {
  return cleanPptMessage(error?.message || fallback)
}

function isSlideScriptEndpointUnavailable(error) {
  const text = String(error?.message || '')
  return text.includes('/api/slide-script') && (text.includes('"status":404') || text.includes('HTTP 404') || text.includes('Not Found'))
}

function cleanPptMessage(message) {
  const rawText = String(message || '')
  // Prefer Chinese user copy; hide raw English pipeline chatter.
  const lowerRaw = rawText.toLowerCase()
  if (/parsing source materials/i.test(rawText)) return '正在解析资料…'
  if (/^parsed:/i.test(rawText.trim())) return rawText.replace(/^Parsed:\s*/i, '资料解析完成：').replace(/\s*\(layout continuity applied\)/i, '')
  if (/competition material diagnosis/i.test(rawText)) return '正在分析资料完整度与关键事实…'
  if (/competition roadshow analysis/i.test(rawText)) return '正在整理路演结构与材料要点…'
  if (/querying external research/i.test(rawText)) return '正在补充外部参考资料…'
  if (/external research returned no results/i.test(rawText)) return '外部参考资料暂无结果，继续用已有材料生成'
  if (/confirmed page content cards loaded/i.test(rawText)) return '已加载确认后的内容卡片'
  if (/creating design specification/i.test(rawText)) return '正在生成设计规范…'
  if (/reused existing design specification/i.test(rawText)) return '沿用已有设计规范'
  if (/pagecontentcards generated/i.test(rawText)) {
    const m = rawText.match(/(\d+)/)
    return m ? `已生成 ${m[1]} 页内容卡片` : '内容卡片已生成'
  }
  const text = rawText
    .replace(/\bMiMo\b/gi, '智能生成服务')
    .replace(/\btoken[-\s]?plan\b/gi, '生成任务')
    .replace(/roadshow\s+request\s+attempt\s+\d+\s+exceeded\s+\d+s\s+after\s+\d+\s+attempts/gi, '素材策划连接波动，系统已保留当前进度，可从缓存继续生成')
    .replace(/roadshow\s+research\s+request\s+attempt\s+\d+\s+exceeded\s+\d+s/gi, '素材策划连接波动，系统正在重新建立请求并保留当前进度')
    .replace(/request\s+attempt\s+\d+\s+exceeded\s+\d+s/gi, '生成连接波动，系统正在重新建立请求并保留当前进度')
    .replace(/\battempt\s+\d+\s+exceeded\s+\d+s\b/gi, '连接波动，系统正在重新建立请求并保留当前进度')
    .replace(/\s*after\s+\d+\s+attempts\b/gi, '')
    .replace(/Pass\s*\d+\s*\/\s*\d+\s*[—-]\s*/gi, '')
    .replace(/\bmanuscript\b/gi, '页面内容稿')
    .replace(/\borchestrator\b/gi, '生成服务')
    .replace(/\bSVGs?\b/g, 'PPT 页面')
    .replace(/exceeded \d+s/gi, '连接波动')
    .replace(/\btimeout\b|\btimed out\b|请求超时/gi, '连接波动')
    .replace(/避免变成普通项目汇报/g, '强化比赛路演表达')
    .replace(/避免变成资料摘要/g, '强化页面支撑逻辑')
    .replace(/\bfallback\b/gi, '可编辑版本')
    .replace(/资料摘要/g, '资料要点')
  const lower = text.toLowerCase()
  // Drop remaining raw English status lines from the activity log
  if (/^[A-Za-z][A-Za-z0-9 ,.:;()/_-]{8,}$/.test(text.trim()) && !/[一-鿿]/.test(text)) {
    if (lower.includes('research') || lower.includes('parsing') || lower.includes('generat') || lower.includes('enrich') || lower.includes('query') || lower.includes('competition') || lower.includes('external')) {
      return '处理中…'
    }
  }
  if (lower.includes('session not found')) {
    return '上传会话已失效，请重新选择/上传资料后再生成'
  }
  if (
    lower.includes('server restarted while this job was running')
    || lower.includes('server restarted')
    || text.includes('生成服务已重启')
  ) {
    return '生成服务刚才重启，当前任务已中断。请直接再点一次「开始生成 / 重新生成」（资料通常不用重传）。'
  }
  if (text.includes('/api/slide-script') && (text.includes('"status":404') || lower.includes('not found') || lower.includes('http 404'))) {
    return '讲稿后台同步暂未完成，当前页内容已保存在幻灯片备注中，稍后可再次保存讲稿。'
  }
  if (lower.includes('bad gateway') || lower.includes('openresty')) {
    return '智能生成服务连接不稳定。任务工作区已保留，系统会继续监听可用结果。'
  }
  if (lower.includes('request timed out') || lower.includes('timeout') || text.includes('请求超时')) {
    return '智能生成服务连接波动。任务工作区已保留，系统正在继续监听并重新建立请求。'
  }
  if (lower.includes('connection error') || lower.includes('failed to fetch')) {
    return '连接暂时不稳定。任务工作区已保留，系统正在继续监听。'
  }
  return text
}

function displayPptStage(stage) {
  const map = {
    pending: '准备中',
    queued: '排队中',
    running: '生成中',
    parsing: '解析资料',
    research: '素材策划',
    content_cards: '内容卡片',
    waiting_confirmation: '等待确认',
    script: '生成讲稿',
    strategy: '叙事策略',
    generation: '页面生成',
    postprocess: '视觉修整',
    export: '导出文件',
    complete: '完成',
    cancelling: '正在取消',
    cancelled: '已取消',
    error: '异常',
    poll: '状态同步',
    refine: '反馈优化',
    resume: '继续生成',
    materials: '资料准备',
    service: '服务状态',
    history: '历史记录',
    preview: '预览',
    ws: '实时通道'
  }
  return map[String(stage || '')] || cleanPptMessage(stage || '事件')
}
</script>

<style scoped>
.eyebrow {
  margin-bottom: 5px;
  color: #7affb4;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.preview-head p {
  margin: 0;
  color: rgba(240, 241, 250, 0.62);
  line-height: 1.45;
}

.agent-layout {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: none;
  min-height: 0;
  height: 100%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: clamp(320px, 18vw, 420px) minmax(720px, 1fr) clamp(260px, 15vw, 360px);
  gap: 16px;
  align-items: stretch;
}

.agent-panel {
  position: relative;
  border: 1px solid rgba(240, 241, 250, 0.15);
  border-radius: 0;
  background:
    linear-gradient(135deg, rgba(240, 241, 250, 0.04), rgba(122, 255, 180, 0.022) 48%, transparent),
    rgba(7, 9, 12, 0.9);
  box-shadow: inset 0 1px 0 rgba(240, 241, 250, 0.04), 0 20px 70px rgba(0, 0, 0, 0.28);
}

.control-panel,
.log-panel,
.preview-panel {
  min-height: 0;
  padding: 16px;
}

.control-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  padding-bottom: 0;
}

.preview-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-title,
.preview-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 9px;
  border-bottom: 1px solid rgba(240, 241, 250, 0.1);
}

.panel-title span {
  margin: 0;
  color: #f0f1fa;
  font-size: 16px;
  line-height: 1.18;
  font-weight: 900;
}

.preview-head > div {
  min-width: 0;
}

.pipeline-meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.pipeline-meta .eyebrow {
  margin-bottom: 0;
  color: #7affb4;
  font-size: 13px;
}

.pipeline-status {
  color: rgba(240, 241, 250, 0.88);
  font-size: 13px;
  font-weight: 900;
}

.pipeline-meta small {
  min-width: 0;
  overflow: hidden;
  color: rgba(240, 241, 250, 0.5);
  font-size: 12px;
  font-weight: 760;
  text-overflow: ellipsis;
}

.panel-title small,
.muted {
  color: rgba(240, 241, 250, 0.48);
}

.panel-title-actions {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.new-ppt-button {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border: 1px solid rgba(122, 255, 180, 0.46);
  border-radius: 999px;
  background: rgba(122, 255, 180, 0.1);
  color: #7affb4;
  font-size: 12px;
  font-weight: 950;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.new-ppt-button:hover {
  border-color: rgba(122, 255, 180, 0.86);
  background: rgba(122, 255, 180, 0.18);
  color: #f0fff7;
}

.panel-link {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid rgba(240, 241, 250, 0.16);
  border-radius: 999px;
  background: rgba(240, 241, 250, 0.035);
  color: rgba(240, 241, 250, 0.68);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.panel-link:hover {
  border-color: rgba(122, 255, 180, 0.62);
  background: rgba(122, 255, 180, 0.08);
  color: #7affb4;
}

.content-card-panel {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.content-card-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
  border: 1px solid rgba(122, 255, 180, 0.22);
  background: rgba(122, 255, 180, 0.06);
}

.content-card-toolbar strong,
.plan-summary-block b,
.page-card-head span {
  color: #f0f1fa;
  font-weight: 900;
}

.content-card-toolbar span,
.plan-summary-block small,
.storyline-step span,
.page-card-head small {
  display: block;
  margin-top: 4px;
  color: rgba(240, 241, 250, 0.55);
  font-size: 12px;
  line-height: 1.5;
}

.card-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
}

.plan-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.plan-summary-block {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  background: rgba(240, 241, 250, 0.035);
}

.plan-summary-block span {
  display: block;
  margin-top: 6px;
  color: #7affb4;
  font-size: 15px;
  font-weight: 900;
}

.storyline-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.storyline-step {
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  background: rgba(5, 6, 8, 0.42);
}

.storyline-step b {
  color: rgba(240, 241, 250, 0.9);
  font-size: 13px;
}

.content-card-list {
  min-height: 0;
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 12px;
  overflow: auto;
  padding-right: 4px;
}

.page-content-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(240, 241, 250, 0.13);
  background: rgba(240, 241, 250, 0.04);
}

.page-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.page-card-head b {
  padding: 2px 7px;
  border: 1px solid rgba(122, 255, 180, 0.28);
  color: #7affb4;
  font-size: 11px;
}

.page-card-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.page-card-fields label {
  min-width: 0;
  color: rgba(240, 241, 250, 0.6);
  font-size: 12px;
  font-weight: 800;
}

.page-card-fields label :deep(.el-input),
.page-card-fields label :deep(.el-textarea),
.page-card-fields label :deep(.el-select) {
  margin-top: 5px;
}

.wide-field {
  grid-column: 1 / -1;
}

.card-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.card-flags span {
  padding: 2px 7px;
  border: 1px solid rgba(255, 206, 86, 0.28);
  color: rgba(255, 226, 146, 0.9);
  font-size: 11px;
}

.file-drop {
  position: relative;
  min-height: 76px;
  display: grid;
  grid-template-columns: 42px minmax(0, max-content);
  grid-template-rows: min-content min-content;
  grid-template-areas:
    "icon title"
    "icon hint";
  align-items: center;
  align-content: center;
  justify-content: center;
  column-gap: 12px;
  row-gap: 3px;
  padding: 12px 14px;
  border: 1px dashed rgba(122, 255, 180, 0.38);
  border-radius: 0;
  background:
    linear-gradient(135deg, rgba(122, 255, 180, 0.1), rgba(240, 241, 250, 0.035)),
    rgba(240, 241, 250, 0.028);
  color: rgba(240, 241, 250, 0.84);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.file-drop::after {
  content: "+";
  position: absolute;
  top: 12px;
  right: 14px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(122, 255, 180, 0.13);
  color: #7affb4;
  font-size: 15px;
  font-weight: 900;
}

.file-drop:hover {
  border-color: rgba(122, 255, 180, 0.86);
  background:
    linear-gradient(135deg, rgba(122, 255, 180, 0.16), rgba(240, 241, 250, 0.045)),
    rgba(240, 241, 250, 0.04);
}

.file-drop.is-ready {
  border-color: rgba(122, 255, 180, 0.72);
  background: rgba(122, 255, 180, 0.08);
}

.file-drop input {
  display: none;
}

.file-drop .el-icon {
  grid-area: icon;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 0;
  background: rgba(122, 255, 180, 0.1);
  box-shadow: inset 0 0 0 1px rgba(122, 255, 180, 0.22);
  font-size: 22px;
  color: #7affb4;
  justify-self: center;
}

.file-drop strong {
  grid-area: title;
  max-width: 360px;
  min-width: 0;
  overflow-wrap: anywhere;
  overflow: hidden;
  padding-right: 26px;
  font-size: 15px;
  font-weight: 900;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-drop span {
  grid-area: hint;
  max-width: 360px;
  min-width: 0;
  overflow: hidden;
  padding-right: 26px;
  color: rgba(240, 241, 250, 0.58);
  font-size: 12px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.idea-brief-card {
  display: grid;
  gap: 9px;
  margin: 0 0 8px;
  padding: 10px;
  border: 1px solid rgba(122, 255, 180, 0.22);
  border-radius: 0;
  background: linear-gradient(180deg, rgba(122, 255, 180, 0.08), rgba(240, 241, 250, 0.028));
}

.idea-brief-head {
  display: grid;
  gap: 3px;
}

.idea-brief-head strong {
  color: rgba(240, 240, 250, 0.92);
  font-size: 13px;
  font-weight: 900;
}

.idea-brief-head span {
  color: rgba(240, 240, 250, 0.54);
  font-size: 11px;
  line-height: 1.4;
}

.idea-brief-card :deep(.el-textarea__inner) {
  min-height: 74px !important;
  max-height: 74px;
  border-color: rgba(240, 241, 250, 0.16);
  background: rgba(240, 241, 250, 0.035);
  color: #f0f1fa;
  line-height: 1.45;
}

.control-panel.is-idea-mode .prep-mode-button {
  min-height: 42px;
  align-content: center;
  padding: 7px 9px;
}

.control-panel.is-idea-mode .prep-mode-button span {
  display: none;
}

.control-panel.is-idea-mode .idea-brief-card {
  gap: 7px;
  margin-bottom: 7px;
  padding: 9px;
}

.control-panel.is-idea-mode .file-drop {
  min-height: 68px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  padding: 10px 12px;
}

.control-panel.is-idea-mode .file-drop .el-icon {
  flex: 0 0 auto;
}

.control-panel.is-idea-mode .file-drop strong {
  max-width: calc(100% - 120px);
  padding-right: 0;
  line-height: 1;
}

.control-panel.is-idea-mode .file-drop span {
  display: none;
}

.control-panel.is-idea-mode .readiness-card {
  margin-top: 6px;
  padding: 7px 10px;
}

.control-panel.is-idea-mode .readiness-card span {
  display: none;
}

.control-panel.is-idea-mode .material-brief {
  gap: 7px;
  margin-top: 6px;
  padding: 8px;
}

.control-panel.is-idea-mode .brief-head span {
  display: none;
}

.control-panel.is-idea-mode .brief-grid {
  gap: 5px;
}

.control-panel.is-idea-mode .brief-chip {
  min-height: 36px;
  padding: 5px 7px;
}

.control-panel.is-idea-mode .material-brief {
  max-height: none;
}

.form-block {
  display: grid;
  gap: 6px;
  margin-top: 12px;
}

.form-block label {
  color: rgba(240, 241, 250, 0.78);
  font-size: 13px;
  font-weight: 800;
}

.generation-target {
  margin: 0 0 8px;
}

.generation-target :deep(.el-radio-group) {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.generation-target :deep(.el-radio-button__inner) {
  width: 100%;
  border-color: rgba(240, 241, 250, 0.16);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
  color: rgba(240, 241, 250, 0.74);
  font-weight: 900;
}

.generation-target :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: #7affb4;
  background: #7affb4;
  color: #050608;
  box-shadow: none;
}

.target-note {
  color: rgba(240, 241, 250, 0.48);
  font-size: 12px;
  line-height: 1.35;
}

.prep-mode {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
  margin: 0 0 8px;
}

.prep-mode-button {
  width: 100%;
  min-height: 58px;
  display: grid;
  align-content: start;
  gap: 4px;
  padding: 9px 10px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
  color: rgba(240, 241, 250, 0.78);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.prep-mode-button.active {
  border-color: rgba(122, 255, 180, 0.72);
  background: rgba(122, 255, 180, 0.1);
  color: #f0fff8;
}

.prep-mode-button:hover {
  border-color: rgba(122, 255, 180, 0.48);
  background: rgba(122, 255, 180, 0.07);
}

.prep-mode-button strong {
  font-size: 13px;
}

.prep-mode-button span {
  color: rgba(240, 241, 250, 0.5);
  font-size: 11px;
  line-height: 1.35;
}

.readiness-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(122, 255, 180, 0.24);
  border-radius: 0;
  background: rgba(122, 255, 180, 0.07);
}

.readiness-card strong,
.readiness-card span {
  display: block;
}

.readiness-card strong {
  font-size: 13px;
  line-height: 1.35;
}

.readiness-card span {
  margin-top: 2px;
  color: rgba(240, 241, 250, 0.58);
  font-size: 11px;
  line-height: 1.45;
}

.readiness-card b {
  min-width: 58px;
  color: #7affb4;
  font-size: 18px;
  text-align: right;
}

.material-brief {
  display: grid;
  gap: 10px;
  margin-top: 10px;
  padding: 12px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
}

.brief-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.brief-head strong,
.brief-head span {
  display: block;
}

.brief-head span {
  margin-top: 3px;
  color: rgba(240, 241, 250, 0.48);
  font-size: 12px;
}

.brief-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}

.brief-chip {
  min-height: 46px;
  display: grid;
  align-content: center;
  align-items: center;
  gap: 2px;
  padding: 6px 9px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.03);
  color: rgba(240, 241, 250, 0.68);
  cursor: pointer;
}

.brief-chip.done {
  border-color: rgba(122, 255, 180, 0.34);
  background: rgba(122, 255, 180, 0.08);
  color: #d8ffe8;
}

.brief-chip span {
  color: #7affb4;
  font-size: 11px;
  font-weight: 900;
}

.brief-chip b {
  overflow: hidden;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-title {
  display: grid;
  gap: 4px;
  width: 100%;
  line-height: 1.25;
}

.question-body {
  padding: 12px;
}

.question-list {
  display: grid;
  gap: 10px;
}

.compact-field {
  margin-top: 0;
}

.extra-notes {
  margin-top: 12px;
}

.extra-notes :deep(.el-textarea__inner) {
  min-height: 72px !important;
  max-height: 72px;
  line-height: 1.45;
}

.paper-upload-guide {
  display: grid;
  gap: 6px;
  margin-top: 14px;
  padding: 14px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
}

.paper-upload-guide strong {
  color: rgba(240, 240, 250, 0.88);
}

.paper-upload-guide span {
  color: rgba(240, 240, 250, 0.5);
  font-size: 12px;
  line-height: 1.6;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.switch-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.switch-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  min-height: 50px;
  padding: 10px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
}

.switch-row strong,
.switch-row span {
  display: block;
}

.switch-row strong {
  margin-bottom: 4px;
}

.switch-row span {
  color: rgba(240, 241, 250, 0.48);
  font-size: 12px;
}

.action-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin-top: 0;
}

.action-row.has-secondary {
  grid-template-columns: minmax(0, 1fr) 120px;
}

.action-row .el-button {
  min-width: 0;
}

.action-row :deep(.is-generating-action.is-loading) {
  cursor: wait;
  opacity: 0.96;
}

.action-row :deep(.is-generating-action .el-icon.is-loading) {
  animation-duration: 0.72s;
}

.action-dock {
  position: sticky;
  bottom: 0;
  z-index: 3;
  margin: auto -16px -16px;
  padding: 10px 16px 16px;
  border-top: 1px solid rgba(240, 241, 250, 0.1);
  background: linear-gradient(180deg, rgba(7, 9, 12, 0.74), rgba(7, 9, 12, 0.98) 28%);
}

.action-row .el-button + .el-button {
  margin-left: 0;
}

.history-entry {
  width: 100%;
  min-height: 42px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding: 0 14px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
  color: rgba(240, 241, 250, 0.82);
  cursor: pointer;
}

.history-entry span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 900;
}

.download-button {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  padding: 0 16px;
  border: 1px solid #7affb4;
  border-radius: 999px;
  background: #7affb4;
  color: #050608;
  cursor: pointer;
  font-weight: 900;
  font: inherit;
  text-decoration: none;
  white-space: nowrap;
  transition: transform 0.18s ease, background 0.18s ease;
}

.download-button:hover:not(:disabled) {
  background: #e9ecf6;
}

.download-button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.stage-row {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 0;
  height: 30px;
  min-height: 30px;
  margin: 6px 0 8px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  overflow: hidden;
}

.stage-card {
  min-width: 0;
  min-height: 0;
  height: 28px;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 0;
  border-right: 1px solid rgba(240, 241, 250, 0.08);
  border-radius: 0;
  color: rgba(240, 241, 250, 0.46);
  background: rgba(240, 241, 250, 0.028);
  font-size: 12px;
  font-weight: 800;
}

.stage-card span {
  width: 100%;
  min-width: 0;
  padding: 0 4px;
  overflow: hidden;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-card:last-child {
  border-right: 0;
}

.stage-card.active {
  color: #050608;
  background: #7affb4;
}

.stage-card.done {
  color: #d8ffe8;
  background: rgba(122, 255, 180, 0.1);
}

.stage-card.warn {
  color: #fed7aa;
  border-color: rgba(249, 115, 22, 0.45);
  background: rgba(249, 115, 22, 0.12);
}

.preview-panel.is-running .stage-card.active::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(240, 241, 250, 0.45), transparent);
  transform: translateX(-120%);
  animation: pipeline-stage-scan 1.5s cubic-bezier(0.16, 1, 0.3, 1) infinite;
  pointer-events: none;
}

.preview-panel.is-running .stage-card.active span {
  position: relative;
  z-index: 1;
}

.preview-panel :deep(.el-progress) {
  margin-top: 0;
}

.preview-panel :deep(.el-progress-bar__outer) {
  position: relative;
  overflow: hidden;
  height: 8px !important;
}

.preview-panel.is-running :deep(.el-progress-bar__outer)::after {
  content: '';
  position: absolute;
  inset: 0;
  width: 34%;
  background: linear-gradient(90deg, transparent, rgba(122, 255, 180, 0.28), transparent);
  transform: translateX(-120%);
  animation: pipeline-progress-sweep 1.8s cubic-bezier(0.16, 1, 0.3, 1) infinite;
  pointer-events: none;
}

.preview-panel :deep(.ppt-react-workspace-shell) {
  --ppa-speaker-strip-height: 64px;
  flex: 1;
  min-height: 0;
  height: 100%;
}

.preview-panel :deep(.ppa-slide-workspace) {
  min-height: 0;
  height: 100%;
}

.preview-panel :deep(.ppa-slide-workspace-header) {
  min-height: 46px;
}

.preview-panel :deep(.ppa-slide-toolbar) {
  min-height: 40px;
}

.preview-panel :deep(.ppa-speaker-strip) {
  min-height: 0;
  padding: 8px 12px;
}

.preview-panel :deep(.ppa-slide-canvas-area) {
  gap: 8px;
  padding: 10px;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 14px;
  padding: 10px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
}

.toolbar-link {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid rgba(122, 255, 180, 0.58);
  border-radius: 999px;
  background: rgba(122, 255, 180, 0.12);
  color: #d8ffe8;
  font-weight: 800;
  text-decoration: none;
}

.error-box {
  min-height: 30px;
  display: flex;
  align-items: center;
  margin: 0 0 8px;
  padding: 0 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 122, 122, 0.34);
  border-radius: 0;
  background: rgba(93, 14, 18, 0.28);
  color: #ffcaca;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: 0;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slide-workbench {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 16px;
}

.thumbs {
  max-height: 640px;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 10px;
  padding-right: 4px;
}

.thumb-card {
  padding: 8px;
  border: 1px solid rgba(240, 241, 250, 0.14);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
  color: rgba(240, 241, 250, 0.72);
  cursor: pointer;
  text-align: left;
}

.thumb-card.active {
  border-color: #7affb4;
  box-shadow: 0 0 0 2px rgba(122, 255, 180, 0.12);
}

.thumb-card span {
  display: block;
  margin-bottom: 6px;
  font-weight: 900;
}

.thumb-svg,
.svg-stage {
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #f8fafc;
}

.thumb-svg :deep(svg),
.svg-stage :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.svg-stage {
  width: 100%;
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
}

.slide-notes {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 0;
  background: rgba(240, 241, 250, 0.045);
  color: rgba(240, 241, 250, 0.7);
  line-height: 1.7;
}

.slide-notes-input {
  margin-top: 12px;
}

.text-editor-panel {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
}

.mini-title,
.history-head,
.version-item,
.history-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.mini-title {
  margin-bottom: 10px;
}

.mini-title span,
.version-item span,
.history-head span {
  color: rgba(240, 240, 250, 0.5);
  font-size: 12px;
}

.text-edit-list {
  display: grid;
  gap: 10px;
}

.text-edit-item {
  display: grid;
  gap: 6px;
}

.text-edit-item span {
  color: rgba(240, 240, 250, 0.58);
  font-size: 12px;
  font-weight: 800;
}

.empty-preview {
  min-height: 520px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  border: 1px dashed rgba(240, 241, 250, 0.18);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
  text-align: center;
}

.empty-mark {
  width: 74px;
  height: 74px;
  display: grid;
  place-items: center;
  border-radius: 0;
  background: rgba(122, 255, 180, 0.12);
  color: #7affb4;
  font-weight: 900;
}

.empty-preview h3 {
  margin: 0;
}

.empty-preview p {
  max-width: 420px;
  margin: 0;
  color: rgba(240, 240, 250, 0.52);
  line-height: 1.7;
}

.log-list {
  display: grid;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.feedback-panel {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(240, 240, 250, 0.1);
}

.compact-title {
  margin-bottom: 10px;
}

.regen-scope {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  margin-bottom: 10px;
}

.regen-scope :deep(.el-radio-button__inner) {
  width: 100%;
}

.compact-switch {
  min-height: 48px;
  margin-bottom: 8px;
  padding: 9px;
}

.feedback-panel :deep(.el-textarea__inner) {
  min-height: 104px !important;
  max-height: 160px;
  border-radius: var(--ds-textarea-radius, var(--ds-radius-md)) !important;
  line-height: 1.55;
  padding: 12px 14px;
}

.full-button {
  width: 100%;
  margin-top: 10px;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-head {
  margin-bottom: 14px;
}

.history-card {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
  color: #f0f1fa;
  cursor: pointer;
  text-align: left;
}

.history-card.active {
  border-color: rgba(122, 255, 180, 0.62);
  box-shadow: none;
}

.history-card strong,
.history-card span {
  display: block;
}

.history-card strong {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-card span,
.history-card small {
  margin-top: 5px;
  color: rgba(240, 241, 250, 0.54);
}

.history-error {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid rgba(255, 111, 111, 0.34);
  background: rgba(255, 111, 111, 0.08);
  color: #ffd7d7;
}

.history-error span {
  color: rgba(255, 215, 215, 0.72);
  line-height: 1.55;
}

.history-drawer :deep(.el-drawer__body) {
  background: #07090c;
}

.drawer-intro {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid rgba(122, 255, 180, 0.22);
  border-radius: 0;
  background: rgba(122, 255, 180, 0.08);
}

.drawer-intro strong {
  color: #d8ffe8;
}

.drawer-intro span {
  color: rgba(240, 240, 250, 0.62);
  font-size: 12px;
  line-height: 1.55;
}

:global(.questionnaire-drawer.el-drawer) {
  background: #0b1118;
  color: #f0f0fa;
}

:global(.questionnaire-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding: 18px 20px 12px;
  border-bottom: 1px solid rgba(240, 240, 250, 0.1);
  background: #0b1118;
  color: #f0f0fa;
}

:global(.questionnaire-drawer .el-drawer__title) {
  color: #f0f0fa;
  font-size: 20px;
  font-weight: 900;
}

:global(.questionnaire-drawer .el-drawer__close-btn) {
  color: rgba(240, 240, 250, 0.82);
}

:global(.questionnaire-drawer .el-drawer__body) {
  padding: 18px 20px 24px;
  background: #0b1118;
  color: #f0f0fa;
}

:global(.questionnaire-drawer .drawer-intro) {
  border: 1px solid rgba(122, 255, 180, 0.22);
  background: rgba(122, 255, 180, 0.08);
}

:global(.questionnaire-drawer .drawer-intro strong) {
  color: #d8ffe8;
}

:global(.questionnaire-drawer .drawer-intro span) {
  color: rgba(240, 240, 250, 0.62);
}

:global(.questionnaire-drawer .material-basket) {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.03);
}

:global(.questionnaire-drawer .material-basket-head) {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

:global(.questionnaire-drawer .material-basket-head strong),
:global(.questionnaire-drawer .material-basket-head span) {
  display: block;
}

:global(.questionnaire-drawer .material-basket-head strong) {
  color: rgba(240, 240, 250, 0.92);
  font-weight: 900;
}

:global(.questionnaire-drawer .material-basket-head span),
:global(.questionnaire-drawer .material-category-hint),
:global(.questionnaire-drawer .material-empty) {
  color: rgba(240, 240, 250, 0.56);
  font-size: 12px;
  line-height: 1.55;
}

:global(.questionnaire-drawer .basket-upload-button) {
  min-height: 34px;
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  padding: 0 12px;
  border: 1px solid rgba(122, 255, 180, 0.38);
  border-radius: 999px;
  background: rgba(122, 255, 180, 0.12);
  color: #d8ffe8;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

:global(.questionnaire-drawer .basket-upload-button input) {
  display: none;
}

:global(.questionnaire-drawer .material-category-tabs) {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 7px;
}

:global(.questionnaire-drawer .material-category-tab) {
  min-height: 46px;
  display: grid;
  align-content: center;
  gap: 2px;
  padding: 7px 8px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.03);
  color: rgba(240, 240, 250, 0.74);
  cursor: pointer;
  text-align: left;
}

:global(.questionnaire-drawer .material-category-tab.active) {
  border-color: rgba(122, 255, 180, 0.62);
  background: rgba(122, 255, 180, 0.12);
  color: #ecfeff;
}

:global(.questionnaire-drawer .material-category-tab strong) {
  overflow: hidden;
  font-size: 12px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.questionnaire-drawer .material-category-tab span) {
  color: #7affb4;
  font-size: 11px;
  font-weight: 900;
}

:global(.questionnaire-drawer .material-category-hint) {
  margin: -2px 0 0;
}

:global(.questionnaire-drawer .material-file-list) {
  display: grid;
  gap: 6px;
  max-height: 180px;
  overflow: auto;
}

:global(.questionnaire-drawer .material-file-item) {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid rgba(240, 240, 250, 0.1);
  border-radius: 0;
  background: rgba(9, 13, 20, 0.72);
}

:global(.questionnaire-drawer .material-file-item div) {
  min-width: 0;
}

:global(.questionnaire-drawer .material-file-item strong),
:global(.questionnaire-drawer .material-file-item span) {
  display: block;
}

:global(.questionnaire-drawer .material-file-item strong) {
  overflow: hidden;
  color: rgba(240, 240, 250, 0.88);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.questionnaire-drawer .material-file-item span) {
  margin-top: 2px;
  color: rgba(240, 240, 250, 0.5);
  font-size: 11px;
}

:global(.questionnaire-drawer .material-file-item button) {
  border: 0;
  background: transparent;
  color: #fca5a5;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

:global(.questionnaire-drawer .questionnaire-collapse) {
  margin-top: 14px;
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 240, 250, 0.03);
  overflow: hidden;
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__header) {
  min-height: 58px;
  padding: 0 12px;
  border-bottom-color: rgba(240, 240, 250, 0.08);
  background: rgba(240, 240, 250, 0.02);
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__wrap) {
  border-bottom-color: rgba(240, 240, 250, 0.08);
  background: transparent;
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__content) {
  padding: 0;
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__arrow) {
  color: rgba(240, 240, 250, 0.62);
}

:global(.questionnaire-drawer .question-title span) {
  color: rgba(240, 240, 250, 0.94);
  font-size: 15px;
  font-weight: 900;
}

:global(.questionnaire-drawer .question-title small) {
  color: rgba(240, 240, 250, 0.52);
  line-height: 1.5;
}

:global(.questionnaire-drawer .form-block label) {
  color: rgba(240, 240, 250, 0.78);
}

:global(.questionnaire-drawer .el-input__wrapper),
:global(.questionnaire-drawer .el-textarea__inner) {
  border-color: rgba(240, 240, 250, 0.16);
  background: rgba(240, 241, 250, 0.035);
  box-shadow: 0 0 0 1px rgba(240, 240, 250, 0.18) inset;
}

:global(.questionnaire-drawer .el-input__inner),
:global(.questionnaire-drawer .el-textarea__inner) {
  color: #f0f1fa;
}

.log-item {
  padding: 7px 9px;
  border: 1px solid rgba(240, 241, 250, 0.1);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.028);
}

.log-item b {
  display: block;
  margin-bottom: 5px;
  color: #7affb4;
  font-size: 11px;
  line-height: 1.2;
  text-transform: uppercase;
}

.log-item p {
  margin: 0;
  color: rgba(240, 241, 250, 0.68);
  font-size: 12px;
  font-weight: 650;
  line-height: 1.45;
  word-break: break-word;
}

.ppt-agent-page :deep(.el-button) {
  border-color: rgba(240, 241, 250, 0.18);
  border-radius: 999px;
  background: rgba(240, 241, 250, 0.035);
  color: rgba(240, 241, 250, 0.82);
  font-weight: 900;
  --el-button-text-color: rgba(240, 241, 250, 0.82);
  --el-button-hover-text-color: #050608;
  --el-button-hover-bg-color: #e9ecf6;
  --el-button-hover-border-color: #e9ecf6;
  --el-button-active-text-color: #050608;
  --el-button-active-bg-color: #d9dde8;
  --el-button-active-border-color: #d9dde8;
}

.ppt-agent-page :deep(.el-button:hover),
.ppt-agent-page :deep(.el-button:focus),
.ppt-agent-page :deep(.el-button:focus-visible) {
  border-color: #e9ecf6 !important;
  background: #e9ecf6 !important;
  color: #050608 !important;
}

.ppt-agent-page :deep(.el-button:hover .el-icon),
.ppt-agent-page :deep(.el-button:hover span),
.ppt-agent-page :deep(.el-button:focus .el-icon),
.ppt-agent-page :deep(.el-button:focus span),
.ppt-agent-page :deep(.el-button:focus-visible .el-icon),
.ppt-agent-page :deep(.el-button:focus-visible span) {
  color: #050608 !important;
}

.ppt-agent-page :deep(.el-button--primary) {
  border-color: #e9ecf6;
  background: #e9ecf6;
  color: #050608;
  --el-button-text-color: #050608;
  --el-button-hover-text-color: #050608;
}

.ppt-agent-page :deep(.el-button--danger.is-plain),
.ppt-agent-page :deep(.el-button--danger) {
  border-color: rgba(255, 122, 122, 0.42);
  background: rgba(255, 122, 122, 0.1);
  color: #ffcaca;
  --el-button-text-color: #ffcaca;
  --el-button-hover-text-color: #050608;
  --el-button-hover-bg-color: #ffcaca;
  --el-button-hover-border-color: #ffcaca;
}

.ppt-agent-page :deep(.el-button--warning) {
  border-color: rgba(255, 211, 138, 0.48);
  background: rgba(255, 211, 138, 0.1);
  color: #ffd38a;
  --el-button-text-color: #ffd38a;
  --el-button-hover-text-color: #050608;
  --el-button-hover-bg-color: #ffd38a;
  --el-button-hover-border-color: #ffd38a;
}

.ppt-agent-page :deep(.el-tag) {
  border-color: rgba(122, 255, 180, 0.38);
  border-radius: 999px;
  background: rgba(122, 255, 180, 0.1);
  color: #7affb4;
  font-weight: 900;
}

.ppt-agent-page :deep(.el-input__wrapper),
.ppt-agent-page :deep(.el-textarea__inner) {
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
  box-shadow: 0 0 0 1px rgba(240, 241, 250, 0.14) inset;
}

.ppt-agent-page :deep(.el-input__wrapper.is-focus),
.ppt-agent-page :deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px rgba(122, 255, 180, 0.58) inset, 0 0 0 3px rgba(122, 255, 180, 0.08);
}

.ppt-agent-page :deep(.el-input__inner),
.ppt-agent-page :deep(.el-textarea__inner) {
  color: #f0f1fa;
}

.ppt-agent-page :deep(.el-input__inner::placeholder),
.ppt-agent-page :deep(.el-textarea__inner::placeholder) {
  color: rgba(240, 241, 250, 0.38);
}

.ppt-agent-page :deep(.el-radio-button__inner) {
  border-color: rgba(240, 241, 250, 0.16);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.03);
  color: rgba(240, 241, 250, 0.72);
  font-weight: 900;
}

.ppt-agent-page :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: #7affb4;
  background: #7affb4;
  color: #050608;
  box-shadow: none;
}

.ppt-agent-page :deep(.el-switch.is-checked .el-switch__core) {
  border-color: #7affb4;
  background: #7affb4;
}

.ppt-agent-page :deep(.el-progress-bar__outer) {
  border-radius: 0;
  background: rgba(240, 241, 250, 0.12);
}

.ppt-agent-page :deep(.el-progress-bar__inner) {
  border-radius: 0;
  background: linear-gradient(90deg, #7affb4, #e9ecf6);
}

.ppt-agent-page :deep(.el-progress__text) {
  color: rgba(240, 241, 250, 0.8);
  font-weight: 900;
}

@keyframes pipeline-stage-scan {
  0% {
    transform: translateX(-120%);
  }

  100% {
    transform: translateX(120%);
  }
}

@keyframes pipeline-progress-sweep {
  0% {
    transform: translateX(-120%);
  }

  100% {
    transform: translateX(320%);
  }
}

.preview-panel :deep(.ppt-react-workspace-shell),
.preview-panel :deep(.ppa-slide-workspace),
.preview-panel :deep(.ppa-slide-workspace-header),
.preview-panel :deep(.ppa-slide-toolbar),
.preview-panel :deep(.ppa-speaker-strip),
.preview-panel :deep(.ppa-slide-canvas-area) {
  border-color: var(--ds-line) !important;
  background-color: var(--ds-surface-solid) !important;
  color: var(--ds-ink-2);
}

.preview-panel :deep(.ppa-slide-toolbar button) {
  border-radius: 999px;
}

:global(.history-drawer.el-drawer) {
  background: #07090c;
  color: #f0f1fa;
}

:global(.history-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding: 18px 20px 12px;
  border-bottom: 1px solid rgba(240, 241, 250, 0.1);
  background: #07090c;
  color: #f0f1fa;
}

:global(.history-drawer .el-drawer__title) {
  color: #f0f1fa;
  font-size: 18px;
  font-weight: 900;
}

:global(.history-drawer .el-drawer__body) {
  background:
    linear-gradient(rgba(240, 241, 250, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240, 241, 250, 0.035) 1px, transparent 1px),
    #07090c;
  background-size: 64px 64px;
  color: #f0f1fa;
}

:global(.history-drawer .history-head span) {
  color: rgba(240, 241, 250, 0.54);
}

:global(.history-drawer .history-card) {
  border: 1px solid rgba(240, 241, 250, 0.12);
  border-radius: 0;
  background: rgba(240, 241, 250, 0.035);
  color: #f0f1fa;
}

:global(.history-drawer .history-card.active) {
  border-color: rgba(122, 255, 180, 0.62);
  background: rgba(122, 255, 180, 0.08);
  box-shadow: none;
}

:global(.history-drawer .history-card span),
:global(.history-drawer .history-card small) {
  color: rgba(240, 241, 250, 0.54);
}

@media (max-width: 1280px) {
  .agent-layout {
    grid-template-columns: 340px 1fr;
  }

  .prep-mode {
    grid-template-columns: 1fr;
  }

  .log-panel {
    grid-column: 1 / -1;
  }
}

@media (max-height: 940px) and (min-width: 1281px) {
  .preview-head p {
    margin-top: 4px;
    line-height: 1.45;
  }

  .control-panel,
  .log-panel,
  .preview-panel {
    padding: 12px;
  }

  .panel-title {
    margin-bottom: 7px;
  }

  .form-block label {
    font-size: 12px;
  }

  .target-note,
  .prep-mode-button span {
    display: none;
  }

  .prep-mode-button {
    min-height: 38px;
    align-content: center;
  }

  .file-drop {
    min-height: 64px;
    padding: 8px 10px;
  }

  .file-drop strong {
    max-width: 280px;
  }

  .file-drop .el-icon {
    font-size: 20px;
  }

  .readiness-card,
  .material-brief {
    margin-top: 6px;
  }

  .readiness-card span,
  .brief-head span {
    display: none;
  }

  .brief-grid {
    gap: 5px;
  }

  .brief-chip {
    min-height: 28px;
  }

  .action-dock {
    margin-right: -12px;
    margin-bottom: -12px;
    margin-left: -12px;
    padding: 8px 12px 12px;
  }

  .stage-card {
    min-height: 0;
    height: 28px;
    font-size: 12px;
  }

  .stage-row {
    margin: 6px 0 8px;
  }

  .feedback-panel :deep(.el-textarea__inner) {
    min-height: 82px !important;
    max-height: 82px;
  }

}

@media (max-height: 820px) and (min-width: 1281px) {
  .file-drop {
    min-height: 48px;
  }

  .file-drop .el-icon {
    width: 30px;
    height: 30px;
  }

  .file-drop span {
    display: none;
  }

  .readiness-card {
    padding-top: 6px;
    padding-bottom: 6px;
  }

  .material-brief {
    padding-top: 8px;
    padding-bottom: 8px;
  }

}

@media (max-width: 900px) {
  .agent-layout,
  .slide-workbench,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .control-panel {
    position: static;
    max-height: none;
  }

  .action-dock {
    position: sticky;
    margin-right: -12px;
    margin-bottom: -12px;
    margin-left: -12px;
  }
}

.eyebrow,
.pipeline-meta .eyebrow {
  color: var(--ds-orange-700);
  font-family: var(--ds-font-sans);
  font-size: var(--ds-text-label);
  font-weight: var(--ds-weight-bold);
  letter-spacing: 0;
  text-transform: none;
}

.preview-head p {
  color: var(--ds-muted);
  font-family: var(--ds-font-sans);
}

.drawer-close:focus-visible,
.new-ppt-button:focus-visible,
.panel-link:focus-visible,
.output-type-card:focus-visible,
.prep-mode-button:focus-visible,
.brief-chip:focus-visible,
.download-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.agent-layout {
  grid-template-columns: minmax(0, 1fr) clamp(270px, 18vw, 320px);
  gap: var(--ds-space-4);
}

.creation-landing,
.creation-setup-shell {
  position: relative;
  z-index: 1;
  min-height: 0;
}

.creation-landing {
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--ds-card-border);
  border-radius: 22px;
  background: var(--ds-surface-solid);
  box-shadow: 0 18px 50px rgba(26, 30, 42, 0.06);
}

.creation-landing__content {
  width: min(100%, 980px);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: clamp(36px, 6vh, 72px) var(--ds-space-6);
  text-align: center;
  animation: creation-content-in 420ms var(--ds-motion-ease-out) both;
}

.creation-file-mark {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  margin-bottom: var(--ds-space-4);
  border: 1px solid var(--ds-line-strong);
  border-radius: 22px;
  background: var(--ds-surface-subtle);
  color: var(--ds-ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.creation-file-mark svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

.creation-eyebrow {
  color: var(--ds-muted);
  font-size: var(--ds-text-body);
  font-weight: var(--ds-weight-medium);
}

.creation-landing h2 {
  margin: var(--ds-space-3) 0 0;
  color: var(--ds-ink);
  font-size: clamp(34px, 3.2vw, 50px);
  line-height: 1.12;
  font-weight: var(--ds-weight-bold);
  letter-spacing: -0.035em;
}

.creation-landing__content > p {
  max-width: 720px;
  margin: var(--ds-space-4) 0 0;
  color: var(--ds-muted);
  font-size: 17px;
  line-height: 1.7;
}

.creation-steps {
  width: min(100%, 850px);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--ds-space-3);
  margin-top: clamp(30px, 4vh, 48px);
}

.creation-step {
  min-height: 112px;
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-4);
  padding: 22px;
  border: 1px solid var(--ds-line);
  border-radius: 18px;
  background: var(--ds-surface-subtle);
  text-align: left;
  transition:
    transform var(--ds-motion-duration-standard) var(--ds-motion-ease-out),
    border-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.creation-step:hover {
  border-color: var(--ds-orange-200);
  box-shadow: 0 12px 28px rgba(211, 59, 20, 0.08);
}

.creation-step > span {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--ds-ink);
  color: #fff;
  font-size: 16px;
  font-weight: var(--ds-weight-bold);
}

.creation-step strong,
.creation-step small {
  display: block;
}

.creation-step strong {
  color: var(--ds-ink);
  font-size: 18px;
  line-height: 1.4;
}

.creation-step small {
  margin-top: 6px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.55;
}

.creation-start-button {
  min-height: 50px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: clamp(28px, 4vh, 44px);
  padding: 0 26px;
  border: 1px solid var(--ds-btn-primary-bg);
  border-radius: 14px;
  background: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
  font: inherit;
  font-size: 16px;
  font-weight: var(--ds-weight-bold);
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(211, 59, 20, 0.18);
  transition:
    transform var(--ds-motion-duration-standard) var(--ds-motion-ease-out),
    background-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.creation-start-button:hover {
  background: var(--ds-btn-primary-bg-hover);
  box-shadow: 0 14px 28px rgba(211, 59, 20, 0.24);
}

.creation-start-button span {
  font-size: 19px;
  transition: transform var(--ds-motion-duration-standard) var(--ds-motion-ease-out);
}

.creation-start-button:hover span {
  transform: translateX(3px);
}

.creation-start-button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.creation-setup-shell {
  overflow: hidden;
}

.creation-setup-panel {
  width: min(100%, 1120px);
  height: 100%;
  margin: 0 auto;
  padding: 0 clamp(24px, 4vw, 56px) var(--ds-space-6);
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--ds-surface-solid);
  animation: creation-content-in 360ms var(--ds-motion-ease-out) both;
}

.creation-setup-panel > .form-block,
.creation-setup-panel > .prep-mode,
.creation-setup-panel > .idea-brief-card,
.creation-setup-panel > .file-drop,
.creation-setup-panel > .readiness-card,
.creation-setup-panel > .material-brief,
.creation-setup-panel > .paper-upload-guide,
.creation-setup-panel > .creation-options-grid,
.creation-setup-panel > .action-dock {
  width: min(100%, 880px);
  margin-right: auto;
  margin-left: auto;
}

.creation-setup-panel > .panel-title {
  width: min(100%, 880px);
  margin-right: auto;
  margin-left: auto;
}

.creation-setup-panel > .action-dock {
  position: static;
  margin-top: var(--ds-space-6);
  margin-bottom: 0;
  padding: var(--ds-space-4) 0 0;
  background: transparent;
}

.creation-options-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-4);
}

.creation-options-grid .form-block {
  min-width: 0;
  margin: 0;
  padding: var(--ds-space-4);
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-subtle);
}

.creation-options-grid .el-select {
  width: 100%;
}

@keyframes creation-content-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.agent-panel {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.preview-panel,
.log-panel {
  padding: var(--ds-space-4);
}

.panel-title,
.preview-head {
  border-bottom-color: var(--ds-line);
}

.panel-title span,
.content-card-toolbar strong,
.plan-summary-block b,
.page-card-head span,
.pipeline-status {
  color: var(--ds-ink);
  font-family: var(--ds-font-sans);
  font-weight: var(--ds-weight-bold);
}

.panel-title small,
.muted,
.pipeline-meta small,
.content-card-toolbar span,
.plan-summary-block small,
.storyline-step span,
.page-card-head small {
  color: var(--ds-muted);
}

.material-drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: 2200;
  display: flex;
  align-items: stretch;
  background: rgba(18, 20, 26, 0.28);
}

.material-drawer {
  width: min(520px, calc(100vw - 32px));
  height: 100%;
  padding: 0 var(--ds-space-5);
  overflow-x: hidden;
  overflow-y: auto;
  border: 0;
  border-right: 1px solid var(--ds-line);
  border-radius: 0;
  background: var(--ds-surface-solid);
  box-shadow: var(--ds-shadow-stage);
}

.material-drawer-head {
  position: sticky;
  top: 0;
  z-index: 4;
  min-height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
  margin: 0 calc(var(--ds-space-5) * -1) var(--ds-space-4);
  padding: 0 var(--ds-space-5);
  border-bottom: 1px solid var(--ds-line);
  background: var(--ds-surface-solid);
}

.material-drawer-head span,
.material-drawer-head small {
  display: block;
}

.material-drawer-head span {
  color: var(--ds-ink);
  font-size: 18px;
  font-weight: var(--ds-weight-bold);
}

.material-drawer-head small {
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.drawer-close {
  width: var(--ds-btn-height-icon);
  height: var(--ds-btn-height-icon);
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: 50%;
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-ink-2);
  font: inherit;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.material-drawer-enter-active,
.material-drawer-leave-active {
  transition: opacity var(--ds-motion-duration-standard) var(--ds-motion-ease-out);
}

.material-drawer-enter-active .material-drawer,
.material-drawer-leave-active .material-drawer {
  transition: transform var(--ds-motion-duration-page) var(--ds-motion-ease-out);
}

.material-drawer-enter-from,
.material-drawer-leave-to {
  opacity: 0;
}

.material-drawer-enter-from .material-drawer,
.material-drawer-leave-to .material-drawer {
  transform: translateX(-24px);
}

.new-ppt-button,
.panel-link {
  min-height: var(--ds-btn-height-sm);
  border-color: var(--ds-btn-secondary-border);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
  font-family: var(--ds-font-sans);
  font-weight: var(--ds-weight-bold);
  transform: none;
}

.new-ppt-button:hover,
.panel-link:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-orange-50);
  color: var(--ds-orange-800);
  transform: none;
}

.output-type-block {
  gap: var(--ds-space-2);
  margin: var(--ds-space-3) 0 var(--ds-space-3);
  padding-top: var(--ds-space-3);
  border-top: 1px solid var(--ds-line);
}

.output-type-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-3);
}

.output-type-heading label {
  color: var(--ds-ink);
  font-size: 13px;
  font-weight: var(--ds-weight-bold);
}

.output-type-heading span {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.output-type-options {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--ds-space-2);
}

.output-type-card {
  width: 100%;
  min-width: 0;
  min-height: 68px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 22px;
  align-items: center;
  gap: var(--ds-space-3);
  padding: 11px 13px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-canvas);
  color: var(--ds-ink-2);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color var(--ds-control-transition),
    background-color var(--ds-control-transition),
    box-shadow var(--ds-control-transition);
}

.output-type-card:hover:not(:disabled) {
  border-color: var(--ds-orange-300);
  background: var(--ds-orange-50);
}

.output-type-card.active {
  border-color: var(--ds-orange-400);
  background: var(--ds-orange-50);
  box-shadow: inset 0 0 0 1px rgba(196, 58, 18, 0.05);
}

.output-type-card:disabled {
  cursor: not-allowed;
  opacity: 0.64;
}

.output-type-card.active:disabled {
  opacity: 0.84;
}

.output-type-code {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: var(--ds-radius-sm);
  background: var(--ds-surface-solid);
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: var(--ds-weight-bold);
  letter-spacing: 0.04em;
  box-shadow: inset 0 0 0 1px var(--ds-line);
}

.output-type-card.active .output-type-code {
  background: var(--ds-orange-100);
  color: var(--ds-orange-800);
  box-shadow: inset 0 0 0 1px var(--ds-orange-200);
}

.output-type-copy,
.output-type-copy strong,
.output-type-copy small {
  display: block;
}

.output-type-copy strong {
  color: var(--ds-ink);
  font-size: 14px;
  font-weight: var(--ds-weight-bold);
  line-height: 1.3;
}

.output-type-copy small {
  margin-top: 3px;
  overflow: hidden;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.output-type-check {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border: 1px solid var(--ds-line-strong);
  border-radius: 50%;
  background: var(--ds-surface-solid);
  color: var(--ds-orange-700);
  font-size: 12px;
  font-weight: var(--ds-weight-bold);
  line-height: 1;
}

.output-type-card.active .output-type-check {
  border-color: var(--ds-orange-700);
  background: var(--ds-orange-700);
  color: var(--ds-surface-solid);
}

.output-type-note {
  margin-top: 1px;
  padding-left: 55px;
  font-size: 11px;
}

.file-drop,
.idea-brief-card,
.prep-mode-button,
.readiness-card,
.material-brief,
.brief-chip,
.paper-upload-guide,
.switch-row {
  border-color: var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
  color: var(--ds-ink-2);
  box-shadow: none;
  transform: none;
}

.file-drop {
  border-style: dashed;
  border-color: var(--ds-orange-300);
  background: var(--ds-orange-50);
}

.file-drop:hover,
.file-drop.is-ready {
  border-color: var(--ds-orange-600);
  background: var(--ds-orange-100);
  transform: none;
}

.file-drop::after,
.file-drop .el-icon {
  color: var(--ds-orange-700);
  background: var(--ds-orange-100);
  box-shadow: inset 0 0 0 1px var(--ds-orange-200);
}

.file-drop strong,
.idea-brief-head strong,
.readiness-card strong,
.brief-head strong,
.paper-upload-guide strong,
.switch-row strong {
  color: var(--ds-ink);
}

.file-drop span,
.idea-brief-head span,
.target-note,
.prep-mode-button span,
.readiness-card span,
.brief-head span,
.paper-upload-guide span,
.switch-row span {
  color: var(--ds-muted);
}

.prep-mode-button:hover,
.prep-mode-button.active,
.brief-chip.done {
  border-color: var(--ds-orange-300);
  background: var(--ds-orange-50);
  color: var(--ds-orange-900);
  transform: none;
}

.brief-chip span,
.readiness-card b {
  color: var(--ds-orange-700);
}

.action-dock {
  border-top-color: var(--ds-line);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.76), var(--ds-surface-solid) 28%);
}

.download-button {
  min-height: var(--ds-btn-height);
  border-color: var(--ds-btn-primary-bg);
  background: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
  font-family: var(--ds-font-sans);
  font-weight: var(--ds-weight-bold);
  transform: none;
}

.download-button:hover:not(:disabled) {
  border-color: var(--ds-btn-primary-bg-hover);
  background: var(--ds-btn-primary-bg-hover);
  color: var(--ds-btn-primary-fg);
  transform: none;
}

.stage-row {
  height: 34px;
  min-height: 34px;
  border-color: var(--ds-line);
  border-radius: var(--ds-radius-sm);
}

.stage-card {
  height: 32px;
  border-right-color: var(--ds-line);
  background: var(--ds-canvas);
  color: var(--ds-muted);
  font-family: var(--ds-font-sans);
}

.stage-card.active {
  background: var(--ds-orange-700);
  color: var(--ds-btn-primary-fg);
}

.stage-card.done {
  background: var(--ds-green-soft);
  color: var(--ds-green);
}

.stage-card.warn {
  border-color: var(--ds-status-warning-border);
  background: var(--ds-amber-soft);
  color: var(--ds-amber);
}

.content-card-toolbar,
.plan-summary-block,
.storyline-step,
.page-content-card,
.editor-toolbar,
.text-editor-panel,
.slide-notes,
.log-item {
  border-color: var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
  color: var(--ds-ink-2);
}

.content-card-toolbar,
.readiness-card,
.drawer-intro {
  border-color: var(--ds-orange-200);
  background: var(--ds-orange-50);
}

.plan-summary-block span,
.page-card-head b,
.log-item b {
  color: var(--ds-orange-700);
}

.page-card-head b {
  border-color: var(--ds-orange-200);
  background: var(--ds-orange-50);
}

.log-item p {
  color: var(--ds-muted);
}

.feedback-panel {
  border-bottom-color: var(--ds-line);
}

.error-box {
  border-color: var(--ds-status-danger-border);
  border-radius: var(--ds-radius-sm);
  background: var(--ds-red-soft);
  color: var(--ds-red);
}

.ppt-agent-page :deep(.el-button) {
  border-color: var(--ds-btn-secondary-border);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-btn-secondary-fg);
  font-family: var(--ds-font-sans);
  font-weight: var(--ds-weight-bold);
  --el-button-text-color: var(--ds-btn-secondary-fg);
  --el-button-hover-text-color: var(--ds-orange-800);
  --el-button-hover-bg-color: var(--ds-orange-50);
  --el-button-hover-border-color: var(--ds-btn-secondary-border-hover);
  --el-button-active-text-color: var(--ds-orange-900);
  --el-button-active-bg-color: var(--ds-orange-100);
  --el-button-active-border-color: var(--ds-orange-400);
}

.ppt-agent-page :deep(.el-button:hover),
.ppt-agent-page :deep(.el-button:focus) {
  border-color: var(--ds-btn-secondary-border-hover) !important;
  background: var(--ds-orange-50) !important;
  color: var(--ds-orange-800) !important;
}

.ppt-agent-page :deep(.el-button--primary) {
  border-color: var(--ds-btn-primary-bg);
  background: var(--ds-btn-primary-bg);
  color: var(--ds-btn-primary-fg);
  --el-button-text-color: var(--ds-btn-primary-fg);
  --el-button-hover-text-color: var(--ds-btn-primary-fg);
}

.ppt-agent-page :deep(.el-button--primary:hover),
.ppt-agent-page :deep(.el-button--primary:focus) {
  border-color: var(--ds-btn-primary-bg-hover) !important;
  background: var(--ds-btn-primary-bg-hover) !important;
  color: var(--ds-btn-primary-fg) !important;
}

.ppt-agent-page :deep(.el-input__wrapper),
.ppt-agent-page :deep(.el-select__wrapper) {
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  background: var(--ds-input-bg);
  box-shadow: none;
}

.ppt-agent-page :deep(.el-textarea__inner) {
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-textarea-radius, var(--ds-radius-md));
  background: var(--ds-input-bg);
  box-shadow: none;
}

.ppt-agent-page :deep(.el-input__wrapper.is-focus),
.ppt-agent-page :deep(.el-textarea__inner:focus),
.ppt-agent-page :deep(.el-select__wrapper.is-focused) {
  border-color: var(--ds-orange-action);
  box-shadow: var(--ds-btn-focus-ring);
}

.ppt-agent-page :deep(.el-input__inner),
.ppt-agent-page :deep(.el-textarea__inner),
.ppt-agent-page :deep(.el-select__selected-item) {
  color: var(--ds-ink);
}

.ppt-agent-page :deep(.el-input__inner::placeholder),
.ppt-agent-page :deep(.el-textarea__inner::placeholder) {
  color: var(--ds-faint);
}

.ppt-agent-page :deep(.el-radio-button__inner),
.generation-target :deep(.el-radio-button__inner) {
  border-color: var(--ds-line);
  border-radius: 0;
  background: var(--ds-surface-solid);
  color: var(--ds-muted);
}

.ppt-agent-page :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-radius: var(--ds-radius-pill) 0 0 var(--ds-radius-pill);
}

.ppt-agent-page :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 0 var(--ds-radius-pill) var(--ds-radius-pill) 0;
}

.ppt-agent-page :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner),
.generation-target :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  border-color: var(--ds-orange-700);
  background: var(--ds-orange-700);
  color: var(--ds-btn-primary-fg);
}

.ppt-agent-page :deep(.el-switch.is-checked .el-switch__core),
.ppt-agent-page :deep(.el-progress-bar__inner) {
  border-color: var(--ds-orange-700);
  background: var(--ds-orange-700);
}

.ppt-agent-page :deep(.el-progress-bar__outer) {
  background: var(--ds-canvas-deep);
}

.ppt-agent-page :deep(.el-tag) {
  border-color: var(--ds-status-success-border);
  background: var(--ds-green-soft);
  color: var(--ds-green);
  font-family: var(--ds-font-sans);
}

:global(.questionnaire-drawer.el-drawer),
:global(.history-drawer.el-drawer),
:global(.questionnaire-drawer .el-drawer__header),
:global(.history-drawer .el-drawer__header),
:global(.questionnaire-drawer .el-drawer__body),
:global(.history-drawer .el-drawer__body) {
  background: var(--ds-surface-solid);
  color: var(--ds-ink);
}

:global(.questionnaire-drawer .el-drawer__header),
:global(.history-drawer .el-drawer__header) {
  border-bottom-color: var(--ds-line);
}

:global(.questionnaire-drawer .el-drawer__title),
:global(.history-drawer .el-drawer__title),
:global(.questionnaire-drawer .question-title span),
:global(.questionnaire-drawer .material-basket-head strong) {
  color: var(--ds-ink);
}

:global(.questionnaire-drawer .question-title small),
:global(.questionnaire-drawer .material-basket-head span),
:global(.questionnaire-drawer .material-category-hint),
:global(.questionnaire-drawer .material-empty) {
  color: var(--ds-muted);
}

:global(.questionnaire-drawer .material-basket),
:global(.questionnaire-drawer .questionnaire-collapse) {
  border-color: var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
}

:global(.questionnaire-drawer .material-category-tab),
:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__header) {
  border-color: var(--ds-line);
  background: var(--ds-canvas);
  color: var(--ds-ink-2);
}

:global(.questionnaire-drawer .material-category-tab.active) {
  border-color: var(--ds-orange-300);
  background: var(--ds-orange-50);
  color: var(--ds-orange-900);
}

:global(.questionnaire-drawer .material-category-tab span),
:global(.questionnaire-drawer .basket-upload-button) {
  color: var(--ds-orange-700);
}

:global(.questionnaire-drawer .basket-upload-button) {
  border-color: var(--ds-orange-300);
  background: var(--ds-orange-50);
}

:global(.questionnaire-drawer .el-drawer__close-btn) {
  color: var(--ds-ink-2);
}

:global(.questionnaire-drawer .drawer-intro) {
  border-color: var(--ds-orange-200);
  border-radius: var(--ds-radius-md);
  background: var(--ds-orange-50);
}

:global(.questionnaire-drawer .drawer-intro strong) {
  color: var(--ds-orange-900);
}

:global(.questionnaire-drawer .drawer-intro span) {
  color: var(--ds-muted);
}

:global(.questionnaire-drawer .material-basket-head) {
  align-items: flex-start;
}

:global(.questionnaire-drawer .basket-upload-button) {
  color: var(--ds-orange-800);
}

:global(.questionnaire-drawer .material-category-tab strong) {
  color: var(--ds-ink-2);
}

:global(.questionnaire-drawer .material-category-tab.active strong) {
  color: var(--ds-orange-900);
}

:global(.questionnaire-drawer .material-file-item) {
  border-color: var(--ds-line);
  border-radius: var(--ds-radius-sm);
  background: var(--ds-canvas);
}

:global(.questionnaire-drawer .material-file-item strong) {
  color: var(--ds-ink-2);
}

:global(.questionnaire-drawer .material-file-item span) {
  color: var(--ds-muted);
}

:global(.questionnaire-drawer .material-file-item button) {
  color: var(--ds-status-danger-text);
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__wrap) {
  border-bottom-color: var(--ds-line);
  background: var(--ds-surface-solid);
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__content) {
  color: var(--ds-ink-2);
}

:global(.questionnaire-drawer .questionnaire-collapse .el-collapse-item__arrow) {
  color: var(--ds-muted);
}

:global(.questionnaire-drawer .question-body) {
  background: var(--ds-surface-solid);
}

:global(.questionnaire-drawer .form-block label) {
  color: var(--ds-ink-2);
  font-weight: var(--ds-weight-bold);
}

:global(.questionnaire-drawer .el-input__wrapper) {
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  background: var(--ds-input-bg);
  box-shadow: none;
}

:global(.questionnaire-drawer .el-textarea__inner) {
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-textarea-radius, var(--ds-radius-md));
  background: var(--ds-input-bg);
  box-shadow: none;
  line-height: 1.55;
}

:global(.questionnaire-drawer .el-input__wrapper:hover),
:global(.questionnaire-drawer .el-textarea__inner:hover) {
  border-color: var(--ds-input-border-hover);
}

:global(.questionnaire-drawer .el-input__wrapper.is-focus),
:global(.questionnaire-drawer .el-textarea__inner:focus) {
  border-color: var(--ds-input-focus-border);
  box-shadow: var(--ds-input-focus-ring);
}

:global(.questionnaire-drawer .el-input__inner),
:global(.questionnaire-drawer .el-textarea__inner) {
  color: var(--ds-ink);
}

:global(.questionnaire-drawer .el-input__inner::placeholder),
:global(.questionnaire-drawer .el-textarea__inner::placeholder) {
  color: var(--ds-faint);
}

:global(.history-drawer .history-head span),
:global(.history-drawer .history-card span),
:global(.history-drawer .history-card small) {
  color: var(--ds-muted);
}

:global(.history-drawer .history-card) {
  border-color: var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
  color: var(--ds-ink);
  transition:
    border-color var(--ds-control-transition),
    background-color var(--ds-control-transition);
}

:global(.history-drawer .history-card:hover) {
  border-color: var(--ds-orange-300);
  background: var(--ds-orange-50);
}

:global(.history-drawer .history-card.active) {
  border-color: var(--ds-orange-700);
  background: var(--ds-orange-50);
}

:global(.history-drawer .history-error) {
  border-color: var(--ds-status-danger-border);
  border-radius: var(--ds-radius-md);
  background: var(--ds-status-danger-bg);
  color: var(--ds-status-danger-text);
}

:global(.history-drawer .history-error span) {
  color: var(--ds-status-danger-text);
}

.history-loading {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-canvas);
}

.history-loading-dot {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--ds-orange-700);
  animation: history-loading-pulse 1s ease-in-out infinite alternate;
}

.history-loading strong,
.history-loading small {
  display: block;
}

.history-loading strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-body);
}

.history-loading small {
  margin-top: 3px;
  color: var(--ds-muted);
}

@keyframes history-loading-pulse {
  from {
    opacity: 0.35;
    transform: scale(0.8);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* PPT creation flow: use the global product vocabulary and reveal detail only
   when the user asks for it. */
.ppt-icon-button {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: 10px;
  background: var(--ds-btn-secondary-bg);
  color: var(--ds-ink-2);
  font: inherit;
  cursor: pointer;
  transition:
    color 180ms var(--ds-motion-ease-out),
    border-color 180ms var(--ds-motion-ease-out),
    background-color 180ms var(--ds-motion-ease-out);
}

.ppt-icon-button:hover {
  border-color: var(--ds-orange-200);
  background: var(--ds-orange-50);
  color: var(--ds-orange-800);
}

.ppt-icon-button:focus-visible,
.project-info-summary:focus-visible,
.advanced-settings-toggle:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.creation-landing {
  border-radius: var(--ds-radius-lg);
  box-shadow: var(--ds-card-shadow);
}

.creation-landing__content {
  width: min(100%, 560px);
  padding: clamp(30px, 5vh, 54px) var(--ds-space-5);
  animation-duration: 220ms;
}

.creation-file-mark {
  width: 48px;
  height: 48px;
  margin-bottom: var(--ds-space-3);
  border: 0;
  border-radius: 13px;
  background: var(--ds-orange-50);
  color: var(--ds-orange-700);
  box-shadow: none;
}

.creation-file-mark svg {
  width: 24px;
  height: 24px;
}

.creation-landing h2 {
  margin: 0;
  font-size: 30px;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.creation-landing__content > p {
  max-width: 38em;
  margin-top: var(--ds-space-2);
  font-size: var(--ds-text-body);
  line-height: 1.6;
}

.creation-steps {
  width: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  margin-top: var(--ds-space-5);
}

.creation-step {
  min-height: 0;
  display: inline;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.4;
  text-align: center;
  transition: none;
}

.creation-step:hover {
  border: 0;
  background: transparent;
  box-shadow: none;
  transform: none;
}

.creation-steps > i {
  width: 18px;
  height: 1px;
  background: var(--ds-line-strong);
}

.creation-start-button {
  min-height: var(--ds-btn-height);
  margin-top: var(--ds-space-5);
  padding: 0 var(--ds-btn-padding-x);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-btn-font);
  box-shadow: none;
  transition:
    border-color 180ms var(--ds-motion-ease-out),
    background-color 180ms var(--ds-motion-ease-out);
}

.creation-start-button:hover {
  box-shadow: none;
  transform: none;
}

.creation-setup-panel {
  width: min(100%, 760px);
  height: 100%;
  padding: var(--ds-space-5) clamp(22px, 4vw, 42px) var(--ds-space-6);
  border-radius: var(--ds-radius-lg);
  animation-duration: 220ms;
}

.creation-setup-panel > .form-block,
.creation-setup-panel > .file-drop,
.creation-setup-panel > .project-info-summary,
.creation-setup-panel > .paper-upload-guide,
.creation-setup-panel > .advanced-settings-toggle,
.creation-setup-panel > .advanced-settings-panel,
.creation-setup-panel > .creation-save-note,
.creation-setup-panel > .creation-service-warning,
.creation-setup-panel > .action-dock {
  width: 100%;
  max-width: 640px;
  margin-right: auto;
  margin-left: auto;
}

.creation-setup-panel > .output-type-block {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}

.creation-setup-panel .output-type-options {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ds-space-2);
}

.creation-setup-panel .output-type-card {
  min-height: 62px;
  grid-template-columns: minmax(0, 1fr) 18px;
  gap: var(--ds-space-2);
  padding: 11px 13px;
}

.creation-setup-panel .output-type-copy strong {
  font-size: var(--ds-text-body);
}

.creation-setup-panel .output-type-copy small {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.35;
}

#ppt-material-setup .file-drop {
  min-height: 78px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-3);
  padding: var(--ds-space-3) var(--ds-space-4);
  text-align: left;
}

#ppt-material-setup .file-drop .el-icon {
  margin: 0;
}

#ppt-material-setup .file-drop strong,
#ppt-material-setup .file-drop span {
  max-width: 52ch;
}

.project-info-summary {
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
  margin-top: var(--ds-space-3);
  padding: 10px 13px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-sm);
  background: var(--ds-surface-subtle);
  color: var(--ds-ink-2);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.project-info-summary > div {
  display: flex;
  align-items: baseline;
  gap: var(--ds-space-2);
  min-width: 0;
}

.project-info-summary strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-body);
}

.project-info-summary span {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.project-info-summary__action {
  flex: 0 0 auto;
  color: var(--ds-orange-700) !important;
  font-weight: var(--ds-weight-bold);
}

.advanced-settings-toggle {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--ds-space-3);
  padding: 0 13px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-sm);
  background: var(--ds-surface-solid);
  color: var(--ds-ink-2);
  font: inherit;
  font-size: var(--ds-text-body-sm);
  cursor: pointer;
}

.advanced-settings-toggle > span:first-child {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.advanced-settings-panel {
  display: grid;
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-3);
  padding-top: var(--ds-space-4);
  border-top: 1px solid var(--ds-line);
}

.advanced-settings-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr 1fr;
  align-items: end;
  gap: var(--ds-space-3);
}

.advanced-settings-grid .form-block {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
}

.advanced-settings-grid .form-block > label {
  display: block;
  margin-bottom: 6px;
}

.advanced-settings-grid :deep(.el-radio-button__inner) {
  min-height: 32px;
  padding: 7px 12px;
  font-size: var(--ds-text-caption);
  line-height: 16px;
}

.advanced-settings-grid :deep(.el-select__wrapper) {
  min-height: 32px;
}

.advanced-settings-panel .generation-target,
.advanced-settings-panel .prep-mode,
.advanced-settings-panel .idea-brief-card,
.advanced-settings-panel .readiness-card,
.advanced-settings-panel .extra-notes,
.advanced-settings-panel .creation-options-grid {
  margin: 0;
}

.advanced-settings-panel .form-block > label {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-bold);
}

.advanced-settings-panel .creation-options-grid {
  gap: var(--ds-space-2);
}

.advanced-settings-panel .creation-options-grid .form-block {
  padding: 0;
  border: 0;
  background: transparent;
}

.creation-service-warning {
  margin-top: var(--ds-space-3);
  padding: 9px 12px;
  border: 1px solid var(--ds-status-warning-border);
  border-radius: var(--ds-radius-sm);
  background: var(--ds-status-warning-bg);
  color: var(--ds-status-warning-text);
  font-size: var(--ds-text-caption);
}

.creation-setup-panel > .action-dock {
  position: static;
  margin-top: var(--ds-space-4);
  margin-bottom: 0;
  padding: 0;
  border-top: 0;
  background: transparent;
}

.creation-setup-panel > .action-dock .el-button {
  min-height: var(--ds-btn-height);
  border-radius: var(--ds-radius-sm);
}

#ppt-material-setup .file-drop {
  min-height: 82px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  grid-template-areas: "icon copy";
  align-items: center;
  justify-content: stretch;
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-3);
  padding: 14px 16px;
  border: 1px dashed var(--ds-orange-300);
  border-radius: var(--ds-radius-md);
  background: linear-gradient(90deg, var(--ds-surface-solid), var(--ds-orange-50));
  text-align: left;
  box-shadow: none;
}

#ppt-material-setup .file-drop::after {
  content: none;
}

#ppt-material-setup .file-drop .file-drop__icon {
  grid-area: icon;
  width: 40px;
  height: 40px;
  margin: 0;
  border-radius: 10px;
  background: var(--ds-surface-solid);
  color: var(--ds-orange-700);
  font-size: 19px;
  box-shadow: inset 0 0 0 1px var(--ds-orange-200);
}

#ppt-material-setup .file-drop__copy {
  grid-area: copy;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

#ppt-material-setup .file-drop__copy strong {
  max-width: none;
  padding: 0;
  overflow: visible;
  color: var(--ds-ink);
  font-size: var(--ds-text-body);
  font-weight: var(--ds-weight-bold);
  line-height: 1.35;
  text-overflow: clip;
  white-space: normal;
}

#ppt-material-setup .file-drop__copy small {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

#ppt-material-setup .file-drop:hover,
#ppt-material-setup .file-drop.is-ready {
  border-color: var(--ds-orange-600);
  background: var(--ds-orange-50);
}

#ppt-material-setup .file-drop:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ds-orange-600) 22%, transparent);
  outline-offset: 2px;
}

#ppt-material-setup .file-drop.is-ready .file-drop__icon {
  background: var(--ds-orange-100);
}

.creation-landing {
  width: min(100%, var(--ds-page-max));
  margin: 0 auto;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  place-items: stretch;
  overflow: hidden;
}

.creation-landing__content {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
  align-items: stretch;
  padding: 0;
  text-align: left;
}

.creation-landing__intro,
.creation-landing__process {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.creation-landing__intro {
  align-items: flex-start;
  padding: clamp(52px, 6vh, 68px) clamp(40px, 4.5vw, 56px);
}

.creation-landing__process {
  padding: clamp(52px, 6vh, 68px) clamp(38px, 4vw, 50px);
  border-left: 1px solid var(--ds-line);
  background: var(--ds-surface-subtle);
}

.creation-file-mark {
  width: 50px;
  height: 50px;
  margin: 0 0 var(--ds-space-5);
  border-radius: 14px;
}

.creation-file-mark .el-icon {
  font-size: 23px;
}

.creation-kicker,
.creation-guide-kicker {
  color: var(--ds-orange-700);
  font-size: var(--ds-text-label);
  font-weight: var(--ds-weight-bold);
}

.creation-landing h2 {
  max-width: 13em;
  margin: var(--ds-space-3) 0 0;
  font-size: clamp(32px, 3vw, 42px);
  line-height: 1.18;
  letter-spacing: -0.035em;
}

.creation-landing__intro > p {
  max-width: 33em;
  margin: var(--ds-space-4) 0 0;
  font-size: 16px;
  line-height: 1.75;
}

.creation-start-button {
  align-self: flex-start;
  min-height: 46px;
  margin-top: var(--ds-space-6);
  padding: 0 24px;
}

.creation-start-note {
  margin-top: var(--ds-space-3);
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.5;
}

.creation-process-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--ds-space-4);
  padding-bottom: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-line);
}

.creation-process-head strong {
  color: var(--ds-ink);
  font-size: 20px;
}

.creation-process-head span {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.creation-steps {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  margin: var(--ds-space-3) 0 0;
  padding: 0;
  list-style: none;
}

.creation-step {
  min-height: 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: start;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4) 0;
  border: 0;
  border-bottom: 1px solid var(--ds-line);
  background: transparent;
  text-align: left;
}

.creation-step:last-child {
  border-bottom: 0;
}

.creation-step:hover {
  border-color: var(--ds-line);
  background: transparent;
  box-shadow: none;
  transform: none;
}

.creation-step > span {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--ds-orange-100);
  color: var(--ds-orange-800);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-bold);
}

.creation-step strong {
  font-size: var(--ds-text-body);
  line-height: 1.4;
}

.creation-step small {
  margin-top: 3px;
  font-size: var(--ds-text-caption);
  line-height: 1.55;
}

.creation-result-note {
  margin: var(--ds-space-3) 0 0;
  padding-top: var(--ds-space-4);
  border-top: 1px solid var(--ds-line);
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.6;
}

.creation-setup-shell {
  width: 100%;
  max-width: var(--ds-page-max);
  height: auto;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  grid-template-rows: auto auto;
  align-items: stretch;
  gap: 0;
  margin: 0 auto;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-surface-solid);
  box-shadow: var(--ds-card-shadow);
}

.creation-setup-guide {
  min-height: 0;
  height: auto;
  padding: 26px 24px 24px;
  overflow: visible;
  border: 0;
  border-right: 1px solid var(--ds-line);
  border-radius: 0;
  background: var(--ds-surface-subtle);
  box-shadow: none;
}

.creation-setup-guide h2 {
  margin: var(--ds-space-3) 0 0;
  color: var(--ds-ink);
  font-size: 22px;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.creation-setup-guide > p {
  margin: var(--ds-space-3) 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-body-sm);
  line-height: 1.65;
}

.creation-guide-steps {
  display: grid;
  gap: 0;
  margin: var(--ds-space-4) 0 0;
  padding: 0;
  list-style: none;
}

.creation-guide-steps li {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: var(--ds-space-3);
  padding: 10px 0;
  color: var(--ds-muted);
}

.creation-guide-steps li > span {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 1px solid var(--ds-line-strong);
  border-radius: 50%;
  background: var(--ds-surface-solid);
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: var(--ds-weight-bold);
}

.creation-guide-steps strong,
.creation-guide-steps small {
  display: block;
}

.creation-guide-steps strong {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-body-sm);
  line-height: 1.4;
}

.creation-guide-steps small {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.5;
}

.creation-guide-steps li.is-complete > span {
  border-color: var(--ds-ink);
  background: var(--ds-ink);
  color: var(--ds-surface-solid);
}

.creation-guide-steps li.is-current > span {
  border-color: var(--ds-orange-700);
  background: var(--ds-orange-700);
  color: var(--ds-surface-solid);
}

.creation-guide-steps li.is-current strong {
  color: var(--ds-ink);
}

.creation-guide-note {
  margin-top: var(--ds-space-4);
  padding: 11px 12px;
  border: 1px solid var(--ds-orange-200);
  border-radius: var(--ds-radius-sm);
  background: var(--ds-orange-50);
}

.creation-guide-note strong,
.creation-guide-note span {
  display: block;
}

.creation-guide-note strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-caption);
}

.creation-guide-note span {
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.5;
}

.creation-setup-panel {
  width: 100%;
  height: auto;
  min-height: 0;
  margin: 0;
  padding: 26px 30px 28px;
  overflow-x: hidden;
  overflow-y: visible;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.creation-setup-panel > .form-block,
.creation-setup-panel > .file-drop,
.creation-setup-panel > .project-info-summary,
.creation-setup-panel > .paper-upload-guide,
.creation-setup-panel > .advanced-settings-toggle,
.creation-setup-panel > .advanced-settings-panel,
.creation-setup-panel > .creation-save-note,
.creation-setup-panel > .creation-service-warning,
.creation-setup-panel > .action-dock {
  max-width: none;
}

.creation-save-note {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  margin: var(--ds-space-3) 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.5;
}

.creation-save-note .el-icon {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--ds-green);
}

@media (prefers-reduced-motion: reduce) {
  .material-drawer-enter-active,
  .material-drawer-leave-active,
  .material-drawer-enter-active .material-drawer,
  .material-drawer-leave-active .material-drawer,
  .history-loading-dot,
  .creation-landing__content,
  .creation-setup-panel {
    transition: none;
    animation: none;
  }

  .creation-step,
  .creation-start-button,
  .creation-start-button span {
    transition: none;
  }
}

@media (max-width: 1180px) {
  .agent-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .creation-landing {
    min-height: 560px;
  }

  .preview-panel {
    min-height: 720px;
  }

  .log-panel {
    min-height: 440px;
  }
}

@media (max-width: 900px) {
  .ppt-agent-page.is-landing-view,
  .ppt-agent-page.is-setup-view {
    padding-bottom: calc(112px + env(safe-area-inset-bottom));
  }

  .creation-landing__content {
    grid-template-columns: 1fr;
  }

  .creation-landing__intro,
  .creation-landing__process {
    padding: 40px;
  }

  .creation-landing__process {
    border-top: 1px solid var(--ds-line);
    border-left: 0;
  }

  .creation-setup-shell {
    width: min(100%, 680px);
    height: auto;
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    overflow: visible;
  }

  .creation-setup-guide,
  .creation-setup-panel {
    height: auto;
    min-height: 0;
  }

  .creation-setup-guide {
    border-right: 0;
    border-bottom: 1px solid var(--ds-line);
  }
}

@media (max-width: 720px) {
  .creation-landing {
    min-height: 520px;
    overflow: visible;
  }

  .creation-landing__content {
    padding: 0;
  }

  .creation-landing__intro,
  .creation-landing__process {
    padding: 32px var(--ds-space-4);
  }

  .creation-landing h2 {
    font-size: 28px;
  }

  .creation-landing__content > p {
    font-size: var(--ds-text-body);
  }

  .creation-steps {
    display: grid;
    margin-top: var(--ds-space-3);
  }

  .creation-options-grid {
    grid-template-columns: 1fr;
  }

  .creation-step {
    min-height: 0;
    display: grid;
    padding: var(--ds-space-3) 0;
  }

  .creation-setup-shell {
    overflow: visible;
  }

  .creation-setup-panel {
    height: auto;
    min-height: 0;
    padding: var(--ds-space-4);
    padding-bottom: 96px;
  }

  .creation-setup-guide {
    padding: var(--ds-space-5) var(--ds-space-4);
  }

  .material-drawer {
    width: 100%;
  }

  .creation-setup-panel .output-type-options {
    grid-template-columns: 1fr;
  }

  .advanced-settings-grid {
    grid-template-columns: 1fr;
  }

  .project-info-summary > div {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }

  .preview-panel {
    min-height: 620px;
  }
}

/* AiAppShell is the sole owner of page gutters and viewport sizing. */
.ppt-agent-page {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
  max-height: none;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  gap: 0;
  padding: 0;
  overflow: hidden;
  color: var(--ds-ink-2);
  background: transparent;
  font-family: var(--ds-font-sans);
}

.ppt-agent-page.is-landing-view,
.ppt-agent-page.is-setup-view {
  height: auto;
  min-height: 0;
  max-height: none;
  display: block;
  padding: 0;
  overflow: visible;
}

.creation-landing {
  width: 100%;
  min-height: 0;
  margin: 0;
  display: block;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.creation-landing__content {
  height: auto;
}

.creation-setup-shell {
  max-width: none;
  grid-template-rows: auto;
  margin: 0;
}

@media (max-width: 1180px) {
  .ppt-agent-page.is-workspace-view {
    height: auto;
    min-height: 100%;
    overflow: visible;
  }

  .ppt-agent-page.is-workspace-view .agent-layout {
    height: auto;
    min-height: 100%;
  }
}

.ppt-mobile-more {
  display: none;
}

@media (max-width: 767px) {
  .ppt-icon-button.ppt-workspace-secondary-action {
    display: none;
  }

  .ppt-mobile-more {
    display: inline-flex;
  }

  .ppt-workspace-primary-action,
  .ppt-mobile-more .ppt-icon-button {
    width: 40px;
    min-width: 40px;
    height: 40px;
  }
}
</style>
