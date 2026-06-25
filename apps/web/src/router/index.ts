import { createRouter, createWebHistory } from 'vue-router'
import home from './home/index'
import wordBook from './word-book/index'
import setting from './setting/index'
import chat from './chat/index'
import course from './course/index'
import { useUserStore } from '@/stores/user'
import { ensureValidToken } from '@/apis/auth'
import { isShowLogin } from '@/components/Login/loginState'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...home,
    ...wordBook,
    ...setting,
    ...chat,
    ...course,
  ]
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) {
    return true
  }

  const userStore = useUserStore()
  if (!userStore.getAccessToken) {
    isShowLogin.value = true
    return false
  }

  const token = await ensureValidToken()
  if (!token) {
    userStore.logout()
    isShowLogin.value = true
    return false
  }

  return true
})

export default router
