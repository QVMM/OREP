<template>
  <div class="user-group-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">用户与组织 / 用户组</span>
        <h1>用户组</h1>
        <p>用户组用于跨组织筛选和后续权限模板，不替代学校、学院、班级归属。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button type="primary" @click="openGroupDialog()"><el-icon><Plus /></el-icon>新增用户组</el-button>
      </div>
    </section>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">用户组列表</span>
            <span class="admin-panel-subtitle">用于专家组、学生组、指导教师组、评委组等横向分组。</span>
          </div>
        </div>
      </template>
      <div class="admin-filter-bar">
        <el-input v-model.trim="keyword" clearable placeholder="搜索用户组名称 / 说明" />
        <el-button plain @click="fetchGroups">刷新</el-button>
      </div>
      <el-table :data="filteredGroups" v-loading="loading" border stripe>
        <el-table-column prop="name" label="用户组" min-width="180" />
        <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openGroupDialog(row)">修改</el-button>
            <el-button type="danger" link @click="deleteGroup(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filteredGroups.length === 0 && !loading" class="admin-empty">暂无匹配用户组。</div>
    </el-card>

    <el-dialog v-model="showGroupDialog" :title="groupForm.id ? '修改用户组' : '新增用户组'" width="520px" @closed="resetGroupForm">
      <el-form ref="groupFormRef" :model="groupForm" :rules="groupRules" label-width="82px">
        <el-form-item label="名称" prop="name">
          <el-input v-model.trim="groupForm.name" placeholder="例如：国赛备赛学生组" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model.trim="groupForm.description" type="textarea" :rows="3" placeholder="用户组用途、权限边界或筛选说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="showGroupDialog = false">取消</el-button>
        <el-button type="primary" round :loading="savingGroup" @click="saveGroup">保存</el-button>
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
const savingGroup = ref(false)
const groups = ref([])
const keyword = ref('')
const showGroupDialog = ref(false)
const groupFormRef = ref(null)

const groupForm = reactive({ id: null, name: '', description: '' })
const groupRules = {
  name: [{ required: true, message: '请输入用户组名称', trigger: 'blur' }]
}

const filteredGroups = computed(() => {
  const q = keyword.value.toLowerCase()
  if (!q) return groups.value
  return groups.value.filter(item => `${item.name || ''} ${item.description || ''}`.toLowerCase().includes(q))
})

function ensureSuccess(res) {
  if (res?.code && res.code !== 200) throw new Error(res.message || '操作失败')
  return res
}

async function fetchGroups() {
  loading.value = true
  try {
    const res = ensureSuccess(await request.get('/api/user/organization/options'))
    groups.value = res.data?.groups || []
  } finally {
    loading.value = false
  }
}

function openGroupDialog(row) {
  resetGroupForm()
  if (row) {
    Object.assign(groupForm, {
      id: row.id,
      name: row.name || '',
      description: row.description || ''
    })
  }
  showGroupDialog.value = true
}

function resetGroupForm() {
  Object.assign(groupForm, { id: null, name: '', description: '' })
  groupFormRef.value?.clearValidate()
}

async function saveGroup() {
  const valid = await groupFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingGroup.value = true
  try {
    if (groupForm.id) {
      ensureSuccess(await request.put(`/api/user/organization/groups/${groupForm.id}`, groupForm))
    } else {
      ensureSuccess(await request.post('/api/user/organization/groups', groupForm))
    }
    ElMessage.success(groupForm.id ? '用户组已修改' : '用户组已新增')
    showGroupDialog.value = false
    await fetchGroups()
  } catch (e) {
    ElMessage.error(e.message || '保存用户组失败')
  } finally {
    savingGroup.value = false
  }
}

async function deleteGroup(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户组“${row.name}”？`, '删除用户组', { type: 'warning' })
    ensureSuccess(await request.delete(`/api/user/organization/groups/${row.id}`))
    ElMessage.success('用户组已删除')
    await fetchGroups()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message || '删除用户组失败')
  }
}

onMounted(fetchGroups)
</script>
