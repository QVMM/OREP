<template>
  <AiScoreReportShell title="五维评分" subtitle="按评分表定位扣分与整改">
    <div class="page-stack">
      <section class="score-summary" aria-label="评分表关键摘要">
        <article v-for="metric in metrics" :key="metric.label" :class="['summary-item', metric.tone]">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="dimension-workbench">
        <aside class="dimension-index panel-block">
          <div class="section-head">
            <span>评分导航</span>
            <strong>五维评分表</strong>
            <p>按维度查看扣分项</p>
          </div>
          <div v-if="dimensionRows.length" class="dimension-list">
            <button
              v-for="dim in dimensionRows"
              :key="dim.key"
              type="button"
              :class="['dimension-row', dim.tone, { active: dim.key === report.selectedDimensionKey.value }]"
              @click="report.selectedDimensionKey.value = dim.key"
            >
              <span class="dimension-name">{{ dim.name }}</span>
              <b>{{ dim.score }}/{{ dim.maxScore }}</b>
              <small>{{ dim.gapText }}</small>
              <i aria-hidden="true"><em :style="{ width: `${dim.percent}%` }"></em></i>
              <mark>{{ dim.deductionCount }}个扣分点</mark>
            </button>
          </div>
          <AiScoreEmptyState v-else title="暂无维度评分" description="报告未返回维度拆解数据。" />
        </aside>

        <main class="score-table-panel panel-block">
          <div class="table-hero">
            <div class="table-title">
              <span>当前维度</span>
              <h2>{{ selectedName }}评分表</h2>
              <p>逐项定位扣分原因、整改动作与验收标准。</p>
            </div>
            <div class="table-score">
              <strong>{{ selectedScore }}</strong>
              <span>本维度差距 {{ selectedGapText }}</span>
            </div>
          </div>

          <div class="dimension-progress" aria-label="当前维度得分进度">
            <em :style="{ width: `${selectedPercent}%` }"></em>
          </div>

          <div class="table-meta">
            <div><span>评分项</span><b>{{ selectedItemRows.length }} 项</b></div>
            <div><span>关联证据</span><b>{{ selectedEvidenceCount }} 条</b></div>
            <div><span>扣分点</span><b>{{ selectedDeductionPointCount }} 个</b></div>
          </div>

          <section class="rule-observation-panel">
            <div class="rule-panel-head">
              <div>
                <span>规则引擎观测点</span>
                <strong>{{ ruleEngine.statusText }}</strong>
              </div>
              <p>{{ ruleEngine.diffReasonText }}</p>
            </div>
            <div v-if="selectedObservationRows.length" class="observation-table">
              <article v-for="item in selectedObservationRows" :key="item.id" class="observation-row">
                <div>
                  <b>{{ item.name }}</b>
                  <small>{{ item.modelReason }}</small>
                </div>
                <span>{{ item.evidenceLevelLabel }}</span>
                <strong>{{ item.rawScoreText }} / {{ item.capText }}</strong>
                <em :class="{ capped: item.isCapped }">{{ item.isCapped ? '证据封顶' : item.evidenceCapText }}</em>
                <button type="button" @click="openObservationEvidence(item)">{{ item.evidenceAnchorIds.length || item.deductions.length }} 条证据</button>
              </article>
            </div>
            <p v-else class="rule-empty">历史报告未生成规则引擎观测点，仍可查看原五维评分表。</p>
          </section>

          <div v-if="selectedItemRows.length" class="rubric-table">
            <div class="rubric-head">
              <span>评分项</span>
              <span>满分</span>
              <span>得分</span>
              <span>扣分位置</span>
              <span>扣分原因</span>
              <span>怎么改</span>
              <span>验收标准</span>
              <span>证据</span>
            </div>
            <article v-for="item in selectedItemRows" :key="item.id" class="rubric-row">
              <div class="item-name">
                <b>{{ item.name }}</b>
                <small>{{ selectedName }}</small>
              </div>
              <span class="cell-max">{{ item.maxText }}</span>
              <strong :class="['cell-score', item.tone]">{{ item.scoreText }}</strong>
              <span :class="['deduction-tag', item.tone]">{{ item.deductionLocation }}</span>
              <p class="reason-copy">{{ item.reason }}</p>
              <p class="fix-copy">{{ item.fixAction }}</p>
              <p class="acceptance-copy">{{ item.acceptance }}</p>
              <button type="button" @click="openEvidence(item)">{{ item.evidenceText }}</button>
            </article>
          </div>
          <AiScoreEmptyState v-else title="暂无评分项" description="当前维度未返回评分项明细，可先查看证据链和改进方案。" />

          <div class="table-action-bar">
            <p><span>本维度优先整改</span>{{ prioritySummary }}</p>
            <div>
              <RouterLink class="primary-action" :to="report.sectionPath('actions')">按扣分点生成整改任务</RouterLink>
              <RouterLink class="secondary-action" :to="report.sectionPath('evidence')">查看证据链</RouterLink>
            </div>
          </div>
        </main>
      </section>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreEmptyState from '../../components/ai-score/report/AiScoreEmptyState.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'
