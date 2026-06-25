<template>
    <Teleport to="body">
        <Transition name="pay-fade">
            <div v-if="modelValue" class="fixed inset-0 z-[55] flex items-center justify-center p-4">
                <!-- 遮罩 -->
                <div class="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm" aria-hidden="true" />

                <!-- 弹框 -->
                <div class="relative w-full max-w-md rounded-2xl bg-white shadow-xl shadow-indigo-500/10 border border-zinc-100 overflow-hidden"
                    role="dialog" aria-modal="true" aria-labelledby="pay-dialog-title">
                    <!-- 标题 -->
                    <div class="px-6 pt-6 pb-4 border-b border-zinc-100">
                        <h2 id="pay-dialog-title" class="text-lg font-semibold text-zinc-900">确认支付</h2>
                        <p class="mt-1 text-sm text-zinc-500">请核对课程信息后完成支付</p>
                    </div>
                    <!-- 课程信息（有 course 时展示） -->
                    <div v-if="course" class="p-6 space-y-4">
                        <div class="flex gap-4 rounded-xl bg-zinc-50/80 p-4">
                            <div class="w-20 h-20 shrink-0 rounded-lg overflow-hidden bg-zinc-200">
                                <img :src="imageSrc(course.url)" :alt="course.name"
                                    class="w-full h-full object-cover" />
                            </div>
                            <div class="min-w-0 flex-1">
                                <h3 class="text-sm font-medium text-zinc-900 line-clamp-2">{{ course.name }}</h3>
                                <p class="mt-1 text-xs text-zinc-500">讲师 {{ course.teacher }}</p>
                            </div>
                        </div>
                        <div
                            class="flex items-center justify-between rounded-xl border border-zinc-100 bg-indigo-50/50 px-4 py-3">
                            <span class="text-sm text-zinc-600">支付金额</span>
                            <span class="text-xl font-bold text-indigo-600">¥{{ course.price }}</span>
                        </div>
                        <!-- 支付剩余时间倒计时（点击确认支付后显示） -->
                        <div v-if="isPay && timeExpire > 0"
                            class="flex flex-col items-center rounded-xl border border-amber-100 bg-amber-50/50 px-4 py-3">
                            <el-countdown title="支付剩余时间" format="HH:mm:ss" :value="timeExpire" @finish="tips" />
                            <p class="mt-2 text-xs text-amber-700/80">支付完成后将自动确认，也可切回本页等待</p>
                        </div>
                    </div>

                    <!-- 无数据时的占位 -->
                    <div v-else class="p-6 text-center text-sm text-zinc-400">
                        暂无课程信息
                    </div>

                    <!-- 底部按钮 -->
                    <div class="flex gap-3 px-6 pb-6 pt-2">
                        <button type="button"
                            class="flex-1 py-2.5 rounded-xl text-sm font-medium text-zinc-600 border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors"
                            @click="close">
                            取消
                        </button>
                        <button type="button"
                            class="flex-1 py-2.5 rounded-xl text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="isPay" @click="onConfirm">
                            {{ isPay ? '支付中...' : '确认支付' }}
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>


<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import type { Course } from '@en/common/course';
import { ElMessage } from 'element-plus';
import type { CreatePayDto, ResultPay } from '@en/common/pay';
import { createPay, syncPay } from '@/apis/pay';
import { useSocket } from '@/hooks/useSocket';
import { useTracker } from '@/hooks/useTracker';

const emit = defineEmits<{ success: [] }>();
const { getSocket } = useSocket();
const tracker = useTracker();
const modelValue = defineModel<boolean>('modelValue', { required: true });
const props = defineProps<{
    course: Course | null;
    /** 聊天购课：订单已创建，本弹框仅跳转支付宝 */
    preCreatedOrder?: ResultPay | null;
}>();
const isPay = ref(false);
const timeExpire = ref(0);
const outTradeNo = ref('');
const paymentHandled = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;
let syncing = false;

const stopPolling = () => {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
};

