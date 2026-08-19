<template>
  <section class="student-card training-learning-card">
    <button type="button" class="training-learning-card__head" :aria-expanded="!collapsed" @click="collapsed = !collapsed">
      <span class="training-flow-number">01</span>
      <div><h2>今日学习</h2><p>{{ summaryText }}</p></div>
      <span class="training-learning-card__progress" :class="{ 'is-incomplete': completedCount < localResources.length }">
        {{ learningProgressLabel }}
      </span>
      <span class="training-learning-card__toggle">{{ collapsed ? '展开' : '收起' }}</span>
    </button>

    <div v-if="!collapsed" class="training-learning-list">
      <article v-for="item in localResources" :key="item.id" class="training-learning-item" :class="{ 'is-complete': isComplete(item) }">
        <div class="training-learning-item__signal">
          <CircleCheck v-if="isComplete(item)" />
          <VideoPlay v-else-if="item.resourceType === 'VIDEO' || item.resourceType === 'EMBED_VIDEO'" />
          <Document v-else-if="item.resourceType === 'DOCUMENT'" />
          <Link v-else />
        </div>
        <div class="training-learning-item__copy">
          <div class="training-learning-item__heading">
            <div class="training-learning-item__identity">
              <h3>{{ item.title }}</h3>
              <small>
                {{ typeLabel(item.resourceType, item.provider) }}
                <template v-if="item.resourceType === 'VIDEO' || item.resourceType === 'EMBED_VIDEO'">
                  · 已学习 {{ formatDuration(item.actualLearningSeconds) }}
                </template>
                <template v-else-if="item.durationSeconds"> · 预计 {{ Math.max(1, Math.ceil(item.durationSeconds / 60)) }} 分钟</template>
                <template v-if="item.progressPercent"> · {{ item.resourceType === 'EMBED_VIDEO' ? '进度' : '已覆盖' }} {{ item.progressPercent }}%</template>
              </small>
            </div>
            <span
              v-if="item.resourceType === 'VIDEO' || item.resourceType === 'EMBED_VIDEO'"
              class="training-learning-progress-ring"
              :style="{ '--learning-progress': `${videoProgress(item) * 3.6}deg` }"
              :aria-label="`学习进度 ${videoProgress(item)}%`"
              role="img"
            ><b>{{ videoProgress(item) }}%</b></span>
            <span :class="{ 'is-required': required(item) }">{{ required(item) ? '必学' : '选学' }}</span>
          </div>
          <p v-if="item.description">{{ item.description }}</p>
        </div>
        <div v-if="!isPlayable(item) || isComplete(item)" class="training-learning-item__actions">
          <a
            v-if="item.resourceType === 'DOCUMENT' && isDownloadOnly(item)"
            :href="withAuthMediaUrl(item.resourceUrl)"
            target="_blank"
            rel="noopener"
            :download="item.fileName || ''"
          >下载资料</a>
          <button v-else-if="item.resourceType === 'DOCUMENT'" type="button" @click="previewDocument(item)">预览资料</button>
          <a
            v-else-if="item.resourceType === 'LINK'"
            class="is-link-action"
            :href="item.resourceUrl"
            target="_blank"
            rel="noopener"
            @click="openedLinks.add(item.id)"
          >
            <Link />
            打开链接
          </a>
          <a
            v-else-if="item.resourceType === 'EMBED_VIDEO' && item.resourceUrl"
            class="is-link-action"
            :href="item.resourceUrl"
            target="_blank"
            rel="noopener"
          >
            <Link />
            原站打开
          </a>
          <button
            v-if="canMarkComplete(item) && !isComplete(item)"
            type="button"
            class="is-complete-action"
            :disabled="savingId === item.id || (item.resourceType === 'LINK' && !openedLinks.has(item.id))"
            :title="item.resourceType === 'LINK' && !openedLinks.has(item.id) ? '请先打开链接再标记已学' : undefined"
            @click="markComplete(item)"
          >{{ savingId === item.id ? '保存中…' : '标记已学' }}</button>
          <span v-if="isComplete(item)" class="training-learning-item__done"><CircleCheck /> 已完成</span>
        </div>
        <p
          v-if="item.resourceType === 'LINK' && !isComplete(item) && !openedLinks.has(item.id)"
          class="training-learning-item__hint"
        >请先打开链接浏览，再点「标记已学」</p>
        <div v-if="item.resourceType === 'VIDEO'" class="training-learning-item__player">
          <TrainingVideoPlayer
            :resource="item"
            @heartbeat="syncVideo($event.video, item, $event.force, $event.reset)"
            @restricted="showSeekRestriction"
          />
        </div>
        <div v-else-if="item.resourceType === 'EMBED_VIDEO'" class="training-learning-item__player">
          <TrainingEmbedPlayer :resource="item" @change="replaceResource" />
        </div>
      </article>
    </div>
    <div v-if="notice" class="training-learning-card__notice" :class="{ 'is-error': error }">{{ notice }}</div>
    <FilePreview v-model:visible="preview.visible" :file-url="preview.fileUrl" :file-name="preview.fileName" :file-type="preview.fileType" />
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { CircleCheck, Document, Link, VideoPlay } from '@element-plus/icons-vue'
import FilePreview from '../../../components/FilePreview.vue'
import TrainingVideoPlayer from './TrainingVideoPlayer.vue'
import TrainingEmbedPlayer from './TrainingEmbedPlayer.vue'
import { withAuthMediaUrl } from '../../../utils/mediaUrl'
import { completeTrainingLearningResource, updateTrainingLearningProgress } from '../api'

