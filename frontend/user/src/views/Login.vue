<template>
  <main class="auth">
    <div class="auth__shell">
      <!-- 左侧：轻量产品语境（非长引导页） -->
      <aside class="auth__intro" aria-label="产品简介">
        <header class="auth__brand auth__brand--intro">
          <img
            class="auth__logo"
            src="/brand/competition-brain-mark.svg?v=20260723"
            alt=""
            width="44"
            height="44"
          />
          <div>
            <strong>启发·竞赛大脑</strong>
            <span>智能备赛工作台</span>
          </div>
        </header>

        <div class="auth__pitch">
          <h1>
            备赛路上，
            <em>少绕弯、多落地</em>
          </h1>
          <p class="auth__tagline">
            启发·竞赛大脑把训练、路演评分与 AI 辅导放在同一工作台，
            帮你把今天该做的事推进下去。
          </p>
        </div>

        <ul class="auth__points" role="list">
          <li
            v-for="(point, index) in capabilityPoints"
            :key="point.title"
            class="auth__point"
            :style="{ '--stagger': `${index * 70}ms` }"
          >
            <span class="auth__point-icon" aria-hidden="true">{{ point.icon }}</span>
            <div>
              <strong>{{ point.title }}</strong>
              <p>{{ point.desc }}</p>
            </div>
          </li>
        </ul>
      </aside>

      <!-- 右侧：登录 / 申请 -->
      <section class="auth__card" aria-labelledby="auth-title">
        <header class="auth__brand auth__brand--card">
          <img
            class="auth__logo auth__logo--sm"
            src="/brand/competition-brain-mark.svg?v=20260723"
            alt=""
            width="36"
            height="36"
          />
          <div>
            <strong>启发·竞赛大脑</strong>
            <span>智能备赛工作台</span>
          </div>
        </header>

        <div class="auth__heading">
          <h2 id="auth-title">{{ isLogin ? '登录' : '申请账号' }}</h2>
          <p>
            {{ isLogin
              ? '使用老师分配的账号进入工作台'
              : '填写信息后，请联系管理员开通' }}
          </p>
        </div>

        <form v-if="isLogin" class="auth__form" @submit.prevent="handleLogin">
          <label class="auth__field">
            <span>用户名</span>
            <input
              ref="userInputRef"
              v-model="loginForm.username"
              type="text"
              name="username"
              autocomplete="username"
              placeholder="请输入用户名"
              :class="{ 'is-error': loginErrors.username }"
              @keydown.enter.prevent="focusPassword"
            />
            <em v-if="loginErrors.username">{{ loginErrors.username }}</em>
          </label>

          <label class="auth__field">
            <span>密码</span>
            <div class="auth__password">
              <input
                ref="passInputRef"
                v-model="loginForm.password"
                :type="showPassword ? 'text' : 'password'"
                name="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                :class="{ 'is-error': loginErrors.password }"
              />
              <button
                type="button"
                class="auth__eye"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
            <em v-if="loginErrors.password">{{ loginErrors.password }}</em>
          </label>

          <div class="auth__row">
            <label class="auth__check">
              <input v-model="loginForm.remember" type="checkbox" />
              <span>记住我</span>
            </label>
            <button type="button" class="auth__link" @click="handleForgotPassword">
              忘记密码
            </button>
          </div>

          <button class="auth__submit" type="submit" :disabled="loading">
            <span v-if="!loading">进入工作台</span>
            <span v-else class="auth__submit-busy">
              <i class="auth__spin" aria-hidden="true" />
              登录中…
            </span>
          </button>
        </form>

        <form v-else class="auth__form" @submit.prevent="handleRegister">
          <label class="auth__field">
            <span>用户名</span>
            <input
              v-model="registerForm.username"
              type="text"
              maxlength="20"
              autocomplete="username"
              placeholder="2–20 位登录名"
              :class="{ 'is-error': registerErrors.username }"
            />
            <em v-if="registerErrors.username">{{ registerErrors.username }}</em>
          </label>

          <label class="auth__field">
            <span>邮箱</span>
            <input
              v-model="registerForm.email"
              type="email"
              autocomplete="email"
              placeholder="用于接收开通通知"
              :class="{ 'is-error': registerErrors.email }"
            />
            <em v-if="registerErrors.email">{{ registerErrors.email }}</em>
          </label>

          <label class="auth__field">
            <span>密码</span>
            <input
              v-model="registerForm.password"
              type="password"
              autocomplete="new-password"
              placeholder="至少 6 位"
              :class="{ 'is-error': registerErrors.password }"
            />
            <em v-if="registerErrors.password">{{ registerErrors.password }}</em>
          </label>

          <label class="auth__field">
            <span>确认密码</span>
            <input
              v-model="registerForm.confirmPassword"
              type="password"
              autocomplete="new-password"
              placeholder="再次输入密码"
              :class="{ 'is-error': registerErrors.confirmPassword }"
            />
            <em v-if="registerErrors.confirmPassword">{{ registerErrors.confirmPassword }}</em>
          </label>

          <button class="auth__submit" type="submit" :disabled="loading">
            {{ loading ? '提交中…' : '提交申请' }}
          </button>
        </form>

        <footer class="auth__footer">
          <template v-if="isLogin">
            <span>还没有账号？</span>
            <button type="button" class="auth__link" @click="switchTab('register')">
              申请账号
            </button>
          </template>
          <template v-else>
            <span>已有账号？</span>
            <button type="button" class="auth__link" @click="switchTab('login')">
              返回登录
            </button>
          </template>
        </footer>
      </section>
    </div>

    <p class="auth__hint">账号由老师或管理员开通 · 启发·竞赛大脑</p>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeTab = ref('login')
