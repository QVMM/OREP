<template>
  <div class="course-page">
    <main class="course-page__inner">
      <template v-if="!selectedCourse">
        <section class="course-hero">
          <div class="course-hero__copy">
            <h1>课程学习</h1>
            <p>按课程体系学习知识、演练答辩、沉淀资料。先继续当前课程，再进入分类浏览。</p>
          </div>
          <div class="course-hero__actions">
            <BaseButton :disabled="!featuredCourse" @click="openCourse(featuredCourse?.id)">
              继续学习
            </BaseButton>
          </div>
          <div class="course-hero__progress">
            <div>
              <span>总学习时长：</span>
              <strong>{{ formatStudyDuration(totalLearnedSeconds) }}</strong>
            </div>
            <div class="course-hero__progress-line">
              <small>当前课程进度 {{ heroProgress }}%</small>
              <i><b :style="{ width: `${heroProgress}%` }"></b></i>
            </div>
            <p>{{ featuredCourse?.title || '暂无进行中的课程' }}{{ featuredCourse?.currentChapterTitle ? ` · ${featuredCourse.currentChapterTitle}` : '' }}</p>
          </div>
        </section>

        <section class="course-layout">
        <aside class="course-aside">
          <section class="course-sidebar">
            <div class="course-sidebar__head">
              <strong>课程分类</strong>
              <span>共 {{ courses.length }} 门</span>
            </div>

            <label class="course-search">
              <span class="sr-only">搜索课程</span>
              <input v-model="searchKeyword" type="search" placeholder="搜索课程" />
            </label>

            <div class="category-scroll">
              <div class="category-tree" role="tree">
                <button
                  type="button"
                  class="category-item category-item--root"
                  :class="{ active: activeCategory === 'all' }"
                  @click="setCategory('all')"
                >
                  <span>全部课程</span>
                  <b>{{ courses.length }}</b>
                </button>

                <section v-for="group in categoryTree" :key="group.key" class="category-group">
                  <button
                    type="button"
                    class="category-group__head"
                    :aria-expanded="expandedGroups.includes(group.key)"
                    @click="toggleCategoryGroup(group.key)"
                  >
                    <span>{{ group.label }}</span>
                    <b>{{ group.count }}</b>
                  </button>
                  <div v-show="expandedGroups.includes(group.key)" class="category-group__children">
                    <button
                      v-for="item in group.children"
                      :key="item.value"
                      type="button"
                      class="category-item category-item--child"
                      :class="{ active: activeCategory === item.value }"
                      @click="setCategory(item.value)"
                    >
                      <span>{{ item.label }}</span>
                      <b>{{ item.count }}</b>
                    </button>
                  </div>
                </section>
              </div>
            </div>
          </section>

          <section class="learning-suggestions" aria-label="学习建议">
            <header>
              <span class="learning-suggestions__accent" aria-hidden="true"></span>
              <h2>学习建议</h2>
            </header>
            <div class="learning-suggestion-list">
              <article v-for="item in weeklyStudyPlan" :key="item.id" class="learning-suggestion-item">
                <i class="learning-suggestion-dot" :class="`is-${item.tone}`" aria-hidden="true"></i>
                <div>
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.subtitle }}</span>
                </div>
              </article>
            </div>
          </section>
        </aside>

        <section class="course-main" v-loading="loading">
          <div class="filter-row" aria-label="课程筛选">
            <div class="filter-row__tabs">
              <BaseButton
                v-for="item in filters"
                :key="item.value"
                type="secondary"
                size="small"
                class="filter-tab"
                :aria-pressed="activeFilter === item.value"
                @click="setFilter(item.value)"
              >
                {{ item.label }}
              </BaseButton>
            </div>
            <BaseButton type="ghost" size="small">按最近学习排序</BaseButton>
          </div>

          <section class="course-grid">
            <article
              v-for="(course, index) in visibleCourses"
              :key="course.id"
              class="course-card"
              role="link"
              tabindex="0"
              :aria-label="`打开课程：${course.title}`"
              @click="openCourse(course.id)"
              @keydown.enter.prevent="openCourse(course.id)"
              @keydown.space.prevent="openCourse(course.id)"
            >
              <div class="course-card__cover" :class="{ 'has-image': course.coverUrl }" :style="courseCoverStyle(course)">
                <img v-if="course.coverUrl" class="course-card__cover-img" :src="withAuthMediaUrl(course.coverUrl)" :alt="course.title" />
                <div class="course-card__badges">
                  <b>{{ courseStatusText(course) }}</b>
                  <em>{{ course.courseTypeLabel || '课程学习' }}</em>
                </div>
              </div>
              <div class="course-card__body">
                <h2>{{ course.title }}</h2>
                <span class="course-card__source">{{ course.category || '竞赛备赛课程' }}</span>
                <span class="course-card__meta">{{ courseMetaText(course) }} · {{ progressText(course) }}</span>
                <p>{{ course.subtitle || course.description || '暂无课程说明' }}</p>
                <div class="course-progress">
                  <i><b :style="{ width: `${course.progressPercent || 0}%` }"></b></i>
                </div>
              </div>
            </article>

            <div v-if="visibleCourses.length === 0 && !loading" class="empty-panel">
              <strong>课程需按赛道定制</strong>
              <span>可上传自定义课程。</span>
            </div>
          </section>
        </section>
      </section>
      </template>

      <section v-else class="course-detail course-detail-page" v-loading="loading">
        <BaseButton type="text" size="small" class="back-link detail-back" @click="backToCourseList">
          <el-icon><ArrowLeft /></el-icon>
          返回课程列表
        </BaseButton>

        <header class="learning-detail-hero">
          <div class="learning-detail-hero__copy">
            <span class="course-kicker">{{ selectedCourse.category || '课程详情' }}</span>
            <h1>{{ selectedCourse.title }}</h1>
            <p>{{ selectedCourse.description || selectedCourse.subtitle || '暂无课程说明' }}</p>
            <div class="learning-detail-hero__actions">
              <BaseButton @click="continueFirstAvailableLesson">
                继续学习
              </BaseButton>
              <BaseButton type="secondary" @click="detailTab = 'attachments'">
                查看资料
              </BaseButton>
            </div>
          </div>
          <div class="learning-detail-hero__status">
            <small>当前学习位置</small>
            <strong>{{ currentChapterTitle }}</strong>
            <span>{{ currentLessonText }}</span>
            <b>{{ nextLessonText }}</b>
          </div>
        </header>

        <section class="learning-detail-layout">
          <main class="learning-detail-main">
            <div class="learning-section-head">
              <h2>课程章节</h2>
              <span>{{ totalLessonCount }} 小节 · {{ selectedCourse.chapters?.length || 0 }} 个章节</span>
            </div>

            <nav class="detail-tabs learning-detail-tabs" aria-label="课程详情导航">
              <BaseButton type="secondary" size="small" :aria-pressed="detailTab === 'catalog'" @click="detailTab = 'catalog'">课程目录</BaseButton>
              <BaseButton type="secondary" size="small" :aria-pressed="detailTab === 'intro'" @click="detailTab = 'intro'">课程介绍</BaseButton>
              <BaseButton type="secondary" size="small" :aria-pressed="detailTab === 'records'" @click="detailTab = 'records'">学习记录</BaseButton>
              <BaseButton type="secondary" size="small" :aria-pressed="detailTab === 'attachments'" @click="detailTab = 'attachments'">课程资料</BaseButton>
            </nav>

            <div v-if="detailTab === 'catalog'" class="learning-chapter-list">
              <section v-for="chapter in selectedCourse.chapters" :key="chapter.id" class="learning-chapter">
                <div class="learning-chapter__title">
                  <strong>{{ chapter.title }}</strong>
                  <span>{{ chapterSummaryText(chapter) }}</span>
                </div>

                <div class="learning-lesson-list">
                  <button
                    v-for="lesson in chapter.lessons"
                    :key="lesson.id"
                    type="button"
                    class="learning-lesson"
                    :class="{ current: lesson.current, completed: lesson.completed }"
                    @click="continueLesson(lesson)"
                  >
                    <span class="learning-lesson__number">{{ lessonNumber(lesson) }}</span>
                    <span class="learning-lesson__copy">
                      <strong>{{ lesson.title }}</strong>
                      <small>{{ lessonSubText(lesson) }}</small>
                    </span>
                    <span class="learning-lesson__meta">{{ lessonDurationText(lesson) }}</span>
                    <em>{{ lessonActionText(lesson) }}</em>
                  </button>
                </div>
              </section>

              <div v-if="!selectedCourse.chapters?.length" class="empty-panel">
                <strong>该课程暂无章节</strong>
                <span>课程章节发布后会显示在这里。</span>
              </div>
            </div>

            <div v-else-if="detailTab === 'intro'" class="detail-info-panel">
              <h3>课程介绍</h3>
              <p class="detail-info-copy">{{ selectedCourse.description || selectedCourse.subtitle || '暂无课程介绍。' }}</p>
              <div class="detail-info-grid">
                <span>课程分类 <b>{{ selectedCourse.category || '未分类' }}</b></span>
                <span>课程类型 <b>{{ selectedCourse.courseTypeLabel || '课程' }}</b></span>
                <span>学习进度 <b>{{ selectedCourse.progressPercent || 0 }}%</b></span>
              </div>
            </div>

            <div v-else-if="detailTab === 'records'" class="detail-info-panel">
              <h3>学习记录</h3>
              <p class="detail-info-copy">{{ completedLessonCount }} / {{ totalLessonCount }} 小节已完成，当前建议继续学习“{{ currentLesson?.title || '第一节课' }}”。</p>
              <div class="detail-record-list">
                <span>最近学习 <b>{{ currentLesson?.title || '暂无记录' }}</b></span>
                <span>本周建议 <b>完成 2 小节</b></span>
                <span>下一步 <b>{{ nextLesson?.title || '复习已完成内容' }}</b></span>
              </div>
            </div>

            <div v-else class="detail-resource-list">
              <a
                v-for="item in courseMaterials"
                :key="item.id"
                class="detail-resource"
                :href="withAuthMediaUrl(item.fileUrl) || '#'"
                :target="item.fileUrl ? '_blank' : undefined"
                rel="noreferrer"
              >
                <span class="material-name" :title="item.name">{{ item.name }}</span>
                <b>{{ materialActionText(item) }}</b>
              </a>
              <div v-if="!courseMaterials.length" class="empty-panel">
                <strong>该课程暂无资料</strong>
                <span>讲义、文档和课后练习发布后会显示在这里。</span>
              </div>
            </div>
          </main>

          <aside class="learning-detail-side">
            <section class="side-card learning-progress-card">
              <h2>学习进度</h2>
              <div class="learning-progress-card__main">
                <span>整体完成</span>
                <strong>{{ selectedCourse.progressPercent || 0 }}%</strong>
              </div>
              <i><b :style="{ width: `${selectedCourse.progressPercent || 0}%` }"></b></i>
              <p>{{ completedLessonCount }} / {{ totalLessonCount }} 小节已完成，本周建议完成 2 小节。</p>
            </section>

            <section class="side-card learning-material-card">
              <h2>课程资料</h2>
              <a
                v-for="item in courseMaterials"
                :key="item.id"
                :href="withAuthMediaUrl(item.fileUrl) || '#'"
                :target="item.fileUrl ? '_blank' : undefined"
                rel="noreferrer"
              >
                <span class="material-name" :title="item.name">{{ item.name }}</span>
                <b>{{ materialActionText(item) }}</b>
              </a>
              <p v-if="!courseMaterials.length">暂无课程资料</p>
            </section>

            <section class="side-card weak-card">
              <h2>薄弱点建议</h2>
              <div class="weak-card__box">
                <strong>{{ weakSuggestion.title }}</strong>
                <p>{{ weakSuggestion.description }}</p>
              </div>
              <span>推荐章节 <b>{{ weakSuggestion.chapter }}</b></span>
              <span>推荐练习 <b>{{ weakSuggestion.practice }}</b></span>
            </section>
          </aside>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import BaseButton from '../components/base/BaseButton.vue'
