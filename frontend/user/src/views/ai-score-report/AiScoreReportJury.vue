<template>
  <AiScoreReportShell title="多维评委" mode="editorial">
    <div class="jury-page">
      <div class="work">
        <header class="report-page-head">
          <div class="report-head-copy">
            <h1>多维评委</h1>
            <p>从九种评审取向复核同一场路演，辅助判断结论是否稳定。</p>
            <div class="report-session">
              <span>评分场次</span>
              <strong>{{ sessionTitle }}</strong>
              <small>{{ sessionSubtitle }}</small>
            </div>
          </div>
          <div class="report-page-actions" aria-label="报告操作">
            <BaseButton type="secondary" @click="report.downloadPdf?.()">下载报告</BaseButton>
            <BaseButton type="secondary" :to="report.sectionPath('result')">返回评分总结</BaseButton>
            <BaseButton
              v-if="canStartJury"
              :disabled="report.juryStarting.value || isProcessing"
              @click="handleStartJuryReview"
            >
              {{ regenLabel }}
            </BaseButton>
          </div>
        </header>

        <section class="report-overview" aria-label="多维评委概览">
          <div class="report-overview__identity">
            <p>本场得分</p>
            <h2>
              {{ formatScore(officialScore) }}
              <small>/ 100</small>
              <span v-if="levelLabel">{{ levelLabel }}</span>
            </h2>
            <span>多维评委仅用于交叉复核，不会改写本场得分。</span>
          </div>

          <div class="report-overview__progress">
            <div>
              <strong>评委复核 <em>{{ members.length }} / 9</em></strong>
              <span>九席独立评分，汇总时去掉最高分与最低分。</span>
            </div>
            <div class="report-progress-track" aria-hidden="true">
              <i :style="{ width: `${juryProgress}%` }"></i>
            </div>
          </div>

          <div class="report-overview__metrics">
            <div>
              <strong>{{ scoredMembers.length }}</strong>
              <span>有效席位</span>
            </div>
            <div>
              <strong>{{ formatScore(juryAverageDisplay) }}</strong>
              <span>评委均分</span>
            </div>
          </div>
        </section>

        <header class="head">
          <span class="label">R03</span>
          <div>
            <h2>多维评委复核</h2>
            <p class="lead">
              点选评委查看独立评语，并对照<strong>去掉最高与最低</strong>后的复核结果。
            </p>
          </div>
        </header>

        <section v-if="isProcessing" class="state-card">
          <h3>多维评委生成中</h3>
          <p>正在从 16 种人格中抽取 9 位并各自独立打分。本场得分不会被改写。</p>
        </section>

        <section v-else-if="isEmpty" class="state-card">
          <h3>{{ isFailed ? '多维评委生成失败' : '还没有生成多维评委' }}</h3>
          <p>{{ emptyStateMessage }}</p>
        </section>

        <section v-else-if="report.juryLoading.value" class="state-card">
          <h3>正在加载多维评委</h3>
          <p>正在汇总九位评委的独立打分，请稍候。</p>
        </section>

        <section v-else-if="report.juryError.value" class="state-card">
          <h3>多维评委暂不可用</h3>
          <p>{{ report.juryError.value }}</p>
        </section>

        <template v-else>
          <section class="jury-conclusion" aria-label="多维评委复核结论">
            <div class="jury-conclusion__copy">
              <span>复核结论</span>
              <h3>{{ juryConclusionTitle }}</h3>
              <p>{{ juryConclusionBody }}</p>
            </div>
            <div class="jury-conclusion__numbers">
              <div>
                <span>本场得分</span>
                <strong>{{ formatScore(officialScore) }}</strong>
              </div>
              <div>
                <span>去极值均分</span>
                <strong>{{ formatScore(juryAverageDisplay) }}</strong>
              </div>
              <div>
                <span>两者相差</span>
                <strong :class="juryDiffTone">{{ formatDiff(juryDiffDisplay) }}</strong>
              </div>
            </div>
          </section>

          <div class="jury-workspace">
            <section class="jury-roster" aria-label="评委席">
              <header class="jury-roster__head">
                <div>
                  <span>评分构成</span>
                  <h3>哪些分数计入均分</h3>
                </div>
                <small>分组结果已自动标明</small>
              </header>

              <div class="jury-groups" role="listbox" aria-label="多维评委分组列表">
                <section
                  v-for="group in juryGroups"
                  :key="group.key"
                  class="jury-group"
                  :class="`is-${group.key}`"
                >
                  <header>
                    <strong>{{ group.title }}</strong>
                    <span>{{ group.description }}</span>
                  </header>
                  <div class="judge-grid">
                    <button
                      v-for="member in group.members"
                      :key="member.id"
                      type="button"
                      class="judge-card"
                      role="option"
                      :aria-selected="member.id === selectedMemberId"
                      :class="{
                        'is-selected': member.id === selectedMemberId,
                        'is-trimmed': Boolean(member.trimRole),
                        'is-pending': member.referenceScore == null
                      }"
                      @click="selectedMemberId = member.id"
                    >
                      <span class="judge-card__top">
                        <em>{{ member.personaCode }}</em>
                        <b>{{ formatSeatScore(member.referenceScore) }}</b>
                      </span>
                      <strong>{{ member.displayTitle }}</strong>
                      <small>{{ member.focusLine }}</small>
                      <span class="judge-card__status">
                        <template v-if="member.trimRole === 'high'">最高分 · 不计入均分</template>
                        <template v-else-if="member.trimRole === 'low'">最低分 · 不计入均分</template>
                        <template v-else-if="member.referenceScore == null">暂未生成评分</template>
                        <template v-else>计入均分</template>
                      </span>
                    </button>
                  </div>
                </section>
              </div>
            </section>

            <section v-if="selectedMember" class="sheet" aria-live="polite">
            <div class="sheet-top">
              <div class="sheet-id">
                <span class="code">{{ selectedMember.personaCode }}</span>
                <h3>{{ selectedMember.displayTitle }}</h3>
                <span class="sub">{{ selectedMember.lens }}</span>
                <span
                  v-if="selectedMember.trimRole === 'high'"
                  class="trim-inline"
                >已剔除 · 最高</span>
                <span
                  v-else-if="selectedMember.trimRole === 'low'"
                  class="trim-inline low"
                >已剔除 · 最低</span>
              </div>
              <div class="sheet-score">
                <span class="num">{{ formatSeatScore(selectedMember.referenceScore) }}</span>
                <span class="vs" :class="selectedVs.cls">{{ selectedVs.text }}</span>
              </div>
            </div>

            <div class="triptych">
              <div class="k">
                <h4>冲分要领</h4>
                <p>{{ selectedMember.keyLine }}</p>
              </div>
              <div class="ok">
                <h4>认可</h4>
                <p :class="{ quiet: !selectedMember.praiseLine || selectedMember.praiseLine.startsWith('报告未返回') }">
                  {{ selectedMember.praiseLine }}
                </p>
              </div>
              <div class="risk">
                <h4>担忧</h4>
                <p :class="{ quiet: !selectedMember.worryLine || selectedMember.worryLine.startsWith('报告未返回') }">
                  {{ selectedMember.worryLine }}
                </p>
              </div>
            </div>

            <div class="decide">
              <div>
                <div class="decide-label">下一轮先改 · 多人同盯</div>
                <div v-if="consensusCards.length" class="chips">
                  <span
                    v-for="item in consensusCards"
                    :key="item.title"
                    class="chip"
                    :class="{ 'is-hit': isChipHit(item, selectedMember) }"
                  >
                    {{ item.title }}
                    <em>{{ consensusFrequency(item) }}/{{ members.length || 9 }}</em>
                  </span>
                </div>
                <p v-else class="empty-inline">评委暂未返回可汇总的共识问题；可先看各位独立评语。</p>
              </div>
              <div class="decide-actions">
                <BaseButton :to="report.sectionPath('todos')">放进待办</BaseButton>
              </div>
            </div>
            </section>
          </div>
        </template>
      </div>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import BaseButton from '../../components/base/BaseButton.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()
