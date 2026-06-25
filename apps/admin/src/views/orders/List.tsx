import { DatePicker, Input, Segmented, Select, Space, Table, Tag, Button, message } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { downloadOrdersCsv, fetchOrders } from '@/apis/admin'
import { DataCard, FilterCard, PageShell } from '@/components'
import { formatDateTime } from '@/utils/datetime'
import { TRADE_STATUS_MAP, type AdminOrder } from '@en/common/admin'

const { RangePicker } = DatePicker

type OrderTab = 'all' | 'unpaid'

export default function OrderListPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)
  const [tab, setTab] = useState<OrderTab>('all')
  const [exporting, setExporting] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    if (searchParams.get('tab') === 'unpaid') {
      setTab('unpaid')
      setStatus('UNPAID')
      setPage(1)
    }
  }, [searchParams])

  const effectiveStatus = tab === 'unpaid' ? 'UNPAID' : status

  const { data, isLoading } = useQuery({
    queryKey: ['admin-orders', page, pageSize, search, effectiveStatus, dateRange],
    queryFn: () =>
      fetchOrders({
        page,
        pageSize,
        keyword: search || undefined,
        status: effectiveStatus,
        startDate: dateRange?.[0],
        endDate: dateRange?.[1],
      }),
  })

  const columns = [
    { title: '订单号', dataIndex: 'outTradeNo', key: 'outTradeNo' },
    { title: '用户', dataIndex: 'userName', key: 'userName' },
    { title: '手机号', dataIndex: 'userPhone', key: 'userPhone' },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      align: 'right' as const,
      render: (v: number) => <span style={{ fontWeight: 600 }}>¥{v.toFixed(2)}</span>,
    },
    {
      title: '状态',
      dataIndex: 'tradeStatus',
      key: 'tradeStatus',
      render: (v: string) => {
        const meta = TRADE_STATUS_MAP[v] ?? { label: v, color: 'default' }
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (v: string) => formatDateTime(v),
    },
  ]

  const handleTabChange = (value: OrderTab) => {
    setTab(value)
    setPage(1)
    if (value === 'unpaid') {
      setSearchParams({ tab: 'unpaid' })
    } else {
      setSearchParams({})
      setStatus(undefined)
    }
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      await downloadOrdersCsv({
        status: effectiveStatus,
        startDate: dateRange?.[0],
        endDate: dateRange?.[1],
        keyword: search || undefined,
      })
    } catch {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  return (
    <PageShell title="订单管理" description="查看与筛选平台支付订单">
      <Segmented
        options={[
          { label: '全部', value: 'all' },
          { label: '待支付', value: 'unpaid' },
        ]}
        value={tab}
        onChange={(v) => handleTabChange(v as OrderTab)}
        style={{ marginBottom: 16 }}
      />
      <FilterCard>
        <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Input.Search
              placeholder="订单号 / 用户名"
              allowClear
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={(v) => {
                setSearch(v)
                setPage(1)
              }}
              style={{ width: 220 }}
            />
            {tab === 'all' && (
              <Select
                allowClear
                placeholder="订单状态"
                style={{ width: 140 }}
                value={status}
                onChange={(v) => {
                  setStatus(v)
                  setPage(1)
                }}
                options={Object.entries(TRADE_STATUS_MAP).map(([value, { label }]) => ({
                  value,
                  label,
                }))}
              />
            )}
            <RangePicker
              onChange={(dates) => {
                if (!dates || !dates[0] || !dates[1]) {
                  setDateRange(null)
                } else {
                  setDateRange([dates[0].toISOString(), dates[1].toISOString()])
                }
                setPage(1)
              }}
            />
          </Space>
          <Button loading={exporting} onClick={() => void handleExport()}>
            导出 CSV
          </Button>
        </Space>
      </FilterCard>
      <DataCard flush>
        <Table<AdminOrder>
          rowKey="id"
          size="middle"
          loading={isLoading}
          columns={columns}
          dataSource={data?.data.list ?? []}
          onRow={(record) => ({
            onClick: () => navigate(`/orders/${record.id}`),
            style: { cursor: 'pointer' },
          })}
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
    </PageShell>
  )
}
