<template>
    <div class="flex-1 flex flex-col chat-main min-w-0">
        <WelcomeScreen v-if="!chatStore.activeConversationId" @select-card="handleSelectCard" />
        <template v-else>
            <ChatTopbar
                :title="chatStore.activeConversation?.title ?? '新对话'"
                :role-icon="roleInfo.icon"
                :role-label="roleInfo.label"
                :is-streaming="isStreaming"
                @stop="stopGeneration"
            />
            <div class="flex-1 overflow-y-auto chat-scroll px-5 py-4">
                <div class="max-w-[720px] mx-auto space-y-7">
                    <ChatMessageItem
                        v-for="(item, index) in list"
                        :key="index"
                        :item="item"
                        :avatar="avatar"
                        :ai-avatar="aiAvatar"
                        :role-label="roleInfo.label"
                        :role-icon="roleInfo.icon"
                        :expanded="expandedTools.has(item.toolId ?? '')"
                        @retry="retryMessage"
                        @toggle-tool="toggleToolExpand"
                    />
                    <div ref="chatRef" />
                </div>
            </div>
        </template>
        <ChatInputDock
            ref="dockRef"
            v-model="message"
            v-model:deep-think="deepThink"
            v-model:web-search="webSearch"
            :is-streaming="isStreaming"
            :is-recording="isRecording"
            :placeholder="inputPlaceholder"
            @send="sendMessage"
            @stop="stopGeneration"
            @start-recording="startRecording"
            @stop-recording="stopRecording"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, useTemplateRef, watch, nextTick, onMounted, onUnmounted } from 'vue'
import type { ChatMessageList, ChatDto, ChatSSEMessage, ChatMessage } from '@en/common/chat'
import { useVoiceToText } from '@/hooks/useVoiceToText'
import { useAvatar } from '@/hooks/useAvatar'
import aiAvatar from '@/assets/images/avatar/1.png'
import { useChatStore } from '@/stores/chat'
import { ensureValidToken } from '@/apis/auth'
import { useRouter } from 'vue-router'
import { getChatHistory, generateTitle } from '@/apis/chat'
import { sse, CHAT_URL } from '@/apis/sse'
import { roleConfig } from '../roleConfig'
import WelcomeScreen from './WelcomeScreen.vue'
import ChatTopbar from './ChatTopbar.vue'
import ChatMessageItem from './ChatMessage.vue'
import type { LocalMessage } from './ChatMessage.vue'
import ChatInputDock from './ChatInputDock.vue'

const router = useRouter()
const chatStore = useChatStore()
const { avatar } = useAvatar()
const { isRecording, start, stop } = useVoiceToText({ lang: 'zh-CN', continuous: true })

const list = ref<ChatMessageList>([])
const message = ref('')
const deepThink = ref(false)
const webSearch = ref(false)
const chatRef = useTemplateRef<HTMLDivElement>('chatRef')
const dockRef = ref<InstanceType<typeof ChatInputDock> | null>(null)
const expandedTools = ref<Set<string>>(new Set())
const isStreaming = ref(false)

const roleInfo = computed(() => roleConfig[chatStore.activeRole])

const toggleToolExpand = (toolId: string | undefined) => {
    if (!toolId) return
    if (expandedTools.value.has(toolId)) expandedTools.value.delete(toolId)
    else expandedTools.value.add(toolId)
}

function scrollToBottom(force = false) {
    const el = chatRef.value?.parentElement?.parentElement
    if (!el) return
    if (!force) {
        const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150
        if (!isNearBottom) return
    }
    nextTick(() => chatRef.value?.scrollIntoView({ behavior: 'smooth' }))
}

let abortController: AbortController | null = null
let toolCallingStart = 0
let isSending = false
let currentConversationId: string | null = null

function findLastAiChatMessage(): LocalMessage | undefined {
    return [...list.value].reverse().find(
        m => m.role === 'ai' && m.type === 'chat',
    ) as LocalMessage | undefined
}

function stopGeneration() {
    if (abortController) {
        abortController.abort()
        abortController = null
    }
    isStreaming.value = false
    const aiMsg = findLastAiChatMessage()
    if (!aiMsg) return
    aiMsg.streaming = false
    if (aiMsg.content) {
        aiMsg.status = undefined
        aiMsg.interrupted = true
    }
}

watch(() => chatStore.activeRole, () => {
    if (abortController) { abortController.abort(); abortController = null }
    isStreaming.value = false
    isSending = false
    currentConversationId = null
    list.value = []
})

