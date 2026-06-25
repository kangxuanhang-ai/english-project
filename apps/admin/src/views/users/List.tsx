import { Input, Segmented, Table } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchUsers } from '@/apis/admin'
import { DataCard, FilterCard, PageShell } from '@/components'
import { formatDateTime } from '@/utils/datetime'
import type { AdminUserItem } from '@en/common/admin'

type UserTab = 'user' | 'admin'

export default function UserListPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<UserTab>('user')
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, pageSize, search, tab],
    queryFn: () =>
      fetchUsers({ page, pageSize, keyword: search || undefined, role: tab }),
  })

  const columns = useMemo(() => {
    const base = [
      { title: '昵称', dataIndex: 'name', key: 'name' },
      { title: '手机号', dataIndex: 'phone', key: 'phone' },
    ]
    if (tab === 'user') {
      return [
        ...base,
        { title: '掌握词数', dataIndex: 'masteredWords', key: 'masteredWords' },
        { title: '打卡天数', dataIndex: 'dayNumber', key: 'dayNumber' },
        {
          title: '注册时间',
          dataIndex: 'createdAt',
          key: 'createdAt',
          render: (v: string) => formatDateTime(v),
        },
        {
          title: '最近登录',
          dataIndex: 'lastLoginAt',
          key: 'lastLoginAt',
          render: (v: string) => formatDateTime(v),
        },
      ]
    }
    return [
      ...base,
      { title: '邮箱', dataIndex: 'email', key: 'email', render: (v: string) => v || '—' },
      {
        title: '注册时间',
        dataIndex: 'createdAt',
        key: 'createdAt',
        render: (v: string) => formatDateTime(v),
      },
      {
        title: '最近登录',
        dataIndex: 'lastLoginAt',
        key: 'lastLoginAt',
        render: (v: string) => formatDateTime(v),
      },
    ]
  }, [tab])

  return (
    <PageShell
      title="用户管理"
      description={
        tab === 'user' ? 'C 端学员：学习数据与注册信息' : 'B 端管理员：后台登录账号'
      }
    >
      <FilterCard>
        <div className="flex flex-wrap items-center gap-3">
          <Segmented
            value={tab}
            options={[
              { label: 'C 端学员', value: 'user' },
              { label: 'B 端管理员', value: 'admin' },
            ]}
            onChange={(v) => {
              setTab(v as UserTab)
              setPage(1)
            }}
          />
          <Input.Search
            placeholder="搜索姓名/手机号/邮箱"
            allowClear
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={(v) => {
              setSearch(v)
              setPage(1)
            }}
            style={{ width: 280 }}
          />
        </div>
      </FilterCard>
      <DataCard flush>
        <Table<AdminUserItem>
          rowKey="id"
          size="middle"
          loading={isLoading}
          columns={columns}
          dataSource={data?.data.list ?? []}
          onRow={(record) => ({
            onClick: () => navigate(`/users/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current: page,
            pageSize,
            total: data?.data.total ?? 0,
            showTotal: (t) => `共 ${t} 条`,
            showSizeChanger: true,
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
