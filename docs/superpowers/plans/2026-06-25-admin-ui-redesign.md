# B 端管理后台 UI 翻新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `apps/admin` 全站 UI 翻新为与 C 端统一的 Indigo 品牌风格，引入主题 token、布局壳与公共组件，覆盖 12 个已挂载 view（不含 Login）。

**Architecture:** 先落地 `antd-theme.ts` + `admin-theme.css` + 5 个公共组件，再重写 `AdminLayout` 与 `Login`，最后逐页迁移 List/Detail/Form。不改后端 API、路由或业务逻辑；删除无路由引用的 `Placeholder.tsx`。

**Tech Stack:** React 18, Ant Design 5, Vite, TanStack Query, @ant-design/plots, dayjs

**设计文档:** [2026-06-25-admin-ui-redesign-design.md](../specs/2026-06-25-admin-ui-redesign-design.md)

**测试说明:** 仓库无 vitest 基础设施；各 Task 用 `pnpm --filter @en/admin build` + 浏览器手动验收（登录、侧栏、各列表/详情页）。

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/admin/src/theme/antd-theme.ts` | Create | 导出 `adminTheme` ConfigProvider token |
| `apps/admin/src/styles/admin-theme.css` | Create | CSS 变量、字体 import、布局/登录/StatCard 样式 |
| `apps/admin/src/components/PageShell.tsx` | Create | 统一页面标题区 + back/extra |
| `apps/admin/src/components/FilterCard.tsx` | Create | 筛选区 Card 容器 |
| `apps/admin/src/components/DataCard.tsx` | Create | 表格/Descriptions Card 容器 |
| `apps/admin/src/components/StatCard.tsx` | Create | 仪表盘指标卡 |
| `apps/admin/src/components/EmptyHint.tsx` | Create | 统一 Empty 状态 |
| `apps/admin/src/components/index.ts` | Create | barrel export |
| `apps/admin/src/main.tsx` | Modify | 接入 theme + css |
| `apps/admin/src/layout/AdminLayout.tsx` | Rewrite | 浅色侧栏 240px、面包屑、头像 |
| `apps/admin/src/views/Login.tsx` | Rewrite | 左右分栏渐变登录 |
| `apps/admin/src/views/Dashboard.tsx` | Rewrite | StatCard + Indigo 图表 |
| `apps/admin/src/views/orders/List.tsx` | Modify | PageShell + FilterCard + DataCard |
| `apps/admin/src/views/orders/Detail.tsx` | Modify | PageShell back + DataCard |
| `apps/admin/src/views/users/List.tsx` | Modify | 同上 |
| `apps/admin/src/views/users/Detail.tsx` | Modify | 同上 |
| `apps/admin/src/views/courses/List.tsx` | Modify | PageShell extra + DataCard |
| `apps/admin/src/views/courses/Form.tsx` | Modify | PageShell back + 表单 Card |
| `apps/admin/src/views/knowledge/List.tsx` | Modify | PageShell + FilterCard + Dragger + DataCard |
| `apps/admin/src/views/knowledge/Detail.tsx` | Modify | PageShell back + DataCard |
| `apps/admin/src/views/knowledge/Search.tsx` | Modify | PageShell + 结果列表样式 |
| `apps/admin/src/views/analytics/Overview.tsx` | Modify | PageShell + StatCard + DataCard |
| `apps/admin/src/views/Placeholder.tsx` | Delete | 无路由引用 |
| `docs/superpowers/specs/2026-06-25-admin-ui-redesign-design.md` | Modify | 状态改为「已评审，计划已编写」 |

---

## Phase 1 — 主题与公共组件

> **完成标准:** `pnpm --filter @en/admin build` 通过；组件可独立 import。

---

### Task 1.1: Ant Design 主题 token

**Files:**
- Create: `apps/admin/src/theme/antd-theme.ts`
- Modify: `apps/admin/src/main.tsx`

- [ ] **Step 1:** 创建 `antd-theme.ts`：

```typescript
import type { ThemeConfig } from 'antd'

