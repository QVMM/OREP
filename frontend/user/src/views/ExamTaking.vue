<template>
  <div class="take-page">
    <section v-if="attempt" class="take-shell">
      <header class="exam-topbar">
        <BaseButton type="text" size="small" class="back-link" @click="router.push('/exam-system')">‹ 返回考试系统</BaseButton>
        <div class="paper-title">
          <strong>{{ attempt.title }}</strong>
          <span>正式考试 · 题序随机 · 提交后不可修改</span>
        </div>
        <div class="status-cluster">
          <span class="save-state">答案已保存</span>
          <span class="timer-pill" :class="{ urgent: remainSeconds < 300 }">{{ remainText }}</span>
        </div>
      </header>

      <main v-if="!result" class="take-layout">
        <section class="question-stage">
          <header class="question-progress">
            <div class="progress-main">
              <strong>已完成 {{ answeredCount }} / {{ attempt.questions.length }} 题</strong>
              <span>第 {{ activeIndex + 1 }} 题正在作答，建议先完成选择题，再处理主观题。</span>
              <div class="progress-track"><i :style="{ width: progressPercent }"></i></div>
            </div>
            <div class="progress-mini">
              <div><span>已答</span><strong>{{ answeredCount }}</strong></div>
              <div><span>标记</span><strong>{{ markedCount }}</strong></div>
              <div><span>剩余</span><strong>{{ attempt.questions.length - answeredCount }}</strong></div>
            </div>
          </header>

          <section class="question-body">
            <div class="question-meta">
              <div class="question-meta-left">
                <span class="question-number">{{ String(activeIndex + 1).padStart(2, '0') }} / {{ String(attempt.questions.length).padStart(2, '0') }}</span>
                <span class="chip">{{ typeLabel(activeQuestion.questionType) }}</span>
                <span class="chip">{{ activeQuestion.score || 0 }} 分</span>
              </div>
              <button
                type="button"
                class="mark-btn"
                :class="{ active: isMarked(activeQuestion) }"
                @click="toggleMark(activeQuestion)"
              >
                {{ isMarked(activeQuestion) ? '已标记' : '标记此题' }}
              </button>
            </div>

            <h1>{{ activeQuestion.stem }}</h1>

            <div
              v-if="activeQuestion.material || activeQuestion.context || activeQuestion.description"
              class="question-material"
            >
              {{ activeQuestion.material || activeQuestion.context || activeQuestion.description }}
            </div>

            <div v-if="activeQuestion.questionType === 'single' || activeQuestion.questionType === 'judge'" class="option-stack">
              <button
                v-for="(option, optionIndex) in parseOptions(activeQuestion.optionsJson)"
                :key="option.key"
                type="button"
                :class="{ selected: answers[activeQuestion.id]?.[0] === option.key }"
                @click="answers[activeQuestion.id] = [option.key]"
              >
                <b>{{ optionDisplayKey(optionIndex) }}</b>
                <span>{{ option.text }}</span>
              </button>
            </div>

            <div v-else-if="activeQuestion.questionType === 'multiple'" class="option-stack">
              <button
                v-for="(option, optionIndex) in parseOptions(activeQuestion.optionsJson)"
                :key="option.key"
                type="button"
                :class="{ selected: answers[activeQuestion.id]?.includes(option.key) }"
                @click="toggleMulti(activeQuestion.id, option.key)"
              >
                <b>{{ optionDisplayKey(optionIndex) }}</b>
                <span>{{ option.text }}</span>
              </button>
            </div>

            <textarea
              v-else
              v-model="textAnswers[activeQuestion.id]"
              class="answer-text"
              :placeholder="activeQuestion.questionType === 'programming' ? '输入代码或函数名' : '输入答案'"
              :rows="activeQuestion.questionType === 'programming' ? 10 : 6"
            />
          </section>

          <footer class="question-footer">
            <div class="nav-side">
              <BaseButton type="secondary" :disabled="activeIndex === 0" @click="activeIndex--">上一题</BaseButton>
              <BaseButton type="secondary" @click="favorite(activeQuestion)">收藏题目</BaseButton>
            </div>
            <div class="nav-side">
              <BaseButton type="secondary" :disabled="activeIndex === attempt.questions.length - 1" @click="activeIndex++">下一题</BaseButton>
              <BaseButton @click="submitExam">检查并交卷</BaseButton>
            </div>
          </footer>
        </section>

        <aside class="answer-side">
          <section class="side-panel">
            <div class="side-head">
              <h2>答题卡</h2>
              <span>已答 {{ answeredCount }} · 标记 {{ markedCount }}</span>
            </div>
            <div class="answer-grid">
              <button
                v-for="(question, index) in attempt.questions"
                :key="question.id"
                type="button"
                :class="{ current: index === activeIndex, done: isAnswered(question), flag: isMarked(question) }"
                @click="activeIndex = index"
              >
                {{ index + 1 }}
              </button>
            </div>
            <div class="legend">
              <span><i class="now"></i>当前</span>
              <span><i class="done"></i>已答</span>
              <span><i class="flag"></i>标记</span>
              <span><i></i>未答</span>
            </div>
            <BaseButton class="side-submit" @click="submitExam">交卷</BaseButton>
          </section>

          <section class="side-panel">
            <div class="side-head">
              <h2>考试状态</h2>
            </div>
            <div class="side-list">
              <div class="side-row"><span>自动保存</span><strong>已开启</strong></div>
              <div class="side-row"><span>剩余时间</span><strong>{{ remainText }}</strong></div>
              <div class="side-row"><span>切屏记录</span><strong>{{ screenLeaveCount }} 次</strong></div>
              <div class="side-row"><span>主观题</span><strong>{{ subjectiveCount }} 题</strong></div>
            </div>
          </section>
        </aside>
      </main>

      <section v-else class="result-panel">
        <span class="result-kicker">考试结果</span>
        <h2>{{ result.score }} / {{ result.totalScore }}</h2>
        <p v-if="result.manualReviewRequired">
          本次测评包含 {{ result.manualQuestionCount }} 道编程题，已提交管理员人工评阅。
        </p>
        <p v-else>{{ result.passed ? '已通过本次测评' : '未达到及格线，请复盘错题' }}</p>
        <div class="result-actions">
          <BaseButton @click="router.push('/exam-system/wrong-book')">查看错题本</BaseButton>
          <BaseButton type="secondary" @click="router.push('/exam-system')">返回考试系统</BaseButton>
        </div>
        <div class="wrong-list">
          <article v-for="item in result.wrongQuestions" :key="item.questionId">
            <strong>{{ item.stem }}</strong>
            <small>正确答案：{{ answersToText(item.answerJson) }}</small>
            <p>{{ item.analysis }}</p>
          </article>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../utils/request'