import { findFrameByAnchor } from '../../utils/aiScoreFrameMatching'

const router = useRouter()
const report = useAiScoreReportContext()
const ruleEngine = computed(() => report.ruleEngineReport.value)

const selectedName = computed(() => report.selectedDimension.value?.name || '评分维度')
const selectedScore = computed(() => {
  const dimension = report.selectedDimension.value
  if (!dimension) return '-'
  return `${report.formatNumber(dimension.score, 1)}/${dimension.maxScore || 100}`
})
const dimensionRows = computed(() => report.dimensions.value.map(dim => {
  const maxScore = Number(dim.maxScore || 100)
  const score = Number(dim.score || 0)
  const gap = Math.max(0, maxScore - score)
  const deductionCount = countDeductionPoints(dim)
  return {
    ...dim,
    score: report.formatNumber(score, 1),
    maxScore,
    percent: Math.min(100, dim.percent || (maxScore ? score / maxScore * 100 : 0)),
    gap,
    gapText: gap ? `差 ${report.formatNumber(gap, 1)}` : '满分',
    deductionCount,
    tone: gap >= maxScore * 0.4 ? 'danger' : gap >= maxScore * 0.2 ? 'warning' : 'ok'
  }
}))
const maxGap = computed(() => [...dimensionRows.value].sort((a, b) => b.gap - a.gap)[0])
const selectedEvidenceCount = computed(() => evidenceForDimension(report.selectedDimension.value).length)
const selectedDeductionCount = computed(() => deductionsForDimension(report.selectedDimension.value).length)
const selectedDeductionPointCount = computed(() => Math.max(selectedDeductionCount.value, selectedItemRows.value.filter(item => item.hasDeduction).length))
const selectedObservationRows = computed(() => {
  const selected = report.selectedDimension.value
  if (!selected) return ruleEngine.value.observations.slice(0, 15)
  const name = String(selected.name || '').toLowerCase()
  const key = String(selected.key || '').toLowerCase()
  return ruleEngine.value.observations.filter(item => {
    const dimension = String(item.dimensionName || '').toLowerCase()
    return dimension.includes(name) || dimension.includes(key) || name.includes(dimension)
  })
})
const selectedGap = computed(() => {
  const dimension = report.selectedDimension.value
  if (!dimension) return 0
  return Math.max(0, Number(dimension.maxScore || 100) - Number(dimension.score || 0))
})
const selectedGapText = computed(() => selectedGap.value ? report.formatNumber(selectedGap.value, 1) : '0')
const selectedPercent = computed(() => {
  const dimension = report.selectedDimension.value
  if (!dimension) return 0
  const maxScore = Number(dimension.maxScore || 100)
  const score = Number(dimension.score || 0)
  return Math.min(100, maxScore ? score / maxScore * 100 : 0)
})
const targetScore = computed(() => firstPresent(
  report.result.value.target_score,
  report.result.value.targetScore,
  report.scoreRecoverySummary.value.target_score,
  report.scoreRecoverySummary.value.targetScore
))
const recoverable = computed(() => firstPresent(
  report.scoreRecoverySummary.value.recoverable_range,
  report.scoreRecoverySummary.value.recoverableRange,
  report.scoreRecoverySummary.value.recoverable_score,
  report.scoreRecoverySummary.value.recoverableScore
))
const selectedItemRows = computed(() => (report.selectedItems.value || []).map(normalizeScoreItem))
const prioritySummary = computed(() => {
  const names = selectedItemRows.value
    .filter(item => item.hasDeduction)
    .sort((a, b) => Number(a.scoreRatio || 0) - Number(b.scoreRatio || 0))
    .slice(0, 3)
    .map(item => item.deductionLocation)
  return names.length ? names.join('、') : '继续保留高分项，并用证据链补齐可验收材料。'
})
const metrics = computed(() => [
  { label: '当前评分', value: `${report.formatNumber(report.overallScore.value, 1)}/100`, hint: report.scoreLevel.value.label, tone: 'primary' },
  { label: '最大失分维度', value: maxGap.value?.name || '-', hint: maxGap.value ? maxGap.value.gapText : '暂无维度数据', tone: 'warning' },
  { label: '重点扣分项', value: selectedItemRows.value.slice(0, 3).map(item => item.name).join(' / ') || '待识别', hint: selectedName.value, tone: 'danger' },
  { label: '待生成整改', value: `${selectedDeductionPointCount.value || selectedItemRows.value.length} 项`, hint: recoverable.value == null ? '按评分表生成' : `可追回 ${recoverable.value}`, tone: 'success' },
  { label: '目标评分', value: targetScore.value == null ? '待设置' : `${report.formatNumber(targetScore.value, 1)}/100`, hint: targetScore.value == null ? '报告未返回' : '报告目标值' }
])

