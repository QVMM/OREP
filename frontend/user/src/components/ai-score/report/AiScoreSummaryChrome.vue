<template>
  <div class="report-chrome" aria-label="评分总结导航">
    <div class="report-head">
      <div class="head-copy">
        <h1>
          {{ title }}
          <span v-if="scoreDisplay || levelLabelDisplay" class="score-pill">
            <template v-if="scoreDisplay">{{ scoreDisplay }}</template>
            <span v-if="levelLabelDisplay">{{ levelLabelDisplay }}</span>
          </span>
        </h1>
        <div v-if="subtitleDisplay" class="report-sub">{{ subtitleDisplay }}</div>
      </div>
      <div class="head-actions">
        <button type="button" class="btn btn-ghost" @click="onDownload">下载报告</button>
        <button type="button" class="btn btn-ghost" @click="onGoMeeting">返回路演</button>
        <button type="button" class="btn btn-primary" @click="onSync">同步到任务</button>
      </div>
    </div>

    <nav class="seg-bar" aria-label="评分情境">
      <RouterLink
        v-for="item in segments"
        :key="item.key"
        :to="sectionPath(item.key)"
        class="seg"
        :class="{ 'is-on': activeKey === item.key }"
      >
        {{ item.label }}
        <span v-if="item.count !== '' && item.count != null" class="n">{{ item.count }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAiScoreReportContext } from '../../../composables/useAiScoreReport'

const props = defineProps({
  title: { type: String, default: '评分总结' },
  /** Raw score; empty/undefined → no pill number (never invent) */
  score: { type: [Number, String], default: undefined },
  levelLabel: { type: String, default: undefined },
  /** project / track / session meta string */
  subtitle: { type: String, default: undefined },
  activeKey: {
    type: String,
    default: 'result',
    validator: (v) => ['result', 'todos', 'why'].includes(v)
  },
  todoCount: { type: [Number, String], default: undefined }
})

const emit = defineEmits(['sync'])

const report = useAiScoreReportContext()

const sectionPath = report.sectionPath

const scoreDisplay = computed(() => {
  if (props.score !== undefined && props.score !== null && props.score !== '') {
    return formatScore(props.score)
  }
  // Prefer raw fields so we don't surface context's 0 fallback as a real score
  const raw = firstPresent(
    report.aiScore?.value?.overall_score,
    report.aiScore?.value?.overallScore,
    report.result?.value?.overallScore,
    report.result?.value?.overall_score
  )
  if (raw === undefined || raw === null || raw === '') return ''
  return formatScore(raw)
})

const levelLabelDisplay = computed(() => {
  if (props.levelLabel !== undefined) return String(props.levelLabel || '')
  return String(report.scoreLevel?.value?.label || '')
})

const subtitleDisplay = computed(() => {
  if (props.subtitle !== undefined) return String(props.subtitle || '')
  const result = report.result?.value || {}
  const track = firstPresent(
    report.reportTrackName?.value,
    result.track_name,
    result.trackName
  )
  const project = firstPresent(result.project_name, result.projectName, result.project?.name)
  const session = firstPresent(result.session_no, result.sessionNo)
  const completed = firstPresent(result.completed_at, result.completedAt)
  const parts = [track, project, session, formatDateShort(completed)].filter(Boolean)
  return parts.join(' · ')
})

const todoCountDisplay = computed(() => {
  if (props.todoCount !== undefined && props.todoCount !== null && props.todoCount !== '') {
    return props.todoCount
  }
  const fromNav = (report.navItems?.value || []).find((item) => item.key === 'todos')
  if (fromNav?.count !== undefined && fromNav?.count !== null && fromNav.count !== '') {
    return fromNav.count
  }
  const drafts = report.reportWorkItemDrafts?.value?.length
  const tasks = report.trainingTasks?.value?.length
  const n = drafts || tasks || ''
  return n || ''
})

const segments = computed(() => [
  { key: 'result', label: '结果', count: '' },
  { key: 'todos', label: '待办', count: todoCountDisplay.value },
  { key: 'why', label: '依据', count: '' }
])

function onDownload() {
  report.downloadPdf?.()
}

function onGoMeeting() {
  report.goMeeting?.()
}

function onSync() {
  emit('sync')
}

