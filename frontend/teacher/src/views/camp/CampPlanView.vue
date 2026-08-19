<template>
  <div class="daily-plan-page" :class="{ 'teacher-page': !embedded, 'is-embedded': embedded }">
    <header v-if="!embedded" class="teacher-page__head plan-head">
      <div>
        <h1>训练营 · 计划</h1>
        <p>
          {{ projectTitle }} · {{ campTitle }}
          <span v-if="dateRangeLabel !== '— 至 —'"> · {{ dateRangeLabel }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button
          v-if="progressDay"
          type="button"
          class="teacher-btn teacher-btn--secondary"
          @click="jumpToday"
        >
          定位今天
        </button>
        <button
          v-if="selected"
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="saving || !canPublish"
          @click="save(true)"
        >
          {{ saving ? '发布中…' : '发布任务' }}
        </button>
      </div>
    </header>

    <!-- 嵌入工作台时：操作条贴在内容上方，避免重复页标题 -->
    <div v-if="embedded && hasCamp && days.length" class="plan-embed-toolbar">
      <p class="plan-embed-toolbar__tip">选中一天后编辑内容，点「发布任务」学生端才会看到。</p>
      <div class="plan-embed-toolbar__actions">
        <button
          v-if="progressDay"
          type="button"
          class="teacher-btn teacher-btn--secondary teacher-btn--sm"
          @click="jumpToday"
        >
          定位今天
        </button>
        <button
          v-if="selected"
          type="button"
          class="teacher-btn teacher-btn--primary teacher-btn--sm"
          :disabled="saving || !canPublish"
          @click="save(true)"
        >
          {{ saving ? '发布中…' : '发布任务' }}
        </button>
      </div>
    </div>

    <p v-if="notice" class="plan-notice" :class="{ 'is-error': error }" aria-live="polite">{{ notice }}</p>
    <section v-if="loading" class="teacher-card teacher-empty">正在读取训练计划…</section>

    <section v-else-if="!embedded && (!hasCamp || !days.length)" class="teacher-card empty-plan">
      <h2>还没有可编辑的训练计划</h2>
      <p>请先创建训练营并生成逐日草稿。创建后会自动进入「计划」编排。</p>
      <router-link class="teacher-btn teacher-btn--primary" to="/camp/create">创建训练营</router-link>
    </section>

    <section v-else-if="embedded && (!hasCamp || !days.length)" class="teacher-card empty-plan">
      <h2>暂无训练日草稿</h2>
      <p>当前训练营还没有可编辑的训练日，请检查营期是否已生成。</p>
    </section>

    <template v-else>
      <div class="plan-layout">
        <!-- 左侧：每日队列列表 -->
        <aside class="plan-queue teacher-card" aria-label="每日队列">
          <header class="plan-queue__head">
            <div>
              <strong>每日队列</strong>
              <small>共 {{ totalDays }} 天</small>
              <button
                v-if="embedded && hasCamp"
                type="button"
                class="plan-extend-btn"
                @click="$emit('extend-days')"
              >
                延长天数
              </button>
            </div>
            <div class="plan-queue__filters" role="tablist" aria-label="筛选状态">
              <button
                v-for="f in queueFilters"
                :key="f.key"
                type="button"
                role="tab"
                :aria-selected="queueFilter === f.key"
                :class="{ 'is-active': queueFilter === f.key }"
                @click="queueFilter = f.key"
              >
                {{ f.label }}
              </button>
            </div>
          </header>
          <div class="plan-queue__list">
            <button
              v-for="day in filteredQueueDays"
              :key="day.dayNo"
              type="button"
              class="queue-item"
              :class="{ 'is-active': day.dayNo === selectedDayNo }"
              @click="selectDayNo(day.dayNo)"
            >
              <span class="queue-item__day">
                <em v-if="relativeLabel(day.dayNo)">{{ relativeLabel(day.dayNo) }}</em>
                <strong>第 {{ day.dayNo }} 天</strong>
              </span>
              <span class="queue-item__meta">
                <time>{{ formatMd(day.trainingDate) }}</time>
                <i :data-status="uiStatus(day)">{{ statusLabelUi(day) }}</i>
              </span>
              <small class="queue-item__title">{{ dayCardTitle(day) }}</small>
            </button>
            <p v-if="!filteredQueueDays.length" class="queue-empty">该筛选下没有训练日</p>
          </div>
        </aside>

        <!-- 右侧：当日编辑 -->
        <article v-if="selected" class="plan-editor teacher-card">
        <header class="plan-editor__head">
          <div>
            <h2>
              第 {{ selected.dayNo }} 天
              <template v-if="form.title"> · {{ form.title }}</template>
            </h2>
            <p>{{ formatDate(selected.trainingDate) }} · 保存和发布只影响当前训练日</p>
          </div>
          <div class="plan-editor__head-side">
            <button type="button" class="teacher-link text-button" @click="previewStudent">预览学生端</button>
            <span class="plan-status" :data-status="uiStatus(selected)">{{ statusLabelUi(selected) }}</span>
          </div>
        </header>

        <div class="plan-editor__body">
          <!-- ① 今天做什么 -->
          <section class="plan-block" id="plan-core">
            <header class="plan-block__head">
              <div>
                <strong>① 今天做什么</strong>
                <small>主题 + 列表摘要 + 富文本任务说明</small>
              </div>
            </header>
            <div class="plan-block__body plan-core">
              <div class="plan-core__top">
                <label class="plan-field plan-field--grow">
                  <span>训练主题 <i>*</i></span>
                  <input
                    v-model.trim="form.title"
                    :placeholder="`填写第 ${selected.dayNo} 天训练主题`"
                    maxlength="160"
                  />
                </label>
                <label class="plan-field plan-field--inline">
                  <span>截止时间</span>
                  <input v-model="form.deadline" type="time" />
                </label>
              </div>

              <label class="plan-field">
                <span>列表摘要 <i>*</i></span>
                <textarea
                  v-model.trim="form.summary"
                  rows="2"
                  placeholder="一句话摘要，出现在工作台、日程列表等处"
                />
              </label>

              <div class="plan-field plan-field--rich">
                <div class="plan-field__label-row">
                  <span>任务说明（富文本）</span>
                  <small>学生详情页主内容 · 支持标题、列表、图片、Word 图文粘贴</small>
                </div>
                <TrainingRichTextEditor ref="richEditor" v-model="form.contentHtml" />
              </div>

              <p class="plan-core__hint">默认面向 {{ projectTitle }} 全体成员</p>
            </div>
          </section>

          <!-- ② 学习资料 -->
          <section class="plan-block" id="plan-learning">
            <header class="plan-block__head">
              <div>
                <strong>② 学习资料</strong>
                <small>可选 · {{ learningHint }}</small>
              </div>
            </header>
            <div class="plan-block__body">
              <TrainingLearningResourcesEditor
                v-if="selected?.dayId"
                v-model="form.learningResources"
                :day-id="selected.dayId"
                compact
              />
              <div v-else class="teacher-empty">请先选择训练日</div>
            </div>
          </section>

          <!-- ③ 学生交什么 -->
          <section class="plan-block" id="plan-submit">
            <header class="plan-block__head">
              <div>
                <strong>③ 学生交什么</strong>
                <small>发布前至少完整一项</small>
              </div>
              <div class="plan-block__head-actions">
                <button
                  type="button"
                  class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                  :disabled="hasDailyReportTask"
                  :title="hasDailyReportTask ? '已添加日报任务' : '一键加入：学生去写今日日报'"
                  @click="addDailyReportTask"
                >
                  {{ hasDailyReportTask ? '✓ 已加日报' : '+ 提交日报' }}
                </button>
                <button
                  type="button"
                  class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                  :disabled="hasTypingPracticeTask"
                  :title="hasTypingPracticeTask ? '已添加打字任务' : '一键加入：学生去完成打字练习'"
                  @click="addTypingPracticeTask"
                >
                  {{ hasTypingPracticeTask ? '✓ 已加打字' : '+ 打字练习' }}
                </button>
                <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="addTask">
                  + 添加任务
                </button>
              </div>
            </header>
            <div class="plan-block__body">
              <div class="submit-list">
                <section
                  v-for="(task, index) in form.tasks"
                  :key="task.key"
                  class="submit-card"
                  :class="{
                    'is-daily-report': isDailyReportTask(task),
                    'is-typing-practice': isTypingPracticeTask(task)
                  }"
                >
                  <header class="submit-card__head">
                    <strong>
                      任务 {{ index + 1 }}
                      <em v-if="isDailyReportTask(task)" class="submit-card__badge">日报</em>
                      <em v-else-if="isTypingPracticeTask(task)" class="submit-card__badge submit-card__badge--typing">打字</em>
                    </strong>
                    <div class="submit-card__actions">
                      <label class="submit-required">
                        <input v-model="task.required" type="checkbox" />
                        {{ task.required ? '必交' : '选交' }}
                      </label>
                      <button
                        v-if="form.tasks.length > 1"
                        type="button"
                        class="submit-delete"
                        aria-label="删除任务"
                        @click="removeTask(index)"
                      >
                        删除
                      </button>
                    </div>
                  </header>
                  <div class="submit-card__body">
                    <template v-if="isDailyReportTask(task)">
                      <label class="plan-field">
                        <span>任务标题</span>
                        <input v-model.trim="task.title" placeholder="提交今日日报" />
                      </label>
                      <label class="plan-field">
                        <span>说明</span>
                        <input v-model.trim="task.description" placeholder="学生在日报中心填写并提交" />
                      </label>
                      <p class="daily-report-hint">
                        学生端将显示「去写今日日报」按钮，跳转到日报页填写图文日报（可插图），无需在此选择文件格式。
                      </p>
                    </template>
                    <template v-else-if="isTypingPracticeTask(task)">
                      <label class="plan-field">
                        <span>任务标题</span>
                        <input v-model.trim="task.title" placeholder="完成今日打字练习" />
                      </label>
                      <label class="plan-field">
                        <span>说明</span>
                        <input v-model.trim="task.description" placeholder="请练习打字至少 20 分钟" />
                      </label>
                      <p class="daily-report-hint typing-practice-hint">
                        学生端将显示「去打字练习」按钮；任务说明请写清「练习打字 20 分钟」，无需选择文件格式。
                      </p>
                    </template>
                    <template v-else>
                      <label class="plan-field">
                        <span>任务标题</span>
                        <input v-model.trim="task.title" placeholder="例如：运行环境截图" />
                      </label>
                      <label class="plan-field">
                        <span>说明</span>
                        <input v-model.trim="task.description" placeholder="学生需要提交什么" />
                      </label>
                      <div class="plan-field">
                        <span>接受格式</span>
                        <div class="format-presets">
                          <button
                            v-for="preset in formatPresets"
                            :key="preset.key"
                            type="button"
                            class="format-preset"
                            :class="{ 'is-active': isPresetActive(task, preset) }"
                            @click="applyPreset(task, preset)"
                          >
                            {{ preset.label }}
                          </button>
                          <button
                            type="button"
                            class="format-preset format-preset--more"
                            :class="{ 'is-active': task.showMoreFormats }"
                            @click="task.showMoreFormats = !task.showMoreFormats"
                          >
                            更多
                          </button>
                        </div>
                        <div v-if="task.showMoreFormats" class="format-chips">
                          <button
                            v-for="fmt in allFormats"
                            :key="fmt"
                            type="button"
                            class="format-chip"
                            :class="{ 'is-active': task.formats.includes(fmt) }"
                            @click="toggleFormat(task, fmt)"
                          >
                            {{ fmt }}
                          </button>
                        </div>
                        <small v-if="task.formats.length" class="format-selected">
                          已选：{{ task.formats.join('、') }}
                        </small>
                      </div>
                    </template>
                  </div>
                </section>
                <div v-if="!form.tasks.length" class="submit-empty">
                  <p>还没有提交任务。可一键加「日报」「打字练习」，或添加普通文件提交任务。</p>
                  <div class="submit-empty__actions">
                    <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="addDailyReportTask">
                      + 提交日报
                    </button>
                    <button type="button" class="teacher-btn teacher-btn--primary teacher-btn--sm" @click="addTypingPracticeTask">
                      + 打字练习
                    </button>
                    <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="addTask">
                      添加提交任务
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <footer class="plan-editor__footer">
          <p class="plan-footer-hint">
            <template v-if="!canPublish">
              {{ publishBlockReason }}
            </template>
            <template v-else>
              主题、说明与提交任务已就绪，可发布给学生
            </template>
          </p>
          <div class="plan-footer-actions">
            <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="saving" @click="save(false)">
              {{ isPublished ? '保存修改' : '保存草稿' }}
            </button>
            <button
              type="button"
              class="teacher-btn teacher-btn--primary"
              :disabled="saving || !canPublish"
              @click="save(true)"
            >
              {{ saving ? '处理中…' : '发布任务' }}
            </button>
          </div>
        </footer>
      </article>

        <section v-else class="plan-editor teacher-card plan-editor--empty">
          <div class="teacher-empty">请从左侧选择一个训练日</div>
        </section>
      </div>
    </template>

    <StudentDayPreviewModal
      v-model:open="previewOpen"
      :day-no="selected?.dayNo || selectedDayNo"
      :title="form.title"
      :summary="form.summary"
      :content-html="form.contentHtml"
      :deadline="form.deadline"
      :training-date="selected?.trainingDate || ''"
      :project-name="projectTitle"
      :camp-name="campTitle"
      :learning-resources="form.learningResources"
      :tasks="form.tasks"
    />
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import TrainingRichTextEditor from '../../components/training/TrainingRichTextEditor.vue'
import TrainingLearningResourcesEditor from '../../components/training/TrainingLearningResourcesEditor.vue'
import StudentDayPreviewModal from '../../components/training/StudentDayPreviewModal.vue'
import {
  fetchTeacherCamp,
  updateTeacherTrainingDay,
  uploadTeacherTrainingDayImage,
  uploadTeacherTrainingDayAttachment,
  reorderTeacherTrainingDayAttachments,
} from '../../api'
import { useTeacherContextStore } from '../../stores/context'

