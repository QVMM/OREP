<template>
  <AiScoreReportShell title="现场呈现" subtitle="按画面证据定位站位、仪态与演示问题">
    <div class="page-stack">
      <section class="presentation-summary" aria-label="现场呈现关键指标">
        <article v-for="metric in metrics" :key="metric.label" :class="['summary-item', metric.tone]">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="presentation-workbench">
        <aside class="issue-panel panel-block">
          <div class="panel-head">
            <span>问题镜头队列</span>
            <strong>优先处理的呈现问题</strong>
            <em>{{ filteredIssues.length }}/{{ presentationIssues.length }} 条</em>
          </div>

          <div class="filter-chips" aria-label="现场呈现问题筛选">
            <button
              v-for="filter in issueFilters"
              :key="filter.key"
              type="button"
              :class="{ active: activeFilter === filter.key }"
              @click="activeFilter = filter.key"
            >
              {{ filter.label }} <b>{{ filter.count }}</b>
            </button>
          </div>

          <label class="issue-search">
            <span>搜索镜头</span>
            <input v-model.trim="searchKeyword" type="search" placeholder="搜索时间、问题或整改动作" />
          </label>

          <div v-if="filteredIssues.length" ref="issueListRef" class="issue-list">
            <button
              v-for="(item, index) in filteredIssues"
              :key="item.id"
              type="button"
              :class="['issue-row', item.tone, { active: item.id === selectedIssue?.id }]"
              @click="selectIssue(item)"
            >
              <span>#{{ index + 1 }}</span>
              <div>
                <b>{{ item.time }} · {{ item.title }}</b>
                <p>{{ item.evidence }}</p>
                <small>整改：{{ item.action }}</small>
              </div>
              <i>{{ item.priority }}</i>
            </button>
          </div>
          <AiScoreEmptyState v-else title="暂无匹配镜头" description="可切换筛选条件，或等待现场呈现建议生成。" />
        </aside>

        <main class="diagnosis-panel panel-block">
          <header class="diagnosis-head">
            <div>
              <span>现场画面诊断</span>
              <h2>{{ selectedIssue?.time || '--:--' }} · {{ selectedIssue?.title || '现场呈现问题' }}</h2>
              <p>{{ selectedIssue?.priority || '待判断' }} · {{ selectedIssue?.goal || '选择左侧镜头查看证据和整改标准' }}</p>
            </div>
            <strong>{{ selectedIssue?.riskLabel || '待复盘' }}</strong>
          </header>

          <section class="snapshot-stage">
            <img v-if="selectedFrameImage" :src="selectedFrameImage" alt="现场呈现快照证据" />
            <div v-else class="snapshot-placeholder">
              <span>暂无快照</span>
              <p>当前报告未返回可展示的现场画面证据。</p>
            </div>
            <div v-if="selectedFrameImage" class="snapshot-shade"></div>
            <button v-for="callout in activeCallouts" :key="callout.label" type="button" class="callout-dot" :style="{ left: callout.x, top: callout.y }">
              <b>{{ callout.label }}</b>
              <span>{{ callout.text }}</span>
            </button>
          </section>

          <section class="diagnosis-grid">
            <article>
              <h3>扣分原因</h3>
              <p>{{ selectedIssue?.reason || '报告未返回该镜头的具体扣分说明。' }}</p>
            </article>
            <article>
              <h3>怎么改</h3>
              <p>{{ selectedIssue?.fix || '下一轮彩排时，把站位、屏幕切换和评委互动拆成可检查动作。' }}</p>
            </article>
          </section>

          <section class="acceptance-line">
            <span>验收标准</span>
            <ul>
              <li v-for="standard in acceptanceStandards" :key="standard">{{ standard }}</li>
            </ul>
          </section>
        </main>

        <aside class="dashboard-panel panel-block">
          <div class="panel-head compact">
            <span>呈现仪表盘</span>
            <strong>{{ dashboardVerdict }}</strong>
          </div>

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

          <section class="pass-line">
            <h3>本轮通过线</h3>
            <ul>
              <li>讲者离屏幕边缘 1 米</li>
              <li>队员站成浅弧线</li>
              <li>关键页停留 3 秒</li>
              <li>讲完回看评委</li>
            </ul>
          </section>

          <button
            type="button"
            class="plan-button"
            :disabled="report.presentationCoachingLoading.value || !report.effectiveMeetingId.value"
            @click="report.loadPresentationCoaching(true)"
          >
            {{ report.presentationCoachingLoading.value ? '生成中' : '生成现场呈现训练' }}
          </button>
        </aside>
      </section>

      <section class="next-training panel-block">
        <div class="panel-head inline">
          <div>
            <span>下一轮呈现整改</span>
            <strong>从快照问题到彩排动作</strong>
          </div>
          <em>{{ rehearsalTasks.length }} 项</em>
        </div>

        <div class="task-list">
          <article v-for="task in rehearsalTasks" :key="task.title">
            <div>
              <b>{{ task.title }}</b>
              <span>待训练</span>
            </div>
            <p>{{ task.detail }}</p>
            <small>{{ task.source }}</small>
          </article>
        </div>
      </section>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreEmptyState from '../../components/ai-score/report/AiScoreEmptyState.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()