import request from '../utils/request'
import { withAuthMediaUrl } from '../utils/mediaUrl'

const filters = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'unfinished' },
  { label: '已完成', value: 'completed' }
]

const loading = ref(false)
const courses = ref([])
const selectedCourse = ref(null)
const activeFilter = ref('all')
const activeCategory = ref('all')
const detailTab = ref('catalog')
const searchKeyword = ref('')
const expandedGroups = ref(['basic', 'practice', 'ai', 'general'])
const route = useRoute()
const router = useRouter()

const weeklyStudyPlan = computed(() => {
  const active = featuredCourse.value
  const lessons = selectedCourse.value?.id === active?.id ? allLessons.value : []
  const next = lessons.find((lesson) => !lesson.completed) || lessons[0]
  return [
    {
      id: 1,
      tone: active ? 'active' : 'muted',
      title: active ? `继续学习：${active.title}` : '暂无可学习课程',
      subtitle: active ? `${active.progressPercent || 0}% 已完成` : '请等待管理员发布课程'
    },
    {
      id: 2,
      tone: courses.value.length > 0 ? 'available' : 'muted',
      title: next ? `完成课时：${next.title}` : '查看课程目录',
      subtitle: next ? `预计 ${Math.max(1, Math.round((next.durationSeconds || 0) / 60))} 分钟` : `${courses.value.length} 门课程可浏览`
    },
    {
      id: 3,
      tone: completedCount.value > 0 ? 'done' : 'muted',
      title: completedCount.value > 0 ? '复习已完成课程' : '完成首次学习记录',
      subtitle: completedCount.value > 0 ? `${completedCount.value} 门已完成` : '播放视频后自动同步进度'
    }
  ]
})

const categories = computed(() => {
  return [...new Set(courses.value.map((item) => item.category).filter(Boolean))]
})

const categoryTree = computed(() => {
  const groups = new Map()
  categories.value.forEach((category) => {
    const group = categoryGroupFor(category)
    if (!groups.has(group.key)) {
      groups.set(group.key, { ...group, count: 0, children: [] })
    }
    const count = courses.value.filter((course) => course.category === category).length
    const target = groups.get(group.key)
    target.count += count
    target.children.push({
      label: category,
      value: category,
      count,
    })
  })
  return Array.from(groups.values())
})

