# Chat UI 角色剧场（Role Theatre）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在仅改动 Chat 页的前提下，将三栏聊天 UI 升级到 `chat-ui-design.html` v3 的「角色剧场」视觉，5 角色 accent 联动，不修改全局 Header / 后端 / store 结构。

**Architecture:** 扩展 `roleConfig.ts` 输出 CSS 变量 → 注入 `chat-shell` → 新增 `ChatTopbar` / `ChatMessage` / `ChatInputDock` / `RoleSwitchBanner` 拆分 `ChatArea` 模板；样式集中在 `chat-theme.css`（含自 `deep-seek.css` 复制的 `.chat-md`）。SSE / Pinia 逻辑保留在 `ChatArea.vue`，仅补停止生成与 AbortError 分支。

**Tech Stack:** Vue 3 Composition API、Tailwind CSS 4、marked + hljs + DOMPurify、Google Fonts（经 `chat-theme.css` @import）

**设计 spec：** [2026-06-23-chat-role-theatre-design.md](../specs/2026-06-23-chat-role-theatre-design.md)

**视觉原型：** [chat-ui-design.html](../../../chat-ui-design.html)（仅对照 Header 以下 `chat-shell` 区域）

**禁止修改：** `apps/web/src/layout/**`、`packages/common/chat/**`、`server/**`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/web/src/views/Chat/roleConfig.ts` | Extend | `label`、`theme`、`roleThemeVars()` |
| `apps/web/src/assets/css/chat-theme.css` | Create | 字体、`.chat-main`、`.chat-md`、动画、滚动条 |
| `apps/web/src/assets/css/deep-seek.css` | **Keep** | 不修改、不删除 |
| `apps/web/src/views/Chat/index.vue` | Modify | `chat-shell` 样式 + CSS 变量 + `RoleSwitchBanner` |
| `apps/web/src/views/Chat/components/RoleSwitchBanner.vue` | Create | 角色切换 pill toast |
| `apps/web/src/views/Chat/components/ChatTopbar.vue` | Create | 对话标题 + role chip + 停止生成 |
| `apps/web/src/views/Chat/components/ChatMessage.vue` | Create | 用户气泡 + AI 卡片各态 |
| `apps/web/src/views/Chat/components/ChatInputDock.vue` | Create | floating dock + toggle + auto-resize |
| `apps/web/src/views/Chat/markdown.ts` | Create | marked + hljs + DOMPurify，`parseMarkdown()` |
| `apps/web/src/views/Chat/components/ChatArea.vue` | Refactor | 逻辑保留，模板拆到子组件；abort 处理 |
| `apps/web/src/views/Chat/components/WelcomeScreen.vue` | Upgrade | 渐变标题、推荐卡片、orb |
| `apps/web/src/views/Chat/components/RoleList.vue` | Upgrade | 208px、icon box、accent active |
| `apps/web/src/views/Chat/components/ConversationList.vue` | Upgrade | 268px、accent 新建按钮、空状态 |

---

## Task 1: 扩展 roleConfig — theme + roleThemeVars

**Files:**
- Modify: `apps/web/src/views/Chat/roleConfig.ts`

- [ ] **Step 1: 添加类型与 theme 数据**

在文件顶部追加接口，并为每个角色增加 `label` 与 `theme`：

```ts
export interface RoleTheme {
  accent: string
  accentDark: string
  accentLight: string
  accentSoft: string
  accentBorder: string
  accentText: string
  iconBg: string
}

export interface RoleInfo {
  label: string
  icon: string
  desc: string
  greeting: string
  subtitle: string
  cards: RoleCard[]
  theme: RoleTheme
}
```

五角色 theme 值（与 spec 一致）：

| role | accent | accentDark | accentLight | accentSoft | accentBorder | accentText | iconBg |
|------|--------|------------|-------------|------------|--------------|------------|--------|
| normal | `#6366f1` | `#4f46e5` | `#818cf8` | `#eef2ff` | `#c7d2fe` | `#4338ca` | `linear-gradient(135deg,#818cf8,#6366f1)` |
| master | `#7c3aed` | `#6d28d9` | `#a78bfa` | `#f5f3ff` | `#ddd6fe` | `#5b21b6` | `linear-gradient(135deg,#a78bfa,#7c3aed)` |
| business | `#2563eb` | `#1d4ed8` | `#60a5fa` | `#eff6ff` | `#bfdbfe` | `#1e40af` | `linear-gradient(135deg,#60a5fa,#2563eb)` |
| qilinge | `#e11d48` | `#be123c` | `#fb7185` | `#fff1f2` | `#fecdd3` | `#9f1239` | `linear-gradient(135deg,#fb7185,#e11d48)` |
| xiaoman | `#0891b2` | `#0e7490` | `#22d3ee` | `#ecfeff` | `#a5f3fc` | `#155e75` | `linear-gradient(135deg,#22d3ee,#0891b2)` |

