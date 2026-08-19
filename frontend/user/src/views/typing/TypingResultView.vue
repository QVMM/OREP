<template>
  <AiAppShell mode="landing" width="wide" class="tr-page">
    <template #header>
      <AiAppHeader
        app="typing"
        mode="landing"
        :title="isRanked ? '排位成绩' : '本局结果'"
        :subtitle="headerSub"
        back-label="打字练习"
        back-to="/typing-practice"
      />
    </template>

    <div v-if="result" class="tr">
      <!-- 成绩总览 -->
      <section class="tr-hero" aria-label="本局成绩">
        <div class="tr-hero__main">
          <div class="tr-score">
            <strong>{{ result.cpm }}</strong>
            <span>CPM</span>
          </div>
          <div class="tr-metrics">
            <div>
              <strong>{{ result.accuracy }}%</strong>
              <span>准确率</span>
            </div>
            <div>
              <strong>{{ result.correctChars }}</strong>
              <span>正确字</span>
            </div>
            <div>
              <strong>{{ formatDuration(result.elapsedMs) }}</strong>
              <span>用时</span>
            </div>
          </div>
        </div>
        <p v-if="result.rank" class="tr-rank-line">
          组织排位 <b>第 {{ result.rank }} 名</b>
        </p>
        <p v-if="todayNote" class="tr-today">{{ todayNote }}</p>
        <p v-if="durationUnsynced" class="tr-warn">{{ unsyncedMessage }}</p>
      </section>

      <!-- AI 教练 -->
      <section class="tr-card tr-coach" :class="`is-${coach?.level || 'steady'}`" aria-label="AI 教练">
        <header class="tr-coach__head">
          <span class="tr-coach__badge">
            <i aria-hidden="true" />
            AI 教练
          </span>
          <span class="tr-coach__src">{{ coachSourceLabel }}</span>
        </header>
        <h2>{{ coach?.headline || '分析中…' }}</h2>
        <p class="tr-coach__summary">{{ coach?.summary }}</p>

        <ul v-if="coach?.issues?.length" class="tr-issues">
          <li v-for="item in coach.issues" :key="item.id">
            <strong>{{ item.title }}</strong>
            <span>{{ item.detail }}</span>
          </li>
        </ul>

        <div v-if="coach?.tips?.length" class="tr-tips">
          <span v-for="(tip, i) in coach.tips" :key="i">{{ tip }}</span>
        </div>

        <div v-if="coach?.prescription" class="tr-rx">
          <div class="tr-rx__copy">
            <small>{{ coach.prescription.label }}</small>
            <strong>{{ coach.prescription.title }}</strong>
            <p>{{ coach.prescription.reason }}</p>
          </div>
          <button type="button" class="tr-btn tr-btn--primary" @click="runPrescription">
            {{ coach.prescription.cta || '按建议再练' }}
          </button>
        </div>
      </section>

      <div class="tr-grid">
        <!-- 易错字 -->
        <section class="tr-card" aria-label="易错字">
          <header class="tr-card__head">
            <h3>{{ errors.length ? '易错字' : '本局很稳' }}</h3>
            <p>
              {{ errors.length
                ? '点字可看次数，建议做薄弱攻坚'
                : '无明显易错，可加时长或去排位' }}
            </p>
          </header>
          <ul v-if="errors.length" class="tr-errors">
            <li v-for="item in errors" :key="item.char + item.count">
              <span class="ch">{{ displayChar(item.char) }}</span>
              <span class="n">{{ item.count }}</span>
            </li>
          </ul>
          <button
            v-if="errors.length >= 2"
            type="button"
            class="tr-btn tr-btn--ghost tr-btn--block"
            @click="startDrill"
          >
            薄弱攻坚 · 3 分钟
          </button>
        </section>

        <!-- 组织榜 -->
        <section v-if="boardPreview.length" class="tr-card" aria-label="组织榜">
          <header class="tr-card__head">
            <h3>组织榜</h3>
            <p>排位赛个人最佳</p>
          </header>
          <ol class="tr-board">
            <li
              v-for="row in boardPreview"
              :key="row.rank + '-' + row.userId"
              :class="{ 'is-me': row.isMe }"
            >
              <span class="tr-board__n">{{ row.rank }}</span>
              <strong>{{ row.isMe ? '我' : row.username }}</strong>
              <em>{{ row.cpm }}</em>
            </li>
          </ol>
        </section>
      </div>

      <!-- 底部操作 -->
      <footer class="tr-actions">
        <button type="button" class="tr-btn tr-btn--primary tr-btn--lg" @click="again">
          {{ isRanked ? '再打一局排位' : '再来一局' }}
        </button>
        <button
          v-if="!isRanked"
          type="button"
          class="tr-btn tr-btn--ghost tr-btn--lg"
          @click="goRanked"
        >
          去排位赛
        </button>
        <button type="button" class="tr-btn tr-btn--ghost tr-btn--lg" @click="goHome">
          返回首页
        </button>
      </footer>
    </div>

    <div v-else class="tr-empty">
      <strong>暂无成绩</strong>
      <p>先完成一局练习吧。</p>
      <button type="button" class="tr-btn tr-btn--primary" @click="goHome">去练习</button>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
