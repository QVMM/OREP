<template>
  <div class="playback-page" :class="{ 'is-embedded': embedded, 'teacher-page': !embedded }">
    <header v-if="!embedded" class="teacher-page__head">
      <div>
        <h1>录制回放</h1>
        <p>
          会议录制与上传/在线评分视频共用同一库，不重复录制。可回放、跳转评分报告。
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          刷新
        </button>
        <router-link class="teacher-btn teacher-btn--primary" to="/review/reports?tab=upload">
          上传评分视频
        </router-link>
      </div>
    </header>

    <div v-else class="embed-toolbar">
      <p class="embed-hint">会议录制与评分上传视频同一库，不重复存储。可回放、跳转评分报告。</p>
      <div class="embed-actions">
        <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" :disabled="loading" @click="load">
          刷新
        </button>
        <router-link class="teacher-btn teacher-btn--primary teacher-btn--sm" to="/review/reports?tab=upload">
          上传评分视频
        </router-link>
      </div>
    </div>

    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>

    <section class="kpi-strip" aria-label="回放概览">
      <article class="teacher-card teacher-metric-card">
        <small>全部</small>
        <strong>{{ list.length }}</strong>
        <em>录制 + 评分视频</em>
      </article>
      <article class="teacher-card teacher-metric-card">
        <small>可回放</small>
        <strong class="is-accent">{{ readyCount }}</strong>
        <em>有可播放文件</em>
      </article>
      <article class="teacher-card teacher-metric-card">
        <small>处理中</small>
        <strong>{{ processingCount }}</strong>
        <em>生成或评分中</em>
      </article>
      <article class="teacher-card teacher-metric-card">
        <small>累计时长</small>
        <strong class="kpi-sm">{{ totalDurationLabel }}</strong>
        <em>{{ totalSizeLabel }}</em>
      </article>
    </section>

    <section class="toolbar teacher-card">
      <div class="toolbar__inner">
        <input v-model.trim="query" type="search" placeholder="搜索标题、项目、来源…" />
        <div class="status-tabs" role="tablist">
          <button
            v-for="tab in statusTabs"
            :key="tab.key"
            type="button"
            role="tab"
            :class="{ 'is-active': statusFilter === tab.key }"
            @click="statusFilter = tab.key"
          >
            {{ tab.label }}
            <b>{{ tab.count }}</b>
          </button>
        </div>
      </div>
    </section>

    <div v-if="loading" class="teacher-empty">正在加载回放库…</div>

    <div v-else-if="!list.length" class="teacher-card empty-panel">
      <strong>还没有可回放的视频</strong>
      <p>路演会议录制、或在评分报告中上传视频评分后，会出现在这里。同一视频只存一份。</p>
      <div class="empty-actions">
        <router-link
          v-if="!embedded"
          class="teacher-btn teacher-btn--primary"
          to="/roadshow"
        >去路演场次</router-link>
        <button
          v-else
          type="button"
          class="teacher-btn teacher-btn--primary"
          @click="$emit('switch-tab', 'sessions')"
        >去场次列表</button>
        <router-link class="teacher-btn teacher-btn--secondary" to="/review/reports?tab=upload">上传评分</router-link>
      </div>
    </div>

    <div v-else-if="!filtered.length" class="teacher-card empty-panel compact">
      <strong>没有匹配项</strong>
      <p>换个关键词或状态筛选再试。</p>
    </div>

    <div v-else class="playback-layout">
      <!-- 列表 -->
      <section class="teacher-card list-panel">
        <div class="teacher-card__head">
          <h2>回放列表</h2>
          <span>{{ filtered.length }} 条</span>
        </div>
        <div class="list-body">
          <button
            v-for="(item, index) in filtered"
            :key="item.id"
            type="button"
            class="rec-item"
            :class="{ 'is-active': activeId === item.id }"
            @click="select(item)"
          >
            <span class="rec-item__idx">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="rec-item__main">
              <div class="rec-item__top">
                <strong>{{ item.title || '未命名' }}</strong>
                <span class="source-pill" :data-source="item.source">{{ item.sourceLabel || sourceLabel(item) }}</span>
              </div>
              <small>
                {{ formatDate(item.recordedAt) }}
                <template v-if="item.teamName"> · {{ item.teamName }}</template>
                <template v-if="item.durationSeconds"> · {{ formatDuration(item.durationSeconds) }}</template>
              </small>
            </div>
            <span class="status-pill" :data-status="item.status">{{ statusText(item.status) }}</span>
          </button>
        </div>
      </section>

      <!-- 播放器 -->
      <section class="teacher-card player-panel">
        <template v-if="active">
          <div class="teacher-card__head">
            <div>
              <h2>{{ active.title }}</h2>
              <p class="head-sub">
                {{ active.sourceLabel || sourceLabel(active) }}
                <template v-if="active.teamName"> · {{ active.teamName }}</template>
                · {{ formatDate(active.recordedAt) }}
              </p>
            </div>
            <div class="head-actions">
              <a
                v-if="active.reportId || active.sessionId"
                class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                :href="reportHref(active)"
                target="_blank"
                rel="noopener"
              >评分报告</a>
              <a
                v-if="active.meetingId"
                class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                :href="meetingHref(active.meetingId)"
                target="_blank"
                rel="noopener"
              >进会页</a>
            </div>
          </div>

          <div class="teacher-card__body player-body">
            <div v-if="playError" class="plan-notice is-error">{{ playError }}</div>

            <div v-if="!canPlay(active)" class="player-placeholder">
              <strong>{{ statusText(active.status) }}</strong>
              <p v-if="active.errorMessage">{{ active.errorMessage }}</p>
              <p v-else>文件尚未就绪，请稍后再刷新。上传评分与会议录制会自动出现在此列表。</p>
            </div>

            <template v-else>
              <div class="video-shell">
                <video
                  ref="videoEl"
                  class="video-el"
                  controls
                  playsinline
                  :src="playbackSrc"
                  @error="onVideoError"
                />
              </div>
              <div class="meta-grid">
                <div><span>来源</span><strong>{{ active.sourceLabel || sourceLabel(active) }}</strong></div>
                <div><span>状态</span><strong>{{ statusText(active.status) }}</strong></div>
                <div><span>时长</span><strong>{{ formatDuration(active.durationSeconds) || '—' }}</strong></div>
                <div><span>大小</span><strong>{{ formatSize(active.sizeBytes) || '—' }}</strong></div>
                <div v-if="active.meetingId"><span>会议</span><strong>#{{ active.meetingId }}</strong></div>
                <div v-if="active.sessionId"><span>评分会话</span><strong>#{{ active.sessionId }}</strong></div>
              </div>
            </template>
          </div>
        </template>

        <div v-else class="player-empty">
          <strong>选择左侧一条视频</strong>
          <p>支持会议录制与上传评分视频，共用服务器上已有文件。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { fetchTeacherRecordings } from '../../api'
