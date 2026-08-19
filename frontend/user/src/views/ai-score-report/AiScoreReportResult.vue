<template>
  <AiScoreReportShell title="评分总结" mode="editorial">
    <div class="result-page coach-report-page is-scrollable">
      <div class="result-scroll coach-report-scroll">
        <div class="report-standard">
          <AiScoreReportCoachChrome
            active="result"
            title="本场结果"
            :description="resultLead"
            :score-display="officialScoreDisplay"
            :todo-count="chromeTodoCount || 0"
            @sync="onChromeSync"
          />

          <section class="conclusion-home" aria-label="本场结论" data-testid="conclusion-home">
            <article class="conclusion-block" data-testid="conclusion-official">
              <span>1 · 权威分</span>
              <strong>{{ home.officialScoreDisplay }}</strong>
              <p>
                量表 {{ home.contractVersion || '未标注版本' }}
                · {{ home.teacherHeadline }}
              </p>
              <p v-if="home.gap.tapeGrounded">
                {{ home.gap.identityReason }}
                <template v-if="home.gap.modelReviewScore != null">
                  · 模型复核分 {{ home.gap.modelReviewScore }}
                </template>
              </p>
            </article>

            <article
              class="conclusion-block"
              :class="'is-' + home.stability.band"
              data-testid="conclusion-stability"
            >
              <span>2 · 复评稳定性</span>
              <strong>{{ home.stability.headline }}</strong>
              <p v-if="home.stability.runCount > 0">
                已记录 {{ home.stability.runCount }} 次成功跑分
                <template v-if="home.stability.runs.length">
                  ·
                  <em v-for="run in home.stability.runs" :key="run.runIndex">
                    #{{ run.runIndex }} {{ run.officialScore == null ? '—' : run.officialScore }}
                    <template v-if="run.seekableAnchorRate != null">
                      · 锚点 {{ Math.round(run.seekableAnchorRate * 100) }}%
                    </template>
                  </em>
                </template>
              </p>
              <p v-if="home.stability.mixed && home.stability.identityHeadline">
                {{ home.stability.identityHeadline }}；整卷宗含旧抽取，不把本场说成已复评稳定。
              </p>
              <p v-if="home.stability.newerSessionId" data-testid="stability-newer-run">
                本卷宗有更新复评 #{{ home.stability.newerRunIndex }}。
                当前仍是本场 #{{ home.stability.thisRunIndex }}，权威分不换成新场。
                <RouterLink :to="newerReportPath">打开最新场</RouterLink>
              </p>
              <p v-else-if="!home.stability.runCount">尚未复评，不显示绿档。</p>
            </article>

            <article class="conclusion-block is-unlit" data-testid="conclusion-claims">
              <span>3 · 实质核验</span>
              <ul>
                <li v-for="claim in home.claims" :key="claim.claimType">
                  <b>{{ claim.label }}</b>
                  {{ claim.statement }}
                </li>
              </ul>
            </article>

            <article class="conclusion-block" data-testid="conclusion-gap">
              <span>4 · 满分差距</span>
              <div class="conclusion-split">
                <div>
                  <small>上轮闭环率</small>
                  <b>{{ home.gap.closureDisplay }}</b>
                </div>
                <div>
                  <small>本场权威分</small>
                  <b>{{ home.gap.officialScoreDisplay }}</b>
                </div>
              </div>
              <p>
                两个数分开看，不会合成完成度。
                <template v-if="home.gap.closurePendingNextRun">
                  本场刚发布的任务书不算上轮闭环。
                  <template v-if="home.gap.hungDisplay">{{ home.gap.hungDisplay }}，下场才算闭环。</template>
                </template>
              </p>
              <ul v-if="home.gap.ceilingGaps.length" class="conclusion-gaps">
                <li v-for="item in home.gap.ceilingGaps" :key="item.title">
                  <b>{{ item.title }}</b>
                  {{ item.whyNotFull }}
                </li>
              </ul>
            </article>

            <article
              class="conclusion-block"
              :class="{ 'is-unlit': !home.tasksAvailable }"
              data-testid="conclusion-tasks"
            >
              <span>5 · 任务书</span>
              <template v-if="home.tasksAvailable && home.tasks.length">
                <ul>
                  <li v-for="task in home.tasks" :key="task.title">
                    <b>{{ task.title }}</b>
                    <em v-if="task.expectedGain">{{ task.expectedGain }}</em>
                  </li>
                </ul>
              </template>
              <template v-else>
                <strong>本场任务书尚未发布</strong>
                <p>未发布条目不会进入学生待办中心。</p>
              </template>
            </article>

            <article
              class="conclusion-block"
              :class="{ 'is-unlit': !home.finalized }"
              data-testid="conclusion-teacher"
            >
              <span>6 · 教师确认</span>
              <strong>{{ home.teacherHeadline }}</strong>
              <p>{{ home.finalized ? '本场已确认，可作为终局。' : '未确认前，不把本场当成终局。' }}</p>
            </article>
          </section>

          <section class="challenge-panel" aria-label="本场质询" data-testid="challenge-panel">
            <div class="coach-section__label">质询条 · 下钻</div>
            <h2 class="coach-section__title">本场质询</h2>
            <p v-if="!challengeSet.scanned" class="coach-section__desc">{{ challengeSet.note || '本场未完成质询' }}</p>
            <p v-else-if="!challengeSet.items.length" class="coach-section__desc">{{ challengeSet.note || '本场未发现可核验争议' }}</p>
            <p v-else class="coach-section__desc">
              规则先扫出的争议，不改权威分。
              <template v-if="canResolveChallenge">教师可采纳或驳回。</template>
            </p>
            <ul v-if="challengeSet.items.length" class="challenge-list">
              <li v-for="item in challengeSet.items" :key="item.challengeId" class="challenge-item">
                <div>
                  <b>{{ item.targetDimension || '本场' }}</b>
                  {{ item.statement }}
                  <em>{{ statusLabel(item.status) }}</em>
                </div>
                <div class="challenge-item__actions">
                  <button
                    v-if="item.seekable && item.startMs != null"
                    type="button"
                    class="coach-action-ghost"
                    @click="jumpChallenge(item)"
                  >
                    跳到 {{ formatChallengeTime(item.startMs) }}
                  </button>
                  <template v-if="canResolveChallenge">
                    <button
                      v-if="item.status !== 'accepted'"
                      type="button"
                      class="coach-action-primary"
                      @click="resolveOne(item, 'accept')"
                    >采纳</button>
                    <button
                      v-if="item.status !== 'rejected'"
                      type="button"
                      class="coach-action-ghost"
                      @click="resolveOne(item, 'reject')"
                    >驳回</button>
                  </template>
                </div>
              </li>
            </ul>
            <p v-if="challengeSet.acceptedAdjustment" class="challenge-adjust">
              教师已采纳质询，草案调整 +{{ challengeSet.acceptedAdjustment }}
              <template v-if="challengeSet.adjustedDraftScore != null">
                ，调整后草案 {{ challengeSet.adjustedDraftScore }}
              </template>
              ；权威分未改。
            </p>
          </section>

          <!-- 总评长文仅保留在 PDF；Web 上直接看问题与改法，避免学生看不懂的摘要块 -->

          <section class="coach-section" aria-label="主要问题">
            <div class="coach-section__label">主要问题 · {{ topItems.length }} 项优先</div>
            <h2 class="coach-section__title">优先改这些</h2>
            <p class="coach-section__desc">展开看改法摘要；详细步骤在「待办」里按表执行。</p>

            <div v-if="topItems.length" class="coach-issue-list">
              <article
                v-for="(rx, idx) in topItems"
                :key="rx.id"
                class="coach-issue-card"
                data-testid="priority-task"
                :class="{ 'is-open': openRxId === rx.id }"
              >
                <button type="button" class="coach-issue-card__main" @click="toggleRx(rx.id)">
                  <div class="coach-issue-card__index">{{ idx + 1 }}</div>
                  <div class="coach-issue-card__body">
                    <div class="coach-issue-card__title-row">
                      <h3>{{ rx.title }}</h3>
                      <span class="coach-pill" :class="pillClass(rx, idx)">{{ rx.priorityLabel || (idx === 0 ? '先改' : '建议改') }}</span>
                    </div>
                    <p class="coach-issue-card__desc">{{ rx.desc || '本场在该点上证据或表达不足，需要优先补齐。' }}</p>
                    <div class="coach-issue-card__tags">
                      <span v-if="rx.dimension">{{ rx.dimension }}</span>
                      <span v-if="rx.howSteps?.length">{{ rx.howSteps.length }} 步改法</span>
                      <span v-else-if="rx.doneLines.length">{{ rx.doneLines.length }} 项验收</span>
                    </div>
                  </div>
                  <div class="coach-issue-card__toggle" aria-hidden="true">
                    {{ openRxId === rx.id ? '收起' : '展开' }}
                  </div>
                </button>

                <div v-if="openRxId === rx.id" class="coach-issue-card__detail">
                  <div v-if="rx.howSteps?.length" class="coach-mini-steps">
                    <div class="coach-mini-steps__title">怎么改</div>
                    <ol>
                      <li v-for="step in rx.howSteps.slice(0, 4)" :key="step.step">
                        <b>{{ step.step }}.</b> {{ step.action }}
                        <em v-if="step.deliverable">产出：{{ step.deliverable }}</em>
                      </li>
                    </ol>
                  </div>
                  <p v-else-if="rx.how" class="coach-detail-line"><b>怎么改</b>{{ rx.how }}</p>
                  <p v-if="rx.doneLines.length" class="coach-detail-line"><b>怎样算完成</b>{{ rx.doneLines.join('；') }}</p>
                  <div class="coach-issue-card__actions">
                    <button type="button" class="coach-action-primary" @click="goTodosTask(rx)">去待办改</button>
                    <button v-if="rx.evidenceAnchorIds.length" type="button" class="coach-action-ghost" @click="goWhy">看依据</button>
                    <button type="button" class="coach-action-ghost" @click="syncOne(rx)">派给队友</button>
                  </div>
                </div>
              </article>
            </div>

            <div v-else class="coach-empty">
              暂无结构化改进任务，可先到「依据」回看录像。
            </div>

            <RouterLink
              v-if="view.hasMorePrescriptions"
              class="coach-more-link"
              :to="report.sectionPath('todos')"
            >
              查看全部 {{ view.metrics.prescriptionCount }} 项待办 →
            </RouterLink>
          </section>

          <div v-if="view.dimensions.length" class="report-insight-grid coach-secondary">
            <section v-if="view.dimensions.length" class="report-insight-card report-dimensions-card">
              <header>
                <div>
                  <span>下钻</span>
                  <h2>能力维度</h2>
                  <p>哪一块偏弱，对照分数即可。</p>
                </div>
                <RouterLink :to="report.sectionPath('why')">看依据 ›</RouterLink>
              </header>

              <div class="dimension-panel">
                <div v-if="view.showRadar" class="radar-stage" aria-label="能力维度雷达图">
                  <svg class="radar-svg" viewBox="0 0 360 360" role="img">
                    <defs>
                      <linearGradient id="reportRadarFill" x1="15%" y1="10%" x2="85%" y2="90%">
                        <stop offset="0%" stop-color="rgba(255, 126, 66, 0.32)" />
                        <stop offset="100%" stop-color="rgba(232, 74, 28, 0.10)" />
                      </linearGradient>
                    </defs>
                    <polygon
                      v-for="ring in radarRings"
                      :key="'ring-' + ring.scale"
                      :points="ring.points"
                      fill="none"
                      :stroke="ring.stroke"
                      :stroke-width="ring.width"
                    />
                    <line
                      v-for="(pt, i) in radarVertices"
                      :key="'axis-' + i"
                      x1="180"
                      y1="180"
                      :x2="pt.x"
                      :y2="pt.y"
                      stroke="rgba(31,36,48,0.08)"
                      stroke-width="1"
                    />
                    <polygon
                      :points="radarData"
                      fill="url(#reportRadarFill)"
                      stroke="#f05a25"
                      stroke-width="2"
                      stroke-linejoin="round"
                    />
                    <circle
                      v-for="(pt, i) in radarDataPoints"
                      :key="'dot-' + i"
                      :cx="pt.x"
                      :cy="pt.y"
                      r="3.5"
                      fill="#fff"
                      stroke="#f05a25"
                      stroke-width="1.5"
                    />
                    <g
                      v-for="(label, i) in radarLabels"
                      :key="'label-' + i"
                      class="radar-label"
                      :class="{ weak: label.weak }"
                    >
                      <text :x="label.x" :y="label.y" text-anchor="middle">{{ label.shortName }}</text>
                      <text :x="label.x" :y="label.y + 15" text-anchor="middle">{{ label.scoreDisplay }}</text>
                    </g>
                  </svg>
                </div>

                <ul class="dimension-list">
                  <li
                    v-for="(dim, idx) in view.dimensions"
                    :key="dim.key"
                    :class="{ weak: dim.key === view.weakestDimensionKey }"
                  >
                    <div>
                      <span>{{ String(idx + 1).padStart(2, '0') }}</span>
                      <strong>{{ dim.name }}</strong>
                      <em v-if="dim.key === view.weakestDimensionKey">主要短板</em>
                      <b>{{ dim.scoreDisplay }}</b>
                    </div>
                    <div class="dimension-track" aria-hidden="true">
                      <i :style="{ width: `${Math.max(4, Math.min(100, dim.percent || 0))}%` }"></i>
                    </div>
                  </li>
                </ul>
              </div>
            </section>
          </div>

          <p v-if="view.coverage.canClaimCompleteTodos" class="coverage-note is-complete">
            已识别 {{ view.coverage.lossItemCount }} 条失分账目，并归并为 {{ view.coverage.remediationTaskCount }} 项改进任务，覆盖 {{ formatGap(view.coverage.coveredGapPoints) }} 分差距。
          </p>
          <p v-else-if="report.contractVersion.value === 'ai-score-report-v3'" class="coverage-note is-incomplete">
            评分事实已保留，但改进清单尚未完整生成；当前列表仅展示已确认事项。
          </p>

          <nav v-if="visibleContinueLinks.length" class="report-continue" aria-label="继续查看">
            <RouterLink
              v-for="link in visibleContinueLinks"
              :key="link.key"
              :to="report.sectionPath(link.key)"
            >
              <div>
                <strong>{{ link.title }}</strong>
                <span>{{ link.desc }}</span>
              </div>
              <b aria-hidden="true">›</b>
            </RouterLink>
          </nav>

        </div>
      </div>

      <AiScoreTeamSyncDialog
        v-model="syncOpen"
        :items="syncItems"
        :preselected-ids="syncPreselectedIds"
      />
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreReportCoachChrome from '../../components/ai-score/report/AiScoreReportCoachChrome.vue'
import AiScoreTeamSyncDialog from '../../components/ai-score/report/AiScoreTeamSyncDialog.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'
import { buildScoreSummaryPresentation } from '../../utils/aiScoreSummaryPresentation'
import { buildConclusionHome } from '../../utils/aiScoreConclusionHome'
import { useAuthStore } from '../../stores/auth'

