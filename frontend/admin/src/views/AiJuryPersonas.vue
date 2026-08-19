<template>
  <div class="jury-personas-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">AI评审团</span>
        <h1>维护 16 个 AI 评委视角</h1>
        <p>画像只影响关注重点和反馈风格，不改变统一评分标准。修改前建议先确认该画像在报告中的业务角色。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchPersonas">刷新</el-button>
        <el-button type="warning" plain @click="resetDefaults">恢复默认</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ personas.length }}</strong><span>画像总数</span><small>16人格评审团</small></article>
      <article class="admin-metric-card"><strong>{{ enabledCount }}</strong><span>已启用</span><small>参与报告复核</small></article>
      <article class="admin-metric-card"><strong>{{ disabledCount }}</strong><span>已停用</span><small>暂不参与复核</small></article>
      <article class="admin-metric-card"><strong>{{ focusItemCount }}</strong><span>重点观测点</span><small>所有画像合计</small></article>
    </section>

    <el-card class="admin-table-card page-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">画像列表</span>
            <span class="admin-panel-subtitle">编辑前先确认关注点、核心特质和重点评分项是否符合业务语义。</span>
          </div>
        </div>
      </template>

      <el-table :data="personas" v-loading="loading" border stripe>
        <el-table-column prop="code" label="类型" width="90" />
        <el-table-column prop="name" label="评委画像" min-width="160" />
        <el-table-column prop="short_label" label="关注点" min-width="180" show-overflow-tooltip />
        <el-table-column label="核心特质" min-width="220">
          <template #default="{ row }">
            <el-tag v-for="trait in row.judge_profile?.core_traits || []" :key="trait" size="small" effect="plain">
              {{ trait }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="重点评分项" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            {{ (row.rubric_focus?.primary_items || []).join(' / ') }}
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled === false ? 'info' : 'success'">
              {{ row.enabled === false ? '停用' : '启用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="openEditor(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showEditor" :title="`编辑 ${editForm.code} 评委画像`" width="860px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="画像名称">
              <el-input v-model="editForm.name" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="短标签">
              <el-input v-model="editForm.short_label" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="启用">
              <el-switch v-model="editForm.enabled" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="评审视角提示词">
          <el-input v-model="editForm.prompt_modifier" type="textarea" :rows="3" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="核心特质（逗号分隔）">
              <el-input v-model="profileText.core_traits" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="证据偏好（逗号分隔）">
              <el-input v-model="profileText.evidence_preference" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="评分风格">
          <el-input v-model="editForm.judge_profile.scoring_style" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="敏感风险（逗号分隔）">
          <el-input v-model="profileText.sensitive_risks" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="高分原因">
              <el-input v-model="editForm.judge_profile.likely_high_score_reason" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="低分原因">
              <el-input v-model="editForm.judge_profile.likely_low_score_reason" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="反馈风格">
          <el-input v-model="editForm.judge_profile.feedback_style" type="textarea" :rows="2" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="重点维度（逗号分隔）">
              <el-input v-model="rubricText.primary_dimensions" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重点观测点（逗号分隔）">
              <el-input v-model="rubricText.primary_items" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="showEditor = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePersona">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const loading = ref(false)
const saving = ref(false)
const personas = ref([])
const showEditor = ref(false)
const editForm = reactive(emptyForm())
const profileText = reactive({
  core_traits: '',
  evidence_preference: '',
  sensitive_risks: ''
})
const rubricText = reactive({
  primary_dimensions: '',
  primary_items: ''
})
const enabledCount = computed(() => personas.value.filter(item => item.enabled !== false).length)
const disabledCount = computed(() => personas.value.filter(item => item.enabled === false).length)
const focusItemCount = computed(() => personas.value.reduce((sum, item) => sum + (item.rubric_focus?.primary_items?.length || 0), 0))

function emptyForm() {
  return {
    code: '',
    name: '',
    short_label: '',
    prompt_modifier: '',
    enabled: true,
    judge_profile: {
      core_traits: [],
      scoring_style: '',
      evidence_preference: [],
      sensitive_risks: [],
      likely_high_score_reason: '',
      likely_low_score_reason: '',
      feedback_style: ''
    },
    rubric_focus: {
      primary_dimensions: [],
      primary_items: [],
      secondary_dimensions: []
    }
  }
}

onMounted(fetchPersonas)

async function fetchPersonas() {
  loading.value = true
  try {
    const res = await request.get('/api/admin/ai-jury/personas')
    personas.value = res.data?.personas || res.personas || []
  } finally {
    loading.value = false
  }
}

function openEditor(row) {
  Object.assign(editForm, emptyForm(), JSON.parse(JSON.stringify(row)))
  profileText.core_traits = (editForm.judge_profile.core_traits || []).join('，')
  profileText.evidence_preference = (editForm.judge_profile.evidence_preference || []).join('，')
  profileText.sensitive_risks = (editForm.judge_profile.sensitive_risks || []).join('，')
  rubricText.primary_dimensions = (editForm.rubric_focus.primary_dimensions || []).join('，')
  rubricText.primary_items = (editForm.rubric_focus.primary_items || []).join('，')
  showEditor.value = true
}

async function savePersona() {
  saving.value = true
  try {
    const payload = JSON.parse(JSON.stringify(editForm))
    payload.judge_profile.core_traits = splitList(profileText.core_traits)
    payload.judge_profile.evidence_preference = splitList(profileText.evidence_preference)
    payload.judge_profile.sensitive_risks = splitList(profileText.sensitive_risks)
    payload.rubric_focus.primary_dimensions = splitList(rubricText.primary_dimensions)
    payload.rubric_focus.primary_items = splitList(rubricText.primary_items)
    await request.put(`/api/admin/ai-jury/personas/${payload.code}`, payload)
    ElMessage.success('评委画像已保存')
    showEditor.value = false
    await fetchPersonas()
  } finally {
    saving.value = false
  }
}

async function resetDefaults() {
  await ElMessageBox.confirm('确定恢复 16 个默认 AI 评委画像？当前自定义内容会被覆盖。', '恢复默认', { type: 'warning' })
  await request.post('/api/admin/ai-jury/personas/reset')
  ElMessage.success('已恢复默认画像')
  await fetchPersonas()
}

function splitList(text) {
  return String(text || '')
    .split(/[，,]/)
    .map(item => item.trim())
    .filter(Boolean)
}
</script>

<style scoped>
.el-tag + .el-tag {
  margin-left: 6px;
  margin-bottom: 4px;
}
</style>
