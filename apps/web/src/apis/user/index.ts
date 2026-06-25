import { serverApi, type Response } from '..';
import type { UserLogin, UserRegister,WebResultUser,AvatarResult,UserUpdate } from "@en/common/user";

//用户登录
export const login = (data: UserLogin) => serverApi.post('/user/login', data) as Promise<Response<WebResultUser>>
//用户注册
export const register = (data: UserRegister) => serverApi.post('/user/register', data) as Promise<Response<WebResultUser>>
//上传头像
export const uploadAvatar = (file: FormData) => serverApi.post('/user/upload-avatar', file) as Promise<Response<AvatarResult>>
//更新用户信息
export const updateUser = (data: UserUpdate) => serverApi.post('/user/update-user', data) as Promise<Response<UserUpdate>>
//用户打卡
export const checkIn = () => serverApi.post('/user/check-in') as Promise<Response<{ dayNumber: number; checkedIn: boolean }>>

// 学习数据看板
export const getDashboard = () => serverApi.get('/user/dashboard') as Promise<Response<import('@en/common/user').DashboardStats>>

