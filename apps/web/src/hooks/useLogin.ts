import { isShowLogin } from '@/components/Login/loginState'
import { useUserStore } from '@/stores/user'
import { useChatStore } from '@/stores/chat'
import router from '@/router'

export const useLogin = () => {
    const userStore = useUserStore()
    const chatStore = useChatStore()

    /** 已登录返回 true；未登录则弹出登录框并返回 false（非异常） */
    const login = (): Promise<boolean> => {
        if (userStore.getUser) {
            return Promise.resolve(true)
        }
        isShowLogin.value = true
        return Promise.resolve(false)
    }

    const logout = () => {
        chatStore.activeRole = 'normal'
        chatStore.activeConversationId = null
        chatStore.conversations = []
        userStore.logout()
        router.push('/')
    }

    const hide = () => {
        isShowLogin.value = false
    }

    return {
        login,
        hide,
        logout,
    }
}