各角色 `label`：`智能助手` / `英语大师` / `商务英语` / `麒麟哥` / `小满模式`

**本 Step 必须一次完成：** 5 个角色的 `roleConfig` 条目 **全部** 补齐 `label` + `theme`，不要只改接口或只改部分角色。

- [ ] **Step 2: 实现 roleThemeVars**

```ts
export function roleThemeVars(role: ChatRoleType): Record<string, string> {
  const t = roleConfig[role].theme
  return {
    '--chat-accent': t.accent,
    '--chat-accent-dark': t.accentDark,
    '--chat-accent-light': t.accentLight,
    '--chat-accent-soft': t.accentSoft,
    '--chat-accent-border': t.accentBorder,
    '--chat-accent-text': t.accentText,
    '--chat-icon-bg': t.iconBg,
    '--chat-glow': `${t.accent}33`,
    '--chat-bubble-shadow': `0 4px 14px ${t.accent}40`,
  }
}
```

- [ ] **Step 3: 运行 type-check**

Run: `pnpm --filter @en/web type-check`
Expected: PASS（Step 1 已补齐全部 5 角色 `label`/`theme` 时，`roleConfig.ts` 自洽，不应报错）

---

## Task 2: 创建 chat-theme.css

**Files:**
- Create: `apps/web/src/assets/css/chat-theme.css`
- Reference: `apps/web/src/assets/css/deep-seek.css`
- Reference: `chat-ui-design.html`（`.chat-main`、`.chat-md`、动画）

- [ ] **Step 1: 复制 deep-seek 为 chat-md 基础**

1. 复制 `deep-seek.css` 全部内容到 `chat-theme.css`
2. 全局替换 `.deepseek-markdown` → `.chat-md`
3. 删除 `.chat-md` 上的 `max-width: 80%`（卡片内由父容器控制宽度）

- [ ] **Step 2: 文件头部追加字体与 Chat 作用域**

```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Source+Serif+4:wght@600&display=swap');

.chat-shell {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.chat-main {
  background: #faf9f6;
  position: relative;
  overflow: hidden;
}

.chat-main::before {
  content: '';
  position: absolute;
  top: -120px;
  right: -80px;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, var(--chat-glow) 0%, transparent 70%);
  pointer-events: none;
}
```

> **accent 切换不做 CSS 变量 transition：** `transition: --chat-accent` 无效（自定义属性默认不可过渡；`@property` 仅 Chromium 可靠）。角色切换时 `--chat-*` 变量 **瞬时更新**；200ms 动画仅用于 `RoleSwitchBanner` 的 fade。若侧栏 active 需要柔和感，给具体元素加 `transition: background-color 200ms, border-color 200ms, box-shadow 200ms`。

- [ ] **Step 3: 适配 Markdown accent 样式**

在 `.chat-md h3` 规则中增加：

```css
.chat-md h3 {
  font-family: 'Source Serif 4', Georgia, serif;
  padding-left: 10px;
  border-left: 3px solid var(--chat-accent);
  border-bottom: none;
}
.chat-md table thead {
  background: var(--chat-accent-soft);
}
```

- [ ] **Step 4: 追加动画与滚动条**

```css
@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.msg-in { animation: msgIn 0.25s ease both; }

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.stream-cursor::after {
  content: '▋';
  animation: cursor-blink 1s step-end infinite;
  color: var(--chat-accent);
  margin-left: 2px;
}

.chat-scroll::-webkit-scrollbar { width: 4px; }
.chat-scroll::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
```

- [ ] **Step 5: 确认 deep-seek.css 未改动**

