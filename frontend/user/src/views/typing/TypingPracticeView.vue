<template>
  <AiAppShell mode="landing" width="wide" class="typing-home">
    <template #header>
      <AiAppHeader
        app="typing"
        mode="landing"
        title="AI 智能打字"
        subtitle="练速度 · 提正确率 · 冲组织排位"
        back-label="AI 应用中心"
        back-to="/ai-apps"
      />
    </template>

    <div class="th">
      <p class="th-summary" aria-label="今日概况">
        <span>{{ todaySummaryLine }}</span>
        <i aria-hidden="true">·</i>
        <span>排名 {{ myBoardLine }}</span>
        <template v-if="insightAvgCpm">
          <i aria-hidden="true">·</i>
          <span>近均 {{ insightAvgCpm }} CPM</span>
        </template>
      </p>

      <!-- 历史洞察：趋势 + 均速 + 最近记录 -->
      <TypingInsightsPanel
        :stats="insightStats"
        :local-trend="localTrend"
        :local-sessions="localSessions"
      />

      <div class="th-layout">
        <!-- 主设置 -->
        <section class="th-card th-setup" aria-label="开始练习">
          <div class="th-seg" role="tablist" aria-label="模式">
            <button
              type="button"
              role="tab"
              :class="{ 'is-active': playMode === 'practice' }"
              :aria-selected="playMode === 'practice'"
              @click="playMode = 'practice'"
            >自主练习</button>
            <button
              type="button"
              role="tab"
              :class="{ 'is-active': playMode === 'code' }"
              :aria-selected="playMode === 'code'"
              @click="playMode = 'code'"
            >代码练习</button>
            <button
              type="button"
              role="tab"
              :class="{ 'is-active': playMode === 'ranked' }"
              :aria-selected="playMode === 'ranked'"
              @click="playMode = 'ranked'"
            >排位赛</button>
          </div>

          <template v-if="playMode === 'practice'">
            <div class="th-block">
              <span class="th-label">时长</span>
              <div class="th-chips" role="group" aria-label="练习时长">
                <button
                  v-for="opt in DURATION_CHIPS"
                  :key="opt.label"
                  type="button"
                  class="th-chip"
                  :class="{ 'is-active': isDurationActive(opt) }"
                  @click="selectDuration(opt)"
                >{{ opt.short }}</button>
              </div>
              <div v-if="prefs.useCustomDuration || prefs.durationSec === 0" class="th-custom-min">
                <label>
                  自定义
                  <input v-model.number="prefs.customMinutes" type="number" min="1" max="60" step="1" />
                  分钟
                </label>
              </div>
            </div>

            <div class="th-block th-block--row">
              <label class="th-field">
                <span class="th-label">语言</span>
                <select v-model="prefs.lang" class="th-select">
                  <option v-for="opt in LANG_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </label>
              <label class="th-field">
                <span class="th-label">难度</span>
                <select v-model.number="prefs.difficulty" class="th-select">
                  <option v-for="opt in DIFFICULTY_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                </select>
              </label>
            </div>

            <div class="th-block">
              <div class="th-block__head">
                <span class="th-label">练习文案</span>
                <div class="th-text-mode">
                  <button
                    type="button"
                    :class="{ 'is-active': !useCustomText }"
                    @click="useCustomText = false"
                  >系统文案</button>
                  <button
                    type="button"
                    :class="{ 'is-active': useCustomText }"
                    @click="useCustomText = true"
                  >自定义</button>
                </div>
              </div>

              <template v-if="useCustomText">
                <textarea
                  v-model="customText"
                  class="th-textarea"
                  :class="{ 'is-code-paste': looksLikeCodePaste }"
                  rows="6"
                  maxlength="20000"
                  spellcheck="false"
                  placeholder="粘贴要练习的文字或代码…支持换行与缩进（代码会自动用等宽显示）"
                />
                <p v-if="looksLikeCodePaste" class="th-hint th-hint--code">
                  已识别为代码：建议切到「代码练习」获得语法高亮与规范提示；此处也会保留换行缩进。
                </p>
                <div class="th-custom-bar">
                  <input
                    v-model="customTitle"
                    type="text"
                    class="th-title-input"
                    maxlength="120"
                    placeholder="文案标题（可选）"
                  />
                  <button
                    type="button"
                    class="th-btn th-btn--ghost"
                    :disabled="customSaving || !customText.trim()"
                    @click="saveCustomToAccount"
                  >{{ customSaving ? '保存中…' : (editingCustomId ? '更新到账户' : '保存到账户') }}</button>
                  <button
                    v-if="editingCustomId"
                    type="button"
                    class="th-btn th-btn--ghost"
                    :disabled="customSaving"
                    @click="clearCustomSelection"
                  >另存为新</button>
                </div>

                <div v-if="customTexts.length" class="th-saved">
                  <span class="th-label">已保存的文案</span>
                  <ul class="th-saved__list">
                    <li
                      v-for="item in customTexts"
                      :key="item.id"
                      :class="{ 'is-active': editingCustomId === item.id }"
                    >
                      <button type="button" class="th-saved__main" @click="applyCustomText(item)">
                        <strong>{{ item.title || '未命名' }}</strong>
                        <span>{{ item.charCount || (item.content || '').length }} 字</span>
                      </button>
                      <button type="button" class="th-saved__del" title="删除" @click="removeCustomText(item)">×</button>
                    </li>
                  </ul>
                </div>
                <p v-else-if="customLoaded && !customTexts.length" class="th-hint">
                  还没有保存过文案。写好后点「保存到账户」，换设备登录也能用。
                </p>
                <p v-if="customError" class="th-error">{{ customError }}</p>
              </template>
              <p v-else class="th-hint">将按语言与难度自动抽取系统练习文案。</p>
            </div>
          </template>

          <template v-else-if="playMode === 'code'">
            <p class="th-code-lead">
              像写代码一样练：语法高亮 · 行号 · 自动跳过行首缩进 · 行内空格仍需敲
            </p>

            <div class="th-block">
              <span class="th-label">时长</span>
              <div class="th-chips" role="group" aria-label="练习时长">
                <button
                  v-for="opt in DURATION_CHIPS"
                  :key="`code-${opt.label}`"
                  type="button"
                  class="th-chip"
                  :class="{ 'is-active': isDurationActive(opt) }"
                  @click="selectDuration(opt)"
                >{{ opt.short }}</button>
              </div>
              <div v-if="prefs.useCustomDuration || prefs.durationSec === 0" class="th-custom-min">
                <label>
                  自定义
                  <input v-model.number="prefs.customMinutes" type="number" min="1" max="60" step="1" />
                  分钟
                </label>
              </div>
            </div>

            <div class="th-block">
              <span class="th-label">编程语言</span>
              <div class="th-lang-chips" role="group" aria-label="编程语言">
                <button
                  v-for="opt in CODE_LANG_OPTIONS"
                  :key="opt.value"
                  type="button"
                  class="th-lang-chip"
                  :class="{ 'is-active': codeLang === opt.value }"
                  @click="selectCodeLang(opt.value)"
                >{{ opt.short || opt.label }}</button>
              </div>
            </div>

            <div class="th-block">
              <div class="th-block__head">
                <span class="th-label">练习内容</span>
                <div class="th-text-mode">
                  <button
                    type="button"
                    :class="{ 'is-active': codeSource === 'sample' }"
                    @click="codeSource = 'sample'"
                  >内置样例</button>
                  <button
                    type="button"
                    :class="{ 'is-active': codeSource === 'paste' }"
                    @click="codeSource = 'paste'"
                  >粘贴代码</button>
                </div>
              </div>

              <div v-if="codeSource === 'sample' && codeSamples.length > 1" class="th-sample-list">
                <button
                  v-for="s in codeSamples"
                  :key="s.id"
                  type="button"
                  class="th-sample-card"
                  :class="{ 'is-active': codeSampleId === s.id }"
                  @click="selectCodeSample(s)"
                >
                  <strong>{{ s.title }}</strong>
                  <span>{{ s.level }} · {{ s.lines }} 行 · {{ s.chars }} 字</span>
                </button>
              </div>

              <div class="th-code-editor" :class="{ 'is-paste': codeSource === 'paste' }">
                <div class="th-code-editor__bar">
                  <span class="th-code-editor__dot" aria-hidden="true" />
                  <span class="th-code-editor__dot" aria-hidden="true" />
                  <span class="th-code-editor__dot" aria-hidden="true" />
                  <span class="th-code-editor__file">{{ codeFileLabel }}</span>
                  <span class="th-code-editor__meta">{{ codeStatsLine }}</span>
                </div>

                <textarea
                  v-if="codeSource === 'paste'"
                  v-model="codeText"
                  class="th-textarea is-code-paste th-textarea--code th-code-editor__input"
                  rows="11"
                  maxlength="30000"
                  spellcheck="false"
                  placeholder="粘贴项目代码…保留缩进与换行。粘贴后自动识别语言。"
                  @paste="onCodePaste"
                />
                <pre
                  v-else
                  class="th-code-preview hljs"
                  tabindex="0"
                  aria-label="样例预览"
                ><code v-html="codePreviewHtml || codePreviewFallback" /></pre>
              </div>

              <p v-if="codeDetectNote" class="th-hint th-hint--code">{{ codeDetectNote }}</p>
              <p v-else class="th-hint">
                行首缩进自动跳过 · Tab 可忽略 · 行内空格仍需敲 · Esc 暂停
              </p>
            </div>

            <div v-if="codeTips.length" class="th-code-tips">
              <span class="th-label">编码规范 · {{ codeLangLabel }}</span>
              <ul class="th-code-tips__list">
                <li v-for="(tip, i) in codeTips" :key="i">{{ tip }}</li>
              </ul>
            </div>
          </template>

          <template v-else>
            <div class="th-ranked">
              <p class="th-ranked__tip">
                固定 <strong>10 分钟</strong> · <strong>{{ rankedMeta.targetChars }} 字</strong>赛题 · 成绩进组织榜
              </p>
              <p class="th-ranked__preview">{{ rankedPreview }}</p>
            </div>
          </template>

          <div v-if="playMode !== 'code'" class="th-block">
            <span class="th-label">空格显示</span>
            <div class="th-chips" role="group" aria-label="空格显示">
              <button
                v-for="opt in spaceGlyphOptions"
                :key="opt.value"
                type="button"
                class="th-chip"
                :class="{ 'is-active': prefs.spaceGlyph === opt.value }"
                :title="opt.hint"
                @click="selectSpaceGlyph(opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>

          <div class="th-actions">
            <button
              type="button"
              class="th-btn th-btn--primary th-start"
              @click="onStartClick"
            >
              {{ startButtonLabel }}
            </button>
          </div>
        </section>

        <!-- 排行榜 -->
        <aside class="th-card th-board" aria-label="组织速度榜">
          <header class="th-board__head">
            <div>
              <h3>组织速度榜</h3>
              <p>我的排名 {{ myBoardLine }}</p>
            </div>
            <button type="button" class="th-link" :disabled="boardLoading" @click="loadBoard">
              {{ boardLoading ? '…' : '刷新' }}
            </button>
          </header>
          <p v-if="boardError" class="th-empty">{{ boardError }}</p>
          <p v-else-if="!boardLoading && !boardList.length" class="th-empty">还没有排位成绩</p>
          <ol v-else class="th-rank">
            <li
              v-for="row in boardList.slice(0, 10)"
              :key="`${row.userId}-${row.rank}`"
              :class="{ 'is-me': row.isMe }"
            >
              <span class="th-rank__n">{{ row.rank }}</span>
              <strong class="th-rank__name">{{ row.isMe ? '我' : row.username }}</strong>
              <span class="th-rank__cpm">{{ row.cpm }}</span>
              <span class="th-rank__acc">{{ formatAcc(row.accuracy) }}%</span>
            </li>
          </ol>
        </aside>
      </div>

      <section v-if="weakChars.length" class="th-card th-weak" aria-label="薄弱攻坚">
        <div class="th-weak__main">
          <span class="th-label">薄弱字</span>
          <ul class="th-weak__list">
            <li v-for="item in weakChars.slice(0, 8)" :key="item.char + item.count">
              {{ item.char === ' ' ? '空格' : item.char }}
            </li>
            <li v-if="weakChars.length > 8" class="is-more">+{{ weakChars.length - 8 }}</li>
          </ul>
        </div>
        <button type="button" class="th-btn th-btn--ghost" @click="startWeakDrill">练 3 分钟</button>
      </section>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
