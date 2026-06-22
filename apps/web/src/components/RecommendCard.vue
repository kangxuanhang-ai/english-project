<!-- apps/web/src/components/RecommendCard.vue -->
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getRecommend, type RecommendData } from '@/apis/recommend';

const props = defineProps<{
    /** 精简模式（首页用） */
    compact?: boolean;
}>();

const router = useRouter();
const loading = ref(true);
const data = ref<RecommendData | null>(null);
const error = ref(false);

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

const handleStartLearn = (courseId: string | null) => {
    if (courseId) {
        router.push({ path: '/course', query: { id: courseId } });
    } else {
        router.push('/course');
    }
};

onMounted(() => fetchRecommend());
</script>

<template>
    <!-- 加载中 -->
    <div v-if="loading" class="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm animate-pulse">
        <div class="h-5 bg-zinc-200 rounded w-32 mb-4"></div>
        <div class="h-4 bg-zinc-100 rounded w-full mb-2"></div>
        <div class="h-4 bg-zinc-100 rounded w-3/4"></div>
    </div>

    <!-- 错误/无数据 -->
    <div v-else-if="error || !data" class="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm text-center">
        <p class="text-zinc-400 text-sm mb-3">{{ error ? '加载失败' : '暂无推荐，请先开始学习' }}</p>
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

        <!-- 推荐课程 -->
        <div v-for="(course, index) in data.courses" :key="course.course_id ?? index" class="mb-4 last:mb-0">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <p class="text-sm font-medium text-zinc-800">{{ course.title }}</p>
                    <p class="text-xs text-zinc-500 mt-1">{{ course.reason }}</p>
                </div>
                <button
                    @click="handleStartLearn(course.course_id)"
                    class="ml-3 px-3 py-1 text-xs bg-indigo-500 text-white rounded-full hover:bg-indigo-600 transition-colors cursor-pointer shrink-0"
                >
                    开始学习
                </button>
            </div>
        </div>

        <!-- 学习计划（完整模式） -->
        <div v-if="!props.compact && data.daily_plan" class="mt-4 pt-4 border-t border-zinc-100">
            <p class="text-xs font-medium text-zinc-700 mb-2">📋 今日学习计划</p>
            <ul class="text-xs text-zinc-500 space-y-1">
                <li>· 每日新学 {{ data.daily_plan.new_words_per_day }} 个单词</li>
                <li>· {{ data.daily_plan.review_frequency }}</li>
                <li>· 预计 {{ data.daily_plan.estimated_completion }} 完成</li>
            </ul>
        </div>

        <!-- 总结 -->
        <p v-if="data.summary" class="text-xs text-zinc-400 mt-3 line-clamp-2">{{ data.summary }}</p>
    </div>
</template>
