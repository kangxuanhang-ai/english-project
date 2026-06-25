# Chat UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按照 `chat-ui-preview.html` 原型重设计 Chat 页面的欢迎界面和周围 UI，聊天气泡不动。

**Architecture:** 新增 `roleConfig.ts` 集中管理角色配置，新增 `WelcomeScreen.vue` 处理欢迎界面，修改 4 个现有 Vue 文件调整样式。

**Tech Stack:** Vue 3 Composition API、Tailwind CSS 4、Element Plus

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/web/src/views/Chat/roleConfig.ts` | Create | 角色图标、描述、问候语、快捷卡片配置 |
| `apps/web/src/views/Chat/components/WelcomeScreen.vue` | Create | 欢迎界面（问候语 + 副标题 + 快捷卡片） |
| `apps/web/src/views/Chat/index.vue:2` | Modify | 容器样式（圆角、阴影、背景色） |
| `apps/web/src/views/Chat/components/RoleList.vue` | Modify | 关联 roleConfig，添加图标+描述，调整 active 样式 |
| `apps/web/src/views/Chat/components/ConversationList.vue` | Modify | 宽度 260px，圆形按钮，header 布局 |
| `apps/web/src/views/Chat/components/ChatArea.vue` | Modify | 集成 WelcomeScreen，toggle pill 和按钮样式 |

---

## Task 1: 创建 roleConfig.ts

**Files:**
- Create: `apps/web/src/views/Chat/roleConfig.ts`

角色配置数据，5 个角色各自的图标、描述、问候语、副标题、3 张快捷卡片。

- [ ] **Step 1: 创建 roleConfig.ts**

```ts
import type { ChatRoleType } from '@en/common/chat'

export interface RoleCard {
  icon: string
  color: string
  title: string
  desc: string
  placeholder: string
  toggle?: 'deep' | 'web'
}

export interface RoleInfo {
  icon: string
  desc: string
  greeting: string
  subtitle: string
  cards: RoleCard[]
}

