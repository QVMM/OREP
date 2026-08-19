<template>
  <div class="practice-page" :class="`accent-${sourceMeta.accent}`">
    <section class="practice-shell">
      <header class="practice-topbar">
        <BaseButton type="text" size="small" class="back-link" @click="router.push(sourceMeta.backPath)">
          <el-icon><ArrowLeft /></el-icon>
          返回{{ sourceMeta.title }}
        </BaseButton>
        <div class="practice-title">
          <strong>{{ sourceMeta.title }}练习</strong>
          <span>{{ sourceMeta.subtitle }}</span>
        </div>
        <div class="status-cluster">
          <span>{{ result ? '练习已完成' : '练习中' }}</span>
          <b>{{ result ? accuracyText : `${answeredCount}/${questions.length}` }}</b>
        </div>
      </header>

      <main v-if="!result" v-loading="loading" class="practice-layout">
        <section v-if="activeQuestion" class="question-stage">
          <header class="question-progress">
            <div class="progress-main">
              <strong>已完成 {{ answeredCount }} / {{ questions.length }} 题</strong>
              <span>当前第 {{ activeIndex + 1 }} 题，练习结果只用于复盘，不影响正式考试成绩。</span>
              <div class="progress-track"><i :style="{ width: progressPercent }"></i></div>
            </div>
            <div class="progress-mini">
              <div><span>已答</span><strong>{{ answeredCount }}</strong></div>
              <div><span>未答</span><strong>{{ questions.length - answeredCount }}</strong></div>
              <div><span>总题数</span><strong>{{ questions.length }}</strong></div>
            </div>
          </header>

          <section class="question-body">
            <div class="question-meta">
              <div>
                <span class="question-number">{{ String(activeIndex + 1).padStart(2, '0') }} / {{ String(questions.length).padStart(2, '0') }}</span>
                <span class="chip">{{ typeLabel(activeQuestion.questionType) }}</span>
                <span class="chip">{{ activeQuestion.score || 0 }} 分</span>
              </div>
            </div>

            <h1>{{ activeQuestion.stem }}</h1>

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
              :rows="activeQuestion.questionType === 'programming' ? 10 : 6"
              :placeholder="activeQuestion.questionType === 'programming' ? '输入代码或解题思路，提交后对照参考答案自查' : '输入答案'"
            />
          </section>

          <footer class="question-footer">
            <div class="nav-side">
              <BaseButton type="secondary" :disabled="activeIndex === 0" @click="activeIndex--">上一题</BaseButton>
            </div>
            <div class="nav-side">
              <BaseButton type="secondary" :disabled="activeIndex === questions.length - 1" @click="activeIndex++">下一题</BaseButton>
              <BaseButton @click="finishPractice">完成练习</BaseButton>
            </div>
          </footer>
        </section>

        <aside class="practice-side">
          <section class="side-panel">
            <div class="side-head">
              <h2>练习卡</h2>
              <span>已答 {{ answeredCount }}</span>
            </div>
            <div class="answer-grid">
              <button
                v-for="(question, index) in questions"
                :key="question.id"
                type="button"
                :class="{ current: index === activeIndex, done: isAnswered(question) }"
                @click="activeIndex = index"
              >
                {{ index + 1 }}
              </button>
            </div>
            <div class="legend">
              <span><i class="now"></i>当前</span>
              <span><i class="done"></i>已答</span>
              <span><i></i>未答</span>
            </div>
            <BaseButton class="side-submit" :disabled="!questions.length" @click="finishPractice">完成练习</BaseButton>
          </section>

          <section class="side-panel">
            <div class="side-head">
              <h2>练习说明</h2>
            </div>
            <div class="side-list">
              <div class="side-row"><span>来源</span><strong>{{ sourceMeta.title }}</strong></div>
              <div class="side-row"><span>题目顺序</span><strong>随机</strong></div>
              <div class="side-row"><span>成绩影响</span><strong>不计入考试</strong></div>
            </div>
          </section>
        </aside>

        <div v-if="!questions.length && !loading" class="empty-panel">
          <span>暂无练习题</span>
          <h2>{{ sourceMeta.emptyTitle }}</h2>
          <p>{{ sourceMeta.emptyText }}</p>
          <BaseButton type="secondary" @click="router.push(sourceMeta.backPath)">返回{{ sourceMeta.title }}</BaseButton>
        </div>
      </main>

      <section v-else class="result-panel">
        <div class="result-summary">
          <span>练习结果</span>
          <h1>{{ accuracyText }}</h1>
          <p>客观题已自动核对，主观题请对照参考答案自查。建议先看错误原因，再回到错题本继续复盘。</p>
          <div class="result-actions">
            <BaseButton @click="restart">再练一次</BaseButton>
            <BaseButton type="secondary" @click="router.push(sourceMeta.backPath)">返回{{ sourceMeta.title }}</BaseButton>
          </div>
        </div>

        <div class="review-list">
          <article v-for="(item, index) in result.items" :key="item.question.id" :class="{ wrong: !item.correct && !item.manual }">
            <div class="review-head">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <b>{{ item.manual ? '自查' : item.correct ? '正确' : '错误' }}</b>
            </div>
            <h2>{{ item.question.stem }}</h2>
            <div class="review-answer">
              <small>你的答案：{{ item.answerText || '未作答' }}</small>
              <small>参考答案：{{ answersToText(item.question.answerJson) }}</small>
            </div>
            <p>{{ item.question.analysis || '暂无解析' }}</p>
          </article>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import request from '../utils/request'
