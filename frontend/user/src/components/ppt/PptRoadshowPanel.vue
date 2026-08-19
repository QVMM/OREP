<template>
  <div class="roadshow-panel">
    <div class="roadshow-hero" :class="roadshowStatusClass(roadshowStructure.status)">
      <div>
        <span class="quality-eyebrow">整套路演结构体检</span>
        <h2>{{ roadshowStatusText(roadshowStructure.status) }}</h2>
        <p>{{ roadshowStructure.summary }}</p>
        <small v-if="roadshowStructure.generated_at" class="report-freshness">
          当前展示为最近一次保存结果 · {{ roadshowStructure.generated_at }}
        </small>
        <div class="quality-hero-actions">
          <el-button size="small" :loading="roadshowChecking" @click="$emit('run-check')">
            重新体检
          </el-button>
        </div>
      </div>
      <strong>{{ roadshowStructure.score ?? '-' }}</strong>
    </div>

    <div class="roadshow-story-map">
      <div class="roadshow-story-head">
        <div>
          <span class="quality-eyebrow">60 分钟比赛故事线</span>
          <h3>把“汇报 + 实操”组织成裁判容易打分的叙事路径</h3>
          <p>建议先讲清政策和问题，再证明方案与技术，随后进入实操证据，最后收束价值、团队和答辩。</p>
        </div>
        <strong>{{ roadshowStorylineCoverage.ready }}/{{ roadshowStorylineCoverage.total }}</strong>
      </div>
      <div class="roadshow-story-track">
        <div
          v-for="phase in roadshowStoryPhases"
          :key="phase.key"
          class="story-phase-card"
          :class="[phase.status, { active: phase.page_indices.includes(currentPageIndex) }]"
        >
          <div class="story-phase-index">{{ phase.order }}</div>
          <div class="story-phase-main">
            <span>{{ phase.minutes }} 分钟 · {{ phase.required ? '必备' : '增强' }}</span>
            <h4>{{ phase.name }}</h4>
            <p>{{ phase.goal }}</p>
            <div v-if="phase.sequence_events.length" class="story-phase-alerts">
              <span>{{ phase.sequence_events.length }} 个顺序提醒</span>
              <em>{{ phase.sequence_events[0].message }}</em>
            </div>
            <div class="story-phase-pages">
              <button
                v-for="pageIndex in phase.page_indices.slice(0, 6)"
                :key="pageIndex"
                type="button"
                @click="$emit('preview-page', pageIndex)"
              >
                第{{ pageIndex }}页
              </button>
              <em v-if="!phase.page_indices.length">{{ phase.missing_hint }}</em>
            </div>
          </div>
          <strong>{{ storyPhaseStatusText(phase.status) }}</strong>
        </div>
      </div>
    </div>

    <div v-if="roadshowStructure.priority_actions?.length" class="roadshow-actions">
      <h3>优先优化建议</h3>
      <div
        v-for="action in roadshowStructure.priority_actions"
        :key="`${action.module}-${action.action}`"
        class="roadshow-action-item"
        :class="action.priority"
      >
        <strong>{{ action.module }}</strong>
        <span>{{ action.action }}</span>
      </div>
    </div>

    <div class="roadshow-module-grid">
      <div
        v-for="module in roadshowStructure.modules"
        :key="module.key"
        class="roadshow-module-card"
        :class="module.status"
      >
        <div class="roadshow-module-head">
          <div>
            <span>{{ module.required ? '必备模块' : '增强模块' }}</span>
            <h3>{{ module.name }}</h3>
          </div>
          <strong>{{ roadshowModuleStatusText(module.status) }}</strong>
        </div>
        <p>{{ module.hint }}</p>
        <div class="roadshow-pages">
          <span v-if="!module.page_indices?.length">暂无明确支撑页</span>
          <span v-for="pageIndex in module.page_indices || []" :key="pageIndex">第 {{ pageIndex }} 页</span>
        </div>
      </div>
    </div>

    <div class="roadshow-sequence">
      <h3>叙事顺序检查</h3>
      <div
        v-for="event in roadshowSequenceEvents"
        :key="`${event.code}-${event.page_index || 'all'}-${event.message}`"
        class="sequence-event"
        :class="event.severity"
      >
        <div>
          <span>{{ sequenceSeverityText(event.severity) }} · {{ sequenceEventPhaseName(event) }}</span>
          <h4>{{ event.message }}</h4>
          <p>{{ event.suggested_action }}</p>
        </div>
        <el-button
          v-if="event.page_index"
          size="small"
          text
          @click="$emit('preview-page', event.page_index)"
        >
          查看第 {{ event.page_index }} 页
        </el-button>
      </div>
      <template v-if="!roadshowSequenceEvents.length">
        <p v-for="issue in roadshowStructure.sequence?.issues || []" :key="issue">{{ issue }}</p>
      </template>
    </div>

    <div v-if="roadshowStructure.pacing" class="roadshow-pacing">
      <div class="roadshow-pacing-head">
        <div>
          <span class="quality-eyebrow">讲解节奏检查</span>
          <h3>{{ pacingStatusText(roadshowStructure.pacing.status) }}</h3>
          <p>{{ roadshowStructure.pacing.summary }}</p>
        </div>
        <strong>{{ roadshowStructure.pacing.estimated_total_minutes }} 分钟</strong>
      </div>
      <div class="pacing-metrics">
        <div>
          <span>目标时长</span>
          <strong>{{ roadshowStructure.pacing.target_minutes }} 分钟</strong>
        </div>
        <div>
          <span>信息偏密</span>
          <strong>{{ roadshowStructure.pacing.dense_pages?.length || 0 }} 页</strong>
        </div>
        <div>
          <span>信息偏薄</span>
          <strong>{{ roadshowStructure.pacing.thin_pages?.length || 0 }} 页</strong>
        </div>
        <div>
          <span>重复/跳跃</span>
          <strong>{{ (roadshowStructure.pacing.repeated_pairs?.length || 0) + (roadshowStructure.pacing.jump_pairs?.length || 0) }} 组</strong>
        </div>
      </div>
      <div class="pacing-issues">
        <p v-for="issue in roadshowStructure.pacing.issues || []" :key="issue">{{ issue }}</p>
      </div>
      <div class="pacing-page-list">
        <button
          v-for="page in roadshowStructure.pacing.pages || []"
          :key="page.page_index"
          :class="['pacing-page-chip', page.density]"
          @click="$emit('preview-page', page.page_index)"
        >
          <span>第 {{ page.page_index }} 页</span>
          <strong>{{ page.estimated_seconds }}s</strong>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['run-check', 'preview-page'])