const selectedIssueId = ref('')
const activeFilter = ref('all')
const searchKeyword = ref('')
const issueListRef = ref(null)

const screenSummary = computed(() => firstObject(report.videoAgg.value.screen_content_summary, report.videoAgg.value.screenContentSummary, report.video.value.screen_content_summary, report.video.value.screenContentSummary))
const keyFrames = computed(() => report.evidenceFrames.value)
const visualAverage = computed(() => firstPresent(report.videoAgg.value.avg_visual_composite, report.videoAgg.value.avgVisualComposite, report.videoAgg.value.visual_average, report.videoAgg.value.visualAverage))
const imageEfficiency = computed(() => {
  const raw = Number(firstPresent(visualAverage.value, report.videoAgg.value.visual_valid_rate, report.videoAgg.value.visualValidRate, 72))
  if (!Number.isFinite(raw)) return 72
  return raw <= 10 ? Math.round(raw * 10) : Math.round(Math.min(raw, 100))
})
const mainScreenType = computed(() => {
  const distributions = [screenSummary.value.screen_type_distribution, screenSummary.value.screenTypeDistribution, screenSummary.value.content_type_counts, screenSummary.value.contentTypeCounts, report.videoAgg.value.screen_type_distribution, report.videoAgg.value.screenTypeDistribution]
  for (const distribution of distributions) {
    const top = topDistributionItem(distribution)
    if (top) return top.name
  }
  return keyFrames.value.map(frame => firstPresent(frame.screen_type, frame.screenType, frame.title)).find(Boolean) || '待识别'
})
const presentationSummary = computed(() => {
  const coaching = report.presentationCoaching.value || {}
  const risk = coaching.judge_risk || coaching.judgeRisk || {}
  if (coaching.summary_title || coaching.summary) {
    return {
      title: coaching.summary_title || '现场呈现复盘建议',
      summary: coaching.summary || '模型已生成现场呈现复盘建议。',
      riskLevel: risk.level ? `${risk.level}风险` : '已生成',
      goal: risk.next_rehearsal_goal || risk.nextRehearsalGoal || risk.focus || '下一轮彩排目标'
    }
  }
  if (report.presentationCoachingLoading.value) return { title: '正在生成现场呈现复盘', summary: '系统正在结合关键帧、屏幕识别和音画融合时间窗生成现场动作建议。', riskLevel: '生成中', goal: '评委视角分析' }
  if (report.presentationCoachingError.value) return { title: '现场呈现建议暂未生成', summary: report.presentationCoachingError.value, riskLevel: '待生成', goal: '模型建议不可用' }
  return { title: '先定位站位与镜头问题', summary: '模型建议生成后，会展示评委视角下的呈现问题、关键片段和下一轮彩排动作。', riskLevel: '-', goal: '站位与镜头' }
})
const contradictionItems = computed(() => report.contradictions.value.map((item, index) => ({
  id: item.id || `contradiction-${index}`,
  frame: frameNearSeconds(secondsFromContradiction(item), index),
  time: item.time || report.formatTime(secondsFromContradiction(item)),
  category: '互动',
  title: item.title || '音画不同步',
  evidence: item.description || item.summary || item.reason || '讲解内容和画面证据没有同步出现。',
  reason: item.reason || item.description || '口播内容、屏幕画面和手势指向没有形成同一证据点，评委难以快速对应。',
  fix: '切换页面前先口头预告，再用手势指向关键区域，最后补一句结果说明。',
  action: '先预告，再切屏，再指向',
  priority: index < 2 ? '高优先' : '中优先',
  riskLabel: '音画不同步',
  tone: index < 2 ? 'danger' : 'warning',
  goal: '让评委看到的画面和听到的话同步',
  source: '音画融合'
})))
const frameIssues = computed(() => {
  const frames = keyFrames.value.length ? keyFrames.value : [null, null, null, null, null, null]
  return sampleFramesAcrossTimeline(frames, 12).map((frame, index) => {
    const text = frameText(frame)
    const category = classifyPresentationIssue(text, index)
    const profile = issueProfile(category)
    const seconds = frame ? frameSeconds(frame) : 84 + index * 36
    return {
      id: `frame-issue-${firstPresent(frame?.id, frame?.backendId, index)}`,
      frame,
      time: frame?.timeLabel || report.formatTime(seconds),
      category,
      title: profile.title,
      evidence: profile.evidence(text),
      reason: profile.reason,
      fix: profile.fix,
      action: profile.action,
      priority: index === 4 || index < 3 ? '高优先' : '中优先',
      riskLabel: profile.riskLabel,
      tone: index === 4 || index < 3 ? 'danger' : 'warning',
      goal: profile.goal,
      source: '关键帧证据'
    }
  })
})
const presentationIssues = computed(() => {
  const merged = [...frameIssues.value, ...contradictionItems.value]
    .sort((a, b) => secondsFromIssue(a) - secondsFromIssue(b))
  return dedupeIssuesByTime(merged).slice(0, 16)
})
const filteredIssues = computed(() => {
  const keyword = searchKeyword.value.toLowerCase()
  return presentationIssues.value.filter(item => {
    const matchFilter = activeFilter.value === 'all' ||
      (activeFilter.value === 'position' && item.category === '站位') ||
      (activeFilter.value === 'block' && item.category === '遮挡') ||
      (activeFilter.value === 'interaction' && item.category === '互动') ||
      (activeFilter.value === 'priority' && item.priority === '高优先')
    if (!matchFilter) return false
    if (!keyword) return true
    return `${item.time} ${item.title} ${item.evidence} ${item.action}`.toLowerCase().includes(keyword)
  })
})
const selectedIssue = computed(() => presentationIssues.value.find(item => item.id === selectedIssueId.value) || filteredIssues.value[0] || presentationIssues.value[0] || null)
const selectedFrame = computed(() => selectedIssue.value?.frame || keyFrames.value[0] || null)
const selectedFrameImage = computed(() => imageUrl(selectedFrame.value))
const activeCallouts = computed(() => calloutsFor(selectedIssue.value?.category))
const issueFilters = computed(() => [
  { key: 'all', label: '全部', count: presentationIssues.value.length },
  { key: 'position', label: '站位', count: presentationIssues.value.filter(item => item.category === '站位').length },
  { key: 'block', label: '遮挡', count: presentationIssues.value.filter(item => item.category === '遮挡').length },
  { key: 'interaction', label: '互动', count: presentationIssues.value.filter(item => item.category === '互动').length },
  { key: 'priority', label: '优先', count: presentationIssues.value.filter(item => item.priority === '高优先').length }
])
const metrics = computed(() => [
  { label: '呈现总评', value: presentationSummary.value.riskLevel === '-' ? '需优化' : presentationSummary.value.riskLevel, hint: presentationSummary.value.goal, tone: 'primary' },
  { label: '画面有效率', value: `${imageEfficiency.value}%`, hint: mainScreenType.value === '待识别' ? '待识别主画面' : mainScreenType.value, tone: imageEfficiency.value >= 80 ? 'success' : 'warning' },
  { label: '站位风险', value: `${presentationIssues.value.filter(item => item.category === '站位').length}处`, hint: '队形/视线/讲者位置' },
  { label: 'PPT遮挡', value: `${presentationIssues.value.filter(item => item.category === '遮挡').length}次`, hint: '遮挡屏幕或重点区域', tone: 'warning' },
  { label: '互动覆盖', value: `${presentationIssues.value.filter(item => item.category === '互动').length}人`, hint: '评委互动与眼神覆盖' },
  { label: '下轮重点', value: trainingFocus.value, hint: '按快照验收', tone: 'success' }
])
const trainingFocus = computed(() => {
  if (presentationIssues.value.some(item => item.category === '遮挡')) return '站位与镜头'
  if (presentationIssues.value.some(item => item.category === '互动')) return '互动覆盖'
  return '站位重排'
})
const dashboardVerdict = computed(() => {
  if (presentationSummary.value.title && presentationSummary.value.title !== '等待现场呈现建议') return presentationSummary.value.title.length > 12 ? trainingFocus.value : presentationSummary.value.title
  return '先看快照，再调站位'
})
const dashboardTargets = computed(() => [
  { label: '站位', value: `${presentationIssues.value.filter(item => item.category === '站位').length}处`, hint: '目标 0 处遮挡', percent: inversePercent(presentationIssues.value.filter(item => item.category === '站位').length, 6) },
  { label: '屏幕可读性', value: `${imageEfficiency.value}%`, hint: '目标 90% 以上', percent: clamp(imageEfficiency.value) },
  { label: '互动', value: `${presentationIssues.value.filter(item => item.category === '互动').length}人`, hint: '目标覆盖评委席', percent: clamp(45 + presentationIssues.value.filter(item => item.category === '互动').length * 12) },
  { label: '镜头稳定', value: keyFrames.value.length ? `${keyFrames.value.length}帧` : '-', hint: '目标关键页清晰', percent: clamp(keyFrames.value.length ? 76 : 24) }
])
const acceptanceStandards = computed(() => {
  if (selectedIssue.value?.category === '互动') return ['讲完关键结论后看评委', '每段至少 1 次眼神覆盖', '互动问题有明确回应', '手势不遮挡画面']
  if (selectedIssue.value?.category === '遮挡') return ['讲者离屏幕边缘 1 米', '指向内容不挡核心数据', '关键页停留 3 秒', '讲完回到队形']
  return ['队员站成浅弧线', '主讲人位于画面中心侧前方', '非主讲人不分散视线', '转场前后队形稳定']
})
const rehearsalTasks = computed(() => {
  const coaching = report.presentationCoaching.value || {}
  const actions = firstArray(coaching.action_prescriptions, coaching.actionPrescriptions, coaching.actions)
  if (actions.length) return actions.slice(0, 4).map((item, index) => ({ title: item.title || `呈现动作 ${index + 1}`, detail: item.standard_action || item.standardAction || item.scenario || item.description || '模型未返回标准动作。', source: 'AI教练建议' }))
  return [
    { title: '站位重排', detail: '主讲人站在屏幕侧前方，队员站成浅弧线，避免把屏幕和产品台挡住。', source: '快照证据' },
    { title: 'PPT切换节奏', detail: '每次切换前先预告页面目的，关键页停留 3 秒，再讲数据或画面结论。', source: '屏幕可读性' },
    { title: '评委互动', detail: '讲完一段关键结论后看向评委席，保留 1 秒自然停顿，等待反馈。', source: '现场互动' },
    { title: '镜头复盘', detail: '彩排后截取 5 张关键快照，对照遮挡、站位、视线和手势逐项检查。', source: '下轮验收' }
  ]
})

