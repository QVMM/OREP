<template>
  <div class="exam-page">
    <main class="exam-page__inner">
      <header class="exam-header">
        <div class="exam-title-block">
          <h1>练习与考试</h1>
          <p>复习真实错题、整理收藏题，并参加老师发布的正式考试。</p>
          <div v-if="wrongQuestions.length" class="exam-actions">
            <BaseButton
              @click="router.push('/exam-system/wrong-book')"
            >
              查看错题本
            </BaseButton>
          </div>
        </div>

        <div class="exam-metrics" aria-label="练习状态">
          <div>
            <strong>{{ wrongQuestions.length }}</strong>
            <span>待复盘错题</span>
          </div>
          <div>
            <strong>{{ favorites.length }}</strong>
            <span>收藏题</span>
          </div>
          <div>
            <strong>{{ papers.length }}</strong>
            <span>可考试</span>
          </div>
        </div>
      </header>

      <section class="exam-switcher">
        <div class="exam-tabs" role="tablist" aria-label="练习与考试导航">
          <BaseButton
            v-for="item in views"
            :key="item.value"
            type="secondary"
            size="small"
            :aria-pressed="activeView === item.value"
            @click="activeView = item.value"
          >
            {{ item.label }}
          </BaseButton>
        </div>
      </section>

      <section class="exam-content exam-content--single">
        <section class="main-panel" v-loading="loading">
          <div v-show="activeView === 'training'" class="view-panel">
            <div class="section-title">
              <h2>自主练习</h2>
              <span>仅使用你的真实错题与收藏题</span>
            </div>

            <div class="task-list">
              <button
                v-if="wrongQuestions.length"
                type="button"
                class="task-row task-row--primary"
                @click="router.push('/exam-system/practice/wrong')"
              >
                <span class="task-type">错题</span>
                <div>
                  <strong>错题专项练习</strong>
                  <small>{{ wrongQuestions.length }} 道错题 · 来源于你已完成的考试</small>
                </div>
                <em>开始练习</em>
              </button>

              <button
                v-if="favorites.length"
                type="button"
                class="task-row"
                @click="router.push('/exam-system/practice/favorites')"
              >
                <span class="task-type">收藏</span>
                <div>
                  <strong>收藏题练习</strong>
                  <small>{{ favorites.length }} 道收藏题 · 适合集中巩固</small>
                </div>
                <em>开始练习</em>
              </button>

              <div v-if="!wrongQuestions.length && !favorites.length && !loading" class="empty-panel">
                <strong>还没有可练习的题目</strong>
                <span>完成老师发布的考试后，错题会自动沉淀；收藏的题目也会出现在这里。</span>
              </div>
            </div>
          </div>

          <div v-show="activeView === 'exam'" class="view-panel">
            <div class="section-title">
              <h2>正式考试</h2>
              <span>{{ loading ? '正在同步' : '已同步' }}</span>
            </div>

            <div class="task-list">
              <button v-for="paper in filteredPapers" :key="paper.id" type="button" class="task-row" @click="startExam(paper)">
                <span class="task-type">考试</span>
                <div>
                  <strong>{{ paper.title }}</strong>
                  <small>{{ paper.durationMinutes }} 分钟 · {{ paper.passScore || 60 }} 分及格</small>
                </div>
                <em>进入考试</em>
              </button>

              <div v-if="!filteredPapers.length && !loading" class="empty-panel">
                <strong>暂无已发布考试</strong>
                <span>老师发布后会显示在这里。</span>
              </div>
            </div>
          </div>

          <div v-show="activeView === 'wrong'" class="view-panel">
            <div class="section-title">
              <h2>错题沉淀</h2>
              <span>错题和收藏统一复习</span>
            </div>

            <div class="task-list">
              <button type="button" class="task-row" @click="router.push('/exam-system/wrong-book')">
                <span class="task-type">错题</span>
                <div>
                  <strong>错题本</strong>
                  <small>{{ wrongQuestions.length }} 道错题 · 可查看答案与解析</small>
                </div>
                <em>复盘</em>
              </button>
              <button type="button" class="task-row" @click="router.push('/exam-system/favorites')">
                <span class="task-type">收藏</span>
                <div>
                  <strong>收藏题</strong>
                  <small>{{ favorites.length }} 道重点题</small>
                </div>
                <em>查看</em>
              </button>
            </div>
          </div>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '../components/base/BaseButton.vue'
import request from '../utils/request'

const router = useRouter()
const loading = ref(false)
const papers = ref([])
const wrongQuestions = ref([])
const favorites = ref([])
const activeView = ref('training')

const views = [
  { label: '训练中心', value: 'training' },
  { label: '正式考试', value: 'exam' },
  { label: '错题沉淀', value: 'wrong' }
]

const filteredPapers = computed(() => papers.value)

onMounted(fetchData)

async function fetchData() {
  loading.value = true
  try {
    const [paperRes, wrongRes, favoriteRes] = await Promise.all([
      request.get('/api/exams'),
      request.get('/api/exams/wrong-questions'),
      request.get('/api/exams/favorites')
    ])
    papers.value = paperRes.data || []
    wrongQuestions.value = wrongRes.data || []
    favorites.value = favoriteRes.data || []
    if (!wrongQuestions.value.length && !favorites.value.length && papers.value.length) {
      activeView.value = 'exam'
    }
  } finally {
    loading.value = false
  }
}

function startExam(paper) {
  router.push({ name: 'ExamTaking', params: { paperId: paper.id } })
}
</script>

<style>
.exam-page {
  min-height: calc(100vh - var(--header-height));
  background: transparent;
}

