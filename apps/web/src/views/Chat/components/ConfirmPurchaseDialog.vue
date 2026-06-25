<template>
    <Teleport to="body">
        <Transition name="confirm-fade">
            <div v-if="modelValue" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
                <div class="absolute inset-0 bg-emerald-950/40 backdrop-blur-sm" aria-hidden="true" />
                <div
                    class="confirm-purchase relative w-full max-w-md rounded-2xl overflow-hidden shadow-2xl shadow-emerald-900/15 border border-emerald-200/80"
                    role="dialog"
                    aria-modal="true"
                >
                    <!-- 顶部色带 + 步骤 -->
                    <div class="confirm-purchase__hero px-6 pt-5 pb-5">
                        <div class="flex items-center gap-3">
                            <div class="confirm-purchase__icon" aria-hidden="true">🛒</div>
                            <div>
                                <h2 class="text-lg font-bold text-white tracking-tight">确认购买</h2>
                                <p class="mt-0.5 text-sm text-emerald-100/85">{{ subtitle }}</p>
                            </div>
                        </div>
                    </div>

                    <div v-if="course" class="bg-white px-6 py-5 space-y-4">
                        <div class="flex gap-4 rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
                            <div class="w-20 h-20 shrink-0 rounded-xl overflow-hidden bg-emerald-100 ring-2 ring-emerald-200/60">
                                <img :src="course.url" :alt="course.name" class="w-full h-full object-cover" />
                            </div>
                            <div class="min-w-0 flex-1">
                                <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-600 mb-1">待购课程</p>
                                <h3 class="text-sm font-semibold text-zinc-900 line-clamp-2">{{ course.name }}</h3>
                                <p class="mt-1 text-xs text-zinc-500">讲师 {{ course.teacher }}</p>
                            </div>
                        </div>

                        <div class="flex items-center justify-between rounded-xl border border-emerald-200 bg-linear-to-r from-emerald-50 to-teal-50 px-4 py-3">
                            <span class="text-sm font-medium text-emerald-900/70">应付金额</span>
                            <span class="text-2xl font-bold text-emerald-700">¥{{ course.price }}</span>
                        </div>

                        <div
                            v-if="recommendList.length"
                            class="rounded-xl border border-dashed border-emerald-200 bg-emerald-50/30 px-4 py-3 text-xs text-zinc-600 space-y-1.5"
                        >
                            <p class="font-semibold text-emerald-800">推荐列表 · 请核对序号</p>
                            <p
                                v-for="(title, i) in recommendList"
                                :key="i"
                                class="flex items-center gap-1.5"
                                :class="i + 1 === selectedIndex ? 'text-emerald-800 font-semibold' : ''"
                            >
                                <span
                                    class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
                                    :class="i + 1 === selectedIndex ? 'bg-emerald-600 text-white' : 'bg-emerald-100 text-emerald-700'"
                                >{{ i + 1 }}</span>
                                <span>{{ title }}</span>
                                <span v-if="i + 1 === selectedIndex" class="text-emerald-600">✓ 已选</span>
                            </p>
                        </div>

                        <p class="text-[11px] text-center text-zinc-400">
                            点击「确定购买」后将创建订单，下一步跳转支付宝完成支付
                        </p>
                    </div>

                    <div class="flex gap-3 px-6 pb-6 pt-1 bg-white">
                        <button
                            type="button"
                            class="flex-1 py-2.5 rounded-xl text-sm font-medium text-zinc-600 border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors"
                            :disabled="submitting"
                            @click="close"
                        >
                            再想想
                        </button>
                        <button
                            type="button"
                            class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-linear-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 transition-all shadow-md shadow-emerald-600/25 disabled:opacity-50"
                            :disabled="submitting"
                            @click="onConfirm"
                        >
                            {{ submitting ? '处理中...' : confirmLabel }}
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CourseBatchStatus } from '@en/common/course'
import type { ResultPay } from '@en/common/pay'
import { ElMessage } from 'element-plus'
import { createPay, resumePay } from '@/apis/pay'

const modelValue = defineModel<boolean>('modelValue', { required: true })
const props = defineProps<{
    course: CourseBatchStatus | null
    mode?: 'create' | 'resume'
    selectedIndex?: number
    recommendTitles?: string[]
}>()

const emit = defineEmits<{
    confirmed: [order: ResultPay]
    owned: [course: CourseBatchStatus]
}>()

const submitting = ref(false)

const subtitle = computed(() =>
    props.mode === 'resume'
        ? '有待支付订单，确认后继续'
        : '选好课程了吗？确认后将进入支付',
)

const confirmLabel = computed(() =>
    props.mode === 'resume' ? '继续下单' : '确定购买',
)

const selectedIndex = computed(() => props.selectedIndex ?? 0)
const recommendList = computed(() => props.recommendTitles ?? [])

const close = () => {
    if (submitting.value) return
    modelValue.value = false
}

const onConfirm = async () => {
    if (!props.course || submitting.value) return
    submitting.value = true
    try {
        if (props.mode === 'resume') {
            const res = await resumePay({ courseId: props.course.id })
            if (res.code === 200) {
                emit('confirmed', res.data)
                modelValue.value = false
                return
            }
            ElMessage.warning(res.message || '订单已过期，请重新购买')
            return
        }

        const body = {
            subject: props.course.name,
            body: props.course.description || '',
            total_amount: props.course.price,
            courseId: props.course.id,
        }
        const res = await createPay(body)
        if (res.code === 200) {
            emit('confirmed', res.data)
            modelValue.value = false
            return
        }
        const msg = res.message || '创建订单失败'
        if (msg.includes('未完成的支付订单')) {
            const resumeRes = await resumePay({ courseId: props.course.id })
            if (resumeRes.code === 200) {
                emit('confirmed', resumeRes.data)
                modelValue.value = false
                return
            }
            ElMessage.warning(resumeRes.message || '订单已过期，请重新购买')
            return
        }
        if (msg.includes('已经购买')) {
            modelValue.value = false
            ElMessage.info(msg)
            emit('owned', props.course)
            return
        }
        ElMessage.error(msg)
    } catch {
        ElMessage.error(props.mode === 'resume' ? '继续支付失败，请重试' : '创建订单失败，请重试')
    } finally {
        submitting.value = false
    }
}
</script>

<style scoped>
.confirm-purchase__hero {
    background: linear-gradient(135deg, #059669 0%, #0d9488 45%, #047857 100%);
}

.confirm-purchase__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.75rem;
    height: 2.75rem;
    border-radius: 0.875rem;
    font-size: 1.35rem;
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.25);
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
    transition: opacity 0.2s ease;
}
.confirm-fade-enter-from,
.confirm-fade-leave-to {
    opacity: 0;
}
</style>
