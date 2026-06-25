import axios from 'axios'
import { useUserStore } from '@/stores/user'

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = useUserStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (error) => {
    if (error.response?.status === 401) {
      useUserStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export async function adminPing() {
  return api.get<unknown, ApiResponse<{ ok: boolean }>>('/admin/ping')
}