.exam-page__inner {
  width: 100%;
  margin: 0 auto;
  padding: 0 0 var(--ds-space-6, 24px);
  display: grid;
  gap: 18px;
}

.exam-hero,
.task-queue,
.exam-switcher,
.filter-panel,
.main-panel,
.insight-panel,
.set-card,
.exam-card,
.wrong-card,
.empty-panel {
  border: 1px solid var(--orep-border-soft);
  background: var(--orep-surface-raised);
  box-shadow: none;
}

.exam-hero {
  min-height: 304px;
  border-radius: 22px;
  padding: 34px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 36px;
  align-items: center;
  background:
    radial-gradient(circle at 88% 10%, oklch(0.93 0.055 48 / 0.8), transparent 28%),
    linear-gradient(90deg, var(--orep-surface-raised), var(--orep-orange-wash));
  overflow: hidden;
}

.exam-crumb {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.exam-crumb b {
  color: var(--orep-orange);
}

.exam-crumb span {
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: var(--orep-border-soft);
}

.exam-crumb em {
  font-style: normal;
}

.exam-hero h1 {
  margin: 20px 0 14px;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.3;
  letter-spacing: 0;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.exam-hero p {
  max-width: 760px;
  margin: 0;
  color: var(--orep-muted);
  font-size: 15px;
  line-height: 1.78;
}

.exam-hero__actions {
  margin-top: 46px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-hero__actions span,
.exam-switcher > span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 780;
}

.exam-button,
.tiny-button {
  border: 1px solid var(--orep-border-soft);
  border-radius: 9px;
  background: var(--orep-surface-raised);
  color: var(--orep-text-strong);
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}

.exam-button {
  min-height: 40px;
  padding: 0 20px;
  font-size: 14px;
}

.exam-button--primary,
.tiny-button {
  border-color: var(--orep-text-strong);
  background: var(--orep-text-strong);
  color: var(--orep-surface-raised);
}

.tiny-button {
  min-height: 34px;
  padding: 0 14px;
  font-size: 13px;
}

.diagnosis {
  position: relative;
  min-height: 236px;
  border-radius: 22px;
  border: 1px solid oklch(0.91 0.018 55 / 0.72);
  background:
    radial-gradient(circle at 20% 20%, oklch(0.93 0.07 48 / 0.72), transparent 32%),
    linear-gradient(135deg, oklch(0.998 0.004 55 / 0.92), oklch(0.965 0.018 55 / 0.78));
  padding: 22px;
  display: grid;
  gap: 16px;
  box-shadow: 0 24px 70px oklch(0.42 0.08 45 / 0.08);
  overflow: hidden;
  animation: floatIn 520ms var(--orep-ease-out) both;
}

.diagnosis::after {
  content: "";
  position: absolute;
  right: -40px;
  bottom: -70px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  border: 34px solid oklch(0.89 0.04 50 / 0.55);
  opacity: 0.68;
}

.diagnosis > * {
  position: relative;
  z-index: 1;
}

.diagnosis-head,
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
}

.diagnosis h2,
.section-title h2 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 20px;
  line-height: 1.25;
}

.diagnosis-head span,
.section-title span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.diagnosis-core {
  display: grid;
  grid-template-columns: 142px minmax(0, 1fr);
  gap: 20px;
  align-items: center;
}

.accuracy-ring {
  width: 136px;
  height: 136px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  align-content: center;
  background:
    radial-gradient(circle at center, oklch(0.995 0.004 55) 0 56%, transparent 57%),
    conic-gradient(var(--orep-orange) var(--accuracy), oklch(0.89 0.012 55) 0);
  box-shadow:
    inset 0 0 0 1px oklch(0.91 0.014 55),
    0 20px 44px oklch(0.42 0.08 45 / 0.12);
  animation: ringSettle 720ms var(--orep-ease-out) both;
}

.accuracy-ring strong,
.accuracy-ring span {
  display: block;
  text-align: center;
}

.accuracy-ring strong {
  color: var(--orep-text-strong);
  font-size: 32px;
  line-height: 1;
}

.accuracy-ring span {
  margin-top: 7px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 820;
}

.diagnosis-copy p {
  margin: 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.7;
  font-weight: 760;
}

.score-chip {
  width: fit-content;
  min-height: 42px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 0 14px;
  background: var(--orep-text-strong);
  color: var(--orep-surface-raised);
}

.score-chip span {
  color: oklch(0.86 0.01 55);
  font-size: 12px;
  font-weight: 820;
}

.score-chip strong {
  font-size: 20px;
  line-height: 1;
}

.diagnosis-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.diagnosis-stats div {
  min-height: 60px;
  border-radius: 14px;
  background: oklch(1 0 0 / 0.62);
  display: grid;
  align-content: center;
  gap: 5px;
  padding: 10px 12px;
}

.diagnosis-stats span,
.diagnosis-tags span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 820;
}

.diagnosis-stats strong {
  color: var(--orep-text-strong);
  font-size: 22px;
  line-height: 1;
}

.diagnosis-stats .orange {
  color: var(--orep-orange);
}

.diagnosis-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.diagnosis-tags b,
.tag-row small,
.status {
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
}

.diagnosis-tags b {
  min-height: 24px;
  border: 1px solid oklch(0.88 0.025 55);
  background: oklch(1 0 0 / 0.62);
  color: var(--orep-muted);
  padding: 0 9px;
}