import {
  DURATION_UNSYNCED_MESSAGE,
  fetchTypingCoach,
  flushTypingSessionQueue,
  isTypingSessionQueued,
} from '@/modules/typing/api'
import {
  buildCoachReport,
  buildDrillText,
  prescriptionToSessionCfg,
} from '@/modules/typing/coach'
import { formatDuration } from '@/modules/typing/engine'
import { getRankedMeta, RANKED_TEXT_VERSION } from '@/modules/typing/rankedText'
import {
  formatDurationMinutes,
  loadHistory,
  loadLastResult,
  loadPrefs,
  resolvePracticeDurationSec,
  summarizeHistory,
  summarizeToday,
} from '@/modules/typing/storage'

const router = useRouter()
const result = ref(null)
const summary = ref(summarizeHistory([]))
const today = ref(summarizeToday([]))
const coach = ref(null)
const coachFromServer = ref(false)
const durationUnsynced = ref(false)
const unsyncedMessage = DURATION_UNSYNCED_MESSAGE

function refreshUnsyncedFlag() {
  const row = result.value
  if (!row) {
    durationUnsynced.value = false
    return
  }
  durationUnsynced.value = Boolean(
    isTypingSessionQueued(row.clientSessionId)
    || (row.durationUnsynced && !row.serverId)
    || (row.syncError && !row.serverId),
  )
}

onMounted(async () => {
  result.value = loadLastResult()
  const history = loadHistory()
  summary.value = summarizeHistory(history)
  today.value = summarizeToday(history)

  if (!result.value) return
  refreshUnsyncedFlag()
  try {
    await flushTypingSessionQueue()
  } catch {
    /* 队列会留下，练习页心跳再试 */
  }
  refreshUnsyncedFlag()

  coach.value = buildCoachReport(result.value, {
    today: today.value,
    history,
  })

  try {
    const remote = await fetchTypingCoach({
      result: {
        cpm: result.value.cpm,
        accuracy: result.value.accuracy,
        correctChars: result.value.correctChars,
        elapsedMs: result.value.elapsedMs,
        mode: result.value.mode || result.value.playMode,
        topErrors: result.value.topErrors,
        errorMap: result.value.errorMap,
      },
      today: today.value,
    })
    if (remote?.headline) {
      if (remote.prescription?.drill && !remote.prescription.customText && remote.prescription.weakChars?.length) {
        remote.prescription.customText = buildDrillText(remote.prescription.weakChars, 280)
      }
      coach.value = remote
      coachFromServer.value = true
    }
  } catch {
    coachFromServer.value = false
  }
})

const isRanked = computed(() => result.value?.mode === 'ranked' || result.value?.playMode === 'ranked')
const isCode = computed(() =>
  result.value?.playMode === 'code'
  || result.value?.sourceType === 'code'
  || result.value?.mode === 'code'
)

const headerSub = computed(() => {
  if (isRanked.value) return result.value?.rank ? `组织第 ${result.value.rank} 名` : '排位成绩已记录'
  if (isCode.value) return '代码练习 · 巩固缩进与符号手感'
  return coach.value?.headline ? 'AI 教练已出点评' : '本局数据与建议'
})

const todayNote = computed(() => {
  const t = today.value
  if (!t?.count) return ''
  return `今日 ${t.count} 次 · ${t.durationLabel || formatDurationMinutes(t.totalElapsedMs)} · 最高 ${t.bestCpm || 0} CPM`
})