import TypingInsightsPanel from '@/modules/typing/TypingInsightsPanel.vue'
import {
  createTypingCustomText,
  deleteTypingCustomText,
  fetchTypingLeaderboard,
  fetchTypingMyStats,
  flushTypingSessionQueue,
  listTypingCustomTexts,
  updateTypingCustomText,
} from '@/modules/typing/api'
import {
  DIFFICULTY_OPTIONS,
  DURATION_PRESETS,
  LANG_OPTIONS,
} from '@/modules/typing/catalog'
import { buildDrillText } from '@/modules/typing/coach'
import {
  CODE_LANG_OPTIONS,
  countCodeStats,
  detectCodeLanguage,
  getStyleTips,
  highlightCodeHtml,
  indentUnitForLang,
  listCodeSamples,
  looksLikeCode,
  normalizeCodeText,
} from '@/modules/typing/codePractice'
import { getRankedMeta, RANKED_TEXT_VERSION } from '@/modules/typing/rankedText'
import {
  buildLocalDailyTrend,
  formatDurationMinutes,
  listLocalRecentSessions,
  loadHistory,
  loadPrefs,
  normalizeSpaceGlyph,
  resolvePracticeDurationSec,
  savePrefs,
  SPACE_GLYPH_OPTIONS,
  summarizeHistory,
  summarizeToday,
} from '@/modules/typing/storage'

