export interface Paginated<T> {
  list: T[]
  total: number
}

export interface TrendPoint {
  date: string
  count: number
}

export interface AdminDashboard {
  userCount: number
  todayNewUsers: number
  courseCount: number
  todayOrders: number
  totalRevenue: number
  todayRevenue: number
  knowledgeDocCount: number
  knowledgeReadyCount: number
  unpaidOrders: number
  failedKnowledgeDocs: number
  todayPv: number
  todayUv: number
  recentErrors: number
  newUsersTrend: TrendPoint[]
  pvTrend: TrendPoint[]
}

export interface AdminUserItem {
  id: string
  name: string
  email?: string | null
  phone: string
  avatar?: string | null
  wordNumber: number
  dayNumber: number
  role: string
  masteredWords?: number
  createdAt?: string | null
  lastLoginAt?: string | null
}

export interface AdminUserDetail extends AdminUserItem {
  masteredWords: number
  purchasedCourses: number
  recentCourses: { id: string; name: string; value: string; purchasedAt?: string | null }[]
}

export interface AdminCourse {
  id: string
  name: string
  value: string
  description?: string | null
  teacher: string
  url: string
  price: number
  isPublished: boolean
  createdAt?: string | null
  updatedAt?: string | null
}

export interface AdminOrder {
  id: string
  outTradeNo: string
  tradeNo?: string | null
  amount: number
  subject: string
  tradeStatus: string
  sendPayTime?: string | null
  createdAt?: string | null
  userId: string
  userName?: string | null
  userPhone?: string | null
}

export interface AdminOrderDetail extends AdminOrder {
  body?: string | null
  courses: { id: string; name: string; value: string }[]
}

export type CourseValue = 'gk' | 'zk' | 'gre' | 'toefl' | 'ielts' | 'cet6' | 'cet4' | 'ky'

export const COURSE_VALUE_OPTIONS: { label: string; value: CourseValue }[] = [
  { label: '高考', value: 'gk' },
  { label: '中考', value: 'zk' },
  { label: 'GRE', value: 'gre' },
  { label: '托福', value: 'toefl' },
  { label: '雅思', value: 'ielts' },
  { label: '六级', value: 'cet6' },
  { label: '四级', value: 'cet4' },
  { label: '考研', value: 'ky' },
]

export const TRADE_STATUS_MAP: Record<string, { label: string; color: string }> = {
  NOT_PAY: { label: '未支付', color: 'default' },
  WAIT_BUYER_PAY: { label: '待支付', color: 'processing' },
  TRADE_CLOSED: { label: '已关闭', color: 'default' },
  TRADE_SUCCESS: { label: '支付成功', color: 'success' },
  TRADE_FINISHED: { label: '已完成', color: 'success' },
}

export interface AdminAnalyticsOverview {
  days: number
  pvTrend: TrendPoint[]
  uvTrend: TrendPoint[]
}

export interface AdminPageRankItem {
  path: string
  count: number
}

export interface AdminAnalyticsPages {
  days: number
  list: AdminPageRankItem[]
}

export interface AdminErrorItem {
  id: string
  error: string
  message?: string | null
  stack?: string | null
  url?: string | null
  visitorId: string
  createdAt?: string | null
}

export interface AdminPerformanceAvg {
  fp?: number | null
  fcp?: number | null
  lcp?: number | null
  inp?: number | null
  cls?: number | null
}

export interface AdminPerformanceTrendPoint {
  date: string
  lcp?: number | null
  fcp?: number | null
}

export interface AdminAnalyticsPerformance {
  days: number
  avg: AdminPerformanceAvg
  trend: AdminPerformanceTrendPoint[]
}