function normalizeScoreItem(item, index) {
  const score = firstPresent(item.score, item.value, item.current_score, item.currentScore)
  const max = firstPresent(item.max_score, item.maxScore, item.full_score, item.fullScore)
  const reason = firstPresent(item.reason, item.evaluation, item.comment, item.detail, item.issue, '报告未返回该评分项评价。')
  const fixAction = firstPresent(item.suggestion, item.improvement, item.action, item.fix, item.advice, inferFixAction(item, reason))
  const acceptance = firstPresent(item.acceptance, item.acceptanceCriteria, item.acceptance_criteria, item.check, item.validation, inferAcceptance(item, reason), '补齐报告指出的证据缺口，并在下一轮彩排中验证。')
  const evidence = evidenceForText(`${item.name || item.title || ''} ${reason}`)
  const maxNumber = Number(max || 0)
  const scoreNumber = Number(score || 0)
  const scoreRatio = maxNumber ? scoreNumber / maxNumber : 1
  const tone = scoreRatio < 0.6 ? 'danger' : scoreRatio < 0.8 ? 'warning' : 'normal'
  return {
    id: item.id || item.key || `${item.name || item.title || 'score-item'}-${index}`,
    name: item.name || item.title || item.item || '评分项',
    maxText: max ? report.formatNumber(max, 0) : '-',
    scoreText: score === undefined ? '-' : report.formatNumber(score, 1),
    scoreRatio,
    hasDeduction: maxNumber ? scoreNumber < maxNumber : Boolean(reason),
    tone,
    deductionLocation: firstPresent(item.deduction_location, item.deductionLocation, item.issue_type, item.issueType, inferDeductionLocation(item, reason)),
    reason,
    fixAction,
    acceptance,
    evidenceText: evidence.length ? `${evidence.length} 条证据` : '看证据',
    evidence
  }
}

