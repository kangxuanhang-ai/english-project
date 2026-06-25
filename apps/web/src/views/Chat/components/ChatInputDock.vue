<template>
    <div
        class="input-dock shrink-0 px-7 pb-5 pt-4 relative z-[2]"
        :class="{ 'opacity-60': isStreaming && !isRecording, 'input-dock--oral': oralMode }"
        style="background: linear-gradient(180deg, transparent, rgba(255,255,255,.5))"
    >
        <div class="max-w-[720px] mx-auto">
            <!-- 口语模式：能力标签，替代深度思考/联网 -->
            <div v-if="oralMode" class="flex flex-wrap gap-2 mb-3">
                <span class="oral-feature-tag oral-feature-tag--active">🎤 Voice · EN-US</span>
                <span class="oral-feature-tag oral-feature-tag--active">🔊 Auto-read replies</span>
                <span class="oral-feature-tag">✓ Grammar coach on demand</span>
            </div>
            <div v-else class="flex gap-2 mb-3">
                <button
                    type="button"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11.5px] font-semibold border transition-all"
                    :class="deepThink
                        ? 'border-[color-mix(in_srgb,var(--chat-accent)_30%,transparent)] text-[var(--chat-accent-text)] shadow-[0_1px_4px_var(--chat-glow)]'
                        : 'border-stone-200 bg-white/80 text-stone-500 hover:bg-stone-50'"
                    :style="deepThink ? { background: 'var(--chat-accent-soft)' } : {}"
                    @click="toggleDeepThink"
                >
                    <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v1"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v1"/><path d="M12 2v2"/><path d="M12 22v-2"/><path d="M9.5 22A2.5 2.5 0 0 0 12 19.5v-1"/><path d="M14.5 22A2.5 2.5 0 0 1 12 19.5v-1"/><circle cx="12" cy="12" r="4"/></svg>
                    <span>深度思考</span>
                </button>
                <button
                    type="button"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11.5px] font-semibold border transition-all"
                    :class="webSearch
                        ? 'bg-blue-50 border-blue-300 text-blue-800 shadow-[0_1px_4px_rgba(37,99,235,.1)]'
                        : 'border-stone-200 bg-white/80 text-stone-500 hover:bg-stone-50'"
                    @click="toggleWebSearch"
                >
                    <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                    <span>联网搜索</span>
                </button>
            </div>

            <div
                class="flex items-end gap-2.5 bg-white border border-stone-200 rounded-[18px] px-3 py-3 pl-[18px] shadow-[0_2px_8px_rgba(0,0,0,.04),0_8px_24px_rgba(0,0,0,.03)] transition-all"
                :class="[
                    focused ? 'border-[color-mix(in_srgb,var(--chat-accent)_40%,#e7e5e4)] shadow-[0_0_0_4px_var(--chat-glow),0_4px_16px_rgba(0,0,0,.05)]' : '',
                    isStreaming && !isRecording ? 'pointer-events-none grayscale-[30%]' : '',
                    oralMode ? 'border-teal-200/80 bg-teal-50/20' : '',
                ]"
            >
                <textarea
                    ref="textareaRef"
                    :value="modelValue"
                    :placeholder="placeholder"
                    maxlength="4000"
                    rows="1"
                    class="flex-1 border-none outline-none resize-none bg-transparent text-sm leading-relaxed min-h-[46px] max-h-[120px] overflow-y-auto"
                    :class="oralMode ? 'text-teal-950 placeholder:text-teal-600/45' : 'text-stone-900'"
                    :style="{ height: `${MIN_HEIGHT}px` }"
                    @input="onInput"
                    @keydown="onKeydown"
                    @focus="focused = true"
                    @blur="focused = false"
                />
                <div class="flex gap-1.5 shrink-0 items-center">
                    <!-- 口语模式：麦克风优先、更大 -->
                    <template v-if="oralMode && !isStreaming">
                        <button
                            v-if="!isRecording"
                            type="button"
                            class="oral-mic-btn w-[46px] h-[46px] rounded-2xl flex items-center justify-center text-white shadow-lg shadow-teal-500/30 pointer-events-auto"
                            title="Start speaking"
                            @click="emit('start-recording')"
                        >
                            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
                        </button>
                        <button
                            v-else
                            type="button"
                            class="oral-mic-btn oral-mic-btn--recording w-[46px] h-[46px] rounded-2xl flex items-center justify-center text-white pointer-events-auto"
                            title="Stop & send"
                            @click="emit('stop-recording')"
                        >
                            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                        </button>
                    </template>
                    <button
                        v-if="isStreaming"
                        type="button"
                        class="w-[38px] h-[38px] rounded-xl flex items-center justify-center bg-stone-400 text-white pointer-events-auto"
                        @click="emit('stop')"
                    >
                        <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                    </button>
                    <button
                        v-else
                        type="button"
                        class="w-[38px] h-[38px] rounded-xl flex items-center justify-center text-white shadow-[0_3px_12px_var(--chat-bubble-shadow)]"
                        :class="oralMode ? 'bg-linear-to-br from-teal-400 to-emerald-600' : ''"
                        :style="oralMode ? {} : { background: 'linear-gradient(145deg, var(--chat-accent-light), var(--chat-accent-dark))' }"
                        @click="emit('send')"
                    >
                        <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
                    </button>
                    <button
                        v-if="!oralMode && !isRecording"
                        type="button"
                        class="w-[38px] h-[38px] rounded-xl flex items-center justify-center border border-stone-200 bg-stone-50 text-stone-500 hover:border-stone-300 pointer-events-auto"
                        @click="emit('start-recording')"
                    >
                        <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
                    </button>
                    <button
                        v-else-if="!oralMode"
                        type="button"
                        class="w-[38px] h-[38px] rounded-xl flex items-center justify-center border border-red-300 bg-red-50 text-red-600 mic-recording pointer-events-auto"
                        @click="emit('stop-recording')"
                    >
                        <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
                    </button>
                </div>
            </div>
            <div class="text-right text-[10.5px] mt-2 font-medium tracking-wide" :class="oralMode ? 'text-teal-600/60' : 'text-stone-400'">
                <span v-if="isStreaming">按 Esc 或点击停止生成中断</span>
                <span v-else-if="oralMode && isRecording" class="text-teal-700">🎙️ Listening… tap stop when finished</span>
                <span v-else-if="oralMode">Tap the big mic to speak · replies read aloud automatically</span>
                <span v-else>{{ modelValue.length }} / 4000</span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const MIN_HEIGHT = 46
