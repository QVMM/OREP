<template>
  <BaseCard class="recent-activity">
    <template #header>
      <div class="recent-activity__header">
        <h3 class="recent-activity__title">最近活动</h3>
        <BaseButton type="text" size="small" @click="$emit('viewAll')">
          查看全部
        </BaseButton>
      </div>
    </template>

    <div v-if="activities.length" class="recent-activity__list">
      <div
        v-for="(item, index) in activities.slice(0, 5)"
        :key="index"
        class="recent-activity__item"
      >
        <div class="recent-activity__icon" :class="`recent-activity__icon--${item.type || 'default'}`">
          <span>{{ getIcon(item.type) }}</span>
        </div>
        <div class="recent-activity__info">
          <p class="recent-activity__desc">{{ item.description }}</p>
          <span class="recent-activity__time">{{ item.time }}</span>
        </div>
      </div>
    </div>

    <div v-else class="recent-activity__empty">
      <p>暂无最近活动</p>
    </div>
  </BaseCard>
</template>

<script setup>
import { BaseCard, BaseButton } from '../base'

defineProps({
  activities: {
    type: Array,
    default: () => []
  }
})

defineEmits(['viewAll'])

const icons = {
  course: '📖',
  exam: '📝',
  meeting: '📹',
  ppt: '📊',
  task: '✅',
  system: '🔔',
  default: '📌'
}

function getIcon(type) {
  return icons[type] || icons.default
}
</script>

<style scoped>
.recent-activity__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.recent-activity__title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.recent-activity__list {
  display: flex;
  flex-direction: column;
}

.recent-activity__item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-light);
}

.recent-activity__item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.recent-activity__item:first-child {
  padding-top: 0;
}

.recent-activity__icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  font-size: 18px;
  background: rgba(0, 122, 255, 0.08);
}

.recent-activity__icon--course {
  background: rgba(0, 122, 255, 0.08);
}

.recent-activity__icon--exam {
  background: rgba(255, 149, 0, 0.08);
}

.recent-activity__icon--meeting {
  background: rgba(88, 86, 214, 0.08);
}

.recent-activity__icon--ppt {
  background: rgba(52, 199, 89, 0.08);
}

.recent-activity__icon--task {
  background: rgba(52, 199, 89, 0.08);
}

.recent-activity__icon--system {
  background: rgba(0, 122, 255, 0.08);
}

.recent-activity__info {
  flex: 1;
  min-width: 0;
}

.recent-activity__desc {
  margin: 0 0 4px;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  line-height: var(--line-height-normal);
}

.recent-activity__time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.recent-activity__empty {
  padding: 32px 0;
  text-align: center;
}

.recent-activity__empty p {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}
</style>
