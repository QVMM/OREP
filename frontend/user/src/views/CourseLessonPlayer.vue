<template>
  <div class="player-page">
    <section class="player-shell" v-loading="loading">
      <header class="player-header">
        <BaseButton type="text" size="small" class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回课程
        </BaseButton>

        <div v-if="course" class="player-title">
          <span>{{ course.category || '课程学习' }} · {{ course.title }}</span>
          <h1>{{ currentLesson?.title || course.title }}</h1>
        </div>

        <div v-if="course" class="course-progress-pill">
          <span>课程进度</span>
          <strong>{{ course.progressPercent || 0 }}%</strong>
        </div>
      </header>

      <main v-if="course && currentLesson" class="player-layout">
        <section class="player-main">
          <div class="video-card">
            <div class="video-frame">
              <video
                v-if="currentLesson.resourceUrl"
                ref="videoRef"
                class="lesson-video"
                :class="{ ready: isVideoReady }"
                :controls="isVideoReady"
                controlsList="nodownload noremoteplayback"
                disablePictureInPicture
                playsinline
                preload="metadata"
                :src="videoPlayUrl"
                @loadstart="resetVideoLoading"
                @loadedmetadata="resumePlayback"
                @canplay="handleVideoReady"
                @play="handlePlay"
                @pause="handlePause"
                @playing="handleVideoReady"
                @waiting="handleVideoWaiting"
                @timeupdate="syncVideoProgress"
                @seeking="guardSeeking"
                @ratechange="guardPlaybackRate"
                @error="handleVideoError"
                @ended="completeLesson"
              ></video>
              <div v-if="currentLesson.resourceUrl && showVideoOverlay" class="video-loader" aria-live="polite">
                <span>{{ videoLoadStep.kicker }}</span>
                <strong>{{ videoLoadStep.title }}</strong>
                <p>{{ videoLoadStep.description }}</p>
              </div>
              <div v-if="!currentLesson.resourceUrl" class="video-empty">
                <strong>视频未上传</strong>
                <p>该课时还没有上传视频，请联系管理员。</p>
              </div>
            </div>
          </div>

          <article class="lesson-summary">
            <BaseButton class="next-btn" :disabled="!nextLesson" @click="switchLesson(nextLesson)">
              下一课时
              <el-icon><ArrowRight /></el-icon>
            </BaseButton>
            <span>当前课时</span>
            <h2>{{ currentLesson.title }}</h2>
            <p>{{ currentLesson.description || lessonDescription }}</p>
            <div class="lesson-summary__meta">
              <small>{{ lessonDurationLabel }}</small>
              <small>{{ syncLabel }}</small>
              <small>{{ currentLesson.completed ? '已完成' : '学习中' }}</small>
            </div>
          </article>
        </section>

        <aside class="player-side">
          <section class="side-panel catalog-panel">
            <header>
              <h2>章节目录</h2>
              <span>{{ allLessons.length }} 节</span>
            </header>
            <div class="catalog-list">
              <template v-for="chapter in course.chapters" :key="chapter.id">
                <strong class="catalog-chapter">{{ chapter.title }}</strong>
                <button
                  v-for="lesson in chapter.lessons"
                  :key="lesson.id"
                  type="button"
                  class="catalog-lesson"
                  :class="{ active: lesson.id === currentLesson.id, completed: lesson.completed }"
                  @click="switchLesson(lesson)"
                >
                  <span>{{ lessonIndex(lesson) }}</span>
                  <b>{{ lesson.title }}</b>
                  <small>{{ lesson.completed ? '已完成' : formatDuration(lesson.durationSeconds) }}</small>
                </button>
              </template>
            </div>
          </section>

          <section class="side-panel note-panel">
            <h2>学习笔记</h2>
            <textarea v-model="lessonNote" placeholder="记录本节关键点、答辩表达或疑问..."></textarea>
            <BaseButton class="panel-action" @click="saveLessonNote">保存笔记</BaseButton>
          </section>

          <section class="side-panel action-panel">
            <h2>课后动作</h2>
            <BaseButton type="secondary" class="panel-action" @click="goBack">回到课程详情</BaseButton>
          </section>
        </aside>
      </main>

      <div v-else-if="!loading" class="missing-panel">
        <span class="kicker">课时不可用</span>
        <p>没有找到该课时，请返回课程目录重新选择。</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import BaseButton from '../components/base/BaseButton.vue'