Run: `git diff apps/web/src/assets/css/deep-seek.css`
Expected: 无 diff

---

## Task 3: 升级 index.vue — chat-shell + RoleSwitchBanner

**Files:**
- Modify: `apps/web/src/views/Chat/index.vue`
- Create: `apps/web/src/views/Chat/components/RoleSwitchBanner.vue`

- [ ] **Step 1: 创建 RoleSwitchBanner.vue**

```vue
<template>
  <Transition name="role-banner">
    <div v-if="visible" class="role-switch-banner">
      已切换到 {{ info.icon }} {{ info.label }}
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { roleConfig } from '../roleConfig'

const STORAGE_KEY = 'chat-role-toast-seen'
const chatStore = useChatStore()
const visible = ref(false)
let hideTimer: ReturnType<typeof setTimeout> | null = null

const info = computed(() => roleConfig[chatStore.activeRole])

watch(() => chatStore.activeRole, () => {
  if (sessionStorage.getItem(STORAGE_KEY)) return
  sessionStorage.setItem(STORAGE_KEY, '1')
  visible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { visible.value = false }, 3200)
})
</script>

<style scoped>
.role-switch-banner {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  background: var(--chat-accent-soft);
  border: 1px solid var(--chat-accent-border);
  color: var(--chat-accent-text);
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
}
.role-banner-enter-active, .role-banner-leave-active { transition: opacity .2s ease; }
.role-banner-enter-from, .role-banner-leave-to { opacity: 0; }
</style>
```

- [ ] **Step 2: 更新 index.vue 模板与 script**

```vue
<template>
  <div
    class="chat-shell relative w-[1200px] mx-auto flex my-10 rounded-[24px] overflow-hidden bg-white shadow-[0_0_0_1px_rgba(0,0,0,.04),0_12px_40px_rgba(0,0,0,.08)]"
    :style="{ ...themeVars, height: 'calc(100vh - 160px)' }"
  >
    <RoleSwitchBanner />
    <RoleList />
    <ConversationList />
    <ChatArea />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
// ...existing imports...
import RoleSwitchBanner from './components/RoleSwitchBanner.vue'
import { roleThemeVars } from './roleConfig'

const themeVars = computed(() => roleThemeVars(chatStore.activeRole))
// ...existing onMounted logic unchanged...
</script>

<style>
@import '@/assets/css/chat-theme.css';
</style>
```

注意：`chat-theme.css` 在 `index.vue` import 一次即可覆盖全 Chat 子树；**不要**改 `layout/Header`。

- [ ] **Step 3: 浏览器冒烟**

Run: `pnpm web`，打开 `/chat/normal`
Expected: 卡片圆角 24px；切换角色时 accent 变量生效（侧栏尚未升级时可能只有 shell 过渡）

---

## Task 4: 创建 ChatInputDock.vue

**Files:**
- Create: `apps/web/src/views/Chat/components/ChatInputDock.vue`

- [ ] **Step 1: 实现 props / emits**

```ts
const props = defineProps<{
  modelValue: string
  deepThink: boolean
  webSearch: boolean
  isStreaming: boolean
  isRecording: boolean
  placeholder: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:deepThink': [value: boolean]
  'update:webSearch': [value: boolean]
  send: []
  stop: []
  'start-recording': []
  'stop-recording': []
}>()
```

- [ ] **Step 2: 实现 auto-resize 与 Enter 发送**

```ts
const MIN_HEIGHT = 46
const MAX_HEIGHT = 120
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = `${Math.min(Math.max(el.scrollHeight, MIN_HEIGHT), MAX_HEIGHT)}px`
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (!props.isStreaming) emit('send')
  }
}

function resetHeight() {
  if (textareaRef.value) textareaRef.value.style.height = `${MIN_HEIGHT}px`
}
defineExpose({ resetHeight })
```

- [ ] **Step 3: 模板结构（对照 chat-ui-design.html input dock）**