const review = computed(() => normalizeReview(report.juryResult.value))
const selectedMemberId = ref('')

const canStartJury = computed(() => Boolean(report.effectiveSessionId.value || report.effectiveMeetingId.value))
const isProcessing = computed(() =>
  report.juryStarting.value
  || ['processing', 'pending', 'running'].includes(String(review.value?.status || '').toLowerCase())
)
const isEmpty = computed(() =>
  !review.value
  || review.value.status === 'empty'
  || !review.value.members?.length
)
const isFailed = computed(() => ['failed', 'partial_failed'].includes(String(review.value?.status || '').toLowerCase()))
const emptyStateMessage = computed(() => {
  if (isFailed.value) {
    return review.value?.explanation || review.value?.errorMessage || '评委生成失败，请点击重新生成。'
  }
  return '抽 9 位独立打分，去掉最高最低后取均分。只作对照，不修改本场得分。'
})

const members = computed(() => review.value.members || [])

const scoredMembers = computed(() =>
  members.value
    .filter((m) => m.referenceScore != null)
    .slice()
    .sort((a, b) => Number(a.referenceScore) - Number(b.referenceScore))
)

const pendingMembers = computed(() =>
  members.value.filter((m) => m.referenceScore == null)
)

const includedMembers = computed(() =>
  scoredMembers.value.filter((member) => !member.trimRole)
)

const trimmedLowMember = computed(() =>
  scoredMembers.value.find((member) => member.trimRole === 'low') || null
)

const trimmedHighMember = computed(() =>
  scoredMembers.value.find((member) => member.trimRole === 'high') || null
)

const trimmedMembers = computed(() =>
  [trimmedLowMember.value, trimmedHighMember.value].filter(Boolean)
)

const juryGroups = computed(() => [
  {
    key: 'included',
    title: '计入均分',
    description: `${includedMembers.value.length} 位评委`,
    members: includedMembers.value
  },
  {
    key: 'trimmed',
    title: '已剔除',
    description: '最低分与最高分',
    members: trimmedMembers.value
  },
  {
    key: 'pending',
    title: '尚未评分',
    description: `${pendingMembers.value.length} 位评委`,
    members: pendingMembers.value
  }
].filter((group) => group.members.length))

const officialScore = computed(() => firstPresent(
  report.overallScore?.value,
  review.value.officialScore,
  review.value.disputeReviewContext?.ruleEngineScore
))

const juryAverageDisplay = computed(() => firstPresent(
  report.juryResult.value?.jury?.trimmed_average_score,
  report.juryResult.value?.jury?.trimmedAverageScore,
  report.juryResult.value?.juryAverageScore,
  report.juryResult.value?.jury_average_score,
  review.value.juryAverageScore
))

const juryDiffDisplay = computed(() => {
  const average = firstNumber(juryAverageDisplay.value)
  const official = firstNumber(officialScore.value)
  if (average != null && official != null) return average - official
  return firstPresent(
    report.juryResult.value?.jury?.score_diff_from_official,
    report.juryResult.value?.jury?.scoreDiffFromOfficial,
    report.juryResult.value?.scoreDiffFromOfficial,
    report.juryResult.value?.score_diff_from_official,
    review.value.scoreDiffFromOfficial
  )
})

const juryConclusionTitle = computed(() => {
  const average = firstNumber(juryAverageDisplay.value)
  const official = firstNumber(officialScore.value)
  const diff = firstNumber(juryDiffDisplay.value)
  if (average == null) return '评委复核结果尚未完整生成'
  if (official == null || diff == null) return `去极值后的评委均分为 ${formatScore(average)} 分`
  if (Math.abs(diff) < 0.05) return '评委均分与本场得分一致'
  return `评委均分比本场得分${diff > 0 ? '高' : '低'} ${formatScore(Math.abs(diff))} 分`
})

const juryConclusionBody = computed(() => {
  const included = includedMembers.value.length
  const low = trimmedLowMember.value
  const high = trimmedHighMember.value
  if (low && high) {
    return `${included} 位评委计入均分；最低分 ${low.personaCode} ${formatSeatScore(low.referenceScore)} 分、最高分 ${high.personaCode} ${formatSeatScore(high.referenceScore)} 分已剔除。`
  }
  if (included) return `${included} 位评委计入均分，系统将按复核规则处理极值。`
  return '评委评分正在汇总，完整后会直接标出计入均分与已剔除席位。'
})

const juryDiffTone = computed(() => {
  const diff = firstNumber(juryDiffDisplay.value)
  if (diff == null || Math.abs(diff) < 0.05) return ''
  return diff > 0 ? 'is-higher' : 'is-lower'
})