watch([filteredIssues, presentationIssues], () => {
  const source = filteredIssues.value.length ? filteredIssues.value : presentationIssues.value
  if (!source.length) {
    selectedIssueId.value = ''
    return
  }
  if (!source.some(item => item.id === selectedIssueId.value)) {
    const preferred = source.find(item => item.category === '遮挡') || source[Math.min(4, source.length - 1)]
    selectedIssueId.value = preferred?.id || source[0].id
  }
  nextTick(scrollActiveIssueIntoView)
}, { immediate: true })

function selectIssue(item) {
  selectedIssueId.value = item.id
  if (item.frame) report.selectedEvidenceFrame.value = item.frame
  nextTick(scrollActiveIssueIntoView)
}

function scrollActiveIssueIntoView() {
  const list = issueListRef.value
  const active = list?.querySelector?.('.issue-row.active')
  if (!list || !active) return
  list.scrollTo({ top: Math.max(active.offsetTop - list.offsetTop - 6, 0), behavior: 'auto' })
}

function classifyPresentationIssue(text, index) {
  const value = String(text || '')
  if (/遮挡|看不清|屏幕|PPT|画面|字幕|投屏/.test(value) || index % 4 === 0) return '遮挡'
  if (/互动|评委|眼神|提问|回应|观众/.test(value) || index % 4 === 2) return '互动'
  return '站位'
}