import BaseButton from '../components/base/BaseButton.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const questions = ref([])
const activeIndex = ref(0)
const answers = ref({})
const textAnswers = ref({})
const result = ref(null)

const sourceMeta = computed(() => {
  if (route.params.source === 'favorites') {
    return {
      title: '收藏题',
      subtitle: '从收藏题里抽取重点题，做一次轻量自测。',
      fetchUrl: '/api/exams/favorites',
      backPath: '/exam-system/favorites',
      emptyTitle: '暂无收藏题可练习',
      emptyText: '先在错题本或考试页收藏题目，再回来一键练习。',
      accent: 'blue'
    }
  }
  return {
    title: '错题本',
    subtitle: '只练错题本里的题，确认自己是否已经补上薄弱点。',
    fetchUrl: '/api/exams/wrong-questions',
    backPath: '/exam-system/wrong-book',
    emptyTitle: '暂无错题可练习',
    emptyText: '完成考试后，错题会自动进入错题本。',
    accent: 'orange'
  }
})

const activeQuestion = computed(() => questions.value[activeIndex.value])
const answeredCount = computed(() => questions.value.filter(isAnswered).length)
const progressPercent = computed(() => {
  if (!questions.value.length) return '0%'
  return `${Math.round((answeredCount.value / questions.value.length) * 100)}%`
})
const accuracyText = computed(() => {
  if (!result.value) return '0%'
  const objectiveCount = result.value.items.filter((item) => !item.manual).length
  if (!objectiveCount) return '需自查'
  return `${Math.round((result.value.correct / objectiveCount) * 100)}%`
})

onMounted(fetchQuestions)

async function fetchQuestions() {
  loading.value = true
  try {
    const res = await request.get(sourceMeta.value.fetchUrl)
    questions.value = shuffle(res.data || [])
  } finally {
    loading.value = false
  }
}

function toggleMulti(questionId, key) {
  const current = new Set(answers.value[questionId] || [])
  current.has(key) ? current.delete(key) : current.add(key)
  answers.value[questionId] = [...current]
}

function finishPractice() {
  if (!questions.value.length) return
  const items = questions.value.map((question) => {
    const manual = question.questionType === 'programming'
    const submitted = manual || question.questionType === 'blank'
      ? [textAnswers.value[question.id] || '']
      : answers.value[question.id] || []
    return {
      question,
      manual,
      correct: manual ? false : isCorrect(question, submitted),
      answerText: submitted.filter(Boolean).join('、')
    }
  })
  result.value = {
    items,
    correct: items.filter((item) => !item.manual && item.correct).length
  }
  ElMessage.success('练习已完成')
}

