<template>
  <div class="deduction-card-container">
    <!-- Card Header -->
    <div class="card-header">
      <!-- Col 1: Number -->
      <div class="header-col-num">
        <span class="num-text">0{{ idx + 1 }}</span>
      </div>

      <!-- Col 2: Title and Subtitle -->
      <div class="header-col-title">
        <div class="title-row">
          <h4 class="title-text">{{ issue.title }}</h4>
          <span v-if="issue.level === 'P0'" class="urgent-badge">高风险</span>
        </div>
        <p class="subtitle-text">{{ issue.detail }}</p>
      </div>

      <!-- Col 3: Dimension tags -->
      <div class="header-col-dims">
        <span class="dims-label">扣分维度</span>
        <div class="dims-tags">
          <span v-for="tag in dimTags" :key="tag" class="dim-pill">{{ tag }}</span>
        </div>
      </div>

      <!-- Col 4: Score influence -->
      <div class="header-col-score">
        <span class="score-label">扣分影响</span>
        <span class="score-val">{{ issue.score }}</span>
      </div>

      <!-- Col 5: Action Button -->
      <div class="header-col-action">
        <button type="button" class="btn-orange-pill" @click="$emit('view-plan', issue)">
          查看整改方案
        </button>
      </div>
    </div>

    <!-- Card Body -->
    <div class="card-body">
      <!-- Thumbnail -->
      <div v-if="hasFrame" class="body-thumbnail">
        <img :src="frameImage" alt="关键帧" />
      </div>

      <!-- Detail text info -->
      <div class="body-right-content">
        <!-- Transcript Excerpt -->
        <div class="transcript-row">
          <span class="clock-icon">🕒</span>
          <span class="transcript-time">{{ frameTime }}</span>
          <span class="transcript-text">“{{ transcript }}”</span>
        </div>

        <!-- Deduction Reason -->
        <div class="reason-row">
          <span class="reason-bar"></span>
          <span class="reason-label">扣分原因</span>
          <span class="reason-text">{{ issue.reason || issue.detail }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  idx: { type: Number, required: true },
  issue: { type: Object, required: true },
  dimTags: { type: Array, default: () => [] },
  hasFrame: { type: Boolean, default: false },
  frameTime: { type: String, default: '01:30' },
  frameImage: { type: String, default: '' },
  transcript: { type: String, default: '' }
})

defineEmits(['view-plan'])
</script>

<style scoped>
.deduction-card-container {
  border: 1px solid #eef1f6;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  padding: 22px 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  margin-bottom: 18px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.deduction-card-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(253, 102, 66, 0.05);
}

/* Card Header Layout */
.card-header {
  display: flex;
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid #f2f5fa;
  margin-bottom: 18px;
}

.header-col-num {
  padding-right: 20px;
  flex-shrink: 0;
}

.num-text {
  font-size: 38px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
  font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  letter-spacing: -1px;
}

.header-col-title {
  flex: 1;
  padding: 0 22px;
  border-left: 1.2px solid #eef1f6;
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.title-text {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  margin: 0;
}

.urgent-badge {
  font-size: 11px;
  font-weight: 800;
  background: #fef2f2;
  color: #dc2626;
  padding: 2px 8px;
  border-radius: 99px;
}

.subtitle-text {
  font-size: 13px;
  color: #8a8888;
  margin: 0;
  line-height: 1.4;
}

.header-col-dims {
  padding: 0 22px;
  border-left: 1.2px solid #eef1f6;
  width: 230px;
  flex-shrink: 0;
}

.dims-label {
  font-size: 11px;
  color: #8a8888;
  margin-bottom: 6px;
  display: block;
  font-weight: 600;
}

.dims-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dim-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 99px;
  background: #fff5f2;
  color: #fd6642;
  font-size: 11px;
  font-weight: 700;
}

.header-col-score {
  padding: 0 22px;
  border-left: 1.2px solid #eef1f6;
  text-align: right;
  width: 100px;
  flex-shrink: 0;
}

.score-label {
  font-size: 11px;
  color: #8a8888;
  margin-bottom: 4px;
  display: block;
  font-weight: 600;
}

.score-val {
  font-size: 26px;
  font-weight: 900;
  color: #dc2626;
  line-height: 1.1;
  font-family: 'Outfit', 'Inter', sans-serif;
}

.header-col-action {
  padding-left: 22px;
  border-left: 1.2px solid #eef1f6;
  flex-shrink: 0;
}

.btn-orange-pill {
  height: 34px;
  padding: 0 18px;
  border: none;
  border-radius: 99px;
  background: #fd6642;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.18s ease, transform 0.18s ease;
  box-shadow: 0 4px 12px rgba(253, 102, 66, 0.2);
}

.btn-orange-pill:hover {
  background: #f15a24;
  transform: translateY(-1px);
}

/* Card Body Layout */
.card-body {
  display: flex;
  gap: 20px;
}

.body-thumbnail {
  width: 160px;
  height: 96px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #eef1f6;
  flex-shrink: 0;
  background: #f9f9fb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.body-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.body-right-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
}

.transcript-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #555555;
  line-height: 1.6;
}

.clock-icon {
  color: #8a8888;
}

.transcript-time {
  font-weight: 700;
  color: #8a8888;
  white-space: nowrap;
  margin-right: 4px;
}

.transcript-text {
  color: #555555;
  font-style: italic;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.reason-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
}

.reason-bar {
  display: inline-block;
  width: 3px;
  height: 14px;
  background: #111827;
  align-self: center;
}

.reason-label {
  font-weight: 800;
  color: #111827;
  white-space: nowrap;
  margin-right: 4px;
}

.reason-text {
  color: #555555;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Responsive */
@media (max-width: 960px) {
  .card-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .header-col-title,
  .header-col-dims,
  .header-col-score,
  .header-col-action {
    border-left: none;
    padding: 0;
    width: auto;
  }

  .header-col-score {
    text-align: left;
  }

  .card-body {
    flex-direction: column;
  }

  .body-thumbnail {
    width: 100%;
    height: 140px;
  }
}
</style>
