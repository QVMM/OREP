<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="student-preview-mask"
      role="presentation"
      @click.self="close"
      @keydown.esc.prevent="close"
    >
      <!-- 无传统对话框边框：仅悬浮关闭 + 预览舞台 -->
      <button type="button" class="student-preview-close" aria-label="关闭预览" @click="close">
        ×
      </button>

      <div
        class="student-preview-stage"
        role="dialog"
        aria-modal="true"
        aria-labelledby="studentPreviewTitle"
        tabindex="-1"
        ref="stageRef"
      >
        <div class="student-preview-chrome">
          <span class="student-preview-pill">学生视角 · 预览</span>
          <span class="student-preview-chrome__meta">不会提交真实数据 · 按当前编辑内容即时渲染</span>
        </div>

        <header class="sp-page-head">
          <div>
            <h1 id="studentPreviewTitle">任务详情</h1>
            <p>
              {{ projectName }}
              <template v-if="campName && campName !== projectName"> · {{ campName }}</template>
              · 训练第 {{ dayNo }} 天
            </p>
          </div>
          <div class="sp-due">
            <span>截止时间</span>
            <strong>{{ dueLabel }}</strong>
          </div>
        </header>

        <nav class="sp-flow" :class="{ 'has-learning': learningItems.length }" aria-label="今日训练流程">
          <template v-if="learningItems.length">
            <div class="is-active">
              <span>01</span>
              <div>
                <strong>今日学习</strong>
                <small>{{ learningItems.length }} 项资料</small>
              </div>
            </div>
            <i class="sp-flow__line" aria-hidden="true" />
          </template>
          <div class="is-active">
            <span>{{ learningItems.length ? '02' : '01' }}</span>
            <div>
              <strong>今日任务</strong>
              <small>任务书与交付要求</small>
            </div>
          </div>
          <i class="sp-flow__line" aria-hidden="true" />
          <div>
            <span>{{ learningItems.length ? '03' : '02' }}</span>
            <div>
              <strong>成果提交</strong>
              <small>预览态不可提交</small>
            </div>
          </div>
        </nav>

        <div class="sp-layout">
          <main class="sp-main">
            <!-- 学习资料 -->
            <section v-if="learningItems.length" class="sp-card">
              <header class="sp-card__head">
                <span class="sp-step">{{ learningItems.length ? '01' : '' }}</span>
                <div>
                  <small>今日学习</small>
                  <h2>学习内容</h2>
                </div>
              </header>
              <ul class="sp-learn-list">
                <li v-for="item in learningItems" :key="item.id || item.title">
                  <em>{{ typeLabel(item) }}</em>
                  <div>
                    <strong>{{ item.title || '未命名资料' }}</strong>
                    <small>
                      {{ item.required === false || item.required === 0 ? '选学' : '必学' }}
                      <template v-if="item.fileName"> · {{ item.fileName }}</template>
                    </small>
                  </div>
                </li>
              </ul>
            </section>

            <!-- 任务书 -->
            <section class="sp-card">
              <header class="sp-card__head">
                <span class="sp-step">{{ learningItems.length ? '02' : '01' }}</span>
                <div>
                  <small>今日任务</small>
                  <h2>任务书</h2>
                </div>
              </header>

              <div class="sp-task-title">
                <span>任务主题</span>
                <h3>{{ title || `第 ${dayNo} 天训练` }}</h3>
              </div>

              <section class="sp-section">
                <h4>任务概要</h4>
                <p>{{ summary || '按照交付要求完成今天的训练，并提交可检查的成果。' }}</p>
              </section>

              <section class="sp-section">
                <h4>正式任务描述</h4>
                <div
                  v-if="safeHtml"
                  class="sp-rich"
                  v-html="safeHtml"
                />
                <div v-else class="sp-empty">老师暂未填写正式任务描述。</div>
              </section>

              <section class="sp-section">
                <h4>交付要求</h4>
                <div v-if="taskItems.length" class="sp-reqs">
                  <article
                    v-for="(task, index) in taskItems"
                    :key="task.key || index"
                    :class="{
                      'is-optional': task.required === false,
                      'is-daily-report': isDailyReportTask(task),
                      'is-typing-practice': isTypingPracticeTask(task)
                    }"
                  >
                    <span class="sp-reqs__dot" :class="{ 'is-optional': task.required === false }" />
                    <div>
                      <strong>
                        {{ task.title || `任务 ${index + 1}` }}
                        <i>{{ task.required === false ? '选交' : '必交' }}</i>
                        <em v-if="isDailyReportTask(task)" class="sp-reqs__badge">日报</em>
                        <em v-else-if="isTypingPracticeTask(task)" class="sp-reqs__badge sp-reqs__badge--typing">打字</em>
                      </strong>
                      <p v-if="task.description">{{ task.description }}</p>
                      <small v-if="isDailyReportTask(task)">学生端显示「去写今日日报」入口</small>
                      <small v-else-if="isTypingPracticeTask(task)">学生端显示「去打字练习」入口</small>
                      <small v-else-if="task.formats?.length">支持格式：{{ task.formats.join('、') }}</small>
                      <button
                        v-if="isDailyReportTask(task)"
                        type="button"
                        class="sp-reqs__cta"
                        disabled
                      >
                        去写今日日报
                      </button>
                      <button
                        v-else-if="isTypingPracticeTask(task)"
                        type="button"
                        class="sp-reqs__cta sp-reqs__cta--typing"
                        disabled
                      >
                        去打字练习
                      </button>
                    </div>
                  </article>
                </div>
                <div v-else class="sp-empty">老师暂未拆分交付清单，请按任务说明提交成果。</div>
              </section>
            </section>
          </main>

          <aside class="sp-side">
            <section class="sp-card sp-submit-card">
              <header class="sp-card__head">
                <span class="sp-step">{{ learningItems.length ? '03' : '02' }}</span>
                <div>
                  <h2>提交成果</h2>
                  <p>完成任务书要求后提交可检查成果</p>
                </div>
              </header>
              <div class="sp-submit-meta">
                <span>截止时间</span>
                <strong>{{ dueLabel }}</strong>
              </div>
              <div class="sp-banner">
                <strong>预览模式</strong>
                <p>此处为学生端提交入口示意，预览不会实际上传或提交。</p>
              </div>
              <button type="button" class="sp-fake-btn" disabled>提交成果</button>
            </section>
          </aside>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { withAuthMediaHtml } from '../../utils/mediaUrl'

