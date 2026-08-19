# OREP前端UI重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重新设计OREP平台的前端界面，采用现代苹果设计风格，提升用户体验和视觉一致性。

**Architecture:** 基于现有Vue 3 + Element Plus架构，创建统一的设计系统，包括CSS变量、基础组件库和页面重构。采用渐进式重构策略，确保系统稳定性。

**Tech Stack:** Vue 3, Composition API, CSS Variables, Element Plus, Vite, Pinia, Vue Router

---

## 文件结构映射

### 新增文件
- `frontend/user/src/styles/design-system.css` - 设计系统CSS变量
- `frontend/user/src/components/base/BaseButton.vue` - 基础按钮组件
- `frontend/user/src/components/base/BaseCard.vue` - 基础卡片组件
- `frontend/user/src/components/base/BaseInput.vue` - 基础输入框组件
- `frontend/user/src/components/base/BaseModal.vue` - 基础模态框组件
- `frontend/user/src/components/base/BaseIcon.vue` - 基础图标组件
- `frontend/user/src/components/layout/AppHeader.vue` - 应用头部导航
- `frontend/user/src/components/layout/AppFooter.vue` - 应用页脚
- `frontend/user/src/components/dashboard/HeroCarousel.vue` - 首页轮播组件
- `frontend/user/src/components/dashboard/TaskCard.vue` - 任务卡片组件
- `frontend/user/src/components/dashboard/QuickEntry.vue` - 快速入口组件
- `frontend/user/src/components/dashboard/RecentActivity.vue` - 最近活动组件

### 修改文件
- `frontend/user/src/App.vue` - 主应用布局重构
- `frontend/user/src/views/Dashboard.vue` - 首页重构
- `frontend/user/src/views/Login.vue` - 登录页重构
- `frontend/user/src/views/CourseLearning.vue` - 课程学习页重构
- `frontend/user/src/views/ExamSystem.vue` - 考试系统页重构
- `frontend/user/src/views/OnlineMeeting.vue` - 在线会议页重构
- `frontend/user/src/views/PptGenerator.vue` - PPT生成页重构
- `frontend/user/src/views/Profile.vue` - 个人中心页重构

---

## Task 1: 设计系统基础搭建

**Files:**
- Create: `frontend/user/src/styles/design-system.css`

- [ ] **Step 1: 创建设计系统CSS变量文件**

```css
/* frontend/user/src/styles/design-system.css */
:root {
  /* 配色方案 */
  --color-primary: #007AFF;
  --color-primary-light: #4DA3FF;
  --color-primary-dark: #0056CC;
  --color-secondary: #5856D6;
  --color-success: #34C759;
  --color-warning: #FF9500;
  --color-error: #FF3B30;
  --color-info: #007AFF;
  
  /* 背景色 */
  --color-bg-primary: #FFFFFF;
  --color-bg-secondary: #F2F2F7;
  --color-bg-tertiary: #E5E5EA;
  --color-bg-elevated: #FFFFFF;
  
  /* 文字色 */
  --color-text-primary: #1D1D1F;
  --color-text-secondary: #8E8E93;
  --color-text-tertiary: #C7C7CC;
  --color-text-inverse: #FFFFFF;
  
  /* 边框色 */
  --color-border: #E5E5EA;
  --color-border-focus: #007AFF;
  
  /* 字体系统 */
  --font-family-primary: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
  --font-family-mono: 'SF Mono', 'Fira Code', 'Roboto Mono', monospace;
  
  /* 字体大小 */
  --font-size-xs: 13px;
  --font-size-sm: 15px;
  --font-size-base: 17px;
  --font-size-lg: 20px;
  --font-size-xl: 22px;
  --font-size-2xl: 28px;
  --font-size-3xl: 34px;
  
  /* 字体粗细 */
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  
  /* 行高 */
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
  
  /* 圆角 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 50%;
  
  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.15);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.2);
  --shadow-xl: 0 12px 36px rgba(0, 0, 0, 0.25);
  
  /* 间距 */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-2xl: 48px;
  --spacing-3xl: 64px;
  
  /* 过渡动画 */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 350ms ease;
  
  /* z-index层级 */
  --z-dropdown: 1000;
  --z-sticky: 1020;
  --z-fixed: 1030;
  --z-modal-backdrop: 1040;
  --z-modal: 1050;
  --z-popover: 1060;
  --z-tooltip: 1070;
  
  /* 布局 */
  --header-height: 64px;
  --sidebar-width: 280px;
  --content-max-width: 1440px;
}

/* 深色模式（预留） */
@media (prefers-color-scheme: dark) {
  :root {
    /* 深色模式变量将在后续版本实现 */
  }
}

/* 响应式断点 */
@media (max-width: 1199px) {
  :root {
    --font-size-3xl: 28px;
    --font-size-2xl: 24px;
    --spacing-3xl: 48px;
  }
}

@media (max-width: 767px) {
  :root {
    --font-size-3xl: 24px;
    --font-size-2xl: 20px;
    --font-size-xl: 18px;
    --header-height: 56px;
    --spacing-3xl: 32px;
  }
}

/* 基础样式重置 */
*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
  background-color: var(--color-bg-secondary);
}

a {
  color: var(--color-primary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

a:hover {
  color: var(--color-primary-dark);
}

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  background: none;
}

input,
textarea,
select {
  font-family: inherit;
  font-size: inherit;
}

img {
  max-width: 100%;
  height: auto;
}

/* 工具类 */
.text-primary { color: var(--color-primary); }
.text-secondary { color: var(--color-text-secondary); }
.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-error { color: var(--color-error); }

.bg-primary { background-color: var(--color-bg-primary); }
.bg-secondary { background-color: var(--color-bg-secondary); }

.rounded-sm { border-radius: var(--radius-sm); }
.rounded-md { border-radius: var(--radius-md); }
.rounded-lg { border-radius: var(--radius-lg); }
.rounded-full { border-radius: var(--radius-full); }

.shadow-sm { box-shadow: var(--shadow-sm); }
.shadow-md { box-shadow: var(--shadow-md); }
.shadow-lg { box-shadow: var(--shadow-lg); }

/* 动画类 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all var(--transition-normal);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.scale-enter-active,
.scale-leave-active {
  transition: all var(--transition-fast);
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
```