function sampleFramesAcrossTimeline(frames, targetCount) {
  if (!Array.isArray(frames) || frames.length <= targetCount) return frames
  const sorted = [...frames].sort((a, b) => frameSeconds(a) - frameSeconds(b))
  const picked = new Map()
  const lastIndex = sorted.length - 1
  for (let i = 0; i < targetCount; i += 1) {
    const index = Math.round((lastIndex * i) / Math.max(targetCount - 1, 1))
    const frame = sorted[index]
    picked.set(frameToken(frame, index), frame)
  }
  return [...picked.values()].sort((a, b) => frameSeconds(a) - frameSeconds(b))
}

function dedupeIssuesByTime(items) {
  const result = []
  for (const item of items) {
    const seconds = secondsFromIssue(item)
    const tooClose = result.some(existing => Math.abs(secondsFromIssue(existing) - seconds) < 8 && existing.category === item.category)
    if (!tooClose) result.push(item)
  }
  return result
}

function secondsFromIssue(item) {
  if (item?.frame) return frameSeconds(item.frame)
  return secondsFromTimeLabel(item?.time)
}

function secondsFromTimeLabel(value) {
  const parts = String(value || '').split(':').map(part => Number(part))
  if (parts.some(part => !Number.isFinite(part))) return 0
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  return parts[0] || 0
}