export const roleConfig: Record<ChatRoleType, RoleInfo> = {
  normal: {
    icon: '🧠',
    desc: '查词·语法·搜索',
    greeting: '你好！👋',
    subtitle: '我是你的英语学习助手，有什么可以帮你的？',
    cards: [
      { icon: '🔍', color: 'purple', title: '查词释义', desc: '查询单词的含义、音标和例句', placeholder: '请输入要查询的单词...' },
      { icon: '✏️', color: 'blue', title: '语法检查', desc: '检查英语句子的语法错误并给出修正', placeholder: '请输入要检查语法的英语句子...', toggle: 'deep' },
      { icon: '🌐', color: 'green', title: '联网搜索', desc: '搜索互联网获取最新的信息', placeholder: '请输入要搜索的内容...', toggle: 'web' },
    ]
  },
  master: {
    icon: '🎓',
    desc: '专业术语，英文回复',
    greeting: 'Hello! 🎓',
    subtitle: "I'm your English master. Let's practice together.",
    cards: [
      { icon: '📖', color: 'purple', title: '用英语解释', desc: '让我用英语帮你解释词义和概念', placeholder: '请输入要解释的单词或概念...' },
      { icon: '🗣️', color: 'blue', title: '纠正我的表达', desc: '帮你改正英语表达中的错误', placeholder: '请输入你想纠正的英语句子...', toggle: 'deep' },
      { icon: '💡', color: 'green', title: '举例造句', desc: '用例句帮你理解和记忆单词', placeholder: '请输入要造句的单词...' },
    ]
  },
  business: {
    icon: '💼',
    desc: '商务场景对话',
    greeting: '你好！💼',
    subtitle: '我是商务英语专家，帮你搞定职场英语。',
    cards: [
      { icon: '✉️', color: 'purple', title: '写商务邮件', desc: '帮你撰写专业的英文商务邮件', placeholder: '请描述邮件的场景和目的...' },
      { icon: '🤝', color: 'blue', title: '模拟面试对话', desc: '模拟真实场景练习商务英语', placeholder: '请选择面试场景或直接开始对话...' },
      { icon: '📊', color: 'green', title: '商务术语解释', desc: '解释商务场景中的专业术语', placeholder: '请输入要查询的商务术语...' },
    ]
  },
  qilinge: {
    icon: '🤣',
    desc: '搞笑风格回复',
    greeting: '嘿！🤣',
    subtitle: '麒麟哥来了！准备好被我气死吧！',
    cards: [
      { icon: '🤣', color: 'pink', title: '搞笑解释单词', desc: '用麒麟哥的方式帮你记住单词', placeholder: '随便说个单词让我吐槽...' },
      { icon: '😤', color: 'rose', title: '吐槽我的语法', desc: '看看你的英语有多离谱', placeholder: '发一句英语让我吐槽...' },
      { icon: '🎭', color: 'amber', title: '角色扮演对话', desc: '进入剧情，用英语吵架', placeholder: '选个场景，我们开始表演...' },
    ]
  },
  xiaoman: {
    icon: '💻',
    desc: '程序员术语',
    greeting: 'Hey! 💻',
    subtitle: '小满模式已启动，用程序员的方式学英语。',
    cards: [
      { icon: '💻', color: 'cyan', title: '代码解释语法', desc: '用伪代码和逻辑帮你理解英语语法', placeholder: '输入你想理解的语法规则...' },
      { icon: '🐛', color: 'teal', title: 'Debug 这句话', desc: '像 debug 一样帮你找出英语错误', placeholder: '粘贴你写的英语，我来 debug...', toggle: 'deep' },
      { icon: '⚡', color: 'orange', title: '编程英语术语', desc: '学习程序员常用的英语表达', placeholder: '输入编程相关的英语术语...' },
    ]
  },
}
```

- [ ] **Step 2: 验证类型正确**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

---

## Task 2: 创建 WelcomeScreen.vue

**Files:**
- Create: `apps/web/src/views/Chat/components/WelcomeScreen.vue`

欢迎界面组件。从 `chatStore.activeRole` + `roleConfig` 取数据，通过 emit 通知父组件卡片点击事件。

- [ ] **Step 1: 创建 WelcomeScreen.vue**

```vue
<template>
    <div class="flex-1 flex flex-col items-center justify-center p-10 animate-fade-in-up">
        <div class="text-[28px] font-bold text-gray-800 mb-2">{{ info.greeting }}</div>
        <div class="text-[15px] text-gray-400 mb-10">{{ info.subtitle }}</div>
        <div class="flex gap-4">
            <div
                v-for="(card, i) in info.cards"
                :key="i"
                class="w-[240px] p-5 border border-gray-100 rounded-2xl cursor-pointer transition-all duration-250 bg-white relative overflow-hidden group hover:border-indigo-200 hover:shadow-[0_8px_24px_rgba(99,102,241,0.1)] hover:-translate-y-[3px] animate-fade-in-card"
                :style="{ animationDelay: `${0.1 * (i + 1)}s` }"
                @click="handleCardClick(card)"
            >
                <div
                    class="w-[44px] h-[44px] rounded-[14px] flex items-center justify-center text-[22px] mb-[14px] transition-transform duration-250 group-hover:scale-110"
                    :class="iconBgClass(card.color)"
                >{{ card.icon }}</div>
                <div class="text-sm font-semibold text-gray-800 mb-1">{{ card.title }}</div>
                <div class="text-xs text-gray-400 leading-relaxed">{{ card.desc }}</div>
                <div
                    class="absolute bottom-0 left-0 right-0 h-[3px] rounded-b-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-250"
                    :class="bottomBarClass(card.color)"
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

function bottomBarClass(color: string) {
    const map: Record<string, string> = {
        purple: 'bg-gradient-to-r from-indigo-400 to-indigo-500',
        blue: 'bg-gradient-to-r from-blue-400 to-blue-500',
        green: 'bg-gradient-to-r from-green-400 to-green-500',
        pink: 'bg-gradient-to-r from-pink-400 to-pink-500',
        rose: 'bg-gradient-to-r from-rose-400 to-rose-500',
        amber: 'bg-gradient-to-r from-amber-400 to-amber-500',
        cyan: 'bg-gradient-to-r from-cyan-400 to-cyan-500',
        teal: 'bg-gradient-to-r from-teal-400 to-teal-500',
        orange: 'bg-gradient-to-r from-orange-400 to-orange-500',
    }
    return map[color] ?? map.purple
}
</script>

<style scoped>
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
```

- [ ] **Step 2: 验证类型正确**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

---

## Task 3: 修改 RoleList.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/RoleList.vue` (全文替换)

关联 `roleConfig`，每个角色显示图标 + 名称 + 描述，active 改为左边框 indigo 样式。

- [ ] **Step 1: 替换 RoleList.vue**