const props = defineProps({ resources: { type: Array, default: () => [] } })
const emit = defineEmits(['change'])
const localResources = ref([])
const collapsed = ref(false)
const savingId = ref(null)
const openedLinks = reactive(new Set())
const lastSyncAt = new Map()
const videoSessionId = globalThis.crypto?.randomUUID?.() || `session_${Date.now()}_${Math.random().toString(36).slice(2)}`
const notice = ref('')
const error = ref(false)
const preview = reactive({ visible: false, fileUrl: '', fileName: '', fileType: '' })
const DOWNLOAD_ONLY_EXTENSIONS = new Set(['zip', 'rar', '7z'])

watch(() => props.resources, value => {
  localResources.value = (value || []).map(item => ({ ...item }))
}, { immediate: true, deep: true })

const completedCount = computed(() => localResources.value.filter(isComplete).length)
const requiredCount = computed(() => localResources.value.filter(required).length)
const estimatedMinutes = computed(() => Math.ceil(localResources.value.reduce((sum, item) => sum + Number(item.durationSeconds || 0), 0) / 60))
const summaryText = computed(() => [`${localResources.value.length} 项内容`, `${requiredCount.value} 项必学`, estimatedMinutes.value ? `预计 ${estimatedMinutes.value} 分钟` : ''].filter(Boolean).join(' · '))
const learningProgressLabel = computed(() => {
  const total = localResources.value.length
  if (completedCount.value >= total && total > 0) return `${completedCount.value}/${total} 已完成`
  if (completedCount.value === 0) return `0/${total} 未完成`
  return `${completedCount.value}/${total} 项完成`
})