要点：
- 外层 `max-w-[720px] mx-auto w-full px-5 pb-5 pt-2`，顶部渐变 `bg-gradient-to-t from-white via-white/95 to-transparent`
- toggle 两行 SVG + 文字；deepThink active 用 `var(--chat-accent-soft)` 背景；webSearch active 用 blue 系
- textarea：`rounded-[18px] border border-gray-100 shadow-sm focus:ring-4 focus:outline-none`，focus ring 颜色 `var(--chat-glow)`
- 发送按钮 38×38：`background: linear-gradient(135deg, var(--chat-accent-light), var(--chat-accent))`
- 流式时发送按钮变 stop 图标，点击 `emit('stop')`；整体 `opacity-50 pointer-events-none` 除 stop 按钮
- 右下角字数 `{{ modelValue.length }} / 4000`；流式时改文案「按 Esc 或点击停止生成中断」

- [ ] **Step 4: type-check**

Run: `pnpm --filter @en/web type-check`
Expected: PASS

---

## Task 5: 创建 ChatMessage.vue + markdown.ts

**Files:**
- Create: `apps/web/src/views/Chat/components/ChatMessage.vue`
- Create: `apps/web/src/views/Chat/markdown.ts`

- [ ] **Step 1: 创建 markdown.ts**

从 `ChatArea.vue` 剪切 marked 配置，写入独立模块（Task 7 再从 ChatArea 删除重复 import）：

```ts
// apps/web/src/views/Chat/markdown.ts
import { marked } from 'marked'
import hljs from 'highlight.js'
import { markedHighlight } from 'marked-highlight'
import DOMPurify from 'dompurify'

marked.use(markedHighlight({
  langPrefix: 'hljs language-',
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
}))

export function parseMarkdown(content: string): string {
  return content ? DOMPurify.sanitize(marked.parse(content) as string) : ''
}
```

- [ ] **Step 2: 定义 props**

```ts
import { parseMarkdown } from '../markdown'

type LocalMessage = ChatMessage & { interrupted?: boolean }

const props = defineProps<{
  item: LocalMessage
  avatar: string
  aiAvatar: string
  roleLabel: string
  roleIcon: string
  expanded: boolean
}>()

const emit = defineEmits<{
  retry: [item: LocalMessage]
  'toggle-tool': [toolId: string | undefined]
}>()
```

- [ ] **Step 3: 用户消息模板**

右对齐；40px 头像双层 ring；气泡：

```html
<div
  class="max-w-[80%] px-4 py-2.5 text-sm text-white rounded-[18px_18px_6px_18px]"
  style="background: linear-gradient(135deg, var(--chat-accent-light), var(--chat-accent), var(--chat-accent-dark)); box-shadow: var(--chat-bubble-shadow)"
>{{ item.content }}</div>
```

- [ ] **Step 4: AI 卡片模板**

结构：
1. header：`roleIcon` + `roleLabel` + 绿点 + 时间占位「刚刚」
2. 顶条 3px：`background: linear-gradient(90deg, var(--chat-accent-light), var(--chat-accent))`
3. body 按 `status` / `streaming` 分支：
   - `loading` → 三点 bounce（`background: var(--chat-accent)`）
   - `tool_calling` → 黄色 pending pill
   - `tool_done` → 绿色 done pill
   - `reasoning` → 可折叠 gray bar（`ref expandedReasoning`）
   - `streaming` → `whitespace-pre-wrap` + `stream-cursor` class
   - `error` → 红色 error-box + 重试按钮 `@click="emit('retry', item)"`
   - 完成 → `<div class="chat-md" v-html="parseMarkdown(item.content)" />`
4. 若 `item.interrupted && item.content` → footer「已中断」12px `#a8a29e`

- [ ] **Step 5: tool 独立消息（type === 'tool'）**

与 spec 一致：pill + 点击展开 input/output；复用 AI 列左对齐缩进 `ml-14`

- [ ] **Step 6: type-check**

Run: `pnpm --filter @en/web type-check`
Expected: PASS

---

## Task 6: 创建 ChatTopbar.vue

**Files:**
- Create: `apps/web/src/views/Chat/components/ChatTopbar.vue`

- [ ] **Step 1: 实现组件**

```vue
<template>
  <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100/80 bg-white/80 backdrop-blur-sm shrink-0">
    <h2 class="text-[15px] font-semibold text-gray-800 truncate mr-4">{{ title }}</h2>
    <div class="flex items-center gap-2 shrink-0">
      <button
        v-if="isStreaming"
        type="button"
        class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
        @click="emit('stop')"
      >停止生成</button>
      <span
        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
        style="background: var(--chat-accent-soft); color: var(--chat-accent-text); border: 1px solid var(--chat-accent-border)"
      >
        {{ roleIcon }} {{ roleLabel }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  roleIcon: string
  roleLabel: string
  isStreaming: boolean
}>()
const emit = defineEmits<{ stop: [] }>()
</script>
```

