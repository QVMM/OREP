import { createApp, h } from 'vue'
import { createPinia } from 'pinia'
import { ElConfigProvider } from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import router from './router'
import { initFrontendMonitor } from './utils/monitor'
import './styles/design-system.css'
import './theme.css'
import './styles/apple-tokens.css'
import './styles/workspace-tokens.css'
import './styles/apple-components.css'
import './styles/workspace-components.css'
import './styles/ai-score-report-layout.css'
import './styles/ai-app-shell.css'
import './styles/student-flow.css'
import './orep-feedback.css'
import './mobile.css'
import './styles/control-primitives.css'

if (typeof navigator !== 'undefined' && /Windows/i.test(navigator.userAgent)) {
  document.documentElement.classList.add('is-windows')
}

const Root = {
  render: () => h(ElConfigProvider, { locale: zhCn }, () => h(App))
}

const app = createApp(Root)
const pinia = createPinia()

app.use(pinia)
app.use(router)

app.mount('#app')

initFrontendMonitor(router, 'user_frontend')