defineProps({
  roadshowStructure: { type: Object, required: true },
  roadshowChecking: { type: Boolean, default: false },
  roadshowStoryPhases: { type: Array, default: () => [] },
  roadshowStorylineCoverage: { type: Object, default: () => ({ total: 0, ready: 0 }) },
  roadshowSequenceEvents: { type: Array, default: () => [] },
  currentPageIndex: { type: Number, default: 1 },
  roadshowStatusClass: { type: Function, required: true },
  roadshowStatusText: { type: Function, required: true },
  storyPhaseStatusText: { type: Function, required: true },
  roadshowModuleStatusText: { type: Function, required: true },
  sequenceSeverityText: { type: Function, required: true },
  sequenceEventPhaseName: { type: Function, required: true },
  pacingStatusText: { type: Function, required: true }
})
</script>

<style scoped>
.roadshow-panel {
  display: grid;
  gap: 20px;
}

.roadshow-hero,
.roadshow-story-map,
.roadshow-actions,
.roadshow-sequence,
.roadshow-pacing {
  padding: 22px 24px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.96);
}

.roadshow-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
}

.roadshow-hero.is-ready {
  border-color: rgba(74, 222, 128, 0.24);
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.92), rgba(255, 255, 255, 0.98));
}

.roadshow-hero.is-needs_focus {
  border-color: rgba(250, 204, 21, 0.24);
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.92), rgba(255, 255, 255, 0.98));
}

.roadshow-hero.is-at_risk {
  border-color: rgba(248, 113, 113, 0.24);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.94), rgba(255, 255, 255, 0.98));
}

.roadshow-hero h2,
.roadshow-story-head h3,
.roadshow-pacing-head h3,
.roadshow-sequence h3 {
  margin: 6px 0 10px;
  color: #0f172a;
}

.roadshow-hero p,
.roadshow-story-head p,
.roadshow-pacing-head p,
.sequence-event p {
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

.roadshow-hero strong,
.roadshow-story-head strong,
.roadshow-pacing-head strong {
  color: #0f172a;
  font-size: 42px;
  line-height: 1;
}

.quality-hero-actions,
.roadshow-story-head,
.roadshow-pacing-head,
.roadshow-module-head,
.sequence-event {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.roadshow-story-track,
.roadshow-module-grid,
.pacing-metrics,
.pacing-page-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.story-phase-card,
.roadshow-module-card,
.roadshow-action-item,
.sequence-event {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.98);
}

.story-phase-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
}

.story-phase-card.active {
  border-color: rgba(37, 99, 235, 0.24);
}

.story-phase-index {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-weight: 800;
}

.story-phase-main > span,
.roadshow-module-head span,
.sequence-event span {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.story-phase-main h4,
.roadshow-module-head h3,
.sequence-event h4 {
  margin: 8px 0;
  color: #0f172a;
}

.story-phase-main p,
.roadshow-module-card p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.story-phase-pages,
.roadshow-pages,
.story-phase-alerts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.story-phase-pages button,
.roadshow-pages span,
.story-phase-alerts span,
.story-phase-alerts em,
.pacing-page-chip {
  border: 0;
  border-radius: 999px;
  padding: 8px 12px;
  font-weight: 700;
}

.story-phase-pages button,
.pacing-page-chip {
  cursor: pointer;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.roadshow-pages span,
.story-phase-alerts span,
.story-phase-alerts em {
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
  font-style: normal;
}

.roadshow-actions h3 {
  margin: 0 0 14px;
  color: #0f172a;
}

.roadshow-action-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.roadshow-action-item strong {
  color: #0f172a;
}

.roadshow-action-item span {
  color: #475569;
}

.roadshow-module-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.sequence-event.warning {
  border-color: rgba(250, 204, 21, 0.24);
}

.sequence-event.fail {
  border-color: rgba(248, 113, 113, 0.24);
}

.pacing-metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.pacing-metrics > div {
  padding: 14px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.pacing-metrics span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.pacing-metrics strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 20px;
}

.pacing-issues {
  margin-top: 16px;
}

.pacing-issues p {
  margin: 0 0 8px;
  color: #475569;
}

.pacing-page-list {
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
}

.pacing-page-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pacing-page-chip.dense {
  background: rgba(248, 113, 113, 0.12);
  color: #b91c1c;
}

.pacing-page-chip.thin {
  background: rgba(250, 204, 21, 0.16);
  color: #b45309;
}

@media (max-width: 980px) {
  .roadshow-hero,
  .roadshow-story-head,
  .roadshow-pacing-head,
  .story-phase-card,
  .sequence-event,
  .roadshow-action-item {
    grid-template-columns: 1fr;
    display: grid;
  }

  .roadshow-module-grid,
  .pacing-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
