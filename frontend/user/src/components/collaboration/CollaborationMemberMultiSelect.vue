<template>
  <div ref="rootRef" class="member-multi-select" :class="{ 'is-open': isOpen }">
    <button
      class="member-multi-select__trigger"
      type="button"
      role="combobox"
      aria-haspopup="listbox"
      :aria-label="ariaLabel"
      :aria-expanded="isOpen"
      :disabled="disabled"
      @click="togglePanel"
      @keydown.down.prevent="openPanel"
    >
      <span :class="{ 'is-placeholder': selectedMembers.length === 0 }">
        {{ triggerText }}
      </span>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5" /></svg>
    </button>

    <div v-if="selectedMembers.length" class="member-multi-select__selection" aria-live="polite">
      <template v-if="selectedMembers.length <= 2">
        <span v-for="member in selectedMembers" :key="member.userId">
          {{ memberName(member) }}
          <button
            type="button"
            :aria-label="`移除 ${memberName(member)}`"
            @click="removeMember(member.userId)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 7 10 10M17 7 7 17" /></svg>
          </button>
        </span>
      </template>
      <span v-else class="is-count">已选 {{ selectedMembers.length }} 人</span>
    </div>

    <div
      v-if="isOpen"
      class="member-multi-select__panel"
      @keydown.esc.stop.prevent="closePanel"
    >
      <div class="member-multi-select__search">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" />
          <path d="m16 16 4 4" />
        </svg>
        <input
          ref="searchRef"
          v-model.trim="query"
          type="search"
          aria-label="搜索团队成员"
          placeholder="搜索姓名、账号或角色"
        />
      </div>

      <div class="member-multi-select__tools">
        <span>{{ filteredMembers.length }} 名成员</span>
        <div>
          <button
            type="button"
            :disabled="filteredMembers.length === 0 || allFilteredSelected"
            @click="selectFiltered"
          >
            全选当前结果
          </button>
          <button type="button" :disabled="selectedMembers.length === 0" @click="clearAll">
            清空
          </button>
        </div>
      </div>

      <div
        class="member-multi-select__options"
        role="listbox"
        aria-label="可邀请成员"
        aria-multiselectable="true"
      >
        <label
          v-for="member in filteredMembers"
          :key="member.userId"
          class="member-multi-select__option"
          :class="{ 'is-selected': isSelected(member.userId) }"
          role="option"
          :aria-selected="isSelected(member.userId)"
        >
          <input
            type="checkbox"
            :checked="isSelected(member.userId)"
            :disabled="!isSelected(member.userId) && modelValue.length >= max"
            @change="toggleMember(member.userId)"
          />
          <span class="member-multi-select__avatar" aria-hidden="true">
            {{ memberName(member).slice(0, 1).toUpperCase() }}
          </span>
          <span class="member-multi-select__identity">
            <strong>{{ memberName(member) }}</strong>
            <small>{{ member.positionName || member.roleName || member.roleInTeam || '项目成员' }}</small>
          </span>
          <svg class="member-multi-select__check" viewBox="0 0 24 24" aria-hidden="true">
            <path d="m6 12 4 4 8-8" />
          </svg>
        </label>
        <p v-if="filteredMembers.length === 0">没有找到匹配的团队成员</p>
      </div>

      <p v-if="modelValue.length >= max" class="member-multi-select__limit">
        一次最多邀请 {{ max }} 名成员
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  members: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  max: { type: Number, default: 50 },
  ariaLabel: { type: String, default: '协作成员 *' },
})

const emit = defineEmits(['update:modelValue'])
const rootRef = ref(null)
const searchRef = ref(null)
const isOpen = ref(false)
const query = ref('')

const selectedIds = computed(() => new Set(props.modelValue.map(Number)))
const selectedMembers = computed(() => props.modelValue
  .map(id => props.members.find(member => Number(member.userId) === Number(id)))
  .filter(Boolean))
const filteredMembers = computed(() => {
  const keyword = query.value.toLowerCase()
  if (!keyword) return props.members
  return props.members.filter(member => [
    member.username,
    member.name,
    member.account,
    member.positionName,
    member.roleName,
    member.roleInTeam,
  ].some(value => String(value || '').toLowerCase().includes(keyword)))
})
const allFilteredSelected = computed(() => (
  filteredMembers.value.length > 0
  && filteredMembers.value.every(member => selectedIds.value.has(Number(member.userId)))
))
const triggerText = computed(() => {
  if (props.loading) return '正在加载成员…'
  if (!props.modelValue.length) return props.disabled ? '请先选择项目团队' : '请选择协作成员'
  if (selectedMembers.value.length <= 2) {
    return selectedMembers.value.map(memberName).join('、')
  }
  return `已选择 ${selectedMembers.value.length} 名成员`
})

