<template>
    <div class="flex-1 flex flex-col chat-main min-w-0" :class="{ 'chat-main--oral': isOralMode }">
        <WelcomeScreen v-if="!chatStore.activeConversationId" @select-card="handleSelectCard" />
        <template v-else>
            <OralStudioBanner v-if="isOralMode" />
            <ChatTopbar
                :title="chatStore.activeConversation?.title ?? '新对话'"
                :role-icon="roleInfo.icon"
                :role-label="roleInfo.label"
                :is-streaming="isStreaming"
                :oral-mode="isOralMode"
                @stop="stopGeneration"
            />
            <div ref="scrollContainerRef" class="flex-1 overflow-y-auto chat-scroll px-5 py-4">
                <div class="max-w-[720px] mx-auto space-y-7">
                    <div v-if="historyLoading" class="py-12 text-center text-sm text-stone-400">加载对话历史…</div>
                    <div v-else-if="historyError" class="py-12 text-center">
                        <p class="text-sm text-stone-500 mb-3">{{ historyError }}</p>
                        <button
                            type="button"
                            class="text-sm text-indigo-600 hover:text-indigo-500"
                            @click="reloadHistory"
                        >重试</button>
                    </div>
                    <template v-else>
                    <ChatMessageItem
                        v-for="(item, index) in list"
                        :key="item.id ?? index"
                        :item="item"
                        :avatar="avatar"
                        :ai-avatar="aiAvatar"
                        :role-label="roleInfo.label"
                        :role-icon="roleInfo.icon"
                        :auto-tts="autoTts"
                        :tts-lang="ttsLang"
                        :oral-mode="isOralMode"
                        @retry="retryMessage"
                        @recommend-buy="(c) => emit('recommend-buy', c)"
                        @recommend-learn="(c) => emit('recommend-learn', c)"
                        @purchase-learn="(c) => emit('purchase-learn', c)"
                    />
                    <div ref="chatRef" />
                    <div v-if="historyTruncated" class="text-center text-xs text-stone-400 py-2">
                        仅显示最近 50 条消息，更早的记录未加载
                    </div>
                    </template>
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
            :oral-mode="isOralMode"
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
import OralStudioBanner from './OralStudioBanner.vue'
import ChatTopbar from './ChatTopbar.vue'
import ChatMessageItem from './ChatMessage.vue'
import type { LocalMessage } from './ChatMessage.vue'
import ChatInputDock from './ChatInputDock.vue'
import type { CourseBatchStatus } from '@en/common/course'
import { ElMessage } from 'element-plus'
import { isShowLogin } from '@/components/Login/loginState'
import { stripRecommendationJson, sanitizeContentAfter } from '../sanitizeContent'
import { parseRecommendBlock } from '../parseRecommendBlock'
import { parseGrammarBlock } from '../parseGrammarBlock'
import { parsePurchaseBlock } from '../parsePurchaseBlock'
import type { ChatPurchaseBlock } from '@en/common/chat'

const emit = defineEmits<{
    'recommend-buy': [course: CourseBatchStatus]
    'recommend-learn': [course: CourseBatchStatus]
    'purchase-confirm': [block: ChatPurchaseBlock]
    'purchase-learn': [course: CourseBatchStatus]
}>()

const router = useRouter()
const chatStore = useChatStore()
const isOralMode = computed(() => chatStore.activeRole === 'oral')
const { avatar } = useAvatar()
const voiceLang = computed(() =>
    chatStore.activeRole === 'oral' ? 'en-US' : 'zh-CN',
)
const autoTts = computed(() =>
    chatStore.activeRole === 'oral' || chatStore.activeRole === 'master',
)
const ttsLang = computed(() =>
    chatStore.activeRole === 'oral' || chatStore.activeRole === 'master' ? 'en-US' : 'zh-CN',
)
const { isRecording, start, stop, setLang } = useVoiceToText({
    lang: voiceLang.value,
    continuous: true,
})

watch(voiceLang, (lang) => setLang(lang), { immediate: true })

const inputPlaceholder = ref('请输入内容')

watch(isOralMode, (oral) => {
    if (oral) {
        deepThink.value = false
        webSearch.value = false
        if (inputPlaceholder.value === '请输入内容') {
            inputPlaceholder.value = 'Speak or type in English — tap 🎤 for voice'
        }
    } else if (inputPlaceholder.value.startsWith('Speak or type')) {
        inputPlaceholder.value = '请输入内容'
    }
}, { immediate: true })

const list = ref<ChatMessageList>([])
const message = ref('')
const deepThink = ref(false)
const webSearch = ref(false)

/** 与后端 _should_auto_web_search 对齐：天气/新闻等实时问题 */
const REALTIME_WEB_HINTS = [
    '天气', '气温', '下雨', '下雪', '预报', '风力',
    '新闻', '热搜', '最新', '实时', '今天', '明天', '后天',
    '股价', '汇率', '赛事', '比赛结果',
]