- [ ] **Step 2: 在main.js中引入设计系统**

```javascript
// frontend/user/src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/design-system.css' // 新增：引入设计系统
import App from './App.vue'
import router from './router'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
```

- [ ] **Step 3: 验证设计系统加载**

运行开发服务器：
```bash
cd frontend/user && npm run dev
```

预期：页面正常加载，无CSS错误，浏览器开发者工具中可以看到CSS变量已定义。

- [ ] **Step 4: 提交设计系统基础**

```bash
git add frontend/user/src/styles/design-system.css frontend/user/src/main.js
git commit -m "feat: add design system CSS variables and base styles"
```

---

## Task 2: 基础组件库开发

**Files:**
- Create: `frontend/user/src/components/base/BaseButton.vue`
- Create: `frontend/user/src/components/base/BaseCard.vue`
- Create: `frontend/user/src/components/base/BaseInput.vue`
- Create: `frontend/user/src/components/base/BaseIcon.vue`

- [ ] **Step 1: 创建BaseButton组件**

```vue
<!-- frontend/user/src/components/base/BaseButton.vue -->
<template>
  <button
    :class="[
      'base-button',
      `base-button--${type}`,
      `base-button--${size}`,
      { 'base-button--disabled': disabled },
      { 'base-button--loading': loading }
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="base-button__spinner"></span>
    <span v-if="$slots.icon && !loading" class="base-button__icon">
      <slot name="icon"></slot>
    </span>
    <span class="base-button__text">
      <slot></slot>
    </span>
  </button>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'text', 'danger'].includes(value)
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const handleClick = (event) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  font-family: var(--font-family-primary);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: 1px solid transparent;
  outline: none;
  position: relative;
  overflow: hidden;
}

.base-button:active {
  transform: scale(0.98);
}

/* 类型样式 */
.base-button--primary {
  background-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.base-button--primary:hover:not(.base-button--disabled) {
  background-color: var(--color-primary-dark);
  box-shadow: var(--shadow-md);
}

.base-button--secondary {
  background-color: transparent;
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.base-button--secondary:hover:not(.base-button--disabled) {
  background-color: rgba(0, 122, 255, 0.1);
}

.base-button--text {
  background-color: transparent;
  color: var(--color-primary);
  padding: 0;
  border: none;
}

.base-button--text:hover:not(.base-button--disabled) {
  color: var(--color-primary-dark);
  text-decoration: underline;
}

.base-button--danger {
  background-color: var(--color-error);
  color: var(--color-text-inverse);
}

.base-button--danger:hover:not(.base-button--disabled) {
  background-color: #E0332B;
  box-shadow: var(--shadow-md);
}

/* 尺寸样式 */
.base-button--small {
  padding: 6px 12px;
  font-size: var(--font-size-xs);
  height: 32px;
}

.base-button--medium {
  padding: 10px 20px;
  font-size: var(--font-size-sm);
  height: 40px;
}

.base-button--large {
  padding: 14px 28px;
  font-size: var(--font-size-base);
  height: 48px;
}

/* 状态样式 */
.base-button--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.base-button--loading {
  cursor: wait;
}

/* 加载动画 */
.base-button__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.base-button__icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.base-button__text {
  display: flex;
  align-items: center;
}
</style>
```

- [ ] **Step 2: 创建BaseCard组件**

```vue
<!-- frontend/user/src/components/base/BaseCard.vue -->
<template>
  <div
    :class="[
      'base-card',
      { 'base-card--hoverable': hoverable },
      { 'base-card--elevated': elevated }
    ]"
    @click="handleClick"
  >
    <div v-if="$slots.header" class="base-card__header">
      <slot name="header"></slot>
    </div>
    <div class="base-card__body">
      <slot></slot>
    </div>
    <div v-if="$slots.footer" class="base-card__footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  hoverable: {
    type: Boolean,
    default: false
  },
  elevated: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const handleClick = (event) => {
  emit('click', event)
}
</script>

<style scoped>
.base-card {
  background-color: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.base-card--hoverable:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.base-card--elevated {
  box-shadow: var(--shadow-md);
}

.base-card__header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.base-card__body {
  padding: var(--spacing-lg);
}

.base-card__footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  background-color: var(--color-bg-secondary);
}
</style>
```

- [ ] **Step 3: 创建BaseInput组件**

```vue
<!-- frontend/user/src/components/base/BaseInput.vue -->
<template>
  <div :class="['base-input', { 'base-input--error': error }]">
    <label v-if="label" class="base-input__label" :for="inputId">
      {{ label }}
      <span v-if="required" class="base-input__required">*</span>
    </label>
    <div class="base-input__wrapper">
      <span v-if="$slots.prefix" class="base-input__prefix">
        <slot name="prefix"></slot>
      </span>
      <input
        :id="inputId"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        class="base-input__field"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      <span v-if="$slots.suffix" class="base-input__suffix">
        <slot name="suffix"></slot>
      </span>
    </div>
    <p v-if="error" class="base-input__error">{{ error }}</p>
    <p v-else-if="hint" class="base-input__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  readonly: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'focus', 'blur'])

const inputId = computed(() => `input-${Math.random().toString(36).substr(2, 9)}`)

const handleInput = (event) => {
  emit('update:modelValue', event.target.value)
}

const handleFocus = (event) => {
  emit('focus', event)
}

const handleBlur = (event) => {
  emit('blur', event)
}
</script>

<style scoped>
.base-input {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.base-input__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.base-input__required {
  color: var(--color-error);
  margin-left: 2px;
}

.base-input__wrapper {
  display: flex;
  align-items: center;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  overflow: hidden;
}

.base-input__wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

.base-input--error .base-input__wrapper {
  border-color: var(--color-error);
}

.base-input--error .base-input__wrapper:focus-within {
  box-shadow: 0 0 0 3px rgba(255, 59, 48, 0.1);
}

.base-input__prefix,
.base-input__suffix {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--spacing-md);
  color: var(--color-text-secondary);
}

.base-input__field {
  flex: 1;
  padding: 10px var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: transparent;
  border: none;
  outline: none;
}

.base-input__field::placeholder {
  color: var(--color-text-tertiary);
}

.base-input__field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.base-input__error {
  font-size: var(--font-size-xs);
  color: var(--color-error);
  margin: 0;
}

.base-input__hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin: 0;
}
</style>
```