const levelLabel = computed(() => String(report.scoreLevel?.value?.label || ''))

const trackName = computed(() => {
  const result = report.result?.value || {}
  return firstPresent(report.reportTrackName?.value, result.track_name, result.trackName, '')
})

const projectName = computed(() => {
  const result = report.result?.value || {}
  return firstPresent(result.project_name, result.projectName, result.project?.name, '')
})

const sessionLabel = computed(() => {
  const result = report.result?.value || {}
  return firstPresent(result.session_no, result.sessionNo, '')
})

const sessionTitle = computed(() => {
  const session = firstPresent(
    sessionLabel.value,
    report.sessionId?.value,
    report.effectiveSessionId?.value
  )
  return session ? `Session ${session}` : '本次路演'
})

const sessionSubtitle = computed(() => {
  const result = report.result?.value || {}
  const parts = [trackName.value, projectName.value].filter(Boolean)
  const completed = firstPresent(result.completed_at, result.completedAt)
  if (completed) {
    const date = new Date(completed)
    if (!Number.isNaN(date.getTime())) {
      parts.push(`${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`)
    }
  }
  return parts.join(' · ') || '评分结果已生成'
})

const juryProgress = computed(() => Math.min(100, Math.round((members.value.length / 9) * 100)))

const regenLabel = computed(() => {
  if (report.juryStarting.value || isProcessing.value) return '生成中'
  if (isEmpty.value) return '生成多维评委'
  return '重新抽取'
})

const selectedMember = computed(() =>
  members.value.find((m) => m.id === selectedMemberId.value)
  || scoredMembers.value[0]
  || members.value[0]
  || null
)

const selectedVs = computed(() => vsSession(selectedMember.value?.referenceScore, officialScore.value))

const consensusCards = computed(() => {
  const explicit = arrayFrom(firstPresent(
    review.value.aggregate?.consensusIssues,
    review.value.aggregate?.consensus_issues
  )).map((item, index) => normalizeConsensusItem(item, index))
  if (explicit.length) return explicit.slice(0, 5)

  const counts = new Map()
  for (const member of members.value) {
    const key = normalizeKey(member.worryLine)
    if (!key || key.length < 6) continue
    const title = String(member.worryLine || '').split(/[；;。]/u)[0].trim()
    if (!title) continue
    const prev = counts.get(title) || { title, count: 0 }
    prev.count += 1
    counts.set(title, prev)
  }
  return [...counts.values()]
    .filter((item) => item.count >= 2)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)
})

watch(
  () => [scoredMembers.value, members.value],
  () => {
    const list = scoredMembers.value.length ? scoredMembers.value : members.value
    if (!list.length) {
      selectedMemberId.value = ''
      return
    }
    if (!list.some((m) => m.id === selectedMemberId.value)) {
      const preferred = list.find((m) => !m.trimRole) || list[0]
      selectedMemberId.value = preferred.id
    }
  },
  { immediate: true }
)

async function handleStartJuryReview() {
  if (report.juryStarting.value) return
  await report.startJuryReview()
}

function isChipHit(item, member) {
  if (!item?.title || !member) return false
  const hay = [
    member.worryLine,
    member.keyLine,
    member.focusLine,
    member.lens,
    ...(member.themes || [])
  ].join(' ')
  return hay.includes(String(item.title))
}

function normalizeReview(value) {
  if (!value) return { status: 'empty', members: [] }
  const rawMembers = Array.isArray(value.members) ? value.members : []
  const official = firstPresent(value.officialScore, value.official_score, report.overallScore?.value)
  const juryAvg = firstPresent(
    value.juryAverageScore,
    value.jury_average_score,
    value.jury?.trimmed_average_score,
    value.jury?.trimmedAverageScore
  )
  const removedHigh = firstPresent(
    value.jury?.removed_high?.persona_code,
    value.jury?.removed_high?.personaCode,
    value.jury?.removedHigh?.persona_code,
    value.jury?.removedHigh?.personaCode,
    value.jury?.removed_high,
    value.jury?.removedHigh
  )
  const removedLow = firstPresent(
    value.jury?.removed_low?.persona_code,
    value.jury?.removed_low?.personaCode,
    value.jury?.removedLow?.persona_code,
    value.jury?.removedLow?.personaCode,
    value.jury?.removed_low,
    value.jury?.removedLow
  )

  return {
    ...value,
    status: value.status || (rawMembers.length ? 'completed' : 'empty'),
    officialScore: official,
    juryAverageScore: juryAvg,
    scoreDiffFromOfficial: firstPresent(
      value.scoreDiffFromOfficial,
      value.score_diff_from_official,
      value.jury?.score_diff_from_official,
      value.jury?.scoreDiffFromOfficial
    ),
    judgeCount: firstPresent(value.judgeCount, value.judge_count, rawMembers.length),
    disputeReviewContext: normalizeDisputeContext(firstPresent(value.disputeReviewContext, value.dispute_review_context)),
    members: rawMembers.map((member, index) =>
      normalizeMember(member, index, { official, removedHigh, removedLow })
    ),
    aggregate: normalizeAggregate(value.aggregate)
  }
}

function normalizeDisputeContext(value) {
  if (!value || typeof value !== 'object') return {}
  return {
    ...value,
    ruleEngineScore: firstPresent(value.ruleEngineScore, value.rule_engine_score, value.officialScore, value.official_score)
  }
}

function normalizeAggregate(value) {
  if (!value) return {}
  return {
    ...value,
    consensusIssues: arrayFrom(firstPresent(value.consensusIssues, value.consensus_issues, [])),
    nextTrainingPriorities: arrayFrom(firstPresent(value.nextTrainingPriorities, value.next_training_priorities, []))
  }
}

