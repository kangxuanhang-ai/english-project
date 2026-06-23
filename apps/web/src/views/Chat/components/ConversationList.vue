<template>
    <div class="w-[268px] flex flex-col border-r border-gray-200 shrink-0 bg-[#fefefe]">
        <div class="flex items-center justify-between px-4 pt-5 pb-3">
            <span class="text-[13px] font-bold text-gray-500">对话</span>
            <button
                type="button"
                class="w-[30px] h-[30px] rounded-[10px] text-white text-lg leading-none flex items-center justify-center hover:opacity-90 transition-opacity"
                style="background: linear-gradient(135deg, var(--chat-accent-light), var(--chat-accent)); box-shadow: 0 2px 8px var(--chat-glow)"
                @click="handleCreate"
            >+</button>
        </div>

        <div class="flex-1 overflow-y-auto px-3">
            <div
                v-for="conv in chatStore.conversations"
                :key="conv.id"
                @click="handleSelect(conv.id)"
                class="group rounded-lg py-2.5 px-3 cursor-pointer transition-all duration-200 mb-0.5 border flex items-center gap-2"
                :class="chatStore.activeConversationId === conv.id ? '' : 'border-transparent hover:bg-stone-50/80'"
                :style="chatStore.activeConversationId === conv.id
                    ? { background: 'var(--chat-accent-soft)', borderColor: 'var(--chat-accent-border)' }
                    : {}"
            >
                <span
                    v-if="chatStore.activeConversationId === conv.id"
                    class="w-1.5 h-1.5 rounded-full shrink-0 shadow-[0_0_6px_var(--chat-glow)]"
                    style="background: var(--chat-accent)"
                />
                <div class="text-[13px] text-gray-700 truncate flex-1">{{ conv.title }}</div>
                <button
                    type="button"
                    class="w-6 h-6 rounded-md bg-red-50 text-red-500 text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center shrink-0 hover:bg-red-100"
                    @click.stop="handleDelete(conv.id)"
                >
                    <el-icon><Delete /></el-icon>
                </button>
            </div>

            <div
                v-if="chatStore.conversations.length === 0"
                class="flex flex-col items-center justify-center gap-2 text-gray-400 mt-16 px-4 text-center"
            >
                <div class="w-12 h-12 rounded-2xl bg-stone-50 border border-stone-100 flex items-center justify-center text-xl mb-1">💬</div>
                <div class="text-[13px] font-medium text-stone-500">暂无对话</div>
                <div class="text-[11px] text-stone-400">点击上方 + 开始新对话</div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'

const chatStore = useChatStore()
const router = useRouter()

const handleCreate = async () => {
    try {
        const id = await chatStore.createConversation(chatStore.activeRole)
        router.replace(`/chat/${chatStore.activeRole}/${id}`)
    } catch (error) {
        ElMessage.error('创建对话失败')
    }
}

const handleSelect = (id: string) => {
    chatStore.setConversation(id)
    router.replace(`/chat/${chatStore.activeRole}/${id}`)
}

const handleDelete = async (id: string) => {
    try {
        await ElMessageBox.confirm('确定删除这个对话吗？', '提示', {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
        })
    } catch {
        return
    }
    try {
        await chatStore.deleteConversation(id)
        if (chatStore.activeConversationId) {
            router.replace(`/chat/${chatStore.activeRole}/${chatStore.activeConversationId}`)
        } else {
            router.replace(`/chat/${chatStore.activeRole}`)
        }
    } catch (error) {
        ElMessage.error('删除对话失败')
    }
}
</script>
