<template>
    <div class="w-[1200px] mx-auto mt-10 pb-30">
        <!-- 背景区域 -->
        <div class="relative flex justify-between rounded-[20px] p-9">
            <div class="absolute inset-0 bg-linear-to-r from-gray-900 via-gray-900 to-gray-900/70 rounded-[20px]" />
            <div class="relative z-8 p-8">
                <span class="text-white text-1xl bg-indigo-500/20 rounded-[100px] px-4 py-2">坚持5天打卡学习</span>
                <div class="text-2xl font-bold pt-8 text-l text-indigo-500">通过跟AI对话，提高你的英语水平</div>
                <div class="text-1xl font-bold pt-5 text-gray-300">超1000000学员的选择，提升您的英语能力</div>
                <div class="flex items-center gap-2 pt-10">
                    <button
                        @click="showLogin"
                        class="bg-indigo-700 text-white rounded-[100px] px-4 py-2 cursor-pointer text-sm block w-30 h-10">立即学习</button>
                    <button
                        class="bg-indigo-700 text-white rounded-[100px] px-4 py-2 cursor-pointer text-sm block w-30 h-10">查看课程</button>
                </div>
                <div class="flex items-center gap-4 pt-4">
                    <button
                        v-if="!userStore.getUser"
                        @click="handleCheckIn"
                        class="px-6 py-2 bg-indigo-500 text-white rounded-full text-sm hover:bg-indigo-600 transition-colors">
                        登录后打卡
                    </button>
                    <button
                        v-else-if="!isCheckedIn"
                        @click="handleCheckIn"
                        class="px-6 py-2 bg-indigo-500 text-white rounded-full text-sm hover:bg-indigo-600 transition-colors">
                        📌 打卡
                    </button>
                    <span
                        v-else
                        class="px-6 py-2 bg-gray-200 text-gray-500 rounded-full text-sm cursor-not-allowed">
                        ✅ 已打卡
                    </span>
                    <span
                        :class="{ 'animate-bounce text-indigo-400': isAnimating }"
                        class="text-white text-sm">
                        累计 {{ userStore.getUser?.dayNumber ?? 0 }} 天
                    </span>
                </div>
            </div>
            <div class="relative z-8 p-8">
                <Hologram />
            </div>
        </div>
        <!-- AI 推荐卡片 -->
        <div v-if="userStore.getUser" class="mt-6">
            <RecommendCard compact />
        </div>
        <!-- 描述区域 -->
        <div class="rounded-[20px] p-10 text-center">
            <div class="text-2xl text-why font-bold text-gray-800">为什么选择我们?</div>
            <div class="text-1xl text-why-content font-bold text-gray-600 mt-4">我们经过科学的验证，AI学习英语的效果比传统学习方式更好，更高效。</div>
        </div>
        <!-- 数据统计区域 -->
        <div class="mt-16 py-12 flex items-center justify-between">
            <template v-for="(item, index) in stats" :key="item.label">
                <div class="flex-1 text-center">
                    <div class="flex items-baseline justify-center gap-1">
                        <span class="text-4xl font-bold text-gray-800 stat-number">{{ item.value }}</span>
                        <span class="text-2xl font-bold text-indigo-500">{{ item.suffix }}</span>
                    </div>
                    <div class="text-gray-500 mt-2">{{ item.label }}</div>
                </div>
                <div v-if="index < stats.length - 1" class="w-px h-16 bg-gray-200" />
            </template>
        </div>
        <div class="relative text-center py-8 mb-6">
            <!-- 装饰性光晕背景 -->
            <div
                class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-indigo-200/30 rounded-full blur-3xl" />
            <div class="relative z-10">
                <span
                    class="inline-block text-core  px-4 py-1.5 bg-indigo-100 text-indigo-600 text-sm font-medium rounded-full mb-4">✨
                    核心优势</span>
                <div
                    class="text-3xl font-bold core-title bg-linear-to-r from-gray-800 via-indigo-700 to-indigo-500 bg-clip-text text-transparent">
                    重新定义英语学习方式
                </div>
                <div class="text-base text-gray-500 mt-4  mx-auto core-content leading-relaxed">
                    融合前沿 AI 技术与语言学研究，打造沉浸式学习体验，让每一分钟的学习都更有价值
                </div>
            </div>
        </div>
        <div class="grid cards-container grid-cols-3 gap-6" style="perspective: 1000px">
            <div v-for="(item, index) in abouts" :key="item.title"
                class="about-card group relative overflow-hidden rounded-[24px] p-8 cursor-pointer transition-all duration-500 hover:-translate-y-2 bg-white border border-gray-200 hover:border-indigo-300 hover:shadow-xl hover:shadow-indigo-500/10"
                :style="{ animationDelay: `${index * 100}ms` }">
                <!-- 装饰性背景图案 -->
                <div
                    class="absolute -right-8 -top-8 w-32 h-32 bg-indigo-100 rounded-full blur-2xl group-hover:scale-150 group-hover:bg-indigo-200 transition-all duration-700" />
                <div class="absolute -left-4 -bottom-4 w-24 h-24 bg-indigo-50 rounded-full" />

                <!-- 图标区域 -->
                <div
                    class="relative z-10 w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 group-hover:bg-indigo-200 transition-all duration-300">
                    {{ item.icon }}
                </div>

                <!-- 内容区域 -->
                <div class="relative z-10">
                    <div class="text-xl font-bold text-gray-800 mb-3">{{ item.title }}</div>
                    <div class="text-sm text-gray-500 leading-relaxed">{{ item.content }}</div>
                </div>
            </div>
        </div>
    </div>