function restart() {
  answers.value = {}
  textAnswers.value = {}
  activeIndex.value = 0
  result.value = null
  questions.value = shuffle([...questions.value])
}

function isCorrect(question, submitted) {
  const expected = readAnswers(question.answerJson)
  if (question.questionType === 'multiple') {
    return expected.length === submitted.length && expected.every((item) => submitted.includes(item))
  }
  return normalize(expected[0]) === normalize(submitted[0])
}

function isAnswered(question) {
  if (question.questionType === 'blank' || question.questionType === 'programming') return !!textAnswers.value[question.id]
  return !!answers.value[question.id]?.length
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

function readAnswers(json) {
  try {
    return JSON.parse(json || '[]').map((item) => String(item))
  } catch {
    return []
  }
}

function answersToText(json) {
  return readAnswers(json).join('、') || '待人工自查'
}

function normalize(value) {
  return String(value || '').trim().toLowerCase()
}

function shuffle(items) {
  return [...items].sort(() => Math.random() - 0.5)
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
.practice-page {
  min-height: 100vh;
  background-color: #ffffff;
  background-image: none;
  color: var(--orep-text-strong);
}

.practice-shell {
  min-height: 100vh;
  display: grid;
  grid-template-rows: 68px minmax(0, 1fr);
}

.practice-topbar {
  position: sticky;
  top: 0;
  z-index: 12;
  border-bottom: 1px solid var(--orep-border-soft);
  background: oklch(0.997 0.005 55 / 0.94);
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
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.practice-title {
  min-width: 0;
  text-align: center;
}

.practice-title strong,
.practice-title span {
  display: block;
}

.practice-title strong {
  font-size: 18px;
  line-height: 1.2;
}

.practice-title span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.status-cluster {
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.status-cluster span,
.status-cluster b {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0 14px;
  font-weight: 850;
}

.status-cluster span {
  background: oklch(0.95 0.028 145);
  color: oklch(0.48 0.11 145);
}

.status-cluster b {
  background: oklch(0.97 0.028 58);
  color: var(--orep-orange);
}

.practice-layout {
  width: min(1500px, calc(100% - 56px));
  margin: 28px auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 22px;
  align-items: start;
}

.question-stage,
.side-panel,
.result-panel,
.empty-panel {
  border: 1px solid var(--orep-border-soft);
  border-radius: 8px;
  background: oklch(0.997 0.004 65);
  box-shadow: 0 20px 50px oklch(0.72 0.035 55 / 0.14);
}

.question-stage {
  min-height: calc(100vh - 124px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.question-progress {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 28px;
  align-items: center;
  padding: 26px 34px 22px;
  border-bottom: 1px solid var(--orep-border-soft);
}

.progress-main strong {
  display: block;
  font-size: 20px;
}

.progress-main span {
  display: block;
  margin-top: 8px;
  color: var(--orep-muted);
}

.progress-track {
  height: 8px;
  margin-top: 18px;
  border-radius: 999px;
  background: oklch(0.91 0.012 58);
  overflow: hidden;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ds-orange);
  transition: width 260ms ease;
}

.progress-mini {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.progress-mini div {
  text-align: center;
  border-left: 1px solid var(--orep-border-soft);
}

.progress-mini span,
.side-head span,
.side-row span,
.review-answer small {
  display: block;
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 720;
}

.progress-mini strong {
  display: block;
  margin-top: 6px;
  font-size: 26px;
}

.question-body {
  padding: 48px 78px;
}

.question-meta > div {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.question-number {
  color: var(--orep-orange);
  font-size: 16px;
  font-weight: 900;
}

.chip {
  min-height: 30px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0 14px;
  background: oklch(0.95 0.01 60);
  color: var(--orep-muted);
  font-weight: 780;
}

.question-body h1 {
  max-width: 980px;
  margin: 28px 0 34px;
  font-size: 24px;
  line-height: 1.32;
  font-weight: 920;
}

.option-stack {
  max-width: 1000px;
  display: grid;
  gap: 14px;
}

.option-stack button {
  min-height: 72px;
  display: grid;
  grid-template-columns: 46px 1fr;
  align-items: center;
  gap: 16px;
  border: 1px solid oklch(0.88 0.012 60);
  border-radius: 8px;
  background: oklch(0.997 0.003 65);
  padding: 16px 22px;
  color: var(--orep-text-strong);
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
}

.option-stack button:hover {
  transform: translateY(-1px);
  border-color: oklch(0.83 0.04 58);
}

.option-stack button.selected {
  border-color: oklch(0.72 0.16 48);
  background: oklch(0.97 0.03 58);
}

.option-stack b {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: oklch(0.94 0.012 60);
  color: var(--orep-muted);
}

.option-stack button.selected b {
  background: var(--orep-orange);
  color: oklch(0.99 0.005 60);
}

.answer-text {
  width: min(920px, 100%);
  border: 1px solid oklch(0.88 0.012 60);
  border-radius: 8px;
  padding: 16px;
  background: oklch(0.995 0.004 65);
  color: var(--orep-text-strong);
  font: inherit;
  line-height: 1.7;
  resize: vertical;
  outline: none;
}

.question-footer {
  min-height: 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 34px;
  border-top: 1px solid var(--orep-border-soft);
  background: oklch(0.992 0.004 65);
}

.nav-side {
  display: flex;
  gap: 12px;
}

.outline-btn,
.primary-btn,
.submit-wide {
  min-height: 44px;
  border-radius: 8px;
  padding: 0 20px;
  font: inherit;
  font-weight: 850;
  cursor: pointer;
}

.outline-btn {
  border: 1px solid oklch(0.87 0.014 60);
  background: oklch(0.997 0.003 65);
  color: var(--orep-text-strong);
}

.primary-btn,
.submit-wide {
  border: 1px solid oklch(0.15 0.015 45);
  background: oklch(0.15 0.015 45);
  color: oklch(0.98 0.005 60);
}

.outline-btn:disabled,
.primary-btn:disabled,
.submit-wide:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.practice-side {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 18px;
}

.side-panel {
  padding: 20px;
}

.side-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.side-head h2 {
  margin: 0;
  font-size: 22px;
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-top: 18px;
}

.answer-grid button {
  aspect-ratio: 1;
  border: 1px solid oklch(0.88 0.014 60);
  border-radius: 8px;
  background: oklch(0.997 0.004 65);
  color: var(--orep-text-strong);
  font-weight: 900;
  cursor: pointer;
}

.answer-grid button.current {
  border-color: oklch(0.18 0.012 45);
  box-shadow: inset 0 0 0 2px oklch(0.18 0.012 45);
}

.answer-grid button.done {
  background: oklch(0.96 0.032 58);
  color: var(--orep-orange);
}

.legend {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 16px 0;
  color: var(--orep-muted);
  font-size: 13px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: oklch(0.88 0.01 60);
}

.legend i.now {
  background: oklch(0.18 0.012 45);
}

.legend i.done {
  background: var(--orep-orange);
}

.submit-wide {
  width: 100%;
}

.side-list {
  display: grid;
  gap: 16px;
  margin-top: 20px;
}

.side-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.empty-panel {
  grid-column: 1 / -1;
  padding: 44px;
  text-align: center;
}

.empty-panel span,
.result-summary span {
  color: var(--orep-orange);
  font-weight: 860;
}

.empty-panel h2 {
  margin: 12px 0;
}

.result-panel {
  width: min(1500px, calc(100% - 56px));
  margin: 28px auto;
  padding: 28px;
}

.result-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
  border-bottom: 1px solid var(--orep-border-soft);
  padding-bottom: 24px;
}

.result-summary h1 {
  margin: 10px 0 0;
  font-size: 24px;
  line-height: 1;
}

.result-summary p {
  max-width: 720px;
  margin: 14px 0 0;
  color: var(--orep-muted);
  line-height: 1.8;
}

.result-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.review-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 22px;
}

.review-list article {
  border: 1px solid oklch(0.88 0.012 60);
  border-radius: 8px;
  background: oklch(0.997 0.003 65);
  padding: 20px;
}

.review-list article.wrong {
  border-color: oklch(0.78 0.14 35);
  background: oklch(0.98 0.024 38);
}

.review-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--orep-orange);
  font-weight: 900;
}

.review-list h2 {
  margin: 16px 0;
  font-size: 20px;
  line-height: 1.45;
}

.review-answer {
  display: grid;
  gap: 6px;
}

.review-list p {
  margin: 14px 0 0;
  color: var(--orep-muted);
  line-height: 1.8;
}

@media (max-width: 1080px) {
  .practice-layout,
  .result-summary,
  .review-list {
    grid-template-columns: 1fr;
  }

  .practice-side {
    position: static;
  }
}

@media (max-width: 760px) {
  .practice-topbar {
    grid-template-columns: 1fr;
    gap: 8px;
    min-height: auto;
    padding: 14px;
  }

  .practice-title {
    text-align: left;
  }

  .status-cluster {
    justify-self: start;
  }

  .practice-layout,
  .result-panel {
    width: calc(100% - 28px);
  }

  .question-progress {
    grid-template-columns: 1fr;
  }

  .question-body {
    padding: 28px 20px;
  }

  .question-footer,
  .nav-side {
    flex-direction: column;
    align-items: stretch;
  }
}

/* Compact answering typography: keep practice pages readable without oversized text. */
.practice-shell {
  grid-template-rows: 60px minmax(0, 1fr);
}

.practice-topbar {
  padding: 0 var(--ds-space-6, 24px);
}

.back-link,
.status-cluster span,
.status-cluster b,
.outline-btn,
.primary-btn,
.submit-wide {
  font-size: 13px;
}

.practice-title strong {
  font-size: 16px;
}

.practice-title span {
  font-size: 11px;
}

.status-cluster span,
.status-cluster b {
  min-height: 30px;
  padding: 0 12px;
}

.practice-layout {
  width: min(1440px, calc(100% - 48px));
  margin: 22px auto;
  grid-template-columns: minmax(0, 1fr) 292px;
  gap: 18px;
}

.question-stage {
  min-height: calc(100vh - 108px);
}

.question-progress {
  grid-template-columns: minmax(0, 1fr) 250px;
  gap: 20px;
  padding: 18px 28px 16px;
}

.progress-main strong {
  font-size: 17px;
}

.progress-main span,
.progress-mini span,
.side-head span,
.side-row span,
.legend,
.review-answer small {
  font-size: 12px;
}

.progress-track {
  height: 7px;
  margin-top: 14px;
}

.progress-mini {
  gap: 10px;
}

.progress-mini strong {
  font-size: 22px;
}

.question-body {
  padding: 34px 58px;
}

.question-number {
  font-size: 14px;
}

.chip {
  min-height: 26px;
  padding: 0 11px;
  font-size: 12px;
}

.question-body h1 {
  max-width: 940px;
  margin: 22px 0 26px;
  font-size: 24px;
  line-height: 1.45;
  font-weight: 850;
}

.option-stack {
  max-width: 940px;
  gap: 10px;
}

.option-stack button {
  min-height: 58px;
  grid-template-columns: 38px 1fr;
  gap: 12px;
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
}

.answer-text {
  font-size: 14px;
}

.question-footer {
  min-height: 66px;
  padding: 14px 28px;
}

.outline-btn,
.primary-btn,
.submit-wide {
  min-height: 38px;
  padding: 0 16px;
}

.practice-side {
  top: 82px;
  gap: 14px;
}

.side-panel {
  padding: 16px;
}

.side-head h2 {
  font-size: 16px;
}

.answer-grid {
  gap: 8px;
  margin-top: 14px;
}

.answer-grid button {
  border-radius: 9px;
  font-size: 14px;
}

.side-list {
  gap: 12px;
  margin-top: 14px;
}

.side-row strong {
  font-size: 14px;
}

.result-summary h1 {
  font-size: 24px;
}

.review-list h2 {
  font-size: 16px;
}

.practice-page {
  background: var(--ds-page-bg);
}

.practice-topbar,
.question-stage,
.side-panel,
.result-panel {
  border-color: var(--ds-card-border-color);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
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
.answer-grid button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: 2px;
}

@media (max-width: 1080px) {
  .practice-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .question-progress {
    grid-template-columns: 1fr;
  }

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
