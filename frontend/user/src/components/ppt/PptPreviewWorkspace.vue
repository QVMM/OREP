<template>
  <div class="ppt-preview-workspace">
    <div class="preview-toolbar">
      <div class="toolbar-left">
        <span class="slide-counter">{{ totalSlides ? currentSlideIndex + 1 : 0 }} / {{ totalSlides }}</span>
        <span class="slide-title">{{ currentSlideTitle }}</span>
      </div>
      <div class="toolbar-center">
        <el-button-group>
          <el-button @click="$emit('prev')" :disabled="currentSlideIndex === 0">
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <el-button @click="$emit('next')" :disabled="currentSlideIndex >= totalSlides - 1">
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </el-button-group>
      </div>
      <div class="toolbar-right">
        <el-button @click="$emit('refresh')" :loading="previewLoading">
          <el-icon><RefreshRight /></el-icon>
          刷新预览
        </el-button>
        <el-button @click="$emit('zoom-out')" :disabled="previewScale <= 0.35">-</el-button>
        <span class="zoom-label">{{ Math.round(previewScale * 100) }}%</span>
        <el-button @click="$emit('zoom-in')" :disabled="previewScale >= 0.8">+</el-button>
        <el-button @click="$emit('regenerate')">
          <el-icon><RefreshRight /></el-icon>
          重新生成
        </el-button>
        <el-button type="primary" :disabled="exportDisabled" @click="$emit('export')">
          <el-icon><Download /></el-icon>
          {{ exportText }}
        </el-button>
      </div>
    </div>

    <div class="preview-workbench">
      <div class="slide-preview-container">
        <div v-if="previewLoading" class="preview-loading">
          <el-icon class="is-loading" size="42"><Loading /></el-icon>
          <div class="preview-loading-title">正在加载 HTML 幻灯片</div>
          <div class="preview-loading-desc">如果页数较多，预览读取可能需要几秒钟</div>
        </div>
        <div v-else-if="currentSlideHtml" class="slide-frame" :style="slideFrameStyle">
          <iframe
            :srcdoc="currentSlideHtml"
            class="slide-iframe"
            sandbox="allow-same-origin allow-scripts"
          ></iframe>
        </div>
        <div v-else class="slide-placeholder">
          <el-icon size="64"><Picture /></el-icon>
          <strong>{{ previewError || '暂无可预览的幻灯片' }}</strong>
          <span>可能是 HTML 页面还没有写入完成，或本地状态没有同步到最新任务。</span>
          <el-button type="primary" plain @click="$emit('refresh')" :loading="previewLoading">
            重新加载预览
          </el-button>
        </div>
      </div>

      <aside class="slide-script-panel">
        <div class="script-panel-top">
          <span>逐页讲稿</span>
          <strong>约 {{ currentSlideEstimatedMinutes }} 分钟</strong>
        </div>
        <h3>{{ currentSlideTitle }}</h3>
        <div class="script-goal">
          <label>本页目标</label>
          <p>{{ currentSlideGoal }}</p>
        </div>
        <div class="script-content">
          <p v-if="currentSlideScript">{{ currentSlideScript }}</p>
          <p v-else class="empty-script">该页还没有讲稿。建议回到大纲编辑页补充讲稿，或后续使用页面级修复生成讲稿。</p>
        </div>
        <div class="script-tips">
          <span>讲解建议</span>
          <p>比赛按 60 分钟口径准备，预览时建议边看页面边校准“这页证明了哪个评分点”。</p>
        </div>
      </aside>
    </div>

    <div v-if="slides.length" class="slide-thumbnails">
      <div
        v-for="(slide, index) in slides"
        :key="index"
        :class="['thumbnail-item', { active: index === currentSlideIndex }]"
        @click="$emit('select-slide', index)"
      >
        <div class="thumbnail-number">{{ index + 1 }}</div>
        <div class="thumbnail-title">{{ slide.title || slide.phase || '幻灯片' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ArrowLeft, ArrowRight, Download, Loading, Picture, RefreshRight } from '@element-plus/icons-vue'

defineEmits(['prev', 'next', 'refresh', 'zoom-in', 'zoom-out', 'regenerate', 'export', 'select-slide'])

defineProps({
  totalSlides: { type: Number, default: 0 },
  currentSlideIndex: { type: Number, default: 0 },
  currentSlideTitle: { type: String, default: '' },
  currentSlideHtml: { type: String, default: '' },
  previewError: { type: String, default: '' },
  previewLoading: { type: Boolean, default: false },
  previewScale: { type: Number, default: 0.5 },
  slideFrameStyle: { type: Object, default: () => ({}) },
  exportDisabled: { type: Boolean, default: false },
  exportText: { type: String, default: '导出 PPT' },
  currentSlideEstimatedMinutes: { type: String, default: '1' },
  currentSlideGoal: { type: String, default: '' },
  currentSlideScript: { type: String, default: '' },
  slides: { type: Array, default: () => [] }
})
</script>

<style scoped>
.preview-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  margin-bottom: 16px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 16px 44px rgba(0, 0, 0, 0.14);
}

