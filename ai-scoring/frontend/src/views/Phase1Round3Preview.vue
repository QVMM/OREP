<template>
  <div class="phase1-round3">
    <n-card title="Step 3: HTML 预览" class="preview-card">
      <template #header-extra>
        <n-tag type="success">Round 3</n-tag>
      </template>

      <!-- 步骤指示器 -->
      <n-steps :current="currentStep" class="steps">
        <n-step title="填写问卷" description="填写项目信息" />
        <n-step title="确认大纲" description="确认PPT大纲" />
        <n-step title="生成内容" description="AI生成内容" />
        <n-step title="预览" description="HTML预览" />
      </n-steps>

      <n-divider />

      <!-- 无数据提示 -->
      <div v-if="!hasGeneratedTask" class="empty-state">
        <n-empty description="请先完成内容生成">
          <template #extra>
            <n-button type="primary" @click="goToRound2">
              去生成内容
            </n-button>
          </template>
        </n-empty>
      </div>

      <!-- 预览区域 -->
      <div v-else class="preview-section">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-section">
          <n-spin size="large" />
          <p class="loading-text">正在生成预览，请稍候...</p>
          <n-progress
            type="line"
            :percentage="progressPercentage"
            :show-indicator="true"
            status="success"
          />
        </div>

        <!-- 预览内容 -->
        <div v-else-if="previewPages.length" class="preview-content">
          <!-- 预览控制栏 -->
          <div class="preview-toolbar">
            <n-space>
              <n-button-group>
                <n-button @click="handlePrevSlide" :disabled="currentSlideIndex <= 0">
                  <template #icon>
                    <n-icon><ChevronBackOutline /></n-icon>
                  </template>
                  上一页
                </n-button>
                <n-button disabled>
                  {{ currentSlideIndex + 1 }} / {{ totalSlides }}
                </n-button>
                <n-button @click="handleNextSlide" :disabled="currentSlideIndex >= totalSlides - 1">
                  下一页
                  <template #icon>
                    <n-icon><ChevronForwardOutline /></n-icon>
                  </template>
                </n-button>
              </n-button-group>

              <n-button-group>
                <n-button @click="handleZoomOut" :disabled="scale <= 0.5">
                  <template #icon>
                    <n-icon><RemoveOutline /></n-icon>
                  </template>
                </n-button>
                <n-button disabled>{{ Math.round(scale * 100) }}%</n-button>
                <n-button @click="handleZoomIn" :disabled="scale >= 2">
                  <template #icon>
                    <n-icon><AddOutline /></n-icon>
                  </template>
                </n-button>
              </n-button-group>
            </n-space>

            <n-space>
              <n-button @click="handleFullscreen">
                <template #icon>
                  <n-icon><ExpandOutline /></n-icon>
                </template>
                全屏
              </n-button>
              <n-button @click="handleDownload">
                <template #icon>
                  <n-icon><DownloadOutline /></n-icon>
                </template>
                下载
              </n-button>
              <n-button type="primary" @click="handleRegenerate">
                重新生成
              </n-button>
            </n-space>
          </div>

          <!-- 幻灯片预览区域 -->
          <div class="slides-container" ref="slidesContainerRef">
            <div
              class="slide-wrapper"
              :style="{
                transform: `scale(${scale})`,
                width: `${slideWidth}px`,
                height: `${slideHeight}px`
              }"
            >
              <iframe
                class="slide-frame"
                :srcdoc="currentSlideHtml"
                title="PPT HTML Preview"
                sandbox="allow-same-origin allow-scripts"
              />
            </div>
          </div>

          <!-- 缩略图列表 -->
          <div class="thumbnails-section">
            <div class="thumbnails-header">
              <span>幻灯片缩略图</span>
            </div>
            <div class="thumbnails-list">
              <div
                v-for="(slide, index) in previewPages"
                :key="index"
                :class="['thumbnail', { active: index === currentSlideIndex }]"
                @click="goToSlide(index)"
              >
                <div class="thumbnail-number">{{ index + 1 }}</div>
                <div class="thumbnail-title">{{ slide.title || `第 ${index + 1} 页` }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 初始状态 -->
        <div v-else class="init-section">
          <n-result status="info" title="准备生成预览" description="点击开始生成HTML预览">
            <template #footer>
              <n-space justify="center">
                <n-button @click="goToRound2">返回内容</n-button>
                <n-button type="primary" @click="handleStartPreview" :loading="loading">
                  开始生成预览
                </n-button>
              </n-space>
            </template>
          </n-result>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div v-if="previewPages.length && !loading" class="actions">
        <n-button @click="goToRound2">
          返回内容
        </n-button>
        <n-button @click="handleStartOver">
          重新开始
        </n-button>
        <n-button type="primary" @click="handleComplete">
          完成生成
        </n-button>
      </div>

      <!-- 全屏预览弹窗 -->
      <n-modal
        v-model:show="fullscreenVisible"
        preset="card"
        title="全屏预览"
        style="width: 100%; height: 100%; margin: 0"
        :bordered="false"
        :segmented="false"
      >
        <div class="fullscreen-preview">
          <iframe
            class="slide-fullscreen"
            :srcdoc="currentSlideHtml"
            title="PPT Fullscreen Preview"
            sandbox="allow-same-origin allow-scripts"
          />
          <div class="fullscreen-controls">
            <n-button-group>
              <n-button @click="handlePrevSlide">
                <template #icon>
                  <n-icon><ChevronBackOutline /></n-icon>
                </template>
              </n-button>
              <n-button disabled>{{ currentSlideIndex + 1 }} / {{ totalSlides }}</n-button>
              <n-button @click="handleNextSlide">
                <template #icon>
                  <n-icon><ChevronForwardOutline /></n-icon>
                </template>
              </n-button>
            </n-button-group>
            <n-button @click="fullscreenVisible = false">
              退出全屏
            </n-button>
          </div>
        </div>
      </n-modal>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePPTStore } from '@/stores/pptStore'