const FORMAT_PRESETS = [
  { key: 'image', label: '图片', formats: ['PNG', 'JPG', 'JPEG'] },
  { key: 'doc', label: '文档', formats: ['PDF', 'Word', 'PPT', 'Excel'] },
  { key: 'pdf', label: 'PDF', formats: ['PDF'] },
  { key: 'any', label: '任意文件', formats: ['PDF', 'Word', 'PPT', 'Excel', 'PNG', 'JPG', 'ZIP'] },
]

const ALL_FORMATS = [
  'PDF', 'Word', 'PPT', 'Excel',
  'JPG', 'JPEG', 'PNG', 'WEBP', 'GIF',
  'MP4', 'MOV', 'AVI', 'WEBM',
  'MP3', 'WAV', 'M4A',
  'ZIP', 'RAR', '7Z',
]

function planStatusUi(status) {
  const s = String(status || '').toUpperCase()
  if (s === 'PUBLISHED') return 'published'
  if (s === 'CLOSED') return 'withdrawn'
  if (s === 'DRAFT') return 'draft'
  return 'unplanned'
}

const props = defineProps({
  /** 嵌入「训练营」工作台时隐藏独立页头，空状态由外壳处理 */
  embedded: { type: Boolean, default: false },
  campIdProp: { type: [String, Number], default: '' },
  reloadNonce: { type: Number, default: 0 },
})

