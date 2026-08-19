<template>
  <AiScoreReportShell title="证据链" subtitle="按评分项核验证据来源">
    <template #actions>
      <button type="button" class="primary" :disabled="!report.effectiveSessionId.value || report.evidenceBundleLoading.value" @click="report.handlePrepareEvidenceBundle">
        {{ report.evidenceBundleLoading.value ? '生成中' : '生成证据快照' }}
      </button>
    </template>

    <div class="page-stack">
      <section class="evidence-summary" aria-label="证据关键指标">
        <article v-for="metric in metrics" :key="metric.label" :class="['summary-item', metric.tone]">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="observation-evidence-panel panel-block">
        <div class="panel-head inline">
          <div>
            <span>观测点证据</span>
            <strong>证据等级与扣分影响</strong>
          </div>
          <em>{{ observationEvidenceRows.length }} 项</em>
        </div>
        <div v-if="observationEvidenceRows.length" class="observation-evidence-list">
          <article v-for="item in observationEvidenceRows" :key="item.id" class="observation-evidence-row">
            <div>
              <b>{{ item.name }}</b>
              <p>{{ item.modelReason }}</p>
            </div>
            <span>{{ item.evidenceLevelLabel }}</span>
            <strong>{{ item.rawScoreText }} / {{ item.capText }}</strong>
            <em>{{ item.deductions.length ? `${item.deductions.length} 个扣分项` : '无当前扣分' }}</em>
            <button type="button" @click="selectObservationEvidence(item)">定位证据</button>
          </article>
        </div>
        <p v-else class="quiet-copy">历史报告未生成规则引擎观测点，证据链仍按转写、关键帧和锚点展示。</p>
      </section>

      <section class="snapshot-workbench">
        <aside class="timeline-panel panel-block">
          <div class="panel-head">
            <span>证据筛选</span>
            <strong>快照时间线</strong>
            <em>{{ filteredTimelineItems.length }}/{{ timelineItems.length }} 条</em>
          </div>

          <div class="filter-chips" aria-label="证据类型筛选">
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

          <label class="evidence-search">
            <span>搜索证据</span>
            <input v-model.trim="searchKeyword" type="search" placeholder="搜索时间、评分项或证据内容" />
          </label>

          <div v-if="filteredTimelineItems.length" class="timeline-list">
            <button
              v-for="item in filteredTimelineItems"
              :key="item.id"
              type="button"
              :class="['timeline-row', item.tone, { active: item.id === selectedTimelineItemId }]"
              @click="selectTimelineItem(item)"
            >
              <span>{{ item.time }}</span>
              <div>
                <b>{{ item.title }}</b>
                <p>{{ item.summary }}</p>
                <mark v-if="item.dimension">{{ item.dimension }}</mark>
              </div>
              <i>{{ item.type }}</i>
            </button>
          </div>
          <AiScoreEmptyState v-else title="暂无匹配证据" description="可切换筛选条件，或生成证据快照后再查看结构化结果。" />
        </aside>

        <main class="snapshot-panel panel-block">
          <header class="snapshot-head">
            <div>
              <span>当前证据</span>
              <h2>{{ selectedTimeline?.title || '证据详情' }}</h2>
              <p>{{ selectedTimeline?.time || '-' }} · {{ selectedTimeline?.type || '证据点' }} · {{ selectedTimeline?.source || '报告证据' }}</p>
            </div>
            <strong>{{ selectedTimeline?.time || '--:--' }}</strong>
          </header>

          <section class="snapshot-stage" aria-label="证据快照">
            <img v-if="selectedFrameImage" :src="selectedFrameImage" alt="评分关键帧快照" />
            <div v-else class="text-snapshot">
              <span>{{ selectedTimeline?.type || '转写证据' }}</span>
              <p>{{ selectedTimeline?.summary || '请选择左侧证据点。' }}</p>
            </div>
          </section>

          <section class="snapshot-caption">
            <div>
              <span>快照说明</span>
              <p>{{ snapshotDescription }}</p>
            </div>
            <div class="snapshot-actions">
              <button type="button" @click="selectNeighbor(-1)">上一条</button>
              <button type="button" @click="selectNeighbor(1)">下一条</button>
              <button type="button" @click="copyEvidence">复制证据</button>
            </div>
          </section>
        </main>

        <aside class="relation-panel panel-block">
          <div class="panel-head compact">
            <span>证据关联</span>
            <strong>评分项核验</strong>
          </div>

          <section class="relation-section">
            <h3>关联评分项</h3>
            <div v-if="relationTags.length" class="relation-tags">
              <span v-for="tag in relationTags" :key="tag">{{ tag }}</span>
            </div>
            <p v-else class="quiet-copy">当前证据暂未关联评分项，生成证据快照后可自动归档。</p>
          </section>

          <dl class="verify-list">
            <div><dt>类型</dt><dd>{{ selectedTimeline?.type || '-' }}</dd></div>
            <div><dt>置信度</dt><dd>{{ selectedTimeline?.confidence || '-' }}</dd></div>
            <div><dt>关联维度</dt><dd>{{ selectedTimeline?.dimension || '未标注' }}</dd></div>
            <div><dt>来源</dt><dd>{{ selectedTimeline?.source || '报告证据' }}</dd></div>
          </dl>

          <section class="relation-section">
            <h3>可用操作</h3>
            <div class="relation-actions">
              <RouterLink :to="report.sectionPath('dimensions')">关联评分项</RouterLink>
              <RouterLink :to="report.sectionPath('actions')">加入整改证据</RouterLink>
              <button type="button" @click="selectNeighbor(1)">查看相邻片段</button>
            </div>
          </section>

          <section :class="['risk-box', selectedTimeline?.tone]">
            <h3>风险提示</h3>
            <p>{{ riskSummary }}</p>
          </section>
        </aside>
      </section>

      <section class="anchor-panel panel-block">
        <div class="panel-head inline">
          <div>
            <span>证据锚点</span>
            <strong>按评分项归档</strong>
          </div>
          <em>{{ anchorItems.length }} 条</em>
        </div>

        <div v-if="anchorRows.length" class="anchor-table">
          <div class="anchor-head">
            <span>评分项</span>
            <span>证据时间</span>
            <span>证据类型</span>
            <span>证据摘要</span>
            <span>可信度</span>
            <span>操作</span>
          </div>
          <article v-for="anchor in anchorRows" :key="anchor.id" class="anchor-row">
            <b>{{ anchor.dimension || '未标注' }}</b>
            <span>{{ anchor.time }}</span>
            <span>{{ anchor.type }}</span>
            <p>{{ anchor.summary }}</p>
            <strong>{{ anchor.confidence || '-' }}</strong>
            <button type="button" @click="selectTimelineItem(anchor)">定位</button>
          </article>
        </div>
        <AiScoreEmptyState v-else title="暂无结构化证据锚点" description="生成证据快照后，系统会按评分项自动归档关键证据。" />
      </section>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreEmptyState from '../../components/ai-score/report/AiScoreEmptyState.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'
