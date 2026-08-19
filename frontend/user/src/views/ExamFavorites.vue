<template>
  <QuestionReviewDesk
    title="收藏题"
    eyebrow="重点题库"
    subtitle="保存个人重点题，考前快速扫一遍题干、答案和解析。"
    metric-label="收藏数量"
    empty-title="暂无收藏"
    empty-text="在考试答题页或错题本里点击收藏后，题目会出现在这里。"
    fetch-url="/api/exams/favorites"
    practice-source="favorites"
    accent="orange"
  />
</template>

<script setup>
import QuestionReviewDesk from '../components/exam/QuestionReviewDesk.vue'
</script>