function normalizeMember(member, index, ctx = {}) {
  const personaView = objectFrom(firstPresent(member.persona_view, member.personaView))
  const personaCode = firstPresent(
    member.personaCode,
    member.persona_code,
    member.persona,
    member.code,
    personaView.personaCode,
    personaView.persona_code,
    personaView.code
  )
  const displayName = firstPresent(
    member.displayName,
    member.display_name,
    member.roleLabel,
    member.role_label,
    member.name,
    personaView.role_label,
    personaView.roleLabel,
    personaView.displayName,
    personaView.name,
    personaCode,
    `评委 ${index + 1}`
  )
  const shortLabel = firstPresent(member.short_label, member.shortLabel, personaView.short_label, personaView.shortLabel, '')
  const referenceScore = firstNumber(
    member.referenceScore,
    member.reference_score,
    member.overallScore,
    member.overall_score,
    member.finalScore,
    member.final_score,
    member.score
  )

  const concerns = arrayFrom(firstPresent(
    personaView.top_concerns,
    personaView.topConcerns,
    member.critical_issues,
    member.criticalIssues,
    member.perspectiveQuestions,
    member.perspective_questions
  )).map(normalizePlainText).filter(Boolean)

  const highlights = arrayFrom(firstPresent(
    member.highlights,
    member.strengths,
    personaView.highlights,
    personaView.strengths
  )).map(normalizePlainText).filter(Boolean)

  const suggestions = arrayFrom(firstPresent(
    member.trainingSuggestions,
    member.training_suggestions,
    member.improvement_priorities,
    member.improvementPriorities,
    personaView.improvement_priorities,
    personaView.improvementPriorities
  )).map((item) => normalizeSuggestion(item))

  const optimization = firstPresent(
    personaView.optimization_angle,
    personaView.optimizationAngle,
    personaView.score_reasoning_style,
    personaView.scoreReasoningStyle,
    member.summary,
    ''
  )

  const focusLine = shortLabel
    || concerns.slice(0, 2).join('、')
    || suggestions[0]?.issue
    || '路演表现'

  const keyLine = firstPresent(
    suggestions[0]?.suggestion,
    optimization,
    concerns[0] && `先回应：${concerns[0]}`,
    member.summary,
    '报告未返回该评委的冲分要领。'
  )

  const praiseLine = firstPresent(
    highlights[0],
    arrayFrom(member.evidence_summary?.strengths || member.evidenceSummary?.strengths)[0],
    '报告未返回该评委的认可点。'
  )

  const worryLine = firstPresent(
    concerns[0],
    suggestions[0]?.issue,
    arrayFrom(member.evidenceConcerns)[0],
    member.summary && member.summary !== keyLine ? member.summary : '',
    '报告未返回该评委的担忧点。'
  )

  const removedRole = String(firstPresent(member.removed_role, member.removedRole, '')).toLowerCase()
  let trimRole = ''
  if (removedRole === 'highest' || removedRole === 'high') trimRole = 'high'
  else if (removedRole === 'lowest' || removedRole === 'low') trimRole = 'low'
  else if (personaCode && String(ctx.removedHigh || '') === String(personaCode)) trimRole = 'high'
  else if (personaCode && String(ctx.removedLow || '') === String(personaCode)) trimRole = 'low'

  const track = firstPresent(report.reportTrackName?.value, '')
  const lens = shortLabel
    ? (track ? `${track} · ${shortLabel}` : shortLabel)
    : (track ? `${track} · 独立取向` : '独立取向评审')

  const themes = arrayFrom(firstPresent(
    member.themes,
    member.theme_tags,
    member.themeTags,
    personaView.themes
  )).map(normalizePlainText).filter(Boolean)

  return {
    ...member,
    id: String(firstPresent(member.id, member.memberId, member.member_id, member.seat_no, personaCode, `member-${index}`)),
    personaCode: personaCode || '—',
    displayTitle: String(displayName || '评委').replace(/评委$/u, ''),
    focusLine: String(focusLine || '路演表现'),
    lens,
    keyLine: String(keyLine || '报告未返回该评委的冲分要领。'),
    praiseLine: String(praiseLine || '报告未返回该评委的认可点。'),
    worryLine: String(worryLine || '报告未返回该评委的担忧点。'),
    referenceScore,
    trimRole,
    themes,
    trainingSuggestions: suggestions
  }
}

function normalizeSuggestion(item) {
  const parsed = parseJsonLike(item)
  const source = parsed && typeof parsed === 'object' ? parsed : { suggestion: normalizePlainText(item) }
  return {
    issue: firstPresent(source.issue, source.problem, source.title, source.name, normalizePlainText(item), ''),
    suggestion: firstPresent(source.suggestion, source.action, source.improvement, source.fix, normalizePlainText(item), ''),
    dimension: firstPresent(source.dimension, source.category, '')
  }
}

function normalizeConsensusItem(item, index) {
  const parsed = parseJsonLike(item)
  const source = parsed && typeof parsed === 'object' ? parsed : { title: normalizePlainText(item) }
  return {
    title: firstPresent(source.title, source.issue, source.name, normalizePlainText(item), `共识问题 ${index + 1}`),
    count: Number(firstPresent(source.count, source.frequency, source.hit_count, source.hitCount, 1)) || 1
  }
}

function consensusFrequency(item) {
  return Math.max(1, Math.min(Number(item?.count) || 1, members.value.length || 9))
}

function vsSession(score, sessionScore) {
  const s = firstNumber(score)
  const o = firstNumber(sessionScore)
  if (s == null) return { text: '暂无独立分', cls: '' }
  if (o == null) return { text: '与本场得分对照待生成', cls: '' }
  const d = s - o
  if (Math.abs(d) < 0.05) return { text: '与本场得分持平', cls: '' }
  if (d < 0) return { text: `较本场 ${formatDiff(d)}`, cls: 'down' }
  return { text: `较本场 ${formatDiff(d)}`, cls: 'up' }
}

function formatScore(value) {
  if (value == null || value === '') return '—'
  return report.formatNumber(value, 1)
}

function formatSeatScore(value) {
  const n = firstNumber(value)
  if (n == null) return '—'
  return report.formatNumber(n, 1)
}

function formatDiff(value) {
  if (value == null || value === '') return '—'
  return report.formatSignedNumber(value, 1)
}

function parseJsonLike(value) {
  if (value && typeof value === 'object') return value
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null
  try {
    return JSON.parse(trimmed)
  } catch {
    return null
  }
}

function normalizePlainText(value) {
  if (value == null) return ''
  if (typeof value === 'string') {
    const parsed = parseJsonLike(value)
    if (parsed && typeof parsed === 'object') {
      return firstPresent(parsed.issue, parsed.title, parsed.suggestion, parsed.dimension, '') || ''
    }
    return value
  }
  if (typeof value === 'object') {
    return firstPresent(value.issue, value.title, value.name, value.suggestion, value.text, value.dimension, '') || ''
  }
  return String(value)
}