const completedCount = computed(() => {
  return courses.value.filter((item) => item.learningStatus === 'completed').length
})

const featuredCourse = computed(() => {
  return courses.value.find((course) => (course.progressPercent || 0) > 0 && (course.progressPercent || 0) < 100) || courses.value[0]
})

const heroProgress = computed(() => Math.max(0, Math.min(100, Number(featuredCourse.value?.progressPercent) || 0)))
const totalLearnedSeconds = computed(() => courses.value.reduce((total, course) => total + Math.max(0, Number(course.learnedSeconds) || 0), 0))

const visibleCourses = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return courses.value
  return courses.value.filter((course) => {
    return [course.title, course.subtitle, course.description, course.category]
      .filter(Boolean)
      .some((text) => String(text).toLowerCase().includes(keyword))
  })
})

const allLessons = computed(() => {
  return selectedCourse.value?.chapters?.flatMap((chapter) => chapter.lessons || []) || []
})

const totalLessonCount = computed(() => {
  return selectedCourse.value?.totalLessons || allLessons.value.length || 0
})

const completedLessonCount = computed(() => {
  return allLessons.value.filter((lesson) => lesson.completed).length
})

const currentLesson = computed(() => {
  return allLessons.value.find((lesson) => lesson.current) || allLessons.value.find((lesson) => !lesson.completed) || allLessons.value[0]
})

const currentChapter = computed(() => {
  if (!selectedCourse.value?.chapters?.length || !currentLesson.value) return selectedCourse.value?.chapters?.[0]
  return selectedCourse.value.chapters.find((chapter) => (chapter.lessons || []).some((lesson) => lesson.id === currentLesson.value.id)) || selectedCourse.value.chapters[0]
})

const currentChapterTitle = computed(() => {
  return currentChapter.value?.title || '暂无章节'
})

const currentLessonText = computed(() => {
  if (!currentLesson.value) return '课程章节发布后即可开始学习。'
  if (currentLesson.value.current) return `上次学习到 ${formatDuration(selectedCourse.value?.learnedSeconds)}，继续播放即可衔接。`
  if (currentLesson.value.completed) return '已完成当前课程，可进入复习或查看资料。'
  return `建议从“${currentLesson.value.title}”开始学习。`
})

const nextLesson = computed(() => {
  if (!allLessons.value.length || !currentLesson.value) return null
  const index = allLessons.value.findIndex((lesson) => lesson.id === currentLesson.value.id)
  return allLessons.value.slice(index + 1).find((lesson) => !lesson.completed) || allLessons.value.find((lesson) => !lesson.completed && lesson.id !== currentLesson.value.id)
})

const nextLessonText = computed(() => {
  return nextLesson.value ? `下一节：${nextLesson.value.title}` : '下一步：复习课程重点'
})

const courseMaterials = computed(() => {
  return selectedCourse.value?.attachments || []
})

const weakSuggestion = computed(() => {
  const lesson = allLessons.value.find((item) => !item.completed && /复杂|算法|结构|表达|答辩/.test(item.title || '')) || nextLesson.value || currentLesson.value
  return {
    title: lesson ? `${lesson.title}需要补强` : '建议先完成当前章节',
    description: lesson ? `结合最近学习进度，建议优先学习“${lesson.title}”，再进入配套练习。` : '课程章节发布后，系统会根据学习记录生成薄弱点建议。',
    chapter: lessonNumber(lesson) ? `${lessonNumber(lesson)} ${lesson?.title}` : '暂无推荐',
    practice: lesson ? '专项练习' : '暂无练习'
  }
})

onMounted(() => {
  fetchCourses()
  syncCourseFromRoute()
})

watch(
  () => route.params.courseId,
  () => {
    syncCourseFromRoute()
  }
)

async function fetchCourses() {
  loading.value = true
  try {
    const res = await request.get('/api/courses', {
      params: {
        filter: activeFilter.value,
        category: activeCategory.value
      }
    })
    courses.value = res.data || []
  } finally {
    loading.value = false
  }
}

async function openCourse(courseId) {
  if (!courseId) return
  await router.push({
    name: 'CourseDetail',
    params: { courseId }
  })
}

async function syncCourseFromRoute() {
  const courseId = route.params.courseId
  if (!courseId) {
    selectedCourse.value = null
    return
  }
  await fetchCourseDetail(courseId)
}

async function fetchCourseDetail(courseId) {
  loading.value = true
  try {
    const res = await request.get(`/api/courses/${courseId}`)
    selectedCourse.value = res.data
    detailTab.value = 'catalog'
  } finally {
    loading.value = false
  }
}

async function continueLesson(lesson) {
  if (!selectedCourse.value || !lesson) return
  await router.push({
    name: 'CourseLessonPlayer',
    params: {
      courseId: selectedCourse.value.id,
      lessonId: lesson.id
    }
  })
}

function continueFirstAvailableLesson() {
  const lesson = allLessons.value.find((item) => item.current) || allLessons.value.find((item) => !item.completed) || allLessons.value[0]
  continueLesson(lesson)
}

function backToCourseList() {
  selectedCourse.value = null
  router.push({ name: 'CourseLearning' })
}

function setFilter(value) {
  activeFilter.value = value
  fetchCourses()
}

function setCategory(value) {
  activeCategory.value = value
  fetchCourses()
}

function toggleCategoryGroup(key) {
  if (expandedGroups.value.includes(key)) {
    expandedGroups.value = expandedGroups.value.filter((item) => item !== key)
    return
  }
  expandedGroups.value = [...expandedGroups.value, key]
}

function categoryGroupFor(category) {
  const text = String(category || '')
  if (/编程|算法|数据|基础|结构|数学|理论/.test(text)) {
    return { key: 'basic', label: '知识基础' }
  }
  if (/AI|人工智能|智能|模型|机器|视觉|大数据/.test(text)) {
    return { key: 'ai', label: '智能应用' }
  }
  if (/工程|实践|项目|路演|答辩|交付|PPT|讲稿/.test(text)) {
    return { key: 'practice', label: '项目路演' }
  }
  return { key: 'general', label: '通用课程' }
}

function thumbCode(course) {
  if (!course?.title) return '课'
  if (course.title.includes('Python')) return 'PY'
  if (course.title.includes('Spring') || course.title.includes('Vue')) return 'SV'
  if (course.title.includes('PPT')) return 'PT'
  return course.title.slice(0, 1)
}