function openEvidence(item) {
  if (item.evidence[0]?.frame) report.selectedEvidenceFrame.value = item.evidence[0].frame
  router.push(report.sectionPath('evidence'))
}

function openObservationEvidence(item) {
  const anchorId = item.evidenceAnchorIds[0] || item.deductions[0]?.evidenceAnchorIds?.[0]
  const anchor = report.structuredEvidenceAnchors.value.find(value => String(value.id) === String(anchorId))
  if (anchor) {
    const frame = findFrame(anchor)
    if (frame) report.selectedEvidenceFrame.value = frame
  }
  router.push(report.sectionPath('evidence'))
}

function evidenceForDimension(dimension) {
  if (!dimension) return []
  return evidenceForText(`${dimension.name} ${dimension.key}`)
}

function deductionsForDimension(dimension) {
  if (!dimension) return []
  const key = `${dimension.name} ${dimension.key}`.toLowerCase()
  return report.currentStructuredDeductions.value.filter(item => `${item.dimension || ''} ${item.dimensionName || ''} ${item.title || ''} ${item.name || ''}`.toLowerCase().includes(dimension.name?.toLowerCase() || '') || key.includes(String(item.dimension || '').toLowerCase()))
}

function countDeductionPoints(dimension) {
  const structuredCount = deductionsForDimension(dimension).length
  const itemCount = (dimension?.items || []).filter(item => {
    const score = Number(firstPresent(item.score, item.value, item.current_score, item.currentScore, 0))
    const max = Number(firstPresent(item.max_score, item.maxScore, item.full_score, item.fullScore, 0))
    return max ? score < max : Boolean(firstPresent(item.reason, item.evaluation, item.comment, item.detail, item.issue))
  }).length
  return Math.max(structuredCount, itemCount)
}

function evidenceForText(text) {
  const query = String(text || '').toLowerCase()
  return [
    ...report.structuredEvidenceAnchors.value.map(item => ({ ...item, frame: findFrame(item) })),
    ...report.evidenceFrames.value.map(frame => ({ title: frame.title, evidenceText: frame.caption, frame }))
  ].filter(item => `${item.dimension || ''} ${item.title || ''} ${item.anchorTitle || ''} ${item.evidenceText || ''} ${item.summary || ''}`.toLowerCase().split(/\s+/).some(part => part && query.includes(part)))
}

