<template>
  <div class="student-page">
    <header v-if="!submissionSuccess" class="student-page__head submission-head">
      <div>
        <h1>{{ isNew ? '提交训练成果' : '查看训练成果' }}</h1>
        <p>{{ isNew ? '交付内容、文件和链接都在这里一次提交。' : '查看本次提交内容、文件和审核状态。' }}</p>
      </div>
      <BaseButton type="secondary" :to="backPath"><ArrowLeft /> 返回训练详情</BaseButton>
    </header>

    <section v-if="submissionSuccess" class="student-card submission-success" role="status" aria-live="polite">
      <div class="submission-success__mark" aria-hidden="true">
        <svg viewBox="0 0 64 64" focusable="false">
          <circle cx="32" cy="32" r="27"></circle>
          <path d="m20 32 8 8 17-18"></path>
        </svg>
      </div>
      <span class="submission-success__eyebrow">成果已保存</span>
      <h1>提交成功</h1>
      <p>你的训练成果已同步到协作任务，老师和团队成员可以在同一处查看与审核。</p>
      <div class="submission-success__task">
        <span>本次提交</span>
        <strong>{{ submissionSuccess.taskTitle || task.title || '训练任务成果' }}</strong>
        <small>当前状态 · 待审核</small>
      </div>
      <BaseButton size="large" :to="collaborationSubmissionPath">
        查看提交详情 <ArrowRight />
      </BaseButton>
    </section>

    <section v-else-if="loading" class="student-card student-skeleton">
      <el-skeleton :rows="9" animated />
    </section>
    <section v-else-if="day.locked" class="student-card student-error">
      <div class="student-empty__content">
        <div class="student-empty__icon"><WarningFilled /></div>
        <h2>{{ trainingDayLockLabel(day) || '训练日尚未开放' }}</h2>
        <p>{{ trainingDayLockMessage(day) }}</p>
        <BaseButton :to="backPath">返回训练详情</BaseButton>
      </div>
    </section>

    <section v-else-if="error" class="student-card student-error">
      <div class="student-empty__content">
        <div class="student-empty__icon"><WarningFilled /></div>
        <h2>提交信息暂时没有加载出来</h2>
        <p>{{ error }}</p>
        <BaseButton @click="load">重新加载</BaseButton>
      </div>
    </section>

    <div v-else class="submission-layout">
      <main class="submission-main">
        <section class="student-card submission-task">
          <span class="submission-task__eyebrow">{{ isNew ? '当前任务' : `第 ${submission.versionNo || 1} 次提交` }}</span>
          <h2>{{ task.title || submission.taskTitle }}</h2>
          <p>{{ task.description || submission.taskDescription || '按任务要求提交可检查的训练成果。' }}</p>
        </section>

        <section v-if="isNew && incompleteRequiredLearningCount > 0" class="student-card submission-form">
          <p class="submission-block-note">还有 {{ incompleteRequiredLearningCount }} 项必学内容未完成，请先完成学习再提交。</p>
          <div class="submission-form__actions">
            <BaseButton :to="backPath">返回完成学习</BaseButton>
          </div>
        </section>

        <section v-else-if="isNew" class="student-card submission-form">
          <div class="form-field">
            <label for="submission-content">成果说明</label>
            <textarea
              id="submission-content"
              v-model.trim="form.content"
              class="ds-textarea"
              rows="6"
              placeholder="说明你完成了什么、如何完成，以及希望老师重点看哪里。"
            ></textarea>
          </div>
          <div class="form-field">
            <label for="submission-type">成果类型</label>
            <select id="submission-type" v-model="form.submissionType" class="ds-select">
              <option value="DOCUMENT">文档</option>
              <option value="PPT">演示文稿</option>
              <option value="SCRIPT">讲稿</option>
              <option value="VIDEO">视频</option>
              <option value="CODE">代码</option>
              <option value="DESIGN">设计稿</option>
              <option value="OTHER">其他</option>
            </select>
          </div>
          <div class="form-field">
            <label for="submission-link">成果链接（可选）</label>
            <input id="submission-link" v-model.trim="form.link" class="ds-input" type="url" placeholder="https://">
          </div>
          <div class="form-field">
            <label>成果文件（可选）</label>
            <DropFileUpload
              v-model="selectedFile"
              size="md"
              title="拖拽成果文件到此处，或点击选择"
              hint="提交时自动上传，并保留原文件名和大小"
              accept-hint="支持常见文档、压缩包与演示文稿"
              :disabled="submitting"
              @error="onDropError"
            />
            <p v-if="pendingAsset" class="submission-pending-file">
              已上传待提交：{{ pendingAsset.fileName }}（失败可直接重试，无需重新选择文件）
            </p>
          </div>
          <label class="sync-option">
            <input v-model="form.syncToMaterial" type="checkbox">
            <span>同时保存到资源中心</span>
          </label>
          <div class="submission-form__actions">
            <BaseButton type="secondary" :to="backPath">暂不提交</BaseButton>
            <BaseButton :loading="submitting" @click="submit">
              {{ submitting ? '正在提交…' : '确认提交' }}
              <ArrowRight v-if="!submitting" />
            </BaseButton>
          </div>
        </section>

        <section v-else class="student-card submission-detail">
          <div class="submission-detail__status">
            <span>当前状态</span>
            <strong>{{ submissionStatusLabel(submission.status) }}</strong>
            <small>{{ formatDateTime(submission.submittedAt) }}提交</small>
          </div>
          <div class="submission-detail__block">
            <h2>成果说明</h2>
            <p>{{ submission.content || '本次提交没有填写文字说明。' }}</p>
          </div>
          <div v-if="submission.assets?.length" class="submission-detail__block">
            <h2>成果文件</h2>
            <a v-for="asset in submission.assets" :key="asset.id" :href="asset.fileUrl" target="_blank" rel="noopener">
              <Document />
              <span>
                <strong>{{ asset.fileName || '成果文件' }}</strong>
                <small>{{ formatFileSize(asset.fileSize) }}</small>
              </span>
              <ArrowRight />
            </a>
          </div>
          <div v-if="submission.links?.length" class="submission-detail__block">
            <h2>成果链接</h2>
            <a v-for="link in submission.links" :key="link.id" :href="link.url" target="_blank" rel="noopener">
              <Link />
              <span><strong>{{ link.title || link.url }}</strong></span>
              <ArrowRight />
            </a>
          </div>
        </section>
      </main>

      <aside class="submission-aside">
        <section class="student-card submission-checklist">
          <div class="student-card__head">
            <h2>交付清单</h2>
            <span>{{ requirements.length }} 项</span>
          </div>
          <div v-if="requirements.length">
            <article v-for="item in requirements" :key="item.id">
              <CircleCheck />
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.required ? '必交' : '可选' }}</small>
              </div>
            </article>
          </div>
          <p v-else class="submission-aside__empty">老师暂未拆分交付清单。</p>
        </section>

        <section v-if="!isNew" class="student-card submission-feedback-link">
          <h2>老师反馈</h2>
          <p>{{ submission.feedbackReady ? '老师已经完成反馈，可以查看具体意见。' : '老师反馈后，这里会自动出现提醒。' }}</p>
          <BaseButton
            v-if="submission.feedbackReady"
            :to="`/training/feedback/${submission.submissionId}`"
          >
            查看反馈 <ArrowRight />
          </BaseButton>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  CircleCheck,
  Document,
  Link,
  WarningFilled
} from '@element-plus/icons-vue'
import BaseButton from '../../components/base/BaseButton.vue'
import DropFileUpload from '../../components/base/DropFileUpload.vue'
import {
  fetchTrainingDay,
  fetchTrainingSubmission,
  submitTrainingTask,
  uploadTrainingFile
} from './api'
import { formatDateTime, submissionStatusLabel, trainingDayLockLabel, trainingDayLockMessage } from './format'
import { clearSubmissionDraft, loadSubmissionDraft, saveSubmissionDraft } from './submissionDraft'
import { trackFrontendEvent } from '../../utils/monitor'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const submitting = ref(false)
const submissionSuccess = ref(null)
const day = ref({})
const submission = ref({})
const selectedFile = ref(null)
const form = ref({
  content: '',
  submissionType: 'DOCUMENT',
  link: '',
  syncToMaterial: true
})

