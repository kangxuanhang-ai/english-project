import { Descriptions, Table, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { fetchUserDetail } from '@/apis/admin'
import { DataCard, PageShell } from '@/components'
import { formatDateTime } from '@/utils/datetime'

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-user', id],
    queryFn: () => fetchUserDetail(id!),
    enabled: !!id,
  })

  const user = data?.data

  return (
    <PageShell title={user?.name ?? '用户详情'} back>
      <DataCard loading={isLoading}>
        {user && (
          <>
            <Descriptions
              column={2}
              bordered
              size="small"
              labelStyle={{ width: 120, background: '#fafafa' }}
            >
              <Descriptions.Item label="手机号">{user.phone}</Descriptions.Item>
              <Descriptions.Item label="邮箱">{user.email ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="掌握词数">{user.masteredWords}</Descriptions.Item>
              <Descriptions.Item label="已购课程">{user.purchasedCourses}</Descriptions.Item>
              <Descriptions.Item label="打卡天数">{user.dayNumber}</Descriptions.Item>
              <Descriptions.Item label="注册时间">
                {formatDateTime(user.createdAt)}
              </Descriptions.Item>
              <Descriptions.Item label="最近登录" span={2}>
                {formatDateTime(user.lastLoginAt)}
              </Descriptions.Item>
            </Descriptions>

            <Typography.Title level={5} style={{ marginTop: 24 }}>
              已购课程
            </Typography.Title>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={user.recentCourses}
              columns={[
                { title: '课程名', dataIndex: 'name' },
                { title: '类型', dataIndex: 'value' },
                {
                  title: '购买时间',
                  dataIndex: 'purchasedAt',
                  render: (v: string) => formatDateTime(v),
                },
              ]}
            />
          </>
        )}
      </DataCard>
    </PageShell>
  )
}
