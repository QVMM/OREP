<template>
  <div class="outline-editor">
    <div class="editor-toolbar">
      <el-button size="small" @click="$emit('expand-all')">
        <el-icon><Expand /></el-icon>
        展开全部
      </el-button>
      <el-button size="small" @click="$emit('collapse-all')">
        <el-icon><Fold /></el-icon>
        收起全部
      </el-button>
      <el-button size="small" @click="$emit('reset')" :disabled="!hasChanges">
        <el-icon><RefreshRight /></el-icon>
        恢复原始
      </el-button>
    </div>

    <div class="outline-pages">
      <div
        v-for="(page, index) in pages"
        :key="index"
        :class="['outline-page-item', { expanded: page._expanded, modified: page._modified }]"
      >
        <div class="page-header" @click="$emit('toggle-expand', index)">
          <div class="page-index-badge">{{ index + 1 }}</div>
          <div class="page-title-preview">
            <span class="title-text">{{ page.title || page.section || '无标题' }}</span>
            <div class="page-tags">
              <el-tag size="small" type="info">{{ page.phase || page.section || '未分类' }}</el-tag>
              <el-tag v-if="page.slide_role" size="small">{{ page.slide_role }}</el-tag>
              <el-tag v-if="page.act_phase" size="small" effect="plain" type="success">{{ actPhaseLabel(page.act_phase) }}</el-tag>
              <el-tag v-if="page.page_series_type" size="small" effect="plain" type="warning">{{ page.page_series_type }}</el-tag>
              <el-tag v-if="page._modified" size="small" type="warning">已修改</el-tag>
            </div>
          </div>
          <div class="page-actions">
            <el-icon v-if="page._expanded"><ArrowUp /></el-icon>
            <el-icon v-else><ArrowDown /></el-icon>
          </div>
        </div>

        <div v-if="page._expanded" class="page-edit-content">
          <el-form label-position="top" size="default">
            <el-form-item label="页面标题">
              <el-input
                :model-value="page.title"
                placeholder="请输入页面标题"
                @update:model-value="updateField(index, 'title', $event)"
              />
            </el-form-item>

            <el-form-item label="章节/阶段">
              <el-select
                :model-value="page.section"
                placeholder="选择章节"
                style="width: 100%"
                @update:model-value="updateField(index, 'section', $event)"
              >
                <el-option v-for="option in sectionOptions" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
            </el-form-item>

            <el-form-item label="页面类型">
              <el-select
                :model-value="page.slide_role"
                placeholder="选择页面类型"
                style="width: 100%"
                @update:model-value="updateField(index, 'slide_role', $event)"
              >
                <el-option v-for="option in slideRoleOptions" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
            </el-form-item>

            <div class="design-contract-grid">
              <div class="design-contract-card">
                <span class="design-label">页面契约</span>
                <strong>{{ page.contract_id || '待推断' }}</strong>
              </div>
              <div class="design-contract-card">
                <span class="design-label">页面类型</span>
                <strong>{{ page.page_type || 'content_page' }}</strong>
              </div>
              <div class="design-contract-card">
                <span class="design-label">所属幕次</span>
                <strong>{{ actPhaseLabel(page.act_phase) }}</strong>
              </div>
              <div class="design-contract-card">
                <span class="design-label">页系样张</span>
                <strong>{{ page.page_series_type || 'content_support' }}</strong>
              </div>
              <div class="design-contract-card">
                <span class="design-label">视觉职责</span>
                <strong>{{ page.page_visual_role || 'supporting_panel' }}</strong>
              </div>
              <div class="design-contract-card">
                <span class="design-label">承接角色</span>
                <strong>{{ page.transition_role || 'supporting_content' }}</strong>
              </div>
            </div>

            <el-form-item label="页面内容摘要">
              <el-input
                :model-value="page.content"
                type="textarea"
                :rows="3"
                placeholder="说明这一页要表达的核心内容，AI 会据此继续扩写和生成 HTML"
                @update:model-value="updateField(index, 'content', $event)"
              />
            </el-form-item>

            <el-form-item label="PPT页内文字">
              <el-input
                :model-value="page.ppt_text"
                type="textarea"
                :rows="3"
                placeholder="填写希望直接出现在PPT页面上的精炼文字"
                @update:model-value="updateField(index, 'ppt_text', $event)"
              />
            </el-form-item>

            <el-form-item label="内容要点">
              <div class="content-points-editor">
                <div
                  v-for="(point, pIdx) in page.content_points"
                  :key="pIdx"
                  class="content-point-item"
                >
                  <el-input
                    :model-value="page.content_points[pIdx]"
                    placeholder="输入内容要点"
                    @update:model-value="updatePoint(index, pIdx, $event)"
                  />
                  <el-button
                    type="danger"
                    text
                    @click="$emit('remove-point', index, pIdx)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
                <el-button
                  type="primary"
                  text
                  @click="$emit('add-point', index)"
                >
                  <el-icon><Plus /></el-icon>
                  添加要点
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="演讲备注">
              <el-input
                :model-value="page.speaker_notes"
                type="textarea"
                :rows="3"
                placeholder="演讲备注（可选）"
                @update:model-value="updateField(index, 'speaker_notes', $event)"
              />
            </el-form-item>

            <el-form-item label="视觉/版式建议">
              <el-input
                :model-value="page.visual_suggestion"
                type="textarea"
                :rows="2"
                placeholder="如：用流程图展示、左右对比、突出关键数据等"
                @update:model-value="updateField(index, 'visual_suggestion', $event)"
              />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ArrowDown, ArrowUp, Delete, Expand, Fold, Plus, RefreshRight } from '@element-plus/icons-vue'

