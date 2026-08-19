<template>
  <BaseCard hoverable class="task-card">
    <div class="task-card__header">
      <div class="task-card__icon" :class="`task-card__icon--${type}`">
        <span>{{ typeIcon }}</span>
      </div>
      <span class="task-card__status" :class="`task-card__status--${status}`">
        {{ statusLabel }}
      </span>
    </div>
    <h3 class="task-card__title">{{ title }}</h3>
    <p v-if="description" class="task-card__desc">{{ description }}</p>
    <div class="task-card__footer">
      <span class="task-card__deadline">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
          <path d="M7 4V7.5L9 9" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
        {{ deadline }}
      </span>
      <BaseButton
        v-if="actionText"
        type="text"
        size="small"
        @click="$emit('action')"
      >
        {{ actionText }}
      </BaseButton>
    </div>
  </BaseCard>
</template>

<script setup>
import { computed } from 'vue'
import { BaseCard, BaseButton } from '../base'

const props = defineProps({
  type: {
    type: String,
    default: 'course',
    validator: (v) => ['course', 'exam', 'meeting', 'ppt'].includes(v)
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  deadline: {
    type: String,
    default: ''
  },
  status: {
    type: String,
    default: 'pending',
    validator: (v) => ['pending', 'in-progress', 'completed', 'overdue'].includes(v)
  },
  actionText: {
    type: String,
    default: '去完成'
  }
})

defineEmits(['action'])

const typeIcons = {
  course: '📖',
  exam: '📝',
  meeting: '📹',
  ppt: '📊'
}

const statusLabels = {
  pending: '待完成',
  'in-progress': '进行中',
  completed: '已完成',
  overdue: '已截止'
}

const typeIcon = computed(() => typeIcons[props.type] || '📋')
const statusLabel = computed(() => statusLabels[props.status] || props.status)
</script>

<style scoped>
.task-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.task-card__icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  font-size: 20px;
}

.task-card__icon--course {
  background: rgba(0, 122, 255, 0.1);
}

.task-card__icon--exam {
  background: rgba(255, 149, 0, 0.1);
}

.task-card__icon--meeting {
  background: rgba(88, 86, 214, 0.1);
}

.task-card__icon--ppt {
  background: rgba(52, 199, 89, 0.1);
}

.task-card__status {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.task-card__status--pending {
  background: rgba(0, 122, 255, 0.08);
  color: var(--color-primary);
}

.task-card__status--in-progress {
  background: rgba(255, 149, 0, 0.08);
  color: var(--color-warning);
}

.task-card__status--completed {
  background: rgba(52, 199, 89, 0.08);
  color: var(--color-success);
}

.task-card__status--overdue {
  background: rgba(255, 59, 48, 0.08);
  color: var(--color-error);
}

.task-card__title {
  margin: 0 0 8px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: var(--line-height-tight);
}

.task-card__desc {
  margin: 0 0 16px;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: var(--line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.task-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.task-card__deadline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
</style>
