<template>
  <AiScoreReportShell title="依据" mode="editorial">
    <div class="why-page coach-report-page is-scrollable">
      <div class="why-scroll coach-report-scroll">
        <div class="report-standard">
          <AiScoreReportCoachChrome
            active="why"
            title="评分依据"
            :description="whyLead"
            :score-display="scoreDisplay"
            :todo-count="todoCount || 0"
            @sync="onChromeSync"
          />

          <main class="review-workspace">
            <section class="review-stage report-task-card" aria-label="路演视频复盘台" data-testid="review-stage">
              <header class="task-card-head">
                <span class="task-card-number">R01</span>
                <div>
                  <h2>录像与事件时间轴</h2>
                  <p>点击事件或章节，快速回到评分发生的现场。</p>
                </div>
                <span>{{ minutes.timelineEvents.length }} 个事件已定位</span>
              </header>

              <div class="stage-body">
                <div class="video-card">
                  <header class="stage-head">
                    <div>
                      <span class="eyebrow">路演现场</span>
                      <strong>{{ activeChapter?.title || '整场回放' }}</strong>
                    </div>
                    <div class="stage-meta">
                      <span class="live-dot" />
                      {{ formatReviewTime(currentTime) }} / {{ formatReviewTime(totalDuration) }}
                    </div>
                  </header>

                  <div v-if="minutes.media.available" class="video-viewport">
                    <video
                      ref="videoRef"
                      class="roadshow-video"
                      data-testid="roadshow-video"
                      :src="authenticatedStreamUrl"
                      controls
                      playsinline
                      preload="metadata"
                      @loadedmetadata="onLoadedMetadata"
                      @timeupdate="onTimeUpdate"
                      @seeking="onTimeUpdate"
                      @error="onVideoError"
                    />
                    <div v-if="activeChapter" class="chapter-overlay">
                      <span>当前章节</span>
                      <b>{{ activeChapter.title }}</b>
                    </div>
                  </div>

                  <div v-else class="video-empty">
                    <div class="empty-icon">▶</div>
                    <strong>当前报告未关联可播放视频</strong>
                    <span>评分事实仍可查看；系统不会用静态图片冒充完整回放。</span>
                  </div>

                  <div v-if="videoError" class="video-error" role="alert">
                    <span>{{ videoError }}</span>
                    <button type="button" @click="reloadVideo">重新加载</button>
                  </div>
                </div>

                <section class="timeline-card" aria-label="路演事件时间轴" data-testid="timeline-card">
                  <div class="timeline-title-row">
                    <div>
                      <span class="eyebrow">事件时间轴</span>
                      <b>{{ minutes.timelineEvents.length }} 个已定位评分事件</b>
                    </div>
                    <span>点击节点跳转视频</span>
                  </div>

                  <div class="chapter-rail" aria-label="路演章节">
                    <button
                      v-for="chapter in timelineChapters"
                      :key="chapter.id"
                      type="button"
                      class="chapter-segment"
                      :class="{ active: chapter.id === activeChapter?.id }"
                      :style="chapterStyle(chapter)"
                      :title="`${chapter.title} ${chapter.timeLabel}`"
                      @click="seekTo(chapter.startSeconds)"
                    >
                      <span>{{ chapter.title }}</span>
                    </button>
                  </div>

                  <div
                    class="event-track"
                    role="slider"
                    tabindex="0"
                    :aria-valuemin="0"
                    :aria-valuemax="Math.round(totalDuration)"
                    :aria-valuenow="Math.round(currentTime)"
                    aria-label="视频时间轴"
                    @click="seekFromTrack"
                    @keydown.left.prevent="seekTo(currentTime - 5)"
                    @keydown.right.prevent="seekTo(currentTime + 5)"
                  >
                    <div class="track-fill" :style="{ width: `${progressPercent}%` }" />
                    <button
                      v-for="event in minutes.timelineEvents"
                      :key="event.id"
                      type="button"
                      class="event-marker"
                      data-testid="timeline-event"
                      :class="{ active: event.id === currentScoreEvent?.id }"
                      :style="markerStyle(event)"
                      :aria-label="`${event.timeLabel}，${event.title}，扣 ${formatPoints(event.points)} 分`"
                      @click.stop="selectEvent(event)"
                    >
                      <span />
                    </button>
                    <span class="playhead" :style="{ left: `${progressPercent}%` }" />
                  </div>

                  <div class="timeline-footer">
                    <span>00:00</span>
                    <article v-if="currentScoreEvent" class="current-event">
                      <div class="event-time">{{ currentScoreEvent.timeLabel }}</div>
                      <div class="event-copy">
                        <b>{{ currentScoreEvent.title }}</b>
                        <span>{{ currentScoreEvent.dimensionName || '评分规则' }}</span>
                      </div>
                      <strong v-if="currentScoreEvent.points != null">−{{ formatPoints(currentScoreEvent.points) }}</strong>
                    </article>
                    <span>{{ formatReviewTime(totalDuration) }}</span>
                  </div>
                </section>
              </div>
            </section>

            <aside class="review-panel report-task-card" aria-label="评分纪要" data-testid="review-panel">
              <header class="task-card-head">
                <span class="task-card-number">R02</span>
                <div>
                  <h2>逐段核验评分依据</h2>
                  <p>在评分事件、人物转写和路演章节之间切换核验。</p>
                </div>
                <span class="truth-badge">只读真实分析字段</span>
              </header>

              <nav class="panel-tabs" aria-label="依据类型">
                <button
                  v-for="tab in panelTabs"
                  :key="tab.key"
                  type="button"
                  :class="{ active: activeTab === tab.key }"
                  @click="activeTab = tab.key"
                >
                  {{ tab.label }}
                  <span>{{ tab.count }}</span>
                </button>
              </nav>

              <div v-if="activeTab === 'transcript'" class="panel-tools">
                <label>
                  <span aria-hidden="true">⌕</span>
                  <input v-model="transcriptQuery" type="search" placeholder="搜索发言内容" aria-label="搜索发言内容">
                </label>
                <span v-if="minutes.isStableFinal" class="speaker-state final">
                  已确认 {{ minutes.stablePeople.length }} 位稳定人物
                </span>
                <span v-else-if="unresolvedSegmentCount" class="speaker-state">
                  {{ unresolvedSegmentCount }} 段身份证据不足
                </span>
                <button
                  v-if="canRecomputeSpeakerAttribution"
                  type="button"
                  class="recompute-attribution-btn"
                  data-testid="recompute-speaker-attribution"
                  :disabled="recomputingSpeakerAttribution"
                  @click="onRecomputeSpeakerAttribution"
                >
                  {{ recomputingSpeakerAttribution ? '重算中…' : '重算人物归属' }}
                </button>
              </div>

              <div ref="panelScrollRef" class="panel-scroll" data-testid="panel-scroll">
                <section v-if="activeTab === 'events'" class="event-list">
                  <div class="score-accounting">
                    <span>完整失分账本</span>
                    <b>{{ minutes.scoreEvents.length }} 项 · 合计 −{{ formatPoints(totalLoss) }} 分</b>
                  </div>
                  <button
                    v-for="event in minutes.scoreEvents"
                    :key="event.id"
                    type="button"
                    class="event-row"
                    data-testid="score-event"
                    :class="{
                      active: event.id === currentScoreEvent?.id,
                      estimated: event.timeEstimated,
                      unlocated: event.timeSeconds == null
                    }"
                    @click="selectEvent(event)"
                  >
                    <span class="row-time" :title="event.timeEstimated ? '根据内容与片长估算的相对时间，可跳转回看' : '证据锚点时间'">
                      {{ event.timeLabel }}
                    </span>
                    <span class="row-body">
                      <span class="row-kicker">{{ event.dimensionName || lossTypeLabel(event.lossType) }}</span>
                      <b>{{ event.title }}</b>
                      <small v-if="event.evidenceText">证据：{{ event.evidenceText }}</small>
                      <small v-else-if="event.acceptanceCriteria">验收：{{ event.acceptanceCriteria }}</small>
                    </span>
                    <strong v-if="event.points != null">−{{ formatPoints(event.points) }}</strong>
                  </button>
                  <div v-if="!minutes.scoreEvents.length" class="panel-empty">暂无结构化评分事件</div>
                </section>

                <section v-else-if="activeTab === 'transcript'" class="transcript-list">
                  <div
                    v-for="segment in filteredTranscript"
                    :key="segment.id"
                    class="transcript-row"
                    :class="{ active: segment.id === activeTranscript?.id }"
                    role="button"
                    tabindex="0"
                    @click="seekTo(segment.startSeconds)"
                    @keydown.enter.prevent="seekTo(segment.startSeconds)"
                  >
                    <span class="speaker-avatar">{{ speakerInitial(segment.speakerName) }}</span>
                    <span class="row-body">
                      <span class="speaker-line">
                        <b>{{ segment.speakerName }}</b>
                        <small v-if="segment.typeLabel">{{ segment.typeLabel }}</small>
                        <time>{{ segment.timeLabel }}</time>
                      </span>
                      <span class="transcript-text">{{ segment.text }}</span>
                    </span>
                  </div>
                  <div v-if="!filteredTranscript.length" class="panel-empty">
                    {{ transcriptQuery ? '没有匹配的发言内容' : '尚无可用转写' }}
                  </div>
                </section>

                <section v-else class="chapter-list">
                  <button
                    v-for="chapter in minutes.chapters"
                    :key="chapter.id"
                    type="button"
                    class="chapter-row"
                    :class="{ active: chapter.id === activeChapter?.id }"
                    @click="seekTo(chapter.startSeconds)"
                  >
                    <span class="chapter-index">{{ String(minutes.chapters.indexOf(chapter) + 1).padStart(2, '0') }}</span>
                    <span class="row-body">
                      <span class="speaker-line">
                        <b>{{ chapter.title }}</b>
                        <time>{{ chapter.timeLabel }}</time>
                      </span>
                      <span>{{ chapter.summary || '本章节暂无结构摘要' }}</span>
                      <small v-if="chapter.gap">诊断：{{ chapter.gap }}</small>
                    </span>
                  </button>
                  <div v-if="!minutes.chapters.length" class="panel-empty">尚无真实路演章节分析</div>
                </section>
              </div>
            </aside>
          </main>

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
import { computed, nextTick, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreReportCoachChrome from '../../components/ai-score/report/AiScoreReportCoachChrome.vue'
import AiScoreTeamSyncDialog from '../../components/ai-score/report/AiScoreTeamSyncDialog.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'
import { getUserToken } from '../../utils/authStorage'
import {
  buildMinutesPresentation,
  formatReviewTime,
  resolveActiveReviewState
} from '../../utils/aiScoreMinutesPresentation'

const report = useAiScoreReportContext()
const route = useRoute()
const videoRef = ref(null)
const panelScrollRef = ref(null)
const activeTab = ref('events')
const transcriptQuery = ref('')
const currentTime = ref(0)
const metadataDuration = ref(0)
const selectedEventId = ref('')
const videoError = ref('')
const syncOpen = ref(false)
const syncItems = ref([])
const syncPreselectedIds = ref([])

const minutes = computed(() => buildMinutesPresentation({
  sessionId: report.effectiveSessionId?.value,
  mediaPlayback: report.mediaPlayback?.value,
  asrSegments: report.asrSegments?.value,
  speakerMappings: report.speakerMappings?.value,
  speakerAttributionStatus: report.speakerAttributionStatus?.value,
  stablePeople: report.stablePeople?.value,
  finalSpeakerSegments: report.finalSpeakerSegments?.value,
  pitchChapters: report.pitchChapters?.value,
  observations: report.structuredObservations?.value,
  deductions: report.currentStructuredDeductions?.value || report.structuredDeductions?.value,
  lossLedger: report.lossLedger?.value,
  evidenceAnchors: report.structuredEvidenceAnchors?.value,
  diagnosticIssues: report.issues?.value
}))

const authenticatedStreamUrl = computed(() => {
  const raw = minutes.value.media.streamUrl
  if (!raw) return ''
  const token = getUserToken()
  if (!token) return raw
  try {
    const url = new URL(raw, window.location.origin)
    url.searchParams.set('t', token)
    return `${url.pathname}${url.search}`
  } catch {
    return raw
  }
})

const totalDuration = computed(() => metadataDuration.value || minutes.value.durationSeconds || 0)
const activeState = computed(() => resolveActiveReviewState(minutes.value, currentTime.value))
const activeChapter = computed(() => activeState.value.chapter)
const activeTranscript = computed(() => activeState.value.transcript)
const currentScoreEvent = computed(() => {
  return minutes.value.scoreEvents.find(item => item.id === selectedEventId.value) || activeState.value.scoreEvent || minutes.value.timelineEvents[0] || null
})
const progressPercent = computed(() => totalDuration.value > 0 ? clamp(currentTime.value / totalDuration.value * 100, 0, 100) : 0)
const totalLoss = computed(() => minutes.value.scoreEvents.reduce((sum, item) => sum + (Number(item.points) || 0), 0))
const locatedEventPercent = computed(() => {
  if (!minutes.value.scoreEvents.length) return 0
  return clamp(minutes.value.timelineEvents.length / minutes.value.scoreEvents.length * 100, 0, 100)
})
const todoCount = computed(() => {
  const fromNav = (report.navItems?.value || []).find(item => item.key === 'todos')
  if (fromNav?.count !== undefined && fromNav?.count !== null && fromNav.count !== '') return fromNav.count
  return report.reportWorkItemDrafts?.value?.length || report.trainingTasks?.value?.length || 0
})
const scoreDisplay = computed(() => {
  const value = Number(report.overallScore?.value)
  return Number.isFinite(value) ? value.toFixed(1) : '—'
})
const sessionTitle = computed(() => {
  const result = report.result?.value || {}
  const session = firstPresent(
    result.session_no,
    result.sessionNo,
    report.sessionId?.value,
    report.effectiveSessionId?.value
  )
  return session ? `场次 ${session}` : '本次路演'
})
const sessionSubtitle = computed(() => {
  const result = report.result?.value || {}
  const parts = [
    firstPresent(report.reportTrackName?.value, result.track_name, result.trackName),
    firstPresent(result.project_name, result.projectName, result.project?.name)
  ].filter(Boolean)
  const completed = firstPresent(result.completed_at, result.completedAt)
  if (completed) {
    const date = new Date(completed)
    if (!Number.isNaN(date.getTime())) {
      parts.push(`${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`)
    }
  }
  return parts.join(' · ')
})
const whyLead = computed(() => {
  const events = minutes.value.scoreEvents?.length || 0
  const precise = (minutes.value.scoreEvents || []).filter(item => item.timeSeconds != null && !item.timeEstimated).length
  const estimated = (minutes.value.scoreEvents || []).filter(item => item.timeEstimated).length
  if (!events) return '暂无结构化评分事件。有录像时可先通看全片，再对照结果与待办。'
  if (estimated) {
    return `共 ${events} 项评分事件，均可跳转录像（${precise} 项精确锚点，${estimated} 项为相对时间）。点事件回看现场。`
  }
  return `共 ${events} 项评分事件，均可跳转到录像。点事件回看现场，核对结果与待办。`
})
const timelineChapters = computed(() => minutes.value.chapters.filter(chapter => {
  if (!totalDuration.value) return true
  return (chapter.endSeconds - chapter.startSeconds) < totalDuration.value * 0.82
}))
const filteredTranscript = computed(() => {
  const query = transcriptQuery.value.trim().toLowerCase()
  if (!query) return minutes.value.transcript
  return minutes.value.transcript.filter(item => `${item.speakerName} ${item.typeLabel || ''} ${item.text}`.toLowerCase().includes(query))
})
const unresolvedSegmentCount = computed(() => minutes.value.transcript.filter(item =>
  ['UNKNOWN', 'OVERLAP'].includes(String(item.speakerState || '').toUpperCase())
).length)
const canRecomputeSpeakerAttribution = computed(() => Boolean(
  report.effectiveSessionId?.value
  && (
    minutes.value.transcript.length > 0
    || (report.asrSegments?.value || []).length > 0
  )
))
const recomputingSpeakerAttribution = computed(() => Boolean(
  report.recomputingSpeakerAttribution?.value
))
const panelTabs = computed(() => [
  { key: 'events', label: '评分事件', count: minutes.value.scoreEvents.length },
  { key: 'transcript', label: '人物转写', count: minutes.value.transcript.length },
  { key: 'chapters', label: '路演章节', count: minutes.value.chapters.length }
])

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function onLoadedMetadata(event) {
  metadataDuration.value = Number(event.target?.duration) || 0
  videoError.value = ''
  seekFromQuery()
}

function seekFromQuery() {
  const raw = route.query.t
  const seconds = Number(Array.isArray(raw) ? raw[0] : raw)
  if (Number.isFinite(seconds) && seconds >= 0) {
    seekTo(seconds, { play: false })
  }
}

function onTimeUpdate(event) {
  currentTime.value = Number(event.target?.currentTime) || 0
  if (selectedEventId.value) {
    const selected = minutes.value.scoreEvents.find(item => item.id === selectedEventId.value)
    if (selected?.timeSeconds != null && Math.abs(currentTime.value - selected.timeSeconds) > 20) selectedEventId.value = ''
  }
}

function onVideoError() {
  videoError.value = '视频加载失败，请检查登录状态或稍后重试。'
}

function reloadVideo() {
  videoError.value = ''
  const video = videoRef.value
  if (!video) return
  video.load()
}

function seekTo(seconds, { play = true } = {}) {
  const target = clamp(Number(seconds) || 0, 0, totalDuration.value || Number.MAX_SAFE_INTEGER)
  currentTime.value = target
  const video = videoRef.value
  if (!video) return
  try {
    video.currentTime = target
  } catch {
    // Some browsers throw if metadata is not ready yet; timeupdate will catch up.
  }
  if (play) {
    const playPromise = video.play?.()
    if (playPromise?.catch) playPromise.catch(() => {})
  }
}

function seekFromTrack(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  if (!rect.width || !totalDuration.value) return
  seekTo((event.clientX - rect.left) / rect.width * totalDuration.value)
}

function selectEvent(event) {
  selectedEventId.value = event.id
  if (event.timeSeconds != null) {
    seekTo(event.timeSeconds)
    if (event.timeEstimated) {
      ElMessage.info('该事件无精确帧锚点，已跳到相对合适时间，便于对照回看')
    }
    return
  }
  ElMessage.info('这项失分暂无可用视频时间')
}

function markerStyle(event) {
  return { left: `${positionPercent(event.timeSeconds)}%` }
}

function chapterStyle(chapter) {
  const start = positionPercent(chapter.startSeconds)
  const end = positionPercent(chapter.endSeconds)
  return { left: `${start}%`, width: `${Math.max(2.2, end - start)}%` }
}

function positionPercent(seconds) {
  return totalDuration.value > 0 ? clamp(Number(seconds) / totalDuration.value * 100, 0, 100) : 0
}

function formatPoints(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(1) : '—'
}

function lossTypeLabel(value) {
  return ({
    performance_gap: '表现差距',
    evidence_limited: '证据限制',
    hard_violation: '明确惩罚'
  })[value] || '评分规则'
}

function speakerInitial(value) {
  const text = String(value || '发').trim()
  if (!text) return '发'
  // 1号选手 → 「1」；未识别/外部/待确认 → 单字
  const slot = text.match(/^(\d+)\s*号/)
  if (slot) return slot[1]
  if (/未识别|待确认|外部|画外|多人/.test(text)) return text.slice(0, 1)
  return text.slice(0, 1)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function onChromeSync() {
  const drafts = report.reportWorkItemDrafts?.value || []
  if (!drafts.length) {
    ElMessage.warning('暂无可同步到团队任务的正式整改项')
    return
  }
  syncItems.value = drafts.map(item => ({
    id: String(item.id),
    title: String(item.title || item.id),
    recoverDisplay: item.recoverDisplay || ''
  }))
  syncPreselectedIds.value = syncItems.value.slice(0, 3).map(item => item.id)
  syncOpen.value = true
  nextTick(() => panelScrollRef.value?.scrollTo?.({ top: 0 }))
}

async function onRecomputeSpeakerAttribution() {
  if (!report.recomputeSpeakerAttribution) {
    ElMessage.warning('当前报告不支持重算人物归属')
    return
  }
  try {
    await report.recomputeSpeakerAttribution()
    activeTab.value = 'transcript'
  } catch {
    // Error toast is already shown by the report composable.
  }
}
</script>

<style scoped>
.why-page {
  --ink: #1f2430;
  --muted: #6f7684;
  --faint: #9a9fa8;
  --line: #e8e3dc;
  --orange: #ff6a2a;
  --orange-dark: #d94b16;
  --orange-soft: #fff1e8;
  --green: #238b62;
  --panel-soft: #fbfaf8;
  box-sizing: border-box;
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--ink);
  background: transparent;
}

.why-scroll {
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
  scrollbar-gutter: stable;
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
  color: var(--ink);
  font-size: 28px;
  font-weight: 760;
  line-height: 1.2;
  letter-spacing: -0.035em;
}

.report-page-head p {
  margin-top: 8px;
  color: var(--muted);
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
  color: var(--muted);
  font-size: 12px;
}

.report-session strong {
  color: var(--ink);
  font-size: 12px;
}

.report-session small {
  max-width: 260px;
  overflow: hidden;
  color: var(--faint);
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
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.48);
}

