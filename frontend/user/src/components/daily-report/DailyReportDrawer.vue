<template>
  <Teleport to="body">
    <Transition name="dr-fade">
      <div
        v-if="open"
        class="dr-overlay"
        role="presentation"
        @click.self="close"
      >
        <aside
          class="dr-drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="dr-title"
          @keydown.esc="close"
        >
          <header class="dr-drawer__head">
            <div>
              <p class="dr-kicker">备赛收工</p>
              <h2 id="dr-title">今日日报</h2>
              <p class="dr-sub">{{ dateLabel }} · {{ contextHint }}</p>
            </div>
            <button type="button" class="dr-icon-btn" aria-label="关闭" @click="close">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
            </button>
          </header>

          <div v-if="loading" class="dr-body dr-muted">加载中…</div>
          <div v-else class="dr-body">
            <p v-if="status === 'SUBMITTED'" class="dr-status is-ok">今日已提交，仍可修改后再次保存</p>
            <p v-else class="dr-status">约 2～3 分钟填完，提交后红点会消失</p>

            <label class="dr-field">
              <span>今天做了什么 <em>必填</em></span>
              <textarea
                v-model="form.contentDone"
                rows="4"
                :placeholder="placeholderDone"
                maxlength="2000"
              />
            </label>

            <label class="dr-field">
              <span>卡点 / 需要帮助 <em class="opt">选填</em></span>
              <textarea
                v-model="form.contentBlocker"
                rows="2"
                placeholder="没有就写「无」或留空"
                maxlength="1000"
              />
            </label>

            <label class="dr-field">
              <span>明天计划 <em>必填</em></span>
              <textarea
                v-model="form.contentNext"
                rows="2"
                :placeholder="placeholderNext"
                maxlength="1000"
              />
            </label>

            <p v-if="error" class="dr-error" role="alert">{{ error }}</p>
          </div>

          <footer class="dr-footer">
            <button type="button" class="dr-btn dr-btn--ghost" :disabled="saving" @click="saveDraft">
              存草稿
            </button>
            <button type="button" class="dr-btn dr-btn--primary" :disabled="saving" @click="submit">
              {{ saving ? '提交中…' : '提交日报' }}
            </button>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { fetchDailyReportToday, saveDailyReport } from '../../services/dailyReportClient'

const props = defineProps({
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'saved'])

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const status = ref('DRAFT')
const contextType = ref('FREE')
const reportDate = ref('')

const form = reactive({
  contentDone: '',
  contentBlocker: '',
  contentNext: '',
})

const dateLabel = computed(() => {
  const d = reportDate.value ? new Date(`${reportDate.value}T00:00:00`) : new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const week = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `${mm}月${dd}日 · 周${week}`
})

const contextHint = computed(() => {
  if (contextType.value === 'CAMP') return '结合今日训练与备赛进展'
  if (contextType.value === 'ROADSHOW') return '可写路演练习、改稿、演示情况'
  return '记录今天的备赛推进即可'
})

const placeholderDone = computed(() => {
  if (contextType.value === 'ROADSHOW') return '例如：路演练了 3 遍，改了开场与第 2 页数据…'
  if (contextType.value === 'CAMP') return '例如：完成第 N 天训练任务，看完材料并提交成果…'
  return '用几句话写下今天做了什么'
})

const placeholderNext = computed(() => {
  if (contextType.value === 'ROADSHOW') return '例如：明天精修讲稿后半段，再完整彩排一次'
  return '明天最想推进的一件事'
})

watch(() => props.open, async (v) => {
  if (!v) return
  error.value = ''
  loading.value = true
  try {
    const data = await fetchDailyReportToday()
    reportDate.value = data?.reportDate || new Date().toISOString().slice(0, 10)
    contextType.value = data?.contextType || 'FREE'
    const r = data?.report
    if (r) {
      form.contentDone = r.contentDone || ''
      form.contentBlocker = r.contentBlocker || ''
      form.contentNext = r.contentNext || ''
      status.value = r.status || 'DRAFT'
    } else {
      form.contentDone = ''
      form.contentBlocker = ''
      form.contentNext = ''
      status.value = 'DRAFT'
    }
  } catch (e) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
})