defineEmits(['extend-days'])

const route = useRoute()
const ctx = useTeacherContextStore()

const loading = ref(true)
const saving = ref(false)
const notice = ref('')
const error = ref(false)
const previewOpen = ref(false)
const selectedDayNo = ref(1)
const queueFilter = ref('all')
const queueFilters = [
  { key: 'all', label: '全部' },
  { key: 'published', label: '已发布' },
  { key: 'draft', label: '草稿' },
  { key: 'unplanned', label: '未规划' },
]
const progressDay = ref(0)
const days = ref([])
const campMeta = ref({ name: '', startDate: '', endDate: '', totalDays: 0, campId: null, teamId: null })
const richEditor = ref(null)
const hasCamp = ref(false)

const form = reactive({
  title: '',
  summary: '',
  contentHtml: '',
  deadline: '22:00',
  submitTarget: 'all',
  tasks: [],
  learning: [],
  learningResources: [],
  attachments: [],
})

const formatPresets = FORMAT_PRESETS
const allFormats = ALL_FORMATS
const totalDays = computed(() => days.value.length || campMeta.value.totalDays || 0)
const selected = computed(() => days.value.find((d) => d.dayNo === selectedDayNo.value) || days.value[0] || null)
const campTitle = computed(() => campMeta.value.name || ctx.campName || '训练营')
const projectTitle = computed(() => ctx.projectName || '未选择项目')
const dateRangeLabel = computed(() => {
  const s = formatDate(campMeta.value.startDate)
  const e = formatDate(campMeta.value.endDate)
  if (s === '—' && e === '—') return '— 至 —'
  return `${s} 至 ${e}`
})