export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: '#4338ca',
    colorLink: '#4338ca',
    colorBgLayout: '#faf9f6',
    colorBgContainer: '#ffffff',
    colorText: '#18181b',
    colorTextSecondary: '#71717a',
    colorBorder: '#e4e4e7',
    borderRadius: 12,
    borderRadiusLG: 16,
    fontFamily: "'Plus Jakarta Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    controlHeight: 36,
    controlHeightLG: 40,
  },
  components: {
    Layout: {
      siderBg: '#ffffff',
      headerBg: '#ffffff',
      bodyBg: '#faf9f6',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#eef2ff',
      itemSelectedColor: '#4338ca',
      itemHoverBg: '#f4f4f5',
      itemBorderRadius: 10,
      iconSize: 16,
    },
    Card: { paddingLG: 20 },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#71717a',
      rowHoverBg: '#faf9ff',
    },
    Button: {
      primaryShadow: '0 2px 0 rgba(67,56,202,0.08)',
    },
  },
}
```

- [ ] **Step 2:** 修改 `main.tsx`，接入 theme（css 在 Task 1.2 添加）：

```typescript
import { adminTheme } from '@/theme/antd-theme'

// 在 ConfigProvider 上：
<ConfigProvider locale={zhCN} theme={adminTheme}>
```

- [ ] **Step 3:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS（此时 css 尚未引入，build 仍应成功）

---

### Task 1.2: 全局 CSS 与样式变量

**Files:**
- Create: `apps/admin/src/styles/admin-theme.css`
- Modify: `apps/admin/src/main.tsx`

- [ ] **Step 1:** 创建 `admin-theme.css`：

```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

:root {
  --admin-primary: #4338ca;
  --admin-primary-hover: #6366f1;
  --admin-primary-light: #eef2ff;
  --admin-bg-layout: #faf9f6;
  --admin-bg-container: #ffffff;
  --admin-border: #e4e4e7;
  --admin-text-primary: #18181b;
  --admin-text-secondary: #71717a;
  --admin-text-tertiary: #a1a1aa;
  --admin-shadow-card: 0 1px 2px rgba(24, 24, 27, 0.04), 0 4px 16px rgba(67, 56, 202, 0.06);
  --admin-shadow-elevated: 0 8px 32px rgba(67, 56, 202, 0.12);
}

body {
  margin: 0;
  background: var(--admin-bg-layout);
}

/* 内容区路由切换淡入 */
.admin-content-inner {
  max-width: 1440px;
  margin: 0 auto;
  animation: adminFadeIn 150ms ease;
}

@keyframes adminFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 侧栏 Logo */
.admin-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 64px;
  padding: 0 20px;
  border-bottom: 1px solid var(--admin-border);
}

.admin-logo-mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--admin-primary);
  color: #fff;
  font-weight: 700;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.admin-logo-text-main {
  font-size: 15px;
  font-weight: 600;
  color: var(--admin-text-primary);
  line-height: 1.2;
}

.admin-logo-text-sub {
  font-size: 12px;
  color: var(--admin-text-secondary);
}

/* 菜单选中左侧竖条 */
.admin-sider .ant-menu-item-selected {
  border-inline-start: 3px solid var(--admin-primary) !important;
}

/* StatCard hover */
.admin-stat-card {
  transition: transform 150ms ease, box-shadow 150ms ease;
  box-shadow: var(--admin-shadow-card);
}

.admin-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(67, 56, 202, 0.12);
}

.admin-stat-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--admin-primary-light);
  color: var(--admin-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

/* 登录页 */
.admin-login-root {
  min-height: 100vh;
  display: flex;
}

.admin-login-brand {
  flex: 0 0 45%;
  background: linear-gradient(145deg, #312e81 0%, #4338ca 45%, #6366f1 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 48px;
}

.admin-login-brand::before,
.admin-login-brand::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  pointer-events: none;
}

.admin-login-brand::before {
  width: 320px;
  height: 320px;
  top: -80px;
  right: -60px;
}

.admin-login-brand::after {
  width: 240px;
  height: 240px;
  bottom: -40px;
  left: -40px;
}

.admin-login-brand-inner {
  position: relative;
  z-index: 1;
  color: #fff;
}

.admin-login-pill {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  font-size: 13px;
  margin-bottom: 24px;
}

.admin-login-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 12px;
}

.admin-login-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.75);
  margin: 0 0 32px;
}