- [ ] **Step 2: type-check**

Run: `pnpm --filter @en/web type-check`
Expected: PASS

---

## Task 7: 重构 ChatArea.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 替换 import**

移除：
- `@/assets/css/deep-seek.css`（样式已由 `index.vue` 引入 `chat-theme.css`）
- `marked` / `hljs` / `marked-highlight` / `DOMPurify` 及 `parseMarkdown`（已迁至 `markdown.ts`，由 `ChatMessage.vue` 使用）

- [ ] **Step 2: 模板结构**

```vue
<div class="flex-1 flex flex-col chat-main min-w-0">
  <WelcomeScreen v-if="!chatStore.activeConversationId" @select-card="handleSelectCard" />
  <template v-else>
    <ChatTopbar
      :title="chatStore.activeConversation?.title ?? '新对话'"
      :role-icon="roleInfo.icon"
      :role-label="roleInfo.label"
      :is-streaming="isStreaming"
      @stop="stopGeneration"
    />
    <div class="flex-1 overflow-y-auto chat-scroll px-5 py-4">
      <div class="max-w-[720px] mx-auto space-y-4">
        <ChatMessage
          v-for="(item, index) in list"
          :key="index"
          :item="item"
          :avatar="avatar"
          :ai-avatar="aiAvatar"
          :role-label="roleInfo.label"
          :role-icon="roleInfo.icon"
          :expanded="expandedTools.has(item.toolId ?? '')"
          class="msg-in"
          @retry="retryMessage"
          @toggle-tool="toggleToolExpand"
        />
        <div ref="chatRef" />
      </div>
    </div>
  </template>
  <ChatInputDock
    ref="dockRef"
    v-model="message"
    v-model:deep-think="deepThink"
    v-model:web-search="webSearch"
    :is-streaming="isStreaming"
    :is-recording="isRecording"
    :placeholder="inputPlaceholder"
    @send="sendMessage"
    @stop="stopGeneration"
    @start-recording="startRecording"
    @stop-recording="stopRecording"
  />
</div>
```

- [ ] **Step 3: 暴露 isStreaming 为 ref**

将 `let isStreaming = false` 改为 `const isStreaming = ref(false)`，SSE 回调内用 `isStreaming.value`；模板传 `:is-streaming="isStreaming"` 时用 `.value` 自动解包。

- [ ] **Step 4: 实现 stopGeneration + AbortError 分支**

先提取查找当前 AI 回复的 helper（避免末尾是 `type === 'tool'` 时找错；error 回调也不依赖 `aiIndex` 闭包）：

```ts
type LocalMessage = ChatMessage & { interrupted?: boolean }

/** 倒序找最后一条 AI 聊天消息（当前轮次的回复） */
function findLastAiChatMessage(): LocalMessage | undefined {
  return [...list.value].reverse().find(
    m => m.role === 'ai' && m.type === 'chat',
  ) as LocalMessage | undefined
}

function stopGeneration() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  isStreaming.value = false
  const aiMsg = findLastAiChatMessage()
  if (!aiMsg) return
  aiMsg.streaming = false
  if (aiMsg.content) {
    aiMsg.status = undefined
    aiMsg.interrupted = true
  }
}
```

在 **`sendMessage` 内部** 传给 `sse()` 的 error 回调（保持闭包或直接用 helper，二选一即可）：

```ts
(error: Error) => {
  if (error.name === 'AbortError') {
    stopGeneration()
    return
  }
  const aiMsg = findLastAiChatMessage()
  if (aiMsg) {
    aiMsg.status = 'error'
    aiMsg.content = '网络错误，请检查连接后重试'
    aiMsg.streaming = false
  }
  isStreaming.value = false
}
```

> 不要写 `list.value[aiIndex]` 或 `list.value[length - 1]`——工具调用会在列表末尾插入 `type === 'tool'` 项。

- [ ] **Step 5: Esc 快捷键**

