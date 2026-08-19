<template>
  <div class="banner-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">首页轮播</span>
        <h1>维护用户端首页运营位</h1>
        <p>管理首页顶部轮播图、按钮文案、跳转路径和展示顺序。启用前请确认图片、主按钮和路径都能正常跳转。</p>
      </div>
      <div class="admin-hero-actions">
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建轮播
      </el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ total }}</strong><span>轮播总数</span><small>所有分页合计</small></article>
      <article class="admin-metric-card"><strong>{{ activeBannerCount }}</strong><span>当前展示</span><small>当前页启用项</small></article>
      <article class="admin-metric-card"><strong>{{ inactiveBannerCount }}</strong><span>已停用</span><small>当前页停用项</small></article>
      <article class="admin-metric-card"><strong>{{ selectedBannerIds.length }}</strong><span>已选轮播</span><small>可批量删除</small></article>
    </section>

    <el-card shadow="never" class="banner-card admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">轮播列表</span>
            <span class="admin-panel-subtitle">按排序从小到大展示。停用项保留配置，但用户端不展示。</span>
          </div>
        </div>
      </template>
      <el-alert
        v-if="loadError"
        class="load-error"
        type="error"
        :title="loadError"
        show-icon
        :closable="false"
      />
      <div class="batch-bar">
        <el-checkbox
          :model-value="allVisibleSelected"
          :indeterminate="someVisibleSelected"
          :disabled="banners.length === 0"
          @change="toggleSelectAll"
        >
          全选当前页
        </el-checkbox>
        <el-button
          type="danger"
          size="small"
          :disabled="selectedBannerIds.length === 0"
          @click="batchRemoveBanners"
        >
          批量删除
        </el-button>
      </div>
      <div v-loading="loading" class="banner-list">
        <div
          v-for="item in banners"
          :key="item.id"
          class="banner-row"
          :class="{ disabled: item.status === 'INACTIVE' }"
        >
          <el-checkbox
            class="banner-check"
            :model-value="selectedBannerIds.includes(item.id)"
            @change="toggleBanner(item.id)"
          />
          <div class="banner-cover" :style="item.imageUrl ? { backgroundImage: `url(${item.imageUrl})` } : {}">
            <span v-if="!item.imageUrl">无图片</span>
          </div>
          <div class="banner-info">
            <div class="banner-title">
              <h3>{{ item.title }}</h3>
              <el-tag :type="item.status === 'ACTIVE' ? 'success' : 'info'" effect="dark">
                {{ item.status === 'ACTIVE' ? '展示中' : '已停用' }}
              </el-tag>
            </div>
            <p>{{ item.subtitle || '暂无副标题' }}</p>
            <div class="banner-meta">
              <span>排序 {{ item.sortOrder }}</span>
              <span>主按钮：{{ item.ctaText || '-' }} → {{ item.ctaPath || '-' }}</span>
              <span>次按钮：{{ item.secondaryText || '-' }} → {{ item.secondaryPath || '-' }}</span>
            </div>
          </div>
          <div class="banner-actions">
            <el-button @click="openEdit(item)">编辑</el-button>
            <el-popconfirm title="确定删除这条轮播吗？" @confirm="removeBanner(item)">
              <template #reference>
                <el-button type="danger" plain>删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>

        <el-empty v-if="!loading && banners.length === 0" description="暂无轮播" />
      </div>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="prev, pager, next, sizes, total"
          :total="total"
          :page-sizes="[5, 10, 20, 50]"
          @current-change="fetchBanners"
          @size-change="fetchBanners"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑首页轮播' : '新建首页轮播'"
      width="760px"
      destroy-on-close
    >
      <el-form :model="form" label-width="110px" class="banner-form">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="120" show-word-limit placeholder="例如：项目路演作战台" />
        </el-form-item>
        <el-form-item label="副标题">
          <el-input
            v-model="form.subtitle"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="一句话说明本屏重点"
          />
        </el-form-item>
        <el-form-item label="轮播图片">
          <div class="upload-line">
            <el-input v-model="form.imageUrl" placeholder="/uploads/..." />
            <el-upload
              :http-request="uploadImage"
              :show-file-list="false"
              accept="image/*"
            >
              <el-button :loading="uploading">
                <el-icon><Upload /></el-icon>
                上传
              </el-button>
            </el-upload>
          </div>
          <div v-if="form.imageUrl" class="preview" :style="{ backgroundImage: `url(${form.imageUrl})` }"></div>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="主按钮文案">
              <el-input v-model="form.ctaText" maxlength="40" placeholder="继续推进" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="主按钮路径">
              <el-input v-model="form.ctaPath" placeholder="/project-team" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="次按钮文案">
              <el-input v-model="form.secondaryText" maxlength="40" placeholder="进入会议" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="次按钮路径">
              <el-input v-model="form.secondaryPath" placeholder="/online-meeting" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.sortOrder" :min="0" :max="9999" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-radio-group v-model="form.status">
                <el-radio-button label="ACTIVE">展示</el-radio-button>
                <el-radio-button label="INACTIVE">停用</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBanner">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'
import request from '../api/request'
import { batchDeleteSummary } from '../utils/batchDelete'