import {
  AddOutline,
  ChevronBackOutline,
  ChevronForwardOutline,
  DownloadOutline,
  ExpandOutline,
  RemoveOutline
} from '@vicons/ionicons5'

const router = useRouter()
const pptStore = usePPTStore()

// 状态
const currentStep = ref(3)
const loading = ref(false)
const currentSlideIndex = ref(0)
const scale = ref(1)
const slideWidth = ref(960)
const slideHeight = ref(540)
const progressPercentage = ref(0)
const fullscreenVisible = ref(false)
const slidesContainerRef = ref(null)

// 是否已有后端任务
const hasGeneratedTask = computed(() => !!pptStore.taskId)

// 获取预览数据
const previewData = computed(() => pptStore.preview)

// 获取后端真实 HTML 页面
const previewPages = computed(() => {
  const pages = previewData.value?.pages || []
  if (pages.length) return pages

  const htmlPages = previewData.value?.html_pages || []
  return htmlPages.map((html, index) => ({
    page_index: index + 1,
    title: `第 ${index + 1} 页`,
    html
  }))
})

// 总幻灯片数
const totalSlides = computed(() => previewPages.value.length)

// 当前幻灯片HTML
const currentSlideHtml = computed(() => {
  if (!previewPages.value.length) return ''
  return previewPages.value[currentSlideIndex.value]?.html || ''
})

// 上一页
function handlePrevSlide() {
  if (currentSlideIndex.value > 0) {
    currentSlideIndex.value--
  }
}

// 下一页
function handleNextSlide() {
  if (currentSlideIndex.value < totalSlides.value - 1) {
    currentSlideIndex.value++
  }
}

// 跳转到指定幻灯片
function goToSlide(index) {
  currentSlideIndex.value = index
}

// 放大
function handleZoomIn() {
  if (scale.value < 2) {
    scale.value = Math.min(2, scale.value + 0.1)
  }
}

// 缩小
function handleZoomOut() {
  if (scale.value > 0.5) {
    scale.value = Math.max(0.5, scale.value - 0.1)
  }
}

// 全屏预览
function handleFullscreen() {
  fullscreenVisible.value = true
}

// 下载
function handleDownload() {
  if (pptStore.downloadUrl) {
    window.open(pptStore.downloadUrl, '_blank')
  }
}

// 重新生成
function handleRegenerate() {
  handleStartPreview()
}

// 开始生成预览
async function handleStartPreview() {
  loading.value = true
  progressPercentage.value = 0

  const progressTimer = setInterval(() => {
    if (progressPercentage.value < 90) {
      progressPercentage.value += Math.random() * 10
    }
  }, 500)

  try {
    await pptStore.generatePreview()
    clearInterval(progressTimer)
    progressPercentage.value = 100
  } catch (err) {
    clearInterval(progressTimer)
    console.error('生成预览失败:', err)
  } finally {
    loading.value = false
  }
}

// 跳转到 Round 2
function goToRound2() {
  router.push('/phase1/round2')
}

// 重新开始
function handleStartOver() {
  pptStore.resetState()
  router.push('/generate')
}

// 完成生成
function handleComplete() {
  // 显示完成提示
  const { createMessage } = window
  if (createMessage) {
    createMessage.success('PPT 生成完成！')
  }

  // 可以跳转到其他页面或展示最终结果
  router.push('/')
}
</script>

<style scoped>
.phase1-round3 {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.preview-card {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.steps {
  margin-bottom: 20px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
}

.loading-text {
  margin: 16px 0;
  color: #666;
}

.init-section {
  padding: 40px 0;
}

.preview-section {
  margin-top: 20px;
}

.preview-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9f9f9;
  border-radius: 8px;
  margin-bottom: 20px;
}

.slides-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 600px;
  padding: 40px;
  background: #e8e8e8;
  border-radius: 8px;
  overflow: auto;
}

.slide-wrapper {
  transition: transform 0.2s ease;
  transform-origin: center center;
}

.slide,
.slide-frame {
  width: 100%;
  height: 100%;
  background: white;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border-radius: 4px;
  overflow: hidden;
  border: 0;
}

.thumbnails-section {
  margin-top: 20px;
}

.thumbnails-header {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.thumbnails-list {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.thumbnail {
  flex-shrink: 0;
  width: 120px;
  padding: 8px;
  background: #f9f9f9;
  border: 2px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.thumbnail:hover {
  background: #f0f0f0;
}

.thumbnail.active {
  border-color: #18a058;
  background: #e8f5e9;
}

.thumbnail-number {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.thumbnail-title {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.fullscreen-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 100px);
  background: #333;
}

.slide-fullscreen {
  flex: 1;
  width: 100%;
  max-width: 1200px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  border: 0;
}

.fullscreen-controls {
  display: flex;
  gap: 16px;
  padding: 16px;
  justify-content: center;
}
</style>

<style>
/* 预览幻灯片内容的全局样式 */
.preview-slide-content {
  padding: 40px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-slide-header h1 {
  margin: 0 0 30px 0;
  font-size: 32px;
  color: #333;
  text-align: center;
}

.preview-slide-body {
  flex: 1;
  font-size: 18px;
  line-height: 1.8;
}

.preview-slide-body p {
  margin: 0 0 20px 0;
}

.preview-slide-body ul {
  margin: 0;
  padding-left: 24px;
}

.preview-slide-body li {
  margin-bottom: 8px;
}

.preview-slide-notes {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #eee;
  color: #999;
}
</style>
