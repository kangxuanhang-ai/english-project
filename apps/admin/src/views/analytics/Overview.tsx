import { Col, Row, Segmented, Space, Table, Tabs } from 'antd'
import { Column, Line } from '@ant-design/plots'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  fetchAnalyticsErrors,
  fetchAnalyticsOverview,
  fetchAnalyticsPages,
  fetchAnalyticsPerformance,
} from '@/apis/admin'
import { DataCard, FilterCard, PageShell, StatCard } from '@/components'
import { formatDateTime } from '@/utils/datetime'
import type { AdminErrorItem, AdminPerformanceTrendPoint, TrendPoint } from '@en/common/admin'
import { EyeOutlined } from '@ant-design/icons'

const CHART_COLOR = '#4338ca'

type DaysRange = 7 | 30

function DaysPicker({ value, onChange }: { value: DaysRange; onChange: (v: DaysRange) => void }) {
  return (
    <Segmented
      options={[
        { label: '近 7 天', value: 7 },
        { label: '近 30 天', value: 30 },
      ]}
      value={value}
      onChange={(v) => onChange(v as DaysRange)}
    />
  )
}

function TrafficTab() {
  const [days, setDays] = useState<DaysRange>(7)

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['admin-analytics-overview', days],
    queryFn: () => fetchAnalyticsOverview(days),
  })
  const { data: pages, isLoading: pagesLoading } = useQuery({
    queryKey: ['admin-analytics-pages', days],
    queryFn: () => fetchAnalyticsPages(days),
  })

  const trafficData = useMemo(() => {
    const pv = overview?.data.pvTrend ?? []
    const uv = overview?.data.uvTrend ?? []
    return [
      ...pv.map((d: TrendPoint) => ({ date: d.date, count: d.count, type: 'PV' })),
      ...uv.map((d: TrendPoint) => ({ date: d.date, count: d.count, type: 'UV' })),
    ]
  }, [overview])

  const latestPv = overview?.data.pvTrend?.at(-1)?.count ?? 0
  const latestUv = overview?.data.uvTrend?.at(-1)?.count ?? 0

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <FilterCard>
        <DaysPicker value={days} onChange={setDays} />
      </FilterCard>
      <Row gutter={16}>
        <Col xs={24} sm={12}>
          <StatCard title="最新 PV" value={latestPv} icon={<EyeOutlined />} loading={overviewLoading} />
        </Col>
        <Col xs={24} sm={12}>
          <StatCard title="最新 UV" value={latestUv} icon={<EyeOutlined />} loading={overviewLoading} />
        </Col>
      </Row>
      <DataCard title="PV / UV 趋势" loading={overviewLoading}>
        <Line
          data={trafficData}
          xField="date"
          yField="count"
          seriesField="type"
          height={280}
          smooth
          color={[CHART_COLOR, '#6366f1']}
        />
      </DataCard>
      <DataCard title="页面 PV Top 20" loading={pagesLoading}>
        <Column
          data={pages?.data.list ?? []}
          xField="path"
          yField="count"
          height={320}
          color={CHART_COLOR}
          label={{ position: 'top' }}
          xAxis={{ label: { autoRotate: true } }}
        />
      </DataCard>
    </Space>
  )
}

function ErrorsTab() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-analytics-errors', page, pageSize],
    queryFn: () => fetchAnalyticsErrors({ page, pageSize }),
  })

  const columns = [
    { title: '类型', dataIndex: 'error', key: 'error', width: 160, ellipsis: true },
    { title: '消息', dataIndex: 'message', key: 'message', ellipsis: true },
    { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
    {
      title: '时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 180,
      render: (v: string | null | undefined) => formatDateTime(v),
    },
  ]

  return (
    <DataCard flush>
      <Table<AdminErrorItem>
        rowKey="id"
        size="middle"
        loading={isLoading}
        columns={columns}
        dataSource={data?.data.list ?? []}
        expandable={{
          expandedRowRender: (record) => (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>
              {record.stack || '无 stack 信息'}
            </pre>
          ),
          rowExpandable: (record) => !!record.stack,
        }}
        pagination={{
          current: page,
          pageSize,
          total: data?.data.total ?? 0,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />
    </DataCard>
  )
}

function PerformanceTab() {
  const [days, setDays] = useState<DaysRange>(7)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-analytics-performance', days],
    queryFn: () => fetchAnalyticsPerformance(days),
  })

  const avg = data?.data.avg
  const trendData = useMemo(() => {
    const trend = data?.data.trend ?? []
    return [
      ...trend.map((d: AdminPerformanceTrendPoint) => ({ date: d.date, value: d.lcp, metric: 'LCP' })),
      ...trend.map((d: AdminPerformanceTrendPoint) => ({ date: d.date, value: d.fcp, metric: 'FCP' })),
    ].filter((d) => d.value != null)
  }, [data])

  const metrics = [
    { title: 'FP (ms)', value: avg?.fp ?? '-' },
    { title: 'FCP (ms)', value: avg?.fcp ?? '-' },
    { title: 'LCP (ms)', value: avg?.lcp ?? '-' },
    { title: 'INP (ms)', value: avg?.inp ?? '-' },
    { title: 'CLS', value: avg?.cls ?? '-' },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <FilterCard>
        <DaysPicker value={days} onChange={setDays} />
      </FilterCard>
      <Row gutter={[16, 16]}>
        {metrics.map((m) => (
          <Col xs={12} sm={8} md={4} key={m.title}>
            <StatCard title={m.title} value={m.value} icon={<EyeOutlined />} loading={isLoading} />
          </Col>
        ))}
      </Row>
      <DataCard title="LCP / FCP 趋势" loading={isLoading}>
        <Line
          data={trendData}
          xField="date"
          yField="value"
          seriesField="metric"
          height={280}
          smooth
          color={[CHART_COLOR, '#6366f1']}
        />
      </DataCard>
    </Space>
  )
}

export default function AnalyticsOverviewPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') ?? 'traffic'
  const [activeTab, setActiveTab] = useState(initialTab)

  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab) setActiveTab(tab)
  }, [searchParams])

  return (
    <PageShell title="数据监控" description="埋点趋势与前端质量">
      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          setActiveTab(key)
          setSearchParams(key === 'traffic' ? {} : { tab: key })
        }}
        items={[
          { key: 'traffic', label: '流量', children: <TrafficTab /> },
          { key: 'errors', label: '错误', children: <ErrorsTab /> },
          { key: 'performance', label: '性能', children: <PerformanceTab /> },
        ]}
      />
    </PageShell>
  )
}