function normalizeKey(value) {
  return String(value || '').replace(/\s+/g, '').toLowerCase()
}

function arrayFrom(value) {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null || value === '') return []
  return [value]
}

function objectFrom(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function firstPresent(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== '')
}

function firstNumber(...values) {
  for (const value of values) {
    if (value === undefined || value === null || value === '') continue
    const number = Number(value)
    if (Number.isFinite(number)) return number
  }
  return null
}
</script>

<style scoped>
.jury-page {
  --canvas: #f7f3ee;
  --line: rgba(40, 36, 32, 0.08);
  --line-strong: rgba(40, 36, 32, 0.12);
  --ink: #16181d;
  --ink-2: #2f333c;
  --muted: #6b7280;
  --faint: #9aa1ad;
  --orange: #e84a1c;
  --orange-deep: #c93d12;
  --orange-soft: #fde8de;
  --orange-wash: #fef6f2;
  --green: #0f9f6e;
  --figure: #2a2e36;
  --max: 1120px;
  --gutter: clamp(28px, 4vw, 48px);
  --font: "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", "Noto Sans SC",
    -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --num: "DIN Alternate", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;

  color: var(--ink);
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background:
    radial-gradient(ellipse 65% 36% at 50% 0%, rgba(232, 74, 28, 0.045), transparent 55%),
    linear-gradient(180deg, #faf7f3 0%, var(--canvas) 42%, #f3efe9 100%);
  font-family: var(--font);
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
}

.jury-page :deep(em),
.jury-page :deep(i) {
  font-style: normal;
}

.chrome {
  flex: 0 0 auto;
  border-bottom: 1px solid var(--line);
  background: rgba(251, 249, 246, 0.88);
  padding: 12px var(--gutter) 11px;
}

.chrome-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.chrome h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--orange-wash);
  border: 1px solid var(--orange-soft);
  font-family: var(--num);
  font-size: 12px;
  font-weight: 700;
  color: var(--orange-deep);
}

.pill span {
  font-family: var(--font);
  font-size: 11px;
  font-weight: 600;
  color: var(--orange);
}

.sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
}

.sub .sep { color: var(--faint); }
.sub a { color: var(--muted); text-decoration: none; }
.sub a:hover { color: var(--orange); }
.sub strong { color: var(--ink); font-weight: 700; }

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.work {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  max-width: var(--max);
  width: 100%;
  margin: 0 auto;
  padding: 18px var(--gutter) 16px;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.head {
  flex: 0 0 auto;
  width: 100%;
  margin: 0 0 14px;
  text-align: left;
}

.head .label {
  display: block;
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.1em;
}

.head h2 {
  display: block;
  margin: 0 0 6px;
  max-width: 18em;
  font-size: clamp(22px, 2.4vw, 28px);
  font-weight: 700;
  line-height: 1.28;
}

.head .lead {
  display: block;
  margin: 0;
  max-width: 40em;
  font-size: 14px;
  line-height: 1.65;
  color: var(--muted);
  font-weight: 500;
}

.head .lead strong {
  color: var(--ink);
  font-weight: 700;
}

.state-card {
  padding: 36px 28px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.55);
  text-align: center;
}

.state-card h3 {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 700;
}

.state-card p {
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.65;
  font-weight: 500;
}

/* 路演光场 */
.scene-band {
  flex: 0 0 auto;
  position: relative;
  width: 100%;
  height: 120px;
  margin-bottom: 12px;
  border-radius: 18px;
  overflow: hidden;
  background:
    radial-gradient(ellipse 70% 140% at 74% 42%, rgba(168, 196, 220, 0.22), transparent 58%),
    radial-gradient(ellipse 55% 120% at 20% 72%, rgba(232, 74, 28, 0.08), transparent 60%),
    radial-gradient(ellipse 50% 80% at 50% 0%, rgba(255, 255, 255, 0.55), transparent 65%),
    linear-gradient(185deg, #faf6f1 0%, #f0ebe4 100%);
}

.scene-band .orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(28px);
  pointer-events: none;
  z-index: 0;
}

.scene-band .orb.a {
  width: 160px; height: 160px; left: 8%; top: -40%;
  background: rgba(232, 74, 28, 0.12);
}
.scene-band .orb.b {
  width: 200px; height: 200px; right: 6%; top: -30%;
  background: rgba(150, 185, 215, 0.2);
}
.scene-band .orb.c {
  width: 120px; height: 80px; left: 40%; bottom: -30%;
  background: rgba(255, 220, 180, 0.22);
}

.proj {
  position: absolute;
  right: 7%; top: 14px; bottom: 18px;
  width: min(38%, 280px);
  border-radius: 14px;
  z-index: 1;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.55), rgba(230, 238, 246, 0.4));
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    0 8px 24px rgba(80, 100, 130, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  overflow: hidden;
}

.proj .lines {
  position: absolute; left: 18%; right: 22%; top: 28%;
  display: flex; flex-direction: column; gap: 7px;
}

.proj .lines i {
  display: block; height: 4px; border-radius: 2px;
  background: rgba(90, 130, 170, 0.18);
}
.proj .lines i:nth-child(1) { width: 72%; }
.proj .lines i:nth-child(2) { width: 48%; }
.proj .lines i:nth-child(3) { width: 60%; }

.proj .dot {
  position: absolute; right: 16%; top: 22%;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  opacity: 0.75;
  box-shadow: 0 0 8px rgba(15, 159, 110, 0.35);
}

.floor-glow {
  position: absolute;
  left: 8%; bottom: 10px;
  width: 42%; height: 28px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(255, 255, 255, 0.85), rgba(255, 200, 150, 0.15) 45%, transparent 70%);
  z-index: 1;
  pointer-events: none;
}

.scene-art {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
}

.sil-cast {
  position: absolute;
  left: 12%; bottom: 16px;
  display: flex;
  align-items: flex-end;
  gap: 5px;
  z-index: 2;
}