const isNew = computed(() => route.params.submissionId === 'new')
const taskId = computed(() => Number(route.query.taskId || submission.value.taskId || 0))
const task = computed(() => {
  if (!isNew.value) return submission.value
  return (day.value.tasks || []).find(item => Number(item.taskId) === taskId.value) || day.value.primaryTask || {}
})
const requirements = computed(() => task.value.requirements || submission.value.requirements || [])
const incompleteRequiredLearningCount = computed(() => {
  if (Number(day.value.incompleteRequiredLearningCount) > 0) {
    return Number(day.value.incompleteRequiredLearningCount)
  }
  return (day.value.learningResources || []).filter((item) => {
    const required = item.required === true || Number(item.required) === 1
    const complete = item.learningStatus === 'COMPLETED' || Number(item.progressPercent) >= 100
    return required && !complete
  }).length
})
const pendingAsset = ref(null)
const backPath = computed(() => {
  const dayId = route.query.dayId || day.value.dayId
  return dayId && taskId.value ? `/training/tasks/${taskId.value}?dayId=${dayId}` : '/training/today'
})
const collaborationSubmissionPath = computed(() => ({
  path: `/project-team/details/task-${submissionSuccess.value?.taskId || taskId.value}`,
  query: {
    teamId: submissionSuccess.value?.teamId || day.value.camp?.teamId || undefined,
    submissionId: submissionSuccess.value?.submissionId || undefined
  }
}))

