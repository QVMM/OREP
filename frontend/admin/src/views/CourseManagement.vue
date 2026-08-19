<template>
  <div class="course-admin admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">课程管理</span>
        <h1>按课程、章节、课时维护学习内容</h1>
        <p>先筛选课程并选中一门课程，再维护章节、视频课时和附件。避免在未选中课程时误传资料。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button type="primary" @click="openCourseDialog()"><el-icon><Plus /></el-icon>新建课程</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ courses.length }}</strong><span>课程总数</span><small>当前显示 {{ filteredCourses.length }} 门</small></article>
      <article class="admin-metric-card"><strong>{{ publishedCourseCount }}</strong><span>已发布</span><small>用户端可见课程</small></article>
      <article class="admin-metric-card"><strong>{{ draftCourseCount }}</strong><span>草稿</span><small>待完善后发布</small></article>
      <article class="admin-metric-card"><strong>{{ selectedCourse ? selectedCourse.chapters?.length || 0 : 0 }}</strong><span>当前课程章节</span><small>{{ selectedCourse?.title || '尚未选择课程' }}</small></article>
    </section>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">课程列表</span>
            <span class="admin-panel-subtitle">点击课程行后，在下方维护该课程的章节、课时和附件。</span>
          </div>
          <div class="admin-panel-actions">
            <el-button type="danger" :disabled="selectedCourses.length === 0" @click="batchDeleteCourses">
              批量删除
            </el-button>
          </div>
        </div>
      </template>

      <div class="admin-filter-bar">
        <el-input v-model.trim="courseKeyword" clearable placeholder="搜索课程名称 / 分类" />
        <el-select v-model="courseStatusFilter" clearable placeholder="发布状态">
          <el-option label="已发布" value="published" />
          <el-option label="草稿" value="draft" />
        </el-select>
        <el-select v-model="courseTypeFilter" clearable placeholder="课程类型">
          <el-option label="必修课" value="required" />
          <el-option label="选修课" value="elective" />
        </el-select>
      </div>

      <el-table
        :data="filteredCourses"
        v-loading="loading"
        border
        stripe
        @row-click="selectCourse"
        @selection-change="selectedCourses = $event"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="title" label="课程名称" min-width="220" />
        <el-table-column prop="courseType" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.courseType === 'elective' ? 'success' : 'warning'">
              {{ row.courseType === 'elective' ? '选修课' : '必修课' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="130" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'">
              {{ row.status === 'published' ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sortOrder" label="排序" width="90" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openCourseDialog(row)">编辑</el-button>
            <el-button link type="danger" @click.stop="deleteCourse(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filteredCourses.length === 0 && !loading" class="admin-empty">没有匹配课程。可以清空筛选条件，或新建课程。</div>
    </el-card>

    <el-card class="admin-panel detail-panel" v-if="selectedCourse">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">{{ selectedCourse.title }}</span>
            <span class="admin-panel-subtitle">{{ selectedCourse.description || selectedCourse.subtitle || '维护课程目录与视频课时' }}</span>
          </div>
          <div class="admin-panel-actions">
            <el-button @click="openChapterDialog">
              <el-icon><FolderAdd /></el-icon>
              新建章节
            </el-button>
            <el-button type="primary" @click="openLessonDialog" :disabled="chapterOptions.length === 0">
              <el-icon><VideoPlay /></el-icon>
              新建课时
            </el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!selectedCourse.chapters?.length" description="暂无章节，请先创建章节" />
      <div v-else class="chapter-list">
        <section v-for="chapter in selectedCourse.chapters" :key="chapter.id" class="chapter-card">
          <div class="chapter-card__head">
            <h3>{{ chapter.title }}</h3>
            <div>
              <el-button link type="primary" @click="openChapterDialog(chapter)">编辑章节</el-button>
              <el-button link type="danger" @click="deleteChapter(chapter)">删除章节</el-button>
            </div>
          </div>
          <el-table :data="chapter.lessons" border>
            <el-table-column prop="title" label="课时名称" min-width="220" />
            <el-table-column label="时长" width="100">
              <template #default="{ row }">{{ formatDuration(row.durationSeconds) }}</template>
            </el-table-column>
            <el-table-column label="视频" min-width="220">
              <template #default="{ row }">
                <span v-if="row.resourceUrl" class="video-ready">已上传：{{ row.videoMimeType || 'video' }}</span>
                <span v-else class="video-missing">未上传视频</span>
              </template>
            </el-table-column>
            <el-table-column label="上传视频" width="220">
              <template #default="{ row }">
                <el-upload
                  :action="`/api/admin/courses/lessons/${row.id}/video`"
                  :headers="uploadHeaders"
                  :data="{ durationSeconds: row.durationSeconds || 0 }"
                  :show-file-list="false"
                  accept=".mp4,.webm,.mov,.m4v,video/*"
                  :before-upload="beforeVideoUpload"
                  :on-success="handleVideoSuccess"
                  :on-error="handleVideoError"
                >
                  <el-button size="small" type="primary" plain>
                    <el-icon><Upload /></el-icon>
                    上传/替换
                  </el-button>
                </el-upload>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button link type="primary" @click="openLessonDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="deleteLesson(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </el-card>

    <el-card class="admin-panel detail-panel" v-if="selectedCourse">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">课程附件</span>
            <span class="admin-panel-subtitle">上传课件、讲义、练习包和参考资料，用户端课程附件会同步展示。</span>
          </div>
          <div class="admin-panel-actions">
            <el-button type="danger" :disabled="selectedAttachments.length === 0" @click="batchDeleteAttachments">
              批量删除
            </el-button>
            <el-upload
              :action="`/api/admin/courses/${selectedCourse.id}/attachments`"
              :headers="uploadHeaders"
              :data="{ sortOrder: nextAttachmentSort }"
              :show-file-list="false"
              accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.rar,.png,.jpg,.jpeg"
              :before-upload="beforeAttachmentUpload"
              :on-success="handleAttachmentSuccess"
              :on-error="handleAttachmentError"
            >
              <el-button type="primary">
                <el-icon><Upload /></el-icon>
                上传附件
              </el-button>
            </el-upload>
          </div>
        </div>
      </template>

      <el-empty v-if="!selectedCourse.attachments?.length" description="暂无课程附件" />
      <el-table v-else :data="selectedCourse.attachments" border @selection-change="selectedAttachments = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="name" label="附件名称" min-width="260" />
        <el-table-column prop="fileType" label="类型" width="100">
          <template #default="{ row }">
            <el-tag>{{ (row.fileType || 'file').toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fileSize" label="大小" width="120" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="previewAttachment(row)">查看</el-button>
            <el-button link type="danger" @click="deleteAttachment(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <div v-else class="admin-empty">请先在课程列表中选择一门课程，再维护章节、课时和附件。</div>

    <el-dialog v-model="courseDialogVisible" :title="courseForm.id ? '编辑课程' : '新建课程'" width="620px">
      <el-form :model="courseForm" label-width="90px">
        <el-form-item label="课程名称"><el-input v-model="courseForm.title" /></el-form-item>
        <el-form-item label="副标题"><el-input v-model="courseForm.subtitle" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="courseForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="课程封面">
          <div class="course-cover-field">
            <div class="course-cover-preview" :class="{ empty: !courseForm.coverUrl }">
              <img v-if="courseForm.coverUrl" :src="coverPreviewSrc(courseForm.coverUrl)" alt="课程封面预览" />
              <span v-else>用于用户端首页课程卡片</span>
            </div>
            <div class="course-cover-actions">
              <el-upload
                :action="courseForm.id ? `/api/admin/courses/${courseForm.id}/cover` : ''"
                :headers="uploadHeaders"
                :show-file-list="false"
                accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                :disabled="!courseForm.id"
                :before-upload="beforeCoverUpload"
                :on-success="handleCoverSuccess"
                :on-error="handleCoverError"
              >
                <el-button type="primary" plain :disabled="!courseForm.id">
                  <el-icon><Upload /></el-icon>
                  上传封面
                </el-button>
              </el-upload>
              <small>{{ courseForm.id ? '支持 JPG、PNG、WebP，建议上传 16:9 横版图。非 16:9 图片会按中心裁切展示，最大 5MB。' : '新建课程需先保存，再上传封面。' }}</small>
              <el-input v-model="courseForm.coverUrl" placeholder="也可填写 /uploads/... 图片地址" />
            </div>
          </div>
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="courseForm.courseType">
            <el-radio-button label="required">必修课</el-radio-button>
            <el-radio-button label="elective">选修课</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分类"><el-input v-model="courseForm.category" /></el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="courseForm.status">
            <el-radio-button label="draft">草稿</el-radio-button>
            <el-radio-button label="published">发布</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="强调色"><el-color-picker v-model="courseForm.accentColor" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="courseForm.sortOrder" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chapterDialogVisible" :title="chapterForm.id ? '编辑章节' : '新建章节'" width="460px">
      <el-form :model="chapterForm" label-width="80px">
        <el-form-item label="章节名"><el-input v-model="chapterForm.title" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="chapterForm.sortOrder" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="lessonDialogVisible" :title="lessonForm.id ? '编辑课时' : '新建课时'" width="520px">
      <el-form :model="lessonForm" label-width="90px">
        <el-form-item label="所属章节">
          <el-select v-model="lessonForm.chapterId" placeholder="选择章节" style="width: 100%">
            <el-option v-for="item in chapterOptions" :key="item.id" :label="item.title" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课时名称"><el-input v-model="lessonForm.title" /></el-form-item>
        <el-form-item label="时长秒数"><el-input-number v-model="lessonForm.durationSeconds" :min="0" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="lessonForm.sortOrder" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="lessonDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveLesson">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FolderAdd, Plus, Upload, VideoPlay } from '@element-plus/icons-vue'
import request from '../api/request'
import { getAdminToken } from '../utils/authStorage'
import { batchDeleteSummary, idsFromRows } from '../utils/batchDelete'

const loading = ref(false)
const courses = ref([])
const selectedCourse = ref(null)
const selectedCourses = ref([])
const selectedAttachments = ref([])
const courseDialogVisible = ref(false)
const chapterDialogVisible = ref(false)
const lessonDialogVisible = ref(false)
const courseKeyword = ref('')
const courseStatusFilter = ref('')
const courseTypeFilter = ref('')

const courseForm = ref(defaultCourseForm())
const chapterForm = ref({ id: null, title: '', sortOrder: 0 })
const lessonForm = ref({ id: null, chapterId: null, title: '', durationSeconds: 0, sortOrder: 0 })

const uploadHeaders = computed(() => ({ Authorization: `Bearer ${getAdminToken()}` }))

function coverPreviewSrc(url) {
  if (!url) return ''
  const token = getAdminToken()
  if (!token || !String(url).includes('/uploads/course-covers/')) return url
  const sep = String(url).includes('?') ? '&' : '?'
  return `${url}${sep}t=${encodeURIComponent(token)}`
}
const chapterOptions = computed(() => selectedCourse.value?.chapters || [])
const nextAttachmentSort = computed(() => (selectedCourse.value?.attachments?.length || 0) * 10 + 10)
const filteredCourses = computed(() => {
  const q = courseKeyword.value.toLowerCase()
  return courses.value.filter((course) => {
    const matchKeyword = !q || `${course.title || ''} ${course.category || ''} ${course.subtitle || ''}`.toLowerCase().includes(q)
    const matchStatus = !courseStatusFilter.value || course.status === courseStatusFilter.value
    const matchType = !courseTypeFilter.value || course.courseType === courseTypeFilter.value
    return matchKeyword && matchStatus && matchType
  })
})
const publishedCourseCount = computed(() => courses.value.filter((course) => course.status === 'published').length)
const draftCourseCount = computed(() => courses.value.filter((course) => course.status !== 'published').length)

onMounted(fetchCourses)

function defaultCourseForm() {
  return {
    title: '',
    subtitle: '',
    description: '',
    courseType: 'required',
    category: '人工智能',
    coverUrl: '',
    accentColor: '#7cffb2',
    status: 'draft',
    sortOrder: 0
  }
}

async function fetchCourses() {
  loading.value = true
  try {
    const res = await request.get('/api/admin/courses')
    courses.value = res.data || []
    if (selectedCourse.value) await loadCourseDetail(selectedCourse.value.id)
  } finally {
    loading.value = false
  }
}

async function selectCourse(row) {
  await loadCourseDetail(row.id)
}

async function loadCourseDetail(id) {
  const res = await request.get(`/api/admin/courses/${id}`)
  selectedCourse.value = res.data
}

function openCourseDialog(row) {
  courseForm.value = row ? { ...row } : defaultCourseForm()
  courseDialogVisible.value = true
}

async function saveCourse() {
  if (!courseForm.value.title?.trim()) return ElMessage.error('请填写课程名称')
  if (courseForm.value.id) {
    await request.put(`/api/admin/courses/${courseForm.value.id}`, courseForm.value)
  } else {
    await request.post('/api/admin/courses', courseForm.value)
  }
  ElMessage.success('课程已保存')
  courseDialogVisible.value = false
  await fetchCourses()
}

async function deleteCourse(row) {
  await ElMessageBox.confirm(`确定删除课程「${row.title}」？`, '删除课程', { type: 'warning' })
  await request.delete(`/api/admin/courses/${row.id}`)
  if (selectedCourse.value?.id === row.id) selectedCourse.value = null
  ElMessage.success('课程已删除')
  await fetchCourses()
}

async function batchDeleteCourses() {
  const ids = idsFromRows(selectedCourses.value)
  if (ids.length === 0) return
  await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 门课程？`, '批量删除课程', { type: 'warning' })
  const res = await request.post('/api/admin/courses/batch-delete', { ids })
  const summary = batchDeleteSummary(res, '课程')
  ElMessage[summary.type](summary.message)
  if (selectedCourse.value && ids.includes(selectedCourse.value.id)) selectedCourse.value = null
  selectedCourses.value = []
  await fetchCourses()
}

function openChapterDialog(chapter) {
  chapterForm.value = chapter
    ? { id: chapter.id, title: chapter.title, sortOrder: chapter.sortOrder || 0 }
    : { id: null, title: '', sortOrder: (selectedCourse.value?.chapters?.length || 0) * 10 + 10 }
  chapterDialogVisible.value = true
}

async function saveChapter() {
  if (!chapterForm.value.title?.trim()) return ElMessage.error('请填写章节名')
  if (chapterForm.value.id) {
    await request.put(`/api/admin/courses/${selectedCourse.value.id}/chapters/${chapterForm.value.id}`, chapterForm.value)
  } else {
    await request.post(`/api/admin/courses/${selectedCourse.value.id}/chapters`, chapterForm.value)
  }
  ElMessage.success(chapterForm.value.id ? '章节已更新' : '章节已创建')
  chapterDialogVisible.value = false
  await loadCourseDetail(selectedCourse.value.id)
}

async function deleteChapter(chapter) {
  await ElMessageBox.confirm(`确定删除章节「${chapter.title}」？章节下课时会一并删除。`, '删除章节', { type: 'warning' })
  await request.delete(`/api/admin/courses/${selectedCourse.value.id}/chapters/${chapter.id}`)
  ElMessage.success('章节已删除')
  await loadCourseDetail(selectedCourse.value.id)
}

function openLessonDialog(lesson) {
  const firstChapter = chapterOptions.value[0]
  lessonForm.value = lesson
    ? {
        id: lesson.id,
        chapterId: lesson.chapterId,
        title: lesson.title,
        durationSeconds: lesson.durationSeconds || 0,
        sortOrder: lesson.sortOrder || 0
      }
    : { id: null, chapterId: firstChapter?.id || null, title: '', durationSeconds: 0, sortOrder: 10 }
  lessonDialogVisible.value = true
}

async function saveLesson() {
  if (!lessonForm.value.chapterId) return ElMessage.error('请选择章节')
  if (!lessonForm.value.title?.trim()) return ElMessage.error('请填写课时名称')
  const payload = {
    ...lessonForm.value,
    lessonType: 'video'
  }
  if (lessonForm.value.id) {
    await request.put(`/api/admin/courses/${selectedCourse.value.id}/lessons/${lessonForm.value.id}`, payload)
  } else {
    await request.post(`/api/admin/courses/${selectedCourse.value.id}/lessons`, payload)
  }
  ElMessage.success(lessonForm.value.id ? '课时已更新' : '课时已创建，现在可以上传视频')
  lessonDialogVisible.value = false
  await loadCourseDetail(selectedCourse.value.id)
}

async function deleteLesson(row) {
  await ElMessageBox.confirm(`确定删除课时「${row.title}」？`, '删除课时', { type: 'warning' })
  await request.delete(`/api/admin/courses/${selectedCourse.value.id}/lessons/${row.id}`)
  ElMessage.success('课时已删除')
  await loadCourseDetail(selectedCourse.value.id)
}

function beforeVideoUpload(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['mp4', 'webm', 'mov', 'm4v'].includes(ext)) {
    ElMessage.error('仅支持 mp4、webm、mov、m4v 视频')
    return false
  }
  if (file.size > 500 * 1024 * 1024) {
    ElMessage.error('视频不能超过 500MB')
    return false
  }
  return true
}

async function handleVideoSuccess(res) {
  if (res.code !== 200) return ElMessage.error(res.message || '视频上传失败')
  ElMessage.success('视频已上传')
  await loadCourseDetail(selectedCourse.value.id)
}

function handleVideoError() {
  ElMessage.error('视频上传失败')
}

function beforeCoverUpload(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['jpg', 'jpeg', 'png', 'webp'].includes(ext)) {
    ElMessage.error('仅支持 JPG、PNG、WebP 图片')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('封面图片不能超过 5MB')
    return false
  }
  return true
}

async function handleCoverSuccess(res) {
  if (res.code !== 200) return ElMessage.error(res.message || '封面上传失败')
  courseForm.value.coverUrl = res.data?.coverUrl || courseForm.value.coverUrl
  ElMessage.success('封面已上传')
  await fetchCourses()
}

function handleCoverError() {
  ElMessage.error('封面上传失败')
}

function beforeAttachmentUpload(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  const allowed = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'zip', 'rar', 'png', 'jpg', 'jpeg']
  if (!allowed.includes(ext)) {
    ElMessage.error('仅支持 PDF、Office、压缩包和图片附件')
    return false
  }
  if (file.size > 100 * 1024 * 1024) {
    ElMessage.error('附件不能超过 100MB')
    return false
  }
  return true
}

async function handleAttachmentSuccess(res) {
  if (res.code !== 200) return ElMessage.error(res.message || '附件上传失败')
  ElMessage.success('附件已上传')
  await loadCourseDetail(selectedCourse.value.id)
}

function handleAttachmentError() {
  ElMessage.error('附件上传失败')
}

function previewAttachment(row) {
  if (!row.fileUrl) return
  window.open(row.fileUrl, '_blank', 'noopener,noreferrer')
}

async function deleteAttachment(row) {
  await ElMessageBox.confirm(`确定删除附件「${row.name}」？`, '删除附件', { type: 'warning' })
  await request.delete(`/api/admin/courses/${selectedCourse.value.id}/attachments/${row.id}`)
  ElMessage.success('附件已删除')
  await loadCourseDetail(selectedCourse.value.id)
}

async function batchDeleteAttachments() {
  if (!selectedCourse.value) return
  const ids = idsFromRows(selectedAttachments.value)
  if (ids.length === 0) return
  await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个课程附件？`, '批量删除附件', { type: 'warning' })
  const res = await request.post(`/api/admin/courses/${selectedCourse.value.id}/attachments/batch-delete`, { ids })
  const summary = batchDeleteSummary(res, '附件')
  ElMessage[summary.type](summary.message)
  selectedAttachments.value = []
  await loadCourseDetail(selectedCourse.value.id)
}

function formatDuration(seconds) {
  const total = Number(seconds) || 0
  const minutes = String(Math.floor(total / 60)).padStart(2, '0')
  const rest = String(total % 60).padStart(2, '0')
  return `${minutes}:${rest}`
}
</script>

<style scoped>
.chapter-list {
  display: grid;
  gap: 18px;
}

.chapter-card {
  padding: 18px;
  border: 1px solid var(--admin-border-soft);
  border-radius: var(--admin-radius-md);
  background: var(--admin-surface-muted);
}

.chapter-card h3 {
  margin: 0;
  color: var(--admin-text-strong);
}

.chapter-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.video-ready {
  color: var(--admin-green);
  font-weight: 600;
}

.video-missing {
  color: var(--admin-primary);
}

.course-cover-field {
  width: 100%;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.course-cover-preview {
  height: 108px;
  border: 1px solid var(--admin-border-soft);
  border-radius: var(--admin-radius-sm);
  background: var(--admin-surface-muted);
  overflow: hidden;
}

.course-cover-preview.empty {
  display: grid;
  place-items: center;
  padding: 12px;
  color: var(--admin-text-muted);
  font-size: 13px;
  text-align: center;
}

.course-cover-preview img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.course-cover-actions {
  display: grid;
  gap: 8px;
}

.course-cover-actions small {
  color: var(--admin-text-muted);
  line-height: 1.5;
}
</style>
