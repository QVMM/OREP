<template>
  <AiScoreReportShell title="改进方案" subtitle="把扣分项变成团队可执行、可验收的提分动作">
    <div class="page-stack action-page">
      <section class="action-summary" aria-label="改进方案关键指标">
        <article v-for="metric in metrics" :key="metric.label" :class="['summary-item', metric.tone]">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="improve-loop panel-block" aria-label="提分闭环">
        <div class="panel-head inline">
          <div>
            <span>提分闭环</span>
            <strong>从扣分到复核的完整路径</strong>
          </div>
          <em>先定位扣分，再派发任务，最后复核提分</em>
        </div>
        <div class="loop-track">
          <article v-for="(step, index) in improvementLoop" :key="step.label">
            <span>{{ index + 1 }}</span>
            <div>
              <b>{{ step.label }}</b>
              <strong>{{ step.value }}</strong>
              <small>{{ step.hint }}</small>
            </div>
          </article>
        </div>
      </section>

      <section class="action-workbench">
        <aside class="queue-panel panel-block">
          <div class="panel-head">
            <span>扣分清单</span>
            <strong>{{ activeFilter === 'p0' ? '先处理这些扣分' : '全报告扣分项' }}</strong>
            <em>{{ filteredActionItems.length }}/{{ actionItems.length }} 项</em>
          </div>

          <div class="filter-chips" aria-label="整改任务筛选">
            <button
              v-for="filter in filters"
              :key="filter.key"
              type="button"
              :class="{ active: activeFilter === filter.key }"
              @click="activeFilter = filter.key"
            >
              {{ filter.label }} <b>{{ filter.count }}</b>
            </button>
          </div>

          <div class="deduction-table-head">
            <span>排名</span>
            <span>扣分项</span>
            <span>来源</span>
            <span>可提分</span>
          </div>

          <div v-if="filteredActionItems.length" class="queue-list">
            <button
              v-for="(item, index) in filteredActionItems"
              :key="item.id"
              type="button"
              :class="['queue-row', item.tone, { active: item.id === selectedActionId }]"
              @click="selectAction(item)"
            >
              <span>{{ index + 1 }}</span>
              <div>
                <b>{{ item.title }}</b>
                <small>{{ item.shortAction }}</small>
              </div>
              <mark>{{ item.sourceLabel }}</mark>
              <i>{{ item.recoverableShort }}</i>
            </button>
          </div>
          <AiScoreEmptyState v-else title="暂无匹配整改项" description="可切换筛选条件，或先生成提分方案。" />
          <label class="queue-search">
            <span>搜索整改项</span>
            <input v-model.trim="searchKeyword" type="search" placeholder="搜索扣分项、维度或整改动作" />
          </label>
        </aside>

        <main class="prescription-panel panel-block">
          <header class="prescription-head">
            <div>
              <span>整改详情</span>
              <h2>{{ selectedAction?.title || '选择一个扣分项' }}</h2>
              <p>{{ selectedAction?.dimension || '待识别维度' }} · {{ selectedAction?.sourceLabel || '报告汇总' }} · {{ selectedAction?.recoverable || '追回分待测算' }}</p>
            </div>
            <strong>{{ selectedAction?.statusLabel || '待整改' }}</strong>
          </header>

          <section class="detail-meta">
            <span>扣分原因 <b>{{ selectedAction?.deductionLabel || '问题未定位' }}</b></span>
            <span>负责人 <b>{{ selectedAction?.owner || '待分配' }}</b></span>
            <span>问题来源 <b>{{ selectedAction?.sourceLabel || '报告汇总' }}</b></span>
          </section>

          <section class="logic-grid" aria-label="整改逻辑">
            <article>
              <span class="logic-icon">扣</span>
              <h3>为什么扣分</h3>
              <p>{{ selectedAction?.reason || '当前报告未返回该扣分项的原因说明。' }}</p>
            </article>
            <article>
              <span class="logic-icon">改</span>
              <h3>怎么改</h3>
              <p>{{ selectedAction?.action || '把问题拆成团队任务，并在下一轮彩排中拿证据验证。' }}</p>
            </article>
            <article>
              <span class="logic-icon">交</span>
              <h3>交付物</h3>
              <ul>
                <li v-for="item in deliveryItems" :key="item">{{ item }}</li>
              </ul>
            </article>
            <article>
              <span class="logic-icon">验</span>
              <h3>验收标准</h3>
              <ul>
                <li v-for="standard in acceptanceStandards" :key="standard">{{ standard }}</li>
              </ul>
            </article>
          </section>

          <section class="step-plan">
            <div class="step-head">
              <span>本轮行动线</span>
              <b>{{ selectedAction?.cycle || '今天完成拆解，下一轮复核' }}</b>
            </div>
            <div class="step-track">
              <mark v-for="step in actionSteps" :key="step.name">
                <b>{{ step.name }}</b>
                <small>{{ step.owner }}</small>
              </mark>
            </div>
          </section>

          <section class="acceptance-box">
            <div>
              <span>当前结论</span>
              <p>这条整改要先补齐可展示材料，再用彩排视频或证据截图证明已经改完。</p>
            </div>
            <div class="prescription-actions">
              <button type="button" class="primary" @click="selectCurrentForTeamTask">加入团队任务</button>
              <button
                type="button"
                :disabled="report.actionPlanCoachingLoading.value || !report.effectiveMeetingId.value"
                @click="report.loadActionPlanCoaching(true)"
              >
                {{ report.actionPlanCoachingLoading.value ? '生成中' : '刷新提分方案' }}
              </button>
            </div>
          </section>
        </main>

        <aside class="dashboard-panel panel-block">
          <div class="panel-head compact">
            <span>任务派发</span>
            <strong>{{ dashboardVerdict }}</strong>
          </div>

          <section class="dispatch-box">
            <label>
              <span>选择团队</span>
              <select v-model="report.selectedTeamIdForTasks.value" aria-label="选择项目团队">
                <option value="">技术组（8人）</option>
                <option v-for="team in report.availableTeams.value" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
              </select>
            </label>
            <div class="dispatch-count">
              <span>已选任务</span>
              <strong>{{ report.selectedReportWorkItemIds.value.length || 3 }} 项</strong>
            </div>
            <div class="role-grid">
              <span v-for="role in roleSuggestions" :key="role.name">{{ role.name }} <b>{{ role.count }}</b></span>
            </div>
            <button
              type="button"
              class="plan-button"
              :disabled="report.creatingTeamTasks.value || !report.selectedReportWorkItemIds.value.length"
              @click="report.createTeamTasksFromReport"
            >
              {{ report.creatingTeamTasks.value ? '生成中' : '生成团队任务' }}
            </button>
          </section>

          <div class="target-bars">
            <article v-for="target in dashboardTargets" :key="target.label">
              <div>
                <span>{{ target.label }}</span>
                <b>{{ target.value }}</b>
              </div>
              <i><em :style="{ width: `${target.percent}%` }"></em></i>
              <small>{{ target.hint }}</small>
            </article>
          </div>

          <section class="team-box" v-if="report.createdTeamTaskCount.value > 0">
            <button v-if="report.createdTeamTaskCount.value > 0" type="button" class="ghost-button" @click="report.goTeamScoreWorkItems">
              查看已生成任务
            </button>
          </section>

          <section class="pass-line">
            <h3>本轮通过线</h3>
            <ul>
              <li>每个高优先扣分项都有负责人</li>
              <li>每项整改都有可截图或可演示证据</li>
              <li>复核时能对照原扣分点说明变化</li>
              <li>团队任务状态回传到工作台</li>
            </ul>
          </section>
        </aside>
      </section>

      <section class="review-plan panel-block">
        <div class="panel-head inline">
          <div>
            <span>复核看板</span>
            <strong>证据、任务、提分都要能回看</strong>
          </div>
          <em>{{ reviewDate ? report.formatDateTime(reviewDate) : '待安排' }}</em>
        </div>
        <div class="review-grid">
          <article v-for="item in acceptanceItems" :key="item.title">
            <span v-if="item.percent" class="review-ring" :style="{ '--ring': `${item.percent}%` }"><b>{{ item.percent }}%</b></span>
            <b>{{ item.title }}</b>
            <p>{{ item.detail }}</p>
          </article>
        </div>
      </section>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreEmptyState from '../../components/ai-score/report/AiScoreEmptyState.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()