```vue
<template>
    <div class="w-[200px] flex flex-col border-r border-gray-200" style="background: #f8f7ff">
        <div class="px-4 pt-5 pb-3">
            <h3 class="text-xs font-bold text-gray-500 uppercase tracking-wide">角色</h3>
        </div>
        <div class="flex-1 overflow-y-auto px-3">
            <div
                v-for="mode in chatModes"
                :key="mode.id"
                @click="handleClick(mode)"
                :class="chatStore.activeRole === mode.role
                    ? 'bg-indigo-50 border-l-[3px] border-l-indigo-500'
                    : 'border-l-[3px] border-l-transparent hover:bg-indigo-50/50'"
                class="flex items-center gap-[10px] rounded-lg py-[10px] px-2 cursor-pointer transition-all duration-200 mb-[2px]"
            >
                <span class="text-xl leading-none shrink-0">{{ roleConfig[mode.role]?.icon ?? '💬' }}</span>
                <div class="min-w-0">
                    <div class="text-[13px] font-semibold text-gray-800 leading-snug">{{ mode.label }}</div>
                    <div class="text-[11px] text-gray-400 leading-snug mt-px truncate">{{ roleConfig[mode.role]?.desc ?? '' }}</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { ChatModeList, ChatMode } from '@en/common/chat'
import { getChatMode } from '@/apis/chat'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'
import { roleConfig } from '../roleConfig'

const chatStore = useChatStore()
const router = useRouter()
const chatModes = ref<ChatModeList>([])

const handleClick = (mode: ChatMode) => {
    chatStore.setRole(mode.role)
    router.replace(`/chat/${mode.role}`)
}

onMounted(async () => {
    const res = await getChatMode()
    chatModes.value = res.data
})
</script>
```

- [ ] **Step 2: 验证类型正确**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

---

## Task 4: 修改 ConversationList.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/ConversationList.vue` (全文替换)

宽度从 320px 改为 260px，header 改为 "对话" 标题 + 圆形 "+" 按钮，active 改为 indigo 样式。

- [ ] **Step 1: 替换 ConversationList.vue**

```vue
<template>
    <div class="w-[260px] flex flex-col border-r border-gray-200" style="background: #f8f7ff">
        <!-- 顶部：标题 + 新建按钮 -->
        <div class="flex items-center justify-between px-4 pt-5 pb-3">
            <span class="text-[13px] font-bold text-gray-500">对话</span>
            <el-button
                class="!w-7 !h-7 !rounded-full !p-0 !border-0 !text-white"
                style="background: #6366f1"
                @click="handleCreate"
            >+</el-button>
        </div>

        <!-- 对话列表 -->
        <div class="flex-1 overflow-y-auto px-3">
            <div
                v-for="conv in chatStore.conversations"
                :key="conv.id"
                @click="handleSelect(conv.id)"
                :class="chatStore.activeConversationId === conv.id
                    ? 'bg-indigo-50 border-indigo-200'
                    : 'border-transparent hover:bg-indigo-50/50'"
                class="group rounded-lg py-[10px] px-3 cursor-pointer transition-all duration-200 mb-[2px] border flex items-center justify-between"
            >
                <div class="text-[13px] text-gray-700 truncate flex-1 mr-2">
                    {{ conv.title }}
                </div>
                <el-button
                    type="danger"
                    size="small"
                    link
                    class="!opacity-0 group-hover:!opacity-100 transition-opacity"
                    @click.stop="handleDelete(conv.id)"
                >
                    <el-icon><Delete /></el-icon>
                </el-button>
            </div>

            <!-- 空状态 -->
            <div
                v-if="chatStore.conversations.length === 0"
                class="flex flex-col items-center justify-center gap-2 text-gray-400 mt-16"
            >
                <div class="text-[13px] font-medium">暂无对话</div>
                <div class="text-[11px] text-gray-300">点击上方 + 新建</div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { Delete } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'

const chatStore = useChatStore()
const router = useRouter()

const handleCreate = async () => {
    const id = await chatStore.createConversation(chatStore.activeRole)
    router.replace(`/chat/${chatStore.activeRole}/${id}`)
}

const handleSelect = (id: string) => {
    chatStore.setConversation(id)
    router.replace(`/chat/${chatStore.activeRole}/${id}`)
}

const handleDelete = async (id: string) => {
    await chatStore.deleteConversation(id)
    if (chatStore.activeConversationId) {
        router.replace(`/chat/${chatStore.activeRole}/${chatStore.activeConversationId}`)
    } else {
        router.replace(`/chat/${chatStore.activeRole}`)
    }
}
</script>

<style scoped>
.el-button:hover {
    background: #4f46e5 !important;
}
</style>
```

