import { Navigate } from 'react-router-dom'
import { createBrowserRouter } from 'react-router-dom'
import type { ReactNode } from 'react'
import AdminLayout from '@/layout/AdminLayout'
import DashboardPage from '@/views/Dashboard'
import LoginPage from '@/views/Login'
import KnowledgeListPage from '@/views/knowledge/List'
import KnowledgeDetailPage from '@/views/knowledge/Detail'
import KnowledgeSearchPage from '@/views/knowledge/Search'
import AnalyticsOverviewPage from '@/views/analytics/Overview'
import CourseListPage from '@/views/courses/List'
import CourseFormPage from '@/views/courses/Form'
import OrderListPage from '@/views/orders/List'
import OrderDetailPage from '@/views/orders/Detail'
import UserListPage from '@/views/users/List'
import UserDetailPage from '@/views/users/Detail'
import McpTemplatesPage from '@/views/mcp-templates/List'
import { useUserStore } from '@/stores/user'

function RequireAdmin({ children }: { children: ReactNode }) {
  const token = useUserStore.getState().accessToken
  const user = useUserStore.getState().user
  if (!token || user?.role !== 'admin') {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function GuestOnly({ children }: { children: ReactNode }) {
  const token = useUserStore.getState().accessToken
  const user = useUserStore.getState().user
  if (token && user?.role === 'admin') {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

export const router = createBrowserRouter(
  [
  {
    path: '/login',
    element: (
      <GuestOnly>
        <LoginPage />
      </GuestOnly>
    ),
  },
  {
    path: '/',
    element: (
      <RequireAdmin>
        <AdminLayout />
      </RequireAdmin>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'knowledge', element: <KnowledgeListPage /> },
      { path: 'knowledge/search', element: <KnowledgeSearchPage /> },
      { path: 'knowledge/:id', element: <KnowledgeDetailPage /> },
      { path: 'users', element: <UserListPage /> },
      { path: 'users/:id', element: <UserDetailPage /> },
      { path: 'courses', element: <CourseListPage /> },
      { path: 'courses/new', element: <CourseFormPage /> },
      { path: 'courses/:id/edit', element: <CourseFormPage /> },
      { path: 'orders', element: <OrderListPage /> },
      { path: 'orders/:id', element: <OrderDetailPage /> },
      { path: 'analytics', element: <AnalyticsOverviewPage /> },
      { path: 'mcp-templates', element: <McpTemplatesPage /> },
    ],
  },
  ],
  { basename: import.meta.env.BASE_URL.replace(/\/$/, '') || undefined },
)
