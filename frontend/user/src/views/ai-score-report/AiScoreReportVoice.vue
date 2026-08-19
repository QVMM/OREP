<template>
  <AiScoreReportShell title="表达节奏" subtitle="把问题句改成可训练话术">
    <div class="page-stack">
      <section class="voice-summary" aria-label="表达训练关键指标">
        <article v-for="metric in metrics" :key="metric.label" :class="['summary-item', metric.tone]">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="training-workbench">
        <aside class="queue-panel panel-block">
          <div class="panel-head">
            <span>训练队列</span>
            <strong>优先处理的问题句</strong>
            <em>{{ filteredProblemItems.length }}/{{ problemItems.length }} 条</em>
          </div>

          <div class="filter-chips" aria-label="表达问题筛选">
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

          <label class="queue-search">
            <span>搜索训练句</span>
            <input v-model.trim="searchKeyword" type="search" placeholder="搜索时间、问题句或训练动作" />
          </label>

          <div v-if="filteredProblemItems.length" ref="queueListRef" class="queue-list">
            <button
              v-for="(item, index) in filteredProblemItems"
              :key="item.id"
              type="button"
              :class="['queue-row', item.tone, { active: item.id === selectedProblemId }]"
              @click="selectProblem(item)"
            >
              <span>#{{ index + 1 }}</span>
              <div>
                <b>{{ item.time }} · {{ item.title }}</b>
                <p>{{ item.context }}</p>
                <small>{{ item.objective }}</small>
              </div>
              <i>{{ item.priority }}</i>
            </button>
          </div>
          <AiScoreEmptyState v-else title="暂无匹配问题句" description="可切换筛选条件，或等待表达节奏建议生成。" />
        </aside>

        <main class="prescription-panel panel-block">
          <header class="prescription-head">
            <div>
              <span>训练处方</span>
              <h2>{{ selectedProblem?.time || '--:--' }} · {{ selectedProblem?.title || '问题句训练' }}</h2>
              <p>{{ selectedProblem?.priority || '待训练' }} · {{ selectedProblem?.objective || '选择左侧问题句开始训练' }}</p>
            </div>
            <strong>{{ selectedProblem?.riskLabel || '待练' }}</strong>
          </header>

          <div class="diagnosis-strip">
            <span v-for="tag in diagnosisTags" :key="tag">{{ tag }}</span>
          </div>

          <section class="rewrite-board">
            <article class="original-sentence">
              <h3>原句</h3>
              <p>{{ selectedProblem?.fullText || selectedProblem?.context || '请选择左侧问题句。' }}</p>
            </article>
            <article class="suggested-sentence">
              <h3>建议话术</h3>
              <ol>
                <li v-for="line in rewriteLines" :key="line">{{ line }}</li>
              </ol>
            </article>
          </section>

          <section class="rhythm-guide">
            <div class="guide-head">
              <span>朗读节奏</span>
              <b>20 秒内完成，保留 2 个自然停顿</b>
            </div>
            <div class="rhythm-track">
              <mark>起句 0-5秒</mark>
              <mark>停顿1秒</mark>
              <mark>证据 6-14秒</mark>
              <mark>停顿1秒</mark>
              <mark>收束 15-20秒</mark>
            </div>
          </section>

          <section class="acceptance-box">
            <div>
              <span>本句验收标准</span>
              <ul>
                <li>单句不超过 20 秒</li>
                <li>中间至少 1 次自然停顿</li>
                <li>不出现“那么”“呢”等填充词</li>
              </ul>
            </div>
            <div class="prescription-actions">
              <button type="button" class="primary" @click="addTrainingTask">加入训练清单</button>
              <button type="button" @click="copyRewrite">复制建议话术</button>
              <RouterLink :to="report.sectionPath('evidence')">查看证据快照</RouterLink>
            </div>
          </section>
        </main>

        <aside class="coach-dashboard panel-block" :class="{ warning: report.expressionCoachingError.value }">
          <div class="panel-head compact">
            <span>训练仪表盘</span>
            <strong>{{ coachVerdict }}</strong>
          </div>

          <div class="target-bars">
            <article v-for="target in coachTargets" :key="target.label">
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
              <li>平均语速 220-240 字/分钟</li>
              <li>单次停顿不超过 5 秒</li>
              <li>每分钟填充词不超过 1 次</li>
              <li>重点句能在 20 秒内讲完</li>
            </ul>
          </section>

          <button
            type="button"
            class="plan-button"
            :disabled="report.expressionCoachingLoading.value || !report.effectiveMeetingId.value"
            @click="report.loadExpressionCoaching(true)"
          >
            {{ report.expressionCoachingLoading.value ? '生成中' : '生成表达训练计划' }}
          </button>
        </aside>
      </section>

      <section class="next-training panel-block">
        <div class="panel-head inline">
          <div>
            <span>下一轮训练任务</span>
            <strong>从问题句到可验收动作</strong>
          </div>
          <em>{{ trainingItems.length }} 项</em>
        </div>

        <div class="task-list">
          <article v-for="item in trainingItems" :key="item.title">
            <div>
              <b>{{ item.title }}</b>
              <span>待训练</span>
            </div>
            <p>{{ item.detail }}</p>
            <small>{{ item.source }}</small>
          </article>
        </div>
      </section>
    </div>
  </AiScoreReportShell>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiScoreReportShell from '../../components/ai-score/report/AiScoreReportShell.vue'