function courseCoverStyle(course) {
  const cover = withAuthMediaUrl(course?.coverUrl)
  if (cover) {
    const safe = cover.replace(/"/g, '')
    return { backgroundImage: `linear-gradient(180deg, rgba(0,0,0,.1), rgba(0,0,0,.28)), url("${safe}")` }
  }
  return { '--cover-accent': course?.accentColor || 'var(--orep-orange)' }
}

function progressText(course) {
  if ((course.progressPercent || 0) >= 100) return '已学完'
  if ((course.progressPercent || 0) > 0) return `${course.progressPercent}%`
  return '未学习'
}

function courseStatusText(course) {
  const progress = Number(course?.progressPercent) || 0
  if (progress >= 100 || course?.learningStatus === 'completed') return '已完成'
  if (progress > 0) return '进行中'
  return '未开始'
}

function courseMetaText(course) {
  const lessonCount = course?.totalLessons || course?.lessonCount || 0
  const chapterCount = course?.totalChapters || course?.chapterCount || course?.chapters?.length || 0
  if (lessonCount && chapterCount) return `${lessonCount} 节课 · ${chapterCount} 章`
  if (lessonCount) return `${lessonCount} 节课`
  if (course?.category) return course.category
  return progressText(course)
}

function lessonStatusText(lesson) {
  if (lesson.completed) return '已完成'
  if (lesson.current) return `上次学习到 ${formatDuration(selectedCourse.value?.learnedSeconds)}`
  return `时长 ${formatDuration(lesson.durationSeconds)}`
}

function chapterSummaryText(chapter) {
  const lessons = chapter?.lessons || []
  const completed = lessons.filter((lesson) => lesson.completed).length
  const current = lessons.filter((lesson) => lesson.current).length
  if (current) return `${lessons.length} 小节 · ${current} 小节进行中`
  if (completed === lessons.length && lessons.length) return `${lessons.length} 小节 · 已完成`
  if (completed) return `${lessons.length} 小节 · 已完成 ${completed}`
  return `${lessons.length} 小节 · 未开始`
}

function lessonNumber(lesson) {
  const index = allLessons.value.findIndex((item) => item.id === lesson?.id)
  if (index < 0) return '--'
  return String(index + 1).padStart(2, '0')
}

function lessonSubText(lesson) {
  if (lesson?.completed) return '已完成 · 可随时复习'
  if (lesson?.current) return `正在学习 · 上次学习到 ${formatDuration(selectedCourse.value?.learnedSeconds)}`
  if (lesson?.description) return lesson.description
  return '未开始 · 建议按顺序学习'
}

function lessonDurationText(lesson) {
  const duration = Number(lesson?.durationSeconds) || 0
  if (!duration) return lesson?.typeLabel || '视频'
  const minutes = Math.max(1, Math.round(duration / 60))
  return `${minutes} 分钟 · ${lesson?.typeLabel || '视频'}`
}

function lessonActionText(lesson) {
  if (lesson?.current) return '播放'
  if (lesson?.completed) return '复习'
  return '查看'
}

function materialActionText(item) {
  const type = String(item?.fileType || item?.name || '')
  if (/练习|题|测验/.test(type)) return '开始'
  if (/pdf|预览/i.test(type)) return '预览'
  if (item?.fileUrl) return '下载'
  return '查看'
}

function formatDuration(seconds) {
  const total = Math.max(0, Number(seconds) || 0)
  const minutes = String(Math.floor(total / 60)).padStart(2, '0')
  const rest = String(total % 60).padStart(2, '0')
  return `${minutes}:${rest}`
}

function formatStudyDuration(seconds) {
  const totalMinutes = Math.max(0, Math.round((Number(seconds) || 0) / 60))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours > 0 ? `${hours} 小时 ${minutes} 分钟` : `${minutes} 分钟`
}
</script>

<style scoped>
.course-page {
  min-height: calc(100vh - var(--header-height));
  background: transparent;
}

.course-page__inner {
  width: 100%;
  max-width: 100%;
  margin: 0;
  /* 页边距由 .workspace-main 唯一提供 */
  padding: 0 0 var(--ds-space-6, 24px);
  min-width: 100%;
  overflow-x: hidden;
}

.course-layout {
  display: grid;
  grid-template-columns: 252px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.course-sidebar,
.course-main,
.course-detail,
.featured-course,
.course-card,
.chapter-panel,
.chapter-summary,
.attachment-card,
.empty-panel {
  border: 1px solid var(--orep-border-soft);
  background: var(--orep-surface-raised);
  box-shadow: var(--orep-shadow-soft);
}

.course-sidebar {
  position: sticky;
  top: calc(var(--header-height) + 18px);
  border-radius: 18px;
  padding: 14px;
  display: grid;
  gap: 6px;
  max-height: calc(100vh - var(--header-height) - 44px);
  overflow: auto;
}

.course-sidebar__head {
  padding: 4px 4px 12px;
  border-bottom: 1px solid var(--orep-border-soft);
  margin-bottom: 4px;
}

.course-sidebar__head strong,
.course-sidebar__head span {
  display: block;
}

.course-sidebar__head strong {
  color: var(--orep-text-strong);
  font-size: 16px;
}

.course-sidebar__head span {
  margin-top: 5px;
  color: var(--orep-muted);
  font-size: 12px;
}

.category-item {
  min-height: 44px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--orep-muted);
  padding: 0 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font: inherit;
  font-weight: 820;
  cursor: pointer;
}

.category-tree {
  display: grid;
  gap: 8px;
}

.category-group {
  display: grid;
  gap: 6px;
}

.category-group__head {
  min-height: 34px;
  border: 0;
  background: transparent;
  color: var(--orep-text-strong);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
  font: inherit;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
}

.category-group__head::before {
  content: "›";
  color: var(--orep-muted);
  font-size: 15px;
  line-height: 1;
  transform: rotate(0deg);
  transition: transform 160ms var(--orep-ease-out);
}

.category-group__head[aria-expanded="true"]::before {
  transform: rotate(90deg);
}

.category-group__head span {
  flex: 1;
  text-align: left;
}

.category-group__head b {
  color: var(--orep-muted);
  font-size: 13px;
}

.category-group__children {
  position: relative;
  display: grid;
  gap: 7px;
  padding-left: 16px;
}

.category-group__children::before {
  content: "";
  position: absolute;
  left: 6px;
  top: 4px;
  bottom: 4px;
  width: 1px;
  background: var(--orep-border-soft);
}

.category-item--child {
  position: relative;
}

.category-item--child::before {
  content: "";
  position: absolute;
  left: -10px;
  top: 50%;
  width: 10px;
  height: 1px;
  background: var(--orep-border-soft);
}

.category-item b {
  min-width: 24px;
  height: 24px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: var(--orep-bg);
  color: var(--orep-muted);
  font-size: 11px;
}

.category-item.active {
  background: var(--orep-orange-soft);
  color: var(--orep-text-strong);
  box-shadow: inset 0 0 0 1px oklch(0.88 0.055 55);
}

.category-item.active b {
  background: var(--orep-surface-raised);
  color: var(--orep-orange);
}

.course-main,
.course-detail {
  border-radius: 20px;
  padding: 22px;
}

.course-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 22px;
  align-items: end;
}

.course-kicker {
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 900;
}

.course-header h1,
.detail-hero h1 {
  margin: 12px 0 10px;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.3;
  letter-spacing: 0;
}

.course-header p,
.detail-hero p {
  margin: 0;
  max-width: 760px;
  color: var(--orep-muted);
  line-height: 1.75;
}

.course-header__stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.course-header__stats div {
  min-height: 78px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 14px;
  padding: 13px;
  background: var(--orep-bg);
}

.course-header__stats strong,
.course-header__stats span {
  display: block;
}

.course-header__stats strong {
  color: var(--orep-text-strong);
  font-size: 28px;
  line-height: 1;
}

.course-header__stats span {
  margin-top: 8px;
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 760;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 22px 0 16px;
}

