<template>
    <div
        class="w-[208px] flex flex-col border-r border-gray-200 shrink-0"
        style="background: linear-gradient(180deg, #fafaff, #f5f4ff)"
    >
        <div class="px-4 pt-5 pb-3">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wide">角色</h3>
        </div>
        <div class="flex-1 overflow-y-auto px-3">
            <div
                v-for="mode in chatModes"
                :key="mode.id"
                @click="handleClick(mode)"
                class="flex items-center gap-2.5 rounded-lg py-2.5 px-2 cursor-pointer transition-all duration-200 mb-0.5 border border-l-[3px]"
                :class="chatStore.activeRole === mode.role
                    ? 'shadow-[0_0_0_1px_var(--chat-glow)]'
                    : 'border-transparent hover:bg-white/60'"
                :style="chatStore.activeRole === mode.role
                    ? { background: 'var(--chat-accent-soft)', borderColor: 'var(--chat-accent-border)', borderLeftColor: 'var(--chat-accent)' }
                    : { borderLeftColor: 'transparent' }"
            >
                <div
                    class="w-[38px] h-[38px] rounded-xl flex items-center justify-center text-lg shrink-0"
                    :style="{ background: roleConfig[mode.role]?.theme.iconBg ?? 'var(--chat-icon-bg)' }"
                >{{ roleConfig[mode.role]?.icon ?? '💬' }}</div>
                <div class="min-w-0">
                    <div class="text-[13px] font-semibold text-gray-800 leading-snug">{{ roleConfig[mode.role]?.label ?? stripEmoji(mode.label) }}</div>
                    <div class="text-[11px] text-gray-400 leading-snug mt-px truncate">{{ roleConfig[mode.role]?.desc ?? '' }}</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { ChatModeList, ChatMode } from '@en/common/chat'
import { getChatMode } from '@/apis/chat'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'
import { roleConfig } from '../roleConfig'

const chatStore = useChatStore()
const router = useRouter()
const chatModes = ref<ChatModeList>([])

function stripEmoji(label: string) {
    return label.replace(/^[\p{Emoji_Presentation}\p{Emoji}️‍⃣]+\s*/u, '')
}

const handleClick = (mode: ChatMode) => {
    chatStore.setRole(mode.role)
    router.replace(`/chat/${mode.role}`)
}

onMounted(async () => {
    try {
        const res = await getChatMode()
        chatModes.value = res.data
    } catch (error) {
        ElMessage.error('加载角色列表失败')
    }
})
</script>
