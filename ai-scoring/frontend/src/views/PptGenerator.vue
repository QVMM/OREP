<template>
  <div class="ppt-generator">
    <n-card title="PPT 生成" class="generator-card">
      <template #header-extra>
        <n-tag v-if="result" type="success" size="small">已完成</n-tag>
      </template>

      <!-- 问卷表单 -->
      <n-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-placement="top"
        class="survey-form"
      >
        <n-grid :cols="2" :x-gap="20">
          <n-gi>
            <n-form-item label="项目名称" path="project_name">
              <n-input
                v-model:value="formData.project_name"
                placeholder="请输入项目名称"
              />
            </n-form-item>
          </n-gi>

          <n-gi>
            <n-form-item label="团队规模" path="team_size">
              <n-input-number
                v-model:value="formData.team_size"
                :min="1"
                :max="1000"
                placeholder="请输入团队规模"
                style="width: 100%"
              />
            </n-form-item>
          </n-gi>
        </n-grid>

        <n-form-item label="核心问题" path="core_problem">
          <n-input
            v-model:value="formData.core_problem"
            type="textarea"
            placeholder="描述项目要解决的核心问题"
            :rows="3"
          />
        </n-form-item>

        <n-form-item label="目标市场" path="target_market">
          <n-input
            v-model:value="formData.target_market"
            type="textarea"
            placeholder="描述目标市场"
            :rows="2"
          />
        </n-form-item>

        <n-grid :cols="2" :x-gap="20">
          <n-gi>
            <n-form-item label="解决方案" path="solution_description">
              <n-input
                v-model:value="formData.solution_description"
                type="textarea"
                placeholder="描述您的解决方案"
                :rows="3"
              />
            </n-form-item>
          </n-gi>

          <n-gi>
            <n-form-item label="商业模式" path="business_model">
              <n-input
                v-model:value="formData.business_model"
                type="textarea"
                placeholder="描述商业模式"
                :rows="3"
              />
            </n-form-item>
          </n-gi>
        </n-grid>

        <n-grid :cols="2" :x-gap="20">
          <n-gi>
            <n-form-item label="竞争优势" path="competitive_advantage">
              <n-input
                v-model:value="formData.competitive_advantage"
                type="textarea"
                placeholder="描述竞争优势"
                :rows="2"
              />
            </n-form-item>
          </n-gi>

          <n-gi>
            <n-form-item label="融资阶段" path="funding_stage">
              <n-select
                v-model:value="formData.funding_stage"
                :options="fundingStageOptions"
                placeholder="请选择融资阶段"
              />
            </n-form-item>
          </n-gi>
        </n-grid>

        <n-form-item label="关键指标" path="key_metrics">
          <n-input
            v-model:value="formData.key_metrics"
            type="textarea"
            placeholder="如：用户数、收入、增长率等关键指标"
            :rows="2"
          />
        </n-form-item>
      </n-form>

      <!-- 操作按钮 -->
      <div class="actions">
        <n-button @click="handleReset" :disabled="loading">
          重置
        </n-button>
        <n-button
          type="primary"
          @click="handleGenerate"
          :loading="loading"
          :disabled="!!result"
        >
          生成 PPT
        </n-button>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-section">
        <n-spin size="large" />
        <p class="loading-text">正在生成大纲，请稍候...</p>
        <n-progress
          type="line"
          :percentage="progressPercentage"
          :show-indicator="true"
          status="success"
        />
      </div>

      <!-- 结果展示 -->
      <div v-if="result" class="result-section">
        <n-divider>生成结果</n-divider>

        <n-alert type="success" title="生成成功" class="result-alert">
          项目画像已生成，现在可以进入下一步确认大纲。
        </n-alert>

        <div class="result-data">
          <n-descriptions label-placement="top" bordered>
            <n-descriptions-item label="任务ID">
              {{ result.task_id || result.id || 'N/A' }}
            </n-descriptions-item>
            <n-descriptions-item label="项目名称">
              {{ result.project_name || formData.project_name }}
            </n-descriptions-item>
          </n-descriptions>
        </div>

        <div class="result-actions">
          <n-button type="primary" @click="handleNextStep">
            进入大纲确认
          </n-button>
        </div>
      </div>

      <!-- 错误展示 -->
      <div v-if="error" class="error-section">
        <n-alert type="error" :title="error">
          请检查输入内容后重试
        </n-alert>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePPTStore } from '@/stores/pptStore'

const router = useRouter()
const pptStore = usePPTStore()

// 表单引用
const formRef = ref(null)

// 加载状态
const loading = ref(false)
const progressPercentage = ref(0)
const error = ref(null)

// 表单数据
const formData = ref({
  project_name: '',
  team_size: 0,
  core_problem: '',
  target_market: '',
  solution_description: '',
  business_model: '',
  competitive_advantage: '',
  funding_stage: '',
  key_metrics: ''
})

// 融资阶段选项
const fundingStageOptions = [
  { label: '未融资', value: 'pre_seed' },
  { label: '种子轮', value: 'seed' },
  { label: '天使轮', value: 'angel' },
  { label: 'Pre-A轮', value: 'pre_a' },
  { label: 'A轮', value: 'a' },
  { label: 'B轮', value: 'b' },
  { label: 'C轮及以上', value: 'c_plus' },
  { label: '已盈利', value: 'profitable' }
]

// 表单验证规则
const rules = {
  project_name: {
    required: true,
    message: '请输入项目名称',
    trigger: 'blur'
  },
  core_problem: {
    required: true,
    message: '请描述核心问题',
    trigger: 'blur'
  }
}

// 结果数据
const result = computed(() => pptStore.outline)

// 模拟进度
let progressTimer = null

function startProgress() {
  progressPercentage.value = 0
  progressTimer = setInterval(() => {
    if (progressPercentage.value < 90) {
      progressPercentage.value += Math.random() * 15
    }
  }, 500)
}

function stopProgress() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
  progressPercentage.value = 100
}

// 生成 PPT
async function handleGenerate() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  error.value = null
  startProgress()

  try {
    // 保存表单数据到 store
    pptStore.setSurveyData(formData.value)

    // 调用 API 生成大纲
    const response = await pptStore.generateOutline(formData.value)

    stopProgress()

    // 跳转到 Phase1Round1 页面
    if (response) {
      router.push('/phase1/round1')
    }
  } catch (err) {
    stopProgress()
    error.value = err.message || '生成失败，请重试'
  } finally {
    loading.value = false
  }
}

// 重置表单
function handleReset() {
  formData.value = {
    project_name: '',
    team_size: 0,
    core_problem: '',
    target_market: '',
    solution_description: '',
    business_model: '',
    competitive_advantage: '',
    funding_stage: '',
    key_metrics: ''
  }
  error.value = null
  formRef.value?.restoreValidation()
}

// 进入下一步
function handleNextStep() {
  router.push('/phase1/round1')
}
</script>

<style scoped>
.ppt-generator {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.generator-card {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.survey-form {
  margin-bottom: 20px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
}

.loading-text {
  margin: 16px 0;
  color: #666;
}

.result-section {
  margin-top: 24px;
}

.result-alert {
  margin-bottom: 16px;
}

.result-data {
  margin-bottom: 20px;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.error-section {
  margin-top: 24px;
}
</style>