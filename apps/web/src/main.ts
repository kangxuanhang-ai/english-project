import '@/assets/base.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import focusPlugin from './directives/focus'
const app = createApp(App) // 创建 App 实例
const pinia = createPinia() // 创建 Pinia 实例
pinia.use(piniaPluginPersistedstate) // 使用 Pinia 持久化状态
app.use(pinia) // 使用 Pinia
app.use(ElementPlus, { locale: zhCn }) // 使用 ElementPlus
app.use(router) // 使用 Router
app.use(focusPlugin) // 使用 focus 指令
app.mount('#app')