function frameToken(frame, fallbackIndex = 0) {
  return String(firstPresent(frame?.backendId, frame?.id, frame?.frame_id, frame?.frameId, frame?.visual_frame_id, frame?.visualFrameId, imageUrl(frame), fallbackIndex))
}

function issueProfile(category) {
  const profiles = {
    遮挡: {
      title: '站位遮挡画面',
      riskLabel: '优先整改',
      goal: '让评委完整看到屏幕和产品证据',
      reason: '讲者或队员靠近屏幕中心，容易挡住 PPT 关键数据、产品展示或演示路径，评委无法同步看清证据。',
      fix: '主讲人站到屏幕侧前方，讲到关键数据时用短手势指向，不跨到屏幕正中；切页后停 3 秒再讲结论。',
      action: '侧站讲解，关键页停留',
      evidence: text => text && text !== '暂无画面说明。' ? clipText(text, 42) : '画面中讲者与屏幕距离过近，重点区域容易被遮挡。'
    },
    互动: {
      title: '评委互动不足',
      riskLabel: '互动偏弱',
      goal: '让评委感到被回应和被引导',
      reason: '讲解持续面向屏幕或稿件，缺少看评委、停顿和回应动作，现场连接感不足。',
      fix: '每讲完一个关键结论，抬头看评委席 1 秒；进入下一页前补一句“请看这个结果”。',
      action: '讲完结论看评委',
      evidence: text => text && text !== '暂无画面说明。' ? clipText(text, 42) : '该片段缺少明显的评委视线互动和现场回应。'
    },
    站位: {
      title: '队形站位分散',
      riskLabel: '队形需优化',
      goal: '让团队呈现稳定、有主次',
      reason: '队员间距和前后层次不稳定，主讲人与辅助成员的视觉主次不够清晰。',
      fix: '队员站成浅弧线，主讲人位于侧前方，非主讲人保持安静站姿，不抢画面中心。',
      action: '浅弧线站位',
      evidence: text => text && text !== '暂无画面说明。' ? clipText(text, 42) : '队员站位较分散，主讲人和屏幕之间的主次关系不清。'
    }
  }
  return profiles[category] || profiles.站位
}