const selectedActionId = ref('')
const activeFilter = ref('p0')
const searchKeyword = ref('')

const recoverableScore = computed(() => firstPresent(report.scoreRecoverySummary.value.recoverable_score, report.scoreRecoverySummary.value.recoverableScore, report.scoreRecoverySummary.value.recoverable_range, report.scoreRecoverySummary.value.recoverableRange))
const p0Tasks = computed(() => actionItems.value.filter(item => item.priority === 'HIGH').length)
const reviewDate = computed(() => firstPresent(report.scoreRecoverySummary.value.review_date, report.scoreRecoverySummary.value.reviewDate, report.scoreRecoverySummary.value.recheck_date, report.scoreRecoverySummary.value.recheckDate, report.result.value.review_date, report.result.value.reviewDate, report.result.value.next_review_at, report.result.value.nextReviewAt))
const evidenceConfidence = computed(() => {
  const value = Number(report.structuredEvidenceConfidence.value || 0)
  return value > 0 ? `${Math.round(value * 100)}%` : '待采样'
})

const metrics = computed(() => [
  { label: '今日重点', value: primaryFocus.value, hint: `覆盖 ${activeSourceCount.value} 类问题源`, tone: 'danger' },
  { label: '整改池', value: `${actionItems.value.length} 项`, hint: '评分表+表达+现场+建议', tone: 'primary' },
  { label: '高优先任务', value: `${p0Tasks.value} 项`, hint: '需要优先分配负责人', tone: p0Tasks.value ? 'danger' : 'success' },
  { label: '可追回分', value: recoverableScore.value == null ? '待生成' : formatRecoverableScore(recoverableScore.value), hint: recoverableScore.value == null ? '报告未测算' : '报告测算值', tone: 'success' },
  { label: '复核日期', value: reviewDate.value ? report.formatDateTime(reviewDate.value) : '待安排', hint: reviewDate.value ? '下一轮复核' : '报告未返回' },
  { label: '已勾选', value: `${report.selectedReportWorkItemIds.value.length}/${teamRows.value.length}`, hint: '生成后进入团队工作台', tone: 'warning' }
])

const actionPlanTasks = computed(() => {
  const plan = report.actionPlanCoaching.value || {}
  return arrayFrom(firstPresent(plan.tasks, plan.task_list, plan.taskList, plan.action_items, plan.actionItems, plan.work_items, plan.workItems, plan.plan, plan.items))
})

const draftRows = computed(() => report.reportWorkItemDrafts.value.map((item, index) => {
  const source = report.currentStructuredDeductions.value[index] || {}
  const deducted = Number(firstPresent(source.deducted, source.deduction, source.score_impact, source.scoreImpact, 0))
  return normalizeActionItem({
    ...source,
    ...item,
    sourceId: item.id,
    title: item.title?.replace(/^处理扣分项：/, '') || source.title || source.dimension || '整改任务',
    reason: item.description || source.reason || source.detail,
    action: source.suggestion || source.improvement || item.description,
    priority: item.priority || (deducted >= 5 ? 'HIGH' : 'MEDIUM'),
    recoverable: firstPresent(item.expectedRecoverPoints, source.maxRecoverablePoints, source.max_recoverable_points, Math.abs(deducted) || ''),
    owner: firstPresent(item.ownerRole, source.ownerRole, source.owner_role),
    acceptance: firstPresent(item.acceptanceCriteria, source.acceptanceCriteria, source.acceptance_criteria),
    cycle: firstPresent(item.timeSuggestion, source.timeSuggestion, source.time_suggestion),
    evidence: Array.isArray(item.evidenceAnchorIds) && item.evidenceAnchorIds.length ? `${item.evidenceAnchorIds.length}条验收证据` : '',
    selectedValue: item.id,
    sourceType: 'team'
  }, index)
}))

const deductionRows = computed(() => report.currentStructuredDeductions.value.map((item, index) => normalizeActionItem({
  ...item,
  title: firstPresent(item.title, item.name, item.dimension, item.item, '扣分项整改'),
  reason: firstPresent(item.reason, item.detail, item.comment, item.description),
  action: firstPresent(item.suggestion, item.improvement, item.action, item.fix, item.advice),
  priority: isHighImpactDeduction(item) ? 'HIGH' : 'MEDIUM',
  recoverable: firstPresent(item.maxRecoverablePoints, item.max_recoverable_points, item.deducted, item.deduction, ''),
  sourceType: 'rubric'
}, index)))

const coachingRows = computed(() => actionPlanTasks.value.map((item, index) => normalizeActionItem({
  ...item,
  title: firstPresent(item.title, item.name, item.issue, item.task, '提分任务'),
  reason: firstPresent(item.reason, item.detail, item.problem, item.description),
  action: firstPresent(item.action, item.suggestion, item.improvement, item.fix, item.solution),
  priority: firstPresent(item.priority, item.level, item.severity, index < 2 ? 'HIGH' : 'MEDIUM'),
  recoverable: firstPresent(item.recoverable, item.recoverable_score, item.recoverableScore, item.score, ''),
  sourceType: 'coach'
}, index)))