import AiScoreEmptyState from '../../components/ai-score/report/AiScoreEmptyState.vue'
import { useAiScoreReportContext } from '../../composables/useAiScoreReport'

const report = useAiScoreReportContext()

const selectedProblemId = ref('')
const activeFilter = ref('all')
const searchKeyword = ref('')
const manualTrainingCount = ref(0)
const queueListRef = ref(null)

const speechRateNumber = computed(() => Number(report.speech.value.speech_rate?.global_chars_per_minute || 0))
const speechRate = computed(() => speechRateNumber.value ? `${report.formatNumber(speechRateNumber.value, 1)} 字/分钟` : '-')
const speechIdeal = computed(() => report.speech.value.speech_rate?.ideal_range || '220-240 字/分钟')
const severePauseCount = computed(() => {
  const severe = report.topPauses.value.filter(item => String(item.severity || '').includes('严重')).length
  return severe || report.topPauses.value.filter(item => Number(item.duration || 0) >= 5).length
})
const fillerRate = computed(() => {
  const value = report.speech.value.fillers?.filler_rate_percent
  return value === undefined || value === null || value === '' ? '-' : `${report.formatNumber(value, 2)}%`
})
const recoverableScore = computed(() => firstPresent(
  report.scoreRecoverySummary.value.voice_recoverable,
  report.scoreRecoverySummary.value.voiceRecoverable,
  report.scoreRecoverySummary.value.expression_recoverable,
  report.scoreRecoverySummary.value.expressionRecoverable,
  report.scoreRecoverySummary.value.recoverable_range,
  report.scoreRecoverySummary.value.recoverableRange
) ?? '待测算')
const longestPauseText = computed(() => report.longestPause.value === '0.0' ? '-' : `${report.longestPause.value}s`)
const coachVerdict = computed(() => {
  const title = report.expressionCoaching.value?.summary_title
  if (title) return title.length > 16 ? '先压长句，再控停顿' : title
  if (speechRateNumber.value > 250 && severePauseCount.value) return '先压长句，再控停顿'
  if (report.fillerTotal.value) return '先替换口头禅'
  return '先建立表达节奏'
})
const expressionStability = computed(() => {
  if (speechRateNumber.value > 250 && severePauseCount.value) return '偏快且断裂'
  if (speechRateNumber.value > 250) return '语速偏快'
  if (severePauseCount.value) return '停顿偏多'
  return report.speech.value.speech_rate?.global_rating || '待评估'
})