import request from '../utils/request'
import { getUserToken } from '../utils/authStorage'
import { withAuthMediaUrl } from '../utils/mediaUrl'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const course = ref(null)
const currentLesson = ref(null)
const videoRef = ref(null)
const videoPlayUrl = ref('')
const maxWatchedSeconds = ref(0)
const syncState = ref('ready')
const isVideoReady = ref(false)
const isBuffering = ref(false)
const videoLoadError = ref(false)
const lessonNote = ref('')
let lastProgressSyncAt = 0
let lastWallSyncAt = 0

const allLessons = computed(() => {
  return course.value?.chapters?.flatMap((chapter) => chapter.lessons || []) || []
})

const lessonProgressPercent = computed(() => {
  const duration = Math.max(1, Number(currentLesson.value?.durationSeconds) || 0)
  return Math.min(100, Math.round((maxWatchedSeconds.value * 100) / duration))
})

const syncLabel = computed(() => {
  const labels = {
    ready: '等待播放',
    watching: '正在学习',
    syncing: '同步中',
    synced: '已同步',
    guarded: '已拦截异常进度',
    failed: '同步失败'
  }
  return labels[syncState.value] || '等待播放'
})

const lessonDescription = computed(() => {
  return '本节围绕课程关键知识点展开，帮助你把学习内容转化为路演表达和答辩准备。'
})

const lessonDurationLabel = computed(() => {
  return `${formatDuration(maxWatchedSeconds.value)} / ${formatDuration(currentLesson.value?.durationSeconds)}`
})

const showVideoOverlay = computed(() => {
  return !isVideoReady.value || isBuffering.value || videoLoadError.value
})

const videoLoadStep = computed(() => {
  if (videoLoadError.value) {
    return {
      kicker: '视频加载异常',
      title: '视频暂时无法载入',
      description: '请检查视频文件是否已上传成功，或稍后重新进入课程。'
    }
  }
  if (isBuffering.value) {
    return {
      kicker: '正在缓冲',
      title: '正在补充视频缓冲',
      description: '学习进度通道保持在线，缓冲完成后会继续播放。'
    }
  }
  return {
    kicker: '准备播放',
    title: '正在建立学习会话',
    description: '校验课程权限、接入视频流，并准备实时同步学习进度。'
  }
})

const nextLesson = computed(() => {
  const index = allLessons.value.findIndex((lesson) => lesson.id === currentLesson.value?.id)
  return index >= 0 ? allLessons.value[index + 1] : null
})

onMounted(() => {
  loadCourse()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pagehide', handlePageHide)
  window.addEventListener('beforeunload', handlePageHide)
})

onBeforeUnmount(() => {
  flushProgress({ keepalive: true, silent: true })
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
  window.removeEventListener('beforeunload', handlePageHide)
})

watch(
  () => route.params.lessonId,
  () => {
    pickCurrentLesson()
    lastProgressSyncAt = 0
    lastWallSyncAt = 0
    maxWatchedSeconds.value = 0
    syncState.value = 'ready'
    resetVideoLoading()
    loadLessonNote()
    loadLessonPlayUrl()
  }
)

async function loadCourse() {
  loading.value = true
  try {
    const res = await request.get(`/api/courses/${route.params.courseId}`)
    course.value = res.data
    pickCurrentLesson()
    loadLessonNote()
    loadLessonPlayUrl()
  } finally {
    loading.value = false
  }
}