.task-queue {
  position: relative;
  border-radius: 18px;
  padding: 16px 18px;
  display: grid;
  grid-template-columns: 210px repeat(3, minmax(0, 1fr));
  gap: 0;
  align-items: center;
  background:
    radial-gradient(circle at 8% 15%, oklch(0.96 0.055 55 / 0.78), transparent 30%),
    linear-gradient(90deg, oklch(0.99 0.018 55), oklch(0.985 0.012 55));
  overflow: hidden;
}

.task-queue::before {
  content: "";
  position: absolute;
  left: 0;
  top: 18px;
  bottom: 18px;
  width: 4px;
  border-radius: 0 999px 999px 0;
  background: var(--orep-orange);
}

.task-title {
  position: relative;
  display: grid;
  align-content: center;
  gap: 7px;
  min-height: 70px;
  padding: 0 18px 0 12px;
}

.task-title h2 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 20px;
  line-height: 1.2;
}

.task-title span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 780;
  line-height: 1.55;
}

.task-title::after {
  content: "提醒";
  width: fit-content;
  min-height: 24px;
  border-radius: 999px;
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
  display: inline-flex;
  align-items: center;
  padding: 0 9px;
  font-size: 12px;
  font-weight: 900;
}

.queue-item {
  position: relative;
  min-height: 66px;
  border: 0;
  border-left: 1px solid oklch(0.9 0.018 55);
  border-radius: 0;
  background: transparent;
  color: inherit;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  text-align: left;
  cursor: pointer;
  box-shadow: none;
  transition: background 160ms var(--orep-ease-out), color 160ms var(--orep-ease-out);
}

.queue-item:hover {
  background: oklch(1 0 0 / 0.38);
}

.queue-item i {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: oklch(0.965 0.028 55);
  color: var(--orep-orange);
  display: grid;
  place-items: center;
  font-style: normal;
  font-weight: 900;
  font-size: 13px;
}

.queue-item strong,
.queue-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-item strong {
  color: var(--orep-text-strong);
  font-size: 14px;
  line-height: 1.25;
}

.queue-item small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.queue-item em {
  min-height: 24px;
  border-radius: 999px;
  background: oklch(1 0 0 / 0.68);
  border: 1px solid oklch(0.91 0.018 55);
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  font-style: normal;
  font-size: 12px;
  font-weight: 820;
  white-space: nowrap;
}

.queue-item:first-of-type {
  background: linear-gradient(90deg, oklch(1 0 0 / 0.52), transparent);
}

.queue-item:first-of-type em {
  background: var(--orep-orange);
  border-color: var(--orep-orange);
  color: white;
}

.queue-item:first-of-type i {
  background: var(--orep-orange);
  color: white;
  box-shadow: 0 8px 18px oklch(0.68 0.16 48 / 0.22);
}

.exam-switcher {
  min-height: 66px;
  border-radius: 18px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.exam-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.exam-tab {
  min-height: 38px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  background: oklch(0.982 0.004 55);
  color: var(--orep-muted);
  padding: 0 16px;
  font: inherit;
  font-size: 14px;
  font-weight: 860;
  cursor: pointer;
}

.exam-tab.active {
  border-color: var(--orep-text-strong);
  background: var(--orep-text-strong);
  color: var(--orep-surface-raised);
}

.exam-content {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.exam-content--single {
  grid-template-columns: minmax(0, 1fr);
}

.filter-panel {
  position: sticky;
  top: calc(var(--header-height) + 18px);
  border-radius: 18px;
  padding: 18px;
}

.filter-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.filter-head h2 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 20px;
}

.filter-head span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.search-box input {
  width: 100%;
  height: 40px;
  border: 0;
  border-radius: 10px;
  background: oklch(0.972 0.007 55);
  color: var(--orep-text-strong);
  padding: 0 12px;
  font: inherit;
  outline: none;
  margin-bottom: 14px;
}

.filter-tree {
  border-top: 1px solid var(--orep-border-soft);
  display: grid;
  gap: 10px;
  padding-top: 14px;
}

.tree-group {
  display: grid;
  gap: 8px;
}

.tree-root,
.tree-leaf {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--orep-text-strong);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font: inherit;
  cursor: pointer;
  text-align: left;
}

.tree-root {
  min-height: 32px;
  border-radius: 9px;
  padding: 0 6px;
  font-size: 14px;
  font-weight: 920;
}

.tree-root::before {
  content: "";
  width: 6px;
  height: 6px;
  border-right: 2px solid var(--orep-muted);
  border-bottom: 2px solid var(--orep-muted);
  margin-right: 8px;
  transform: rotate(45deg) translateY(-1px);
}

.tree-root span {
  flex: 1;
}

.tree-root b,
.tree-leaf b {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 900;
}

.tree-children {
  position: relative;
  display: grid;
  gap: 4px;
  margin-left: 9px;
  padding-left: 14px;
}

.tree-children::before {
  content: "";
  position: absolute;
  top: 4px;
  bottom: 8px;
  left: 0;
  width: 1px;
  background: oklch(0.9 0.011 55);
}

.tree-leaf {
  position: relative;
  min-height: 34px;
  border-radius: 9px;
  padding: 0 10px;
  color: var(--orep-muted);
  font-size: 14px;
  font-weight: 820;
}

.tree-leaf::before {
  content: "";
  position: absolute;
  left: -14px;
  top: 50%;
  width: 10px;
  height: 1px;
  background: oklch(0.9 0.011 55);
}

.tree-leaf.active {
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
}

.tree-leaf.active::after {
  content: "";
  position: absolute;
  left: -18px;
  top: 50%;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--orep-orange);
  transform: translateY(-50%);
}

.tree-leaf.active b {
  color: var(--orep-orange);
}

.filter-group {
  border-top: 1px solid var(--orep-border-soft);
  padding-top: 14px;
  margin-top: 14px;
}

