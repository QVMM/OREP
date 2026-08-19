<template>
  <div class="phase1-round2">
    <n-card title="Step 2: 内容生成与确认" class="content-card">
      <template #header-extra>
        <n-tag type="warning">Round 2</n-tag>
      </template>

      <!-- 步骤指示器 -->
      <n-steps :current="currentStep" class="steps">
        <n-step title="填写问卷" description="填写项目信息" />
        <n-step title="确认大纲" description="确认PPT大纲" />
        <n-step title="生成内容" description="AI生成内容" />
        <n-step title="预览" description="HTML预览" />
      </n-steps>

      <n-divider />

      <!-- 无数据提示 -->
      <div v-if="!hasOutline" class="empty-state">
        <n-empty description="请先完成大纲生成">
          <template #extra>
            <n-button type="primary" @click="goToRound1">
              去生成大纲
            </n-button>
          </template>
        </n-empty>
      </div>

      <!-- 内容展示与编辑 -->
      <div v-else class="content-section">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-section">
          <n-spin size="large" />
          <p class="loading-text">正在生成内容，请稍候...</p>
          <n-progress
            type="line"
            :percentage="progressPercentage"
            :show-indicator="true"
            status="success"
          />
        </div>

        <!-- 内容列表 -->
        <div v-else-if="contentData" class="content-list">
          <div class="content-header">
            <h3>PPT 内容详情</h3>
            <n-space>
              <n-button @click="handleExpandAll">
                {{ isAllExpanded ? '收起全部' : '展开全部' }}
              </n-button>
              <n-button type="primary" @click="handleRegenerate">
                重新生成
              </n-button>
            </n-space>
          </div>

          <n-collapse :default-expanded-names="expandedNames" @update:expanded-names="handleExpandChange">
            <n-collapse-item
              v-for="(slide, index) in contentSlides"
              :key="index"
              :title="slide.title"
              :name="index"
            >
              <template #header>
                <div class="slide-header">
                  <n-tag :type="getSlideTypeColor(slide.type)" size="small">
                    {{ index + 1 }}
                  </n-tag>
                  <span class="slide-title">{{ slide.title }}</span>
                  <n-tag v-if="slide.status" :type="getStatusType(slide.status)" size="small">
                    {{ slide.status }}
                  </n-tag>
                </div>
              </template>

              <div class="slide-content">
                <div v-if="slide.bullet_points" class="bullet-points">
                  <h4>要点</h4>
                  <ul>
                    <li v-for="(point, pIndex) in slide.bullet_points" :key="pIndex">
                      {{ point }}
                    </li>
                  </ul>
                </div>

                <div v-if="slide.content" class="content-text">
                  <h4>详细内容</h4>
                  <p>{{ slide.content }}</p>
                </div>

                <div v-if="slide.notes" class="speaker-notes">
                  <h4>演讲备注</h4>
                  <p>{{ slide.notes }}</p>
                </div>

                <div v-if="slide.suggestions" class="ai-suggestions">
                  <h4>AI 建议</h4>
                  <n-alert type="info" :show-icon="false">
                    {{ slide.suggestions }}
                  </n-alert>
                </div>

                <!-- 编辑按钮 -->
                <div class="slide-actions">
                  <n-button size="small" @click="handleEditSlide(slide, index)">
                    编辑此页
                  </n-button>
                </div>
              </div>
            </n-collapse-item>
          </n-collapse>

          <!-- 内容统计 -->
          <div class="content-stats">
            <n-grid :cols="4" :x-gap="20">
              <n-gi>
                <n-statistic label="页数" :value="contentSlides.length" />
              </n-gi>
              <n-gi>
                <n-statistic label="总字数" :value="totalWords" />
              </n-gi>
              <n-gi>
                <n-statistic label="预计演讲时长" :value="estimatedTime" suffix="分钟" />
              </n-gi>
              <n-gi>
                <n-statistic label="完成度" :value="completionRate" suffix="%" />
              </n-gi>
            </n-grid>
          </div>
        </div>

        <!-- 初始状态：还未生成内容 -->
        <div v-else class="init-section">
          <n-result status="info" title="准备生成内容" description="请确认大纲后，点击开始生成内容">
            <template #footer>
              <n-space justify="center">
                <n-button @click="goToRound1">返回大纲</n-button>
                <n-button type="primary" @click="handleStartGenerate" :loading="loading">
                  开始生成内容
                </n-button>
              </n-space>
            </template>
          </n-result>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div v-if="contentData && !loading" class="actions">
        <n-button @click="goToRound1">
          返回大纲
        </n-button>
        <n-button
          type="primary"
          @click="handleConfirm"
          :loading="confirming"
        >
          确认进入预览
        </n-button>
      </div>

      <!-- 编辑弹窗 -->
      <n-modal
        v-model:show="editModalVisible"
        preset="card"
        title="编辑幻灯片内容"
        style="width: 700px"
        :bordered="false"
      >
        <n-form label-placement="left" label-width="100">
          <n-form-item label="标题">
            <n-input v-model:value="editingSlide.title" />
          </n-form-item>
          <n-form-item label="详细内容">
            <n-input
              v-model:value="editingSlide.content"
              type="textarea"
              :rows="6"
              placeholder="请输入详细内容"
            />
          </n-form-item>
          <n-form-item label="演讲备注">
            <n-input
              v-model:value="editingSlide.notes"
              type="textarea"
              :rows="3"
              placeholder="请输入演讲备注"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="editModalVisible = false">取消</n-button>
            <n-button type="primary" @click="handleSaveEdit">保存</n-button>
          </n-space>
        </template>
      </n-modal>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePPTStore } from '@/stores/pptStore'

