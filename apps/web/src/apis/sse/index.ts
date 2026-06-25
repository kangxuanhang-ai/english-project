import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { Method } from 'axios'
import { ensureValidToken } from '@/apis/auth'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

export const CHAT_URL = '/ai/v1/chat'

export const sse = async <T, V = any>(
    url: string,
    method: Method = "POST",
    body: V,
    callback?: (data: T) => void,
    errorCallback?: (error: Error) => void,
    signal?: AbortSignal,
) => {
    const token = await ensureValidToken()
    if (!token) {
        ElMessage.error('登录已过期，请重新登录')
        useUserStore().logout()
        router.replace('/')
        return
    }

    fetchEventSource(url, {
        method: method.toLowerCase(),
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        openWhenHidden: false,
        signal,
        async onopen(response) {
            if (response.status === 401) {
                ElMessage.error('登录已过期，请重新登录')
                useUserStore().logout()
                router.replace('/')
                throw new Error('Unauthorized')
            }
            if (response.status === 429) {
                ElMessage.error('请求过于频繁，请稍后再试')
                throw new Error('Rate limited')
            }
            if (!response.ok) {
                const text = await response.text()
                throw new Error(text || `HTTP ${response.status}`)
            }
        },
        onmessage: (event) => {
            try {
                callback?.(JSON.parse(event.data) as T)
            } catch (e) {
                console.warn('SSE JSON parse error:', event.data, e)
            }
        },
        onerror(error) {
            errorCallback?.(error)
            throw error
        },
    })
}
