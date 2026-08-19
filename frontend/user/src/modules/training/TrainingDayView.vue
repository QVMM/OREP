<template>
  <div ref="pageRef" class="student-page training-day-page">
    <header class="student-page__head training-page-head">
      <div>
        <h1>任务详情</h1>
        <p v-if="data.hasTrainingDay">
          {{ camp.teamName }}<template v-if="camp.campName && camp.campName !== camp.teamName"> · {{ formatTrainingCopy(camp.campName) }}</template> · 训练第 {{ data.dayNo }} 天
        </p>
        <p v-else>查看当天任务、成果提交和老师反馈。</p>
      </div>
      <div class="training-head-actions">
        <BaseButton type="secondary" to="/training/today">返回训练任务</BaseButton>
        <div v-if="data.hasTrainingDay" class="training-countdown">
          <span>距离备赛结束</span>
          <strong>{{ camp.remainingDays ?? '—' }}</strong>
          <em>天</em>
        </div>
      </div>
    </header>

    <section v-if="loading" class="student-card student-skeleton">
      <el-skeleton :rows="9" animated />
    </section>

    <section v-else-if="error" class="student-card student-error">
      <div class="student-empty__content">
        <div class="student-empty__icon"><WarningFilled /></div>
        <h2>训练详情暂时没有加载出来</h2>
        <p>{{ error }}</p>
        <BaseButton @click="load">重新加载</BaseButton>
      </div>
    </section>

    <section v-else-if="!data.hasCamp" class="student-card student-empty">
      <div class="student-empty__content">
        <div class="student-empty__icon"><Calendar /></div>
        <h2>当前没有训练安排</h2>
        <p>{{ formatTrainingCopy(data.message) }}</p>
        <BaseButton type="secondary" to="/project-team">查看团队信息</BaseButton>
      </div>
    </section>

    <section v-else-if="!data.hasTrainingDay" class="student-card student-empty">
      <div class="student-empty__content">
        <div class="student-empty__icon"><Clock /></div>
        <h2>今天暂未安排训练</h2>
        <p>{{ data.nextDay?.trainingDate ? `下一次训练是第 ${data.nextDay.dayNo} 天，日期为 ${formatDate(data.nextDay.trainingDate)}。` : data.message }}</p>
        <BaseButton to="/training/today">查看训练任务</BaseButton>
      </div>
    </section>

    <section v-else-if="data.locked" class="student-card student-empty">
      <div class="student-empty__content">
        <div class="student-empty__icon"><Clock /></div>
        <h2>{{ trainingDayLockLabel(data) || '训练日尚未开放' }}</h2>
        <p>{{ trainingDayLockMessage(data) }}</p>
        <BaseButton to="/training/today">查看训练任务</BaseButton>
      </div>
    </section>

    <template v-else>
      <nav
        class="training-flow"
        :class="{ 'has-learning': learningResources.length }"
        aria-label="今日训练流程"
      >
        <template v-if="learningResources.length">
          <div class="is-active">
            <span>01</span><div><strong>今日学习</strong><small>{{ learningFlowStatus }}</small></div>
          </div>
          <span class="training-flow__connector" aria-hidden="true"></span>
        </template>
        <div class="is-active">
          <span>{{ learningResources.length ? '02' : '01' }}</span><div><strong>今日任务</strong><small>任务书与交付要求</small></div>
        </div>
        <span class="training-flow__connector" aria-hidden="true"></span>
        <div>
          <span>{{ learningResources.length ? '03' : '02' }}</span><div><strong>成果提交</strong><small>{{ submissionStatusLabel(submissionStatus) }}</small></div>
        </div>
      </nav>

      <div
        class="training-dashboard"
        :class="{ 'is-side-rail': bothSidePanelsCollapsed }"
      >
        <main class="training-primary">
          <TrainingLearningSection
            v-if="learningResources.length"
            id="training-learning"
            :resources="learningResources"
            @change="updateLearningResources"
          />

          <section class="student-card training-focus-card">
            <div class="training-section-title">
              <span class="training-section-title__step">{{ learningResources.length ? '02' : '01' }}</span>
              <div><small>今日任务</small><h2>任务书</h2></div>
            </div>

            <div class="training-task-book__title">
              <span>任务主题</span>
              <h3>{{ primaryTask.title || data.title }}</h3>
            </div>

            <section class="training-task-book__section is-summary" aria-labelledby="taskSummaryTitle">
              <h4 id="taskSummaryTitle">任务概要</h4>
              <p>{{ data.summary || '按照交付要求完成今天的训练，并提交可检查的成果。' }}</p>
            </section>

            <section class="training-task-book__section" aria-labelledby="taskDescriptionTitle">
              <h4 id="taskDescriptionTitle">正式任务描述</h4>
              <div
                v-if="safeContentHtml"
                ref="richContentRef"
                class="training-rich-content"
                v-html="safeContentHtml"
              ></div>
              <p v-else-if="primaryTask.description" class="training-task-book__fallback">{{ primaryTask.description }}</p>
              <div v-else class="training-inline-empty">老师暂未填写正式任务描述。</div>
            </section>

            <section class="training-task-book__section" aria-labelledby="taskRequirementsTitle">
              <h4 id="taskRequirementsTitle">交付要求</h4>
              <div v-if="requirements.length" class="training-requirements" aria-label="交付要求">
                <article
                  v-for="item in requirements"
                  :key="item.id"
                  :class="{
                    'is-optional': !item.required,
                    'is-daily-report': isDailyReportRequirement(item),
                    'is-typing-practice': isTypingPracticeRequirement(item)
                  }"
                >
                  <span
                    class="training-requirements__signal"
                    :class="{ 'is-optional': !item.required }"
                    :aria-label="item.required ? '必交' : '可选'"
                    :title="item.required ? '必交' : '可选'"
                  ></span>
                  <div class="training-requirements__copy">
                    <strong>
                      {{ item.title }}
                      <em v-if="isDailyReportRequirement(item)" class="training-requirements__badge">日报</em>
                      <em
                        v-else-if="isTypingPracticeRequirement(item)"
                        class="training-requirements__badge training-requirements__badge--typing"
                      >打字</em>
                    </strong>
                    <p v-if="item.description">{{ item.description }}</p>
                    <router-link
                      v-if="isDailyReportRequirement(item)"
                      class="training-requirements__cta"
                      to="/daily-reports/write"
                    >
                      去写今日日报
                      <ArrowRight />
                    </router-link>
                    <router-link
                      v-else-if="isTypingPracticeRequirement(item)"
                      class="training-requirements__cta training-requirements__cta--typing"
                      to="/typing-practice"
                    >
                      去打字练习
                      <ArrowRight />
                    </router-link>
                  </div>
                </article>
              </div>
              <div v-else class="training-inline-empty">老师暂未拆分交付清单，请按任务说明提交成果。</div>
            </section>

            <div v-if="secondaryTasks.length" class="training-secondary-tasks">
              <strong>同日其他任务</strong>
              <router-link
                v-for="task in secondaryTasks"
                :key="task.taskId"
                :to="`/training/tasks/${task.taskId}?dayId=${data.dayId}`"
              >
                <span>{{ task.title }}</span>
                <em>{{ task.latestSubmissionId ? submissionStatusLabel(task.latestSubmissionStatus) : '查看详情' }}</em>
                <ArrowRight />
              </router-link>
            </div>

          </section>
        </main>

        <aside class="training-side" :class="{ 'is-rail': bothSidePanelsCollapsed }">
          <section
            v-if="!attachmentsCollapsed"
            id="trainingAttachmentsPanel"
            class="student-card training-attachments-card"
          >
            <div class="training-card-head">
              <h2>任务附件</h2>
              <div class="training-card-head__actions">
                <span>{{ taskAttachments.length }} 个</span>
                <button
                  type="button"
                  class="training-panel-toggle"
                  aria-label="折叠任务附件"
                  aria-controls="trainingAttachmentsPanel"
                  :aria-expanded="true"
                  title="折叠任务附件"
                  @click="toggleSidePanel('attachments')"
                >
                  <Fold aria-hidden="true" />
                </button>
              </div>
            </div>

            <div v-if="taskAttachments.length" class="training-attachment-list">
              <article v-for="attachment in taskAttachments" :key="attachment.id" class="training-attachment-item">
                <span class="training-attachment-item__type">{{ fileExtension(attachment.fileName) }}</span>
                <div class="training-attachment-item__meta">
                  <strong>{{ attachment.fileName }}</strong>
                  <small>{{ formatFileSize(attachment.fileSize) }}</small>
                </div>
                <div class="training-attachment-item__actions">
                  <button type="button" @click="previewAttachment(attachment)">预览</button>
                  <a v-if="attachment.fileUrl" :href="withAuthMediaUrl(attachment.fileUrl)" :download="attachment.fileName">下载</a>
                </div>
              </article>
            </div>
            <div v-else class="training-inline-empty">老师暂未上传任务附件。</div>
          </section>

          <button
            v-else
            type="button"
            class="student-card training-side-restore"
            aria-label="展开任务附件"
            aria-controls="trainingAttachmentsPanel"
            :aria-expanded="false"
            title="展开任务附件"
            @click="toggleSidePanel('attachments')"
          >
            <span class="training-side-restore__icon">
              <Paperclip aria-hidden="true" />
              <em v-if="taskAttachments.length">{{ taskAttachments.length }}</em>
            </span>
            <span class="training-side-restore__copy">
              <strong>任务附件</strong>
              <small>{{ taskAttachments.length }} 个文件</small>
            </span>
            <Expand class="training-side-restore__expand" aria-hidden="true" />
          </button>

          <section
            v-if="!submissionCollapsed"
            id="trainingSubmissionPanel"
            class="student-card training-submit-card"
          >
            <div class="training-card-head">
              <div class="training-section-title training-submit-card__heading">
                <span class="training-section-title__step">{{ learningResources.length ? '03' : '02' }}</span>
                <div>
                  <h2>提交成果</h2>
                  <p>完成任务书要求后，提交可检查的成果</p>
                </div>
              </div>
              <div class="training-card-head__actions">
                <span class="training-submit-card__status">{{ submissionStatusLabel(submissionStatus) }}</span>
                <button
                  type="button"
                  class="training-panel-toggle"
                  aria-label="折叠提交成果"
                  aria-controls="trainingSubmissionPanel"
                  :aria-expanded="true"
                  title="折叠提交成果"
                  @click="toggleSidePanel('submission')"
                >
                  <Fold aria-hidden="true" />
                </button>
              </div>
            </div>

            <div class="training-submit-card__time">
              <span>{{ hasSubmission ? '提交时间' : '截止时间' }}</span>
              <strong>{{ hasSubmission ? formatDateTime(submission.submittedAt || primaryTask.latestSubmittedAt) : formatDateTime(data.dueAt) }}</strong>
            </div>

            <div class="training-status-banner" :class="`is-${statusBanner.tone}`">
              <span aria-hidden="true"></span>
              <strong>{{ statusBanner.title }}</strong>
            </div>

            <div v-if="incompleteRequiredLearningCount" class="training-learning-reminder">
              还有 {{ incompleteRequiredLearningCount }} 项必学内容未完成，完成后再提交。
            </div>

            <div class="training-submit-card__actions">
              <BaseButton
                v-if="hasDailyReportRequirement"
                type="secondary"
                to="/daily-reports/write"
              >
                去写今日日报 <ArrowRight />
              </BaseButton>
              <BaseButton
                v-if="hasTypingPracticeRequirement"
                type="secondary"
                to="/typing-practice"
              >
                去打字练习 <ArrowRight />
              </BaseButton>
              <BaseButton
                v-if="canOpenSubmission && !hasSubmission && hasFileSubmissionRequirement"
                :to="newSubmissionPath"
              >
                去提交成果 <ArrowRight />
              </BaseButton>
              <BaseButton
                v-else-if="canOpenSubmission && !hasSubmission && !hasDailyReportRequirement && !hasTypingPracticeRequirement"
                :to="newSubmissionPath"
              >
                去提交成果 <ArrowRight />
              </BaseButton>
              <p v-else-if="!canOpenSubmission && !hasSubmission" class="training-submit-lock">
                {{ submissionBlockReason }}
              </p>
              <template v-else-if="needsRevision && canOpenSubmission">
                <BaseButton :to="newSubmissionPath">提交新版本 <ArrowRight /></BaseButton>
                <BaseButton v-if="feedback.feedbackReady" type="secondary" :to="`/training/feedback/${latestSubmissionId}`">查看老师反馈</BaseButton>
                <BaseButton type="secondary" :to="collaborationSubmissionPath">查看我的提交</BaseButton>
              </template>
              <template v-else-if="feedback.feedbackReady">
                <BaseButton :to="`/training/feedback/${latestSubmissionId}`">查看老师反馈 <ArrowRight /></BaseButton>
                <BaseButton type="secondary" :to="collaborationSubmissionPath">查看我的提交</BaseButton>
              </template>
              <BaseButton v-else :to="collaborationSubmissionPath">查看我的提交 <ArrowRight /></BaseButton>
            </div>
          </section>

          <button
            v-else
            type="button"
            class="student-card training-side-restore"
            aria-label="展开提交成果"
            aria-controls="trainingSubmissionPanel"
            :aria-expanded="false"
            title="展开提交成果"
            @click="toggleSidePanel('submission')"
          >
            <span class="training-side-restore__icon is-submission">
              <DocumentChecked aria-hidden="true" />
              <em class="is-status" :class="`is-${statusBanner.tone}`"></em>
            </span>
            <span class="training-side-restore__copy">
              <strong>提交成果</strong>
              <small>{{ submissionStatusLabel(submissionStatus) }}</small>
            </span>
            <Expand class="training-side-restore__expand" aria-hidden="true" />
          </button>

          <span class="training-panel-announcement" role="status" aria-live="polite">
            {{ sidePanelAnnouncement }}
          </span>
        </aside>
      </div>

      <aside
        v-if="outlineEnabled"
        class="training-document-outline"
        :class="{ 'is-open': outlineOpen }"
        aria-label="任务书章节导航"
        @mouseenter="openOutline"
        @mouseleave="scheduleOutlineClose"
        @focusin="openOutline"
        @focusout="scheduleOutlineClose"
      >
        <div
          class="training-document-outline__rail"
        >
          <button
            v-for="item in outlineItems"
            :key="`dot-${item.id}`"
            type="button"
            class="training-document-outline__tick"
            :class="{
              'is-secondary': item.level === 2,
              'is-active': item.id === highlightedOutlineId
            }"
            :aria-label="`跳转到${item.text}`"
            :aria-current="item.id === activeHeadingId ? 'location' : undefined"
            aria-controls="trainingDocumentOutlinePanel"
            :aria-expanded="outlineOpen"
            @mouseenter="previewOutlineItem(item)"
            @focus="previewOutlineItem(item)"
            @click.stop="scrollToOutlineItem(item)"
          >
            <span class="training-document-outline__mark" aria-hidden="true"></span>
          </button>
        </div>

        <nav
          id="trainingDocumentOutlinePanel"
          class="training-document-outline__panel"
          :aria-hidden="!outlineOpen"
          aria-label="任务书目录"
        >
          <header>
            <strong>任务书目录</strong>
            <span>已阅读 {{ readingProgress }}%</span>
          </header>
          <button
            v-for="(item, index) in outlineItems"
            :key="item.id"
            type="button"
            :style="{ '--outline-index': index }"
            :class="{
              'is-secondary': item.level === 2,
              'is-active': item.id === highlightedOutlineId
            }"
            @mouseenter="previewOutlineItem(item)"
            @focus="previewOutlineItem(item)"
            @click="scrollToOutlineItem(item)"
          >
            {{ item.text }}
          </button>
        </nav>
      </aside>

      <button
        v-if="outlineEnabled"
        type="button"
        class="training-mobile-outline-trigger"
        aria-label="打开任务书目录"
        :aria-expanded="mobileOutlineOpen"
        aria-controls="trainingMobileOutlinePanel"
        @click="mobileOutlineOpen = true"
      >
        <Menu aria-hidden="true" />
        <span>目录</span>
      </button>

      <div
        v-if="outlineEnabled && mobileOutlineOpen"
        class="training-mobile-outline-backdrop"
        @click.self="mobileOutlineOpen = false"
      >
        <nav id="trainingMobileOutlinePanel" class="training-mobile-outline-panel" aria-label="任务书目录">
          <header>
            <div>
              <strong>任务书目录</strong>
              <span>已阅读 {{ readingProgress }}%</span>
            </div>
            <button type="button" aria-label="关闭任务书目录" @click="mobileOutlineOpen = false">关闭</button>
          </header>
          <button
            v-for="item in outlineItems"
            :key="`mobile-${item.id}`"
            type="button"
            :class="{
              'is-secondary': item.level === 2,
              'is-active': item.id === activeHeadingId
            }"
            @click="scrollToOutlineItem(item)"
          >
            {{ item.text }}
          </button>
        </nav>
      </div>

      <transition name="training-reading-toast">
        <div
          v-if="resumeMessage"
          class="training-reading-resume"
          role="status"
          aria-live="polite"
        >
          {{ resumeMessage }}
        </div>
      </transition>

      <transition name="training-back-top">
        <button
          v-if="showBackToTop"
          type="button"
          class="training-back-to-top"
          aria-label="回到任务书顶部"
          title="回到顶部"
          @click="scrollToTop"
        >
          <Top aria-hidden="true" />
          <span>回到顶部</span>
        </button>
      </transition>
    </template>

    <FilePreview
      v-model:visible="preview.visible"
      :file-url="preview.fileUrl"
      :file-name="preview.fileName"
      :file-type="preview.fileType"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import DOMPurify from 'dompurify'