const router = useRouter()
const pptStore = usePPTStore()

// 状态
const currentStep = ref(2)
const loading = ref(false)
const confirming = ref(false)
const isAllExpanded = ref(true)
const expandedNames = ref([])
const progressPercentage = ref(0)
const editModalVisible = ref(false)
const editingIndex = ref(-1)

// 编辑中的幻灯片
const editingSlide = ref({
  title: '',
  content: '',
  notes: ''
})

// 是否有大纲数据
const hasOutline = computed(() => !!pptStore.outline)

// 获取内容数据
const contentData = computed(() => pptStore.content)

// 转换内容数据为幻灯片数组
const contentSlides = computed(() => {
  if (!contentData.value) return []

  const data = contentData.value
  if (Array.isArray(data.slides)) {
    return data.slides
  }
  if (Array.isArray(data.contents)) {
    return data.contents
  }
  if (Array.isArray(data)) {
    return data
  }

  return []
})

// 总字数
const totalWords = computed(() => {
  return contentSlides.value.reduce((sum, slide) => {
    const text = slide.content || ''
    return sum + text.replace(/\s/g, '').length
  }, 0)
})

// 预计时长
const estimatedTime = computed(() => {
  return Math.ceil(totalWords.value / 200) // 假设每分钟200字
})

// 完成度
const completionRate = computed(() => {
  const slides = contentSlides.value
  if (slides.length === 0) return 0

  const completed = slides.filter(s => s.content && s.content.length > 0).length
  return Math.round((completed / slides.length) * 100)
})

// 获取幻灯片类型颜色
function getSlideTypeColor(type) {
  const colorMap = {
    cover: 'error',
    toc: 'warning',
    content: 'default',
    image: 'info',
    data: 'success',
    summary: 'success',
    ending: 'error'
  }
  return colorMap[type] || 'default'
}

// 获取状态类型
function getStatusType(status) {
  const typeMap = {
    generated: 'success',
    pending: 'warning',
    failed: 'error',
    editing: 'info'
  }
  return typeMap[status] || 'default'
}

// 跳转到 Round 1
function goToRound1() {
  router.push('/phase1/round1')
}

// 展开/收起变化
function handleExpandChange(names) {
  expandedNames.value = names
}

// 展开全部
function handleExpandAll() {
  if (isAllExpanded.value) {
    expandedNames.value = []
  } else {
    expandedNames.value = contentSlides.value.map((_, i) => i)
  }
  isAllExpanded.value = !isAllExpanded.value
}

// 开始生成内容
async function handleStartGenerate() {
  loading.value = true
  progressPercentage.value = 0

  const progressTimer = setInterval(() => {
    if (progressPercentage.value < 90) {
      progressPercentage.value += Math.random() * 10
    }
  }, 500)

  try {
    await pptStore.generateContent(pptStore.outline)

    clearInterval(progressTimer)
    progressPercentage.value = 100

    // 默认展开所有
    expandedNames.value = contentSlides.value.map((_, i) => i)
  } catch (err) {
    clearInterval(progressTimer)
    console.error('生成内容失败:', err)
  } finally {
    loading.value = false
  }
}

// 重新生成
function handleRegenerate() {
  handleStartGenerate()
}

// 编辑幻灯片
function handleEditSlide(slide, index) {
  editingIndex.value = index
  editingSlide.value = { ...slide }
  editModalVisible.value = true
}

// 保存编辑
function handleSaveEdit() {
  if (editingIndex.value >= 0) {
    const slides = [...contentSlides.value]
    slides[editingIndex.value] = {
      ...slides[editingIndex.value],
      ...editingSlide.value,
      status: 'editing'
    }
    pptStore.setContent({ ...contentData.value, slides })
  }
  editModalVisible.value = false
}

// 确认进入预览
async function handleConfirm() {
  confirming.value = true
  try {
    pptStore.setCurrentRound(3)
    pptStore.setCurrentPhase(1)
    router.push('/phase1/round3')
  } finally {
    confirming.value = false
  }
}
</script>

<style scoped>
.phase1-round2 {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.content-card {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.steps {
  margin-bottom: 20px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
}

.loading-text {
  margin: 16px 0;
  color: #666;
}

.init-section {
  padding: 40px 0;
}

.content-section {
  margin-top: 20px;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.content-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.slide-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slide-title {
  font-weight: 500;
}

.slide-content {
  padding: 12px 0;
}

.slide-content h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #666;
}

.bullet-points ul {
  margin: 0;
  padding-left: 20px;
}

.bullet-points li {
  margin-bottom: 4px;
  line-height: 1.6;
}

.content-text p {
  margin: 0;
  line-height: 1.8;
}

.speaker-notes {
  margin-top: 16px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
}

.speaker-notes p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.ai-suggestions {
  margin-top: 16px;
}

.slide-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.content-stats {
  margin-top: 24px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