.filter-group strong {
  display: flex;
  justify-content: space-between;
  color: var(--orep-text-strong);
  font-size: 14px;
  margin-bottom: 10px;
}

.filter-group button {
  width: 100%;
  min-height: 34px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--orep-muted);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 10px;
  font: inherit;
  font-size: 14px;
  font-weight: 820;
  cursor: pointer;
}

.filter-group button.active {
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
}

.main-panel {
  border-radius: 18px;
  padding: 20px;
}

.view-panel {
  display: grid;
  gap: 16px;
}

.training-top {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: var(--ds-space-5);
}

.recommend-card {
  min-height: 190px;
  border-radius: 16px;
  background:
    radial-gradient(circle at 85% 20%, oklch(0.9 0.08 50 / 0.7), transparent 30%),
    var(--orep-orange-wash);
  padding: 20px;
  display: grid;
  align-content: space-between;
}

.recommend-card span,
.card-kicker {
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 900;
}

.recommend-card h3 {
  margin: 12px 0 8px;
  color: var(--orep-text-strong);
  font-size: 27px;
  line-height: 1.22;
}

.recommend-card p,
.set-card p,
.exam-card p,
.wrong-card p {
  margin: 0;
  color: var(--orep-muted);
  line-height: 1.65;
}

.training-status {
  min-height: 190px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 16px;
  background:
    linear-gradient(180deg, oklch(1 0 0 / 0.72), oklch(0.99 0.006 55)),
    var(--orep-surface-raised);
  padding: 18px;
  display: grid;
  align-content: space-between;
  gap: 14px;
}

.training-status__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.training-status__head span,
.training-status__stats span {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 850;
}

.training-status__head strong {
  color: var(--orep-text-strong);
  font-size: 36px;
  line-height: 1;
}

.training-status__bar {
  height: 8px;
  border-radius: 999px;
  background: oklch(0.91 0.012 55);
  overflow: hidden;
}

.training-status__bar i {
  height: 100%;
  border-radius: inherit;
  display: block;
  background: var(--ds-orange);
}

.training-status p {
  margin: 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.65;
  font-weight: 760;
}

.training-status__stats {
  border-top: 1px solid var(--orep-border-soft);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding-top: 12px;
}

.training-status__stats button {
  min-height: 42px;
  border: 1px solid oklch(0.91 0.016 55);
  border-radius: 12px;
  background: oklch(0.99 0.006 55);
  color: inherit;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  font: inherit;
  cursor: pointer;
  text-align: left;
  transition: background 160ms var(--orep-ease-out), border-color 160ms var(--orep-ease-out), transform 160ms var(--orep-ease-out);
}

.training-status__stats button:hover {
  border-color: oklch(0.84 0.06 55);
  background: var(--orep-orange-wash);
  transform: translateY(-1px);
}

.training-status__stats strong {
  color: var(--orep-text-strong);
  font-size: 20px;
  line-height: 1;
}

.training-status__stats i {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--orep-surface-raised);
  color: var(--orep-orange);
  display: grid;
  place-items: center;
  font-style: normal;
  font-size: 18px;
  font-weight: 900;
  line-height: 1;
}

.set-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.set-card,
.exam-card,
.wrong-card {
  border-radius: 16px;
  padding: 18px;
  min-height: 214px;
  display: grid;
  align-content: space-between;
  transition: transform 160ms var(--orep-ease-out), box-shadow 160ms var(--orep-ease-out);
}

.set-card:hover,
.exam-card:hover,
.wrong-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px oklch(0.2 0.015 45 / 0.07);
}

.set-card h3,
.exam-card h3,
.wrong-card h3 {
  margin: 12px 0 8px;
  color: var(--orep-text-strong);
  font-size: 20px;
  line-height: 1.28;
}

.tag-row {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.tag-row small {
  min-height: 26px;
  background: oklch(0.972 0.007 55);
  color: var(--orep-muted);
  padding: 0 9px;
  font-weight: 780;
}

.card-foot {
  margin-top: 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-foot span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.exam-list {
  display: grid;
  gap: 12px;
}

.exam-card {
  min-height: 136px;
  grid-template-columns: minmax(0, 1fr) 180px;
  align-items: center;
  gap: 18px;
}

.exam-status {
  justify-self: end;
  display: grid;
  gap: 8px;
  justify-items: end;
}

.status {
  min-height: 28px;
  padding: 0 10px;
  font-weight: 900;
  background: oklch(0.972 0.007 55);
  color: var(--orep-muted);
}

.status.open {
  background: oklch(0.93 0.06 150);
  color: var(--orep-green);
}

.wrong-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 14px;
}

.wrong-stack {
  display: grid;
  gap: 14px;
}

.wrong-card {
  min-height: 160px;
}

.insight-panel {
  border-radius: 18px;
  padding: 18px;
}

.insight-panel h3 {
  margin: 0 0 16px;
  color: var(--orep-text-strong);
  font-size: 20px;
}

.insight-list {
  display: grid;
  gap: 12px;
}

.insight-item {
  min-height: 54px;
  border-radius: 12px;
  background: oklch(0.972 0.007 55);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px;
}

.insight-item strong,
.insight-item span {
  display: block;
}

.insight-item strong {
  color: var(--orep-text-strong);
}

.insight-item span {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
}

.insight-item b {
  color: var(--orep-orange);
}

.empty-panel {
  border-radius: 16px;
  padding: 38px;
  text-align: center;
}

.empty-panel strong,
.empty-panel span {
  display: block;
}

.empty-panel strong {
  color: var(--orep-text-strong);
  font-size: 18px;
}

.empty-panel span {
  margin-top: 8px;
  color: var(--orep-muted);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1180px) {
  .exam-hero,
  .task-queue,
  .exam-content,
  .training-top,
  .wrong-layout {
    grid-template-columns: 1fr;
  }

  .filter-panel {
    position: static;
  }

  .set-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-title {
    border-right: 0;
    border-bottom: 1px solid var(--orep-border-soft);
    padding-right: 0;
    padding-bottom: 12px;
  }
}

@media (max-width: 760px) {
  .exam-page__inner {
    padding: 0 0 var(--ds-space-6, 24px);
  }

  .exam-hero {
    padding: 24px;
  }

  .exam-hero h1 {
    font-size: 24px;
    font-weight: 700;
  letter-spacing: -0.02em;
}

  .exam-switcher,
  .exam-card {
    grid-template-columns: 1fr;
  }

  .exam-switcher {
    align-items: flex-start;
    flex-direction: column;
  }

  .set-grid,
  .training-status__stats,
  .diagnosis-core,
  .diagnosis-stats {
    grid-template-columns: 1fr;
  }
}

@keyframes floatIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes ringSettle {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .diagnosis,
  .accuracy-ring {
    animation: none;
  }
}

/* Workspace visual normalization: match CourseLearning page. */
.exam-page {
  min-height: 100%;
  background: transparent;
}

.exam-page__inner {
  width: 100%;
  padding: 0 0 var(--ds-space-6, 24px);
  box-sizing: border-box;
}

.exam-hero {
  border: 0;
  border-radius: 0;
  padding: 0 0 16px;
  min-height: 104px;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 420px);
  gap: clamp(18px, 2vw, 28px);
  background: transparent;
  box-shadow: none;
  overflow: visible;
}

