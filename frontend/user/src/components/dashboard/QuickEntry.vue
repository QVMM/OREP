<template>
  <div class="quick-entry">
    <button
      v-for="entry in entries"
      :key="entry.key"
      class="quick-entry__item"
      @click="$emit('navigate', entry.path)"
    >
      <div class="quick-entry__icon" :class="`quick-entry__icon--${entry.key}`">
        <span>{{ entry.icon }}</span>
      </div>
      <span class="quick-entry__label">{{ entry.label }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  entries: {
    type: Array,
    default: () => [
      { key: 'training', icon: '📖', label: '训练任务', path: '/training/today' },
      { key: 'meeting', icon: '📹', label: '路演训练', path: '/online-meeting' },
      { key: 'ppt', icon: '📊', label: 'PPT生成', path: '/ppt-generator' },
      { key: 'script', icon: '✍️', label: '演讲稿', path: '/script-editor' },
      { key: 'recording', icon: '🎬', label: '路演回放', path: '/my-recordings' },
      { key: 'stats', icon: '📈', label: '数据统计', path: '/statistics' },
      { key: 'profile', icon: '👤', label: '个人中心', path: '/profile' }
    ]
  }
})

defineEmits(['navigate'])
</script>

<style scoped>
.quick-entry {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.quick-entry__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.quick-entry__item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: transparent;
}

.quick-entry__icon {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  font-size: 26px;
  transition: transform var(--transition-fast);
}

.quick-entry__item:hover .quick-entry__icon {
  transform: scale(1.1);
}

.quick-entry__icon--course {
  background: rgba(0, 122, 255, 0.1);
}

.quick-entry__icon--exam {
  background: rgba(255, 149, 0, 0.1);
}

.quick-entry__icon--meeting {
  background: rgba(88, 86, 214, 0.1);
}

.quick-entry__icon--ppt {
  background: rgba(52, 199, 89, 0.1);
}

.quick-entry__icon--script {
  background: rgba(255, 59, 48, 0.1);
}

.quick-entry__icon--recording {
  background: rgba(255, 149, 0, 0.1);
}

.quick-entry__icon--stats {
  background: rgba(0, 122, 255, 0.1);
}

.quick-entry__icon--profile {
  background: rgba(88, 86, 214, 0.1);
}

.quick-entry__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

@media (max-width: 767px) {
  .quick-entry {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