const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const loadError = ref('')
const banners = ref([])
const selectedBannerIds = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const emptyForm = {
  title: '',
  subtitle: '',
  imageUrl: '',
  ctaText: '继续推进',
  ctaPath: '/project-team',
  secondaryText: '进入会议',
  secondaryPath: '/online-meeting',
  sortOrder: 0,
  status: 'ACTIVE'
}
const form = reactive({ ...emptyForm })
const visibleBannerIds = computed(() => banners.value.map(item => item.id))
const allVisibleSelected = computed(() => visibleBannerIds.value.length > 0 && visibleBannerIds.value.every(id => selectedBannerIds.value.includes(id)))
const someVisibleSelected = computed(() => !allVisibleSelected.value && visibleBannerIds.value.some(id => selectedBannerIds.value.includes(id)))
const activeBannerCount = computed(() => banners.value.filter(item => item.status === 'ACTIVE').length)
const inactiveBannerCount = computed(() => banners.value.filter(item => item.status === 'INACTIVE').length)

function resetForm() {
  Object.assign(form, emptyForm)
  editingId.value = null
}

async function fetchBanners() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await request.get('/api/home/admin/banners', {
      params: { page: page.value, pageSize: pageSize.value }
    })
    banners.value = res.data?.items || []
    selectedBannerIds.value = selectedBannerIds.value.filter(id => banners.value.some(item => item.id === id))
    total.value = Number(res.data?.total || 0)
  } catch (error) {
    loadError.value = '首页轮播数据加载失败，请检查登录权限或稍后重试。'
    banners.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function toggleBanner(id) {
  if (selectedBannerIds.value.includes(id)) {
    selectedBannerIds.value = selectedBannerIds.value.filter(item => item !== id)
  } else {
    selectedBannerIds.value = [...selectedBannerIds.value, id]
  }
}

function toggleSelectAll(checked) {
  if (checked) {
    selectedBannerIds.value = Array.from(new Set([...selectedBannerIds.value, ...visibleBannerIds.value]))
  } else {
    selectedBannerIds.value = selectedBannerIds.value.filter(id => !visibleBannerIds.value.includes(id))
  }
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(item) {
  resetForm()
  editingId.value = item.id
  Object.assign(form, {
    title: item.title || '',
    subtitle: item.subtitle || '',
    imageUrl: item.imageUrl || '',
    ctaText: item.ctaText || '',
    ctaPath: item.ctaPath || '',
    secondaryText: item.secondaryText || '',
    secondaryPath: item.secondaryPath || '',
    sortOrder: Number(item.sortOrder || 0),
    status: item.status || 'ACTIVE'
  })
  dialogVisible.value = true
}

async function uploadImage(option) {
  uploading.value = true
  try {
    const payload = new FormData()
    payload.append('file', option.file)
    const res = await request.post('/api/upload', payload, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    form.imageUrl = res.data?.url || ''
    ElMessage.success('图片已上传')
  } finally {
    uploading.value = false
  }
}

async function saveBanner() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写轮播标题')
    return
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (editingId.value) {
      await request.put(`/api/home/admin/banners/${editingId.value}`, payload)
    } else {
      await request.post('/api/home/admin/banners', payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    await fetchBanners()
  } finally {
    saving.value = false
  }
}

async function removeBanner(item) {
  await request.delete(`/api/home/admin/banners/${item.id}`)
  ElMessage.success('已删除')
  await fetchBanners()
}

async function batchRemoveBanners() {
  if (selectedBannerIds.value.length === 0) return
  await ElMessageBox.confirm(`确定删除选中的 ${selectedBannerIds.value.length} 条首页轮播？`, '批量删除轮播', { type: 'warning' })
  const res = await request.post('/api/home/admin/banners/batch-delete', { ids: selectedBannerIds.value })
  const summary = batchDeleteSummary(res, '轮播')
  ElMessage[summary.type](summary.message)
  selectedBannerIds.value = []
  await fetchBanners()
}

onMounted(fetchBanners)
</script>

<style scoped>
.banner-page {
  display: grid;
  gap: 18px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-radius: 10px;
  color: #eef5ff;
  background: linear-gradient(135deg, #162536, #0d1720);
}

.page-head p {
  margin: 0 0 8px;
  color: #67e8a3;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 3px;
}

.page-head h2 {
  margin: 0 0 8px;
  font-size: 28px;
}

.page-head span {
  color: rgba(238, 245, 255, .68);
}

.banner-card {
  border-radius: 10px;
}

.load-error {
  margin-bottom: 14px;
}

.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.banner-list {
  display: grid;
  gap: 14px;
  min-height: 180px;
}

.banner-row {
  display: grid;
  grid-template-columns: 28px 220px minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
}

.banner-check {
  justify-self: center;
}

.banner-row.disabled {
  opacity: .62;
}

.banner-cover {
  height: 124px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #909399;
  background: #111827;
  background-size: cover;
  background-position: center;
}

.banner-info {
  min-width: 0;
}

.banner-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.banner-title h3 {
  margin: 0;
  font-size: 18px;
}

.banner-info p {
  margin: 8px 0 12px;
  color: #606266;
  line-height: 1.6;
}

.banner-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: #909399;
  font-size: 12px;
}

.banner-actions {
  display: flex;
  gap: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.upload-line {
  width: 100%;
  display: flex;
  gap: 10px;
}

.preview {
  width: 260px;
  height: 116px;
  margin-top: 12px;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  background-size: cover;
  background-position: center;
}

@media (max-width: 900px) {
  .banner-row {
    grid-template-columns: 1fr;
  }

  .banner-actions,
  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