function findFrame(anchor) {
  return findFrameByAnchor(anchor, report.evidenceFrames.value, { sessionId: report.effectiveSessionId.value })
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function inferDeductionLocation(item, reason) {
  const text = `${item.name || item.title || ''} ${reason || ''}`
  if (/标准|规范|合规|流程|引用/.test(text)) return '标准引用缺失'
  if (/停顿|填充词|犹豫|重复|卡顿|熟练/.test(text)) return '口头犹豫与重复'
  if (/难度|技术栈|复杂|集成|高并发|部署|模型/.test(text)) return '技术难点未展开'
  if (/先进|前沿|选型|对比|AI|RAG|实时/.test(text)) return '前沿性证明不足'
  if (/语速|讲解|表达|节奏|互动/.test(text)) return '表达节奏影响呈现'
  return '评分证据不足'
}

function inferFixAction(item, reason) {
  const text = `${item.name || item.title || ''} ${reason || ''}`
  if (/标准|规范|合规|流程|引用/.test(text)) return '补充标准名称、检查表或合规依据，并在路演中明确引用。'
  if (/停顿|填充词|犹豫|重复|卡顿|熟练/.test(text)) return '围绕关键操作录制三轮演练，压缩重复表达，保留一次流畅版本。'
  if (/难度|技术栈|复杂|集成|高并发|部署|模型/.test(text)) return '拆出2个技术难点，说明方案、取舍和实际运行效果。'
  if (/先进|前沿|选型|对比|AI|RAG|实时/.test(text)) return '增加技术选型对比或前沿能力展示，让评委看到先进性证据。'
  if (/语速|讲解|表达|节奏|互动/.test(text)) return '重点段放慢语速，减少填充词，并加入评委可感知的停顿。'
  return '把扣分原因转成一条可执行任务，并在下一轮彩排中复测。'
}

function inferAcceptance(item, reason) {
  const text = `${item.name || item.title || ''} ${reason || ''}`
  if (/标准|规范|合规|流程|引用/.test(text)) return '能展示标准文档片段或检查表，并说清对应环节。'
  if (/停顿|填充词|犹豫|重复|卡顿|熟练/.test(text)) return '关键步骤连续讲完，无明显卡顿、重复和长停顿。'
  if (/难度|技术栈|复杂|集成|高并发|部署|模型/.test(text)) return '至少讲清2个技术难点、解决方案和效果验证。'
  if (/先进|前沿|选型|对比|AI|RAG|实时/.test(text)) return '有技术对比表或实际效果截图支撑先进性。'
  if (/语速|讲解|表达|节奏|互动/.test(text)) return '重点段语速稳定，填充词明显减少，逻辑停顿清晰。'
  return '下一轮彩排能提供证据材料或现场演示结果。'
}
</script>

<style scoped>
.page-stack { display: grid; gap: 10px; min-width: 0; }
.panel-block { min-width: 0; border: 1px solid #e2d8cf; border-radius: 8px; background: #fffdfa; box-shadow: 0 12px 34px rgba(82, 61, 46, .045); }
.score-summary { display: grid; grid-template-columns: 1fr .95fr 1.25fr .78fr .75fr; overflow: hidden; border: 1px solid #e2d8cf; border-radius: 8px; background: #fffdfa; }
.summary-item { min-height: 58px; padding: 9px 14px; border-right: 1px solid #efe7df; }
.summary-item:last-child { border-right: 0; }
.summary-item span, .summary-item small { display: block; color: #6c7280; font-size: 11px; line-height: 1.25; }
.summary-item strong { display: block; overflow: hidden; margin: 4px 0 2px; color: #182033; font-size: 20px; line-height: 1; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
.summary-item.primary strong { color: #e85d2a; }
.summary-item.warning strong { color: #e85d2a; }
.summary-item.danger strong { color: #be3d2b; font-size: 16px; }
.summary-item.success strong { color: #15835f; }
.dimension-workbench { display: grid; grid-template-columns: 270px minmax(0, 1fr); gap: 10px; min-width: 0; align-items: start; }
.dimension-index { position: sticky; top: 76px; padding: 12px; }
.section-head { display: grid; gap: 3px; margin-bottom: 10px; }
.section-head span, .table-title span { justify-self: start; padding: 2px 7px; border-radius: 999px; background: #fff0e8; color: #c6532d; font-size: 10px; font-weight: 900; letter-spacing: 0; }
.section-head strong { margin: 0; color: #182033; font-size: 16px; letter-spacing: 0; }
.section-head p { margin: 0; color: #7b8495; font-size: 11px; line-height: 1.25; }
.dimension-list { display: grid; gap: 7px; }
.dimension-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-areas: "name score" "bar gap" "badge badge"; gap: 6px 8px; align-items: center; width: 100%; min-width: 0; padding: 9px 10px; border: 1px solid #ece4dc; border-radius: 7px; background: #fff; color: #182033; text-align: left; cursor: pointer; transition: border-color .18s ease, background .18s ease, transform .18s ease; }
.dimension-row:hover { border-color: #f2ad91; transform: translateY(-1px); }
.dimension-row.active { border-color: #e85d2a; background: #fff3ec; box-shadow: inset 0 0 0 1px rgba(232, 93, 42, .2); }
.dimension-name { grid-area: name; font-size: 12px; font-weight: 900; }
.dimension-row b { grid-area: score; color: #182033; font-size: 12px; font-weight: 900; font-variant-numeric: tabular-nums; }
.dimension-row small { grid-area: gap; justify-self: end; color: #7d8795; font-size: 10px; }
.dimension-row mark { grid-area: badge; justify-self: start; padding: 2px 6px; border-radius: 5px; background: #f5f7fb; color: #667085; font-size: 10px; font-weight: 800; }
.dimension-row.active mark { background: #ffe2d5; color: #be3d2b; }
.dimension-row i { grid-area: bar; height: 5px; overflow: hidden; border-radius: 999px; background: #e9edf4; }
.dimension-row em { display: block; height: 100%; border-radius: inherit; background: #22a66b; }
.dimension-row.warning em { background: #f0a12b; }
.dimension-row.danger em { background: #e84c3d; }
.score-table-panel { overflow: hidden; padding: 0; border-color: #dfd2c7; background: #fff; }
.table-hero { display: flex; justify-content: space-between; gap: 16px; padding: 11px 14px 7px; border-bottom: 1px solid #f0e5dc; background: linear-gradient(180deg, #fffdfb 0%, #fff8f3 100%); }
.table-title h2 { margin: 4px 0 2px; color: #182033; font-size: 20px; line-height: 1.1; letter-spacing: 0; }
.table-title p { margin: 0; color: #667085; font-size: 12px; line-height: 1.25; }
.table-score { display: grid; justify-items: end; align-content: start; gap: 3px; min-width: 132px; }
.table-score strong { color: #e85d2a; font-size: 28px; line-height: .95; font-weight: 950; font-variant-numeric: tabular-nums; }
.table-score span { color: #9a4a2e; font-size: 11px; font-weight: 850; }
.dimension-progress { height: 5px; margin: 0 14px 7px; overflow: hidden; border-radius: 999px; background: #eceff5; }
.dimension-progress em { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #e85d2a, #f2a12b); }
.table-meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0 14px 7px; overflow: hidden; border: 1px solid #eee4dc; border-radius: 6px; }
.table-meta div { padding: 5px 9px; border-right: 1px solid #eee4dc; background: #fff; }
.table-meta div:last-child { border-right: 0; }
.table-meta span { display: block; color: #717b8c; font-size: 10px; }
.table-meta b { display: block; margin-top: 1px; color: #182033; font-size: 12px; line-height: 1.15; }
.rule-observation-panel { margin: 0 14px 8px; overflow: hidden; border: 1px solid #e5dcd3; border-radius: 7px; background: #fffdfa; }
.rule-panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 10px; border-bottom: 1px solid #efe7df; background: #fbf4ee; }
.rule-panel-head span { display: inline-flex; padding: 2px 7px; border-radius: 999px; background: #fff0e8; color: #c6532d; font-size: 10px; font-weight: 900; }
.rule-panel-head strong { display: block; margin-top: 3px; color: #182033; font-size: 13px; }
.rule-panel-head p { margin: 0; color: #5f6878; font-size: 11px; line-height: 1.35; text-align: right; }
.observation-table { display: grid; }
.observation-row { display: grid; grid-template-columns: minmax(180px, 1fr) 120px 86px 92px 70px; gap: 8px; align-items: center; min-width: 720px; padding: 7px 10px; border-top: 1px solid #f0e7df; background: #fff; }
.observation-row:first-child { border-top: 0; }
.observation-row b { display: block; color: #182033; font-size: 12px; font-weight: 900; }
.observation-row small { display: -webkit-box; overflow: hidden; margin-top: 2px; color: #667085; font-size: 10.5px; line-height: 1.35; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.observation-row span, .observation-row strong, .observation-row em { color: #253247; font-size: 11px; font-style: normal; font-weight: 850; }
.observation-row strong { color: #e85d2a; font-variant-numeric: tabular-nums; }
.observation-row em { justify-self: start; padding: 2px 6px; border-radius: 5px; background: #f5f7fb; color: #667085; }
.observation-row em.capped { background: #fff0d8; color: #9b5a11; }
.observation-row button { min-height: 25px; padding: 0 8px; border: 1px solid #f2b39c; border-radius: 5px; background: #fff7f2; color: #d9532a; font-size: 10.5px; font-weight: 900; cursor: pointer; white-space: nowrap; }
.rule-empty { margin: 0; padding: 10px; color: #7b8495; font-size: 12px; }
.rubric-table { margin: 0 8px 8px; overflow: auto; border: 1px solid #e5dcd3; border-radius: 7px; }
.rubric-head, .rubric-row { display: grid; grid-template-columns: 94px 36px 42px 100px minmax(265px, 1.85fr) minmax(240px, 1.5fr) minmax(184px, 1.05fr) 56px; gap: 7px; align-items: start; min-width: 1030px; padding: 6px 8px; }
.rubric-head { position: sticky; top: 0; z-index: 1; color: #6b574b; background: #fbf4ee; font-size: 11px; font-weight: 900; line-height: 1.2; }
.rubric-row { border-top: 1px solid #efe7df; background: #fffdfa; }
.rubric-row:nth-child(even) { background: #fff; }
.rubric-row:hover { background: #fff8f3; }
.item-name { display: grid; gap: 2px; }
.item-name b { color: #182033; font-size: 12px; font-weight: 900; line-height: 1.25; }
.item-name small { color: #8992a3; font-size: 10px; line-height: 1.1; }
.cell-max, .cell-score { color: #182033; font-size: 12px; font-weight: 900; line-height: 1.25; font-variant-numeric: tabular-nums; }
.cell-score.danger { color: #d43d30; }
.cell-score.warning { color: #d97b16; }
.deduction-tag { display: inline-flex; align-items: center; justify-content: center; min-height: 20px; padding: 2px 6px; border-radius: 5px; background: #f3f5f8; color: #566174; font-size: 10px; font-weight: 750; line-height: 1.2; }
.deduction-tag.danger { background: #ffe7df; color: #be3d2b; }
.deduction-tag.warning { background: #fff0d8; color: #9b5a11; }
.rubric-row p { display: -webkit-box; overflow: hidden; margin: 0; color: #4d596b; font-size: 10.5px; line-height: 1.38; -webkit-box-orient: vertical; }
.reason-copy { -webkit-line-clamp: 4; }
.fix-copy, .acceptance-copy { -webkit-line-clamp: 3; }
.rubric-row .fix-copy { color: #253247; font-weight: 700; }
.rubric-row button { min-height: 26px; padding: 0 8px; border: 1px solid #f2b39c; border-radius: 5px; background: #fff7f2; color: #d9532a; font-size: 11px; font-weight: 900; cursor: pointer; white-space: nowrap; }
.rubric-row button:hover { border-color: #e85d2a; background: #fff0e8; }
.table-action-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-top: 1px solid #efe5dd; background: #fff8f3; }
.table-action-bar p { margin: 0; color: #253247; font-size: 12px; font-weight: 850; }
.table-action-bar p span { margin-right: 8px; color: #9a4a2e; font-size: 11px; }
.table-action-bar div { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
.primary-action, .secondary-action { display: inline-flex; align-items: center; min-height: 30px; padding: 0 11px; border-radius: 5px; text-decoration: none; font-size: 11px; font-weight: 900; }
.primary-action { border: 1px solid #e85d2a; background: #e85d2a; color: #fff; box-shadow: 0 6px 14px rgba(232, 93, 42, .18); }
.secondary-action { border: 1px solid #dfcfc2; background: #fff; color: #be3d2b; }
@media (max-width: 1180px) {
  .score-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dimension-workbench { grid-template-columns: 1fr; }
  .dimension-index { position: static; }
}
@media (max-width: 760px) {
  .score-summary, .table-meta { grid-template-columns: 1fr; }
  .summary-item, .table-meta div { border-right: 0; border-bottom: 1px solid #efe7df; }
  .table-hero, .table-action-bar { display: grid; }
  .table-score { justify-items: start; }
}
</style>