watch(() => chatStore.activeConversationId, async (newId) => {
    if (isStreaming.value || isSending) return
    if (newId !== currentConversationId) {
        list.value = []
        currentConversationId = newId
    }
    if (abortController) { abortController.abort(); abortController = null }
    if (newId) {
        const res = await getChatHistory(newId)
        list.value = res.data
        nextTick(() => chatRef.value?.scrollIntoView({ behavior: 'smooth' }))
    }
})

function handleSelectCard(placeholder: string, toggle?: 'deep' | 'web') {
    message.value = placeholder
    inputPlaceholder.value = '请输入内容'
    if (toggle === 'deep') { deepThink.value = true; webSearch.value = false }
    else if (toggle === 'web') { webSearch.value = true; deepThink.value = false }
    else { deepThink.value = false; webSearch.value = false }
}

function retryMessage(item: ChatMessage) {
    if (!item.originalContent) return
    message.value = item.originalContent
    const idx = list.value.indexOf(item)
    if (idx > 0 && list.value[idx - 1]?.role === 'human') {
        list.value.splice(idx - 1, 2)
    } else {
        list.value.splice(idx, 1)
    }
    nextTick(() => sendMessage())
}

const inputPlaceholder = ref('请输入内容')

const sendMessage = async () => {
    if (!message.value) return
    if (!await ensureValidToken()) return
    isSending = true
    if (!chatStore.activeConversationId) {
        const id = await chatStore.createConversation(chatStore.activeRole)
        currentConversationId = id
        router.replace(`/chat/${chatStore.activeRole}/${id}`)
    }
    if (!chatStore.activeConversationId) { isSending = false; return }
    const msg = message.value
    message.value = ''
    dockRef.value?.resetHeight?.()
    inputPlaceholder.value = '请输入内容'
    list.value.push({ role: 'human', content: msg, type: 'chat' })
    list.value.push({ role: 'ai', content: '', reasoning: '', status: 'loading', type: 'chat', originalContent: msg, streaming: true })
    nextTick(() => scrollToBottom(true))
    const aiIndex = list.value.length - 1
    const isFirstMessage = list.value.filter(m => m.role === 'human').length === 1

    if (abortController) abortController.abort()
    abortController = new AbortController()
    isStreaming.value = true
    isSending = false

    sse<ChatSSEMessage, ChatDto>(CHAT_URL, 'POST',
        { conversationId: chatStore.activeConversationId!, role: chatStore.activeRole, content: msg, deepThink: deepThink.value, webSearch: webSearch.value },
        (data) => {
            const aiMsg = list.value[aiIndex]
            if (!aiMsg) return
            if (data.type === 'reasoning') { aiMsg.reasoning += data.content ?? ''; if (aiMsg.status === 'loading') aiMsg.status = undefined; scrollToBottom() }
            if (data.type === 'chat') { if (aiMsg.status) aiMsg.status = undefined; aiMsg.content += data.content ?? ''; scrollToBottom() }
            if (data.type === 'tool') { toolCallingStart = Date.now(); aiMsg.status = 'tool_calling'; aiMsg.toolName = data.tool; list.value.push({ role: 'ai', content: '', type: 'tool', toolId: data.id, toolName: data.tool, toolInput: data.input }); scrollToBottom() }
            if (data.type === 'tool_result') { setTimeout(() => { if (list.value[aiIndex]) list.value[aiIndex].status = 'tool_done' }, Math.max(0, 800 - (Date.now() - toolCallingStart))); const t = [...list.value].reverse().find(m => m.type === 'tool' && m.toolId === data.id); if (t) t.toolOutput = data.output; scrollToBottom() }
            if (data.type === 'done') {
                isStreaming.value = false
                if (aiMsg) aiMsg.streaming = false
                scrollToBottom()
                if (isFirstMessage && chatStore.activeConversation?.title === '新对话') {
                    generateTitle(chatStore.activeConversationId!, msg).then(res => {
                        chatStore.updateTitle(res.data.id, res.data.title)
                    }).catch(() => {})
                }
            }
            if (data.type === 'error') {
                if (aiMsg) { aiMsg.status = 'error'; aiMsg.content = data.message || '请求失败，请重试'; aiMsg.streaming = false }
                isStreaming.value = false
            }
        },
        (error) => {
            if (error.name === 'AbortError') {
                stopGeneration()
                return
            }
            const aiMsg = findLastAiChatMessage()
            if (aiMsg) {
                aiMsg.status = 'error'
                aiMsg.content = '网络错误，请检查连接后重试'
                aiMsg.streaming = false
            }
            isStreaming.value = false
        },
        abortController.signal,
    )
}

const startRecording = () => start((result) => { message.value = result })
const stopRecording = () => { stop(); sendMessage() }

function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && isStreaming.value) stopGeneration()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
    window.removeEventListener('keydown', onKeydown)
    if (abortController) abortController.abort()
})
</script>
