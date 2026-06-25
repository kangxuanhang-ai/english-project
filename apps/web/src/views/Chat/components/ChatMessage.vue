<template>
    <!-- 用户消息 -->
    <div v-if="item.role === 'human'" class="flex flex-row-reverse items-end gap-3.5 msg-in">
        <div
            class="w-10 h-10 rounded-full overflow-hidden shrink-0 ring-2 ring-white shadow-[0_0_0_1px_var(--chat-accent-border)]"
        >
            <el-avatar :size="40" :src="avatar" />
        </div>
        <div class="flex flex-col items-end max-w-[min(72%,480px)]">
            <span v-if="oralMode" class="text-[10px] font-bold uppercase tracking-wider text-teal-600/70 mb-1 mr-1">You said</span>
            <div
                class="px-[18px] py-3 text-sm text-white leading-relaxed rounded-[20px_20px_6px_20px]"
                :class="oralMode ? 'oral-user-bubble' : ''"
                :style="oralMode ? {} : { background: 'linear-gradient(145deg, var(--chat-accent-light) 0%, var(--chat-accent) 50%, var(--chat-accent-dark) 100%)', boxShadow: '0 4px 16px var(--chat-bubble-shadow), inset 0 1px 0 rgba(255,255,255,.15)' }"
            >{{ item.content }}</div>
        </div>
    </div>

    <!-- AI 卡片消息 -->
    <div v-else class="flex items-start gap-3.5 msg-in">
        <div
            class="w-10 h-10 rounded-full shrink-0 ring-2 ring-white shadow-[0_0_0_1px_var(--chat-accent-border),0_4px_12px_var(--chat-glow)] overflow-hidden"
        >
            <el-avatar :size="40" :src="aiAvatar" />
        </div>
        <div class="flex-1 min-w-0 max-w-[85%]">
            <div class="relative overflow-hidden rounded-[18px] shadow-[0_2px_8px_rgba(0,0,0,.04),0_8px_24px_rgba(0,0,0,.03)]" :class="oralMode ? 'oral-examiner-card bg-linear-to-br from-white to-teal-50/40 border border-teal-100/80' : 'bg-white/92 backdrop-blur-sm border border-black/[0.06]'">
                <div
                    class="absolute top-0 left-0 right-0 h-[3px]"
                    :style="{ background: oralMode ? 'linear-gradient(90deg, #5eead4, #0d9488, #059669)' : 'linear-gradient(90deg, var(--chat-accent-light), var(--chat-accent), var(--chat-accent-dark))' }"
                />
                <div class="flex items-center justify-between px-[18px] py-3 border-b" :class="oralMode ? 'border-teal-100/80' : 'border-black/[0.04]'">
                    <div class="flex items-center gap-1.5 text-xs font-bold" :class="oralMode ? 'text-teal-900' : 'text-stone-700'">
                        <span class="w-1.5 h-1.5 rounded-full shadow-[0_0_6px_var(--chat-accent)]" :style="{ background: oralMode ? '#14b8a6' : 'var(--chat-accent)' }" />
                        <template v-if="oralMode">🎙️ Examiner Feedback</template>
                        <template v-else>{{ roleIcon }} {{ roleLabel }}</template>
                    </div>
                    <span v-if="oralMode" class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-100 text-teal-700">EN</span>
                    <span v-else class="text-[11px] text-stone-400 font-medium">刚刚</span>
                </div>

                <div class="px-[18px] py-4 text-[13.5px] text-stone-700 leading-relaxed">
                    <div v-if="showReasoningSection" class="mb-3">
                        <button
                            type="button"
                            class="w-[calc(100%-0px)] mx-0 flex items-center gap-2 px-3 py-2 rounded-xl bg-gradient-to-br from-stone-50 to-stone-100 border border-stone-200 text-[11px] text-stone-500 font-medium"
                            @click="reasoningOpen = !reasoningOpen"
                        >
                            <span v-if="isReasoningStreaming" class="flex items-center gap-1.5 text-indigo-600">
                                <span class="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                                深度思考中…
                            </span>
                            <span v-else>深度思考</span>
                            <span class="ml-auto text-[10px]">{{ reasoningOpen ? '▲' : '▼' }}</span>
                        </button>
                        <div v-if="reasoningOpen" class="mt-2 px-3.5 py-3 rounded-xl bg-stone-50 border border-stone-100 border-l-[3px] border-l-indigo-300 text-[11.5px] text-stone-600 leading-relaxed whitespace-pre-wrap">
                            <template v-if="item.reasoning">
                                {{ item.reasoning }}<span v-if="isReasoningStreaming" class="stream-cursor" />
                            </template>
                            <div v-else-if="isReasoningStreaming" class="flex gap-1.5 py-1">
                                <span v-for="n in 3" :key="n" class="typing-dot" />
                            </div>
                        </div>
                    </div>

                    <div v-if="showMainLoading" class="flex gap-1.5 py-1.5">
                        <span v-for="n in 3" :key="n" class="typing-dot" />
                    </div>

                    <div v-else-if="item.status === 'error'" class="p-3.5 rounded-xl bg-gradient-to-br from-red-50 to-red-100 border border-red-200 text-red-700 text-[13px]">
                        {{ item.content }}
                        <button
                            type="button"
                            class="mt-3 px-4 py-1.5 rounded-lg border border-red-300 bg-white text-red-600 text-xs font-semibold shadow-sm"
                            @click="emit('retry', item)"
                        >重试</button>
                    </div>

                    <template v-else>
                        <div v-if="item.content" class="chat-md">
                            <div v-html="renderedHtml" />
                        </div>

                        <div
                            v-if="isRecommendLoading"
                            class="mt-3 flex items-center gap-2 px-3 py-2.5 rounded-xl text-[11px] font-medium border"
                            style="color: var(--chat-accent-text); border-color: var(--chat-accent-border); background: var(--chat-accent-soft)"
                        >
                            <span class="animate-pulse">⏳</span>
                            正在根据你的学习数据生成推荐…
                        </div>

                        <div
                            v-if="isGrammarLoading"
                            class="mt-3 flex items-center gap-2 px-3 py-2.5 rounded-xl text-[11px] font-medium border"
                            style="color: var(--chat-accent-text); border-color: var(--chat-accent-border); background: var(--chat-accent-soft)"
                        >
                            <span class="animate-pulse">⏳</span>
                            正在检查语法…
                        </div>

                        <ChatRecommendBlock
                            v-if="item.recommendBlock"
                            :data="item.recommendBlock"
                            @buy="(c) => emit('recommend-buy', c)"
                            @learn="(c) => emit('recommend-learn', c)"
                        />

                        <ChatGrammarBlock
                            v-if="item.grammarBlock"
                            :data="item.grammarBlock"
                        />

                        <div
                            v-if="showPurchaseLearn"
                            class="mt-3"
                        >
                            <button
                                type="button"
                                class="inline-flex items-center justify-center px-4 py-2 rounded-xl text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors"
                                @click="onPurchaseLearn"
                            >
                                去学习
                            </button>
                        </div>

                        <div v-if="item.contentAfter" class="chat-md mt-3">
                            <div v-html="renderedHtmlAfter" />
                        </div>

                        <div
                            v-if="showToolCalling"
                            class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-semibold bg-gradient-to-br from-teal-50 to-emerald-100 border border-teal-200 text-teal-800 mb-2"
                        >
                            <span class="animate-pulse">⏳</span>
                            {{ toolCallingLabel }}
                        </div>

                        <div
                            v-else-if="showToolDone"
                            class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-semibold bg-gradient-to-br from-green-50 to-green-100 border border-green-300 text-green-800 mb-2"
                        >
                            ✓ {{ toolDoneLabel }}
                        </div>

                        <div
                            v-else-if="showHistoryTool"
                            class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-semibold bg-gradient-to-br from-green-50 to-green-100 border border-green-300 text-green-800 mb-2"
                        >
                            ✓ {{ toolDoneLabel }}
                            <span v-if="item.toolSummary" class="font-normal text-green-700/80 truncate max-w-[240px]">
                                · {{ item.toolSummary }}
                            </span>
                        </div>
                    </template>
                </div>

                <div
                    v-if="hasReadableContent && !item.streaming && item.status !== 'error' && item.role === 'ai'"
                    class="px-[18px] pb-3 flex justify-end border-t border-black/[0.03] pt-2"
                >
                    <button
                        v-if="ttsSupported"
                        type="button"
                        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] text-stone-500 hover:bg-stone-50 border border-stone-200"
                        @click="handleSpeak"
                    >
                        🔊 {{ isSpeaking ? 'Reading…' : 'Read aloud' }}
                    </button>
                </div>

                <div v-if="item.interrupted && item.content" class="px-[18px] pb-3 text-xs text-stone-400">
                    已中断
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ChatMessage } from '@en/common/chat'
import type { CourseBatchStatus } from '@en/common/course'
import ChatRecommendBlock from './ChatRecommendBlock.vue'
import ChatGrammarBlock from './ChatGrammarBlock.vue'
import { parseMarkdown } from '../markdown'
import { useTTS } from '@/hooks/useTTS'

