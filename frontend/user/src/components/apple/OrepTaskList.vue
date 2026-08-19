<template>
  <section class="orep-task-list" aria-label="今日任务">
    <header class="orep-task-list__header">
      <div>
        <span>Today's Path</span>
        <h2>今天练哪一段，Agent 已经排好。</h2>
      </div>
      <button type="button" @click="$emit('view-all')">查看团队任务</button>
    </header>

    <div class="orep-task-list__items">
      <article v-for="task in tasks" :key="task.id" class="orep-task-list__item">
        <span class="orep-task-list__type">{{ task.typeLabel || task.type }}</span>
        <div>
          <strong>{{ task.title }}</strong>
          <p>{{ task.description }}</p>
        </div>
        <button type="button" @click="$emit('action', task)">
          {{ task.actionText || '去完成' }}
        </button>
      </article>

      <article v-if="!tasks.length" class="orep-task-list__empty">
        <strong>今日没有强制任务</strong>
        <p>可以从脚本、PPT 或路演练习里任选一个环节继续推进。</p>
      </article>
    </div>
  </section>
</template>

<script setup>
defineEmits(['action', 'view-all'])

defineProps({
  tasks: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.orep-task-list {
  border: 1px solid var(--orep-border-soft);
  border-radius: 24px;
  background: oklch(1 0.003 255 / 0.78);
  padding: 22px;
}

.orep-task-list__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.orep-task-list__header span {
  color: var(--orep-blue);
  font-size: 12px;
  font-weight: 900;
}

.orep-task-list__header h2 {
  margin: 6px 0 0;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.25;
}

.orep-task-list__header button,
.orep-task-list__item button {
  border: 0;
  border-radius: 999px;
  background: var(--orep-blue-soft);
  color: var(--orep-blue);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.orep-task-list__header button {
  min-height: 36px;
  padding: 0 14px;
  white-space: nowrap;
}

.orep-task-list__items {
  display: grid;
  gap: 10px;
}

.orep-task-list__item {
  min-height: 82px;
  padding: 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 18px;
  background: var(--orep-surface-raised);
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}

.orep-task-list__type {
  min-height: 36px;
  border-radius: 999px;
  background: var(--orep-bg-soft);
  color: var(--orep-muted);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 900;
}

.orep-task-list__item strong,
.orep-task-list__empty strong {
  display: block;
  color: var(--orep-text-strong);
  font-size: 15px;
}

.orep-task-list__item p,
.orep-task-list__empty p {
  margin: 5px 0 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.45;
}

.orep-task-list__item button {
  min-height: 36px;
  padding: 0 14px;
}

.orep-task-list__empty {
  padding: 24px;
  border: 1px dashed var(--orep-border);
  border-radius: 18px;
  background: var(--orep-bg-soft);
}

@media (max-width: 640px) {
  .orep-task-list__header {
    display: grid;
  }

  .orep-task-list__item {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .orep-task-list__type {
    width: fit-content;
    padding: 0 12px;
  }
}
</style>