- [ ] **Step 2: 验证类型正确**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

---

## Task 5: 修改 ChatArea.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue` (全文替换)

集成 WelcomeScreen，调整 toggle pill 为 indigo 样式，发送/语音按钮改为圆形。

- [ ] **Step 1: 替换 ChatArea.vue**

```vue
<template>
    <div class="flex-1 flex flex-col bg-white">
        <!-- 无对话时显示欢迎界面 -->
        <WelcomeScreen v-if="!chatStore.activeConversationId" @select-card="handleSelectCard" />

        <!-- 有对话时显示消息列表 -->
        <template v-else>
            <div class="flex-1 overflow-y-auto p-5">
                <div v-for="(item, index) in list" :key="index">
                    <div class="flex justify-end items-center gap-4 mt-5 mb-5 mr-5" v-if="item.role === 'human'">
                        <div class="text-sm text-white max-w-[80%] rounded-lg p-2 bg-blue-500 shadow-md">{{ item.content }}</div>
                        <div><el-avatar :size="35">user</el-avatar></div>
                    </div>
                    <template v-else-if="item.type === 'tool'"></template>
                    <div v-else class="flex justify-start items-center gap-4 mt-5 mb-5">
                        <div><el-avatar :size="35">AI</el-avatar></div>
                        <div>
                            <div v-if="item.reasoning" class="text-[12px] text-gray-500 max-w-[80%] p-2">{{ item.reasoning }}</div>
                            <div v-if="item.status === 'loading'" class="flex items-center gap-1 mt-2">
                                <span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>
                            </div>
                            <div v-else-if="item.status === 'tool_calling'" class="text-xs text-gray-400 mt-2">
                                <span class="inline-block tool-shake">🔍</span>
                                <span class="ml-1">正在调用 <strong>{{ item.toolName }}</strong>...</span>
                            </div>
                            <div v-else-if="item.status === 'tool_done'" class="text-xs text-green-500 mt-2">
                                <span>✅</span><span class="ml-1"><strong>{{ item.toolName }}</strong> 查询完成</span>
                            </div>
                            <div v-if="item.content !== ''" class="text-sm text-gray-700 max-w-[80%] bg-white rounded-lg mt-2 deepseek-markdown" v-html="parseMarkdown(item.content)" />
                        </div>
                    </div>
                </div>
                <div ref="chatRef"></div>
            </div>

            <!-- 输入区域 -->
            <div class="flex flex-col gap-3 p-5 border-t border-gray-100">
                <div class="flex items-center gap-2">
                    <div class="flex items-center gap-1 px-3 py-1 rounded-full text-xs cursor-pointer transition-all border"
                        :class="deepThink ? 'bg-indigo-100 border-indigo-400 text-indigo-700' : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'"
                        @click="toggleDeepThink"><span>🧠</span><span>深度思考</span></div>
                    <div class="flex items-center gap-1 px-3 py-1 rounded-full text-xs cursor-pointer transition-all border"
                        :class="webSearch ? 'bg-blue-100 border-blue-400 text-blue-700' : 'bg-gray-100 border-gray-200 text-gray-500 hover:bg-gray-200'"
                        @click="toggleWebSearch"><span>🌐</span><span>联网搜索</span></div>
                </div>
                <div class="flex items-end gap-[10px]">
                    <el-input @keyup.enter="sendMessage" type="textarea" :rows="2" v-model="message" :placeholder="inputPlaceholder" class="flex-1" />
                    <el-button class="!rounded-full !w-[44px] !h-[44px] !p-0" style="background: #6366f1; border-color: #6366f1" :icon="Position" type="primary" @click="sendMessage" />
                    <el-button v-if="!isRecording" class="!rounded-full !w-[44px] !h-[44px] !p-0 !bg-transparent !border-gray-200 !text-gray-400 hover:!border-gray-400 hover:!text-gray-600" :icon="Mic" @click="startRecording" />
                    <el-button v-else class="!rounded-full !w-[44px] !h-[44px] !p-0" style="background: #6366f1; border-color: #6366f1" :icon="VideoPause" type="primary" @click="stopRecording" />
                </div>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, watch, nextTick, onUnmounted } from 'vue'
import { Position, Mic, VideoPause } from '@element-plus/icons-vue'
import type { ChatMessageList, ChatDto, ChatSSEMessage } from '@en/common/chat'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import '@/assets/css/deep-seek.css'
import { useVoiceToText } from '@/hooks/useVoiceToText'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { refreshTokenApi } from '@/apis/auth'
import { useRouter } from 'vue-router'
import { getChatHistory, generateTitle } from '@/apis/chat'
import { sse, CHAT_URL } from '@/apis/sse'
import WelcomeScreen from './WelcomeScreen.vue'

const router = useRouter()
const userStore = useUserStore()

async function ensureToken() {
    const token = userStore.getAccessToken
    const refreshToken = userStore.getRefreshToken
    if (!token || !refreshToken) return false
    try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (Date.now() >= (payload.exp * 1000 - 10000)) {
            const result = await refreshTokenApi({ refreshToken })
            if (result.success) {
                userStore.updateToken(result.data)
            } else {
                return false
            }
        }
    } catch {}
    return true
}

const chatStore = useChatStore()
const { isRecording, start, stop } = useVoiceToText({ lang: 'zh-CN', continuous: true })

const list = ref<ChatMessageList>([])
const message = ref('')
const deepThink = ref(false)
const webSearch = ref(false)
const chatRef = useTemplateRef<HTMLDivElement>('chatRef')

let abortController: AbortController | null = null
let toolCallingStart = 0
let isStreaming = false
let isSending = false
let currentConversationId: string | null = null

watch(() => chatStore.activeRole, () => {
    if (abortController) { abortController.abort(); abortController = null }
    isStreaming = false
    isSending = false
    currentConversationId = null
    list.value = []
})

watch(() => chatStore.activeConversationId, async (newId) => {
    if (isStreaming || isSending) return
    if (newId !== currentConversationId) {
        list.value = []
        currentConversationId = newId
    }
    if (abortController) { abortController.abort(); abortController = null }
    if (newId) {
        const res = await getChatHistory(newId)
        list.value = res.data
    }
})

const toggleDeepThink = () => { deepThink.value = !deepThink.value; if (deepThink.value) webSearch.value = false }
const toggleWebSearch = () => { webSearch.value = !webSearch.value; if (webSearch.value) deepThink.value = false }

function handleSelectCard(placeholder: string, toggle?: 'deep' | 'web') {
    message.value = ''
    inputPlaceholder.value = placeholder
    if (toggle === 'deep') { deepThink.value = true; webSearch.value = false }
    else if (toggle === 'web') { webSearch.value = true; deepThink.value = false }
    else { deepThink.value = false; webSearch.value = false }
}

const inputPlaceholder = ref('请输入内容')

const sendMessage = async () => {
    if (!message.value) return
    if (!await ensureToken()) return
    isSending = true
    if (!chatStore.activeConversationId) {
        const id = await chatStore.createConversation(chatStore.activeRole)
        currentConversationId = id
        router.replace(`/chat/${chatStore.activeRole}/${id}`)
    }
    if (!chatStore.activeConversationId) { isSending = false; return }
    const msg = message.value; message.value = ''
    inputPlaceholder.value = '请输入内容'
    list.value.push({ role: 'human', content: msg, type: 'chat' })
    list.value.push({ role: 'ai', content: '', reasoning: '', status: 'loading', type: 'chat' })
    const aiIndex = list.value.length - 1
    const isFirstMessage = list.value.filter(m => m.role === 'human').length === 1

    if (abortController) abortController.abort()
    abortController = new AbortController()
    isStreaming = true
    isSending = false

    sse<ChatSSEMessage, ChatDto>(CHAT_URL, "POST",
        { conversationId: chatStore.activeConversationId!, role: chatStore.activeRole, content: msg, deepThink: deepThink.value, webSearch: webSearch.value },
        (data) => {
            const aiMsg = list.value[aiIndex]
            if (!aiMsg) return
            if (data.type === 'reasoning') { aiMsg.reasoning += data.content ?? ''; if (aiMsg.status === 'loading') aiMsg.status = undefined }
            if (data.type === 'chat') { if (aiMsg.status) aiMsg.status = undefined; aiMsg.content += data.content ?? '' }
            if (data.type === 'tool') { toolCallingStart = Date.now(); aiMsg.status = 'tool_calling'; aiMsg.toolName = data.tool; list.value.push({ role: 'ai', content: '', type: 'tool', toolId: data.id, toolName: data.tool, toolInput: data.input }) }
            if (data.type === 'tool_result') { setTimeout(() => { if (list.value[aiIndex]) list.value[aiIndex].status = 'tool_done' }, Math.max(0, 800 - (Date.now() - toolCallingStart))); const t = [...list.value].reverse().find(m => m.type === 'tool' && m.toolName === data.tool); if (t) t.toolOutput = data.output }
        },
        undefined,
        abortController.signal,
    )

    if (isFirstMessage && chatStore.activeConversation?.title === '新对话') {
        const convId = chatStore.activeConversationId!
        const poll = setInterval(async () => {
            const aiMsg = list.value[aiIndex]
            if (aiMsg && !aiMsg.status && aiMsg.content) {
                clearInterval(poll)
                isStreaming = false
                try {
                    const res = await generateTitle(convId, msg)
                    chatStore.updateTitle(res.data.id, res.data.title)
                } catch {}
            }
        }, 1000)
        setTimeout(() => { clearInterval(poll); isStreaming = false }, 10000)
    } else {
        const poll = setInterval(() => {
            const aiMsg = list.value[aiIndex]
            if (aiMsg && !aiMsg.status && aiMsg.content) {
                clearInterval(poll)
                isStreaming = false
            }
        }, 1000)
        setTimeout(() => { clearInterval(poll); isStreaming = false }, 10000)
    }
}

const parseMarkdown = (content: string) => content ? DOMPurify.sanitize(marked.parse(content) as string) : ''
const startRecording = () => start((result) => { message.value = result })
const stopRecording = () => { stop(); sendMessage() }
watch(() => list.value.length, () => { nextTick(() => { chatRef.value?.scrollIntoView({ behavior: 'smooth' }) }) })
onUnmounted(() => { if (abortController) abortController.abort() })
</script>

<style scoped>
.loading-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background-color: #9ca3af; animation: dot-bounce 1.4s infinite ease-in-out both; }
.loading-dot:nth-child(1) { animation-delay: -0.32s; } .loading-dot:nth-child(2) { animation-delay: -0.16s; } .loading-dot:nth-child(3) { animation-delay: 0s; }
@keyframes dot-bounce { 0%, 80%, 100% { transform: scale(0); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
.tool-shake { animation: shake 0.6s infinite; }
@keyframes shake { 0%, 100% { transform: translateX(0); } 20% { transform: translateX(-2px) rotate(-5deg); } 40% { transform: translateX(2px) rotate(5deg); } 60% { transform: translateX(-2px) rotate(-3deg); } 80% { transform: translateX(2px) rotate(3deg); } }
</style>
```

