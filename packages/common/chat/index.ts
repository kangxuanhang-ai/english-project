export type ChatRole = 'human' | 'ai';
export type ChatRoleType = 'normal' | 'master' | 'business' | 'qilinge' | 'xiaoman' | 'oral';
export type ChatMessageType = 'reasoning' | 'chat' | 'tool' | 'tool_result' | 'done' | 'error';
export type ChatStatus = 'loading' | 'tool_calling' | 'tool_done' | 'error';
export type ChatRecommendCourse = {
    course_id: string | null
    title: string
    reason: string
    match_score: number
}

export type ChatRecommendDailyPlan = {
    new_words_per_day: number
    review_frequency: string
    estimated_completion: string
}

/** 聊天气泡内嵌的推荐区块（方案 B，非首页卡片） */
export type ChatRecommendBlock = {
    courses: ChatRecommendCourse[]
    daily_plan?: ChatRecommendDailyPlan
    summary?: string
}

/** grammar_check 工具结果卡片 */
export type ChatGrammarBlock = {
    ok: boolean
    summary?: string
    error?: string
    original?: string
    corrected?: string
    explanation?: string
}

export type ChatPurchaseAction = 'confirm' | 'resume_pay' | 'already_owned' | 'not_found'

/** course_purchase 工具结构化结果 */
export type ChatPurchaseBlock = {
    action: ChatPurchaseAction
    message?: string
    /** 用户选择的推荐序号（1 起） */
    selectedIndex?: number
    /** 当前对话推荐列表标题，便于确认 */
    recommendTitles?: string[]
    course?: {
        id: string
        name: string
        value: string
        description?: string
        teacher: string
        url: string
        price: string
        purchased: boolean
    }
}

export type ChatMessage = {
    id?: string
    role: ChatRole
    content: string;
    /** course_recommendation 工具返回后、卡片下方的补充文字 */
    contentAfter?: string
    reasoning?: string;
    type: ChatMessageType
    status?: ChatStatus
    toolId?: string
    toolName?: string
    /** 历史回放时工具输出摘要（word_lookup 等） */
    toolSummary?: string
    toolInput?: string
    toolOutput?: string
    /** 历史回放 / 流式结束时内嵌的推荐卡片数据 */
    recommendBlock?: ChatRecommendBlock
    /** grammar_check 工具结果卡片 */
    grammarBlock?: ChatGrammarBlock
    /** course_purchase 工具结果（already_owned 时展示去学习按钮） */
    purchaseBlock?: ChatPurchaseBlock
    originalContent?: string  // 重试时用的原始用户消息
    streaming?: boolean       // SSE 流式输出中，完成前用纯文本展示
}
export type ChatMessageList = ChatMessage[]

/** SSE 服务端推送的 wire format（短字段名） */
export type ChatSSEMessage = {
    type: ChatMessageType
    content?: string
    role?: ChatRole
    reasoning?: string
    id?: string
    tool?: string
    input?: string
    output?: string
    /** course_recommendation 工具结果的结构化卡片数据 */
    recommendBlock?: ChatRecommendBlock
    /** grammar_check 工具结果的结构化卡片数据 */
    grammarBlock?: ChatGrammarBlock
    /** course_purchase 工具结果的结构化数据 */
    purchaseBlock?: ChatPurchaseBlock
    message?: string  // error 事件的错误信息
}

export type ChatMode = {
    label: string;
    id: string;
    role: ChatRoleType;
}
export type ChatModeList = ChatMode[]

export type ChatDto = {
    conversationId: string  // 新增必填
    deepThink: boolean;
    webSearch: boolean;
    role: ChatRoleType;
    content: string;
}

/** 对话元数据 */
export type Conversation = {
    id: string
    role: ChatRoleType
    title: string
    createdAt: string
    updatedAt: string
}
