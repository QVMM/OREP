<template>
  <div class="materials-panel">
    <div class="materials-hero">
      <div>
        <span class="quality-eyebrow">高级素材台</span>
        <h3>日常补图优先在 HTML 预览右侧完成，这里只保留集中上传和高级管理。</h3>
        <p>如果你只是想给当前页补一张图，建议回到 HTML 预览；这里只在需要统一管理素材、刷新绑定、查看证据包时使用。</p>
      </div>
      <el-button size="small" type="primary" plain @click="$emit('back-to-html')">
        返回 HTML 预览
      </el-button>
    </div>

    <div class="material-upload-card" data-focus-anchor="material-upload">
      <div class="material-upload-copy">
        <span class="quality-eyebrow">证据素材库</span>
        <h2>{{ activeMaterialTask ? `给第${activeMaterialTask.page_index}页上传素材` : '上传截图、设备照片、数据图' }}</h2>
        <p>{{ activeMaterialTask ? activeMaterialTask.summary : '建议上传系统界面、操作流程、设备运行、模型指标、结果数据等素材。系统会做轻量质量判断和匿名风险提醒。' }}</p>
        <div v-if="activeEvidencePack" class="material-pack-banner">
          <div>
            <span>当前证据包</span>
            <strong>{{ activeEvidencePack.title }}</strong>
            <small>{{ activeEvidencePack.description }}</small>
            <div v-if="activeEvidencePack.page_indices?.length" class="material-pack-banner-pages">
              <label>对应页面</label>
              <div class="material-pack-page-pills compact">
                <button
                  v-for="pageIndex in activeEvidencePack.page_indices || []"
                  :key="`banner-${pageIndex}`"
                  type="button"
                  class="material-pack-page-pill"
                  :class="{ active: Number(pageIndex) === Number(currentPageIndex) }"
                  @click="$emit('set-page', Number(pageIndex))"
                >
                  第{{ pageIndex }}页
                </button>
              </div>
            </div>
          </div>
          <el-button size="small" text @click="$emit('clear-evidence-pack-focus')">
            清除聚焦
          </el-button>
        </div>
        <el-button size="small" :loading="materialRefreshing" @click="$emit('refresh-material-recommendations')">
          刷新绑定推荐
        </el-button>
      </div>
      <div class="material-upload-controls">
        <div v-if="activeEvidencePack?.page_indices?.length" class="material-upload-target-pages">
          <label>这组素材将优先用于</label>
          <div class="material-pack-page-pills compact">
            <button
              v-for="pageIndex in activeEvidencePack.page_indices || []"
              :key="`upload-${pageIndex}`"
              type="button"
              class="material-pack-page-pill"
              :class="{ active: Number(pageIndex) === Number(currentPageIndex) }"
              @click="$emit('set-page', Number(pageIndex))"
            >
              第{{ pageIndex }}页
            </button>
          </div>
        </div>
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
            v-for="step in practiceSteps || []"
            :key="step.step_id"
            :label="`${step.step_order}. ${step.step_title}`"
            :value="step.step_id"
          />
        </el-select>
        <el-input
          :model-value="materialDescription"
          type="textarea"
          :rows="3"
          :placeholder="materialDescriptionPlaceholder"
          @update:model-value="$emit('update:materialDescription', $event)"
        />
        <el-upload
          drag
          action=""
          :http-request="httpUpload"
          :show-file-list="false"
          :disabled="materialUploading"
          accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv"
        >
          <el-icon class="material-upload-icon"><Upload /></el-icon>
          <div class="el-upload__text">拖拽素材到这里，或点击上传</div>
        </el-upload>
      </div>
    </div>

    <details v-if="materialUploadTasks.length" class="materials-primary-tasks">
      <summary>
        <span>逐页待上传清单</span>
        <strong>{{ materialUploadPendingCount }}/{{ materialUploadTasks.length }}</strong>
      </summary>
      <div class="material-task-board">
        <div class="material-task-head">
          <div>
            <span class="quality-eyebrow">逐页待上传清单</span>
            <h3>直接看哪一页缺哪张图，点一下就上传</h3>
            <p>这部分作为高级补图清单保留。日常优先在 HTML 预览右侧直接处理当前页。</p>
          </div>
        </div>
        <div class="material-task-list">
          <button
            v-for="taskItem in materialUploadTasks"
            :key="taskItem.key"
            type="button"
            class="material-task-item"
            :class="{ active: activeMaterialTask?.key === taskItem.key, ready: taskItem.status === 'ready' }"
            @click="$emit('select-material-task', taskItem)"
          >
            <div class="material-task-top">
              <span>第{{ taskItem.page_index }}页</span>
              <strong>{{ taskItem.status === 'ready' ? '已补齐' : '待上传' }}</strong>
            </div>
            <h4>{{ taskItem.page_title }}</h4>
            <p>{{ taskItem.summary }}</p>
            <div class="material-task-tags">
              <span v-for="asset in taskItem.required_assets.slice(0, 4)" :key="asset">{{ asset }}</span>
            </div>
          </button>
        </div>
      </div>
    </details>

    <div v-if="activeEvidencePack" class="material-pack-focus-board">
      <div class="material-pack-focus-head">
        <div>
          <span class="quality-eyebrow">证据包上传任务</span>
          <h3>{{ activeEvidencePack.title }}</h3>
          <p>上传这组素材后，会优先服务这些页面与证据位，系统也会按这组约束重新做绑定。</p>
        </div>
        <strong>{{ activeEvidencePack.ready_count || 0 }}/{{ activeEvidencePack.asset_count || 0 }}</strong>
      </div>
      <div class="material-pack-focus-grid">
        <div class="material-pack-focus-block">
          <span>覆盖页面</span>
          <div class="material-pack-page-pills">
            <button
              v-for="pageIndex in activeEvidencePack.page_indices || []"
              :key="pageIndex"
              type="button"
              class="material-pack-page-pill"
              :class="{ active: Number(pageIndex) === Number(currentPageIndex) }"
              @click="$emit('set-page', Number(pageIndex))"
            >
              第{{ pageIndex }}页
            </button>
          </div>
        </div>
        <div v-if="activeEvidencePack.required_assets?.length" class="material-pack-focus-block">
          <span>建议素材</span>
          <div class="material-pack-tags">
            <strong v-for="asset in activeEvidencePack.required_assets" :key="asset">{{ asset }}</strong>
          </div>
        </div>
      </div>
    </div>

    <details class="materials-advanced">
      <summary>高级视图：证据包与证据链</summary>

      <div class="policy-evidence-card">
        <div>
          <span class="quality-eyebrow">政策证据链</span>
          <h3>政策页需要官方来源或截图，不能只写概念文字</h3>
          <p>
            已识别 {{ policyPages.length }} 个政策页，
            已上传 {{ policyEvidenceAssets.length }} 份政策证据。
            建议至少上传 1 张政策官网截图或政策文件截图，并在说明中写清官方链接/发布单位。
          </p>
        </div>
        <el-button
          size="small"
          type="primary"
          plain
          @click="$emit('prepare-policy-upload')"
        >
          准备上传政策截图
        </el-button>
      </div>

      <div v-if="materialEvidencePlan" class="evidence-plan-board" :class="materialEvidencePlan.status">
        <div class="evidence-plan-head">
          <div>
            <span class="quality-eyebrow">证据补强计划</span>
            <h3>系统已按证据包收敛素材缺口</h3>
            <p>{{ materialEvidencePlan.summary }}</p>
          </div>
          <div class="evidence-plan-score">
            <strong>{{ materialEvidencePlan.ready_count }}/{{ materialEvidencePlan.total_required }}</strong>
            <span>证据包已覆盖</span>
          </div>
        </div>
        <div v-if="materialEvidencePacks.length" class="evidence-pack-grid">
          <div
            v-for="pack in materialEvidencePacks"
            :key="pack.key"
            class="evidence-pack-card"
            :class="[pack.status, { active: activeEvidencePack?.key === pack.key }]"
          >
            <div class="evidence-pack-head">
              <div>
                <span>{{ pack.status === 'ready' ? '已覆盖' : (pack.status === 'partial' ? '部分覆盖' : '待补强') }}</span>
                <h4>{{ pack.title }}</h4>
              </div>
              <strong>{{ pack.ready_count || 0 }}/{{ pack.asset_count || 0 }}</strong>
            </div>
            <p>{{ pack.description }}</p>
            <div v-if="pack.page_indices?.length" class="evidence-pack-pages">
              <span>覆盖页面</span>
              <strong>{{ targetPagesText(pack.page_indices) }}</strong>
            </div>
            <div v-if="pack.required_assets?.length" class="evidence-pack-tags">
              <span v-for="asset in pack.required_assets.slice(0, 4)" :key="asset">{{ asset }}</span>
            </div>
            <div v-if="pack.asset_names?.length" class="evidence-pack-assets">
              <span>已识别素材</span>
              <strong>{{ pack.asset_names.slice(0, 2).join(' / ') }}</strong>
            </div>
            <div v-if="pack.reasons?.length" class="evidence-pack-reasons">
              <span>{{ pack.reasons[0] }}</span>
            </div>
            <div class="evidence-pack-actions">
              <el-button
                v-if="pack.primary_requirement"
                size="small"
                type="primary"
                plain
                @click="$emit('activate-evidence-pack', pack)"
              >
                {{ pack.status === 'ready' ? '继续补强这组素材' : '按证据包上传' }}
              </el-button>
            </div>
          </div>
        </div>
        <div class="evidence-plan-subhead">
          <strong>逐页映射参考</strong>
          <span>下面保留逐页要求，方便你查看这组证据具体会落到哪些页面。</span>
        </div>
        <div class="evidence-plan-grid">
          <div
            v-for="group in materialEvidenceGroups"
            :key="group.key"
            class="evidence-plan-card"
            :class="group.status"
          >
            <div class="evidence-plan-card-head">
              <span>{{ group.missing_count ? `缺 ${group.missing_count} 项` : '已就绪' }}</span>
              <strong>{{ materialTypeText(group.asset_type) }}</strong>
            </div>
            <h4>{{ group.title }}</h4>
            <p>{{ group.description }}</p>
            <div class="evidence-plan-pages">
              <span v-if="group.target_pages?.length">{{ targetPagesText(group.target_pages.slice(0, 6)) }}</span>
              <span v-else>暂未发现强制缺口</span>
            </div>
            <div v-if="group.requirements?.length" class="evidence-plan-requirements">
              <button
                v-for="requirement in group.requirements.slice(0, 3)"
                :key="requirement.key"
                type="button"
                @click="$emit('prepare-evidence-plan-upload', requirement)"
              >
                第{{ requirement.page_index }}页 · {{ requirement.title }}
              </button>
            </div>
            <el-button
              v-if="group.primary_requirement"
              size="small"
              type="primary"
              plain
              @click="$emit('prepare-evidence-plan-upload', group.primary_requirement)"
            >
              按计划上传
            </el-button>
          </div>
        </div>
      </div>

      <div class="evidence-chain-board">
        <div class="evidence-chain-head">
          <div>
            <span class="quality-eyebrow">证据链总览</span>
            <h3>把素材绑定到政策、实操、评分点，而不是只做文件仓库</h3>
            <p>优先补齐政策官方来源、实操截图/照片/数据图，以及高风险评分点证据。</p>
          </div>
          <strong>{{ evidenceChainSummary.ready }}/{{ evidenceChainSummary.total }}</strong>
        </div>
        <div class="evidence-chain-grid">
          <div
            v-for="item in evidenceChainItems"
            :key="item.key"
            class="evidence-chain-card"
            :class="item.status"
          >
            <div class="evidence-chain-card-head">
              <span>{{ item.count }} 份</span>
              <strong>{{ evidenceChainStatusText(item.status) }}</strong>
            </div>
            <h4>{{ item.title }}</h4>
            <p>{{ item.description }}</p>
            <div class="evidence-chain-tags">
              <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
            </div>
            <el-button
              v-if="item.action"
              size="small"
              type="primary"
              plain
              @click="item.action()"
            >
              {{ item.actionText }}
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="materialAssets.length" class="material-list">
        <div
          v-for="asset in materialAssets"
          :key="asset.id"
          class="material-card"
          :class="{ warning: asset.privacy_risk !== 'low' }"
        >
          <a
            v-if="asset.analysis_result?.is_image"
            class="material-thumb"
            :href="asset.file_url"
            target="_blank"
            rel="noreferrer"
          >
            <img :src="asset.file_url" :alt="asset.filename" />
          </a>
          <a v-else class="material-thumb document" :href="asset.file_url" target="_blank" rel="noreferrer">
            {{ asset.asset_type || 'FILE' }}
          </a>
          <div class="material-body">
            <div class="material-head">
              <div>
                <span>{{ materialTypeText(asset.asset_type) }} · {{ formatDate(asset.created_at) }}</span>
                <h3>{{ asset.filename }}</h3>
              </div>
              <strong>{{ materialQualityText(asset.quality) }}</strong>
            </div>
            <p>{{ asset.description || '暂无说明，建议补充这份素材能证明什么。' }}</p>
            <div class="material-tags">
              <span v-for="usage in asset.analysis_result?.suggested_usage || []" :key="usage">{{ usage }}</span>
            </div>
            <div
              v-if="asset.analysis_result?.confirmed_page_bindings?.length || asset.analysis_result?.confirmed_step_bindings?.length || asset.analysis_result?.confirmed_scoring_bindings?.length"
              class="binding-confirmed"
            >
              <label>已确认绑定</label>
              <div v-if="asset.analysis_result?.confirmed_page_bindings?.length" class="binding-list">
                <button
                  v-for="binding in asset.analysis_result.confirmed_page_bindings"
                  :key="`confirmed-page-${binding.page_index}`"
                  type="button"
                  class="binding-chip confirmed"
                >
                  第 {{ binding.page_index }} 页
                  <em @click.stop="$emit('clear-confirmed-binding', { asset, bindingType: 'page', targetKey: String(binding.target_key || binding.page_index) })">移除</em>
                </button>
              </div>
              <div v-if="asset.analysis_result?.confirmed_step_bindings?.length" class="binding-list">
                <button
                  v-for="binding in asset.analysis_result.confirmed_step_bindings"
                  :key="`confirmed-step-${binding.step_id}`"
                  type="button"
                  class="binding-chip confirmed"
                >
                  实操：{{ binding.target_label || binding.step_id }}
                  <em @click.stop="$emit('clear-confirmed-binding', { asset, bindingType: 'step', targetKey: String(binding.target_key || binding.step_id) })">移除</em>
                </button>
              </div>
              <div v-if="asset.analysis_result?.confirmed_scoring_bindings?.length" class="binding-list">
                <button
                  v-for="binding in asset.analysis_result.confirmed_scoring_bindings"
                  :key="`confirmed-scoring-${binding.point_id}`"
                  type="button"
                  class="binding-chip confirmed"
                >
                  评分点：{{ binding.target_label || binding.point_id }}
                  <em @click.stop="$emit('clear-confirmed-binding', { asset, bindingType: 'scoring_point', targetKey: String(binding.target_key || binding.point_id) })">移除</em>
                </button>
              </div>
            </div>
            <div class="binding-recommendation">
              <label>智能绑定推荐 · {{ asset.analysis_result?.binding_confidence || 0 }}%</label>
              <p>{{ asset.analysis_result?.binding_reason || '暂无推荐理由' }}</p>
              <div v-if="asset.analysis_result?.recommended_step_bindings?.length" class="binding-list">
                <button
                  v-for="binding in asset.analysis_result.recommended_step_bindings"
                  :key="binding.step_id"
                  type="button"
                  class="binding-chip"
                  @click="$emit('confirm-binding', { asset, bindingType: 'step', targetKey: String(binding.step_id), targetLabel: binding.step_title || binding.step_id })"
                >
                  实操：{{ binding.step_order }}. {{ binding.step_title }}
                  <em>确认</em>
                </button>
              </div>
              <div v-if="asset.analysis_result?.recommended_scoring_bindings?.length" class="binding-list">
                <button
                  v-for="binding in asset.analysis_result.recommended_scoring_bindings"
                  :key="binding.point_id"
                  type="button"
                  class="binding-chip"
                  @click="$emit('confirm-binding', { asset, bindingType: 'scoring_point', targetKey: String(binding.point_id), targetLabel: binding.point_name || binding.point_id })"
                >
                  评分点：{{ binding.point_name }}
                  <em>确认</em>
                </button>
              </div>
              <div v-if="asset.analysis_result?.recommended_page_bindings?.length" class="binding-list">
                <button
                  v-for="binding in asset.analysis_result.recommended_page_bindings"
                  :key="`${binding.source}-${binding.page_index}`"
                  type="button"
                  class="binding-chip"
                  @click="$emit('confirm-binding', { asset, bindingType: 'page', targetKey: String(binding.page_index), targetLabel: `第${binding.page_index}页` })"
                >
                  第 {{ binding.page_index }} 页
                  <em>确认</em>
                </button>
              </div>
            </div>
            <div v-if="asset.analysis_result?.tips?.length" class="material-tips">
              <span v-for="tip in asset.analysis_result.tips" :key="tip">{{ tip }}</span>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无素材证据，上传后会出现在这里，并可支撑实操步骤与评分点" />
    </details>
  </div>