const report = useAiScoreReportContext()
const router = useRouter()
const auth = useAuthStore()

const openRxId = ref('')
const syncOpen = ref(false)
const syncItems = ref([])
const syncPreselectedIds = ref([])

const officialScoreDisplay = computed(() => {
  const val = report.overallScore.value
  if (val === null || val === undefined || val === '') return '—'
  const number = Number(val)
  if (!Number.isFinite(number)) return '—'
  return number.toFixed(1)
})

const view = computed(() => {
  const result = report.result.value || {}
  const recovery = report.scoreRecoverySummary.value || {}
  return buildScoreSummaryPresentation({
    overallScore: report.overallScore.value,
    scoreLevel: report.scoreLevel.value,
    aiScore: report.aiScore.value,
    result,
    scoreRecoverySummary: recovery,
    scoreProjection: report.scoreProjection.value,
    lossLedger: report.lossLedger.value,
    coverageSummary: report.coverageSummary.value,
    ruleEngineReport: report.ruleEngineReport.value,
    trainingTasks: report.trainingTasks.value,
    unifiedTodos: report.unifiedTodos.value,
    reportWorkItemDrafts: report.reportWorkItemDrafts.value,
    currentStructuredDeductions: report.currentStructuredDeductions.value,
    dimensions: report.dimensions.value,
    evidenceAnchors: report.structuredEvidenceAnchors.value,
    evidenceFrames: report.evidenceFrames.value,
    reportTrackName: report.reportTrackName.value,
    reportSourceType: report.reportSourceType.value,
    sessionId: report.sessionId.value || report.effectiveSessionId.value,
    reportId: report.reportId.value,
    createdTeamTaskCount: report.createdTeamTaskCount.value,
    juryResult: report.juryResult.value,
    previousScoreDelta: firstPresent(
      result.previous_score_delta,
      result.previousScoreDelta,
      result.score_delta,
      result.scoreDelta,
      recovery.previous_score_delta,
      recovery.previousScoreDelta,
      recovery.score_delta,
      recovery.scoreDelta
    ),
    previousScore: firstPresent(result.previousScore, result.previous_score, recovery.previousScore),
    scoreComparison: firstPresent(
      result.scoreComparison,
      result.score_comparison,
      recovery.scoreComparison,
      recovery.score_comparison
    ),
    formatNumber: report.formatNumber,
    formatTime: report.formatTime
  })
})

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

