# Chat UI Redesign Design

## Overview

按照 `chat-ui-preview.html` 原型的视觉设计，重新实现 Chat 页面的欢迎界面和周围 UI 元素。聊天气泡样式保持不变。

## Scope

**改动范围**：
- 整体容器样式（圆角、阴影、背景色）
- RoleList（添加图标 + 描述，调整 active 状态样式）
- ConversationList（宽度、按钮样式）
- ChatArea 欢迎界面（问候语 + 副标题 + 快捷卡片）
- 输入区域（toggle pill、按钮样式微调）

**不改动**：聊天气泡样式、消息渲染逻辑、SSE 通信、store 逻辑、API 层

## Design

### 1. 整体布局和容器

**当前**：`w-[1200px] rounded-[15px]`，无阴影，无背景色
**改为**：
```html
<div class="w-[1200px] mx-auto flex my-10 rounded-[20px] overflow-hidden bg-white shadow-[0_4px_24px_rgba(0,0,0,0.06),0_1px_4px_rgba(0,0,0,0.04)]" style="height: calc(100vh - 160px)">
```

三栏布局不变，ConversationList 宽度从 320px 改为 260px。

### 2. RoleList（左侧角色栏）

**当前**：只显示 label 文字，active 用 `bg-purple-300`
**改为**：
- 每个角色显示：emoji 图标 + 角色名 + 描述
- active 状态：左边框 3px `#6366f1`（indigo）+ 背景 `#eef2ff`
- hover 状态：`rgba(99,102,241,0.06)` 浅底色
- 背景色改为 `#f8f7ff`

**新增文件**：`apps/web/src/views/Chat/roleConfig.ts`

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

RoleList 从后端拿到 `ChatMode` 后，用 `role` 字段关联 `roleConfig` 取图标和描述。

### 3. ConversationList（中间对话栏）

**当前**：320px，顶部 el-button "新建对话"，背景 `bg-purple-50`
**改为**：
- 宽度 260px，背景 `#f8f7ff`
- 顶部 header：左侧 "对话" 标题（`text-[13px] font-bold text-gray-500`），右侧圆形 "+" 按钮（28px，bg `#6366f1`，hover `#4f46e5`）
- 对话列表项 active 改为 `bg-indigo-50 border-indigo-200`
- 空状态居中显示 "暂无对话" + "点击上方 + 新建"

### 4. ChatArea 欢迎界面

**新增文件**：`apps/web/src/views/Chat/components/WelcomeScreen.vue`

当 `chatStore.activeConversationId` 为 null 时显示：
- 居中布局，`fadeInUp` 入场动画
- 问候语：根据当前角色动态显示（从 `roleConfig` 取 `greeting`）
- 副标题：从 `roleConfig` 取 `subtitle`
- 快捷卡片：3 张横向排列

**卡片样式**：
- 宽度 240px，圆角 16px，hover 上浮 + 底部彩色线条动画
- 图标区域：44px 圆角方块，渐变背景色（按 color 字段映射）
- 标题 + 描述文字

**卡片颜色映射**（渐变背景 + 底部线条）：
- purple: `#eef2ff → #e0e7ff` / `#818cf8 → #6366f1`
- blue: `#eff6ff → #dbeafe` / `#60a5fa → #3b82f6`
- green: `#f0fdf4 → #dcfce7` / `#4ade80 → #22c55e`
- pink: `#fdf2f8 → #fce7f3` / `#f472b6 → #ec4899`
- rose: `#fff1f2 → #ffe4e6` / `#fb7185 → #f43f5e`
- amber: `#fffbeb → #fef3c7` / `#fbbf24 → #f59e0b`
- cyan: `#ecfeff → #cffafe` / `#22d3ee → #06b6d4`
- teal: `#f0fdfa → #ccfbf1` / `#2dd4bf → #14b8a6`
- orange: `#fff7ed → #ffedd5` / `#fb923c → #f97316`

**数据来源**：WelcomeScreen 直接从 `chatStore.activeRole` 读取当前角色，再用 `roleConfig[role]` 取 greeting、subtitle 和 cards。不需要传 prop。

**事件通信**：WelcomeScreen 通过 `emit('selectCard', placeholder, toggle)` 通知 ChatArea，ChatArea 处理 placeholder 更新和 toggle 状态切换。

### 5. 输入区域

**样式微调**：
- toggle pill：紫色系改为 indigo（`bg-indigo-100 border-indigo-400 text-indigo-700`），蓝色 pill 保持
- textarea：保持 el-input，添加 `auto-resize`（监听 input 事件，`style.height = min(scrollHeight, 120)px`）
- 发送按钮：`rounded-full`，bg `#6366f1`，hover `#4f46e5`
- 语音按钮：`rounded-full`，透明背景 + border，hover 变深

**行为不变**：深度思考/联网搜索互斥、Enter 发送、语音自动发送

## New Files

| File | Purpose |
|------|---------|
| `apps/web/src/views/Chat/roleConfig.ts` | 角色配置（图标、描述、问候语、快捷卡片） |
| `apps/web/src/views/Chat/components/WelcomeScreen.vue` | 欢迎界面组件 |

## Modified Files

| File | Changes |
|------|---------|
| `apps/web/src/views/Chat/index.vue` | 容器样式（圆角、阴影、背景色） |
| `apps/web/src/views/Chat/components/RoleList.vue` | 关联 roleConfig，添加图标+描述，调整 active 样式 |
| `apps/web/src/views/Chat/components/ConversationList.vue` | 宽度 260px，圆形按钮，header 布局调整 |
| `apps/web/src/views/Chat/components/ChatArea.vue` | 集成 WelcomeScreen，toggle pill 样式，按钮样式 |

## Dependencies

无新增依赖。使用现有 Tailwind CSS + Element Plus。
