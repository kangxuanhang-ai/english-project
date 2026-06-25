export const IS_SHOW_LOGIN = Symbol('IS_SHOW_LOGIN') // 是否显示登录框 表示唯一值 并且不可被篡改的

export type LoginType = 'login' | 'register' // 登录类型