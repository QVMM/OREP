<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>待审队列</h1>
        <p>日任务批改、路演评分确认、AI 待办审核汇到这里</p>
      </div>
    </header>
    <section class="teacher-card">
      <div class="teacher-card__body">
        <div class="teacher-list">
          <router-link v-for="item in items" :key="item.id" :to="item.to" class="teacher-list__item">
            <div>
              <strong>{{ item.title }}</strong>
              <small>{{ item.meta }}</small>
            </div>
            <span class="teacher-tag is-warn">{{ item.badge }}</span>
          </router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
const items = [
  { id: 1, title: '日任务待批改 · 12 份', meta: '集训第 4 天', badge: '批改', to: '/camp/review-queue' },
  { id: 2, title: 'AI 报告待确认 · 报告 #15', meta: '智慧养老 · 64.8 分', badge: '确认', to: '/review/reports' },
  { id: 3, title: 'AI 待办待审 · 5 条', meta: '发布前可改负责人与截止日', badge: '审核', to: '/review/ai-todos' },
]
</script>
