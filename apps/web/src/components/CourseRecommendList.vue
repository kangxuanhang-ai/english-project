<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { CourseBatchStatus } from '@en/common/course';
import type { CourseRecommendation } from '@/apis/recommend';
import { getCourseBatchStatus } from '@/apis/course';
import { ElMessage } from 'element-plus';

const props = defineProps<{
    courses: CourseRecommendation[];
}>();

const emit = defineEmits<{
    buy: [course: CourseBatchStatus];
    learn: [course: CourseBatchStatus];
}>();

const statusMap = ref<Map<string, CourseBatchStatus>>(new Map());
const loading = ref(false);
const loadFailed = ref(false);

async function loadStatus() {
    const ids = props.courses
        .map((c) => c.course_id)
        .filter((id): id is string => !!id);
    if (!ids.length) return;

    loading.value = true;
    loadFailed.value = false;
    try {
        const res = await getCourseBatchStatus(ids);
        if (res.code === 200) {
            statusMap.value = new Map(res.data.items.map((item) => [item.id, item]));
        } else {
            loadFailed.value = true;
            ElMessage.error('加载购课状态失败');
        }
    } catch {
        loadFailed.value = true;
        ElMessage.error('加载购课状态失败，请重试');
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    void loadStatus();
});

defineExpose({ reload: loadStatus });

const getStatus = (courseId: string | null) => {
    if (!courseId) return null;
    return statusMap.value.get(courseId) ?? null;
};
</script>

<template>
    <div v-if="loadFailed" class="mb-3 text-xs text-amber-700 flex items-center justify-between gap-2">
        <span>购课状态加载失败</span>
        <button type="button" class="text-indigo-600 hover:text-indigo-500 font-medium" @click="loadStatus">重试</button>
    </div>
    <div v-for="(course, index) in courses" :key="course.course_id ?? index" class="mb-4 last:mb-0">
        <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-zinc-800">{{ course.title }}</p>
                <p class="text-xs text-zinc-500 mt-1">{{ course.reason }}</p>
                <p v-if="course.match_score" class="text-[10px] text-indigo-400 mt-1">
                    匹配度 {{ Math.round(course.match_score * 100) }}%
                </p>
            </div>
            <template v-if="getStatus(course.course_id)">
                <button
                    v-if="getStatus(course.course_id)!.purchased"
                    type="button"
                    class="ml-3 px-3 py-1.5 text-xs bg-indigo-500 text-white rounded-full hover:bg-indigo-600 transition-colors cursor-pointer shrink-0"
                    @click="emit('learn', getStatus(course.course_id)!)"
                >
                    立即学习
                </button>
                <button
                    v-else
                    type="button"
                    class="ml-3 px-3 py-1.5 text-xs bg-indigo-500 text-white rounded-full hover:bg-indigo-600 transition-colors cursor-pointer shrink-0"
                    :disabled="loading"
                    @click="emit('buy', getStatus(course.course_id)!)"
                >
                    立即购买 ¥{{ getStatus(course.course_id)!.price }}
                </button>
            </template>
            <span v-else-if="loading" class="text-xs text-zinc-400 shrink-0">加载中…</span>
        </div>
    </div>
</template>