```ts
import { onMounted, onUnmounted } from 'vue'

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isStreaming.value) stopGeneration()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
```

- [ ] **Step 6: sendMessage 成功后重置 textarea 高度**

```ts
const dockRef = ref<InstanceType<typeof ChatInputDock> | null>(null)
// sendMessage 内 message.value = '' 之后：
dockRef.value?.resetHeight?.()
```

- [ ] **Step 7: 添加 roleInfo computed**

```ts
const roleInfo = computed(() => roleConfig[chatStore.activeRole])
```

- [ ] **Step 8: type-check + 手动验证停止生成**

Run: `pnpm --filter @en/web type-check`

手动：
1. 发一条消息，流式过程中点「停止生成」
2. Expected: 已输出文字保留；无红色 error-box；可选「已中断」footer
3. 不应出现「网络错误」

---

## Task 8: 升级 WelcomeScreen.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/WelcomeScreen.vue`

- [ ] **Step 1: 增加 welcome-orb 与渐变标题**

```vue
<div class="flex-1 flex flex-col items-center justify-center p-10 relative overflow-hidden">
  <div class="welcome-orb absolute inset-0 pointer-events-none" />
  <h1
    class="relative text-[36px] font-semibold mb-2 font-serif"
    style="font-family:'Source Serif 4',serif;background:linear-gradient(135deg,#1c1917,var(--chat-accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent"
  >{{ info.greeting }}</h1>
  <p class="relative text-[15px] text-[#78716c] mb-2">{{ info.subtitle }}</p>
  <p class="relative text-xs text-[#a8a29e] mb-10">选择快捷卡片，或直接在下方输入</p>
  <!-- cards -->
</div>
```

`.welcome-orb` 样式写入组件 scoped 或 `chat-theme.css`：

```css
.welcome-orb {
  background: radial-gradient(ellipse 60% 50% at 50% 40%, var(--chat-glow), transparent);
}
```

- [ ] **Step 2: 第一张卡片 featured + 推荐徽章**

```vue
<div
  v-for="(card, i) in info.cards"
  :key="i"
  class="relative p-5 border border-gray-100 rounded-2xl cursor-pointer bg-white transition-all duration-250 group hover:-translate-y-[5px]"
  :class="i === 0 ? 'w-[280px]' : 'w-[240px]'"
  :style="{ animationDelay: `${0.05 + i * 0.07}s`, boxShadow: '0 1px 3px rgba(0,0,0,.04)' }"
  @click="handleCardClick(card)"
>
  <span v-if="i === 0" class="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full"
    style="background:var(--chat-accent-soft);color:var(--chat-accent-text)">推荐</span>
  <!-- icon + title + desc + hover bottom accent bar using var(--chat-accent) -->
</div>
```

- [ ] **Step 3: 卡片 hover 阴影改用 accent**

`hover:shadow-[0_12px_32px_var(--chat-glow)]` 或 inline `:style` 绑定 `var(--chat-glow)`

- [ ] **Step 4: 浏览器验证 5 角色欢迎页**

切换 5 角色，确认 greeting / accent / 推荐徽章

---

## Task 9: 升级 RoleList.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/RoleList.vue`

- [ ] **Step 1: 宽度与背景**

- `w-[200px]` → `w-[208px]`
- 背景 → `linear-gradient(180deg, #fafaff, #f5f4ff)`

- [ ] **Step 2: icon box + accent active**

```vue
<div
  class="w-[38px] h-[38px] rounded-[12px] flex items-center justify-center text-lg shrink-0"
  :style="{ background: roleConfig[mode.role].theme.iconBg }"
>{{ roleConfig[mode.role].icon }}</div>
```

active 态（替换 indigo 写死）：

```vue
:class="chatStore.activeRole === mode.role
  ? 'border border-[var(--chat-accent-border)] bg-[var(--chat-accent-soft)] shadow-[0_0_0_1px_var(--chat-glow)]'
  : 'border border-transparent hover:bg-white/60'"
class="... border-l-[3px] ..."
:style="chatStore.activeRole === mode.role ? { borderLeftColor: 'var(--chat-accent)' } : {}"
```

显示名改用 `roleConfig[mode.role].label`（可不再 stripEmoji backend label）