import {
  findFrameByAnchor,
  findFrameNearSeconds as findFrameNearSecondsStrict,
  frameSeconds as strictFrameSeconds
} from '../../utils/aiScoreFrameMatching'

const report = useAiScoreReportContext()

const selectedTimelineItemId = ref('')
const activeFilter = ref('all')
const searchKeyword = ref('')

const selectedTimeline = computed(() => timelineItems.value.find(item => item.id === selectedTimelineItemId.value) || filteredTimelineItems.value[0] || timelineItems.value[0] || null)
const selectedFrame = computed(() => selectedTimeline.value?.frame || null)
const selectedFrameImage = computed(() => imageUrl(selectedFrame.value))
const selectedIndex = computed(() => filteredTimelineItems.value.findIndex(item => item.id === selectedTimeline.value?.id))
const observationEvidenceRows = computed(() => report.ruleEngineReport.value.observations.slice(0, 15))

const anchorItems = computed(() => report.structuredEvidenceAnchors.value.map((item, index) => {
  const frame = findAnchorFrame(item)
  const observationCodes = uniqueStrings(
    item.observationCodes || item.observation_codes || item.observationCode || item.observation_code
  )
  const linkedLossCauses = uniqueStrings(item.linkedLossCauses || item.linked_loss_causes)
  const scoreLinked = Boolean(
    item.scoreLinked
    || item.score_linked
    || observationCodes.length
    || linkedLossCauses.length
  )
  const structuredTone = firstPresent(item.riskTone, item.risk_tone, '')
  return {
    raw: item,
    id: `anchor-${item.id || item.anchor_id || index}`,
    seconds: secondsFromEvidence(item, index),
    time: anchorTime(item, index),
    title: firstPresent(item.anchorTitle, item.anchor_title, item.title, item.dimension, typeLabel(item.anchorType), '证据锚点'),
    summary: firstPresent(item.evidenceText, item.evidence_text, item.summary, item.reason, item.detail, item.text, '暂无证据说明。'),
    type: typeLabel(firstPresent(item.anchorType, item.anchor_type, item.sourceType, item.source_type)) || '结构化锚点',
    confidence: confidenceLabel(item.confidence),
    dimension: firstPresent(
      (item.dimensionNames || item.dimension_names || [])[0],
      item.dimension,
      item.dimensionName,
      item.dimension_name,
      observationCodes.join(' / '),
      ''
    ),
    observationCodes,
    linkedLossCauses,
    scoreLinked,
    source: '结构化锚点',
    tone: structuredTone || (scoreLinked ? 'warning' : 'ok'),
    frame,
    category: 'anchor'
  }
}))
const frameItems = computed(() => report.evidenceFrames.value.map((frame, index) => ({
  raw: frame,
  id: `frame-${frame.id || frame.backendId || index}`,
  seconds: frameSeconds(frame),
  time: frame.timeLabel || report.formatTime(frameSeconds(frame)),
  title: frame.title || '关键帧',
  summary: frame.caption || '暂无画面说明。',
  type: frame.screen_type || frame.screenType || frame.frame_type || frame.frameType || '关键帧',
  confidence: confidenceLabel(frame.confidence),
  dimension: frame.dimension || '',
  observationCodes: [],
  linkedLossCauses: [],
  scoreLinked: false,
  source: '视觉关键帧',
  tone: 'ok',
  frame,
  category: 'frame'
})))
const transcriptItems = computed(() => report.asrSegments.value.map((segment, index) => {
  const speakerLabel = firstPresent(
    segment.displaySpeaker,
    segment.display_speaker,
    segment.speakerName,
    segment.speaker_name,
    segment.personName,
    segment.person_name,
    segment.speaker,
    segment.role,
    `转写片段 ${index + 1}`
  )
  return {
    raw: segment,
    id: `asr-${segment.id || index}`,
    seconds: secondsFromEvidence(segment, index),
    time: report.formatTime(secondsFromEvidence(segment, index)),
    title: speakerLabel,
    summary: firstPresent(segment.text, segment.transcript, segment.content, '暂无转写文本。'),
    type: '转写片段',
    confidence: confidenceLabel(segment.confidence),
    dimension: '',
    observationCodes: [],
    linkedLossCauses: [],
    scoreLinked: false,
    source: 'ASR转写',
    tone: 'ok',
    frame: nearestFrame(secondsFromEvidence(segment, index)),
    category: 'transcript'
  }
}))
const timelineItems = computed(() => [...anchorItems.value, ...frameItems.value, ...transcriptItems.value].sort((a, b) => a.seconds - b.seconds))
const filteredTimelineItems = computed(() => {
  const keyword = searchKeyword.value.toLowerCase()
  return timelineItems.value.filter(item => {
    const matchFilter = activeFilter.value === 'all' ||
      (activeFilter.value === 'risk' && item.tone !== 'ok') ||
      (activeFilter.value === 'transcript' && item.category === 'transcript') ||
      (activeFilter.value === 'frame' && item.category === 'frame') ||
      (activeFilter.value === 'linked' && item.scoreLinked)
    if (!matchFilter) return false
    if (!keyword) return true
    return `${item.time} ${item.title} ${item.summary} ${item.type} ${item.dimension} ${(item.observationCodes || []).join(' ')}`.toLowerCase().includes(keyword)
  })
})
const filters = computed(() => [
  { key: 'all', label: '全部', count: timelineItems.value.length },
  { key: 'risk', label: '风险', count: timelineItems.value.filter(item => item.tone !== 'ok').length },
  { key: 'transcript', label: '转写', count: transcriptItems.value.length },
  { key: 'frame', label: '关键帧', count: frameItems.value.length },
  { key: 'linked', label: '已关联', count: timelineItems.value.filter(item => item.scoreLinked).length }
])
const metrics = computed(() => [
  { label: '证据快照', value: snapshotStatus.value, hint: report.effectiveSessionId.value ? '用于本轮正式评分' : '旧报告无会话快照' },
  { label: '证据总数', value: timelineItems.value.length || '-', hint: '关键帧+转写+锚点', tone: 'primary' },
  { label: '转写片段', value: report.asrSegments.value.length || '-', hint: '语音证据' },
  { label: '关键帧', value: report.evidenceFrames.value.length || '-', hint: '画面证据' },
  { label: '风险证据', value: timelineItems.value.filter(item => item.tone !== 'ok').length, hint: '疑似扣分/风险', tone: 'warning' },
  { label: '规则观测点', value: observationEvidenceRows.value.length || '0', hint: report.ruleEngineReport.value.hasShadow ? '已按证据等级归档' : '旧报告未启用' }
])
const snapshotStatus = computed(() => statusLabel(report.evidenceBundle.value?.snapshotStatus || 'missing'))
const relationTags = computed(() => {
  const item = selectedTimeline.value
  if (!item) return []
  const tags = [
    item.dimension,
    ...(item.observationCodes || []),
    ...(item.linkedLossCauses || []).slice(0, 2),
  ].filter(Boolean)
  return [...new Set(tags)].slice(0, 4)
})
const snapshotDescription = computed(() => {
  if (!selectedTimeline.value) return '请选择左侧证据点查看快照详情。'
  if (selectedTimeline.value.category === 'frame') return selectedTimeline.value.summary === '暂无画面说明。'
    ? '当前关键帧已采集，但视觉描述尚未生成。生成证据快照后可补全画面说明和评分项关联。'
    : selectedTimeline.value.summary
  return selectedTimeline.value.summary
})
const riskSummary = computed(() => {
  const item = selectedTimeline.value
  if (!item) return '请选择证据后查看风险提示。'
  if (item.tone === 'danger') {
    const causes = (item.linkedLossCauses || []).join('、')
    return causes
      ? `该证据已关联规则失分：${causes}。请回到「为什么不是 100 分」核对账本。`
      : '该证据已关联硬性扣分项，请回到失分账本核对原因。'
  }
  if (item.tone === 'warning') {
    const codes = (item.observationCodes || []).join('、')
    return codes
      ? `该证据支撑观测点 ${codes}，但仍有表现或证据等级缺口。`
      : '该证据与评分观测点相关，建议结合相邻片段复核。'
  }
  if (item.scoreLinked) return '该证据已绑定评分观测点，可作为核验素材。'
  return '当前条目未绑定正式失分账本，仅作过程浏览，不代表扣分判定。'
})
const anchorRows = computed(() => anchorItems.value.slice(0, 8))

