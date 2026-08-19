<template>
  <div class="student-page">
    <header class="student-page__head">
      <div>
        <h1>老师反馈</h1>
        <p>只呈现审核结论、具体意见和下一步修改方向。</p>
      </div>
      <BaseButton type="secondary" :to="`/training/submissions/${route.params.submissionId}`">
        <ArrowLeft /> 返回提交详情
      </BaseButton>
    </header>

    <section v-if="loading" class="student-card student-skeleton">
      <el-skeleton :rows="7" animated />
    </section>
    <section v-else-if="error" class="student-card student-error">
      <div class="student-empty__content">
        <div class="student-empty__icon"><WarningFilled /></div>
        <h2>反馈暂时没有加载出来</h2>
        <p>{{ error }}</p>
        <BaseButton @click="load">重新加载</BaseButton>
      </div>
    </section>
    <section v-else-if="!data.feedbackReady" class="student-card student-empty">
      <div class="student-empty__content">
        <div class="student-empty__icon"><Clock /></div>
        <h2>老师还没有完成反馈</h2>
        <p>本次成果已经提交，老师审核完成后会在这里显示具体意见。</p>
        <BaseButton type="secondary" :to="`/training/submissions/${route.params.submissionId}`">查看提交内容</BaseButton>
      </div>
    </section>
    <div v-else class="feedback-layout">
      <section class="student-card feedback-result">
        <div class="feedback-result__icon" :class="{ 'is-approved': data.status === 'APPROVED' }">
          <CircleCheck v-if="data.status === 'APPROVED'" />
          <EditPen v-else />
        </div>
        <span>审核结论</span>
        <h2>{{ submissionStatusLabel(data.status) }}</h2>
        <p>{{ data.taskTitle }}</p>
        <div class="feedback-meta">
          <div><span>反馈老师</span><strong>{{ data.reviewerName || '指导老师' }}</strong></div>
          <div><span>反馈时间</span><strong>{{ formatDateTime(data.reviewedAt) }}</strong></div>
          <div><span>提交版本</span><strong>第 {{ data.versionNo }} 次</strong></div>
        </div>
      </section>
      <section class="student-card feedback-comment">
        <div class="student-card__head">
          <h2>具体反馈</h2>
        </div>
        <blockquote>{{ data.reviewComment || '老师已完成审核，但没有填写补充说明。' }}</blockquote>
        <div class="feedback-actions">
          <BaseButton type="secondary" :to="`/training/submissions/${data.submissionId}`">查看原提交</BaseButton>
          <BaseButton v-if="data.status !== 'APPROVED'" to="/training/today">
            返回训练任务 <ArrowRight />
          </BaseButton>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  CircleCheck,
  Clock,
  EditPen,
  WarningFilled
} from '@element-plus/icons-vue'
import BaseButton from '../../components/base/BaseButton.vue'
import { fetchTrainingFeedback } from './api'
import { formatDateTime, submissionStatusLabel } from './format'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref({})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchTrainingFeedback(route.params.submissionId)
  } catch (loadError) {
    error.value = loadError?.message || '请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.feedback-back {
  margin-bottom: 10px;
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: var(--ds-orange-action);
  font-size: var(--ds-text-label);
  font-weight: 700;
  text-decoration: none;
}

.feedback-back svg {
  width: 15px;
}

.feedback-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: var(--ds-space-5);
  align-items: start;
}

.feedback-result,
.feedback-comment {
  padding: var(--ds-space-6);
}

.feedback-result {
  text-align: center;
}

.feedback-result__icon {
  width: 58px;
  height: 58px;
  margin: 0 auto var(--ds-space-5);
  border-radius: var(--ds-radius-lg);
  display: grid;
  place-items: center;
  color: var(--ds-orange-action);
  background: var(--ds-orange-wash);
}

.feedback-result__icon.is-approved {
  color: var(--ds-status-success-fg);
  background: var(--ds-status-success-bg);
}

.feedback-result__icon svg {
  width: 27px;
}

.feedback-result > span {
  color: var(--ds-faint);
  font-size: var(--ds-text-label);
}

.feedback-result h2 {
  margin: var(--ds-space-2) 0;
  font-size: var(--ds-text-h2);
}

.feedback-result > p {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
}

.feedback-meta {
  margin-top: var(--ds-space-6);
  display: grid;
}

.feedback-meta > div {
  min-height: 58px;
  border-top: 1px solid var(--ds-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-4);
}

.feedback-meta span {
  color: var(--ds-faint);
  font-size: var(--ds-text-label);
}

.feedback-meta strong {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-caption);
}

.feedback-comment blockquote {
  min-height: 230px;
  margin: var(--ds-space-5) 0 0;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-6);
  color: var(--ds-ink-2);
  background: var(--ds-input-readonly-bg);
  font-size: var(--ds-text-body);
  line-height: 1.9;
  white-space: pre-wrap;
}

.feedback-actions {
  margin-top: var(--ds-space-5);
  display: flex;
  justify-content: flex-end;
  gap: var(--ds-space-3);
}

.feedback-actions svg {
  width: 15px;
}

@media (max-width: 800px) {
  .feedback-layout {
    grid-template-columns: 1fr;
  }
}
</style>
