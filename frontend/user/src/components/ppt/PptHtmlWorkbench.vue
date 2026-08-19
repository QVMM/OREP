<template>
  <aside class="speaker-panel">
    <div class="speaker-panel-head">
      <span class="quality-eyebrow">预览调整工作台</span>
      <el-tag size="small" :type="qualityTagType">
        {{ qualityTagText }}
      </el-tag>
    </div>
    <h3>{{ title }}</h3>

    <div class="workbench-score-grid">
      <div>
        <span>质量分</span>
        <strong>{{ qualityScore }}</strong>
      </div>
      <div>
        <span>待处理</span>
        <strong>{{ issueCount }}</strong>
      </div>
      <div>
        <span>生成拦截</span>
        <strong>{{ gateCount }}</strong>
      </div>
      <div>
        <span>结构提醒</span>
        <strong>{{ sequenceCount }}</strong>
      </div>
    </div>

    <div class="speaker-meta">
      <span>页面目标</span>
      <strong>{{ pageGoal }}</strong>
    </div>

    <div v-if="templateChips.length" class="workbench-card">
      <strong>版式合同</strong>
      <div class="workbench-tags">
        <el-tag v-for="chip in templateChips" :key="chip" size="small" effect="plain">
          {{ chip }}
        </el-tag>
      </div>
    </div>

    <div v-if="practiceRows.length" class="workbench-card practice-contract-card">
      <strong>实操闭环</strong>
      <dl>
        <template v-for="row in practiceRows" :key="row.label">
          <dt>{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </template>
      </dl>
    </div>

    <div class="speaker-script">
      <div class="script-title">
        <strong>本页讲稿</strong>
        <span>建议控制 60 分钟总节奏下的单页表达</span>
      </div>
      <p v-if="pageScript">{{ pageScript }}</p>
      <p v-else class="is-empty">该页暂未沉淀讲稿，建议在质量报告中修复“讲稿可用”问题。</p>
    </div>

    <div v-if="actionFeedback" class="workbench-card action-feedback-card" :class="actionFeedback.type">
      <strong>{{ actionFeedback.title }}</strong>
      <p>{{ actionFeedback.summary }}</p>
      <ul v-if="actionFeedback.points?.length" class="action-feedback-list">
        <li v-for="point in actionFeedback.points" :key="point">{{ point }}</li>
      </ul>
      <div v-if="actionFeedback.nextPendingItem || actionFeedback.allowDownload" class="action-feedback-actions">
        <el-button
          v-if="actionFeedback.nextPendingItem"
          size="small"
          text
          @click="$emit('handle-feedback-item', actionFeedback.nextPendingItem)"
        >
          {{ downloadFlowActive ? '先处理并继续下载' : (actionFeedback.nextPendingItem.actionText || '继续补强下一项') }}
        </el-button>
        <el-button
          v-if="actionFeedback.allowDownload"
          size="small"
          type="primary"
          plain
          @click="$emit('download-from-feedback')"
        >
          {{ actionFeedback.title?.includes('直接下载') ? '继续下载' : (downloadFlowActive ? '继续下载当前版本' : '下载当前版本') }}
        </el-button>
      </div>
    </div>

    <div v-if="failedMessages.length" class="speaker-risks">
      <strong>当前页风险</strong>
      <p v-for="issue in failedMessages.slice(0, 4)" :key="issue">{{ issue }}</p>
    </div>

    <div v-if="gateItems.length" class="workbench-card gate-mini-card">
      <strong>生成期门禁记录</strong>
      <p v-for="item in gateItems.slice(0, 2)" :key="item.key || item.text || item.title">
        {{ item.text }}
      </p>
    </div>

    <div v-if="sequenceEvents.length" class="workbench-card sequence-mini-card">
      <strong>结构顺序提醒</strong>
      <p v-for="event in sequenceEvents.slice(0, 2)" :key="event.key || event.text || event.message">
        {{ event.text }}
      </p>
    </div>

    <div v-if="evidenceHints.length" class="workbench-card evidence-mini-card">
      <strong>素材证据提醒</strong>
      <p v-for="hint in evidenceHints" :key="hint">{{ hint }}</p>
    </div>

    <div class="workbench-card inline-material-card">
      <div class="inline-material-head">
        <div>
          <strong>当前页补图</strong>
          <p v-if="materialTask">
            第{{ materialTask.page_index }}页「{{ materialTask.page_title }}」
          </p>
          <p v-else>当前页没有明确缺图任务，也可以直接补系统截图、结果图或政策截图。</p>
        </div>
        <el-button
          v-if="materialTask"
          size="small"
          type="primary"
          plain
          @click="$emit('prepare-inline-material')"
        >
          按本页缺口预填
        </el-button>
      </div>

      <div v-if="materialTask?.required_assets?.length" class="inline-material-tags">
        <span v-for="asset in materialTask.required_assets.slice(0, 4)" :key="asset">{{ asset }}</span>
      </div>

      <p v-if="materialTask?.summary" class="inline-material-summary">
        {{ materialTask.summary }}
      </p>

      <div v-if="linkedAssets.length" class="inline-material-linked">
        <label>已确认绑定素材</label>
        <div class="inline-material-tags linked">
          <button
            v-for="asset in linkedAssets.slice(0, 3)"
            :key="asset.id || asset.filename"
            type="button"
            class="inline-binding-chip confirmed"
            @click="$emit('clear-current-page-binding', asset)"
          >
            {{ asset.filename || `素材 ${asset.id}` }}
            <em>移除本页</em>
          </button>
        </div>
      </div>

      <div v-if="recommendedAssets.length" class="inline-material-linked">
        <label>推荐绑定到当前页</label>
        <div class="inline-material-tags linked">
          <button
            v-for="asset in recommendedAssets.slice(0, 3)"
            :key="`recommended-${asset.id || asset.filename}`"
            type="button"
            class="inline-binding-chip"
            @click="$emit('confirm-current-page-binding', asset)"
          >
            {{ asset.filename || `素材 ${asset.id}` }}
            <em>确认到本页</em>
          </button>
        </div>
      </div>

      <div v-if="relatedMaterialTasks.length" class="inline-material-task-drawer">
        <div class="inline-material-task-head">
          <div>
            <label>相关补图任务</label>
            <p>直接在当前页看清楚哪几页还缺图，点任务就会把上传表单预填好。</p>
          </div>
          <el-button size="small" text @click="$emit('toggle-inline-tasks')">
            {{ showInlineTasks ? '收起' : '展开' }}
          </el-button>
        </div>
        <div v-show="showInlineTasks" class="inline-material-task-list">
          <button
            v-for="taskItem in relatedMaterialTasks"
            :key="`inline-${taskItem.key}`"
            type="button"
            class="inline-material-task-item"
            :class="{ active: Number(taskItem.page_index) === Number(currentPageIndex), ready: taskItem.status === 'ready' }"
            @click="$emit('select-material-task', taskItem)"
          >
            <div class="inline-material-task-top">
              <span>第{{ taskItem.page_index }}页</span>
              <strong>{{ taskItem.status === 'ready' ? '已补齐' : '待上传' }}</strong>
            </div>
            <p>{{ taskItem.summary }}</p>
          </button>
        </div>
      </div>

      <div class="inline-material-form">
        <el-select :model-value="materialAssetType" placeholder="素材类型" @update:model-value="$emit('update:materialAssetType', $event)">
          <el-option label="政策官网截图" value="policy_screenshot" />
          <el-option label="政策文件材料" value="policy_document" />
          <el-option label="系统截图" value="screenshot" />
          <el-option label="设备照片" value="image" />
          <el-option label="数据图表" value="chart" />
          <el-option label="视频关键帧" value="video_frame" />
          <el-option label="文档材料" value="document" />
        </el-select>
        <el-select :model-value="linkedStepId" clearable placeholder="绑定实操步骤（可选）" @update:model-value="$emit('update:linkedStepId', $event)">
          <el-option
            v-for="step in practiceSteps"
            :key="step.step_id"
            :label="`${step.step_order}. ${step.step_title}`"
            :value="step.step_id"
          />
        </el-select>
        <el-input
          :model-value="materialDescription"
          type="textarea"
          :rows="2"
          :placeholder="materialDescriptionPlaceholder"
          @update:model-value="$emit('update:materialDescription', $event)"
        />
        <el-upload
          class="inline-material-upload"
          drag
          action=""
          :http-request="httpUpload"
          :show-file-list="false"
          :disabled="materialUploading"
          accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv"
        >
          <el-icon class="material-upload-icon"><Upload /></el-icon>
          <div class="el-upload__text">直接给当前页拖图或点击上传</div>
        </el-upload>
      </div>
    </div>

    <div class="speaker-actions">
      <div class="speaker-primary-action">
        <span class="quality-eyebrow">当前推荐动作</span>
        <strong>{{ primaryAction.label }}</strong>
        <p>{{ primaryAction.hint }}</p>
      </div>
      <el-button
        size="small"
        type="primary"
        :plain="primaryAction.mode !== 'quality'"
        @click="$emit('primary-action')"
      >
        {{ primaryAction.label }}
      </el-button>
    </div>

    <div class="speaker-secondary-actions">
      <el-button size="small" text @click="$emit('view-quality')">
        查看质量
      </el-button>
      <el-button size="small" text @click="$emit('repair-history')">
        修复历史
      </el-button>
      <el-button size="small" text @click="$emit('toggle-inline-tasks')">
        {{ showInlineTasks ? '收起补图任务' : '展开补图任务' }}
      </el-button>
      <el-button size="small" text @click="$emit('open-material-workspace')">
        高级素材台
      </el-button>
    </div>
  </aside>
</template>

<script setup>
import { Upload } from '@element-plus/icons-vue'

const emit = defineEmits([
  'prepare-inline-material',
  'toggle-inline-tasks',
  'select-material-task',
  'update:materialAssetType',
  'update:linkedStepId',
  'update:materialDescription',
  'upload',
  'confirm-current-page-binding',
  'clear-current-page-binding',
  'handle-feedback-item',
  'download-from-feedback',
  'primary-action',
  'view-quality',
  'repair-history',
  'open-material-workspace'
])

const props = defineProps({
  qualityTagType: { type: String, default: 'info' },
  qualityTagText: { type: String, default: '待质检' },
  title: { type: String, default: '' },
  qualityScore: { type: [String, Number], default: '-' },
  issueCount: { type: Number, default: 0 },
  gateCount: { type: Number, default: 0 },
  sequenceCount: { type: Number, default: 0 },
  pageGoal: { type: String, default: '' },
  templateChips: { type: Array, default: () => [] },
  practiceRows: { type: Array, default: () => [] },
  pageScript: { type: String, default: '' },
  actionFeedback: { type: Object, default: null },
  failedMessages: { type: Array, default: () => [] },
  gateItems: { type: Array, default: () => [] },
  sequenceEvents: { type: Array, default: () => [] },
  evidenceHints: { type: Array, default: () => [] },
  materialTask: { type: Object, default: null },
  linkedAssets: { type: Array, default: () => [] },
  recommendedAssets: { type: Array, default: () => [] },
  relatedMaterialTasks: { type: Array, default: () => [] },
  showInlineTasks: { type: Boolean, default: false },
  currentPageIndex: { type: Number, default: 1 },
  materialAssetType: { type: String, default: 'screenshot' },
  linkedStepId: { type: String, default: '' },
  materialDescription: { type: String, default: '' },
  materialDescriptionPlaceholder: { type: String, default: '' },
  practiceSteps: { type: Array, default: () => [] },
  materialUploading: { type: Boolean, default: false },
  downloadFlowActive: { type: Boolean, default: false },
  primaryAction: {
    type: Object,
    default: () => ({ label: '查看质量结论', hint: '', mode: 'quality' })
  }
})

function httpUpload(payload) {
  return emit('upload', payload)
}
</script>

<style scoped>
.speaker-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.speaker-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.speaker-panel h3 {
  margin: 0;
  color: #fff;
  font-size: 24px;
  line-height: 1.5;
}

.workbench-score-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.workbench-score-grid > div {
  padding: 14px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.12);
  display: grid;
  gap: 6px;
}