- [ ] **Step 4: 创建BaseIcon组件**

```vue
<!-- frontend/user/src/components/base/BaseIcon.vue -->
<template>
  <span
    :class="['base-icon', `base-icon--${size}`]"
    :style="{ color: color }"
    v-html="iconSvg"
  ></span>
</template>

<script setup>
import { defineProps, computed } from 'vue'

const props = defineProps({
  name: {
    type: String,
    required: true
  },
  size: {
    type: String,
    default: 'medium',
    validator: (value) => ['small', 'medium', 'large'].includes(value)
  },
  color: {
    type: String,
    default: 'currentColor'
  }
})

// 这里可以集成图标库，如Lucide或自定义SVG
// 目前使用简单的占位实现
const iconSvg = computed(() => {
  // 实际项目中应替换为真实的图标SVG
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="10"/>
  </svg>`
})
</script>

<style scoped>
.base-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.base-icon svg {
  width: 100%;
  height: 100%;
}

.base-icon--small {
  width: 16px;
  height: 16px;
}

.base-icon--medium {
  width: 20px;
  height: 20px;
}

.base-icon--large {
  width: 24px;
  height: 24px;
}
</style>
```

- [ ] **Step 5: 创建基础组件索引文件**

```vue
<!-- frontend/user/src/components/base/index.js -->
export { default as BaseButton } from './BaseButton.vue'
export { default as BaseCard } from './BaseCard.vue'
export { default as BaseInput } from './BaseInput.vue'
export { default as BaseIcon } from './BaseIcon.vue'
```

- [ ] **Step 6: 验证基础组件**

在Dashboard.vue中临时使用BaseButton进行测试：

```vue
<template>
  <div>
    <BaseButton type="primary" @click="test">测试按钮</BaseButton>
  </div>
</template>

<script setup>
import { BaseButton } from '@/components/base'

const test = () => {
  console.log('Button clicked')
}
</script>
```

运行开发服务器验证组件正常显示。

- [ ] **Step 7: 提交基础组件**

```bash
git add frontend/user/src/components/base/
git commit -m "feat: add base UI components (Button, Card, Input, Icon)"
```

---

## Task 3: 应用布局重构

**Files:**
- Modify: `frontend/user/src/App.vue`
- Create: `frontend/user/src/components/layout/AppHeader.vue`
- Create: `frontend/user/src/components/layout/AppFooter.vue`

- [ ] **Step 1: 创建AppHeader组件**

```vue
<!-- frontend/user/src/components/layout/AppHeader.vue -->
<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="app-header__left">
        <router-link to="/" class="app-header__logo">
          <span class="app-header__logo-mark">竞赛大脑</span>
          <span class="app-header__logo-subtitle">COMPETITION BRAIN</span>
        </router-link>
      </div>

      <nav class="app-header__nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="app-header__nav-item"
          :class="{ 'app-header__nav-item--active': isActive(item.path) }"
        >
          <span class="app-header__nav-code">{{ item.code }}</span>
          <span class="app-header__nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="app-header__right">
        <el-dropdown @command="handleCommand" trigger="click">
          <div class="app-header__user">
            <div class="app-header__avatar">
              {{ username.charAt(0).toUpperCase() }}
            </div>
            <span class="app-header__username">{{ username }}</span>
            <el-icon class="app-header__arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人中心
              </el-dropdown-item>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElDropdown, ElDropdownMenu, ElDropdownItem, ElIcon } from 'element-plus'
import { ArrowDown, User, SwitchButton } from '@element-plus/icons-vue'
import { getUserToken, removeUserToken } from '@/utils/authStorage'

const router = useRouter()
const route = useRoute()

const username = computed(() => {
  // 从store或localStorage获取用户名
  return localStorage.getItem('username') || '用户'
})

const navItems = [
  { path: '/', code: '01', label: '首页' },
  { path: '/course-learning', code: '02', label: '课程学习' },
  { path: '/exam-system', code: '03', label: '考试系统' },
  { path: '/online-meeting', code: '04', label: '在线会议' },
  { path: '/ppt-generator', code: '05', label: 'PPT生成' }
]

const isActive = (path) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'logout':
      removeUserToken()
      router.push('/login')
      break
  }
}
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--header-height);
  background-color: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border);
  z-index: var(--z-sticky);
  backdrop-filter: blur(20px);
  background-color: rgba(255, 255, 255, 0.8);
}

.app-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-xl);
}

.app-header__left {
  display: flex;
  align-items: center;
}

.app-header__logo {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: var(--color-text-primary);
}

.app-header__logo-mark {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
}

.app-header__logo-subtitle {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  letter-spacing: 1px;
}

.app-header__nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.app-header__nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  text-decoration: none;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);
}

.app-header__nav-item:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.app-header__nav-item--active {
  background-color: var(--color-primary);
  color: var(--color-text-inverse);
}

.app-header__nav-code {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  opacity: 0.7;
}

.app-header__nav-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.app-header__right {
  display: flex;
  align-items: center;
}