import { getToken } from '../../utils/auth'
import { studentAiReportUrl, studentMeetingUrl } from '../../utils/studentApp'

defineProps({
  /** 嵌入路演场次页时隐藏独立页头，避免双层导航 */
  embedded: { type: Boolean, default: false },
})
defineEmits(['switch-tab'])

const list = ref([])
const loading = ref(false)
const error = ref('')
const query = ref('')
const statusFilter = ref('all')
const activeId = ref('')
const playbackSrc = ref('')
const playError = ref('')
const videoEl = ref(null)
let blobUrl = ''

const active = computed(() => list.value.find((x) => x.id === activeId.value) || null)

const readyCount = computed(() => list.value.filter((x) => canPlay(x)).length)
const processingCount = computed(() => list.value.filter((x) => x.status === 'PROCESSING').length)
const failedCount = computed(() => list.value.filter((x) => x.status === 'FAILED').length)

const totalDurationSeconds = computed(() =>
  list.value.reduce((sum, x) => sum + (Number(x.durationSeconds) || 0), 0)
)
const totalSizeBytes = computed(() =>
  list.value.reduce((sum, x) => sum + (Number(x.sizeBytes) || 0), 0)
)
const totalDurationLabel = computed(() => formatDuration(totalDurationSeconds.value) || '—')
const totalSizeLabel = computed(() => formatSize(totalSizeBytes.value) || '—')

const statusTabs = computed(() => [
  { key: 'all', label: '全部', count: list.value.length },
  { key: 'READY', label: '可回放', count: readyCount.value },
  { key: 'PROCESSING', label: '处理中', count: processingCount.value },
  { key: 'FAILED', label: '失败', count: failedCount.value },
])