.exam-hero::before,
.diagnosis::after,
.task-queue::before,
.task-title::after {
  display: none;
}

.exam-crumb {
  margin-bottom: 8px;
  color: var(--workspace-orange-600);
  font-size: 12px;
  font-weight: 800;
}

.exam-hero h1 {
  margin: 0;
  color: var(--workspace-ink-900);
  font-size: 24px;
  font-weight: 800;
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.exam-hero p {
  max-width: 760px;
  margin-top: 7px;
  color: var(--workspace-ink-500);
  font-size: clamp(12px, 0.8vw, 14px);
  font-weight: 600;
  line-height: 1.65;
}

.exam-hero__actions {
  margin-top: 16px;
}

.exam-hero__actions span,
.exam-switcher > span {
  color: var(--workspace-ink-500);
  font-size: 12px;
  font-weight: 650;
}

.diagnosis,
.task-queue,
.exam-switcher,
.filter-panel,
.main-panel,
.recommend-card,
.training-status,
.set-card,
.exam-card,
.wrong-card,
.insight-panel,
.empty-panel {
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: var(--workspace-radius-card);
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(255, 251, 247, 0.52));
  box-shadow: var(--workspace-shadow-soft), inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.diagnosis {
  min-height: 0;
  padding: 18px;
  animation: none;
}

.diagnosis-core {
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 14px;
}

.accuracy-ring {
  width: 92px;
  height: 92px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.82);
  animation: none;
}

.accuracy-ring strong {
  font-size: 22px;
}

.accuracy-ring span,
.diagnosis-copy p,
.diagnosis-stats span,
.diagnosis-tags span,
.section-title span,
.queue-item small,
.task-title span {
  color: var(--workspace-ink-500);
  font-size: 12px;
  font-weight: 650;
}

.diagnosis h2,
.section-title h2,
.task-title h2,
.filter-head h2,
.insight-panel h3 {
  color: var(--workspace-ink-900);
  font-size: clamp(15px, 0.95vw, 17px);
  font-weight: 800;
  line-height: 1.3;
}

.score-chip {
  min-height: 34px;
  margin-top: 10px;
  color: #fff;
  background: var(--ds-orange-action);
}

.task-queue {
  grid-template-columns: 190px repeat(3, minmax(0, 1fr));
  margin-top: 0;
  padding: 14px 16px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(255, 251, 247, 0.52));
}

.queue-item {
  border-left: 1px solid rgba(219, 205, 194, 0.42);
}

.queue-item i,
.queue-item:first-of-type i {
  color: var(--workspace-orange-600);
  background: var(--workspace-orange-50);
  box-shadow: none;
}

.queue-item strong,
.set-card h3,
.exam-card h3,
.wrong-card h3,
.insight-item strong {
  color: var(--workspace-ink-900);
  font-size: 14px;
  font-weight: 800;
}

.queue-item:first-of-type,
.queue-item:hover {
  background: rgba(255, 247, 243, 0.55);
}

.queue-item:first-of-type em,
.status.open {
  background: var(--ds-orange-action);
  border-color: var(--workspace-orange-600);
  color: #fff;
}

.exam-switcher {
  min-height: 58px;
  padding: 10px 16px;
}

.exam-tab {
  min-height: 34px;
  border-color: rgba(255, 255, 255, 0.82);
  background: rgba(255, 255, 255, 0.64);
  color: var(--workspace-ink-500);
  font-size: 13px;
  font-weight: 750;
}

.exam-tab.active {
  border-color: var(--workspace-orange-600);
  background: var(--ds-orange-action);
  color: #fff;
}

.exam-content {
  grid-template-columns: clamp(232px, 15vw, 280px) minmax(0, 1fr);
  gap: clamp(16px, 1.4vw, 22px);
}

.filter-panel,
.main-panel {
  border-radius: var(--workspace-radius-card);
}