const pauseItems = computed(() => report.topPauses.value.map((pause, index) => {
  const duration = Number(pause.duration || 0)
  return {
    id: `pause-${index}`,
    category: 'pause',
    time: report.formatTime(firstPresent(pause.position_seconds, pause.positionSeconds, pause.timestamp, pause.time) || 0),
    title: '停顿预演训练',
    fullText: clipEmpty(`${pause.context_before || ''} ${pause.context_after || ''}`),
    context: report.clipText(clipEmpty(`${pause.context_before || ''} ${pause.context_after || ''}`), 88),
    objective: '目标：把空档改成过渡话术',
    action: '用“下面进入下一步”承接操作间隙。',
    priority: duration >= 8 ? '高优先' : '中优先',
    riskLabel: duration >= 8 ? '严重停顿' : '长停顿',
    tone: duration >= 8 ? 'danger' : 'warning',
    seconds: firstPresent(pause.position_seconds, pause.positionSeconds, pause.timestamp, pause.time) || 0
  }
}))
const transcriptProblems = computed(() => report.asrSegments.value
  .map((segment, index) => ({ segment, index, text: firstPresent(segment.text, segment.transcript, segment.content, '') }))
  .filter(item => item.text && (item.text.length > 72 || /那么|呢|然后|就是|嗯|啊|这个|那个/.test(item.text)))
  .slice(0, 10)
  .map(({ segment, index, text }) => {
    const hasFiller = /那么|呢|然后|就是|嗯|啊|这个|那个/.test(text)
    const isLong = text.length > 72
    return {
      id: `asr-${index}`,
      category: hasFiller && !isLong ? 'filler' : 'long',
      time: report.formatTime(firstPresent(segment.start, segment.start_seconds, segment.startSeconds, segment.timestamp, segment.time) || index * 30),
      title: isLong ? '长句压缩训练' : '填充词替换训练',
      fullText: text,
      context: report.clipText(text, 88),
      objective: isLong ? '目标：拆成2句，先结论后证据' : '目标：替换“那么/呢”',
      action: isLong ? '拆成两句：先结论，再证据。' : '替换为“接下来”“具体来说”，或直接删除。',
      priority: index < 4 ? '高优先' : '中优先',
      riskLabel: isLong ? '句子过长' : '填充词集中',
      tone: index < 4 ? 'danger' : 'warning',
      seconds: firstPresent(segment.start, segment.start_seconds, segment.startSeconds, segment.timestamp, segment.time) || index * 30
    }
  }))
const problemItems = computed(() => [...transcriptProblems.value, ...pauseItems.value]
  .sort((a, b) => priorityWeight(b) - priorityWeight(a) || Number(a.seconds || 0) - Number(b.seconds || 0))
  .slice(0, 12))
