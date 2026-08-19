<template>
  <div class="admin-login-page">
    <section class="command-panel">
      <div class="command-grid" aria-hidden="true"></div>
      <div class="command-frame" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>

      <div class="command-content">
        <div class="brand-lockup">
          <div class="brand-mark">OREP</div>
          <div class="brand-copy">
            <span>竞赛备赛大脑</span>
            <strong>管理控制台</strong>
          </div>
        </div>

        <div class="command-hero">
          <p class="kicker">管理员入口</p>
          <h1>管理后台指挥中枢</h1>
          <p>
            面向运营与教研管理者，集中监管用户、资源、评分、会议与平台数据状态。
          </p>
        </div>

        <div class="authority-strip" aria-label="管理端能力">
          <div class="authority-cell">
            <span>权限</span>
            <strong>权限管控</strong>
          </div>
          <div class="authority-cell">
            <span>审计</span>
            <strong>数据审计</strong>
          </div>
          <div class="authority-cell">
            <span>运营</span>
            <strong>资源治理</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="access-panel">
      <div class="access-card">
        <div class="card-header">
          <p class="kicker">安全登录</p>
          <h2>管理员登录</h2>
          <p>请使用已授权的管理账号进入后台</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          size="large"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="用户名"
              :prefix-icon="User"
              size="large"
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              :prefix-icon="Lock"
              show-password
              size="large"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              class="login-btn"
              @click="handleLogin"
            >
              进入后台
            </el-button>
          </el-form-item>
        </el-form>

        <div class="admin-note">
          <span>后台权限由系统管理员统一分配</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import request from '../api/request'
import { useUserStore } from '../stores/user'
import { canAccessAdmin } from '../utils/permissions'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

// 表单数据
const form = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 处理登录
async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    const res = await request.post('/api/auth/login', {
      username: form.username,
      password: form.password
    })
    const payload = res.data || res
    const user = payload.user || {}
    const role = user.role || payload.role
    if (!canAccessAdmin(role)) {
      ElMessage.error('该账号无权进入管理后台')
      return
    }
    userStore.setLoginInfo({
      token: payload.token,
      username: user.username || form.username,
      role,
      tenantId: user.tenantId ?? null,
    })
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (err) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 20%, rgba(243, 107, 23, 0.18), transparent 28%),
    radial-gradient(circle at 80% 78%, rgba(255, 241, 232, 0.14), transparent 30%),
    linear-gradient(135deg, #171717 0%, #24160f 52%, #0f0f0f 100%);
  color: #fff8f3;
  font-family: var(--admin-font-sans);
}

.command-panel {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 64px;
  border-right: 1px solid rgba(255, 248, 243, 0.14);
}

.command-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 248, 243, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 248, 243, 0.055) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.78), transparent 84%);
}

.command-frame {
  position: absolute;
  right: -90px;
  bottom: -130px;
  width: 560px;
  height: 560px;
  border: 1px solid rgba(243, 107, 23, 0.34);
  transform: rotate(12deg);
}

.command-frame span {
  position: absolute;
  border: 1px solid rgba(255, 248, 243, 0.12);
}

.command-frame span:nth-child(1) {
  inset: 70px;
}

.command-frame span:nth-child(2) {
  inset: 140px;
}

.command-frame span:nth-child(3) {
  inset: 210px;
  background: rgba(243, 107, 23, 0.1);
}

.command-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 640px;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 96px;
}

.brand-mark {
  min-width: 126px;
  height: 46px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 248, 243, 0.86);
  background: #fff8f3;
  color: #171717;
  font-size: 21px;
  font-weight: 900;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.brand-copy span,
.kicker,
.authority-cell span {
  font-size: 11px;
  line-height: 1;
  color: rgba(255, 248, 243, 0.56);
  letter-spacing: 0.08em;
}

.brand-copy strong {
  font-size: 13px;
  line-height: 1;
  color: #f36b17;
  letter-spacing: 0.08em;
}

.command-hero {
  max-width: 640px;
}

.command-hero h1 {
  max-width: 640px;
  margin: 16px 0 18px;
  color: #fff8f3;
  font-size: 52px;
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: 0;
}