import BaseButton from '../components/base/BaseButton.vue'

const route = useRoute()
const router = useRouter()
const attempt = ref(null)
const result = ref(null)
const activeIndex = ref(0)
const answers = ref({})
const textAnswers = ref({})
const remainSeconds = ref(0)
const screenLeaveCount = ref(0)
const markedQuestions = ref({})
let timer = null

const activeQuestion = computed(() => attempt.value?.questions?.[activeIndex.value] || {})
const answeredCount = computed(() => attempt.value?.questions?.filter(isAnswered).length || 0)
const markedCount = computed(() => attempt.value?.questions?.filter(isMarked).length || 0)
const subjectiveCount = computed(() => attempt.value?.questions?.filter(question => question.questionType === 'blank' || question.questionType === 'programming').length || 0)
const progressPercent = computed(() => {
  const total = attempt.value?.questions?.length || 0
  if (!total) return '0%'
  return `${Math.round((answeredCount.value / total) * 100)}%`
})
const remainText = computed(() => {
  const minutes = String(Math.floor(remainSeconds.value / 60)).padStart(2, '0')
  const seconds = String(remainSeconds.value % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
})

onMounted(async () => {
  await start()
  document.addEventListener('visibilitychange', reportLeave)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  document.removeEventListener('visibilitychange', reportLeave)
})

async function start() {
  const res = await request.post(`/api/exams/${route.params.paperId}/start`)
  attempt.value = res.data
  tick()
  timer = setInterval(tick, 1000)
}

function tick() {
  if (!attempt.value?.deadlineAt || result.value) return
  const deadline = new Date(attempt.value.deadlineAt).getTime()
  remainSeconds.value = Math.max(0, Math.floor((deadline - Date.now()) / 1000))
  if (remainSeconds.value === 0) submitExam(true)
}

function parseOptions(json) {
  try {
    return JSON.parse(json || '[]')
  } catch {
    return []
  }
}

function optionDisplayKey(index) {
  return String.fromCharCode(65 + index)
}

function toggleMulti(questionId, key) {
  const current = new Set(answers.value[questionId] || [])
  current.has(key) ? current.delete(key) : current.add(key)
  answers.value[questionId] = [...current]
}

function isAnswered(question) {
  if (question.questionType === 'blank' || question.questionType === 'programming') return !!textAnswers.value[question.id]
  return !!answers.value[question.id]?.length
}

function isMarked(question) {
  return !!markedQuestions.value[question?.id]
}

function toggleMark(question) {
  if (!question?.id) return
  markedQuestions.value[question.id] = !markedQuestions.value[question.id]
}

async function submitExam(auto = false) {
  if (!auto) await ElMessageBox.confirm('确认提交本次考试？提交后不可修改。', '交卷确认', { type: 'warning' })
  const payload = {}
  for (const question of attempt.value.questions) {
    if (question.questionType === 'blank' || question.questionType === 'programming') {
      payload[question.id] = JSON.stringify([textAnswers.value[question.id] || ''])
    } else {
      payload[question.id] = JSON.stringify(answers.value[question.id] || [])
    }
  }
  const res = await request.post(`/api/exams/attempts/${attempt.value.attemptId}/submit`, payload)
  result.value = res.data
  clearInterval(timer)
  if (auto) ElMessage.warning('考试时间已到，系统已自动交卷')
}

async function favorite(question) {
  await request.post(`/api/exams/questions/${question.id}/favorite`)
  ElMessage.success('收藏状态已更新')
}

async function reportLeave() {
  if (document.visibilityState !== 'hidden' || !attempt.value || result.value) return
  screenLeaveCount.value += 1
  await request.post(`/api/exams/attempts/${attempt.value.attemptId}/screen-leave`)
}

function answersToText(json) {
  try {
    return JSON.parse(json || '[]').join('、')
  } catch {
    return ''
  }
}

function typeLabel(type) {
  return {
    single: '单选题',
    multiple: '多选题',
    judge: '判断题',
    blank: '填空题',
    programming: '编程题'
  }[type] || type
}
</script>

<style scoped>
.take-page {
  min-height: 100vh;
  background-color: #ffffff;
  background-image: none;
  color: var(--orep-text-strong);
}

.take-shell {
  min-height: 100vh;
  display: grid;
  grid-template-rows: 68px minmax(0, 1fr);
}

.exam-topbar {
  position: sticky;
  top: 0;
  z-index: 12;
  border-bottom: 1px solid var(--orep-border-soft);
  background: oklch(0.997 0.005 55 / 0.92);
  backdrop-filter: blur(18px);
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto minmax(180px, 1fr);
  align-items: center;
  gap: 18px;
  padding: 0 var(--ds-space-6, 24px);
}

.back-link {
  justify-self: start;
  border: 0;
  background: transparent;
  color: var(--orep-muted);
  font: inherit;
  font-weight: 820;
  cursor: pointer;
}

.paper-title {
  min-width: 0;
  text-align: center;
}

.paper-title strong,
.paper-title span {
  display: block;
}

.paper-title strong {
  color: var(--orep-text-strong);
  font-size: 18px;
  line-height: 1.2;
}

.paper-title span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.status-cluster {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 10px;
}

.save-state,
.timer-pill {
  min-height: 36px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 13px;
  font-weight: 860;
  white-space: nowrap;
}

.save-state {
  border: 1px solid oklch(0.9 0.045 150);
  background: oklch(0.98 0.02 150);
  color: var(--orep-green);
  font-size: 12px;
}

.save-state::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--orep-green);
}

