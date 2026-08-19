<template>
  <div class="empty-state">
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '报告生成后会在这里展示分析结果。' }
})
</script>

<style scoped>
.empty-state {
  display: grid;
  place-items: center;
  min-height: 180px;
  padding: 24px;
  border: 1px dashed #cbd6e8;
  border-radius: 12px;
  background: #f8fbff;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: #0d1b3d;
  font-size: 16px;
}

.empty-state p {
  max-width: 420px;
  margin: 8px 0 0;
  color: #66728a;
  line-height: 1.7;
}
</style>
