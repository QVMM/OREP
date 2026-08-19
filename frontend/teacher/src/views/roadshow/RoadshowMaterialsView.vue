<template>
  <div class="teacher-page">
    <header class="teacher-page__head"><div><h1>PPT / 讲稿</h1><p>路演材料统一查看 · 学生文件中心同源数据</p></div><router-link class="teacher-btn teacher-btn--primary" to="/resources">新建材料</router-link></header>
    <section class="teacher-card"><div class="teacher-card__head"><h2>路演材料</h2><span>{{ list.length }} 份</span></div><div class="teacher-card__body teacher-list">
      <div v-for="row in list" :key="row.id" class="teacher-list__item"><div><strong>{{ row.name }}</strong><small>{{ row.teamName }} · {{ typeLabel(row.materialType) }} · {{ formatDate(row.updatedAt) }}<template v-if="row.ownerName"> · {{ row.ownerName }}</template></small></div><a v-if="row.fileUrl" class="teacher-btn teacher-btn--secondary teacher-btn--sm" :href="row.fileUrl" target="_blank" rel="noopener">打开</a><span v-else class="teacher-tag is-info">待上传文件</span></div>
      <div v-if="!list.length" class="teacher-empty">暂无 PPT 或讲稿材料</div>
    </div></section>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { fetchTeacherResources } from '../../api'
const list = ref([])
function typeLabel(value) { return ({ PPT: 'PPT', SCRIPT: '讲稿', DOC: '文档', DOCS: '文档' })[value] || value }
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—' }
onMounted(async () => { list.value = (await fetchTeacherResources()).filter((x) => ['PPT', 'SCRIPT', 'DOC', 'DOCS'].includes(x.materialType)) })
</script>