const router = useRouter()
const prefs = reactive(loadPrefs())
const spaceGlyphOptions = SPACE_GLYPH_OPTIONS
prefs.spaceGlyph = normalizeSpaceGlyph(prefs.spaceGlyph)
const playMode = ref(
  prefs.playMode === 'ranked' ? 'ranked'
    : prefs.playMode === 'code' ? 'code'
      : 'practice'
)
const useCustomText = ref(false)
const customText = ref('')
const customTitle = ref('')
const editingCustomId = ref(null)
const customTexts = ref([])
const customLoaded = ref(false)
const customSaving = ref(false)
const customError = ref('')

/** 代码练习 */
const codeLang = ref(prefs.codeLang || 'javascript')
const codeSource = ref(prefs.codeSource === 'paste' ? 'paste' : 'sample')
const codeText = ref('')
const codeSampleId = ref('')
const codePreviewHtml = ref('')
const codeDetectNote = ref('')
let previewTimer = null
let previewSeq = 0

const looksLikeCodePaste = computed(() => looksLikeCode(customText.value))

const codeTips = computed(() => getStyleTips(codeLang.value))

const codeSamples = computed(() => listCodeSamples(codeLang.value))

const codeLangLabel = computed(() =>
  CODE_LANG_OPTIONS.find((o) => o.value === codeLang.value)?.label || codeLang.value
)

const codeIndentLabel = computed(() => {
  const unit = indentUnitForLang(codeLang.value)
  if (unit === '\t') return 'Tab'
  return `${unit.length} 空格`
})

const codeStats = computed(() => countCodeStats(codeText.value))

const codeStatsLine = computed(() => {
  const { lines, chars } = codeStats.value
  if (!chars) return '空'
  return `${lines} 行 · ${chars} 字`
})