function pickCurrentLesson() {
  const lessonId = Number(route.params.lessonId)
  currentLesson.value = allLessons.value.find((lesson) => lesson.id === lessonId) || null
  const learnedSeconds = Number(course.value?.learnedSeconds) || 0
  maxWatchedSeconds.value = course.value?.currentLessonId === lessonId ? learnedSeconds : 0
  videoPlayUrl.value = ''
}

async function loadLessonPlayUrl() {
  if (!currentLesson.value?.resourceUrl) return
  try {
    const res = await request.get(`/api/courses/lessons/${currentLesson.value.id}/play-url`, {
      timeout: 20000,
      silentError: true
    })
    videoPlayUrl.value = withAuthMediaUrl(res.data?.videoUrl || currentLesson.value.resourceUrl)
  } catch {
    videoPlayUrl.value = withAuthMediaUrl(currentLesson.value.resourceUrl)
  }
}

async function switchLesson(lesson) {
  if (!lesson || !course.value) return
  await flushProgress({ silent: true })
  await router.push({
    name: 'CourseLessonPlayer',
    params: {
      courseId: course.value.id,
      lessonId: lesson.id
    }
  })
}

function resumePlayback(event) {
  if (!course.value || !currentLesson.value) return
  const learnedSeconds = Number(course.value.learnedSeconds) || 0
  if (course.value.currentLessonId === currentLesson.value.id && learnedSeconds > 0) {
    event.target.currentTime = Math.min(learnedSeconds, Math.max(0, event.target.duration - 1))
    maxWatchedSeconds.value = Math.max(maxWatchedSeconds.value, Math.floor(event.target.currentTime || 0))
  }
}

function resetVideoLoading() {
  isVideoReady.value = false
  isBuffering.value = false
  videoLoadError.value = false
}

function handleVideoReady() {
  isVideoReady.value = true
  isBuffering.value = false
  videoLoadError.value = false
}

function handleVideoWaiting() {
  if (isVideoReady.value) {
    isBuffering.value = true
  }
}

function handleVideoError() {
  videoLoadError.value = true
  isBuffering.value = false
}

async function syncVideoProgress(event) {
  if (!course.value || !currentLesson.value) return
  const current = Math.floor(event.target.currentTime || 0)
  maxWatchedSeconds.value = Math.max(maxWatchedSeconds.value, current)
  const now = Date.now()
  if (Math.abs(current - lastProgressSyncAt) < 5 && now - lastWallSyncAt < 8000) return
  await flushProgress({ learnedSeconds: current })
}

async function completeLesson(event) {
  if (!course.value || !currentLesson.value) return
  const finalSeconds = Math.floor(event?.target?.duration || currentLesson.value.durationSeconds || maxWatchedSeconds.value)
  maxWatchedSeconds.value = Math.max(maxWatchedSeconds.value, finalSeconds)
  await flushProgress({ learnedSeconds: finalSeconds })
  await request.post(`/api/courses/lessons/${currentLesson.value.id}/complete`)
  ElMessage.success('课时已完成')
  await loadCourse()
}

function handlePlay() {
  syncState.value = 'watching'
}

function handlePause() {
  flushProgress({ silent: true })
}

function guardSeeking(event) {
  if (!currentLesson.value || currentLesson.value.completed) return
  const video = event.target
  const current = Math.floor(video.currentTime || 0)
  const allowedForward = maxWatchedSeconds.value + 8
  if (current > allowedForward) {
    video.currentTime = maxWatchedSeconds.value
    syncState.value = 'guarded'
    ElMessage.warning('为保证学习记录有效，请按顺序观看当前课时')
  }
}

function guardPlaybackRate(event) {
  const video = event.target
  if (video.playbackRate > 1.25) {
    video.playbackRate = 1.25
    syncState.value = 'guarded'
    ElMessage.warning('当前课程最高支持 1.25 倍速学习')
  }
}

