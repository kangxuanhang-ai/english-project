import { uploadUrl } from '@/apis' //头像地址的前缀
import defaultAvatar from '@/assets/images/avatar/default-avatar.png' //默认头像
import { useUserStore } from '@/stores/user' //用户信息
import { computed } from 'vue'
export const useAvatar = () => {
    const userStore = useUserStore() //初始化pinia
    const avatar = computed(() => {
        if(userStore.getUser?.avatar) {
            return uploadUrl + userStore.getUser.avatar
        }
        else {
            return defaultAvatar
        }
    })
    const customAvatar = (avatar: string) => {
        if(avatar) {
            return uploadUrl + avatar
        }
        else {
            return defaultAvatar
        }
    }
    return {
        avatar,
        customAvatar
    }
}