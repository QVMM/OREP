<template>
  <div class="priority-tabs" role="tablist" aria-label="问题优先级筛选">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="tab"
      :aria-selected="option.value === modelValue"
      :aria-disabled="option.count === 0 && option.value !== 'all'"
      :disabled="option.count === 0 && option.value !== 'all'"
      :class="['priority-tab', option.tone, { active: option.value === modelValue }]"
      @click="$emit('update:modelValue', option.value)"
    >
      <span>{{ option.label }}</span>
      <b>{{ option.count }}</b>
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: 'all' },
  options: { type: Array, default: () => [] }
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.priority-tabs {
  display: grid;
  grid-template-columns: 1.18fr repeat(3, minmax(0, 1fr));
  gap: 0;
  margin: 0 0 12px;
  padding: 3px;
  border: 1px solid #e6edf5;
  border-radius: 9px;
  background: #f8fafc;
}

.priority-tab {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  min-width: 0;
  height: 30px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: #7a8798;
  padding: 0 7px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.priority-tab:disabled {
  cursor: default;
  opacity: .58;
}

.priority-tab span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.priority-tab:first-child span {
  min-width: 24px;
}

.priority-tab b {
  display: inline-grid;
  flex: 0 0 auto;
  min-width: 18px;
  height: 18px;
  place-items: center;
  padding: 0 5px;
  border-radius: 999px;
  background: #edf2f7;
  color: #667085;
  font-size: 11px;
  line-height: 1;
}

.priority-tab.active {
  border-color: #ffd7c8;
  background: #fff;
  box-shadow: 0 1px 2px rgba(17, 24, 39, .05);
  color: #e24b1a;
}

.priority-tab.active b,
.priority-tab.danger.active b {
  background: #f15a24;
  color: #fffaf7;
}

.priority-tab.danger:not(.active) b {
  background: #fff0ed;
  color: #d92d20;
}

.priority-tab.medium:not(.active) b {
  background: #fff4e8;
  color: #dc6803;
}

.priority-tab.low:not(.active) b {
  background: #eef4ff;
  color: #47607a;
}
</style>
