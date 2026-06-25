<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ChatRecommendBlock } from '@en/common/chat'
import type { CourseBatchStatus } from '@en/common/course'
import { getCourseBatchStatus } from '@/apis/course'
import { ElMessage } from 'element-plus'

const props = defineProps<{
    data: ChatRecommendBlock
}>()

const emit = defineEmits<{
    buy: [course: CourseBatchStatus]
    learn: [course: CourseBatchStatus]
}>()

const statusMap = ref<Map<string, CourseBatchStatus>>(new Map())
const loading = ref(false)
const loadFailed = ref(false)

async function loadStatus() {
    const ids = props.data.courses
        .map((c) => c.course_id)
        .filter((id): id is string => !!id)
    if (!ids.length) return

    loading.value = true
    loadFailed.value = false
    try {
        const res = await getCourseBatchStatus(ids)
        if (res.code === 200) {
            statusMap.value = new Map(res.data.items.map((item) => [item.id, item]))
        } else {
            loadFailed.value = true
            ElMessage.error('加载购课状态失败')
        }
    } catch {
        loadFailed.value = true
        ElMessage.error('加载购课状态失败，请重试')
    } finally {
        loading.value = false
    }
}

onMounted(() => {
    void loadStatus()
})

const getStatus = (courseId: string | null) => {
    if (!courseId) return null
    return statusMap.value.get(courseId) ?? null
}

const formatScore = (score: number) => Math.round(score * 100)

const planChips = computed(() => {
    const plan = props.data.daily_plan
    if (!plan) return []
    const eta = (plan.estimated_completion ?? '').replace(/^预计\s*/, '')
    return [
        { icon: '📖', text: `每日 ${plan.new_words_per_day} 词` },
        { icon: '🔁', text: plan.review_frequency },
        ...(eta ? [{ icon: '⏱️', text: eta }] : []),
    ]
})
</script>

<template>
    <div class="chat-recommend-block">
        <div class="chat-recommend-block__header">
            <div class="chat-recommend-block__header-icon">🎯</div>
            <div>
                <p class="chat-recommend-block__title">为你推荐</p>
                <p class="chat-recommend-block__subtitle">根据你的学习进度智能匹配</p>
            </div>
        </div>

        <div
            v-if="loadFailed"
            class="chat-recommend-block__alert"
        >
            <span>购课状态加载失败</span>
            <button type="button" class="chat-recommend-block__retry" @click="loadStatus">重试</button>
        </div>

        <ul class="chat-recommend-block__list">
            <li
                v-for="(course, index) in data.courses"
                :key="course.course_id ?? index"
                class="chat-recommend-block__item"
                :class="{ 'chat-recommend-block__item--featured': index === 0 }"
            >
                <div class="chat-recommend-block__item-top">
                    <div class="chat-recommend-block__rank">{{ index + 1 }}</div>
                    <div class="chat-recommend-block__body">
                        <div class="chat-recommend-block__title-row">
                            <p class="chat-recommend-block__course-title">{{ course.title }}</p>
                            <span v-if="index === 0" class="chat-recommend-block__badge">首推</span>
                        </div>
                        <div class="chat-recommend-block__score-row">
                            <div class="chat-recommend-block__score-track">
                                <div
                                    class="chat-recommend-block__score-fill"
                                    :style="{ width: `${formatScore(course.match_score)}%` }"
                                />
                            </div>
                            <span class="chat-recommend-block__score-label">匹配 {{ formatScore(course.match_score) }}%</span>
                        </div>
                        <p class="chat-recommend-block__reason">{{ course.reason }}</p>
                    </div>
                </div>

                <div class="chat-recommend-block__action">
                    <template v-if="getStatus(course.course_id)">
                        <button
                            v-if="getStatus(course.course_id)!.purchased"
                            type="button"
                            class="chat-recommend-block__btn chat-recommend-block__btn--learn"
                            @click="emit('learn', getStatus(course.course_id)!)"
                        >
                            去学习
                        </button>
                        <button
                            v-else
                            type="button"
                            class="chat-recommend-block__btn chat-recommend-block__btn--buy"
                            :disabled="loading"
                            @click="emit('buy', getStatus(course.course_id)!)"
                        >
                            <span class="chat-recommend-block__btn-price">¥{{ getStatus(course.course_id)!.price }}</span>
                            <span>立即购买</span>
                        </button>
                    </template>
                    <div v-else-if="loading" class="chat-recommend-block__btn-skeleton" />
                </div>
            </li>
        </ul>

        <div v-if="planChips.length" class="chat-recommend-block__footer">
            <span
                v-for="(chip, i) in planChips"
                :key="i"
                class="chat-recommend-block__chip"
            >
                <span class="chat-recommend-block__chip-icon">{{ chip.icon }}</span>
                {{ chip.text }}
            </span>
        </div>
    </div>
</template>

<style scoped>
.chat-recommend-block {
    margin-top: 1rem;
    border-radius: 16px;
    overflow: hidden;
    background: #fff;
    border: 1px solid color-mix(in srgb, var(--chat-accent-border) 70%, transparent);
    box-shadow:
        0 1px 2px rgba(15, 23, 42, 0.04),
        0 8px 24px -8px color-mix(in srgb, var(--chat-accent) 18%, transparent);
}