function formatScore(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  // Keep one decimal when needed; whole numbers stay clean
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function formatDateShort(value) {
  if (!value) return ''
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return ''
    return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
  } catch {
    return ''
  }
}

function firstPresent(...values) {
  return values.find((v) => v !== undefined && v !== null && v !== '')
}
</script>

<style scoped>
.report-chrome {
  /* 小改：对齐 DESIGN.md token，结构不变 */
  --chrome-canvas: var(--ds-canvas, #f6f2ec);
  --chrome-line: var(--ds-line, rgba(28, 26, 22, 0.09));
  --chrome-ink: var(--ds-ink, #12141a);
  --chrome-ink-2: var(--ds-ink-2, #2c3038);
  --chrome-muted: var(--ds-muted, #6b7280);
  --chrome-faint: var(--ds-faint, #9aa1ad);
  --chrome-orange: var(--ds-orange, #e84a1c);
  --chrome-orange-deep: var(--ds-orange-deep, #c43a12);
  --chrome-orange-soft: var(--ds-orange-soft, #fde8de);
  --chrome-orange-wash: var(--ds-orange-wash, #fef6f2);
  --chrome-font: var(--ds-font-sans, "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif);
  --chrome-num: var(--ds-font-num, "DIN Alternate", "SF Pro Text", Arial, sans-serif);

  /* Pinned by parent flex column (not sticky) — avoids blank gap under workspace topbar */
  position: relative;
  flex-shrink: 0;
  z-index: 20;
  background: var(--chrome-canvas);
  border-bottom: 1px solid var(--chrome-line);
  color: var(--chrome-ink);
  font-family: var(--chrome-font);
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
}

.report-chrome :deep(em),
.report-chrome :deep(i) {
  font-style: normal;
}

.report-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 16px clamp(18px, 3vw, 28px) 4px;
}

.head-copy {
  min-width: 0;
}

.report-head h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.3;
  font-style: normal;
  font-synthesis: none;
}

.score-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 10px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--chrome-orange-wash);
  border: 1px solid var(--chrome-orange-soft);
  font-family: var(--chrome-num);
  font-size: 13px;
  font-weight: 700;
  color: var(--chrome-orange-deep);
  vertical-align: middle;
  font-variant-numeric: tabular-nums;
}

.score-pill span {
  font-family: var(--chrome-font);
  font-size: 11px;
  font-weight: 600;
  color: var(--chrome-orange);
}

.report-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--chrome-muted);
  font-weight: 500;
}

.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  flex-shrink: 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: var(--ds-btn-height, 40px);
  padding: 0 16px;
  border: 0;
  border-radius: var(--ds-radius-pill, 999px);
  background: none;
  font-family: inherit;
  font-size: var(--ds-btn-font, 15px);
  font-weight: 700;
  font-style: normal;
  font-synthesis: none;
  cursor: pointer;
  color: inherit;
}

.btn-ghost {
  color: var(--chrome-muted);
}

.btn-ghost:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--chrome-ink-2);
}

.btn-primary {
  background: var(--chrome-orange);
  color: #fff;
  box-shadow: none;
}

.btn-primary:hover {
  background: var(--chrome-orange-deep);
}

.seg-bar {
  display: flex;
  gap: 6px;
  padding: 8px clamp(18px, 3vw, 28px) 14px;
}

.seg {
  display: inline-flex;
  align-items: center;
  height: 36px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 14px;
  font-weight: 500;
  color: var(--chrome-muted);
  text-decoration: none;
  font-style: normal;
  font-synthesis: none;
  background: transparent;
}

.seg:hover {
  color: var(--chrome-ink-2);
  background: rgba(255, 255, 255, 0.55);
}

.seg.is-on {
  background: #fff;
  color: var(--chrome-ink);
  font-weight: 700;
  border-color: var(--chrome-line);
  box-shadow: 0 1px 2px rgba(116, 71, 39, 0.06);
}

.seg .n {
  margin-left: 5px;
  font-family: var(--chrome-num);
  font-size: 12px;
  font-weight: 700;
  color: var(--chrome-faint);
  font-variant-numeric: tabular-nums;
}

.seg.is-on .n {
  color: var(--chrome-orange);
}

@media (max-width: 720px) {
  .report-head {
    flex-direction: column;
  }

  .head-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
