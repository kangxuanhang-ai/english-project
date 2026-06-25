import { Descriptions, Table, Tag, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchOrderDetail } from '@/apis/admin'
import { DataCard, PageShell } from '@/components'
import { formatDateTime } from '@/utils/datetime'
import { TRADE_STATUS_MAP } from '@en/common/admin'

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-order', id],
    queryFn: () => fetchOrderDetail(id!),
    enabled: !!id,
  })

  const order = data?.data
  const statusMeta = order ? TRADE_STATUS_MAP[order.tradeStatus] : null

  return (
    <PageShell
      title={order ? `订单 ${order.outTradeNo}` : '订单详情'}
      back
      extra={
        statusMeta ? <Tag color={statusMeta.color}>{statusMeta.label}</Tag> : undefined
      }
    >
      <DataCard loading={isLoading}>
        {order && (
          <>
            <Descriptions
              column={2}
              bordered
              size="small"
              labelStyle={{ width: 120, background: '#fafafa' }}
            >
              <Descriptions.Item label="商户订单号">{order.outTradeNo}</Descriptions.Item>
              <Descriptions.Item label="支付宝单号">{order.tradeNo ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="用户">
                <Link to={`/users/${order.userId}`}>{order.userName ?? '-'}</Link>
              </Descriptions.Item>
              <Descriptions.Item label="手机号">
                <Link to={`/users/${order.userId}`}>{order.userPhone ?? '-'}</Link>
              </Descriptions.Item>
              <Descriptions.Item label="金额">¥{order.amount.toFixed(2)}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {statusMeta ? <Tag color={statusMeta.color}>{statusMeta.label}</Tag> : order.tradeStatus}
              </Descriptions.Item>
              <Descriptions.Item label="标题" span={2}>
                {order.subject}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatDateTime(order.createdAt)}
              </Descriptions.Item>
              <Descriptions.Item label="支付时间">
                {formatDateTime(order.sendPayTime)}
              </Descriptions.Item>
            </Descriptions>

            <Typography.Title level={5} style={{ marginTop: 24 }}>
              关联课程
            </Typography.Title>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={order.courses}
              columns={[
                { title: '课程名', dataIndex: 'name' },
                { title: '类型', dataIndex: 'value' },
              ]}
            />
          </>
        )}
      </DataCard>
    </PageShell>
  )
}