.toolbar-left {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.slide-counter {
  color: rgba(148, 163, 184, 0.88);
  font-size: 12px;
  font-weight: 700;
}

.slide-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #fff;
  font-size: 16px;
  font-weight: 800;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.zoom-label {
  min-width: 52px;
  text-align: center;
  color: rgba(226, 232, 240, 0.82);
  font-weight: 700;
}

.preview-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  margin-bottom: 18px;
}

.slide-preview-container {
  position: relative;
  min-height: 720px;
  padding: 20px;
  border-radius: 24px;
  background: radial-gradient(circle at top left, rgba(59, 130, 246, 0.12), transparent 34%), rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.12);
  overflow: hidden;
}

.preview-loading,
.slide-placeholder {
  min-height: 680px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 14px;
  color: rgba(226, 232, 240, 0.74);
}

.preview-loading-title,
.slide-placeholder strong {
  color: #fff;
  font-size: 18px;
  font-weight: 800;
}

.preview-loading-desc,
.slide-placeholder span {
  max-width: 420px;
  text-align: center;
  line-height: 1.7;
}

.slide-frame {
  width: 1920px;
  height: 1080px;
  transform-origin: top left;
}

.slide-iframe {
  width: 1920px;
  height: 1080px;
  border: 0;
  border-radius: 26px;
  background: #0f172a;
}

.slide-script-panel {
  min-height: 720px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.16);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.script-panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: rgba(191, 219, 254, 0.88);
  font-size: 12px;
  font-weight: 800;
}

.slide-script-panel h3 {
  margin: 0;
  color: #fff;
  font-size: 22px;
  line-height: 1.4;
}

.script-goal,
.script-tips {
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.script-goal label,
.script-tips span {
  display: block;
  margin-bottom: 8px;
  color: rgba(191, 219, 254, 0.9);
  font-size: 12px;
  font-weight: 800;
}

.script-goal p,
.script-tips p {
  margin: 0;
  color: rgba(226, 232, 240, 0.78);
  line-height: 1.7;
}

.script-content {
  flex: 1;
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(148, 163, 184, 0.14);
  overflow: auto;
}

.script-content p {
  margin: 0;
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.85;
}

.empty-script {
  color: rgba(226, 232, 240, 0.52) !important;
}

.slide-thumbnails {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.thumbnail-item {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.72);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.thumbnail-item:hover {
  transform: translateY(-2px);
  border-color: rgba(96, 165, 250, 0.28);
}

.thumbnail-item.active {
  border-color: rgba(59, 130, 246, 0.38);
  background: linear-gradient(135deg, rgba(30, 64, 175, 0.28), rgba(15, 23, 42, 0.82));
}

.thumbnail-number {
  margin-bottom: 8px;
  color: rgba(191, 219, 254, 0.92);
  font-size: 12px;
  font-weight: 800;
}

.thumbnail-title {
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.6;
}

@media (max-width: 1180px) {
  .preview-toolbar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .toolbar-right {
    justify-content: flex-start;
  }

  .preview-workbench {
    grid-template-columns: 1fr;
  }

  .slide-script-panel {
    min-height: auto;
  }
}
</style>