const coachSourceLabel = computed(() => {
  if (!coach.value) return ''
  return coachFromServer.value ? '云端' : '即时'
})

const errors = computed(() => {
  if (!result.value) return []
  if (Array.isArray(result.value.topErrors) && result.value.topErrors.length) {
    return result.value.topErrors.slice(0, 10)
  }
  const map = result.value.errorMap || {}
  return Object.entries(map)
    .filter(([ch]) => ch && ch !== ' ' && ch !== '\n')
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([char, count]) => ({ char, count }))
})

const boardPreview = computed(() => {
  const list = result.value?.leaderboard?.list
  return Array.isArray(list) ? list.slice(0, 8) : []
})

function displayChar(ch) {
  if (ch === ' ') return '␣'
  if (ch === '\n') return '↵'
  return ch
}

function runPrescription() {
  const p = coach.value?.prescription
  if (!p) {
    again()
    return
  }
  if (p.mode === 'ranked') {
    goRanked()
    return
  }
  const cfg = prescriptionToSessionCfg(p)
  if (!cfg) return
  if (cfg.drill && !cfg.customText && (p.weakChars || []).length) {
    cfg.customText = buildDrillText(p.weakChars, 280)
  }
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify(cfg))
  router.replace({ name: 'TypingPlay' })
}

function startDrill() {
  const weak = errors.value.map((e) => e.char)
  const text = buildDrillText(weak, 280)
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'practice',
    mode: 'timed',
    durationSec: 180,
    lang: 'zh',
    difficulty: 2,
    customText: text,
    sourceType: 'drill',
    drill: true,
    weakChars: weak,
  }))
  router.replace({ name: 'TypingPlay' })
}

function again() {
  if (isRanked.value) {
    goRanked()
    return
  }
  const prefs = loadPrefs()
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'practice',
    mode: 'timed',
    durationSec: resolvePracticeDurationSec(prefs),
    lang: prefs.lang,
    difficulty: prefs.difficulty,
    customText: '',
    sourceType: 'catalog',
  }))
  router.replace({ name: 'TypingPlay' })
}

function goRanked() {
  const meta = getRankedMeta()
  sessionStorage.setItem('orep_typing_session_cfg', JSON.stringify({
    playMode: 'ranked',
    mode: 'timed',
    durationSec: meta.durationSec,
    lang: 'zh',
    difficulty: 2,
    customText: meta.text,
    sourceType: 'ranked',
    textVersion: RANKED_TEXT_VERSION,
  }))
  router.replace({ name: 'TypingPlay' })
}

function goHome() {
  router.push({ name: 'TypingPractice' })
}
</script>

<style scoped>
.tr-page {
  --ink: #111827;
  --ink-2: #374151;
  --muted: #6b7280;
  --line: #e8eaed;
  --soft: #f6f7f9;
  --accent: #e5481d;
  --radius: 14px;
}

.tr {
  display: grid;
  gap: 12px;
  width: 100%;
  max-width: 880px;
  margin: 0 auto;
}

/* Hero score */
.tr-hero {
  padding: 18px 18px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
.tr-hero__main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px 28px;
}
.tr-score {
  display: grid;
  gap: 2px;
  min-width: 100px;
}
.tr-score strong {
  font-size: clamp(36px, 6vw, 48px);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.tr-score span {
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.04em;
}
.tr-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  flex: 1;
}
.tr-metrics > div {
  min-width: 72px;
  display: grid;
  gap: 2px;
}
.tr-metrics strong {
  font-size: 20px;
  font-weight: 750;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}
.tr-metrics span {
  font-size: 11px;
  font-weight: 650;
  color: var(--muted);
}
.tr-rank-line {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--ink-2);
}
.tr-rank-line b {
  color: var(--accent);
  font-weight: 800;
}
.tr-today {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
}
.tr-warn {
  margin: 10px 0 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  font-size: 12px;
  line-height: 1.45;
}

/* Cards */
.tr-card {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}
.tr-card__head {
  margin-bottom: 12px;
}
.tr-card__head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 750;
  color: var(--ink);
}
.tr-card__head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
}

.tr-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-items: start;
}

