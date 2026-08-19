<template>
  <div class="organization-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">组织分组</span>
        <h1>维护学校、学院、班级和用户组</h1>
        <p>组织归属影响用户筛选、课程/考试分配和后续权限管理。先建学校，再建学院和班级，用户组用于跨组织的备赛分组。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button type="primary" @click="openUnitDialog"><el-icon><Plus /></el-icon>新增学校</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ schoolCount }}</strong><span>学校</span><small>一级组织</small></article>
      <article class="admin-metric-card"><strong>{{ collegeCount }}</strong><span>学院</span><small>归属于学校</small></article>
      <article class="admin-metric-card"><strong>{{ classCount }}</strong><span>班级</span><small>学生主要归属</small></article>
    </section>

    <el-card class="admin-table-card org-query-card">
      <el-form :model="query" inline label-width="76px" class="org-query-form">
        <el-form-item label="组织名称">
          <el-input v-model.trim="query.name" clearable placeholder="请输入学校、学院或班级名称" @keyup.enter="applyQuery" />
        </el-form-item>
        <el-form-item label="组织类型">
          <el-select v-model="query.type" clearable placeholder="全部类型">
            <el-option label="学校" value="SCHOOL" />
            <el-option label="学院" value="COLLEGE" />
            <el-option label="班级" value="CLASS" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyQuery">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">组织架构</span>
            <span class="admin-panel-subtitle">若依式树表：学校为一级，学院为二级，班级为末级。筛选时保留匹配节点的上级路径。</span>
          </div>
          <div class="admin-panel-actions">
            <el-button size="small" @click="toggleExpandAll">{{ expandAll ? '折叠全部' : '展开全部' }}</el-button>
            <el-button size="small" @click="fetchOptions">刷新</el-button>
            <el-button size="small" type="primary" @click="openUnitDialog"><el-icon><Plus /></el-icon>新增学校</el-button>
          </div>
        </div>
      </template>
          <el-table
            :key="tableKey"
            :data="filteredUnitTree"
            v-loading="loading"
            border
            stripe
            row-key="treeId"
            :default-expand-all="expandAll"
            :tree-props="{ children: 'children' }"
          >
            <el-table-column prop="name" label="组织名称" min-width="260">
              <template #default="{ row }">
                <div class="unit-name-cell">
                  <div class="unit-name-inner" :style="{ paddingLeft: `${(row.level || 0) * 28}px` }">
                    <strong>{{ row.name }}</strong>
                    <small>{{ unitPath(row) }}</small>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <el-tag :type="unitTag(row.type)" effect="light">{{ unitTypeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="上级组织" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.parentName || '无' }}
              </template>
            </el-table-column>
            <el-table-column label="下级数量" width="110">
              <template #default="{ row }">
                {{ relationText(row) }}
              </template>
            </el-table-column>
            <el-table-column prop="code" label="编码" width="130">
              <template #default="{ row }">{{ row.code || '-' }}</template>
            </el-table-column>
            <el-table-column prop="createdAt" label="创建时间" width="170" />
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.type === 'SCHOOL'"
                  type="primary"
                  link
                  @click="openChildUnitDialog(row, 'COLLEGE')"
                >
                  新增学院
                </el-button>
                <el-button
                  v-else-if="row.type === 'COLLEGE'"
                  type="primary"
                  link
                  @click="openChildUnitDialog(row, 'CLASS')"
                >
                  新增班级
                </el-button>
                <el-button type="primary" link @click="openUnitDialog(row)">修改</el-button>
                <el-button type="danger" link @click="deleteUnit(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="filteredUnitTree.length === 0 && !loading" class="admin-empty">暂无匹配组织，请调整查询条件。</div>
    </el-card>

    <el-dialog v-model="showUnitDialog" :title="unitDialogTitle" width="560px" @closed="resetUnitForm">
      <el-form ref="unitFormRef" :model="unitForm" :rules="unitRules" label-width="82px">
        <el-form-item label="类型" prop="type">
          <el-select v-model="unitForm.type" :disabled="unitTypeLocked" style="width: 100%" @change="onUnitTypeChange">
            <el-option label="学校" value="SCHOOL" />
            <el-option label="学院" value="COLLEGE" />
            <el-option label="班级" value="CLASS" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="unitForm.type !== 'SCHOOL'" label="上级" prop="parentId">
          <el-select v-model="unitForm.parentId" :disabled="unitTypeLocked" filterable style="width: 100%">
            <el-option
              v-for="item in parentOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model.trim="unitForm.name" placeholder="例如：信息工程学院 / 23软件1班" />
        </el-form-item>
        <el-form-item label="编码">
          <el-input v-model.trim="unitForm.code" placeholder="可选，例如 SE-2023-01" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="showUnitDialog = false">取消</el-button>
        <el-button type="primary" round :loading="savingUnit" @click="createUnit">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '../api/request'

