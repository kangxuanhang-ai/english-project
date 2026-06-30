import {
  ApiOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  HomeOutlined,
  LineChartOutlined,
  LogoutOutlined,
  ReadOutlined,
  ShoppingOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Avatar, Breadcrumb, Button, Layout, Menu, Space, Typography } from 'antd'
import { useMemo, useState, type ReactNode } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useUserStore } from '@/stores/user'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库' },
  { key: '/users', icon: <TeamOutlined />, label: '用户管理' },
  { key: '/courses', icon: <ReadOutlined />, label: '课程管理' },
  { key: '/orders', icon: <ShoppingOutlined />, label: '订单管理' },
  { key: '/analytics', icon: <LineChartOutlined />, label: '数据监控' },
  { key: '/mcp-templates', icon: <ApiOutlined />, label: '外部 MCP' },
]

const routeLabels: Record<string, string> = {
  '/': '仪表盘',
  '/knowledge': '知识库',
  '/knowledge/search': '检索测试',
  '/users': '用户管理',
  '/courses': '课程管理',
  '/orders': '订单管理',
  '/analytics': '数据监控',
  '/mcp-templates': '外部 MCP',
}

function buildBreadcrumbs(pathname: string) {
  const items: { title: ReactNode; path?: string }[] = [
    { title: <HomeOutlined />, path: '/' },
  ]
  if (pathname === '/') {
    items.push({ title: '仪表盘' })
    return items
  }
  const segments = pathname.split('/').filter(Boolean)
  let acc = ''
  for (let i = 0; i < segments.length; i++) {
    acc += `/${segments[i]}`
    const isLast = i === segments.length - 1
    const isId = /^[0-9a-f-]{36}$/i.test(segments[i]) || segments[i].length > 20
    const label = isId
      ? isLast
        ? '详情'
        : (routeLabels[acc.replace(/\/[^/]+$/, '')] ?? segments[i])
      : (routeLabels[acc] ??
        (segments[i] === 'new' ? '新建' : segments[i] === 'edit' ? '编辑' : segments[i]))
    items.push(isLast ? { title: label } : { title: label, path: acc })
  }
  return items
}

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useUserStore((s) => s.user)
  const logout = useUserStore((s) => s.logout)
  const [collapsed, setCollapsed] = useState(false)

  const selectedKey =
    menuItems.find((item) => item.key !== '/' && location.pathname.startsWith(item.key))?.key ?? '/'

  const breadcrumbs = useMemo(() => buildBreadcrumbs(location.pathname), [location.pathname])
  const initial = (user?.name ?? '管').slice(0, 1).toUpperCase()

  const breadcrumbItems = breadcrumbs.map((item, index) => ({
    title:
      item.path && index < breadcrumbs.length - 1 ? (
        <span
          role="link"
          tabIndex={0}
          style={{ cursor: 'pointer' }}
          onClick={() => navigate(item.path!)}
          onKeyDown={(e) => e.key === 'Enter' && navigate(item.path!)}
        >
          {item.title}
        </span>
      ) : (
        item.title
      ),
  }))

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        collapsedWidth={72}
        theme="light"
        className="admin-sider"
        style={{ borderRight: '1px solid #e4e4e7' }}
      >
        <div
          className="admin-logo"
          style={{
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '0 8px' : '0 20px',
          }}
        >
          <div className="admin-logo-mark">E</div>
          {!collapsed && (
            <div>
              <div className="admin-logo-text-main">English</div>
              <div className="admin-logo-text-sub">管理后台</div>
            </div>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderInline: 'none', padding: '8px 12px' }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            height: 56,
            lineHeight: '56px',
            background: '#fff',
            borderBottom: '1px solid #e4e4e7',
            paddingInline: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Breadcrumb items={breadcrumbItems} />
          <Space size={12}>
            <Avatar size={32} style={{ background: '#eef2ff', color: '#4338ca', fontWeight: 600 }}>
              {initial}
            </Avatar>
            <Typography.Text strong style={{ fontSize: 14 }}>
              {user?.name ?? '管理员'}
            </Typography.Text>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 24, background: '#faf9f6' }}>
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
