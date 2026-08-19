<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="sync-modal-root"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ai-score-team-sync-title"
    >
      <div class="scrim" @click="close" />
      <div class="modal" :class="{ 'is-success': phase === 'success' }">
        <template v-if="phase === 'form'">
          <h2 id="ai-score-team-sync-title">同步到团队任务</h2>
          <p class="d">选团队，勾选要派的待办。改完可在任务管理里跟进。</p>

          <label for="ai-score-team-select">项目团队</label>
          <select
            id="ai-score-team-select"
            v-model="teamId"
            :disabled="!teams.length || creating"
          >
            <option value="" disabled>
              {{ teams.length ? '请选择项目团队' : '暂无可用团队' }}
            </option>
            <option
              v-for="team in teams"
              :key="team.id"
              :value="String(team.id)"
            >
              {{ teamLabel(team) }}
            </option>
          </select>

          <p v-if="!teams.length" class="hint">
            请先加入或创建项目团队，再同步任务。
          </p>

          <div v-if="selectableItems.length" class="check-list" role="group" aria-label="待同步任务">
            <label
              v-for="item in selectableItems"
              :key="item.id"
              class="check"
            >
              <input
                type="checkbox"
                :value="item.id"
                :checked="localSelectedIds.includes(item.id)"
                :disabled="creating"
                @change="toggleItem(item.id, $event.target.checked)"
              >
              <div>
                <strong>{{ item.title }}</strong>
                <small v-if="item.recoverDisplay">大约能涨 {{ item.recoverDisplay }}</small>
              </div>
            </label>
          </div>
          <p v-else class="hint">暂无可同步的工作项草稿。</p>

          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" :disabled="creating" @click="close">
              取消
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="creating || !canSubmit"
              @click="confirmSync"
            >
              {{ creating ? '同步中…' : `确认同步${selectedCount ? ` ${selectedCount} 条` : ''}` }}
            </button>
          </div>
        </template>

        <template v-else>
          <h2 id="ai-score-team-sync-title">已同步 {{ successCount }} 条任务</h2>
          <p class="d">可在任务管理里更新进度。</p>
          <div class="modal-actions">
            <button type="button" class="btn btn-ghost" @click="close">留在这里</button>
            <button type="button" class="btn btn-primary" @click="goBoard">去任务看板</button>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAiScoreReportContext } from '../../../composables/useAiScoreReport'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  /** Selectable work items: { id, title, recoverDisplay? } */
  items: { type: Array, default: () => [] },
  /** Optional pre-checked ids; empty → check all selectable */
  preselectedIds: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'success'])

const report = useAiScoreReportContext()

const phase = ref('form')
const localSelectedIds = ref([])
const successCount = ref(0)
const teamId = ref('')

const teams = computed(() => report.availableTeams.value || [])
const creating = computed(() => Boolean(report.creatingTeamTasks.value))

const draftItems = computed(() => {
  const drafts = report.reportWorkItemDrafts?.value || []
  return drafts.map((item) => ({
    id: String(item.id),
    title: String(item.title || '').trim() || String(item.id),
    recoverDisplay: recoverFromDraft(item)
  })).filter((item) => item.id)
})

const selectableItems = computed(() => {
  const fromProps = (props.items || [])
    .map((item) => ({
      id: String(item?.id ?? ''),
      title: String(item?.title || '').trim(),
      recoverDisplay: item?.recoverDisplay ? String(item.recoverDisplay) : ''
    }))
    .filter((item) => item.id && item.title)

  if (!fromProps.length) return draftItems.value

  // Only keep items that map to real work-item drafts (API requires draft ids)
  const draftById = new Map(draftItems.value.map((d) => [d.id, d]))
  const mapped = fromProps
    .map((item) => {
      const draft = draftById.get(item.id)
      if (!draft) return null
      return {
        id: draft.id,
        title: item.title || draft.title,
        recoverDisplay: item.recoverDisplay || draft.recoverDisplay
      }
    })
    .filter(Boolean)

  // If none of the presentation ids match drafts, fall back to drafts so sync still works
  return mapped.length ? mapped : draftItems.value
})

const selectedCount = computed(() => localSelectedIds.value.length)

const canSubmit = computed(() =>
  Boolean(teamId.value) && selectedCount.value > 0 && teams.value.length > 0
)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) {
      phase.value = 'form'
      return
    }
    phase.value = 'form'
    successCount.value = 0
    if (!report.availableTeams.value?.length) {
      await report.loadAvailableTeams?.()
    }
    teamId.value = String(report.selectedTeamIdForTasks.value || '')
    if (!teamId.value && teams.value.length === 1) {
      teamId.value = String(teams.value[0].id)
    }
    initSelection()
  }
)