function shouldAutoWebSearch(text: string): boolean {
    const t = text.trim()
    return t.length > 0 && REALTIME_WEB_HINTS.some((h) => t.includes(h))
}

const chatRef = useTemplateRef<HTMLDivElement>('chatRef')
const scrollContainerRef = useTemplateRef<HTMLDivElement>('scrollContainerRef')
const dockRef = ref<InstanceType<typeof ChatInputDock> | null>(null)
const isStreaming = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const historyTruncated = ref(false)

const roleInfo = computed(() => roleConfig[chatStore.activeRole])

let scrollRafId: number | null = null
let pendingForce = false

function scrollToBottom(force = false, instant = false) {
    if (force) pendingForce = true
    if (scrollRafId !== null) return
    scrollRafId = requestAnimationFrame(() => {
        scrollRafId = null
        const f = pendingForce
        pendingForce = false
        const container = scrollContainerRef.value
        if (!container) return
        if (!f) {
            const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150
            if (!isNearBottom) return
        }
        container.scrollTo({
            top: container.scrollHeight,
            behavior: instant || f ? 'auto' : 'smooth',
        })
    })
}

async function scrollToBottomAfterRender(force = false) {
    await nextTick()
    await nextTick()
    scrollToBottom(force, true)
}

let abortController: AbortController | null = null
let toolCallingStart = 0
let isSending = false
let currentConversationId: string | null = null
/** 结构化工具（推荐/语法）之后，后续 chat 片段写入 contentAfter */
let postToolStreamPhase: 'none' | 'after' = 'none'
let isAlive = true

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
    isSending = false
    const aiMsg = findLastAiChatMessage()
    if (!aiMsg) return
    aiMsg.streaming = false
    if (aiMsg.content) {
        aiMsg.status = undefined
        aiMsg.interrupted = true
    }
}

watch(() => chatStore.activeConversationId, async (newId, oldId) => {
    if (oldId && newId !== oldId && (isStreaming.value || isSending)) {
        stopGeneration()
        ElMessage.info('已切换对话，当前回复已停止')
    }
    if (isStreaming.value || isSending) return
    if (newId !== currentConversationId) {
        list.value = []
        currentConversationId = newId
    }
    if (abortController) { abortController.abort(); abortController = null }
    if (newId) {
        await loadHistory(newId)
    } else {
        historyError.value = ''
        historyLoading.value = false
    }
}, { immediate: true })

async function loadHistory(conversationId: string) {
    if (!isAlive) return
    historyLoading.value = true
    historyError.value = ''
    historyTruncated.value = false
    try {
        const res = await getChatHistory(conversationId)
        if (!isAlive) return
        historyTruncated.value = !!res.data.truncated
        list.value = res.data.messages.map((msg, index) => {
            const item: ChatMessage = {
                ...msg,
                id: msg.id ?? `hist-${index}`,
                type: msg.type ?? 'chat',
            }
            if (item.role === 'ai') {
                if (item.content) item.content = stripRecommendationJson(item.content)
                if (item.contentAfter) {
                    item.contentAfter = sanitizeContentAfter(item.contentAfter, !!item.recommendBlock)
                }
            }
            return item
        })
    } catch {
        historyError.value = '加载历史失败，请重试'
        ElMessage.error('加载对话历史失败')
    } finally {
        historyLoading.value = false
        if (isAlive && list.value.length > 0) {
            await scrollToBottomAfterRender(true)
        }
    }
}

function reloadHistory() {
    const id = chatStore.activeConversationId
    if (id) void loadHistory(id)
}

