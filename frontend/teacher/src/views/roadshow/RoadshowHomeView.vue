<template>
  <div class="teacher-page roadshow-home">
    <header class="teacher-page__head">
      <div>
        <h1>路演场次</h1>
        <p>
          {{
            activeTab === 'recordings'
              ? '会议录制与评分视频统一回放，不重复存储'
              : '一场路演在同一页完成：时间、名单、进会、结束后回看'
          }}
          <span v-if="activeTab === 'sessions' && sourceLabel" class="teacher-muted"> · {{ sourceLabel }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button
          v-if="activeTab === 'sessions'"
          type="button"
          class="teacher-btn teacher-btn--secondary"
          :disabled="loading"
          @click="load"
        >
          刷新
        </button>
        <button
          v-if="activeTab === 'sessions'"
          type="button"
          class="teacher-btn teacher-btn--primary"
          @click="creating = true"
        >
          创建场次
        </button>
      </div>
    </header>

    <div class="roadshow-tabs" role="tablist" aria-label="路演场次分区">
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'sessions'"
        :class="{ 'is-active': activeTab === 'sessions' }"
        @click="setTab('sessions')"
      >
        场次列表
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="activeTab === 'recordings'"
        :class="{ 'is-active': activeTab === 'recordings' }"
        @click="setTab('recordings')"
      >
        录制回放
      </button>
    </div>

    <!-- 场次列表（原功能不变） -->
    <template v-if="activeTab === 'sessions'">
      <p v-if="error" class="teacher-tag is-warn" style="margin-bottom: 12px">{{ error }}</p>
      <p v-if="msg" class="teacher-tag is-ok" style="margin-bottom: 12px">{{ msg }}</p>

      <section class="teacher-card">
        <div class="teacher-card__body" style="padding-top: 8px">
          <div v-if="loading" class="teacher-empty">加载会议列表…</div>
          <table v-else class="teacher-table">
            <thead>
              <tr>
                <th>场次</th>
                <th>会议号</th>
                <th>状态</th>
                <th>时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in sessions" :key="s.id">
                <td>{{ s.title }}</td>
                <td>{{ s.code || s.meetingCode || '—' }}</td>
                <td>
                  <span class="teacher-tag" :class="statusClass(s.status)">{{ statusLabel(s.status) }}</span>
                </td>
                <td>{{ formatTime(s) }}</td>
                <td style="display: flex; gap: 6px; flex-wrap: wrap">
                  <a
                    class="teacher-btn teacher-btn--primary teacher-btn--sm"
                    :href="studentMeetingUrl(s.id)"
                    target="_blank"
                    rel="noopener"
                  >进会</a>
                  <button
                    type="button"
                    class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                    @click="setTab('recordings')"
                  >回放</button>
                </td>
              </tr>
              <tr v-if="!sessions.length">
                <td colspan="5" class="teacher-empty">暂无场次，点击右上角创建</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <!-- 录制回放子页：不改变回放组件自身逻辑 -->
    <RoadshowRecordingsView
      v-else
      embedded
      @switch-tab="setTab"
    />

    <Teleport to="body">
      <div
        v-if="creating"
        class="drawer-mask teacher-overlay-mask"
        role="presentation"
        @click.self="creating = false"
      >
        <aside class="drawer" role="dialog" aria-modal="true" aria-label="创建路演场次">
          <h2 style="margin: 0 0 12px; font-size: 18px">创建路演场次</h2>
          <label class="field"><span>名称</span><input v-model="form.title" placeholder="例如：周五彩排场" /></label>
          <label class="field"><span>时长（分钟）</span><input v-model.number="form.durationMinutes" type="number" min="15" step="15" /></label>
          <p v-if="createError" class="teacher-tag is-warn">{{ createError }}</p>
          <div style="display: flex; gap: 8px; margin-top: 8px">
            <button type="button" class="teacher-btn teacher-btn--primary" :disabled="saving" @click="create">
              {{ saving ? '创建中…' : '创建' }}
            </button>
            <button type="button" class="teacher-btn teacher-btn--secondary" @click="creating = false">取消</button>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createMeeting, fetchMeetings } from '../../api'