const filtered = computed(() => {
  const q = query.value.toLowerCase()
  return list.value.filter((item) => {
    if (statusFilter.value !== 'all' && item.status !== statusFilter.value) return false
    if (!q) return true
    return [
      item.title,
      item.teamName,
      item.sourceLabel,
      item.meetingId,
      item.sessionId,
      item.sessionNo,
    ]
      .join(' ')
      .toLowerCase()
      .includes(q)
  })
})

function sourceLabel(item) {
  if (item?.source === 'AI_UPLOAD') return '评分视频'
  if (item?.source === 'MEETING_RECORDING') return '会议录制'
  return item?.sourceLabel || '视频'
}

function statusText(status) {
  const map = {
    READY: '可回放',
    PROCESSING: '处理中',
    FAILED: '失败',
    UNKNOWN: '未知',
  }
  return map[status] || status || '未知'
}

function canPlay(item) {
  if (!item) return false
  if (item.ready === false) return false
  if (item.status === 'FAILED') return false
  return Boolean(item.playUrl || item.streamApi || item.filePath || item.cameraFile || item.screenFile)
}

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDuration(seconds) {
  const n = Math.max(0, Math.round(Number(seconds) || 0))
  if (!n) return ''
  const m = Math.floor(n / 60)
  const s = n % 60
  if (m >= 60) {
    const h = Math.floor(m / 60)
    return `${h} 时 ${m % 60} 分`
  }
  return s ? `${m} 分 ${s} 秒` : `${m} 分`
}

function formatSize(bytes) {
  const n = Number(bytes) || 0
  if (!n) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function reportHref(item) {
  return studentAiReportUrl({
    reportId: item.reportId,
    sessionId: item.sessionId,
    meetingId: item.meetingId,
  })
}

function meetingHref(meetingId) {
  return studentMeetingUrl(meetingId)
}

function revokeBlob() {
  if (blobUrl) {
    URL.revokeObjectURL(blobUrl)
    blobUrl = ''
  }
  playbackSrc.value = ''
}

async function select(item) {
  activeId.value = item.id
  playError.value = ''
  await startPlayback(item)
}

async function startPlayback(item) {
  revokeBlob()
  if (!canPlay(item)) return

  // 优先直链 /uploads
  const direct = item.playUrl || (String(item.filePath || '').startsWith('/uploads/') ? item.filePath : '')
  if (direct && (direct.startsWith('/uploads/') || direct.startsWith('http') || direct.startsWith('blob:'))) {
    const token = getToken()
    playbackSrc.value = (token && String(direct).includes('/uploads/ai-score/'))
      ? `${direct}${direct.includes('?') ? '&' : '?'}t=${encodeURIComponent(token)}`
      : direct
    await nextTick()
    return
  }

  // 会议录制：鉴权 stream
  if (item.streamApi) {
    try {
      const token = getToken()
      const res = await fetch(item.streamApi, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error('无法获取播放流')
      const blob = await res.blob()
      blobUrl = URL.createObjectURL(blob)
      playbackSrc.value = blobUrl
    } catch (e) {
      playError.value = e?.message || '播放失败'
    }
  }
}

function onVideoError() {
  playError.value = '视频无法播放，文件可能缺失或格式不受支持'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const rows = await fetchTeacherRecordings()
    list.value = Array.isArray(rows) ? rows : []
    if (activeId.value) {
      const still = list.value.find((x) => x.id === activeId.value)
      if (still) await startPlayback(still)
      else {
        activeId.value = list.value[0]?.id || ''
        if (list.value[0]) await startPlayback(list.value[0])
      }
    } else if (list.value[0] && canPlay(list.value[0])) {
      activeId.value = list.value[0].id
      await startPlayback(list.value[0])
    }
  } catch (e) {
    error.value = e?.message || '回放库加载失败'
    list.value = []
  } finally {
    loading.value = false
  }
}

watch(activeId, () => {
  playError.value = ''
})

onUnmounted(() => {
  revokeBlob()
})

load()
</script>

<style scoped>
.playback-page.is-embedded {
  min-width: 0;
}
.embed-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.embed-hint {
  margin: 0;
  flex: 1;
  min-width: 200px;
  font-size: 13px;
  color: var(--ds-muted);
  line-height: 1.5;
}
.embed-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plan-notice {
  margin: 0 0 14px;
  padding: 11px 14px;
  border-radius: 11px;
  font-size: 12px;
  font-weight: 700;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}

.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.kpi-sm {
  font-size: 18px !important;
  letter-spacing: 0 !important;
}

.toolbar {
  margin-bottom: 16px;
}
.toolbar__inner {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
}
.toolbar input[type='search'] {
  box-sizing: border-box;
  flex: 1;
  min-width: 200px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 10px;
  font: 500 13px var(--ds-font-sans);
}
.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.status-tabs button {
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--ds-line);
  border-radius: 999px;
  background: #fff;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: 700 12px var(--ds-font-sans);
  color: var(--ds-ink-2);
  cursor: pointer;
}
.status-tabs button b {
  font-variant-numeric: tabular-nums;
  color: var(--ds-muted);
}
.status-tabs button.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.status-tabs button.is-active b {
  color: var(--ds-orange-deep);
}

