<template>
  <div class="style-preview-section">
    <div class="style-section-header">
      <div>
        <h3>选择视觉风格</h3>
        <p>先看风格样张，再生成全套 HTML，减少“生成完才发现风格不对”的风险。</p>
      </div>
      <el-button size="small" :loading="loading" @click="$emit('reload')">
        <el-icon><RefreshRight /></el-icon>
        重新生成样张
      </el-button>
    </div>

    <div v-if="loading" class="style-preview-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="styles.length" class="style-preview-grid">
      <div
        v-for="style in styles"
        :key="style.style_id"
        :class="['style-preview-card', { active: selectedStyle === style.style_id }]"
        @click="$emit('select', style.style_id)"
      >
        <div class="style-preview-frame">
          <iframe
            :srcdoc="style.preview_html"
            sandbox="allow-same-origin"
            class="style-preview-iframe"
          />
        </div>
        <div class="style-preview-info">
          <div class="style-card-kicker">
            {{ selectedStyle === style.style_id ? '当前生成风格' : '点击切换风格' }}
          </div>
          <div class="style-name">{{ style.style_name }}</div>
          <div class="style-desc">{{ style.description }}</div>
          <div class="style-tags">
            <el-tag
              v-for="keyword in style.keywords"
              :key="keyword"
              size="small"
              effect="plain"
            >
              {{ keyword }}
            </el-tag>
          </div>
        </div>
        <div v-if="selectedStyle === style.style_id" class="style-selected-badge">
          <el-icon><Check /></el-icon>
          已选择
        </div>
      </div>
    </div>

    <div v-else class="style-preview-empty">
      <el-icon><Picture /></el-icon>
      <span>还没有样张，点击右上角重新生成后选择一个视觉方向。</span>
    </div>
  </div>
</template>

<script setup>
import { Check, Picture, RefreshRight } from '@element-plus/icons-vue'

defineEmits(['reload', 'select'])

defineProps({
  loading: { type: Boolean, default: false },
  styles: { type: Array, default: () => [] },
  selectedStyle: { type: String, default: '' }
})
</script>

<style scoped>
.style-preview-section {
  margin-bottom: 24px;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background: rgba(15, 23, 42, 0.66);
}

.style-section-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.style-section-header h3 {
  margin: 0 0 8px;
  color: #fff;
  font-size: 18px;
}

.style-section-header p {
  margin: 0;
  color: rgba(226, 232, 240, 0.7);
  line-height: 1.7;
}

.style-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.style-preview-card {
  position: relative;
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.86);
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.style-preview-card:hover {
  transform: translateY(-3px);
  border-color: rgba(96, 165, 250, 0.3);
}

.style-preview-card.active {
  border-color: #3b82f6;
  box-shadow: 0 18px 48px rgba(59, 130, 246, 0.18);
}

.style-preview-frame {
  height: 230px;
  overflow: hidden;
  background: #0f172a;
}

.style-preview-iframe {
  width: 1280px;
  height: 720px;
  border: 0;
  transform: scale(0.318);
  transform-origin: top left;
  pointer-events: none;
}

.style-preview-info {
  padding: 18px;
}

.style-card-kicker {
  color: #93c5fd;
  font-size: 12px;
  font-weight: 800;
}

.style-name {
  margin-top: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: 800;
}

.style-desc {
  margin-top: 10px;
  color: rgba(226, 232, 240, 0.74);
  line-height: 1.7;
}

.style-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.style-selected-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.92);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.style-preview-empty {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(226, 232, 240, 0.66);
}

@media (max-width: 1180px) {
  .style-preview-grid {
    grid-template-columns: 1fr;
  }

  .style-preview-frame {
    height: 260px;
  }

  .style-preview-iframe {
    transform: scale(0.24);
  }
}

@media (max-width: 760px) {
  .style-section-header {
    flex-direction: column;
  }
}
</style>