import {
  ArrowRight,
  Calendar,
  Clock,
  DocumentChecked,
  Expand,
  Fold,
  Menu,
  Paperclip,
  Top,
  WarningFilled
} from '@element-plus/icons-vue'
import BaseButton from '../../components/base/BaseButton.vue'
import FilePreview from '../../components/FilePreview.vue'
import { getStoredUser } from '../../utils/authStorage'
import { withAuthMediaHtml, withAuthMediaUrl } from '../../utils/mediaUrl'
import TrainingLearningSection from './components/TrainingLearningSection.vue'
import {
  fetchTodayTrainingOverview,
  fetchTrainingDayOverview,
  fetchTrainingFeedback,
  fetchTrainingSubmission,
  reportTaskBookDwell
} from './api'
import { formatDate, formatDateTime, formatTrainingCopy, submissionStatusLabel, trainingDayLockLabel, trainingDayLockMessage } from './format'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref({})
const preview = reactive({ visible: false, fileUrl: '', fileName: '', fileType: '' })
const attachmentsCollapsed = ref(false)
const submissionCollapsed = ref(false)
const sidePanelAnnouncement = ref('')
const pageRef = ref(null)
const richContentRef = ref(null)
const outlineItems = ref([])
const outlineEnabled = ref(false)
const outlineOpen = ref(false)
const mobileOutlineOpen = ref(false)
const activeHeadingId = ref('')
const hoveredOutlineId = ref('')
const readingProgress = ref(0)
const resumeMessage = ref('')
const showBackToTop = ref(false)