async function load() {
  submissionSuccess.value = null
  loading.value = true
  error.value = ''
  try {
    if (isNew.value) {
      if (!route.query.dayId || !taskId.value) throw new Error('缺少训练日或任务信息')
      day.value = await fetchTrainingDay(route.query.dayId)
      const draft = loadSubmissionDraft(taskId.value)
      if (draft?.content && !form.value.content) form.value.content = draft.content
      if (draft?.submissionType) form.value.submissionType = draft.submissionType
      if (draft?.link && !form.value.link) form.value.link = draft.link
      if (draft?.pendingAsset?.fileUrl) pendingAsset.value = draft.pendingAsset
    } else {
      submission.value = await fetchTrainingSubmission(route.params.submissionId)
    }
  } catch (loadError) {
    error.value = loadError?.message || '请稍后重试。'
  } finally {
    loading.value = false
  }
}

function onDropError(err) {
  ElMessage.warning(err?.message || '文件不符合要求')
}

function trackSubmit(actionName, detail) {
  trackFrontendEvent({
    source: 'user_frontend',
    actionType: 'training_submit',
    actionName,
    route: window.location.pathname + window.location.search,
    pageTitle: document.title,
    detail
  })
}

async function submit() {
  if (!Number.isFinite(taskId.value) || taskId.value <= 0) {
    ElMessage.warning('缺少训练任务信息，请从训练日重新进入')
    return
  }
  if (day.value.locked) {
    ElMessage.warning(trainingDayLockMessage(day.value) || '训练日尚未开放')
    return
  }
  if (incompleteRequiredLearningCount.value > 0) {
    ElMessage.warning(`还有 ${incompleteRequiredLearningCount.value} 项必学内容未完成，请先完成学习再提交`)
    return
  }
  if (!form.value.content && !form.value.link && !selectedFile.value && !pendingAsset.value) {
    ElMessage.warning('请填写成果说明、添加成果链接或选择成果文件')
    return
  }
  if (selectedFile.value && selectedFile.value.size > 200 * 1024 * 1024) {
    ElMessage.warning('文件较大，将按文件大小延长上传等待时间，请保持页面打开')
  }
  submitting.value = true
  const started = Date.now()
  let stage = 'prepare'
  const hasFile = Boolean(selectedFile.value || pendingAsset.value)
  saveSubmissionDraft(taskId.value, {
    content: form.value.content,
    submissionType: form.value.submissionType,
    link: form.value.link
  })
  try {
    let assets = pendingAsset.value?.fileUrl ? [pendingAsset.value] : []
    if (selectedFile.value) {
      stage = 'upload'
      const uploaded = await uploadTrainingFile(selectedFile.value)
      pendingAsset.value = uploaded
      saveSubmissionDraft(taskId.value, { pendingAsset: uploaded })
      assets = [uploaded]
    }
    const links = form.value.link
      ? [{ title: '成果链接', url: form.value.link, linkType: 'OTHER' }]
      : []
    stage = 'submit'
    const result = await submitTrainingTask(taskId.value, {
      content: form.value.content,
      submissionType: form.value.submissionType,
      syncToMaterial: form.value.syncToMaterial,
      assets,
      links
    })
    const id = result.id || result.submissionId
    if (!id) throw new Error('提交可能已保存，但未返回提交记录。请返回训练详情确认，勿重复连点')
    clearSubmissionDraft(taskId.value)
    pendingAsset.value = null
    if (result.materialSyncFailed) {
      ElMessage.warning('成果已提交，同步到资源中心失败，不影响老师审核')
    }
    submissionSuccess.value = {
      submissionId: id,
      taskId: result.taskId || taskId.value,
      teamId: result.teamId || day.value.camp?.teamId,
      taskTitle: result.taskTitle || task.value.title
    }
    trackSubmit(result.idempotentReuse ? 'submit_reused' : 'submit_ok', {
      taskId: taskId.value,
      httpStatus: 200,
      reason: '',
      costMs: Date.now() - started,
      hasFile,
      stage
    })
  } catch (submitError) {
    trackSubmit('submit_failed', {
      taskId: taskId.value,
      httpStatus: Number(submitError?.response?.status || 0),
      reason: submitError?.message || '提交失败',
      costMs: Date.now() - started,
      hasFile,
      stage
    })
    if (!submitError?.alreadyToasted) {
      ElMessage.error(submitError?.message || '提交失败，请重试')
    }
  } finally {
    submitting.value = false
  }
}