.sil-cast .p {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.sil-cast .p.lead {
  transform: translateY(-4px) scale(1.06);
  transform-origin: bottom center;
}

.sil-cam {
  position: absolute;
  right: 9%; bottom: 14px;
  z-index: 2;
  opacity: 0.9;
}

.score-over {
  position: absolute;
  left: 48%; top: 50%;
  transform: translate(-20%, -54%);
  z-index: 3;
  text-align: left;
  min-width: 118px;
  padding: 10px 16px 9px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.75);
  box-shadow:
    0 8px 28px rgba(40, 36, 32, 0.06),
    0 1px 0 rgba(255, 255, 255, 0.85) inset;
  backdrop-filter: blur(16px) saturate(1.1);
  -webkit-backdrop-filter: blur(16px) saturate(1.1);
}

.score-over .v {
  font-family: var(--num);
  font-size: 28px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.03em;
  line-height: 1;
}

.score-over .v small {
  font-size: 11px;
  font-weight: 600;
  color: var(--faint);
  margin-left: 2px;
}

.score-over .c {
  margin-top: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--orange-deep);
}

.metrics {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  margin-bottom: 14px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}

.metrics b {
  font-family: var(--num);
  font-weight: 700;
  color: var(--ink);
}

.metrics .up { color: var(--green); }
.metrics .down { color: var(--orange-deep); }
.metrics .sep { color: var(--faint); }

.gallery {
  flex: 0 0 auto;
  margin-bottom: 12px;
}

.gallery-cap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}

.gallery-cap strong {
  color: var(--ink-2);
  font-weight: 700;
  font-size: 13px;
}

.bench {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 8px 0;
}

.scored {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: clamp(12px, 1.8vw, 20px);
  flex-wrap: wrap;
}

.pending-group {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-left: 16px;
  padding-left: 16px;
  border-left: 1px solid var(--line);
}

.pending-stack {
  display: flex;
  align-items: flex-end;
}

.pending-stack .judge {
  width: 42px;
  margin-left: -10px;
}

.pending-stack .judge:first-child { margin-left: 0; }
.pending-stack .fig-wrap { width: 34px; height: 52px; }
.pending-stack .badge {
  min-width: 26px;
  height: 14px;
  font-size: 9px;
  bottom: 6px;
}

.pending-note {
  font-size: 11px;
  line-height: 1.4;
  color: var(--muted);
  font-weight: 500;
  padding-bottom: 4px;
  max-width: 5.5em;
}

.pending-note b {
  display: block;
  color: var(--ink);
  font-weight: 700;
  margin-bottom: 2px;
}

.pending-note button {
  color: var(--orange);
  font-weight: 700;
  font-size: 11px;
  text-decoration: underline;
  text-underline-offset: 2px;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
}

.pending-note button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.judge {
  width: 70px;
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  transition: transform 140ms ease;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
  color: inherit;
}

.judge:hover { transform: translateY(-2px); }
.judge.is-on { transform: translateY(-4px); }

.fig-wrap {
  position: relative;
  width: 48px;
  height: 64px;
}

.fig-wrap svg {
  display: block;
  width: 48px;
  height: 56px;
}

.fig-wrap .ring {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 40px;
  height: 8px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: rgba(23, 26, 36, 0.06);
}

.judge.is-on .fig-wrap .ring {
  background: rgba(232, 74, 28, 0.16);
  box-shadow: 0 0 0 1px rgba(232, 74, 28, 0.22);
}

.judge .fill { fill: var(--figure); }
.judge.is-on .fill { fill: var(--orange); }
.judge.trim-high .fill { fill: #c45a2a; }
.judge.trim-low .fill { fill: #7a808c; }
.judge.miss .fill { fill: #c5c8d0; }

.badge {
  position: absolute;
  left: 50%;
  bottom: 10px;
  transform: translateX(-50%);
  z-index: 3;
  min-width: 34px;
  height: 17px;
  padding: 0 5px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--line-strong);
  font-family: var(--num);
  font-size: 11px;
  font-weight: 700;
  display: grid;
  place-items: center;
}

.judge.is-on .badge {
  border-color: rgba(232, 74, 28, 0.4);
  color: var(--orange-deep);
  background: var(--orange-wash);
}

.lbl {
  margin-top: 6px;
  text-align: center;
  width: 100%;
}

.lbl .code {
  font-family: var(--num);
  font-size: 10px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.05em;
}

.judge.is-on .lbl .code { color: var(--orange); }

.lbl .name {
  margin-top: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lbl .tag {
  margin-top: 2px;
  font-size: 10px;
  font-weight: 700;
  min-height: 12px;
}

.lbl .tag.high { color: var(--orange-deep); }
.lbl .tag.low { color: var(--faint); }

/* Grok open sheet */
.sheet {
  flex: 0 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 4px;
  border-top: 1px solid var(--line-strong);
  background: transparent;
}

.sheet-top {
  flex-shrink: 0;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px 16px;
  padding: 14px 0 12px;
}

.sheet-id {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px 10px;
  min-width: 0;
}

.sheet-top .code {
  font-family: var(--num);
  font-size: 11px;
  font-weight: 700;
  color: var(--faint);
  letter-spacing: 0.06em;
  flex-shrink: 0;
}

.sheet-top h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.2;
  flex-shrink: 0;
  color: var(--ink);
}

.sheet-top .sub {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  display: inline;
}

.sheet-top .sub::before {
  content: "·";
  margin-right: 8px;
  color: var(--faint);
}

.sheet-score {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-shrink: 0;
  text-align: right;
}

.sheet-score .num {
  font-family: var(--num);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1;
  color: var(--ink);
}

.sheet-score .vs {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
}

.sheet-score .vs.up { color: var(--green); }
.sheet-score .vs.down { color: var(--orange-deep); }

.trim-inline {
  font-size: 11px;
  font-weight: 600;
  color: var(--orange-deep);
  white-space: nowrap;
  flex-shrink: 0;
  padding: 1px 0;
  border-bottom: 1px solid rgba(201, 61, 18, 0.25);
}

.trim-inline.low {
  color: var(--faint);
  border-bottom-color: rgba(154, 161, 173, 0.35);
}

.triptych {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.25fr 1fr 1fr;
  gap: 0;
}

.triptych > div {
  padding: 4px 20px 14px 0;
  min-height: 0;
}

.triptych > div + div {
  border-left: 1px solid var(--line);
  padding-left: 18px;
}

.triptych h4 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--faint);
}