/* Coach */
.tr-coach {
  border-color: color-mix(in srgb, #fed7aa 55%, var(--line));
  background: linear-gradient(160deg, #fff7ed 0%, #fff 48%);
}
.tr-coach.is-great {
  border-color: color-mix(in srgb, #6ee7b7 40%, var(--line));
  background: linear-gradient(160deg, #ecfdf5 0%, #fff 48%);
}
.tr-coach.is-focus {
  border-color: color-mix(in srgb, #fca5a5 40%, var(--line));
  background: linear-gradient(160deg, #fef2f2 0%, #fff 50%);
}
.tr-coach__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.tr-coach__badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 750;
  color: #c2410c;
  letter-spacing: 0.03em;
}
.tr-coach.is-great .tr-coach__badge { color: #047857; }
.tr-coach.is-focus .tr-coach__badge { color: #b91c1c; }
.tr-coach__badge i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 18%, transparent);
}
.tr-coach__src {
  font-size: 11px;
  font-weight: 650;
  color: var(--muted);
}
.tr-coach h2 {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 750;
  letter-spacing: -0.02em;
  color: var(--ink);
  line-height: 1.35;
}
.tr-coach__summary {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--ink-2);
}

.tr-issues {
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}
.tr-issues li {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.8);
}
.tr-issues strong {
  display: block;
  margin-bottom: 3px;
  font-size: 13px;
  color: var(--ink);
}
.tr-issues span {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}

.tr-tips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}
.tr-tips span {
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: #fff;
  font-size: 12px;
  color: var(--ink-2);
  line-height: 1.35;
}

.tr-rx {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, #fdba74 40%, var(--line));
  background: #fff;
}
.tr-rx__copy { min-width: 0; flex: 1; }
.tr-rx__copy small {
  display: block;
  margin-bottom: 3px;
  font-size: 11px;
  font-weight: 750;
  color: #c2410c;
  letter-spacing: 0.03em;
}
.tr-rx__copy strong {
  display: block;
  font-size: 14px;
  color: var(--ink);
  margin-bottom: 3px;
}
.tr-rx__copy p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
}

/* Errors */
.tr-errors {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
}
.tr-errors li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--soft);
}
.tr-errors .ch {
  font-family: ui-monospace, "Cascadia Code", Consolas, Menlo, monospace;
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
}
.tr-errors .n {
  font-size: 12px;
  font-weight: 650;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

/* Board */
.tr-board {
  list-style: none;
  margin: 0;
  padding: 0;
}
.tr-board li {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 34px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  padding: 2px 0;
}
.tr-board li:last-child { border-bottom: 0; }
.tr-board li.is-me {
  background: color-mix(in srgb, #fff7ed 70%, transparent);
  margin: 0 -6px;
  padding: 2px 6px;
  border-radius: 8px;
}
.tr-board__n {
  color: var(--muted);
  font-weight: 750;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
.tr-board strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 650;
  color: var(--ink);
}
.tr-board em {
  font-style: normal;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
  font-size: 12px;
}

/* Buttons */
.tr-btn {
  appearance: none;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 8px 16px;
  font: 650 13px/1 inherit;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, filter 0.15s;
}
.tr-btn--primary {
  background: var(--accent);
  color: #fff;
}
.tr-btn--primary:hover { filter: brightness(0.96); }
.tr-btn--ghost {
  background: #fff;
  border-color: var(--line);
  color: var(--ink);
}
.tr-btn--ghost:hover { background: var(--soft); }
.tr-btn--lg {
  min-height: 42px;
  padding: 0 18px;
  font-size: 14px;
  font-weight: 700;
}
.tr-btn--block {
  width: 100%;
  min-height: 36px;
}

.tr-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 4px;
}

.tr-empty {
  max-width: 420px;
  margin: 40px auto;
  padding: 32px 24px;
  text-align: center;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #fff;
  display: grid;
  gap: 8px;
  justify-items: center;
}
.tr-empty strong {
  font-size: 16px;
  color: var(--ink);
}
.tr-empty p {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--muted);
}

@media (max-width: 720px) {
  .tr-grid { grid-template-columns: 1fr; }
  .tr-rx {
    flex-direction: column;
    align-items: stretch;
  }
  .tr-actions { flex-direction: column; }
  .tr-actions .tr-btn { width: 100%; }
}
</style>