const dimensionItemRows = computed(() => {
  const rows = []
  report.dimensions.value.forEach(dimension => {
    ;(dimension.items || []).forEach((item, index) => {
      const score = Number(firstPresent(item.score, item.value, item.current_score, item.currentScore, 0))
      const max = Number(firstPresent(item.max_score, item.maxScore, item.full_score, item.fullScore, 0))
      const reason = firstPresent(item.reason, item.evaluation, item.comment, item.detail, item.issue, item.description, '')
      if (!reason && !(max && score < max)) return
      rows.push(normalizeActionItem({
        title: firstPresent(item.name, item.title, item.item, `${dimension.name}评分项`),
        dimension: dimension.name,
        reason: reason || `${dimension.name}下该评分项未达到满分要求。`,
        action: firstPresent(item.suggestion, item.improvement, item.action, item.fix, inferFixAction(item, reason)),
        acceptance: firstPresent(item.acceptanceCriteria, item.acceptance_criteria, item.acceptance, inferAcceptance(firstPresent(item.name, item.title, ''), reason)),
        priority: max && max - score >= 5 ? 'HIGH' : 'MEDIUM',
        recoverable: max ? max - score : '',
        evidence: item.evidence?.length ? `${item.evidence.length}条证据` : '',
        sourceType: 'rubricItem'
      }, `${dimension.key}-${index}`))
    })
  })
  return rows
})

const expressionRows = computed(() => {
  const transcriptRows = report.asrSegments.value
    .map((segment, index) => {
      const text = firstPresent(segment.text, segment.transcript, segment.content, '')
      if (!text || (text.length <= 72 && !/那么|呢|然后|就是|嗯|啊|这个|那个/.test(text))) return null
      const hasFiller = /那么|呢|然后|就是|嗯|啊|这个|那个/.test(text)
      const isLong = text.length > 72
      return normalizeActionItem({
        title: isLong ? '长句压缩训练' : '填充词替换训练',
        dimension: '表达节奏',
        reason: report.clipText(text, 120),
        action: isLong ? '拆成两句：先结论，再证据，并保留自然停顿。' : '替换“那么、呢、然后”等填充词，保留干净连接词。',
        acceptance: isLong ? '重点句能在 20 秒内讲完，且至少有 1 次自然停顿。' : '每分钟填充词不超过 1 次。',
        priority: index < 4 ? 'HIGH' : 'MEDIUM',
        sourceType: 'voice'
      }, `asr-${index}`)
    })
    .filter(Boolean)
    .slice(0, 8)
  const pauseRows = report.topPauses.value.map((pause, index) => {
    const duration = Number(pause.duration || 0)
    return normalizeActionItem({
      title: '停顿预演训练',
      dimension: '表达节奏',
      reason: `检测到 ${report.formatNumber(duration, 1)} 秒停顿，容易让评委感到转场断裂。`,
      action: '给操作空档准备过渡话术，彩排时单次停顿控制在 5 秒内。',
      acceptance: '单次停顿不超过 5 秒，操作间隙有自然承接话术。',
      priority: duration >= 8 ? 'HIGH' : 'MEDIUM',
      recoverable: duration >= 8 ? 2 : 1,
      sourceType: 'voice'
    }, `pause-${index}`)
  })
  return [...transcriptRows, ...pauseRows]
})

const presentationRows = computed(() => {
  const frameRows = sampleFramesAcrossTimeline(report.evidenceFrames.value, 10).map((frame, index) => {
    const text = `${frame.title || ''} ${frame.caption || ''}`
    const category = classifyPresentationIssue(text, index)
    return normalizeActionItem({
      title: category === '遮挡' ? '站位遮挡画面' : category === '互动' ? '互动覆盖不足' : '队形与视线不稳',
      dimension: '现场呈现',
      reason: category === '遮挡' ? '关键画面中讲者或队员容易遮挡屏幕重点区域。' : category === '互动' ? '讲解与评委互动、视线覆盖不足，现场说服力被削弱。' : '队伍站位和镜头重心不够稳定，影响评委观看重点。',
      action: category === '遮挡' ? '主讲人侧站讲解，关键页停留 3 秒，指向内容不挡核心数据。' : category === '互动' ? '讲完关键结论后回看评委，保留 1 秒自然停顿。' : '队员站成浅弧线，主讲人位于屏幕侧前方。',
      acceptance: category === '遮挡' ? '关键页截图中核心数据不被遮挡。' : category === '互动' ? '每段关键结论后至少 1 次眼神覆盖评委席。' : '彩排快照中队形稳定，非主讲人不分散视线。',
      priority: index < 4 ? 'HIGH' : 'MEDIUM',
      evidence: frame.timeLabel,
      sourceType: 'presentation'
    }, `frame-${index}`)
  })
  const contradictionRows = report.contradictions.value.map((item, index) => normalizeActionItem({
    title: item.title || '音画不同步',
    dimension: '现场呈现',
    reason: item.description || item.summary || item.reason || '口播内容和画面证据没有同步出现。',
    action: '切换页面前先口头预告，再指向关键区域，最后补一句结果说明。',
    acceptance: '评委能在同一时间看到画面证据并听到对应解释。',
    priority: index < 2 ? 'HIGH' : 'MEDIUM',
    sourceType: 'presentation'
  }, `fusion-${index}`))
  return [...frameRows, ...contradictionRows]
})

const priorityRows = computed(() => report.priorities.value.map((item, index) => normalizeActionItem({
  ...item,
  title: firstPresent(item.issue, item.title, item.dimension, item.name, '提分任务'),
  reason: firstPresent(item.reason, item.detail, item.description, item.issue),
  action: firstPresent(item.suggestion, item.improvement, item.action, '补齐评分报告指出的关键证据，并在下一轮彩排中验证。'),
  priority: index < 3 ? 'HIGH' : 'MEDIUM',
  sourceType: 'priority'
}, index)))

const teamRows = computed(() => draftRows.value.filter(item => item.selectedValue))

const actionItems = computed(() => {
  const rows = dedupeActionItems([
    ...coachingRows.value,
    ...draftRows.value,
    ...deductionRows.value,
    ...dimensionItemRows.value,
    ...expressionRows.value,
    ...presentationRows.value,
    ...priorityRows.value
  ])
  return rows.sort((a, b) => priorityRank(b) - priorityRank(a) || sourceRank(b) - sourceRank(a) || Number(b.recoverableNumber || 0) - Number(a.recoverableNumber || 0)).slice(0, 28)
})

const topActionItems = computed(() => actionItems.value.filter(item => item.priority === 'HIGH').slice(0, 3))

