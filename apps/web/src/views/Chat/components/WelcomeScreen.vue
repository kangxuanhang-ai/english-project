<template>
    <!-- 口语考官欢迎页 -->
    <div v-if="isOral" class="flex-1 flex flex-col items-center justify-center p-10 relative overflow-hidden animate-fade-in-up oral-welcome">
        <div class="oral-welcome-bg absolute inset-0 pointer-events-none" />
        <div class="relative flex gap-1 mb-6 h-8 items-end">
            <span v-for="n in 5" :key="n" class="oral-bar" :style="{ animationDelay: `${n * 0.12}s` }" />
        </div>
        <h1 class="relative text-[38px] font-semibold mb-2 text-center text-teal-900" style="font-family: 'Source Serif 4', Georgia, serif;">
            Speaking Studio
        </h1>
        <p class="relative text-base text-teal-700/90 mb-1 text-center font-medium">Practice English like a real IELTS speaking test</p>
        <p class="relative text-xs text-teal-600/60 mb-10 text-center max-w-md">
            🎤 Voice input in English · 🔊 Examiner replies read aloud · ✓ Grammar coaching built-in
        </p>
        <div class="relative flex gap-4 flex-wrap justify-center">
            <div
                v-for="(card, i) in info.cards"
                :key="i"
                class="oral-scene-card group relative p-5 border border-teal-100 rounded-2xl cursor-pointer bg-white/90 transition-all duration-250 hover:-translate-y-1 animate-fade-in-card"
                :class="i === 0 ? 'w-[280px] ring-2 ring-teal-200/60' : 'w-[240px]'"
                :style="{ animationDelay: `${0.05 + i * 0.07}s` }"
                @click="handleCardClick(card)"
            >
                <span v-if="i === 0" class="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-100 text-teal-800">Start here</span>
                <div class="w-11 h-11 rounded-[14px] flex items-center justify-center text-[22px] mb-3.5 bg-linear-to-br from-teal-50 to-emerald-100 group-hover:scale-110 transition-transform">
                    {{ card.icon }}
                </div>
                <div class="text-sm font-semibold text-teal-950 mb-1">{{ card.title }}</div>
                <div class="text-xs text-teal-700/65 leading-relaxed">{{ card.desc }}</div>
            </div>
        </div>
    </div>

    <!-- 其他角色欢迎页 -->
    <div v-else class="flex-1 flex flex-col items-center justify-center p-10 relative overflow-hidden animate-fade-in-up">
        <div class="welcome-orb absolute inset-0 pointer-events-none" />
        <h1
            class="relative text-[36px] font-semibold mb-2 text-center"
            style="font-family: 'Source Serif 4', Georgia, serif; background: linear-gradient(135deg, #1c1917, var(--chat-accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text"
        >{{ info.greeting }}</h1>
        <p class="relative text-[15px] text-[#78716c] mb-2 text-center">{{ info.subtitle }}</p>
        <p class="relative text-xs text-[#a8a29e] mb-10 text-center">选择快捷卡片，或直接在下方输入</p>
        <div class="relative flex gap-4 flex-wrap justify-center">
            <div
                v-for="(card, i) in info.cards"
                :key="i"
                class="relative p-5 border border-gray-100 rounded-2xl cursor-pointer bg-white transition-all duration-250 group hover:-translate-y-[5px] animate-fade-in-card"
                :class="i === 0 ? 'w-[280px]' : 'w-[240px]'"
                :style="{
                    animationDelay: `${0.05 + i * 0.07}s`,
                    boxShadow: '0 1px 3px rgba(0,0,0,.04)',
                }"
                @click="handleCardClick(card)"
            >
                <span
                    v-if="i === 0"
                    class="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full"
                    style="background: var(--chat-accent-soft); color: var(--chat-accent-text); border: 1px solid var(--chat-accent-border)"
                >推荐</span>
                <div
                    class="w-11 h-11 rounded-[14px] flex items-center justify-center text-[22px] mb-3.5 transition-transform duration-250 group-hover:scale-110"
                    :class="iconBgClass(card.color)"
                >{{ card.icon }}</div>
                <div class="text-sm font-semibold text-gray-800 mb-1">{{ card.title }}</div>
                <div class="text-xs text-gray-400 leading-relaxed">{{ card.desc }}</div>
                <div
                    class="absolute bottom-0 left-0 right-0 h-[3px] rounded-b-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-250"
                    :style="{ background: 'linear-gradient(90deg, var(--chat-accent-light), var(--chat-accent))' }"
                />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { roleConfig, type RoleCard } from '../roleConfig'

const chatStore = useChatStore()
const isOral = computed(() => chatStore.activeRole === 'oral')

const emit = defineEmits<{
    selectCard: [placeholder: string, toggle?: 'deep' | 'web']
}>()

const info = computed(() => roleConfig[chatStore.activeRole])

function handleCardClick(card: RoleCard) {
    emit('selectCard', card.placeholder, card.toggle)
}

function iconBgClass(color: string) {
    const map: Record<string, string> = {
        purple: 'bg-gradient-to-br from-indigo-50 to-indigo-100',
        blue: 'bg-gradient-to-br from-blue-50 to-blue-100',
        green: 'bg-gradient-to-br from-green-50 to-green-100',
        pink: 'bg-gradient-to-br from-pink-50 to-pink-100',
        rose: 'bg-gradient-to-br from-rose-50 to-rose-100',
        amber: 'bg-gradient-to-br from-amber-50 to-amber-100',
        cyan: 'bg-gradient-to-br from-cyan-50 to-cyan-100',
        teal: 'bg-gradient-to-br from-teal-50 to-teal-100',
        orange: 'bg-gradient-to-br from-orange-50 to-orange-100',
    }
    return map[color] ?? map.purple
}
</script>

<style scoped>
.welcome-orb {
    background: radial-gradient(ellipse 60% 50% at 50% 40%, var(--chat-glow), transparent);
}
.oral-welcome-bg {
    background:
        radial-gradient(ellipse 55% 45% at 50% 35%, rgba(45, 212, 191, 0.18), transparent),
        radial-gradient(ellipse 40% 30% at 80% 70%, rgba(16, 185, 129, 0.1), transparent);
}
.oral-bar {
    display: block;
    width: 4px;
    height: 8px;
    border-radius: 999px;
    background: linear-gradient(180deg, #5eead4, #0d9488);
    animation: oral-wave 1.2s ease-in-out infinite;
}
@keyframes oral-wave {
    0%, 100% { height: 8px; opacity: 0.45; }
    50% { height: 28px; opacity: 1; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInCards {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up { animation: fadeInUp 0.4s ease; }
.animate-fade-in-card { animation: fadeInCards 0.4s ease both; }
</style>
