<!-- apps/web/src/components/RecommendCard.vue -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { getRecommend, type RecommendData } from '@/apis/recommend';
import CourseRecommendList from '@/components/CourseRecommendList.vue';
import type { CourseBatchStatus } from '@en/common/course';

const props = defineProps<{
    compact?: boolean;
}>();

const emit = defineEmits<{
    buy: [course: CourseBatchStatus];
    learn: [course: CourseBatchStatus];
}>();

const loading = ref(true);
const data = ref<RecommendData | null>(null);
const error = ref(false);

const cardMinHeight = computed(() => (props.compact ? '80px' : '160px'));

const fetchRecommend = async (force = false) => {
    loading.value = true;
    error.value = false;
    try {
        const res = await getRecommend(force);
        data.value = res.data;
    } catch (e) {
        console.error('获取推荐失败:', e);
        error.value = true;
    } finally {
        loading.value = false;
    }
};

const handleRefresh = () => fetchRecommend(true);

defineExpose({ reload: () => fetchRecommend(true) });

onMounted(() => fetchRecommend());
</script>

<template>
    <!-- 加载中 -->
    <div
        v-if="loading"
        class="recommend-card recommend-card--loading bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm bg-indigo-50/30"
        :style="{ minHeight: cardMinHeight }"
    >
        <div class="flex items-center justify-between mb-3">
            <h3 class="text-base font-semibold text-zinc-900">🎯 AI 学习推荐</h3>
            <span class="text-xs text-indigo-500 analyzing-dots">分析中</span>
        </div>
        <p class="text-xs text-zinc-500 mb-4">正在根据你的学习进度生成个性化推荐…</p>

        <div class="flex items-start justify-between mb-4">
            <div class="flex-1 space-y-2">
                <div class="shimmer-bar h-4 rounded w-2/5"></div>
                <div class="shimmer-bar h-3 rounded w-full"></div>
            </div>
            <div class="shimmer-bar h-6 rounded-full w-16 ml-3 shrink-0"></div>
        </div>

        <div v-if="!props.compact" class="flex items-start justify-between mb-4">
            <div class="flex-1 space-y-2">
                <div class="shimmer-bar h-4 rounded w-1/3"></div>
                <div class="shimmer-bar h-3 rounded w-4/5"></div>
            </div>
            <div class="shimmer-bar h-6 rounded-full w-16 ml-3 shrink-0"></div>
        </div>

        <div v-if="!props.compact" class="pt-4 border-t border-zinc-100">
            <div class="shimmer-bar h-3 rounded w-24 mb-3"></div>
            <div class="space-y-2">
                <div class="shimmer-bar h-3 rounded w-full"></div>
                <div class="shimmer-bar h-3 rounded w-5/6"></div>
            </div>
        </div>
    </div>

    <!-- 错误/无数据 -->
    <div
        v-else-if="error || !data"
        class="recommend-card bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm flex flex-col items-center justify-center text-center"
        :style="{ minHeight: cardMinHeight }"
    >
        <p class="text-zinc-400 text-sm mb-3">{{ error ? '加载失败，请稍后重试' : '暂无推荐，请先开始学习' }}</p>
        <button
            v-if="error"
            @click="fetchRecommend()"
            class="text-xs text-indigo-500 hover:text-indigo-600 transition-colors cursor-pointer"
        >
            重试
        </button>
    </div>

    <!-- 正常展示 -->
    <div v-else class="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-zinc-900">🎯 AI 学习推荐</h3>
            <button
                @click="handleRefresh"
                class="text-xs text-indigo-500 hover:text-indigo-600 transition-colors cursor-pointer"
            >
                换一批
            </button>
        </div>

        <CourseRecommendList
            :courses="data.courses"
            @buy="(c) => emit('buy', c)"
            @learn="(c) => emit('learn', c)"
        />

        <div v-if="!props.compact && data.daily_plan" class="mt-4 pt-4 border-t border-zinc-100">
            <p class="text-xs font-medium text-zinc-700 mb-2">📋 今日学习计划</p>
            <ul class="text-xs text-zinc-500 space-y-1">
                <li>· 每日新学 {{ data.daily_plan.new_words_per_day }} 个单词</li>
                <li>· {{ data.daily_plan.review_frequency }}</li>
                <li>· 预计 {{ data.daily_plan.estimated_completion }} 完成</li>
            </ul>
        </div>

        <p v-if="data.summary" class="text-xs text-zinc-400 mt-3 line-clamp-2">{{ data.summary }}</p>
    </div>
</template>

<style scoped>
.recommend-card--loading {
    animation: fadeIn 150ms ease forwards;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.shimmer-bar {
    background: linear-gradient(90deg, rgb(228 228 231) 0%, rgb(244 244 245) 50%, rgb(228 228 231) 100%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.analyzing-dots::after {
    content: '.';
    animation: dots 1.5s steps(1, end) infinite;
}

@keyframes dots {
    0%, 20% { content: '.'; }
    40% { content: '..'; }
    60%, 100% { content: '...'; }
}
</style>