.featured-course {
  min-height: 190px;
  border-radius: 18px;
  padding: 14px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) auto;
  gap: 20px;
  align-items: center;
  margin-bottom: 16px;
  cursor: pointer;
}

.featured-course__cover,
.course-card__cover,
.detail-hero__cover {
  background:
    linear-gradient(135deg, var(--cover-accent, var(--orep-orange)), oklch(0.88 0.07 55)),
    var(--orep-orange-soft);
  background-size: cover;
  background-position: center;
  color: var(--orep-surface-raised);
  display: grid;
  place-items: center;
  overflow: hidden;
}

.featured-course__cover {
  height: 162px;
  border-radius: 14px;
}

.featured-course__cover span,
.course-card__cover span,
.detail-hero__cover span {
  font-size: 42px;
  font-weight: 900;
  text-shadow: 0 8px 22px oklch(0.2 0.015 45 / 0.25);
}

.featured-course__copy small {
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 900;
}

.featured-course__copy h2 {
  margin: 9px 0 8px;
  color: var(--orep-text-strong);
  font-size: 25px;
  line-height: 1.24;
}

.featured-course__copy p {
  margin: 0 0 18px;
  color: var(--orep-muted);
  line-height: 1.65;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.course-card {
  min-height: 310px;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color var(--ds-control-transition), background-color var(--ds-control-transition);
}

.course-card:hover {
  border-color: var(--ds-line-strong);
}

.course-card__cover {
  height: 140px;
}

.course-card__body {
  padding: 15px;
}

.course-card__tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.course-card__tags b,
.course-card__tags small {
  min-height: 26px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 820;
}

.course-card__tags b {
  color: var(--orep-orange);
  background: var(--orep-orange-soft);
}

.course-card__tags small {
  color: var(--orep-muted);
  background: var(--orep-bg);
}

.course-card h2 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 18px;
  line-height: 1.35;
}

.course-card p {
  display: -webkit-box;
  min-height: 42px;
  margin: 8px 0 14px;
  overflow: hidden;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.course-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.course-progress i,
.detail-progress i {
  height: 7px;
  flex: 1;
  border-radius: 999px;
  overflow: hidden;
  background: var(--orep-border-soft);
}

.course-progress b,
.detail-progress b {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: inherit;
  background: var(--orep-orange);
}

.course-progress span {
  min-width: 52px;
  color: var(--orep-muted);
  text-align: right;
  font-size: 12px;
  font-weight: 820;
}

.course-detail {
  width: min(1260px, 100%);
  margin: 0 auto;
}

.back-link {
  border: 0;
  background: transparent;
  color: var(--orep-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: inherit;
  font-weight: 820;
  cursor: pointer;
  margin-bottom: 16px;
}

.detail-tabs {
  display: flex;
  gap: 8px;
  margin: 18px 0;
}

.empty-panel {
  border-radius: 16px;
  padding: 18px;
  color: inherit;
  text-decoration: none;
}

.empty-panel strong,
.empty-panel span {
  display: block;
}

.empty-panel strong {
  margin-top: 18px;
  color: var(--orep-text-strong);
  font-size: 17px;
}

.empty-panel span {
  margin-top: 8px;
  color: var(--orep-muted);
  font-size: 13px;
}

.empty-panel {
  grid-column: 1 / -1;
  text-align: center;
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

.course-page {
  background: transparent;
}

.course-page__inner {
  width: 100%;
  max-width: 100%;
  padding: 0 0 var(--ds-space-6, 24px);
}

.course-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(260px, 330px);
  gap: 22px;
  align-items: end;
  padding: 0 0 20px;
  margin-bottom: 14px;
  overflow: hidden;
}

.course-hero::after {
  display: none;
}

.course-hero__copy h1 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.course-hero__copy p {
  max-width: 760px;
  margin: 6px 0 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.55;
}

.course-hero__actions {
  position: relative;
  z-index: 1;
  padding-bottom: 3px;
}

.course-hero__progress {
  position: relative;
  z-index: 1;
  min-height: 76px;
  display: grid;
  align-content: center;
  gap: 9px;
  padding: 12px 0 0 28px;
}

.course-hero__progress::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 2px;
  width: 1px;
  background: var(--ds-line);
}

.course-hero__progress div {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 18px;
}

.course-hero__progress span,
.course-hero__progress p {
  color: var(--orep-muted);
  font-size: 14px;
  font-weight: 780;
}

.course-hero__progress strong {
  color: var(--orep-text-strong);
  font-size: 18px;
  line-height: 1;
}

.course-hero__progress i {
  height: 7px;
  border-radius: 999px;
  background: oklch(0.91 0.01 55);
  overflow: hidden;
}

.course-hero__progress b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--orep-orange);
}

.course-hero__progress p {
  margin: 0;
}

.course-hero__progress-line {
  display: grid !important;
  grid-template-columns: auto minmax(110px, 1fr);
  align-items: center !important;
  gap: 10px !important;
}

.course-hero__progress-line small {
  color: var(--orep-muted);
  font-size: 11px;
  white-space: nowrap;
}

.course-hero__progress-line i {
  width: 100%;
}

.course-layout {
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 18px;
}

.course-aside {
  position: sticky;
  top: calc(var(--header-height) + 18px);
  display: grid;
  gap: 14px;
}

.course-sidebar,
.course-main,
.weekly-plan-card {
  box-shadow: none;
}

.course-sidebar {
  position: static;
  top: auto;
  height: 330px;
  max-height: none;
  overflow: hidden;
  border-radius: 18px;
  padding: 18px 16px 20px;
  gap: 14px;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
}

.course-sidebar__head {
  border-bottom: 0;
  margin-bottom: 8px;
  padding: 0;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.course-sidebar__head strong {
  font-size: 20px;
  font-weight: 900;
}

.course-sidebar__head span {
  margin: 0;
  font-size: 14px;
  font-weight: 780;
}

.course-search input {
  width: 100%;
  height: 40px;
  border: 0;
  border-radius: 10px;
  background: oklch(0.972 0.004 55);
  color: var(--orep-text-strong);
  padding: 0 14px;
  font: inherit;
  font-weight: 760;
  outline: none;
}

.course-search input:focus {
  box-shadow: inset 0 0 0 1px oklch(0.82 0.08 50);
  background: oklch(0.99 0.004 55);
}

.category-scroll {
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: oklch(0.82 0.02 55) transparent;
}

.category-scroll::-webkit-scrollbar {
  width: 5px;
}

.category-scroll::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: oklch(0.82 0.02 55);
}

.category-item {
  min-height: 34px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  padding: 0 10px;
  font-size: 14px;
}

.category-item--root {
  min-height: 38px;
  margin-bottom: 2px;
  background: oklch(0.982 0.004 55);
  font-weight: 900;
}

.category-item--child {
  min-height: 32px;
  border: 0;
  background: transparent;
  color: var(--orep-muted);
  font-size: 13px;
}

.category-item.active {
  background: var(--orep-orange-wash);
  color: var(--orep-orange);
  box-shadow: none;
}

.category-item b {
  background: transparent;
}

.category-tree {
  gap: 10px;
}

.category-group {
  gap: 3px;
}

.category-group__head {
  min-height: 30px;
  padding: 0 2px;
  color: var(--orep-text-strong);
  font-size: 13px;
}

