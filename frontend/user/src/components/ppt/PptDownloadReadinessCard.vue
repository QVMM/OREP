<template>
  <div class="download-readiness-card" :class="status" data-download-readiness-root="true">
    <div class="download-readiness-head">
      <div>
        <span class="quality-eyebrow">下载条件</span>
        <h3>{{ headlineText }}</h3>
        <p>{{ summary }}</p>
        <div class="download-head-stats">
          <span v-if="downloadFlowActive" class="download-head-pill flow">
            下载流程进行中
          </span>
          <span class="download-head-pill primary">
            {{ primaryPillText }}
          </span>
          <span class="download-head-pill">
            已满足 {{ doneCount }}/{{ checklist.length || 0 }}
          </span>
          <span v-if="statusHint" class="download-head-pill subtle">
            {{ statusHint }}
          </span>
        </div>
        <p v-if="downloadFlowActive" class="download-flow-tip">
          你当前是从下载入口进入的，处理完这一项后，系统会继续带你回到下载流程。
        </p>
        <el-button
          v-if="downloadFlowActive"
          size="small"
          text
          class="download-flow-exit"
          @click="$emit('exit-download-flow')"
        >
          先退出下载流程
        </el-button>
      </div>
      <el-button
        size="small"
        :type="status === 'blocked' ? 'warning' : 'primary'"
        plain
        :loading="downloadLoading"
        @click="$emit('download')"
      >
        {{ topDownloadButtonText }}
      </el-button>
    </div>
    <div
      v-if="actionFeedback"
      class="download-action-feedback"
      :class="actionFeedback.type || 'info'"
    >
      <div class="download-action-feedback-copy">
        <span class="download-action-feedback-eyebrow">刚刚处理结果</span>
        <strong>{{ actionFeedback.title || '下载条件已更新' }}</strong>
        <p>{{ actionFeedback.summary }}</p>
        <ul v-if="actionFeedback.points?.length" class="download-action-feedback-points">
          <li v-for="point in actionFeedback.points" :key="point">{{ point }}</li>
        </ul>
      </div>
      <div class="download-action-feedback-actions">
        <el-button
          v-if="actionFeedback.nextPendingItem"
          size="small"
          text
          @click="$emit('handle-item', actionFeedback.nextPendingItem)"
        >
          {{ downloadFlowActive ? '先处理并继续下载' : (actionFeedback.nextPendingItem.actionText || '继续处理下一项') }}
        </el-button>
        <el-button
          v-else-if="status === 'warning' && nextWarningFollowupAction"
          size="small"
          text
          @click="$emit('handle-item', nextWarningFollowupAction)"
        >
          {{ downloadFlowActive ? '先处理并继续下载' : (nextWarningFollowupAction.actionText || '继续补强当前版') }}
        </el-button>
        <el-button
          v-if="status !== 'blocked' || actionFeedback.allowDownload"
          size="small"
          type="primary"
          :loading="downloadLoading"
          @click="$emit('download')"
        >
          {{ feedbackDownloadButtonText }}
        </el-button>
      </div>
    </div>
    <div class="download-readiness-list">
      <div
        v-if="status === 'blocked' && nextPendingItem"
        class="download-next-item"
      >
        <div>
          <span class="download-next-label">建议下一步</span>
          <strong>{{ nextPendingItem.title }}</strong>
          <p>{{ nextPendingItem.detail }}</p>
        </div>
        <el-button
          size="small"
          type="warning"
          plain
          :loading="loadingKey === nextPendingItem.key"
          @click="$emit('handle-item', nextPendingItem)"
        >
          {{ downloadFlowActive ? '先处理并继续下载' : (nextPendingItem.actionText || '继续处理下一项') }}
        </el-button>
      </div>
      <div
        v-else-if="status === 'warning' && nextWarningFollowupAction"
        class="download-next-item warning-followup"
      >
        <div>
          <span class="download-next-label">建议继续补强</span>
          <strong>{{ nextWarningFollowupAction.title }}</strong>
          <p>{{ nextWarningFollowupAction.detail }}</p>
        </div>
        <el-button
          size="small"
          type="warning"
          plain
          @click="$emit('handle-item', nextWarningFollowupAction)"
        >
          {{ downloadFlowActive ? '先处理并继续下载' : (nextWarningFollowupAction.actionText || '继续补强当前版') }}
        </el-button>
      </div>
      <div
        v-for="item in checklist"
        :key="item.key"
        :data-checklist-key="item.key"
        class="download-readiness-item"
        :class="{ done: item.done, pending: !item.done }"
      >
        <div class="download-readiness-copy">
          <strong>{{ item.done ? '已满足' : '未满足' }} · {{ item.title }}</strong>
          <div class="download-progress-line">
            <span>{{ item.progressText }}</span>
            <el-progress
              :percentage="item.progressPercent"
              :status="item.done ? 'success' : undefined"
              :stroke-width="8"
              :show-text="false"
            />
          </div>
          <p>{{ item.detail }}</p>
          <div v-if="!item.done && (item.relatedPoints?.length || item.targetPages?.length)" class="download-inline-assist">
            <div v-if="item.relatedPoints?.length" class="download-inline-group">
              <span class="download-inline-label">当前优先补</span>
              <div class="download-inline-tags">
                <span
                  v-for="point in item.relatedPoints"
                  :key="`${item.key}-${point}`"
                  class="download-inline-tag point"
                >
                  {{ point }}
                </span>
              </div>
            </div>
            <div v-if="item.targetPages?.length" class="download-inline-group">
              <span class="download-inline-label">关联页面</span>
              <div class="download-inline-tags">
                <span
                  v-for="pageIndex in item.targetPages.slice(0, 6)"
                  :key="`${item.key}-page-${pageIndex}`"
                  class="download-inline-tag page"
                >
                  第{{ pageIndex }}页
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="!item.done && item.actionable" class="download-readiness-actions">
          <small class="download-action-hint">
            {{ downloadFlowActive ? '处理完后会继续回到下载流程' : (item.actionHint || '') }}
          </small>
          <el-button
            size="small"
            text
            :loading="loadingKey === item.key"
            @click="$emit('handle-item', item)"
          >
            {{ downloadFlowActive ? '先处理并继续下载' : (item.actionText || '去处理') }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

defineEmits(['download', 'handle-item', 'exit-download-flow'])

const props = defineProps({
  status: { type: String, default: 'unknown' },
  summary: { type: String, default: '' },
  statusHint: { type: String, default: '' },
  warningSuggestionCount: { type: Number, default: 0 },
  checklist: { type: Array, default: () => [] },
  loadingKey: { type: String, default: '' },
  nextPendingItem: { type: Object, default: null },
  actionFeedback: { type: Object, default: null },
  downloadLoading: { type: Boolean, default: false },
  downloadFlowActive: { type: Boolean, default: false },
  nextWarningFollowupAction: { type: Object, default: null }
})

const doneCount = computed(() => props.checklist.filter(item => item?.done).length)
const pendingCount = computed(() => props.checklist.filter(item => !item?.done).length)
const headlineText = computed(() => {
  if (props.status === 'blocked') return '距离可下载还差这些条件'
  if (props.status === 'warning') return '当前版本可下载，但建议继续补强'
  return '当前已满足下载条件'
})

const topDownloadButtonText = computed(() => {
  if (props.status === 'blocked') return props.downloadFlowActive ? '查看并继续下载' : '查看详细条件'
  if (props.status === 'warning') return props.downloadFlowActive ? '继续下载当前版本' : '下载当前版本'
  return props.downloadFlowActive ? '继续下载' : '立即下载'
})

const feedbackDownloadButtonText = computed(() => {
  if (props.status === 'ready') return props.downloadFlowActive ? '继续下载' : '现在下载'
  return props.downloadFlowActive ? '继续下载当前版本' : '下载当前版本'
})

const primaryPillText = computed(() => {
  if (props.status === 'ready') return '已满足下载条件'
  if (props.status === 'warning') {
    return props.warningSuggestionCount
      ? `当前版可下，还差 ${props.warningSuggestionCount} 项建议`
      : '当前版可直接下载'
  }
  return pendingCount.value ? `还差 ${pendingCount.value} 项` : '已全部满足'
})
</script>

<style scoped>
.download-readiness-card {
  margin: 22px 0 0;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid rgba(59, 130, 246, 0.14);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.96));
}

