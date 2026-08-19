<template>
  <form class="teacher-collaboration-form" @submit.prevent="submit">
    <div>
      <h3>发布协调任务</h3>
      <p>任务会进入学生协作台，成果提交后回到你的待审核列表。</p>
    </div>
    <label>
      <span>项目团队 *</span>
      <select v-model="form.teamId" required @change="loadMembers">
        <option value="" disabled>请选择团队</option>
        <option v-for="team in store.teams" :key="team.id" :value="team.id">{{ team.name }}</option>
      </select>
    </label>
    <label>
      <span>负责人 *</span>
      <select v-model="form.ownerUserId" required :disabled="memberLoading">
        <option value="" disabled>{{ memberLoading ? '正在加载成员' : '请选择负责人' }}</option>
        <option v-for="member in students" :key="member.userId" :value="member.userId">
          {{ member.username }} · {{ member.positionName || '项目成员' }}
        </option>
      </select>
    </label>
    <label>
      <span>任务标题 *</span>
      <input v-model.trim="form.title" maxlength="160" required placeholder="例如：完成决赛版路演材料核对" />
    </label>
    <label>
      <span>任务说明</span>
      <textarea v-model.trim="form.description" maxlength="1000" rows="4" placeholder="写清交付结果、验收标准和参考材料"></textarea>
    </label>
    <div class="teacher-collaboration-form__grid">
      <label>
        <span>优先级</span>
        <select v-model="form.priority">
          <option value="MEDIUM">普通</option>
          <option value="HIGH">高</option>
          <option value="URGENT">紧急</option>
          <option value="LOW">低</option>
        </select>
      </label>
      <label>
        <span>截止时间</span>
        <input v-model="form.dueAt" type="datetime-local" />
      </label>
    </div>
    <p v-if="error" class="is-error" role="alert">{{ error }}</p>
    <footer>
      <button type="button" @click="store.back">取消</button>
      <button class="is-primary" type="submit" :disabled="submitting">
        {{ submitting ? '正在发布…' : '发布任务' }}
      </button>
    </footer>
  </form>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchTeamDashboard } from '../../api'
import { useTeacherCollaborationStore } from '../../stores/collaboration'

const store = useTeacherCollaborationStore()
const form = reactive({
  teamId: store.activeTeamId === 'all' ? '' : store.activeTeamId,
  ownerUserId: '',
  title: '',
  description: '',
  priority: 'MEDIUM',
  dueAt: '',
})
const members = ref([])
const memberLoading = ref(false)
const submitting = ref(false)
const error = ref('')
const students = computed(() => members.value.filter(member => member.roleInTeam !== 'MENTOR'))

onMounted(async () => {
  await store.loadTeams()
  if (form.teamId) await loadMembers()
})

async function loadMembers() {
  form.ownerUserId = ''
  if (!form.teamId) return
  memberLoading.value = true
  error.value = ''
  try {
    const dashboard = await fetchTeamDashboard(form.teamId)
    members.value = dashboard?.members || []
  } catch (loadError) {
    error.value = loadError?.message || '团队成员加载失败'
  } finally {
    memberLoading.value = false
  }
}

async function submit() {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await store.publishTask(form.teamId, {
      title: form.title,
      description: form.description,
      ownerUserId: Number(form.ownerUserId),
      assigneeUserIds: [Number(form.ownerUserId)],
      priority: form.priority,
      dueAt: form.dueAt ? `${form.dueAt}:00` : null,
      status: 'TODO',
    })
  } catch (submitError) {
    error.value = submitError?.message || '任务发布失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.teacher-collaboration-form {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.teacher-collaboration-form h3 { margin: 0; font-size: 16px; }
.teacher-collaboration-form > div:first-child p { margin: 5px 0 0; color: var(--ds-muted); font-size: 11px; line-height: 1.6; }
.teacher-collaboration-form label { display: grid; gap: 6px; }
.teacher-collaboration-form label span { color: var(--ds-muted); font-size: 11px; font-weight: 700; }
.teacher-collaboration-form input,
.teacher-collaboration-form select,
.teacher-collaboration-form textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-input-border);
  border-radius: 9px;
  padding: 0 11px;
  color: var(--ds-ink);
  background: #fff;
  font: 500 12px var(--ds-font-sans);
}
.teacher-collaboration-form input,
.teacher-collaboration-form select { height: 38px; }
.teacher-collaboration-form textarea { min-height: 86px; padding-block: 9px; resize: vertical; line-height: 1.55; }
.teacher-collaboration-form input:focus,
.teacher-collaboration-form select:focus,
.teacher-collaboration-form textarea:focus { outline: none; border-color: var(--ds-orange); box-shadow: var(--ds-input-focus-ring); }
.teacher-collaboration-form__grid { display: grid; grid-template-columns: 112px minmax(0,1fr); gap: 10px; }
.teacher-collaboration-form .is-error { margin: 0; color: #b42318; font-size: 11px; }
.teacher-collaboration-form footer { margin-top: auto; padding-top: 14px; border-top: 1px solid var(--ds-line); display: flex; justify-content: flex-end; gap: 8px; }
.teacher-collaboration-form footer button { height: 36px; padding: 0 14px; border: 1px solid var(--ds-line-strong); border-radius: 9px; color: var(--ds-ink-2); background:#fff; font:700 12px var(--ds-font-sans); cursor:pointer; }
.teacher-collaboration-form footer button.is-primary { border-color: var(--ds-orange-deep); color:#fff; background:var(--ds-orange-deep); }
.teacher-collaboration-form footer button:disabled { opacity:.55; cursor:wait; }
</style>