const codeFileLabel = computed(() => {
  const map = {
    javascript: 'practice.js',
    java: 'Practice.java',
    python: 'practice.py',
    sql: 'query.sql',
    html: 'ScoreCard.vue',
    css: 'score-card.css',
    json: 'report.json',
    plaintext: 'notes.txt',
  }
  return map[codeLang.value] || 'code.txt'
})

const codePreviewFallback = computed(() =>
  (codeText.value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
)

const startButtonLabel = computed(() => {
  if (playMode.value === 'ranked') return '进入排位赛 · 10 分钟'
  if (playMode.value === 'code') {
    const n = codeStats.value.chars
    return n
      ? `开始代码练习 · ${practiceDurationLabel.value} · ${n} 字`
      : `开始代码练习 · ${practiceDurationLabel.value}`
  }
  return `开始练习 · ${practiceDurationLabel.value}`
})

const summary = ref(summarizeHistory([]))
const todayLocal = ref(summarizeToday([]))
const localTrend = ref(buildLocalDailyTrend([], 14))
const localSessions = ref([])
const boardList = ref([])
const boardLoading = ref(false)
const boardError = ref('')
const myRank = ref(null)
const serverStats = ref(null)
const rankedMeta = getRankedMeta()

const DURATION_CHIPS = DURATION_PRESETS.map((opt) => ({
  ...opt,
  short: opt.value === 0 ? '自定义' : opt.label.replace(/\s/g, ''),
}))

const todayView = computed(() => {
  const local = todayLocal.value || summarizeToday([])
  const remote = serverStats.value?.today
  if (!remote || !Number(remote.count)) {
    return {
      count: local.count,
      bestCpm: local.bestCpm,
      avgAccuracy: local.avgAccuracy,
      durationLabel: local.durationLabel || formatDurationMinutes(local.totalElapsedMs),
    }
  }
  return {
    count: Math.max(Number(remote.count) || 0, local.count),
    bestCpm: Math.max(Number(remote.bestCpm) || 0, local.bestCpm || 0),
    avgAccuracy: Number(remote.avgAccuracy) || local.avgAccuracy || 0,
    durationLabel: formatDurationMinutes(
      Math.max(Number(remote.totalElapsedMs) || 0, local.totalElapsedMs || 0)
    ),
  }
})

const todaySummaryLine = computed(() => {
  if (!todayView.value.count) return '今日还没练'
  const acc = todayView.value.avgAccuracy ? ` · ${todayView.value.avgAccuracy}%` : ''
  const cpm = todayView.value.bestCpm ? ` · 最高 ${todayView.value.bestCpm}` : ''
  return `今日 ${todayView.value.count} 次 · ${todayView.value.durationLabel}${cpm}${acc}`
})

const weakChars = computed(() => summary.value?.weakChars || [])

const rankedPreview = computed(() => {
  const t = rankedMeta.text || ''
  return [...t].slice(0, 72).join('') + (t.length > 72 ? '…' : '')
})

const practiceDurationLabel = computed(() => {
  const sec = resolvePracticeDurationSec(prefs)
  if (sec >= 60 && sec % 60 === 0) return `${sec / 60} 分钟`
  if (sec >= 60) return `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`
  return `${sec} 秒`
})

const myBoardLine = computed(() => {
  if (myRank.value) return `第 ${myRank.value}`
  if (serverStats.value?.myRank) return `第 ${serverStats.value.myRank}`
  return '未上榜'
})

/** 合并服务端 + 本地历史，供洞察面板使用 */
const insightStats = computed(() => {
  const remote = serverStats.value || {}
  const local = summary.value || {}
  return {
    ...remote,
    avgCpm: Number(remote.avgCpm) || local.avgCpm || 0,
    avgCpm7d: Number(remote.avgCpm7d) || local.avgCpm || 0,
    bestCpm: Math.max(
      Number(remote.bestCpm) || 0,
      Number(remote.bestPracticeCpm) || 0,
      Number(remote.bestRankedCpm) || 0,
      Number(local.bestCpm) || 0
    ),
    bestPracticeCpm: Number(remote.bestPracticeCpm) || 0,
    bestRankedCpm: Number(remote.bestRankedCpm) || 0,
    avgAccuracy: Number(remote.avgAccuracy) || local.avgAccuracy || 0,
    sessionCount: Number(remote.sessionCount || remote.practiceCount)
      || local.count
      || 0,
    practiceCount: Number(remote.practiceCount) || local.count || 0,
    totalElapsedMs: Number(remote.totalElapsedMs) || 0,
    dailyTrend: Array.isArray(remote.dailyTrend) && remote.dailyTrend.length
      ? remote.dailyTrend
      : localTrend.value,
    recentSessions: Array.isArray(remote.recentSessions) && remote.recentSessions.length
      ? remote.recentSessions
      : localSessions.value,
  }
})

const insightAvgCpm = computed(() =>
  Number(insightStats.value.avgCpm7d)
  || Number(insightStats.value.avgCpm)
  || Number(summary.value?.avgCpm)
  || 0
)

watch(playMode, (v) => {
  prefs.playMode = v
  savePrefs({ playMode: v })
  if (v === 'code') {
    if (codeSource.value === 'sample') loadCodeSample()
    else scheduleCodePreview()
  }
})

watch(codeLang, (v) => {
  prefs.codeLang = v
  savePrefs({ codeLang: v })
})

watch(codeSource, (v) => {
  prefs.codeSource = v
  savePrefs({ codeSource: v })
  codeDetectNote.value = ''
  if (v === 'sample') loadCodeSample()
  else scheduleCodePreview()
})

watch(codeText, () => {
  scheduleCodePreview()
})

function selectCodeLang(lang) {
  if (codeLang.value === lang) return
  codeLang.value = lang
  codeDetectNote.value = ''
  if (codeSource.value === 'sample') loadCodeSample()
  else scheduleCodePreview()
}

function loadCodeSample() {
  const samples = listCodeSamples(codeLang.value)
  const current = samples.find((s) => s.id === codeSampleId.value) || samples[0]
  codeSampleId.value = current?.id || ''
  codeText.value = current?.content || ''
  scheduleCodePreview()
}

function selectCodeSample(sample) {
  codeSampleId.value = sample.id
  codeText.value = sample.content || ''
  scheduleCodePreview()
}

function onCodePaste() {
  // 下一 tick 读 v-model 已更新的内容
  requestAnimationFrame(() => {
    const text = codeText.value
    if (!looksLikeCode(text)) return
    const detected = detectCodeLanguage(text)
    if (detected && detected !== codeLang.value && detected !== 'plaintext') {
      codeLang.value = detected
      codeDetectNote.value = `已自动识别为 ${CODE_LANG_OPTIONS.find((o) => o.value === detected)?.label || detected}`
    }
    scheduleCodePreview()
  })
}

function scheduleCodePreview() {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(() => refreshCodePreview(), 80)
}

async function refreshCodePreview() {
  if (codeSource.value === 'paste') return
  const seq = ++previewSeq
  const html = await highlightCodeHtml(codeText.value, codeLang.value)
  if (seq !== previewSeq) return
  codePreviewHtml.value = html
}

function onStartClick() {
  if (playMode.value === 'ranked') startRanked()
  else if (playMode.value === 'code') startCodePractice()
  else startPractice()
}

function refreshLocalStats() {
  const history = loadHistory()
  summary.value = summarizeHistory(history)
  todayLocal.value = summarizeToday(history)
  localTrend.value = buildLocalDailyTrend(history, 14)
  localSessions.value = listLocalRecentSessions(history, 12)
}

onMounted(async () => {
  refreshLocalStats()
  if (playMode.value === 'code') {
    if (codeSource.value === 'sample') loadCodeSample()
    else scheduleCodePreview()
  }
  await Promise.all([
    loadBoard(),
    loadStats(),
    loadCustomTexts(),
    flushTypingSessionQueue().catch(() => []),
  ])
  refreshLocalStats()
})

onBeforeUnmount(() => {
  clearTimeout(previewTimer)
})

function isDurationActive(opt) {
  if (opt.value === 0) return prefs.useCustomDuration || prefs.durationSec === 0
  return !prefs.useCustomDuration && prefs.durationSec === opt.value
}

function selectDuration(opt) {
  if (opt.value === 0) {
    prefs.useCustomDuration = true
    prefs.durationSec = 0
    if (!prefs.customMinutes) prefs.customMinutes = 5
  } else {
    prefs.useCustomDuration = false
    prefs.durationSec = opt.value
  }
}

function formatAcc(v) {
  const n = Number(v)
  if (Number.isNaN(n)) return '—'
  return Math.round(n * 10) / 10
}

function selectSpaceGlyph(mode) {
  prefs.spaceGlyph = normalizeSpaceGlyph(mode)
  savePrefs({ spaceGlyph: prefs.spaceGlyph })
}

function persistPrefs() {
  savePrefs({
    playMode: playMode.value,
    durationSec: prefs.durationSec,
    customMinutes: prefs.customMinutes,
    useCustomDuration: prefs.useCustomDuration,
    lang: prefs.lang,
    difficulty: prefs.difficulty,
    codeLang: codeLang.value,
    codeSource: codeSource.value,
    spaceGlyph: normalizeSpaceGlyph(prefs.spaceGlyph),
  })
}

async function loadCustomTexts() {
  customError.value = ''
  try {
    customTexts.value = await listTypingCustomTexts()
  } catch {
    customTexts.value = []
  } finally {
    customLoaded.value = true
  }
}

function applyCustomText(item) {
  useCustomText.value = true
  customText.value = item.content || ''
  customTitle.value = item.title || ''
  editingCustomId.value = item.id
}

function clearCustomSelection() {
  editingCustomId.value = null
  customTitle.value = ''
}

async function saveCustomToAccount() {
  const content = customText.value.trim()
  if (!content) {
    customError.value = '请先填写文案内容'
    return
  }
  customSaving.value = true
  customError.value = ''
  try {
    const title = (customTitle.value || '').trim() || content.slice(0, 20)
    let saved
    if (editingCustomId.value) {
      saved = await updateTypingCustomText(editingCustomId.value, { title, content })
      ElMessage.success('已更新到账户')
    } else {
      saved = await createTypingCustomText({ title, content })
      editingCustomId.value = saved?.id || null
      ElMessage.success('已保存到账户，下次登录仍可用')
    }
    if (saved) {
      customTitle.value = saved.title || title
      await loadCustomTexts()
    }
  } catch (e) {
    customError.value = e?.message || '保存失败'
  } finally {
    customSaving.value = false
  }
}

async function removeCustomText(item) {
  try {
    await ElMessageBox.confirm(`删除「${item.title || '未命名'}」？`, '删除文案', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteTypingCustomText(item.id)
    if (editingCustomId.value === item.id) {
      editingCustomId.value = null
    }
    await loadCustomTexts()
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e?.message || '删除失败')
  }
}

function startPractice() {
  persistPrefs()
  if (useCustomText.value && !customText.value.trim()) {
    ElMessage.warning('请填写自定义文案，或切换回系统文案')
    return
  }
  const durationSec = resolvePracticeDurationSec(prefs)
  let text = ''
  let sourceType = 'catalog'
  let codeLangForSession = null
  if (useCustomText.value && customText.value.trim()) {
    // 代码：只去首尾空行，保留缩进；普通文案：trim
    if (looksLikeCodePaste.value) {
      text = normalizeCodeText(customText.value)
      sourceType = 'code'
      codeLangForSession = detectCodeLanguage(text)
    } else {
      text = customText.value.trim()
      sourceType = 'paste'
    }
  }
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'practice',
    mode: 'timed',
    durationSec,
    lang: sourceType === 'code' ? 'mixed' : prefs.lang,
    difficulty: prefs.difficulty,
    customText: text,
    sourceType,
    codeLang: codeLangForSession,
    customTextId: useCustomText.value ? editingCustomId.value : null,
  }))
  router.push({ name: 'TypingPlay' })
}

