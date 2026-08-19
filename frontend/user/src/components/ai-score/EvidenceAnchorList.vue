<template>
  <section class="anchor-panel" aria-label="证据锚点">
    <header>
      <div>
        <span class="eyebrow">EVIDENCE ANCHORS</span>
        <h3>证据锚点</h3>
      </div>
      <small>{{ anchors.length }} 条</small>
    </header>
    <div v-if="anchors.length" class="anchor-layout">
      <div class="anchor-list">
        <button
          v-for="anchor in anchors"
          :key="anchor.id"
          type="button"
          :class="{ active: selected?.id === anchor.id }"
          @click="selected = anchor"
        >
          <b>{{ anchor.anchorTitle || typeLabel(anchor.anchorType) }}</b>
          <span>{{ timeLabel(anchor) }}</span>
          <p>{{ anchor.evidenceText || '暂无证据文本' }}</p>
        </button>
      </div>
      <article class="anchor-detail">
        <span>{{ typeLabel(selected?.anchorType) }}</span>
        <h4>{{ selected?.anchorTitle || '证据详情' }}</h4>
        <p>{{ selected?.evidenceText || '选择左侧证据锚点查看详情。' }}</p>
        <dl>
          <div>
            <dt>来源</dt>
            <dd>{{ selected?.sourceRef || '-' }}</dd>
          </div>
          <div>
            <dt>时间范围</dt>
            <dd>{{ timeLabel(selected) }}</dd>
          </div>
          <div>
            <dt>置信度</dt>
            <dd>{{ confidenceLabel(selected) }}</dd>
          </div>
        </dl>
      </article>
    </div>
    <div v-else class="empty">暂无结构化证据锚点。</div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  anchors: { type: Array, default: () => [] }
})

const selected = ref(null)

watch(
  () => props.anchors,
  (anchors) => {
    selected.value = anchors?.[0] || null
  },
  { immediate: true }
)

const typeMap = {
  transcript_segment: '转写片段',
  transcript: '转写证据',
  frame_ocr: '关键帧/OCR',
  frame: '关键帧',
  screen_ocr: '屏幕识别'
}

function typeLabel(type) {
  return typeMap[type] || type || '证据'
}

function timeLabel(anchor) {
  if (!anchor) return '-'
  if (anchor.sourceRef) return anchor.sourceRef
  const start = Number(anchor.startMs ?? 0)
  const end = Number(anchor.endMs ?? 0)
  if (!start && !end) return '-'
  return `${formatMs(start)}-${formatMs(end)}`
}

function formatMs(ms) {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0')
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}

function confidenceLabel(anchor) {
  if (!anchor || anchor.confidence == null) return '-'
  return `${Math.round(Number(anchor.confidence) * 100)}%`
}
</script>

<style scoped>
.anchor-panel {
  padding: 18px;
  border: 1px solid rgba(126, 231, 176, 0.16);
  border-radius: 8px;
  background: rgba(9, 17, 14, 0.94);
}

header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.eyebrow {
  color: #7ee7b0;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

h3,
h4,
b,
dd {
  color: #f5fff8;
}

h3,
h4,
p {
  margin: 0;
}

header small,
span,
dt,
p,
.empty {
  color: rgba(232, 245, 237, 0.66);
}

.anchor-layout {
  display: grid;
  grid-template-columns: minmax(240px, 0.85fr) minmax(0, 1.15fr);
  gap: 14px;
}

.anchor-list {
  display: grid;
  gap: 8px;
  max-height: 380px;
  overflow: auto;
}

button {
  width: 100%;
  text-align: left;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
  cursor: pointer;
}

button.active,
button:focus-visible {
  border-color: rgba(126, 231, 176, 0.65);
  outline: none;
}

button p {
  margin-top: 6px;
  line-height: 1.5;
}

.anchor-detail {
  min-height: 240px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.055);
}

.anchor-detail h4 {
  margin: 8px 0 12px;
  font-size: 20px;
}

.anchor-detail p {
  line-height: 1.8;
}

dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 16px 0 0;
}

dl div {
  padding: 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.18);
}

dd {
  margin: 4px 0 0;
  word-break: break-word;
}

@media (max-width: 900px) {
  .anchor-layout,
  dl {
    grid-template-columns: 1fr;
  }
}
</style>
