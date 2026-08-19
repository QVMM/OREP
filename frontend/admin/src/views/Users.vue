<template>
  <div class="users-page admin-page">
    <section class="admin-page-hero">
      <div>
        <span class="admin-kicker">用户管理</span>
        <h1>维护账号、角色和组织归属</h1>
        <p>先用角色、学校、学院、班级和用户组定位用户，再处理新增、改角色、改归属或删除。减少管理员在大表格里反复查找。</p>
      </div>
      <div class="admin-hero-actions">
        <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon>新增用户</el-button>
        <el-button plain @click="refreshAll"><el-icon><RefreshRight /></el-icon>刷新</el-button>
      </div>
    </section>

    <section class="admin-metrics">
      <article class="admin-metric-card"><strong>{{ users.length }}</strong><span>用户总数</span><small>当前筛选 {{ filteredUsers.length }} 人</small></article>
      <article class="admin-metric-card"><strong>{{ adminUserCount }}</strong><span>管理成员</span><small>管理员、校级管理员和教师</small></article>
      <article class="admin-metric-card"><strong>{{ studentUserCount }}</strong><span>学生用户</span><small>主要参与学习、考试和路演</small></article>
      <article class="admin-metric-card"><strong>{{ selectedUsers.length }}</strong><span>已选用户</span><small>可执行批量删除</small></article>
    </section>

    <el-card class="admin-table-card">
      <template #header>
        <div class="admin-panel-head">
          <div>
            <span class="admin-panel-title">用户列表</span>
            <span class="admin-panel-subtitle">先筛选，再编辑。角色和组织归属分开操作，降低误改权限风险。</span>
          </div>
          <div class="admin-panel-actions">
            <el-button
              type="danger"
              size="small"
              :disabled="selectedUsers.length === 0"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除
            </el-button>
          </div>
        </div>
      </template>

      <div class="admin-filter-bar">
        <el-input v-model.trim="filters.keyword" clearable placeholder="搜索用户名 / 邮箱" />
        <el-select v-model="filters.role" clearable placeholder="角色">
          <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
        </el-select>
        <el-select v-if="schools.length > 1" v-model="filters.schoolId" clearable placeholder="学校" @change="onFilterSchoolChange">
          <el-option v-for="item in schools" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-if="filterColleges.length > 1" v-model="filters.collegeId" clearable placeholder="学院" @change="onFilterCollegeChange">
          <el-option v-for="item in filterColleges" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="filters.classId" clearable placeholder="班级">
          <el-option v-for="item in filterClasses" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="filters.groupId" clearable placeholder="用户组">
          <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button plain @click="resetFilters">清空筛选</el-button>
      </div>

      <el-table
        :data="filteredUsers"
        v-loading="loading"
        border
        stripe
        @selection-change="selectedUsers = $event"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="150">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="28">{{ row.username?.charAt(0)?.toUpperCase() }}</el-avatar>
              <span>{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="210" show-overflow-tooltip />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" effect="light" round>
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="组织归属" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="org-cell">
              <strong>{{ row.schoolName || '未设置学校' }}</strong>
              <small>{{ row.collegeName || '未设置学院' }} / {{ row.className || '未设置班级' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="用户组" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.groupNames || row.userGroup || '未分组' }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.isPlatformAdmin" prop="tenantId" label="租户" width="80" />
        <el-table-column prop="createdAt" label="注册时间" width="170" />
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openUsernameDialog(row)">
              <el-icon><EditPen /></el-icon>
              用户名
            </el-button>
            <el-button size="small" type="primary" link @click="openOrgDialog(row)">
              <el-icon><OfficeBuilding /></el-icon>
              归属
            </el-button>
            <el-button size="small" type="primary" link @click="openRoleDialog(row)">
              <el-icon><Edit /></el-icon>
              角色
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filteredUsers.length === 0 && !loading" class="admin-empty">没有匹配用户。请清空筛选条件，或新增用户。</div>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="新增用户" width="720px" @closed="resetCreateForm">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="96px">
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model.trim="createForm.username" placeholder="2-20 位用户名" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model.trim="createForm.email" placeholder="用于登录和通知的邮箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="初始密码" prop="password">
              <el-input v-model="createForm.password" type="password" show-password placeholder="6-30 位初始密码" maxlength="30" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" prop="role">
              <el-select v-model="createForm.role" style="width: 100%">
                <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学校">
              <el-select
                v-model="createForm.schoolId"
                :disabled="schools.length === 1"
                clearable
                filterable
                style="width: 100%"
                @change="onCreateSchoolChange"
              >
                <el-option v-for="item in schools" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学院">
              <el-select v-model="createForm.collegeId" clearable filterable style="width: 100%" @change="onCreateCollegeChange">
                <el-option v-for="item in createColleges" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="班级">
              <el-select v-model="createForm.classId" clearable filterable style="width: 100%">
                <el-option v-for="item in createClasses" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用户组">
              <el-select v-model="createForm.groupIds" multiple filterable collapse-tags collapse-tags-tooltip style="width: 100%">
                <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button round @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" round :loading="savingUser" @click="createUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showOrgDialog" title="编辑组织归属" width="620px">
      <el-form label-width="86px">
        <el-form-item label="用户">
          <span>{{ editUser?.username }}</span>
        </el-form-item>
        <el-form-item label="学校">
          <el-select v-model="orgForm.schoolId" clearable filterable style="width: 100%" @change="onOrgSchoolChange">
            <el-option v-for="item in schools" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学院">
          <el-select v-model="orgForm.collegeId" clearable filterable style="width: 100%" @change="onOrgCollegeChange">
            <el-option v-for="item in orgColleges" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="orgForm.classId" clearable filterable style="width: 100%">
            <el-option v-for="item in orgClasses" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户组">
          <el-select v-model="orgForm.groupIds" multiple filterable collapse-tags collapse-tags-tooltip style="width: 100%">
            <el-option v-for="item in groups" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="showOrgDialog = false">取消</el-button>
        <el-button type="primary" round :loading="savingOrg" @click="updateOrganization">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUsernameDialog" title="修改用户名" width="420px">
      <el-form ref="usernameFormRef" :model="usernameForm" :rules="usernameRules" label-width="80px">
        <el-form-item label="原用户名">
          <span>{{ editUser?.username }}</span>
        </el-form-item>
        <el-form-item label="新用户名" prop="username">
          <el-input
            v-model.trim="usernameForm.username"
            placeholder="2-20 位，用于登录"
            maxlength="20"
            show-word-limit
          />
        </el-form-item>
        <p class="username-hint">修改后该账号需用新用户名登录；邮箱与密码不变。</p>
      </el-form>
      <template #footer>
        <el-button round @click="showUsernameDialog = false">取消</el-button>
        <el-button type="primary" round :loading="savingUsername" @click="updateUsername">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRoleDialog" title="修改用户角色" width="400px">
      <el-form label-width="70px">
        <el-form-item label="用户">
          <span>{{ editUser?.username }}</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newRole" style="width: 100%">
            <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="showRoleDialog = false">取消</el-button>
        <el-button type="primary" round :loading="savingRole" @click="updateRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, EditPen, OfficeBuilding, Plus, RefreshRight } from '@element-plus/icons-vue'
import request from '../api/request'
import { batchDeleteSummary, idsFromRows } from '../utils/batchDelete'
import { assignableRoleOptions } from '../utils/permissions'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

const loading = ref(false)
const savingUser = ref(false)
const savingRole = ref(false)
const savingOrg = ref(false)
const savingUsername = ref(false)
const users = ref([])
const selectedUsers = ref([])
const units = ref([])
const groups = ref([])
const showCreateDialog = ref(false)
const showRoleDialog = ref(false)
const showOrgDialog = ref(false)
const showUsernameDialog = ref(false)
const createFormRef = ref(null)
const usernameFormRef = ref(null)
const editUser = ref(null)
const newRole = ref('')
const usernameForm = reactive({ username: '' })
const usernameRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度为 2-20 位', trigger: 'blur' },
    {
      pattern: /^[\w\u4e00-\u9fa5.-]+$/,
      message: '仅支持中英文、数字、下划线、点与短横线',
      trigger: 'blur',
    },
  ],
}

