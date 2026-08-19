<template>
  <section class="visual-frame-strip" aria-label="关键帧佐证">
    <header class="strip-head">
      <div>
        <span>{{ eyebrow }}</span>
        <strong>{{ title }}</strong>
      </div>
      <div class="strip-status">
        <div class="status-line">
          <em>{{ countText }}</em>
          <b>{{ activeFrame?.time || fallbackTime }} · {{ activeFrame?.stageName || fallbackStage }}</b>
        </div>
        <div class="strip-nav" aria-label="关键帧翻页">
          <button type="button" aria-label="向前浏览关键帧" @click="scrollFrames(-1)">‹</button>
          <button type="button" aria-label="向后浏览关键帧" @click="scrollFrames(1)">›</button>
        </div>
      </div>
    </header>

    <div class="strip-shell">
      <div ref="trackRef" class="frame-track">
        <button
          v-for="frame in frames"
          :key="frame.id"
          type="button"
          :class="['frame-card', { active: frame.id === activeFrame?.id }]"
          @click="$emit('select', frame)"
        >
          <figure>
            <img v-if="frame.image" :src="frame.image" loading="lazy" alt="" />
            <span v-else>{{ frame.stageName }}</span>
            <figcaption>
              <b>{{ frame.time }}</b>
              <small>{{ frame.stageName }}</small>
            </figcaption>
          </figure>
          <p>{{ frame.summary }}</p>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  frames: { type: Array, default: () => [] },
  activeFrame: { type: Object, default: null },
  countText: { type: String, default: '暂无关键帧' },
  eyebrow: { type: String, default: '逐帧审阅' },
  title: { type: String, default: '全部关键帧佐证' },
  fallbackTime: { type: String, default: '00:00' },
  fallbackStage: { type: String, default: '关键帧' },
  fallbackSummary: { type: String, default: '当前片段暂无画面说明。' }
})

defineEmits(['select'])

const trackRef = ref(null)

watch(() => props.activeFrame?.id, async (id) => {
  if (!id) return
  await nextTick()
  scrollActiveFrameIntoView(id)
})

function scrollFrames(direction) {
  const track = trackRef.value
  if (!track) return
  const card = track.querySelector('.frame-card')
  const distance = card ? card.offsetWidth + 20 : 300
  track.scrollBy({ left: direction * distance * 2, behavior: 'smooth' })
}

function scrollActiveFrameIntoView(id) {
  const track = trackRef.value
  if (!track) return
  const cards = Array.from(track.querySelectorAll('.frame-card'))
  const index = props.frames.findIndex(frame => frame.id === id)
  const card = cards[index]
  if (!card) return
  const cardLeft = card.offsetLeft
  const cardRight = cardLeft + card.offsetWidth
  const visibleLeft = track.scrollLeft
  const visibleRight = visibleLeft + track.clientWidth
  if (cardLeft >= visibleLeft && cardRight <= visibleRight) return
  track.scrollTo({ left: Math.max(0, cardLeft - 12), behavior: 'smooth' })
}
</script>

<style scoped>
.visual-frame-strip {
  margin-top: 10px;
  padding: 12px;
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  background: #fffefe;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
  color: #24313f;
}

.strip-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.strip-head span {
  display: block;
  color: #8a95a6;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.strip-head strong {
  display: block;
  margin-top: 4px;
  color: #172033;
  font-size: 16px;
  font-weight: 850;
  line-height: 1.25;
}

.strip-status {
  display: grid;
  justify-items: end;
  gap: 7px;
  flex: 0 0 auto;
}

.status-line,
.strip-nav {
  display: inline-flex;
  align-items: center;
}

.status-line {
  gap: 6px;
}

.strip-status em,
.strip-status b,
.strip-nav button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-style: normal;
  line-height: 1;
}

.strip-status em {
  min-height: 25px;
  padding: 0 10px;
  background: #e6f5f2;
  color: #0b706d;
  font-size: 12px;
  font-weight: 900;
}

.strip-status b {
  min-height: 24px;
  padding: 0 9px;
  background: #f1f6f5;
  color: #647086;
  font-size: 12px;
  font-weight: 800;
}

.strip-nav {
  overflow: hidden;
  border: 1px solid #dbe3eb;
  border-radius: 7px;
  background: #fbfdff;
}

.strip-nav button {
  width: 28px;
  height: 26px;
  border: 0;
  border-right: 1px solid #e6edf5;
  background: transparent;
  color: #647086;
  font-size: 19px;
  font-weight: 700;
  cursor: pointer;
  transition: background .18s ease, color .18s ease;
}

.strip-nav button:last-child {
  border-right: 0;
}

.strip-nav button:hover {
  background: #f1f6f5;
  color: #0b8580;
}

.strip-shell {
  position: relative;
  overflow: hidden;
}

.frame-track {
  display: grid;
  grid-auto-columns: calc((100% - 10px) / 2);
  grid-auto-flow: column;
  gap: 10px;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 0 3px;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
}

.frame-track::-webkit-scrollbar {
  display: none;
}

.frame-card {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 7px;
  min-width: 0;
  height: 154px;
  overflow: hidden;
  padding: 7px;
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  background: #ffffff;
  color: #35455a;
  text-align: left;
  cursor: pointer;
  scroll-snap-align: start;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease, background .18s ease;
}

.frame-card:hover {
  border-color: #9bcac3;
  transform: translateY(-1px);
}

.frame-card.active {
  border-color: #159083;
  background: #fbfffe;
  box-shadow: 0 0 0 2px rgba(21, 144, 131, .12);
}

.frame-card figure {
  position: relative;
  min-width: 0;
  height: 84px;
  margin: 0;
  overflow: hidden;
  border-radius: 6px;
  background: #edf4f2;
}

.frame-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.frame-card figure > span {
  display: grid;
  place-items: center;
  height: 100%;
  padding: 8px;
  color: #7a8798;
  font-size: 12px;
}

.frame-card figcaption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
  padding: 18px 8px 6px;
  background: linear-gradient(180deg, rgba(20, 30, 38, 0), rgba(20, 30, 38, .78));
}

.frame-card figcaption b {
  color: #fbfefd;
  font-size: 13px;
  font-weight: 900;
}

.frame-card figcaption small {
  min-width: 0;
  overflow: hidden;
  color: rgba(251, 254, 253, .88);
  font-size: 12px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.frame-card > p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  padding: 0 2px;
  color: #647086;
  font-size: 12px;
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@media (max-width: 760px) {
  .visual-frame-strip {
    padding: 12px;
  }

  .strip-head {
    display: grid;
  }

  .strip-status {
    justify-items: start;
  }

  .frame-track {
    grid-auto-columns: 82%;
  }

  .status-line {
    flex-wrap: wrap;
  }
}
</style>
