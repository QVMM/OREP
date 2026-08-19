<template>
  <div class="review-page" :class="`accent-${accent}`">
    <section class="review-shell">
      <header class="review-hero">
        <div class="hero-copy">
          <BaseButton type="text" size="small" class="back-link" @click="router.push('/exam-system')">
            <el-icon><ArrowLeft /></el-icon>
            返回考试系统
          </BaseButton>
          <nav class="review-page-tabs" aria-label="题目复盘页面">
            <router-link to="/exam-system/wrong-book" :class="{ active: !isFavoritesReview }">
              错题本
            </router-link>
            <router-link to="/exam-system/favorites" :class="{ active: isFavoritesReview }">
              收藏题
            </router-link>
          </nav>
          <span>{{ eyebrow }}</span>
          <h1>{{ title }}</h1>
          <p>{{ subtitle }}</p>
        </div>
        <div class="hero-actions">
          <BaseButton :disabled="!questions.length" @click="startPractice">
            进入专项练习
            <el-icon><ArrowRight /></el-icon>
          </BaseButton>
          <BaseButton type="secondary" @click="clearFilters">重置筛选</BaseButton>
        </div>
      </header>

      <section class="review-summary" aria-label="复盘概览">
        <div class="panel-main">
          <strong>{{ questions.length }}</strong>
          <div>
            <span>{{ metricLabel }}</span>
          </div>
        </div>
        <div class="panel-stats">
          <div>
            <span>选择题</span>
            <strong>{{ choiceCount }}</strong>
          </div>
          <div>
            <span>主观题</span>
            <strong>{{ subjectiveCount }}</strong>
          </div>
        </div>
      </section>

      <section class="review-workbench">
        <aside class="review-sidebar">
          <div class="sidebar-head">
            <h2>复盘筛选</h2>
            <span>{{ questions.length }} 题</span>
          </div>
          <label class="search-box">
            <el-icon><Search /></el-icon>
            <input v-model="keyword" type="search" placeholder="搜索题干、解析、知识点" />
          </label>

          <section class="filter-block">
            <div class="filter-title">题型</div>
            <button
              v-for="item in filters"
              :key="item.value"
              type="button"
              :class="{ active: activeType === item.value }"
              @click="activeType = item.value"
            >
              <span>{{ item.label }}</span>
              <b>{{ item.count }}</b>
            </button>
          </section>

          <section class="filter-block">
            <div class="filter-title">知识点</div>
            <button
              v-for="item in categoryFilters"
              :key="item.value"
              type="button"
              :class="{ active: activeCategory === item.value }"
              @click="activeCategory = item.value"
            >
              <span>{{ item.label }}</span>
              <b>{{ item.count }}</b>
            </button>
          </section>
        </aside>

        <main v-loading="loading" class="question-stage">
          <div class="stage-head">
            <div>
              <h2>复盘题目</h2>
              <p>先看解析，再进入同类题练习，避免只重复做错。</p>
            </div>
            <BaseButton size="small" :disabled="!questions.length" @click="startPractice">
              练同类题
            </BaseButton>
          </div>

          <article v-for="(item, index) in filteredQuestions" :key="item.id" class="question-card">
            <div class="question-top">
              <div class="question-index">{{ String(index + 1).padStart(2, '0') }}</div>
              <div class="question-title">
                <div class="question-meta">
                  <span>{{ typeLabel(item.questionType) }}</span>
                  <small>{{ item.category || '通用题库' }} · {{ difficultyLabel(item.difficulty) }}</small>
                </div>
                <h3>{{ item.stem }}</h3>
              </div>
              <BaseButton type="secondary" size="small" @click="favorite(item)">
                {{ isFavoritesReview ? '取消收藏' : '收藏' }}
              </BaseButton>
            </div>

            <div v-if="isChoice(item.questionType)" class="option-list">
              <div v-for="(option, optionIndex) in parseOptions(item.optionsJson)" :key="option.key">
                <b>{{ optionDisplayKey(optionIndex) }}</b>
                <span>{{ option.text }}</span>
              </div>
            </div>

            <div class="answer-panel">
              <div class="answer-box">
                <span>参考答案</span>
                <strong>{{ answersToText(item.answerJson) }}</strong>
              </div>
              <div class="analysis-box">
                <span>解析</span>
                <p>{{ item.analysis || '暂无解析，建议先记录自己的错误原因，再进入同类练习。' }}</p>
              </div>
            </div>
          </article>

          <div v-if="!filteredQuestions.length && !loading" class="empty-panel">
            <span>暂无内容</span>
            <h2>{{ emptyTitle }}</h2>
            <p>{{ emptyText }}</p>
            <BaseButton type="secondary" @click="clearFilters">清空筛选条件</BaseButton>
          </div>
        </main>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Search } from '@element-plus/icons-vue'