function startCodePractice() {
  persistPrefs()
  let text = normalizeCodeText(codeText.value)
  let lang = codeLang.value || 'javascript'
  if (!text) {
    if (codeSource.value === 'paste') {
      ElMessage.warning('请粘贴要练习的代码，或切换到内置样例')
      return
    }
    const samples = listCodeSamples(lang)
    const picked = samples.find((s) => s.id === codeSampleId.value) || samples[0]
    text = normalizeCodeText(picked?.content || '')
  }
  if (!text) {
    ElMessage.warning('暂无可用代码')
    return
  }
  if (codeSource.value === 'paste' && looksLikeCode(text)) {
    const detected = detectCodeLanguage(text)
    if (detected) lang = detected
  }
  const durationSec = resolvePracticeDurationSec(prefs)
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'code',
    mode: 'timed',
    durationSec,
    lang: 'mixed',
    difficulty: prefs.difficulty,
    customText: text,
    sourceType: 'code',
    codeLang: lang,
  }))
  router.push({ name: 'TypingPlay' })
}

function startWeakDrill() {
  const weak = weakChars.value.map((w) => w.char)
  if (!weak.length) return
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'practice',
    mode: 'timed',
    durationSec: 180,
    lang: 'zh',
    difficulty: 2,
    customText: buildDrillText(weak, 280),
    sourceType: 'drill',
    drill: true,
    weakChars: weak,
  }))
  router.push({ name: 'TypingPlay' })
}