watch([filteredTimelineItems, timelineItems], () => {
  const source = filteredTimelineItems.value.length ? filteredTimelineItems.value : timelineItems.value
  if (!source.length) {
    selectedTimelineItemId.value = ''
    return
  }
  if (!source.some(item => item.id === selectedTimelineItemId.value)) selectedTimelineItemId.value = source[0].id
}, { immediate: true })

function selectTimelineItem(item) {
  selectedTimelineItemId.value = item.id
  if (item.frame) report.selectedEvidenceFrame.value = item.frame
}

function selectObservationEvidence(item) {
  const anchorId = item.evidenceAnchorIds[0] || item.deductions[0]?.evidenceAnchorIds?.[0]
  const anchor = anchorId
    ? anchorItems.value.find(value => String(value.raw?.id) === String(anchorId) || String(value.id) === `anchor-${anchorId}`)
    : null
  if (anchor) {
    selectTimelineItem(anchor)
    return
  }
  searchKeyword.value = item.dimensionName || item.name
}

function selectNeighbor(step) {
  const list = filteredTimelineItems.value
  if (!list.length) return
  const current = selectedIndex.value < 0 ? 0 : selectedIndex.value
  const next = Math.min(list.length - 1, Math.max(0, current + step))
  selectTimelineItem(list[next])
}