.download-readiness-card.blocked {
  border-color: rgba(248, 113, 113, 0.24);
}

.download-readiness-card.warning {
  border-color: rgba(250, 204, 21, 0.24);
}

.download-readiness-card.ready {
  border-color: rgba(74, 222, 128, 0.24);
}

.download-readiness-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.download-readiness-head h3 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: 26px;
}

.download-readiness-head p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.download-head-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.download-head-pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.download-head-pill.primary {
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
}

.download-head-pill.flow {
  background: rgba(124, 58, 237, 0.12);
  color: #7c3aed;
}

.download-head-pill.subtle {
  background: rgba(250, 204, 21, 0.14);
  color: #b45309;
}

.download-flow-tip {
  margin: 12px 0 0;
  color: #7c3aed;
  font-size: 13px;
  line-height: 1.7;
}

.download-flow-exit {
  margin-top: 8px;
  padding-left: 0;
}

.download-readiness-list {
  display: grid;
  gap: 16px;
}

.download-action-feedback {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  padding: 18px 20px;
  margin-bottom: 16px;
  border-radius: 20px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.95), rgba(248, 250, 252, 0.98));
  align-items: center;
}

.download-action-feedback.success {
  border-color: rgba(34, 197, 94, 0.22);
  background: linear-gradient(135deg, rgba(240, 253, 244, 0.96), rgba(248, 250, 252, 0.98));
}