const loading = ref(false)
const savingUnit = ref(false)
const units = ref([])
const showUnitDialog = ref(false)
const unitFormRef = ref(null)
const unitTypeLocked = ref(false)
const expandAll = ref(true)
const tableKey = ref(0)

const query = reactive({
  name: '',
  type: ''
})

const unitForm = reactive({
  id: null,
  type: 'SCHOOL',
  parentId: '',
  name: '',
  code: ''
})

const unitRules = {
  type: [{ required: true, message: '请选择组织类型', trigger: 'change' }],
  parentId: [{ required: true, message: '请选择上级组织', trigger: 'change' }],
  name: [{ required: true, message: '请输入组织名称', trigger: 'blur' }]
}

const unitDialogTitle = computed(() => {
  if (unitForm.id) return '修改组织'
  if (unitForm.type === 'COLLEGE') return '新增学院'
  if (unitForm.type === 'CLASS') return '新增班级'
  return '新增学校'
})

const unitRows = computed(() => {
  const byId = new Map(units.value.map(item => [Number(item.id), item]))
  return units.value.map(item => ({
    ...item,
    treeId: `${item.type}-${item.id}`,
    parentName: item.parentId ? byId.get(Number(item.parentId))?.name || '未找到上级' : '无'
  }))
})

const unitTree = computed(() => {
  const rows = unitRows.value.map(item => ({ ...item, children: [] }))
  const byId = new Map(rows.map(item => [Number(item.id), item]))
  const roots = []

  rows.forEach((item) => {
    const parent = item.parentId ? byId.get(Number(item.parentId)) : null
    if (parent) {
      parent.children.push(item)
    } else {
      roots.push(item)
    }
  })

  const order = { SCHOOL: 1, COLLEGE: 2, CLASS: 3 }
  const sortTree = (items) => {
    items.sort((a, b) => (order[a.type] || 9) - (order[b.type] || 9) || String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN'))
    items.forEach(item => sortTree(item.children))
  }
  const assignLevel = (items, level = 0) => {
    items.forEach((item) => {
      item.level = level
      assignLevel(item.children, level + 1)
    })
  }
  sortTree(roots)
  assignLevel(roots)
  return roots
})

const filteredUnitTree = computed(() => {
  const name = query.name.toLowerCase()
  const type = query.type
  if (!name && !type) return unitTree.value

  function filterNodes(nodes) {
    return nodes
      .map((node) => {
        const children = filterNodes(node.children || [])
        const matchName = !name || String(node.name || '').toLowerCase().includes(name)
        const matchType = !type || node.type === type
        const selfMatched = matchName && matchType
        if (selfMatched || children.length > 0) {
          return { ...node, children }
        }
        return null
      })
      .filter(Boolean)
  }

  return filterNodes(unitTree.value)
})

const parentOptions = computed(() => {
  if (unitForm.type === 'COLLEGE') return units.value.filter(item => item.type === 'SCHOOL')
  if (unitForm.type === 'CLASS') return units.value.filter(item => item.type === 'COLLEGE')
  return []
})
const schoolCount = computed(() => units.value.filter(item => item.type === 'SCHOOL').length)
const collegeCount = computed(() => units.value.filter(item => item.type === 'COLLEGE').length)
const classCount = computed(() => units.value.filter(item => item.type === 'CLASS').length)

function ensureSuccess(res) {
  if (res?.code && res.code !== 200) throw new Error(res.message || '操作失败')
  return res
}

async function fetchOptions() {
  loading.value = true
  try {
    const res = ensureSuccess(await request.get('/api/user/organization/options'))
    units.value = res.data?.units || []
  } finally {
    loading.value = false
  }
}

function openUnitDialog(row) {
  resetUnitForm()
  if (row) {
    Object.assign(unitForm, {
      id: row.id,
      type: row.type,
      parentId: row.parentId || '',
      name: row.name || '',
      code: row.code || ''
    })
  }
  showUnitDialog.value = true
}

function openChildUnitDialog(parent, childType) {
  resetUnitForm()
  unitTypeLocked.value = true
  Object.assign(unitForm, {
    type: childType,
    parentId: parent.id,
    name: '',
    code: ''
  })
  showUnitDialog.value = true
}

function resetUnitForm() {
  unitTypeLocked.value = false
  Object.assign(unitForm, { id: null, type: 'SCHOOL', parentId: '', name: '', code: '' })
  unitFormRef.value?.clearValidate()
}

function onUnitTypeChange() {
  unitForm.parentId = ''
}

function applyQuery() {
  expandAll.value = true
  tableKey.value += 1
}

function resetQuery() {
  query.name = ''
  query.type = ''
  applyQuery()
}

function toggleExpandAll() {
  expandAll.value = !expandAll.value
  tableKey.value += 1
}

async function createUnit() {
  const valid = await unitFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingUnit.value = true
  try {
    const payload = {
      ...unitForm,
      parentId: unitForm.parentId || null
    }
    if (unitForm.id) {
      ensureSuccess(await request.put(`/api/user/organization/units/${unitForm.id}`, payload))
    } else {
      ensureSuccess(await request.post('/api/user/organization/units', payload))
    }
    ElMessage.success(unitForm.id ? '组织已修改' : '组织已新增')
    showUnitDialog.value = false
    await fetchOptions()
  } catch (e) {
    ElMessage.error(e.message || '新增组织失败')
  } finally {
    savingUnit.value = false
  }
}

async function deleteUnit(row) {
  try {
    await ElMessageBox.confirm(`确认删除组织“${row.name}”？存在下级组织时不能删除。`, '删除组织', { type: 'warning' })
    ensureSuccess(await request.delete(`/api/user/organization/units/${row.id}`))
    ElMessage.success('组织已删除')
    await fetchOptions()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message || '删除组织失败')
  }
}