const filteredQueueDays = computed(() => {
  const list = days.value || []
  if (queueFilter.value === 'all') return list
  return list.filter((d) => uiStatus(d) === queueFilter.value)
})

const isPublished = computed(() => uiStatus(selected.value) === 'published')
const hasDailyReportTask = computed(() => form.tasks.some((t) => isDailyReportTask(t)))
const hasTypingPracticeTask = computed(() => form.tasks.some((t) => isTypingPracticeTask(t)))
const incompleteTaskCount = computed(() =>
  form.tasks.filter((t) => {
    if (!t.title.trim()) return true
    // 日报 / 打字练习不要求文件格式
    if (isDailyReportTask(t) || isTypingPracticeTask(t)) return !String(t.description || '').trim()
    return !t.description.trim() || !(t.formats || []).length
  }).length
)
const canPublish = computed(() =>
  Boolean(form.title.trim() && form.summary.trim() && form.tasks.some((t) => t.title.trim()) && incompleteTaskCount.value === 0)
)
const learningHint = computed(() => {
  const n = form.learningResources?.length || 0
  return n ? `已添加 ${n} 项` : '未添加'
})
const publishBlockReason = computed(() => {
  if (!form.title.trim()) return '请填写训练主题'
  if (!form.summary.trim()) return '请填写简短说明'
  if (!form.tasks.length) return '请至少添加一项提交任务'
  if (incompleteTaskCount.value) return `还有 ${incompleteTaskCount.value} 项提交任务未填完整（标题、说明、格式）`
  return '完善后即可发布'
})

function uiStatus(day) {
  if (!day) return 'unplanned'
  if (day.planStatus) return planStatusUi(day.planStatus)
  const s = String(day.status || '').toUpperCase()
  if (s === 'PUBLISHED') return 'published'
  if (s === 'CLOSED') return 'withdrawn'
  if (!day.title && s === 'DRAFT') return day.summary || day.requirements?.length ? 'draft' : 'unplanned'
  if (s === 'DRAFT') return day.title ? 'draft' : 'unplanned'
  return planStatusUi(s)
}

function statusLabelUi(day) {
  return ({ unplanned: '未规划', draft: '草稿', published: '已发布', withdrawn: '已撤回' })[uiStatus(day)] || '草稿'
}

function dayCardTitle(day) {
  if (uiStatus(day) === 'unplanned') return '待规划'
  return day.title || '主题待填写'
}

function relativeLabel(dayNo) {
  if (!progressDay.value) return ''
  if (dayNo === progressDay.value - 1) return '昨天'
  if (dayNo === progressDay.value) return '今天'
  if (dayNo === progressDay.value + 1) return '明天'
  return ''
}

function formatDate(value) {
  return value ? String(value).slice(0, 10) : '—'
}

function formatMd(value) {
  const s = formatDate(value)
  return s.length >= 10 ? s.slice(5) : s
}

function sameFormats(a = [], b = []) {
  if (a.length !== b.length) return false
  const sa = [...a].map((x) => String(x).toUpperCase()).sort()
  const sb = [...b].map((x) => String(x).toUpperCase()).sort()
  return sa.every((v, i) => v === sb[i])
}

function isPresetActive(task, preset) {
  return sameFormats(task.formats, preset.formats)
}

function applyPreset(task, preset) {
  task.formats = [...preset.formats]
  task.formatCategory = preset.key === 'image' ? 'image' : preset.key === 'any' ? 'common' : 'common'
  task.showMoreFormats = false
}

function isDailyReportTask(task = {}) {
  const asset = String(task.assetType || task.asset_type || '').toUpperCase()
  if (asset === 'DAILY_REPORT') return true
  const title = String(task.title || '')
  return /日报/.test(title) && asset === 'LINK'
}

function isTypingPracticeTask(task = {}) {
  const asset = String(task.assetType || task.asset_type || '').toUpperCase()
  if (asset === 'TYPING_PRACTICE') return true
  const title = String(task.title || '')
  return /打字练习|打字任务/.test(title) && (asset === 'LINK' || !asset)
}

function isSpecialSubmitTask(task = {}) {
  return isDailyReportTask(task) || isTypingPracticeTask(task)
}

