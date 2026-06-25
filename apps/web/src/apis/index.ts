import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { createAuthInterceptor } from './auth'

export const uploadUrl = import.meta.env.VITE_MINIO_ENDPOINT
export const socketUrl = import.meta.env.VITE_SOCKET_URL
export const timeout = 50000

// server 服务器接口
export const serverApi = axios.create({
    baseURL: '/api/v1',
    timeout,
})

// 请求拦截器
serverApi.interceptors.request.use(config => {
    const userStore = useUserStore()
    if (userStore.getAccessToken) {
        config.headers.Authorization = `Bearer ${userStore.getAccessToken}`
    }
    return config
})

// 响应拦截器 — 使用工厂函数
serverApi.interceptors.response.use(res => {
    return res.data
}, createAuthInterceptor(() => serverApi))

// ai 服务器接口
export const aiApi = axios.create({
    baseURL: '/ai/v1',
    timeout,
})

// 请求拦截器
aiApi.interceptors.request.use(config => {
    const userStore = useUserStore()
    if (userStore.getAccessToken) {
        config.headers.Authorization = `Bearer ${userStore.getAccessToken}`
    }
    return config
})

// 响应拦截器 — 使用工厂函数
aiApi.interceptors.response.use(res => {
    return res.data
}, createAuthInterceptor(() => aiApi))

export interface Response<T = any> {
    timestamp: string,
    path: string,
    message: string,
    code: number,
    success: boolean,
    data: T
}