.search-box input,
.tree-leaf.active,
.diagnosis-stats div,
.insight-item {
  background: rgba(255, 247, 243, 0.68);
}

.tree-root,
.tree-leaf {
  color: var(--workspace-ink-700);
  font-size: 13px;
  font-weight: 750;
}

.tree-leaf.active {
  color: var(--workspace-orange-600);
}

.exam-button,
.tiny-button {
  min-height: 38px;
  border-radius: var(--workspace-radius-md);
  padding: 0 16px;
  border: 1px solid rgba(255, 255, 255, 0.82);
  background: rgba(255, 255, 255, 0.64);
  color: var(--workspace-ink-700);
  font-size: 13px;
  font-weight: 800;
}

.exam-button--primary,
.tiny-button {
  border-color: var(--workspace-orange-600);
  background: var(--ds-orange-action);
  color: #fff;
  box-shadow: 0 10px 20px rgba(240, 75, 24, 0.16);
}

.recommend-card,
.training-status,
.set-card,
.exam-card,
.wrong-card,
.insight-panel {
  padding: 18px;
}

.tag-row small,
.diagnosis-tags b,
.status {
  border-color: rgba(255, 174, 142, 0.3);
  color: var(--workspace-orange-600);
  background: var(--workspace-orange-50);
}

@media (max-width: 1180px) {
  .exam-hero,
  .task-queue,
  .exam-content,
  .training-top,
  .wrong-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .exam-page__inner {
    padding: 0 0 var(--ds-space-6, 24px);
  }

  .exam-hero {
    padding: 0 0 16px;
  }

  .exam-hero h1 {
    font-size: 24px;
    font-weight: 700;
  letter-spacing: -0.02em;
}
}

/* Compact redesign: keep the page quiet and close to CourseLearning. */
.exam-page__inner {
  display: grid;
  gap: 16px;
  padding: 0 0 var(--ds-space-6, 24px);
}

.exam-hero {
  display: block;
  min-height: 0;
  padding: 0 0 10px;
  margin: 0;
}

.exam-crumb {
  margin-bottom: 6px;
  font-size: 11px;
}