.category-group__head::before {
  font-size: 13px;
}

.category-group__head b {
  color: var(--orep-muted);
  font-size: 12px;
}

.category-group__children {
  gap: 2px;
  padding-left: 16px;
}

.category-group__children::before {
  left: 5px;
  top: 7px;
  bottom: 7px;
  background: oklch(0.92 0.008 55);
}

.category-item--child::before {
  left: -10px;
  width: 8px;
  background: oklch(0.92 0.008 55);
}

.learning-suggestions {
  padding: var(--ds-space-2) var(--ds-space-1) var(--ds-space-1);
}

.learning-suggestions header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-3);
}

.learning-suggestions__accent {
  width: 3px;
  height: 14px;
  border-radius: var(--ds-radius-pill);
  background: var(--ds-orange-action);
}

.learning-suggestions h2 {
  margin: 0;
  color: var(--ds-ink);
  font-size: var(--ds-text-caption);
  font-weight: var(--ds-weight-bold);
  line-height: var(--ds-leading-title);
}

.learning-suggestion-list {
  display: grid;
  gap: var(--ds-space-3);
}

.learning-suggestion-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  align-items: start;
  gap: var(--ds-space-2);
}

.learning-suggestion-dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 999px;
  background: var(--ds-faint);
  box-shadow: 0 0 0 3px var(--ds-input-readonly-bg);
}

.learning-suggestion-dot.is-active {
  background: var(--ds-orange-action);
  box-shadow: 0 0 0 3px var(--ds-orange-wash);
}

.learning-suggestion-dot.is-available {
  background: var(--ds-orange-400);
  box-shadow: 0 0 0 3px var(--ds-orange-wash);
}

.learning-suggestion-dot.is-done {
  background: var(--ds-green);
  box-shadow: 0 0 0 3px var(--ds-green-soft);
}

.learning-suggestion-item strong,
.learning-suggestion-item span {
  display: block;
}

.learning-suggestion-item strong {
  color: var(--ds-ink-2);
  font-size: var(--ds-text-label);
  font-weight: var(--ds-weight-semibold);
  line-height: 1.4;
}

.learning-suggestion-item span {
  margin-top: 3px;
  color: var(--ds-faint);
  font-size: var(--ds-text-micro);
  font-weight: var(--ds-weight-medium);
  line-height: 1.5;
}

.course-main {
  border-radius: 18px;
  padding: 0;
  border: 0;
  background: transparent;
}

.filter-row {
  min-height: 64px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 16px;
  background: var(--orep-surface-raised);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  margin: 0 0 16px;
  padding: 0 18px;
}

.filter-row__tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.course-grid {
  grid-template-columns: repeat(auto-fill, minmax(238px, 1fr));
  gap: 22px 24px;
}

.course-card {
  min-height: 304px;
  border-radius: 7px;
  box-shadow: var(--ds-card-shadow);
  background: var(--orep-surface-raised);
  border: 1px solid oklch(0.92 0.006 55);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.course-card:hover {
  border-color: var(--ds-line-strong);
  box-shadow: var(--ds-card-shadow);
}

.course-card__cover {
  position: relative;
  aspect-ratio: 16 / 9;
  flex: 0 0 auto;
  background: var(--ds-btn-secondary-bg-active);
  background-size: cover;
  background-position: center;
  color: var(--orep-surface-raised);
  display: block;
  padding: 0;
  overflow: hidden;
}

.course-card:first-child .course-card__cover {
  background: var(--ds-surface-subtle);
  color: var(--ds-muted);
}

.course-card__cover.has-image {
  background: oklch(0.965 0.006 55);
  color: var(--orep-surface-raised);
}

.course-card__cover-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  padding: 0;
}