function taskModel(item = {}) {
  const assetType = String(item.assetType || item.asset_type || '').toUpperCase() || null
  const isReport = assetType === 'DAILY_REPORT' || isDailyReportTask(item)
  const isTyping = !isReport && (assetType === 'TYPING_PRACTICE' || isTypingPracticeTask(item))
  let resolvedAsset = assetType || null
  if (isReport) resolvedAsset = 'DAILY_REPORT'
  else if (isTyping) resolvedAsset = 'TYPING_PRACTICE'
  return {
    key: item.key || `${Date.now()}-${Math.random()}`,
    title: item.title || '',
    description: item.description || '',
    required: item.required !== false,
    assetType: resolvedAsset,
    formats: (isReport || isTyping)
      ? []
      : [...(item.formats || (assetType ? formatsFromAssetType(assetType) : ['PDF']))],
    formatCategory: item.formatCategory || 'common',
    showMoreFormats: false,
  }
}

function fillForm(day) {
  if (!day) return
  form.title = day.title || ''
  form.summary = day.summary || day.goal || ''
  form.contentHtml = day.contentHtml || ''
  form.deadline = day.deadline || (day.dueAt ? String(day.dueAt).slice(11, 16) : '22:00')
  form.submitTarget = 'all'
  form.attachments = (day.attachments || []).map((a) => ({ ...a }))
  form.learningResources = (day.learningResources || []).map((item) => ({ ...item }))
  if (day.tasks?.length) {
    form.tasks = day.tasks.map(taskModel)
  } else if (day.requirements?.length) {
    form.tasks = day.requirements.map((r) =>
      taskModel({
        title: r.title,
        description: r.description,
        required: r.required,
        assetType: r.assetType,
        formats: ['DAILY_REPORT', 'TYPING_PRACTICE'].includes(String(r.assetType || '').toUpperCase())
          ? []
          : (r.formats || formatsFromAssetType(r.assetType)),
      })
    )
  } else {
    // 未规划日默认一条空任务，减少一步点击
    form.tasks = [taskModel({ required: true, formats: ['PNG', 'JPG', 'JPEG'] })]
  }
  form.learning = (day.learning || []).map((item) => ({ ...item }))
}

function selectDayNo(dayNo) {
  selectedDayNo.value = dayNo
  const day = days.value.find((d) => d.dayNo === dayNo)
  fillForm(day)
  notice.value = ''
  error.value = false
}

function jumpToday() {
  const target = progressDay.value || days.value[0]?.dayNo
  if (target) {
    queueFilter.value = 'all'
    selectDayNo(target)
  }
}

function addTask() {
  form.tasks.push(taskModel({ required: true, formats: ['PNG', 'JPG', 'JPEG'] }))
}

function addDailyReportTask() {
  if (hasDailyReportTask.value) {
    notice.value = '已存在日报任务，无需重复添加'
    error.value = false
    return
  }
  // 若仅有一条空白默认任务，替换为日报；否则追加
  const onlyBlank = form.tasks.length === 1
    && !form.tasks[0].title.trim()
    && !isSpecialSubmitTask(form.tasks[0])
  const reportTask = taskModel({
    title: '提交今日日报',
    description: '打开日报中心，填写今天做了什么、卡点与明天计划（支持图文），提交后红点消失。',
    required: true,
    assetType: 'DAILY_REPORT',
    formats: [],
  })
  if (onlyBlank) form.tasks = [reportTask]
  else form.tasks.push(reportTask)
  notice.value = '已加入「提交今日日报」任务，保存/发布后学生可见'
  error.value = false
}

function addTypingPracticeTask() {
  if (hasTypingPracticeTask.value) {
    notice.value = '已存在打字练习任务，无需重复添加'
    error.value = false
    return
  }
  const onlyBlank = form.tasks.length === 1
    && !form.tasks[0].title.trim()
    && !isSpecialSubmitTask(form.tasks[0])
  const typingTask = taskModel({
    title: '完成今日打字练习',
    description: '打开打字练习页，今日请连续练习打字至少 20 分钟（可配合指法提示与计时）。完成后回到任务页确认。',
    required: true,
    assetType: 'TYPING_PRACTICE',
    formats: [],
  })
  if (onlyBlank) form.tasks = [typingTask]
  else form.tasks.push(typingTask)
  notice.value = '已加入「完成今日打字练习」（需练习 20 分钟），保存/发布后学生可见'
  error.value = false
}

function removeTask(index) {
  form.tasks.splice(index, 1)
}

function toggleFormat(task, fmt) {
  if (task.formats.includes(fmt)) task.formats = task.formats.filter((f) => f !== fmt)
  else task.formats = [...task.formats, fmt]
}

function previewStudent() {
  previewOpen.value = true
}