.exam-hero h1 {
  font-size: 24px;
  line-height: 1.3;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.exam-hero p {
  max-width: 860px;
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.exam-hero__actions {
  margin-top: 12px;
  gap: 10px;
}

.diagnosis {
  display: none;
}

.task-queue {
  grid-template-columns: 170px repeat(3, minmax(0, 1fr));
  gap: 0;
  min-height: 72px;
  padding: 0;
  overflow: hidden;
}

.task-title {
  min-height: 72px;
  padding: 12px 16px;
  border-right: 1px solid rgba(219, 205, 194, 0.42);
}

.task-title h2 {
  font-size: 15px;
}

.task-title span {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.queue-item {
  min-height: 72px;
  padding: 10px 14px;
}

.queue-item i {
  width: 28px;
  height: 28px;
  font-size: 12px;
}

.queue-item strong {
  font-size: 13px;
}

.queue-item em {
  min-height: 22px;
  font-size: 11px;
}

.exam-switcher {
  min-height: 52px;
  padding: 8px 14px;
}

.exam-switcher > span {
  max-width: 620px;
  text-align: right;
}

.exam-content {
  align-items: stretch;
}

.filter-panel {
  padding: 16px;
}

.main-panel {
  padding: 18px;
}

.section-title {
  margin-bottom: 14px;
}

.training-top {
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 14px;
}

.recommend-card,
.training-status,
.set-card,
.exam-card,
.wrong-card,
.insight-panel {
  min-height: 0;
  padding: 16px;
}

.recommend-card h3,
.set-card h3,
.exam-card h3,
.wrong-card h3 {
  margin-top: 6px;
  font-size: 18px;
  line-height: 1.3;
}

.recommend-card p,
.set-card p,
.exam-card p,
.wrong-card p,
.training-status p {
  font-size: 13px;
  line-height: 1.65;
}

.training-status__head strong {
  font-size: 24px;
}

.training-status__stats button {
  min-height: 46px;
  border-radius: 14px;
}

.set-grid {
  gap: 14px;
}

@media (max-width: 1180px) {
  .task-queue,
  .training-top {
    grid-template-columns: 1fr;
  }

  .task-title,
  .queue-item {
    border-right: 0;
    border-bottom: 1px solid rgba(219, 205, 194, 0.42);
  }
}

/* Minimal exam layout: fewer cards, shorter copy, consistent small type. */
.exam-page__inner {
  max-width: 100%;
  gap: 14px;
  padding-top: 20px;
  padding: 0 0 var(--ds-space-6, 24px);
}

.exam-hero {
  padding-bottom: 4px;
}

.exam-crumb {
  display: none;
}

.exam-hero h1 {
  font-size: 24px;
  font-weight: 800;
}

.exam-hero p {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.exam-hero__actions {
  margin-top: 12px;
}

.task-queue {
  display: none;
}

.exam-switcher {
  min-height: 48px;
  padding: 7px 10px;
  border-radius: 14px;
  box-shadow: none;
}

.exam-switcher > span {
  font-size: 12px;
}

.exam-tab {
  min-height: 32px;
  padding: 0 14px;
  font-size: 13px;
}

.exam-content {
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 14px;
}

.filter-panel,
.main-panel {
  border-radius: 16px;
  box-shadow: none;
}

.filter-panel {
  padding: 14px;
}

.filter-head {
  margin-bottom: 10px;
}

.filter-head h2,
.section-title h2,
.insight-panel h3 {
  font-size: 15px;
}

.filter-head span,
.section-title span {
  font-size: 12px;
}

.search-box input {
  height: 34px;
  margin-bottom: 10px;
  font-size: 13px;
}

.filter-tree {
  gap: 8px;
  padding-top: 10px;
}

.tree-root,
.tree-leaf {
  min-height: 30px;
  font-size: 13px;
}

.main-panel {
  padding: 16px;
}

.view-panel {
  gap: 12px;
}

.section-title {
  margin-bottom: 0;
}

.training-top {
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.recommend-card,
.training-status,
.set-card,
.exam-card,
.wrong-card,
.insight-panel {
  border-radius: 14px;
  box-shadow: none;
}

.recommend-card {
  min-height: 112px;
  padding: 16px 18px;
  background: rgba(255, 247, 243, 0.62);
}

.recommend-card h3 {
  margin: 4px 0 0;
  font-size: 18px;
}

.recommend-card p,
.set-card p,
.wrong-card p,
.exam-card p,
.tag-row {
  display: none;
}

.card-foot {
  margin-top: 12px;
}

.training-status {
  min-height: 0;
  padding: 12px 14px;
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
}

.training-status__head {
  display: block;
}

.training-status__head span {
  display: block;
  margin-bottom: 5px;
}

.training-status__head strong {
  font-size: 20px;
}

.training-status p {
  display: none;
}

.training-status__stats {
  border-top: 0;
  grid-template-columns: repeat(2, 96px);
  gap: 8px;
  padding-top: 0;
}

.training-status__stats button {
  min-height: 38px;
  border-radius: 10px;
}

.training-status__stats strong {
  font-size: 16px;
}

.set-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.5);
}

.set-card {
  min-height: 58px;
  border: 0;
  border-radius: 0;
  border-bottom: 1px solid rgba(219, 205, 194, 0.42);
  background: transparent;
  padding: 12px 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.set-card:last-child {
  border-bottom: 0;
}

.set-card:hover,
.exam-card:hover,
.wrong-card:hover {
  transform: none;
  box-shadow: none;
}

.set-card h3,
.exam-card h3,
.wrong-card h3 {
  margin: 3px 0 0;
  font-size: 15px;
}

.card-kicker,
.recommend-card span {
  font-size: 11px;
}

.set-card .card-foot {
  margin-top: 0;
}

.set-card .card-foot span {
  display: none;
}

.exam-card,
.wrong-card {
  min-height: 86px;
  padding: 14px 16px;
}

.exam-card {
  grid-template-columns: minmax(0, 1fr) auto;
}

.wrong-layout {
  grid-template-columns: minmax(0, 1fr);
}

.insight-panel {
  display: none;
}

.exam-button,
.tiny-button {
  min-height: 34px;
  padding: 0 14px;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .exam-content,
  .training-status {
    grid-template-columns: 1fr;
  }

  .training-status__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Final task-page redesign. */
.exam-page {
  min-height: 100%;
  background: transparent;
}

.exam-page__inner {
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 0 0 var(--ds-space-6, 24px);
  display: grid;
  gap: 14px;
  box-sizing: border-box;
}

.exam-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--ds-space-6);
  align-items: end;
}

.exam-title-block h1 {
  margin: 0;
  color: var(--workspace-ink-900);
  font-size: 24px;
  font-weight: var(--ds-weight-bold);
  line-height: 1.3;
  letter-spacing: -0.01em;
}

.exam-title-block p {
  margin: 6px 0 0;
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-medium);
  line-height: 1.5;
}

.exam-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
  margin-top: var(--ds-space-3);
}

.exam-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(76px, 1fr));
  gap: var(--ds-space-2);
  min-width: 286px;
}

.exam-metrics div {
  min-height: 58px;
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-card-bg);
  display: grid;
  align-content: center;
  gap: 4px;
  padding: 8px 12px;
}

.exam-metrics strong {
  color: var(--workspace-ink-900);
  font-size: 18px;
  line-height: 1;
}

.exam-metrics span,
.current-task__copy span,
.current-task__copy p,
.section-title span,
.task-row small,
.filter-head span,
.tree-root b,
.tree-leaf b,
.empty-panel span {
  color: var(--workspace-ink-500);
  font-size: 12px;
  font-weight: 650;
}

.current-task {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px) auto;
  gap: 18px;
  align-items: center;
  padding: 16px 18px;
  box-shadow: var(--ds-card-shadow);
}

.current-task__copy h2 {
  margin: 4px 0 5px;
  color: var(--workspace-ink-900);
  font-size: 17px;
  font-weight: 800;
  line-height: 1.28;
}

.current-task__copy span,
.task-row--primary .task-type {
  color: var(--workspace-orange-600);
}

.current-task__progress {
  display: grid;
  gap: 8px;
}

.current-task__progress span {
  color: var(--workspace-ink-700);
  font-size: 13px;
  font-weight: 800;
}

.current-task__progress i {
  height: 8px;
  border-radius: 999px;
  background: rgba(219, 205, 194, 0.46);
  overflow: hidden;
}

.current-task__progress b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ds-orange);
}

.exam-switcher {
  min-height: 44px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
  display: flex;
  align-items: center;
}

.exam-tabs {
  display: inline-flex;
  gap: var(--ds-space-2);
  padding: var(--ds-space-1);
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-pill);
  background: var(--ds-card-bg);
}