.course-card__badges {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 10px;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.course-card__badges b,
.course-card__badges em {
  min-height: 27px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  font-style: normal;
  font-weight: 880;
  white-space: nowrap;
  box-shadow: 0 4px 10px oklch(0.2 0.015 45 / 0.1);
}

.course-card__badges b {
  background: var(--orep-orange-soft);
  color: var(--orep-orange);
  border: 1px solid oklch(0.9 0.06 55);
}

.course-card__badges em {
  max-width: 54%;
  background: var(--orep-text-strong);
  color: var(--orep-surface-raised);
  border: 1px solid oklch(0.24 0.01 45);
  overflow: hidden;
  text-overflow: ellipsis;
}

.course-card__body {
  position: static;
  min-height: 166px;
  padding: 13px 15px 12px;
  display: grid;
  grid-template-rows: 24px 19px 19px minmax(44px, auto) 8px;
  align-content: start;
  gap: 6px;
  flex: 1;
}

.course-card h2 {
  align-self: center;
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 16px;
  line-height: 1.35;
  font-weight: 880;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-card__source {
  color: oklch(0.47 0.02 55);
  font-size: 13px;
  font-weight: 680;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-card__meta {
  color: oklch(0.62 0.014 55);
  font-size: 12px;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-card p {
  min-height: 44px;
  border-radius: 7px;
  margin: 0;
  padding: 8px 10px;
  background: oklch(0.975 0.003 55);
  font-size: 12px;
  line-height: 1.42;
  color: oklch(0.61 0.016 55);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.course-progress {
  width: 100%;
  align-self: end;
}

.course-progress i {
  height: 4px;
  background: oklch(0.93 0.01 55);
}

.course-detail-page {
  width: min(1520px, 100%);
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
}

.detail-back {
  margin-bottom: 14px;
  font-size: 15px;
}

.learning-detail-hero {
  min-height: 154px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 18px;
  background: var(--ds-card-bg);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  overflow: hidden;
}

.learning-detail-hero__copy {
  padding: 28px 34px;
}

.learning-detail-hero h1 {
  margin: 10px 0 8px;
  color: var(--orep-text-strong);
  font-size: 32px;
  line-height: 1.15;
  letter-spacing: 0;
}

.learning-detail-hero p {
  max-width: 780px;
  margin: 0;
  color: var(--orep-muted);
  font-size: 14px;
  line-height: 1.65;
}

.learning-detail-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

.learning-detail-hero__status {
  background: var(--ds-orange-wash);
  display: grid;
  align-content: center;
  gap: 10px;
  padding: 24px 30px;
}

.learning-detail-hero__status small {
  color: var(--orep-orange);
  font-size: 12px;
  font-weight: 900;
}

.learning-detail-hero__status strong {
  color: var(--orep-text-strong);
  font-size: 18px;
  line-height: 1.25;
}

.learning-detail-hero__status span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
  line-height: 1.55;
}

.learning-detail-hero__status b {
  width: fit-content;
  min-height: 28px;
  border-radius: 999px;
  background: var(--orep-surface-raised);
  color: var(--orep-orange);
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 900;
}

.learning-detail-layout {
  margin-top: 18px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(280px, 22vw, 360px);
  gap: 18px;
  align-items: start;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
}

.learning-detail-main,
.learning-detail-side .side-card {
  border: 1px solid var(--orep-border-soft);
  border-radius: 18px;
  background: var(--orep-surface-raised);
  box-shadow: none;
}

.learning-detail-main {
  padding: 22px;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
}

.learning-section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.learning-section-head h2 {
  margin: 0;
  color: var(--orep-text-strong);
  font-size: 24px;
  line-height: 1.25;
}

.learning-section-head span {
  color: var(--orep-muted);
  font-size: 14px;
  font-weight: 820;
  white-space: nowrap;
}

.learning-detail-tabs {
  margin: 0 0 18px;
}

.learning-chapter {
  display: grid;
  grid-template-columns: minmax(250px, 280px) minmax(0, 1fr);
  gap: 24px;
  padding: 20px 0;
  border-top: 1px solid var(--orep-border-soft);
}

.learning-chapter:first-child {
  border-top: 0;
  padding-top: 0;
}

.learning-chapter__title {
  display: grid;
  align-content: start;
  gap: 8px;
  min-width: 0;
  padding-top: 4px;
}

.learning-chapter__title strong {
  color: var(--orep-text-strong);
  font-size: 16px;
  line-height: 1.35;
}

.learning-chapter__title span {
  color: var(--orep-muted);
  font-size: 13px;
  font-weight: 820;
}

.learning-lesson-list {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.learning-lesson {
  width: 100%;
  min-height: 58px;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) minmax(96px, 118px) 74px;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 160ms var(--orep-ease-out), border-color 160ms var(--orep-ease-out), transform 160ms var(--orep-ease-out);
}

.learning-lesson:hover {
  border-color: oklch(0.9 0.026 55);
  background: oklch(0.985 0.012 55);
}

.learning-lesson.current {
  border-color: oklch(0.9 0.04 55);
  background: var(--orep-orange-wash);
}

.learning-lesson__number {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: oklch(0.974 0.004 55);
  color: var(--orep-muted);
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 900;
}

.learning-lesson.current .learning-lesson__number {
  background: var(--orep-orange);
  color: var(--orep-surface-raised);
}

.learning-lesson.completed .learning-lesson__number {
  color: var(--orep-green);
}

.learning-lesson__copy strong,
.learning-lesson__copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.learning-lesson__copy strong {
  color: var(--orep-text-strong);
  font-size: 15px;
  line-height: 1.35;
}

.learning-lesson__copy small {
  margin-top: 4px;
  color: var(--orep-muted);
  font-size: 12px;
  line-height: 1.35;
}

.learning-lesson__meta {
  color: var(--orep-muted);
  font-size: 12px;
  font-weight: 820;
  white-space: nowrap;
}

.learning-lesson em {
  min-height: 32px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  background: var(--orep-surface-raised);
  color: var(--orep-text-strong);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  font-style: normal;
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
}

.learning-lesson.current em {
  border-color: var(--orep-text-strong);
  background: var(--orep-text-strong);
  color: var(--orep-surface-raised);
}

.learning-detail-side {
  position: sticky;
  top: calc(var(--header-height) + 18px);
  display: grid;
  gap: 14px;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
  align-self: start;
}

.learning-detail-side .side-card {
  padding: 18px;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.learning-detail-side h2,
.detail-info-panel h3 {
  margin: 0 0 16px;
  color: var(--orep-text-strong);
  font-size: 20px;
  line-height: 1.25;
}

.learning-progress-card__main {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 10px;
}

.learning-progress-card__main span {
  color: var(--orep-muted);
  font-weight: 820;
}

.learning-progress-card__main strong {
  color: var(--orep-text-strong);
  font-size: 28px;
  line-height: 1;
}

.learning-progress-card i {
  height: 8px;
  border-radius: 999px;
  background: oklch(0.91 0.01 55);
  display: block;
  overflow: hidden;
}

.learning-progress-card b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--orep-orange);
}

.learning-progress-card p,
.learning-material-card p {
  margin: 12px 0 0;
  color: var(--orep-muted);
  font-size: 14px;
  font-weight: 780;
  line-height: 1.55;
}

.learning-material-card a,
.detail-resource,
.weak-card > span {
  min-height: 48px;
  border-top: 1px solid var(--orep-border-soft);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--orep-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 820;
  min-width: 0;
}

.learning-material-card a {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 32px;
  justify-content: stretch;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.learning-material-card a span,
.detail-resource span,
.weak-card > span span {
  display: block;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow-wrap: anywhere;
}

.material-name {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.learning-material-card a:first-of-type,
.detail-resource:first-of-type,
.weak-card > span:first-of-type {
  border-top: 0;
}

.learning-material-card b,
.detail-resource b,
.weak-card b {
  flex: 0 0 auto;
  color: var(--orep-orange);
  font-size: 13px;
  white-space: nowrap;
  justify-self: end;
}

.weak-card__box {
  border-radius: 14px;
  background: var(--orep-orange-wash);
  padding: 14px;
  margin-bottom: 12px;
}

.weak-card__box strong {
  display: block;
  color: var(--orep-text-strong);
  margin-bottom: 6px;
}

.weak-card__box p {
  margin: 0;
  color: var(--orep-muted);
  font-size: 13px;
  line-height: 1.6;
}

.detail-info-panel {
  border-top: 1px solid var(--orep-border-soft);
  padding-top: 18px;
}

.detail-info-panel p {
  margin: 0;
  max-width: 880px;
  color: var(--orep-muted);
  line-height: 1.8;
}

.detail-info-grid,
.detail-record-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.detail-info-grid span,
.detail-record-list span {
  min-height: 68px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 14px;
  background: oklch(0.985 0.006 55);
  color: var(--orep-muted);
  display: grid;
  align-content: center;
  gap: 6px;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 780;
}

.detail-info-grid b,
.detail-record-list b {
  color: var(--orep-text-strong);
  font-size: 15px;
}

.detail-resource-list {
  display: grid;
  border-top: 1px solid var(--orep-border-soft);
  padding-top: 8px;
}

@media (max-width: 1180px) {
  .course-hero {
    grid-template-columns: minmax(0, 1fr) auto minmax(240px, 300px);
    gap: 16px;
    padding: 0 0 20px;
}

  .course-hero__progress {
    min-height: 68px;
    padding-left: 18px;
  }

  .course-hero__progress::before {
    display: block;
  }

  .course-layout,
  .chapter-layout,
  .learning-detail-hero,
  .learning-detail-layout {
    grid-template-columns: 1fr;
  }

  .course-aside {
    position: static;
  }

  .course-sidebar,
  .chapter-summary,
  .learning-detail-side {
    position: static;
  }

  .course-sidebar {
    height: 320px;
  }

  .course-grid,
  .attachment-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .learning-detail-side {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
}

@media (max-width: 820px) {
  .course-page__inner {
    width: 100%;
    padding: 0 0 var(--ds-space-6, 24px);
  }

  .course-hero {
    grid-template-columns: 1fr;
    gap: 14px;
    padding: 0 0 20px;
  }

  .course-hero::after {
    width: 100%;
    height: 32px;
  }

  .course-hero__copy h1 {
    font-size: 24px;
  }

  .course-hero__actions {
    padding-bottom: 0;
  }

  .course-hero__actions :deep(.base-button) {
    width: fit-content;
  }

  .course-hero__progress {
    grid-column: auto;
    border-top: 1px solid oklch(0.9 0.026 55);
    min-height: 0;
    padding-left: 0;
    padding-top: 14px;
  }

  .course-hero__progress::before {
    display: none;
  }

  .filter-row {
    align-items: flex-start;
    flex-direction: column;
    padding: 14px;
  }

  .course-sidebar {
    height: auto;
    max-height: 420px;
  }

  .category-scroll {
    max-height: 270px;
  }

  .course-header,
  .featured-course,
  .detail-hero {
    grid-template-columns: 1fr;
  }

  .course-grid,
  .attachment-grid {
    grid-template-columns: 1fr;
  }

  .learning-detail-hero__copy {
    padding: 26px 22px;
  }

  .learning-detail-hero h1 {
    font-size: 30px;
  }

  .learning-detail-hero__status {
    padding: 22px;
  }

  .learning-section-head,
  .learning-lesson {
    align-items: flex-start;
  }

  .learning-section-head {
    flex-direction: column;
    gap: 8px;
  }

  .learning-section-head span {
    white-space: normal;
  }

  .learning-chapter {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .learning-lesson {
    grid-template-columns: 40px minmax(0, 1fr);
    padding: 14px;
  }

  .learning-lesson__meta,
  .learning-lesson em {
    grid-column: 2;
  }

  .learning-detail-side,
  .detail-info-grid,
  .detail-record-list {
    grid-template-columns: 1fr;
  }
}

/* Workspace typography and visual normalization. Keep this layer last. */
.course-page {
  min-height: 100%;
  background: transparent;
}

.course-page__inner {
  width: 100%;
  padding: 0 0 var(--ds-space-6, 24px);
  box-sizing: border-box;
}

.course-hero {
  grid-template-columns: minmax(0, 1fr) auto minmax(240px, 300px);
  gap: clamp(14px, 1.4vw, 22px);
  min-height: 98px;
  margin-bottom: 18px;
  padding: 0 0 20px;
  align-items: center;
}

.course-hero::after {
  opacity: 0.34;
}

.course-hero__copy h1,
.learning-detail-hero h1 {
  margin: 0;
  color: var(--workspace-ink-900);
  font-size: clamp(22px, 1.45vw, 26px);
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: -0.01em;
}

.course-hero__copy p,
.learning-detail-hero p {
  max-width: 760px;
  margin-top: 7px;
  color: var(--workspace-ink-500);
  font-size: clamp(12px, 0.8vw, 14px);
  font-weight: 600;
  line-height: 1.65;
}

.course-layout {
  grid-template-columns: clamp(232px, 15vw, 280px) minmax(0, 1fr);
  gap: clamp(16px, 1.4vw, 22px);
}

.course-sidebar,
.weekly-plan-card,
.filter-row,
.course-card,
.learning-detail-hero,
.learning-detail-main,
.learning-detail-side,
.detail-info-panel,
.detail-resource {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.course-sidebar {
  height: auto;
  min-height: 330px;
  padding: 18px 16px;
  gap: 12px;
}

.course-sidebar__head strong,
.weekly-plan-card h2,
.learning-section-head h2,
.detail-info-panel h3,
.learning-detail-side h2 {
  color: var(--workspace-ink-900);
  font-size: clamp(15px, 0.95vw, 17px);
  font-weight: 800;
  line-height: 1.3;
}

.course-sidebar__head span,
.weekly-plan-card header span,
.sort-button,
.course-card__source,
.course-card__meta {
  color: var(--workspace-ink-500);
  font-size: 12px;
  font-weight: 700;
}

.course-search input,
.category-item--root,
.weekly-plan-item,
.course-card p {
  background: var(--ds-btn-secondary-bg-hover);
}

.course-search input {
  min-height: var(--ds-input-height-sm);
  border: 1px solid var(--ds-input-border);
  border-radius: var(--ds-input-radius);
  color: var(--ds-ink-2);
  background: var(--ds-input-bg);
  transition: border-color var(--ds-control-transition), box-shadow var(--ds-control-transition);
}

.course-search input:hover {
  border-color: var(--ds-input-border-hover);
}

.course-search input:focus-visible {
  border-color: var(--ds-input-focus-border);
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
  box-shadow: var(--ds-input-focus-ring);
}

.category-item,
.category-group__head {
  color: var(--workspace-ink-700);
  font-size: 13px;
  font-weight: 750;
}

.category-item.active {
  color: var(--ds-btn-selected-fg);
  background: var(--ds-btn-selected-bg);
  box-shadow: inset 0 0 0 1px var(--ds-btn-selected-border);
}

.filter-row {
  min-height: 58px;
  padding: 10px 16px;
}

.course-grid {
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: clamp(16px, 1.4vw, 22px);
}

.course-card {
  min-height: 300px;
  border-radius: 18px;
  overflow: hidden;
}

.course-card h2 {
  color: var(--workspace-ink-900);
  font-size: 16px;
  font-weight: 800;
}

.course-card p {
  color: var(--workspace-ink-500);
  font-size: 12px;
}

.course-progress b,
.detail-progress b,
.course-hero__progress b {
  background: var(--ds-orange);
}

.course-detail-page,
.learning-detail-layout,
.learning-detail-main,
.learning-detail-side,
.detail-info-panel,
.detail-resource-list {
  min-width: 0;
  max-width: 100%;
}

.learning-detail-main {
  align-self: start;
}

.detail-info-panel {
  overflow: hidden;
  padding: 18px;
  border-top: 0;
}

.detail-info-panel h3,
.learning-detail-side h2 {
  margin-bottom: 12px;
}

.detail-info-copy,
.detail-info-panel p {
  max-width: 72ch;
  color: var(--workspace-ink-500);
  font-size: 13px;
  font-weight: 620;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.detail-info-grid,
.detail-record-list {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.detail-info-grid span,
.detail-record-list span {
  min-width: 0;
  min-height: 64px;
  border-color: rgba(240, 222, 213, 0.74);
  background: var(--ds-btn-secondary-bg-hover);
  box-shadow: none;
}

.detail-info-grid b,
.detail-record-list b {
  min-width: 0;
  overflow: hidden;
  color: var(--workspace-ink-900);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-resource-list {
  align-content: start;
  gap: 8px;
  min-height: 0;
  padding-top: 0;
  border-top: 0;
}

.detail-resource,
.learning-material-card a {
  min-width: 0;
  max-width: 100%;
  min-height: 44px;
  box-sizing: border-box;
}

.detail-resource {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 46px;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  border-top: 0;
  border-radius: 12px;
}

.detail-resource:hover,
.learning-material-card a:hover {
  border-color: var(--ds-btn-selected-border);
  background: var(--ds-orange-wash);
}

.learning-material-card a {
  grid-template-columns: minmax(0, 1fr) 42px;
  min-height: 40px;
}

.material-name {
  display: block;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  color: var(--workspace-ink-500);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-resource b,
.learning-material-card b {
  justify-self: end;
  min-width: 34px;
  text-align: right;
}

.learning-material-card p {
  margin-top: 8px;
}

@media (max-width: 820px) {
  .course-hero,
  .course-layout,
  .learning-detail-layout {
    grid-template-columns: 1fr;
  }

  .course-hero__copy h1,
  .learning-detail-hero h1 {
    font-size: 22px;
  }

  .detail-resource {
    grid-template-columns: minmax(0, 1fr) 42px;
  }
}
</style>