function formatFileSize(bytes) {
  const value = Number(bytes || 0)
  if (!value) return '大小未知'
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

watch(() => route.fullPath, load, { immediate: true })
</script>

<style scoped>
.submission-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.submission-back {
  margin-bottom: 10px;
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: var(--ds-orange-action);
  font-size: var(--ds-text-label);
  font-weight: 700;
  text-decoration: none;
}

.submission-back svg {
  width: 15px;
}

.submission-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--ds-space-5);
  align-items: start;
}

.submission-main,
.submission-aside {
  display: grid;
  gap: var(--ds-space-5);
}

.submission-task,
.submission-form,
.submission-detail,
.submission-checklist,
.submission-feedback-link {
  padding: var(--ds-space-6);
}

.submission-task__eyebrow {
  color: var(--ds-orange-action);
  font-size: var(--ds-text-label);
  font-weight: 700;
}

.submission-task h2 {
  margin: var(--ds-space-3) 0 var(--ds-space-2);
  font-size: var(--ds-text-h2);
}

.submission-task p {
  margin: 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.75;
}

.submission-form {
  display: grid;
  gap: var(--ds-space-5);
}

.submission-block-note,
.submission-pending-file {
  margin: 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.7;
}

.form-field {
  display: grid;
  gap: var(--ds-space-2);
}

.form-field > label {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-body-sm);
  font-weight: 700;
}

.sync-option {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
}

.sync-option input {
  accent-color: var(--ds-orange-action);
}

.sync-option input:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.submission-form__actions {
  padding-top: 6px;
  display: flex;
  justify-content: flex-end;
  gap: var(--ds-space-3);
}

.submission-form__actions svg {
  width: 15px;
}

.submission-form__actions button:disabled {
  cursor: wait;
}

.submission-checklist .student-card__head > span {
  color: var(--ds-faint);
  font-size: var(--ds-text-label);
}

.submission-checklist article {
  min-height: 62px;
  border-top: 1px solid var(--ds-line);
  display: grid;
  grid-template-columns: 20px 1fr;
  align-items: center;
  gap: var(--ds-space-3);
}

.submission-checklist article > svg {
  width: 18px;
  color: var(--ds-green);
}