.download-action-feedback.warning {
  border-color: rgba(245, 158, 11, 0.22);
  background: linear-gradient(135deg, rgba(255, 251, 235, 0.96), rgba(255, 247, 237, 0.98));
}

.download-action-feedback-eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.download-action-feedback-copy strong {
  display: block;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.5;
}

.download-action-feedback-copy p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.7;
}

.download-action-feedback-actions {
  display: grid;
  gap: 10px;
  justify-items: end;
}

.download-action-feedback-points {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #334155;
  line-height: 1.7;
}

.download-next-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 20px;
  border: 1px solid rgba(251, 191, 36, 0.28);
  background: linear-gradient(135deg, rgba(255, 251, 235, 0.95), rgba(255, 247, 237, 0.96));
  align-items: center;
}

.download-next-item.warning-followup {
  border-color: rgba(250, 204, 21, 0.22);
  background: linear-gradient(135deg, rgba(255, 251, 235, 0.92), rgba(255, 255, 255, 0.97));
}

.download-next-label {
  display: inline-block;
  margin-bottom: 8px;
  color: #b45309;
  font-size: 12px;
  font-weight: 800;
}

.download-next-item strong {
  display: block;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.5;
}

.download-next-item p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.7;
}

.download-readiness-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
}

.download-readiness-item.done {
  border-color: rgba(74, 222, 128, 0.28);
  background: rgba(240, 253, 244, 0.92);
}

.download-readiness-item.pending {
  border-color: rgba(251, 191, 36, 0.24);
}

.download-readiness-copy strong {
  display: block;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.5;
}

.download-progress-line {
  margin-top: 12px;
}

.download-progress-line span {
  display: block;
  margin-bottom: 8px;
  color: #2563eb;
  font-weight: 800;
}

.download-readiness-copy p {
  margin: 12px 0 0;
  color: #475569;
  line-height: 1.75;
}

.download-inline-assist {
  margin-top: 14px;
  display: grid;
  gap: 12px;
}

.download-inline-group {
  display: grid;
  gap: 8px;
}

.download-inline-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.download-inline-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.download-inline-tag {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.download-inline-tag.point {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.download-inline-tag.page {
  background: rgba(16, 185, 129, 0.12);
  color: #0f766e;
}

.download-readiness-actions {
  display: grid;
  align-content: center;
  justify-items: end;
  gap: 8px;
}

.download-action-hint {
  color: #64748b;
}

@media (max-width: 980px) {
  .download-readiness-head,
  .download-readiness-item,
  .download-next-item,
  .download-action-feedback {
    grid-template-columns: 1fr;
    display: grid;
  }

  .download-readiness-actions {
    justify-items: start;
  }

  .download-action-feedback-actions {
    justify-items: start;
  }
}
</style>
