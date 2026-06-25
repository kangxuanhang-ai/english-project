import type { ChatRoleType } from '@en/common/chat'

export interface RoleTheme {
  accent: string
  accentDark: string
  accentLight: string
  accentSoft: string
  accentBorder: string
  accentText: string
  iconBg: string
}

export interface RoleCard {
  icon: string
  color: string
  title: string
  desc: string
  placeholder: string
  toggle?: 'deep' | 'web'
}

export interface RoleInfo {
  label: string
  theme: RoleTheme
  icon: string
  desc: string
  greeting: string
  subtitle: string
  cards: RoleCard[]
}

export const roleConfig: Record<ChatRoleType, RoleInfo> = {
  normal: {
    label: '智能助手',
    theme: {
      accent: '#6366f1',
      accentDark: '#4f46e5',
      accentLight: '#818cf8',
      accentSoft: '#eef2ff',
      accentBorder: '#c7d2fe',
      accentText: '#4338ca',
      iconBg: 'linear-gradient(135deg,#818cf8,#6366f1)',
    },
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
    label: '英语大师',
    theme: {
      accent: '#7c3aed',
      accentDark: '#6d28d9',
      accentLight: '#a78bfa',
      accentSoft: '#f5f3ff',
      accentBorder: '#ddd6fe',
      accentText: '#5b21b6',
      iconBg: 'linear-gradient(135deg,#a78bfa,#7c3aed)',
    },
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
    label: '商务英语',
    theme: {
      accent: '#2563eb',
      accentDark: '#1d4ed8',
      accentLight: '#60a5fa',
      accentSoft: '#eff6ff',
      accentBorder: '#bfdbfe',
      accentText: '#1e40af',
      iconBg: 'linear-gradient(135deg,#60a5fa,#2563eb)',
    },
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
    label: '麒麟哥',
    theme: {
      accent: '#e11d48',
      accentDark: '#be123c',
      accentLight: '#fb7185',
      accentSoft: '#fff1f2',
      accentBorder: '#fecdd3',
      accentText: '#9f1239',
      iconBg: 'linear-gradient(135deg,#fb7185,#e11d48)',
    },
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
    label: '小满模式',
    theme: {
      accent: '#0891b2',
      accentDark: '#0e7490',
      accentLight: '#22d3ee',
      accentSoft: '#ecfeff',
      accentBorder: '#a5f3fc',
      accentText: '#155e75',
      iconBg: 'linear-gradient(135deg,#22d3ee,#0891b2)',
    },
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
  oral: {
    label: '口语考官',
    theme: {
      accent: '#0d9488',
      accentDark: '#0f766e',
      accentLight: '#2dd4bf',
      accentSoft: '#f0fdfa',
      accentBorder: '#99f6e4',
      accentText: '#115e59',
      iconBg: 'linear-gradient(135deg,#2dd4bf,#0d9488)',
    },
    icon: '🎙️',
    desc: '英文陪练·纠错',
    greeting: 'Hello! 🎙️',
    subtitle: "I'm your speaking examiner. Let's practice in English.",
    cards: [
      { icon: '🗣️', color: 'teal', title: '自我介绍', desc: 'Practice a 1-minute self introduction', placeholder: 'Tap mic and introduce yourself in English...' },
      { icon: '✈️', color: 'cyan', title: '旅行场景', desc: 'Role-play at the airport or hotel', placeholder: 'Tell me about your last trip...' },
      { icon: '💼', color: 'green', title: '面试模拟', desc: 'Answer common interview questions', placeholder: 'Describe your strengths in English...' },
    ]
  },
}

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