</template>

<script setup>
import { Upload } from '@element-plus/icons-vue'

const emit = defineEmits([
  'back-to-html',
  'set-page',
  'clear-evidence-pack-focus',
  'refresh-material-recommendations',
  'update:materialAssetType',
  'update:linkedStepId',
  'update:materialDescription',
  'upload',
  'select-material-task',
  'prepare-policy-upload',
  'activate-evidence-pack',
  'prepare-evidence-plan-upload',
  'confirm-binding',
  'clear-confirmed-binding'
])

defineProps({
  activeMaterialTask: { type: Object, default: null },
  activeEvidencePack: { type: Object, default: null },
  currentPageIndex: { type: Number, default: 1 },
  materialRefreshing: { type: Boolean, default: false },
  materialAssetType: { type: String, default: 'screenshot' },
  linkedStepId: { type: String, default: '' },
  materialDescription: { type: String, default: '' },
  materialDescriptionPlaceholder: { type: String, default: '' },
  materialUploading: { type: Boolean, default: false },
  practiceSteps: { type: Array, default: () => [] },
  materialUploadTasks: { type: Array, default: () => [] },
  materialUploadPendingCount: { type: Number, default: 0 },
  materialEvidencePlan: { type: Object, default: null },
  materialEvidencePacks: { type: Array, default: () => [] },
  materialEvidenceGroups: { type: Array, default: () => [] },
  policyPages: { type: Array, default: () => [] },
  policyEvidenceAssets: { type: Array, default: () => [] },
  evidenceChainSummary: { type: Object, default: () => ({ ready: 0, total: 0 }) },
  evidenceChainItems: { type: Array, default: () => [] },
  materialAssets: { type: Array, default: () => [] },
  materialTypeText: { type: Function, required: true },
  targetPagesText: { type: Function, required: true },
  evidenceChainStatusText: { type: Function, required: true },
  formatDate: { type: Function, required: true },
  materialQualityText: { type: Function, required: true }
})