export type LocalMessage = ChatMessage & { interrupted?: boolean; usedDeepThink?: boolean }

const props = defineProps<{
    item: LocalMessage
    avatar: string
    aiAvatar: string
    roleLabel: string
    roleIcon: string
    autoTts?: boolean
    ttsLang?: string
    oralMode?: boolean
}>()

const emit = defineEmits<{
    retry: [item: LocalMessage]
    'recommend-buy': [course: CourseBatchStatus]
    'recommend-learn': [course: CourseBatchStatus]
    'purchase-learn': [course: CourseBatchStatus]
}>()

const reasoningOpen = ref(false)
const spokenIds = ref(new Set<string>())
const { supported: ttsSupported, isSpeaking, speak, stop } = useTTS()

const showReasoningSection = computed(() =>
    !!props.item.reasoning || !!props.item.usedDeepThink,
)

const hasStructuredToolBlock = computed(() =>
    !!(props.item.recommendBlock || props.item.grammarBlock || props.item.purchaseBlock),
)

const isReasoningStreaming = computed(() =>
    !!props.item.streaming
    && !!props.item.usedDeepThink
    && !props.item.content
    && !hasStructuredToolBlock.value,
)

const showMainLoading = computed(() =>
    (props.item.status === 'loading' || (props.item.status === 'tool_calling' && !props.item.content && !hasStructuredToolBlock.value))
    && !isReasoningStreaming.value,
)