.chat-recommend-block__header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 1rem;
    background: linear-gradient(
        135deg,
        color-mix(in srgb, var(--chat-accent-soft) 90%, #fff) 0%,
        #fff 100%
    );
    border-bottom: 1px solid color-mix(in srgb, var(--chat-accent-border) 50%, transparent);
}

.chat-recommend-block__header-icon {
    width: 2.25rem;
    height: 2.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    font-size: 1.125rem;
    background: #fff;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--chat-accent) 12%, transparent);
}

.chat-recommend-block__title {
    font-size: 0.8125rem;
    font-weight: 700;
    color: var(--chat-accent-text);
    line-height: 1.2;
}

.chat-recommend-block__subtitle {
    margin-top: 0.125rem;
    font-size: 0.6875rem;
    color: #a8a29e;
    line-height: 1.2;
}

.chat-recommend-block__alert {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    font-size: 0.6875rem;
    color: #b45309;
    background: #fffbeb;
    border-bottom: 1px solid #fde68a;
}

.chat-recommend-block__retry {
    font-weight: 600;
    color: var(--chat-accent);
    cursor: pointer;
}

.chat-recommend-block__retry:hover {
    opacity: 0.85;
}

.chat-recommend-block__list {
    list-style: none;
    margin: 0;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
}

.chat-recommend-block__item {
    padding: 0.875rem;
    border-radius: 12px;
    background: #fafaf9;
    border: 1px solid #f5f5f4;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-recommend-block__item--featured {
    background: linear-gradient(
        160deg,
        color-mix(in srgb, var(--chat-accent-soft) 55%, #fff) 0%,
        #fff 55%
    );
    border-color: color-mix(in srgb, var(--chat-accent-border) 80%, transparent);
    box-shadow: 0 4px 14px -6px color-mix(in srgb, var(--chat-accent) 22%, transparent);
}

.chat-recommend-block__item-top {
    display: flex;
    gap: 0.75rem;
}

.chat-recommend-block__rank {
    flex-shrink: 0;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.6875rem;
    font-weight: 700;
    color: #fff;
    background: var(--chat-accent-light);
}

.chat-recommend-block__item--featured .chat-recommend-block__rank {
    background: linear-gradient(145deg, var(--chat-accent-light), var(--chat-accent));
}

.chat-recommend-block__body {
    flex: 1;
    min-width: 0;
}

.chat-recommend-block__title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.chat-recommend-block__course-title {
    font-size: 0.875rem;
    font-weight: 700;
    color: #292524;
    line-height: 1.3;
}

.chat-recommend-block__badge {
    font-size: 0.625rem;
    font-weight: 700;
    padding: 0.125rem 0.4375rem;
    border-radius: 999px;
    color: var(--chat-accent-text);
    background: color-mix(in srgb, var(--chat-accent-soft) 80%, #fff);
    border: 1px solid color-mix(in srgb, var(--chat-accent-border) 60%, transparent);
}

.chat-recommend-block__score-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.chat-recommend-block__score-track {
    flex: 1;
    height: 4px;
    border-radius: 999px;
    background: #e7e5e4;
    overflow: hidden;
}

.chat-recommend-block__score-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--chat-accent-light), var(--chat-accent));
    transition: width 0.4s ease;
}

.chat-recommend-block__score-label {
    flex-shrink: 0;
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--chat-accent-text);
    white-space: nowrap;
}

.chat-recommend-block__reason {
    margin-top: 0.5rem;
    font-size: 0.75rem;
    line-height: 1.55;
    color: #78716c;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.chat-recommend-block__action {
    margin-top: 0.75rem;
    padding-left: 2.25rem;
}

.chat-recommend-block__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    min-width: 6.5rem;
    padding: 0.4375rem 1rem;
    border: none;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
    background: linear-gradient(145deg, var(--chat-accent-light), var(--chat-accent));
    box-shadow: 0 4px 12px -4px color-mix(in srgb, var(--chat-accent) 45%, transparent);
}

.chat-recommend-block__btn:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px -4px color-mix(in srgb, var(--chat-accent) 50%, transparent);
}

.chat-recommend-block__btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.chat-recommend-block__btn--learn {
    background: linear-gradient(145deg, var(--chat-accent), var(--chat-accent-dark));
}

.chat-recommend-block__btn-price {
    font-weight: 700;
    opacity: 0.95;
}

.chat-recommend-block__btn-skeleton {
    height: 2rem;
    width: 6.5rem;
    border-radius: 999px;
    background: linear-gradient(90deg, #f5f5f4 0%, #e7e5e4 50%, #f5f5f4 100%);
    background-size: 200% 100%;
    animation: recommend-shimmer 1.4s ease-in-out infinite;
}

.chat-recommend-block__footer {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
    padding: 0.625rem 1rem 0.875rem;
    border-top: 1px solid #f5f5f4;
    background: #fafaf9;
}

.chat-recommend-block__chip {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.3125rem 0.625rem;
    border-radius: 999px;
    font-size: 0.6875rem;
    color: #57534e;
    background: #fff;
    border: 1px solid #e7e5e4;
    line-height: 1.3;
}

.chat-recommend-block__chip-icon {
    font-size: 0.75rem;
    line-height: 1;
}

@keyframes recommend-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
</style>