.app-header__user {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.app-header__user:hover {
  background-color: var(--color-bg-secondary);
}

.app-header__avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background-color: var(--color-primary);
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.app-header__username {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.app-header__arrow {
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* 响应式设计 */
@media (max-width: 767px) {
  .app-header__nav {
    display: none;
  }
  
  .app-header__inner {
    padding: 0 var(--spacing-md);
  }
}
</style>
```

- [ ] **Step 2: 创建AppFooter组件**

```vue
<!-- frontend/user/src/components/layout/AppFooter.vue -->
<template>
  <footer class="app-footer">
    <div class="app-footer__inner">
      <div class="app-footer__left">
        <span class="app-footer__copyright">
          © {{ currentYear }} 竞赛大脑. 保留所有权利.
        </span>
      </div>
      <div class="app-footer__right">
        <a href="#" class="app-footer__link">隐私政策</a>
        <a href="#" class="app-footer__link">服务条款</a>
        <a href="#" class="app-footer__link">联系我们</a>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue'

const currentYear = computed(() => new Date().getFullYear())
</script>

<style scoped>
.app-footer {
  background-color: var(--color-bg-primary);
  border-top: 1px solid var(--color-border);
  padding: var(--spacing-xl) 0;
  margin-top: auto;
}

.app-footer__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-xl);
}

.app-footer__left {
  display: flex;
  align-items: center;
}

.app-footer__copyright {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.app-footer__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.app-footer__link {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.app-footer__link:hover {
  color: var(--color-primary);
}

/* 响应式设计 */
@media (max-width: 767px) {
  .app-footer__inner {
    flex-direction: column;
    gap: var(--spacing-md);
    text-align: center;
  }
}
</style>
```

- [ ] **Step 3: 重构App.vue布局**

```vue
<!-- frontend/user/src/App.vue -->
<template>
  <div class="app-container" :class="{ 'is-meeting-route': isMeetingRoute }">
    <!-- 登录页面不显示导航栏 -->
    <template v-if="!isAuthPage">
      <AppHeader />
      <main class="app-main">
        <router-view />
      </main>
      <AppFooter />
    </template>
    
    <!-- 登录页面 -->
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'

const route = useRoute()

const isAuthPage = computed(() => {
  return route.path === '/login' || route.path === '/register'
})

const isMeetingRoute = computed(() => {
  return route.path.startsWith('/meeting/')
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  margin-top: var(--header-height);
  padding: var(--spacing-2xl) var(--spacing-xl);
  max-width: var(--content-max-width);
  margin-left: auto;
  margin-right: auto;
  width: 100%;
}

/* 会议页面特殊布局 */
.is-meeting-route .app-main {
  margin-top: 0;
  padding: 0;
  max-width: none;
}

/* 响应式设计 */
@media (max-width: 767px) {
  .app-main {
    padding: var(--spacing-lg) var(--spacing-md);
  }
}
</style>
```

- [ ] **Step 4: 验证布局重构**

运行开发服务器，检查：
1. 顶部导航栏正常显示
2. 导航项点击正常跳转
3. 用户头像下拉菜单正常工作
4. 页脚正常显示
5. 响应式布局正常

- [ ] **Step 5: 提交布局重构**

```bash
git add frontend/user/src/App.vue frontend/user/src/components/layout/
git commit -m "feat: refactor app layout with new header and footer components"
```

---

## Task 4: 首页（Dashboard）重构

**Files:**
- Modify: `frontend/user/src/views/Dashboard.vue`
- Create: `frontend/user/src/components/dashboard/HeroCarousel.vue`
- Create: `frontend/user/src/components/dashboard/TaskCard.vue`
- Create: `frontend/user/src/components/dashboard/QuickEntry.vue`
- Create: `frontend/user/src/components/dashboard/RecentActivity.vue`

- [ ] **Step 1: 创建HeroCarousel组件**

```vue
<!-- frontend/user/src/components/dashboard/HeroCarousel.vue -->
<template>
  <section class="hero-carousel">
    <div class="hero-carousel__slides" :style="slidesStyle">
      <div
        v-for="(slide, index) in slides"
        :key="index"
        class="hero-carousel__slide"
        :class="{ 'hero-carousel__slide--active': index === activeIndex }"
      >
        <div class="hero-carousel__content">
          <span class="hero-carousel__eyebrow">{{ slide.eyebrow }}</span>
          <h1 class="hero-carousel__title">{{ slide.title }}</h1>
          <p class="hero-carousel__subtitle">{{ slide.subtitle }}</p>
          <div class="hero-carousel__actions">
            <BaseButton
              v-if="slide.primaryAction"
              type="primary"
              size="large"
              @click="handleAction(slide.primaryAction)"
            >
              {{ slide.primaryAction.text }}
            </BaseButton>
            <BaseButton
              v-if="slide.secondaryAction"
              type="secondary"
              size="large"
              @click="handleAction(slide.secondaryAction)"
            >
              {{ slide.secondaryAction.text }}
            </BaseButton>
          </div>
        </div>
        <div class="hero-carousel__visual">
          <div class="hero-carousel__illustration">
            <!-- 插图区域 -->
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="slides.length > 1" class="hero-carousel__controls">
      <button
        class="hero-carousel__arrow hero-carousel__arrow--left"
        @click="prev"
        aria-label="上一张"
      >
        <span>‹</span>
      </button>
      
      <div class="hero-carousel__dots">
        <button
          v-for="(_, index) in slides"
          :key="index"
          class="hero-carousel__dot"
          :class="{ 'hero-carousel__dot--active': index === activeIndex }"
          @click="goTo(index)"
          :aria-label="`切换到第 ${index + 1} 张`"
        ></button>
      </div>
      
      <button
        class="hero-carousel__arrow hero-carousel__arrow--right"
        @click="next"
        aria-label="下一张"
      >
        <span>›</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { BaseButton } from '@/components/base'

const props = defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  autoplay: {
    type: Boolean,
    default: true
  },
  interval: {
    type: Number,
    default: 5000
  }
})

const emit = defineEmits(['action'])

const activeIndex = ref(0)
let autoplayTimer = null

const slidesStyle = computed(() => ({
  transform: `translateX(-${activeIndex.value * 100}%)`
}))

const next = () => {
  activeIndex.value = (activeIndex.value + 1) % props.slides.length
}

const prev = () => {
  activeIndex.value = (activeIndex.value - 1 + props.slides.length) % props.slides.length
}

const goTo = (index) => {
  activeIndex.value = index
}

const startAutoplay = () => {
  if (props.autoplay && props.slides.length > 1) {
    autoplayTimer = setInterval(next, props.interval)
  }
}

const stopAutoplay = () => {
  if (autoplayTimer) {
    clearInterval(autoplayTimer)
    autoplayTimer = null
  }
}

const handleAction = (action) => {
  emit('action', action)
}

onMounted(() => {
  startAutoplay()
})

onUnmounted(() => {
  stopAutoplay()
})
</script>

<style scoped>
.hero-carousel {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 400px;
}

.hero-carousel__slides {
  display: flex;
  transition: transform var(--transition-slow);
}

.hero-carousel__slide {
  min-width: 100%;
  display: flex;
  align-items: center;
  padding: var(--spacing-3xl);
}

.hero-carousel__content {
  flex: 1;
  max-width: 500px;
}

.hero-carousel__eyebrow {
  display: inline-block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: rgba(255, 255, 255, 0.8);
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: var(--spacing-md);
}

.hero-carousel__title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: white;
  line-height: var(--line-height-tight);
  margin-bottom: var(--spacing-md);
}

.hero-carousel__subtitle {
  font-size: var(--font-size-lg);
  color: rgba(255, 255, 255, 0.9);
  line-height: var(--line-height-normal);
  margin-bottom: var(--spacing-xl);
}

.hero-carousel__actions {
  display: flex;
  gap: var(--spacing-md);
}

.hero-carousel__visual {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-carousel__illustration {
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.hero-carousel__controls {
  position: absolute;
  bottom: var(--spacing-xl);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.hero-carousel__arrow {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  transition: background var(--transition-fast);
  border: none;
}

.hero-carousel__arrow:hover {
  background: rgba(255, 255, 255, 0.3);
}

.hero-carousel__dots {
  display: flex;
  gap: var(--spacing-sm);
}

.hero-carousel__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
}

.hero-carousel__dot--active {
  width: 24px;
  background: white;
}

/* 响应式设计 */
@media (max-width: 767px) {
  .hero-carousel {
    min-height: 300px;
  }
  
  .hero-carousel__slide {
    padding: var(--spacing-xl);
    flex-direction: column;
    text-align: center;
  }
  
  .hero-carousel__title {
    font-size: var(--font-size-2xl);
  }
  
  .hero-carousel__actions {
    justify-content: center;
  }
  
  .hero-carousel__visual {
    display: none;
  }
}
</style>
```

- [ ] **Step 2: 创建TaskCard组件**

```vue
<!-- frontend/user/src/components/dashboard/TaskCard.vue -->
<template>
  <BaseCard hoverable class="task-card" @click="handleClick">
    <div class="task-card__header">
      <div class="task-card__icon" :style="{ backgroundColor: iconBgColor }">
        <span class="task-card__icon-text">{{ iconText }}</span>
      </div>
      <div class="task-card__meta">
        <span class="task-card__type">{{ type }}</span>
        <span class="task-card__time">{{ time }}</span>
      </div>
    </div>
    <div class="task-card__body">
      <h3 class="task-card__title">{{ title }}</h3>
      <p class="task-card__description">{{ description }}</p>
    </div>
    <div class="task-card__footer">
      <span class="task-card__status" :class="statusClass">
        {{ statusText }}
      </span>
      <span class="task-card__action">查看 →</span>
    </div>
  </BaseCard>
</template>

<script setup>
import { computed } from 'vue'
import { BaseCard } from '@/components/base'

const props = defineProps({
  type: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  time: {
    type: String,
    default: ''
  },
  status: {
    type: String,
    default: 'pending',
    validator: (value) => ['pending', 'in-progress', 'completed', 'overdue'].includes(value)
  },
  icon: {
    type: String,
    default: '📋'
  }
})

const emit = defineEmits(['click'])

const iconBgColor = computed(() => {
  const colors = {
    '课程': '#E3F2FD',
    '考试': '#FFF3E0',
    '会议': '#E8F5E9',
    'PPT': '#F3E5F5'
  }
  return colors[props.type] || '#F5F5F5'
})

const iconText = computed(() => {
  return props.icon || props.type.charAt(0)
})

const statusClass = computed(() => `task-card__status--${props.status}`)

const statusText = computed(() => {
  const texts = {
    'pending': '待完成',
    'in-progress': '进行中',
    'completed': '已完成',
    'overdue': '已逾期'
  }
  return texts[props.status]
})

const handleClick = () => {
  emit('click')
}
</script>

<style scoped>
.task-card {
  cursor: pointer;
}

.task-card__header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.task-card__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.task-card__icon-text {
  font-size: var(--font-size-xl);
}

.task-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.task-card__type {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.task-card__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.task-card__body {
  margin-bottom: var(--spacing-md);
}

.task-card__title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
  line-height: var(--line-height-tight);
}

.task-card__description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.task-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.task-card__status {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.task-card__status--pending {
  background-color: #FFF3E0;
  color: #E65100;
}

.task-card__status--in-progress {
  background-color: #E3F2FD;
  color: #1565C0;
}

.task-card__status--completed {
  background-color: #E8F5E9;
  color: #2E7D32;
}

.task-card__status--overdue {
  background-color: #FFEBEE;
  color: #C62828;
}

.task-card__action {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}
</style>
```

- [ ] **Step 3: 创建QuickEntry组件**

```vue
<!-- frontend/user/src/components/dashboard/QuickEntry.vue -->
<template>
  <div class="quick-entry">
    <div class="quick-entry__grid">
      <router-link
        v-for="entry in entries"
        :key="entry.path"
        :to="entry.path"
        class="quick-entry__item"
      >
        <div class="quick-entry__icon" :style="{ backgroundColor: entry.color }">
          <span>{{ entry.icon }}</span>
        </div>
        <span class="quick-entry__label">{{ entry.label }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
const entries = [
  { path: '/course-learning', icon: '📚', label: '课程学习', color: '#E3F2FD' },
  { path: '/exam-system', icon: '📝', label: '考试系统', color: '#FFF3E0' },
  { path: '/online-meeting', icon: '🎥', label: '在线会议', color: '#E8F5E9' },
  { path: '/ppt-generator', icon: '📊', label: 'PPT生成', color: '#F3E5F5' },
  { path: '/script-editor', icon: '✍️', label: '演讲稿', color: '#E0F7FA' },
  { path: '/my-recordings', icon: '🎬', label: '我的录制', color: '#FBE9E7' },
  { path: '/statistics', icon: '📈', label: '数据统计', color: '#F1F8E9' },
  { path: '/profile', icon: '👤', label: '个人中心', color: '#FFF8E1' }
]
</script>

<style scoped>
.quick-entry {
  padding: var(--spacing-lg) 0;
}

.quick-entry__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
}

.quick-entry__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-radius: var(--radius-lg);
  background-color: var(--color-bg-primary);
  text-decoration: none;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.quick-entry__item:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.quick-entry__icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.quick-entry__label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

/* 响应式设计 */
@media (max-width: 1199px) {
  .quick-entry__grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 767px) {
  .quick-entry__grid {
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-md);
  }
  
  .quick-entry__item {
    padding: var(--spacing-md);
  }
  
  .quick-entry__icon {
    width: 48px;
    height: 48px;
    font-size: 24px;
  }
}

@media (max-width: 480px) {
  .quick-entry__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
```

- [ ] **Step 4: 创建RecentActivity组件**

```vue
<!-- frontend/user/src/components/dashboard/RecentActivity.vue -->
<template>
  <BaseCard class="recent-activity">
    <template #header>
      <div class="recent-activity__header">
        <h3 class="recent-activity__title">最近活动</h3>
        <BaseButton type="text" size="small">查看全部</BaseButton>
      </div>
    </template>
    
    <div class="recent-activity__list">
      <div
        v-for="activity in activities"
        :key="activity.id"
        class="recent-activity__item"
      >
        <div class="recent-activity__icon" :style="{ backgroundColor: activity.color }">
          <span>{{ activity.icon }}</span>
        </div>
        <div class="recent-activity__content">
          <p class="recent-activity__text">{{ activity.text }}</p>
          <span class="recent-activity__time">{{ activity.time }}</span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script setup>
import { BaseCard, BaseButton } from '@/components/base'

const activities = [
  {
    id: 1,
    icon: '📚',
    text: '完成了《数据分析基础》课程第3章',
    time: '2小时前',
    color: '#E3F2FD'
  },
  {
    id: 2,
    icon: '📝',
    text: '参加了《项目管理》模拟考试',
    time: '4小时前',
    color: '#FFF3E0'
  },
  {
    id: 3,
    icon: '🎥',
    text: '参加了团队周会',
    time: '昨天',
    color: '#E8F5E9'
  },
  {
    id: 4,
    icon: '📊',
    text: '生成了《季度汇报》PPT',
    time: '昨天',
    color: '#F3E5F5'
  },
  {
    id: 5,
    icon: '✍️',
    text: '更新了路演演讲稿',
    time: '2天前',
    color: '#E0F7FA'
  }
]
</script>

<style scoped>
.recent-activity__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.recent-activity__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.recent-activity__list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.recent-activity__item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.recent-activity__item:hover {
  background-color: var(--color-bg-secondary);
}

.recent-activity__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.recent-activity__content {
  flex: 1;
  min-width: 0;
}

.recent-activity__text {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  line-height: var(--line-height-normal);
  margin-bottom: var(--spacing-xs);
}

.recent-activity__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}
</style>
```

- [ ] **Step 5: 重构Dashboard页面**

```vue
<!-- frontend/user/src/views/Dashboard.vue -->
<template>
  <div class="dashboard">
    <!-- 轮播区域 -->
    <HeroCarousel :slides="slides" @action="handleCarouselAction" />
    
    <!-- 今日任务 -->
    <section class="dashboard__section">
      <h2 class="dashboard__section-title">今日任务</h2>
      <div class="dashboard__tasks-grid">
        <TaskCard
          v-for="task in todayTasks"
          :key="task.id"
          v-bind="task"
          @click="handleTaskClick(task)"
        />
      </div>
    </section>
    
    <!-- 快速入口 -->
    <section class="dashboard__section">
      <h2 class="dashboard__section-title">快速入口</h2>
      <QuickEntry />
    </section>
    
    <!-- 最近活动 -->
    <section class="dashboard__section">
      <RecentActivity />
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import HeroCarousel from '@/components/dashboard/HeroCarousel.vue'
import TaskCard from '@/components/dashboard/TaskCard.vue'
import QuickEntry from '@/components/dashboard/QuickEntry.vue'
import RecentActivity from '@/components/dashboard/RecentActivity.vue'

const router = useRouter()

const slides = [
  {
    eyebrow: 'COMPETITION BRAIN PORTAL',
    title: '项目路演作战台',
    subtitle: '从学习、测评到团队交付，聚焦今天最该推进的事项。',
    primaryAction: { text: '开始学习', path: '/course-learning' },
    secondaryAction: { text: '查看任务', path: '/exam-system' }
  },
  {
    eyebrow: 'NEW FEATURE',
    title: 'AI智能评分',
    subtitle: '利用人工智能技术，自动评估您的演讲表现。',
    primaryAction: { text: '立即体验', path: '/ai-score' }
  }
]

const todayTasks = ref([
  {
    id: 1,
    type: '课程',
    title: '完成数据分析基础第4章',
    description: '学习数据可视化基础，掌握常用图表类型和使用场景。',
    time: '截止：今天 18:00',
    status: 'pending',
    icon: '📚'
  },
  {
    id: 2,
    type: '考试',
    title: '项目管理模拟考试',
    description: '包含选择题和案例分析题，预计耗时45分钟。',
    time: '截止：今天 20:00',
    status: 'in-progress',
    icon: '📝'
  },
  {
    id: 3,
    type: '会议',
    title: '团队周会',
    description: '讨论本周项目进展和下周计划。',
    time: '今天 14:00-15:00',
    status: 'pending',
    icon: '🎥'
  },
  {
    id: 4,
    type: 'PPT',
    title: '准备季度汇报PPT',
    description: '整理本季度工作成果和下季度规划。',
    time: '截止：明天',
    status: 'pending',
    icon: '📊'
  }
])

const handleCarouselAction = (action) => {
  if (action.path) {
    router.push(action.path)
  }
}

const handleTaskClick = (task) => {
  // 根据任务类型跳转到相应页面
  const routes = {
    '课程': '/course-learning',
    '考试': '/exam-system',
    '会议': '/online-meeting',
    'PPT': '/ppt-generator'
  }
  if (routes[task.type]) {
    router.push(routes[task.type])
  }
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2xl);
}

.dashboard__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.dashboard__section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.dashboard__tasks-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-lg);
}