const filteredActionItems = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return actionItems.value.filter(item => {
    const matchesFilter =
      activeFilter.value === 'all' ||
      (activeFilter.value === 'p0' && item.priority === 'HIGH') ||
      (activeFilter.value === 'rubric' && ['rubric', 'rubricItem'].includes(item.sourceType)) ||
      (activeFilter.value === 'voice' && item.sourceType === 'voice') ||
      (activeFilter.value === 'presentation' && item.sourceType === 'presentation') ||
      (activeFilter.value === 'evidence' && item.needsEvidence) ||
      (activeFilter.value === 'team' && item.sourceType === 'team')
    const matchesKeyword = !keyword || [item.title, item.dimension, item.reason, item.action, item.acceptance].some(value => String(value || '').toLowerCase().includes(keyword))
    return matchesFilter && matchesKeyword
  })
})

const selectedAction = computed(() => actionItems.value.find(item => item.id === selectedActionId.value) || filteredActionItems.value[0] || actionItems.value[0] || null)

const filters = computed(() => [
  { key: 'all', label: '全部', count: actionItems.value.length },
  { key: 'p0', label: '优先', count: actionItems.value.filter(item => item.priority === 'HIGH').length },
  { key: 'rubric', label: '评分表', count: actionItems.value.filter(item => ['rubric', 'rubricItem'].includes(item.sourceType)).length },
  { key: 'voice', label: '表达', count: actionItems.value.filter(item => item.sourceType === 'voice').length },
  { key: 'presentation', label: '现场', count: actionItems.value.filter(item => item.sourceType === 'presentation').length },
  { key: 'evidence', label: '补证据', count: actionItems.value.filter(item => item.needsEvidence).length },
  { key: 'team', label: '可派发', count: actionItems.value.filter(item => item.sourceType === 'team').length }
])

const activeSourceCount = computed(() => sourceMatrix.value.filter(item => item.count > 0).length)
const rubricCount = computed(() => actionItems.value.filter(item => ['rubric', 'rubricItem'].includes(item.sourceType)).length)
const voiceCount = computed(() => actionItems.value.filter(item => item.sourceType === 'voice').length)
const presentationCount = computed(() => actionItems.value.filter(item => item.sourceType === 'presentation').length)
const teamTaskCount = computed(() => report.selectedReportWorkItemIds.value.length || teamRows.value.length)

const improvementLoop = computed(() => [
  { label: '评分表扣分', value: `${rubricCount.value} 项`, hint: '先找准扣在哪一项' },
  { label: '表达问题', value: `${voiceCount.value} 项`, hint: '把问题句变成训练话术' },
  { label: '现场问题', value: `${presentationCount.value} 项`, hint: '用快照复查站位与画面' },
  { label: '生成整改任务', value: `${teamTaskCount.value} 项`, hint: '派发到团队工作台' },
  { label: '下一轮复核', value: reviewDate.value ? '已安排' : '待安排', hint: reviewDate.value ? report.formatDateTime(reviewDate.value) : '完成后重新评分' }
])

const sourceMatrix = computed(() => {
  const total = Math.max(actionItems.value.length, 1)
  return [
    { label: '评分表', count: rubricCount.value },
    { label: '表达', count: voiceCount.value },
    { label: '现场', count: presentationCount.value },
    { label: '建议', count: actionItems.value.filter(item => ['coach', 'priority'].includes(item.sourceType)).length }
  ].map(item => ({ ...item, percent: percent(item.count, total) }))
})

const primaryFocus = computed(() => {
  const item = actionItems.value[0]
  if (!item) return '待生成'
  return report.clipText(item.title, 10)
})

const dashboardVerdict = computed(() => {
  if (!actionItems.value.length) return '先生成整改项'
  if (report.selectedReportWorkItemIds.value.length) return '可以派发任务'
  if (p0Tasks.value) return '先处理高优先'
  return '按计划推进'
})

const dashboardTargets = computed(() => [
  { label: '任务选择', value: `${report.selectedReportWorkItemIds.value.length || 3}项`, hint: `共 ${actionItems.value.length} 项可处理`, percent: percent(report.selectedReportWorkItemIds.value.length || 3, Math.max(actionItems.value.length, 1)) },
  { label: '高优先处理', value: `${p0Tasks.value}项`, hint: '目标全部分配负责人', percent: inversePercent(p0Tasks.value, Math.max(actionItems.value.length, 1)) },
  { label: '证据补齐', value: evidenceConfidence.value, hint: '目标证据覆盖扣分点', percent: evidenceConfidence.value === '待采样' ? 72 : Number(evidenceConfidence.value.replace('%', '')) },
  { label: '复核准备', value: reviewDate.value ? '已安排' : '待安排', hint: '完成整改后重新评分', percent: reviewDate.value ? 78 : 28 }
])

const roleSuggestions = computed(() => [
  { name: '产品负责人', count: '1人' },
  { name: '算法工程师', count: /技术|先进|模型|AI/.test(`${selectedAction.value?.title || ''}${selectedAction.value?.reason || ''}`) ? '2人' : '1人' },
  { name: '前端工程师', count: '1人' },
  { name: '数据分析师', count: /数据|量化|技术|先进/.test(`${selectedAction.value?.title || ''}${selectedAction.value?.reason || ''}`) ? '1人' : '待定' }
])

const actionSteps = computed(() => {
  const item = selectedAction.value
  if (!item) return buildActionSteps(['定位扣分', '分配负责人', '补齐证据', '下一轮复核'])
  if (/时长|直播|展示|完整/.test(item.title + item.reason)) return buildActionSteps(['补齐缺失环节', '录制完整彩排', '标注关键证据', '重新评分复核'])
  if (/数据|量化|成本|反馈/.test(item.title + item.reason)) return buildActionSteps(['补数据来源', '做对比图表', '放入路演页', '评委视角复核'])
  if (/规范|合规|安全|标准|知识产权/.test(item.title + item.reason)) return buildActionSteps(['列出标准依据', '补合规材料', '截图存证', '逐项验收'])
  return buildActionSteps(['定位扣分', '拆成任务', '补齐证据', '下一轮复核'])
})

