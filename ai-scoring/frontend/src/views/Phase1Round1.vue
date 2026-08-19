<template>
  <div class="phase1-round1">
    <n-card title="Step 1: 大纲生成与确认" class="outline-card">
      <template #header-extra>
        <n-tag type="info">Round 1</n-tag>
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
      <div v-if="!outlineData" class="empty-state">
        <n-empty description="暂无生成的大纲">
          <template #extra>
            <n-button type="primary" @click="goToGenerator">
              去填写问卷
            </n-button>
          </template>
        </n-empty>
      </div>

      <!-- 大纲列表 -->
      <div v-else class="outline-section">
        <div class="outline-header">
          <h3>PPT 大纲</h3>
          <n-button text type="primary" @click="handleExpandAll">
            {{ isAllExpanded ? '收起全部' : '展开全部' }}
          </n-button>
        </div>

        <n-list hoverable clickable class="outline-list">
          <n-list-item
            v-for="(slide, index) in outlineSlides"
            :key="index"
            @click="handleSlideClick(slide, index)"
          >
            <template #prefix>
              <n-tag :type="getSlideTypeColor(slide.type)" size="small">
                {{ slide.slide || index + 1 }}
              </n-tag>
            </template>

            <n-thing>
              <template #header>
                <span class="slide-title">{{ slide.title }}</span>
              </template>
              <template #description>
                <span class="slide-type">{{ slide.type || '内容页' }}</span>
              </template>
              <template #default>
                <div v-if="slide.content" class="slide-content-preview">
                  {{ slide.content }}
                </div>
              </template>
            </n-thing>

            <template #suffix>
              <n-button text type="primary" @click.stop="handleEditSlide(slide, index)">
                <template #icon>
                  <n-icon><CreateOutline /></n-icon>
                </template>
              </n-button>
            </template>
          </n-list-item>
        </n-list>

        <!-- 大纲统计 -->
        <div class="outline-stats">
          <n-statistic label="幻灯片总数" :value="outlineSlides.length" />
          <n-statistic label="预计时长" :value="estimatedTime" suffix="分钟" />
        </div>
      </div>

      <!-- 操作按钮 -->
      <div v-if="outlineData" class="actions">
        <n-button @click="handleBack">
          返回修改
        </n-button>
        <n-button @click="handleEdit">
          编辑大纲
        </n-button>
        <n-button
          type="primary"
          @click="handleConfirm"
          :loading="confirming"
        >
          确认进入下一步
        </n-button>
      </div>

      <!-- 编辑弹窗 -->
      <n-modal
        v-model:show="editModalVisible"
        preset="card"
        title="编辑大纲项"
        style="width: 600px"
        :bordered="false"
      >
        <n-form label-placement="left" label-width="80">
          <n-form-item label="标题">
            <n-input v-model:value="editingSlide.title" />
          </n-form-item>
          <n-form-item label="类型">
            <n-select
              v-model:value="editingSlide.type"
              :options="slideTypeOptions"
            />
          </n-form-item>
          <n-form-item label="内容">
            <n-input
              v-model:value="editingSlide.content"
              type="textarea"
              :rows="4"
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

      <!-- 新建大纲项弹窗 -->
      <n-modal
        v-model:show="addModalVisible"
        preset="card"
        title="添加大纲项"
        style="width: 600px"
        :bordered="false"
      >
        <n-form label-placement="left" label-width="80">
          <n-form-item label="标题">
            <n-input v-model:value="newSlide.title" placeholder="请输入标题" />
          </n-form-item>
          <n-form-item label="类型">
            <n-select
              v-model:value="newSlide.type"
              :options="slideTypeOptions"
            />
          </n-form-item>
          <n-form-item label="内容">
            <n-input
              v-model:value="newSlide.content"
              type="textarea"
              :rows="4"
              placeholder="请输入内容概要"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="addModalVisible = false">取消</n-button>
            <n-button type="primary" @click="handleAddSlide">添加</n-button>
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
import { CreateOutline } from '@vicons/ionicons5'

const router = useRouter()
const pptStore = usePPTStore()

// 状态
const currentStep = ref(1)
const confirming = ref(false)
const isAllExpanded = ref(true)
const editModalVisible = ref(false)
const addModalVisible = ref(false)
const editingIndex = ref(-1)

// 编辑中的大纲项
const editingSlide = ref({
  title: '',
  type: 'content',
  content: ''
})

// 新建的大纲项
const newSlide = ref({
  title: '',
  type: 'content',
  content: ''
})

// 幻灯片类型选项
const slideTypeOptions = [
  { label: '封面', value: 'cover' },
  { label: '目录', value: 'toc' },
  { label: '内容页', value: 'content' },
  { label: '图片页', value: 'image' },
  { label: '数据页', value: 'data' },
  { label: '总结页', value: 'summary' },
  { label: '结束页', value: 'ending' }
]

// 获取大纲数据
const outlineData = computed(() => pptStore.outline)

// 转换大纲数据为幻灯片数组
const outlineSlides = computed(() => {
  if (!outlineData.value) return []

  const data = outlineData.value
  if (Array.isArray(data.outline)) {
    return data.outline
  }

  // 如果是对象形式，尝试提取
  if (data.slides) {
    return data.slides
  }

  if (data.pages) {
    return data.pages
  }

  // 如果是数组直接返回
  if (Array.isArray(data)) {
    return data
  }

  return []
})

// 预计时长（每页约2分钟）
const estimatedTime = computed(() => {
  return outlineSlides.value.length * 2
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

// 跳转到问卷页面
function goToGenerator() {
  router.push('/generate')
}

// 返回修改
function handleBack() {
  router.push('/generate')
}

// 展开/收起全部
function handleExpandAll() {
  isAllExpanded.value = !isAllExpanded.value
}

// 点击幻灯片
function handleSlideClick(slide, index) {
  handleEditSlide(slide, index)
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
    const slides = [...outlineSlides.value]
    slides[editingIndex.value] = { ...editingSlide.value }
    pptStore.setOutline({ ...outlineData.value, outline: slides })
  }
  editModalVisible.value = false
}

// 添加幻灯片
function handleAddSlide() {
  const slides = [...outlineSlides.value]
  slides.push({ ...newSlide.value })
  pptStore.setOutline({ ...outlineData.value, outline: slides })

  newSlide.value = { title: '', type: 'content', content: '' }
  addModalVisible.value = false
}

// 编辑大纲
function handleEdit() {
  addModalVisible.value = true
}

// 确认进入下一步
async function handleConfirm() {
  confirming.value = true
  try {
    // 保存当前状态
    pptStore.setCurrentRound(2)
    pptStore.setCurrentPhase(1)

    // 跳转到 Round 2
    router.push('/phase1/round2')
  } finally {
    confirming.value = false
  }
}
</script>

<style scoped>
.phase1-round1 {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.outline-card {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.steps {
  margin-bottom: 20px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.outline-section {
  margin-top: 20px;
}

.outline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.outline-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.outline-list {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}

.slide-title {
  font-weight: 500;
}

.slide-type {
  color: #666;
  font-size: 12px;
}

.slide-content-preview {
  margin-top: 8px;
  color: #999;
  font-size: 13px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.outline-stats {
  display: flex;
  gap: 40px;
  margin-top: 24px;
  padding: 16px;
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
