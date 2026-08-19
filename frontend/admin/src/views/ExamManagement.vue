<template>
  <div class="exam-admin admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">考试管理</span>
        <h1>维护题库、考试和人工评阅</h1>
        <p>题库负责内容质量，考试负责发布规则，人工评阅负责处理编程题等主观题。每个环节都需要清楚筛选和状态反馈。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchAll">刷新全部</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ questions.length }}</strong><span>题目总数</span><small>启用 {{ enabledQuestionCount }} 道</small></article>
      <article class="admin-metric-card"><strong>{{ papers.length }}</strong><span>考试总数</span><small>已发布 {{ publishedPaperCount }} 场</small></article>
      <article class="admin-metric-card"><strong>{{ reviews.length }}</strong><span>待人工评阅</span><small>需要教师或管理员处理</small></article>
      <article class="admin-metric-card"><strong>{{ selectedQuestions.length + selectedPapers.length }}</strong><span>已选条目</span><small>用于批量删除</small></article>
    </section>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="题库管理" name="questions">
        <el-card class="admin-table-card">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">题库管理</span>
                <span class="admin-panel-subtitle">用题型、难度、状态和关键词快速定位题目，编辑前先确认分类和答案。</span>
              </div>
              <div class="admin-panel-actions">
                <el-button type="danger" :disabled="selectedQuestions.length === 0" @click="batchDeleteQuestions">
                  批量删除
                </el-button>
                <el-button type="primary" @click="openQuestionDialog()">
                  <el-icon><Plus /></el-icon>
                  新建题目
                </el-button>
              </div>
            </div>
          </template>

          <div class="admin-filter-bar">
            <el-input v-model.trim="questionKeyword" clearable placeholder="搜索题干 / 分类" />
            <el-select v-model="questionTypeFilter" clearable placeholder="题型">
              <el-option label="单选题" value="single" />
              <el-option label="多选题" value="multiple" />
              <el-option label="判断题" value="judge" />
              <el-option label="填空题" value="blank" />
              <el-option label="编程题" value="programming" />
            </el-select>
            <el-select v-model="questionDifficultyFilter" clearable placeholder="难度">
              <el-option label="简单" value="easy" />
              <el-option label="普通" value="normal" />
              <el-option label="困难" value="hard" />
            </el-select>
            <el-select v-model="questionStatusFilter" clearable placeholder="状态">
              <el-option label="启用" value="enabled" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </div>

          <el-table :data="filteredQuestions" v-loading="loading" border stripe @selection-change="selectedQuestions = $event">
            <el-table-column type="selection" width="48" />
            <el-table-column prop="stem" label="题干" min-width="300" show-overflow-tooltip />
            <el-table-column label="题型" width="110">
              <template #default="{ row }">{{ typeLabel(row.questionType) }}</template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="130" />
            <el-table-column prop="difficulty" label="难度" width="100" />
            <el-table-column prop="score" label="分值" width="80" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
                  {{ row.status === 'enabled' ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openQuestionDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="deleteQuestion(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="filteredQuestions.length === 0 && !loading" class="admin-empty">没有匹配题目。请调整筛选条件，或新建题目。</div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="考试管理" name="papers">
        <el-card class="admin-table-card">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">考试管理</span>
                <span class="admin-panel-subtitle">配置时长、及格线、随机题序、随机选项和防切屏，发布后用户端可参加。</span>
              </div>
              <div class="admin-panel-actions">
                <el-button type="danger" :disabled="selectedPapers.length === 0" @click="batchDeletePapers">
                  批量删除
                </el-button>
                <el-button type="primary" @click="openPaperDialog()">
                  <el-icon><Plus /></el-icon>
                  新建考试
                </el-button>
              </div>
            </div>
          </template>

          <div class="admin-filter-bar">
            <el-input v-model.trim="paperKeyword" clearable placeholder="搜索考试名称" />
            <el-select v-model="paperStatusFilter" clearable placeholder="状态">
              <el-option label="发布" value="published" />
              <el-option label="草稿" value="draft" />
            </el-select>
          </div>

          <el-table :data="filteredPapers" v-loading="loading" border stripe @selection-change="selectedPapers = $event">
            <el-table-column type="selection" width="48" />
            <el-table-column prop="title" label="考试名称" min-width="240" />
            <el-table-column prop="durationMinutes" label="时长(分钟)" width="110" />
            <el-table-column prop="passScore" label="及格线" width="90" />
            <el-table-column label="防作弊" width="180">
              <template #default="{ row }">
                <el-tag>{{ row.shuffleQuestions ? '题序随机' : '固定题序' }}</el-tag>
                <el-tag class="tag-gap" type="success">{{ row.shuffleOptions ? '选项随机' : '选项固定' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'published' ? 'success' : 'info'">
                  {{ row.status === 'published' ? '发布' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openPaperDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="deletePaper(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="filteredPapers.length === 0 && !loading" class="admin-empty">没有匹配考试。请调整筛选条件，或新建考试。</div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="人工评阅" name="reviews">
        <el-card class="admin-table-card">
          <template #header>
            <div class="admin-panel-head">
              <div>
                <span class="admin-panel-title">人工评阅</span>
                <span class="admin-panel-subtitle">处理含编程题或主观题的待评阅考试记录，保存后刷新待办。</span>
              </div>
              <el-button @click="fetchReviews">刷新</el-button>
            </div>
          </template>

          <el-table :data="reviews" v-loading="loading" border stripe>
            <el-table-column prop="paperTitle" label="考试名称" min-width="220" />
            <el-table-column prop="userId" label="用户ID" width="100" />
            <el-table-column prop="score" label="当前得分" width="100" />
            <el-table-column prop="totalScore" label="总分" width="90" />
            <el-table-column prop="submittedAt" label="提交时间" width="180" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag type="warning">{{ row.status === 'pending_review' ? '待评阅' : row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openReview(row)">评阅</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="reviews.length === 0 && !loading" class="admin-empty">暂无待人工评阅记录。</div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="questionDialogVisible" :title="questionForm.id ? '编辑题目' : '新建题目'" width="760px">
      <el-form :model="questionForm" label-width="92px">
        <el-form-item label="题型">
          <el-select v-model="questionForm.questionType" style="width: 100%">
            <el-option label="单选题" value="single" />
            <el-option label="多选题" value="multiple" />
            <el-option label="判断题" value="judge" />
            <el-option label="填空题" value="blank" />
            <el-option label="编程题" value="programming" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干"><el-input v-model="questionForm.stem" type="textarea" :rows="4" /></el-form-item>
        <el-form-item v-if="isChoiceType(questionForm.questionType)" label="选项">
          <el-input v-model="questionForm.optionsText" type="textarea" :rows="5" placeholder="每行一个选项，例如：A. 检索增强生成" />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="questionForm.answerText" type="textarea" :rows="3" placeholder="多选用逗号分隔；填空/编程填写参考答案" />
        </el-form-item>
        <el-form-item label="解析"><el-input v-model="questionForm.analysis" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="questionForm.category" /></el-form-item>
        <el-form-item label="难度">
          <el-select v-model="questionForm.difficulty" style="width: 100%">
            <el-option label="简单" value="easy" />
            <el-option label="普通" value="normal" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="分值"><el-input-number v-model="questionForm.score" :min="1" /></el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="questionForm.status">
            <el-radio-button label="enabled">启用</el-radio-button>
            <el-radio-button label="disabled">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="paperDialogVisible" :title="paperForm.id ? '编辑考试' : '新建考试'" width="780px">
      <el-form :model="paperForm" label-width="100px">
        <el-form-item label="考试名称"><el-input v-model="paperForm.title" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="paperForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="时长"><el-input-number v-model="paperForm.durationMinutes" :min="1" /> 分钟</el-form-item>
        <el-form-item label="及格线"><el-input-number v-model="paperForm.passScore" :min="0" /></el-form-item>
        <el-form-item label="考试题目">
          <el-select v-model="paperForm.questionIds" multiple filterable style="width: 100%" placeholder="选择题目">
            <el-option
              v-for="item in questions"
              :key="item.id"
              :label="`${typeLabel(item.questionType)} | ${item.stem}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="防作弊">
          <el-checkbox v-model="paperForm.shuffleQuestions">随机题序</el-checkbox>
          <el-checkbox v-model="paperForm.shuffleOptions">随机选项</el-checkbox>
          <el-checkbox v-model="paperForm.antiCheatEnabled">记录切屏</el-checkbox>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="paperForm.status">
            <el-radio-button label="draft">草稿</el-radio-button>
            <el-radio-button label="published">发布</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="paperDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePaper">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="reviewDrawerVisible" title="人工评阅" size="680px">
      <template v-if="reviewDetail">
        <div class="review-summary">
          <strong>{{ reviewDetail.paperTitle }}</strong>
          <span>用户ID：{{ reviewDetail.userId }}</span>
        </div>
        <div class="review-list">
          <article v-for="item in reviewDetail.answers" :key="item.answerId" class="review-item">
            <h3>{{ item.stem }}</h3>
            <p class="label">学生答案</p>
            <pre>{{ answersToText(item.studentAnswerJson) }}</pre>
            <p class="label">参考答案</p>
            <pre>{{ answersToText(item.referenceAnswerJson) }}</pre>
            <el-form-item label="得分">
              <el-input-number v-model="item.score" :min="0" :max="item.maxScore || 0" />
              <span class="max-score">/ {{ item.maxScore || 0 }}</span>
            </el-form-item>
          </article>
        </div>
        <div class="drawer-actions">
          <el-button @click="reviewDrawerVisible = false">取消</el-button>
          <el-button type="primary" @click="saveReview">保存评分</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '../api/request'
import { batchDeleteSummary, idsFromRows } from '../utils/batchDelete'

const activeTab = ref('questions')
const loading = ref(false)
const questions = ref([])
const papers = ref([])
const reviews = ref([])
const selectedQuestions = ref([])
const selectedPapers = ref([])
const questionDialogVisible = ref(false)
const paperDialogVisible = ref(false)
const reviewDrawerVisible = ref(false)
const reviewDetail = ref(null)
const questionForm = ref(defaultQuestionForm())
const paperForm = ref(defaultPaperForm())
const questionKeyword = ref('')
const questionTypeFilter = ref('')
const questionDifficultyFilter = ref('')
const questionStatusFilter = ref('')
const paperKeyword = ref('')
const paperStatusFilter = ref('')

const filteredQuestions = computed(() => {
  const q = questionKeyword.value.toLowerCase()
  return questions.value.filter((question) => {
    const matchKeyword = !q || `${question.stem || ''} ${question.category || ''}`.toLowerCase().includes(q)
    const matchType = !questionTypeFilter.value || question.questionType === questionTypeFilter.value
    const matchDifficulty = !questionDifficultyFilter.value || question.difficulty === questionDifficultyFilter.value
    const matchStatus = !questionStatusFilter.value || question.status === questionStatusFilter.value
    return matchKeyword && matchType && matchDifficulty && matchStatus
  })
})

const filteredPapers = computed(() => {
  const q = paperKeyword.value.toLowerCase()
  return papers.value.filter((paper) => {
    const matchKeyword = !q || `${paper.title || ''} ${paper.description || ''}`.toLowerCase().includes(q)
    const matchStatus = !paperStatusFilter.value || paper.status === paperStatusFilter.value
    return matchKeyword && matchStatus
  })
})

const enabledQuestionCount = computed(() => questions.value.filter((question) => question.status === 'enabled').length)
const publishedPaperCount = computed(() => papers.value.filter((paper) => paper.status === 'published').length)

onMounted(fetchAll)

async function fetchAll() {
  loading.value = true
  try {
    const [questionRes, paperRes] = await Promise.all([
      request.get('/api/admin/exams/questions'),
      request.get('/api/admin/exams/papers')
    ])
    questions.value = questionRes.data || []
    papers.value = paperRes.data || []
    await fetchReviews(false)
  } finally {
    loading.value = false
  }
}

async function fetchReviews(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const res = await request.get('/api/admin/exams/reviews/pending')
    reviews.value = res.data || []
  } finally {
    if (showLoading) loading.value = false
  }
}

function defaultQuestionForm() {
  return {
    questionType: 'single',
    stem: '',
    optionsText: 'A. \nB. \nC. \nD. ',
    answerText: '',
    analysis: '',
    category: '通用',
    difficulty: 'normal',
    score: 5,
    status: 'enabled'
  }
}

function defaultPaperForm() {
  return {
    title: '',
    description: '',
    durationMinutes: 45,
    passScore: 60,
    status: 'draft',
    shuffleQuestions: true,
    shuffleOptions: true,
    antiCheatEnabled: true,
    questionIds: []
  }
}

function openQuestionDialog(row) {
  questionForm.value = row ? fromQuestion(row) : defaultQuestionForm()
  questionDialogVisible.value = true
}

async function openPaperDialog(row) {
  if (!row) {
    paperForm.value = defaultPaperForm()
    paperDialogVisible.value = true
    return
  }
  paperDialogVisible.value = true
  const res = await request.get(`/api/admin/exams/papers/${row.id}`)
  const detail = res.data || row
  paperForm.value = {
    ...defaultPaperForm(),
    ...detail,
    questionIds: (detail.questions || []).map((item) => item.questionId)
  }
}

async function saveQuestion() {
  if (!questionForm.value.stem?.trim()) return ElMessage.error('请填写题干')
  const payload = toQuestionPayload(questionForm.value)
  if (questionForm.value.id) await request.put(`/api/admin/exams/questions/${questionForm.value.id}`, payload)
  else await request.post('/api/admin/exams/questions', payload)
  ElMessage.success('题目已保存')
  questionDialogVisible.value = false
  await fetchAll()
}

async function savePaper() {
  if (!paperForm.value.title?.trim()) return ElMessage.error('请填写考试名称')
  const payload = {
    ...paperForm.value,
    questions: paperForm.value.questionIds.map((id, index) => ({
      questionId: id,
      score: questions.value.find((item) => item.id === id)?.score || 5,
      sortOrder: (index + 1) * 10
    }))
  }
  if (paperForm.value.id) await request.put(`/api/admin/exams/papers/${paperForm.value.id}`, payload)
  else await request.post('/api/admin/exams/papers', payload)
  ElMessage.success('考试已保存')
  paperDialogVisible.value = false
  await fetchAll()
}

async function deleteQuestion(row) {
  await ElMessageBox.confirm(`确定删除该题目？`, '删除题目', { type: 'warning' })
  await request.delete(`/api/admin/exams/questions/${row.id}`)
  ElMessage.success('题目已删除')
  await fetchAll()
}

async function batchDeleteQuestions() {
  const ids = idsFromRows(selectedQuestions.value)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 道题目？`, '批量删除题目', { type: 'warning' })
    const res = await request.post('/api/admin/exams/questions/batch-delete', { ids })
    const summary = batchDeleteSummary(res, '题目')
    ElMessage[summary.type](summary.message)
    selectedQuestions.value = []
    await fetchAll()
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

async function deletePaper(row) {
  await ElMessageBox.confirm(`确定删除考试「${row.title}」？`, '删除考试', { type: 'warning' })
  await request.delete(`/api/admin/exams/papers/${row.id}`)
  ElMessage.success('考试已删除')
  await fetchAll()
}

async function batchDeletePapers() {
  const ids = idsFromRows(selectedPapers.value)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 场考试？`, '批量删除考试', { type: 'warning' })
    const res = await request.post('/api/admin/exams/papers/batch-delete', { ids })
    const summary = batchDeleteSummary(res, '考试')
    ElMessage[summary.type](summary.message)
    selectedPapers.value = []
    await fetchAll()
  } catch (e) { if (e !== 'cancel') console.error(e) }
}

async function openReview(row) {
  const res = await request.get(`/api/admin/exams/reviews/${row.attemptId}`)
  reviewDetail.value = res.data
  reviewDrawerVisible.value = true
}

async function saveReview() {
  if (!reviewDetail.value) return
  await request.post(`/api/admin/exams/reviews/${reviewDetail.value.attemptId}/grade`, {
    answers: (reviewDetail.value.answers || []).map((item) => ({
      answerId: item.answerId,
      score: item.score || 0
    }))
  })
  ElMessage.success('评分已保存')
  reviewDrawerVisible.value = false
  await fetchReviews(false)
}

function toQuestionPayload(form) {
  return {
    questionType: form.questionType,
    stem: form.stem,
    optionsJson: JSON.stringify(parseOptions(form.questionType, form.optionsText)),
    answerJson: JSON.stringify(parseAnswers(form.answerText)),
    analysis: form.analysis,
    category: form.category,
    difficulty: form.difficulty,
    score: form.score,
    status: form.status
  }
}

function fromQuestion(row) {
  return {
    ...defaultQuestionForm(),
    ...row,
    optionsText: optionsToText(row.optionsJson),
    answerText: answersToText(row.answerJson)
  }
}

function parseOptions(type, text) {
  if (!isChoiceType(type) && type !== 'judge') return []
  if (type === 'judge') return [{ key: 'true', text: '正确' }, { key: 'false', text: '错误' }]
  return (text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const match = line.match(/^([A-Z])[\.\、\s]+(.+)$/i)
      return { key: (match?.[1] || String.fromCharCode(65 + index)).toUpperCase(), text: match?.[2] || line }
    })
}

function parseAnswers(text) {
  return (text || '').split(/[,，\n]/).map((item) => item.trim()).filter(Boolean)
}

function optionsToText(json) {
  try {
    return JSON.parse(json || '[]').map((item) => `${item.key}. ${item.text}`).join('\n')
  } catch {
    return ''
  }
}

function answersToText(json) {
  try {
    return JSON.parse(json || '[]').join(',')
  } catch {
    return ''
  }
}

function isChoiceType(type) {
  return type === 'single' || type === 'multiple'
}

function typeLabel(type) {
  return {
    single: '单选题',
    multiple: '多选题',
    judge: '判断题',
    blank: '填空题',
    programming: '编程题'
  }[type] || type
}
</script>

<style scoped>
.tag-gap {
  margin-left: 6px;
}

.review-summary {
  display: grid;
  gap: 6px;
  margin-bottom: 18px;
  padding: 14px 16px;
  border: 1px solid var(--admin-border-soft);
  border-radius: var(--admin-radius-md);
  background: var(--admin-surface-muted);
}

.review-summary strong {
  color: var(--admin-text-strong);
  font-size: 18px;
}

.review-summary span,
.label {
  color: var(--admin-muted);
  font-size: 13px;
}

.review-list {
  display: grid;
  gap: 16px;
}

.review-item {
  padding: 16px;
  border: 1px solid var(--admin-border-soft);
  border-radius: var(--admin-radius-md);
}

.review-item h3 {
  margin: 0 0 14px;
  color: var(--admin-text-strong);
  font-size: 16px;
  line-height: 1.5;
}

.review-item pre {
  max-height: 220px;
  overflow: auto;
  margin: 8px 0 14px;
  padding: 12px;
  border-radius: 8px;
  color: var(--admin-text-strong);
  background: var(--admin-surface-muted);
  white-space: pre-wrap;
  word-break: break-word;
}

.max-score {
  margin-left: 8px;
  color: var(--admin-muted);
}

.drawer-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 14px;
  background: var(--admin-surface);
}
</style>