async function copyEvidence() {
  const item = selectedTimeline.value
  if (!item) return
  await navigator.clipboard?.writeText?.(`[${item.time}] ${item.title}：${item.summary}`)
  ElMessage.success('证据内容已复制')
}

function findAnchorFrame(anchor) {
  return findFrameByAnchor(anchor, report.evidenceFrames.value, { sessionId: report.effectiveSessionId.value })
}

function nearestFrame(seconds) {
  return findFrameNearSecondsStrict(seconds, report.evidenceFrames.value, { sessionId: report.effectiveSessionId.value })
}

function anchorTime(anchor, index) {
  const direct = firstPresent(anchor.time, anchor.timeLabel, anchor.sourceRef)
  if (direct) return direct
  return report.formatTime(secondsFromEvidence(anchor, index))
}

function secondsFromEvidence(item, index = 0) {
  const seconds = firstPresent(item.timestamp, item.time_seconds, item.timeSeconds, item.position_seconds, item.positionSeconds, item.start, item.start_seconds, item.startSeconds)
  if (seconds !== undefined) return Number(seconds)
  const ms = firstPresent(item.startMs, item.start_ms)
  if (ms !== undefined) return Number(ms) / 1000
  return index * 30
}

function frameSeconds(frame) {
  return strictFrameSeconds(frame)
}