const detachPayListeners = () => {
    getSocket()?.off('paymentSuccess', showPaySuccess);
    document.removeEventListener('visibilitychange', onVisibilityChange);
};

const showPaySuccess = (payload?: string | { userId?: string; courseId?: string; outTradeNo?: string }) => {
    if (paymentHandled.value) return;

    // 兼容旧版仅传 userId 字符串；新版校验订单与课程
    if (payload && typeof payload === 'object') {
        if (payload.outTradeNo && outTradeNo.value && payload.outTradeNo !== outTradeNo.value) {
            return;
        }
        if (payload.courseId && props.course?.id && payload.courseId !== props.course.id) {
            return;
        }
    }

    paymentHandled.value = true;
    stopPolling();
    detachPayListeners();
    isPay.value = false;

    ElMessage.success({
        message: '支付成功',
        duration: 3000,
    });
    void tracker.trackEvent('pay_success', {
        courseId: props.course?.id,
        courseName: props.course?.name,
    });
    emit('success');
    close();
};

const checkPaymentStatus = async () => {
    if (!outTradeNo.value || paymentHandled.value || syncing) return;
    syncing = true;
    try {
        const res = await syncPay({ outTradeNo: outTradeNo.value });
        if (res.code === 200 && res.data.paid) {
            showPaySuccess();
        }
    } catch {
        // 轮询失败时静默重试
    } finally {
        syncing = false;
    }
};

const startPolling = () => {
    stopPolling();
    if (!outTradeNo.value) return;
    void checkPaymentStatus();
    pollTimer = setInterval(() => {
        void checkPaymentStatus();
    }, 3000);
};

const onVisibilityChange = () => {
    if (document.visibilityState === 'visible' && outTradeNo.value && timeExpire.value > Date.now()) {
        void checkPaymentStatus();
    }
};

watch(modelValue, (visible) => {
    const socket = getSocket();
    if (visible) {
        paymentHandled.value = false;
        socket?.on('paymentSuccess', showPaySuccess);
        document.addEventListener('visibilitychange', onVisibilityChange);
    } else {
        detachPayListeners();
        stopPolling();
    }
});

onBeforeUnmount(() => {
    stopPolling();
    detachPayListeners();
});

const imageSrc = (url: string) => {
    return url;
}

const tips = () => {
    ElMessage.error('支付超时，请重新支付');
    timeExpire.value = 0;
    isPay.value = false;
    stopPolling();
}

const close = () => {
    modelValue.value = false;
    timeExpire.value = 0;
    isPay.value = false;
    outTradeNo.value = '';
    stopPolling();
}

const onConfirm = async () => {
    if (isPay.value) return
    if (props.preCreatedOrder) {
        isPay.value = true;
        paymentHandled.value = false;
        window.open(props.preCreatedOrder.payUrl, '_blank');
        outTradeNo.value = props.preCreatedOrder.outTradeNo;
        timeExpire.value = props.preCreatedOrder.timeExpire;
        startPolling();
        return;
    }
    try {
        isPay.value = true;
        paymentHandled.value = false;
        const body: CreatePayDto = {
            subject: props.course?.name || '',
            body: props.course?.description || '',
            total_amount: props.course?.price || '',
            courseId: props.course?.id || '',
        }
        const res = await createPay(body);
        if (res.code === 200) {
            window.open(res.data.payUrl, '_blank');
            outTradeNo.value = res.data.outTradeNo;
            timeExpire.value = res.data.timeExpire;
            startPolling();
            // 订单已创建，保持 isPay 直至支付成功/超时/关闭
        } else {
            ElMessage.error(res.message);
            isPay.value = false;
        }
    } catch (error) {
        ElMessage.error('创建支付订单失败');
        isPay.value = false;
    }
}
</script>

<style scoped>
.pay-fade-enter-active,
.pay-fade-leave-active {
    transition: opacity 0.2s ease;
}

.pay-fade-enter-from,
.pay-fade-leave-to {
    opacity: 0;
}
</style>