const roleOptions = computed(() => assignableRoleOptions(userStore.role))

const filters = reactive({
  keyword: '',
  role: '',
  schoolId: '',
  collegeId: '',
  classId: '',
  groupId: ''
})

const createForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'STUDENT',
  schoolId: '',
  collegeId: '',
  classId: '',
  groupIds: []
})

const orgForm = reactive({
  schoolId: '',
  collegeId: '',
  classId: '',
  groupIds: []
})

const createRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度为 2-20 位', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度为 6-30 位', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const schools = computed(() => units.value.filter(item => item.type === 'SCHOOL'))
const colleges = computed(() => units.value.filter(item => item.type === 'COLLEGE'))
const classes = computed(() => units.value.filter(item => item.type === 'CLASS'))
const filterColleges = computed(() => colleges.value.filter(item => !filters.schoolId || Number(item.parentId) === Number(filters.schoolId)))
const filterClasses = computed(() => classes.value.filter(item => !filters.collegeId || Number(item.parentId) === Number(filters.collegeId)))
const createColleges = computed(() => colleges.value.filter(item => !createForm.schoolId || Number(item.parentId) === Number(createForm.schoolId)))
const createClasses = computed(() => classes.value.filter(item => !createForm.collegeId || Number(item.parentId) === Number(createForm.collegeId)))
const orgColleges = computed(() => colleges.value.filter(item => !orgForm.schoolId || Number(item.parentId) === Number(orgForm.schoolId)))
const orgClasses = computed(() => classes.value.filter(item => !orgForm.collegeId || Number(item.parentId) === Number(orgForm.collegeId)))
const filteredUsers = computed(() => {
  const keyword = filters.keyword.toLowerCase()
  return users.value.filter(user => {
    if (keyword && ![user.username, user.email].some(value => String(value || '').toLowerCase().includes(keyword))) return false
    if (filters.role && user.role !== filters.role) return false
    if (filters.schoolId && Number(user.schoolId) !== Number(filters.schoolId)) return false
    if (filters.collegeId && Number(user.collegeId) !== Number(filters.collegeId)) return false
    if (filters.classId && Number(user.classId) !== Number(filters.classId)) return false
    if (filters.groupId && !groupIdsOf(user).includes(Number(filters.groupId))) return false
    return true
  })
})