const deliveryItems = computed(() => {
  const item = selectedAction.value
  if (!item) return ['1 条整改说明', '1 张证据截图', '1 次复核记录']
  const text = `${item.title} ${item.reason} ${item.action}`
  if (/先进|技术|模型|实时|AI|AR|RAG|WebRTC/.test(text)) return ['1 页技术选型对比表', '1 段可播放演示视频', '2 张运行效果截图']
  if (/数据|量化|成本|反馈|经济|实用/.test(text)) return ['1 张数据来源截图', '1 页对比图表', '1 段结论话术']
  if (/规范|标准|合规|安全|知识产权/.test(text)) return ['1 份标准或合规清单', '1 张检查表截图', '1 段路演引用话术']
  if (/表达|语速|停顿|口头禅|长句/.test(text)) return ['1 版精简话术', '1 段录音回放', '1 份填充词统计']
  if (/站位|遮挡|镜头|互动|现场/.test(text)) return ['1 张彩排快照', '1 份站位示意', '1 段复核视频片段']
  return ['1 条整改说明', '1 张证据截图', '1 次复核记录']
})

const acceptanceStandards = computed(() => {
  const item = selectedAction.value
  if (!item) return ['能说明扣分项已被处理', '有对应截图、数据或演示证据', '下一轮评分同项不再重复扣分']
  return [
    item.acceptance || '有对应截图、数据或演示证据，能支撑整改已完成。',
    item.evidenceLabel === '待补齐' ? '至少补充 1 条证据锚点或一张验收截图。' : `复核时展示${item.evidenceLabel}。`,
    '下一轮评分时，对照原扣分原因说明改动前后差异。'
  ]
})

const acceptanceItems = computed(() => [
  { title: '证据补齐', percent: evidenceConfidence.value === '待采样' ? 72 : Number(evidenceConfidence.value.replace('%', '')), detail: evidenceConfidence.value === '待采样' ? '当前证据置信度未形成样本，优先给每个高优先整改项补证据锚点。' : `当前证据置信度 ${evidenceConfidence.value}，复核时检查新增证据是否覆盖扣分点。` },
  { title: '任务闭环', percent: percent(report.selectedReportWorkItemIds.value.length || 12, Math.max(actionItems.value.length, 1)), detail: actionItems.value.length ? `本轮已整理 ${actionItems.value.length} 个整改项，勾选后可生成团队任务并分配负责人。` : '暂无可自动生成任务，需先生成提分方案或回到评分表核对扣分项。' },
  { title: '提分对比', detail: recoverableScore.value == null ? '完成整改后重新评分，对比本轮扣分项是否收敛。' : `当前可追回 ${formatRecoverableScore(recoverableScore.value)}，复核时对照总分变化。` }
])

watch([filteredActionItems, actionItems], () => {
  const source = filteredActionItems.value.length ? filteredActionItems.value : actionItems.value
  if (!source.some(item => item.id === selectedActionId.value)) selectedActionId.value = source[0]?.id || ''
}, { immediate: true })

function selectAction(item) {
  selectedActionId.value = item.id
}

function selectPriorityAction(item) {
  activeFilter.value = 'p0'
  selectAction(item)
}

function buildActionSteps(names) {
  const owners = ['今天拆解', '负责人补齐', '彩排验证', '复核评分']
  return names.map((name, index) => ({ name, owner: owners[index] || '待安排' }))
}

function selectCurrentForTeamTask() {
  const item = selectedAction.value
  if (!item?.selectedValue) {
    ElMessage.info('该整改项来自建议列表，暂无可直接派发的工作项。')
    return
  }
  const selected = report.selectedReportWorkItemIds.value
  if (!selected.includes(item.selectedValue)) selected.push(item.selectedValue)
  ElMessage.success('已加入团队任务勾选')
}

function normalizeActionItem(item, index) {
  const title = firstPresent(item.title, item.issue, item.name, item.dimension, '整改任务')
  const priority = normalizePriority(firstPresent(item.priority, item.severity, item.level))
  const recoverableNumber = Number(firstPresent(item.recoverable, item.maxRecoverablePoints, item.max_recoverable_points, item.deducted, item.deduction, 0))
  const reason = firstPresent(item.reason, item.detail, item.description, item.problem, '当前报告未返回详细原因，请结合评分表和证据链核对。')
  const action = firstPresent(item.action, item.suggestion, item.improvement, item.fix, item.solution, '补齐证据并在下一轮彩排中复测。')
  const acceptance = firstPresent(item.acceptance, item.acceptanceCriteria, item.acceptance_criteria, item.validation, item.verify, inferAcceptance(title, reason))
  const dimension = firstPresent(item.dimension, item.dimensionName, item.dimension_name, item.category, '综合提分')
  const evidenceLabel = firstPresent(item.evidence, item.evidenceLabel, item.acceptanceEvidence, item.acceptance_evidence, '')
  const sourceType = item.sourceType || 'priority'
  const sourceLabel = sourceTypeLabel(sourceType)
  const shortAction = report.clipText(action, 34)
  return {
    id: `${sourceType}-${index}-${slug(title)}`,
    selectedValue: item.selectedValue || '',
    sourceType,
    sourceLabel,
    title,
    dimension,
    reason,
    action,
    acceptance,
    priority,
    priorityLabel: priority === 'HIGH' ? '高优先' : priority === 'LOW' ? '低优先' : '中优先',
    statusLabel: item.statusLabel || '待整改',
    owner: firstPresent(item.owner, item.assignee, item.ownerName, '待分配'),
    cycle: firstPresent(item.cycle, item.due, item.deadline, '今天拆解，下一轮复核'),
    recoverable: recoverableNumber ? `可追回 ${report.formatNumber(Math.abs(recoverableNumber), 1)} 分` : '追回分待测算',
    recoverableShort: recoverableNumber ? `${report.formatNumber(Math.abs(recoverableNumber), 1)}分` : '待测',
    recoverableNumber: Math.abs(recoverableNumber || 0),
    deductionLabel: inferDeductionLabel(title, reason),
    evidenceLabel: evidenceLabel || '待补齐',
    needsEvidence: !evidenceLabel || /证据|截图|数据|标准|材料|锚点/.test(action + acceptance + reason),
    shortAction,
    tone: priority === 'HIGH' ? 'danger' : recoverableNumber >= 3 ? 'warning' : 'normal'
  }
}

function normalizePriority(value) {
  const text = String(value || '').toUpperCase()
  if (/HIGH|CRITICAL|P0|高|严重|关键/.test(text)) return 'HIGH'
  if (/LOW|P2|低/.test(text)) return 'LOW'
  return 'MEDIUM'
}

function priorityRank(item) {
  return { HIGH: 3, MEDIUM: 2, LOW: 1 }[item.priority] || 0
}

function sourceRank(item) {
  return { rubricItem: 6, rubric: 5, voice: 4, presentation: 3, team: 2, coach: 1, priority: 0 }[item.sourceType] || 0
}

function sourceTypeLabel(type) {
  return {
    rubric: '评分表',
    rubricItem: '评分表',
    voice: '表达',
    presentation: '现场',
    team: '可派发',
    coach: '模型',
    priority: '建议'
  }[type] || '报告'
}

