<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>题库与考试</h1>
        <p>题库维护 · 自定义/智能组卷 · 发布考试任务</p>
      </div>
      <div class="teacher-page__actions">
        <span class="teacher-tag is-info">共 {{ data.questionCount || 0 }} 道可用题目</span>
      </div>
    </header>

    <div class="teacher-split">
      <section class="teacher-card">
        <div class="teacher-card__head"><h2>题库</h2></div>
        <div class="teacher-card__body">
          <table class="teacher-table">
            <thead><tr><th>题库</th><th>题量</th><th>状态</th><th>更新</th></tr></thead>
            <tbody>
              <tr v-for="b in banks" :key="b.id">
                <td>{{ b.name }}</td>
                <td>{{ b.count }}</td>
                <td><span class="teacher-tag">{{ statusLabel(b.status) }}</span></td>
                <td>{{ formatDate(b.updatedAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section class="teacher-card">
        <div class="teacher-card__head"><h2>考试任务</h2></div>
        <div class="teacher-card__body">
          <div class="teacher-list">
            <div v-for="e in data.papers || []" :key="e.id" class="teacher-list__item">
              <div>
                <strong>{{ e.title }}</strong>
                <small>{{ e.questionCount || 0 }} 题 · {{ e.durationMinutes }} 分钟 · 合格 {{ e.passScore }} 分 · {{ e.attemptCount || 0 }} 人作答</small>
              </div>
              <span class="teacher-tag" :class="String(e.status).toLowerCase() === 'published' ? 'is-ok' : 'is-info'">{{ statusLabel(e.status) }}</span>
            </div>
            <div v-if="!(data.papers || []).length" class="teacher-empty">尚无试卷数据</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { fetchTeacherExams } from '../../api'

const data = ref({ questionCount: 0, papers: [] })
const banks = computed(() => [{ id: 'all', name: '平台题库', count: data.value.questionCount || 0, status: '可用', updatedAt: data.value.papers?.[0]?.updatedAt }])
function formatDate(value) { return value ? new Date(value).toLocaleDateString('zh-CN') : '—' }
function statusLabel(value) {
  const map = { published: '已发布', draft: '草稿', disabled: '已停用', active: '可用' }
  const key = String(value || '').toLowerCase()
  if (map[key]) return map[key]
  if (/[\u4e00-\u9fff]/.test(String(value || ''))) return value
  return '未知'
}
onMounted(async () => { data.value = await fetchTeacherExams() })
</script>