watch(() => chatStore.activeRole, () => {
    if (abortController) { abortController.abort(); abortController = null }
    isStreaming.value = false
    isSending = false
    currentConversationId = null
    list.value = []
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

const sendMessage = async () => {
    if (!message.value) return
    const token = await ensureValidToken()
    if (!token) {
        ElMessage.error('登录已过期，请重新登录')
        isShowLogin.value = true
        return
    }
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
    list.value.push({ id: `human-${Date.now()}`, role: 'human', content: msg, type: 'chat' })
    list.value.push({
        id: `ai-${Date.now()}`,
        role: 'ai',
        content: '',
        reasoning: deepThink.value ? '' : undefined,
        usedDeepThink: !isOralMode.value && deepThink.value,
        status: 'loading',
        type: 'chat',
        originalContent: msg,
        streaming: true,
    })
    nextTick(() => scrollToBottom(true))
    const aiIndex = list.value.length - 1
    const isFirstMessage = list.value.filter(m => m.role === 'human').length === 1

    if (abortController) abortController.abort()
    abortController = new AbortController()
    isStreaming.value = true
    isSending = false

    postToolStreamPhase = 'none'
    let pendingPurchaseBlock: ChatPurchaseBlock | null = null

    const effectiveWebSearch = !isOralMode.value && !deepThink.value
        && (webSearch.value || shouldAutoWebSearch(msg))

    sse<ChatSSEMessage, ChatDto>(CHAT_URL, 'POST',
        { conversationId: chatStore.activeConversationId!, role: chatStore.activeRole, content: msg, deepThink: isOralMode.value ? false : deepThink.value, webSearch: effectiveWebSearch },
        (data) => {
            if (!isAlive) return
            const aiMsg = list.value[aiIndex]
            if (!aiMsg) return
            if (data.type === 'reasoning') { aiMsg.reasoning += data.content ?? ''; if (aiMsg.status === 'loading') aiMsg.status = undefined; scrollToBottom() }
            if (data.type === 'chat') {
                if (aiMsg.status) aiMsg.status = undefined
                const chunk = data.content ?? ''
                if (postToolStreamPhase === 'after') {
                    const merged = (aiMsg.contentAfter ?? '') + chunk
                    aiMsg.contentAfter = sanitizeContentAfter(merged, !!(aiMsg.recommendBlock || aiMsg.grammarBlock))
                } else {
                    aiMsg.content = stripRecommendationJson(aiMsg.content + chunk)
                }
                scrollToBottom()
            }
            if (data.type === 'tool') {
                toolCallingStart = Date.now()
                aiMsg.status = 'tool_calling'
                aiMsg.toolName = data.tool
                if (data.tool === 'course_recommendation' || data.tool === 'grammar_check') {
                    postToolStreamPhase = 'after'
                }
                scrollToBottom()
            }
            if (data.type === 'tool_result') {
                if (data.tool === 'course_recommendation') {
                    const block = data.recommendBlock ?? parseRecommendBlock(data.output ?? '')
                    if (block) aiMsg.recommendBlock = block
                    aiMsg.status = undefined
                    if (aiMsg.contentAfter) {
                        aiMsg.contentAfter = sanitizeContentAfter(aiMsg.contentAfter, true)
                    }
                } else if (data.tool === 'grammar_check') {
                    const block = data.grammarBlock ?? parseGrammarBlock(data.output ?? '')
                    if (block) aiMsg.grammarBlock = block
                    aiMsg.status = undefined
                    if (aiMsg.contentAfter) {
                        aiMsg.contentAfter = sanitizeContentAfter(aiMsg.contentAfter, true)
                    }
                } else if (data.tool === 'course_purchase') {
                    const block = data.purchaseBlock ?? parsePurchaseBlock(data.output ?? '')
                    aiMsg.status = undefined
                    if (block?.action === 'already_owned' && block.course) {
                        aiMsg.purchaseBlock = block
                    } else if (block?.action === 'confirm' || block?.action === 'resume_pay') {
                        pendingPurchaseBlock = block
                    }
                } else {
                    setTimeout(() => {
                        const msg = list.value[aiIndex]
                        if (!msg) return
                        msg.status = 'tool_done'
                        setTimeout(() => {
                            if (list.value[aiIndex]?.status === 'tool_done') {
                                list.value[aiIndex].status = undefined
                            }
                        }, 600)
                    }, Math.max(0, 400 - (Date.now() - toolCallingStart)))
                }
                scrollToBottom()
            }
            if (data.type === 'done') {
                isStreaming.value = false
                postToolStreamPhase = 'none'
                if (aiMsg) {
                    aiMsg.content = stripRecommendationJson(aiMsg.content)
                    if (aiMsg.contentAfter) {
                        aiMsg.contentAfter = sanitizeContentAfter(aiMsg.contentAfter, !!(aiMsg.recommendBlock || aiMsg.grammarBlock))
                    }
                    aiMsg.streaming = false
                    aiMsg.status = undefined
                }
                if (pendingPurchaseBlock) {
                    emit('purchase-confirm', pendingPurchaseBlock)
                    pendingPurchaseBlock = null
                }
                scrollToBottom()
                if (isFirstMessage && chatStore.activeConversation?.title === '新对话') {
                    generateTitle(chatStore.activeConversationId!, msg).then(res => {
                        chatStore.updateTitle(res.data.id, res.data.title)
                    }).catch(() => {
                        const fallback = msg.trim().slice(0, 30) || '新对话'
                        if (chatStore.activeConversationId) {
                            chatStore.updateTitle(chatStore.activeConversationId, fallback)
                        }
                    })
                }
            }
            if (data.type === 'error') {
                pendingPurchaseBlock = null
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
    isAlive = false
    window.removeEventListener('keydown', onKeydown)
    if (abortController) abortController.abort()
    if (scrollRafId !== null) cancelAnimationFrame(scrollRafId)
    pendingForce = false
})
</script>