function dedupeActionItems(items) {
  const seen = new Set()
  return items.filter(item => {
    const key = `${item.sourceType}-${item.title}-${item.dimension}`.replace(/\s+/g, '')
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function isHighImpactDeduction(item) {
  const deducted = Number(firstPresent(item.deducted, item.deduction, item.score_impact, item.scoreImpact, 0))
  const markers = [item.priority, item.severity, item.level, item.impact, item.risk_level, item.riskLevel, item.category].map(value => String(value || '').toLowerCase())
  return Math.abs(deducted) >= 5 || markers.some(value => /p0|high|critical|severe|高影响|高危|严重|关键/.test(value))
}

function inferDeductionLabel(title, reason) {
  const text = `${title} ${reason}`
  if (/时长|缺失|完整/.test(text)) return '展示不完整'
  if (/规范|标准|合规|安全|知识产权/.test(text)) return '规范依据不足'
  if (/数据|量化|成本|反馈/.test(text)) return '数据支撑不足'
  if (/语速|停顿|口头禅|表达/.test(text)) return '表达影响理解'
  if (/站位|遮挡|镜头|互动/.test(text)) return '现场呈现扣分'
  return '关键扣分点'
}

function inferAcceptance(title, reason) {
  const text = `${title} ${reason}`
  if (/时长|直播|展示/.test(text)) return '补齐缺失演示环节，并用完整彩排视频复核。'
  if (/数据|量化|成本/.test(text)) return '提供数据来源、对比图表和结论页截图。'
  if (/规范|合规|安全|知识产权/.test(text)) return '展示标准文档、合规说明或检查表。'
  return '提交可被评委直接查看的整改证据。'
}

function inferFixAction(item, reason) {
  const text = `${item.name || item.title || ''} ${reason || ''}`
  if (/标准|规范|合规|流程|引用|安全|知识产权/.test(text)) return '补充标准名称、检查表、合规依据或安全测试材料，并在路演中明确引用。'
  if (/停顿|填充词|犹豫|重复|卡顿|熟练/.test(text)) return '围绕关键操作录制三轮演练，压缩重复表达，保留一次流畅版本。'
  if (/难度|技术栈|复杂|集成|高并发|部署|模型/.test(text)) return '拆出2个技术难点，说明方案、取舍和实际运行效果。'
  if (/先进|前沿|选型|对比|AI|RAG|实时/.test(text)) return '增加技术选型对比或前沿能力展示，让评委看到先进性证据。'
  if (/语速|讲解|表达|节奏|互动/.test(text)) return '重点段放慢语速，减少填充词，并加入评委可感知的停顿。'
  return '把扣分原因转成一条可执行任务，并在下一轮彩排中复测。'
}

function classifyPresentationIssue(text, index) {
  const value = String(text || '')
  if (/遮挡|看不清|屏幕|PPT|画面|字幕|投屏/.test(value) || index % 4 === 0) return '遮挡'
  if (/互动|评委|眼神|提问|回应|观众/.test(value) || index % 4 === 2) return '互动'
  return '站位'
}

function sampleFramesAcrossTimeline(frames, targetCount) {
  if (!Array.isArray(frames) || frames.length <= targetCount) return frames || []
  const sorted = [...frames].sort((a, b) => frameSeconds(a) - frameSeconds(b))
  const picked = new Map()
  const lastIndex = sorted.length - 1
  for (let i = 0; i < targetCount; i += 1) {
    const index = Math.round((lastIndex * i) / Math.max(targetCount - 1, 1))
    const frame = sorted[index]
    picked.set(firstPresent(frame?.backendId, frame?.id, index), frame)
  }
  return [...picked.values()].sort((a, b) => frameSeconds(a) - frameSeconds(b))
}

function frameSeconds(frame) {
  const raw = firstPresent(frame?.timestamp, frame?.time, frame?.position_seconds, frame?.positionSeconds, frame?.timestamp_ms != null ? Number(frame.timestamp_ms) / 1000 : undefined, frame?.timestampMs != null ? Number(frame.timestampMs) / 1000 : undefined, 0)
  return Number(raw) || 0
}

function formatRecoverableScore(value) {
  if (typeof value === 'number') return `${report.formatNumber(value, 1)} 分`
  return String(value)
}

function percent(value, total) {
  if (!total) return 0
  return Math.max(8, Math.min(100, Math.round((Number(value || 0) / total) * 100)))
}

function inversePercent(value, total) {
  if (!total) return 100
  return Math.max(10, Math.min(100, 100 - Math.round((Number(value || 0) / total) * 100)))
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value && typeof value === 'object') return Object.values(value)
  return []
}

function slug(value) {
  return String(value || '').replace(/\s+/g, '-').slice(0, 24)
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}
</script>

<style>
.page-stack { display: grid; gap: 14px; min-width: 0; }
.action-page { --action-ink: #182033; --action-muted: #667085; --action-line: #e9ded5; --action-accent: #e85d2a; --action-hot: #be3d2b; --action-green: #16845f; --action-soft: #fff3ec; }
.action-page .panel-block { min-width: 0; border: 1px solid var(--action-line); border-radius: 8px; background: linear-gradient(180deg, #fff 0%, #fffaf6 100%); box-shadow: 0 14px 34px rgba(47, 37, 29, .055); }
.action-summary { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); overflow: hidden; border: 1px solid #e3d7cc; border-radius: 8px; background: #fffdfb; box-shadow: 0 10px 24px rgba(47, 37, 29, .045); }
.summary-item { display: grid; gap: 2px; min-height: 72px; padding: 13px 16px; border-right: 1px solid #efe6de; }
.summary-item:last-child { border-right: 0; }
.summary-item span { color: #7b8495; font-size: 11px; font-weight: 750; }
.summary-item strong { color: #182033; font-size: 20px; line-height: 1.05; letter-spacing: 0; }
.summary-item small { color: #667085; font-size: 11px; line-height: 1.25; }
.summary-item.danger strong { color: #e85d2a; }
.summary-item.primary strong { color: #d84b2a; }
.summary-item.success strong { color: #16845f; }
.summary-item.warning strong { color: #b66b13; }
.improve-loop { padding: 12px 16px 10px; border-color: #f0cdbd; background: #fffdfb; }
.improve-loop .panel-head { margin-bottom: 6px; }
.loop-track { position: relative; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0; align-items: start; padding: 4px 20px 0; }
.loop-track::before { content: ""; position: absolute; left: 76px; right: 76px; top: 18px; height: 4px; border-radius: 999px; background: #e85d2a; }
.loop-track article { position: relative; display: grid; justify-items: center; gap: 5px; min-height: 74px; padding: 0 8px; text-align: center; background: transparent; }
.loop-track article::after { content: ""; position: absolute; right: -12px; top: 16px; width: 34px; border-top: 1px dashed #9aa4b2; }
.loop-track article:last-child::after { display: none; }
.loop-track article > span { position: relative; z-index: 1; display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: #e85d2a; color: #fff; font-size: 11px; font-weight: 950; box-shadow: 0 0 0 5px #fffdfb; }
.loop-track b { display: block; color: #182033; font-size: 12px; line-height: 1.2; }
.loop-track strong { display: block; color: #e85d2a; font-size: 14px; line-height: 1; }
.loop-track small { display: block; color: #667085; font-size: 10px; line-height: 1.2; }
.action-workbench { display: grid; grid-template-columns: 360px minmax(0, 1fr) 300px; gap: 10px; align-items: start; min-width: 0; }
.queue-panel, .dashboard-panel { padding: 12px; }
.panel-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 10px; margin-bottom: 10px; }
.panel-head.inline { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.panel-head.compact { display: block; }
.panel-head span { display: inline-flex; width: fit-content; margin-bottom: 4px; padding: 3px 7px; border-radius: 999px; background: #fff0e8; color: #d84b2a; font-size: 10px; font-weight: 900; }
.panel-head strong { color: #182033; font-size: 16px; line-height: 1.2; }
.panel-head em { color: #7b8495; font-style: normal; font-size: 12px; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; padding-bottom: 9px; border-bottom: 1px solid #f0e5dc; }
.filter-chips button { height: 26px; padding: 0 9px; border: 1px solid #eaded4; border-radius: 999px; background: #fff; color: #667085; font-size: 11px; font-weight: 800; cursor: pointer; }
.filter-chips button.active { border-color: #e85d2a; background: #fff0e8; color: #d84b2a; }
.filter-chips b { margin-left: 3px; color: inherit; }
.queue-search { display: grid; gap: 6px; margin-top: 10px; }
.queue-search span { color: #667085; font-size: 11px; font-weight: 800; }
.queue-search input { width: 100%; height: 30px; padding: 0 10px; border: 1px solid #e4d9cf; border-radius: 6px; background: #fff; color: #182033; font-size: 11px; outline: none; }
.queue-search input:focus { border-color: #e85d2a; box-shadow: 0 0 0 3px rgba(232, 93, 42, .1); }
.deduction-table-head { display: grid; grid-template-columns: 38px minmax(0, 1fr) 58px 54px; gap: 8px; padding: 0 10px 7px; color: #7b8495; font-size: 10px; font-weight: 850; }
.queue-list { display: grid; gap: 0; max-height: 482px; overflow: auto; padding-right: 2px; border: 1px solid #f0e5dc; border-radius: 7px; background: #fff; }
.queue-row { position: relative; display: grid; grid-template-columns: 38px minmax(0, 1fr) 58px 54px; gap: 8px; align-items: center; width: 100%; min-height: 40px; padding: 7px 9px; border: 0; border-bottom: 1px solid #f1e7df; border-radius: 0; background: #fff; text-align: left; cursor: pointer; overflow: hidden; }
.queue-row:last-child { border-bottom: 0; }
.queue-row::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(232,93,42,.09), rgba(255,255,255,0) 58%); opacity: 0; transition: opacity .18s ease; pointer-events: none; }
.queue-row:hover::after, .queue-row.active::after { opacity: 1; }
.queue-row > * { position: relative; z-index: 1; }
.queue-row.danger { border-color: transparent; }
.queue-row.active { background: #fff3ec; box-shadow: inset 2px 0 0 #e85d2a; }
.queue-row > span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; background: #ffe4d7; color: #d84b2a; font-size: 11px; font-weight: 950; }
.queue-row b { color: #182033; font-size: 11px; font-weight: 900; }
.queue-row small { display: block; overflow: hidden; margin-top: 2px; color: #15835f; font-size: 10px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.queue-row mark { justify-self: start; padding: 2px 6px; border-radius: 999px; background: #fff0e8; color: #d84b2a; font-size: 10px; font-weight: 900; }
.queue-row i { color: #e85d2a; font-style: normal; font-size: 11px; font-weight: 950; text-align: right; white-space: nowrap; }
.prescription-panel { overflow: hidden; padding: 0; }
.prescription-head { display: flex; justify-content: space-between; gap: 14px; padding: 14px 16px 12px; border-bottom: 1px solid #f0e5dc; background: linear-gradient(180deg, #fffdfb 0%, #fff7f0 100%); }
.prescription-head span { color: #d84b2a; font-size: 11px; font-weight: 900; }
.prescription-head h2 { margin: 4px 0 2px; color: #182033; font-size: 20px; line-height: 1.15; }
.prescription-head p { margin: 0; color: #667085; font-size: 11px; line-height: 1.35; }
.prescription-head strong { align-self: start; padding: 4px 8px; border-radius: 999px; background: #ffe2d5; color: #be3d2b; font-size: 11px; white-space: nowrap; }
.detail-meta { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 10px 14px 8px; border: 1px solid #f0e5dc; border-radius: 7px; overflow: hidden; background: #fff; }
.detail-meta span { display: grid; gap: 4px; padding: 9px 12px; border-right: 1px solid #f0e5dc; color: #7b8495; font-size: 10px; font-weight: 850; }
.detail-meta span:last-child { border-right: 0; }
.detail-meta b { color: #182033; font-size: 12px; }
.logic-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; padding: 0 14px 10px; }
.logic-grid article { position: relative; min-height: 118px; padding: 13px 13px 12px 42px; border: 1px solid #efe4dc; border-radius: 7px; background: #fff; }
.logic-grid article:nth-child(2), .logic-grid article:nth-child(4) { background: linear-gradient(180deg, #fffaf6 0%, #fff 100%); }
.logic-grid h3 { margin: 0 0 8px; color: #182033; font-size: 13px; }
.logic-grid p { margin: 0; color: #4d596b; font-size: 12px; line-height: 1.65; }
.logic-icon { position: absolute; left: 13px; top: 13px; display: grid; place-items: center; width: 20px; height: 20px; border-radius: 5px; border: 1px solid #ffd0bc; background: #fff0e8; color: #e85d2a; font-size: 11px; font-weight: 950; }
.logic-grid ul { margin: 0; padding: 0; list-style: none; }
.logic-grid li { position: relative; margin: 6px 0; padding-left: 15px; color: #4d596b; font-size: 12px; line-height: 1.4; }
.logic-grid li::before { content: ""; position: absolute; left: 0; top: .62em; width: 6px; height: 6px; border-radius: 50%; background: #e85d2a; }
.step-plan { margin: 0 14px 10px; padding: 12px; border: 1px solid #efe4dc; border-radius: 7px; background: #fff; }
.step-head { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 10px; color: #182033; font-size: 12px; font-weight: 900; }
.step-head span { color: #9a4a2e; }
.step-track { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: hidden; border: 1px solid #eadfd6; border-radius: 8px; background: #f3f6fa; }
.step-track mark { position: relative; display: grid; gap: 3px; padding: 8px 8px; background: #ffe6da; color: #be3d2b; font-size: 11px; font-weight: 900; text-align: center; }
.step-track mark:nth-child(even) { background: #eef2f7; color: #566174; }
.step-track mark + mark::before { content: ""; position: absolute; left: 0; top: 20%; bottom: 20%; width: 1px; background: rgba(24,32,51,.08); }
.step-track b { font-size: 11px; line-height: 1.15; }
.step-track small { color: inherit; font-size: 9px; font-weight: 750; opacity: .78; }
.acceptance-box { display: flex; justify-content: space-between; gap: 12px; padding: 12px 14px 14px; border-top: 1px solid #f0e5dc; background: #fffdfb; }
.acceptance-box span { color: #9a4a2e; font-size: 12px; font-weight: 900; }
.acceptance-box p { max-width: 560px; margin: 7px 0 0; color: #4d596b; font-size: 12px; line-height: 1.6; }
.acceptance-box ul, .pass-line ul { margin: 8px 0 0; padding: 0; list-style: none; }
.acceptance-box li, .pass-line li { margin: 5px 0; color: #314055; font-size: 12px; line-height: 1.35; }
.acceptance-box li::before, .pass-line li::before { content: "✓"; margin-right: 7px; color: #16845f; font-weight: 900; }
.prescription-actions { display: flex; flex-wrap: wrap; gap: 7px; align-content: start; justify-content: flex-end; min-width: 210px; }
.prescription-actions button, .plan-button, .ghost-button { min-height: 30px; padding: 0 11px; border: 1px solid #dfcfc2; border-radius: 5px; background: #fff; color: #be3d2b; font-size: 11px; font-weight: 900; cursor: pointer; }
.prescription-actions .primary, .plan-button { border-color: #e85d2a; background: #e85d2a; color: #fff; box-shadow: 0 6px 14px rgba(232, 93, 42, .18); }
.prescription-actions button:disabled, .plan-button:disabled { border-color: #d9dfe8; background: #d9dfe8; color: #fff; cursor: not-allowed; box-shadow: none; }
.dispatch-box { display: grid; gap: 10px; margin-bottom: 10px; padding: 12px; border: 1px solid #f0d7c8; border-radius: 8px; background: #fff6f0; }
.dispatch-box label { display: grid; gap: 6px; }
.dispatch-box label span, .dispatch-count span { color: #667085; font-size: 11px; font-weight: 850; }
.dispatch-box select { width: 100%; height: 32px; padding: 0 10px; border: 1px solid #dfcfc2; border-radius: 6px; background: #fff; color: #182033; font-size: 12px; outline: none; }
.dispatch-count { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: #182033; }
.dispatch-count strong { color: #e85d2a; font-size: 16px; }
.role-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.role-grid span { display: flex; justify-content: space-between; gap: 4px; padding: 6px 8px; border: 1px solid #eadbd0; border-radius: 6px; background: #fff; color: #4d596b; font-size: 11px; font-weight: 850; }
.role-grid b { color: #182033; }
.target-bars { display: grid; gap: 8px; }
.command-score { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: center; margin-bottom: 12px; padding: 12px; border: 1px solid #f0d7c8; border-radius: 8px; background: #fff6f0; }
.command-score span, .command-score small { display: block; color: #7b8495; font-size: 10px; font-weight: 850; }
.command-score strong { display: block; margin: 3px 0; color: #e85d2a; font-size: 30px; line-height: .95; }
.command-score b { align-self: start; padding: 4px 7px; border-radius: 999px; background: #ffe2d5; color: #be3d2b; font-size: 10px; white-space: nowrap; }
.target-bars article { padding: 10px; border: 1px solid #efe4dc; border-radius: 7px; background: #fff; }
.target-bars div { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.target-bars span { color: #182033; font-size: 12px; font-weight: 900; }
.target-bars b { color: #182033; font-size: 13px; }
.target-bars i { display: block; height: 6px; overflow: hidden; border-radius: 999px; background: #edf1f7; }
.target-bars em { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #e85d2a, #f0a12b); }
.target-bars small { display: block; margin-top: 7px; color: #7b8495; font-size: 10px; }
.team-box, .pass-line { margin-top: 12px; padding: 11px; border: 1px solid #efe4dc; border-radius: 7px; background: #fffdfb; }
.team-box h3, .pass-line h3 { margin: 0 0 10px; color: #182033; font-size: 13px; }
.team-box select { width: 100%; height: 32px; margin-bottom: 8px; padding: 0 10px; border: 1px solid #dfcfc2; border-radius: 5px; background: #fff; color: #182033; font-size: 11px; outline: none; }
.team-box button { width: 100%; margin-top: 6px; }
.review-plan { padding: 13px 14px; }
.review-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.review-grid article { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px 12px; align-items: center; padding: 11px 12px; border: 1px solid #efe4dc; border-radius: 7px; background: #fffdfb; }
.review-grid b { color: #182033; font-size: 12px; }
.review-grid p { grid-column: 2; margin: 0; color: #566174; font-size: 12px; line-height: 1.6; }
.review-ring { grid-row: span 2; display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: conic-gradient(#28a866 var(--ring), #f0a12b 0 82%, #e8edf4 0); }
.review-ring::before { content: ""; position: absolute; width: 42px; height: 42px; border-radius: 50%; background: #fffdfb; }
.review-ring { position: relative; }
.review-ring b { position: relative; z-index: 1; color: #182033; font-size: 13px; }
@media (max-width: 1200px) {
  .action-summary { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .summary-item:nth-child(3n) { border-right: 0; }
  .loop-track { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .loop-track::before { display: none; }
  .action-workbench { grid-template-columns: 280px minmax(0, 1fr); }
  .dashboard-panel { grid-column: 1 / -1; }
}
@media (max-width: 900px) {
  .action-summary, .action-workbench, .detail-meta, .logic-grid, .review-grid, .loop-track { grid-template-columns: 1fr; }
  .summary-item { border-right: 0; border-bottom: 1px solid #efe6de; }
  .acceptance-box, .prescription-head, .panel-head.inline { display: grid; }
  .prescription-actions { justify-content: flex-start; min-width: 0; }
  .step-track { grid-template-columns: 1fr; border-radius: 7px; }
}
</style>
