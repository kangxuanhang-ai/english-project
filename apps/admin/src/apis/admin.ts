import { api, type ApiResponse } from '@/apis'
import { useUserStore } from '@/stores/user'
import type {
  AdminAnalyticsOverview,
  AdminAnalyticsPages,
  AdminAnalyticsPerformance,
  AdminCourse,
  AdminDashboard,
  AdminErrorItem,
  AdminOrder,
  AdminOrderDetail,
  AdminUserDetail,
  AdminUserItem,
  Paginated,
} from '@en/common/admin'
import type {
  KnowledgeChunkItem,
  KnowledgeDocumentItem,
  KnowledgeSearchResult,
} from '@en/common/knowledge'
import type { AdminMcpTemplateItem } from '@en/common/external-mcp'

export function fetchDashboard() {
  return api.get<unknown, ApiResponse<AdminDashboard>>('/admin/dashboard')
}

export function fetchUsers(params: {
  page: number
  pageSize: number
  keyword?: string
  role?: 'user' | 'admin'
}) {
  return api.get<unknown, ApiResponse<Paginated<AdminUserItem>>>('/admin/users', { params })
}

export function fetchUserDetail(id: string) {
  return api.get<unknown, ApiResponse<AdminUserDetail>>(`/admin/users/${id}`)
}

export function fetchCourses(params: { page: number; pageSize: number }) {
  return api.get<unknown, ApiResponse<Paginated<AdminCourse>>>('/admin/courses', { params })
}

export function fetchCourse(id: string) {
  return api.get<unknown, ApiResponse<AdminCourse>>(`/admin/courses/${id}`)
}

export function uploadCourseCover(file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post<unknown, ApiResponse<{ url: string; path: string }>>(
    '/admin/courses/upload-cover',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

export function createCourse(body: Omit<AdminCourse, 'id' | 'isPublished' | 'createdAt' | 'updatedAt'>) {
  return api.post('/admin/courses', body)
}

export function updateCourse(id: string, body: Partial<AdminCourse>) {
  return api.put(`/admin/courses/${id}`, body)
}

export function publishCourse(id: string) {
  return api.put(`/admin/courses/${id}/publish`)
}

export function unpublishCourse(id: string) {
  return api.put(`/admin/courses/${id}/unpublish`)
}

export function fetchOrders(params: {
  page: number
  pageSize: number
  status?: string
  startDate?: string
  endDate?: string
  keyword?: string
}) {
  return api.get<unknown, ApiResponse<Paginated<AdminOrder>>>('/admin/orders', { params })
}

export function fetchOrderDetail(id: string) {
  return api.get<unknown, ApiResponse<AdminOrderDetail>>(`/admin/orders/${id}`)
}

export type OrderExportParams = {
  status?: string
  startDate?: string
  endDate?: string
  keyword?: string
}

export async function downloadOrdersCsv(params: OrderExportParams) {
  const token = useUserStore.getState().accessToken
  const search = new URLSearchParams()
  if (params.status) search.set('status', params.status)
  if (params.startDate) search.set('startDate', params.startDate)
  if (params.endDate) search.set('endDate', params.endDate)
  if (params.keyword) search.set('keyword', params.keyword)
  const qs = search.toString()
  const url = `/api/v1/admin/orders/export${qs ? `?${qs}` : ''}`
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('导出失败')
  const blob = await res.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = `orders-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(blobUrl)
}

export function fetchKnowledgeDocs(params: {
  page: number
  pageSize: number
  keyword?: string
  status?: string
}) {
  return api.get<unknown, ApiResponse<Paginated<KnowledgeDocumentItem>>>(
    '/admin/knowledge',
    { params },
  )
}

export function fetchKnowledgeDoc(id: string) {
  return api.get<unknown, ApiResponse<KnowledgeDocumentItem>>(
    `/admin/knowledge/${id}`,
  )
}

export function fetchKnowledgeChunks(id: string, params: { page: number; pageSize: number }) {
  return api.get<unknown, ApiResponse<Paginated<KnowledgeChunkItem>>>(
    `/admin/knowledge/${id}/chunks`,
    { params },
  )
}

export function uploadKnowledgeFile(file: File, title?: string) {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  return api.post<
    unknown,
    ApiResponse<{ id: string; status: string }>
  >('/admin/knowledge/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function updateKnowledgeTitle(id: string, title: string) {
  return api.put(`/admin/knowledge/${id}`, { title })
}

export function deleteKnowledgeDoc(id: string) {
  return api.delete(`/admin/knowledge/${id}`)
}

export function reindexKnowledgeDoc(id: string) {
  return api.post(`/admin/knowledge/${id}/reindex`)
}

export function searchKnowledge(params: { q: string; topK?: number }) {
  return api.get<unknown, ApiResponse<KnowledgeSearchResult>>(
    '/admin/knowledge/search',
    { params },
  )
}

export function fetchKnowledgeDownloadUrl(id: string) {
  return api.get<unknown, ApiResponse<{ url: string }>>(`/admin/knowledge/${id}/download`)
}

export function fetchAnalyticsOverview(days: 7 | 30) {
  return api.get<unknown, ApiResponse<AdminAnalyticsOverview>>('/admin/analytics/overview', {
    params: { days },
  })
}

export function fetchAnalyticsPages(days: 7 | 30) {
  return api.get<unknown, ApiResponse<AdminAnalyticsPages>>('/admin/analytics/pages', {
    params: { days },
  })
}

export function fetchAnalyticsErrors(params: { page: number; pageSize: number }) {
  return api.get<unknown, ApiResponse<Paginated<AdminErrorItem>>>('/admin/analytics/errors', {
    params,
  })
}

export function fetchAnalyticsPerformance(days: 7 | 30) {
  return api.get<unknown, ApiResponse<AdminAnalyticsPerformance>>('/admin/analytics/performance', {
    params: { days },
  })
}

export function fetchMcpTemplates() {
  return api.get<unknown, ApiResponse<AdminMcpTemplateItem[]>>('/admin/mcp-templates')
}

export function updateMcpTemplate(
  id: string,
  body: Partial<{
    url: string
    description: string
    globallyEnabled: boolean
    headerSchema: Record<string, unknown>
    exposedTools: string[]
    fetchUrlAllowlist: string[]
  }>,
) {
  return api.put(`/admin/mcp-templates/${id}`, body)
}

export function testMcpTemplate(id: string) {
  return api.post<unknown, ApiResponse<{ tools: unknown[]; template: AdminMcpTemplateItem }>>(
    `/admin/mcp-templates/${id}/test`,
  )
}