const todosView = computed(() => ({ items: report.unifiedTodos.value || [] }))

/** Top 3: prefer todos presentation detail, fall back to score summary prescriptions. */
const topItems = computed(() => {
  const todoById = new Map(todosView.value.items.map(item => [item.id, item]))
  const fromSummary = view.value.topPrescriptions
  if (fromSummary.length) {
    return fromSummary.map((rx, index) => {
      const todo = todoById.get(rx.id)
      const desc = firstNonEmpty(
        todo?.issueParagraph,
        rx.issueParagraph,
        todo?.why && todo.why !== rx.title ? todo.why : '',
        rx.reason && rx.reason !== rx.title ? rx.reason : '',
        rx.desc
      )
      const how = firstNonEmpty(todo?.how, rx.action)
      const doneLines = todo?.doneLines?.length
        ? todo.doneLines
        : (rx.acceptance ? [rx.acceptance] : [])
      const howSteps = todo?.howSteps?.length ? todo.howSteps : (rx.howSteps || [])
      return {
        id: rx.id,
        index: index + 1,
        title: rx.title,
        desc,
        how,
        howSteps,
        doneLines,
        dimension: firstNonEmpty(todo?.dimension, rx.dimension, ''),
        priorityLabel: firstNonEmpty(todo?.priorityLabel, rx.priorityLabel, index === 0 ? '先改' : '建议改'),
        recoverDisplay: firstNonEmpty(todo?.recoverDisplay, rx.recoverDisplay),
        scoreImpactLabel: firstNonEmpty(todo?.scoreImpactLabel, ''),
        evidenceAnchorIds: todo?.evidenceAnchorIds?.length ? todo.evidenceAnchorIds : rx.evidenceAnchorIds
      }
    })
  }
  return todosView.value.items.slice(0, 3).map((todo, index) => ({
    id: todo.id,
    index: index + 1,
    title: todo.title,
    desc: todo.issueParagraph || (todo.why && todo.why !== todo.title ? todo.why : ''),
    how: todo.how || '',
    howSteps: todo.howSteps || [],
    doneLines: todo.doneLines || [],
    dimension: todo.dimension || '',
    priorityLabel: todo.priorityLabel || (index === 0 ? '先改' : '建议改'),
    recoverDisplay: todo.recoverDisplay || '',
    scoreImpactLabel: todo.scoreImpactLabel || '',
    evidenceAnchorIds: todo.evidenceAnchorIds || []
  }))
})

const challengeSet = computed(() => report.challenges?.value || { scanned: false, items: [] })

const home = computed(() => buildConclusionHome({
  overallScore: report.overallScore.value,
  officialScore: report.overallScore.value,
  contractVersion: report.contractVersion.value,
  stability: report.stability?.value || report.result.value?.stability,
  verifyClaims: report.verifyClaims?.value || report.result.value?.verifyClaims || report.result.value?.verify_claims,
  taskBook: report.taskBook?.value || report.result.value?.taskBook || report.result.value?.task_book,
  scoreGap: report.scoreGap?.value || report.result.value?.scoreGap || report.result.value?.score_gap,
  deliberation: report.deliberation?.value || report.result.value?.deliberation,
  teacherConfirmed: report.teacherConfirmed?.value || report.result.value?.teacherConfirmed,
  result: report.result.value
}))

const canResolveChallenge = computed(() => {
  const role = String(auth.user?.role || '').toUpperCase()
  return ['TEACHER', 'ADMIN', 'SUPER_ADMIN', 'SCHOOL_ADMIN'].includes(role) && !home.value.finalized
})

const newerReportPath = computed(() => {
  const sessionId = home.value.stability.newerSessionId
  return sessionId ? `/ai-score/report/${sessionId}/result` : ''
})

const resultLead = computed(() => {
  if (home.value.stability.pinUnstable) return home.value.stability.headline
  if (home.value.stability.band === 'not_reviewed') return home.value.stability.headline
  const gap = view.value.metrics?.fullGapDisplay
  const todos = view.value.metrics?.prescriptionCount
  const bits = []
  if (gap) bits.push(`距离满分还差 ${gap} 分`)
  if (todos) bits.push(`${todos} 项可改`)
  bits.push('先看结论六块，再去待办逐步改。')
  return bits.join(' · ')
})

function pillClass(rx, idx) {
  const label = String(rx?.priorityLabel || (idx === 0 ? '先改' : ''))
  if (label.includes('先')) return 'is-p0'
  if (label.includes('后')) return 'is-p2'
  return 'is-p1'
}

const chromeSubtitle = computed(() => {
  const meta = view.value.meta
  const parts = [meta.trackName, meta.projectName, meta.sessionLabel].filter(Boolean)
  if (meta.completedAt) {
    try {
      const d = new Date(meta.completedAt)
      if (!Number.isNaN(d.getTime())) {
        parts.push(`${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`)
      }
    } catch { /* ignore */ }
  }
  return parts.join(' · ')
})

const chromeTodoCount = computed(() => {
  const fromNav = (report.navItems?.value || []).find(item => item.key === 'todos')
  if (fromNav?.count !== undefined && fromNav?.count !== null && fromNav.count !== '') return fromNav.count
  return view.value.metrics.prescriptionCount || todosView.value.items.length || ''
})

const hasAnyMetric = computed(() => {
  // Show the four-metric strip whenever we have a real overall score (or any metric payload)
  if (view.value.score.value !== null && view.value.score.value !== undefined) return true
  const m = view.value.metrics
  return Boolean(m.goalDisplay || m.fullGapDisplay || m.predictedScoreDisplay || m.todayDisplay || m.prescriptionCount)
})

function formatGap(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(1) : '—'
}

const scoreNoteTitle = computed(() => {
  return view.value.score.levelLabel || ''
})

const scoreNoteBody = computed(() => {
  return view.value.score.levelText || ''
})

const visibleContinueLinks = computed(() =>
  (view.value.continueLinks || []).filter(link => link.show !== false)
)