.playback-layout {
  display: grid;
  grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.list-body {
  max-height: min(70vh, 760px);
  overflow: auto;
  padding: 10px 12px 14px;
  display: grid;
  gap: 8px;
}
.rec-item {
  width: 100%;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
  padding: 12px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  font: inherit;
  transition: border-color 0.15s, background 0.15s;
}
.rec-item:hover {
  border-color: rgba(232, 74, 28, 0.35);
}
.rec-item.is-active {
  border-color: var(--ds-orange);
  background: #fffaf7;
  box-shadow: inset 3px 0 0 var(--ds-orange);
}
.rec-item__idx {
  color: var(--ds-faint);
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  padding-top: 2px;
}
.rec-item__main {
  min-width: 0;
  display: grid;
  gap: 4px;
}
.rec-item__top {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
}
.rec-item strong {
  font-size: 13px;
  color: var(--ds-ink);
  line-height: 1.35;
}
.rec-item small {
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.4;
}

.source-pill {
  flex: 0 0 auto;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  background: #f3f4f6;
  color: #4b5563;
}
.source-pill[data-source='AI_UPLOAD'] {
  background: #eff6ff;
  color: #1d4ed8;
}
.source-pill[data-source='MEETING_RECORDING'] {
  background: #ecfdf5;
  color: #047857;
}

.status-pill {
  flex: 0 0 auto;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
  background: #f3f4f6;
  color: #4b5563;
}
.status-pill[data-status='READY'] {
  background: #e8f8f0;
  color: #0f6b4c;
}
.status-pill[data-status='PROCESSING'] {
  background: #fff7ed;
  color: #c2410c;
}
.status-pill[data-status='FAILED'] {
  background: #fff1f0;
  color: #d14343;
}

.player-panel .teacher-card__head {
  align-items: flex-start;
}
.head-sub {
  margin: 4px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.player-body {
  display: grid;
  gap: 14px;
}
.video-shell {
  border-radius: 14px;
  overflow: hidden;
  background: #0f1115;
  aspect-ratio: 16 / 9;
}
.video-el {
  width: 100%;
  height: 100%;
  display: block;
  background: #000;
  object-fit: contain;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.meta-grid > div {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f7f8f9;
  border: 1px solid var(--ds-line);
  display: grid;
  gap: 4px;
}
.meta-grid span {
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}
.meta-grid strong {
  font-size: 13px;
  color: var(--ds-ink);
}
.player-placeholder,
.player-empty {
  padding: 48px 20px;
  text-align: center;
  display: grid;
  gap: 8px;
  justify-items: center;
  color: var(--ds-muted);
}
.player-placeholder strong,
.player-empty strong {
  color: var(--ds-ink);
  font-size: 15px;
}
.player-placeholder p,
.player-empty p {
  margin: 0;
  max-width: 360px;
  font-size: 13px;
  line-height: 1.55;
}

.empty-panel {
  padding: 48px 24px;
  text-align: center;
  display: grid;
  gap: 10px;
  justify-items: center;
}
.empty-panel.compact {
  padding: 32px 20px;
}
.empty-panel strong {
  font-size: 16px;
}
.empty-panel p {
  margin: 0;
  max-width: 420px;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.55;
}
.empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}

@media (max-width: 960px) {
  .kpi-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .playback-layout {
    grid-template-columns: 1fr;
  }
  .list-body {
    max-height: 320px;
  }
  .meta-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