const filteredProblemItems = computed(() => {
  const keyword = searchKeyword.value.toLowerCase()
  return problemItems.value.filter(item => {
    const matchFilter = activeFilter.value === 'all' ||
      (activeFilter.value === 'long' && item.category === 'long') ||
      (activeFilter.value === 'pause' && item.category === 'pause') ||
      (activeFilter.value === 'filler' && item.category === 'filler') ||
      (activeFilter.value === 'priority' && item.priority === '高优先')
    if (!matchFilter) return false
    if (!keyword) return true
    return `${item.time} ${item.title} ${item.context} ${item.objective}`.toLowerCase().includes(keyword)
  })
})
const selectedProblem = computed(() => problemItems.value.find(item => item.id === selectedProblemId.value) || filteredProblemItems.value[0] || problemItems.value[0] || null)
const filters = computed(() => [
  { key: 'all', label: '全部', count: problemItems.value.length },
  { key: 'long', label: '长句', count: problemItems.value.filter(item => item.category === 'long').length },
  { key: 'pause', label: '停顿', count: problemItems.value.filter(item => item.category === 'pause').length },
  { key: 'filler', label: '口头禅', count: report.fillerTotal.value || problemItems.value.filter(item => item.category === 'filler').length },
  { key: 'priority', label: '优先', count: problemItems.value.filter(item => item.priority === '高优先').length }
])
const metrics = computed(() => [
  { label: '今日训练重点', value: trainingFocus.value, hint: `先处理 ${problemItems.value.length || 0} 条问题句`, tone: 'primary' },
  { label: '平均语速', value: speechRate.value, hint: `建议 ${speechIdeal.value}` },
  { label: '严重停顿', value: `${severePauseCount.value} 处`, hint: `最长 ${longestPauseText.value}`, tone: severePauseCount.value ? 'warning' : 'success' },
  { label: '口头禅', value: `${report.fillerTotal.value || 0} 次`, hint: fillerRate.value === '-' ? '占比待生成' : `占比 ${fillerRate.value}`, tone: report.fillerTotal.value ? 'warning' : '' },
  { label: '训练完成度', value: `${manualTrainingCount.value}/4`, hint: manualTrainingCount.value ? '进行中' : '待开始' },
  { label: '验收目标', value: '语速稳定', hint: '停顿 ≤5秒', tone: 'success' }
])
const trainingFocus = computed(() => {
  if (transcriptProblems.value.some(item => item.category === 'long')) return '长句压缩'
  if (severePauseCount.value) return '停顿预演'
  if (report.fillerTotal.value) return '口头禅替换'
  return '表达校准'
})
const diagnosisTags = computed(() => {
  const item = selectedProblem.value
  if (!item) return ['待选择问题句']
  if (item.category === 'pause') return ['停顿过长', '转场空档', '需要过渡话术', '易影响连贯性']
  if (item.category === 'filler') return ['填充词集中', '表达不够干净', '需要替换连接词', '影响专业感']
  return ['句子过长', '信息密度高', '缺少停顿点', '易影响评委理解']
})
const rewriteLines = computed(() => {
  const item = selectedProblem.value
  if (!item) return ['请选择左侧问题句后生成训练话术。']
  if (item.category === 'pause') return [
    '下面进入关键操作演示，我先说明目标。',
    '完成这一步后，我们再看数据或画面证据。'
  ]
  if (item.category === 'filler') return [
    '接下来，我用一个具体结果说明项目价值。',
    '具体来说，这一步解决的是评委最关心的落地问题。'
  ]
  return rewriteLongSentence(item.fullText || item.context)
})
const coachTargets = computed(() => [
  { label: '语速', value: speechRate.value, hint: '目标 240 内', percent: clamp((240 / Math.max(240, speechRateNumber.value || 240)) * 100) },
  { label: '停顿', value: longestPauseText.value, hint: '目标 ≤5秒', percent: clamp((5 / Math.max(5, Number(report.longestPause.value || 0))) * 100) },
  { label: '口头禅', value: `${report.fillerTotal.value || 0} 次`, hint: '目标 ≤20次', percent: clamp((20 / Math.max(20, Number(report.fillerTotal.value || 0))) * 100) },
  { label: '训练任务', value: `${manualTrainingCount.value}/4`, hint: '完成 4 项', percent: clamp((manualTrainingCount.value / 4) * 100) }
])
const trainingItems = computed(() => {
  const training = report.expressionCoaching.value?.training || []
  const sourceItems = training.length
    ? training.map((item, index) => ({ title: item.title || `训练 ${index + 1}`, detail: item.detail || item.description || item.action || '模型未返回训练细节。', source: 'AI教练建议' }))
    : [
        { title: '长句压缩', detail: '把前 4 条高优先问题句改写成“结论、证据、收束”三段话术。', source: '问题句训练' },
        { title: '停顿预演', detail: '每个操作空档准备一句过渡话术，彩排时单次停顿不超过 5 秒。', source: '停顿检测' },
        { title: '填充词替换', detail: '把“那么、呢、然后”替换为“接下来、具体来说、因此”。', source: '口头禅统计' },
        { title: '时间补足', detail: '补齐缺失演示环节，重新分配每段讲解时长，保证总时长达标。', source: '训练规划' }
      ]
  return sourceItems.slice(0, 4)
})