.admin-login-bullets {
  margin: 0;
  padding-left: 18px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 2;
}

.admin-login-form-side {
  flex: 1;
  background: var(--admin-bg-layout);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.admin-login-form-card {
  width: 100%;
  max-width: 400px;
  border-radius: 16px !important;
  box-shadow: var(--admin-shadow-elevated) !important;
}

/* 知识库检索结果 */
.admin-search-hit {
  border-left: 3px solid var(--admin-primary);
  padding-left: 16px;
  margin-bottom: 16px;
}

/* 上传 Dragger */
.admin-upload-dragger .ant-upload-drag {
  border-color: #c7d2fe !important;
  background: #faf9ff !important;
}

@media (max-width: 768px) {
  .admin-login-brand {
    display: none;
  }
}
```

- [ ] **Step 2:** 在 `main.tsx` 追加：

```typescript
import '@/styles/admin-theme.css'
```

- [ ] **Step 3:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

### Task 1.3: 公共组件 PageShell / FilterCard / DataCard

**Files:**
- Create: `apps/admin/src/components/PageShell.tsx`
- Create: `apps/admin/src/components/FilterCard.tsx`
- Create: `apps/admin/src/components/DataCard.tsx`

- [ ] **Step 1:** 创建 `PageShell.tsx`：

```tsx
import { ArrowLeftOutlined } from '@ant-design/icons'
import { Button, Space, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

type PageShellProps = {
  title: string
  description?: string
  extra?: ReactNode
  back?: boolean
  children: ReactNode
}

export default function PageShell({ title, description, extra, back, children }: PageShellProps) {
  const navigate = useNavigate()

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 20,
          gap: 16,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          {back && (
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(-1)}
              style={{ marginBottom: 8, paddingInline: 0 }}
            >
              返回
            </Button>
          )}
          <Typography.Title
            level={4}
            style={{ margin: 0, fontWeight: 600, letterSpacing: '-0.02em' }}
          >
            {title}
          </Typography.Title>
          {description && (
            <Typography.Text type="secondary" style={{ fontSize: 13, marginTop: 4, display: 'block' }}>
              {description}
            </Typography.Text>
          )}
        </div>
        {extra && <Space wrap>{extra}</Space>}
      </div>
      {children}
    </div>
  )
}
```

- [ ] **Step 2:** 创建 `FilterCard.tsx`：

```tsx
import { Card } from 'antd'
import type { ReactNode } from 'react'

export default function FilterCard({ children }: { children: ReactNode }) {
  return (
    <Card
      bordered={false}
      style={{ marginBottom: 16, boxShadow: 'var(--admin-shadow-card)' }}
      styles={{ body: { padding: '16px 20px' } }}
    >
      {children}
    </Card>
  )
}
```

- [ ] **Step 3:** 创建 `DataCard.tsx`：

```tsx
import { Card } from 'antd'
import type { ReactNode } from 'react'

type DataCardProps = {
  title?: ReactNode
  children: ReactNode
  /** 表格场景 true → body padding 0 */
  flush?: boolean
  loading?: boolean
}

export default function DataCard({ title, children, flush, loading }: DataCardProps) {
  return (
    <Card
      title={title}
      bordered={false}
      loading={loading}
      style={{ boxShadow: 'var(--admin-shadow-card)' }}
      styles={{ body: { padding: flush ? 0 : 20 } }}
    >
      {children}
    </Card>
  )
}
```

- [ ] **Step 4:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

### Task 1.4: 公共组件 StatCard / EmptyHint + barrel

**Files:**
- Create: `apps/admin/src/components/StatCard.tsx`
- Create: `apps/admin/src/components/EmptyHint.tsx`
- Create: `apps/admin/src/components/index.ts`

- [ ] **Step 1:** 创建 `StatCard.tsx`：

```tsx
import { Card, Statistic } from 'antd'
import type { ReactNode } from 'react'

type StatCardProps = {
  title: string
  value: number | string
  prefix?: ReactNode
  suffix?: ReactNode
  icon: ReactNode
  loading?: boolean
}