const loading = ref(false)
const showPassword = ref(false)
const userInputRef = ref(null)
const passInputRef = ref(null)

const isLogin = computed(() => activeTab.value === 'login')

/** 轻量能力点：补产品语境，不是长引导页 */
const capabilityPoints = [
  {
    icon: '训',
    title: '今日训练与任务',
    desc: '看清今天该推进什么，节奏不摊薄。',
  },
  {
    icon: '演',
    title: '路演评分与复盘',
    desc: '五维诊断指出短板，下次知道练什么。',
  },
  {
    icon: '启',
    title: '小启 AI 辅导',
    desc: '开场、讲稿与备赛安排，随时可问。',
  },
]

const loginForm = reactive({
  username: '',
  password: '',
  remember: true,
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const loginErrors = reactive({ username: '', password: '' })
const registerErrors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

onMounted(() => {
  nextTick(() => userInputRef.value?.focus?.())
})

function switchTab(tab) {
  activeTab.value = tab
  clearErrors()
  showPassword.value = false
}

function clearErrors() {
  loginErrors.username = ''
  loginErrors.password = ''
  registerErrors.username = ''
  registerErrors.email = ''
  registerErrors.password = ''
  registerErrors.confirmPassword = ''
}

function focusPassword() {
  passInputRef.value?.focus?.()
}

function validateLogin() {
  clearErrors()
  let valid = true
  if (!loginForm.username.trim()) {
    loginErrors.username = '请输入用户名'
    valid = false
  }
  if (!loginForm.password) {
    loginErrors.password = '请输入密码'
    valid = false
  }
  return valid
}

async function handleLogin() {
  if (!validateLogin()) return
  loading.value = true
  try {
    await authStore.login(loginForm.username.trim(), loginForm.password)
    ElMessage.success('登录成功')
    const redirect = resolveLoginRedirect(route.query?.redirect)
    router.replace(redirect || '/')
  } catch (error) {
    console.error('登录失败:', error)
  } finally {
    loading.value = false
  }
}

function resolveLoginRedirect(raw) {
  if (raw == null || raw === '') return null
  let value = String(Array.isArray(raw) ? raw[0] : raw)
  try {
    value = decodeURIComponent(value)
  } catch {
    /* keep */
  }
  if (!value.startsWith('/') || value.startsWith('//')) return null
  if (value.startsWith('/login') || value.startsWith('/register') || value.startsWith('/intro')) {
    return null
  }
  return value
}

function validateRegister() {
  clearErrors()
  let valid = true
  if (!registerForm.username.trim()) {
    registerErrors.username = '请输入用户名'
    valid = false
  } else if (registerForm.username.trim().length < 2) {
    registerErrors.username = '用户名至少 2 位'
    valid = false
  }
  if (!registerForm.email.trim()) {
    registerErrors.email = '请输入邮箱'
    valid = false
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerForm.email)) {
    registerErrors.email = '请输入有效邮箱'
    valid = false
  }
  if (!registerForm.password) {
    registerErrors.password = '请输入密码'
    valid = false
  } else if (registerForm.password.length < 6) {
    registerErrors.password = '密码至少 6 位'
    valid = false
  }
  if (!registerForm.confirmPassword) {
    registerErrors.confirmPassword = '请确认密码'
    valid = false
  } else if (registerForm.password !== registerForm.confirmPassword) {
    registerErrors.confirmPassword = '两次密码不一致'
    valid = false
  }
  return valid
}

async function handleRegister() {
  if (!validateRegister()) return
  loading.value = true
  try {
    ElMessage.success('申请已记录，请联系管理员开通账号')
    activeTab.value = 'login'
    loginForm.username = registerForm.username.trim()
  } finally {
    loading.value = false
  }
}

function handleForgotPassword() {
  ElMessage.info('请联系老师或管理员重置密码')
}
</script>

<style scoped>
.auth {
  --auth-ink: #18181b;
  --auth-muted: #71717a;
  --auth-line: rgba(15, 23, 42, 0.08);
  --auth-orange: #e84a1c;
  --auth-orange-deep: #c43a12;
  --auth-ring: rgba(232, 74, 28, 0.18);
  --auth-canvas: #f7f7f8;
  --auth-ease: cubic-bezier(0.22, 1, 0.36, 1);

  position: relative;
  min-height: 100%;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px 40px;
  box-sizing: border-box;
  color: var(--auth-ink);
  overflow: auto;
  -webkit-overflow-scrolling: touch;
  background-color: var(--auth-canvas);
  background-image:
    radial-gradient(ellipse 70% 55% at 50% -10%, rgba(255, 255, 255, 0.95), transparent 55%),
    radial-gradient(ellipse 50% 40% at 12% 88%, rgba(232, 74, 28, 0.05), transparent 60%),
    radial-gradient(ellipse 45% 35% at 92% 18%, rgba(232, 74, 28, 0.04), transparent 55%);
}

.auth__shell {
  position: relative;
  z-index: 1;
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(340px, 0.95fr);
  gap: 28px 40px;
  align-items: center;
}

/* —— 左侧介绍 —— */
.auth__intro {
  min-width: 0;
  padding: 8px 8px 8px 4px;
  animation: auth-rise 0.55s var(--auth-ease) both;
}

.auth__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth__brand--intro {
  margin-bottom: 28px;
}

.auth__brand--card {
  display: none;
  margin-bottom: 22px;
}

.auth__logo {
  width: 44px;
  height: 44px;
  display: block;
  flex-shrink: 0;
  border-radius: 12px;
}

.auth__logo--sm {
  width: 36px;
  height: 36px;
  border-radius: 10px;
}

.auth__brand strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.auth__brand span {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--auth-muted);
}

