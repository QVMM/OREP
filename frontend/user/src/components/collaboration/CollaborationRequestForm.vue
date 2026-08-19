<template>
  <section v-if="successResult" class="collaboration-form-success" aria-live="polite">
    <span class="collaboration-form-success__icon" aria-hidden="true">
      <svg viewBox="0 0 24 24"><path d="m6 12 4 4 8-8" /></svg>
    </span>
    <h3>已向 {{ successResult.count }} 人发送协作申请</h3>
    <p>每位成员可以独立接受、完成并提交自己的协作任务。</p>
    <div>
      <button type="button" @click="returnToList">返回任务列表</button>
      <button class="is-primary" type="button" @click="continueCreating">继续发起</button>
    </div>
  </section>

  <form v-else class="collaboration-form" @submit.prevent="submit">
    <header>
      <h3>发起协作</h3>
      <p>一次可邀请多名团队成员，每个人会收到一项独立任务。</p>
    </header>

    <label>
      <span>项目团队 *</span>
      <select v-model="form.teamId" required @change="changeTeam">
        <option value="" disabled>请选择团队</option>
        <option v-for="team in store.teams" :key="team.id" :value="team.id">
          {{ team.name }}
        </option>
      </select>
    </label>

    <div class="collaboration-form__field">
      <span>协作成员 *</span>
      <CollaborationMemberMultiSelect
        v-model="form.recipientUserIds"
        :members="availableMembers"
        :loading="memberLoading"
        :disabled="!form.teamId || memberLoading"
        :max="50"
        aria-label="协作成员 *"
      />
    </div>

    <label>
      <span>任务标题 *</span>
      <input v-model.trim="form.title" maxlength="160" required placeholder="例如：完善路演稿第 3 部分" />
    </label>

    <label>
      <span>任务说明</span>
      <textarea
        v-model.trim="form.description"
        maxlength="1000"
        rows="4"
        placeholder="说明交付结果、参考材料或需要协助的重点"
      ></textarea>
    </label>

    <div class="collaboration-form__grid">
      <label>
        <span>优先级</span>
        <select v-model="form.priority">
          <option value="LOW">低</option>
          <option value="MEDIUM">普通</option>
          <option value="HIGH">高</option>
          <option value="URGENT">紧急</option>
        </select>
      </label>
      <label>
        <span>期望截止</span>
        <input v-model="form.dueAt" type="datetime-local" />
      </label>
    </div>

    <p v-if="errorMessage" class="collaboration-form__error" role="alert">{{ errorMessage }}</p>

    <footer>
      <button type="button" @click="store.back">取消</button>
      <button
        class="is-primary"
        type="submit"
        :disabled="submitting || !canSubmit"
      >
        {{ submitLabel }}
      </button>
    </footer>
  </form>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useCollaborationStore } from '../../stores/collaboration'
import CollaborationMemberMultiSelect from './CollaborationMemberMultiSelect.vue'

const store = useCollaborationStore()
const auth = useAuthStore()
const initial = store.drafts.request || {}
const form = reactive({
  teamId: initial.teamId || store.activeTeamId || '',
  recipientUserIds: Array.isArray(initial.recipientUserIds)
    ? initial.recipientUserIds.map(Number)
    : initial.recipientUserId ? [Number(initial.recipientUserId)] : [],
  title: initial.title || '',
  description: initial.description || '',
  priority: initial.priority || 'MEDIUM',
  dueAt: initial.dueAt || '',
})
const memberLoading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const successResult = ref(null)
const retryKey = ref('')
const retryFingerprint = ref('')

const availableMembers = computed(() => {
  const members = store.membersByTeam[String(form.teamId)] || []
  const currentUserId = Number(auth.user?.id || auth.user?.userId)
  return members.filter(member => Number(member.userId) !== currentUserId)
})
const canSubmit = computed(() => (
  Boolean(form.teamId)
  && form.recipientUserIds.length > 0
  && form.recipientUserIds.length <= 50
  && Boolean(form.title.trim())
))
const submitLabel = computed(() => {
  if (submitting.value) return `正在向 ${form.recipientUserIds.length} 人发送…`
  if (!form.recipientUserIds.length) return '请选择协作成员'
  if (form.recipientUserIds.length === 1) return '发送协作申请'
  return `向 ${form.recipientUserIds.length} 人发送协作申请`
})

watch(
  form,
  value => {
    store.drafts.request = {
      ...value,
      recipientUserIds: [...value.recipientUserIds],
    }
  },
  { deep: true }
)

onMounted(async () => {
  try {
    await store.loadTeams()
    if (form.teamId) await loadMembers(false)
  } catch (error) {
    errorMessage.value = errorMessageOf(error, '团队信息加载失败')
  }
})

async function changeTeam() {
  await loadMembers(true)
}

