<template>
    <div
        class="flex items-center justify-between px-5 py-3 border-b shrink-0 gap-3"
        :class="oralMode
            ? 'border-teal-100/80 bg-linear-to-r from-teal-50/90 to-white/80 backdrop-blur-sm'
            : 'border-gray-100/80 bg-white/80 backdrop-blur-sm'"
    >
        <div class="flex-1 min-w-0">
            <p v-if="oralMode" class="text-[10px] font-bold uppercase tracking-[0.18em] text-teal-600/80 mb-0.5">Speaking Studio</p>
            <h2
                class="text-[15px] font-semibold line-clamp-2 leading-snug"
                :class="oralMode ? 'text-teal-950' : 'text-gray-800'"
                :title="title"
            >{{ title }}</h2>
        </div>
        <div class="flex items-center gap-2 shrink-0">
            <button
                v-if="isStreaming"
                type="button"
                class="text-xs px-3 py-1.5 rounded-full border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 font-semibold"
                @click="emit('stop')"
            >停止生成</button>
            <span
                v-if="oralMode"
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold text-teal-800 bg-teal-100/80 border border-teal-200/80"
            >
                <span class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                LIVE · {{ roleIcon }} {{ roleLabel }}
            </span>
            <span
                v-else
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
                style="background: var(--chat-accent-soft); color: var(--chat-accent-text); border: 1px solid var(--chat-accent-border)"
            >
                {{ roleIcon }} {{ roleLabel }}
            </span>
        </div>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    title: string
    roleIcon: string
    roleLabel: string
    isStreaming: boolean
    oralMode?: boolean
}>()

const emit = defineEmits<{ stop: [] }>()
</script>