async function save(publish) {
  if (!selected.value) return
  if (publish && !canPublish.value) {
    error.value = true
    notice.value = publishBlockReason.value
    return
  }

  saving.value = true
  notice.value = ''
  error.value = false

  try {
    if (!selected.value?.dayId || String(selected.value.dayId).startsWith('mock-')) {
      error.value = true
      notice.value = '当前没有可保存的真实训练日，请先创建训练营'
      return
    }

    let contentHtml = form.contentHtml || ''
    const pendingImages = richEditor.value?.getPendingImages?.() || []
    for (const image of pendingImages) {
      const uploaded = await uploadTeacherTrainingDayImage(selected.value.dayId, image.file)
      contentHtml = contentHtml.split(image.localUrl).join(uploaded.url)
    }
    form.contentHtml = contentHtml
    richEditor.value?.setHtml?.(contentHtml)
    richEditor.value?.clearPendingImages?.()

    for (let index = 0; index < form.attachments.length; index += 1) {
      const attachment = form.attachments[index]
      if (!attachment.file) continue
      const uploaded = await uploadTeacherTrainingDayAttachment(selected.value.dayId, attachment.file)
      form.attachments.splice(index, 1, { ...uploaded, localKey: `server-${uploaded.id}` })
    }
    const attachmentIds = form.attachments.map((item) => item.id).filter(Boolean)
    if (attachmentIds.length) await reorderTeacherTrainingDayAttachments(selected.value.dayId, attachmentIds)

    const dueAt = form.deadline
      ? `${String(selected.value.trainingDate).slice(0, 10)}T${form.deadline}:00`
      : null

    const tasksToSave = form.tasks.filter((t) => t.title.trim())
    const updated = await updateTeacherTrainingDay(selected.value.dayId, {
      title: form.title,
      summary: form.summary,
      contentHtml,
      dueAt,
      status: publish ? 'PUBLISHED' : selected.value.status,
      requirements: tasksToSave.map((task) => ({
        required: task.required,
        title: task.title,
        description: task.description,
        assetType: isDailyReportTask(task)
          ? 'DAILY_REPORT'
          : isTypingPracticeTask(task)
            ? 'TYPING_PRACTICE'
            : assetTypeFromFormats(task.formats),
      })),
    })
    const target = days.value.find((day) => day.dayId === selected.value.dayId)
    if (target) {
      Object.assign(target, updated, {
        planStatus: publish ? 'published' : uiStatus({ ...target, ...updated, planStatus: undefined }),
        title: form.title,
        summary: form.summary,
        tasks: tasksToSave.map(taskModel),
      })
      if (publish) target.planStatus = 'published'
      else if (String(updated?.status || target.status).toUpperCase() !== 'PUBLISHED') target.planStatus = 'draft'
    }
    fillForm(target || selected.value)
    notice.value = publish
      ? `第 ${selected.value.dayNo} 天已发布，学生端现已可见`
      : `第 ${selected.value.dayNo} 天已保存`
  } catch (err) {
    error.value = true
    notice.value = err?.response?.data?.message || err?.message || '保存失败'
  } finally {
    saving.value = false
  }
}

function formatsFromAssetType(assetType) {
  const t = String(assetType || 'FILE').toUpperCase()
  if (t === 'DAILY_REPORT' || t === 'TYPING_PRACTICE') return []
  if (t === 'VIDEO') return ['MP4', 'MOV']
  if (t === 'AUDIO') return ['MP3', 'WAV']
  if (t === 'IMAGE') return ['PNG', 'JPG', 'JPEG']
  if (t === 'LINK') return []
  return ['PDF', 'Word']
}

function categoryFromAssetType(assetType) {
  const t = String(assetType || 'FILE').toUpperCase()
  if (t === 'VIDEO') return 'video'
  if (t === 'AUDIO') return 'audio'
  if (t === 'IMAGE') return 'image'
  return 'common'
}

function assetTypeFromFormats(formats = []) {
  const list = (formats || []).map((f) => String(f).toUpperCase())
  if (list.some((f) => ['MP4', 'MOV', 'AVI', 'WEBM'].includes(f))) return 'VIDEO'
  if (list.some((f) => ['MP3', 'WAV', 'M4A', 'AAC'].includes(f))) return 'AUDIO'
  if (list.some((f) => ['PNG', 'JPG', 'JPEG', 'WEBP', 'GIF'].includes(f))) return 'IMAGE'
  return 'FILE'
}

function clearPlan(message = '', isError = false) {
  hasCamp.value = false
  days.value = []
  campMeta.value = { name: '', startDate: '', endDate: '', totalDays: 0, campId: null, teamId: null }
  progressDay.value = 0
  selectedDayNo.value = 1
  if (message) {
    notice.value = message
    error.value = isError
  }
}

async function load() {
  loading.value = true
  notice.value = ''
  error.value = false
  try {
    const campId = props.campIdProp || route.query.campId || ctx.campId || ''
    const data = await fetchTeacherCamp(campId)
    if (data?.hasCamp && data.days?.length) {
      hasCamp.value = true
      days.value = data.days.map((day) => ({
        ...day,
        planStatus: planStatusUi(day.status),
        deadline: day.dueAt ? String(day.dueAt).slice(11, 16) : '22:00',
        tasks: (day.requirements || []).map((r) =>
          taskModel({
            title: r.title,
            description: r.description || '',
            required: r.required !== false,
            assetType: r.assetType,
            formats: ['DAILY_REPORT', 'TYPING_PRACTICE'].includes(String(r.assetType || '').toUpperCase())
              ? []
              : formatsFromAssetType(r.assetType),
            formatCategory: categoryFromAssetType(r.assetType),
          })
        ),
        learning: [],
        learningResources: day.learningResources || [],
      }))
      campMeta.value = {
        name: data.camp?.campName || ctx.campName,
        startDate: data.camp?.startDate,
        endDate: data.camp?.endDate,
        totalDays: data.camp?.totalDays || days.value.length,
        campId: data.camp?.campId,
        teamId: data.camp?.teamId,
      }
      progressDay.value = Number(data.camp?.currentDay) || days.value[0]?.dayNo || 1
      const preferTomorrow = route.query.day === 'tomorrow'
      const targetNo = preferTomorrow ? progressDay.value + 1 : progressDay.value
      const current =
        days.value.find((d) => d.dayNo === targetNo) ||
        days.value.find((d) => d.dayNo === progressDay.value) ||
        days.value[0]
      selectDayNo(current.dayNo)
    } else {
      clearPlan(
        props.embedded
          ? ''
          : '当前还没有训练营或训练日。请先创建训练营。',
        false
      )
    }
  } catch (err) {
    clearPlan(err?.response?.data?.message || err?.message || '训练计划加载失败', true)
  } finally {
    loading.value = false
  }
}