const props = defineProps({
  open: { type: Boolean, default: false },
  dayNo: { type: [Number, String], default: 1 },
  title: { type: String, default: '' },
  summary: { type: String, default: '' },
  contentHtml: { type: String, default: '' },
  deadline: { type: String, default: '22:00' },
  trainingDate: { type: String, default: '' },
  projectName: { type: String, default: '' },
  campName: { type: String, default: '' },
  learningResources: { type: Array, default: () => [] },
  tasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:open', 'close'])

const stageRef = ref(null)

const learningItems = computed(() => (props.learningResources || []).filter(Boolean))
const taskItems = computed(() =>
  (props.tasks || []).filter((t) => t && (String(t.title || '').trim() || String(t.description || '').trim()))
)

const dueLabel = computed(() => {
  const date = props.trainingDate ? String(props.trainingDate).slice(0, 10) : ''
  const time = props.deadline || '22:00'
  return date ? `${date} ${time}` : time
})

/** 教师自有内容预览：去掉 script / 事件属性，避免误注入 */
const safeHtml = computed(() => sanitizePreviewHtml(props.contentHtml))

function sanitizePreviewHtml(html) {
  if (!html || !String(html).trim()) return ''
  let out = String(html)
  out = out.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
  out = out.replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
  out = out.replace(/javascript:/gi, '')
  return withAuthMediaHtml(out.trim())
}

function typeLabel(item) {
  const t = String(item?.resourceType || item?.type || '').toUpperCase()
  if (t === 'VIDEO' || t === '视频' || t === 'EMBED_VIDEO') return '视频'
  if (t === 'LINK' || t === '链接') return '链接'
  if (t === 'DOCUMENT' || t === '文档') return '文档'
  return '资料'
}

function isDailyReportTask(task = {}) {
  const asset = String(task.assetType || task.asset_type || '').toUpperCase()
  if (asset === 'DAILY_REPORT') return true
  return /日报/.test(String(task.title || ''))
}

function isTypingPracticeTask(task = {}) {
  const asset = String(task.assetType || task.asset_type || '').toUpperCase()
  if (asset === 'TYPING_PRACTICE') return true
  return /打字练习|打字任务/.test(String(task.title || ''))
}

function close() {
  emit('update:open', false)
  emit('close')
}

watch(
  () => props.open,
  async (v) => {
    if (typeof document === 'undefined') return
    document.body.style.overflow = v ? 'hidden' : ''
    if (v) {
      await nextTick()
      stageRef.value?.focus?.()
    }
  }
)
</script>

<style scoped>
.student-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 28px 20px 36px;
  background: rgba(16, 18, 24, 0.52);
  /* 不用 blur：全屏实色遮罩更干净 */
  overflow: auto;
}

.student-preview-close {
  position: fixed;
  top: 18px;
  right: 20px;
  z-index: 1201;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: #30343a;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
}
.student-preview-close:hover {
  background: #fff;
}

/* 无对话框边框：整页舞台直接铺在遮罩上 */
.student-preview-stage {
  width: min(1120px, 100%);
  max-height: min(92vh, 960px);
  overflow: auto;
  border: 0;
  border-radius: 18px;
  outline: none;
  background: #f3f4f6;
  box-shadow: 0 28px 80px rgba(10, 12, 18, 0.28);
  padding: 18px 20px 28px;
}

.student-preview-chrome {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.student-preview-pill {
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: #12141a;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}
.student-preview-chrome__meta {
  color: #6b7280;
  font-size: 12px;
}

.sp-page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}
.sp-page-head h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #12141a;
}
.sp-page-head p {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 13px;
}
.sp-due {
  flex: none;
  min-width: 140px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #fff;
  text-align: right;
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.04);
}
.sp-due span {
  display: block;
  color: #8b919a;
  font-size: 11px;
  font-weight: 700;
}
.sp-due strong {
  display: block;
  margin-top: 4px;
  font-size: 14px;
  color: #12141a;
}

