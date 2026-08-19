<template>
  <div class="file-admin-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">文件中心管理</span>
        <h1>管理用户端文件中心资料</h1>
        <p>管理员统一查看、下载和删除文件中心资源。删除会同时移除资源记录和上传文件。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button plain @click="fetchFiles"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="danger" :disabled="selectedRows.length === 0" @click="handleBatchDelete">
          <el-icon><Delete /></el-icon>批量删除
        </el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ files.length }}</strong><span>文件总数</span><small>当前显示 {{ filteredFiles.length }} 个</small></article>
      <article class="admin-metric-card"><strong>{{ totalSizeText }}</strong><span>占用空间</span><small>按资源记录统计</small></article>
      <article class="admin-metric-card"><strong>{{ categoryOptions.length }}</strong><span>文件夹</span><small>含系统分类和自定义分类</small></article>
      <article class="admin-metric-card"><strong>{{ selectedRows.length }}</strong><span>已选文件</span><small>仅管理员可删除</small></article>
    </section>

    <section class="file-admin-window">
      <aside class="file-admin-sidebar">
        <div class="side-section">
          <span>常用位置</span>
          <button type="button" :class="{ active: activeCategory === 'all' }" @click="activeCategory = 'all'">
            <el-icon><Files /></el-icon><b>全部文件</b><em>{{ files.length }}</em>
          </button>
          <button type="button" :class="{ active: activeCategory === 'custom' }" @click="activeCategory = 'custom'">
            <el-icon><FolderOpened /></el-icon><b>自定义文件夹</b><em>{{ customCount }}</em>
          </button>
        </div>
        <div class="side-section">
          <span>文件夹</span>
          <button
            v-for="item in categoryOptions"
            :key="item.key"
            type="button"
            :class="{ active: activeCategory === item.key }"
            @click="activeCategory = item.key"
          >
            <el-icon><Folder /></el-icon><b>{{ item.label }}</b><em>{{ item.count }}</em>
          </button>
        </div>
      </aside>

      <main class="file-admin-main">
        <div class="file-admin-toolbar">
          <div>
            <strong>{{ activeTitle }}</strong>
            <small>{{ filteredFiles.length }} 个文件</small>
          </div>
          <div class="file-admin-filters">
            <el-input v-model.trim="keyword" clearable placeholder="搜索文件名 / 上传人 / 类型" />
            <el-select v-model="typeFilter" clearable placeholder="文件类型">
              <el-option v-for="item in typeOptions" :key="item" :label="item.toUpperCase()" :value="item" />
            </el-select>
          </div>
        </div>

        <el-table
          :data="filteredFiles"
          v-loading="loading"
          height="100%"
          border
          stripe
          @selection-change="selectedRows = $event"
          @row-click="selectedFile = $event"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="name" label="文件名" min-width="240">
            <template #default="{ row }">
              <div class="file-name-cell">
                <el-icon :size="18" :color="extColor(row.ext)"><Document /></el-icon>
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="文件夹" width="150">
            <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
          </el-table-column>
          <el-table-column prop="size" label="大小" width="110" />
          <el-table-column label="类型" width="92">
            <template #default="{ row }">
              <el-tag effect="plain" round size="small" :type="extTagType(row.ext)">{{ (row.ext || '').toUpperCase() }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="uploaderName" label="上传人" width="110" />
          <el-table-column prop="createdAt" label="上传时间" width="170" />
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click.stop="downloadFile(row)"><el-icon><Download /></el-icon>下载</el-button>
              <el-button size="small" type="danger" link @click.stop="handleDelete(row)"><el-icon><Delete /></el-icon>删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="filteredFiles.length === 0 && !loading" class="admin-empty">
          <el-icon :size="48" color="#cbd5e1"><FolderOpened /></el-icon>
          <p>{{ files.length === 0 ? '暂无文件中心资源。' : '没有匹配的文件，请调整筛选条件。' }}</p>
        </div>
      </main>

      <aside class="file-admin-inspector">
        <template v-if="selectedFile">
          <div class="inspector-icon">{{ (selectedFile.ext || getExt(selectedFile.name) || 'file').slice(0, 3).toUpperCase() }}</div>
          <h2>{{ selectedFile.name }}</h2>
          <p>{{ categoryLabel(selectedFile.category) }} · {{ selectedFile.size || '-' }}</p>
          <div class="inspector-actions">
            <el-button plain @click="downloadFile(selectedFile)"><el-icon><Download /></el-icon>下载</el-button>
            <el-button type="danger" plain @click="handleDelete(selectedFile)"><el-icon><Delete /></el-icon>删除</el-button>
          </div>
          <dl>
            <dt>文件 ID</dt><dd>{{ selectedFile.id }}</dd>
            <dt>文件类型</dt><dd>{{ selectedFile.ext || getExt(selectedFile.name) || '-' }}</dd>
            <dt>上传人</dt><dd>{{ selectedFile.uploaderName || selectedFile.uploadedBy || '-' }}</dd>
            <dt>上传时间</dt><dd>{{ selectedFile.createdAt || '-' }}</dd>
            <dt>存储路径</dt><dd>{{ selectedFile.filePath || '-' }}</dd>
          </dl>
        </template>
        <div v-else class="inspector-empty">选择一个文件后查看详细信息。</div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Document, Download, Files, Folder, FolderOpened, Refresh } from '@element-plus/icons-vue'
