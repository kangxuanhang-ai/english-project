<template>
    <div class="oral-studio-banner mx-5 mt-3 mb-1 shrink-0">
        <div class="relative overflow-hidden rounded-2xl border border-teal-200/60 bg-linear-to-r from-teal-50/90 via-white/80 to-emerald-50/90 px-4 py-3 shadow-sm">
            <div class="absolute inset-0 oral-wave-bg pointer-events-none opacity-40" />
            <div class="relative flex flex-wrap items-center justify-between gap-3">
                <div class="flex items-center gap-3 min-w-0">
                    <div class="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-teal-400 to-emerald-600 text-white text-lg shadow-md shadow-teal-500/30">
                        🎙️
                        <span class="oral-live-dot absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-white" />
                    </div>
                    <div class="min-w-0">
                        <p class="text-sm font-bold text-teal-900 tracking-tight">Speaking Studio</p>
                        <p class="text-[11px] text-teal-700/70 truncate">英文对话 · 语音输入 · 自动朗读 · 按需语法纠错</p>
                    </div>
                </div>
                <div class="flex flex-wrap gap-1.5">
                    <span class="oral-pill">🎤 英文语音输入</span>
                    <span class="oral-pill">🔊 回复自动朗读</span>
                    <span class="oral-pill">✓ 语法纠错（按需）</span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.oral-wave-bg {
    background: repeating-linear-gradient(
        90deg,
        transparent,
        transparent 8px,
        rgba(45, 212, 191, 0.08) 8px,
        rgba(45, 212, 191, 0.08) 10px
    );
    animation: wave-slide 12s linear infinite;
}
@keyframes wave-slide {
    from { transform: translateX(0); }
    to { transform: translateX(-40px); }
}
.oral-live-dot {
    animation: live-pulse 2s ease-in-out infinite;
}
@keyframes live-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.7; transform: scale(1.15); }
}
.oral-pill {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 600;
    color: #115e59;
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid rgba(153, 246, 228, 0.9);
    white-space: nowrap;
}
</style>