async function flushProgress(options = {}) {
  if (!course.value || !currentLesson.value) return
  const learnedSeconds = Math.floor(options.learnedSeconds ?? videoRef.value?.currentTime ?? maxWatchedSeconds.value ?? 0)
  maxWatchedSeconds.value = Math.max(maxWatchedSeconds.value, learnedSeconds)
  lastProgressSyncAt = learnedSeconds
  lastWallSyncAt = Date.now()

  const payload = {
    lessonId: currentLesson.value.id,
    learnedSeconds
  }

  if (options.keepalive) {
    const token = getUserToken()
    fetch(`/api/courses/${course.value.id}/progress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(payload),
      keepalive: true
    }).catch(() => {})
    return
  }

  try {
    if (!options.silent) syncState.value = 'syncing'
    await request.post(`/api/courses/${course.value.id}/progress`, payload, {
      timeout: 20000,
      silentError: true
    })
    syncState.value = 'synced'
  } catch (error) {
    syncState.value = 'failed'
    if (!options.silent) throw error
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    flushProgress({ keepalive: true, silent: true })
  }
}

function handlePageHide() {
  flushProgress({ keepalive: true, silent: true })
}

function goBack() {
  router.push(`/course-learning/${route.params.courseId}`)
}

function lessonIndex(lesson) {
  const index = allLessons.value.findIndex((item) => item.id === lesson?.id)
  return index >= 0 ? String(index + 1).padStart(2, '0') : '--'
}

function noteStorageKey() {
  return `orep-course-note:${route.params.courseId}:${route.params.lessonId}`
}

function loadLessonNote() {
  lessonNote.value = localStorage.getItem(noteStorageKey()) || ''
}

function saveLessonNote() {
  localStorage.setItem(noteStorageKey(), lessonNote.value.trim())
  ElMessage.success('笔记已保存')
}

function formatDuration(seconds) {
  const total = Math.max(0, Number(seconds) || 0)
  const minutes = String(Math.floor(total / 60)).padStart(2, '0')
  const rest = String(total % 60).padStart(2, '0')
  return `${minutes}:${rest}`
}
</script>

<style scoped>
.player-page {
  min-height: calc(100vh - 72px);
  padding: 0 0 var(--ds-space-6, 24px);
  background: transparent;
  color: var(--orep-text-strong);
}

.player-shell {
  width: 100%;
  margin: 0;
}

.player-header {
  display: grid;
  grid-template-columns: 116px minmax(0, 1fr) 142px;
  align-items: center;
  gap: 18px;
  margin-bottom: 18px;
}

.back-btn {
  justify-content: flex-start;
}

.next-btn {
  position: absolute;
  right: 22px;
  top: 22px;
}

.player-title {
  min-width: 0;
}

.player-title span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.player-title h1 {
  margin: 5px 0 0;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.25;
  font-weight: 900;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-progress-pill {
  min-height: 42px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  background: var(--orep-surface-raised);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 14px;
}

.course-progress-pill span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 820;
}

.course-progress-pill strong {
  color: var(--orep-text-strong);
  font-size: 16px;
}

.player-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 22px;
  align-items: start;
}

.player-main {
  display: grid;
  gap: 18px;
}

.video-card,
.lesson-summary,
.side-panel,
.missing-panel {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.video-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 16px;
  background: #0d0d0d;
}

.lesson-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  display: block;
  object-fit: contain;
  background: #000;
  transition: opacity 0.28s ease;
}

.lesson-video.ready {
  opacity: 1;
}

.video-loader {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  padding: 36px;
  text-align: center;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.34), rgba(0, 0, 0, 0.82));
}

.video-loader span {
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 900;
}

.video-loader strong {
  color: white;
  font-size: 24px;
  font-weight: 900;
}

.video-loader p {
  max-width: 440px;
  margin: 0;
  color: rgba(255, 255, 255, 0.62);
  font-size: 15px;
  line-height: 1.65;
}

.video-empty {
  width: min(520px, calc(100% - 48px));
  padding: 32px;
  border: 1px dashed rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: white;
  text-align: center;
}

.video-empty p {
  margin: 10px 0 0;
  color: rgba(255, 255, 255, 0.58);
}

.lesson-summary {
  position: relative;
  padding: 24px 190px 24px 26px;
}

.lesson-summary > span {
  color: var(--orep-orange);
  font-size: 13px;
  font-weight: 900;
}

.lesson-summary h2 {
  margin: 10px 0 12px;
  color: var(--orep-text-strong);
  font-size: 26px;
  line-height: 1.25;
}

.lesson-summary p {
  max-width: 820px;
  margin: 0;
  color: var(--orep-muted);
  font-size: 15px;
  line-height: 1.7;
}

.lesson-summary__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.lesson-summary__meta small {
  min-height: 28px;
  border-radius: 999px;
  background: oklch(0.972 0.006 55);
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 820;
}

.player-side {
  position: sticky;
  top: calc(var(--header-height) + 18px);
  display: grid;
  gap: 14px;
}

.side-panel {
  padding: 18px;
}

.side-panel header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.side-panel h2 {
  margin: 0 0 14px;
  color: var(--orep-text-strong);
  font-size: 20px;
  line-height: 1.25;
}

.side-panel header h2 {
  margin: 0;
}

.side-panel header span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.catalog-list {
  display: grid;
  gap: 10px;
  max-height: 260px;
  overflow: auto;
  padding-right: 2px;
}

.catalog-chapter {
  margin-top: 4px;
  color: var(--orep-text-strong);
  font-size: 13px;
}

.catalog-lesson {
  width: 100%;
  min-height: 44px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: var(--orep-surface-raised);
  color: var(--orep-muted);
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  text-align: left;
  cursor: pointer;
}

.catalog-lesson span {
  color: inherit;
  font-weight: 900;
}

.catalog-lesson b,
.catalog-lesson small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.catalog-lesson b {
  color: var(--orep-text-strong);
  font-size: 14px;
  line-height: 1.2;
}

.catalog-lesson small {
  grid-column: 2;
  color: var(--orep-muted);
  font-size: 12px;
}

.catalog-lesson.active {
  border-color: oklch(0.9 0.04 55);
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
}

.catalog-lesson.completed span {
  color: var(--orep-green);
}

.note-panel textarea {
  width: 100%;
  height: 138px;
  resize: vertical;
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  background: var(--ds-input-bg);
  color: var(--orep-text-strong);
  padding: 14px;
  font: inherit;
  line-height: 1.6;
  outline: none;
}

.note-panel textarea:focus-visible {
  border-color: var(--ds-input-focus-border);
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
  box-shadow: var(--ds-input-focus-ring);
}

.panel-action {
  width: 100%;
}

.note-panel .panel-action {
  margin-top: 12px;
}

.action-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.missing-panel {
  padding: 38px;
}

.missing-panel p {
  margin: 10px 0 0;
  color: var(--orep-muted);
}

@media (max-width: 1180px) {
  .player-header,
  .player-layout {
    grid-template-columns: 1fr;
  }

  .course-progress-pill {
    width: fit-content;
  }

  .player-side {
    position: static;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .catalog-list {
    max-height: 300px;
  }
}

@media (max-width: 820px) {
  .player-page {
    min-height: calc(100vh - 64px);
    padding: 0 0 96px;
  }

  .player-side {
    grid-template-columns: 1fr;
  }

  .video-frame {
    min-height: 240px;
  }

  .lesson-summary {
    padding: 22px;
  }

  .next-btn {
    position: static;
    width: fit-content;
    margin-bottom: 16px;
  }

  .player-title h1 {
    white-space: normal;
    font-size: 24px;
  }
}
</style>
