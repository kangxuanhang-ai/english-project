import md5 from 'md5'
import { api, type ApiResponse } from '@/apis'
import type { WebResultUser } from '@en/common/user'

export async function login(phone: string, password: string) {
  return api.post<unknown, ApiResponse<WebResultUser>>('/user/login', {
    phone,
    password: md5(password),
  })
}
