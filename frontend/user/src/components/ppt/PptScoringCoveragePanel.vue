<template>
  <div class="coverage-panel">
    <div v-if="scoringDashboard" class="scoring-dashboard-hero" :class="scoringDashboardStatusClass(scoringDashboard.status)">
      <div>
        <span class="quality-eyebrow">评委视角评分点总控</span>
        <h2>{{ scoringDashboardStatusText(scoringDashboard.status) }}</h2>
        <p>{{ scoringDashboard.summary }}</p>
        <small v-if="scoringDashboard.generated_at" class="report-freshness">
          当前展示为最近一次保存结果 · {{ scoringDashboard.generated_at }}
        </small>
        <div class="quality-hero-actions">
          <el-button size="small" :loading="scoringDashboardChecking" @click="$emit('run-dashboard-check')">
            重新生成看板
          </el-button>
        </div>
      </div>
      <strong>{{ scoringDashboard.score ?? '-' }}</strong>
    </div>

    <div v-if="scoringDashboard?.priority_actions?.length" class="scoring-risk-actions">
      <h3>优先补强比赛评分证据</h3>
      <div
        v-for="action in scoringDashboard.priority_actions"
        :key="`${action.category}-${action.point_name}`"
        class="scoring-risk-action"
        :class="action.risk_level"
      >
        <strong>{{ action.point_name }}</strong>
        <span>{{ action.action }}</span>
      </div>
    </div>

    <div class="judge-matrix">
      <div class="judge-matrix-head">
        <div>
          <span class="quality-eyebrow">评委评分风险矩阵</span>
          <h3>按 2025 评分表五大类看丢分风险</h3>
          <p>优先补强高权重、高风险、缺少比赛评分证据支撑的评分项，避免页面好看但评委看不到得分依据。</p>
        </div>
        <strong>100 分</strong>
      </div>
      <div class="judge-matrix-grid">
        <div
          v-for="category in judgeScoringCategories"
          :key="category.key"
          class="judge-category-card"
          :class="[category.risk_level, { active: judgeCategoryHasHighlightedPoint(category) }]"
        >
          <div class="judge-category-head">
            <div>
              <span>{{ category.weight }} 分 · {{ riskLevelText(category.risk_level) }}</span>
              <h4>{{ category.name }}</h4>
            </div>
            <strong>{{ category.covered_count }}/{{ category.total_count }}</strong>
          </div>
          <p>{{ category.description }}</p>
          <div class="judge-category-metrics">
            <span>高风险 {{ category.high_risk_count }} 项</span>
            <span>素材 {{ category.material_count }} 个</span>
            <span>支撑页 {{ category.page_indices.length }} 页</span>
          </div>
          <div class="judge-point-list">
            <button
              v-for="point in category.points.slice(0, 4)"
              :key="point.point_id || point.point_name"
              type="button"
              :class="[point.risk_level || (point.covered ? 'low' : 'high'), { active: scoringPointMatches(point.point_name) }]"
              @click="point.page_indices?.length && $emit('preview-page', point.page_indices[0])"
            >
              {{ point.point_name }}
            </button>
          </div>
          <em>{{ category.action }}</em>
        </div>
      </div>
    </div>

    <div v-if="scoringDashboard?.items?.length" class="scoring-risk-grid">
      <div
        v-for="item in scoringDashboard.items"
        :key="item.point_id"
        class="scoring-risk-card"
        :class="[item.risk_level, { active: scoringPointMatches(item.point_name) }]"
      >
        <div class="scoring-risk-head">
          <div>
            <span>{{ item.category }} · {{ item.required ? '必备' : '增强' }}</span>
            <h3>{{ item.point_name }}</h3>
          </div>
          <strong>{{ riskLevelText(item.risk_level) }}</strong>
        </div>
        <p>{{ item.action }}</p>
        <div class="scoring-risk-reasons">
          <span v-for="reason in item.risk_reasons" :key="reason">{{ reason }}</span>
        </div>
        <div class="scoring-risk-meta">
          <span>支撑页：{{ item.page_indices?.length ? targetPagesText(item.page_indices) : '暂无' }}</span>
          <span>证据素材：{{ item.material_count || 0 }} 个</span>
        </div>
      </div>
    </div>

    <div class="coverage-hero">
      <div>
        <span class="quality-eyebrow">比赛评分点覆盖矩阵</span>
        <h2>比赛必备评分点覆盖 {{ scoringCoverage.required_coverage_rate || '0%' }}</h2>
        <p>
          已覆盖 {{ scoringCoverage.covered || 0 }}/{{ scoringCoverage.total_points || 0 }} 个评分点，
          必备项 {{ scoringCoverage.required_covered || 0 }}/{{ scoringCoverage.required_points || 0 }} 个。
          这里用于判断路演内容是否真正服务比赛评分表，并具备可验证的得分证据，而不是只做了好看的页面。
        </p>
      </div>
      <strong>{{ scoringCoverage.coverage_rate || '0%' }}</strong>
    </div>

    <div v-if="missingRequired.length" class="missing-box">
      <h3>优先补齐的比赛评分证据</h3>
      <div
        v-for="item in missingRequired"
        :key="`${item.category}-${item.point_name}`"
        class="missing-item"
        :class="{ active: scoringPointMatches(item.point_name) }"
        :data-scoring-point="item.point_name"
      >
        <strong>{{ item.point_name }}</strong>
        <span>{{ item.hint }}</span>
      </div>
    </div>

    <div class="coverage-list">
      <div
        v-for="item in scoringCoverage.items"
        :key="item.point_id"
        class="coverage-card"
        :class="{ covered: item.covered, required: item.required, active: scoringPointMatches(item.point_name) }"
        :data-scoring-point="item.point_name"
      >
        <div class="coverage-card-head">
          <div>
            <span>{{ item.category }} · {{ item.required ? '必备' : '增强' }}</span>
            <h3>{{ item.point_name }}</h3>
          </div>
          <strong>{{ item.covered ? '已覆盖' : '缺失' }}</strong>
        </div>
        <p>{{ item.covered ? coverageEvidenceText(item) : item.hint }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['run-dashboard-check', 'preview-page'])