function calloutsFor(category) {
  if (category === '互动') return [
    { label: '1', text: '视线偏向屏幕', x: '52%', y: '38%' },
    { label: '2', text: '评委互动不足', x: '72%', y: '58%' },
    { label: '3', text: '转场缺少停顿', x: '34%', y: '66%' }
  ]
  if (category === '遮挡') return [
    { label: '1', text: '讲者遮挡屏幕', x: '48%', y: '42%' },
    { label: '2', text: '队员站位分散', x: '68%', y: '60%' },
    { label: '3', text: '视线未面向评委', x: '32%', y: '55%' }
  ]
  return [
    { label: '1', text: '队形不够集中', x: '38%', y: '48%' },
    { label: '2', text: '主讲位置偏中', x: '56%', y: '42%' },
    { label: '3', text: '辅助成员分散', x: '72%', y: '63%' }
  ]
}

function frameText(frame) {
  return firstPresent(frame?.caption, frame?.ocr_text, frame?.ocrText, frame?.description, frame?.title, '暂无画面说明。')
}

function frameNearSeconds(seconds, fallbackIndex = 0) {
  const frames = keyFrames.value
  if (!frames.length) return null
  const nearest = frames
    .map(frame => ({ frame, distance: Math.abs(frameSeconds(frame) - seconds) }))
    .sort((a, b) => a.distance - b.distance)[0]
  return nearest?.frame || frames[Math.min(fallbackIndex, frames.length - 1)]
}

function secondsFromContradiction(item) {
  return Number(firstPresent(item.time_seconds, item.timeSeconds, item.position_seconds, item.positionSeconds, item.time_min != null ? Number(item.time_min) * 60 : undefined, item.timeMin != null ? Number(item.timeMin) * 60 : undefined, 0) || 0)
}

function frameSeconds(frame) {
  return Number(firstPresent(frame?.timestamp, frame?.time_seconds, frame?.timeSeconds, frame?.position_seconds, frame?.positionSeconds, frame?.time, 0) || 0)
}

function imageUrl(frame) {
  return firstPresent(frame?.image_url, frame?.imageUrl, frame?.frame_url, frame?.frameUrl, frame?.url, frame?.screenshot_url, frame?.screenshotUrl, '')
}

function topDistributionItem(distribution) {
  if (!distribution) return null
  if (Array.isArray(distribution)) return distribution.map(item => ({ name: item.name || item.label || item.type || item.key, value: Number(item.value ?? item.count ?? item.total ?? 0) })).filter(item => item.name).sort((a, b) => b.value - a.value)[0] || null
  if (typeof distribution === 'object') return Object.entries(distribution).map(([name, value]) => ({ name, value: Number(value || 0) })).sort((a, b) => b.value - a.value)[0] || null
  return null
}

function firstObject(...values) {
  return values.find(value => value && typeof value === 'object' && !Array.isArray(value)) || {}
}

