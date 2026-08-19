<template>
  <div class="slide-list">
    <h3>幻灯片列表</h3>
    <div class="slides">
      <div
        v-for="(slide, index) in slides"
        :key="index"
        class="slide-item"
        :class="{ active: index === currentIndex }"
        @click="$emit('select', index)"
      >
        <span class="slide-number">{{ index + 1 }}</span>
        <span class="slide-title">{{ slide.title || '无标题' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  currentIndex: {
    type: Number,
    default: 0
  }
})

defineEmits(['select'])
</script>

<style scoped>
.slide-list {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
}

.slides {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.slide-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 1px solid #eee;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.slide-item:hover {
  background: #f5f5f5;
}

.slide-item.active {
  background: #42b983;
  color: #fff;
}

.slide-number {
  font-weight: bold;
  min-width: 24px;
}

.slide-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