function required(item) { return item?.required === true || Number(item?.required) === 1 }
function isComplete(item) { return item?.learningStatus === 'COMPLETED' || Number(item?.progressPercent) >= 100 }
function videoProgress(item) { return Math.max(0, Math.min(100, Number(item?.progressPercent || 0))) }
function formatDuration(value) {
  const seconds = Math.max(0, Number(value || 0))
  if (seconds < 60) return `${Math.floor(seconds)} 秒`
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60)
  return remainder ? `${minutes} 分 ${remainder} 秒` : `${minutes} 分钟`
}
function typeLabel(type, provider) {
  if (type === 'EMBED_VIDEO') {
    return String(provider || '').toUpperCase() === 'BILIBILI' ? 'B站视频' : '站外视频'
  }
  return { VIDEO: '视频', DOCUMENT: '资料', LINK: '外部链接' }[type] || '学习内容'
}
function isPlayable(item) {
  return item?.resourceType === 'VIDEO' || item?.resourceType === 'EMBED_VIDEO'
}
function canMarkComplete(item) {
  // 站内视频 / 站外内嵌靠进度自动完成；文档与外链可标记已学
  return item?.resourceType === 'DOCUMENT' || item?.resourceType === 'LINK'
}
function fileExtension(item) {
  const source = String(item?.fileName || item?.resourceUrl || '').split(/[?#]/)[0]
  const index = source.lastIndexOf('.')
  return index < 0 ? '' : source.slice(index + 1).toLowerCase()
}
function isDownloadOnly(item) { return DOWNLOAD_ONLY_EXTENSIONS.has(fileExtension(item)) }
function previewDocument(item) {
  // FilePreview uses fetch + native media tags; protected learning URLs need ?t=
  Object.assign(preview, {
    visible: true,
    fileUrl: withAuthMediaUrl(item.resourceUrl),
    fileName: item.fileName || item.title,
    fileType: item.mimeType || ''
  })
}
async function markComplete(item) {
  savingId.value = item.id; notice.value = ''; error.value = false
  try {
    replaceResource(await completeTrainingLearningResource(item.id))
    notice.value = `“${item.title}”已标记为完成`
  } catch (err) {
    error.value = true
    notice.value = err?.response?.data?.message || err?.message || '学习进度保存失败'
  } finally { savingId.value = null }
}
async function syncVideo(video, item, force = false, reset = false) {
  if (!Number.isFinite(video.duration) || video.duration <= 0) return
  const now = Date.now()
  if (!force && now - Number(lastSyncAt.get(item.id) || 0) < 5000) return
  lastSyncAt.set(item.id, now)
  try {
    replaceResource(await updateTrainingLearningProgress(item.id, {
      sessionId: videoSessionId,
      positionSeconds: Math.floor(video.currentTime),
      durationSeconds: Math.floor(video.duration),
      reset
    }))
  } catch {
    error.value = true
    notice.value = '播放进度暂未同步，恢复网络后继续播放即可重试。'
  }
}
function showSeekRestriction() {
  error.value = false
  notice.value = '未学习的部分不能直接跳过，可拖回已经学习过的位置复习。'
}
function replaceResource(updated) {
  localResources.value = localResources.value.map(item => item.id === updated.id ? { ...item, ...updated } : item)
  emit('change', localResources.value)
}
</script>

<style scoped>
.training-learning-card{overflow:hidden}.training-learning-card__head{box-sizing:border-box;width:100%;min-height:84px;padding:18px 20px;border:0;display:grid;grid-template-columns:34px minmax(0,1fr) auto auto;gap:12px;align-items:center;text-align:left;color:inherit;background:transparent;cursor:pointer}.training-flow-number{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;color:#fff;background:var(--ds-orange);font-size:10px;font-weight:900}.training-learning-card__head h2{margin:0;font-size:17px}.training-learning-card__head p{margin:4px 0 0;color:var(--ds-muted);font-size:11px}.training-learning-card__progress{padding:5px 9px;border-radius:999px;color:#0b7753;background:#e6f6ef;font-size:10px;font-weight:800}.training-learning-card__progress.is-incomplete{color:var(--ds-orange-deep);background:var(--ds-orange-wash)}.training-learning-card__toggle{color:var(--ds-muted);font-size:11px}.training-learning-list{border-top:1px solid var(--ds-line)}.training-learning-item{padding:14px 20px;display:grid;grid-template-columns:38px minmax(0,1fr) auto;gap:12px;align-items:center;border-bottom:1px solid var(--ds-line)}.training-learning-item:last-child{border-bottom:0}.training-learning-item__signal{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;color:var(--ds-orange);background:var(--ds-orange-wash)}.training-learning-item__signal svg{width:17px}.training-learning-item.is-complete .training-learning-item__signal{color:#0b8c63;background:#e6f6ef}.training-learning-item__copy{min-width:0}.training-learning-item__heading{display:flex;align-items:center;gap:7px}.training-learning-item__identity{min-width:0;display:grid;gap:2px}.training-learning-item__copy h3{overflow:hidden;margin:0;font-size:13px;line-height:1.25;text-overflow:ellipsis;white-space:nowrap}.training-learning-item__copy span{padding:3px 6px;border-radius:999px;color:var(--ds-muted);background:var(--ds-surface-soft);font-size:9px}.training-learning-item__copy span.is-required{color:var(--ds-orange-deep);background:var(--ds-orange-wash)}.training-learning-item__copy p{margin:5px 0 0;color:var(--ds-ink-soft);font-size:11px}.training-learning-item__copy small{color:var(--ds-muted);font-size:10px;line-height:1.2}.training-learning-item__actions{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:8px}.training-learning-item__actions button,.training-learning-item__actions a{box-sizing:border-box;min-height:34px;padding:0 14px;border:1px solid var(--ds-btn-secondary-border,var(--ds-line));border-radius:var(--ds-radius-pill,999px);color:var(--ds-btn-secondary-fg,var(--ds-ink));background:var(--ds-btn-secondary-bg,#fff);font-size:12px;font-weight:700;line-height:1;text-decoration:none;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;transition:background-color .15s,border-color .15s,color .15s,box-shadow .15s}.training-learning-item__actions a.is-link-action{color:var(--ds-orange-800,#9f2c0a);border-color:color-mix(in srgb,var(--ds-orange,#e5481d) 35%,var(--ds-line,#e5e7eb));background:var(--ds-orange-wash,#fff7ed);font-weight:750}.training-learning-item__actions a.is-link-action:hover{border-color:var(--ds-orange,#e5481d);background:var(--ds-orange-soft,#ffedd5);color:var(--ds-orange-900,#7c2d12)}.training-learning-item__actions a.is-link-action svg{width:14px;height:14px;flex:none}.training-learning-item__actions .is-complete-action{color:#fff;border-color:var(--ds-btn-primary-bg,var(--ds-orange));background:var(--ds-btn-primary-bg,var(--ds-orange))}.training-learning-item__actions .is-complete-action:hover:not(:disabled){background:var(--ds-btn-primary-bg-hover,var(--ds-orange-deep,#c43a12));border-color:var(--ds-btn-primary-bg-hover,var(--ds-orange-deep,#c43a12))}.training-learning-item__actions button:disabled{opacity:.45;cursor:not-allowed}.training-learning-item__hint{grid-column:2/-1;margin:0;padding:0 2px;color:var(--ds-muted);font-size:11px;line-height:1.4;font-weight:550}.training-learning-item__done{display:flex;align-items:center;gap:4px;color:#0b7753;font-size:12px;font-weight:800}.training-learning-item__done svg{width:15px}.training-learning-item__player{grid-column:2/-1}.training-learning-card__notice{margin:0 20px 16px;padding:9px 11px;border-radius:9px;color:#0b7753;background:#e6f6ef;font-size:10px}.training-learning-card__notice.is-error{color:#a33a24;background:#fff0ec}@media(max-width:760px){.training-learning-card__head{grid-template-columns:32px minmax(0,1fr);padding:16px}.training-learning-card__progress,.training-learning-card__toggle{grid-column:2}.training-learning-item{grid-template-columns:36px minmax(0,1fr);padding:13px 16px}.training-learning-item__actions,.training-learning-item__player{grid-column:2}.training-learning-item__actions{justify-content:flex-start;flex-wrap:wrap}}
.training-learning-item__player{min-width:0}
.training-learning-item__player{grid-column:1/-1}
.training-learning-progress-ring{box-sizing:border-box!important;width:28px!important;height:28px!important;flex:0 0 28px!important;padding:3px!important;display:grid!important;place-items:center!important;border-radius:50%!important;background:conic-gradient(var(--ds-orange) var(--learning-progress),#eceef1 0)!important;transition:background 320ms ease}
.training-learning-progress-ring::before{grid-area:1/1;width:20px;height:20px;border-radius:50%;background:#fff;content:""}
.training-learning-progress-ring b{grid-area:1/1;z-index:1;color:var(--ds-orange-deep);font-size:8px;line-height:1;font-weight:850}
@media(max-width:760px){.training-learning-item__actions,.training-learning-item__player,.training-learning-item__hint{grid-column:1/-1}.training-learning-item__actions{justify-content:flex-start}}
@media(prefers-reduced-motion:reduce){.training-learning-progress-ring{transition:none}}
</style>