import request from '../api/request'
import { getAdminToken } from '../utils/authStorage'
import { batchDeleteSummary, idsFromRows } from '../utils/batchDelete'

const systemCategories = [
  { key: 'competition', label: '赛项文件' },
  { key: 'team', label: '团队项目材料' },
  { key: 'research', label: '调研资料' },
  { key: 'proof', label: '成果证明' },
  { key: 'content', label: 'PPT/讲稿素材' },
  { key: 'public', label: '公共资源' }
]

const loading = ref(false)
const files = ref([])
const categories = ref([])
const selectedRows = ref([])
const selectedFile = ref(null)
const keyword = ref('')
const typeFilter = ref('')
const activeCategory = ref('all')

const customCategoryKeys = computed(() => new Set(categories.value.map(item => item.key)))
const customCount = computed(() => files.value.filter(file => customCategoryKeys.value.has(file.category)).length)

const categoryOptions = computed(() => {
  const all = [...systemCategories, ...categories.value]
  return all.map(item => ({
    ...item,
    count: files.value.filter(file => (file.category || 'public') === item.key).length
  }))
})

const activeTitle = computed(() => {
  if (activeCategory.value === 'all') return '全部文件'
  if (activeCategory.value === 'custom') return '自定义文件夹'
  return categoryLabel(activeCategory.value)
})

const typeOptions = computed(() => Array.from(new Set(files.value.map(file => file.ext || getExt(file.name || '')).filter(Boolean))).sort())

const filteredFiles = computed(() => {
  const q = keyword.value.toLowerCase()
  return files.value.filter((file) => {
    const ext = file.ext || getExt(file.name || '')
    const category = file.category || 'public'
    const matchCategory = activeCategory.value === 'all'
      || category === activeCategory.value
      || (activeCategory.value === 'custom' && customCategoryKeys.value.has(category))
    const matchType = !typeFilter.value || ext === typeFilter.value
    const matchKeyword = !q || `${file.name || ''} ${file.uploaderName || ''} ${ext} ${categoryLabel(category)}`.toLowerCase().includes(q)
    return matchCategory && matchType && matchKeyword
  })
})

const totalSizeText = computed(() => {
  const bytes = files.value.reduce((sum, file) => sum + parseSize(file.size || file.fileSize), 0)
  if (!bytes) return '0 MB'
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
})