defineProps({
  scoringCoverage: { type: Object, required: true },
  scoringDashboard: { type: Object, default: null },
  scoringDashboardChecking: { type: Boolean, default: false },
  judgeScoringCategories: { type: Array, default: () => [] },
  missingRequired: { type: Array, default: () => [] },
  scoringDashboardStatusClass: { type: Function, required: true },
  scoringDashboardStatusText: { type: Function, required: true },
  judgeCategoryHasHighlightedPoint: { type: Function, required: true },
  riskLevelText: { type: Function, required: true },
  scoringPointMatches: { type: Function, required: true },
  targetPagesText: { type: Function, required: true },
  coverageEvidenceText: { type: Function, required: true }
})
</script>

<style scoped>
.coverage-panel {
  display: grid;
  gap: 20px;
}

.scoring-dashboard-hero,
.judge-matrix,
.coverage-hero,
.missing-box {
  padding: 22px 24px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.scoring-dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
}

.scoring-dashboard-hero.is-stable {
  border-color: rgba(74, 222, 128, 0.24);
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.92), rgba(255, 255, 255, 0.98));
}

.scoring-dashboard-hero.is-watch {
  border-color: rgba(250, 204, 21, 0.24);
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.92), rgba(255, 255, 255, 0.98));
}

.scoring-dashboard-hero.is-high_risk {
  border-color: rgba(248, 113, 113, 0.24);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.94), rgba(255, 255, 255, 0.98));
}

.scoring-dashboard-hero h2,
.judge-matrix-head h3,
.coverage-hero h2,
.missing-box h3 {
  margin: 6px 0 10px;
  color: #0f172a;
}

.scoring-dashboard-hero p,
.judge-matrix-head p,
.coverage-hero p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.report-freshness {
  display: block;
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}

.scoring-dashboard-hero strong,
.judge-matrix-head strong,
.coverage-hero strong {
  color: #0f172a;
  font-size: 42px;
  line-height: 1;
}

.quality-hero-actions,
.judge-matrix-head,
.judge-category-head,
.scoring-risk-head,
.coverage-card-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.scoring-risk-actions,
.scoring-risk-grid,
.coverage-list {
  display: grid;
  gap: 14px;
}

.scoring-risk-action,
.judge-category-card,
.scoring-risk-card,
.coverage-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.98);
}

.scoring-risk-action {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.judge-matrix-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.judge-category-card.active,
.scoring-risk-card.active,
.missing-item.active,
.coverage-card.active {
  border-color: rgba(37, 99, 235, 0.28);
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.1) inset;
}

.judge-category-card h4,
.scoring-risk-head h3,
.coverage-card-head h3 {
  margin: 8px 0;
  color: #0f172a;
}

.judge-category-card p,
.scoring-risk-card p,
.coverage-card p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.judge-category-metrics,
.judge-point-list,
.scoring-risk-reasons,
.scoring-risk-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.judge-category-metrics span,
.judge-point-list button,
.scoring-risk-reasons span,
.scoring-risk-meta span,
.missing-item strong,
.missing-item span {
  border-radius: 999px;
  padding: 8px 12px;
  font-weight: 700;
}

.judge-category-metrics span,
.scoring-risk-reasons span,
.scoring-risk-meta span {
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.judge-point-list button {
  cursor: pointer;
  border: 0;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.judge-point-list button.high {
  background: rgba(248, 113, 113, 0.12);
  color: #b91c1c;
}

.judge-point-list button.low {
  background: rgba(74, 222, 128, 0.16);
  color: #166534;
}

.scoring-risk-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.missing-box {
  display: grid;
  gap: 12px;
}

.missing-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(251, 191, 36, 0.24);
  background: rgba(255, 251, 235, 0.92);
}

.missing-item strong {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.missing-item span {
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.coverage-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.coverage-card.covered {
  border-color: rgba(74, 222, 128, 0.24);
  background: rgba(240, 253, 244, 0.92);
}

.coverage-card.required:not(.covered) {
  border-color: rgba(248, 113, 113, 0.24);
}

@media (max-width: 980px) {
  .scoring-dashboard-hero,
  .judge-matrix-head,
  .scoring-risk-action,
  .judge-category-head,
  .scoring-risk-head,
  .coverage-card-head,
  .missing-item {
    grid-template-columns: 1fr;
    display: grid;
  }

  .judge-matrix-grid,
  .scoring-risk-grid,
  .coverage-list {
    grid-template-columns: 1fr;
  }
}
</style>