onMounted(() => document.addEventListener('pointerdown', handleOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', handleOutside))

function memberName(member) {
  return member?.username || member?.name || member?.account || '团队成员'
}

function isSelected(userId) {
  return selectedIds.value.has(Number(userId))
}

function togglePanel() {
  if (isOpen.value) closePanel()
  else openPanel()
}

async function openPanel() {
  if (props.disabled) return
  isOpen.value = true
  await nextTick()
  searchRef.value?.focus({ preventScroll: true })
}

function closePanel() {
  isOpen.value = false
  query.value = ''
}

function toggleMember(userId) {
  const id = Number(userId)
  if (isSelected(id)) {
    emit('update:modelValue', props.modelValue.filter(value => Number(value) !== id))
    return
  }
  if (props.modelValue.length >= props.max) return
  emit('update:modelValue', [...props.modelValue, id])
}

function removeMember(userId) {
  const id = Number(userId)
  emit('update:modelValue', props.modelValue.filter(value => Number(value) !== id))
}

function selectFiltered() {
  const next = [...props.modelValue]
  const selected = new Set(next.map(Number))
  for (const member of filteredMembers.value) {
    const id = Number(member.userId)
    if (selected.has(id)) continue
    if (next.length >= props.max) break
    next.push(id)
    selected.add(id)
  }
  emit('update:modelValue', next)
}

function clearAll() {
  emit('update:modelValue', [])
}

function handleOutside(event) {
  if (isOpen.value && !rootRef.value?.contains(event.target)) closePanel()
}
</script>

<style scoped>
.member-multi-select {
  position: relative;
}

.member-multi-select__trigger {
  width: 100%;
  height: 40px;
  border: 1px solid var(--ds-input-border);
  border-radius: 10px;
  padding: 0 11px 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--ds-ink);
  background: #fff;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.member-multi-select__trigger > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-multi-select__trigger .is-placeholder {
  color: var(--ds-faint);
}

.member-multi-select__trigger svg {
  flex: 0 0 17px;
  width: 17px;
  fill: none;
  stroke: var(--ds-muted);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 160ms ease;
}

.member-multi-select.is-open .member-multi-select__trigger {
  border-color: var(--ds-input-focus-border);
  box-shadow: var(--ds-input-focus-ring);
}

.member-multi-select.is-open .member-multi-select__trigger svg {
  transform: rotate(180deg);
}

.member-multi-select__trigger:disabled {
  color: var(--ds-btn-disabled-fg);
  background: var(--ds-btn-disabled-bg);
  cursor: not-allowed;
}

.member-multi-select__selection {
  margin-top: 7px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.member-multi-select__selection > span {
  max-width: 100%;
  height: 25px;
  border-radius: 7px;
  padding: 0 6px 0 9px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  overflow: hidden;
  color: #2d5ea8;
  background: #eef5ff;
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-multi-select__selection > span.is-count {
  padding-inline: 9px;
  color: var(--ds-orange-700);
  background: var(--ds-orange-50);
}

.member-multi-select__selection button {
  flex: 0 0 20px;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 5px;
  padding: 0;
  display: grid;
  place-items: center;
  color: inherit;
  background: transparent;
  cursor: pointer;
}

.member-multi-select__selection button:hover {
  background: rgba(45, 94, 168, 0.1);
}

.member-multi-select__selection svg {
  width: 13px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
}

.member-multi-select__panel {
  position: absolute;
  z-index: 8;
  top: calc(100% + 8px);
  right: 0;
  left: 0;
  border: 1px solid var(--ds-card-border);
  border-radius: 13px;
  padding: 10px;
  color: var(--ds-ink);
  background: #fff;
  box-shadow: 0 16px 36px rgba(29, 29, 31, 0.14), 0 2px 8px rgba(29, 29, 31, 0.06);
  animation: member-panel-in 160ms ease-out both;
}

.member-multi-select__search {
  height: 38px;
  border: 1px solid var(--ds-input-border);
  border-radius: 9px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.member-multi-select__search:focus-within {
  border-color: var(--ds-input-focus-border);
  box-shadow: var(--ds-input-focus-ring);
}

.member-multi-select__search svg {
  flex: 0 0 17px;
  width: 17px;
  fill: none;
  stroke: var(--ds-muted);
  stroke-width: 1.7;
  stroke-linecap: round;
}

.member-multi-select__search input {
  min-width: 0;
  height: 100%;
  border: 0;
  padding: 0;
  flex: 1;
  color: inherit;
  background: transparent;
  font: inherit;
  font-size: 12px;
  outline: 0;
}

.member-multi-select__tools {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--ds-faint);
  font-size: 10px;
}

.member-multi-select__tools > div {
  display: flex;
  gap: 9px;
}

.member-multi-select__tools button {
  border: 0;
  padding: 4px 0;
  color: #2d6cdf;
  background: transparent;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}

.member-multi-select__tools button:disabled {
  color: var(--ds-faint);
  cursor: default;
}

.member-multi-select__options {
  max-height: 230px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.member-multi-select__option {
  min-height: 50px;
  border-radius: 9px;
  padding: 6px 8px;
  display: flex;
  align-items: center;
  gap: 9px;
  cursor: pointer;
}

.member-multi-select__option:hover {
  background: var(--ds-surface-soft);
}

.member-multi-select__option.is-selected {
  background: #f0f6ff;
}

.member-multi-select__option > input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
}

.member-multi-select__avatar {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #2d6cdf;
  background: #e9f2ff;
  font-size: 12px;
  font-weight: 800;
}

.member-multi-select__identity {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 2px;
}

.member-multi-select__identity strong,
.member-multi-select__identity small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.member-multi-select__identity strong {
  font-size: 12px;
}

.member-multi-select__identity small {
  color: var(--ds-muted);
  font-size: 10px;
}

.member-multi-select__check {
  flex: 0 0 18px;
  width: 18px;
  fill: none;
  stroke: transparent;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.member-multi-select__option.is-selected .member-multi-select__check {
  stroke: #2d6cdf;
}

.member-multi-select__options > p {
  margin: 24px 0;
  color: var(--ds-muted);
  font-size: 11px;
  text-align: center;
}

.member-multi-select__limit {
  margin: 8px 2px 0;
  color: var(--ds-status-warning-fg);
  font-size: 10px;
}

@keyframes member-panel-in {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.99);
  }
}

@media (prefers-reduced-motion: reduce) {
  .member-multi-select__panel {
    animation-duration: 0.01ms;
  }

  .member-multi-select__trigger,
  .member-multi-select__trigger svg {
    transition-duration: 0.01ms;
  }
}
</style>