- [ ] **Step 2: 验证类型正确**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

---

## Task 6: 修改 index.vue 容器样式

**Files:**
- Modify: `apps/web/src/views/Chat/index.vue:2`

容器加圆角 20px、阴影、白色背景。

- [ ] **Step 1: 修改容器 div**

将第 2 行：
```html
<div class="w-[1200px] mx-auto flex my-10 rounded-[15px] overflow-hidden" style="height: calc(100vh - 160px)">
```

改为：
```html
<div class="w-[1200px] mx-auto flex my-10 rounded-[20px] overflow-hidden bg-white shadow-[0_4px_24px_rgba(0,0,0,0.06),0_1px_4px_rgba(0,0,0,0.04)]" style="height: calc(100vh - 160px)">
```

- [ ] **Step 2: 验证类型正确**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

- [ ] **Step 3: 启动开发服务器验证视觉效果**

Run: `pnpm web`
Expected: 浏览器打开 http://localhost:8080/chat/normal，看到新的欢迎界面和周围 UI

---

## Task 7: 最终验证

- [ ] **Step 1: 类型检查**

Run: `cd apps/web && npx vue-tsc --noEmit`
Expected: 无报错

- [ ] **Step 2: 构建验证**

Run: `cd apps/web && pnpm build`
Expected: 构建成功，无错误

- [ ] **Step 3: 视觉走查**

打开浏览器访问以下 URL，逐一验证：
- `http://localhost:8080/chat/normal` — 智能助手欢迎界面，3 张卡片正确
- `http://localhost:8080/chat/master` — 英语大师欢迎界面，英文问候
- `http://localhost:8080/chat/qilinge` — 麒麟哥欢迎界面，粉/玫瑰/琥珀色卡片
- `http://localhost:8080/chat/xiaoman` — 小满模式欢迎界面，青/橙色卡片

验证项：
- 左侧 RoleList 有图标 + 描述，active 左边框 indigo
- 中间 ConversationList 260px，圆形 "+" 按钮
- 右侧欢迎界面居中，卡片 hover 有上浮 + 底部线条动画
- 点击卡片后自动创建对话，输入框 placeholder 正确
- toggle pill 点击卡片后正确激活
- 切换角色后欢迎界面内容更新
