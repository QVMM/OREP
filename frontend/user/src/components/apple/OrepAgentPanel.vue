<template>
  <aside class="orep-agent-panel" aria-label="OREP Agent 建议">
    <header>
      <span>OREP Agent</span>
      <h2>下一步建议</h2>
    </header>

    <div class="orep-agent-panel__list">
      <article v-for="suggestion in suggestions" :key="suggestion.title">
        <strong>{{ suggestion.title }}</strong>
        <p>{{ suggestion.description }}</p>
      </article>
    </div>

    <button type="button" @click="$emit('start')">让 Agent 帮我整理</button>
  </aside>
</template>

<script setup>
defineEmits(['start'])

defineProps({
  suggestions: {
    type: Array,
    default: () => [],
  },
})
</script>

<style scoped>
.orep-agent-panel {
  border: 1px solid oklch(0.85 0.03 255);
  border-radius: 24px;
  background:
    linear-gradient(180deg, var(--orep-blue-soft), oklch(1 0.003 255));
  padding: 22px;
  display: grid;
  gap: 18px;
}

.orep-agent-panel header span {
  color: var(--orep-blue);
  font-size: 12px;
  font-weight: 900;
}

.orep-agent-panel h2 {
  margin: 6px 0 0;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.25;
}

.orep-agent-panel__list {
  display: grid;
  gap: 10px;
}

.orep-agent-panel article {
  padding: 14px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 18px;
  background: oklch(1 0.003 255 / 0.72);
}

.orep-agent-panel strong {
  display: block;
  color: var(--orep-text-strong);
  font-size: 14px;
}

.orep-agent-panel p {
  margin: 6px 0 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.5;
}

.orep-agent-panel button {
  min-height: 44px;
  border: 0;
  border-radius: 999px;
  background: var(--orep-blue);
  color: oklch(0.99 0.004 255);
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}
</style>