function startRanked() {
  persistPrefs()
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'ranked',
    mode: 'timed',
    durationSec: rankedMeta.durationSec,
    lang: 'zh',
    difficulty: 2,
    customText: rankedMeta.text,
    sourceType: 'ranked',
    textVersion: RANKED_TEXT_VERSION,
  }))
  router.push({ name: 'TypingPlay' })
}

async function loadBoard() {
  boardLoading.value = true
  boardError.value = ''
  try {
    const data = await fetchTypingLeaderboard({ textVersion: RANKED_TEXT_VERSION, limit: 30 })
    boardList.value = Array.isArray(data?.list) ? data.list : []
    myRank.value = data?.myRank ?? null
  } catch {
    boardError.value = '榜单暂时加载失败'
    boardList.value = []
  } finally {
    boardLoading.value = false
  }
}

async function loadStats() {
  try {
    serverStats.value = await fetchTypingMyStats()
  } catch {
    serverStats.value = null
  }
}
</script>

<style scoped>
.typing-home {
  --ink: #111827;
  --ink-2: #374151;
  --muted: #6b7280;
  --line: #e8eaed;
  --soft: #f6f7f9;
  --accent: #e5481d;
  --radius: 14px;
}

.th {
  display: grid;
  gap: 14px;
  width: 100%;
  max-width: 1040px;
  margin: 0 auto;
  min-width: 0;
}

.th-summary {
  margin: 0;
  padding: 0 2px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px 0;
}
.th-summary i {
  font-style: normal;
  margin: 0 8px;
  opacity: .5;
}

.th-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 280px);
  gap: 12px;
  align-items: stretch;
}

.th-card {
  box-sizing: border-box;
  margin: 0;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
  min-width: 0;
}

.th-setup {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.th-seg {
  display: inline-flex;
  flex-wrap: wrap;
  padding: 3px;
  border-radius: 999px;
  background: var(--soft);
  border: 1px solid var(--line);
  margin-bottom: 16px;
  align-self: flex-start;
  max-width: 100%;
}
.th-seg button {
  appearance: none;
  border: 0;
  background: transparent;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  color: var(--muted);
  font: 650 13px/1 inherit;
  cursor: pointer;
  white-space: nowrap;
}
.th-seg button.is-active {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 1px 2px rgba(15, 23, 42, .06);
  font-weight: 750;
}

.th-block { margin-bottom: 16px; }
.th-block--row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.th-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.th-label {
  display: block;
  color: var(--ink-2);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}
.th-block__head .th-label { margin-bottom: 0; }

.th-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.th-chip {
  appearance: none;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-2);
  font: 600 13px/1 inherit;
  cursor: pointer;
}
.th-chip.is-active {
  border-color: var(--ink);
  background: var(--ink);
  color: #fff;
  font-weight: 700;
}