watch([filteredProblemItems, problemItems], () => {
  const source = filteredProblemItems.value.length ? filteredProblemItems.value : problemItems.value
  if (!source.length) {
    selectedProblemId.value = ''
    return
  }
  if (!source.some(item => item.id === selectedProblemId.value)) {
    const fillerItem = source.find(item => item.category === 'filler')
    selectedProblemId.value = fillerItem?.id || source[0].id
  }
  nextTick(scrollActiveProblemIntoView)
}, { immediate: true })

function selectProblem(item) {
  selectedProblemId.value = item.id
  nextTick(scrollActiveProblemIntoView)
}

function addTrainingTask() {
  manualTrainingCount.value = Math.min(4, manualTrainingCount.value + 1)
  ElMessage.success('已加入表达训练清单')
}

async function copyRewrite() {
  await navigator.clipboard?.writeText?.(rewriteLines.value.join('\n'))
  ElMessage.success('建议话术已复制')
}

function rewriteLongSentence(text) {
  const clean = String(text || '').replace(/\s+/g, '')
  if (!clean) return ['请先给这句话补充明确结论。', '再用一个证据说明为什么成立。']
  const first = report.clipText(clean, 34)
  const secondSource = clean.slice(34)
  const second = secondSource ? report.clipText(secondSource, 42) : '然后用数据、画面或操作结果补充证据。'
  return [
    `先说结论：${first}`,
    `再给证据：${second}`,
    '最后收束：这就是本环节对项目落地的支撑。'
  ]
}

function priorityWeight(item) {
  return item.priority === '高优先' ? 2 : 1
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '')
}

function clipEmpty(text) {
  const value = String(text || '').replace(/^\s*\/\s*$/, '').trim()
  return value || '报告未返回该停顿片段的上下文。'
}

function clamp(value) {
  return Math.max(4, Math.min(100, Number(value) || 0))
}

function scrollActiveProblemIntoView() {
  const list = queueListRef.value
  const active = list?.querySelector?.('.queue-row.active')
  if (!list || !active) return
  list.scrollTo({ top: Math.max(active.offsetTop - 6, 0), behavior: 'auto' })
}
</script>