import { studentMeetingUrl as buildStudentMeetingUrl } from '../../utils/studentApp'
import RoadshowRecordingsView from './RoadshowRecordingsView.vue'

const route = useRoute()
const router = useRouter()

const sessions = ref([])
const loading = ref(false)
const saving = ref(false)
const creating = ref(false)
const error = ref('')
const createError = ref('')
const msg = ref('')
const sourceLabel = ref('')

const form = reactive({
  title: '',
  durationMinutes: 60,
})

const activeTab = computed(() => {
  const t = String(route.query.tab || 'sessions')
  return t === 'recordings' ? 'recordings' : 'sessions'
})

function setTab(tab) {
  const next = tab === 'recordings' ? 'recordings' : 'sessions'
  router.replace({
    path: '/roadshow',
    query: next === 'sessions' ? {} : { tab: next },
  })
}

function statusLabel(status) {
  const map = {
    CREATED: '未开始',
    RUNNING: '进行中',
    ENDED: '已结束',
    CANCELLED: '已取消',
    今日: '今日',
    已排期: '已排期',
  }
  if (map[status]) return map[status]
  if (/[\u4e00-\u9fff]/.test(String(status || ''))) return status
  return map[String(status || '').toUpperCase()] || '未知'
}

function statusClass(status) {
  if (status === 'RUNNING' || status === '今日') return 'is-warn'
  if (status === 'ENDED') return 'is-ok'
  return 'is-info'
}

function formatTime(s) {
  if (s.time && s.date) return `${s.date} ${s.time}`
  if (s.startTime) return String(s.startTime).replace('T', ' ').slice(0, 16)
  if (s.createdAt) return String(s.createdAt).replace('T', ' ').slice(0, 16)
  return '—'
}

function studentMeetingUrl(id) {
  return buildStudentMeetingUrl(id)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const list = await fetchMeetings()
    const rows = Array.isArray(list) ? list : list?.records || list?.list || []
    if (!rows.length) {
      sessions.value = []
      sourceLabel.value = '尚无真实路演场次'
      return
    }
    sessions.value = rows.map((m) => ({
      id: m.id,
      title: m.title || m.name || `会议 ${m.id}`,
      status: m.status,
      code: m.meetingCode || m.code || m.roomCode,
      startTime: m.startTime || m.scheduledStart || m.createdAt,
      createdAt: m.createdAt,
    }))
    sourceLabel.value = '已连接后端会议列表'
  } catch (e) {
    sessions.value = []
    sourceLabel.value = '路演数据加载失败'
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function create() {
  createError.value = ''
  saving.value = true
  try {
    await createMeeting({
      title: form.title || '路演场次',
      durationMinutes: form.durationMinutes || 60,
    })
    msg.value = '场次已创建'
    creating.value = false
    form.title = ''
    await load()
  } catch (e) {
    createError.value = e.message || '创建失败'
  } finally {
    saving.value = false
  }
}

watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'sessions' && !sessions.value.length && !loading.value) load()
  }
)

onMounted(() => {
  if (activeTab.value === 'sessions') load()
})
</script>

<style scoped>
.roadshow-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
  padding: 4px;
  width: fit-content;
  max-width: 100%;
  border-radius: 12px;
  background: #f3f4f6;
  border: 1px solid var(--ds-line);
}
.roadshow-tabs button {
  height: 36px;
  padding: 0 16px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  font: 700 13px var(--ds-font-sans);
  color: var(--ds-muted);
  cursor: pointer;
}
.roadshow-tabs button.is-active {
  background: #fff;
  color: var(--ds-ink);
  box-shadow: 0 1px 3px rgba(29, 29, 31, 0.08);
}

.drawer-mask {
  display: grid;
  justify-content: end;
}
.drawer {
  box-sizing: border-box;
  width: min(400px, 100vw);
  height: 100%;
  max-height: 100dvh;
  background: #fff;
  padding: 24px;
  display: grid;
  align-content: start;
  gap: 12px;
  box-shadow: -16px 0 48px rgba(0, 0, 0, 0.18);
  overflow: auto;
}
.field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.field input {
  border: 1px solid rgba(29, 29, 31, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  font-size: 14px;
  font-weight: 500;
}
</style>
