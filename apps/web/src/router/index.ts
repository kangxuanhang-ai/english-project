import { createRouter, createWebHistory } from 'vue-router'
import home from './home/index'
import wordBook from './word-book/index'
import setting from './setting/index'
import chat from './chat/index'
import course from './course/index'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...home, //主页
    ...wordBook, //词库
    ...setting, //设置
    ...chat, //聊天
    ...course, //课程
  ]
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth) {
    const userStore = useUserStore()
    if (!userStore.getAccessToken) {
      return { path: '/' }
    }
  }
})

export default router
