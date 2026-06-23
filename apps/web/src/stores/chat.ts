import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import type { ChatRoleType, Conversation } from '@en/common/chat'
import {
    getConversations,
    createConversation as createConversationApi,
    deleteConversationApi,
} from '@/apis/chat'

export const useChatStore = defineStore('chat', () => {
    const activeRole = ref<ChatRoleType>('normal')
    const activeConversationId = ref<string | null>(null)
    const conversations = ref<Conversation[]>([])

    const activeConversation = computed(() =>
        conversations.value.find(c => c.id === activeConversationId.value)
    )

    /** 切换角色：拉取对话列表，默认选中第一条 */
    async function setRole(role: ChatRoleType) {
        activeRole.value = role
        activeConversationId.value = null
        try {
            const res = await getConversations(role)
            conversations.value = res.data
            if (res.data.length > 0) {
                activeConversationId.value = res.data[0].id
            }
        } catch {
            conversations.value = []
            ElMessage.error('加载对话列表失败')
        }
    }

    /** 切换对话 */
    function setConversation(id: string) {
        activeConversationId.value = id
    }

    /** 新建对话：创建并设为 active */
    async function createConversation(role: ChatRoleType): Promise<string> {
        try {
            const res = await createConversationApi(role)
            const conv = res.data
            conversations.value.unshift(conv)
            activeConversationId.value = conv.id
            return conv.id
        } catch (e) {
            ElMessage.error('创建对话失败')
            throw e
        }
    }

    /** 删除对话：自动切到下一条 */
    async function deleteConversation(id: string) {
        try {
            await deleteConversationApi(id)
            const idx = conversations.value.findIndex(c => c.id === id)
            conversations.value = conversations.value.filter(c => c.id !== id)

            // 如果删的是当前对话，切到最近一条
            if (activeConversationId.value === id) {
                if (conversations.value.length > 0) {
                    const newIdx = Math.min(idx, conversations.value.length - 1)
                    activeConversationId.value = conversations.value[newIdx].id
                } else {
                    activeConversationId.value = null
                }
            }
        } catch (e) {
            ElMessage.error('删除对话失败')
            throw e
        }
    }

    /** 更新对话标题 */
    function updateTitle(id: string, title: string) {
        const conv = conversations.value.find(c => c.id === id)
        if (conv) {
            conv.title = title
        }
    }

    return {
        activeRole,
        activeConversationId,
        conversations,
        activeConversation,
        setRole,
        setConversation,
        createConversation,
        deleteConversation,
        updateTitle,
    }
})
