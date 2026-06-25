import {
  DatabaseOutlined,
  EyeOutlined,
  PayCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Col, Row, Alert, Button, Space } from 'antd'
import { Line } from '@ant-design/plots'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchDashboard } from '@/apis/admin'
import { DataCard, EmptyHint, PageShell, StatCard } from '@/components'

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

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: fetchDashboard,
  })
  const stats = data?.data

  const usersTrend = lineConfig(stats?.newUsersTrend)
  const pvTrend = lineConfig(stats?.pvTrend)

  return (
    <PageShell title="仪表盘" description="平台运营数据概览">
      {(stats?.unpaidOrders ?? 0) > 0 || (stats?.failedKnowledgeDocs ?? 0) > 0 ? (
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
          {(stats?.unpaidOrders ?? 0) > 0 && (
            <Alert
              type="warning"
              showIcon
              message={`${stats!.unpaidOrders} 笔订单待支付`}
              action={
                <Button size="small" onClick={() => navigate('/orders?tab=unpaid')}>
                  去处理
                </Button>
              }
            />
          )}
          {(stats?.failedKnowledgeDocs ?? 0) > 0 && (
            <Alert
              type="error"
              showIcon
              message={`${stats!.failedKnowledgeDocs} 个知识库文档索引失败`}
              action={
                <Button size="small" onClick={() => navigate('/knowledge?status=failed')}>
                  去查看
                </Button>
              }
            />
          )}
        </Space>
      ) : null}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="总用户"
            value={stats?.userCount ?? 0}
            icon={<TeamOutlined />}
            loading={isLoading}
            onClick={() => navigate('/users')}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="今日订单额"
            value={stats?.todayRevenue ?? 0}
            prefix="¥"
            icon={<PayCircleOutlined />}
            loading={isLoading}
            onClick={() => navigate('/orders')}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="知识库文档"
            value={stats?.knowledgeDocCount ?? 0}
            suffix={`/ ${stats?.knowledgeReadyCount ?? 0} 就绪`}
            icon={<DatabaseOutlined />}
            loading={isLoading}
            onClick={() => navigate('/knowledge')}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="今日 PV"
            value={stats?.todayPv ?? 0}
            suffix={`UV ${stats?.todayUv ?? 0}`}
            icon={<EyeOutlined />}
            loading={isLoading}
            onClick={() => navigate('/analytics')}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <DataCard title="近 7 天新增用户">
            {usersTrend ? <Line {...usersTrend} /> : <EmptyHint description="暂无趋势数据" />}
          </DataCard>
        </Col>
        <Col xs={24} lg={12}>
          <DataCard title="近 7 天 PV">
            {pvTrend ? <Line {...pvTrend} /> : <EmptyHint description="暂无趋势数据" />}
          </DataCard>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={8} xl={4}>
          <StatCard
            title="今日新用户"
            value={stats?.todayNewUsers ?? 0}
            icon={<TeamOutlined />}
            loading={isLoading}
            onClick={() => navigate('/users')}
          />
        </Col>
        <Col xs={24} sm={12} lg={8} xl={5}>
          <StatCard
            title="课程总数"
            value={stats?.courseCount ?? 0}
            icon={<DatabaseOutlined />}
            loading={isLoading}
            onClick={() => navigate('/courses')}
          />
        </Col>
        <Col xs={24} sm={12} lg={8} xl={5}>
          <StatCard
            title="今日订单数"
            value={stats?.todayOrders ?? 0}
            icon={<PayCircleOutlined />}
            loading={isLoading}
            onClick={() => navigate('/orders')}
          />
        </Col>
        <Col xs={24} sm={12} lg={8} xl={5}>
          <StatCard
            title="累计收入"
            value={stats?.totalRevenue ?? 0}
            prefix="¥"
            icon={<PayCircleOutlined />}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} sm={12} lg={8} xl={5}>
          <StatCard
            title="近 7 天错误"
            value={stats?.recentErrors ?? 0}
            icon={<EyeOutlined />}
            loading={isLoading}
            onClick={() => navigate('/analytics?tab=errors')}
          />
        </Col>
      </Row>
    </PageShell>
  )
}