.auth__pitch h1 {
  margin: 0;
  font-size: clamp(28px, 3.2vw, 36px);
  font-weight: 700;
  letter-spacing: -0.035em;
  line-height: 1.22;
  color: var(--auth-ink);
}

.auth__pitch h1 em {
  font-style: normal;
  color: var(--auth-orange-deep);
}

.auth__tagline {
  margin: 14px 0 0;
  max-width: 36ch;
  font-size: 15px;
  line-height: 1.65;
  font-weight: 500;
  color: var(--auth-muted);
}

.auth__points {
  list-style: none;
  margin: 28px 0 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.auth__point {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 42, 0.05);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  animation: auth-rise 0.55s var(--auth-ease) both;
  animation-delay: calc(120ms + var(--stagger, 0ms));
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s var(--auth-ease);
}

.auth__point:hover {
  border-color: rgba(232, 74, 28, 0.18);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
  transform: translateY(-1px);
}

.auth__point-icon {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 800;
  color: var(--auth-orange-deep);
  background: rgba(232, 74, 28, 0.1);
  letter-spacing: 0;
}

.auth__point strong {
  display: block;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--auth-ink);
}

.auth__point p {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  font-weight: 500;
  color: var(--auth-muted);
}

/* —— 右侧登录卡 —— */
.auth__card {
  width: 100%;
  max-width: 400px;
  justify-self: end;
  padding: 32px 28px 28px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.03),
    0 12px 32px rgba(15, 23, 42, 0.06);
  animation: auth-rise 0.5s var(--auth-ease) 80ms both;
}

.auth__heading {
  margin-bottom: 22px;
}

.auth__heading h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.auth__heading p {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--auth-muted);
  font-weight: 500;
}

.auth__form {
  display: grid;
  gap: 14px;
}

.auth__field {
  display: grid;
  gap: 6px;
}

.auth__field > span {
  font-size: 13px;
  font-weight: 650;
  color: #3f3f46;
}