watch(
  [() => props.campIdProp, () => route.query.campId, () => route.query.day, () => ctx.campId, () => props.reloadNonce],
  load,
  { immediate: true }
)
</script>

<style scoped>
.daily-plan-page {
  max-width: none;
  width: 100%;
  padding-bottom: 28px;
}
.daily-plan-page.is-embedded {
  padding-bottom: 8px;
}
.plan-embed-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  margin-bottom: 12px;
  padding: 10px 14px;
  border: 1px solid var(--ds-line, #e4e4e7);
  border-radius: 12px;
  background: #fff;
}
.plan-embed-toolbar__tip {
  margin: 0;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
}
.plan-embed-toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plan-head h1 {
  margin: 0;
}

.plan-notice {
  margin: 0 0 12px;
  padding: 11px 14px;
  border-radius: 11px;
  color: #0b7753;
  background: #e5f6ef;
  font-size: 12px;
  font-weight: 700;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}

.empty-plan {
  padding: 40px 24px;
  text-align: center;
}
.empty-plan h2 {
  margin: 0 0 8px;
}
.empty-plan p {
  margin: 0 0 18px;
  color: var(--ds-muted);
}

/* —— 左队列 + 右编辑（自适应） —— */
.plan-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  min-height: 0;
}

.plan-queue {
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 12px;
  align-self: start;
  max-height: min(78vh, 860px);
  overflow: hidden;
}
.plan-queue__head {
  flex: 0 0 auto;
  padding: 12px 12px 8px;
  border-bottom: 1px solid rgba(29, 29, 31, 0.06);
  display: grid;
  gap: 10px;
}
.plan-queue__head strong {
  display: block;
  font-size: 14px;
}
.plan-queue__head small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--ds-muted);
  font-weight: 600;
}
.plan-extend-btn {
  margin-top: 6px;
  height: 26px;
  padding: 0 8px;
  border: 1px solid var(--ds-line);
  border-radius: 7px;
  background: #fff;
  color: var(--ds-ink);
  font: 700 11px/1 var(--ds-font-sans);
  cursor: pointer;
}
.plan-extend-btn:hover {
  border-color: var(--ds-orange);
  color: var(--ds-orange-deep);
}
.plan-queue__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.plan-queue__filters button {
  height: 26px;
  padding: 0 8px;
  border: 1px solid var(--ds-line);
  border-radius: 999px;
  background: #fff;
  font: 700 11px var(--ds-font-sans);
  color: var(--ds-ink-2);
  cursor: pointer;
}
.plan-queue__filters button.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.plan-queue__list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px;
  display: grid;
  gap: 6px;
  align-content: start;
  overscroll-behavior-y: auto;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}
.plan-queue__list::-webkit-scrollbar {
  width: 8px;
}
.plan-queue__list::-webkit-scrollbar-thumb {
  background: rgba(24, 24, 27, 0.18);
  border-radius: 999px;
}
.plan-queue__list::-webkit-scrollbar-thumb:hover {
  background: rgba(232, 74, 28, 0.45);
}
.queue-item {
  width: 100%;
  display: grid;
  gap: 3px;
  padding: 10px 10px;
  border: 1px solid var(--ds-line);
  border-radius: 11px;
  background: #fafbfc;
  text-align: left;
  cursor: pointer;
  color: inherit;
  font: inherit;
  transition: border-color 0.15s, background 0.15s;
}
.queue-item:hover {
  border-color: rgba(232, 74, 28, 0.28);
  background: #fff;
}
.queue-item.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  box-shadow: inset 3px 0 0 var(--ds-orange);
}
.queue-item__day {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
}
.queue-item__day em {
  font-style: normal;
  font-size: 11px;
  font-weight: 800;
  color: var(--ds-orange);
}
.queue-item__day strong {
  font-size: 13px;
  color: var(--ds-ink);
}
.queue-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 11px;
  color: var(--ds-muted);
}
.queue-item__meta i {
  font-style: normal;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  background: #eef0f2;
  color: #5f656d;
}
.queue-item__meta i[data-status='published'] {
  background: var(--ds-green-soft);
  color: var(--ds-green);
}
.queue-item__meta i[data-status='draft'] {
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.queue-item__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ds-faint);
  font-size: 11px;
}
.queue-empty {
  margin: 12px 4px;
  font-size: 12px;
  color: var(--ds-muted);
  text-align: center;
}

/* —— 编辑器 —— */
.plan-editor {
  overflow: hidden;
  min-width: 0;
}
.plan-editor--empty {
  min-height: 200px;
  display: grid;
  place-items: center;
}
.plan-editor__head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(29, 29, 31, 0.06);
}
.plan-editor__head h2 {
  margin: 0;
  font-size: 17px;
  line-height: 1.35;
}
.plan-editor__head p {
  margin: 6px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}
.plan-editor__head-side {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
}
.text-button {
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}
.plan-status {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  background: #f1f2f4;
  color: #5f656d;
}
.plan-status[data-status='published'] {
  background: var(--ds-green-soft);
  color: var(--ds-green);
}
.plan-status[data-status='draft'] {
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}

