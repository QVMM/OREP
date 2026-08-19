<template>
  <div class="no-access admin-page">
    <section class="access-card">
      <span class="admin-kicker">访问受限</span>
      <h1>无权访问管理后台</h1>
      <p>当前账号（{{ userStore.username || '未登录' }}）没有管理后台权限。</p>
      <p>仅平台管理员、学校管理员或教师可进入后台；学生与普通用户请使用用户端。</p>
      <el-button type="primary" @click="goLogin">返回登录</el-button>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

function goLogin() {
  userStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.no-access {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at 50% 0%, rgba(243, 107, 23, 0.18), transparent 28rem),
    var(--admin-bg);
}

.access-card {
  width: min(100%, 560px);
  padding: 40px;
  border: 1px solid var(--admin-border-soft);
  border-radius: var(--admin-radius-lg);
  background: var(--admin-surface);
  box-shadow: var(--admin-shadow);
  text-align: center;
}

.access-card h1 {
  margin: 8px 0 14px;
  color: var(--admin-text-strong);
  font-size: 30px;
}

.access-card p {
  margin: 8px 0;
  color: var(--admin-muted);
  line-height: 1.7;
}

.access-card .el-button {
  margin-top: 18px;
}
</style>
