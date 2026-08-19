<template>
  <div class="resource-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">资源管理</span>
        <h1>统一维护备赛资料和 PPT 资源</h1>
        <p>上传后用户端可下载或引用。管理员先确认格式、大小和命名，再用搜索和类型筛选快速定位资源。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchFiles"><el-icon><Refresh /></el-icon>刷新资源</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ files.length }}</strong><span>资源总数</span><small>当前显示 {{ filteredFiles.length }} 个</small></article>
      <article class="admin-metric-card"><strong>{{ totalSizeText }}</strong><span>资源总大小</span><small>单个文件上限 50MB</small></article>
      <article class="admin-metric-card"><strong>{{ typeCount }}</strong><span>文件类型</span><small>PPT、PDF、Word 等资料</small></article>
      <article class="admin-metric-card"><strong>{{ selectedFiles.length }}</strong><span>已选资源</span><small>可批量删除无效文件</small></article>
    </section>

    <el-card class="admin-panel upload-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">上传资源</span>
            <span class="admin-panel-subtitle">支持 .pptx .ppt .pdf .doc .docx，建议文件名包含赛事、课程或用途。</span>
          </div>
        </div>
      </template>
      <el-upload
        ref="uploadRef"
        :action="uploadUrl"
        :headers="uploadHeaders"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        :file-list="[]"
        accept=".pptx,.ppt,.pdf,.doc,.docx"
        drag
        :limit="10"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">支持 .pptx .ppt .pdf .doc .docx 格式，单个文件不超过 50MB</div>
        </template>
      </el-upload>
    </el-card>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">资源列表</span>
            <span class="admin-panel-subtitle">按文件名、上传人或类型查找，下载确认后再做删除。</span>
          </div>
          <div class="admin-panel-actions">
            <el-button
              type="danger"
              size="small"
              :disabled="selectedFiles.length === 0"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon> 批量删除
            </el-button>
          </div>
        </div>
      </template>
      <div class="admin-filter-bar">
        <el-input v-model.trim="keyword" clearable placeholder="搜索文件名 / 上传人" />
        <el-select v-model="typeFilter" clearable placeholder="文件类型">
          <el-option v-for="item in typeOptions" :key="item" :label="item.toUpperCase()" :value="item" />
        </el-select>
      </div>

      <el-table :data="filteredFiles" v-loading="loading" border stripe @selection-change="selectedFiles = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="name" label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon :size="18" :color="extColor(row.ext)"><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="120" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag effect="plain" round size="small" :type="extTagType(row.ext)">
              {{ (row.ext || '').toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploaderName" label="上传人" width="100" />
        <el-table-column prop="createdAt" label="上传时间" width="170" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="downloadFile(row)">
              <el-icon><Download /></el-icon> 下载
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="filteredFiles.length === 0 && !loading" class="admin-empty">
        <el-icon :size="48" color="#cbd5e1"><FolderOpened /></el-icon>
        <p>{{ files.length === 0 ? '暂无资源文件，请先上传。' : '没有匹配的资源，请调整筛选条件。' }}</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UploadFilled, Refresh, Document, Download, Delete, FolderOpened
} from '@element-plus/icons-vue'
import request from '../api/request'
import { getAdminToken } from '../utils/authStorage'
import { batchDeleteSummary, idsFromRows } from '../utils/batchDelete'

const loading = ref(false)
const files = ref([])
const selectedFiles = ref([])
const uploadRef = ref(null)
const keyword = ref('')
const typeFilter = ref('')

const uploadUrl = '/api/admin/ppt/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${getAdminToken()}`
}))

const filteredFiles = computed(() => {
  const q = keyword.value.toLowerCase()
  return files.value.filter((file) => {
    const ext = file.ext || getExt(file.name || '')
    const matchType = !typeFilter.value || ext === typeFilter.value
    const matchKeyword = !q || `${file.name || ''} ${file.uploaderName || ''}`.toLowerCase().includes(q)
    return matchType && matchKeyword
  })
})

const typeOptions = computed(() => Array.from(new Set(files.value.map((file) => file.ext || getExt(file.name || '')).filter(Boolean))).sort())
const typeCount = computed(() => typeOptions.value.length)
const totalSizeText = computed(() => {
  const bytes = files.value.reduce((sum, file) => sum + parseSize(file.size), 0)
  if (!bytes) return '0 MB'
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
})

function getExt(name) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.substring(i + 1).toLowerCase() : ''
}

function parseSize(size) {
  if (typeof size === 'number') return size
  const text = String(size || '').trim().toLowerCase()
  const value = Number.parseFloat(text)
  if (!Number.isFinite(value)) return 0
  if (text.includes('gb')) return value * 1024 * 1024 * 1024
  if (text.includes('mb')) return value * 1024 * 1024
  if (text.includes('kb')) return value * 1024
  return value
}

function extColor(ext) {
  return { pptx: '#d44a2e', ppt: '#d44a2e', pdf: '#e53e3e', doc: '#2b6cb0', docx: '#2b6cb0' }[ext] || '#909399'
}

function extTagType(ext) {
  return { pdf: 'danger', doc: '', docx: '', pptx: 'warning', ppt: 'warning' }[ext] || 'info'
}

async function fetchFiles() {
  loading.value = true
  try {
    const res = await request.get('/api/admin/ppt')
    files.value = res.data || []
  } catch (e) { console.error(e) }
  loading.value = false
}

function beforeUpload(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['pptx', 'ppt', 'pdf', 'doc', 'docx'].includes(ext)) {
    ElMessage.error('仅支持 .pptx .ppt .pdf .doc .docx 文件')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件不能超过 50MB')
    return false
  }
  return true
}

function handleUploadSuccess(res) {
  if (res.code === 200) {
    ElMessage.success('上传成功')
    fetchFiles()
  } else {
    ElMessage.error(res.message || '上传失败')
  }
}

function handleUploadError() {
  ElMessage.error('上传失败，请重试')
}

function downloadFile(row) {
  const token = getAdminToken()
  const a = document.createElement('a')
  a.href = row.url + '?t=' + token
  a.download = row.name
  a.click()
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除 "${row.name}"？`, '删除确认', { type: 'warning' })
    const res = await request.delete(`/api/admin/ppt/${row.id}`)
    if (res.code === 200) {
      ElMessage.success('已删除')
      fetchFiles()
    }
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

async function handleBatchDelete() {
  const ids = idsFromRows(selectedFiles.value)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个资源文件？`, '批量删除资源', { type: 'warning' })
    const res = await request.post('/api/admin/ppt/batch-delete', { ids })
    const summary = batchDeleteSummary(res, '资源')
    ElMessage[summary.type](summary.message)
    selectedFiles.value = []
    await fetchFiles()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

onMounted(() => { fetchFiles() })
</script>

<style scoped>
.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.admin-empty p { margin-top: 12px; }
</style>