.plan-editor__body {
  display: grid;
  gap: 0;
}

.plan-block {
  border-bottom: 1px solid rgba(29, 29, 31, 0.06);
}
.plan-block:last-of-type {
  border-bottom: 0;
}
.plan-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px 0;
}
.plan-block__head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.plan-block__head strong {
  display: block;
  font-size: 14px;
}
.plan-block__head small {
  display: block;
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: 12px;
}
.plan-block__body {
  padding: 14px 18px 18px;
}

.plan-core {
  display: grid;
  gap: 14px;
}
.plan-core__top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px;
  gap: 12px;
  align-items: end;
}
.plan-core__hint {
  margin: 0;
  color: var(--ds-faint);
  font-size: 12px;
}
.plan-field--grow {
  min-width: 0;
}
.plan-field--rich {
  gap: 8px;
}
.plan-field__label-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
}
.plan-field__label-row > span {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.plan-field__label-row small {
  color: var(--ds-faint);
  font-size: 12px;
  font-weight: 500;
}
/* 富文本在单页里常显，高度适中可写长文 */
.plan-field--rich :deep(.rich-editor) {
  height: min(560px, 58vh);
  min-height: 360px;
}

.plan-field {
  display: grid;
  gap: 7px;
  min-width: 0;
}
.plan-field > span {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.plan-field > span i {
  color: var(--ds-orange);
  font-style: normal;
}
.plan-field input,
.plan-field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--ds-input-border, var(--ds-line-strong));
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
  color: var(--ds-ink);
  font: inherit;
  font-size: 14px;
}
.plan-field textarea {
  resize: vertical;
  min-height: 64px;
  line-height: 1.55;
}
.plan-field input:focus,
.plan-field textarea:focus {
  outline: none;
  border-color: var(--ds-orange);
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.12);
}
.plan-field--inline {
  width: 160px;
}
.plan-field--inline input {
  min-height: 40px;
}

/* 提交任务 */
.submit-list {
  display: grid;
  gap: 12px;
}
.submit-card {
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}
.submit-card.is-daily-report,
.submit-card.is-typing-practice {
  border-color: rgba(232, 74, 28, 0.28);
  background: linear-gradient(180deg, #fffaf7 0%, #fff 48%);
}
.submit-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(29, 29, 31, 0.05);
  background: #fafafa;
}
.submit-card.is-daily-report .submit-card__head,
.submit-card.is-typing-practice .submit-card__head {
  background: #fff4ee;
}
.submit-card__head strong {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.submit-card__badge {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--ds-orange);
  color: #fff;
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}
.submit-card__badge--typing {
  background: #0f766e;
}
.daily-report-hint,
.typing-practice-hint {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 12px;
  line-height: 1.5;
}
.typing-practice-hint {
  background: #f0fdfa;
  color: #115e59;
}
.submit-card__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.submit-required {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
  cursor: pointer;
}
.submit-delete {
  border: 0;
  background: transparent;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.submit-delete:hover {
  color: #a33a24;
}
.submit-card__body {
  display: grid;
  gap: 12px;
  padding: 12px;
}
.submit-empty {
  padding: 20px;
  border: 1px dashed var(--ds-line-strong);
  border-radius: 12px;
  text-align: center;
}
.submit-empty p {
  margin: 0 0 12px;
  color: var(--ds-muted);
  font-size: 13px;
}
.submit-empty__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.format-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.format-preset {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 999px;
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-ink-2);
  cursor: pointer;
}
.format-preset:hover {
  border-color: rgba(232, 74, 28, 0.35);
}
.format-preset.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.format-preset--more {
  color: var(--ds-muted);
}
.format-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.format-chip {
  min-height: 28px;
  padding: 0 9px;
  border: 1px solid var(--ds-line);
  border-radius: 8px;
  background: #f6f7f8;
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
  cursor: pointer;
}
.format-chip.is-active {
  border-color: rgba(232, 74, 28, 0.4);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.format-selected {
  display: block;
  margin-top: 8px;
  color: var(--ds-faint);
  font-size: 12px;
}

/* 底栏 */
.plan-editor__footer {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 18px;
  border-top: 1px solid var(--ds-line);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
}
.plan-footer-hint {
  margin: 0;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.45;
  max-width: 52%;
}
.plan-footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .plan-layout {
    grid-template-columns: 1fr;
  }
  .plan-queue {
    position: static;
    max-height: none;
  }
  .plan-queue__list {
    display: flex;
    flex-direction: row;
    gap: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 10px;
    scroll-snap-type: x proximity;
  }
  .queue-item {
    flex: 0 0 min(220px, 72vw);
    scroll-snap-align: start;
  }
}

@media (max-width: 720px) {
  .plan-core__top {
    grid-template-columns: 1fr;
  }
  .plan-field--inline {
    width: 100%;
  }
  .plan-field--rich :deep(.rich-editor) {
    height: min(480px, 55vh);
    min-height: 300px;
  }
  .plan-editor__head {
    flex-direction: column;
  }
  .plan-footer-hint {
    max-width: none;
  }
  .plan-editor__footer {
    flex-direction: column;
    align-items: stretch;
  }
  .plan-footer-actions {
    width: 100%;
  }
  .plan-footer-actions .teacher-btn {
    flex: 1;
  }
}
</style>
