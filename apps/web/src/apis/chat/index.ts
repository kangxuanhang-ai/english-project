import { aiApi, type Response } from '..'
import type { ChatModeList, ChatRoleType, ChatMessageList, Conversation } from '@en/common/chat'

// 获取消息模式列表
export const getChatMode = () =>
    aiApi.get('/prompt/list') as Promise<Response<ChatModeList>>

// 获取历史记录（参数改为 conversationId）
export const getChatHistory = (conversationId: string) =>
    aiApi.get(`/chat/history?conversationId=${conversationId}`) as Promise<
        Response<{ messages: ChatMessageList; truncated: boolean }>
    >

// 新建对话
export const createConversation = (role: ChatRoleType) =>
    aiApi.post('/chat/conversations', { role }) as Promise<Response<Conversation>>

// 获取对话列表
export const getConversations = (role: ChatRoleType) =>
    aiApi.get(`/chat/conversations?role=${role}`) as Promise<Response<Conversation[]>>

// 删除对话
export const deleteConversationApi = (id: string) =>
    aiApi.delete(`/chat/conversations/${id}`) as Promise<Response<void>>

// 生成标题（路由在 conversation router 下）
export const generateTitle = (conversationId: string, firstMessage: string) =>
    aiApi.post('/chat/conversations/title', { conversationId, firstMessage }) as Promise<Response<{ id: string; title: string }>>
