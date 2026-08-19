<template>
  <QuestionReviewDesk
    title="错题本"
    eyebrow="错题复盘"
    subtitle="把做错的题收束到独立复盘区，按题型筛选、看解析、把重点题加入收藏。"
    metric-label="错题数量"
    empty-title="暂无错题"
    empty-text="完成考试后，系统会把客观题错题自动沉淀到这里。"
    fetch-url="/api/exams/wrong-questions"
    practice-source="wrong"
    accent="orange"
  />
</template>

<script setup>
import QuestionReviewDesk from '../components/exam/QuestionReviewDesk.vue'
</script>