function close() {
  emit('close')
}

async function saveDraft() {
  await persist(false)
}

async function submit() {
  await persist(true)
}

async function persist(submitFlag) {
  error.value = ''
  if (submitFlag) {
    if (!form.contentDone.trim()) {
      error.value = '请填写「今天做了什么」'
      return
    }
    if (!form.contentNext.trim()) {
      error.value = '请填写「明天计划」'
      return
    }
  }
  saving.value = true
  try {
    const saved = await saveDailyReport({
      reportDate: reportDate.value,
      contentDone: form.contentDone,
      contentBlocker: form.contentBlocker,
      contentNext: form.contentNext,
      submit: submitFlag,
    })
    status.value = saved?.status || (submitFlag ? 'SUBMITTED' : 'DRAFT')
    emit('saved', saved)
    if (submitFlag) close()
  } catch (e) {
    error.value = e?.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.dr-overlay {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-fixed, 1000) + 40);
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(2px);
}

.dr-drawer {
  width: min(420px, 100vw);
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  box-shadow: -12px 0 40px rgba(15, 23, 42, 0.12);
}

.dr-drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid var(--ds-line, #eceff3);
}

.dr-kicker {
  margin: 0 0 4px;
  color: var(--ds-orange-700, #c2410c);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.06em;
}

.dr-drawer__head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
}

.dr-sub {
  margin: 4px 0 0;
  color: var(--ds-muted, #6b7280);
  font-size: 12px;
}

.dr-icon-btn {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--ds-ink-2);
  cursor: pointer;
}

.dr-icon-btn svg {
  width: 18px;
  height: 18px;
}

.dr-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 18px 12px;
  display: grid;
  gap: 14px;
  align-content: start;
}

.dr-muted { color: var(--ds-muted); font-size: 13px; }

.dr-status {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.45;
}

.dr-status.is-ok {
  background: #ecfdf5;
  color: #047857;
}

.dr-field {
  display: grid;
  gap: 6px;
}

.dr-field > span {
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-ink-2);
}

.dr-field em {
  color: var(--ds-orange-700, #c2410c);
  font-style: normal;
  font-weight: 650;
  margin-left: 4px;
}

.dr-field em.opt {
  color: var(--ds-muted);
  font-weight: 600;
}

.dr-field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--ds-line, #e5e7eb);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  font-size: 14px;
  line-height: 1.55;
  resize: vertical;
  min-height: 72px;
}

.dr-field textarea:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--ds-orange-400, #fb923c) 55%, var(--ds-line));
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.dr-error {
  margin: 0;
  color: #b91c1c;
  font-size: 12px;
}

.dr-footer {
  display: flex;
  gap: 10px;
  padding: 12px 18px 18px;
  border-top: 1px solid var(--ds-line, #eceff3);
}

.dr-btn {
  flex: 1;
  min-height: 44px;
  border-radius: 999px;
  border: 0;
  font: inherit;
  font-size: 14px;
  font-weight: 750;
  cursor: pointer;
}

.dr-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.dr-btn--ghost {
  background: #f3f4f6;
  color: var(--ds-ink-2);
}

.dr-btn--primary {
  background: var(--ds-orange-600, #ea580c);
  color: #fff;
}

.dr-fade-enter-active,
.dr-fade-leave-active {
  transition: opacity 0.18s ease;
}

.dr-fade-enter-active .dr-drawer,
.dr-fade-leave-active .dr-drawer {
  transition: transform 0.2s ease;
}

.dr-fade-enter-from,
.dr-fade-leave-to {
  opacity: 0;
}

.dr-fade-enter-from .dr-drawer,
.dr-fade-leave-to .dr-drawer {
  transform: translateX(12px);
}
</style>