const adminUserCount = computed(() => users.value.filter(user => ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'].includes(user.role)).length)
const studentUserCount = computed(() => users.value.filter(user => user.role === 'STUDENT').length)

function roleLabel(role) {
  return roleOptions.value.find(item => item.value === role)?.label?.replace(/ \(.+\)/, '') || role || '未知'
}

function roleTagType(role) {
  return roleOptions.value.find(item => item.value === role)?.tag || 'info'
}

function ensureSuccess(res) {
  if (res?.code && res.code !== 200) {
    throw new Error(res.message || '操作失败')
  }
  return res
}

async function refreshAll() {
  await Promise.all([fetchOrganizationOptions(), fetchUsers()])
}

function resetFilters() {
  Object.assign(filters, {
    keyword: '',
    role: '',
    schoolId: '',
    collegeId: '',
    classId: '',
    groupId: ''
  })
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = ensureSuccess(await request.get('/api/user/list'))
    users.value = res.data || res.list || res || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function fetchOrganizationOptions() {
  const res = ensureSuccess(await request.get('/api/user/organization/options'))
  units.value = res.data?.units || []
  groups.value = res.data?.groups || []
}

function openCreateDialog() {
  resetCreateForm()
  if (schools.value.length === 1) {
    createForm.schoolId = schools.value[0].id
    if (createColleges.value.length === 1) {
      createForm.collegeId = createColleges.value[0].id
    }
  }
  showCreateDialog.value = true
}

function resetCreateForm() {
  Object.assign(createForm, {
    username: '',
    email: '',
    password: '',
    role: 'STUDENT',
    schoolId: '',
    collegeId: '',
    classId: '',
    groupIds: []
  })
  createFormRef.value?.clearValidate()
}

async function createUser() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  savingUser.value = true
  try {
    ensureSuccess(await request.post('/api/user', payloadWithNulls(createForm)))
    ElMessage.success('用户已新增')
    showCreateDialog.value = false
    await fetchUsers()
  } catch (e) {
    ElMessage.error(e.message || '新增用户失败')
    console.error(e)
  } finally {
    savingUser.value = false
  }
}

function openOrgDialog(user) {
  editUser.value = user
  Object.assign(orgForm, {
    schoolId: user.schoolId || '',
    collegeId: user.collegeId || '',
    classId: user.classId || '',
    groupIds: groupIdsOf(user)
  })
  showOrgDialog.value = true
}

async function updateOrganization() {
  if (!editUser.value) return
  savingOrg.value = true
  try {
    ensureSuccess(await request.post(`/api/user/${editUser.value.id}/organization`, payloadWithNulls(orgForm)))
    ElMessage.success('组织归属已更新')
    showOrgDialog.value = false
    await fetchUsers()
  } catch (e) {
    ElMessage.error(e.message || '保存归属失败')
    console.error(e)
  } finally {
    savingOrg.value = false
  }
}

function openRoleDialog(user) {
  editUser.value = user
  newRole.value = user.role
  showRoleDialog.value = true
}

function openUsernameDialog(user) {
  editUser.value = user
  usernameForm.username = user.username || ''
  showUsernameDialog.value = true
  usernameFormRef.value?.clearValidate()
}

async function updateUsername() {
  if (!editUser.value?.id) {
    ElMessage.error('未选中用户，请刷新页面后重试')
    return
  }
  const valid = await usernameFormRef.value?.validate().catch(() => false)
  if (!valid) return

  const next = String(usernameForm.username || '').trim()
  if (next === editUser.value.username) {
    showUsernameDialog.value = false
    return
  }

  savingUsername.value = true
  try {
    // request 拦截器在 HTTP 错误时已 toast；业务码非 200 时在此提示
    const res = await request.post(`/api/user/${editUser.value.id}/username`, { username: next })
    if (res?.code != null && Number(res.code) !== 200) {
      ElMessage.error(res.message || '用户名更新失败')
      return
    }
    ElMessage.success('用户名已更新')
    showUsernameDialog.value = false
    await fetchUsers()
  } catch (e) {
    // HTTP 4xx/5xx：拦截器已提示；此处避免再弹英文 Request failed...
    if (e?.response) return
    const msg = String(e?.message || '')
    if (msg && !/^Request failed/i.test(msg) && msg !== 'Network Error') {
      ElMessage.error(msg)
    } else {
      ElMessage.error('用户名更新失败，请稍后重试')
    }
    console.error(e)
  } finally {
    savingUsername.value = false
  }
}

async function updateRole() {
  if (!editUser.value) return

  savingRole.value = true
  try {
    ensureSuccess(await request.post(`/api/user/${editUser.value.id}/role`, { role: newRole.value }))
    ElMessage.success('角色已更新')
    showRoleDialog.value = false
    await fetchUsers()
  } catch (e) {
    ElMessage.error(e.message || '角色更新失败')
    console.error(e)
  } finally {
    savingRole.value = false
  }
}

async function handleDelete(user) {
  try {
    await ElMessageBox.confirm(
      `确认删除用户 "${user.username}"？删除后该账号将无法登录。`,
      '删除用户',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    ensureSuccess(await request.delete(`/api/user/${user.id}`))
    ElMessage.success('用户已删除')
    await fetchUsers()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.message || '删除用户失败')
      console.error(e)
    }
  }
}

async function handleBatchDelete() {
  const ids = idsFromRows(selectedUsers.value)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${ids.length} 个用户？删除后账号将无法登录。`,
      '批量删除用户',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    const res = ensureSuccess(await request.post('/api/user/batch-delete', { ids }))
    const summary = batchDeleteSummary(res, '用户')
    ElMessage[summary.type](summary.message)
    selectedUsers.value = []
    await fetchUsers()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.message || '批量删除用户失败')
      console.error(e)
    }
  }
}

function onFilterSchoolChange() {
  filters.collegeId = ''
  filters.classId = ''
}

function onFilterCollegeChange() {
  filters.classId = ''
}

function onCreateSchoolChange() {
  createForm.collegeId = ''
  createForm.classId = ''
}

function onCreateCollegeChange() {
  createForm.classId = ''
}

function onOrgSchoolChange() {
  orgForm.collegeId = ''
  orgForm.classId = ''
}

function onOrgCollegeChange() {
  orgForm.classId = ''
}

function groupIdsOf(user) {
  if (Array.isArray(user.groupIds)) return user.groupIds.map(Number)
  return String(user.groupIds || '')
    .split(',')
    .map(item => Number(item))
    .filter(Boolean)
}

function payloadWithNulls(form) {
  return {
    ...form,
    schoolId: form.schoolId || null,
    collegeId: form.collegeId || null,
    classId: form.classId || null,
    groupIds: form.groupIds || []
  }
}

onMounted(refreshAll)
</script>

<style scoped>
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.org-cell {
  display: grid;
  gap: 3px;
}

.org-cell strong {
  color: var(--admin-text-strong);
  font-weight: 600;
}

.org-cell small {
  color: var(--admin-muted);
}

.username-hint {
  margin: 0 0 0 80px;
  font-size: 12px;
  color: var(--admin-muted);
  line-height: 1.45;
}
</style>