function imageUrl(frame) {
  if (!frame) return ''
  return firstPresent(frame.image_url, frame.imageUrl, frame.frame_url, frame.frameUrl, frame.url, '')
}

function typeLabel(type) {
  const typeMap = { transcript_segment: '转写片段', transcript: '转写证据', frame_ocr: '关键帧/OCR', frame: '关键帧', screen_ocr: '屏幕识别' }
  return typeMap[type] || type || ''
}

function confidenceLabel(value) {
  if (value === undefined || value === null || value === '') return '-'
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)
  return number <= 1 ? `${Math.round(number * 100)}%` : `${Math.round(number)}%`
}

function statusLabel(status) {
  const map = { ready: '已生成', missing: '待生成', preparing: '生成中', failed: '生成失败' }
  return map[status] || status || '待生成'
}

function uniqueStrings(value) {
  const list = Array.isArray(value) ? value : (value === undefined || value === null || value === '' ? [] : [value])
  const result = []
  const seen = new Set()
  for (const item of list) {
    const text = String(item || '').trim()
    if (!text || seen.has(text)) continue
    seen.add(text)
    result.push(text)
  }
  return result
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}
</script>

<style scoped>
.page-stack { display: grid; gap: 12px; min-width: 0; }
.panel-block { min-width: 0; border: 1px solid #e2d8cf; border-radius: 8px; background: #fffdfa; box-shadow: 0 12px 34px rgba(82, 61, 46, .045); }
.evidence-summary { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); overflow: hidden; border: 1px solid #e2d8cf; border-radius: 8px; background: #fffdfa; }
.summary-item { min-height: 64px; padding: 10px 14px; border-right: 1px solid #efe7df; }
.summary-item:last-child { border-right: 0; }
.summary-item span, .summary-item small { display: block; color: #6c7280; font-size: 11px; line-height: 1.25; }
.summary-item strong { display: block; margin: 5px 0 2px; color: #182033; font-size: 22px; line-height: 1; font-weight: 900; font-variant-numeric: tabular-nums; }
.summary-item.primary strong { color: #e85d2a; }
.summary-item.warning strong { color: #e85d2a; }
.observation-evidence-panel { padding: 12px; }
.observation-evidence-list { overflow: hidden; border: 1px solid #e5dcd3; border-radius: 7px; }
.observation-evidence-row { display: grid; grid-template-columns: minmax(220px, 1fr) 128px 82px 92px 72px; gap: 10px; align-items: center; min-width: 760px; padding: 8px 10px; border-top: 1px solid #efe7df; background: #fff; }
.observation-evidence-row:first-child { border-top: 0; }
.observation-evidence-row b { display: block; color: #182033; font-size: 12px; font-weight: 900; }
.observation-evidence-row p { display: -webkit-box; overflow: hidden; margin: 3px 0 0; color: #566174; font-size: 11px; line-height: 1.4; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.observation-evidence-row span, .observation-evidence-row em { color: #5f6878; font-size: 11px; font-style: normal; font-weight: 850; }
.observation-evidence-row strong { color: #e85d2a; font-size: 12px; font-weight: 900; font-variant-numeric: tabular-nums; }
.observation-evidence-row button { min-height: 26px; padding: 0 8px; border: 1px solid #f2b39c; border-radius: 5px; background: #fff7f2; color: #d9532a; font-size: 10.5px; font-weight: 900; cursor: pointer; white-space: nowrap; }
.snapshot-workbench { display: grid; grid-template-columns: 320px minmax(0, 1fr) 245px; gap: 10px; align-items: start; min-width: 0; }
.timeline-panel, .relation-panel { padding: 12px; }
.panel-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 10px; margin-bottom: 10px; }
.panel-head.inline { display: flex; align-items: center; justify-content: space-between; }
.panel-head span { justify-self: start; padding: 2px 7px; border-radius: 999px; background: #fff0e8; color: #c6532d; font-size: 10px; font-weight: 900; }
.panel-head strong { color: #182033; font-size: 16px; }
.panel-head em { align-self: end; color: #7b8495; font-style: normal; font-size: 11px; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.filter-chips button { min-height: 26px; padding: 0 8px; border: 1px solid #e7ded6; border-radius: 999px; background: #fff; color: #5f6878; font-size: 11px; font-weight: 800; cursor: pointer; }
.filter-chips button.active { border-color: #e85d2a; background: #fff0e8; color: #d9532a; }
.filter-chips b { margin-left: 3px; font-variant-numeric: tabular-nums; }
.evidence-search { display: grid; gap: 5px; margin-bottom: 10px; }
.evidence-search span { color: #687084; font-size: 11px; font-weight: 800; }
.evidence-search input { width: 100%; height: 32px; padding: 0 10px; border: 1px solid #e4d9cf; border-radius: 6px; background: #fff; color: #182033; font-size: 12px; outline: none; }
.evidence-search input:focus { border-color: #e85d2a; box-shadow: 0 0 0 3px rgba(232, 93, 42, .1); }
.timeline-list { display: grid; gap: 7px; max-height: 580px; overflow: auto; padding-right: 2px; }
.timeline-row { display: grid; grid-template-columns: 48px minmax(0, 1fr) 58px; gap: 8px; align-items: start; width: 100%; min-width: 0; padding: 9px 10px; border: 1px solid #eee4dc; border-left: 3px solid #32b36b; border-radius: 7px; background: #fff; text-align: left; cursor: pointer; }
.timeline-row.warning { border-left-color: #f0a12b; }
.timeline-row.danger { border-left-color: #e84c3d; }
.timeline-row.active { border-color: #e85d2a; border-left-color: #e85d2a; background: #fff3ec; box-shadow: inset 0 0 0 1px rgba(232, 93, 42, .18); }
.timeline-row span { color: #e85d2a; font-size: 11px; font-weight: 900; font-variant-numeric: tabular-nums; }
.timeline-row b { color: #182033; font-size: 12px; font-weight: 900; }
.timeline-row p { display: -webkit-box; overflow: hidden; margin: 3px 0 0; color: #566174; font-size: 11px; line-height: 1.45; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.timeline-row mark { display: inline-flex; margin-top: 5px; padding: 2px 6px; border-radius: 5px; background: #f3f5f8; color: #667085; font-size: 10px; font-weight: 800; }
.timeline-row i { color: #7b8495; font-style: normal; font-size: 10px; text-align: right; }
.snapshot-panel { overflow: hidden; padding: 0; background: #fff; }
.snapshot-head { display: flex; justify-content: space-between; gap: 16px; padding: 12px 14px 8px; border-bottom: 1px solid #f0e5dc; background: linear-gradient(180deg, #fffdfb 0%, #fff8f3 100%); }
.snapshot-head span { padding: 2px 7px; border-radius: 999px; background: #fff0e8; color: #c6532d; font-size: 10px; font-weight: 900; }
.snapshot-head h2 { margin: 5px 0 2px; color: #182033; font-size: 20px; line-height: 1.1; }
.snapshot-head p { margin: 0; color: #667085; font-size: 12px; line-height: 1.35; }
.snapshot-head strong { color: #e85d2a; font-size: 22px; line-height: 1; font-weight: 950; font-variant-numeric: tabular-nums; }
.snapshot-stage { display: grid; place-items: center; min-height: 360px; margin: 10px 12px 0; overflow: hidden; border: 1px solid #ebe2d9; border-radius: 7px; background: #f8f6f3; }
.snapshot-stage img { display: block; width: 100%; max-height: 430px; object-fit: contain; background: #111827; }
.text-snapshot { display: grid; align-content: center; gap: 12px; width: 100%; min-height: 330px; padding: 34px; background: #fffdfb; }
.text-snapshot span { color: #e85d2a; font-size: 12px; font-weight: 900; }
.text-snapshot p { margin: 0; color: #263142; font-size: 15px; line-height: 1.9; }
.snapshot-caption { display: flex; justify-content: space-between; gap: 12px; margin: 10px 12px 12px; padding: 11px 12px; border: 1px solid #ebe2d9; border-radius: 7px; background: #fffdfa; }
.snapshot-caption span { color: #8a604c; font-size: 11px; font-weight: 900; }
.snapshot-caption p { margin: 4px 0 0; color: #4d596b; font-size: 12px; line-height: 1.6; }
.snapshot-actions { display: flex; flex-wrap: wrap; gap: 6px; align-content: start; justify-content: flex-end; min-width: 210px; }
.snapshot-actions button, .relation-actions a, .relation-actions button, .anchor-row button { min-height: 28px; padding: 0 9px; border: 1px solid #dfcfc2; border-radius: 5px; background: #fff; color: #be3d2b; text-decoration: none; font-size: 11px; font-weight: 900; cursor: pointer; }
.relation-panel { display: grid; gap: 10px; }
.relation-section { padding: 10px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.relation-section h3, .risk-box h3 { margin: 0 0 8px; color: #182033; font-size: 13px; }
.relation-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.relation-tags span { padding: 4px 8px; border-radius: 999px; background: #fff0e8; color: #be3d2b; font-size: 11px; font-weight: 850; }
.quiet-copy { margin: 0; color: #7b8495; font-size: 12px; line-height: 1.6; }
.verify-list { display: grid; gap: 7px; margin: 0; }
.verify-list div { padding: 9px 10px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.verify-list dt { color: #7b8495; font-size: 10px; font-weight: 900; }
.verify-list dd { margin: 4px 0 0; color: #182033; font-size: 12px; line-height: 1.45; word-break: break-word; }
.relation-actions { display: grid; gap: 7px; }
.relation-actions a, .relation-actions button { justify-content: center; display: inline-flex; align-items: center; }
.risk-box { padding: 10px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.risk-box.danger { border-color: #ffd2c4; background: #fff4ef; }
.risk-box.warning { border-color: #ffe0a7; background: #fff8e9; }
.risk-box p { margin: 0; color: #566174; font-size: 12px; line-height: 1.6; }
.anchor-panel { padding: 12px; }
.anchor-table { overflow: hidden; border: 1px solid #e5dcd3; border-radius: 7px; }
.anchor-head, .anchor-row { display: grid; grid-template-columns: 150px 82px 90px minmax(0, 1fr) 70px 58px; gap: 10px; align-items: start; padding: 8px 10px; }
.anchor-head { color: #6b574b; background: #fbf4ee; font-size: 11px; font-weight: 900; }
.anchor-row { border-top: 1px solid #efe7df; background: #fff; }
.anchor-row b, .anchor-row strong, .anchor-row span { color: #182033; font-size: 12px; }
.anchor-row p { display: -webkit-box; overflow: hidden; margin: 0; color: #566174; font-size: 12px; line-height: 1.45; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
@media (max-width: 1280px) {
  .snapshot-workbench { grid-template-columns: 300px minmax(0, 1fr); }
  .relation-panel { grid-column: 1 / -1; grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .evidence-summary, .snapshot-workbench, .relation-panel, .anchor-head, .anchor-row { grid-template-columns: 1fr; }
  .snapshot-caption { display: grid; }
  .snapshot-actions { justify-content: flex-start; }
}
</style>