const RADAR_CX = 180
const RADAR_CY = 180
const RADAR_R = 98
const RADAR_LABEL_R = 138

const radarVertices = computed(() => {
  const n = Math.max(view.value.dimensions.length, 3)
  return Array.from({ length: n }, (_, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI / n)
    return {
      x: RADAR_CX + RADAR_R * Math.cos(angle),
      y: RADAR_CY + RADAR_R * Math.sin(angle),
      angle
    }
  })
})

const radarRings = computed(() => {
  // denser, quieter rings — editorial product chart, not Excel spider
  const scales = [
    { scale: 0.25, stroke: 'rgba(23,26,36,0.045)', width: 1 },
    { scale: 0.5, stroke: 'rgba(23,26,36,0.07)', width: 1 },
    { scale: 0.75, stroke: 'rgba(23,26,36,0.055)', width: 1 },
    { scale: 1, stroke: 'rgba(23,26,36,0.1)', width: 1.15 }
  ]
  return scales.map((item) => ({
    ...item,
    points: radarRing(item.scale)
  }))
})

function radarRing(scale) {
  return radarVertices.value
    .map((pt) => {
      const x = RADAR_CX + (pt.x - RADAR_CX) * scale
      const y = RADAR_CY + (pt.y - RADAR_CY) * scale
      return `${x},${y}`
    })
    .join(' ')
}

const radarDataPoints = computed(() => {
  const dims = view.value.dimensions
  const n = dims.length
  if (!n) return []
  return dims.map((dim, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI / n)
    // floor radius so near-zero dims still show a vertex, without inflating mid scores
    const ratio = Math.max(0.08, Math.min(1, (dim.percent || 0) / 100))
    const r = ratio * RADAR_R
    return {
      x: RADAR_CX + r * Math.cos(angle),
      y: RADAR_CY + r * Math.sin(angle),
      weak: dim.key === view.value.weakestDimensionKey
    }
  })
})

const radarData = computed(() => radarDataPoints.value.map((p) => `${p.x},${p.y}`).join(' '))

const radarLabels = computed(() => {
  const dims = view.value.dimensions
  const n = dims.length
  if (!n) return []
  return dims.map((dim, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI / n)
    // slight outward bias so labels never collide with the polygon stroke
    const x = RADAR_CX + RADAR_LABEL_R * Math.cos(angle)
    const y = RADAR_CY + RADAR_LABEL_R * Math.sin(angle)
    const name = String(dim.name || '')
    // 中文两字短标；英文 key 已在 presentation 层映射为中文
    const shortName = /[\u4e00-\u9fff]/.test(name)
      ? (name.length > 2 ? name.slice(0, 2) : name)
      : (name.length > 4 ? name.slice(0, 4) : name)
    return {
      x,
      y,
      shortName,
      scoreDisplay: dim.scoreDisplay,
      weak: dim.key === view.value.weakestDimensionKey
    }
  })
})

function firstNonEmpty(...values) {
  return values.find(v => v !== undefined && v !== null && String(v).trim() !== '') || ''
}

function toggleRx(id) {
  openRxId.value = openRxId.value === id ? '' : id
}

function goTodos() {
  router.push(report.sectionPath('todos'))
}

function goTodosTask(rx) {
  const taskId = rx?.id
  if (taskId) {
    router.push({ path: report.sectionPath('todos'), query: { task: taskId } })
    return
  }
  goTodos()
}

function goWhy() {
  router.push(report.sectionPath('why'))
}

function formatChallengeTime(startMs) {
  const total = Math.max(0, Math.floor(Number(startMs) / 1000))
  const minutes = String(Math.floor(total / 60)).padStart(2, '0')
  const seconds = String(total % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}

function statusLabel(status) {
  if (status === 'accepted') return '已采纳'
  if (status === 'rejected') return '已驳回'
  return '未决'
}

function jumpChallenge(item) {
  const seconds = Number(item?.startMs) / 1000
  if (!Number.isFinite(seconds) || seconds < 0) {
    goWhy()
    return
  }
  router.push({ path: report.sectionPath('why'), query: { t: String(seconds) } })
}

async function resolveOne(item, action) {
  try {
    await report.resolveChallenge(item.challengeId, action)
    ElMessage.success(action === 'accept' ? '已采纳该条质询，权威分未改' : '已驳回该条质询')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '处理质询失败')
  }
}

function draftItemsForSync() {
  const drafts = report.reportWorkItemDrafts.value || []
  const todoById = new Map(todosView.value.items.map(item => [item.id, item]))
  return drafts.map((draft) => {
    const todo = todoById.get(draft.id)
    return {
      id: String(draft.id),
      title: String(draft.title || todo?.title || draft.id),
      recoverDisplay: todo?.recoverDisplay || ''
    }
  })
}

function openSyncDialog({ preselectedIds = [] } = {}) {
  const drafts = draftItemsForSync()
  if (!drafts.length) {
    ElMessage.warning('暂无映射到团队工作项的草稿，请到待办页处理')
    router.push(report.sectionPath('todos'))
    return
  }
  const draftIdSet = new Set(drafts.map(d => d.id))
  const pre = preselectedIds.map(String).filter(id => draftIdSet.has(id))
  syncItems.value = drafts
  syncPreselectedIds.value = pre.length ? pre : drafts.slice(0, Math.min(3, drafts.length)).map(d => d.id)
  syncOpen.value = true
}

function onChromeSync() {
  const topIds = topItems.value.map(item => item.id)
  if (!topIds.length && !report.reportWorkItemDrafts.value.length) {
    ElMessage.warning('暂无可同步的处方')
    return
  }
  openSyncDialog({ preselectedIds: topIds })
}

function syncOne(rx) {
  const drafts = draftItemsForSync()
  if (!drafts.length) {
    ElMessage.warning('暂无工作项草稿，请到待办页查看')
    router.push(report.sectionPath('todos'))
    return
  }
  const draftIds = drafts.map(d => d.id)
  if (draftIds.includes(rx.id)) {
    openSyncDialog({ preselectedIds: [rx.id] })
    return
  }
  const fallback = drafts[Math.min(Math.max((rx.index || 1) - 1, 0), drafts.length - 1)]
  openSyncDialog({ preselectedIds: fallback ? [fallback.id] : [] })
}

watch(() => topItems.value, (list) => {
  if (list.length && !openRxId.value) openRxId.value = list[0].id
}, { immediate: true })
</script>

