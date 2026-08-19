<template>
  <article
    class="collaboration-item"
    :class="[{ 'is-action': item.actionRequired }, `is-source-${sourceTone}`]"
  >
    <button
      class="collaboration-item__main"
      type="button"
      :aria-label="`${item.sourceLabel || '协作任务'}：${item.title}，${statusLabel}`"
      @click="$emit('open', item)"
    >
      <span class="collaboration-item__signal" aria-hidden="true"></span>
      <span class="collaboration-item__content">
        <span class="collaboration-item__eyebrow">
          <span class="collaboration-item__source">{{ item.sourceLabel || '学生协作' }}</span>
          <em>{{ statusLabel }}</em>
        </span>
        <strong>{{ item.title }}</strong>
        <small>{{ relationshipText }}</small>
      </span>
      <span v-if="primaryActionLabel" class="collaboration-item__primary-label">
        {{ primaryActionLabel }}
      </span>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m9 6 6 6-6 6" />
      </svg>
    </button>
    <div v-if="item.canAccept || item.canWithdraw" class="collaboration-item__actions">
      <button v-if="item.canWithdraw" type="button" @click="$emit('withdraw', item)">撤回</button>
      <template v-if="item.canAccept">
        <button type="button" @click="$emit('decline', item)">婉拒</button>
        <button class="is-primary" type="button" @click="$emit('accept', item)">接受</button>
      </template>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true },
})

defineEmits(['open', 'accept', 'decline', 'withdraw'])

const fallbackStatusLabels = {
  PENDING: '等待回应',
  ACCEPTED: '进行中',
  TODO: '待开始',
  IN_PROGRESS: '进行中',
  REVIEWING: '待审核',
  CHANGES_REQUESTED: '待修改',
  DONE: '已完成',
  CANCELLED: '已取消',
  DECLINED: '已婉拒',
  WITHDRAWN: '已撤回',
  COMPLETED: '已完成',
}

const statusLabel = computed(() => (
  props.item.statusLabel
  || fallbackStatusLabels[props.item.status]
  || '任务'
))

const sourceTone = computed(() => ({
  TRAINING_DAY: 'training',
  TEAM_TASK: 'team',
  TEACHER_ASSIGNMENT: 'teacher',
  PEER_COLLABORATION: 'peer',
}[props.item.sourceType] || 'peer'))

const primaryActionLabel = computed(() => {
  if (props.item.canAccept || props.item.canWithdraw) return ''
  return {
    REVIEW: '审核',
    SUBMIT: '去完成',
    OPEN: '查看',
  }[props.item.primaryAction] || ''
})

const relationshipText = computed(() => {
  const team = props.item.teamName || '项目团队'
  const deadline = props.item.dueAt
    ? ` · 截止 ${String(props.item.dueAt).replace('T', ' ').slice(5, 16)}`
    : ''
  if (props.item.entityType === 'REQUEST' || !props.item.entityType) {
    const relationship = props.item.requesterIsCurrentUser
      ? `你发给 ${props.item.recipientName || '团队成员'}`
      : `${props.item.requesterName || '团队成员'} 发给你`
    return `${team} · ${relationship}${deadline}`
  }
  const publisher = props.item.createdByCurrentUser
    ? '你发布'
    : `${props.item.creatorName || props.item.requesterName || '团队成员'}发布`
  return `${team} · ${publisher}${deadline}`
})
</script>

<style scoped>
.collaboration-item {
  --collaboration-source: #7657d6;
  border-bottom: 1px solid var(--ds-line);
  background: #fff;
}

.collaboration-item:first-child {
  border-top: 1px solid var(--ds-line);
}

.collaboration-item.is-source-training { --collaboration-source: var(--ds-orange-500); }
.collaboration-item.is-source-team { --collaboration-source: #2d6cdf; }
.collaboration-item.is-source-teacher { --collaboration-source: #159a73; }

.collaboration-item.is-action {
  margin: 0 -8px;
  padding: 0 8px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(229, 72, 29, 0.055), rgba(255, 255, 255, 0));
}

.collaboration-item__main {
  width: 100%;
  min-height: 94px;
  border: 0;
  padding: 14px 4px;
  display: flex;
  align-items: flex-start;
  gap: 11px;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.collaboration-item__signal {
  flex: 0 0 8px;
  width: 8px;
  height: 8px;
  margin-top: 9px;
  border-radius: 999px;
  background: var(--collaboration-source);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--collaboration-source) 10%, transparent);
}

.collaboration-item__content {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 6px;
}

.collaboration-item__eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--ds-muted);
  font-size: 10px;
}

.collaboration-item__source {
  color: var(--collaboration-source);
  font-weight: 800;
}

.collaboration-item__eyebrow em {
  padding: 2px 6px;
  border-radius: 999px;
  color: var(--ds-ink-2);
  background: var(--ds-surface-soft);
  font-style: normal;
  font-weight: 700;
}

.collaboration-item.is-action .collaboration-item__eyebrow em {
  color: var(--ds-status-warning-fg);
  background: var(--ds-status-warning-bg);
}

.collaboration-item__content strong {
  overflow: hidden;
  color: var(--ds-ink);
  font-size: 14px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collaboration-item__content small {
  overflow: hidden;
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collaboration-item__primary-label {
  flex: 0 0 auto;
  margin-top: 30px;
  color: var(--collaboration-source);
  font-size: 10px;
  font-weight: 800;
}

.collaboration-item__main > svg {
  flex: 0 0 17px;
  width: 17px;
  margin-top: 29px;
  fill: none;
  stroke: var(--ds-faint);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.collaboration-item__actions {
  padding: 0 4px 12px 27px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.collaboration-item__actions button {
  height: 32px;
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: 9px;
  padding: 0 12px;
  color: var(--ds-ink-2);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.collaboration-item__actions button.is-primary {
  border-color: var(--ds-orange-700);
  color: #fff;
  background: var(--ds-orange-700);
}

.collaboration-item button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: 2px;
}

@media (max-width: 420px) {
  .collaboration-item__primary-label { display: none; }
}
</style>
