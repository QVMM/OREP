<template>
  <div class="quality-panel">
    <div class="quality-hero" :class="qualityStatusClass(qualityReport.overall_status)">
      <div>
        <span class="quality-eyebrow">基础质检摘要</span>
        <h2>{{ qualityStatusText(qualityReport.overall_status) }}</h2>
        <p>
          共 {{ qualityReport.total_pages || 0 }} 页，
          HTML 有效 {{ qualityReport.html_success_count || 0 }} 页，
          空页风险 {{ qualityReport.empty_page_count || 0 }} 页，
          内容过密 {{ qualityReport.density_warning_count || 0 }} 页，
          视口风险 {{ qualityReport.viewport_risk_count || 0 }} 页，
          占位词 {{ qualityReport.placeholder_issue_count || 0 }} 页，
          行业污染 {{ qualityReport.industry_issue_count || 0 }} 页，
          模板页 {{ qualityReport.template_issue_count || 0 }} 页，
          评分缺口 {{ qualityReport.scoring_gap_count || 0 }} 页，
          实操问题 {{ qualityReport.practice_issue_count || 0 }} 页，
          素材缺口 {{ qualityReport.material_gap_count || 0 }} 页，
          布局风险 {{ qualityReport.layout_risk_count || 0 }} 页，
          图表风险 {{ qualityReport.diagram_risk_count || 0 }} 页。
        </p>
        <div class="quality-hero-actions">
          <el-button size="small" :loading="qualityChecking" @click="$emit('run-quality-check')">
            重新质检
          </el-button>
          <el-button
            size="small"
            type="primary"
            :disabled="batchRepairableCount === 0"
            :loading="batchRepairing"
            @click="$emit('batch-repair')"
          >
            批量修复可自动项（{{ batchRepairableCount }}）
          </el-button>
        </div>
      </div>
      <strong>{{ qualityReport.average_score ?? '-' }}</strong>
    </div>

    <div class="quality-priority-board">
      <div class="quality-priority-head">
        <div>
          <span class="quality-eyebrow">修复优先级驾驶舱</span>
          <h3>先处理会影响路演观感和评分可信度的硬伤</h3>
          <p>P0 是必须先修的页面级硬伤，P1 是影响专业度和评分覆盖的重要风险，P2 适合最后统一打磨。</p>
        </div>
        <el-button
          size="small"
          type="primary"
          :disabled="batchRepairableCount === 0"
          :loading="batchRepairing"
          @click="$emit('batch-repair')"
        >
          批量修复可自动项
        </el-button>
      </div>
      <div class="quality-priority-grid">
        <div
          v-for="group in qualityPriorityGroups"
          :key="group.level"
          class="quality-priority-card"
          :class="group.level"
        >
          <div class="priority-card-head">
            <span>{{ group.level }}</span>
            <strong>{{ group.pages.length }} 页</strong>
          </div>
          <h4>{{ group.title }}</h4>
          <p>{{ group.description }}</p>
          <div v-if="group.pages.length" class="priority-page-links">
            <button
              v-for="page in group.pages.slice(0, 5)"
              :key="page.page_index"
              type="button"
              @click="$emit('preview-page', page.page_index)"
            >
              第{{ page.page_index }}页
            </button>
          </div>
          <div v-else class="priority-empty">暂无该级别问题</div>
        </div>
      </div>
    </div>

    <div v-if="htmlQualityGateItems.length" class="html-gate-card">
      <div class="html-gate-head">
        <div>
          <span class="quality-eyebrow">生成期自动拦截记录</span>
          <h3>系统已在进入预览前处理 {{ htmlQualityGate.retry_count || 0 }} 个 P0 视觉风险页</h3>
          <p>
            其中 {{ htmlQualityGate.passed_after_retry || 0 }} 页经 AI 二次重写后通过，
            {{ htmlQualityGate.fallback_count || 0 }} 页进入安全兜底。
          </p>
        </div>
        <strong>{{ htmlQualityGate.passed_after_retry || 0 }}/{{ htmlQualityGate.retry_count || 0 }}</strong>
      </div>
      <div class="html-gate-list">
        <div v-for="item in htmlQualityGateItems" :key="`${item.page_index}-${item.created_at}`" class="html-gate-item">
          <div>
            <span>第 {{ item.page_index }} 页</span>
            <h4>{{ item.title || getOutlineTitle(item.page_index) }}</h4>
            <p>{{ gateActionText(item.action) }}</p>
          </div>
          <div class="html-gate-tags">
            <span v-for="check in item.failed_checks || []" :key="check">{{ gateCheckText(check) }}</span>
          </div>
          <el-button size="small" text @click="$emit('preview-page', item.page_index)">查看此页</el-button>
        </div>
      </div>
    </div>

    <div class="quality-page-list">
      <div
        v-for="page in qualityPages"
        :key="page.page_index"
        class="quality-page-card"
        :class="[qualityStatusClass(page.status), qualityPriorityLevel(page)]"
        :data-quality-page="page.page_index"
      >
        <div class="quality-page-head">
          <div>
            <span>第 {{ page.page_index }} 页 · {{ qualityPriorityLevel(page) }}</span>
            <h3>{{ page.title || getOutlineTitle(page.page_index) }}</h3>
          </div>
          <strong>{{ page.score }} 分</strong>
        </div>
        <div v-if="page.status !== 'pass'" class="quality-card-brief">
          <span>{{ qualityPriorityReason(page) }}</span>
          <em>{{ strategyText(page.regeneration_strategy) || '建议人工复查页面表达' }}</em>
        </div>
        <div class="quality-checks">
          <span
            v-for="check in normalizeChecks(page.checks)"
            :key="check.key"
            :class="{ pass: check.pass }"
            :title="check.message"
          >
            {{ check.label }}：{{ check.pass ? '通过' : '需关注' }}
          </span>
        </div>
        <div v-if="pageRiskBadges(page).length" class="quality-risk-badges">
          <span
            v-for="badge in pageRiskBadges(page)"
            :key="badge"
            class="risk-badge"
          >
            {{ badge }}
          </span>
        </div>
        <div v-if="failedCheckMessages(page).length" class="quality-issues">
          <p v-for="message in failedCheckMessages(page)" :key="message">{{ message }}</p>
        </div>
        <p v-if="page.regeneration_strategy" class="quality-fix">
          建议：{{ strategyText(page.regeneration_strategy) }}
        </p>
        <p v-if="resolvedRepairRouteReason(page)" class="quality-fix">
          {{ repairRouteLabel(inferCurrentRepairRoute(page)) }}：{{ resolvedRepairRouteReason(page) }}
        </p>
        <p v-if="page.repair_feedback_hint" class="quality-fix quality-fix-warning">
          {{ page.repair_feedback_hint }}
        </p>
        <div
          v-if="pageIssueProfileSummary(page).length"
          class="quality-issue-profile"
        >
          <strong>缺陷档案</strong>
          <p v-for="item in pageIssueProfileSummary(page)" :key="item">{{ item }}</p>
        </div>
        <div v-if="page.status !== 'pass'" class="quality-actions">
          <el-button
            size="small"
            type="primary"
            plain
            :loading="repairingPageIndex === page.page_index"
            @click="$emit('repair-page', page)"
          >
            {{ repairActionButtonText(page) }}
          </el-button>
          <el-button
            size="small"
            text
            @click="$emit('preview-page', page.page_index)"
          >
            查看此页
          </el-button>
          <el-button
            size="small"
            text
            @click="$emit('open-repair-history', page.page_index)"
          >
            修复历史
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['run-quality-check', 'batch-repair', 'preview-page', 'repair-page', 'open-repair-history'])