watch(
    () => [props.item.streaming, props.item.reasoning, props.item.usedDeepThink] as const,
    ([streaming, reasoning, usedDeepThink]) => {
        if (streaming && (reasoning || usedDeepThink)) {
            reasoningOpen.value = true
        }
    },
    { immediate: true },
)

const CURSOR = '<span class="stream-cursor"></span>'

const isRecommendLoading = computed(() =>
    props.item.status === 'tool_calling'
    && props.item.toolName === 'course_recommendation'
    && !props.item.recommendBlock,
)

const TOOL_LABELS: Record<string, { calling: string; done: string }> = {
    word_lookup: { calling: '正在查询单词…', done: '单词查询完成' },
    progress_query: { calling: '正在查询学习进度…', done: '学习进度查询完成' },
    grammar_check: { calling: '正在检查语法…', done: '语法检查完成' },
    web_search: { calling: '正在联网搜索…', done: '搜索完成' },
    knowledge_search: { calling: '正在检索知识库…', done: '知识库检索完成' },
    course_recommendation: { calling: '正在生成推荐…', done: '推荐生成完成' },
    course_purchase: { calling: '正在处理购课…', done: '购课请求已处理' },
}

const toolLabels = computed(() => {
    const name = props.item.toolName ?? ''
    if (props.oralMode && name === 'grammar_check') {
        return { calling: 'Checking your grammar…', done: 'Grammar check done' }
    }
    return TOOL_LABELS[name] ?? { calling: '正在查询…', done: '查询完成' }
})

const showHistoryTool = computed(() =>
    !props.item.status
    && !!props.item.toolName
    && props.item.toolName !== 'course_recommendation'
    && props.item.toolName !== 'course_purchase'
    && !(props.item.toolName === 'grammar_check' && props.item.grammarBlock),
)

const showToolCalling = computed(() =>
    props.item.status === 'tool_calling'
    && props.item.toolName !== 'course_recommendation'
    && props.item.toolName !== 'grammar_check'
    && props.item.toolName !== 'course_purchase',
)

const isGrammarLoading = computed(() =>
    props.item.status === 'tool_calling'
    && props.item.toolName === 'grammar_check'
    && !props.item.grammarBlock,
)

const showToolDone = computed(() =>
    props.item.status === 'tool_done'
    && props.item.toolName !== 'course_recommendation'
    && props.item.toolName !== 'grammar_check'
    && props.item.toolName !== 'course_purchase',
)

const showPurchaseLearn = computed(() =>
    props.item.purchaseBlock?.action === 'already_owned'
    && !!props.item.purchaseBlock.course,
)

const onPurchaseLearn = () => {
    const course = props.item.purchaseBlock?.course
    if (course) emit('purchase-learn', course)
}

const toolCallingLabel = computed(() => toolLabels.value.calling)
const toolDoneLabel = computed(() => toolLabels.value.done)

const hasReadableContent = computed(() =>
    !!(props.item.content || props.item.contentAfter || props.item.recommendBlock || props.item.grammarBlock || props.item.purchaseBlock),
)

const renderedHtml = computed(() => {
    if (!props.item.content) return ''
    let html = parseMarkdown(props.item.content)
    if (props.item.streaming && !hasStructuredToolBlock.value && !props.item.contentAfter) {
        html += CURSOR
    }
    return html
})

const renderedHtmlAfter = computed(() => {
    if (!props.item.contentAfter) return ''
    let html = parseMarkdown(props.item.contentAfter)
    if (props.item.streaming) html += CURSOR
    return html
})

const speakText = computed(() =>
    [props.item.content, props.item.contentAfter].filter(Boolean).join('\n'),
)

const handleSpeak = () => {
    if (!speakText.value) return
    if (isSpeaking.value) {
        stop()
        return
    }
    speak(speakText.value, props.ttsLang ?? 'zh-CN')
}

watch(
    () => props.item.streaming,
    (streaming, prev) => {
        if (prev && !streaming && props.autoTts && speakText.value && props.item.role === 'ai') {
            const id = props.item.id ?? speakText.value.slice(0, 32)
            if (spokenIds.value.has(id)) return
            spokenIds.value.add(id)
            speak(speakText.value, props.ttsLang ?? 'en-US')
        }
    },
)
</script>

<style scoped>
.typing-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--chat-accent);
    animation: bounce 1.4s infinite ease-in-out both;
}
.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0s; }
@keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.35; }
    40% { transform: translateY(-5px); opacity: 1; }
}
.oral-user-bubble {
    background: linear-gradient(145deg, #5eead4 0%, #0d9488 55%, #0f766e 100%);
    box-shadow: 0 4px 18px rgba(13, 148, 136, 0.35), inset 0 1px 0 rgba(255,255,255,.2);
}
.oral-examiner-card {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
}
</style>