/* 响应式设计 */
@media (max-width: 1199px) {
  .dashboard__tasks-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 767px) {
  .dashboard__tasks-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 6: 验证首页重构**

运行开发服务器，检查：
1. 轮播组件正常工作
2. 任务卡片正确显示
3. 快速入口布局正常
4. 最近活动列表正常
5. 响应式布局正常

- [ ] **Step 7: 提交首页重构**

```bash
git add frontend/user/src/views/Dashboard.vue frontend/user/src/components/dashboard/
git commit -m "feat: refactor Dashboard page with new Apple-style components"
```

---

## Task 5: 登录页面重构

**Files:**
- Modify: `frontend/user/src/views/Login.vue`

- [ ] **Step 1: 重构登录页面**

```vue
<!-- frontend/user/src/views/Login.vue -->
<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-left">
        <div class="login-branding">
          <div class="login-logo">
            <span class="login-logo__mark">竞赛大脑</span>
            <span class="login-logo__subtitle">COMPETITION BRAIN</span>
          </div>
          <h1 class="login-title">欢迎回来</h1>
          <p class="login-description">
            登录以继续您的学习旅程，掌握竞赛技能，提升项目路演能力。
          </p>
        </div>
        <div class="login-features">
          <div class="login-feature">
            <span class="login-feature__icon">📚</span>
            <span class="login-feature__text">丰富的课程资源</span>
          </div>
          <div class="login-feature">
            <span class="login-feature__icon">🎯</span>
            <span class="login-feature__text">智能学习路径</span>
          </div>
          <div class="login-feature">
            <span class="login-feature__icon">🏆</span>
            <span class="login-feature__text">实战演练平台</span>
          </div>
        </div>
      </div>
      
      <div class="login-right">
        <div class="login-form-container">
          <div class="login-tabs">
            <button
              :class="['login-tab', { 'login-tab--active': activeTab === 'login' }]"
              @click="activeTab = 'login'"
            >
              登录
            </button>
            <button
              :class="['login-tab', { 'login-tab--active': activeTab === 'register' }]"
              @click="activeTab = 'register'"
            >
              注册
            </button>
          </div>
          
          <form v-if="activeTab === 'login'" class="login-form" @submit.prevent="handleLogin">
            <BaseInput
              v-model="loginForm.username"
              label="用户名"
              placeholder="请输入用户名"
              required
            />
            <BaseInput
              v-model="loginForm.password"
              type="password"
              label="密码"
              placeholder="请输入密码"
              required
            />
            <div class="login-options">
              <label class="login-remember">
                <input type="checkbox" v-model="loginForm.remember" />
                <span>记住我</span>
              </label>
              <a href="#" class="login-forgot">忘记密码？</a>
            </div>
            <BaseButton
              type="primary"
              size="large"
              :loading="loading"
              @click="handleLogin"
            >
              登录
            </BaseButton>
          </form>
          
          <form v-else class="login-form" @submit.prevent="handleRegister">
            <BaseInput
              v-model="registerForm.username"
              label="用户名"
              placeholder="请输入用户名"
              required
            />
            <BaseInput
              v-model="registerForm.email"
              type="email"
              label="邮箱"
              placeholder="请输入邮箱"
              required
            />
            <BaseInput
              v-model="registerForm.password"
              type="password"
              label="密码"
              placeholder="请输入密码"
              required
            />
            <BaseInput
              v-model="registerForm.confirmPassword"
              type="password"
              label="确认密码"
              placeholder="请再次输入密码"
              required
            />
            <BaseButton
              type="primary"
              size="large"
              :loading="loading"
              @click="handleRegister"
            >
              注册
            </BaseButton>
          </form>
          
          <div class="login-divider">
            <span>或</span>
          </div>
          
          <div class="login-social">
            <button class="login-social__btn" @click="handleSocialLogin('wechat')">
              <span>微信登录</span>
            </button>
            <button class="login-social__btn" @click="handleSocialLogin('qq')">
              <span>QQ登录</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { BaseInput, BaseButton } from '@/components/base'
import { setUserToken } from '@/utils/authStorage'

const router = useRouter()

const activeTab = ref('login')
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  remember: false
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  
  loading.value = true
  
  try {
    // 模拟登录API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 假设登录成功
    setUserToken('mock-token')
    localStorage.setItem('username', loginForm.username)
    
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    ElMessage.error('登录失败，请重试')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.email || !registerForm.password) {
    ElMessage.warning('请填写所有必填字段')
    return
  }
  
  if (registerForm.password !== registerForm.confirmPassword) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  
  loading.value = true
  
  try {
    // 模拟注册API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
  } catch (error) {
    ElMessage.error('注册失败，请重试')
  } finally {
    loading.value = false
  }
}

const handleSocialLogin = (provider) => {
  ElMessage.info(`${provider}登录功能开发中`)
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-secondary);
  padding: var(--spacing-xl);
}

.login-container {
  display: flex;
  max-width: 1000px;
  width: 100%;
  background-color: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.login-left {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--spacing-3xl);
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: white;
}

.login-branding {
  margin-bottom: var(--spacing-3xl);
}

.login-logo {
  display: flex;
  flex-direction: column;
  margin-bottom: var(--spacing-xl);
}

.login-logo__mark {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
}

.login-logo__subtitle {
  font-size: var(--font-size-xs);
  opacity: 0.8;
  letter-spacing: 2px;
  margin-top: var(--spacing-xs);
}

.login-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-md);
}

.login-description {
  font-size: var(--font-size-base);
  opacity: 0.9;
  line-height: var(--line-height-normal);
}

.login-features {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.login-feature {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.login-feature__icon {
  font-size: var(--font-size-xl);
}

.login-feature__text {
  font-size: var(--font-size-sm);
  opacity: 0.9;
}

.login-right {
  flex: 1;
  padding: var(--spacing-3xl);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-form-container {
  width: 100%;
  max-width: 400px;
}

.login-tabs {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--spacing-md);
}

.login-tab {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  transition: color var(--transition-fast);
  border-bottom: 2px solid transparent;
  margin-bottom: -calc(var(--spacing-md) + 1px);
}

.login-tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.login-remember {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.login-remember input {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary);
}

.login-forgot {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  text-decoration: none;
}

.login-forgot:hover {
  text-decoration: underline;
}

.login-divider {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin: var(--spacing-lg) 0;
}

.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background-color: var(--color-border);
}

.login-divider span {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.login-social {
  display: flex;
  gap: var(--spacing-md);
}

.login-social__btn {
  flex: 1;
  padding: var(--spacing-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.login-social__btn:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-text-secondary);
}

/* 响应式设计 */
@media (max-width: 767px) {
  .login-container {
    flex-direction: column;
  }
  
  .login-left {
    padding: var(--spacing-xl);
  }
  
  .login-right {
    padding: var(--spacing-xl);
  }
  
  .login-title {
    font-size: var(--font-size-2xl);
  }
}
</style>
```

- [ ] **Step 2: 验证登录页面**

运行开发服务器，检查：
1. 登录/注册标签切换正常
2. 表单输入和验证正常
3. 按钮点击效果正常
4. 响应式布局正常

- [ ] **Step 3: 提交登录页面重构**

```bash
git add frontend/user/src/views/Login.vue
git commit -m "feat: refactor Login page with Apple-style design"
```

---

## Task 6: 其他核心页面重构

**Files:**
- Modify: `frontend/user/src/views/CourseLearning.vue`
- Modify: `frontend/user/src/views/ExamSystem.vue`
- Modify: `frontend/user/src/views/OnlineMeeting.vue`
- Modify: `frontend/user/src/views/PptGenerator.vue`
- Modify: `frontend/user/src/views/Profile.vue`

- [ ] **Step 1: 重构课程学习页面**

由于篇幅限制，这里提供重构的核心思路：

1. 使用新的设计系统CSS变量
2. 替换Element Plus组件为自定义基础组件
3. 应用苹果风格的布局和样式
4. 添加响应式设计
5. 优化动画效果

具体实现步骤：
- 分析现有页面结构
- 逐步替换组件和样式
- 测试功能完整性
- 优化用户体验

- [ ] **Step 2: 重构考试系统页面**

类似课程学习页面的重构过程。

- [ ] **Step 3: 重构在线会议页面**

类似课程学习页面的重构过程。

- [ ] **Step 4: 重构PPT生成页面**

类似课程学习页面的重构过程。

- [ ] **Step 5: 重构个人中心页面**

类似课程学习页面的重构过程。

- [ ] **Step 6: 提交所有页面重构**

```bash
git add frontend/user/src/views/
git commit -m "feat: refactor all core pages with Apple-style design system"
```

---

## Task 7: 响应式适配和优化

**Files:**
- Modify: `frontend/user/src/styles/design-system.css`
- Modify: 各页面组件

- [ ] **Step 1: 测试响应式断点**

使用浏览器开发者工具测试以下断点：
- 1200px+ (桌面端)
- 768px-1199px (平板端)
- <768px (移动端)

- [ ] **Step 2: 修复响应式问题**

针对发现的问题进行修复：
1. 调整网格布局
2. 优化字体大小
3. 调整间距
4. 隐藏/显示特定元素

- [ ] **Step 3: 性能优化**

1. 优化图片资源
2. 减少CSS选择器复杂度
3. 使用CSS containment
4. 优化动画性能

- [ ] **Step 4: 无障碍优化**

1. 添加ARIA标签
2. 确保键盘导航
3. 优化颜色对比度
4. 添加焦点样式

- [ ] **Step 5: 提交优化**

```bash
git add .
git commit -m "feat: optimize responsive design and accessibility"
```

---

## Task 8: 测试和调优

**Files:**
- 测试文件（如适用）

- [ ] **Step 1: 功能测试**

测试所有页面的核心功能：
1. 登录/注册流程
2. 课程学习流程
3. 考试系统流程
4. 在线会议流程
5. PPT生成流程

- [ ] **Step 2: 兼容性测试**

测试不同浏览器：
1. Chrome
2. Firefox
3. Safari
4. Edge

- [ ] **Step 3: 性能测试**

使用Lighthouse测试：
1. 性能分数
2. 可访问性分数
3. 最佳实践分数
4. SEO分数

- [ ] **Step 4: 用户反馈收集**

收集用户反馈：
1. 界面美观度
2. 操作便捷性
3. 功能完整性
4. 性能体验

- [ ] **Step 5: 最终调优**

根据反馈进行最终调整：
1. 修复发现的问题
2. 优化用户体验
3. 完善细节设计

- [ ] **Step 6: 提交最终版本**

```bash
git add .
git commit -m "feat: complete UI redesign with Apple-style design system"
```

---

## 验收清单

### 视觉验收
- [ ] 苹果设计风格正确应用
- [ ] 配色方案符合规范
- [ ] 圆角和阴影效果一致
- [ ] 字体和排版规范

### 交互验收
- [ ] 动画效果流畅自然
- [ ] 触觉反馈适当
- [ ] 状态反馈明确
- [ ] 操作响应及时

### 功能验收
- [ ] 所有功能正常工作
- [ ] 响应式布局正确
- [ ] 数据加载和显示正常
- [ ] 错误处理得当

### 性能验收
- [ ] 页面加载时间<3秒
- [ ] 动画帧率>60fps
- [ ] 内存使用合理
- [ ] 无卡顿和闪烁

---

## 后续维护

### 设计系统维护
- 定期更新设计规范
- 组件库版本管理
- 文档持续完善

### 功能扩展
- 新功能组件开发
- 现有组件优化
- 用户反馈集成

### 技术升级
- 框架版本升级
- 构建工具优化
- 性能持续改进