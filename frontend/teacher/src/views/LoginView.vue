<template>
  <div class="login-page">
    <form class="login-card" @submit.prevent="onSubmit">
      <div class="login-brand">
        <span class="login-mark">师</span>
        <div>
          <h1>教师端登录</h1>
          <p>启发·竞赛大脑 · 带队教学运营</p>
        </div>
      </div>

      <label class="field">
        <span>账号</span>
        <input v-model.trim="username" type="text" autocomplete="username" placeholder="用户名 / 手机号" required />
      </label>
      <label class="field">
        <span>密码</span>
        <input v-model="password" type="password" autocomplete="current-password" placeholder="密码" required />
      </label>

      <p v-if="error" class="login-error">{{ error }}</p>

      <button class="teacher-btn teacher-btn--primary login-submit" type="submit" :disabled="loading">
        {{ loading ? '登录中…' : '进入首页' }}
      </button>

      <p class="login-hint">仅教师 / 管理员账号可登录。学生请使用学生端；与学生端共用账号体系，但角色权限分离。</p>
    </form>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../api'
import { canAccessTeacherPortal, clearAuth, setAuth } from '../utils/auth'

const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

onMounted(() => {
  if (route.query.reason === 'teacher-only') {
    error.value = '仅教师或管理员可进入教师端，学生请使用学生端。'
  }
})

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    const data = await login(username.value, password.value)
    const token = data?.token || data?.accessToken || ''
    const user = data?.user || data || {}
    if (!token) throw new Error('登录成功但未返回 token')
    // 学生等非教师角色禁止进入教师端（前后端双重约束）
    if (!canAccessTeacherPortal(user)) {
      clearAuth()
      throw new Error('当前账号不是教师或管理员，请使用学生端登录。教师端仅限教师角色。')
    }
    setAuth(token, user)
    router.replace(route.query.redirect || '/')
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 14% -12%, rgba(232, 74, 28, 0.08), transparent 34%),
    var(--ds-canvas, #f3f4f6);
}
.login-card {
  width: min(420px, 100%);
  padding: 28px 28px 24px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(29, 29, 31, 0.08);
  box-shadow: 0 16px 40px rgba(40, 36, 32, 0.08);
  display: grid;
  gap: 14px;
}
.login-brand {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 8px;
}
.login-mark {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #e84a1c;
  font-weight: 800;
  font-size: 18px;
}
.login-brand h1 {
  margin: 0;
  font-size: 22px;
}
.login-brand p {
  margin: 4px 0 0;
  color: var(--ds-muted);
  font-size: 13px;
}
.field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.field input {
  height: 44px;
  border: 1px solid rgba(29, 29, 31, 0.14);
  border-radius: 12px;
  padding: 0 14px;
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  color: var(--ds-ink);
}
.field input:focus {
  outline: none;
  border-color: #e84a1c;
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.16);
}
.login-submit {
  width: 100%;
}
.login-error {
  margin: 0;
  color: #c92f3b;
  font-size: 13px;
  font-weight: 600;
}
.login-hint {
  margin: 0;
  font-size: 12px;
  color: var(--ds-muted);
  line-height: 1.5;
}
</style>