function unitTypeLabel(type) {
  return { SCHOOL: '学校', COLLEGE: '学院', CLASS: '班级' }[type] || type
}

function unitTag(type) {
  return { SCHOOL: 'success', COLLEGE: 'primary', CLASS: 'warning' }[type] || 'info'
}

function unitPath(row) {
  if (row.type === 'SCHOOL') return '一级组织'
  if (row.type === 'COLLEGE') return `归属于学校：${row.parentName || '-'}`
  if (row.type === 'CLASS') return `归属于学院：${row.parentName || '-'}`
  return '组织节点'
}

function relationText(row) {
  if (row.type === 'SCHOOL') return `${row.children?.length || 0} 个学院`
  if (row.type === 'COLLEGE') return `${row.children?.length || 0} 个班级`
  return '0'
}

onMounted(fetchOptions)
</script>

<style scoped>
.terminal-unit {
  color: var(--admin-faint);
  font-size: 12px;
}

.org-query-card :deep(.el-card__body) {
  padding: 14px 18px 2px;
}

.org-query-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.org-query-form :deep(.el-input),
.org-query-form :deep(.el-select) {
  width: 240px;
}

.unit-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
}

.unit-name-inner {
  display: inline-flex;
  align-items: baseline;
  min-width: 0;
}

.unit-name-cell strong {
  color: var(--admin-text-strong);
  font-weight: 800;
  margin-right: 8px;
}

.unit-name-cell small {
  color: var(--admin-muted);
  font-size: 12px;
}

</style>