const emit = defineEmits([
  'expand-all',
  'collapse-all',
  'reset',
  'toggle-expand',
  'update-page',
  'add-point',
  'remove-point'
])

const props = defineProps({
  pages: {
    type: Array,
    default: () => []
  },
  hasChanges: {
    type: Boolean,
    default: false
  }
})

const sectionOptions = [
  { label: '封面', value: 'cover' },
  { label: '目录与60分钟节奏', value: 'agenda' },
  { label: '政策与产业背景', value: 'policy_context' },
  { label: '项目定义', value: 'project_definition' },
  { label: '问题与方案承接', value: 'solution_overview' },
  { label: '技术架构', value: 'technical_architecture' },
  { label: '实操演示', value: 'practice_demo' },
  { label: '安全与规范', value: 'safety_norms' },
  { label: '应用价值', value: 'application_value' },
  { label: '创新成效', value: 'innovation' },
  { label: '团队协作', value: 'team_collaboration' },
  { label: '研发历程', value: 'rd_journey' },
  { label: '产教融合', value: 'industry_education' },
  { label: '总结收束', value: 'closing_summary' },
  { label: '感谢', value: 'thanks' }
]

const slideRoleOptions = [
  { label: '标题页', value: 'title' },
  { label: '内容页', value: 'content' },
  { label: '图文页', value: 'image_text' },
  { label: '对比页', value: 'comparison' },
  { label: '数据页', value: 'data' },
  { label: '图表页', value: 'chart' },
  { label: '列表页', value: 'list' }
]

const actPhaseLabelMap = {
  act_1_opening_alignment: '第一幕·开场对齐',
  act_2_problem_solution: '第二幕·问题到方案',
  act_3_technical_proof: '第三幕·技术与实操证明',
  act_4_value_closing: '第四幕·价值与收束'
}

function actPhaseLabel(value) {
  return actPhaseLabelMap[value] || value || '待推断'
}

function updateField(index, field, value) {
  const page = { ...(Array.isArray(props.pages) ? props.pages[index] : {}) }
  if (!page) return
  page[field] = value
  page._modified = true
  emit('update-page', index, page)
}

function updatePoint(index, pointIndex, value) {
  const page = { ...(Array.isArray(props.pages) ? props.pages[index] : {}) }
  if (!page) return
  const nextPoints = Array.isArray(page.content_points) ? [...page.content_points] : []
  nextPoints[pointIndex] = value
  page.content_points = nextPoints
  page._modified = true
  emit('update-page', index, page)
}
</script>

<style scoped>
.outline-editor {
  margin-bottom: 24px;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.outline-pages {
  display: grid;
  gap: 14px;
}

.outline-page-item {
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.78);
  overflow: hidden;
}

.outline-page-item.modified {
  border-color: rgba(250, 204, 21, 0.26);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  cursor: pointer;
}

.page-index-badge {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.18);
  color: #93c5fd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  flex-shrink: 0;
}

.page-title-preview {
  min-width: 0;
  flex: 1;
}

.title-text {
  display: block;
  color: #fff;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.5;
}

.page-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.page-actions {
  color: rgba(226, 232, 240, 0.66);
}

.page-edit-content {
  padding: 0 18px 18px;
}

.content-points-editor {
  display: grid;
  gap: 10px;
}

.content-point-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.design-contract-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}

.design-contract-card {
  border-radius: 14px;
  border: 1px solid rgba(96, 165, 250, 0.18);
  background: rgba(15, 23, 42, 0.55);
  padding: 12px 14px;
  display: grid;
  gap: 4px;
}

.design-label {
  color: rgba(148, 163, 184, 0.9);
  font-size: 12px;
}

.design-contract-card strong {
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

@media (max-width: 760px) {
  .page-header {
    align-items: flex-start;
  }
}
</style>