- [ ] **Step 3: 浏览器验证左栏 5 角色 active 变色**

---

## Task 10: 升级 ConversationList.vue

**Files:**
- Modify: `apps/web/src/views/Chat/components/ConversationList.vue`

- [ ] **Step 1: 宽度与背景**

- `w-[260px]` → `w-[268px]`
- 背景 `#fefefe`（与左栏分层）

- [ ] **Step 2: 新建按钮 accent 渐变**

替换 `el-button` 为原生 button（避免 Element 覆盖样式）：

```vue
<button
  type="button"
  class="w-[30px] h-[30px] rounded-[10px] text-white text-lg leading-none flex items-center justify-center"
  style="background:linear-gradient(135deg,var(--chat-accent-light),var(--chat-accent));box-shadow:0 2px 8px var(--chat-glow)"
  @click="handleCreate"
>+</button>
```

- [ ] **Step 3: 列表项 active 态**

active：`background: var(--chat-accent-soft)` + 左侧 6px 圆点（accent 色 + glow）

- [ ] **Step 4: 空状态图标卡片**

增加一个小卡片容器 + 「点击上方 + 开始新对话」文案（对照 design.html）

- [ ] **Step 5: 删除按钮**

hover 显示红色小方块（可保留 el-button link 或改 div）

---

## Task 11: 最终验收

**Files:** 全部 Task 1–10 产出

- [ ] **Step 1: type-check**

Run: `pnpm --filter @en/web type-check`
Expected: PASS，无 `@en/common/chat` 改动

- [ ] **Step 2: 确认 Header 未改动**

Run: `git diff apps/web/src/layout/`
Expected: 无 diff

- [ ] **Step 3: 对照 spec 验收标准 1–10**

| # | 检查项 | 操作 |
|---|--------|------|
| 1 | 5 角色 accent 联动 | 切换角色，观察气泡/顶条/发送钮/侧栏 |
| 2 | ChatTopbar | 进入有历史的对话 |
| 3 | AI 卡片各态 | 触发 loading / 工具 / reasoning / 流式 / 错误 |
| 4 | Input dock | 无 Element textarea 默认样式 |
| 5 | 欢迎页推荐徽章 | 无对话态 |
| 6 | 停止生成 | 流式中断，内容保留，无 error-box |
| 7 | 角色切换 banner | 首次切换角色，3s 消失 |
| 8 | type-check | 已通过 |
| 9 | Header 不变 | 与改动前对比截图 |
| 10 | 视觉对齐 design.html | 对照 `chat-shell` 三栏（不含 mock header） |

- [ ] **Step 4: 提交（用户要求时再 commit）**

```bash
git add apps/web/src/views/Chat apps/web/src/assets/css/chat-theme.css docs/superpowers/plans/2026-06-23-chat-role-theatre.md
git commit -m "feat(web): Role Theatre chat UI redesign"
```

---

## Spec Coverage Checklist

| Spec 章节 | 对应 Task |
|-----------|-----------|
| 范围边界 / 禁止 Header | Task 3 note + Task 11 Step 2 |
| roleConfig theme | Task 1 |
| chat-theme.css / deep-seek 迁移 | Task 2 |
| RoleList | Task 9 |
| ConversationList | Task 10 |
| ChatTopbar + 停止生成 | Task 6 + Task 7 Step 4 |
| WelcomeScreen | Task 8 |
| ChatMessage | Task 5 |
| markdown.ts | Task 5 Step 1 |
| ChatInputDock + auto-resize | Task 4 |
| 角色切换 banner | Task 3 |
| 字体加载策略 | Task 2 Step 2 |
| 验收标准 1–10 | Task 11 |

---

## 参考文档

| 文档 | 用途 |
|------|------|
| [2026-06-23-chat-role-theatre-design.md](../specs/2026-06-23-chat-role-theatre-design.md) | 设计 spec |
| [chat-ui-design.html](../../../chat-ui-design.html) | 视觉对照 |
| [2026-06-14-chat-issues-fix-design.md](../specs/2026-06-14-chat-issues-fix-design.md) | SSE done/error 行为 |
| [2026-06-12-chat-ui-redesign.md](./2026-06-12-chat-ui-redesign.md) | 第一轮已完成的欢迎页/侧栏基础 |