async function loadMembers(clearRecipients) {
  if (clearRecipients) form.recipientUserIds = []
  if (!form.teamId) return
  memberLoading.value = true
  errorMessage.value = ''
  try {
    await store.loadMembers(form.teamId)
    const availableIds = new Set(availableMembers.value.map(member => Number(member.userId)))
    form.recipientUserIds = form.recipientUserIds.filter(id => availableIds.has(Number(id)))
  } catch (error) {
    errorMessage.value = errorMessageOf(error, '团队成员加载失败')
  } finally {
    memberLoading.value = false
  }
}

async function submit() {
  if (submitting.value || !canSubmit.value) return
  const payload = {
    teamId: Number(form.teamId),
    recipientUserIds: form.recipientUserIds.map(Number),
    title: form.title,
    description: form.description,
    priority: form.priority,
    dueAt: form.dueAt ? `${form.dueAt}:00` : null,
  }
  const fingerprint = JSON.stringify(payload)
  if (!retryKey.value || retryFingerprint.value !== fingerprint) {
    retryKey.value = createIdempotencyKey()
    retryFingerprint.value = fingerprint
  }

  submitting.value = true
  errorMessage.value = ''
  try {
    successResult.value = await store.createRequests(payload, retryKey.value)
  } catch (error) {
    errorMessage.value = errorMessageOf(
      error,
      '协作申请发送失败，请检查网络后重试'
    )
    if (errorMessage.value.includes('重新发送')
      || errorMessage.value.includes('状态不完整')) {
      retryKey.value = ''
      retryFingerprint.value = ''
    }
  } finally {
    submitting.value = false
  }
}

function returnToList() {
  delete store.drafts.request
  store.setActiveTab('CREATED_BY_ME')
  store.back()
}

function continueCreating() {
  const teamId = form.teamId
  Object.assign(form, {
    teamId,
    recipientUserIds: [],
    title: '',
    description: '',
    priority: 'MEDIUM',
    dueAt: '',
  })
  retryKey.value = ''
  retryFingerprint.value = ''
  successResult.value = null
  errorMessage.value = ''
}

function createIdempotencyKey() {
  return globalThis.crypto?.randomUUID?.()
    || `collaboration-batch-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function errorMessageOf(error, fallback) {
  return error?.response?.data?.message
    || error?.response?.data?.detail
    || error?.message
    || fallback
}
</script>

<style scoped>
.collaboration-form,
.collaboration-form-success {
  min-height: 100%;
}

.collaboration-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.collaboration-form header {
  margin-bottom: 4px;
}

.collaboration-form h3,
.collaboration-form-success h3 {
  margin: 0;
  font-size: 16px;
}

.collaboration-form header p {
  margin: 5px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}

.collaboration-form label,
.collaboration-form__field {
  display: grid;
  gap: 7px;
}

.collaboration-form label > span,
.collaboration-form__field > span {
  color: var(--ds-ink-2);
  font-size: 12px;
  font-weight: 700;
}

.collaboration-form input,
.collaboration-form select,
.collaboration-form textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--ds-input-border);
  border-radius: 10px;
  padding: 0 12px;
  color: var(--ds-ink);
  background: #fff;
  font: inherit;
  font-size: 13px;
}

.collaboration-form input,
.collaboration-form select {
  height: 40px;
}

.collaboration-form textarea {
  min-height: 92px;
  padding-block: 10px;
  resize: vertical;
  line-height: 1.55;
}

.collaboration-form input:focus,
.collaboration-form select:focus,
.collaboration-form textarea:focus {
  border-color: var(--ds-input-focus-border);
  outline: none;
  box-shadow: var(--ds-input-focus-ring);
}

.collaboration-form__grid {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 12px;
}

.collaboration-form__error {
  margin: 0;
  border-radius: 9px;
  padding: 9px 11px;
  color: var(--ds-status-danger-fg);
  background: var(--ds-status-danger-bg);
  font-size: 11px;
  line-height: 1.5;
}

.collaboration-form footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--ds-line);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.collaboration-form footer button,
.collaboration-form-success button {
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

.collaboration-form footer button.is-primary,
.collaboration-form-success button.is-primary {
  border-color: var(--ds-orange-700);
  color: #fff;
  background: var(--ds-orange-700);
}

.collaboration-form footer button:disabled {
  border-color: var(--ds-btn-disabled-border);
  color: var(--ds-btn-disabled-fg);
  background: var(--ds-btn-disabled-bg);
  cursor: not-allowed;
}

.collaboration-form-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.collaboration-form-success__icon {
  width: 54px;
  height: 54px;
  margin-bottom: 16px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, #2f9d77, #37b78d);
  box-shadow: 0 10px 24px rgba(47, 157, 119, 0.2);
}

.collaboration-form-success__icon svg {
  width: 28px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.collaboration-form-success p {
  max-width: 290px;
  margin: 9px 0 22px;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.6;
}

.collaboration-form-success > div {
  display: flex;
  gap: 8px;
}

@media (max-width: 420px) {
  .collaboration-form__grid {
    grid-template-columns: 1fr;
  }

  .collaboration-form-success > div {
    width: 100%;
  }

  .collaboration-form-success button {
    min-width: 0;
    flex: 1;
  }
}
</style>
