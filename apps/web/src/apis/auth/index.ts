import axios from 'axios'
import type { Token } from '@en/common/user'
import type { Response } from '../index'
import { useUserStore } from '@/stores/user'
import type { AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const refreshServer = axios.create({
    baseURL: '/api/v1',
    timeout: 50000,
})

//响应拦截器
refreshServer.interceptors.response.use(res => {
    return res.data
}, error => {
    return Promise.reject(error)
})

//导出刷新token的接口了
export const refreshTokenApi = (data: Omit<Token, 'accessToken'>) => refreshServer.post('/user/refresh-token', data) as Promise<Response<Token>>

//为什么要分开 隔离起来 防止死循环
//隔离起来 这个接口是不会携带token的 因为我们携带token是在serverApi携带token
//安全策略

/**
 * 统一 token 有效性检查，5s buffer。
 * 返回有效 token 字符串，或 null（需要重新登录）。
 */
export async function ensureValidToken(): Promise<string | null> {
    const userStore = useUserStore()
    const token = userStore.getAccessToken
    const refreshToken = userStore.getRefreshToken
    if (!token || !refreshToken) return null
    try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (Date.now() >= (payload.exp * 1000 - 5000)) {
            const result = await refreshTokenApi({ refreshToken })
            if (result.success) {
                userStore.updateToken(result.data)
                return result.data.accessToken
            }
            return null
        }
        return token
    } catch {
        return null
    }
}

/**
 * 401 拦截器工厂函数。
 * 每个 Axios 实例独立的 isRefreshing 和 requestQueue，避免共享队列。
 */
export function createAuthInterceptor(getApi: () => AxiosInstance) {
    let isRefreshing = false
    let requestQueue: ((newAccessToken: string) => void)[] = []

    return async (error: any) => {
        if (error.code === 'ERR_NETWORK') {
            ElMessage.error('网络连接失败,请重试')
            return Promise.reject(error)
        }
        if (error.response?.status !== 401) {
            const msg = error.response?.data?.message || '服务器异常,请稍后再试'
            ElMessage.error(msg)
            return Promise.reject(error)
        }

        const userStore = useUserStore()
        const accessToken = userStore.getAccessToken
        const refreshToken = userStore.getRefreshToken
        const originalRequest = error.config

        if (!accessToken || !refreshToken) {
            userStore.logout()
            ElMessage.error('登录已过期,请重新登录')
            router.replace('/')
            return Promise.reject(error)
        }

        if (isRefreshing) {
            return new Promise((resolve) => {
                requestQueue.push((newAccessToken: string) => {
                    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
                    resolve(getApi()(originalRequest))
                })
            })
        }

        isRefreshing = true
        try {
            const newToken = await refreshTokenApi({ refreshToken })
            if (newToken.success) {
                userStore.updateToken(newToken.data)
            } else {
                userStore.logout()
                ElMessage.error('登录已过期,请重新登录')
                router.replace('/')
                return Promise.reject(error)
            }
            const newAccessToken = newToken.data.accessToken
            requestQueue.forEach(callback => callback(newAccessToken))
            return getApi()(originalRequest)
        } catch (err) {
            return Promise.reject(err)
        } finally {
            requestQueue = []
            isRefreshing = false
        }
    }
}