.th-custom-min {
  margin-top: 10px;
}
.th-custom-min label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink-2);
  font-weight: 600;
}
.th-custom-min input {
  width: 64px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0 8px;
  font: inherit;
  text-align: center;
}

.th-field { display: grid; gap: 6px; min-width: 0; }
.th-select {
  width: 100%;
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0 10px;
  font: inherit;
  font-size: 13px;
  background: #fff;
  color: var(--ink);
}

.th-text-mode {
  display: inline-flex;
  padding: 2px;
  border-radius: 999px;
  background: var(--soft);
  border: 1px solid var(--line);
}
.th-text-mode button {
  appearance: none;
  border: 0;
  background: transparent;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  color: var(--muted);
  font: 650 12px/1 inherit;
  cursor: pointer;
}
.th-text-mode button.is-active {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 1px 2px rgba(15, 23, 42, .05);
}

.th-textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  font: inherit;
  font-size: 13px;
  line-height: 1.55;
  resize: vertical;
  min-height: 96px;
  background: #fafbfc;
  white-space: pre-wrap;
  tab-size: 4;
}
.th-textarea.is-code-paste {
  font-family:
    ui-monospace,
    "JetBrains Mono",
    "Cascadia Code",
    "SF Mono",
    Consolas,
    Menlo,
    monospace;
  font-size: 12.5px;
  line-height: 1.5;
  background: #f8fafc;
  color: #0f172a;
}
.th-textarea:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
  background: #fff;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent);
}
.th-textarea.is-code-paste:focus {
  background: #fff;
}
.th-textarea--code {
  min-height: 180px;
  tab-size: 2;
}
.th-hint--code {
  margin-top: 8px;
  color: var(--ds-orange-700, #c2410c);
  font-weight: 650;
}

.th-code-lead {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: 0.01em;
}

.th-lang-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.th-lang-chip {
  appearance: none;
  min-height: 30px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink-2);
  font: 650 12px/1 inherit;
  cursor: pointer;
}
.th-lang-chip.is-active {
  border-color: #0f172a;
  background: #0f172a;
  color: #fff;
  font-weight: 750;
}

.th-sample-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}
.th-sample-card {
  appearance: none;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  padding: 10px 12px;
  cursor: pointer;
  display: grid;
  gap: 4px;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.th-sample-card strong {
  font-size: 13px;
  color: var(--ink);
  font-weight: 700;
}
.th-sample-card span {
  font-size: 11px;
  color: var(--muted);
  font-weight: 550;
}
.th-sample-card:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}
.th-sample-card.is-active {
  border-color: #0f172a;
  background: #f1f5f9;
  box-shadow: 0 0 0 1px #0f172a inset;
}