const READING_STORAGE_VERSION = 1
const READING_STORAGE_MAX_AGE = 1000 * 60 * 60 * 24 * 90
const OUTLINE_MIN_HEADING_COUNT = 2
const OUTLINE_MIN_CONTENT_HEIGHT = 720
let readingScrollRoot = null
let readingScrollTarget = null
let contentResizeObserver = null
let outlineCloseTimer = 0
let savePositionTimer = 0
let resumeMessageTimer = 0
let scrollFrame = 0
let lastScrollTop = 0
let upwardScrollDistance = 0
let restoringReadingPosition = false
let restoreAnchor = null
let restoreCorrectionTimer = 0
let restoreCorrectionFrame = 0
let readingPositionSavedForExit = false

// 任务书驻留：可见且近期有交互时累计
const dwellSessionId = globalThis.crypto?.randomUUID?.()
  || `dwell_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
let dwellTimer = 0
let dwellLastActiveAt = Date.now()
let dwellPageVisible = typeof document === 'undefined' ? true : !document.hidden

const camp = computed(() => data.value.camp || {})
const tasks = computed(() => data.value.tasks || [])
const primaryTask = computed(() => data.value.primaryTask || {})
const requirements = computed(() => primaryTask.value.requirements || [])
const learningResources = computed(() => data.value.learningResources || [])

function isDailyReportRequirement(item = {}) {
  const asset = String(item.assetType || item.asset_type || '').toUpperCase()
  if (asset === 'DAILY_REPORT') return true
  // 兼容老师仅写「日报」标题的旧数据
  return /日报/.test(String(item.title || ''))
}
function isTypingPracticeRequirement(item = {}) {
  const asset = String(item.assetType || item.asset_type || '').toUpperCase()
  if (asset === 'TYPING_PRACTICE') return true
  return /打字练习|打字任务/.test(String(item.title || ''))
}
function isSpecialRequirement(item = {}) {
  return isDailyReportRequirement(item) || isTypingPracticeRequirement(item)
}
const hasDailyReportRequirement = computed(() => requirements.value.some(isDailyReportRequirement))
const hasTypingPracticeRequirement = computed(() => requirements.value.some(isTypingPracticeRequirement))
const hasFileSubmissionRequirement = computed(() => {
  if (!requirements.value.length) return true
  return requirements.value.some((item) => !isSpecialRequirement(item))
})
const completedLearningCount = computed(() => learningResources.value.filter(item => item.learningStatus === 'COMPLETED' || Number(item.progressPercent) >= 100).length)
const learningFlowStatus = computed(() => {
  const total = learningResources.value.length
  if (completedLearningCount.value >= total && total > 0) return '已完成'
  if (completedLearningCount.value === 0) return '未完成'
  return `${completedLearningCount.value}/${total} 项完成`
})
const incompleteRequiredLearningCount = computed(() => learningResources.value.filter(item => {
  const required = item.required === true || Number(item.required) === 1
  const complete = item.learningStatus === 'COMPLETED' || Number(item.progressPercent) >= 100
  return required && !complete
}).length)
const secondaryTasks = computed(() => tasks.value.filter(task => task.taskId !== primaryTask.value.taskId))
const submission = computed(() => data.value.submission || {})
const feedback = computed(() => data.value.feedback || {})
const latestSubmissionId = computed(() => primaryTask.value.latestSubmissionId || submission.value.submissionId)
const submissionStatus = computed(() => String(primaryTask.value.latestSubmissionStatus || submission.value.status || ''))
const hasSubmission = computed(() => Boolean(latestSubmissionId.value))
const needsRevision = computed(() => ['CHANGES_REQUESTED', 'REJECTED'].includes(submissionStatus.value))
const newSubmissionPath = computed(() => `/training/submissions/new?taskId=${primaryTask.value.taskId}&dayId=${data.value.dayId}`)
const dayLocked = computed(() => Boolean(data.value.locked))
const submissionBlockReason = computed(() => {
  if (dayLocked.value) return trainingDayLockMessage(data.value) || trainingDayLockLabel(data.value)
  if (incompleteRequiredLearningCount.value > 0) {
    return `还有 ${incompleteRequiredLearningCount.value} 项必学内容未完成，请先完成学习再提交。`
  }
  return ''
})
const canOpenSubmission = computed(() => !submissionBlockReason.value)
const collaborationSubmissionPath = computed(() => ({
  path: `/project-team/details/task-${primaryTask.value.taskId}`,
  query: {
    teamId: camp.value.teamId || undefined,
    submissionId: latestSubmissionId.value || undefined
  }
}))
const taskAttachments = computed(() => data.value.attachments || [])
const bothSidePanelsCollapsed = computed(() => attachmentsCollapsed.value && submissionCollapsed.value)
const highlightedOutlineId = computed(() => hoveredOutlineId.value || activeHeadingId.value)
const safeContentHtml = computed(() => withAuthMediaHtml(DOMPurify.sanitize(Number(primaryTask.value.isPrimary) === 1 ? data.value.contentHtml || '' : '', {
  ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'strong', 'b', 'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'br', 'span'],
  ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'src', 'alt', 'data-text-color']
})))
const readingStorageKey = computed(() => {
  const user = getStoredUser()
  const userId = user?.id || user?.userId || user?.username || 'anonymous'
  const taskId = primaryTask.value.taskId || route.params.taskId || 'task'
  const dayId = data.value.dayId || route.query.dayId || route.params.dayId || 'day'
  return `orep:training-reading:v${READING_STORAGE_VERSION}:${userId}:${taskId}:${dayId}`
})

function updateLearningResources(resources) {
  data.value = { ...data.value, learningResources: resources }
}

const statusBanner = computed(() => {
  if (!hasSubmission.value) {
    return { tone: 'orange', title: `请在 ${formatDateTime(data.value.dueAt)} 前提交成果`, detail: '' }
  }
  if (needsRevision.value) {
    return { tone: 'red', title: '老师已反馈，请按意见修改后提交新版本', detail: formatDateTime(feedback.value.reviewedAt) }
  }
  if (submissionStatus.value === 'APPROVED') {
    return { tone: 'green', title: '本次训练已完成', detail: `${formatDateTime(submission.value.submittedAt)} 提交` }
  }
  return {
    tone: 'yellow',
    title: submissionStatus.value === 'REVIEWING' ? '老师正在批改' : '成果已提交，等待老师批改',
    detail: `${formatDateTime(submission.value.submittedAt || primaryTask.value.latestSubmittedAt)} 提交`
  }
})

function fileExtension(name = '') {
  const extension = String(name).split('.').pop()
  return extension && extension !== name ? extension.slice(0, 4).toUpperCase() : 'FILE'
}

function formatFileSize(value) {
  const bytes = Number(value || 0)
  if (!bytes) return '未知大小'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function previewAttachment(attachment) {
  preview.fileUrl = attachment.fileUrl || ''
  preview.fileName = attachment.fileName || '任务附件'
  preview.fileType = attachment.mimeType || ''
  preview.visible = true
}

function toggleSidePanel(panel) {
  if (panel === 'attachments') {
    attachmentsCollapsed.value = !attachmentsCollapsed.value
    sidePanelAnnouncement.value = `任务附件已${attachmentsCollapsed.value ? '折叠' : '展开'}`
    return
  }
  submissionCollapsed.value = !submissionCollapsed.value
  sidePanelAnnouncement.value = `提交成果已${submissionCollapsed.value ? '折叠' : '展开'}`
}

function resetSidePanels() {
  attachmentsCollapsed.value = false
  submissionCollapsed.value = false
  sidePanelAnnouncement.value = ''
}

function hashString(value = '') {
  let hash = 2166136261
  const source = String(value)
  for (let index = 0; index < source.length; index += 1) {
    hash ^= source.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(36)
}

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
}

function getScrollTop() {
  if (!readingScrollRoot) return window.scrollY || 0
  return readingScrollRoot.scrollTop
}

function getScrollViewportHeight() {
  return readingScrollRoot?.clientHeight || window.innerHeight || 0
}

function resolveReadingScrollRoot() {
  const candidate = pageRef.value?.closest('.workspace-main') || null
  if (!candidate) return null
  const overflowY = window.getComputedStyle(candidate).overflowY
  return /(auto|scroll|overlay)/.test(overflowY) ? candidate : null
}

function getMaxScrollTop() {
  if (!readingScrollRoot) {
    const element = document.scrollingElement
    return Math.max(0, (element?.scrollHeight || 0) - window.innerHeight)
  }
  return Math.max(0, readingScrollRoot.scrollHeight - readingScrollRoot.clientHeight)
}

function scrollRootTo(top, behavior = 'auto') {
  const nextTop = Math.max(0, Number(top) || 0)
  if (readingScrollRoot) {
    readingScrollRoot.scrollTo({ top: nextTop, behavior })
    return
  }
  window.scrollTo({ top: nextTop, behavior })
}

function elementTopInScrollRoot(element) {
  if (!element) return 0
  const rect = element.getBoundingClientRect()
  if (!readingScrollRoot) return rect.top + (window.scrollY || 0)
  const rootRect = readingScrollRoot.getBoundingClientRect()
  return rect.top - rootRect.top + readingScrollRoot.scrollTop
}

function findOutlineElement(id) {
  if (!richContentRef.value || !id) return null
  const elementById = document.getElementById(id)
  if (elementById && richContentRef.value.contains(elementById)) return elementById
  return [...richContentRef.value.querySelectorAll('h1, h2, h3')]
    .find(element => element.id === id) || null
}

function rebuildOutline() {
  const content = richContentRef.value
  if (!content) {
    outlineItems.value = []
    outlineEnabled.value = false
    activeHeadingId.value = ''
    return
  }

  const headings = [...content.querySelectorAll('h1, h2, h3')]
    .map(element => ({
      element,
      text: element.textContent?.replace(/\s+/g, ' ').trim() || '',
      tagLevel: Number(element.tagName.slice(1))
    }))
    .filter(item => item.text)

  const presentLevels = [...new Set(headings.map(item => item.tagLevel))].sort((left, right) => left - right)
  const visibleLevels = presentLevels.slice(0, 2)
  const occurrenceBySignature = new Map()
  const taskScope = primaryTask.value.taskId || route.params.taskId || 'task'

  outlineItems.value = headings
    .filter(item => visibleLevels.includes(item.tagLevel))
    .map(item => {
      const signature = `${item.tagLevel}:${item.text}`
      const occurrence = (occurrenceBySignature.get(signature) || 0) + 1
      occurrenceBySignature.set(signature, occurrence)
      const id = `training-heading-${taskScope}-${hashString(signature)}-${occurrence}`
      item.element.id = id
      item.element.classList.add('training-rich-content__anchor')
      return {
        id,
        text: item.text,
        level: item.tagLevel === visibleLevels[0] ? 1 : 2
      }
    })

  refreshOutlineEligibility()
  activeHeadingId.value = outlineItems.value[0]?.id || ''
}

function refreshOutlineEligibility() {
  const content = richContentRef.value
  const viewportHeight = getScrollViewportHeight()
  const minimumHeight = Math.max(OUTLINE_MIN_CONTENT_HEIGHT, viewportHeight * 1.2)
  outlineEnabled.value = Boolean(
    content &&
    outlineItems.value.length >= OUTLINE_MIN_HEADING_COUNT &&
    content.scrollHeight >= minimumHeight
  )
  if (!outlineEnabled.value) {
    outlineOpen.value = false
    mobileOutlineOpen.value = false
  }
}

function updateReadingState() {
  scrollFrame = 0
  const content = richContentRef.value
  if (!content) return

  const rootTop = readingScrollRoot?.getBoundingClientRect().top || 0
  const viewportHeight = getScrollViewportHeight()
  const activationLine = rootTop + Math.min(150, viewportHeight * 0.24)
  let currentItem = outlineItems.value[0]
  for (const item of outlineItems.value) {
    const heading = findOutlineElement(item.id)
    if (heading && heading.getBoundingClientRect().top <= activationLine) {
      currentItem = item
    } else {
      break
    }
  }
  activeHeadingId.value = currentItem?.id || ''

  const scrollTop = getScrollTop()
  const contentTop = elementTopInScrollRoot(content)
  const readableDistance = Math.max(1, content.scrollHeight - viewportHeight * 0.45)
  readingProgress.value = Math.round(Math.min(1, Math.max(0, (scrollTop - contentTop) / readableDistance)) * 100)
}

function scheduleReadingStateUpdate() {
  if (scrollFrame) return
  scrollFrame = window.requestAnimationFrame(updateReadingState)
}

function clearRestoreCorrection() {
  window.clearTimeout(restoreCorrectionTimer)
  if (restoreCorrectionFrame) window.cancelAnimationFrame(restoreCorrectionFrame)
  restoreCorrectionFrame = 0
  restoreAnchor = null
}

function scheduleRestoreCorrection() {
  if (!restoreAnchor || restoreCorrectionFrame) return
  restoreCorrectionFrame = window.requestAnimationFrame(() => {
    restoreCorrectionFrame = 0
    if (!restoreAnchor) return
    const heading = findOutlineElement(restoreAnchor.headingId)
    if (!heading) {
      clearRestoreCorrection()
      return
    }
    const targetTop = Math.min(
      elementTopInScrollRoot(heading) + restoreAnchor.headingOffset,
      getMaxScrollTop()
    )
    if (Math.abs(getScrollTop() - targetTop) < 2) return
    restoringReadingPosition = true
    scrollRootTo(targetTop, 'auto')
    window.requestAnimationFrame(() => {
      restoringReadingPosition = false
      lastScrollTop = getScrollTop()
      updateReadingState()
    })
  })
}

function saveReadingPosition() {
  window.clearTimeout(savePositionTimer)
  if (restoringReadingPosition || !data.value.hasTrainingDay || !readingScrollTarget) return

  const scrollTop = getScrollTop()
  const maxScrollTop = getMaxScrollTop()
  const activeItem = outlineItems.value.find(item => item.id === activeHeadingId.value)
  const activeElement = activeItem ? findOutlineElement(activeItem.id) : null
  const payload = {
    version: READING_STORAGE_VERSION,
    savedAt: Date.now(),
    contentHash: hashString(safeContentHtml.value),
    headingId: activeItem?.id || '',
    headingText: activeItem?.text || '',
    headingOffset: activeElement ? scrollTop - elementTopInScrollRoot(activeElement) : 0,
    scrollTop,
    ratio: maxScrollTop > 0 ? scrollTop / maxScrollTop : 0
  }

  try {
    window.localStorage.setItem(readingStorageKey.value, JSON.stringify(payload))
  } catch {
    // 浏览器禁用本地存储时，不阻断任务书阅读。
  }
}

function scheduleSaveReadingPosition() {
  window.clearTimeout(savePositionTimer)
  savePositionTimer = window.setTimeout(saveReadingPosition, 360)
}

function handleReadingScroll() {
  const currentScrollTop = getScrollTop()
  const delta = currentScrollTop - lastScrollTop
  const viewportHeight = getScrollViewportHeight()
  const deepEnough = currentScrollTop > Math.max(520, viewportHeight * 0.8)

  if (delta < 0) upwardScrollDistance += Math.abs(delta)
  if (delta > 18) upwardScrollDistance = 0

  if (!deepEnough || delta > 36) {
    showBackToTop.value = false
  } else if (upwardScrollDistance >= 72) {
    showBackToTop.value = true
  }

  lastScrollTop = currentScrollTop
  if (restoreAnchor && !restoringReadingPosition) scheduleRestoreCorrection()
  scheduleReadingStateUpdate()
  scheduleSaveReadingPosition()
}

function handleUserScrollIntent(event) {
  if (!restoreAnchor) return
  if (event.type === 'keydown') {
    const scrollKeys = ['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' ']
    if (!scrollKeys.includes(event.key)) return
  }
  clearRestoreCorrection()
}

function bindReadingScrollRoot() {
  const nextRoot = resolveReadingScrollRoot()
  if (readingScrollRoot === nextRoot && readingScrollTarget) return

  readingScrollTarget?.removeEventListener('scroll', handleReadingScroll)
  readingScrollTarget?.removeEventListener('wheel', handleUserScrollIntent)
  readingScrollTarget?.removeEventListener('touchstart', handleUserScrollIntent)
  readingScrollTarget?.removeEventListener('pointerdown', handleUserScrollIntent)
  readingScrollRoot = nextRoot
  readingScrollTarget = nextRoot || window
  lastScrollTop = getScrollTop()
  upwardScrollDistance = 0
  readingScrollTarget.addEventListener('scroll', handleReadingScroll, { passive: true })
  readingScrollTarget.addEventListener('wheel', handleUserScrollIntent, { passive: true })
  readingScrollTarget.addEventListener('touchstart', handleUserScrollIntent, { passive: true })
  readingScrollTarget.addEventListener('pointerdown', handleUserScrollIntent, { passive: true })
}

function readStoredPosition() {
  try {
    const stored = JSON.parse(window.localStorage.getItem(readingStorageKey.value) || 'null')
    if (!stored || stored.version !== READING_STORAGE_VERSION) return null
    if (Date.now() - Number(stored.savedAt || 0) > READING_STORAGE_MAX_AGE) return null
    return stored
  } catch {
    return null
  }
}

async function waitForRichContentLayout() {
  await nextTick()
  const images = [...(richContentRef.value?.querySelectorAll('img') || [])]
    .filter(image => !image.complete)

  if (images.length) {
    const imageSettled = Promise.all(images.map(image => new Promise(resolve => {
      image.addEventListener('load', resolve, { once: true })
      image.addEventListener('error', resolve, { once: true })
    })))
    const timeout = new Promise(resolve => window.setTimeout(resolve, 1200))
    await Promise.race([imageSettled, timeout])
  }

  await new Promise(resolve => window.requestAnimationFrame(() => window.requestAnimationFrame(resolve)))
}

function showResumeMessage(item) {
  window.clearTimeout(resumeMessageTimer)
  resumeMessage.value = item?.text
    ? `已回到上次阅读位置 · ${item.text}`
    : '已回到上次阅读位置'
  resumeMessageTimer = window.setTimeout(() => {
    resumeMessage.value = ''
  }, 3200)
}

async function restoreReadingPosition() {
  await waitForRichContentLayout()
  refreshOutlineEligibility()
  const stored = readStoredPosition()
  if (!stored || !readingScrollTarget) {
    updateReadingState()
    return
  }

  const sameContent = stored.contentHash === hashString(safeContentHtml.value)
  let matchedItem = outlineItems.value.find(item => item.id === stored.headingId)
  if (!matchedItem && stored.headingText) {
    matchedItem = outlineItems.value.find(item => item.text === stored.headingText)
  }

  let targetTop = 0
  if (matchedItem) {
    const heading = findOutlineElement(matchedItem.id)
    targetTop = elementTopInScrollRoot(heading) + Number(stored.headingOffset || 0)
  } else if (sameContent && Number.isFinite(Number(stored.scrollTop))) {
    targetTop = Number(stored.scrollTop)
  } else {
    targetTop = getMaxScrollTop() * Math.min(1, Math.max(0, Number(stored.ratio || 0)))
  }

  if (targetTop < 80) {
    updateReadingState()
    return
  }

  restoringReadingPosition = true
  if (matchedItem) {
    restoreAnchor = {
      headingId: matchedItem.id,
      headingOffset: Number(stored.headingOffset || 0)
    }
    window.clearTimeout(restoreCorrectionTimer)
    restoreCorrectionTimer = window.setTimeout(clearRestoreCorrection, 8000)
  }
  scrollRootTo(Math.min(targetTop, getMaxScrollTop()), 'auto')
  await new Promise(resolve => window.requestAnimationFrame(resolve))
  restoringReadingPosition = false
  lastScrollTop = getScrollTop()
  updateReadingState()
  scheduleRestoreCorrection()
  showResumeMessage(matchedItem)
}

async function initializeReadingTools() {
  bindReadingScrollRoot()
  await nextTick()
  rebuildOutline()
  contentResizeObserver?.disconnect()
  if (richContentRef.value && typeof ResizeObserver !== 'undefined') {
    contentResizeObserver = new ResizeObserver(() => {
      refreshOutlineEligibility()
      scheduleRestoreCorrection()
      scheduleReadingStateUpdate()
    })
    contentResizeObserver.observe(richContentRef.value)
  }
  await restoreReadingPosition()
}

function resetReadingTools() {
  window.clearTimeout(outlineCloseTimer)
  window.clearTimeout(savePositionTimer)
  window.clearTimeout(resumeMessageTimer)
  if (scrollFrame) window.cancelAnimationFrame(scrollFrame)
  clearRestoreCorrection()
  contentResizeObserver?.disconnect()
  contentResizeObserver = null
  outlineItems.value = []
  outlineEnabled.value = false
  outlineOpen.value = false
  mobileOutlineOpen.value = false
  activeHeadingId.value = ''
  hoveredOutlineId.value = ''
  readingProgress.value = 0
  resumeMessage.value = ''
  showBackToTop.value = false
  upwardScrollDistance = 0
}

function openOutline() {
  window.clearTimeout(outlineCloseTimer)
  outlineOpen.value = true
}

function scheduleOutlineClose() {
  window.clearTimeout(outlineCloseTimer)
  outlineCloseTimer = window.setTimeout(() => {
    outlineOpen.value = false
    hoveredOutlineId.value = ''
  }, 320)
}

function previewOutlineItem(item) {
  window.clearTimeout(outlineCloseTimer)
  hoveredOutlineId.value = item.id
  outlineOpen.value = true
}

function scrollToOutlineItem(item) {
  activeHeadingId.value = item.id
  hoveredOutlineId.value = ''
  outlineOpen.value = false
  mobileOutlineOpen.value = false
  const heading = document.getElementById(item.id) || findOutlineElement(item.id)
  if (!heading) return
  scrollRootTo(elementTopInScrollRoot(heading) - 22, prefersReducedMotion() ? 'auto' : 'smooth')
}

function scrollToTop() {
  showBackToTop.value = false
  upwardScrollDistance = 0
  scrollRootTo(0, prefersReducedMotion() ? 'auto' : 'smooth')
}

function handlePageHide() {
  saveReadingPosition()
  flushTaskBookDwell(true).catch(() => {})
}

function markDwellActive() {
  dwellLastActiveAt = Date.now()
}

function handleDwellVisibility() {
  dwellPageVisible = !document.hidden
  if (dwellPageVisible) markDwellActive()
}

function isDwellActive() {
  return Date.now() - dwellLastActiveAt < 120000
}

async function flushTaskBookDwell(force = false) {
  const dayId = data.value?.dayId
  if (!dayId || !data.value?.hasTrainingDay) return
  const visible = dwellPageVisible
  const active = isDwellActive()
  if (!force && (!visible || !active)) return
  try {
    await reportTaskBookDwell(dayId, {
      sessionId: dwellSessionId,
      visible,
      active: active || force,
      reset: false
    })
  } catch {
    // 驻留统计失败不影响任务书使用
  }
}

function startDwellTracking() {
  stopDwellTracking()
  if (!data.value?.dayId || !data.value?.hasTrainingDay) return
  markDwellActive()
  flushTaskBookDwell(true).catch(() => {})
  dwellTimer = window.setInterval(() => {
    flushTaskBookDwell(false).catch(() => {})
  }, 15000)
}

function stopDwellTracking() {
  if (dwellTimer) {
    window.clearInterval(dwellTimer)
    dwellTimer = 0
  }
}

function isTrainingDetailRoute() {
  return route.name === 'TrainingTaskDetail' || route.name === 'TrainingDayDetail'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const dayId = route.params.dayId || route.query.dayId
    const payload = dayId
      ? await fetchTrainingDayOverview(dayId)
      : await fetchTodayTrainingOverview()
    if (route.params.taskId && payload.hasTrainingDay) {
      const selectedTask = (payload.tasks || []).find(task => String(task.taskId) === String(route.params.taskId))
      if (!selectedTask) throw new Error('当前训练任务不存在或已被调整。')
      payload.primaryTask = selectedTask
      if (selectedTask.latestSubmissionId) {
        const [selectedSubmission, selectedFeedback] = await Promise.all([
          fetchTrainingSubmission(selectedTask.latestSubmissionId),
          fetchTrainingFeedback(selectedTask.latestSubmissionId)
        ])
        payload.submission = selectedSubmission
        payload.feedback = selectedFeedback
      } else {
        payload.submission = {}
        payload.feedback = { feedbackReady: false }
      }
    }
    data.value = payload
    startDwellTracking()
  } catch (loadError) {
    error.value = loadError?.message || '请稍后重试。'
    stopDwellTracking()
  } finally {
    loading.value = false
  }
}

watch(() => route.fullPath, async () => {
  saveReadingPosition()
  flushTaskBookDwell(true).catch(() => {})
  if (!isTrainingDetailRoute()) {
    readingPositionSavedForExit = true
    stopDwellTracking()
    return
  }
  readingPositionSavedForExit = false
  resetReadingTools()
  resetSidePanels()
  await load()
  await initializeReadingTools()
}, { immediate: true })

onBeforeRouteLeave(() => {
  saveReadingPosition()
  flushTaskBookDwell(true).catch(() => {})
  readingPositionSavedForExit = true
})

onMounted(() => {
  window.addEventListener('pagehide', handlePageHide)
  window.addEventListener('keydown', handleUserScrollIntent)
  document.addEventListener('visibilitychange', handleDwellVisibility)
  window.addEventListener('pointerdown', markDwellActive, { passive: true })
  window.addEventListener('keydown', markDwellActive)
  window.addEventListener('scroll', markDwellActive, { passive: true })
})

onBeforeUnmount(() => {
  if (!readingPositionSavedForExit) saveReadingPosition()
  flushTaskBookDwell(true).catch(() => {})
  stopDwellTracking()
  readingScrollTarget?.removeEventListener('scroll', handleReadingScroll)
  readingScrollTarget?.removeEventListener('wheel', handleUserScrollIntent)
  readingScrollTarget?.removeEventListener('touchstart', handleUserScrollIntent)
  readingScrollTarget?.removeEventListener('pointerdown', handleUserScrollIntent)
  window.removeEventListener('pagehide', handlePageHide)
  window.removeEventListener('keydown', handleUserScrollIntent)
  document.removeEventListener('visibilitychange', handleDwellVisibility)
  window.removeEventListener('pointerdown', markDwellActive)
  window.removeEventListener('keydown', markDwellActive)
  window.removeEventListener('scroll', markDwellActive)
  resetReadingTools()
})
</script>

<style scoped>
.training-page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--ds-space-6);
}

.training-head-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.training-countdown {
  display: flex;
  align-items: baseline;
  gap: 6px;
  color: var(--ds-muted);
  font-size: var(--ds-text-label);
  white-space: nowrap;
}

.training-countdown strong {
  color: var(--ds-orange-action);
  font-size: 28px;
  line-height: 1;
}

.training-countdown em {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
  font-style: normal;
}

.training-flow {
  margin-bottom: var(--ds-space-5);
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-lg);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(12px, 2vw, 28px);
  background: var(--ds-surface-solid);
  box-shadow: var(--ds-shadow-soft);
}

.training-flow > div {
  flex: 0 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 9px;
}

.training-flow__connector {
  min-width: 40px;
  max-width: 160px;
  height: 1px;
  flex: 1 1 96px;
  background: var(--ds-line-strong);
}

.training-flow > div > span {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: var(--ds-muted);
  background: var(--ds-surface-soft);
  font-size: 9px;
  font-weight: 900;
}

.training-flow > div.is-active > span {
  color: #fff;
  background: var(--ds-orange-action);
}

.training-flow strong,
.training-flow small {
  display: block;
  white-space: nowrap;
}

.training-flow strong {
  color: var(--ds-ink);
  font-size: 11px;
}

.training-flow small {
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 9px;
}

.training-dashboard {
  display: grid;
  grid-template-columns: minmax(0, 74fr) minmax(0, 26fr);
  gap: clamp(var(--ds-space-4), 1.6vw, var(--ds-space-6));
  align-items: start;
}

.training-dashboard.is-side-rail {
  grid-template-columns: minmax(0, 1fr) 64px;
}

.training-primary,
.training-side {
  display: grid;
  gap: var(--ds-space-5);
}

.training-side {
  position: sticky;
  top: 0;
  max-height: calc(100dvh - var(--workspace-header-height) - (var(--ds-page-margin-y, 40px) * 2));
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}

.training-focus-card,
.training-attachments-card,
.training-submit-card {
  padding: var(--ds-space-6);
}

.training-card-head__actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.training-panel-toggle {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border: 1px solid var(--ds-line);
  border-radius: 9px;
  padding: 0;
  display: grid;
  place-items: center;
  color: var(--ds-muted);
  background: var(--ds-surface-solid);
  cursor: pointer;
}

.training-panel-toggle svg {
  width: 16px;
  height: 16px;
}

.training-panel-toggle:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
}

.training-panel-toggle:focus-visible,
.training-side-restore:focus-visible {
  outline: 2px solid var(--ds-orange-action);
  outline-offset: 2px;
}

.training-side-restore {
  width: 100%;
  min-height: 64px;
  border: 1px solid var(--ds-line);
  padding: 12px 14px;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 18px;
  align-items: center;
  gap: var(--ds-space-3);
  color: var(--ds-ink-2);
  background: var(--ds-surface-solid);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.training-side-restore:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  background: var(--ds-orange-wash);
}

.training-side-restore__icon {
  width: 36px;
  height: 36px;
  position: relative;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
}

.training-side-restore__icon svg {
  width: 18px;
  height: 18px;
}

.training-side-restore__icon em {
  min-width: 16px;
  height: 16px;
  position: absolute;
  top: -5px;
  right: -5px;
  border: 2px solid var(--ds-surface-solid);
  border-radius: var(--ds-radius-pill);
  padding: 0 4px;
  display: grid;
  place-items: center;
  color: var(--ds-surface-solid);
  background: var(--ds-orange-action);
  font-size: 8px;
  font-style: normal;
  font-weight: 800;
  line-height: 1;
}

.training-side-restore__icon em.is-status {
  min-width: 10px;
  width: 10px;
  height: 10px;
  top: -2px;
  right: -2px;
  padding: 0;
}

.training-side-restore__icon em.is-status.is-green {
  background: var(--ds-status-success-fg);
}

.training-side-restore__icon em.is-status.is-red {
  background: var(--ds-btn-danger-fg);
}

.training-side-restore__icon em.is-status.is-yellow {
  background: var(--ds-status-warning-fg);
}

.training-side-restore__copy {
  min-width: 0;
}

.training-side-restore__copy strong,
.training-side-restore__copy small {
  display: block;
}

.training-side-restore__copy strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-label);
}

.training-side-restore__copy small {
  margin-top: 3px;
  overflow: hidden;
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.training-side-restore__expand {
  width: 16px;
  height: 16px;
  color: var(--ds-muted);
}

.training-side.is-rail {
  overflow: visible;
  scrollbar-gutter: auto;
}

.training-side.is-rail .training-side-restore {
  min-height: 56px;
  border-radius: 16px;
  padding: 10px;
  display: grid;
  grid-template-columns: 1fr;
  place-items: center;
}

.training-side.is-rail .training-side-restore__copy,
.training-side.is-rail .training-side-restore__expand {
  display: none;
}

.training-panel-announcement {
  width: 1px;
  height: 1px;
  position: absolute;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

.training-section-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
}

.training-section-title > .training-section-title__step {
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange-action);
  font-size: 10px;
  font-weight: 900;
}

.training-section-title small {
  display: block;
  margin-bottom: 2px;
  color: var(--ds-orange-action);
  font-size: 9px;
  font-weight: 800;
}

.training-section-title h2,
.training-card-head h2 {
  margin: 0;
  color: var(--ds-ink);
  font-size: 17px;
}

.training-task-book__title {
  margin: var(--ds-space-5) 0 var(--ds-space-2);
}

.training-task-book__title > span {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  font-weight: 700;
}

.training-task-book__title h3 {
  margin: 5px 0 0;
  color: var(--ds-ink);
  font-size: clamp(22px, 1.8vw, 28px);
  line-height: 1.28;
  letter-spacing: -0.02em;
  font-weight: 700;
}

.training-task-book__section {
  margin-top: var(--ds-space-5);
  border-top: 1px solid var(--ds-line);
  padding-top: var(--ds-space-5);
}

.training-task-book__section > h4 {
  margin: 0 0 var(--ds-space-3);
  color: var(--ds-ink);
  font-size: 14px;
}

.training-task-book__section.is-summary p,
.training-task-book__fallback {
  margin: 0;
  color: var(--ds-muted);
  font-size: 14px;
  line-height: 1.75;
  white-space: pre-wrap;
}

.training-status-banner {
  min-height: 38px;
  border-radius: var(--ds-radius-md);
  padding: 0 var(--ds-space-4);
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-text-label);
}

.training-status-banner > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.training-status-banner strong {
  font-weight: 700;
}

.training-status-banner.is-orange,
.training-status-banner.is-yellow {
  color: var(--ds-status-warning-fg);
  background: var(--ds-status-warning-bg);
}

.training-status-banner.is-green {
  color: var(--ds-status-success-fg);
  background: var(--ds-status-success-bg);
}

.training-status-banner.is-red {
  color: var(--ds-btn-danger-fg);
  background: var(--ds-btn-danger-bg-hover);
}

.training-rich-content {
  padding: 0;
  color: var(--ds-ink-2);
  font-size: 14px;
  line-height: 1.8;
}

.training-rich-content :deep(p) { margin: 0 0 12px; }
.training-rich-content :deep(p:last-child) { margin-bottom: 0; }
.training-rich-content :deep(h1) { margin: 22px 0 10px; color: var(--ds-ink); font-size: 24px; line-height: 1.35; }
.training-rich-content :deep(h2) { margin: 20px 0 9px; color: var(--ds-ink); font-size: 20px; line-height: 1.4; }
.training-rich-content :deep(h3) { margin: 18px 0 8px; color: var(--ds-ink); font-size: 17px; line-height: 1.45; }
.training-rich-content :deep(h1:first-child),
.training-rich-content :deep(h2:first-child),
.training-rich-content :deep(h3:first-child) { margin-top: 0; }
.training-rich-content :deep(ul),
.training-rich-content :deep(ol) { margin: 10px 0; padding-left: 24px; }
.training-rich-content :deep(blockquote) { margin: 14px 0; border: 1px solid var(--ds-orange-100); border-radius: var(--ds-radius-sm); padding: 11px 14px; background: var(--ds-orange-wash); }
.training-rich-content :deep(a) { color: var(--ds-orange-deep); text-underline-offset: 3px; }
.training-rich-content :deep(img) { max-width: 100%; height: auto; margin: 16px auto; border-radius: var(--ds-radius-md); display: block; box-shadow: 0 6px 20px rgba(31, 35, 41, .09); }
.training-rich-content :deep(span[data-text-color="ink"]) { color: #12141a; }
.training-rich-content :deep(span[data-text-color="muted"]) { color: #6b7280; }
.training-rich-content :deep(span[data-text-color="orange"]) { color: #e84a1c; }
.training-rich-content :deep(span[data-text-color="green"]) { color: #0f9f6e; }
.training-rich-content :deep(span[data-text-color="amber"]) { color: #d98200; }
.training-rich-content :deep(span[data-text-color="red"]) { color: #d83a45; }

.training-submit-card .training-card-head {
  align-items: flex-start;
}

.training-submit-card__heading {
  min-width: 0;
  flex: 1;
  align-items: flex-start;
}

.training-submit-card__heading > div {
  min-width: 0;
}

.training-submit-card__heading > .training-section-title__step {
  margin-top: 1px;
}

.training-submit-card .training-card-head p {
  margin: 5px 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  line-height: 1.5;
}

.training-submit-card__status {
  flex: 0 0 auto;
  border-radius: var(--ds-radius-pill);
  padding: 5px 9px;
  color: var(--ds-orange-action);
  background: var(--ds-orange-wash);
  font-size: var(--ds-text-micro);
  font-weight: 700;
}

.training-learning-reminder {
  margin-top: var(--ds-space-3);
  border: 1px solid var(--ds-orange-100);
  border-radius: var(--ds-radius-md);
  padding: 9px 11px;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
  font-size: 10px;
  line-height: 1.5;
}

.training-submit-lock {
  margin: var(--ds-space-2) 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.6;
}

.training-submit-card__time {
  margin-top: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-line);
  padding-bottom: var(--ds-space-4);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--ds-space-3);
}

.training-submit-card__time span {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
}

.training-submit-card__time strong {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-label);
  text-align: right;
}

.training-submit-card .training-status-banner {
  margin-top: var(--ds-space-4);
}

.training-secondary-tasks svg {
  width: 15px;
}

.training-requirements {
  margin-top: 0;
  display: grid;
  gap: var(--ds-space-4);
}

.training-requirements article {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: start;
  gap: var(--ds-space-3);
}

.training-requirements__signal {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--ds-orange-action);
  box-shadow: 0 0 0 3px var(--ds-orange-wash);
}

.training-requirements__signal.is-optional {
  background: var(--ds-faint);
  box-shadow: 0 0 0 3px var(--ds-input-readonly-bg);
}

.training-requirements strong {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: var(--ds-text-label);
}

.training-requirements p {
  margin: 3px 0 0;
  color: var(--ds-faint);
  font-size: var(--ds-text-micro);
}

.training-requirements article.is-daily-report {
  padding: 12px;
  border: 1px solid rgba(232, 74, 28, 0.22);
  border-radius: 12px;
  background: linear-gradient(180deg, #fffaf7 0%, #fff 70%);
}

.training-requirements article.is-typing-practice {
  padding: 12px;
  border: 1px solid rgba(15, 118, 110, 0.22);
  border-radius: 12px;
  background: linear-gradient(180deg, #f0fdfa 0%, #fff 70%);
}

.training-requirements__badge {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--ds-orange);
  color: #fff;
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}

.training-requirements__badge--typing {
  background: #0f766e;
}

.training-requirements__copy {
  min-width: 0;
  display: grid;
  gap: 8px;
}

.training-requirements__cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--ds-orange);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  text-decoration: none;
}

.training-requirements__cta--typing {
  background: #0f766e;
}

.training-requirements__cta svg {
  width: 14px;
  height: 14px;
}

.training-requirements__cta:hover {
  filter: brightness(1.05);
}

.training-secondary-tasks {
  margin-top: var(--ds-space-4);
  display: grid;
}

.training-secondary-tasks > strong {
  margin-bottom: var(--ds-space-2);
  font-size: var(--ds-text-label);
}

.training-secondary-tasks a {
  min-height: 46px;
  display: grid;
  grid-template-columns: 1fr auto 16px;
  align-items: center;
  gap: var(--ds-space-3);
  color: var(--ds-ink-2);
  font-size: var(--ds-text-label);
  text-decoration: none;
}

.training-secondary-tasks em {
  color: var(--ds-orange-action);
  font-style: normal;
}

.training-submit-card__actions {
  margin-top: var(--ds-space-4);
  display: grid;
  gap: var(--ds-space-2);
}

.training-submit-card__actions :deep(.base-button) {
  width: 100%;
  justify-content: center;
}

.training-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
}

.training-attachments-card .training-card-head__actions > span {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  font-weight: 600;
  line-height: 1;
}

.training-attachment-list {
  margin-top: var(--ds-space-4);
  display: grid;
}

.training-attachment-item {
  border-bottom: 1px solid var(--ds-line);
  padding: var(--ds-space-3) 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: var(--ds-space-2) var(--ds-space-3);
  align-items: center;
}

.training-attachment-item:first-child {
  padding-top: 0;
}

.training-attachment-item:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.training-attachment-item__type {
  width: 36px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
  font-size: 9px;
  font-weight: 800;
}

.training-attachment-item__meta {
  min-width: 0;
}

.training-attachment-item__meta strong,
.training-attachment-item__meta small {
  display: block;
}

.training-attachment-item__meta strong {
  overflow: hidden;
  color: var(--ds-ink-2);
  font-size: var(--ds-text-label);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.training-attachment-item__meta small {
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
}

.training-attachment-item__actions {
  grid-column: 2;
  display: flex;
  gap: var(--ds-space-2);
}

.training-attachment-item__actions button,
.training-attachment-item__actions a {
  min-height: 28px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-pill);
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ds-ink-2);
  background: #fff;
  font: inherit;
  font-size: var(--ds-text-micro);
  font-weight: 700;
  line-height: 1;
  text-decoration: none;
  cursor: pointer;
}

.training-attachment-item__actions button:hover,
.training-attachment-item__actions a:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
}

.training-attachment-item__actions button:focus-visible,
.training-attachment-item__actions a:focus-visible {
  outline: 2px solid var(--ds-orange-action);
  outline-offset: 2px;
}

.training-attachments-card > .training-inline-empty {
  margin-top: var(--ds-space-4);
}

.training-inline-empty {
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-4);
  color: var(--ds-muted);
  background: var(--ds-input-readonly-bg);
  font-size: var(--ds-text-label);
}

.training-rich-content :deep(.training-rich-content__anchor) {
  scroll-margin-top: 22px;
}

.training-document-outline {
  width: 34px;
  height: clamp(320px, 43dvh, 420px);
  position: fixed;
  z-index: 24;
  top: calc(50% + var(--workspace-header-height) / 2);
  left: calc(var(--workspace-sidebar-width) + 10px);
  transform: translateY(-50%);
  transition: width 220ms var(--ds-motion-ease-out);
}

.training-document-outline.is-open {
  width: 300px;
}

.training-document-outline__rail {
  width: 28px;
  height: 100%;
  position: relative;
  border: 0;
  padding: 8px 0 8px 4px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
  color: inherit;
  background: transparent;
  cursor: default;
}

.training-document-outline__rail::before {
  content: none;
}

.training-document-outline__tick {
  width: 28px;
  height: 17px;
  border: 0;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  background: transparent;
  cursor: pointer;
}

.training-document-outline__mark {
  box-sizing: border-box;
  width: 8px;
  height: 3px;
  position: relative;
  z-index: 1;
  border-radius: 1px;
  background: color-mix(in srgb, var(--ds-muted) 42%, transparent);
  box-shadow: none;
  transition:
    width var(--ds-transition),
    height var(--ds-transition),
    background var(--ds-transition),
    box-shadow var(--ds-transition),
    transform var(--ds-transition);
}

.training-document-outline__tick.is-secondary .training-document-outline__mark {
  width: 8px;
  height: 3px;
  background: color-mix(in srgb, var(--ds-muted) 42%, transparent);
}

.training-document-outline__tick.is-active .training-document-outline__mark {
  width: 24px;
  height: 3px;
  background: var(--ds-ink);
  box-shadow: none;
}

.training-document-outline__rail:hover
  .training-document-outline__tick:not(.is-active)
  .training-document-outline__mark {
  background: color-mix(in srgb, var(--ds-muted) 64%, transparent);
}

.training-document-outline__tick:has(+ .training-document-outline__tick.is-active)
  .training-document-outline__mark,
.training-document-outline__tick.is-active
  + .training-document-outline__tick
  .training-document-outline__mark {
  width: 17px;
}

.training-document-outline__tick:has(
    + .training-document-outline__tick + .training-document-outline__tick.is-active
  )
  .training-document-outline__mark,
.training-document-outline__tick.is-active
  + .training-document-outline__tick
  + .training-document-outline__tick
  .training-document-outline__mark {
  width: 12px;
}

.training-document-outline__panel {
  box-sizing: border-box;
  width: 272px;
  max-height: min(640px, calc(100dvh - var(--workspace-header-height) - 48px));
  position: absolute;
  top: 50%;
  left: 28px;
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  padding: 14px;
  display: grid;
  gap: 2px;
  overflow-x: hidden;
  overflow-y: auto;
  opacity: 0;
  pointer-events: none;
  transform: translate(-10px, -50%) scale(.985);
  transform-origin: left center;
  background: var(--ds-surface-solid);
  box-shadow:
    0 24px 56px rgba(31, 35, 41, .14),
    0 2px 10px rgba(31, 35, 41, .05);
  scrollbar-width: thin;
  transition:
    opacity 170ms var(--ds-motion-ease-out),
    transform 240ms var(--ds-motion-ease-out);
}

.training-document-outline.is-open .training-document-outline__panel {
  opacity: 1;
  pointer-events: auto;
  transform: translate(0, -50%) scale(1);
}

.training-document-outline__panel header {
  position: sticky;
  z-index: 2;
  top: -14px;
  margin: -2px -2px 6px;
  padding: 10px 9px 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-3);
  background: var(--ds-surface-solid);
}

.training-document-outline__panel header strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-label);
}

.training-document-outline__panel header span {
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.training-document-outline__panel > button,
.training-mobile-outline-panel > button {
  width: 100%;
  min-height: 38px;
  border: 1px solid transparent;
  border-radius: var(--ds-radius-sm);
  padding: 9px 10px;
  overflow: hidden;
  color: var(--ds-muted);
  background: transparent;
  font: inherit;
  font-size: var(--ds-text-micro);
  line-height: 1.45;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition:
    color 160ms var(--ds-motion-ease-out),
    border-color 160ms var(--ds-motion-ease-out),
    background 160ms var(--ds-motion-ease-out);
}

.training-document-outline__panel > button.is-secondary,
.training-mobile-outline-panel > button.is-secondary {
  padding-left: 26px;
  color: var(--ds-faint);
}

.training-document-outline__panel > button:hover,
.training-mobile-outline-panel > button:hover {
  color: var(--ds-ink);
  background: color-mix(in srgb, var(--ds-surface-soft) 72%, transparent);
}

.training-document-outline__panel > button.is-active,
.training-mobile-outline-panel > button.is-active {
  border-color: var(--ds-orange-100);
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
  font-weight: 800;
}

.training-document-outline__panel > button {
  opacity: 0;
  transform: translateX(-5px);
  transition:
    opacity 160ms var(--ds-motion-ease-out),
    transform 210ms var(--ds-motion-ease-out),
    color 160ms var(--ds-motion-ease-out),
    border-color 160ms var(--ds-motion-ease-out),
    background 160ms var(--ds-motion-ease-out);
}

.training-document-outline.is-open .training-document-outline__panel > button {
  opacity: 1;
  transform: translateX(0);
  transition-delay: calc(45ms + var(--outline-index) * 16ms);
}

.training-document-outline__panel > button:focus-visible,
.training-mobile-outline-trigger:focus-visible,
.training-mobile-outline-panel button:focus-visible,
.training-back-to-top:focus-visible {
  outline: 2px solid var(--ds-orange-action);
  outline-offset: 2px;
}

.training-document-outline__tick:focus-visible {
  outline: none;
}

.training-document-outline__tick:focus-visible .training-document-outline__mark {
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--ds-orange-action) 14%, transparent);
}

.training-mobile-outline-trigger {
  display: none;
}

.training-mobile-outline-backdrop {
  position: fixed;
  z-index: 50;
  inset: 0;
  padding: var(--ds-space-5);
  align-items: flex-end;
  background: rgba(18, 20, 24, .32);
  backdrop-filter: blur(3px);
}

.training-mobile-outline-panel {
  width: 100%;
  max-height: min(70dvh, 620px);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-xl) var(--ds-radius-xl) var(--ds-radius-lg) var(--ds-radius-lg);
  padding: var(--ds-space-4);
  display: grid;
  overflow-y: auto;
  background: var(--ds-surface-solid);
  box-shadow: 0 24px 60px rgba(20, 22, 27, .2);
}

.training-mobile-outline-panel header {
  margin-bottom: var(--ds-space-2);
  padding: 0 var(--ds-space-2) var(--ds-space-3);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
}

.training-mobile-outline-panel header strong,
.training-mobile-outline-panel header span {
  display: block;
}

.training-mobile-outline-panel header strong {
  color: var(--ds-ink);
  font-size: 16px;
}

.training-mobile-outline-panel header span {
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: var(--ds-text-micro);
}

.training-mobile-outline-panel header > button {
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-pill);
  padding: 7px 11px;
  color: var(--ds-ink-2);
  background: var(--ds-surface-solid);
  font: inherit;
  font-size: var(--ds-text-micro);
  font-weight: 700;
}

.training-reading-resume {
  max-width: min(520px, calc(100vw - 40px));
  position: fixed;
  z-index: 48;
  top: calc(var(--workspace-header-height) + 20px);
  left: calc(var(--workspace-sidebar-width) + (100vw - var(--workspace-sidebar-width)) / 2);
  border: 1px solid var(--ds-orange-100);
  border-radius: var(--ds-radius-pill);
  padding: 9px 14px;
  color: var(--ds-orange-deep);
  background: color-mix(in srgb, var(--ds-orange-wash) 92%, #fff);
  box-shadow: 0 10px 28px rgba(89, 43, 27, .1);
  font-size: var(--ds-text-micro);
  font-weight: 700;
  transform: translateX(-50%);
}

.training-back-to-top {
  min-height: 40px;
  position: fixed;
  z-index: 28;
  right: clamp(18px, 2.2vw, 34px);
  bottom: clamp(18px, 2.6vw, 34px);
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-pill);
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--ds-ink-2);
  background: color-mix(in srgb, var(--ds-surface-solid) 96%, transparent);
  box-shadow: 0 12px 30px rgba(31, 35, 41, .14);
  font: inherit;
  font-size: var(--ds-text-micro);
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(8px);
}

.training-back-to-top svg {
  width: 15px;
  height: 15px;
}

.training-back-to-top:hover {
  border-color: var(--ds-btn-secondary-border-hover);
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
}

.training-reading-toast-enter-active,
.training-reading-toast-leave-active,
.training-back-top-enter-active,
.training-back-top-leave-active {
  transition:
    opacity 180ms var(--ds-motion-ease-out),
    transform 180ms var(--ds-motion-ease-out);
}

.training-reading-toast-enter-from,
.training-reading-toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}

.training-back-top-enter-from,
.training-back-top-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 1080px) {
  .training-dashboard {
    grid-template-columns: 1fr;
  }

  .training-dashboard.is-side-rail {
    grid-template-columns: 1fr;
  }

  .training-side {
    position: static;
    top: auto;
    max-height: none;
    overflow: visible;
    grid-template-columns: 1fr;
    scrollbar-gutter: auto;
  }

  .training-side.is-rail {
    grid-template-columns: 1fr 1fr;
  }

  .training-side.is-rail .training-side-restore {
    min-height: 64px;
    border-radius: var(--ds-radius-lg);
    padding: 12px 14px;
    grid-template-columns: 36px minmax(0, 1fr) 18px;
    place-items: center stretch;
  }

  .training-side.is-rail .training-side-restore__copy {
    display: block;
  }

  .training-side.is-rail .training-side-restore__expand {
    display: block;
  }
}

@media (max-width: 900px), (hover: none) {
  .training-document-outline {
    display: none;
  }

  .training-mobile-outline-trigger {
    min-height: 38px;
    position: fixed;
    z-index: 28;
    left: 16px;
    bottom: 18px;
    border: 1px solid var(--ds-card-border);
    border-radius: var(--ds-radius-pill);
    padding: 0 13px;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: var(--ds-ink-2);
    background: color-mix(in srgb, var(--ds-surface-solid) 96%, transparent);
    box-shadow: 0 10px 28px rgba(31, 35, 41, .13);
    font: inherit;
    font-size: var(--ds-text-micro);
    font-weight: 800;
  }

  .training-mobile-outline-trigger svg {
    width: 15px;
    height: 15px;
  }

  .training-mobile-outline-backdrop {
    display: flex;
  }

  .training-reading-resume {
    top: calc(var(--workspace-header-height) + 12px);
    left: 50%;
  }
}

@media (max-width: 720px) {
  .training-flow {
    display: flex;
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  .training-flow__connector {
    display: none;
  }

  .training-flow strong,
  .training-flow small {
    white-space: normal;
  }

  .training-page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .training-head-actions {
    width: 100%;
    justify-content: space-between;
  }

  .training-side {
    grid-template-columns: 1fr;
  }

  .training-side.is-rail {
    grid-template-columns: 1fr;
  }

  .training-status-banner {
    align-items: flex-start;
    flex-wrap: wrap;
    padding-top: var(--ds-space-2);
    padding-bottom: var(--ds-space-2);
  }

  .training-focus-card,
  .training-attachments-card,
  .training-submit-card {
    padding: var(--ds-space-5);
  }

  .training-back-to-top {
    right: 16px;
    bottom: 18px;
  }

  .training-back-to-top span {
    display: none;
  }

  .training-mobile-outline-backdrop {
    padding: var(--ds-space-3);
  }

}

@media (prefers-reduced-motion: reduce) {
  .training-document-outline,
  .training-document-outline__mark,
  .training-document-outline__panel,
  .training-document-outline__panel > button,
  .training-reading-toast-enter-active,
  .training-reading-toast-leave-active,
  .training-back-top-enter-active,
  .training-back-top-leave-active {
    transition: none;
  }
}
</style>