function firstArray(...values) {
  return values.find(value => Array.isArray(value) && value.length) || []
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function clipText(value, length) {
  const text = String(value || '').replace(/\s+/g, '')
  return text.length > length ? `${text.slice(0, length)}...` : text
}

function clamp(value) {
  return Math.max(4, Math.min(100, Number(value) || 0))
}

function inversePercent(value, max) {
  return clamp(100 - (Number(value || 0) / max) * 100)
}
</script>

<style scoped>
.page-stack { display: grid; gap: 8px; min-width: 0; }
.panel-block { min-width: 0; border: 1px solid #e4dbd2; border-radius: 8px; background: #fffdfa; box-shadow: 0 8px 22px rgba(82, 61, 46, .035); }
.presentation-summary { display: grid; grid-template-columns: 1.05fr 1fr .9fr .9fr .9fr 1fr; overflow: hidden; border: 1px solid #e4dbd2; border-radius: 8px; background: #fffdfa; }
.summary-item { min-height: 56px; padding: 8px 14px; border-right: 1px solid #efe7df; }
.summary-item:last-child { border-right: 0; }
.summary-item span, .summary-item small { display: block; color: #6c7280; font-size: 11px; line-height: 1.25; }
.summary-item strong { display: block; overflow: hidden; margin: 4px 0 1px; color: #182033; font-size: 20px; line-height: 1; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
.summary-item.primary strong, .summary-item.warning strong { color: #e85d2a; }
.summary-item.success strong { color: #15835f; }
.presentation-workbench { display: grid; grid-template-columns: 300px minmax(0, 1fr) 260px; gap: 8px; align-items: start; min-width: 0; }
.issue-panel, .dashboard-panel { padding: 10px; }
.panel-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 3px 8px; margin-bottom: 8px; }
.panel-head.inline { display: flex; align-items: center; justify-content: space-between; }
.panel-head span, .diagnosis-head span { justify-self: start; padding: 2px 7px; border-radius: 999px; background: #fff0e8; color: #c6532d; font-size: 10px; font-weight: 900; }
.panel-head strong { color: #182033; font-size: 15px; line-height: 1.2; }
.panel-head em { align-self: end; color: #7b8495; font-style: normal; font-size: 11px; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
.filter-chips button { min-height: 24px; padding: 0 8px; border: 1px solid #e7ded6; border-radius: 999px; background: #fff; color: #5f6878; font-size: 10px; font-weight: 800; cursor: pointer; }
.filter-chips button.active { border-color: #e85d2a; background: #fff0e8; color: #d9532a; }
.filter-chips b { margin-left: 3px; }
.issue-search { display: grid; gap: 4px; margin-bottom: 8px; }
.issue-search span { color: #687084; font-size: 11px; font-weight: 800; }
.issue-search input { width: 100%; height: 30px; padding: 0 10px; border: 1px solid #e4d9cf; border-radius: 6px; background: #fff; color: #182033; font-size: 11px; outline: none; }
.issue-search input:focus { border-color: #e85d2a; box-shadow: 0 0 0 3px rgba(232, 93, 42, .1); }
.issue-list { display: grid; gap: 6px; max-height: 560px; overflow: auto; padding-right: 2px; }
.issue-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) 42px; gap: 6px; align-items: start; width: 100%; padding: 8px 9px; border: 1px solid #eee4dc; border-left: 3px solid #f0a12b; border-radius: 7px; background: #fff; text-align: left; cursor: pointer; }
.issue-row.danger { border-left-color: #e84c3d; }
.issue-row.active { border-color: #e85d2a; border-left-color: #e85d2a; background: #fff3ec; box-shadow: inset 0 0 0 1px rgba(232, 93, 42, .18); }
.issue-row > span { color: #e85d2a; font-size: 11px; font-weight: 950; }
.issue-row b { color: #182033; font-size: 11px; font-weight: 900; }
.issue-row p { display: -webkit-box; overflow: hidden; margin: 3px 0; color: #566174; font-size: 10px; line-height: 1.4; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.issue-row small { color: #15835f; font-size: 10px; font-weight: 800; }
.issue-row i { color: #be3d2b; font-style: normal; font-size: 9px; font-weight: 900; text-align: right; white-space: nowrap; }
.diagnosis-panel { overflow: hidden; padding: 0; background: #fff; }
.diagnosis-head { display: flex; justify-content: space-between; gap: 14px; padding: 11px 13px 8px; border-bottom: 1px solid #f0e5dc; background: linear-gradient(180deg, #fffdfb 0%, #fff8f3 100%); }
.diagnosis-head h2 { margin: 4px 0 2px; color: #182033; font-size: 19px; line-height: 1.1; }
.diagnosis-head p { margin: 0; color: #667085; font-size: 11px; line-height: 1.35; }
.diagnosis-head strong { align-self: start; padding: 4px 8px; border-radius: 999px; background: #ffe2d5; color: #be3d2b; font-size: 11px; white-space: nowrap; }
.snapshot-stage { position: relative; display: grid; place-items: center; aspect-ratio: 32 / 17; min-height: 420px; max-height: 560px; margin: 10px 12px 10px; overflow: hidden; border: 1px solid #ebe2d9; border-radius: 7px; background: #111827; }
.snapshot-stage img { display: block; width: 100%; height: 100%; object-fit: contain; object-position: center; background: #111827; }
.snapshot-shade { position: absolute; inset: 0; pointer-events: none; background: linear-gradient(180deg, rgba(24,32,51,.02), rgba(24,32,51,.12)); }
.snapshot-placeholder { display: grid; place-items: center; gap: 6px; color: #7b8495; text-align: center; }
.snapshot-placeholder span { color: #182033; font-size: 18px; font-weight: 900; }
.snapshot-placeholder p { margin: 0; font-size: 12px; }
.callout-dot { position: absolute; z-index: 2; display: flex; align-items: center; gap: 5px; max-width: 150px; padding: 4px 7px 4px 4px; border: 1px solid rgba(255,255,255,.82); border-radius: 999px; background: rgba(232, 93, 42, .94); color: #fff; font-size: 10px; font-weight: 900; box-shadow: 0 8px 18px rgba(22, 27, 37, .2); transform: translate(-50%, -50%); }
.callout-dot b { display: grid; place-items: center; width: 18px; height: 18px; border-radius: 999px; background: #fff; color: #e85d2a; font-size: 11px; }
.callout-dot span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.diagnosis-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; padding: 0 12px 8px; }
.diagnosis-grid article { min-height: 94px; padding: 10px 11px; border: 1px solid #ebe2d9; border-radius: 7px; background: #fffdfa; }
.diagnosis-grid h3, .pass-line h3 { margin: 0 0 7px; color: #182033; font-size: 13px; }
.diagnosis-grid p { display: -webkit-box; overflow: hidden; margin: 0; color: #4d596b; font-size: 12px; line-height: 1.6; -webkit-line-clamp: 4; -webkit-box-orient: vertical; }
.acceptance-line { display: flex; align-items: flex-start; gap: 12px; margin: 0 12px 10px; padding: 9px 10px; border: 1px solid #ebe2d9; border-radius: 7px; background: #fff; }
.acceptance-line span { flex: 0 0 auto; color: #8a604c; font-size: 11px; font-weight: 900; }
.acceptance-line ul, .pass-line ul { display: flex; flex-wrap: wrap; gap: 7px 12px; margin: 0; padding: 0; list-style: none; color: #344054; font-size: 11px; }
.acceptance-line li::before, .pass-line li::before { content: '✓'; margin-right: 5px; color: #15835f; font-weight: 900; }
.dashboard-panel { display: grid; gap: 8px; }
.target-bars { display: grid; gap: 7px; }
.target-bars article { padding: 8px 9px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.target-bars div { display: flex; justify-content: space-between; gap: 8px; color: #182033; font-size: 11px; font-weight: 900; }
.target-bars i { display: block; height: 5px; margin: 7px 0 4px; overflow: hidden; border-radius: 999px; background: #e9edf4; }
.target-bars em { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #e85d2a, #f2a12b); }
.target-bars small { color: #7b8495; font-size: 10px; }
.pass-line { padding: 9px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.pass-line ul { display: grid; gap: 5px; }
.plan-button { min-height: 30px; padding: 0 11px; border: 1px solid #e85d2a; border-radius: 5px; background: #e85d2a; color: #fff; font-size: 11px; font-weight: 900; box-shadow: 0 6px 14px rgba(232, 93, 42, .18); cursor: pointer; }
.plan-button:disabled { opacity: .65; cursor: not-allowed; }
.next-training { padding: 11px 12px; }
.task-list { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.task-list article { padding: 11px 12px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.task-list div { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.task-list b { color: #182033; font-size: 13px; }
.task-list span { padding: 2px 6px; border-radius: 999px; background: #f5f7fb; color: #667085; font-size: 10px; font-weight: 850; white-space: nowrap; }
.task-list p { display: -webkit-box; overflow: hidden; min-height: 48px; margin: 8px 0; color: #566174; font-size: 12px; line-height: 1.45; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
.task-list small { color: #15835f; font-size: 11px; font-weight: 850; }
@media (max-width: 1280px) {
  .presentation-workbench { grid-template-columns: 290px minmax(0, 1fr); }
  .dashboard-panel { grid-column: 1 / -1; grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .presentation-summary, .presentation-workbench, .diagnosis-grid, .task-list, .dashboard-panel { grid-template-columns: 1fr; }
  .acceptance-line { display: grid; }
  .snapshot-stage { min-height: 240px; max-height: none; }
}
</style>