defineProps({
  qualityReport: { type: Object, required: true },
  qualityChecking: { type: Boolean, default: false },
  batchRepairableCount: { type: Number, default: 0 },
  batchRepairing: { type: Boolean, default: false },
  qualityPriorityGroups: { type: Array, default: () => [] },
  htmlQualityGate: { type: Object, default: () => ({}) },
  htmlQualityGateItems: { type: Array, default: () => [] },
  qualityPages: { type: Array, default: () => [] },
  repairingPageIndex: { type: [Number, String], default: '' },
  qualityStatusClass: { type: Function, required: true },
  qualityStatusText: { type: Function, required: true },
  qualityPriorityLevel: { type: Function, required: true },
  qualityPriorityReason: { type: Function, required: true },
  normalizeChecks: { type: Function, required: true },
  pageRiskBadges: { type: Function, required: true },
  failedCheckMessages: { type: Function, required: true },
  strategyText: { type: Function, required: true },
  resolvedRepairRouteReason: { type: Function, required: true },
  repairRouteLabel: { type: Function, required: true },
  inferCurrentRepairRoute: { type: Function, required: true },
  pageIssueProfileSummary: { type: Function, required: true },
  repairActionButtonText: { type: Function, required: true },
  gateActionText: { type: Function, required: true },
  gateCheckText: { type: Function, required: true },
  getOutlineTitle: { type: Function, required: true }
})
</script>