</template>


<script setup lang="ts">
import Hologram from './components/Hologram.vue'
import RecommendCard from '@/components/RecommendCard.vue'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useLogin } from '@/hooks/useLogin'
import { checkIn } from '@/apis/user'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
const { login } = useLogin()
const userStore = useUserStore()
const isCheckedIn = computed(() => userStore.isCheckedIn)
const isAnimating = ref(false)

const handleCheckIn = async () => {
    if (!userStore.getUser) {
        ElMessage.warning('请先登录')
        return
    }

    try {
        const res = await checkIn()
        if (res.success) {
            userStore.updateDayNumber(res.data.dayNumber)
            if (res.data.checkedIn) {
                userStore.lastCheckInDate = new Date().toISOString().slice(0, 10)
                isAnimating.value = true
                setTimeout(() => { isAnimating.value = false }, 1000)
            } else {
                // 后端说已打卡，也同步状态
                userStore.lastCheckInDate = new Date().toISOString().slice(0, 10)
            }
            ElMessage.success(res.message)
        }
    } catch (e) {
        // Error handled by interceptor
    }
}

const stats = reactive([
    { value: 0, suffix: '+', label: '累计学员', target: 1000000 },
    { value: 0, suffix: '+', label: '精品课程', target: 500 },
    { value: 0, suffix: '%', label: '学员满意度', target: 98 },
    { value: 0, suffix: '+', label: '学习时长(小时)', target: 5000000 }
])
const abouts = [
    {
        icon: '🖼️',
        title: 'AI情境学习',
        content: '沉浸式场景模拟，让你在真实语境中自然习得英语，告别枯燥的死记硬背。'
    },
    {
        icon: '🧠',
        title: '智能对话练习',
        content: 'AI 实时纠错反馈，个性化对话训练，24小时随时练习口语表达。'
    },
    {
        icon: '🎤',
        title: '科学词汇记忆',
        content: '基于艾宾浩斯遗忘曲线，智能安排复习计划，让单词真正记住。'
    },
]

let gsapInstance: any = null
let ScrollTriggerInstance: any = null

const initProject = (gsap: any, ScrollTrigger: any) => {
    //数字滚动动画
    stats.forEach((item) => {
        gsap.to(item, {
            value: item.target, //目标值
            duration: 2, //持续时间
            ease: 'power2.inOut', //过度动画
        })
    })
    //卡片过度
    const cards = gsap.utils.toArray('.about-card') as HTMLElement[]
    cards.forEach((card, index) => {
        gsap.fromTo(card,
            {
                opacity: 0,
                y: 40,
                scale: 0.98,
            },
            {
                opacity: 1,
                y: 0,
                scale: 1,
                duration: 0.5,
                delay: index * 0.08,
                ease: 'power2.out',
                scrollTrigger: {
                    trigger: '.cards-container',
                    start: 'top 75%',
                }
            })
    })
    //文字过度
    gsap.fromTo('.text-why', {
        opacity: 0,
        y: 60,
    }, {
        opacity: 1,
        y: 0,
    })
    gsap.fromTo('.text-why-content', {
        opacity: 0,
        y: 60,
    }, {
        opacity: 1,
        y: 0,
    })
    //核心优势文字过度
    gsap.fromTo('.text-core', {
        opacity: 0,
        y: 60,
    }, {
        opacity: 1,
        y: 0,
        scrollTrigger: {
            trigger: '.text-core',
            start: 'top 70%',
        }
    })
    gsap.fromTo('.core-title', {
        opacity: 0,
        y: 60,
    }, {
        opacity: 1,
        y: 0,
        scrollTrigger: {
            trigger: '.core-title',
            start: 'top 70%',
        }
    })
    gsap.fromTo('.core-content', {
        opacity: 0,
        y: 60,
    }, {
        opacity: 1,
        y: 0,
        scrollTrigger: {
            trigger: '.core-content',
            start: 'top 70%',
        }
    })
}

const showLogin = () => {
     login().then(() => {
        console.log('登录成功之后跳转页面')
     })
}

onMounted(async () => {
    const gsapModule = await import('gsap')
    const gsap = gsapModule.default || gsapModule.gsap || gsapModule
    const { ScrollTrigger } = await import('gsap/ScrollTrigger')
    gsap.registerPlugin(ScrollTrigger)

    gsapInstance = gsap
    ScrollTriggerInstance = ScrollTrigger

    initProject(gsap, ScrollTrigger)
})

onUnmounted(() => {
    if (ScrollTriggerInstance) {
        ScrollTriggerInstance.getAll().forEach((t: any) => t.kill())
    }
})

</script>