.timer-pill {
  border: 1px solid oklch(0.88 0.07 55);
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.timer-pill.urgent {
  border-color: oklch(0.72 0.16 35);
  background: oklch(0.96 0.045 35);
  color: oklch(0.55 0.18 35);
}

.take-layout {
  width: min(1500px, calc(100% - 56px));
  margin: 0 auto;
  padding: 22px 0 42px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 318px;
  gap: 20px;
  align-items: start;
}

.question-stage,
.side-panel,
.result-panel {
  border: 1px solid var(--orep-border-soft);
  border-radius: 22px;
  background: var(--orep-surface-raised);
  box-shadow: none;
}

.question-stage {
  min-height: calc(100vh - var(--header-height) - 132px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.question-progress {
  border-bottom: 1px solid var(--orep-border-soft);
  padding: 18px 24px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  background:
    radial-gradient(circle at 92% 0%, oklch(0.9 0.08 55 / 0.18), transparent 30%),
    linear-gradient(180deg, var(--orep-surface-raised), oklch(0.99 0.01 55));
}

.progress-main strong,
.progress-main span {
  display: block;
}

.progress-main strong {
  color: var(--orep-text-strong);
  font-size: 15px;
}

.progress-main span {
  margin-top: 5px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.progress-track {
  height: 7px;
  margin-top: 12px;
  border-radius: 999px;
  background: oklch(0.91 0.012 55);
  overflow: hidden;
}

.progress-track i {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: var(--ds-orange);
}

.progress-mini {
  display: flex;
  gap: 18px;
}

.progress-mini div {
  min-width: 58px;
  text-align: right;
}

.progress-mini span,
.progress-mini strong {
  display: block;
}

.progress-mini span {
  color: var(--orep-muted);
  font-size: 11px;
  font-weight: 800;
}

.progress-mini strong {
  margin-top: 4px;
  color: var(--orep-text-strong);
  font-size: 22px;
  line-height: 1;
}

.question-body {
  padding: 40px 52px 34px;
}

.question-meta,
.question-meta-left,
.question-footer,
.nav-side {
  display: flex;
  align-items: center;
  gap: 12px;
}

.question-meta,
.question-footer {
  justify-content: space-between;
}

.question-meta-left {
  flex-wrap: wrap;
}

.question-number {
  color: var(--orep-orange);
  font-size: 14px;
  font-weight: 920;
}

.chip {
  min-height: 26px;
  border-radius: 999px;
  background: oklch(0.96 0.01 55);
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 820;
}

.mark-btn {
  min-height: 34px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  background: var(--orep-surface-raised);
  color: var(--orep-muted);
  padding: 0 12px;
  font: inherit;
  font-weight: 860;
  cursor: pointer;
}

.mark-btn.active {
  border-color: oklch(0.86 0.07 55);
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
}

.question-body h1 {
  max-width: 920px;
  margin: 30px 0 20px;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.3;
  letter-spacing: 0;
}

.question-material {
  max-width: 920px;
  border-left: 4px solid var(--orep-orange);
  border-radius: 0 14px 14px 0;
  background: oklch(0.985 0.018 55);
  color: var(--orep-muted);
  padding: 14px 18px;
  font-size: 14px;
  line-height: 1.75;
}

.option-stack {
  max-width: 940px;
  margin-top: 28px;
  display: grid;
  gap: 14px;
}

.option-stack button {
  width: 100%;
  min-height: 72px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 16px;
  background: var(--orep-surface-raised);
  color: var(--orep-text-strong);
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  text-align: left;
  font: inherit;
  cursor: pointer;
  transition: background 160ms var(--orep-ease-out), border-color 160ms var(--orep-ease-out), transform 160ms var(--orep-ease-out);
}

.option-stack button:hover {
  border-color: oklch(0.84 0.07 55);
  background: oklch(0.99 0.014 55);
  transform: translateY(-1px);
}

.option-stack button.selected {
  border-color: var(--orep-orange);
  background: var(--orep-orange-wash);
}

.option-stack b {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: oklch(0.94 0.012 55);
  color: var(--orep-muted);
  display: grid;
  place-items: center;
  font-weight: 920;
}

.option-stack button.selected b {
  background: var(--orep-orange);
  color: white;
}

.option-stack span {
  color: var(--orep-text-strong);
  font-size: 16px;
  line-height: 1.55;
  font-weight: 760;
}

.answer-text {
  width: min(940px, 100%);
  min-height: 220px;
  margin-top: 28px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 16px;
  background: var(--orep-surface-raised);
  color: var(--orep-text-strong);
  outline: none;
  resize: vertical;
  padding: 18px;
  font: inherit;
  line-height: 1.8;
}

.answer-text:focus {
  border-color: var(--orep-orange);
  box-shadow: 0 0 0 4px oklch(0.78 0.13 60 / 0.1);
}

.question-footer {
  border-top: 1px solid var(--orep-border-soft);
  padding: 18px 24px;
  background: var(--orep-surface-raised);
  flex-wrap: wrap;
}

.outline-btn,
.primary-btn,
.result-actions button {
  min-height: 42px;
  border-radius: 11px;
  padding: 0 18px;
  font: inherit;
  font-weight: 880;
  cursor: pointer;
}

.outline-btn,
.result-actions button {
  border: 1px solid var(--orep-border-soft);
  background: var(--orep-surface-raised);
  color: var(--orep-text-strong);
}

.primary-btn {
  border: 1px solid var(--orep-text-strong);
  background: var(--orep-text-strong);
  color: var(--orep-surface-raised);
}

button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.answer-side {
  position: sticky;
  top: 90px;
  display: grid;
  gap: 14px;
}

.side-panel {
  padding: 18px;
  border-radius: 18px;
}

.side-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}

.side-head h2 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 20px;
}

.side-head span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 800;
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.answer-grid button {
  position: relative;
  aspect-ratio: 1;
  border: 1px solid var(--orep-border-soft);
  border-radius: 10px;
  background: var(--orep-surface-raised);
  color: var(--orep-muted);
  font: inherit;
  font-weight: 880;
  cursor: pointer;
}

.answer-grid button.done {
  border-color: var(--orep-orange);
  background: var(--orep-orange);
  color: white;
}

.answer-grid button.current {
  border-color: var(--orep-text-strong);
  box-shadow: 0 0 0 3px oklch(0.2 0.015 45 / 0.08);
  color: var(--orep-text-strong);
}

.answer-grid button.flag::after {
  content: "";
  position: absolute;
  top: 6px;
  right: 6px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: oklch(0.78 0.12 75);
}

.legend {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: oklch(0.91 0.012 55);
}

.legend .done {
  background: var(--orep-orange);
}

.legend .now {
  background: var(--orep-text-strong);
}

.legend .flag {
  background: oklch(0.78 0.12 75);
}

.submit-wide {
  width: 100%;
  min-height: 46px;
  margin-top: 16px;
  border: 1px solid var(--orep-text-strong);
  border-radius: 12px;
  background: var(--orep-text-strong);
  color: white;
  font: inherit;
  font-weight: 920;
  cursor: pointer;
}

.side-list {
  display: grid;
  gap: 12px;
}

.side-row {
  min-height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 760;
}

.side-row strong {
  color: var(--orep-text-strong);
}

.result-panel {
  width: min(1180px, calc(100% - 56px));
  margin: 22px auto 56px;
  padding: 28px;
}

.result-kicker {
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 900;
}

.result-panel h2 {
  margin: 12px 0 0;
  color: var(--orep-text-strong);
  font-size: 42px;
}

.result-panel p {
  color: var(--orep-muted);
  line-height: 1.8;
}

.result-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.wrong-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 24px;
}

.wrong-list article {
  border: 1px solid var(--orep-border-soft);
  border-radius: 14px;
  background: oklch(0.99 0.006 55);
  padding: 18px;
}

.wrong-list strong,
.wrong-list small {
  display: block;
}

.wrong-list small {
  margin-top: 8px;
  color: var(--orep-orange);
}

@media (max-width: 1100px) {
  .take-layout {
    grid-template-columns: 1fr;
  }

  .answer-side {
    position: static;
  }

  .question-stage {
    min-height: auto;
  }
}

@media (max-width: 760px) {
  .exam-topbar {
    position: static;
    grid-template-columns: 1fr;
    justify-items: start;
    min-height: auto;
    padding: 14px;
  }

  .paper-title {
    text-align: left;
  }

  .status-cluster {
    justify-self: start;
    flex-wrap: wrap;
  }

  .take-layout,
  .result-panel {
    width: calc(100% - 28px);
  }

  .question-progress {
    grid-template-columns: 1fr;
  }

  .progress-mini {
    justify-content: space-between;
  }

  .question-body {
    padding: 28px 20px;
  }

  .question-body h1 {
    font-size: 24px;
  }

  .question-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .wrong-list {
    grid-template-columns: 1fr;
  }
}

/* Compact answering typography: match practice page scale. */
.exam-topbar {
  min-height: 60px;
  padding: 0 var(--ds-space-6, 24px);
}

.back-link,
.save-state,
.outline-btn,
.primary-btn,
.result-actions button,
.submit-wide {
  font-size: 13px;
}

.paper-title strong {
  font-size: 16px;
}

.paper-title span {
  font-size: 11px;
}

.save-state,
.timer-pill {
  min-height: 30px;
  padding: 0 12px;
}

.timer-pill {
  font-size: 14px;
}

.take-layout {
  width: min(1440px, calc(100% - 48px));
  padding: 22px 0 36px;
  grid-template-columns: minmax(0, 1fr) 292px;
  gap: 18px;
}

.question-stage {
  min-height: calc(100vh - var(--header-height) - 116px);
  border-radius: 18px;
}

.question-progress {
  padding: 16px 22px;
}

.progress-main strong {
  font-size: 15px;
}

.progress-main span,
.progress-mini span,
.side-head span,
.legend span,
.side-row,
.result-kicker {
  font-size: 12px;
}

.progress-track {
  height: 6px;
  margin-top: 10px;
}

.progress-mini {
  gap: 14px;
}

.progress-mini div {
  min-width: 50px;
}

.progress-mini strong {
  font-size: 18px;
}

.question-body {
  padding: 32px 46px 30px;
}

.question-number {
  font-size: 13px;
}

.chip {
  min-height: 24px;
  padding: 0 9px;
  font-size: 11px;
}

.mark-btn {
  min-height: 30px;
  padding: 0 11px;
  font-size: 12px;
}

.question-body h1 {
  max-width: 940px;
  margin: 22px 0 18px;
  font-size: 24px;
  line-height: 1.45;
  font-weight: 850;
}

.question-material {
  max-width: 940px;
  padding: 12px 16px;
  font-size: 13px;
}

.option-stack {
  max-width: 940px;
  margin-top: 22px;
  gap: 10px;
}

.option-stack button {
  min-height: 58px;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
  border-radius: 12px;
  padding: 12px 16px;
}

.option-stack b {
  width: 32px;
  height: 32px;
  font-size: 13px;
}

.option-stack span {
  font-size: 14px;
  line-height: 1.55;
  font-weight: 720;
}

.answer-text {
  min-height: 180px;
  margin-top: 22px;
  border-radius: 12px;
  padding: 14px;
  font-size: 14px;
}

.question-footer {
  padding: 14px 22px;
}

.outline-btn,
.primary-btn,
.result-actions button {
  min-height: 38px;
  border-radius: 10px;
  padding: 0 16px;
}

.answer-side {
  top: 90px;
  gap: 14px;
}

.side-panel {
  padding: 16px;
  border-radius: 16px;
}

.side-head {
  margin-bottom: 12px;
}

.side-head h2 {
  font-size: 16px;
}

.answer-grid {
  gap: 8px;
}

.answer-grid button {
  border-radius: 9px;
  font-size: 14px;
}

.submit-wide {
  min-height: 40px;
  margin-top: 14px;
  border-radius: 10px;
}

.side-list {
  gap: 10px;
}

.side-row {
  min-height: 30px;
}

.side-row strong {
  font-size: 13px;
}

.result-panel h2 {
  font-size: 34px;
}

.wrong-list article {
  padding: 16px;
}

.wrong-list strong {
  font-size: 15px;
}

.take-page {
  background: var(--ds-page-bg);
}

.exam-topbar,
.question-stage,
.side-panel,
.result-panel {
  border-color: var(--ds-card-border-color);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.question-progress {
  background: var(--ds-card-bg);
}

.progress-track i {
  background: var(--ds-orange);
}

.answer-text {
  border-color: var(--ds-input-border);
  background: var(--ds-input-bg);
}

.answer-text:focus {
  border-color: var(--ds-input-border-focus);
  box-shadow: var(--ds-focus-ring);
}

.side-submit {
  width: 100%;
  margin-top: 16px;
}

.option-stack button:hover {
  transform: none;
  box-shadow: none;
}

.option-stack button:focus-visible,
.answer-grid button:focus-visible,
.mark-btn:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: 2px;
}

@media (max-width: 1100px) {
  .take-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .question-body {
    padding: 24px 18px;
  }

  .question-body h1 {
    font-size: 20px;
  }

  .option-stack button {
    min-height: 54px;
  }
}
</style>

/* TRAINING-CAMP-DS-ALIGN */
.practice-page,
.take-page {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
.practice-page h1,
.take-page h1,
.practice-title h1,
.paper-title h1 {
  font-size: 24px !important;
  line-height: 1.3 !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
}