const MAX_HEIGHT = 120

const props = defineProps<{
    modelValue: string
    deepThink: boolean
    webSearch: boolean
    isStreaming: boolean
    isRecording: boolean
    oralMode?: boolean
    placeholder: string
}>()

const emit = defineEmits<{
    'update:modelValue': [value: string]
    'update:deepThink': [value: boolean]
    'update:webSearch': [value: boolean]
    send: []
    stop: []
    'start-recording': []
    'stop-recording': []
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const focused = ref(false)

function autoResize(el: HTMLTextAreaElement) {
    el.style.height = 'auto'
    el.style.height = `${Math.min(Math.max(el.scrollHeight, MIN_HEIGHT), MAX_HEIGHT)}px`
}

function onInput(e: Event) {
    const el = e.target as HTMLTextAreaElement
    emit('update:modelValue', el.value)
    autoResize(el)
}

function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        if (!props.isStreaming) emit('send')
    }
}

function toggleDeepThink() {
    const next = !props.deepThink
    emit('update:deepThink', next)
    if (next) emit('update:webSearch', false)
}

function toggleWebSearch() {
    const next = !props.webSearch
    emit('update:webSearch', next)
    if (next) emit('update:deepThink', false)
}

function resetHeight() {
    if (textareaRef.value) {
        textareaRef.value.style.height = `${MIN_HEIGHT}px`
    }
}

defineExpose({ resetHeight })
</script>

<style scoped>
.mic-recording {
    animation: pulse-ring 1.5s ease infinite;
}
.oral-mic-btn {
    background: linear-gradient(145deg, #2dd4bf, #0d9488);
    animation: mic-glow 2.5s ease-in-out infinite;
}
.oral-mic-btn--recording {
    background: linear-gradient(145deg, #f87171, #dc2626);
    animation: pulse-ring 1.2s ease infinite;
}
.oral-feature-tag {
    display: inline-flex;
    align-items: center;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 600;
    color: #5eead4;
    background: rgba(255, 255, 255, 0.7);
    border: 1px dashed rgba(153, 246, 228, 0.8);
}
.oral-feature-tag--active {
    color: #115e59;
    background: rgba(240, 253, 250, 0.95);
    border: 1px solid rgba(45, 212, 191, 0.5);
}
@keyframes pulse-ring {
    0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.25); }
    50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
}
@keyframes mic-glow {
    0%, 100% { box-shadow: 0 4px 20px rgba(13, 148, 136, 0.35); }
    50% { box-shadow: 0 4px 28px rgba(45, 212, 191, 0.55); }
}
</style>