.auth__field input,
.auth__password input {
  width: 100%;
  height: 46px;
  box-sizing: border-box;
  border: 1px solid var(--auth-line);
  border-radius: 12px;
  padding: 0 14px;
  font: inherit;
  font-size: 15px;
  color: var(--auth-ink);
  background: #fff;
  outline: none;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.auth__field input::placeholder,
.auth__password input::placeholder {
  color: #a1a1aa;
}

.auth__field input:hover,
.auth__password input:hover {
  border-color: rgba(24, 24, 27, 0.16);
}

.auth__field input:focus,
.auth__password input:focus {
  border-color: rgba(232, 74, 28, 0.55);
  box-shadow: 0 0 0 3px var(--auth-ring);
}

.auth__field input.is-error,
.auth__password input.is-error {
  border-color: rgba(185, 28, 28, 0.45);
}

.auth__field em {
  font-style: normal;
  font-size: 12px;
  font-weight: 600;
  color: #b91c1c;
}

.auth__password {
  position: relative;
  display: grid;
}

.auth__password input {
  padding-right: 58px;
}

.auth__eye {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  height: 34px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--auth-muted);
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.auth__eye:hover {
  color: var(--auth-orange-deep);
  background: rgba(232, 74, 28, 0.06);
}

.auth__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 28px;
}

.auth__check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.auth__check input {
  width: 15px;
  height: 15px;
  accent-color: var(--auth-orange);
  cursor: pointer;
}

.auth__check span {
  font-size: 13px;
  font-weight: 600;
  color: #52525b;
}

.auth__link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--auth-orange-deep);
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.auth__link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.auth__submit {
  margin-top: 4px;
  height: 48px;
  border: 0;
  border-radius: 12px;
  background: var(--auth-orange);
  color: #fff;
  font: inherit;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition:
    background 0.18s ease,
    transform 0.15s var(--auth-ease),
    box-shadow 0.18s ease,
    opacity 0.15s ease;
  box-shadow: 0 6px 16px rgba(232, 74, 28, 0.2);
}

.auth__submit:hover:not(:disabled) {
  background: var(--auth-orange-deep);
  box-shadow: 0 8px 20px rgba(196, 58, 18, 0.24);
  transform: translateY(-1px);
}

.auth__submit:active:not(:disabled) {
  transform: translateY(0) scale(0.99);
}

.auth__submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.auth__submit-busy {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.auth__spin {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: auth-spin 0.7s linear infinite;
}

.auth__footer {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--auth-line);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: var(--auth-muted);
  font-weight: 550;
}

.auth__hint {
  position: relative;
  z-index: 1;
  margin: 24px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: #a1a1aa;
  text-align: center;
  animation: auth-rise 0.55s var(--auth-ease) 0.28s both;
}

@keyframes auth-rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes auth-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 平板：收紧间距 */
@media (max-width: 900px) {
  .auth__shell {
    width: min(400px, 100%);
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .auth__intro {
    padding: 0;
    text-align: left;
  }

  .auth__pitch h1 {
    font-size: 26px;
  }

  .auth__tagline {
    max-width: none;
    font-size: 14px;
  }

  .auth__points {
    margin-top: 18px;
    gap: 8px;
  }

  .auth__point {
    padding: 12px;
  }

  .auth__card {
    justify-self: stretch;
    max-width: none;
  }

  /* 小屏登录卡上显示品牌，左侧品牌可保留 */
  .auth__brand--card {
    display: none;
  }
}

/* 手机：介绍压短，能力点横排摘要或更紧 */
@media (max-width: 560px) {
  .auth {
    padding: 20px 16px 28px;
    justify-content: flex-start;
    padding-top: max(28px, 6vh);
  }

  .auth__pitch h1 {
    font-size: 24px;
  }

  .auth__points {
    gap: 8px;
  }

  .auth__point p {
    font-size: 12px;
  }

  .auth__card {
    padding: 24px 18px 20px;
    border-radius: 18px;
  }

  .auth__heading h2 {
    font-size: 22px;
  }

  /* 能力点在登录卡下方更自然时：shell 顺序 intro → card 已合适 */
}

@media (prefers-reduced-motion: reduce) {
  .auth__intro,
  .auth__card,
  .auth__point,
  .auth__hint {
    animation: none !important;
  }

  .auth__point,
  .auth__field input,
  .auth__password input,
  .auth__submit,
  .auth__eye {
    transition: none !important;
  }

  .auth__point:hover,
  .auth__submit:hover:not(:disabled),
  .auth__submit:active:not(:disabled) {
    transform: none !important;
  }

  .auth__spin {
    animation: none;
  }
}
</style>