watch(teamId, (id) => {
  if (props.modelValue && id) {
    report.selectedTeamIdForTasks.value = String(id)
  }
})

function initSelection() {
  const available = new Set(selectableItems.value.map((item) => item.id))
  const preferred = (props.preselectedIds || [])
    .map(String)
    .filter((id) => available.has(id))
  if (preferred.length) {
    localSelectedIds.value = preferred
    return
  }
  const fromContext = (report.selectedReportWorkItemIds.value || [])
    .map(String)
    .filter((id) => available.has(id))
  if (fromContext.length) {
    localSelectedIds.value = fromContext
    return
  }
  localSelectedIds.value = selectableItems.value.map((item) => item.id)
}

function toggleItem(id, checked) {
  const key = String(id)
  if (checked) {
    if (!localSelectedIds.value.includes(key)) {
      localSelectedIds.value = [...localSelectedIds.value, key]
    }
  } else {
    localSelectedIds.value = localSelectedIds.value.filter((x) => x !== key)
  }
}

function teamLabel(team) {
  const name = firstPresent(team?.name, team?.teamName, team?.team_name, team?.title, '')
  return name || `团队 ${team?.id ?? ''}`
}

function recoverFromDraft(item) {
  const n = Number(
    firstPresent(
      item.expectedRecoverPoints,
      item.expected_recover_points,
      item.recoverableScore,
      item.maxRecoverablePoints
    )
  )
  if (!Number.isFinite(n) || n === 0) return ''
  return `+${Math.abs(n).toFixed(1)}`
}

function firstPresent(...values) {
  return values.find((v) => v !== undefined && v !== null && v !== '')
}

function close() {
  emit('update:modelValue', false)
}

async function confirmSync() {
  if (!canSubmit.value) {
    if (!teamId.value) ElMessage.warning('请先选择项目团队')
    else if (!selectedCount.value) ElMessage.warning('请选择要生成的工作项')
    return
  }
  report.selectedTeamIdForTasks.value = String(teamId.value)
  report.selectedReportWorkItemIds.value = [...localSelectedIds.value]

  // Reset so early-return (no create) does not reuse a prior count as success.
  report.createdTeamTaskCount.value = 0
  await report.createTeamTasksFromReport()
  const created = Number(report.createdTeamTaskCount.value || 0)
  if (created > 0) {
    successCount.value = created
    phase.value = 'success'
    emit('success', { count: created, ids: [...localSelectedIds.value] })
  }
}

function goBoard() {
  close()
  report.goTeamScoreWorkItems?.()
}
</script>

<style scoped>
.sync-modal-root {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 24px;
  font-family: "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", "Noto Sans SC",
    -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
  color: #171a24;
}

.scrim {
  position: absolute;
  inset: 0;
  background: rgba(23, 26, 36, 0.4);
}

.modal {
  position: relative;
  width: min(420px, 100%);
  max-height: min(80vh, 640px);
  overflow: auto;
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 28px 70px rgba(116, 71, 39, 0.12);
}

.modal h2 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 700;
  font-style: normal;
  font-synthesis: none;
}

.modal .d {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.6;
  color: #697386;
  font-weight: 500;
}

.modal label[for],
.modal > label:not(.check) {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #a9b0bc;
  margin-bottom: 6px;
}

.modal select {
  width: 100%;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(219, 205, 194, 0.55);
  padding: 0 12px;
  margin-bottom: 12px;
  background: #fff;
  font-size: 14px;
  font-family: inherit;
  font-style: normal;
  font-synthesis: none;
  color: inherit;
}

.hint {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.55;
  color: #697386;
  font-weight: 500;
}

.check-list {
  max-height: 240px;
  overflow: auto;
}

.check {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid rgba(219, 205, 194, 0.55);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.check input {
  margin-top: 3px;
  flex-shrink: 0;
}

.check strong {
  display: block;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  color: #171a24;
}

.check small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: #169b68;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  background: none;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  font-style: normal;
  font-synthesis: none;
  cursor: pointer;
  color: inherit;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  color: #697386;
}

.btn-ghost:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.04);
  color: #343a49;
}

.btn-primary {
  background: linear-gradient(135deg, #f04b18, #ff7a45);
  color: #fff;
  box-shadow: 0 8px 18px rgba(240, 75, 24, 0.22);
}

.btn-primary:hover:not(:disabled) {
  filter: brightness(1.03);
}
</style>