.report-overview__identity p,
.report-overview__identity h2,
.report-overview__identity > span {
  margin: 0;
}

.report-overview__identity p {
  color: var(--orange);
  font-size: 10px;
  font-weight: 750;
}

.report-overview__identity h2 {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 4px 0 5px;
  color: var(--ink);
  font: 800 28px/1.1 ui-monospace, SFMono-Regular, Menlo, monospace;
  font-variant-numeric: tabular-nums;
}

.report-overview__identity h2 small {
  color: var(--faint);
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
}

.report-overview__identity > span {
  display: block;
  color: var(--muted);
  font-size: 11px;
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
  color: var(--ink);
  font-size: 12px;
}

.report-overview__progress strong em {
  margin-left: 5px;
  color: var(--orange);
  font-style: normal;
}

.report-overview__progress span {
  margin-top: 4px;
  overflow: hidden;
  color: var(--muted);
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
  background: var(--orange);
}

.report-overview__metrics {
  align-self: stretch;
  display: flex;
  align-items: center;
}

.report-overview__metrics div {
  min-width: 94px;
  padding: 6px 16px;
  border-left: 1px solid var(--line);
  text-align: center;
}

.report-overview__metrics strong,
.report-overview__metrics span {
  display: block;
}

.report-overview__metrics strong {
  color: var(--ink);
  font: 800 19px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
}