.sp-flow {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  gap: 8px;
  align-items: center;
  margin-bottom: 14px;
  padding: 12px;
  border-radius: 14px;
  background: #fff;
}
.sp-flow:not(.has-learning) {
  grid-template-columns: 1fr auto 1fr;
}
.sp-flow > div {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-width: 0;
}
.sp-flow > div > span {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: #eceef0;
  color: #5f656d;
  font-size: 12px;
  font-weight: 800;
}
.sp-flow > div.is-active > span {
  background: #12141a;
  color: #fff;
}
.sp-flow strong {
  display: block;
  font-size: 13px;
  color: #12141a;
}
.sp-flow small {
  display: block;
  margin-top: 2px;
  color: #8b919a;
  font-size: 11px;
}
.sp-flow__line {
  height: 1px;
  background: #e5e7eb;
}

.sp-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.55fr);
  gap: 14px;
  align-items: start;
}
.sp-main {
  display: grid;
  gap: 14px;
  min-width: 0;
}
.sp-side {
  min-width: 0;
}

.sp-card {
  border-radius: 14px;
  background: #fff;
  padding: 16px 18px 18px;
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.04);
}
.sp-card__head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}
.sp-card__head h2 {
  margin: 0;
  font-size: 16px;
  color: #12141a;
}
.sp-card__head small {
  display: block;
  margin-bottom: 2px;
  color: #8b919a;
  font-size: 11px;
  font-weight: 700;
}
.sp-card__head p {
  margin: 4px 0 0;
  color: #8b919a;
  font-size: 12px;
}
.sp-step {
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: #12141a;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.sp-learn-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.sp-learn-list li {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 10px;
  border-radius: 12px;
  background: #f7f8f9;
}
.sp-learn-list em {
  font-style: normal;
  height: 34px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  background: #fff0ea;
  color: #c2410c;
  font-size: 11px;
  font-weight: 800;
}
.sp-learn-list strong {
  display: block;
  font-size: 13px;
  color: #12141a;
}
.sp-learn-list small {
  display: block;
  margin-top: 3px;
  color: #8b919a;
  font-size: 11px;
}