.exam-content {
  display: grid;
  grid-template-columns: 226px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.exam-content--single {
  grid-template-columns: minmax(0, 1fr);
}

.filter-panel,
.main-panel {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.filter-panel {
  position: sticky;
  top: 16px;
  padding: 14px;
}

.filter-head,
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}

.filter-head h2,
.section-title h2 {
  margin: 0;
  color: var(--workspace-ink-900);
  font-size: 15px;
  font-weight: 800;
}

.search-box input {
  width: 100%;
  height: 34px;
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  background: var(--ds-input-bg);
  color: var(--workspace-ink-900);
  padding: 0 11px;
  margin: 12px 0;
  font: inherit;
  font-size: 13px;
  outline: none;
}

.search-box input:hover {
  border-color: var(--ds-input-border-hover);
}

.search-box input:focus-visible {
  border-color: var(--ds-input-focus-border);
  box-shadow: var(--ds-input-focus-ring);
}

.filter-tree,
.tree-group,
.tree-children,
.view-panel,
.task-list {
  display: grid;
}

.filter-tree {
  gap: 10px;
}

.tree-group {
  gap: 6px;
}

.tree-root,
.tree-leaf {
  width: 100%;
  min-height: 30px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--workspace-ink-700);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 9px;
  font: inherit;
  font-size: 13px;
  font-weight: 760;
  cursor: pointer;
}

.tree-root {
  font-weight: 820;
}

.tree-children {
  gap: 2px;
  margin-left: 8px;
  padding-left: 10px;
  border-left: 1px solid rgba(219, 205, 194, 0.6);
}

.tree-leaf.active {
  background: var(--ds-btn-selected-bg);
  color: var(--ds-btn-selected-fg);
  box-shadow: inset 0 0 0 1px var(--ds-btn-selected-border);
}

.tree-leaf.active b {
  color: var(--workspace-orange-600);
}

.main-panel {
  padding: var(--ds-space-6);
}

.view-panel {
  gap: 12px;
}

.task-list {
  border: 1px solid var(--ds-line);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-solid);
  overflow: hidden;
}

.task-row {
  width: 100%;
  min-height: 64px;
  border: 0;
  border-bottom: 1px solid var(--ds-line);
  background: transparent;
  color: inherit;
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: var(--ds-space-3) var(--ds-space-4);
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.task-row:last-child {
  border-bottom: 0;
}

.task-row:hover {
  background: var(--ds-btn-secondary-bg-hover);
}

.task-row:focus-visible,
.tree-root:focus-visible,
.tree-leaf:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: -2px;
}

.exam-page button:hover,
.exam-page button:active {
  transform: none;
}

.task-row--primary {
  background: var(--ds-orange-wash);
}

.task-type {
  color: var(--workspace-ink-500);
  font-size: 12px;
  font-weight: 800;
}

.task-row strong {
  display: block;
  overflow: hidden;
  color: var(--workspace-ink-900);
  font-size: 15px;
  font-weight: 800;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-row small {
  display: block;
  overflow: hidden;
  margin-top: 4px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-row em {
  min-height: 30px;
  color: var(--ds-btn-selected-fg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--ds-space-2);
  font-style: normal;
  font-size: 12px;
  font-weight: 820;
  white-space: nowrap;
}

.task-row--primary em {
  color: var(--ds-btn-selected-fg);
  background: transparent;
}

.empty-panel {
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 34px;
  text-align: center;
}

.empty-panel strong {
  display: block;
  color: var(--workspace-ink-900);
  font-size: 15px;
}

.empty-panel span {
  display: block;
  margin-top: 6px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 1180px) {
  .exam-header,
  .current-task,
  .exam-content {
    grid-template-columns: 1fr;
  }

  .exam-metrics {
    min-width: 0;
  }

  .filter-panel {
    position: static;
  }
}

@media (max-width: 720px) {
  .exam-page__inner {
    padding: 0 0 var(--ds-space-6, 24px);
  }

  .exam-metrics,
  .task-row {
    grid-template-columns: 1fr;
  }

  .task-row {
    gap: 8px;
    align-items: start;
  }

  .task-row em {
    justify-self: start;
  }
}
</style>

/* TRAINING-CAMP-DS-ALIGN */
.exam-page {
  background: transparent !important;
}
.exam-page__inner {
  width: 100% !important;
  max-width: none !important;
  margin: 0 !important;
  padding: 0 0 var(--ds-space-6, 24px) !important;
}
.exam-hero h1,
.exam-title-block h1 {
  font-size: 24px !important;
  line-height: 1.3 !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
}
.exam-hero p,
.exam-title-block p {
  margin-top: 6px !important;
  font-size: 13px !important;
  line-height: 1.55 !important;
}
.exam-button {
  min-height: var(--ds-btn-height, 40px) !important;
  height: var(--ds-btn-height, 40px) !important;
  padding: 0 var(--ds-btn-padding-x, 18px) !important;
  border-radius: var(--ds-radius-pill, 999px) !important;
  font-size: var(--ds-btn-font, 14px) !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}
.exam-button--primary,
.exam-button.exam-button--primary {
  border: 1px solid var(--ds-btn-primary-bg, #e84a1c) !important;
  background: var(--ds-btn-primary-bg, #e84a1c) !important;
  color: #fff !important;
}
.exam-button--primary:hover,
.exam-button.exam-button--primary:hover {
  background: var(--ds-btn-primary-bg-hover, #d94319) !important;
  border-color: var(--ds-btn-primary-bg-hover, #d94319) !important;
  color: #fff !important;
}
.exam-button:not(.exam-button--primary) {
  background: #fff !important;
  color: #1d1d1f !important;
  border: 1px solid rgba(29,29,31,.16) !important;
}
.exam-button:not(.exam-button--primary):hover {
  color: #e84a1c !important;
  background: #f5f5f7 !important;
  border-color: rgba(232,74,28,.34) !important;
}