import request from '../../utils/request'
import BaseButton from '../base/BaseButton.vue'

const props = defineProps({
  title: { type: String, required: true },
  eyebrow: { type: String, required: true },
  subtitle: { type: String, required: true },
  metricLabel: { type: String, required: true },
  emptyTitle: { type: String, required: true },
  emptyText: { type: String, required: true },
  fetchUrl: { type: String, required: true },
  practiceSource: { type: String, required: true },
  accent: { type: String, default: 'green' }
})

const router = useRouter()
const loading = ref(false)
const questions = ref([])
const activeType = ref('all')
const activeCategory = ref('all')
const keyword = ref('')
const isFavoritesReview = computed(() => props.fetchUrl === '/api/exams/favorites')

const filteredQuestions = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return questions.value.filter((item) => {
    const typeMatched = activeType.value === 'all' || item.questionType === activeType.value
    const categoryMatched = activeCategory.value === 'all' || categoryName(item) === activeCategory.value
    const textMatched = !text || `${item.stem || ''} ${item.analysis || ''} ${categoryName(item)}`.toLowerCase().includes(text)
    return typeMatched && categoryMatched && textMatched
  })
})

const choiceCount = computed(() => questions.value.filter((item) => isChoice(item.questionType)).length)
const subjectiveCount = computed(() => questions.value.length - choiceCount.value)

const filters = computed(() => {
  const types = [
    { value: 'all', label: '全部' },
    { value: 'single', label: '单选' },
    { value: 'multiple', label: '多选' },
    { value: 'judge', label: '判断' },
    { value: 'blank', label: '填空' },
    { value: 'programming', label: '编程' }
  ]
  return types.map((item) => ({
    ...item,
    count: item.value === 'all'
      ? questions.value.length
      : questions.value.filter((question) => question.questionType === item.value).length
  }))
})

const categoryFilters = computed(() => {
  const buckets = new Map()
  for (const question of questions.value) {
    const name = categoryName(question)
    buckets.set(name, (buckets.get(name) || 0) + 1)
  }
  return [
    { value: 'all', label: '全部知识点', count: questions.value.length },
    ...Array.from(buckets, ([value, count]) => ({ value, label: value, count }))
  ]
})

onMounted(fetchQuestions)

