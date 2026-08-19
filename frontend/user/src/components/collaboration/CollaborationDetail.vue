<template>
  <div class="collaboration-detail">
    <div class="collaboration-detail__heading">
      <span>{{ item.teamName || '项目团队' }}</span>
      <em>{{ statusLabel }}</em>
      <h3>{{ item.title }}</h3>
      <p>{{ item.description || '发起人暂未补充任务说明。' }}</p>
    </div>

    <dl>
      <div>
        <dt>发起人</dt>
        <dd>{{ item.requesterName || '团队成员' }}</dd>
      </div>
      <div>
        <dt>协作成员</dt>
        <dd>{{ item.recipientName || '团队成员' }}</dd>
      </div>
      <div>
        <dt>优先级</dt>
        <dd>{{ priorityLabel }}</dd>
      </div>
      <div>
        <dt>期望截止</dt>
        <dd>{{ deadlineLabel }}</dd>
      </div>
    </dl>

    <div v-if="item.responseReason" class="collaboration-detail__notice">
      <strong>响应说明</strong>
      <p>{{ item.responseReason }}</p>
    </div>

    <div v-if="declining" class="collaboration-detail__decline">
      <label for="collaboration-decline-reason">婉拒说明（可选）</label>
      <textarea
        id="collaboration-decline-reason"
        v-model.trim="declineReason"
        maxlength="500"
        rows="3"
        placeholder="简单说明原因，便于对方重新安排"
      ></textarea>
    </div>

    <p v-if="errorMessage" class="collaboration-detail__error" role="alert">{{ errorMessage }}</p>

    <footer>
      <button v-if="item.canWithdraw" type="button" :disabled="busy" @click="withdraw">撤回申请</button>
      <template v-if="item.canAccept">
        <button v-if="!declining" type="button" :disabled="busy" @click="declining = true">婉拒</button>
        <button v-else type="button" :disabled="busy" @click="decline">确认婉拒</button>
        <button class="is-primary" type="button" :disabled="busy" @click="accept">接受协作</button>
      </template>
      <button
        v-if="item.linkedTaskId"
        class="is-primary"
        type="button"
        @click="openTask"
      >
        打开任务
      </button>
    </footer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCollaborationStore } from '../../stores/collaboration'

const props = defineProps({
  item: { type: Object, required: true },
})

const store = useCollaborationStore()
const router = useRouter()
const busy = ref(false)
const declining = ref(false)
const declineReason = ref('')
const errorMessage = ref('')

const statusLabel = computed(() => ({
  PENDING: '等待回应',
  ACCEPTED: '协作进行中',
  DECLINED: '已婉拒',
  WITHDRAWN: '已撤回',
  COMPLETED: '已完成',
}[props.item.status] || '协作任务'))

const priorityLabel = computed(() => ({
  LOW: '低',
  MEDIUM: '普通',
  HIGH: '高',
  URGENT: '紧急',
}[props.item.priority] || '普通'))

const deadlineLabel = computed(() => (
  props.item.dueAt
    ? String(props.item.dueAt).replace('T', ' ').slice(0, 16)
    : '未设置'
))

async function run(action) {
  if (busy.value) return
  busy.value = true
  errorMessage.value = ''
  try {
    await action()
  } catch (error) {
    errorMessage.value = error?.message || '操作失败，请刷新后重试'
  } finally {
    busy.value = false
  }
}

function accept() {
  return run(() => store.accept(props.item.id))
}

function decline() {
  return run(() => store.decline(props.item.id, declineReason.value))
}

function withdraw() {
  return run(() => store.withdraw(props.item.id))
}

function openTask() {
  store.close()
  router.push({
    path: `/project-team/details/task-${props.item.linkedTaskId}`,
    query: { teamId: props.item.teamId },
  })
}
</script>

<style scoped>
.collaboration-detail {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.collaboration-detail__heading {
  padding-bottom: 20px;
  border-bottom: 1px solid var(--ds-line);
}

.collaboration-detail__heading > span {
  color: var(--ds-muted);
  font-size: 12px;
}

.collaboration-detail__heading > em {
  margin-left: 8px;
  padding: 3px 7px;
  border-radius: 999px;
  color: var(--ds-status-warning-fg);
  background: var(--ds-status-warning-bg);
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
}

.collaboration-detail h3 {
  margin: 14px 0 8px;
  font-size: 18px;
  line-height: 1.4;
}

.collaboration-detail__heading p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.collaboration-detail dl {
  margin: 0;
  padding: 20px 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 20px;
}

.collaboration-detail dl > div {
  display: grid;
  gap: 5px;
}

.collaboration-detail dt {
  color: var(--ds-muted);
  font-size: 11px;
}

.collaboration-detail dd {
  margin: 0;
  color: var(--ds-ink-2);
  font-size: 13px;
  font-weight: 600;
}

.collaboration-detail__notice,
.collaboration-detail__decline {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 10px;
  background: #f5f6f8;
}

.collaboration-detail__notice strong,
.collaboration-detail__decline label {
  font-size: 12px;
}

.collaboration-detail__notice p {
  margin: 5px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}

.collaboration-detail__decline {
  display: grid;
  gap: 8px;
}

.collaboration-detail__decline textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-input-border);
  border-radius: 9px;
  padding: 9px 10px;
  font: inherit;
  font-size: 12px;
  resize: vertical;
}

.collaboration-detail__error {
  margin: 0 0 12px;
  color: var(--ds-status-danger-fg);
  font-size: 12px;
}

.collaboration-detail footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--ds-line);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.collaboration-detail footer button {
  height: 36px;
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: 10px;
  padding: 0 14px;
  color: var(--ds-ink-2);
  background: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.collaboration-detail footer button.is-primary {
  border-color: var(--ds-orange-700);
  color: #fff;
  background: var(--ds-orange-700);
}

.collaboration-detail footer button:disabled {
  opacity: 0.55;
  cursor: wait;
}
</style>
