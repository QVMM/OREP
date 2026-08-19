<template>
  <div class="camp-overview-panel">
    <div v-if="loading" class="teacher-card teacher-empty">正在加载概览…</div>
    <template v-else-if="data.hasCamp">
      <section class="teacher-stat-row" aria-label="训练营关键指标">
        <div class="teacher-card teacher-stat">
          <span>今日提交</span>
          <strong>{{ today?.submittedCount || 0 }}/{{ data.memberCount || 0 }}</strong>
        </div>
        <div class="teacher-card teacher-stat">
          <span>待批改</span>
          <strong class="is-accent">{{ data.pendingReviews || 0 }}</strong>
        </div>
        <div class="teacher-card teacher-stat">
          <span>风险学生</span>
          <strong>{{ riskCount }}</strong>
        </div>
        <div class="teacher-card teacher-stat">
          <span>当前天</span>
          <strong>第 {{ camp.currentDay || 0 }} 天</strong>
        </div>
      </section>

      <section class="teacher-card">
        <div class="teacher-card__head">
          <h2>近几日任务</h2>
          <button type="button" class="teacher-link text-button" @click="$emit('goto-plan')">
            去计划编排 ›
          </button>
        </div>
        <div class="teacher-card__body" style="padding-top: 8px">
          <div class="teacher-table-wrap">
            <table class="teacher-table">
              <thead>
                <tr>
                  <th>天</th>
                  <th>日期</th>
                  <th>任务</th>
                  <th>提交</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in visibleDays" :key="d.dayNo">
                  <td>第 {{ d.dayNo }} 天</td>
                  <td>{{ formatDate(d.trainingDate) }}</td>
                  <td>{{ d.title || '—' }}</td>
                  <td>{{ d.submittedCount || 0 }}/{{ data.memberCount || 0 }}</td>
                  <td>
                    <span
                      class="teacher-tag"
                      :class="
                        d.pendingCount
                          ? 'is-warn'
                          : Number(d.submittedCount) >= Number(data.memberCount) && Number(data.memberCount) > 0
                            ? 'is-ok'
                            : ''
                      "
                    >
                      {{ statusLabel(d) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!visibleDays.length" class="teacher-empty">暂无近几日数据</div>
        </div>
      </section>

    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { fetchTeacherCamp } from '../../api'
import { useTeacherContextStore } from '../../stores/context'

const props = defineProps({
  campIdProp: { type: [String, Number], default: '' },
})

defineEmits(['goto-plan', 'open-schedule', 'open-delete'])

const ctx = useTeacherContextStore()
const loading = ref(true)
const data = ref({ hasCamp: false, days: [], progress: [], memberCount: 0, pendingReviews: 0, camp: {} })

const camp = computed(() => data.value.camp || {})
const today = computed(() =>
  (data.value.days || []).find((d) => Number(d.dayNo) === Number(camp.value.currentDay))
)
const visibleDays = computed(() => {
  const day = Number(camp.value.currentDay || 1)
  return (data.value.days || []).filter((d) => Math.abs(Number(d.dayNo) - day) <= 3)
})
const riskCount = computed(() =>
  (data.value.progress || []).filter((m) =>
    (m.days || []).some(
      (d) =>
        ['EXPIRED', 'NOT_SUBMITTED'].includes(d.status) && new Date(d.trainingDate) <= new Date()
    )
  ).length
)

function formatDate(value) {
  return value ? String(value).slice(5).replace('-', '/') : '—'
}

function statusLabel(day) {
  if (Number(day.pendingCount) > 0) return '批改中'
  if (Number(day.submittedCount) >= Number(data.value.memberCount) && Number(data.value.memberCount) > 0) {
    return '已提交'
  }
  if (Number(day.dayNo) === Number(camp.value.currentDay)) return '进行中'
  return Number(day.dayNo) < Number(camp.value.currentDay) ? '有缺交' : '未开始'
}

async function load() {
  loading.value = true
  try {
    const campId = props.campIdProp || ctx.campId || ''
    data.value = await fetchTeacherCamp(campId)
  } catch {
    data.value = { hasCamp: false, days: [], progress: [], memberCount: 0, pendingReviews: 0, camp: {} }
  } finally {
    loading.value = false
  }
}

watch(() => [props.campIdProp, ctx.campId], load, { immediate: true })
</script>

<style scoped>
.text-button {
  border: 0;
  background: none;
  cursor: pointer;
  font: inherit;
}
</style>