.triptych p {
  margin: 0;
  font-size: 14px;
  line-height: 1.62;
  color: var(--ink-2);
  font-weight: 500;
}

.triptych .k p {
  font-weight: 600;
  color: var(--ink);
  font-size: 14.5px;
  line-height: 1.55;
}

.triptych p.quiet { color: var(--faint); }

.decide {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 0 2px;
  border-top: 1px solid var(--line);
  background: transparent;
}

.decide-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--faint);
  margin-bottom: 8px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.chip.is-hit { color: var(--ink); }

.chip.is-hit::before {
  content: "";
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--orange);
  flex-shrink: 0;
}

.chip em {
  font-style: normal;
  font-family: var(--num);
  font-size: 11px;
  font-weight: 700;
  color: var(--faint);
}

.chip.is-hit em { color: var(--orange-deep); }

.decide-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.link-quiet {
  font-size: 13px;
  font-weight: 600;
  color: var(--faint);
  text-decoration: none;
}

.link-quiet:hover { color: var(--muted); }

.empty-inline {
  margin: 0;
  font-size: 13px;
  color: var(--faint);
  font-weight: 500;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  padding: 0 13px;
  border: 0;
  border-radius: 999px;
  background: none;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  font-style: normal;
  font-synthesis: none;
  cursor: pointer;
  color: inherit;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-ghost { color: var(--muted); }
.btn-ghost:hover { background: rgba(0, 0, 0, 0.04); }

.btn-soft {
  background: transparent;
  border: 1px solid var(--line-strong);
  color: var(--ink-2);
}

.btn-primary {
  background: var(--orange);
  color: #fff;
}

.btn-primary:hover { background: var(--orange-deep); }

@media (max-width: 900px) {
  .scored { max-width: 100%; }
  .pending-group {
    margin-left: 0;
    padding-left: 0;
    border-left: 0;
    width: 100%;
    justify-content: center;
    margin-top: 8px;
  }
  .triptych { grid-template-columns: 1fr; }
  .triptych > div { padding: 10px 0 12px; }
  .triptych > div + div {
    border-left: 0;
    border-top: 1px solid var(--line);
    padding-left: 0;
    padding-top: 12px;
  }
  .scene-band { height: 100px; }
  .score-over {
    left: 50%;
    transform: translate(-50%, -54%);
  }
}

/* 与评分总结、整改待办、评分依据统一的报告页面骨架 */
.jury-page {
  --report-orange: #ff6a2a;
  --report-orange-deep: #d94b16;
  --report-orange-soft: #fff1e8;
  --report-ink: #1f2430;
  --report-muted: #6f7684;
  --report-faint: #9a9fa8;
  --report-line: #e8e3dc;
  --report-panel: #ffffff;
  --report-panel-soft: #fbfaf8;

  color: var(--report-ink);
  background: transparent;
}

.work {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 0 48px;
  box-sizing: border-box;
  overflow-x: hidden;
  overflow-y: auto;
  background: transparent;
}

.report-page-head {
  margin-bottom: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 32px;
}

.report-head-copy {
  min-width: 0;
  flex: 1;
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
  max-width: 320px;
  overflow: hidden;
  color: var(--report-faint);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-page-actions {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.report-overview {
  min-height: 104px;
  padding: 18px 24px;
  display: grid;
  grid-template-columns: minmax(260px, 1.15fr) minmax(260px, 0.95fr) auto;
  align-items: center;
  gap: 28px;
  border-top: 1px solid var(--report-line);
  border-bottom: 1px solid var(--report-line);
  background: rgba(255, 255, 255, 0.48);
}

.report-overview__identity p,
.report-overview__identity h2,
.report-overview__identity > span {
  margin: 0;
}

.report-overview__identity p {
  color: var(--report-orange);
  font-size: 10px;
  font-weight: 750;
}

.report-overview__identity h2 {
  margin: 3px 0 5px;
  display: flex;
  align-items: baseline;
  gap: 5px;
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 28px;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.report-overview__identity h2 small {
  color: var(--report-faint);
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

.report-overview__identity > span {
  display: block;
  max-width: 320px;
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
  min-width: 92px;
  padding: 6px 15px;
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

.head {
  width: 100%;
  margin: 26px 0 18px;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 18px;
  text-align: left;
}

.head .label {
  margin: 4px 0 0;
  color: var(--report-orange);
  font: 750 12px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.08em;
}

.head h2 {
  max-width: none;
  margin: 0;
  color: var(--report-ink);
  font-size: 20px;
  line-height: 1.35;
}

.head .lead {
  max-width: none;
  margin-top: 6px;
  color: var(--report-muted);
  font-size: 12px;
  line-height: 1.65;
}

.state-card {
  min-height: 210px;
  padding: 36px 28px;
  display: grid;
  align-content: center;
  justify-items: center;
  border: 1px solid var(--report-line);
  border-radius: 16px;
  background: var(--report-panel);
  box-shadow: 0 14px 32px rgba(38, 31, 27, 0.05);
}

.state-card p:last-child {
  margin-bottom: 0;
}

.scene-band,
.sheet {
  border: 1px solid var(--report-line);
  box-shadow: 0 14px 32px rgba(38, 31, 27, 0.05);
}

.scene-band {
  border-radius: 16px;
}

.gallery,
.sheet {
  background: var(--report-panel);
}

.sheet {
  padding: 22px 24px;
  border-radius: 16px;
}

@media (max-width: 1080px) {
  .report-overview {
    grid-template-columns: minmax(240px, 1fr) minmax(240px, 0.9fr);
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
}

@media (max-width: 760px) {
  .report-page-head {
    align-items: stretch;
    flex-direction: column;
  }

  .report-page-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .report-session {
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

  .head {
    grid-template-columns: 44px minmax(0, 1fr);
    gap: 12px;
  }
}

.jury-workspace {
  display: grid;
  grid-template-columns: minmax(300px, 0.86fr) minmax(0, 1.44fr);
  align-items: start;
  gap: 16px;
}

.jury-conclusion {
  margin-bottom: 16px;
  padding: 20px 22px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 24px;
  border: 1px solid #f0c5b3;
  border-radius: 16px;
  background: #fff8f4;
  box-shadow: inset 4px 0 var(--report-orange);
}

.jury-conclusion__copy span,
.jury-conclusion__copy h3,
.jury-conclusion__copy p {
  margin: 0;
}

.jury-conclusion__copy > span {
  color: var(--report-orange-deep);
  font-size: 10px;
  font-weight: 750;
}

.jury-conclusion__copy h3 {
  margin-top: 5px;
  color: var(--report-ink);
  font-size: 18px;
  line-height: 1.35;
}

.jury-conclusion__copy p {
  margin-top: 7px;
  color: var(--report-muted);
  font-size: 11px;
  line-height: 1.65;
}

.jury-conclusion__numbers {
  display: grid;
  grid-template-columns: repeat(3, minmax(88px, auto));
}

.jury-conclusion__numbers div {
  min-width: 96px;
  padding: 4px 16px;
  border-left: 1px solid #edd8cf;
  text-align: center;
}

.jury-conclusion__numbers span,
.jury-conclusion__numbers strong {
  display: block;
}

.jury-conclusion__numbers span {
  color: var(--report-muted);
  font-size: 10px;
}

.jury-conclusion__numbers strong {
  margin-top: 6px;
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 20px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.jury-conclusion__numbers strong.is-lower {
  color: var(--report-orange-deep);
}

.jury-conclusion__numbers strong.is-higher {
  color: #158260;
}

.jury-roster {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--report-line);
  border-radius: 16px;
  background: var(--report-panel);
  box-shadow: 0 14px 32px rgba(38, 31, 27, 0.05);
}

.jury-roster__head {
  padding: 18px 18px 14px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--report-line);
}

.jury-roster__head span,
.jury-roster__head h3,
.jury-roster__head small {
  margin: 0;
}

.jury-roster__head span {
  color: var(--report-orange);
  font-size: 10px;
  font-weight: 750;
}

.jury-roster__head h3 {
  margin-top: 4px;
  color: var(--report-ink);
  font-size: 16px;
  line-height: 1.3;
}

.jury-roster__head small {
  color: var(--report-faint);
  font-size: 10px;
  white-space: nowrap;
}

.jury-groups {
  padding: 0 12px 12px;
}

.jury-group {
  padding-top: 12px;
}

.jury-group + .jury-group {
  margin-top: 4px;
  border-top: 1px solid var(--report-line);
}

.jury-group > header {
  padding: 0 2px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.jury-group > header strong {
  color: #39715a;
  font-size: 11px;
}

.jury-group > header span {
  color: var(--report-faint);
  font-size: 9px;
}

.jury-group.is-trimmed > header strong {
  color: var(--report-orange-deep);
}

.judge-grid {
  padding: 8px 0 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.judge-card {
  min-width: 0;
  min-height: 116px;
  padding: 13px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  border: 1px solid var(--report-line);
  border-radius: 12px;
  color: var(--report-ink);
  background: #fff;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}

.judge-card:hover {
  border-color: #e5b7a3;
  background: #fffaf7;
}

.judge-card:focus-visible {
  outline: 2px solid rgba(255, 106, 42, 0.38);
  outline-offset: 2px;
}

.judge-card.is-selected {
  border-color: #f0a485;
  background: var(--report-orange-soft);
  box-shadow: inset 3px 0 var(--report-orange);
}

.judge-card.is-pending {
  opacity: 0.72;
}

.judge-card__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.judge-card__top em {
  color: var(--report-faint);
  font: 750 10px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.04em;
}

.judge-card__top b {
  color: var(--report-ink);
  font-family: var(--num);
  font-size: 18px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.judge-card.is-selected .judge-card__top em,
.judge-card.is-selected .judge-card__top b {
  color: var(--report-orange-deep);
}

.judge-card > strong {
  overflow: hidden;
  margin-top: 7px;
  color: var(--report-ink);
  font-size: 12px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.judge-card > small {
  min-height: 30px;
  overflow: hidden;
  margin-top: 4px;
  color: var(--report-muted);
  display: -webkit-box;
  font-size: 10px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.judge-card__status {
  align-self: flex-start;
  margin-top: auto;
  padding-top: 8px;
  color: #4f765f;
  font-size: 9px;
  font-weight: 700;
}

.judge-card.is-trimmed .judge-card__status {
  color: #bd4b1d;
}

.jury-group.is-trimmed .judge-card {
  border-style: dashed;
  background: #fcfaf8;
}

.jury-workspace .sheet {
  min-width: 0;
  margin: 0;
  padding: 22px 24px;
  align-self: start;
  border-top: 1px solid var(--report-line);
  background: var(--report-panel);
}

.jury-workspace .sheet-top {
  align-items: flex-start;
  padding: 0 0 18px;
}

.jury-workspace .sheet-top h3 {
  font-size: 20px;
}

.jury-workspace .sheet-top .sub {
  white-space: normal;
}

.jury-workspace .triptych {
  display: grid;
  grid-template-columns: 1fr;
}

.jury-workspace .triptych > div {
  min-height: 0;
  padding: 16px 0;
}

.jury-workspace .triptych > div + div {
  padding: 16px 0;
  border-top: 1px solid var(--report-line);
  border-left: 0;
}

.jury-workspace .triptych h4 {
  margin-bottom: 7px;
  color: var(--report-faint);
  font-size: 10px;
}

.jury-workspace .triptych p,
.jury-workspace .triptych .k p {
  color: var(--report-ink-2, #343a49);
  font-size: 12px;
  line-height: 1.7;
}

.jury-workspace .decide {
  padding-top: 16px;
  border-top: 1px solid var(--report-line);
}

.jury-workspace .decide-actions {
  margin-left: auto;
}

@media (max-width: 900px) {
  .jury-conclusion {
    grid-template-columns: 1fr;
  }

  .jury-conclusion__numbers div:first-child {
    border-left: 0;
  }

  .jury-workspace {
    grid-template-columns: 1fr;
  }

  .judge-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .jury-conclusion {
    padding: 18px;
  }

  .jury-conclusion__numbers {
    grid-template-columns: 1fr;
  }

  .jury-conclusion__numbers div {
    padding: 10px 0;
    border-top: 1px solid #edd8cf;
    border-left: 0;
    text-align: left;
  }

  .judge-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .jury-roster__head {
    align-items: flex-start;
    flex-direction: column;
  }

  .jury-workspace .sheet-top {
    align-items: flex-start;
    flex-direction: column;
  }

  .jury-workspace .sheet-score {
    text-align: left;
  }
}
</style>
