<template>
  <button
    class="teacher-collaboration-entry"
    type="button"
    :aria-expanded="store.isOpen"
    :aria-label="store.actionCount ? `协作，${store.actionCount} 项待处理` : '协作'"
    @click="open"
  >
    <CollaborationBrandMark />
    <span class="teacher-collaboration-entry__text">
      <strong>协作</strong>
      <small>{{ store.actionCount ? `${store.actionCount} 项待处理` : '任务与审核' }}</small>
    </span>
    <em v-if="store.actionCount">{{ store.actionCount > 99 ? '99+' : store.actionCount }}</em>
  </button>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useTeacherCollaborationStore } from '../../stores/collaboration'
import CollaborationBrandMark from './CollaborationBrandMark.vue'

const store = useTeacherCollaborationStore()
const router = useRouter()

function open() {
  if (store.isFeatureEnabled) {
    store.toggle()
    return
  }
  router.push('/projects')
}
</script>

<style scoped>
.teacher-collaboration-entry {
  position: relative;
  width: 100%;
  min-height: 52px;
  padding: 8px 10px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 10px;
  color: var(--ds-ink-2);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.teacher-collaboration-entry:hover {
  border-color: rgba(232, 74, 28, 0.28);
  background: var(--ds-orange-wash);
  box-shadow: 0 4px 14px rgba(29, 29, 31, 0.04);
}

.teacher-collaboration-entry__text {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.teacher-collaboration-entry__text strong {
  font-size: 13px;
  font-weight: 700;
  color: var(--ds-ink);
}

.teacher-collaboration-entry__text small {
  font-size: 11px;
  color: var(--ds-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.teacher-collaboration-entry em {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange);
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.teacher-collaboration-entry:focus-visible {
  outline: 2px solid var(--ds-orange);
  outline-offset: 2px;
}

.teacher-collaboration-entry :deep(.teacher-collaboration-mark),
.teacher-collaboration-entry :deep(.collaboration-brand-mark) {
  width: 34px;
  height: 34px;
}
</style>