function getExt(name = '') {
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

function categoryLabel(key = 'public') {
  return [...systemCategories, ...categories.value].find(item => item.key === key)?.label || key || '公共资源'
}

function extColor(ext) {
  return { pptx: '#d44a2e', ppt: '#d44a2e', pdf: '#e53e3e', doc: '#2b6cb0', docx: '#2b6cb0', xls: '#22863a', xlsx: '#22863a' }[ext] || '#909399'
}

function extTagType(ext) {
  return { pdf: 'danger', doc: '', docx: '', pptx: 'warning', ppt: 'warning', xls: 'success', xlsx: 'success' }[ext] || 'info'
}

async function fetchFiles() {
  loading.value = true
  try {
    const [fileRes, categoryRes] = await Promise.all([
      request.get('/api/admin/ppt'),
      request.get('/api/ppt-template/categories')
    ])
    files.value = fileRes.data || []
    categories.value = categoryRes.data || []
    if (selectedFile.value && !files.value.some(item => item.id === selectedFile.value.id)) selectedFile.value = null
  } finally {
    loading.value = false
  }
}

function downloadFile(row) {
  const token = getAdminToken()
  const a = document.createElement('a')
  a.href = `${row.url || `/api/ppt-template/download/${encodeURIComponent(row.name)}`}${row.url?.includes('?') ? '&' : '?'}t=${token}`
  a.download = row.name
  a.click()
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」？删除后用户端文件中心也不可再下载。`, '删除文件', { type: 'warning' })
    const res = await request.delete(`/api/admin/ppt/${row.id}`)
    if (res.code === 200) {
      ElMessage.success('文件已删除')
      if (selectedFile.value?.id === row.id) selectedFile.value = null
      await fetchFiles()
    }
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

async function handleBatchDelete() {
  const ids = idsFromRows(selectedRows.value)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个文件？删除后用户端文件中心也不可再下载。`, '批量删除文件', { type: 'warning' })
    const res = await request.post('/api/admin/ppt/batch-delete', { ids })
    const summary = batchDeleteSummary(res, '文件')
    ElMessage[summary.type](summary.message)
    selectedRows.value = []
    selectedFile.value = null
    await fetchFiles()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

onMounted(fetchFiles)
</script>

<style scoped>
.file-admin-window {
  min-height: 620px;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 300px;
  overflow: hidden;
  border: 1px solid var(--admin-border);
  border-radius: 24px;
  background: var(--admin-surface);
  box-shadow: var(--admin-shadow-soft);
}

.file-admin-sidebar,
.file-admin-inspector {
  min-height: 0;
  overflow: auto;
  background: #fff7ef;
}

.file-admin-sidebar {
  padding: 14px 10px;
  border-right: 1px solid var(--admin-border);
}

.side-section {
  display: grid;
  gap: 6px;
  margin-bottom: 18px;
}

.side-section > span {
  padding: 0 10px 4px;
  color: var(--admin-muted);
  font-size: 12px;
  font-weight: 800;
}

.side-section button {
  min-height: 36px;
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--admin-text);
  cursor: pointer;
}

.side-section button.active,
.side-section button:hover {
  background: rgba(243, 107, 23, 0.12);
  color: var(--admin-primary);
}

.side-section b {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.side-section em {
  padding: 1px 7px;
  border-radius: 999px;
  background: #fff;
  color: var(--admin-muted);
  font-style: normal;
  font-size: 12px;
}

.file-admin-main {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  position: relative;
}

.file-admin-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid var(--admin-border);
}

.file-admin-toolbar strong,
.file-admin-toolbar small {
  display: block;
}

.file-admin-toolbar small {
  margin-top: 4px;
  color: var(--admin-muted);
}

.file-admin-filters {
  display: grid;
  grid-template-columns: 260px 150px;
  gap: 10px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-name-cell span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-admin-inspector {
  padding: 20px;
  border-left: 1px solid var(--admin-border);
}

.inspector-icon {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  display: grid;
  place-items: center;
  background: #fff0e4;
  color: var(--admin-primary);
  font-weight: 900;
}

.file-admin-inspector h2 {
  margin: 16px 0 6px;
  font-size: 18px;
  line-height: 1.35;
  word-break: break-word;
}

.file-admin-inspector p {
  margin: 0;
  color: var(--admin-muted);
}

.inspector-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 18px 0;
}

.file-admin-inspector dl {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-top: 16px;
  border-top: 1px solid var(--admin-border);
}

.file-admin-inspector dt {
  color: var(--admin-muted);
  font-size: 12px;
}

.file-admin-inspector dd {
  margin: -6px 0 4px;
  color: var(--admin-text-strong);
  word-break: break-all;
}

.inspector-empty {
  min-height: 240px;
  display: grid;
  place-items: center;
  color: var(--admin-muted);
  text-align: center;
}

@media (max-width: 1280px) {
  .file-admin-window {
    grid-template-columns: 200px minmax(0, 1fr);
  }
  .file-admin-inspector {
    display: none;
  }
}
</style>