.submission-checklist strong,
.submission-checklist small {
  display: block;
}

.submission-checklist strong {
  font-size: var(--ds-text-caption);
}

.submission-checklist small {
  margin-top: 4px;
  color: var(--ds-faint);
  font-size: var(--ds-text-micro);
}

.submission-aside__empty {
  margin: var(--ds-space-5) 0 0;
  color: var(--ds-faint);
  font-size: var(--ds-text-label);
}

.submission-feedback-link h2 {
  margin: 0;
  font-size: 17px;
}

.submission-feedback-link p {
  margin: var(--ds-space-3) 0 var(--ds-space-5);
  color: var(--ds-muted);
  font-size: var(--ds-text-label);
  line-height: 1.7;
}

.submission-feedback-link a {
  width: 100%;
}

.submission-feedback-link svg {
  width: 15px;
}

.submission-success {
  width: min(100%, 640px);
  min-height: 520px;
  margin: 48px auto 0;
  padding: 64px 56px;
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}

.submission-success__mark {
  width: 88px;
  height: 88px;
  margin-bottom: 24px;
  color: var(--ds-green, #2e9b67);
}

.submission-success__mark svg {
  width: 100%;
  height: 100%;
  fill: none;
  overflow: visible;
}

.submission-success__mark circle {
  fill: rgba(46, 155, 103, 0.1);
  stroke: currentColor;
  stroke-width: 2.5;
}

.submission-success__mark path {
  stroke: currentColor;
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.submission-success__eyebrow {
  color: var(--ds-green, #2e9b67);
  font-size: var(--ds-text-label);
  font-weight: 700;
}

.submission-success h1 {
  margin: 10px 0 12px;
  color: var(--ds-ink);
  font-size: 30px;
  line-height: 1.2;
}

.submission-success > p {
  max-width: 440px;
  margin: 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.75;
}

.submission-success__task {
  width: min(100%, 430px);
  margin: 30px 0 24px;
  padding: 16px 18px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  display: grid;
  gap: 6px;
  background: var(--ds-input-readonly-bg);
  text-align: left;
}

.submission-success__task span,
.submission-success__task small {
  color: var(--ds-faint);
  font-size: var(--ds-text-label);
}

.submission-success__task strong {
  color: var(--ds-ink);
  font-size: var(--ds-text-body-sm);
  line-height: 1.45;
}

.submission-success > .base-button {
  min-width: 180px;
}

.submission-detail__status {
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-5);
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--ds-space-1) var(--ds-space-5);
  background: var(--ds-input-readonly-bg);
}

.submission-detail__status span,
.submission-detail__status small {
  color: var(--ds-faint);
  font-size: var(--ds-text-label);
}

.submission-detail__status strong {
  color: var(--ds-orange-action);
  font-size: var(--ds-text-body-sm);
}

.submission-detail__block {
  margin-top: 26px;
}

.submission-detail__block h2 {
  margin: 0 0 12px;
  font-size: 15px;
}

.submission-detail__block > p {
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-5);
  color: var(--ds-ink-2);
  background: var(--ds-input-readonly-bg);
  font-size: var(--ds-text-caption);
  line-height: 1.8;
  white-space: pre-wrap;
}

.submission-detail__block > a {
  min-height: 64px;
  border-top: 1px solid var(--ds-line);
  display: grid;
  grid-template-columns: 22px 1fr 18px;
  align-items: center;
  gap: var(--ds-space-3);
  color: var(--ds-ink);
  text-decoration: none;
}

.submission-detail__block > a > svg {
  width: 18px;
  color: var(--ds-orange-action);
}

.submission-detail__block > a strong,
.submission-detail__block > a small {
  display: block;
}

.submission-detail__block > a strong {
  font-size: var(--ds-text-caption);
}

.submission-detail__block > a small {
  margin-top: 4px;
  color: var(--ds-faint);
  font-size: var(--ds-text-micro);
}

@media (max-width: 900px) {
  .submission-layout {
    grid-template-columns: 1fr;
  }

  .submission-success {
    min-height: 460px;
    margin-top: 24px;
    padding: 48px 24px;
  }
}
</style>