function httpUpload(payload) {
  return emit('upload', payload)
}
</script>

<style scoped>
.materials-panel {
  display: grid;
  gap: 20px;
}

.materials-hero,
.material-upload-card,
.material-pack-focus-board,
.policy-evidence-card,
.evidence-plan-board,
.evidence-chain-board {
  padding: 22px 24px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.materials-hero,
.material-upload-card,
.policy-evidence-card,
.evidence-plan-head,
.material-pack-focus-head,
.evidence-chain-head,
.material-head,
.evidence-plan-card-head,
.evidence-pack-head,
.materials-primary-tasks > summary {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.materials-hero h3,
.policy-evidence-card h3,
.evidence-plan-head h3,
.material-pack-focus-head h3,
.evidence-chain-head h3,
.material-task-head h3 {
  margin: 6px 0 10px;
  color: #0f172a;
}

.materials-hero p,
.policy-evidence-card p,
.evidence-plan-head p,
.material-pack-focus-head p,
.evidence-chain-head p,
.material-upload-copy p,
.material-task-head p,
.evidence-plan-card p,
.evidence-chain-card p,
.material-body p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.material-upload-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 420px);
}

.material-upload-controls {
  display: grid;
  gap: 12px;
}

.material-pack-banner,
.material-pack-focus-grid,
.evidence-plan-grid,
.evidence-pack-grid,
.evidence-chain-grid,
.material-list,
.material-task-list {
  display: grid;
  gap: 14px;
}

