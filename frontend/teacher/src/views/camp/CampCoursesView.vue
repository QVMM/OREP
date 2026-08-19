<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>课程</h1>
        <p>
          创建视频课、上传附件与简介，再挂到日任务或全营
          <span v-if="sourceLabel" class="teacher-muted"> · {{ sourceLabel }}</span>
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">刷新</button>
        <button type="button" class="teacher-btn teacher-btn--primary" @click="msg = '完整建课走管理端课程接口，后续在此嵌向导'">
          新建课程
        </button>
      </div>
    </header>
    <p v-if="msg" class="teacher-tag is-info" style="margin-bottom: 12px">{{ msg }}</p>
    <p v-if="error" class="teacher-tag is-warn" style="margin-bottom: 12px">{{ error }}</p>

    <section class="teacher-card">
      <div class="teacher-card__body">
        <div v-if="loading" class="teacher-empty">加载课程…</div>
        <div v-else class="teacher-list">
          <div v-for="c in courses" :key="c.id" class="teacher-list__item">
            <div>
              <strong>{{ c.title }}</strong>
              <small>{{ c.meta }}</small>
            </div>
            <a class="teacher-btn teacher-btn--secondary teacher-btn--sm"
              :href="studentCourseUrl(c.id)"
              target="_blank"
              rel="noopener"
            >学生端预览</a>
          </div>
          <div v-if="!courses.length" class="teacher-empty">暂无课程</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { fetchCourses } from '../../api'
import { studentCourseUrl } from '../../utils/studentApp'

const courses = ref([])
const loading = ref(false)
const error = ref('')
const msg = ref('')
const sourceLabel = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchCourses()
    const rows = Array.isArray(data) ? data : data?.list || data?.records || []
    if (!rows.length) {
      courses.value = []
      sourceLabel.value = '课程库暂无数据'
      return
    }
    courses.value = rows.map((c) => ({
      id: c.id,
      title: c.title || c.name || `课程 ${c.id}`,
      meta: [c.lessonCount != null ? `${c.lessonCount} 课时` : '', c.category || '', c.updatedAt || '']
        .filter(Boolean)
        .join(' · ') || '已上架',
    }))
    sourceLabel.value = '已连接 /api/courses'
  } catch (e) {
    error.value = e.message
    courses.value = []
    sourceLabel.value = '课程数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