.th-code-editor {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #1e293b;
  background: #0f172a;
  box-shadow: 0 8px 24px rgba(15, 23, 42, .12);
}
.th-code-editor__bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  min-height: 34px;
}
.th-code-editor__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #475569;
}
.th-code-editor__dot:nth-child(1) { background: #f87171; }
.th-code-editor__dot:nth-child(2) { background: #fbbf24; }
.th-code-editor__dot:nth-child(3) { background: #34d399; }
.th-code-editor__file {
  margin-left: 8px;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 650;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.th-code-editor__meta {
  margin-left: auto;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.th-code-editor__input {
  margin: 0;
  border: 0 !important;
  border-radius: 0 !important;
  background: #0f172a !important;
  color: #e2e8f0 !important;
  min-height: 220px;
  box-shadow: none !important;
}
.th-code-editor__input::placeholder {
  color: #64748b;
}
.th-code-editor__input:focus {
  background: #0b1220 !important;
  box-shadow: none !important;
}

.th-code-preview {
  margin: 0;
  padding: 14px 16px;
  min-height: 200px;
  max-height: 280px;
  overflow: auto;
  background: #0f172a;
  color: #cbd5e1;
  font-family:
    ui-monospace,
    "JetBrains Mono",
    "Cascadia Code",
    "SF Mono",
    Consolas,
    Menlo,
    monospace;
  font-size: 12.5px;
  line-height: 1.55;
  tab-size: 2;
  white-space: pre;
}
.th-code-preview code {
  font: inherit;
  color: inherit;
  white-space: inherit;
}
/* 预览区 hljs 暗色 token */
.th-code-preview :deep(.hljs-keyword),
.th-code-preview :deep(.hljs-built_in),
.th-code-preview :deep(.hljs-selector-tag) { color: #c4b5fd; }
.th-code-preview :deep(.hljs-string),
.th-code-preview :deep(.hljs-template-string),
.th-code-preview :deep(.hljs-attr) { color: #6ee7b7; }
.th-code-preview :deep(.hljs-comment),
.th-code-preview :deep(.hljs-quote) { color: #64748b; font-style: italic; }
.th-code-preview :deep(.hljs-number),
.th-code-preview :deep(.hljs-literal) { color: #fbbf24; }
.th-code-preview :deep(.hljs-title),
.th-code-preview :deep(.hljs-section),
.th-code-preview :deep(.function_) { color: #7dd3fc; }
.th-code-preview :deep(.hljs-type),
.th-code-preview :deep(.hljs-class),
.th-code-preview :deep(.hljs-params) { color: #67e8f9; }
.th-code-preview :deep(.hljs-meta),
.th-code-preview :deep(.hljs-name),
.th-code-preview :deep(.hljs-tag) { color: #f9a8d4; }
.th-code-preview :deep(.hljs-variable),
.th-code-preview :deep(.hljs-property),
.th-code-preview :deep(.hljs-template-variable) { color: #fdba74; }
.th-code-preview :deep(.hljs-punctuation),
.th-code-preview :deep(.hljs-operator) { color: #94a3b8; }

.th-code-tips {
  margin: 0 0 4px;
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, #fff7ed 0%, #fffbeb 100%);
  border: 1px solid #fed7aa;
}
.th-code-tips .th-label {
  margin-bottom: 8px;
  color: #9a3412;
}
.th-code-tips__list {
  margin: 0;
  padding: 0 0 0 1.1em;
  display: grid;
  gap: 6px;
  color: #7c2d12;
  font-size: 12.5px;
  line-height: 1.5;
  font-weight: 550;
}
.th-code-tips__list li::marker {
  color: #ea580c;
}

.th-custom-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  align-items: center;
}
.th-title-input {
  flex: 1;
  min-width: 140px;
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0 12px;
  font: inherit;
  font-size: 13px;
  background: #fff;
}

.th-saved { margin-top: 12px; }
.th-saved .th-label { margin-bottom: 6px; }
.th-saved__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
  max-height: 160px;
  overflow: auto;
}
.th-saved__list li {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}
.th-saved__list li.is-active {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
  background: color-mix(in srgb, var(--accent) 6%, #fff);
}
.th-saved__main {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  text-align: left;
  padding: 8px 10px;
  cursor: pointer;
  display: grid;
  gap: 2px;
}
.th-saved__main strong {
  font-size: 13px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.th-saved__main span { font-size: 11px; color: var(--muted); }
.th-saved__del {
  width: 32px;
  height: 32px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  border-radius: 8px;
  margin-right: 4px;
}
.th-saved__del:hover { background: #fef2f2; color: #b91c1c; }

.th-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
}
.th-error {
  margin: 8px 0 0;
  font-size: 12px;
  color: #b91c1c;
  font-weight: 600;
}

.th-ranked__tip {
  margin: 0 0 10px;
  color: var(--ink-2);
  font-size: 13px;
  line-height: 1.55;
}
.th-ranked__tip strong { color: var(--ink); font-weight: 750; }
.th-ranked__preview {
  margin: 0;
  padding: 12px;
  border-radius: 12px;
  background: var(--soft);
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}

.th-actions {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.th-btn {
  appearance: none;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 8px 14px;
  font: 650 13px/1 inherit;
  cursor: pointer;
  transition: background .15s, border-color .15s, opacity .15s;
}
.th-btn:disabled { opacity: .5; cursor: not-allowed; }
.th-btn--primary { background: var(--accent); color: #fff; }
.th-btn--primary:hover:not(:disabled) { filter: brightness(.96); }
.th-btn--ghost {
  background: #fff;
  border-color: var(--line);
  color: var(--ink);
}
.th-btn--ghost:hover:not(:disabled) { background: var(--soft); }
.th-start {
  width: 100%;
  min-height: 44px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 750;
}

.th-link {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--accent);
  font: 700 12px/1 inherit;
  cursor: pointer;
  padding: 0;
}
.th-link:disabled { opacity: .45; cursor: default; }

/* board */
.th-board {
  display: flex;
  flex-direction: column;
  padding: 14px;
}
.th-board__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.th-board__head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 750;
  color: var(--ink);
}
.th-board__head p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}
.th-empty {
  margin: 0;
  padding: 8px 0;
  color: var(--muted);
  font-size: 12px;
}
.th-rank {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: auto;
  min-height: 0;
  flex: 1;
}
.th-rank li {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 40px 40px;
  gap: 6px;
  align-items: center;
  min-height: 34px;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.th-rank li:last-child { border-bottom: 0; }
.th-rank li.is-me { font-weight: 700; }
.th-rank__n {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  font-size: 11px;
}
.th-rank__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--ink);
}
.th-rank__cpm {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 750;
  color: var(--ink);
}
.th-rank__acc {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  font-size: 11px;
}

/* weak */
.th-weak {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
}
.th-weak__main { min-width: 0; display: grid; gap: 6px; }
.th-weak__main .th-label { margin: 0; }
.th-weak__list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.th-weak__list li {
  min-height: 26px;
  padding: 0 8px;
  border-radius: 8px;
  background: var(--soft);
  border: 1px solid var(--line);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  display: inline-flex;
  align-items: center;
}
.th-weak__list li.is-more {
  font-family: inherit;
  font-weight: 600;
  color: var(--muted);
  font-size: 12px;
}

@media (max-width: 800px) {
  .th-layout { grid-template-columns: 1fr; }
  .th-board { max-height: 320px; }
}
@media (max-width: 560px) {
  .th { max-width: none; }
  .th-block--row { grid-template-columns: 1fr; }
  .th-weak { flex-direction: column; align-items: stretch; }
  .th-weak .th-btn { width: 100%; }
}
</style>