.material-pack-banner,
.material-pack-focus-block,
.evidence-plan-card,
.evidence-pack-card,
.evidence-chain-card,
.material-card,
.material-task-item {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.98);
}

.material-pack-banner-pages,
.material-upload-target-pages {
  margin-top: 10px;
}

.material-pack-page-pills,
.evidence-pack-tags,
.evidence-chain-tags,
.material-task-tags,
.material-tags,
.binding-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.material-pack-page-pill,
.evidence-pack-tags span,
.evidence-chain-tags span,
.material-task-tags span,
.material-tags span,
.binding-list span,
.binding-chip {
  border: 0;
  border-radius: 999px;
  padding: 8px 12px;
  font-weight: 700;
}

.material-pack-page-pill {
  cursor: pointer;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.material-pack-page-pill.active {
  background: rgba(37, 99, 235, 0.18);
}

.evidence-pack-tags span,
.evidence-chain-tags span,
.material-task-tags span,
.material-tags span,
.binding-list span {
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.binding-chip {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: rgba(239, 246, 255, 0.95);
  border: 1px solid rgba(96, 165, 250, 0.32);
  color: #1d4ed8;
}

.binding-chip.confirmed {
  background: rgba(236, 253, 245, 0.95);
  border-color: rgba(16, 185, 129, 0.3);
  color: #047857;
}

.binding-chip em {
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  opacity: 0.8;
}

.materials-primary-tasks {
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.materials-primary-tasks > summary,
.materials-advanced > summary {
  cursor: pointer;
  padding: 18px 22px;
  list-style: none;
}

.materials-primary-tasks > summary::-webkit-details-marker,
.materials-advanced > summary::-webkit-details-marker {
  display: none;
}

.material-task-board,
.materials-advanced {
  padding: 0 22px 22px;
}

.material-task-item {
  text-align: left;
  cursor: pointer;
}

.material-task-item.active {
  border-color: rgba(37, 99, 235, 0.28);
}

.material-task-item.ready {
  border-color: rgba(74, 222, 128, 0.24);
}

.material-task-top,
.evidence-plan-card-head,
.evidence-pack-head,
.evidence-chain-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.material-task-top span,
.evidence-plan-card-head span,
.evidence-pack-head span,
.evidence-chain-card-head span,
.material-head span {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.material-task-top strong,
.evidence-plan-card-head strong,
.evidence-pack-head strong,
.evidence-chain-card-head strong,
.evidence-plan-score strong,
.material-head strong {
  color: #0f172a;
}

.material-task-item h4,
.evidence-plan-card h4,
.evidence-pack-head h4,
.evidence-chain-card h4,
.material-head h3 {
  margin: 8px 0;
  color: #0f172a;
}

.evidence-plan-board.ready {
  border-color: rgba(74, 222, 128, 0.24);
}

.evidence-plan-subhead {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin: 18px 0 14px;
}

.evidence-plan-pages,
.evidence-pack-pages,
.evidence-pack-assets,
.evidence-pack-reasons {
  margin-top: 12px;
}

.evidence-chain-grid,
.material-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.material-card {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 14px;
}

.material-card.warning {
  border-color: rgba(250, 204, 21, 0.24);
}

.material-thumb {
  display: block;
  border-radius: 18px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.05);
}

.material-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.material-thumb.document {
  display: grid;
  place-items: center;
  min-height: 180px;
  color: #2563eb;
  font-weight: 800;
}

.binding-confirmed,
.binding-recommendation,
.material-tips {
  margin-top: 12px;
}

@media (max-width: 980px) {
  .materials-hero,
  .material-upload-card,
  .policy-evidence-card,
  .evidence-plan-head,
  .material-pack-focus-head,
  .evidence-chain-head,
  .material-head,
  .materials-primary-tasks > summary,
  .materials-advanced > summary,
  .material-card {
    grid-template-columns: 1fr;
    display: grid;
  }

  .evidence-plan-grid,
  .evidence-pack-grid,
  .evidence-chain-grid,
  .material-list {
    grid-template-columns: 1fr;
  }
}
</style>