<style scoped>
.page-stack { display: grid; gap: 8px; min-width: 0; }
.panel-block { min-width: 0; border: 1px solid #e4dbd2; border-radius: 8px; background: #fffdfa; box-shadow: 0 8px 22px rgba(82, 61, 46, .035); }
.voice-summary { display: grid; grid-template-columns: 1.2fr 1fr .95fr .95fr .95fr .95fr; overflow: hidden; border: 1px solid #e4dbd2; border-radius: 8px; background: #fffdfa; }
.summary-item { min-height: 56px; padding: 8px 14px; border-right: 1px solid #efe7df; }
.summary-item:last-child { border-right: 0; }
.summary-item span, .summary-item small { display: block; color: #6c7280; font-size: 11px; line-height: 1.25; }
.summary-item strong { display: block; overflow: hidden; margin: 4px 0 1px; color: #182033; font-size: 20px; line-height: 1; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
.summary-item.primary strong, .summary-item.warning strong { color: #e85d2a; }
.summary-item.success strong { color: #15835f; }
.training-workbench { display: grid; grid-template-columns: 288px minmax(0, 1fr) 240px; gap: 8px; align-items: start; min-width: 0; }
.queue-panel, .coach-dashboard { padding: 10px; }
.panel-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 3px 8px; margin-bottom: 8px; }
.panel-head.inline { display: flex; align-items: center; justify-content: space-between; }
.panel-head span, .prescription-head span { justify-self: start; padding: 2px 7px; border-radius: 999px; background: #fff0e8; color: #c6532d; font-size: 10px; font-weight: 900; }
.panel-head strong { color: #182033; font-size: 15px; line-height: 1.2; }
.panel-head em { align-self: end; color: #7b8495; font-style: normal; font-size: 11px; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
.filter-chips button { min-height: 24px; padding: 0 8px; border: 1px solid #e7ded6; border-radius: 999px; background: #fff; color: #5f6878; font-size: 10px; font-weight: 800; cursor: pointer; }
.filter-chips button.active { border-color: #e85d2a; background: #fff0e8; color: #d9532a; }
.filter-chips b { margin-left: 3px; }
.queue-search { display: grid; gap: 4px; margin-bottom: 8px; }
.queue-search span { color: #687084; font-size: 11px; font-weight: 800; }
.queue-search input { width: 100%; height: 30px; padding: 0 10px; border: 1px solid #e4d9cf; border-radius: 6px; background: #fff; color: #182033; font-size: 11px; outline: none; }
.queue-search input:focus { border-color: #e85d2a; box-shadow: 0 0 0 3px rgba(232, 93, 42, .1); }
.queue-list { display: grid; gap: 6px; max-height: 520px; overflow: auto; padding-right: 2px; }
.queue-row { display: grid; grid-template-columns: 34px minmax(0, 1fr) 42px; gap: 6px; align-items: start; width: 100%; padding: 8px 9px; border: 1px solid #eee4dc; border-left: 3px solid #f0a12b; border-radius: 7px; background: #fff; text-align: left; cursor: pointer; }
.queue-row.danger { border-left-color: #e84c3d; }
.queue-row.active { border-color: #e85d2a; border-left-color: #e85d2a; background: #fff3ec; box-shadow: inset 0 0 0 1px rgba(232, 93, 42, .18); }
.queue-row > span { color: #e85d2a; font-size: 11px; font-weight: 950; }
.queue-row b { color: #182033; font-size: 11px; font-weight: 900; }
.queue-row p { display: -webkit-box; overflow: hidden; margin: 3px 0; color: #566174; font-size: 10px; line-height: 1.4; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.queue-row small { color: #15835f; font-size: 10px; font-weight: 800; }
.queue-row i { color: #be3d2b; font-style: normal; font-size: 9px; font-weight: 900; text-align: right; white-space: nowrap; }
.prescription-panel { overflow: hidden; padding: 0; background: #fff; }
.prescription-head { display: flex; justify-content: space-between; gap: 14px; padding: 11px 13px 8px; border-bottom: 1px solid #f0e5dc; background: linear-gradient(180deg, #fffdfb 0%, #fff8f3 100%); }
.prescription-head h2 { margin: 4px 0 2px; color: #182033; font-size: 19px; line-height: 1.1; }
.prescription-head p { margin: 0; color: #667085; font-size: 11px; line-height: 1.35; }
.prescription-head strong { align-self: start; padding: 4px 8px; border-radius: 999px; background: #ffe2d5; color: #be3d2b; font-size: 11px; white-space: nowrap; }
.diagnosis-strip { display: flex; flex-wrap: wrap; gap: 5px; padding: 9px 12px 0; }
.diagnosis-strip span { padding: 3px 8px; border-radius: 999px; background: #f5f7fb; color: #5f6878; font-size: 10px; font-weight: 850; }
.rewrite-board { display: grid; grid-template-columns: minmax(0, .95fr) minmax(0, 1.05fr); gap: 8px; padding: 9px 12px; }
.rewrite-board article { min-height: 165px; padding: 11px; border: 1px solid #ebe2d9; border-radius: 7px; }
.original-sentence { background: #fbf7f3; }
.suggested-sentence { background: #fffdfb; }
.rewrite-board h3, .pass-line h3 { margin: 0 0 8px; color: #182033; font-size: 13px; }
.rewrite-board p { display: -webkit-box; overflow: hidden; margin: 0; color: #4d596b; font-size: 12px; line-height: 1.65; -webkit-line-clamp: 6; -webkit-box-orient: vertical; }
.rewrite-board ol { display: grid; gap: 7px; margin: 0; padding-left: 19px; color: #263142; font-size: 12px; line-height: 1.6; font-weight: 750; }
.suggested-sentence li::marker { color: #e85d2a; font-weight: 900; }
.rhythm-guide { margin: 0 12px 8px; padding: 9px 10px; border: 1px solid #ebe2d9; border-radius: 7px; background: #fffdfa; }
.guide-head { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 8px; color: #6b7280; font-size: 11px; font-weight: 850; }
.guide-head span { color: #8a604c; }
.rhythm-track { display: grid; grid-template-columns: 1.1fr .75fr 1.35fr .75fr 1fr; overflow: hidden; border-radius: 999px; background: #eef2f6; }
.rhythm-track mark { padding: 6px 8px; background: transparent; color: #4d596b; font-size: 10px; font-weight: 850; text-align: center; }
.rhythm-track mark:nth-child(odd) { background: #ffe9df; color: #be3d2b; }
.acceptance-box { display: flex; justify-content: space-between; gap: 10px; margin: 0 12px 10px; padding: 9px 10px; border: 1px solid #ebe2d9; border-radius: 7px; background: #fff; }
.acceptance-box span { color: #8a604c; font-size: 11px; font-weight: 900; }
.acceptance-box ul, .pass-line ul { display: grid; gap: 5px; margin: 6px 0 0; padding: 0; list-style: none; color: #344054; font-size: 11px; }
.acceptance-box li::before, .pass-line li::before { content: '✓'; margin-right: 6px; color: #15835f; font-weight: 900; }
.prescription-actions { display: flex; flex-wrap: wrap; gap: 7px; align-content: start; justify-content: flex-end; min-width: 230px; }
.prescription-actions button, .prescription-actions a, .plan-button { min-height: 28px; padding: 0 10px; border: 1px solid #dfcfc2; border-radius: 5px; background: #fff; color: #be3d2b; text-decoration: none; font-size: 10px; font-weight: 900; cursor: pointer; }
.prescription-actions .primary, .plan-button { border-color: #e85d2a; background: #e85d2a; color: #fff; box-shadow: 0 6px 14px rgba(232, 93, 42, .18); }
.coach-dashboard { display: grid; gap: 8px; }
.coach-dashboard.warning { border-color: #ffd7bd; background: #fffaf6; }
.target-bars { display: grid; gap: 7px; }
.target-bars article { padding: 8px 9px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
.target-bars div { display: flex; justify-content: space-between; gap: 8px; color: #182033; font-size: 11px; font-weight: 900; }
.target-bars i { display: block; height: 5px; margin: 7px 0 4px; overflow: hidden; border-radius: 999px; background: #e9edf4; }
.target-bars em { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #e85d2a, #f2a12b); }
.target-bars small { color: #7b8495; font-size: 10px; }
.pass-line { padding: 9px; border: 1px solid #eee4dc; border-radius: 7px; background: #fff; }
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
  .training-workbench { grid-template-columns: 310px minmax(0, 1fr); }
  .coach-dashboard { grid-column: 1 / -1; grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .voice-summary, .training-workbench, .rewrite-board, .task-list, .coach-dashboard { grid-template-columns: 1fr; }
  .acceptance-box { display: grid; }
  .prescription-actions { justify-content: flex-start; min-width: 0; }
  .rhythm-track { grid-template-columns: 1fr; border-radius: 7px; }
}
</style>