<style scoped>
.result-page {
  --canvas: var(--ds-canvas, #f3f4f6);
  --surface: var(--ds-surface-solid, #ffffff);
  --line: var(--ds-line, rgba(28, 26, 22, 0.09));
  --ink: var(--ds-ink, #12141a);
  --ink-2: var(--ds-ink-2, #2c3038);
  --muted: var(--ds-muted, #6b7280);
  --faint: var(--ds-faint, #9aa1ad);
  --orange: var(--ds-orange, #e84a1c);
  --orange-deep: var(--ds-orange-deep, #c43a12);
  --orange-soft: var(--ds-orange-soft, #fee9df);
  --orange-wash: var(--ds-orange-wash, #fff7f2);
  --green: var(--ds-green, #0f9f6e);
  --shadow: none;
  --max: var(--ds-page-max, 1280px);
  --gutter: 0px;
  --font: var(--ds-font-sans, inherit);
  --num: var(--ds-font-num, inherit);

  box-sizing: border-box;
  color: var(--ink);
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #ffffff;
  background-image: none;
  font-family: var(--font);
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
}

.result-page :deep(em),
.result-page :deep(i) {
  font-style: normal;
}

/* 唯一纵向滚动层：定高 flex 子项，滚轮落在中间内容区即可滚 */
.result-scroll {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
  scrollbar-gutter: stable;
}

.result-stage {
  position: relative;
  padding-bottom: 48px;
}

.wrap {
  max-width: var(--max);
  margin: 0 auto;
  padding: 0 var(--gutter);
}

/* —— Hero —— */
.hero {
  padding: 44px 0 0;
  position: relative;
  z-index: 1;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 22px;
  font-size: 12px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.08em;
}

.eyebrow::before {
  content: "";
  width: 18px;
  height: 1.5px;
  background: var(--orange);
  border-radius: 2px;
}

.score-line {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 20px 32px;
  margin-bottom: 28px;
}

.score-giant {
  font-family: var(--num);
  font-size: clamp(80px, 12vw, 112px);
  font-weight: 700;
  letter-spacing: -0.035em;
  line-height: 0.9;
  font-variant-numeric: tabular-nums;
}

.score-giant .u {
  font-family: var(--font);
  font-size: 0.24em;
  font-weight: 600;
  color: var(--faint);
  margin-left: 4px;
  vertical-align: 0.6em;
}

.score-note {
  max-width: 200px;
  padding-bottom: 10px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--muted);
  font-weight: 500;
}

.score-note b {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--orange-deep);
}

.score-note b.good { color: var(--green); }
.score-note b.mid { color: #b45309; }
.score-note b.risk { color: var(--orange-deep); }

.headline {
  margin: 0 0 14px;
  max-width: 15em;
  font-size: clamp(26px, 3.6vw, 38px);
  font-weight: 700;
  line-height: 1.22;
  letter-spacing: 0;
}

.lead {
  margin: 0 0 28px;
  max-width: 36em;
  font-size: 16px;
  line-height: 1.7;
  color: var(--muted);
  font-weight: 500;
}

/* metrics inside hero — same paper, thin top rule only */
.metrics {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  padding: 22px 0 8px;
  border-top: 1px solid var(--line);
  margin: 0;
}

.metric {
  flex: 1 1 120px;
  min-width: 100px;
  padding: 4px 28px 4px 0;
  position: relative;
}

.metric:not(:last-child)::after {
  content: "";
  position: absolute;
  right: 14px;
  top: 18%;
  bottom: 18%;
  width: 1px;
  background: var(--line);
}

.metric .k {
  font-size: 12px;
  font-weight: 600;
  color: var(--faint);
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}

.metric .v {
  font-family: var(--num);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.metric .v.down { color: var(--orange-deep); }
.metric .v.up { color: var(--green); }

.metric .h {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
  line-height: 1.35;
}

.projection-note {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--faint);
  font-weight: 500;
}

.coverage-note {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.65;
  font-weight: 600;
}

.coverage-note.is-complete {
  color: #25633d;
  background: rgba(52, 168, 83, 0.08);
  border: 1px solid rgba(52, 168, 83, 0.18);
}

.coverage-note.is-incomplete {
  color: #9a4b13;
  background: rgba(234, 139, 41, 0.09);
  border: 1px solid rgba(234, 139, 41, 0.2);
}

/* —— Blocks —— */
.block {
  padding: 40px 0 4px;
  position: relative;
  z-index: 1;
}

.block-label {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.1em;
}

.block-title {
  margin: 0 0 10px;
  max-width: 14em;
  font-size: clamp(22px, 2.8vw, 28px);
  font-weight: 700;
  line-height: 1.25;
}

.block-lead {
  margin: 0 0 28px;
  max-width: 34em;
  font-size: 14px;
  line-height: 1.65;
  color: var(--muted);
  font-weight: 500;
}

/* prescriptions */
.rx {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rx-item {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: 8px 16px;
  padding: 26px 0;
  border-top: 1px solid var(--line);
  cursor: pointer;
}

.rx-item:last-child {
  border-bottom: 1px solid var(--line);
}

.rx-num {
  font-family: var(--num);
  font-size: 14px;
  font-weight: 700;
  color: var(--orange);
  padding-top: 5px;
}

.rx-item h3 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: 0;
}

.rx-item .desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--muted);
  font-weight: 500;
  max-width: 38em;
}

.rx-body-extra {
  display: none;
  margin-top: 16px;
}

.rx-item.is-open .rx-body-extra {
  display: block;
}

.rx-prose {
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink-2);
  font-weight: 500;
  padding: 16px 0 4px;
  max-width: 40em;
}

.rx-prose strong {
  font-weight: 700;
  color: var(--ink);
}

.rx-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.rx-gain {
  text-align: right;
  padding-top: 4px;
}

.rx-gain .n {
  font-family: var(--num);
  font-size: 26px;
  font-weight: 700;
  color: var(--green);
  line-height: 1;
}

.rx-gain .l {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--faint);
}

.chip {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--ink-2);
  cursor: pointer;
  text-decoration: none;
  font-family: inherit;
  font-style: normal;
  font-synthesis: none;
}

.chip:hover {
  background: rgba(255, 255, 255, 0.7);
}

.chip.primary {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}

.chip.soft {
  background: var(--orange-soft);
  border-color: transparent;
  color: var(--orange-deep);
}

.text-link {
  display: inline-block;
  margin-top: 18px;
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
  text-decoration: none;
}

.text-link:hover {
  color: var(--orange);
}

.empty-block {
  padding: 24px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.empty-block p {
  color: var(--muted);
  margin: 0 0 14px;
  font-size: 14px;
}

.empty-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* soft jury feature — light bg, orange left border */
.feature {
  display: grid;
  grid-template-columns: 1.35fr 0.85fr;
  gap: 20px;
  padding: 24px 24px 22px;
  border-radius: 18px;
  margin: 4px 0 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(255, 247, 243, 0.9));
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  width: 100%;
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  border-left: 3px solid var(--orange);
  transition: border-color 160ms ease, box-shadow 160ms ease;
  font-family: inherit;
  font-style: normal;
  font-synthesis: none;
}

.feature:hover {
  border-color: rgba(240, 75, 24, 0.28);
  box-shadow: 0 18px 44px rgba(116, 71, 39, 0.1);
}

.feature .block-label {
  color: var(--orange-deep);
}

.feature h2 {
  margin: 0 0 10px;
  font-size: clamp(20px, 2.4vw, 26px);
  font-weight: 700;
  color: var(--ink);
  line-height: 1.25;
}

.feature p {
  margin: 0 0 16px;
  max-width: 36em;
  font-size: 14px;
  line-height: 1.65;
  color: var(--muted);
  font-weight: 500;
}

.feature p strong {
  color: var(--ink);
}

.feature-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 28px;
  margin-bottom: 16px;
}

.feature-stats span {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--faint);
  margin-bottom: 4px;
}

.feature-stats b {
  font-family: var(--num);
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}

.feature-stats b.warn {
  color: var(--orange-deep);
}

.feature-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--orange), #ff7a45);
  color: #fff;
  box-shadow: 0 8px 18px rgba(240, 75, 24, 0.22);
  pointer-events: none;
}

.feature-side {
  border-left: 1px solid var(--line);
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.mini-p {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.mini-p span {
  height: 32px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid var(--line);
  font-family: var(--num);
  font-size: 10px;
  font-weight: 700;
  color: var(--ink-2);
}

.feature-side small {
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}

/* dimensions — editorial radar + list */
.dim-lead {
  margin-bottom: 8px;
}

.dim-row {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: 36px 48px;
  align-items: center;
  margin-top: 8px;
}

.radar-stage {
  position: relative;
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
  aspect-ratio: 1;
  /* no card: chart sits on the page paper */
  background: transparent;
  border: 0;
  box-shadow: none;
}

.radar-haze {
  position: absolute;
  inset: 14% 12% 16%;
  border-radius: 50%;
  background:
    radial-gradient(circle at 50% 46%, rgba(255, 190, 140, 0.16), transparent 58%),
    radial-gradient(circle at 50% 55%, rgba(240, 75, 24, 0.05), transparent 72%);
  pointer-events: none;
  filter: blur(2px);
  z-index: 0;
}

.radar-svg {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}

.radar-orbit {
  animation: radar-orbit-spin 28s linear infinite;
  transform-origin: 180px 180px;
}

@keyframes radar-orbit-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.radar-shape {
  animation: radar-reveal 900ms cubic-bezier(0.22, 1, 0.36, 1) both;
  transform-origin: 180px 180px;
}

.radar-shape-glow {
  animation: radar-reveal 900ms cubic-bezier(0.22, 1, 0.36, 1) both;
  transform-origin: 180px 180px;
}

@keyframes radar-reveal {
  from {
    opacity: 0;
    transform: scale(0.86);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.radar-label-name {
  font-size: 11px;
  font-weight: 700;
  fill: var(--ink-2);
  letter-spacing: 0.02em;
}

.radar-label-score {
  font-family: var(--num);
  font-size: 10px;
  font-weight: 700;
  fill: var(--muted);
}

.radar-label.weak .radar-label-name {
  fill: var(--orange-deep);
}

.radar-label.weak .radar-label-score {
  fill: var(--orange-deep);
}

.dims {
  list-style: none;
  margin: 0;
  padding: 0;
}

.dims li {
  padding: 14px 0 12px;
  border-bottom: 1px solid var(--line);
}

.dims li:first-child {
  border-top: 1px solid var(--line);
  padding-top: 16px;
}

.dim-main {
  display: grid;
  gap: 10px;
}

.dim-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
}

.dims .name {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 0;
}

.dims .name em {
  font-style: normal;
  font-family: var(--num);
  font-size: 11px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.06em;
  min-width: 1.6em;
}

.dims .name mark {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--orange-wash);
  border: 1px solid var(--orange-soft);
  color: var(--orange-deep);
  font-size: 11px;
  font-weight: 700;
}

.dims .val {
  font-family: var(--num);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
  flex-shrink: 0;
}

.dim-track {
  height: 4px;
  border-radius: 999px;
  background: rgba(23, 26, 36, 0.06);
  overflow: hidden;
}

.dim-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(240, 75, 24, 0.35), #f04b18 70%, #ff8a55);
  box-shadow: 0 0 12px rgba(240, 75, 24, 0.25);
  transition: width 700ms cubic-bezier(0.22, 1, 0.36, 1);
}

.dims li.weak .name {
  color: var(--orange-deep);
}

.dims li.weak .val {
  color: var(--orange-deep);
}

.dims li.weak .dim-track i {
  background: linear-gradient(90deg, rgba(217, 67, 18, 0.45), #d94312);
}

/* continue strip */
.continue {
  margin: 28px 0 40px;
  padding-top: 24px;
  border-top: 1px solid var(--line);
}

.continue-label {
  margin: 0 0 16px;
  font-size: 12px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.1em;
}

.continue-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.continue-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  text-align: left;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
  transition: color 120ms ease;
  text-decoration: none;
  color: inherit;
}

.continue-row:hover {
  color: var(--orange);
}

.continue-row:hover .arrow {
  transform: translateX(3px);
  color: var(--orange);
}

.continue-row strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
  color: inherit;
}

.continue-row span:not(.arrow) {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
  line-height: 1.5;
}

.continue-row:hover span:not(.arrow) {
  color: var(--muted);
}

.continue-row .arrow {
  font-size: 18px;
  color: var(--faint);
  transition: 120ms ease;
  flex-shrink: 0;
}

@media (max-width: 860px) {
  .rx-item {
    grid-template-columns: 48px 1fr;
  }

  .rx-gain {
    grid-column: 2;
    text-align: left;
    display: flex;
    gap: 10px;
    align-items: baseline;
  }

  .feature {
    grid-template-columns: 1fr;
  }

  .feature-side {
    border-left: 0;
    border-top: 1px solid var(--line);
    padding-left: 0;
    padding-top: 16px;
  }

  .dim-row {
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .radar-stage {
    max-width: 300px;
  }

  .metric:not(:last-child)::after {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .radar-orbit,
  .radar-shape,
  .radar-shape-glow {
    animation: none !important;
  }

  .dim-track i {
    transition: none;
  }
}

/* A 方案：与训练营 / 训练任务页面使用同一套页面骨架 */
.result-page {
  --report-orange: #ff6a2a;
  --report-orange-deep: #d94b16;
  --report-orange-soft: #fff1e8;
  --report-ink: #1f2430;
  --report-muted: #6f7684;
  --report-faint: #9a9fa8;
  --report-line: #e8e3dc;
  --report-panel: #ffffff;
  --report-panel-soft: #fbfaf8;

  background: transparent;
  color: var(--report-ink);
}

.result-scroll {
  background: transparent;
}

.conclusion-home {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 28px;
}

.conclusion-block {
  min-height: 112px;
  padding: 16px 18px;
  border: 1px solid var(--line);
  background: #fff;
}

.conclusion-block span {
  display: block;
  margin-bottom: 8px;
  color: var(--faint);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.conclusion-block strong,
.conclusion-block b {
  display: block;
  color: var(--ink);
  font-size: 18px;
  line-height: 1.3;
}

.conclusion-block p,
.conclusion-block li {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.conclusion-block ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.conclusion-block em {
  margin-right: 8px;
  font-style: normal;
}

.conclusion-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.conclusion-split small {
  display: block;
  color: var(--faint);
  font-size: 11px;
}

.conclusion-gaps {
  margin-top: 8px;
}

.conclusion-gaps li + li {
  margin-top: 4px;
}

.conclusion-block.is-red {
  border-color: #f3b4a0;
  background: var(--orange-wash);
}

.conclusion-block.is-yellow {
  border-color: #ead38a;
  background: #fff9e8;
}

.conclusion-block.is-green {
  border-color: #b9e0d1;
  background: #f3fbf7;
}

.challenge-panel {
  margin: 20px 0 8px;
}

.challenge-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.challenge-item {
  padding: 12px 0;
  border-top: 1px solid var(--line);
}

.challenge-item b {
  display: inline;
  margin-right: 6px;
}

.challenge-item em {
  margin-left: 8px;
  color: var(--faint);
  font-style: normal;
}

.challenge-item__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.challenge-adjust {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.conclusion-block.is-not_reviewed,
.conclusion-block.is-unlit {
  background: #fafafa;
}

@media (max-width: 720px) {
  .conclusion-home,
  .conclusion-split {
    grid-template-columns: 1fr;
  }
}

.report-standard {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 var(--ds-space-8, 32px);
  box-sizing: border-box;
}

.report-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 32px;
  margin-bottom: 24px;
}

.report-page-head h1,
.report-page-head p,
.report-session span,
.report-session strong,
.report-session small {
  margin: 0;
}

.report-page-head h1 {
  color: var(--report-ink);
  font-size: 28px;
  font-weight: 760;
  line-height: 1.2;
  letter-spacing: -0.035em;
}

.report-page-head p {
  margin-top: 8px;
  color: var(--report-muted);
  font-size: 13px;
  line-height: 1.6;
}

.report-head-copy {
  min-width: 0;
  flex: 1;
}

.report-page-actions {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.report-session {
  min-width: 0;
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.report-session span,
.report-session strong,
.report-session small {
  display: inline;
}

.report-session span {
  color: var(--report-muted);
  font-size: 12px;
}

.report-session strong {
  color: var(--report-ink);
  font-size: 12px;
}

.report-session small {
  max-width: 260px;
  overflow: hidden;
  color: var(--report-faint);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-overview {
  min-height: 104px;
  padding: 18px 24px;
  display: grid;
  grid-template-columns: minmax(270px, 1.15fr) minmax(280px, 0.95fr) auto;
  align-items: center;
  gap: 28px;
  border-top: 1px solid var(--report-line);
  border-bottom: 1px solid var(--report-line);
  background: rgba(255, 255, 255, 0.48);
}

.report-overview__identity p,
.report-overview__identity h2,
.report-overview__identity > div > span {
  margin: 0;
}

.report-overview__identity p {
  color: var(--report-orange);
  font-size: 10px;
  font-weight: 750;
}

.report-overview__identity h2 {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin: 3px 0 5px;
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 28px;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.report-overview__identity h2 small {
  color: var(--report-faint);
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
}

.report-overview__identity h2 span {
  margin-left: 7px;
  padding: 4px 8px;
  border-radius: 999px;
  color: #bd4b1d;
  background: var(--report-orange-soft);
  font-family: var(--font);
  font-size: 10px;
  font-weight: 750;
}

.report-overview__identity h2 span.good {
  color: #1d7856;
  background: #eaf7f0;
}

.report-overview__identity > div > span {
  display: block;
  max-width: 310px;
  overflow: hidden;
  color: var(--report-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-overview__progress {
  display: grid;
  gap: 10px;
}

.report-overview__progress strong,
.report-overview__progress span {
  display: block;
}

.report-overview__progress strong {
  color: var(--report-ink);
  font-size: 12px;
}

.report-overview__progress strong em {
  margin-left: 5px;
  color: var(--report-orange);
  font-style: normal;
}

.report-overview__progress span {
  overflow: hidden;
  margin-top: 4px;
  color: var(--report-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-progress-track {
  overflow: hidden;
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: #ece8e3;
}

.report-progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--report-orange);
  transition: width 500ms ease;
}

.report-overview__metrics {
  align-self: stretch;
  display: flex;
  align-items: center;
}

.report-overview__metrics div {
  min-width: 94px;
  padding: 6px 16px;
  border-left: 1px solid var(--report-line);
  text-align: center;
}

.report-overview__metrics strong,
.report-overview__metrics span {
  display: block;
}

.report-overview__metrics strong {
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 19px;
  font-variant-numeric: tabular-nums;
}

.report-overview__metrics span {
  margin-top: 5px;
  color: var(--report-muted);
  font-size: 11px;
}

.report-toolbar {
  margin: 26px 0 18px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.report-toolbar h2,
.report-toolbar p {
  margin: 0;
}

.report-toolbar h2 {
  color: var(--report-ink);
  font-size: 20px;
}

.report-toolbar p {
  margin-top: 6px;
  color: var(--report-muted);
  font-size: 12px;
}

.report-tabs {
  padding: 4px;
  display: flex;
  gap: 2px;
  border: 1px solid var(--report-line);
  border-radius: 12px;
  background: #f7f4f0;
}

.report-tabs a {
  min-height: 36px;
  padding: 0 15px;
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  color: #666d78;
  font-size: 12px;
  font-weight: 650;
  text-decoration: none;
}

.report-tabs a span {
  margin-left: 5px;
  color: var(--report-faint);
  font-size: 10px;
}

.report-tabs a.is-active {
  color: var(--report-ink);
  background: #fff;
  box-shadow: 0 3px 10px rgba(45, 36, 29, 0.08);
}

.report-tabs a.is-active span {
  color: var(--report-orange);
}

.report-cycle-card,
.report-insight-card {
  overflow: hidden;
  border: 1px solid var(--report-line);
  border-radius: 16px;
  background: var(--report-panel);
  box-shadow: 0 10px 30px rgba(38, 32, 27, 0.04);
}

.report-cycle-card__head {
  min-height: 84px;
  padding: 18px 24px;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  border-bottom: 1px solid var(--report-line);
  background: var(--report-panel-soft);
}

.report-cycle-card__number,
.report-insight-card header > div > span {
  color: var(--report-orange);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.report-cycle-card__head h2,
.report-cycle-card__head p {
  margin: 0;
}

.report-cycle-card__head h2 {
  color: var(--report-ink);
  font-size: 16px;
}

.report-cycle-card__head p,
.report-cycle-card__head > span:last-child {
  margin-top: 5px;
  color: var(--report-muted);
  font-size: 11px;
}

.report-cycle-card__body {
  margin: 0 24px;
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
}

.report-score-rail {
  position: relative;
  padding: 28px 24px 28px 2px;
  border-right: 1px solid var(--report-line);
}

.report-score-rail span,
.report-score-rail strong,
.report-score-rail small {
  display: block;
}

.report-score-rail span {
  color: var(--report-faint);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.report-score-rail strong {
  margin-top: 7px;
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

.report-score-rail small {
  margin-top: 4px;
  color: var(--report-muted);
  font-size: 11px;
}

.report-score-rail i {
  position: absolute;
  top: 35px;
  right: -5px;
  width: 9px;
  height: 9px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: var(--report-orange);
  box-shadow: 0 0 0 1px var(--report-orange), 0 0 0 5px rgba(255, 106, 42, 0.1);
}

.report-priority-body {
  min-width: 0;
  padding: 24px 0 26px 28px;
}

.report-diagnosis {
  min-height: 42px;
  margin-bottom: 12px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  border: 1px solid #eee7df;
  border-radius: 10px;
  background: var(--report-panel-soft);
}

.report-diagnosis span {
  padding: 4px 8px;
  border-radius: 999px;
  color: #b94b20;
  background: var(--report-orange-soft);
  font-size: 10px;
  font-weight: 750;
}

.report-diagnosis p {
  margin: 0;
  color: var(--report-ink);
  font-size: 12px;
  font-weight: 650;
  line-height: 1.55;
}

.priority-items {
  display: grid;
  gap: 10px;
}

.priority-item {
  min-height: 104px;
  padding: 16px 16px 16px 18px;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 15px;
  border: 1px solid #ece8e3;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.priority-item:hover,
.priority-item:focus-within,
.priority-item.is-open {
  border-color: rgba(255, 106, 42, 0.42);
  box-shadow: 0 10px 26px rgba(78, 52, 33, 0.07);
}

.priority-item:hover {
  transform: translateY(-2px);
}

.priority-item__signal {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #c94e18;
  background: var(--report-orange-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  font-weight: 800;
}

.priority-item__content {
  min-width: 0;
}

.priority-item__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.priority-item h3,
.priority-item p {
  margin: 0;
}

.priority-item h3 {
  color: var(--report-ink);
  font-size: 14px;
}

.priority-item__primary {
  flex: 0 0 auto;
  padding: 3px 6px;
  border-radius: 5px;
  color: #d5551c;
  background: var(--report-orange-soft);
  font-size: 9px;
  font-weight: 750;
}

.priority-item__content > p {
  overflow: hidden;
  margin-top: 7px;
  color: var(--report-muted);
  font-size: 11px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.priority-item__meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px 14px;
  color: #8a9099;
  font-size: 10px;
}

.priority-item__meta span {
  position: relative;
}

.priority-item__meta span + span::before {
  position: absolute;
  top: 50%;
  left: -8px;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: #babdc3;
  content: "";
}

.priority-item__detail {
  display: none;
  margin-top: 15px;
  padding-top: 14px;
  border-top: 1px solid var(--report-line);
}

.priority-item.is-open .priority-item__detail {
  display: block;
}

.priority-item__detail p {
  margin: 0 0 8px;
  color: var(--report-muted);
  font-size: 11px;
  line-height: 1.65;
}

.priority-item__detail p strong {
  margin-right: 8px;
  color: var(--report-ink);
}

.priority-item--coach .priority-item__issue {
  margin: 8px 0 0;
  color: var(--report-ink);
  font-size: 13px;
  line-height: 1.7;
}

.priority-item--coach .priority-item__detail p,
.priority-item--coach .priority-steps {
  font-size: 12.5px;
  line-height: 1.7;
  color: #3a3f49;
}

.priority-steps {
  margin: 0 0 12px;
}

.priority-steps strong {
  display: block;
  margin-bottom: 6px;
  color: var(--report-ink);
}

.priority-steps ol {
  margin: 0;
  padding-left: 1.2em;
}

.priority-steps li {
  margin: 0 0 6px;
}

.priority-steps em {
  color: var(--report-muted);
  font-style: normal;
}

.report-score-rail--coach {
  text-align: left;
}

.report-score-rail__gap {
  margin: 10px 0 0;
  color: var(--report-muted);
  font-size: 12px;
  line-height: 1.5;
}

.report-diagnosis--coach p {
  font-size: 14px;
  line-height: 1.75;
  color: var(--report-ink);
}

.priority-item__actions {
  margin-top: 13px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.priority-item__actions button {
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid var(--report-line);
  border-radius: 8px;
  color: #464b54;
  background: #fff;
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.priority-item__actions .action-primary {
  border-color: var(--report-orange-deep);
  color: #fff;
  background: var(--report-orange-deep);
}

.priority-item__action {
  min-width: 105px;
  display: grid;
  justify-items: end;
  gap: 13px;
}

.priority-item__action > span {
  padding: 4px 8px;
  border-radius: 999px;
  color: #c94e18;
  background: var(--report-orange-soft);
  font-size: 10px;
  font-weight: 700;
}

.priority-item__action strong {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #414650;
  font-size: 11px;
}

.priority-item__action b {
  font-size: 16px;
  font-weight: 500;
  transition: transform 180ms ease;
}

.priority-item.is-open .priority-item__action b {
  transform: rotate(90deg);
}

.report-empty {
  padding: 28px;
  border: 1px dashed var(--report-line);
  border-radius: 12px;
  color: var(--report-muted);
  text-align: center;
  font-size: 12px;
}

.report-more-link {
  margin-top: 15px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--report-orange-deep);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.report-insight-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(300px, 0.75fr);
  gap: 18px;
}

.report-insight-card header {
  min-height: 76px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--report-line);
  background: var(--report-panel-soft);
}

.report-insight-card header > div {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  align-items: baseline;
}

.report-insight-card header h2,
.report-insight-card header p {
  margin: 0;
}

.report-insight-card header h2 {
  color: var(--report-ink);
  font-size: 15px;
}

.report-insight-card header p {
  grid-column: 2;
  margin-top: 5px;
  color: var(--report-muted);
  font-size: 10px;
}

.report-insight-card header a,
.report-insight-card header button {
  flex: 0 0 auto;
  border: 0;
  color: #555b65;
  background: transparent;
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}

.dimension-panel {
  min-height: 330px;
  padding: 18px 24px 22px;
  display: grid;
  grid-template-columns: minmax(250px, 0.95fr) minmax(260px, 1.05fr);
  align-items: center;
  gap: 26px;
}

.radar-stage {
  width: 100%;
  max-width: 300px;
  margin: 0 auto;
  aspect-ratio: 1;
}

.radar-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.radar-label text:first-child {
  fill: #5f6570;
  font-family: var(--font);
  font-size: 11px;
  font-weight: 650;
}

.radar-label text:last-child {
  fill: var(--report-faint);
  font-family: var(--num);
  font-size: 10px;
  font-weight: 650;
}

.radar-label.weak text:first-child,
.radar-label.weak text:last-child {
  fill: var(--report-orange-deep);
}

.dimension-list {
  margin: 0;
  padding: 0;
  display: grid;
  gap: 15px;
  list-style: none;
}

.dimension-list li > div:first-child {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
}

.dimension-list li span {
  color: var(--report-faint);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 10px;
  font-weight: 700;
}

.dimension-list li strong {
  color: var(--report-ink);
  font-size: 12px;
}

.dimension-list li em {
  padding: 3px 6px;
  border-radius: 5px;
  color: #c94e18;
  background: var(--report-orange-soft);
  font-size: 9px;
  font-style: normal;
  font-weight: 750;
}

.dimension-list li b {
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 13px;
}

.dimension-track {
  overflow: hidden;
  height: 4px;
  margin: 7px 0 0 36px;
  border-radius: 999px;
  background: #ece8e3;
}

.dimension-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #8e949f;
}

.dimension-list li.weak .dimension-track i {
  background: var(--report-orange);
}

.jury-body {
  min-height: 330px;
  padding: 26px 22px;
  display: flex;
  flex-direction: column;
}

.jury-personas {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.jury-personas span {
  min-height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid #eee7df;
  border-radius: 8px;
  color: #737985;
  background: var(--report-panel-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 9px;
  font-weight: 750;
}

.jury-body > p {
  margin: 20px 0;
  color: var(--report-muted);
  font-size: 11px;
  line-height: 1.7;
}

.jury-metrics {
  margin-top: auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-top: 1px solid var(--report-line);
}

.jury-metrics div {
  padding: 16px 8px 0;
  text-align: center;
}

.jury-metrics div + div {
  border-left: 1px solid var(--report-line);
}

.jury-metrics strong,
.jury-metrics span {
  display: block;
}

.jury-metrics strong {
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 17px;
}

.jury-metrics strong.warn {
  color: var(--report-orange-deep);
}

.jury-metrics span {
  margin-top: 5px;
  color: var(--report-muted);
  font-size: 9px;
}

.jury-waiting {
  margin-top: auto;
  padding: 16px;
  border-radius: 10px;
  color: var(--report-muted);
  background: var(--report-panel-soft);
  text-align: center;
  font-size: 11px;
}

.coverage-note {
  margin: 18px 0 0;
  border-radius: 10px;
  font-size: 11px;
}

.report-continue {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.report-continue a {
  min-height: 72px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid var(--report-line);
  border-radius: 12px;
  color: inherit;
  background: #fff;
  text-decoration: none;
}

.report-continue strong,
.report-continue span {
  display: block;
}

.report-continue strong {
  color: var(--report-ink);
  font-size: 12px;
}

.report-continue span {
  margin-top: 5px;
  color: var(--report-muted);
  font-size: 10px;
  line-height: 1.5;
}

.report-continue b {
  color: var(--report-faint);
  font-size: 20px;
  font-weight: 500;
}

@media (max-width: 1080px) {
  .report-overview {
    grid-template-columns: minmax(250px, 1fr) minmax(250px, 0.9fr);
  }

  .report-overview__metrics {
    grid-column: 1 / -1;
    padding-top: 10px;
    border-top: 1px solid var(--report-line);
  }

  .report-overview__metrics div {
    flex: 1;
    border-left: 0;
  }

  .report-insight-grid {
    grid-template-columns: 1fr;
  }

  .jury-body {
    min-height: auto;
  }
}

@media (max-width: 760px) {
  .report-standard {
    padding: 0 0 40px;
  }

  .report-page-head,
  .report-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .report-page-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .report-overview {
    padding: 18px 0;
    grid-template-columns: 1fr;
    gap: 16px;
    background: transparent;
  }

  .report-overview__progress {
    padding-top: 14px;
    border-top: 1px solid var(--report-line);
  }

  .report-overview__metrics {
    grid-column: auto;
  }

  .report-tabs {
    overflow-x: auto;
  }

  .report-tabs a {
    flex: 0 0 auto;
  }

  .report-cycle-card__head {
    grid-template-columns: 46px 1fr;
  }

  .report-cycle-card__head > span:last-child {
    grid-column: 2;
  }

  .report-cycle-card__body {
    grid-template-columns: 1fr;
    margin: 0 16px;
  }

  .report-score-rail {
    padding: 20px 0 13px;
    display: flex;
    align-items: baseline;
    gap: 9px;
    border-right: 0;
  }

  .report-score-rail strong,
  .report-score-rail small {
    margin: 0;
  }

  .report-score-rail i {
    display: none;
  }

  .report-priority-body {
    padding: 0 0 22px;
  }

  .priority-item {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .priority-item__action {
    grid-column: 2;
    min-width: 0;
    display: flex;
    justify-content: space-between;
  }

  .dimension-panel {
    grid-template-columns: 1fr;
  }

  .report-continue {
    grid-template-columns: 1fr;
  }

}

@media (prefers-reduced-motion: reduce) {
  .report-progress-track i,
  .priority-item,
  .priority-item__action b {
    transition: none;
  }
}

</style>