.workbench-score-grid span {
  color: rgba(226, 232, 240, 0.52);
  font-size: 12px;
}

.workbench-score-grid strong {
  color: #fff;
  font-size: 20px;
}

.speaker-meta {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.speaker-meta span {
  color: rgba(226, 232, 240, 0.52);
  font-size: 12px;
}

.speaker-meta strong {
  display: block;
  margin-top: 8px;
  color: #fff;
  line-height: 1.7;
}

.workbench-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.workbench-card > strong {
  display: block;
  margin-bottom: 10px;
  color: #fff;
}

.workbench-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.practice-contract-card dl {
  margin: 0;
  display: grid;
  gap: 8px;
}

.practice-contract-card dt {
  color: rgba(148, 163, 184, 0.92);
  font-size: 12px;
  font-weight: 800;
}

.practice-contract-card dd {
  margin: 0;
  color: rgba(226, 232, 240, 0.78);
  line-height: 1.65;
}

.speaker-script {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.script-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.script-title strong {
  color: #fff;
}

.script-title span {
  color: rgba(148, 163, 184, 0.88);
  font-size: 12px;
}

.speaker-script p {
  margin: 0;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.85;
}

.speaker-script .is-empty {
  color: rgba(226, 232, 240, 0.48);
}

.action-feedback-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.speaker-risks {
  padding: 16px;
  border-radius: 18px;
  background: rgba(127, 29, 29, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.18);
}

.speaker-risks strong {
  display: block;
  margin-bottom: 10px;
  color: #fecaca;
}

.speaker-risks p,
.gate-mini-card p,
.sequence-mini-card p,
.evidence-mini-card p {
  margin: 0 0 10px;
  color: rgba(255, 255, 255, 0.74);
  line-height: 1.7;
}

.speaker-risks p:last-child,
.gate-mini-card p:last-child,
.sequence-mini-card p:last-child,
.evidence-mini-card p:last-child {
  margin-bottom: 0;
}

.inline-material-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.inline-material-head p {
  margin: 8px 0 0;
  color: rgba(226, 232, 240, 0.68);
  line-height: 1.7;
}

.inline-material-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.inline-material-tags span,
.inline-binding-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  color: #bfdbfe;
  font-size: 12px;
  font-weight: 700;
}

.inline-material-tags.linked span,
.inline-binding-chip.confirmed {
  background: rgba(16, 185, 129, 0.12);
  color: #a7f3d0;
}

.inline-binding-chip {
  appearance: none;
  border: 1px solid rgba(59, 130, 246, 0.22);
  cursor: pointer;
}

.inline-binding-chip.confirmed {
  border-color: rgba(16, 185, 129, 0.22);
}

.inline-binding-chip em {
  font-style: normal;
  font-size: 11px;
  opacity: 0.8;
}

.inline-material-summary {
  margin: 12px 0 0;
  color: rgba(226, 232, 240, 0.72);
  line-height: 1.7;
}

.inline-material-linked {
  margin-top: 14px;
}

.inline-material-linked label,
.inline-material-task-head label {
  color: rgba(148, 163, 184, 0.92);
  font-size: 12px;
  font-weight: 800;
}

.inline-material-task-drawer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.inline-material-task-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.inline-material-task-head p {
  margin: 8px 0 0;
  color: rgba(226, 232, 240, 0.62);
  line-height: 1.6;
}

.inline-material-task-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.inline-material-task-item {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(255, 255, 255, 0.03);
  text-align: left;
  cursor: pointer;
}

.inline-material-task-item.active {
  border-color: rgba(59, 130, 246, 0.3);
}

.inline-material-task-item.ready {
  border-color: rgba(74, 222, 128, 0.26);
}

.inline-material-task-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.inline-material-task-top span {
  color: rgba(191, 219, 254, 0.88);
  font-size: 12px;
  font-weight: 800;
}

.inline-material-task-top strong {
  color: rgba(255, 255, 255, 0.88);
  font-size: 12px;
}

.inline-material-task-item p {
  margin: 10px 0 0;
  color: rgba(226, 232, 240, 0.7);
  line-height: 1.6;
}

.inline-material-form {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.speaker-actions {
  display: grid;
  gap: 12px;
}

.speaker-primary-action strong {
  display: block;
  margin: 6px 0 8px;
  color: #fff;
  font-size: 18px;
}

.speaker-primary-action p {
  margin: 0;
  color: rgba(226, 232, 240, 0.7);
  line-height: 1.7;
}

.speaker-secondary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 1200px) {
  .workbench-score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
