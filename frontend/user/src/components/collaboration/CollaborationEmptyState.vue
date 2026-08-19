<template>
  <div class="collaboration-empty">
    <span aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <path d="M7 5.5h10A2.5 2.5 0 0 1 19.5 8v8A2.5 2.5 0 0 1 17 18.5H9L4.5 21v-4A2.5 2.5 0 0 1 3 14.7V8A2.5 2.5 0 0 1 5.5 5.5H7Z" />
        <path d="M8 10h8M8 14h5" />
      </svg>
    </span>
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '这里暂时没有任务' },
  description: { type: String, default: '新的协作任务和状态变化会集中出现在这里。' },
})
</script>

<style scoped>
.collaboration-empty {
  min-height: 264px;
  border: 1px dashed var(--ds-line-strong);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  background: #fafafb;
}

.collaboration-empty > span {
  width: 44px;
  height: 44px;
  margin-bottom: 16px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-700);
  background: var(--ds-orange-50);
}

.collaboration-empty svg {
  width: 23px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.collaboration-empty strong {
  font-size: 14px;
}

.collaboration-empty p {
  max-width: 300px;
  margin: 8px 0 0;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.65;
}
</style>