.sp-task-title {
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid #eef0f2;
}
.sp-task-title span {
  display: block;
  color: #8b919a;
  font-size: 11px;
  font-weight: 700;
}
.sp-task-title h3 {
  margin: 6px 0 0;
  font-size: 20px;
  line-height: 1.35;
  color: #12141a;
}

.sp-section {
  margin-top: 16px;
}
.sp-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #4b515a;
}
.sp-section > p {
  margin: 0;
  color: #30343a;
  font-size: 14px;
  line-height: 1.65;
}

.sp-rich {
  color: #1f2329;
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.sp-rich :deep(h1),
.sp-rich :deep(h2),
.sp-rich :deep(h3) {
  margin: 0.8em 0 0.4em;
  line-height: 1.35;
  color: #12141a;
}
.sp-rich :deep(h1) { font-size: 1.35em; }
.sp-rich :deep(h2) { font-size: 1.2em; }
.sp-rich :deep(h3) { font-size: 1.08em; }
.sp-rich :deep(p) {
  margin: 0 0 0.75em;
}
.sp-rich :deep(ul),
.sp-rich :deep(ol) {
  margin: 0 0 0.75em;
  padding-left: 1.35em;
}
.sp-rich :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 10px;
  margin: 8px 0;
}
.sp-rich :deep(blockquote) {
  margin: 0 0 0.75em;
  padding: 8px 12px;
  border-left: 3px solid #d1d5db;
  background: #f7f8f9;
  color: #4b515a;
}
.sp-rich :deep(a) {
  color: #c2410c;
}

.sp-empty {
  padding: 14px;
  border-radius: 10px;
  background: #f7f8f9;
  color: #8b919a;
  font-size: 13px;
}

.sp-reqs {
  display: grid;
  gap: 8px;
}
.sp-reqs article {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: #f7f8f9;
}
.sp-reqs__dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: #12141a;
}
.sp-reqs__dot.is-optional {
  background: #9ca3af;
}
.sp-reqs strong {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #12141a;
}
.sp-reqs strong i {
  font-style: normal;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: #e8eaed;
  color: #5f656d;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}
.sp-reqs p {
  margin: 5px 0 0;
  color: #4b515a;
  font-size: 13px;
  line-height: 1.5;
}
.sp-reqs small {
  display: block;
  margin-top: 6px;
  color: #8b919a;
  font-size: 11px;
}
.sp-reqs article.is-daily-report {
  background: #fff7ed;
  border: 1px solid rgba(232, 74, 28, 0.2);
}
.sp-reqs article.is-typing-practice {
  background: #f0fdfa;
  border: 1px solid rgba(15, 118, 110, 0.22);
}
.sp-reqs__badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: #e84a1c;
  color: #fff;
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}
.sp-reqs__badge--typing {
  background: #0f766e;
}
.sp-reqs__cta {
  margin-top: 8px;
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: #e84a1c;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  opacity: 0.85;
  cursor: default;
}
.sp-reqs__cta--typing {
  background: #0f766e;
}

.sp-submit-card {
  position: sticky;
  top: 0;
}
.sp-submit-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eef0f2;
}
.sp-submit-meta span {
  color: #8b919a;
  font-size: 12px;
}
.sp-submit-meta strong {
  font-size: 14px;
  color: #12141a;
}
.sp-banner {
  padding: 12px;
  border-radius: 12px;
  background: #fff8f5;
  border: 1px dashed rgba(232, 74, 28, 0.28);
  margin-bottom: 12px;
}
.sp-banner strong {
  display: block;
  font-size: 13px;
  color: #c2410c;
}
.sp-banner p {
  margin: 4px 0 0;
  color: #7c2d12;
  font-size: 12px;
  line-height: 1.5;
}
.sp-fake-btn {
  width: 100%;
  min-height: 42px;
  border: 0;
  border-radius: 11px;
  background: #d1d5db;
  color: #6b7280;
  font-size: 14px;
  font-weight: 700;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .sp-layout {
    grid-template-columns: 1fr;
  }
  .sp-submit-card {
    position: static;
  }
  .sp-flow {
    grid-template-columns: 1fr;
  }
  .sp-flow__line {
    display: none;
  }
  .sp-page-head {
    flex-direction: column;
    align-items: stretch;
  }
  .sp-due {
    text-align: left;
  }
}
</style>