export default function StatCard({ title, value, prefix, suffix, icon, loading }: StatCardProps) {
  return (
    <Card
      bordered={false}
      loading={loading}
      className="admin-stat-card"
      styles={{ body: { padding: 20 } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div className="admin-stat-card-icon">{icon}</div>
      </div>
      <Statistic
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={{ fontSize: 28, fontWeight: 700, color: '#18181b' }}
      />
      <div style={{ marginTop: 8, fontSize: 14, color: '#71717a' }}>{title}</div>
    </Card>
  )
}
```

- [ ] **Step 2:** 创建 `EmptyHint.tsx`：

```tsx
import { Empty } from 'antd'

export default function EmptyHint({ description = '暂无数据' }: { description?: string }) {
  return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={description} />
}
```

- [ ] **Step 3:** 创建 `components/index.ts`：

```typescript
export { default as PageShell } from './PageShell'
export { default as FilterCard } from './FilterCard'
export { default as DataCard } from './DataCard'
export { default as StatCard } from './StatCard'
export { default as EmptyHint } from './EmptyHint'
```

- [ ] **Step 4:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 2 — 布局壳与登录页

> **完成标准:** 登录后可见浅色 240px 侧栏、面包屑、头像；登录页左右分栏正常。

---

### Task 2.1: 重写 AdminLayout

**Files:**
- Modify: `apps/admin/src/layout/AdminLayout.tsx`

- [ ] **Step 1:** 完整替换 `AdminLayout.tsx`：

```tsx
import {
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
import { useMemo, useState } from 'react'
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
]

const routeLabels: Record<string, string> = {
  '/': '仪表盘',
  '/knowledge': '知识库',
  '/knowledge/search': '检索测试',
  '/users': '用户管理',
  '/courses': '课程管理',
  '/orders': '订单管理',
  '/analytics': '数据监控',
}

function buildBreadcrumbs(pathname: string) {
  const items: { title: React.ReactNode }[] = [{ title: <HomeOutlined /> }]
  if (pathname === '/') {
    items.push({ title: '仪表盘' })
    return items
  }
  const segments = pathname.split('/').filter(Boolean)
  let acc = ''
  for (let i = 0; i < segments.length; i++) {
    acc += `/${segments[i]}`
    const isId = /^[0-9a-f-]{36}$/i.test(segments[i]) || segments[i].length > 20
    const label = isId
      ? i === segments.length - 1
        ? '详情'
        : routeLabels[acc.replace(/\/[^/]+$/, '')] ?? segments[i]
      : routeLabels[acc] ?? (segments[i] === 'new' ? '新建' : segments[i] === 'edit' ? '编辑' : segments[i])
    items.push({ title: label })
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
        <div className="admin-logo" style={{ justifyContent: collapsed ? 'center' : 'flex-start', padding: collapsed ? '0 8px' : '0 20px' }}>
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
          <Breadcrumb items={breadcrumbs} />
          <Space size={12}>
            <Avatar
              size={32}
              style={{ background: '#eef2ff', color: '#4338ca', fontWeight: 600 }}
            >
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
```

- [ ] **Step 2:** 浏览器验证（需 `pnpm admin` 或 `pnpm all` 运行中）

1. 登录 B 端 `http://localhost:8081`
2. 确认侧栏白底 240px、Logo「E」、菜单选中 Indigo 浅底
3. 确认顶栏面包屑与头像

- [ ] **Step 3:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

### Task 2.2: 重写登录页

**Files:**
- Modify: `apps/admin/src/views/Login.tsx`

- [ ] **Step 1:** 保留现有 `onFinish` 登录逻辑，替换 JSX 为左右分栏结构：

```tsx
// 外层结构：
<div className="admin-login-root">
  <div className="admin-login-brand">
    <div className="admin-login-brand-inner">
      <div className="admin-login-pill">English Learning Platform</div>
      <h1 className="admin-login-title">运营管理后台</h1>
      <p className="admin-login-subtitle">知识库 · 用户 · 课程 · 数据，一站管理</p>
      <ul className="admin-login-bullets">
        <li>仪表盘运营概览</li>
        <li>知识库 RAG 文档管理</li>
        <li>订单与用户数据监控</li>
      </ul>
    </div>
  </div>
  <div className="admin-login-form-side">
    <Card className="admin-login-form-card" bordered={false}>
      {/* 保留原有 Form：phone / password / submit */}
      <Typography.Title level={4} style={{ marginBottom: 4 }}>管理后台登录</Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 24 }}>
        使用管理员账号登录
      </Typography.Paragraph>
      {/* ... Form ... */}
      <Typography.Text type="secondary" style={{ fontSize: 13, display: 'block', marginTop: 16, textAlign: 'center' }}>
        非管理员账号将无法进入
      </Typography.Text>
    </Card>
  </div>
</div>
```

- [ ] **Step 2:** 浏览器验证

1. 访问 `/login`，确认左侧渐变 + 文案、右侧表单 Card
2. 用 `13800000000` / `admin123` 登录成功

- [ ] **Step 3:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 3 — 仪表盘

> **完成标准:** 4+5 StatCard、Indigo 折线图、loading skeleton。

---

### Task 3.1: 重写 Dashboard

**Files:**
- Modify: `apps/admin/src/views/Dashboard.tsx`

- [ ] **Step 1:** 引入组件与图标：

```tsx
import {
  DatabaseOutlined,
  EyeOutlined,
  PayCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Col, Row } from 'antd'
import { Line } from '@ant-design/plots'
import { useQuery } from '@tanstack/react-query'
import { fetchDashboard } from '@/apis/admin'
import { DataCard, EmptyHint, PageShell, StatCard } from '@/components'
```

- [ ] **Step 2:** 定义图表 config helper：

```tsx
const CHART_COLOR = '#4338ca'

function lineConfig(points: { date: string; count: number }[] | undefined) {
  const data = points ?? []
  if (data.length === 0) return null
  return {
    data,
    xField: 'date',
    yField: 'count',
    height: 240,
    smooth: true,
    color: CHART_COLOR,
    areaStyle: { fill: 'l(270) 0:#4338ca33 1:#4338ca00' },
  }
}
```

- [ ] **Step 3:** 页面结构：

```tsx
return (
  <PageShell title="仪表盘" description="平台运营数据概览">
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={6}>
        <StatCard title="总用户" value={stats?.userCount ?? 0} icon={<TeamOutlined />} loading={isLoading} />
      </Col>
      {/* 今日订单额 / 知识库 / 今日 PV — 同上 */}
    </Row>

    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      <Col xs={24} lg={12}>
        <DataCard title="近 7 天新增用户">
          {lineConfig(stats?.newUsersTrend) ? (
            <Line {...lineConfig(stats!.newUsersTrend)!} />
          ) : (
            <EmptyHint description="暂无趋势数据" />
          )}
        </DataCard>
      </Col>
      {/* PV 趋势 */}
    </Row>

    <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
      {/* 5 个小 StatCard：todayNewUsers, courseCount, todayOrders, totalRevenue(¥), recentErrors */}
    </Row>
  </PageShell>
)
```

- [ ] **Step 4:** 浏览器验证首页 StatCard hover 与图表 Indigo 色

- [ ] **Step 5:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 4 — 列表页迁移

> **完成标准:** 4 个 List 页均 PageShell + FilterCard（课程可无 Filter）+ DataCard；表格 `size="middle"` + `showTotal`。

---

### Task 4.1: 订单列表

**Files:**
- Modify: `apps/admin/src/views/orders/List.tsx`

- [ ] **Step 1:** 删除顶部 `Typography.Title level={4}`
- [ ] **Step 2:** 包裹结构：

```tsx
<PageShell title="订单管理" description="查看与筛选平台支付订单">
  <FilterCard>
    <Space wrap>{/* 现有 Input.Search / Select / RangePicker */}</Space>
  </FilterCard>
  <DataCard flush>
    <Table size="middle" pagination={{ ...existing, showTotal: (t) => `共 ${t} 条` }} />
  </DataCard>
</PageShell>
```

- [ ] **Step 3:** 金额列加 `align: 'right'`，render 用 `<span style={{ fontWeight: 600 }}>`

---

### Task 4.2: 用户列表

**Files:**
- Modify: `apps/admin/src/views/users/List.tsx`

- [ ] **Step 1:** 同 Task 4.1 模式，`title="用户管理"` `description="查看注册用户与学习数据"`

---

### Task 4.3: 课程列表

**Files:**
- Modify: `apps/admin/src/views/courses/List.tsx`

- [ ] **Step 1:** 将「新建课程」Button 移到 PageShell `extra`：

```tsx
<PageShell
  title="课程管理"
  description="管理平台课程与上下架状态"
  extra={<Button type="primary" onClick={() => navigate('/courses/new')}>新建课程</Button>}
>
  <DataCard flush>
    <Table ... />
  </DataCard>
</PageShell>
```

- [ ] **Step 2:** 删除原 `Space justifyContent space-between` 标题行

---

### Task 4.4: 知识库列表

**Files:**
- Modify: `apps/admin/src/views/knowledge/List.tsx`

- [ ] **Step 1:** PageShell + FilterCard（搜索 + 跳转检索测试按钮）
- [ ] **Step 2:** Dragger 独立 Card，`className="admin-upload-dragger"`，放在 FilterCard 与 DataCard 之间
- [ ] **Step 3:** Table 放入 DataCard flush

- [ ] **Step 4:** 验证编译 + 浏览器抽查 4 个列表页

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 5 — 详情页与表单

> **完成标准:** 3 个 Detail + 1 个 Form 均使用 PageShell back + DataCard。

---

### Task 5.1: 订单详情

**Files:**
- Modify: `apps/admin/src/views/orders/Detail.tsx`

- [ ] **Step 1:** 删除 `Typography.Link` 返回链
- [ ] **Step 2:** 结构：

```tsx
<PageShell
  title={`订单 ${order?.outTradeNo ?? ''}`}
  back
  extra={statusMeta ? <Tag color={statusMeta.color}>{statusMeta.label}</Tag> : undefined}
>
  <DataCard loading={isLoading}>
    <Descriptions column={2} bordered size="small" labelStyle={{ width: 120, background: '#fafafa' }}>
      {/* 现有字段 */}
    </Descriptions>
    <Typography.Title level={5} style={{ marginTop: 24 }}>关联课程</Typography.Title>
    <Table ... />
  </DataCard>
</PageShell>
```

---

### Task 5.2: 用户详情

**Files:**
- Modify: `apps/admin/src/views/users/Detail.tsx`

- [ ] **Step 1:** `PageShell title={user?.name ?? '用户详情'} back` + DataCard 包裹 Descriptions 与已购课程 Table

---

### Task 5.3: 知识库详情

**Files:**
- Modify: `apps/admin/src/views/knowledge/Detail.tsx`

- [ ] **Step 1:** `PageShell title={doc?.title ?? '文档详情'} back` + Row/Col 布局（主 Descriptions + 侧 chunk 列表 DataCard）

---

### Task 5.4: 课程表单

**Files:**
- Modify: `apps/admin/src/views/courses/Form.tsx`

- [ ] **Step 1:** 删除 `Typography.Link` 返回
- [ ] **Step 2:**

```tsx
<PageShell title={isEdit ? '编辑课程' : '新建课程'} back>
  <Card bordered={false} style={{ maxWidth: 640, boxShadow: 'var(--admin-shadow-card)' }}>
    <Form layout="vertical" ...>
      {/* 现有字段 */}
      <Space style={{ marginTop: 8 }}>
        <Button onClick={() => navigate('/courses')}>取消</Button>
        <Button type="primary" htmlType="submit" loading={saveMut.isPending}>保存</Button>
      </Space>
    </Form>
  </Card>
</PageShell>
```

- [ ] **Step 3:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 6 — 数据监控与知识库检索

---

### Task 6.1: 数据监控 Overview

**Files:**
- Modify: `apps/admin/src/views/analytics/Overview.tsx`

- [ ] **Step 1:** 顶部改为：

```tsx
<PageShell title="数据监控" description="埋点趋势与前端质量">
  <FilterCard>
    <DaysPicker ... />
    <Segmented ... />
  </FilterCard>
  {/* 概览 StatCard 行 */}
  <Tabs items={[...]} />
</PageShell>
```

- [ ] **Step 2:** 各 Tab 内图表/表格用 DataCard 包裹；Line/Column 图 `color: '#4338ca'`
- [ ] **Step 3:** 错误表格时间列保持 `formatDateTime`

---

### Task 6.2: 知识库检索页

**Files:**
- Modify: `apps/admin/src/views/knowledge/Search.tsx`

- [ ] **Step 1:** 删除顶部 Link+Title 行，改为：

```tsx
<PageShell title="检索测试" description="测试知识库向量检索效果" back>
  <FilterCard>
    <Space wrap>{/* TopK + Input + 检索 Button primary */}</Space>
  </FilterCard>
  <DataCard>
    {results.length === 0 ? (
      <EmptyHint description="输入问题后点击检索" />
    ) : (
      results.map((hit) => (
        <div key={hit.chunkId} className="admin-search-hit">
          <Space><Tag color="blue">相似度 {(hit.score * 100).toFixed(1)}%</Tag></Space>
          <Typography.Paragraph ellipsis={{ rows: 3 }}>{hit.content}</Typography.Paragraph>
        </div>
      ))
    )}
  </DataCard>
</PageShell>
```

- [ ] **Step 2:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 7 — 清理与终验

---

### Task 7.1: 删除 Placeholder

**Files:**
- Delete: `apps/admin/src/views/Placeholder.tsx`

- [ ] **Step 1:** 删除文件
- [ ] **Step 2:** 全仓库 grep 确认无 import：

Run: `rg "Placeholder" apps/admin`
Expected: 无匹配

---

### Task 7.2: 更新设计文档状态

**Files:**
- Modify: `docs/superpowers/specs/2026-06-25-admin-ui-redesign-design.md`

- [ ] **Step 1:** 将首行状态改为：

```markdown
> 状态：**已评审** — 实现计划：[2026-06-25-admin-ui-redesign.md](../plans/2026-06-25-admin-ui-redesign.md)
```

---

### Task 7.3: 终验清单

- [ ] **Step 1:** 构建

Run: `pnpm --filter @en/admin build`
Expected: PASS，无 TS 错误

- [ ] **Step 2:** grep 确认无裸 Title 顶页（Login 除外）

Run: `rg "Typography\.Title level=\{4\}" apps/admin/src/views`
Expected: 无匹配（Title 仅存在于 PageShell / Login / 区块小标题 level 5）

- [ ] **Step 3:** grep 确认 12 个 view 均 import PageShell

Run: `rg "PageShell" apps/admin/src/views --files-with-matches`
Expected: 12 个文件（Dashboard, orders/List, orders/Detail, users/List, users/Detail, courses/List, courses/Form, knowledge/List, knowledge/Detail, knowledge/Search, analytics/Overview）— **不含 Login**

- [ ] **Step 4:** 浏览器手动验收（`pnpm admin`）

| 页面 | 检查项 |
|------|--------|
| `/login` | 渐变左栏 + 表单 Card |
| `/` | 4 StatCard hover + Indigo 图表 |
| `/orders` | FilterCard + 表格 Card |
| `/orders/:id` | 返回 + 状态 Tag extra |
| `/users` `/courses` `/knowledge` | 统一布局 |
| `/analytics` | Tabs + 图表 Indigo |
| `/knowledge/search` | 检索结果左竖条 |
| 768px 宽 | 登录左栏隐藏；侧栏可折叠 |

- [ ] **Step 5:** 可选 commit（仅用户要求时）

```bash
git add apps/admin docs/superpowers
git commit -m "feat(admin): redesign UI with Indigo brand theme"
```

---

## Spec Coverage Self-Review

| Spec 章节 | 对应 Task |
|-----------|-----------|
| 设计 Token | Task 1.1, 1.2 |
| 布局壳 AdminLayout | Task 2.1 |
| 登录页 | Task 2.2 |
| PageShell / FilterCard / DataCard / StatCard / EmptyHint | Task 1.3, 1.4 |
| 仪表盘 | Task 3.1 |
| 列表页规范 | Task 4.1–4.4 |
| 详情页规范 | Task 5.1–5.3 |
| 课程表单 | Task 5.4 |
| 数据监控 | Task 6.1 |
| 知识库检索 | Task 6.2 |
| Placeholder 删除 | Task 7.1 |
| 验收标准 1–6 | Task 7.3 |

**无遗漏。**

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-25-admin-ui-redesign.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每个 Phase/Task 派生子 agent，任务间 review，迭代快
2. **Inline Execution** — 在本会话按 Phase 顺序直接改代码，每 Phase 结束后 checkpoint 给你看

**Which approach?**