.report-overview__metrics span {
  margin-top: 5px;
  color: var(--muted);
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
  color: var(--ink);
  font-size: 20px;
}

.report-toolbar p {
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
}

.report-tabs {
  padding: 4px;
  display: flex;
  gap: 2px;
  border: 1px solid var(--line);
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
  color: var(--faint);
  font-size: 10px;
}

.report-tabs a.is-active {
  color: var(--ink);
  background: #fff;
  box-shadow: 0 3px 10px rgba(45, 36, 29, 0.08);
}

.review-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.48fr) minmax(350px, 0.82fr);
  align-items: start;
  gap: 18px;
}

.review-stage,
.review-panel {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(38, 32, 27, 0.04);
}

.review-stage {
  height: clamp(720px, calc(100vh - 210px), 900px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}

.task-card-head {
  min-height: 84px;
  padding: 18px 24px;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  border-bottom: 1px solid var(--line);
  background: var(--panel-soft);
}

.task-card-head h2,
.task-card-head p {
  margin: 0;
}

.task-card-head h2 {
  color: var(--ink);
  font-size: 16px;
}

.task-card-head p {
  margin-top: 5px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}

.task-card-head > span:last-child {
  color: var(--faint);
  font-size: 10px;
}

.task-card-number {
  color: var(--orange);
  font: 800 13px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
}

.stage-body {
  min-height: 0;
  padding: 18px;
  display: grid;
  grid-template-rows: minmax(390px, 1fr) auto;
  gap: 12px;
}

.video-card {
  position: relative;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border-radius: 14px;
  background: #111318;
}

.stage-head {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 7px 12px;
  color: #f8fafc;
  border-bottom: 1px solid rgba(255,255,255,.08);
}

.stage-head > div:first-child { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.stage-head strong { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.eyebrow { color: var(--orange); font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.stage-meta { display: flex; align-items: center; gap: 7px; flex: 0 0 auto; color: #b8c0cc; font: 600 12px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: #ff6a3d; box-shadow: 0 0 0 4px rgba(255,106,61,.12); }

.video-viewport { position: relative; min-height: 0; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #090a0d; }
.roadshow-video { width: 100%; height: 100%; max-width: 100%; max-height: 100%; object-fit: contain; background: #090a0d; }
.chapter-overlay { position: absolute; top: 12px; left: 12px; display: flex; gap: 8px; align-items: center; padding: 7px 10px; border: 1px solid rgba(255,255,255,.16); border-radius: 9px; color: #fff; background: rgba(13,15,20,.72); backdrop-filter: blur(10px); pointer-events: none; }
.chapter-overlay span { color: #abb4c2; font-size: 10px; }
.chapter-overlay b { font-size: 12px; }
.video-empty { min-height: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #d4d8df; text-align: center; }
.video-empty span { max-width: 380px; color: #8e97a5; font-size: 12px; }
.empty-icon { display: grid; place-items: center; width: 46px; height: 46px; padding-left: 3px; border: 1px solid #3b414c; border-radius: 50%; color: #ff7a50; }
.video-error { position: absolute; inset: auto 12px 12px; display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 9px 11px; border: 1px solid rgba(255,122,80,.35); border-radius: 10px; color: #ffd8ca; background: rgba(55,20,10,.9); font-size: 12px; }
.video-error button { border: 0; color: #fff; background: transparent; font-weight: 700; cursor: pointer; }

.timeline-card { flex: 0 0 auto; padding: clamp(10px, 1.2vh, 14px) 14px 12px; border: 1px solid var(--line); border-radius: 14px; background: #fff; }
.timeline-title-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.timeline-title-row > div { display: flex; align-items: baseline; gap: 10px; }
.timeline-title-row b { font-size: 13px; }
.timeline-title-row > span { color: var(--faint); font-size: 10px; }
.chapter-rail { position: relative; height: clamp(26px, 3.2vh, 34px); margin: 0 2px 8px; overflow: hidden; border-radius: 7px; background: #f4f1ed; }
.chapter-segment { position: absolute; inset-block: 0; min-width: 2px; padding: 0 5px; overflow: hidden; border: 0; border-right: 1px solid #fff; color: #7b6f66; background: #ebe4de; font-size: 9px; white-space: nowrap; text-overflow: ellipsis; cursor: pointer; }
.chapter-segment:nth-child(2n) { background: #f3e7df; }
.chapter-segment.active { z-index: 2; color: #fff; background: var(--orange); }
.event-track { position: relative; height: 16px; margin: 0 7px; border-radius: 999px; background: #e8e3dd; cursor: pointer; outline-offset: 4px; }
.track-fill { position: absolute; inset: 0 auto 0 0; border-radius: inherit; background: linear-gradient(90deg, #ef4b1b, #ff875f); pointer-events: none; }
.playhead { position: absolute; top: 50%; width: 2px; height: 24px; transform: translate(-1px,-50%); background: #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.18); pointer-events: none; }
.event-marker { position: absolute; top: 50%; width: 18px; height: 28px; padding: 0; transform: translate(-50%,-50%); border: 0; background: transparent; cursor: pointer; z-index: 3; }
.event-marker span { display: block; width: 9px; height: 9px; margin: auto; border: 2px solid #fff; border-radius: 50%; background: #d94317; box-shadow: 0 1px 5px rgba(0,0,0,.25); }
.event-marker.active span { width: 13px; height: 13px; background: #17191f; box-shadow: 0 0 0 4px rgba(239,75,27,.2); }
.timeline-footer { display: grid; grid-template-columns: 40px minmax(0,1fr) 45px; gap: 10px; align-items: center; margin-top: 9px; color: var(--faint); font: 600 10px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
.timeline-footer > span:last-child { text-align: right; }
.current-event { min-width: 0; display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 9px; padding: 7px 10px; border-radius: 9px; background: var(--orange-soft); font-family: inherit; }
.event-time { color: var(--orange-dark); font: 700 10px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
.event-copy { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.event-copy b { overflow: hidden; color: #30251f; font-size: 11px; white-space: nowrap; text-overflow: ellipsis; }
.event-copy span { overflow: hidden; color: #9b7665; font-size: 9px; white-space: nowrap; text-overflow: ellipsis; }
.current-event > strong { color: var(--orange-dark); font: 800 14px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }

.review-panel {
  height: clamp(720px, calc(100vh - 210px), 900px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}
.panel-head { display: flex; justify-content: space-between; align-items: center; gap: 14px; padding: 17px 18px 12px; }
.panel-head h2 { margin: 4px 0 0; font-size: 18px; line-height: 1.2; }
.truth-badge { justify-self: end; flex: 0 0 auto; padding: 5px 8px; border: 1px solid #d8e9e0; border-radius: 999px; color: var(--green) !important; background: #f3fbf7; font-size: 10px !important; font-weight: 700; }
.panel-tabs { display: grid; grid-template-columns: repeat(3,1fr); padding: 0 12px; border-bottom: 1px solid var(--line); }
.panel-tabs button { position: relative; padding: 11px 4px; border: 0; color: #747b88; background: transparent; font-size: 12px; font-weight: 700; cursor: pointer; }
.panel-tabs button span { display: inline-grid; min-width: 18px; height: 18px; place-items: center; margin-left: 3px; border-radius: 99px; color: #8c929c; background: #eeeae5; font-size: 9px; }
.panel-tabs button.active { color: var(--orange-dark); }
.panel-tabs button.active::after { content: ''; position: absolute; left: 26%; right: 26%; bottom: -1px; height: 2px; background: var(--orange); }
.panel-tabs button.active span { color: #fff; background: var(--orange); }
.panel-tools { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 12px; border-bottom: 1px solid var(--line); background: #fff; flex-wrap: wrap; }
.panel-tools label { min-width: 0; flex: 1; display: flex; align-items: center; gap: 7px; padding: 6px 9px; border: 1px solid #e3ded8; border-radius: 9px; color: #989fa9; background: #faf9f7; }
.panel-tools input { width: 100%; border: 0; outline: 0; color: var(--ink); background: transparent; font-size: 11px; }
.speaker-state { flex: 0 0 auto; color: #9a6a55; font-size: 9px; }
.speaker-state.final { color: var(--green); }
.recompute-attribution-btn {
  flex: 0 0 auto;
  border: 1px solid #f0c9b0;
  border-radius: 999px;
  padding: 5px 12px;
  background: var(--orange-soft);
  color: var(--orange-dark);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.recompute-attribution-btn:hover:not(:disabled) {
  background: #ffe4d4;
  border-color: #e8a57c;
}
.recompute-attribution-btn:disabled {
  opacity: 0.65;
  cursor: wait;
}
.panel-scroll { flex: 1 1 auto; min-height: 0; overflow-x: hidden; overflow-y: auto; scrollbar-gutter: stable; overscroll-behavior: contain; }
.panel-scroll::-webkit-scrollbar { width: 8px; }
.panel-scroll::-webkit-scrollbar-thumb { border: 2px solid transparent; border-radius: 99px; background: #cfc7bf; background-clip: content-box; }
.score-accounting { position: sticky; top: 0; z-index: 3; display: flex; justify-content: space-between; gap: 8px; padding: 10px 14px; border-bottom: 1px solid var(--line); color: #6f7783; background: rgba(251,250,248,.96); backdrop-filter: blur(10px); font-size: 10px; }
.score-accounting b { color: var(--orange-dark); }
.event-row,
.transcript-row,
.chapter-row { width: 100%; display: grid; border: 0; border-bottom: 1px solid var(--line); color: var(--ink); background: transparent; text-align: left; cursor: pointer; }
.event-row { grid-template-columns: 72px minmax(0,1fr) auto; gap: 11px; padding: 14px; }
.event-row:hover,
.transcript-row:hover,
.chapter-row:hover { background: #fff; }
.event-row.active { box-shadow: inset 3px 0 var(--orange); background: #fff8f4; }
.event-row.unlocated .row-time { color: #9aa1ad; font-family: inherit; }
.event-row.estimated .row-time { color: #b45309; }
.row-time { color: var(--orange-dark); font: 700 10px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; }
.row-body { min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.row-kicker { color: #8a7367; font-size: 9px; font-weight: 700; }
.row-body > b { font-size: 12px; line-height: 1.45; }
.row-body > small { color: var(--muted); font-size: 10px; line-height: 1.5; }
.event-row > strong { color: var(--orange-dark); font: 800 14px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
.transcript-row { grid-template-columns: 30px minmax(0,1fr); gap: 10px; padding: 13px 14px; }
.transcript-row.active { box-shadow: inset 3px 0 var(--orange); background: #fff8f4; }
.speaker-avatar { display: grid; width: 28px; height: 28px; place-items: center; border-radius: 9px; color: #fff; background: linear-gradient(145deg,#f07347,#d84516); font-size: 10px; font-weight: 800; }
.speaker-line { display: flex; align-items: baseline; gap: 6px; }
.speaker-line b { font-size: 11px; }
.speaker-line small { color: var(--faint); font-size: 8px; }
.speaker-line time { margin-left: auto; color: #a87963; font: 700 9px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
.transcript-text { color: #404652; font-size: 12px; line-height: 1.75; }
.chapter-row { grid-template-columns: 32px minmax(0,1fr); gap: 10px; padding: 14px; }
.chapter-row.active { box-shadow: inset 3px 0 var(--orange); background: #fff8f4; }
.chapter-index { color: #c3b5aa; font: 800 14px/1 ui-monospace, SFMono-Regular, Menlo, monospace; }
.chapter-row .row-body > span:not(.speaker-line) { color: #4b515b; font-size: 11px; line-height: 1.55; }
.panel-empty { display: grid; min-height: 190px; place-items: center; padding: 28px; color: var(--faint); font-size: 12px; text-align: center; }

@media (max-width: 1000px) {
  .report-overview {
    grid-template-columns: minmax(250px, 1fr) minmax(250px, .9fr);
  }
  .report-overview__metrics {
    grid-column: 1 / -1;
    padding-top: 10px;
    border-top: 1px solid var(--line);
  }
  .report-overview__metrics div {
    flex: 1;
    border-left: 0;
  }
  .review-workspace { grid-template-columns: 1fr; }
  .review-stage,
  .review-panel { height: auto; }
  .review-panel { min-height: 620px; max-height: 760px; }
}

@media (max-width: 760px) {
  .report-standard { padding-bottom: 40px; }
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
    border-top: 1px solid var(--line);
  }
  .report-overview__metrics { grid-column: auto; }
  .report-tabs { overflow-x: auto; }
  .report-tabs a { flex: 0 0 auto; }
  .task-card-head {
    grid-template-columns: 44px 1fr;
    padding: 16px;
  }
  .task-card-head > span:last-child {
    grid-column: 2;
    justify-self: start;
  }
  .stage-body {
    min-height: 590px;
    padding: 8px;
    grid-template-rows: minmax(300px, 1fr) auto;
  }
  .timeline-title-row > span,
  .chapter-segment span { display: none; }
  .event-row { grid-template-columns: 62px minmax(0,1fr); }
  .event-row > strong { grid-column: 2; }
  .truth-badge { display: none; }
}

</style>