.command-hero p:not(.kicker) {
  max-width: 550px;
  margin: 0;
  color: rgba(255, 248, 243, 0.68);
  font-size: 16px;
  line-height: 1.8;
  overflow-wrap: anywhere;
}

.authority-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 72px;
  border: 1px solid rgba(255, 248, 243, 0.16);
  background: rgba(255, 248, 243, 0.045);
}

.authority-cell {
  min-height: 92px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.authority-cell + .authority-cell {
  border-left: 1px solid rgba(240, 248, 242, 0.12);
}

.authority-cell strong {
  color: #f0f8f2;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}

.access-panel {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 15, 15, 0.78);
  padding: 48px;
}

.access-card {
  width: 100%;
  max-width: 360px;
  padding: 34px;
  border: 1px solid rgba(255, 248, 243, 0.16);
  border-radius: 24px;
  background: rgba(255, 248, 243, 0.055);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.26);
}

.card-header {
  margin-bottom: 32px;
}

.card-header .kicker {
  margin: 0 0 14px;
}

.card-header h2 {
  margin: 0 0 8px;
  color: #fff8f3;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 0;
}

.card-header p {
  margin: 0;
  color: rgba(255, 248, 243, 0.62);
  font-size: 15px;
}

.admin-login-page :deep(.el-input__wrapper) {
  padding: 12px 16px;
  border-radius: 14px;
  background: rgba(255, 248, 243, 0.05);
  box-shadow: 0 0 0 1px rgba(255, 248, 243, 0.16);
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.admin-login-page :deep(.el-input__wrapper:hover) {
  background: rgba(255, 248, 243, 0.08);
  box-shadow: 0 0 0 1px rgba(255, 248, 243, 0.28);
}

.admin-login-page :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px rgba(243, 107, 23, 0.9),
    0 0 0 4px rgba(243, 107, 23, 0.12);
}

.admin-login-page :deep(.el-input__inner) {
  color: #fff8f3;
  font-size: 15px;
}

.admin-login-page :deep(.el-input__inner::placeholder) {
  color: rgba(255, 248, 243, 0.38);
}

.admin-login-page :deep(.el-input__prefix),
.admin-login-page :deep(.el-input__suffix) {
  color: rgba(255, 248, 243, 0.58);
}

.admin-login-page :deep(.el-form-item) {
  margin-bottom: 20px;
}

.admin-login-page :deep(.el-form-item__error) {
  color: #ff7b7b;
  padding-top: 6px;
}

.login-btn {
  width: 100%;
  height: 48px;
  border: 1px solid #f36b17;
  border-radius: 999px;
  background: #f36b17;
  color: #ffffff;
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 0.08em;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.login-btn:hover {
  color: #ffffff;
  background: #ff8537;
  border-color: #ff8537;
  transform: translateY(-1px);
}

.admin-note {
  margin-top: 24px;
  text-align: center;
  color: rgba(255, 248, 243, 0.58);
  font-size: 14px;
}

@media (max-width: 1080px) {
  .admin-login-page {
    min-height: 100vh;
    overflow: auto;
    flex-direction: column;
  }

  .command-panel {
    width: 100%;
    min-height: 48vh;
    padding: 40px 28px;
    border-right: 0;
    border-bottom: 1px solid rgba(255, 248, 243, 0.14);
  }

  .brand-lockup {
    margin-bottom: 48px;
  }

  .command-hero h1 {
    font-size: 38px;
  }

  .authority-strip {
    margin-top: 40px;
  }

  .access-panel {
    width: 100%;
    min-height: 52vh;
    padding: 40px 24px;
  }
}

@media (max-width: 640px) {
  .command-panel {
    padding: 28px 18px;
  }

  .command-frame {
    display: none;
  }

  .brand-lockup {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }

  .command-hero h1 {
    font-size: 30px;
  }

  .command-hero p:not(.kicker) {
    max-width: 100%;
    font-size: 14px;
  }

  .authority-strip {
    grid-template-columns: 1fr;
  }

  .authority-cell + .authority-cell {
    border-left: 0;
    border-top: 1px solid rgba(255, 248, 243, 0.12);
  }

  .access-panel {
    padding: 24px 16px 32px;
  }

  .access-card {
    padding: 24px;
  }

  .card-header h2 {
    font-size: 26px;
  }
}
</style>
