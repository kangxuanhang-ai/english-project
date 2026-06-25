<template>
    <div
        class="chat-shell relative w-[1200px] mx-auto flex my-4 rounded-[24px] overflow-hidden bg-white shadow-[0_0_0_1px_rgba(0,0,0,.04),0_12px_40px_rgba(0,0,0,.08)]"
        :class="{ 'chat-shell--oral': chatStore.activeRole === 'oral' }"
        :style="{ ...themeVars, height: 'calc(100vh - 96px)', minHeight: '680px' }"
    >
        <RoleSwitchBanner />
        <RoleList />
        <ConversationList />
        <ChatArea
            @recommend-buy="onRecommendBuy"
            @recommend-learn="onRecommendLearn"
            @purchase-confirm="onPurchaseConfirm"
            @purchase-learn="onPurchaseLearn"
        />
    </div>
    <ConfirmPurchaseDialog
        v-model="confirmVisible"
        :course="confirmCourse"
        :mode="confirmMode"
        :selected-index="confirmSelectedIndex"
        :recommend-titles="confirmRecommendTitles"
        @confirmed="onOrderCreated"
        @owned="onPurchaseLearn"
    />
    <CoursePay
        v-model="payVisible"
        :course="selectedCourse"
        :pre-created-order="preCreatedOrder"
        @success="onPaySuccess"
    />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import RoleList from './components/RoleList.vue'
import ConversationList from './components/ConversationList.vue'
import ChatArea from './components/ChatArea.vue'
import RoleSwitchBanner from './components/RoleSwitchBanner.vue'
import ConfirmPurchaseDialog from './components/ConfirmPurchaseDialog.vue'
import CoursePay from '@/views/Course/components/Pay.vue'
import { roleThemeVars } from './roleConfig'
import type { ChatPurchaseBlock, ChatRoleType } from '@en/common/chat'
import type { Course } from '@en/common/course'
import type { CourseBatchStatus } from '@en/common/course'
import type { ResultPay } from '@en/common/pay'
import { useCourseAction } from '@/hooks/useCourseAction'
import { syncLearningToAi } from '@/utils/learningSync'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const { goLearn, toCourse } = useCourseAction()
const payVisible = ref(false)
const confirmVisible = ref(false)
const confirmMode = ref<'create' | 'resume'>('create')
const selectedCourse = ref<Course | null>(null)
const confirmCourse = ref<CourseBatchStatus | null>(null)
const confirmSelectedIndex = ref<number | undefined>(undefined)
const confirmRecommendTitles = ref<string[]>([])
const preCreatedOrder = ref<ResultPay | null>(null)

const themeVars = computed(() => roleThemeVars(chatStore.activeRole))

const VALID_ROLES: ChatRoleType[] = ['normal', 'master', 'business', 'qilinge', 'xiaoman', 'oral']

const openConfirmPurchase = (
    course: CourseBatchStatus,
    mode: 'create' | 'resume' = 'create',
    meta?: Pick<ChatPurchaseBlock, 'selectedIndex' | 'recommendTitles'>,
) => {
    payVisible.value = false
    preCreatedOrder.value = null
    confirmCourse.value = course
    confirmMode.value = mode
    confirmSelectedIndex.value = meta?.selectedIndex
    confirmRecommendTitles.value = meta?.recommendTitles ?? []
    confirmVisible.value = true
}

const openPayWithOrder = (course: CourseBatchStatus, order: ResultPay) => {
    confirmVisible.value = false
    selectedCourse.value = toCourse(course)
    preCreatedOrder.value = order
    payVisible.value = true
}

const onRecommendBuy = (c: CourseBatchStatus) => {
    openConfirmPurchase(c, 'create')
}

const onRecommendLearn = (c: CourseBatchStatus) => {
    goLearn(c)
}

const onPurchaseLearn = (c: CourseBatchStatus) => {
    goLearn(c)
}

const onPurchaseConfirm = (block: ChatPurchaseBlock) => {
    if (!block.course) return
    const mode = block.action === 'resume_pay' ? 'resume' : 'create'
    openConfirmPurchase(block.course, mode, {
        selectedIndex: block.selectedIndex,
        recommendTitles: block.recommendTitles,
    })
}

const onOrderCreated = (order: ResultPay) => {
    if (!confirmCourse.value) return
    openPayWithOrder(confirmCourse.value, order)
}

const onPaySuccess = () => {
    preCreatedOrder.value = null
    void syncLearningToAi()
}

watch(payVisible, (visible) => {
    if (!visible) {
        preCreatedOrder.value = null
    }
})

onMounted(async () => {
    const role = route.params.role as string
    const conversationId = route.params.conversationId as string | undefined
    if (!role || !VALID_ROLES.includes(role as ChatRoleType)) { router.replace('/chat/normal'); return }
    await chatStore.setRole(role as ChatRoleType)
    if (conversationId) {
        if (chatStore.conversations.some(c => c.id === conversationId)) {
            chatStore.setConversation(conversationId)
        } else {
            router.replace(`/chat/${role}`)
        }
    }
})
</script>

<style>
@import '@/assets/css/chat-theme.css';
</style>
