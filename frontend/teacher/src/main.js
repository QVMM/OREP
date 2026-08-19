import { createApp, h } from 'vue'
import { createPinia } from 'pinia'
import { ElConfigProvider } from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import router from './router'
import '@user-styles/workspace-tokens.css'
import '@user-styles/workspace-components.css'
import '@user-styles/control-primitives.css'
import './styles/teacher.css'

const Root = {
  render: () => h(ElConfigProvider, { locale: zhCn }, () => h(App)),
}

const app = createApp(Root)
app.use(createPinia())
app.use(router)
app.mount('#app')