async function fetchQuestions() {
  loading.value = true
  try {
    const res = await request.get(props.fetchUrl)
    questions.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function favorite(item) {
  await request.post(`/api/exams/questions/${item.id}/favorite`)
  ElMessage.success(isFavoritesReview.value ? '已取消收藏' : '已加入收藏题')
  if (isFavoritesReview.value) await fetchQuestions()
}

function startPractice() {
  if (!questions.value.length) return
  router.push({ name: 'ExamPractice', params: { source: props.practiceSource } })
}

function clearFilters() {
  activeType.value = 'all'
  activeCategory.value = 'all'
  keyword.value = ''
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

function answersToText(json) {
  try {
    return JSON.parse(json || '[]').join('、') || '待人工评阅'
  } catch {
    return '待人工评阅'
  }
}

function isChoice(type) {
  return type === 'single' || type === 'multiple' || type === 'judge'
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

function difficultyLabel(value) {
  return {
    easy: '简单',
    normal: '普通',
    hard: '困难'
  }[value] || '普通'
}

function categoryName(item) {
  return item.category || item.knowledgePoint || item.courseCategory || '通用题库'
}
</script>

<style scoped>
.review-page {
  position: relative;
  min-height: calc(100vh - 72px);
  padding: 34px 32px 72px;
  color: var(--orep-text-strong);
  background:
    radial-gradient(circle at 86% 12%, oklch(0.89 0.12 52 / 0.24), transparent 30%),
    linear-gradient(180deg, oklch(0.985 0.006 55), oklch(0.965 0.012 58));
}

.review-page.accent-blue {
  background:
    radial-gradient(circle at 86% 12%, oklch(0.82 0.11 245 / 0.16), transparent 30%),
    linear-gradient(180deg, oklch(0.985 0.006 55), oklch(0.965 0.012 58));
}

.review-shell {
  position: relative;
  width: min(1440px, 100%);
  margin: 0 auto;
}

.review-hero,
.review-sidebar,
.question-stage {
  border: 1px solid oklch(0.88 0.012 60);
  border-radius: 8px;
  background: oklch(0.995 0.004 65 / 0.9);
  box-shadow: 0 22px 58px oklch(0.74 0.04 55 / 0.18);
}

.review-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  align-items: stretch;
  gap: 42px;
  padding: 32px;
  overflow: hidden;
  background:
    linear-gradient(110deg, oklch(0.995 0.004 65) 0%, oklch(0.985 0.018 58) 100%);
}

.hero-copy {
  max-width: 820px;
}

.back-link {
  min-height: 32px;
  margin-bottom: 24px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  color: var(--orep-muted);
  font: inherit;
  font-weight: 760;
  cursor: pointer;
}

.hero-copy > span,
.empty-panel > span {
  color: var(--orep-orange);
  font-size: 13px;
  font-weight: 850;
  letter-spacing: 0;
}

.accent-blue .hero-copy > span,
.accent-blue .empty-panel > span {
  color: oklch(0.58 0.14 245);
}

.review-hero h1 {
  margin: 14px 0 0;
  font-size: clamp(34px, 4vw, 56px);
  line-height: 1.08;
  font-weight: 900;
  letter-spacing: 0;
}

.review-hero p {
  max-width: 760px;
  margin: 18px 0 0;
  color: var(--orep-muted);
  line-height: 1.8;
  font-size: 16px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.primary-action,
.ghost-action,
.small-action,
.pin-btn,
.filter-block button {
  border-radius: 8px;
  font: inherit;
  font-weight: 820;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.primary-action,
.ghost-action,
.small-action {
  min-height: 44px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.primary-action,
.small-action {
  border: 1px solid oklch(0.15 0.015 45);
  background: oklch(0.15 0.015 45);
  color: oklch(0.98 0.006 70);
}

.primary-action:disabled,
.small-action:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.ghost-action {
  border: 1px solid oklch(0.88 0.014 60);
  background: oklch(0.995 0.004 65);
  color: var(--orep-text-strong);
}

.primary-action:not(:disabled):hover,
.small-action:not(:disabled):hover,
.ghost-action:hover,
.pin-btn:hover,
.filter-block button:hover {
  transform: translateY(-1px);
}

.hero-panel {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  border-left: 1px solid oklch(0.88 0.018 58);
  padding-left: 30px;
}

.panel-main {
  align-self: center;
}

.panel-main span,
.panel-main small,
.panel-stats span,
.question-meta small,
.analysis-box span,
.answer-box span,
.filter-title {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 740;
}

.panel-main strong {
  display: block;
  margin: 10px 0 4px;
  color: var(--orep-orange);
  font-size: 58px;
  line-height: 1;
  font-weight: 930;
  letter-spacing: 0;
}

.accent-blue .panel-main strong {
  color: oklch(0.58 0.14 245);
}

.panel-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-top: 1px solid oklch(0.89 0.012 60);
  padding-top: 18px;
}

.panel-stats div + div {
  border-left: 1px solid oklch(0.89 0.012 60);
  padding-left: 18px;
}

.panel-stats strong {
  display: block;
  margin-top: 6px;
  font-size: 26px;
  line-height: 1;
}

.review-workbench {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
  margin-top: 22px;
  align-items: start;
}

.review-sidebar {
  position: sticky;
  top: calc(var(--header-height) + 18px);
  padding: 18px;
}

.sidebar-head,
.stage-head,
.question-top,
.question-meta,
.answer-panel {
  display: flex;
  align-items: flex-start;
}

.sidebar-head,
.stage-head {
  justify-content: space-between;
  gap: 16px;
}

.sidebar-head h2,
.stage-head h2 {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
}

.sidebar-head span {
  color: var(--orep-muted);
  font-weight: 780;
}

.search-box {
  min-height: 44px;
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid oklch(0.9 0.01 60);
  background: oklch(0.975 0.006 60);
}

.search-box input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--orep-text-strong);
}

.filter-block {
  display: grid;
  gap: 8px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid oklch(0.9 0.01 60);
}

.filter-title {
  margin-bottom: 4px;
}

.filter-block button {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--orep-text-strong);
  padding: 0 10px;
  text-align: left;
}

.filter-block button.active {
  border-color: oklch(0.89 0.045 58);
  background: oklch(0.96 0.03 58);
  color: var(--orep-orange);
}

.filter-block b {
  font-size: 13px;
}

.question-stage {
  min-height: 560px;
  padding: 20px;
}

.stage-head {
  padding: 4px 4px 18px;
}

.stage-head p {
  margin: 8px 0 0;
  color: var(--orep-muted);
}

.question-card {
  border: 1px solid oklch(0.89 0.012 60);
  border-radius: 8px;
  background: oklch(0.997 0.003 65);
  padding: 20px;
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.question-card + .question-card {
  margin-top: 12px;
}

.question-card:hover {
  border-color: oklch(0.86 0.04 58);
  box-shadow: 0 16px 36px oklch(0.74 0.04 55 / 0.14);
}

.question-top {
  gap: 14px;
}

.question-index {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: oklch(0.96 0.032 58);
  color: var(--orep-orange);
  font-weight: 900;
}

.question-title {
  min-width: 0;
  flex: 1;
}

.question-meta {
  justify-content: flex-start;
  gap: 10px;
}

.question-meta span {
  color: var(--orep-orange);
  font-size: 13px;
  font-weight: 850;
}

.question-card h3 {
  margin: 8px 0 0;
  font-size: 22px;
  line-height: 1.45;
  font-weight: 900;
}

.option-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 18px 0 0 56px;
}

.option-list div {
  display: grid;
  grid-template-columns: 32px 1fr;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid oklch(0.91 0.01 60);
  border-radius: 8px;
  background: oklch(0.982 0.004 60);
}

.option-list b {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: oklch(0.94 0.012 60);
  color: var(--orep-muted);
  font-size: 13px;
}

.answer-panel {
  align-items: stretch;
  gap: 10px;
  margin: 18px 0 0 56px;
}

.answer-box,
.analysis-box {
  border-radius: 8px;
  padding: 14px;
  background: oklch(0.975 0.012 58);
}

.answer-box {
  flex: 0 0 210px;
}

.analysis-box {
  flex: 1;
}

.answer-box span,
.analysis-box span {
  display: block;
  margin-bottom: 8px;
}

.answer-box strong {
  display: block;
  font-size: 18px;
  line-height: 1.4;
}

.analysis-box p,
.empty-panel p {
  margin: 0;
  color: var(--orep-muted);
  line-height: 1.8;
}

.pin-btn {
  flex: 0 0 auto;
  min-height: 36px;
  border: 1px solid oklch(0.89 0.014 60);
  background: oklch(0.995 0.004 65);
  color: var(--orep-text-strong);
  padding: 0 14px;
}

.empty-panel {
  border: 1px dashed oklch(0.86 0.018 60);
  border-radius: 8px;
  background: oklch(0.99 0.004 65);
  padding: 42px;
  text-align: center;
}

.empty-panel h2 {
  margin: 10px 0;
}

@media (max-width: 1100px) {
  .review-hero,
  .review-workbench {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    border-left: 0;
    border-top: 1px solid oklch(0.88 0.018 58);
    padding-left: 0;
    padding-top: 22px;
  }

  .review-sidebar {
    position: static;
  }
}

@media (max-width: 760px) {
  .review-page {
    padding: 18px 14px 42px;
  }

  .review-hero,
  .question-stage,
  .review-sidebar {
    padding: 16px;
  }

  .option-list,
  .answer-panel {
    grid-template-columns: 1fr;
    flex-direction: column;
    margin-left: 0;
  }

  .question-top {
    flex-wrap: wrap;
  }
}

/* Compact review desk: match the exam system task-page scale. */
.review-page {
  min-height: 100%;
  padding: var(--ds-page-margin-y, 40px) var(--ds-page-margin-x, 40px);
  background: transparent;
}

.review-shell {
  width: 100%;
  max-width: none;
  margin: 0;
}

.review-hero,
.review-sidebar,
.question-stage {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-card-radius);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.review-hero {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
  padding: 20px 22px;
  background: var(--ds-card-bg);
}

.hero-copy {
  max-width: 860px;
}

.back-link {
  min-height: 28px;
  margin-bottom: 8px;
  width: fit-content;
  color: var(--workspace-ink-500, var(--orep-muted));
  font-size: 13px;
  font-weight: 700;
}

.hero-copy > span,
.empty-panel > span {
  font-size: 12px;
  font-weight: 800;
}

.hero-copy > span {
  display: none;
}

.review-hero h1 {
  margin: 4px 0 0;
  color: var(--workspace-ink-900, var(--orep-text-strong));
  font-size: 22px;
  line-height: 1.25;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.review-hero p {
  max-width: 820px;
  margin: 6px 0 0;
  color: var(--workspace-ink-500, var(--orep-muted));
  font-size: 13px;
  font-weight: 650;
  line-height: 1.55;
}

.hero-actions {
  margin-top: 12px;
  gap: 10px;
}

.filter-block button {
  border-radius: 10px;
  font-size: 13px;
  font-weight: 800;
}

.hero-panel {
  width: 300px;
  border-left: 1px solid rgba(219, 205, 194, 0.54);
  padding-left: 24px;
}

.panel-main span,
.panel-main small,
.panel-stats span,
.question-meta small,
.analysis-box span,
.answer-box span,
.filter-title,
.sidebar-head span,
.stage-head p {
  color: var(--workspace-ink-500, var(--orep-muted));
  font-size: 12px;
  font-weight: 650;
}

.panel-main strong {
  margin: 6px 0 4px;
  color: var(--workspace-orange-600, var(--orep-orange));
  font-size: 28px;
  font-weight: 800;
}

.panel-stats {
  padding-top: 12px;
}

.panel-stats strong {
  margin-top: 5px;
  font-size: 18px;
}

.review-workbench {
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 14px;
  margin-top: 14px;
}

.review-sidebar {
  top: 16px;
  padding: 14px;
}

.sidebar-head h2,
.stage-head h2 {
  color: var(--workspace-ink-900, var(--orep-text-strong));
  font-size: 15px;
  font-weight: 800;
}

.search-box {
  min-height: 34px;
  margin-top: 12px;
  border-color: var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  background: var(--ds-input-bg);
}

.search-box:focus-within {
  border-color: var(--ds-input-border-focus);
  box-shadow: var(--ds-focus-ring);
}

.search-box input {
  font-size: 13px;
}

.filter-block {
  gap: 4px;
  margin-top: 14px;
  padding-top: 14px;
  border-top-color: rgba(219, 205, 194, 0.5);
}

.filter-title {
  margin-bottom: 2px;
}

.filter-block button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid transparent;
  color: var(--ds-fg-secondary);
  background: transparent;
}

.filter-block button.active {
  border-color: var(--ds-selected-border);
  background: var(--ds-selected-bg);
  color: var(--ds-selected-text);
}

.filter-block button:not(.active):hover {
  background: var(--ds-surface-subtle);
  transform: none;
}

.filter-block button.active:hover {
  transform: none;
}

.filter-block button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: 2px;
}

.filter-block b {
  font-size: 12px;
}

.question-stage {
  min-height: 0;
  padding: 16px;
}

.stage-head {
  padding: 0 0 12px;
  align-items: center;
}

.stage-head p {
  margin: 5px 0 0;
}

.question-card {
  border-color: var(--ds-card-border-color);
  border-radius: 14px;
  background: var(--ds-surface);
  padding: 16px;
}

.question-card + .question-card {
  margin-top: 10px;
}

.question-top {
  gap: 12px;
}

.question-index {
  width: 32px;
  height: 32px;
  background: var(--workspace-orange-50, var(--orep-orange-wash));
  font-size: 13px;
}

.question-meta {
  gap: 8px;
}

.question-meta span {
  color: var(--workspace-orange-600, var(--orep-orange));
  font-size: 12px;
  font-weight: 800;
}

.question-card h3 {
  margin: 5px 0 0;
  color: var(--workspace-ink-900, var(--orep-text-strong));
  font-size: 16px;
  line-height: 1.5;
  font-weight: 800;
}

.pin-btn {
  min-height: 32px;
  padding: 0 12px;
}

.option-list {
  gap: 8px;
  margin: 12px 0 0 44px;
}

.option-list div {
  min-height: 38px;
  grid-template-columns: 28px 1fr;
  gap: 10px;
  border-color: var(--ds-border-subtle);
  border-radius: 10px;
  background: var(--ds-surface);
  padding: 8px 10px;
}

.option-list b {
  width: 24px;
  height: 24px;
  font-size: 12px;
}

.option-list span {
  color: var(--workspace-ink-700, var(--orep-text-strong));
  font-size: 13px;
  line-height: 1.45;
}

.answer-panel {
  gap: 8px;
  margin: 12px 0 0 44px;
}

.answer-box,
.analysis-box {
  border-radius: 10px;
  background: var(--ds-surface-subtle);
  padding: 12px;
}

.answer-box {
  flex-basis: 170px;
}

.answer-box span,
.analysis-box span {
  margin-bottom: 5px;
}

.answer-box strong {
  font-size: 15px;
}

.analysis-box p,
.empty-panel p {
  color: var(--workspace-ink-500, var(--orep-muted));
  font-size: 13px;
  line-height: 1.6;
}

.empty-panel {
  border-radius: 14px;
  padding: 34px;
}

.empty-panel h2 {
  font-size: 18px;
}

@media (max-width: 1100px) {
  .review-hero,
  .review-workbench {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    width: auto;
    border-left: 0;
    border-top: 1px solid rgba(219, 205, 194, 0.54);
    padding-left: 0;
    padding-top: 14px;
  }

  .review-sidebar {
    position: static;
  }
}

@media (max-width: 760px) {
  .review-page {
    padding: 18px 16px 96px;
  }

  .review-hero,
  .question-stage,
  .review-sidebar {
    padding: 14px;
  }

  .review-hero h1 {
    font-size: 20px;
  }

  .option-list,
  .answer-panel {
    grid-template-columns: 1fr;
    flex-direction: column;
    margin-left: 0;
  }
}

/* Unified review workspace: light hierarchy shared with training tasks. */
.review-page {
  --review-orange: var(--workspace-orange-600, #e75b25);
  --review-orange-soft: var(--workspace-orange-50, #fff2e9);
  --review-ink: var(--workspace-ink-900, #242832);
  --review-muted: var(--workspace-ink-500, #737984);
  --review-line: #e7e1da;
  padding: 0 0 72px;
}

.review-hero {
  min-height: 108px;
  padding: 0 0 20px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
  overflow: visible;
  border: 0;
  border-bottom: 1px solid var(--review-line);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.hero-copy {
  min-width: 0;
  max-width: 760px;
}

.back-link {
  margin: 0 0 12px;
  padding: 0;
  color: var(--review-muted);
}

.review-page-tabs {
  width: fit-content;
  margin: 0 0 16px;
  padding: 3px;
  display: flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--review-line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
}

.review-page-tabs a {
  min-width: 76px;
  min-height: 32px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  color: var(--review-muted);
  font-size: 13px;
  font-weight: 700;
  transition: color 160ms ease, background-color 160ms ease, box-shadow 160ms ease;
}

.review-page-tabs a:hover {
  color: var(--review-ink);
}

.review-page-tabs a.active {
  color: #c94e18;
  background: var(--review-orange-soft);
  box-shadow: 0 1px 3px rgba(65, 43, 29, 0.08);
}

.review-page-tabs a:focus-visible {
  outline: 2px solid var(--review-orange);
  outline-offset: 2px;
}

.review-hero h1 {
  margin: 0;
  color: var(--review-ink);
  font-size: 28px;
  font-weight: 760;
  letter-spacing: -0.035em;
}

.review-hero p {
  margin: 8px 0 0;
  color: var(--review-muted);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
}

.hero-actions {
  flex: 0 0 auto;
  margin: 0;
  align-items: center;
}

.review-summary {
  min-height: 78px;
  padding: 14px 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 28px;
  border-bottom: 1px solid var(--review-line);
}

.panel-main {
  display: flex;
  align-items: center;
  gap: 14px;
}

.panel-main strong {
  min-width: 42px;
  margin: 0;
  color: var(--review-orange);
  font-size: 28px;
  line-height: 1;
}

.panel-main span,
.panel-main small {
  display: block;
}

.panel-main span {
  color: var(--review-ink);
  font-size: 13px;
  font-weight: 760;
}

.panel-main small {
  margin-top: 4px;
  color: var(--review-muted);
  font-size: 11px;
}

.panel-stats {
  padding: 0;
  display: flex;
  border: 0;
}

.panel-stats div {
  min-width: 92px;
  padding: 2px 22px;
  border-left: 1px solid var(--review-line);
  text-align: center;
}

.panel-stats div + div {
  padding-left: 22px;
  border-left: 1px solid var(--review-line);
}

.panel-stats strong {
  margin-top: 4px;
  color: var(--review-ink);
  font-size: 18px;
}

.review-workbench {
  grid-template-columns: 232px minmax(0, 1fr);
  gap: 16px;
  margin-top: 20px;
}

.review-sidebar,
.question-stage {
  border: 1px solid var(--review-line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 30px rgba(49, 40, 33, 0.035);
}

.review-sidebar {
  top: 18px;
  padding: 16px;
}

.sidebar-head h2,
.stage-head h2 {
  color: var(--review-ink);
  font-size: 16px;
  letter-spacing: -0.01em;
}

.search-box {
  min-height: 40px;
  border-color: var(--review-line);
  border-radius: 10px;
  background: #fbfaf8;
}

.filter-block {
  border-top-color: var(--review-line);
}

.filter-block button {
  min-height: 36px;
  border-radius: 9px;
  color: #555c68;
  font-weight: 650;
}

.filter-block button.active {
  border-color: #f0c9b7;
  color: #c94e18;
  background: var(--review-orange-soft);
}

.question-stage {
  padding: 18px;
}

.stage-head {
  margin-bottom: 2px;
  padding: 0 2px 16px;
  border-bottom: 1px solid var(--review-line);
}

.stage-head p {
  color: var(--review-muted);
  font-weight: 500;
}

.question-card {
  margin-top: 14px;
  padding: 18px;
  border: 1px solid var(--review-line);
  border-radius: 14px;
  background: #fff;
  box-shadow: none;
}

.question-card + .question-card {
  margin-top: 12px;
}

.question-card:hover {
  border-color: #efc0aa;
  box-shadow: 0 8px 22px rgba(76, 53, 37, 0.05);
  transform: none;
}

.question-index {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  color: #c94e18;
  background: var(--review-orange-soft);
}

.question-meta span {
  color: #c94e18;
}

.question-card h3 {
  color: var(--review-ink);
  font-size: 16px;
  font-weight: 740;
}

.option-list div {
  border-color: #ece7e2;
  background: #fbfaf8;
}

.option-list b {
  color: #767c85;
  background: #f0ede9;
}

.answer-box,
.analysis-box {
  border: 1px solid #eee9e4;
  background: #faf8f6;
}

.answer-box strong {
  color: var(--review-ink);
}

.empty-panel {
  border-color: var(--review-line);
  background: #fbfaf8;
}

@media (max-width: 1100px) {
  .review-workbench {
    grid-template-columns: 1fr;
  }

  .review-sidebar {
    position: static;
  }
}

@media (max-width: 760px) {
  .review-page {
    padding: 0 0 78px;
  }

  .review-hero {
    align-items: stretch;
    flex-direction: column;
    gap: 18px;
  }

  .hero-actions {
    align-self: stretch;
  }

  .review-page-tabs {
    width: 100%;
  }

  .review-page-tabs a {
    flex: 1;
  }

  .review-summary {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .panel-stats div {
    flex: 1;
  }

  .question-card {
    padding: 14px;
  }

  .option-list,
  .answer-panel {
    margin-left: 0;
  }
}
</style>