<style scoped>
.quality-panel {
  display: grid;
  gap: 20px;
}

.quality-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  padding: 24px 26px;
  border-radius: 28px;
  border: 1px solid rgba(59, 130, 246, 0.18);
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.92), rgba(255, 255, 255, 0.98));
}

.quality-hero.is-warning {
  border-color: rgba(245, 158, 11, 0.26);
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.92), rgba(255, 255, 255, 0.98));
}

.quality-hero.is-fail {
  border-color: rgba(239, 68, 68, 0.24);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.94), rgba(255, 255, 255, 0.98));
}

.quality-hero h2,
.quality-priority-head h3,
.html-gate-head h3 {
  margin: 6px 0 10px;
  color: #0f172a;
}

.quality-hero p,
.quality-priority-head p,
.html-gate-head p {
  margin: 0;
  color: #475569;
  line-height: 1.75;
}

.quality-hero > strong,
.html-gate-head > strong {
  font-size: 42px;
  line-height: 1;
  color: #0f172a;
}

.quality-hero-actions,
.quality-priority-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.quality-priority-board,
.html-gate-card {
  padding: 22px 24px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.quality-priority-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.quality-priority-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.98);
}

.quality-priority-card.P0 {
  border-color: rgba(248, 113, 113, 0.28);
  background: rgba(254, 242, 242, 0.98);
}

.quality-priority-card.P1 {
  border-color: rgba(250, 204, 21, 0.28);
  background: rgba(255, 251, 235, 0.98);
}

.quality-priority-card.P2 {
  border-color: rgba(59, 130, 246, 0.2);
  background: rgba(239, 246, 255, 0.98);
}

.priority-card-head,
.html-gate-head,
.quality-page-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.priority-card-head span,
.html-gate-item span,
.quality-page-head span {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.priority-card-head strong,
.quality-page-head strong {
  color: #0f172a;
  font-size: 20px;
}

.quality-priority-card h4,
.html-gate-item h4,
.quality-page-head h3 {
  margin: 8px 0;
  color: #0f172a;
}

.quality-priority-card p,
.html-gate-item p,
.quality-card-brief em,
.quality-fix,
.quality-issue-profile p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.priority-page-links,
.html-gate-tags,
.quality-checks,
.quality-risk-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.priority-page-links button,
.html-gate-tags span,
.quality-checks span,
.risk-badge {
  border: 0;
  border-radius: 999px;
  padding: 8px 12px;
  font-weight: 700;
}

.priority-page-links button {
  cursor: pointer;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.html-gate-tags span,
.quality-checks span {
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.quality-checks span.pass {
  background: rgba(74, 222, 128, 0.16);
  color: #166534;
}

.risk-badge {
  background: rgba(248, 113, 113, 0.12);
  color: #b91c1c;
}

.priority-empty {
  margin-top: 14px;
  color: #94a3b8;
}

.html-gate-list,
.quality-page-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.html-gate-item,
.quality-page-card {
  padding: 18px 20px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(255, 255, 255, 0.96);
}

.quality-page-card.is-warning {
  border-color: rgba(250, 204, 21, 0.28);
}

.quality-page-card.is-fail {
  border-color: rgba(248, 113, 113, 0.28);
}

.quality-page-card.P0 {
  box-shadow: inset 3px 0 0 rgba(239, 68, 68, 0.72);
}

.quality-page-card.P1 {
  box-shadow: inset 3px 0 0 rgba(245, 158, 11, 0.72);
}

.quality-page-card.P2 {
  box-shadow: inset 3px 0 0 rgba(59, 130, 246, 0.72);
}

.quality-card-brief,
.quality-issues,
.quality-issue-profile,
.quality-actions {
  margin-top: 14px;
}

.quality-card-brief {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.quality-card-brief span {
  color: #0f172a;
  font-weight: 700;
}

.quality-fix-warning {
  color: #b45309;
}

.quality-issues p {
  margin: 0 0 8px;
  color: #92400e;
}

.quality-issue-profile strong {
  display: block;
  margin-bottom: 6px;
  color: #0f172a;
}

.quality-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 980px) {
  .quality-hero,
  .quality-priority-head,
  .quality-hero-actions,
  .quality-card-brief {
    grid-template-columns: 1fr;
    display: grid;
  }

  .quality-priority-grid {
    grid-template-columns: 1fr;
  }
}
</style>
